# MM-003: local small-VLM baseline protocol v1

## Decision

The outcome-neutral local baseline protocol was frozen on 2026-08-17 before
any MM-002 evaluation output was generated. The exact next gate is
`MM-003-local-small-vlm-baseline-execution-v1`: one fresh model load, one
complete nine-case run, nine generation calls in frozen case order, and zero
retries.

No formal model result exists at this protocol gate. In particular,
`baseline_executed=false`, `model_evaluated=false`, `training=false`, and
`runtime_eligible=false` remain frozen claims.

After this protocol was merged unchanged, its one registered execution attempt
reached scoring after all nine generation calls but failed with
`EMPTY_METRIC_DENOMINATOR`; no result artifact was written and no retry was
performed. That later outcome is recorded separately in the
[failure classification](MM-003-local-small-vlm-baseline-failure-classification-v1.md)
and does not rewrite this preregistration.

## Model and backend selection

The protocol pins:

```text
repo_id=Qwen/Qwen2.5-VL-3B-Instruct
revision=66285546d2b821cf421d4f5eb2576359d3770cd3
architecture=Qwen2_5_VLForConditionalGeneration
backend=transformers 4.49.0
torch=2.6.0+cu124
dtype=bfloat16
attention_implementation=sdpa
device=NVIDIA GeForce RTX 4090 Laptop GPU
```

The model is inside the registered 0.5B-3B band and its model card explicitly
targets visual localization and agent/computer-use tasks. `vLLM`, `inspect-ai`,
`uv`, FlashAttention, and bitsandbytes were absent locally, so the protocol
uses the already compatible Transformers backend rather than introducing an
unvalidated serving stack for a nine-case correctness baseline.

The model's `qwen-research` license permits non-commercial research or
evaluation only. This local gate does not authorize commercial use, serving,
promotion, redistribution, or Runtime integration. A separate license and
release decision would be required before any such use.

All 14 repository files are pinned by exact local SHA-256 and byte count. The
two weight shards additionally match the Hub LFS SHA-256 values:

| Weight | Bytes | SHA-256 |
|---|---:|---|
| `model-00001-of-00002.safetensors` | 3,982,649,232 | `sha256:41a8895c164b4d32bae6b302f4603fcbc1797f32dafa45c7e9bcda23c6755df8` |
| `model-00002-of-00002.safetensors` | 3,526,688,744 | `sha256:365531ff8752420e89dee707b79d021fb2d6e25abafe486f080555a4fe6972e4` |

## Frozen evaluation input

The protocol reuses the unchanged nine-family MM-002 eval split:

```text
suite file SHA-256=sha256:c59ea8314cad0ae936fadd6648cc270e3332d40115ed1ca6f9c00730c85c7b2e
suite canonical SHA-256=sha256:0774ae2c4d835ab613f46344b33ec0dac5ec1bf12d38db72fca2fdde94431b00
prediction schema SHA-256=sha256:a4ab293cb0831475899d208b06a4a7c2835405a112538695f83ac3a595357b46
```

Each case runs only in its originally registered observation mode, giving
three UIA-only, three screenshot-only, and three fused cases. This compares
the three frozen groups without manufacturing missing modalities from gold.
The prompt contains a filtered `model_input`; it cannot contain `gold` or raw
`screenshot_regions`. Six full-frame 1280x900 PNGs are rendered only from the
frozen model-input screenshot regions with a standard-library, host-font-free
renderer. UIA-only cases receive no image.

The compiled output uses the existing closed MM-002 prediction schema. It
extracts the first JSON object, performs strict validation without type
coercion, and deterministically converts invalid output to
`disposition=fallback, reason=model_output_invalid`. Raw output remains in the
registered run artifact.

## Outcome-neutral measurement protocol

Generation is fixed at `do_sample=false`, `temperature=null`,
`repetition_penalty=1.05`, `max_new_tokens=256`, `use_cache=true`,
`use_fast=false`, and seed `20260817`. Model materialization may use the
network before execution; the run itself sets the Hugging Face and Transformers
offline controls and requires `local_files_only=true`.

The report records overall MM-002 metrics plus per-observation-mode task
success proxy, candidate steps, fallback rate, and latency. It also records
overall elapsed time and CUDA allocated/reserved memory. Registered caps are:

| Resource | Cap |
|---|---:|
| elapsed time | 1,200 seconds |
| peak GPU allocated memory | 16,500,000,000 bytes |
| peak GPU reserved memory | 16,500,000,000 bytes |

No quality threshold is registered. The formal gate asks whether the exact
baseline completed with integrity, offline execution, valid compiled records,
zero retries, and resource compliance. Poor accuracy or all-fallback output
would remain reportable baseline quality rather than justify changing the
protocol after observing results.

## Frozen protocol artifacts

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `configs/mm003_multimodal_gui_action_model_baseline_v1.json` | 11,151 | `sha256:0046143f2c8badb5b2eaa809ac4c7abce81d1c0a5156fe2668b4e5cf9668aa10` |
| `src/fullcycle_bridge/mm003_baseline_protocol.py` | 29,420 | `sha256:e8ed98ed2f90c7001aa93cff15093288cdca3bdb35544216dbdefa648d80e9ef` |
| `scripts/run_mm003_multimodal_gui_action_baseline.py` | 31,983 | `sha256:42cc765d6d698a539123dc341245e7df379bdc67c4d312aaef22131752cf3c84` |

The config also binds the six PNG paths, bytes, hashes, the frozen scorer
source, every model file, exact environment, prompt, compiler, measurement
set, resource caps, constraints, and next gate.

## Compatibility smoke and validation

A pre-freeze smoke used one unrelated blank 512x512 synthetic image and asked
for the word `READY`; it did not load any MM-002 case. The corrected explicit
processor/generation settings produced `READY` in 4.989717400007066 seconds
with two generated tokens, peak CUDA allocated memory 7,953,781,760 bytes, and
peak reserved memory 8,311,013,376 bytes. This proves only that the pinned
model/backend can load and generate on the local GPU.

The focused protocol suite passes 8 tests. The local CPython 3.11.15, 3.12.12,
and 3.13.7 unified offline gates each pass 502 tests with four Windows
symlink-privilege skips, `valid=true`, and 43 audited source files. Ruff,
strict mypy, `py_compile`, preregistration byte recomputation, model manifest
hashing, deterministic PNG recomputation, and visual inspection pass.

## What this proves and does not prove

This gate proves the experiment was specified before formal eval execution and
that the selected model/backend is locally loadable. It does not prove any
MM-002 model metric, repeated-run variance, cross-machine reproducibility,
QLoRA training or independent Adapter loading, generalization, real GUI
capture, direct execution, serving, promotion, commercial eligibility, or
Runtime readiness.

That exact action was attempted once after merge and did not pass. A separate
`MM-003-local-small-vlm-baseline-recovery-protocol-v2` has since frozen the
outcome-neutral scoring and persistence recovery without changing the model,
inputs, prompt, compiler, generation settings, or eval answers. That separately
preregistered v2 execution later completed once and established a negative
9/9-fallback baseline. The current next action is
`MM-003-small-vlm-post-training-protocol-v1`.
