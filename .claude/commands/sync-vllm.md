---
description: Sync the recipes against a vLLM release — detect stale usage and missed improvements, apply the safe fixes on a branch
argument-hint: <target-tag> [prev-tag] [--report-only] [--release-notes <file>] [--check-images]
---

# /sync-vllm

Run manually after an upstream vLLM release. Detects recipe content upstream has
removed, renamed, deprecated, changed the default of, or that is used below the
version that introduced it; detects improvements the recipes could adopt; applies
the safe fixes on a branch, one commit per logical change. **No push, no PR.**

Arguments: `$ARGUMENTS` — first token is the target tag, an optional second bare
token is the previous tag (default: the previous **stable** release; rc tags are
skipped everywhere).

## Ground rules

- **The reference clone `.claude_workdir/vllm` is read-only.** `git show`,
  `git diff`, `git log`, `git tag` only. Never checkout, fetch, worktree, or
  write anything there.
- **Never read upstream through a Bash `git log`/`git tag` call.** rtk truncates
  that output — `git log --oneline v0.28.0..v0.29.0 | wc -l` reports 50 when the
  real answer is 58. Upstream facts come from the scripts in
  `.claude/sync-vllm/` (which shell out directly and are not hooked), or from
  `rtk proxy "<cmd>"` for a one-off.
- **Release tags are shallow and sit on release branches.** `v0.28.0` is not an
  ancestor of `v0.29.0`, so `prev..target` ranges are meaningless here. The tree
  at a tag is complete; commit ranges are not. The scripts already account for
  this — do not reintroduce a range query.
- **Scope.** Editable: `models/**/*.yaml`. Scanned but never edited:
  `taxonomy.yaml`, `strategies/*.yaml`, `kv_store/*.yaml`, `scripts/`,
  `src/lib/command-synthesis.js`. Out of scope entirely: the legacy top-level
  Markdown recipe trees. If `command-synthesis.js` emits a removed or deprecated
  flag, that finding goes at the **top** of the report — it affects every recipe.
- **No finding without upstream evidence.** Uncertain means `low` confidence and
  report-only. Never guess a replacement flag.

## Pipeline

All artifacts go to `.claude_workdir/reports/vllm-<target>/` (gitignored, never
committed). Scripts live in `.claude/sync-vllm/`; `REPORT=.claude_workdir/reports/vllm-<target>`.

The unit of discovery is a **capability**, not a PR and not a flag diff: a
concept users care about — a new or reworked kernel/backend (attention, MoE,
GEMM), a quantization format, a parallelism mode, a spec-decoding method, a
KV-cache or scheduling feature, a compilation change, or a changed default.
A release should yield 20-30 of them. Do **not** resolve every release-note
bullet to a PR; open one only to confirm an enabling condition for a capability
you have selected (`capabilities.py --resolve-pr N`).

### 1. Preflight

```bash
python3 .claude/sync-vllm/flagset.py --tag <target>     # resolves the tag locally
git status --porcelain                                  # must be empty
```

- Target tag missing locally → **stop** and tell the user to fetch it.
- Working tree dirty → **stop**.
- Unless `--report-only`: branch `sync/vllm-<target>` must NOT exist. If it does,
  **stop**. Otherwise create it from the current branch. Never commit to the base
  branch.

### 2. Capability discovery

```bash
python3 .claude/sync-vllm/parse_notes.py  --target <target> --report-dir $REPORT   # caches the notes
python3 .claude/sync-vllm/capabilities.py --target <target> --report-dir $REPORT --draft
```

Reads only the Highlights section, any Breaking Changes / Deprecations section,
and the `docs/` diff between the tags. A docs file counts only when it is new or
names a flag/env whose introducing tag IS the target — otherwise it is prose
churn. Offline: `parse_notes.py --release-notes <file>` or `--no-fetch`.

Output `capabilities.draft.yaml`. Each entry has `id`, `concept`, `title`,
`since`, `how_enabled` (auto, or the explicit flags/envs/enum values),
`default_on`, `applies_to {hardware, model_traits, quant}`, `effect`
(perf|memory|accuracy|usability|correctness) and `evidence`.

The vocabulary is the repo's own where it fits — `taxonomy.yaml`'s hardware
generations/brands and `kv_offload` ids, `strategies/*.yaml` parallelism names,
the recipes' feature keys and precisions. Read those before inventing a term.

### 3. Curate (judgement)

Edit the draft into `$REPORT/capabilities.yaml`: fix `concept`, tighten
`applies_to` so it names the hardware/quant/traits the evidence actually covers,
correct `how_enabled`, drop entries that are neither a capability nor a breaking
change. Aim for 20-30. A capability whose `applies_to` you cannot narrow is not
evidence — leave it unbounded and the cohort step will refuse it.

### 4. Verify capabilities

```bash
python3 .claude/sync-vllm/capabilities.py --target <target> --report-dir $REPORT --verify
python3 .claude/sync-vllm/capabilities.py --target <target> --self-test     # negative test
```

The enabling flag, env or enum value must exist at the target tag, and a cited
`file:line` must really contain the symbol; anything else is dropped. Categories
with no independent re-check (`default_change`, `default_on`) cap at `medium`.
`--self-test` feeds in a bogus flag, a bogus `file:line` and a bogus enum value
and fails unless all three are dropped and the control survives — run it
whenever you touch the verifier.

### 5. Profiles and cohorts

```bash
node .claude/sync-vllm/profiles.mjs --report-dir $REPORT
```

Builds a deterministic profile per recipe (family, dense/MoE, quant variants,
hardware keys, strategies, features, backends already in use) and matches each
capability's `applies_to` against them. Recipes already using the flag are
excluded, and so are capabilities that are on by default with nothing to edit.
A cohort over 30 recipes is refused as too broad — narrow `applies_to` and re-run.

### 6. Judgement, once per capability

For each capability with a bounded cohort, produce **one** entry: the edit
template (which key, which block, which value), the cohort, the evidence, and a
tier. Never one judgement per recipe. Emit nothing when the hardware or model
evidence does not cover the cohort.

### 7. Stale-usage scan (deterministic, unchanged in spirit)

```bash
python3 .claude/sync-vllm/inventory.py --target <target> --out $REPORT/inventory.json
node .claude/sync-vllm/scan.mjs   --target <target> --report-dir $REPORT
node .claude/sync-vllm/verify.mjs --target <target> --report-dir $REPORT
```

`verify.mjs` groups by **root cause**: one finding per flag/env with the recipe
count and list, not one per recipe. Flags vLLM never shipped go to the
unverifiable-plugin bucket and are never called stale.

### 7b. Model-support floor scan

Step 7 asks whether a recipe's *flags* exist at its floor. This asks the prior
question: was the *model* servable at that version at all?

```bash
python3 .claude/sync-vllm/index_models.py --target <target>                      # arch -> introducing tag
python3 .claude/sync-vllm/model_floors.py --target <target> --report-dir $REPORT # [--no-fetch]
```

`index_models.py` reads `vllm/model_executor/models/registry.py` at each tag;
`model_floors.py` resolves each checkpoint's architecture from its HF
`config.json` (cached under `$REPORT/hf-configs/`) and compares the introducing
tag with the declared floor. Output `model-floors.json`, rendered by `report.mjs`.

**The registry is only evidence for recipes the in-tree wheel serves.** A recipe
whose documented path is an out-of-tree plugin or a pinned image registers its
own architecture and legitimately runs on a vLLM older than the in-tree landing —
`registry.py` says nothing about its floor, and raising it would contradict the
recipe's own release-tested pin. `plugin_served()` skips those recipes on four
signals: an `omni` recipe, a non-first-party `docker_image`, a `vllm==` pin in
the guide, or an architecture selected via `--hf-overrides`. They land in
`plugin_served_skipped` — **skipped, not cleared**. Never edit a floor there, and
never widen the check to "fix" them: on those recipes the guide's pin is right
and the registry is wrong.

A floor is also repeated in the guide's `- vLLM >= X` Prerequisites line.
`model_floors.py` returns it as `guide_prerequisite`; a floor commit that leaves
it behind makes the recipe contradict itself, so the two edits belong in the
same commit.

`--self-test` checks both behaviours offline against known recipes.

### 8. Apply (skip entirely under `--report-only`)

```bash
node .claude/sync-vllm/commit.mjs snapshot --report-dir $REPORT     # once, before the first edit
```

Then per logical change, in its own commit:

1. make the edit with the normal editing tools — never re-serialize the YAML, or
   comments, key order and the `guide: |` block scalar are lost;
2. ```bash
   node .claude/sync-vllm/commit.mjs commit --report-dir $REPORT \
     --finding R-07 --files models/<org>/<repo>.yaml \
     --expect-paths '/model/min_vllm_version' \
     --subject '[<Org>] <subject>'
   ```
   The gate rebuilds the JSON API and refuses unless the build passes, no recipe
   outside the edited ones changed generated output (a recipe's own promoted
   variants count as its own), and every changed JSON key matches
   `--expect-paths`. On failure it restores the touched files and prints
   `status: skipped` — record that and move on. Never reset, amend, or rewrite.
3. Run `node scripts/build-recipes-api.mjs` once more at the end.

### 9. Report, then stop

```bash
node .claude/sync-vllm/report.mjs --report-dir $REPORT [--branch sync/vllm-<target>] [--report-only]
```

`report.md` is five sections and about two screens: **What shipped** /
**Adoption opportunities** / **Breaking & stale, by root cause** /
**Model-support floors** / **Unverifiable plugin flags**. The floors section is
rendered only when step 7b has run, and always states how many recipes were
skipped as plugin-served so the skip never reads as clean coverage. Per-recipe
detail belongs in `findings.json`, `cohorts.json` and `model-floors.json`, never
in the report. Then **stop** — no push, no PR.

`--check-images` (opt-in, network, strictly report-only):

```bash
node .claude/sync-vllm/check_images.mjs --target <target> --report-dir $REPORT
```

## Apply rules

| Finding | Condition | Action |
|---|---|---|
| Capability adoption, pure flag swap | upstream documents the equivalence, and the evidence covers the cohort's hardware **and** model family | auto-apply |
| Capability adoption, anything else | — | report only |
| Removed/renamed flag or env, replacement documented | effective floor ≥ the removal tag | auto-apply |
| Removed/renamed flag or env, replacement documented | effective floor < the removal tag | needs decision |
| Removed/renamed flag or env, **no** documented replacement | — | needs decision: deleting it and re-spelling it are different edits |
| Removed flag in a recipe with **no** `min_vllm_version` | — | auto-apply, and say in the report that it may break on older vLLM |
| Flag/env below its introducing tag, in the **unconditional** command (`model.base_args`/`base_env`, default variant) | — | raise `model.min_vllm_version`, **own commit** |
| Same, in a non-default variant that carries its own pin | — | raise **that variant's** pin, own commit |
| Same, in `features.*`, `hardware_overrides.*`, `strategy_overrides.*` or the guide | — | **per-block floor question — report only.** An optional block using a newer flag does not make the recipe's baseline wrong; raising the model floor would overstate the requirement for every other user |
| `default-changed` | — | report only, `medium` confidence at best |
| Floor below the release that registered the architecture, recipe served by the in-tree wheel | the recipe is absent from `plugin_served_skipped` | raise the floor to exactly that release, **own commit**, and update the guide's `- vLLM >= X` line in the same commit |
| Same, but the recipe is in `plugin_served_skipped` | — | **never edited.** The plugin or pinned image registers the architecture; the registry is not evidence about this recipe |
| `config_unreadable` — gated (401/403) or no `config.json` (404) | — | report only: the architecture is unknowable from here, not a floor error |
| `architecture_unregistered`, `floor_predates_support: true` — registered on main after the target, floor absent or ≤ target | — | report only: a floor *candidate* for `nightly`/the next release. Check by hand first — a `--trust-remote-code` recipe may already run on the Transformers backend |
| `architecture_unregistered`, `on_main: false` | — | report only: plugin, out-of-tree, or a `params.json` (Mistral-format) architecture the HF config names differently |
| Plugin/unverifiable flag | — | the plugin bucket, never "stale", never edited |
| Anything `low` confidence | — | report only |

The **effective floor** is `max(model.min_vllm_version, variants.<v>.min_vllm_version)`
for the block the token sits in; `"nightly"`/`"main"` means no floor. A recipe
pinned *above* the target tag is ahead of it, not stale.

Never touch a recipe's verified-claim metadata — `meta.hardware`, `verified`
badges, `performance_headline`, benchmark numbers.

**Do not run the auto-apply path until a report in this format has been
reviewed.** Until then every run is effectively `--report-only`.

## Commits

Repo style, not Conventional Commits (`CONTRIBUTING.md` and the history use
`[Org] Sentence` / `Add <org>/<repo> recipe`; upstream enforces DCO):

- one recipe → `[<Org>] <subject>`, e.g. `[Qwen] Raise vLLM floor to 0.17.0 for --language-model-only`
- a sweep across recipes → `[vLLM <target>] <subject>`
- always `git commit -s` (the gate does this); subject only, no body
- **no URLs, no issue/PR links, no AI attribution** in the message. Finding IDs
  and upstream links live in the report, keyed by commit hash.

## Tracking between releases

No state file. `report.mjs` loads the most recent earlier `findings.json` under
`.claude_workdir/reports/` and marks findings whose status has not changed as
carried over. Re-evaluate the previous run's `skipped` / `needs decision` items
against the new target before re-reporting them.
