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

### 1. Preflight

```bash
python3 .claude/sync-vllm/flagset.py --tag <target>     # resolves the tag locally
git status --porcelain                                  # must be empty
```

- Target tag missing locally → **stop** and tell the user to fetch it.
- Working tree dirty → **stop**.
- Unless `--report-only`: branch `sync/vllm-<target>` must NOT exist
  (`git rev-parse --verify`). If it does, **stop** and say so. Otherwise create it
  from the current branch. Never commit to the base branch.

### 2. Discovery (two independent passes)

```bash
python3 .claude/sync-vllm/inventory.py   --target <target> [--prev <prev>] --out $REPORT/inventory.json
python3 .claude/sync-vllm/parse_notes.py --target <target> [--prev <prev>] --report-dir $REPORT --merge
```

`inventory.py` is the source pass (AST over `arg_utils.py`, the frontend
`cli_args.py`, `envs.py` and `vllm/config/*.py`): removals, additions, new values
in a flag's choice set, changed defaults, deprecation notices attributed to the
declaration that encloses them.

`parse_notes.py` is the release-notes pass: `gh release view` for every non-rc
release in `(prev, target]`, cached under `$REPORT/release-notes/`, bullets split
into clauses so each `(#NNNN)` keeps its own flags, envs, models and hardware,
then resolved to local commits. Offline: pass `--release-notes <file>`, or
`--no-fetch` to use the cache; it warns loudly when notes are missing and the
source pass carries the run alone.

`--merge` folds the notes into `inventory.json`: items found by both passes are
marked `source: both`, source-only items say so, notes-only items must survive
verification in step 5 or be dropped.

### 3. Flag index (absolute check)

`scan.mjs` builds it on demand; to inspect or warm it:

```bash
python3 .claude/sync-vllm/index_flags.py --target <target> --query=--some-flag
```

Cached at `.claude_workdir/reports/vllm-sync-cache/flag-index.json` and extended
incrementally (62 stable tags, ~3 s cold, seconds warm). This is what catches
staleness a skipped release would otherwise hide, and what answers "did this flag
exist at the tag this recipe pins?".

### 4. Scan

```bash
node .claude/sync-vllm/scan.mjs --target <target> --report-dir $REPORT
```

Line-based, so every match has `file:line` and edits stay surgical. Two tiers:

- **structured** — `base_args`/`extra_args`/`args` and `base_env`/`extra_env`/`env`
  blocks. Every rule applies, including "this flag is in no release" and "this
  value is not an accepted choice".
- **prose** — guide code fences, strategy YAML, the synthesis source. Only tokens
  vLLM has actually shipped at some tag are judged; anything else belongs to
  docker, pip or a plugin, not to vLLM.

### 5. Missed improvements (the one LLM step)

`candidates.json → missed[]` holds deterministic joins between notes items and
recipes (model family and hardware). They are **candidates, not findings**. For
each one you keep:

- cite a specific upstream `file:line` at the target tag, or a PR whose diff you
  read in the clone;
- propose a concrete YAML edit — which key, which value, which variant/hardware
  block. No "consider enabling X";
- drop anything you cannot tie to the recipe's *hardware* **and** *model family*.

### 6. Verify

```bash
node .claude/sync-vllm/verify.mjs --target <target> --report-dir $REPORT
```

Re-asks every claim independently (upstream symbol at the cited line, real
presence/absence at the tag, the downstream line unchanged since the scan),
drops what fails, and groups candidates into findings — one per
(file, token, category), and floor findings per (file, pin scope, tier).
It **proposes** a status; it does not apply.

### 7. Apply (skip entirely under `--report-only`)

```bash
node .claude/sync-vllm/commit.mjs snapshot --report-dir $REPORT     # once, before the first edit
```

Then per finding, in its own commit:

1. make the edit with the normal editing tools — never re-serialize the YAML, or
   comments, key order and the `guide: |` block scalar are lost;
2. ```bash
   node .claude/sync-vllm/commit.mjs commit --report-dir $REPORT \
     --finding F-07 --files models/<org>/<repo>.yaml \
     --expect-paths '/model/min_vllm_version' \
     --subject '[<Org>] <subject>'
   ```
   The gate rebuilds the JSON API and refuses the commit unless the build passes,
   no recipe outside the edited ones changed generated output (a recipe's own
   promoted variants count as its own), and every changed JSON key matches
   `--expect-paths`. On failure it restores the touched files and prints
   `status: skipped` with the reason — record that finding as
   `skipped (<reason>)` and move on. Never reset, amend, or rewrite history.
3. Run `node scripts/build-recipes-api.mjs` once more at the end.

### 8. Report, then stop

```bash
node .claude/sync-vllm/report.mjs --report-dir $REPORT [--branch sync/vllm-<target>] [--report-only]
```

Writes `report.md` and `summary.md` from `findings.json`. Before running it,
write back into `findings.json` for every finding you acted on:
`status_final` (`applied (<hash>)`, `applied (not re-verified on hardware) (<hash>)`,
`needs decision`, or `skipped (<reason>)`), plus `commit` and `subject`. Append
your missed-improvement sections to `report.md` afterwards in the same field
format. Then **stop** — no push, no PR.

`--check-images` (opt-in, network, strictly report-only):

```bash
node .claude/sync-vllm/check_images.mjs --target <target> --report-dir $REPORT
```

## Apply rules

| Finding | Condition | Action |
|---|---|---|
| Removed/renamed flag or env, replacement documented | effective floor ≥ the removal/rename tag | auto-apply |
| Removed/renamed flag or env, replacement documented | effective floor < that tag | **needs decision** — applying would break the versions the recipe claims |
| Removed/renamed flag or env, **no** documented replacement | any | **needs decision** — deleting it and re-spelling it are different edits, and upstream has not said which |
| Removed flag in a recipe with **no** `min_vllm_version` | — | auto-apply, and the report must say the edit may break the recipe on older vLLM |
| Deprecated flag with a documented replacement | floor ≥ the tag introducing the replacement | auto-apply |
| Flag/env used below the version that introduced it (structured tier) | always | raise the floor to the introducing tag, **own commit** |
| Same, guide-prose tier | always | report only — the guide text is what is wrong, not necessarily the pin |
| `default-changed` | always | report only |
| Missed improvement, pure flag swap | upstream documents the equivalence | auto-apply |
| Missed improvement, hardware-dependent | upstream evidence covers this recipe's hardware **and** model family | auto-apply, status `applied (not re-verified on hardware)` |
| Missed improvement, hardware-dependent | evidence is only "it merged", or covers other hardware / another model family, or needs multi-node | report only |
| `unknown-upstream`, `invalid-value`, anything `low` | — | report only |

The **effective floor** is `max(model.min_vllm_version, variants.<v>.min_vllm_version)`
for the block the token sits in; `"nightly"`/`"main"` means no floor. A recipe
pinned *above* the target tag is ahead of it, not stale.

Never touch a recipe's verified-claim metadata — `meta.hardware`, `verified`
badges, `performance_headline`, benchmark numbers.

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
