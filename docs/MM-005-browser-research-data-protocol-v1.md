# MM-005 Browser Research data protocol v1

## Outcome

`MM-005-browser-research-data-protocol-v1` preregisters the exact first
synthetic dataset for the bounded Browser Research environment selected by the
parent protocol. It rebuilds every future record, static source snapshot,
screenshot, dataset file, manifest, path, byte count, and SHA-256 receipt in
memory. It writes none of those future outputs and creates no execution
evidence.

The frozen artifact is
`configs/mm005_browser_research_data_protocol_v1.json`: 73,476 canonical bytes
with SHA-256
`38e31afc46cf92603d191563bc5460062adeb702e7df3ee4ff18f485b034283a`.
It binds the 76,364-byte parent Browser Research protocol and five exact
implementation/source receipts.

## Frozen data grid

The deterministic seed is `55006`. Each of the four task families has eight
unique template families: six train and two validation. One template produces
one record and a bundle of one, two, or three sources.

| Measure | Train | Validation | Total |
|---|---:|---:|---:|
| Template families / records | 24 | 8 | 32 |
| Static source snapshots | 51 | 17 | 68 |
| Unique 1280×900 PNG screenshots | 51 | 17 | 68 |

The task/source-count plan is explicit:

| Task family | Sources per ordinal | Train sources | Validation sources | Total |
|---|---|---:|---:|---:|
| `single_source_fact_citation` | `1,1,1,1,1,1,1,1` | 6 | 2 | 8 |
| `multi_source_synthesis_citation` | `2,2,3,2,3,3,2,3` | 15 | 5 | 20 |
| `cross_source_comparison_citation` | `2,2,3,2,3,3,2,3` | 15 | 5 | 20 |
| `freshness_conflict_resolution` | `2,2,3,2,3,3,2,3` | 15 | 5 | 20 |

The 139 planned outputs are 68 PNGs, 68 canonical static-source JSON
descriptors, `train.json`, `validation.json`, and `manifest.json`. Their future
tree totals 986,989 bytes. Every path, byte count, and SHA-256 is frozen before
generation.

## Static-source and three-modality alignment

Each source uses a unique HTTPS `.invalid` URL and fixed publication time. Its
static snapshot is a canonical JSON descriptor, not executable HTML. It
contains the exact source object embedded in the future record plus bindings
to the future screenshot path, source URL identity, and source snapshot
identity. It contains no JavaScript, cookie, session, login, form, transaction,
download, or external retrieval behavior.

DOM nodes are the single synthetic ground truth:

1. `page_text` must equal the visible DOM-node text joined in node order.
2. The PNG is deterministically rendered from those exact nodes and normalized
   bounding boxes.
3. The record binds the PNG bytes through `screenshot_sha256`.
4. The standalone source descriptor must contain the exact same source object.

Screenshots are fixed 1280×900 8-bit RGB PNGs. They use the repository's
embedded bitmap font, no host font, no metadata chunks, a `none` filter on
every row, and zlib level 9. The plan does not import or run a browser engine,
Pillow, OCR, network client, or model library.

## Record, citation, freshness, and leakage validation

All 32 records are built through the parent Browser Research record contract.
The data protocol additionally requires:

- exact coverage of all four task families, all four source kinds, both
  splits, and the one/two/three-source range;
- 6/2 train/validation templates per task family and 51/17 sources per split;
- disjoint family, template, instruction, observation, target, screenshot,
  source-URL, and source-snapshot identities across splits;
- zero collision with every identity in the parent MM-002 through prior
  MM-005 exclusion registry;
- exact screenshot path/hash, PNG structure, dimensions, uniqueness, and
  DOM-render rebuild;
- exact canonical source-descriptor-to-record-source binding;
- single-source answers bound to their cited fact node;
- multi-source synthesis answers reconstructed from every cited source in
  source order;
- comparison answers recomputed from the cited maximum and minimum values;
- freshness answers bound to the latest published source while citing both an
  earlier and the latest source;
- byte-exact reconstruction of all 139 planned outputs.

No LLM judge is used. These checks validate a preregistered plan in memory;
they do not establish that the future dataset has been generated.

## Freeze claims and authority

The fixed output root `fixtures/mm005_browser_research_v1` and execution
evidence path `baseline/mm005-browser-research-data-generation-v1.json` are
absent at freeze. Generation, records, snapshots, screenshots, dataset
validation, Environment Adapter/Verifier execution, live browser/network use,
model training/evaluation, quality, safety, prompt-injection robustness,
real/external content, capture, Serving, promotion, and Runtime claims are all
false.

Page content and model output have no instruction or execution authority.
Runtime remains the sole policy, approval, WAL, grounding, budget, recovery,
and desktop-dispatch boundary. No Runtime repository or integration change is
authorized.

## Repeatability meaning

The repeatability target is exact preregistration and planned-byte
reconstruction: the same parent/source bytes and seed must reproduce the same
template registry, records, source descriptors, screenshots, datasets,
manifest, paths, counts, and SHA-256 receipts. It does not establish dataset
generation, browser execution, model/training repeatability, external-web
behavior, resource repeatability, or cross-machine reproducibility.

Fourteen focused adversarial tests cover the frozen artifact, parent/source
receipts, the balanced template/source grid, exact planned outputs, PNG and
source-descriptor structure, parent record/exclusion validation, DOM/page-text/
screenshot alignment, citation/freshness semantics, all split identity
classes, seed binding, tamper rejection, fixed-output absence, and the browser/
network/model/execution-free import boundary. Ruff, scoped strict Mypy,
`py_compile`, builder `--check`, and `git diff --check` pass. Local CPython
3.11.15, 3.12.12, and 3.13.7 each pass the complete unified 811-test gate with
four expected Windows privilege skips, 63 audited source files, and
`valid=true`.

## Next gate

The registered downstream gate is
`MM-005-browser-research-data-generation-v1`. It may be designed only after
this exact preregistration cleanly merges, both feature-branch copies are
deleted, and `master == origin/master`. That later gate must independently
freeze an atomic, exact-tree, zero-retry materialization boundary before any of
the 139 outputs can be written.
