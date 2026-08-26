# MM-005 Document/Chart/PDF model-evaluation protocol v1

## Outcome

The outcome-neutral read-only model-evaluation protocol is frozen before any
model import or call. Its canonical preregistration is
`configs/mm005_document_chart_pdf_model_evaluation_protocol_v1.json`: 58,414
bytes with SHA-256
`cdb8d1ea09221763d87cd79ba752d9af8264ce49b7cf600eed338a073a04561b`.

PR #55 first merged the independent Adapter/Verifier implementation and its
exact conformance evidence as
`ff52da51aba534b051f9e247518fb2d20d1db1e2`. All six Linux Python-matrix checks
passed, there were no reviews, comments, or review threads, and both feature-
branch copies were deleted before this protocol slice began.

The fixed evaluation output directory is absent. No attempt has been claimed,
no model has been imported or called, and no GPU measurement has occurred.

## Read-only candidate and lineage

The only registered candidate is the exact local
`Qwen/Qwen2.5-VL-3B-Instruct` revision
`66285546d2b821cf421d4f5eb2576359d3770cd3` plus the read-only
`mm003-qlora-sft-v2` Adapter. The model and Adapter receipts, MM-004 candidate
protocol/evidence/result review, MM-005 Adapter/Verifier evidence, merged
lineage commits, generated dataset tree, and all protocol source receipts are
closed inputs.

The registered execution environment is Python 3.12.12, PyTorch 2.6.0+cu124,
Transformers 4.49.0, bitsandbytes 0.50.1, and the RTX 4090 Laptop GPU. Training,
Adapter mutation, model/tensor saving, network access, and Runtime integration
are forbidden.

## Input and prompt isolation

All 32 synthetic records are measured once in frozen record-ID order: 24 train
and eight validation records across all four task families and source kinds.
The protocol binds 32 prompt projections whose model payload JSON totals 31,430
bytes and whose exact visual payloads total 314,128 bytes.

The model sees only:

- the fixed system prompt;
- canonical JSON with `instruction`, `observation`, `source_kind`, and
  `task_family_id`; and
- the exact Adapter-selected image bytes.

Gold output, record/split/provenance identity, Verifier metadata, receipts, and
real repository paths remain outside the model payload. Each projection binds
its canonical bytes and SHA-256 receipt before execution.

## Compiler, Verifier, and metrics

The strict compiler accepts only one UTF-8 JSON object with exactly `answer`,
`evidence_refs`, and `page_number`. Duplicate or extra keys, non-finite values,
duplicate references, invalid identifiers, wrong scalar types, oversized
output, and out-of-scope pages are invalid and score as wrong.

The independent deterministic Verifier uses no model judge. It registers total
metrics for compiler validity, answer exactness, ordered evidence exactness,
page exactness, joint exactness, compiler-invalid count, and every split, task
family, and source kind. Accuracy thresholds cannot change whether the formal
measurement completed; an unfavorable result must still be preserved and
reviewed rather than retried.

## Single-attempt execution contract

The future formal runner is registered for exactly one owner-marked run:

| Counter or cap | Frozen value |
|---|---:|
| Fresh base-model loads | 1 |
| Independent Adapter loads | 1 |
| Ordered generation calls | 32 |
| Retries | 0 |
| Network / training / backward / optimizer operations | 0 |
| Elapsed-time cap | 1,800 seconds |
| Peak allocated/reserved GPU-memory cap | 16.5 GB |

The attempt becomes consumed only when the fixed output directory is atomically
claimed with an exclusive owner receipt. Before that claim, a failed preflight
may be corrected; after it, retry is forbidden. Formal execution additionally
requires the exact protocol to be merged and the local `master`, `origin/master`,
and supplied freeze commit to be identical.

## Terminal evidence and failure handling

A successful terminal must persist the owner, evaluation candidate,
predictions, and evidence under the fixed output directory. A consumed failure
instead persists one mutually exclusive failure receipt. Failure receipts keep
only the safe exception type, stage, owner binding, and completed-record prefix;
they exclude exception messages, tracebacks, secrets, and machine paths.

Resource-cap failure preserves completed measurements but fails the integrity
gate. It does not authorize a retry or turn a partial result into evidence of
quality.

## Claim and Runtime boundary

At protocol freeze, generation/dataset validation and model-free Adapter/
Verifier conformance remain established. `attempt_consumed`,
`evaluation_executed`, `model_evaluated`, and `formal_measurement_complete` are
false. Model training, Adapter mutation, quality improvement, generalized
quality, safety, real-content behavior, Serving, promotion, and Runtime
eligibility are also false.

Model output has no execution authority. Runtime remains the sole policy,
approval, WAL, grounding, budget, recovery, and desktop-dispatch boundary; no
Runtime repository or integration change is authorized.

## Validation evidence at freeze

Fourteen focused adversarial tests cover byte-exact reconstruction, lineage,
prompt closure and gold/path isolation, fake-dependency 32-call lifecycle,
compiler/Verifier metric totality, wrong and invalid results, resource caps,
owner/failure receipts, artifact resealing, feature-branch formal rejection,
and absence of top-level model imports or write paths. The complete MM-005
focused chain passes 78 tests.

Ruff, scoped strict Mypy on the contract/builder/runner, `py_compile`, protocol
`--check`, and the unified-gate protocol probe pass. Local CPython 3.11.15,
3.12.12, and 3.13.7 each pass the unified 738-test gate with four expected
Windows privilege skips, 60 audited source files, and `valid=true`. These
checks prove the frozen measurement contract and deterministic reconstruction.
They do not prove model-load success, model quality, safety, same-machine
evaluation repeatability, cross-machine reproducibility, Serving, promotion,
or Runtime eligibility.

## Next gate

After this exact protocol merges with checks, review state, and conflicts clear,
the single next gate is
`MM-005-document-chart-pdf-model-evaluation-execution-v1`. It may consume the
one registered attempt from the aligned merged commit. A successful terminal
routes to result review; a consumed failure routes to failure classification.
