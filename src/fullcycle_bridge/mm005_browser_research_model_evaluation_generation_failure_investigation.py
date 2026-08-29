"""Model-free preregistration for the MM-005 Browser eval v2 investigation."""

from __future__ import annotations

import hashlib
import json
import struct
from collections.abc import Mapping, Sequence
from typing import Any, NoReturn

from . import mm005_browser_research_adapter_verifier as adapter_verifier
from . import mm005_browser_research_model_evaluation as v1
from . import (
    mm005_browser_research_model_evaluation_failure_classification_v2 as failure,
)
from . import mm005_browser_research_model_evaluation_protocol_v2 as v2

PROTOCOL_VERSION = 1
GATE_ID = failure.NEXT_GATE_ID
INVESTIGATION_ID = "mm005-browser-research-model-eval-v2-generation-failure-static-v1"
INVESTIGATION_GATE_ID = (
    "MM-005-browser-research-model-evaluation-generation-failure-investigation-v1"
)
CLASSIFICATION_MERGE_COMMIT = "e52060ff82b62f6042ec371b72f011e5fa5c0681"

PREREGISTRATION_PATH = (
    "configs/mm005_browser_research_model_evaluation_generation_failure_"
    "investigation_protocol_v1.json"
)
RESULT_PATH = (
    "baseline/mm005-browser-research-model-eval-v2-generation-failure-"
    "investigation-v1.json"
)

CLASSIFICATION_BYTES = 11_920
CLASSIFICATION_SHA256 = (
    "sha256:169c78c7337eca32de8769c8598b9f514e2acc33a04ec50a0fdc4bc5a3895197"
)
CLASSIFICATION_REPORT_DIGEST = (
    "sha256:425bcf20cdab6a70d2bf67ed9bdbd19bddc3c9020bdd99800fedac8d6c9bcbe1"
)
TARGET_RECORD_ID = failure.FAILED_RECORD_ID
TARGET_CASE_ORDER_INDEX = 3
TARGET_DATASET_RECORD_INDEX = 17
TARGET_TEMPLATE_ID = "mm005-browser-cross-comparison-06"
TARGET_SPLIT = "train"
TARGET_TASK_FAMILY = "cross_source_comparison_citation"
TARGET_SOURCE_KIND = "synthetic_comparison_source_bundle"
TARGET_SOURCE_COUNT = 3

COMPLETED_PREFIX_CONTROL_IDS = failure.COMPLETED_RECORD_IDS
SAME_SHAPE_CONTROL_IDS = (
    "sha256:7cf64b00eaa41d8441acbe4cf44192cba08c4c8034a5897be1d61f934e8ce099",
    "sha256:c4841dcbf483a0e85d2580c429bdffd64d000ee047247849357f478619a2d5fd",
    "sha256:d3d546ecc5e3ce15c05b85447f90a291573d057beb2be9bfefb4d752e452ab92",
)

PROTOCOL_SOURCE_PATHS = {
    "adapter_verifier": (
        "src/fullcycle_bridge/mm005_browser_research_adapter_verifier.py"
    ),
    "browser_data_contract": "src/fullcycle_bridge/mm005_browser_research_data.py",
    "failure_classification_v2": (
        "src/fullcycle_bridge/"
        "mm005_browser_research_model_evaluation_failure_classification_v2.py"
    ),
    "investigation_builder": (
        "scripts/prepare_mm005_browser_research_model_evaluation_generation_"
        "failure_investigation_protocol_v1.py"
    ),
    "investigation_contract": (
        "src/fullcycle_bridge/"
        "mm005_browser_research_model_evaluation_generation_failure_"
        "investigation.py"
    ),
    "model_evaluation_contract_v1": (
        "src/fullcycle_bridge/mm005_browser_research_model_evaluation.py"
    ),
    "recovery_contract_v2": (
        "src/fullcycle_bridge/mm005_browser_research_model_evaluation_protocol_v2.py"
    ),
    "recovery_protocol_builder_v2": (
        "scripts/prepare_mm005_browser_research_model_evaluation_v2.py"
    ),
    "shared_generation_helper": "scripts/run_mm003_multimodal_gui_action_baseline.py",
    "v2_runner": "scripts/run_mm005_browser_research_model_evaluation_v2.py",
}

STATIC_DIAGNOSTIC_STEPS = (
    "validate_published_failure_lineage_and_raw_terminal_artifacts",
    "rebuild_frozen_dataset_and_artifact_context",
    "select_exact_fourth_record_and_frozen_controls",
    "recompute_record_and_artifact_receipts",
    "recompute_adapter_projection_and_gold_path_isolation",
    "recompute_model_payload_and_prompt_projection",
    "recompute_runtime_message_transport_shape_with_opaque_image_sentinels",
    "verify_frozen_runner_control_flow_boundary",
    "apply_outcome_neutral_static_decision_rubric",
)

HISTORICAL_GENERATION_STAGE_ORDER = (
    "record_adaptation_completed",
    "image_open_and_rgb_conversion_completed",
    "generation_started_checkpoint_durably_persisted",
    "runtime_messages_build",
    "pre_generation_cuda_synchronize",
    "chat_template_render",
    "processor_tensorization",
    "processor_device_transfer",
    "model_generate",
    "output_trim_and_decode",
    "post_generation_cuda_synchronize",
    "case_result_build",
    "generation_completed_checkpoint",
)

FUTURE_DIAGNOSTIC_CHECKPOINT_REQUIREMENTS = (
    "runtime_messages_build_started",
    "runtime_messages_build_completed",
    "pre_generation_cuda_sync_started",
    "pre_generation_cuda_sync_completed",
    "chat_template_started",
    "chat_template_completed",
    "processor_tensorization_started",
    "processor_tensorization_completed",
    "processor_device_transfer_started",
    "processor_device_transfer_completed",
    "model_generate_started",
    "model_generate_completed",
    "decode_started",
    "decode_completed",
    "post_generation_cuda_sync_started",
    "post_generation_cuda_sync_completed",
    "case_result_build_started",
    "case_result_build_completed",
)

REQUIRED_GATES = (
    "published_failure_classification_lineage_integrity",
    "v2_preregistration_owner_progress_failure_classification_integrity",
    "fourth_record_and_completed_prefix_integrity",
    "static_input_artifact_receipt_integrity",
    "adapter_projection_integrity",
    "model_payload_gold_and_path_isolation",
    "prompt_projection_integrity",
    "runtime_message_transport_shape_integrity",
    "historical_checkpoint_boundary_integrity",
    "outcome_neutral_decision_rubric",
    "model_free_capability_boundary",
    "v2_immutable_and_zero_retry",
    "future_diagnostic_separate_identity_and_output",
    "runtime_authority_preserved",
    "fail_closed_claims",
)

DECISION_OUTCOMES = (
    "protocol_or_lineage_invalid",
    "deterministic_static_input_or_message_failure_reproduced",
    "static_pipeline_reconstructed_without_contract_violation",
    "static_difference_observed_without_causal_failure",
    "static_investigation_inconclusive",
)


class MM005GenerationFailureInvestigationError(ValueError):
    """Stable fail-closed error for protocol or evidence drift."""

    def __init__(self, code: str, location: str = "$") -> None:
        self.code = code
        self.location = location
        super().__init__(f"{code} at {location}")


def artifact_json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )


def sha256_bytes(payload: bytes) -> str:
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def parse_strict_json_bytes(payload: bytes, *, location: str) -> dict[str, Any]:
    if not isinstance(payload, bytes) or len(payload) > 8 * 1024 * 1024:
        _fail("JSON_BYTES_INVALID", location)
    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
        raise MM005GenerationFailureInvestigationError(
            "JSON_INVALID", location
        ) from exc
    if not isinstance(value, dict):
        _fail("JSON_OBJECT_REQUIRED", location)
    return value


def build_static_record_registry(
    records: Sequence[Mapping[str, Any]],
    artifact_payloads: Mapping[str, bytes],
    v2_preregistration: Mapping[str, Any],
) -> dict[str, Any]:
    """Rebuild target and frozen controls without processor, model, CUDA, or PIL."""

    ordered = sorted(records, key=lambda item: str(item.get("record_id")))
    record_ids = [str(item.get("record_id")) for item in ordered]
    input_suite = _mapping(v2_preregistration.get("input_suite"), "$.input_suite")
    case_order = _string_sequence(
        input_suite.get("case_order"), "$.input_suite.case_order"
    )
    if record_ids != case_order or len(record_ids) != 32:
        _fail("CASE_ORDER_MISMATCH", "$.input_suite.case_order")
    if case_order[TARGET_CASE_ORDER_INDEX] != TARGET_RECORD_ID:
        _fail("TARGET_CASE_ORDER_MISMATCH", "$.input_suite.case_order")

    prompt_registry = {
        str(item.get("record_id")): item
        for item in _object_sequence(
            input_suite.get("prompt_projection_registry"),
            "$.input_suite.prompt_projection_registry",
        )
    }
    if set(prompt_registry) != set(record_ids):
        _fail("PROMPT_REGISTRY_CLOSURE_MISMATCH", "$.input_suite")

    screenshot_payloads, source_snapshot_payloads = v1.artifact_input_sets(
        artifact_payloads
    )
    diagnostic_ids = (
        (TARGET_RECORD_ID,)
        + tuple(COMPLETED_PREFIX_CONTROL_IDS)
        + tuple(SAME_SHAPE_CONTROL_IDS)
    )
    if len(set(diagnostic_ids)) != len(diagnostic_ids):
        _fail("DIAGNOSTIC_RECORD_IDS_NOT_UNIQUE", "$.diagnostic_records")

    by_id = {str(item.get("record_id")): item for item in ordered}
    registry: list[dict[str, Any]] = []
    for record_id in diagnostic_ids:
        record = by_id.get(record_id)
        registered = prompt_registry.get(record_id)
        if record is None or registered is None:
            _fail("DIAGNOSTIC_RECORD_MISSING", f"$.diagnostic_records.{record_id}")
        try:
            adapted = adapter_verifier.adapt_record(
                record, screenshot_payloads, source_snapshot_payloads
            )
        except adapter_verifier.MM005BrowserResearchAdapterVerifierError as exc:
            raise MM005GenerationFailureInvestigationError(
                "ADAPTER_STATIC_RECONSTRUCTION_FAILED",
                f"$.diagnostic_records.{record_id}",
            ) from exc

        model_payload = adapted.model_payload()
        projection = v1.build_prompt_projection(
            model_payload, len(adapted.screenshot_payloads)
        )
        projection_payload = artifact_json_bytes(projection)
        sentinels = [object() for _payload in adapted.screenshot_payloads]
        runtime_messages = v1.build_runtime_messages(model_payload, sentinels)
        transport_projection = _runtime_transport_projection(
            runtime_messages, sentinels
        )
        transport_payload = artifact_json_bytes(transport_projection)
        if transport_payload != projection_payload:
            _fail(
                "RUNTIME_MESSAGE_TRANSPORT_PROJECTION_MISMATCH",
                f"$.diagnostic_records.{record_id}",
            )

        audit = adapted.audit_projection()
        bindings = _object_sequence(
            audit.get("source_bindings"),
            f"$.diagnostic_records.{record_id}.source_bindings",
        )
        screenshot_receipts: list[dict[str, Any]] = []
        snapshot_receipts: list[dict[str, Any]] = []
        source_ids: list[str] = []
        for index, binding in enumerate(bindings):
            source_ids.append(str(binding.get("source_id")))
            screenshot = dict(
                _mapping(
                    binding.get("screenshot"),
                    f"$.diagnostic_records.{record_id}.source_bindings[{index}]",
                )
            )
            snapshot = dict(
                _mapping(
                    binding.get("source_snapshot"),
                    f"$.diagnostic_records.{record_id}.source_bindings[{index}]",
                )
            )
            screenshot_payload = artifact_payloads.get(str(screenshot.get("path")))
            snapshot_payload = artifact_payloads.get(str(snapshot.get("path")))
            if (
                screenshot_payload is None
                or _receipt(str(screenshot["path"]), screenshot_payload) != screenshot
                or snapshot_payload is None
                or _receipt(str(snapshot["path"]), snapshot_payload) != snapshot
            ):
                _fail(
                    "STATIC_ARTIFACT_RECEIPT_MISMATCH",
                    f"$.diagnostic_records.{record_id}.source_bindings[{index}]",
                )
            width, height, bit_depth, color_type, interlace = _png_header(
                screenshot_payload,
                f"$.diagnostic_records.{record_id}.source_bindings[{index}].screenshot",
            )
            screenshot_receipts.append(
                {
                    **screenshot,
                    "png": {
                        "width": width,
                        "height": height,
                        "bit_depth": bit_depth,
                        "color_type": color_type,
                        "interlace": interlace,
                    },
                }
            )
            snapshot_receipts.append(snapshot)

        observed = {
            "record_id": record_id,
            "role": (
                "target"
                if record_id == TARGET_RECORD_ID
                else (
                    "authenticated_completed_prefix_control"
                    if record_id in COMPLETED_PREFIX_CONTROL_IDS
                    else "same_shape_static_control"
                )
            ),
            "case_order_index": record_ids.index(record_id),
            "dataset_record_index": _dataset_record_index(records, record_id),
            "split": record.get("split"),
            "template_id": record.get("template_id"),
            "task_family_id": record.get("task_family_id"),
            "source_kind": record.get("source_kind"),
            "source_count": len(bindings),
            "source_ids": source_ids,
            "record": _byte_receipt(artifact_json_bytes(record)),
            "adapter_audit_projection": _byte_receipt(adapted.audit_projection_json),
            "model_payload": _byte_receipt(adapted.model_payload_json),
            "model_payload_exact_keys": list(v1.MODEL_PAYLOAD_KEYS),
            "prompt_projection": _byte_receipt(projection_payload),
            "runtime_message_transport_projection": _byte_receipt(transport_payload),
            "screenshot_payloads": screenshot_receipts,
            "source_snapshot_payloads": snapshot_receipts,
            "runtime_message_shape": {
                "message_count": 2,
                "system_messages": 1,
                "user_messages": 1,
                "image_channels": len(bindings),
                "text_parts": 1,
                "opaque_sentinels_only": True,
            },
            "gold_or_verifier_fields_exposed": False,
            "real_file_path_exposed": False,
            "source_snapshots_exposed": False,
        }
        _validate_against_registered_projection(observed, registered)
        registry.append(observed)

    target = registry[0]
    if (
        target["record_id"] != TARGET_RECORD_ID
        or target["case_order_index"] != TARGET_CASE_ORDER_INDEX
        or target["dataset_record_index"] != TARGET_DATASET_RECORD_INDEX
        or target["split"] != TARGET_SPLIT
        or target["template_id"] != TARGET_TEMPLATE_ID
        or target["task_family_id"] != TARGET_TASK_FAMILY
        or target["source_kind"] != TARGET_SOURCE_KIND
        or target["source_count"] != TARGET_SOURCE_COUNT
    ):
        _fail("TARGET_RECORD_CONTRACT_MISMATCH", "$.diagnostic_records[0]")
    return {
        "target_record_id": TARGET_RECORD_ID,
        "target_case_order_index": TARGET_CASE_ORDER_INDEX,
        "completed_prefix_control_ids": list(COMPLETED_PREFIX_CONTROL_IDS),
        "same_shape_control_ids": list(SAME_SHAPE_CONTROL_IDS),
        "records": registry,
    }


def expected_preregistration(
    *,
    v2_preregistration: Mapping[str, Any],
    v2_preregistration_payload: bytes,
    attempt_owner_payload: bytes,
    progress_payload: bytes,
    failure_payload: bytes,
    classification: Mapping[str, Any],
    classification_payload: bytes,
    source_receipts: Mapping[str, Mapping[str, Any]],
    records: Sequence[Mapping[str, Any]],
    artifact_payloads: Mapping[str, bytes],
    freeze_status: str,
    output_absent: bool,
) -> dict[str, Any]:
    """Build the exact outcome-neutral investigation preregistration."""

    if freeze_status != "frozen":
        _fail("FREEZE_STATUS_INVALID", "$.freeze_status")
    if output_absent is not True:
        _fail("OUTPUT_PRESENT_AT_FREEZE", "$.freeze_preconditions")
    _validate_upstream_payloads(
        v2_preregistration_payload=v2_preregistration_payload,
        attempt_owner_payload=attempt_owner_payload,
        progress_payload=progress_payload,
        failure_payload=failure_payload,
        classification=classification,
        classification_payload=classification_payload,
    )
    if artifact_json_bytes(v2_preregistration) != v2_preregistration_payload:
        _fail("V2_PREREGISTRATION_NOT_CANONICAL", "$.source_lineage")
    observed_sources = {
        name: dict(_mapping(source_receipts.get(name), f"$.source_receipts.{name}"))
        for name in sorted(PROTOCOL_SOURCE_PATHS)
    }
    if set(source_receipts) != set(PROTOCOL_SOURCE_PATHS):
        _fail("PROTOCOL_SOURCE_SET_MISMATCH", "$.source_receipts")
    for name, path in PROTOCOL_SOURCE_PATHS.items():
        if observed_sources[name].get("path") != path:
            _fail("PROTOCOL_SOURCE_PATH_MISMATCH", f"$.source_receipts.{name}")

    static_registry = build_static_record_registry(
        records, artifact_payloads, v2_preregistration
    )
    authenticated_progress = _mapping(
        classification.get("authenticated_progress"),
        "$.classification.authenticated_progress",
    )
    observed_failure = _mapping(
        classification.get("failure"), "$.classification.failure"
    )
    locked_action = _mapping(
        classification.get("locked_next_action"), "$.classification.locked_next_action"
    )
    result: dict[str, Any] = {
        "mm005_browser_research_generation_failure_investigation_protocol_version": (
            PROTOCOL_VERSION
        ),
        "gate_id": GATE_ID,
        "investigation_id": INVESTIGATION_ID,
        "freeze_status": freeze_status,
        "decision": (
            "outcome_neutral_model_free_generation_failure_investigation_"
            "preregistration"
        ),
        "source_lineage": {
            "classification_merge_commit": CLASSIFICATION_MERGE_COMMIT,
            "v2_protocol_freeze_commit": failure.PROTOCOL_FREEZE_COMMIT,
            "upstream_artifacts": {
                "v2_preregistration": _receipt(
                    v2.PREREGISTRATION_PATH, v2_preregistration_payload
                ),
                "attempt_owner": _receipt(
                    failure.TRACKED_ATTEMPT_OWNER_PATH, attempt_owner_payload
                ),
                "progress": _receipt(failure.TRACKED_PROGRESS_PATH, progress_payload),
                "failure": _receipt(failure.TRACKED_FAILURE_PATH, failure_payload),
                "classification": _receipt(
                    failure.ARTIFACT_PATH, classification_payload
                ),
            },
            "classification_report_digest": CLASSIFICATION_REPORT_DIGEST,
            "protocol_sources": observed_sources,
        },
        "authenticated_failure_boundary": {
            "event_count": authenticated_progress.get("event_count"),
            "terminal_sequence": authenticated_progress.get("terminal_sequence"),
            "completed_record_ids": authenticated_progress.get("completed_record_ids"),
            "active_record_id": authenticated_progress.get("active_record_id"),
            "active_record_durable_completion": False,
            "counters": authenticated_progress.get("counters"),
            "stage": observed_failure.get("stage"),
            "exception_type": observed_failure.get("exception_type"),
            "root_cause_authenticated": False,
            "failed_runtime_substage_authenticated": False,
            "checkpoint_proves_model_generate_entered": False,
            "controller_console_text_authenticated": False,
        },
        "historical_control_flow_boundary": {
            "ordered_stage_span": list(HISTORICAL_GENERATION_STAGE_ORDER),
            "durably_authenticated_through": (
                "generation_started_checkpoint_durably_persisted"
            ),
            "pre_checkpoint_returns_implied_by_frozen_control_flow": [
                "record_adaptation_completed",
                "image_open_and_rgb_conversion_completed",
            ],
            "post_checkpoint_substages_not_individually_authenticated": list(
                HISTORICAL_GENERATION_STAGE_ORDER[3:-1]
            ),
            "fourth_generation_completed_checkpoint_present": False,
            "historical_root_cause_inferred_from_static_control_flow": False,
        },
        "static_investigation_plan": {
            "model_free": True,
            "pure_static_and_canonical_reconstruction_only": True,
            "steps": list(STATIC_DIAGNOSTIC_STEPS),
            "record_registry": static_registry,
            "decision_rubric": {
                "allowed_outcomes": list(DECISION_OUTCOMES),
                "outcome_selected_at_protocol_freeze": None,
                "static_failure_may_support_deterministic_reproduction_only": True,
                "static_pass_does_not_establish_historical_runtime_health": True,
                "static_difference_does_not_establish_causality": True,
                "root_cause_requires_separate_evidence": True,
            },
        },
        "static_investigation_contract": {
            "gate_id": INVESTIGATION_GATE_ID,
            "clean_aligned_merged_master_required": True,
            "protocol_and_sources_must_equal_freeze_commit_blobs": True,
            "fixed_result_path": RESULT_PATH,
            "fixed_result_absent_at_protocol_freeze": True,
            "exclusive_result_publication": True,
            "zero_internal_retry": True,
            "implementation_source_frozen_by_this_protocol": False,
            "implementation_must_conform_to_static_plan": True,
            "model_import_or_call": False,
            "processor_load_or_call": False,
            "pil_image_decode": False,
            "torch_import": False,
            "cuda": False,
            "network": False,
            "live_browser": False,
            "training": False,
            "v2_output_read_only": True,
        },
        "future_diagnostic_experiment_policy": {
            "currently_justified": False,
            "experiment_id": None,
            "run_id": None,
            "output_root": None,
            "execution_authorized": False,
            "prerequisite": (
                "validated static investigation result that remains inconclusive"
            ),
            "separate_protocol_clean_merge_required": True,
            "new_identity_and_output_required": True,
            "v2_output_reuse_forbidden": True,
            "minimum_durable_substage_checkpoints": list(
                FUTURE_DIAGNOSTIC_CHECKPOINT_REQUIREMENTS
            ),
            "checkpoint_observation_does_not_prove_async_error_origin": True,
            "own_authority_resource_and_terminal_contracts_required": True,
        },
        "freeze_preconditions": {
            "classification_clean_merge_is_ancestor": True,
            "classification_next_gate_matches": locked_action.get("gate_id") == GATE_ID,
            "investigation_output_absent": output_absent,
            "model_imported_or_called_at_protocol_freeze": False,
            "processor_loaded_or_called_at_protocol_freeze": False,
            "cuda_used_at_protocol_freeze": False,
            "v2_execution_retried": False,
        },
        "formal_gate": {
            "required_gates": list(REQUIRED_GATES),
            "root_cause_or_static_failure_required_for_measurement_completion": False,
            "quality_threshold_gate": False,
        },
        "authority_contract": {
            "model_or_cuda_execution_authorized": False,
            "processor_execution_authorized": False,
            "live_browser_or_network_authorized": False,
            "capture_authorized": False,
            "v1_or_v2_retry_authorized": False,
            "recovery_v3_authorized": False,
            "model_output_has_execution_authority": False,
            "page_content_has_execution_authority": False,
            "runtime_repository_changed": False,
            "runtime_integration_changed": False,
            "runtime_policy_or_approval_bypass": False,
            "runtime_is_sole_policy_approval_wal_grounding_budget_dispatch_boundary": (
                True
            ),
        },
        "claims": {
            "investigation_protocol_frozen": True,
            "investigation_executed": False,
            "static_root_cause_reproduced": False,
            "failed_runtime_substage_isolated": False,
            "remediation_delta_established": False,
            "recovery_v3_justified": False,
            "diagnostic_model_or_cuda_execution_authorized": False,
            "v2_attempt_consumed": True,
            "v2_execution_retried": False,
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
        },
        "next_gate": INVESTIGATION_GATE_ID,
        "runtime_eligible": False,
    }
    return result


def validate_preregistration(
    value: Mapping[str, Any],
    **inputs: Any,
) -> dict[str, Any]:
    """Fail closed unless the preregistration exactly recomputes."""

    expected = expected_preregistration(**inputs)
    if artifact_json_bytes(dict(value)) != artifact_json_bytes(expected):
        _fail("PREREGISTRATION_MISMATCH", "$.preregistration")
    return expected


def _validate_upstream_payloads(
    *,
    v2_preregistration_payload: bytes,
    attempt_owner_payload: bytes,
    progress_payload: bytes,
    failure_payload: bytes,
    classification: Mapping[str, Any],
    classification_payload: bytes,
) -> None:
    expected = (
        (
            v2_preregistration_payload,
            failure.PREREGISTRATION_BYTES,
            failure.PREREGISTRATION_SHA256,
            "V2_PREREGISTRATION_BINDING_MISMATCH",
        ),
        (
            attempt_owner_payload,
            failure.ATTEMPT_OWNER_BYTES,
            failure.ATTEMPT_OWNER_SHA256,
            "ATTEMPT_OWNER_BINDING_MISMATCH",
        ),
        (
            progress_payload,
            failure.PROGRESS_BYTES,
            failure.PROGRESS_SHA256,
            "PROGRESS_BINDING_MISMATCH",
        ),
        (
            failure_payload,
            failure.FAILURE_BYTES,
            failure.FAILURE_SHA256,
            "FAILURE_BINDING_MISMATCH",
        ),
        (
            classification_payload,
            CLASSIFICATION_BYTES,
            CLASSIFICATION_SHA256,
            "CLASSIFICATION_BINDING_MISMATCH",
        ),
    )
    for payload, byte_count, digest, code in expected:
        if len(payload) != byte_count or sha256_bytes(payload) != digest:
            _fail(code, "$.source_lineage")
    if artifact_json_bytes(classification) != classification_payload:
        _fail("CLASSIFICATION_NOT_CANONICAL", "$.source_lineage")
    if classification.get("report_digest") != CLASSIFICATION_REPORT_DIGEST:
        _fail("CLASSIFICATION_REPORT_DIGEST_MISMATCH", "$.source_lineage")
    action = _mapping(
        classification.get("locked_next_action"), "$.classification.locked_next_action"
    )
    progress = _mapping(
        classification.get("authenticated_progress"),
        "$.classification.authenticated_progress",
    )
    observed_failure = _mapping(
        classification.get("failure"), "$.classification.failure"
    )
    claims = _mapping(classification.get("claims"), "$.classification.claims")
    if (
        classification.get("gate_id") != failure.CLASSIFICATION_GATE_ID
        or action.get("gate_id") != GATE_ID
        or action.get("protocol_freeze_is_model_free") is not True
        or progress.get("active_record_id") != TARGET_RECORD_ID
        or progress.get("completed_record_ids") != list(COMPLETED_PREFIX_CONTROL_IDS)
        or observed_failure.get("root_cause_authenticated") is not False
        or claims.get("attempt_consumed") is not True
        or claims.get("model_evaluated") is not False
    ):
        _fail("CLASSIFICATION_BOUNDARY_MISMATCH", "$.classification")


def _validate_against_registered_projection(
    observed: Mapping[str, Any], registered: Mapping[str, Any]
) -> None:
    for key in (
        "record_id",
        "split",
        "task_family_id",
        "source_kind",
        "source_count",
        "model_payload_exact_keys",
        "gold_or_verifier_fields_exposed",
        "real_file_path_exposed",
        "source_snapshots_exposed",
    ):
        if observed.get(key) != registered.get(key):
            _fail("REGISTERED_PROJECTION_MISMATCH", f"$.record.{key}")
    for key in ("model_payload", "prompt_projection"):
        if observed.get(key) != registered.get(key):
            _fail("REGISTERED_PROJECTION_RECEIPT_MISMATCH", f"$.record.{key}")
    for observed_key, registered_key in (
        ("screenshot_payloads", "screenshot_payloads"),
        ("source_snapshot_payloads", "source_snapshot_payloads"),
    ):
        observed_receipts = [
            {name: item[name] for name in ("bytes", "sha256")}
            for item in _object_sequence(
                observed.get(observed_key), f"$.record.{observed_key}"
            )
        ]
        if observed_receipts != registered.get(registered_key):
            _fail("REGISTERED_ARTIFACT_RECEIPT_MISMATCH", f"$.record.{observed_key}")


def _runtime_transport_projection(
    messages: Sequence[Mapping[str, Any]], sentinels: Sequence[object]
) -> list[dict[str, Any]]:
    checked = _object_sequence(messages, "$.runtime_messages")
    if len(checked) != 2:
        _fail("RUNTIME_MESSAGE_COUNT", "$.runtime_messages")
    result: list[dict[str, Any]] = [dict(checked[0])]
    user = checked[1]
    content = _object_sequence(user.get("content"), "$.runtime_messages[1].content")
    converted: list[dict[str, Any]] = []
    sentinel_index = 0
    for index, item in enumerate(content):
        if item.get("type") == "image":
            if (
                set(item) != {"type", "image"}
                or sentinel_index >= len(sentinels)
                or item.get("image") is not sentinels[sentinel_index]
            ):
                _fail("RUNTIME_IMAGE_SENTINEL_MISMATCH", f"$.runtime_messages[{index}]")
            converted.append(
                {
                    "type": "image",
                    "image_transport": v1.SCREENSHOT_TRANSPORT_MARKER,
                }
            )
            sentinel_index += 1
        elif item.get("type") == "text" and set(item) == {"type", "text"}:
            converted.append(dict(item))
        else:
            _fail("RUNTIME_MESSAGE_CONTENT_INVALID", f"$.runtime_messages[{index}]")
    if sentinel_index != len(sentinels):
        _fail("RUNTIME_IMAGE_SENTINEL_COUNT", "$.runtime_messages")
    result.append({"role": user.get("role"), "content": converted})
    return result


def _dataset_record_index(records: Sequence[Mapping[str, Any]], record_id: str) -> int:
    matches = [item for item in records if item.get("record_id") == record_id]
    if len(matches) != 1:
        _fail("DATASET_RECORD_ID_NOT_UNIQUE", f"$.records.{record_id}")
    split = matches[0].get("split")
    split_records = [item for item in records if item.get("split") == split]
    for index, item in enumerate(split_records):
        if item.get("record_id") == record_id:
            return index
    _fail("DATASET_RECORD_INDEX_MISSING", f"$.records.{record_id}")


def _png_header(payload: bytes, location: str) -> tuple[int, int, int, int, int]:
    if (
        not isinstance(payload, bytes)
        or len(payload) < 33
        or payload[:8] != b"\x89PNG\r\n\x1a\n"
        or payload[12:16] != b"IHDR"
        or struct.unpack(">I", payload[8:12])[0] != 13
    ):
        _fail("PNG_HEADER_INVALID", location)
    width, height, bit_depth, color_type, compression, filter_method, interlace = (
        struct.unpack(">IIBBBBB", payload[16:29])
    )
    if (
        (width, height) != (1280, 900)
        or bit_depth != 8
        or color_type != 2
        or compression != 0
        or filter_method != 0
        or interlace != 0
    ):
        _fail("PNG_FORMAT_INVALID", location)
    return width, height, bit_depth, color_type, interlace


def _receipt(path: str, payload: bytes) -> dict[str, Any]:
    return {"path": path, "bytes": len(payload), "sha256": sha256_bytes(payload)}


def _byte_receipt(payload: bytes) -> dict[str, Any]:
    return {"bytes": len(payload), "sha256": sha256_bytes(payload)}


def _mapping(value: object, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        _fail("OBJECT_REQUIRED", location)
    return value


def _object_sequence(value: object, location: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        _fail("ARRAY_REQUIRED", location)
    return [_mapping(item, f"{location}[{index}]") for index, item in enumerate(value)]


def _string_sequence(value: object, location: str) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        _fail("STRING_ARRAY_REQUIRED", location)
    if any(not isinstance(item, str) for item in value):
        _fail("STRING_ARRAY_REQUIRED", location)
    return list(value)


def _unique_object(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail("JSON_DUPLICATE_KEY", "$.json")
        result[key] = value
    return result


def _reject_constant(value: str) -> NoReturn:
    _fail("JSON_NONFINITE", f"$.json.{value}")


def _fail(code: str, location: str = "$") -> NoReturn:
    raise MM005GenerationFailureInvestigationError(code, location)


__all__ = [
    "CLASSIFICATION_BYTES",
    "CLASSIFICATION_MERGE_COMMIT",
    "CLASSIFICATION_REPORT_DIGEST",
    "CLASSIFICATION_SHA256",
    "COMPLETED_PREFIX_CONTROL_IDS",
    "DECISION_OUTCOMES",
    "FUTURE_DIAGNOSTIC_CHECKPOINT_REQUIREMENTS",
    "GATE_ID",
    "HISTORICAL_GENERATION_STAGE_ORDER",
    "INVESTIGATION_GATE_ID",
    "INVESTIGATION_ID",
    "MM005GenerationFailureInvestigationError",
    "PREREGISTRATION_PATH",
    "PROTOCOL_SOURCE_PATHS",
    "PROTOCOL_VERSION",
    "REQUIRED_GATES",
    "RESULT_PATH",
    "SAME_SHAPE_CONTROL_IDS",
    "STATIC_DIAGNOSTIC_STEPS",
    "TARGET_CASE_ORDER_INDEX",
    "TARGET_DATASET_RECORD_INDEX",
    "TARGET_RECORD_ID",
    "artifact_json_bytes",
    "build_static_record_registry",
    "expected_preregistration",
    "parse_strict_json_bytes",
    "sha256_bytes",
    "validate_preregistration",
]
