"""Prepare or execute the frozen MM-003 QLoRA post-training recovery v2."""

from __future__ import annotations

import argparse
import gc
import importlib.metadata
import json
import math
import os
import random
import re
import sys
import time
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SRC))

from fullcycle_bridge import gui_grounding_eval as base_scorer  # noqa: E402
from fullcycle_bridge import gui_grounding_eval_v2 as scorer  # noqa: E402
from fullcycle_bridge import mm003_post_training_protocol_v2 as contract  # noqa: E402
from scripts import run_mm003_multimodal_gui_action_baseline as base_runner  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("--model-snapshot", type=Path, required=True)
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
    run.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / contract.RUN_OUTPUT_ROOT,
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "prepare":
        result = prepare_protocol(
            model_snapshot=args.model_snapshot,
            output_path=args.output,
            freeze_status=args.freeze_status,
            check=args.check,
        )
    else:
        result = execute_frozen_protocol(
            model_snapshot=args.model_snapshot,
            preregistration_path=args.preregistration,
            protocol_freeze_commit=args.protocol_freeze_commit,
            output_dir=args.output_dir,
        )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


def prepare_protocol(
    *,
    model_snapshot: Path,
    output_path: Path,
    freeze_status: str,
    check: bool,
) -> dict[str, Any]:
    inputs = load_and_validate_inputs()
    _validate_local_dependency_wheel()
    recovery_lineage = _load_recovery_lineage()
    v1_preregistration = recovery_lineage["v1_preregistration"]
    model_manifest = base_runner.model_file_manifest(model_snapshot)
    if model_manifest != v1_preregistration["model"]["files"]:
        raise RuntimeError("model snapshot differs from frozen v1 manifest")
    _validate_preregistered_inputs(v1_preregistration, inputs)
    preregistration = contract.expected_preregistration(
        freeze_status=freeze_status,
        v1_preregistration=v1_preregistration,
        source_hashes=protocol_source_hashes(),
        train=inputs["train"],
        validation=inputs["validation"],
    )
    payload = contract.artifact_json_bytes(preregistration)
    if check:
        observed = base_runner._read_regular_file(
            output_path, "post-training preregistration", 4 * 1024 * 1024
        )
        if observed != payload:
            raise RuntimeError(
                "post-training preregistration differs from recomputation"
            )
    else:
        base_runner._write_exclusive(output_path, payload)
    return {
        "eval_isolation": inputs["isolation_audit"]["passed"],
        "freeze_status": freeze_status,
        "model_files": len(preregistration["model"]["files"]),
        "screenshots": len(inputs["training_screenshot_receipts"]),
        "sha256": contract.sha256_bytes(payload),
        "source_files": len(contract.PROTOCOL_SOURCE_PATHS),
        "train_records": contract.TRAIN_RECORDS,
        "validation_records": contract.VALIDATION_RECORDS,
        "valid": True,
    }


def execute_frozen_protocol(
    *,
    model_snapshot: Path,
    preregistration_path: Path,
    protocol_freeze_commit: str,
    output_dir: Path,
) -> dict[str, Any]:
    """Run the single registered train/save/reload/eval lifecycle."""

    if not base_runner.re_full_commit(protocol_freeze_commit):
        raise RuntimeError("protocol freeze commit must be a lowercase 40-hex commit")
    expected_output_dir = (ROOT / contract.RUN_OUTPUT_ROOT).resolve()
    output_dir = output_dir.resolve()
    if output_dir != expected_output_dir:
        raise RuntimeError("output directory differs from frozen protocol")
    if output_dir.exists():
        raise RuntimeError("output directory must be absent before model load")

    output_dir.mkdir(parents=True, exist_ok=False)
    lifecycle_started = time.perf_counter()
    stage = "preregistration"
    preregistration_payload: bytes | None = None
    try:
        preregistration_payload = base_runner._read_regular_file(
            preregistration_path, "post-training preregistration", 4 * 1024 * 1024
        )
        raw = contract.parse_strict_json_bytes(
            preregistration_payload, location="$.preregistration"
        )
        if not isinstance(raw, dict):
            raise RuntimeError("post-training preregistration must be an object")

        stage = "recovery_lineage"
        recovery_lineage = _load_recovery_lineage()
        v1_preregistration = recovery_lineage["v1_preregistration"]
        stage = "protocol_sources"
        trusted_source_hashes = _validate_protocol_sources(raw)
        stage = "dependency_wheel"
        _validate_local_dependency_wheel()
        stage = "inputs"
        inputs = load_and_validate_inputs()
        stage = "preregistration_validation"
        preregistration = contract.validate_preregistration(
            raw,
            v1_preregistration=v1_preregistration,
            train=inputs["train"],
            validation=inputs["validation"],
            source_hashes=trusted_source_hashes,
        )
        stage = "preregistered_inputs"
        _validate_preregistered_inputs(preregistration, inputs)
        stage = "training_prompt_preflight"
        prompt_preflight = contract.validate_prompt_preflight(
            preregistration,
            train=inputs["train"],
            validation=inputs["validation"],
        )
        stage = "model_manifest"
        model_manifest = base_runner.model_file_manifest(model_snapshot)
        if model_manifest != preregistration["model"]["files"]:
            raise RuntimeError("model snapshot differs from frozen manifest")

        stage = "dependency_import"
        _enable_offline_execution()
        dependencies = _load_ml_dependencies()
        torch = dependencies[1]
        stage = "locked_environment"
        environment = observed_environment(torch)
        if environment != contract.LOCKED_ENVIRONMENT:
            raise RuntimeError(f"locked environment mismatch: {environment!r}")

        stage = "training"
        training = _train_adapter(
            dependencies=dependencies,
            model_snapshot=model_snapshot,
            train=inputs["train"],
            validation=inputs["validation"],
            output_dir=output_dir,
            protocol_freeze_commit=protocol_freeze_commit,
            preregistration_payload=preregistration_payload,
            environment=environment,
            model_manifest=model_manifest,
            isolation_audit=inputs["isolation_audit"],
        )
        stage = "independent_adapter_load_and_eval"
        evaluation = _independent_load_and_eval(
            dependencies=dependencies,
            model_snapshot=model_snapshot,
            adapter_dir=output_dir / "adapter",
            eval_suite=inputs["eval_suite"],
            eval_screenshot_receipts=inputs["eval_screenshot_receipts"],
        )
        stage = "resource_accounting"
        torch.cuda.synchronize()
        peak_gpu_allocated_bytes = int(torch.cuda.max_memory_allocated())
        peak_gpu_reserved_bytes = int(torch.cuda.max_memory_reserved())
        lifecycle_resources = {
            "elapsed_seconds": time.perf_counter() - lifecycle_started,
            "peak_gpu_allocated_bytes": peak_gpu_allocated_bytes,
            "peak_gpu_reserved_bytes": peak_gpu_reserved_bytes,
        }
        stage = "evidence"
        evidence = build_evidence(
            preregistration=preregistration,
            preregistration_payload=preregistration_payload,
            protocol_freeze_commit=protocol_freeze_commit,
            training=training,
            evaluation=evaluation,
            environment=environment,
            model_manifest=model_manifest,
            isolation_audit=inputs["isolation_audit"],
            prompt_preflight=prompt_preflight,
            lifecycle_resources=lifecycle_resources,
        )
        predictions_payload = contract.artifact_json_bytes(evaluation["predictions"])
        evidence_payload = contract.artifact_json_bytes(evidence)
        base_runner._write_exclusive(
            output_dir / "mm002-predictions.json", predictions_payload
        )
        base_runner._write_exclusive(output_dir / "evidence.json", evidence_payload)
        return {
            "adapter_independently_loadable": evidence["claims"][
                "adapter_independently_loadable"
            ],
            "classification": evidence["classification"],
            "formal_gate_passed": evidence["formal_gate_passed"],
            "quality_improved": evidence["claims"]["quality_improved"],
            "valid": evidence["formal_gate_passed"],
        }
    except Exception as exc:
        exception_type, exception_code, exception_location = (
            _safe_exception_diagnostic(exc)
        )
        failure = {
            "failure_version": 2,
            "experiment_id": contract.EXPERIMENT_ID,
            "gate_id": contract.EXECUTION_GATE_ID,
            "protocol_freeze_commit": protocol_freeze_commit,
            "preregistration_sha256": (
                contract.sha256_bytes(preregistration_payload)
                if preregistration_payload is not None
                else None
            ),
            "stage": stage,
            "exception_type": exception_type,
            "exception_code": exception_code,
            "exception_location": exception_location,
            "retry_count": 0,
            "formal_gate_passed": False,
            "claims": _negative_result_claims(),
            "runtime_eligible": False,
        }
        failure_path = output_dir / "failure.json"
        if not failure_path.exists():
            base_runner._write_exclusive(
                failure_path, contract.artifact_json_bytes(failure)
            )
        raise


def load_and_validate_inputs() -> dict[str, Any]:
    train_path = ROOT / contract.TRAIN_DATASET_PATH
    validation_path = ROOT / contract.VALIDATION_DATASET_PATH
    train_payload = base_runner._read_regular_file(
        train_path, "training fixture", 4 * 1024 * 1024
    )
    validation_payload = base_runner._read_regular_file(
        validation_path, "validation fixture", 4 * 1024 * 1024
    )
    train_raw = contract.parse_strict_json_bytes(train_payload, location="$.train")
    validation_raw = contract.parse_strict_json_bytes(
        validation_payload, location="$.validation"
    )
    train = contract.validate_dataset(train_raw, split="train")
    validation = contract.validate_dataset(validation_raw, split="validation")

    training_screenshot_receipts = contract.expected_screenshot_receipts()
    for receipt in training_screenshot_receipts:
        payload = base_runner._read_regular_file(
            ROOT / receipt["path"],
            f"training screenshot {receipt['case_id']}",
            4 * 1024 * 1024,
        )
        if (
            len(payload) != receipt["bytes"]
            or contract.sha256_bytes(payload) != receipt["sha256"]
        ):
            raise RuntimeError("training screenshot differs from deterministic source")

    eval_suite_path = ROOT / contract.baseline.MM002_SUITE_PATH
    eval_payload = base_runner._read_regular_file(
        eval_suite_path, "MM-002 eval suite", 2 * 1024 * 1024
    )
    eval_suite = base_scorer.load_suite_file(eval_suite_path.resolve())
    if (
        contract.sha256_bytes(eval_payload) != contract.baseline.MM002_SUITE_FILE_SHA256
        or base_scorer.sha256_json(eval_suite)
        != contract.baseline.MM002_SUITE_CANONICAL_SHA256
    ):
        raise RuntimeError("MM-002 eval suite binding mismatch")
    eval_screenshot_receipts, eval_screenshot_payloads = _eval_screenshots(eval_suite)
    isolation_audit = contract.audit_eval_isolation(
        train=train,
        validation=validation,
        eval_suite=eval_suite,
        eval_screenshot_payloads=eval_screenshot_payloads,
    )
    if not isolation_audit["passed"]:
        raise RuntimeError("training data overlaps frozen MM-002 eval")
    return {
        "eval_screenshot_receipts": eval_screenshot_receipts,
        "eval_suite": eval_suite,
        "isolation_audit": isolation_audit,
        "train": train,
        "train_receipt": {
            "path": contract.TRAIN_DATASET_PATH,
            "bytes": len(train_payload),
            "sha256": contract.sha256_bytes(train_payload),
        },
        "training_screenshot_receipts": training_screenshot_receipts,
        "validation": validation,
        "validation_receipt": {
            "path": contract.VALIDATION_DATASET_PATH,
            "bytes": len(validation_payload),
            "sha256": contract.sha256_bytes(validation_payload),
        },
    }


def build_evidence(
    *,
    preregistration: Mapping[str, Any],
    preregistration_payload: bytes,
    protocol_freeze_commit: str,
    training: Mapping[str, Any],
    evaluation: Mapping[str, Any],
    environment: Mapping[str, Any],
    model_manifest: Sequence[Mapping[str, Any]],
    isolation_audit: Mapping[str, Any],
    prompt_preflight: Mapping[str, Any],
    lifecycle_resources: Mapping[str, Any],
) -> dict[str, Any]:
    resources = _mapping(lifecycle_resources, "$.lifecycle_resources")
    caps = _mapping(preregistration["resource_caps"], "$.resource_caps")
    adapter_manifest = training["adapter_manifest"]
    required_adapter_files = preregistration["outputs"]["required_adapter_files"]
    gates = {
        "protocol_integrity": (
            preregistration["freeze_status"] == "frozen"
            and training["protocol"]["preregistration_sha256"]
            == contract.sha256_bytes(preregistration_payload)
            and training["protocol"]["freeze_commit"] == protocol_freeze_commit
        ),
        "exact_model_files": list(model_manifest) == preregistration["model"]["files"],
        "locked_environment": dict(environment) == contract.LOCKED_ENVIRONMENT,
        "training_fixture_integrity": (
            training["data"]["train_records"] == contract.TRAIN_RECORDS
            and training["data"]["validation_records"] == contract.VALIDATION_RECORDS
        ),
        contract.RECOVERY_PROMPT_GATE: (
            dict(prompt_preflight)
            == {
                "records_checked": contract.TRAIN_RECORDS
                + contract.VALIDATION_RECORDS,
                "receipts_matched": True,
                "aggregate_sha256": preregistration["prompt_receipts"][
                    "aggregate_sha256"
                ],
            }
        ),
        "eval_isolation": bool(isolation_audit["passed"]),
        "offline_single_training_run": training["execution"]
        == {
            "fresh_train_model_loads": 1,
            "full_training_runs": 1,
            "network_used": False,
            "retry_count": 0,
            "training_completed": True,
        },
        "adapter_artifact_integrity": (
            [item["path"] for item in adapter_manifest] == required_adapter_files
            and all(item["bytes"] > 0 for item in adapter_manifest)
        ),
        "independent_adapter_load": evaluation["execution"]["independent_adapter_loads"]
        == 1,
        "unchanged_mm002_eval": evaluation["execution"]
        == {
            "fresh_base_loads": 1,
            "full_eval_runs": 1,
            "generate_calls": 9,
            "independent_adapter_loads": 1,
            "network_used": False,
            "retry_count": 0,
        },
        "total_scoring": evaluation["score"]["case_count"] == 9,
        "resource_caps": (
            resources["elapsed_seconds"] <= caps["elapsed_seconds"]
            and resources["peak_gpu_allocated_bytes"]
            <= caps["peak_gpu_allocated_bytes"]
            and resources["peak_gpu_reserved_bytes"] <= caps["peak_gpu_reserved_bytes"]
        ),
        "fail_closed_claims": (
            preregistration["runtime_eligible"] is False
            and preregistration["claims"]["promotion_eligible"] is False
            and all(
                value is False
                for value in preregistration["authority_contract"].values()
            )
        ),
    }
    formal_gate_passed = (
        list(gates) == preregistration["formal_gate"]["required_gates"]
        and all(gates.values())
    )
    claims = _negative_result_claims()
    claims.update(
        {
            "training_executed": formal_gate_passed,
            "adapter_created": formal_gate_passed,
            "adapter_independently_loadable": formal_gate_passed,
            "model_evaluated": formal_gate_passed,
        }
    )
    return {
        "evidence_version": 2,
        "experiment_id": contract.EXPERIMENT_ID,
        "gate_id": contract.EXECUTION_GATE_ID,
        "captured_at_utc": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "protocol": {
            "freeze_commit": protocol_freeze_commit,
            "preregistration_sha256": contract.sha256_bytes(preregistration_payload),
        },
        "gates": gates,
        "formal_gate_passed": formal_gate_passed,
        "classification": (
            "local_qlora_adapter_measurement_established"
            if formal_gate_passed
            else "local_qlora_adapter_measurement_not_established"
        ),
        "prompt_preflight": dict(prompt_preflight),
        "training": dict(training),
        "evaluation": dict(evaluation),
        "resources": dict(resources),
        "claims": claims,
        "next_gate": (
            contract.SUCCESS_NEXT_GATE_ID if formal_gate_passed else None
        ),
        "runtime_eligible": False,
    }


def protocol_source_hashes() -> dict[str, str]:
    return {
        name: contract.sha256_bytes(
            base_runner._read_regular_file(
                ROOT / path, f"protocol source {name}", 4 * 1024 * 1024
            )
        )
        for name, path in contract.PROTOCOL_SOURCE_PATHS.items()
    }


def _load_recovery_lineage() -> dict[str, dict[str, Any]]:
    v1_preregistration_payload = base_runner._read_regular_file(
        ROOT / contract.V1_PREREGISTRATION_RECEIPT["path"],
        "v1 post-training preregistration",
        4 * 1024 * 1024,
    )
    v1_failure_payload = base_runner._read_regular_file(
        ROOT / contract.V1_FAILURE_RECEIPT["path"],
        "v1 post-training failure receipt",
        4 * 1024 * 1024,
    )
    v1_failure_classification_payload = base_runner._read_regular_file(
        ROOT / contract.V1_FAILURE_CLASSIFICATION_RECEIPT["path"],
        "v1 post-training failure classification",
        4 * 1024 * 1024,
    )
    return contract.validate_recovery_lineage_payloads(
        v1_preregistration_payload=v1_preregistration_payload,
        v1_failure_payload=v1_failure_payload,
        v1_failure_classification_payload=v1_failure_classification_payload,
    )


def observed_environment(torch: Any) -> dict[str, Any]:
    return {
        **base_runner.observed_environment(torch),
        "bitsandbytes": importlib.metadata.version("bitsandbytes"),
    }


def _train_adapter(
    *,
    dependencies: tuple[Any, ...],
    model_snapshot: Path,
    train: Mapping[str, Any],
    validation: Mapping[str, Any],
    output_dir: Path,
    protocol_freeze_commit: str,
    preregistration_payload: bytes,
    environment: Mapping[str, Any],
    model_manifest: Sequence[Mapping[str, Any]],
    isolation_audit: Mapping[str, Any],
) -> dict[str, Any]:
    (
        _,
        torch,
        image_class,
        lora_config_class,
        task_type,
        get_peft_model,
        _,
        prepare_model_for_kbit_training,
        processor_class,
        model_class,
        quantization_config_class,
        scheduler_factory,
    ) = dependencies
    _seed_all(torch, contract.TRAINING_SEED)
    before_allocated = int(torch.cuda.memory_allocated())
    before_reserved = int(torch.cuda.memory_reserved())
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
        quantization_config=_quantization_config(torch, quantization_config_class),
        attn_implementation="sdpa",
        device_map={"": 0},
        local_files_only=True,
        low_cpu_mem_usage=True,
    )
    model = prepare_model_for_kbit_training(
        model,
        use_gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
    )
    model = get_peft_model(
        model,
        lora_config_class(
            task_type=task_type.CAUSAL_LM,
            r=16,
            lora_alpha=32,
            lora_dropout=0.05,
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
            bias="none",
        ),
    )
    model.train()
    model.config.use_cache = False
    trainable_parameters = sum(
        parameter.numel() for parameter in model.parameters() if parameter.requires_grad
    )
    if trainable_parameters != 7_372_800:
        raise RuntimeError("trainable parameter count differs from compatibility smoke")

    optimizer = torch.optim.AdamW(
        (parameter for parameter in model.parameters() if parameter.requires_grad),
        lr=0.0002,
        weight_decay=0.0,
    )
    steps_per_epoch = math.ceil(contract.TRAIN_RECORDS / 3)
    total_steps = steps_per_epoch * 3
    scheduler = scheduler_factory(
        optimizer,
        num_warmup_steps=round(total_steps * 0.1),
        num_training_steps=total_steps,
    )
    epoch_metrics: list[dict[str, Any]] = []
    optimizer_steps = 0
    records = list(train["records"])
    optimizer.zero_grad(set_to_none=True)
    for epoch in range(1, 4):
        order = list(range(len(records)))
        random.Random(contract.TRAINING_SEED + epoch).shuffle(order)
        losses: list[float] = []
        for micro_step, record_index in enumerate(order, start=1):
            batch = _encode_training_record(
                torch=torch,
                image_class=image_class,
                processor=processor,
                record=records[record_index],
            )
            output = model(**batch)
            loss = output.loss
            if not bool(torch.isfinite(loss).item()):
                raise RuntimeError("training loss is not finite")
            losses.append(float(loss.detach().cpu().item()))
            (loss / 3).backward()
            if micro_step % 3 == 0:
                torch.nn.utils.clip_grad_norm_(
                    (
                        parameter
                        for parameter in model.parameters()
                        if parameter.requires_grad
                    ),
                    max_norm=1.0,
                )
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad(set_to_none=True)
                optimizer_steps += 1
        validation_loss = _validation_loss(
            torch=torch,
            image_class=image_class,
            processor=processor,
            model=model,
            records=list(validation["records"]),
        )
        epoch_metrics.append(
            {
                "epoch": epoch,
                "mean_train_loss": sum(losses) / len(losses),
                "mean_validation_loss": validation_loss,
                "optimizer_steps_completed": optimizer_steps,
                "record_order": [records[item]["case_id"] for item in order],
            }
        )
        model.train()
    if optimizer_steps != total_steps:
        raise RuntimeError("optimizer step count differs from frozen protocol")

    adapter_dir = output_dir / "adapter"
    model.save_pretrained(adapter_dir, safe_serialization=True)
    _canonicalize_adapter_artifacts(adapter_dir)
    adapter_manifest = _adapter_manifest(adapter_dir)
    torch.cuda.synchronize()
    resources = {
        "elapsed_seconds": time.perf_counter() - started,
        "gpu_allocated_before_bytes": before_allocated,
        "gpu_reserved_before_bytes": before_reserved,
        "gpu_allocated_after_bytes": int(torch.cuda.memory_allocated()),
        "gpu_reserved_after_bytes": int(torch.cuda.memory_reserved()),
        "peak_gpu_allocated_bytes": int(torch.cuda.max_memory_allocated()),
        "peak_gpu_reserved_bytes": int(torch.cuda.max_memory_reserved()),
    }
    artifact = {
        "training_run_version": 1,
        "experiment_id": contract.EXPERIMENT_ID,
        "gate_id": contract.EXECUTION_GATE_ID,
        "protocol": {
            "freeze_commit": protocol_freeze_commit,
            "preregistration_sha256": contract.sha256_bytes(preregistration_payload),
        },
        "model": {
            "repo_id": contract.MODEL_ID,
            "revision": contract.MODEL_REVISION,
            "files": list(model_manifest),
        },
        "environment": dict(environment),
        "data": {
            "train_records": len(records),
            "validation_records": len(validation["records"]),
            "eval_isolation": dict(isolation_audit),
        },
        "execution": {
            "fresh_train_model_loads": 1,
            "full_training_runs": 1,
            "network_used": False,
            "retry_count": 0,
            "training_completed": True,
        },
        "optimizer_steps": optimizer_steps,
        "epoch_metrics": epoch_metrics,
        "trainable_parameters": trainable_parameters,
        "adapter_manifest": adapter_manifest,
        "resources": resources,
    }
    base_runner._write_exclusive(
        output_dir / "training-run.json", contract.artifact_json_bytes(artifact)
    )

    del optimizer, scheduler, model, processor
    gc.collect()
    torch.cuda.empty_cache()
    return artifact


def _independent_load_and_eval(
    *,
    dependencies: tuple[Any, ...],
    model_snapshot: Path,
    adapter_dir: Path,
    eval_suite: Mapping[str, Any],
    eval_screenshot_receipts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    (
        _,
        torch,
        image_class,
        _,
        _,
        _,
        peft_model_class,
        _,
        processor_class,
        model_class,
        quantization_config_class,
        _,
    ) = dependencies
    _seed_all(torch, contract.TRAINING_SEED)
    processor = processor_class.from_pretrained(
        model_snapshot,
        local_files_only=True,
        min_pixels=256 * 28 * 28,
        max_pixels=1280 * 28 * 28,
        use_fast=False,
    )
    base_model = model_class.from_pretrained(
        model_snapshot,
        quantization_config=_quantization_config(torch, quantization_config_class),
        attn_implementation="sdpa",
        device_map={"": 0},
        local_files_only=True,
        low_cpu_mem_usage=True,
    )
    model = peft_model_class.from_pretrained(
        base_model,
        adapter_dir,
        is_trainable=False,
        local_files_only=True,
    ).eval()
    model.config.use_cache = True

    screenshot_hashes = {
        item["case_id"]: item["sha256"] for item in eval_screenshot_receipts
    }
    case_results: list[dict[str, Any]] = []
    prediction_records: list[dict[str, Any]] = []
    for case in eval_suite["cases"]:
        case_id = case["case_id"]
        content: list[dict[str, Any]] = []
        images: list[Any] | None = None
        image = None
        if case["observation_mode"] != "uia_only":
            image = image_class.open(
                ROOT / contract.baseline.SCREENSHOT_ROOT / f"{case_id}.png"
            ).convert("RGB")
            images = [image]
            content.append({"type": "image", "image": image})
        prompt = contract.baseline.build_user_prompt(case)
        content.append({"type": "text", "text": prompt})
        messages = [
            {"role": "system", "content": contract.baseline.SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ]
        torch.cuda.synchronize()
        started = time.perf_counter()
        raw_output, generated_tokens = base_runner._generate_one(
            torch=torch,
            model=model,
            processor=processor,
            messages=messages,
            images=images,
            max_new_tokens=256,
        )
        torch.cuda.synchronize()
        compiled = contract.baseline.compile_raw_prediction(raw_output, case)
        prediction_records.append(compiled)
        case_results.append(
            {
                "case_id": case_id,
                "observation_mode": case["observation_mode"],
                "raw_output": raw_output,
                "compiled_prediction": compiled,
                "compiler_fallback": compiled["reason"] == "model_output_invalid",
                "generated_tokens": generated_tokens,
                "latency_seconds": time.perf_counter() - started,
                "screenshot_sha256": screenshot_hashes.get(case_id),
            }
        )
        if image is not None:
            image.close()
    predictions = {
        "gui_grounding_prediction_version": 1,
        "suite_id": eval_suite["suite_id"],
        "producer": {
            "kind": "model",
            "model_id": contract.ADAPTER_MODEL_ID,
            "model_revision": contract.MODEL_REVISION,
        },
        "records": prediction_records,
    }
    report = scorer.score_predictions(eval_suite, predictions)
    return {
        "execution": {
            "fresh_base_loads": 1,
            "full_eval_runs": 1,
            "generate_calls": len(case_results),
            "independent_adapter_loads": 1,
            "network_used": False,
            "retry_count": 0,
        },
        "cases": case_results,
        "predictions": predictions,
        "score": report,
    }


def _encode_training_record(
    *, torch: Any, image_class: Any, processor: Any, record: Mapping[str, Any]
) -> dict[str, Any]:
    content: list[dict[str, Any]] = []
    images: list[Any] | None = None
    image = None
    if record["observation_mode"] != "uia_only":
        split = str(record["case_id"]).split("-")[1]
        image = image_class.open(
            ROOT
            / contract.TRAINING_SCREENSHOT_ROOT
            / split
            / f"{record['case_id']}.png"
        ).convert("RGB")
        images = [image]
        content.append({"type": "image", "image": image})
    content.append({"type": "text", "text": contract.render_training_input(record)})
    prefix_messages = [
        {"role": "system", "content": contract.SYSTEM_PROMPT},
        {"role": "user", "content": content},
    ]
    full_messages = [
        *prefix_messages,
        {"role": "assistant", "content": contract.render_training_target(record)},
    ]
    prefix = _processor_encode(
        processor, prefix_messages, images, add_generation_prompt=True
    )
    batch = _processor_encode(
        processor, full_messages, images, add_generation_prompt=False
    )
    prefix_length = int(prefix.input_ids.shape[1])
    if prefix_length >= int(batch.input_ids.shape[1]):
        raise RuntimeError("assistant target has no trainable tokens")
    if not torch.equal(prefix.input_ids[0], batch.input_ids[0, :prefix_length]):
        raise RuntimeError("multimodal prompt prefix differs from full example")
    labels = batch.input_ids.clone()
    labels[:, :prefix_length] = -100
    labels[batch.attention_mask == 0] = -100
    cuda_batch = {key: value.to("cuda") for key, value in batch.items()}
    cuda_batch["labels"] = labels.to("cuda")
    if image is not None:
        image.close()
    return cuda_batch


def _validation_loss(
    *,
    torch: Any,
    image_class: Any,
    processor: Any,
    model: Any,
    records: Sequence[Mapping[str, Any]],
) -> float:
    model.eval()
    losses: list[float] = []
    with torch.no_grad():
        for record in records:
            batch = _encode_training_record(
                torch=torch,
                image_class=image_class,
                processor=processor,
                record=record,
            )
            loss = float(model(**batch).loss.detach().cpu().item())
            if not math.isfinite(loss):
                raise RuntimeError("validation loss is not finite")
            losses.append(loss)
    return sum(losses) / len(losses)


def _processor_encode(
    processor: Any,
    messages: list[dict[str, Any]],
    images: list[Any] | None,
    *,
    add_generation_prompt: bool,
) -> Any:
    text = processor.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=add_generation_prompt,
    )
    kwargs: dict[str, Any] = {
        "text": [text],
        "padding": True,
        "return_tensors": "pt",
    }
    if images is not None:
        kwargs["images"] = images
    return processor(**kwargs)


def _canonicalize_adapter_artifacts(adapter_dir: Path) -> None:
    config_path = adapter_dir / "adapter_config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["base_model_name_or_path"] = contract.MODEL_ID
    config["revision"] = contract.MODEL_REVISION
    config_path.write_bytes(contract.artifact_json_bytes(config))
    readme = (
        "# MM-003 QLoRA SFT v2 Adapter\n\n"
        "This local research Adapter is bound to the frozen MM-003 post-training "
        "recovery v2 protocol. It is not approved for serving, promotion, "
        "commercial use, or Runtime execution.\n"
    ).encode("utf-8")
    (adapter_dir / "README.md").write_bytes(readme)


def _adapter_manifest(adapter_dir: Path) -> list[dict[str, Any]]:
    required = ["README.md", "adapter_config.json", "adapter_model.safetensors"]
    observed = sorted(path.name for path in adapter_dir.iterdir() if path.is_file())
    if observed != required:
        raise RuntimeError("Adapter file set differs from frozen protocol")
    adapter_config = json.loads(
        (adapter_dir / "adapter_config.json").read_text(encoding="utf-8")
    )
    if (
        adapter_config.get("base_model_name_or_path") != contract.MODEL_ID
        or adapter_config.get("revision") != contract.MODEL_REVISION
    ):
        raise RuntimeError("Adapter base model binding differs from frozen protocol")
    return [
        {
            "path": name,
            "bytes": (adapter_dir / name).stat().st_size,
            "sha256": contract.sha256_bytes((adapter_dir / name).read_bytes()),
        }
        for name in required
    ]


def _eval_screenshots(
    suite: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, bytes]]:
    cases = {case["case_id"]: case for case in suite["cases"]}
    receipts: list[dict[str, Any]] = []
    payloads: dict[str, bytes] = {}
    for case_id in contract.baseline.SCREENSHOT_CASES:
        expected = contract.baseline.render_case_png(cases[case_id])
        path = ROOT / contract.baseline.SCREENSHOT_ROOT / f"{case_id}.png"
        payload = base_runner._read_regular_file(
            path, f"MM-002 screenshot {case_id}", 4 * 1024 * 1024
        )
        if payload != expected:
            raise RuntimeError("MM-002 screenshot differs from frozen renderer")
        payloads[case_id] = payload
        receipts.append(
            {
                "case_id": case_id,
                "path": f"{contract.baseline.SCREENSHOT_ROOT}/{case_id}.png",
                "bytes": len(payload),
                "sha256": contract.sha256_bytes(payload),
            }
        )
    return receipts, payloads


def _validate_preregistered_inputs(
    preregistration: Mapping[str, Any], inputs: Mapping[str, Any]
) -> None:
    lineage = preregistration["source_lineage"]
    for key in (
        "train_receipt",
        "validation_receipt",
        "training_screenshot_receipts",
        "eval_screenshot_receipts",
        "isolation_audit",
    ):
        prereg_key = {
            "train_receipt": "training_data",
            "validation_receipt": "validation_data",
            "training_screenshot_receipts": "training_screenshots",
            "eval_screenshot_receipts": None,
            "isolation_audit": "eval_isolation",
        }[key]
        expected = (
            lineage["unchanged_mm002_eval"]["screenshots"]
            if prereg_key is None
            else lineage[prereg_key]
        )
        if inputs[key] != expected:
            raise RuntimeError(f"preregistered input differs: {key}")


def _validate_protocol_sources(
    preregistration: Mapping[str, Any],
) -> dict[str, str]:
    observed = protocol_source_hashes()
    registered = preregistration["source_lineage"]["protocol_sources"]
    for name, digest in observed.items():
        if registered[name] != {
            "path": contract.PROTOCOL_SOURCE_PATHS[name],
            "sha256": digest,
        }:
            raise RuntimeError(f"protocol source differs: {name}")
    return observed


def _validate_local_dependency_wheel() -> None:
    path = ROOT / contract.BITSANDBYTES_WHEEL["path"]
    payload = base_runner._read_regular_file(
        path, "bitsandbytes wheel", 64 * 1024 * 1024
    )
    if (
        len(payload) != contract.BITSANDBYTES_WHEEL["bytes"]
        or contract.sha256_bytes(payload) != contract.BITSANDBYTES_WHEEL["sha256"]
    ):
        raise RuntimeError("bitsandbytes wheel receipt mismatch")


def _load_ml_dependencies() -> tuple[Any, ...]:
    import bitsandbytes
    import torch
    from peft import (  # type: ignore[import-not-found]
        LoraConfig,
        PeftModel,
        TaskType,
        get_peft_model,
        prepare_model_for_kbit_training,
    )
    from PIL import Image
    from transformers import (  # type: ignore[import-untyped]
        AutoProcessor,
        BitsAndBytesConfig,
        Qwen2_5_VLForConditionalGeneration,
        get_cosine_schedule_with_warmup,
    )

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable")
    return (
        bitsandbytes,
        torch,
        Image,
        LoraConfig,
        TaskType,
        get_peft_model,
        PeftModel,
        prepare_model_for_kbit_training,
        AutoProcessor,
        Qwen2_5_VLForConditionalGeneration,
        BitsAndBytesConfig,
        get_cosine_schedule_with_warmup,
    )


def _quantization_config(torch: Any, config_class: Any) -> Any:
    return config_class(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )


def _enable_offline_execution() -> None:
    os.environ["HF_DATASETS_OFFLINE"] = "1"
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"


def _seed_all(torch: Any, seed: int) -> None:
    random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False


def _safe_exception_diagnostic(
    exc: Exception,
) -> tuple[str, str | None, str | None]:
    exception_type = type(exc).__name__
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,95}", exception_type) is None:
        exception_type = "Exception"
    if not isinstance(exc, contract.MM003PostTrainingProtocolError):
        return exception_type, None, None
    code = getattr(exc, "code", None)
    location = getattr(exc, "location", None)
    if (
        not isinstance(code, str)
        or re.fullmatch(r"[A-Z][A-Z0-9_]{0,95}", code) is None
        or not isinstance(location, str)
        or len(location) > 256
        or re.fullmatch(
            r"\$(?:\.[A-Za-z_][A-Za-z0-9_]*|\[[0-9]+\])*", location
        )
        is None
    ):
        return exception_type, None, None
    return exception_type, code, location


def _negative_result_claims() -> dict[str, bool]:
    return {
        "training_executed": False,
        "adapter_created": False,
        "adapter_independently_loadable": False,
        "model_evaluated": False,
        "quality_improved": False,
        "repeatability_established": False,
        "cross_machine_reproducibility": False,
        "portable_artifact": False,
        "commercial_use_eligible": False,
        "serving_eligible": False,
        "promotion_eligible": False,
        "runtime_eligible": False,
    }


def _mapping(value: object, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise RuntimeError(f"expected object at {location}")
    return value


if __name__ == "__main__":
    raise SystemExit(main())
