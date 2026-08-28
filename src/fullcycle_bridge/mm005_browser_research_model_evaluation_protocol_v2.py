"""Closed recovery protocol for MM-005 Browser Research model evaluation v2.

The v2 protocol preserves every scientific variable from v1.  It changes only
the registered experiment/output identity, source closure, long-path-safe Git
blob reader, and crash-consistent progress/terminal lifecycle authorized by the
tracked v1 failure classification.
"""

from __future__ import annotations

import copy
import math
import re
from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any, NoReturn, cast

from . import mm005_browser_research_model_evaluation as v1
from . import mm005_browser_research_model_evaluation_failure_classification as failure

PROTOCOL_VERSION = 2
ATTEMPT_OWNER_VERSION = 2
PROGRESS_VERSION = 1
CANDIDATE_VERSION = v1.CANDIDATE_VERSION
PREDICTIONS_VERSION = v1.PREDICTIONS_VERSION
EVIDENCE_VERSION = 2
FAILURE_VERSION = 2

PROTOCOL_GATE_ID = failure.NEXT_GATE_ID
EXECUTION_GATE_ID = failure.RECOVERY_EXECUTION_GATE_ID
FAILURE_CLASSIFICATION_GATE_ID = failure.RECOVERY_FAILURE_CLASSIFICATION_GATE_ID
RESULT_REVIEW_GATE_ID = failure.RECOVERY_RESULT_REVIEW_GATE_ID
EXPERIMENT_ID = failure.RECOVERY_EXPERIMENT_ID
RUN_ID = failure.RECOVERY_RUN_ID
SUITE_ID = v1.SUITE_ID

PREREGISTRATION_PATH = (
    "configs/mm005_browser_research_model_evaluation_protocol_v2.json"
)
RUN_OUTPUT_ROOT = failure.RECOVERY_OUTPUT_DIRECTORY
ATTEMPT_OWNER_PATH = f"{RUN_OUTPUT_ROOT}/attempt-owner.json"
PROGRESS_PATH = f"{RUN_OUTPUT_ROOT}/progress.json"
LIFECYCLE_LEASE_ROOT = f"{RUN_OUTPUT_ROOT}.lifecycle"
LIFECYCLE_LEASE_PATH = f"{LIFECYCLE_LEASE_ROOT}/lease"
LIFECYCLE_LEASE_MARKER = (
    b"MM-005-browser-research-model-evaluation-recovery-lifecycle-v1\n"
)
EVALUATION_CANDIDATE_PATH = f"{RUN_OUTPUT_ROOT}/evaluation-candidate.json"
PREDICTIONS_PATH = f"{RUN_OUTPUT_ROOT}/predictions.json"
EVIDENCE_PATH = f"{RUN_OUTPUT_ROOT}/evidence.json"
FAILURE_PATH = f"{RUN_OUTPUT_ROOT}/failure.json"

CLASSIFICATION_MERGE_COMMIT = "28211e62d907c16a6d2208bca20f139ee7e31f5f"
V1_PROTOCOL_FREEZE_COMMIT = failure.PROTOCOL_FREEZE_COMMIT
V1_PREREGISTRATION_RECEIPT = {
    "path": v1.PREREGISTRATION_PATH,
    "bytes": failure.PREREGISTRATION_BYTES,
    "sha256": failure.PREREGISTRATION_SHA256,
}
V1_ATTEMPT_OWNER_RECEIPT = {
    "path": failure.TRACKED_ATTEMPT_OWNER_PATH,
    "bytes": failure.ATTEMPT_OWNER_BYTES,
    "sha256": failure.ATTEMPT_OWNER_SHA256,
}
V1_FAILURE_CLASSIFICATION_RECEIPT = {
    "path": failure.ARTIFACT_PATH,
    "bytes": 11_936,
    "sha256": (
        "sha256:628f9a24267c292d318ca279eb0642c72fbc705b1211629ef8b9edf6318e6e11"
    ),
    "report_digest": (
        "sha256:8768a18c0aecc1da4bc693130b023b4949f5059b0eac6eabae6cbede6cae4d2a"
    ),
}

MODEL_SNAPSHOT_ROOT = v1.MODEL_SNAPSHOT_ROOT
ADAPTER_ROOT = v1.ADAPTER_ROOT
ADAPTER_LFS_PATH = v1.ADAPTER_LFS_PATH
FORMAL_PYTHON_PATH = v1.FORMAL_PYTHON_PATH
FORMAL_PYTHON_ARGS = list(v1.FORMAL_PYTHON_ARGS)
MODEL_ID = v1.MODEL_ID
MODEL_REVISION = v1.MODEL_REVISION
ADAPTER_MODEL_ID = v1.ADAPTER_MODEL_ID
ADAPTER_RECEIPTS = v1.ADAPTER_RECEIPTS
SEED = v1.SEED
EXPECTED_RECORDS = v1.EXPECTED_RECORDS
EXPECTED_SOURCE_BINDINGS = v1.EXPECTED_SOURCE_BINDINGS
MAX_NEW_TOKENS = v1.MAX_NEW_TOKENS
RESOURCE_CAPS = dict(v1.RESOURCE_CAPS)

PROTOCOL_SOURCE_PATHS = {
    **v1.PROTOCOL_SOURCE_PATHS,
    "model_evaluation_failure_classification_contract": (
        "src/fullcycle_bridge/"
        "mm005_browser_research_model_evaluation_failure_classification.py"
    ),
    "model_evaluation_recovery_builder": (
        "scripts/prepare_mm005_browser_research_model_evaluation_v2.py"
    ),
    "model_evaluation_recovery_contract": (
        "src/fullcycle_bridge/mm005_browser_research_model_evaluation_protocol_v2.py"
    ),
    "model_evaluation_recovery_io": (
        "src/fullcycle_bridge/mm005_browser_research_model_evaluation_recovery_io.py"
    ),
    "model_evaluation_recovery_runner": (
        "scripts/run_mm005_browser_research_model_evaluation_v2.py"
    ),
    "model_evaluation_recovery_terminalizer": (
        "scripts/recover_mm005_browser_research_model_evaluation_v2.py"
    ),
}
V1_PROTOCOL_SOURCE_KEYS = tuple(sorted(v1.PROTOCOL_SOURCE_PATHS))
V2_PROTOCOL_SOURCE_KEYS = tuple(
    sorted(set(PROTOCOL_SOURCE_PATHS).difference(V1_PROTOCOL_SOURCE_KEYS))
)

PRESERVED_V1_SUBTREES = (
    "decision",
    "candidate",
    "input_suite",
    "prompt_contract",
    "compiler",
    "verifier",
    "metrics",
    "execution_protocol",
    "resource_caps",
    "authority_contract",
    "freeze_preconditions",
    "claims",
)
FORMAL_GATE_ADDITIONS = (
    "long_path_safe_freeze_blob_read",
    "durable_progress_persistence",
    "interruption_terminal_recovery",
)
REQUIRED_GATES = (*v1.REQUIRED_GATES, *FORMAL_GATE_ADDITIONS)
FAILURE_STAGES = (*v1.FAILURE_STAGES, "external_interruption_recovery")

PROGRESS_EVENTS = (
    "attempt_claimed",
    "context_preflight_completed",
    "base_load_started",
    "base_load_completed",
    "adapter_load_started",
    "adapter_load_completed",
    "generation_started",
    "generation_completed",
    "model_evaluation_completed",
    "candidate_persisted",
    "predictions_persisted",
    "success_terminal_ready",
    "failure_terminal_ready",
)
TERMINAL_EVENTS = ("success_terminal_ready", "failure_terminal_ready")

FREEZE_BLOB_READER = {
    "command": "git cat-file blob <commit>:<path>",
    "depends_on_core_longpaths": False,
    "git_show_path_read_used": False,
    "stderr_or_absolute_path_persisted": False,
}

DURABLE_RECOVERY_CONTRACT = {
    "progress_version": PROGRESS_VERSION,
    "path": PROGRESS_PATH,
    "format": "canonical_jsonl_append_only_sha256_chain",
    "first_checkpoint_committed_with_owner_claim": True,
    "single_writer_exclusive_lock_held_during_execution": True,
    "lifecycle_lease_path": LIFECYCLE_LEASE_PATH,
    "lifecycle_lease_acquired_before_attempt_claim": True,
    "base_adapter_and_generation_attempt_completion_checkpoints": True,
    "per_record_generation_attempt_and_completion_checkpoints": True,
    "checkpoint_flush_and_fsync_required": True,
    "partial_progress_tail_recovery": (
        "hash_record_then_truncate_to_last_authenticated_event"
    ),
    "terminal_protocol": "terminal_ready_checkpoint_then_exact_terminal_artifact",
    "partial_terminal_repair": "exact_expected_canonical_prefix_only",
    "recovery_requires_exact_attempt_id": True,
    "recovery_requires_executor_lock_released": True,
    "recovery_imports_or_calls_model": False,
    "recovery_uses_network": False,
    "recovery_retries_v1_or_v2_model_execution": False,
    "progress_claim_scope": "durable_checkpoint_facts_not_uncheckpointed_work",
    "success_and_failure_are_mutually_exclusive": True,
}

ALLOWED_VALUE_REPLACEMENTS: dict[tuple[str, ...], Any] = {
    ("mm005_browser_research_model_evaluation_protocol_version",): PROTOCOL_VERSION,
    ("gate_id",): PROTOCOL_GATE_ID,
    ("experiment_id",): EXPERIMENT_ID,
    ("outputs", "output_directory"): RUN_OUTPUT_ROOT,
    ("outputs", "attempt_owner"): ATTEMPT_OWNER_PATH,
    ("outputs", "evaluation_candidate"): EVALUATION_CANDIDATE_PATH,
    ("outputs", "predictions"): PREDICTIONS_PATH,
    ("outputs", "evidence"): EVIDENCE_PATH,
    ("outputs", "failure"): FAILURE_PATH,
    ("failure_receipt_contract", "stages"): list(FAILURE_STAGES),
    ("failure_receipt_contract", "next_gate"): FAILURE_CLASSIFICATION_GATE_ID,
    ("formal_gate", "required_gates"): list(REQUIRED_GATES),
    ("next_gate",): EXECUTION_GATE_ID,
}


class MM005BrowserResearchRecoveryError(ValueError):
    """Stable fail-closed error for recovery-protocol drift."""

    def __init__(self, code: str, location: str = "$") -> None:
        self.code = code
        self.location = location
        super().__init__(f"{code} at {location}")


def artifact_json_bytes(value: object) -> bytes:
    return cast(bytes, v1.artifact_json_bytes(value))


def sha256_bytes(payload: bytes) -> str:
    return cast(str, v1.sha256_bytes(payload))


def parse_strict_json_bytes(payload: bytes, *, location: str) -> dict[str, Any]:
    try:
        return cast(
            dict[str, Any], v1.parse_strict_json_bytes(payload, location=location)
        )
    except v1.MM005ModelEvaluationError as exc:
        raise MM005BrowserResearchRecoveryError(exc.code, exc.location) from exc


def expected_recovery_lineage(
    *,
    v1_preregistration_payload: bytes,
    v1_attempt_owner_payload: bytes,
    v1_failure_classification_payload: bytes,
) -> dict[str, Any]:
    parsed = validate_recovery_lineage_payloads(
        v1_preregistration_payload=v1_preregistration_payload,
        v1_attempt_owner_payload=v1_attempt_owner_payload,
        v1_failure_classification_payload=v1_failure_classification_payload,
    )
    classification = parsed["v1_failure_classification"]
    return {
        "classification_merge_commit": CLASSIFICATION_MERGE_COMMIT,
        "v1_protocol_freeze_commit": V1_PROTOCOL_FREEZE_COMMIT,
        "v1_preregistration": dict(V1_PREREGISTRATION_RECEIPT),
        "v1_attempt_owner": dict(V1_ATTEMPT_OWNER_RECEIPT),
        "v1_failure_classification": {
            "path": V1_FAILURE_CLASSIFICATION_RECEIPT["path"],
            "bytes": V1_FAILURE_CLASSIFICATION_RECEIPT["bytes"],
            "sha256": V1_FAILURE_CLASSIFICATION_RECEIPT["sha256"],
            "report_digest": classification["report_digest"],
        },
        "v1_owner_only_attempt_preserved_read_only": True,
        "v1_retry_authorized": False,
        "v2_is_new_experiment": True,
    }


def validate_recovery_lineage_payloads(
    *,
    v1_preregistration_payload: bytes,
    v1_attempt_owner_payload: bytes,
    v1_failure_classification_payload: bytes,
) -> dict[str, dict[str, Any]]:
    payloads = {
        "v1_preregistration": (
            v1_preregistration_payload,
            V1_PREREGISTRATION_RECEIPT,
        ),
        "v1_attempt_owner": (
            v1_attempt_owner_payload,
            V1_ATTEMPT_OWNER_RECEIPT,
        ),
        "v1_failure_classification": (
            v1_failure_classification_payload,
            V1_FAILURE_CLASSIFICATION_RECEIPT,
        ),
    }
    parsed: dict[str, dict[str, Any]] = {}
    for name, (payload, expected_receipt) in payloads.items():
        if (
            len(payload) != expected_receipt["bytes"]
            or sha256_bytes(payload) != expected_receipt["sha256"]
        ):
            _fail("RECOVERY_LINEAGE_RECEIPT_MISMATCH", f"$.{name}")
        value = parse_strict_json_bytes(payload, location=f"$.{name}")
        if artifact_json_bytes(value) != payload:
            _fail("RECOVERY_LINEAGE_NOT_CANONICAL", f"$.{name}")
        parsed[name] = value

    preregistration = parsed["v1_preregistration"]
    if (
        preregistration.get("mm005_browser_research_model_evaluation_protocol_version")
        != v1.PROTOCOL_VERSION
        or preregistration.get("gate_id") != v1.PROTOCOL_GATE_ID
        or preregistration.get("freeze_status") != "frozen"
    ):
        _fail("V1_PREREGISTRATION_BOUNDARY_MISMATCH", "$.v1_preregistration")
    owner = parsed["v1_attempt_owner"]
    if (
        owner.get("gate_id") != v1.EXECUTION_GATE_ID
        or owner.get("run_id") != v1.RUN_ID
        or _mapping(owner.get("claims"), "$.v1_attempt_owner.claims").get(
            "retry_allowed"
        )
        is not False
    ):
        _fail("V1_OWNER_BOUNDARY_MISMATCH", "$.v1_attempt_owner")
    classification = parsed["v1_failure_classification"]
    if (
        classification.get("report_digest")
        != V1_FAILURE_CLASSIFICATION_RECEIPT["report_digest"]
    ):
        _fail(
            "V1_FAILURE_CLASSIFICATION_REPORT_MISMATCH",
            "$.v1_failure_classification.report_digest",
        )
    validate_failure_classification_recovery_policy(classification)
    return parsed


def validate_failure_classification_recovery_policy(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    action = _mapping(value.get("locked_next_action"), "$.locked_next_action")
    expected_identity = {
        "gate_id": PROTOCOL_GATE_ID,
        "execution_gate_id": EXECUTION_GATE_ID,
        "failure_classification_gate_id": FAILURE_CLASSIFICATION_GATE_ID,
        "result_review_gate_id": RESULT_REVIEW_GATE_ID,
        "experiment_id": EXPERIMENT_ID,
        "run_id": RUN_ID,
        "output_directory": RUN_OUTPUT_ROOT,
        "new_experiment_not_v1_retry": True,
    }
    for key, expected in expected_identity.items():
        if not _json_equal(action.get(key), expected):
            _fail("RECOVERY_POLICY_IDENTITY_MISMATCH", f"$.locked_next_action.{key}")
    if not _json_equal(
        action.get("v1_subtrees_exactly_preserved"), list(PRESERVED_V1_SUBTREES)
    ):
        _fail(
            "RECOVERY_POLICY_PRESERVATION_MISMATCH",
            "$.locked_next_action.v1_subtrees_exactly_preserved",
        )
    required = _mapping(
        action.get("required_v2_values"), "$.locked_next_action.required_v2_values"
    )
    expected_required = {
        "mm005_browser_research_model_evaluation_protocol_version": PROTOCOL_VERSION,
        "gate_id": PROTOCOL_GATE_ID,
        "experiment_id": EXPERIMENT_ID,
        "run_id": RUN_ID,
        "next_gate": EXECUTION_GATE_ID,
        "success_next_gate": RESULT_REVIEW_GATE_ID,
        "failure_receipt_contract.next_gate": FAILURE_CLASSIFICATION_GATE_ID,
        "outputs.output_directory": RUN_OUTPUT_ROOT,
        "outputs.attempt_owner": ATTEMPT_OWNER_PATH,
        "outputs.progress": PROGRESS_PATH,
        "outputs.evaluation_candidate": EVALUATION_CANDIDATE_PATH,
        "outputs.predictions": PREDICTIONS_PATH,
        "outputs.evidence": EVIDENCE_PATH,
        "outputs.failure": FAILURE_PATH,
        "freeze_blob_reader.command": FREEZE_BLOB_READER["command"],
        "freeze_blob_reader.depends_on_core_longpaths": False,
    }
    if not _json_equal(required, expected_required):
        _fail(
            "RECOVERY_POLICY_REQUIRED_VALUES_MISMATCH",
            "$.locked_next_action.required_v2_values",
        )
    allowed = _mapping(
        action.get("allowed_v2_differences"),
        "$.locked_next_action.allowed_v2_differences",
    )
    expected_allowed = {
        "identity_and_output_path_replacements": True,
        "source_receipt_closure_for_v2_code_and_v1_lineage": True,
        "git_blob_reader_replaces_git_show_path_read": True,
        "durable_progress_checkpoint_contract": True,
        "model_free_terminal_recovery_after_external_interruption": True,
        "formal_gate_additions": list(FORMAL_GATE_ADDITIONS),
        "other_candidate_data_prompt_verifier_metric_or_resource_changes": False,
    }
    if not _json_equal(allowed, expected_allowed):
        _fail(
            "RECOVERY_POLICY_ALLOWED_DIFFERENCES_MISMATCH",
            "$.locked_next_action.allowed_v2_differences",
        )
    return {
        "preserved_subtrees": len(PRESERVED_V1_SUBTREES),
        "formal_gate_additions": len(FORMAL_GATE_ADDITIONS),
        "new_experiment_not_v1_retry": True,
    }


def expected_preregistration(
    *,
    freeze_status: str,
    v1_preregistration: Mapping[str, Any],
    source_receipts: Mapping[str, Mapping[str, Any]],
    v1_preregistration_payload: bytes,
    v1_attempt_owner_payload: bytes,
    v1_failure_classification_payload: bytes,
    output_absent: bool,
) -> dict[str, Any]:
    if freeze_status != "frozen":
        _fail("FREEZE_STATUS_INVALID", "$.freeze_status")
    if output_absent is not True:
        _fail("OUTPUT_ALREADY_EXISTS", "$.freeze_preconditions")
    base = _validated_v1_preregistration(v1_preregistration, v1_preregistration_payload)
    if set(source_receipts) != set(PROTOCOL_SOURCE_PATHS):
        _fail("INVALID_SOURCE_KEYS", "$.source_receipts")
    base_sources = _mapping(base.get("source_receipts"), "$.v1.source_receipts")
    checked_sources: dict[str, dict[str, Any]] = {}
    for name, path in sorted(PROTOCOL_SOURCE_PATHS.items()):
        observed = _closed_receipt(
            source_receipts.get(name), f"$.source_receipts.{name}"
        )
        if observed["path"] != path:
            _fail("SOURCE_PATH_MISMATCH", f"$.source_receipts.{name}.path")
        if name in V1_PROTOCOL_SOURCE_KEYS and not _json_equal(
            observed,
            _closed_receipt(base_sources.get(name), f"$.v1.source_receipts.{name}"),
        ):
            _fail("V1_SOURCE_RECEIPT_REPLACED", f"$.source_receipts.{name}")
        checked_sources[name] = observed

    recovery_lineage = expected_recovery_lineage(
        v1_preregistration_payload=v1_preregistration_payload,
        v1_attempt_owner_payload=v1_attempt_owner_payload,
        v1_failure_classification_payload=v1_failure_classification_payload,
    )
    result = copy.deepcopy(base)
    for delta_path, replacement in ALLOWED_VALUE_REPLACEMENTS.items():
        _set_path(result, delta_path, copy.deepcopy(replacement))
    result_sources = cast(dict[str, Any], result["source_receipts"])
    for name in V2_PROTOCOL_SOURCE_KEYS:
        result_sources[name] = checked_sources[name]
    source_lineage = cast(dict[str, Any], result["source_lineage"])
    source_lineage["recovery_lineage"] = recovery_lineage
    outputs = cast(dict[str, Any], result["outputs"])
    outputs["progress"] = PROGRESS_PATH
    failure_contract = cast(dict[str, Any], result["failure_receipt_contract"])
    failure_contract.update(
        {
            "progress_receipt_required": True,
            "terminal_ready_checkpoint_required": True,
            "external_recovery_model_import_or_call_allowed": False,
            "partial_terminal_repair": "exact_expected_canonical_prefix_only",
        }
    )
    result["run_id"] = RUN_ID
    result["success_next_gate"] = RESULT_REVIEW_GATE_ID
    result["freeze_blob_reader"] = copy.deepcopy(FREEZE_BLOB_READER)
    result["durable_recovery_contract"] = copy.deepcopy(DURABLE_RECOVERY_CONTRACT)
    validate_recovery_delta(
        base,
        result,
        source_receipts=checked_sources,
        recovery_lineage=recovery_lineage,
    )
    return result


def validate_preregistration(
    value: Mapping[str, Any],
    **kwargs: Any,
) -> dict[str, Any]:
    expected = expected_preregistration(freeze_status="frozen", **kwargs)
    if not _json_equal(dict(value), expected):
        _fail("PREREGISTRATION_RECOMPUTATION_MISMATCH", "$.preregistration")
    return expected


def validate_recovery_delta(
    v1_preregistration: Mapping[str, Any],
    v2_preregistration: Mapping[str, Any],
    *,
    source_receipts: Mapping[str, Mapping[str, Any]],
    recovery_lineage: Mapping[str, Any],
) -> dict[str, Any]:
    base = copy.deepcopy(dict(v1_preregistration))
    expected_new_sections: dict[tuple[str, ...], Any] = {
        ("source_lineage", "recovery_lineage"): recovery_lineage,
        ("outputs", "progress"): PROGRESS_PATH,
        ("failure_receipt_contract", "progress_receipt_required"): True,
        ("failure_receipt_contract", "terminal_ready_checkpoint_required"): True,
        (
            "failure_receipt_contract",
            "external_recovery_model_import_or_call_allowed",
        ): False,
        ("failure_receipt_contract", "partial_terminal_repair"): (
            "exact_expected_canonical_prefix_only"
        ),
        ("run_id",): RUN_ID,
        ("success_next_gate",): RESULT_REVIEW_GATE_ID,
        ("freeze_blob_reader",): FREEZE_BLOB_READER,
        ("durable_recovery_contract",): DURABLE_RECOVERY_CONTRACT,
    }
    expected_source_additions = {
        name: dict(source_receipts[name]) for name in V2_PROTOCOL_SOURCE_KEYS
    }
    observed_replacements: set[tuple[str, ...]] = set()
    observed_source_additions: set[str] = set()
    observed_new_sections: set[tuple[str, ...]] = set()

    def compare(left: Any, right: Any, path: tuple[str, ...]) -> None:
        if isinstance(left, Mapping):
            if not isinstance(right, Mapping):
                _fail("CONTAINER_REPLACEMENT", _path_label(path))
            left_mapping = cast(Mapping[str, Any], left)
            right_mapping = cast(Mapping[str, Any], right)
            for key in left_mapping:
                if key not in right_mapping:
                    _fail("V1_FIELD_REMOVED", _path_label((*path, key)))
                compare(left_mapping[key], right_mapping[key], (*path, key))
            for key in right_mapping:
                if key in left_mapping:
                    continue
                added_path = (*path, key)
                if path == ("source_receipts",):
                    if key not in expected_source_additions:
                        _fail("UNAUTHORIZED_SOURCE_ADDITION", _path_label(added_path))
                    if not _json_equal(
                        right_mapping[key], expected_source_additions[key]
                    ):
                        _fail("INVALID_SOURCE_RECEIPT", _path_label(added_path))
                    observed_source_additions.add(key)
                    continue
                if added_path not in expected_new_sections:
                    _fail("UNAUTHORIZED_FIELD_ADDITION", _path_label(added_path))
                if not _json_equal(
                    right_mapping[key], expected_new_sections[added_path]
                ):
                    _fail("RECOVERY_NEW_SECTION_MISMATCH", _path_label(added_path))
                observed_new_sections.add(added_path)
            return
        if isinstance(right, Mapping):
            _fail("CONTAINER_REPLACEMENT", _path_label(path))
        if _json_equal(left, right):
            return
        if path not in ALLOWED_VALUE_REPLACEMENTS:
            _fail("UNAUTHORIZED_VALUE_CHANGE", _path_label(path))
        if not _json_equal(right, ALLOWED_VALUE_REPLACEMENTS[path]):
            _fail("AUTHORIZED_VALUE_MISMATCH", _path_label(path))
        observed_replacements.add(path)

    compare(base, v2_preregistration, ())
    if observed_replacements != set(ALLOWED_VALUE_REPLACEMENTS):
        _fail("INCOMPLETE_RECOVERY_REPLACEMENTS", "$.recovery_delta")
    if observed_source_additions != set(V2_PROTOCOL_SOURCE_KEYS):
        _fail("INCOMPLETE_RECOVERY_SOURCE_ADDITIONS", "$.recovery_delta")
    if observed_new_sections != set(expected_new_sections):
        _fail("INCOMPLETE_RECOVERY_NEW_SECTIONS", "$.recovery_delta")
    for name in PRESERVED_V1_SUBTREES:
        if not _json_equal(base.get(name), v2_preregistration.get(name)):
            _fail("PRESERVED_SUBTREE_CHANGED", f"$.{name}")
    return {
        "comparison_unit": "recursive_json_leaf",
        "arrays_compared_atomically": True,
        "exact_value_replacements": sorted(
            _path_text(path) for path in observed_replacements
        ),
        "preserved_protocol_sources": list(V1_PROTOCOL_SOURCE_KEYS),
        "added_protocol_sources": sorted(observed_source_additions),
        "authorized_new_sections": sorted(
            _path_text(path) for path in observed_new_sections
        ),
        "preserved_subtrees": list(PRESERVED_V1_SUBTREES),
        "required_gates": list(REQUIRED_GATES),
    }


def expected_execution_counters() -> dict[str, int]:
    return cast(dict[str, int], v1.expected_execution_counters())


def build_attempt_owner(
    *, protocol_freeze_commit: str, preregistration_payload: bytes, attempt_id: str
) -> dict[str, Any]:
    _validate_commit(protocol_freeze_commit)
    _validate_attempt_id(attempt_id)
    return {
        "mm005_browser_research_model_evaluation_attempt_owner_version": (
            ATTEMPT_OWNER_VERSION
        ),
        "gate_id": EXECUTION_GATE_ID,
        "experiment_id": EXPERIMENT_ID,
        "run_id": RUN_ID,
        "attempt_id": attempt_id,
        "protocol_freeze_commit": protocol_freeze_commit,
        "preregistration": _receipt(PREREGISTRATION_PATH, preregistration_payload),
        "progress_path": PROGRESS_PATH,
        "recovery": {
            "exact_attempt_id_required": True,
            "executor_lock_must_be_released": True,
            "model_free_terminal_recovery_only": True,
        },
        "claims": {
            "attempt_consumed": True,
            "retry_allowed": False,
            "v1_retried": False,
            "model_output_has_execution_authority": False,
            "runtime_eligible": False,
        },
    }


def validate_attempt_owner(
    value: object,
    *,
    protocol_freeze_commit: str,
    preregistration_payload: bytes,
) -> dict[str, Any]:
    observed = _mapping(value, "$.attempt_owner")
    expected = build_attempt_owner(
        protocol_freeze_commit=protocol_freeze_commit,
        preregistration_payload=preregistration_payload,
        attempt_id=str(observed.get("attempt_id")),
    )
    if not _json_equal(observed, expected):
        _fail("ATTEMPT_OWNER_MISMATCH", "$.attempt_owner")
    return expected


def build_progress_event(
    *,
    previous_journal_payload: bytes,
    protocol_freeze_commit: str,
    preregistration_payload: bytes,
    attempt_owner_payload: bytes,
    event: str,
    counters: Mapping[str, Any],
    completed_record_ids: Sequence[str],
    record_id: str | None = None,
    artifact_states: Mapping[str, Any] | None = None,
    terminal: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    owner = parse_strict_json_bytes(attempt_owner_payload, location="$.attempt_owner")
    if artifact_json_bytes(owner) != attempt_owner_payload:
        _fail("ATTEMPT_OWNER_NOT_CANONICAL", "$.attempt_owner")
    checked_owner = validate_attempt_owner(
        owner,
        protocol_freeze_commit=protocol_freeze_commit,
        preregistration_payload=preregistration_payload,
    )
    attempt_id = str(checked_owner["attempt_id"])
    previous = validate_progress_journal(
        previous_journal_payload,
        protocol_freeze_commit=protocol_freeze_commit,
        preregistration_payload=preregistration_payload,
        attempt_owner_payload=attempt_owner_payload,
        allow_empty=True,
    )
    sequence = len(previous)
    previous_event = previous[-1] if previous else None
    value = {
        "mm005_browser_research_model_evaluation_progress_version": (PROGRESS_VERSION),
        "gate_id": EXECUTION_GATE_ID,
        "run_id": RUN_ID,
        "attempt_id": attempt_id,
        "sequence": sequence,
        "event": event,
        "record_id": record_id,
        "previous_event_sha256": (
            None
            if previous_event is None
            else sha256_bytes(artifact_json_bytes(previous_event))
        ),
        "protocol": {
            "freeze_commit": protocol_freeze_commit,
            "preregistration": _receipt(PREREGISTRATION_PATH, preregistration_payload),
            "attempt_owner": _receipt(ATTEMPT_OWNER_PATH, attempt_owner_payload),
        },
        "counters": dict(counters),
        "completed_record_ids": list(completed_record_ids),
        "artifacts": _normalize_artifact_states(artifact_states or {}),
        "terminal": None if terminal is None else dict(terminal),
        "claims": {
            "durable_checkpoint": True,
            "uncheckpointed_work_claimed": False,
            "model_output_has_execution_authority": False,
            "runtime_eligible": False,
        },
    }
    _validate_progress_event(value, previous_event, preregistration_payload)
    return value


def validate_progress_journal(
    payload: bytes,
    *,
    protocol_freeze_commit: str,
    preregistration_payload: bytes,
    attempt_owner_payload: bytes,
    allow_empty: bool = False,
) -> list[dict[str, Any]]:
    if not isinstance(payload, bytes) or len(payload) > 8 * 1024 * 1024:
        _fail("PROGRESS_BYTES_INVALID", "$.progress")
    if not payload:
        if allow_empty:
            return []
        _fail("PROGRESS_EMPTY", "$.progress")
    if not payload.endswith(b"\n"):
        _fail("PROGRESS_PARTIAL_LINE", "$.progress")
    owner = parse_strict_json_bytes(attempt_owner_payload, location="$.attempt_owner")
    if artifact_json_bytes(owner) != attempt_owner_payload:
        _fail("ATTEMPT_OWNER_NOT_CANONICAL", "$.attempt_owner")
    validate_attempt_owner(
        owner,
        protocol_freeze_commit=protocol_freeze_commit,
        preregistration_payload=preregistration_payload,
    )
    events: list[dict[str, Any]] = []
    for index, line in enumerate(payload.splitlines(keepends=True)):
        event = parse_strict_json_bytes(line, location=f"$.progress[{index}]")
        if artifact_json_bytes(event) != line:
            _fail("PROGRESS_EVENT_NOT_CANONICAL", f"$.progress[{index}]")
        _validate_progress_event(
            event,
            events[-1] if events else None,
            preregistration_payload,
            expected_owner=owner,
        )
        events.append(event)
    if not events and not allow_empty:
        _fail("PROGRESS_EMPTY", "$.progress")
    return events


def recover_progress_prefix(
    payload: bytes,
    *,
    protocol_freeze_commit: str,
    preregistration_payload: bytes,
    attempt_owner_payload: bytes,
) -> tuple[list[dict[str, Any]], bytes, dict[str, Any] | None]:
    """Return the authenticated JSONL prefix and bind an incomplete tail.

    This is only for process-restart recovery while holding the exclusive
    progress lease.  Complete but invalid lines are never discarded.
    """

    if not payload:
        _fail("PROGRESS_EMPTY", "$.progress")
    last_newline = payload.rfind(b"\n")
    if last_newline < 0:
        _fail("PROGRESS_INITIAL_EVENT_NOT_DURABLE", "$.progress")
    prefix = payload[: last_newline + 1]
    tail = payload[last_newline + 1 :]
    events = validate_progress_journal(
        prefix,
        protocol_freeze_commit=protocol_freeze_commit,
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


def build_evaluation_candidate(
    *,
    protocol_freeze_commit: str,
    preregistration_payload: bytes,
    attempt_owner_payload: bytes,
    cases: Sequence[Mapping[str, Any]],
    records: Sequence[Mapping[str, Any]],
    artifact_payloads: Mapping[str, bytes],
    execution: Mapping[str, Any],
    resources: Mapping[str, Any],
) -> dict[str, Any]:
    _validate_commit(protocol_freeze_commit)
    owner = parse_strict_json_bytes(attempt_owner_payload, location="$.attempt_owner")
    validate_attempt_owner(
        owner,
        protocol_freeze_commit=protocol_freeze_commit,
        preregistration_payload=preregistration_payload,
    )
    ordered = sorted(records, key=lambda item: str(item.get("record_id")))
    if len(cases) != len(ordered):
        _fail("CANDIDATE_CASE_COUNT", "$.cases")
    rebuilt: list[dict[str, Any]] = []
    for index, (record, raw_case) in enumerate(zip(ordered, cases, strict=True)):
        case = _mapping(raw_case, f"$.cases[{index}]")
        rebuilt_case = v1.build_case_result(
            record=record,
            artifact_payloads=artifact_payloads,
            raw_output=str(case.get("raw_output")),
            generated_tokens=_strict_int(
                case.get("generated_tokens"), f"$.cases[{index}].generated_tokens"
            ),
            latency_seconds=_strict_number(
                case.get("latency_seconds"), f"$.cases[{index}].latency_seconds"
            ),
        )
        if not _json_equal(case, rebuilt_case):
            _fail("CANDIDATE_CASE_MISMATCH", f"$.cases[{index}]")
        rebuilt.append(rebuilt_case)
    if not _json_equal(execution, expected_execution_counters()):
        _fail("EXECUTION_COUNTERS", "$.execution")
    checked_resources = _validated_resources(resources)
    return {
        "mm005_browser_research_model_evaluation_candidate_version": (
            CANDIDATE_VERSION
        ),
        "gate_id": EXECUTION_GATE_ID,
        "run_id": RUN_ID,
        "protocol_freeze_commit": protocol_freeze_commit,
        "preregistration": _receipt(PREREGISTRATION_PATH, preregistration_payload),
        "attempt_owner": _receipt(ATTEMPT_OWNER_PATH, attempt_owner_payload),
        "producer": {
            "kind": "model",
            "model_id": MODEL_ID,
            "model_revision": MODEL_REVISION,
            "adapter_model_id": ADAPTER_MODEL_ID,
            "execution_form": "nf4_base_plus_read_only_lora_adapter",
        },
        "execution": dict(execution),
        "resources": checked_resources,
        "cases": rebuilt,
        "claims": {
            "all_registered_model_calls_completed": True,
            "scoring_completed": False,
            "formal_measurement_complete": False,
            "model_output_has_execution_authority": False,
            "runtime_eligible": False,
        },
    }


def validate_evaluation_candidate(
    value: object,
    *,
    protocol_freeze_commit: str,
    preregistration_payload: bytes,
    attempt_owner_payload: bytes,
    records: Sequence[Mapping[str, Any]],
    artifact_payloads: Mapping[str, bytes],
) -> dict[str, Any]:
    observed = _mapping(value, "$.evaluation_candidate")
    expected = build_evaluation_candidate(
        protocol_freeze_commit=protocol_freeze_commit,
        preregistration_payload=preregistration_payload,
        attempt_owner_payload=attempt_owner_payload,
        cases=_object_sequence(observed.get("cases"), "$.evaluation_candidate.cases"),
        records=records,
        artifact_payloads=artifact_payloads,
        execution=_mapping(
            observed.get("execution"), "$.evaluation_candidate.execution"
        ),
        resources=_mapping(
            observed.get("resources"), "$.evaluation_candidate.resources"
        ),
    )
    if not _json_equal(observed, expected):
        _fail("EVALUATION_CANDIDATE_MISMATCH", "$.evaluation_candidate")
    return expected


def build_predictions(candidate: Mapping[str, Any]) -> dict[str, Any]:
    return cast(dict[str, Any], v1.build_predictions(candidate))


def build_evidence(
    *,
    protocol_freeze_commit: str,
    preregistration_payload: bytes,
    attempt_owner_payload: bytes,
    progress_payload: bytes,
    evaluation_candidate_payload: bytes,
    predictions_payload: bytes,
    records: Sequence[Mapping[str, Any]],
    artifact_payloads: Mapping[str, bytes],
    captured_at_utc: str,
) -> dict[str, Any]:
    _validate_timestamp(captured_at_utc)
    owner = parse_strict_json_bytes(attempt_owner_payload, location="$.attempt_owner")
    candidate = parse_strict_json_bytes(
        evaluation_candidate_payload, location="$.evaluation_candidate"
    )
    predictions = parse_strict_json_bytes(predictions_payload, location="$.predictions")
    validate_attempt_owner(
        owner,
        protocol_freeze_commit=protocol_freeze_commit,
        preregistration_payload=preregistration_payload,
    )
    checked_candidate = validate_evaluation_candidate(
        candidate,
        protocol_freeze_commit=protocol_freeze_commit,
        preregistration_payload=preregistration_payload,
        attempt_owner_payload=attempt_owner_payload,
        records=records,
        artifact_payloads=artifact_payloads,
    )
    expected_predictions = build_predictions(checked_candidate)
    if not _json_equal(predictions, expected_predictions):
        _fail("PREDICTIONS_MISMATCH", "$.predictions")
    progress = validate_progress_journal(
        progress_payload,
        protocol_freeze_commit=protocol_freeze_commit,
        preregistration_payload=preregistration_payload,
        attempt_owner_payload=attempt_owner_payload,
    )
    terminal = progress[-1]
    terminal_data = _mapping(terminal.get("terminal"), "$.progress.terminal")
    if (
        terminal.get("event") != "success_terminal_ready"
        or terminal_data.get("kind") != "success"
        or terminal_data.get("captured_at_utc") != captured_at_utc
        or not _json_equal(terminal.get("counters"), checked_candidate["execution"])
    ):
        _fail("SUCCESS_PROGRESS_TERMINAL_MISMATCH", "$.progress")
    _require_terminal_artifact_state(
        terminal,
        "evaluation_candidate",
        EVALUATION_CANDIDATE_PATH,
        evaluation_candidate_payload,
    )
    _require_terminal_artifact_state(
        terminal,
        "predictions",
        PREDICTIONS_PATH,
        predictions_payload,
    )
    cases = _object_sequence(checked_candidate["cases"], "$.candidate.cases")
    metrics = v1.score_case_results(records, cases)
    counters = _mapping(checked_candidate["execution"], "$.candidate.execution")
    resources = _mapping(checked_candidate["resources"], "$.candidate.resources")
    caps_passed = all(
        _strict_number(resources[key], f"$.resources.{key}") <= limit
        for key, limit in RESOURCE_CAPS.items()
    )
    gates = {name: True for name in REQUIRED_GATES}
    gates["one_fresh_base_and_adapter_load"] = (
        counters.get("fresh_base_loads") == 1
        and counters.get("independent_adapter_loads") == 1
    )
    gates["thirty_two_ordered_calls"] = (
        counters.get("generate_calls") == EXPECTED_RECORDS
        and counters.get("screenshot_inputs") == EXPECTED_SOURCE_BINDINGS
        and counters.get("source_snapshot_inputs") == 0
        and len(cases) == EXPECTED_RECORDS
    )
    gates["offline_zero_retry"] = all(
        counters.get(name) == 0
        for name in (
            "network_attempts",
            "retry_count",
            "training_runs",
            "optimizer_steps",
            "backward_calls",
            "adapter_writes",
            "model_or_tensor_saves",
        )
    )
    gates["resource_caps"] = caps_passed
    gates["durable_progress_persistence"] = terminal.get("sequence") == (
        len(progress) - 1
    )
    gates["interruption_terminal_recovery"] = True
    formal_gate_passed = all(gates.values())
    claims = {
        **v1.FREEZE_CLAIMS,
        "attempt_consumed": True,
        "evaluation_executed": True,
        "model_evaluated": True,
        "formal_measurement_complete": formal_gate_passed,
    }
    return {
        "mm005_browser_research_model_evaluation_evidence_version": (EVIDENCE_VERSION),
        "gate_id": EXECUTION_GATE_ID,
        "run_id": RUN_ID,
        "classification": (
            "outcome_neutral_measurement_complete_within_registered_caps"
            if formal_gate_passed
            else "outcome_neutral_measurement_complete_outside_registered_caps"
        ),
        "captured_at_utc": captured_at_utc,
        "protocol_freeze_commit": protocol_freeze_commit,
        "artifacts": {
            "preregistration": _receipt(PREREGISTRATION_PATH, preregistration_payload),
            "attempt_owner": _receipt(ATTEMPT_OWNER_PATH, attempt_owner_payload),
            "progress": _receipt(PROGRESS_PATH, progress_payload),
            "evaluation_candidate": _receipt(
                EVALUATION_CANDIDATE_PATH, evaluation_candidate_payload
            ),
            "predictions": _receipt(PREDICTIONS_PATH, predictions_payload),
        },
        "producer": copy.deepcopy(checked_candidate["producer"]),
        "execution": dict(counters),
        "resources": dict(resources),
        "metrics": metrics,
        "required_gates": gates,
        "formal_gate_passed": formal_gate_passed,
        "claims": claims,
        "limitations": {
            "accuracy_threshold_applied": False,
            "repeatability_established": False,
            "training_repeatability_established": False,
            "cross_machine_reproducibility": False,
            "generalized_quality_established": False,
            "safety_established": False,
            "prompt_injection_safety_established": False,
            "real_content_behavior_established": False,
            "live_browser_used": False,
            "execution_network_used": False,
            "runtime_eligibility": False,
            "terminal_recovery_exercised_in_this_success": False,
        },
        "next_gate": RESULT_REVIEW_GATE_ID,
    }


def validate_evidence(value: object, **kwargs: Any) -> dict[str, Any]:
    observed = _mapping(value, "$.evidence")
    expected = build_evidence(
        **kwargs,
        captured_at_utc=str(observed.get("captured_at_utc")),
    )
    if not _json_equal(observed, expected):
        _fail("EVIDENCE_MISMATCH", "$.evidence")
    return expected


def build_failure(
    *,
    protocol_freeze_commit: str,
    preregistration_payload: bytes,
    attempt_owner_payload: bytes,
    progress_payload: bytes,
    artifact_payloads: Mapping[str, bytes | None],
) -> dict[str, Any]:
    owner = parse_strict_json_bytes(attempt_owner_payload, location="$.attempt_owner")
    validate_attempt_owner(
        owner,
        protocol_freeze_commit=protocol_freeze_commit,
        preregistration_payload=preregistration_payload,
    )
    progress = validate_progress_journal(
        progress_payload,
        protocol_freeze_commit=protocol_freeze_commit,
        preregistration_payload=preregistration_payload,
        attempt_owner_payload=attempt_owner_payload,
    )
    last = progress[-1]
    terminal = _mapping(last.get("terminal"), "$.progress.terminal")
    if (
        last.get("event") != "failure_terminal_ready"
        or terminal.get("kind") != "failure"
    ):
        _fail("FAILURE_PROGRESS_TERMINAL_MISMATCH", "$.progress")
    stage = str(terminal.get("stage"))
    exception_type = str(terminal.get("exception_type"))
    captured_at_utc = str(terminal.get("captured_at_utc"))
    if stage not in FAILURE_STAGES:
        _fail("FAILURE_STAGE", "$.progress.terminal.stage")
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,127}", exception_type) is None:
        _fail("FAILURE_EXCEPTION_TYPE", "$.progress.terminal.exception_type")
    _validate_timestamp(captured_at_utc)
    counters = _mapping(last.get("counters"), "$.progress.counters")
    completed = _string_sequence(
        last.get("completed_record_ids"), "$.progress.completed_record_ids"
    )
    normalized_states = _normalize_artifact_states(
        _mapping(last.get("artifacts"), "$.progress.artifacts")
    )
    artifact_receipts: dict[str, Any] = {}
    for name, path in (
        ("evaluation_candidate", EVALUATION_CANDIDATE_PATH),
        ("predictions", PREDICTIONS_PATH),
    ):
        payload = artifact_payloads.get(name)
        state = normalized_states[name]
        if payload is None:
            if state is not None:
                _fail("FAILURE_ARTIFACT_STATE_MISMATCH", f"$.artifacts.{name}")
            artifact_receipts[name] = None
        else:
            expected = {
                "state": str(_mapping(state, f"$.artifacts.{name}").get("state")),
                "receipt": _receipt(path, payload),
            }
            if not _json_equal(state, expected):
                _fail("FAILURE_ARTIFACT_STATE_MISMATCH", f"$.artifacts.{name}")
            artifact_receipts[name] = expected
    return {
        "mm005_browser_research_model_evaluation_failure_version": FAILURE_VERSION,
        "gate_id": EXECUTION_GATE_ID,
        "run_id": RUN_ID,
        "protocol_freeze_commit": protocol_freeze_commit,
        "captured_at_utc": captured_at_utc,
        "stage": stage,
        "exception_type": exception_type,
        "counters": dict(counters),
        "completed_record_ids": list(completed),
        "artifacts": {
            "preregistration": _receipt(PREREGISTRATION_PATH, preregistration_payload),
            "attempt_owner": _receipt(ATTEMPT_OWNER_PATH, attempt_owner_payload),
            "progress": _receipt(PROGRESS_PATH, progress_payload),
            **artifact_receipts,
        },
        "terminal_recovery": {
            "external_controller_interruption": bool(
                terminal.get("external_controller_interruption")
            ),
            "interrupted_after_event": terminal.get("interrupted_after_event"),
            "discarded_progress_tail": terminal.get("discarded_progress_tail"),
            "model_imported_or_called_by_recovery": False,
            "network_used_by_recovery": False,
            "model_execution_retried": False,
            "durable_progress_only": True,
        },
        "claims": {
            **v1.FREEZE_CLAIMS,
            "attempt_consumed": True,
        },
        "next_gate": FAILURE_CLASSIFICATION_GATE_ID,
    }


def validate_failure(value: object, **kwargs: Any) -> dict[str, Any]:
    observed = _mapping(value, "$.failure")
    expected = build_failure(**kwargs)
    if not _json_equal(observed, expected):
        _fail("FAILURE_MISMATCH", "$.failure")
    return expected


def terminal_event(
    *,
    kind: str,
    captured_at_utc: str,
    stage: str | None = None,
    exception_type: str | None = None,
    external_controller_interruption: bool = False,
    interrupted_after_event: str | None = None,
    discarded_progress_tail: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    _validate_timestamp(captured_at_utc)
    if kind == "success":
        if (
            any(
                value is not None
                for value in (
                    stage,
                    exception_type,
                    interrupted_after_event,
                    discarded_progress_tail,
                )
            )
            or external_controller_interruption
        ):
            _fail("SUCCESS_TERMINAL_FIELDS", "$.terminal")
        return {"kind": "success", "captured_at_utc": captured_at_utc}
    if kind != "failure" or stage not in FAILURE_STAGES:
        _fail("FAILURE_TERMINAL_FIELDS", "$.terminal")
    if (
        exception_type is None
        or re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,127}", exception_type) is None
        or interrupted_after_event not in PROGRESS_EVENTS
    ):
        _fail("FAILURE_TERMINAL_FIELDS", "$.terminal")
    checked_tail: dict[str, Any] | None = None
    if discarded_progress_tail is not None:
        tail = _mapping(discarded_progress_tail, "$.terminal.discarded_progress_tail")
        if (
            set(tail)
            != {
                "bytes",
                "sha256",
                "authenticated_event",
                "execution_fact_claimed",
            }
            or _strict_int(
                tail.get("bytes"), "$.terminal.discarded_progress_tail.bytes"
            )
            <= 0
            or not isinstance(tail.get("sha256"), str)
            or re.fullmatch(r"sha256:[0-9a-f]{64}", str(tail.get("sha256"))) is None
            or tail.get("authenticated_event") is not False
            or tail.get("execution_fact_claimed") is not False
        ):
            _fail("FAILURE_TERMINAL_TAIL", "$.terminal.discarded_progress_tail")
        checked_tail = dict(tail)
    return {
        "kind": "failure",
        "captured_at_utc": captured_at_utc,
        "stage": stage,
        "exception_type": exception_type,
        "external_controller_interruption": external_controller_interruption,
        "interrupted_after_event": interrupted_after_event,
        "discarded_progress_tail": checked_tail,
    }


def artifact_state(path: str, payload: bytes, *, state: str) -> dict[str, Any]:
    if state not in {"validated", "observed_unvalidated"}:
        _fail("ARTIFACT_STATE_INVALID", "$.artifact_state")
    return {"state": state, "receipt": _receipt(path, payload)}


def _validate_progress_event(
    value: Mapping[str, Any],
    previous: Mapping[str, Any] | None,
    preregistration_payload: bytes,
    *,
    expected_owner: Mapping[str, Any] | None = None,
) -> None:
    expected_keys = {
        "mm005_browser_research_model_evaluation_progress_version",
        "gate_id",
        "run_id",
        "attempt_id",
        "sequence",
        "event",
        "record_id",
        "previous_event_sha256",
        "protocol",
        "counters",
        "completed_record_ids",
        "artifacts",
        "terminal",
        "claims",
    }
    if set(value) != expected_keys:
        _fail("PROGRESS_FIELD_SET", "$.progress")
    event = str(value.get("event"))
    sequence = _strict_int(value.get("sequence"), "$.progress.sequence")
    attempt_id = str(value.get("attempt_id"))
    _validate_attempt_id(attempt_id)
    if (
        value.get("mm005_browser_research_model_evaluation_progress_version")
        != PROGRESS_VERSION
        or value.get("gate_id") != EXECUTION_GATE_ID
        or value.get("run_id") != RUN_ID
        or event not in PROGRESS_EVENTS
    ):
        _fail("PROGRESS_IDENTITY", "$.progress")
    if expected_owner is not None and attempt_id != expected_owner.get("attempt_id"):
        _fail("PROGRESS_OWNER_MISMATCH", "$.progress.attempt_id")
    protocol = _mapping(value.get("protocol"), "$.progress.protocol")
    freeze_commit = protocol.get("freeze_commit")
    if not isinstance(freeze_commit, str):
        _fail("PROGRESS_PROTOCOL_BINDING", "$.progress.protocol.freeze_commit")
    _validate_commit(freeze_commit)
    if protocol.get("preregistration") != _receipt(
        PREREGISTRATION_PATH, preregistration_payload
    ) or not isinstance(protocol.get("attempt_owner"), Mapping):
        _fail("PROGRESS_PROTOCOL_BINDING", "$.progress.protocol")
    if expected_owner is not None:
        expected_freeze_commit = expected_owner.get("protocol_freeze_commit")
        if freeze_commit != expected_freeze_commit or protocol.get(
            "attempt_owner"
        ) != _receipt(
            ATTEMPT_OWNER_PATH,
            artifact_json_bytes(expected_owner),
        ):
            _fail("PROGRESS_OWNER_BINDING", "$.progress.protocol")
    if previous is None:
        if (
            sequence != 0
            or event != "attempt_claimed"
            or value.get("previous_event_sha256") is not None
        ):
            _fail("PROGRESS_INITIAL_EVENT", "$.progress")
    else:
        if previous.get("event") in TERMINAL_EVENTS:
            _fail("PROGRESS_AFTER_TERMINAL", "$.progress")
        if (
            sequence != _strict_int(previous.get("sequence"), "$.previous.sequence") + 1
            or value.get("previous_event_sha256")
            != sha256_bytes(artifact_json_bytes(previous))
            or attempt_id != previous.get("attempt_id")
            or protocol != previous.get("protocol")
        ):
            _fail("PROGRESS_CHAIN", "$.progress")
        _validate_progress_transition(previous, value)
    counters = _validate_partial_counters(
        _mapping(value.get("counters"), "$.progress.counters")
    )
    completed = _validate_completed_record_ids(
        _string_sequence(
            value.get("completed_record_ids"), "$.progress.completed_record_ids"
        ),
        counters,
        preregistration_payload,
    )
    record_id = value.get("record_id")
    case_order, screenshot_counts = _input_case_contract(preregistration_payload)
    if event in {"generation_started", "generation_completed"}:
        if not isinstance(record_id, str):
            _fail("PROGRESS_RECORD_ID", "$.progress.record_id")
    elif record_id is not None:
        _fail("PROGRESS_RECORD_ID", "$.progress.record_id")
    if event == "generation_started" and counters["generate_attempts"] != (
        counters["generate_calls"] + 1
    ):
        _fail("PROGRESS_GENERATION_STARTED_COUNTER", "$.progress.counters")
    if event == "generation_started":
        if len(completed) >= len(case_order) or record_id != case_order[len(completed)]:
            _fail("PROGRESS_GENERATION_RECORD_ORDER", "$.progress.record_id")
        expected_screenshot_inputs = (
            sum(screenshot_counts[item] for item in completed)
            + screenshot_counts[record_id]
        )
    else:
        expected_screenshot_inputs = sum(screenshot_counts[item] for item in completed)
    if event != "failure_terminal_ready" and (
        counters["screenshot_inputs"] != expected_screenshot_inputs
    ):
        _fail("PROGRESS_SCREENSHOT_COUNTER", "$.progress.counters.screenshot_inputs")
    if event == "generation_completed" and (
        counters["generate_calls"] != len(completed)
        or counters["generate_attempts"] != counters["generate_calls"]
    ):
        _fail("PROGRESS_GENERATION_COMPLETED_COUNTER", "$.progress.counters")
    artifacts = _normalize_artifact_states(
        _mapping(value.get("artifacts"), "$.progress.artifacts")
    )
    if previous is not None:
        previous_artifacts = _normalize_artifact_states(
            _mapping(previous.get("artifacts"), "$.previous.artifacts")
        )
        for name in artifacts:
            if previous_artifacts[name] is not None and not _json_equal(
                artifacts[name], previous_artifacts[name]
            ):
                _fail("PROGRESS_ARTIFACT_REPLACED", f"$.progress.artifacts.{name}")
    terminal = value.get("terminal")
    if event not in TERMINAL_EVENTS:
        if terminal is not None:
            _fail("PROGRESS_NONTERMINAL_HAS_TERMINAL", "$.progress.terminal")
    else:
        checked_terminal = _mapping(terminal, "$.progress.terminal")
        expected_kind = "success" if event == "success_terminal_ready" else "failure"
        if checked_terminal.get("kind") != expected_kind:
            _fail("PROGRESS_TERMINAL_KIND", "$.progress.terminal")
        _validate_timestamp(str(checked_terminal.get("captured_at_utc")))
        if expected_kind == "success":
            expected_terminal = terminal_event(
                kind="success",
                captured_at_utc=str(checked_terminal.get("captured_at_utc")),
            )
        else:
            tail = checked_terminal.get("discarded_progress_tail")
            expected_terminal = terminal_event(
                kind="failure",
                captured_at_utc=str(checked_terminal.get("captured_at_utc")),
                stage=str(checked_terminal.get("stage")),
                exception_type=str(checked_terminal.get("exception_type")),
                external_controller_interruption=bool(
                    checked_terminal.get("external_controller_interruption")
                ),
                interrupted_after_event=str(
                    checked_terminal.get("interrupted_after_event")
                ),
                discarded_progress_tail=(
                    None
                    if tail is None
                    else _mapping(tail, "$.progress.terminal.discarded_progress_tail")
                ),
            )
            if previous is None or checked_terminal.get(
                "interrupted_after_event"
            ) != previous.get("event"):
                _fail("PROGRESS_FAILURE_BOUNDARY", "$.progress.terminal")
        if not _json_equal(checked_terminal, expected_terminal):
            _fail("PROGRESS_TERMINAL_FIELDS", "$.progress.terminal")
    _validate_event_envelope(event, counters, completed, artifacts)
    expected_claims = {
        "durable_checkpoint": True,
        "uncheckpointed_work_claimed": False,
        "model_output_has_execution_authority": False,
        "runtime_eligible": False,
    }
    if not _json_equal(value.get("claims"), expected_claims):
        _fail("PROGRESS_CLAIMS", "$.progress.claims")


def _validate_progress_transition(
    previous: Mapping[str, Any], current: Mapping[str, Any]
) -> None:
    previous_event = str(previous.get("event"))
    event = str(current.get("event"))
    allowed: dict[str, set[str]] = {
        "attempt_claimed": {"context_preflight_completed", "failure_terminal_ready"},
        "context_preflight_completed": {"base_load_started", "failure_terminal_ready"},
        "base_load_started": {"base_load_completed", "failure_terminal_ready"},
        "base_load_completed": {"adapter_load_started", "failure_terminal_ready"},
        "adapter_load_started": {"adapter_load_completed", "failure_terminal_ready"},
        "adapter_load_completed": {"generation_started", "failure_terminal_ready"},
        "generation_started": {"generation_completed", "failure_terminal_ready"},
        "generation_completed": {
            "generation_started",
            "model_evaluation_completed",
            "failure_terminal_ready",
        },
        "model_evaluation_completed": {
            "candidate_persisted",
            "failure_terminal_ready",
        },
        "candidate_persisted": {"predictions_persisted", "failure_terminal_ready"},
        "predictions_persisted": {
            "success_terminal_ready",
            "failure_terminal_ready",
        },
    }
    if event not in allowed.get(previous_event, set()):
        _fail("PROGRESS_TRANSITION", "$.progress.event")
    previous_counters = _mapping(previous.get("counters"), "$.previous.counters")
    current_counters = _mapping(current.get("counters"), "$.progress.counters")
    for name in expected_execution_counters():
        if _strict_int(current_counters.get(name), f"$.progress.counters.{name}") < (
            _strict_int(previous_counters.get(name), f"$.previous.counters.{name}")
        ):
            _fail("PROGRESS_COUNTER_REGRESSION", f"$.progress.counters.{name}")
    if event == "failure_terminal_ready" and not _json_equal(
        current_counters, previous_counters
    ):
        _fail("PROGRESS_FAILURE_COUNTER_CHANGE", "$.progress.counters")
    previous_completed = _string_sequence(
        previous.get("completed_record_ids"), "$.previous.completed_record_ids"
    )
    current_completed = _string_sequence(
        current.get("completed_record_ids"), "$.progress.completed_record_ids"
    )
    if list(current_completed[: len(previous_completed)]) != list(previous_completed):
        _fail("PROGRESS_COMPLETED_PREFIX_REGRESSION", "$.progress.completed_record_ids")
    if event == "generation_completed":
        if (
            current.get("record_id") != previous.get("record_id")
            or len(current_completed) != len(previous_completed) + 1
            or current_completed[-1] != current.get("record_id")
        ):
            _fail("PROGRESS_GENERATION_PAIR", "$.progress")
    elif list(current_completed) != list(previous_completed):
        _fail("PROGRESS_COMPLETED_IDS_CHANGED", "$.progress.completed_record_ids")


def _validate_event_envelope(
    event: str,
    counters: Mapping[str, int],
    completed: Sequence[str],
    artifacts: Mapping[str, Any],
) -> None:
    zero = {name: 0 for name in expected_execution_counters()}
    zero["run_attempts"] = 1
    exact_states = {
        "attempt_claimed": zero,
        "context_preflight_completed": zero,
        "base_load_started": {**zero, "fresh_base_load_attempts": 1},
        "base_load_completed": {
            **zero,
            "fresh_base_load_attempts": 1,
            "fresh_base_loads": 1,
        },
        "adapter_load_started": {
            **zero,
            "fresh_base_load_attempts": 1,
            "fresh_base_loads": 1,
            "independent_adapter_load_attempts": 1,
        },
        "adapter_load_completed": {
            **zero,
            "fresh_base_load_attempts": 1,
            "fresh_base_loads": 1,
            "independent_adapter_load_attempts": 1,
            "independent_adapter_loads": 1,
        },
    }
    if event in exact_states and not _json_equal(counters, exact_states[event]):
        _fail("PROGRESS_EVENT_COUNTER_ENVELOPE", "$.progress.counters")
    if event in exact_states and completed:
        _fail("PROGRESS_EVENT_COMPLETED_ENVELOPE", "$.progress.completed_record_ids")
    if event == "model_evaluation_completed" and not _json_equal(
        counters, expected_execution_counters()
    ):
        _fail("PROGRESS_EVENT_COUNTER_ENVELOPE", "$.progress.counters")
    if (
        event
        in {
            "model_evaluation_completed",
            "candidate_persisted",
            "predictions_persisted",
            "success_terminal_ready",
        }
        and len(completed) != EXPECTED_RECORDS
    ):
        _fail("PROGRESS_EVENT_COMPLETED_ENVELOPE", "$.progress.completed_record_ids")
    if event in {
        "attempt_claimed",
        "context_preflight_completed",
        "base_load_started",
        "base_load_completed",
        "adapter_load_started",
        "adapter_load_completed",
        "generation_started",
        "generation_completed",
        "model_evaluation_completed",
    } and any(value is not None for value in artifacts.values()):
        _fail("PROGRESS_EVENT_ARTIFACT_ENVELOPE", "$.progress.artifacts")
    if event == "candidate_persisted":
        candidate_state = artifacts["evaluation_candidate"]
        if (
            candidate_state is None
            or _mapping(
                candidate_state, "$.progress.artifacts.evaluation_candidate"
            ).get("state")
            != "validated"
            or artifacts["predictions"] is not None
        ):
            _fail("PROGRESS_EVENT_ARTIFACT_ENVELOPE", "$.progress.artifacts")
    if event in {"predictions_persisted", "success_terminal_ready"}:
        if any(
            value is None
            or _mapping(value, "$.progress.artifacts").get("state") != "validated"
            for value in artifacts.values()
        ):
            _fail("PROGRESS_EVENT_ARTIFACT_ENVELOPE", "$.progress.artifacts")


def _validate_partial_counters(value: Mapping[str, Any]) -> dict[str, int]:
    expected = expected_execution_counters()
    if set(value) != set(expected):
        _fail("PROGRESS_COUNTER_KEYS", "$.progress.counters")
    result: dict[str, int] = {}
    for name, maximum in expected.items():
        item = _strict_int(value.get(name), f"$.progress.counters.{name}")
        if item < 0 or item > maximum:
            _fail("PROGRESS_COUNTER_RANGE", f"$.progress.counters.{name}")
        result[name] = item
    for name in (
        "retry_count",
        "network_attempts",
        "training_runs",
        "optimizer_steps",
        "backward_calls",
        "adapter_writes",
        "model_or_tensor_saves",
        "source_snapshot_inputs",
    ):
        if result[name] != 0:
            _fail("PROGRESS_FORBIDDEN_COUNTER", f"$.progress.counters.{name}")
    if (
        result["fresh_base_loads"] > result["fresh_base_load_attempts"]
        or result["independent_adapter_loads"]
        > result["independent_adapter_load_attempts"]
        or result["independent_adapter_load_attempts"] > result["fresh_base_loads"]
        or result["generate_calls"] > result["generate_attempts"]
        or result["generate_attempts"] - result["generate_calls"] > 1
        or (
            result["generate_attempts"] > 0 and result["independent_adapter_loads"] != 1
        )
    ):
        _fail("PROGRESS_COUNTER_CAUSALITY", "$.progress.counters")
    return result


def _validate_completed_record_ids(
    values: Sequence[str],
    counters: Mapping[str, int],
    preregistration_payload: bytes,
) -> list[str]:
    order, _screenshot_counts = _input_case_contract(preregistration_payload)
    result = list(values)
    if result != list(order[: len(result)]) or len(set(result)) != len(result):
        _fail("PROGRESS_COMPLETED_RECORD_PREFIX", "$.progress.completed_record_ids")
    if len(result) != counters["generate_calls"]:
        _fail("PROGRESS_COMPLETED_RECORD_COUNT", "$.progress.completed_record_ids")
    return result


def _input_case_contract(
    preregistration_payload: bytes,
) -> tuple[list[str], dict[str, int]]:
    preregistration = parse_strict_json_bytes(
        preregistration_payload, location="$.preregistration"
    )
    suite = _mapping(preregistration.get("input_suite"), "$.input_suite")
    order = _string_sequence(suite.get("case_order"), "$.input_suite.case_order")
    projections = _object_sequence(
        suite.get("prompt_projection_registry"),
        "$.input_suite.prompt_projection_registry",
    )
    counts: dict[str, int] = {}
    for index, projection in enumerate(projections):
        record_id = projection.get("record_id")
        screenshots = projection.get("screenshot_payloads")
        if (
            not isinstance(record_id, str)
            or record_id in counts
            or not isinstance(screenshots, list)
            or not screenshots
        ):
            _fail(
                "PROGRESS_INPUT_CONTRACT",
                f"$.input_suite.prompt_projection_registry[{index}]",
            )
        counts[record_id] = len(screenshots)
    if set(counts) != set(order) or len(order) != EXPECTED_RECORDS:
        _fail("PROGRESS_INPUT_CONTRACT", "$.input_suite")
    return order, counts


def _normalize_artifact_states(value: Mapping[str, Any]) -> dict[str, Any]:
    expected_paths = {
        "evaluation_candidate": EVALUATION_CANDIDATE_PATH,
        "predictions": PREDICTIONS_PATH,
    }
    if set(value).difference(expected_paths):
        _fail("ARTIFACT_STATE_KEYS", "$.artifacts")
    result: dict[str, Any] = {}
    for name, path in expected_paths.items():
        raw = value.get(name)
        if raw is None:
            result[name] = None
            continue
        state = _mapping(raw, f"$.artifacts.{name}")
        if set(state) != {"state", "receipt"} or state.get("state") not in {
            "validated",
            "observed_unvalidated",
        }:
            _fail("ARTIFACT_STATE_INVALID", f"$.artifacts.{name}")
        receipt = _closed_receipt(state.get("receipt"), f"$.artifacts.{name}.receipt")
        if receipt["path"] != path:
            _fail("ARTIFACT_STATE_PATH", f"$.artifacts.{name}.receipt.path")
        result[name] = {"state": state["state"], "receipt": receipt}
    return result


def _require_terminal_artifact_state(
    terminal_event_value: Mapping[str, Any], name: str, path: str, payload: bytes
) -> None:
    artifacts = _normalize_artifact_states(
        _mapping(terminal_event_value.get("artifacts"), "$.progress.artifacts")
    )
    expected = {"state": "validated", "receipt": _receipt(path, payload)}
    if not _json_equal(artifacts.get(name), expected):
        _fail("TERMINAL_ARTIFACT_STATE_MISMATCH", f"$.progress.artifacts.{name}")


def _validated_v1_preregistration(
    value: Mapping[str, Any], payload: bytes
) -> dict[str, Any]:
    if (
        len(payload) != V1_PREREGISTRATION_RECEIPT["bytes"]
        or sha256_bytes(payload) != V1_PREREGISTRATION_RECEIPT["sha256"]
        or artifact_json_bytes(value) != payload
    ):
        _fail("V1_PREREGISTRATION_RECEIPT_MISMATCH", "$.v1_preregistration")
    parsed = parse_strict_json_bytes(payload, location="$.v1_preregistration")
    if not _json_equal(parsed, value):
        _fail("V1_PREREGISTRATION_MISMATCH", "$.v1_preregistration")
    return copy.deepcopy(parsed)


def _validated_resources(value: Mapping[str, Any]) -> dict[str, float | int]:
    if set(value) != set(RESOURCE_CAPS):
        _fail("RESOURCE_KEYS", "$.resources")
    result: dict[str, float | int] = {}
    for name in RESOURCE_CAPS:
        item = _strict_number(value.get(name), f"$.resources.{name}")
        if not math.isfinite(float(item)) or item < 0:
            _fail("RESOURCE_VALUE", f"$.resources.{name}")
        result[name] = item
    return result


def _receipt(path: str, payload: bytes) -> dict[str, Any]:
    return {"path": path, "bytes": len(payload), "sha256": sha256_bytes(payload)}


def _closed_receipt(value: object, location: str) -> dict[str, Any]:
    receipt = _mapping(value, location)
    if set(receipt) != {"path", "bytes", "sha256"}:
        _fail("RECEIPT_FIELD_SET", location)
    path = receipt.get("path")
    size = receipt.get("bytes")
    digest = receipt.get("sha256")
    if (
        not isinstance(path, str)
        or not path
        or "\\" in path
        or path.startswith("/")
        or ".." in Path(path).parts
        or type(size) is not int
        or size < 0
        or not isinstance(digest, str)
        or re.fullmatch(r"sha256:[0-9a-f]{64}", digest) is None
    ):
        _fail("RECEIPT_INVALID", location)
    return {"path": path, "bytes": size, "sha256": digest}


def _set_path(target: dict[str, Any], path: tuple[str, ...], value: Any) -> None:
    current = target
    for key in path[:-1]:
        item = current.get(key)
        if not isinstance(item, dict):
            _fail("REPLACEMENT_PARENT_MISSING", _path_label(path))
        current = item
    if path[-1] not in current:
        _fail("REPLACEMENT_PATH_MISSING", _path_label(path))
    current[path[-1]] = value


def _mapping(value: object, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail("EXPECTED_OBJECT", location)
    return cast(Mapping[str, Any], value)


def _object_sequence(value: object, location: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        _fail("EXPECTED_ARRAY", location)
    return [_mapping(item, f"{location}[{index}]") for index, item in enumerate(value)]


def _string_sequence(value: object, location: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        _fail("EXPECTED_STRING_ARRAY", location)
    return cast(list[str], value)


def _strict_int(value: object, location: str) -> int:
    if type(value) is not int:
        _fail("EXPECTED_INTEGER", location)
    return value


def _strict_number(value: object, location: str) -> float | int:
    if type(value) not in {int, float}:
        _fail("EXPECTED_NUMBER", location)
    number = cast(float | int, value)
    if not math.isfinite(float(number)):
        _fail("EXPECTED_FINITE_NUMBER", location)
    return number


def _validate_attempt_id(value: str) -> None:
    if re.fullmatch(r"[0-9a-f]{64}", value) is None:
        _fail("ATTEMPT_ID", "$.attempt_id")


def _validate_commit(value: str) -> None:
    if re.fullmatch(r"[0-9a-f]{40}", value) is None:
        _fail("PROTOCOL_FREEZE_COMMIT", "$.protocol_freeze_commit")


def _validate_timestamp(value: str) -> None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise MM005BrowserResearchRecoveryError(
            "TIMESTAMP_INVALID", "$.captured_at_utc"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        _fail("TIMESTAMP_INVALID", "$.captured_at_utc")


def _json_equal(left: object, right: object) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, Mapping):
        if not isinstance(right, Mapping) or set(left) != set(right):
            return False
        return all(_json_equal(left[key], right[key]) for key in left)
    if isinstance(left, list):
        return (
            isinstance(right, list)
            and len(left) == len(right)
            and all(_json_equal(a, b) for a, b in zip(left, right, strict=True))
        )
    if isinstance(left, float):
        return isinstance(right, float) and left.hex() == right.hex()
    return left == right


def _path_text(path: tuple[str, ...]) -> str:
    return ".".join(path)


def _path_label(path: tuple[str, ...]) -> str:
    return "$" if not path else "$." + _path_text(path)


def _fail(code: str, location: str = "$") -> NoReturn:
    raise MM005BrowserResearchRecoveryError(code, location)


__all__ = [
    "ADAPTER_LFS_PATH",
    "ADAPTER_RECEIPTS",
    "ADAPTER_ROOT",
    "ATTEMPT_OWNER_PATH",
    "CLASSIFICATION_MERGE_COMMIT",
    "DURABLE_RECOVERY_CONTRACT",
    "EVALUATION_CANDIDATE_PATH",
    "EVIDENCE_PATH",
    "EXECUTION_GATE_ID",
    "EXPERIMENT_ID",
    "FAILURE_CLASSIFICATION_GATE_ID",
    "FAILURE_PATH",
    "FORMAL_GATE_ADDITIONS",
    "FORMAL_PYTHON_ARGS",
    "FORMAL_PYTHON_PATH",
    "LIFECYCLE_LEASE_MARKER",
    "LIFECYCLE_LEASE_PATH",
    "LIFECYCLE_LEASE_ROOT",
    "FREEZE_BLOB_READER",
    "MAX_NEW_TOKENS",
    "MODEL_SNAPSHOT_ROOT",
    "PREDICTIONS_PATH",
    "PREREGISTRATION_PATH",
    "PROGRESS_EVENTS",
    "PROGRESS_PATH",
    "PROTOCOL_GATE_ID",
    "PROTOCOL_SOURCE_PATHS",
    "REQUIRED_GATES",
    "RESOURCE_CAPS",
    "RESULT_REVIEW_GATE_ID",
    "RUN_ID",
    "RUN_OUTPUT_ROOT",
    "SEED",
    "TERMINAL_EVENTS",
    "artifact_json_bytes",
    "artifact_state",
    "build_attempt_owner",
    "build_evaluation_candidate",
    "build_evidence",
    "build_failure",
    "build_predictions",
    "build_progress_event",
    "expected_execution_counters",
    "expected_preregistration",
    "parse_strict_json_bytes",
    "sha256_bytes",
    "terminal_event",
    "validate_attempt_owner",
    "validate_evaluation_candidate",
    "validate_evidence",
    "validate_failure",
    "validate_failure_classification_recovery_policy",
    "validate_preregistration",
    "validate_progress_journal",
    "recover_progress_prefix",
    "validate_recovery_delta",
    "validate_recovery_lineage_payloads",
]
