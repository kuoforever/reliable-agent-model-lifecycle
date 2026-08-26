# MM-005 Document/Chart/PDF Adapter/Verifier implementation v1

## Outcome

The model-free Adapter/Verifier protocol merged through PR #54 as
`db8c6833f43c02a0b255c436558e0269a8bde3b4` after six Linux Python-matrix
checks passed with no review findings or conflicts. Its feature branch was
deleted locally and remotely before implementation began.

The registered
`MM-005-document-chart-pdf-adapter-verifier-implementation-v1` is now
implemented and executed against every frozen protocol vector without loading
or evaluating a model. The canonical implementation evidence is
`baseline/mm005-document-chart-pdf-adapter-verifier-implementation-v1.json`:
102,117 bytes with SHA-256
`d4cbe61cac4cff60c15e769c35e481ca93f71524b23bf0dad4ddf75095d17bf2`.
It binds five implementation/protocol source receipts, the exact protocol
merge commit and artifact, all consumed read-only upstream data, 32 Adapter
executions, and 160 compiler/Verifier executions.

PR #55 merged that exact implementation/evidence as
`ff52da51aba534b051f9e247518fb2d20d1db1e2` after six Linux Python-matrix
checks passed with zero reviews, comments, or review threads. Both feature-
branch copies were deleted before model-evaluation protocol work began.

## Implemented Adapter interface

`AdaptedInput` separates the model-facing transport from audit metadata:

| Channel | Contents | Model-visible |
|---|---|---:|
| `model_payload_json` | Canonical `instruction`, `observation`, `source_kind`, and `task_family_id` | Yes |
| `image_bytes` | Exact tracked PNG bytes selected by observation SHA-256 | Yes, as the visual channel |
| `audit_projection_json` | Record ID, image path/bytes/SHA-256 receipt, projection receipt, and no-authority declarations | No |

The Adapter validates the complete parent record contract, requires exactly
one safe repository-relative image path whose actual bytes match the record
image hash, and rejects missing, duplicate, tampered, non-byte, absolute, or
traversal bindings. Returned JSON accessors reconstruct fresh objects so a
caller cannot mutate the stored canonical projection. Gold, record/split/
provenance/Verifier metadata, and the real image path never enter the model
payload.

All 32 implemented audit projections reproduce the frozen protocol receipts
byte for byte. Their model payloads total 31,430 bytes; the 32 visual payloads
total 314,128 bytes.

## Implemented compiler and Verifier

The implementation is independent of the reference compiler/Verifier used to
freeze expected outcomes. It separately enforces the same strict JSON
contract: exact keys only, unique object keys and evidence refs, finite values,
UTF-8 and size limits, strict scalar types, registered identifiers, and exact
single-page scope. In particular, Python `bool` cannot substitute for an
integer page number, and an unpaired Unicode surrogate is invalid output.

The deterministic Verifier independently validates the compiled shape, then
applies NFC plus ASCII-space-trim exact answer matching, exact ordered evidence
matching, and exact page matching. It never uses a model or LLM judge.

| Conformance result | Count |
|---|---:|
| Frozen cases executed | 160 |
| Compiler-valid cases | 96 |
| Compiler-invalid cases | 64 |
| Joint-correct positive controls | 32 |
| Joint-incorrect negative controls | 128 |
| Projection mismatches | 0 |
| Compiler/verdict mismatches | 0 |

## Claim and authority boundary

`environment_adapter_implemented`, `environment_adapter_executed`,
`verifier_implemented`, and `verifier_executed` are now true in addition to the
already established generation/record/image/dataset claims. These statements
refer only to model-free execution over the 32 frozen synthetic records and
160 registered controls.

Model training/evaluation, quality improvement, safety, real or external
content, capture, Serving, promotion, Runtime repository/integration changes,
and Runtime eligibility remain false. Model output has no execution authority;
Runtime remains the sole policy, approval, WAL, grounding, budget, recovery,
and desktop-dispatch boundary.

## Validation evidence

Twelve implementation-focused adversarial tests cover all 32 projections and
160 Verifier vectors, independent differential compilation, extra/duplicate/
non-finite/oversized/type/Unicode failures, forged compiled objects, answer
normalization, image binding failures, immutable accessors, source/merge
lineage, evidence resealing, authority, and import boundaries. Together with
the data, generation, and protocol suites, 50 focused MM-005 chain tests pass.

Full-repository Ruff 0.15.22, scoped strict Mypy 2.3.0 on the three new typed
implementation/evidence/builder files, `py_compile`, builder `--check`, and
`git diff --check` pass. Local CPython 3.11.15, 3.12.12, and 3.13.7 each pass
the unified 724-test gate with four expected Windows privilege skips, 59
audited source files, and `valid=true`.

This establishes exact Adapter/Verifier conformance and deterministic evidence
reconstruction on the registered local Python matrix. It does not establish
model or training repeatability, cross-machine reproducibility, generalized
quality, safety, Serving, promotion, or Runtime eligibility.

## Downstream protocol and next gate

The registered `MM-005-document-chart-pdf-model-evaluation-protocol-v1` is now
frozen locally as 58,414 canonical bytes with SHA-256
`cdb8d1ea09221763d87cd79ba752d9af8264ce49b7cf600eed338a073a04561b`.
It binds the exact candidate/model lineage, 32 prompt projections, total
metrics, resource caps, one owner-marked attempt, and terminal success/failure
receipts before any model import or call.

Publishing that protocol is current. After a clean merge, the single next gate
is `MM-005-document-chart-pdf-model-evaluation-execution-v1`; no model execution
or training is authorized on the protocol feature branch.
