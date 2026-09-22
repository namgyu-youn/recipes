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
  --candidates --moe-backend=BROKEN,--linear-backend=b12x --out "$TMP" >/dev/null

# The recipe already sets --kv-cache-dtype fp8 here, so the knob is absent.
# Add one fp8-KV config by hand so the accuracy gate has something to reject.
python3 - "$TMP/plan.json" <<'EOF'
import json, sys
p = json.load(open(sys.argv[1]))
p["configs"] = [c for c in p["configs"] if c["name"] in
                ("baseline", "spec-mtp", "moe-backend-BROKEN", "linear-backend-b12x", "mnseqs-32")]
for c in p["configs"]:
    c["argv"] = [a if a != "fp8" else "auto" for a in c["argv"]]
bad = dict(p["configs"][0], name="kv-fp8", why="fp8 KV", extra_args=["--kv-cache-dtype", "fp8"])
bad["argv"] = [a if a != "auto" else "fp8" for a in p["configs"][0]["argv"]]
p["configs"].append(bad)
m32 = next(c for c in p["configs"] if c["name"] == "mnseqs-32")
m64 = dict(m32, name="mnseqs-64", why="max-num-seqs 64", extra_args=["--max-num-seqs", "64"])
m64["argv"] = [a if a != "32" else "64" for a in m32["argv"]]
p["configs"].append(m64)
p["probes"] = p["probes"][:8]
json.dump(p, open(sys.argv[1], "w"))
EOF

# Offline stand-in for the Spec-Bench download.
mkdir -p "$TMP/results" && echo '{"category": "writing", "turns": ["Write a haiku."]}' >"$TMP/results/spec_bench.jsonl"
PATH="$HERE:$PATH" python3 "$SKILL/runner.py" "$TMP/plan.json" --out "$TMP/results" --port 18123 --ready-timeout 30 >"$TMP/run.log"
# Second run must resume, not re-run.
PATH="$HERE:$PATH" python3 "$SKILL/runner.py" "$TMP/plan.json" --out "$TMP/results" --port 18123 >>"$TMP/run.log"
python3 "$SKILL/analyze.py" "$TMP" >/dev/null

fail=0
check() { if grep -q -- "$2" "$1"; then echo "ok   $3"; else echo "FAIL $3"; fail=1; fi; }
R="$TMP/report.md"
check "$R" '`moe-backend-BROKEN`.*start_failed' "startup failure is recorded, sweep continues"
check "$R" '`kv-fp8`.*accuracy 4/8' "accuracy gate rejects a config that loses probes"
check "$R" '`linear-backend-b12x`.*| pass |' "a sub-noise config passes the gate"
check "$R" '\*\*`mnseqs-32`\*\* wins 4/4' "the real +20% win is the verdict"
check "$R" '`mnseqs-64`.*slower decode' "a throughput gain with +50% TPOT is flagged"
if grep -q 'mnseqs-64`\*\* wins' "$R"; then echo "FAIL TPOT regression counted as a win"; fail=1; else echo "ok   TPOT regression is not a win"; fi
check "$R" '^## spec_text — Spec-Bench' "spec configs add a real-text workload"
check "$R" 'baseline caps --max-num-seqs at 8' "queueing baseline is warned about"
check "$R" '`baseline`.*| 8/8' "probe answers are read from reasoning when content is empty"
if grep -q 'linear-backend-b12x`\*\* wins' "$R"; then echo "FAIL +1% counted as a win"; fail=1; else echo "ok   +1% stays inside the noise floor"; fi
check "$TMP/run.log" 'already done, skipping' "re-run resumes from result.json"
[ "$fail" = 0 ] && echo "selftest PASS" || { echo "selftest FAIL — report at $R"; cat "$R"; exit 1; }
