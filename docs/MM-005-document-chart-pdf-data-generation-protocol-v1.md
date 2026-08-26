# MM-005 Document/Chart/PDF data generation protocol v1

## Outcome

The exact data preregistration merged through PR #51 as
`3992778151bb7209c00c89e77e07894e075ff066`. The separate
`MM-005-document-chart-pdf-data-generation-v1` protocol and one-shot runner
then merged through PR #52 as
`fbf1c64398d89c35e95f80322fd665ae3c2f2c1d`; both feature-branch copies were
deleted. From that exact aligned `master`, the registered generation executed
once and produced the tracked synthetic fixtures and narrow execution
evidence described below.

The canonical protocol is
`configs/mm005_document_chart_pdf_data_generation_v1.json`: 17,780 bytes with
SHA-256
`6e212237ee59d9730f97028769033a0991f9e3c6b893a404fc583274f813f2ed`.
It binds four exact source receipts, the 24,909-byte data protocol, and all 49
planned output receipts.

## Frozen execution plan

The execution plan preserves the existing `seed=55005` data grid:

| Measure | Frozen value |
|---|---:|
| Templates / records | 32 / 32 |
| Train / validation records | 24 / 8 |
| PNG page images | 32 |
| Single-page PDF source artifacts | 14 |
| Output files | 49 |
| Output bytes | 434,212 |
| Internal retries | 0 |

Formal execution requires all of the following:

- the current branch is `master`;
- `HEAD == origin/master ==` the supplied 40-hex freeze commit;
- the generation protocol, data protocol, data contract/builder, and
  generation contract/runner exactly match `git show <freeze-commit>:<path>`;
- the fixed output root and evidence path are both absent;
- every in-memory output passes the frozen data, parent-record, exclusion,
  split-isolation, PNG/PDF, and answer/evidence checks before writing;
- all files are written to a unique staging directory and the complete output
  root is atomically renamed into place;
- the persisted tree contains exactly the 49 registered paths, with no extra
  file, symlink, or reparse directory;
- all persisted bytes are read back and independently validated before the
  execution evidence is written exclusively and atomically.

The runner has no internal retry. If execution leaves only one of output or
evidence present, the unified gate rejects the state as incomplete rather than
treating a later invocation as a retry.

## Freeze state and claims

At the runner freeze, `fixtures/mm005_document_chart_pdf_v1` and
`baseline/mm005-document-chart-pdf-data-generation-v1.json` were absent.
Generation, records, images, dataset validation, Environment Adapter,
Verifier, model, quality, safety, real/external content, capture, Serving,
promotion, and Runtime claims were all false.

Model output has no execution authority. Runtime remains the sole policy,
approval, WAL, grounding, budget, recovery, and desktop-dispatch boundary. No
Runtime repository or integration change is authorized.

## Formal execution result and claim boundary

The single registered invocation used protocol freeze commit
`fbf1c64398d89c35e95f80322fd665ae3c2f2c1d` and completed without retry. An
independent persisted-byte readback validates exactly 49 output files totaling
434,212 bytes:

| Output | Count / bytes |
|---|---:|
| Train records | 24 / 65,327 JSON bytes |
| Validation records | 8 / 22,490 JSON bytes |
| Manifest | 1 / 14,789 JSON bytes |
| PNG page images | 32 |
| Single-page PDFs | 14 |

The 16,680-byte execution evidence at
`baseline/mm005-document-chart-pdf-data-generation-v1.json` has SHA-256
`a11a373a6c7d49b02470a84d9c303cb4f424ff6693dcc516ef8060af032d649f`.
All 16 registered integrity, isolation, atomicity, exact-tree, readback,
authority, and fail-closed gates are true.

Only `generation_executed`, `records_generated`, `images_generated`, and
`dataset_validated` are now true. Environment Adapter implementation,
Verifier execution, model training/evaluation, quality improvement, safety,
real/external content, capture, Serving, promotion, Runtime eligibility, and
Runtime repository/integration changes remain false.

## Validation evidence

Fourteen focused tests cover exact protocol reconstruction, tracked evidence
and output reconstruction, source and claim tamper, actual output semantics,
single-byte drift, evidence resealing, atomic/exclusive materialization, exact
output trees, exclusive evidence, merged-master enforcement, and model/network
import boundaries. Full-repository Ruff 0.15.22, scoped strict Mypy 2.3.0,
`py_compile`, protocol `--check`, and `git diff --check` pass. After execution,
local CPython 3.11.15, 3.12.12, and 3.13.7 each pass the unified 702-test gate
with four expected Windows privilege skips, 56 audited source files, and
`valid=true`.

These checks establish deterministic protocol and exact same-machine output
reconstruction. They do not establish model, training, external-renderer,
cross-machine, quality, safety, Serving, promotion, or Runtime repeatability.

## Consumed execution and next gate

The consumed invocation was:

```powershell
work/training-env/Scripts/python.exe -I `
  scripts/run_mm005_document_chart_pdf_generation.py execute `
  --protocol-freeze-commit fbf1c64398d89c35e95f80322fd665ae3c2f2c1d
```

It must not be invoked again: the fixed output and evidence are consumed,
immutable inputs to later gates. The registered next gate is
`MM-005-document-chart-pdf-adapter-verifier-protocol-v1`. It is now frozen as
a separate 126,032-byte model-free artifact with 32 Adapter projection
receipts and 160 deterministic Verifier controls. The downstream independent
Adapter/Verifier implementation now reproduces all of them exactly and is
merged. Its downstream outcome-neutral model-evaluation protocol is now frozen
locally before any model import or call. The consumed generation result remains
immutable throughout.
