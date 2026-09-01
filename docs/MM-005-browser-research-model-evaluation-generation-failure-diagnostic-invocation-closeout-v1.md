# MM-005 Browser Research generation-failure diagnostic invocation closeout v1

## Status and evidence boundary

This model-free closeout retires the single v1 diagnostic invocation without
inventing a diagnostic terminal. PR #78 published the 2,706-byte execution
authority as signed squash commit
`0a271e2c27c65e9595953dadb98200ea5ec51acb`, whose sole parent is the PR #77
implementation commit `7da39396c951a9248fe49c1bd69080923b827fa1`.
The authority artifact has exactly one first-parent introduction commit and
SHA-256
`903e681c2957e185da36ed1f991cc5b339b0e692e8c730da63069690277b9e6b`.

The formal workspace was clean and aligned at that authority commit. The
authority lineage, four frozen dependency receipts, hydrated model and Adapter
inputs, local dependency wheel, exact 17-field Windows/CUDA environment, and
read-only GPU capability preflight all passed. The v1 output root, lifecycle
lease, and reserved staging siblings were absent before invocation.

The registered command was invoked exactly once:

```text
work/training-env/Scripts/python.exe -I -B -X pycache_prefix=NUL scripts/run_mm005_browser_research_model_evaluation_generation_failure_diagnostic_v1.py --execute
```

It exited with code `1` and controller-observed exception type
`RecoveryIOError` before any diagnostic attempt claim. The authority's one
formal-invocation budget is therefore spent, its retry budget remains zero,
and the same identity must never be invoked again.

## Pre-claim implementation defect

The frozen runner first validates execution state, then constructs a
`DirectoryTreeGuard` for `work/evaluation-runs`, and only after that would
publish the lifecycle lease and atomically claim owner plus genesis. A fresh
clean worktree had no `work/evaluation-runs` directory. `DirectoryTreeGuard`
requires every guarded directory to exist, so guard construction raised before
the lifecycle publication, owner/genesis claim, terminal-handler scope, model
body, or CUDA workload.

The implementation tests correctly allowed a safe missing output parent for
read-only plan/check and tested owner/lifecycle crash staging, but they did not
exercise the execute path from a fresh missing output parent. That gap is the
bounded v1 implementation defect recorded here. It does not establish anything
about the historical generation failure, Runtime health, model/Adapter output,
quality, or causal origin.

## Why no diagnostic failure artifact exists

The frozen failure grammar is owner-bound. Its minimum journal state is the
`attempt_claimed` genesis frame; the six `pre_record_lifecycle` alternatives
are all non-empty prefixes beginning with that frame. There is no zero-owner,
zero-frame failure scope. The v1 process stopped before owner/genesis, leaving:

- no output parent or output root;
- no lifecycle lease root or lease;
- no attempt owner or progress journal;
- no success or failure terminal;
- no reserved staging sibling.

Consequently, the failure cannot be represented by `pre_record_lifecycle` or
any other frozen terminal scope. Writing `diagnostic-failure.json`, selecting
`diagnostic_inconclusive`, or claiming
`diagnostic_protocol_or_lineage_invalid` would synthesize evidence that the
authenticated state does not contain. The formal selected outcome remains
`null`; controller observation is not formal terminal telemetry.

## Canonical closeout

The canonical closeout is 6,507 bytes with file SHA-256
`d8a64be5b0361322246faf4eeccde04f9921e0a9c586f3498b188a6477d1ddce`:

- [invocation closeout](../baseline/mm005-browser-research-model-eval-v2-generation-failure-diagnostic-v1-invocation-closeout.json)

It binds the PR #76 protocol commit, PR #77 implementation commit, PR #78
authority artifact and unique introduction, exact frozen v1 runner bytes, and
exact recovery-I/O bytes. It records one observed formal invocation, zero
remaining formal invocations, zero retry, process exit code `1`, the pre-claim
boundary, absent durable runtime topology, unavailable failure scope, no formal
outcome, and fail-closed claims. It persists neither raw exception message nor
traceback and creates no runtime or terminal artifact.

## Locked next action

The immediate bounded detour is `repository-ci-lfs-maintenance-v1`:

1. remove duplicate feature-push and pull-request CI execution while preserving
   the required check context;
2. add workflow concurrency cancellation and job timeouts;
3. run the three-version pointer-only contract without hydrating LFS payloads;
4. keep one separate hydrated integrity gate for the large Adapter payload.

After that maintenance merge, resume only with a new diagnostic v2 experiment,
run, and output identity in this order:

```text
diagnostic-protocol-v2
        -> diagnostic-implementation-v2
        -> diagnostic-execution-authority-v2
        -> diagnostic-execution-v2
```

That future chain may fix safe output-parent creation and add a fresh-worktree
execute-path regression test. It is not a retry of v1. V1 output-parent
workaround execution, terminal synthesis, and automatic recovery v3 remain
unauthorized.

## Validation

The focused closeout suite passes 7/7 tests. The canonical builder `--check`
reproduces the artifact without mutation, validates the authority's unique
first-parent introduction and parent, binds exact frozen source blobs, and
statically confirms guard-before-lifecycle-before-claim ordering with no
output-parent creation step. CPython 3.11.15, 3.12.12, and 3.13.7 each pass
the complete unified gate with 1,039 tests, four expected Windows privilege
skips, 77 audited source files, and `valid=true`. Ruff 0.15.2, strict Mypy
2.3.0, three-version `py_compile`, and `git diff --check` also pass.
