# MM-005 Browser Research generation-failure investigation implementation v1

> **Result: IMPLEMENTATION PUBLISHED; FIXED RESULT VALIDATED LOCALLY — PR #74
> published the closed implementation. One clean merged-master model-free
> invocation created the fixed result, and the patched historical checker
> independently recomputes it. The result publication slice is not yet
> merged.**

## Published predecessor

PR #73 published the 33,476-byte outcome-neutral investigation protocol as
signed squash commit `fe430710924537a18e677b75202f0c19806d3f12`. Its
canonical SHA-256 is
`be8ecd067e884a8d60c9664013943d6887c769ac35a389934509b73338247494`.
The merge completed only after all six Linux Python-matrix checks passed and
no review, comment, thread, conflict, or merge-state blocker remained. Both
feature-branch copies were deleted and local `master == origin/master` before
this implementation slice started.

The published protocol did not freeze implementation source or select an
outcome. This bounded successor supplies that missing implementation contract
without modifying the protocol, its config, its ten-source closure, or any
consumed v1/v2 artifact.

## Closed result and decision contract

The result contract is
[`src/fullcycle_bridge/mm005_browser_research_model_evaluation_generation_failure_investigation_result.py`](../src/fullcycle_bridge/mm005_browser_research_model_evaluation_generation_failure_investigation_result.py).
It closes the fixed result schema, nine-step observation topology, strict
Boolean inputs, mutually exclusive predicates, precedence, claim transitions,
and outcome-to-protocol routing before formal execution.

The five outcomes are evaluated in this exact order:

1. `protocol_or_lineage_invalid`;
2. `deterministic_static_input_or_message_failure_reproduced`;
3. `static_difference_observed_without_causal_failure`;
4. `static_pipeline_reconstructed_without_contract_violation`; and
5. `static_investigation_inconclusive`.

Trust, lineage, implementation-source, path, timestamp, Git, schema, and
unexpected internal failures abort without publishing a result. Only an
allowlisted stable error raised inside the trusted pure-static registry
reconstruction can support deterministic reproduction. Because that registry
builder interleaves records and logical stages, such an error terminates at
the composite reconstruction step; its mapped `failure_domain_step` is
diagnostic context and does not claim earlier domain steps completed. An
inconclusive result requires an explicit closed observer reason and is never a
catch-all.

The structural comparator is limited to task family, source kind/count,
model-payload bytes, prompt bytes, and runtime-message shape. Record,
Adapter, payload, prompt, message, screenshot, and snapshot content digests
are deliberately excluded from structural causality. Different records are
expected to have different content hashes.

Every valid result keeps historical runtime health, root-cause reproduction,
failed-substage isolation, remediation, recovery-v3, model/CUDA diagnostic
execution, v2 retry, original formal measurement, model evaluation, quality,
safety, repeatability, Serving, promotion, and Runtime eligibility false.
Successor routing can only freeze a separate protocol; it never authorizes the
successor execution.

## Runner and source lineage

The runner is
[`scripts/run_mm005_browser_research_model_evaluation_generation_failure_investigation_v1.py`](../scripts/run_mm005_browser_research_model_evaluation_generation_failure_investigation_v1.py).
Its implementation freeze closure contains exactly the result contract, this
runner, and the focused test. The formal path requires:

- PR #73 to be an ancestor and its config plus all ten protocol sources to
  equal the exact PR #73 Git blobs;
- all three implementation paths to have the same earliest introduction on
  canonical `refs/remotes/origin/master --first-parent` history, equal to the
  formal freeze commit;
- the complete PR #73-to-freeze tree delta to contain exactly the ten reviewed
  implementation/integration/documentation paths, proving every unlisted
  recursive Python dependency remains at the PR #73 tree;
- the three implementation sources to equal the formal merged-master commit
  blobs;
- branch `master`, `HEAD == origin/master`, and a clean worktree;
- the fixed result path to be absent; and
- exclusive `xb` creation, flush, and `fsync`, with zero internal retry.

The canonical-introduction and exact-slice gates run before the default path
builds or exclusively writes a result. A mismatched merge therefore aborts
without consuming the fixed result path.

Runner modes are deliberately distinct:

- `--plan` validates the published protocol lineage and returns a read-only,
  non-eligible plan before this slice merges;
- default mode is the one formal invocation and is forbidden on this feature
  branch; and
- `--check` reads a published result once, binds its freeze to canonical
  mainline history, the exact ten-path slice, PR #73 config/ten-source blobs,
  and three implementation receipts, and only then starts historical Python.
  It creates a temporary `--local --shared` checkout with hooks, LFS filters,
  lazy fetch, inherited `GIT_*`, symlink checkout, and global/system Git config
  disabled; requires the checkout runner to be a regular file exactly equal
  to its freeze blob; and runs it with `python -I -S -B`. The parent accepts
  only a canonical closed summary and re-reads the fixed result bytes before
  returning, so late replacement or deletion fails closed.

The result-publication slice also binds `core.longpaths=true` into every
historical Git command and uses the short `m5gfh-*`/`c` temporary topology.
This prevents Windows from silently omitting deep tracked fixtures and keeps
Python cleanup below the Win32 path budget. Historical worker stdout may have
exactly one terminal LF or the single terminal CRLF produced by Windows text
stdout; CRLF is normalized to LF before the existing strict parse and exact
canonical-byte comparison. Embedded or repeated CR/LF remains invalid.

No mode imports or calls a processor, model, PIL, `torch`, CUDA, browser,
network, training, or Runtime integration. The runner has no mutable output
override.

## Current evidence and limits

The 32-test focused suite covers all five predicate selections, bool/integer
aliases, contradictions, allowlisted versus unknown exceptions, truthful
composite-step sequencing, structural/content separation, real frozen-input
in-memory reconstruction, exact PR #73 Git binding, canonical mainline
introduction, exact tree-diff closure, bootstrap receipts, local/no-lazy Git
isolation, complete 769-path historical materialization, exact historical
runner bytes, LF/CRLF-closed summary routing, late swap/create/delete
rejection, pre-write abort ordering, control-flow marker count/order, clean
aligned master, exclusive publication, unsafe paths and links, attempt-ID
privacy, claim/routing closure, and forbidden capabilities.

A clean shared clone of signed PR #74 merge commit
`c2b04f68dfbb0f96423ecf83a8d73529fdf9d055` executed the default runner once
at `2026-08-29T09:11:14Z`. It exclusively created the 39,843-byte fixed result
with file SHA-256
`2be8caf8dbc35d2741d81d408f21fea08d7961cc970590a25922bc757485ca93`
and report digest
`001b44cdb9d0a11a4be48e10f6653074e4bf407a43daaad1930c6d92e5f8cde7`.
The selected outcome is
`static_pipeline_reconstructed_without_contract_violation`: the static
pipeline rebuilds, the claimed generation failure is not reproduced, and the
Runtime root cause remains unresolved. The formal gate permits only freezing
`MM-005-browser-research-model-evaluation-generation-failure-diagnostic-protocol-v1`;
it does not authorize diagnostic execution or recovery v3.

The pre-result unified validator calls only `result_contract()` and
`runner.run(plan=True)`, audits the exact three-file source closure, and
reports result absent, result invalid, investigation not executed, and Runtime
ineligible. It never calls the default runner or formal result builder.

After a result exists, the unified route skips current protocol semantic
validation, implementation AST audit, and `--plan`, and delegates to
historical `--check`. It still imports the current frozen-v1 runner/protocol/
result modules and uses their strict parser/bootstrap code; it does not claim
zero current-import or parser dependency.

The first real historical check exposed Windows long-path materialization and
terminal-CRLF portability defects in the parent checker. It did not modify the
result or consume another formal attempt. After the bounded parent-only fix,
the exact c2b runner executed under `-I -S -B`, recomputed the saved result,
and returned `checked=true` and `valid=true`. The fixed result bytes remained
unchanged, and the default runner was not rerun.

## Exact next action

Validate and publish the immutable fixed result plus the parent-only Windows
historical-check portability fix in one bounded pull request. Wait for all
checks and review/conflict state, merge only when clear, delete both branch
copies, and restore aligned master. Only then may the separate outcome-neutral
diagnostic protocol be frozen; diagnostic execution remains unauthorized.

## Validation

The published protocol's 16 focused tests pass on local CPython 3.11.15,
3.12.12, and 3.13.7. The result slice's 32 focused tests pass on the same
matrix. Ruff 0.15.22, Ruff format check, scoped strict Mypy 2.3.0,
`py_compile`, protocol `--check`, real historical `--check`, and the complete
CPython 3.11.15, 3.12.12, and 3.13.7 unified offline gates pass. Each unified
gate runs 961 tests with four expected Windows privilege skips and 74 audited
source files, and reports `result_present=true`,
`investigation_executed=true`, `runner_plan_valid=false`,
`runner_check_valid=true`, and `valid=true`.
