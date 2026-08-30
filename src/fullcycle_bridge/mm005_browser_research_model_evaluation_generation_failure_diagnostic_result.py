"""Closed journal and terminal contracts for the MM-005 generation diagnostic.

The module is deliberately model-free.  It validates the frozen protocol,
attempt ownership, every durable checkpoint, and the mutually exclusive
success/failure artifacts.  It never imports or calls a model, processor,
PIL, torch, CUDA, browser, network, training, or Runtime integration.
"""

from __future__ import annotations

import copy
import math
import re
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any, NoReturn, cast

from . import (
    mm005_browser_research_model_evaluation_generation_failure_diagnostic as protocol,
)
from . import mm005_browser_research_model_evaluation_protocol_v2 as v2

RESULT_VERSION = 1
FAILURE_VERSION = 1
ATTEMPT_OWNER_VERSION = 1
PROGRESS_VERSION = 1
EXECUTION_AUTHORITY_VERSION = 1

GATE_ID = protocol.IMPLEMENTATION_GATE_ID
EXECUTION_AUTHORITY_GATE_ID = (
    "MM-005-browser-research-model-evaluation-generation-failure-"
    "diagnostic-execution-authority-v1"
)
EXECUTION_GATE_ID = (
    "MM-005-browser-research-model-evaluation-generation-failure-"
    "diagnostic-execution-v1"
)
EXECUTION_AUTHORITY_PATH = (
    "configs/mm005_browser_research_model_evaluation_generation_failure_"
    "diagnostic_execution_authority_v1.json"
)
RESULT_REVIEW_GATE_ID = (
    "MM-005-browser-research-model-evaluation-generation-failure-"
    "diagnostic-result-review-v1"
)

PROTOCOL_MERGE_COMMIT = "9c90c5e68d4386b30db613930ec7dc0147999c04"
PROTOCOL_BYTES = 57_143
PROTOCOL_SHA256 = (
    "sha256:13d1808168819414df2a0ca33d1f59e5e8efd52de6f0b49946d02cf070c992d6"
)

IMPLEMENTATION_SOURCE_PATHS = {
    "diagnostic_result_contract": (
        "src/fullcycle_bridge/mm005_browser_research_model_evaluation_"
        "generation_failure_diagnostic_result.py"
    ),
    "diagnostic_runner": (
        "scripts/run_mm005_browser_research_model_evaluation_generation_"
        "failure_diagnostic_v1.py"
    ),
    "diagnostic_result_tests": (
        "tests/test_mm005_browser_research_model_evaluation_generation_"
        "failure_diagnostic_result.py"
    ),
}
CRITICAL_EXECUTION_DEPENDENCY_SOURCE_PATHS = {
    "recovery_io": (
        "src/fullcycle_bridge/mm005_browser_research_model_evaluation_recovery_io.py"
    ),
    "repeatability_runner": "scripts/run_mm003_post_training_eval_repeatability.py",
    "upstream_model_runner": "scripts/run_mm003_qlora_post_training_v2.py",
    "v1_dataset_runner": ("scripts/run_mm005_browser_research_model_evaluation.py"),
}
EXECUTION_AUTHORITY_SLICE_PATHS = frozenset(
    {
        "AI_Infra_LLM_Agent_待做任务清单.md",
        "PROJECT_STATUS.md",
        "README.md",
        EXECUTION_AUTHORITY_PATH,
        (
            "docs/MM-005-browser-research-model-evaluation-generation-failure-"
            "diagnostic-execution-authority-v1.md"
        ),
        (
            "docs/MM-005-browser-research-model-evaluation-generation-failure-"
            "diagnostic-implementation-v1.md"
        ),
        "docs/README.md",
        (
            "scripts/prepare_mm005_browser_research_model_evaluation_generation_"
            "failure_diagnostic_execution_authority_v1.py"
        ),
        "scripts/validate_offline.py",
        (
            "tests/test_mm005_browser_research_model_evaluation_generation_failure_"
            "diagnostic_execution_authority.py"
        ),
    }
)

OUTCOME_PRECEDENCE = tuple(protocol.ALLOWED_OUTCOMES)
FAILURE_SCOPES = (
    "pre_record_lifecycle",
    "inter_record_transition",
    "active_record_substage",
    "post_record_terminalization",
)
SAFE_EXCEPTION_TYPE_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,95}")
COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}")
ATTEMPT_ID_PATTERN = re.compile(r"[0-9a-f]{64}")

RESULT_REQUIRED_TOP_LEVEL_KEYS = (
    "mm005_browser_research_generation_failure_diagnostic_result_version",
    "gate_id",
    "experiment_id",
    "run_id",
    "captured_at_utc",
    "classification",
    "protocol_lineage",
    "implementation_lineage",
    "execution_authority_lineage",
    "artifacts",
    "record_results",
    "observed_environment",
    "resources",
    "checkpoint_summary",
    "decision",
    "formal_gate",
    "claims",
    "limitations",
    "locked_next_action",
    "report_digest",
)

FAILURE_REQUIRED_TOP_LEVEL_KEYS = (
    "mm005_browser_research_generation_failure_diagnostic_failure_version",
    "gate_id",
    "experiment_id",
    "run_id",
    "captured_at_utc",
    "classification",
    "protocol_lineage",
    "implementation_lineage",
    "execution_authority_lineage",
    "artifacts",
    "failure_scope",
    "exception_type",
    "checkpoint_summary",
    "decision",
    "claims",
    "limitations",
    "locked_next_action",
    "report_digest",
)

FORMAL_RESULT_GATES = (
    "protocol_merge_and_blob_integrity",
    "implementation_source_integrity",
    "single_owner_and_zero_retry",
    "exact_session_lifecycle",
    "exact_seven_record_order",
    "exact_126_checkpoint_closure",
    "success_terminal_mutual_exclusion",
    "execution_environment_integrity",
    "resource_caps",
    "fail_closed_claims",
)


class MM005GenerationFailureDiagnosticResultError(ValueError):
    """Stable fail-closed error for diagnostic result or journal drift."""

    def __init__(self, code: str, location: str = "$") -> None:
        self.code = code
        self.location = location
        super().__init__(f"{code} at {location}")


def artifact_json_bytes(value: object) -> bytes:
    return cast(bytes, protocol.artifact_json_bytes(value))


def sha256_bytes(payload: bytes) -> str:
    return cast(str, protocol.sha256_bytes(payload))


def parse_strict_json_bytes(payload: bytes, *, location: str) -> dict[str, Any]:
    try:
        value = protocol.parse_strict_json_bytes(payload, location=location)
    except protocol.MM005GenerationFailureDiagnosticProtocolError as exc:
        raise MM005GenerationFailureDiagnosticResultError(
            exc.code, exc.location
        ) from exc
    return cast(dict[str, Any], value)


def result_contract() -> dict[str, Any]:
    """Return the closed implementation, journal, and terminal schema."""

    summary = {
        "result_version": RESULT_VERSION,
        "failure_version": FAILURE_VERSION,
        "attempt_owner_version": ATTEMPT_OWNER_VERSION,
        "progress_version": PROGRESS_VERSION,
        "execution_authority_version": EXECUTION_AUTHORITY_VERSION,
        "gate_id": GATE_ID,
        "next_gate_id": EXECUTION_AUTHORITY_GATE_ID,
        "reserved_execution_gate_id": EXECUTION_GATE_ID,
        "result_review_gate_id": RESULT_REVIEW_GATE_ID,
        "protocol_binding": {
            "merge_commit": PROTOCOL_MERGE_COMMIT,
            "path": protocol.PREREGISTRATION_PATH,
            "bytes": PROTOCOL_BYTES,
            "sha256": PROTOCOL_SHA256,
            "all_thirteen_protocol_sources_bound_to_merge_blobs": True,
        },
        "implementation_source_paths": dict(IMPLEMENTATION_SOURCE_PATHS),
        "critical_execution_dependency_source_paths": dict(
            CRITICAL_EXECUTION_DEPENDENCY_SOURCE_PATHS
        ),
        "execution_authority_slice_paths": sorted(EXECUTION_AUTHORITY_SLICE_PATHS),
        "execution_authority_contract": {
            "fixed_path": EXECUTION_AUTHORITY_PATH,
            "separate_clean_merge_required": True,
            "exact_implementation_freeze_commit_required": True,
            "exact_environment_and_resource_caps_required": True,
            "critical_execution_dependency_receipts_required": True,
            "authority_path_has_one_first_parent_introduction_commit": True,
            "authority_gate_has_exact_reviewed_slice_delta": True,
            "execute_head_must_equal_authority_introduction_commit": True,
            "reconcile_head_must_equal_authority_introduction_commit": True,
            "clean_aligned_master_and_origin_master_required": True,
            "assume_unchanged_or_skip_worktree_index_flags_forbidden": True,
            "git_fsmonitor_disabled_for_all_execution_checks": True,
            "owner_embeds_contract_and_binds_authority_freeze_commit": True,
            "implementation_gate_may_not_create_this_artifact": True,
        },
        "owner_contract": {
            "attempt_id_format": "64_lowercase_hex",
            "attempt_id_appears_only_in_owner": True,
            "lease_acquired_before_owner_claim": True,
            "owner_and_genesis_published_atomically": True,
            "reserved_sibling_staging_blocks_a_new_claim": True,
            "formal_invocation_budget": 1,
            "retry_budget": 0,
        },
        "journal_contract": {
            "format": "canonical_jsonl_append_only_sha256_chain",
            "session_lifecycle_events": list(protocol.SESSION_LIFECYCLE_EVENTS),
            "case_order": list(protocol.DIAGNOSTIC_CASE_ORDER),
            "durable_checkpoint_events": list(protocol.DIAGNOSTIC_CHECKPOINTS),
            "per_record_checkpoint_count": len(protocol.DIAGNOSTIC_CHECKPOINTS),
            "maximum_checkpoint_count": (
                protocol.FULL_SUCCESS_DURABLE_SUBSTAGE_EVENT_COUNT
            ),
            "event_identity_fields": list(protocol.EVENT_IDENTITY_FIELDS),
            "completed_record_ids_are_exact_case_order_prefix": True,
            "active_record_is_first_incomplete_record": True,
            "checkpoint_state_is_recomputed_not_caller_asserted": True,
            "no_frame_after_terminal": True,
        },
        "terminal_contract": {
            "success_and_failure_mutually_exclusive": True,
            "success_result_path": protocol.SUCCESS_RESULT_PATH,
            "failure_path": protocol.FAILURE_PATH,
            "success_requires_exact_7_record_126_checkpoint_plan": True,
            "failure_scopes": list(FAILURE_SCOPES),
            "active_record_failure_requires_nonempty_proper_prefix": True,
            "post_record_failure_is_exact_126_to_success_terminal_window": True,
            "failure_allowed_text_fields": ["exception_type"],
            "message_traceback_args_absolute_path_or_secret_forbidden": True,
            "terminal_artifact_exclusive_create_or_exact_prefix_repair": True,
        },
        "result_schema": {
            "required_top_level_keys": list(RESULT_REQUIRED_TOP_LEVEL_KEYS),
            "record_result_count": len(protocol.DIAGNOSTIC_CASE_ORDER),
            "formal_result_gates": list(FORMAL_RESULT_GATES),
            "selected_outcome": (
                "diagnostic_completed_without_observed_runtime_failure"
            ),
        },
        "failure_schema": {
            "required_top_level_keys": list(FAILURE_REQUIRED_TOP_LEVEL_KEYS),
            "active_record_outcome": (
                "diagnostic_failure_observed_between_durable_checkpoints"
            ),
            "other_scope_outcome": "diagnostic_inconclusive",
            "checkpoint_interval_is_not_causal_origin": True,
        },
        "outcome_selection": {
            "allowed_outcomes": list(protocol.ALLOWED_OUTCOMES),
            "precedence": list(OUTCOME_PRECEDENCE),
            "protocol_or_lineage_invalid_aborts_without_terminal_publication": True,
            "exactly_one_selected_after_valid_terminal": True,
        },
        "claims_contract": _negative_claims(),
        "publication_contract": {
            "implementation_must_cleanly_merge_before_authority_freeze": True,
            "separate_execution_authority_and_resource_preflight_required": True,
            "clean_implementation_merge_alone_authorizes_execution": False,
            "implementation_freeze_commit_recorded_in_owner_and_terminal": True,
            "feature_branch_formal_execution_eligible": False,
            "plan_is_read_only": True,
            "check_does_not_republish": True,
            "zero_internal_retry": True,
            "no_mutable_output_override": True,
        },
    }
    return summary


def execution_plan() -> dict[str, Any]:
    """Return the freeze-time plan; it grants no execution authority."""

    summary = {
        "implementation_contract_valid": True,
        "gate_id": GATE_ID,
        "next_gate_id": EXECUTION_AUTHORITY_GATE_ID,
        "reserved_execution_gate_id": EXECUTION_GATE_ID,
        "protocol_merge_commit": PROTOCOL_MERGE_COMMIT,
        "protocol_sha256": PROTOCOL_SHA256,
        "implementation_source_files": len(IMPLEMENTATION_SOURCE_PATHS),
        "result_and_failure_schema_frozen": True,
        "maximum_checkpoint_count": (
            protocol.FULL_SUCCESS_DURABLE_SUBSTAGE_EVENT_COUNT
        ),
        "formal_execution_eligible": False,
        "eligibility_reason": (
            "separate_execution_authority_and_exact_resource_preflight_must_"
            "freeze_after_the_clean_implementation_merge"
        ),
        "diagnostic_execution_authorized": False,
        "diagnostic_attempt_consumed": False,
        "diagnostic_executed": False,
        "selected_outcome": None,
        "model_processor_pil_torch_cuda_browser_network_authorized": False,
        "recovery_v3_authorized": False,
        "runtime_eligible": False,
    }
    return summary


def select_outcome(
    *,
    protocol_and_lineage_valid: bool,
    terminal_kind: str | None,
    failure_scope: str | None,
) -> str:
    """Select exactly one outcome from trusted terminal state."""

    if type(protocol_and_lineage_valid) is not bool:
        _fail("OUTCOME_TRUST_BOOL_REQUIRED", "$.decision")
    if not protocol_and_lineage_valid:
        if terminal_kind is not None or failure_scope is not None:
            _fail("UNTRUSTED_TERMINAL_PUBLICATION_FORBIDDEN", "$.decision")
        return "diagnostic_protocol_or_lineage_invalid"
    if terminal_kind == "success" and failure_scope is None:
        return "diagnostic_completed_without_observed_runtime_failure"
    if terminal_kind == "failure" and failure_scope in FAILURE_SCOPES:
        if failure_scope == "active_record_substage":
            return "diagnostic_failure_observed_between_durable_checkpoints"
        return "diagnostic_inconclusive"
    _fail("OUTCOME_TERMINAL_STATE_INVALID", "$.decision")


def build_execution_authority_contract(
    *,
    implementation_freeze_commit: str,
    expected_environment: Mapping[str, Any],
    critical_execution_dependency_receipts: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the future gate's closed authority payload without publishing it."""

    _validate_commit(implementation_freeze_commit, "$.implementation_freeze_commit")
    environment = _validated_environment(expected_environment)
    dependency_receipts = _validated_critical_execution_dependency_receipts(
        critical_execution_dependency_receipts
    )
    return {
        "mm005_browser_research_generation_failure_diagnostic_execution_authority_version": (
            EXECUTION_AUTHORITY_VERSION
        ),
        "gate_id": EXECUTION_AUTHORITY_GATE_ID,
        "next_gate": EXECUTION_GATE_ID,
        "protocol_merge_commit": PROTOCOL_MERGE_COMMIT,
        "implementation_freeze_commit": implementation_freeze_commit,
        "critical_execution_dependency_receipts": dependency_receipts,
        "resource_preflight": {
            "expected_environment": environment,
            "resource_caps": dict(v2.RESOURCE_CAPS),
            "exact_environment_match_required_before_model_load_or_cuda_workload": True,
            "read_only_cuda_capability_observation_allowed_for_exact_match": True,
            "missing_or_unverifiable_resource_blocks_execution": True,
        },
        "budgets": {
            "formal_invocations": 1,
            "retries": 0,
            "per_record_attempts": 1,
        },
        "authority_contract": {
            "diagnostic_execution_authorized": True,
            "v1_or_v2_retry_authorized": False,
            "recovery_v3_authorized": False,
            "live_browser_or_network_authorized": False,
            "training_authorized": False,
            "runtime_integration_changed": False,
            "runtime_policy_or_approval_bypass": False,
            "current_head_equals_authority_introduction_commit": True,
            "assume_unchanged_or_skip_worktree_index_flags_forbidden": True,
            "git_fsmonitor_disabled": True,
            "reserved_sibling_staging_blocks_execution": True,
        },
        "claims": {
            "authority_frozen": True,
            "diagnostic_attempt_consumed": False,
            "diagnostic_executed": False,
            "model_evaluated": False,
            "runtime_eligible": False,
        },
    }


def build_attempt_owner(
    *,
    implementation_freeze_commit: str,
    preregistration_payload: bytes,
    authority_freeze_commit: str,
    execution_authority_payload: bytes,
    attempt_id: str,
) -> dict[str, Any]:
    _validate_commit(implementation_freeze_commit, "$.implementation_freeze_commit")
    _validate_commit(authority_freeze_commit, "$.authority_freeze_commit")
    _validated_preregistration_payload(preregistration_payload)
    authority = _validated_execution_authority_payload(
        execution_authority_payload,
        implementation_freeze_commit=implementation_freeze_commit,
    )
    if type(attempt_id) is not str or ATTEMPT_ID_PATTERN.fullmatch(attempt_id) is None:
        _fail("ATTEMPT_ID_INVALID", "$.attempt_id")
    return {
        "mm005_browser_research_generation_failure_diagnostic_attempt_owner_version": (
            ATTEMPT_OWNER_VERSION
        ),
        "gate_id": EXECUTION_GATE_ID,
        "experiment_id": protocol.EXPERIMENT_ID,
        "run_id": protocol.RUN_ID,
        "protocol_merge_commit": PROTOCOL_MERGE_COMMIT,
        "implementation_freeze_commit": implementation_freeze_commit,
        "execution_authority": {
            "freeze_commit": authority_freeze_commit,
            "artifact": _receipt(EXECUTION_AUTHORITY_PATH, execution_authority_payload),
            "contract": authority,
        },
        "preregistration": _receipt(
            protocol.PREREGISTRATION_PATH, preregistration_payload
        ),
        "attempt_id": attempt_id,
        "budgets": {
            "formal_invocations": 1,
            "retries": 0,
            "per_record_attempts": 1,
        },
        "claims": {
            "single_owner": True,
            "attempt_claimed": True,
            "diagnostic_result_exists": False,
            "diagnostic_failure_exists": False,
            "model_output_has_execution_authority": False,
            "runtime_eligible": False,
        },
    }


def validate_attempt_owner(
    value: object,
    *,
    implementation_freeze_commit: str,
    preregistration_payload: bytes,
) -> dict[str, Any]:
    observed = _mapping(value, "$.attempt_owner")
    authority = _mapping(
        observed.get("execution_authority"), "$.attempt_owner.execution_authority"
    )
    authority_contract = _mapping(
        authority.get("contract"), "$.attempt_owner.execution_authority.contract"
    )
    expected = build_attempt_owner(
        implementation_freeze_commit=implementation_freeze_commit,
        preregistration_payload=preregistration_payload,
        authority_freeze_commit=str(authority.get("freeze_commit")),
        execution_authority_payload=artifact_json_bytes(authority_contract),
        attempt_id=str(observed.get("attempt_id")),
    )
    if not _json_equal(observed, expected):
        _fail("ATTEMPT_OWNER_MISMATCH", "$.attempt_owner")
    return expected


def build_progress_event(
    *,
    previous_journal_payload: bytes,
    implementation_freeze_commit: str,
    preregistration_payload: bytes,
    attempt_owner_payload: bytes,
    event: str,
    record_id: str | None = None,
    diagnostic_index: int | None = None,
    observed_environment: Mapping[str, Any] | None = None,
    captured_at_utc: str | None = None,
    exception_type: str | None = None,
    resources: Mapping[str, Any] | None = None,
    case_result: Mapping[str, Any] | None = None,
    discarded_progress_tail: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the one exact next progress frame from authenticated history."""

    owner = _validated_owner_payload(
        attempt_owner_payload,
        implementation_freeze_commit=implementation_freeze_commit,
        preregistration_payload=preregistration_payload,
    )
    previous_events = validate_progress_journal(
        previous_journal_payload,
        implementation_freeze_commit=implementation_freeze_commit,
        preregistration_payload=preregistration_payload,
        attempt_owner_payload=attempt_owner_payload,
        allow_empty=True,
    )
    return _expected_progress_event(
        previous_events=previous_events,
        previous_journal_payload=previous_journal_payload,
        owner=owner,
        preregistration_payload=preregistration_payload,
        attempt_owner_payload=attempt_owner_payload,
        event=event,
        record_id=record_id,
        diagnostic_index=diagnostic_index,
        observed_environment=observed_environment,
        captured_at_utc=captured_at_utc,
        exception_type=exception_type,
        resources=resources,
        case_result=case_result,
        discarded_progress_tail=discarded_progress_tail,
    )


def build_case_result_summary(
    case_result: Mapping[str, Any], *, diagnostic_index: int
) -> dict[str, Any]:
    """Project one in-memory case to a closed, text-free durable summary."""

    if type(diagnostic_index) is not int or not (
        0 <= diagnostic_index < len(protocol.DIAGNOSTIC_CASE_ORDER)
    ):
        _fail("CASE_SUMMARY_INDEX_INVALID", "$.case_result")
    case = _mapping(case_result, "$.case_result")
    record_id = protocol.DIAGNOSTIC_CASE_ORDER[diagnostic_index]
    if case.get("record_id") != record_id:
        _fail("CASE_SUMMARY_RECORD_ID_INVALID", "$.case_result")
    raw_value = case.get("raw_output")
    if type(raw_value) is not str:
        _fail("CASE_SUMMARY_RAW_OUTPUT_TYPE", "$.case_result.raw_output")
    try:
        raw_output = raw_value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise MM005GenerationFailureDiagnosticResultError(
            "CASE_SUMMARY_RAW_OUTPUT_UTF8", "$.case_result.raw_output"
        ) from exc
    canonical_case = artifact_json_bytes(dict(case))
    if len(canonical_case) > 64 * 1024:
        _fail("CASE_SUMMARY_CASE_OVERSIZED", "$.case_result")
    summary = {
        "record_id": record_id,
        "diagnostic_index": diagnostic_index,
        "case_result": _byte_receipt(canonical_case),
        "raw_output": _byte_receipt(raw_output),
        "compiled_output": _byte_receipt(
            artifact_json_bytes(case.get("compiled_output"))
        ),
        "verdict": _byte_receipt(artifact_json_bytes(case.get("verdict"))),
        "citation_semantics": _byte_receipt(
            artifact_json_bytes(case.get("citation_semantics"))
        ),
        "generated_tokens": _strict_int(
            case.get("generated_tokens"), "$.case_result.generated_tokens"
        ),
        "latency_seconds": _strict_number(
            case.get("latency_seconds"), "$.case_result.latency_seconds"
        ),
        "model_payload_sha256": _sha256_text(
            case.get("model_payload_sha256"), "$.case_result.model_payload_sha256"
        ),
        "prompt_projection_sha256": _sha256_text(
            case.get("prompt_projection_sha256"),
            "$.case_result.prompt_projection_sha256",
        ),
        "source_count": _strict_int(
            case.get("source_count"), "$.case_result.source_count"
        ),
        "screenshot_sha256": _sha256_sequence(
            case.get("screenshot_sha256"), "$.case_result.screenshot_sha256"
        ),
        "source_snapshot_sha256": _sha256_sequence(
            case.get("source_snapshot_sha256"),
            "$.case_result.source_snapshot_sha256",
        ),
        "arbitrary_model_text_persisted": False,
        "model_output_has_execution_authority": False,
    }
    return _validated_case_summary(summary, diagnostic_index, "$.case_result")


def _validated_case_summary(
    value: object, diagnostic_index: int, location: str
) -> dict[str, Any]:
    observed = _mapping(value, location)
    record_id = protocol.DIAGNOSTIC_CASE_ORDER[diagnostic_index]
    expected_keys = {
        "record_id",
        "diagnostic_index",
        "case_result",
        "raw_output",
        "compiled_output",
        "verdict",
        "citation_semantics",
        "generated_tokens",
        "latency_seconds",
        "model_payload_sha256",
        "prompt_projection_sha256",
        "source_count",
        "screenshot_sha256",
        "source_snapshot_sha256",
        "arbitrary_model_text_persisted",
        "model_output_has_execution_authority",
    }
    if set(observed) != expected_keys:
        _fail("CASE_SUMMARY_FIELDS", location)
    source_count = _strict_int(observed.get("source_count"), f"{location}.source_count")
    generated_tokens = _strict_int(
        observed.get("generated_tokens"), f"{location}.generated_tokens"
    )
    latency = _strict_number(
        observed.get("latency_seconds"), f"{location}.latency_seconds"
    )
    screenshots = _sha256_sequence(
        observed.get("screenshot_sha256"), f"{location}.screenshot_sha256"
    )
    snapshots = _sha256_sequence(
        observed.get("source_snapshot_sha256"),
        f"{location}.source_snapshot_sha256",
    )
    expected = {
        "record_id": record_id,
        "diagnostic_index": diagnostic_index,
        "case_result": _closed_byte_receipt(
            observed.get("case_result"), f"{location}.case_result"
        ),
        "raw_output": _closed_byte_receipt(
            observed.get("raw_output"), f"{location}.raw_output"
        ),
        "compiled_output": _closed_byte_receipt(
            observed.get("compiled_output"), f"{location}.compiled_output"
        ),
        "verdict": _closed_byte_receipt(observed.get("verdict"), f"{location}.verdict"),
        "citation_semantics": _closed_byte_receipt(
            observed.get("citation_semantics"), f"{location}.citation_semantics"
        ),
        "generated_tokens": generated_tokens,
        "latency_seconds": latency,
        "model_payload_sha256": _sha256_text(
            observed.get("model_payload_sha256"),
            f"{location}.model_payload_sha256",
        ),
        "prompt_projection_sha256": _sha256_text(
            observed.get("prompt_projection_sha256"),
            f"{location}.prompt_projection_sha256",
        ),
        "source_count": source_count,
        "screenshot_sha256": screenshots,
        "source_snapshot_sha256": snapshots,
        "arbitrary_model_text_persisted": False,
        "model_output_has_execution_authority": False,
    }
    if (
        generated_tokens < 0
        or generated_tokens > v2.MAX_NEW_TOKENS
        or latency < 0
        or source_count <= 0
        or len(screenshots) != source_count
        or len(snapshots) != source_count
        or not _json_equal(observed, expected)
    ):
        _fail("CASE_SUMMARY_INVALID", location)
    return expected


def validate_progress_journal(
    payload: bytes,
    *,
    implementation_freeze_commit: str,
    preregistration_payload: bytes,
    attempt_owner_payload: bytes,
    allow_empty: bool = False,
) -> list[dict[str, Any]]:
    if type(payload) is not bytes or len(payload) > 8 * 1024 * 1024:
        _fail("PROGRESS_BYTES_INVALID", "$.progress")
    if not payload:
        if allow_empty:
            return []
        _fail("PROGRESS_EMPTY", "$.progress")
    if not payload.endswith(b"\n"):
        _fail("PROGRESS_PARTIAL_LINE", "$.progress")
    owner = _validated_owner_payload(
        attempt_owner_payload,
        implementation_freeze_commit=implementation_freeze_commit,
        preregistration_payload=preregistration_payload,
    )
    events: list[dict[str, Any]] = []
    authenticated = b""
    for index, line in enumerate(payload.splitlines(keepends=True)):
        value = parse_strict_json_bytes(line, location=f"$.progress[{index}]")
        if artifact_json_bytes(value) != line:
            _fail("PROGRESS_EVENT_NOT_CANONICAL", f"$.progress[{index}]")
        terminal = _mapping_or_none(value.get("terminal"), f"$.progress[{index}]")
        environment = value.get("observed_environment")
        resource_value = value.get("resources")
        expected = _expected_progress_event(
            previous_events=events,
            previous_journal_payload=authenticated,
            owner=owner,
            preregistration_payload=preregistration_payload,
            attempt_owner_payload=attempt_owner_payload,
            event=str(value.get("event")),
            record_id=(
                None if value.get("record_id") is None else str(value["record_id"])
            ),
            diagnostic_index=(
                None
                if value.get("diagnostic_index") is None
                else _strict_int(
                    value.get("diagnostic_index"),
                    f"$.progress[{index}].diagnostic_index",
                )
            ),
            observed_environment=(
                _mapping(environment, f"$.progress[{index}].observed_environment")
                if value.get("event") == "context_preflight_completed"
                else None
            ),
            captured_at_utc=(
                None if terminal is None else str(terminal.get("captured_at_utc"))
            ),
            exception_type=(
                None if terminal is None else terminal.get("exception_type")
            ),
            resources=(
                _mapping(resource_value, f"$.progress[{index}].resources")
                if value.get("event") == "success_terminal_ready"
                else None
            ),
            case_result=(
                _mapping(value.get("case_result"), f"$.progress[{index}].case_result")
                if value.get("event") == "case_result_build_completed"
                else None
            ),
            discarded_progress_tail=(
                None
                if terminal is None or terminal.get("discarded_progress_tail") is None
                else _mapping(
                    terminal.get("discarded_progress_tail"),
                    f"$.progress[{index}].terminal.discarded_progress_tail",
                )
            ),
        )
        if not _json_equal(value, expected):
            _fail("PROGRESS_EVENT_MISMATCH", f"$.progress[{index}]")
        events.append(expected)
        authenticated += line
    return events


def recover_progress_prefix(
    payload: bytes,
    *,
    implementation_freeze_commit: str,
    preregistration_payload: bytes,
    attempt_owner_payload: bytes,
) -> tuple[list[dict[str, Any]], bytes, dict[str, Any] | None]:
    """Return the authenticated JSONL prefix plus a non-claiming tail receipt."""

    if not payload:
        _fail("PROGRESS_EMPTY", "$.progress")
    last_newline = payload.rfind(b"\n")
    if last_newline < 0:
        _fail("PROGRESS_INITIAL_EVENT_NOT_DURABLE", "$.progress")
    prefix = payload[: last_newline + 1]
    tail = payload[last_newline + 1 :]
    events = validate_progress_journal(
        prefix,
        implementation_freeze_commit=implementation_freeze_commit,
        preregistration_payload=preregistration_payload,
        attempt_owner_payload=attempt_owner_payload,
    )
    tail_receipt = None
    if tail:
        if b"\n" in tail or len(tail) > 1_048_576:
            _fail("PROGRESS_PARTIAL_TAIL_INVALID", "$.progress")
        tail_receipt = {
            "bytes": len(tail),
            "sha256": sha256_bytes(tail),
            "authenticated_event": False,
            "execution_fact_claimed": False,
        }
    return events, prefix, tail_receipt


def failure_scope_for_journal(
    payload: bytes,
    *,
    implementation_freeze_commit: str,
    preregistration_payload: bytes,
    attempt_owner_payload: bytes,
) -> str:
    events = validate_progress_journal(
        payload,
        implementation_freeze_commit=implementation_freeze_commit,
        preregistration_payload=preregistration_payload,
        attempt_owner_payload=attempt_owner_payload,
    )
    if events[-1]["event"] in protocol.TERMINAL_EVENTS:
        _fail("FAILURE_SCOPE_AFTER_TERMINAL", "$.progress")
    return _derive_failure_scope(events[-1])


def build_diagnostic_result(
    *,
    implementation_freeze_commit: str,
    preregistration_payload: bytes,
    attempt_owner_payload: bytes,
    progress_payload: bytes,
    implementation_context: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the exact success result from a success-terminal journal."""

    context = _validated_terminal_context(
        implementation_freeze_commit=implementation_freeze_commit,
        preregistration_payload=preregistration_payload,
        attempt_owner_payload=attempt_owner_payload,
        progress_payload=progress_payload,
        implementation_context=implementation_context,
        expected_terminal="success_terminal_ready",
    )
    terminal = context["terminal"]
    checked_cases = _validated_cases_from_events(context["events"])
    environment = _validated_environment(terminal["observed_environment"])
    resources = _validated_resources(terminal["resources"])
    outcome = select_outcome(
        protocol_and_lineage_valid=True,
        terminal_kind="success",
        failure_scope=None,
    )
    gates = {name: True for name in FORMAL_RESULT_GATES}
    gates["resource_caps"] = all(
        resources[name] <= limit for name, limit in v2.RESOURCE_CAPS.items()
    )
    formal_gate_passed = all(gates.values())
    without_digest = {
        "mm005_browser_research_generation_failure_diagnostic_result_version": (
            RESULT_VERSION
        ),
        "gate_id": EXECUTION_GATE_ID,
        "experiment_id": protocol.EXPERIMENT_ID,
        "run_id": protocol.RUN_ID,
        "captured_at_utc": terminal["terminal"]["captured_at_utc"],
        "classification": outcome,
        "protocol_lineage": context["protocol_lineage"],
        "implementation_lineage": context["implementation_lineage"],
        "execution_authority_lineage": context["execution_authority_lineage"],
        "artifacts": context["artifacts"],
        "record_results": checked_cases,
        "observed_environment": environment,
        "resources": resources,
        "checkpoint_summary": _checkpoint_summary(terminal),
        "decision": {
            "selected_outcome": outcome,
            "runtime_failure_observed": False,
            "historical_runtime_health_established": False,
            "runtime_root_cause_established": False,
            "checkpoint_interval_is_causal_origin": False,
        },
        "formal_gate": {
            "required_gates": gates,
            "passed": formal_gate_passed,
            "quality_threshold_applied": False,
        },
        "claims": {
            **_negative_claims(),
            "diagnostic_attempt_consumed": True,
            "diagnostic_executed": True,
            "all_registered_diagnostic_calls_completed": True,
            "diagnostic_completed_without_observed_runtime_failure": True,
        },
        "limitations": _limitations(),
        "locked_next_action": _result_review_action(),
    }
    return {
        **without_digest,
        "report_digest": sha256_bytes(artifact_json_bytes(without_digest)),
    }


def validate_diagnostic_result(value: object, **inputs: Any) -> dict[str, Any]:
    observed = _mapping(value, "$.diagnostic_result")
    expected = build_diagnostic_result(**inputs)
    if set(observed) != set(RESULT_REQUIRED_TOP_LEVEL_KEYS) or not _json_equal(
        observed, expected
    ):
        _fail("DIAGNOSTIC_RESULT_MISMATCH", "$.diagnostic_result")
    return expected


def build_diagnostic_failure(
    *,
    implementation_freeze_commit: str,
    preregistration_payload: bytes,
    attempt_owner_payload: bytes,
    progress_payload: bytes,
    implementation_context: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the exact safe failure artifact from a failure-terminal journal."""

    context = _validated_terminal_context(
        implementation_freeze_commit=implementation_freeze_commit,
        preregistration_payload=preregistration_payload,
        attempt_owner_payload=attempt_owner_payload,
        progress_payload=progress_payload,
        implementation_context=implementation_context,
        expected_terminal="failure_terminal_ready",
    )
    terminal = context["terminal"]
    terminal_data = _mapping(terminal.get("terminal"), "$.progress.terminal")
    scope = str(terminal_data.get("failure_scope"))
    exception_type = _safe_exception_type(
        terminal_data.get("exception_type"), "$.progress.terminal.exception_type"
    )
    outcome = select_outcome(
        protocol_and_lineage_valid=True,
        terminal_kind="failure",
        failure_scope=scope,
    )
    diagnostic_started = (
        bool(terminal["completed_record_ids"])
        or terminal["active_record_id"] is not None
        or scope == "post_record_terminalization"
    )
    without_digest = {
        "mm005_browser_research_generation_failure_diagnostic_failure_version": (
            FAILURE_VERSION
        ),
        "gate_id": EXECUTION_GATE_ID,
        "experiment_id": protocol.EXPERIMENT_ID,
        "run_id": protocol.RUN_ID,
        "captured_at_utc": terminal_data["captured_at_utc"],
        "classification": outcome,
        "protocol_lineage": context["protocol_lineage"],
        "implementation_lineage": context["implementation_lineage"],
        "execution_authority_lineage": context["execution_authority_lineage"],
        "artifacts": context["artifacts"],
        "failure_scope": scope,
        "exception_type": exception_type,
        "checkpoint_summary": _checkpoint_summary(terminal),
        "decision": {
            "selected_outcome": outcome,
            "runtime_failure_observed_between_durable_checkpoints": (
                scope == "active_record_substage"
            ),
            "failed_runtime_substage_isolated": False,
            "runtime_root_cause_established": False,
            "checkpoint_interval_is_causal_origin": False,
        },
        "claims": {
            **_negative_claims(),
            "diagnostic_attempt_consumed": True,
            "diagnostic_executed": diagnostic_started,
            "all_registered_diagnostic_calls_completed": (
                scope == "post_record_terminalization"
            ),
            "diagnostic_failure_observed_between_durable_checkpoints": (
                scope == "active_record_substage"
            ),
        },
        "limitations": _limitations(),
        "locked_next_action": _result_review_action(),
    }
    return {
        **without_digest,
        "report_digest": sha256_bytes(artifact_json_bytes(without_digest)),
    }


def validate_diagnostic_failure(value: object, **inputs: Any) -> dict[str, Any]:
    observed = _mapping(value, "$.diagnostic_failure")
    expected = build_diagnostic_failure(**inputs)
    if set(observed) != set(FAILURE_REQUIRED_TOP_LEVEL_KEYS) or not _json_equal(
        observed, expected
    ):
        _fail("DIAGNOSTIC_FAILURE_MISMATCH", "$.diagnostic_failure")
    return expected


def _expected_progress_event(
    *,
    previous_events: Sequence[Mapping[str, Any]],
    previous_journal_payload: bytes,
    owner: Mapping[str, Any],
    preregistration_payload: bytes,
    attempt_owner_payload: bytes,
    event: str,
    record_id: str | None,
    diagnostic_index: int | None,
    observed_environment: Mapping[str, Any] | None,
    captured_at_utc: str | None,
    exception_type: object,
    resources: Mapping[str, Any] | None,
    case_result: Mapping[str, Any] | None,
    discarded_progress_tail: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if previous_events and previous_events[-1].get("event") in protocol.TERMINAL_EVENTS:
        _fail("PROGRESS_AFTER_TERMINAL", "$.progress")
    previous = previous_events[-1] if previous_events else None
    sequence = len(previous_events)
    previous_hash = (
        None if previous is None else sha256_bytes(artifact_json_bytes(dict(previous)))
    )
    state = _state_after_event(
        previous,
        owner=owner,
        event=event,
        record_id=record_id,
        diagnostic_index=diagnostic_index,
        observed_environment=observed_environment,
        captured_at_utc=captured_at_utc,
        exception_type=exception_type,
        resources=resources,
        case_result=case_result,
        discarded_progress_tail=discarded_progress_tail,
    )
    return {
        "mm005_browser_research_generation_failure_diagnostic_progress_version": (
            PROGRESS_VERSION
        ),
        "gate_id": EXECUTION_GATE_ID,
        "experiment_id": protocol.EXPERIMENT_ID,
        "run_id": protocol.RUN_ID,
        "sequence": sequence,
        "previous_event_sha256": previous_hash,
        "protocol_merge_commit": PROTOCOL_MERGE_COMMIT,
        "implementation_freeze_commit": owner["implementation_freeze_commit"],
        "execution_authority_freeze_commit": _mapping(
            owner["execution_authority"], "$.attempt_owner.execution_authority"
        )["freeze_commit"],
        "preregistration": _receipt(
            protocol.PREREGISTRATION_PATH, preregistration_payload
        ),
        "attempt_owner": _receipt(protocol.ATTEMPT_OWNER_PATH, attempt_owner_payload),
        **state,
        "claims": {
            "durable_checkpoint": True,
            "uncheckpointed_work_claimed": False,
            "checkpoint_interval_is_causal_origin": False,
            "model_output_has_execution_authority": False,
            "runtime_eligible": False,
        },
    }


def _state_after_event(
    previous: Mapping[str, Any] | None,
    *,
    owner: Mapping[str, Any],
    event: str,
    record_id: str | None,
    diagnostic_index: int | None,
    observed_environment: Mapping[str, Any] | None,
    captured_at_utc: str | None,
    exception_type: object,
    resources: Mapping[str, Any] | None,
    case_result: Mapping[str, Any] | None,
    discarded_progress_tail: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if previous is None:
        if (
            event != "attempt_claimed"
            or record_id is not None
            or diagnostic_index is not None
            or any(
                value is not None
                for value in (
                    observed_environment,
                    captured_at_utc,
                    exception_type,
                    resources,
                    case_result,
                    discarded_progress_tail,
                )
            )
        ):
            _fail("PROGRESS_GENESIS_INVALID", "$.progress")
        return _state_object(
            event=event,
            record_id=None,
            diagnostic_index=None,
            session_events=[event],
            completed=[],
            active_record_id=None,
            active_index=None,
            active_events=[],
            checkpoint_count=0,
            last_started=None,
            last_completed=None,
            environment=None,
            resources=None,
            terminal=None,
        )

    session_events = _string_sequence(
        previous.get("session_lifecycle_events"), "$.previous.session_lifecycle_events"
    )
    completed = _string_sequence(
        previous.get("completed_record_ids"), "$.previous.completed_record_ids"
    )
    active_id = previous.get("active_record_id")
    active_index = previous.get("active_record_diagnostic_index")
    active_events = _string_sequence(
        previous.get("active_record_events"), "$.previous.active_record_events"
    )
    checkpoint_count = _strict_int(
        previous.get("durable_substage_event_count"),
        "$.previous.durable_substage_event_count",
    )
    environment = previous.get("observed_environment")

    if event == "failure_terminal_ready":
        if record_id is not None or diagnostic_index is not None:
            _fail("FAILURE_TERMINAL_RECORD_ID_FORBIDDEN", "$.progress")
        if (
            observed_environment is not None
            or resources is not None
            or case_result is not None
        ):
            _fail("FAILURE_TERMINAL_EXTRA_OBSERVATION", "$.progress")
        _validate_timestamp(captured_at_utc)
        checked_exception = _safe_exception_type(
            exception_type, "$.progress.terminal.exception_type"
        )
        scope = _derive_failure_scope(previous)
        last_started = previous.get("last_started_checkpoint")
        last_completed = previous.get("last_completed_checkpoint")
        if scope in {"pre_record_lifecycle", "inter_record_transition"}:
            last_started = None
            last_completed = None
        if scope == "inter_record_transition":
            active_index = len(completed)
            active_id = protocol.DIAGNOSTIC_CASE_ORDER[active_index]
        elif scope == "post_record_terminalization":
            final_plan = protocol.PER_RECORD_CHECKPOINT_PLANS[-1]["durable_events"]
            last_started = dict(final_plan[-2])
            last_completed = dict(final_plan[-1])
        terminal = {
            "kind": "failure",
            "captured_at_utc": captured_at_utc,
            "failure_scope": scope,
            "exception_type": checked_exception,
            "selected_outcome": select_outcome(
                protocol_and_lineage_valid=True,
                terminal_kind="failure",
                failure_scope=scope,
            ),
            "continue_after_failure": False,
            "retry_authorized": False,
            "message_traceback_path_or_secret_persisted": False,
            "discarded_progress_tail": _closed_discarded_tail(
                discarded_progress_tail,
                "$.progress.terminal.discarded_progress_tail",
            ),
        }
        return _state_object(
            event=event,
            record_id=None,
            diagnostic_index=None,
            session_events=session_events,
            completed=completed,
            active_record_id=(None if active_id is None else str(active_id)),
            active_index=(
                None
                if active_index is None
                else _strict_int(
                    active_index, "$.previous.active_record_diagnostic_index"
                )
            ),
            active_events=active_events,
            checkpoint_count=checkpoint_count,
            last_started=_mapping_copy_or_none(last_started, "$.previous.last_started"),
            last_completed=_mapping_copy_or_none(
                last_completed, "$.previous.last_completed"
            ),
            environment=_mapping_copy_or_none(environment, "$.previous.environment"),
            resources=None,
            terminal=terminal,
        )

    if event == "success_terminal_ready":
        if (
            record_id is not None
            or diagnostic_index is not None
            or observed_environment is not None
            or exception_type is not None
            or case_result is not None
            or discarded_progress_tail is not None
            or completed != list(protocol.DIAGNOSTIC_CASE_ORDER)
            or active_id is not None
            or active_events
            or checkpoint_count != protocol.FULL_SUCCESS_DURABLE_SUBSTAGE_EVENT_COUNT
        ):
            _fail("SUCCESS_TERMINAL_STATE_INVALID", "$.progress")
        _validate_timestamp(captured_at_utc)
        checked_resources = _validated_resources(resources)
        terminal = {
            "kind": "success",
            "captured_at_utc": captured_at_utc,
            "selected_outcome": select_outcome(
                protocol_and_lineage_valid=True,
                terminal_kind="success",
                failure_scope=None,
            ),
            "runtime_failure_observed": False,
        }
        return _state_object(
            event=event,
            record_id=None,
            diagnostic_index=None,
            session_events=session_events,
            completed=completed,
            active_record_id=None,
            active_index=None,
            active_events=[],
            checkpoint_count=checkpoint_count,
            last_started=dict(
                protocol.PER_RECORD_CHECKPOINT_PLANS[-1]["durable_events"][-2]
            ),
            last_completed=dict(
                protocol.PER_RECORD_CHECKPOINT_PLANS[-1]["durable_events"][-1]
            ),
            environment=_mapping_copy_or_none(environment, "$.previous.environment"),
            resources=checked_resources,
            terminal=terminal,
        )

    if any(
        value is not None
        for value in (
            captured_at_utc,
            exception_type,
            resources,
            discarded_progress_tail,
        )
    ):
        _fail("NONTERMINAL_TERMINAL_FIELDS", "$.progress")

    session_index = len(session_events)
    if session_index < len(protocol.SESSION_LIFECYCLE_EVENTS):
        expected_event = protocol.SESSION_LIFECYCLE_EVENTS[session_index]
        if (
            event != expected_event
            or record_id is not None
            or diagnostic_index is not None
        ):
            _fail("SESSION_LIFECYCLE_TRANSITION", "$.progress")
        if case_result is not None:
            _fail("CASE_RESULT_EVENT_INVALID", "$.progress")
        if event == "context_preflight_completed":
            environment = _validated_environment(observed_environment)
            owner_authority = _mapping(
                owner.get("execution_authority"), "$.attempt_owner.execution_authority"
            )
            authority_contract = _mapping(
                owner_authority.get("contract"),
                "$.attempt_owner.execution_authority.contract",
            )
            authority_preflight = _mapping(
                authority_contract.get("resource_preflight"),
                "$.attempt_owner.execution_authority.contract.resource_preflight",
            )
            authority_environment = _validated_environment(
                authority_preflight.get("expected_environment")
            )
            if not _json_equal(environment, authority_environment):
                _fail("ENVIRONMENT_AUTHORITY_MISMATCH", "$.observed_environment")
        elif observed_environment is not None:
            _fail("ENVIRONMENT_OBSERVATION_EVENT_INVALID", "$.progress")
        session_events.append(event)
        return _state_object(
            event=event,
            record_id=None,
            diagnostic_index=None,
            session_events=session_events,
            completed=completed,
            active_record_id=None,
            active_index=None,
            active_events=[],
            checkpoint_count=checkpoint_count,
            last_started=None,
            last_completed=None,
            environment=_mapping_copy_or_none(environment, "$.environment"),
            resources=None,
            terminal=None,
        )

    if observed_environment is not None:
        _fail("ENVIRONMENT_OBSERVATION_EVENT_INVALID", "$.progress")
    if len(session_events) != len(protocol.SESSION_LIFECYCLE_EVENTS):
        _fail("SESSION_LIFECYCLE_INCOMPLETE", "$.progress")
    expected_index = len(completed)
    if active_id is None:
        if expected_index >= len(protocol.DIAGNOSTIC_CASE_ORDER):
            _fail("CHECKPOINT_AFTER_COMPLETE_PLAN", "$.progress")
        expected_record = protocol.DIAGNOSTIC_CASE_ORDER[expected_index]
        expected_checkpoint = protocol.DIAGNOSTIC_CHECKPOINTS[0]
        if (
            record_id != expected_record
            or diagnostic_index != expected_index
            or event != expected_checkpoint
        ):
            _fail("CHECKPOINT_RECORD_START_INVALID", "$.progress")
        active_id = expected_record
        active_index = expected_index
        active_events = [event]
    else:
        checked_active_index = _strict_int(
            active_index, "$.previous.active_record_diagnostic_index"
        )
        if checked_active_index != expected_index:
            _fail("ACTIVE_RECORD_INDEX_INVALID", "$.progress")
        if len(active_events) >= len(protocol.DIAGNOSTIC_CHECKPOINTS):
            _fail("ACTIVE_RECORD_PLAN_ALREADY_COMPLETE", "$.progress")
        expected_checkpoint = protocol.DIAGNOSTIC_CHECKPOINTS[len(active_events)]
        if (
            record_id != active_id
            or diagnostic_index != checked_active_index
            or event != expected_checkpoint
        ):
            _fail("CHECKPOINT_SEQUENCE_INVALID", "$.progress")
        active_events.append(event)
    checkpoint_count += 1
    checked_case_result: dict[str, Any] | None = None
    if event == "case_result_build_completed":
        if case_result is None:
            _fail("CASE_RESULT_REQUIRED", "$.progress.case_result")
        assert diagnostic_index is not None
        checked_case_result = _validated_case_summary(
            case_result, diagnostic_index, "$.progress.case_result"
        )
        payload = artifact_json_bytes(checked_case_result)
        if len(payload) > 64 * 1024:
            _fail("CASE_RESULT_INVALID", "$.progress.case_result")
    elif case_result is not None:
        _fail("CASE_RESULT_EVENT_INVALID", "$.progress.case_result")
    identity = {
        "record_id": str(record_id),
        "diagnostic_index": diagnostic_index,
        "event": event,
    }
    last_started = (
        identity
        if event.endswith("_started")
        else previous.get("last_started_checkpoint")
    )
    last_completed = (
        identity
        if event.endswith("_completed")
        else previous.get("last_completed_checkpoint")
    )
    if len(active_events) == len(protocol.DIAGNOSTIC_CHECKPOINTS):
        completed.append(str(active_id))
        active_id = None
        active_index = None
        active_events = []
        last_started = None
        last_completed = None
    return _state_object(
        event=event,
        record_id=record_id,
        diagnostic_index=diagnostic_index,
        session_events=session_events,
        completed=completed,
        active_record_id=(None if active_id is None else str(active_id)),
        active_index=(
            None if active_index is None else _strict_int(active_index, "$.active")
        ),
        active_events=active_events,
        checkpoint_count=checkpoint_count,
        last_started=_mapping_copy_or_none(last_started, "$.last_started"),
        last_completed=_mapping_copy_or_none(last_completed, "$.last_completed"),
        environment=_mapping_copy_or_none(environment, "$.environment"),
        resources=None,
        terminal=None,
        case_result=checked_case_result,
    )


def _state_object(
    *,
    event: str,
    record_id: str | None,
    diagnostic_index: int | None,
    session_events: Sequence[str],
    completed: Sequence[str],
    active_record_id: str | None,
    active_index: int | None,
    active_events: Sequence[str],
    checkpoint_count: int,
    last_started: Mapping[str, Any] | None,
    last_completed: Mapping[str, Any] | None,
    environment: Mapping[str, Any] | None,
    resources: Mapping[str, Any] | None,
    terminal: Mapping[str, Any] | None,
    case_result: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "event": event,
        "record_id": record_id,
        "diagnostic_index": diagnostic_index,
        "session_lifecycle_events": list(session_events),
        "completed_record_ids": list(completed),
        "active_record_id": active_record_id,
        "active_record_diagnostic_index": active_index,
        "active_record_events": list(active_events),
        "durable_substage_event_count": checkpoint_count,
        "last_started_checkpoint": (
            None if last_started is None else dict(last_started)
        ),
        "last_completed_checkpoint": (
            None if last_completed is None else dict(last_completed)
        ),
        "observed_environment": (None if environment is None else dict(environment)),
        "resources": None if resources is None else dict(resources),
        "terminal": None if terminal is None else dict(terminal),
        "case_result": None if case_result is None else dict(case_result),
    }


def _derive_failure_scope(previous: Mapping[str, Any]) -> str:
    session_events = _string_sequence(
        previous.get("session_lifecycle_events"), "$.progress.session_lifecycle_events"
    )
    completed = _string_sequence(
        previous.get("completed_record_ids"), "$.progress.completed_record_ids"
    )
    active_id = previous.get("active_record_id")
    active_events = _string_sequence(
        previous.get("active_record_events"), "$.progress.active_record_events"
    )
    count = _strict_int(
        previous.get("durable_substage_event_count"),
        "$.progress.durable_substage_event_count",
    )
    if not completed and active_id is None and not active_events and count == 0:
        if not session_events:
            _fail("PRE_RECORD_FAILURE_STATE_INVALID", "$.progress")
        return "pre_record_lifecycle"
    if active_id is not None:
        if not active_events or len(active_events) >= len(
            protocol.DIAGNOSTIC_CHECKPOINTS
        ):
            _fail("ACTIVE_FAILURE_PREFIX_INVALID", "$.progress")
        return "active_record_substage"
    if completed == list(protocol.DIAGNOSTIC_CASE_ORDER):
        if count != protocol.FULL_SUCCESS_DURABLE_SUBSTAGE_EVENT_COUNT:
            _fail("POST_RECORD_FAILURE_COUNT_INVALID", "$.progress")
        return "post_record_terminalization"
    if completed != list(protocol.DIAGNOSTIC_CASE_ORDER[: len(completed)]):
        _fail("INTER_RECORD_COMPLETED_PREFIX_INVALID", "$.progress")
    return "inter_record_transition"


def _validated_terminal_context(
    *,
    implementation_freeze_commit: str,
    preregistration_payload: bytes,
    attempt_owner_payload: bytes,
    progress_payload: bytes,
    implementation_context: Mapping[str, Any],
    expected_terminal: str,
) -> dict[str, Any]:
    _validate_commit(implementation_freeze_commit, "$.implementation_freeze_commit")
    _validated_preregistration_payload(preregistration_payload)
    owner = _validated_owner_payload(
        attempt_owner_payload,
        implementation_freeze_commit=implementation_freeze_commit,
        preregistration_payload=preregistration_payload,
    )
    events = validate_progress_journal(
        progress_payload,
        implementation_freeze_commit=implementation_freeze_commit,
        preregistration_payload=preregistration_payload,
        attempt_owner_payload=attempt_owner_payload,
    )
    terminal = events[-1]
    if terminal.get("event") != expected_terminal:
        _fail("TERMINAL_KIND_MISMATCH", "$.progress")
    checked_implementation = _validated_implementation_context(
        implementation_context, implementation_freeze_commit
    )
    execution_authority = copy.deepcopy(owner["execution_authority"])
    return {
        "events": events,
        "terminal": terminal,
        "protocol_lineage": {
            "protocol_merge_commit": PROTOCOL_MERGE_COMMIT,
            "preregistration": _receipt(
                protocol.PREREGISTRATION_PATH, preregistration_payload
            ),
            "all_thirteen_protocol_sources_match_merge_blobs": True,
        },
        "implementation_lineage": checked_implementation,
        "execution_authority_lineage": execution_authority,
        "artifacts": {
            "attempt_owner": _receipt(
                protocol.ATTEMPT_OWNER_PATH, attempt_owner_payload
            ),
            "progress": _receipt(protocol.PROGRESS_PATH, progress_payload),
        },
    }


def _validated_cases_from_events(
    events: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    cases = [
        _mapping(item.get("case_result"), "$.progress.case_result")
        for item in events
        if item.get("event") == "case_result_build_completed"
    ]
    if len(cases) != len(protocol.DIAGNOSTIC_CASE_ORDER):
        _fail("DIAGNOSTIC_CASE_COUNT_INVALID", "$.record_results")
    rebuilt: list[dict[str, Any]] = []
    for index, (record_id, raw_summary) in enumerate(
        zip(protocol.DIAGNOSTIC_CASE_ORDER, cases, strict=True)
    ):
        summary = _validated_case_summary(
            raw_summary, index, f"$.record_results[{index}]"
        )
        if summary["record_id"] != record_id:
            _fail("DIAGNOSTIC_CASE_MISMATCH", f"$.record_results[{index}]")
        rebuilt.append(summary)
    return rebuilt


def _validated_implementation_context(
    value: Mapping[str, Any], implementation_freeze_commit: str
) -> dict[str, Any]:
    observed = _mapping(value, "$.implementation_context")
    bindings = _mapping(observed.get("source_bindings"), "$.implementation_context")
    if set(bindings) != set(IMPLEMENTATION_SOURCE_PATHS):
        _fail("IMPLEMENTATION_SOURCE_SET_MISMATCH", "$.implementation_context")
    normalized: dict[str, dict[str, Any]] = {}
    for name, path in sorted(IMPLEMENTATION_SOURCE_PATHS.items()):
        item = _mapping(bindings.get(name), f"$.implementation_context.{name}")
        expected: dict[str, Any] = {
            "path": path,
            "bytes": _strict_int(item.get("bytes"), f"$.implementation_context.{name}"),
            "sha256": str(item.get("sha256")),
            "tracked_bytes_equal_implementation_freeze_commit_blob": True,
        }
        if (
            item.get("path") != path
            or expected["bytes"] <= 0
            or re.fullmatch(r"sha256:[0-9a-f]{64}", expected["sha256"]) is None
            or not _json_equal(item, expected)
        ):
            _fail(
                "IMPLEMENTATION_SOURCE_BINDING_INVALID",
                f"$.implementation_context.{name}",
            )
        normalized[name] = expected
    expected_context = {
        "freeze_commit": implementation_freeze_commit,
        "source_bindings": normalized,
        "three_sources_share_first_parent_introduction_commit": True,
        "exact_reviewed_slice_delta": True,
    }
    if not _json_equal(observed, expected_context):
        _fail("IMPLEMENTATION_CONTEXT_MISMATCH", "$.implementation_context")
    return expected_context


def _validated_owner_payload(
    payload: bytes,
    *,
    implementation_freeze_commit: str,
    preregistration_payload: bytes,
) -> dict[str, Any]:
    owner = parse_strict_json_bytes(payload, location="$.attempt_owner")
    if artifact_json_bytes(owner) != payload:
        _fail("ATTEMPT_OWNER_NOT_CANONICAL", "$.attempt_owner")
    return validate_attempt_owner(
        owner,
        implementation_freeze_commit=implementation_freeze_commit,
        preregistration_payload=preregistration_payload,
    )


def _validated_preregistration_payload(payload: bytes) -> dict[str, Any]:
    if type(payload) is not bytes or len(payload) != PROTOCOL_BYTES:
        _fail("PREREGISTRATION_BYTES_MISMATCH", "$.preregistration")
    if sha256_bytes(payload) != PROTOCOL_SHA256:
        _fail("PREREGISTRATION_SHA256_MISMATCH", "$.preregistration")
    value = parse_strict_json_bytes(payload, location="$.preregistration")
    if artifact_json_bytes(value) != payload:
        _fail("PREREGISTRATION_NOT_CANONICAL", "$.preregistration")
    if (
        value.get("gate_id") != protocol.GATE_ID
        or value.get("next_gate") != GATE_ID
        or value.get("runtime_eligible") is not False
    ):
        _fail("PREREGISTRATION_GATE_MISMATCH", "$.preregistration")
    return value


def _validated_execution_authority_payload(
    payload: bytes, *, implementation_freeze_commit: str
) -> dict[str, Any]:
    if type(payload) is not bytes or not payload or len(payload) > 64 * 1024:
        _fail("EXECUTION_AUTHORITY_BYTES_INVALID", "$.execution_authority")
    value = parse_strict_json_bytes(payload, location="$.execution_authority")
    if artifact_json_bytes(value) != payload:
        _fail("EXECUTION_AUTHORITY_NOT_CANONICAL", "$.execution_authority")
    preflight = _mapping(
        value.get("resource_preflight"), "$.execution_authority.resource_preflight"
    )
    dependency_receipts = _mapping(
        value.get("critical_execution_dependency_receipts"),
        "$.execution_authority.critical_execution_dependency_receipts",
    )
    expected = build_execution_authority_contract(
        implementation_freeze_commit=implementation_freeze_commit,
        expected_environment=_mapping(
            preflight.get("expected_environment"),
            "$.execution_authority.resource_preflight.expected_environment",
        ),
        critical_execution_dependency_receipts=dependency_receipts,
    )
    if not _json_equal(value, expected):
        _fail("EXECUTION_AUTHORITY_MISMATCH", "$.execution_authority")
    return expected


def _validated_critical_execution_dependency_receipts(
    value: object,
) -> dict[str, dict[str, Any]]:
    observed = _mapping(value, "$.critical_execution_dependency_receipts")
    if set(observed) != set(CRITICAL_EXECUTION_DEPENDENCY_SOURCE_PATHS):
        _fail(
            "CRITICAL_EXECUTION_DEPENDENCY_SOURCE_FIELDS",
            "$.critical_execution_dependency_receipts",
        )
    normalized: dict[str, dict[str, Any]] = {}
    for name, path in sorted(CRITICAL_EXECUTION_DEPENDENCY_SOURCE_PATHS.items()):
        item = _mapping(
            observed.get(name),
            f"$.critical_execution_dependency_receipts.{name}",
        )
        if set(item) != {"path", "bytes", "sha256"}:
            _fail(
                "CRITICAL_EXECUTION_DEPENDENCY_RECEIPT_FIELDS",
                f"$.critical_execution_dependency_receipts.{name}",
            )
        size = _strict_int(
            item.get("bytes"),
            f"$.critical_execution_dependency_receipts.{name}.bytes",
        )
        expected = {
            "path": path,
            "bytes": size,
            "sha256": _sha256_text(
                item.get("sha256"),
                f"$.critical_execution_dependency_receipts.{name}.sha256",
            ),
        }
        if size <= 0 or size > 64 * 1024 * 1024 or not _json_equal(item, expected):
            _fail(
                "CRITICAL_EXECUTION_DEPENDENCY_RECEIPT_INVALID",
                f"$.critical_execution_dependency_receipts.{name}",
            )
        normalized[name] = expected
    return normalized


def _validated_environment(value: object) -> dict[str, Any]:
    observed = _mapping(value, "$.observed_environment")
    required = set(protocol.OBSERVED_ENVIRONMENT_FIELDS)
    if set(observed) != required:
        _fail("OBSERVED_ENVIRONMENT_FIELDS", "$.observed_environment")
    normalized: dict[str, Any] = {}
    for name in sorted(observed):
        item = observed[name]
        if name == "gpu_vram_bytes":
            checked = _strict_int(item, f"$.observed_environment.{name}")
            if checked <= 0:
                _fail("OBSERVED_ENVIRONMENT_VALUE", f"$.observed_environment.{name}")
            normalized[name] = checked
        elif (
            type(item) is not str
            or not item
            or len(item) > 256
            or any(
                ord(character) < 0x20 or ord(character) == 0x7F for character in item
            )
        ):
            _fail("OBSERVED_ENVIRONMENT_VALUE", f"$.observed_environment.{name}")
        else:
            normalized[name] = item
    return normalized


def _validated_resources(value: object) -> dict[str, float | int]:
    observed = _mapping(value, "$.resources")
    if set(observed) != set(v2.RESOURCE_CAPS):
        _fail("RESOURCE_FIELDS", "$.resources")
    elapsed = observed.get("elapsed_seconds")
    if type(elapsed) is not float or not (
        0.0 <= elapsed <= v2.RESOURCE_CAPS["elapsed_seconds"]
    ):
        _fail("RESOURCE_VALUE", "$.resources.elapsed_seconds")
    checked: dict[str, float | int] = {"elapsed_seconds": elapsed}
    for name in ("peak_gpu_allocated_bytes", "peak_gpu_reserved_bytes"):
        item = _strict_int(observed.get(name), f"$.resources.{name}")
        if item < 0 or item > v2.RESOURCE_CAPS[name]:
            _fail("RESOURCE_VALUE", f"$.resources.{name}")
        checked[name] = item
    return checked


def _checkpoint_summary(terminal: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "session_lifecycle_events": list(terminal["session_lifecycle_events"]),
        "completed_record_ids": list(terminal["completed_record_ids"]),
        "active_record_id": terminal["active_record_id"],
        "active_record_diagnostic_index": terminal["active_record_diagnostic_index"],
        "active_record_events": list(terminal["active_record_events"]),
        "durable_substage_event_count": terminal["durable_substage_event_count"],
        "last_started_checkpoint": copy.deepcopy(terminal["last_started_checkpoint"]),
        "last_completed_checkpoint": copy.deepcopy(
            terminal["last_completed_checkpoint"]
        ),
        "terminal_event": terminal["event"],
        "checkpoint_interval_is_causal_origin": False,
    }


def _negative_claims() -> dict[str, bool]:
    return {
        "diagnostic_attempt_consumed": False,
        "diagnostic_executed": False,
        "all_registered_diagnostic_calls_completed": False,
        "diagnostic_completed_without_observed_runtime_failure": False,
        "diagnostic_failure_observed_between_durable_checkpoints": False,
        "historical_runtime_health_established": False,
        "failed_runtime_substage_isolated": False,
        "runtime_root_cause_established": False,
        "remediation_delta_established": False,
        "recovery_v3_justified": False,
        "formal_measurement_complete": False,
        "model_evaluated": False,
        "quality_established": False,
        "safety_established": False,
        "evaluation_repeatability_established": False,
        "resource_repeatability_established": False,
        "cross_machine_reproducibility_established": False,
        "serving_eligible": False,
        "promotion_eligible": False,
        "runtime_eligible": False,
    }


def _limitations() -> dict[str, bool]:
    return {
        "checkpoint_interval_proves_async_error_origin": False,
        "historical_runtime_health_established": False,
        "causal_root_cause_established": False,
        "remediation_or_recovery_selected": False,
        "quality_or_repeatability_established": False,
        "live_browser_or_network_used": False,
        "real_content_captured": False,
        "runtime_eligibility": False,
    }


def _result_review_action() -> dict[str, Any]:
    return {
        "next_gate_id": RESULT_REVIEW_GATE_ID,
        "action": "review_authenticated_diagnostic_terminal_without_auto_recovery",
        "automatic_recovery_authorized": False,
        "recovery_v3_authorized": False,
        "v2_retry_authorized": False,
        "runtime_eligible": False,
    }


def _receipt(path: str, payload: bytes) -> dict[str, Any]:
    if type(payload) is not bytes:
        _fail("RECEIPT_PAYLOAD_BYTES_REQUIRED", f"$.receipt.{path}")
    return {"path": path, "bytes": len(payload), "sha256": sha256_bytes(payload)}


def _byte_receipt(payload: bytes) -> dict[str, Any]:
    if type(payload) is not bytes:
        _fail("BYTE_RECEIPT_PAYLOAD_REQUIRED", "$.receipt")
    return {"bytes": len(payload), "sha256": sha256_bytes(payload)}


def _closed_byte_receipt(value: object, location: str) -> dict[str, Any]:
    observed = _mapping(value, location)
    if set(observed) != {"bytes", "sha256"}:
        _fail("BYTE_RECEIPT_FIELDS", location)
    size = _strict_int(observed.get("bytes"), f"{location}.bytes")
    digest = _sha256_text(observed.get("sha256"), f"{location}.sha256")
    if size < 0 or size > 64 * 1024:
        _fail("BYTE_RECEIPT_SIZE", location)
    return {"bytes": size, "sha256": digest}


def _closed_discarded_tail(
    value: Mapping[str, Any] | None, location: str
) -> dict[str, Any] | None:
    if value is None:
        return None
    observed = _mapping(value, location)
    if set(observed) != {
        "bytes",
        "sha256",
        "authenticated_event",
        "execution_fact_claimed",
    }:
        _fail("DISCARDED_TAIL_FIELDS", location)
    size = _strict_int(observed.get("bytes"), f"{location}.bytes")
    expected = {
        "bytes": size,
        "sha256": _sha256_text(observed.get("sha256"), f"{location}.sha256"),
        "authenticated_event": False,
        "execution_fact_claimed": False,
    }
    if size <= 0 or size > 1_048_576 or not _json_equal(observed, expected):
        _fail("DISCARDED_TAIL_INVALID", location)
    return expected


def _sha256_text(value: object, location: str) -> str:
    if type(value) is not str or re.fullmatch(r"sha256:[0-9a-f]{64}", value) is None:
        _fail("SHA256_INVALID", location)
    return value


def _sha256_sequence(value: object, location: str) -> list[str]:
    items = _string_sequence(value, location)
    return [
        _sha256_text(item, f"{location}[{index}]") for index, item in enumerate(items)
    ]


def _safe_exception_type(value: object, location: str) -> str:
    if type(value) is not str or SAFE_EXCEPTION_TYPE_PATTERN.fullmatch(value) is None:
        _fail("EXCEPTION_TYPE_UNSAFE", location)
    return value


def _validate_commit(value: str, location: str) -> None:
    if type(value) is not str or COMMIT_PATTERN.fullmatch(value) is None:
        _fail("GIT_COMMIT_INVALID", location)


def _validate_timestamp(value: object) -> None:
    if type(value) is not str or not value or len(value) > 64:
        _fail("TIMESTAMP_INVALID", "$.captured_at_utc")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise MM005GenerationFailureDiagnosticResultError(
            "TIMESTAMP_INVALID", "$.captured_at_utc"
        ) from exc
    offset = parsed.utcoffset()
    if parsed.tzinfo is None or offset is None:
        _fail("TIMESTAMP_TIMEZONE_REQUIRED", "$.captured_at_utc")
    if offset.total_seconds() != 0:
        _fail("TIMESTAMP_UTC_REQUIRED", "$.captured_at_utc")


def _mapping(value: object, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail("OBJECT_REQUIRED", location)
    return value


def _mapping_or_none(value: object, location: str) -> Mapping[str, Any] | None:
    if value is None:
        return None
    return _mapping(value, location)


def _mapping_copy_or_none(value: object, location: str) -> dict[str, Any] | None:
    if value is None:
        return None
    return dict(_mapping(value, location))


def _object_sequence(value: object, location: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        _fail("OBJECT_SEQUENCE_REQUIRED", location)
    return [_mapping(item, f"{location}[{index}]") for index, item in enumerate(value)]


def _string_sequence(value: object, location: str) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        _fail("STRING_SEQUENCE_REQUIRED", location)
    if any(type(item) is not str for item in value):
        _fail("STRING_SEQUENCE_REQUIRED", location)
    return list(value)


def _strict_int(value: object, location: str) -> int:
    if type(value) is not int:
        _fail("INTEGER_REQUIRED", location)
    return value


def _strict_number(value: object, location: str) -> float | int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _fail("NUMBER_REQUIRED", location)
    try:
        finite = math.isfinite(value)
    except OverflowError:
        _fail("FINITE_NUMBER_REQUIRED", location)
    if not finite:
        _fail("FINITE_NUMBER_REQUIRED", location)
    return value


def _json_equal(left: object, right: object) -> bool:
    try:
        return artifact_json_bytes(left) == artifact_json_bytes(right)
    except (TypeError, ValueError):
        return False


def _fail(code: str, location: str = "$") -> NoReturn:
    raise MM005GenerationFailureDiagnosticResultError(code, location)


__all__ = [
    "ATTEMPT_OWNER_VERSION",
    "EXECUTION_AUTHORITY_GATE_ID",
    "EXECUTION_AUTHORITY_PATH",
    "EXECUTION_AUTHORITY_SLICE_PATHS",
    "EXECUTION_AUTHORITY_VERSION",
    "CRITICAL_EXECUTION_DEPENDENCY_SOURCE_PATHS",
    "EXECUTION_GATE_ID",
    "FAILURE_REQUIRED_TOP_LEVEL_KEYS",
    "FAILURE_SCOPES",
    "FAILURE_VERSION",
    "FORMAL_RESULT_GATES",
    "GATE_ID",
    "IMPLEMENTATION_SOURCE_PATHS",
    "MM005GenerationFailureDiagnosticResultError",
    "OUTCOME_PRECEDENCE",
    "PROGRESS_VERSION",
    "PROTOCOL_BYTES",
    "PROTOCOL_MERGE_COMMIT",
    "PROTOCOL_SHA256",
    "RESULT_REQUIRED_TOP_LEVEL_KEYS",
    "RESULT_REVIEW_GATE_ID",
    "RESULT_VERSION",
    "artifact_json_bytes",
    "build_attempt_owner",
    "build_case_result_summary",
    "build_diagnostic_failure",
    "build_diagnostic_result",
    "build_execution_authority_contract",
    "build_progress_event",
    "execution_plan",
    "failure_scope_for_journal",
    "parse_strict_json_bytes",
    "recover_progress_prefix",
    "result_contract",
    "select_outcome",
    "sha256_bytes",
    "validate_attempt_owner",
    "validate_diagnostic_failure",
    "validate_diagnostic_result",
    "validate_progress_journal",
]
