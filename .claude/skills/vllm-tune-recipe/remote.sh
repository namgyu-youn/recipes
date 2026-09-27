#!/usr/bin/env bash
# Drive runner.py on a rented box over SSH. Run from the repo root.
#
#   remote.sh <user@host> <port> start  <plan-dir> [runner args...]
#   remote.sh <user@host> <port> status <plan-dir>
#   remote.sh <user@host> <port> watch  <plan-dir>   # one line per new log line; exits when the run ends
#   remote.sh <user@host> <port> pull   <plan-dir>
#   remote.sh <user@host> <port> stop   <plan-dir>
#
# start queues behind any runner already going on the box, so several plans
# can be started back to back. TUNE_VENV (default /root/venv) is activated
# first when it exists.
set -euo pipefail

host=$1 port=$2 cmd=$3 dir=${4%/}
shift 4 || true
rdir="tune/$(basename "$dir")"
venv=${TUNE_VENV:-/root/venv}
here=$(cd "$(dirname "$0")" && pwd)
r() { ssh -o ConnectTimeout=15 -o BatchMode=yes -p "$port" "$host" "$@"; }

case $cmd in
start)
  r "mkdir -p $rdir"
  scp -q -P "$port" "$here/runner.py" "$dir/plan.json" "$host:$rdir/"
  # setsid -f detaches fully, so this ssh returns at once. Wait on the runner
  # process itself (^python3): waiting shells, this one and other queued ones,
  # also carry "runner.py plan.json" in their command lines.
  r "cd $rdir && setsid -f sh -c '[ -f $venv/bin/activate ] && . $venv/bin/activate;
      while pgrep -f \"^python3 runner.py plan.json\" >/dev/null; do sleep 30; done;
      python3 runner.py plan.json --out results $*' >> sweep.log 2>&1 < /dev/null"
  echo "started $rdir (log: $rdir/sweep.log)"
  ;;
status)
  r "tail -5 $rdir/sweep.log; pgrep -af '[r]unner.py|[v]llm serve' | cut -c1-120 || true;
     nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader 2>/dev/null"
  ;;
watch)
  # grep -c prints 0 and exits 1 on an empty log; don't add a second 0.
  n=$(r "grep -c . $rdir/sweep.log 2>/dev/null" || true)
  n=${n:-0}
  while true; do
    out=$(r "grep . $rdir/sweep.log; pgrep -f '[r]unner.py' >/dev/null || echo __IDLE__" 2>&1) || { echo "ssh failed"; sleep 60; continue; }
    body=$(echo "$out" | grep -v __IDLE__ || true)
    t=$(echo "$body" | grep -c . || true)
    if [ "$t" -gt "$n" ]; then echo "$body" | tail -n +$((n + 1)); n=$t; fi
    if echo "$out" | grep -q __IDLE__; then echo "runner idle"; break; fi
    sleep 60
  done
  ;;
pull)
  mkdir -p "$dir"
  scp -q -r -P "$port" "$host:$rdir/results" "$dir/"
  echo "pulled $dir/results"
  ;;
stop)
  r "pkill -f '[r]unner.py plan.json' || true; pkill -INT -f '[v]llm serve' || true"
  ;;
*)
  echo "unknown command $cmd" >&2
  exit 2
  ;;
esac
