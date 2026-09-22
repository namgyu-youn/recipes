#!/usr/bin/env python3
"""Turn a /tune-recipe results directory into report.md.

    python3 analyze.py <plan-dir>        # expects <plan-dir>/plan.json and <plan-dir>/results/

A config is only eligible to win if it started, completed every request and
scored within --tolerance probes of the baseline. A win needs to beat the
baseline by --noise percent: each workload runs once, so smaller gaps are noise.
It must also keep E2E latency p50 within --latency percent of the baseline,
so a throughput gain bought with slower requests is not a win. E2E, not TPOT:
when the baseline queues (--max-num-seqs below concurrency), TPOT only times
the requests that got a slot, and a config that removes the queue looks slower.
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
def placement(cfg, plan, mixed):
    hw = plan["hardware"]
    if mixed:
        return ("workload-dependent — it also loses on some workloads, so keep the recipe default and "
                f"say in the guide when to turn it on for {hw['id']}")
    if cfg["name"].startswith("variant-"):
        return f"variant choice — note in the guide that `{cfg['variant']}` is the faster checkpoint on {hw['id']}"
    if cfg["name"].startswith("strategy-"):
        return f"strategy choice — the Strategy row already offers `{cfg['strategy']}`; document it in the guide for {hw['id']} x{hw['count']}"
    if cfg["name"].startswith("spec-"):
        return "feature default — consider dropping `spec_decoding` from `opt_in_features` (or `default_mode`) only if every hardware shows the same gain"
    if cfg.get("extra_env"):
        env = " ".join(f"{k}={v}" for k, v in cfg["extra_env"].items())
        return f"`{env}` — `variants.{plan['variant']}.hardware_overrides.{hw['id']}.extra_env`"
    if not cfg.get("extra_args"):
        return f"not a flag change ({cfg['why']}) — no recipe placement; report it where that change lives"
    args = " ".join(cfg["extra_args"])
    if plan["variant"] == "default":
        return f"`{args}` — recipe `hardware_overrides.{hw['generation']}.extra_args` covers the whole generation; only with evidence from more than {hw['id']}"
    return f"`{args}` — `variants.{plan['variant']}.hardware_overrides.{hw['id']}.extra_args`"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan_dir")
    ap.add_argument("--tolerance", type=int, default=2, help="probes a config may lose vs baseline")
    ap.add_argument("--noise", type=float, default=3.0, help="minimum %% gain that counts as a win")
    ap.add_argument("--latency", type=float, default=10.0, help="maximum %% E2E latency p50 regression a win may carry")
    ap.add_argument("--gsm8k-tolerance", type=float, default=2.0,
                    help="GSM8K points a config may lose vs baseline (when runner.py ran --gsm8k)")
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
        g, bg = r.get("gsm8k"), base.get("gsm8k")
        if g and bg and (bg["accuracy"] - g["accuracy"]) * 100 > args.gsm8k_tolerance:
            return f"gsm8k {g['accuracy']:.1%} vs baseline {bg['accuracy']:.1%}"
        return "pass"

    hw = plan["hardware"]
    lines = [
        f"# Tuning — {plan['hf_id']} [{plan['variant']}] on {hw['id']} x{hw['count']}",
        "",
        f"vLLM `{env.get('vllm')}` · GPUs: {', '.join(sorted(set(env.get('gpus', [])))) or 'unknown'}"
        f" · recipe floor {plan['min_vllm_version']} · plan {plan['created'][:16]}",
        "",
        f"One run per workload; wins below {args.noise}% are treated as noise. "
        f"A win must keep E2E latency p50 within +{args.latency}% of baseline. "
        f"Accuracy is {len(plan['probes'])} arithmetic probes; a config may lose at most {args.tolerance} vs baseline.",
        "",
    ]
    # Weight-only labels on layers that ship activation scales: vLLM follows
    # the label, so a checkpoint can run slower than its tensors allow.
    ckpt_warnings = {}
    for r in results.values():
        c = r.get("checkpoint") or {}
        if c.get("a16_layers_with_input_scale"):
            ckpt_warnings[c["dir"]] = (
                f"`{c['dir']}`: {c['a16_layers_with_input_scale']} of {c['a16_layers']} layers labeled W4A16 "
                "(weight-only) ship activation `input_scale`s — vLLM runs them on weight-only kernels. "
                "If the model card says activations are quantized, a relabeled copy may run on native kernels; test it with --gsm8k.")
    for w in plan.get("warnings", []) + env.get("warnings", []) + list(ckpt_warnings.values()):
        lines += [f"> ⚠ {w}", ""]

    lines += ["## Configs", "", "| Config | Change | GPUs | Startup | Peak mem | Probes | GSM8K | Gate |", "|---|---|---|---|---|---|---|---|"]
    by_name = {c["name"]: c for c in plan["configs"]}
    for cfg in plan["configs"]:
        r = results.get(cfg["name"], {})
        acc = r.get("accuracy")
        lines.append(
            f"| `{cfg['name']}` | {cfg['why']} | {gpus_used(cfg['argv'])} | {fmt(r.get('startup_s'), 0) + 's' if r.get('startup_s') else '—'}"
            f" | {fmt(r['peak_mem_mib'] / 1024) + ' GiB' if r.get('peak_mem_mib') else '—'}"
            f" | {'%d/%d' % (acc['correct'], acc['total']) if acc else '—'}"
            f"{' (%d cut)' % acc['truncated'] if acc and acc.get('truncated') else ''}"
            f" | {'%.1f%% (%d/%d)' % (r['gsm8k']['accuracy'] * 100, r['gsm8k']['correct'], r['gsm8k']['total']) if r.get('gsm8k') else '—'}"
            f" | {gate(cfg['name'])} |"
        )

    base_cfg = by_name["baseline"]
    base_backends = set(base.get("backends") or [])
    lines += ["", "## Startup and kernels", "",
              "What vLLM logged while starting each config: engine init, per-model warmup runs, and the backends it chose.",
              "", "| Config | Startup | Engine init | Warmup runs | Backends |", "|---|---|---|---|---|"]
    slow_starts = []
    for cfg in plan["configs"]:
        r = results.get(cfg["name"]) or {}
        if "startup_s" not in r:
            continue
        st = r.get("startup") or {}
        runs = st.get("warmup_run_s")
        runs = " + ".join(f"{x:,.0f}s" for x in (runs if isinstance(runs, list) else [runs])) if runs else "—"
        bk = r.get("backends") or []
        if cfg["name"] != "baseline":
            bk = [f"+{b}" for b in bk if b not in base_backends] or ["same as baseline"]
        init = st.get("engine_init_s")
        lines.append(f"| `{cfg['name']}` | {r['startup_s']:,.0f}s | {f'{init:,.0f}s' if init else '—'} | {runs} | {'; '.join(bk) or '—'} |")
        # vLLM's frontend waits VLLM_ENGINE_READY_TIMEOUT_S (600 s) for the engine;
        # the runner raises it, the site's command does not.
        if (init or 0) > 600 and "VLLM_ENGINE_READY_TIMEOUT_S" not in cfg["env"]:
            slow_starts.append((cfg["name"], init))
    for name, init in slow_starts:
        lines += ["", f"> ⚠ `{name}`: engine init took {init:,.0f} s, past vLLM's default 600 s engine-ready wait — "
                  "the site's command fails on a launch like this one (usually the first on a machine, before caches fill)."]

    wins, losses = {}, {}
    for w in plan["workloads"]:
        name = w["name"]
        if not any(name in (r.get("workloads") or {}) for r in results.values()):
            continue  # skipped with runner.py --workloads
        b = base["workloads"].get(name, {})
        source = "Spec-Bench prompts" if w.get("dataset") == "spec_bench" else f"{w['input_len']} in"
        lines += [
            "", f"## {name} — {source} / {w['output_len']} out, concurrency {w['concurrency']}", "",
            "| Config | Output tok/s | per GPU | TTFT p50 ms | TPOT p50 ms | E2E p50 ms | TTFT p99 ms |", "|---|---|---|---|---|---|---|",
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
            is_base = cfg["name"] == "baseline"
            tpot_d = pct(m.get("median_tpot_ms"), b.get("median_tpot_ms"))
            e2el_d = pct(m.get("median_e2el_ms"), b.get("median_e2el_ms"))
            slow = e2el_d is not None and e2el_d > args.latency
            lines.append(
                f"| `{cfg['name']}` | {fmt(tput)}{fmt_delta(d if not is_base else None)}"
                f" | {fmt(tput / g if tput else None)}{fmt_delta(per_gpu_d if not is_base else None)}"
                f" | {fmt(m.get('median_ttft_ms'))} | {fmt(m.get('median_tpot_ms'), 2)}{fmt_delta(tpot_d if not is_base else None)}"
                f" | {fmt(m.get('median_e2el_ms'), 0)}{fmt_delta(e2el_d if not is_base else None)}"
                f"{' ⚠ slower requests' if slow and not is_base else ''} | {fmt(m.get('p99_ttft_ms'))} |"
            )
            if not is_base and gate(cfg["name"]) == "pass" and not slow and d is not None and d > best_gain:
                best, best_gain = cfg["name"], d
            if not is_base and gate(cfg["name"]) == "pass" and d is not None and (d < -args.noise or slow):
                losses.setdefault(cfg["name"], []).append((name, d, e2el_d))
        accept = [
            f"`{c['name']}` {m['spec']['acceptance_rate']:.1%} (mean length {m['spec']['mean_acceptance_length']:.2f};"
            f" per position {' / '.join(f'{x:.2f}' for x in m['spec']['per_position'])})"
            for c in plan["configs"]
            if (m := (results.get(c["name"]) or {}).get("workloads", {}).get(name, {})).get("spec")
        ]
        if accept:
            lines += ["", "Draft acceptance: " + "; ".join(accept) + "."]
        if best:
            wins.setdefault(best, []).append((name, best_gain))
            lines += ["", f"Best: `{best}`, {best_gain:+.1f}% output tok/s over baseline."]
        else:
            lines += ["", "No eligible config beats the baseline beyond noise."]

    profiles = sorted(res_dir.glob("*/profile-*.json"))
    if profiles:
        lines += [
            "", "## Profiles", "",
            "Separate traced runs (torch profiler, 30 steady-state iterations); not part of the numbers above.",
        ]
        for path in profiles:
            prof = json.loads(path.read_text())
            lines += ["", f"### `{prof['name']}` — {prof.get('workload', '?')}", ""]
            if prof.get("status") != "ok" or "kernels" not in prof:
                lines.append(f"No profile: {prof.get('error') or prof.get('status')}.")
                continue
            lines += [f"{prof['gpu_ms']:,} ms of GPU kernel time traced.", "", "| Kernel | ms | Share |", "|---|---|---|"]
            for k in prof["kernels"][:10]:
                name = k["name"] if len(k["name"]) <= 90 else k["name"][:87] + "..."
                lines.append(f"| `{name}` | {k['ms']:,.1f} | {k['share']:.1%} |")

    lines += ["", "## Verdict", ""]
    if not wins:
        lines.append("Keep the recipe as is: no change beats the baseline on any workload beyond noise.")
    for name, ws in sorted(wins.items(), key=lambda kv: -len(kv[1])):
        cfg = by_name[name]
        where = ", ".join(f"{w} {g:+.1f}%" for w, g in ws)
        lines.append(f"- **`{name}`** wins {len(ws)}/{len(plan['workloads'])} workloads ({where}).")
        if name in losses:
            lost = ", ".join(f"{w} {d:+.1f}%" + (f" (E2E {e:+.1f}%)" if e is not None and e > args.latency else "")
                             for w, d, e in losses[name])
            lines.append(f"  - Loses: {lost}.")
        lines.append(f"  - Placement: {placement(cfg, plan, name in losses)}.")
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
