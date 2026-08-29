# MM-005 Browser Research model-evaluation recovery protocol v2

> **Result: FROZEN LOCALLY — the recovery protocol is model-free and validated;
> no v2 attempt has been consumed and no model has been evaluated.**

## Why v2 exists

The published v1 experiment is permanently consumed. Its authenticated output
tree contains only the exact 649-byte `attempt-owner.json` because an external
controller interruption occurred before the runner persisted a terminal
artifact. The v1 failure classification deliberately does not infer missing
counters, completed records, model calls, outputs, metrics, resources, or a
formal failure stage.

V2 is therefore a new experiment, not a v1 retry. It keeps the complete v1
measurement meaning unchanged and adds only the lifecycle evidence needed to
make an externally interrupted run recoverable without reloading or recalling
the model.

## Frozen artifact and lineage

The canonical preregistration is
[`configs/mm005_browser_research_model_evaluation_protocol_v2.json`](../configs/mm005_browser_research_model_evaluation_protocol_v2.json).
It is 120,315 bytes with SHA-256
`512b3523196bf80e7e137c7777c205fa92a57acf371464f3f65671c406706c2e`.
Its identities are:

- gate `MM-005-browser-research-model-evaluation-recovery-protocol-v2`;
- execution gate `MM-005-browser-research-model-evaluation-execution-v2`;
- experiment `mm005-browser-research-model-eval-v2`;
- run `mm005-browser-research-model-eval-r2`;
- output directory
  `work/evaluation-runs/mm005-browser-research-model-eval-v2`;
- success review `MM-005-browser-research-model-evaluation-result-review-v2`;
- failure classification
  `MM-005-browser-research-model-evaluation-failure-classification-v2`.

The protocol-source closure contains 18 exact code receipts: the 12 v1
protocol sources, the failure-classification contract, and five v2
implementation sources. Separately, `source_lineage.recovery_lineage` binds
the immutable v1 preregistration, tracked v1 owner, published v1 freeze commit
`7af879457bd55c9b3f6b4f7abf33e43ed181c2e9`, published failure-classification
commit `28211e62d907c16a6d2208bca20f139ee7e31f5f`, classification bytes, and its
internal report digest. Historical Git bytes are read with
`git cat-file blob <commit>:<path>`; neither the builder nor the formal runner
depends directly or transitively on `git show`.

## Closed delta from v1

The protocol preserves these 12 v1 subtrees exactly:

- `decision`, `candidate`, `input_suite`, and `prompt_contract`;
- `compiler`, `verifier`, and `metrics`;
- `execution_protocol`, `resource_caps`, and `authority_contract`;
- `freeze_preconditions` and `claims`.

The recursive delta comparator is type-strict and closed. Arrays are atomic;
booleans cannot stand in for integers; integers and floats are distinct; and
float identity uses `float.hex()`, including signed zero. The only permitted
changes are the new identity/output/source closure, the Git blob reader, and
the durable recovery contract. Candidate, data, order, screenshot inputs,
audit-only source snapshots, prompt, compiler, Verifier, metrics, seed,
generation parameters, resource caps, zero-retry policy, and Runtime authority
remain unchanged.

## Durable lifecycle

The formal runner acquires the named lifecycle lease at
`work/evaluation-runs/mm005-browser-research-model-eval-v2.lifecycle/lease`
before attempting an output claim. Repository-root-to-output directory
identities are guarded for the full run; symlink, junction, reparse, hardlink,
path escape, and replacement races fail closed.

The owner and genesis progress event are assembled in one staging directory
and published by one directory rename. The lifecycle marker is likewise fully
written in a staging directory before its canonical directory rename, so a
preclaim process kill exposes either no canonical marker or a complete marker,
never a partial authoritative one.

`progress.json` is canonical JSONL with an append-only SHA-256 event chain.
Every checkpoint is flushed and `fsync`-committed. It records only durable
facts:

- base-model and Adapter load attempt/completion;
- each record's generation attempt/completion in frozen order;
- exact screenshot count, generation counter deltas, completed-record prefix,
  candidate persistence, and terminal readiness;
- monotonic counters and artifact states derived from the preceding event.

A torn final frame is first bound by its bytes and digest, then truncated to
the last authenticated event while the same lifecycle lease is held. A
complete but invalid newline-terminated frame is never discarded.

## Model-free terminal recovery

The recovery command requires the exact protocol freeze commit and attempt ID,
acquires the same lifecycle lease before reading progress, validates the owner
and complete journal, and reconstructs exactly one expected canonical success
or failure artifact from the terminal-ready event. The terminal file may be
absent, complete, or an exact byte prefix of those reconstructed bytes,
including the zero-byte prefix. Any wrong prefix, extra artifact, counter
inflation, record/order mismatch, screenshot mismatch, or second terminal is
rejected.

Recovery imports or calls no model, uses no CUDA or network, and performs no
retry. It cannot reconstruct the missing v1 progress and cannot continue an
interrupted generation. Its only authority is to finish persistence of a
terminal artifact whose complete canonical content is already determined by
authenticated v2 checkpoints.

After this protocol is published and merged, the registered commands are:

```powershell
work\training-env\Scripts\python.exe -I -B -X pycache_prefix=NUL scripts\run_mm005_browser_research_model_evaluation_v2.py --protocol-freeze-commit <merged-protocol-commit>

work\training-env\Scripts\python.exe -I -B -X pycache_prefix=NUL scripts\recover_mm005_browser_research_model_evaluation_v2.py --protocol-freeze-commit <merged-protocol-commit> --attempt-id <exact-v2-attempt-id>
```

The recovery command is applicable only after an interrupted v2 process has
released the lifecycle lease. Neither command is authorized from a feature
branch or before `master == origin/master == <merged-protocol-commit>`.

## Validation and claim boundary

The 21 focused adversarial tests cover exact v1 lineage and closed delta,
source drift, `git cat-file blob`, owner/genesis and lifecycle-marker atomicity,
lease ordering, full directory-chain identity, progress hash/counter/state
algebra, torn tails, incorrect record/screenshot transitions, terminal counter
inflation, exact-prefix repair, and the absence of model/CUDA/network/retry
capability. Ruff, Ruff format check, scoped strict Mypy, `py_compile`, and
protocol `--check` pass. Local CPython 3.11.15, 3.12.12, and 3.13.7 each pass
all 21 focused tests and the complete 898-test unified gate with four expected
Windows privilege skips, 71 audited source files, and `valid=true`.

At freeze, the v2 output and lifecycle roots are absent,
`attempt_consumed=false`, and `model_evaluated=false`. No Browser Research v2
measurement, result, quality, safety, repeatability, resource, cross-machine,
Serving, promotion, live-browser/network, real-content, capture, training, or
Runtime claim is established. The only next gate after a clean protocol merge,
branch cleanup, and aligned `master` is
`MM-005-browser-research-model-evaluation-execution-v2`.
