# MM-003 small-VLM post-training failure classification v1

> **Result: COMPLETE LOCALLY — the registered v1 execution failed before the
> first model forward; no retry or post-training result is authorized.**

## Observed outcome

The hardened v1 protocol was merged as commit
`a882e6096a87e475511890be9fc804a468143868` before execution. The exact local
snapshot, preregistration, ten sources, dependency wheel, fixtures, model
manifest, and locked environment passed preflight. The one registered
execution then entered `training` and wrote this fail-closed receipt:

```text
stage=training
exception_type=MM003ProtocolError
retry_count=0
formal_gate_passed=false
```

The 897-byte byte-identical tracked receipt is
[`baseline/mm003-qwen2.5-vl-3b-qlora-sft-v1-failure.json`](../baseline/mm003-qwen2.5-vl-3b-qlora-sft-v1-failure.json),
with SHA-256
`8c82455b406c66a038deaaadeb9251b9eb626145a5f31d36b04d5ad7d10c72d9`.
The formal output directory contains only the original `failure.json`; no
Adapter, training-run, predictions, or evidence artifact exists.

## Deterministic root cause

Epoch 1 uses `Random(20260818)` to shuffle the 18 training records. The first
zero-based index is 17, so the first record is `pt-train-018/fused`. That
record's mode and channels are internally valid. The failure occurs because
the post-training `render_training_input` delegates to the MM-002 baseline
`filtered_model_input`, whose frozen `CASE_MODES` registry contains only
`ground-001` through `ground-009`.

A model-free static recomputation calls the same renderer for all 18 training
and nine validation records. All 27 fail with:

```text
CASE_MODE_MISMATCH at $.case
```

The mismatch is therefore an integration error in the training prompt
contract, not an invalid `fused` fixture, CUDA failure, checkpoint failure, or
QLoRA-backend failure. The first record fails before processor encoding,
model forward, loss, backward, optimizer step, Adapter save, or MM-002 eval.

The receipt itself stores only the safe exception type and stage, not the
exception code or location. The code and location above are explicitly a
deterministic static reproduction plus control-flow inference, not external
process telemetry or a field recovered from the receipt.

## Evidence boundary

The 15,877-byte derived classification is
[`baseline/mm003-qwen2.5-vl-3b-qlora-sft-v1-failure-classification.json`](../baseline/mm003-qwen2.5-vl-3b-qlora-sft-v1-failure-classification.json),
with SHA-256
`66b9e8352caacd1a10e750a222ce2a0a7994df385e23e31dbc76a68b6109aef6`
and internal report digest
`sha256:85fddade5e6a3c665771c6cb74c5e610f003817b3eddf5a21f1b2a070ea1dd53`.
It binds the exact 17,601-byte preregistration, all ten frozen protocol source
receipts, the raw failure receipt, both actual tracked fixture receipts,
deterministic record order, and static 27-record reproduction.

The execution lifecycle was attempted and consumed, but
`training_executed=false`, `adapter_created=false`,
`adapter_independently_loadable=false`, `model_evaluated=false`,
`quality_improved=false`, `promotion_eligible=false`, and
`runtime_eligible=false`. Model/LoRA setup progress is recorded only as
control-flow inference; it is not a successful training claim. No retry was
performed.

## Locked recovery protocol

The exact next gate is
`MM-003-small-vlm-post-training-recovery-protocol-v2`. It must be a separate,
outcome-neutral protocol with a new experiment, execution gate, merged freeze
commit, and output directory. It must not edit or delete the v1 protocol,
failure receipt, or run directory.

The classification locks the v2 identities exactly: execution gate
`MM-003-small-vlm-post-training-execution-v2`, experiment
`mm003-qwen2.5-vl-3b-qlora-sft-v2`, output directory
`work/training-runs/mm003-qlora-sft-v2`, and success-next gate
`MM-003-small-vlm-post-training-result-review-v2`. Its machine-readable
whitelist requires v2 to bind the v1 preregistration, raw receipt, and derived
classification; preserve the complete model, dependency/environment,
fixtures/targets, training, eval/reload, Adapter, resource-cap, claims, and
authority subtrees; and change only v2 identity/source/output, prompt
projection/receipts, render-totality, and next-gate fields.

The v2 change is limited to the failed boundary:

- add a post-training-specific `pt-*` case-to-mode registry while retaining
  the baseline `ground-*` invariant;
- render and validate all 27 actual input prompts before dependency or model
  load;
- freeze prompt receipts and prove that targets, family/repeat metadata, and
  raw screenshot regions remain excluded; and
- preserve the model, revision, datasets, targets, hyperparameters, MM-002
  eval, resource caps, zero-retry policy, and all authority boundaries.

A future v2 execution is a newly preregistered gate, not a retry of v1.

## Validation

The six focused classification tests and the CPython 3.11.15, 3.12.12, and
3.13.7 unified offline gates pass. Each unified gate runs 537 tests with four
expected Windows privilege skips, reports `valid=true`, and audits 48 source files. The
classifier also checks the ignored local receipt against the tracked raw copy
when the local formal directory is available; clean CI validates the tracked
canonical copy without requiring the GPU run directory.

```powershell
python -I .\scripts\classify_mm003_post_training_failure.py --check
python -I .\scripts\validate_offline.py
```
