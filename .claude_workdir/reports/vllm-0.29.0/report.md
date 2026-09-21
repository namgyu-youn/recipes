# vLLM sync — v0.24.0 → v0.29.0

Report-only: nothing was edited or committed. 41 capabilities shipped (14 breaking changes are in section 3);
21 stale-usage root causes; 4 adoption opportunities with a bounded cohort.

## What shipped

| Concept | Capability | How enabled | Effect | Confidence |
|---|---|---|---|---|
| spec_decoding | Universal speculative decoding for heterogeneous vocabularies (TLI): plus new DSpark and DFlash drafters | no flag — automatic | usability | medium |
| spec_decoding | New Inkling model family: with a full support stack: base modeling, piecewise CUDA graph support, Hopper FA4 relative attention, MTP=1 speculative decoding, LoRA | no flag — automatic | usability | medium |
| spec_decoding | DeepSeek-V4 performance push: across vendors: a specialized routing kernel (2.94% E2E TPOT, #48660), fused_topk_bias (1.5–2x kernel, #47463) | no flag — automatic | perf | medium |
| spec_decoding | DeepSeek V4: sparse MLA now works end-to-end for plain decode, MTP, and DSpark speculative decoding, joined by AMD Quark NVFP4 support | no flag — automatic | perf | medium |
| spec_decoding | Speculative decoding advances: DFlash2 with local convolution and a candidate selector, DSpark confidence-scheduled verification, and async scheduling auto-enabled for draft models | no flag — automatic | usability | medium |
| spec_decoding | Per-Request Acceptance Metrics | `--per-request-spec-decode-metrics` | usability | high |
| spec_decoding | internal prefill checkpoints deliver a 9%-25% TTFT improvement | no flag — automatic | perf | medium |
| attention_backend | FLASH_ATTN_MLA_SPARSE Hopper sparse-MLA backend, DCP + FP8 KV cache in MLA decode, XQA decode kernels | `--attention-backend FLASH_ATTN_MLA_SPARSE` | usability | high |
| attention_backend | AITER FlashAttention MLA prefill backend ROCM_AITER_FA | `--attention-backend ROCM_AITER_FA` | usability | high |
| attention_backend | Flexible attention backends: the attention backend can now be selected per KV-cache group | no flag — automatic | usability | medium |
| attention_backend | FlashAttention 4 integration deepens on SM100: FP8 KV cache support and headdim-256 support | no flag — automatic | usability | medium |
| attention_backend | DeepSeek-V4 performance push: sequence parallelism, ~2x kernel improvement by skipping empty c128 launches, 3.4% E2E TTFT from skipping unneeded topk/router | no flag — automatic | memory | medium |
| attention_backend | FlashInfer all-reduce enabled by default for TP CUDA groups, opt out with VLLM_ALLREDUCE_USE_FLASHINFER=0 | `VLLM_ALLREDUCE_USE_FLASHINFER` | usability | medium |
| parallelism | New Streaming Parser Engine: — a unified tool-call/reasoning parsing framework, with a new Kimi k2.5/k2.6/k2.7 parser and ports of seed_oss and DeepSeek V4 | no flag — automatic | usability | medium |
| parallelism | KV offloading & tiered secondary storage: matured substantially: offloading metrics, tier-owned event handling, object-store secondary tier with workload identity, DP-replica-aware tiering | no flag — automatic | usability | medium |
| parallelism | Resilient large-scale serving: a (simplified) fault tolerance framework for DP+EP external load-balancer deployments and async preparation for elastic EP scaling | no flag — automatic | usability | medium |
| parallelism | Disaggregation for hybrid models: NIXL P/D for hybrid MLA+SSM models, heterogeneous P/D block sizes for hybrid models, and MoRIIO heterogeneous TP<->DP prefill/decode read routing | no flag — automatic | usability | medium |
| parallelism | Kimi-K3 performance push: a major optimization effort for Kimi-K3 across the stack — Decode Context Parallel (DCP) support, fused FlashKDA decode and prefill kernels | no flag — automatic | memory | medium |
| parallelism | Context parallelism: --dcp-q-replicate with query replication default-on for GLM sparse attention, DCP fused attention fix for DeepSeek-V3.2 / GLM-5.2 | `--dcp-q-replicate` | correctness | high |
| compilation | Model Runner V2 is now the default for all dense models: Building on quantized-model support from the previous release, MRv2 is now the standard execution path, with new support for EVS, realtime embeddings | no flag — automatic | usability | medium |
| compilation | Model Runner V2 expands to non-generative workloads: encoder-only attention, sequence pooling for embedding/classification, encoder token classification and token embedding, BGE-M3 pooling | no flag — automatic | usability | medium |
| compilation | Model Runner V2 maturation: E/P/D disaggregation, weight offloading, multi-layer MTP KV cache support, encoder CUDA graphs | no flag — automatic | usability | medium |
| compilation | and the Blackwell CUDA graph capture default raised to 1024 | no flag — automatic | usability | medium |
| compilation | Model Runner V2 is now the default for all models: completing the rollout that began with pooling models | no flag — automatic | memory | medium |
| moe_backend | The Transformers modeling backend is now as fast as native vLLM: and gained FP8 MoE support, CUDA graph + embed scaling fixes, and migration of GPTBigCode/Starcoder2 and RoBERTa | no flag — automatic | correctness | medium |
| moe_backend | tuned LL BF16 router GEMM with warmup skipped for non-MoE models, Triton tensor-descriptor path for fused MoE via VLLM_TRITON_USE_TD | `VLLM_TRITON_USE_TD` | usability | high |
| moe_backend | MoE refactor: FusedMoE renamed to FusedMoEFactory, MoeWNA16 migrated to the MK oracle scheme | no flag — automatic | usability | medium |
| moe_backend | Kimi K3 support: with a full stack landing in one release: core model files and kernels, Python and Rust frontends, AttnRes kernels, DeepGEMM support | no flag — automatic | usability | medium |
| moe_backend | More new models: Qwen3.5 text-only dense and MoE models with EVS video token pruning, K-EXAONE-2.0-750B-A37B, VaultGemma via the Transformers modeling backend | no flag — automatic | usability | medium |
| kv_cache | Tiered KV cache offloading: disk offloading support, out-of-tree secondary tier managers via module_path, partial secondary-tier load results, tiering metrics | no flag — automatic | usability | medium |
| kv_cache | prefix caching enabled by default for Mamba models | no flag — automatic | usability | medium |
| kv_cache | KV offload tiering metrics renamed from kv_offload_tiering_block_{queries,hits} to ..._chunk_ | no flag — automatic | usability | medium |
| kv_cache | prefix-cache NONE_HASH is deterministic by default so distributed KV cache users no longer need to pin PYTHONHASHSEED | no flag — automatic | usability | medium |
| runtime | MoE communication: DeepEP v2 receiver CPU overhead and MXFP8 activation scale dispatch, FlashInfer one-sided All2All refinements | `--enforce-eager` | correctness | high |
| runtime | Rust frontend: --generation-config vllm | `--generation-config` | usability | high |
| runtime | Adaptive Verification: --enforce-eager, --speculative-config, --tokenizer-mode | `--enforce-eager`, `--speculative-config`, `--tokenizer-mode`, `--trust-remote-code`, `VLLM_ADAPTIVE_VERIFICATION_PROFILE_CONTEXT_LEN` | memory | high |
| runtime | Sampling Mask (Distribution Replay) | `--logits-processors`, `--logprobs-mode`, `--return-sampling-mask` | usability | high |
| kernel | --linear-backend honored for ModelOpt W4A16 | `--linear-backend flashinfer_cutedsl` | usability | high |
| kernel | b12x Linear and MoE Backends | `--linear-backend b12x`, `--moe-backend b12x`, `VLLM_B12X_MOE_FP4_FORCE_A16` | perf | high |
| scheduling | New endpoints & options: --max-num-queued-reqs / --max-num-queued-tokens | `--max-num-queued-reqs`, `--max-num-queued-tokens` | usability | high |
| quantization | Kimi-K3 and DeepSeek V4 performance: fused MXFP4 top-k finalization in the K3 latent tail (about 5% E2E latency, #53152) | no flag — automatic | perf | medium |

37 of these need no recipe edit: on by default with nothing to remove, or with no hardware/model dimension to bound a cohort.

## Adoption opportunities

**FLASH_ATTN_MLA_SPARSE Hopper sparse-MLA backend, DCP + FP8 KV cache in MLA decode, XQA decode kernels** — attention_backend, confidence high
Add `--attention-backend FLASH_ATTN_MLA_SPARSE` to 3 recipes: deepseek-ai/DeepSeek-V4-Flash, inclusionAI/Ling-3.0-flash, zai-org/GLM-5.3-Flash.
⚠ 3 of them already set the same flag to a different value — that is a backend swap with a behaviour change, not an addition: deepseek-ai/DeepSeek-V4-Flash (--attention-backend B12X_MLA_SPARSE → FLASH_ATTN_MLA_SPARSE), inclusionAI/Ling-3.0-flash (--attention-backend TRITON_MLA → FLASH_ATTN_MLA_SPARSE), zai-org/GLM-5.3-Flash (--attention-backend ROCM_AITER_MLA_SPARSE → FLASH_ATTN_MLA_SPARSE).
Why it applies (fp8): "`FLASH_ATTN_MLA_SPARSE` Hopper sparse-MLA backend (#46189), DCP + FP8 KV cache in MLA decode (#44044), XQA decode kernels (#43232)."
Tier: **report-only — needs an edit template and review before applying.**

**MoE communication: DeepEP v2 receiver CPU overhead and MXFP8 activation scale dispatch, FlashInfer one-sided All2All refinements** — runtime, confidence high
Add `--enforce-eager` to 2 recipes: MiniMaxAI/MiniMax-M3, tencent/Hy4-preview.
Why it applies (cpu): "**MoE communication**: DeepEP v2 receiver CPU overhead (#51114) and MXFP8 activation scale dispatch (#51398), FlashInfer one-sided All2All refinements (#51924), DeepEP v2 fixes for `--enforce-eager` startup (#51824) and the decode/cudagraph"
Tier: **report-only — needs an edit template and review before applying.**

**b12x Linear and MoE Backends** — kernel, confidence high
Add `--linear-backend b12x`, `--moe-backend b12x`, `VLLM_B12X_MOE_FP4_FORCE_A16` to 8 recipes (1 already using it, excluded): Google/diffusiongemma-26B-A4B-it, Google/gemma-4-26B-A4B-it, MiniMaxAI/MiniMax-M2.7, Qwen/Qwen3.6-35B-A3B, Qwen/Qwen3.8-Flash-Next, inclusionAI/Ling-3.0-flash, nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16, nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16.
⚠ 3 of them already set the same flag to a different value — that is a backend swap with a behaviour change, not an addition: Qwen/Qwen3.6-35B-A3B (--moe-backend marlin → b12x), Qwen/Qwen3.8-Flash-Next (--moe-backend marlin → b12x), nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16 (--linear-backend humming → b12x).

| Where | Name | Value | Recipe floor | Evidence | Verdict |
|---|---|---|---|---|---|
| `deepseek-ai/DeepSeek-V4.1-Flash:385` | `NVIDIA` | — | 0.30.0 | `only offers Docker. On NVIDIA that is `vllm/vllm-openai:nightly`: the architecture` | stale guide text |

21 further recipe(s) set it below the v0.29.0 floor, where it is still load-bearing — keep: Google/gemma-4-12B-it (floor 0.23.0), Google/gemma-4-26B-A4B-it (floor 0.25.0), Google/gemma-4-31B-it (floor 0.19.1), Google/gemma-4-E2B-it (floor 0.19.1), Google/gemma-4-E4B-it (floor 0.19.1), MiniMaxAI/MiniMax-M3 (floor 0.24.0).
Why it applies (dgx_spark_gb10): "# b12x Linear and MoE Backends [b12x](https://pypi.org/project/b12x/) provides optional CUDA kernels for NVIDIA SM120 and SM121 GPUs."
Tier: **report-only — needs an edit template and review before applying.**

**Adaptive Verification: --enforce-eager, --speculative-config, --tokenizer-mode** — runtime, confidence high
Add `--enforce-eager`, `--speculative-config`, `--tokenizer-mode`, `--trust-remote-code`, `VLLM_ADAPTIVE_VERIFICATION_PROFILE_CONTEXT_LEN` to 1 recipes (63 already using it, excluded): zai-org/GLM-OCR.
Why it applies (spec_decoding): "# Adaptive Verification Speculative decoding buys fewer decode steps with more compute."
Tier: **report-only — needs an edit template and review before applying.**


3 further capabilities matched more than 30 recipes, which means `applies_to` is not narrow enough to be evidence: AITER FlashAttention MLA prefill backend ROCM_AITER_FA; tuned LL BF16 router GEMM with warmup skipped for non-MoE models, Triton tensor-descriptor path for fused MoE via VLLM_TRITON_USE_TD; Per-Request Acceptance Metrics. Narrow hardware/quant/traits in `capabilities.yaml` and re-run before judging these.

## Breaking & stale, by root cause

21 root causes. 1 have at least one recipe where the edit is mechanical; 13 are per-block floor questions (a newer flag inside `features.*` or `hardware_overrides.*` does not make the recipe's baseline wrong).

| ID | Flag / env | What | Recipes | Action | Confidence |
|---|---|---|---|---|---|
| R-03 | `--mm-encoder-tp-mode` | used below its introducing release (needs v0.10.2) | 5 | raise model floor, per-block floor question | high |
| R-09 | `--task` | removed upstream (gone in v0.13.0) | 1 | decide: drop or re-spell | high |
| R-11 | `--rope-scaling` | removed upstream (gone in v0.11.1) | 1 | decide: drop or re-spell | high |
| R-12 | `--attention-backend` | invalid-value — deepseek-ai/DeepSeek-V4-Flash sets `B12X_MLA_SPARSE`, not accepted at the target tag (accepted: AMX_MLA, CPU_ATTN, CPU_MLA, CUSTOM, …) | 1 | report only | low |
| R-14 | `VLLM_USE_BREAKABLE_CUDAGRAPH` | used below its introducing release (needs v0.22.0) | 1 | vendor-image block — cannot move a pin | high |
| R-16 | `--long-prefill-token-threshold` | upstream default changed — the recipe relies on the default, which changed upstream | 1 | report only | medium |
| R-18 | `--disable-log-requests` | removed upstream (gone in v0.17.0) | 1 | decide: drop or re-spell | high |
| R-19 | `--dcp-comm-backend` | upstream default changed — the recipe sets this flag explicitly, so the changed default does not reach it | 1 | report only | medium |
| R-21 | `--cc.pass_config.fuse_allreduce_rms` | wrong dash — argparse rejects it | 1 | replace | high |

- `--task` → no replacement documented. read the argparse help, the config field docstring and every deprecation line mentioning it at v0.12.0; none names a replacement
  > model_group.add_argument('--task', **model_kwargs['task'], deprecated=True)
- `--rope-scaling` → no replacement documented. read the argparse help, the config field docstring and every deprecation line mentioning it at v0.11.0; none names a replacement
  > model_group.add_argument('--rope-scaling', **model_kwargs['rope_scaling'])
- `--disable-log-requests` → replace with `--enable-log-requests`. its default was the negation of enable_log_requests at v0.16.0 (vllm/engine/arg_utils.py:2087), and --enable-log-requests exists at the target tag
  > parser.add_argument('--disable-log-requests', action=argparse.BooleanOptionalAction, default=not AsyncEngineArgs.enable_log_requests, help='[DEPRECATED] Disable logging requests.', deprecated=True)
Also announced as breaking: PagedAttention has been removed: The legacy attention implementation is deleted now that V1/MRv2 backends are the standard path; Models removed: Baichuan, Aquila, Grok, Tarsier / Tarsier2, AyaVision / MusicFlamingo, Mantis; Deprecated the old FP8 online MoE quantization class; Models removed: TeleChat, Persimmon and Fuyu; Models removed: Plamo2, Ouro; Removed the no-longer-supported max_num_partial_prefills and max_long_partial_prefills arguments; bitsandbytes support migrated to an out-of-tree plugin; The deprecated calculate_kv_scales runtime KV scale calculation was removed; override_attention_dtype was removed; MoE legacy code removed; PyAV video decoder backend removed; python -m vllm.entrypoints.openai.api_server is deprecated; prefix_cache_retention_interval default changed from dense to 0 for SWA/SSM models; VLLM_TEST_FORCE_FP8_MARLIN removed in favor of --linear-backend / --moe-backend.

**Per-block floor policy (12 flags, 34 recipes).** Each of these is a flag used below its introducing release, but only inside
`features.*` (opt-in), `hardware_overrides.*` or `strategy_overrides.*`. The recipe's
unconditional command is unaffected, so the model floor is not wrong — the question is whether the
block should carry its own floor. One decision covers all of them: `--language-model-only` (22), `--attention-backend` (5), `--moe-backend` (4), `VLLM_ROCM_SHUFFLE_KV_CACHE_LAYOUT` (3), `VLLM_ROCM_USE_AITER` (3), `VLLM_SSM_CONV_STATE_LAYOUT` (2), `VLLM_ENGINE_READY_TIMEOUT_S` (2), `--disable-chunked-mm-input` (1), `--linear-backend` (1), `--prefill-schedule-interval` (1), `--speculative-config` (1), `--quantization-config.moe.activation` (1). Full list in `findings.json`.

Per-recipe lines, blocks and floors: `findings.json`.

## Unverifiable flags

Not stale usage — vLLM never shipped these, so this tool has nothing to check them against.

Each is classified by the recipe context it sits in — an omni task section, a pinned image, or the company its neighbours keep — not by how the name is spelled.

- **vllm-omni** (24 flags across 20 recipes) — name is in that plugin's namespace: `--omni`, `--init-timeout`, `--deploy-config`, `--cfg-parallel-size`, `--ulysses-degree`, `--use-hsdp`, `--hsdp-shard-size`, `--diffusion-attention-backend`, +16 more.
- **vendor-image** (6 flags across 1 recipes) — block pins eugr/spark-vllm-b12x:latest: `VLLM_MEMORY_PROFILE_INCLUDE_ATTN`, `VLLM_USE_B12X_WO_PROJECTION`, `VLLM_USE_B12X_MHC`, `VLLM_USE_B12X_FP8_GEMM`, `VLLM_USE_B12X_MOE`, `VLLM_USE_B12X_SPARSE_INDEXER`.
- **vllm-ascend** (1 flags across 1 recipes) — name is in that plugin's namespace: `VLLM_ASCEND_ENABLE_PREFETCH_MLP`.
- **Newer than v0.29.0** (2) — present in the clone but not in a stable release yet, so the recipe is ahead of its pin: `VLLM_PLE_CPU_OFFLOAD` (present at v0.30.0rc2, 1 recipe), `VLLM_ROCM_USE_AITER_MOE_SITUV2` (present at main (HEAD of the clone), 1 recipe).

21 release items were out of the capability vocabulary (new model support, packaging) and are recorded in `capabilities.yaml` rather than shown above.
