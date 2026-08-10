"""Fail-closed offline-artifact eligibility reassessment for the FP32 package.

The contract consumes authenticated projections from the already-frozen
quality review, composite manifest, clean-location replay, and hosted-origin
gates.  It derives only offline-artifact eligibility.  Portable-package,
preferred-candidate, serving, promotion, merged-artifact, and Runtime decisions
remain separate and false.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from typing import Any, Mapping, NoReturn

from .consumer import canonical_json_bytes


PREREGISTRATION_VERSION = 1
EVIDENCE_VERSION = 1
GATE_ID = (
    "FC-MVP-001-fp32-attached-offline-artifact-eligibility-reassessment-v1"
)
EXPERIMENT_ID = (
    "fc-mvp-001-fp32-attached-offline-artifact-eligibility-reassessment-v1"
)
PACKAGE_ID = "fc-mvp-001-fp32-attached-factorized-lora-package-v1"
CANDIDATE_ID = "fp32-attached-factorized-lora"

PASS_CLASSIFICATION = (
    "fp32_attached_fixed_compiler_favorable_eval_offline_artifact_package_eligible"
)
INCOMPLETE_CLASSIFICATION = (
    "fp32_attached_offline_artifact_eligibility_requirements_incomplete"
)
PASS_NEXT_GATE_ID = (
    "FC-MVP-001-fp32-attached-preferred-offline-candidate-decision-v1"
)
FAILURE_NEXT_GATE_ID = (
    "FC-MVP-001-fp32-attached-offline-artifact-eligibility-"
    "failure-classification-v1"
)

PREREGISTRATION_PATH = (
    "configs/tool_router_fp32_attached_offline_artifact_eligibility_"
    "reassessment_v1.json"
)
CONTRACT_SOURCE_PATH = (
    "src/fullcycle_bridge/"
    "tool_router_fp32_attached_offline_artifact_eligibility_reassessment.py"
)
BUILDER_SOURCE_PATH = (
    "scripts/reassess_tool_router_fp32_attached_offline_artifact_eligibility.py"
)
PROTOCOL_SOURCE_PATHS = {
    "builder_source": BUILDER_SOURCE_PATH,
    "contract_source": CONTRACT_SOURCE_PATH,
}

UPSTREAM_ARTIFACTS = {
    "artifact_eligibility_review": {
        "path": "baseline/fc-mvp-001-fp32-attached-artifact-eligibility-review-v1.json",
        "sha256": (
            "sha256:81977f318c6bcfed8d3844575dc245d4b94c2636a2359165f9aa5553c9b006f8"
        ),
    },
    "offline_package_manifest": {
        "path": "baseline/fc-mvp-001-fp32-attached-offline-package-manifest-v1.json",
        "sha256": (
            "sha256:4125f2eef2a4b8f07015169ac7fb77b830514e053a4624aa703e5f5a64943eb0"
        ),
    },
    "offline_package_reproducibility": {
        "path": (
            "baseline/fc-mvp-001-fp32-attached-offline-package-"
            "reproducibility-v1.json"
        ),
        "sha256": (
            "sha256:0e0d2174f4723ab42a5c11375cee10a819e32737810f63111d098decc2984044"
        ),
    },
    "remote_revision_origin_attestation": {
        "path": (
            "baseline/fc-mvp-001-fp32-attached-remote-revision-origin-"
            "attestation-v1.json"
        ),
        "sha256": (
            "sha256:cdde41aed18e2fecccea1833f16cea4fc808eb5d212376c96f3e2763fcef7cfd"
        ),
    },
}

REQUIREMENT_KEYS = (
    "behavioral_reproducibility_established",
    "clean_location_resolution_established",
    "compiled_quality_evidence_favorable",
    "metadata_complete",
    "offline_package_identity_complete",
    "prior_package_blockers_resolved",
    "remote_revision_origin_attested",
    "repository_local_evidence_usable",
)
REQUIREMENT_BLOCKERS = {
    "behavioral_reproducibility_established": (
        "behavioral_reproducibility_unverified"
    ),
    "clean_location_resolution_established": (
        "clean_location_resolution_unverified"
    ),
    "compiled_quality_evidence_favorable": (
        "compiled_quality_evidence_not_favorable"
    ),
    "metadata_complete": "metadata_incomplete",
    "offline_package_identity_complete": "offline_package_identity_incomplete",
    "prior_package_blockers_resolved": "prior_package_blockers_unresolved",
    "remote_revision_origin_attested": "remote_revision_origin_unverified",
    "repository_local_evidence_usable": "repository_local_evidence_unusable",
}

RESOLVED_PRIOR_PACKAGE_BLOCKERS = (
    "base_model_revision_binding_missing",
    "composite_manifest_missing",
    "package_use_and_limitations_documentation_incomplete",
    "portable_base_model_binding_missing",
    "required_compiler_binding_missing",
    "tokenizer_file_manifest_missing",
)

EXPECTED_UPSTREAM_VALIDATIONS: dict[str, dict[str, Any]] = {
    "artifact_eligibility_review": {
        "frozen_review_valid": True,
        "upstream_evaluation_favorable": True,
        "repository_local_evidence_usable": True,
        "offline_artifact_eligible": False,
        "portable_package_eligible": False,
        "classification": (
            "fp32_attached_fixed_compiler_favorable_eval_but_offline_artifact_"
            "package_incomplete"
        ),
        "blocking_finding_count": 6,
        "next_gate": "FC-MVP-001-fp32-attached-offline-package-manifest-v1",
        "runtime_eligible": False,
    },
    "offline_package_manifest": {
        "frozen_manifest_valid": True,
        "manifest_file_sha256": UPSTREAM_ARTIFACTS["offline_package_manifest"][
            "sha256"
        ],
        "metadata_complete": True,
        "offline_package_identity_complete": True,
        "attached_package_identity_bound": True,
        "prior_package_blocker_count_resolved": 6,
        "eligible_for_clean_location_reproducibility_test": True,
        "remote_revision_origin_attested": False,
        "behavioral_reproducibility_established": False,
        "offline_artifact_eligible": False,
        "portable_package_eligible": False,
        "preferred_offline_candidate": False,
        "serving_readiness_established": False,
        "artifact_promotion_allowed": False,
        "merged_artifact_allowed": False,
        "classification": "fp32_attached_metadata_only_composite_manifest_complete",
        "remaining_blocking_findings": [
            "behavioral_reproducibility_unverified",
            "clean_location_resolution_unverified",
            "remote_revision_origin_unverified",
        ],
        "remaining_blocking_finding_count": 3,
        "next_gate": (
            "FC-MVP-001-fp32-attached-offline-package-reproducibility-v1"
        ),
        "runtime_eligible": False,
    },
    "offline_package_reproducibility": {
        "frozen_gate_valid": True,
        "classification": (
            "fp32_attached_same_environment_clean_location_behavior_exactly_"
            "reproduced"
        ),
        "formal_gate_passed": True,
        "clean_location_resolution_established": True,
        "behavioral_reproducibility_established": True,
        "remaining_blocking_findings": ["remote_revision_origin_unverified"],
        "next_gate": (
            "FC-MVP-001-fp32-attached-remote-revision-origin-attestation-v1"
        ),
        "runtime_eligible": False,
    },
    "remote_revision_origin_attestation": {
        "frozen_gate_valid": True,
        "classification": (
            "fp32_attached_github_and_huggingface_hosted_revision_origins_attested"
        ),
        "formal_gate_passed": True,
        "remote_revision_origin_attested": True,
        "remaining_blocking_findings": [],
        "next_gate": GATE_ID,
        "offline_artifact_eligible": False,
        "portable_package_eligible": False,
        "preferred_offline_candidate": False,
        "runtime_eligible": False,
    },
}

ZERO_SHA256 = "sha256:" + "0" * 64
SHA256_PATTERN = re.compile(r"sha256:[0-9a-f]{64}")
GIT_COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}")
MAX_JSON_BYTES = 4 * 1024 * 1024


class EligibilityReassessmentError(ValueError):
    """Raised when the reassessment trust root or decision drifts."""


def artifact_json_bytes(value: Mapping[str, Any]) -> bytes:
    """Serialize one tracked artifact with stable pretty JSON."""

    return (
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    ).encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    """Return the project-prefixed SHA-256 identity for bytes."""

    return "sha256:" + hashlib.sha256(payload).hexdigest()


def parse_strict_json_bytes(
    payload: bytes,
    *,
    path: str,
    max_bytes: int = MAX_JSON_BYTES,
) -> Any:
    """Parse bounded UTF-8 JSON while rejecting duplicates and non-finite values."""

    if not isinstance(payload, bytes):
        _fail("INVALID_JSON_PAYLOAD", path, type(payload).__name__)
    if not payload or len(payload) > max_bytes:
        _fail("INVALID_JSON_PAYLOAD_SIZE", path, str(len(payload)))
    try:
        value = json.loads(
            payload,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_json_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise EligibilityReassessmentError(
            f"INVALID_JSON at {path}: {exc}"
        ) from exc
    _validate_finite_json(value, path)
    return value


def expected_preregistration(
    *,
    freeze_status: str,
    protocol_source_hashes: Mapping[str, str],
) -> dict[str, Any]:
    """Build the exact draft or frozen preregistration."""

    if freeze_status not in {"draft", "frozen"}:
        _fail("INVALID_FREEZE_STATUS", "$.freeze_status", freeze_status)
    if set(protocol_source_hashes) != set(PROTOCOL_SOURCE_PATHS):
        _fail(
            "INVALID_PROTOCOL_SOURCE_KEYS",
            "$.source_lineage.protocol_sources",
            repr(sorted(protocol_source_hashes)),
        )
    for name, value in protocol_source_hashes.items():
        _validate_sha256(value, f"$.source_lineage.protocol_sources.{name}.sha256")

    return {
        "preregistration_version": PREREGISTRATION_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "gate_id": GATE_ID,
        "package_id": PACKAGE_ID,
        "candidate_id": CANDIDATE_ID,
        "freeze_status": freeze_status,
        "decision_scope": {
            "decision": "offline_artifact_eligibility_only",
            "quality_basis": "fixed_compiler_favorable_frozen_full_eval",
            "behavior_basis": (
                "same_recorded_environment_exact_twenty_case_raw_and_compiled_"
                "output_reproduction"
            ),
            "origin_basis": (
                "github_and_huggingface_https_hosted_revision_authorities"
            ),
            "portable_package_decision": False,
            "preferred_candidate_decision": False,
            "serving_or_runtime_decision": False,
        },
        "source_lineage": {
            "upstream_artifacts": copy.deepcopy(UPSTREAM_ARTIFACTS),
            "protocol_sources": {
                name: {
                    "path": PROTOCOL_SOURCE_PATHS[name],
                    "sha256": protocol_source_hashes[name],
                }
                for name in sorted(PROTOCOL_SOURCE_PATHS)
            },
        },
        "eligibility_requirements": list(REQUIREMENT_KEYS),
        "resolved_prior_package_blockers": list(
            RESOLVED_PRIOR_PACKAGE_BLOCKERS
        ),
        "outcome_classifications": {
            "eligible": PASS_CLASSIFICATION,
            "incomplete": INCOMPLETE_CLASSIFICATION,
        },
        "outcome_next_actions": {
            "eligible": {
                "gate_id": PASS_NEXT_GATE_ID,
                "action": (
                    "decide preferred offline candidate status from frozen quality, "
                    "compiler dependency, resource, execution-form, and portability "
                    "evidence without promotion serving or Runtime integration"
                ),
            },
            "incomplete": {
                "gate_id": FAILURE_NEXT_GATE_ID,
                "action": (
                    "classify the unresolved fixed eligibility requirement before "
                    "changing any package byte or downstream decision"
                ),
            },
        },
        "constraints": _constraints(),
        "claims": _false_downstream_claims(),
        "runtime_eligible": False,
    }


def validate_preregistration(
    preregistration: Mapping[str, Any],
    *,
    require_frozen: bool = True,
) -> dict[str, Any]:
    """Validate exact preregistration shape without trusting its source hashes."""

    source_lineage = _mapping(
        preregistration.get("source_lineage"), "$.source_lineage"
    )
    protocol_sources = _mapping(
        source_lineage.get("protocol_sources"),
        "$.source_lineage.protocol_sources",
    )
    if set(protocol_sources) != set(PROTOCOL_SOURCE_PATHS):
        _fail(
            "INVALID_PROTOCOL_SOURCE_KEYS",
            "$.source_lineage.protocol_sources",
            repr(sorted(protocol_sources)),
        )
    hashes: dict[str, str] = {}
    for name, relative in PROTOCOL_SOURCE_PATHS.items():
        receipt = _mapping(
            protocol_sources.get(name),
            f"$.source_lineage.protocol_sources.{name}",
        )
        if receipt.get("path") != relative:
            _fail(
                "PROTOCOL_SOURCE_PATH_MISMATCH",
                f"$.source_lineage.protocol_sources.{name}.path",
                repr(receipt.get("path")),
            )
        value = receipt.get("sha256")
        if not isinstance(value, str):
            _fail(
                "INVALID_SHA256",
                f"$.source_lineage.protocol_sources.{name}.sha256",
                repr(value),
            )
        _validate_sha256(
            value, f"$.source_lineage.protocol_sources.{name}.sha256"
        )
        hashes[name] = value
    freeze_status = preregistration.get("freeze_status")
    if not isinstance(freeze_status, str):
        _fail("INVALID_FREEZE_STATUS", "$.freeze_status", repr(freeze_status))
    expected = expected_preregistration(
        freeze_status=freeze_status,
        protocol_source_hashes=hashes,
    )
    if dict(preregistration) != expected:
        _fail(
            "PREREGISTRATION_RECOMPUTATION_MISMATCH",
            "$.preregistration",
            "fields drifted",
        )
    if require_frozen and freeze_status != "frozen":
        _fail("PREREGISTRATION_NOT_FROZEN", "$.freeze_status", freeze_status)
    return expected


def classify_offline_artifact_eligibility(
    requirements: Mapping[str, bool],
) -> dict[str, Any]:
    """Apply one outcome-neutral categorical eligibility rubric."""

    if tuple(sorted(requirements)) != tuple(sorted(REQUIREMENT_KEYS)) or any(
        type(value) is not bool for value in requirements.values()
    ):
        _fail("INVALID_ELIGIBILITY_REQUIREMENTS", "$.requirements", repr(requirements))
    blockers = sorted(
        REQUIREMENT_BLOCKERS[name]
        for name, passed in requirements.items()
        if not passed
    )
    eligible = not blockers
    return {
        "requirements": dict(sorted(requirements.items())),
        "blocking_findings": blockers,
        "blocking_finding_count": len(blockers),
        "offline_artifact_eligible": eligible,
        "classification": (
            PASS_CLASSIFICATION if eligible else INCOMPLETE_CLASSIFICATION
        ),
    }


def build_reassessment_evidence(
    preregistration: Mapping[str, Any],
    *,
    preregistration_sha256: str,
    protocol_freeze_commit: str,
    upstream_payloads: Mapping[str, bytes],
    upstream_validations: Mapping[str, Mapping[str, Any]],
    protocol_source_payloads: Mapping[str, bytes],
) -> dict[str, Any]:
    """Recompute one offline-only eligibility decision from frozen validators."""

    prereg = validate_preregistration(preregistration)
    _validate_sha256(preregistration_sha256, "$.preregistration_sha256")
    if not GIT_COMMIT_PATTERN.fullmatch(protocol_freeze_commit):
        _fail(
            "INVALID_PROTOCOL_FREEZE_COMMIT",
            "$.protocol_freeze_commit",
            protocol_freeze_commit,
        )
    _validate_upstream_payloads(upstream_payloads)
    _validate_upstream_validations(upstream_validations)
    protocol_receipts = _validate_protocol_sources(
        prereg, protocol_source_payloads
    )
    _validate_upstream_identities(upstream_payloads)

    requirements = {
        "behavioral_reproducibility_established": True,
        "clean_location_resolution_established": True,
        "compiled_quality_evidence_favorable": True,
        "metadata_complete": True,
        "offline_package_identity_complete": True,
        "prior_package_blockers_resolved": True,
        "remote_revision_origin_attested": True,
        "repository_local_evidence_usable": True,
    }
    decision = classify_offline_artifact_eligibility(requirements)
    eligible = decision["offline_artifact_eligible"] is True
    next_action = prereg["outcome_next_actions"][
        "eligible" if eligible else "incomplete"
    ]
    gates = {
        **dict(decision["requirements"]),
        "protocol_integrity": True,
    }
    evidence: dict[str, Any] = {
        "evidence_version": EVIDENCE_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "gate_id": GATE_ID,
        "package_id": PACKAGE_ID,
        "candidate_id": CANDIDATE_ID,
        "preregistration": {
            "path": PREREGISTRATION_PATH,
            "sha256": preregistration_sha256,
            "freeze_status": prereg["freeze_status"],
        },
        "protocol_freeze_commit": protocol_freeze_commit,
        "protocol_sources": protocol_receipts,
        "upstream_evidence": {
            name: {
                **copy.deepcopy(UPSTREAM_ARTIFACTS[name]),
                "validation": copy.deepcopy(dict(upstream_validations[name])),
            }
            for name in sorted(UPSTREAM_ARTIFACTS)
        },
        "resolved_prior_package_blockers": list(
            RESOLVED_PRIOR_PACKAGE_BLOCKERS
        ),
        "eligibility_decision": decision,
        "gates": dict(sorted(gates.items())),
        "classification": decision["classification"],
        "formal_gate_passed": eligible,
        "derived_claims": {
            "compiled_quality_evidence_favorable": True,
            "repository_local_evidence_usable": True,
            "metadata_complete": True,
            "offline_package_identity_complete": True,
            "clean_location_resolution_established": True,
            "behavioral_reproducibility_established": True,
            "behavioral_reproducibility_scope": (
                "same_recorded_environment_exact_twenty_case_raw_and_compiled_"
                "output_reproduction"
            ),
            "remote_revision_origin_attested": True,
            "remote_revision_origin_scope": (
                "github_and_huggingface_https_hosted_revision_authorities"
            ),
            "offline_artifact_eligible": eligible,
            "offline_artifact_eligibility_scope": (
                "fixed_composite_package_with_same_recorded_environment_exact_"
                "replay_and_hosted_revision_origin"
            ),
            "portable_package_eligible": False,
            "cross_machine_reproducibility_established": False,
            "preferred_offline_candidate": False,
            "serving_readiness_established": False,
            "artifact_promotion_allowed": False,
            "merged_artifact_allowed": False,
            "runtime_eligible": False,
        },
        "remaining_blocking_findings": list(decision["blocking_findings"]),
        "remaining_blocking_finding_count": decision["blocking_finding_count"],
        "locked_next_action": {
            "gate_id": next_action["gate_id"],
            "action": next_action["action"],
            "eligible_to_start": eligible,
            "classification": decision["classification"],
            "formal_gate_passed": eligible,
            "offline_artifact_eligible": eligible,
            "portable_package_eligible": False,
            "preferred_offline_candidate": False,
            "artifact_promotion_allowed": False,
            "runtime_integration_allowed": False,
        },
        "constraints": _constraints(),
        "claims": {
            **_false_downstream_claims(),
            "offline_artifact_eligible": eligible,
            "metadata_only_reassessment": True,
            "upstream_validators_recomputed": True,
            "new_model_execution": False,
            "network_used": False,
        },
        "model_artifact_saved": False,
        "tensor_payload_saved": False,
        "offline": True,
        "runtime_eligible": False,
    }
    evidence["report_digest"] = sha256_bytes(canonical_json_bytes(evidence))
    return evidence


def validate_reassessment_evidence(
    preregistration_payload: bytes,
    evidence_payload: bytes,
    *,
    expected_preregistration_sha256: str,
    expected_evidence_sha256: str,
    expected_protocol_freeze_commit: str,
    upstream_payloads: Mapping[str, bytes],
    upstream_validations: Mapping[str, Mapping[str, Any]],
    protocol_source_payloads: Mapping[str, bytes],
) -> dict[str, Any]:
    """Authenticate raw roots and exactly recompute the tracked evidence."""

    _require_payload_sha256(
        preregistration_payload,
        expected_preregistration_sha256,
        "$.preregistration",
    )
    _require_payload_sha256(
        evidence_payload,
        expected_evidence_sha256,
        "$.evidence",
    )
    preregistration = _mapping(
        parse_strict_json_bytes(preregistration_payload, path="$.preregistration"),
        "$.preregistration",
    )
    evidence = _mapping(
        parse_strict_json_bytes(evidence_payload, path="$.evidence"),
        "$.evidence",
    )
    expected = build_reassessment_evidence(
        preregistration,
        preregistration_sha256=expected_preregistration_sha256,
        protocol_freeze_commit=expected_protocol_freeze_commit,
        upstream_payloads=upstream_payloads,
        upstream_validations=upstream_validations,
        protocol_source_payloads=protocol_source_payloads,
    )
    if evidence != expected:
        _fail(
            "EVIDENCE_RECOMPUTATION_MISMATCH",
            "$.evidence",
            "tracked evidence differs",
        )
    derived = _mapping(evidence.get("derived_claims"), "$.derived_claims")
    return {
        "frozen_gate_valid": True,
        "classification": evidence["classification"],
        "formal_gate_passed": evidence["formal_gate_passed"],
        "offline_artifact_eligible": derived["offline_artifact_eligible"],
        "portable_package_eligible": derived["portable_package_eligible"],
        "preferred_offline_candidate": derived["preferred_offline_candidate"],
        "prior_package_blocker_count_resolved": len(
            evidence["resolved_prior_package_blockers"]
        ),
        "remaining_blocking_findings": evidence[
            "remaining_blocking_findings"
        ],
        "next_gate": evidence["locked_next_action"]["gate_id"],
        "runtime_eligible": evidence["runtime_eligible"],
    }


def _validate_upstream_payloads(upstream_payloads: Mapping[str, bytes]) -> None:
    if set(upstream_payloads) != set(UPSTREAM_ARTIFACTS):
        _fail(
            "INVALID_UPSTREAM_PAYLOAD_KEYS",
            "$.upstream_payloads",
            repr(sorted(upstream_payloads)),
        )
    for name, receipt in UPSTREAM_ARTIFACTS.items():
        _require_payload_sha256(
            upstream_payloads[name], receipt["sha256"], f"$.upstream_payloads.{name}"
        )


def _validate_upstream_validations(
    upstream_validations: Mapping[str, Mapping[str, Any]],
) -> None:
    if set(upstream_validations) != set(EXPECTED_UPSTREAM_VALIDATIONS):
        _fail(
            "INVALID_UPSTREAM_VALIDATION_KEYS",
            "$.upstream_validations",
            repr(sorted(upstream_validations)),
        )
    for name, expected in EXPECTED_UPSTREAM_VALIDATIONS.items():
        actual = dict(upstream_validations[name])
        _validate_finite_json(actual, f"$.upstream_validations.{name}")
        if actual != expected:
            _fail(
                "UPSTREAM_VALIDATION_MISMATCH",
                f"$.upstream_validations.{name}",
                "canonical projection drifted",
            )


def _validate_protocol_sources(
    preregistration: Mapping[str, Any],
    protocol_source_payloads: Mapping[str, bytes],
) -> dict[str, dict[str, Any]]:
    if set(protocol_source_payloads) != set(PROTOCOL_SOURCE_PATHS):
        _fail(
            "INVALID_PROTOCOL_SOURCE_KEYS",
            "$.protocol_source_payloads",
            repr(sorted(protocol_source_payloads)),
        )
    prereg_sources = preregistration["source_lineage"]["protocol_sources"]
    receipts: dict[str, dict[str, Any]] = {}
    for name, relative in sorted(PROTOCOL_SOURCE_PATHS.items()):
        payload = protocol_source_payloads[name]
        observed = sha256_bytes(payload)
        expected = prereg_sources[name]["sha256"]
        if observed != expected:
            _fail(
                "PROTOCOL_SOURCE_HASH_MISMATCH",
                f"$.protocol_source_payloads.{name}",
                observed,
            )
        receipts[name] = {
            "path": relative,
            "bytes": len(payload),
            "sha256": observed,
        }
    return receipts


def _validate_upstream_identities(upstream_payloads: Mapping[str, bytes]) -> None:
    expected: dict[str, dict[str, Any]] = {
        "artifact_eligibility_review": {
            "gate_id": "FC-MVP-001-fp32-attached-artifact-eligibility-review-v1",
            "runtime_eligible": False,
        },
        "offline_package_manifest": {
            "gate_id": "FC-MVP-001-fp32-attached-offline-package-manifest-v1",
            "package_id": PACKAGE_ID,
        },
        "offline_package_reproducibility": {
            "gate_id": "FC-MVP-001-fp32-attached-offline-package-reproducibility-v1",
            "formal_gate_passed": True,
            "runtime_eligible": False,
        },
        "remote_revision_origin_attestation": {
            "gate_id": "FC-MVP-001-fp32-attached-remote-revision-origin-attestation-v1",
            "formal_gate_passed": True,
            "runtime_eligible": False,
        },
    }
    for name, fields in expected.items():
        value = _mapping(
            parse_strict_json_bytes(
                upstream_payloads[name], path=f"$.upstream_payloads.{name}"
            ),
            f"$.upstream_payloads.{name}",
        )
        for field, expected_value in fields.items():
            if value.get(field) != expected_value:
                _fail(
                    "UPSTREAM_IDENTITY_MISMATCH",
                    f"$.upstream_payloads.{name}.{field}",
                    repr(value.get(field)),
                )


def _constraints() -> dict[str, bool]:
    return {
        "adapter_or_weight_mutation": False,
        "artifact_promotion": False,
        "base_or_tokenizer_substitution": False,
        "decision_compiler_change": False,
        "desktop_integration": False,
        "eval_answer_tuning": False,
        "execution_form_change": False,
        "full_eval_run": False,
        "generation_change": False,
        "mcp_integration": False,
        "merged_weight_creation": False,
        "network_collection": False,
        "new_data": False,
        "precision_change": False,
        "prompt_change": False,
        "provider_integration": False,
        "runtime_integration": False,
        "serving_integration": False,
        "training": False,
    }


def _false_downstream_claims() -> dict[str, bool]:
    return {
        "artifact_promotion_allowed": False,
        "author_identity_or_signature_attested": False,
        "cross_machine_reproducibility_established": False,
        "historical_transparency_log_attested": False,
        "merged_artifact_allowed": False,
        "portable_package_eligible": False,
        "preferred_offline_candidate": False,
        "runtime_eligible": False,
        "serving_readiness_established": False,
        "supply_chain_signature_attested": False,
    }


def _require_payload_sha256(payload: bytes, expected: str, path: str) -> None:
    if not isinstance(payload, bytes):
        _fail("INVALID_PAYLOAD", path, type(payload).__name__)
    _validate_sha256(expected, f"{path}.expected_sha256")
    observed = sha256_bytes(payload)
    if observed != expected:
        _fail("PAYLOAD_SHA256_MISMATCH", path, observed)


def _validate_sha256(value: str, path: str) -> None:
    if not isinstance(value, str) or not SHA256_PATTERN.fullmatch(value):
        _fail("INVALID_SHA256", path, repr(value))


def _mapping(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        _fail("EXPECTED_OBJECT", path, type(value).__name__)
    return dict(value)


def _validate_finite_json(value: Any, path: str) -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            _fail("NONFINITE_NUMBER", path, repr(value))
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_finite_json(item, f"{path}[{index}]")
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                _fail("NON_STRING_KEY", path, repr(key))
            _validate_finite_json(item, f"{path}.{key}")
        return
    _fail("INVALID_JSON_TYPE", path, type(value).__name__)


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate key: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> NoReturn:
    raise ValueError(f"non-finite JSON number: {value}")


def _fail(code: str, path: str, detail: str) -> NoReturn:
    raise EligibilityReassessmentError(f"{code} at {path}: {detail}")


__all__ = [
    "BUILDER_SOURCE_PATH",
    "CONTRACT_SOURCE_PATH",
    "EVIDENCE_VERSION",
    "EligibilityReassessmentError",
    "EXPECTED_UPSTREAM_VALIDATIONS",
    "GATE_ID",
    "INCOMPLETE_CLASSIFICATION",
    "PASS_CLASSIFICATION",
    "PASS_NEXT_GATE_ID",
    "PREREGISTRATION_PATH",
    "PROTOCOL_SOURCE_PATHS",
    "REQUIREMENT_KEYS",
    "UPSTREAM_ARTIFACTS",
    "artifact_json_bytes",
    "build_reassessment_evidence",
    "classify_offline_artifact_eligibility",
    "expected_preregistration",
    "parse_strict_json_bytes",
    "sha256_bytes",
    "validate_preregistration",
    "validate_reassessment_evidence",
]
