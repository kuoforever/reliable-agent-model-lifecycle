"""Fail-closed MM-005 same-machine fixed-suite evaluation replay contract.

The module is model-free.  It authenticates the completed 32-case baseline,
freezes one unchanged replay, and derives raw, compiled, Verifier, metric, and
generated-token comparisons.  Equality is an observed outcome rather than a
measurement-completion threshold.
"""

from __future__ import annotations

import copy
import re
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any, NoReturn, cast

from . import mm005_document_chart_pdf_model_evaluation as baseline

PREREGISTRATION_VERSION = 1
ATTEMPT_OWNER_VERSION = 1
CANDIDATE_VERSION = 1
PREDICTIONS_VERSION = 1
EVIDENCE_VERSION = 1
FAILURE_VERSION = 1

PROTOCOL_GATE_ID = (
    "MM-005-document-chart-pdf-model-evaluation-repeatability-protocol-v1"
)
EXECUTION_GATE_ID = (
    "MM-005-document-chart-pdf-model-evaluation-repeatability-execution-v1"
)
RESULT_REVIEW_GATE_ID = (
    "MM-005-document-chart-pdf-model-evaluation-repeatability-result-review-v1"
)
FAILURE_CLASSIFICATION_GATE_ID = (
    "MM-005-document-chart-pdf-model-evaluation-repeatability-failure-classification-v1"
)
EXPERIMENT_ID = "mm005-document-chart-pdf-model-eval-repeatability-v1"
RUN_ID = "mm005-document-chart-pdf-model-eval-replay-r1"

PREREGISTRATION_PATH = (
    "configs/mm005_document_chart_pdf_model_evaluation_repeatability_protocol_v1.json"
)
RUN_OUTPUT_ROOT = (
    "work/evaluation-runs/mm005-document-chart-pdf-model-eval-repeatability-v1"
)
ATTEMPT_OWNER_PATH = f"{RUN_OUTPUT_ROOT}/attempt-owner.json"
EVALUATION_CANDIDATE_PATH = f"{RUN_OUTPUT_ROOT}/evaluation-candidate.json"
PREDICTIONS_PATH = f"{RUN_OUTPUT_ROOT}/predictions.json"
EVIDENCE_PATH = f"{RUN_OUTPUT_ROOT}/evidence.json"
FAILURE_PATH = f"{RUN_OUTPUT_ROOT}/failure.json"

BASELINE_PROTOCOL_FREEZE_COMMIT = "3be0083c3197111d57a4a5e5f70feced9f2c96f9"
BASELINE_RESULT_MERGE_COMMIT = "056eb8d050eb0f0491ff21a07bd5b7716abf7eb8"
BASELINE_PREREGISTRATION_RECEIPT: dict[str, int | str] = {
    "path": baseline.PREREGISTRATION_PATH,
    "bytes": 58_414,
    "sha256": "sha256:cdb8d1ea09221763d87cd79ba752d9af8264ce49b7cf600eed338a073a04561b",
}
_BASELINE_PREFIX = "baseline/mm005-document-chart-pdf-model-eval-v1-"
BASELINE_ARTIFACTS: dict[str, dict[str, int | str]] = {
    "attempt_owner": {
        "path": f"{_BASELINE_PREFIX}attempt-owner.json",
        "bytes": 656,
        "sha256": "sha256:ca9e420fbce5582cab5944e0c290e569f97cad85ad3a5cf9e3c53aa13989d00b",
    },
    "evaluation_candidate": {
        "path": f"{_BASELINE_PREFIX}evaluation-candidate.json",
        "bytes": 32_190,
        "sha256": "sha256:e26f6a9ca03e826f627ae90aca5b2fdcf5bbed770d9752aa9ba74982ed7d12ea",
    },
    "predictions": {
        "path": f"{_BASELINE_PREFIX}predictions.json",
        "bytes": 18_543,
        "sha256": "sha256:f9a545175688451fc5025eb1e90a1e1354a59c536887a54fe62deb80a019fff7",
    },
    "evidence": {
        "path": f"{_BASELINE_PREFIX}evidence.json",
        "bytes": 7_495,
        "sha256": "sha256:5e330dde1debe7a207638d164aade8ab2c63fbcd8149b3178d64a16afd0fc78e",
    },
}
BASELINE_REVIEW_RECEIPT: dict[str, int | str] = {
    "path": f"{_BASELINE_PREFIX}result-review.json",
    "bytes": 15_235,
    "sha256": "sha256:7cc4990f900787123f078d2387855e4708b5eadb8d6705bb6364d8cab2f935a7",
}

PROTOCOL_SOURCE_PATHS = {
    "baseline_contract": (
        "src/fullcycle_bridge/mm005_document_chart_pdf_model_evaluation.py"
    ),
    "baseline_builder": (
        "scripts/prepare_mm005_document_chart_pdf_model_evaluation.py"
    ),
    "baseline_runner": "scripts/run_mm005_document_chart_pdf_model_evaluation.py",
    "baseline_result_validator": (
        "scripts/validate_mm005_document_chart_pdf_model_evaluation_result.py"
    ),
    "repeatability_contract": (
        "src/fullcycle_bridge/"
        "mm005_document_chart_pdf_model_evaluation_repeatability.py"
    ),
    "repeatability_builder": (
        "scripts/prepare_mm005_document_chart_pdf_model_evaluation_repeatability.py"
    ),
    "repeatability_runner": (
        "scripts/run_mm005_document_chart_pdf_model_evaluation_repeatability.py"
    ),
    "attempt_guard_runner": ("scripts/run_mm003_post_training_eval_repeatability.py"),
    "model_dependency_runner": "scripts/run_mm003_qlora_post_training_v2.py",
    "model_generation_runner": ("scripts/run_mm003_multimodal_gui_action_baseline.py"),
    "adapter_verifier": (
        "src/fullcycle_bridge/mm005_document_chart_pdf_adapter_verifier.py"
    ),
    "adapter_verifier_implementation": (
        "src/fullcycle_bridge/"
        "mm005_document_chart_pdf_adapter_verifier_implementation.py"
    ),
}

EXPECTED_RECORDS = baseline.EXPECTED_RECORDS
RESOURCE_CAPS = dict(baseline.RESOURCE_CAPS)
REQUIRED_GATES = (
    "protocol_integrity",
    "baseline_result_integrity",
    "exact_candidate_and_environment",
    "exact_inputs_prompts_compiler_verifier_generation",
    "offline_single_replay",
    "attempt_ownership",
    "candidate_and_predictions_binding",
    "layered_comparison_complete",
    "resource_caps",
    "fail_closed_claims",
)
FAILURE_STAGES = (
    "output_claim",
    "dependency_and_environment_validation",
    "model_load_and_generation",
    "candidate_persistence",
    "scoring",
    "predictions_persistence",
    "evidence_persistence",
)

FREEZE_CLAIMS = {
    "baseline_attempt_consumed": True,
    "baseline_evaluation_executed": True,
    "baseline_model_evaluated": True,
    "baseline_formal_measurement_complete": True,
    "repeatability_protocol_frozen": True,
    "replay_attempt_consumed": False,
    "replay_executed": False,
    "replay_model_evaluated": False,
    "formal_measurement_complete": False,
    "same_machine_fixed_suite_repeatability_established": False,
    "training_repeatability_established": False,
    "resource_repeatability_established": False,
    "cross_machine_reproducibility_established": False,
    "quality_improved": False,
    "generalized_quality_established": False,
    "safety_established": False,
    "serving_eligible": False,
    "promotion_eligible": False,
    "runtime_eligible": False,
}

MEASUREMENT_CLASSIFICATION = (
    "same_machine_fixed_32_case_repeatability_measurement_complete_within_caps"
)
RESOURCE_EXCEEDED_CLASSIFICATION = (
    "same_machine_fixed_32_case_repeatability_measurement_resource_exceeded"
)
INTEGRITY_FAILURE_CLASSIFICATION = (
    "same_machine_fixed_32_case_repeatability_measurement_integrity_failed"
)

_SHA256 = re.compile(r"sha256:[0-9a-f]{64}\Z")
_COMMIT = re.compile(r"[0-9a-f]{40}\Z")


class MM005EvaluationRepeatabilityError(ValueError):
    """Raised when protocol or replay evidence fails closed."""


def artifact_json_bytes(value: object) -> bytes:
    return cast(bytes, baseline.artifact_json_bytes(value))


def sha256_bytes(payload: bytes) -> str:
    return cast(str, baseline.sha256_bytes(payload))


def parse_strict_json_bytes(payload: bytes, *, location: str) -> dict[str, Any]:
    return cast(
        dict[str, Any], baseline.parse_strict_json_bytes(payload, location=location)
    )


def expected_execution_counters() -> dict[str, int]:
    return cast(dict[str, int], baseline.expected_execution_counters())


def expected_preregistration(
    *,
    freeze_status: str,
    source_receipts: Mapping[str, Mapping[str, Any]],
    baseline_preregistration_payload: bytes,
    baseline_artifact_payloads: Mapping[str, bytes],
    baseline_review_payload: bytes,
    baseline_inputs: Mapping[str, Any],
    output_absent: bool,
) -> dict[str, Any]:
    if freeze_status not in {"draft", "frozen"}:
        _fail("FREEZE_STATUS_INVALID")
    if output_absent is not True:
        _fail("OUTPUT_ALREADY_EXISTS")
    sources = _closed_receipts(source_receipts, "$.source_receipts")
    authenticated = validate_baseline_payloads(
        baseline_preregistration_payload=baseline_preregistration_payload,
        baseline_artifact_payloads=baseline_artifact_payloads,
        baseline_review_payload=baseline_review_payload,
        baseline_inputs=baseline_inputs,
    )
    preregistration = authenticated["preregistration"]
    reference_candidate = authenticated["candidate"]
    reference_evidence = authenticated["evidence"]
    case_order = [str(item["record_id"]) for item in reference_candidate["cases"]]
    reference = comparison_reference(
        candidate=reference_candidate,
        evidence=reference_evidence,
    )
    candidate = _mapping(preregistration.get("candidate"), "$.candidate")
    execution = _mapping(
        preregistration.get("execution_protocol"), "$.execution_protocol"
    )
    return {
        "mm005_document_chart_pdf_model_evaluation_repeatability_protocol_version": (
            PREREGISTRATION_VERSION
        ),
        "gate_id": PROTOCOL_GATE_ID,
        "freeze_status": freeze_status,
        "decision": "outcome_neutral_same_machine_fixed_32_case_replay_protocol",
        "experiment_id": EXPERIMENT_ID,
        "run_id": RUN_ID,
        "source_receipts": sources,
        "source_lineage": {
            "baseline_protocol_freeze_commit": BASELINE_PROTOCOL_FREEZE_COMMIT,
            "baseline_result_merge_commit": BASELINE_RESULT_MERGE_COMMIT,
            "baseline_preregistration": _receipt(
                str(BASELINE_PREREGISTRATION_RECEIPT["path"]),
                baseline_preregistration_payload,
            ),
            "baseline_artifacts": {
                name: _receipt(str(BASELINE_ARTIFACTS[name]["path"]), payload)
                for name, payload in sorted(baseline_artifact_payloads.items())
            },
            "baseline_result_review": _receipt(
                str(BASELINE_REVIEW_RECEIPT["path"]), baseline_review_payload
            ),
        },
        "candidate": copy.deepcopy(dict(candidate)),
        "environment": copy.deepcopy(candidate["environment"]),
        "input_suite": copy.deepcopy(preregistration["input_suite"]),
        "prompt_contract": copy.deepcopy(preregistration["prompt_contract"]),
        "compiler": copy.deepcopy(preregistration["compiler"]),
        "verifier": copy.deepcopy(preregistration["verifier"]),
        "generation": copy.deepcopy(execution["generation"]),
        "execution_protocol": {
            "model_snapshot_root": baseline.MODEL_SNAPSHOT_ROOT,
            "adapter_root": baseline.ADAPTER_ROOT,
            "python_invocation": copy.deepcopy(execution["python_invocation"]),
            "run_count": 1,
            "fresh_base_loads": 1,
            "independent_adapter_loads": 1,
            "generate_calls": EXPECTED_RECORDS,
            "case_order": case_order,
            "retry_count": 0,
            "network_used": False,
            "local_files_only": True,
            "training_runs": 0,
            "optimizer_steps": 0,
            "backward_calls": 0,
            "adapter_writes": 0,
            "model_or_tensor_saves": 0,
            "attempt_consumption": {
                "consumed_when": "owner_marked_directory_atomically_claimed",
                "retry_allowed_before_consumption": True,
                "retry_allowed_after_consumption": False,
            },
        },
        "comparison_protocol": {
            "scope": (
                "same_machine_registered_environment_unchanged_fixed_32_case_suite"
            ),
            "case_order": case_order,
            "reference": reference,
            "layers": {
                "raw_output": {
                    "comparison": "exact_utf8_bytes",
                    "normalization_allowed": False,
                    "case_count": EXPECTED_RECORDS,
                },
                "compiled_output": {
                    "comparison": "exact_canonical_json",
                    "recompiled_from_raw": True,
                    "case_count": EXPECTED_RECORDS,
                },
                "verifier_verdict": {
                    "comparison": "exact_canonical_json",
                    "recomputed_from_compiled_and_gold": True,
                    "case_count": EXPECTED_RECORDS,
                },
                "metrics": {
                    "comparison": "exact_structured_equality",
                    "reference_recomputed": True,
                    "replay_recomputed": True,
                },
                "generated_token_count": {
                    "comparison": "exact_integer",
                    "case_count": EXPECTED_RECORDS,
                },
            },
            "equality_required_for_measurement_completion": False,
            "drift_must_be_preserved": True,
            "drift_authorizes_retry": False,
        },
        "resource_protocol": {
            "integrity_caps": copy.deepcopy(RESOURCE_CAPS),
            "baseline_observation": copy.deepcopy(reference_candidate["resources"]),
            "comparison_is_diagnostic_only": True,
            "equality_required": False,
            "resource_repeatability_claimed": False,
        },
        "outputs": {
            "output_directory": RUN_OUTPUT_ROOT,
            "attempt_owner": ATTEMPT_OWNER_PATH,
            "evaluation_candidate": EVALUATION_CANDIDATE_PATH,
            "predictions": PREDICTIONS_PATH,
            "evidence": EVIDENCE_PATH,
            "failure": FAILURE_PATH,
            "exclusive_create": True,
            "success_and_failure_are_mutually_exclusive": True,
            "machine_paths_recorded": False,
            "exception_messages_or_tracebacks_recorded": False,
            "adapter_copy_allowed": False,
            "model_or_tensor_save_allowed": False,
        },
        "formal_gate": {
            "required_gates": list(REQUIRED_GATES),
            "equality_is_gate": False,
            "quality_threshold_is_gate": False,
            "resource_caps_are_integrity_gate": True,
        },
        "authority_contract": copy.deepcopy(preregistration["authority_contract"]),
        "freeze_preconditions": {
            "fixed_replay_output_absent": True,
            "second_model_imported_at_protocol_freeze": False,
            "second_model_called_at_protocol_freeze": False,
            "replay_attempt_consumed_at_protocol_freeze": False,
        },
        "claims": copy.deepcopy(FREEZE_CLAIMS),
        "limitations": {
            "fixed_synthetic_suite_only": True,
            "same_machine_registered_environment_only": True,
            "training_repeatability_tested": False,
            "resource_repeatability_tested": False,
            "cross_machine_reproducibility_tested": False,
            "generalized_quality_tested": False,
            "safety_tested": False,
            "runtime_integration_tested": False,
        },
        "next_gate": EXECUTION_GATE_ID,
    }


def validate_preregistration(value: object, **kwargs: Any) -> dict[str, Any]:
    expected = expected_preregistration(freeze_status="frozen", **kwargs)
    if not _json_exact(value, expected):
        _fail("PREREGISTRATION_MISMATCH")
    return expected


def validate_baseline_payloads(
    *,
    baseline_preregistration_payload: bytes,
    baseline_artifact_payloads: Mapping[str, bytes],
    baseline_review_payload: bytes,
    baseline_inputs: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    _check_receipt(
        baseline_preregistration_payload,
        BASELINE_PREREGISTRATION_RECEIPT,
        "BASELINE_PREREGISTRATION",
    )
    if set(baseline_artifact_payloads) != set(BASELINE_ARTIFACTS):
        _fail("BASELINE_ARTIFACT_SET_MISMATCH")
    for name, receipt in BASELINE_ARTIFACTS.items():
        _check_receipt(baseline_artifact_payloads[name], receipt, name.upper())
    _check_receipt(baseline_review_payload, BASELINE_REVIEW_RECEIPT, "BASELINE_REVIEW")
    preregistration = _parse_canonical(
        baseline_preregistration_payload, "baseline_preregistration"
    )
    owner = _parse_canonical(
        baseline_artifact_payloads["attempt_owner"], "baseline_attempt_owner"
    )
    candidate = _parse_canonical(
        baseline_artifact_payloads["evaluation_candidate"], "baseline_candidate"
    )
    predictions = _parse_canonical(
        baseline_artifact_payloads["predictions"], "baseline_predictions"
    )
    evidence = _parse_canonical(
        baseline_artifact_payloads["evidence"], "baseline_evidence"
    )
    review = _parse_canonical(baseline_review_payload, "baseline_review")
    try:
        baseline.validate_preregistration(preregistration, **dict(baseline_inputs))
        baseline.validate_evidence(
            evidence,
            protocol_freeze_commit=BASELINE_PROTOCOL_FREEZE_COMMIT,
            preregistration_payload=baseline_preregistration_payload,
            attempt_owner_payload=baseline_artifact_payloads["attempt_owner"],
            evaluation_candidate_payload=baseline_artifact_payloads[
                "evaluation_candidate"
            ],
            predictions_payload=baseline_artifact_payloads["predictions"],
            records=_object_sequence(baseline_inputs.get("records"), "$.records"),
            image_payloads=_bytes_mapping(
                baseline_inputs.get("image_payloads"), "$.image_payloads"
            ),
        )
    except baseline.MM005ModelEvaluationError as exc:
        raise MM005EvaluationRepeatabilityError(str(exc)) from exc
    claims = _mapping(review.get("claims"), "$.baseline_review.claims")
    if (
        evidence.get("formal_gate_passed") is not True
        or evidence.get("classification")
        != "outcome_neutral_measurement_complete_within_registered_caps"
        or review.get("gate_id") != baseline.RESULT_REVIEW_GATE_ID
        or review.get("next_gate") != PROTOCOL_GATE_ID
        or review.get("classification")
        != "fixed_synthetic_suite_joint_exact_19_of_32_with_task_family_skew"
        or claims.get("repeatability_established") is not False
        or review.get("runtime_eligible") is not False
    ):
        _fail("BASELINE_RESULT_BOUNDARY_MISMATCH")
    return {
        "preregistration": preregistration,
        "owner": owner,
        "candidate": candidate,
        "predictions": predictions,
        "evidence": evidence,
        "review": review,
    }


def comparison_reference(
    *, candidate: Mapping[str, Any], evidence: Mapping[str, Any]
) -> dict[str, Any]:
    cases = _object_sequence(candidate.get("cases"), "$.candidate.cases")
    metrics = _mapping(evidence.get("metrics"), "$.evidence.metrics")
    return {
        "raw_outputs_sha256": _case_layer_digest(cases, "raw_output"),
        "compiled_outputs_sha256": _case_layer_digest(cases, "compiled_output"),
        "verifier_verdicts_sha256": _case_layer_digest(cases, "verdict"),
        "metrics_sha256": sha256_bytes(artifact_json_bytes(metrics)),
        "generated_token_counts_sha256": _case_layer_digest(cases, "generated_tokens"),
    }


def build_attempt_owner(
    *, protocol_freeze_commit: str, preregistration_payload: bytes, attempt_id: str
) -> dict[str, Any]:
    _validate_commit(protocol_freeze_commit)
    if re.fullmatch(r"[0-9a-f]{64}", attempt_id) is None:
        _fail("ATTEMPT_ID_INVALID")
    return {
        "mm005_document_chart_pdf_model_evaluation_repeatability_attempt_owner_version": (
            ATTEMPT_OWNER_VERSION
        ),
        "gate_id": EXECUTION_GATE_ID,
        "experiment_id": EXPERIMENT_ID,
        "run_id": RUN_ID,
        "attempt_id": attempt_id,
        "protocol_freeze_commit": protocol_freeze_commit,
        "preregistration": _receipt(PREREGISTRATION_PATH, preregistration_payload),
        "claims": {
            "replay_attempt_consumed": True,
            "retry_allowed": False,
            "model_output_has_execution_authority": False,
            "runtime_eligible": False,
        },
    }


def validate_attempt_owner(
    value: object,
    *,
    protocol_freeze_commit: str,
    preregistration_payload: bytes,
) -> dict[str, Any]:
    observed = _mapping(value, "$.attempt_owner")
    expected = build_attempt_owner(
        protocol_freeze_commit=protocol_freeze_commit,
        preregistration_payload=preregistration_payload,
        attempt_id=str(observed.get("attempt_id")),
    )
    if not _json_exact(observed, expected):
        _fail("ATTEMPT_OWNER_MISMATCH")
    return expected


def build_evaluation_candidate(
    *,
    protocol_freeze_commit: str,
    preregistration_payload: bytes,
    attempt_owner_payload: bytes,
    cases: Sequence[Mapping[str, Any]],
    records: Sequence[Mapping[str, Any]],
    image_payloads: Mapping[str, bytes],
    execution: Mapping[str, Any],
    resources: Mapping[str, Any],
) -> dict[str, Any]:
    _validate_commit(protocol_freeze_commit)
    owner = _parse_canonical(attempt_owner_payload, "attempt_owner")
    validate_attempt_owner(
        owner,
        protocol_freeze_commit=protocol_freeze_commit,
        preregistration_payload=preregistration_payload,
    )
    ordered = sorted(records, key=lambda item: str(item.get("record_id")))
    if len(cases) != EXPECTED_RECORDS or len(ordered) != EXPECTED_RECORDS:
        _fail("CANDIDATE_CASE_COUNT_MISMATCH")
    rebuilt: list[dict[str, Any]] = []
    for index, (record, raw_case) in enumerate(zip(ordered, cases, strict=True)):
        case = _mapping(raw_case, f"$.cases[{index}]")
        try:
            expected_case = baseline.build_case_result(
                record=record,
                image_payloads=image_payloads,
                raw_output=_strict_string(
                    case.get("raw_output"), f"$.cases[{index}].raw_output"
                ),
                generated_tokens=_strict_int(
                    case.get("generated_tokens"),
                    f"$.cases[{index}].generated_tokens",
                ),
                latency_seconds=_strict_number(
                    case.get("latency_seconds"),
                    f"$.cases[{index}].latency_seconds",
                ),
            )
        except baseline.MM005ModelEvaluationError as exc:
            raise MM005EvaluationRepeatabilityError(str(exc)) from exc
        if not _json_exact(case, expected_case):
            _fail("CANDIDATE_CASE_RECOMPUTATION_MISMATCH")
        rebuilt.append(expected_case)
    if not _json_exact(execution, expected_execution_counters()):
        _fail("EXECUTION_COUNTERS_MISMATCH")
    checked_resources = _validated_resources(resources)
    return {
        "mm005_document_chart_pdf_model_evaluation_repeatability_candidate_version": (
            CANDIDATE_VERSION
        ),
        "gate_id": EXECUTION_GATE_ID,
        "experiment_id": EXPERIMENT_ID,
        "run_id": RUN_ID,
        "protocol_freeze_commit": protocol_freeze_commit,
        "preregistration": _receipt(PREREGISTRATION_PATH, preregistration_payload),
        "attempt_owner": _receipt(ATTEMPT_OWNER_PATH, attempt_owner_payload),
        "producer": {
            "kind": "model",
            "model_id": baseline.MODEL_ID,
            "model_revision": baseline.MODEL_REVISION,
            "adapter_model_id": baseline.ADAPTER_MODEL_ID,
            "execution_form": "nf4_base_plus_read_only_lora_adapter",
        },
        "execution": copy.deepcopy(dict(execution)),
        "resources": checked_resources,
        "cases": rebuilt,
        "claims": {
            "all_registered_model_calls_completed": True,
            "comparison_completed": False,
            "formal_measurement_complete": False,
            "same_machine_fixed_suite_repeatability_established": False,
            "model_output_has_execution_authority": False,
            "runtime_eligible": False,
        },
    }


def validate_evaluation_candidate(
    value: object,
    *,
    protocol_freeze_commit: str,
    preregistration_payload: bytes,
    attempt_owner_payload: bytes,
    records: Sequence[Mapping[str, Any]],
    image_payloads: Mapping[str, bytes],
) -> dict[str, Any]:
    observed = _mapping(value, "$.evaluation_candidate")
    expected = build_evaluation_candidate(
        protocol_freeze_commit=protocol_freeze_commit,
        preregistration_payload=preregistration_payload,
        attempt_owner_payload=attempt_owner_payload,
        cases=_object_sequence(observed.get("cases"), "$.candidate.cases"),
        records=records,
        image_payloads=image_payloads,
        execution=_mapping(observed.get("execution"), "$.candidate.execution"),
        resources=_mapping(observed.get("resources"), "$.candidate.resources"),
    )
    if not _json_exact(observed, expected):
        _fail("EVALUATION_CANDIDATE_MISMATCH")
    return expected


def build_predictions(candidate: Mapping[str, Any]) -> dict[str, Any]:
    cases = _object_sequence(candidate.get("cases"), "$.candidate.cases")
    return {
        "mm005_document_chart_pdf_model_evaluation_repeatability_predictions_version": (
            PREDICTIONS_VERSION
        ),
        "gate_id": EXECUTION_GATE_ID,
        "suite_id": baseline.SUITE_ID,
        "producer": copy.deepcopy(candidate["producer"]),
        "records": [
            {
                "record_id": item["record_id"],
                "raw_output": item["raw_output"],
                "compiled_output": copy.deepcopy(item["compiled_output"]),
                "verdict": copy.deepcopy(item["verdict"]),
                "generated_tokens": item["generated_tokens"],
                "latency_seconds": item["latency_seconds"],
            }
            for item in cases
        ],
        "claims": {
            "contains_model_outputs": True,
            "model_output_has_execution_authority": False,
            "runtime_eligible": False,
        },
    }


def compare_candidates(
    *,
    reference_candidate: Mapping[str, Any],
    reference_evidence: Mapping[str, Any],
    replay_candidate: Mapping[str, Any],
    records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    reference_cases = _object_sequence(
        reference_candidate.get("cases"), "$.reference.cases"
    )
    replay_cases = _object_sequence(replay_candidate.get("cases"), "$.replay.cases")
    case_order = [str(item["record_id"]) for item in reference_cases]
    if (
        len(reference_cases) != EXPECTED_RECORDS
        or len(replay_cases) != EXPECTED_RECORDS
        or [str(item["record_id"]) for item in replay_cases] != case_order
    ):
        _fail("COMPARISON_CASE_ORDER_MISMATCH")
    layers: dict[str, tuple[str, list[str]]] = {}
    for output_name, field in (
        ("raw_outputs", "raw_output"),
        ("compiled_outputs", "compiled_output"),
        ("verifier_verdicts", "verdict"),
        ("generated_token_counts", "generated_tokens"),
    ):
        mismatches = [
            case_order[index]
            for index, (left, right) in enumerate(
                zip(reference_cases, replay_cases, strict=True)
            )
            if not _layer_exact(left[field], right[field], raw=field == "raw_output")
        ]
        layers[output_name] = (field, mismatches)
    try:
        reference_metrics = baseline.score_case_results(records, reference_cases)
        replay_metrics = baseline.score_case_results(records, replay_cases)
    except baseline.MM005ModelEvaluationError as exc:
        raise MM005EvaluationRepeatabilityError(str(exc)) from exc
    persisted_metrics = _mapping(
        reference_evidence.get("metrics"), "$.reference_evidence.metrics"
    )
    if not _json_exact(reference_metrics, persisted_metrics):
        _fail("REFERENCE_METRICS_RECOMPUTATION_MISMATCH")
    metric_names = list(reference_metrics)
    if list(replay_metrics) != metric_names:
        _fail("METRIC_SET_OR_ORDER_MISMATCH")
    metric_mismatches = [
        name
        for name in metric_names
        if not _json_exact(reference_metrics[name], replay_metrics[name])
    ]
    result: dict[str, Any] = {
        "case_order": case_order,
        "raw_outputs": _layer_result(
            reference_cases, replay_cases, *layers["raw_outputs"]
        ),
        "compiled_outputs": _layer_result(
            reference_cases, replay_cases, *layers["compiled_outputs"]
        ),
        "verifier_verdicts": _layer_result(
            reference_cases, replay_cases, *layers["verifier_verdicts"]
        ),
        "generated_token_counts": _layer_result(
            reference_cases, replay_cases, *layers["generated_token_counts"]
        ),
        "metrics": {
            "exact": not metric_mismatches,
            "mismatch_names": metric_mismatches,
            "reference_sha256": sha256_bytes(artifact_json_bytes(reference_metrics)),
            "replay_sha256": sha256_bytes(artifact_json_bytes(replay_metrics)),
            "reference": copy.deepcopy(reference_metrics),
            "replay": copy.deepcopy(replay_metrics),
        },
        "resources": _resource_diagnostics(
            _mapping(reference_candidate.get("resources"), "$.reference.resources"),
            _mapping(replay_candidate.get("resources"), "$.replay.resources"),
        ),
    }
    result["all_registered_layers_exact"] = all(
        _mapping(result[name], f"$.comparison.{name}").get("exact") is True
        for name in (
            "raw_outputs",
            "compiled_outputs",
            "verifier_verdicts",
            "generated_token_counts",
            "metrics",
        )
    )
    return result


def build_evidence(
    *,
    protocol_freeze_commit: str,
    preregistration_payload: bytes,
    preregistration: Mapping[str, Any],
    attempt_owner_payload: bytes,
    evaluation_candidate_payload: bytes,
    predictions_payload: bytes,
    reference_candidate: Mapping[str, Any],
    reference_evidence: Mapping[str, Any],
    records: Sequence[Mapping[str, Any]],
    image_payloads: Mapping[str, bytes],
    observed_environment: Mapping[str, Any],
    captured_at_utc: str,
) -> dict[str, Any]:
    _validate_timestamp(captured_at_utc)
    owner = _parse_canonical(attempt_owner_payload, "attempt_owner")
    candidate = _parse_canonical(evaluation_candidate_payload, "candidate")
    predictions = _parse_canonical(predictions_payload, "predictions")
    validate_attempt_owner(
        owner,
        protocol_freeze_commit=protocol_freeze_commit,
        preregistration_payload=preregistration_payload,
    )
    checked_candidate = validate_evaluation_candidate(
        candidate,
        protocol_freeze_commit=protocol_freeze_commit,
        preregistration_payload=preregistration_payload,
        attempt_owner_payload=attempt_owner_payload,
        records=records,
        image_payloads=image_payloads,
    )
    expected_predictions = build_predictions(checked_candidate)
    if not _json_exact(predictions, expected_predictions):
        _fail("PREDICTIONS_MISMATCH")
    comparison = compare_candidates(
        reference_candidate=reference_candidate,
        reference_evidence=reference_evidence,
        replay_candidate=checked_candidate,
        records=records,
    )
    reference = comparison_reference(
        candidate=reference_candidate, evidence=reference_evidence
    )
    comparison_protocol = _mapping(
        preregistration.get("comparison_protocol"), "$.comparison_protocol"
    )
    resources = _mapping(checked_candidate.get("resources"), "$.candidate.resources")
    gates = {
        "protocol_integrity": (
            artifact_json_bytes(preregistration) == preregistration_payload
            and preregistration.get("gate_id") == PROTOCOL_GATE_ID
            and preregistration.get("freeze_status") == "frozen"
            and bool(_COMMIT.fullmatch(protocol_freeze_commit))
        ),
        "baseline_result_integrity": (
            reference_evidence.get("formal_gate_passed") is True
            and _json_exact(comparison_protocol.get("reference"), reference)
        ),
        "exact_candidate_and_environment": (
            _json_exact(
                checked_candidate.get("producer"), reference_candidate.get("producer")
            )
            and _json_exact(observed_environment, preregistration.get("environment"))
        ),
        "exact_inputs_prompts_compiler_verifier_generation": (
            [item["record_id"] for item in checked_candidate["cases"]]
            == preregistration["input_suite"]["case_order"]
            and preregistration["comparison_protocol"][
                "equality_required_for_measurement_completion"
            ]
            is False
        ),
        "offline_single_replay": _json_exact(
            checked_candidate.get("execution"), expected_execution_counters()
        ),
        "attempt_ownership": artifact_json_bytes(owner) == attempt_owner_payload,
        "candidate_and_predictions_binding": (
            artifact_json_bytes(checked_candidate) == evaluation_candidate_payload
            and artifact_json_bytes(expected_predictions) == predictions_payload
        ),
        "layered_comparison_complete": (
            len(comparison["case_order"]) == EXPECTED_RECORDS
            and all(
                _mapping(comparison[name], f"$.comparison.{name}").get("total")
                == EXPECTED_RECORDS
                for name in (
                    "raw_outputs",
                    "compiled_outputs",
                    "verifier_verdicts",
                    "generated_token_counts",
                )
            )
            and isinstance(comparison["metrics"]["exact"], bool)
        ),
        "resource_caps": all(
            _strict_number(resources[key], f"$.resources.{key}") <= limit
            for key, limit in RESOURCE_CAPS.items()
        ),
    }
    pre_claims_passed = all(gates.values())
    claims = execution_claims(formal_gate_passed=pre_claims_passed)
    gates["fail_closed_claims"] = _claims_fail_closed(
        claims, formal_gate_passed=pre_claims_passed
    )
    if tuple(gates) != REQUIRED_GATES:
        _fail("FORMAL_GATE_SET_OR_ORDER_MISMATCH")
    formal_gate_passed = all(gates.values())
    claims = execution_claims(formal_gate_passed=formal_gate_passed)
    integrity_names = tuple(name for name in REQUIRED_GATES if name != "resource_caps")
    if not all(gates[name] for name in integrity_names):
        classification = INTEGRITY_FAILURE_CLASSIFICATION
    elif not gates["resource_caps"]:
        classification = RESOURCE_EXCEEDED_CLASSIFICATION
    else:
        classification = MEASUREMENT_CLASSIFICATION
    return {
        "mm005_document_chart_pdf_model_evaluation_repeatability_evidence_version": (
            EVIDENCE_VERSION
        ),
        "gate_id": EXECUTION_GATE_ID,
        "experiment_id": EXPERIMENT_ID,
        "run_id": RUN_ID,
        "captured_at_utc": captured_at_utc,
        "protocol_freeze_commit": protocol_freeze_commit,
        "classification": classification,
        "artifacts": {
            "preregistration": _receipt(PREREGISTRATION_PATH, preregistration_payload),
            "attempt_owner": _receipt(ATTEMPT_OWNER_PATH, attempt_owner_payload),
            "evaluation_candidate": _receipt(
                EVALUATION_CANDIDATE_PATH, evaluation_candidate_payload
            ),
            "predictions": _receipt(PREDICTIONS_PATH, predictions_payload),
        },
        "baseline": {
            "protocol_freeze_commit": BASELINE_PROTOCOL_FREEZE_COMMIT,
            "result_merge_commit": BASELINE_RESULT_MERGE_COMMIT,
            "artifacts": copy.deepcopy(BASELINE_ARTIFACTS),
            "result_review": copy.deepcopy(BASELINE_REVIEW_RECEIPT),
        },
        "producer": copy.deepcopy(checked_candidate["producer"]),
        "execution": copy.deepcopy(checked_candidate["execution"]),
        "comparison": comparison,
        "replay_metrics": copy.deepcopy(comparison["metrics"]["replay"]),
        "resources": copy.deepcopy(dict(resources)),
        "gates": gates,
        "formal_gate_passed": formal_gate_passed,
        "claims": claims,
        "limitations": {
            "result_review_required_before_repeatability_claim": True,
            "training_repeatability_unestablished": True,
            "resource_repeatability_unestablished": True,
            "cross_machine_reproducibility_unestablished": True,
            "generalized_quality_unestablished": True,
            "safety_unestablished": True,
            "serving_promotion_runtime_eligibility_unestablished": True,
        },
        "next_gate": (
            RESULT_REVIEW_GATE_ID
            if formal_gate_passed
            else FAILURE_CLASSIFICATION_GATE_ID
        ),
        "runtime_eligible": False,
    }


def execution_claims(*, formal_gate_passed: bool) -> dict[str, bool]:
    claims = copy.deepcopy(FREEZE_CLAIMS)
    claims.update(
        {
            "replay_attempt_consumed": True,
            "replay_executed": True,
            "replay_model_evaluated": True,
            "formal_measurement_complete": formal_gate_passed,
        }
    )
    return claims


def build_failure(
    *,
    protocol_freeze_commit: str,
    preregistration_payload: bytes,
    attempt_owner_payload: bytes,
    stage: str,
    exception_type: str,
    counters: Mapping[str, Any],
    completed_record_ids: Sequence[str],
    records: Sequence[Mapping[str, Any]],
    image_payloads: Mapping[str, bytes],
    evaluation_candidate_payload: bytes | None,
    predictions_payload: bytes | None,
) -> dict[str, Any]:
    if stage not in FAILURE_STAGES:
        _fail("FAILURE_STAGE_INVALID")
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]{0,127}", exception_type) is None:
        _fail("FAILURE_EXCEPTION_TYPE_INVALID")
    owner = _parse_canonical(attempt_owner_payload, "attempt_owner")
    validate_attempt_owner(
        owner,
        protocol_freeze_commit=protocol_freeze_commit,
        preregistration_payload=preregistration_payload,
    )
    expected_order = _case_order_from_preregistration(preregistration_payload)
    completed = list(completed_record_ids)
    if completed != expected_order[: len(completed)]:
        _fail("FAILURE_COMPLETED_PREFIX_MISMATCH")
    _validate_partial_counters(counters)
    _validate_failure_progress(counters, completed_count=len(completed), stage=stage)
    candidate: dict[str, Any] | None = None
    if evaluation_candidate_payload is not None:
        parsed_candidate = _parse_canonical(
            evaluation_candidate_payload, "failure_candidate"
        )
        candidate = validate_evaluation_candidate(
            parsed_candidate,
            protocol_freeze_commit=protocol_freeze_commit,
            preregistration_payload=preregistration_payload,
            attempt_owner_payload=attempt_owner_payload,
            records=records,
            image_payloads=image_payloads,
        )
    if predictions_payload is not None:
        if candidate is None:
            _fail("FAILURE_PREDICTIONS_WITHOUT_CANDIDATE")
        parsed_predictions = _parse_canonical(
            predictions_payload, "failure_predictions"
        )
        if not _json_exact(parsed_predictions, build_predictions(candidate)):
            _fail("FAILURE_PREDICTIONS_BINDING_MISMATCH")
    candidate_required = stage in {
        "scoring",
        "predictions_persistence",
        "evidence_persistence",
    }
    predictions_required = stage == "evidence_persistence"
    artifacts_forbidden = stage in {
        "output_claim",
        "dependency_and_environment_validation",
        "model_load_and_generation",
    }
    if candidate_required and candidate is None:
        _fail("FAILURE_CANDIDATE_REQUIRED")
    if predictions_required and predictions_payload is None:
        _fail("FAILURE_PREDICTIONS_REQUIRED")
    if (
        stage in {"candidate_persistence", "scoring"}
        and predictions_payload is not None
    ):
        _fail("FAILURE_PREDICTIONS_FORBIDDEN")
    if artifacts_forbidden and (
        evaluation_candidate_payload is not None or predictions_payload is not None
    ):
        _fail("FAILURE_ARTIFACTS_FORBIDDEN")
    return {
        "mm005_document_chart_pdf_model_evaluation_repeatability_failure_version": (
            FAILURE_VERSION
        ),
        "gate_id": EXECUTION_GATE_ID,
        "experiment_id": EXPERIMENT_ID,
        "run_id": RUN_ID,
        "protocol_freeze_commit": protocol_freeze_commit,
        "classification": "consumed_same_machine_fixed_suite_replay_incomplete",
        "stage": stage,
        "exception_type": exception_type,
        "artifacts": {
            "preregistration": _receipt(PREREGISTRATION_PATH, preregistration_payload),
            "attempt_owner": _receipt(ATTEMPT_OWNER_PATH, attempt_owner_payload),
            "evaluation_candidate": _optional_receipt(
                EVALUATION_CANDIDATE_PATH, evaluation_candidate_payload
            ),
            "predictions": _optional_receipt(PREDICTIONS_PATH, predictions_payload),
        },
        "execution": copy.deepcopy(dict(counters)),
        "completed_record_ids": completed,
        "claims": {
            **execution_claims(formal_gate_passed=False),
            "replay_executed": False,
            "replay_model_evaluated": False,
        },
        "diagnostic_policy": {
            "exception_message_recorded": False,
            "traceback_recorded": False,
            "absolute_paths_recorded": False,
            "secrets_recorded": False,
        },
        "next_gate": FAILURE_CLASSIFICATION_GATE_ID,
        "runtime_eligible": False,
    }


def _layer_result(
    reference_cases: Sequence[Mapping[str, Any]],
    replay_cases: Sequence[Mapping[str, Any]],
    field: str,
    mismatches: Sequence[str],
) -> dict[str, Any]:
    return {
        "exact": not mismatches,
        "exact_count": EXPECTED_RECORDS - len(mismatches),
        "total": EXPECTED_RECORDS,
        "mismatch_record_ids": list(mismatches),
        "reference_sha256": _case_layer_digest(reference_cases, field),
        "replay_sha256": _case_layer_digest(replay_cases, field),
    }


def _case_layer_digest(cases: Sequence[Mapping[str, Any]], field: str) -> str:
    return sha256_bytes(
        artifact_json_bytes(
            [
                {"record_id": str(item["record_id"]), field: copy.deepcopy(item[field])}
                for item in cases
            ]
        )
    )


def _resource_diagnostics(
    reference: Mapping[str, Any], replay: Mapping[str, Any]
) -> dict[str, Any]:
    checked_reference = _validated_resources(reference)
    checked_replay = _validated_resources(replay)
    return {
        "reference": checked_reference,
        "replay": checked_replay,
        "absolute_delta": {
            key: checked_replay[key] - checked_reference[key] for key in RESOURCE_CAPS
        },
        "exact": all(
            checked_reference[key] == checked_replay[key] for key in RESOURCE_CAPS
        ),
        "diagnostic_only": True,
        "resource_repeatability_established": False,
    }


def _validated_resources(value: Mapping[str, Any]) -> dict[str, float | int]:
    if set(value) != set(RESOURCE_CAPS):
        _fail("RESOURCE_FIELD_SET_MISMATCH")
    result: dict[str, float | int] = {}
    for key in RESOURCE_CAPS:
        item = _strict_number(value.get(key), f"$.resources.{key}")
        if item < 0:
            _fail("RESOURCE_VALUE_INVALID")
        result[key] = item
    return result


def _claims_fail_closed(claims: Mapping[str, Any], *, formal_gate_passed: bool) -> bool:
    expected = execution_claims(formal_gate_passed=formal_gate_passed)
    return _json_exact(claims, expected) and all(
        claims[name] is False
        for name in (
            "same_machine_fixed_suite_repeatability_established",
            "training_repeatability_established",
            "resource_repeatability_established",
            "cross_machine_reproducibility_established",
            "quality_improved",
            "generalized_quality_established",
            "safety_established",
            "serving_eligible",
            "promotion_eligible",
            "runtime_eligible",
        )
    )


def _validate_partial_counters(value: Mapping[str, Any]) -> None:
    expected = expected_execution_counters()
    if set(value) != set(expected):
        _fail("PARTIAL_COUNTER_FIELD_SET_MISMATCH")
    for key, maximum in expected.items():
        observed = value[key]
        if type(observed) is not int or observed < 0 or observed > maximum:
            _fail("PARTIAL_COUNTER_VALUE_INVALID")


def _validate_failure_progress(
    value: Mapping[str, Any], *, completed_count: int, stage: str
) -> None:
    generate_attempts = _strict_int(
        value.get("generate_attempts"), "$.failure.execution.generate_attempts"
    )
    generate_calls = _strict_int(
        value.get("generate_calls"), "$.failure.execution.generate_calls"
    )
    if not (
        completed_count <= generate_calls <= completed_count + 1
        and generate_calls <= generate_attempts <= completed_count + 1
    ):
        _fail("FAILURE_GENERATION_PROGRESS_MISMATCH")
    if not (
        _strict_int(
            value.get("fresh_base_loads"), "$.failure.execution.fresh_base_loads"
        )
        <= _strict_int(
            value.get("fresh_base_load_attempts"),
            "$.failure.execution.fresh_base_load_attempts",
        )
        <= 1
    ):
        _fail("FAILURE_BASE_LOAD_PROGRESS_MISMATCH")
    if not (
        _strict_int(
            value.get("independent_adapter_loads"),
            "$.failure.execution.independent_adapter_loads",
        )
        <= _strict_int(
            value.get("independent_adapter_load_attempts"),
            "$.failure.execution.independent_adapter_load_attempts",
        )
        <= _strict_int(
            value.get("fresh_base_loads"), "$.failure.execution.fresh_base_loads"
        )
    ):
        _fail("FAILURE_ADAPTER_LOAD_PROGRESS_MISMATCH")
    if generate_attempts and value.get("independent_adapter_loads") != 1:
        _fail("FAILURE_GENERATION_WITHOUT_ADAPTER")
    if stage in {
        "candidate_persistence",
        "scoring",
        "predictions_persistence",
        "evidence_persistence",
    } and not _json_exact(value, expected_execution_counters()):
        _fail("FAILURE_TERMINAL_COUNTERS_MISMATCH")


def _case_order_from_preregistration(payload: bytes) -> list[str]:
    value = _parse_canonical(payload, "preregistration")
    suite = _mapping(value.get("input_suite"), "$.input_suite")
    return _string_sequence(suite.get("case_order"), "$.input_suite.case_order")


def _parse_canonical(payload: bytes, label: str) -> dict[str, Any]:
    try:
        value = parse_strict_json_bytes(payload, location=f"$.{label}")
    except baseline.MM005ModelEvaluationError as exc:
        raise MM005EvaluationRepeatabilityError(str(exc)) from exc
    if artifact_json_bytes(value) != payload:
        _fail(f"{label.upper()}_NONCANONICAL")
    return value


def _closed_receipts(
    value: Mapping[str, Mapping[str, Any]], location: str
) -> dict[str, dict[str, Any]]:
    if set(value) != set(PROTOCOL_SOURCE_PATHS):
        _fail("SOURCE_RECEIPT_SET_MISMATCH")
    result: dict[str, dict[str, Any]] = {}
    for name, relative in sorted(PROTOCOL_SOURCE_PATHS.items()):
        receipt = _mapping(value.get(name), f"{location}.{name}")
        if (
            set(receipt) != {"path", "bytes", "sha256"}
            or receipt.get("path") != relative
            or type(receipt.get("bytes")) is not int
            or cast(int, receipt["bytes"]) <= 0
            or not isinstance(receipt.get("sha256"), str)
            or _SHA256.fullmatch(cast(str, receipt["sha256"])) is None
        ):
            _fail("SOURCE_RECEIPT_INVALID")
        result[name] = copy.deepcopy(dict(receipt))
    return result


def _check_receipt(
    payload: bytes, receipt: Mapping[str, int | str], label: str
) -> None:
    if len(payload) != int(receipt["bytes"]) or sha256_bytes(payload) != str(
        receipt["sha256"]
    ):
        _fail(f"{label}_RECEIPT_MISMATCH")


def _receipt(path: str, payload: bytes) -> dict[str, Any]:
    return {"path": path, "bytes": len(payload), "sha256": sha256_bytes(payload)}


def _optional_receipt(path: str, payload: bytes | None) -> dict[str, Any] | None:
    return None if payload is None else _receipt(path, payload)


def _layer_exact(left: object, right: object, *, raw: bool) -> bool:
    if raw:
        return (
            isinstance(left, str)
            and isinstance(right, str)
            and (left.encode("utf-8") == right.encode("utf-8"))
        )
    return _json_exact(left, right)


def _json_exact(left: object, right: object) -> bool:
    try:
        return artifact_json_bytes(left) == artifact_json_bytes(right)
    except (TypeError, ValueError):
        return False


def _mapping(value: object, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail(f"EXPECTED_OBJECT_AT_{location}")
    return cast(Mapping[str, Any], value)


def _object_sequence(value: object, location: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        _fail(f"EXPECTED_ARRAY_AT_{location}")
    if not all(isinstance(item, Mapping) for item in value):
        _fail(f"EXPECTED_OBJECT_ITEMS_AT_{location}")
    return cast(list[Mapping[str, Any]], list(value))


def _string_sequence(value: object, location: str) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        _fail(f"EXPECTED_STRING_ARRAY_AT_{location}")
    if not all(isinstance(item, str) for item in value):
        _fail(f"EXPECTED_STRING_ITEMS_AT_{location}")
    return list(cast(Sequence[str], value))


def _bytes_mapping(value: object, location: str) -> Mapping[str, bytes]:
    mapping = _mapping(value, location)
    if not all(
        isinstance(key, str) and isinstance(item, bytes)
        for key, item in mapping.items()
    ):
        _fail(f"EXPECTED_BYTE_MAPPING_AT_{location}")
    return cast(Mapping[str, bytes], mapping)


def _strict_string(value: object, location: str) -> str:
    if type(value) is not str:
        _fail(f"EXPECTED_STRING_AT_{location}")
    return value


def _strict_int(value: object, location: str) -> int:
    if type(value) is not int:
        _fail(f"EXPECTED_INTEGER_AT_{location}")
    return value


def _strict_number(value: object, location: str) -> float | int:
    if type(value) not in {int, float}:
        _fail(f"EXPECTED_NUMBER_AT_{location}")
    observed = cast(float | int, value)
    if isinstance(observed, float) and not (-float("inf") < observed < float("inf")):
        _fail(f"EXPECTED_FINITE_NUMBER_AT_{location}")
    return observed


def _validate_commit(value: str) -> None:
    if _COMMIT.fullmatch(value) is None:
        _fail("COMMIT_INVALID")


def _validate_timestamp(value: str) -> None:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise MM005EvaluationRepeatabilityError("TIMESTAMP_INVALID") from exc
    if parsed.tzinfo is None:
        _fail("TIMESTAMP_TIMEZONE_MISSING")


def _fail(code: str) -> NoReturn:
    raise MM005EvaluationRepeatabilityError(code)
