"""Recompute and review the frozen MM-004 hard-negative model result."""

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
    mm004_hard_negative_model_evaluation as contract,
)
from scripts import (  # noqa: E402
    run_mm004_hard_negative_model_evaluation as formal_runner,
)
from scripts import validate_mm003_post_training_v2_result as file_validator  # noqa: E402

PROTOCOL_FREEZE_COMMIT = "365935c02e16badec9ba40a3c4d078b66726f96e"
PREREGISTRATION_RECEIPT: dict[str, int | str] = {
    "path": contract.PREREGISTRATION_PATH,
    "bytes": 50_642,
    "sha256": "sha256:bee2093d54d95cc52303c57c598d99a071aff85bef9f56605adeb2b604f8c0d9",
}
REVIEW_GATE_ID = contract.RESULT_REVIEW_GATE_ID
NEXT_GATE_ID = "MM-005-multimodal-environment-adaptation-protocol-v1"
CLASSIFICATION = (
    "fixed_suite_all_hard_negatives_rejected_with_clean_accept_recall_4_of_28"
)

_ARTIFACT_PREFIX = "baseline/mm004-hard-negative-model-eval-v2-"
ARTIFACTS: dict[str, dict[str, int | str]] = {
    "attempt_owner": {
        "path": f"{_ARTIFACT_PREFIX}attempt-owner.json",
        "bytes": 644,
        "sha256": "sha256:80d121c5e196e4cd6c7af68f08ba9a940af559909fe41b4a0b0e858068f59098",
    },
    "evaluation_candidate": {
        "path": f"{_ARTIFACT_PREFIX}evaluation-candidate.json",
        "bytes": 34_700,
        "sha256": "sha256:246b5708362df0c51ea5362b0817b2a3c2984fbfc0f0e6148966b6612b8b20fe",
    },
    "predictions": {
        "path": f"{_ARTIFACT_PREFIX}predictions.json",
        "bytes": 7_761,
        "sha256": "sha256:cbf07b21abe620098f5f442778e0c3ef29a948e2c5ffd5c70a1baa9adda98618",
    },
    "evidence": {
        "path": f"{_ARTIFACT_PREFIX}evidence.json",
        "bytes": 6_644,
        "sha256": "sha256:87c45c9a174b9c6d0419f1d0ba9c619597848b13fe4447a19988e7a6ff56292c",
    },
}
REVIEW_PATH = f"{_ARTIFACT_PREFIX}result-review.json"
REVIEW_BYTES = 18_220
REVIEW_SHA256 = (
    "sha256:711c1b52619d856015b832cd54a3bbfcaa419f360b95bf448d62de8230bdb720"
)


class MM004HardNegativeResultError(ValueError):
    """Raised when frozen execution evidence or its review fails closed."""


def validate_repository(root: Path = ROOT) -> dict[str, Any]:
    expected_review, summary = build_repository_review(root)
    try:
        review_payload = file_validator._read_exact(
            root,
            root / REVIEW_PATH,
            expected_bytes=REVIEW_BYTES,
            expected_sha256=REVIEW_SHA256,
            label="MM-004 hard-negative result review",
        )
    except file_validator.MM003PostTrainingV2ResultError as exc:
        raise MM004HardNegativeResultError(str(exc)) from exc
    review = _canonical_object(review_payload, "result_review")
    if review != expected_review:
        _fail("RESULT_REVIEW_RECOMPUTATION_MISMATCH")
    return summary


def build_repository_review(root: Path = ROOT) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        file_validator._require_canonical_repository_root(root)
        context = formal_runner.load_authenticated_context()
        source_receipts = formal_runner.source_receipts()
        preregistration_payload = file_validator._read_exact(
            root,
            root / str(PREREGISTRATION_RECEIPT["path"]),
            expected_bytes=int(PREREGISTRATION_RECEIPT["bytes"]),
            expected_sha256=str(PREREGISTRATION_RECEIPT["sha256"]),
            label="MM-004 hard-negative preregistration",
        )
        payloads = {
            name: file_validator._read_exact(
                root,
                root / str(receipt["path"]),
                expected_bytes=int(receipt["bytes"]),
                expected_sha256=str(receipt["sha256"]),
                label=f"MM-004 hard-negative {name}",
            )
            for name, receipt in ARTIFACTS.items()
        }
    except file_validator.MM003PostTrainingV2ResultError as exc:
        raise MM004HardNegativeResultError(str(exc)) from exc

    try:
        failure_path, failure_parents = file_validator._safe_repository_parent_chain(
            root,
            root / f"{_ARTIFACT_PREFIX}failure.json",
            "MM-004 hard-negative success failure artifact",
        )
        if os.path.lexists(failure_path):
            _fail("SUCCESS_FAILURE_ARTIFACT_PRESENT")
        file_validator._recheck_repository_parent_chain(
            failure_parents,
            "MM-004 hard-negative success failure artifact",
        )
    except file_validator.MM003PostTrainingV2ResultError as exc:
        raise MM004HardNegativeResultError(str(exc)) from exc
    return validate_execution_payloads(
        preregistration_payload=preregistration_payload,
        payloads=payloads,
        context=context,
        source_receipts=source_receipts,
    )


def validate_execution_payloads(
    *,
    preregistration_payload: bytes,
    payloads: Mapping[str, bytes],
    context: Mapping[str, Any],
    source_receipts: Mapping[str, Mapping[str, Any]],
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
        context=context,
        source_receipts=source_receipts,
    )
    records = _object_sequence(context.get("records"), "$.context.records")
    review = build_review(evidence=evidence, candidate=candidate, records=records)
    metrics = _mapping(evidence.get("metrics"), "$.evidence.metrics")
    resources = _mapping(evidence.get("resources"), "$.evidence.resources")
    return review, {
        "formal_gate_passed": True,
        "classification": CLASSIFICATION,
        "record_count": metrics["record_count"],
        "overall_accuracy": _mapping(
            metrics["overall_accuracy"], "$.metrics.overall_accuracy"
        )["value"],
        "clean_accept_recall": _mapping(
            metrics["clean_accept_recall"], "$.metrics.clean_accept_recall"
        )["value"],
        "hard_negative_rejection_recall": _mapping(
            metrics["hard_negative_rejection_recall"],
            "$.metrics.hard_negative_rejection_recall",
        )["value"],
        "pair_exact_accuracy": _mapping(
            metrics["pair_exact_accuracy"], "$.metrics.pair_exact_accuracy"
        )["value"],
        "compiler_validity": _mapping(
            metrics["compiler_validity"], "$.metrics.compiler_validity"
        )["value"],
        "clean_false_rejects": metrics["clean_false_rejects"],
        "clean_invalid_outputs": 4,
        "hard_negative_false_accepts": metrics["hard_negative_false_accepts"],
        "compiler_fallback_count": 4,
        "evaluation_executed": True,
        "model_evaluated": True,
        "training_executed": False,
        "quality_improved": False,
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
    context: Mapping[str, Any],
    source_receipts: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    preregistration = _canonical_object(preregistration_payload, "preregistration")
    owner = _canonical_object(payloads["attempt_owner"], "attempt_owner")
    candidate = _canonical_object(
        payloads["evaluation_candidate"], "evaluation_candidate"
    )
    predictions = _canonical_object(payloads["predictions"], "predictions")
    evidence = _canonical_object(payloads["evidence"], "evidence")
    records = _object_sequence(context.get("records"), "$.context.records")
    try:
        contract.validate_preregistration(
            preregistration,
            generation_evidence=_mapping(
                context.get("generation_evidence"), "$.context.generation_evidence"
            ),
            candidate_repeatability_protocol=_mapping(
                context.get("candidate_repeatability_protocol"),
                "$.context.candidate_repeatability_protocol",
            ),
            candidate_result_review=_mapping(
                context.get("candidate_result_review"),
                "$.context.candidate_result_review",
            ),
            records=records,
            source_receipts=source_receipts,
        )
        expected = contract.validate_evidence(
            evidence,
            protocol_freeze_commit=PROTOCOL_FREEZE_COMMIT,
            preregistration_payload=preregistration_payload,
            attempt_owner_payload=payloads["attempt_owner"],
            evaluation_candidate_payload=payloads["evaluation_candidate"],
            predictions_payload=payloads["predictions"],
            records=records,
        )
    except contract.MM004ModelEvaluationError as exc:
        raise MM004HardNegativeResultError(str(exc)) from exc
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
    expected_claims = {key: False for key in contract.FREEZE_CLAIM_KEYS}
    expected_claims.update(
        {
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
        != "mm004_hard_negative_model_measurement_complete_within_caps"
        or evidence.get("formal_gate_passed") is not True
        or evidence.get("next_gate") != REVIEW_GATE_ID
        or dict(required_gates) != expected_gates
        or dict(execution) != contract.expected_execution_counters()
        or dict(claims) != expected_claims
    ):
        _fail("FORMAL_RESULT_BOUNDARY_MISMATCH")

    _require_metric(metrics, "overall_accuracy", correct=32, total=56)
    _require_metric(metrics, "clean_accept_recall", correct=4, total=28)
    _require_metric(
        metrics,
        "hard_negative_rejection_recall",
        correct=28,
        total=28,
    )
    _require_metric(metrics, "pair_exact_accuracy", correct=4, total=28)
    _require_metric(metrics, "compiler_validity", correct=52, total=56)
    if (
        metrics.get("record_count") != 56
        or metrics.get("hard_negative_false_accepts") != 0
        or metrics.get("clean_false_rejects") != 20
        or metrics.get("balanced_variant_accuracy") != 4 / 7
    ):
        _fail("RESULT_METRIC_BOUNDARY_MISMATCH")

    cases = _object_sequence(candidate.get("cases"), "$.candidate.cases")
    if len(records) != 56 or len(cases) != 56:
        _fail("RESULT_CASE_COUNT_MISMATCH")
    rows: list[dict[str, Any]] = []
    for record, case in zip(records, cases, strict=True):
        compiled = _mapping(
            case.get("compiled_prediction"), "$.case.compiled_prediction"
        )
        verifier = _mapping(record.get("verifier"), "$.record.verifier")
        expected = str(verifier["verdict"])
        predicted = str(compiled["verdict"])
        rows.append(
            {
                "record_id": record["record_id"],
                "pair_id": record["pair_id"],
                "split": record["split"],
                "category_id": record["category_id"],
                "variant": record["variant"],
                "expected": expected,
                "predicted": predicted,
                "compiler_fallback": compiled["compiler_fallback"],
                "correct": predicted == expected,
            }
        )

    clean_false_rejects = [
        row["record_id"]
        for row in rows
        if row["variant"] == "clean" and row["predicted"] == "reject"
    ]
    clean_invalid = [
        row["record_id"]
        for row in rows
        if row["variant"] == "clean" and row["compiler_fallback"] is True
    ]
    negative_false_accepts = [
        row["record_id"]
        for row in rows
        if row["variant"] == "hard_negative" and row["predicted"] == "accept"
    ]
    incorrect = [row for row in rows if row["correct"] is False]
    if (
        len(clean_false_rejects) != 20
        or len(clean_invalid) != 4
        or negative_false_accepts
        or len(incorrect) != 24
    ):
        _fail("BAD_CASE_TAXONOMY_MISMATCH")

    latencies = [float(case["latency_seconds"]) for case in cases]
    generated_tokens = [int(case["generated_tokens"]) for case in cases]
    verdict_counts = Counter(str(row["predicted"]) for row in rows)
    resource_caps = contract.RESOURCE_CAPS
    for name, cap in resource_caps.items():
        if float(resources[name]) > float(cap):
            _fail("RESOURCE_CAP_EXCEEDED")

    return {
        "mm004_hard_negative_model_evaluation_result_review_version": 2,
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
            "record_count": 56,
            "pair_count": 28,
            "metrics": copy.deepcopy(dict(metrics)),
            "output_distribution": {
                "accept": verdict_counts["accept"],
                "reject": verdict_counts["reject"],
                "invalid": verdict_counts["invalid"],
            },
            "incorrect_case_count": len(incorrect),
            "bad_case_taxonomy": {
                "clean_false_reject_record_ids": clean_false_rejects,
                "clean_invalid_output_record_ids": clean_invalid,
                "hard_negative_false_accept_record_ids": negative_false_accepts,
            },
            "incorrect_cases": incorrect,
        },
        "execution": copy.deepcopy(dict(execution)),
        "case_diagnostics": {
            "latency_seconds": {
                "sum": sum(latencies),
                "mean": sum(latencies) / len(latencies),
                "minimum": min(latencies),
                "maximum": max(latencies),
            },
            "generated_tokens": {
                "sum": sum(generated_tokens),
                "mean": sum(generated_tokens) / len(generated_tokens),
                "minimum": min(generated_tokens),
                "maximum": max(generated_tokens),
            },
        },
        "resources": {
            "observed": copy.deepcopy(dict(resources)),
            "registered_caps": copy.deepcopy(dict(resource_caps)),
            "within_caps": True,
        },
        "claims": {
            "attempt_consumed": True,
            "evaluation_executed": True,
            "model_evaluated": True,
            "formal_measurement_complete": True,
            "fixed_suite_all_hard_negatives_rejected": True,
            "fixed_suite_clean_false_refusal_observed": True,
            "quality_improved": False,
            "generalized_quality_established": False,
            "safety_established": False,
            "training_executed": False,
            "adapter_modified": False,
            "serving_eligible": False,
            "promotion_eligible": False,
            "runtime_eligible": False,
        },
        "limitations": {
            "single_fixed_synthetic_suite": True,
            "no_pre_registered_quality_threshold": True,
            "no_baseline_comparison_for_quality_improvement": True,
            "clean_accept_recall_is_4_of_28": True,
            "clean_false_rejects_are_20_of_28": True,
            "clean_invalid_outputs_are_4_of_28": True,
            "hard_negative_rejection_is_28_of_28": True,
            "cross_machine_reproducibility_tested": False,
            "resource_repeatability_tested": False,
            "real_content_tested": False,
            "runtime_integration_tested": False,
        },
        "next_gate": NEXT_GATE_ID,
        "next_action": (
            "freeze one bounded MM-005 environment-adaptation protocol before "
            "adding another environment, modality, training run, or Runtime change"
        ),
        "runtime_eligible": False,
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


def _check_payload_receipt(
    payload: bytes, receipt: Mapping[str, int | str], label: str
) -> None:
    if (
        len(payload) != int(receipt["bytes"])
        or contract.sha256_bytes(payload) != str(receipt["sha256"])
    ):
        _fail(f"{label.upper()}_RECEIPT_MISMATCH")


def _canonical_object(payload: bytes, label: str) -> dict[str, Any]:
    try:
        raw = contract.parse_strict_json_bytes(payload, location=f"$.{label}")
    except contract.MM004ModelEvaluationError as exc:
        raise MM004HardNegativeResultError(str(exc)) from exc
    if not isinstance(raw, dict):
        _fail(f"{label.upper()}_NOT_OBJECT")
    value = cast(dict[str, Any], raw)
    if contract.artifact_json_bytes(value) != payload:
        _fail(f"{label.upper()}_NONCANONICAL_JSON")
    return value


def _mapping(value: object, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail(f"EXPECTED_OBJECT_AT_{location}")
    return cast(Mapping[str, Any], value)


def _object_sequence(value: object, location: str) -> Sequence[Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        _fail(f"EXPECTED_ARRAY_AT_{location}")
    items = cast(Sequence[object], value)
    if not all(isinstance(item, Mapping) for item in items):
        _fail(f"EXPECTED_OBJECT_ITEMS_AT_{location}")
    return cast(Sequence[Mapping[str, Any]], items)


def _fail(code: str) -> NoReturn:
    raise MM004HardNegativeResultError(code)


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
        MM004HardNegativeResultError,
        file_validator.MM003PostTrainingV2ResultError,
        contract.MM004ModelEvaluationError,
    ) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(summary, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
