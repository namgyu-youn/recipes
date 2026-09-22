#!/usr/bin/env python3
"""Execute a /tune-recipe plan on the GPU box. Standard library only.

    python3 runner.py plan.json --out results/ [--only baseline,kv-fp8]
                      [--port 8000] [--ready-timeout 1800]
    python3 runner.py plan.json --out results/ --only baseline,<cfg> --profile chat

For each config: start `vllm serve`, wait for /health, score the arithmetic
probes, run `vllm bench serve` once per workload, stop the server. Every config
writes results/<name>/result.json; a config that already has one is skipped, so
re-running after an interruption resumes. A config that fails to start is
recorded as such and the sweep moves on.

--profile <workload> is a separate pass: each --only config is restarted with
the torch profiler, a short run of that workload is traced, and the top GPU
kernels land in results/<name>/profile-<workload>.json. Profiler overhead skews
timing, so these runs never feed the throughput tables.
"""

import argparse
import gzip
import importlib.util
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BENCH_KEYS = (
    "completed", "failed", "duration", "request_throughput", "output_throughput",
    "total_token_throughput", "median_ttft_ms", "p99_ttft_ms", "median_tpot_ms",
    "p99_tpot_ms", "median_itl_ms", "p99_itl_ms", "median_e2el_ms",
)

SPEC_COUNTERS = ("num_drafts", "num_draft_tokens", "num_accepted_tokens")
SPEC_BENCH_URL = "https://raw.githubusercontent.com/hemingkx/Spec-Bench/refs/heads/main/data/spec_bench/question.jsonl"


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def http_json(url, payload=None, timeout=10):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read() or b"null")


def gpu_mem_used_mib():
    if not shutil.which("nvidia-smi"):
        return None
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10,
        )
        return sum(int(x) for x in r.stdout.split()) if r.returncode == 0 else None
    except (subprocess.SubprocessError, ValueError):
        return None


class MemSampler(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.peak = None
        self._halt = threading.Event()

    def run(self):
        while not self._halt.is_set():
            used = gpu_mem_used_mib()
            if used is not None:
                self.peak = max(self.peak or 0, used)
            self._halt.wait(2)

    def stop(self):
        self._halt.set()


def environment(plan):
    env = {"python": sys.version.split()[0]}
    try:
        env["vllm"] = subprocess.run(
            ["vllm", "--version"], capture_output=True, text=True, timeout=120
        ).stdout.strip().splitlines()[-1]
    except (OSError, subprocess.SubprocessError, IndexError):
        env["vllm"] = None
    env["gpus"] = []
    if shutil.which("nvidia-smi"):
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"],
            capture_output=True, text=True,
        )
        if r.returncode == 0:
            env["gpus"] = r.stdout.strip().splitlines()
    want = plan["hardware"]["count"]
    env["warnings"] = []
    if env["gpus"] and len(env["gpus"]) < want:
        env["warnings"].append(f"plan needs {want} GPUs, box has {len(env['gpus'])}")
    return env


def start_server(cfg, port, log_path, ready_timeout):
    argv = [*cfg["argv"], "--port", str(port)]
    # A cold compile on a fresh box can outlast the frontend's own 600 s wait
    # for the engine; let wait_ready's timeout be the only one.
    env = {**os.environ, "VLLM_ENGINE_READY_TIMEOUT_S": str(ready_timeout),
           **{k: str(v) for k, v in cfg["env"].items()}}
    fh = open(log_path, "w")
    fh.write(f"# {' '.join(argv)}\n# env: {cfg['env']}\n")
    fh.flush()
    proc = subprocess.Popen(argv, env=env, stdout=fh, stderr=subprocess.STDOUT, start_new_session=True)
    return proc, fh


def wait_ready(proc, port, timeout):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if proc.poll() is not None:
            return False, f"server exited with code {proc.returncode}"
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=5)
            return True, round(time.time() - t0, 1)
        except OSError:
            time.sleep(5)
    return False, f"not ready after {timeout}s"


def stop_server(proc, fh):
    if proc.poll() is None:
        try:
            os.killpg(proc.pid, signal.SIGINT)
            proc.wait(timeout=60)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
        except ProcessLookupError:
            pass
    fh.close()
    # Let the driver release memory before the next config measures its peak.
    for _ in range(60):
        used = gpu_mem_used_mib()
        if used is None or used < 2048:
            break
        time.sleep(2)


def post(url, timeout):
    urllib.request.urlopen(urllib.request.Request(url, data=b"", method="POST"), timeout=timeout).read()


def spec_counters(port):
    """Cumulative spec-decode counters from /metrics (both frontends export
    the same names), or None when the server has no spec decoding."""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/metrics", timeout=10) as r:
            text = r.read().decode()
    except OSError:
        return None
    out, per_pos = {}, {}
    for line in text.splitlines():
        m = re.match(r"vllm:spec_decode_(num_\w+?)(?:_total)?(\{[^}]*\})?\s+(\S+)$", line)
        if not m:
            continue
        name, labels, val = m.group(1), m.group(2) or "", float(m.group(3))
        if name == "num_accepted_tokens_per_pos":
            pos = re.search(r'position="(\d+)"', labels)
            if pos:
                per_pos[int(pos.group(1))] = per_pos.get(int(pos.group(1)), 0) + val
        elif name in SPEC_COUNTERS:
            out[name] = out.get(name, 0) + val
    if not out:
        return None
    out["per_pos"] = per_pos
    return out


def spec_delta(before, after):
    """Draft acceptance over one workload, from counters scraped around it."""
    if not before or not after:
        return None
    d = {k: after.get(k, 0) - before.get(k, 0) for k in SPEC_COUNTERS}
    if not d["num_drafts"] or not d["num_draft_tokens"]:
        return None
    return {
        "acceptance_rate": d["num_accepted_tokens"] / d["num_draft_tokens"],
        "mean_acceptance_length": 1 + d["num_accepted_tokens"] / d["num_drafts"],
        "per_position": [
            (after["per_pos"][i] - before["per_pos"].get(i, 0)) / d["num_drafts"]
            for i in sorted(after["per_pos"])
        ],
    }


def top_kernels(trace_dir, n=15):
    """GPU time per kernel name, summed over the torch-profiler traces."""
    totals = {}
    for path in Path(trace_dir).rglob("*.json.gz"):
        with gzip.open(path, "rt") as fh:
            for e in json.load(fh).get("traceEvents", []):
                if e.get("cat") == "kernel":
                    totals[e["name"]] = totals.get(e["name"], 0) + e.get("dur", 0)
    gpu_us = sum(totals.values())
    if not gpu_us:
        return None
    top = sorted(totals.items(), key=lambda kv: -kv[1])[:n]
    return {
        "gpu_ms": round(gpu_us / 1000, 1),
        "kernels": [{"name": k, "ms": round(v / 1000, 2), "share": v / gpu_us} for k, v in top],
    }


def wait_for_traces(trace_dir, timeout=600):
    """Traces are written after /stop_profile returns; wait until their size settles."""
    last, t0 = None, time.time()
    while time.time() - t0 < timeout:
        sizes = sorted((p.name, p.stat().st_size) for p in Path(trace_dir).rglob("*.json.gz"))
        if sizes and sizes == last:
            return
        last = sizes
        time.sleep(10)


def served_model(port):
    return http_json(f"http://127.0.0.1:{port}/v1/models")["data"][0]["id"]


def score_probes(port, model, probes):
    def ask(p):
        try:
            r = http_json(
                f"http://127.0.0.1:{port}/v1/chat/completions",
                {"model": model, "messages": [{"role": "user", "content": p["prompt"]}],
                 "temperature": 0, "max_tokens": 4096},
                timeout=600,
            )
            choice = r["choices"][0]
            msg = choice["message"]
            # A reasoning parser moves thinking out of `content`; if the answer
            # never left it (or the budget ran out), read the reasoning instead.
            text = msg.get("content") or msg.get("reasoning") or msg.get("reasoning_content") or ""
        except (OSError, KeyError, ValueError) as e:
            return {"answer": p["answer"], "got": None, "error": str(e)}
        nums = re.findall(r"-?\d[\d,]*", text)
        got = int(nums[-1].replace(",", "")) if nums else None
        return {"answer": p["answer"], "got": got, "truncated": choice.get("finish_reason") == "length"}

    with ThreadPoolExecutor(16) as ex:
        rows = list(ex.map(ask, probes))
    return {
        "correct": sum(r["got"] == r["answer"] for r in rows),
        "total": len(rows),
        "truncated": sum(bool(r.get("truncated")) for r in rows),
        "rows": rows,
    }


def run_bench(cfg, w, port, model, out_dir, spec_bench_path):
    fname = f"bench-{w['name']}.json"
    cmd = ["vllm", "bench", "serve", "--model", model, "--port", str(port)]
    if w.get("dataset") == "spec_bench":
        # Real chat prompts, no --ignore-eos: text after EOS is degenerate and
        # would inflate draft acceptance.
        cmd += [
            "--backend", "openai-chat", "--endpoint", "/v1/chat/completions",
            "--dataset-name", "spec_bench", "--dataset-path", str(spec_bench_path),
            "--spec-bench-output-len", str(w["output_len"]),
        ]
    else:
        cmd += [
            "--backend", "vllm", "--dataset-name", "random", "--ignore-eos",
            "--random-input-len", str(w["input_len"]), "--random-output-len", str(w["output_len"]),
        ]
    cmd += [
        "--num-prompts", str(w["num_prompts"]), "--max-concurrency", str(w["concurrency"]),
        "--seed", "0", "--percentile-metrics", "ttft,tpot,itl,e2el",
        "--save-result", "--result-dir", str(out_dir), "--result-filename", fname,
    ]
    if "--trust-remote-code" in cfg["argv"]:
        cmd.append("--trust-remote-code")
    with open(out_dir / f"bench-{w['name']}.log", "w") as fh:
        rc = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT).returncode
    path = out_dir / fname
    if rc != 0 or not path.exists():
        return {"error": f"bench exited {rc}"}
    data = json.loads(path.read_text())
    return {k: data.get(k) for k in BENCH_KEYS}


def run_config(cfg, plan, args, out_root):
    out_dir = out_root / cfg["name"]
    out_dir.mkdir(parents=True, exist_ok=True)
    result = {"name": cfg["name"], "status": "ok", "workloads": {}}
    log(f"{cfg['name']}: starting server")
    sampler = MemSampler()
    sampler.start()
    proc, fh = start_server(cfg, args.port, out_dir / "server.log", args.ready_timeout)
    try:
        ok, info = wait_ready(proc, args.port, args.ready_timeout)
        if not ok:
            tail = (out_dir / "server.log").read_text(errors="replace").splitlines()[-40:]
            result.update(status="start_failed", error=info, log_tail=tail)
            log(f"{cfg['name']}: {info}")
            return result
        result["startup_s"] = info
        model = served_model(args.port)
        log(f"{cfg['name']}: ready in {info}s, scoring {len(plan['probes'])} probes")
        result["accuracy"] = score_probes(args.port, model, plan["probes"])
        for w in plan["workloads"]:
            log(f"{cfg['name']}: bench {w['name']}")
            before = spec_counters(args.port)
            result["workloads"][w["name"]] = run_bench(cfg, w, args.port, model, out_dir, out_root / "spec_bench.jsonl")
            spec = spec_delta(before, spec_counters(args.port))
            if spec:
                result["workloads"][w["name"]]["spec"] = spec
            if proc.poll() is not None:
                result.update(status="crashed", error=f"server exited {proc.returncode} during {w['name']}")
                break
    finally:
        stop_server(proc, fh)
        sampler.stop()
        result["peak_mem_mib"] = sampler.peak
    return result


def profile_config(cfg, w, args, out_root):
    out_dir = out_root / cfg["name"] / "profile"
    trace_dir = (out_dir / "traces").resolve()
    trace_dir.mkdir(parents=True, exist_ok=True)
    # Skip warm-up iterations, then trace a short steady-state window.
    prof = {
        "profiler": "torch", "torch_profiler_dir": str(trace_dir), "ignore_frontend": True,
        "torch_profiler_with_stack": False, "delay_iterations": 20, "max_iterations": 30,
    }
    run_cfg = dict(cfg, argv=[*cfg["argv"], "--profiler-config", json.dumps(prof)])
    log(f"{cfg['name']}: starting server with profiler")
    proc, fh = start_server(run_cfg, args.port, out_dir / "server.log", args.ready_timeout)
    try:
        ok, info = wait_ready(proc, args.port, args.ready_timeout)
        if not ok:
            return {"name": cfg["name"], "status": "start_failed", "error": info}
        model = served_model(args.port)
        post(f"http://127.0.0.1:{args.port}/start_profile", 60)
        log(f"{cfg['name']}: tracing {w['name']}")
        bench = run_bench(cfg, dict(w, num_prompts=w["concurrency"] * 2), args.port, model, out_dir, out_root / "spec_bench.jsonl")
        post(f"http://127.0.0.1:{args.port}/stop_profile", 600)
        wait_for_traces(trace_dir)
        kernels = top_kernels(trace_dir) or {"error": "no kernel events in the trace"}
        return {"name": cfg["name"], "status": "ok", "workload": w["name"], "bench": bench, **kernels}
    finally:
        stop_server(proc, fh)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--out", default="results")
    ap.add_argument("--only", default="")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--ready-timeout", type=int, default=1800)
    ap.add_argument("--profile", metavar="WORKLOAD", help="trace this workload for each --only config")
    args = ap.parse_args()

    plan = json.loads(Path(args.plan).read_text())
    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)
    env = environment(plan)
    (out_root / "env.json").write_text(json.dumps(env, indent=2))
    log(f"vllm {env['vllm']}, {len(env['gpus'])} GPU(s)")
    for w in env["warnings"]:
        log(f"WARNING: {w}")

    spec_bench = out_root / "spec_bench.jsonl"
    if any(w.get("dataset") == "spec_bench" for w in plan["workloads"]):
        # `vllm bench` reads Spec-Bench with pandas, which only vllm[bench] installs.
        if importlib.util.find_spec("pandas") is None:
            sys.exit('the spec_text workload needs pandas: uv pip install "vllm[bench]"')
    if any(w.get("dataset") == "spec_bench" for w in plan["workloads"]) and not spec_bench.exists():
        try:
            urllib.request.urlretrieve(SPEC_BENCH_URL, spec_bench)
        except OSError as e:
            sys.exit(f"could not fetch Spec-Bench prompts ({e}); place question.jsonl at {spec_bench}")

    only = set(filter(None, args.only.split(",")))
    if args.profile:
        w = next((w for w in plan["workloads"] if w["name"] == args.profile), None)
        if not w or not only:
            sys.exit("--profile needs a workload from the plan and --only <configs>")
        for cfg in plan["configs"]:
            done = out_root / cfg["name"] / f"profile-{w['name']}.json"
            if cfg["name"] not in only or done.exists():
                continue
            result = profile_config(cfg, w, args, out_root)
            done.write_text(json.dumps(result, indent=2))
            log(f"{cfg['name']}: profile {result['status']}")
        log("profiling finished")
        return

    for cfg in plan["configs"]:
        if only and cfg["name"] not in only:
            continue
        done = out_root / cfg["name"] / "result.json"
        if done.exists():
            log(f"{cfg['name']}: already done, skipping")
            continue
        result = run_config(cfg, plan, args, out_root)
        done.write_text(json.dumps(result, indent=2))
        log(f"{cfg['name']}: {result['status']}")
    log("sweep finished")


if __name__ == "__main__":
    main()
