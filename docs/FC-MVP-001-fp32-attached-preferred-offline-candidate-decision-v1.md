# FC-MVP-001 FP32 attached preferred offline candidate decision v1

## Outcome

The frozen metadata-only decision derives
`fp32_attached_preferred_offline_candidate_under_fixed_compiler_attached_execution_and_registered_resource_caps`,
`formal_gate_passed=true`, and `preferred_offline_candidate=true` for the exact
eligible FP32 attached composite package.

The claim means only that this package is the preferred next offline candidate
for portable-package qualification under the fixed compiler, attached-only
execution form, and the already registered resource caps. Portable-package,
cross-machine, serving, promotion, merged-artifact, and Runtime claims remain
false.

## Frozen protocol and evidence

The outcome-neutral categorical decision protocol was frozen before formal
evidence generation at
`1f9aeecda71ad7f758a905b1eec3dccb3885e10f`.

| Item | Bytes | SHA-256 |
|---|---:|---|
| Preregistration | 5,158 | `75f25ceebb6a9428ad3d92f4ecc778d8725e1d52e32367ff8db3cb2ac3125f21` |
| Contract source | 32,616 | `501f67b49b0e1264c9efa63520a67d393669721f771c5ebbd1e76da218ad04f7` |
| Builder source | 8,723 | `758edd8574babda2b203f74a399fdcb7657af27d8c2a084500547dbc5414dece` |
| Focused test source | 12,804 | `54e2f0571b24c9f6c9559d41343652314e771f2497859a701771a7e7986e7786` |
| Formal evidence | 9,619 | `02f66ed79edce17803ddc1ed172c35a995be4ee8ed984cdd49b4e24bc5748c55` |

The formal report digest is
`67398fb9dbc1c144c2bba218d3028babee2f56cf12ca5e3f10a00d44453265f6`.
The builder `--check` path reproduces the evidence byte for byte.

## Bound decision inputs

The builder authenticates and recomputes both canonical upstream validators:

| Evidence | SHA-256 | Role |
|---|---|---|
| Frozen artifact eligibility review | `81977f318c6bcfed8d3844575dc245d4b94c2636a2359165f9aa5553c9b006f8` | BF16/FP32 compiled quality, compiler dependency, resource, and execution-form comparison |
| Offline artifact eligibility reassessment | `0cccb2a7c7cdc24c824ee0ca4606f8c14e9b561473e50e8b31072291357b15ed` | Exact composite package eligibility, replay, origin, and portability boundary |

The BF16 path is a frozen compiled-quality and resource reference. This gate
does not claim that BF16 is a separately complete or eligible offline package.

## Decision facts

The selection rubric uses categorical requirements rather than a post-hoc
weighted score.

| Dimension | BF16 attached reference | FP32 attached candidate | Decision boundary |
|---|---:|---:|---|
| Compiled argument exact match | `0.20` | `0.25` | improved |
| Compiled argument field F1 | `0.2608695652173913` | `0.29787234042553196` | improved |
| Compiled tool accuracy | `0.95` | `0.95` | equal |
| Compiled risk macro F1 | `0.7095238095238096` | `0.7095238095238096` | equal |
| Raw semantic validity | `0.85` | `0.80` | regression disclosed; compiler remains required |
| Full-eval elapsed seconds | `76.99041939998278` | `71.6701673999778` | ratio `0.9308972201805388`; stable speedup not established |
| Peak allocated GPU bytes | `3,150,315,520` | `6,267,895,296` | ratio `1.9896087411587269`; within the registered `6,300,631,040` cap |

The only strict per-example improvement is `eval-016.arguments`. There are
zero compiled regression events and all seven frozen compiled safety checks
pass. Only one registered full-eval run exists, so repeat variance remains
unestimated. The exact package binds the required `compile_decision` v1 and
the `attached_factorized_lora` execution form; neither may be removed from the
candidate identity.

## Gate results

All 12 preregistered gates are true:

1. `attached_execution_form_bound`
2. `comparison_reference_bound`
3. `compiled_quality_strictly_improved`
4. `compiled_safety_and_non_regression_passed`
5. `compiler_dependency_bound`
6. `decision_limitations_disclosed`
7. `offline_artifact_eligible`
8. `portability_boundary_acknowledged`
9. `protocol_integrity`
10. `registered_resource_gate_passed`
11. `same_environment_reproducibility_established`
12. `upstream_protocols_valid`

There is no remaining blocker inside the declared preference-decision scope.
The two downstream open findings are exactly
`cross_machine_reproducibility_unestablished` and
`portable_package_eligibility_unestablished`.

## Claims and limits

The decision uses no network, model load, generation, training, or new
evaluation and saves no model or tensor payload. It does not establish:

- cross-machine, cross-driver, or cross-library reproducibility;
- portable-package eligibility;
- a stable FP32 speedup, serving capacity, latency, or cost;
- generalization beyond the frozen 20-case set;
- artifact promotion, merged-artifact permission, serving readiness, or
  Runtime/Provider/MCP/Desktop eligibility.

## Validation

- Focused decision tests: `12/12` pass.
- Unified offline gate on local CPython 3.11.15, 3.12.12, and 3.13.7: `403`
  tests pass with `valid=true`, one platform privilege skip, and `35` source
  files audited on each interpreter.
- Ruff, strict mypy on the typed decision scope, py_compile, builder `--check`,
  and `git diff --check` pass.

The clean pull-request CI matrix independently passes the same 403-test gate
with `valid=true` and 35 source files audited on CPython 3.11.15, 3.12.13, and
3.13.14.

## Locked next action

The single next gate is
`FC-MVP-001-fp32-attached-portable-package-qualification-v1`. It must qualify
portable-package status with explicit cross-machine behavior and environment
evidence while keeping promotion, serving, and Runtime integration prohibited.
