#!/usr/bin/env python3
"""Model-support index: architecture -> introducing / removing vLLM tag.

The flag index answers "did this flag exist at the version the recipe pins?".
This answers the prior question: did the *model* exist? A recipe can pin a
release that predates its own architecture, and no amount of flag checking
finds that.

Two sources, both in vllm/model_executor/models/registry.py:

  the supported dicts          every architecture vLLM serves at that tag
  _PREVIOUSLY_SUPPORTED_MODELS arch -> the last version that supported it,
                               stated by upstream rather than inferred

Cached beside the flag index and extended incrementally.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys

import flagset as F
import index_flags as IDX

REGISTRY_PATHS = [
    "vllm/model_executor/models/registry.py",
    "vllm/model_executor/models/__init__.py",
]
# Dict names are not stable across releases: `_GENERATION_MODELS` became
# `_TEXT_GENERATION_MODELS` in v0.6.3, and `_CROSS_ENCODER_MODELS` was split
# into `_SEQUENCE_CLASSIFICATION_MODELS` and friends in v0.18.0. An allowlist of
# names silently loses whole categories on every rename and reports the rename
# as "the model appeared in this release". So the dicts are detected by shape
# instead: a top-level dict whose keys are architecture identifiers.
CATEGORY_HINTS = [
    ("MULTIMODAL", "multimodal"),
    ("SPECULATIVE", "speculative"),
    ("EMBEDDING", "embedding"),
    ("LATE_INTERACTION", "embedding"),
    ("CROSS_ENCODER", "classification"),
    ("CLASSIFICATION", "classification"),
    ("REWARD", "reward"),
    ("TRANSFORMERS", "transformers-backend"),
    ("GENERATION", "text"),
]
EXCLUDED_DICTS = {"_PREVIOUSLY_SUPPORTED_MODELS", "_ROCM_PARTIALLY_SUPPORTED_MODELS",
                  "_ROCM_UNSUPPORTED_MODELS", "_OOT_SUPPORTED_MODELS"}
ARCH_RE = re.compile(r"^[A-Z][A-Za-z0-9_]{3,}$")


def _category_of(dict_name: str) -> str:
    for hint, category in CATEGORY_HINTS:
        if hint in dict_name:
            return category
    return "other"


REMOVED_DICT = "_PREVIOUSLY_SUPPORTED_MODELS"

CACHE_PATH = IDX.CACHE_DIR / "model-index.json"
SCHEMA = 1


def _registry_source(tag: str) -> str | None:
    for path in REGISTRY_PATHS:
        src = F.read(tag, path)
        if src is not None and "ForCausalLM" in src:
            return src
    return None


def _top_level_dicts(src: str) -> dict[str, ast.Dict]:
    out: dict[str, ast.Dict] = {}
    for node in ast.parse(src).body:
        name = None
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            name = node.target.id
        value = getattr(node, "value", None)
        if name and isinstance(value, ast.Dict):
            out[name] = value
    return out


def archs_at(tag: str) -> tuple[dict[str, str], dict[str, str]]:
    """({arch: category} supported, {arch: last_supported_version} removed)."""
    src = _registry_source(tag)
    if src is None:
        return {}, {}
    dicts = _top_level_dicts(src)
    supported: dict[str, str] = {}
    for name, node in dicts.items():
        if name in EXCLUDED_DICTS:
            continue
        keys = [k.value for k in node.keys if isinstance(k, ast.Constant) and isinstance(k.value, str)]
        if not keys:
            continue
        arch_like = [k for k in keys if ARCH_RE.match(k)]
        if len(arch_like) / len(keys) < 0.8:
            continue  # a config dict, not a model registry
        category = _category_of(name)
        for key in arch_like:
            supported.setdefault(key, category)
    removed: dict[str, str] = {}
    node = dicts.get(REMOVED_DICT)
    if node:
        for key, value in zip(node.keys, node.values):
            if isinstance(key, ast.Constant) and isinstance(value, ast.Constant):
                removed[key.value] = str(value.value)
    return supported, removed


def build(target: str, rebuild: bool = False, quiet: bool = True) -> dict:
    cache = {"schema": SCHEMA, "per_tag": {}} if rebuild else _load()
    wanted = IDX.tags_up_to(target)
    if target not in wanted and F.tag_exists(target):
        wanted = wanted + [target]
    for tag in [t for t in wanted if t not in cache["per_tag"]]:
        supported, removed = archs_at(tag)
        if not supported:
            continue
        cache["per_tag"][tag] = {"supported": supported, "removed": removed}
        if not quiet:
            print(f"  {tag}: {len(supported)} architectures", file=sys.stderr)
    _save(cache)
    return cache


def _load() -> dict:
    if CACHE_PATH.is_file():
        cache = json.loads(CACHE_PATH.read_text())
        if cache.get("schema") == SCHEMA:
            return cache
    return {"schema": SCHEMA, "per_tag": {}}


def _save(cache: dict) -> None:
    IDX.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, sort_keys=True))


def index_for(target: str, rebuild: bool = False, quiet: bool = True) -> dict:
    cache = build(target, rebuild=rebuild, quiet=quiet)
    tags = sorted(cache["per_tag"], key=F.version_key)
    tags = [t for t in tags if F.version_key(t) <= F.version_key(target)]

    presence: dict[str, list[str]] = {}
    category: dict[str, str] = {}
    for tag in tags:
        for arch, cat in cache["per_tag"][tag]["supported"].items():
            presence.setdefault(arch, []).append(tag)
            category[arch] = cat

    oldest = tags[0] if tags else None
    out: dict[str, dict] = {}
    for arch, seen in presence.items():
        after = tags[tags.index(seen[-1]) + 1 :]
        out[arch] = {
            "introduced": seen[0],
            # Present at the oldest tag we can read means "at or before" — the
            # index cannot see further back, and reporting a floor below it
            # would be an artifact of where the history stops.
            "introduced_at_or_before": seen[0] == oldest,
            "category": category[arch],
            "removed": after[0] if after else None,
        }
    # upstream states the last supported version itself; trust it over inference
    last = cache["per_tag"].get(tags[-1], {}) if tags else {}
    for arch, version in (last.get("removed") or {}).items():
        entry = out.setdefault(arch, {"introduced": None, "category": "removed"})
        entry["last_supported"] = version
        entry.setdefault("removed", None)
        entry["removed_upstream_stated"] = True
    return {"target": target, "indexed_tags": tags, "architectures": out}


# Facts confirmed by hand against the registry at those tags. Two dict renames
# (_GENERATION_MODELS in v0.6.3, _CROSS_ENCODER_MODELS in v0.18.0) each made a
# whole category look newly introduced, which reads as "this recipe pins too
# low" for every model in it. These pin the shape of the parse, not the data.
SELF_TEST = [
    ("LlamaForCausalLM", "at-or-before", None),
    ("Qwen2ForCausalLM", "introduced", "v0.3.0"),
    ("GptOssForCausalLM", "introduced", "v0.10.1"),
    ("Qwen2_5_VLForConditionalGeneration", "introduced", "v0.7.2"),
    ("JinaVLForRanking", "introduced", "v0.10.0"),
    ("Cosmos3ForConditionalGeneration", "introduced", "v0.23.0"),
    ("Phi3SmallForCausalLM", "last_supported", "0.9.2"),
]


def self_test(target: str) -> int:
    idx = index_for(target)["architectures"]
    ok = True
    for arch, kind, expected in SELF_TEST:
        entry = idx.get(arch)
        if not entry:
            print(f"  FAIL {arch}: not in the index at all")
            ok = False
            continue
        if kind == "at-or-before":
            good = bool(entry.get("introduced_at_or_before"))
            detail = f"introduced {entry['introduced']}"
        elif kind == "introduced":
            good = entry["introduced"] == expected and not entry.get("introduced_at_or_before")
            detail = f"introduced {entry['introduced']}, expected {expected}"
        else:
            good = entry.get("last_supported") == expected
            detail = f"last_supported {entry.get('last_supported')}, expected {expected}"
        print(f"  {'ok  ' if good else 'FAIL'} {arch:42} {detail}")
        ok = ok and good
    print(f"model-index self-test {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--target", required=True)
    ap.add_argument("--rebuild", action="store_true")
    ap.add_argument("--query", action="append", default=[])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if not F.tag_exists(args.target):
        print(f"tag {args.target} not found locally", file=sys.stderr)
        return 2

    if args.self_test:
        return self_test(args.target)

    idx = index_for(args.target, rebuild=args.rebuild, quiet=False)
    if args.json:
        print(json.dumps(idx, indent=2, sort_keys=True))
        return 0

    archs = idx["architectures"]
    print(
        f"indexed {len(idx['indexed_tags'])} tags "
        f"({idx['indexed_tags'][0]} .. {idx['indexed_tags'][-1]}), "
        f"{len(archs)} architectures  cache: {CACHE_PATH.name}"
    )
    for name in args.query:
        entry = archs.get(name)
        if not entry:
            print(f"  {name:46} not registered at any indexed tag")
            continue
        state = (
            f"removed (last supported {entry['last_supported']})"
            if entry.get("last_supported")
            else f"removed in {entry['removed']}"
            if entry.get("removed")
            else "supported"
        )
        print(f"  {name:46} introduced {str(entry['introduced']):9} {entry['category']:20} {state}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
