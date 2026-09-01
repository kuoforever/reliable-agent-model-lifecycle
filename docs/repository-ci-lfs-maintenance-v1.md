# Repository CI/LFS maintenance v1

## Objective

`repository-ci-lfs-maintenance-v1` removes redundant feature-push CI and
separates repository-pointer checks from hydrated payload integrity without
renaming the three required Python matrix contexts.

The controlled variable is CI transport and gate placement. Model, dataset,
Adapter, evaluation, diagnostic, Runtime, and consumed-output bytes are
unchanged. This maintenance does not authorize another v1 diagnostic
invocation or synthesize a missing terminal.

## Frozen LFS inventory

The canonical
[`repository_ci_lfs_inventory_v1.json`](../configs/repository_ci_lfs_inventory_v1.json)
is 2,293 bytes with SHA-256
`e409ca5cefd51cf6cdcf822c5514985f1788708f2b5a033dbc27873a09cf1f94`.
It binds the exact `.gitattributes` Git blob and all four LFS pointer blobs:

| Path | LFS object bytes | OID |
|---|---:|---|
| `baseline/adapters/fc-mvp-001-lora-sft-v1/adapter_model.safetensors` | 17,462,432 | `sha256:1c58a3d0...3d65659` |
| `baseline/adapters/fc-mvp-001-lora-sft-v2/adapter_model.safetensors` | 17,462,432 | `sha256:efb62471...4f342` |
| `baseline/adapters/mm003-qwen2.5-vl-3b-qlora-sft-v2/adapter_model.safetensors` | 29,529,752 | `sha256:d93d2ea2...14701` |
| `baseline/fc-mvp-001-fp32-attached-merge-numerics-v1-tensors.bin` | 46,069,904 | `sha256:550175df...98a9` |

The total hydrated payload is 110,524,520 bytes. Every Git blob is the exact
canonical 133-byte LFS pointer. The standard-library validator also discovers
all paths with `filter=lfs` from the cached Git attributes, so an unregistered
fifth LFS path fails closed.

## Split gates

The required contexts remain exactly:

- `python-matrix (3.11)`
- `python-matrix (3.12)`
- `python-matrix (3.13)`

Each matrix job checks out full Git history with `lfs: false` and smudge
disabled, then runs
`python -I scripts/validate_repository_ci.py --mode pointer`. The validator
checks the frozen inventory, `.gitattributes`, Git pointer blob/OID/size,
working-tree pointer bytes, every tracked Python file with `py_compile`, and
107 explicit standard-library core tests, and then revalidates all four
pointers before emitting its summary. During those tests, child processes
receive exactly the repository `src` directory as `PYTHONPATH`; inherited path
entries are neither trusted nor appended, and the parent environment is
restored afterward. Its summary states
`scope=pointer_and_stdlib_only`, `full_integrity_verified=false`, and
`lfs_payloads_read=0`. These jobs do not run `validate_offline.py` and do not
read a hydrated LFS payload.

The separate `hydrated-lfs-integrity` job uses Python 3.11. It checks out
pointer-only and first runs the metadata-only validator, which proves that all
four working-tree files are still exact 133-byte pointers while reading zero
LFS payload bytes. It then pulls exactly the four registered paths, runs
`git lfs fsck --objects --pointers HEAD`, streams all 110,524,520 bytes through
the frozen size/SHA-256 validator, and runs the complete
`python -I scripts/validate_offline.py` gate.
Only this job establishes hydrated payload integrity plus the complete
repository gate.

Both jobs use full history, bounded timeouts, read-only repository permission,
and immutable Node 24 action pins. Workflow-level concurrency cancels a stale
run for the same PR or branch. Events are limited to pull requests targeting
`master` and pushes to `master`, eliminating the former feature-push/PR
duplicate.

## Rollout and expected transfer

The existing ruleset keeps only the three matrix contexts required while this
workflow is introduced. `hydrated-lfs-integrity` must be added as a fourth
required context after all four jobs pass on both the maintenance pull request
and its post-merge `master` run; staging the ruleset this way avoids a
required-check deadlock.

For one feature push, one PR run, and one post-merge run, the old workflow
hydrated nine copies of the four objects: 994,720,680 bytes, or approximately
0.926 GiB. The split workflow hydrates two copies: 221,049,040 bytes, or
approximately 0.206 GiB. This is a 77.8% reduction in LFS payload transfer for
that lifecycle, excluding ordinary Git checkout bytes and service-side cache
effects.

## Evidence boundary

Pointer-only success proves Git metadata, pointer policy, source syntax, and
the explicit core tests for that Python minor. It does not prove LFS payload
availability or complete repository integrity. Hydrated success proves the
four registered payload receipts and the existing complete offline gate; it
does not establish a new model result, quality improvement, Runtime cause, or
diagnostic execution.

After this maintenance merges cleanly and branch cleanup plus the four-job
post-merge observation are complete, the only product successor remains a new
identity sequence:

```text
diagnostic-protocol-v2
        -> implementation-v2
        -> execution-authority-v2
        -> exact-once execution-v2
```

That future execution is not a v1 retry, and automatic recovery v3 remains
unauthorized.
