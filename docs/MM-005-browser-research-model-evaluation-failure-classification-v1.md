# MM-005 Browser Research model-evaluation failure classification v1

> **Result: COMPLETE LOCALLY — the registered v1 attempt is consumed, but no
> authenticated terminal measurement exists and no retry is authorized.**

## Observed lifecycle

The outcome-neutral v1 protocol was published through PR #69 as signed squash
commit `7af879457bd55c9b3f6b4f7abf33e43ed181c2e9` before formal execution. Its
first command failed during freeze-commit path reading because Windows
`git show <commit>:<path>` hit a long-path boundary. That pre-consumption event
occurred before output claim, model import, GPU use, or model call. Repository-
local `core.longpaths=true` was then enabled and the complete freeze-commit
preflight passed while the fixed v1 output remained absent.

The same registered command was invoked again. It atomically wrote the v1
`attempt-owner.json`, which permanently changed the lifecycle to
`attempt_consumed=true` and `retry_allowed=false`. The controlling task was
then externally interrupted while the process was active. Process termination
bypassed the runner's Python exception handler, so no authenticated
`failure.json` or success artifact could be persisted.

The stable durable v1 directory contains exactly one file:

```text
attempt-owner.json
```

It contains no evaluation candidate, predictions, evidence, or formal failure
receipt. The directory is immutable: it must not be deleted, reopened,
overwritten, supplemented, or retried.

## Evidence boundary

The original 649-byte owner is tracked byte-for-byte as
[`baseline/mm005-browser-research-model-eval-v1-attempt-owner.json`](../baseline/mm005-browser-research-model-eval-v1-attempt-owner.json),
with SHA-256
`c5649806987521be26304e6abf81d545ab2522d71289d700d2c49305828b9ca6`.
The classifier validates it with the frozen v1 `validate_attempt_owner`
contract. It does not repeat the attempt identifier in the derived report.

The 11,936-byte canonical classification is
[`baseline/mm005-browser-research-model-eval-v1-failure-classification.json`](../baseline/mm005-browser-research-model-eval-v1-failure-classification.json),
with SHA-256
`628f9a24267c292d318ca279eb0642c72fbc705b1211629ef8b9edf6318e6e11`
and internal report digest
`sha256:8768a18c0aecc1da4bc693130b023b4949f5059b0eac6eabae6cbede6cae4d2a`.
It binds the exact v1 preregistration, all 12 frozen protocol sources, and the
tracked owner. Freeze-commit bytes are read with `git cat-file blob`, so the
classification does not depend on `core.longpaths`. When the ignored local run
directory exists, validation additionally requires an exact one-entry,
non-reparse, non-hardlinked tree whose owner bytes equal the tracked copy.
Clean CI validates the tracked copy without requiring that local directory.

The classification is
`external_controller_interruption_after_owner_claim_before_terminal_persistence`
in category
`controller_lifecycle_interruption_and_terminal_persistence`. The causal label
comes from controller observation correlated with the authenticated owner-only
state; it is not a formal-runner-authenticated exception receipt. Transient
checkpoint-load output and GPU activity were observed, but those observations
are explicitly non-authenticated and are not used to claim a completed model
load, any exact generation-call count, or model evaluation.

Exact execution counters, completed record IDs, raw outputs, compiled
predictions, metrics, latency, resources, and terminal failure stage are
unavailable and were not reconstructed. Therefore `formal_gate_passed=false`,
`evaluation_executed=false`, `formal_measurement_complete=false`,
`model_evaluated=false`, and `evaluation_result_available=false`. Here
`model_evaluated=false` means that no complete authenticated formal measurement
exists; it does not prove that no process-local model activity occurred. The
durable evidence does not attribute the outcome to model quality, dataset,
Adapter, compiler, Verifier, CUDA, resource caps, or runner algorithm.

## Repeatability boundary

The classification and its freeze-commit source bindings are deterministically
reconstructable from tracked bytes. That is implementation conformance and
evidence-reconstruction repeatability only. It is not Browser Research model-
evaluation repeatability, training repeatability, resource repeatability, or
cross-machine reproducibility; all of those claims remain false.

## Locked recovery protocol

The exact next gate is
`MM-005-browser-research-model-evaluation-recovery-protocol-v2`. It must freeze
a new experiment, not retry v1. Its locked identities are:

- execution gate `MM-005-browser-research-model-evaluation-execution-v2`;
- experiment `mm005-browser-research-model-eval-v2`;
- run `mm005-browser-research-model-eval-r2`;
- output directory `work/evaluation-runs/mm005-browser-research-model-eval-v2`;
- success review `MM-005-browser-research-model-evaluation-result-review-v2`.

The v2 protocol must bind the v1 preregistration, tracked owner, and this
classification. It must preserve the candidate and revision, read-only
Adapter, 32-record dataset and case order, 68 screenshot inputs, audit-only
source snapshots, prompt/compiler/Verifier/metrics, seed and generation
settings, resource caps, zero-retry policy, and authority boundaries.

Only the v2 identity/output/source closure, a long-path-safe Git blob reader,
durable progress checkpoints, and model-free terminal recovery after an
external interruption may change. No v1 file or directory may be changed, and
no v2 execution is authorized until that separate protocol is validated,
published, merged, cleaned up, and aligned with `master == origin/master`.

## Validation

```powershell
python -I -B scripts/classify_mm005_browser_research_model_evaluation_failure.py --check
python -I -B scripts/validate_offline.py
```

The nine focused tests cover exact recomputation, owner binding, local-tree
topology, hardlink rejection, `git cat-file blob` use, freeze-blob drift,
fail-closed claims, v2 identity, and artifact tamper. Local CPython 3.11.15,
3.12.12, and 3.13.7 each pass the complete 877-test unified gate with four
expected Windows privilege skips, 69 audited source files, and `valid=true`.
This validation is model-free and does not consume another attempt.
