# MM-005 Browser Research generation-failure diagnostic implementation v2

## Status and authority boundary

This is the implementation-freeze-only successor to the protocol published
through PR #81 as verified signed squash commit
`eb2aea3ca1eb5d82e823f7fc7a6aac7b5beb3fc9`. It binds the exact
62,653-byte preregistration with SHA-256
`0d00d89235bae8d0a2271934aaf18008d7c31c3f9a9f3c83a9afdd5d1a474a52`
and preserves its new experiment, run, output, lease, scientific, and
zero-retry identity. The protocol merge remains the immutable receipt and
ancestor. Non-lifecycle zero-LFS-bandwidth CI maintenance M1 is
`e5e618b491a3dc38dbed9cdcd4c6c384f2df0f54`, whose unique parent is the
protocol merge. The literal implementation base is the later non-lifecycle
exact-head checkout maintenance M2
`8c679eba08a979fb60bfd87fbe8c73c8725d89c0`, whose unique parent is M1. The
implementation freeze must in turn have M2 as its unique direct parent.

This gate publishes no execution-authority artifact and performs no formal
diagnostic invocation. `--plan` and `--check` are read-only. Public
`--execute` can enter the implementation core only through a separately
published canonical authority at clean aligned exact `master`; no CLI flag,
environment variable, test mode, or public API bypass exists. Authority-v2
and exact-once execution-v2 remain later independent gates, and neither is a
retry of v1.

## Exact implementation slice

The reviewed implementation freeze must have
`8c679eba08a979fb60bfd87fbe8c73c8725d89c0` as its unique direct parent and
must differ from that implementation base by exactly these 11 paths:

1. `AI_Infra_LLM_Agent_待做任务清单.md`
2. `PROJECT_STATUS.md`
3. `README.md`
4. `docs/MM-005-browser-research-model-evaluation-generation-failure-diagnostic-implementation-v2.md`
5. `docs/MM-005-browser-research-model-evaluation-generation-failure-diagnostic-protocol-v2.md`
6. `docs/README.md`
7. `scripts/run_mm005_browser_research_model_evaluation_generation_failure_diagnostic_v2.py`
8. `scripts/validate_offline.py`
9. `src/fullcycle_bridge/mm005_browser_research_model_evaluation_generation_failure_diagnostic_result_v2.py`
10. `tests/test_mm005_browser_research_model_evaluation_generation_failure_diagnostic_protocol_v2.py`
11. `tests/test_mm005_browser_research_model_evaluation_generation_failure_diagnostic_result_v2.py`

The result contract, runner, and result tests are three new implementation
sources. They must share the implementation's unique first-parent introduction
commit and equal that commit's Git blobs. The immutable protocol config,
protocol contract/builder, every v1 implementation or output, recovery I/O,
model/data artifacts, Adapter, and Runtime remain unchanged.

## Ordered output-parent preparation

The future-authorized internal core freezes this sequence:

1. revalidate published authority, exact clean aligned HEAD, first-parent
   lineage, all tracked source bytes, hidden index flags, and fully unclaimed
   new-v2 topology;
2. require ordinary non-symlink/non-reparse repository root and existing
   direct-child `work`, then construct and verify
   `DirectoryTreeGuard(ROOT, work)`;
3. require `work/evaluation-runs` absent and call exactly one one-argument
   `os.mkdir` for that single component, with no parent creation or
   `exist_ok`;
4. revalidate authority, HEAD, lineage, sources, remaining unclaimed topology,
   and root/work/created-parent identity and ancestry;
5. construct and verify
   `DirectoryTreeGuard(ROOT, work/evaluation-runs)`;
6. create and enter the lifecycle lease, then revalidate again;
7. atomically publish owner plus the `attempt_claimed` genesis frame by an
   exclusive sibling-staging directory rename;
8. construct the output guard, enter the progress lease, and revalidate the
   claimed topology; and
9. only then cross `first_heavy_dependency_boundary`.

Parent creation is neither an attempt claim nor telemetry. A pre-parent or
post-create/pre-lifecycle failure has no owner-bound terminal grammar. A
lifecycle-stage pre-owner failure may leave lifecycle-only evidence. A claim
staging failure may leave lifecycle plus a reserved sibling, which permanently
blocks another attempt. The implementation does not delete or reinterpret any
of those states. Directory identity checks narrow observed replacement but do
not claim to eliminate every same-privilege TOCTOU window.

## Owner, journal, terminal, and reconciliation

All owner, progress, result, failure, and authority schema versions are
explicitly v2. The owner exact-binds `protocol_merge_commit`,
`zero_bandwidth_maintenance_commit`, `implementation_base_commit`,
implementation freeze, authority introduction, full authority payload, and
one private 64-lowercase-hex attempt ID. Owner and genesis are published
together. Every canonical JSONL journal frame records P, M1, and M2, while
terminal protocol lineage records both unique-parent edges P-to-M1 and
M1-to-M2. The journal retains the immutable seven-record,
17-environment-field, 9-substage, 126-checkpoint, 133-frame success grammar and
four owner-bound failure scopes.

Owner-bound exceptions are handled only after the atomic claim. A controlled
exception before the first record becomes the existing
`pre_record_lifecycle` failure and does not invent a zero-owner scope. Once an
output root is claimed, public execution routes only to reconciliation; it
never calls the first-heavy boundary a second time. Authenticated terminal
state may be repaired, while lineage drift or reserved staging fails closed.

## Mandatory real Git/filesystem regression

The implementation test creates a real temporary clone beginning at the exact
implementation base `8c679eba08a979fb60bfd87fbe8c73c8725d89c0`, verifies
its unique parent M1 `e5e618b491a3dc38dbed9cdcd4c6c384f2df0f54` and M1's
unique parent/protocol receipt
`eb2aea3ca1eb5d82e823f7fc7a6aac7b5beb3fc9`, commits an exact 11-path
implementation fixture, then commits one synthetic test-only authority. It
aligns local and remote `master`, creates safe `work`, and leaves
`work/evaluation-runs` absent. The regression also rejects an implementation
freeze separated from M2 by even an empty intermediate commit before any
output-parent mutation. This test-only lineage is passed only to the private
typed core and grants no production authority.

The regression mocks none of `os.mkdir`, `DirectoryTreeGuard`, lifecycle,
owner/genesis claim, or filesystem I/O. Its sole executed injection is a
controlled exception at `first_heavy_dependency_boundary`, after real parent/
lifecycle/owner/genesis creation and claimed-state revalidation. Fail-on-call
spies guard the registered Python socket APIs, the model-load-capable
production boundary, and the CUDA workload; all must remain uncalled. This
claim does not extend to unregistered native or subprocess networking. The
durable journal is exactly `attempt_claimed` followed by
`failure_terminal_ready`, the formal scope is `pre_record_lifecycle`, and the
model/PIL/torch/CUDA/network module set is unchanged. This controlled test
consumes no formal invocation budget.

Additional real temporary-repository negatives cover dirty and misaligned
HEAD, wrong branch, hidden index flags, unsafe `work`, parent collision,
post-create Git drift, parent identity replacement, lifecycle-only evidence,
and reserved owner staging. Missing or unpublished authority fails before
mutation, and claimed topology can route only to reconciliation.

## Validation and locked next action

Focused protocol/result tests must pass on CPython 3.11, 3.12, and 3.13. The
protocol builder `--check`, runner `--plan`/`--check`, Ruff check/format,
scoped strict Mypy, three-version `py_compile`, diff validation, and at least
one current-commit CPython 3.11 complete unified gate must all pass before
publication. The unified validator must observe the authority, parent,
lifecycle, owner, progress, success, and failure paths absent before and after
plan/check.

After a clean implementation merge and exact merge-HEAD checks, the only
successor is
`MM-005-browser-research-model-evaluation-generation-failure-diagnostic-execution-authority-v2`.
That later gate must independently bind the clean implementation commit,
environment, dependencies, budgets, and authority introduction. Do not create
authority or execute the diagnostic in this gate. Stop on receipt, identity,
scientific, path-ceiling, topology, check, review, conflict, or strict
up-to-date drift.
