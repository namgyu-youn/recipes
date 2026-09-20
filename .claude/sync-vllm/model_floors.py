#!/usr/bin/env python3
"""Check every recipe's vLLM floor against when its architecture landed.

A recipe declares `min_vllm_version`, and the flag scan checks the flags it
emits against that floor. This checks the prior question: was the *model*
servable at that version at all? A recipe pinned below its own architecture's
introducing release is wrong no matter which flags it passes.

Architectures come from each checkpoint's config.json on HuggingFace (cached
under the report directory), introducing tags from index_models.py. Recipes with
no floor at all are reported separately: the index says what the floor should be.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import subprocess
import sys
from pathlib import Path

import yaml

import flagset as F
import index_models as MODELS

HF_CONFIG = "https://huggingface.co/{model_id}/raw/main/config.json"


def fetch_config(model_id: str, cache_dir: Path, allow_fetch: bool) -> dict | None:
    cached = cache_dir / f"{model_id.replace('/', '__')}.json"
    if cached.is_file():
        try:
            return json.loads(cached.read_text())
        except json.JSONDecodeError:
            return None
    if not allow_fetch:
        return None
    proc = subprocess.run(
        ["curl", "-sL", "--max-time", "25", HF_CONFIG.format(model_id=model_id)],
        capture_output=True,
        text=True,
    )
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        cached.write_text("{}")  # gated or missing: remember, don't refetch
        return None
    cached.write_text(json.dumps(data))
    return data


def architectures(config: dict | None) -> list[str]:
    if not config:
        return []
    archs = config.get("architectures") or []
    for key in ("text_config", "language_config", "llm_config"):
        nested = config.get(key)
        if isinstance(nested, dict):
            archs += nested.get("architectures") or []
    return sorted({a for a in archs if isinstance(a, str)})


def checkpoints(doc: dict, path: str) -> list[tuple[str, str, str | None]]:
    """[(scope, model_id, declared floor)] for the recipe and each variant."""
    model = doc.get("model") or {}
    base_floor = model.get("min_vllm_version")
    out = [("model", model.get("model_id"), base_floor)]
    for name, variant in (doc.get("variants") or {}).items():
        if not isinstance(variant, dict) or not variant.get("model_id"):
            continue
        out.append((f"variants.{name}", variant["model_id"], variant.get("min_vllm_version") or base_floor))
    return [(scope, mid, floor) for scope, mid, floor in out if mid]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--target", required=True)
    ap.add_argument("--report-dir", required=True)
    ap.add_argument("--no-fetch", action="store_true", help="use cached configs only")
    ap.add_argument("--only", help="substring filter on the recipe path")
    args = ap.parse_args()

    report_dir = Path(args.report_dir)
    cache_dir = report_dir / "hf-configs"
    cache_dir.mkdir(parents=True, exist_ok=True)

    idx = MODELS.index_for(args.target)["architectures"]
    recipes = sorted((F.REPO_ROOT / "models").rglob("*.yaml"))
    if args.only:
        recipes = [r for r in recipes if args.only in str(r)]

    jobs = []
    for path in recipes:
        try:
            doc = yaml.safe_load(path.read_text())
        except yaml.YAMLError:
            continue
        if not isinstance(doc, dict):
            continue
        rel = str(path.relative_to(F.REPO_ROOT))
        for scope, model_id, floor in checkpoints(doc, rel):
            jobs.append((rel, scope, model_id, floor))

    configs: dict[str, dict | None] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        futures = {
            pool.submit(fetch_config, mid, cache_dir, not args.no_fetch): mid
            for mid in {j[2] for j in jobs}
        }
        for future in concurrent.futures.as_completed(futures):
            configs[futures[future]] = future.result()

    below, unknown_arch, no_floor, removed_arch = [], [], [], []
    for rel, scope, model_id, floor in jobs:
        archs = architectures(configs.get(model_id))
        if not archs:
            unknown_arch.append({"file": rel, "scope": scope, "model_id": model_id})
            continue
        known = [a for a in archs if a in idx]
        if not known:
            unknown_arch.append(
                {"file": rel, "scope": scope, "model_id": model_id, "architectures": archs}
            )
            continue
        # the architecture that landed latest is what gates the recipe
        gating = max(known, key=lambda a: F.version_key(idx[a]["introduced"] or "v0.0.0"))
        introduced = idx[gating]["introduced"]
        entry = {
            "file": rel,
            "scope": scope,
            "model_id": model_id,
            "architecture": gating,
            "introduced": introduced,
            "floor": floor,
        }
        if idx[gating].get("last_supported"):
            entry["last_supported"] = idx[gating]["last_supported"]
            removed_arch.append(entry)
            continue
        if not floor:
            no_floor.append(entry)
            continue
        if str(floor).lower() in {"nightly", "main"}:
            continue
        if idx[gating].get("introduced_at_or_before"):
            continue  # the registry history does not reach far enough to judge
        if F.version_key(floor) < F.version_key(introduced):
            below.append(entry)

    out = {
        "target": args.target,
        "checked": len(jobs),
        "floor_below_model_support": below,
        "no_floor_declared": no_floor,
        "architecture_removed_upstream": removed_arch,
        "architecture_unknown": unknown_arch,
    }
    (report_dir / "model-floors.json").write_text(json.dumps(out, indent=2, sort_keys=True))

    print(f"checked {len(jobs)} checkpoints across {len(recipes)} recipes")
    print(f"  floor below the model's introducing release: {len(below)}")
    for e in sorted(below, key=lambda e: e["file"])[:20]:
        print(
            f"    {e['file'][7:]:52} {e['scope']:18} pins {e['floor']:8} "
            f"needs {e['introduced']:9} ({e['architecture']})"
        )
    print(f"  no floor declared: {len(no_floor)}")
    for e in sorted(no_floor, key=lambda e: e["file"])[:10]:
        print(f"    {e['file'][7:]:52} {e['scope']:18} architecture landed in {e['introduced']} ({e['architecture']})")
    print(f"  architecture no longer supported upstream: {len(removed_arch)}")
    for e in removed_arch[:10]:
        print(f"    {e['file'][7:]:52} {e['architecture']} last supported {e['last_supported']}")
    print(f"  architecture not in the registry (plugin/out-of-tree/gated): {len(unknown_arch)}")
    print(f"  -> {report_dir / 'model-floors.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
