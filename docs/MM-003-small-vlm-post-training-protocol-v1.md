# MM-003 small-VLM post-training protocol v1

> Status: frozen locally before any registered training execution; merge this
> protocol before running `MM-003-small-vlm-post-training-execution-v1`.

## Decision

This gate freezes one outcome-neutral local QLoRA SFT lifecycle for the
existing `Qwen/Qwen2.5-VL-3B-Instruct` baseline. It does not require a quality
improvement. It requires the training inputs, model, environment,
hyperparameters, Adapter outputs, independent reload, unchanged MM-002
evaluation, resource caps, and failure semantics to be fixed before training.

The 17,601-byte preregistration is
`configs/mm003_small_vlm_post_training_protocol_v1.json`, with SHA-256
`e965d240bff9195daca2b2945ca91a567fc8b3f97f929e689aa79aff18292390`.
It binds ten protocol sources and all 14 files from model revision
`66285546d2b821cf421d4f5eb2576359d3770cd3`.

## Training-only inputs

The deterministic builder produces two reviewed synthetic fixtures:

| Split | Records | Optimizer use | Grid |
|---|---:|---|---|
| train | 18 | yes | two examples for every observation-mode × disposition pair |
| validation | 9 | no | one example for every observation-mode × disposition pair |

The three observation modes are `uia_only`, `screenshot_only`, and `fused`.
The three target dispositions are `act`, `reject`, and `fallback`. The 18
non-UIA examples have byte-reproducible 448×448 PNGs. Every target is accepted
by the unchanged strict MM-003 compiler before the fixture is eligible.

The isolation audit compares train plus validation against the frozen MM-002
eval across seven exact-identity classes:

- case IDs;
- family IDs;
- instructions;
- canonical complete model inputs;
- canonical targets versus eval gold records;
- screenshot SHA-256 values;
- train versus validation families.

All overlap sets are empty. The builder also records
`mm002_eval_gold_used=false`; the validation split is training-process
validation only and does not replace or modify MM-002.

## Locked local environment

The protocol retains the baseline Windows, Python 3.12.12, PyTorch
2.6.0+cu124, Transformers 4.49.0, PEFT 0.14.0, Accelerate 1.3.0, and RTX 4090
Laptop GPU pins. It adds bitsandbytes 0.50.1 from the exact Win64 wheel:

```text
bytes=37,961,070
sha256=86f76e8a3278fbbfc3fa0d79d1c4e706ebc214babd57f0ea30e2da509bbdaad5
```

`requirements/mm003_qlora_training.lock` is a separate MM-003 lock; the
historical Tool Router training lock remains unchanged.

Before freeze, an eval-independent blank-image smoke used the same NF4 and
gradient-checkpointing backend. It found 414 `Linear4bit` modules and
7,372,800 trainable LoRA parameters, produced a finite loss and a nonzero
finite LoRA gradient, and saved no Adapter. Peak CUDA allocated/reserved were
3,941,332,480 / 4,273,995,776 bytes. This proves local backend compatibility,
not training completion, Adapter loadability, MM-002 quality, or
reproducibility.

## Frozen QLoRA configuration

| Parameter | Value |
|---|---|
| Seed | `20260817` |
| Quantization | 4-bit NF4, double quantization, BF16 compute |
| LoRA | rank 16, alpha 32, dropout 0.05, bias none |
| Target modules | `q_proj`, `k_proj`, `v_proj`, `o_proj` |
| Epochs | 3 |
| Micro / accumulation / effective batch | 1 / 3 / 3 |
| Optimizer | AdamW, learning rate 0.0002, weight decay 0 |
| Schedule | cosine, warmup ratio 0.1 |
| Gradient checkpointing | enabled, non-reentrant |
| Gradient clipping | max norm 1.0 |
| Prompt loss | masked; assistant target only |

The runner checks that the multimodal prefix tokens are an exact prefix of the
full training sequence before masking. This prevents system, user, and image
tokens from silently entering the loss.

## Execution lifecycle

The registered execution is one zero-retry offline lifecycle:

1. Recompute the preregistration, model manifest, fixtures, screenshots,
   sources, dependency receipt, and MM-002 isolation audit.
2. Fresh-load the 4-bit base once, attach trainable LoRA modules, and run one
   three-epoch training execution.
3. Save exactly `README.md`, `adapter_config.json`, and
   `adapter_model.safetensors`; canonicalize the base model ID and revision so
   no machine-local snapshot path becomes authoritative.
4. Persist the training run, delete the training model and optimizer, collect
   Python garbage, and empty the CUDA cache.
5. Fresh-load the same 4-bit base, independently load the saved Adapter with
   `PeftModel.from_pretrained`, and run the unchanged nine-case MM-002 prompt,
   image, compiler, generation, and total-scoring path once.
6. Persist predictions and evidence. On any exception, write a path-redacted
   failure receipt and do not retry.

The total elapsed, peak allocated, and peak reserved caps are 1,800 seconds,
16,500,000,000 bytes, and 16,500,000,000 bytes. A formal pass is a measurement
pass: it establishes that the registered local lifecycle completed and the
Adapter reloaded. It does not automatically set `quality_improved=true`.

## Formal gates

All 12 gates are required:

1. protocol integrity;
2. exact model files;
3. locked environment;
4. training fixture integrity;
5. eval isolation;
6. offline single training run;
7. Adapter artifact integrity;
8. independent Adapter load;
9. unchanged MM-002 eval;
10. total scoring;
11. resource caps;
12. fail-closed claims.

At protocol freeze, all result claims remain false, including training
executed, Adapter created/loadable, model evaluated, quality improved,
repeatability, cross-machine reproducibility, portability, commercial use,
serving, promotion, and Runtime eligibility.

## Validation and exact next action

Focused protocol tests pass 10/10. Ruff, `py_compile`, deterministic fixture
rebuild/check, preregistration recomputation, and `git diff --check` pass. The
The CPython 3.11.15, 3.12.12, and 3.13.7 unified offline gates pass 528 tests with four expected
Windows privilege skips, `valid=true`, and 47 audited source files.

After this protocol is merged, execute exactly once:

```powershell
.\work\training-env\Scripts\python.exe scripts\run_mm003_qlora_post_training.py run `
  --model-snapshot <exact-pinned-local-snapshot> `
  --protocol-freeze-commit <merged-protocol-commit> `
  --output-dir <repo-root>\work\training-runs\mm003-qlora-sft-v1
```

Do not run that command from an unmerged tree, substitute eval data, retry a
failed formal attempt, or treat candidate model output as execution authority.
