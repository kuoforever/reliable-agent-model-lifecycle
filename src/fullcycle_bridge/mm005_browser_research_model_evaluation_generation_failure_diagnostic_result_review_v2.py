"""Model-free review of the authenticated MM-005 diagnostic-v2 terminal.

The ignored runtime tree remains the immutable source of the owner, journal,
and failure bytes.  This module freezes only safe receipts and conclusions; it
never copies exception messages, tracebacks, absolute paths, environment
values, model output, or secrets into the tracked review.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, NoReturn, cast

from . import (
    mm005_browser_research_model_evaluation_generation_failure_diagnostic_protocol_v2 as protocol,
)
from . import (
    mm005_browser_research_model_evaluation_generation_failure_diagnostic_result_v2 as result_contract,
)

REVIEW_VERSION = 2
GATE_ID = result_contract.RESULT_REVIEW_GATE_ID
FAILED_GATE_ID = result_contract.EXECUTION_GATE_ID
AUTHORITY_INTRODUCTION_COMMIT = "6bfaf262eb2dd7cce6ffee928622a8785fa6eb1a"
AUTHORITY_PARENT_COMMIT = "ac052a3781246deb7365914dacfa271d37cfef59"

AUTHORITY_BYTES = 2_944
AUTHORITY_SHA256 = (
    "sha256:b638a7a73b401d6d968f9edc1b351e13394602b7d68dae7789f4485d996f39f0"
)
PREREGISTRATION_BYTES = 62_653
PREREGISTRATION_SHA256 = result_contract.PROTOCOL_SHA256
ATTEMPT_OWNER_BYTES = 4_550
ATTEMPT_OWNER_SHA256 = (
    "sha256:9be5d3b8d7041897c0f37fc8ed91145f5bb5d005644049e0c885dc05d747d9d9"
)
PROGRESS_BYTES = 4_173
PROGRESS_SHA256 = (
    "sha256:779edbd9c1275343859d0f349ad66cb356e7fb87dfd63fb9d919a7977ebda2ba"
)
FAILURE_BYTES = 8_975
FAILURE_SHA256 = (
    "sha256:4caaf601124cee082bb5bfbe61d73493e820ec4c84e70a3e1be2811e47fa3d54"
)
LIFECYCLE_LEASE_BYTES = 371
LIFECYCLE_LEASE_SHA256 = (
    "sha256:b377c5f63324ebcea5ecaecb838d6dad6e5c860d2933c065ff651ea2719f8099"
)

REVIEW_PATH = (
    "baseline/mm005-browser-research-model-eval-v2-generation-failure-"
    "diagnostic-v2-result-review.json"
)
REVIEW_SLICE_PATHS = frozenset(
    {
        "AI_Infra_LLM_Agent_待做任务清单.md",
        "PROJECT_STATUS.md",
        "README.md",
        REVIEW_PATH,
        (
            "docs/MM-005-browser-research-model-evaluation-generation-failure-"
            "diagnostic-result-review-v2.md"
        ),
        "docs/README.md",
        (
            "scripts/prepare_mm005_browser_research_model_evaluation_generation_"
            "failure_diagnostic_result_review_v2.py"
        ),
        "scripts/validate_offline.py",
        "scripts/validate_repository_ci.py",
        (
            "src/fullcycle_bridge/mm005_browser_research_model_evaluation_"
            "generation_failure_diagnostic_result_review_v2.py"
        ),
        (
            "tests/test_mm005_browser_research_model_evaluation_generation_"
            "failure_diagnostic_result_review_v2.py"
        ),
        "tests/test_validate_repository_ci.py",
    }
)

CLASSIFICATION = (
    "authenticated_pre_record_lifecycle_failure_without_diagnostic_execution_"
    "or_authenticated_root_cause"
)
EXPECTED_CAPTURED_AT_UTC = "2026-09-03T09:26:57.049004+00:00"
EXPECTED_FAILURE_SCOPE = "pre_record_lifecycle"
EXPECTED_EXCEPTION_TYPE = "RuntimeError"
EXPECTED_OUTCOME = "diagnostic_inconclusive"
EXPECTED_EVENTS = ("attempt_claimed", "failure_terminal_ready")

REQUIRED_TOP_LEVEL_KEYS = (
    "mm005_browser_research_generation_failure_diagnostic_result_review_version",
    "gate_id",
    "failed_gate_id",
    "experiment_id",
    "run_id",
    "classification",
    "lineage",
    "authenticated_artifacts",
    "authenticated_terminal",
    "invocation",
    "evidence_policy",
    "decision",
    "claims",
    "limitations",
    "locked_next_action",
    "publication",
    "report_digest",
)


class MM005GenerationFailureDiagnosticResultReviewError(ValueError):
    """Stable fail-closed error for diagnostic result-review drift."""

    def __init__(self, code: str, location: str = "$") -> None:
        self.code = code
        self.location = location
        super().__init__(f"{code} at {location}")


def artifact_json_bytes(value: object) -> bytes:
    return cast(bytes, result_contract.artifact_json_bytes(value))


def sha256_bytes(payload: bytes) -> str:
    return cast(str, result_contract.sha256_bytes(payload))


def build_result_review(*, authority_payload: bytes) -> dict[str, Any]:
    """Build the safe canonical review from the frozen authority receipt."""

    authority = _validate_authority_payload(authority_payload)
    body: dict[str, Any] = {
        "mm005_browser_research_generation_failure_diagnostic_result_review_version": (
            REVIEW_VERSION
        ),
        "gate_id": GATE_ID,
        "failed_gate_id": FAILED_GATE_ID,
        "experiment_id": protocol.EXPERIMENT_ID,
        "run_id": protocol.RUN_ID,
        "classification": CLASSIFICATION,
        "lineage": {
            "protocol": {
                "merge_commit": result_contract.PROTOCOL_MERGE_COMMIT,
                "artifact": _receipt(
                    protocol.PREREGISTRATION_PATH,
                    PREREGISTRATION_BYTES,
                    PREREGISTRATION_SHA256,
                ),
            },
            "implementation": {
                "zero_bandwidth_maintenance_commit": (
                    result_contract.ZERO_BANDWIDTH_MAINTENANCE_COMMIT
                ),
                "base_commit": result_contract.IMPLEMENTATION_BASE_COMMIT,
                "initial_publication_commit": (
                    result_contract.INITIAL_IMPLEMENTATION_PUBLICATION_COMMIT
                ),
                "freeze_commit": AUTHORITY_PARENT_COMMIT,
            },
            "execution_authority": {
                "introduction_commit": AUTHORITY_INTRODUCTION_COMMIT,
                "parent_commit": AUTHORITY_PARENT_COMMIT,
                "unique_first_parent_introduction": True,
                "artifact": _receipt(
                    result_contract.EXECUTION_AUTHORITY_PATH,
                    AUTHORITY_BYTES,
                    AUTHORITY_SHA256,
                ),
                "formal_invocation_budget": authority["budgets"][
                    "formal_invocations"
                ],
                "retry_budget": authority["budgets"]["retries"],
            },
        },
        "authenticated_artifacts": {
            "attempt_owner": {
                **_receipt(
                    protocol.ATTEMPT_OWNER_PATH,
                    ATTEMPT_OWNER_BYTES,
                    ATTEMPT_OWNER_SHA256,
                ),
                "canonical_kind": "json",
                "copied_into_review": False,
            },
            "progress": {
                **_receipt(
                    protocol.PROGRESS_PATH, PROGRESS_BYTES, PROGRESS_SHA256
                ),
                "canonical_kind": "jsonl",
                "authenticated_event_count": len(EXPECTED_EVENTS),
                "copied_into_review": False,
            },
            "failure": {
                **_receipt(
                    protocol.FAILURE_PATH, FAILURE_BYTES, FAILURE_SHA256
                ),
                "canonical_kind": "json",
                "copied_into_review": False,
            },
            "lifecycle_lease": {
                **_receipt(
                    protocol.LIFECYCLE_LEASE_PATH,
                    LIFECYCLE_LEASE_BYTES,
                    LIFECYCLE_LEASE_SHA256,
                ),
                "canonical_kind": "json",
                "copied_into_review": False,
            },
            "source_tree": "ignored_immutable_local_runtime_tree",
            "tracked_raw_artifact_count": 0,
            "runtime_artifacts_modified_by_review": False,
        },
        "authenticated_terminal": {
            "durable_state": "authenticated_failure",
            "captured_at_utc": EXPECTED_CAPTURED_AT_UTC,
            "event_names": list(EXPECTED_EVENTS),
            "event_sequences": [0, 1],
            "terminal_event": "failure_terminal_ready",
            "failure_scope": EXPECTED_FAILURE_SCOPE,
            "exception_type": EXPECTED_EXCEPTION_TYPE,
            "selected_outcome": EXPECTED_OUTCOME,
            "session_lifecycle_events": ["attempt_claimed"],
            "completed_record_ids": [],
            "active_record_id": None,
            "active_record_diagnostic_index": None,
            "durable_substage_event_count": 0,
            "observed_environment": None,
            "resources": None,
            "message_traceback_path_or_secret_persisted": False,
        },
        "invocation": {
            "formal_invocation_budget": 1,
            "formal_invocations_consumed": 1,
            "formal_invocation_budget_remaining": 0,
            "execution_attempt_claimed": True,
            "diagnostic_attempt_consumed": True,
            "retry_budget": 0,
            "retries_observed": 0,
            "retry_authorized": False,
            "same_identity_reinvocation_authorized": False,
        },
        "evidence_policy": {
            "authenticated_owner_journal_and_failure_only": True,
            "safe_exception_type_only": True,
            "exception_message_copied": False,
            "traceback_copied": False,
            "absolute_runtime_path_copied": False,
            "attempt_identifier_copied": False,
            "environment_values_copied": False,
            "model_output_copied": False,
            "controller_observation_exists_outside_authenticated_artifacts": True,
            "controller_observation_content_copied": False,
            "controller_observation_used_for_root_cause": False,
            "controller_observation_used_for_remediation": False,
            "missing_measurements_reconstructed": False,
        },
        "decision": {
            "selected_outcome": EXPECTED_OUTCOME,
            "result_review_gate_passed": True,
            "diagnostic_formal_gate_passed": False,
            "diagnostic_execution_completed": False,
            "model_evaluation_completed": False,
            "runtime_failure_observed_between_durable_checkpoints": False,
            "failed_runtime_substage_isolated": False,
            "runtime_root_cause_established": False,
            "remediation_delta_established": False,
            "recovery_selected": False,
        },
        "claims": {
            "execution_authority_published": True,
            "formal_invocation_budget_spent": True,
            "diagnostic_attempt_consumed": True,
            "authenticated_failure_terminal_reviewed": True,
            "terminal_persistence_completed": True,
            "diagnostic_executed": False,
            "all_registered_diagnostic_calls_completed": False,
            "diagnostic_completed_without_observed_runtime_failure": False,
            "diagnostic_failure_observed_between_durable_checkpoints": False,
            "model_evaluated": False,
            "formal_measurement_complete": False,
            "historical_runtime_health_established": False,
            "failed_runtime_substage_isolated": False,
            "runtime_root_cause_established": False,
            "remediation_delta_established": False,
            "recovery_v3_justified": False,
            "quality_established": False,
            "safety_established": False,
            "evaluation_repeatability_established": False,
            "resource_repeatability_established": False,
            "cross_machine_reproducibility_established": False,
            "serving_eligible": False,
            "promotion_eligible": False,
            "runtime_eligible": False,
        },
        "limitations": {
            "authenticated_exception_message_available": False,
            "authenticated_traceback_available": False,
            "authenticated_observed_environment_available": False,
            "authenticated_resource_measurement_available": False,
            "diagnostic_record_execution_available": False,
            "causal_root_cause_established": False,
            "controller_observation_can_upgrade_authenticated_claims": False,
            "same_identity_retry_can_recover_missing_evidence": False,
        },
        "locked_next_action": {
            "action": "stop_after_authenticated_result_review",
            "next_gate_id": None,
            "diagnostic_v2_chain_closed": True,
            "v2_retry_authorized": False,
            "automatic_recovery_authorized": False,
            "recovery_v3_authorized": False,
            "new_diagnostic_identity_authorized": False,
            "runtime_change_authorized": False,
            "separate_roadmap_scope_selection_required": True,
        },
        "publication": {
            "slice_paths": sorted(REVIEW_SLICE_PATHS),
            "slice_path_count": len(REVIEW_SLICE_PATHS),
            "raw_runtime_artifact_added_to_git": False,
            "diagnostic_runner_modified": False,
            "execution_authority_modified": False,
            "model_or_cuda_execution_by_review": False,
            "git_lfs_payload_bytes_required": 0,
        },
    }
    return {**body, "report_digest": sha256_bytes(artifact_json_bytes(body))}


def validate_runtime_terminal(
    *,
    authority_payload: bytes,
    preregistration_payload: bytes,
    attempt_owner_payload: bytes,
    progress_payload: bytes,
    failure_payload: bytes,
    lifecycle_lease_payload: bytes,
    implementation_context: Mapping[str, Any],
) -> dict[str, Any]:
    """Authenticate the ignored runtime bytes without copying unsafe content."""

    _validate_authority_payload(authority_payload)
    _validate_bound_payload(
        preregistration_payload,
        expected_bytes=PREREGISTRATION_BYTES,
        expected_sha256=PREREGISTRATION_SHA256,
        location="$.runtime.preregistration",
    )
    _validate_bound_payload(
        attempt_owner_payload,
        expected_bytes=ATTEMPT_OWNER_BYTES,
        expected_sha256=ATTEMPT_OWNER_SHA256,
        location="$.runtime.attempt_owner",
    )
    _validate_bound_payload(
        progress_payload,
        expected_bytes=PROGRESS_BYTES,
        expected_sha256=PROGRESS_SHA256,
        location="$.runtime.progress",
    )
    _validate_bound_payload(
        failure_payload,
        expected_bytes=FAILURE_BYTES,
        expected_sha256=FAILURE_SHA256,
        location="$.runtime.failure",
    )
    _validate_bound_payload(
        lifecycle_lease_payload,
        expected_bytes=LIFECYCLE_LEASE_BYTES,
        expected_sha256=LIFECYCLE_LEASE_SHA256,
        location="$.runtime.lifecycle_lease",
    )

    owner = result_contract.parse_strict_json_bytes(
        attempt_owner_payload, location="$.runtime.attempt_owner"
    )
    checked_owner = result_contract.validate_attempt_owner(
        owner,
        implementation_freeze_commit=AUTHORITY_PARENT_COMMIT,
        preregistration_payload=preregistration_payload,
    )
    if artifact_json_bytes(checked_owner) != attempt_owner_payload:
        _fail("ATTEMPT_OWNER_NOT_CANONICAL", "$.runtime.attempt_owner")

    events = result_contract.validate_progress_journal(
        progress_payload,
        implementation_freeze_commit=AUTHORITY_PARENT_COMMIT,
        preregistration_payload=preregistration_payload,
        attempt_owner_payload=attempt_owner_payload,
    )
    failure = result_contract.parse_strict_json_bytes(
        failure_payload, location="$.runtime.failure"
    )
    checked_failure = result_contract.validate_diagnostic_failure(
        failure,
        implementation_freeze_commit=AUTHORITY_PARENT_COMMIT,
        preregistration_payload=preregistration_payload,
        attempt_owner_payload=attempt_owner_payload,
        progress_payload=progress_payload,
        implementation_context=implementation_context,
    )
    if artifact_json_bytes(checked_failure) != failure_payload:
        _fail("FAILURE_NOT_CANONICAL", "$.runtime.failure")

    event_names = tuple(str(event.get("event")) for event in events)
    event_sequences = [event.get("sequence") for event in events]
    terminal = _mapping(events[-1].get("terminal"), "$.runtime.progress.terminal")
    claims = _mapping(checked_failure.get("claims"), "$.runtime.failure.claims")
    decision = _mapping(
        checked_failure.get("decision"), "$.runtime.failure.decision"
    )
    if (
        event_names != EXPECTED_EVENTS
        or event_sequences != [0, 1]
        or terminal.get("captured_at_utc") != EXPECTED_CAPTURED_AT_UTC
        or terminal.get("failure_scope") != EXPECTED_FAILURE_SCOPE
        or terminal.get("exception_type") != EXPECTED_EXCEPTION_TYPE
        or terminal.get("selected_outcome") != EXPECTED_OUTCOME
        or terminal.get("message_traceback_path_or_secret_persisted") is not False
        or checked_failure.get("classification") != EXPECTED_OUTCOME
        or checked_failure.get("failure_scope") != EXPECTED_FAILURE_SCOPE
        or checked_failure.get("exception_type") != EXPECTED_EXCEPTION_TYPE
        or decision.get("selected_outcome") != EXPECTED_OUTCOME
        or claims.get("diagnostic_attempt_consumed") is not True
        or claims.get("diagnostic_executed") is not False
        or claims.get("model_evaluated") is not False
        or claims.get("formal_measurement_complete") is not False
        or claims.get("runtime_root_cause_established") is not False
        or claims.get("runtime_eligible") is not False
    ):
        _fail("AUTHENTICATED_TERMINAL_MISMATCH", "$.runtime")

    return {
        "valid": True,
        "event_count": len(events),
        "failure_scope": checked_failure["failure_scope"],
        "selected_outcome": checked_failure["classification"],
        "diagnostic_attempt_consumed": True,
        "diagnostic_executed": False,
        "model_evaluated": False,
        "formal_measurement_complete": False,
        "root_cause_established": False,
        "retry_authorized": False,
    }


def validate_result_review(
    value: Mapping[str, Any], *, authority_payload: bytes
) -> dict[str, Any]:
    """Require exact equality with the deterministic safe review."""

    if set(value) != set(REQUIRED_TOP_LEVEL_KEYS):
        _fail("RESULT_REVIEW_TOP_LEVEL_KEYS", "$")
    expected = build_result_review(authority_payload=authority_payload)
    if artifact_json_bytes(dict(value)) != artifact_json_bytes(expected):
        _fail("RESULT_REVIEW_MISMATCH", "$")
    return expected


def parse_and_validate_result_review(
    payload: bytes, *, authority_payload: bytes
) -> dict[str, Any]:
    try:
        value = result_contract.parse_strict_json_bytes(
            payload, location="$.diagnostic_result_review"
        )
    except result_contract.MM005GenerationFailureDiagnosticResultError as exc:
        raise MM005GenerationFailureDiagnosticResultReviewError(
            exc.code, exc.location
        ) from exc
    if artifact_json_bytes(value) != payload:
        _fail("RESULT_REVIEW_NOT_CANONICAL", "$")
    return validate_result_review(value, authority_payload=authority_payload)


def _validate_authority_payload(payload: bytes) -> dict[str, Any]:
    _validate_bound_payload(
        payload,
        expected_bytes=AUTHORITY_BYTES,
        expected_sha256=AUTHORITY_SHA256,
        location="$.lineage.execution_authority.artifact",
    )
    authority: dict[str, Any] = dict(
        result_contract.parse_strict_json_bytes(
            payload, location="$.execution_authority"
        )
    )
    if artifact_json_bytes(authority) != payload:
        _fail("EXECUTION_AUTHORITY_NOT_CANONICAL", "$.execution_authority")
    budgets = _mapping(authority.get("budgets"), "$.execution_authority.budgets")
    if (
        authority.get("gate_id") != result_contract.EXECUTION_AUTHORITY_GATE_ID
        or authority.get("next_gate") != FAILED_GATE_ID
        or authority.get("implementation_freeze_commit") != AUTHORITY_PARENT_COMMIT
        or authority.get("protocol_merge_commit")
        != result_contract.PROTOCOL_MERGE_COMMIT
        or budgets
        != {"formal_invocations": 1, "per_record_attempts": 1, "retries": 0}
    ):
        _fail("EXECUTION_AUTHORITY_LINEAGE_MISMATCH", "$.execution_authority")
    return authority


def _receipt(path: str, size: int, digest: str) -> dict[str, Any]:
    return {"path": path, "bytes": size, "sha256": digest}


def _validate_bound_payload(
    payload: bytes, *, expected_bytes: int, expected_sha256: str, location: str
) -> None:
    if (
        type(payload) is not bytes
        or len(payload) != expected_bytes
        or sha256_bytes(payload) != expected_sha256
    ):
        _fail("BOUND_PAYLOAD_MISMATCH", location)


def _mapping(value: object, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail("OBJECT_REQUIRED", location)
    return cast(Mapping[str, Any], value)


def _fail(code: str, location: str) -> NoReturn:
    raise MM005GenerationFailureDiagnosticResultReviewError(code, location)


__all__ = [
    "ATTEMPT_OWNER_BYTES",
    "ATTEMPT_OWNER_SHA256",
    "AUTHORITY_BYTES",
    "AUTHORITY_INTRODUCTION_COMMIT",
    "AUTHORITY_PARENT_COMMIT",
    "AUTHORITY_SHA256",
    "CLASSIFICATION",
    "EXPECTED_OUTCOME",
    "FAILURE_BYTES",
    "FAILURE_SHA256",
    "GATE_ID",
    "LIFECYCLE_LEASE_BYTES",
    "LIFECYCLE_LEASE_SHA256",
    "MM005GenerationFailureDiagnosticResultReviewError",
    "PROGRESS_BYTES",
    "PROGRESS_SHA256",
    "REVIEW_PATH",
    "REVIEW_SLICE_PATHS",
    "REVIEW_VERSION",
    "artifact_json_bytes",
    "build_result_review",
    "parse_and_validate_result_review",
    "sha256_bytes",
    "validate_result_review",
    "validate_runtime_terminal",
]
