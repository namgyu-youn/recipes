#!/usr/bin/env node
/**
 * capabilities + cohorts + findings -> report.md (about two screens).
 *
 * Five sections, in the order a reader needs them: what shipped, what we could
 * adopt, what is broken or stale by root cause, which floors predate model support,
 * and the flags this tool cannot speak to. Per-recipe detail lives in the JSON — the
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
  "vendor-block-floor-question": "vendor-image block — cannot move a pin",
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

/**
 * How to turn it on, without repeating a flag twice. A flag that has a
 * documented value is shown as the pair; only a flag with no value is shown
 * bare.
 */
function enablement(how) {
  if (!how) return "—";
  const valued = new Set((how.enum_values || []).map((e) => e.flag));
  const bits = [
    ...(how.enum_values || []).map((e) => `${e.flag} ${e.value}`),
    ...(how.flags || []).filter((f) => !valued.has(f)),
    ...(how.envs || []),
  ];
  if (!bits.length) return how.mode === "auto" ? "no flag — automatic" : "—";
  return bits.map((b) => `\`${b}\``).join(", ");
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
  // Optional: only present once model_floors.py has run for this target.
  const floorsPath = join(reportDir, "model-floors.json");
  const modelFloors = existsSync(floorsPath) ? JSON.parse(readFileSync(floorsPath, "utf8")) : null;
  const { target, findings, plugin_flags: pluginFlags } = findingsDoc;

  // Between-release tracking. Three states matter to a reader coming back after
  // a release: what is new, what is unchanged (and can be skimmed), and what
  // disappeared — the last being the only evidence that earlier runs led
  // anywhere. The result is written back to findings.json, because a carry-over
  // marking that lives only in the rendered report cannot be acted on.
  const prev = previousRun(target);
  const key = (f) => `${f.category}::${f.token}`;
  const prevByKey = new Map((prev?.data.findings || []).map((f) => [key(f), f]));
  const currentKeys = new Set(findings.map(key));
  for (const f of findings) {
    const before = prevByKey.get(key(f));
    f.carried_over = Boolean(before);
    f.first_seen = before ? before.first_seen || prev.dir.replace("vllm-", "") : target.replace(/^v/, "");
  }
  const resolved = [...prevByKey.values()].filter((f) => !currentKeys.has(key(f)));
  const fresh = findings.filter((f) => !f.carried_over);
  if (prev) {
    findingsDoc.compared_against = prev.dir;
    findingsDoc.resolved_since_previous = resolved.map((f) => ({
      id: f.id,
      category: f.category,
      token: f.token,
      recipe_count: f.recipe_count,
    }));
    writeFileSync(join(reportDir, "findings.json"), JSON.stringify(findingsDoc, null, 2));
  }

  // A capability with no cohort but with reverse hits is still actionable —
  // the edit is subtractive (drop a now-default env, fix stale guide text).
  const actionable = cohorts.filter((c) => !c.skipped && (c.cohort?.length || c.reverse_hits?.length));
  const needNarrowing = cohorts.filter((c) => c.skipped?.startsWith("cohort of"));
  const noEdit = cohorts.filter((c) => c.skipped && !c.skipped.startsWith("cohort of"));

  // Removals and deprecations are breaking news, not shipped capabilities.
  const shipped = caps.filter((c) => (c.kind || "capability") === "capability");
  const breakingCaps = caps.filter((c) => c.kind === "breaking");
  const outOfScope = caps.filter((c) => c.kind === "out_of_scope");

  const byConcept = new Map();
  for (const cap of shipped) {
    if (!byConcept.has(cap.concept)) byConcept.set(cap.concept, []);
    byConcept.get(cap.concept).push(cap);
  }

  // Titles are never truncated: a cut title is the one thing a reader cannot
  // recover from the table.
  const capRows = [...byConcept.entries()]
    .sort((a, b) => b[1].length - a[1].length)
    .map(([concept, list]) =>
      list
        .map(
          (cap) =>
            `| ${concept} | ${cap.title} | ${enablement(cap.how_enabled)} | ${cap.effect} | ${cap.confidence} |`
        )
        .join("\n")
    )
    .join("\n");

  const adoption = actionable.length
    ? actionable
        .map((c) => {
          const lines = [`**${c.title}** — ${c.concept}, confidence ${c.confidence}`];
          if (c.cohort.length) {
            const files = c.cohort.map((r) => short(r.file));
            const shown = files.slice(0, 8).join(", ");
            const more = files.length > 8 ? `, +${files.length - 8} more` : "";
            const already = c.excluded_already_using?.length
              ? ` (${c.excluded_already_using.length} already using it, excluded)`
              : "";
            lines.push(
              `Add ${enablement(c.how_enabled)} to ${c.cohort.length} recipes${already}: ${shown}${more}.`
            );
            const conflicting = c.cohort.filter((r) => r.conflicts?.length);
            if (c.required_floor) {
              lines.push(
                `Required floor for this edit: **${c.required_floor}**${c.floor_note ? ` (${c.floor_note})` : ""}.` +
                  (c.install ? ` Install change: \`${c.install.command}\` — ${c.install.note}.` : "")
              );
            }
            if (c.evidence_sentence) lines.push(`Evidence: "${c.evidence_sentence}"`);
            if (conflicting.length) {
              lines.push(
                `⚠ ${conflicting.length} of them already set the same flag to a different value — ` +
                  `that is a backend swap with a behaviour change, not an addition: ${conflicting
                    .slice(0, 4)
                    .map((r) => `${short(r.file)} (${r.conflicts[0].flag} ${r.conflicts[0].current} → ${r.conflicts[0].proposed})`)
                    .join(", ")}${conflicting.length > 4 ? ", …" : ""}.`
              );
            }
          }
          const actionableHits = (c.reverse_hits || []).filter((h) => h.actionable !== false);
          const keepHits = (c.reverse_hits || []).filter((h) => h.actionable === false);
          if (actionableHits.length) {
            // Per row: what is set, to what value, and against which floor —
            // the three things that decide whether it is really redundant.
            lines.push("");
            lines.push("| Where | Name | Value | Recipe floor | Evidence | Verdict |");
            lines.push("|---|---|---|---|---|---|");
            for (const h of actionableHits.slice(0, 12)) {
              const where = h.line ? `${short(h.file)}:${h.line}` : short(h.file);
              const what = h.snippet ? `\`${h.snippet.replace(/\|/g, "\\|")}\`` : `\`${h.path || "env"}\``;
              lines.push(
                `| \`${where}\` | \`${h.name}\` | ${h.value ? `\`${h.value}\`` : "—"} | ${
                  h.floor || "unset"
                } | ${what} | ${h.kind.replace(/-/g, " ")} |`
              );
            }
            if (actionableHits.length > 12) lines.push(`| … | +${actionableHits.length - 12} more in cohorts.json | | | | |`);
            lines.push("");
            if (keepHits.length) {
              const explained = keepHits.filter((h) => h.kind === "guide-explains-why").length;
              if (explained) {
                lines.push(
                  `${explained} guide mention(s) explain why the setting is there (\"required for …\", ` +
                    `\"can be enabled if needed\") — documentation, not staleness.`
                );
              }
              lines.push(
                `${keepHits.length - explained} further recipe(s) set it below the ${c.since || "release"} floor, where it is still ` +
                  `load-bearing — keep: ${[...new Set(keepHits.map((h) => `${short(h.file)} (floor ${h.floor || "unset"})`))]
                    .slice(0, 6)
                    .join(", ")}.`
              );
            }
            if (c.caveat) lines.push(`⚠ ${c.caveat}`);
          }
          // For a default change, quote the sentence that states the default —
          // not whichever sentence happened to mention the dimension.
          const defaultQuote = String(c.evidence?.text || "")
            .split(/(?<=[.;])\s+/)
            .map((t) => t.replace(/\s+/g, " ").trim())
            .find((t) => /\bdefault\b/i.test(t));
          if (c.reverse_hits?.length && defaultQuote) {
            lines.push(`Upstream states the default: "${defaultQuote.slice(0, 240)}"`);
          }
          if (c.supporting_sentence) {
            lines.push(
              `Why it applies (${c.supporting_sentence.dimension}): "${c.supporting_sentence.sentence
                .replace(/\s+/g, " ")
                .trim()}"`
            );
          }
          lines.push(`Tier: **report-only — needs an edit template and review before applying.**`);
          return lines.join("\n");
        })
        .join("\n\n")
    : "_None with a bounded cohort this release._";

  // One policy entry, not one row per flag: every per-block floor question has
  // the same answer, and the list belongs in findings.json.
  const floorQuestions = findings.filter(
    (f) =>
      f.category === "below-introducing-version" &&
      f.recipes.every((r) => r.action === "per-block-floor-question")
  );
  const floorIds = new Set(floorQuestions.map((f) => f.id));
  const detailFor = (f) => {
    if (f.category === "invalid-value") {
      const r = f.recipes[0];
      return `${short(r.file)} sets \`${f.invalid_value || "?"}\`, not accepted at ${f.upstream.introduced ? "" : ""}the target tag${
        f.accepted_sample?.length ? ` (accepted: ${f.accepted_sample.slice(0, 4).join(", ")}, …)` : ""
      }`;
    }
    if (f.category === "default-changed") return f.upstream.recheck;
    return "";
  };
  const staleRows = findings
    .filter((f) => !floorIds.has(f.id))
    .map(
      (f) =>
        `| ${f.id} | \`${f.token}\` | ${CATEGORY_WORD[f.category] || f.category}${
          // "needs X" is the introducing tag, which only means something while
          // the flag still exists; for a removed flag the removal tag is the fact.
          f.upstream.removed
            ? ` (gone in ${f.upstream.removed})`
            : f.upstream.introduced && !["default-changed", "invalid-value"].includes(f.category)
              ? ` (needs ${f.upstream.introduced})`
              : ""
        }${detailFor(f) ? ` — ${detailFor(f)}` : ""} | ${f.recipe_count} | ${[
          ...new Set(f.recipes.map((r) => ACTION_WORD[r.action] || r.action)),
        ].join(", ")} | ${f.confidence}${f.carried_over ? " · carried over" : ""} |`
    )
    .join("\n");

  const namespaces = new Map();
  for (const p of pluginFlags) {
    if (!namespaces.has(p.namespace)) namespaces.set(p.namespace, []);
    namespaces.get(p.namespace).push(p);
  }
  const byNamespace = [...namespaces.entries()].sort((a, b) => b[1].length - a[1].length);
  const knownPlugin = pluginFlags.filter((p) => p.namespace !== "vendor-image");
  const vendor = pluginFlags.filter((p) => p.namespace === "vendor-image");
  const notYetReleased = findingsDoc.not_yet_released || [];
  // What upstream actually said, at the last tag where the flag existed.
  const resolutions = findingsDoc.resolutions || {};
  const removedEvidence = findings
    .filter((f) => ["removed", "renamed"].includes(f.category) && resolutions[f.token])
    .map((f) => {
      const r = resolutions[f.token];
      const verdict = r.replacement
        ? `replace with \`${r.replacement}\``
        : r.resolution === "remove"
          ? "drop it — upstream says so"
          : "no replacement documented";
      return `- \`${f.token}\` → ${verdict}. ${r.why}${r.quote ? `\n  > ${r.quote.replace(/\n/g, " ").slice(0, 200)}` : ""}`;
    })
    .join("\n");

  const pluginTokens = pluginFlags.map((p) => p.token);
  const pluginRecipes = new Set(pluginFlags.flatMap((p) => p.recipes));

  const autoEligible = findings.filter((f) => f.status === "auto-apply-eligible");
  const perBlock = findings.filter((f) => f.recipes.some((r) => r.action === "per-block-floor-question"));

  // Floors below the release that first registered the architecture. Recipes
  // whose serving path is a plugin or a pinned image are skipped upstream of
  // here by model_floors.py; the count is surfaced so the skip stays visible
  // rather than looking like clean coverage.
  const below = modelFloors?.floor_below_model_support || [];
  const pluginServed = modelFloors?.plugin_served_skipped || [];
  const modelFloorSection = !modelFloors
    ? ""
    : `## Model-support floors

${modelFloors.checked} checkpoints checked across the recipes that the in-tree wheel serves. ${below.length} pin a vLLM release older than the one that first registered their architecture, so the version the recipe claims to support cannot serve the model at all.

${
  below.length
    ? `| Recipe | Scope | Architecture | Pins | Needs | Guide line |\n|---|---|---|---|---|---|\n` +
      below
        .slice()
        .sort((a, b) => a.file.localeCompare(b.file))
        .map(
          (e) =>
            `| \`${short(e.file)}\` | ${e.scope} | ${e.architecture} | ${e.floor} | ${e.introduced} | ${
              e.guide_prerequisite ? `\`${e.guide_prerequisite}\` — update too` : "—"
            } |`
        )
        .join("\n")
    : "Nothing below its introducing release."
}

**${pluginServed.length} recipes were skipped, not cleared.** Their documented serving path is not the in-tree wheel — an omni recipe, a non-first-party image, a \`vllm==\` pin in the guide, or an architecture selected via \`--hf-overrides\` — so the plugin or image registers the architecture itself and \`registry.py\` says nothing about their floor. Raising one from the registry would contradict the recipe's own release-tested pin. Never auto-apply to these.${
  pluginServed.length
    ? `\n\n` +
      pluginServed
        .slice(0, 8)
        .map((e) => `- \`${short(e.file)}\` — ${e.why}`)
        .join("\n") +
      (pluginServed.length > 8 ? `\n- …${pluginServed.length - 8} more in \`model-floors.json\`.` : "")
    : ""
}

${modelFloors.no_floor_declared?.length || 0} recipes declare no floor at all and ${
        modelFloors.architecture_removed_upstream?.length || 0
      } use an architecture upstream has dropped. Per-recipe detail: \`model-floors.json\`.

`;

  const md = `# vLLM sync — ${inventory.prev} → ${target}

${args.branch ? `Branch \`${args.branch}\`. ` : ""}${
    args["report-only"] ? "Report-only: nothing was edited or committed. " : ""
  }${shipped.length} capabilities shipped (${breakingCaps.length} breaking changes are in section 3);
${findings.length} stale-usage root causes; ${actionable.length} adoption opportunit${
    actionable.length === 1 ? "y" : "ies"
  } with a bounded cohort.

${
  prev
    ? `**Since \`${prev.dir}\`:** ${fresh.length} new root cause${fresh.length === 1 ? "" : "s"}${
        fresh.length
          ? ` (${fresh.map((f) => `\`${f.token}\` ${f.category}`).join(", ")})`
          : ""
      }, ${findings.length - fresh.length} carried over unchanged, ${resolved.length} no longer reported${
        resolved.length
          ? ` (${resolved.map((f) => `\`${f.token}\` ${f.category}`).join(", ")})`
          : ""
      }. A finding can stop being reported because the recipe changed or because upstream did — the category says which to check.\n`
    : ""
}
## What shipped

| Concept | Capability | How enabled | Effect | Confidence |
|---|---|---|---|---|
${capRows}

${
    shipped.length - actionable.length > 0
      ? `${shipped.length - actionable.length} of these need no recipe edit: on by default with nothing to remove, or with no hardware/model dimension to bound a cohort.`
      : ""
  }

## Adoption opportunities

${adoption}

${
  needNarrowing.length
    ? `\n${needNarrowing.length} further capabilit${needNarrowing.length === 1 ? "y" : "ies"} matched more than 30 recipes, which means \`applies_to\` is not narrow enough to be evidence: ${needNarrowing
        .map((c) => c.title)
        .slice(0, 4)
        .join("; ")}${needNarrowing.length > 4 ? "; …" : ""}. Narrow hardware/quant/traits in \`capabilities.yaml\` and re-run before judging these.`
    : ""
}

## Breaking & stale, by root cause

${findings.length} root causes. ${autoEligible.length} have at least one recipe where the edit is mechanical; ${perBlock.length} are per-block floor questions (a newer flag inside \`features.*\` or \`hardware_overrides.*\` does not make the recipe's baseline wrong).

| ID | Flag / env | What | Recipes | Action | Confidence |
|---|---|---|---|---|---|
${staleRows}

${removedEvidence}
${
  breakingCaps.length
    ? `Also announced as breaking: ${breakingCaps.map((c) => c.title).join("; ")}.\n`
    : ""
}
**Per-block floor policy (${floorQuestions.length} flags, ${
    new Set(floorQuestions.flatMap((f) => f.recipes.map((r) => r.file))).size
  } recipes).** Each of these is a flag used below its introducing release, but only inside
\`features.*\` (opt-in), \`hardware_overrides.*\` or \`strategy_overrides.*\`. The recipe's
unconditional command is unaffected, so the model floor is not wrong — the question is whether the
block should carry its own floor. One decision covers all of them: ${floorQuestions
    .map((f) => `\`${f.token}\` (${f.recipe_count})`)
    .join(", ")}. Full list in \`findings.json\`.

Per-recipe lines, blocks and floors: \`findings.json\`.

${
  (findingsDoc.vendor_overlaps || []).length
    ? `## Vendor image overlapping upstream\n\n${findingsDoc.vendor_overlaps
        .map(
          (o) =>
            `**${o.id} — \`${o.image}\`** in ${o.recipes.map(short).join(", ")}. ${o.note || ""}\n\n` +
            `| Vendor env | Upstream equivalent |\n|---|---|\n` +
            Object.entries(o.mapping)
              .map(([k, v]) => `| \`${k}\` | ${v.startsWith("--") ? `\`${v}\`` : v} |`)
              .join("\n") +
            `\n\n${o.risk} **Report-only: the decision is whether to migrate off the image, and that needs GB10 validation.**`
        )
        .join("\n\n")}\n\n`
    : ""
}${modelFloorSection}## Unverifiable flags

Not stale usage — vLLM never shipped these, so this tool has nothing to check them against.

Each is classified by the recipe context it sits in — an omni task section, a pinned image, or the company its neighbours keep — not by how the name is spelled.

${byNamespace
    .map(
      ([ns, list]) =>
        `- **${ns}** (${list.length} flags across ${
          new Set(list.flatMap((p) => p.recipes)).size
        } recipes) — ${list[0].why}: ${list
          .slice(0, 8)
          .map((p) => `\`${p.token}\``)
          .join(", ")}${list.length > 8 ? `, +${list.length - 8} more` : ""}.`
    )
    .join("\n")}
${
  notYetReleased.length
    ? `- **Newer than ${target}** (${notYetReleased.length}) — present in the clone but not in a stable release yet, so the recipe is ahead of its pin: ${notYetReleased
        .map((n) => `\`${n.token}\` (${n.where}, ${n.recipes.length} recipe${n.recipes.length === 1 ? "" : "s"})`)
        .join(", ")}.`
    : ""
}
${outOfScope.length ? `\n${outOfScope.length} release items were out of the capability vocabulary (new model support, packaging) and are recorded in \`capabilities.yaml\` rather than shown above.` : ""}
`;

  writeFileSync(join(reportDir, "report.md"), md);

  const summary = `# vLLM sync summary — ${inventory.prev} → ${target}

${args.branch ? `Branch: \`${args.branch}\`` : "Report-only run — no branch, no commits."}
${prev ? `Compared against \`${prev.dir}\`: ${findings.filter((f) => f.carried_over).length} root causes carried over.` : "No earlier run to compare against."}

- capabilities shipped: ${shipped.length} — ${actionable.length} actionable, ${needNarrowing.length} need a narrower \`applies_to\`, ${Math.max(0, shipped.length - actionable.length - needNarrowing.length)} need no recipe edit
- breaking changes announced: ${breakingCaps.length}
- stale-usage root causes: ${findings.length} across ${new Set(findings.flatMap((f) => f.recipes.map((r) => r.file))).size} recipes
- per-block floor questions: ${perBlock.length}
- unverifiable flags: ${knownPlugin.length} plugin-namespace, ${vendor.length} vendor/out-of-tree, ${notYetReleased.length} newer than ${target}
- commits: ${args.branch && !args["report-only"] ? "see report.md" : "none (report-only)"}
`;
  writeFileSync(join(reportDir, "summary.md"), summary);

  const lines = md.split("\n").length;
  console.log(`report.md (${lines} lines) + summary.md written to ${reportDir}`);
}

main();
