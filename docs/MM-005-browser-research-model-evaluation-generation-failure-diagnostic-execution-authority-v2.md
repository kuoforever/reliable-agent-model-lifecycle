# MM-005 Browser Research generation-failure diagnostic execution authority v2

## Status and scope

This gate freezes the separate execution authority required by the final
diagnostic implementation-v2 freeze I2, published through PR #85 as
`ac052a3781246deb7365914dacfa271d37cfef59`. I2 has initial implementation
publication I1 `e185c76e0d0ace44a13e10f06d8644939e1981b8` as its unique direct
parent. The earlier chain remains exact:

```text
P eb2aea3 -> M1 e5e618b -> M2 8c679eb -> I1 e185c76 -> I2 ac052a3 -> A
```

The authority permits exactly one later offline diagnostic-v2 invocation with
zero retry and one attempt per record. It does not consume that invocation,
create `work/evaluation-runs`, a lifecycle lease, owner, progress, output,
success, failure, or staging state, and it does not observe or run a model,
processor, PIL, torch, CUDA workload, GPU resource probe, browser, network,
training, or Runtime integration. The reserved next gate is
`MM-005-browser-research-model-evaluation-generation-failure-diagnostic-execution-v2`.

## Closed authority slice and introduction

The authority commit must have I2 as its unique parent and differ from I2 by
exactly these ten paths:

1. `AI_Infra_LLM_Agent_待做任务清单.md`
2. `PROJECT_STATUS.md`
3. `README.md`
4. `configs/mm005_browser_research_model_evaluation_generation_failure_diagnostic_execution_authority_v2.json`
5. `docs/MM-005-browser-research-model-evaluation-generation-failure-diagnostic-execution-authority-v2.md`
6. `docs/MM-005-browser-research-model-evaluation-generation-failure-diagnostic-implementation-v2.md`
7. `docs/README.md`
8. `scripts/prepare_mm005_browser_research_model_evaluation_generation_failure_diagnostic_execution_authority_v2.py`
9. `scripts/validate_offline.py`
10. `tests/test_mm005_browser_research_model_evaluation_generation_failure_diagnostic_execution_authority_v2.py`

Git supplies the authority commit identity after the commit is created; it is
not self-authored into the commit. The builder accepts only two stages. Before
the artifact is tracked, `HEAD` must equal I2 exactly. Once tracked, the
authority path must have exactly one first-parent introduction at current
`HEAD`, that commit must have I2 as its unique parent, its I2 delta must be the
exact ten paths above, and the current authority bytes must equal the
introduction-commit blob. An arbitrary I2 descendant is not a valid draft
stage. A feature-branch candidate tracked at `HEAD` is not described as merged
or execution-eligible.

## Canonical authority and receipts

The canonical artifact is
`configs/mm005_browser_research_model_evaluation_generation_failure_diagnostic_execution_authority_v2.json`.
It is 2,944 bytes with SHA-256
`b638a7a73b401d6d968f9edc1b351e13394602b7d68dae7789f4485d996f39f0`.
Its closed schema binds P, M1, M2, I1, I2, the registered resource caps, one
formal invocation, zero retry, one attempt per record, and four direct critical
execution-dependency byte receipts:

| Receipt | Bytes | SHA-256 |
|---|---:|---|
| recovery I/O | 13,995 | `7ffd029e...704b1` |
| repeatability runner | 56,740 | `3330e84f...88b0` |
| upstream model runner | 41,803 | `2a86ac6b...23af` |
| v1 dataset runner | 29,571 | `0286e274...f71c` |

The closed authority JSON intentionally does not add an
`implementation_source_receipts` field. Instead, the builder and unified
validator independently require the three implementation sources to equal
their I2 Git blobs and retain I1 as their sole first-parent introduction:

| Source | Bytes | SHA-256 |
|---|---:|---|
| result contract v2 | 84,964 | `8a850a3e...0177d` |
| runner v2 | 108,172 | `8116987a...a1c1` |
| result tests v2 | 119,143 | `0cdd4b55...35ade` |

These are direct registered receipts and lineage checks, not a transitive
Python or native call-graph proof.

## Expected environment and resource boundary

The artifact binds the frozen expected 17-field environment: CPython 3.12.12
on Windows 11/AMD64, RTX 4090 Laptop GPU, CUDA compute capability 8.9, driver
596.49, torch 2.6.0+cu124, transformers 4.49.0, and the remaining exact values
in the canonical JSON. `bitsandbytes` is intentionally outside this 17-field
projection. The caps remain 1,800 seconds, 16,500,000,000 peak allocated GPU
bytes, and 16,500,000,000 peak reserved GPU bytes.

This authority freeze does not claim that the current machine matches those
values. Only after a clean authority merge may execution perform the separate
read-only exact-environment and CUDA-capability observation. Missing,
unverifiable, or unequal fields and resources block model load and CUDA work.

## Builder, validation, and zero-bandwidth boundary

Default builder mode captures and revalidates the Git/source/topology snapshot,
requires the existing ordinary `configs` parent, and writes only the authority
artifact with exclusive `xb` creation and file `fsync`. It never creates a
parent and refuses an existing target. `--check` compares stable bytes before
and after full input revalidation and does not republish anything. Both paths
reject hidden index flags, Git replace/graft state, source drift, authority-byte
race, output-parent/runtime/lifecycle/reserved-staging state, or lineage drift.

All builder Git reads remove ambient `GIT_*` variables case-insensitively,
disable hooks, fsmonitor, commit-graph and LFS filters, set
`GIT_LFS_SKIP_SMUDGE=1` and `GIT_NO_LAZY_FETCH=1`, and use only local history
and blobs. No LFS fetch, pull, fsck, hydration, payload read, or network call is
performed. This preserves the exhausted monthly Git LFS bandwidth boundary.

The new local authority-focused suite checks canonical closure, exact expected
environment/caps/budgets, four critical receipts, three I2 source receipts,
the two-stage lineage, exclusive creation, read-only plan/check, Git hardening,
negative lineage/byte drift, and absent runtime state. Existing required GitHub
jobs continue to run their established 62 stage-aware protocol/result tests
plus pointer/trust-anchor validation and read zero LFS payload bytes; they do
not directly add this local authority test module to the fixed focused list.
The local full offline validator may rehash already hydrated local LFS payload
bytes, but it performs no LFS network transfer, download, or new hydration.

Final draft-stage validation passes 72/72 focused tests on each of CPython
3.11.15, 3.12.12, and 3.13.7: the established 19 protocol-v2 and 43 result-v2
tests plus the 10 authority-v2 tests. The CPython 3.11.15 unified offline gate
passes 1,131 tests with five expected Windows privilege skips, audits 79 source
files, and reports `valid=true`. Ruff 0.15.22, strict Mypy 2.3.0 on the builder,
scoped Mypy on the unified validator, three-version `py_compile`, builder
`--check`, runner `--plan`/`--check`, canonical bytes/hash, exact-ten diff,
non-LFS attributes, and `git diff --check` also pass. None of these commands
invokes formal execution, a model, torch, CUDA workload, or network transfer.

The authority contract sets `diagnostic_execution_authorized=true`, while this
freeze itself keeps `formal_execution_eligible=false`,
`diagnostic_attempt_consumed=false`, `diagnostic_executed=false`,
`model_evaluated=false`, and `runtime_eligible=false`. Plan and check do not
enter the execution path.

## Locked next action

After the authority commit cleanly merges, required exact-HEAD checks pass,
both feature-branch copies are deleted, and local
`master == origin/master == HEAD` equals the sole authority introduction
commit, the only next action is the single registered diagnostic execution-v2
gate. Before invoking it, recheck clean alignment, exact lineage and receipts,
unclaimed topology, authority bytes, the frozen expected environment, and
read-only CUDA capability. Do not add an authority-following closeout commit,
reuse a v1 identity, retry v1, dispatch the manual hydrated-LFS workflow, or
auto-route any eventual terminal into recovery v3.
