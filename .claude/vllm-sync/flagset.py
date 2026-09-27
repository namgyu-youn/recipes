#!/usr/bin/env python3
"""Extract vLLM's CLI flag set and env-var set at a given tag.

Upstream is read via `git show <tag>:<path>` only; nothing here checks out,
fetches, or writes to the reference clone. Every subprocess call is made
directly (not through a shell), so rtk's Bash-hook truncation never applies —
see README.md.

Flags are the union of two AST-derived sets, because neither alone is right:

  literal  add_argument("--x", ...) string constants   (exact, but older tags
           generated some flags from dataclass fields without a literal)
  field    annotated field names of EngineArgs / AsyncEngineArgs /
           FrontendArgs / BaseFrontendArgs, as --kebab-case

Each entry records the `role` it came from. Field-only entries from
`frontend_args` are authoritative — that parser is generated wholesale from the
dataclass via get_kwargs(cls), so `--port` and `--tool-parser-plugin` have no
literal. Field-only entries from `engine_args` are weaker: a handful are
internal fields that never reach the parser. Callers use `role` + `sources` to
tell the two apart rather than treating "field-only" as one class.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
VLLM_CLONE = REPO_ROOT / ".claude_workdir" / "vllm"

# Path candidates per role, newest layout first. Upstream moves these between
# releases (FrontendArgs lived under entrypoints/openai/ before v0.29.0), so a
# missing path means "unknown at this tag", never "removed".
PATHS = {
    "engine_args": ["vllm/engine/arg_utils.py"],
    "frontend_args": [
        "vllm/entrypoints/launchers/cli_args.py",
        "vllm/entrypoints/openai/cli_args.py",
        "vllm/entrypoints/cli/serve.py",
    ],
    "envs": ["vllm/envs.py"],
}

ARG_CLASSES = {"EngineArgs", "AsyncEngineArgs", "FrontendArgs", "BaseFrontendArgs"}


class UpstreamError(RuntimeError):
    pass


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(VLLM_CLONE), *args],
        capture_output=True,
        text=True,
    )


def tag_exists(tag: str) -> bool:
    return _git("rev-parse", "--verify", "--quiet", f"{tag}^{{commit}}").returncode == 0


def stable_tags() -> list[str]:
    """Release tags only, rc/dev excluded, ordered oldest -> newest."""
    out = _git("tag", "--list", "v[0-9]*").stdout.split()
    keep = []
    for t in out:
        parts = t.lstrip("v").split(".")
        if len(parts) == 3 and all(p.isdigit() for p in parts):
            keep.append(t)
    return sorted(keep, key=version_key)


def version_key(tag: str) -> tuple[int, ...]:
    return tuple(int(p) for p in tag.lstrip("v").split("."))


def previous_stable(tag: str) -> str | None:
    tags = stable_tags()
    if tag not in tags:
        earlier = [t for t in tags if version_key(t) < version_key(tag)]
        return earlier[-1] if earlier else None
    i = tags.index(tag)
    return tags[i - 1] if i else None


@lru_cache(maxsize=None)
def read(tag: str, path: str) -> str | None:
    r = _git("show", f"{tag}:{path}")
    return r.stdout if r.returncode == 0 else None


def resolve_path(tag: str, role: str) -> tuple[str, str] | None:
    """First candidate path for `role` that exists at `tag` -> (path, source)."""
    for path in PATHS[role]:
        src = read(tag, path)
        if src is not None:
            return path, src
    return None


def _literal_flags(src: str, path: str, role: str) -> dict[str, dict]:
    """add_argument("--x", "-y", ...) constants, including short aliases."""
    found: dict[str, dict] = {}
    for node in ast.walk(ast.parse(src)):
        if not (isinstance(node, ast.Call) and _is_add_argument(node.func)):
            continue
        names = [
            a.value
            for a in node.args
            if isinstance(a, ast.Constant)
            and isinstance(a.value, str)
            and a.value.startswith("-")
        ]
        primary = next((n for n in names if n.startswith("--")), None)
        for name in names:
            entry = found.setdefault(
                name,
                {
                    "sources": [],
                    "role": role,
                    "file": path,
                    "line": node.lineno,
                    "aliases": [],
                },
            )
            if "literal" not in entry["sources"]:
                entry["sources"].append("literal")
            if primary and name != primary:
                entry["alias_of"] = primary
            entry["aliases"] = [n for n in names if n != name]
    return found


def _is_add_argument(func: ast.expr) -> bool:
    return (isinstance(func, ast.Attribute) and func.attr == "add_argument") or (
        isinstance(func, ast.Name) and func.id == "add_argument"
    )


def _field_flags(src: str, path: str, role: str) -> dict[str, dict]:
    """Annotated field names of the argument dataclasses, as --kebab-case."""
    found: dict[str, dict] = {}
    for node in ast.walk(ast.parse(src)):
        if not (isinstance(node, ast.ClassDef) and node.name in ARG_CLASSES):
            continue
        for stmt in node.body:
            if not (isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name)):
                continue
            name = stmt.target.id
            if name.startswith("_"):  # private, never a CLI flag
                continue
            flag = "--" + name.replace("_", "-")
            entry = found.setdefault(
                flag,
                {
                    "sources": [],
                    "role": role,
                    "declared_in": node.name,
                    "file": path,
                    "line": stmt.lineno,
                    "aliases": [],
                },
            )
            if "field" not in entry["sources"]:
                entry["sources"].append("field")
    return found


def _merge(into: dict[str, dict], other: dict[str, dict]) -> dict[str, dict]:
    for flag, entry in other.items():
        if flag in into:
            for src in entry["sources"]:
                if src not in into[flag]["sources"]:
                    into[flag]["sources"].append(src)
            if "declared_in" in entry:
                into[flag].setdefault("declared_in", entry["declared_in"])
        else:
            into[flag] = entry
    return into


@lru_cache(maxsize=None)
def flags_at(tag: str) -> dict[str, dict]:
    """{flag: {sources, file, line, aliases, alias_of?}} at `tag`."""
    flags: dict[str, dict] = {}
    seen_any = False
    for role in ("engine_args", "frontend_args"):
        resolved = resolve_path(tag, role)
        if resolved is None:
            continue
        seen_any = True
        path, src = resolved
        _merge(flags, _literal_flags(src, path, role))
        _merge(flags, _field_flags(src, path, role))
    if not seen_any:
        raise UpstreamError(f"no argument-parsing source found at {tag}")
    return flags


@lru_cache(maxsize=None)
def envs_at(tag: str) -> dict[str, dict]:
    """{ENV_VAR: {file, line}} from the environment_variables dict at `tag`."""
    resolved = resolve_path(tag, "envs")
    if resolved is None:
        raise UpstreamError(f"vllm/envs.py not found at {tag}")
    path, src = resolved
    found: dict[str, dict] = {}
    for node in ast.walk(ast.parse(src)):
        target_names = []
        value = None
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            target_names = [node.target.id]
            value = node.value
        elif isinstance(node, ast.Assign):
            target_names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            value = node.value
        if "environment_variables" not in target_names or not isinstance(value, ast.Dict):
            continue
        for key in value.keys:
            if isinstance(key, ast.Constant) and isinstance(key.value, str):
                found.setdefault(key.value, {"file": path, "line": key.lineno})
    if not found:
        raise UpstreamError(f"environment_variables dict not parsed at {tag}")
    return found


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tag")
    ap.add_argument(
        "--newest-rc",
        action="store_true",
        help="print the newest release-candidate tag and exit",
    )
    ap.add_argument("--what", choices=["flags", "envs", "both"], default="both")
    ap.add_argument("--json", action="store_true", help="full JSON instead of a summary")
    args = ap.parse_args()

    if args.newest_rc:
        tags = _git("tag", "--list", "v[0-9]*rc*").stdout.split()
        def rc_key(tag: str) -> tuple:
            m = re.match(r"v(\d+)\.(\d+)\.(\d+)rc(\d+)", tag)
            return tuple(int(g) for g in m.groups()) if m else (0, 0, 0, 0)
        ranked = sorted((t for t in tags if rc_key(t) != (0, 0, 0, 0)), key=rc_key)
        print(ranked[-1] if ranked else "")
        return 0

    if not args.tag:
        ap.error("--tag is required unless --newest-rc is given")

    if not VLLM_CLONE.is_dir():
        print(f"reference clone missing: {VLLM_CLONE}", file=sys.stderr)
        return 2
    if not tag_exists(args.tag):
        print(
            f"tag {args.tag} not found locally — fetch it in {VLLM_CLONE} first",
            file=sys.stderr,
        )
        return 2

    out: dict = {"tag": args.tag}
    if args.what in ("flags", "both"):
        flags = flags_at(args.tag)
        out["paths"] = {
            role: (resolve_path(args.tag, role) or ("<missing>", ""))[0]
            for role in ("engine_args", "frontend_args", "envs")
        }
        out["flags"] = flags
    if args.what in ("envs", "both"):
        out["envs"] = envs_at(args.tag)

    if args.json:
        print(json.dumps(out, indent=2, sort_keys=True))
        return 0

    if "flags" in out:
        flags = out["flags"]
        literal = [f for f, e in flags.items() if "literal" in e["sources"]]
        field_only = sorted(f for f, e in flags.items() if e["sources"] == ["field"])
        weak = sorted(
            f
            for f, e in flags.items()
            if e["sources"] == ["field"] and e["role"] == "engine_args"
        )
        longs = [f for f in flags if f.startswith("--")]
        print(f"{args.tag}  paths: {out['paths']}")
        print(
            f"  flags: {len(flags)} total "
            f"({len(longs)} long, {len(flags) - len(longs)} short aliases), "
            f"{len(literal)} literal, {len(field_only)} field-only"
        )
        print(
            f"  field-only: {len(field_only)} "
            f"({len(field_only) - len(weak)} frontend/authoritative, "
            f"{len(weak)} engine-args/weak)"
        )
        print(f"  weak (engine-args field-only): {weak}")
    if "envs" in out:
        print(f"  envs: {len(out['envs'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
