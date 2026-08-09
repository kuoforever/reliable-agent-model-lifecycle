# FC-MVP-001 FP32 attached offline package reproducibility v1

## Outcome

`FC-MVP-001-fp32-attached-offline-package-reproducibility-v1` completed its
single pre-registered formal replay locally on 2026-08-06. A fresh checkout and
freshly downloaded pinned base snapshot resolved the exact unchanged FP32
attached LoRA package in a caller-supplied clean location. In the same recorded
software and GPU environment, all 20 raw model outputs and all 20 compiled
decisions exactly reproduce the frozen reference.

Strict recomputation derives the classification
`fp32_attached_same_environment_clean_location_behavior_exactly_reproduced`
and `formal_gate_passed=true`. The result establishes clean-location
resolution and same-recorded-environment behavioral reproducibility for this
one fixed 20-case replay. It does not establish remote revision origin,
cross-machine portability, repeat variance, serving readiness, promotion, or
Runtime eligibility.

## Frozen protocol and tracked evidence

The materialization, execution, and comparison protocol was frozen before the
formal clean-location replay at commit
`eafd3f646e4ec08dd0a1f76443ccfd416e81fa22`.

The 15,606-byte preregistration is
`configs/tool_router_fp32_attached_offline_package_reproducibility_v1.json`
with raw-file SHA-256
`982d039b2b591d2dab80d489bbbada252c764c82fce94334580807616b22ffff`.
It binds the external manifest and reference artifacts, the exact source
closure, one candidate, one fresh load, 20 ordered generation calls, zero
retry, exact raw-byte and compiled-canonical comparisons, and fixed resource
caps.

The formal tracked artifacts are:

- `baseline/tool-router-fp32-attached-offline-package-reproducibility-v1-predictions.json`,
  33,942 bytes, SHA-256
  `a0e99e80e091d3d6c191e3863449a6a5298d7f0d3a23cc6d786968562e6d2a46`;
- `baseline/fc-mvp-001-fp32-attached-offline-package-reproducibility-v1.json`,
  11,434 bytes, SHA-256
  `0e0d2174f4723ab42a5c11375cee10a819e32737810f63111d098decc2984044`.

The unified offline validator treats the preregistration, replay, evidence,
manifest, reference predictions, reference evidence, fixed eval, freeze
commit, and protocol source hashes as external trust inputs. It rebuilds the
complete evidence object instead of trusting the runner's recorded decisions.

## Clean-location materialization

The formal materialization used an exclusively created destination whose
identifier is `0fd9083350344509b1896d27f3ade5f4`. It performed a fresh HTTPS Git
fetch of the frozen commit, an exact local Git LFS checkout of the Adapter
object, and a pinned Hugging Face snapshot download for
`Qwen/Qwen2.5-1.5B-Instruct` revision
`989aa7980e4cf806f80c7fef2b1adb7bc71aa306`.

Strict manifest resolution passed without issues:

| Group | Files | Matched bytes |
|---|---:|---:|
| Base model and tokenizer | 9/9 | 3,098,971,928 |
| Adapter | 3/3 | 17,468,332 |
| Repository source closure | 15/15 | 233,571 |

The clean resolution digest is
`589d25652e91b93cc8be9f37708beb0badb74a5e7ea1775ba7317e949d1080e4`.
The clean checkout `HEAD` exactly matched the protocol freeze commit and
`git status --porcelain=v1 --ignored` was empty before and after preflight.
The receipt records no absolute paths, symlinks, reparse points, hardlinks,
overwrite, alternate remote, alternate revision, or historical Adapter base
path use.

Network access was allowed only during materialization. Execution used the
destination-scoped cache and recorded `execution_network_used=false`. On
Windows, the frozen materializer gives only the child downloader's
`--local-dir` argument an extended-length path so the 260-character temporary
weight path can complete; stored layout and receipt paths remain ordinary
relative paths. The Git LFS step separately verifies the one expected object
before a local-only checkout replaces the pointer file. These are transport
controls, not remote-origin attestation.

## Preflight and formal execution

The clean-checkout runner first executed `--preflight-only`. It returned
`eligible=true`, `generate_calls=0`, `model_loaded=false`,
`runtime_imported=false`, and `outputs_created=false`. Thus preflight checked
the frozen static contract and materialization receipt without consuming the
formal model attempt.

The one formal run used:

- Python 3.12.12;
- PyTorch 2.6.0+cu124 and CUDA 12.4;
- Transformers 4.49.0, PEFT 0.14.0, Accelerate 1.3.0, and
  huggingface_hub 0.29.3;
- one NVIDIA GeForce RTX 4090 Laptop GPU with compute capability 8.9;
- one fresh FP32 base-model load and the unchanged attached FP32 LoRA;
- 20 ordered generation calls, no warmup, retry, fallback, training, data
  change, prompt change, compiler change, precision change, or weight change.

The precision audit records 1,543,714,304 FP32 base elements, 4,358,144 FP32
Adapter elements across 224 parameter tensors and 112 LoRA target modules, and
64 FP32 buffer elements. No model artifact or tensor payload was saved.

## Behavioral and resource result

The replay observes 20/20 exact UTF-8 raw outputs and 20/20 exact canonical
compiled outputs. There are no raw mismatches, compiled mismatches, or
compilation failures. The reference and observed digests are identical:

- raw outputs:
  `0ea00c3d73ba40a158d8fb54862d334c42d37be0f895455ea12788240fa2af28`;
- compiled outputs:
  `e6ae4e8f825085e72be476fe340a37a8b1d3f2488a078474c5766e085d6e4e0c`.

All pre-registered resource caps pass:

| Measure | Observed | Maximum | Result |
|---|---:|---:|---|
| Measured replay elapsed time | 38.108256999985315 s | 153.98083879996557 s | pass |
| Peak allocated GPU memory | 6,267,895,296 B | 6,300,631,040 B | pass |
| Allocated before load | 0 B | 16,777,216 B | pass |
| Allocated after release | 8,519,680 B | 16,777,216 B | pass |

The enclosing runner process took 49.7 seconds wall-clock time. That is not the
registered measured replay interval. Peak GPU memory passed with only
32,735,744 bytes, about 31.219 MiB, of headroom; this is evidence that this run
met its cap, not evidence of broad deployment capacity.

## Decision boundary

All seven registered gates pass: metadata validation, materialization,
clean-location resolution, environment, execution contract, behavioral replay,
and resources. Derived claims set metadata completeness, package identity,
clean-location resolution, and the scoped behavioral reproduction to true.

The only remaining blocking finding is
`remote_revision_origin_unverified`. Fresh network retrieval proves that the
transport completed and the resulting bytes match the externally authenticated
manifest. It does not independently establish that the remote service's named
revision is the authoritative origin of those bytes.

Accordingly all of the following remain false:

- `remote_revision_origin_attested`;
- offline-artifact and portable-package eligibility;
- preferred-candidate status;
- serving readiness;
- artifact promotion and merged-artifact permission; and
- Runtime eligibility and Runtime/Provider/MCP/Desktop integration.

The evidence also does not establish cross-machine, cross-driver, or
cross-library reproducibility; transitive dependency hash completeness;
external execution-count attestation; exclusion of alternate runs; full-eval
repeat variance; generalization; production safety; throughput; or cost.

## Validation evidence

The unified offline gate passes with `valid=true`, `351 tests`, and
`source_files_audited=32` on CPython 3.11.15, 3.12.12, and 3.13.7. Each version
has one Windows symlink-privilege skip. The 56 focused protocol tests pass with
the same single skip. Ruff, strict mypy on the typed core/materializer/runner
scope, `py_compile`, and `git diff --check` also pass.

An independent read-only audit found no P0, P1, or P2 issue. It independently
recomputed replay and evidence hashes, all raw and compiled record hashes,
resource-cap arithmetic, materialization and clean-resolution digests, freeze
commit source blobs, path redaction, offline/network separation, and all
fail-closed eligibility claims.

## Next gate

The single next objective is
`FC-MVP-001-fp32-attached-remote-revision-origin-attestation-v1`:
independently attest the pinned remote revision origin while keeping all
promotion, serving, and Runtime claims false. No part of that next gate is
implemented or claimed by this evidence.
