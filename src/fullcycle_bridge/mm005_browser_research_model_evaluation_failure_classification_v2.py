"""Model-free classification of the consumed MM-005 Browser eval v2 failure."""

from __future__ import annotations

import os
import re
import stat
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any, NoReturn

from . import mm005_browser_research_model_evaluation as v1
from . import (
    mm005_browser_research_model_evaluation_failure_classification as v1_failure,
)
from . import mm005_browser_research_model_evaluation_protocol_v2 as protocol
from . import mm005_browser_research_model_evaluation_recovery_io as recovery_io

FAILURE_CLASSIFICATION_VERSION = 2
CLASSIFICATION_GATE_ID = protocol.FAILURE_CLASSIFICATION_GATE_ID
FAILED_GATE_ID = protocol.EXECUTION_GATE_ID
NEXT_GATE_ID = (
    "MM-005-browser-research-model-evaluation-generation-failure-"
    "investigation-protocol-v1"
)
PROTOCOL_FREEZE_COMMIT = "91b637c6b365ea8632b31335f5c74ac6c60e6b71"
PREREGISTRATION_BYTES = 120_315
PREREGISTRATION_SHA256 = (
    "sha256:512b3523196bf80e7e137c7777c205fa92a57acf371464f3f65671c406706c2e"
)
CLASSIFIED_AT_UTC = "2026-08-29T02:53:10Z"

TRACKED_ATTEMPT_OWNER_PATH = (
    "baseline/mm005-browser-research-model-eval-v2-attempt-owner.json"
)
TRACKED_PROGRESS_PATH = "baseline/mm005-browser-research-model-eval-v2-progress.json"
TRACKED_FAILURE_PATH = "baseline/mm005-browser-research-model-eval-v2-failure.json"
ARTIFACT_PATH = (
    "baseline/mm005-browser-research-model-eval-v2-failure-classification.json"
)

ATTEMPT_OWNER_BYTES = 938
ATTEMPT_OWNER_SHA256 = (
    "sha256:a80cf6a2a9142fdfbc7a92646498a05e5036fc13227af88470297b98990aad87"
)
PROGRESS_BYTES = 22_782
PROGRESS_SHA256 = (
    "sha256:a19709eb55fedc248eed32c1acbe9dbf0caa61f2cfc1a9ae7f5cf16b2a9a70b1"
)
FAILURE_BYTES = 2_675
FAILURE_SHA256 = (
    "sha256:46f3968482567db2810237c277f65d982ce9518f829c43ad96bd1fc7d2776bc7"
)

EXPECTED_LOCAL_ENTRIES = (
    "attempt-owner.json",
    "failure.json",
    "progress.json",
)
EXPECTED_EVENT_COUNT = 14
EXPECTED_TERMINAL_SEQUENCE = 13
FAILED_RECORD_ID = (
    "sha256:26b3a9da0467d1c18cc4a050ec10dc03a415a9c3a38a2a37de8b9805c67adaf7"
)
COMPLETED_RECORD_IDS = (
    "sha256:0a28a7ef2a71ee5ba36d7f329a7e02bcd3149a36b64667ab387cf080991238f6",
    "sha256:192b8da3beaae26a899e6ab6cc8be8d5dbbc7ae79cc9940d0ef67e939887a17e",
    "sha256:1c616001f9cd831a764e5ced483c827ca0c81d67d8124f713cbff1b6248b319f",
)
EXPECTED_COUNTERS = {
    "adapter_writes": 0,
    "backward_calls": 0,
    "fresh_base_load_attempts": 1,
    "fresh_base_loads": 1,
    "generate_attempts": 4,
    "generate_calls": 3,
    "independent_adapter_load_attempts": 1,
    "independent_adapter_loads": 1,
    "model_or_tensor_saves": 0,
    "network_attempts": 0,
    "optimizer_steps": 0,
    "retry_count": 0,
    "run_attempts": 1,
    "screenshot_inputs": 9,
    "source_snapshot_inputs": 0,
    "training_runs": 0,
}

_MAX_BOUND_FILE_BYTES = 8 * 1024 * 1024
_RAW_TRACKED_PATHS = {
    "attempt_owner": TRACKED_ATTEMPT_OWNER_PATH,
    "progress": TRACKED_PROGRESS_PATH,
    "failure": TRACKED_FAILURE_PATH,
}
_RAW_LOCAL_PATHS = {
    "attempt_owner": protocol.ATTEMPT_OWNER_PATH,
    "progress": protocol.PROGRESS_PATH,
    "failure": protocol.FAILURE_PATH,
}


def load_tracked_failure_context(root: Path) -> dict[str, Any]:
    """Validate the frozen protocol and three tracked terminal artifacts."""

    preregistration_payload = _read_regular_file(
        root / protocol.PREREGISTRATION_PATH,
        "MM-005 Browser Research model-evaluation v2 preregistration",
    )
    if (
        len(preregistration_payload) != PREREGISTRATION_BYTES
        or protocol.sha256_bytes(preregistration_payload) != PREREGISTRATION_SHA256
    ):
        _fail("PREREGISTRATION_BINDING_MISMATCH", "$.protocol.preregistration")
    preregistration = protocol.parse_strict_json_bytes(
        preregistration_payload, location="$.protocol.preregistration"
    )
    if protocol.artifact_json_bytes(preregistration) != preregistration_payload:
        _fail("PREREGISTRATION_NOT_CANONICAL", "$.protocol.preregistration")

    _require_git_commit(root, PROTOCOL_FREEZE_COMMIT)
    frozen_preregistration = _read_git_blob(
        root, PROTOCOL_FREEZE_COMMIT, protocol.PREREGISTRATION_PATH
    )
    if frozen_preregistration != preregistration_payload:
        _fail("FROZEN_PREREGISTRATION_MISMATCH", "$.protocol.preregistration")

    source_receipts: dict[str, dict[str, Any]] = {}
    source_bindings: dict[str, dict[str, Any]] = {}
    registered_sources = _mapping(
        preregistration.get("source_receipts"), "$.protocol.source_receipts"
    )
    if set(registered_sources) != set(protocol.PROTOCOL_SOURCE_PATHS):
        _fail("PROTOCOL_SOURCE_SET_MISMATCH", "$.protocol.source_receipts")
    for name, relative in sorted(protocol.PROTOCOL_SOURCE_PATHS.items()):
        payload = _read_regular_file(root / relative, f"protocol source {name}")
        receipt = _receipt(relative, payload)
        if (
            dict(_mapping(registered_sources.get(name), f"$.source_receipts.{name}"))
            != receipt
        ):
            _fail("PROTOCOL_SOURCE_RECEIPT_MISMATCH", f"$.source_receipts.{name}")
        if _read_git_blob(root, PROTOCOL_FREEZE_COMMIT, relative) != payload:
            _fail("FROZEN_PROTOCOL_SOURCE_MISMATCH", f"$.source_bindings.{name}")
        source_receipts[name] = receipt
        source_bindings[name] = {
            **receipt,
            "tracked_bytes_equal_freeze_commit_blob": True,
        }

    v1_preregistration_payload = _read_regular_file(
        root / v1.PREREGISTRATION_PATH, "v1 preregistration"
    )
    v1_preregistration = v1.parse_strict_json_bytes(
        v1_preregistration_payload, location="$.v1_preregistration"
    )
    v1_attempt_owner_payload = _read_regular_file(
        root / v1_failure.TRACKED_ATTEMPT_OWNER_PATH, "tracked v1 attempt owner"
    )
    v1_failure_classification_payload = _read_regular_file(
        root / v1_failure.ARTIFACT_PATH, "tracked v1 failure classification"
    )
    protocol.validate_preregistration(
        preregistration,
        v1_preregistration=v1_preregistration,
        source_receipts=source_receipts,
        v1_preregistration_payload=v1_preregistration_payload,
        v1_attempt_owner_payload=v1_attempt_owner_payload,
        v1_failure_classification_payload=v1_failure_classification_payload,
        output_absent=True,
    )

    owner_payload = _read_bound_artifact(
        root,
        TRACKED_ATTEMPT_OWNER_PATH,
        ATTEMPT_OWNER_BYTES,
        ATTEMPT_OWNER_SHA256,
        "attempt_owner",
    )
    progress_payload = _read_bound_artifact(
        root,
        TRACKED_PROGRESS_PATH,
        PROGRESS_BYTES,
        PROGRESS_SHA256,
        "progress",
    )
    failure_payload = _read_bound_artifact(
        root,
        TRACKED_FAILURE_PATH,
        FAILURE_BYTES,
        FAILURE_SHA256,
        "failure",
    )

    owner = protocol.parse_strict_json_bytes(owner_payload, location="$.attempt_owner")
    checked_owner = protocol.validate_attempt_owner(
        owner,
        protocol_freeze_commit=PROTOCOL_FREEZE_COMMIT,
        preregistration_payload=preregistration_payload,
    )
    if protocol.artifact_json_bytes(checked_owner) != owner_payload:
        _fail("ATTEMPT_OWNER_NOT_CANONICAL", "$.attempt_owner")
    events = protocol.validate_progress_journal(
        progress_payload,
        protocol_freeze_commit=PROTOCOL_FREEZE_COMMIT,
        preregistration_payload=preregistration_payload,
        attempt_owner_payload=owner_payload,
    )
    failure = protocol.parse_strict_json_bytes(failure_payload, location="$.failure")
    checked_failure = protocol.validate_failure(
        failure,
        protocol_freeze_commit=PROTOCOL_FREEZE_COMMIT,
        preregistration_payload=preregistration_payload,
        attempt_owner_payload=owner_payload,
        progress_payload=progress_payload,
        artifact_payloads={"evaluation_candidate": None, "predictions": None},
    )
    if protocol.artifact_json_bytes(checked_failure) != failure_payload:
        _fail("FAILURE_NOT_CANONICAL", "$.failure")
    _validate_observed_failure(events, checked_failure)
    return {
        "preregistration": preregistration,
        "preregistration_payload": preregistration_payload,
        "source_bindings": source_bindings,
        "owner": checked_owner,
        "owner_payload": owner_payload,
        "progress_events": events,
        "progress_payload": progress_payload,
        "failure": checked_failure,
        "failure_payload": failure_payload,
    }


def build_failure_classification(root: Path) -> dict[str, Any]:
    """Recompute the classification from frozen and tracked authenticated bytes."""

    context = load_tracked_failure_context(root)
    preregistration_payload = _bytes(context["preregistration_payload"])
    owner_payload = _bytes(context["owner_payload"])
    progress_payload = _bytes(context["progress_payload"])
    failure_payload = _bytes(context["failure_payload"])
    events = _object_sequence(context["progress_events"], "$.progress_events")
    failure = _mapping(context["failure"], "$.failure")
    terminal = _mapping(events[-1].get("terminal"), "$.progress.terminal")

    result: dict[str, Any] = {
        "mm005_browser_research_model_evaluation_failure_classification_version": (
            FAILURE_CLASSIFICATION_VERSION
        ),
        "gate_id": CLASSIFICATION_GATE_ID,
        "failed_gate_id": FAILED_GATE_ID,
        "experiment_id": protocol.EXPERIMENT_ID,
        "run_id": protocol.RUN_ID,
        "classified_at_utc": CLASSIFIED_AT_UTC,
        "protocol": {
            "definition_gate_id": protocol.PROTOCOL_GATE_ID,
            "freeze_commit": PROTOCOL_FREEZE_COMMIT,
            "freeze_blob_reader": "git_cat_file_blob",
            "preregistration": {
                "path": protocol.PREREGISTRATION_PATH,
                "bytes": len(preregistration_payload),
                "sha256": protocol.sha256_bytes(preregistration_payload),
                "canonical_json": True,
                "tracked_bytes_equal_freeze_commit_blob": True,
            },
            "source_bindings": context["source_bindings"],
            "source_binding_count": len(protocol.PROTOCOL_SOURCE_PATHS),
        },
        "raw_artifacts": {
            "attempt_owner": _artifact_binding(
                protocol.ATTEMPT_OWNER_PATH,
                TRACKED_ATTEMPT_OWNER_PATH,
                owner_payload,
                canonical_kind="json",
            ),
            "progress": {
                **_artifact_binding(
                    protocol.PROGRESS_PATH,
                    TRACKED_PROGRESS_PATH,
                    progress_payload,
                    canonical_kind="jsonl",
                ),
                "authenticated_event_count": len(events),
                "terminal_sequence": events[-1]["sequence"],
            },
            "failure": _artifact_binding(
                protocol.FAILURE_PATH,
                TRACKED_FAILURE_PATH,
                failure_payload,
                canonical_kind="json",
            ),
        },
        "attempt": {
            "experiment_attempt_ordinal": 1,
            "browser_research_model_evaluation_experiment_ordinal": 2,
            "owner_claim_completed": True,
            "attempt_consumed": True,
            "retry_allowed": False,
            "operator_retry_count": 0,
            "durable_terminal_state": "authenticated_failure",
            "directory_entries_observed": list(EXPECTED_LOCAL_ENTRIES),
            "progress_present": True,
            "evaluation_candidate_present": False,
            "predictions_present": False,
            "evidence_present": False,
            "failure_receipt_present": True,
            "attempt_id_repeated_in_classification": False,
        },
        "authenticated_progress": {
            "event_count": len(events),
            "terminal_sequence": events[-1]["sequence"],
            "last_event": events[-1]["event"],
            "interrupted_after_event": terminal["interrupted_after_event"],
            "active_record_id": events[-2]["record_id"],
            "active_record_durable_completion": False,
            "completed_record_ids": list(failure["completed_record_ids"]),
            "completed_record_count": len(failure["completed_record_ids"]),
            "counters": dict(_mapping(failure["counters"], "$.failure.counters")),
            "artifact_states": {
                "evaluation_candidate": None,
                "predictions": None,
            },
        },
        "failure": {
            "classification": (
                "generation_stage_runtime_error_after_three_completed_calls_"
                "before_fourth_completion"
            ),
            "category": (
                "generation_pipeline_runtime_failure_without_attributable_substage"
            ),
            "stage": failure["stage"],
            "exception_type": failure["exception_type"],
            "formal_runner_failure_receipt_available": True,
            "python_exception_handler_completed": True,
            "terminal_persistence_completed": True,
            "root_cause_authenticated": False,
            "failed_generation_substage_authenticated": False,
            "cuda_cause_attributed": False,
            "oom_or_resource_cap_cause_attributed": False,
            "gpu_or_driver_cause_attributed": False,
            "model_cause_attributed": False,
            "adapter_cause_attributed": False,
            "dataset_or_record_cause_attributed": False,
            "prompt_or_processor_cause_attributed": False,
            "compiler_or_verifier_cause_attributed": False,
            "runner_algorithm_cause_attributed": False,
        },
        "transient_non_authenticated_controller_observation": {
            "cuda_illegal_memory_access_text_seen": True,
            "captured_in_protocol_artifact": False,
            "exception_message_or_traceback_persisted": False,
            "formal_cause_derived_from_observation": False,
        },
        "evidence_policy": {
            "durable_authenticated_progress_only": True,
            "safe_exception_type_only": True,
            "exception_message_used_for_classification": False,
            "traceback_used_for_classification": False,
            "raw_outputs_available": False,
            "compiled_predictions_available": False,
            "metrics_available": False,
            "latency_or_resource_measurement_available": False,
            "missing_artifacts_reconstructed": False,
            "consumed_directory_deleted_reopened_or_overwritten": False,
        },
        "formal_gate_passed": False,
        "claims": {
            "evaluation_execution_attempted": True,
            "authenticated_partial_generation_progress": True,
            "fresh_base_load_completed": True,
            "independent_adapter_load_completed": True,
            "completed_generate_calls": 3,
            "fourth_generation_attempt_started": True,
            "attempt_consumed": True,
            "evaluation_executed": False,
            "formal_measurement_complete": False,
            "model_evaluated": False,
            "evaluation_result_available": False,
            "model_trained": False,
            "adapter_modified": False,
            "quality_established": False,
            "quality_improved": False,
            "generalized_quality_established": False,
            "safety_established": False,
            "evaluation_repeatability_established": False,
            "resource_repeatability_established": False,
            "cross_machine_reproducibility_established": False,
            "serving_eligible": False,
            "promotion_eligible": False,
            "runtime_eligible": False,
        },
        "locked_next_action": {
            "gate_id": NEXT_GATE_ID,
            "action": (
                "freeze a separate model-free investigation protocol that binds "
                "the v2 owner, progress, failure, and classification; statically "
                "isolates the fourth-record generation pipeline; and, only if "
                "still necessary, preregisters a new diagnostic experiment with "
                "fine-grained substage checkpoints before any model or CUDA run"
            ),
            "why_not_recovery_v3": (
                "durable recovery and terminal persistence succeeded, while no "
                "failed generation substage or remediating semantic delta is "
                "authenticated"
            ),
            "protocol_freeze_is_model_free": True,
            "model_or_cuda_execution_authorized_by_classification": False,
            "acceptance": {
                "v2_preregistration_bound": True,
                "v2_owner_progress_and_failure_bound": True,
                "v2_execution_not_retried": True,
                "fourth_record_static_input_and_message_diagnostics": True,
                "runtime_substage_attribution_not_inferred": True,
                "new_diagnostic_run_requires_separate_identity_output_and_merge": True,
                "diagnostic_checkpoints_precede_any_future_execution": True,
            },
            "constraints": {
                "v1_or_v2_artifacts_modified": False,
                "v2_execution_retried": False,
                "candidate_model_or_revision_changed": False,
                "adapter_changed": False,
                "dataset_or_case_order_changed": False,
                "prompt_compiler_verifier_or_metrics_changed": False,
                "quality_threshold_added": False,
                "training": False,
                "live_browser_or_network": False,
                "runtime_integration": False,
            },
        },
        "runtime_eligible": False,
    }
    result["report_digest"] = protocol.sha256_bytes(
        protocol.artifact_json_bytes(result)
    )
    return result


def validate_failure_classification(
    root: Path, value: Mapping[str, Any]
) -> dict[str, Any]:
    """Fail closed unless the derived classification exactly recomputes."""

    expected = build_failure_classification(root)
    if protocol.artifact_json_bytes(dict(value)) != protocol.artifact_json_bytes(
        expected
    ):
        _fail("FAILURE_CLASSIFICATION_MISMATCH", "$.failure_classification")
    return expected


def verify_local_consumed_tree_if_present(root: Path) -> dict[str, Any]:
    """Verify ignored terminal bytes under the released lifecycle lease when present."""

    context = load_tracked_failure_context(root)
    output_directory = root / protocol.RUN_OUTPUT_ROOT
    lifecycle_root = root / protocol.LIFECYCLE_LEASE_ROOT
    output_exists = os.path.lexists(output_directory)
    lifecycle_exists = os.path.lexists(lifecycle_root)
    if not output_exists and not lifecycle_exists:
        return {
            "local_directory_present": False,
            "lifecycle_present": False,
            "expected_entries": list(EXPECTED_LOCAL_ENTRIES),
            "tracked_artifacts_valid": True,
        }
    if output_exists is not True or lifecycle_exists is not True:
        _fail("LOCAL_LIFECYCLE_TOPOLOGY_MISMATCH", "$.local_attempt")

    tracked_payloads = {
        "attempt_owner": _bytes(context["owner_payload"]),
        "progress": _bytes(context["progress_payload"]),
        "failure": _bytes(context["failure_payload"]),
    }
    recovery_io.validate_lock_file(
        root / protocol.LIFECYCLE_LEASE_PATH, protocol.LIFECYCLE_LEASE_MARKER
    )
    with recovery_io.ProgressLease(root / protocol.LIFECYCLE_LEASE_PATH) as lifecycle:
        lifecycle.verify()
        guard = recovery_io.DirectoryTreeGuard(root, output_directory)
        entries = sorted(path.name for path in output_directory.iterdir())
        if entries != list(EXPECTED_LOCAL_ENTRIES):
            _fail("UNEXPECTED_LOCAL_ATTEMPT_ENTRIES", "$.local_attempt.directory")
        for name, local_relative in _RAW_LOCAL_PATHS.items():
            local_payload = recovery_io.read_regular_file(
                root / local_relative, max_bytes=_MAX_BOUND_FILE_BYTES
            )
            if local_payload != tracked_payloads[name]:
                _fail("LOCAL_TRACKED_ARTIFACT_MISMATCH", f"$.local_attempt.{name}")
        guard.verify()
        lifecycle.verify()
    return {
        "local_directory_present": True,
        "lifecycle_present": True,
        "expected_entries": list(EXPECTED_LOCAL_ENTRIES),
        "tracked_artifacts_valid": True,
    }


def _validate_observed_failure(
    events: Sequence[Mapping[str, Any]], failure: Mapping[str, Any]
) -> None:
    if (
        len(events) != EXPECTED_EVENT_COUNT
        or events[-1].get("sequence") != EXPECTED_TERMINAL_SEQUENCE
        or events[-1].get("event") != "failure_terminal_ready"
        or events[-2].get("event") != "generation_started"
        or events[-2].get("record_id") != FAILED_RECORD_ID
        or list(failure.get("completed_record_ids", [])) != list(COMPLETED_RECORD_IDS)
        or dict(_mapping(failure.get("counters"), "$.failure.counters"))
        != EXPECTED_COUNTERS
        or failure.get("stage") != "generation"
        or failure.get("exception_type") != "RuntimeError"
        or failure.get("next_gate") != CLASSIFICATION_GATE_ID
    ):
        _fail("OBSERVED_FAILURE_BOUNDARY_MISMATCH", "$.failure")
    terminal_recovery = _mapping(
        failure.get("terminal_recovery"), "$.failure.terminal_recovery"
    )
    claims = _mapping(failure.get("claims"), "$.failure.claims")
    artifacts = _mapping(failure.get("artifacts"), "$.failure.artifacts")
    if (
        terminal_recovery.get("external_controller_interruption") is not False
        or terminal_recovery.get("interrupted_after_event") != "generation_started"
        or terminal_recovery.get("discarded_progress_tail") is not None
        or terminal_recovery.get("model_execution_retried") is not False
        or artifacts.get("evaluation_candidate") is not None
        or artifacts.get("predictions") is not None
        or claims.get("attempt_consumed") is not True
        or claims.get("evaluation_executed") is not False
        or claims.get("formal_measurement_complete") is not False
        or claims.get("model_evaluated") is not False
    ):
        _fail("OBSERVED_FAILURE_CLAIMS_MISMATCH", "$.failure")


def _artifact_binding(
    source_path: str,
    tracked_path: str,
    payload: bytes,
    *,
    canonical_kind: str,
) -> dict[str, Any]:
    return {
        "source_path": source_path,
        "path": tracked_path,
        "bytes": len(payload),
        "sha256": protocol.sha256_bytes(payload),
        "canonical_json": canonical_kind == "json",
        "canonical_jsonl": canonical_kind == "jsonl",
        "contract_valid": True,
        "attempt_id_repeated_in_classification": False,
    }


def _read_bound_artifact(
    root: Path,
    relative: str,
    expected_bytes: int,
    expected_sha256: str,
    label: str,
) -> bytes:
    payload = _read_regular_file(root / relative, f"tracked {label}")
    if (
        len(payload) != expected_bytes
        or protocol.sha256_bytes(payload) != expected_sha256
    ):
        _fail("TRACKED_ARTIFACT_BINDING_MISMATCH", f"$.raw_artifacts.{label}")
    return payload


def _receipt(path: str, payload: bytes) -> dict[str, Any]:
    return {
        "path": path,
        "bytes": len(payload),
        "sha256": protocol.sha256_bytes(payload),
    }


def _require_git_commit(root: Path, commit: str) -> None:
    if re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        _fail("GIT_COMMIT_INVALID", "$.protocol.freeze_commit")
    try:
        completed = subprocess.run(
            ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
            cwd=root,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise protocol.MM005BrowserResearchRecoveryError(
            "GIT_COMMIT_READ_FAILED", "$.protocol.freeze_commit"
        ) from exc
    if completed.returncode != 0:
        _fail("GIT_COMMIT_MISSING", "$.protocol.freeze_commit")


def _read_git_blob(root: Path, commit: str, relative_path: str) -> bytes:
    path = PurePosixPath(relative_path)
    if (
        not relative_path
        or "\\" in relative_path
        or path.is_absolute()
        or ".." in path.parts
    ):
        _fail("GIT_BLOB_PATH_INVALID", "$.protocol.source")
    try:
        completed = subprocess.run(
            ["git", "cat-file", "blob", f"{commit}:{relative_path}"],
            cwd=root,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise protocol.MM005BrowserResearchRecoveryError(
            "GIT_BLOB_READ_FAILED", "$.protocol.source"
        ) from exc
    if completed.returncode != 0 or len(completed.stdout) > 64 * 1024 * 1024:
        _fail("GIT_BLOB_READ_FAILED", "$.protocol.source")
    return completed.stdout


def _read_regular_file(path: Path, label: str) -> bytes:
    try:
        metadata = path.lstat()
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise protocol.MM005BrowserResearchRecoveryError(
            "MISSING_BOUND_FILE", f"$.{label}"
        ) from exc
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    if (
        not stat.S_ISREG(metadata.st_mode)
        or path.is_symlink()
        or bool(getattr(metadata, "st_file_attributes", 0) & reparse_flag)
        or metadata.st_nlink != 1
        or os.path.normcase(str(resolved)) != os.path.normcase(os.path.abspath(path))
    ):
        _fail("UNSAFE_BOUND_FILE", f"$.{label}")
    payload = resolved.read_bytes()
    if len(payload) > _MAX_BOUND_FILE_BYTES:
        _fail("BOUND_FILE_OVERSIZED", f"$.{label}")
    return payload


def _mapping(value: object, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        _fail("OBJECT_REQUIRED", location)
    return value


def _object_sequence(value: object, location: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        _fail("ARRAY_REQUIRED", location)
    return [_mapping(item, f"{location}[{index}]") for index, item in enumerate(value)]


def _bytes(value: object) -> bytes:
    if not isinstance(value, bytes):
        _fail("BYTES_REQUIRED", "$.internal")
    return value


def _fail(code: str, location: str) -> NoReturn:
    raise protocol.MM005BrowserResearchRecoveryError(code, location)


__all__ = [
    "ARTIFACT_PATH",
    "ATTEMPT_OWNER_BYTES",
    "ATTEMPT_OWNER_SHA256",
    "CLASSIFICATION_GATE_ID",
    "COMPLETED_RECORD_IDS",
    "EXPECTED_COUNTERS",
    "EXPECTED_EVENT_COUNT",
    "EXPECTED_LOCAL_ENTRIES",
    "FAILED_GATE_ID",
    "FAILED_RECORD_ID",
    "FAILURE_BYTES",
    "FAILURE_CLASSIFICATION_VERSION",
    "FAILURE_SHA256",
    "NEXT_GATE_ID",
    "PREREGISTRATION_BYTES",
    "PREREGISTRATION_SHA256",
    "PROGRESS_BYTES",
    "PROGRESS_SHA256",
    "PROTOCOL_FREEZE_COMMIT",
    "TRACKED_ATTEMPT_OWNER_PATH",
    "TRACKED_FAILURE_PATH",
    "TRACKED_PROGRESS_PATH",
    "build_failure_classification",
    "load_tracked_failure_context",
    "validate_failure_classification",
    "verify_local_consumed_tree_if_present",
]
