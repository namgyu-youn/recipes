#!/usr/bin/env node
/**
 * capabilities + cohorts + findings -> report.md (about two screens).
 *
 * Four sections, in the order a reader needs them: what shipped, what we could
 * adopt, what is broken or stale by root cause, and the flags this tool cannot
 * speak to. Per-recipe detail lives in findings.json and cohorts.json — the
 * report names counts and files, never 122 individual entries.
 */

import { readFileSync, writeFileSync, existsSync, readdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import yaml from "js-yaml";

const HERE = dirname(fileURLToPath(import.meta.url));
const REPORTS = join(HERE, "..", "..", ".claude_workdir", "reports");

const CATEGORY_WORD = {
  removed: "removed upstream",
  renamed: "renamed upstream",
  "below-introducing-version": "used below its introducing release",
  "default-changed": "upstream default changed",
  "wrong-dash": "wrong dash — argparse rejects it",
};

const ACTION_WORD = {
  "raise-floor": "raise model floor",
  "raise-variant-floor": "raise variant pin",
  "per-block-floor-question": "per-block floor question",
  replace: "replace",
  resolve: "decide: drop or re-spell",
  report: "report only",
};

function short(file) {
  return file.replace(/^models\//, "").replace(/\.yaml$/, "");
}

function previousRun(target) {
  if (!existsSync(REPORTS)) return null;
  const key = (d) => d.replace("vllm-", "").split(".").map((p) => parseInt(p, 10) || 0);
  const cmp = (a, b) => {
    const [x, y] = [key(a), key(b)];
    for (let i = 0; i < 3; i += 1) if ((x[i] || 0) !== (y[i] || 0)) return (x[i] || 0) - (y[i] || 0);
    return 0;
  };
  const self = `vllm-${target.replace(/^v/, "")}`;
  const dirs = readdirSync(REPORTS)
    .filter((d) => /^vllm-\d/.test(d) && d !== self && existsSync(join(REPORTS, d, "findings.json")))
    .sort(cmp)
    .filter((d) => cmp(d, self) < 0);
  const prev = dirs.pop();
  return prev ? { dir: prev, data: JSON.parse(readFileSync(join(REPORTS, prev, "findings.json"), "utf8")) } : null;
}

function enablement(how) {
  if (!how) return "—";
  const bits = [...(how.flags || []), ...(how.envs || [])];
  for (const e of how.enum_values || []) bits.push(`${e.flag} ${e.value}`);
  if (!bits.length) return how.mode === "auto" ? "no flag — automatic" : "—";
  return bits.map((b) => `\`${b}\``).join(" ");
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
  const reportDir = args["report-dir"];
  if (!reportDir) {
    console.error("usage: report.mjs --report-dir D [--branch B] [--report-only]");
    process.exit(2);
  }

  const findingsDoc = JSON.parse(readFileSync(join(reportDir, "findings.json"), "utf8"));
  const caps =
    yaml.load(readFileSync(join(reportDir, "capabilities.verified.yaml"), "utf8")).capabilities || [];
  const cohorts = JSON.parse(readFileSync(join(reportDir, "cohorts.json"), "utf8")).cohorts || [];
  const inventory = JSON.parse(readFileSync(join(reportDir, "inventory.json"), "utf8"));
  const { target, findings, plugin_flags: pluginFlags } = findingsDoc;

  const prev = previousRun(target);
  const prevKeys = new Set((prev?.data.findings || []).map((f) => `${f.category}::${f.token}`));
  for (const f of findings) f.carried_over = prevKeys.has(`${f.category}::${f.token}`);

  const actionable = cohorts.filter((c) => c.cohort?.length);
  const needNarrowing = cohorts.filter((c) => c.skipped?.startsWith("cohort of"));
  const noEdit = cohorts.filter((c) => c.skipped && !c.skipped.startsWith("cohort of"));

  const byConcept = new Map();
  for (const cap of caps) {
    if (!byConcept.has(cap.concept)) byConcept.set(cap.concept, []);
    byConcept.get(cap.concept).push(cap);
  }

  const capRows = [...byConcept.entries()]
    .sort((a, b) => b[1].length - a[1].length)
    .map(([concept, list]) =>
      list
        .map(
          (cap) =>
            `| ${concept} | ${cap.title.slice(0, 62)} | ${enablement(cap.how_enabled)} | ${cap.effect} | ${cap.confidence} |`
        )
        .join("\n")
    )
    .join("\n");

  const adoption = actionable.length
    ? actionable
        .map((c) => {
          const files = c.cohort.map((r) => short(r.file));
          const shown = files.slice(0, 8).join(", ");
          const more = files.length > 8 ? `, +${files.length - 8} more` : "";
          const already = c.excluded_already_using?.length
            ? ` (${c.excluded_already_using.length} recipes already use it)`
            : "";
          return `**${c.title}** — ${c.concept}, ${c.effect}, confidence ${c.confidence}
Enable with ${enablement(c.how_enabled)}. Cohort: ${c.cohort.length} recipes${already} — ${shown}${more}.
Evidence: ${(c.evidence?.section || "—")}${c.evidence?.prs?.length ? `, PRs ${c.evidence.prs.map((p) => `#${p}`).join(", ")}` : ""}.
Tier: **report-only until an edit template is written and reviewed.**`;
        })
        .join("\n\n")
    : "_None with a bounded cohort this release._";

  const staleRows = findings
    .map(
      (f) =>
        `| ${f.id} | \`${f.token}\` | ${CATEGORY_WORD[f.category] || f.category}${
          // "needs X" is the introducing tag, which only means something while
          // the flag still exists; for a removed flag the removal tag is the fact.
          f.upstream.removed
            ? ` (gone in ${f.upstream.removed})`
            : f.upstream.introduced
              ? ` (needs ${f.upstream.introduced})`
              : ""
        } | ${f.recipe_count} | ${[
          ...new Set(f.recipes.map((r) => ACTION_WORD[r.action] || r.action)),
        ].join(", ")} | ${f.confidence}${f.carried_over ? " · carried over" : ""} |`
    )
    .join("\n");

  const pluginTokens = pluginFlags.map((p) => p.token);
  const pluginRecipes = new Set(pluginFlags.flatMap((p) => p.recipes));

  const autoEligible = findings.filter((f) => f.status === "auto-apply-eligible");
  const perBlock = findings.filter((f) => f.recipes.some((r) => r.action === "per-block-floor-question"));

  const md = `# vLLM sync — ${inventory.prev} → ${target}

${args.branch ? `Branch \`${args.branch}\`. ` : ""}${
    args["report-only"] ? "Report-only: nothing was edited or committed. " : ""
  }${caps.length} capabilities shipped; ${findings.length} stale-usage root causes across the recipes;
${actionable.length} adoption opportunit${actionable.length === 1 ? "y" : "ies"} with a bounded cohort.

## What shipped

| Concept | Capability | How enabled | Effect | Confidence |
|---|---|---|---|---|
${capRows}

${noEdit.length ? `${noEdit.length} of these need no recipe edit (on by default, or no hardware/model evidence to bound them).` : ""}

## Adoption opportunities

${adoption}

${
  needNarrowing.length
    ? `\n${needNarrowing.length} further capabilities matched more than 30 recipes, which means \`applies_to\` is not narrow enough to be evidence: ${needNarrowing
        .map((c) => c.id)
        .slice(0, 6)
        .join(", ")}${needNarrowing.length > 6 ? ", …" : ""}. Narrow hardware/quant/traits in \`capabilities.yaml\` and re-run before judging these.`
    : ""
}

## Breaking & stale, by root cause

${findings.length} root causes. ${autoEligible.length} have at least one recipe where the edit is mechanical; ${perBlock.length} are per-block floor questions (a newer flag inside \`features.*\` or \`hardware_overrides.*\` does not make the recipe's baseline wrong).

| ID | Flag / env | What | Recipes | Action | Confidence |
|---|---|---|---|---|---|
${staleRows}

Per-recipe lines, blocks and floors: \`findings.json\`.

## Unverifiable plugin flags

${pluginTokens.length} flags/envs across ${pluginRecipes.size} recipes are not shipped by vLLM at any indexed tag and are almost certainly registered by a plugin or vendor image (vllm-omni, vllm-ascend, vendor builds). They are **not** stale usage and this tool cannot verify them: ${pluginTokens
    .slice(0, 12)
    .map((t) => `\`${t}\``)
    .join(", ")}${pluginTokens.length > 12 ? `, +${pluginTokens.length - 12} more` : ""}.
`;

  writeFileSync(join(reportDir, "report.md"), md);

  const summary = `# vLLM sync summary — ${inventory.prev} → ${target}

${args.branch ? `Branch: \`${args.branch}\`` : "Report-only run — no branch, no commits."}
${prev ? `Compared against \`${prev.dir}\`: ${findings.filter((f) => f.carried_over).length} root causes carried over.` : "No earlier run to compare against."}

- capabilities shipped: ${caps.length} (${actionable.length} with a bounded cohort, ${needNarrowing.length} need narrowing, ${noEdit.length} need no edit)
- stale-usage root causes: ${findings.length} across ${new Set(findings.flatMap((f) => f.recipes.map((r) => r.file))).size} recipes
- per-block floor questions: ${perBlock.length}
- unverifiable plugin flags: ${pluginTokens.length} across ${pluginRecipes.size} recipes
- commits: ${args.branch && !args["report-only"] ? "see report.md" : "none (report-only)"}
`;
  writeFileSync(join(reportDir, "summary.md"), summary);

  const lines = md.split("\n").length;
  console.log(`report.md (${lines} lines) + summary.md written to ${reportDir}`);
}

main();
