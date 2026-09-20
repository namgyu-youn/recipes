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

/** Raw env assignments with their values, so "set to the new default" is visible. */
function envAssignments(doc) {
  const out = {};
  const visit = (node, path = "") => {
    if (!node || typeof node !== "object") return;
    for (const [k, v] of Object.entries(node)) {
      const next = path ? `${path}.${k}` : k;
      if (/^(base_env|extra_env|env)$/.test(k) && v && typeof v === "object") {
        for (const [name, value] of Object.entries(v)) out[name] = { value: String(value), path: next };
      } else visit(v, next);
    }
  };
  visit(doc);
  return out;
}

// Guide text that deliberately explains why a setting is there is not stale:
// "required for DSpark", "can be enabled if needed".
const GUIDE_INTENTIONAL_RE = /\brequired\b|\bif needed\b|can be enabled|\bonly if\b|\bnote:/i;

const GUIDE_NEGATION_RE =
  /\bno longer\b|\bnot needed\b|\bno\s+`|\bdon'?t\b|\bdo not\b|\bdeprecat\w*\b|\bremoved\b|\binstead of\b|\bis not\b|\bisn'?t\b|\bnever\b|\bavoid\b|\bunsupported\b/i;

/**
 * Guide lines that show a command, with their real line number in the file.
 *
 * Same rule as scan.mjs: fenced lines always, inline-code lines unless the
 * sentence negates them. The line number matters because a reader has to be
 * able to open the guide at that point and see the snippet.
 */
function guideCommandLines(filePath) {
  const lines = readFileSync(filePath, "utf8").split("\n");
  const start = lines.findIndex((l) => /^guide:\s*[|>]/.test(l));
  if (start === -1) return [];
  const out = [];
  let open = false;
  for (let i = start + 1; i < lines.length; i += 1) {
    const line = lines[i];
    if (line.trim() && !/^\s/.test(line)) break; // dedented out of the block
    if (/^\s*```/.test(line)) {
      open = !open;
      continue;
    }
    if (open || (/`[^`]*`/.test(line) && !GUIDE_NEGATION_RE.test(line))) {
      out.push({ line: i + 1, text: line.trim() });
    }
  }
  return out;
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
      flag_values: values,
      envs_in_use: [...envs.keys()],
      env_assignments: envAssignments(doc),
      guide_commands: guideCommandLines(file),
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
  // An omni recipe serves through vllm-omni, whose flag surface and defaults
  // are its own. A core vLLM capability does not automatically reach it, so it
  // stays out unless the capability's evidence actually mentions omni.
  const omniRecipe = (profile.tasks || []).includes("omni");
  if (omniRecipe && !/\bomni\b|diffusion/i.test(String(cap.evidence?.text || ""))) {
    return { ok: false, why: "omni recipe — core-flag evidence does not cover vllm-omni" };
  }
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

/**
 * Is this recipe already using the capability?
 *
 * When the capability names a value, the value is what counts: a recipe passing
 * `--moe-backend deep_gemm` is NOT already using `--moe-backend b12x`, and
 * treating it as such empties the cohort of exactly the recipes that could
 * adopt it. Only a flag with no documented value falls back to flag presence.
 */
function alreadyUsing(cap, profile) {
  const how = cap.how_enabled || {};
  const valued = new Set((how.enum_values || []).map((e) => e.flag));
  for (const entry of how.enum_values || []) {
    const used = (profile.flag_values || []).filter((v) => v.flag === entry.flag).map((v) => v.value);
    if (used.includes(entry.value)) return `already passes ${entry.flag} ${entry.value}`;
  }
  for (const flag of how.flags || []) {
    if (valued.has(flag)) continue; // judged by value above
    if (profile.flags_in_use.includes(flag)) return `already passes ${flag}`;
  }
  for (const env of how.envs || []) {
    if (profile.envs_in_use.includes(env)) return `already sets ${env}`;
  }
  return null;
}

/**
 * For a capability that needs no flag, the edit is subtractive: a recipe that
 * pins what is now the default, keeps a workaround the release retires, or has
 * guide text describing the old behaviour. Without one of these there is
 * nothing to do, and the capability is not an adoption opportunity at all.
 */
function cmpVersion(a, b) {
  const key = (v) => String(v || "").replace(/^v/, "").split(".").map((x) => parseInt(x, 10) || 0);
  const [x, y] = [key(a), key(b)];
  for (let i = 0; i < Math.max(x.length, y.length); i += 1) {
    if ((x[i] || 0) !== (y[i] || 0)) return (x[i] || 0) - (y[i] || 0);
  }
  return 0;
}

const OPT_IN_VALUES = new Set(["1", "true", "on", "yes"]);
const OPT_OUT_VALUES = new Set(["0", "false", "off", "no"]);

function reverseHits(cap, profile) {
  const markers = cap.reverse_markers || {};
  const hits = [];
  const floor = profile.min_vllm_version || null;
  // Setting a value is only *redundant* once the recipe's own floor is at or
  // above the release that made it the default. Below that floor the recipe
  // still supports versions where the setting does something, so it stays.
  const floorCovers = floor && cmpVersion(floor, cap.since || "") >= 0;

  for (const name of markers.now_default || []) {
    const assigned = profile.env_assignments?.[name];
    if (assigned) {
      const value = String(assigned.value).toLowerCase();
      // "0" turns the new default OFF. That is a deliberate workaround, not a
      // redundant restatement, and deleting it would change behaviour.
      if (OPT_OUT_VALUES.has(value)) {
        hits.push({
          file: profile.file,
          kind: "explicit-opt-out",
          name,
          value: assigned.value,
          floor,
          detail: `${name}=${assigned.value} in ${assigned.path} opts OUT of the new default — keep unless the reason is gone`,
        });
        continue;
      }
      if (!OPT_IN_VALUES.has(value)) continue;
      if (!floorCovers) {
        // Not actionable: at this floor the env still does something, so
        // removing it would change behaviour on the versions the recipe claims.
        hits.push({
          file: profile.file,
          kind: "keep-below-floor",
          actionable: false,
          name,
          value: assigned.value,
          floor,
          detail: `${name}=${assigned.value} in ${assigned.path}; default only since ${cap.since}, recipe floor is ${floor || "unset"} — keep`,
        });
        continue;
      }
      hits.push({
        file: profile.file,
        kind: "redundant-explicit",
        actionable: true,
        name,
        value: assigned.value,
        floor,
        path: assigned.path,
        detail: `${name}=${assigned.value} in ${assigned.path}; default since ${cap.since}, recipe floor ${floor} — redundant`,
      });
    } else if (profile.flags_in_use.includes(name) && floorCovers) {
      hits.push({
        file: profile.file,
        kind: "redundant-explicit",
        name,
        floor,
        detail: `passes ${name}; default since ${cap.since}, recipe floor ${floor} — redundant`,
      });
    }
  }
  for (const name of markers.obsolete || []) {
    const assigned = profile.env_assignments?.[name];
    if (assigned) {
      hits.push({
        file: profile.file,
        kind: "obsolete-workaround",
        name,
        value: assigned.value,
        floor,
        replacement: (cap.supersedes || {})[name] || null,
        detail: `${name}=${assigned.value} in ${assigned.path} — superseded${
          (cap.supersedes || {})[name] ? ` by ${cap.supersedes[name]}` : ""
        }`,
      });
    }
  }
  for (const name of [...(markers.now_default || []), ...(markers.obsolete || [])]) {
    for (const hit of profile.guide_commands || []) {
      if (!hit.text.includes(name)) continue;
      const value = (hit.text.match(new RegExp(`${name}\\s*=\\s*["']?([\\w.-]+)`)) || [])[1] || null;
      const intentional = GUIDE_INTENTIONAL_RE.test(hit.text);
      hits.push({
        file: profile.file,
        kind: intentional ? "guide-explains-why" : "stale-guide-text",
        actionable: Boolean(floorCovers) && !intentional,
        name,
        value,
        floor,
        line: hit.line,
        snippet: hit.text.slice(0, 120),
        detail: `guide shows ${name} at line ${hit.line}`,
      });
    }
  }
  // One recipe can set the same name in several blocks; that is one edit.
  const seen = new Set();
  return hits.filter((h) => {
    const key = `${h.file}::${h.kind}::${h.name}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

/**
 * A dimension is evidence only if it is specific and the release actually says
 * so. Brand alone ("nvidia") is a wildcard — it covers most of the catalogue —
 * and a dimension nothing in the text supports is a keyword coincidence.
 */
const WILDCARD_HARDWARE = new Set(["nvidia", "amd", "cuda"]);

/**
 * How a dimension is spelled in a release note. The recipes call it
 * `spec_decoding`; the notes say "speculative decoding". Matching the literal
 * token would reject the sentence that supports the dimension.
 */
const DIMENSION_SYNONYMS = {
  spec_decoding: /specul|eagle|\bmtp\b|dspark|dflash/i,
  moe: /\bmoe\b|mixture[- ]of[- ]experts|expert/i,
  dense: /\bdense\b/i,
  long_context: /long context|rope|yarn/i,
  multimodal: /multimodal|vision|\bvl\b|image|video|audio/i,
  tool_calling: /tool[- ]call/i,
  reasoning: /reasoning/i,
  dgx_spark_gb10: /dgx spark|gb10|sm121/i,
  rtx_pro_6000: /rtx pro 6000|sm120/i,
  rtx_pro_5000: /rtx pro 5000|sm120/i,
  rtx_5090: /rtx 5090|sm120/i,
};

function supportingSentence(cap) {
  const text = String(cap.evidence?.text || "");
  const sentences = text.split(/(?<=[.;])\s+/);
  const dimensions = [
    ...(cap.applies_to?.hardware || []).filter((h) => !WILDCARD_HARDWARE.has(h.toLowerCase())),
    ...(cap.applies_to?.quant || []),
    cap.applies_to?.model_traits?.architecture,
    ...(cap.applies_to?.model_traits?.features || []),
  ].filter(Boolean);
  const clean = (t) => t.replace(/\s+/g, " ").trim();
  for (const dimension of dimensions) {
    const re =
      DIMENSION_SYNONYMS[dimension] ||
      new RegExp(`\\b${dimension.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}`, "i");
    const hit = sentences.find((s) => re.test(s));
    if (hit) return { dimension, sentence: clean(hit).slice(0, 240) };
  }
  return null;
}

/**
 * A capability can enable more than one thing, and the parts do not share a
 * cohort. b12x is the case in point: the linear backend applies to any
 * supported quantization, the MoE backend only to MoE models, and the FP4
 * activation knob only to NVFP4 checkpoints. Folding them into one flag list
 * would propose `--moe-backend b12x` for dense models.
 */
function expandParts(caps) {
  const out = [];
  for (const cap of caps) {
    if (!cap.parts?.length) {
      out.push(cap);
      continue;
    }
    for (const [i, part] of cap.parts.entries()) {
      out.push({
        ...cap,
        // Reverse markers belong to the capability, not to each part; listing
        // them under every part would repeat the same rows three times.
        reverse_markers: i === 0 ? cap.reverse_markers : { now_default: [], obsolete: [] },
        id: `${cap.id}/${part.id}`,
        title: `${cap.title} — ${part.title || part.id}`,
        part: part.kind || "primary",
        how_enabled: part.how_enabled,
        applies_to: { ...cap.applies_to, ...(part.applies_to || {}) },
        required_floor: part.required_floor || cap.min_vllm_version || null,
        floor_note: part.floor_note || null,
        evidence_sentence: part.evidence_sentence || null,
        install: cap.install || null,
        note: cap.note || null,
        parts: undefined,
      });
    }
  }
  return out;
}

function buildCohorts(allCaps, profiles) {
  const out = [];
  const caps = expandParts(allCaps);
  for (const cap of caps) {
    // A removal is not something to adopt.
    if (cap.kind === "breaking" || cap.kind === "out_of_scope") {
      out.push({
        id: cap.id,
        title: cap.title,
        concept: cap.concept,
        kind: cap.kind,
        cohort: [],
        skipped: cap.kind === "breaking" ? "breaking change — belongs in the stale section" : cap.drop_reason || "out of scope",
      });
      continue;
    }
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
    const support = supportingSentence(cap);
    const needsNoFlag =
      !(cap.how_enabled?.flags || []).length &&
      !(cap.how_enabled?.envs || []).length &&
      !(cap.how_enabled?.enum_values || []).length;
    if (needsNoFlag) {
      const hits = profiles.flatMap((p) => reverseHits(cap, p));
      out.push({
        id: cap.id,
        title: cap.title,
        concept: cap.concept,
        confidence: cap.confidence,
        supporting_sentence: support,
        cohort: [],
        since: cap.since,
        caveat: cap.caveat || null,
        reverse_hits: hits,
        skipped: hits.length
          ? undefined
          : "automatic, and no recipe pins the old default, keeps a retired workaround or documents it — nothing to edit",
      });
      continue;
    }

    // The dimension requirement guards the FORWARD path only. Adding a flag to
    // a cohort needs evidence that the capability covers those recipes; a
    // reverse hit is already bounded to one recipe by the fact that the recipe
    // literally contains the name.
    if (!support) {
      out.push({
        id: cap.id,
        title: cap.title,
        concept: cap.concept,
        confidence: cap.confidence,
        cohort: [],
        skipped:
          "no non-wildcard hardware/model dimension backed by a sentence in the evidence — " +
          "brand alone is not a dimension",
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
      const wanted = (cap.applies_to?.hardware || []).map((h) => h.toLowerCase());
      cohort.push({
        file: profile.file,
        why: checks.map((c) => c.why).join("; "),
        architecture: profile.architecture,
        precisions: profile.precisions,
        // Which of the recipe's own hardware blocks the edit belongs in.
        matched_hardware: profile.hardware_keys.filter((k) => wanted.includes(k.toLowerCase())),
        matched_quant: (cap.applies_to?.quant || []).filter((q) => profile.precisions.includes(q)),
        // The same flag already set to a different value: adopting is then a
        // swap with a behaviour change, not an addition.
        conflicts: (cap.how_enabled?.enum_values || []).flatMap((e) =>
          (profile.flag_values || [])
            .filter((v) => v.flag === e.flag && v.value !== e.value)
            .map((v) => ({ flag: e.flag, current: v.value, proposed: e.value, path: v.path }))
        ),
        hardware_keys: profile.hardware_keys,
        floor: profile.min_vllm_version,
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
      part: cap.part,
      since: cap.since,
      caveat: cap.caveat || null,
      required_floor: cap.required_floor || null,
      floor_note: cap.floor_note || null,
      evidence_sentence: cap.evidence_sentence || null,
      install: cap.install || null,
      note: cap.note || null,
      supporting_sentence: support,
      reverse_hits: profiles.flatMap((p) => reverseHits(cap, p)),
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

  const sized = cohorts.filter((c) => c.cohort.length || c.reverse_hits?.length);
  console.log(`${profiles.length} recipe profiles; ${caps.length} capabilities`);
  console.log(`  capabilities with a cohort: ${sized.length}`);
  console.log(`  skipped (unbounded or default-on): ${cohorts.filter((c) => c.skipped).length}`);
  for (const c of sized.sort((a, b) => b.cohort.length - a.cohort.length)) {
    const excl = c.excluded_already_using?.length ? `, ${c.excluded_already_using.length} already using` : "";
    const rev = c.reverse_hits?.length ? `, ${c.reverse_hits.length} reverse hits` : "";
    console.log(`    ${c.id.slice(0, 46).padEnd(46)} ${String(c.cohort.length).padStart(3)} recipes${excl}${rev}`);
  }
  console.log(`  -> ${join(reportDir, "cohorts.json")}`);
}

main();
