# vLLM sync report — v0.28.0 → v0.29.0

Generated 2026-09-20T10:50:59.032Z (report-only: nothing was edited or committed).

Upstream inventory: 414 items from the release-notes pass and the source pass
(default-changed 6, deprecated 11, new-feature 372, perf-improvement 18, removed 6, renamed 1).
Downstream: 122 verified findings, 0 candidates dropped in verification.

| Status | Count |
|---|---|
| needs decision | 87 |
| auto-apply-eligible | 35 |

| Category | Count |
|---|---|
| unknown-upstream | 60 |
| below-introducing-version | 46 |
| removed | 14 |
| default-changed | 1 |
| wrong-dash | 1 |

| Confidence | Count |
|---|---|
| high | 62 |
| low | 60 |

## Auto-apply eligible (35)

### F-01 — `--language-model-only` in `baidu/ERNIE-4.5-VL-28B-A3B-PT.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | below-introducing-version — flag used below the version that introduced it |
| Source | source-only |
| Downstream location | `models/baidu/ERNIE-4.5-VL-28B-A3B-PT.yaml:33` (`features.text_only.args`) |
| Upstream evidence | introduced v0.17.0; introduced in v0.17.0, present at v0.29.0 |
| Current usage | `- "--language-model-only"` |
| Proposed change | raise `model.min_vllm_version` from `0.11.0` to `0.17.0` (own commit) |
| Version floor | 0.11.0 — model.min_vllm_version |
| Confidence | high — --language-model-only was introduced in v0.17.0, above the pinned floor 0.11.0 |
| Risk | the default command is wrong at the pinned floor 0.11.0; raising the pin changes the Install block's version |
| Status | auto-apply-eligible |

### F-02 — `--language-model-only` in `deepseek-ai/DeepSeek-OCR-2.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | below-introducing-version — flag used below the version that introduced it |
| Source | source-only |
| Downstream location | `models/deepseek-ai/DeepSeek-OCR-2.yaml:35` (`features.text_only.args`) |
| Upstream evidence | introduced v0.17.0; introduced in v0.17.0, present at v0.29.0 |
| Current usage | `- "--language-model-only"` |
| Proposed change | raise `model.min_vllm_version` from `0.12.0` to `0.17.0` (own commit) |
| Version floor | 0.12.0 — model.min_vllm_version |
| Confidence | high — --language-model-only was introduced in v0.17.0, above the pinned floor 0.12.0 |
| Risk | the default command is wrong at the pinned floor 0.12.0; raising the pin changes the Install block's version |
| Status | auto-apply-eligible |

### F-03 — `--language-model-only` in `deepseek-ai/DeepSeek-OCR.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | below-introducing-version — flag used below the version that introduced it |
| Source | source-only |
| Downstream location | `models/deepseek-ai/DeepSeek-OCR.yaml:40` (`features.text_only.args`) |
| Upstream evidence | introduced v0.17.0; introduced in v0.17.0, present at v0.29.0 |
| Current usage | `- "--language-model-only"` |
| Proposed change | raise `model.min_vllm_version` from `0.12.0` to `0.17.0` (own commit) |
| Version floor | 0.12.0 — model.min_vllm_version |
| Confidence | high — --language-model-only was introduced in v0.17.0, above the pinned floor 0.12.0 |
| Risk | the default command is wrong at the pinned floor 0.12.0; raising the pin changes the Install block's version |
| Status | auto-apply-eligible |

### F-04 — `VLLM_ENGINE_READY_TIMEOUT_S` in `deepseek-ai/DeepSeek-R1.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | below-introducing-version — flag used below the version that introduced it |
| Source | source-only |
| Downstream location | `models/deepseek-ai/DeepSeek-R1.yaml:94` (`strategy_overrides.single_node_dpa_tp.extra_env.VLLM_ENGINE_READY_TIMEOUT_S`) |
| Upstream evidence | introduced v0.14.0; introduced in v0.14.0, present at v0.29.0 |
| Current usage | `VLLM_ENGINE_READY_TIMEOUT_S: "1800"` |
| Proposed change | raise `model.min_vllm_version` from `0.12.0` to `0.14.0` (own commit) |
| Version floor | 0.12.0 — model.min_vllm_version |
| Confidence | high — VLLM_ENGINE_READY_TIMEOUT_S was introduced in v0.14.0, above the pinned floor 0.12.0 |
| Risk | the default command is wrong at the pinned floor 0.12.0; raising the pin changes the Install block's version |
| Status | auto-apply-eligible |

### F-05 — `VLLM_ENGINE_READY_TIMEOUT_S` in `deepseek-ai/DeepSeek-V3.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | below-introducing-version — flag used below the version that introduced it |
| Source | source-only |
| Downstream location | `models/deepseek-ai/DeepSeek-V3.yaml:90` (`strategy_overrides.single_node_dpa_tp.extra_env.VLLM_ENGINE_READY_TIMEOUT_S`) |
| Upstream evidence | introduced v0.14.0; introduced in v0.14.0, present at v0.29.0 |
| Current usage | `VLLM_ENGINE_READY_TIMEOUT_S: "1800"` |
| Proposed change | raise `model.min_vllm_version` from `0.12.0` to `0.14.0` (own commit) |
| Version floor | 0.12.0 — model.min_vllm_version |
| Confidence | high — VLLM_ENGINE_READY_TIMEOUT_S was introduced in v0.14.0, above the pinned floor 0.12.0 |
| Risk | the default command is wrong at the pinned floor 0.12.0; raising the pin changes the Install block's version |
| Status | auto-apply-eligible |

### F-06 — `--linear-backend` in `deepseek-ai/DeepSeek-V4-Flash.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | below-introducing-version — flag used below the version that introduced it |
| Source | release-notes |
| Downstream location | `models/deepseek-ai/DeepSeek-V4-Flash.yaml:250` (`variants.fp8.hardware_overrides.dgx_spark_gb10.extra_args`), `models/deepseek-ai/DeepSeek-V4-Flash.yaml:262` (`variants.fp8.hardware_overrides.dgx_spark_gb10.extra_env.VLLM_USE_BREAKABLE_CUDAGRAPH`) |
| Upstream evidence | introduced v0.22.0; introduced in v0.22.0, present at v0.29.0 |
| Current usage | `- "--linear-backend"` |
| Proposed change | raise `variants.fp8.min_vllm_version` from `0.20.0` to `0.22.0` (own commit) |
| Version floor | 0.20.0 — model.min_vllm_version |
| Tokens | `--linear-backend` (needs v0.22.0), `VLLM_USE_BREAKABLE_CUDAGRAPH` (needs v0.22.0) |
| Confidence | high — --linear-backend was introduced in v0.22.0, above the pinned floor 0.20.0 |
| Risk | the default command is wrong at the pinned floor 0.20.0; raising the pin changes the Install block's version |
| Status | auto-apply-eligible |

### F-07 — `--linear-backend` in `deepseek-ai/DeepSeek-V4-Flash.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | below-introducing-version — flag used below the version that introduced it |
| Source | release-notes |
| Downstream location | `models/deepseek-ai/DeepSeek-V4-Flash.yaml:326` (`variants.nvfp4.hardware_overrides.dgx_spark_gb10.extra_args`), `models/deepseek-ai/DeepSeek-V4-Flash.yaml:338` (`variants.nvfp4.hardware_overrides.dgx_spark_gb10.extra_env.VLLM_USE_BREAKABLE_CUDAGRAPH`) |
| Upstream evidence | introduced v0.22.0; introduced in v0.22.0, present at v0.29.0 |
| Current usage | `- "--linear-backend"` |
| Proposed change | raise `variants.nvfp4.min_vllm_version` from `0.20.0` to `0.22.0` (own commit) |
| Version floor | 0.20.0 — model.min_vllm_version |
| Tokens | `--linear-backend` (needs v0.22.0), `VLLM_USE_BREAKABLE_CUDAGRAPH` (needs v0.22.0) |
| Confidence | high — --linear-backend was introduced in v0.22.0, above the pinned floor 0.20.0 |
| Risk | the default command is wrong at the pinned floor 0.20.0; raising the pin changes the Install block's version |
| Status | auto-apply-eligible |

### F-08 — `--linear-backend` in `deepseek-ai/DeepSeek-V4-Flash.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | below-introducing-version — flag used below the version that introduced it |
| Source | release-notes |
| Downstream location | `models/deepseek-ai/DeepSeek-V4-Flash.yaml:625` (`strategy_overrides.multi_node_tp.hardware_overrides.blackwell.extra_args`) |
| Upstream evidence | introduced v0.22.0; introduced in v0.22.0, present at v0.29.0 |
| Current usage | `- "--linear-backend"` |
| Proposed change | raise `model.min_vllm_version` from `0.20.0` to `0.22.0` (own commit) |
| Version floor | 0.20.0 — model.min_vllm_version |
| Confidence | high — --linear-backend was introduced in v0.22.0, above the pinned floor 0.20.0 |
| Risk | the default command is wrong at the pinned floor 0.20.0; raising the pin changes the Install block's version |
| Status | auto-apply-eligible |

### F-09 — `--language-model-only` in `internlm/Intern-S1.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | below-introducing-version — flag used below the version that introduced it |
| Source | source-only |
| Downstream location | `models/internlm/Intern-S1.yaml:44` (`features.text_only.args`), `models/internlm/Intern-S1.yaml:48` (`features.encoder_parallel.args`) |
| Upstream evidence | introduced v0.17.0; introduced in v0.17.0, present at v0.29.0 |
| Current usage | `- "--language-model-only"` |
| Proposed change | raise `model.min_vllm_version` from `0.10.0` to `0.17.0` (own commit) |
| Version floor | 0.10.0 — model.min_vllm_version |
| Tokens | `--language-model-only` (needs v0.17.0), `--mm-encoder-tp-mode` (needs v0.10.2) |
| Confidence | high — --language-model-only was introduced in v0.17.0, above the pinned floor 0.10.0 |
| Risk | the default command is wrong at the pinned floor 0.10.0; raising the pin changes the Install block's version |
| Status | auto-apply-eligible |

### F-10 — `VLLM_ROCM_USE_AITER` in `jinaai/jina-reranker-m0.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | below-introducing-version — flag used below the version that introduced it |
| Source | source-only |
| Downstream location | `models/jinaai/jina-reranker-m0.yaml:46` (`hardware_overrides.amd.extra_env.VLLM_ROCM_USE_AITER`) |
| Upstream evidence | introduced v0.8.2; introduced in v0.8.2, present at v0.29.0 |
| Current usage | `VLLM_ROCM_USE_AITER: "1"` |
| Proposed change | raise `model.min_vllm_version` from `0.8.0` to `0.8.2` (own commit) |
| Version floor | 0.8.0 — model.min_vllm_version |
| Confidence | high — VLLM_ROCM_USE_AITER was introduced in v0.8.2, above the pinned floor 0.8.0 |
| Risk | the default command is wrong at the pinned floor 0.8.0; raising the pin changes the Install block's version |
| Status | auto-apply-eligible |

### F-11 — `--speculative-config` in `meta-llama/Llama-3.1-8B-Instruct.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | below-introducing-version — flag used below the version that introduced it |
| Source | source-only |
| Downstream location | `models/meta-llama/Llama-3.1-8B-Instruct.yaml:38` (`features.spec_decoding.args`), `models/meta-llama/Llama-3.1-8B-Instruct.yaml:95` (`hardware_overrides.amd.extra_env.VLLM_ROCM_USE_AITER`) |
| Upstream evidence | introduced v0.8.2; introduced in v0.8.2, present at v0.29.0 |
| Current usage | `- "--speculative-config"` |
| Proposed change | raise `model.min_vllm_version` from `0.6.0` to `0.8.2` (own commit) |
| Version floor | 0.6.0 — model.min_vllm_version |
| Tokens | `--speculative-config` (needs v0.8.2), `VLLM_ROCM_USE_AITER` (needs v0.8.2) |
| Confidence | high — --speculative-config was introduced in v0.8.2, above the pinned floor 0.6.0 |
| Risk | the default command is wrong at the pinned floor 0.6.0; raising the pin changes the Install block's version |
| Status | auto-apply-eligible |

### F-12 — `--language-model-only` in `microsoft/Phi-4-mini-instruct.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | below-introducing-version — flag used below the version that introduced it |
| Source | source-only |
| Downstream location | `models/microsoft/Phi-4-mini-instruct.yaml:30` (`features.text_only.args`), `models/microsoft/Phi-4-mini-instruct.yaml:34` (`features.encoder_parallel.args`) |
| Upstream evidence | introduced v0.17.0; introduced in v0.17.0, present at v0.29.0 |
| Current usage | `- "--language-model-only"` |
| Proposed change | raise `model.min_vllm_version` from `0.7.0` to `0.17.0` (own commit) |
| Version floor | 0.7.0 — model.min_vllm_version |
| Tokens | `--language-model-only` (needs v0.17.0), `--mm-encoder-tp-mode` (needs v0.10.2) |
| Confidence | high — --language-model-only was introduced in v0.17.0, above the pinned floor 0.7.0 |
| Risk | the default command is wrong at the pinned floor 0.7.0; raising the pin changes the Install block's version |
| Status | auto-apply-eligible |

### F-13 — `--attention-backend` in `MiniMaxAI/MiniMax-M2.1.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | below-introducing-version — flag used below the version that introduced it |
| Source | source-only |
| Downstream location | `models/MiniMaxAI/MiniMax-M2.1.yaml:70` (`hardware_overrides.amd.extra_args`), `models/MiniMaxAI/MiniMax-M2.1.yaml:74` (`hardware_overrides.amd.extra_env.VLLM_ROCM_SHUFFLE_KV_CACHE_LAYOUT`) |
| Upstream evidence | introduced v0.13.0; introduced in v0.13.0, present at v0.29.0 |
| Current usage | `- "--attention-backend"` |
| Proposed change | raise `model.min_vllm_version` from `0.11.0` to `0.15.0` (own commit) |
| Version floor | 0.11.0 — model.min_vllm_version |
| Tokens | `--attention-backend` (needs v0.13.0), `VLLM_ROCM_SHUFFLE_KV_CACHE_LAYOUT` (needs v0.15.0) |
| Confidence | high — --attention-backend was introduced in v0.13.0, above the pinned floor 0.11.0 |
| Risk | the default command is wrong at the pinned floor 0.11.0; raising the pin changes the Install block's version |
| Status | auto-apply-eligible |

### F-14 — `--attention-backend` in `MiniMaxAI/MiniMax-M2.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | below-introducing-version — flag used below the version that introduced it |
| Source | source-only |
| Downstream location | `models/MiniMaxAI/MiniMax-M2.yaml:86` (`hardware_overrides.amd.extra_args`), `models/MiniMaxAI/MiniMax-M2.yaml:90` (`hardware_overrides.amd.extra_env.VLLM_ROCM_SHUFFLE_KV_CACHE_LAYOUT`) |
| Upstream evidence | introduced v0.13.0; introduced in v0.13.0, present at v0.29.0 |
| Current usage | `- "--attention-backend"` |
| Proposed change | raise `model.min_vllm_version` from `0.11.0` to `0.15.0` (own commit) |
| Version floor | 0.11.0 — model.min_vllm_version |
| Tokens | `--attention-backend` (needs v0.13.0), `VLLM_ROCM_SHUFFLE_KV_CACHE_LAYOUT` (needs v0.15.0) |
| Confidence | high — --attention-backend was introduced in v0.13.0, above the pinned floor 0.11.0 |
| Risk | the default command is wrong at the pinned floor 0.11.0; raising the pin changes the Install block's version |
| Status | auto-apply-eligible |

### F-15 — `--language-model-only` in `mistralai/Ministral-3-14B-Instruct-2512.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | below-introducing-version — flag used below the version that introduced it |
| Source | source-only |
| Downstream location | `models/mistralai/Ministral-3-14B-Instruct-2512.yaml:46` (`features.text_only.args`) |
| Upstream evidence | introduced v0.17.0; introduced in v0.17.0, present at v0.29.0 |
| Current usage | `- "--language-model-only"` |
| Proposed change | raise `model.min_vllm_version` from `0.11.0` to `0.17.0` (own commit) |
| Version floor | 0.11.0 — model.min_vllm_version |
| Confidence | high — --language-model-only was introduced in v0.17.0, above the pinned floor 0.11.0 |
| Risk | the default command is wrong at the pinned floor 0.11.0; raising the pin changes the Install block's version |
| Status | auto-apply-eligible |

### F-16 — `--language-model-only` in `mistralai/Ministral-3-8B-Reasoning-2512.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | below-introducing-version — flag used below the version that introduced it |
| Source | source-only |
| Downstream location | `models/mistralai/Ministral-3-8B-Reasoning-2512.yaml:50` (`features.text_only.args`) |
| Upstream evidence | introduced v0.17.0; introduced in v0.17.0, present at v0.29.0 |
| Current usage | `- "--language-model-only"` |
| Proposed change | raise `model.min_vllm_version` from `0.11.0` to `0.17.0` (own commit) |
| Version floor | 0.11.0 — model.min_vllm_version |
| Confidence | high — --language-model-only was introduced in v0.17.0, above the pinned floor 0.11.0 |
| Risk | the default command is wrong at the pinned floor 0.11.0; raising the pin changes the Install block's version |
| Status | auto-apply-eligible |

### F-17 — `--language-model-only` in `mistralai/Mistral-Large-3-675B-Instruct-2512.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | below-introducing-version — flag used below the version that introduced it |
| Source | source-only |
| Downstream location | `models/mistralai/Mistral-Large-3-675B-Instruct-2512.yaml:43` (`features.text_only.args`) |
| Upstream evidence | introduced v0.17.0; introduced in v0.17.0, present at v0.29.0 |
| Current usage | `- "--language-model-only"` |
| Proposed change | raise `model.min_vllm_version` from `0.11.0` to `0.17.0` (own commit) |
| Version floor | 0.11.0 — model.min_vllm_version |
| Confidence | high — --language-model-only was introduced in v0.17.0, above the pinned floor 0.11.0 |
| Risk | the default command is wrong at the pinned floor 0.11.0; raising the pin changes the Install block's version |
| Status | auto-apply-eligible |

### F-18 — `--language-model-only` in `nvidia/NVIDIA-Nemotron-Nano-12B-v2-VL-BF16.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | below-introducing-version — flag used below the version that introduced it |
| Source | source-only |
| Downstream location | `models/nvidia/NVIDIA-Nemotron-Nano-12B-v2-VL-BF16.yaml:38` (`features.text_only.args`) |
| Upstream evidence | introduced v0.17.0; introduced in v0.17.0, present at v0.29.0 |
| Current usage | `- "--language-model-only"` |
| Proposed change | raise `model.min_vllm_version` from `0.11.1` to `0.17.0` (own commit) |
| Version floor | 0.11.1 — model.min_vllm_version |
| Confidence | high — --language-model-only was introduced in v0.17.0, above the pinned floor 0.11.1 |
| Risk | the default command is wrong at the pinned floor 0.11.1; raising the pin changes the Install block's version |
| Status | auto-apply-eligible |

### F-19 — `--quantization-config.moe.activation` in `openai/gpt-oss-120b.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | below-introducing-version — flag used below the version that introduced it |
| Source | source-only |
| Downstream location | `models/openai/gpt-oss-120b.yaml:72` (`hardware_overrides.blackwell.extra_args`), `models/openai/gpt-oss-120b.yaml:79` (`hardware_overrides.amd.extra_args`) |
| Upstream evidence | introduced v0.20.0; introduced in v0.20.0, present at v0.29.0 |
| Current usage | `- "--quantization-config.moe.activation"` |
| Proposed change | raise `model.min_vllm_version` from `0.10.0` to `0.20.0` (own commit) |
| Version floor | 0.10.0 — model.min_vllm_version |
| Tokens | `--quantization-config.moe.activation` (needs v0.20.0), `--attention-backend` (needs v0.13.0) |
| Confidence | high — --quantization-config.moe.activation was introduced in v0.20.0, above the pinned floor 0.10.0 |
| Risk | the default command is wrong at the pinned floor 0.10.0; raising the pin changes the Install block's version |
| Status | auto-apply-eligible |

### F-20 — `--attention-backend` in `openai/gpt-oss-20b.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | below-introducing-version — flag used below the version that introduced it |
| Source | source-only |
| Downstream location | `models/openai/gpt-oss-20b.yaml:63` (`hardware_overrides.amd.extra_args`) |
| Upstream evidence | introduced v0.13.0; introduced in v0.13.0, present at v0.29.0 |
| Current usage | `- "--attention-backend"` |
| Proposed change | raise `model.min_vllm_version` from `0.10.0` to `0.13.0` (own commit) |
| Version floor | 0.10.0 — model.min_vllm_version |
| Confidence | high — --attention-backend was introduced in v0.13.0, above the pinned floor 0.10.0 |
| Risk | the default command is wrong at the pinned floor 0.10.0; raising the pin changes the Install block's version |
| Status | auto-apply-eligible |

### F-21 — `--language-model-only` in `OpenGVLab/InternVL3_5-8B.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | below-introducing-version — flag used below the version that introduced it |
| Source | source-only |
| Downstream location | `models/OpenGVLab/InternVL3_5-8B.yaml:34` (`features.text_only.args`), `models/OpenGVLab/InternVL3_5-8B.yaml:38` (`features.encoder_parallel.args`) |
| Upstream evidence | introduced v0.17.0; introduced in v0.17.0, present at v0.29.0 |
| Current usage | `- "--language-model-only"` |
| Proposed change | raise `model.min_vllm_version` from `0.10.0` to `0.17.0` (own commit) |
| Version floor | 0.10.0 — model.min_vllm_version |
| Tokens | `--language-model-only` (needs v0.17.0), `--mm-encoder-tp-mode` (needs v0.10.2) |
| Confidence | high — --language-model-only was introduced in v0.17.0, above the pinned floor 0.10.0 |
| Risk | the default command is wrong at the pinned floor 0.10.0; raising the pin changes the Install block's version |
| Status | auto-apply-eligible |

### F-22 — `--language-model-only` in `PaddlePaddle/PaddleOCR-VL-1.5.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | below-introducing-version — flag used below the version that introduced it |
| Source | source-only |
| Downstream location | `models/PaddlePaddle/PaddleOCR-VL-1.5.yaml:42` (`features.text_only.args`) |
| Upstream evidence | introduced v0.17.0; introduced in v0.17.0, present at v0.29.0 |
| Current usage | `- "--language-model-only"` |
| Proposed change | raise `model.min_vllm_version` from `0.11.1` to `0.17.0` (own commit) |
| Version floor | 0.11.1 — model.min_vllm_version |
| Confidence | high — --language-model-only was introduced in v0.17.0, above the pinned floor 0.11.1 |
| Risk | the default command is wrong at the pinned floor 0.11.1; raising the pin changes the Install block's version |
| Status | auto-apply-eligible |

### F-23 — `--language-model-only` in `PaddlePaddle/PaddleOCR-VL-1.6.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | below-introducing-version — flag used below the version that introduced it |
| Source | source-only |
| Downstream location | `models/PaddlePaddle/PaddleOCR-VL-1.6.yaml:44` (`features.text_only.args`) |
| Upstream evidence | introduced v0.17.0; introduced in v0.17.0, present at v0.29.0 |
| Current usage | `- "--language-model-only"` |
| Proposed change | raise `model.min_vllm_version` from `0.11.1` to `0.17.0` (own commit) |
| Version floor | 0.11.1 — model.min_vllm_version |
| Confidence | high — --language-model-only was introduced in v0.17.0, above the pinned floor 0.11.1 |
| Risk | the default command is wrong at the pinned floor 0.11.1; raising the pin changes the Install block's version |
| Status | auto-apply-eligible |

### F-24 — `--language-model-only` in `PaddlePaddle/PaddleOCR-VL.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | below-introducing-version — flag used below the version that introduced it |
| Source | source-only |
| Downstream location | `models/PaddlePaddle/PaddleOCR-VL.yaml:41` (`features.text_only.args`) |
| Upstream evidence | introduced v0.17.0; introduced in v0.17.0, present at v0.29.0 |
| Current usage | `- "--language-model-only"` |
| Proposed change | raise `model.min_vllm_version` from `0.11.1` to `0.17.0` (own commit) |
| Version floor | 0.11.1 — model.min_vllm_version |
| Confidence | high — --language-model-only was introduced in v0.17.0, above the pinned floor 0.11.1 |
| Risk | the default command is wrong at the pinned floor 0.11.1; raising the pin changes the Install block's version |
| Status | auto-apply-eligible |

### F-25 — `--language-model-only` in `Qwen/Qwen2.5-VL-72B-Instruct.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | below-introducing-version — flag used below the version that introduced it |
| Source | source-only |
| Downstream location | `models/Qwen/Qwen2.5-VL-72B-Instruct.yaml:34` (`features.text_only.args`), `models/Qwen/Qwen2.5-VL-72B-Instruct.yaml:38` (`features.encoder_parallel.args`), `models/Qwen/Qwen2.5-VL-72B-Instruct.yaml:70` (`hardware_overrides.hopper.extra_args`), `models/Qwen/Qwen2.5-VL-72B-Instruct.yaml:75` (`hardware_overrides.blackwell.extra_args`), `models/Qwen/Qwen2.5-VL-72B-Instruct.yaml:81` (`hardware_overrides.amd.extra_args`), `models/Qwen/Qwen2.5-VL-72B-Instruct.yaml:86` (`hardware_overrides.amd.extra_env.VLLM_ROCM_USE_AITER`) |
| Upstream evidence | introduced v0.17.0; introduced in v0.17.0, present at v0.29.0 |
| Current usage | `- "--language-model-only"` |
| Proposed change | raise `model.min_vllm_version` from `0.7.0` to `0.17.0` (own commit) |
| Version floor | 0.7.0 — model.min_vllm_version |
| Tokens | `--language-model-only` (needs v0.17.0), `--mm-encoder-tp-mode` (needs v0.10.2), `VLLM_ROCM_USE_AITER` (needs v0.8.2) |
| Confidence | high — --language-model-only was introduced in v0.17.0, above the pinned floor 0.7.0 |
| Risk | the default command is wrong at the pinned floor 0.7.0; raising the pin changes the Install block's version |
| Status | auto-apply-eligible |

### F-26 — `--language-model-only` in `Qwen/Qwen2.5-VL-7B-Instruct.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | below-introducing-version — flag used below the version that introduced it |
| Source | source-only |
| Downstream location | `models/Qwen/Qwen2.5-VL-7B-Instruct.yaml:33` (`features.text_only.args`), `models/Qwen/Qwen2.5-VL-7B-Instruct.yaml:37` (`features.encoder_parallel.args`) |
| Upstream evidence | introduced v0.17.0; introduced in v0.17.0, present at v0.29.0 |
| Current usage | `- "--language-model-only"` |
| Proposed change | raise `model.min_vllm_version` from `0.7.0` to `0.17.0` (own commit) |
| Version floor | 0.7.0 — model.min_vllm_version |
| Tokens | `--language-model-only` (needs v0.17.0), `--mm-encoder-tp-mode` (needs v0.10.2) |
| Confidence | high — --language-model-only was introduced in v0.17.0, above the pinned floor 0.7.0 |
| Risk | the default command is wrong at the pinned floor 0.7.0; raising the pin changes the Install block's version |
| Status | auto-apply-eligible |

### F-27 — `--language-model-only` in `Qwen/Qwen3-VL-235B-A22B-Instruct.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | below-introducing-version — flag used below the version that introduced it |
| Source | source-only |
| Downstream location | `models/Qwen/Qwen3-VL-235B-A22B-Instruct.yaml:44` (`features.text_only.args`), `models/Qwen/Qwen3-VL-235B-A22B-Instruct.yaml:113` (`hardware_overrides.amd.extra_env.VLLM_ROCM_SHUFFLE_KV_CACHE_LAYOUT`) |
| Upstream evidence | introduced v0.17.0; introduced in v0.17.0, present at v0.29.0 |
| Current usage | `- "--language-model-only"` |
| Proposed change | raise `model.min_vllm_version` from `0.11.0` to `0.17.0` (own commit) |
| Version floor | 0.11.0 — model.min_vllm_version |
| Tokens | `--language-model-only` (needs v0.17.0), `VLLM_ROCM_SHUFFLE_KV_CACHE_LAYOUT` (needs v0.15.0) |
| Confidence | high — --language-model-only was introduced in v0.17.0, above the pinned floor 0.11.0 |
| Risk | the default command is wrong at the pinned floor 0.11.0; raising the pin changes the Install block's version |
| Status | auto-apply-eligible |

### F-28 — `--language-model-only` in `Qwen/Qwen3-VL-30B-A3B-Instruct.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | below-introducing-version — flag used below the version that introduced it |
| Source | source-only |
| Downstream location | `models/Qwen/Qwen3-VL-30B-A3B-Instruct.yaml:37` (`features.text_only.args`) |
| Upstream evidence | introduced v0.17.0; introduced in v0.17.0, present at v0.29.0 |
| Current usage | `- "--language-model-only"` |
| Proposed change | raise `model.min_vllm_version` from `0.11.0` to `0.17.0` (own commit) |
| Version floor | 0.11.0 — model.min_vllm_version |
| Confidence | high — --language-model-only was introduced in v0.17.0, above the pinned floor 0.11.0 |
| Risk | the default command is wrong at the pinned floor 0.11.0; raising the pin changes the Install block's version |
| Status | auto-apply-eligible |

### F-29 — `VLLM_SSM_CONV_STATE_LAYOUT` in `Qwen/Qwen3.5-122B-A10B.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | below-introducing-version — flag used below the version that introduced it |
| Source | source-only |
| Downstream location | `models/Qwen/Qwen3.5-122B-A10B.yaml:138` (`strategy_overrides.pd_cluster.prefill.env.VLLM_SSM_CONV_STATE_LAYOUT`), `models/Qwen/Qwen3.5-122B-A10B.yaml:141` (`strategy_overrides.pd_cluster.decode.env.VLLM_SSM_CONV_STATE_LAYOUT`) |
| Upstream evidence | introduced v0.20.0; introduced in v0.20.0, present at v0.29.0 |
| Current usage | `VLLM_SSM_CONV_STATE_LAYOUT: "DS"` |
| Proposed change | raise `model.min_vllm_version` from `0.17.0` to `0.20.0` (own commit) |
| Version floor | 0.17.0 — model.min_vllm_version |
| Confidence | high — VLLM_SSM_CONV_STATE_LAYOUT was introduced in v0.20.0, above the pinned floor 0.17.0 |
| Risk | the default command is wrong at the pinned floor 0.17.0; raising the pin changes the Install block's version |
| Status | auto-apply-eligible |

### F-30 — `VLLM_SSM_CONV_STATE_LAYOUT` in `Qwen/Qwen3.5-397B-A17B.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | below-introducing-version — flag used below the version that introduced it |
| Source | source-only |
| Downstream location | `models/Qwen/Qwen3.5-397B-A17B.yaml:240` (`strategy_overrides.pd_cluster.prefill.env.VLLM_SSM_CONV_STATE_LAYOUT`), `models/Qwen/Qwen3.5-397B-A17B.yaml:243` (`strategy_overrides.pd_cluster.decode.env.VLLM_SSM_CONV_STATE_LAYOUT`) |
| Upstream evidence | introduced v0.20.0; introduced in v0.20.0, present at v0.29.0 |
| Current usage | `VLLM_SSM_CONV_STATE_LAYOUT: "DS"` |
| Proposed change | raise `model.min_vllm_version` from `0.17.0` to `0.20.0` (own commit) |
| Version floor | 0.17.0 — model.min_vllm_version |
| Confidence | high — VLLM_SSM_CONV_STATE_LAYOUT was introduced in v0.20.0, above the pinned floor 0.17.0 |
| Risk | the default command is wrong at the pinned floor 0.17.0; raising the pin changes the Install block's version |
| Status | auto-apply-eligible |

### F-31 — `--language-model-only` in `tencent/HunyuanOCR.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | below-introducing-version — flag used below the version that introduced it |
| Source | source-only |
| Downstream location | `models/tencent/HunyuanOCR.yaml:31` (`features.text_only.args`) |
| Upstream evidence | introduced v0.17.0; introduced in v0.17.0, present at v0.29.0 |
| Current usage | `- "--language-model-only"` |
| Proposed change | raise `model.min_vllm_version` from `0.11.0` to `0.17.0` (own commit) |
| Version floor | 0.11.0 — model.min_vllm_version |
| Confidence | high — --language-model-only was introduced in v0.17.0, above the pinned floor 0.11.0 |
| Risk | the default command is wrong at the pinned floor 0.11.0; raising the pin changes the Install block's version |
| Status | auto-apply-eligible |

### F-32 — `--language-model-only` in `zai-org/GLM-4.5V.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | below-introducing-version — flag used below the version that introduced it |
| Source | source-only |
| Downstream location | `models/zai-org/GLM-4.5V.yaml:57` (`features.text_only.args`) |
| Upstream evidence | introduced v0.17.0; introduced in v0.17.0, present at v0.29.0 |
| Current usage | `- "--language-model-only"` |
| Proposed change | raise `model.min_vllm_version` from `0.12.0` to `0.17.0` (own commit) |
| Version floor | 0.12.0 — model.min_vllm_version |
| Confidence | high — --language-model-only was introduced in v0.17.0, above the pinned floor 0.12.0 |
| Risk | the default command is wrong at the pinned floor 0.12.0; raising the pin changes the Install block's version |
| Status | auto-apply-eligible |

### F-33 — `--language-model-only` in `zai-org/GLM-4.6V.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | below-introducing-version — flag used below the version that introduced it |
| Source | source-only |
| Downstream location | `models/zai-org/GLM-4.6V.yaml:57` (`features.text_only.args`) |
| Upstream evidence | introduced v0.17.0; introduced in v0.17.0, present at v0.29.0 |
| Current usage | `- "--language-model-only"` |
| Proposed change | raise `model.min_vllm_version` from `0.12.0` to `0.17.0` (own commit) |
| Version floor | 0.12.0 — model.min_vllm_version |
| Confidence | high — --language-model-only was introduced in v0.17.0, above the pinned floor 0.12.0 |
| Risk | the default command is wrong at the pinned floor 0.12.0; raising the pin changes the Install block's version |
| Status | auto-apply-eligible |

### F-34 — `--language-model-only` in `zai-org/GLM-OCR.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | below-introducing-version — flag used below the version that introduced it |
| Source | source-only |
| Downstream location | `models/zai-org/GLM-OCR.yaml:41` (`features.text_only.args`) |
| Upstream evidence | introduced v0.17.0; introduced in v0.17.0, present at v0.29.0 |
| Current usage | `- "--language-model-only"` |
| Proposed change | raise `model.min_vllm_version` from `0.12.0` to `0.17.0` (own commit) |
| Version floor | 0.12.0 — model.min_vllm_version |
| Confidence | high — --language-model-only was introduced in v0.17.0, above the pinned floor 0.12.0 |
| Risk | the default command is wrong at the pinned floor 0.12.0; raising the pin changes the Install block's version |
| Status | auto-apply-eligible |

### F-35 — `--language-model-only` in `zai-org/Glyph.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | below-introducing-version — flag used below the version that introduced it |
| Source | source-only |
| Downstream location | `models/zai-org/Glyph.yaml:42` (`features.text_only.args`) |
| Upstream evidence | introduced v0.17.0; introduced in v0.17.0, present at v0.29.0 |
| Current usage | `- "--language-model-only"` |
| Proposed change | raise `model.min_vllm_version` from `0.11.0` to `0.17.0` (own commit) |
| Version floor | 0.11.0 — model.min_vllm_version |
| Confidence | high — --language-model-only was introduced in v0.17.0, above the pinned floor 0.11.0 |
| Risk | the default command is wrong at the pinned floor 0.11.0; raising the pin changes the Install block's version |
| Status | auto-apply-eligible |


## Needs decision (87)

### F-36 — `--disable-log-requests` in `baidu/ERNIE-4.5-VL-28B-A3B-PT.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | removed — removed upstream |
| Source | source-only |
| Downstream location | `models/baidu/ERNIE-4.5-VL-28B-A3B-PT.yaml:148` (`guide`) — guide text |
| Upstream evidence | introduced v0.4.2; removed v0.17.0; absent from the flag set at v0.29.0; last present before v0.17.0 |
| Current usage | `--disable-log-requests \` |
| Proposed change | decide whether to drop `--disable-log-requests` or re-spell it; upstream documents no replacement |
| Version floor | 0.11.0 — model.min_vllm_version |
| Confidence | high — removed upstream in v0.17.0 (introduced v0.4.2) |
| Risk | --disable-log-requests is gone at v0.29.0, but upstream documents no replacement — deleting it and re-spelling it are different edits |
| Status | needs decision |

### F-37 — `--omni` in `bosonai/higgs-audio-v3-tts-4b.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/bosonai/higgs-audio-v3-tts-4b.yaml:24` (`model.base_args`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `- "--omni"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.22.0 — model.min_vllm_version |
| Confidence | low — --omni is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-38 — `VLLM_ENGINE_READY_TIMEOUT_S` in `deepseek-ai/DeepSeek-R1.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | below-introducing-version — flag used below the version that introduced it |
| Source | source-only |
| Downstream location | `models/deepseek-ai/DeepSeek-R1.yaml:166` (`guide`) — guide text, `models/deepseek-ai/DeepSeek-R1.yaml:204` (`guide`) — guide text |
| Upstream evidence | introduced v0.14.0; introduced in v0.14.0, present at v0.29.0 |
| Current usage | `export VLLM_ENGINE_READY_TIMEOUT_S=1800` |
| Proposed change | update the guide text (it shows flags needing 0.17.0, the recipe pins 0.12.0) |
| Version floor | 0.12.0 — model.min_vllm_version |
| Tokens | `VLLM_ENGINE_READY_TIMEOUT_S` (needs v0.14.0), `--moe-backend` (needs v0.17.0) |
| Confidence | high — VLLM_ENGINE_READY_TIMEOUT_S was introduced in v0.14.0, above the pinned floor 0.12.0 |
| Risk | the guide shows flags newer than the pinned floor 0.12.0; the guide text is what needs updating, not necessarily the pin |
| Status | needs decision |

### F-39 — `VLLM_ENGINE_READY_TIMEOUT_S` in `deepseek-ai/DeepSeek-V3.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | below-introducing-version — flag used below the version that introduced it |
| Source | source-only |
| Downstream location | `models/deepseek-ai/DeepSeek-V3.yaml:163` (`guide`) — guide text, `models/deepseek-ai/DeepSeek-V3.yaml:201` (`guide`) — guide text |
| Upstream evidence | introduced v0.14.0; introduced in v0.14.0, present at v0.29.0 |
| Current usage | `export VLLM_ENGINE_READY_TIMEOUT_S=1800` |
| Proposed change | update the guide text (it shows flags needing 0.17.0, the recipe pins 0.12.0) |
| Version floor | 0.12.0 — model.min_vllm_version |
| Tokens | `VLLM_ENGINE_READY_TIMEOUT_S` (needs v0.14.0), `--moe-backend` (needs v0.17.0) |
| Confidence | high — VLLM_ENGINE_READY_TIMEOUT_S was introduced in v0.14.0, above the pinned floor 0.12.0 |
| Risk | the guide shows flags newer than the pinned floor 0.12.0; the guide text is what needs updating, not necessarily the pin |
| Status | needs decision |

### F-40 — `VLLM_MEMORY_PROFILE_INCLUDE_ATTN` in `deepseek-ai/DeepSeek-V4-Flash.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/deepseek-ai/DeepSeek-V4-Flash.yaml:194` (`variants.default.hardware_overrides.dgx_spark_gb10.extra_env.VLLM_MEMORY_PROFILE_INCLUDE_ATTN`), `models/deepseek-ai/DeepSeek-V4-Flash.yaml:264` (`variants.fp8.hardware_overrides.dgx_spark_gb10.extra_env.VLLM_MEMORY_PROFILE_INCLUDE_ATTN`), `models/deepseek-ai/DeepSeek-V4-Flash.yaml:340` (`variants.nvfp4.hardware_overrides.dgx_spark_gb10.extra_env.VLLM_MEMORY_PROFILE_INCLUDE_ATTN`), `models/deepseek-ai/DeepSeek-V4-Flash.yaml:411` (`variants.dspark.hardware_overrides.dgx_spark_gb10.extra_env.VLLM_MEMORY_PROFILE_INCLUDE_ATTN`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `VLLM_MEMORY_PROFILE_INCLUDE_ATTN: "1"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.25.0 — variant default pin |
| Confidence | low — VLLM_MEMORY_PROFILE_INCLUDE_ATTN is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-41 — `VLLM_USE_B12X_WO_PROJECTION` in `deepseek-ai/DeepSeek-V4-Flash.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/deepseek-ai/DeepSeek-V4-Flash.yaml:196` (`variants.default.hardware_overrides.dgx_spark_gb10.extra_env.VLLM_USE_B12X_WO_PROJECTION`), `models/deepseek-ai/DeepSeek-V4-Flash.yaml:266` (`variants.fp8.hardware_overrides.dgx_spark_gb10.extra_env.VLLM_USE_B12X_WO_PROJECTION`), `models/deepseek-ai/DeepSeek-V4-Flash.yaml:342` (`variants.nvfp4.hardware_overrides.dgx_spark_gb10.extra_env.VLLM_USE_B12X_WO_PROJECTION`), `models/deepseek-ai/DeepSeek-V4-Flash.yaml:413` (`variants.dspark.hardware_overrides.dgx_spark_gb10.extra_env.VLLM_USE_B12X_WO_PROJECTION`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `VLLM_USE_B12X_WO_PROJECTION: "1"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.25.0 — variant default pin |
| Confidence | low — VLLM_USE_B12X_WO_PROJECTION is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-42 — `VLLM_USE_B12X_MHC` in `deepseek-ai/DeepSeek-V4-Flash.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/deepseek-ai/DeepSeek-V4-Flash.yaml:197` (`variants.default.hardware_overrides.dgx_spark_gb10.extra_env.VLLM_USE_B12X_MHC`), `models/deepseek-ai/DeepSeek-V4-Flash.yaml:267` (`variants.fp8.hardware_overrides.dgx_spark_gb10.extra_env.VLLM_USE_B12X_MHC`), `models/deepseek-ai/DeepSeek-V4-Flash.yaml:343` (`variants.nvfp4.hardware_overrides.dgx_spark_gb10.extra_env.VLLM_USE_B12X_MHC`), `models/deepseek-ai/DeepSeek-V4-Flash.yaml:414` (`variants.dspark.hardware_overrides.dgx_spark_gb10.extra_env.VLLM_USE_B12X_MHC`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `VLLM_USE_B12X_MHC: "1"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.25.0 — variant default pin |
| Confidence | low — VLLM_USE_B12X_MHC is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-43 — `VLLM_USE_B12X_FP8_GEMM` in `deepseek-ai/DeepSeek-V4-Flash.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/deepseek-ai/DeepSeek-V4-Flash.yaml:198` (`variants.default.hardware_overrides.dgx_spark_gb10.extra_env.VLLM_USE_B12X_FP8_GEMM`), `models/deepseek-ai/DeepSeek-V4-Flash.yaml:268` (`variants.fp8.hardware_overrides.dgx_spark_gb10.extra_env.VLLM_USE_B12X_FP8_GEMM`), `models/deepseek-ai/DeepSeek-V4-Flash.yaml:344` (`variants.nvfp4.hardware_overrides.dgx_spark_gb10.extra_env.VLLM_USE_B12X_FP8_GEMM`), `models/deepseek-ai/DeepSeek-V4-Flash.yaml:415` (`variants.dspark.hardware_overrides.dgx_spark_gb10.extra_env.VLLM_USE_B12X_FP8_GEMM`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `VLLM_USE_B12X_FP8_GEMM: "1"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.25.0 — variant default pin |
| Confidence | low — VLLM_USE_B12X_FP8_GEMM is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-44 — `VLLM_USE_B12X_MOE` in `deepseek-ai/DeepSeek-V4-Flash.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/deepseek-ai/DeepSeek-V4-Flash.yaml:199` (`variants.default.hardware_overrides.dgx_spark_gb10.extra_env.VLLM_USE_B12X_MOE`), `models/deepseek-ai/DeepSeek-V4-Flash.yaml:269` (`variants.fp8.hardware_overrides.dgx_spark_gb10.extra_env.VLLM_USE_B12X_MOE`), `models/deepseek-ai/DeepSeek-V4-Flash.yaml:345` (`variants.nvfp4.hardware_overrides.dgx_spark_gb10.extra_env.VLLM_USE_B12X_MOE`), `models/deepseek-ai/DeepSeek-V4-Flash.yaml:416` (`variants.dspark.hardware_overrides.dgx_spark_gb10.extra_env.VLLM_USE_B12X_MOE`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `VLLM_USE_B12X_MOE: "1"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.25.0 — variant default pin |
| Confidence | low — VLLM_USE_B12X_MOE is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-45 — `VLLM_USE_B12X_SPARSE_INDEXER` in `deepseek-ai/DeepSeek-V4-Flash.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/deepseek-ai/DeepSeek-V4-Flash.yaml:200` (`variants.default.hardware_overrides.dgx_spark_gb10.extra_env.VLLM_USE_B12X_SPARSE_INDEXER`), `models/deepseek-ai/DeepSeek-V4-Flash.yaml:270` (`variants.fp8.hardware_overrides.dgx_spark_gb10.extra_env.VLLM_USE_B12X_SPARSE_INDEXER`), `models/deepseek-ai/DeepSeek-V4-Flash.yaml:346` (`variants.nvfp4.hardware_overrides.dgx_spark_gb10.extra_env.VLLM_USE_B12X_SPARSE_INDEXER`), `models/deepseek-ai/DeepSeek-V4-Flash.yaml:417` (`variants.dspark.hardware_overrides.dgx_spark_gb10.extra_env.VLLM_USE_B12X_SPARSE_INDEXER`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `VLLM_USE_B12X_SPARSE_INDEXER: "1"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.25.0 — variant default pin |
| Confidence | low — VLLM_USE_B12X_SPARSE_INDEXER is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-46 — `--prefill-schedule-interval` in `deepseek-ai/DeepSeek-V4-Pro.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | below-introducing-version — flag used below the version that introduced it |
| Source | source-only |
| Downstream location | `models/deepseek-ai/DeepSeek-V4-Pro.yaml:499` (`guide`) — guide text, `models/deepseek-ai/DeepSeek-V4-Pro.yaml:517` (`guide`) — guide text |
| Upstream evidence | introduced v0.24.0; introduced in v0.24.0, present at v0.29.0 |
| Current usage | `- Add `--prefill-schedule-interval 8` and `--long-prefill-token-threshold 16384`.` |
| Proposed change | update the guide text (it shows flags needing 0.24.0, the recipe pins 0.20.0) |
| Version floor | 0.20.0 — model.min_vllm_version |
| Tokens | `--prefill-schedule-interval` (needs v0.24.0), `VLLM_PREFIX_CACHE_RETENTION_INTERVAL` (needs v0.23.0) |
| Confidence | high — --prefill-schedule-interval was introduced in v0.24.0, above the pinned floor 0.20.0 |
| Risk | the guide shows flags newer than the pinned floor 0.20.0; the guide text is what needs updating, not necessarily the pin |
| Status | needs decision |

### F-47 — `--omni` in `fishaudio/s2-pro.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/fishaudio/s2-pro.yaml:24` (`model.base_args`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `- "--omni"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.19.0 — model.min_vllm_version |
| Confidence | low — --omni is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-48 — `--omni` in `inclusionAI/Ming-omni-tts-0.5B.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/inclusionAI/Ming-omni-tts-0.5B.yaml:24` (`model.base_args`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `- "--omni"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.22.0 — model.min_vllm_version |
| Confidence | low — --omni is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-49 — `VLLM_ROCM_USE_AITER` in `jinaai/jina-reranker-m0.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | below-introducing-version — flag used below the version that introduced it |
| Source | source-only |
| Downstream location | `models/jinaai/jina-reranker-m0.yaml:90` (`guide`) — guide text |
| Upstream evidence | introduced v0.8.2; introduced in v0.8.2, present at v0.29.0 |
| Current usage | `export VLLM_ROCM_USE_AITER=1` |
| Proposed change | update the guide text (it shows flags needing 0.8.2, the recipe pins 0.8.0) |
| Version floor | 0.8.0 — model.min_vllm_version |
| Confidence | high — VLLM_ROCM_USE_AITER was introduced in v0.8.2, above the pinned floor 0.8.0 |
| Risk | the guide shows flags newer than the pinned floor 0.8.0; the guide text is what needs updating, not necessarily the pin |
| Status | needs decision |

### F-50 — `--diffusion-attention-backend` in `Lightricks/LTX-2.5-Diffusers.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/Lightricks/LTX-2.5-Diffusers.yaml:57` (`variants.default.hardware_overrides.b200.extra_args`), `models/Lightricks/LTX-2.5-Diffusers.yaml:61` (`variants.default.hardware_overrides.gb200.extra_args`), `models/Lightricks/LTX-2.5-Diffusers.yaml:65` (`variants.default.hardware_overrides.b300.extra_args`), `models/Lightricks/LTX-2.5-Diffusers.yaml:69` (`variants.default.hardware_overrides.gb300.extra_args`), `models/Lightricks/LTX-2.5-Diffusers.yaml:94` (`variants.fp8.hardware_overrides.b200.extra_args`), `models/Lightricks/LTX-2.5-Diffusers.yaml:98` (`variants.fp8.hardware_overrides.gb200.extra_args`), `models/Lightricks/LTX-2.5-Diffusers.yaml:102` (`variants.fp8.hardware_overrides.b300.extra_args`), `models/Lightricks/LTX-2.5-Diffusers.yaml:106` (`variants.fp8.hardware_overrides.gb300.extra_args`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `- "--diffusion-attention-backend"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.27.0 — model.min_vllm_version |
| Confidence | low — --diffusion-attention-backend is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-51 — `--model-class-name` in `Lightricks/LTX-2.5-Diffusers.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/Lightricks/LTX-2.5-Diffusers.yaml:155` (`omni.tasks.extra_args`), `models/Lightricks/LTX-2.5-Diffusers.yaml:174` (`omni.tasks.extra_args`), `models/Lightricks/LTX-2.5-Diffusers.yaml:196` (`omni.tasks.extra_args`), `models/Lightricks/LTX-2.5-Diffusers.yaml:215` (`omni.tasks.extra_args`), `models/Lightricks/LTX-2.5-Diffusers.yaml:237` (`omni.tasks.extra_args`), `models/Lightricks/LTX-2.5-Diffusers.yaml:256` (`omni.tasks.extra_args`), `models/Lightricks/LTX-2.5-Diffusers.yaml:278` (`omni.tasks.extra_args`), `models/Lightricks/LTX-2.5-Diffusers.yaml:297` (`omni.tasks.extra_args`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `- "--model-class-name"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.27.0 — model.min_vllm_version |
| Confidence | low — --model-class-name is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-52 — `VLLM_ROCM_USE_AITER` in `meta-llama/Llama-3.1-8B-Instruct.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | below-introducing-version — flag used below the version that introduced it |
| Source | source-only |
| Downstream location | `models/meta-llama/Llama-3.1-8B-Instruct.yaml:140` (`guide`) — guide text, `models/meta-llama/Llama-3.1-8B-Instruct.yaml:229` (`guide`) — guide text, `models/meta-llama/Llama-3.1-8B-Instruct.yaml:233` (`guide`) — guide text |
| Upstream evidence | introduced v0.8.2; introduced in v0.8.2, present at v0.29.0 |
| Current usage | `export VLLM_ROCM_USE_AITER=1` |
| Proposed change | update the guide text (it shows flags needing 0.8.2, the recipe pins 0.6.0) |
| Version floor | 0.6.0 — model.min_vllm_version |
| Tokens | `VLLM_ROCM_USE_AITER` (needs v0.8.2), `--speculative-config` (needs v0.8.2) |
| Confidence | high — VLLM_ROCM_USE_AITER was introduced in v0.8.2, above the pinned floor 0.6.0 |
| Risk | the guide shows flags newer than the pinned floor 0.6.0; the guide text is what needs updating, not necessarily the pin |
| Status | needs decision |

### F-53 — `--disable-log-requests` in `meta-llama/Llama-3.1-8B-Instruct.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | removed — removed upstream |
| Source | source-only |
| Downstream location | `models/meta-llama/Llama-3.1-8B-Instruct.yaml:143` (`guide`) — guide text |
| Upstream evidence | introduced v0.4.2; removed v0.17.0; absent from the flag set at v0.29.0; last present before v0.17.0 |
| Current usage | `--disable-log-requests` |
| Proposed change | decide whether to drop `--disable-log-requests` or re-spell it; upstream documents no replacement |
| Version floor | 0.6.0 — model.min_vllm_version |
| Confidence | high — removed upstream in v0.17.0 (introduced v0.4.2) |
| Risk | --disable-log-requests is gone at v0.29.0, but upstream documents no replacement — deleting it and re-spelling it are different edits |
| Status | needs decision |

### F-54 — `--disable-log-requests` in `meta-llama/Llama-3.3-70B-Instruct.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | removed — removed upstream |
| Source | source-only |
| Downstream location | `models/meta-llama/Llama-3.3-70B-Instruct.yaml:134` (`guide`) — guide text |
| Upstream evidence | introduced v0.4.2; removed v0.17.0; absent from the flag set at v0.29.0; last present before v0.17.0 |
| Current usage | `--disable-log-requests` |
| Proposed change | decide whether to drop `--disable-log-requests` or re-spell it; upstream documents no replacement |
| Version floor | 0.12.0 — model.min_vllm_version |
| Confidence | high — removed upstream in v0.17.0 (introduced v0.4.2) |
| Risk | --disable-log-requests is gone at v0.29.0, but upstream documents no replacement — deleting it and re-spelling it are different edits |
| Status | needs decision |

### F-55 — `--disable-log-requests` in `meta-llama/Llama-4-Scout-17B-16E-Instruct.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | removed — removed upstream |
| Source | source-only |
| Downstream location | `models/meta-llama/Llama-4-Scout-17B-16E-Instruct.yaml:145` (`guide`) — guide text |
| Upstream evidence | introduced v0.4.2; removed v0.17.0; absent from the flag set at v0.29.0; last present before v0.17.0 |
| Current usage | `--disable-log-requests` |
| Proposed change | decide whether to drop `--disable-log-requests` or re-spell it; upstream documents no replacement |
| Version floor | 0.12.0 — model.min_vllm_version |
| Confidence | high — removed upstream in v0.17.0 (introduced v0.4.2) |
| Risk | --disable-log-requests is gone at v0.29.0, but upstream documents no replacement — deleting it and re-spelling it are different edits |
| Status | needs decision |

### F-56 — `--num-gpus` in `MiniMaxAI/MiniMax-H3.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/MiniMaxAI/MiniMax-H3.yaml:63` (`model.base_args`), `models/MiniMaxAI/MiniMax-H3.yaml:651` (`variants.default.hardware_overrides.dgx_spark_gb10.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:671` (`variants.default.hardware_overrides.ascend_950pr.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:693` (`variants.default.hardware_overrides.rtx_pro_5000_4x.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:709` (`variants.default.hardware_overrides.rtx_pro_6000_2x.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:723` (`variants.default.hardware_overrides.rtx_5090_2x.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:746` (`variants.default.hardware_overrides.rtx_4090_2x.extra_args`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `- "--num-gpus"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.26.0 — model.min_vllm_version |
| Confidence | low — --num-gpus is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-57 — `--usp` in `MiniMaxAI/MiniMax-H3.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/MiniMaxAI/MiniMax-H3.yaml:65` (`model.base_args`), `models/MiniMaxAI/MiniMax-H3.yaml:653` (`variants.default.hardware_overrides.dgx_spark_gb10.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:675` (`variants.default.hardware_overrides.ascend_950pr.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:697` (`variants.default.hardware_overrides.rtx_pro_5000_4x.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:713` (`variants.default.hardware_overrides.rtx_pro_6000_2x.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:727` (`variants.default.hardware_overrides.rtx_5090_2x.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:750` (`variants.default.hardware_overrides.rtx_4090_2x.extra_args`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `- "--usp"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.26.0 — model.min_vllm_version |
| Confidence | low — --usp is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-58 — `--ring` in `MiniMaxAI/MiniMax-H3.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/MiniMaxAI/MiniMax-H3.yaml:67` (`model.base_args`), `models/MiniMaxAI/MiniMax-H3.yaml:655` (`variants.default.hardware_overrides.dgx_spark_gb10.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:677` (`variants.default.hardware_overrides.ascend_950pr.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:699` (`variants.default.hardware_overrides.rtx_pro_5000_4x.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:715` (`variants.default.hardware_overrides.rtx_pro_6000_2x.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:729` (`variants.default.hardware_overrides.rtx_5090_2x.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:752` (`variants.default.hardware_overrides.rtx_4090_2x.extra_args`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `- "--ring"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.26.0 — model.min_vllm_version |
| Confidence | low — --ring is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-59 — `--vae-patch-parallel-size` in `MiniMaxAI/MiniMax-H3.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/MiniMaxAI/MiniMax-H3.yaml:69` (`model.base_args`), `models/MiniMaxAI/MiniMax-H3.yaml:657` (`variants.default.hardware_overrides.dgx_spark_gb10.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:681` (`variants.default.hardware_overrides.ascend_950pr.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:703` (`variants.default.hardware_overrides.rtx_pro_5000_4x.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:719` (`variants.default.hardware_overrides.rtx_pro_6000_2x.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:733` (`variants.default.hardware_overrides.rtx_5090_2x.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:756` (`variants.default.hardware_overrides.rtx_4090_2x.extra_args`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `- "--vae-patch-parallel-size"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.26.0 — model.min_vllm_version |
| Confidence | low — --vae-patch-parallel-size is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-60 — `--vae-parallel-mode` in `MiniMaxAI/MiniMax-H3.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/MiniMaxAI/MiniMax-H3.yaml:71` (`model.base_args`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `- "--vae-parallel-mode"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.26.0 — model.min_vllm_version |
| Confidence | low — --vae-parallel-mode is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-61 — `--vae-use-tiling` in `MiniMaxAI/MiniMax-H3.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/MiniMaxAI/MiniMax-H3.yaml:73` (`model.base_args`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `- "--vae-use-tiling"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.26.0 — model.min_vllm_version |
| Confidence | low — --vae-use-tiling is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-62 — `VLLM_OMNI_VIDEO_SYNC_TIMEOUT` in `MiniMaxAI/MiniMax-H3.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/MiniMaxAI/MiniMax-H3.yaml:76` (`model.base_env.VLLM_OMNI_VIDEO_SYNC_TIMEOUT`), `models/MiniMaxAI/MiniMax-H3.yaml:667` (`variants.default.hardware_overrides.dgx_spark_gb10.extra_env.VLLM_OMNI_VIDEO_SYNC_TIMEOUT`), `models/MiniMaxAI/MiniMax-H3.yaml:690` (`variants.default.hardware_overrides.ascend_950pr.extra_env.VLLM_OMNI_VIDEO_SYNC_TIMEOUT`), `models/MiniMaxAI/MiniMax-H3.yaml:743` (`variants.default.hardware_overrides.rtx_5090_2x.extra_env.VLLM_OMNI_VIDEO_SYNC_TIMEOUT`), `models/MiniMaxAI/MiniMax-H3.yaml:766` (`variants.default.hardware_overrides.rtx_4090_2x.extra_env.VLLM_OMNI_VIDEO_SYNC_TIMEOUT`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `VLLM_OMNI_VIDEO_SYNC_TIMEOUT: "1800"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.26.0 — model.min_vllm_version |
| Confidence | low — VLLM_OMNI_VIDEO_SYNC_TIMEOUT is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-63 — `--task` in `MiniMaxAI/MiniMax-H3.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | removed — removed upstream |
| Source | source-only |
| Downstream location | `models/MiniMaxAI/MiniMax-H3.yaml:100` (`omni.tasks.benchmark`) — guide text, `models/MiniMaxAI/MiniMax-H3.yaml:190` (`omni.tasks.benchmark`) — guide text, `models/MiniMaxAI/MiniMax-H3.yaml:341` (`omni.tasks.benchmark`) — guide text, `models/MiniMaxAI/MiniMax-H3.yaml:424` (`omni.tasks.benchmark`) — guide text, `models/MiniMaxAI/MiniMax-H3.yaml:518` (`omni.tasks.benchmark`) — guide text |
| Upstream evidence | introduced v0.6.4; removed v0.13.0; absent from the flag set at v0.29.0; last present before v0.13.0 |
| Current usage | `--task t2v \` |
| Proposed change | decide whether to drop `--task` or re-spell it; upstream documents no replacement |
| Version floor | 0.26.0 — model.min_vllm_version |
| Confidence | high — removed upstream in v0.13.0 (introduced v0.6.4) |
| Risk | --task is gone at v0.29.0, but upstream documents no replacement — deleting it and re-spelling it are different edits |
| Status | needs decision |

### F-64 — `--task-type` in `MiniMaxAI/MiniMax-H3.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/MiniMaxAI/MiniMax-H3.yaml:111` (`omni.tasks.hardware_overrides.rtx_pro_5000_4x.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:114` (`omni.tasks.hardware_overrides.rtx_pro_6000_2x.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:117` (`omni.tasks.hardware_overrides.rtx_5090_2x.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:120` (`omni.tasks.hardware_overrides.rtx_4090_2x.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:135` (`omni.tasks.hardware_overrides.dgx_spark_gb10.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:150` (`omni.tasks.hardware_overrides.ascend_950pr.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:202` (`omni.tasks.hardware_overrides.rtx_pro_5000_4x.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:205` (`omni.tasks.hardware_overrides.rtx_pro_6000_2x.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:208` (`omni.tasks.hardware_overrides.rtx_5090_2x.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:211` (`omni.tasks.hardware_overrides.rtx_4090_2x.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:228` (`omni.tasks.hardware_overrides.dgx_spark_gb10.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:267` (`omni.tasks.hardware_overrides.rtx_pro_5000_4x.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:270` (`omni.tasks.hardware_overrides.rtx_pro_6000_2x.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:273` (`omni.tasks.hardware_overrides.rtx_5090_2x.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:276` (`omni.tasks.hardware_overrides.rtx_4090_2x.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:295` (`omni.tasks.hardware_overrides.dgx_spark_gb10.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:353` (`omni.tasks.hardware_overrides.rtx_pro_5000_4x.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:356` (`omni.tasks.hardware_overrides.rtx_pro_6000_2x.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:359` (`omni.tasks.hardware_overrides.rtx_5090_2x.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:362` (`omni.tasks.hardware_overrides.rtx_4090_2x.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:379` (`omni.tasks.hardware_overrides.dgx_spark_gb10.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:436` (`omni.tasks.hardware_overrides.rtx_pro_5000_4x.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:439` (`omni.tasks.hardware_overrides.rtx_pro_6000_2x.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:442` (`omni.tasks.hardware_overrides.rtx_5090_2x.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:445` (`omni.tasks.hardware_overrides.rtx_4090_2x.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:466` (`omni.tasks.hardware_overrides.dgx_spark_gb10.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:529` (`omni.tasks.hardware_overrides.rtx_pro_5000_4x.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:532` (`omni.tasks.hardware_overrides.rtx_pro_6000_2x.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:535` (`omni.tasks.hardware_overrides.rtx_5090_2x.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:538` (`omni.tasks.hardware_overrides.rtx_4090_2x.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:557` (`omni.tasks.hardware_overrides.dgx_spark_gb10.extra_args`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `extra_args: ["--task-type", "fl2va"]` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.26.0 — model.min_vllm_version |
| Confidence | low — --task-type is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-65 — `--init-timeout` in `MiniMaxAI/MiniMax-H3.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/MiniMaxAI/MiniMax-H3.yaml:661` (`variants.default.hardware_overrides.dgx_spark_gb10.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:685` (`variants.default.hardware_overrides.ascend_950pr.extra_args`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `- "--init-timeout"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.26.0 — model.min_vllm_version |
| Confidence | low — --init-timeout is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-66 — `--diffusion-attention-backend` in `MiniMaxAI/MiniMax-H3.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/MiniMaxAI/MiniMax-H3.yaml:664` (`variants.default.hardware_overrides.dgx_spark_gb10.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:705` (`variants.default.hardware_overrides.rtx_pro_5000_4x.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:735` (`variants.default.hardware_overrides.rtx_5090_2x.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:758` (`variants.default.hardware_overrides.rtx_4090_2x.extra_args`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `- "--diffusion-attention-backend"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.26.0 — model.min_vllm_version |
| Confidence | low — --diffusion-attention-backend is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-67 — `--text-encoder-tp-size` in `MiniMaxAI/MiniMax-H3.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/MiniMaxAI/MiniMax-H3.yaml:679` (`variants.default.hardware_overrides.ascend_950pr.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:701` (`variants.default.hardware_overrides.rtx_pro_5000_4x.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:717` (`variants.default.hardware_overrides.rtx_pro_6000_2x.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:731` (`variants.default.hardware_overrides.rtx_5090_2x.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:754` (`variants.default.hardware_overrides.rtx_4090_2x.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:780` (`hardware_overrides.amd.extra_args`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `- "--text-encoder-tp-size"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.26.0 — model.min_vllm_version |
| Confidence | low — --text-encoder-tp-size is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-68 — `--stage-init-timeout` in `MiniMaxAI/MiniMax-H3.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/MiniMaxAI/MiniMax-H3.yaml:687` (`variants.default.hardware_overrides.ascend_950pr.extra_args`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `- "--stage-init-timeout"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.26.0 — model.min_vllm_version |
| Confidence | low — --stage-init-timeout is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-69 — `--enable-distributed-layerwise-offload` in `MiniMaxAI/MiniMax-H3.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/MiniMaxAI/MiniMax-H3.yaml:737` (`variants.default.hardware_overrides.rtx_5090_2x.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:760` (`variants.default.hardware_overrides.rtx_4090_2x.extra_args`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `- "--enable-distributed-layerwise-offload"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.26.0 — model.min_vllm_version |
| Confidence | low — --enable-distributed-layerwise-offload is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-70 — `--dlo-no-use-allgather` in `MiniMaxAI/MiniMax-H3.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/MiniMaxAI/MiniMax-H3.yaml:738` (`variants.default.hardware_overrides.rtx_5090_2x.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:761` (`variants.default.hardware_overrides.rtx_4090_2x.extra_args`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `- "--dlo-no-use-allgather"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.26.0 — model.min_vllm_version |
| Confidence | low — --dlo-no-use-allgather is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-71 — `--dlo-resident-layers` in `MiniMaxAI/MiniMax-H3.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/MiniMaxAI/MiniMax-H3.yaml:739` (`variants.default.hardware_overrides.rtx_5090_2x.extra_args`), `models/MiniMaxAI/MiniMax-H3.yaml:762` (`variants.default.hardware_overrides.rtx_4090_2x.extra_args`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `- "--dlo-resident-layers"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.26.0 — model.min_vllm_version |
| Confidence | low — --dlo-resident-layers is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-72 — `--omni` in `mistralai/Voxtral-4B-TTS-2603.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/mistralai/Voxtral-4B-TTS-2603.yaml:24` (`model.base_args`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `- "--omni"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.20.0 — model.min_vllm_version |
| Confidence | low — --omni is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-73 — `--disable-log-requests` in `moonshotai/Kimi-K2-Instruct.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | removed — removed upstream |
| Source | source-only |
| Downstream location | `models/moonshotai/Kimi-K2-Instruct.yaml:92` (`strategy_overrides.multi_node_tp_pp.vllm_args`) — guide text, `models/moonshotai/Kimi-K2-Instruct.yaml:143` (`guide`) — guide text |
| Upstream evidence | introduced v0.4.2; removed v0.17.0; absent from the flag set at v0.29.0; last present before v0.17.0 |
| Current usage | `- "--disable-log-requests"` |
| Proposed change | decide whether to drop `--disable-log-requests` or re-spell it; upstream documents no replacement |
| Version floor | 0.12.0 — model.min_vllm_version |
| Confidence | high — removed upstream in v0.17.0 (introduced v0.4.2) |
| Risk | --disable-log-requests is gone at v0.29.0, but upstream documents no replacement — deleting it and re-spelling it are different edits |
| Status | needs decision |

### F-74 — `--dcp-comm-backend` in `moonshotai/Kimi-K3.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | default-changed — upstream default changed |
| Source | source-only |
| Downstream location | `models/moonshotai/Kimi-K3.yaml:89` (`features.decode_context_parallelism.args`), `models/moonshotai/Kimi-K3.yaml:444` (`guide`) — guide text |
| Upstream evidence | introduced v0.18.0; `vllm/config/parallel.py:361` @ v0.29.0; no independent upstream re-check for this category |
| Current usage | `- "--dcp-comm-backend"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.29.0 — model.min_vllm_version |
| Confidence | high — default 'ag_rs' -> None |
| Risk | a changed upstream default is a behaviour question for the recipe author |
| Status | needs decision |

### F-75 — `VLLM_ROCM_USE_AITER_MOE_SITUV2` in `moonshotai/Kimi-K3.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/moonshotai/Kimi-K3.yaml:268` (`hardware_overrides.amd.extra_env.VLLM_ROCM_USE_AITER_MOE_SITUV2`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `VLLM_ROCM_USE_AITER_MOE_SITUV2: "1"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.29.0 — model.min_vllm_version |
| Confidence | low — VLLM_ROCM_USE_AITER_MOE_SITUV2 is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-76 — `--init-timeout` in `nvidia/Cosmos3-Nano.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/nvidia/Cosmos3-Nano.yaml:37` (`model.base_args`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `- "--init-timeout"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.21.0 — model.min_vllm_version |
| Confidence | low — --init-timeout is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-77 — `--cfg-parallel-size` in `nvidia/Cosmos3-Super-Image2Video.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/nvidia/Cosmos3-Super-Image2Video.yaml:37` (`model.base_args`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `- "--cfg-parallel-size"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.21.0 — model.min_vllm_version |
| Confidence | low — --cfg-parallel-size is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-78 — `--ulysses-degree` in `nvidia/Cosmos3-Super-Image2Video.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/nvidia/Cosmos3-Super-Image2Video.yaml:39` (`model.base_args`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `- "--ulysses-degree"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.21.0 — model.min_vllm_version |
| Confidence | low — --ulysses-degree is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-79 — `--use-hsdp` in `nvidia/Cosmos3-Super-Image2Video.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/nvidia/Cosmos3-Super-Image2Video.yaml:41` (`model.base_args`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `- "--use-hsdp"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.21.0 — model.min_vllm_version |
| Confidence | low — --use-hsdp is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-80 — `--hsdp-shard-size` in `nvidia/Cosmos3-Super-Image2Video.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/nvidia/Cosmos3-Super-Image2Video.yaml:42` (`model.base_args`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `- "--hsdp-shard-size"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.21.0 — model.min_vllm_version |
| Confidence | low — --hsdp-shard-size is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-81 — `--init-timeout` in `nvidia/Cosmos3-Super-Image2Video.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/nvidia/Cosmos3-Super-Image2Video.yaml:44` (`model.base_args`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `- "--init-timeout"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.21.0 — model.min_vllm_version |
| Confidence | low — --init-timeout is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-82 — `--cfg-parallel-size` in `nvidia/Cosmos3-Super-Text2Image.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/nvidia/Cosmos3-Super-Text2Image.yaml:38` (`model.base_args`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `- "--cfg-parallel-size"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.21.0 — model.min_vllm_version |
| Confidence | low — --cfg-parallel-size is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-83 — `--ulysses-degree` in `nvidia/Cosmos3-Super-Text2Image.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/nvidia/Cosmos3-Super-Text2Image.yaml:40` (`model.base_args`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `- "--ulysses-degree"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.21.0 — model.min_vllm_version |
| Confidence | low — --ulysses-degree is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-84 — `--use-hsdp` in `nvidia/Cosmos3-Super-Text2Image.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/nvidia/Cosmos3-Super-Text2Image.yaml:44` (`model.base_args`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `- "--use-hsdp"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.21.0 — model.min_vllm_version |
| Confidence | low — --use-hsdp is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-85 — `--hsdp-shard-size` in `nvidia/Cosmos3-Super-Text2Image.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/nvidia/Cosmos3-Super-Text2Image.yaml:45` (`model.base_args`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `- "--hsdp-shard-size"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.21.0 — model.min_vllm_version |
| Confidence | low — --hsdp-shard-size is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-86 — `--init-timeout` in `nvidia/Cosmos3-Super-Text2Image.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/nvidia/Cosmos3-Super-Text2Image.yaml:47` (`model.base_args`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `- "--init-timeout"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.21.0 — model.min_vllm_version |
| Confidence | low — --init-timeout is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-87 — `--cfg-parallel-size` in `nvidia/Cosmos3-Super.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/nvidia/Cosmos3-Super.yaml:37` (`model.base_args`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `- "--cfg-parallel-size"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.21.0 — model.min_vllm_version |
| Confidence | low — --cfg-parallel-size is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-88 — `--ulysses-degree` in `nvidia/Cosmos3-Super.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/nvidia/Cosmos3-Super.yaml:39` (`model.base_args`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `- "--ulysses-degree"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.21.0 — model.min_vllm_version |
| Confidence | low — --ulysses-degree is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-89 — `--use-hsdp` in `nvidia/Cosmos3-Super.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/nvidia/Cosmos3-Super.yaml:41` (`model.base_args`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `- "--use-hsdp"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.21.0 — model.min_vllm_version |
| Confidence | low — --use-hsdp is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-90 — `--hsdp-shard-size` in `nvidia/Cosmos3-Super.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/nvidia/Cosmos3-Super.yaml:42` (`model.base_args`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `- "--hsdp-shard-size"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.21.0 — model.min_vllm_version |
| Confidence | low — --hsdp-shard-size is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-91 — `--init-timeout` in `nvidia/Cosmos3-Super.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/nvidia/Cosmos3-Super.yaml:44` (`model.base_args`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `- "--init-timeout"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.21.0 — model.min_vllm_version |
| Confidence | low — --init-timeout is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-92 — `--moe-backend` in `openai/gpt-oss-120b.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | below-introducing-version — flag used below the version that introduced it |
| Source | both |
| Downstream location | `models/openai/gpt-oss-120b.yaml:147` (`guide`) — guide text, `models/openai/gpt-oss-120b.yaml:184` (`guide`) — guide text, `models/openai/gpt-oss-120b.yaml:198` (`guide`) — guide text |
| Upstream evidence | introduced v0.17.0; `vllm/config/kernel.py:235` @ v0.29.0; PRs #52182; introduced in v0.17.0, present at v0.29.0 |
| Current usage | `On vLLM v0.28.0+ the FlashInfer TRTLLM MXFP4 MoE path is selected automatically on Blackwell; it can be pinned explicitly with `--moe-backend flashinfer_trtllm ` |
| Proposed change | update the guide text (it shows flags needing 0.17.0, the recipe pins 0.10.0) |
| Version floor | 0.10.0 — model.min_vllm_version |
| Tokens | `--moe-backend` (needs v0.17.0), `--attention-backend` (needs v0.13.0), `--tool-server` (needs v0.10.1) |
| Confidence | high — --moe-backend was introduced in v0.17.0, above the pinned floor 0.10.0 |
| Risk | the guide shows flags newer than the pinned floor 0.10.0; the guide text is what needs updating, not necessarily the pin |
| Status | needs decision |

### F-93 — `--moe-backend` in `openai/gpt-oss-20b.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | below-introducing-version — flag used below the version that introduced it |
| Source | both |
| Downstream location | `models/openai/gpt-oss-20b.yaml:174` (`guide`) — guide text, `models/openai/gpt-oss-20b.yaml:187` (`guide`) — guide text, `models/openai/gpt-oss-20b.yaml:212` (`guide`) — guide text |
| Upstream evidence | introduced v0.17.0; `vllm/config/kernel.py:235` @ v0.29.0; PRs #52182; introduced in v0.17.0, present at v0.29.0 |
| Current usage | `On vLLM v0.28.0+ the FlashInfer TRTLLM MXFP4 MoE path is selected automatically on Blackwell; it can be pinned explicitly with `--moe-backend flashinfer_trtllm ` |
| Proposed change | update the guide text (it shows flags needing 0.17.0, the recipe pins 0.10.0) |
| Version floor | 0.10.0 — model.min_vllm_version |
| Tokens | `--moe-backend` (needs v0.17.0), `--attention-backend` (needs v0.13.0), `--tool-server` (needs v0.10.1) |
| Confidence | high — --moe-backend was introduced in v0.17.0, above the pinned floor 0.10.0 |
| Risk | the guide shows flags newer than the pinned floor 0.10.0; the guide text is what needs updating, not necessarily the pin |
| Status | needs decision |

### F-94 — `--omni` in `openbmb/VoxCPM2.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/openbmb/VoxCPM2.yaml:24` (`model.base_args`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `- "--omni"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.21.0 — model.min_vllm_version |
| Confidence | low — --omni is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-95 — `--omni` in `OpenMOSS-Team/MOSS-SoundEffect.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/OpenMOSS-Team/MOSS-SoundEffect.yaml:24` (`model.base_args`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `- "--omni"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.22.0 — model.min_vllm_version |
| Confidence | low — --omni is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-96 — `--deploy-config` in `OpenMOSS-Team/MOSS-SoundEffect.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/OpenMOSS-Team/MOSS-SoundEffect.yaml:25` (`model.base_args`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `- "--deploy-config"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.22.0 — model.min_vllm_version |
| Confidence | low — --deploy-config is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-97 — `--omni` in `OpenMOSS-Team/MOSS-TTS-Realtime.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/OpenMOSS-Team/MOSS-TTS-Realtime.yaml:24` (`model.base_args`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `- "--omni"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.22.0 — model.min_vllm_version |
| Confidence | low — --omni is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-98 — `--omni` in `OpenMOSS-Team/MOSS-TTS.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/OpenMOSS-Team/MOSS-TTS.yaml:24` (`model.base_args`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `- "--omni"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.22.0 — model.min_vllm_version |
| Confidence | low — --omni is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-99 — `--deploy-config` in `OpenMOSS-Team/MOSS-TTS.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/OpenMOSS-Team/MOSS-TTS.yaml:25` (`model.base_args`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `- "--deploy-config"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.22.0 — model.min_vllm_version |
| Confidence | low — --deploy-config is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-100 — `--omni` in `OpenMOSS-Team/MOSS-TTSD-v1.0.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/OpenMOSS-Team/MOSS-TTSD-v1.0.yaml:24` (`model.base_args`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `- "--omni"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.22.0 — model.min_vllm_version |
| Confidence | low — --omni is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-101 — `--deploy-config` in `OpenMOSS-Team/MOSS-TTSD-v1.0.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/OpenMOSS-Team/MOSS-TTSD-v1.0.yaml:25` (`model.base_args`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `- "--deploy-config"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.22.0 — model.min_vllm_version |
| Confidence | low — --deploy-config is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-102 — `--omni` in `OpenMOSS-Team/MOSS-VoiceGenerator.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/OpenMOSS-Team/MOSS-VoiceGenerator.yaml:24` (`model.base_args`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `- "--omni"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.22.0 — model.min_vllm_version |
| Confidence | low — --omni is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-103 — `--deploy-config` in `OpenMOSS-Team/MOSS-VoiceGenerator.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/OpenMOSS-Team/MOSS-VoiceGenerator.yaml:25` (`model.base_args`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `- "--deploy-config"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.22.0 — model.min_vllm_version |
| Confidence | low — --deploy-config is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-104 — `--ignored-layers` in `Qwen/Qwen-Image.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/Qwen/Qwen-Image.yaml:48` (`variants.fp8.extra_args`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `- "--ignored-layers"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.18.0 — model.min_vllm_version |
| Confidence | low — --ignored-layers is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-105 — `VLLM_USE_V1` in `Qwen/Qwen2.5-32B.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | removed — removed upstream |
| Source | source-only |
| Downstream location | `models/Qwen/Qwen2.5-32B.yaml:98` (`guide`) — guide text |
| Upstream evidence | introduced v0.6.4; removed v0.11.1; absent from the flag set at v0.29.0; last present before v0.11.1 |
| Current usage | `- vLLM has been V1-engine-only for a long time, so no `VLLM_USE_V1=1` export is needed even though the upstream TPU recipe still shows it.` |
| Proposed change | decide whether to drop `VLLM_USE_V1` or re-spell it; upstream documents no replacement |
| Version floor | 0.6.2 — model.min_vllm_version |
| Confidence | high — removed upstream in v0.11.1 (introduced v0.6.4) |
| Risk | VLLM_USE_V1 is gone at v0.29.0, but upstream documents no replacement — deleting it and re-spelling it are different edits |
| Status | needs decision |

### F-106 — `--mm-encoder-tp-mode` in `Qwen/Qwen2.5-VL-72B-Instruct.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | below-introducing-version — flag used below the version that introduced it |
| Source | source-only |
| Downstream location | `models/Qwen/Qwen2.5-VL-72B-Instruct.yaml:124` (`guide`) — guide text, `models/Qwen/Qwen2.5-VL-72B-Instruct.yaml:131` (`guide`) — guide text, `models/Qwen/Qwen2.5-VL-72B-Instruct.yaml:136` (`guide`) — guide text, `models/Qwen/Qwen2.5-VL-72B-Instruct.yaml:148` (`guide`) — guide text, `models/Qwen/Qwen2.5-VL-72B-Instruct.yaml:157` (`guide`) — guide text |
| Upstream evidence | introduced v0.10.2; introduced in v0.10.2, present at v0.29.0 |
| Current usage | `--mm-encoder-tp-mode data \` |
| Proposed change | update the guide text (it shows flags needing 0.10.2, the recipe pins 0.7.0) |
| Version floor | 0.7.0 — model.min_vllm_version |
| Tokens | `--mm-encoder-tp-mode` (needs v0.10.2), `VLLM_ROCM_USE_AITER` (needs v0.8.2), `--data-parallel-size` (needs v0.8.3) |
| Confidence | high — --mm-encoder-tp-mode was introduced in v0.10.2, above the pinned floor 0.7.0 |
| Risk | the guide shows flags newer than the pinned floor 0.7.0; the guide text is what needs updating, not necessarily the pin |
| Status | needs decision |

### F-107 — `--mm-encoder-tp-mode` in `Qwen/Qwen2.5-VL-7B-Instruct.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | below-introducing-version — flag used below the version that introduced it |
| Source | source-only |
| Downstream location | `models/Qwen/Qwen2.5-VL-7B-Instruct.yaml:129` (`guide`) — guide text, `models/Qwen/Qwen2.5-VL-7B-Instruct.yaml:161` (`guide`) — guide text, `models/Qwen/Qwen2.5-VL-7B-Instruct.yaml:180` (`guide`) — guide text, `models/Qwen/Qwen2.5-VL-7B-Instruct.yaml:190` (`guide`) — guide text |
| Upstream evidence | introduced v0.10.2; introduced in v0.10.2, present at v0.29.0 |
| Current usage | `--mm-encoder-tp-mode data` |
| Proposed change | update the guide text (it shows flags needing 0.10.2, the recipe pins 0.7.0) |
| Version floor | 0.7.0 — model.min_vllm_version |
| Tokens | `--mm-encoder-tp-mode` (needs v0.10.2), `--disable-chunked-mm-input` (needs v0.8.4), `--data-parallel-size` (needs v0.8.3) |
| Confidence | high — --mm-encoder-tp-mode was introduced in v0.10.2, above the pinned floor 0.7.0 |
| Risk | the guide shows flags newer than the pinned floor 0.7.0; the guide text is what needs updating, not necessarily the pin |
| Status | needs decision |

### F-108 — `--guided-decoding-backend` in `Qwen/Qwen2.5-VL-7B-Instruct.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | removed — removed upstream |
| Source | source-only |
| Downstream location | `models/Qwen/Qwen2.5-VL-7B-Instruct.yaml:160` (`guide`) — guide text |
| Upstream evidence | introduced v0.4.2; removed v0.12.0; absent from the flag set at v0.29.0; last present before v0.12.0 |
| Current usage | `--guided-decoding-backend xgrammar \` |
| Proposed change | decide whether to drop `--guided-decoding-backend` or re-spell it; upstream documents no replacement |
| Version floor | 0.7.0 — model.min_vllm_version |
| Confidence | high — removed upstream in v0.12.0 (introduced v0.4.2) |
| Risk | --guided-decoding-backend is gone at v0.29.0, but upstream documents no replacement — deleting it and re-spelling it are different edits |
| Status | needs decision |

### F-109 — `--disable-log-requests` in `Qwen/Qwen3-235B-A22B-Instruct-2507.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | removed — removed upstream |
| Source | source-only |
| Downstream location | `models/Qwen/Qwen3-235B-A22B-Instruct-2507.yaml:113` (`guide`) — guide text, `models/Qwen/Qwen3-235B-A22B-Instruct-2507.yaml:132` (`guide`) — guide text |
| Upstream evidence | introduced v0.4.2; removed v0.17.0; absent from the flag set at v0.29.0; last present before v0.17.0 |
| Current usage | `--disable-log-requests \` |
| Proposed change | decide whether to drop `--disable-log-requests` or re-spell it; upstream documents no replacement |
| Version floor | 0.10.0 — model.min_vllm_version |
| Confidence | high — removed upstream in v0.17.0 (introduced v0.4.2) |
| Risk | --disable-log-requests is gone at v0.29.0, but upstream documents no replacement — deleting it and re-spelling it are different edits |
| Status | needs decision |

### F-110 — `--swap-space` in `Qwen/Qwen3-235B-A22B-Instruct-2507.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | removed — removed upstream |
| Source | source-only |
| Downstream location | `models/Qwen/Qwen3-235B-A22B-Instruct-2507.yaml:114` (`guide`) — guide text, `models/Qwen/Qwen3-235B-A22B-Instruct-2507.yaml:133` (`guide`) — guide text |
| Upstream evidence | introduced v0.4.2; removed v0.18.0; absent from the flag set at v0.29.0; last present before v0.18.0 |
| Current usage | `--swap-space 32 \` |
| Proposed change | decide whether to drop `--swap-space` or re-spell it; upstream documents no replacement |
| Version floor | 0.10.0 — model.min_vllm_version |
| Confidence | high — removed upstream in v0.18.0 (introduced v0.4.2) |
| Risk | --swap-space is gone at v0.29.0, but upstream documents no replacement — deleting it and re-spelling it are different edits |
| Status | needs decision |

### F-111 — `--disable-log-requests` in `Qwen/Qwen3-32B.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | removed — removed upstream |
| Source | source-only |
| Downstream location | `models/Qwen/Qwen3-32B.yaml:128` (`guide`) — guide text |
| Upstream evidence | introduced v0.4.2; removed v0.17.0; absent from the flag set at v0.29.0; last present before v0.17.0 |
| Current usage | `--disable-log-requests \` |
| Proposed change | decide whether to drop `--disable-log-requests` or re-spell it; upstream documents no replacement |
| Version floor | 0.8.5 — model.min_vllm_version |
| Confidence | high — removed upstream in v0.17.0 (introduced v0.4.2) |
| Risk | --disable-log-requests is gone at v0.29.0, but upstream documents no replacement — deleting it and re-spelling it are different edits |
| Status | needs decision |

### F-112 — `--async-scheduling` in `Qwen/Qwen3-32B.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | below-introducing-version — flag used below the version that introduced it |
| Source | source-only |
| Downstream location | `models/Qwen/Qwen3-32B.yaml:156` (`guide`) — guide text |
| Upstream evidence | introduced v0.10.0; introduced in v0.10.0, present at v0.29.0 |
| Current usage | `--async-scheduling` |
| Proposed change | update the guide text (it shows flags needing 0.10.0, the recipe pins 0.8.5) |
| Version floor | 0.8.5 — model.min_vllm_version |
| Confidence | high — --async-scheduling was introduced in v0.10.0, above the pinned floor 0.8.5 |
| Risk | the guide shows flags newer than the pinned floor 0.8.5; the guide text is what needs updating, not necessarily the pin |
| Status | needs decision |

### F-113 — `--disable-log-requests` in `Qwen/Qwen3-4B.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | removed — removed upstream |
| Source | source-only |
| Downstream location | `models/Qwen/Qwen3-4B.yaml:111` (`guide`) — guide text |
| Upstream evidence | introduced v0.4.2; removed v0.17.0; absent from the flag set at v0.29.0; last present before v0.17.0 |
| Current usage | `--disable-log-requests \` |
| Proposed change | decide whether to drop `--disable-log-requests` or re-spell it; upstream documents no replacement |
| Version floor | 0.8.5 — model.min_vllm_version |
| Confidence | high — removed upstream in v0.17.0 (introduced v0.4.2) |
| Risk | --disable-log-requests is gone at v0.29.0, but upstream documents no replacement — deleting it and re-spelling it are different edits |
| Status | needs decision |

### F-114 — `--omni` in `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice.yaml:24` (`model.base_args`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `- "--omni"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.20.0 — model.min_vllm_version |
| Confidence | low — --omni is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-115 — `VLLM_ROCM_SHUFFLE_KV_CACHE_LAYOUT` in `Qwen/Qwen3-VL-235B-A22B-Instruct.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | below-introducing-version — flag used below the version that introduced it |
| Source | source-only |
| Downstream location | `models/Qwen/Qwen3-VL-235B-A22B-Instruct.yaml:189` (`guide`) — guide text, `models/Qwen/Qwen3-VL-235B-A22B-Instruct.yaml:199` (`guide`) — guide text, `models/Qwen/Qwen3-VL-235B-A22B-Instruct.yaml:210` (`guide`) — guide text, `models/Qwen/Qwen3-VL-235B-A22B-Instruct.yaml:224` (`guide`) — guide text, `models/Qwen/Qwen3-VL-235B-A22B-Instruct.yaml:231` (`guide`) — guide text, `models/Qwen/Qwen3-VL-235B-A22B-Instruct.yaml:231` (`guide`) — guide text, `models/Qwen/Qwen3-VL-235B-A22B-Instruct.yaml:241` (`guide`) — guide text, `models/Qwen/Qwen3-VL-235B-A22B-Instruct.yaml:253` (`guide`) — guide text |
| Upstream evidence | introduced v0.15.0; introduced in v0.15.0, present at v0.29.0 |
| Current usage | `export VLLM_ROCM_SHUFFLE_KV_CACHE_LAYOUT="1"` |
| Proposed change | update the guide text (it shows flags needing 0.15.0, the recipe pins 0.11.0) |
| Version floor | 0.11.0 — model.min_vllm_version |
| Tokens | `VLLM_ROCM_SHUFFLE_KV_CACHE_LAYOUT` (needs v0.15.0), `--attention-backend` (needs v0.13.0) |
| Confidence | high — VLLM_ROCM_SHUFFLE_KV_CACHE_LAYOUT was introduced in v0.15.0, above the pinned floor 0.11.0 |
| Risk | the guide shows flags newer than the pinned floor 0.11.0; the guide text is what needs updating, not necessarily the pin |
| Status | needs decision |

### F-116 — `--rope-scaling` in `Qwen/Qwen3-VL-235B-A22B-Instruct.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | removed — removed upstream |
| Source | source-only |
| Downstream location | `models/Qwen/Qwen3-VL-235B-A22B-Instruct.yaml:267` (`guide`) — guide text |
| Upstream evidence | introduced v0.4.3; removed v0.11.1; absent from the flag set at v0.29.0; last present before v0.11.1 |
| Current usage | ``--rope-scaling '{"rope_type":"yarn","factor":3.0,"original_max_position_embeddings":262144,"mrope_section":[24,20,20],"mrope_interleaved":true}' --max-model-le` |
| Proposed change | decide whether to drop `--rope-scaling` or re-spell it; upstream documents no replacement |
| Version floor | 0.11.0 — model.min_vllm_version |
| Confidence | high — removed upstream in v0.11.1 (introduced v0.4.3) |
| Risk | --rope-scaling is gone at v0.29.0, but upstream documents no replacement — deleting it and re-spelling it are different edits |
| Status | needs decision |

### F-117 — `VLLM_ASCEND_ENABLE_PREFETCH_MLP` in `Qwen/Qwen3.5-397B-A17B.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/Qwen/Qwen3.5-397B-A17B.yaml:164` (`variants.ascend_w8a8_mtp.extra_env.VLLM_ASCEND_ENABLE_PREFETCH_MLP`), `models/Qwen/Qwen3.5-397B-A17B.yaml:211` (`variants.ascend_w4a4_mxfp4.extra_env.VLLM_ASCEND_ENABLE_PREFETCH_MLP`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `VLLM_ASCEND_ENABLE_PREFETCH_MLP: "1"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.23.0 — variant ascend_w8a8_mtp pin |
| Confidence | low — VLLM_ASCEND_ENABLE_PREFETCH_MLP is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-118 — `VLLM_PLE_CPU_OFFLOAD` in `Qwen/Qwen3.8-Flash-Next.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/Qwen/Qwen3.8-Flash-Next.yaml:127` (`variants.fp8.hardware_overrides.h100.extra_env.VLLM_PLE_CPU_OFFLOAD`), `models/Qwen/Qwen3.8-Flash-Next.yaml:180` (`strategy_overrides.single_node_dep.extra_env.VLLM_PLE_CPU_OFFLOAD`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `VLLM_PLE_CPU_OFFLOAD: "1"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.29.0 — model.min_vllm_version |
| Confidence | low — VLLM_PLE_CPU_OFFLOAD is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-119 — `VLLM_OMNI_TARGET_DEVICE` in `stabilityai/stable-diffusion-3.5-medium.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/stabilityai/stable-diffusion-3.5-medium.yaml:71` (`hardware_overrides.amd.extra_env.VLLM_OMNI_TARGET_DEVICE`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `VLLM_OMNI_TARGET_DEVICE: "rocm"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.12.0 — model.min_vllm_version |
| Confidence | low — VLLM_OMNI_TARGET_DEVICE is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |

### F-120 — `--disable-log-requests` in `zai-org/GLM-4.7.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | removed — removed upstream |
| Source | source-only |
| Downstream location | `models/zai-org/GLM-4.7.yaml:150` (`guide`) — guide text |
| Upstream evidence | introduced v0.4.2; removed v0.17.0; absent from the flag set at v0.29.0; last present before v0.17.0 |
| Current usage | `--disable-log-requests \` |
| Proposed change | decide whether to drop `--disable-log-requests` or re-spell it; upstream documents no replacement |
| Version floor | 0.24.0 — model.min_vllm_version |
| Confidence | high — removed upstream in v0.17.0 (introduced v0.4.2) |
| Risk | --disable-log-requests is gone at v0.29.0, but upstream documents no replacement — deleting it and re-spelling it are different edits |
| Status | needs decision |

### F-121 — `--cc.pass_config.fuse_allreduce_rms` in `zai-org/GLM-5.1.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | wrong-dash — two dashes on a one-dash alias — argparse rejects it |
| Source | source-only |
| Downstream location | `models/zai-org/GLM-5.1.yaml:89` (`variants.mxfp4.extra_args`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `- "--cc.pass_config.fuse_allreduce_rms=False"` |
| Proposed change | replace `--cc.pass_config.fuse_allreduce_rms` with `-cc` |
| Version floor | 0.24.0 — variant mxfp4 pin |
| Confidence | high — -cc is registered with a single dash as the alias of --compilation-config; `--cc` is not a prefix abbreviation of it, so this argument is rejected |
| Risk | the flag is spelled with two dashes where only a one-dash alias is registered |
| Status | needs decision |

### F-122 — `--omni` in `zai-org/GLM-TTS.yaml`

| Field | Value |
|---|---|
| Type | stale-usage |
| Category | unknown-upstream — not shipped by vLLM at any indexed tag |
| Source | source-only |
| Downstream location | `models/zai-org/GLM-TTS.yaml:24` (`model.base_args`) |
| Upstream evidence | absent from every indexed tag |
| Current usage | `- "--omni"` |
| Proposed change | report only — no mechanical edit |
| Version floor | 0.22.0 — model.min_vllm_version |
| Confidence | low — --omni is in no indexed release and resembles no vLLM flag — likely provided by a plugin (vllm-omni, vllm-ascend, ...), which this tool cannot see |
| Risk | not shipped by vLLM at any indexed tag; most likely a plugin flag this tool cannot see |
| Status | needs decision |


## Missed improvements — prefiltered candidates (642)

These are deterministic model/hardware joins between the release notes and the recipes.
They are NOT findings until the orchestrator confirms each one against upstream and
proposes a concrete edit; unconfirmed rows must not be applied.

| Recipe | Item | Models | Hardware | PRs |
|---|---|---|---|---|
| `Google/gemma-4-12B-it.yaml` | I-159 | gemma4 | — | #53884 |
| `Google/gemma-4-12B-it.yaml` | I-350 | gemma4 | — | #53657 |
| `Google/gemma-4-26B-A4B-it.yaml` | I-159 | gemma4 | — | #53884 |
| `Google/gemma-4-26B-A4B-it.yaml` | I-350 | gemma4 | — | #53657 |
| `Google/gemma-4-31B-it.yaml` | I-159 | gemma4 | — | #53884 |
| `Google/gemma-4-31B-it.yaml` | I-350 | gemma4 | — | #53657 |
| `Google/gemma-4-E2B-it.yaml` | I-159 | gemma4 | — | #53884 |
| `Google/gemma-4-E2B-it.yaml` | I-350 | gemma4 | — | #53657 |
| `Google/gemma-4-E4B-it.yaml` | I-159 | gemma4 | — | #53884 |
| `Google/gemma-4-E4B-it.yaml` | I-350 | gemma4 | — | #53657 |
| `MiniMaxAI/MiniMax-H3.yaml` | I-127 | minimax-m3 | — | #51203 |
| `MiniMaxAI/MiniMax-H3.yaml` | I-227 | minimax-m3 | — | #52849 |
| `MiniMaxAI/MiniMax-M2.1.yaml` | I-127 | minimax-m3 | — | #51203 |
| `MiniMaxAI/MiniMax-M2.1.yaml` | I-227 | minimax-m3 | — | #52849 |
| `MiniMaxAI/MiniMax-M2.5.yaml` | I-127 | minimax-m3 | — | #51203 |
| `MiniMaxAI/MiniMax-M2.5.yaml` | I-227 | minimax-m3 | — | #52849 |
| `MiniMaxAI/MiniMax-M2.7.yaml` | I-127 | minimax-m3 | — | #51203 |
| `MiniMaxAI/MiniMax-M2.7.yaml` | I-227 | minimax-m3 | — | #52849 |
| `MiniMaxAI/MiniMax-M2.yaml` | I-127 | minimax-m3 | — | #51203 |
| `MiniMaxAI/MiniMax-M2.yaml` | I-227 | minimax-m3 | — | #52849 |
| `MiniMaxAI/MiniMax-M3.yaml` | I-127 | minimax-m3 | — | #51203 |
| `MiniMaxAI/MiniMax-M3.yaml` | I-227 | minimax-m3 | — | #52849 |
| `Qwen/Qwen-Image.yaml` | I-056 | qwen3-omni | — | #52560 |
| `Qwen/Qwen-Image.yaml` | I-075 | qwen3.8-flash-next | — | #53896 |
| `Qwen/Qwen-Image.yaml` | I-087 | qwen3-omni | — | #52786 |
| `Qwen/Qwen-Image.yaml` | I-092 | qwen3.5 | — | #48850 |
| `Qwen/Qwen-Image.yaml` | I-093 | qwen3.5 | — | #47640 |
| `Qwen/Qwen-Image.yaml` | I-111 | qwen3-vl | — | #54380 |
| `Qwen/Qwen-Image.yaml` | I-122 | qwen3-omni | — | #50858 |
| `Qwen/Qwen-Image.yaml` | I-150 | qwen | — | #52539 |
| `Qwen/Qwen-Image.yaml` | I-158 | qwen3 | — | #52197 |
| `Qwen/Qwen-Image.yaml` | I-186 | qwen3.6 | — | #52676 |
| `Qwen/Qwen-Image.yaml` | I-369 | qwen | — | #51169 |
| `Qwen/Qwen2.5-32B.yaml` | I-150 | qwen | — | #52539 |
| `Qwen/Qwen2.5-32B.yaml` | I-369 | qwen | — | #51169 |
| `Qwen/Qwen2.5-VL-72B-Instruct.yaml` | I-150 | qwen | — | #52539 |
| `Qwen/Qwen2.5-VL-72B-Instruct.yaml` | I-369 | qwen | — | #51169 |
| `Qwen/Qwen2.5-VL-7B-Instruct.yaml` | I-150 | qwen | — | #52539 |
| `Qwen/Qwen2.5-VL-7B-Instruct.yaml` | I-369 | qwen | — | #51169 |
| `Qwen/Qwen3-1.7B.yaml` | I-056 | qwen3-omni | — | #52560 |
| `Qwen/Qwen3-1.7B.yaml` | I-075 | qwen3.8-flash-next | — | #53896 |
| `Qwen/Qwen3-1.7B.yaml` | I-087 | qwen3-omni | — | #52786 |
| `Qwen/Qwen3-1.7B.yaml` | I-092 | qwen3.5 | — | #48850 |
| `Qwen/Qwen3-1.7B.yaml` | I-093 | qwen3.5 | — | #47640 |
| `Qwen/Qwen3-1.7B.yaml` | I-111 | qwen3-vl | — | #54380 |
| `Qwen/Qwen3-1.7B.yaml` | I-122 | qwen3-omni | — | #50858 |
| `Qwen/Qwen3-1.7B.yaml` | I-150 | qwen | — | #52539 |
| `Qwen/Qwen3-1.7B.yaml` | I-158 | qwen3 | — | #52197 |
| `Qwen/Qwen3-1.7B.yaml` | I-186 | qwen3.6 | — | #52676 |
| `Qwen/Qwen3-1.7B.yaml` | I-369 | qwen | — | #51169 |
| `Qwen/Qwen3-14B.yaml` | I-056 | qwen3-omni | — | #52560 |
| `Qwen/Qwen3-14B.yaml` | I-075 | qwen3.8-flash-next | — | #53896 |
| `Qwen/Qwen3-14B.yaml` | I-087 | qwen3-omni | — | #52786 |
| `Qwen/Qwen3-14B.yaml` | I-092 | qwen3.5 | — | #48850 |
| `Qwen/Qwen3-14B.yaml` | I-093 | qwen3.5 | — | #47640 |
| `Qwen/Qwen3-14B.yaml` | I-111 | qwen3-vl | — | #54380 |
| `Qwen/Qwen3-14B.yaml` | I-122 | qwen3-omni | — | #50858 |
| `Qwen/Qwen3-14B.yaml` | I-150 | qwen | — | #52539 |
| `Qwen/Qwen3-14B.yaml` | I-158 | qwen3 | — | #52197 |
| `Qwen/Qwen3-14B.yaml` | I-186 | qwen3.6 | — | #52676 |

…and 582 more in `findings.json`.
