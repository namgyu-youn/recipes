#!/usr/bin/env node
// Build a tuning plan for one recipe on one rentable GPU box.
//
//   node .claude/skills/tune-recipe/plan.mjs --recipe Qwen/Qwen3.6-35B-A3B \
//     --gpu rtx_pro_6000 --count 1 [--variant nvfp4] [--candidates --moe-backend=b12x,...]
//     [--cohorts <sync-vllm cohorts.json>] [--max-backends 6] [--no-knobs] [--out <dir>]
//     [--variants fp8,default] [--env NAME=value ...]
//
// --candidates takes `--flag=value` (one backend/knob), a bare `--flag`
// (e.g. --enforce-eager) or `ENV:NAME=value` (one environment variable).
// --variants adds one config per other checkpoint of the recipe. --env sets a
// variable on EVERY config (e.g. a workaround the whole plan needs), so the
// comparison between configs stays one change apart.
//
// Every serve command comes from src/lib/command-synthesis.js, so config
// "baseline" is exactly what the recipe page renders for this hardware. The
// other configs change ONE thing each: strategy, spec-decoding on/off/mode,
// one backend value, or one tuning knob.
//
// Run from the repo root.

import fs from "fs";
import path from "path";
import yaml from "js-yaml";
import {
  resolveCommand,
  recommendStrategy,
  effectiveCompatibleStrategies,
  isStrategySupportedOnHardware,
  isStrategyReachable,
  isHardwareSupported,
  isPrecisionCompatible,
  isVariantHardwareSupported,
  isModeAllowedForVariant,
  isModeSupported,
  computeDockerMeta,
} from "../../../src/lib/command-synthesis.js";

const ROOT = process.cwd();
const USER_MD = path.join(ROOT, ".claude_workdir/USER.md");

// USER.md rental names → taxonomy GPU family (a family is a profile id with any
// `_<n>x` suffix stripped). Rentals with no taxonomy profile (A100, RTX 6000
// Ada, RTX A6000) are absent: the site renders no command for them.
const RENTAL_FAMILY = {
  "B300 SXM6 AC": "b300",
  "B200": "b200",
  "H200": "h200",
  "H100 80GB HBM3": "h100",
  "H100 PCIe": "h100",
  "RTX 5090": "rtx_5090",
  "RTX 4090": "rtx_4090",
  "RTX PRO 6000 Blackwell Server Edition": "rtx_pro_6000",
  "RTX PRO 6000 Blackwell Workstation Edition": "rtx_pro_6000",
};

const BACKEND_FLAGS = ["--attention-backend", "--moe-backend", "--linear-backend"];

// Workloads are fixed so results are comparable across runs and recipes.
const WORKLOADS = [
  { name: "chat", input_len: 1000, output_len: 250, concurrency: 16, num_prompts: 160 },
  { name: "long_prefill", input_len: 8000, output_len: 100, concurrency: 4, num_prompts: 40 },
  { name: "decode_heavy", input_len: 250, output_len: 1000, concurrency: 32, num_prompts: 128 },
  // One user at a time: the latency workstation recipes are tuned for.
  { name: "single_user", input_len: 1000, output_len: 250, concurrency: 1, num_prompts: 10 },
];

// Draft acceptance on random-token prompts is not what users see, so a plan
// with spec-* configs adds a real-text workload. Concurrency stays low so a
// recipe's small --max-num-seqs does not turn it into a queueing test.
const SPEC_WORKLOAD = { name: "spec_text", dataset: "spec_bench", output_len: 256, concurrency: 8, num_prompts: 80 };

function die(msg) {
  console.error(`error: ${msg}`);
  process.exit(1);
}

function parseArgs(argv) {
  const out = { variant: "default", count: 1, maxBackends: 6, knobs: true, candidates: [], variants: [], env: {} };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    const next = () => argv[++i];
    if (a === "--recipe") out.recipe = next();
    else if (a === "--variant") out.variant = next();
    else if (a === "--gpu") out.gpu = next();
    else if (a === "--count") out.count = Number(next());
    else if (a === "--candidates") out.candidates = next().split(",").filter(Boolean);
    else if (a === "--cohorts") out.cohorts = next();
    else if (a === "--max-backends") out.maxBackends = Number(next());
    else if (a === "--no-knobs") out.knobs = false;
    else if (a === "--out") out.out = next();
    else if (a === "--variants") out.variants = next().split(",").filter(Boolean);
    else if (a === "--env") {
      const [k, ...v] = next().split("=");
      out.env[k] = v.join("=");
    }
    else die(`unknown argument ${a}`);
  }
  if (!out.recipe || !out.gpu) die("--recipe and --gpu are required");
  return out;
}

// True when version a is newer than b ("0.28.0" vs "0.17.0"); "nightly" wins.
const newerVersion = (a, b) => {
  if (!a || a === b) return false;
  if (a === "nightly" || !b) return true;
  const [x, y] = [a, b].map((v) => String(v).split(".").map(Number));
  for (let i = 0; i < Math.max(x.length, y.length); i++) if ((x[i] || 0) !== (y[i] || 0)) return (x[i] || 0) > (y[i] || 0);
  return false;
};
const readYaml = (p) => yaml.load(fs.readFileSync(p, "utf8"));
// Quote for commands.sh so its lines paste into a shell as-is.
const shq = (a) => (/^[\w@%+=:,./-]+$/.test(String(a)) ? String(a) : `'${String(a).replace(/'/g, `'\\''`)}'`);
const family = (id) => id.replace(/_\d+x$/, "");

function rentableCounts() {
  if (!fs.existsSync(USER_MD)) die(`${USER_MD} not found — it lists the rentable GPUs`);
  const counts = {};
  for (const line of fs.readFileSync(USER_MD, "utf8").split("\n")) {
    const m = line.match(/^\|\s*([^|]+?)\s*\|\s*([\d,\s]+?)\s*\|$/);
    if (!m) continue;
    const fam = RENTAL_FAMILY[m[1]];
    if (!fam) continue;
    counts[fam] = [...new Set([...(counts[fam] || []), ...m[2].split(",").map(Number)])];
  }
  return counts;
}

// Pick the taxonomy profile for (family, count). An exact-count profile wins;
// otherwise the family's base profile is cloned with the rented count and
// per-GPU VRAM kept, so the id (and every override keyed on it) stays the same.
function resolveProfile(taxonomy, fam, count) {
  const profiles = taxonomy.hardware_profiles;
  const members = Object.keys(profiles).filter((id) => family(id) === fam);
  if (!members.length) die(`no taxonomy profile for GPU family ${fam}`);
  const exact = members.find((id) => profiles[id].gpu_count === count);
  if (exact) return { id: exact, profile: profiles[exact], synthetic: false };
  const base = members.includes(fam)
    ? fam
    : members.sort((a, b) => profiles[a].gpu_count - profiles[b].gpu_count)[0];
  const p = profiles[base];
  const perGpu = p.vram_gb / p.gpu_count;
  return {
    id: base,
    profile: { ...p, gpu_count: count, vram_gb: Math.round(perGpu * count) },
    synthetic: true,
  };
}

function loadStrategies() {
  const out = {};
  for (const dir of ["strategies", "kv_store"]) {
    for (const f of fs.readdirSync(path.join(ROOT, dir)).filter((f) => f.endsWith(".yaml"))) {
      const s = readYaml(path.join(ROOT, dir, f));
      out[s.name] = s;
    }
  }
  return out;
}

function loadRecipe(spec) {
  const rel = spec.endsWith(".yaml") ? spec : `models/${spec}.yaml`;
  const file = path.join(ROOT, rel);
  if (!fs.existsSync(file)) die(`recipe not found: ${rel}`);
  const recipe = readYaml(file);
  const [org, repo] = rel.replace(/^models\//, "").replace(/\.yaml$/, "").split("/");
  recipe.hf_id = `${org}/${repo}`;
  return { recipe, file: rel };
}

// Same rule as scripts/build-recipes-api.mjs defaultFeaturesFor.
function defaultFeatures(recipe, hwId, variantKey) {
  const optIn = new Set(recipe.opt_in_features || []);
  for (const f of recipe.hardware_opt_in_features?.[hwId] || []) optIn.add(f);
  const forced = new Set(Object.keys(recipe.variants?.[variantKey]?.default_modes || {}));
  return Object.keys(recipe.features || {}).filter((f) => forced.has(f) || !optIn.has(f));
}

function flagValue(argv, flag) {
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === flag) return argv[i + 1];
    if (argv[i].startsWith(`${flag}=`)) return argv[i].slice(flag.length + 1);
  }
  return undefined;
}

// Backend values other recipes already ship for this GPU: overrides keyed by
// its exact id or family. Generation keys are NOT evidence — "blackwell" spans
// SM100 datacenter parts and SM120 workstation cards, whose kernels differ.
function repoBackendValues(hwId) {
  const keys = new Set([hwId, family(hwId)]);
  const found = {};
  const note = (args) => {
    for (const flag of BACKEND_FLAGS) {
      const v = args && flagValue(args.map(String), flag);
      if (v) (found[flag] ||= new Map()).set(v, (found[flag].get(v) || 0) + 1);
    }
  };
  const walk = (dir) => {
    for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
      const p = path.join(dir, e.name);
      if (e.isDirectory()) walk(p);
      else if (e.name.endsWith(".yaml")) {
        let r;
        try { r = readYaml(p); } catch { continue; }
        for (const [k, ho] of Object.entries(r.hardware_overrides || {})) if (keys.has(k)) note(ho?.extra_args);
        for (const v of Object.values(r.variants || {})) {
          for (const [k, ho] of Object.entries(v?.hardware_overrides || {})) if (keys.has(k)) note(ho?.extra_args);
        }
      }
    }
  };
  walk(path.join(ROOT, "models"));
  return found;
}

function cohortCandidates(cohortsPath, recipeFile) {
  if (!cohortsPath) return [];
  const data = JSON.parse(fs.readFileSync(cohortsPath, "utf8"));
  const list = Array.isArray(data) ? data : data.cohorts || [];
  const out = [];
  for (const c of list) {
    if (!(c.cohort || []).some((m) => m.file === recipeFile)) continue;
    for (const e of c.how_enabled?.enum_values || []) out.push({ flag: e.flag, value: e.value, source: `cohort ${c.id}` });
  }
  return out;
}

// Deterministic arithmetic probes: a correctness signal that does not depend
// on matching the baseline token-for-token (a different kernel legitimately
// perturbs greedy decoding).
function probes(n = 32) {
  let seed = 20260921;
  const rnd = () => (seed = (seed * 1103515245 + 12345) % 2147483648) / 2147483648;
  return Array.from({ length: n }, () => {
    const a = 12 + Math.floor(rnd() * 88);
    const b = 12 + Math.floor(rnd() * 88);
    const c = 100 + Math.floor(rnd() * 900);
    return {
      prompt: `What is ${a} * ${b} + ${c}? Reply with only the final integer.`,
      answer: a * b + c,
    };
  });
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const taxonomy = readYaml(path.join(ROOT, "taxonomy.yaml"));
  const strategies = loadStrategies();
  const { recipe, file } = loadRecipe(args.recipe);

  const fam = family(args.gpu);
  const rentable = rentableCounts();
  if (!rentable[fam]?.includes(args.count)) {
    die(`${fam} x${args.count} is not rentable per USER.md (rentable: ${JSON.stringify(rentable[fam] || [])})`);
  }
  const { id: hwId, profile, synthetic } = resolveProfile(taxonomy, fam, args.count);
  const tax = { ...taxonomy, hardware_profiles: { ...taxonomy.hardware_profiles, [hwId]: profile } };

  const variant = recipe.variants?.[args.variant];
  if (!variant) die(`variant ${args.variant} not in recipe (have: ${Object.keys(recipe.variants || {}).join(", ")})`);
  if (!isHardwareSupported(recipe, hwId)) die(`${recipe.hf_id} marks ${hwId} unsupported`);
  if (!isPrecisionCompatible(profile, variant)) die(`${variant.precision} is not runnable on ${hwId} (${profile.generation})`);
  if (!isVariantHardwareSupported(variant, hwId)) die(`variant ${args.variant} marks ${hwId} unsupported`);
  if (profile.multi_node) die(`${hwId} is a multi-node profile — out of scope`);
  const warnings = [];
  if (profile.restricted && !recipe.meta?.hardware?.[hwId]) {
    warnings.push(`${hwId} is a restricted profile the recipe does not list in meta.hardware — the site does not offer this command`);
  }
  if (recipe.model?.install?.pip === false || variant.hardware_overrides?.[hwId]?.install?.pip === false) {
    warnings.push("the recipe is Docker-only on this hardware; runner.py uses the pip path, so run it inside the recipe's image");
  }

  const features = defaultFeatures(recipe, hwId, args.variant);
  const modes = { ...(variant.default_modes || {}) };

  const offered = effectiveCompatibleStrategies(recipe).filter((s) => {
    const spec = strategies[s];
    if (!spec || spec.deploy_type !== "single_node") return false;
    if (!isStrategySupportedOnHardware(recipe, s, hwId)) return false;
    if (!isStrategyReachable(recipe, s, "single_node", args.count, hwId)) return false;
    // TEP/DEP on one GPU degenerate to TP.
    return args.count > 1 || s === "single_node_tp";
  });
  if (!offered.length) die(`no single-node strategy reaches ${hwId} x${args.count} for this recipe`);
  const rec = recommendStrategy(recipe, profile, 1);
  const baseStrategy = offered.includes(rec) ? rec : offered[0];

  const render = (strategy, feats, featModes, extra, variantKey, extraEnv) => {
    const r = resolveCommand(recipe, variantKey, strategy, hwId, feats, strategies, tax, extra, 1, null, featModes);
    if (!r || r.deployType !== "single_node") return null;
    return { argv: r.argv, env: { ...(r.env || {}), ...args.env, ...extraEnv } };
  };

  const configs = [];
  const seen = new Set();
  const add = (name, why, strategy, feats, featModes, extra = [], { variant: v = args.variant, env = {} } = {}) => {
    const r = render(strategy, feats, featModes, extra, v, env);
    if (!r) return;
    const key = JSON.stringify([r.argv, r.env]);
    if (seen.has(key)) return; // a change that renders identically is not a config
    seen.add(key);
    configs.push({ name, why, strategy, variant: v, features: feats, modes: featModes, extra_args: extra, extra_env: env, ...r });
  };
  if (Object.keys(args.env).length) {
    warnings.push(`every config runs with ${Object.entries(args.env).map(([k, v]) => `${k}=${v}`).join(" ")} (--env), which the site's command does not set`);
  }

  add("baseline", "the command the recipe page renders for this hardware", baseStrategy, features, modes);
  if (!configs.length) die("baseline command failed to render");
  const baseArgv = configs[0].argv;

  for (const s of offered) {
    if (s !== baseStrategy) add(`strategy-${s}`, `serving strategy ${s}`, s, features, modes);
  }

  // Other checkpoints of the same recipe, each with its own page defaults.
  for (const vk of args.variants) {
    const v = recipe.variants?.[vk];
    if (!v) die(`variant ${vk} not in recipe`);
    if (vk === args.variant) continue;
    if (!isPrecisionCompatible(profile, v) || !isVariantHardwareSupported(v, hwId)) {
      warnings.push(`variant ${vk} skipped: not runnable on ${hwId}`);
      continue;
    }
    if ((v.vram_minimum_gb || 0) > profile.vram_gb) {
      warnings.push(`variant ${vk} skipped: needs ${v.vram_minimum_gb} GB, box has ${profile.vram_gb} GB`);
      continue;
    }
    const vMin = v.min_vllm_version || recipe.model?.min_vllm_version;
    const baseMin = variant.min_vllm_version || recipe.model?.min_vllm_version;
    if (newerVersion(vMin, baseMin)) warnings.push(`variant ${vk} needs vLLM >= ${vMin}, above the plan floor ${baseMin}`);
    add(`variant-${vk}`, `variant ${vk} (${v.model_id || recipe.model?.model_id})`, baseStrategy,
      defaultFeatures(recipe, hwId, vk), { ...(v.default_modes || {}) }, [], { variant: vk });
  }

  // Spec decoding is the only feature toggled: it is a perf knob, whereas
  // tool calling / reasoning / text-only change what the server does.
  const spec = recipe.features?.spec_decoding;
  if (spec) {
    if (features.includes("spec_decoding")) {
      add("spec-off", "spec decoding disabled", baseStrategy, features.filter((f) => f !== "spec_decoding"), modes);
    }
    const on = features.includes("spec_decoding") ? features : [...features, "spec_decoding"];
    if (spec.modes) {
      for (const [mk, mode] of Object.entries(spec.modes)) {
        if (!isModeAllowedForVariant(mode, args.variant) || !isModeSupported(mode, profile, hwId)) continue;
        add(`spec-${mk}`, `spec decoding, ${mode.label || mk} method`, baseStrategy, on, { ...modes, spec_decoding: mk });
      }
    } else if (!features.includes("spec_decoding")) {
      add("spec-on", "spec decoding enabled", baseStrategy, on, modes);
    }
  }

  // Backend candidates: explicit > sync-vllm cohort > what other recipes ship here.
  const isMoe = recipe.model?.architecture === "moe";
  const baseAttn = flagValue(baseArgv, "--attention-backend") || "";
  const usesMla = /MLA/i.test(baseAttn);
  // Explicit env and bare-flag candidates; `--flag=value` ones join the backend list.
  for (const c of args.candidates) {
    if (c.startsWith("ENV:")) {
      const [k, ...v] = c.slice(4).split("=");
      add(`env-${k}-${v.join("=")}`, `${k}=${v.join("=")} (--candidates)`, baseStrategy, features, modes, [], { env: { [k]: v.join("=") } });
    } else if (!c.includes("=")) {
      add(c.replace(/^--/, ""), `${c} (--candidates)`, baseStrategy, features, modes, [c]);
    }
  }
  const cands = [
    ...args.candidates.filter((c) => c.includes("=") && !c.startsWith("ENV:")).map((c) => {
      const [flag, value] = c.split("=");
      return { flag, value, source: "--candidates" };
    }),
    ...cohortCandidates(args.cohorts, file),
  ];
  const repoVals = repoBackendValues(hwId);
  for (const flag of BACKEND_FLAGS) {
    const ranked = [...(repoVals[flag] || new Map()).entries()].sort((a, b) => b[1] - a[1]);
    for (const [value, n] of ranked) cands.push({ flag, value, source: `${n} recipe(s) ship it on ${family(hwId)}` });
  }
  let backendCount = 0;
  const tried = new Set();
  for (const c of cands) {
    // Backend names are case-insensitive (flashinfer == FLASHINFER).
    const key = `${c.flag}=${String(c.value).toLowerCase()}`;
    if (!c.flag || !c.value || tried.has(key)) continue;
    tried.add(key);
    if (c.flag === "--moe-backend" && !isMoe) continue;
    if (c.flag === "--attention-backend" && /MLA/i.test(c.value) !== usesMla) continue;
    if (String(flagValue(baseArgv, c.flag) || "").toLowerCase() === c.value.toLowerCase()) continue;
    const explicit = c.source === "--candidates";
    if (!explicit && backendCount >= args.maxBackends) continue;
    const before = configs.length;
    add(`${c.flag.replace(/^--/, "")}-${c.value}`, `${c.flag} ${c.value} (${c.source})`, baseStrategy, features, modes, [c.flag, c.value]);
    if (!explicit && configs.length > before) backendCount++;
  }

  const maxConc = Math.max(...WORKLOADS.map((w) => w.concurrency));
  const seqs = Number(flagValue(baseArgv, "--max-num-seqs"));
  if (seqs && seqs < maxConc) {
    warnings.push(`baseline caps --max-num-seqs at ${seqs}, below workload concurrency ${maxConc}: requests queue, so TTFT includes wait time`);
  }

  if (args.knobs) {
    const fp8Kv = ["hopper", "blackwell", "ada"].includes(profile.generation);
    if (fp8Kv && !flagValue(baseArgv, "--kv-cache-dtype")) {
      add("kv-fp8", "FP8 KV cache (more KV capacity; accuracy-gated)", baseStrategy, features, modes, ["--kv-cache-dtype", "fp8"]);
    }
    // The recipe auto-fits TP to VRAM, so a model that fits one GPU leaves the
    // rest of a rented box idle. Measure using all of it.
    const baseTp = Number(flagValue(baseArgv, "--tensor-parallel-size"));
    if (baseTp && baseTp < args.count) {
      const before = configs.length;
      add(`tp-${args.count}`, `--tensor-parallel-size ${args.count} (recipe fits TP=${baseTp}; uses the whole box)`, baseStrategy, features, modes, ["--tensor-parallel-size", String(args.count)]);
      const c = configs[configs.length - 1];
      if (configs.length > before && Number(flagValue(c.argv, "--tensor-parallel-size")) !== args.count) configs.pop();
    }
    if (seqs && seqs < maxConc) {
      add(`mnseqs-${maxConc}`, `--max-num-seqs ${maxConc} (recipe caps at ${seqs}, below workload concurrency)`, baseStrategy, features, modes, ["--max-num-seqs", String(maxConc)]);
    }
    if (!flagValue(baseArgv, "--max-num-batched-tokens")) {
      add("mnbt-16384", "larger prefill chunk (--max-num-batched-tokens 16384)", baseStrategy, features, modes, ["--max-num-batched-tokens", "16384"]);
    }
  }

  const maxLen = Number(flagValue(baseArgv, "--max-model-len")) || recipe.model?.context_length || 8192;
  const workloads = WORKLOADS.map((w) => {
    const input = Math.min(w.input_len, maxLen - w.output_len - 64);
    return { ...w, input_len: input };
  }).filter((w) => w.input_len > 0);
  if (configs.some((c) => c.name.startsWith("spec-"))) workloads.push(SPEC_WORKLOAD);

  const stamp = new Date().toISOString().replace(/[-:]/g, "").slice(0, 13);
  const outDir = args.out || path.join(".claude_workdir/tune", recipe.hf_id.replace("/", "__"), `${hwId}x${args.count}-${args.variant}-${stamp}`);
  fs.mkdirSync(outDir, { recursive: true });

  const plan = {
    recipe: file,
    hf_id: recipe.hf_id,
    variant: args.variant,
    hardware: { id: hwId, family: fam, count: args.count, generation: profile.generation, synthetic_profile: synthetic },
    min_vllm_version: variant.min_vllm_version || recipe.model?.min_vllm_version || null,
    docker_image: computeDockerMeta(recipe, variant, profile, hwId)?.image || null,
    dependencies: (recipe.dependencies || [])
      .filter((d) => !d.brand || [].concat(d.brand).includes(profile.brand))
      .map((d) => ({ command: d.command, optional: !!d.optional })),
    created: new Date().toISOString(),
    warnings,
    configs,
    workloads,
    probes: probes(),
  };
  fs.writeFileSync(path.join(outDir, "plan.json"), JSON.stringify(plan, null, 2));

  const sh = ["# Commands in this plan (for reading; runner.py executes them)", ""];
  for (const c of configs) {
    const env = Object.entries(c.env).map(([k, v]) => `${k}=${shq(v)}`).join(" ");
    sh.push(`# ${c.name}: ${c.why}`, `${env ? env + " " : ""}${c.argv.map(shq).join(" ")}`, "");
  }
  fs.writeFileSync(path.join(outDir, "commands.sh"), sh.join("\n"));

  console.log(`plan: ${outDir}/plan.json`);
  console.log(`  ${recipe.hf_id} [${args.variant}] on ${hwId} x${args.count}${synthetic ? " (profile cloned to rented count)" : ""}`);
  for (const c of configs) console.log(`  - ${c.name.padEnd(34)} ${c.why}`);
  for (const w of warnings) console.log(`  ! ${w}`);
  console.log(`  workloads: ${workloads.map((w) => `${w.name}(${w.dataset || w.input_len}/${w.output_len} c${w.concurrency})`).join(", ")}`);
}

main();
