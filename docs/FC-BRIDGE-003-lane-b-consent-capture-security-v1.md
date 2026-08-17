# FC-BRIDGE-003: Lane B consent, capture, and security contract v1

## Decision

The local contract review completed on 2026-08-17. Lane B remains a separate,
disabled-by-default data lane for explicitly consented rich training episodes.
It does not change the automatic Lane A Runtime export or any Runtime code.

The v1 review bundle contains three independently versioned records:

```text
explicit run-scoped consent
    -> quarantined content-addressed episode references
    -> complete deletion receipt
```

The canonical versions are:

```text
lane_b_bundle_version=1
lane_b_consent_version=1
lane_b_episode_version=1
lane_b_deletion_receipt_version=1
runtime_freeze_commit=324ff2fb5911e332ddb5c5f90eb41296e8faf7a9
```

## Consent and capture boundary

The validator requires exact, closed records and rejects unknown fields. The
consent must be explicit, run-scoped, time-bounded, application-bounded, and
acknowledge a visible capture indicator. Wildcard application scope,
background capture, automatic Runtime export, and network upload are rejected.
Retention is bounded to 1–90 days and must support deletion on request.

Capture declarations require a separate adapter and storage namespace, local
sanitization before write, image redaction before write, content-addressed
artifact references, and no mutation of the source safe trace. The contract
forbids API keys or tokens, assigned-secret plaintext, memory, continuation,
cooperative-control records, authority handoff/resume state, and unredacted
sensitive content.

## Authority and evidence boundary

Each episode binds exact Runtime, model, policy, environment, observation,
candidate-action, Runtime-decision, tool-result, post-observation, and
state-verifier references. Model output is only a candidate and has
`execution_authority=none`. Runtime policy remains the sole dispatch
authority; no Runner, MCP, Desktop, approval, grounding, budget, or recovery
boundary can be bypassed.

Success labels must be state-based and must not use model self-report. A
deletion receipt must bind the episode digest, cover every artifact ID and
content digest, report zero remaining artifacts, and retain no raw content.

## Frozen synthetic evidence

The review fixture is intentionally synthetic and reference-only:

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `schemas/lane_b_capture_bundle_v1.schema.json` | 23,929 | `sha256:634089a84a3d9f63ede12ab8bd0ce905b03a8891dfaf2dedd547a73f2ee49368` |
| `fixtures/lane_b_v1/valid/minimal-bundle.json` | 11,820 | `sha256:c0d90c1b355e902c730a1048cdd5baec03f73d174c662389943d2d4649909074` |

The fixture contains nine synthetic content references, one transition, and a
complete synthetic deletion receipt. It remains
`training_use=quarantine_review_only`, `dataset_split=unassigned`,
`license_status=pending_review`, and `training_eligible=false`. Four saved
invalid fixtures pin stable errors for malformed JSON, missing consent,
unknown fields, and unsupported versions. Mutation tests additionally cover
consent reuse, scope and retention drift, unsafe files, duplicate JSON keys,
non-finite values, content/binding drift, authority violations, model
self-report, and incomplete deletion.

## Reproduction

Run the focused contract suite:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
python .\tests\test_lane_b.py
```

Run the repository gate:

```powershell
python -I .\scripts\validate_offline.py
```

The local CPython 3.11.15, 3.12.12, and 3.13.7 gates each passed 442 tests with
2 Windows symlink-privilege skips, `valid=true`, and 38 audited source files.
The focused suite passed 21 tests with 1 Windows symlink-privilege skip. Ruff,
strict mypy, and `py_compile` passed on the scoped Python files. A final
no-dependency wheel build contains both Lane B modules and the
`fullcycle-lane-b` console entry point.

## What this proves and does not prove

This evidence closes the Lane B v1 consent/capture/security **contract review**
only. It proves deterministic fail-closed validation of a synthetic review
bundle. It does not prove that a capture adapter exists, that real
sanitization/redaction/storage/deletion was executed, that a real episode was
collected, that a dataset split or license was approved, or that any episode
is eligible for training. It adds no model, serving, deployment, promotion,
or Runtime eligibility claim.

At this review's completion, the exact next local gate was
`MM-001-multimodal-trajectory-schema-v1`; that gate has since completed.
