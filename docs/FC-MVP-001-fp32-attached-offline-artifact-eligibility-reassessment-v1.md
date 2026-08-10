# FC-MVP-001 FP32 attached offline artifact eligibility reassessment v1

## Outcome

The frozen metadata-only reassessment derives
`fp32_attached_fixed_compiler_favorable_eval_offline_artifact_package_eligible`,
`formal_gate_passed=true`, and `offline_artifact_eligible=true` for the exact
FP32 attached factorized-LoRA composite package.

This decision is intentionally narrow. It does not establish a portable
package, cross-machine reproducibility, preferred-candidate status, serving
readiness, artifact promotion, a merged artifact, or Runtime eligibility.

## Frozen protocol and formal evidence

The protocol was frozen before evidence generation at
`2a5db8afaf90a3557d6d8d8cd808089d305d83e1`.

| Item | Bytes | SHA-256 |
|---|---:|---|
| Preregistration | 4,920 | `f1fc627d3d20f9c954f93e0cd4c930b22f592c48d2f4af72220c184f2e32c662` |
| Contract source | 30,480 | `958ebf9b1b1a3c3cd37b18318e9572c1c36e502d090772a9e2165b9d1d4d75c3` |
| Builder source | 13,180 | `29a25968306efef47b472d2e0ef0eb4e8a17a6ed3987cdd4e81c4bda044cbcd4` |
| Focused test source | 13,061 | `e4fb86fd8edb86c3532e73ff11769349dc044c825e9eeced5a7876f5d1e07532` |
| Formal evidence | 9,747 | `0cccb2a7c7cdc24c824ee0ca4606f8c14e9b561473e50e8b31072291357b15ed` |

The formal report digest is
`de2efef12eb504d06f7e3cf97b09d6844059f1595e388f8eafcaeb316ef2c7ce`.
The builder `--check` path reproduces the evidence byte for byte.

## Bound upstream evidence

The reassessment binds and recomputes the canonical validators for four
repository-local artifacts:

| Evidence layer | SHA-256 | Established boundary |
|---|---|---|
| Frozen artifact eligibility review | `81977f318c6bcfed8d3844575dc245d4b94c2636a2359165f9aa5553c9b006f8` | Fixed-compiler quality favorable; six package blockers remained at that gate |
| Offline package manifest | `4125f2eef2a4b8f07015169ac7fb77b830514e053a4624aa703e5f5a64943eb0` | Complete composite identity and all six package blockers resolved |
| Clean-location reproducibility | `0e0d2174f4723ab42a5c11375cee10a819e32737810f63111d098decc2984044` | Same recorded environment exact 20-case raw and compiled replay |
| Remote revision-origin attestation | `cdde41aed18e2fecccea1833f16cea4fc808eb5d212376c96f3e2763fcef7cfd` | Fixed GitHub and Hugging Face hosted revision origins |

The manifest layer resolves the review's six exact blockers:

- `base_model_revision_binding_missing`
- `composite_manifest_missing`
- `package_use_and_limitations_documentation_incomplete`
- `portable_base_model_binding_missing`
- `required_compiler_binding_missing`
- `tokenizer_file_manifest_missing`

The word `portable` in the historical blocker identifies a missing package
binding; resolving it does not establish portable-package eligibility.

## Gate results

All nine preregistered gates are true:

1. `behavioral_reproducibility_established`
2. `clean_location_resolution_established`
3. `compiled_quality_evidence_favorable`
4. `metadata_complete`
5. `offline_package_identity_complete`
6. `prior_package_blockers_resolved`
7. `protocol_integrity`
8. `remote_revision_origin_attested`
9. `repository_local_evidence_usable`

The reassessment has no remaining blocking finding within its declared
eligibility scope. It uses no network, model load, generation, training, or
new evaluation. It saves no model or tensor payload and mutates none of the
bound package components or upstream evidence.

## Claims and limits

The positive claim is limited to the fixed composite package with favorable
fixed-compiler evaluation, same-recorded-environment exact replay, and hosted
revision origin. The following remain false or unestablished:

- cross-machine reproducibility and portable-package eligibility;
- preferred offline candidate status;
- serving readiness, artifact promotion, or merged-artifact permission;
- Runtime, Provider, MCP, or Desktop integration eligibility;
- author identity or signature, supply-chain signature, and historical
  transparency-log attestation;
- hermetic or transitive dependency provenance.

## Validation

- Focused reassessment tests: `12/12` pass.
- Unified offline gate on local CPython 3.11.15, 3.12.12, and 3.13.7: `391`
  tests pass with `valid=true`, one platform privilege skip, and `34` source
  files audited on each interpreter.
- Ruff, strict mypy on the typed reassessment scope, py_compile, builder
  `--check`, and `git diff --check` pass.

The clean pull-request CI matrix independently passes the same 391-test gate
with `valid=true` and 34 source files audited on CPython 3.11.15, 3.12.13, and
3.13.14.

## Locked next action

The single next gate is
`FC-MVP-001-fp32-attached-preferred-offline-candidate-decision-v1`. It must
compare frozen quality, compiler dependency, resource, execution-form, and
portability evidence without promotion, serving, or Runtime integration.
