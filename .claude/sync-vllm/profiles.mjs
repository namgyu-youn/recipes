#!/usr/bin/env node
/**
 * Recipe profiles and capability cohorts — both deterministic.
 *
 * A profile is what a recipe *is*, read straight out of its YAML: model family,
 * dense or MoE, which quantizations it ships, which hardware it claims, which
 * parallelism strategies and backends it already uses. A cohort is the set of
 * recipes a capability could apply to, obtained by matching
 * `capability.applies_to` against those profiles.
 *
 * Nothing here decides whether a capability *should* be adopted — that is the
 * one judgement step, made once per capability, not once per recipe. This just
 * bounds the question, and removes the recipes where the answer is already no:
 * those already using the flag, and those where the capability is on by default
 * and needs no edit at all.
 *
 * A capability with no hardware, model-trait or quant evidence produces no
 * cohort. An unbounded capability would otherwise "apply to" all 191 recipes,
 * which is the substring-join failure mode this replaced.
 */

import { readFileSync, writeFileSync, readdirSync, statSync } from "node:fs";
import { join, relative, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import yaml from "js-yaml";

const HERE = dirname(fileURLToPath(import.meta.url));
const REPO = join(HERE, "..", "..");

const BACKEND_FLAGS = ["--attention-backend", "--moe-backend", "--linear-backend"];

/**
 * A cohort wider than this is treated as unbounded rather than as an
 * opportunity. "Applies to every dense model" is not evidence that a capability
 * applies to a recipe; it means `applies_to` has not been narrowed yet, and a
 * cohort that size is the substring-join failure mode wearing a new name.
 */
const MAX_COHORT = 30;

function walk(dir, out = []) {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) walk(full, out);
    else if (full.endsWith(".yaml")) out.push(full);
  }
  return out;
}

function collect(node, fn, path = "") {
  if (Array.isArray(node)) node.forEach((v, i) => collect(v, fn, `${path}[${i}]`));
  else if (node && typeof node === "object") {
    for (const [k, v] of Object.entries(node)) collect(v, fn, path ? `${path}.${k}` : k);
  } else fn(node, path);
}

/** Every arg token and env name a recipe emits, with the block it sits in. */
function argsAndEnvs(doc) {
  const flags = new Map();
  const envs = new Map();
  const values = [];
  const visitArgs = (list, path) => {
    if (!Array.isArray(list)) return;
    list.forEach((item, i) => {
      if (typeof item !== "string") return;
      if (item.startsWith("-")) {
        const name = item.split("=")[0];
        if (!flags.has(name)) flags.set(name, path);
        const inline = item.includes("=") ? item.split("=").slice(1).join("=") : null;
        const next = inline ?? (typeof list[i + 1] === "string" && !list[i + 1].startsWith("-") ? list[i + 1] : null);
        if (next) values.push({ flag: name, value: next, path });
      }
    });
  };
  collect(doc, (value, path) => {
    if (/(^|\.)(base_env|extra_env|env)\.[A-Za-z_]\w*$/.test(path)) {
      envs.set(path.split(".").pop(), path);
    }
  });
  const visit = (node, path = "") => {
    if (!node || typeof node !== "object") return;
    for (const [k, v] of Object.entries(node)) {
      const next = path ? `${path}.${k}` : k;
      if (/^(base_args|extra_args|args)$/.test(k)) visitArgs(v, next);
      else visit(v, next);
    }
  };
  visit(doc);
  return { flags, envs, values };
}

function hardwareKeys(doc) {
  const keys = new Set();
  for (const k of Object.keys(doc?.meta?.hardware || {})) keys.add(k);
  for (const k of Object.keys(doc?.hardware_overrides || {})) keys.add(k);
  for (const variant of Object.values(doc?.variants || {})) {
    for (const k of Object.keys(variant?.hardware_overrides || {})) keys.add(k);
  }
  if (doc?.meta?.default_hardware) keys.add(doc.meta.default_hardware);
  return [...keys];
}

/** Hardware keys are a mix of profile ids, generations and brands — flatten. */
function hardwareTerms(keys, taxonomy) {
  const terms = new Set();
  for (const key of keys) {
    terms.add(key.toLowerCase());
    const profile = taxonomy.hardware_profiles?.[key];
    if (profile) {
      if (profile.generation) terms.add(String(profile.generation).toLowerCase());
      if (profile.brand) terms.add(String(profile.brand).toLowerCase());
    }
  }
  return [...terms];
}

function buildProfiles(taxonomy) {
  const profiles = [];
  for (const file of walk(join(REPO, "models"))) {
    const rel = relative(REPO, file);
    let doc;
    try {
      doc = yaml.load(readFileSync(file, "utf8"));
    } catch {
      continue;
    }
    if (!doc?.model) continue;
    const { flags, envs, values } = argsAndEnvs(doc);
    const keys = hardwareKeys(doc);
    const backends = {};
    for (const flag of BACKEND_FLAGS) {
      const used = values.filter((v) => v.flag === flag).map((v) => v.value);
      if (used.length) backends[flag] = [...new Set(used)];
    }
    profiles.push({
      file: rel,
      model_id: doc.model.model_id || null,
      family: String(doc.model.model_id || rel).split("/").pop().toLowerCase(),
      provider: doc.meta?.provider || null,
      architecture: doc.model.architecture || null,
      tasks: doc.meta?.tasks || [],
      precisions: [
        ...new Set(Object.values(doc.variants || {}).map((v) => v?.precision).filter(Boolean)),
      ],
      hardware_keys: keys,
      hardware_terms: hardwareTerms(keys, taxonomy),
      strategies: doc.compatible_strategies || [],
      features: Object.keys(doc.features || {}),
      backends_in_use: backends,
      flags_in_use: [...flags.keys()],
      envs_in_use: [...envs.keys()],
      min_vllm_version: doc.model.min_vllm_version || null,
      variant_floors: Object.fromEntries(
        Object.entries(doc.variants || {})
          .filter(([, v]) => v?.min_vllm_version)
          .map(([k, v]) => [k, v.min_vllm_version])
      ),
    });
  }
  return profiles;
}

// ---------------------------------------------------------------------------
// cohorts
// ---------------------------------------------------------------------------

function matchesHardware(cap, profile) {
  const want = (cap.applies_to?.hardware || []).map((h) => h.toLowerCase());
  if (!want.length) return { ok: true, why: "capability names no hardware" };
  const hit = want.filter((w) => profile.hardware_terms.includes(w));
  return { ok: hit.length > 0, why: hit.length ? `hardware ${hit.join(",")}` : "hardware mismatch" };
}

function matchesTraits(cap, profile) {
  const traits = cap.applies_to?.model_traits || {};
  if (traits.architecture && traits.architecture !== profile.architecture) {
    return { ok: false, why: `architecture ${profile.architecture} != ${traits.architecture}` };
  }
  if (traits.tasks?.length && !traits.tasks.some((t) => profile.tasks.includes(t))) {
    return { ok: false, why: "task mismatch" };
  }
  if (traits.features?.length && !traits.features.some((f) => profile.features.includes(f))) {
    return { ok: false, why: `recipe has no ${traits.features.join("/")} feature` };
  }
  return { ok: true, why: "traits match" };
}

function matchesQuant(cap, profile) {
  const want = cap.applies_to?.quant || [];
  if (!want.length) return { ok: true, why: "capability names no quantization" };
  const hit = want.filter((q) => profile.precisions.includes(q));
  return { ok: hit.length > 0, why: hit.length ? `quant ${hit.join(",")}` : "quant mismatch" };
}

function alreadyUsing(cap, profile) {
  const how = cap.how_enabled || {};
  for (const flag of how.flags || []) {
    if (profile.flags_in_use.includes(flag)) return `already passes ${flag}`;
  }
  for (const env of how.envs || []) {
    if (profile.envs_in_use.includes(env)) return `already sets ${env}`;
  }
  for (const entry of how.enum_values || []) {
    if ((profile.backends_in_use[entry.flag] || []).includes(entry.value)) {
      return `already uses ${entry.flag} ${entry.value}`;
    }
  }
  return null;
}

function buildCohorts(caps, profiles) {
  const out = [];
  for (const cap of caps) {
    const bounded =
      (cap.applies_to?.hardware || []).length ||
      Object.keys(cap.applies_to?.model_traits || {}).length ||
      (cap.applies_to?.quant || []).length;

    if (!bounded) {
      out.push({
        id: cap.id,
        title: cap.title,
        concept: cap.concept,
        confidence: cap.confidence,
        cohort: [],
        skipped: "no hardware, model-trait or quant evidence — cohort not computed",
      });
      continue;
    }
    if (cap.default_on && (cap.how_enabled?.mode || "auto") === "auto") {
      out.push({
        id: cap.id,
        title: cap.title,
        concept: cap.concept,
        confidence: cap.confidence,
        cohort: [],
        skipped: "on by default and needs no flag — nothing to edit",
      });
      continue;
    }

    const cohort = [];
    const excluded = [];
    for (const profile of profiles) {
      const checks = [matchesHardware(cap, profile), matchesTraits(cap, profile), matchesQuant(cap, profile)];
      const failed = checks.find((c) => !c.ok);
      if (failed) continue;
      const using = alreadyUsing(cap, profile);
      if (using) {
        excluded.push({ file: profile.file, reason: using });
        continue;
      }
      cohort.push({
        file: profile.file,
        why: checks.map((c) => c.why).join("; "),
        architecture: profile.architecture,
        precisions: profile.precisions,
        hardware_keys: profile.hardware_keys,
      });
    }
    const entry = {
      id: cap.id,
      title: cap.title,
      concept: cap.concept,
      effect: cap.effect,
      confidence: cap.confidence,
      how_enabled: cap.how_enabled,
      applies_to: cap.applies_to,
      evidence: cap.evidence,
      cohort,
      excluded_already_using: excluded,
    };
    if (cohort.length > MAX_COHORT) {
      entry.skipped = `cohort of ${cohort.length} recipes is too broad — narrow applies_to (hardware, quant or model traits) before judging adoption`;
      entry.cohort_sample = cohort.slice(0, 5).map((c) => c.file);
      entry.cohort = [];
    }
    out.push(entry);
  }
  return out;
}

// ---------------------------------------------------------------------------

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
    console.error("usage: profiles.mjs --report-dir D [--capabilities <file>]");
    process.exit(2);
  }
  const taxonomy = yaml.load(readFileSync(join(REPO, "taxonomy.yaml"), "utf8"));
  const profiles = buildProfiles(taxonomy);
  writeFileSync(join(reportDir, "profiles.json"), JSON.stringify({ profiles }, null, 2));

  const capPath = args.capabilities
    ? join(REPO, args.capabilities)
    : join(reportDir, "capabilities.verified.yaml");
  const caps = yaml.load(readFileSync(capPath, "utf8")).capabilities || [];
  const cohorts = buildCohorts(caps, profiles);
  writeFileSync(join(reportDir, "cohorts.json"), JSON.stringify({ cohorts }, null, 2));

  const sized = cohorts.filter((c) => c.cohort.length);
  console.log(`${profiles.length} recipe profiles; ${caps.length} capabilities`);
  console.log(`  capabilities with a cohort: ${sized.length}`);
  console.log(`  skipped (unbounded or default-on): ${cohorts.filter((c) => c.skipped).length}`);
  for (const c of sized.sort((a, b) => b.cohort.length - a.cohort.length)) {
    const excl = c.excluded_already_using.length ? `, ${c.excluded_already_using.length} already using` : "";
    console.log(`    ${c.id.slice(0, 46).padEnd(46)} ${String(c.cohort.length).padStart(3)} recipes${excl}`);
  }
  console.log(`  -> ${join(reportDir, "cohorts.json")}`);
}

main();
