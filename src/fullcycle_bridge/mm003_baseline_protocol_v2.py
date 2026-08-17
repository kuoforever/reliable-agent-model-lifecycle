"""Outcome-neutral recovery protocol for the second MM-003 baseline gate."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any, NoReturn, cast

from . import mm003_baseline_protocol as v1

PREREGISTRATION_VERSION = 2
GATE_ID = "MM-003-multimodal-gui-action-model-recovery-v2"
EXPERIMENT_ID = "mm003-qwen2.5-vl-3b-instruct-baseline-v2"
EXECUTION_GATE_ID = "MM-003-local-small-vlm-baseline-execution-v2"

MODEL_ID = v1.MODEL_ID
MODEL_REVISION = v1.MODEL_REVISION
MODEL_LICENSE = v1.MODEL_LICENSE
MODEL_LICENSE_SCOPE = v1.MODEL_LICENSE_SCOPE
MODEL_ARCHITECTURE = v1.MODEL_ARCHITECTURE
MODEL_WEIGHT_SHA256 = v1.MODEL_WEIGHT_SHA256
MODEL_FILE_SIZES = v1.MODEL_FILE_SIZES
MM002_SUITE_PATH = v1.MM002_SUITE_PATH
MM002_SUITE_FILE_SHA256 = v1.MM002_SUITE_FILE_SHA256
MM002_SUITE_CANONICAL_SHA256 = v1.MM002_SUITE_CANONICAL_SHA256
MM002_SCHEMA_PATH = v1.MM002_SCHEMA_PATH
MM002_SCHEMA_SHA256 = v1.MM002_SCHEMA_SHA256
SCREENSHOT_ROOT = v1.SCREENSHOT_ROOT
SCREENSHOT_CASES = v1.SCREENSHOT_CASES
CASE_ORDER = v1.CASE_ORDER
CASE_MODES = v1.CASE_MODES
LOCKED_ENVIRONMENT = v1.LOCKED_ENVIRONMENT
SYSTEM_PROMPT = v1.SYSTEM_PROMPT
PNG_WIDTH = v1.PNG_WIDTH
PNG_HEIGHT = v1.PNG_HEIGHT

PREREGISTRATION_PATH = "configs/mm003_multimodal_gui_action_model_baseline_v2.json"
RUN_ARTIFACT_PATH = "baseline/mm003-qwen2.5-vl-3b-baseline-v2-run.json"
PREDICTIONS_ARTIFACT_PATH = "baseline/mm003-qwen2.5-vl-3b-baseline-v2-predictions.json"
EVIDENCE_ARTIFACT_PATH = "baseline/mm003-qwen2.5-vl-3b-baseline-v2.json"
FAILURE_ARTIFACT_PATH = "baseline/mm003-qwen2.5-vl-3b-baseline-v2-failure.json"

V1_FAILURE_ARTIFACT_PATH = (
    "baseline/mm003-qwen2.5-vl-3b-baseline-v1-failure-classification.json"
)
V1_FAILURE_ARTIFACT_BYTES = 4_480
V1_FAILURE_ARTIFACT_SHA256 = (
    "sha256:fc8ef58286f425c03e8f20148c1b2b014c29be4468b61f8c0e650f507ec2dce6"
)

CONTRACT_SOURCE_PATH = "src/fullcycle_bridge/mm003_baseline_protocol_v2.py"
RUNNER_SOURCE_PATH = "scripts/run_mm003_multimodal_gui_action_baseline_v2.py"
SCORER_SOURCE_PATH = "src/fullcycle_bridge/gui_grounding_eval_v2.py"
PROTOCOL_SOURCE_PATHS = {
    "base_contract": v1.CONTRACT_SOURCE_PATH,
    "base_runner": v1.RUNNER_SOURCE_PATH,
    "base_scorer": v1.SCORER_SOURCE_PATH,
    "recovery_contract": CONTRACT_SOURCE_PATH,
    "recovery_runner": RUNNER_SOURCE_PATH,
    "recovery_scorer": SCORER_SOURCE_PATH,
}
_BASE_SOURCE_KEYS = {
    "contract": "base_contract",
    "runner": "base_runner",
    "scorer": "base_scorer",
}
_SHA256_PATTERN = re.compile(r"sha256:[0-9a-f]{64}")

MM003ProtocolError = v1.MM003ProtocolError
artifact_json_bytes = v1.artifact_json_bytes
canonical_json_bytes = v1.canonical_json_bytes
sha256_bytes = v1.sha256_bytes
parse_strict_json_bytes = v1.parse_strict_json_bytes
filtered_model_input = v1.filtered_model_input
build_user_prompt = v1.build_user_prompt
compile_raw_prediction = v1.compile_raw_prediction
render_case_png = v1.render_case_png


def expected_preregistration(
    *,
    freeze_status: str,
    model_files: Sequence[Mapping[str, Any]],
    screenshot_files: Sequence[Mapping[str, Any]],
    protocol_source_hashes: Mapping[str, str],
) -> dict[str, Any]:
    """Build v2 while preserving every model/input/generation decision from v1."""

    if set(protocol_source_hashes) != set(PROTOCOL_SOURCE_PATHS):
        _fail("INVALID_SOURCE_KEYS", "$.source_lineage.protocol_sources")
    for name, digest in protocol_source_hashes.items():
        if not isinstance(digest, str) or _SHA256_PATTERN.fullmatch(digest) is None:
            _fail("INVALID_SHA256", f"$.source_lineage.protocol_sources.{name}.sha256")
    base_hashes = {
        base_name: protocol_source_hashes[v2_name]
        for base_name, v2_name in _BASE_SOURCE_KEYS.items()
    }
    result = v1.expected_preregistration(
        freeze_status=freeze_status,
        model_files=model_files,
        screenshot_files=screenshot_files,
        protocol_source_hashes=base_hashes,
    )
    result["preregistration_version"] = PREREGISTRATION_VERSION
    result["experiment_id"] = EXPERIMENT_ID
    result["gate_id"] = GATE_ID
    result["scope"]["decision"] = "local_small_vlm_baseline_recovery_measurement_only"
    result["source_lineage"]["protocol_sources"] = {
        name: {
            "path": PROTOCOL_SOURCE_PATHS[name],
            "sha256": protocol_source_hashes[name],
        }
        for name in sorted(PROTOCOL_SOURCE_PATHS)
    }
    result["source_lineage"]["v1_failure_classification"] = {
        "path": V1_FAILURE_ARTIFACT_PATH,
        "bytes": V1_FAILURE_ARTIFACT_BYTES,
        "sha256": V1_FAILURE_ARTIFACT_SHA256,
        "failed_gate_id": "MM-003-local-small-vlm-baseline-execution-v1",
        "formal_gate_passed": False,
    }
    result["execution_protocol"]["outputs"] = {
        "run": RUN_ARTIFACT_PATH,
        "predictions": PREDICTIONS_ARTIFACT_PATH,
        "evidence": EVIDENCE_ARTIFACT_PATH,
        "failure": FAILURE_ARTIFACT_PATH,
    }
    result["execution_protocol"]["scoring_policy"] = {
        "core_suite_denominators": "positive_required",
        "prediction_coordinate_ref_disagreement_rate_zero_denominator": (
            "not_applicable"
        ),
        "not_applicable_value": None,
    }
    result["execution_protocol"]["persistence_policy"] = {
        "output_directory_must_be_absent_before_load": True,
        "raw_run_written_before_scoring": True,
        "compiled_predictions_written_before_scoring": True,
        "writes_are_exclusive": True,
        "scoring_failure_receipt_required": True,
        "success_evidence_written_after_scoring": True,
    }
    result["measurements"]["prediction_dependent_diagnostics"] = [
        "prediction_coordinate_ref_disagreement_rate"
    ]
    result["formal_gate"].update(
        {
            "requires_prediction_dependent_metric_totality": True,
            "requires_prescore_candidate_persistence": True,
            "requires_scoring_failure_receipt_policy": True,
        }
    )
    result["recovery_constraints"] = {
        "v1_protocol_or_artifact_rewrite": False,
        "model_or_revision_change": False,
        "synthetic_input_change": False,
        "prompt_change": False,
        "compiler_change": False,
        "generation_change": False,
        "eval_answer_change": False,
        "quality_threshold_added": False,
    }
    result["next_gate_after_freeze"] = {
        "gate_id": EXECUTION_GATE_ID,
        "action": (
            "execute the newly frozen recovery baseline exactly once with one "
            "fresh load, nine ordered calls, zero retries, prescore candidate "
            "persistence, and total scoring"
        ),
    }
    return result


def validate_preregistration(
    value: Mapping[str, Any], *, require_frozen: bool = True
) -> dict[str, Any]:
    """Recompute every v2 field while treating only content receipts as inputs."""

    model = _mapping(value.get("model"), "$.model")
    lineage = _mapping(value.get("source_lineage"), "$.source_lineage")
    sources = _mapping(
        lineage.get("protocol_sources"), "$.source_lineage.protocol_sources"
    )
    hashes: dict[str, str] = {}
    for name, path in PROTOCOL_SOURCE_PATHS.items():
        receipt = _mapping(
            sources.get(name), f"$.source_lineage.protocol_sources.{name}"
        )
        if receipt.get("path") != path:
            _fail(
                "SOURCE_PATH_MISMATCH", f"$.source_lineage.protocol_sources.{name}.path"
            )
        digest = receipt.get("sha256")
        if not isinstance(digest, str) or _SHA256_PATTERN.fullmatch(digest) is None:
            _fail("INVALID_SHA256", f"$.source_lineage.protocol_sources.{name}.sha256")
        hashes[name] = digest
    status = value.get("freeze_status")
    expected = expected_preregistration(
        freeze_status=str(status),
        model_files=_sequence(model.get("files"), "$.model.files"),
        screenshot_files=_sequence(
            lineage.get("screenshots"), "$.source_lineage.screenshots"
        ),
        protocol_source_hashes=hashes,
    )
    if dict(value) != expected:
        _fail("PREREGISTRATION_RECOMPUTATION_MISMATCH", "$.preregistration")
    if require_frozen and status != "frozen":
        _fail("PREREGISTRATION_NOT_FROZEN", "$.freeze_status")
    return expected


def _mapping(value: object, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail("EXPECTED_OBJECT", location)
    return value


def _sequence(value: object, location: str) -> Sequence[Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        _fail("EXPECTED_ARRAY", location)
    return cast(Sequence[Mapping[str, Any]], value)


def _fail(code: str, location: str) -> NoReturn:
    raise MM003ProtocolError(code, location)


__all__ = [
    "CASE_MODES",
    "CASE_ORDER",
    "EVIDENCE_ARTIFACT_PATH",
    "EXECUTION_GATE_ID",
    "EXPERIMENT_ID",
    "FAILURE_ARTIFACT_PATH",
    "GATE_ID",
    "LOCKED_ENVIRONMENT",
    "MODEL_FILE_SIZES",
    "MODEL_ID",
    "MODEL_REVISION",
    "PREDICTIONS_ARTIFACT_PATH",
    "PREREGISTRATION_PATH",
    "PROTOCOL_SOURCE_PATHS",
    "RUN_ARTIFACT_PATH",
    "SCREENSHOT_CASES",
    "SCREENSHOT_ROOT",
    "artifact_json_bytes",
    "build_user_prompt",
    "canonical_json_bytes",
    "compile_raw_prediction",
    "expected_preregistration",
    "parse_strict_json_bytes",
    "render_case_png",
    "sha256_bytes",
    "validate_preregistration",
]
