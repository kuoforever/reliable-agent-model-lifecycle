"""Model-free classification of the consumed MM-005 Browser eval v1 attempt."""

from __future__ import annotations

import os
import re
import stat
import subprocess
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any, NoReturn

from . import mm005_browser_research_model_evaluation as protocol

FAILURE_CLASSIFICATION_VERSION = 1
CLASSIFICATION_GATE_ID = protocol.FAILURE_CLASSIFICATION_GATE_ID
FAILED_GATE_ID = protocol.EXECUTION_GATE_ID
NEXT_GATE_ID = "MM-005-browser-research-model-evaluation-recovery-protocol-v2"
RECOVERY_EXECUTION_GATE_ID = (
    "MM-005-browser-research-model-evaluation-execution-v2"
)
RECOVERY_FAILURE_CLASSIFICATION_GATE_ID = (
    "MM-005-browser-research-model-evaluation-failure-classification-v2"
)
RECOVERY_RESULT_REVIEW_GATE_ID = (
    "MM-005-browser-research-model-evaluation-result-review-v2"
)
RECOVERY_EXPERIMENT_ID = "mm005-browser-research-model-eval-v2"
RECOVERY_RUN_ID = "mm005-browser-research-model-eval-r2"
RECOVERY_OUTPUT_DIRECTORY = (
    "work/evaluation-runs/mm005-browser-research-model-eval-v2"
)
PROTOCOL_FREEZE_COMMIT = "7af879457bd55c9b3f6b4f7abf33e43ed181c2e9"
PREREGISTRATION_BYTES = 116_152
PREREGISTRATION_SHA256 = (
    "sha256:84cd3d20d5a678a8ad0f7c38ad12e057225a4250e8143c5f004c2eaef8981f3f"
)
TRACKED_ATTEMPT_OWNER_PATH = (
    "baseline/mm005-browser-research-model-eval-v1-attempt-owner.json"
)
LOCAL_ATTEMPT_OWNER_PATH = protocol.ATTEMPT_OWNER_PATH
ATTEMPT_OWNER_BYTES = 649
ATTEMPT_OWNER_SHA256 = (
    "sha256:c5649806987521be26304e6abf81d545ab2522d71289d700d2c49305828b9ca6"
)
ARTIFACT_PATH = (
    "baseline/mm005-browser-research-model-eval-v1-failure-classification.json"
)
CLASSIFIED_AT_UTC = "2026-08-27T09:41:01Z"
EXPECTED_LOCAL_ENTRIES = (Path(LOCAL_ATTEMPT_OWNER_PATH).name,)
_MAX_BOUND_FILE_BYTES = 4 * 1024 * 1024


def build_failure_classification(root: Path) -> dict[str, Any]:
    """Rebuild the classification from frozen protocol and tracked owner bytes."""

    preregistration_payload = _read_regular_file(
        root / protocol.PREREGISTRATION_PATH,
        "MM-005 Browser Research model-evaluation v1 preregistration",
    )
    if (
        len(preregistration_payload) != PREREGISTRATION_BYTES
        or protocol.sha256_bytes(preregistration_payload)
        != PREREGISTRATION_SHA256
    ):
        _fail("PREREGISTRATION_BINDING_MISMATCH", "$.protocol.preregistration")

    _require_git_commit(root, PROTOCOL_FREEZE_COMMIT)
    frozen_preregistration = _read_git_blob(
        root, PROTOCOL_FREEZE_COMMIT, protocol.PREREGISTRATION_PATH
    )
    if frozen_preregistration != preregistration_payload:
        _fail("FROZEN_PREREGISTRATION_MISMATCH", "$.protocol.preregistration")

    preregistration = protocol.parse_strict_json_bytes(
        preregistration_payload,
        location="$.protocol.preregistration",
    )
    if protocol.artifact_json_bytes(preregistration) != preregistration_payload:
        _fail("PREREGISTRATION_NOT_CANONICAL", "$.protocol.preregistration")
    _validate_protocol_boundary(preregistration)
    source_bindings = _source_bindings(root, preregistration)
    owner_binding = _tracked_owner_binding(root, preregistration_payload)

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
            "core_longpaths_setting_required": False,
            "preregistration": {
                "path": protocol.PREREGISTRATION_PATH,
                "bytes": len(preregistration_payload),
                "sha256": protocol.sha256_bytes(preregistration_payload),
                "tracked_bytes_equal_freeze_commit_blob": True,
                "canonical_json": True,
            },
            "source_bindings": source_bindings,
            "source_binding_count": len(source_bindings),
        },
        "attempt_owner": owner_binding,
        "attempt": {
            "attempt_ordinal": 1,
            "owner_claim_completed": True,
            "attempt_consumed": True,
            "retry_allowed": False,
            "operator_retry_count": 0,
            "durable_terminal_state_at_classification": "owner_only",
            "directory_entries_observed": list(EXPECTED_LOCAL_ENTRIES),
            "evaluation_candidate_present": False,
            "predictions_present": False,
            "evidence_present": False,
            "failure_receipt_present": False,
            "authenticated_failure_stage": None,
            "authenticated_exception_type": None,
            "exact_execution_counters_available": False,
            "exact_completed_record_ids_available": False,
            "exact_model_load_completion_available": False,
            "exact_generate_call_completion_available": False,
            "exact_execution_progress": "unknown",
        },
        "failure": {
            "classification": (
                "external_controller_interruption_after_owner_claim_before_"
                "terminal_persistence"
            ),
            "category": (
                "controller_lifecycle_interruption_and_terminal_persistence"
            ),
            "cause_basis": (
                "controller-observed process interruption correlated with the "
                "authenticated owner-only durable state"
            ),
            "cause_authenticated_by_formal_runner": False,
            "formal_runner_failure_receipt_available": False,
            "python_exception_handler_completed": False,
            "terminal_persistence_completed": False,
            "model_or_output_quality_cause_attributed": False,
            "dataset_cause_attributed": False,
            "adapter_cause_attributed": False,
            "compiler_cause_attributed": False,
            "verifier_cause_attributed": False,
            "cuda_cause_attributed": False,
            "resource_cap_cause_attributed": False,
            "runner_algorithm_cause_attributed": False,
        },
        "separate_preconsumption_event": {
            "classification": "windows_git_show_long_path_read_failure",
            "owner_claimed": False,
            "attempt_consumed": False,
            "model_imported": False,
            "model_called": False,
            "corrected_before_consumed_attempt": True,
            "freeze_validation_repassed_before_consumed_attempt": True,
            "part_of_consumed_failure": False,
            "evidence_basis": "controller_observation_not_formal_telemetry",
        },
        "evidence_policy": {
            "durable_authenticated_facts": [
                "v1 preregistration equals its freeze-commit Git blob",
                "all v1 protocol sources equal their freeze-commit Git blobs",
                "tracked attempt owner is canonical and contract-valid",
                "attempt owner claims attempt_consumed true and retry_allowed false",
                "the observed local run directory was owner-only",
            ],
            "transient_non_authenticated_controller_observation": {
                "checkpoint_shard_loading_output_seen": True,
                "gpu_compute_seen": True,
                "formal_progress_derived_from_observation": False,
                "model_load_completion_claimed": False,
                "generate_call_count_claimed": False,
            },
            "formal_model_evaluated_false_semantics": (
                "no complete authenticated formal measurement exists; this is "
                "not proof that no process-local model activity occurred"
            ),
            "raw_outputs_reconstructed": False,
            "compiled_predictions_reconstructed": False,
            "metrics_reconstructed": False,
            "latency_or_resources_reconstructed": False,
            "failure_receipt_synthesized_in_v1_directory": False,
            "v1_directory_deleted_reopened_or_overwritten": False,
        },
        "reconstruction_scope": {
            "classification_recomputable_from_tracked_inputs": True,
            "freeze_commit_source_conformance_checked": True,
            "local_owner_tree_checked_when_present": True,
            "model_evaluation_repeatability_established": False,
            "training_repeatability_established": False,
            "resource_repeatability_established": False,
            "cross_machine_reproducibility_established": False,
        },
        "formal_gate_passed": False,
        "claims": {
            "evaluation_execution_attempted": True,
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
            "training_repeatability_established": False,
            "resource_repeatability_established": False,
            "cross_machine_reproducibility_established": False,
            "serving_eligible": False,
            "promotion_eligible": False,
            "runtime_eligible": False,
        },
        "locked_next_action": _locked_recovery_action(
            preregistration_payload, owner_binding
        ),
        "runtime_eligible": False,
    }
    result["report_digest"] = protocol.sha256_bytes(
        protocol.artifact_json_bytes(result)
    )
    return result


def validate_failure_classification(
    root: Path, value: Mapping[str, Any]
) -> dict[str, Any]:
    """Fail closed unless the classification exactly recomputes."""

    expected = build_failure_classification(root)
    if dict(value) != expected:
        _fail("FAILURE_CLASSIFICATION_MISMATCH", "$.failure_classification")
    return expected


def verify_local_attempt_owner_if_present(root: Path) -> dict[str, Any]:
    """Verify the ignored owner-only tree when it exists; permit clean CI absence."""

    preregistration_payload = _read_regular_file(
        root / protocol.PREREGISTRATION_PATH,
        "MM-005 Browser Research model-evaluation v1 preregistration",
    )
    binding = _tracked_owner_binding(root, preregistration_payload)
    output_directory = root / protocol.RUN_OUTPUT_ROOT
    if not os.path.lexists(output_directory):
        return {
            "local_directory_present": False,
            "expected_entries": list(EXPECTED_LOCAL_ENTRIES),
            "tracked_owner_valid": True,
            "owner": binding,
        }
    _assert_safe_directory(output_directory, "$.local_attempt.directory")
    entries = sorted(path.name for path in output_directory.iterdir())
    if entries != list(EXPECTED_LOCAL_ENTRIES):
        _fail("UNEXPECTED_LOCAL_ATTEMPT_ENTRIES", "$.local_attempt.directory")
    local_owner = _read_regular_file(
        root / LOCAL_ATTEMPT_OWNER_PATH,
        "local MM-005 Browser Research attempt owner",
    )
    tracked_owner = _read_regular_file(
        root / TRACKED_ATTEMPT_OWNER_PATH,
        "tracked MM-005 Browser Research attempt owner",
    )
    if local_owner != tracked_owner:
        _fail("LOCAL_TRACKED_OWNER_MISMATCH", "$.local_attempt.owner")
    return {
        "local_directory_present": True,
        "expected_entries": list(EXPECTED_LOCAL_ENTRIES),
        "tracked_owner_valid": True,
        "owner": binding,
    }


def _source_bindings(
    root: Path, preregistration: Mapping[str, Any]
) -> dict[str, dict[str, Any]]:
    receipts = _mapping(preregistration.get("source_receipts"), "$.source_receipts")
    if set(receipts) != set(protocol.PROTOCOL_SOURCE_PATHS):
        _fail("PROTOCOL_SOURCE_SET_MISMATCH", "$.source_receipts")
    bindings: dict[str, dict[str, Any]] = {}
    for name, relative in sorted(protocol.PROTOCOL_SOURCE_PATHS.items()):
        payload = _read_regular_file(root / relative, f"v1 protocol source {name}")
        frozen_payload = _read_git_blob(root, PROTOCOL_FREEZE_COMMIT, relative)
        if payload != frozen_payload:
            _fail("FROZEN_PROTOCOL_SOURCE_MISMATCH", f"$.source_bindings.{name}")
        expected = {
            "path": relative,
            "bytes": len(payload),
            "sha256": protocol.sha256_bytes(payload),
        }
        receipt = _mapping(receipts.get(name), f"$.source_receipts.{name}")
        if dict(receipt) != expected:
            _fail("PROTOCOL_SOURCE_RECEIPT_MISMATCH", f"$.source_bindings.{name}")
        bindings[name] = {
            **expected,
            "tracked_bytes_equal_freeze_commit_blob": True,
        }
    return bindings


def _tracked_owner_binding(
    root: Path, preregistration_payload: bytes
) -> dict[str, Any]:
    payload = _read_regular_file(
        root / TRACKED_ATTEMPT_OWNER_PATH,
        "tracked MM-005 Browser Research attempt owner",
    )
    if (
        len(payload) != ATTEMPT_OWNER_BYTES
        or protocol.sha256_bytes(payload) != ATTEMPT_OWNER_SHA256
    ):
        _fail("ATTEMPT_OWNER_BINDING_MISMATCH", "$.attempt_owner")
    raw = protocol.parse_strict_json_bytes(payload, location="$.attempt_owner")
    validated = protocol.validate_attempt_owner(
        raw,
        protocol_freeze_commit=PROTOCOL_FREEZE_COMMIT,
        preregistration_payload=preregistration_payload,
    )
    if protocol.artifact_json_bytes(validated) != payload:
        _fail("ATTEMPT_OWNER_NOT_CANONICAL", "$.attempt_owner")
    claims = _mapping(validated.get("claims"), "$.attempt_owner.claims")
    if (
        claims.get("attempt_consumed") is not True
        or claims.get("retry_allowed") is not False
        or claims.get("model_output_has_execution_authority") is not False
        or claims.get("runtime_eligible") is not False
    ):
        _fail("ATTEMPT_OWNER_CLAIMS_MISMATCH", "$.attempt_owner.claims")
    return {
        "source_path": LOCAL_ATTEMPT_OWNER_PATH,
        "path": TRACKED_ATTEMPT_OWNER_PATH,
        "bytes": len(payload),
        "sha256": protocol.sha256_bytes(payload),
        "canonical_json": True,
        "contract_valid": True,
        "attempt_id_repeated_in_classification": False,
        "claims": dict(claims),
    }


def _validate_protocol_boundary(preregistration: Mapping[str, Any]) -> None:
    execution = _mapping(
        preregistration.get("execution_protocol"), "$.execution_protocol"
    )
    consumption = _mapping(
        execution.get("attempt_consumption"),
        "$.execution_protocol.attempt_consumption",
    )
    outputs = _mapping(preregistration.get("outputs"), "$.outputs")
    failure_contract = _mapping(
        preregistration.get("failure_receipt_contract"),
        "$.failure_receipt_contract",
    )
    claims = _mapping(preregistration.get("claims"), "$.claims")
    if (
        preregistration.get("gate_id") != protocol.PROTOCOL_GATE_ID
        or preregistration.get("next_gate") != protocol.EXECUTION_GATE_ID
        or preregistration.get("experiment_id") != protocol.EXPERIMENT_ID
        or preregistration.get("freeze_status") != "frozen"
        or outputs.get("output_directory") != protocol.RUN_OUTPUT_ROOT
        or outputs.get("attempt_owner") != protocol.ATTEMPT_OWNER_PATH
        or outputs.get("failure") != protocol.FAILURE_PATH
        or failure_contract.get("next_gate")
        != protocol.FAILURE_CLASSIFICATION_GATE_ID
        or consumption
        != {
            "consumed_when": "owner_marked_directory_atomically_claimed",
            "retry_allowed_before_consumption": True,
            "retry_allowed_after_consumption": False,
        }
        or claims.get("attempt_consumed") is not False
        or claims.get("evaluation_executed") is not False
        or claims.get("model_evaluated") is not False
        or claims.get("formal_measurement_complete") is not False
    ):
        _fail("PREREGISTRATION_BOUNDARY_MISMATCH", "$.protocol.preregistration")


def _locked_recovery_action(
    preregistration_payload: bytes, owner_binding: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "gate_id": NEXT_GATE_ID,
        "execution_gate_id": RECOVERY_EXECUTION_GATE_ID,
        "failure_classification_gate_id": RECOVERY_FAILURE_CLASSIFICATION_GATE_ID,
        "result_review_gate_id": RECOVERY_RESULT_REVIEW_GATE_ID,
        "experiment_id": RECOVERY_EXPERIMENT_ID,
        "run_id": RECOVERY_RUN_ID,
        "output_directory": RECOVERY_OUTPUT_DIRECTORY,
        "new_experiment_not_v1_retry": True,
        "lineage_requirements": {
            "v1_preregistration": {
                "path": protocol.PREREGISTRATION_PATH,
                "bytes": len(preregistration_payload),
                "sha256": protocol.sha256_bytes(preregistration_payload),
            },
            "v1_attempt_owner": {
                "path": owner_binding["path"],
                "bytes": owner_binding["bytes"],
                "sha256": owner_binding["sha256"],
            },
            "v1_failure_classification": {
                "path": ARTIFACT_PATH,
                "file_receipt_required_at_v2_freeze": True,
                "report_digest_required_at_v2_freeze": True,
            },
        },
        "v1_subtrees_exactly_preserved": [
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
        ],
        "required_v2_values": {
            "mm005_browser_research_model_evaluation_protocol_version": 2,
            "gate_id": NEXT_GATE_ID,
            "experiment_id": RECOVERY_EXPERIMENT_ID,
            "run_id": RECOVERY_RUN_ID,
            "next_gate": RECOVERY_EXECUTION_GATE_ID,
            "success_next_gate": RECOVERY_RESULT_REVIEW_GATE_ID,
            "failure_receipt_contract.next_gate": (
                RECOVERY_FAILURE_CLASSIFICATION_GATE_ID
            ),
            "outputs.output_directory": RECOVERY_OUTPUT_DIRECTORY,
            "outputs.attempt_owner": (
                f"{RECOVERY_OUTPUT_DIRECTORY}/attempt-owner.json"
            ),
            "outputs.progress": f"{RECOVERY_OUTPUT_DIRECTORY}/progress.json",
            "outputs.evaluation_candidate": (
                f"{RECOVERY_OUTPUT_DIRECTORY}/evaluation-candidate.json"
            ),
            "outputs.predictions": f"{RECOVERY_OUTPUT_DIRECTORY}/predictions.json",
            "outputs.evidence": f"{RECOVERY_OUTPUT_DIRECTORY}/evidence.json",
            "outputs.failure": f"{RECOVERY_OUTPUT_DIRECTORY}/failure.json",
            "freeze_blob_reader.command": "git cat-file blob <commit>:<path>",
            "freeze_blob_reader.depends_on_core_longpaths": False,
        },
        "allowed_v2_differences": {
            "identity_and_output_path_replacements": True,
            "source_receipt_closure_for_v2_code_and_v1_lineage": True,
            "git_blob_reader_replaces_git_show_path_read": True,
            "durable_progress_checkpoint_contract": True,
            "model_free_terminal_recovery_after_external_interruption": True,
            "formal_gate_additions": [
                "long_path_safe_freeze_blob_read",
                "durable_progress_persistence",
                "interruption_terminal_recovery",
            ],
            "other_candidate_data_prompt_verifier_metric_or_resource_changes": False,
        },
        "constraints": {
            "v1_directory_deleted": False,
            "v1_directory_reopened": False,
            "v1_owner_rewritten": False,
            "v1_failure_receipt_synthesized": False,
            "v1_execution_retried": False,
            "model_or_revision_changed": False,
            "adapter_changed": False,
            "dataset_or_case_order_changed": False,
            "prompt_or_compiler_changed": False,
            "verifier_or_metrics_changed": False,
            "seed_or_generation_changed": False,
            "resource_caps_changed": False,
            "training_added": False,
            "live_browser_or_network_added": False,
            "runtime_integration": False,
        },
    }


def _require_git_commit(root: Path, commit: str) -> None:
    if re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        _fail("GIT_COMMIT_INVALID", "$.protocol.freeze_commit")
    try:
        completed = subprocess.run(
            ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
            cwd=root,
            check=False,
            capture_output=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise protocol.MM005ModelEvaluationError(
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
            capture_output=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise protocol.MM005ModelEvaluationError(
            "GIT_BLOB_READ_FAILED", "$.protocol.source"
        ) from exc
    if completed.returncode != 0 or len(completed.stdout) > _MAX_BOUND_FILE_BYTES:
        _fail("GIT_BLOB_READ_FAILED", "$.protocol.source")
    return completed.stdout


def _assert_safe_directory(path: Path, location: str) -> None:
    try:
        metadata = path.lstat()
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise protocol.MM005ModelEvaluationError(
            "UNSAFE_BOUND_DIRECTORY", location
        ) from exc
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or path.is_symlink()
        or bool(getattr(metadata, "st_file_attributes", 0) & reparse_flag)
        or os.path.normcase(str(resolved))
        != os.path.normcase(os.path.abspath(path))
    ):
        _fail("UNSAFE_BOUND_DIRECTORY", location)


def _read_regular_file(path: Path, label: str) -> bytes:
    try:
        metadata = path.lstat()
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise protocol.MM005ModelEvaluationError(
            "MISSING_BOUND_FILE", f"$.{label}"
        ) from exc
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    if (
        not stat.S_ISREG(metadata.st_mode)
        or path.is_symlink()
        or bool(getattr(metadata, "st_file_attributes", 0) & reparse_flag)
        or metadata.st_nlink != 1
        or os.path.normcase(str(resolved))
        != os.path.normcase(os.path.abspath(path))
    ):
        _fail("UNSAFE_BOUND_FILE", f"$.{label}")
    payload = resolved.read_bytes()
    if len(payload) > _MAX_BOUND_FILE_BYTES:
        _fail("BOUND_FILE_OVERSIZED", f"$.{label}")
    return payload


def _mapping(value: object, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or any(
        not isinstance(key, str) for key in value
    ):
        _fail("OBJECT_REQUIRED", location)
    return value


def _fail(code: str, location: str) -> NoReturn:
    raise protocol.MM005ModelEvaluationError(code, location)


__all__ = [
    "ARTIFACT_PATH",
    "ATTEMPT_OWNER_BYTES",
    "ATTEMPT_OWNER_SHA256",
    "CLASSIFICATION_GATE_ID",
    "EXPECTED_LOCAL_ENTRIES",
    "FAILED_GATE_ID",
    "FAILURE_CLASSIFICATION_VERSION",
    "LOCAL_ATTEMPT_OWNER_PATH",
    "NEXT_GATE_ID",
    "PROTOCOL_FREEZE_COMMIT",
    "RECOVERY_EXECUTION_GATE_ID",
    "RECOVERY_EXPERIMENT_ID",
    "RECOVERY_FAILURE_CLASSIFICATION_GATE_ID",
    "RECOVERY_OUTPUT_DIRECTORY",
    "RECOVERY_RESULT_REVIEW_GATE_ID",
    "RECOVERY_RUN_ID",
    "TRACKED_ATTEMPT_OWNER_PATH",
    "build_failure_classification",
    "validate_failure_classification",
    "verify_local_attempt_owner_if_present",
]
