"""Recompute and review the frozen MM-005 Document/Chart/PDF model result."""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, NoReturn, cast

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SRC))

from fullcycle_bridge import (  # noqa: E402
    mm005_document_chart_pdf_model_evaluation as contract,
)
from scripts import (  # noqa: E402
    prepare_mm005_document_chart_pdf_model_evaluation as protocol_builder,
)
from scripts import validate_mm003_post_training_v2_result as file_validator  # noqa: E402

PROTOCOL_FREEZE_COMMIT = "3be0083c3197111d57a4a5e5f70feced9f2c96f9"
PREREGISTRATION_RECEIPT: dict[str, int | str] = {
    "path": contract.PREREGISTRATION_PATH,
    "bytes": 58_414,
    "sha256": "sha256:cdb8d1ea09221763d87cd79ba752d9af8264ce49b7cf600eed338a073a04561b",
}
REVIEW_GATE_ID = contract.RESULT_REVIEW_GATE_ID
NEXT_GATE_ID = "MM-005-document-chart-pdf-model-evaluation-repeatability-protocol-v1"
CLASSIFICATION = "fixed_synthetic_suite_joint_exact_19_of_32_with_task_family_skew"

_ARTIFACT_PREFIX = "baseline/mm005-document-chart-pdf-model-eval-v1-"
ARTIFACTS: dict[str, dict[str, int | str]] = {
    "attempt_owner": {
        "path": f"{_ARTIFACT_PREFIX}attempt-owner.json",
        "bytes": 656,
        "sha256": "sha256:ca9e420fbce5582cab5944e0c290e569f97cad85ad3a5cf9e3c53aa13989d00b",
    },
    "evaluation_candidate": {
        "path": f"{_ARTIFACT_PREFIX}evaluation-candidate.json",
        "bytes": 32_190,
        "sha256": "sha256:e26f6a9ca03e826f627ae90aca5b2fdcf5bbed770d9752aa9ba74982ed7d12ea",
    },
    "predictions": {
        "path": f"{_ARTIFACT_PREFIX}predictions.json",
        "bytes": 18_543,
        "sha256": "sha256:f9a545175688451fc5025eb1e90a1e1354a59c536887a54fe62deb80a019fff7",
    },
    "evidence": {
        "path": f"{_ARTIFACT_PREFIX}evidence.json",
        "bytes": 7_495,
        "sha256": "sha256:5e330dde1debe7a207638d164aade8ab2c63fbcd8149b3178d64a16afd0fc78e",
    },
}
REVIEW_PATH = f"{_ARTIFACT_PREFIX}result-review.json"
REVIEW_BYTES = 15_235
REVIEW_SHA256 = (
    "sha256:7cc4990f900787123f078d2387855e4708b5eadb8d6705bb6364d8cab2f935a7"
)


class MM005DocumentChartPdfResultError(ValueError):
    """Raised when frozen execution evidence or its review fails closed."""


def validate_repository(root: Path = ROOT) -> dict[str, Any]:
    expected_review, summary = build_repository_review(root)
    try:
        review_payload = file_validator._read_exact(
            root,
            root / REVIEW_PATH,
            expected_bytes=REVIEW_BYTES,
            expected_sha256=REVIEW_SHA256,
            label="MM-005 Document/Chart/PDF result review",
        )
    except file_validator.MM003PostTrainingV2ResultError as exc:
        raise MM005DocumentChartPdfResultError(str(exc)) from exc
    review = _canonical_object(review_payload, "result_review")
    if review != expected_review:
        _fail("RESULT_REVIEW_RECOMPUTATION_MISMATCH")
    return summary


def build_repository_review(root: Path = ROOT) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        file_validator._require_canonical_repository_root(root)
        inputs = protocol_builder.protocol_inputs()
        freeze_inputs = {**inputs, "output_absent": True}
        preregistration_payload = file_validator._read_exact(
            root,
            root / str(PREREGISTRATION_RECEIPT["path"]),
            expected_bytes=int(PREREGISTRATION_RECEIPT["bytes"]),
            expected_sha256=str(PREREGISTRATION_RECEIPT["sha256"]),
            label="MM-005 Document/Chart/PDF preregistration",
        )
        payloads = {
            name: file_validator._read_exact(
                root,
                root / str(receipt["path"]),
                expected_bytes=int(receipt["bytes"]),
                expected_sha256=str(receipt["sha256"]),
                label=f"MM-005 Document/Chart/PDF {name}",
            )
            for name, receipt in ARTIFACTS.items()
        }
    except file_validator.MM003PostTrainingV2ResultError as exc:
        raise MM005DocumentChartPdfResultError(str(exc)) from exc

    try:
        failure_path, failure_parents = file_validator._safe_repository_parent_chain(
            root,
            root / f"{_ARTIFACT_PREFIX}failure.json",
            "MM-005 Document/Chart/PDF success failure artifact",
        )
        if os.path.lexists(failure_path):
            _fail("SUCCESS_FAILURE_ARTIFACT_PRESENT")
        file_validator._recheck_repository_parent_chain(
            failure_parents,
            "MM-005 Document/Chart/PDF success failure artifact",
        )
    except file_validator.MM003PostTrainingV2ResultError as exc:
        raise MM005DocumentChartPdfResultError(str(exc)) from exc
    return validate_execution_payloads(
        preregistration_payload=preregistration_payload,
        payloads=payloads,
        inputs=freeze_inputs,
    )


def validate_execution_payloads(
    *,
    preregistration_payload: bytes,
    payloads: Mapping[str, bytes],
    inputs: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    _check_payload_receipt(
        preregistration_payload,
        PREREGISTRATION_RECEIPT,
        "preregistration",
    )
    if set(payloads) != set(ARTIFACTS):
        _fail("ARTIFACT_SET_MISMATCH")
    for name, receipt in ARTIFACTS.items():
        _check_payload_receipt(payloads[name], receipt, name)

    candidate, evidence = recompute_evidence(
        preregistration_payload=preregistration_payload,
        payloads=payloads,
        inputs=inputs,
    )
    records = _object_sequence(inputs.get("records"), "$.inputs.records")
    review = build_review(evidence=evidence, candidate=candidate, records=records)
    metrics = _mapping(evidence.get("metrics"), "$.evidence.metrics")
    resources = _mapping(evidence.get("resources"), "$.evidence.resources")
    per_family = _mapping(metrics.get("per_task_family"), "$.metrics.per_task_family")
    return review, {
        "formal_gate_passed": True,
        "classification": CLASSIFICATION,
        "record_count": metrics["record_count"],
        "joint_exact_accuracy": _metric_value(metrics, "joint_exact_accuracy"),
        "compiler_validity": _metric_value(metrics, "compiler_validity"),
        "compiler_invalid_count": metrics["compiler_invalid_count"],
        "answer_only_wrong_count": 9,
        "incorrect_case_count": 13,
        "chart_joint_exact_accuracy": _metric_value(
            _mapping(
                per_family.get("chart_value_evidence_grounding"),
                "$.metrics.per_task_family.chart_value_evidence_grounding",
            ),
            "joint_exact_accuracy",
        ),
        "document_text_joint_exact_accuracy": _metric_value(
            _mapping(
                per_family.get("document_text_evidence_grounding"),
                "$.metrics.per_task_family.document_text_evidence_grounding",
            ),
            "joint_exact_accuracy",
        ),
        "page_region_joint_exact_accuracy": _metric_value(
            _mapping(
                per_family.get("page_region_selection"),
                "$.metrics.per_task_family.page_region_selection",
            ),
            "joint_exact_accuracy",
        ),
        "table_joint_exact_accuracy": _metric_value(
            _mapping(
                per_family.get("table_cell_evidence_grounding"),
                "$.metrics.per_task_family.table_cell_evidence_grounding",
            ),
            "joint_exact_accuracy",
        ),
        "evaluation_executed": True,
        "model_evaluated": True,
        "quality_improved": False,
        "repeatability_established": False,
        "elapsed_seconds": resources["elapsed_seconds"],
        "peak_gpu_allocated_bytes": resources["peak_gpu_allocated_bytes"],
        "peak_gpu_reserved_bytes": resources["peak_gpu_reserved_bytes"],
        "evidence_sha256": ARTIFACTS["evidence"]["sha256"],
        "review_bytes": REVIEW_BYTES,
        "review_sha256": REVIEW_SHA256,
        "next_gate": NEXT_GATE_ID,
        "runtime_eligible": False,
    }


def recompute_evidence(
    *,
    preregistration_payload: bytes,
    payloads: Mapping[str, bytes],
    inputs: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    preregistration = _canonical_object(preregistration_payload, "preregistration")
    owner = _canonical_object(payloads["attempt_owner"], "attempt_owner")
    candidate = _canonical_object(
        payloads["evaluation_candidate"], "evaluation_candidate"
    )
    predictions = _canonical_object(payloads["predictions"], "predictions")
    evidence = _canonical_object(payloads["evidence"], "evidence")
    records = _object_sequence(inputs.get("records"), "$.inputs.records")
    image_payloads = _bytes_mapping(
        inputs.get("image_payloads"), "$.inputs.image_payloads"
    )
    try:
        contract.validate_preregistration(preregistration, **dict(inputs))
        expected = contract.validate_evidence(
            evidence,
            protocol_freeze_commit=PROTOCOL_FREEZE_COMMIT,
            preregistration_payload=preregistration_payload,
            attempt_owner_payload=payloads["attempt_owner"],
            evaluation_candidate_payload=payloads["evaluation_candidate"],
            predictions_payload=payloads["predictions"],
            records=records,
            image_payloads=image_payloads,
        )
    except contract.MM005ModelEvaluationError as exc:
        raise MM005DocumentChartPdfResultError(str(exc)) from exc
    if contract.artifact_json_bytes(owner) != payloads["attempt_owner"]:
        _fail("ATTEMPT_OWNER_CANONICAL_MISMATCH")
    if contract.artifact_json_bytes(candidate) != payloads["evaluation_candidate"]:
        _fail("EVALUATION_CANDIDATE_CANONICAL_MISMATCH")
    if contract.artifact_json_bytes(predictions) != payloads["predictions"]:
        _fail("PREDICTIONS_CANONICAL_MISMATCH")
    if contract.artifact_json_bytes(expected) != payloads["evidence"]:
        _fail("EXECUTION_EVIDENCE_RECOMPUTATION_MISMATCH")
    return candidate, evidence


def build_review(
    *,
    evidence: Mapping[str, Any],
    candidate: Mapping[str, Any],
    records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    metrics = _mapping(evidence.get("metrics"), "$.evidence.metrics")
    execution = _mapping(evidence.get("execution"), "$.evidence.execution")
    resources = _mapping(evidence.get("resources"), "$.evidence.resources")
    required_gates = _mapping(
        evidence.get("required_gates"), "$.evidence.required_gates"
    )
    claims = _mapping(evidence.get("claims"), "$.evidence.claims")
    expected_claims = dict(contract.FREEZE_CLAIMS)
    expected_claims.update(
        {
            "attempt_consumed": True,
            "evaluation_executed": True,
            "model_evaluated": True,
            "formal_measurement_complete": True,
        }
    )
    expected_gates = {gate: True for gate in contract.REQUIRED_GATES}
    if (
        evidence.get("gate_id") != contract.EXECUTION_GATE_ID
        or evidence.get("protocol_freeze_commit") != PROTOCOL_FREEZE_COMMIT
        or evidence.get("classification")
        != "outcome_neutral_measurement_complete_within_registered_caps"
        or evidence.get("formal_gate_passed") is not True
        or evidence.get("next_gate") != REVIEW_GATE_ID
        or dict(required_gates) != expected_gates
        or dict(execution) != contract.expected_execution_counters()
        or dict(claims) != expected_claims
    ):
        _fail("FORMAL_RESULT_BOUNDARY_MISMATCH")

    _require_metric(metrics, "compiler_validity", correct=28, total=32)
    _require_metric(metrics, "answer_exact_accuracy", correct=19, total=32)
    _require_metric(metrics, "evidence_exact_accuracy", correct=28, total=32)
    _require_metric(metrics, "page_exact_accuracy", correct=28, total=32)
    _require_metric(metrics, "joint_exact_accuracy", correct=19, total=32)
    if metrics.get("record_count") != 32 or metrics.get("compiler_invalid_count") != 4:
        _fail("RESULT_METRIC_BOUNDARY_MISMATCH")
    _validate_group_metrics(metrics)

    cases = _object_sequence(candidate.get("cases"), "$.candidate.cases")
    if len(records) != 32 or len(cases) != 32:
        _fail("RESULT_CASE_COUNT_MISMATCH")
    record_by_id = {str(record["record_id"]): record for record in records}
    if len(record_by_id) != 32:
        _fail("RESULT_RECORD_ID_MISMATCH")
    rows: list[dict[str, Any]] = []
    failure_counts: Counter[str] = Counter()
    for case in cases:
        record_id = str(case["record_id"])
        record = record_by_id.get(record_id)
        if record is None:
            _fail("RESULT_CASE_RECORD_MISMATCH")
        verdict = _mapping(case.get("verdict"), "$.case.verdict")
        compiled = _mapping(case.get("compiled_output"), "$.case.compiled_output")
        failure_kind = _failure_kind(verdict)
        failure_counts[failure_kind] += 1
        rows.append(
            {
                "record_id": record_id,
                "split": record["split"],
                "task_family_id": record["task_family_id"],
                "source_kind": record["source_kind"],
                "failure_kind": failure_kind,
                "compiler_error_code": compiled["error_code"],
                "valid_output": verdict["valid_output"],
                "answer_exact": verdict["answer_exact"],
                "evidence_exact": verdict["evidence_exact"],
                "page_exact": verdict["page_exact"],
                "joint_correct": verdict["joint_correct"],
            }
        )
    if failure_counts != Counter(
        {"correct": 19, "answer_only_wrong": 9, "compiler_invalid": 4}
    ):
        _fail("BAD_CASE_TAXONOMY_MISMATCH")

    incorrect = [row for row in rows if row["joint_correct"] is False]
    compiler_invalid_ids = [
        row["record_id"] for row in rows if row["failure_kind"] == "compiler_invalid"
    ]
    answer_only_wrong_ids = [
        row["record_id"] for row in rows if row["failure_kind"] == "answer_only_wrong"
    ]
    task_family_incorrect = Counter(str(row["task_family_id"]) for row in incorrect)
    if task_family_incorrect != Counter(
        {
            "document_text_evidence_grounding": 8,
            "page_region_selection": 5,
        }
    ):
        _fail("TASK_FAMILY_BAD_CASE_MISMATCH")

    latencies = [float(case["latency_seconds"]) for case in cases]
    generated_tokens = [int(case["generated_tokens"]) for case in cases]
    for name, cap in contract.RESOURCE_CAPS.items():
        if float(resources[name]) > float(cap):
            _fail("RESOURCE_CAP_EXCEEDED")

    return {
        "mm005_document_chart_pdf_model_evaluation_result_review_version": 1,
        "gate_id": REVIEW_GATE_ID,
        "reviewed_execution_gate_id": contract.EXECUTION_GATE_ID,
        "classification": CLASSIFICATION,
        "protocol": {
            "freeze_commit": PROTOCOL_FREEZE_COMMIT,
            "preregistration": copy.deepcopy(PREREGISTRATION_RECEIPT),
        },
        "frozen_artifacts": {
            name: copy.deepcopy(receipt) for name, receipt in ARTIFACTS.items()
        },
        "review_process": {
            "model_imported": False,
            "model_reloaded": False,
            "cuda_used": False,
            "network_used": False,
            "verifier_recomputed": True,
            "scorer_recomputed": True,
            "candidate_and_predictions_revalidated": True,
            "evidence_rebuilt_from_frozen_inputs": True,
            "historical_resources_reused_from_execution_evidence": True,
            "resources_independently_remeasured": False,
        },
        "formal_measurement": {
            "required_gates": list(contract.REQUIRED_GATES),
            "passed_gates": list(contract.REQUIRED_GATES),
            "formal_gate_passed": True,
            "accuracy_threshold_registered": False,
            "formal_gate_means_measurement_complete_not_quality_accepted": True,
        },
        "observed_behavior": {
            "suite_id": metrics["suite_id"],
            "record_count": 32,
            "metrics": copy.deepcopy(dict(metrics)),
            "output_distribution": {
                "compiler_valid": failure_counts["correct"]
                + failure_counts["answer_only_wrong"],
                "compiler_invalid": failure_counts["compiler_invalid"],
                "joint_correct": failure_counts["correct"],
                "joint_incorrect": len(incorrect),
            },
            "incorrect_case_count": len(incorrect),
            "bad_case_taxonomy": {
                "compiler_invalid_record_ids": compiler_invalid_ids,
                "answer_only_wrong_record_ids": answer_only_wrong_ids,
                "other_wrong_record_ids": [],
                "incorrect_by_task_family": dict(sorted(task_family_incorrect.items())),
            },
            "incorrect_cases": incorrect,
        },
        "execution": copy.deepcopy(dict(execution)),
        "case_diagnostics": {
            "latency_seconds": _distribution(latencies),
            "generated_tokens": _distribution(generated_tokens),
        },
        "resources": {
            "observed": copy.deepcopy(dict(resources)),
            "registered_caps": copy.deepcopy(dict(contract.RESOURCE_CAPS)),
            "within_caps": True,
        },
        "claims": {
            "attempt_consumed": True,
            "evaluation_executed": True,
            "model_evaluated": True,
            "formal_measurement_complete": True,
            "fixed_suite_joint_exact_19_of_32_observed": True,
            "task_family_skew_observed": True,
            "chart_and_table_joint_exact_16_of_16_observed": True,
            "document_text_joint_exact_0_of_8_observed": True,
            "quality_improved": False,
            "generalized_quality_established": False,
            "safety_established": False,
            "repeatability_established": False,
            "training_repeatability_established": False,
            "cross_machine_reproducibility_established": False,
            "training_executed": False,
            "adapter_modified": False,
            "real_content_behavior_established": False,
            "serving_eligible": False,
            "promotion_eligible": False,
            "runtime_eligible": False,
        },
        "limitations": {
            "single_fixed_synthetic_suite": True,
            "no_pre_registered_quality_threshold": True,
            "no_same_environment_baseline_comparison": True,
            "joint_exact_is_19_of_32": True,
            "compiler_invalid_is_4_of_32": True,
            "document_text_joint_exact_is_0_of_8": True,
            "page_region_joint_exact_is_3_of_8": True,
            "chart_and_table_joint_exact_is_16_of_16": True,
            "same_machine_repeatability_tested": False,
            "cross_machine_reproducibility_tested": False,
            "resource_repeatability_tested": False,
            "real_content_tested": False,
            "runtime_integration_tested": False,
        },
        "next_gate": NEXT_GATE_ID,
        "next_action": (
            "freeze one outcome-neutral same-machine fixed-suite repeatability "
            "protocol before any second model import or call"
        ),
        "runtime_eligible": False,
    }


def _validate_group_metrics(metrics: Mapping[str, Any]) -> None:
    expected = {
        "per_split": {
            "train": (14, 24, 21),
            "validation": (5, 8, 7),
        },
        "per_task_family": {
            "chart_value_evidence_grounding": (8, 8, 8),
            "document_text_evidence_grounding": (0, 8, 8),
            "page_region_selection": (3, 8, 4),
            "table_cell_evidence_grounding": (8, 8, 8),
        },
        "per_source_kind": {
            "synthetic_bar_chart": (5, 6, 5),
            "synthetic_single_page_pdf": (9, 14, 13),
            "synthetic_table_document": (4, 6, 4),
            "synthetic_text_document": (1, 6, 6),
        },
    }
    for group_name, groups in expected.items():
        observed_groups = _mapping(metrics.get(group_name), f"$.metrics.{group_name}")
        if set(observed_groups) != set(groups):
            _fail(f"{group_name.upper()}_SET_MISMATCH")
        for name, (joint_correct, total, compiler_valid) in groups.items():
            observed = _mapping(
                observed_groups.get(name), f"$.metrics.{group_name}.{name}"
            )
            _require_metric(
                observed,
                "joint_exact_accuracy",
                correct=joint_correct,
                total=total,
            )
            _require_metric(
                observed,
                "compiler_validity",
                correct=compiler_valid,
                total=total,
            )


def _failure_kind(verdict: Mapping[str, Any]) -> str:
    if verdict.get("joint_correct") is True:
        return "correct"
    if verdict.get("valid_output") is not True:
        return "compiler_invalid"
    if (
        verdict.get("answer_exact") is False
        and verdict.get("evidence_exact") is True
        and verdict.get("page_exact") is True
    ):
        return "answer_only_wrong"
    return "other_wrong"


def _distribution(values: Sequence[float | int]) -> dict[str, float | int]:
    return {
        "sum": sum(values),
        "mean": sum(values) / len(values),
        "minimum": min(values),
        "maximum": max(values),
    }


def _require_metric(
    metrics: Mapping[str, Any], name: str, *, correct: int, total: int
) -> None:
    metric = _mapping(metrics.get(name), f"$.metrics.{name}")
    if (
        metric.get("correct") != correct
        or metric.get("total") != total
        or metric.get("value") != correct / total
    ):
        _fail(f"{name.upper()}_MISMATCH")


def _metric_value(metrics: Mapping[str, Any], name: str) -> Any:
    return _mapping(metrics.get(name), f"$.metrics.{name}")["value"]


def _check_payload_receipt(
    payload: bytes, receipt: Mapping[str, int | str], label: str
) -> None:
    if len(payload) != int(receipt["bytes"]) or contract.sha256_bytes(payload) != str(
        receipt["sha256"]
    ):
        _fail(f"{label.upper()}_RECEIPT_MISMATCH")


def _canonical_object(payload: bytes, label: str) -> dict[str, Any]:
    try:
        raw = contract.parse_strict_json_bytes(payload, location=f"$.{label}")
    except contract.MM005ModelEvaluationError as exc:
        raise MM005DocumentChartPdfResultError(str(exc)) from exc
    if contract.artifact_json_bytes(raw) != payload:
        _fail(f"{label.upper()}_NONCANONICAL_JSON")
    return cast(dict[str, Any], raw)


def _mapping(value: object, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail(f"EXPECTED_OBJECT_AT_{location}")
    return cast(Mapping[str, Any], value)


def _bytes_mapping(value: object, location: str) -> Mapping[str, bytes]:
    mapping = _mapping(value, location)
    if not all(
        isinstance(key, str) and isinstance(item, bytes)
        for key, item in mapping.items()
    ):
        _fail(f"EXPECTED_BYTE_MAPPING_AT_{location}")
    return cast(Mapping[str, bytes], mapping)


def _object_sequence(value: object, location: str) -> Sequence[Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        _fail(f"EXPECTED_ARRAY_AT_{location}")
    items = cast(Sequence[object], value)
    if not all(isinstance(item, Mapping) for item in items):
        _fail(f"EXPECTED_OBJECT_ITEMS_AT_{location}")
    return cast(Sequence[Mapping[str, Any]], items)


def _fail(code: str) -> NoReturn:
    raise MM005DocumentChartPdfResultError(code)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write-review",
        action="store_true",
        help="exclusively write the recomputed review artifact",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.write_review:
            review, summary = build_repository_review(ROOT)
            payload = contract.artifact_json_bytes(review)
            file_validator._write_exclusive(ROOT, ROOT / REVIEW_PATH, payload)
            summary = {
                **summary,
                "review_bytes": len(payload),
                "review_sha256": contract.sha256_bytes(payload),
            }
        else:
            summary = validate_repository(ROOT)
    except (
        MM005DocumentChartPdfResultError,
        file_validator.MM003PostTrainingV2ResultError,
        contract.MM005ModelEvaluationError,
    ) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(summary, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
