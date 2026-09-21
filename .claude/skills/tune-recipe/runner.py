#!/usr/bin/env python3
"""Execute a /tune-recipe plan on the GPU box. Standard library only.

    python3 runner.py plan.json --out results/ [--only baseline,kv-fp8]
                      [--port 8000] [--ready-timeout 1800]

For each config: start `vllm serve`, wait for /health, score the arithmetic
probes, run `vllm bench serve` once per workload, stop the server. Every config
writes results/<name>/result.json; a config that already has one is skipped, so
re-running after an interruption resumes. A config that fails to start is
recorded as such and the sweep moves on.
"""

import argparse
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


def start_server(cfg, port, log_path):
    argv = [*cfg["argv"], "--port", str(port)]
    env = {**os.environ, **{k: str(v) for k, v in cfg["env"].items()}}
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
            text = r["choices"][0]["message"].get("content") or ""
        except (OSError, KeyError, ValueError) as e:
            return {"answer": p["answer"], "got": None, "error": str(e)}
        nums = re.findall(r"-?\d[\d,]*", text)
        got = int(nums[-1].replace(",", "")) if nums else None
        return {"answer": p["answer"], "got": got}

    with ThreadPoolExecutor(16) as ex:
        rows = list(ex.map(ask, probes))
    return {"correct": sum(r["got"] == r["answer"] for r in rows), "total": len(rows), "rows": rows}


def run_bench(cfg, w, port, model, out_dir):
    fname = f"bench-{w['name']}.json"
    cmd = [
        "vllm", "bench", "serve", "--backend", "vllm", "--model", model,
        "--port", str(port), "--dataset-name", "random",
        "--random-input-len", str(w["input_len"]), "--random-output-len", str(w["output_len"]),
        "--num-prompts", str(w["num_prompts"]), "--max-concurrency", str(w["concurrency"]),
        "--ignore-eos", "--seed", "0", "--percentile-metrics", "ttft,tpot,itl,e2el",
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
    proc, fh = start_server(cfg, args.port, out_dir / "server.log")
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
            result["workloads"][w["name"]] = run_bench(cfg, w, args.port, model, out_dir)
            if proc.poll() is not None:
                result.update(status="crashed", error=f"server exited {proc.returncode} during {w['name']}")
                break
    finally:
        stop_server(proc, fh)
        sampler.stop()
        result["peak_mem_mib"] = sampler.peak
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--out", default="results")
    ap.add_argument("--only", default="")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--ready-timeout", type=int, default=1800)
    args = ap.parse_args()

    plan = json.loads(Path(args.plan).read_text())
    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)
    env = environment(plan)
    (out_root / "env.json").write_text(json.dumps(env, indent=2))
    log(f"vllm {env['vllm']}, {len(env['gpus'])} GPU(s)")
    for w in env["warnings"]:
        log(f"WARNING: {w}")

    only = set(filter(None, args.only.split(",")))
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
