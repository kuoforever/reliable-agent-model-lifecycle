"""Prepare or execute the frozen MM-003 recovery baseline v2."""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SRC))

from fullcycle_bridge import gui_grounding_eval as base_scorer  # noqa: E402
from fullcycle_bridge import gui_grounding_eval_v2 as scorer  # noqa: E402
from fullcycle_bridge import mm003_baseline_failure_classification  # noqa: E402
from fullcycle_bridge import mm003_baseline_protocol_v2 as contract  # noqa: E402
from scripts import run_mm003_multimodal_gui_action_baseline as base_runner  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("--model-snapshot", type=Path, required=True)
    prepare.add_argument("--suite", type=Path, default=ROOT / contract.MM002_SUITE_PATH)
    prepare.add_argument(
        "--screenshots-dir", type=Path, default=ROOT / contract.SCREENSHOT_ROOT
    )
    prepare.add_argument(
        "--output", type=Path, default=ROOT / contract.PREREGISTRATION_PATH
    )
    prepare.add_argument("--freeze-status", choices=("draft", "frozen"), required=True)
    prepare.add_argument("--check", action="store_true")

    run = subparsers.add_parser("run")
    run.add_argument("--model-snapshot", type=Path, required=True)
    run.add_argument(
        "--preregistration",
        type=Path,
        default=ROOT / contract.PREREGISTRATION_PATH,
    )
    run.add_argument("--protocol-freeze-commit", required=True)
    run.add_argument("--output-dir", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "prepare":
        result = prepare_protocol(
            model_snapshot=args.model_snapshot,
            suite_path=args.suite,
            screenshots_dir=args.screenshots_dir,
            output_path=args.output,
            freeze_status=args.freeze_status,
            check=args.check,
        )
    else:
        result = execute_frozen_baseline(
            model_snapshot=args.model_snapshot,
            preregistration_path=args.preregistration,
            protocol_freeze_commit=args.protocol_freeze_commit,
            output_dir=args.output_dir,
        )
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


def prepare_protocol(
    *,
    model_snapshot: Path,
    suite_path: Path,
    screenshots_dir: Path,
    output_path: Path,
    freeze_status: str,
    check: bool,
) -> dict[str, Any]:
    """Bind unchanged v1 inputs plus the recovery scorer and persistence sources."""

    suite_payload = base_runner._read_regular_file(
        suite_path, "MM-002 suite", 2 * 1024 * 1024
    )
    if contract.sha256_bytes(suite_payload) != contract.MM002_SUITE_FILE_SHA256:
        raise RuntimeError("MM-002 suite file hash mismatch")
    suite = base_scorer.load_suite_file(suite_path.resolve())
    if base_scorer.sha256_json(suite) != contract.MM002_SUITE_CANONICAL_SHA256:
        raise RuntimeError("MM-002 suite canonical hash mismatch")

    screenshot_receipts: list[dict[str, Any]] = []
    cases = {case["case_id"]: case for case in suite["cases"]}
    for case_id in contract.SCREENSHOT_CASES:
        payload = contract.render_case_png(cases[case_id])
        path = screenshots_dir / f"{case_id}.png"
        observed = base_runner._read_regular_file(
            path, f"screenshot {case_id}", 4 * 1024 * 1024
        )
        if observed != payload:
            raise RuntimeError(f"screenshot differs from renderer: {case_id}")
        screenshot_receipts.append(
            {
                "case_id": case_id,
                "path": f"{contract.SCREENSHOT_ROOT}/{case_id}.png",
                "bytes": len(payload),
                "sha256": contract.sha256_bytes(payload),
            }
        )

    _validate_v1_failure_artifact()
    preregistration = contract.expected_preregistration(
        freeze_status=freeze_status,
        model_files=base_runner.model_file_manifest(model_snapshot),
        screenshot_files=screenshot_receipts,
        protocol_source_hashes=protocol_source_hashes(),
    )
    payload = contract.artifact_json_bytes(preregistration)
    if check:
        if (
            base_runner._read_regular_file(
                output_path, "v2 preregistration", 4 * 1024 * 1024
            )
            != payload
        ):
            raise RuntimeError("v2 preregistration differs from recomputation")
    else:
        base_runner._write_exclusive(output_path, payload)
    return {
        "freeze_status": freeze_status,
        "model_files": len(preregistration["model"]["files"]),
        "screenshots": len(screenshot_receipts),
        "source_files": len(contract.PROTOCOL_SOURCE_PATHS),
        "sha256": contract.sha256_bytes(payload),
        "valid": True,
    }


def execute_frozen_baseline(
    *,
    model_snapshot: Path,
    preregistration_path: Path,
    protocol_freeze_commit: str,
    output_dir: Path,
) -> dict[str, Any]:
    """Execute the one registered v2 run with prescore candidate persistence."""

    if not base_runner.re_full_commit(protocol_freeze_commit):
        raise RuntimeError("protocol freeze commit must be a lowercase 40-hex commit")
    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise RuntimeError("output directory must be absent before model load")

    preregistration_payload = base_runner._read_regular_file(
        preregistration_path, "v2 preregistration", 4 * 1024 * 1024
    )
    preregistration_raw = contract.parse_strict_json_bytes(
        preregistration_payload, location="$.preregistration"
    )
    if not isinstance(preregistration_raw, dict):
        raise RuntimeError("v2 preregistration must be an object")
    preregistration = contract.validate_preregistration(preregistration_raw)
    _validate_protocol_sources(preregistration)
    _validate_v1_failure_artifact()
    model_manifest = base_runner.model_file_manifest(model_snapshot)
    if model_manifest != preregistration["model"]["files"]:
        raise RuntimeError("model snapshot differs from frozen v2 manifest")

    suite_path = ROOT / contract.MM002_SUITE_PATH
    suite_payload = base_runner._read_regular_file(
        suite_path, "MM-002 suite", 2 * 1024 * 1024
    )
    suite = base_scorer.load_suite_file(suite_path.resolve())
    if (
        contract.sha256_bytes(suite_payload) != contract.MM002_SUITE_FILE_SHA256
        or base_scorer.sha256_json(suite) != contract.MM002_SUITE_CANONICAL_SHA256
    ):
        raise RuntimeError("MM-002 suite binding mismatch")
    screenshot_manifest = base_runner._validate_screenshots(preregistration, suite)

    base_runner._enable_offline_execution()
    torch, model_class, processor_class, image_class = (
        base_runner._load_ml_dependencies()
    )
    environment = base_runner.observed_environment(torch)
    if environment != contract.LOCKED_ENVIRONMENT:
        raise RuntimeError(f"locked environment mismatch: {environment!r}")
    generation = preregistration["execution_protocol"]["generation"]
    base_runner._seed_all(torch, generation["seed"])
    before_allocated = torch.cuda.memory_allocated()
    before_reserved = torch.cuda.memory_reserved()
    torch.cuda.reset_peak_memory_stats()
    started = time.perf_counter()
    processor = processor_class.from_pretrained(
        model_snapshot,
        local_files_only=True,
        min_pixels=preregistration["execution_protocol"]["image_policy"]["min_pixels"],
        max_pixels=preregistration["execution_protocol"]["image_policy"]["max_pixels"],
        use_fast=preregistration["execution_protocol"]["image_policy"]["use_fast"],
    )
    model = model_class.from_pretrained(
        model_snapshot,
        torch_dtype=torch.bfloat16,
        attn_implementation="sdpa",
        device_map="cuda",
        local_files_only=True,
        low_cpu_mem_usage=True,
    ).eval()

    case_results: list[dict[str, Any]] = []
    prediction_records: list[dict[str, Any]] = []
    for case in suite["cases"]:
        case_id = case["case_id"]
        mode = case["observation_mode"]
        prompt = contract.build_user_prompt(case)
        content: list[dict[str, Any]] = []
        images: list[Any] | None = None
        screenshot_sha256: str | None = None
        if mode != "uia_only":
            screenshot_path = ROOT / contract.SCREENSHOT_ROOT / f"{case_id}.png"
            screenshot_payload = base_runner._read_regular_file(
                screenshot_path, f"screenshot {case_id}", 4 * 1024 * 1024
            )
            screenshot_sha256 = contract.sha256_bytes(screenshot_payload)
            image = image_class.open(screenshot_path).convert("RGB")
            images = [image]
            content.append({"type": "image", "image": image})
        content.append({"type": "text", "text": prompt})
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": contract.SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ]
        torch.cuda.synchronize()
        case_started = time.perf_counter()
        raw_output, generated_tokens = base_runner._generate_one(
            torch=torch,
            model=model,
            processor=processor,
            messages=messages,
            images=images,
            max_new_tokens=generation["max_new_tokens"],
        )
        torch.cuda.synchronize()
        latency = time.perf_counter() - case_started
        compiled = contract.compile_raw_prediction(raw_output, case)
        prediction_records.append(compiled)
        case_results.append(
            {
                "case_id": case_id,
                "observation_mode": mode,
                "prompt_sha256": contract.sha256_bytes(prompt.encode("utf-8")),
                "screenshot_sha256": screenshot_sha256,
                "raw_output": raw_output,
                "raw_output_sha256": contract.sha256_bytes(raw_output.encode("utf-8")),
                "compiled_prediction": compiled,
                "compiler_fallback": compiled["reason"] == "model_output_invalid",
                "candidate_steps": 1,
                "generated_tokens": generated_tokens,
                "latency_seconds": latency,
            }
        )

    elapsed = time.perf_counter() - started
    resources = {
        "elapsed_seconds": elapsed,
        "gpu_allocated_before_bytes": before_allocated,
        "gpu_reserved_before_bytes": before_reserved,
        "gpu_allocated_after_bytes": torch.cuda.memory_allocated(),
        "gpu_reserved_after_bytes": torch.cuda.memory_reserved(),
        "peak_gpu_allocated_bytes": torch.cuda.max_memory_allocated(),
        "peak_gpu_reserved_bytes": torch.cuda.max_memory_reserved(),
    }
    predictions = {
        "gui_grounding_prediction_version": 1,
        "suite_id": suite["suite_id"],
        "producer": {
            "kind": "model",
            "model_id": contract.MODEL_ID,
            "model_revision": contract.MODEL_REVISION,
        },
        "records": prediction_records,
    }
    run_artifact = {
        "run_artifact_version": 2,
        "experiment_id": contract.EXPERIMENT_ID,
        "gate_id": contract.GATE_ID,
        "captured_at_utc": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "protocol": {
            "preregistration_sha256": contract.sha256_bytes(preregistration_payload),
            "freeze_commit": protocol_freeze_commit,
        },
        "model_resolution": {
            "repo_id": contract.MODEL_ID,
            "revision": contract.MODEL_REVISION,
            "files": model_manifest,
        },
        "inputs": {
            "suite_file_sha256": contract.sha256_bytes(suite_payload),
            "suite_canonical_sha256": base_scorer.sha256_json(suite),
            "screenshots": screenshot_manifest,
        },
        "environment": environment,
        "execution": {
            "fresh_model_loads": 1,
            "full_eval_runs": 1,
            "generate_calls": len(case_results),
            "retry_count": 0,
            "network_used": False,
            "generation_completed": len(case_results) == 9,
        },
        "persistence": {
            "stage": "pre_score_candidates",
            "raw_run_written_before_scoring": True,
            "compiled_predictions_written_before_scoring": True,
            "writes_are_exclusive": True,
            "scoring_failure_receipt_required": True,
        },
        "cases": case_results,
        "resources": resources,
        "claims": {
            "candidate_outputs_only": True,
            "baseline_executed": False,
            "model_evaluated": False,
            "direct_execution": False,
            "training_performed": False,
            "real_content_used": False,
            "runtime_eligible": False,
        },
    }
    run_payload = contract.artifact_json_bytes(run_artifact)
    predictions_payload = contract.artifact_json_bytes(predictions)
    output_dir.mkdir(parents=True, exist_ok=False)
    run_path = output_dir / Path(contract.RUN_ARTIFACT_PATH).name
    predictions_path = output_dir / Path(contract.PREDICTIONS_ARTIFACT_PATH).name
    base_runner._write_exclusive(run_path, run_payload)
    base_runner._write_exclusive(predictions_path, predictions_payload)
    artifact_receipts = {
        "run": _receipt(contract.RUN_ARTIFACT_PATH, run_payload),
        "predictions": _receipt(
            contract.PREDICTIONS_ARTIFACT_PATH, predictions_payload
        ),
    }

    score = score_with_failure_persistence(
        output_dir=output_dir,
        suite=suite,
        predictions=predictions,
        protocol_freeze_commit=protocol_freeze_commit,
        preregistration_payload=preregistration_payload,
        run_artifact=run_artifact,
        artifact_receipts=artifact_receipts,
    )

    evidence = build_evidence(
        preregistration=preregistration,
        preregistration_payload=preregistration_payload,
        protocol_freeze_commit=protocol_freeze_commit,
        run_artifact=run_artifact,
        predictions=predictions,
        score=score,
        suite=suite,
        run_payload=run_payload,
        predictions_payload=predictions_payload,
        artifact_receipts=artifact_receipts,
    )
    base_runner._write_exclusive(
        output_dir / Path(contract.EVIDENCE_ARTIFACT_PATH).name,
        contract.artifact_json_bytes(evidence),
    )
    return {
        "classification": evidence["classification"],
        "formal_gate_passed": evidence["formal_gate_passed"],
        "metrics": score["metrics"],
        "output_dir": str(output_dir),
        "runtime_eligible": False,
        "valid": True,
    }


def build_evidence(
    *,
    preregistration: Mapping[str, Any],
    preregistration_payload: bytes,
    protocol_freeze_commit: str,
    run_artifact: Mapping[str, Any],
    predictions: Mapping[str, Any],
    score: Mapping[str, Any],
    suite: Mapping[str, Any],
    run_payload: bytes,
    predictions_payload: bytes,
    artifact_receipts: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    execution = run_artifact["execution"]
    resources = run_artifact["resources"]
    caps = preregistration["resource_caps"]
    records = predictions["records"]
    cases = run_artifact["cases"]
    optional_metric = score["metrics"]["prediction_coordinate_ref_disagreement_rate"]
    gates = {
        "protocol_integrity": (
            contract.validate_preregistration(preregistration) == preregistration
            and contract.sha256_bytes(preregistration_payload)
            == run_artifact["protocol"]["preregistration_sha256"]
            and run_artifact["protocol"]["freeze_commit"] == protocol_freeze_commit
        ),
        "exact_model_files": (
            run_artifact["model_resolution"]
            == {
                "repo_id": preregistration["model"]["repo_id"],
                "revision": preregistration["model"]["revision"],
                "files": preregistration["model"]["files"],
            }
        ),
        "exact_synthetic_inputs": base_runner._exact_synthetic_inputs(
            preregistration=preregistration,
            run_artifact=run_artifact,
            suite=suite,
        ),
        "locked_environment": (
            run_artifact["environment"]
            == preregistration["execution_protocol"]["environment"]
        ),
        "one_complete_nine_case_run": (
            execution["fresh_model_loads"] == 1
            and execution["full_eval_runs"] == 1
            and execution["generate_calls"] == 9
            and execution["generation_completed"] is True
            and [record["case_id"] for record in records] == list(contract.CASE_ORDER)
        ),
        "zero_retries": execution["retry_count"] == 0,
        "offline_execution": execution["network_used"] is False,
        "resource_caps": (
            resources["elapsed_seconds"] <= caps["elapsed_seconds"]
            and resources["peak_gpu_allocated_bytes"]
            <= caps["peak_gpu_allocated_bytes"]
            and resources["peak_gpu_reserved_bytes"] <= caps["peak_gpu_reserved_bytes"]
        ),
        "prediction_schema_validity": (
            score["predictions_sha256"] == base_scorer.sha256_json(predictions)
            and len(records) == 9
        ),
        "prediction_dependent_metric_totality": _optional_metric_is_total(
            optional_metric
        ),
        "prescore_candidate_persistence": (
            run_artifact["persistence"]
            == {
                "stage": "pre_score_candidates",
                "raw_run_written_before_scoring": True,
                "compiled_predictions_written_before_scoring": True,
                "writes_are_exclusive": True,
                "scoring_failure_receipt_required": True,
            }
            and artifact_receipts
            == {
                "run": _receipt(contract.RUN_ARTIFACT_PATH, run_payload),
                "predictions": _receipt(
                    contract.PREDICTIONS_ARTIFACT_PATH, predictions_payload
                ),
            }
        ),
        "scoring_failure_receipt_policy": (
            preregistration["execution_protocol"]["persistence_policy"][
                "scoring_failure_receipt_required"
            ]
            is True
            and preregistration["execution_protocol"]["outputs"]["failure"]
            == contract.FAILURE_ARTIFACT_PATH
        ),
    }
    formal_gate_passed = all(gates.values())
    mode_metrics: dict[str, Any] = {}
    suite_cases = {case["case_id"]: case for case in suite["cases"]}
    for mode in ("uia_only", "screenshot_only", "fused"):
        selected = [item for item in cases if item["observation_mode"] == mode]
        correct = sum(
            base_runner._action_correct(
                suite_cases[item["case_id"]], item["compiled_prediction"]
            )
            for item in selected
        )
        fallback = sum(
            item["compiled_prediction"]["disposition"] == "fallback"
            for item in selected
        )
        mode_metrics[mode] = {
            "cases": len(selected),
            "task_success_proxy": {
                "correct": correct,
                "total": len(selected),
                "value": correct / len(selected),
            },
            "candidate_steps": sum(item["candidate_steps"] for item in selected),
            "fallback_rate": {
                "count": fallback,
                "total": len(selected),
                "value": fallback / len(selected),
            },
            "latency_seconds": {
                "total": sum(item["latency_seconds"] for item in selected),
                "mean": sum(item["latency_seconds"] for item in selected)
                / len(selected),
            },
        }
    return {
        "evidence_version": 2,
        "experiment_id": contract.EXPERIMENT_ID,
        "gate_id": contract.GATE_ID,
        "protocol_freeze_commit": protocol_freeze_commit,
        "preregistration": {
            "bytes": len(preregistration_payload),
            "sha256": contract.sha256_bytes(preregistration_payload),
        },
        "prescore_artifacts": dict(artifact_receipts),
        "gates": gates,
        "formal_gate_passed": formal_gate_passed,
        "classification": (
            "local_small_vlm_baseline_established"
            if formal_gate_passed
            else "local_small_vlm_baseline_incomplete"
        ),
        "quality": {"overall": score["metrics"], "by_observation_mode": mode_metrics},
        "resources": resources,
        "compiler": {
            "fallback_count": sum(item["compiler_fallback"] for item in cases),
            "fallback_rate": sum(item["compiler_fallback"] for item in cases)
            / len(cases),
        },
        "claims": {
            "baseline_executed": formal_gate_passed,
            "model_evaluated": formal_gate_passed,
            "post_training_complete": False,
            "adapter_loadable": False,
            "real_content_collected": False,
            "cross_machine_reproducibility_established": False,
            "portable_package_eligible": False,
            "serving_readiness_established": False,
            "artifact_promotion_allowed": False,
            "runtime_eligible": False,
        },
        "limitations": {
            "synthetic_eval_only": True,
            "single_local_run": True,
            "quality_threshold_registered": False,
            "commercial_use_allowed_by_model_license": False,
            "direct_execution_tested": False,
            "runtime_integration_tested": False,
        },
        "next_gate": (
            "MM-003-small-vlm-post-training-protocol-v1"
            if formal_gate_passed
            else "MM-003-local-small-vlm-baseline-failure-classification-v2"
        ),
        "runtime_eligible": False,
    }


def build_scoring_failure_receipt(
    *,
    protocol_freeze_commit: str,
    preregistration_payload: bytes,
    run_artifact: Mapping[str, Any],
    artifact_receipts: Mapping[str, Mapping[str, Any]],
    exception: Exception,
) -> dict[str, Any]:
    if isinstance(exception, base_scorer.GuiGroundingValidationError):
        code = exception.code
        location = exception.location
        detail = exception.detail
    else:
        code = "UNEXPECTED_SCORING_EXCEPTION"
        location = "$.scoring"
        detail = "unexpected scorer exception; inspect local stderr"
    result: dict[str, Any] = {
        "failure_receipt_version": 2,
        "experiment_id": contract.EXPERIMENT_ID,
        "gate_id": contract.EXECUTION_GATE_ID,
        "captured_at_utc": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "protocol": {
            "freeze_commit": protocol_freeze_commit,
            "preregistration_sha256": contract.sha256_bytes(preregistration_payload),
        },
        "prescore_artifacts": dict(artifact_receipts),
        "execution": dict(run_artifact["execution"]),
        "failure": {
            "stage": "scoring",
            "exception_type": (
                f"{type(exception).__module__}.{type(exception).__qualname__}"
            ),
            "code": code,
            "location": location,
            "detail": detail,
        },
        "formal_gate_passed": False,
        "claims": {
            "baseline_executed": False,
            "model_evaluated": False,
            "artifact_promotion_allowed": False,
            "runtime_eligible": False,
        },
        "next_gate": "MM-003-local-small-vlm-baseline-failure-classification-v2",
        "runtime_eligible": False,
    }
    result["receipt_digest"] = contract.sha256_bytes(
        contract.canonical_json_bytes(result)
    )
    return result


def score_with_failure_persistence(
    *,
    output_dir: Path,
    suite: Mapping[str, Any],
    predictions: Mapping[str, Any],
    protocol_freeze_commit: str,
    preregistration_payload: bytes,
    run_artifact: Mapping[str, Any],
    artifact_receipts: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Score after candidate persistence and durably record scorer failures."""

    try:
        return scorer.score_predictions(suite, predictions)
    except Exception as exc:
        failure = build_scoring_failure_receipt(
            protocol_freeze_commit=protocol_freeze_commit,
            preregistration_payload=preregistration_payload,
            run_artifact=run_artifact,
            artifact_receipts=artifact_receipts,
            exception=exc,
        )
        base_runner._write_exclusive(
            output_dir / Path(contract.FAILURE_ARTIFACT_PATH).name,
            contract.artifact_json_bytes(failure),
        )
        raise RuntimeError(f"v2 scoring failed: {exc}") from exc


def protocol_source_hashes() -> dict[str, str]:
    return {
        name: contract.sha256_bytes(
            base_runner._read_regular_file(
                ROOT / relative, f"protocol source {name}", 4 * 1024 * 1024
            )
        )
        for name, relative in contract.PROTOCOL_SOURCE_PATHS.items()
    }


def _validate_protocol_sources(preregistration: Mapping[str, Any]) -> None:
    expected = {
        name: receipt["sha256"]
        for name, receipt in preregistration["source_lineage"][
            "protocol_sources"
        ].items()
    }
    if protocol_source_hashes() != expected:
        raise RuntimeError("v2 protocol source hash mismatch")


def _validate_v1_failure_artifact() -> None:
    path = ROOT / contract.V1_FAILURE_ARTIFACT_PATH
    payload = base_runner._read_regular_file(
        path, "v1 failure classification", 1024 * 1024
    )
    if (
        len(payload) != contract.V1_FAILURE_ARTIFACT_BYTES
        or contract.sha256_bytes(payload) != contract.V1_FAILURE_ARTIFACT_SHA256
    ):
        raise RuntimeError("v1 failure classification binding mismatch")
    raw = contract.parse_strict_json_bytes(
        payload, location="$.v1_failure_classification"
    )
    if not isinstance(raw, dict):
        raise RuntimeError("v1 failure classification must be an object")
    mm003_baseline_failure_classification.validate_failure_classification(ROOT, raw)


def _receipt(path: str, payload: bytes) -> dict[str, Any]:
    return {
        "path": path,
        "bytes": len(payload),
        "sha256": contract.sha256_bytes(payload),
    }


def _optional_metric_is_total(value: object) -> bool:
    if not isinstance(value, Mapping):
        return False
    total = value.get("total")
    correct = value.get("correct")
    if total == 0:
        return dict(value) == {
            "correct": 0,
            "total": 0,
            "value": None,
            "status": "not_applicable",
        }
    return (
        isinstance(total, int)
        and not isinstance(total, bool)
        and total > 0
        and isinstance(correct, int)
        and not isinstance(correct, bool)
        and 0 <= correct <= total
        and value.get("value") == correct / total
        and "status" not in value
    )


if __name__ == "__main__":
    raise SystemExit(main())
