# MM-005 Document/Chart/PDF model-evaluation repeatability protocol v1

> Status: protocol frozen before any second model import or call. The replay
> output is absent and the registered replay has not been consumed.

## Decision

This gate freezes one outcome-neutral, eval-only replay of the unchanged
MM-005 Document/Chart/PDF candidate against the unchanged 32-case synthetic
suite. It is a new measurement lifecycle, not a retry of the consumed baseline.
It does not train, edit, copy, merge, or save the Adapter or base model.

The canonical preregistration is
`configs/mm005_document_chart_pdf_model_evaluation_repeatability_protocol_v1.json`.
It is 47,974 bytes with SHA-256
`4c5186cbfa542125d4f2b96dae14e31955effa330c42951f993413d276962ed7`.
The model-free builder reconstructs those exact bytes from authenticated
sources and baseline artifacts.

```text
protocol gate=MM-005-document-chart-pdf-model-evaluation-repeatability-protocol-v1
execution gate=MM-005-document-chart-pdf-model-evaluation-repeatability-execution-v1
result review=MM-005-document-chart-pdf-model-evaluation-repeatability-result-review-v1
failure classification=MM-005-document-chart-pdf-model-evaluation-repeatability-failure-classification-v1
experiment=mm005-document-chart-pdf-model-eval-repeatability-v1
run=mm005-document-chart-pdf-model-eval-replay-r1
output=work/evaluation-runs/mm005-document-chart-pdf-model-eval-repeatability-v1
```

At freeze, baseline execution facts are true, but replay execution,
same-machine repeatability, training/resource repeatability, quality, safety,
cross-machine, Serving, promotion, and Runtime claims remain false.

## Authenticated baseline

The protocol authenticates model-evaluation freeze commit
`3be0083c3197111d57a4a5e5f70feced9f2c96f9` and result-review merge commit
`056eb8d050eb0f0491ff21a07bd5b7716abf7eb8`. It invokes the existing strict
result validator before accepting the reference observation.

| Reference artifact | Bytes | SHA-256 |
|---|---:|---|
| Baseline preregistration | 58,414 | `cdb8d1ea09221763d87cd79ba752d9af8264ce49b7cf600eed338a073a04561b` |
| Attempt owner | 656 | `ca9e420fbce5582cab5944e0c290e569f97cad85ad3a5cf9e3c53aa13989d00b` |
| Evaluation candidate | 32,190 | `e26f6a9ca03e826f627ae90aca5b2fdcf5bbed770d9752aa9ba74982ed7d12ea` |
| Predictions | 18,543 | `f9a545175688451fc5025eb1e90a1e1354a59c536887a54fe62deb80a019fff7` |
| Evidence | 7,495 | `5e330dde1debe7a207638d164aade8ab2c63fbcd8149b3178d64a16afd0fc78e` |
| Result review | 15,235 | `7cc4990f900787123f078d2387855e4708b5eadb8d6705bb6364d8cab2f935a7` |

Twelve source receipts cover the baseline contract, builder, runner and result
validator; the repeatability contract, builder and runner; the inherited
attempt guard, model dependency and generation runners; and the independent
Adapter/Verifier contract and implementation. The formal runner also verifies
that those source receipts are the bytes stored at the supplied merged freeze
commit.

## Unchanged candidate and suite

The only candidate remains the pinned Qwen2.5-VL base revision plus the exact
read-only `mm003-qlora-sft-v2` Adapter in NF4-base-plus-LoRA execution form.
The registered Python/CUDA/library/GPU environment, all model and Adapter
receipts, 32 record IDs, 32 image payloads, case order, prompt projections,
strict compiler, deterministic Verifier, metric definitions, generation
parameters, seed, and limits are copied from the authenticated baseline.

Gold outputs, record identity, receipts, Verifier metadata, and repository
paths remain outside model-facing payloads. The replay cannot substitute an
alternate model, Adapter, environment, prompt, image, compiler, Verifier, or
generation configuration.

## One-shot execution contract

The replay registers exactly:

| Counter or constraint | Frozen value |
|---|---:|
| Fresh base loads | 1 |
| Independent read-only Adapter loads | 1 |
| Ordered generation calls | 32 |
| Retries | 0 |
| Network attempts | 0 |
| Training / optimizer / backward operations | 0 |
| Adapter / model / tensor writes | 0 |
| Elapsed-time cap | 1,800 seconds |
| Peak allocated/reserved GPU-memory cap | 16.5 GB |

The fixed output directory must be absent. An exclusive owner receipt is first
written in a random same-parent staging directory; its atomic rename to the
fixed path consumes the one attempt. Before consumption, a failed preflight
may be corrected. After consumption, deletion, reuse, overwrite, and retry are
forbidden regardless of whether the terminal is success or failure.

Formal execution requires the supplied freeze commit, local `master`, and
`origin/master` to be identical. It revalidates the canonical preregistration,
source receipts, baseline evidence, model/Adapter inputs, dataset bytes,
isolated Python invocation, dependency wheel, and registered environment
before the first generation call. Model and dataset file identities remain
locked and are checked again after generation.

## Layered outcome comparison

The comparison is deliberately outcome-neutral. Equality is an observation,
not a measurement-completion threshold.

| Layer | Comparison | Drift evidence |
|---|---|---|
| Raw output | exact UTF-8 bytes per record | exact count, aggregate digests, record IDs |
| Compiled output | exact type-strict canonical JSON after recompilation | exact count, aggregate digests, record IDs |
| Verifier verdict | exact recomputed canonical JSON | exact count, aggregate digests, record IDs |
| Metrics | exact recomputed structured equality | reference/replay values, digests, metric names |
| Generated-token count | exact integer per record | exact count, aggregate digests, record IDs |

Behavioral drift must be preserved and still routes a complete within-cap run
to independent result review. It never authorizes an automatic retry.

Resource observations receive reference, replay, absolute-delta, and exactness
diagnostics, but resource equality is not a repeatability gate. The inherited
caps remain an integrity gate. This protocol cannot establish resource
repeatability from two observations.

## Terminal and failure evidence

A successful terminal contains only:

1. `attempt-owner.json`;
2. `evaluation-candidate.json`;
3. `predictions.json`;
4. `evidence.json`.

The candidate is rebuilt from raw outputs, records, and images. Predictions
are rebuilt from the candidate. Evidence recomputes both reference and replay
metrics and every registered comparison layer.

A consumed incomplete attempt instead writes `failure.json`. Its stage names
separate output claim, dependency/environment validation, combined model-load/
generation, candidate persistence, scoring, predictions persistence, and
evidence persistence. Completed record IDs must be an exact case-order prefix;
load/generation counters must agree with that prefix. Any referenced candidate
or predictions artifact is parsed canonically and independently rebound before
its receipt is accepted. Exception messages, tracebacks, absolute paths, and
secrets are never serialized.

## Formal gate and claim boundary

The ten required gates cover protocol and baseline integrity, unchanged
candidate/environment and evaluation inputs, one offline replay, attempt
ownership, candidate/predictions binding, complete layered comparison,
resource caps, and fail-closed claims.

If all ten pass, execution evidence may set replay execution and formal
measurement completion true. It must keep
`same_machine_fixed_suite_repeatability_established=false` until independent
model-free result review verifies the persisted terminal. That review may set
the narrow claim true only if all five registered behavioral layers are exact.

Neither an exact result nor a complete drift result establishes training or
resource repeatability, repeat variance, cross-machine reproducibility,
generalized quality, safety, real/external document behavior, Serving,
promotion, model execution authority, or Runtime eligibility.

## Validation at freeze

The 16 focused model-free tests cover exact lineage and protocol construction,
freeze claims, all five comparison layers, raw-only drift, compiled/Verifier/
metric drift, token-count drift, resource diagnostics and caps, owner/candidate
tampering, authenticated failure progress, terminal-artifact binding, feature-
branch rejection, consumed-output preguard order, no-training AST checks, and
one fake delegated 32-call lifecycle. All 16 pass without loading the model.

The complete MM-005 chain passes 107/107. Ruff, strict Mypy on the contract/
builder/runner, `py_compile`, builder `--check`, the unified-gate protocol
probe, and `git diff --check` pass. Local CPython 3.11.15, 3.12.12, and 3.13.7
each pass the unified 767-test gate with four expected Windows privilege skips,
61 audited source files, and `valid=true`.

## Registered next action

The protocol must first merge with all required checks, review state, and
conflict state clear. Only then may this command be invoked once from aligned
merged `master`, substituting the exact merge commit:

```powershell
.\work\training-env\Scripts\python.exe -I -B -X pycache_prefix=NUL `
  .\scripts\run_mm005_document_chart_pdf_model_evaluation_repeatability.py `
  --protocol-freeze-commit <exact-merged-protocol-commit>
```

The command must not run from a feature branch and must never run a second time
after the output is claimed. Success routes to
`MM-005-document-chart-pdf-model-evaluation-repeatability-result-review-v1`;
an incomplete or integrity-failed consumed attempt routes to the registered
failure-classification gate.
