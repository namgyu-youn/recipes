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
    "kv_cache": r"kv[ _-]cache|prefix[ _-]cach|kv offload|kv transfer|kv connector|paged|block size|none_hash",
    "scheduling": r"schedul|admission|queue|chunked prefill|batch size|preempt",
    "compilation": r"compil|cudagraph|cuda graph|torch\.compile|inductor|piecewise|model runner",
}

# "A default changed" is not a concept — it is a property of one. The concept is
# whatever the default belongs to, and `default_on` carries the rest.
DEFAULT_RE = re.compile(
    r"now the default|is (now )?the default|by default|default(s)? (to|changed)"
    r"|enabled by default|disabled by default",
    re.I,
)

# Tooling for benchmarking, profiling or debugging is not something a recipe
# turns on for users.
TOOLING_RE = re.compile(r"trace replay|benchmark|profil|debug|api server|security|media download", re.I)

# Training-side plumbing. A serving recipe never turns this on.
NOT_SERVING_RE = re.compile(r"weight sync|weight transfer|sharded[_ ]rdt|rl workflow", re.I)

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

# Highlights and the breaking section are written at capability level, so every
# bullet in them is a candidate. The per-area sections (Engine Core, Hardware &
# Performance, Quantization, ...) are changelogs: hundreds of bullets per
# release, most of them internal. A bullet there earns candidacy only by naming
# a flag, env or enum value that still exists at the target tag — that is what
# makes it something a recipe could actually set.
SECTION_PRIMARY = re.compile(r"highlight|breaking|deprecat", re.I)
SECTION_DROP = re.compile(r"contributor|release artifact|new contributor", re.I)

# A release-note heading is not a capability title. "New defaults" says nothing
# about what changed; the title has to name the thing.
GENERIC_TITLE = re.compile(
    r"^(new )?(defaults?|models?|features?|highlights?|breaking changes?|deprecations?|"
    r"performance|kernels?|robustness|correctness|hardware|quantization|api|engine core|"
    r"large scale serving|rl weight sync|speculative decoding|mamba prefix caching)\s*:?$",
    re.I,
)

# Removals and deprecations are breaking news, not shipped capabilities; they
# belong in the stale/breaking section of the report.
BREAKING_RE = re.compile(
    r"\bremoved\b|\bdropped\b|no longer (supported|available|served)|\bdeprecat\w+",
    re.I,
)


# --------------------------------------------------------------------------
# draft
# --------------------------------------------------------------------------


def notes_sections(body: str, primary_only: bool = True) -> list[tuple[str, list[str]]]:
    """[(heading, bullet lines)] per section.

    `primary_only` keeps Highlights and the breaking/deprecation sections; with
    it false every content section comes back, and the caller is responsible for
    filtering the per-area changelog down to bullets that name something real.
    """
    out: list[tuple[str, list[str]]] = []
    heading = ""
    bullets: list[str] = []

    def flush() -> None:
        if not heading or not bullets or SECTION_DROP.search(heading):
            return
        if primary_only and not SECTION_PRIMARY.search(heading):
            return
        out.append((heading, bullets))

    for raw in body.splitlines():
        if raw.startswith("#"):
            flush()
            heading = raw.lstrip("#").strip()
            bullets = []
            continue
        if re.match(r"^\s*[*-]\s+", raw):
            bullets.append(re.sub(r"^\s*[*-]\s+", "", raw).strip())
    flush()
    return out


def area_clauses(bullet: str) -> list[str]:
    """Split a changelog bullet into the clauses its PRs belong to."""
    parts = re.split(r";\s+|(?<=\))\s*,\s+(?=[a-z`])|\.\s+(?=[A-Z])", bullet)
    return [p.strip() for p in parts if p.strip()]


def names_something_real(text: str, flags: dict, envs: dict, semantics: dict) -> bool:
    """Does this clause name a flag, env or enum value that exists at the tag?"""
    if any(f in flags for f in FLAG_RE.findall(text)):
        return True
    if any(e in envs for e in ENV_RE.findall(text)):
        return True
    for token in BACKTICK_RE.findall(text):
        value = token.strip()
        for sem in semantics.values():
            if value in (sem.get("choices") or []):
                return True
    return False


def topic_of(bullet: str) -> str | None:
    m = re.match(r"\*\*(.+?)\*\*", bullet)
    return m.group(1).rstrip(":").strip() if m else None


def clean_title(text: str, topic: str | None = None) -> str:
    """A title that names the thing.

    Strips the bold topic, markdown and PR refs, then keeps the first item of
    what is often a long enumeration — a Highlights bullet can carry eight
    distinct kernel changes, and the first one is the title, not all eight.
    Underscores survive: `VLLM_ALLREDUCE_USE_FLASHINFER` is a name, not
    emphasis. An informative topic ("Kimi-K3 and DeepSeek V4 performance")
    becomes a prefix; a generic one ("New defaults") is dropped.
    """
    body = re.sub(r"^\*\*(.+?)\*\*\s*:?\s*", "", text).strip()
    body = re.sub(r"\s*\(#\d+(?:,\s*#\d+)*\)", "", body)
    body = re.sub(r"[`*]", "", body)
    body = re.split(r"(?<=[a-z0-9\)])\.\s+(?=[A-Z])", body)[0]
    first = body.split(";")[0].strip(" .;,")
    if len(first) > 150:
        clauses = first.split(", ")
        kept = clauses[0]
        for clause in clauses[1:]:
            if len(kept) + len(clause) + 2 > 150:
                break
            kept += ", " + clause
        first = kept.strip(" .;,")
    prefix = f"{topic}: " if topic and not GENERIC_TITLE.match(topic) else ""
    return (prefix + first).strip(" .;,")


def doc_title(tag: str, path: str) -> str | None:
    """The H1 of a docs page, so a docs-derived capability is named, not pathed."""
    src = F.read(tag, path)
    if not src:
        return None
    for line in src.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None


# Where a flag is defined upstream is better evidence of what it is than the
# words around it. vllm/config/kernel.py owns the backend selectors,
# parallel.py the parallelism knobs, and so on.
MODULE_CONCEPT = {
    "kernel.py": "kernel",
    "attention.py": "attention_backend",
    "parallel.py": "parallelism",
    "cache.py": "kv_cache",
    "kv_transfer.py": "kv_cache",
    "offload.py": "kv_cache",
    "scheduler.py": "scheduling",
    "compilation.py": "compilation",
    "speculative.py": "spec_decoding",
    "quantization.py": "quantization",
    "multimodal.py": "multimodal",
    "model.py": "runtime",
    "vllm.py": "runtime",
}


def concept_from_modules(how: dict, semantics: dict) -> str | None:
    """Concept implied by the config module that defines the enabling flag."""
    votes: dict[str, int] = {}
    for flag in how.get("flags") or []:
        entry = semantics.get(flag) or {}
        module = (entry.get("file") or "").rsplit("/", 1)[-1]
        concept = MODULE_CONCEPT.get(module)
        if concept:
            votes[concept] = votes.get(concept, 0) + 1
    return max(votes, key=votes.get) if votes else None


def classify_concept(text: str, title: str = "") -> str:
    # What the title says outweighs what the body mentions in passing: the
    # Model Runner V2 bullet name-drops EAGLE and MTP while being about the
    # runner, not about speculative decoding.
    scores = {
        concept: len(re.findall(pattern, text, re.I)) + 3 * len(re.findall(pattern, title, re.I))
        for concept, pattern in CONCEPTS.items()
    }
    specific = {k: v for k, v in scores.items() if v}
    if specific:
        return max(specific, key=specific.get)
    return "other"


def classify_effect(text: str) -> str:
    for effect, pattern in EFFECTS.items():
        if re.search(pattern, text, re.I):
            return effect
    return "usability"


# An enum value can imply its own hardware: a ROCm backend is AMD, a Hopper
# backend is hopper. Upstream states this in the value name itself.
VALUE_HARDWARE = [
    (re.compile(r"^ROCM_|_AITER", re.I), "amd"),
    (re.compile(r"^CPU_|^AMX_", re.I), "cpu"),
    (re.compile(r"^XPU_", re.I), "xpu"),
    (re.compile(r"SM120|^B12X", re.I), "blackwell"),
]


def applies_to(text: str, semantics: dict, how: dict | None = None) -> dict:
    hardware = [k for k, pattern in HARDWARE_TERMS.items() if re.search(pattern, text, re.I)]
    for entry in (how or {}).get("enum_values", []):
        for pattern, hw in VALUE_HARDWARE:
            if pattern.search(entry["value"]) and hw not in hardware:
                hardware.append(hw)
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


def enum_pairs(text: str, named_flags: list[str], semantics: dict) -> list[dict]:
    """`--moe-backend b12x` — the pair, not just the flag.

    Without the value, "already uses --moe-backend" excludes every recipe that
    passes any MoE backend at all, which is how a real adoption cohort gets
    silently emptied.
    """
    enums: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for flag in named_flags:
        choices = (semantics.get(flag) or {}).get("choices") or []
        for m in re.finditer(rf"{re.escape(flag)}[`\s=]+`?([A-Za-z0-9_.-]+)`?", text):
            pair = (flag, m.group(1))
            if m.group(1) in choices and pair not in seen:
                seen.add(pair)
                enums.append({"flag": flag, "value": m.group(1)})
    # A backticked token can still name a value on its own — "`FLASH_ATTN_MLA_SPARSE`
    # Hopper sparse-MLA backend" never repeats the flag. Pair it only when it is
    # non-numeric and accepted by exactly ONE flag at the tag, so `256` cannot
    # attach itself to whichever flag happens to take that number.
    for token in BACKTICK_RE.findall(text):
        value = token.strip()
        if not value or value.replace(".", "").isdigit() or len(value) < 4:
            continue
        owners = [f for f, sem in semantics.items() if value in (sem.get("choices") or [])]
        if not owners:
            continue
        # Several flags can share one enum class (--attention-backend and
        # --mm-encoder-attn-backend both take AttentionBackendEnum). That is not
        # ambiguity about the value, only about which knob it was meant for, so
        # take the least-qualified flag — the general one, not the sub-scoped.
        classes = {(semantics[f].get("choices_from") or f) for f in owners}
        if len(classes) > 1:
            continue
        owner = min(owners, key=lambda f: (f.count("-"), f))
        if (owner, value) not in seen:
            seen.add((owner, value))
            enums.append({"flag": owner, "value": value})
    return enums[:4]


def enabling(text: str, flags: dict, envs: dict, semantics: dict) -> dict:
    """Flags, envs and enum values named in the text that really exist upstream."""
    named_flags = sorted({f for f in FLAG_RE.findall(text) if f in flags})
    named_envs = sorted({e for e in ENV_RE.findall(text) if e in envs})
    enums = enum_pairs(text, named_flags, semantics)
    mode = "auto" if AUTO_MARKERS.search(text) and not named_flags else None
    if mode is None:
        mode = "explicit" if (named_flags or named_envs or enums or EXPLICIT_MARKERS.search(text)) else "auto"
    return {
        "mode": mode,
        "flags": named_flags,
        "envs": named_envs,
        "enum_values": enums,
    }


def reverse_markers(text: str, envs: dict) -> dict:
    """Names whose presence in a recipe is now redundant or obsolete.

    A capability that is on by default has no flag to add — but it can still
    imply an edit: a recipe that explicitly sets what is now the default, or
    keeps a workaround the release makes unnecessary. These are the names to
    look for in the recipes.
    """
    now_default: list[str] = []
    obsolete: list[str] = []

    for m in re.finditer(r"opt out with `?([A-Z][A-Z0-9_]{3,}|--[a-z0-9-]+)`?", text, re.I):
        now_default.append(m.group(1))
    for m in re.finditer(
        r"no longer (?:need(?:s)? to (?:pin|set|pass)|need(?:s)?|require(?:s)?) `?([A-Z][A-Z0-9_]{3,}|--[a-z0-9-]+)`?",
        text,
        re.I,
    ):
        obsolete.append(m.group(1))
    # A SCREAMING_CASE name that is not a vLLM env is a workaround knob from
    # somewhere else (PYTHONHASHSEED, CUDA_*), worth checking for in recipes.
    for token in re.findall(r"\b([A-Z][A-Z0-9_]{5,})\b", text):
        if token not in envs and token not in obsolete and not token.startswith("VLLM_"):
            obsolete.append(token)
    return {
        "now_default": sorted(set(now_default)),
        "obsolete": sorted(set(obsolete)),
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

        # per-area changelog sections, filtered to clauses naming something real
        for heading, bullets in notes_sections(body, primary_only=False):
            if SECTION_PRIMARY.search(heading):
                continue
            for bullet in bullets:
                for clause in area_clauses(bullet):
                    if not names_something_real(clause, flags, envs, semantics):
                        continue
                    raw.append(
                        {
                            "source": "release-notes-area",
                            "tag": tag,
                            "heading": heading,
                            "topic": topic_of(bullet),
                            "text": clause[:600],
                            "prs": sorted(set(PR_RE.findall(clause)))[:6],
                        }
                    )

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
        h1 = doc_title(target, item["heading"])
        # A page titled "Security" or "Usage" names a chapter, not a capability;
        # the flag it introduces is the subject.
        if h1 and len(h1.split()) <= 2:
            names = item["flags"] + item["envs"]
            h1 = f"{h1}: {', '.join(names[:3])}" if names else None
        item["title"] = h1 or item["title"]
        raw.append(item)

    used: set[str] = set()
    caps = []
    for item in raw:
        text = item["text"]
        title = item.get("title")
        if not title or GENERIC_TITLE.match(title):
            title = clean_title(text, item.get("topic"))
        how = enabling(text, flags, envs, semantics)
        if item["source"] == "docs-diff":
            how = {
                "mode": "explicit" if item["flags"] or item["envs"] else "auto",
                "flags": item["flags"],
                "envs": item["envs"],
                "enum_values": enum_pairs(text, item["flags"], semantics),
            }
        concept = concept_from_modules(how, semantics) or classify_concept(text, title)
        # The vocabulary is fixed. Anything outside it is not a capability —
        # new model support, packaging, CI — and is kept in the YAML with a
        # reason rather than padding "What shipped".
        kind = (
            "out_of_scope"
            if item.get("topic") and re.match(r"new models?$", item["topic"].strip(), re.I)
            else "breaking"
            if BREAKING_RE.search(text)
            else "out_of_scope"
            if concept == "other" or TOOLING_RE.search(title) or NOT_SERVING_RE.search(title)
            else "capability"
        )
        drop_reason = (
            "new model support — not a serving capability"
            if item.get("topic") and re.match(r"new models?$", item["topic"].strip(), re.I)
            else "outside the concept vocabulary"
            if concept == "uncategorized"
            else "RL weight-sync plumbing, not a serving capability"
            if NOT_SERVING_RE.search(title)
            else "benchmark/profiling/serving-infra tooling, not a recipe capability"
            if TOOLING_RE.search(title)
            else None
        )
        caps.append(
            {
                "id": slugify(title, used),
                "kind": kind,
                "concept": concept,
                "title": title.strip(),
                "since": item["tag"],
                "how_enabled": how,
                "default_on": bool(AUTO_MARKERS.search(text) or DEFAULT_RE.search(text)) and not how["flags"],
                "drop_reason": drop_reason,
                "reverse_markers": reverse_markers(text, envs),
                "applies_to": applies_to(text, semantics, how),
                "effect": classify_effect(text),
                "evidence": {
                    "source": item["source"],
                    "section": item["heading"],
                    "prs": item.get("prs", []),
                    "text": text,
                },
            }
        )
    return {"prev": prev, "target": target, "capabilities": dedupe(caps)}


def version_rank(tag: str | None) -> tuple[int, ...]:
    try:
        return F.version_key(tag or "v999.0.0")
    except Exception:
        return (999, 0, 0)


def dedupe(caps: list[dict]) -> list[dict]:
    """Merge entries describing the same change.

    The same capability is often announced twice — once in Highlights and once
    under Breaking Changes — and again in the docs page that documents it. They
    are the same fact with three citations, so they merge into one entry that
    keeps all three.
    """

    stop = {"the", "a", "an", "new", "now", "is", "are", "for", "all", "of", "in", "to",
            "and", "with", "on", "by", "its", "that", "this", "it"}

    def names_of(cap: dict) -> str | None:
        how = cap["how_enabled"]
        names = sorted(how.get("flags", []) + how.get("envs", []))
        return "|".join(names) or None

    def words_of(cap: dict) -> set[str]:
        # sharded_rdt and "Sharded RDT" are the same words differently spelled.
        title = cap["title"].lower().replace("_", " ")
        words = [w for w in re.findall(r"[a-z0-9]+", title) if w not in stop]
        return set(words[:8])

    def same_thing(a: dict, b: dict) -> bool:
        """Two entries describe one change when their titles substantially overlap.

        Exact keys miss the common case: Highlights says "Model Runner V2 is now
        the default for all models" and the breaking section says "Model Runner
        V2 is the default runner for all models".

        The measure is the overlap coefficient, not Jaccard: one announcement is
        usually a fuller version of the other ("Ten deprecated architectures
        removed: Arctic, Chameleon, ..." vs "ten deprecated model architectures
        removed"), and Jaccard punishes exactly that extra detail.
        """
        wa, wb = words_of(a), words_of(b)
        if not wa or not wb:
            return False
        shared = wa & wb
        return len(shared) >= 2 and len(shared) / min(len(wa), len(wb)) >= 0.66

    merged: dict[str, dict] = {}
    for cap in caps:
        key = names_of(cap)
        if key is None or key not in merged:
            existing = next(
                (k for k, v in merged.items() if same_thing(v, cap)),
                None,
            )
            key = existing or key or f"title::{'|'.join(sorted(words_of(cap)))}"
        if key not in merged:
            merged[key] = {**cap, "evidence": {**cap["evidence"], "also": []}}
            continue
        first = merged[key]
        if version_rank(cap.get("since")) < version_rank(first.get("since")):
            first["since"] = cap["since"]  # first announced, not last mentioned
        first["evidence"]["also"].append(
            {"section": cap["evidence"].get("section"), "source": cap["evidence"].get("source")}
        )
        first["evidence"]["prs"] = sorted(set(first["evidence"].get("prs", []) + cap["evidence"].get("prs", [])))
        # a docs page names the thing better than a release-note sentence does
        if cap["evidence"].get("source") == "docs-diff":
            first["title"] = cap["title"]
        if cap["kind"] == "breaking":
            first["kind"] = "breaking"
        for field in ("flags", "envs", "enum_values"):
            have = first["how_enabled"].setdefault(field, [])
            for extra in cap["how_enabled"].get(field, []):
                if extra not in have:
                    have.append(extra)
        for field in ("hardware", "quant"):
            have = first["applies_to"].setdefault(field, [])
            for extra in cap["applies_to"].get(field, []):
                if extra not in have:
                    have.append(extra)
    return list(merged.values())


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
    ap.add_argument(
        "--recall",
        action="store_true",
        help="write recall.md: every Highlights bullet with the capability that covers it, or why not",
    )
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

    if args.recall:
        import yaml

        report_dir = Path(args.report_dir)
        caps = yaml.safe_load((report_dir / "capabilities.yaml").read_text())["capabilities"]
        body = (report_dir / "release-notes" / f"{args.target}.md").read_text()
        rows = []
        for heading, bullets in notes_sections(body):
            if not re.search(r"highlight", heading, re.I):
                continue
            for bullet in bullets:
                topic = topic_of(bullet) or clean_title(bullet)[:60]
                prs = set(PR_RE.findall(bullet))
                words = {
                    w
                    for w in re.findall(r"[a-z0-9]+", clean_title(bullet, topic).lower())
                    if len(w) > 3
                }
                best, best_score = None, 0.0
                for cap in caps:
                    cap_prs = set(cap["evidence"].get("prs") or [])
                    cap_words = {
                        w for w in re.findall(r"[a-z0-9]+", cap["title"].lower()) if len(w) > 3
                    }
                    overlap = len(words & cap_words) / max(1, min(len(words), len(cap_words)))
                    score = (2.0 if prs & cap_prs else 0.0) + overlap
                    if score > best_score:
                        best, best_score = cap, score
                matched = best if best_score >= 0.5 else None
                rows.append(
                    {
                        "item": topic,
                        "capability": matched["id"] if matched else None,
                        "kind": matched["kind"] if matched else None,
                        "reason": None
                        if matched and matched["kind"] == "capability"
                        else (matched or {}).get("drop_reason")
                        or ("recorded as breaking" if matched else "no capability extracted from this bullet"),
                    }
                )
        md = ["# Recall — v0.29.0 Highlights, one row per item", "",
              "| Highlights item | Capability | Outcome |", "|---|---|---|"]
        for r in rows:
            md.append(
                f"| {r['item']} | {('`' + r['capability'] + '`') if r['capability'] else '—'} | "
                f"{r['reason'] or 'covered'} |"
            )
        (report_dir / "recall.md").write_text("\n".join(md) + "\n")
        covered = sum(1 for r in rows if r["reason"] is None)
        print(f"recall: {covered}/{len(rows)} Highlights items map to a shipped capability")
        print("\n".join(md))
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
