#!/usr/bin/env node
/**
 * inventory x recipes -> candidates.json (every match carries file:line).
 *
 * Scanning is line-based on purpose. js-yaml gives us structure but not line
 * numbers, and a parsed-then-redumped YAML loses comments, key order and the
 * `guide: |` block scalars — so the raw text is the scan surface and the parsed
 * copy only answers "which block does this line belong to".
 *
 * Scope (see .claude/commands/sync-vllm.md):
 *   editable     models/**\/*.yaml
 *   report-only  taxonomy.yaml, strategies/*.yaml, kv_store/*.yaml, scripts/,
 *                src/lib/command-synthesis.js
 *
 * Upstream facts come from flagset.py / index_flags.py / inventory.py, spawned
 * directly — never from Bash git output, which rtk truncates. See README.md.
 */

import { execFileSync } from "node:child_process";
import { readFileSync, writeFileSync, readdirSync, statSync, mkdirSync } from "node:fs";
import { join, relative, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import yaml from "js-yaml";

const HERE = dirname(fileURLToPath(import.meta.url));
const REPO = join(HERE, "..", "..");

const REPORT_ONLY_FILES = [
  "taxonomy.yaml",
  "src/lib/command-synthesis.js",
];
const REPORT_ONLY_DIRS = ["strategies", "kv_store", "scripts"];

const FLAG_RE = /(?<![-\w])(--[a-z0-9][a-z0-9-]*(?:\.[\w.]+)?)(?![-\w])/g;
const ENV_RE = /\b(VLLM_[A-Z0-9_]{2,}[A-Z0-9])\b/g;

// Structured vLLM argument/env blocks: the only places a token is definitely
// meant for `vllm serve`, so the only places an unknown flag means anything.
const ARG_PATH_RE = /(^|\.)(base_args|extra_args|args)$/;
// The env var name is itself a YAML key, so the path is `…extra_env.VLLM_X`,
// not `…extra_env`.
const ENV_PATH_RE = /(^|\.)(base_env|extra_env|env)(\.[A-Za-z_]\w*)?$/;

// Flags belonging to other tools that legitimately appear beside vLLM commands
// in guides and in the synthesis source. Without this, `docker run --device`
// reads as vLLM's removed --device flag.
const FOREIGN_FLAGS = new Set([
  "--gpus", "--device", "--network", "--net", "--ipc", "--shm-size", "--privileged",
  "--security-opt", "--group-add", "--entrypoint", "--rm", "--volume", "--env-file",
  "--pre", "--extra-index-url", "--index-strategy", "--index-url", "--torch-backend",
  "--upgrade", "--no-cache-dir", "--no-deps", "--force-reinstall",
]);

// ---------------------------------------------------------------------------
// upstream facts
// ---------------------------------------------------------------------------

function python(script, args) {
  return JSON.parse(
    execFileSync("python3", [join(HERE, script), ...args], {
      encoding: "utf8",
      maxBuffer: 64 * 1024 * 1024,
    })
  );
}

// ---------------------------------------------------------------------------
// file walking
// ---------------------------------------------------------------------------

function walk(dir, out = []) {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    const st = statSync(full);
    if (st.isDirectory()) walk(full, out);
    else out.push(full);
  }
  return out;
}

function targetFiles() {
  const files = [];
  for (const f of walk(join(REPO, "models"))) {
    if (f.endsWith(".yaml")) files.push({ path: f, editable: true });
  }
  for (const f of REPORT_ONLY_FILES) {
    files.push({ path: join(REPO, f), editable: false });
  }
  for (const d of REPORT_ONLY_DIRS) {
    for (const f of walk(join(REPO, d))) {
      if (/\.(yaml|mjs|js|sh)$/.test(f)) files.push({ path: f, editable: false });
    }
  }
  return files;
}

// ---------------------------------------------------------------------------
// YAML path tracking: which block owns each line
// ---------------------------------------------------------------------------

/**
 * Returns an array parallel to `lines` holding the dotted key path of each
 * line. Block scalars (`guide: |`) are handled explicitly: their body is
 * markdown, where a line like "Note: this" would otherwise be read as a key
 * and corrupt the path for the rest of the file.
 */
function pathsForLines(lines) {
  const paths = new Array(lines.length).fill("");
  const stack = []; // {indent, key}
  let block = null; // {indent, path}

  lines.forEach((line, i) => {
    if (block) {
      const indent = line.search(/\S/);
      if (line.trim() === "" || indent > block.indent) {
        paths[i] = block.path;
        return;
      }
      block = null;
    }
    const keyMatch = line.match(/^(\s*)([A-Za-z_][\w.-]*):(\s|$)/);
    const itemMatch = line.match(/^(\s*)-\s/);
    if (keyMatch) {
      const indent = keyMatch[1].length;
      while (stack.length && stack[stack.length - 1].indent >= indent) stack.pop();
      stack.push({ indent, key: keyMatch[2] });
      paths[i] = stack.map((s) => s.key).join(".");
      if (/:\s*[|>][-+0-9]*\s*$/.test(line)) {
        block = { indent, path: paths[i] };
      }
      return;
    }
    if (itemMatch) {
      const indent = itemMatch[1].length;
      while (stack.length && stack[stack.length - 1].indent >= indent + 2) stack.pop();
    }
    paths[i] = stack.map((s) => s.key).join(".");
  });
  return paths;
}

// ---------------------------------------------------------------------------
// recipe context
// ---------------------------------------------------------------------------

/** "nightly"/"main" pins mean "whatever is current", i.e. no floor at all. */
function isUnboundedPin(v) {
  return !v || !/^v?\d/.test(String(v));
}

function versionKey(v) {
  return String(v || "")
    .replace(/^v/, "")
    .split(".")
    .map((p) => parseInt(p, 10) || 0);
}

function cmpVersion(a, b) {
  const [x, y] = [versionKey(a), versionKey(b)];
  for (let i = 0; i < Math.max(x.length, y.length); i += 1) {
    if ((x[i] || 0) !== (y[i] || 0)) return (x[i] || 0) - (y[i] || 0);
  }
  return 0;
}

/** The lowest vLLM version that has to run the command this line belongs to. */
function effectiveFloor(doc, path) {
  const declared = doc?.model?.min_vllm_version || null;
  const modelFloor = isUnboundedPin(declared) ? null : declared;
  const variant = path.match(/^variants\.([\w-]+)\b/);
  if (variant && doc?.variants?.[variant[1]]) {
    const v = doc.variants[variant[1]];
    if (v.nightly_required) return { floor: null, reason: "variant requires nightly" };
    if (v.min_vllm_version && !isUnboundedPin(v.min_vllm_version)) {
      const higher =
        !modelFloor || cmpVersion(v.min_vllm_version, modelFloor) > 0
          ? v.min_vllm_version
          : modelFloor;
      return { floor: higher, reason: `variant ${variant[1]} pin` };
    }
  }
  return {
    floor: modelFloor,
    reason: modelFloor
      ? "model.min_vllm_version"
      : declared
        ? `model.min_vllm_version is "${declared}" — tracks current vLLM, no floor`
        : "no min_vllm_version declared",
  };
}

function recipeFamily(doc) {
  const id = String(doc?.model?.model_id || "");
  const title = String(doc?.meta?.title || "");
  return [id.split("/").pop(), title].filter(Boolean).map((s) => s.toLowerCase());
}

function recipeHardware(doc) {
  const keys = new Set();
  for (const k of Object.keys(doc?.meta?.hardware || {})) keys.add(k.toLowerCase());
  for (const k of Object.keys(doc?.hardware_overrides || {})) keys.add(k.toLowerCase());
  return [...keys];
}

// ---------------------------------------------------------------------------
// scan
// ---------------------------------------------------------------------------

function tokensOnLine(line) {
  const found = [];
  for (const m of line.matchAll(FLAG_RE)) found.push({ kind: "flag", name: m[1] });
  for (const m of line.matchAll(ENV_RE)) found.push({ kind: "env", name: m[1] });
  return found;
}

/** `- "--moe-backend"` followed by `- "deep_gemm"` -> the flag's value. */
function valueAfter(lines, i) {
  const next = lines[i + 1];
  if (!next) return null;
  const m = next.match(/^\s*-\s*["']?([^"'#\s][^"'#]*?)["']?\s*$/);
  if (!m) return null;
  const value = m[1].trim();
  if (value.startsWith("-")) return null;
  return value;
}

function scanFile(file, upstream) {
  const text = readFileSync(file.path, "utf8");
  const lines = text.split("\n");
  const isYaml = file.path.endsWith(".yaml");
  const paths = isYaml ? pathsForLines(lines) : lines.map(() => "");
  let doc = null;
  if (isYaml) {
    try {
      doc = yaml.load(text);
    } catch {
      doc = null;
    }
  }
  const rel = relative(REPO, file.path);
  const out = [];

  lines.forEach((line, i) => {
    if (/^\s*#/.test(line)) return;
    for (const token of tokensOnLine(line)) {
      const path = paths[i] || "";
      // Tier A: a structured vLLM args/env block — every rule applies.
      // Tier B: guide prose, strategy YAML, synthesis source. Only tokens vLLM
      // has actually shipped at some tag are judged there; anything else is
      // another tool's flag, not evidence of staleness.
      const structured =
        isYaml &&
        (token.kind === "flag" ? ARG_PATH_RE.test(path) : ENV_PATH_RE.test(path));
      const known =
        token.kind === "flag" ? token.name in upstream.index.flags : token.name in upstream.index.envs;
      if (!structured && !known) continue;
      if (FOREIGN_FLAGS.has(token.name)) continue;
      const { floor, reason } = isYaml && doc ? effectiveFloor(doc, path) : {};
      const finding = classify(token, upstream, floor, valueAfter(lines, i), structured);
      if (!finding) continue;
      if (finding.category === "unknown-upstream" && (doc?.meta?.tasks || []).includes("omni")) {
        finding.plugin_hint = "vllm-omni";
      }
      out.push({
        file: rel,
        line: i + 1,
        editable: file.editable,
        path,
        snippet: line.trim().slice(0, 160),
        token: token.name,
        kind: token.kind,
        tier: structured ? "structured" : "prose",
        floor: floor || null,
        floor_reason: reason || null,
        ...finding,
      });
    }
  });
  return { rel, doc, candidates: out };
}

function editDistance(a, b) {
  const dp = Array.from({ length: a.length + 1 }, (_, i) => [i, ...Array(b.length).fill(0)]);
  for (let j = 0; j <= b.length; j += 1) dp[0][j] = j;
  for (let i = 1; i <= a.length; i += 1) {
    for (let j = 1; j <= b.length; j += 1) {
      dp[i][j] = Math.min(
        dp[i - 1][j] + 1,
        dp[i][j - 1] + 1,
        dp[i - 1][j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1)
      );
    }
  }
  return dp[a.length][b.length];
}

/**
 * A real flag whose hyphen segments are a subsequence of the unknown flag's.
 *
 * Edit distance is the wrong metric here: the one real typo this repo has had,
 * `--tool-call-parser-plugin` for `--tool-parser-plugin`, is 5 edits apart,
 * while 2-edit neighbours (`--usp` vs `--uds`) are unrelated flags. Requiring a
 * segment subsequence with at least two shared segments, near-equal length and
 * a matching first segment catches the inserted/dropped word and rejects the
 * coincidences — `--diffusion-attention-backend` is a vllm-omni flag, not a
 * misspelling of `--attention-backend`.
 */
function nearestFlag(name, flags) {
  const segments = name.replace(/^--/, "").split("-");
  let best = null;
  for (const candidate of Object.keys(flags)) {
    if (!candidate.startsWith("--")) continue;
    const other = candidate.replace(/^--/, "").split("-");
    if (other.length < 2 || Math.abs(other.length - segments.length) > 1) continue;
    if (other[0] !== segments[0]) continue;
    let i = 0;
    for (const seg of segments) if (i < other.length && other[i] === seg) i += 1;
    if (i === other.length && i >= 2) {
      if (!best || other.length > best.segments) {
        best = { name: candidate, segments: other.length };
      }
    }
  }
  return best;
}

function classify(token, upstream, floor, value, structured) {
  const { flags, envs, index, inventory, semantics, target } = upstream;
  // A recipe pinned above the tag we are syncing to is ahead of it, not stale:
  // its flags and accepted values belong to a release this run cannot see.
  const aheadOfTarget = floor && cmpVersion(floor, target) > 0;
  // `--compilation-config.pass_config.x` is the dotted form of a real flag.
  const base = token.name.includes(".") ? token.name.split(".")[0] : token.name;
  const lookup = token.kind === "flag" ? flags : envs;
  // argparse registers `--no-<name>` for every boolean flag, so
  // `--no-enable-prefix-caching` is `--enable-prefix-caching` negated.
  const negated = base.startsWith("--no-") ? `--${base.slice(5)}` : null;
  const present = token.name in lookup || base in lookup || (negated && negated in lookup);
  const history =
    (token.kind === "flag"
      ? index.flags[token.name] || index.flags[base] || (negated && index.flags[negated])
      : index.envs[token.name]) || null;

  if (!present) {
    if (aheadOfTarget) return null;
    if (!history) {
      // Never shipped by vLLM at any indexed tag. That is a typo only when a
      // real flag is one or two edits away; otherwise it most likely belongs to
      // a platform plugin (vllm-omni's --omni, vllm-ascend's env vars), which
      // this tool has no visibility into.
      const near = token.kind === "flag" ? nearestFlag(base, flags) : null;
      if (near) {
        return {
          category: "never-existed",
          severity: "high",
          why: `${token.name} is in no indexed release; ${near.name} is the same flag with a segment inserted or dropped`,
          suggestion: near.name,
        };
      }
      // `--cc.pass_config...` for `-cc.pass_config...`: the alias is registered
      // with one dash, and `--cc` is not a prefix abbreviation of
      // `--compilation-config`, so argparse rejects the whole argument.
      const shortAlias = base.startsWith("--") ? `-${base.slice(2)}` : null;
      if (shortAlias && shortAlias in flags) {
        const full = flags[shortAlias].alias_of;
        return {
          category: "wrong-dash",
          severity: "high",
          why: `${shortAlias} is registered with a single dash${full ? ` as the alias of ${full}` : ""}; \`${base}\` is not a prefix abbreviation of it, so this argument is rejected`,
          suggestion: shortAlias,
        };
      }
      return {
        category: "unknown-upstream",
        severity: "low",
        why: `${token.name} is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see`,
      };
    }
    return {
      category: "removed",
      severity: "high",
      why: `removed upstream in ${history.removed} (introduced ${history.introduced})`,
      introduced: history.introduced,
      removed: history.removed,
    };
  }

  if (!aheadOfTarget && history && floor && cmpVersion(history.introduced, floor) > 0) {
    return {
      category: "below-introducing-version",
      severity: "medium",
      why: `${token.name} was introduced in ${history.introduced}, above the pinned floor ${floor}`,
      introduced: history.introduced,
    };
  }

  const inv = inventory.items.filter(
    (it) =>
      (it.name === token.name || it.name === base) &&
      ["deprecated", "renamed", "default-changed"].includes(it.category)
  );
  if (inv.length) {
    const first = inv[0];
    return {
      category: first.category,
      severity: first.category === "renamed" ? "high" : "low",
      why: first.detail,
      inventory_id: first.id,
      replacement: first.replacement || null,
    };
  }

  if (value && token.kind === "flag" && structured && !aheadOfTarget) {
    const choices = semantics[token.name]?.choices || semantics[base]?.choices;
    if (Array.isArray(choices) && choices.length && !choices.includes(value)) {
      return {
        category: "invalid-value",
        severity: "high",
        why: `${token.name}=${value} is not among the accepted values at the target tag (${choices.join(", ")})`,
        value,
        choices,
      };
    }
  }
  return null;
}

// ---------------------------------------------------------------------------
// missed-improvement prefilter (deterministic join; the LLM decides)
// ---------------------------------------------------------------------------

function missedImprovements(recipes, inventory) {
  const narrative = inventory.items.filter(
    (i) =>
      ["new-feature", "perf-improvement"].includes(i.category) &&
      (i.models?.length || i.hardware?.length)
  );
  const out = [];
  for (const { rel, doc } of recipes) {
    if (!doc) continue;
    const family = recipeFamily(doc);
    const hardware = recipeHardware(doc);
    for (const item of narrative) {
      const modelHit = (item.models || []).filter((m) =>
        family.some((f) => f.includes(m.split(/[\s-]/)[0]) || m.includes(f.split(/[\s-]/)[0]))
      );
      if (!modelHit.length) continue;
      const hwHit = (item.hardware || []).filter((h) =>
        hardware.some((r) => r.includes(h) || h.includes(r))
      );
      out.push({
        file: rel,
        inventory_id: item.id,
        category: item.category,
        matched_models: modelHit,
        matched_hardware: hwHit,
        detail: item.detail,
        prs: (item.evidence?.prs || []).map((p) => p.pr),
      });
    }
  }
  return out;
}

// ---------------------------------------------------------------------------

function main() {
  const args = Object.fromEntries(
    process.argv.slice(2).reduce((acc, a, i, arr) => {
      if (a.startsWith("--")) acc.push([a.slice(2), arr[i + 1]?.startsWith("--") ? true : arr[i + 1]]);
      return acc;
    }, [])
  );
  const target = args.target;
  const reportDir = args["report-dir"];
  if (!target || !reportDir) {
    console.error("usage: scan.mjs --target <tag> --report-dir <dir>");
    process.exit(2);
  }

  const upstream = {
    target,
    flags: python("flagset.py", ["--tag", target, "--what", "flags", "--json"]).flags,
    envs: python("flagset.py", ["--tag", target, "--what", "envs", "--json"]).envs,
    index: python("index_flags.py", ["--target", target, "--json"]),
    semantics: python("inventory.py", ["--target", target, "--dump-semantics"]),
    inventory: JSON.parse(readFileSync(join(reportDir, "inventory.json"), "utf8")),
  };

  const recipes = [];
  const candidates = [];
  for (const file of targetFiles()) {
    const result = scanFile(file, upstream);
    if (file.editable) recipes.push(result);
    candidates.push(...result.candidates);
  }

  const missed = missedImprovements(recipes, upstream.inventory);
  mkdirSync(reportDir, { recursive: true });
  writeFileSync(
    join(reportDir, "candidates.json"),
    JSON.stringify(
      { target, generated: new Date().toISOString(), stale: candidates, missed },
      null,
      2
    )
  );

  const byCategory = {};
  for (const c of candidates) {
    const key = `${c.category}/${c.tier}`;
    byCategory[key] = (byCategory[key] || 0) + 1;
  }
  console.log(`scanned ${recipes.length} recipes + report-only scope against ${target}`);
  console.log(`  stale-usage candidates: ${candidates.length}`);
  for (const cat of Object.keys(byCategory).sort()) {
    console.log(`    ${cat.padEnd(26)} ${byCategory[cat]}`);
  }
  const nonEditable = candidates.filter((c) => !c.editable);
  console.log(`  in report-only scope: ${nonEditable.length}`);
  for (const c of nonEditable) console.log(`    ${c.file}:${c.line} ${c.token} (${c.category})`);
  console.log(`  missed-improvement prefilter: ${missed.length} recipe x item pairs`);
  console.log(`  -> ${join(reportDir, "candidates.json")}`);
}

main();
