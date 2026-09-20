# vLLM sync — v0.28.0 → v0.29.0

Report-only: nothing was edited or committed. 10 capabilities shipped (4 breaking changes are in section 3);
19 stale-usage root causes; 4 adoption opportunities with a bounded cohort.

## What shipped

| Concept | Capability | How enabled | Effect | Confidence |
|---|---|---|---|---|
| moe_backend | Kimi-K3 and DeepSeek V4 performance: fused MXFP4 top-k finalization in the K3 latent tail (about 5% E2E latency, #53152) | no flag — automatic | perf | medium |
| moe_backend | b12x linear and MoE backends for SM120/SM121 | `--linear-backend b12x`, `--moe-backend b12x`, `VLLM_B12X_MOE_FP4_FORCE_A16` | perf | high |
| moe_backend | Sharded RDT Engine | `--distributed-executor-backend`, `--weight-transfer-config` | usability | high |
| spec_decoding | Per-request speculative-decoding acceptance metrics in OpenAI API responses | `--per-request-spec-decode-metrics` | usability | high |
| spec_decoding | Mamba prefix caching: internal prefill checkpoints (9-25% TTFT) | no flag — automatic | perf | medium |
| parallelism | a new sharded_rdt P2P backend where each worker pulls only its TP/EP slice over NIXL or Ray Direct Transport, rank-local IPC weight updates | no flag — automatic | usability | medium |
| parallelism | FlashInfer all-reduce enabled by default for TP CUDA groups, opt out with VLLM_ALLREDUCE_USE_FLASHINFER=0 | `VLLM_ALLREDUCE_USE_FLASHINFER` | usability | medium |
| compilation | Model Runner V2 is now the default for all models: completing the rollout that began with pooling models | no flag — automatic | memory | medium |
| kv_cache | prefix-cache NONE_HASH is deterministic by default so distributed KV cache users no longer need to pin PYTHONHASHSEED | no flag — automatic | usability | medium |
| scheduling | new --max-num-queued-reqs / --max-num-queued-tokens admission-control flags | `--max-num-queued-reqs`, `--max-num-queued-tokens` | usability | high |

6 of these need no recipe edit: on by default with nothing to remove, or with no hardware/model dimension to bound a cohort.

## Adoption opportunities

**Model Runner V2 is now the default for all models: completing the rollout that began with pooling models** — compilation, confidence medium

| Recipe | Name | Value | Recipe floor | Verdict |
|---|---|---|---|---|
| `Google/gemma-4-26B-A4B-it` | `VLLM_USE_V2_MODEL_RUNNER` | `1` | 0.25.0 | redundant below floor |
| `deepseek-ai/DeepSeek-V4-Flash-Vision-Exp` | `VLLM_USE_V2_MODEL_RUNNER` | `1` | 0.29.0 | redundant explicit |
| `deepseek-ai/DeepSeek-V4-Flash-Vision-Exp` | `VLLM_USE_V2_MODEL_RUNNER` | — | unset | stale guide text |
| `deepseek-ai/DeepSeek-V4-Flash` | `VLLM_USE_V2_MODEL_RUNNER` | `1` | 0.20.0 | redundant below floor |
| `deepseek-ai/DeepSeek-V4.1-Flash` | `VLLM_USE_V2_MODEL_RUNNER` | `1` | 0.30.0 | redundant explicit |
| `moonshotai/Kimi-K3` | `VLLM_USE_V2_MODEL_RUNNER` | `1` | 0.29.0 | redundant explicit |
| `thinkingmachines/Inkling-Small` | `VLLM_USE_V2_MODEL_RUNNER` | `1` | 0.26.0 | redundant below floor |
| `thinkingmachines/Inkling-Small` | `VLLM_USE_V2_MODEL_RUNNER` | — | unset | stale guide text |
| `thinkingmachines/Inkling` | `VLLM_USE_V2_MODEL_RUNNER` | `1` | 0.26.0 | redundant below floor |
| `thinkingmachines/Inkling` | `VLLM_USE_V2_MODEL_RUNNER` | — | unset | stale guide text |
| `zai-org/GLM-5.1` | `VLLM_USE_V2_MODEL_RUNNER` | `1` | 0.24.0 | redundant below floor |
| `zai-org/GLM-5.2` | `VLLM_USE_V2_MODEL_RUNNER` | `1` | 0.24.0 | redundant below floor |
| … | +1 more in cohorts.json | | | |

Why it applies (spec_decoding): "MRV2 also gained CUDA graph memory profiling for KV cache auto-sizing (#53306), batch-sharded sampling that cuts per-step logits memory by 1/TP (#50465), prompt embeds (#42963), `extract_hidden_states` speculation (#49811), padded FULL cuda"
Tier: **report-only — needs an edit template and review before applying.**

**b12x linear and MoE backends for SM120/SM121 — linear backend** — moe_backend, confidence high
Add `--linear-backend b12x` to 12 recipes (1 already using it, excluded): Google/diffusiongemma-26B-A4B-it, Google/gemma-4-26B-A4B-it, Lightricks/LTX-2.5-Diffusers, MiniMaxAI/MiniMax-M2.7, Qwen/Qwen3.6-27B, Qwen/Qwen3.6-35B-A3B, Qwen/Qwen3.8-27B, Qwen/Qwen3.8-Flash-Next, +4 more.
⚠ 1 of them already set the same flag to a different value — that is a backend swap with a behaviour change, not an addition: nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16 (--linear-backend humming → b12x).

| Recipe | Name | Value | Recipe floor | Verdict |
|---|---|---|---|---|
| `deepseek-ai/DeepSeek-V4-Flash` | `VLLM_USE_B12X_WO_PROJECTION` | `1` | 0.20.0 | obsolete workaround → `no upstream equivalent documented` |
| `deepseek-ai/DeepSeek-V4-Flash` | `VLLM_USE_B12X_MHC` | `1` | 0.20.0 | obsolete workaround → `no upstream equivalent documented` |
| `deepseek-ai/DeepSeek-V4-Flash` | `VLLM_USE_B12X_FP8_GEMM` | `1` | 0.20.0 | obsolete workaround → `--linear-backend b12x` |
| `deepseek-ai/DeepSeek-V4-Flash` | `VLLM_USE_B12X_MOE` | `1` | 0.20.0 | obsolete workaround → `--moe-backend b12x` |
| `deepseek-ai/DeepSeek-V4-Flash` | `VLLM_USE_B12X_SPARSE_INDEXER` | `1` | 0.20.0 | obsolete workaround → `no upstream equivalent documented` |

Upstream states the default: "b12x uses MXFP8 activations by default for MXFP4 MoE and the checkpoint's activation format for NVFP4 MoE;"
Why it applies (rtx_pro_6000): "b12x provides optional CUDA kernels for NVIDIA SM120 and SM121 GPUs (RTX Pro 6000/5000, RTX 5090, DGX Spark GB10), installed with pip install vllm[b12x]."
Tier: **report-only — needs an edit template and review before applying.**

**b12x linear and MoE backends for SM120/SM121 — MoE backend (MoE models only)** — moe_backend, confidence high
Add `--moe-backend b12x` to 7 recipes (1 already using it, excluded): Google/diffusiongemma-26B-A4B-it, Google/gemma-4-26B-A4B-it, MiniMaxAI/MiniMax-M2.7, Qwen/Qwen3.6-35B-A3B, Qwen/Qwen3.8-Flash-Next, nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16, nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16.
⚠ 3 of them already set the same flag to a different value — that is a backend swap with a behaviour change, not an addition: Qwen/Qwen3.6-35B-A3B (--moe-backend marlin → b12x), Qwen/Qwen3.8-Flash-Next (--moe-backend marlin → b12x), nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16 (--moe-backend marlin → b12x).
Why it applies (rtx_pro_6000): "b12x provides optional CUDA kernels for NVIDIA SM120 and SM121 GPUs (RTX Pro 6000/5000, RTX 5090, DGX Spark GB10), installed with pip install vllm[b12x]."
Tier: **report-only — needs an edit template and review before applying.**

**b12x linear and MoE backends for SM120/SM121 — force BF16 activations for FP4 MoE** — moe_backend, confidence high
Add `VLLM_B12X_MOE_FP4_FORCE_A16` to 8 recipes: Google/diffusiongemma-26B-A4B-it, Google/gemma-4-26B-A4B-it, MiniMaxAI/MiniMax-M2.7, Qwen/Qwen3.6-35B-A3B, Qwen/Qwen3.8-Flash-Next, deepseek-ai/DeepSeek-V4-Flash, nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16, nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16.
Why it applies (rtx_pro_6000): "b12x provides optional CUDA kernels for NVIDIA SM120 and SM121 GPUs (RTX Pro 6000/5000, RTX 5090, DGX Spark GB10), installed with pip install vllm[b12x]."
Tier: **report-only — needs an edit template and review before applying.**


2 further capabilities matched more than 30 recipes, which means `applies_to` is not narrow enough to be evidence: Per-request speculative-decoding acceptance metrics in OpenAI API responses; Sharded RDT Engine. Narrow hardware/quant/traits in `capabilities.yaml` and re-run before judging these.

## Breaking & stale, by root cause

19 root causes. 1 have at least one recipe where the edit is mechanical; 13 are per-block floor questions (a newer flag inside `features.*` or `hardware_overrides.*` does not make the recipe's baseline wrong).

| ID | Flag / env | What | Recipes | Action | Confidence |
|---|---|---|---|---|---|
| R-02 | `--disable-log-requests` | removed upstream (gone in v0.17.0) | 9 | decide: drop or re-spell, replace | high |
| R-10 | `--task` | removed upstream (gone in v0.13.0) | 1 | decide: drop or re-spell | high |
| R-11 | `--guided-decoding-backend` | removed upstream (gone in v0.12.0) | 1 | decide: drop or re-spell | high |
| R-12 | `--swap-space` | removed upstream (gone in v0.18.0) | 1 | decide: drop or re-spell | high |
| R-14 | `--attention-backend` | invalid-value (needs v0.13.0) | 1 | report only | high |
| R-18 | `--dcp-comm-backend` | upstream default changed (needs v0.18.0) | 1 | report only | medium |

Also announced as breaking: PyAV video decoder backend removed; python -m vllm.entrypoints.openai.api_server is deprecated; prefix_cache_retention_interval default changed from dense to 0 for SWA/SSM models; VLLM_TEST_FORCE_FP8_MARLIN removed in favor of --linear-backend / --moe-backend.

**Per-block floor policy (13 flags, 35 recipes).** Each of these is a flag used below its introducing release, but only inside
`features.*` (opt-in), `hardware_overrides.*` or `strategy_overrides.*`. The recipe's
unconditional command is unaffected, so the model floor is not wrong — the question is whether the
block should carry its own floor. One decision covers all of them: `--language-model-only` (22), `--attention-backend` (5), `VLLM_ROCM_SHUFFLE_KV_CACHE_LAYOUT` (3), `--mm-encoder-tp-mode` (2), `VLLM_SSM_CONV_STATE_LAYOUT` (2), `VLLM_ENGINE_READY_TIMEOUT_S` (2), `VLLM_ROCM_USE_AITER` (2), `--tool-server` (2), `--async-scheduling` (1), `--linear-backend` (1), `VLLM_PREFIX_CACHE_RETENTION_INTERVAL` (1), `--speculative-config` (1), `--quantization-config.moe.activation` (1). Full list in `findings.json`.

Per-recipe lines, blocks and floors: `findings.json`.

## Unverifiable flags

Not stale usage — vLLM never shipped these, so this tool has nothing to check them against.

Each is classified by the recipe context it sits in — an omni task section, a pinned image, or the company its neighbours keep — not by how the name is spelled.

- **vllm-omni** (24 flags across 20 recipes) — recipe declares an omni task section: `--omni`, `--init-timeout`, `--deploy-config`, `--cfg-parallel-size`, `--ulysses-degree`, `--use-hsdp`, `--hsdp-shard-size`, `--diffusion-attention-backend`, +16 more.
- **vendor-image** (6 flags across 1 recipes) — block pins eugr/spark-vllm-b12x:latest: `VLLM_MEMORY_PROFILE_INCLUDE_ATTN`, `VLLM_USE_B12X_WO_PROJECTION`, `VLLM_USE_B12X_MHC`, `VLLM_USE_B12X_FP8_GEMM`, `VLLM_USE_B12X_MOE`, `VLLM_USE_B12X_SPARSE_INDEXER`.
- **unclassified** (1 flags across 1 recipes) — no plugin, vendor image or sibling context: `VLLM_ASCEND_ENABLE_PREFETCH_MLP`.
- **Newer than v0.29.0** (2) — present in the clone but not in a stable release yet, so the recipe is ahead of its pin: `VLLM_PLE_CPU_OFFLOAD` (present at v0.30.0rc2, 1 recipe), `VLLM_ROCM_USE_AITER_MOE_SITUV2` (present at main (HEAD of the clone), 1 recipe).

4 release items were out of the capability vocabulary (new model support, packaging) and are recorded in `capabilities.yaml` rather than shown above.
