---
name: tune-recipe
description: Benchmark one recipe's serve command against one-change-at-a-time alternatives (strategy, spec decoding, attention/MoE/linear backend, tuning knobs) on a GPU box the user can rent, gate each on accuracy, and report whether anything beats the recipe. Local evidence only — never edits recipes, never opens PRs. Use when the user asks to tune, benchmark, or find a faster config for a recipe, or to test a sync-vllm adoption candidate on real hardware.
---

# /tune-recipe

Arguments: `<org>/<repo> <gpu> <count> [variant]`, e.g. `Qwen/Qwen3.6-35B-A3B rtx_pro_6000 1 nvfp4`.
`<gpu>` is a taxonomy GPU family (`h100`, `h200`, `b200`, `b300`, `rtx_pro_6000`,
`rtx_5090`, `rtx_4090`). Scripts live next to this file; run everything from the repo root.

## Ground rules

- **Only rentable hardware.** `plan.mjs` reads the GPU/count table in
  `.claude_workdir/USER.md` and refuses anything else. No multi-node, no GB200/GB300.
- **Output is evidence, not an edit.** The run ends at `report.md`. Changing a recipe
  is a separate request from the user, and even then never touches `meta.hardware`,
  verified badges or `performance_headline` from a tuning run alone. No PRs, no issues.
- **Baseline is the site's command.** Config `baseline` is rendered by
  `src/lib/command-synthesis.js` for this hardware. Every other config changes one
  thing. Don't hand-edit `plan.json` argv to "fix" a config; re-plan instead.
- **A win must clear the gate.** It started, every request completed, it lost at most
  2 of 32 arithmetic probes vs baseline, it beat baseline by >3% (one run per
  workload, so smaller gaps are noise), and its TPOT p50 is at most 10% worse than
  baseline (a throughput gain bought with slower decoding is a trade-off, not a win). Before recommending anything, re-run the
  winner and the baseline with `runner.py --only baseline,<winner>` and confirm.

## Steps

### 1. Plan (local, no GPU)

```bash
node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON .claude/skills/tune-recipe/plan.mjs \
  --recipe <org>/<repo> --gpu <gpu> --count <n> [--variant <v>] \
  [--candidates --moe-backend=b12x,--linear-backend=b12x] \
  [--cohorts .claude_workdir/reports/vllm-<tag>/cohorts.json] [--no-knobs]
```

Writes `.claude_workdir/tune/<org>__<repo>/<hw>x<n>-<variant>-<stamp>/plan.json` and
`commands.sh`. Configs come from:

| Source | Configs |
|---|---|
| recipe | `strategy-*` (other single-node strategies that reach this box), `spec-*` (spec decoding on/off, each available mode) |
| `--candidates` | one config per `flag=value`, always included |
| `--cohorts` | backend values a sync-vllm cohort proposes for this recipe |
| repo | backend values other recipes ship for this exact GPU/family (capped by `--max-backends`, default 6) |
| knobs | `tp-<n>` when TP auto-fit leaves GPUs idle, `mnseqs-32` when `--max-num-seqs` is below workload concurrency, `kv-fp8`, `mnbt-16384` — each only when the baseline doesn't already set it |

Show the user the config list, any `!` warnings, and a time estimate
(≈ 10–15 min per config: model load + probes + three workloads) before touching a box.
Workloads use random tokens, which defeat draft models, so a plan with `spec-*`
configs adds a fourth `spec_text` workload on Spec-Bench chat prompts (the runner
downloads `question.jsonl` on the box). Judge spec decoding on that one.
Read `commands.sh` yourself; drop configs the evidence doesn't support by re-planning
with `--no-knobs` / fewer `--candidates`, not by editing JSON.

### 2. Run (on the box)

The user provides an SSH target once a box is up. Until then, stop after step 1 and
hand over the plan directory.

```bash
H=<user@host>; D=<plan-dir>; R=tune/$(basename $D)
ssh $H "mkdir -p $R && nvidia-smi -L && vllm --version"
scp .claude/skills/tune-recipe/runner.py $D/plan.json $H:$R/
ssh $H "cd $R && nohup python3 runner.py plan.json --out results > sweep.log 2>&1 &"
```

- **Environment first.** `vllm --version` must be ≥ `plan.min_vllm_version`
  (`nightly` means a nightly wheel). Install `plan.dependencies` and any extra a
  candidate needs (b12x → `uv pip install "vllm[b12x]"`). If the plan warns the
  recipe is Docker-only, run `runner.py` inside `plan.docker_image` with the box's
  HF cache mounted. Gated checkpoints need `HF_TOKEN` exported on the box — ask the
  user, never echo it.
- **Monitor** with `ssh $H "tail -5 $R/sweep.log"` at long intervals (use a wakeup,
  not a tight loop). The runner is resumable: after a disconnect or crash, re-run the
  same command and finished configs are skipped.
- A `start_failed` config is a result (the backend doesn't run here), not something
  to debug unless the user asks — its `log_tail` is in `result.json`.

### 3. Analyze (local)

```bash
scp -r $H:$R/results $D/
python3 .claude/skills/tune-recipe/analyze.py $D
```

Present `report.md`'s verdict: the winner per workload, its placement in the YAML, and
GPU-count caveats (a `tp-*`/`strategy-*` config using more GPUs must win per GPU too).
If nothing clears the gate, the answer is "the recipe is already right here" — say so.

## Maintenance

`selftest/selftest.sh` runs plan → runner → analyze against a fake `vllm` (no GPU) and
checks startup-failure isolation, the accuracy gate, the noise floor, the verdict and
resume. Run it after changing any script:

```bash
bash .claude/skills/tune-recipe/selftest/selftest.sh
```
