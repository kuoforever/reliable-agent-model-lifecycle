"""Frozen preferred-offline-candidate decision for the FP32 attached package."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from collections.abc import Mapping
from typing import Any, NoReturn

from fullcycle_bridge.consumer import canonical_json_bytes


PREREGISTRATION_VERSION = 1
EVIDENCE_VERSION = 1
GATE_ID = "FC-MVP-001-fp32-attached-preferred-offline-candidate-decision-v1"
EXPERIMENT_ID = "fc-mvp-001-fp32-attached-preferred-offline-candidate-decision-v1"
PACKAGE_ID = "fc-mvp-001-fp32-attached-factorized-lora-package-v1"
CANDIDATE_ID = "fp32-attached-factorized-lora"
REFERENCE_ID = "bf16-attached-v2-compiled-reference"

PASS_CLASSIFICATION = (
    "fp32_attached_preferred_offline_candidate_under_fixed_compiler_"
    "attached_execution_and_registered_resource_caps"
)
INCOMPLETE_CLASSIFICATION = (
    "fp32_attached_preferred_offline_candidate_requirements_incomplete"
)
PASS_NEXT_GATE_ID = "FC-MVP-001-fp32-attached-portable-package-qualification-v1"
FAILURE_NEXT_GATE_ID = (
    "FC-MVP-001-fp32-attached-preferred-offline-candidate-failure-classification-v1"
)

PREREGISTRATION_PATH = (
    "configs/tool_router_fp32_attached_preferred_offline_candidate_decision_v1.json"
)
CONTRACT_SOURCE_PATH = (
    "src/fullcycle_bridge/"
    "tool_router_fp32_attached_preferred_offline_candidate_decision.py"
)
BUILDER_SOURCE_PATH = (
    "scripts/decide_tool_router_fp32_attached_preferred_offline_candidate.py"
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
    "offline_artifact_eligibility_reassessment": {
        "path": (
            "baseline/fc-mvp-001-fp32-attached-offline-artifact-eligibility-"
            "reassessment-v1.json"
        ),
        "sha256": (
            "sha256:0cccb2a7c7cdc24c824ee0ca4606f8c14e9b561473e50e8b31072291357b15ed"
        ),
    },
}
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
    "offline_artifact_eligibility_reassessment": {
        "frozen_gate_valid": True,
        "classification": (
            "fp32_attached_fixed_compiler_favorable_eval_offline_artifact_"
            "package_eligible"
        ),
        "formal_gate_passed": True,
        "offline_artifact_eligible": True,
        "portable_package_eligible": False,
        "preferred_offline_candidate": False,
        "prior_package_blocker_count_resolved": 6,
        "remaining_blocking_findings": [],
        "next_gate": GATE_ID,
        "runtime_eligible": False,
    },
}

REQUIREMENT_KEYS = (
    "attached_execution_form_bound",
    "comparison_reference_bound",
    "compiled_quality_strictly_improved",
    "compiled_safety_and_non_regression_passed",
    "compiler_dependency_bound",
    "decision_limitations_disclosed",
    "offline_artifact_eligible",
    "portability_boundary_acknowledged",
    "protocol_integrity",
    "registered_resource_gate_passed",
    "same_environment_reproducibility_established",
    "upstream_protocols_valid",
)
REQUIREMENT_BLOCKERS = {
    "attached_execution_form_bound": "attached_execution_form_unbound",
    "comparison_reference_bound": "bf16_comparison_reference_unbound",
    "compiled_quality_strictly_improved": "compiled_quality_strict_improvement_missing",
    "compiled_safety_and_non_regression_passed": (
        "compiled_safety_or_non_regression_failed"
    ),
    "compiler_dependency_bound": "required_compiler_dependency_unbound",
    "decision_limitations_disclosed": "decision_limitations_incomplete",
    "offline_artifact_eligible": "offline_artifact_ineligible",
    "portability_boundary_acknowledged": "portability_boundary_not_acknowledged",
    "protocol_integrity": "decision_protocol_integrity_failed",
    "registered_resource_gate_passed": "registered_resource_gate_failed",
    "same_environment_reproducibility_established": (
        "same_environment_reproducibility_unestablished"
    ),
    "upstream_protocols_valid": "upstream_protocol_validation_failed",
}

ZERO_SHA256 = "sha256:" + "0" * 64
SHA256_PATTERN = re.compile(r"sha256:[0-9a-f]{64}")
GIT_COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}")
MAX_JSON_BYTES = 4 * 1024 * 1024


class PreferredCandidateDecisionError(ValueError):
    """Raised when a preferred-candidate trust root or decision drifts."""


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
    """Parse bounded UTF-8 JSON and reject duplicates or non-finite values."""

    if not isinstance(payload, bytes) or not payload or len(payload) > max_bytes:
        _fail("INVALID_JSON_PAYLOAD", path, repr(type(payload).__name__))
    try:
        value = json.loads(
            payload,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_json_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise PreferredCandidateDecisionError(
            f"INVALID_JSON at {path}: {exc}"
        ) from exc
    _validate_finite_json(value, path)
    return value


def expected_preregistration(
    *,
    freeze_status: str,
    protocol_source_hashes: Mapping[str, str],
) -> dict[str, Any]:
    """Build the exact draft or frozen decision preregistration."""

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
        "comparison_reference_id": REFERENCE_ID,
        "freeze_status": freeze_status,
        "decision_scope": {
            "decision": "preferred_offline_candidate_only",
            "candidate_scope": (
                "exact_eligible_fp32_attached_composite_package_with_fixed_compiler"
            ),
            "reference_scope": (
                "frozen_bf16_attached_v2_compiled_quality_and_resource_reference"
            ),
            "reference_is_not_claimed_offline_artifact_eligible": True,
            "portable_package_decision": False,
            "artifact_promotion_decision": False,
            "serving_or_runtime_decision": False,
        },
        "selection_policy": {
            "rubric": "all_categorical_requirements_must_pass",
            "post_hoc_weighted_score": False,
            "quality": (
                "at_least_one_strict_compiled_improvement_with_zero_compiled_"
                "regression_and_all_frozen_safety_checks"
            ),
            "resources": (
                "reuse_only_the_pre_registered_fp32_remediation_resource_gate_"
                "without_new_thresholds"
            ),
            "compiler": "required_fixed_compiler_must_be_package_bound",
            "execution_form": "attached_factorized_lora_only",
            "portability": (
                "portable_status_may_remain_false_only_if_explicitly_disclosed_"
                "and_deferred_to_a_separate_gate"
            ),
            "limitations": [
                "raw_semantic_validity_regression_disclosed",
                "nearly_two_x_peak_memory_disclosed",
                "stable_speedup_unestablished",
                "single_registered_full_eval_run_and_no_repeat_variance",
                "cross_machine_reproducibility_unestablished",
                "portable_package_eligibility_unestablished",
            ],
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
        "preference_requirements": list(REQUIREMENT_KEYS),
        "outcome_classifications": {
            "preferred": PASS_CLASSIFICATION,
            "incomplete": INCOMPLETE_CLASSIFICATION,
        },
        "outcome_next_actions": {
            "preferred": {
                "gate_id": PASS_NEXT_GATE_ID,
                "action": (
                    "qualify portable-package status with explicit cross-machine "
                    "behavior and environment evidence while keeping promotion, "
                    "serving, and Runtime integration prohibited"
                ),
            },
            "incomplete": {
                "gate_id": FAILURE_NEXT_GATE_ID,
                "action": (
                    "classify the unresolved fixed preference requirement before "
                    "changing any candidate byte or downstream decision"
                ),
            },
        },
        "constraints": _constraints(),
        "claims": {
            **_false_downstream_claims(),
            "offline_artifact_eligible": True,
            "preferred_offline_candidate": False,
        },
        "runtime_eligible": False,
    }


def validate_preregistration(
    preregistration: Mapping[str, Any],
    *,
    require_frozen: bool = True,
) -> dict[str, Any]:
    """Validate exact preregistration shape without trusting reported hashes."""

    lineage = _mapping(preregistration.get("source_lineage"), "$.source_lineage")
    sources = _mapping(
        lineage.get("protocol_sources"), "$.source_lineage.protocol_sources"
    )
    if set(sources) != set(PROTOCOL_SOURCE_PATHS):
        _fail(
            "INVALID_PROTOCOL_SOURCE_KEYS",
            "$.source_lineage.protocol_sources",
            repr(sorted(sources)),
        )
    source_hashes: dict[str, str] = {}
    for name, relative in PROTOCOL_SOURCE_PATHS.items():
        receipt = _mapping(
            sources.get(name), f"$.source_lineage.protocol_sources.{name}"
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
        _validate_sha256(value, f"$.source_lineage.protocol_sources.{name}.sha256")
        source_hashes[name] = value
    status = preregistration.get("freeze_status")
    if not isinstance(status, str):
        _fail("INVALID_FREEZE_STATUS", "$.freeze_status", repr(status))
    expected = expected_preregistration(
        freeze_status=status,
        protocol_source_hashes=source_hashes,
    )
    if dict(preregistration) != expected:
        _fail(
            "PREREGISTRATION_RECOMPUTATION_MISMATCH",
            "$.preregistration",
            "fields drifted",
        )
    if require_frozen and status != "frozen":
        _fail("PREREGISTRATION_NOT_FROZEN", "$.freeze_status", status)
    return expected


def classify_preferred_candidate(requirements: Mapping[str, bool]) -> dict[str, Any]:
    """Apply the frozen all-categorical-requirements preference rubric."""

    if set(requirements) != set(REQUIREMENT_KEYS) or any(
        type(value) is not bool for value in requirements.values()
    ):
        _fail("INVALID_PREFERENCE_REQUIREMENTS", "$.requirements", repr(requirements))
    blockers = sorted(
        REQUIREMENT_BLOCKERS[name]
        for name, passed in requirements.items()
        if not passed
    )
    preferred = not blockers
    return {
        "requirements": dict(sorted(requirements.items())),
        "blocking_findings": blockers,
        "blocking_finding_count": len(blockers),
        "preferred_offline_candidate": preferred,
        "classification": (
            PASS_CLASSIFICATION if preferred else INCOMPLETE_CLASSIFICATION
        ),
    }


def build_decision_evidence(
    preregistration: Mapping[str, Any],
    *,
    preregistration_sha256: str,
    protocol_freeze_commit: str,
    upstream_payloads: Mapping[str, bytes],
    upstream_validations: Mapping[str, Mapping[str, Any]],
    protocol_source_payloads: Mapping[str, bytes],
) -> dict[str, Any]:
    """Recompute one preferred-candidate decision from frozen evidence."""

    prereg = validate_preregistration(preregistration)
    _validate_sha256(preregistration_sha256, "$.preregistration.sha256")
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

    review = _mapping(
        parse_strict_json_bytes(
            upstream_payloads["artifact_eligibility_review"],
            path="$.upstream.artifact_eligibility_review",
        ),
        "$.upstream.artifact_eligibility_review",
    )
    eligibility = _mapping(
        parse_strict_json_bytes(
            upstream_payloads["offline_artifact_eligibility_reassessment"],
            path="$.upstream.offline_artifact_eligibility_reassessment",
        ),
        "$.upstream.offline_artifact_eligibility_reassessment",
    )
    quality = _mapping(review.get("quality_review"), "$.review.quality_review")
    compiled = _mapping(quality.get("compiled_metrics"), "$.quality.compiled")
    reference = _mapping(
        quality.get("compiled_reference_metrics"), "$.quality.reference"
    )
    deltas = _mapping(quality.get("core_quality_deltas"), "$.quality.deltas")
    safety = _mapping(
        quality.get("compiled_safety_checks"), "$.quality.safety"
    )
    raw_semantic = _mapping(
        quality.get("raw_semantic_validity"), "$.quality.raw_semantic"
    )
    compiler = _mapping(
        review.get("compiler_dependency"), "$.review.compiler_dependency"
    )
    resources = _mapping(review.get("resource_review"), "$.review.resources")
    elapsed = _mapping(resources.get("elapsed_seconds"), "$.resources.elapsed")
    peak = _mapping(
        resources.get("peak_gpu_memory_bytes"), "$.resources.peak"
    )
    identity = _mapping(
        review.get("candidate_identity"), "$.review.candidate_identity"
    )
    adapter = _mapping(identity.get("adapter"), "$.identity.adapter")
    derived = _mapping(
        eligibility.get("derived_claims"), "$.eligibility.derived_claims"
    )
    resolved = eligibility.get("resolved_prior_package_blockers")
    if not isinstance(resolved, list) or any(
        not isinstance(value, str) for value in resolved
    ):
        _fail("INVALID_RESOLVED_BLOCKERS", "$.eligibility.resolved", repr(resolved))

    strict_improvements = quality.get("strict_per_example_improvements")
    compiled_improved = (
        quality.get("upstream_evaluation_gate_passed") is True
        and quality.get("comparison_basis") == "fixed_compiler_compiled_outputs"
        and isinstance(strict_improvements, list)
        and len(strict_improvements) >= 1
        and _number(deltas.get("argument_exact_match"), "$.deltas.argument_exact")
        > 0
        and _number(deltas.get("argument_field_f1"), "$.deltas.argument_f1") > 0
    )
    safety_and_non_regression = (
        quality.get("compiled_regression_event_count") == 0
        and len(safety) == 7
        and all(value is True for value in safety.values())
    )
    resource_gate = (
        resources.get("resource_gate_passed") is True
        and resources.get("new_post_hoc_resource_threshold_applied") is False
        and _number(peak.get("fp32_candidate"), "$.peak.fp32")
        <= _number(peak.get("registered_cap"), "$.peak.cap")
        and _number(elapsed.get("fp32_candidate"), "$.elapsed.fp32")
        <= _number(elapsed.get("registered_cap"), "$.elapsed.cap")
    )
    compiler_bound = (
        compiler.get("required") is True
        and compiler.get("bound_by_frozen_eval_evidence") is True
        and compiler.get("bare_adapter_must_not_inherit_compiled_metrics") is True
        and "required_compiler_binding_missing" in resolved
        and derived.get("offline_package_identity_complete") is True
    )
    execution_bound = (
        identity.get("candidate_id") == CANDIDATE_ID
        and adapter.get("execution_form") == "attached_factorized_lora"
        and adapter.get("merge") is False
        and derived.get("offline_package_identity_complete") is True
    )
    reference_bound = (
        quality.get("evaluation_records") == 20
        and reference.get("argument_exact_match") == 0.2
        and compiled.get("argument_exact_match") == 0.25
        and reference.get("argument_field_f1") == 0.2608695652173913
        and compiled.get("argument_field_f1") == 0.29787234042553196
        and peak.get("bf16_reference") == 3150315520
        and peak.get("fp32_candidate") == 6267895296
    )
    portability_acknowledged = (
        derived.get("portable_package_eligible") is False
        and derived.get("cross_machine_reproducibility_established") is False
    )
    limitations_disclosed = (
        _number(raw_semantic.get("delta"), "$.raw_semantic.delta") < 0
        and _number(peak.get("ratio"), "$.peak.ratio") > 1
        and resources.get("stable_speedup_established") is False
        and resources.get("serving_capacity_established") is False
        and quality.get("registered_full_eval_runs") == 1
        and quality.get("full_eval_repeatability_estimated") is False
        and portability_acknowledged
    )
    requirements = {
        "attached_execution_form_bound": execution_bound,
        "comparison_reference_bound": reference_bound,
        "compiled_quality_strictly_improved": compiled_improved,
        "compiled_safety_and_non_regression_passed": safety_and_non_regression,
        "compiler_dependency_bound": compiler_bound,
        "decision_limitations_disclosed": limitations_disclosed,
        "offline_artifact_eligible": derived.get("offline_artifact_eligible") is True,
        "portability_boundary_acknowledged": portability_acknowledged,
        "protocol_integrity": True,
        "registered_resource_gate_passed": resource_gate,
        "same_environment_reproducibility_established": (
            derived.get("behavioral_reproducibility_established") is True
            and derived.get("clean_location_resolution_established") is True
        ),
        "upstream_protocols_valid": True,
    }
    decision = classify_preferred_candidate(requirements)
    preferred = decision["preferred_offline_candidate"] is True
    next_gate = PASS_NEXT_GATE_ID if preferred else FAILURE_NEXT_GATE_ID

    evidence: dict[str, Any] = {
        "evidence_version": EVIDENCE_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "gate_id": GATE_ID,
        "package_id": PACKAGE_ID,
        "candidate_id": CANDIDATE_ID,
        "comparison_reference_id": REFERENCE_ID,
        "preregistration": {
            "path": PREREGISTRATION_PATH,
            "sha256": preregistration_sha256,
            "freeze_status": "frozen",
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
        "comparison": {
            "basis": "fixed_compiler_compiled_outputs",
            "evaluation_records": 20,
            "registered_full_eval_runs": 1,
            "compiled_metrics": copy.deepcopy(compiled),
            "compiled_reference_metrics": copy.deepcopy(reference),
            "core_quality_deltas": copy.deepcopy(deltas),
            "strict_per_example_improvements": copy.deepcopy(strict_improvements),
            "compiled_regression_event_count": 0,
            "compiled_safety_checks": copy.deepcopy(safety),
            "raw_semantic_validity": copy.deepcopy(raw_semantic),
            "compiler_dependency": {
                "required": True,
                "package_bound_after_manifest": compiler_bound,
                "bare_adapter_must_not_inherit_compiled_metrics": True,
                "changed_example_ids": copy.deepcopy(
                    compiler.get("changed_example_ids")
                ),
            },
            "resources": {
                "elapsed_seconds": copy.deepcopy(elapsed),
                "peak_gpu_memory_bytes": copy.deepcopy(peak),
                "registered_resource_gate_passed": resource_gate,
                "stable_speedup_established": False,
                "serving_capacity_established": False,
                "new_post_hoc_resource_threshold_applied": False,
            },
            "execution_form": "attached_factorized_lora",
            "portable_package_eligible": False,
            "cross_machine_reproducibility_established": False,
        },
        "preference_decision": decision,
        "gates": dict(sorted(requirements.items())),
        "classification": decision["classification"],
        "formal_gate_passed": preferred,
        "derived_claims": {
            "offline_artifact_eligible": True,
            "preferred_offline_candidate": preferred,
            "preferred_offline_candidate_scope": (
                "preferred_next_offline_candidate_for_portable_package_"
                "qualification_under_fixed_compiler_attached_execution_and_"
                "registered_resource_caps"
            ),
            "portable_package_eligible": False,
            "cross_machine_reproducibility_established": False,
            "serving_readiness_established": False,
            "artifact_promotion_allowed": False,
            "merged_artifact_allowed": False,
            "runtime_eligible": False,
        },
        "remaining_blocking_findings": copy.deepcopy(
            decision["blocking_findings"]
        ),
        "remaining_blocking_finding_count": decision["blocking_finding_count"],
        "downstream_open_findings": [
            "cross_machine_reproducibility_unestablished",
            "portable_package_eligibility_unestablished",
        ],
        "locked_next_action": {
            "gate_id": next_gate,
            "action": prereg["outcome_next_actions"][
                "preferred" if preferred else "incomplete"
            ]["action"],
            "eligible_to_start": preferred,
            "classification": decision["classification"],
            "formal_gate_passed": preferred,
            "offline_artifact_eligible": True,
            "preferred_offline_candidate": preferred,
            "portable_package_eligible": False,
            "artifact_promotion_allowed": False,
            "runtime_integration_allowed": False,
        },
        "constraints": _constraints(),
        "claims": {
            **_false_downstream_claims(),
            "offline_artifact_eligible": True,
            "preferred_offline_candidate": preferred,
            "metadata_only_decision": True,
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


def validate_decision_evidence(
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
    """Authenticate and exactly recompute one formal decision artifact."""

    _require_payload_sha256(
        preregistration_payload,
        expected_preregistration_sha256,
        "$.preregistration",
    )
    _require_payload_sha256(evidence_payload, expected_evidence_sha256, "$.evidence")
    preregistration = _mapping(
        parse_strict_json_bytes(
            preregistration_payload, path="$.preregistration"
        ),
        "$.preregistration",
    )
    actual = _mapping(
        parse_strict_json_bytes(evidence_payload, path="$.evidence"),
        "$.evidence",
    )
    expected = build_decision_evidence(
        preregistration,
        preregistration_sha256=expected_preregistration_sha256,
        protocol_freeze_commit=expected_protocol_freeze_commit,
        upstream_payloads=upstream_payloads,
        upstream_validations=upstream_validations,
        protocol_source_payloads=protocol_source_payloads,
    )
    if actual != expected:
        _fail("EVIDENCE_RECOMPUTATION_MISMATCH", "$.evidence", "fields drifted")
    return {
        "frozen_gate_valid": True,
        "classification": expected["classification"],
        "formal_gate_passed": expected["formal_gate_passed"],
        "offline_artifact_eligible": expected["derived_claims"][
            "offline_artifact_eligible"
        ],
        "preferred_offline_candidate": expected["derived_claims"][
            "preferred_offline_candidate"
        ],
        "portable_package_eligible": expected["derived_claims"][
            "portable_package_eligible"
        ],
        "remaining_blocking_findings": expected["remaining_blocking_findings"],
        "downstream_open_findings": expected["downstream_open_findings"],
        "next_gate": expected["locked_next_action"]["gate_id"],
        "runtime_eligible": expected["runtime_eligible"],
    }


def _validate_upstream_payloads(upstream_payloads: Mapping[str, bytes]) -> None:
    if set(upstream_payloads) != set(UPSTREAM_ARTIFACTS):
        _fail("INVALID_UPSTREAM_KEYS", "$.upstream", repr(sorted(upstream_payloads)))
    for name, receipt in UPSTREAM_ARTIFACTS.items():
        _require_payload_sha256(
            upstream_payloads[name], receipt["sha256"], f"$.upstream.{name}"
        )


def _validate_upstream_validations(
    upstream_validations: Mapping[str, Mapping[str, Any]],
) -> None:
    _validate_finite_json(upstream_validations, "$.upstream_validations")
    normalized = {
        name: copy.deepcopy(dict(value))
        for name, value in upstream_validations.items()
    }
    if normalized != EXPECTED_UPSTREAM_VALIDATIONS:
        _fail(
            "UPSTREAM_VALIDATION_MISMATCH",
            "$.upstream_validations",
            "canonical projection drifted",
        )


def _validate_protocol_sources(
    preregistration: Mapping[str, Any],
    payloads: Mapping[str, bytes],
) -> dict[str, dict[str, Any]]:
    if set(payloads) != set(PROTOCOL_SOURCE_PATHS):
        _fail(
            "INVALID_PROTOCOL_SOURCE_KEYS",
            "$.protocol_sources",
            repr(sorted(payloads)),
        )
    lineage = _mapping(preregistration.get("source_lineage"), "$.source_lineage")
    expected = _mapping(
        lineage.get("protocol_sources"), "$.source_lineage.protocol_sources"
    )
    receipts: dict[str, dict[str, Any]] = {}
    for name, path in PROTOCOL_SOURCE_PATHS.items():
        payload = payloads[name]
        receipt = _mapping(expected.get(name), f"$.protocol_sources.{name}")
        actual_sha = sha256_bytes(payload)
        if receipt.get("path") != path or receipt.get("sha256") != actual_sha:
            _fail(
                "PROTOCOL_SOURCE_HASH_MISMATCH",
                f"$.protocol_sources.{name}",
                actual_sha,
            )
        receipts[name] = {
            "path": path,
            "bytes": len(payload),
            "sha256": actual_sha,
        }
    return dict(sorted(receipts.items()))


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
        "cross_machine_reproducibility_established": False,
        "merged_artifact_allowed": False,
        "portable_package_eligible": False,
        "runtime_eligible": False,
        "serving_readiness_established": False,
    }


def _require_payload_sha256(payload: bytes, expected: str, path: str) -> None:
    _validate_sha256(expected, f"{path}.sha256")
    actual = sha256_bytes(payload)
    if actual != expected:
        _fail("PAYLOAD_SHA256_MISMATCH", path, actual)


def _validate_sha256(value: str, path: str) -> None:
    if not SHA256_PATTERN.fullmatch(value) or value == ZERO_SHA256:
        _fail("INVALID_SHA256", path, value)


def _mapping(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail("INVALID_OBJECT", path, type(value).__name__)
    return value


def _number(value: Any, path: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _fail("INVALID_NUMBER", path, repr(value))
    result = float(value)
    if not math.isfinite(result):
        _fail("NONFINITE_NUMBER", path, repr(value))
    return result


def _validate_finite_json(value: Any, path: str) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        _fail("NONFINITE_NUMBER", path, repr(value))
    if isinstance(value, dict):
        for key, nested in value.items():
            if not isinstance(key, str):
                _fail("INVALID_JSON_KEY", path, repr(key))
            _validate_finite_json(nested, f"{path}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _validate_finite_json(nested, f"{path}[{index}]")


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate key: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> NoReturn:
    raise ValueError(f"non-finite JSON constant: {value}")


def _fail(code: str, path: str, detail: str) -> NoReturn:
    raise PreferredCandidateDecisionError(f"{code} at {path}: {detail}")
