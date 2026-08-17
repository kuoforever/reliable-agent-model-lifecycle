"""Deterministic classification of the MM-003 QLoRA v1 formal failure."""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any, Mapping, NoReturn, cast

from . import mm003_baseline_protocol as baseline
from . import mm003_post_training_protocol as protocol

FAILURE_CLASSIFICATION_VERSION = 1
CLASSIFICATION_GATE_ID = "MM-003-small-vlm-post-training-failure-classification-v1"
FAILED_GATE_ID = "MM-003-small-vlm-post-training-execution-v1"
NEXT_GATE_ID = "MM-003-small-vlm-post-training-recovery-protocol-v2"
RECOVERY_EXECUTION_GATE_ID = "MM-003-small-vlm-post-training-execution-v2"
RECOVERY_EXPERIMENT_ID = "mm003-qwen2.5-vl-3b-qlora-sft-v2"
RECOVERY_OUTPUT_DIRECTORY = "work/training-runs/mm003-qlora-sft-v2"
RECOVERY_SUCCESS_NEXT_GATE_ID = "MM-003-small-vlm-post-training-result-review-v2"
RECOVERY_PREREGISTRATION_VERSION = 2
RECOVERY_DECISION = "outcome_neutral_qlora_training_and_measurement_recovery_protocol"
RECOVERY_PROMPT_GATE = "post_training_prompt_projection_totality"
RECOVERY_CONTRACT_PATH = (
    "src/fullcycle_bridge/mm003_post_training_protocol_v2.py"
)
RECOVERY_RUNNER_PATH = "scripts/run_mm003_qlora_post_training_v2.py"
PROTOCOL_FREEZE_COMMIT = "a882e6096a87e475511890be9fc804a468143868"
PREREGISTRATION_BYTES = 17_601
PREREGISTRATION_SHA256 = (
    "sha256:9dfd180f24a86814fc32c5ebbfca07a31f713c8387f85ec3212dc538647cb061"
)
LOCAL_FAILURE_RECEIPT_PATH = "work/training-runs/mm003-qlora-sft-v1/failure.json"
FAILURE_RECEIPT_PATH = "baseline/mm003-qwen2.5-vl-3b-qlora-sft-v1-failure.json"
FAILURE_RECEIPT_BYTES = 897
FAILURE_RECEIPT_SHA256 = (
    "sha256:8c82455b406c66a038deaaadeb9251b9eb626145a5f31d36b04d5ad7d10c72d9"
)
ARTIFACT_PATH = (
    "baseline/mm003-qwen2.5-vl-3b-qlora-sft-v1-failure-classification.json"
)


def build_failure_classification(root: Path) -> dict[str, Any]:
    """Bind the exact failure receipt and reproduce its static root cause."""

    preregistration_payload = _read_regular_file(
        root / protocol.PREREGISTRATION_PATH,
        "MM-003 post-training v1 preregistration",
    )
    if (
        len(preregistration_payload) != PREREGISTRATION_BYTES
        or protocol.sha256_bytes(preregistration_payload) != PREREGISTRATION_SHA256
    ):
        _fail("PREREGISTRATION_BINDING_MISMATCH", "$.protocol.preregistration")
    raw_preregistration = protocol.parse_strict_json_bytes(
        preregistration_payload,
        location="$.protocol.preregistration",
    )
    if not isinstance(raw_preregistration, dict):
        _fail("INVALID_PREREGISTRATION", "$.protocol.preregistration")
    preregistration = protocol.validate_preregistration(raw_preregistration)

    source_bindings: dict[str, dict[str, Any]] = {}
    registered_sources = preregistration["source_lineage"]["protocol_sources"]
    for name, relative in protocol.PROTOCOL_SOURCE_PATHS.items():
        payload = _read_regular_file(root / relative, f"MM-003 post-training v1 {name}")
        digest = protocol.sha256_bytes(payload)
        if registered_sources[name] != {"path": relative, "sha256": digest}:
            _fail("PROTOCOL_SOURCE_BINDING_MISMATCH", f"$.source_bindings.{name}")
        source_bindings[name] = {
            "path": relative,
            "bytes": len(payload),
            "sha256": digest,
        }

    failure_receipt = _failure_receipt_binding(root)
    static_reproduction = _reproduce_training_input_failure(
        root,
        preregistration,
    )
    v1_required_gates = list(
        preregistration["formal_gate"]["required_gates"]
    )
    prompt_gate_index = v1_required_gates.index("training_fixture_integrity") + 1
    v2_required_gates = list(v1_required_gates)
    v2_required_gates.insert(prompt_gate_index, RECOVERY_PROMPT_GATE)
    result: dict[str, Any] = {
        "failure_classification_version": FAILURE_CLASSIFICATION_VERSION,
        "classification_gate_id": CLASSIFICATION_GATE_ID,
        "experiment_id": protocol.EXPERIMENT_ID,
        "failed_gate_id": FAILED_GATE_ID,
        "protocol": {
            "definition_gate_id": protocol.GATE_ID,
            "freeze_commit": PROTOCOL_FREEZE_COMMIT,
            "preregistration": {
                "path": protocol.PREREGISTRATION_PATH,
                "bytes": len(preregistration_payload),
                "sha256": protocol.sha256_bytes(preregistration_payload),
            },
        },
        "source_bindings": dict(sorted(source_bindings.items())),
        "failure_receipt": failure_receipt,
        "attempt": {
            "attempt_ordinal": 1,
            "registered_lifecycle_consumed": True,
            "registered_preflight_completed_by_control_flow": True,
            "training_stage_entered": True,
            "operator_retry_count": 0,
            "model_and_lora_setup_reached_by_control_flow": True,
            "training_records_encoded_by_control_flow": 0,
            "model_forward_calls_by_control_flow": 0,
            "backward_calls_by_control_flow": 0,
            "optimizer_steps_completed_by_control_flow": 0,
            "eval_generate_calls_by_control_flow": 0,
            "model_load_completion_attested": False,
            "optimizer_step_evidence_available": False,
            "adapter_artifacts_written": False,
            "training_run_artifact_written": False,
            "predictions_artifact_written": False,
            "evidence_artifact_written": False,
        },
        "failure": {
            "classification": (
                "pre_forward_training_prompt_eval_case_registry_mismatch"
            ),
            "category": "training_prompt_contract_totality",
            "exception_type": "MM003ProtocolError",
            "receipt_exception_code_available": False,
            "receipt_exception_location_available": False,
            "static_reproduction": static_reproduction,
            "trigger": (
                "the post-training renderer delegated pt-* records to the "
                "MM-002 ground-* CASE_MODES registry"
            ),
            "training_fixture_mode_invalid": False,
            "cuda_or_checkpoint_failure": False,
            "model_forward_failure": False,
            "optimizer_failure": False,
            "scoring_failure": False,
        },
        "recoverability": {
            "failure_receipt": True,
            "deterministic_root_cause": True,
            "adapter": False,
            "training_metrics": False,
            "post_training_predictions": False,
            "mm002_metrics": False,
            "reason": (
                "the first frozen training record failed before processor "
                "encoding, forward, backward, optimizer step, Adapter save, or eval"
            ),
        },
        "evidence_policy": {
            "exact_failure_receipt_available": True,
            "local_source_receipt_verified_at_classification": True,
            "clean_validation_uses_tracked_canonical_copy": True,
            "formal_terminal_trace_persisted": False,
            "static_root_cause_reproduction_without_model": True,
            "control_flow_inference_explicit": True,
            "model_load_completion_attested": False,
            "optimizer_step_attested": False,
            "eval_answer_tuning": False,
            "model_or_revision_changed": False,
            "training_data_changed": False,
            "runtime_connected": False,
            "desktop_connected": False,
        },
        "formal_gate_passed": False,
        "claims": {
            "post_training_execution_attempted": True,
            "training_executed": False,
            "adapter_created": False,
            "adapter_independently_loadable": False,
            "model_evaluated": False,
            "quality_improved": False,
            "repeatability_established": False,
            "cross_machine_reproducibility": False,
            "portable_artifact": False,
            "commercial_use_eligible": False,
            "serving_eligible": False,
            "promotion_eligible": False,
            "runtime_eligible": False,
        },
        "locked_next_action": {
            "gate_id": NEXT_GATE_ID,
            "execution_gate_id": RECOVERY_EXECUTION_GATE_ID,
            "experiment_id": RECOVERY_EXPERIMENT_ID,
            "output_directory": RECOVERY_OUTPUT_DIRECTORY,
            "success_next_gate_id": RECOVERY_SUCCESS_NEXT_GATE_ID,
            "action": (
                "freeze a separate outcome-neutral v2 protocol with a "
                "post-training-specific prompt projection and complete "
                "27-record prompt preflight before any dependency or model load"
            ),
            "acceptance": {
                "v1_failure_receipt_bound": True,
                "v1_execution_not_retried": True,
                "baseline_ground_case_registry_unchanged": True,
                "post_training_case_registry_is_separate": True,
                "all_27_prompts_render_during_preflight": True,
                "prompt_projection_excludes_gold_and_raw_regions": True,
                "prompt_receipts_frozen": True,
                "new_gate_experiment_and_output_directory": True,
                "new_run_requires_new_merged_freeze_commit": True,
            },
            "lineage_requirements": {
                "v1_preregistration": {
                    "path": protocol.PREREGISTRATION_PATH,
                    "bytes": PREREGISTRATION_BYTES,
                    "sha256": PREREGISTRATION_SHA256,
                },
                "v1_failure_receipt": {
                    "path": FAILURE_RECEIPT_PATH,
                    "bytes": FAILURE_RECEIPT_BYTES,
                    "sha256": FAILURE_RECEIPT_SHA256,
                },
                "v1_failure_classification": {
                    "path": ARTIFACT_PATH,
                    "file_receipt_required_at_v2_freeze": True,
                    "report_digest_required_at_v2_freeze": True,
                },
                "v1_protocol_source_receipts": sorted(
                    protocol.PROTOCOL_SOURCE_PATHS
                ),
            },
            "v1_sections_exactly_preserved": [
                "authority_contract",
                "model",
                "source_lineage.negative_baseline",
                "source_lineage.baseline_preregistration",
                "source_lineage.training_data",
                "source_lineage.validation_data",
                "source_lineage.training_screenshots",
                "source_lineage.unchanged_mm002_eval",
                "source_lineage.eval_isolation",
                "source_lineage.bitsandbytes_wheel",
                "environment",
                "compatibility_smoke",
                "training_protocol",
                "evaluation_protocol",
                "outputs.required_adapter_files",
                "outputs.writes_are_exclusive",
                "resource_caps",
                "formal_gate.quality_threshold_required",
                "claims",
                "runtime_eligible",
            ],
            "allowed_difference_policy": {
                "comparison_base": protocol.PREREGISTRATION_PATH,
                "comparison_unit": "recursive_json_leaf",
                "arrays_compared_atomically": True,
                "unlisted_existing_leaf_values_must_be_identical": True,
                "unlisted_v1_fields_may_be_removed": False,
                "unlisted_v2_fields_may_be_added": False,
                "listed_container_replacement_authorized": False,
                "whitelist_diff_test_required": True,
            },
            "required_v2_values": {
                "preregistration_version": RECOVERY_PREREGISTRATION_VERSION,
                "experiment_id": RECOVERY_EXPERIMENT_ID,
                "gate_id": NEXT_GATE_ID,
                "decision": RECOVERY_DECISION,
                "outputs.adapter_directory": (
                    f"{RECOVERY_OUTPUT_DIRECTORY}/adapter"
                ),
                "outputs.training_run": (
                    f"{RECOVERY_OUTPUT_DIRECTORY}/training-run.json"
                ),
                "outputs.predictions": (
                    f"{RECOVERY_OUTPUT_DIRECTORY}/mm002-predictions.json"
                ),
                "outputs.evidence": f"{RECOVERY_OUTPUT_DIRECTORY}/evidence.json",
                "outputs.failure": f"{RECOVERY_OUTPUT_DIRECTORY}/failure.json",
                "formal_gate.required_gates": v2_required_gates,
                "next_gate_after_freeze.gate_id": RECOVERY_EXECUTION_GATE_ID,
                "next_gate_after_freeze.action": (
                    "execute the separately frozen v2 QLoRA lifecycle exactly "
                    "once, save the Adapter, independently reload base plus "
                    "Adapter, and run the unchanged nine-case MM-002 evaluation "
                    "with zero retries"
                ),
                "success_next_gate_after_execution": {
                    "gate_id": RECOVERY_SUCCESS_NEXT_GATE_ID,
                    "action": (
                        "review the outcome-neutral v2 training, Adapter, "
                        "independent reload, unchanged MM-002 evaluation, and "
                        "resource evidence without inferring promotion"
                    ),
                },
            },
            "allowed_v2_differences": {
                "exact_value_replacements": [
                    "preregistration_version",
                    "experiment_id",
                    "gate_id",
                    "decision",
                    "outputs.adapter_directory",
                    "outputs.training_run",
                    "outputs.predictions",
                    "outputs.evidence",
                    "outputs.failure",
                    "formal_gate.required_gates",
                    "next_gate_after_freeze.gate_id",
                    "next_gate_after_freeze.action",
                ],
                "source_lineage.protocol_sources": {
                    "v1_receipts_exactly_preserved": sorted(
                        protocol.PROTOCOL_SOURCE_PATHS
                    ),
                    "required_additions": {
                        "post_training_contract_v2": {
                            "path": RECOVERY_CONTRACT_PATH,
                            "sha256_required": True,
                        },
                        "post_training_runner_v2": {
                            "path": RECOVERY_RUNNER_PATH,
                            "sha256_required": True,
                        },
                    },
                    "other_additions_removals_or_replacements_allowed": False,
                },
                "authorized_new_sections": {
                    "source_lineage.v1_failure_lineage": {
                        "closed_schema": True,
                        "required_receipts": [
                            "v1_preregistration",
                            "v1_failure_receipt",
                            "v1_failure_classification",
                        ],
                        "exact_file_receipts_required": True,
                    },
                    "prompt_projection": {
                        "closed_schema": True,
                        "deterministic_builder_recomputation_required": True,
                        "registry_records": 27,
                        "case_ids_and_modes_from_tracked_fixtures": True,
                        "payload_root_fields": [
                            "case_id",
                            "observation_mode",
                            "instruction",
                            "available_tools",
                            "observation",
                        ],
                        "forbidden_source_fields": [
                            "family_id",
                            "training_repeat_group",
                            "target",
                            "model_input.observation.screenshot_regions",
                        ],
                        "baseline_ground_case_registry_unchanged": True,
                        "all_prompts_before_dependency_or_model_load": True,
                    },
                    "prompt_receipts": {
                        "closed_schema": True,
                        "deterministic_builder_recomputation_required": True,
                        "per_case_receipts": 27,
                        "per_case_fields": [
                            "case_id",
                            "observation_mode",
                            "bytes",
                            "sha256",
                        ],
                        "aggregate_digest_required": True,
                    },
                    "success_next_gate_after_execution": {
                        "exact_value_required": True,
                    },
                },
            },
            "constraints": {
                "v1_failure_directory_deleted": False,
                "v1_failure_receipt_rewritten": False,
                "v1_execution_retried": False,
                "eval_answers_changed": False,
                "model_or_revision_changed": False,
                "training_data_changed": False,
                "hyperparameters_changed": False,
                "runtime_integration": False,
            },
        },
        "runtime_eligible": False,
    }
    result["report_digest"] = protocol.sha256_bytes(
        protocol.canonical_json_bytes(result)
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


def verify_local_failure_receipt(root: Path) -> dict[str, Any]:
    """Verify the ignored formal output before capturing its tracked copy."""

    run_directory = (
        root / Path(LOCAL_FAILURE_RECEIPT_PATH).parent
    ).resolve(strict=True)
    if not run_directory.is_dir() or run_directory.is_symlink():
        _fail("UNSAFE_RUN_DIRECTORY", "$.failure_receipt.directory")
    directory_entries = sorted(path.name for path in run_directory.iterdir())
    if directory_entries != [Path(LOCAL_FAILURE_RECEIPT_PATH).name]:
        _fail("UNEXPECTED_RUN_DIRECTORY_ENTRIES", "$.failure_receipt.directory")
    failure_payload = _read_regular_file(
        root / LOCAL_FAILURE_RECEIPT_PATH,
        "MM-003 post-training v1 failure receipt",
    )
    if (
        len(failure_payload) != FAILURE_RECEIPT_BYTES
        or protocol.sha256_bytes(failure_payload) != FAILURE_RECEIPT_SHA256
    ):
        _fail("FAILURE_RECEIPT_BINDING_MISMATCH", "$.failure_receipt")
    raw_failure = protocol.parse_strict_json_bytes(
        failure_payload,
        location="$.failure_receipt.content",
    )
    binding = _failure_receipt_binding(root)
    tracked_payload = _read_regular_file(
        root / FAILURE_RECEIPT_PATH,
        "tracked MM-003 post-training v1 failure receipt",
    )
    if failure_payload != tracked_payload:
        _fail("LOCAL_TRACKED_RECEIPT_MISMATCH", "$.failure_receipt")
    if not isinstance(raw_failure, dict) or raw_failure != binding["content"]:
        _fail("FAILURE_RECEIPT_CONTENT_MISMATCH", "$.failure_receipt.content")
    return binding


def _reproduce_training_input_failure(
    root: Path,
    preregistration: Mapping[str, Any],
) -> dict[str, Any]:
    train_records = _load_registered_dataset(
        root,
        preregistration,
        split="train",
    )["records"]
    validation_records = _load_registered_dataset(
        root,
        preregistration,
        split="validation",
    )["records"]
    order = list(range(len(train_records)))
    epoch_one_shuffle_seed = protocol.TRAINING_SEED + 1
    random.Random(epoch_one_shuffle_seed).shuffle(order)
    failures: list[dict[str, str]] = []
    for record in [*train_records, *validation_records]:
        try:
            protocol.render_training_input(record)
        except baseline.MM003ProtocolError as exc:
            if exc.code != "CASE_MODE_MISMATCH" or exc.location != "$.case":
                _fail("UNEXPECTED_STATIC_FAILURE", "$.failure.static_reproduction")
            failures.append(
                {
                    "case_id": str(record["case_id"]),
                    "code": exc.code,
                    "location": exc.location,
                }
            )
        else:
            _fail("EXPECTED_STATIC_FAILURE_MISSING", "$.failure.static_reproduction")
    if any(record["case_id"] in baseline.CASE_MODES for record in failures):
        _fail("BASELINE_CASE_REGISTRY_DRIFT", "$.failure.static_reproduction")
    first = train_records[order[0]]
    return {
        "training_seed": protocol.TRAINING_SEED,
        "epoch_one_shuffle_seed": epoch_one_shuffle_seed,
        "first_case_id": first["case_id"],
        "first_record_zero_based_index": order[0],
        "first_case_observation_mode": first["observation_mode"],
        "records_checked": len(train_records) + len(validation_records),
        "records_failed": len(failures),
        "exception_type": "MM003ProtocolError",
        "code": "CASE_MODE_MISMATCH",
        "location": "$.case",
        "baseline_registered_case_count": len(baseline.CASE_MODES),
        "post_training_ids_in_baseline_registry": 0,
        "tracked_fixture_receipts_verified": 2,
        "model_or_gpu_used": False,
    }


def _load_registered_dataset(
    root: Path,
    preregistration: Mapping[str, Any],
    *,
    split: str,
) -> dict[str, Any]:
    if split == "train":
        relative = protocol.TRAIN_DATASET_PATH
        lineage_key = "training_data"
    elif split == "validation":
        relative = protocol.VALIDATION_DATASET_PATH
        lineage_key = "validation_data"
    else:
        _fail("INVALID_SPLIT", "$.failure.static_reproduction")
    payload = _read_regular_file(root / relative, f"tracked {split} dataset")
    source_lineage = preregistration.get("source_lineage")
    if not isinstance(source_lineage, Mapping):
        _fail("INVALID_SOURCE_LINEAGE", "$.protocol.preregistration.source_lineage")
    receipt = source_lineage.get(lineage_key)
    expected_receipt = {
        "path": relative,
        "bytes": len(payload),
        "sha256": protocol.sha256_bytes(payload),
    }
    if not isinstance(receipt, Mapping) or dict(receipt) != expected_receipt:
        _fail(
            "DATASET_RECEIPT_BINDING_MISMATCH",
            f"$.protocol.preregistration.source_lineage.{lineage_key}",
        )
    raw = protocol.parse_strict_json_bytes(
        payload,
        location=f"$.failure.static_reproduction.{split}",
    )
    return cast(dict[str, Any], protocol.validate_dataset(raw, split=split))


def _expected_failure_receipt() -> dict[str, Any]:
    negative_claims = {
        "training_executed": False,
        "adapter_created": False,
        "adapter_independently_loadable": False,
        "model_evaluated": False,
        "quality_improved": False,
        "repeatability_established": False,
        "cross_machine_reproducibility": False,
        "portable_artifact": False,
        "commercial_use_eligible": False,
        "serving_eligible": False,
        "promotion_eligible": False,
        "runtime_eligible": False,
    }
    return {
        "failure_version": 1,
        "experiment_id": protocol.EXPERIMENT_ID,
        "gate_id": FAILED_GATE_ID,
        "protocol_freeze_commit": PROTOCOL_FREEZE_COMMIT,
        "preregistration_sha256": PREREGISTRATION_SHA256,
        "stage": "training",
        "exception_type": "MM003ProtocolError",
        "retry_count": 0,
        "formal_gate_passed": False,
        "claims": negative_claims,
        "runtime_eligible": False,
    }


def _failure_receipt_binding(root: Path) -> dict[str, Any]:
    expected = _expected_failure_receipt()
    payload = _read_regular_file(
        root / FAILURE_RECEIPT_PATH,
        "tracked MM-003 post-training v1 failure receipt",
    )
    if (
        len(payload) != FAILURE_RECEIPT_BYTES
        or protocol.sha256_bytes(payload) != FAILURE_RECEIPT_SHA256
    ):
        _fail("FAILURE_RECEIPT_CONSTANT_MISMATCH", "$.failure_receipt")
    raw = protocol.parse_strict_json_bytes(
        payload,
        location="$.failure_receipt.content",
    )
    if not isinstance(raw, dict) or raw != expected:
        _fail("FAILURE_RECEIPT_CONTENT_MISMATCH", "$.failure_receipt.content")
    return {
        "source_path": LOCAL_FAILURE_RECEIPT_PATH,
        "path": FAILURE_RECEIPT_PATH,
        "bytes": len(payload),
        "sha256": protocol.sha256_bytes(payload),
        "directory_entries_observed": ["failure.json"],
        "content": expected,
    }


def _read_regular_file(path: Path, label: str) -> bytes:
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise protocol.MM003PostTrainingProtocolError(
            "MISSING_BOUND_FILE", f"$.{label}"
        ) from exc
    if not resolved.is_file() or resolved.is_symlink():
        _fail("UNSAFE_BOUND_FILE", f"$.{label}")
    return resolved.read_bytes()


def _fail(code: str, location: str) -> NoReturn:
    raise protocol.MM003PostTrainingProtocolError(code, location)


__all__ = [
    "ARTIFACT_PATH",
    "CLASSIFICATION_GATE_ID",
    "FAILED_GATE_ID",
    "FAILURE_CLASSIFICATION_VERSION",
    "FAILURE_RECEIPT_BYTES",
    "FAILURE_RECEIPT_PATH",
    "FAILURE_RECEIPT_SHA256",
    "LOCAL_FAILURE_RECEIPT_PATH",
    "NEXT_GATE_ID",
    "PROTOCOL_FREEZE_COMMIT",
    "RECOVERY_EXECUTION_GATE_ID",
    "RECOVERY_EXPERIMENT_ID",
    "RECOVERY_OUTPUT_DIRECTORY",
    "RECOVERY_PREREGISTRATION_VERSION",
    "RECOVERY_PROMPT_GATE",
    "RECOVERY_SUCCESS_NEXT_GATE_ID",
    "build_failure_classification",
    "validate_failure_classification",
    "verify_local_failure_receipt",
]
