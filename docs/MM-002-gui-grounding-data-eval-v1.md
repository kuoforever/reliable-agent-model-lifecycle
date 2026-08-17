# MM-002: GUI grounding data and evaluation v1

## Decision

The local data/evaluation review completed on 2026-08-17. The repository now
contains a frozen nine-family synthetic GUI grounding eval split, closed suite
and prediction schemas, a strict standard-library validator/scorer, and one
deliberately imperfect synthetic probe report. No model was evaluated.

The suite is bound to:

```text
gui_grounding_eval_version=1
gui_grounding_prediction_version=1
report_version=1
multimodal_trajectory_schema_version=1
runtime_freeze_commit=324ff2fb5911e332ddb5c5f90eb41296e8faf7a9
multimodal_trajectory_schema_merge_commit=3e5908a7ba92d00facb48847915834c1f8fbca30
```

## Dataset and leakage boundary

The nine reviewed cases have unique case and family IDs and unique
instructions. Gold records are structurally separate from `model_input`; the
suite is frozen as `split=eval`, declares `training_use_prohibited=true`, and
cannot be accepted as training-eligible.

Coverage is recomputed from the records:

- grounding: ref, bbox, and fused;
- observation: UIA-only, screenshot-only, and fused;
- OCR: clean, missing, and noisy;
- perturbation: none, moved, occluded, stale ref, and coordinate/ref
  disagreement;
- outcomes: act, reject, and fallback.

Every case binds the MM-001 trajectory schema hash and frozen Runtime commit.
The scorer resolves refs and bboxes against a gold target catalog, applies the
fixed IoU threshold of 0.5, and accumulates mean IoU as exact rational
arithmetic before serialization.

## Frozen artifacts

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `schemas/gui_grounding_eval_suite_v1.schema.json` | 7,417 | `sha256:3d19ab18e53c94e3061cc713b9c56a5ac779429b7742486636eb5d35b076be43` |
| `schemas/gui_grounding_predictions_v1.schema.json` | 2,602 | `sha256:a4ab293cb0831475899d208b06a4a7c2835405a112538695f83ac3a595357b46` |
| `fixtures/gui_grounding_eval_v1/valid/suite.json` | 13,097 | `sha256:c59ea8314cad0ae936fadd6648cc270e3332d40115ed1ca6f9c00730c85c7b2e` |
| `fixtures/gui_grounding_eval_v1/valid/synthetic-probe-predictions.json` | 1,613 | `sha256:1a0ea1005290a5d3fafddfa147d6b3fe79f211a9298e0cf326aec6b176e2dd42` |
| `baseline/mm-002-gui-grounding-data-eval-v1.json` | 1,592 | `sha256:b25611cff7febbaccc01657423ef2d237bf7bd53f3d886b4e4b201fcf49bc2cc` |
| `fixtures/gui_grounding_eval_v1/fixture-metadata.json` | 2,807 | `sha256:cab240c0147a2c36f336b39a0be1f8a65da058deb4daa6906814f0719846adeb` |

The report also binds canonical suite digest
`sha256:0774ae2c4d835ab613f46344b33ec0dac5ec1bf12d38db72fca2fdde94431b00`
and canonical prediction digest
`sha256:c00ac7d6e2e9dc033f664f46d26030ef1bf959f8273413d50c7f96d863a3c2a9`.

## Synthetic probe metrics

The probe intentionally contains both correct and incorrect records:

| Metric | Exact result |
|---|---:|
| Grounding Accuracy | 4/5 = 0.80 |
| Mean IoU | 19/20 = 0.95 |
| Action Accuracy | 6/9 = 0.6666666666666666 |
| Tool Accuracy | 5/5 = 1.00 |
| Argument Exact Match | 4/5 = 0.80 |
| stale-ref rejection | 1/2 = 0.50 |
| coordinate/ref disagreement rejection | 0/1 = 0.00 |
| predicted coordinate/ref disagreement rate | 2/3 = 0.6666666666666666 |

These numbers are scorer test vectors, not model quality. In particular,
`producer_kind=synthetic_probe`, `model_predictions_declared=false`,
`model_evaluated=false`, and `synthetic_probe_only=true` are enforced by the
frozen report and offline gate. Even a future `producer.kind=model` only sets
the declarative `model_predictions_declared`; this scorer cannot attest model
execution by itself.

## Reproduction

```powershell
python -I -c "import runpy,sys; sys.path.insert(0, r'.\src'); runpy.run_path(r'.\tests\test_gui_grounding_eval.py', run_name='__main__')"
python -I .\scripts\validate_offline.py
```

The local CPython 3.11.15, 3.12.12, and 3.13.7 gates each passed 494 tests
with 4 Windows symlink-privilege skips, `valid=true`, and 42 audited source
files. The focused suite passed 26 tests with 1 Windows symlink-privilege
skip. Ruff, strict mypy, `py_compile`, independent Draft 2020-12 metaschema
and instance validation, frozen report recomputation, and artifact hash checks
passed. A final no-dependency wheel contains both GUI grounding modules and
the `fullcycle-gui-grounding-eval` console entry point.

## What this proves and does not prove

This closes only `MM-002-gui-grounding-data-eval-v1`. It proves the frozen
synthetic suite and deterministic scorer cover the registered categories and
fail closed on structural, linkage, leakage, geometry, prediction, and claim
drift. It does not establish VLM quality, generalization, real GUI capture,
real sanitization/redaction, training readiness, model execution,
cross-machine reproducibility, serving, promotion, or Runtime eligibility.

The exact next gate is `MM-003-multimodal-gui-action-model-v1`.
