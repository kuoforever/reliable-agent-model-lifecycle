# MM-005 Document/Chart/PDF Adapter/Verifier protocol v1

## Outcome

The consumed MM-005 generation result is now a read-only upstream input. PR
#53 merged its exact 49 files / 434,212 bytes and 16,680-byte execution
evidence as `3ae49d372b5184418e8353630336fdb802182cbd`; neither may be reused,
overwritten, or regenerated.

The separate model-free
`MM-005-document-chart-pdf-adapter-verifier-protocol-v1` freezes the Adapter
projection and deterministic Verifier behavior before either implementation
is added. Its canonical artifact is
`configs/mm005_document_chart_pdf_adapter_verifier_protocol_v1.json`: 126,032
bytes with SHA-256
`4715134d7bd1f8ae54275764f342bf5a8974cc491298dbefd52971aab876c64a`.
It binds eight source receipts, the exact generation evidence and upstream
protocols, all tracked generated outputs, 32 Adapter projection receipts, and
160 Verifier reference cases.

## Adapter projection boundary

Each of the 32 records has one deterministic projection. The projection keeps
transport and audit metadata outside the model payload:

| Layer | Frozen fields / behavior |
|---|---|
| Model payload | `instruction`, `observation`, `source_kind`, `task_family_id` only |
| Hidden from model payload | expected output, record/family/template identity, split, provenance, Verifier contract, and real file path |
| Image binding | exact path/bytes/SHA-256 receipt outside the model payload |
| Audit receipt | record ID, split, task/source class, image SHA-256, projection bytes, projection SHA-256 |
| Authority | model output has no execution authority and Runtime integration is not authorized |

The observation retains only the frozen synthetic single-page structure needed
by the task, including region references and the image content hash. The actual
tracked image path remains an Adapter-side binding and is never serialized into
the model payload.

## Output compiler and Verifier boundary

The compiler accepts one UTF-8 JSON object of at most 8,192 bytes with exactly
`answer`, `evidence_refs`, and `page_number`. It rejects extra or duplicate
keys, non-finite values, empty or duplicate evidence references, malformed
identifiers, oversized output, and any page other than the registered
single-page value. Invalid output is always wrong.

The deterministic Verifier uses no model or LLM judge. Answers match after
Unicode NFC normalization and ASCII-space trimming; evidence references must
match exactly in order and remain unique; page number must match exactly. Five
reference cases are frozen for every record:

| Case kind | Count | Compiler valid | Joint correct |
|---|---:|---:|---:|
| Exact expected | 32 | 32 | 32 |
| Wrong answer | 32 | 32 | 0 |
| Wrong evidence | 32 | 32 | 0 |
| Duplicate evidence | 32 | 0 | 0 |
| Wrong page | 32 | 0 | 0 |
| **Total** | **160** | **96** | **32** |

This yields 32 positive controls and 128 negative controls across all four task
families, four source kinds, 24 train records, and eight validation records.

## Claim and authority boundary

Generation, record creation, image creation, and dataset validation remain the
only established claims inherited from the consumed upstream result.
Environment Adapter implementation/execution, Verifier implementation/
execution, model training/evaluation, quality, safety, real or external
content, capture, Serving, promotion, and Runtime eligibility remain false.

Runtime remains the sole policy, approval, WAL, grounding, budget, recovery,
and desktop-dispatch boundary. This protocol does not change the Runtime
repository, authorize Runtime integration, or grant model output any execution
authority.

## Validation evidence

Thirty-eight focused MM-005 data, generation, and Adapter/Verifier tests pass.
They cover exact reconstruction, source and upstream receipts, projection
closure and gold/path isolation, image-byte and binding tamper, strict compiler
boundaries, answer normalization, the complete positive/negative case matrix,
protocol tamper, authority, deferred implementation, and model/network import
absence. Ruff 0.15.22, scoped strict Mypy 2.3.0, `py_compile`, builder
`--check`, and `git diff --check` pass.

Local CPython 3.11.15, 3.12.12, and 3.13.7 each pass the unified 712-test gate
with four expected Windows privilege skips, 57 audited source files, and
`valid=true`.

These checks establish deterministic protocol and fixture reconstruction on
the registered local Python matrix. They do not establish Adapter or Verifier
execution, model/training repeatability, cross-machine reproducibility,
generalized quality, safety, Serving, promotion, or Runtime eligibility.

## Downstream implementation result and next gate

PR #54 merged this protocol as
`db8c6833f43c02a0b255c436558e0269a8bde3b4` with all checks clear and both
feature-branch copies deleted. The registered
`MM-005-document-chart-pdf-adapter-verifier-implementation-v1` then reproduced
all 32 projection receipts and 160 compiler/Verifier outcomes exactly while
treating the consumed data and generation evidence as immutable. Its
102,117-byte evidence has SHA-256
`d4cbe61cac4cff60c15e769c35e481ca93f71524b23bf0dad4ddf75095d17bf2`.

The current single next gate is
`MM-005-document-chart-pdf-model-evaluation-protocol-v1`. It must freeze an
outcome-neutral read-only measurement before any model import or call. No
training, capture, network access, or Runtime change is authorized.
