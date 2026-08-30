# MM-005 Browser Research generation-failure diagnostic implementation v1

## Status and scope

This gate freezes the model-free result, failure, journal, owner, authority,
and runner semantics for
`MM-005-browser-research-model-evaluation-generation-failure-diagnostic-implementation-v1`.
It consumes the protocol published through PR #76 as signed squash commit
`9c90c5e68d4386b30db613930ec7dc0147999c04`; the 57,143-byte protocol remains
SHA-256
`13d1808168819414df2a0ca33d1f59e5e8efd52de6f0b49946d02cf070c992d6`.

This is still an implementation-freeze-only gate. No execution-authority,
owner, progress, lifecycle lease, success, failure, output-root, or reserved
staging artifact is created. `--plan` and `--check` are read-only; `--execute`
fails before output, lease, heavy dependency import, model, PIL, torch, or CUDA
work while the separate authority artifact is absent. The exact next gate is
`MM-005-browser-research-model-evaluation-generation-failure-diagnostic-execution-authority-v1`.
The reserved execution gate remains separate and unauthorized.

## Closed implementation slice

The reviewed implementation commit must differ from the protocol merge by
exactly 11 paths: the three canonical trackers, this document and its protocol
predecessor, the docs index, the unified validator, the protocol test updated
to recognize its separate successor, and these three implementation sources:

- `src/fullcycle_bridge/mm005_browser_research_model_evaluation_generation_failure_diagnostic_result.py`
- `scripts/run_mm005_browser_research_model_evaluation_generation_failure_diagnostic_v1.py`
- `tests/test_mm005_browser_research_model_evaluation_generation_failure_diagnostic_result.py`

The three implementation sources must share one first-parent introduction
commit and must equal that commit's Git blobs. The implementation does not
alter the frozen protocol config, protocol contract, builder, predecessor
result, consumed v1/v2 output, or Runtime repository.

## Owner, journal, and terminal contracts

The future owner is canonical JSON and is the only artifact that contains the
64-lowercase-hex private attempt ID. It exact-binds the implementation freeze,
the protocol, and the separately published authority introduction commit,
artifact receipt, and full authority contract. Owner and genesis are prepared
in one sibling staging directory and published as one directory rename only
after the lifecycle lease exists.

Progress is canonical JSONL, append-only, monotonically sequenced, and SHA-256
chained. A complete success has six session events, seven records times 18
durable checkpoint events, and one terminal-ready event: 133 frames total and
126 record checkpoints. The seven-record order and every per-record event are
exact. Stored case summaries contain only bounded scalars and receipts; raw
model text, messages, traceback, absolute paths, token IDs, and secrets are not
publishable.

Failure is closed over four disjoint scopes:

- pre-record lifecycle;
- inter-record transition;
- active-record substage;
- post-record terminalization after all 126 checkpoints.

Only a safe bounded `exception_type` string is permitted. A torn final JSONL
tail may be discarded only after its non-authenticated byte receipt is bound;
a complete invalid frame is never silently discarded. Success and failure
artifacts are mutually exclusive and are rebuilt from the authenticated owner
and journal rather than trusted as self-attestation.

## Separate authority boundary

The future authority schema is frozen here but no authority artifact is
published. It must bind an exact expected environment, the registered resource
caps, one formal invocation, zero retry, the implementation freeze, and four
critical dependency receipts. Those four receipts are useful direct evidence,
not a claimed transitive Python-call closure. The stronger code-closure rule is
that both execution and reconciliation require current `HEAD` to equal the
authority artifact's unique first-parent introduction commit while `master`,
`origin/master`, and the worktree are aligned.

All trusted Git calls discard inherited `GIT_*`, disable global/system config,
replace refs, grafts, lazy fetch, commit-graph acceleration, LFS filters,
hooks, external diffs, rename inference, and fsmonitor. NUL-delimited raw UTF-8
path parsing prevents `core.quotepath` from changing a reviewed slice that
contains the Chinese checklist path. `assume-unchanged` and `skip-worktree`
index flags are rejected. The expected environment must match before model
load or CUDA workload/mutation; read-only CUDA capability observation is
allowed only to construct that comparison.

The exact-HEAD rule means an authority-following commit blocks execution. If
`origin/master` advances after a claimed interruption, automatic
reconciliation also fails closed and requires explicit manual resolution; the
runner does not silently reinterpret the old authority under a new tree.

## Claim and reconciliation safety

The read-only topology includes every fixed authority/output/lease path and
any sibling beginning with the reserved diagnostic prefix. Owner staging,
lifecycle staging, and unknown reserved siblings are durable evidence: they
make `--plan`, `--check`, unified validation, and execution fail closed instead
of starting a second attempt. A missing ignored `work/evaluation-runs` parent
is valid read-only state after its nearest existing ancestor is verified as an
ordinary non-reparse directory; a future authorized execution path remains
responsible for safely preparing the execution parent.

Immediately before claim, and again immediately after the atomic owner/genesis
claim but before dependency load or the diagnostic session, the runner
revalidates the full protocol, implementation, authority, exact HEAD, and
frozen model/dataset lineage under the lifecycle and directory guards. Once an
output is claimed, `--execute` can route only to model-free reconciliation; it
never runs the model a second time. An authenticated incomplete prefix is
terminalized as `InterruptedExecution`, while lineage drift leaves the claimed
evidence untouched for review.

The future execution body permits one offline base/Adapter lifecycle, the
exact seven records, zero retry, and a socket fence around dependency loading
and all model work. Images, including the original PIL handles used for RGB
conversion, are explicitly closed. The current gate never invokes this body.

## Validation

Local CPython 3.11.15, 3.12.12, and 3.13.7 each pass 40 implementation-focused
tests and the 26 predecessor protocol tests. On all three versions the protocol
builder `--check`, runner `--plan`, and runner `--check` agree that the
implementation contract is valid while authority, output, attempt, execution,
reserved staging, result, and Runtime eligibility remain false. Each complete
unified gate passes 1,027 tests with four expected Windows privilege skips, 76
audited source files, and `valid=true`. Ruff 0.15.22 check, scoped format checks,
strict Mypy 2.3.0 on the two core files, three-version `py_compile`, and diff
validation also pass.

The negative tests cover all registered success/failure prefixes, canonical
JSON and numeric edge cases, authority/environment/owner drift, claimed-output
reconciliation without rerun, owner and lifecycle staging interruptions,
unknown reserved staging, fresh-checkout missing output parents, Unicode Git
paths, hidden index flags, fsmonitor-valid drift, and lineage changes on both
sides of claim publication.

## Limitations and locked next action

This implementation proves process-interruption/restart handling only. The two
critical directory renames fsync their files but do not establish portable
parent-directory fsync semantics on Windows, so host/power-loss durability is
not claimed. The recorded elapsed resource value covers dependency loading,
the diagnostic session, and its first final lineage check; it excludes later
success-frame/result construction, final lineage checks, and terminal fsync.
The remaining same-privilege filesystem and source-check TOCTOU windows are not
claimed resistant to a hostile concurrent actor.

Do not create an authority artifact, call `--execute`, create or repair runtime
output, load a model, use CUDA, or infer a causal Runtime substage in this gate.
After a clean implementation merge and branch cleanup, perform only the
separate
`MM-005-browser-research-model-evaluation-generation-failure-diagnostic-execution-authority-v1`
freeze. A clean implementation merge alone grants no execution authority.
