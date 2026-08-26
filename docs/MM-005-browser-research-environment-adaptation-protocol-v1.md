# MM-005 Browser Research environment-adaptation protocol v1

## Outcome

`MM-005-browser-research-environment-adaptation-protocol-v1` freezes the third
registered multimodal environment before any Browser Research data generation,
live browser or network use, model call, training, Serving work, capture, or
Runtime change. Desktop GUI remains first and the closed Document/Chart/PDF
lifecycle remains second; Audio/Video and optional robotics/autonomous-driving
simulation remain deferred.

The frozen artifact is
`configs/mm005_browser_research_environment_adaptation_protocol_v1.json`:
76,364 canonical bytes with SHA-256
`62ef6c554c90d3523b7d9c2a0a102c2a8c783f3d3ba3496cd8c36dfebe04b06e`.

The protocol binds the Document/Chart/PDF result publication merge
`5f60cbf44a311b46b312090d62d2783424c1dc85` and closure record
`0a608f01e7d92ae20878da356443d80d1de0fff8`. Its bounded same-machine
fixed-suite evaluation repeatability result remains read-only. Resource
repeatability remains false, and neither consumed attempt may be deleted,
reopened, reused, overwritten, or retried.

## Bounded first vertical slice

The selected scope is English, deterministic, repository-generated synthetic
Browser Research over one static research bundle containing one to three source
snapshots. Every source exposes three aligned observation modalities:

- visible DOM nodes with normalized bounding boxes;
- an exact screenshot SHA-256 binding;
- page text that must equal the visible DOM-node text in order.

All URLs use reserved `.invalid` domains over canonical HTTPS and forbid query,
fragment, credentials, or port state. Every source has an exact UTC
`published_at`, and every record has a UTC `snapshot_at`; future publication is
invalid. The four task families are:

- `single_source_fact_citation`
- `multi_source_synthesis_citation`
- `cross_source_comparison_citation`
- `freshness_conflict_resolution`

Multi-source tasks must cite at least two distinct sources. Freshness conflict
resolution must include a citation from the latest published source. Live
search/retrieval, navigation, JavaScript, login/session/cookie state, forms,
downloads/uploads/transactions, real or external webpages, prompt-injection
safety claims, and open-web source-quality ranking remain deferred.

Counts, seed, templates, deterministic page/screenshot rendering, output
receipts, and materialization claims are intentionally absent. They belong to
the next gate, `MM-005-browser-research-data-protocol-v1`.

## Four-component environment delta

| New environment component | Frozen responsibility |
|---|---|
| Environment Adapter | Project static DOM/screenshot/page-text bundles into model input and compile a strict cited answer |
| Task set | Define four task families and compatible synthetic source-bundle kinds |
| Deterministic Verifier | Compare normalized answer, exact ordered source-bound citation refs, and freshness semantics without an LLM judge |
| Synthetic dataset | Provide future train/validation records under the frozen source, record, identity, and provenance contracts |

Training/evaluation orchestration, Serving/model routing, policy, approval,
WAL, grounding authority, budgets, recovery, and desktop dispatch remain
inherited and may not be duplicated. This environment does not add a browser
controller, retrieval service, network stack, policy layer, or recovery system.

## Adapter, record, and citation interface

The future Adapter receives only `instruction`, `observation`,
`task_family_id`, and `source_kind`. Gold and Verifier fields remain outside
model input. Real URLs and file paths are prohibited; only synthetic `.invalid`
URLs are model-visible. Candidate output is exactly:

```json
{"answer":"...","citation_refs":["source-1-fact"]}
```

Extra or duplicate keys, malformed/non-finite/oversized JSON, an empty answer,
missing/duplicate/malformed citations, and citations absent from the observed
DOM compile to deterministic invalid output and score wrong.

Each future record binds:

- a local domain-separated `family_id` and complete-body `record_id`;
- shared cross-stage instruction, observation, and target identities;
- every screenshot SHA-256;
- every synthetic source-URL identity;
- every complete source-snapshot identity.

Train and validation must be disjoint by family, template, instruction,
observation, target, image, source URL, and source snapshot. All four families,
all four source kinds, and both splits are mandatory.

## Read-only lineage and leakage exclusions

The protocol reconstructs 102 exact source receipts: 18 protocol, parent,
sequencing, Runtime/capture-boundary, and upstream dataset files plus 84 prior
synthetic PNGs. It recomputes identities from actual MM-002 through MM-005
content rather than trusting older local ID schemes.

| Identity set | Count |
|---|---:|
| Prior case/record IDs | 124 |
| Prior family IDs | 96 |
| Instruction content hashes | 96 |
| Observation content hashes | 96 |
| Target content hashes | 124 |
| Image hashes | 84 |
| Prior Browser Research URL/snapshot hashes | 0 / 0 |

Any prior collision is a hard failure. The empty Browser Research URL/snapshot
sets are explicit because this is the first data boundary for that environment;
future stages must populate and enforce them.

## Provenance, untrusted content, and Runtime authority

Future data is limited to deterministic reviewed repository-generated
synthetic snapshots. No external content is fetched, no live browser or network
is used, Lane B capture stays disabled, and no Runtime browser/document content
is claimed.

Page text, DOM text, and model output have no instruction or execution
authority. The Runtime remains the sole policy, approval, WAL, grounding,
budget, recovery, and dispatch boundary. This protocol changes neither Runtime
code nor Runtime integration state.

At freeze, Adapter implementation, task materialization, dataset generation or
validation, Verifier execution, live browsing, network access, external or real
content collection, model training/evaluation, quality, safety, prompt-
injection safety, Serving, promotion, and Runtime eligibility are all false.

## Repeatability and validation meaning

The repeatability target is protocol and identity reconstruction: unchanged
tracked source bytes must rebuild the same canonical protocol, source receipts,
exclusion sets, record identities, compiler behavior, and deterministic
Verifier decisions. It is not Browser Research model-evaluation, live-browser,
resource, training, or cross-machine repeatability.

Seventeen focused tests cover byte-exact reconstruction, prior closure,
sequence and scope, four-component closure, protocol tampering, future record
coverage, local/cross-stage/source identities, DOM/page-text tampering,
cross-split source reuse, prior Document/Chart/PDF content collision, provenance
rejection, invalid-domain URL enforcement, time ordering, citation existence,
multi-source coverage, freshness selection, and total model-free compilation
and verification. Ruff, strict Mypy, `py_compile`, builder `--check`, and the
unified Browser Research subcheck pass locally. CPython 3.11.15, 3.12.12, and
3.13.7 each pass the complete unified 797-test gate with `valid=true`, four
expected Windows privilege skips, and 62 audited source files. These results
establish protocol/identity reconstruction across the registered local Python
matrix; they do not establish live-browser, model-quality, resource, training,
or cross-machine repeatability.

## Next gate

After this exact protocol merges with checks, review, and conflict state clear,
both feature-branch copies are deleted, and `master == origin/master`, the
single next gate is `MM-005-browser-research-data-protocol-v1`. It must freeze
seed, counts, template families, static source snapshots, deterministic DOM/
page-text/screenshot alignment, output receipts, split isolation, and validation
before generating any Browser Research record or image.
