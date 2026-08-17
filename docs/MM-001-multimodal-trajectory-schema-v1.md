# MM-001: Multimodal trajectory schema v1

## Decision

The local schema review completed on 2026-08-17. Text-only and
image-grounded trajectories now share one strict, versioned topology. The
contract is synthetic-only and compatible with the reviewed Lane B v1 bundle
and episode versions. It neither implements capture nor changes the Runtime
repository.

The canonical bindings are:

```text
multimodal_trajectory_schema_version=1
compatible_lane_b_bundle_version=1
compatible_lane_b_episode_version=1
runtime_freeze_commit=324ff2fb5911e332ddb5c5f90eb41296e8faf7a9
lane_b_contract_merge_commit=d1a8e787951c52c7650b23c71ea3df2b6a9ee00d
```

## Contract boundary

Every record binds Runtime, agent, driver, policy, environment, model, model
revision, trajectory-schema, and compatible Lane B versions. Inputs include a
sanitized instruction, available tool schemas, policy context, and bounded
previous steps. Exactly one current pre-action and one current post-action
observation bind content-addressed UIA, document, OCR, or redacted image
evidence according to the declared modality.

The candidate action represents the selected tool, arguments, optional
`bbox`/`ref`, risk, approval requirement, confidence, rejection/fallback, and
current pre-observation evidence. A candidate has no execution authority.
Runtime remains the sole policy and dispatch authority and binds its decision
to the same policy artifact. The state verifier must cover post-observation
and verifier artifacts; model self-report cannot establish success.

## Frozen synthetic evidence

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `schemas/multimodal_trajectory_v1.schema.json` | 21,091 | `sha256:2109dcd2b06e01bda30ea19bc548cb34031811319e23f0bce5dd91a60c32964c` |
| `fixtures/multimodal_trajectory_v1/valid/text-only.json` | 7,387 | `sha256:9162a2e322961434532b320670bacca3267bfe8cd4f5f823a177361ff5207706` |
| `fixtures/multimodal_trajectory_v1/valid/image-grounded.json` | 11,145 | `sha256:89c45460a6ffd4804f9ef855680fd74be18321afa89e94842bffb6ba833f5963` |
| `fixtures/multimodal_trajectory_v1/fixture-metadata.json` | 1,732 | `sha256:784e7258602b5577a26fb80c3c1a87a8539d06d7adc9bbc119a0da478fd496ea` |

The text fixture has ten artifacts, one available tool, no previous step, and
one successful Runtime-dispatched transition. The image-grounded fixture has
17 artifacts, one available tool, one bound previous step, and a second
successful Runtime-dispatched transition. Both remain synthetic,
`dataset_split=unassigned`, `license_status=pending_review`,
`training_eligible=false`, and `execution_eligible=false`.

Four saved parser fixtures pin stable failures for malformed JSON, missing
fields, duplicate keys, and non-finite values. Mutation tests additionally
cover unknown fields, unsafe files, version and digest drift, orphaned or
mis-typed artifacts, modality mismatch, unsupported `bbox`/`ref`, stale
candidate evidence, broken history and observation links, Runtime authority
violations, model self-report, and governance overclaims.

## Reproduction

Run the focused suite with the repository source path explicitly isolated:

```powershell
python -I -c "import runpy,sys; sys.path.insert(0, r'.\src'); runpy.run_path(r'.\tests\test_multimodal_trajectory.py', run_name='__main__')"
```

Run the repository gate:

```powershell
python -I .\scripts\validate_offline.py
```

The local CPython 3.11.15, 3.12.12, and 3.13.7 gates each passed 468 tests
with 3 Windows symlink-privilege skips, `valid=true`, and 40 audited source
files. The focused suite passed 26 tests with 1 Windows symlink-privilege
skip. Ruff, strict mypy, `py_compile`, independent Draft 2020-12 metaschema
validation, metadata hash recomputation, and both valid JSON Schema instance
checks passed. A final no-dependency wheel build contains both trajectory
modules and the `fullcycle-trajectory` console entry point.

## What this proves and does not prove

This evidence closes only `MM-001-multimodal-trajectory-schema-v1`. It proves
deterministic, fail-closed validation of two synthetic modalities under one
versioned topology. It does not prove capture, sanitization, redaction, or
deletion on real data; GUI grounding quality; model training or execution;
dataset split or license approval; cross-machine reproducibility; portable
packaging; serving, promotion, or Runtime eligibility.

At this review's completion, the exact next local gate was
`MM-002-gui-grounding-data-eval-v1`; that gate has since completed.
