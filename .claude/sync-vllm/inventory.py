#!/usr/bin/env python3
"""Categorize what changed upstream between two tags -> inventory.json.

This is the *source pass*, independent of release notes. It derives everything
from the tree at each tag via AST, never from prose:

  removed          flag/env present at prev, absent at target
  new-feature      flag/env added, or a new value added to a flag's Literal
                   choice set (a new attention/MoE/linear backend, etc.)
  default-changed  a flag's resolved default value differs
  deprecated       a deprecation marker at target names a flag/env
  renamed          a removal and an addition in the same window whose names
                   are close enough to pair (heuristic; always needs judgment)

Defaults and choices are resolved the way vLLM actually layers them: an
EngineArgs field usually defaults to `SomeConfig.field`, so the real default and
the Literal choice set are read from vllm/config/*.py.

Upstream is read through flagset.py (git show only); never from Bash `git log`,
which rtk truncates. See README.md.
"""

from __future__ import annotations

import argparse
import ast
import difflib
import re
import json
import sys
import time
from pathlib import Path

import flagset as F
import index_flags as IDX

CONFIG_DIR = "vllm/config"
DEPRECATION_SCAN = ["engine_args", "frontend_args", "envs"]


# --------------------------------------------------------------------------
# config-module resolution: Config.field -> (default repr, literal choices)
# --------------------------------------------------------------------------


def _config_modules(tag: str) -> dict[str, str]:
    r = F._git("ls-tree", "-r", "--name-only", tag, f"{CONFIG_DIR}/")
    out = {}
    for path in r.stdout.split():
        if path.endswith(".py"):
            src = F.read(tag, path)
            if src is not None:
                out[path] = src
    if not out:  # pre-0.10 layout: one module
        src = F.read(tag, "vllm/config.py")
        if src is not None:
            out["vllm/config.py"] = src
    return out


def _literal_values(node: ast.expr, aliases: dict[str, list[str]]) -> list[str] | None:
    """Literal["a", "b"] -> ["a", "b"]; a Name resolves through module aliases."""
    if isinstance(node, ast.Name):
        return aliases.get(node.id)
    if isinstance(node, ast.Subscript) and getattr(node.value, "id", "") == "Literal":
        sl = node.slice
        elts = sl.elts if isinstance(sl, ast.Tuple) else [sl]
        vals = []
        for e in elts:
            if isinstance(e, ast.Constant):
                vals.append(str(e.value))
                continue
            nested = _literal_values(e, aliases)
            if nested is None:
                # `Literal["auto", RunnerType]` — one member is an alias from
                # another module. A partial set would read as a closed choice
                # list and reject valid values, so the whole set is unknown.
                return None
            vals.extend(nested)
        return sorted(set(vals)) or None
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):  # X | Literal[...]
        sides = []
        for side in (node.left, node.right):
            if isinstance(side, ast.Constant) and side.value is None:
                continue  # `| None` widens nothing
            values = _literal_values(side, aliases)
            if values is None:
                return None  # one side is an alias from another module: unknown
            sides.extend(values)
        return sorted(set(sides)) or None
    return None


def config_fields(tag: str) -> dict[str, dict]:
    """{"ModelConfig.dtype": {default, choices, file, line}} across vllm/config."""
    out: dict[str, dict] = {}
    for path, src in _config_modules(tag).items():
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        aliases: dict[str, list[str]] = {}
        for node in tree.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                target = node.targets[0]
                if isinstance(target, ast.Name):
                    vals = _literal_values(node.value, {})
                    if vals:
                        aliases[target.id] = vals
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            for stmt in node.body:
                if not (
                    isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name)
                ):
                    continue
                out[f"{node.name}.{stmt.target.id}"] = {
                    "default": ast.unparse(stmt.value) if stmt.value else None,
                    "choices": _literal_values(stmt.annotation, aliases),
                    "file": path,
                    "line": stmt.lineno,
                }
    return out


def flag_semantics(tag: str) -> dict[str, dict]:
    """{flag: {default, choices, file, line}} with EngineArgs -> Config resolved."""
    resolved = F.resolve_path(tag, "engine_args")
    if resolved is None:
        return {}
    path, src = resolved
    cfg = config_fields(tag)
    out: dict[str, dict] = {}
    for node in ast.walk(ast.parse(src)):
        if not (isinstance(node, ast.ClassDef) and node.name in F.ARG_CLASSES):
            continue
        for stmt in node.body:
            if not (isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name)):
                continue
            name = stmt.target.id
            if name.startswith("_"):
                continue
            flag = "--" + name.replace("_", "-")
            entry = {
                "default": ast.unparse(stmt.value) if stmt.value else None,
                "choices": _literal_values(stmt.annotation, {}),
                "file": path,
                "line": stmt.lineno,
            }
            # `foo: T = SomeConfig.foo` -> take the real default/choices there
            if (
                isinstance(stmt.value, ast.Attribute)
                and isinstance(stmt.value.value, ast.Name)
            ):
                key = f"{stmt.value.value.id}.{stmt.value.attr}"
                if key in cfg:
                    entry = {**cfg[key], "via": key}
            out[flag] = entry
    return out


# --------------------------------------------------------------------------
# deprecation markers
# --------------------------------------------------------------------------


def _owner_ranges(src: str, path: str) -> list[tuple[int, int, str]]:
    """(start_line, end_line, flag_or_env) spans that own a line in `src`.

    A deprecation notice is attributed to the declaration that encloses it, not
    to whatever name happens to sit a few lines away — in arg_utils.py the
    add_argument calls are dense enough that any text window mis-attributes.

    Spans come from add_argument() calls, argument-dataclass fields, and
    config-dataclass fields together with the docstring that follows them
    (where vLLM actually writes "deprecated").
    """
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []
    spans: list[tuple[int, int, str]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and F._is_add_argument(node.func):
            names = [
                a.value
                for a in node.args
                if isinstance(a, ast.Constant)
                and isinstance(a.value, str)
                and a.value.startswith("--")
            ]
            if names:
                spans.append((node.lineno, node.end_lineno or node.lineno, names[0]))
        elif isinstance(node, ast.ClassDef):
            body = node.body
            for i, stmt in enumerate(body):
                if not (
                    isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name)
                ):
                    continue
                name = stmt.target.id
                if name.startswith("_"):
                    continue
                end = stmt.end_lineno or stmt.lineno
                nxt = body[i + 1] if i + 1 < len(body) else None
                if (
                    isinstance(nxt, ast.Expr)
                    and isinstance(nxt.value, ast.Constant)
                    and isinstance(nxt.value.value, str)
                ):
                    end = nxt.end_lineno or end  # the field's docstring
                spans.append((stmt.lineno, end, "--" + name.replace("_", "-")))
    return spans


def deprecations(tag: str, names: list[str]) -> list[dict]:
    """Deprecation notices at `tag`, attributed to the flag/env they belong to.

    Two attribution paths, both exact rather than proximity-based:
      * the enclosing declaration (see _owner_ranges), for a notice written in
        a flag's help text or a config field's docstring;
      * an env var named word-bounded on the notice line itself.

    Names containing "deprecat" are skipped — a flag *about* deprecation
    (--allow-deprecated-quantization) is not itself deprecated. Each name is
    reported once per file.
    """
    known = {n for n in names if not n.startswith("-")}
    env_patterns = [
        (n, re.compile(rf"\b{re.escape(n)}\b"))
        for n in known
        if "deprecat" not in n.lower()
    ]
    flags = {n for n in names if n.startswith("--") and "deprecat" not in n.lower()}

    sources = {}
    for role in DEPRECATION_SCAN:
        resolved = F.resolve_path(tag, role)
        if resolved:
            sources[resolved[0]] = resolved[1]
    sources.update(_config_modules(tag))

    hits: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for path, src in sorted(sources.items()):
        lines = src.splitlines()
        spans = _owner_ranges(src, path)
        for i, line in enumerate(lines, start=1):
            if "eprecat" not in line:
                continue
            owners = [
                name for start, end, name in spans if start <= i <= end and name in flags
            ]
            for name, pattern in env_patterns:
                if pattern.search(line):
                    owners.append(name)
            for name in owners:
                if (name, path) in seen:
                    continue
                seen.add((name, path))
                hits.append(
                    {"name": name, "file": path, "line": i, "text": line.strip()[:200]}
                )
    return hits


# --------------------------------------------------------------------------
# inventory
# --------------------------------------------------------------------------


def pair_renames(removed: list[str], added: list[str]) -> list[tuple[str, str, float]]:
    pairs = []
    for old in removed:
        match = difflib.get_close_matches(old, added, n=1, cutoff=0.6)
        if match:
            ratio = difflib.SequenceMatcher(None, old, match[0]).ratio()
            pairs.append((old, match[0], round(ratio, 3)))
    return pairs


def build_inventory(prev: str, target: str) -> dict:
    idx = IDX.index_for(target, quiet=True)
    flags_prev, flags_target = F.flags_at(prev), F.flags_at(target)
    envs_prev, envs_target = F.envs_at(prev), F.envs_at(target)
    sem_prev, sem_target = flag_semantics(prev), flag_semantics(target)

    items: list[dict] = []

    def add(category, kind, name, evidence, detail, **extra):
        items.append(
            {
                "id": f"I-{len(items) + 1:03d}",
                "category": category,
                "kind": kind,
                "name": name,
                "source": "source-only",
                "evidence": evidence,
                "detail": detail,
                **extra,
            }
        )

    flags_added = sorted(set(flags_target) - set(flags_prev))
    flags_removed = sorted(set(flags_prev) - set(flags_target))
    envs_added = sorted(set(envs_target) - set(envs_prev))
    envs_removed = sorted(set(envs_prev) - set(envs_target))

    rename_pairs = dict(
        (old, new) for old, new, _ in pair_renames(flags_removed, flags_added)
    )
    rename_pairs.update(
        (old, new) for old, new, _ in pair_renames(envs_removed, envs_added)
    )

    for flag in flags_removed:
        e = flags_prev[flag]
        cat = "renamed" if flag in rename_pairs else "removed"
        add(
            cat,
            "flag",
            flag,
            {"tag": prev, "file": e["file"], "line": e["line"]},
            f"present at {prev}, absent at {target}"
            + (f"; closest new name {rename_pairs[flag]}" if flag in rename_pairs else ""),
            replacement=rename_pairs.get(flag),
            introduced=idx["flags"].get(flag, {}).get("introduced"),
        )
    for env in envs_removed:
        e = envs_prev[env]
        cat = "renamed" if env in rename_pairs else "removed"
        add(
            cat,
            "env",
            env,
            {"tag": prev, "file": e["file"], "line": e["line"]},
            f"present at {prev}, absent at {target}"
            + (f"; closest new name {rename_pairs[env]}" if env in rename_pairs else ""),
            replacement=rename_pairs.get(env),
            introduced=idx["envs"].get(env, {}).get("introduced"),
        )

    reverse_renames = {v: k for k, v in rename_pairs.items()}
    for flag in flags_added:
        if flag in reverse_renames:
            continue
        e = flags_target[flag]
        add(
            "new-feature",
            "flag",
            flag,
            {"tag": target, "file": e["file"], "line": e["line"]},
            f"new in {target} (sources: {', '.join(e['sources'])})",
            introduced=target,
            choices=sem_target.get(flag, {}).get("choices"),
            default=sem_target.get(flag, {}).get("default"),
        )
    for env in envs_added:
        if env in reverse_renames:
            continue
        e = envs_target[env]
        add(
            "new-feature",
            "env",
            env,
            {"tag": target, "file": e["file"], "line": e["line"]},
            f"new in {target}",
            introduced=target,
        )

    # new values in an existing flag's choice set: new backends, formats, modes
    for flag, cur in sem_target.items():
        old = sem_prev.get(flag)
        if not (cur.get("choices") and old and old.get("choices")):
            continue
        gained = sorted(set(cur["choices"]) - set(old["choices"]))
        if gained:
            add(
                "new-feature",
                "enum-value",
                flag,
                {"tag": target, "file": cur["file"], "line": cur["line"]},
                f"{flag} gained {gained} (now {cur['choices']})",
                values=gained,
                choices=cur["choices"],
            )

    for flag, cur in sem_target.items():
        old = sem_prev.get(flag)
        if not old or old.get("default") == cur.get("default"):
            continue
        if old.get("default") is None or cur.get("default") is None:
            continue
        add(
            "default-changed",
            "flag",
            flag,
            {"tag": target, "file": cur["file"], "line": cur["line"]},
            f"default {old['default']} -> {cur['default']}",
            old_default=old["default"],
            new_default=cur["default"],
        )

    known = sorted(set(flags_target) | set(envs_target))
    seen: set[tuple[str, str, int]] = set()
    for hit in deprecations(target, known):
        key = (hit["name"], hit["file"], hit["line"])
        if key in seen:
            continue
        seen.add(key)
        add(
            "deprecated",
            "flag" if hit["name"].startswith("-") else "env",
            hit["name"],
            {"tag": target, "file": hit["file"], "line": hit["line"]},
            hit["text"],
        )

    counts: dict[str, int] = {}
    for item in items:
        counts[item["category"]] = counts.get(item["category"], 0) + 1
    return {
        "prev": prev,
        "target": target,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "counts": counts,
        "items": items,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--target", required=True)
    ap.add_argument("--prev", help="defaults to the previous stable release")
    ap.add_argument("--out", help="write inventory.json here")
    ap.add_argument(
        "--dump-semantics",
        action="store_true",
        help="print {flag: {default, choices}} at --target and exit "
        "(scan.mjs uses it to check that a recipe's value is still a valid choice)",
    )
    args = ap.parse_args()

    for tag in filter(None, [args.target, args.prev]):
        if not F.tag_exists(tag):
            print(f"tag {tag} not found locally — fetch it first", file=sys.stderr)
            return 2
    if args.dump_semantics:
        print(json.dumps(flag_semantics(args.target), indent=2, sort_keys=True))
        return 0

    prev = args.prev or F.previous_stable(args.target)
    if not prev:
        print(f"no stable release before {args.target}", file=sys.stderr)
        return 2

    inv = build_inventory(prev, args.target)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(inv, indent=2, sort_keys=True))

    print(f"{prev} -> {args.target}: {len(inv['items'])} items")
    for cat in sorted(inv["counts"]):
        names = [i["name"] for i in inv["items"] if i["category"] == cat]
        shown = ", ".join(sorted(set(names))[:8])
        more = "" if len(set(names)) <= 8 else f", +{len(set(names)) - 8} more"
        print(f"  {cat:17} {inv['counts'][cat]:4}  {shown}{more}")
    if args.out:
        print(f"  -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
