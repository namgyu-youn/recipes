#!/usr/bin/env node
/**
 * Golden fixtures: findings a run must reproduce, and ones it must not invent.
 *
 * Every entry in golden.json is a case that was confirmed by hand — the manual
 * staleness audit, or a regression caught in review. Two of them went missing
 * between runs (a guide finding lost to a fences-only rule, and one masked by a
 * report generated on the wrong branch), which is exactly the failure this
 * guards: a scan that silently stops finding things looks identical to a clean
 * repo.
 *
 * Exit code 1 on any miss, so it can gate the pipeline.
 */

import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));

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
    console.error("usage: golden.mjs --report-dir D");
    process.exit(2);
  }

  const golden = JSON.parse(readFileSync(join(HERE, "golden.json"), "utf8"));
  const doc = JSON.parse(readFileSync(join(reportDir, "findings.json"), "utf8"));
  if (doc.target !== golden.target) {
    console.log(`golden fixtures are for ${golden.target}, this run targets ${doc.target} — skipped`);
    return;
  }

  const has = (token, file) =>
    doc.findings.some((f) => f.token === token && f.recipes.some((r) => r.file === file));

  const misses = golden.expected.filter((e) => !has(e.token, e.file));
  const invented = (golden.expected_absent || []).filter((e) => has(e.token, e.file));

  for (const e of golden.expected) {
    const ok = has(e.token, e.file);
    console.log(`  ${ok ? "✓" : "✗"} ${e.token.padEnd(38)} ${e.file.replace(/^models\//, "")}`);
    if (!ok) console.log(`      expected because: ${e.source}`);
  }
  for (const e of invented) {
    console.log(`  ✗ UNEXPECTED ${e.token} in ${e.file} — ${e.why}`);
  }

  if (misses.length || invented.length) {
    console.error(
      `\nGOLDEN FIXTURES FAILED: ${misses.length} expected finding(s) missing, ` +
        `${invented.length} known-false finding(s) reported. The scan regressed — do not trust this report.`
    );
    process.exit(1);
  }
  console.log(`\ngolden fixtures: ${golden.expected.length} present, ${(golden.expected_absent || []).length} correctly absent`);
}

main();
