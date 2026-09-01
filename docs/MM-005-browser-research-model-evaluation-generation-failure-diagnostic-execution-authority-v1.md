# MM-005 Browser Research generation-failure diagnostic execution authority v1

## Status and scope

This gate freezes the separate execution authority required by the model-free
diagnostic implementation published through PR #77 as signed squash commit
`7da39396c951a9248fe49c1bd69080923b827fa1`.

The authority permits exactly one later offline diagnostic invocation with zero
retry. It does not consume that invocation, create an owner, progress journal,
lifecycle lease, output root, success, or failure artifact, and it does not run
a model, processor, PIL, torch, CUDA workload, browser, network, training, or
Runtime integration. The reserved next gate is
`MM-005-browser-research-model-evaluation-generation-failure-diagnostic-execution-v1`.

## Closed authority slice

The reviewed authority commit differs from the PR #77 implementation freeze by
exactly the ten paths pre-registered in the implementation contract: the three
canonical trackers, this document and the implementation document, the docs
index, one canonical authority artifact, its model-free builder, the unified
validator, and one focused test module. No implementation, runner, protocol,
critical dependency, frozen input, consumed output, or Runtime path changes.

The canonical artifact is
`configs/mm005_browser_research_model_evaluation_generation_failure_diagnostic_execution_authority_v1.json`.
It binds the PR #77 implementation commit, all registered resource caps, one
formal invocation, zero retry, one attempt per record, and byte receipts for the
four critical execution dependencies. Those receipts are direct reviewed
evidence; they are not represented as a transitive Python call-graph proof.

## Environment and publication boundary

The expected environment is the exact 17-field projection from the frozen v2
candidate: CPython 3.12.12 on Windows/AMD64, RTX 4090 Laptop GPU, CUDA compute
capability 8.9, driver 596.49, torch 2.6.0+cu124, transformers 4.49.0, and the
remaining pinned dependency versions in the canonical artifact. Before model
load or CUDA workload, the runner must observe an exact field-for-field match;
missing or unverifiable capacity fails closed.

The artifact is not executable authority until it is cleanly merged. The later
execution requires `master == origin/master == HEAD`, and `HEAD` must equal the
authority artifact's unique first-parent introduction commit. Its tree delta
from PR #77 must equal the exact ten-path slice, every dependency receipt must
equal the introduction-commit blob, hidden index flags and fsmonitor are
forbidden, and every reserved owner/lifecycle/unknown staging sibling must be
absent. An authority-following commit blocks both execution and automatic
reconciliation.

## Validation and claim boundary

The focused authority tests reproduce the canonical artifact, validate the
implementation/environment/budget binding, verify all four dependency receipts,
check the exact ten-path slice, and prove `--check` is read-only. The complete
offline gate also exercises the predecessor protocol and implementation suites
without entering the execution path.

All 5 authority-focused, 40 implementation-focused, and 26 predecessor-protocol
tests pass on local CPython 3.11.15, 3.12.12, and 3.13.7. Each complete unified
gate passes 1,032 tests with four expected Windows privilege skips, 76 audited
source files, and `valid=true`. The model-free builder check, runner plan/check,
exact 17-field environment preflight, Ruff 0.15.22 check and format, strict Mypy
2.3.0, three-version `py_compile`, and `git diff --check` also pass.

This gate establishes only that the authority artifact and preflight contract
are frozen and publishable. It does not establish that the current machine
matches at execution time, that the diagnostic will complete, that the historic
failure will reproduce, that a checkpoint interval identifies causal origin,
or that recovery v3, Runtime eligibility, quality, safety, repeatability,
portability, serving, or promotion is justified.

## Locked next action

After a clean authority merge, both feature-branch copies are deleted, and local
`master == origin/master == HEAD` equals the authority introduction commit, the
only next action is the single registered
`MM-005-browser-research-model-evaluation-generation-failure-diagnostic-execution-v1`
gate. Do not add a closeout commit before that execution, reuse v1/v2 identities,
retry a consumed attempt, or auto-route a diagnostic outcome into recovery v3.
