#!/usr/bin/env node
/**
 * Mechanically re-check every candidate, then decide what may be applied.
 *
 * Verification is deliberately independent of the scan: each claim is re-asked
 * of upstream at the target tag (does the cited file:line still contain the
 * symbol? is the flag really absent/present? is the introducing tag what we
 * said?) and of the working tree (is the cited downstream line still that
 * line?). Anything that fails is dropped; anything that cannot be checked
 * mechanically drops to `low` confidence rather than being asserted.
 *
 * Candidates are grouped into findings: one finding per (file, token,
 * category), and version-floor findings per (file, pin scope), because their
 * fix is a single `min_vllm_version` bump no matter how many lines triggered it.
 *
 * Output: findings.json (same fields as the report).
 *
 * NOTE ON `status`: this step only *proposes*. A proposal is
 * `auto-apply-eligible` only when the edit is mechanical — a removed flag with
 * a documented replacement, or a floor bump. A removed flag with no documented
 * replacement is `needs decision` even when the apply-rules table would allow
 * auto-apply on the version pin alone, because "delete it" and "replace it with
 * the new spelling" are different edits and upstream has not said which.
 */

import { execFileSync } from "node:child_process";
import { readFileSync, writeFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const REPO = join(HERE, "..", "..");
const CLONE = join(REPO, ".claude_workdir", "vllm");

function git(...args) {
  try {
    return execFileSync("git", ["-C", CLONE, ...args], {
      encoding: "utf8",
      maxBuffer: 64 * 1024 * 1024,
    });
  } catch {
    return null;
  }
}

function python(script, args) {
  return JSON.parse(
    execFileSync("python3", [join(HERE, script), ...args], {
      encoding: "utf8",
      maxBuffer: 64 * 1024 * 1024,
    })
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

// ---------------------------------------------------------------------------
// mechanical checks
// ---------------------------------------------------------------------------

/** The cited upstream file:line at `tag` still contains `symbol`. */
function upstreamCiteHolds(tag, file, line, symbol) {
  if (!file || !line) return { ok: false, reason: "no upstream file:line cited" };
  const blob = git("show", `${tag}:${file}`);
  if (blob === null) return { ok: false, reason: `${file} does not exist at ${tag}` };
  const lines = blob.split("\n");
  const text = lines[line - 1];
  if (text === undefined) return { ok: false, reason: `${file} has no line ${line} at ${tag}` };
  const needle = symbol.replace(/^--/, "").replace(/-/g, "[-_]");
  const window = lines.slice(Math.max(0, line - 3), line + 2).join("\n");
  if (new RegExp(needle, "i").test(window)) return { ok: true, text: text.trim().slice(0, 160) };
  return { ok: false, reason: `line ${line} of ${file} at ${tag} does not mention ${symbol}` };
}

/** The downstream line still reads the way the scan recorded it. */
function downstreamLineHolds(file, line, snippet) {
  let lines;
  try {
    lines = readFileSync(join(REPO, file), "utf8").split("\n");
  } catch {
    return { ok: false, reason: `${file} is gone` };
  }
  // scan.mjs stores the line truncated; compare the same way or a long guide
  // line is reported as "changed since the scan" on every run.
  const text = (lines[line - 1] || "").trim().slice(0, 160);
  if (text !== snippet) return { ok: false, reason: `${file}:${line} changed since the scan` };
  return { ok: true, text };
}

// ---------------------------------------------------------------------------
// grouping
// ---------------------------------------------------------------------------

function pinScope(path) {
  const variant = path.match(/^variants\.([\w-]+)\b/);
  return variant ? `variants.${variant[1]}` : "model";
}

function groupCandidates(stale) {
  const groups = new Map();
  for (const c of stale) {
    // Floor findings are split by tier as well as pin scope: a flag in
    // `extra_args` makes the recipe's own default command wrong at the pin,
    // while the same flag quoted in the guide is documentation to fix, not a
    // reason to raise the version the recipe claims to support.
    const key =
      c.category === "below-introducing-version"
        ? `${c.file}::floor::${pinScope(c.path)}::${c.tier}`
        : `${c.file}::${c.category}::${c.token}`;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(c);
  }
  return groups;
}

// ---------------------------------------------------------------------------
// decisions
// ---------------------------------------------------------------------------

const REPORT_ONLY = {
  "default-changed": "a changed upstream default is a behaviour question for the recipe author",
  "unknown-upstream": "not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see",
  "invalid-value": "the value may come from a plugin or a release newer than the target",
  "wrong-dash": "the flag is spelled with two dashes where only a one-dash alias is registered",
};

function decide(category, members, inventory, target) {
  const first = members[0];
  const floors = members.map((m) => m.floor);
  const floor = floors.find((f) => f) || null;
  const editable = members.every((m) => m.editable);
  const prose = members.every((m) => m.tier === "prose");

  if (REPORT_ONLY[category]) {
    const confident = category === "default-changed" || category === "wrong-dash";
    return {
      type: "stale-usage",
      action: category === "wrong-dash" ? "replace" : "report",
      replacement: category === "wrong-dash" ? first.suggestion : undefined,
      status: "needs decision",
      confidence: confident ? "high" : "low",
      risk: REPORT_ONLY[category],
    };
  }

  if (category === "below-introducing-version") {
    const needed = members
      .map((m) => m.introduced)
      .sort(cmpVersion)
      .pop();
    if (prose) {
      return {
        type: "stale-usage",
        action: "report",
        scope: pinScope(first.path),
        needed_floor: String(needed).replace(/^v/, ""),
        status: "needs decision",
        confidence: "high",
        risk: `the guide shows flags newer than the pinned floor ${floor}; the guide text is what needs updating, not necessarily the pin`,
      };
    }
    return {
      type: "stale-usage",
      action: "raise-floor",
      target_floor: String(needed).replace(/^v/, ""),
      scope: pinScope(first.path),
      status: editable ? "auto-apply-eligible" : "needs decision",
      confidence: "high",
      risk: `the default command is wrong at the pinned floor ${floor}; raising the pin changes the Install block's version`,
    };
  }

  if (category === "removed" || category === "renamed") {
    const inv = inventory.items.find(
      (i) => i.name === first.token && (i.replacement || i.notes?.length)
    );
    const replacement = inv?.replacement || null;
    const removedIn = first.removed;
    const belowRemoval = floor && cmpVersion(floor, removedIn) < 0;

    if (!replacement) {
      return {
        type: "stale-usage",
        action: "resolve",
        status: "needs decision",
        confidence: "high",
        risk:
          `${first.token} is gone at ${target}, but upstream documents no replacement — ` +
          `deleting it and re-spelling it are different edits`,
      };
    }
    if (belowRemoval) {
      return {
        type: "stale-usage",
        action: "replace",
        replacement,
        status: "needs decision",
        confidence: "high",
        risk: `the recipe supports ${floor}, below the removal in ${removedIn}; replacing would break it there`,
      };
    }
    return {
      type: "stale-usage",
      action: "replace",
      replacement,
      status: editable ? "auto-apply-eligible" : "needs decision",
      confidence: "high",
      risk: floor
        ? `pin ${floor} is at or above the removal in ${removedIn}`
        : `no min_vllm_version is declared, so this recipe tracks current vLLM — the edit is right there, ` +
          `but it may break the recipe on vLLM older than ${removedIn}`,
      caveat: floor ? null : "unpinned recipe: note the older-vLLM risk in the report",
    };
  }

  if (category === "deprecated") {
    return {
      type: "stale-usage",
      action: "report",
      status: "needs decision",
      confidence: "medium",
      risk: "deprecated but still accepted at the target tag; replace on the author's schedule",
    };
  }

  return {
    type: "stale-usage",
    action: "report",
    status: "needs decision",
    confidence: "low",
    risk: `unclassified (${category})`,
    ...(prose ? { note: "guide prose only" } : {}),
  };
}

// ---------------------------------------------------------------------------

function main() {
  const args = Object.fromEntries(
    process.argv.slice(2).reduce((acc, a, i, arr) => {
      if (a.startsWith("--")) acc.push([a.slice(2), arr[i + 1]?.startsWith("--") ? true : arr[i + 1]]);
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

  const findings = [];
  const dropped = [];
  let n = 0;

  for (const [key, members] of groupCandidates(candidates.stale)) {
    const first = members[0];
    const category = first.category;

    // 1. the downstream lines still read as scanned
    const live = members.filter((m) => downstreamLineHolds(m.file, m.line, m.snippet).ok);
    if (!live.length) {
      dropped.push({ key, reason: "every cited downstream line changed since the scan" });
      continue;
    }

    // 2. the upstream claim re-checked from scratch at the target tag
    const history =
      first.kind === "flag" ? index.flags[first.token] || index.flags[first.token.split(".")[0]] : index.envs[first.token];
    const presentNow =
      first.kind === "flag"
        ? first.token in flags || first.token.split(".")[0] in flags
        : first.token in envs;
    let upstreamOk = true;
    let upstreamWhy = "";
    if (category === "removed" || category === "renamed") {
      upstreamOk = !presentNow && Boolean(history?.removed);
      upstreamWhy = upstreamOk
        ? `absent from the flag set at ${target}; last present before ${history.removed}`
        : `re-check says ${first.token} is present at ${target}`;
    } else if (category === "below-introducing-version") {
      upstreamOk = presentNow && Boolean(history?.introduced);
      upstreamWhy = upstreamOk
        ? `introduced in ${history.introduced}, present at ${target}`
        : `re-check cannot confirm an introducing tag for ${first.token}`;
    } else if (category === "wrong-dash" || category === "unknown-upstream") {
      upstreamOk = !presentNow && !history;
      upstreamWhy = "absent from every indexed tag";
    } else {
      upstreamWhy = "no independent upstream re-check for this category";
    }
    if (!upstreamOk) {
      dropped.push({ key, reason: upstreamWhy });
      continue;
    }

    // 3. the cited upstream file:line, where the inventory gave one
    const inv = inventory.items.find((i) => i.name === first.token);
    let cite = null;
    if (inv?.evidence?.file) {
      const citeTag = inv.evidence.tag || target;
      const held = upstreamCiteHolds(citeTag, inv.evidence.file, inv.evidence.line, first.token);
      cite = { tag: citeTag, file: inv.evidence.file, line: inv.evidence.line, ...held };
    }

    const decision = decide(category, live, inventory, target);
    if (cite && cite.ok === false) {
      decision.confidence = "low";
      decision.status = "needs decision";
      decision.risk = `${decision.risk}; cited upstream location did not verify (${cite.reason})`;
    }

    n += 1;
    findings.push({
      id: `F-${String(n).padStart(2, "0")}`,
      category,
      source: inv?.source || "source-only",
      file: first.file,
      editable: first.editable,
      locations: live.map((m) => ({ line: m.line, path: m.path, snippet: m.snippet, tier: m.tier })),
      token: first.token,
      kind: first.kind,
      // A floor finding groups every token in one pin scope: the fix is a
      // single bump, but the report has to name each token that forced it.
      tokens: [...new Map(live.map((m) => [m.token, { token: m.token, introduced: m.introduced || null, kind: m.kind }])).values()],
      floor: first.floor,
      floor_reason: first.floor_reason,
      why: first.why,
      upstream: {
        recheck: upstreamWhy,
        introduced: history?.introduced || null,
        removed: history?.removed || null,
        cite,
        prs: (inv?.notes || []).flatMap((note) => note.prs.map((p) => p.pr)),
      },
      ...decision,
    });
  }

  findings.sort((a, b) => {
    const rank = { "auto-apply-eligible": 0, "needs decision": 1 };
    return (rank[a.status] ?? 2) - (rank[b.status] ?? 2) || a.file.localeCompare(b.file);
  });
  findings.forEach((f, i) => {
    f.id = `F-${String(i + 1).padStart(2, "0")}`;
  });

  writeFileSync(
    join(reportDir, "findings.json"),
    JSON.stringify(
      { target, generated: new Date().toISOString(), findings, dropped, missed: candidates.missed },
      null,
      2
    )
  );

  const byStatus = {};
  const byCategory = {};
  for (const f of findings) {
    byStatus[f.status] = (byStatus[f.status] || 0) + 1;
    byCategory[f.category] = (byCategory[f.category] || 0) + 1;
  }
  console.log(`verified ${findings.length} findings from ${candidates.stale.length} candidates`);
  for (const k of Object.keys(byCategory).sort()) console.log(`    ${k.padEnd(28)} ${byCategory[k]}`);
  console.log("  status:");
  for (const k of Object.keys(byStatus).sort()) console.log(`    ${k.padEnd(28)} ${byStatus[k]}`);
  console.log(`  dropped in verification: ${dropped.length}`);
  for (const d of dropped.slice(0, 5)) console.log(`    ${d.key} — ${d.reason}`);
  console.log(`  -> ${join(reportDir, "findings.json")}`);
}

main();
