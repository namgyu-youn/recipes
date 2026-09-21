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
import re
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


# Signals that a recipe's documented serving path is not the in-tree vLLM
# wheel. registry.py then says nothing about the floor: the plugin or the
# pinned image registers the architecture itself, so the recipe legitimately
# runs on a vLLM older than the in-tree landing.
VLLM_PIN_RE = re.compile(r"vllm\s*==\s*([\d.]+)")
ARCH_OVERRIDE_RE = re.compile(r"--hf-overrides[^\n]*architectures", re.I)
FIRST_PARTY_IMAGE = re.compile(r"^vllm/vllm-(openai|tpu)")


def plugin_served(doc: dict, guide: str) -> str | None:
    """Why this recipe's floor cannot be derived from the in-tree registry."""
    meta = doc.get("meta") or {}
    if doc.get("omni") or "omni" in (meta.get("tasks") or []):
        return "omni recipe — served through vllm-omni, which registers the architecture itself"

    images = []
    model = doc.get("model") or {}
    image = model.get("docker_image")
    if isinstance(image, str):
        images.append(image)
    elif isinstance(image, dict):
        images += [v for v in image.values() if isinstance(v, str)]
    for variant in (doc.get("variants") or {}).values():
        if isinstance(variant, dict):
            for hw in (variant.get("hardware_overrides") or {}).values():
                if isinstance(hw, dict) and isinstance(hw.get("docker_image"), str):
                    images.append(hw["docker_image"])
    out_of_tree = [i for i in images if not FIRST_PARTY_IMAGE.match(i)]
    if out_of_tree:
        return f"pins a non-first-party image ({out_of_tree[0]}) that may register the architecture"

    pin = VLLM_PIN_RE.search(guide)
    if pin:
        return f"guide pins vllm=={pin.group(1)} — a release-tested pin, not a floor to raise"
    if ARCH_OVERRIDE_RE.search(guide):
        return "guide selects an architecture via --hf-overrides, so registry.py names the wrong one"
    return None


def guide_floor_line(guide: str) -> str | None:
    """The `- vLLM >= X` prerequisite a floor change also has to update."""
    for line in guide.split("\n"):
        m = re.match(r"\s*-\s*vLLM\s*>=\s*([\d.]+)", line, re.I)
        if m:
            return line.strip()
    return None


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


# Both cases were caught in review of the first floor PR, not by this tool.
# They are cheap to check offline because plugin_served() and guide_floor_line()
# are pure functions of the recipe.
SELF_TEST = [
    ("models/nvidia/Cosmos3-Nano.yaml", "skipped", "omni"),
    ("models/deepseek-ai/DeepSeek-V4-Flash.yaml", "skipped", "image"),
    ("models/openai/gpt-oss-120b.yaml", "checked", None),
    ("models/openai/gpt-oss-120b.yaml", "guide_line", "0.10.0"),
]


def self_test() -> int:
    ok = True
    for rel, kind, expected in SELF_TEST:
        path = F.REPO_ROOT / rel
        if not path.is_file():
            print(f"  skip {rel}: not in this tree")
            continue
        doc = yaml.safe_load(path.read_text())
        guide = str(doc.get("guide") or "")
        reason = plugin_served(doc, guide)
        if kind == "skipped":
            good = bool(reason) and expected in (reason or "")
            detail = reason or "not skipped"
        elif kind == "checked":
            good = reason is None
            detail = reason or "checked, as expected"
        else:
            line = guide_floor_line(guide)
            good = bool(line) and expected in line
            detail = line or "no prerequisite line found"
        print(f"  {'ok  ' if good else 'FAIL'} {rel[7:]:46} {kind:10} {detail[:72]}")
        ok = ok and good
    print(f"model-floors self-test {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--target", required=True)
    ap.add_argument("--report-dir")
    ap.add_argument("--no-fetch", action="store_true", help="use cached configs only")
    ap.add_argument("--only", help="substring filter on the recipe path")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if not args.report_dir:
        ap.error("--report-dir is required unless --self-test is given")
    report_dir = Path(args.report_dir)
    cache_dir = report_dir / "hf-configs"
    cache_dir.mkdir(parents=True, exist_ok=True)

    idx = MODELS.index_for(args.target)["architectures"]
    recipes = sorted((F.REPO_ROOT / "models").rglob("*.yaml"))
    if args.only:
        recipes = [r for r in recipes if args.only in str(r)]

    jobs: list[tuple] = []
    plugin_skipped: list[dict] = []
    for path in recipes:
        try:
            doc = yaml.safe_load(path.read_text())
        except yaml.YAMLError:
            continue
        if not isinstance(doc, dict):
            continue
        rel = str(path.relative_to(F.REPO_ROOT))
        guide = str(doc.get("guide") or "")
        reason = plugin_served(doc, guide)
        if reason:
            plugin_skipped.append({"file": rel, "why": reason})
            continue
        for scope, model_id, floor in checkpoints(doc, rel):
            jobs.append((rel, scope, model_id, floor, guide_floor_line(guide)))

    configs: dict[str, dict | None] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        futures = {
            pool.submit(fetch_config, mid, cache_dir, not args.no_fetch): mid
            for mid in {j[2] for j in jobs}
        }
        for future in concurrent.futures.as_completed(futures):
            configs[futures[future]] = future.result()

    below, unknown_arch, no_floor, removed_arch = [], [], [], []
    for rel, scope, model_id, floor, guide_line in jobs:
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
            # A floor change that leaves this line behind makes the recipe
            # contradict itself: the Install block says one version, the guide
            # prerequisites another.
            "guide_prerequisite": guide_line,
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
        "plugin_served_skipped": plugin_skipped,
        "floor_below_model_support": below,
        "no_floor_declared": no_floor,
        "architecture_removed_upstream": removed_arch,
        "architecture_unknown": unknown_arch,
    }
    (report_dir / "model-floors.json").write_text(json.dumps(out, indent=2, sort_keys=True))

    print(f"checked {len(jobs)} checkpoints across {len(recipes) - len(plugin_skipped)} recipes")
    print(f"  skipped, not served by the in-tree wheel: {len(plugin_skipped)}")
    for e in plugin_skipped[:6]:
        print(f"    {e['file'][7:]:52} {e['why'][:70]}")
    print(f"  floor below the model's introducing release: {len(below)}")
    for e in sorted(below, key=lambda e: e["file"])[:20]:
        print(
            f"    {e['file'][7:]:52} {e['scope']:18} pins {e['floor']:8} "
            f"needs {e['introduced']:9} ({e['architecture']})"
            + (f"  [also update guide: {e['guide_prerequisite']}]" if e.get("guide_prerequisite") else "")
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
