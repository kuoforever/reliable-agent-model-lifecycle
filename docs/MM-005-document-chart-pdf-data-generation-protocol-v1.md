# MM-005 Document/Chart/PDF data generation protocol v1

## Outcome

The exact data preregistration merged through PR #51 as
`3992778151bb7209c00c89e77e07894e075ff066`. The separate
`MM-005-document-chart-pdf-data-generation-v1` protocol is now frozen before
materialization. It adds only the one-shot execution contract, runner, and
evidence boundary needed to turn the already planned bytes into tracked
synthetic fixtures.

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

At this freeze, `fixtures/mm005_document_chart_pdf_v1` and
`baseline/mm005-document-chart-pdf-data-generation-v1.json` remain absent.
Generation, records, images, dataset validation, Environment Adapter,
Verifier, model, quality, safety, real/external content, capture, Serving,
promotion, and Runtime claims are all false.

Model output has no execution authority. Runtime remains the sole policy,
approval, WAL, grounding, budget, recovery, and desktop-dispatch boundary. No
Runtime repository or integration change is authorized.

## Validation evidence

Fourteen focused tests cover exact protocol reconstruction, source and claim
tamper, actual output semantics, single-byte drift, evidence resealing,
atomic/exclusive materialization, exact output trees, exclusive evidence,
merged-master enforcement, target absence, and model/network import
boundaries. Full-repository Ruff 0.15.22, scoped strict Mypy 2.3.0,
`py_compile`, protocol `--check`, and `git diff --check` pass. Local CPython
3.11.15, 3.12.12, and 3.13.7 each pass the unified 702-test gate with four
expected Windows privilege skips, 56 audited source files, and `valid=true`.

These checks establish deterministic protocol and planned-byte
reconstruction. They do not establish model, training, external-renderer,
cross-machine, quality, safety, Serving, promotion, or Runtime repeatability.

## Formal execution and next gate

After this exact protocol and runner are merged and the local branch is again
an aligned `master`, the single registered invocation is:

```powershell
python -I scripts/run_mm005_document_chart_pdf_generation.py execute `
  --protocol-freeze-commit <merged-40-hex-freeze-commit>
```

It may run once with no retry. A validated execution will establish only that
the frozen synthetic records, PNGs, PDFs, split files, manifest, and receipts
were generated and validated. The registered next gate is
`MM-005-document-chart-pdf-adapter-verifier-protocol-v1`; it must remain
separate from this data materialization.
