---
name: tune-recipe
description: Benchmark one recipe's serve command against one-change-at-a-time alternatives (strategy, spec decoding, attention/MoE/linear backend, tuning knobs, other checkpoints, env workarounds) on a GPU box the user can rent, gate each on accuracy and latency, and report whether anything beats the recipe. Local evidence only — never edits recipes, never opens PRs by itself. Use when the user asks to tune, benchmark, or find a faster config for a recipe, or to test a sync-vllm adoption candidate on real hardware.
---

# /tune-recipe

Arguments: `<org>/<repo> <gpu> <count> [variant]`, e.g. `Qwen/Qwen3.6-35B-A3B rtx_pro_6000 1 nvfp4`.
`<gpu>` is a taxonomy GPU family (`h100`, `h200`, `b200`, `b300`, `rtx_pro_6000`,
`rtx_5090`, `rtx_4090`). Scripts live next to this file; run everything from the repo root.

## Ground rules

- **Only rentable hardware.** `plan.mjs` reads the GPU/count table in
  `.claude_workdir/USER.md` and refuses anything else. No multi-node, no GB200/GB300.
- **Output is evidence, not an edit.** The run ends at `report.md`. Changing a recipe
  or opening a PR is a separate request from the user, and even then never touches
  `meta.hardware`, verified badges or `performance_headline` from a tuning run alone.
- **Baseline is the site's command.** Config `baseline` is rendered by
  `src/lib/command-synthesis.js` for this hardware. Every other config changes one
  thing. Don't hand-edit `plan.json`; re-plan with the flags below instead.
- **Check upstream before reproducing.** A recipe bug seen on one vLLM release may
  already be fixed in a newer one: look at the latest release notes and at closed
  PRs in both repos (the user's own included) for the issue number before spending
  box time on it.
- **A win must clear the gate.** It started, every request completed, it lost at most
  2 of 32 arithmetic probes vs baseline (and, with `--gsm8k N`, at most 2 GSM8K
  points — the probes only catch a broken config, GSM8K catches a small quality
  loss such as a quantization change), it beat baseline by >3% (one run per
  workload, so smaller gaps are noise), and its E2E latency p50 is at most 10% worse
  than baseline (a throughput gain bought with slower requests is a trade-off, not a
  win). E2E rather than TPOT: when the baseline queues, TPOT only times requests that
  got a slot, so the config that removes the queue would look slower. A config that
  wins some workloads and loses others is reported as workload-dependent, not as a
  new default. Before recommending anything, re-run the winner and the baseline with
  `runner.py --only baseline,<winner>` and confirm.

## Steps

### 1. Plan (local, no GPU)

```bash
node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON .claude/skills/tune-recipe/plan.mjs \
  --recipe <org>/<repo> --gpu <gpu> --count <n> [--variant <v>] \
  [--candidates --moe-backend=b12x,--enforce-eager,ENV:VLLM_USE_V2_MODEL_RUNNER=0] \
  [--variants fp8,default] [--env NAME=value] \
  [--cohorts .claude_workdir/reports/vllm-<tag>/cohorts.json] [--no-knobs]
```

Writes `.claude_workdir/tune/<org>__<repo>/<hw>x<n>-<variant>-<stamp>/plan.json` and
`commands.sh` (shell-quoted, pasteable). Configs come from:

| Source | Configs |
|---|---|
| recipe | `strategy-*` (other single-node strategies that reach this box), `spec-*` (spec decoding on/off, each available mode) |
| `--variants` | `variant-<v>`: another checkpoint of the recipe with its own page defaults (skipped if it can't run or fit here) |
| `--candidates` | always included: `--flag=value` (a backend or knob), a bare `--flag` (e.g. `--enforce-eager`), or `ENV:NAME=value` (one env var) |
| `--cohorts` | backend values a sync-vllm cohort proposes for this recipe |
| repo | backend values other recipes ship for this exact GPU/family (capped by `--max-backends`, default 6) |
| knobs | `tp-<n>` when TP auto-fit leaves GPUs idle, `mnseqs-32` when `--max-num-seqs` is below workload concurrency, `kv-fp8`, `mnbt-16384` — each only when the baseline doesn't already set it |

`--env NAME=value` is different from an `ENV:` candidate: it applies to *every*
config, for a workaround the whole comparison needs (e.g. `VLLM_USE_V2_MODEL_RUNNER=0`
when spec decoding can't start otherwise, so baseline and `spec-*` stay one change apart).

Workloads: `chat` (1000/250, c16), `long_prefill` (8000/100, c4), `decode_heavy`
(250/1000, c32) and `single_user` (1000/250, c1 — the latency workstation recipes
are tuned for), all on random-token prompts. Drafts are still accepted on those
(the output is the model's own text), but acceptance on random context is not what
users see, so a plan with `spec-*` configs adds `spec_text` on Spec-Bench chat
prompts (the runner downloads `question.jsonl` on the box).

Show the user the config list, any `!` warnings, and a time estimate
(≈ 10–15 min per config: model load + probes + workloads; a cold first start can
take far longer) before touching a box. Read `commands.sh` yourself.

### 2. Run (on the box)

The user provides an SSH target once a box is up. Until then, stop after step 1 and
hand over the plan directory. `remote.sh` wraps the SSH side:

```bash
S=.claude/skills/tune-recipe/remote.sh; H=<user@host>; P=<port>; D=<plan-dir>
$S $H $P start  $D [--only a,b] [--workloads chat,single_user] [--gsm8k 500]   # queues behind a running sweep
$S $H $P start  $D --only baseline --workloads none   # smoke: does it start, is it correct
$S $H $P watch  $D     # prints new log lines, exits when the runner is idle — run it as a Monitor
$S $H $P status $D
$S $H $P pull   $D     # copies results/ into the plan dir
$S $H $P stop   $D
```

- **Environment first.** `vllm --version` must be ≥ `plan.min_vllm_version`
  (`nightly` means a nightly wheel). Install into a venv at `/root/venv` (or set
  `TUNE_VENV`): `uv pip install "vllm[bench,b12x]==<version>"` — `bench` is needed for
  `spec_text`, `b12x` only for b12x candidates — plus `plan.dependencies` and
  `fastsafetensors` when the baseline uses `--load-format fastsafetensors`. If the
  plan warns the recipe is Docker-only, run `runner.py` inside `plan.docker_image`
  with the box's HF cache mounted. Gated checkpoints need `HF_TOKEN` exported on the
  box — ask the user, never echo it. Pre-download checkpoints with `hf download` so
  startup times don't include the download.
- **Don't change the box while a run is live.** Installing into the venv during a
  server start can break it mid-import, so install everything first. Don't edit
  `remote.sh` while a `watch` from it is running (bash reads scripts as it goes).
  Any ad hoc `pkill -f`/`pgrep -f` must not match its own command line — anchor the
  pattern (e.g. `^python3 runner.py`) or use the `[r]unner` trick.
- **Monitor** with `remote.sh watch` as a Monitor (it expires after 30 min — re-arm).
  The runner is resumable: re-run `start` and finished configs are skipped.
- **Startup.** The runner sets `VLLM_ENGINE_READY_TIMEOUT_S` to its own
  `--ready-timeout` (1800 s), so a slow cold compile is measured rather than cut off
  at vLLM's 600 s default. The report flags any config whose engine init exceeded
  600 s — the site's command would fail on such a launch.
- A `start_failed` config is a result (it doesn't run here), not something to debug
  unless the user asks — its `log_tail` is in `result.json`. A diagnostic follow-up
  (e.g. `--enforce-eager`) is a new plan with that candidate, run on few workloads.

### 3. Analyze (local)

```bash
$S $H $P pull $D && python3 .claude/skills/tune-recipe/analyze.py $D
```

`report.md` opens with warnings — including a checkpoint whose layers are labeled
weight-only (W4A16) yet ship activation scales, which vLLM will run on weight-only
kernels (found on `nvidia/Qwen3.6-35B-A3B-NVFP4`: relabeled, the same tensors ran
~35% faster on B200 at the same GSM8K). Then, per config: gate, probes, GSM8K,
startup, and a "Startup and kernels" table
— engine init, warmup runs per model, and the backends vLLM chose (read this first:
e.g. an NVFP4 checkpoint landing on Marlin explains a lot); per workload: throughput,
per-GPU, TTFT/TPOT/E2E, and draft acceptance from `/metrics` for `spec-*` configs.

Present the verdict: the winner per workload, what it loses elsewhere, its placement
in the YAML, and GPU-count caveats (a `tp-*`/`strategy-*` config using more GPUs must
win per GPU too). If nothing clears the gate, the answer is "the recipe is already
right here" — say so.

### 4. Profile (optional, on request)

Only when the user asks, or a result needs explaining (a backend that loses, a
surprising win). It is a separate pass and never feeds the throughput tables:

```bash
$S $H $P start $D --only baseline,<config> --profile <workload> [--profile-delay 0]
```

Each config restarts with the torch profiler (`--profiler-config`), traces 30
iterations of a short run of that workload after skipping `--profile-delay` steps
(default 20 = steady-state decode; 0 = include prefill), and writes its top GPU
kernels to `results/<config>/profile-<workload>.json`; `analyze.py` adds them as a
"Profiles" section. Compare kernel shares between the two configs to say *where*
the time went. A crash (illegal address, bad kernel) is a debugging job for
`compute-sanitizer`, not the profiler.

## Maintenance

`selftest/selftest.sh` runs plan → runner → analyze against a fake `vllm` (no GPU):
startup-failure isolation, the accuracy (probes, GSM8K) and E2E gates, checkpoint
label inspection, the noise floor, the verdict
and its losses, resume, `--env`/`--variants`/env and bare-flag candidates,
`--workloads`, the single-user workload, backend and startup parsing, the slow-start
warning, draft acceptance and the profiling pass. Run it after changing any script:

```bash
bash .claude/skills/tune-recipe/selftest/selftest.sh
```

`remote.sh` is not covered by the selftest; exercise `start`/`watch`/`pull` against a
real box after changing it.
