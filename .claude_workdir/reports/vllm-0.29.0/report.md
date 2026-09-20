# vLLM sync — v0.28.0 → v0.29.0

Report-only: nothing was edited or committed. 10 capabilities shipped (4 breaking changes are in section 3);
26 stale-usage root causes; 2 adoption opportunities with a bounded cohort.

## What shipped

| Concept | Capability | How enabled | Effect | Confidence |
|---|---|---|---|---|
| moe_backend | Kimi-K3 and DeepSeek V4 performance: fused MXFP4 top-k finalization in the K3 latent tail (about 5% E2E latency, #53152) | no flag — automatic | perf | medium |
| moe_backend | b12x linear and MoE backends for SM120/SM121 | `--linear-backend b12x`, `--moe-backend b12x`, `VLLM_B12X_MOE_FP4_FORCE_A16` | perf | high |
| kv_cache | Mamba prefix caching: internal prefill checkpoints (9-25% TTFT) | no flag — automatic | perf | medium |
| kv_cache | prefix-cache NONE_HASH is deterministic by default so distributed KV cache users no longer need to pin PYTHONHASHSEED | no flag — automatic | usability | medium |
| scheduling | new --max-num-queued-reqs / --max-num-queued-tokens admission-control flags | `--max-num-queued-reqs`, `--max-num-queued-tokens` | usability | high |
| scheduling | Trace Replay: --enable-trace-replay | `--enable-trace-replay` | correctness | high |
| default_change | Model Runner V2 is now the default for all models: completing the rollout that began with pooling models | no flag — automatic | memory | medium |
| spec_decoding | Per-request speculative-decoding acceptance metrics in OpenAI API responses | `--per-request-spec-decode-metrics` | usability | high |
| parallelism | FlashInfer all-reduce enabled by default for TP CUDA groups, opt out with VLLM_ALLREDUCE_USE_FLASHINFER=0 | `VLLM_ALLREDUCE_USE_FLASHINFER` | usability | medium |
| frontend | Media download size limits for multimodal serving | `VLLM_MAX_MEDIA_DOWNLOAD_SIZE_MB` | memory | high |

8 of these need no recipe edit: on by default with nothing to remove, or with no hardware/model dimension to bound a cohort.

## Adoption opportunities

**Model Runner V2 is now the default for all models: completing the rollout that began with pooling models** — default_change, confidence medium
Subtractive edits: 9 redundant explicit, 6 stale guide text — Google/gemma-4-26B-A4B-it [redundant explicit: VLLM_USE_V2_MODEL_RUNNER], Qwen/Qwen2.5-32B [stale guide text: VLLM_USE_V1], deepseek-ai/DeepSeek-V4-Flash-Vision-Exp [redundant explicit: VLLM_USE_V2_MODEL_RUNNER], deepseek-ai/DeepSeek-V4-Flash-Vision-Exp [stale guide text: VLLM_USE_V2_MODEL_RUNNER], ….
Why it applies (spec_decoding): "MRV2 also gained CUDA graph memory profiling for KV cache auto-sizing (#53306), batch-sharded sampling that cuts per-step logits memory by 1/TP (#50465), prompt embeds (#42963), `extract_hidden_states` speculation (#49811), padded FULL cuda"
Tier: **report-only — needs an edit template and review before applying.**

**b12x linear and MoE backends for SM120/SM121** — moe_backend, confidence high
Add `--linear-backend b12x`, `--moe-backend b12x`, `VLLM_B12X_MOE_FP4_FORCE_A16` to 10 recipes (1 already using it, excluded): Google/diffusiongemma-26B-A4B-it, Google/gemma-4-26B-A4B-it, MiniMaxAI/MiniMax-M2.7, Qwen/Qwen3.6-27B, Qwen/Qwen3.6-35B-A3B, Qwen/Qwen3.8-27B, Qwen/Qwen3.8-Flash-Next, meta-models/Muse-Glimmer-30B, +2 more.
Why it applies (rtx_pro_6000): "b12x provides optional CUDA kernels for NVIDIA SM120 and SM121 GPUs (RTX Pro 6000/5000, RTX 5090, DGX Spark GB10), installed with `pip install vllm[b12x]`."
Tier: **report-only — needs an edit template and review before applying.**


2 further capabilities matched more than 30 recipes, which means `applies_to` is not narrow enough to be evidence: per-request-acceptance-stats-in-openai-api-respo, vllm-test-force-fp8-marlin-removed-in-favor-of-l. Narrow hardware/quant/traits in `capabilities.yaml` and re-run before judging these.

## Breaking & stale, by root cause

26 root causes. 4 have at least one recipe where the edit is mechanical; 16 are per-block floor questions (a newer flag inside `features.*` or `hardware_overrides.*` does not make the recipe's baseline wrong).

| ID | Flag / env | What | Recipes | Action | Confidence |
|---|---|---|---|---|---|
| R-02 | `--disable-log-requests` | removed upstream (gone in v0.17.0) | 9 | decide: drop or re-spell, replace | high |
| R-04 | `--mm-encoder-tp-mode` | used below its introducing release (needs v0.10.2) | 5 | raise model floor, per-block floor question | high |
| R-12 | `--task` | removed upstream (gone in v0.13.0) | 1 | decide: drop or re-spell | high |
| R-13 | `VLLM_USE_V1` | removed upstream (gone in v0.11.1) | 1 | decide: drop or re-spell | high |
| R-14 | `--guided-decoding-backend` | removed upstream (gone in v0.12.0) | 1 | decide: drop or re-spell | high |
| R-16 | `--swap-space` | removed upstream (gone in v0.18.0) | 1 | decide: drop or re-spell | high |
| R-18 | `--rope-scaling` | removed upstream (gone in v0.11.1) | 1 | decide: drop or re-spell | high |
| R-19 | `--linear-backend` | used below its introducing release (needs v0.22.0) | 1 | raise variant pin | high |
| R-20 | `VLLM_USE_BREAKABLE_CUDAGRAPH` | used below its introducing release (needs v0.22.0) | 1 | raise variant pin | high |
| R-24 | `--dcp-comm-backend` | upstream default changed (needs v0.18.0) | 1 | report only | medium |
| R-26 | `--cc.pass_config.fuse_allreduce_rms` | wrong dash — argparse rejects it | 1 | replace | high |

Also announced as breaking: PyAV video decoder backend removed; python -m vllm.entrypoints.openai.api_server is deprecated; prefix_cache_retention_interval default changed from dense to 0 for SWA/SSM models; VLLM_TEST_FORCE_FP8_MARLIN removed in favor of --linear-backend / --moe-backend.

**Per-block floor policy (15 flags, 34 recipes).** Each of these is a flag used below its introducing release, but only inside
`features.*` (opt-in), `hardware_overrides.*` or `strategy_overrides.*`. The recipe's
unconditional command is unaffected, so the model floor is not wrong — the question is whether the
block should carry its own floor. One decision covers all of them: `--language-model-only` (22), `--attention-backend` (5), `--moe-backend` (4), `VLLM_ROCM_SHUFFLE_KV_CACHE_LAYOUT` (3), `VLLM_ROCM_USE_AITER` (3), `--data-parallel-size` (2), `VLLM_SSM_CONV_STATE_LAYOUT` (2), `VLLM_ENGINE_READY_TIMEOUT_S` (2), `--tool-server` (2), `--disable-chunked-mm-input` (1), `--async-scheduling` (1), `--prefill-schedule-interval` (1), `VLLM_PREFIX_CACHE_RETENTION_INTERVAL` (1), `--speculative-config` (1), `--quantization-config.moe.activation` (1). Full list in `findings.json`.

Per-recipe lines, blocks and floors: `findings.json`.

## Unverifiable flags

Not stale usage — vLLM never shipped these, so this tool has nothing to check them against.

- **Known plugin namespaces** (20 across 19 recipes): `--omni`, `--deploy-config`, `--ulysses-degree`, `--use-hsdp`, `--hsdp-shard-size`, `--diffusion-attention-backend`, `--model-class-name`, `--num-gpus`, `--usp`, `--ring`, `--vae-patch-parallel-size`, `--vae-parallel-mode`, `--vae-use-tiling`, `VLLM_OMNI_VIDEO_SYNC_TIMEOUT`, `--task-type`, `--text-encoder-tp-size`, `--dlo-no-use-allgather`, `--dlo-resident-layers`, `VLLM_ASCEND_ENABLE_PREFETCH_MLP`, `VLLM_OMNI_TARGET_DEVICE`.
- **Vendor or out-of-tree** (11 across 7 recipes) — plain `VLLM_*`/core-looking names absent from every stable tag, the newest rc and main, so they come from a pinned vendor image: `--init-timeout`, `--cfg-parallel-size`, `--stage-init-timeout`, `--enable-distributed-layerwise-offload`, `--ignored-layers`, `VLLM_MEMORY_PROFILE_INCLUDE_ATTN`, `VLLM_USE_B12X_WO_PROJECTION`, `VLLM_USE_B12X_MHC`, `VLLM_USE_B12X_FP8_GEMM`, `VLLM_USE_B12X_MOE`, +1 more.
- **Newer than v0.29.0** (2) — present in the clone but not in a stable release yet, so the recipe is ahead of its pin: `VLLM_PLE_CPU_OFFLOAD` (present at v0.30.0rc2, 1 recipe), `VLLM_ROCM_USE_AITER_MOE_SITUV2` (present at main (HEAD of the clone), 1 recipe).

