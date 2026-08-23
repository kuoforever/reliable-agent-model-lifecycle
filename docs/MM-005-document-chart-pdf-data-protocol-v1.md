# MM-005 Document/Chart/PDF data protocol v1

## Outcome

`MM-005-document-chart-pdf-data-protocol-v1` preregisters the exact first
synthetic dataset for the bounded environment selected by the parent
MM-005 environment-adaptation protocol. It reconstructs every future output
byte and receipt in memory, but writes no fixture, image, PDF, manifest, or
execution evidence.

The frozen artifact is
`configs/mm005_document_chart_pdf_data_protocol_v1.json`: 24,909 canonical
bytes with SHA-256
`7e774e69194e6f70c27c9b53bbab68adb19874780757717ca42012ec48297525`.
It binds the 49,202-byte parent protocol and five exact implementation/source
receipts.

PR #51 merged this exact preregistration as
`3992778151bb7209c00c89e77e07894e075ff066`; its local and remote feature
branches were deleted before the separate generation runner freeze began.

## Frozen data grid

The deterministic seed is `55005`. Each of the four task families has eight
unique template families: six train and two validation. One template produces
one record and one unique page image.

| Measure | Frozen count |
|---|---:|
| Task families | 4 |
| Template families | 32 |
| Records | 32 |
| Train records | 24 |
| Validation records | 8 |
| Unique PNG page images | 32 |
| Deterministic single-page PDF source artifacts | 14 |
| Planned output files | 49 |
| Planned output bytes | 434,212 |

The source distribution is deliberately explicit:

| Source kind | Train | Validation | Total |
|---|---:|---:|---:|
| `synthetic_text_document` | 5 | 1 | 6 |
| `synthetic_table_document` | 5 | 1 | 6 |
| `synthetic_bar_chart` | 4 | 2 | 6 |
| `synthetic_single_page_pdf` | 10 | 4 | 14 |

The 49 planned outputs are 32 PNGs, 14 PDFs, `train.json`,
`validation.json`, and `manifest.json`. Each path, byte count, and SHA-256 is
frozen before execution.

## Deterministic rendering and PDF boundary

Page images are fixed 1280×900 8-bit RGB PNGs. They use an embedded bitmap
font, no host font, no metadata chunks, a `none` filter on every row, and zlib
level 9. The protocol does not depend on Pillow, a browser, OCR, a PDF renderer,
network access, or model libraries.

Templates with source kind `synthetic_single_page_pdf` also produce a
deterministic PDF 1.4 source artifact with one 612×792-point page and the Base14
Helvetica font. The PDF and PNG are derived from the same sanitized layout
ground truth. The PNG is therefore a deterministic visual projection of that
shared synthetic layout, not a claim that an external PDF rasterizer was run.

## Record and semantic validation

Every planned record is built through the parent record contract. The protocol
then requires:

- exact coverage of all four task families, all four source kinds, and both
  splits;
- 6/2 train/validation templates per task family;
- disjoint family, template, instruction, observation, target, and image
  identities across splits;
- zero collision with the parent MM-002 through MM-004 exclusion registry;
- exact one-record-to-one-image hash and split binding;
- valid, unique 1280×900 PNG bytes;
- valid, unique, single-page PDF bytes for all 14 PDF-source templates;
- each non-region answer visible in its cited evidence region, or for region
  selection, the answer equal to a cited region ref;
- byte-exact reconstruction of all 49 planned outputs.

No LLM judge is used. These checks validate the preregistered plan in memory;
they do not turn planned bytes into generated dataset evidence.

## Freeze claims and authority

The fixed output root
`fixtures/mm005_document_chart_pdf_v1` and execution evidence path
`baseline/mm005-document-chart-pdf-data-generation-v1.json` were absent at
freeze. Generation, records/images, dataset validation, Environment Adapter,
Verifier execution, model training/evaluation, quality, safety, real/external
content, capture, Serving, promotion, and Runtime claims were all false at
that gate.

Model output has no execution authority. Runtime remains the sole policy,
approval, WAL, grounding, budget, recovery, and desktop-dispatch boundary. No
Runtime repository or integration change is authorized.

## Repeatability meaning

The repeatability target is exact preregistration and planned-byte
reconstruction: the same parent/source bytes and seed must reproduce the same
template registry, records, PNGs, PDFs, manifests, paths, counts, and SHA-256
receipts. It does not establish model, training, external-renderer, or
cross-machine performance repeatability.

Fourteen focused tests cover the frozen artifact, parent/source receipts,
template balance and compatibility, exact planned outputs, PNG/PDF structure
and uniqueness, parent record/exclusion validation, answer/evidence semantics,
all split identity classes, seed binding, tamper rejection, downstream-state-
independent reconstruction, and the model/network/execution-free import
boundary. At preregistration freeze, full-repository Ruff, scoped strict Mypy,
`py_compile`, builder `--check`, and `git diff --check` passed. Local CPython
3.11.15, 3.12.12, and 3.13.7 each passed the unified 688-test gate with four
expected Windows privilege skips, 55 audited source files, and `valid=true`.

## Downstream result and next gate

The registered `MM-005-document-chart-pdf-data-generation-v1` runner merged
through PR #52 as `fbf1c64398d89c35e95f80322fd665ae3c2f2c1d` and executed
exactly once from that aligned `master`. It independently validated and
materialized all 49 frozen outputs / 434,212 bytes and wrote the narrow
16,680-byte execution evidence without retry. The consumed data/evidence must
remain immutable. The downstream
`MM-005-document-chart-pdf-adapter-verifier-protocol-v1` is now frozen with 32
Adapter projection receipts and 160 deterministic Verifier controls. The
independent Adapter/Verifier implementation now reproduces every receipt and
control exactly; its registered next gate is an outcome-neutral model-
evaluation protocol.
