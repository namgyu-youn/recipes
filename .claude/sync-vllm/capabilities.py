#!/usr/bin/env python3
"""Capability-level discovery and verification.

A *capability* is a concept users care about — a new or reworked kernel/backend,
a quantization format, a parallelism mode, a spec-decoding method, a KV-cache or
scheduling feature, a compilation change, or a changed default. Not a PR, not a
flag diff. One release should yield 20-30 of them.

Discovery reads only the parts of a release that are written at that level:

  * the Highlights section
  * any Breaking Changes / Deprecation section
  * the `docs/` diff between the two tags

PR numbers are carried as evidence but deliberately NOT resolved in bulk; use
`--resolve-pr N` when one specific enabling condition needs confirming.

Two phases:

  --draft   deterministic extraction -> capabilities.draft.yaml
            (the orchestrator curates this into capabilities.yaml: concept,
            how_enabled, applies_to and effect are judgement, the rest is not)
  --verify  mechanical re-check of capabilities.yaml against the target tag:
            the enabling flag / env / enum value must exist, and a cited
            file:line must really contain the symbol. Anything else is dropped.

Upstream is read via flagset.py (git show only). Never through Bash git output,
which rtk truncates. See README.md.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import flagset as F
import index_flags as IDX
import inventory as INV

# Concept vocabulary. Where the repo already names a concept (taxonomy.yaml's
# kv_offload ids, strategies/*.yaml parallelism, the recipes' feature keys), the
# same word is used so a capability can be matched against recipes directly.
CONCEPTS = {
    "attention_backend": r"attention backend|flashattention|fa[234]\b|flashinfer|flash-?attn|xqa|sparse mla|\bmla\b|triton attn",
    "moe_backend": r"\bmoe\b|expert|fused_moe|megamoe|deepgemm|deep_gemm|cutedsl|marlin",
    "linear_backend": r"linear backend|gemm|cublas|cutlass",
    "quantization": r"quantiz|fp8|nvfp4|mxfp4|mxfp8|int4|int8|fp4\b|awq|gptq|compressed-tensors|quark",
    "parallelism": r"tensor parallel|expert parallel|pipeline parallel|data parallel|context parallel|\bdcp\b|\bpcp\b|\btp\b|\bep\b|\bpp\b|\bdp\b|disaggregat|prefill/decode",
    "spec_decoding": r"specul|eagle|\bmtp\b|dspark|dflash|draft model|acceptance",
    "kv_cache": r"kv cache|kv-cache|prefix cach|kv offload|kv transfer|kv connector|paged|block size",
    "scheduling": r"schedul|admission|queue|chunked prefill|batch size|preempt",
    "compilation": r"compil|cudagraph|cuda graph|torch\.compile|inductor|piecewise",
    "frontend": r"api server|openai|frontend|tokenizer|response|endpoint|rust",
    "default_change": r"now the default|by default|default(s)? (to|changed)|enabled by default|disabled by default",
}

EFFECTS = {
    "correctness": r"\bfix|incorrect|wrong|corrupt|race|hang|crash|accuracy regression",
    "accuracy": r"accuracy|quality|perplexity|eval score",
    "memory": r"memory|vram|footprint|oom|allocat",
    "perf": r"speedup|faster|latency|throughput|tpot|ttft|perf|optimiz|\d+(\.\d+)?\s?%|\d+(\.\d+)?x",
    "usability": r"usability|easier|simplif|ergonom|error message|warn",
}

AUTO_MARKERS = re.compile(
    r"now the default|by default|automatic|auto-?enabled|no longer needs?|transparent", re.I
)
EXPLICIT_MARKERS = re.compile(r"opt-?in|enable (it |this )?with|pass |set |`--|`VLLM_", re.I)

FLAG_RE = re.compile(r"(?<![-\w])(--[a-z0-9][a-z0-9-]{2,})(?![-\w])")
ENV_RE = re.compile(r"\b(VLLM_[A-Z0-9_]{3,})\b")
PR_RE = re.compile(r"#(\d{3,7})")
BACKTICK_RE = re.compile(r"`([^`]{2,60})`")

HARDWARE_TERMS = {
    "blackwell": r"blackwell|sm100|sm103|b200|b300|gb200|gb300|gb10",
    "hopper": r"hopper|sm90|h100|h200|h20",
    "ada": r"\bada\b|sm89|l40|rtx 4090",
    "amd": r"\brocm\b|\bamd\b|mi\d{3}|aiter|gfx\d+",
    "nvidia": r"nvidia|cuda|flashinfer|cutlass",
    "xpu": r"\bxpu\b|intel gpu|oneccl",
    "cpu": r"\bcpu\b|amx|xeon",
    "tpu": r"\btpu\b|trillium|v6e",
    "npu": r"ascend|\bnpu\b",
}

QUANT_TERMS = ["nvfp4", "mxfp4", "mxfp8", "fp8", "int8", "int4", "fp4", "bf16", "awq", "gptq"]

SECTION_KEEP = re.compile(r"highlight|breaking|deprecat", re.I)
SECTION_DROP = re.compile(r"contributor|release artifact", re.I)


# --------------------------------------------------------------------------
# draft
# --------------------------------------------------------------------------


def notes_sections(body: str) -> list[tuple[str, list[str]]]:
    """[(heading, bullet lines)] for the sections worth reading at this level."""
    out: list[tuple[str, list[str]]] = []
    heading = ""
    bullets: list[str] = []
    for raw in body.splitlines():
        if raw.startswith("#"):
            if heading and bullets and SECTION_KEEP.search(heading) and not SECTION_DROP.search(heading):
                out.append((heading, bullets))
            heading = raw.lstrip("#").strip()
            bullets = []
            continue
        if re.match(r"^\s*[*-]\s+", raw):
            bullets.append(re.sub(r"^\s*[*-]\s+", "", raw).strip())
    if heading and bullets and SECTION_KEEP.search(heading) and not SECTION_DROP.search(heading):
        out.append((heading, bullets))
    return out


def topic_of(bullet: str) -> str | None:
    m = re.match(r"\*\*(.+?)\*\*", bullet)
    return m.group(1).rstrip(":").strip() if m else None


def classify_concept(text: str) -> str:
    scores = {
        concept: len(re.findall(pattern, text, re.I)) for concept, pattern in CONCEPTS.items()
    }
    # a changed default is a concept of its own only when nothing more specific fires
    specific = {k: v for k, v in scores.items() if k != "default_change" and v}
    if specific:
        return max(specific, key=specific.get)
    return "default_change" if scores["default_change"] else "other"


def classify_effect(text: str) -> str:
    for effect, pattern in EFFECTS.items():
        if re.search(pattern, text, re.I):
            return effect
    return "usability"


def applies_to(text: str, semantics: dict) -> dict:
    hardware = [k for k, pattern in HARDWARE_TERMS.items() if re.search(pattern, text, re.I)]
    quant = [q for q in QUANT_TERMS if re.search(rf"\b{q}\b", text, re.I)]
    traits = {}
    if re.search(r"\bmoe\b|expert|mixture", text, re.I):
        traits["architecture"] = "moe"
    elif re.search(r"\bdense\b", text, re.I):
        traits["architecture"] = "dense"
    if re.search(r"multimodal|vision|\bvl\b|image|video|audio", text, re.I):
        traits["tasks"] = ["multimodal"]
    if re.search(r"specul|eagle|\bmtp\b|dspark|dflash", text, re.I):
        traits.setdefault("features", []).append("spec_decoding")
    return {"hardware": hardware, "model_traits": traits, "quant": quant}


def enabling(text: str, flags: dict, envs: dict, semantics: dict) -> dict:
    """Flags, envs and enum values named in the text that really exist upstream."""
    named_flags = sorted({f for f in FLAG_RE.findall(text) if f in flags})
    named_envs = sorted({e for e in ENV_RE.findall(text) if e in envs})
    enums = []
    for token in BACKTICK_RE.findall(text):
        value = token.strip()
        for flag, sem in semantics.items():
            choices = sem.get("choices") or []
            if value in choices:
                enums.append({"flag": flag, "value": value})
    mode = "auto" if AUTO_MARKERS.search(text) and not named_flags else None
    if mode is None:
        mode = "explicit" if (named_flags or named_envs or enums or EXPLICIT_MARKERS.search(text)) else "auto"
    return {
        "mode": mode,
        "flags": named_flags,
        "envs": named_envs,
        "enum_values": enums[:4],
    }


def slugify(text: str, used: set[str]) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:48] or "capability"
    slug = base
    n = 2
    while slug in used:
        slug = f"{base}-{n}"
        n += 1
    used.add(slug)
    return slug


def docs_candidates(prev: str, target: str, flags: dict, envs: dict, index: dict) -> list[dict]:
    """One candidate per docs file that documents something new in this release.

    A docs file merely being edited says nothing — `--model` and `--port` appear
    in every rewritten example. The file has to either be new, or name a flag or
    env whose introducing tag IS the target; that is what makes it a capability
    rather than prose churn.
    """
    diff = F._git("diff", "--unified=0", prev, target, "--", "docs/").stdout.splitlines()
    per_file: dict[str, list[str]] = {}
    current = None
    for line in diff:
        if line.startswith("+++ b/"):
            current = line[6:]
            per_file.setdefault(current, [])
        elif line.startswith("+") and not line.startswith("+++") and current:
            per_file[current].append(line[1:])
    out = []
    for path, added in per_file.items():
        text = "\n".join(added)
        named_flags = sorted({f for f in FLAG_RE.findall(text) if f in flags})
        named_envs = sorted({e for e in ENV_RE.findall(text) if e in envs})
        if not named_flags and not named_envs:
            continue
        new_flags = [f for f in named_flags if (index["flags"].get(f) or {}).get("introduced") == target]
        new_envs = [e for e in named_envs if (index["envs"].get(e) or {}).get("introduced") == target]
        file_is_new = F.read(prev, path) is None
        if not (new_flags or new_envs or file_is_new):
            continue
        out.append(
            {
                "source": "docs-diff",
                "heading": path,
                "title": f"docs: {path.removeprefix('docs/')}",
                "text": text[:600],
                "flags": new_flags or named_flags,
                "envs": new_envs or named_envs,
                "new_this_release": bool(new_flags or new_envs),
                "file_is_new": file_is_new,
                "prs": [],
            }
        )
    return out


def draft(prev: str, target: str, report_dir: Path) -> dict:
    flags = F.flags_at(target)
    envs = F.envs_at(target)
    semantics = INV.flag_semantics(target)

    raw: list[dict] = []
    cache = report_dir / "release-notes"
    tags = [p.stem for p in sorted(cache.glob("*.md"))] if cache.is_dir() else []
    for tag in tags:
        body = (cache / f"{tag}.md").read_text()
        for heading, bullets in notes_sections(body):
            for bullet in bullets:
                topic = topic_of(bullet)
                # A "New defaults" bullet bundles several unrelated defaults, so
                # it splits into one candidate each. Every other bullet is
                # already one concept — including "X is now the default for all
                # models", whose topic merely contains the word.
                is_defaults_list = bool(topic and re.match(r"(new )?defaults?$", topic.strip(), re.I))
                pieces = (
                    [c.strip() for c in re.split(r";\s+|(?<=\))\s*,\s+(?=[a-z`])", bullet) if c.strip()]
                    if is_defaults_list
                    else [bullet]
                )
                for piece in pieces:
                    raw.append(
                        {
                            "source": "release-notes",
                            "tag": tag,
                            "heading": heading,
                            "topic": topic,
                            "text": piece[:600],
                            "prs": sorted(set(PR_RE.findall(piece)))[:6],
                        }
                    )
    index = IDX.index_for(target, quiet=True)
    for item in docs_candidates(prev, target, flags, envs, index):
        item["tag"] = target
        raw.append(item)

    used: set[str] = set()
    caps = []
    for item in raw:
        text = item["text"]
        title = item.get("title") or item.get("topic") or re.sub(r"\*\*|`", "", text.split(".")[0])[:90]
        how = enabling(text, flags, envs, semantics)
        if item["source"] == "docs-diff":
            how = {
                "mode": "explicit" if item["flags"] or item["envs"] else "auto",
                "flags": item["flags"],
                "envs": item["envs"],
                "enum_values": [],
            }
        caps.append(
            {
                "id": slugify(title, used),
                "concept": classify_concept(text),
                "title": title.strip(),
                "since": item["tag"],
                "how_enabled": how,
                "default_on": bool(AUTO_MARKERS.search(text)) and not how["flags"],
                "applies_to": applies_to(text, semantics),
                "effect": classify_effect(text),
                "evidence": {
                    "source": item["source"],
                    "section": item["heading"],
                    "prs": item.get("prs", []),
                    "text": text,
                },
            }
        )
    return {"prev": prev, "target": target, "capabilities": caps}


# --------------------------------------------------------------------------
# verify
# --------------------------------------------------------------------------


def cite_holds(tag: str, file: str, line: int, symbol: str) -> tuple[bool, str]:
    blob = F.read(tag, file)
    if blob is None:
        return False, f"{file} does not exist at {tag}"
    lines = blob.splitlines()
    if not (1 <= line <= len(lines)):
        return False, f"{file} has no line {line} at {tag} ({len(lines)} lines)"
    window = "\n".join(lines[max(0, line - 3) : line + 2])
    needle = re.escape(symbol.lstrip("-")).replace(r"\-", "[-_]")
    if re.search(needle, window, re.I):
        return True, lines[line - 1].strip()[:160]
    return False, f"{file}:{line} at {tag} does not mention {symbol}"


def verify(caps: list[dict], target: str) -> tuple[list[dict], list[dict]]:
    flags = F.flags_at(target)
    envs = F.envs_at(target)
    semantics = INV.flag_semantics(target)
    kept, dropped = [], []

    for cap in caps:
        how = cap.get("how_enabled") or {}
        checks, failures = [], []

        for flag in how.get("flags") or []:
            base = flag.split(".")[0]
            if flag in flags or base in flags:
                checks.append(f"{flag} exists at {target}")
            else:
                failures.append(f"{flag} is not a flag at {target}")
        for env in how.get("envs") or []:
            if env in envs:
                checks.append(f"{env} exists at {target}")
            else:
                failures.append(f"{env} is not an env var at {target}")
        for entry in how.get("enum_values") or []:
            choices = (semantics.get(entry.get("flag"), {}) or {}).get("choices") or []
            if entry.get("value") in choices:
                checks.append(f"{entry['flag']}={entry['value']} is an accepted value at {target}")
            else:
                failures.append(
                    f"{entry.get('flag')}={entry.get('value')} is not an accepted value at {target}"
                )

        cite = (cap.get("evidence") or {}).get("cite")
        if cite:
            symbol = cite.get("symbol") or (how.get("flags") or how.get("envs") or [""])[0]
            ok, detail = cite_holds(cite.get("tag", target), cite.get("file"), int(cite.get("line", 0)), symbol)
            (checks if ok else failures).append(detail)

        if failures:
            dropped.append({**cap, "dropped_because": failures})
            continue

        if how.get("mode") == "explicit" and not checks:
            dropped.append(
                {**cap, "dropped_because": ["claims an explicit enabling flag/env but names none that exists"]}
            )
            continue

        # No independent re-check exists for a changed default: the source pass
        # can see the new value but nothing proves the release notes' claim
        # about the old behaviour. Cap it.
        confidence = "high" if checks else "medium"
        if cap.get("concept") == "default_change" or cap.get("default_on"):
            confidence = min(confidence, "medium", key=["low", "medium", "high"].index)
        kept.append({**cap, "verified": checks, "confidence": confidence})
    return kept, dropped


def self_test(target: str) -> int:
    """A bogus capability must be dropped. Guards against a pass-through verify."""
    bogus = [
        {
            "id": "bogus-flag",
            "concept": "attention_backend",
            "title": "bogus",
            "how_enabled": {"mode": "explicit", "flags": ["--not-a-real-flag-xyz"], "envs": [], "enum_values": []},
            "evidence": {},
        },
        {
            "id": "bogus-cite",
            "concept": "moe_backend",
            "title": "bogus cite",
            "how_enabled": {"mode": "explicit", "flags": ["--moe-backend"], "envs": [], "enum_values": []},
            "evidence": {"cite": {"tag": target, "file": "vllm/config/kernel.py", "line": 999999, "symbol": "--moe-backend"}},
        },
        {
            "id": "bogus-enum",
            "concept": "moe_backend",
            "title": "bogus enum",
            "how_enabled": {
                "mode": "explicit",
                "flags": [],
                "envs": [],
                "enum_values": [{"flag": "--moe-backend", "value": "definitely_not_a_backend"}],
            },
            "evidence": {},
        },
        {
            "id": "real-control",
            "concept": "moe_backend",
            "title": "control that must survive",
            "how_enabled": {
                "mode": "explicit",
                "flags": ["--moe-backend"],
                "envs": [],
                "enum_values": [{"flag": "--moe-backend", "value": "deep_gemm"}],
            },
            "evidence": {},
        },
    ]
    kept, dropped = verify(bogus, target)
    kept_ids = {c["id"] for c in kept}
    dropped_ids = {c["id"] for c in dropped}
    ok = dropped_ids == {"bogus-flag", "bogus-cite", "bogus-enum"} and kept_ids == {"real-control"}
    for cap in dropped:
        print(f"  dropped {cap['id']}: {cap['dropped_because'][0]}")
    for cap in kept:
        print(f"  kept    {cap['id']}: {', '.join(cap['verified'])}")
    print(f"self-test {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


# --------------------------------------------------------------------------


def dump_yaml(data) -> str:
    try:
        import yaml  # optional; the repo has js-yaml, python yaml is usually present too

        return yaml.safe_dump(data, sort_keys=False, width=100, allow_unicode=True)
    except ImportError:
        return json.dumps(data, indent=2)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--target", required=True)
    ap.add_argument("--prev")
    ap.add_argument("--report-dir")
    ap.add_argument("--draft", action="store_true")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--resolve-pr", help="print the local commit and changed files for one PR")
    args = ap.parse_args()

    if not F.tag_exists(args.target):
        print(f"tag {args.target} not found locally — fetch it first", file=sys.stderr)
        return 2

    if args.resolve_pr:
        log = F._git(
            "log", "--all", "--fixed-strings", f"--grep=(#{args.resolve_pr})", "--format=%H%x1f%s", "-1"
        ).stdout.strip()
        if not log:
            print(f"PR #{args.resolve_pr} is not in the shallow clone")
            return 1
        commit, _, subject = log.partition("\x1f")
        print(f"{commit[:12]} {subject}")
        print(F._git("show", "--stat", "--format=", commit).stdout[:2000])
        return 0

    if args.self_test:
        return self_test(args.target)

    prev = args.prev or F.previous_stable(args.target)
    report_dir = Path(args.report_dir) if args.report_dir else None

    if args.draft:
        data = draft(prev, args.target, report_dir)
        out = report_dir / "capabilities.draft.yaml"
        out.write_text(dump_yaml(data))
        caps = data["capabilities"]
        by_concept: dict[str, int] = {}
        for cap in caps:
            by_concept[cap["concept"]] = by_concept.get(cap["concept"], 0) + 1
        print(f"{prev} -> {args.target}: {len(caps)} draft capabilities")
        for concept in sorted(by_concept, key=lambda c: -by_concept[c]):
            print(f"  {concept:20} {by_concept[concept]}")
        print(f"  -> {out}")
        return 0

    if args.verify:
        import yaml

        path = report_dir / "capabilities.yaml"
        if not path.is_file():
            path = report_dir / "capabilities.draft.yaml"
        data = yaml.safe_load(path.read_text())
        kept, dropped = verify(data["capabilities"], args.target)
        data["capabilities"] = kept
        data["dropped"] = dropped
        (report_dir / "capabilities.verified.yaml").write_text(dump_yaml(data))
        print(f"verified {len(kept)} capabilities, dropped {len(dropped)}")
        for cap in dropped[:10]:
            print(f"  dropped {cap['id']}: {cap['dropped_because'][0]}")
        conf: dict[str, int] = {}
        for cap in kept:
            conf[cap["confidence"]] = conf.get(cap["confidence"], 0) + 1
        print(f"  confidence: {conf}")
        print(f"  -> {report_dir / 'capabilities.verified.yaml'}")
        return 0

    ap.error("pass --draft, --verify, --self-test or --resolve-pr")


if __name__ == "__main__":
    sys.exit(main())
