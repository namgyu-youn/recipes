#!/usr/bin/env bash
# End-to-end check of plan.mjs -> runner.py -> analyze.py with a fake `vllm`.
# Run from the repo root. No GPU needed; exits non-zero on any failed check.
set -euo pipefail

HERE=$(cd "$(dirname "$0")" && pwd)
SKILL=$(dirname "$HERE")
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON "$SKILL/plan.mjs" \
  --recipe Qwen/Qwen3.6-35B-A3B --gpu rtx_pro_6000 --count 1 --variant nvfp4 \
  --candidates --moe-backend=BROKEN,--linear-backend=b12x,ENV:FAKE_SLOW_INIT=1,--enforce-eager \
  --variants fp8 --env FAKE_GLOBAL=1 --out "$TMP" >/dev/null
grep -q "FAKE_GLOBAL=1 vllm serve" "$TMP/commands.sh" && echo "ok   --env reaches every command" || { echo "FAIL --env missing"; exit 1; }

# The recipe already sets --kv-cache-dtype fp8 here, so the knob is absent.
# Add one fp8-KV config by hand so the accuracy gate has something to reject.
python3 - "$TMP/plan.json" <<'EOF'
import json, sys
p = json.load(open(sys.argv[1]))
p["configs"] = [c for c in p["configs"] if c["name"] in
                ("baseline", "spec-mtp", "moe-backend-BROKEN", "linear-backend-b12x", "mnseqs-32",
                 "variant-fp8", "env-FAKE_SLOW_INIT-1", "enforce-eager")]
for c in p["configs"]:
    c["argv"] = [a if a != "fp8" else "auto" for a in c["argv"]]
bad = dict(p["configs"][0], name="kv-fp8", why="fp8 KV", extra_args=["--kv-cache-dtype", "fp8"])
bad["argv"] = [a if a != "auto" else "fp8" for a in p["configs"][0]["argv"]]
p["configs"].append(bad)
m32 = next(c for c in p["configs"] if c["name"] == "mnseqs-32")
m64 = dict(m32, name="mnseqs-64", why="max-num-seqs 64", extra_args=["--max-num-seqs", "64"])
m64["argv"] = [a if a != "32" else "64" for a in m32["argv"]]
p["configs"].append(m64)
m48 = dict(m32, name="mnseqs-48", why="max-num-seqs 48", extra_args=["--max-num-seqs", "48"])
m48["argv"] = [a if a != "32" else "48" for a in m32["argv"]]
p["configs"].append(m48)
p["probes"] = p["probes"][:8]
json.dump(p, open(sys.argv[1], "w"))
EOF

# Offline stand-in for the Spec-Bench download.
mkdir -p "$TMP/results" && echo '{"category": "writing", "turns": ["Write a haiku."]}' >"$TMP/results/spec_bench.jsonl"
# enforce-eager runs alone first, on one workload (--workloads).
PATH="$HERE:$PATH" python3 "$SKILL/runner.py" "$TMP/plan.json" --out "$TMP/results" --port 18123 \
  --only enforce-eager --workloads single_user >"$TMP/run.log"
PATH="$HERE:$PATH" python3 "$SKILL/runner.py" "$TMP/plan.json" --out "$TMP/results" --port 18123 --ready-timeout 30 >>"$TMP/run.log"
# Second run must resume, not re-run.
PATH="$HERE:$PATH" python3 "$SKILL/runner.py" "$TMP/plan.json" --out "$TMP/results" --port 18123 >>"$TMP/run.log"
# Profiling pass: separate traced runs, must not touch result.json.
PATH="$HERE:$PATH" python3 "$SKILL/runner.py" "$TMP/plan.json" --out "$TMP/results" --port 18123 \
  --only baseline,spec-mtp --profile chat >>"$TMP/run.log"
python3 "$SKILL/analyze.py" "$TMP" >/dev/null

fail=0
check() { if grep -q -- "$2" "$1"; then echo "ok   $3"; else echo "FAIL $3"; fail=1; fi; }
R="$TMP/report.md"
check "$R" '`moe-backend-BROKEN`.*start_failed' "startup failure is recorded, sweep continues"
check "$R" '`kv-fp8`.*accuracy 4/8' "accuracy gate rejects a config that loses probes"
check "$R" '`linear-backend-b12x`.*| pass |' "a sub-noise config passes the gate"
check "$R" '\*\*`mnseqs-48`\*\* wins 4/5' "a +25% win with worse TPOT but better E2E is the verdict"
check "$R" '`mnseqs-64`.*slower requests' "a throughput gain with +15% E2E latency is flagged"
if grep -q 'mnseqs-64`\*\* wins' "$R"; then echo "FAIL E2E regression counted as a win"; fail=1; else echo "ok   E2E regression is not a win"; fi
check "$R" '^## spec_text — Spec-Bench' "spec configs add a real-text workload"
check "$R" 'baseline caps --max-num-seqs at 8' "queueing baseline is warned about"
check "$R" '`baseline`.*| 8/8' "probe answers are read from reasoning when content is empty"
if grep -q 'linear-backend-b12x`\*\* wins' "$R"; then echo "FAIL +1% counted as a win"; fail=1; else echo "ok   +1% stays inside the noise floor"; fi
check "$TMP/run.log" 'already done, skipping' "re-run resumes from result.json"
check "$R" '`spec-mtp` 55.0% (mean length 3.20; per position 0.80 / 0.60 / 0.50 / 0.30)' "draft acceptance comes from /metrics deltas"
if grep -q 'Draft acceptance: `baseline`' "$R"; then echo "FAIL baseline reported acceptance"; fail=1; else echo "ok   no acceptance line for a config without spec decoding"; fi
check "$R" '^### `spec-mtp` — chat' "profiled configs get a profile section"
check "$R" '`fused_moe_kernel` | 3.0 | 75.0%' "profile ranks GPU kernels and ignores CPU ops"
check "$R" "^| \`baseline\` .*'MARLIN' NvFp4 MoE backend" "startup table lists the backends vLLM chose"
check "$R" '^| `variant-fp8` .*+FLASHINFER_TRTLLM Fp8 MoE backend' "other configs show only backends that differ"
check "$R" '`env-FAKE_SLOW_INIT-1`: engine init took 700 s' "engine init past 600 s is flagged"
check "$R" '\*\*`variant-fp8`\*\* wins 1/5 workloads (single_user +50.0%)' "the single-user workload runs and can be won"
check "$R" 'Loses: chat -10.0%' "a win that also loses elsewhere lists the losses"
check "$R" 'workload-dependent' "mixed wins are not recommended as defaults"
python3 - "$TMP/results/enforce-eager/result.json" <<'PY' && echo "ok   --workloads limits the benchmarks" || { echo "FAIL --workloads"; fail=1; }
import json, sys
assert list(json.load(open(sys.argv[1]))["workloads"]) == ["single_user"]
PY
[ "$fail" = 0 ] && echo "selftest PASS" || { echo "selftest FAIL — report at $R"; cat "$R"; exit 1; }
