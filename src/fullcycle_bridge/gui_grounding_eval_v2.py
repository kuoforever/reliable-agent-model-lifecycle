"""MM-003 recovery scorer with a total prediction-dependent diagnostic."""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path
from typing import Any

from . import gui_grounding_eval as v1

REPORT_VERSION = 2


def score_predictions(suite_value: object, predictions_value: object) -> dict[str, Any]:
    """Score with v1 semantics and an explicit zero-denominator diagnostic."""

    suite = v1._mapping(suite_value, "$")
    suite_summary = v1.validate_suite(suite)
    predictions = v1._mapping(predictions_value, "$.predictions")
    v1._exact_fields(
        predictions,
        {"gui_grounding_prediction_version", "suite_id", "producer", "records"},
        "$.predictions",
    )
    v1._exact_integer(
        predictions.get("gui_grounding_prediction_version"),
        v1.GUI_GROUNDING_EVAL_VERSION,
        "$.predictions.gui_grounding_prediction_version",
        "UNSUPPORTED_VERSION",
    )
    if v1._identifier(predictions.get("suite_id"), "$.predictions.suite_id") != (
        suite_summary.suite_id
    ):
        v1._fail("SUITE_BINDING_MISMATCH", "$.predictions.suite_id")
    producer_kind = v1._validate_producer(predictions.get("producer"))
    records = v1._sequence(predictions.get("records"), "$.predictions.records")
    cases = v1._sequence(suite.get("cases"), "$.cases")
    if len(records) != len(cases):
        v1._fail("PREDICTION_COUNT_MISMATCH", "$.predictions.records")

    grounding_correct = 0
    grounding_total = 0
    iou_sum = Fraction(0, 1)
    iou_total = 0
    action_correct = 0
    tool_correct = 0
    tool_total = 0
    argument_correct = 0
    argument_total = 0
    stale_correct = 0
    stale_total = 0
    disagreement_rejection_correct = 0
    disagreement_rejection_total = 0
    prediction_disagreements = 0
    prediction_disagreement_total = 0

    threshold = Fraction(
        str(v1._mapping(suite["thresholds"], "$.thresholds")["bbox_iou"])
    )
    for index, (case_value, record_value) in enumerate(
        zip(cases, records, strict=True)
    ):
        case = v1._mapping(case_value, f"$.cases[{index}]")
        record = v1._validate_prediction(record_value, case, index)
        gold = v1._mapping(case["gold"], f"$.cases[{index}].gold")
        catalog = v1._sequence(
            gold["target_catalog"], f"$.cases[{index}].gold.target_catalog"
        )
        ref_target = v1._resolve_ref(record.get("ref"), catalog)
        bbox_target = v1._resolve_bbox(record.get("bbox"), catalog, threshold)
        expected_target = gold.get("target_id")
        capability = case["capability"]
        grounding_match = False
        if gold["disposition"] == "act":
            grounding_total += 1
            if capability == "ref_grounding":
                grounding_match = ref_target == expected_target
            elif capability == "bbox_grounding":
                grounding_match = bbox_target == expected_target
            else:
                grounding_match = (
                    ref_target == expected_target and bbox_target == expected_target
                )
            grounding_correct += int(grounding_match)
            tool_total += 1
            argument_total += 1
            tool_correct += int(
                record["disposition"] == "act" and record["tool"] == gold["tool"]
            )
            argument_correct += int(
                record["disposition"] == "act"
                and record["arguments"] == gold["arguments"]
            )
            if gold["bbox"] is not None:
                iou_total += 1
                iou_sum += v1._bbox_iou(record.get("bbox"), gold["bbox"])
            action_correct += int(record["disposition"] == "act" and grounding_match)
        else:
            action_correct += int(
                record["disposition"] == gold["disposition"]
                and record["reason"] == gold["reason"]
            )

        perturbation = case["perturbation"]
        if perturbation == "stale_ref":
            stale_total += 1
            stale_correct += int(
                record["disposition"] == "reject" and record["reason"] == "stale_ref"
            )
        if perturbation == "coordinate_ref_disagreement":
            disagreement_rejection_total += 1
            disagreement_rejection_correct += int(
                record["disposition"] == "reject"
                and record["reason"] == "coordinate_ref_disagreement"
            )
        if record.get("ref") is not None and record.get("bbox") is not None:
            prediction_disagreement_total += 1
            prediction_disagreements += int(
                ref_target is None or bbox_target is None or ref_target != bbox_target
            )

    return {
        "report_version": REPORT_VERSION,
        "suite_id": suite_summary.suite_id,
        "suite_sha256": v1.sha256_json(suite),
        "predictions_sha256": v1.sha256_json(predictions),
        "case_count": suite_summary.case_count,
        "producer_kind": producer_kind,
        "metrics": {
            "grounding_accuracy": v1._ratio(grounding_correct, grounding_total),
            "mean_iou": v1._fraction_metric(iou_sum, iou_total),
            "action_accuracy": v1._ratio(action_correct, len(cases)),
            "tool_accuracy": v1._ratio(tool_correct, tool_total),
            "argument_exact_match": v1._ratio(argument_correct, argument_total),
            "stale_ref_rejection": v1._ratio(stale_correct, stale_total),
            "coordinate_ref_disagreement_rejection": v1._ratio(
                disagreement_rejection_correct, disagreement_rejection_total
            ),
            "prediction_coordinate_ref_disagreement_rate": _optional_ratio(
                prediction_disagreements, prediction_disagreement_total
            ),
        },
        "coverage": {
            "observation_modes": list(suite_summary.observation_modes),
            "capabilities": list(suite_summary.capabilities),
            "ocr_conditions": list(suite_summary.ocr_conditions),
            "perturbations": list(suite_summary.perturbations),
        },
        "claims": {
            "synthetic_eval_only": True,
            "synthetic_probe_only": producer_kind == "synthetic_probe",
            "model_predictions_declared": producer_kind == "model",
            "model_evaluated": False,
            "real_content_collected": False,
            "capture_adapter_implemented": False,
            "training_eligible": False,
            "execution_eligible": False,
            "runtime_eligible": False,
        },
    }


def score_files(suite_path: Path, predictions_path: Path) -> dict[str, Any]:
    return score_predictions(
        v1.load_suite_file(suite_path), v1.load_predictions_file(predictions_path)
    )


def _optional_ratio(correct: int, total: int) -> dict[str, int | float | str | None]:
    if total < 0 or correct < 0 or correct > total:
        v1._fail("INVALID_METRIC_ARITHMETIC", "$.report.metrics")
    if total == 0:
        return {
            "correct": 0,
            "total": 0,
            "value": None,
            "status": "not_applicable",
        }
    return {"correct": correct, "total": total, "value": correct / total}


__all__ = ["REPORT_VERSION", "score_files", "score_predictions"]
