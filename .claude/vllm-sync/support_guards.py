#!/usr/bin/env python3
"""Derive a capability's applies_to from upstream's own support checks.

Narrowing `applies_to` by hand is the agent's last manual step, and it is the
step most likely to be wrong — "blackwell" covers both B200 (SM100) and RTX Pro
6000 (SM120), and only one of them runs b12x. Upstream already states the
constraint in code, next to the kernel:

    if not current_platform.is_device_capability_family(120):
        return False, "B12X MXFP4 kernels require a Blackwell 12x device"

    def supports_compute_capability(cls, capability) -> bool:
        return capability.major == 9        # Hopper only

So the constraint is read from there instead of inferred from prose. Everything
returned carries a file:line, and a value whose implementation cannot be located
returns nothing rather than a guess.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys

import flagset as F

# Compute capability -> the hardware profile ids in taxonomy.yaml that have it.
# Generation alone cannot express this: "blackwell" spans SM100 datacentre parts
# and SM120 workstation parts, and kernels routinely support one and not the other.
CAPABILITY_PROFILES = {
    89: ["rtx_4090_2x"],
    90: ["h100", "h200"],
    100: ["b200", "gb200", "b300", "gb300", "dgx_station_gb300"],
    103: ["b200", "gb200", "b300", "gb300", "dgx_station_gb300"],
    120: [
        "rtx_pro_6000", "rtx_pro_6000_2x", "rtx_pro_6000_4x", "rtx_pro_6000_8x",
        "rtx_pro_5000", "rtx_pro_5000_4x", "rtx_5090", "rtx_5090_2x", "dgx_spark_gb10",
    ],
    121: ["dgx_spark_gb10"],
}
AMD_PROFILES = ["mi300x", "mi325x", "mi350x", "mi355x"]

PLATFORM_CALLS = {
    "is_rocm": ("hardware", AMD_PROFILES + ["amd"]),
    "is_cuda": ("hardware", ["nvidia"]),
    "is_cuda_alike": ("hardware", ["nvidia"]),
    "is_xpu": ("hardware", ["xpu"]),
    "is_cpu": ("hardware", ["cpu"]),
    "is_tpu": ("hardware", ["tpu"]),
}

QUANT_WORDS = re.compile(r"\b(nvfp4|mxfp4|mxfp8|fp8|int8|int4|fp4|awq|gptq|bf16)\b", re.I)

# Phrases that describe a limit rather than a target. They become notes, not
# dimensions: "does not support expert parallelism" is something a reviewer
# needs to read, not something a cohort can be matched on.
LIMIT_RE = re.compile(
    r"does not support|not supported|only supports?|requires?|incompatible|unsupported", re.I
)


def _module_path(dotted: str) -> str:
    """vllm.v1.attention.backends.mla.x.ClassName -> vllm/v1/attention/backends/mla/x.py"""
    parts = dotted.split(".")
    if parts and parts[-1][:1].isupper():
        parts = parts[:-1]
    return "/".join(parts) + ".py"


def locate(tag: str, value: str, flag: str | None = None) -> list[str]:
    """Candidate implementation modules for an enum value."""
    paths: list[str] = []

    # attention backends: the enum member's value IS the class path
    registry = F.read(tag, "vllm/v1/attention/backends/registry.py")
    if registry:
        try:
            tree = ast.parse(registry)
        except SyntaxError:
            tree = None
        for node in ast.walk(tree) if tree else []:
            if not (isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)):
                continue
            if node.targets[0].id != value:
                continue
            dotted = None
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                dotted = node.value.value
            elif isinstance(node.value, ast.JoinedStr):
                continue
            if dotted:
                paths.append(_module_path(dotted))

    # kernel backends: files are named after the backend under the kernel trees
    listing = F._git("ls-tree", "-r", "--name-only", tag, "vllm/model_executor/kernels/")
    if listing.returncode == 0:
        wanted = f"/{value.lower()}.py"
        paths += [p for p in listing.stdout.split() if p.endswith(wanted)]

    return [p for p in dict.fromkeys(paths) if F.read(tag, p) is not None]


def _capabilities_from(tree: ast.AST) -> list[int]:
    """Compute capabilities named in supports_compute_capability or platform calls."""
    caps: list[int] = []
    for node in ast.walk(tree):
        # current_platform.is_device_capability_family(120)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in {
                "is_device_capability_family",
                "is_device_capability",
                "has_device_capability",
            }:
                for arg in node.args:
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, int):
                        caps.append(arg.value)
        # def supports_compute_capability(...): return capability.major == 9
        if isinstance(node, ast.FunctionDef) and node.name == "supports_compute_capability":
            for cmp_node in ast.walk(node):
                if not isinstance(cmp_node, ast.Compare):
                    continue
                left = cmp_node.left
                is_major = isinstance(left, ast.Attribute) and left.attr == "major"
                for comparator in cmp_node.comparators:
                    if is_major and isinstance(comparator, ast.Constant) and isinstance(comparator.value, int):
                        caps.append(comparator.value * 10)
    return sorted(set(caps))


def guards_for(tag: str, value: str, flag: str | None = None) -> dict:
    hardware: list[str] = []
    quant: list[str] = []
    notes: list[dict] = []
    evidence: list[dict] = []
    modules = locate(tag, value, flag)

    for path in modules:
        src = F.read(tag, path)
        if src is None:
            continue
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        lines = src.splitlines()

        for cap in _capabilities_from(tree):
            profiles = CAPABILITY_PROFILES.get(cap)
            if profiles:
                hardware += profiles
                evidence.append(
                    {"file": path, "capability": cap, "why": f"compute capability {cap}"}
                )

        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                kind = PLATFORM_CALLS.get(node.func.attr)
                if kind:
                    hardware += kind[1]
                    evidence.append(
                        {
                            "file": path,
                            "line": node.lineno,
                            "why": f"current_platform.{node.func.attr}()",
                        }
                    )

        # the messages upstream returns when a configuration is refused
        for i, line in enumerate(lines, 1):
            for message in re.findall(r'"([^"]{16,160})"', line):
                if not LIMIT_RE.search(message):
                    continue
                quant += [q.lower() for q in QUANT_WORDS.findall(message)]
                notes.append({"file": path, "line": i, "text": message})

    # the module path itself is evidence when nothing else fires
    for path in modules:
        if "rocm" in path or "aiter" in path:
            hardware.append("amd")
        for q in QUANT_WORDS.findall(path):
            quant.append(q.lower())

    # A brand is redundant once specific profiles are known, and worse than
    # redundant: "nvidia" is a wildcard the cohort check refuses to treat as
    # evidence, so keeping it alongside the SM120 list weakens the result.
    WILDCARDS = {"nvidia", "amd", "cuda"}
    profiles = [h for h in hardware if h not in WILDCARDS]
    if profiles:
        hardware = profiles

    # An implementation living under backends/mla/ serves MLA-attention models
    # and nothing else — the same fact the "requires model with index_topk"
    # message states, but in a form a cohort can be matched on.
    traits = {}
    if any("/mla/" in path or path.endswith("_mla.py") for path in modules):
        traits["attention"] = "mla"

    return {
        "value": value,
        "modules": modules,
        "model_traits": traits,
        "hardware": sorted(dict.fromkeys(hardware)),
        "quant": sorted(dict.fromkeys(quant)),
        "notes": notes[:8],
        "evidence": evidence[:8],
    }


# Constraints read from upstream and checked by hand. If a refactor moves the
# kernels or renames the platform helpers, these go silently empty and every
# capability widens back out to "all of blackwell" — which is the failure this
# module exists to prevent, so it has to fail loudly instead.
SELF_TEST = [
    ("b12x", "hardware_contains", ["rtx_pro_6000", "dgx_spark_gb10"]),
    ("b12x", "hardware_excludes", ["b200", "gb200", "b300", "nvidia"]),
    ("b12x", "quant_contains", ["nvfp4", "mxfp4"]),
    ("FLASH_ATTN_MLA_SPARSE", "hardware_equals", ["h100", "h200"]),
    ("FLASH_ATTN_MLA_SPARSE", "trait_attention", "mla"),
    ("ROCM_AITER_FA", "hardware_contains", ["mi300x", "mi355x"]),
]


def self_test(tag: str) -> int:
    ok = True
    cache: dict[str, dict] = {}
    for value, kind, expected in SELF_TEST:
        guards = cache.setdefault(value, guards_for(tag, value))
        hardware, quant = guards["hardware"], guards["quant"]
        if kind == "hardware_contains":
            good = all(h in hardware for h in expected)
            detail = f"hardware {hardware[:4]}"
        elif kind == "hardware_excludes":
            good = all(h not in hardware for h in expected)
            detail = f"must exclude {expected}, got {hardware[:4]}"
        elif kind == "hardware_equals":
            good = sorted(hardware) == sorted(expected)
            detail = f"hardware {hardware}"
        elif kind == "quant_contains":
            good = all(q in quant for q in expected)
            detail = f"quant {quant}"
        else:
            good = (guards.get("model_traits") or {}).get("attention") == expected
            detail = f"traits {guards.get('model_traits')}"
        print(f"  {'ok  ' if good else 'FAIL'} {value:24} {kind:20} {detail}")
        ok = ok and good
    print(f"support-guards self-test {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--target", required=True)
    ap.add_argument("--value", action="append", default=[])
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test(args.target)
    if not args.value:
        ap.error("pass --value or --self-test")
    out = {v: guards_for(args.target, v) for v in args.value}
    if args.json:
        print(json.dumps(out, indent=2, sort_keys=True))
        return 0
    for value, g in out.items():
        print(f"{value}")
        print(f"  modules : {g['modules'] or '<not located>'}")
        print(f"  hardware: {g['hardware'] or '—'}")
        print(f"  quant   : {g['quant'] or '—'}")
        for e in g["evidence"]:
            print(f"    evidence {e['file']}{':' + str(e['line']) if e.get('line') else ''} — {e['why']}")
        for n in g["notes"][:4]:
            print(f"    note {n['file']}:{n['line']} — {n['text'][:96]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
