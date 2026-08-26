"""Rebuild and review the frozen MM-005 evaluation-repeatability result."""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, NoReturn, cast

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SRC))

from fullcycle_bridge import (  # noqa: E402
    mm005_document_chart_pdf_model_evaluation_repeatability as contract,
)
from scripts import (  # noqa: E402
    prepare_mm005_document_chart_pdf_model_evaluation_repeatability as protocol_builder,
)
from scripts import validate_mm003_post_training_v2_result as file_validator  # noqa: E402

PROTOCOL_FREEZE_COMMIT = "874f6c1a201a07d6680a3fa12217c1344b14c141"
PREREGISTRATION_RECEIPT: dict[str, int | str] = {
    "path": contract.PREREGISTRATION_PATH,
    "bytes": 47_974,
    "sha256": "sha256:4c5186cbfa542125d4f2b96dae14e31955effa330c42951f993413d276962ed7",
}
REVIEW_GATE_ID = contract.RESULT_REVIEW_GATE_ID
NEXT_GATE_ID = "MM-005-browser-research-environment-adaptation-protocol-v1"
CLASSIFICATION = (
    "bounded_same_machine_registered_environment_fixed_32_case_"
    "evaluation_repeatability_established"
)

_ARTIFACT_PREFIX = (
    "baseline/mm005-document-chart-pdf-model-eval-repeatability-v1-"
)
ARTIFACTS: dict[str, dict[str, int | str]] = {
    "attempt_owner": {
        "path": f"{_ARTIFACT_PREFIX}attempt-owner.json",
        "bytes": 783,
        "sha256": "sha256:4ac65e8f492a0988a0dbf7bface864c51d153f3e11b0fd48647d02226a7f4928",
    },
    "evaluation_candidate": {
        "path": f"{_ARTIFACT_PREFIX}evaluation-candidate.json",
        "bytes": 32_390,
        "sha256": "sha256:de0bf6c2400a06f0edd912d024c50cb711c3686082834c10e1f7c25ef44e7e98",
    },
    "predictions": {
        "path": f"{_ARTIFACT_PREFIX}predictions.json",
        "bytes": 18_660,
        "sha256": "sha256:8664ffa2430680412c19733b49fc77920572a0b8960828e35f5365218ecfaa2e",
    },
    "evidence": {
        "path": f"{_ARTIFACT_PREFIX}evidence.json",
        "bytes": 20_952,
        "sha256": "sha256:659ea12140a85c044be1cdd0bf1ab867cbbdff2a097fbd447e07ec3b84e81617",
    },
}
REVIEW_PATH = f"{_ARTIFACT_PREFIX}result-review.json"
REVIEW_BYTES = 18_817
REVIEW_SHA256 = (
    "sha256:c5b5f12dfaffb387ca7e394c8acbd2b92fc00e3a256ed8cab0d4e624b28d0ec8"
)


class MM005EvaluationRepeatabilityResultError(ValueError):
    """Raised when the frozen replay or independent review fails closed."""


def validate_repository(root: Path = ROOT) -> dict[str, Any]:
    expected_review, summary = build_repository_review(root)
    try:
        review_payload = file_validator._read_exact(
            root,
            root / REVIEW_PATH,
            expected_bytes=REVIEW_BYTES,
            expected_sha256=REVIEW_SHA256,
            label="MM-005 evaluation-repeatability result review",
        )
    except file_validator.MM003PostTrainingV2ResultError as exc:
        raise MM005EvaluationRepeatabilityResultError(str(exc)) from exc
    review = _canonical_object(review_payload, "result_review")
    if review != expected_review:
        _fail("RESULT_REVIEW_RECOMPUTATION_MISMATCH")
    return summary


def build_repository_review(root: Path = ROOT) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        file_validator._require_canonical_repository_root(root)
        inputs = {**protocol_builder.protocol_inputs(), "output_absent": True}
        preregistration_payload = file_validator._read_exact(
            root,
            root / str(PREREGISTRATION_RECEIPT["path"]),
            expected_bytes=int(PREREGISTRATION_RECEIPT["bytes"]),
            expected_sha256=str(PREREGISTRATION_RECEIPT["sha256"]),
            label="MM-005 evaluation-repeatability preregistration",
        )
        payloads = {
            name: file_validator._read_exact(
                root,
                root / str(receipt["path"]),
                expected_bytes=int(receipt["bytes"]),
                expected_sha256=str(receipt["sha256"]),
                label=f"MM-005 evaluation-repeatability {name}",
            )
            for name, receipt in ARTIFACTS.items()
        }
    except file_validator.MM003PostTrainingV2ResultError as exc:
        raise MM005EvaluationRepeatabilityResultError(str(exc)) from exc

    try:
        failure_path, failure_parents = file_validator._safe_repository_parent_chain(
            root,
            root / f"{_ARTIFACT_PREFIX}failure.json",
            "MM-005 evaluation-repeatability success failure artifact",
        )
        if os.path.lexists(failure_path):
            _fail("SUCCESS_FAILURE_ARTIFACT_PRESENT")
        file_validator._recheck_repository_parent_chain(
            failure_parents,
            "MM-005 evaluation-repeatability success failure artifact",
        )
    except file_validator.MM003PostTrainingV2ResultError as exc:
        raise MM005EvaluationRepeatabilityResultError(str(exc)) from exc
    return validate_execution_payloads(
        preregistration_payload=preregistration_payload,
        payloads=payloads,
        inputs=inputs,
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

    preregistration, candidate, evidence = recompute_evidence(
        preregistration_payload=preregistration_payload,
        payloads=payloads,
        inputs=inputs,
    )
    review = build_review(
        preregistration=preregistration,
        evidence=evidence,
        candidate=candidate,
    )
    comparison = _mapping(evidence.get("comparison"), "$.evidence.comparison")
    resources = _mapping(evidence.get("resources"), "$.evidence.resources")
    resource_comparison = _mapping(
        comparison.get("resources"), "$.comparison.resources"
    )
    return review, {
        "formal_gate_passed": True,
        "classification": CLASSIFICATION,
        "record_count": contract.EXPECTED_RECORDS,
        "all_registered_layers_exact": True,
        "raw_outputs_exact": contract.EXPECTED_RECORDS,
        "compiled_outputs_exact": contract.EXPECTED_RECORDS,
        "verifier_verdicts_exact": contract.EXPECTED_RECORDS,
        "metrics_exact": True,
        "generated_token_counts_exact": contract.EXPECTED_RECORDS,
        "same_machine_fixed_suite_repeatability_established": True,
        "training_repeatability_established": False,
        "resource_repeatability_established": False,
        "resource_measurements_exact": resource_comparison["exact"],
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
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    preregistration = _canonical_object(preregistration_payload, "preregistration")
    owner = _canonical_object(payloads["attempt_owner"], "attempt_owner")
    candidate = _canonical_object(
        payloads["evaluation_candidate"], "evaluation_candidate"
    )
    predictions = _canonical_object(payloads["predictions"], "predictions")
    evidence = _canonical_object(payloads["evidence"], "evidence")
    try:
        contract.validate_preregistration(preregistration, **dict(inputs))
        baseline_state = contract.validate_baseline_payloads(
            baseline_preregistration_payload=cast(
                bytes, inputs["baseline_preregistration_payload"]
            ),
            baseline_artifact_payloads=_byte_mapping(
                inputs["baseline_artifact_payloads"],
                "$.inputs.baseline_artifact_payloads",
            ),
            baseline_review_payload=cast(bytes, inputs["baseline_review_payload"]),
            baseline_inputs=_mapping(
                inputs["baseline_inputs"], "$.inputs.baseline_inputs"
            ),
        )
        baseline_inputs = _mapping(
            inputs["baseline_inputs"], "$.inputs.baseline_inputs"
        )
        expected = contract.build_evidence(
            protocol_freeze_commit=PROTOCOL_FREEZE_COMMIT,
            preregistration_payload=preregistration_payload,
            preregistration=preregistration,
            attempt_owner_payload=payloads["attempt_owner"],
            evaluation_candidate_payload=payloads["evaluation_candidate"],
            predictions_payload=payloads["predictions"],
            reference_candidate=_mapping(
                baseline_state["candidate"], "$.baseline_state.candidate"
            ),
            reference_evidence=_mapping(
                baseline_state["evidence"], "$.baseline_state.evidence"
            ),
            records=_object_sequence(baseline_inputs["records"], "$.records"),
            image_payloads=_byte_mapping(
                baseline_inputs["image_payloads"], "$.image_payloads"
            ),
            # The runner supplied its live observation here.  That mapping was
            # not persisted separately, so review can rebuild the passed gate
            # only with the frozen registered mapping and records this limit.
            observed_environment=_mapping(
                preregistration["environment"], "$.preregistration.environment"
            ),
            captured_at_utc=str(evidence["captured_at_utc"]),
        )
    except contract.MM005EvaluationRepeatabilityError as exc:
        raise MM005EvaluationRepeatabilityResultError(str(exc)) from exc
    if contract.artifact_json_bytes(owner) != payloads["attempt_owner"]:
        _fail("ATTEMPT_OWNER_CANONICAL_MISMATCH")
    if contract.artifact_json_bytes(candidate) != payloads["evaluation_candidate"]:
        _fail("EVALUATION_CANDIDATE_CANONICAL_MISMATCH")
    if contract.artifact_json_bytes(predictions) != payloads["predictions"]:
        _fail("PREDICTIONS_CANONICAL_MISMATCH")
    if contract.artifact_json_bytes(expected) != payloads["evidence"]:
        _fail("EXECUTION_EVIDENCE_RECOMPUTATION_MISMATCH")
    return preregistration, candidate, evidence


def build_review(
    *,
    preregistration: Mapping[str, Any],
    evidence: Mapping[str, Any],
    candidate: Mapping[str, Any],
) -> dict[str, Any]:
    gates = _mapping(evidence.get("gates"), "$.evidence.gates")
    comparison = _mapping(evidence.get("comparison"), "$.evidence.comparison")
    execution = _mapping(evidence.get("execution"), "$.evidence.execution")
    resources = _mapping(evidence.get("resources"), "$.evidence.resources")
    claims = _mapping(evidence.get("claims"), "$.evidence.claims")
    expected_gates = {name: True for name in contract.REQUIRED_GATES}
    if (
        evidence.get("gate_id") != contract.EXECUTION_GATE_ID
        or evidence.get("protocol_freeze_commit") != PROTOCOL_FREEZE_COMMIT
        or evidence.get("classification") != contract.MEASUREMENT_CLASSIFICATION
        or evidence.get("formal_gate_passed") is not True
        or evidence.get("next_gate") != REVIEW_GATE_ID
        or dict(gates) != expected_gates
        or dict(execution) != contract.expected_execution_counters()
        or dict(claims) != contract.execution_claims(formal_gate_passed=True)
        or evidence.get("runtime_eligible") is not False
    ):
        _fail("FORMAL_RESULT_BOUNDARY_MISMATCH")

    layer_fields = {
        "raw_outputs": "raw_utf8_output",
        "compiled_outputs": "canonical_compiled_json",
        "verifier_verdicts": "deterministic_verifier_verdict",
        "generated_token_counts": "generated_token_count",
    }
    for name in layer_fields:
        layer = _mapping(comparison.get(name), f"$.comparison.{name}")
        if (
            layer.get("exact") is not True
            or layer.get("exact_count") != contract.EXPECTED_RECORDS
            or layer.get("total") != contract.EXPECTED_RECORDS
            or layer.get("mismatch_record_ids") != []
            or layer.get("reference_sha256") != layer.get("replay_sha256")
        ):
            _fail(f"{name.upper()}_REPEATABILITY_MISMATCH")
    metrics = _mapping(comparison.get("metrics"), "$.comparison.metrics")
    if (
        metrics.get("exact") is not True
        or metrics.get("mismatch_names") != []
        or metrics.get("reference_sha256") != metrics.get("replay_sha256")
        or metrics.get("reference") != metrics.get("replay")
        or comparison.get("all_registered_layers_exact") is not True
    ):
        _fail("METRIC_REPEATABILITY_MISMATCH")

    resource_comparison = _mapping(
        comparison.get("resources"), "$.comparison.resources"
    )
    reference_resources = _mapping(
        resource_comparison.get("reference"), "$.resources.reference"
    )
    replay_resources = _mapping(
        resource_comparison.get("replay"), "$.resources.replay"
    )
    resource_delta = _mapping(
        resource_comparison.get("absolute_delta"), "$.resources.absolute_delta"
    )
    if (
        dict(replay_resources) != dict(resources)
        or resource_comparison.get("diagnostic_only") is not True
        or resource_comparison.get("exact") is not False
        or resource_comparison.get("resource_repeatability_established") is not False
        or resource_delta.get("elapsed_seconds")
        != replay_resources["elapsed_seconds"] - reference_resources["elapsed_seconds"]
        or resource_delta.get("peak_gpu_allocated_bytes") != 0
        or resource_delta.get("peak_gpu_reserved_bytes") != 0
    ):
        _fail("RESOURCE_DIAGNOSTIC_BOUNDARY_MISMATCH")
    for name, cap in contract.RESOURCE_CAPS.items():
        if float(resources[name]) > float(cap):
            _fail("RESOURCE_CAP_EXCEEDED")

    cases = _object_sequence(candidate.get("cases"), "$.candidate.cases")
    if len(cases) != contract.EXPECTED_RECORDS:
        _fail("RESULT_CASE_COUNT_MISMATCH")
    registered_environment = _mapping(
        preregistration.get("environment"), "$.preregistration.environment"
    )
    return {
        "mm005_document_chart_pdf_model_evaluation_repeatability_result_review_version": 1,
        "gate_id": REVIEW_GATE_ID,
        "reviewed_execution_gate_id": contract.EXECUTION_GATE_ID,
        "classification": CLASSIFICATION,
        "scope": "same_machine_registered_environment_fixed_32_case_evaluation",
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
            "candidate_and_predictions_revalidated": True,
            "compiler_verifier_and_metrics_recomputed": True,
            "evidence_rebuilt_from_frozen_inputs": True,
            "historical_timestamp_and_resources_reused": True,
            "timestamp_and_resources_independently_remeasured": False,
        },
        "formal_measurement": {
            "required_gates": list(contract.REQUIRED_GATES),
            "passed_gates": list(contract.REQUIRED_GATES),
            "formal_gate_passed": True,
            "equality_was_measurement_gate": False,
            "quality_threshold_registered": False,
            "resource_caps_were_integrity_gate": True,
        },
        "comparison": copy.deepcopy(dict(comparison)),
        "comparison_semantics": {
            "all_registered_layers_exact_definition": list(layer_fields.values())
            + ["canonical_total_metrics"],
            "transformer_internal_layers_compared": False,
            "generated_token_id_sequences_persisted": False,
            "generated_token_sequence_exact_claimed": False,
            "per_case_latency_registered_as_repeatability_layer": False,
        },
        "execution": copy.deepcopy(dict(execution)),
        "resources": {
            "baseline": copy.deepcopy(dict(reference_resources)),
            "replay": copy.deepcopy(dict(replay_resources)),
            "absolute_delta": copy.deepcopy(dict(resource_delta)),
            "registered_caps": copy.deepcopy(contract.RESOURCE_CAPS),
            "both_runs_within_caps": True,
            "measurements_exact": False,
            "diagnostic_only": True,
        },
        "registered_environment": copy.deepcopy(dict(registered_environment)),
        "environment_evidence": {
            "formal_runner_observed_environment_gate_passed": True,
            "frozen_runner_requires_live_mapping_exact_before_generation": True,
            "observed_environment_mapping_separately_persisted": False,
            "post_run_exact_observed_mapping_independently_recoverable": False,
            "preflight_registered_fields_observed_exact": True,
            "preflight_evidence_class": "reviewer_observed_untracked_context",
        },
        "scope_semantics": {
            "same_machine_definition": (
                "same_windows_host_and_registered_environment_fields"
            ),
            "machine_id_attested": False,
            "hardware_identity_attested": False,
        },
        "claims": {
            "baseline_attempt_consumed": True,
            "replay_attempt_consumed": True,
            "replay_executed": True,
            "model_evaluated": True,
            "formal_measurement_complete": True,
            "raw_outputs_exact_32_of_32": True,
            "compiled_outputs_exact_32_of_32": True,
            "verifier_verdicts_exact_32_of_32": True,
            "metrics_exact": True,
            "generated_token_counts_exact_32_of_32": True,
            "same_machine_fixed_suite_repeatability_established": True,
            "training_repeatability_established": False,
            "resource_repeatability_established": False,
            "cross_machine_reproducibility_established": False,
            "quality_improved": False,
            "generalized_quality_established": False,
            "safety_established": False,
            "real_content_behavior_established": False,
            "serving_eligible": False,
            "promotion_eligible": False,
            "runtime_eligible": False,
        },
        "limitations": {
            "single_reference_and_single_replay": True,
            "same_machine_only": True,
            "fixed_synthetic_32_case_evaluation_only": True,
            "observed_environment_mapping_not_separately_persisted": True,
            "complete_transitive_dependency_hash_lock": False,
            "generated_token_ids_not_persisted": True,
            "per_case_latency_repeatability_tested": False,
            "training_repeatability_tested": False,
            "resource_repeatability_tested": False,
            "full_evaluation_variance_established": False,
            "external_execution_count_attested": False,
            "cross_machine_tested": False,
            "real_content_tested": False,
            "runtime_integration_tested": False,
        },
        "next_gate": NEXT_GATE_ID,
        "next_action": (
            "freeze a model-free Browser Research environment-adaptation protocol "
            "before any new data generation, model call, training, or Runtime change"
        ),
        "runtime_eligible": False,
    }


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
    except contract.MM005EvaluationRepeatabilityError as exc:
        raise MM005EvaluationRepeatabilityResultError(str(exc)) from exc
    if contract.artifact_json_bytes(raw) != payload:
        _fail(f"{label.upper()}_NONCANONICAL_JSON")
    return cast(dict[str, Any], raw)


def _mapping(value: object, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail(f"EXPECTED_OBJECT_AT_{location}")
    return cast(Mapping[str, Any], value)


def _byte_mapping(value: object, location: str) -> Mapping[str, bytes]:
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
    raise MM005EvaluationRepeatabilityResultError(code)


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
        MM005EvaluationRepeatabilityResultError,
        file_validator.MM003PostTrainingV2ResultError,
        contract.MM005EvaluationRepeatabilityError,
    ) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(summary, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
