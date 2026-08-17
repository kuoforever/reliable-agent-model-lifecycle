"""Prepare or execute the frozen MM-003 local small-VLM baseline."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import platform
import random
import stat
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from fullcycle_bridge import gui_grounding_eval  # noqa: E402
from fullcycle_bridge import mm003_baseline_protocol as contract  # noqa: E402


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

    smoke = subparsers.add_parser("smoke")
    smoke.add_argument("--model-snapshot", type=Path, required=True)

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
    elif args.command == "smoke":
        result = run_smoke(args.model_snapshot)
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
    """Bind the exact model, frozen suite, renderer outputs, and protocol sources."""

    suite_payload = _read_regular_file(suite_path, "MM-002 suite", 2 * 1024 * 1024)
    if contract.sha256_bytes(suite_payload) != contract.MM002_SUITE_FILE_SHA256:
        raise RuntimeError("MM-002 suite file hash mismatch")
    suite = gui_grounding_eval.load_suite_file(suite_path.resolve())
    if gui_grounding_eval.sha256_json(suite) != contract.MM002_SUITE_CANONICAL_SHA256:
        raise RuntimeError("MM-002 suite canonical hash mismatch")

    screenshot_receipts: list[dict[str, Any]] = []
    cases = {case["case_id"]: case for case in suite["cases"]}
    for case_id in contract.SCREENSHOT_CASES:
        payload = contract.render_case_png(cases[case_id])
        path = screenshots_dir / f"{case_id}.png"
        if check:
            if (
                _read_regular_file(path, f"screenshot {case_id}", 4 * 1024 * 1024)
                != payload
            ):
                raise RuntimeError(f"screenshot differs from renderer: {case_id}")
        else:
            _write_exclusive(path, payload)
        screenshot_receipts.append(
            {
                "case_id": case_id,
                "path": f"{contract.SCREENSHOT_ROOT}/{case_id}.png",
                "bytes": len(payload),
                "sha256": contract.sha256_bytes(payload),
            }
        )

    preregistration = contract.expected_preregistration(
        freeze_status=freeze_status,
        model_files=model_file_manifest(model_snapshot),
        screenshot_files=screenshot_receipts,
        protocol_source_hashes=protocol_source_hashes(),
    )
    payload = contract.artifact_json_bytes(preregistration)
    if check:
        if (
            _read_regular_file(output_path, "preregistration", 4 * 1024 * 1024)
            != payload
        ):
            raise RuntimeError("preregistration differs from recomputation")
    else:
        _write_exclusive(output_path, payload)
    return {
        "freeze_status": freeze_status,
        "model_files": len(preregistration["model"]["files"]),
        "screenshots": len(screenshot_receipts),
        "sha256": contract.sha256_bytes(payload),
        "valid": True,
    }


def run_smoke(model_snapshot: Path) -> dict[str, Any]:
    """Load the pinned model and generate from one unrelated blank synthetic image."""

    _assert_model_snapshot(model_snapshot)
    _enable_offline_execution()
    torch, model_class, processor_class, image_class = _load_ml_dependencies()
    _seed_all(torch, 20260817)
    torch.cuda.reset_peak_memory_stats()
    started = time.perf_counter()
    processor = processor_class.from_pretrained(
        model_snapshot,
        local_files_only=True,
        min_pixels=256 * 28 * 28,
        max_pixels=1280 * 28 * 28,
        use_fast=False,
    )
    model = model_class.from_pretrained(
        model_snapshot,
        torch_dtype=torch.bfloat16,
        attn_implementation="sdpa",
        device_map="cuda",
        local_files_only=True,
        low_cpu_mem_usage=True,
    ).eval()
    image = image_class.new("RGB", (512, 512), color=(245, 245, 245))
    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": "Compatibility smoke only. Never execute actions.",
        },
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {
                    "type": "text",
                    "text": (
                        "This is a load-only smoke test unrelated to the evaluation. "
                        "Reply with exactly the word READY."
                    ),
                },
            ],
        },
    ]
    raw, tokens = _generate_one(
        torch=torch,
        model=model,
        processor=processor,
        messages=messages,
        images=[image],
        max_new_tokens=16,
    )
    return {
        "elapsed_seconds": time.perf_counter() - started,
        "generated_tokens": tokens,
        "model_id": contract.MODEL_ID,
        "model_revision": contract.MODEL_REVISION,
        "output": raw,
        "peak_gpu_allocated_bytes": torch.cuda.max_memory_allocated(),
        "peak_gpu_reserved_bytes": torch.cuda.max_memory_reserved(),
        "smoke_only": True,
        "valid": True,
    }


def execute_frozen_baseline(
    *,
    model_snapshot: Path,
    preregistration_path: Path,
    protocol_freeze_commit: str,
    output_dir: Path,
) -> dict[str, Any]:
    """Execute the one registered nine-case run and write three exclusive artifacts."""

    if not re_full_commit(protocol_freeze_commit):
        raise RuntimeError("protocol freeze commit must be a lowercase 40-hex commit")
    preregistration_payload = _read_regular_file(
        preregistration_path, "preregistration", 4 * 1024 * 1024
    )
    preregistration_raw = contract.parse_strict_json_bytes(
        preregistration_payload, location="$.preregistration"
    )
    if not isinstance(preregistration_raw, dict):
        raise RuntimeError("preregistration must be an object")
    preregistration = contract.validate_preregistration(preregistration_raw)
    _validate_protocol_sources(preregistration)
    model_manifest = model_file_manifest(model_snapshot)
    if model_manifest != preregistration["model"]["files"]:
        raise RuntimeError("model snapshot differs from frozen manifest")

    suite_path = ROOT / contract.MM002_SUITE_PATH
    suite_payload = _read_regular_file(suite_path, "MM-002 suite", 2 * 1024 * 1024)
    suite = gui_grounding_eval.load_suite_file(suite_path.resolve())
    if (
        contract.sha256_bytes(suite_payload) != contract.MM002_SUITE_FILE_SHA256
        or gui_grounding_eval.sha256_json(suite)
        != contract.MM002_SUITE_CANONICAL_SHA256
    ):
        raise RuntimeError("MM-002 suite binding mismatch")
    screenshot_manifest = _validate_screenshots(preregistration, suite)

    _enable_offline_execution()
    torch, model_class, processor_class, image_class = _load_ml_dependencies()
    environment = observed_environment(torch)
    if environment != contract.LOCKED_ENVIRONMENT:
        raise RuntimeError(f"locked environment mismatch: {environment!r}")
    generation = preregistration["execution_protocol"]["generation"]
    _seed_all(torch, generation["seed"])
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
            screenshot_payload = _read_regular_file(
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
        raw_output, generated_tokens = _generate_one(
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
    score = gui_grounding_eval.score_predictions(suite, predictions)
    run_artifact = {
        "run_artifact_version": 1,
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
            "suite_canonical_sha256": gui_grounding_eval.sha256_json(suite),
            "screenshots": screenshot_manifest,
        },
        "environment": environment,
        "execution": {
            "fresh_model_loads": 1,
            "full_eval_runs": 1,
            "generate_calls": len(case_results),
            "retry_count": 0,
            "network_used": False,
            "completed": len(case_results) == 9,
        },
        "cases": case_results,
        "resources": resources,
        "claims": {
            "candidate_outputs_only": True,
            "direct_execution": False,
            "training_performed": False,
            "real_content_used": False,
            "runtime_eligible": False,
        },
    }
    evidence = build_evidence(
        preregistration=preregistration,
        preregistration_payload=preregistration_payload,
        protocol_freeze_commit=protocol_freeze_commit,
        run_artifact=run_artifact,
        predictions=predictions,
        score=score,
        suite=suite,
    )
    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise RuntimeError("output directory must be absent")
    output_dir.mkdir(parents=True, exist_ok=False)
    outputs = {
        Path(contract.RUN_ARTIFACT_PATH).name: contract.artifact_json_bytes(
            run_artifact
        ),
        Path(contract.PREDICTIONS_ARTIFACT_PATH).name: contract.artifact_json_bytes(
            predictions
        ),
        Path(contract.EVIDENCE_ARTIFACT_PATH).name: contract.artifact_json_bytes(
            evidence
        ),
    }
    for filename, payload in outputs.items():
        _write_exclusive(output_dir / filename, payload)
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
) -> dict[str, Any]:
    execution = run_artifact["execution"]
    resources = run_artifact["resources"]
    caps = preregistration["resource_caps"]
    records = predictions["records"]
    cases = run_artifact["cases"]
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
        "exact_synthetic_inputs": _exact_synthetic_inputs(
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
            and execution["completed"] is True
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
            score["predictions_sha256"] == gui_grounding_eval.sha256_json(predictions)
            and len(records) == 9
        ),
    }
    formal_gate_passed = all(gates.values())
    mode_metrics: dict[str, Any] = {}
    suite_cases = {case["case_id"]: case for case in suite["cases"]}
    for mode in ("uia_only", "screenshot_only", "fused"):
        selected = [item for item in cases if item["observation_mode"] == mode]
        correct = sum(
            _action_correct(suite_cases[item["case_id"]], item["compiled_prediction"])
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
        "evidence_version": 1,
        "experiment_id": contract.EXPERIMENT_ID,
        "gate_id": contract.GATE_ID,
        "protocol_freeze_commit": protocol_freeze_commit,
        "preregistration": {
            "bytes": len(preregistration_payload),
            "sha256": contract.sha256_bytes(preregistration_payload),
        },
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
            else "MM-003-local-small-vlm-baseline-failure-classification-v1"
        ),
        "runtime_eligible": False,
    }


def model_file_manifest(snapshot: Path) -> list[dict[str, Any]]:
    root = snapshot.resolve(strict=True)
    if not root.is_dir() or root.is_symlink():
        raise RuntimeError("model snapshot must be a regular directory")
    names = {path.name for path in root.iterdir()}
    if names != set(contract.MODEL_FILE_SIZES):
        raise RuntimeError(f"model snapshot file set mismatch: {sorted(names)!r}")
    records = []
    for name in sorted(contract.MODEL_FILE_SIZES):
        path = root / name
        payload_hash, byte_count = _stream_hash(path, f"model file {name}")
        records.append({"path": name, "bytes": byte_count, "sha256": payload_hash})
    return records


def protocol_source_hashes() -> dict[str, str]:
    return {
        name: contract.sha256_bytes(
            _read_regular_file(
                ROOT / relative, f"protocol source {name}", 4 * 1024 * 1024
            )
        )
        for name, relative in contract.PROTOCOL_SOURCE_PATHS.items()
    }


def observed_environment(torch: Any) -> dict[str, Any]:
    driver = _nvidia_driver()
    return {
        "accelerate": importlib.metadata.version("accelerate"),
        "compute_capability": ".".join(
            str(item) for item in torch.cuda.get_device_capability(0)
        ),
        "device": "cuda",
        "gpu": torch.cuda.get_device_name(0),
        "gpu_vram_bytes": torch.cuda.get_device_properties(0).total_memory,
        "huggingface_hub": importlib.metadata.version("huggingface-hub"),
        "nvidia_driver": driver,
        "pillow": importlib.metadata.version("pillow"),
        "platform_machine": platform.machine(),
        "platform_release": platform.release(),
        "platform_system": platform.system(),
        "platform_version": platform.version(),
        "python": platform.python_version(),
        "safetensors": importlib.metadata.version("safetensors"),
        "tokenizers": importlib.metadata.version("tokenizers"),
        "torch": torch.__version__,
        "transformers": importlib.metadata.version("transformers"),
    }


def _generate_one(
    *,
    torch: Any,
    model: Any,
    processor: Any,
    messages: list[dict[str, Any]],
    images: list[Any] | None,
    max_new_tokens: int,
) -> tuple[str, int]:
    text = processor.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    kwargs: dict[str, Any] = {
        "text": [text],
        "padding": True,
        "return_tensors": "pt",
    }
    if images is not None:
        kwargs["images"] = images
    inputs = processor(**kwargs).to("cuda")
    with torch.inference_mode():
        generated = model.generate(
            **inputs,
            do_sample=False,
            max_new_tokens=max_new_tokens,
            repetition_penalty=1.05,
            temperature=None,
            use_cache=True,
        )
    trimmed = generated[:, inputs.input_ids.shape[1] :]
    output = processor.batch_decode(
        trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
    )[0]
    return output, int(trimmed.shape[1])


def _load_ml_dependencies() -> tuple[Any, Any, Any, Any]:
    import torch
    from PIL import Image
    from transformers import (  # type: ignore[import-untyped]
        AutoProcessor,
        Qwen2_5_VLForConditionalGeneration,
    )

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable")
    return torch, Qwen2_5_VLForConditionalGeneration, AutoProcessor, Image


def _enable_offline_execution() -> None:
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_DATASETS_OFFLINE"] = "1"


def _seed_all(torch: Any, seed: int) -> None:
    random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False


def _assert_model_snapshot(snapshot: Path) -> None:
    manifest = model_file_manifest(snapshot)
    for record in manifest:
        expected = contract.MODEL_WEIGHT_SHA256.get(record["path"])
        if expected is not None and record["sha256"] != expected:
            raise RuntimeError(f"model weight hash mismatch: {record['path']}")


def _validate_protocol_sources(preregistration: Mapping[str, Any]) -> None:
    expected = {
        name: receipt["sha256"]
        for name, receipt in preregistration["source_lineage"][
            "protocol_sources"
        ].items()
    }
    if protocol_source_hashes() != expected:
        raise RuntimeError("protocol source hash mismatch")


def _validate_screenshots(
    preregistration: Mapping[str, Any], suite: Mapping[str, Any]
) -> list[dict[str, Any]]:
    cases = {case["case_id"]: case for case in suite["cases"]}
    observed_receipts: list[dict[str, Any]] = []
    for receipt in preregistration["source_lineage"]["screenshots"]:
        case_id = receipt["case_id"]
        path = ROOT / receipt["path"]
        payload = _read_regular_file(path, f"screenshot {case_id}", 4 * 1024 * 1024)
        observed = {
            "case_id": case_id,
            "path": receipt["path"],
            "bytes": len(payload),
            "sha256": contract.sha256_bytes(payload),
        }
        if payload != contract.render_case_png(cases[case_id]) or observed != receipt:
            raise RuntimeError(f"screenshot binding mismatch: {case_id}")
        observed_receipts.append(observed)
    return observed_receipts


def _exact_synthetic_inputs(
    *,
    preregistration: Mapping[str, Any],
    run_artifact: Mapping[str, Any],
    suite: Mapping[str, Any],
) -> bool:
    expected_inputs = {
        "suite_file_sha256": contract.MM002_SUITE_FILE_SHA256,
        "suite_canonical_sha256": contract.MM002_SUITE_CANONICAL_SHA256,
        "screenshots": preregistration["source_lineage"]["screenshots"],
    }
    if run_artifact.get("inputs") != expected_inputs:
        return False
    receipts = {
        item["case_id"]: item["sha256"]
        for item in preregistration["source_lineage"]["screenshots"]
    }
    suite_cases = suite.get("cases")
    run_cases = run_artifact.get("cases")
    if not isinstance(suite_cases, list) or not isinstance(run_cases, list):
        return False
    if len(suite_cases) != 9 or len(run_cases) != 9:
        return False
    for case, observed in zip(suite_cases, run_cases, strict=True):
        case_id = case["case_id"]
        expected_screenshot = (
            None if case["observation_mode"] == "uia_only" else receipts[case_id]
        )
        if (
            observed.get("case_id") != case_id
            or observed.get("observation_mode") != case["observation_mode"]
            or observed.get("prompt_sha256")
            != contract.sha256_bytes(contract.build_user_prompt(case).encode("utf-8"))
            or observed.get("screenshot_sha256") != expected_screenshot
        ):
            return False
    return True


def _action_correct(case: Mapping[str, Any], record: Mapping[str, Any]) -> int:
    gold = case["gold"]
    if gold["disposition"] != "act":
        return int(
            record["disposition"] == gold["disposition"]
            and record["reason"] == gold["reason"]
        )
    if record["disposition"] != "act":
        return 0
    catalog = gold["target_catalog"]
    ref_target = next(
        (item["target_id"] for item in catalog if item["ref"] == record["ref"]),
        None,
    )
    bbox_target = None
    if record["bbox"] is not None:
        matches = [
            item["target_id"]
            for item in catalog
            if _bbox_iou(record["bbox"], item["bbox"]) >= 0.5
        ]
        if len(matches) == 1:
            bbox_target = matches[0]
    capability = case["capability"]
    if capability == "ref_grounding":
        matched = ref_target == gold["target_id"]
    elif capability == "bbox_grounding":
        matched = bbox_target == gold["target_id"]
    else:
        matched = ref_target == gold["target_id"] and bbox_target == gold["target_id"]
    return int(matched)


def _bbox_iou(left: Sequence[int], right: Sequence[int]) -> float:
    ix1, iy1 = max(left[0], right[0]), max(left[1], right[1])
    ix2, iy2 = min(left[2], right[2]), min(left[3], right[3])
    intersection = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    left_area = (left[2] - left[0]) * (left[3] - left[1])
    right_area = (right[2] - right[0]) * (right[3] - right[1])
    union = left_area + right_area - intersection
    return intersection / union if union else 0.0


def _nvidia_driver() -> str:
    completed = subprocess.run(
        ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader,nounits"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        timeout=15,
    )
    lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    if completed.returncode != 0 or completed.stderr or len(lines) != 1:
        raise RuntimeError("exactly one NVIDIA driver row is required")
    return lines[0]


def re_full_commit(value: str) -> bool:
    return len(value) == 40 and all(char in "0123456789abcdef" for char in value)


def _stream_hash(path: Path, label: str) -> tuple[str, int]:
    resolved = path.resolve(strict=True)
    info = os.lstat(resolved)
    if not stat.S_ISREG(info.st_mode) or path.is_symlink():
        raise RuntimeError(f"unsafe {label}")
    digest = __import__("hashlib").sha256()
    count = 0
    with resolved.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
            count += len(chunk)
    return "sha256:" + digest.hexdigest(), count


def _read_regular_file(path: Path, label: str, max_bytes: int) -> bytes:
    resolved = path.resolve(strict=True)
    info = os.lstat(resolved)
    if not stat.S_ISREG(info.st_mode) or path.is_symlink() or info.st_size > max_bytes:
        raise RuntimeError(f"unsafe or oversized {label}")
    payload = resolved.read_bytes()
    if len(payload) != info.st_size:
        raise RuntimeError(f"unstable {label}")
    return payload


def _write_exclusive(path: Path, payload: bytes) -> None:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(payload)


if __name__ == "__main__":
    raise SystemExit(main())
