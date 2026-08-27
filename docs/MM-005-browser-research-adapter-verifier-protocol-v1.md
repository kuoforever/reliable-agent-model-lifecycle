# MM-005 Browser Research Adapter/Verifier protocol v1

## Outcome

PR #66 published the consumed Browser Research generation result as
`6e990f0cf8ba4f76bd35a57479c3649c4cadc3aa`. The exact 139-file / 986,989-byte
output tree and 63,294-byte generation evidence are read-only upstream inputs;
they must not be deleted, reopened, overwritten, regenerated, or retried.

The separate model-free
`MM-005-browser-research-adapter-verifier-protocol-v1` freezes how those inputs
will be projected to a model and how candidate answers and citations will be
compiled and verified before either formal implementation exists. Its canonical
artifact is
`configs/mm005_browser_research_adapter_verifier_protocol_v1.json`: 271,406
bytes with SHA-256
`a64f5d3d174ab2e8c7a003626d76981f43c15b9e739f8c999c4198df0c77156b`.
It binds eight source receipts, the exact generation evidence and upstream
protocols, the published result commit, all tracked datasets, 68 screenshot
bindings, 68 source-snapshot bindings, 32 Adapter projection receipts, and 224
Verifier reference cases.

## Adapter projection boundary

Each of the 32 records has one deterministic projection. Transport and audit
metadata remain outside the model payload:

| Layer | Frozen fields / behavior |
|---|---|
| Model payload | `instruction`, static `observation`, `source_kind`, and `task_family_id` only |
| Hidden from model payload | expected answer/citations, record/family/template identity, split, provenance, Verifier rules, screenshot paths, and source-snapshot paths |
| Source binding | ordered source ID plus exact screenshot and source-snapshot path/bytes/SHA-256 receipts, outside the model payload |
| Audit receipt | record ID, split, task/source class, source count, ordered artifact hashes, projection bytes, and projection SHA-256 |
| Authority | page content and model output have no execution authority; Runtime integration is not authorized |

The model-visible observation retains only the registered synthetic static
source content: URL under `.research.invalid`, title, publication time, DOM
nodes, visible-order page text, screenshot content hash, and fixed snapshot
metadata. Exact repository artifact paths never enter the serialized model
payload.

## Output compiler and Verifier boundary

The compiler accepts one UTF-8 JSON object of at most 8,192 bytes with exactly
`answer` and `citation_refs`. It rejects extra or duplicate keys, non-finite
values, empty or duplicate citations, malformed references, oversized answers,
and malformed JSON. Invalid output is always wrong.

The deterministic Verifier uses no model or LLM judge. Answers match after
Unicode NFC normalization and ASCII-space trimming. Citation references must
match the registered expected list exactly, including order and cardinality.
The record contract independently guarantees that expected refs belong to the
record DOM, non-single-source tasks cite at least two distinct sources, and
freshness tasks cite a source with the latest `published_at` value.

Seven reference cases are frozen for every record:

| Case kind | Count | Compiler valid | Joint correct | Purpose |
|---|---:|---:|---:|---|
| Exact expected | 32 | 32 | 32 | Positive control with bound citations and required source coverage |
| Wrong answer | 32 | 32 | 0 | Separates answer correctness from citation correctness |
| Wrong DOM ref | 32 | 32 | 0 | Uses an existing but non-gold ref |
| Unknown DOM ref | 32 | 32 | 0 | Proves syntax alone does not establish source binding |
| Wrong citation sequence or coverage | 32 | 32 | 0 | Reorders multi-source refs, adds an extra single-source ref, or removes the latest freshness source |
| Duplicate citation | 32 | 0 | 0 | Exercises compiler uniqueness rejection |
| Malformed JSON | 32 | 0 | 0 | Exercises total fail-closed parsing |
| **Total** | **224** | **160** | **32** | **32 positive and 192 negative controls** |

All eight freshness records have an explicit negative control that omits the
latest published source. Multi-source synthesis and comparison controls retain
valid JSON while breaking the exact ordered citation contract.

## Claim and authority boundary

Generation, record creation, source-snapshot creation, screenshot creation, and
dataset validation remain the only established claims inherited from the
consumed upstream result. Environment Adapter implementation/execution,
Verifier implementation/execution, live browser or network use, model training
or evaluation, quality, safety, prompt-injection safety, real or external
content, capture, Serving, promotion, and Runtime eligibility remain false.

Runtime remains the sole policy, approval, WAL, grounding, budget, recovery,
and desktop-dispatch boundary. This protocol does not change the Runtime
repository, authorize Runtime integration, or grant page content or model
output any execution authority.

## Validation evidence

Eleven focused adversarial tests pass. They cover exact reconstruction,
published-result and upstream receipts, all 68 dual artifact bindings, all 32
gold/path-isolated projections, screenshot/snapshot/binding tamper rejection,
the strict compiler, answer normalization, all 224 positive/negative and
semantic controls, freshness negatives, protocol tamper rejection, authority,
deferred implementation, and model/network/browser import absence.

Ruff, scoped strict Mypy, `py_compile`, and builder `--check` pass. Local
CPython 3.11.15, 3.12.12, and 3.13.7 each pass the complete unified 839-test
gate with four expected Windows privilege skips, 65 audited source files, and
`valid=true`.

These checks establish deterministic same-repository reconstruction of the
frozen protocol, fixture bindings, projections, compiler cases, and reference
Verifier outcomes. They do not establish a formal Adapter or Verifier
implementation, any model-evaluation repeatability, cross-machine
reproducibility, generalized quality or safety, Serving, promotion, or Runtime
eligibility.

## Next gate

The protocol must first pass the complete local and PR validation matrix, merge
cleanly, delete both feature-branch copies, and leave local `master` aligned
with `origin/master`. Only then may the separate model-free
`MM-005-browser-research-adapter-verifier-implementation-v1` independently
reproduce all 32 projection receipts and 224 compiler/Verifier outcomes while
treating the consumed generation tree and evidence as immutable.
