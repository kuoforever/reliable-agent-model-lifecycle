# MM-003 local small-VLM baseline recovery protocol v2

> **Decision: FROZEN LOCALLY — merge before the one registered v2 execution.**

## Scope

This outcome-neutral recovery protocol responds only to the v1
`EMPTY_METRIC_DENOMINATOR` scoring-totality failure. It does not tune against
model output. The model, exact revision and 14-file manifest, MM-002 suite,
six deterministic screenshots, prompt, compiler, generation settings,
environment lock, resource caps, nine-case order, and zero-retry rule are
byte- or value-identical to v1.

The 13,349-byte preregistration is
[`configs/mm003_multimodal_gui_action_model_baseline_v2.json`](../configs/mm003_multimodal_gui_action_model_baseline_v2.json),
with SHA-256
`369c813dee44b14c6022eb90739bcd37f9f8de472e60a8cee88682454d135403`.
It binds six sources: the frozen v1 contract/runner/scorer and the separate v2
contract/runner/scorer. It also binds the 4,480-byte v1 failure classification
with SHA-256
`fc8ef58286f425c03e8f20148c1b2b014c29be4468b61f8c0e650f507ec2dce6`.

## Scoring recovery

All fixed-suite task metrics retain the v1 positive-denominator requirement.
Only `prediction_coordinate_ref_disagreement_rate` is
prediction-dependent: its denominator counts predictions that contain both a
non-null `ref` and `bbox`. When that cohort is empty, v2 returns:

```json
{"correct":0,"total":0,"value":null,"status":"not_applicable"}
```

For a non-empty cohort, the value and shape remain identical to v1. The
existing synthetic scorer probe reproduces every v1 metric value under v2,
apart from the explicitly bumped `report_version=2`. An all-fallback
prediction set now scores completely while core Grounding Accuracy remains
`0/5` and Action Accuracy remains `0/9`; `not_applicable` is not interpreted
as success.

## Persistence recovery

The v2 output directory must be absent before model load. After the frozen
nine generation calls complete, the runner creates it once and writes two
exclusive artifacts before invoking the scorer:

1. the run artifact, including raw model output, compiled output, per-case
   latency, and aggregate CUDA resources; and
2. the closed-schema compiled predictions artifact.

If scoring raises, the runner writes a separate failure receipt that binds
those two candidate artifacts and keeps all model-evaluated, promotion, and
Runtime claims false. If scoring succeeds, it writes the success evidence
after all gates recompute. Neither path overwrites an artifact.

## Formal gate and boundaries

The formal gate remains quality-neutral. It requires protocol/model/input/
environment integrity, one complete nine-call run, zero retries, offline
execution, resource caps, prediction schema validity, total diagnostic
scoring, pre-score candidate persistence, and the scoring-failure receipt
policy. No minimum quality threshold was added after observing v1.

At this protocol gate, `baseline_executed=false`, `model_evaluated=false`,
`training=false`, `artifact_promotion_allowed=false`, and
`runtime_eligible=false`. No Runtime, MCP, Desktop, serving, commercial-use,
or direct-execution authority is added. Cross-machine reproducibility remains
unestablished.

## Validation and next action

The eight focused recovery tests, Ruff, strict mypy, `py_compile`, exact model
and source hashing, and preregistration byte recomputation pass. The unified
offline gate passes 514 tests with `valid=true` and 46 audited source files on
CPython 3.12.12; PR CI must independently cover 3.11, 3.12, and 3.13.

The single next gate is `MM-003-local-small-vlm-baseline-execution-v2`. After
this protocol is merged unchanged, execute it once from the merge commit with
one fresh load, nine ordered calls, zero retries, and offline inference. A v2
run is a newly preregistered experiment, not a retry of v1.
