# MM-005 Browser Research generation-failure investigation implementation v1

> **Result: COMPLETE LOCALLY, NOT YET PUBLISHED — the closed result contract,
> model-free runner, focused tests, and pre-result unified validation are
> implemented. The fixed result does not exist and the formal investigation
> has not executed.**

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

No mode imports or calls a processor, model, PIL, `torch`, CUDA, browser,
network, training, or Runtime integration. The runner has no mutable output
override.

## Current evidence and limits

The 30-test focused suite covers all five predicate selections, bool/integer
aliases, contradictions, allowlisted versus unknown exceptions, truthful
composite-step sequencing, structural/content separation, real frozen-input
in-memory reconstruction, exact PR #73 Git binding, canonical mainline
introduction, exact tree-diff closure, bootstrap receipts, local/no-lazy Git
isolation, exact historical runner bytes, closed summary routing, late
swap/create/delete rejection, pre-write abort ordering, control-flow marker
count/order, clean aligned master, exclusive publication, unsafe paths and
links, attempt-ID privacy, claim/routing closure, and forbidden capabilities.

The real frozen inputs currently reconstruct in memory to
`static_pipeline_reconstructed_without_contract_violation`. That is a test of
the deterministic builder with a synthetic timestamp and implementation
commit; it is not the authenticated formal outcome and creates no fixed
result.

The pre-result unified validator calls only `result_contract()` and
`runner.run(plan=True)`, audits the exact three-file source closure, and
reports result absent, result invalid, investigation not executed, and Runtime
ineligible. It never calls the default runner or formal result builder.

After a result exists, the unified route skips current protocol semantic
validation, implementation AST audit, and `--plan`, and delegates to
historical `--check`. It still imports the current frozen-v1 runner/protocol/
result modules and uses their strict parser/bootstrap code; it does not claim
zero current-import or parser dependency.

A real end-to-end `isolated clone -> historical runner -> recomputation ->
closed summary` check cannot execute in this pre-result slice because neither
the merged implementation freeze nor result exists. The separate result slice
must run the real `--check` before publication; mocked component coverage is
not evidence for that future endpoint.

## Exact next action

Validate this bounded implementation slice on Python 3.11, 3.12, and 3.13;
publish it through a clean pull request; wait for checks and review/conflict
state; merge only when clear; delete both branch copies; and restore an
aligned master. Only then may one clean merged-master invocation create
`baseline/mm005-browser-research-model-eval-v2-generation-failure-investigation-v1.json`.
That future result must be independently checked and published in its own
bounded slice before any diagnostic protocol becomes active.

## Validation

The published protocol's 16 focused tests pass on local CPython 3.11.15,
3.12.12, and 3.13.7. The implementation's 30 focused tests pass on the same
matrix. Ruff 0.15.22, Ruff format check, scoped strict Mypy 2.3.0,
`py_compile`, protocol `--check`, and the complete CPython 3.11.15, 3.12.12,
and 3.13.7 unified offline gates pass. Each unified gate runs 959 tests with
four expected Windows privilege skips and 74 audited source files, and reports
`result_present=false`, `investigation_executed=false`,
`runner_plan_valid=true`, `runner_check_valid=false`, and `valid=true`.
