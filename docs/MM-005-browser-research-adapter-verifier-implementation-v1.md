# MM-005 Browser Research Adapter/Verifier implementation v1

## Outcome

The model-free protocol merged through PR #67 as
`403cc240fec14d3d9123b6f207112a5290f4fc34` after the Linux Python 3.11,
3.12, and 3.13 checks passed with no review findings or conflicts. Its feature
branch was deleted locally and remotely before implementation began.

The registered `MM-005-browser-research-adapter-verifier-implementation-v1`
is now implemented and executed against every frozen protocol vector without
loading or evaluating a model. The canonical implementation evidence is
`baseline/mm005-browser-research-adapter-verifier-implementation-v1.json`:
195,994 bytes with SHA-256
`77634e6202354641eef84cf1640c17588e902c073f804b535dfb3ada52d09876`.
It binds five implementation/protocol source receipts, the exact protocol
merge commit and artifact, all consumed read-only upstream data, 32 Adapter
executions, and 224 compiler/Verifier/semantic executions.

PR #68 published this exact implementation as
`1177d5649952af6c04f713f5cfbbde47388e3769`. All six Linux Python-matrix
checks passed, there were no reviews, comments, review threads, or conflicts,
the signed squash merge tree exactly matched the implementation tree, and both
feature-branch copies were deleted.

## Implemented Adapter interface

`AdaptedBrowserResearchInput` separates model-facing transports from audit
metadata:

| Channel | Contents | Model-visible |
|---|---|---:|
| `model_payload_json` | Canonical `instruction`, static `observation`, `source_kind`, and `task_family_id` | Yes |
| `screenshot_payloads` | Exact PNG bytes in the record's source order | Yes, as visual channels |
| `source_snapshot_payloads` | Exact canonical source-snapshot bytes used to prove provenance bindings | No; audit only |
| `audit_projection_json` | Record ID, ordered source IDs, screenshot/snapshot path-byte-hash receipts, and no-authority declarations | No |

The Adapter validates the complete parent record contract. For every source it
requires exactly one safe repository-relative PNG whose actual SHA-256 equals
the observation and exactly one canonical source snapshot whose source,
identity, split, family, kind, template, and screenshot path match that
record. It rejects missing, duplicate, tampered, empty, non-byte, absolute,
drive-qualified, backslash, traversal, or NUL-containing artifact bindings.

Returned JSON accessors reconstruct fresh objects so callers cannot mutate the
stored canonical projection. Gold, record/split/provenance/Verifier metadata,
repository paths, and source-snapshot bytes never enter `model_payload_json`.
All 32 implemented audit projections reproduce the frozen protocol receipts
byte for byte. Their model payloads total 81,796 bytes; 68 ordered screenshot
payloads total 600,604 bytes; and 68 audit-only source snapshots total 118,742
bytes.

## Implemented compiler and Verifier

The implementation is independent of the reference compiler/Verifier used to
freeze expected outcomes. It separately enforces the exact two-key JSON
contract: `answer` plus ordered unique `citation_refs`, with unique object
keys, finite values, UTF-8 and size limits, strict scalar types, registered
identifier syntax, and no extra keys. Invalid output is deterministically
wrong.

The Verifier independently validates compiled-object shape, applies NFC plus
ASCII-space-trim exact answer matching and exact ordered citation matching,
then derives DOM-ref-to-source binding, minimum distinct-source coverage, and
latest-published-source freshness diagnostics. It never uses a model or LLM
judge.

| Conformance result | Count |
|---|---:|
| Frozen cases executed | 224 |
| Citation-semantics results recomputed | 224 |
| Compiler-valid cases | 160 |
| Compiler-invalid cases | 64 |
| Joint-correct positive controls | 32 |
| Joint-incorrect negative controls | 192 |
| Freshness latest-source-removal negatives | 8 |
| Projection/compiler/verdict/semantic mismatches | 0 |

## Claim and authority boundary

`environment_adapter_implemented`, `environment_adapter_executed`,
`verifier_implemented`, and `verifier_executed` are now true in addition to
the inherited generation/record/snapshot/screenshot/dataset claims. These
statements refer only to model-free execution over the 32 frozen synthetic
records and 224 registered controls.

Model training/evaluation, model-evaluation repeatability, quality improvement,
safety, prompt-injection safety, real or external content, live browser,
network, capture, Serving, promotion, cross-machine reproducibility, Runtime
repository/integration changes, and Runtime eligibility remain false. Page
content and model output have no execution authority; Runtime remains the sole
policy, approval, WAL, grounding, budget, recovery, and desktop-dispatch
boundary.

## Validation evidence

Thirteen implementation-focused adversarial tests cover all 32 projections and
224 Verifier vectors, independent differential compilation, citation/source/
freshness semantics, extra/duplicate/non-finite/oversized/type/Unicode
failures, forged compiled objects, answer normalization, screenshot/snapshot
binding failures, Windows/relative path safety, immutable accessors,
source/merge lineage, evidence resealing, authority, and import boundaries.

Full-repository Ruff 0.15.22, scoped strict Mypy 2.3.0 on the three typed
implementation/evidence/builder files, `py_compile`, builder `--check`, and
`git diff --check` pass. Local CPython 3.11.15, 3.12.12, and 3.13.7 each pass
the unified 852-test gate with four expected Windows privilege skips, 67
audited source files, and `valid=true`.

This establishes exact Adapter/Verifier conformance and deterministic evidence
reconstruction on the registered local Python matrix. It does not establish
model or training repeatability, cross-machine reproducibility, generalized
quality, safety, Serving, promotion, or Runtime eligibility. Clean PR
validation, merge, branch cleanup, and master alignment completed through PR
#68 before the next protocol freeze began.

## Next gate

The separate `MM-005-browser-research-model-evaluation-protocol-v1` is now
active and frozen locally as an outcome-neutral preregistration before any
model import or call. It must still pass its complete local and PR validation,
merge, branch cleanup, and master-alignment gates before the one registered
formal execution may run. The implementation itself authorizes no model
execution.
