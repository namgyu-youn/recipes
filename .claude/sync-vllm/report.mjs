#!/usr/bin/env node
/**
 * findings.json -> report.md + summary.md.
 *
 * Rendering is mechanical, so it is a script: the report's field set is fixed
 * and re-deriving it by hand each run would cost a lot and drift. Judgment —
 * which missed improvements are real, what a `needs decision` item should
 * become — stays with the orchestrator, which appends its sections and rewrites
 * `Status` lines after applying.
 */

import { readFileSync, writeFileSync, existsSync, readdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const REPORTS = join(HERE, "..", "..", ".claude_workdir", "reports");

const CATEGORY_LABEL = {
  "below-introducing-version": "flag used below the version that introduced it",
  removed: "removed upstream",
  renamed: "renamed upstream",
  deprecated: "deprecated upstream",
  "default-changed": "upstream default changed",
  "unknown-upstream": "not shipped by vLLM at any indexed tag",
  "invalid-value": "value not accepted at the target tag",
  "never-existed": "flag never existed upstream",
  "wrong-dash": "two dashes on a one-dash alias — argparse rejects it",
};

/** Previous run's findings, for carry-over marking. */
function previousFindings(target) {
  if (!existsSync(REPORTS)) return null;
  const key = (d) => d.replace("vllm-", "").split(".").map((p) => parseInt(p, 10) || 0);
  const cmp = (a, b) => {
    const [x, y] = [key(a), key(b)];
    for (let i = 0; i < 3; i += 1) if ((x[i] || 0) !== (y[i] || 0)) return (x[i] || 0) - (y[i] || 0);
    return 0;
  };
  const dirs = readdirSync(REPORTS)
    .filter((d) => /^vllm-\d/.test(d) && d !== `vllm-${target.replace(/^v/, "")}`)
    .filter((d) => existsSync(join(REPORTS, d, "findings.json")))
    .sort(cmp);
  const prev = dirs.filter((d) => cmp(d, `vllm-${target.replace(/^v/, "")}`) < 0).pop();
  if (!prev) return null;
  return { dir: prev, data: JSON.parse(readFileSync(join(REPORTS, prev, "findings.json"), "utf8")) };
}

function fingerprint(f) {
  return `${f.file}::${f.category}::${f.token}`;
}

function locationList(f) {
  return f.locations
    .map((l) => `\`${f.file}:${l.line}\`${l.path ? ` (\`${l.path}\`)` : ""}${l.tier === "prose" ? " — guide text" : ""}`)
    .join(", ");
}

function proposed(f) {
  if (f.action === "raise-floor") {
    return `raise \`${f.scope === "model" ? "model" : f.scope}.min_vllm_version\` from \`${f.floor}\` to \`${f.target_floor}\` (own commit)`;
  }
  if (f.action === "replace") return `replace \`${f.token}\` with \`${f.replacement}\``;
  if (f.action === "resolve") return `decide whether to drop \`${f.token}\` or re-spell it; upstream documents no replacement`;
  if (f.needed_floor) return `update the guide text (it shows flags needing ${f.needed_floor}, the recipe pins ${f.floor})`;
  return "report only — no mechanical edit";
}

function upstreamEvidence(f) {
  const bits = [];
  if (f.upstream.introduced) bits.push(`introduced ${f.upstream.introduced}`);
  if (f.upstream.removed) bits.push(`removed ${f.upstream.removed}`);
  if (f.upstream.cite?.file) {
    bits.push(
      `\`${f.upstream.cite.file}:${f.upstream.cite.line}\` @ ${f.upstream.cite.tag}` +
        (f.upstream.cite.ok ? "" : " (did not verify)")
    );
  }
  if (f.upstream.prs?.length) {
    bits.push(`PRs ${[...new Set(f.upstream.prs)].slice(0, 6).map((p) => `#${p}`).join(", ")}`);
  }
  bits.push(f.upstream.recheck);
  return bits.join("; ");
}

function renderFinding(f) {
  const tokens =
    f.tokens?.length > 1
      ? `\n| Tokens | ${f.tokens.map((t) => `\`${t.token}\` (needs ${t.introduced})`).join(", ")} |`
      : "";
  return `
### ${f.id} — \`${f.token}\` in \`${f.file.replace(/^models\//, "")}\`

| Field | Value |
|---|---|
| Type | ${f.type} |
| Category | ${f.category} — ${CATEGORY_LABEL[f.category] || ""} |
| Source | ${f.source} |
| Downstream location | ${locationList(f)} |
| Upstream evidence | ${upstreamEvidence(f)} |
| Current usage | \`${f.locations[0].snippet.replace(/\|/g, "\\|")}\` |
| Proposed change | ${proposed(f)} |
| Version floor | ${f.floor || "none"} — ${f.floor_reason} |${tokens}
| Confidence | ${f.confidence} — ${f.why.replace(/\|/g, "\\|")} |
| Risk | ${f.risk} |
| Status | ${f.status_final || f.status} |
`;
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
    console.error("usage: report.mjs --report-dir D [--prev-tag v0.28.0] [--branch sync/vllm-0.29.0] [--report-only]");
    process.exit(2);
  }
  const data = JSON.parse(readFileSync(join(reportDir, "findings.json"), "utf8"));
  const inventory = JSON.parse(readFileSync(join(reportDir, "inventory.json"), "utf8"));
  const { target } = data;
  const prev = previousFindings(target);
  const prevSeen = new Map((prev?.data.findings || []).map((f) => [fingerprint(f), f]));

  for (const f of data.findings) {
    const before = prevSeen.get(fingerprint(f));
    if (before && before.status === f.status) f.carried_over = before.id;
  }

  const counts = (key) =>
    data.findings.reduce((acc, f) => {
      // `status` is what verification proposed; `status_final` is what the
      // apply step actually did. Report the latter once it exists.
      const value = key === "status" ? f.status_final || f.status : f[key];
      acc[value] = (acc[value] || 0) + 1;
      return acc;
    }, {});
  const table = (obj) =>
    Object.entries(obj)
      .sort((a, b) => b[1] - a[1])
      .map(([k, v]) => `| ${k} | ${v} |`)
      .join("\n");

  const status = (f) => f.status_final || f.status;
  const applied = data.findings.filter((f) => status(f).startsWith("applied"));
  const eligible = data.findings.filter((f) => status(f) === "auto-apply-eligible");
  const decisions = data.findings.filter((f) => status(f) === "needs decision");
  const skipped = data.findings.filter((f) => status(f).startsWith("skipped"));
  const carried = data.findings.filter((f) => f.carried_over);

  const header = `# vLLM sync report — ${inventory.prev} → ${target}

Generated ${new Date().toISOString()}${args.branch ? ` on branch \`${args.branch}\`` : ""}${
    args["report-only"] ? " (report-only: nothing was edited or committed)" : ""
  }.

Upstream inventory: ${inventory.items.length} items from the release-notes pass and the source pass
(${Object.entries(inventory.counts).map(([k, v]) => `${k} ${v}`).join(", ")}).
Downstream: ${data.findings.length} verified findings, ${data.dropped.length} candidates dropped in verification.

| Status | Count |
|---|---|
${table(counts("status"))}

| Category | Count |
|---|---|
${table(counts("category"))}

| Confidence | Count |
|---|---|
${table(counts("confidence"))}
`;

  const sections = [
    ["Applied", applied],
    ["Auto-apply eligible", eligible],
    ["Needs decision", decisions],
    ["Skipped", skipped],
  ]
    .filter(([, list]) => list.length)
    .map(([title, list]) => `\n## ${title} (${list.length})\n${list.map(renderFinding).join("")}`)
    .join("\n");

  const missedNote = data.missed?.length
    ? `\n## Missed improvements — prefiltered candidates (${data.missed.length})\n\n` +
      "These are deterministic model/hardware joins between the release notes and the recipes.\n" +
      "They are NOT findings until the orchestrator confirms each one against upstream and\n" +
      "proposes a concrete edit; unconfirmed rows must not be applied.\n\n" +
      "| Recipe | Item | Models | Hardware | PRs |\n|---|---|---|---|---|\n" +
      data.missed
        .slice(0, 60)
        .map(
          (m) =>
            `| \`${m.file.replace(/^models\//, "")}\` | ${m.inventory_id} | ${m.matched_models.join(", ")} | ${
              m.matched_hardware.join(", ") || "—"
            } | ${m.prs.slice(0, 3).map((p) => `#${p}`).join(", ")} |`
        )
        .join("\n") +
      (data.missed.length > 60 ? `\n\n…and ${data.missed.length - 60} more in \`findings.json\`.\n` : "\n")
    : "";

  writeFileSync(join(reportDir, "report.md"), `${header}${sections}\n${missedNote}`);

  const summary = `# vLLM sync summary — ${inventory.prev} → ${target}

${args.branch ? `Branch: \`${args.branch}\`` : "Report-only run — no branch, no commits."}
${prev ? `Previous run compared: \`${prev.dir}\` (${carried.length} findings carried over unchanged).` : "No earlier run to compare against."}

| Status | Count |
|---|---|
${table(counts("status"))}

## Commits
${applied.length ? applied.map((f) => `- \`${f.commit || "?"}\` ${f.id} — ${f.subject || proposed(f)}`).join("\n") : "_none_"}

## Auto-apply eligible (${eligible.length})
${
  eligible
    .slice(0, 40)
    .map((f) => `- ${f.id} \`${f.file.replace(/^models\//, "")}\` — ${proposed(f)}`)
    .join("\n") || "_none_"
}${eligible.length > 40 ? `\n- …and ${eligible.length - 40} more in report.md` : ""}

## Needs human judgment (${decisions.length})
${
  decisions
    .slice(0, 40)
    .map((f) => `- ${f.id} \`${f.file.replace(/^models\//, "")}\` \`${f.token}\` — ${f.risk}`)
    .join("\n") || "_none_"
}${decisions.length > 40 ? `\n- …and ${decisions.length - 40} more in report.md` : ""}

## Skipped (${skipped.length})
${skipped.map((f) => `- ${f.id} — ${f.status_final}`).join("\n") || "_none_"}
`;
  writeFileSync(join(reportDir, "summary.md"), summary);

  console.log(`report.md + summary.md written to ${reportDir}`);
  console.log(`  findings ${data.findings.length}, carried over ${carried.length}, missed-improvement candidates ${data.missed?.length || 0}`);
}

main();
