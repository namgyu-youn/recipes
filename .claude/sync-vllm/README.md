# sync-vllm

Tooling behind `/sync-vllm` (`.claude/commands/sync-vllm.md`). Local-only: this
directory is covered by the global `**/.claude/` ignore, so nothing here can leak
into an upstream PR. That is also why it is not under `scripts/`, which is
tracked and ships to `vllm-project/recipes`.

Python parses upstream (`ast` is exact where a grep is not); Node handles YAML,
the JSON API and git, matching the repo's own tooling.

The unit is a **capability** — a concept users care about (a kernel/backend, a
quantization format, a parallelism mode, a spec-decoding method, a KV-cache or
scheduling feature, a compilation change, a changed default) — not a PR and not
a flag diff. 20-30 per release. The stale-usage scan runs alongside it and
reports by **root cause**: one entry per flag/env with its recipe count.

| File | Role |
|---|---|
| `flagset.py` | vLLM's flag set and env set at one tag |
| `index_flags.py` | cached flag/env → introduced/removed tag index over the stable tags |
| `capabilities.py` | discovery (`--draft`) from highlights + breaking/deprecations + docs diff; mechanical `--verify`; `--self-test`; `--resolve-pr` |
| `parse_notes.py` | fetches and caches the release notes |
| `inventory.py` | source pass for the stale scan: removals, new enum values, changed defaults, deprecations |
| `profiles.mjs` | recipe profiles + capability cohorts |
| `scan.mjs` | inventory × recipes → `candidates.json` with `file:line` |
| `verify.mjs` | re-checks candidates independently, groups by root cause → `findings.json` |
| `commit.mjs` | snapshot / check / commit gate around `build-recipes-api.mjs` |
| `report.mjs` | capabilities + cohorts + findings → a two-screen `report.md` |
| `check_images.mjs` | opt-in `--check-images`: are pinned `docker_image` tags still pullable |

Artifacts: `.claude_workdir/reports/vllm-<target>/`.
Shared cache: `.claude_workdir/reports/vllm-sync-cache/flag-index.json`.

## Rules that are easy to get wrong

**Never take upstream facts from Bash `git` output.** rtk wraps Bash commands and
truncates: `git log --oneline v0.28.0..v0.29.0 | wc -l` answers 50 where the real
count is 58. Every script here shells out to git directly (`subprocess` /
`execFileSync`), which is not hooked. For a one-off in the terminal, use
`rtk proxy "<cmd>"`.

**The clone is shallow and its release tags sit on release branches.** `v0.28.0`
is not an ancestor of `v0.29.0` — there is no merge-base, and `rev-list --count
v0.29.0` is 58. Commit *ranges* are therefore useless; PR resolution scans all
refs instead and treats a miss as "outside the shallow boundary", never as
evidence. The *tree* at a tag is complete, which is why every authoritative check
is `git show <tag>:<path>`.

**The clone is read-only.** No checkout, no fetch, no worktree, no commit.

**Flags are not a grep.** They are `add_argument("--x")` literals ∪ the annotated
field names of `EngineArgs`/`AsyncEngineArgs`/`FrontendArgs`/`BaseFrontendArgs`.
The frontend parser is generated wholesale from its dataclass, so `--port` and
`--tool-parser-plugin` exist with no literal anywhere; a literal-only set misses
~56 real flags at v0.29.0. Each entry records which `role` and which `sources` it
came from so the two cases stay distinguishable.

**Defaults and choices live in `vllm/config/*.py`.** An `EngineArgs` field usually
reads `= SomeConfig.field`, so both are resolved through the config dataclasses.
A `Literal[...]` that references a type alias from another module resolves to
*unknown*, never to a partial set — a partial set would reject valid values.

**Editing is textual.** Recipes are round-trip-hostile: comments, key order and
`guide: |` block scalars do not survive a js-yaml dump. `scan.mjs` reads raw
lines (the parsed copy only answers "which block is this line in") and
`commit.mjs` never writes YAML at all.

**A recipe owns its promoted variants.** `models/Qwen/Qwen2.5-VL-7B-Instruct.yaml`
generates `public/Qwen/Qwen2.5-VL-7B-Instruct-AWQ.json` too, so the commit gate
counts variant `model_id`s as the same recipe when it checks blast radius.

**A cohort is bounded or it is nothing.** `applies_to` that matches more than 30
recipes is not evidence that a capability applies — it means the capability has
not been narrowed. `profiles.mjs` refuses those rather than listing them, which
is the guard against the substring-join that produced 642 meaningless rows.

**Optional blocks do not move the model floor.** A newer flag inside
`features.*`, `hardware_overrides.*` or `strategy_overrides.*` only runs on
opt-in, so it is a per-block floor question, not a reason to raise
`model.min_vllm_version` for everyone. Only the unconditional command does that.

**A flag vLLM never shipped is not stale.** vllm-omni, vllm-ascend and vendor
images register their own; they go to one bucket and are never edited.

## Quick run

```bash
REPORT=.claude_workdir/reports/vllm-0.29.0
python3 .claude/sync-vllm/parse_notes.py  --target v0.29.0 --report-dir $REPORT
python3 .claude/sync-vllm/capabilities.py --target v0.29.0 --report-dir $REPORT --draft
# curate capabilities.draft.yaml -> capabilities.yaml, then:
python3 .claude/sync-vllm/capabilities.py --target v0.29.0 --report-dir $REPORT --verify
node     .claude/sync-vllm/profiles.mjs   --report-dir $REPORT
python3 .claude/sync-vllm/inventory.py    --target v0.29.0 --out $REPORT/inventory.json
node     .claude/sync-vllm/scan.mjs       --target v0.29.0 --report-dir $REPORT
node     .claude/sync-vllm/verify.mjs     --target v0.29.0 --report-dir $REPORT
node     .claude/sync-vllm/report.mjs     --report-dir $REPORT --report-only
```
