# vLLM sync — v0.28.0 → v0.29.0

Report-only: nothing was edited or committed. 23 capabilities shipped; 26 stale-usage root causes across the recipes;
2 adoption opportunities with a bounded cohort.

## What shipped

| Concept | Capability | How enabled | Effect | Confidence |
|---|---|---|---|---|
| spec_decoding | Model Runner V2 is now the default for all models | no flag — automatic | memory | medium |
| spec_decoding | Speculative decoding | `--per-request-spec-decode-metrics` | usability | high |
| spec_decoding | Mamba prefix caching | no flag — automatic | perf | medium |
| spec_decoding | docs: features/per_request_metrics.md | `--per-request-spec-decode-metrics` | usability | high |
| spec_decoding | docs: features/speculative_decoding/acceptance_metrics.md | `--per-request-spec-decode-metrics` | correctness | high |
| other | Ten deprecated architectures removed: Arctic, Chameleon, Cheer | no flag — automatic | usability | medium |
| other | FlexOlmo, Olmo3, Hunyuan V1 and Hunyuan VL are now served thro | no flag — automatic | usability | medium |
| other | PyAV video decoder backend removed; use OpenCV or Torchcodec ( | no flag — automatic | usability | medium |
| other | Model Runner V2 is the default runner for all models (#53183) | no flag — automatic | usability | medium |
| attention_backend | New defaults | `VLLM_ALLREDUCE_USE_FLASHINFER` | usability | medium |
| attention_backend | FlashInfer all-reduce enabled by default (#52998) | no flag — automatic | usability | medium |
| attention_backend | docs: serving/online_serving/trace_replay.md | `--enable-trace-replay` | correctness | high |
| moe_backend | VLLM_TEST_FORCE_FP8_MARLIN removed in favor of --linear-backen | `--attention-config` `--linear-backend` `--moe-backend` | usability | high |
| moe_backend | docs: features/quantization/b12x.md | `--linear-backend` `--moe-backend` `VLLM_B12X_MOE_FP4_FORCE_A16` | perf | high |
| moe_backend | docs: training/weight_transfer/sharded_rdt.md | `--distributed-executor-backend` `--weight-transfer-config` | usability | high |
| frontend | python -m vllm | no flag — automatic | usability | medium |
| frontend | docs: usage/security.md | `VLLM_MAX_MEDIA_DOWNLOAD_SIZE_MB` | memory | high |
| quantization | New models | no flag — automatic | usability | medium |
| linear_backend | Kimi-K3 and DeepSeek V4 performance | no flag — automatic | perf | medium |
| parallelism | RL weight sync | no flag — automatic | usability | medium |
| kv_cache | New defaults | no flag — automatic | usability | medium |
| scheduling | New defaults | `--max-num-queued-reqs` `--max-num-queued-tokens` | usability | high |
| default_change | prefix_cache_retention_interval default changed from dense to  | no flag — automatic | correctness | medium |

9 of these need no recipe edit (on by default, or no hardware/model evidence to bound them).

## Adoption opportunities

**Kimi-K3 and DeepSeek V4 performance** — linear_backend, perf, confidence medium
Enable with no flag — automatic. Cohort: 9 recipes — MiniMaxAI/MiniMax-M3, Qwen/Qwen3.5-397B-A17B, Qwen/Qwen3.8-2.4T-A95B, moonshotai/Kimi-K2.5, moonshotai/Kimi-K3, openai/gpt-oss-120b, thinkingmachines/Inkling, zai-org/GLM-5.1, +1 more.
Evidence: Highlights, PRs #49636, #50493, #52188, #52388, #52823, #53040.
Tier: **report-only until an edit template is written and reviewed.**

**docs: features/quantization/b12x.md** — moe_backend, perf, confidence high
Enable with `--linear-backend` `--moe-backend` `VLLM_B12X_MOE_FP4_FORCE_A16`. Cohort: 28 recipes (18 recipes already use it) — Google/diffusiongemma-26B-A4B-it, Google/gemma-4-26B-A4B-it, JetBrains/Mellum2-12B-A2.5B-Thinking, MiniMaxAI/MiniMax-M2.7, MiniMaxAI/MiniMax-M2, Qwen/Qwen3-235B-A22B-Instruct-2507, Qwen/Qwen3-Coder-480B-A35B-Instruct, Qwen/Qwen3-VL-235B-A22B-Instruct, +20 more.
Evidence: docs/features/quantization/b12x.md.
Tier: **report-only until an edit template is written and reviewed.**


12 further capabilities matched more than 30 recipes, which means `applies_to` is not narrow enough to be evidence: new-models, speculative-decoding, rl-weight-sync, ten-deprecated-architectures-removed-arctic-cham, flexolmo-olmo3-hunyuan-v1-and-hunyuan-vl-are-now, pyav-video-decoder-backend-removed-use-opencv-or, …. Narrow hardware/quant/traits in `capabilities.yaml` and re-run before judging these.

## Breaking & stale, by root cause

26 root causes. 3 have at least one recipe where the edit is mechanical; 16 are per-block floor questions (a newer flag inside `features.*` or `hardware_overrides.*` does not make the recipe's baseline wrong).

| ID | Flag / env | What | Recipes | Action | Confidence |
|---|---|---|---|---|---|
| R-01 | `--language-model-only` | used below its introducing release (needs v0.17.0) | 22 | per-block floor question | high |
| R-02 | `--disable-log-requests` | removed upstream (gone in v0.17.0) | 9 | decide: drop or re-spell | high |
| R-03 | `--attention-backend` | used below its introducing release (needs v0.13.0) | 5 | per-block floor question | high |
| R-04 | `--mm-encoder-tp-mode` | used below its introducing release (needs v0.10.2) | 5 | raise model floor, per-block floor question | high |
| R-05 | `--moe-backend` | used below its introducing release (needs v0.17.0) | 4 | per-block floor question | high |
| R-06 | `VLLM_ROCM_SHUFFLE_KV_CACHE_LAYOUT` | used below its introducing release (needs v0.15.0) | 3 | per-block floor question | high |
| R-07 | `VLLM_ROCM_USE_AITER` | used below its introducing release (needs v0.8.2) | 3 | per-block floor question | high |
| R-08 | `--data-parallel-size` | used below its introducing release (needs v0.8.3) | 2 | per-block floor question | high |
| R-09 | `VLLM_SSM_CONV_STATE_LAYOUT` | used below its introducing release (needs v0.20.0) | 2 | per-block floor question | high |
| R-10 | `VLLM_ENGINE_READY_TIMEOUT_S` | used below its introducing release (needs v0.14.0) | 2 | per-block floor question | high |
| R-11 | `--tool-server` | used below its introducing release (needs v0.10.1) | 2 | per-block floor question | high |
| R-12 | `--task` | removed upstream (gone in v0.13.0) | 1 | decide: drop or re-spell | high |
| R-13 | `VLLM_USE_V1` | removed upstream (gone in v0.11.1) | 1 | decide: drop or re-spell | high |
| R-14 | `--guided-decoding-backend` | removed upstream (gone in v0.12.0) | 1 | decide: drop or re-spell | high |
| R-15 | `--disable-chunked-mm-input` | used below its introducing release (needs v0.8.4) | 1 | per-block floor question | high |
| R-16 | `--swap-space` | removed upstream (gone in v0.18.0) | 1 | decide: drop or re-spell | high |
| R-17 | `--async-scheduling` | used below its introducing release (needs v0.10.0) | 1 | per-block floor question | high |
| R-18 | `--rope-scaling` | removed upstream (gone in v0.11.1) | 1 | decide: drop or re-spell | high |
| R-19 | `--linear-backend` | used below its introducing release (needs v0.22.0) | 1 | raise variant pin | high |
| R-20 | `VLLM_USE_BREAKABLE_CUDAGRAPH` | used below its introducing release (needs v0.22.0) | 1 | raise variant pin | high |
| R-21 | `--prefill-schedule-interval` | used below its introducing release (needs v0.24.0) | 1 | per-block floor question | high |
| R-22 | `VLLM_PREFIX_CACHE_RETENTION_INTERVAL` | used below its introducing release (needs v0.23.0) | 1 | per-block floor question | high |
| R-23 | `--speculative-config` | used below its introducing release (needs v0.8.2) | 1 | per-block floor question | high |
| R-24 | `--dcp-comm-backend` | upstream default changed (needs v0.18.0) | 1 | report only | medium |
| R-25 | `--quantization-config.moe.activation` | used below its introducing release (needs v0.20.0) | 1 | per-block floor question | high |
| R-26 | `--cc.pass_config.fuse_allreduce_rms` | wrong dash — argparse rejects it | 1 | replace | high |

Per-recipe lines, blocks and floors: `findings.json`.

## Unverifiable plugin flags

33 flags/envs across 24 recipes are not shipped by vLLM at any indexed tag and are almost certainly registered by a plugin or vendor image (vllm-omni, vllm-ascend, vendor builds). They are **not** stale usage and this tool cannot verify them: `--omni`, `--init-timeout`, `--deploy-config`, `--cfg-parallel-size`, `--ulysses-degree`, `--use-hsdp`, `--hsdp-shard-size`, `--diffusion-attention-backend`, `--model-class-name`, `--num-gpus`, `--usp`, `--ring`, +21 more.
