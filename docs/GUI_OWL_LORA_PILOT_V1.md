# GUI-Owl 4B local LoRA pilot v1

The owner requested this bounded adaptation after the replacement screen.
It improves the narrow text/ref action interface, but **does not meet the
predeclared pilot threshold and is not eligible for live Runtime use**.
The original models, prior evaluation artifacts and Runtime remain unchanged.

## Result

| Measurement | Fresh base load | Fresh base + saved LoRA load |
|---|---:|---:|
| New same-family cases: exact expected action | 4/24 (16.7%) | 17/24 (70.8%) |
| New cases: compiler acceptance | 6/24 | 22/24 |
| Known contract regression: exact action | 1/8 | 5/8 |
| Known contract regression: compiler acceptance | 2/8 | 8/8 |
| Known synthetic visual regression | 8/8 | 8/8 |
| New contract generation median | 1.726 s | 2.374 s |
| Visual generation median | 1.617 s | 2.039 s |

The fixed gate requires at least 20/24 new exact responses, an improvement of
at least eight, and all eight visual cases. The +13 gain and visual conditions
pass; 17/24 misses the exact-response condition. Latency is descriptive for
these single sequential runs with an unmerged Adapter, not a serving SLA or
an intrinsic model speed comparison. No training images were used; unchanged
performance on eight easy synthetic visual tasks is limited regression evidence,
not proof that general visual ability was preserved.

All seven new-case failures are retained:

- Two unverified-content requests still propose `save`; the unchanged compiler
  rejects both with `CONTENT_NOT_VERIFIED`. No save is dispatched.
- Two stale observations return `stop` instead of the expected `observe`.
- Two valid write requests return `stop` instead of `type_text`.
- One reordered-control focus request returns `stop` instead of `click_ref`.

The five extra stops are safe abstentions under this interface but do not make
the expected progress. Compiler acceptance and exact task success are deliberately
separate. In particular, 22/24 accepted proposals is not 22/24 completed tasks.

## What was trained

Base: `mPLUG/GUI-Owl-1.5-4B-Instruct`, fixed revision
`3f061c2c562cc860c42bf32542a70e07a7ff4840`. The two BF16 weight files match
the publisher hashes already retained by probe v2. Each run hashes all cached
base files before and after execution; all four fresh loads use identical files.

Only language attention `q_proj` and `v_proj` receive LoRA: rank 8, alpha 16,
dropout 0, bias none, 2,949,120 FP32 trainable parameters across 36 layers.
The base model and visual encoder are frozen. This is BF16 LoRA, not QLoRA,
and does not train visual grounding or perform screenshot-based instruction tuning.

The deterministic synthetic corpus has 96 training, 12 validation and 24 test
examples covering 12 rule families. Splits have distinct request IDs, scopes,
epochs, labels and complete prompts, but intentionally share templates/rule
families. This is a same-distribution adaptation probe, not family-disjoint,
real-desktop or broad out-of-distribution evaluation. Prior eight contract and
eight visual tasks remain known regression controls, never training records.

Training uses assistant-only cross entropy, batch 1, accumulation 4, 48 fixed
AdamW steps (two passes over training data), initial peak learning rate 2e-4,
four warmup steps followed by linear decay, gradient clipping at 1, SDPA,
non-reentrant gradient checkpointing, and seed 41. Inputs exceeding 1,024
tokens are rejected rather than truncated. The final step is always saved;
validation/test results do not select checkpoints or trigger additional training.
The seed is recorded; byte-identical training reproducibility is not asserted.

A separate disposable four-example preflight performs one optimizer step and
is not saved or reused. Formal training takes 82.765 seconds including loading
and file verification; step 1 completes at 13.703 seconds and step 48 at 74.172.
Peak allocated memory is 9,893,293,056 bytes (9.21 GiB) on the RTX 4090 Laptop
16,376 MiB. First/last batch mean losses are 0.10244/0.01633 (different batches),
and final validation loss is 0.01875. Low token-averaged loss does not guarantee
correct free generation: most answer tokens merely copy IDs and epochs, while
an incorrect action token can determine failure.

Evaluation uses identical prompts and explicit greedy decoding before/after,
including `use_model_defaults=False` and `do_sample=False`, to avoid the
Transformers model-default inheritance issue found in the previous screen.
Four fresh model loads completed: disposable preflight, base evaluation,
formal training, and evaluation of the saved Adapter. There are 80 evaluated
generations total, no excluded evaluation attempts and no desktop actions.

## Artifacts and verification

- `configs/gui_owl_lora_pilot_v1.json`: frozen data, settings and rubric.
- `scripts/build_gui_owl_lora_pilot.py`: deterministic data construction.
- `scripts/run_gui_owl_lora_pilot.py`: isolated preflight, training and evaluation.
- `baseline/gui-owl-lora-pilot-v1.json`: raw event streams, prompts, outputs,
  token IDs, step losses, source/model/environment hashes and independently
  recomputed summary.
- `scripts/review_gui_owl_lora_pilot.py`: model-free scoring and consistency
  checks, including exact split membership and saved/reloaded Adapter identity.
- `requirements/gui_owl_lora_pilot.txt`: tested direct versions, not a complete
  transitive lock. The isolated Python 3.12 environment uses Torch 2.6.0+cu124,
  Transformers 4.57.6 and PEFT 0.17.1 without modifying the previous environments.

Local weights are retained at
`work/gui-owl-lora-v1/train/adapter/adapter_model.safetensors` (11,817,664 bytes),
with the PEFT config and model card alongside them. They are not published to
GitHub or the Hub; the public evidence contains their hashes. Loading requires
the fixed base plus this directory; there is no merged or quantized release.

```powershell
python -I -B scripts/review_gui_owl_lora_pilot.py --unit-tests --check
python -I -B scripts/review_gui_owl_lora_pilot.py --check --adapter-root work/gui-owl-lora-v1/train/adapter
```

For a deliberate reproduction, the training runner accepts `preflight`, `train`
and `eval`, with `--model`, optional `--adapter` for evaluation, and a fresh
`--output` directory. Existing directories are rejected. No GPU is needed for
the reviewer; it verifies retained consistency, not independent attestation of
execution. Runtime still owns live observation, grounding, approval and dispatch.

Local validation passes 13 new data/masking/evidence tests, 21 existing executor
tests and 10 prior screen tests (44 total), repository Ruff, current Adapter
file verification, and unchanged prior-screen evidence replay. The existing
Python 3.11/3.12/3.13 CI matrix gains the model-free pilot reviewer and its tests;
no CI model load or retraining is required.

The single next objective returns to the model-side native proposal adapter
and offline Runtime binding tests recorded in `PROJECT_STATUS.md`. Keep this
LoRA as an experimental contract candidate; do not promote it or start another
training campaign from this failed pilot threshold alone.
