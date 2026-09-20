#!/usr/bin/env node
/**
 * Edit -> build -> commit gate. One logical change per invocation.
 *
 * This script never edits a recipe: the edit is made with the normal editing
 * tools, so comments, key order and `guide: |` block scalars survive (a YAML
 * round-trip through js-yaml would destroy all three). What it does is decide
 * whether that edit may be committed.
 *
 *   snapshot   build the JSON API and record a hash of every generated file
 *   check      rebuild, then verify the edit's blast radius:
 *                - the build succeeded
 *                - no recipe other than the edited ones changed output at all
 *                - within the edited recipes, every changed JSON path matches
 *                  --expect-paths (when given); an unexpected key fails
 *   commit     check, then `git commit -s` the named files, or restore them
 *
 * Failure never leaves a half-applied edit: the touched files are restored with
 * `git checkout --` and the caller records the finding as skipped. History is
 * only ever appended to — no reset, no amend, no rebase.
 */

import { execFileSync, spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { readFileSync, writeFileSync, readdirSync, statSync, mkdirSync, existsSync } from "node:fs";
import { join, relative, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import yaml from "js-yaml";

const HERE = dirname(fileURLToPath(import.meta.url));
const REPO = join(HERE, "..", "..");
const PUBLIC = join(REPO, "public");
const BRANCH_PREFIX = "sync/vllm-";

function git(args, { check = true } = {}) {
  const r = spawnSync("git", ["-C", REPO, ...args], { encoding: "utf8" });
  if (check && r.status !== 0) {
    throw new Error(`git ${args.join(" ")} failed: ${(r.stderr || "").trim()}`);
  }
  return (r.stdout || "").trim();
}

function build() {
  const r = spawnSync("node", [join(REPO, "scripts", "build-recipes-api.mjs")], {
    cwd: REPO,
    encoding: "utf8",
  });
  return { ok: r.status === 0, output: `${r.stdout || ""}${r.stderr || ""}`.trim() };
}

/** The part of a failed build's output worth putting in the report. */
function buildError(output) {
  const lines = output.split("\n");
  const start = lines.findIndex((l) => /(Error|Exception|✗|failed)/i.test(l));
  const slice = start === -1 ? lines.slice(-12) : lines.slice(start, start + 12);
  return slice.join("\n").slice(0, 800);
}

function walk(dir, out = []) {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) walk(full, out);
    else if (full.endsWith(".json")) out.push(full);
  }
  return out;
}

function hashTree() {
  if (!existsSync(PUBLIC)) return {};
  const out = {};
  for (const file of walk(PUBLIC)) {
    out[relative(PUBLIC, file)] = createHash("sha1").update(readFileSync(file)).digest("hex");
  }
  return out;
}

/** public/ path prefix owned by a recipe: models/<org>/<repo>.yaml -> <org>/<repo> */
function recipePrefix(file) {
  const m = file.match(/^models\/(.+)\.yaml$/);
  return m ? m[1] : null;
}

/**
 * Every public/ prefix a recipe generates: its own page plus one per promoted
 * variant. A variant with its own `model_id` is published as a recipe in its
 * own right (Qwen2.5-VL-7B-Instruct-AWQ comes from the base recipe's variants),
 * so its JSON changing is the edit working, not collateral damage.
 */
function ownedPrefixes(file) {
  const base = recipePrefix(file);
  if (!base) return [];
  const prefixes = new Set([base]);
  try {
    const doc = yaml.load(readFileSync(join(REPO, file), "utf8"));
    for (const variant of Object.values(doc?.variants || {})) {
      if (variant?.model_id) prefixes.add(String(variant.model_id));
    }
  } catch {
    /* unparseable YAML fails the build check anyway */
  }
  return [...prefixes];
}

function jsonPaths(value, prefix = "") {
  const out = new Map();
  const visit = (node, path) => {
    if (node && typeof node === "object" && !Array.isArray(node)) {
      for (const [k, v] of Object.entries(node)) visit(v, `${path}/${k}`);
    } else if (Array.isArray(node)) {
      node.forEach((v, i) => visit(v, `${path}/${i}`));
    } else {
      out.set(path, node);
    }
  };
  visit(value, prefix);
  return out;
}

function changedPaths(beforeText, afterText) {
  const before = jsonPaths(JSON.parse(beforeText));
  const after = jsonPaths(JSON.parse(afterText));
  const changed = [];
  for (const [path, value] of after) {
    if (!before.has(path)) changed.push({ path, from: null, to: value });
    else if (JSON.stringify(before.get(path)) !== JSON.stringify(value)) {
      changed.push({ path, from: before.get(path), to: value });
    }
  }
  for (const [path, value] of before) {
    if (!after.has(path)) changed.push({ path, from: value, to: null });
  }
  return changed;
}

function globToRe(glob) {
  return new RegExp(
    `^${glob.replace(/[.+^${}()|[\]\\]/g, "\\$&").replace(/\*\*/g, "\u0000").replace(/\*/g, "[^/]*").replace(/\u0000/g, ".*")}$`
  );
}

// ---------------------------------------------------------------------------

/**
 * Copy every recipe's top-level JSON into the baseline directory.
 *
 * The path-level diff cannot read "before" out of public/, because a `check`
 * rebuilds it: a second check of the same edit would then diff the edit against
 * itself and find nothing. The baseline directory is the only stable "before".
 */
function saveRecipeJson(reportDir) {
  const dir = join(reportDir, "json-baseline");
  mkdirSync(dir, { recursive: true });
  for (const file of walk(PUBLIC)) {
    const rel = relative(PUBLIC, file);
    if (rel.split("/").length !== 2) continue; // <org>/<repo>.json only
    const dest = join(dir, rel);
    mkdirSync(dirname(dest), { recursive: true });
    writeFileSync(dest, readFileSync(file));
  }
}

function snapshot(reportDir) {
  const built = build();
  if (!built.ok) {
    console.error(`build failed before snapshot:\n${built.output}`);
    process.exit(1);
  }
  mkdirSync(reportDir, { recursive: true });
  const hashes = hashTree();
  writeFileSync(join(reportDir, "json-baseline.json"), JSON.stringify(hashes));
  saveRecipeJson(reportDir);
  console.log(`baseline: ${Object.keys(hashes).length} generated files`);
  return hashes;
}

function check(reportDir, files, expectPaths) {
  const baselinePath = join(reportDir, "json-baseline.json");
  if (!existsSync(baselinePath)) {
    return { ok: false, reason: "no baseline — run `commit.mjs snapshot` first" };
  }
  const baseline = JSON.parse(readFileSync(baselinePath, "utf8"));

  // "before" comes from the baseline directory, never from public/, which a
  // check has already rebuilt by the time we compare.
  const previous = new Map();
  for (const file of files) {
    for (const prefix of ownedPrefixes(file)) {
      const saved = join(reportDir, "json-baseline", `${prefix}.json`);
      if (existsSync(saved)) previous.set(`${prefix}.json`, readFileSync(saved, "utf8"));
    }
  }

  const built = build();
  if (!built.ok) {
    return { ok: false, reason: "build failed", detail: buildError(built.output) };
  }

  const after = hashTree();
  const owned = files.flatMap(ownedPrefixes);
  const isOwned = (rel) => owned.some((p) => rel === `${p}.json` || rel.startsWith(`${p}/`));

  const changedFiles = [];
  for (const [rel, hash] of Object.entries(after)) {
    if (baseline[rel] !== hash) changedFiles.push(rel);
  }
  for (const rel of Object.keys(baseline)) {
    if (!(rel in after)) changedFiles.push(rel);
  }

  const foreign = changedFiles.filter((rel) => !isOwned(rel));
  if (foreign.length) {
    return {
      ok: false,
      reason: `the edit changed generated output for ${foreign.length} file(s) outside the edited recipes`,
      detail: foreign.slice(0, 20).join("\n"),
    };
  }

  const paths = [];
  for (const [rel, text] of previous) {
    const now = join(PUBLIC, rel);
    if (!existsSync(now)) continue;
    paths.push(...changedPaths(text, readFileSync(now, "utf8")).map((c) => ({ file: rel, ...c })));
  }

  if (expectPaths.length) {
    const patterns = expectPaths.map(globToRe);
    const unexpected = paths.filter((c) => !patterns.some((re) => re.test(c.path)));
    if (unexpected.length) {
      return {
        ok: false,
        reason: `${unexpected.length} JSON key(s) changed that --expect-paths does not cover`,
        detail: unexpected
          .slice(0, 20)
          .map((c) => `${c.file}${c.path}: ${JSON.stringify(c.from)} -> ${JSON.stringify(c.to)}`)
          .join("\n"),
      };
    }
  }

  return {
    ok: true,
    build: built.output.split("\n").filter((l) => l.includes("JSON API")).join(" ") || built.output.slice(-160),
    changedFiles,
    paths,
  };
}

function restore(files) {
  git(["checkout", "--", ...files], { check: false });
}

function commit(reportDir, files, subject, finding, expectPaths) {
  const branch = git(["rev-parse", "--abbrev-ref", "HEAD"]);
  if (!branch.startsWith(BRANCH_PREFIX)) {
    console.error(`refusing to commit on "${branch}" — expected a ${BRANCH_PREFIX}* branch`);
    process.exit(2);
  }
  const staged = git(["diff", "--cached", "--name-only"]);
  if (staged) {
    console.error(`refusing to commit: the index already holds ${staged.split("\n").length} file(s)`);
    process.exit(2);
  }

  const result = check(reportDir, files, expectPaths);
  if (!result.ok) {
    restore(files);
    console.log(
      JSON.stringify(
        { finding, status: "skipped", reason: result.reason, detail: result.detail || null },
        null,
        2
      )
    );
    process.exit(1);
  }

  git(["add", "--", ...files]);
  git(["commit", "-s", "-m", subject]);
  const hash = git(["rev-parse", "--short", "HEAD"]);

  // the committed state becomes the baseline for the next finding
  writeFileSync(join(reportDir, "json-baseline.json"), JSON.stringify(hashTree()));
  saveRecipeJson(reportDir);

  console.log(
    JSON.stringify(
      {
        finding,
        status: "applied",
        commit: hash,
        subject,
        files,
        build: result.build,
        json_paths_changed: result.paths.map((p) => `${p.file}${p.path}`),
      },
      null,
      2
    )
  );
}

// ---------------------------------------------------------------------------

function parseArgs(argv) {
  const out = { _: [] };
  for (let i = 0; i < argv.length; i += 1) {
    const a = argv[i];
    if (a.startsWith("--")) {
      const next = argv[i + 1];
      out[a.slice(2)] = next && !next.startsWith("--") ? (i += 1, next) : true;
    } else out._.push(a);
  }
  return out;
}

const args = parseArgs(process.argv.slice(2));
const mode = args._[0];
const reportDir = args["report-dir"];
const files = String(args.files || "").split(",").filter(Boolean);
const expectPaths = String(args["expect-paths"] || "").split(",").filter(Boolean);

if (!mode || !reportDir) {
  console.error(
    "usage:\n" +
      "  commit.mjs snapshot --report-dir D\n" +
      "  commit.mjs check    --report-dir D --files a.yaml,b.yaml [--expect-paths '/model/min_vllm_version,...']\n" +
      "  commit.mjs commit   --report-dir D --files a.yaml --finding F-01 --subject '[Org] ...' [--expect-paths ...]"
  );
  process.exit(2);
}

if (mode === "snapshot") snapshot(reportDir);
else if (mode === "check") {
  const r = check(reportDir, files, expectPaths);
  console.log(JSON.stringify(r, null, 2));
  process.exit(r.ok ? 0 : 1);
} else if (mode === "commit") {
  if (!args.subject || !files.length) {
    console.error("commit needs --files and --subject");
    process.exit(2);
  }
  commit(reportDir, files, String(args.subject), args.finding || null, expectPaths);
} else {
  console.error(`unknown mode ${mode}`);
  process.exit(2);
}
