#!/usr/bin/env python3
"""Build and query the flag/env -> introduced/removed tag index.

This is the *absolute* check: independent of any prev..target delta, it answers
"does this flag exist at the tag this recipe pins?" and "when did it appear or
disappear?", so a release we skipped can never hide stale usage.

The index covers stable tags only (rc/dev excluded) and is cached at
.claude_workdir/reports/vllm-sync-cache/flag-index.json. It is extended
incrementally: a run indexes only the stable tags it has not seen yet.

Upstream is read through flagset.py (git show only). Never use Bash `git log`
output for tag lists — rtk truncates it; see README.md.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import flagset as F

CACHE_DIR = F.REPO_ROOT / ".claude_workdir" / "reports" / "vllm-sync-cache"
CACHE_PATH = CACHE_DIR / "flag-index.json"
SCHEMA = 1


def load_cache() -> dict:
    if CACHE_PATH.is_file():
        cache = json.loads(CACHE_PATH.read_text())
        if cache.get("schema") == SCHEMA:
            return cache
    return {"schema": SCHEMA, "per_tag": {}, "unparsed": {}}


def save_cache(cache: dict) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, sort_keys=True))


def tags_up_to(target: str) -> list[str]:
    tags = F.stable_tags()
    if target in tags:
        return tags[: tags.index(target) + 1]
    # target may be an rc or an unreleased tag: take every stable tag below it
    return [t for t in tags if F.version_key(t) < F.version_key(target)]


def build(target: str, rebuild: bool = False, quiet: bool = False) -> dict:
    cache = {"schema": SCHEMA, "per_tag": {}, "unparsed": {}} if rebuild else load_cache()
    wanted = tags_up_to(target)
    if target not in wanted and F.tag_exists(target):
        wanted = wanted + [target]  # index the target itself even if it is an rc
    missing = [t for t in wanted if t not in cache["per_tag"] and t not in cache["unparsed"]]

    for i, tag in enumerate(missing, 1):
        started = time.time()
        try:
            flags = F.flags_at(tag)
            envs = F.envs_at(tag)
        except (F.UpstreamError, SyntaxError, ValueError) as exc:
            cache["unparsed"][tag] = f"{type(exc).__name__}: {exc}"
            if not quiet:
                print(f"  [{i}/{len(missing)}] {tag}: skipped ({exc})", file=sys.stderr)
            continue
        cache["per_tag"][tag] = {
            "flags": sorted(flags),
            "envs": sorted(envs),
            "paths": {
                role: (F.resolve_path(tag, role) or ("<missing>",))[0]
                for role in ("engine_args", "frontend_args", "envs")
            },
        }
        if not quiet:
            print(
                f"  [{i}/{len(missing)}] {tag}: {len(flags)} flags, {len(envs)} envs"
                f" ({time.time() - started:.1f}s)",
                file=sys.stderr,
            )
    if missing:
        save_cache(cache)
    return cache


def derive(cache: dict, kind: str, upto: str | None = None) -> dict[str, dict]:
    """{name: {introduced, removed, absent_in}} over the indexed tags.

    introduced = oldest indexed tag containing it
    removed    = oldest tag *after* its last appearance (None if still present)
    absent_in  = tags between first and last appearance where it is missing
                 (a rename that was reverted, or a flag that came back)
    """
    tags = sorted(cache["per_tag"], key=F.version_key)
    if upto is not None:
        tags = [t for t in tags if F.version_key(t) <= F.version_key(upto)]
    presence: dict[str, list[str]] = {}
    for tag in tags:
        for name in cache["per_tag"][tag][kind]:
            presence.setdefault(name, []).append(tag)

    out: dict[str, dict] = {}
    for name, seen in presence.items():
        first, last = seen[0], seen[-1]
        span = tags[tags.index(first) : tags.index(last) + 1]
        after = tags[tags.index(last) + 1 :]
        out[name] = {
            "introduced": first,
            "removed": after[0] if after else None,
            "absent_in": [t for t in span if t not in seen],
        }
    return out


def index_for(target: str, rebuild: bool = False, quiet: bool = True) -> dict:
    cache = build(target, rebuild=rebuild, quiet=quiet)
    return {
        "target": target,
        "indexed_tags": sorted(cache["per_tag"], key=F.version_key),
        "unparsed_tags": cache["unparsed"],
        "flags": derive(cache, "flags", upto=target),
        "envs": derive(cache, "envs", upto=target),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--target", required=True, help="newest tag to index")
    ap.add_argument("--rebuild", action="store_true", help="discard the cache first")
    ap.add_argument("--query", action="append", default=[], help="flag or env to look up")
    ap.add_argument("--json", action="store_true", help="dump the whole index")
    args = ap.parse_args()

    if not F.tag_exists(args.target):
        print(
            f"tag {args.target} not found locally — fetch it in {F.VLLM_CLONE} first",
            file=sys.stderr,
        )
        return 2

    idx = index_for(args.target, rebuild=args.rebuild, quiet=False)

    if args.json:
        print(json.dumps(idx, indent=2, sort_keys=True))
        return 0

    print(
        f"indexed {len(idx['indexed_tags'])} stable tags "
        f"({idx['indexed_tags'][0]} .. {idx['indexed_tags'][-1]})"
        f"  cache: {CACHE_PATH.relative_to(F.REPO_ROOT)}"
    )
    if idx["unparsed_tags"]:
        print(f"  unparsed: {sorted(idx['unparsed_tags'])}")
    for name in args.query:
        kind = "envs" if name.startswith("VLLM_") or name.isupper() else "flags"
        e = idx[kind].get(name)
        if e is None:
            print(f"  {name:34} never present in any indexed tag")
            continue
        state = "removed in " + e["removed"] if e["removed"] else "present"
        gaps = f"  absent_in={e['absent_in']}" if e["absent_in"] else ""
        print(f"  {name:34} introduced {e['introduced']:9} {state}{gaps}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
