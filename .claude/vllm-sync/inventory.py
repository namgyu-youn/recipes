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
            body = node.body
            for i, stmt in enumerate(body):
                if not (
                    isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name)
                ):
                    continue
                # vLLM documents a config field in the string literal that
                # follows it — that docstring is the flag's --help text, and
                # where a deprecation actually names its replacement.
                nxt = body[i + 1] if i + 1 < len(body) else None
                doc = (
                    nxt.value.value
                    if isinstance(nxt, ast.Expr)
                    and isinstance(nxt.value, ast.Constant)
                    and isinstance(nxt.value.value, str)
                    else None
                )
                out[f"{node.name}.{stmt.target.id}"] = {
                    "default": ast.unparse(stmt.value) if stmt.value else None,
                    "choices": _literal_values(stmt.annotation, aliases),
                    "doc": doc,
                    "file": path,
                    "line": stmt.lineno,
                }
    return out


def _enum_members(tag: str, class_name: str) -> list[str] | None:
    """UPPER_CASE members of an enum class, wherever it lives in the tree.

    Some choice sets are an Enum class rather than a Literal — the attention
    backends are the important one. Without this, `--attention-backend` looks
    like it accepts anything and a bogus value never gets caught.
    """
    hit = _git_grep(tag, f"class {class_name}")
    if not hit:
        return None
    src = read_at(tag, hit)
    if src is None:
        return None
    members: list[str] = []
    inside = False
    for line in src.splitlines():
        if re.match(rf"class {re.escape(class_name)}\b", line):
            inside = True
            continue
        if inside:
            if line and not line[0].isspace():
                break
            m = re.match(r"\s+([A-Z][A-Z0-9_]*)\s*=", line)
            if m:
                members.append(m.group(1))
    return sorted(members) or None


def _git_grep(tag: str, needle: str) -> str | None:
    r = F._git("grep", "-l", needle, tag, "--", "vllm/")
    if r.returncode != 0 or not r.stdout.strip():
        return None
    return r.stdout.split()[0].split(":", 1)[1]


def read_at(tag: str, path: str) -> str | None:
    return F.read(tag, path)


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
            if not entry.get("choices"):
                enum_name = _annotation_enum(stmt.annotation)
                if enum_name:
                    members = _enum_members(tag, enum_name)
                    if members:
                        entry = {**entry, "choices": members, "choices_from": enum_name}
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


def _annotation_enum(node: ast.expr) -> str | None:
    """`AttentionBackendEnum | None` -> "AttentionBackendEnum"."""
    names = []
    stack = [node]
    while stack:
        cur = stack.pop()
        if isinstance(cur, ast.Name):
            names.append(cur.id)
        elif isinstance(cur, ast.BinOp):
            stack.extend([cur.left, cur.right])
        elif isinstance(cur, ast.Subscript):
            stack.append(cur.value)
    return next((n for n in names if n.endswith("Enum")), None)


def replacement_for(tag_removed: str, flag_or_env: str, index: dict) -> dict:
    """What upstream said to use instead, read at the last tag where it existed.

    A removed flag usually spent a release or two carrying its own obituary in
    the argparse help or a deprecation warning. Reading that beats declaring
    "no documented replacement" from the absence alone.
    """
    history = (index["flags"] if flag_or_env.startswith("-") else index["envs"]).get(flag_or_env)
    if not history:
        return {"replacement": None, "why": "no history for this name"}
    tags = [t for t in index["indexed_tags"] if F.version_key(t) < F.version_key(tag_removed)]
    if not tags:
        return {"replacement": None, "why": "no indexed tag before the removal"}
    last = tags[-1]

    texts: list[tuple[str, str]] = []
    for role in ("engine_args", "frontend_args", "envs"):
        resolved = F.resolve_path(last, role)
        if not resolved:
            continue
        path, src = resolved
        if flag_or_env.startswith("-"):
            for node in ast.walk(ast.parse(src)):
                if not (isinstance(node, ast.Call) and F._is_add_argument(node.func)):
                    continue
                names = [
                    a.value for a in node.args if isinstance(a, ast.Constant) and isinstance(a.value, str)
                ]
                if flag_or_env in names:
                    texts.append((f"{path}:{node.lineno}", ast.unparse(node)))
        if flag_or_env in src:
            for i, line in enumerate(src.splitlines(), 1):
                if flag_or_env in line and re.search(r"deprecat|instead|replaced|use ", line, re.I):
                    texts.append((f"{path}:{i}", line.strip()))

    # the flag's real help text: the config field docstring it forwards to
    if flag_or_env.startswith("-"):
        sem = flag_semantics(last).get(flag_or_env) or {}
        via = sem.get("via")
        cfg_entry = config_fields(last).get(via) if via else None
        if cfg_entry and cfg_entry.get("doc"):
            texts.append((f"{cfg_entry['file']}:{cfg_entry['line']} ({via} docstring)", cfg_entry["doc"]))

    for module_path, src in _config_modules(last).items():
        for i, line in enumerate(src.splitlines(), 1):
            if flag_or_env.lstrip("-").replace("-", "_") in line and re.search(
                r"deprecat|instead|replaced|use `", line, re.I
            ):
                texts.append((f"{module_path}:{i}", line.strip()))

    # the deprecation notice is often nowhere near the parser — a request model,
    # a platform check, a warning at startup. One bounded grep finds those.
    field = flag_or_env.lstrip("-").replace("-", "_")
    for needle in {flag_or_env, field}:
        r = F._git("grep", "-n", "-I", "--", needle, last, "--", "vllm/")
        if r.returncode != 0:
            continue
        for hit in r.stdout.splitlines():
            if not re.search(r"deprecat|instead|replaced|in favou?r|please remove|no longer", hit, re.I):
                continue
            # `git grep -n <tag>` prints "<tag>:<path>:<line>:<text>"
            _, _, rest = hit.partition(":")
            path, _, rest = rest.partition(":")
            lineno, _, _text = rest.partition(":")
            # A deprecation message is usually split across several string
            # literals, so the replacement sits a line or two below the word
            # "deprecated". One line is not enough context.
            src = F.read(last, path)
            if src is None:
                texts.append((f"{path}:{lineno}", _text.strip()[:240]))
                continue
            lines = src.splitlines()
            i = int(lineno) if lineno.isdigit() else 1
            window = " ".join(l.strip() for l in lines[max(0, i - 2) : i + 4])
            texts.append((f"{path}:{i}", window[:400]))

    patterns = [
        r"use\s+`?(--[a-z0-9-]+|VLLM_[A-Z0-9_]+)`?\s+instead",
        r"replaced\s+by\s+`?(--[a-z0-9-]+|VLLM_[A-Z0-9_]+)`?",
        r"in favou?r of\s+`?(--[a-z0-9-]+|VLLM_[A-Z0-9_]+)`?",
        r"superseded by\s+`?(--[a-z0-9-]+|VLLM_[A-Z0-9_]+)`?",
        r"(?:migrate|switch) to\s+`?(--[a-z0-9-]+|VLLM_[A-Z0-9_]+)`?",
    ]
    # "please remove it" is a documented resolution too — and a mechanical one.
    remove_patterns = [
        r"please remove it",
        r"simply (remove|drop) it",
        r"no longer (needed|required|has any effect)",
        r"is a no-?op",
    ]

    for where, text in texts:
        for pattern in patterns:
            m = re.search(pattern, text, re.I)
            if m and m.group(1) != flag_or_env:
                return {
                    "replacement": m.group(1),
                    "resolution": "replace",
                    "why": f"documented at {last} in {where}",
                    "quote": text[:240],
                    "last_present": last,
                }
    for where, text in texts:
        if any(re.search(pattern, text, re.I) for pattern in remove_patterns):
            return {
                "replacement": None,
                "resolution": "remove",
                "why": f"upstream says to drop it, documented at {last} in {where}",
                "quote": text[:240],
                "last_present": last,
            }

    # A BooleanOptionalAction flag whose default is the negation of another
    # field was replaced by that field's flag: --disable-log-requests defaults
    # to `not AsyncEngineArgs.enable_log_requests`, i.e. --enable-log-requests.
    target_flags = F.flags_at(index["target"]) if index.get("target") else {}
    for where, text in texts:
        if "BooleanOptionalAction" not in text and "default=not " not in text:
            continue
        for referenced in re.findall(r"\b[A-Za-z]+Args\.([a-z_][a-z0-9_]*)", text):
            candidate = "--" + referenced.replace("_", "-")
            if candidate != flag_or_env and candidate in target_flags:
                return {
                    "replacement": candidate,
                    "resolution": "replace",
                    "why": f"its default was the negation of {referenced} at {last} ({where}), and {candidate} exists at the target tag",
                    "quote": text[:240],
                    "last_present": last,
                }
    return {
        "replacement": None,
        "resolution": "unknown",
        "why": f"read the argparse help, the config field docstring and every deprecation line "
        f"mentioning it at {last}; none names a replacement",
        "last_present": last,
        "quote": texts[0][1][:240] if texts else None,
    }


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
        "--replacements",
        help="comma-separated removed flags/envs; print what upstream said to use instead",
    )
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
    if args.replacements:
        idx = IDX.index_for(args.target, quiet=True)
        out = {}
        for name in args.replacements.split(","):
            name = name.strip()
            if not name:
                continue
            history = (idx["flags"] if name.startswith("-") else idx["envs"]).get(name) or {}
            removed = history.get("removed")
            out[name] = (
                replacement_for(removed, name, idx)
                if removed
                else {"replacement": None, "why": "not recorded as removed"}
            )
        print(json.dumps(out, indent=2, sort_keys=True))
        return 0

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
