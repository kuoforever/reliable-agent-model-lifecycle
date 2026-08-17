# MM-003 local small-VLM baseline failure classification v1

> **Result: COMPLETE LOCALLY — the first registered execution did not pass;
> no model metric or promotion claim is established.**

## Observed outcome

The v1 protocol was merged as commit
`759a4ea2cbc6b45c78451bcbcdf2c26271c7af78` before execution. The one
registered local attempt then loaded the exact pinned Qwen2.5-VL-3B snapshot
and reached `score_predictions` after the exhaustive frozen nine-case loop.
The scorer raised:

```text
EMPTY_METRIC_DENOMINATOR at $report.metrics
```

The failing metric was
`prediction_coordinate_ref_disagreement_rate`. Its denominator increases only
when a compiled prediction contains both a non-null `ref` and `bbox`. No
compiled prediction met that condition, which is a valid model-output shape
for a prediction-dependent diagnostic even though the fixed MM-002 suite has
non-empty denominators for its core task metrics.

This is classified as
`post_generation_scoring_empty_optional_metric_denominator` in category
`scoring_contract_totality`. It is not a CUDA, checkpoint-load, or model-file
failure.

## Evidence boundary

The 4,480-byte canonical failure artifact is
[`baseline/mm003-qwen2.5-vl-3b-baseline-v1-failure-classification.json`](../baseline/mm003-qwen2.5-vl-3b-baseline-v1-failure-classification.json),
with SHA-256
`fc8ef58286f425c03e8f20148c1b2b014c29be4468b61f8c0e650f507ec2dce6`
and internal report digest
`sha256:41f06fb7f7d7a2d586dab8f50118143e5e58d39069ccc54a8339811f48649316`.
It binds the exact v1 preregistration and the frozen contract, runner, and
scorer source hashes.

Reaching the scorer proves by exact runner control flow that the fresh load and
nine generation calls completed. This is explicitly marked as control-flow
inference, not externally attested process telemetry. The v1 runner writes all
three registered artifacts only after scoring, so the exception left the
output directory absent. Raw model outputs, compiled predictions, per-case
latency, aggregate CUDA resources, and MM-002 metrics are not recoverable and
are not reconstructed.

Therefore `formal_gate_passed=false`, `baseline_executed=false`,
`model_evaluated=false`, `artifact_promotion_allowed=false`, and
`runtime_eligible=false`. No retry was performed.

## Locked recovery protocol

The single next gate is
`MM-003-local-small-vlm-baseline-recovery-protocol-v2`. It must freeze, merge,
and validate a new outcome-neutral protocol before another model run. The new
protocol may change only the scoring/persistence failure boundary:

- represent a zero denominator for the prediction-dependent diagnostic as
  explicit `not_applicable`, while core fixed-suite denominators remain
  fail-closed;
- persist raw and compiled outputs before scoring; and
- persist a failure receipt if scoring raises.

The model, revision, synthetic inputs, prompt, compiler, generation settings,
and eval answers remain unchanged. This prevents post-hoc tuning against the
observed failure. A future v2 execution is a new preregistered gate, not a
retry of v1.

## Reproduction

```powershell
python -I .\scripts\classify_mm003_baseline_failure.py --check
python -I .\scripts\validate_offline.py
```

The focused four tests and the unified 506-test gate pass locally. The unified
gate reports `valid=true` and audits 44 source files. Ruff and artifact
recomputation pass. This remains same-machine failure evidence; it does not
establish cross-machine reproducibility, serving readiness, commercial
eligibility, direct execution authority, or Runtime integration.
