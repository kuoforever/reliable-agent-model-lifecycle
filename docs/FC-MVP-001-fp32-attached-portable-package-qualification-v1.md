# FC-MVP-001 FP32 attached portable-package qualification v1

> Status: protocol frozen; independent target-machine execution and formal
> qualification evidence are pending.

## Purpose

This gate decides only whether the exact preferred FP32 attached offline
package is portable to one operationally distinct native Windows target under
the locked user-space environment, same GPU class, fixed compiler, attached
execution form, and registered resource caps.

The protocol does not change the base model, tokenizer, Adapter, compiler,
prompt, generation settings, precision, or execution form. It does not train,
tune against evaluation answers, create merged weights, promote an artifact,
deploy serving, or integrate Runtime/Provider/MCP/Desktop.

## Frozen protocol

The protocol was frozen before any target-machine result at commit
`f8dc9a62471759282ad2b41673d95acd43bf240f`.

| Frozen file | Bytes | SHA-256 |
|---|---:|---|
| `configs/tool_router_fp32_attached_portable_package_qualification_v1.json` | 7,095 | `eceb47c9c952b8ba056abee48a2d55be797145558ac5efcede69d97b9a834577` |
| `scripts/qualify_tool_router_fp32_attached_portable_package.py` | 16,469 | `0b7645d0d8180c56252c9e5ca83e8f74485d7ca79f722e328324281568adefed` |
| `src/fullcycle_bridge/tool_router_fp32_attached_portable_package_qualification.py` | 42,356 | `8929dad009170617defcb2fee3c79efa5a7d9cce534b0478af32dccbf1c50bce` |
| `tests/test_tool_router_fp32_attached_portable_package_qualification.py` | 17,152 | `cf62e1724e60907ea3ce2c7c41589134076e34462bbf825d3f3a555fff33ce42` |

The preregistration has `freeze_status=frozen`. Its source receipts bind the
contract and builder. The test suite independently requires the tracked JSON
to equal the contract-generated frozen preregistration.

## Frozen inputs and execution scope

The gate recomputes the preferred-candidate evidence with SHA-256
`02f66ed79edce17803ddc1ed172c35a995be4ee8ed984cdd49b4e24bc5748c55`.
It reuses the clean-location replay protocol frozen at
`eafd3f646e4ec08dd0a1f76443ccfd416e81fa22`, whose preregistration SHA-256 is
`982d039b2b591d2dab80d489bbbada252c764c82fce94334580807616b22ffff`.

The target replay must retain all of the following:

- Python 3.12.12, PyTorch 2.6.0+cu124, Transformers 4.49.0, PEFT 0.14.0,
  Accelerate 1.3.0, huggingface_hub 0.29.3, safetensors 0.5.3, and tokenizers
  0.21.4;
- one NVIDIA GeForce RTX 4090 Laptop GPU with compute capability 8.9 and the
  registered VRAM value;
- one fresh FP32 attached-model load, one 20-case eval, 20 ordered generation
  calls, and zero retries;
- the fixed compiler, exact UTF-8 raw comparison, exact canonical compiled
  comparison, and existing resource caps; and
- offline execution after the separately permitted materialization phase.

WSL, a second path on the controller, a second virtual environment, or a
second checkout on the same physical host does not satisfy the target-machine
requirement.

## Privacy-preserving machine separation

The preregistration stores a controller separation anchor observed on
2026-08-10. Windows `MachineGuid` and the NVIDIA GPU UUID are normalized and
hashed separately with gate-specific domain-separated SHA-256. Only their
digests and a canonical combined digest are retained. Raw identifiers,
hostname, and machine paths are not recorded.

The target-side builder must run on native Windows. It locally collects the
same two digest classes, binds them to the exact target replay/evidence bytes,
and requires the machine-guid digest, GPU-UUID digest, and combined digest all
to differ from the controller anchor. It also records the target platform,
builder Python, and NVIDIA driver version.

This is a self-observed operational machine-separation receipt. It is not TPM,
TEE, signed remote, or other hardware-backed attestation. The controller
anchor is not historical attestation of the machine that generated every
earlier reference artifact.

## Target execution runbook

Run the already-frozen materializer and replay probe on an independent native
Windows machine, following the materialization, preflight, and offline formal
execution boundaries in
[offline package reproducibility v1](FC-MVP-001-fp32-attached-offline-package-reproducibility-v1.md).
Use a fresh controller/output root so the two frozen replay filenames are
absent before execution.

After the target replay succeeds, run the frozen qualification builder from a
checkout at the protocol freeze commit:

```powershell
python -I scripts\qualify_tool_router_fp32_attached_portable_package.py `
  --protocol-freeze-commit f8dc9a62471759282ad2b41673d95acd43bf240f `
  --clean-repository-root <clean-repository-root> `
  --clean-adapter-root <clean-adapter-root> `
  --target-replay-artifact <target-replay-artifact.json> `
  --target-replay-evidence <target-replay-evidence.json> `
  --output <absent-portable-qualification-evidence.json>
```

The builder independently recomputes the preferred-candidate validator and
the complete target replay validator before collecting the local machine
receipt. The two target artifacts must be new: reuse of either tracked origin
artifact SHA is rejected. The output uses exclusive creation. Later
byte-checking uses the same command plus `--check` and reuses the embedded
machine receipt rather than recollecting a new timestamp.

## Acceptance and failure behavior

All 13 categorical requirements must pass:

1. preferred-candidate gate valid;
2. target replay gate valid;
3. protocol integrity;
4. target machine receipt valid;
5. target machine distinct from the controller;
6. exact package identity and clean resolution;
7. locked environment reproduced;
8. attached execution contract passed;
9. offline execution passed;
10. 20/20 raw outputs exact;
11. 20/20 compiled outputs exact;
12. registered resource caps passed; and
13. limitations disclosed.

Any failed requirement derives
`fp32_attached_portable_package_qualification_incomplete`, preserves
`portable_package_eligible=false`, and routes to
`FC-MVP-001-fp32-attached-portable-package-qualification-failure-classification-v1`.
No failure authorizes changing package bytes or the execution contract.

Only an all-pass result may derive
`fp32_attached_portable_package_qualified_for_distinct_windows_machine_under_locked_environment_fixed_compiler_and_attached_execution`.
Even that bounded result would route to a separate
`FC-MVP-001-fp32-attached-offline-package-promotion-decision-v1`; it would not
itself promote, serve, merge, or integrate the package.

## Validation completed before target execution

The frozen protocol passes the unified offline gate on CPython 3.11.15,
3.12.12, and 3.13.7 with `421 tests`, `valid=true`, and
`source_files_audited=36`; each run has one existing Windows
symlink-privilege skip. The 18 focused tests, Ruff, strict mypy on the new
contract/builder, py_compile, preregistration recomputation, and diff checks
pass.

A native Windows collector smoke test recomputes the controller anchor and
correctly derives `distinct_from_controller=false`, while retaining neither
raw identifier and making no hardware-attestation claim. This proves the
collector and anchor agree on the current controller only. It is not the
required target execution.

One deliberately invalid concurrent three-version test attempt produced a
shared `work/test-fixtures/duplicate.json` file-lock collision. No fixture
remained. Each version was rerun serially and passed; only those serial runs
are valid gate evidence.

## Current limitation and exact next action

No independent target GPU machine or repository self-hosted runner was
available when the protocol was frozen. Therefore no target replay or formal
qualification artifact exists, and cross-machine reproducibility plus
portable-package eligibility remain false.

The single next action is to execute the frozen runbook on one operationally
distinct native Windows machine satisfying the locked environment and same GPU
class, then return the target replay, replay evidence, and qualification
evidence for strict integration. Do not substitute WSL or the controller, and
do not infer promotion, serving, merged-artifact, or Runtime readiness.
