# vLLM sync — v0.28.0 → v0.29.0

Report-only: nothing was edited or committed. 8 capabilities shipped (4 breaking changes are in section 3);
20 stale-usage root causes; 3 adoption opportunities with a bounded cohort.

## What shipped

| Concept | Capability | How enabled | Effect | Confidence |
|---|---|---|---|---|
| spec_decoding | Per-request speculative-decoding acceptance metrics in OpenAI API responses | `--per-request-spec-decode-metrics` | usability | high |
| spec_decoding | Mamba prefix caching: internal prefill checkpoints (9-25% TTFT) | no flag — automatic | perf | medium |
| compilation | Model Runner V2 is now the default for all models: completing the rollout that began with pooling models | no flag — automatic | memory | medium |
| quantization | Kimi-K3 and DeepSeek V4 performance: fused MXFP4 top-k finalization in the K3 latent tail (about 5% E2E latency, #53152) | no flag — automatic | perf | medium |
| attention_backend | FlashInfer all-reduce enabled by default for TP CUDA groups, opt out with VLLM_ALLREDUCE_USE_FLASHINFER=0 | `VLLM_ALLREDUCE_USE_FLASHINFER` | usability | medium |
| kv_cache | prefix-cache NONE_HASH is deterministic by default so distributed KV cache users no longer need to pin PYTHONHASHSEED | no flag — automatic | usability | medium |
| scheduling | new --max-num-queued-reqs / --max-num-queued-tokens admission-control flags | `--max-num-queued-reqs`, `--max-num-queued-tokens` | usability | high |
| kernel | b12x linear and MoE backends for SM120/SM121 | `--linear-backend b12x`, `--moe-backend b12x`, `VLLM_B12X_MOE_FP4_FORCE_A16` | perf | high |

5 of these need no recipe edit: on by default with nothing to remove, or with no hardware/model dimension to bound a cohort.

## Adoption opportunities

**Model Runner V2 is now the default for all models: completing the rollout that began with pooling models** — compilation, confidence medium

| Where | Name | Value | Recipe floor | Evidence | Verdict |
|---|---|---|---|---|---|
| `deepseek-ai/DeepSeek-V4-Flash-Vision-Exp` | `VLLM_USE_V2_MODEL_RUNNER` | `1` | 0.29.0 | `hardware_overrides.amd.extra_env` | redundant explicit |
| `deepseek-ai/DeepSeek-V4-Flash-Vision-Exp:316` | `VLLM_USE_V2_MODEL_RUNNER` | `1` | 0.29.0 | `-e VLLM_USE_V2_MODEL_RUNNER=1 \` | stale guide text |
| `deepseek-ai/DeepSeek-V4.1-Flash` | `VLLM_USE_V2_MODEL_RUNNER` | `1` | 0.30.0 | `variants.default.hardware_overrides.h100.extra_env` | redundant explicit |
| `moonshotai/Kimi-K3` | `VLLM_USE_V2_MODEL_RUNNER` | `1` | 0.29.0 | `hardware_overrides.blackwell.extra_env` | redundant explicit |

2 guide mention(s) explain why the setting is there ("required for …", "can be enabled if needed") — documentation, not staleness.
9 further recipe(s) set it below the v0.29.0 floor, where it is still load-bearing — keep: Google/gemma-4-26B-A4B-it (floor 0.25.0), deepseek-ai/DeepSeek-V4-Flash-Vision-Exp (floor 0.29.0), deepseek-ai/DeepSeek-V4-Flash (floor 0.20.0), moonshotai/Kimi-K3 (floor 0.29.0), thinkingmachines/Inkling-Small (floor 0.26.0), thinkingmachines/Inkling (floor 0.26.0).
⚠ MRV1 remains in use for a few ROCm models and for features MRV2 does not yet support, so an explicit VLLM_USE_V2_MODEL_RUNNER=1 may be deliberate on those recipes — confirm the model class is on MRV2 before removing it.
Why it applies (spec_decoding): "MRV2 also gained CUDA graph memory profiling for KV cache auto-sizing (#53306), batch-sharded sampling that cuts per-step logits memory by 1/TP (#50465), prompt embeds (#42963), `extract_hidden_states` speculation (#49811), padded FULL cuda"
Tier: **report-only — needs an edit template and review before applying.**

**b12x linear and MoE backends for SM120/SM121 — linear backend** — kernel, confidence high
Add `--linear-backend b12x` to 11 recipes (1 already using it, excluded): Google/diffusiongemma-26B-A4B-it, Google/gemma-4-26B-A4B-it, MiniMaxAI/MiniMax-M2.7, Qwen/Qwen3.6-27B, Qwen/Qwen3.6-35B-A3B, Qwen/Qwen3.8-27B, Qwen/Qwen3.8-Flash-Next, inclusionAI/Ling-3.0-flash, +3 more.
Required floor for this edit: **0.29.0** (--linear-backend itself exists since 0.22.0; the b12x value is new in 0.29.0). Install change: `uv pip install "vllm[b12x]"` — b12x kernels ship as a wheel extra, not in the base wheel.
Evidence: "b12x linear kernels participate in automatic selection after established optimized backends and before emulation; select them explicitly with --linear-backend b12x. Linear supports per-tensor FP8, 128x128 block FP8, MXFP8, NVFP4 and MXFP4."
⚠ 1 of them already set the same flag to a different value — that is a backend swap with a behaviour change, not an addition: nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16 (--linear-backend humming → b12x).
Why it applies (rtx_pro_6000): "b12x provides optional CUDA kernels for NVIDIA SM120 and SM121 GPUs (RTX Pro 6000/5000, RTX 5090, DGX Spark GB10), installed with pip install vllm[b12x]."
Tier: **report-only — needs an edit template and review before applying.**

**b12x linear and MoE backends for SM120/SM121 — MoE backend (MoE models only)** — kernel, confidence high
Add `--moe-backend b12x` to 7 recipes (1 already using it, excluded): Google/diffusiongemma-26B-A4B-it, Google/gemma-4-26B-A4B-it, MiniMaxAI/MiniMax-M2.7, Qwen/Qwen3.6-35B-A3B, Qwen/Qwen3.8-Flash-Next, nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16, nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16.
Required floor for this edit: **0.29.0** (--moe-backend itself exists since 0.17.0; the b12x value is new in 0.29.0). Install change: `uv pip install "vllm[b12x]"` — b12x kernels ship as a wheel extra, not in the base wheel.
Evidence: "Only pass --moe-backend b12x for a compatible NVFP4 or MXFP4 MoE model. The b12x MoE backend does not support expert parallelism, expert maps, EXL3, or NF3."
⚠ 3 of them already set the same flag to a different value — that is a backend swap with a behaviour change, not an addition: Qwen/Qwen3.6-35B-A3B (--moe-backend marlin → b12x), Qwen/Qwen3.8-Flash-Next (--moe-backend marlin → b12x), nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16 (--moe-backend marlin → b12x).
Why it applies (rtx_pro_6000): "b12x provides optional CUDA kernels for NVIDIA SM120 and SM121 GPUs (RTX Pro 6000/5000, RTX 5090, DGX Spark GB10), installed with pip install vllm[b12x]."
Tier: **report-only — needs an edit template and review before applying.**


1 further capability matched more than 30 recipes, which means `applies_to` is not narrow enough to be evidence: Per-request speculative-decoding acceptance metrics in OpenAI API responses. Narrow hardware/quant/traits in `capabilities.yaml` and re-run before judging these.

## Breaking & stale, by root cause

20 root causes. 3 have at least one recipe where the edit is mechanical; 12 are per-block floor questions (a newer flag inside `features.*` or `hardware_overrides.*` does not make the recipe's baseline wrong).

| ID | Flag / env | What | Recipes | Action | Confidence |
|---|---|---|---|---|---|
| R-03 | `--mm-encoder-tp-mode` | used below its introducing release (needs v0.10.2) | 5 | raise model floor, per-block floor question | high |
| R-09 | `--task` | removed upstream (gone in v0.13.0) | 1 | decide: drop or re-spell | high |
| R-11 | `--rope-scaling` | removed upstream (gone in v0.11.1) | 1 | decide: drop or re-spell | high |
| R-12 | `--attention-backend` | invalid-value — deepseek-ai/DeepSeek-V4-Flash sets `B12X_MLA_SPARSE`, not accepted at the target tag (accepted: AMX_MLA, CPU_ATTN, CPU_MLA, CUSTOM, …) | 1 | report only | high |
| R-13 | `--linear-backend` | used below its introducing release (needs v0.22.0) | 1 | raise variant pin | high |
| R-14 | `VLLM_USE_BREAKABLE_CUDAGRAPH` | used below its introducing release (needs v0.22.0) | 1 | raise variant pin | high |
| R-17 | `--disable-log-requests` | removed upstream (gone in v0.17.0) | 1 | decide: drop or re-spell | high |
| R-18 | `--dcp-comm-backend` | upstream default changed — the recipe sets this flag explicitly, so the changed default does not reach it | 1 | report only | medium |
| R-20 | `--cc.pass_config.fuse_allreduce_rms` | wrong dash — argparse rejects it | 1 | replace | high |

- `--task` → no replacement documented. read the argparse help, the config field docstring and every deprecation line mentioning it at v0.12.0; none names a replacement
  > model_group.add_argument('--task', **model_kwargs['task'], deprecated=True)
- `--rope-scaling` → no replacement documented. read the argparse help, the config field docstring and every deprecation line mentioning it at v0.11.0; none names a replacement
  > model_group.add_argument('--rope-scaling', **model_kwargs['rope_scaling'])
- `--disable-log-requests` → replace with `--enable-log-requests`. its default was the negation of enable_log_requests at v0.16.0 (vllm/engine/arg_utils.py:2087), and --enable-log-requests exists at the target tag
  > parser.add_argument('--disable-log-requests', action=argparse.BooleanOptionalAction, default=not AsyncEngineArgs.enable_log_requests, help='[DEPRECATED] Disable logging requests.', deprecated=True)
Also announced as breaking: PyAV video decoder backend removed; python -m vllm.entrypoints.openai.api_server is deprecated; prefix_cache_retention_interval default changed from dense to 0 for SWA/SSM models; VLLM_TEST_FORCE_FP8_MARLIN removed in favor of --linear-backend / --moe-backend.

**Per-block floor policy (11 flags, 33 recipes).** Each of these is a flag used below its introducing release, but only inside
`features.*` (opt-in), `hardware_overrides.*` or `strategy_overrides.*`. The recipe's
unconditional command is unaffected, so the model floor is not wrong — the question is whether the
block should carry its own floor. One decision covers all of them: `--language-model-only` (22), `--attention-backend` (5), `--moe-backend` (4), `VLLM_ROCM_SHUFFLE_KV_CACHE_LAYOUT` (3), `VLLM_ROCM_USE_AITER` (3), `VLLM_SSM_CONV_STATE_LAYOUT` (2), `VLLM_ENGINE_READY_TIMEOUT_S` (2), `--disable-chunked-mm-input` (1), `--prefill-schedule-interval` (1), `--speculative-config` (1), `--quantization-config.moe.activation` (1). Full list in `findings.json`.

Per-recipe lines, blocks and floors: `findings.json`.

## Vendor image overlapping upstream

**V-1 — `eugr/spark-vllm-b12x:latest`** in deepseek-ai/DeepSeek-V4-Flash. upstream ships b12x linear/MoE kernels in-tree since v0.29.0 behind --linear-backend/--moe-backend; the VLLM_USE_B12X_* switches exist at no upstream tag, the newest rc or main, and three of them have no documented upstream equivalent

| Vendor env | Upstream equivalent |
|---|---|
| `VLLM_USE_B12X_WO_PROJECTION` | no upstream equivalent documented — cannot be dropped |
| `VLLM_USE_B12X_MHC` | no upstream equivalent documented — cannot be dropped |
| `VLLM_USE_B12X_FP8_GEMM` | `--linear-backend b12x` |
| `VLLM_USE_B12X_MOE` | `--moe-backend b12x` |
| `VLLM_USE_B12X_SPARSE_INDEXER` | no upstream equivalent documented — cannot be dropped |

2 of 5 switches map to upstream flags the recipe already passes; the rest have no documented equivalent. Migrating off the image is a hardware-validated decision (GB10), not a mechanical edit. **Report-only: the decision is whether to migrate off the image, and that needs GB10 validation.**

## Unverifiable flags

Not stale usage — vLLM never shipped these, so this tool has nothing to check them against.

Each is classified by the recipe context it sits in — an omni task section, a pinned image, or the company its neighbours keep — not by how the name is spelled.

- **vllm-omni** (24 flags across 20 recipes) — name is in that plugin's namespace: `--omni`, `--init-timeout`, `--deploy-config`, `--cfg-parallel-size`, `--ulysses-degree`, `--use-hsdp`, `--hsdp-shard-size`, `--diffusion-attention-backend`, +16 more.
- **vllm-ascend** (1 flags across 1 recipes) — name is in that plugin's namespace: `VLLM_ASCEND_ENABLE_PREFETCH_MLP`.
- **vendor-image** (1 flags across 1 recipes) — block pins eugr/spark-vllm-b12x:latest: `VLLM_MEMORY_PROFILE_INCLUDE_ATTN`.
- **Newer than v0.29.0** (2) — present in the clone but not in a stable release yet, so the recipe is ahead of its pin: `VLLM_PLE_CPU_OFFLOAD` (present at v0.30.0rc2, 1 recipe), `VLLM_ROCM_USE_AITER_MOE_SITUV2` (present at main (HEAD of the clone), 1 recipe).

5 release items were out of the capability vocabulary (new model support, packaging) and are recorded in `capabilities.yaml` rather than shown above.
