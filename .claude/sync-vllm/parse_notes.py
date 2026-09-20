#!/usr/bin/env python3
"""Release notes -> inventory items with PR numbers, resolved to local commits.

The primary discovery pass. vLLM's notes are dense prose, not a flag list: one
bullet carries a dozen PR refs, inline `--flags`, env vars, model families and
hardware names. So each bullet is split into clauses, and every `(#NNNN)` is
attributed to the clause it sits in — that clause supplies the flags, envs,
models and hardware the PR is about.

Each PR is then resolved to a real commit in the local clone
(`git log <prev>..<target> --grep "(#NNNN)"`), which gives the changed files as
mechanical evidence. A PR that resolves to no commit in the window is kept but
marked unresolved, never treated as proof.

Network is used only to fetch the notes (`gh release view`). --release-notes
supplies them offline; --no-fetch runs on whatever is already cached.

Never read upstream through Bash `git log` — rtk truncates it. See README.md.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import flagset as F

REPO = "vllm-project/vllm"
SKIP_SECTIONS = {"New Contributors", "Contributors", "Release Artifacts"}
BREAKING_SECTIONS = {"Breaking Changes & Deprecations"}

FLAG_RE = re.compile(r"(?<![-\w])(--[a-z0-9][a-z0-9-]{2,})(?![-\w])")
ENV_RE = re.compile(r"\b(VLLM_[A-Z0-9_]{3,})\b")
PR_RE = re.compile(r"\(#(\d{3,7})\)|#(\d{3,7})\b")
# Model families as recipes name them; matched case-insensitively against a
# clause so scan.mjs can join a note to the recipes it could apply to.
MODEL_RE = re.compile(
    r"\b(deepseek[- ]?v?[\d.]*\w*|kimi[- ]?k\d[\w.]*|glm[- ]?[\d.]+\w*|qwen[\d.]*[-\w]*"
    r"|llama[- ]?[\d.]*\w*|gpt-oss|minimax[- ]?m[\d.]+\w*|mistral\w*|gemma\d*"
    r"|granite\w*|hunyuan\w*|hy[\d-]\w*|ernie[\d.-]*\w*|nemotron\w*"
    r"|intern(?:lm|vl|-s\d)\w*"
    r"|plamo\d*|wan[\d.]*|step\w*|seed[- ]?oss|paddleocr\w*)\b",
    re.I,
)
HARDWARE_RE = re.compile(
    r"\b(sm\d{2,3}|blackwell|hopper|ampere|b200|b300|gb200|gb300|h100|h200|h20"
    r"|a100|l40s?|rtx\s?\d{4}\w*|mi\d{3}x?\w*|rocm|amd|xpu|tpu|cpu|gb10|dgx\s?spark"
    r"|ascend|npu|nvidia|cuda\s?1[0-9.]*)\b",
    re.I,
)

PERF_WORDS = re.compile(
    r"\b(speedup|faster|latency|throughput|tpot|ttft|perf|performance|optimiz\w+"
    r"|tuned|accelerat\w+|reduc\w+|\d+(\.\d+)?\s?%|\d+(\.\d+)?x)\b",
    re.I,
)
DEPRECATED_WORDS = re.compile(r"\bdeprecat\w+\b", re.I)
REMOVED_WORDS = re.compile(r"\b(removed|dropped|no longer (supported|available))\b", re.I)
RENAMED_WORDS = re.compile(r"\b(renamed|replaced by|superseded by|moved to)\b", re.I)
DEFAULT_WORDS = re.compile(
    r"\b(now (the )?default|by default|defaults? (to|changed)|enabled by default"
    r"|disabled by default)\b",
    re.I,
)


def releases_between(prev: str, target: str) -> list[str]:
    """Stable releases in (prev, target], oldest first; patch releases included."""
    tags = F.stable_tags()
    out = [
        t
        for t in tags
        if F.version_key(prev) < F.version_key(t) <= F.version_key(target)
    ]
    if target not in out and F.tag_exists(target):
        out.append(target)  # target may be an rc
    return out


def fetch_notes(tag: str, cache_dir: Path, allow_fetch: bool) -> dict | None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached = cache_dir / f"{tag}.json"
    if cached.is_file():
        return json.loads(cached.read_text())
    if not allow_fetch:
        return None
    proc = subprocess.run(
        ["gh", "release", "view", tag, "--repo", REPO, "--json", "body,tagName,publishedAt"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode != 0:
        print(f"  {tag}: gh failed ({proc.stderr.strip()[:120]})", file=sys.stderr)
        return None
    data = json.loads(proc.stdout)
    cached.write_text(json.dumps(data, indent=2))
    (cache_dir / f"{tag}.md").write_text(data.get("body", ""))
    return data


def clauses(bullet: str) -> list[str]:
    """Split a bullet into PR-sized clauses.

    Splitting on ', ' and ' and ' keeps each `(#NNNN)` with the words that
    describe it; a whole bullet would attribute every flag in it to every PR.
    """
    parts = re.split(r",\s+(?=\S)|;\s+|\.\s+(?=[A-Z])|\s+and\s+(?=\S)", bullet)
    return [p.strip() for p in parts if p.strip()]


def classify(text: str, section: str) -> str:
    if DEPRECATED_WORDS.search(text):
        return "deprecated"
    if RENAMED_WORDS.search(text):
        return "renamed"
    if REMOVED_WORDS.search(text):
        return "removed"
    if DEFAULT_WORDS.search(text):
        return "default-changed"
    if PERF_WORDS.search(text):
        return "perf-improvement"
    if section in BREAKING_SECTIONS:
        return "deprecated"
    return "new-feature"


def parse_body(body: str, tag: str) -> list[dict]:
    section = ""
    items: list[dict] = []
    for raw in body.splitlines():
        line = raw.rstrip()
        if line.startswith("#"):
            section = line.lstrip("#").strip()
            continue
        if section in SKIP_SECTIONS or not re.match(r"^\s*[*-]\s+", line):
            continue
        bullet = re.sub(r"^\s*[*-]\s+", "", line)
        for clause in clauses(bullet):
            prs = sorted({m[0] or m[1] for m in PR_RE.findall(clause)})
            flags = sorted(set(FLAG_RE.findall(clause)))
            envs = sorted(set(ENV_RE.findall(clause)))
            if not prs and not flags and not envs:
                continue
            items.append(
                {
                    "tag": tag,
                    "section": section,
                    "category": classify(clause, section),
                    "prs": prs,
                    "flags": flags,
                    "envs": envs,
                    "models": sorted({m.lower() for m in MODEL_RE.findall(clause)}),
                    "hardware": sorted({h.lower() for h in HARDWARE_RE.findall(clause)}),
                    "text": clause[:400],
                }
            )
    return items


def resolve_prs(items: list[dict], prev: str, target: str) -> dict[str, dict]:
    """PR number -> {commit, subject, files} from the local clone.

    Deliberately NOT a `prev..target` range search. The clone is shallow and its
    release tags sit on release branches: v0.28.0 is not an ancestor of v0.29.0
    (no merge-base at all), and `rev-list --count v0.29.0` is 58, so a range
    resolves barely a tenth of the PRs a release actually lists. Scanning every
    ref's subjects once resolves ~80% and costs one git call.

    Resolution is best-effort evidence, never proof: an unresolved PR just means
    the commit is outside the shallow boundary. The authoritative check stays
    the tree at the tag (flagset/index), which is always complete.
    """
    wanted = {pr for item in items for pr in item["prs"]}
    out: dict[str, dict] = {pr: {"commit": None, "subject": None, "files": []} for pr in wanted}
    log = F._git("log", "--all", "--format=%H%x1f%s").stdout
    for line in log.splitlines():
        commit, _, subject = line.partition("\x1f")
        for match in PR_RE.finditer(subject):
            pr = match.group(1) or match.group(2)
            if pr in wanted and out[pr]["commit"] is None:
                out[pr] = {"commit": commit, "subject": subject, "files": []}
    for pr, entry in out.items():
        if entry["commit"]:
            entry["files"] = F._git(
                "show", "--name-only", "--format=", entry["commit"]
            ).stdout.split()[:40]
    return out


def merge_into_inventory(inv: dict, notes_items: list[dict], resolved: dict) -> dict:
    """Fold notes items into inventory.json, updating `source` on overlaps."""
    by_name: dict[str, list[dict]] = {}
    for item in inv["items"]:
        by_name.setdefault(item["name"], []).append(item)

    for note in notes_items:
        evidence = [
            {"pr": pr, **resolved.get(pr, {})}
            for pr in note["prs"]
        ]
        named = note["flags"] + note["envs"]
        matched = False
        for name in named:
            for item in by_name.get(name, []):
                matched = True
                item["source"] = "both" if item["source"] == "source-only" else item["source"]
                item.setdefault("notes", []).append(
                    {
                        "tag": note["tag"],
                        "section": note["section"],
                        "text": note["text"],
                        "prs": evidence,
                    }
                )
        if matched:
            continue
        for name in named or [None]:
            inv["items"].append(
                {
                    "id": f"I-{len(inv['items']) + 1:03d}",
                    "category": note["category"],
                    "kind": (
                        "flag"
                        if name and name.startswith("--")
                        else "env"
                        if name
                        else "narrative"
                    ),
                    "name": name,
                    "source": "release-notes",
                    "evidence": {"tag": note["tag"], "prs": evidence},
                    "detail": note["text"],
                    "section": note["section"],
                    "models": note["models"],
                    "hardware": note["hardware"],
                }
            )
    counts: dict[str, int] = {}
    for item in inv["items"]:
        counts[item["category"]] = counts.get(item["category"], 0) + 1
    inv["counts"] = counts
    return inv


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--target", required=True)
    ap.add_argument("--prev", help="defaults to the previous stable release")
    ap.add_argument("--report-dir", required=True, help=".claude_workdir/reports/vllm-<target>")
    ap.add_argument("--release-notes", help="offline notes file for the target tag")
    ap.add_argument("--no-fetch", action="store_true", help="use cached notes only")
    ap.add_argument("--merge", action="store_true", help="merge into inventory.json in place")
    args = ap.parse_args()

    prev = args.prev or F.previous_stable(args.target)
    if not prev:
        print(f"no stable release before {args.target}", file=sys.stderr)
        return 2

    report_dir = Path(args.report_dir)
    cache_dir = report_dir / "release-notes"
    tags = releases_between(prev, args.target)

    items: list[dict] = []
    fetched, missing = [], []
    for tag in tags:
        if args.release_notes and tag == args.target:
            body = Path(args.release_notes).read_text()
            cache_dir.mkdir(parents=True, exist_ok=True)
            (cache_dir / f"{tag}.md").write_text(body)
            data = {"body": body, "tagName": tag, "source": "offline"}
        else:
            data = fetch_notes(tag, cache_dir, allow_fetch=not args.no_fetch)
        if not data:
            missing.append(tag)
            continue
        fetched.append(tag)
        items.extend(parse_body(data.get("body", ""), tag))

    if missing:
        print(
            f"WARNING: no release notes for {missing} — the source pass covers these "
            f"releases, the notes pass does not",
            file=sys.stderr,
        )

    resolved = resolve_prs(items, prev, args.target)
    (report_dir / "notes-items.json").write_text(
        json.dumps({"prev": prev, "target": args.target, "releases": fetched,
                    "missing": missing, "items": items, "prs": resolved},
                   indent=2, sort_keys=True)
    )

    unresolved = [pr for pr, r in resolved.items() if not r["commit"]]
    print(f"{prev} -> {args.target}: notes for {fetched or 'none'}")
    print(f"  clauses with a PR/flag/env: {len(items)}")
    print(f"  PRs: {len(resolved)} ({len(resolved) - len(unresolved)} resolved to commits)")
    cats: dict[str, int] = {}
    for item in items:
        cats[item["category"]] = cats.get(item["category"], 0) + 1
    for cat in sorted(cats):
        print(f"    {cat:18} {cats[cat]}")
    named = sorted({n for i in items for n in i["flags"] + i["envs"]})
    print(f"  named flags/envs in notes: {len(named)}")
    print(f"    {', '.join(named[:12])}{' ...' if len(named) > 12 else ''}")

    if args.merge:
        inv_path = report_dir / "inventory.json"
        inv = json.loads(inv_path.read_text())
        merged = merge_into_inventory(inv, items, resolved)
        inv_path.write_text(json.dumps(merged, indent=2, sort_keys=True))
        both = sum(1 for i in merged["items"] if i["source"] == "both")
        print(f"  merged -> {inv_path.name}: {len(merged['items'])} items, {both} in both passes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
