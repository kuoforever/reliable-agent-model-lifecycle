"""Model-free closeout for the exhausted MM-005 diagnostic invocation.

This module records only the authority lineage, the controller-observed
pre-claim boundary, and the absence of durable diagnostic state.  It never
constructs an attempt owner, progress frame, success result, or failure
terminal, and it never imports model or CUDA dependencies.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, NoReturn, cast

from . import (
    mm005_browser_research_model_evaluation_generation_failure_diagnostic as protocol,
)
from . import (
    mm005_browser_research_model_evaluation_generation_failure_diagnostic_result as result_contract,
)

CLOSEOUT_VERSION = 1
GATE_ID = (
    "MM-005-browser-research-model-evaluation-generation-failure-"
    "diagnostic-invocation-closeout-v1"
)
FAILED_GATE_ID = result_contract.EXECUTION_GATE_ID
NEXT_GATE_ID = "repository-ci-lfs-maintenance-v1"
NEW_IDENTITY_PROTOCOL_GATE_ID = (
    "MM-005-browser-research-model-evaluation-generation-failure-diagnostic-protocol-v2"
)
NEW_IDENTITY_IMPLEMENTATION_GATE_ID = (
    "MM-005-browser-research-model-evaluation-generation-failure-"
    "diagnostic-implementation-v2"
)
NEW_IDENTITY_AUTHORITY_GATE_ID = (
    "MM-005-browser-research-model-evaluation-generation-failure-"
    "diagnostic-execution-authority-v2"
)
NEW_IDENTITY_EXECUTION_GATE_ID = (
    "MM-005-browser-research-model-evaluation-generation-failure-"
    "diagnostic-execution-v2"
)

CLOSEOUT_PATH = (
    "baseline/mm005-browser-research-model-eval-v2-generation-failure-"
    "diagnostic-v1-invocation-closeout.json"
)
CLOSEOUT_SLICE_PATHS = frozenset(
    {
        "AI_Infra_LLM_Agent_待做任务清单.md",
        "PROJECT_STATUS.md",
        "README.md",
        CLOSEOUT_PATH,
        (
            "docs/MM-005-browser-research-model-evaluation-generation-failure-"
            "diagnostic-invocation-closeout-v1.md"
        ),
        "docs/README.md",
        (
            "scripts/closeout_mm005_browser_research_model_evaluation_generation_"
            "failure_diagnostic_invocation_v1.py"
        ),
        "scripts/validate_offline.py",
        (
            "src/fullcycle_bridge/mm005_browser_research_model_evaluation_"
            "generation_failure_diagnostic_invocation_closeout.py"
        ),
        (
            "tests/test_mm005_browser_research_model_evaluation_generation_failure_"
            "diagnostic_invocation_closeout.py"
        ),
    }
)
AUTHORITY_INTRODUCTION_COMMIT = "0a271e2c27c65e9595953dadb98200ea5ec51acb"
AUTHORITY_PARENT_COMMIT = "7da39396c951a9248fe49c1bd69080923b827fa1"
AUTHORITY_BYTES = 2_706
AUTHORITY_SHA256 = (
    "sha256:903e681c2957e185da36ed1f991cc5b339b0e692e8c730da63069690277b9e6b"
)
RUNNER_PATH = result_contract.IMPLEMENTATION_SOURCE_PATHS["diagnostic_runner"]
RUNNER_BYTES = 75_956
RUNNER_SHA256 = (
    "sha256:4f45b2db0a138f4920cb4a278c3c6bcc323633d59e650df5bf596bfaa8b704b1"
)
RECOVERY_IO_PATH = result_contract.CRITICAL_EXECUTION_DEPENDENCY_SOURCE_PATHS[
    "recovery_io"
]
RECOVERY_IO_BYTES = 13_995
RECOVERY_IO_SHA256 = (
    "sha256:7ffd029ebf4e4995b1f45aed735a7d5303df273f450d8ad13f106eb044d73e64"
)

FORMAL_COMMAND = (
    "work/training-env/Scripts/python.exe",
    "-I",
    "-B",
    "-X",
    "pycache_prefix=NUL",
    "scripts/run_mm005_browser_research_model_evaluation_generation_failure_"
    "diagnostic_v1.py",
    "--execute",
)

CLASSIFICATION = (
    "formal_invocation_exhausted_before_attempt_claim_on_missing_output_parent_guard"
)

REQUIRED_TOP_LEVEL_KEYS = (
    "mm005_browser_research_generation_failure_diagnostic_invocation_closeout_version",
    "gate_id",
    "failed_gate_id",
    "experiment_id",
    "run_id",
    "classification",
    "lineage",
    "invocation",
    "failure_boundary",
    "durable_runtime_state",
    "frozen_failure_grammar",
    "formal_outcome",
    "claims",
    "limitations",
    "locked_next_action",
    "publication",
    "report_digest",
)


class MM005GenerationFailureDiagnosticInvocationCloseoutError(ValueError):
    """Stable fail-closed error for closeout drift."""

    def __init__(self, code: str, location: str = "$") -> None:
        self.code = code
        self.location = location
        super().__init__(f"{code} at {location}")


def artifact_json_bytes(value: object) -> bytes:
    return cast(bytes, protocol.artifact_json_bytes(value))


def sha256_bytes(payload: bytes) -> str:
    return cast(str, protocol.sha256_bytes(payload))


def build_invocation_closeout(
    *,
    authority_payload: bytes,
    runner_payload: bytes,
    recovery_io_payload: bytes,
) -> dict[str, Any]:
    """Build the canonical non-terminal closeout from frozen byte inputs."""

    _validate_bound_payload(
        authority_payload,
        expected_bytes=AUTHORITY_BYTES,
        expected_sha256=AUTHORITY_SHA256,
        location="$.lineage.execution_authority.artifact",
    )
    authority = result_contract.parse_strict_json_bytes(
        authority_payload, location="$.execution_authority"
    )
    if artifact_json_bytes(authority) != authority_payload:
        _fail("EXECUTION_AUTHORITY_NOT_CANONICAL", "$.lineage.execution_authority")
    if (
        authority.get("gate_id") != result_contract.EXECUTION_AUTHORITY_GATE_ID
        or authority.get("next_gate") != FAILED_GATE_ID
        or authority.get("implementation_freeze_commit") != AUTHORITY_PARENT_COMMIT
        or authority.get("protocol_merge_commit")
        != result_contract.PROTOCOL_MERGE_COMMIT
        or authority.get("budgets")
        != {"formal_invocations": 1, "per_record_attempts": 1, "retries": 0}
    ):
        _fail("EXECUTION_AUTHORITY_LINEAGE_MISMATCH", "$.lineage.execution_authority")

    _validate_bound_payload(
        runner_payload,
        expected_bytes=RUNNER_BYTES,
        expected_sha256=RUNNER_SHA256,
        location="$.lineage.diagnostic_runner",
    )
    _validate_bound_payload(
        recovery_io_payload,
        expected_bytes=RECOVERY_IO_BYTES,
        expected_sha256=RECOVERY_IO_SHA256,
        location="$.lineage.recovery_io",
    )

    body: dict[str, Any] = {
        "mm005_browser_research_generation_failure_diagnostic_invocation_closeout_version": CLOSEOUT_VERSION,
        "gate_id": GATE_ID,
        "failed_gate_id": FAILED_GATE_ID,
        "experiment_id": protocol.EXPERIMENT_ID,
        "run_id": protocol.RUN_ID,
        "classification": CLASSIFICATION,
        "lineage": {
            "protocol_merge_commit": result_contract.PROTOCOL_MERGE_COMMIT,
            "implementation_freeze_commit": AUTHORITY_PARENT_COMMIT,
            "execution_authority": {
                "introduction_commit": AUTHORITY_INTRODUCTION_COMMIT,
                "parent_commit": AUTHORITY_PARENT_COMMIT,
                "unique_first_parent_introduction": True,
                "artifact": _receipt(
                    result_contract.EXECUTION_AUTHORITY_PATH, authority_payload
                ),
            },
            "diagnostic_runner": _receipt(RUNNER_PATH, runner_payload),
            "recovery_io": _receipt(RECOVERY_IO_PATH, recovery_io_payload),
        },
        "invocation": {
            "command_argv": list(FORMAL_COMMAND),
            "working_directory": "repository_root",
            "authority_head_at_invocation": AUTHORITY_INTRODUCTION_COMMIT,
            "clean_aligned_master_preflight_passed": True,
            "exact_environment_preflight_passed": True,
            "formal_invocation_budget": 1,
            "formal_invocations_observed": 1,
            "formal_invocation_budget_remaining": 0,
            "process_exit_code": 1,
            "retry_budget": 0,
            "retries_observed": 0,
            "retry_authorized": False,
            "same_identity_reinvocation_authorized": False,
        },
        "failure_boundary": {
            "controller_observed_exception_type": "RecoveryIOError",
            "runner_function": "_execute_authorized_diagnostic",
            "boundary": "output_parent_guard_construction_before_lifecycle_or_claim",
            "defect": "missing_safe_output_parent_creation_before_directory_tree_guard",
            "output_parent": str(protocol.RUN_OUTPUT_ROOT.rsplit("/", 1)[0]),
            "output_parent_was_missing": True,
            "directory_guard_requires_existing_target": True,
            "lifecycle_publication_entered": False,
            "owner_and_genesis_claim_entered": False,
            "terminal_handler_entered": False,
            "model_body_entered": False,
            "raw_exception_message_persisted": False,
            "traceback_persisted": False,
        },
        "durable_runtime_state": {
            "evidence_source": "controller_observation_after_process_exit",
            "output_parent_present": False,
            "output_root_present": False,
            "lifecycle_lease_root_present": False,
            "lifecycle_lease_present": False,
            "attempt_owner_present": False,
            "progress_present": False,
            "success_result_present": False,
            "failure_present": False,
            "reserved_sibling_staging_present": False,
        },
        "frozen_failure_grammar": {
            "owner_bound": True,
            "minimum_journal_event": "attempt_claimed",
            "allowed_pre_record_session_prefix_count": len(
                protocol.PRE_RECORD_SESSION_PREFIXES
            ),
            "empty_journal_representable": False,
            "zero_owner_failure_representable": False,
            "this_failure_representable": False,
            "terminal_synthesis_authorized": False,
            "failure_scope": None,
        },
        "formal_outcome": {
            "selected_outcome": None,
            "selection_authorized": False,
            "reason": "no_authenticated_owner_bound_terminal_state",
            "diagnostic_protocol_or_lineage_invalid_claimed": False,
            "diagnostic_inconclusive_claimed": False,
            "diagnostic_runtime_failure_claimed": False,
            "diagnostic_success_claimed": False,
        },
        "claims": {
            "execution_authority_published": True,
            "formal_invocation_budget_spent": True,
            "diagnostic_attempt_consumed": False,
            "diagnostic_executed": False,
            "model_loaded": False,
            "model_evaluated": False,
            "cuda_workload_executed": False,
            "diagnostic_terminal_published": False,
            "formal_measurement_complete": False,
            "historical_runtime_health_established": False,
            "runtime_root_cause_established": False,
            "recovery_v3_authorized": False,
            "runtime_eligible": False,
        },
        "limitations": {
            "controller_observation_is_formal_terminal_telemetry": False,
            "diagnostic_failure_scope_available": False,
            "model_or_output_quality_evaluated": False,
            "historical_generation_failure_reproduced": False,
            "preclaim_defect_establishes_historical_runtime_cause": False,
            "same_identity_retry_can_recover_missing_evidence": False,
        },
        "locked_next_action": {
            "next_gate_id": NEXT_GATE_ID,
            "maintenance_scope": [
                "deduplicate_feature_push_and_pull_request_ci",
                "add_ci_concurrency_and_timeout_bounds",
                "separate_three_version_pointer_contract_from_single_hydrated_lfs_integrity_gate",
                "preserve_required_check_context",
            ],
            "resume_gate_id": NEW_IDENTITY_PROTOCOL_GATE_ID,
            "resume_sequence": [
                NEW_IDENTITY_PROTOCOL_GATE_ID,
                NEW_IDENTITY_IMPLEMENTATION_GATE_ID,
                NEW_IDENTITY_AUTHORITY_GATE_ID,
                NEW_IDENTITY_EXECUTION_GATE_ID,
            ],
            "new_experiment_run_and_output_identity_required": True,
            "v1_retry_authorized": False,
            "v1_terminal_synthesis_authorized": False,
            "v1_output_parent_workaround_execution_authorized": False,
            "automatic_recovery_v3_authorized": False,
        },
        "publication": {
            "slice_paths": sorted(CLOSEOUT_SLICE_PATHS),
            "slice_path_count": len(CLOSEOUT_SLICE_PATHS),
            "diagnostic_runner_modified": False,
            "recovery_io_modified": False,
            "runtime_output_added_to_git": False,
            "terminal_artifact_added_to_git": False,
            "model_or_cuda_execution_by_closeout": False,
        },
    }
    return {**body, "report_digest": sha256_bytes(artifact_json_bytes(body))}


def validate_invocation_closeout(
    value: Mapping[str, Any],
    *,
    authority_payload: bytes,
    runner_payload: bytes,
    recovery_io_payload: bytes,
) -> None:
    """Require exact equality with the deterministic closeout."""

    if set(value) != set(REQUIRED_TOP_LEVEL_KEYS):
        _fail("CLOSEOUT_TOP_LEVEL_KEYS", "$")
    expected = build_invocation_closeout(
        authority_payload=authority_payload,
        runner_payload=runner_payload,
        recovery_io_payload=recovery_io_payload,
    )
    if dict(value) != expected:
        _fail("CLOSEOUT_MISMATCH", "$")


def parse_and_validate_invocation_closeout(
    payload: bytes,
    *,
    authority_payload: bytes,
    runner_payload: bytes,
    recovery_io_payload: bytes,
) -> dict[str, Any]:
    try:
        value = result_contract.parse_strict_json_bytes(
            payload, location="$.invocation_closeout"
        )
    except result_contract.MM005GenerationFailureDiagnosticResultError as exc:
        raise MM005GenerationFailureDiagnosticInvocationCloseoutError(
            exc.code, exc.location
        ) from exc
    if artifact_json_bytes(value) != payload:
        _fail("CLOSEOUT_NOT_CANONICAL", "$")
    validate_invocation_closeout(
        value,
        authority_payload=authority_payload,
        runner_payload=runner_payload,
        recovery_io_payload=recovery_io_payload,
    )
    return cast(dict[str, Any], value)


def _receipt(path: str, payload: bytes) -> dict[str, Any]:
    return {"path": path, "bytes": len(payload), "sha256": sha256_bytes(payload)}


def _validate_bound_payload(
    payload: bytes, *, expected_bytes: int, expected_sha256: str, location: str
) -> None:
    if (
        not isinstance(payload, bytes)
        or len(payload) != expected_bytes
        or sha256_bytes(payload) != expected_sha256
    ):
        _fail("BOUND_PAYLOAD_MISMATCH", location)


def _fail(code: str, location: str) -> NoReturn:
    raise MM005GenerationFailureDiagnosticInvocationCloseoutError(code, location)


__all__ = [
    "AUTHORITY_INTRODUCTION_COMMIT",
    "AUTHORITY_PARENT_COMMIT",
    "CLASSIFICATION",
    "CLOSEOUT_PATH",
    "CLOSEOUT_SLICE_PATHS",
    "FAILED_GATE_ID",
    "GATE_ID",
    "MM005GenerationFailureDiagnosticInvocationCloseoutError",
    "NEW_IDENTITY_PROTOCOL_GATE_ID",
    "NEXT_GATE_ID",
    "artifact_json_bytes",
    "build_invocation_closeout",
    "parse_and_validate_invocation_closeout",
    "sha256_bytes",
    "validate_invocation_closeout",
]
