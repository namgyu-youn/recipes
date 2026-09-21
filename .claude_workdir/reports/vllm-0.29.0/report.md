# vLLM sync — v0.28.0 → v0.29.0

Branch `sync/vllm-0.29.0`. 21 capabilities shipped (15 breaking changes are in section 3);
18 stale-usage root causes; 4 adoption opportunities with a bounded cohort.

**Since `vllm-0.28.0`:** 1 new root cause (`--dcp-comm-backend` default-changed), 17 carried over unchanged, 3 no longer reported (`--disable-chunked-mm-input` below-introducing-version, `--moe-backend` invalid-value, `--cc.pass_config.fuse_allreduce_rms` wrong-dash). A finding can stop being reported because the recipe changed or because upstream did — the category says which to check.

## What shipped

| Concept | Capability | How enabled | Effect | Confidence |
|---|---|---|---|---|
| parallelism | New Streaming Parser Engine: — a unified tool-call/reasoning parsing framework, with a new Kimi k2.5/k2.6/k2.7 parser and ports of seed_oss and DeepSeek V4 | no flag — automatic | usability | medium |
| parallelism | Resilient large-scale serving: a (simplified) fault tolerance framework for DP+EP external load-balancer deployments and async preparation for elastic EP scaling | no flag — automatic | usability | medium |
| parallelism | Disaggregation for hybrid models: NIXL P/D for hybrid MLA+SSM models, heterogeneous P/D block sizes for hybrid models, and MoRIIO heterogeneous TP<->DP prefill/decode read routing | no flag — automatic | usability | medium |
| parallelism | Context parallelism: --dcp-q-replicate with query replication default-on for GLM sparse attention, DCP fused attention fix for DeepSeek-V3.2 / GLM-5.2 | `--dcp-q-replicate` | correctness | high |
| parallelism | FlashInfer all-reduce enabled by default for TP CUDA groups, opt out with VLLM_ALLREDUCE_USE_FLASHINFER=0 | `VLLM_ALLREDUCE_USE_FLASHINFER` | usability | medium |
| attention_backend | FLASH_ATTN_MLA_SPARSE Hopper sparse-MLA backend, DCP + FP8 KV cache in MLA decode, XQA decode kernels | `--attention-backend FLASH_ATTN_MLA_SPARSE` | usability | high |
| attention_backend | AITER FlashAttention MLA prefill backend ROCM_AITER_FA | `--attention-backend ROCM_AITER_FA` | usability | high |
| attention_backend | Flexible attention backends: the attention backend can now be selected per KV-cache group | no flag — automatic | usability | medium |
| attention_backend | FlashAttention 4 integration deepens on SM100: FP8 KV cache support and headdim-256 support | no flag — automatic | usability | medium |
| spec_decoding | Universal speculative decoding for heterogeneous vocabularies (TLI): plus new DSpark and DFlash drafters | no flag — automatic | usability | medium |
| spec_decoding | Speculative decoding advances: DFlash2 with local convolution and a candidate selector, DSpark confidence-scheduled verification, and async scheduling auto-enabled for draft models | no flag — automatic | usability | medium |
| spec_decoding | Per-Request Acceptance Metrics | `--per-request-spec-decode-metrics` | usability | high |
| kv_cache | Tiered KV cache offloading: disk offloading support, out-of-tree secondary tier managers via module_path, partial secondary-tier load results, tiering metrics | no flag — automatic | usability | medium |
| kv_cache | prefix caching enabled by default for Mamba models | no flag — automatic | usability | medium |
| kv_cache | prefix-cache NONE_HASH is deterministic by default so distributed KV cache users no longer need to pin PYTHONHASHSEED | no flag — automatic | usability | medium |
| kernel | --linear-backend honored for ModelOpt W4A16 | `--linear-backend` | usability | high |
| kernel | b12x Linear and MoE Backends | `--linear-backend b12x`, `--moe-backend b12x`, `VLLM_B12X_MOE_FP4_FORCE_A16` | perf | high |
| compilation | and the Blackwell CUDA graph capture default raised to 1024 | no flag — automatic | usability | medium |
| compilation | Model Runner V2 is now the default for all models: completing the rollout that began with pooling models | no flag — automatic | memory | medium |
| moe_backend | tuned LL BF16 router GEMM with warmup skipped for non-MoE models, Triton tensor-descriptor path for fused MoE via VLLM_TRITON_USE_TD | `VLLM_TRITON_USE_TD` | usability | high |
| runtime | Rust frontend: --generation-config vllm | `--generation-config` | usability | high |

17 of these need no recipe edit: on by default with nothing to remove, or with no hardware/model dimension to bound a cohort.

## Adoption opportunities

**FLASH_ATTN_MLA_SPARSE Hopper sparse-MLA backend, DCP + FP8 KV cache in MLA decode, XQA decode kernels** — attention_backend, confidence high
Add `--attention-backend FLASH_ATTN_MLA_SPARSE` to 4 recipes: deepseek-ai/DeepSeek-V4-Flash, inclusionAI/Ling-3.0-flash, moonshotai/Kimi-K3, zai-org/GLM-5.3-Flash.
⚠ 4 of them already set the same flag to a different value — that is a backend swap with a behaviour change, not an addition: deepseek-ai/DeepSeek-V4-Flash (--attention-backend B12X_MLA_SPARSE → FLASH_ATTN_MLA_SPARSE), inclusionAI/Ling-3.0-flash (--attention-backend TRITON_MLA → FLASH_ATTN_MLA_SPARSE), moonshotai/Kimi-K3 (--attention-backend TOKENSPEED_MLA → FLASH_ATTN_MLA_SPARSE), zai-org/GLM-5.3-Flash (--attention-backend ROCM_AITER_MLA_SPARSE → FLASH_ATTN_MLA_SPARSE).
Why it applies (mla): "`FLASH_ATTN_MLA_SPARSE` Hopper sparse-MLA backend (#46189), DCP + FP8 KV cache in MLA decode (#44044), XQA decode kernels (#43232)."
Tier: **report-only — needs an edit template and review before applying.**

**AITER FlashAttention MLA prefill backend ROCM_AITER_FA** — attention_backend, confidence high
Add `--attention-backend ROCM_AITER_FA` to 5 recipes: deepseek-ai/DeepSeek-V4-Flash, inclusionAI/Ling-3.0-flash, moonshotai/Kimi-K3, tencent/Hy4-preview, zai-org/GLM-5.3-Flash.
⚠ 5 of them already set the same flag to a different value — that is a backend swap with a behaviour change, not an addition: deepseek-ai/DeepSeek-V4-Flash (--attention-backend B12X_MLA_SPARSE → ROCM_AITER_FA), inclusionAI/Ling-3.0-flash (--attention-backend TRITON_MLA → ROCM_AITER_FA), moonshotai/Kimi-K3 (--attention-backend TOKENSPEED_MLA → ROCM_AITER_FA), tencent/Hy4-preview (--attention-backend FLASHMLA_SPARSE → ROCM_AITER_FA), ….

| Where | Name | Value | Recipe floor | Evidence | Verdict |
|---|---|---|---|---|---|
| `meta-models/Muse-Glimmer-30B:235` | `ROCM_AITER_FA` | — | 0.28.0 | `--attention-backend ROCM_AITER_FA` | stale guide text |

2 further recipe(s) set it below the v0.25.0 floor, where it is still load-bearing — keep: MiniMaxAI/MiniMax-M3 (floor 0.24.0), Qwen/Qwen3-VL-235B-A22B-Instruct (floor 0.11.0).
Why it applies (mla): "AITER FlashAttention MLA prefill backend `ROCM_AITER_FA` (#45033)"
Tier: **report-only — needs an edit template and review before applying.**

**b12x Linear and MoE Backends — --linear-backend b12x** — kernel, confidence high
Add `--linear-backend b12x` to 11 recipes (1 already using it, excluded): Google/diffusiongemma-26B-A4B-it, Google/gemma-4-26B-A4B-it, MiniMaxAI/MiniMax-M2.7, Qwen/Qwen3.6-27B, Qwen/Qwen3.6-35B-A3B, Qwen/Qwen3.8-27B, Qwen/Qwen3.8-Flash-Next, inclusionAI/Ling-3.0-flash, +3 more.
⚠ 1 of them already set the same flag to a different value — that is a backend swap with a behaviour change, not an addition: nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16 (--linear-backend humming → b12x).
Why it applies (mxfp8): "b12x uses MXFP8 activations by default for MXFP4 MoE and the checkpoint's activation format for NVFP4 MoE."
Tier: **report-only — needs an edit template and review before applying.**

**b12x Linear and MoE Backends — --moe-backend b12x (NVFP4/MXFP4 MoE, TP only)** — kernel, confidence high
Add `--moe-backend b12x` to 7 recipes (1 already using it, excluded): Google/diffusiongemma-26B-A4B-it, Google/gemma-4-26B-A4B-it, MiniMaxAI/MiniMax-M2.7, Qwen/Qwen3.6-35B-A3B, Qwen/Qwen3.8-Flash-Next, nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16, nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16.
⚠ 3 of them already set the same flag to a different value — that is a backend swap with a behaviour change, not an addition: Qwen/Qwen3.6-35B-A3B (--moe-backend marlin → b12x), Qwen/Qwen3.8-Flash-Next (--moe-backend marlin → b12x), nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16 (--moe-backend marlin → b12x).
Why it applies (nvfp4): "Select the linear and MoE backends explicitly with: vllm serve <model> \ --linear-backend b12x \ --moe-backend b12x Only pass `--moe-backend b12x` for a compatible NVFP4 or MXFP4 MoE model."
Tier: **report-only — needs an edit template and review before applying.**


2 further capabilities matched more than 30 recipes, which means `applies_to` is not narrow enough to be evidence: tuned LL BF16 router GEMM with warmup skipped for non-MoE models, Triton tensor-descriptor path for fused MoE via VLLM_TRITON_USE_TD; Per-Request Acceptance Metrics. Narrow hardware/quant/traits in `capabilities.yaml` and re-run before judging these.

## Breaking & stale, by root cause

18 root causes. 0 have at least one recipe where the edit is mechanical; 12 are per-block floor questions (a newer flag inside `features.*` or `hardware_overrides.*` does not make the recipe's baseline wrong).

| ID | Flag / env | What | Recipes | Action | Confidence |
|---|---|---|---|---|---|
| R-08 | `--task` | removed upstream (gone in v0.13.0) | 1 | decide: drop or re-spell | high · carried over |
| R-09 | `--rope-scaling` | removed upstream (gone in v0.11.1) | 1 | decide: drop or re-spell | high · carried over |
| R-10 | `--attention-backend` | invalid-value — deepseek-ai/DeepSeek-V4-Flash sets `B12X_MLA_SPARSE`, not accepted at the target tag (accepted: AMX_MLA, CPU_ATTN, CPU_MLA, CUSTOM, …) | 1 | report only | low · carried over |
| R-12 | `VLLM_USE_BREAKABLE_CUDAGRAPH` | used below its introducing release (needs v0.22.0) | 1 | vendor-image block — cannot move a pin | high · carried over |
| R-16 | `--disable-log-requests` | removed upstream (gone in v0.17.0) | 1 | decide: drop or re-spell | high · carried over |
| R-17 | `--dcp-comm-backend` | upstream default changed — the recipe sets this flag explicitly, so the changed default does not reach it | 1 | report only | medium |

- `--task` → no replacement documented. read the argparse help, the config field docstring and every deprecation line mentioning it at v0.12.0; none names a replacement
  > model_group.add_argument('--task', **model_kwargs['task'], deprecated=True)
- `--rope-scaling` → no replacement documented. read the argparse help, the config field docstring and every deprecation line mentioning it at v0.11.0; none names a replacement
  > model_group.add_argument('--rope-scaling', **model_kwargs['rope_scaling'])
- `--disable-log-requests` → replace with `--enable-log-requests`. its default was the negation of enable_log_requests at v0.16.0 (vllm/engine/arg_utils.py:2087), and --enable-log-requests exists at the target tag
  > parser.add_argument('--disable-log-requests', action=argparse.BooleanOptionalAction, default=not AsyncEngineArgs.enable_log_requests, help='[DEPRECATED] Disable logging requests.', deprecated=True)
Also announced as breaking: PagedAttention has been removed: The legacy attention implementation is deleted now that V1/MRv2 backends are the standard path; Models removed: Baichuan, Aquila, Grok, Tarsier / Tarsier2, AyaVision / MusicFlamingo, Mantis; Deprecated the old FP8 online MoE quantization class; Models removed: TeleChat, Persimmon and Fuyu; Models removed: Plamo2, Ouro; Removed the no-longer-supported max_num_partial_prefills and max_long_partial_prefills arguments; bitsandbytes support migrated to an out-of-tree plugin; The deprecated calculate_kv_scales runtime KV scale calculation was removed; override_attention_dtype was removed; MoE legacy code removed; ten deprecated model architectures removed; PyAV video decoder backend removed; python -m vllm.entrypoints.openai.api_server is deprecated; prefix_cache_retention_interval default changed from dense to 0 for SWA/SSM models; VLLM_TEST_FORCE_FP8_MARLIN removed in favor of --linear-backend / --moe-backend.

**Per-block floor policy (12 flags, 33 recipes).** Each of these is a flag used below its introducing release, but only inside
`features.*` (opt-in), `hardware_overrides.*` or `strategy_overrides.*`. The recipe's
unconditional command is unaffected, so the model floor is not wrong — the question is whether the
block should carry its own floor. One decision covers all of them: `--language-model-only` (22), `--attention-backend` (5), `--moe-backend` (4), `VLLM_ROCM_SHUFFLE_KV_CACHE_LAYOUT` (3), `--mm-encoder-tp-mode` (2), `VLLM_SSM_CONV_STATE_LAYOUT` (2), `VLLM_ENGINE_READY_TIMEOUT_S` (2), `--linear-backend` (1), `--prefill-schedule-interval` (1), `--speculative-config` (1), `VLLM_ROCM_USE_AITER` (1), `--quantization-config.moe.activation` (1). Full list in `findings.json`.

Per-recipe lines, blocks and floors: `findings.json`.

## Model-support floors

328 checkpoints checked across the recipes that the in-tree wheel serves. 0 pin a vLLM release older than the one that first registered their architecture, so the version the recipe claims to support cannot serve the model at all.

Nothing below its introducing release.

**40 recipes were skipped, not cleared.** Their documented serving path is not the in-tree wheel — an omni recipe, a non-first-party image, a `vllm==` pin in the guide, or an architecture selected via `--hf-overrides` — so the plugin or image registers the architecture itself and `registry.py` says nothing about their floor. Raising one from the registry would contradict the recipe's own release-tested pin. Never auto-apply to these.

- `Google/gemma-4-26B-A4B-it` — pins a non-first-party image (eugr/spark-vllm:nightly-20260704) that may register the architecture
- `IndexTeam/IndexTTS-2.5` — omni recipe — served through vllm-omni, which registers the architecture itself
- `Lightricks/LTX-2.5-Diffusers` — omni recipe — served through vllm-omni, which registers the architecture itself
- `MiniMaxAI/MiniMax-H3` — omni recipe — served through vllm-omni, which registers the architecture itself
- `OpenMOSS-Team/MOSS-SoundEffect` — omni recipe — served through vllm-omni, which registers the architecture itself
- `OpenMOSS-Team/MOSS-TTS-Realtime` — omni recipe — served through vllm-omni, which registers the architecture itself
- `OpenMOSS-Team/MOSS-TTS` — omni recipe — served through vllm-omni, which registers the architecture itself
- `OpenMOSS-Team/MOSS-TTSD-v1.0` — omni recipe — served through vllm-omni, which registers the architecture itself
- …32 more in `model-floors.json`.

0 recipes declare no floor at all and 0 use an architecture upstream has dropped. 23 checkpoints could not be checked because their `config.json` is unreadable (18 gated, 5 with no `config.json`). 12 name an architecture the v0.29.0 registry lacks: 11 registered on main since, of which 6 declare a floor at or below v0.29.0 or none at all (`IFM/K2-Horizon-0.9B`, `IFM/K2-Horizon-3.7B`, `IFM/K2-Horizon-32B`, `IFM/K2-Horizon-375B-A23B`, `IFM/K2-Horizon-7B`, `IFM/K2-Horizon-MoVA-36B-A4B`), and 1 unregistered on main too (plugin, out-of-tree, or a `params.json` architecture). Per-recipe detail: `model-floors.json`.

## Unverifiable flags

Not stale usage — vLLM never shipped these, so this tool has nothing to check them against.

Each is classified by the recipe context it sits in — an omni task section, a pinned image, or the company its neighbours keep — not by how the name is spelled.

- **vllm-omni** (24 flags across 20 recipes) — name is in that plugin's namespace: `--omni`, `--init-timeout`, `--deploy-config`, `--cfg-parallel-size`, `--ulysses-degree`, `--use-hsdp`, `--hsdp-shard-size`, `--diffusion-attention-backend`, +16 more.
- **vendor-image** (6 flags across 1 recipes) — block pins eugr/spark-vllm-b12x:latest: `VLLM_MEMORY_PROFILE_INCLUDE_ATTN`, `VLLM_USE_B12X_WO_PROJECTION`, `VLLM_USE_B12X_MHC`, `VLLM_USE_B12X_FP8_GEMM`, `VLLM_USE_B12X_MOE`, `VLLM_USE_B12X_SPARSE_INDEXER`.
- **vllm-ascend** (1 flags across 1 recipes) — name is in that plugin's namespace: `VLLM_ASCEND_ENABLE_PREFETCH_MLP`.
- **Newer than v0.29.0** (2) — present in the clone but not in a stable release yet, so the recipe is ahead of its pin: `VLLM_PLE_CPU_OFFLOAD` (present at v0.30.0rc2, 1 recipe), `VLLM_ROCM_USE_AITER_MOE_SITUV2` (present at main (HEAD of the clone), 1 recipe).

38 release items were out of the capability vocabulary (new model support, packaging) and are recorded in `capabilities.yaml` rather than shown above.
