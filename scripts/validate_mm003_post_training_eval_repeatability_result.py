"""Recompute the frozen MM-003 eval-repeatability result without model imports."""

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

from fullcycle_bridge import gui_grounding_eval_v2 as scorer  # noqa: E402
from fullcycle_bridge import (  # noqa: E402
    mm003_post_training_eval_repeatability as contract,
)
from scripts import (  # noqa: E402
    run_mm003_post_training_eval_repeatability as formal_runner,
)
from scripts import validate_mm003_post_training_v2_result as upstream_validator  # noqa: E402

PROTOCOL_FREEZE_COMMIT = "c72b3bd1666ed6b03d9425e1dbaacfe115dda4f8"
PREREGISTRATION_RECEIPT = {
    "path": contract.PREREGISTRATION_PATH,
    "bytes": 22_951,
    "sha256": "sha256:723db665f98e53ef2fe968ee7c6fe663b42d79b86176eef5cf70f11ccc4a312b",
}
REVIEW_GATE_ID = contract.RESULT_REVIEW_GATE_ID
NEXT_GATE_ID = "MM-004-multimodal-hard-negative-data-protocol-v1"
CLASSIFICATION = (
    "same_machine_fixed_eval_raw_compiled_metrics_and_generated_token_counts_exact"
)

_ARTIFACT_PREFIX = (
    "baseline/mm003-qwen2.5-vl-3b-qlora-sft-v2-"
    "eval-repeatability-v1-"
)
ARTIFACTS: dict[str, dict[str, int | str]] = {
    "attempt_owner": {
        "path": f"{_ARTIFACT_PREFIX}attempt-owner.json",
        "bytes": 586,
        "sha256": "sha256:8f6c267ab262021ac6b8805606b9a7e7bb071507968e5d94a0c4b25eadb3d7fb",
    },
    "evaluation_candidate": {
        "path": f"{_ARTIFACT_PREFIX}evaluation-candidate.json",
        "bytes": 9_855,
        "sha256": "sha256:a354f4b3f2b20467ed7d82916345f7b951ca6df1ad9ecc5816734410694e155b",
    },
    "predictions": {
        "path": f"{_ARTIFACT_PREFIX}predictions.json",
        "bytes": 2_241,
        "sha256": "sha256:c2c703e5896fe64df9e156bda9d38975b92c1bf18c72f74f5a232dcbbbc4a028",
    },
    "evidence": {
        "path": f"{_ARTIFACT_PREFIX}evidence.json",
        "bytes": 20_243,
        "sha256": "sha256:e20262debfbefa3e361855728aa8852f1219053d6fb9152158a2916c806a7ad2",
    },
}
REVIEW_PATH = f"{_ARTIFACT_PREFIX}result-review.json"
REVIEW_BYTES = 15_119
REVIEW_SHA256 = (
    "sha256:8979693b6962849555e533332331d91dbb9fad8294f7fbc6703fa09ab3414f4a"
)

ENVIRONMENT_RECOVERY = {
    "evidence_class": "reviewer_observed_untracked_context",
    "independently_recomputable_from_tracked_receipts": False,
    "required_before_execution": True,
    "registered_environment_fields_exact": True,
    "formal_environment_gate_passed": True,
    "formal_launcher": {
        "path": contract.FORMAL_PYTHON_PATH,
        "python_version": "3.12.12",
        "bytes": 274_248,
        "sha256": "sha256:e39ec6e8b80e547ba1b83f7e825122304c106448425207d8496e464757c20c20",
    },
    "original_base": {
        "vendor": "Anaconda",
        "available_when_recovery_began": False,
        "binary_identity_recovered": False,
    },
    "restored_base": {
        "vendor": "Astral python-build-standalone via uv",
        "available_at_formal_execution": True,
        "build": (
            "cpython-3.12.12+20260211-x86_64-pc-windows-msvc-"
            "install_only_stripped"
        ),
        "python_executable_sha256": (
            "sha256:5b9d341b502c252e262a23033b53002fcaa9bc9c952186f1a566bcde0d894881"
        ),
        "python_dll_sha256": (
            "sha256:e3d09dc4129ab93f57bf9a30d7e16cdcb87e73cd27fbbc9377dd58275640e7e8"
        ),
        "uv_executable_sha256": (
            "sha256:8da6cedef60c27ac997ebf400fbfc6d373c5b0a7ae6a299b9d52be7fe63723fb"
        ),
        "uv_manifest_archive_sha256": (
            "sha256:3bf8e8c05ede0077b197a29c99ebdaf253497f27190097494265150b4e70ba8"
        ),
    },
    "torch_wheel": {
        "filename": "torch-2.6.0+cu124-cp312-cp312-win_amd64.whl",
        "sha256": "sha256:3313061c1fec4c7310cf47944e84513dcd27b6173b72a349bb7ca68d0ee6e9c0",
    },
    "local_install_reports": {
        "torch": {
            "path": (
                "work/environment-recovery/mm003-eval-repeatability-v1/"
                "torch-install-report.json"
            ),
            "bytes": 95_029,
            "sha256": (
                "sha256:8cd316e1c1d1e2f811a4f908a6a8428ff1077b622da8bc8bcdda995fb235727c"
            ),
            "tracked": False,
        },
        "non_torch": {
            "path": (
                "work/environment-recovery/mm003-eval-repeatability-v1/"
                "non-torch-install-report.json"
            ),
            "bytes": 356_539,
            "sha256": (
                "sha256:91520fffa8a6db8cbfff8e8b2928728e51e76b34e346e7d7dc7b323f9d2b0e76"
            ),
            "tracked": False,
        },
    },
    "dependency_lock": {
        "path": "requirements/mm003_qlora_training.lock",
        "direct_entries": 10,
        "direct_versions_exact": True,
        "hash_locked": False,
        "complete_transitive_closure": False,
        "transitive_dependency_hashes_pinned": False,
    },
    "observed_unlocked_transitive_versions": {
        "certifi": "2026.7.22",
        "charset-normalizer": "3.5.1",
        "colorama": "0.4.6",
        "filelock": "3.32.3",
        "fsspec": "2026.7.0",
        "idna": "3.19",
        "jinja2": "3.1.6",
        "markupsafe": "3.0.3",
        "mpmath": "1.3.0",
        "networkx": "3.6.1",
        "numpy": "2.5.2",
        "packaging": "26.3",
        "psutil": "7.2.2",
        "pyyaml": "6.0.3",
        "requests": "2.34.2",
        "setuptools": "78.1.0",
        "sympy": "1.13.1",
        "typing-extensions": "4.16.0",
        "urllib3": "2.7.0",
    },
    "byte_identical_original_base_established": False,
    "hermetic_environment_established": False,
}


class MM003EvalRepeatabilityResultError(ValueError):
    """Raised when the frozen execution or independent review fails closed."""


def validate_repository(root: Path = ROOT) -> dict[str, Any]:
    expected_review, summary = build_repository_review(root)
    try:
        review_payload = upstream_validator._read_exact(
            root,
            root / REVIEW_PATH,
            expected_bytes=REVIEW_BYTES,
            expected_sha256=REVIEW_SHA256,
            label="eval-repeatability result review",
        )
    except upstream_validator.MM003PostTrainingV2ResultError as exc:
        raise MM003EvalRepeatabilityResultError(str(exc)) from exc
    review = _canonical_object(review_payload, "result review")
    if review != expected_review:
        _fail("RESULT_REVIEW_RECOMPUTATION_MISMATCH")
    return summary


def build_repository_review(root: Path = ROOT) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        upstream_validator._require_canonical_repository_root(root)
        context = formal_runner.load_authenticated_context()
        source_hashes = formal_runner.protocol_source_hashes()
        preregistration_payload = upstream_validator._read_exact(
            root,
            root / str(PREREGISTRATION_RECEIPT["path"]),
            expected_bytes=int(PREREGISTRATION_RECEIPT["bytes"]),
            expected_sha256=str(PREREGISTRATION_RECEIPT["sha256"]),
            label="eval-repeatability preregistration",
        )
        payloads = {
            name: upstream_validator._read_exact(
                root,
                root / str(receipt["path"]),
                expected_bytes=int(receipt["bytes"]),
                expected_sha256=str(receipt["sha256"]),
                label=f"eval-repeatability {name}",
            )
            for name, receipt in ARTIFACTS.items()
        }
    except upstream_validator.MM003PostTrainingV2ResultError as exc:
        raise MM003EvalRepeatabilityResultError(str(exc)) from exc
    failure_path, failure_parents = upstream_validator._safe_repository_parent_chain(
        root,
        root
        / (
            "baseline/mm003-qwen2.5-vl-3b-qlora-sft-v2-"
            "eval-repeatability-v1-failure.json"
        ),
        "eval-repeatability success failure artifact",
    )
    if os.path.lexists(failure_path):
        _fail("SUCCESS_FAILURE_ARTIFACT_PRESENT")
    upstream_validator._recheck_repository_parent_chain(
        failure_parents, "eval-repeatability success failure artifact"
    )
    return validate_execution_payloads(
        preregistration_payload=preregistration_payload,
        payloads=payloads,
        context=context,
        source_hashes=source_hashes,
    )


def validate_execution_payloads(
    *,
    preregistration_payload: bytes,
    payloads: Mapping[str, bytes],
    context: Mapping[str, Any],
    source_hashes: Mapping[str, str],
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

    expected_evidence, candidate, evidence = recompute_evidence(
        preregistration_payload=preregistration_payload,
        payloads=payloads,
        context=context,
        source_hashes=source_hashes,
    )
    if contract.artifact_json_bytes(expected_evidence) != payloads["evidence"]:
        _fail("EXECUTION_EVIDENCE_RECOMPUTATION_MISMATCH")
    if payloads["predictions"] != contract.artifact_json_bytes(
        _mapping(context["reference_predictions"], "$.reference_predictions")
    ):
        _fail("REPLAY_PREDICTIONS_DIFFER_FROM_REFERENCE_BYTES")

    review = build_review(evidence=evidence, candidate=candidate)
    summary = {
        "formal_gate_passed": True,
        "classification": CLASSIFICATION,
        "all_layers_exact": True,
        "raw_outputs_exact": contract.EXPECTED_CASES,
        "generated_token_counts_exact": contract.EXPECTED_CASES,
        "compiled_predictions_exact": contract.EXPECTED_CASES,
        "compiler_fallback_status_exact": True,
        "metrics_exact": True,
        "same_machine_eval_repeatability_established": True,
        "training_repeatability_established": False,
        "next_gate": NEXT_GATE_ID,
        "runtime_eligible": False,
    }
    return review, summary


def recompute_evidence(
    *,
    preregistration_payload: bytes,
    payloads: Mapping[str, bytes],
    context: Mapping[str, Any],
    source_hashes: Mapping[str, str],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    preregistration_raw = _canonical_object(
        preregistration_payload, "preregistration"
    )
    candidate = _canonical_object(payloads["evaluation_candidate"], "candidate")
    evidence = _canonical_object(payloads["evidence"], "evidence")
    _canonical_object(payloads["attempt_owner"], "attempt owner")
    predictions = _canonical_object(payloads["predictions"], "predictions")

    try:
        preregistration = contract.validate_preregistration(
            preregistration_raw,
            source_hashes=source_hashes,
            upstream_preregistration=_mapping(
                context["upstream_preregistration"], "$.upstream_preregistration"
            ),
            reference_evidence=_mapping(
                context["reference_evidence"], "$.reference_evidence"
            ),
            reference_predictions=_mapping(
                context["reference_predictions"], "$.reference_predictions"
            ),
            result_review=_mapping(context["result_review"], "$.result_review"),
            suite=_mapping(context["suite"], "$.suite"),
        )
        replay_evaluation = {
            "execution": copy.deepcopy(candidate["execution"]),
            "cases": copy.deepcopy(candidate["cases"]),
            "predictions": copy.deepcopy(candidate["predictions"]),
            "score": scorer.score_predictions(
                _mapping(context["suite"], "$.suite"), predictions
            ),
        }
        contract.validate_completed_evaluation(
            replay_evaluation,
            suite=_mapping(context["suite"], "$.suite"),
            screenshot_receipts=_sequence(
                context["screenshot_receipts"], "$.screenshot_receipts"
            ),
        )
        expected = contract.build_evidence(
            preregistration_payload=preregistration_payload,
            attempt_owner_payload=payloads["attempt_owner"],
            evaluation_candidate_payload=payloads["evaluation_candidate"],
            predictions_payload=payloads["predictions"],
            protocol_freeze_commit=PROTOCOL_FREEZE_COMMIT,
            reference_evaluation=_mapping(
                _mapping(context["reference_evidence"], "$.reference_evidence")[
                    "evaluation"
                ],
                "$.reference_evidence.evaluation",
            ),
            replay_evaluation=replay_evaluation,
            preregistration=preregistration,
            suite=_mapping(context["suite"], "$.suite"),
            screenshot_receipts=_sequence(
                context["screenshot_receipts"], "$.screenshot_receipts"
            ),
            environment=_mapping(
                preregistration["environment"], "$.preregistration.environment"
            ),
            model_files=_sequence(
                _mapping(preregistration["model"], "$.preregistration.model")[
                    "files"
                ],
                "$.preregistration.model.files",
            ),
            adapter_receipts=contract.ADAPTER_RECEIPTS,
            resources=_mapping(evidence["resources"], "$.evidence.resources"),
            captured_at_utc=str(evidence["captured_at_utc"]),
        )
    except contract.MM003EvalRepeatabilityError as exc:
        raise MM003EvalRepeatabilityResultError(str(exc)) from exc
    return expected, candidate, evidence


def build_review(
    *, evidence: Mapping[str, Any], candidate: Mapping[str, Any]
) -> dict[str, Any]:
    gates = _mapping(evidence["gates"], "$.evidence.gates")
    comparison = _mapping(evidence["comparison"], "$.evidence.comparison")
    raw = _mapping(comparison["raw_outputs"], "$.comparison.raw_outputs")
    compiled = _mapping(
        comparison["compiled_predictions"], "$.comparison.compiled_predictions"
    )
    metrics = _mapping(comparison["metrics"], "$.comparison.metrics")
    expected_gates = {name: True for name in contract.REQUIRED_GATES}
    if (
        evidence.get("formal_gate_passed") is not True
        or evidence.get("classification") != contract.MEASUREMENT_CLASSIFICATION
        or evidence.get("next_gate") != REVIEW_GATE_ID
        or dict(gates) != expected_gates
        or comparison.get("all_layers_exact") is not True
        or comparison.get("raw_drift_compiled_and_metrics_exact") is not False
        or comparison.get("compiled_drift_metrics_exact") is not False
        or comparison.get("metric_drift") is not False
        or raw.get("exact") != contract.EXPECTED_CASES
        or raw.get("total") != contract.EXPECTED_CASES
        or raw.get("mismatch_case_ids") != []
        or raw.get("generated_tokens_exact") != contract.EXPECTED_CASES
        or raw.get("generated_token_mismatch_case_ids") != []
        or compiled.get("exact") != contract.EXPECTED_CASES
        or compiled.get("total") != contract.EXPECTED_CASES
        or compiled.get("mismatch_case_ids") != []
        or compiled.get("compiler_fallback_mismatch_case_ids") != []
        or metrics.get("exact") is not True
        or metrics.get("mismatch_metric_names") != []
        or evidence.get("claims")
        != contract.execution_claims(formal_gate_passed=True)
        or evidence.get("runtime_eligible") is not False
    ):
        _fail("NARROW_REPEATABILITY_REVIEW_PRECONDITION_MISMATCH")

    cases = _sequence(candidate["cases"], "$.candidate.cases")
    latencies = [float(item["latency_seconds"]) for item in cases]
    score = _mapping(
        _mapping(evidence["evaluation"], "$.evidence.evaluation")["score"],
        "$.evidence.evaluation.score",
    )
    return {
        "review_version": 1,
        "gate_id": REVIEW_GATE_ID,
        "reviewed_execution_gate_id": contract.EXECUTION_GATE_ID,
        "classification": CLASSIFICATION,
        "scope": "same_machine_registered_environment_fixed_nine_case_eval",
        "protocol": {
            "freeze_commit": PROTOCOL_FREEZE_COMMIT,
            "preregistration": copy.deepcopy(PREREGISTRATION_RECEIPT),
        },
        "frozen_artifacts": {
            name: copy.deepcopy(receipt) for name, receipt in ARTIFACTS.items()
        },
        "review_process": {
            "model_reloaded": False,
            "cuda_used": False,
            "scorer_recomputed": True,
            "candidate_binding_recomputed": True,
            "evidence_rebuilt_from_frozen_inputs": True,
            "historical_timestamp_and_resources_reused_from_runner_evidence": True,
            "historical_timestamp_and_resources_independently_remeasured": False,
        },
        "formal_measurement": {
            "required_gates": list(contract.REQUIRED_GATES),
            "passed_gates": list(contract.REQUIRED_GATES),
            "formal_gate_passed": True,
            "quality_threshold_registered": False,
        },
        "comparison": copy.deepcopy(dict(comparison)),
        "comparison_semantics": {
            "all_layers_exact_definition": [
                "raw_utf8_output",
                "canonical_compiled_prediction",
                "canonical_metrics",
            ],
            "transformer_internal_layers_compared": False,
            "generated_token_counts_exact": True,
            "compiler_fallback_status_exact": True,
            "generated_token_id_sequences_persisted": False,
            "generated_token_sequence_exact_claimed": False,
        },
        "execution": copy.deepcopy(
            _mapping(evidence["execution"], "$.evidence.execution")
        ),
        "evaluation": {
            "suite_id": score["suite_id"],
            "case_count": contract.EXPECTED_CASES,
            "case_order": list(contract.CASE_ORDER),
            "compiler_fallback_count": sum(
                1 for item in cases if item["compiler_fallback"] is True
            ),
            "metrics": copy.deepcopy(_mapping(score["metrics"], "$.score.metrics")),
            "case_latency_seconds": [
                {
                    "case_id": item["case_id"],
                    "latency_seconds": item["latency_seconds"],
                }
                for item in cases
            ],
            "latency_summary_seconds": {
                "sum": sum(latencies),
                "mean": sum(latencies) / len(latencies),
                "minimum": min(latencies),
                "maximum": max(latencies),
            },
        },
        "resources": copy.deepcopy(
            _mapping(evidence["resources"], "$.evidence.resources")
        ),
        "environment_recovery": copy.deepcopy(ENVIRONMENT_RECOVERY),
        "scope_semantics": {
            "same_machine_definition": (
                "same_windows_host_and_registered_environment_fields"
            ),
            "machine_id_attested": False,
            "hardware_identity_attested": False,
        },
        "claims": {
            name: name
            in {
                "replay_executed",
                "model_evaluated",
                "formal_measurement_complete",
                "same_machine_eval_repeatability_established",
            }
            for name in contract.CLAIM_KEYS
        },
        "limitations": {
            "single_reference_and_single_replay": True,
            "same_machine_only": True,
            "fixed_synthetic_nine_case_eval_only": True,
            "original_python_base_vendor_reproduced": False,
            "original_python_base_binary_identity_reproduced": False,
            "complete_transitive_dependency_lock": False,
            "training_repeatability_tested": False,
            "resource_repeatability_tested": False,
            "full_eval_repeat_variance_established": False,
            "external_execution_count_attested": False,
            "cross_machine_tested": False,
            "real_content_tested": False,
            "direct_execution_tested": False,
            "runtime_integration_tested": False,
        },
        "next_gate": NEXT_GATE_ID,
        "next_action": (
            "freeze a model-free multimodal hard-negative data protocol before "
            "generating, training on, or evaluating new MM-004 negatives"
        ),
        "runtime_eligible": False,
    }


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
    except contract.MM003EvalRepeatabilityError as exc:
        raise MM003EvalRepeatabilityResultError(str(exc)) from exc
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


def _sequence(value: object, location: str) -> Sequence[Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        _fail(f"EXPECTED_ARRAY_AT_{location}")
    items = cast(Sequence[object], value)
    if not all(isinstance(item, Mapping) for item in items):
        _fail(f"EXPECTED_OBJECT_ITEMS_AT_{location}")
    return cast(Sequence[Mapping[str, Any]], items)


def _fail(code: str) -> NoReturn:
    raise MM003EvalRepeatabilityResultError(code)


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
            upstream_validator._write_exclusive(ROOT, ROOT / REVIEW_PATH, payload)
            summary = {
                **summary,
                "review_bytes": len(payload),
                "review_sha256": contract.sha256_bytes(payload),
            }
        else:
            summary = validate_repository(ROOT)
    except (
        MM003EvalRepeatabilityResultError,
        upstream_validator.MM003PostTrainingV2ResultError,
        contract.MM003EvalRepeatabilityError,
    ) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(summary, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
