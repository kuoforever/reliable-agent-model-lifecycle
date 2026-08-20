"""Recompute the frozen MM-003 QLoRA v2 result review without model imports."""

from __future__ import annotations

import argparse
import math
import os
import re
import stat
import struct
import sys
from array import array
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, NoReturn, cast

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SRC))

from fullcycle_bridge import gui_grounding_eval as base_scorer  # noqa: E402
from fullcycle_bridge import gui_grounding_eval_v2 as scorer  # noqa: E402
from fullcycle_bridge import mm003_post_training_protocol_v2 as contract  # noqa: E402
from scripts import run_mm003_qlora_post_training_v2 as runner  # noqa: E402
from scripts import validate_mm003_baseline_v2_evidence as baseline_validator  # noqa: E402

PROTOCOL_FREEZE_COMMIT = "3751a041ff12886a337df0066232379016fdbd9c"
PREREGISTRATION_BYTES = 26_553
PREREGISTRATION_SHA256 = (
    "sha256:02e36d5981e0ed4ac90bfdb3c5cc9c9e1f78ff29ff927020b0a41ebb27f55c0e"
)
REVIEW_GATE_ID = "MM-003-small-vlm-post-training-result-review-v2"
NEXT_GATE_ID = "MM-003-small-vlm-post-training-eval-repeatability-protocol-v1"
CLASSIFICATION = (
    "specific_synthetic_metric_improvement_with_rejection_failures_"
    "and_repeatability_unestablished"
)
BASELINE_RECEIPT = {
    "path": "baseline/mm003-qwen2.5-vl-3b-baseline-v2.json",
    "bytes": 4_680,
    "sha256": (
        "sha256:a0e3c2503e5bac13bf979c7721dab4350681a84883d749b94ef3ca204d2166fe"
    ),
}
MM002_SUITE_RECEIPT = {
    "path": "fixtures/gui_grounding_eval_v1/valid/suite.json",
    "bytes": 13_097,
    "sha256": (
        "sha256:c59ea8314cad0ae936fadd6648cc270e3332d40115ed1ca6f9c00730c85c7b2e"
    ),
}
ARTIFACTS: dict[str, dict[str, int | str]] = {
    "training_run": {
        "path": "baseline/mm003-qwen2.5-vl-3b-qlora-sft-v2-training-run.json",
        "bytes": 6_853,
        "sha256": (
            "sha256:474595081a20c46a62f664459b734d57ec03c8ddf121c9aedc055e16a052c516"
        ),
    },
    "predictions": {
        "path": "baseline/mm003-qwen2.5-vl-3b-qlora-sft-v2-predictions.json",
        "bytes": 2_241,
        "sha256": (
            "sha256:c2c703e5896fe64df9e156bda9d38975b92c1bf18c72f74f5a232dcbbbc4a028"
        ),
    },
    "evidence": {
        "path": "baseline/mm003-qwen2.5-vl-3b-qlora-sft-v2-evidence.json",
        "bytes": 21_122,
        "sha256": (
            "sha256:2190281e3e8acf97139e08c9949535a07b326897e23c5999a7f4750fccedabd5"
        ),
    },
    "adapter_readme": {
        "path": "baseline/adapters/mm003-qwen2.5-vl-3b-qlora-sft-v2/README.md",
        "bytes": 206,
        "sha256": (
            "sha256:a73f9a4e826eca0a56f08ac2e7d415670b29eaae02bf501aa838ac23aaf3ebdb"
        ),
    },
    "adapter_config": {
        "path": (
            "baseline/adapters/mm003-qwen2.5-vl-3b-qlora-sft-v2/"
            "adapter_config.json"
        ),
        "bytes": 791,
        "sha256": (
            "sha256:e8edf34169cc15c25e98965a5873e27c6eb54f4f95543e60d0452ec2fec60055"
        ),
    },
    "adapter_weights": {
        "path": (
            "baseline/adapters/mm003-qwen2.5-vl-3b-qlora-sft-v2/"
            "adapter_model.safetensors"
        ),
        "bytes": 29_529_752,
        "sha256": (
            "sha256:d93d2ea2d9f05564093cbb0b1286d2c368c54b01e847f1c37a98e00fb2914701"
        ),
    },
}
REVIEW_PATH = "baseline/mm003-qwen2.5-vl-3b-qlora-sft-v2-result-review.json"
REVIEW_BYTES = 11_311
REVIEW_SHA256 = (
    "sha256:3dff57b17eb4fc9966ab53fe92faea8921fb34b485e389aaa19af64610db957d"
)

_TIMESTAMP = re.compile(r"20[0-9]{2}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z")
_TENSOR_KEY = re.compile(
    r"base_model\.model\.model\.layers\.([0-9]+)\.self_attn\."
    r"(q_proj|k_proj|v_proj|o_proj)\.lora_([AB])\.weight"
)
_OVERALL_METRICS = (
    "grounding_accuracy",
    "mean_iou",
    "action_accuracy",
    "tool_accuracy",
    "argument_exact_match",
    "stale_ref_rejection",
    "coordinate_ref_disagreement_rejection",
)


class MM003PostTrainingV2ResultError(ValueError):
    """Raised when the frozen execution or review cannot be reproduced."""


def validate_repository(root: Path = ROOT) -> dict[str, Any]:
    _require_canonical_repository_root(root)
    expected_review, summary = build_repository_review(root)
    review_payload = _read_exact(
        root,
        root / REVIEW_PATH,
        expected_bytes=REVIEW_BYTES,
        expected_sha256=REVIEW_SHA256,
        label="result review",
    )
    review = _object(review_payload, "$.review")
    if contract.artifact_json_bytes(review) != review_payload:
        _fail("NONCANONICAL_REVIEW_JSON")
    if review != expected_review:
        _fail("RESULT_REVIEW_RECOMPUTATION_MISMATCH")
    return summary


def build_repository_review(root: Path = ROOT) -> tuple[dict[str, Any], dict[str, Any]]:
    _require_canonical_repository_root(root)
    suite = _load_safe_mm002_suite(root)
    _validate_zero_shot_baseline(root, suite)
    preregistration_payload = _read_exact(
        root,
        root / contract.PREREGISTRATION_PATH,
        expected_bytes=PREREGISTRATION_BYTES,
        expected_sha256=PREREGISTRATION_SHA256,
        label="preregistration",
    )
    baseline_payload = _read_exact(
        root,
        root / str(BASELINE_RECEIPT["path"]),
        expected_bytes=int(BASELINE_RECEIPT["bytes"]),
        expected_sha256=str(BASELINE_RECEIPT["sha256"]),
        label="zero-shot baseline",
    )
    payloads = {
        name: _read_exact(
            root,
            root / str(receipt["path"]),
            expected_bytes=int(receipt["bytes"]),
            expected_sha256=str(receipt["sha256"]),
            label=name,
        )
        for name, receipt in ARTIFACTS.items()
    }
    failure_path, failure_parents = _safe_repository_parent_chain(
        root,
        root / "baseline/mm003-qwen2.5-vl-3b-qlora-sft-v2-failure.json",
        "success failure artifact",
    )
    if os.path.lexists(failure_path):
        _fail("SUCCESS_FAILURE_ARTIFACT_PRESENT")
    _recheck_repository_parent_chain(failure_parents, "success failure artifact")
    return validate_execution_payloads(
        preregistration_payload=preregistration_payload,
        baseline_payload=baseline_payload,
        payloads=payloads,
        suite=suite,
        repository_root=root,
    )


def _load_safe_mm002_suite(root: Path) -> dict[str, Any]:
    payload = _read_exact(
        root,
        root / str(MM002_SUITE_RECEIPT["path"]),
        expected_bytes=int(MM002_SUITE_RECEIPT["bytes"]),
        expected_sha256=str(MM002_SUITE_RECEIPT["sha256"]),
        label="MM-002 suite",
    )
    suite = _object(payload, "$.mm002_suite")
    try:
        base_scorer.validate_suite(suite)
    except base_scorer.GuiGroundingValidationError as exc:
        raise MM003PostTrainingV2ResultError("MM002_SUITE_INVALID") from exc
    return suite


def _validate_zero_shot_baseline(
    root: Path, suite: Mapping[str, Any]
) -> None:
    preregistration_payload = _read_exact(
        root,
        root / baseline_validator.contract.PREREGISTRATION_PATH,
        expected_bytes=baseline_validator.PREREGISTRATION_BYTES,
        expected_sha256=baseline_validator.PREREGISTRATION_SHA256,
        label="zero-shot preregistration",
    )
    payloads = {
        name: _read_exact(
            root,
            root / str(receipt["path"]),
            expected_bytes=int(receipt["bytes"]),
            expected_sha256=str(receipt["sha256"]),
            label=f"zero-shot {name}",
        )
        for name, receipt in baseline_validator.ARTIFACTS.items()
    }
    failure_path, failure_parents = _safe_repository_parent_chain(
        root,
        root / baseline_validator.contract.FAILURE_ARTIFACT_PATH,
        "zero-shot failure artifact",
    )
    if os.path.lexists(failure_path):
        _fail("ZERO_SHOT_SUCCESS_FAILURE_ARTIFACT_PRESENT")
    _recheck_repository_parent_chain(
        failure_parents, "zero-shot failure artifact"
    )
    try:
        baseline_validator.validate_payloads(
            preregistration_payload=preregistration_payload,
            run_payload=payloads["run"],
            predictions_payload=payloads["predictions"],
            evidence_payload=payloads["evidence"],
            suite=suite,
        )
    except baseline_validator.MM003BaselineV2EvidenceError as exc:
        raise MM003PostTrainingV2ResultError(
            "ZERO_SHOT_BASELINE_RECOMPUTATION_MISMATCH"
        ) from exc
    preregistration = baseline_validator._object(
        preregistration_payload, "$.zero_shot_preregistration"
    )
    source_receipts = baseline_validator._mapping(
        baseline_validator._mapping(
            preregistration["source_lineage"], "$.source_lineage"
        )["protocol_sources"],
        "$.source_lineage.protocol_sources",
    )
    expected_source_hashes = {
        name: baseline_validator._mapping(
            receipt, f"$.source_lineage.protocol_sources.{name}"
        )["sha256"]
        for name, receipt in source_receipts.items()
    }
    if baseline_validator.runner.protocol_source_hashes() != expected_source_hashes:
        _fail("ZERO_SHOT_PROTOCOL_SOURCE_HASH_MISMATCH")


def validate_execution_payloads(
    *,
    preregistration_payload: bytes,
    baseline_payload: bytes,
    payloads: Mapping[str, bytes],
    suite: Mapping[str, Any],
    repository_root: Path = ROOT,
) -> tuple[dict[str, Any], dict[str, Any]]:
    _require_canonical_repository_root(repository_root)
    _check_payload_receipt(
        preregistration_payload,
        expected_bytes=PREREGISTRATION_BYTES,
        expected_sha256=PREREGISTRATION_SHA256,
        label="preregistration",
    )
    _check_payload_receipt(
        baseline_payload,
        expected_bytes=int(BASELINE_RECEIPT["bytes"]),
        expected_sha256=str(BASELINE_RECEIPT["sha256"]),
        label="zero-shot baseline",
    )
    if set(payloads) != set(ARTIFACTS):
        _fail("ARTIFACT_SET_MISMATCH")
    for name, receipt in ARTIFACTS.items():
        _check_payload_receipt(
            payloads[name],
            expected_bytes=int(receipt["bytes"]),
            expected_sha256=str(receipt["sha256"]),
            label=name,
        )

    inputs = runner.load_and_validate_inputs()
    lineage = runner._load_recovery_lineage()
    preregistration = contract.validate_preregistration(
        _object(preregistration_payload, "$.preregistration"),
        v1_preregistration=lineage["v1_preregistration"],
        train=inputs["train"],
        validation=inputs["validation"],
        source_hashes=runner.protocol_source_hashes(),
    )
    if contract.artifact_json_bytes(preregistration) != preregistration_payload:
        _fail("PREREGISTRATION_RECOMPUTATION_MISMATCH")

    training = _canonical_object(payloads["training_run"], "training run")
    predictions = _canonical_object(payloads["predictions"], "predictions")
    evidence = _canonical_object(payloads["evidence"], "evidence")
    baseline = _canonical_object(baseline_payload, "zero-shot baseline")
    adapter_config = _canonical_object(payloads["adapter_config"], "adapter config")
    adapter_audit = inspect_mm003_adapter_safetensors_bytes(
        payloads["adapter_weights"]
    )

    _validate_adapter(
        training=training,
        adapter_config=adapter_config,
        adapter_audit=adapter_audit,
        payloads=payloads,
    )
    _validate_training(training, preregistration)
    evaluation = _validate_evaluation(
        evidence=evidence,
        predictions=predictions,
        suite=suite,
        eval_screenshot_receipts=inputs["eval_screenshot_receipts"],
    )
    _validate_evidence(
        evidence=evidence,
        training=training,
        evaluation=evaluation,
        preregistration=preregistration,
        preregistration_payload=preregistration_payload,
        inputs=inputs,
    )
    taxonomy = _failure_taxonomy(suite=suite, predictions=predictions)
    review = build_review(
        baseline=baseline,
        training=training,
        evidence=evidence,
        adapter_audit=adapter_audit,
        taxonomy=taxonomy,
    )
    metrics = _mapping(
        _mapping(evidence["evaluation"], "$.evidence.evaluation")["score"],
        "$.evidence.evaluation.score",
    )["metrics"]
    summary = {
        "formal_gate_passed": True,
        "classification": CLASSIFICATION,
        "training_executed": True,
        "adapter_independently_loadable": True,
        "model_evaluated": True,
        "compiler_fallback_count": 0,
        "grounding_accuracy": _mapping(metrics, "$.metrics")["grounding_accuracy"],
        "action_accuracy": _mapping(metrics, "$.metrics")["action_accuracy"],
        "repeatability_established": False,
        "next_gate": NEXT_GATE_ID,
        "runtime_eligible": False,
    }
    return review, summary


def build_review(
    *,
    baseline: Mapping[str, Any],
    training: Mapping[str, Any],
    evidence: Mapping[str, Any],
    adapter_audit: Mapping[str, Any],
    taxonomy: Mapping[str, Any],
) -> dict[str, Any]:
    baseline_metrics = _mapping(
        _mapping(baseline["quality"], "$.baseline.quality")["overall"],
        "$.baseline.quality.overall",
    )
    current_metrics = _mapping(
        _mapping(
            _mapping(evidence["evaluation"], "$.evidence.evaluation")["score"],
            "$.evidence.evaluation.score",
        )["metrics"],
        "$.evidence.evaluation.score.metrics",
    )
    comparisons: dict[str, Any] = {}
    improved: list[str] = []
    unchanged: list[str] = []
    regressed: list[str] = []
    for name in _OVERALL_METRICS:
        baseline_result = _mapping(baseline_metrics[name], f"$.baseline.{name}")
        current_result = _mapping(current_metrics[name], f"$.current.{name}")
        baseline_value = _finite_number(baseline_result["value"], "BASELINE_METRIC")
        current_value = _finite_number(current_result["value"], "CURRENT_METRIC")
        delta = current_value - baseline_value
        comparisons[name] = {
            "baseline": dict(baseline_result),
            "post_training": dict(current_result),
            "value_delta": delta,
        }
        if delta > 0:
            improved.append(name)
        elif delta < 0:
            regressed.append(name)
        else:
            unchanged.append(name)
    optional_metric = "prediction_coordinate_ref_disagreement_rate"
    comparisons[optional_metric] = {
        "baseline": dict(
            _mapping(baseline_metrics[optional_metric], "$.baseline.optional_metric")
        ),
        "post_training": dict(
            _mapping(current_metrics[optional_metric], "$.current.optional_metric")
        ),
        "value_delta": None,
        "comparison_status": "not_applicable_in_both_runs",
    }
    if improved != [
        "grounding_accuracy",
        "mean_iou",
        "action_accuracy",
        "tool_accuracy",
        "argument_exact_match",
    ] or unchanged != [
        "stale_ref_rejection",
        "coordinate_ref_disagreement_rejection",
    ] or regressed:
        _fail("METRIC_COMPARISON_CLASSIFICATION_MISMATCH")

    epoch_metrics = _sequence(training["epoch_metrics"], "$.training.epoch_metrics")
    evidence_claims = _mapping(evidence["claims"], "$.evidence.claims")
    return {
        "review_version": 1,
        "gate_id": REVIEW_GATE_ID,
        "reviewed_execution_gate_id": contract.EXECUTION_GATE_ID,
        "classification": CLASSIFICATION,
        "protocol": {
            "freeze_commit": PROTOCOL_FREEZE_COMMIT,
            "preregistration": {
                "path": contract.PREREGISTRATION_PATH,
                "bytes": PREREGISTRATION_BYTES,
                "sha256": PREREGISTRATION_SHA256,
            },
        },
        "frozen_artifacts": {
            name: dict(receipt) for name, receipt in ARTIFACTS.items()
        },
        "formal_measurement": {
            "required_gates": list(contract.REQUIRED_GATES),
            "passed_gates": [
                name
                for name, passed in _mapping(
                    evidence["gates"], "$.evidence.gates"
                ).items()
                if passed is True
            ],
            "formal_gate_passed": True,
            "quality_threshold_registered": False,
        },
        "training": {
            "train_records": 18,
            "validation_records": 9,
            "optimizer_steps": training["optimizer_steps"],
            "trainable_parameters": training["trainable_parameters"],
            "epoch_losses": [
                {
                    "epoch": item["epoch"],
                    "mean_train_loss": item["mean_train_loss"],
                    "mean_validation_loss": item["mean_validation_loss"],
                }
                for item in epoch_metrics
            ],
        },
        "adapter": {
            "manifest": list(
                _sequence(training["adapter_manifest"], "$.training.adapter_manifest")
            ),
            "safetensors_audit": dict(adapter_audit),
            "independent_loads_observed_in_execution": 1,
            "review_reloads_model": False,
        },
        "evaluation": {
            "suite_id": _mapping(
                _mapping(evidence["evaluation"], "$.evidence.evaluation")["score"],
                "$.evidence.evaluation.score",
            )["suite_id"],
            "producer": dict(
                _mapping(
                    _mapping(
                        _mapping(evidence["evaluation"], "$.evidence.evaluation")[
                            "predictions"
                        ],
                        "$.evidence.evaluation.predictions",
                    )["producer"],
                    "$.evidence.evaluation.predictions.producer",
                )
            ),
            "case_count": 9,
            "compiler_fallback_count": 0,
            "metrics": {name: dict(_mapping(value, f"$.metrics.{name}")) for name, value in current_metrics.items()},
            "zero_shot_comparison": {
                "baseline_receipt": dict(BASELINE_RECEIPT),
                "metrics": comparisons,
                "improved_metric_names": improved,
                "unchanged_metric_names": unchanged,
                "regressed_metric_names": regressed,
                "baseline_compiler_fallback_count": 9,
                "post_training_compiler_fallback_count": 0,
            },
            "bad_case_taxonomy": dict(taxonomy),
            "eval_gold_training_use_prohibited": True,
        },
        "resources": dict(_mapping(evidence["resources"], "$.evidence.resources")),
        "claims": {
            "formal_measurement_established": True,
            "training_executed": evidence_claims["training_executed"],
            "adapter_created": evidence_claims["adapter_created"],
            "adapter_independently_loadable": evidence_claims[
                "adapter_independently_loadable"
            ],
            "model_evaluated": evidence_claims["model_evaluated"],
            "specific_synthetic_metric_improvements_observed": True,
            "generalized_quality_improvement_established": False,
            "safety_rejection_success_established": False,
            "repeatability_established": False,
            "cross_machine_reproducibility": False,
            "portable_artifact": False,
            "commercial_use_eligible": False,
            "serving_eligible": False,
            "promotion_eligible": False,
            "runtime_eligible": False,
        },
        "limitations": {
            "single_local_training_run": True,
            "single_local_eval_run": True,
            "synthetic_eval_only": True,
            "quality_threshold_registered": False,
            "training_repeatability_tested": False,
            "eval_repeatability_tested": False,
            "real_content_tested": False,
            "direct_execution_tested": False,
            "runtime_integration_tested": False,
        },
        "next_gate": NEXT_GATE_ID,
        "next_action": (
            "freeze an outcome-neutral same-environment replay protocol for the "
            "unchanged Adapter and MM-002 eval before any repeat execution"
        ),
        "runtime_eligible": False,
    }


def inspect_mm003_adapter_safetensors_bytes(payload: bytes) -> dict[str, Any]:
    if len(payload) < 8:
        _fail("SAFETENSORS_HEADER_MISSING")
    header_bytes = struct.unpack("<Q", payload[:8])[0]
    data_start = 8 + header_bytes
    if header_bytes == 0 or header_bytes % 8 != 0 or data_start > len(payload):
        _fail("SAFETENSORS_HEADER_LENGTH_MISMATCH")
    header = _object(payload[8:data_start], "$.adapter_weights.header")
    metadata = header.pop("__metadata__", None)
    if metadata != {"format": "pt"}:
        _fail("SAFETENSORS_METADATA_MISMATCH")

    expected_keys = {
        (
            f"base_model.model.model.layers.{layer}.self_attn.{projection}."
            f"lora_{factor}.weight"
        )
        for layer in range(36)
        for projection in ("q_proj", "k_proj", "v_proj", "o_proj")
        for factor in ("A", "B")
    }
    if set(header) != expected_keys:
        _fail("ADAPTER_TENSOR_TOPOLOGY_MISMATCH")

    offset_records: list[tuple[int, int, str]] = []
    parameter_count = 0
    shape_counts: dict[str, int] = {}
    for name, raw_tensor in header.items():
        match = _TENSOR_KEY.fullmatch(name)
        tensor = _mapping(raw_tensor, f"$.adapter_weights.header.{name}")
        if match is None or set(tensor) != {"dtype", "shape", "data_offsets"}:
            _fail("ADAPTER_TENSOR_RECORD_MISMATCH")
        projection = match.group(2)
        factor = match.group(3)
        expected_shape = [16, 2048]
        if factor == "B":
            expected_shape = [2048, 16] if projection in {"q_proj", "o_proj"} else [256, 16]
        shape = tensor["shape"]
        offsets = tensor["data_offsets"]
        if tensor["dtype"] != "F32" or shape != expected_shape:
            _fail("ADAPTER_TENSOR_DTYPE_OR_SHAPE_MISMATCH")
        if (
            not isinstance(offsets, list)
            or len(offsets) != 2
            or any(not isinstance(value, int) or isinstance(value, bool) for value in offsets)
            or offsets[0] < 0
            or offsets[1] <= offsets[0]
        ):
            _fail("ADAPTER_TENSOR_OFFSET_MISMATCH")
        elements = math.prod(expected_shape)
        if offsets[1] - offsets[0] != elements * 4:
            _fail("ADAPTER_TENSOR_BYTE_SPAN_MISMATCH")
        parameter_count += elements
        shape_name = "x".join(str(value) for value in expected_shape)
        shape_counts[shape_name] = shape_counts.get(shape_name, 0) + 1
        offset_records.append((offsets[0], offsets[1], name))

    cursor = 0
    for start, end, _ in sorted(offset_records):
        if start != cursor:
            _fail("ADAPTER_TENSOR_OFFSETS_NOT_CONTIGUOUS")
        cursor = end
    if data_start + cursor != len(payload):
        _fail("ADAPTER_TENSOR_PAYLOAD_LENGTH_MISMATCH")
    if parameter_count != 7_372_800 or shape_counts != {
        "16x2048": 144,
        "2048x16": 72,
        "256x16": 72,
    }:
        _fail("ADAPTER_PARAMETER_TOPOLOGY_MISMATCH")
    values = array("f")
    if values.itemsize != 4:
        _fail("ADAPTER_FLOAT32_PLATFORM_MISMATCH")
    values.frombytes(payload[data_start:])
    if sys.byteorder != "little":
        values.byteswap()
    if len(values) != parameter_count or not all(
        math.isfinite(value) for value in values
    ):
        _fail("ADAPTER_TENSOR_NONFINITE_VALUES")
    return {
        "format": "safetensors",
        "metadata": {"format": "pt"},
        "header_bytes": header_bytes,
        "data_bytes": cursor,
        "tensor_count": len(header),
        "dtype_counts": {"F32": len(header)},
        "shape_counts": shape_counts,
        "layer_count": 36,
        "target_modules": ["k_proj", "o_proj", "q_proj", "v_proj"],
        "parameter_count": parameter_count,
        "all_values_finite": True,
    }


def _validate_adapter(
    *,
    training: Mapping[str, Any],
    adapter_config: Mapping[str, Any],
    adapter_audit: Mapping[str, Any],
    payloads: Mapping[str, bytes],
) -> None:
    if (
        adapter_config.get("base_model_name_or_path") != contract.MODEL_ID
        or adapter_config.get("revision") != contract.MODEL_REVISION
        or adapter_config.get("peft_type") != "LORA"
        or adapter_config.get("task_type") != "CAUSAL_LM"
        or adapter_config.get("r") != 16
        or adapter_config.get("lora_alpha") != 32
        or adapter_config.get("lora_dropout") != 0.05
        or set(cast(Sequence[str], adapter_config.get("target_modules")))
        != {"q_proj", "k_proj", "v_proj", "o_proj"}
    ):
        _fail("ADAPTER_CONFIG_MISMATCH")
    expected_manifest = [
        _named_adapter_receipt("adapter_readme", "README.md", payloads),
        _named_adapter_receipt("adapter_config", "adapter_config.json", payloads),
        _named_adapter_receipt(
            "adapter_weights", "adapter_model.safetensors", payloads
        ),
    ]
    if training.get("adapter_manifest") != expected_manifest:
        _fail("ADAPTER_MANIFEST_MISMATCH")
    if (
        adapter_audit.get("tensor_count") != 288
        or adapter_audit.get("parameter_count") != training.get("trainable_parameters")
    ):
        _fail("ADAPTER_AUDIT_MISMATCH")


def _validate_training(
    training: Mapping[str, Any], preregistration: Mapping[str, Any]
) -> None:
    if (
        training.get("training_run_version") != 1
        or training.get("experiment_id") != contract.EXPERIMENT_ID
        or training.get("gate_id") != contract.EXECUTION_GATE_ID
        or training.get("protocol")
        != {
            "freeze_commit": PROTOCOL_FREEZE_COMMIT,
            "preregistration_sha256": PREREGISTRATION_SHA256,
        }
        or training.get("model")
        != {
            "repo_id": contract.MODEL_ID,
            "revision": contract.MODEL_REVISION,
            "files": preregistration["model"]["files"],
        }
        or training.get("environment") != contract.LOCKED_ENVIRONMENT
        or training.get("execution")
        != {
            "fresh_train_model_loads": 1,
            "full_training_runs": 1,
            "network_used": False,
            "retry_count": 0,
            "training_completed": True,
        }
        or training.get("optimizer_steps") != 18
        or training.get("trainable_parameters") != 7_372_800
    ):
        _fail("TRAINING_IDENTITY_OR_EXECUTION_MISMATCH")
    data = _mapping(training.get("data"), "$.training.data")
    if (
        data.get("train_records") != 18
        or data.get("validation_records") != 9
        or data.get("eval_isolation") != preregistration["source_lineage"]["eval_isolation"]
    ):
        _fail("TRAINING_DATA_BINDING_MISMATCH")
    epochs = _sequence(training.get("epoch_metrics"), "$.training.epoch_metrics")
    if len(epochs) != 3:
        _fail("TRAINING_EPOCH_COUNT_MISMATCH")
    train_case_ids = {
        record["case_id"]
        for record in _sequence(
            runner.load_and_validate_inputs()["train"]["records"], "$.train.records"
        )
    }
    previous_train_loss = math.inf
    previous_validation_loss = math.inf
    for index, epoch in enumerate(epochs, start=1):
        train_loss = _positive_finite_number(
            epoch.get("mean_train_loss"), "TRAIN_LOSS_MISMATCH"
        )
        validation_loss = _positive_finite_number(
            epoch.get("mean_validation_loss"), "VALIDATION_LOSS_MISMATCH"
        )
        order = epoch.get("record_order")
        if (
            epoch.get("epoch") != index
            or epoch.get("optimizer_steps_completed") != index * 6
            or not isinstance(order, list)
            or len(order) != 18
            or set(order) != train_case_ids
            or train_loss >= previous_train_loss
            or validation_loss >= previous_validation_loss
        ):
            _fail("TRAINING_EPOCH_RECORD_MISMATCH")
        previous_train_loss = train_loss
        previous_validation_loss = validation_loss
    resources = _mapping(training.get("resources"), "$.training.resources")
    for name in (
        "elapsed_seconds",
        "gpu_allocated_after_bytes",
        "gpu_reserved_after_bytes",
        "peak_gpu_allocated_bytes",
        "peak_gpu_reserved_bytes",
    ):
        _nonnegative_finite_number(resources.get(name), "TRAINING_RESOURCE_MISMATCH")
    if (
        resources.get("gpu_allocated_before_bytes") != 0
        or resources.get("gpu_reserved_before_bytes") != 0
    ):
        _fail("TRAINING_RESOURCE_BASELINE_MISMATCH")


def _validate_evaluation(
    *,
    evidence: Mapping[str, Any],
    predictions: Mapping[str, Any],
    suite: Mapping[str, Any],
    eval_screenshot_receipts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    evaluation = _mapping(evidence.get("evaluation"), "$.evidence.evaluation")
    if evaluation.get("predictions") != predictions:
        _fail("EVALUATION_PREDICTIONS_BINDING_MISMATCH")
    _validate_prediction_identity(predictions, suite)
    execution = evaluation.get("execution")
    if execution != {
        "fresh_base_loads": 1,
        "full_eval_runs": 1,
        "generate_calls": 9,
        "independent_adapter_loads": 1,
        "network_used": False,
        "retry_count": 0,
    }:
        _fail("EVALUATION_EXECUTION_MISMATCH")
    records = _sequence(predictions.get("records"), "$.predictions.records")
    cases = _sequence(evaluation.get("cases"), "$.evaluation.cases")
    suite_cases = {
        case["case_id"]: case
        for case in _sequence(suite.get("cases"), "$.suite.cases")
    }
    screenshot_hashes = {
        item["case_id"]: item["sha256"] for item in eval_screenshot_receipts
    }
    if len(records) != 9 or len(cases) != 9:
        _fail("EVALUATION_CASE_COUNT_MISMATCH")
    for index, (case_result, prediction) in enumerate(zip(cases, records, strict=True)):
        case_id = contract.baseline.CASE_ORDER[index]
        suite_case = suite_cases[case_id]
        raw_output = case_result.get("raw_output")
        expected_screenshot = screenshot_hashes.get(case_id)
        if (
            case_result.get("case_id") != case_id
            or prediction.get("case_id") != case_id
            or case_result.get("observation_mode") != contract.baseline.CASE_MODES[case_id]
            or not isinstance(raw_output, str)
            or contract.baseline.compile_raw_prediction(raw_output, suite_case)
            != prediction
            or case_result.get("compiled_prediction") != prediction
            or case_result.get("compiler_fallback") is not False
            or case_result.get("screenshot_sha256") != expected_screenshot
        ):
            _fail("EVALUATION_CASE_BINDING_MISMATCH")
        _positive_integer(case_result.get("generated_tokens"), "GENERATED_TOKENS_MISMATCH")
        _positive_finite_number(case_result.get("latency_seconds"), "LATENCY_MISMATCH")
    recomputed_score = scorer.score_predictions(suite, predictions)
    if evaluation.get("score") != recomputed_score:
        _fail("EVALUATION_SCORE_RECOMPUTATION_MISMATCH")
    return dict(evaluation)


def _validate_prediction_identity(
    predictions: Mapping[str, Any], suite: Mapping[str, Any]
) -> None:
    if (
        predictions.get("gui_grounding_prediction_version") != 1
        or predictions.get("suite_id") != suite.get("suite_id")
        or predictions.get("producer")
        != {
            "kind": "model",
            "model_id": contract.ADAPTER_MODEL_ID,
            "model_revision": contract.MODEL_REVISION,
        }
    ):
        _fail("PREDICTION_PRODUCER_IDENTITY_MISMATCH")


def _validate_evidence(
    *,
    evidence: Mapping[str, Any],
    training: Mapping[str, Any],
    evaluation: Mapping[str, Any],
    preregistration: Mapping[str, Any],
    preregistration_payload: bytes,
    inputs: Mapping[str, Any],
) -> None:
    captured_at = evidence.get("captured_at_utc")
    if not isinstance(captured_at, str) or _TIMESTAMP.fullmatch(captured_at) is None:
        _fail("EVIDENCE_TIMESTAMP_MISMATCH")
    prompt_preflight = contract.validate_prompt_preflight(
        preregistration,
        train=inputs["train"],
        validation=inputs["validation"],
    )
    recomputed = runner.build_evidence(
        preregistration=preregistration,
        preregistration_payload=preregistration_payload,
        protocol_freeze_commit=PROTOCOL_FREEZE_COMMIT,
        training=training,
        evaluation=evaluation,
        environment=training["environment"],
        model_manifest=training["model"]["files"],
        isolation_audit=training["data"]["eval_isolation"],
        prompt_preflight=prompt_preflight,
        lifecycle_resources=evidence["resources"],
    )
    recomputed["captured_at_utc"] = captured_at
    if recomputed != evidence:
        _fail("EVIDENCE_RECOMPUTATION_MISMATCH")
    claims = _mapping(evidence.get("claims"), "$.evidence.claims")
    if (
        list(_mapping(evidence.get("gates"), "$.evidence.gates"))
        != contract.REQUIRED_GATES
        or not all(_mapping(evidence["gates"], "$.evidence.gates").values())
        or evidence.get("formal_gate_passed") is not True
        or evidence.get("classification") != "local_qlora_adapter_measurement_established"
        or evidence.get("next_gate") != REVIEW_GATE_ID
        or evidence.get("runtime_eligible") is not False
        or claims
        != {
            "training_executed": True,
            "adapter_created": True,
            "adapter_independently_loadable": True,
            "model_evaluated": True,
            "quality_improved": False,
            "repeatability_established": False,
            "cross_machine_reproducibility": False,
            "portable_artifact": False,
            "commercial_use_eligible": False,
            "serving_eligible": False,
            "promotion_eligible": False,
            "runtime_eligible": False,
        }
    ):
        _fail("EVIDENCE_DECISION_OR_CLAIMS_MISMATCH")


def _failure_taxonomy(
    *, suite: Mapping[str, Any], predictions: Mapping[str, Any]
) -> dict[str, Any]:
    suite_cases = {
        case["case_id"]: case
        for case in _sequence(suite.get("cases"), "$.suite.cases")
    }
    records = {
        record["case_id"]: record
        for record in _sequence(predictions.get("records"), "$.predictions.records")
    }
    missing_fused_bbox: list[str] = []
    reject_to_fallback: list[str] = []
    fallback_reason_mismatch: list[str] = []
    exact_actions: list[str] = []
    unclassified: list[str] = []
    for case_id in contract.baseline.CASE_ORDER:
        gold = _mapping(suite_cases[case_id]["gold"], f"$.suite.{case_id}.gold")
        prediction = _mapping(records[case_id], f"$.predictions.{case_id}")
        comparable_fields = ("disposition", "tool", "arguments", "ref", "bbox", "reason")
        if all(prediction.get(name) == gold.get(name) for name in comparable_fields):
            exact_actions.append(case_id)
        elif (
            gold.get("disposition") == "act"
            and suite_cases[case_id]["observation_mode"] == "fused"
            and prediction.get("disposition") == "act"
            and prediction.get("ref") == gold.get("ref")
            and prediction.get("bbox") is None
            and gold.get("bbox") is not None
        ):
            missing_fused_bbox.append(case_id)
        elif gold.get("disposition") == "reject" and prediction.get("disposition") == "fallback":
            reject_to_fallback.append(case_id)
        elif (
            gold.get("disposition") == "fallback"
            and prediction.get("disposition") == "fallback"
            and prediction.get("reason") != gold.get("reason")
        ):
            fallback_reason_mismatch.append(case_id)
        else:
            unclassified.append(case_id)
    expected = {
        "exact_action_cases": ["ground-001", "ground-002", "ground-008"],
        "fused_grounding_missing_bbox": ["ground-003", "ground-006"],
        "reject_downgraded_to_fallback": [
            "ground-004",
            "ground-007",
            "ground-009",
        ],
        "fallback_reason_vocabulary_mismatch": ["ground-005"],
        "unclassified_cases": [],
        "compiler_fallback_cases": [],
    }
    observed = {
        "exact_action_cases": exact_actions,
        "fused_grounding_missing_bbox": missing_fused_bbox,
        "reject_downgraded_to_fallback": reject_to_fallback,
        "fallback_reason_vocabulary_mismatch": fallback_reason_mismatch,
        "unclassified_cases": unclassified,
        "compiler_fallback_cases": [],
    }
    if observed != expected:
        _fail("BAD_CASE_TAXONOMY_MISMATCH")
    return {
        **observed,
        "failed_action_cases": 6,
        "taxonomy_is_review_only": True,
        "eval_answers_may_not_be_copied_into_training": True,
    }


def _named_adapter_receipt(
    artifact_name: str, adapter_name: str, payloads: Mapping[str, bytes]
) -> dict[str, Any]:
    payload = payloads[artifact_name]
    return {
        "path": adapter_name,
        "bytes": len(payload),
        "sha256": contract.sha256_bytes(payload),
    }


def _read_exact(
    root: Path,
    path: Path,
    *,
    expected_bytes: int,
    expected_sha256: str,
    label: str,
) -> bytes:
    safe_path, parent_chain = _safe_repository_parent_chain(root, path, label)
    try:
        before = safe_path.lstat()
    except OSError as exc:
        raise MM003PostTrainingV2ResultError(
            f"MISSING_OR_UNSAFE_{label.upper().replace(' ', '_')}"
        ) from exc
    if (
        not stat.S_ISREG(before.st_mode)
        or _metadata_is_reparse(before)
        or before.st_nlink != 1
    ):
        _fail(f"MISSING_OR_UNSAFE_{label.upper().replace(' ', '_')}")
    if before.st_size != expected_bytes:
        _fail(f"{label.upper().replace(' ', '_')}_BYTE_MISMATCH")
    try:
        with safe_path.open("rb") as handle:
            opened = os.fstat(handle.fileno())
            if _handle_identity_signature(before) != _handle_identity_signature(
                opened
            ) or opened.st_size != expected_bytes or opened.st_nlink != 1:
                _fail(f"UNSTABLE_{label.upper().replace(' ', '_')}")
            payload = handle.read(expected_bytes + 1)
            after_handle = os.fstat(handle.fileno())
        after = safe_path.lstat()
    except OSError as exc:
        raise MM003PostTrainingV2ResultError(
            f"UNSTABLE_{label.upper().replace(' ', '_')}"
        ) from exc
    if (
        _handle_identity_signature(before)
        != _handle_identity_signature(after_handle)
        or _handle_identity_signature(after_handle)
        != _handle_identity_signature(after)
        or _stat_signature(before) != _stat_signature(after)
        or len(payload) != after.st_size
        or _metadata_is_reparse(after)
        or after_handle.st_nlink != 1
        or after.st_nlink != 1
    ):
        _fail(f"UNSTABLE_{label.upper().replace(' ', '_')}")
    _recheck_repository_parent_chain(parent_chain, label)
    _check_payload_receipt(
        payload,
        expected_bytes=expected_bytes,
        expected_sha256=expected_sha256,
        label=label,
    )
    return payload


def _check_payload_receipt(
    payload: bytes, *, expected_bytes: int, expected_sha256: str, label: str
) -> None:
    code = label.upper().replace(" ", "_")
    if len(payload) != expected_bytes:
        _fail(f"{code}_BYTE_MISMATCH")
    if contract.sha256_bytes(payload) != expected_sha256:
        _fail(f"{code}_HASH_MISMATCH")


def _canonical_object(payload: bytes, label: str) -> dict[str, Any]:
    value = _object(payload, f"$.{label.replace(' ', '_')}")
    if contract.artifact_json_bytes(value) != payload:
        _fail(f"NONCANONICAL_{label.upper().replace(' ', '_')}_JSON")
    return value


def _object(payload: bytes, location: str) -> dict[str, Any]:
    value = contract.parse_strict_json_bytes(payload, location=location)
    if not isinstance(value, dict):
        _fail("EXPECTED_OBJECT")
    return value


def _mapping(value: object, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail(f"EXPECTED_OBJECT_AT_{location}")
    return value


def _sequence(value: object, location: str) -> Sequence[Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        _fail(f"EXPECTED_ARRAY_AT_{location}")
    return cast(Sequence[Mapping[str, Any]], value)


def _finite_number(value: object, code: str) -> float:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
    ):
        _fail(code)
    return float(value)


def _positive_finite_number(value: object, code: str) -> float:
    result = _finite_number(value, code)
    if result <= 0:
        _fail(code)
    return result


def _nonnegative_finite_number(value: object, code: str) -> float:
    result = _finite_number(value, code)
    if result < 0:
        _fail(code)
    return result


def _positive_integer(value: object, code: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        _fail(code)


def _stat_signature(value: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _handle_identity_signature(
    value: os.stat_result,
) -> tuple[int, int, int, int, int]:
    # Windows handle fstat and path stat can expose different ctime semantics.
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_size,
        value.st_mtime_ns,
    )


def _metadata_is_reparse(value: os.stat_result) -> bool:
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return stat.S_ISLNK(value.st_mode) or bool(
        getattr(value, "st_file_attributes", 0) & reparse_flag
    )


def _require_canonical_repository_root(root: Path) -> None:
    root_absolute = Path(os.path.abspath(root))
    expected_absolute = Path(os.path.abspath(ROOT))
    if os.path.normcase(str(root_absolute)) != os.path.normcase(
        str(expected_absolute)
    ):
        _fail("REPOSITORY_ROOT_MISMATCH")
    try:
        root_resolved = root_absolute.resolve(strict=True)
        expected_resolved = expected_absolute.resolve(strict=True)
    except OSError as exc:
        raise MM003PostTrainingV2ResultError("REPOSITORY_ROOT_MISMATCH") from exc
    if os.path.normcase(str(root_resolved)) != os.path.normcase(
        str(expected_resolved)
    ):
        _fail("REPOSITORY_ROOT_MISMATCH")


def _safe_directory_signature(path: Path, label: str) -> tuple[int, int, int, int, int, int]:
    label_code = label.upper().replace(" ", "_")
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise MM003PostTrainingV2ResultError(f"UNSAFE_{label_code}_PARENT") from exc
    if not stat.S_ISDIR(metadata.st_mode) or _metadata_is_reparse(metadata):
        _fail(f"UNSAFE_{label_code}_PARENT")
    return _stat_signature(metadata)


def _safe_repository_parent_chain(
    root: Path, path: Path, label: str
) -> tuple[Path, list[tuple[Path, tuple[int, int, int, int, int, int]]]]:
    root_absolute = Path(os.path.abspath(root))
    path_absolute = Path(os.path.abspath(path))
    try:
        relative = path_absolute.relative_to(root_absolute)
    except ValueError:
        _fail(f"{label.upper().replace(' ', '_')}_PATH_ESCAPE")
    if not relative.parts:
        _fail(f"{label.upper().replace(' ', '_')}_PATH_ESCAPE")

    parent_chain: list[tuple[Path, tuple[int, int, int, int, int, int]]] = []
    current = root_absolute
    parent_chain.append((current, _safe_directory_signature(current, label)))
    for part in relative.parts[:-1]:
        current = current / part
        parent_chain.append((current, _safe_directory_signature(current, label)))

    try:
        resolved_root = root_absolute.resolve(strict=True)
        resolved_parent = path_absolute.parent.resolve(strict=True)
    except OSError as exc:
        raise MM003PostTrainingV2ResultError(
            f"UNSAFE_{label.upper().replace(' ', '_')}_PARENT"
        ) from exc
    if resolved_parent != resolved_root and not resolved_parent.is_relative_to(
        resolved_root
    ):
        _fail(f"{label.upper().replace(' ', '_')}_PATH_ESCAPE")
    return path_absolute, parent_chain


def _recheck_repository_parent_chain(
    parent_chain: Sequence[tuple[Path, tuple[int, int, int, int, int, int]]],
    label: str,
    *,
    identity_only: bool = False,
) -> None:
    for path, before in parent_chain:
        after = _safe_directory_signature(path, label)
        if (after[:3] if identity_only else after) != (
            before[:3] if identity_only else before
        ):
            _fail(f"UNSTABLE_{label.upper().replace(' ', '_')}_PARENT")


def _fail(code: str) -> NoReturn:
    raise MM003PostTrainingV2ResultError(code)


def _write_exclusive(root: Path, path: Path, payload: bytes) -> None:
    safe_path, parent_chain = _safe_repository_parent_chain(root, path, "result review")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    descriptor = os.open(safe_path, flags, 0o644)
    created_identity: tuple[int, int] | None = None
    try:
        opened_before = os.fstat(descriptor)
        created_identity = (opened_before.st_dev, opened_before.st_ino)
        if (
            not stat.S_ISREG(opened_before.st_mode)
            or opened_before.st_nlink != 1
            or opened_before.st_size != 0
        ):
            _fail("UNSTABLE_RESULT_REVIEW")
        stream = os.fdopen(descriptor, "wb")
        descriptor = -1
        with stream as handle:
            if handle.write(payload) != len(payload):
                _fail("RESULT_REVIEW_SHORT_WRITE")
            handle.flush()
            os.fsync(handle.fileno())
            opened_after = os.fstat(handle.fileno())
        created = safe_path.lstat()
        if (
            not stat.S_ISREG(created.st_mode)
            or _metadata_is_reparse(created)
            or created.st_nlink != 1
            or created.st_size != len(payload)
            or _handle_identity_signature(opened_after)
            != _handle_identity_signature(created)
        ):
            _fail("UNSTABLE_RESULT_REVIEW")
        _recheck_repository_parent_chain(
            parent_chain, "result review", identity_only=True
        )
        verified = _read_exact(
            root,
            safe_path,
            expected_bytes=len(payload),
            expected_sha256=contract.sha256_bytes(payload),
            label="result review candidate",
        )
        if verified != payload:
            _fail("RESULT_REVIEW_READBACK_MISMATCH")
    except BaseException:
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError:
                pass
        try:
            current = safe_path.lstat()
            if (
                created_identity is not None
                and (current.st_dev, current.st_ino) == created_identity
                and stat.S_ISREG(current.st_mode)
                and not _metadata_is_reparse(current)
                and current.st_nlink == 1
            ):
                safe_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-review", action="store_true")
    args = parser.parse_args(argv)
    if args.write_review:
        review, summary = build_repository_review(ROOT)
        _write_exclusive(ROOT, ROOT / REVIEW_PATH, contract.artifact_json_bytes(review))
    else:
        summary = validate_repository(ROOT)
    print(contract.canonical_json_bytes(summary).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
