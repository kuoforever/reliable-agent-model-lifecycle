"""Deterministic classification for the first MM-003 formal-run failure."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from . import mm003_baseline_protocol as protocol

FAILURE_CLASSIFICATION_VERSION = 1
FAILED_GATE_ID = "MM-003-local-small-vlm-baseline-execution-v1"
NEXT_GATE_ID = "MM-003-local-small-vlm-baseline-recovery-protocol-v2"
PROTOCOL_FREEZE_COMMIT = "759a4ea2cbc6b45c78451bcbcdf2c26271c7af78"
PREREGISTRATION_BYTES = 11_151
PREREGISTRATION_SHA256 = (
    "sha256:0046143f2c8badb5b2eaa809ac4c7abce81d1c0a5156fe2668b4e5cf9668aa10"
)
ARTIFACT_PATH = "baseline/mm003-qwen2.5-vl-3b-baseline-v1-failure-classification.json"


def build_failure_classification(root: Path) -> dict[str, Any]:
    """Bind the observed exception to the exact frozen v1 protocol sources."""

    preregistration_path = root / protocol.PREREGISTRATION_PATH
    preregistration_payload = _read_regular_file(
        preregistration_path, "MM-003 v1 preregistration"
    )
    if (
        len(preregistration_payload) != PREREGISTRATION_BYTES
        or protocol.sha256_bytes(preregistration_payload) != PREREGISTRATION_SHA256
    ):
        _fail("PREREGISTRATION_BINDING_MISMATCH", "$.protocol.preregistration")
    raw = protocol.parse_strict_json_bytes(
        preregistration_payload, location="$.protocol.preregistration"
    )
    if not isinstance(raw, dict):
        _fail("INVALID_PREREGISTRATION", "$.protocol.preregistration")
    preregistration = protocol.validate_preregistration(raw)

    source_bindings: dict[str, dict[str, Any]] = {}
    receipts = preregistration["source_lineage"]["protocol_sources"]
    for name, relative in protocol.PROTOCOL_SOURCE_PATHS.items():
        payload = _read_regular_file(root / relative, f"MM-003 v1 {name} source")
        digest = protocol.sha256_bytes(payload)
        if receipts[name] != {"path": relative, "sha256": digest}:
            _fail(
                "PROTOCOL_SOURCE_BINDING_MISMATCH",
                f"$.source_bindings.{name}",
            )
        source_bindings[name] = {
            "path": relative,
            "bytes": len(payload),
            "sha256": digest,
        }

    result: dict[str, Any] = {
        "failure_classification_version": FAILURE_CLASSIFICATION_VERSION,
        "experiment_id": protocol.EXPERIMENT_ID,
        "failed_gate_id": FAILED_GATE_ID,
        "receipt_captured_at_utc": "2026-08-17T06:00:39Z",
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
        "attempt": {
            "attempt_ordinal": 1,
            "fresh_model_load_completed": True,
            "full_eval_run_completed": False,
            "generation_calls_completed": 9,
            "generation_progress_basis": (
                "traceback reached score_predictions after the exhaustive "
                "frozen nine-case loop"
            ),
            "scoring_started": True,
            "operator_retry_count": 0,
            "artifacts_written": False,
            "output_directory_absent_after_failure": True,
        },
        "failure": {
            "classification": (
                "post_generation_scoring_empty_optional_metric_denominator"
            ),
            "category": "scoring_contract_totality",
            "exception_type": (
                "fullcycle_bridge.gui_grounding_eval.GuiGroundingValidationError"
            ),
            "code": "EMPTY_METRIC_DENOMINATOR",
            "location": "$report.metrics",
            "metric": "prediction_coordinate_ref_disagreement_rate",
            "trigger": ("no compiled prediction supplied both a non-null ref and bbox"),
            "core_suite_denominator_failure": False,
            "cuda_or_model_load_failure": False,
        },
        "recoverability": {
            "raw_model_outputs": False,
            "compiled_predictions": False,
            "per_case_latency": False,
            "aggregate_resources": False,
            "mm002_metrics": False,
            "reason": (
                "the v1 runner writes all three artifacts only after scoring; "
                "process-local results were not persisted before the exception"
            ),
        },
        "evidence_policy": {
            "control_flow_inference_explicit": True,
            "external_process_trace_attested": False,
            "raw_outputs_available": False,
            "eval_answer_tuning": False,
            "prompt_changed_after_observation": False,
            "compiler_changed_after_observation": False,
            "model_or_revision_changed": False,
            "training_performed": False,
            "runtime_connected": False,
            "desktop_connected": False,
        },
        "formal_gate_passed": False,
        "claims": {
            "baseline_execution_attempted": True,
            "baseline_executed": False,
            "model_evaluated": False,
            "post_training_complete": False,
            "adapter_loadable": False,
            "real_content_collected": False,
            "cross_machine_reproducibility_established": False,
            "portable_package_eligible": False,
            "serving_readiness_established": False,
            "artifact_promotion_allowed": False,
            "runtime_eligible": False,
        },
        "locked_next_action": {
            "gate_id": NEXT_GATE_ID,
            "action": (
                "freeze a new outcome-neutral protocol that represents a zero "
                "denominator for the prediction-dependent diagnostic as not "
                "applicable and persists raw and compiled outputs before scoring"
            ),
            "acceptance": {
                "v1_failure_receipt_bound": True,
                "optional_metric_zero_denominator_is_not_applicable": True,
                "raw_outputs_persist_before_scoring": True,
                "compiled_predictions_persist_before_scoring": True,
                "scoring_failure_receipt_persisted": True,
                "new_run_requires_new_merged_freeze_commit": True,
            },
            "constraints": {
                "v1_artifacts_rewritten": False,
                "eval_answers_changed": False,
                "synthetic_inputs_changed": False,
                "prompt_changed": False,
                "compiler_changed": False,
                "model_or_revision_changed": False,
                "training": False,
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
    """Fail closed unless the artifact exactly matches the recomputation."""

    expected = build_failure_classification(root)
    if dict(value) != expected:
        _fail("FAILURE_CLASSIFICATION_MISMATCH", "$.failure_classification")
    return expected


def _read_regular_file(path: Path, label: str) -> bytes:
    resolved = path.resolve(strict=True)
    if not resolved.is_file() or resolved.is_symlink():
        _fail("UNSAFE_SOURCE_FILE", f"$.{label}")
    return resolved.read_bytes()


def _fail(code: str, location: str) -> None:
    raise protocol.MM003ProtocolError(code, location)


__all__ = [
    "ARTIFACT_PATH",
    "FAILED_GATE_ID",
    "FAILURE_CLASSIFICATION_VERSION",
    "NEXT_GATE_ID",
    "PROTOCOL_FREEZE_COMMIT",
    "build_failure_classification",
    "validate_failure_classification",
]
