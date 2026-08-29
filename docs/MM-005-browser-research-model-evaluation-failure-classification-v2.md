# MM-005 Browser Research model-evaluation failure classification v2

> **Result: COMPLETE LOCALLY — the registered v2 attempt is consumed, its
> authenticated partial progress and failure terminal are preserved, and no
> retry, completed measurement, or root-cause claim is authorized.**

## Observed lifecycle

PR #71 published the outcome-neutral recovery-v2 protocol as signed squash
commit `91b637c6b365ea8632b31335f5c74ac6c60e6b71`. After all registered
preconditions passed on aligned
`master == origin/master == 91b637c6b365ea8632b31335f5c74ac6c60e6b71`, the
formal command was invoked exactly once on 2026-08-29:

```powershell
work\training-env\Scripts\python.exe -I -B -X pycache_prefix=NUL scripts\run_mm005_browser_research_model_evaluation_v2.py --protocol-freeze-commit 91b637c6b365ea8632b31335f5c74ac6c60e6b71
```

The runner atomically published the owner and genesis event, completed one
fresh base-model load and one independent Adapter load, and durably completed
the first three records in frozen order. It then persisted the fourth
`generation_started` checkpoint. A `RuntimeError` occurred somewhere within
the registered `generation` stage before a fourth durable completion, and the
runner's Python exception handler successfully wrote the authenticated failure
terminal. No terminal recovery command was needed or run.

The stable consumed output directory contains exactly:

```text
attempt-owner.json
failure.json
progress.json
```

It contains no evaluation candidate, predictions, or evidence. The directory
and lifecycle marker remain immutable local execution evidence: they must not
be deleted, reopened, reused, overwritten, supplemented, or retried.

## Tracked evidence

The three formal artifacts are tracked byte-for-byte:

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| [`attempt-owner.json`](../baseline/mm005-browser-research-model-eval-v2-attempt-owner.json) | 938 | `a80cf6a2a9142fdfbc7a92646498a05e5036fc13227af88470297b98990aad87` |
| [`progress.json`](../baseline/mm005-browser-research-model-eval-v2-progress.json) | 22,782 | `a19709eb55fedc248eed32c1acbe9dbf0caa61f2cfc1a9ae7f5cf16b2a9a70b1` |
| [`failure.json`](../baseline/mm005-browser-research-model-eval-v2-failure.json) | 2,675 | `46f3968482567db2810237c277f65d982ce9518f829c43ad96bd1fc7d2776bc7` |

The 11,920-byte canonical derived classification is
[`baseline/mm005-browser-research-model-eval-v2-failure-classification.json`](../baseline/mm005-browser-research-model-eval-v2-failure-classification.json),
with SHA-256
`169c78c7337eca32de8769c8598b9f514e2acc33a04ec50a0fdc4bc5a3895197`
and internal report digest
`sha256:425bcf20cdab6a70d2bf67ed9bdbd19bddc3c9020bdd99800fedac8d6c9bcbe1`.
It does not repeat the private attempt identifier.

The classifier validates the 120,315-byte recovery-v2 preregistration, all 18
protocol-source blobs at freeze commit
`91b637c6b365ea8632b31335f5c74ac6c60e6b71`, and the three raw artifacts with
the frozen owner, journal, and failure contracts. Historical bytes are read
with `git cat-file blob`. When the ignored local execution tree exists, the
classifier also acquires the lifecycle lease and requires an exact three-file,
non-reparse, non-hardlinked tree whose bytes equal the tracked copies. Clean CI
validates the tracked evidence without requiring the local GPU-run directory.

## Authenticated failure boundary

The 14 canonical append-only journal frames establish these exact durable
facts:

- terminal sequence `13`, with `failure_terminal_ready` immediately after the
  fourth `generation_started` checkpoint;
- base-load attempts/completions `1/1` and independent Adapter-load
  attempts/completions `1/1`;
- generation attempts/completions `4/3`, with the first three frozen record
  IDs as the exact completed prefix;
- nine screenshot inputs and zero source-snapshot model inputs;
- zero retry, network, training, backward, optimizer, Adapter-write, and
  model/tensor-save operations;
- terminal `stage=generation`, `exception_type=RuntimeError`,
  `external_controller_interruption=false`, and no discarded progress tail;
- `attempt_consumed=true`, `evaluation_executed=false`,
  `formal_measurement_complete=false`, and `model_evaluated=false`.

The active fourth record is
`sha256:26b3a9da0467d1c18cc4a050ec10dc03a415a9c3a38a2a37de8b9805c67adaf7`,
a train-split `cross_source_comparison_citation` case using template
`mm005-browser-cross-comparison-06` and three screenshots. This identifies the
durable boundary; it does not establish that the record, its screenshots, or
any particular runtime substage caused the failure.

The formal classification is
`generation_stage_runtime_error_after_three_completed_calls_before_fourth_completion`
in category
`generation_pipeline_runtime_failure_without_attributable_substage`.

## Root-cause and claim boundary

The protocol safely persists only the exception class and registered broad
stage. The `generation` stage spans message construction, synchronization,
processor encoding, generation, post-synchronization, and case construction.
There is no authenticated substage checkpoint, exception message, traceback,
raw fourth output, metric, latency, or resource measurement.

The controller console displayed text consistent with a CUDA illegal-memory-
access error, but that text and traceback were not persisted by the protocol.
The classification records this only as a non-authenticated controller
observation and does not derive a cause from it. The evidence therefore does
not attribute the failure to CUDA, GPU hardware, driver, OOM/resource caps,
model, Adapter, dataset/record, prompt, processor, compiler, Verifier, or runner
algorithm.

Partial authenticated execution is not a completed evaluation. No Browser
Research result, quality improvement, generalized quality, safety, evaluation
repeatability, resource repeatability, cross-machine reproducibility, Serving,
promotion, or Runtime eligibility claim is established.

## Locked investigation protocol

The exact next gate is the model-free
`MM-005-browser-research-model-evaluation-generation-failure-investigation-protocol-v1`.
The classification itself authorizes no model or CUDA execution. The protocol
must first bind the v2 preregistration, owner, 14-frame progress journal,
failure receipt, and derived classification, then statically inspect the fourth
record's frozen inputs and message/prompt pipeline.

If model-free investigation cannot isolate the boundary, any later diagnostic
execution must be a separately preregistered experiment with a new identity
and output directory, fine-grained substage checkpoints, a clean merged-master
precondition, and its own authority and resource limits. It is not a retry of
v2. Recovery-v3 is not yet justified: durable progress and terminal
persistence worked, while no failed substage or remediating semantic delta is
authenticated.

## Validation

```powershell
work\training-env\Scripts\python.exe -I -B scripts\classify_mm005_browser_research_model_evaluation_failure_v2.py --check
work\training-env\Scripts\python.exe -I -B scripts\validate_offline.py
```

The 15 focused adversarial tests cover exact type-strict recomputation, all three raw
bindings, canonical progress and terminal boundaries, fail-closed claims,
non-authenticated controller text, attempt-ID privacy, optional local topology,
hardlink and extra-file rejection, tracked-byte and freeze-blob drift,
boolean/integer substitution, model-free next-gate authority, and absence of
model/network/recovery/retry capability. This validation is model-free and
cannot consume or repair another attempt.

Local CPython 3.11.15, 3.12.12, and 3.13.7 each pass all 15 focused tests and
the complete 913-test unified offline gate with four expected Windows
privilege skips, 72 audited source files, and `valid=true`. Each unified result
recomputes the same classification, `attempt_consumed=true`, and locked
investigation-protocol successor.
