#!/usr/bin/env node
/**
 * Verify the stale-usage scan and group it by root cause.
 *
 * One finding per (category, flag/env) across the whole repo — not per recipe.
 * `--language-model-only` used below its introducing tag in 17 recipes is one
 * root cause with 17 affected recipes, not 17 findings.
 *
 * Verification stays independent of the scan: every claim is re-asked of
 * upstream at the target tag and of the working tree, and anything that fails
 * is dropped.
 *
 * Two rules worth stating because they are judgement encoded once:
 *
 *   Plugin flags. A flag vLLM never shipped is not stale usage. vllm-omni,
 *   vllm-ascend and vendor images register their own flags, and this tool
 *   cannot see them. They collect in one bucket and are never called stale.
 *
 *   Optional blocks. A newer flag inside `features.*`, `hardware_overrides.*`
 *   or `strategy_overrides.*` does not make the recipe's baseline wrong — that
 *   block only runs when the user opts in or lands on that hardware. Raising
 *   `model.min_vllm_version` for it would overstate the requirement for
 *   everyone else, so it is reported as a per-block floor question instead.
 *   Only the unconditional command (model.base_args/base_env, and the default
 *   variant's extras) justifies raising the model floor; a non-default variant
 *   with its own pin raises that pin instead.
 */

import { execFileSync } from "node:child_process";
import { readFileSync, writeFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const REPO = join(HERE, "..", "..");
const CLONE = join(REPO, ".claude_workdir", "vllm");

/**
 * Where an unknown flag comes from, judged by the recipe context rather than
 * by how the flag is spelled.
 *
 * A name-based list is a guess that ages badly: it has to be extended for every
 * new plugin and it mislabels anything whose author did not use the expected
 * prefix. The recipe itself says more — an omni recipe's unknown flags come
 * from vllm-omni, a block pinned to a vendor image gets its flags from that
 * image, and a flag sharing a block with several other unknowns belongs to
 * whatever registered its neighbours.
 */
function classifyUnknown(members) {
  const ctx = members.find((m) => m.context)?.context || {};
  const images = [...new Set(members.map((m) => m.context?.image).filter(Boolean))];
  if (ctx.omni_recipe) {
    return { namespace: "vllm-omni", why: "recipe declares an omni task section" };
  }
  if (ctx.ascend_image) {
    return { namespace: "vllm-ascend", why: `block pins ${images[0]}` };
  }
  if (ctx.vendor_image) {
    return { namespace: "vendor-image", why: `block pins ${images[0]}` };
  }
  if (ctx.block_siblings) {
    return {
      namespace: "plugin-block",
      why: `shares a block with ${ctx.block_siblings} other unknown flag(s)`,
    };
  }
  return { namespace: "unclassified", why: "no plugin, vendor image or sibling context" };
}

function pythonRaw(script, args) {
  return execFileSync("python3", [join(HERE, script), ...args], { encoding: "utf8" }).trim();
}

function git(...args) {
  try {
    return execFileSync("git", ["-C", CLONE, ...args], { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 });
  } catch {
    return null;
  }
}

function python(script, args) {
  return JSON.parse(
    execFileSync("python3", [join(HERE, script), ...args], { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 })
  );
}

function cmpVersion(a, b) {
  const key = (v) => String(v || "").replace(/^v/, "").split(".").map((p) => parseInt(p, 10) || 0);
  const [x, y] = [key(a), key(b)];
  for (let i = 0; i < Math.max(x.length, y.length); i += 1) {
    if ((x[i] || 0) !== (y[i] || 0)) return (x[i] || 0) - (y[i] || 0);
  }
  return 0;
}

function upstreamCiteHolds(tag, file, line, symbol) {
  if (!file || !line) return { ok: false, reason: "no upstream file:line cited" };
  const blob = git("show", `${tag}:${file}`);
  if (blob === null) return { ok: false, reason: `${file} does not exist at ${tag}` };
  const lines = blob.split("\n");
  if (lines[line - 1] === undefined) return { ok: false, reason: `${file} has no line ${line} at ${tag}` };
  const needle = symbol.replace(/^--/, "").replace(/-/g, "[-_]");
  const window = lines.slice(Math.max(0, line - 3), line + 2).join("\n");
  if (new RegExp(needle, "i").test(window)) return { ok: true, text: lines[line - 1].trim().slice(0, 160) };
  return { ok: false, reason: `line ${line} of ${file} at ${tag} does not mention ${symbol}` };
}

function downstreamLineHolds(file, line, snippet) {
  let lines;
  try {
    lines = readFileSync(join(REPO, file), "utf8").split("\n");
  } catch {
    return false;
  }
  return (lines[line - 1] || "").trim().slice(0, 160) === snippet;
}

/**
 * Does this block run in the recipe's default command, or only on opt-in?
 *
 * `conditionality` is computed by scan.mjs, which has the parsed recipe and so
 * can tell a default-on feature from an opt-in one — the distinction that
 * decides whether the model floor is genuinely wrong.
 */
function blockKind(path, conditionality) {
  const scope =
    /^model\./.test(path) || /^variants\.default\./.test(path)
      ? "model"
      : path.match(/^variants\.([\w-]+)\./)
        ? `variants.${path.match(/^variants\.([\w-]+)\./)[1]}`
        : /^features\./.test(path)
          ? `feature ${path.split(".")[1]}`
          : /^hardware_overrides\./.test(path)
            ? "hardware override"
            : /^strategy_overrides\./.test(path)
              ? "strategy override"
              : /^guide/.test(path)
                ? "guide text"
                : path.split(".")[0] || "unknown";
  return { unconditional: conditionality === "unconditional", scope };
}

function main() {
  const args = Object.fromEntries(
    process.argv.slice(2).reduce((acc, a, i, arr) => {
      if (a.startsWith("--")) {
        const next = arr[i + 1];
        acc.push([a.slice(2), !next || next.startsWith("--") ? true : next]);
      }
      return acc;
    }, [])
  );
  const { target } = args;
  const reportDir = args["report-dir"];
  if (!target || !reportDir) {
    console.error("usage: verify.mjs --target <tag> --report-dir <dir>");
    process.exit(2);
  }

  const candidates = JSON.parse(readFileSync(join(reportDir, "candidates.json"), "utf8"));
  const inventory = JSON.parse(readFileSync(join(reportDir, "inventory.json"), "utf8"));
  const index = python("index_flags.py", ["--target", target, "--json"]);
  const flags = python("flagset.py", ["--tag", target, "--what", "flags", "--json"]).flags;
  const envs = python("flagset.py", ["--tag", target, "--what", "envs", "--json"]).envs;

  // 1. group by root cause
  // What upstream said to do instead, read at the last tag where each removed
  // flag still existed — so "no documented replacement" is a checked statement.
  const removedTokens = [
    ...new Set(
      candidates.stale
        .filter((c) => c.category === "removed" || c.category === "renamed")
        .map((c) => c.token)
    ),
  ];
  const resolutions = removedTokens.length
    ? python("inventory.py", ["--target", target, `--replacements=${removedTokens.join(",")}`])
    : {};

  const groups = new Map();
  for (const c of candidates.stale) {
    if (!downstreamLineHolds(c.file, c.line, c.snippet)) continue;
    const key = `${c.category}::${c.token}`;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(c);
  }

  // Unknown tokens split two ways, and the second way is answerable: a plain
  // VLLM_* or core-looking flag might simply be newer than any stable release.
  const newestRc = pythonRaw("flagset.py", ["--newest-rc"]);
  const ahead = {
    rc: newestRc
      ? {
          flags: python("flagset.py", ["--tag", newestRc, "--what", "flags", "--json"]).flags,
          envs: python("flagset.py", ["--tag", newestRc, "--what", "envs", "--json"]).envs,
        }
      : null,
    head: (() => {
      try {
        return {
          flags: python("flagset.py", ["--tag", "main", "--what", "flags", "--json"]).flags,
          envs: python("flagset.py", ["--tag", "main", "--what", "envs", "--json"]).envs,
        };
      } catch {
        return null;
      }
    })(),
  };

  const findings = [];
  const dropped = [];
  const plugin = new Map();
  const notYetReleased = new Map();

  for (const [key, members] of groups) {
    const first = members[0];
    const { category, token, kind } = first;

    if (category === "unknown-upstream") {
      const files = [...new Set(members.map((m) => m.file))];
      // First: is it simply newer than the target's stable release?
      const inRc = ahead.rc && (kind === "flag" ? token in ahead.rc.flags : token in ahead.rc.envs);
      const inHead = ahead.head && (kind === "flag" ? token in ahead.head.flags : token in ahead.head.envs);
      if (inRc || inHead) {
        notYetReleased.set(token, {
          token,
          kind,
          recipes: files,
          lines: members.length,
          where: inRc ? `present at ${newestRc}` : "present at main (HEAD of the clone)",
          note: `the recipe uses a flag newer than ${target} — not yet in a stable release`,
        });
      } else {
        plugin.set(token, {
          token,
          kind,
          recipes: files,
          lines: members.length,
          ...classifyUnknown(members),
        });
      }
      continue;
    }

    // 2. independent upstream re-check
    const base = token.split(".")[0];
    const history = kind === "flag" ? index.flags[token] || index.flags[base] : index.envs[token];
    const presentNow = kind === "flag" ? token in flags || base in flags : token in envs;
    let ok = true;
    let recheck = "";
    if (category === "removed" || category === "renamed") {
      ok = !presentNow && Boolean(history?.removed);
      recheck = ok ? `absent at ${target}; removed in ${history.removed}` : `re-check says ${token} is present at ${target}`;
    } else if (category === "below-introducing-version") {
      ok = presentNow && Boolean(history?.introduced);
      recheck = ok ? `introduced ${history.introduced}, present at ${target}` : `no introducing tag for ${token}`;
    } else if (category === "wrong-dash") {
      ok = !presentNow;
      recheck = `${token} is not a registered flag at ${target}`;
    } else if (category === "default-changed") {
      // A changed default only matters if the recipe leaves it to the default.
      const setsExplicitly = members.some((m) => m.tier === "structured");
      recheck = setsExplicitly
        ? "the recipe sets this flag explicitly, so the changed default does not reach it"
        : "the recipe relies on the default, which changed upstream";
      ok = true;
    } else {
      recheck = "no independent upstream re-check for this category";
    }
    if (!ok) {
      dropped.push({ key, reason: recheck });
      continue;
    }

    const inv = inventory.items.find((i) => i.name === token || i.name === base);
    let cite = null;
    if (inv?.evidence?.file) {
      const citeTag = inv.evidence.tag || target;
      cite = { tag: citeTag, file: inv.evidence.file, line: inv.evidence.line, ...upstreamCiteHolds(citeTag, inv.evidence.file, inv.evidence.line, token) };
    }

    // 3. per-recipe rollup
    const byFile = new Map();
    for (const m of members) {
      if (!byFile.has(m.file)) byFile.set(m.file, []);
      byFile.get(m.file).push(m);
    }
    const recipes = [];
    for (const [file, hits] of byFile) {
      const blocks = hits.map((h) => ({
        ...blockKind(h.path, h.conditionality),
        line: h.line,
        path: h.path,
        tier: h.tier,
        conditionality: h.conditionality,
      }));
      const unconditional = blocks.filter((b) => b.unconditional);
      const floor = hits.find((h) => h.floor)?.floor || null;
      let action = "report";
      let why = "";
      if (category === "below-introducing-version") {
        const variantScoped = blocks.find((b) => b.scope.startsWith("variants."));
        if (unconditional.length) {
          action = "raise-floor";
          why = `used in the unconditional command (${unconditional[0].path})`;
        } else if (variantScoped) {
          action = "raise-variant-floor";
          why = `used only in ${variantScoped.scope}, which carries its own pin`;
        } else {
          action = "per-block-floor-question";
          why = `used only in ${[...new Set(blocks.map((b) => b.scope))].join(", ")} — opt-in or hardware-conditional, so the model floor may be right as it is`;
        }
      } else if (category === "removed" || category === "renamed") {
        const replacement = resolutions[token]?.replacement || inv?.replacement || null;
        const belowRemoval = floor && history?.removed && cmpVersion(floor, history.removed) < 0;
        const resolution = resolutions[token] || {};
        action =
          replacement && !belowRemoval
            ? "replace"
            : resolution.resolution === "remove" && !belowRemoval
              ? "remove"
              : "resolve";
        why = replacement
          ? belowRemoval
            ? `pin ${floor} predates the removal in ${history.removed}`
            : `replace with ${replacement} — ${resolution.why || "documented upstream"}`
          : resolution.resolution === "remove"
            ? resolution.why
            : resolution.why || "no documented replacement";
      } else if (category === "wrong-dash") {
        action = "replace";
        why = first.why;
      }
      recipes.push({
        file,
        floor,
        blocks: blocks.map((b) => ({ line: b.line, path: b.path, scope: b.scope, tier: b.tier })),
        needed: history?.introduced || null,
        action,
        why,
      });
    }

    const eligible = recipes.filter(
      (r) =>
        r.action === "raise-floor" ||
        r.action === "raise-variant-floor" ||
        r.action === "remove" ||
        (r.action === "replace" && category !== "wrong-dash")
    );
    const confidence = category === "default-changed" ? "medium" : cite && !cite.ok ? "low" : "high";

    findings.push({
      id: `R-${String(findings.length + 1).padStart(2, "0")}`,
      category,
      token,
      kind,
      source: inv?.source || "source-only",
      upstream: {
        introduced: history?.introduced || null,
        removed: history?.removed || null,
        recheck,
        cite,
        prs: [...new Set((inv?.notes || []).flatMap((n) => n.prs.map((p) => p.pr)))].slice(0, 6),
      },
      recipe_count: recipes.length,
      line_count: members.length,
      recipes: recipes.sort((a, b) => a.file.localeCompare(b.file)),
      auto_apply_candidates: eligible.length,
      confidence,
      status: eligible.length ? "auto-apply-eligible" : "needs decision",
    });
  }

  findings.sort((a, b) => b.recipe_count - a.recipe_count);
  findings.forEach((f, i) => {
    f.id = `R-${String(i + 1).padStart(2, "0")}`;
  });

  const pluginBucket = [...plugin.values()].sort((a, b) => b.recipes.length - a.recipes.length);

  writeFileSync(
    join(reportDir, "findings.json"),
    JSON.stringify(
      {
        target,
        generated: new Date().toISOString(),
        findings,
        plugin_flags: pluginBucket,
        not_yet_released: [...notYetReleased.values()].sort((a, b) => b.recipes.length - a.recipes.length),
        resolutions,
        dropped,
      },
      null,
      2
    )
  );

  console.log(`root causes: ${findings.length} (from ${candidates.stale.length} scan hits)`);
  for (const f of findings) {
    const actions = [...new Set(f.recipes.map((r) => r.action))].join("/");
    console.log(`  ${f.id} ${f.category.padEnd(26)} ${f.token.padEnd(34)} ${String(f.recipe_count).padStart(3)} recipes  ${actions}`);
  }
  console.log(
    `plugin/vendor flags: ${pluginBucket.length} distinct across ${new Set(pluginBucket.flatMap((p) => p.recipes)).size} recipes`
  );
  console.log(`newer than ${target} (in ${newestRc} or main): ${notYetReleased.size}`);
  for (const n of notYetReleased.values()) {
    console.log(`    ${n.token.padEnd(36)} ${n.where} — ${n.recipes.length} recipes`);
  }
  console.log(`dropped in verification: ${dropped.length}`);
  console.log(`  -> ${join(reportDir, "findings.json")}`);
}

main();
