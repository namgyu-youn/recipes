#!/usr/bin/env python3
"""Turn a /tune-recipe results directory into report.md.

    python3 analyze.py <plan-dir>        # expects <plan-dir>/plan.json and <plan-dir>/results/

A config is only eligible to win if it started, completed every request and
scored within --tolerance probes of the baseline. A win needs to beat the
baseline by --noise percent: each workload runs once, so smaller gaps are noise.
"""

import argparse
import json
from pathlib import Path


def flag(argv, name, default=None):
    for i, a in enumerate(argv):
        if a == name and i + 1 < len(argv):
            return argv[i + 1]
        if a.startswith(name + "="):
            return a.split("=", 1)[1]
    return default


def gpus_used(argv):
    n = 1
    for f in ("--tensor-parallel-size", "--data-parallel-size", "--pipeline-parallel-size"):
        n *= int(flag(argv, f, 1))
    return n


def pct(new, old):
    if not new or not old:
        return None
    return (new - old) / old * 100


def fmt(v, digits=1):
    return "—" if v is None else f"{v:,.{digits}f}"


def fmt_delta(d):
    return "" if d is None else f" ({d:+.1f}%)"


# Where the winning change would go in the recipe YAML. Advice only: the
# tuner never edits a recipe.
def placement(cfg, plan):
    hw = plan["hardware"]
    if cfg["name"].startswith("strategy-"):
        return f"strategy choice — the Strategy row already offers `{cfg['strategy']}`; document it in the guide for {hw['id']} x{hw['count']}"
    if cfg["name"].startswith("spec-"):
        return "feature default — consider dropping `spec_decoding` from `opt_in_features` (or `default_mode`) only if every hardware shows the same gain"
    args = " ".join(cfg["extra_args"])
    if plan["variant"] == "default":
        return f"`{args}` — recipe `hardware_overrides.{hw['generation']}.extra_args` covers the whole generation; only with evidence from more than {hw['id']}"
    return f"`{args}` — `variants.{plan['variant']}.hardware_overrides.{hw['id']}.extra_args`"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan_dir")
    ap.add_argument("--tolerance", type=int, default=2, help="probes a config may lose vs baseline")
    ap.add_argument("--noise", type=float, default=3.0, help="minimum %% gain that counts as a win")
    args = ap.parse_args()

    root = Path(args.plan_dir)
    plan = json.loads((root / "plan.json").read_text())
    res_dir = root / "results"
    env = json.loads((res_dir / "env.json").read_text()) if (res_dir / "env.json").exists() else {}
    results = {}
    for cfg in plan["configs"]:
        p = res_dir / cfg["name"] / "result.json"
        if p.exists():
            results[cfg["name"]] = json.loads(p.read_text())

    base = results.get("baseline")
    if not base or base["status"] != "ok":
        raise SystemExit("baseline did not run successfully — nothing to compare against")
    base_acc = base["accuracy"]["correct"]

    def gate(name):
        r = results.get(name)
        if not r:
            return "not run"
        if r["status"] != "ok":
            return r["status"]
        if any((w.get("failed") or 0) > 0 or "error" in w for w in r["workloads"].values()):
            return "requests failed"
        if r["accuracy"]["correct"] < base_acc - args.tolerance:
            return f"accuracy {r['accuracy']['correct']}/{r['accuracy']['total']} vs baseline {base_acc}"
        return "pass"

    hw = plan["hardware"]
    lines = [
        f"# Tuning — {plan['hf_id']} [{plan['variant']}] on {hw['id']} x{hw['count']}",
        "",
        f"vLLM `{env.get('vllm')}` · GPUs: {', '.join(sorted(set(env.get('gpus', [])))) or 'unknown'}"
        f" · recipe floor {plan['min_vllm_version']} · plan {plan['created'][:16]}",
        "",
        f"One run per workload; wins below {args.noise}% are treated as noise. "
        f"Accuracy is {len(plan['probes'])} arithmetic probes; a config may lose at most {args.tolerance} vs baseline.",
        "",
    ]
    for w in plan.get("warnings", []) + env.get("warnings", []):
        lines += [f"> ⚠ {w}", ""]

    lines += ["## Configs", "", "| Config | Change | GPUs | Startup | Peak mem | Probes | Gate |", "|---|---|---|---|---|---|---|"]
    by_name = {c["name"]: c for c in plan["configs"]}
    for cfg in plan["configs"]:
        r = results.get(cfg["name"], {})
        acc = r.get("accuracy")
        lines.append(
            f"| `{cfg['name']}` | {cfg['why']} | {gpus_used(cfg['argv'])} | {fmt(r.get('startup_s'), 0) + 's' if r.get('startup_s') else '—'}"
            f" | {fmt(r['peak_mem_mib'] / 1024) + ' GiB' if r.get('peak_mem_mib') else '—'}"
            f" | {'%d/%d' % (acc['correct'], acc['total']) if acc else '—'} | {gate(cfg['name'])} |"
        )

    wins = {}
    for w in plan["workloads"]:
        name = w["name"]
        b = base["workloads"].get(name, {})
        lines += [
            "", f"## {name} — {w['input_len']} in / {w['output_len']} out, concurrency {w['concurrency']}", "",
            "| Config | Output tok/s | per GPU | TTFT p50 ms | TPOT p50 ms | TTFT p99 ms |", "|---|---|---|---|---|---|",
        ]
        best, best_gain = None, args.noise
        for cfg in plan["configs"]:
            r = results.get(cfg["name"])
            m = (r or {}).get("workloads", {}).get(name)
            if not m or "error" in m:
                continue
            g = gpus_used(cfg["argv"])
            tput = m.get("output_throughput")
            d = pct(tput, b.get("output_throughput"))
            per_gpu_d = pct(tput / g if tput else None, (b.get("output_throughput") or 0) / gpus_used(by_name["baseline"]["argv"]))
            lines.append(
                f"| `{cfg['name']}` | {fmt(tput)}{fmt_delta(d if cfg['name'] != 'baseline' else None)}"
                f" | {fmt(tput / g if tput else None)}{fmt_delta(per_gpu_d if cfg['name'] != 'baseline' else None)}"
                f" | {fmt(m.get('median_ttft_ms'))} | {fmt(m.get('median_tpot_ms'), 2)} | {fmt(m.get('p99_ttft_ms'))} |"
            )
            if cfg["name"] != "baseline" and gate(cfg["name"]) == "pass" and d is not None and d > best_gain:
                best, best_gain = cfg["name"], d
        if best:
            wins.setdefault(best, []).append((name, best_gain))
            lines += ["", f"Best: `{best}`, {best_gain:+.1f}% output tok/s over baseline."]
        else:
            lines += ["", "No eligible config beats the baseline beyond noise."]

    lines += ["", "## Verdict", ""]
    if not wins:
        lines.append("Keep the recipe as is: no change beats the baseline on any workload beyond noise.")
    for name, ws in sorted(wins.items(), key=lambda kv: -len(kv[1])):
        cfg = by_name[name]
        where = ", ".join(f"{w} {g:+.1f}%" for w, g in ws)
        lines += [
            f"- **`{name}`** wins {len(ws)}/{len(plan['workloads'])} workloads ({where}).",
            f"  - Placement: {placement(cfg, plan)}.",
        ]
        if gpus_used(cfg["argv"]) != gpus_used(by_name["baseline"]["argv"]):
            lines.append("  - Uses a different GPU count than the baseline — compare the per-GPU column before adopting.")
    lines += [
        "",
        "Before editing a recipe: re-run the winner and the baseline (`runner.py --only`) to confirm the gap, "
        "and never change `meta.hardware` / verified badges from a tuning run alone.",
        "",
    ]
    (root / "report.md").write_text("\n".join(lines))
    print(f"report: {root / 'report.md'}")


if __name__ == "__main__":
    main()
