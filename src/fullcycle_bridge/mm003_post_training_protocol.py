"""Frozen, outcome-neutral QLoRA post-training protocol for MM-003."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, NoReturn, cast

from . import gui_grounding_eval
from . import mm003_baseline_protocol as base_v1
from . import mm003_baseline_protocol_v2 as baseline

PREREGISTRATION_VERSION = 1
DATASET_VERSION = 1
GATE_ID = "MM-003-small-vlm-post-training-protocol-v1"
EXECUTION_GATE_ID = "MM-003-small-vlm-post-training-execution-v1"
EXPERIMENT_ID = "mm003-qwen2.5-vl-3b-qlora-sft-v1"

MODEL_ID = baseline.MODEL_ID
MODEL_REVISION = baseline.MODEL_REVISION
MODEL_LICENSE = baseline.MODEL_LICENSE
MODEL_LICENSE_SCOPE = baseline.MODEL_LICENSE_SCOPE
MODEL_ARCHITECTURE = baseline.MODEL_ARCHITECTURE
MODEL_FILE_SIZES = baseline.MODEL_FILE_SIZES
MODEL_WEIGHT_SHA256 = baseline.MODEL_WEIGHT_SHA256
LOCKED_ENVIRONMENT = {
    **baseline.LOCKED_ENVIRONMENT,
    "bitsandbytes": "0.50.1",
}

PREREGISTRATION_PATH = "configs/mm003_small_vlm_post_training_protocol_v1.json"
TRAIN_DATASET_PATH = "fixtures/mm003_post_training_v1/train.json"
VALIDATION_DATASET_PATH = "fixtures/mm003_post_training_v1/validation.json"
TRAINING_SCREENSHOT_ROOT = "fixtures/mm003_post_training_v1/screenshots"
ADAPTER_OUTPUT_ROOT = "work/training-runs/mm003-qlora-sft-v1/adapter"
TRAINING_RUN_ARTIFACT = "work/training-runs/mm003-qlora-sft-v1/training-run.json"
PREDICTIONS_ARTIFACT = "work/training-runs/mm003-qlora-sft-v1/mm002-predictions.json"
EVIDENCE_ARTIFACT = "work/training-runs/mm003-qlora-sft-v1/evidence.json"
FAILURE_ARTIFACT = "work/training-runs/mm003-qlora-sft-v1/failure.json"

BITSANDBYTES_WHEEL = {
    "path": (
        "work/dependency-cache/mm003-qlora-bnb-0.50.1/"
        "bitsandbytes-0.50.1-py3-none-win_amd64.whl"
    ),
    "bytes": 37_961_070,
    "sha256": "sha256:86f76e8a3278fbbfc3fa0d79d1c4e706ebc214babd57f0ea30e2da509bbdaad5",
}

PROTOCOL_SOURCE_PATHS = {
    "base_contract_v1": "src/fullcycle_bridge/mm003_baseline_protocol.py",
    "base_contract_v2": "src/fullcycle_bridge/mm003_baseline_protocol_v2.py",
    "base_runner_v2": "scripts/run_mm003_multimodal_gui_action_baseline_v2.py",
    "base_scorer_v1": "src/fullcycle_bridge/gui_grounding_eval.py",
    "base_scorer_v2": "src/fullcycle_bridge/gui_grounding_eval_v2.py",
    "fixture_builder": "scripts/build_mm003_post_training_fixture.py",
    "post_training_contract": ("src/fullcycle_bridge/mm003_post_training_protocol.py"),
    "post_training_runner": "scripts/run_mm003_qlora_post_training.py",
    "qlora_backend_smoke": "scripts/smoke_mm003_qlora_backend.py",
    "training_lock": "requirements/mm003_qlora_training.lock",
}

BASELINE_V2_PREREGISTRATION = {
    "path": baseline.PREREGISTRATION_PATH,
    "bytes": 13_349,
    "sha256": "sha256:369c813dee44b14c6022eb90739bcd37f9f8de472e60a8cee88682454d135403",
}
BASELINE_V2_EVIDENCE = {
    "path": baseline.EVIDENCE_ARTIFACT_PATH,
    "bytes": 4_680,
    "sha256": "sha256:a0e3c2503e5bac13bf979c7721dab4350681a84883d749b94ef3ca204d2166fe",
    "classification": "local_small_vlm_baseline_established",
    "quality_result": "negative_baseline",
}

TRAIN_RECORDS = 18
VALIDATION_RECORDS = 9
SCREENSHOT_RECORDS = 18
IMAGE_WIDTH = 448
IMAGE_HEIGHT = 448
SYSTEM_PROMPT = baseline.SYSTEM_PROMPT
TRAINING_SEED = 20260817
ID_PATTERN = re.compile(r"[a-z0-9][a-z0-9._-]{0,95}")
SHA256_PATTERN = re.compile(r"sha256:[0-9a-f]{64}")

MM003PostTrainingProtocolError = base_v1.MM003ProtocolError
artifact_json_bytes = base_v1.artifact_json_bytes
canonical_json_bytes = base_v1.canonical_json_bytes
parse_strict_json_bytes = base_v1.parse_strict_json_bytes
sha256_bytes = base_v1.sha256_bytes


def expected_dataset(split: str) -> dict[str, Any]:
    """Build the exact reviewed synthetic train or validation split."""

    if split not in {"train", "validation"}:
        _fail("INVALID_SPLIT", "$.split")
    repeats = 2 if split == "train" else 1
    records: list[dict[str, Any]] = []
    index = 0
    for repeat in range(1, repeats + 1):
        for mode in ("uia_only", "screenshot_only", "fused"):
            for disposition in ("act", "reject", "fallback"):
                index += 1
                records.append(
                    _build_training_record(
                        split=split,
                        index=index,
                        repeat=repeat,
                        mode=mode,
                        disposition=disposition,
                    )
                )
    expected_count = TRAIN_RECORDS if split == "train" else VALIDATION_RECORDS
    if len(records) != expected_count:
        _fail("INVALID_RECORD_COUNT", "$.records")
    return {
        "mm003_post_training_dataset_version": DATASET_VERSION,
        "dataset_id": f"mm003-reviewed-synthetic-{split}-v1",
        "provenance": {
            "source": "deterministic_reviewed_synthetic_fixture",
            "synthetic_only": True,
            "real_content": False,
            "capture_adapter_used": False,
            "automatic_lane_a_export_used": False,
            "mm002_eval_gold_used": False,
            "model_output_has_execution_authority": False,
            "runtime_dispatch_required": True,
        },
        "split_policy": {
            "split": split,
            "optimizer_use": split == "train",
            "validation_only": split == "validation",
            "family_disjoint_from_mm002_eval": True,
            "content_disjoint_from_mm002_eval": True,
            "target_disjoint_from_mm002_eval": True,
            "screenshot_disjoint_from_mm002_eval": True,
        },
        "records": records,
    }


def validate_dataset(value: object, *, split: str) -> dict[str, Any]:
    expected = expected_dataset(split)
    if not isinstance(value, Mapping) or dict(value) != expected:
        _fail("DATASET_RECOMPUTATION_MISMATCH", f"$.{split}")
    for index, record in enumerate(expected["records"]):
        target = render_training_target(record)
        compiled = baseline.compile_raw_prediction(target, record)
        if compiled != record["target"]:
            _fail("TARGET_COMPILER_REJECTION", f"$.{split}.records[{index}]")
    return expected


def render_training_input(record: Mapping[str, Any]) -> str:
    filtered = baseline.filtered_model_input(record)
    return "SYNTHETIC_CASE=" + canonical_json_bytes(filtered).decode("utf-8").rstrip(
        "\n"
    )


def render_training_target(record: Mapping[str, Any]) -> str:
    target = _mapping(record.get("target"), "$.record.target")
    return json.dumps(
        target,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    )


def render_training_png(record: Mapping[str, Any]) -> bytes:
    """Render one deterministic image with the frozen baseline bitmap helpers."""

    mode = record.get("observation_mode")
    if mode not in {"screenshot_only", "fused"}:
        _fail("SCREENSHOT_NOT_REGISTERED", "$.record.observation_mode")
    case_id = str(record.get("case_id"))
    observation = _mapping(
        _mapping(record.get("model_input"), "$.record.model_input").get("observation"),
        "$.record.model_input.observation",
    )
    regions = _sequence(observation.get("screenshot_regions"), "$.screenshot_regions")
    pixels = bytearray((242, 245, 249) * (IMAGE_WIDTH * IMAGE_HEIGHT))
    base_v1._fill_rect(pixels, 0, 0, IMAGE_WIDTH, 42, (38, 50, 68))
    base_v1._draw_text(
        pixels,
        12,
        10,
        case_id.upper(),
        (255, 255, 255),
        2,
    )
    colors = ((44, 112, 190), (151, 83, 176), (46, 139, 87))
    for index, raw_region in enumerate(regions):
        region = _mapping(raw_region, f"$.screenshot_regions[{index}]")
        bbox = _sequence(region.get("bbox"), f"$.screenshot_regions[{index}].bbox")
        if len(bbox) != 4 or any(type(item) is not int for item in bbox):
            _fail("INVALID_SCREENSHOT_BBOX", f"$.screenshot_regions[{index}].bbox")
        x1, y1, x2, y2 = (int(item) for item in bbox)
        color = colors[index % len(colors)]
        base_v1._fill_rect(pixels, x1, y1, x2, y2, (255, 255, 255))
        base_v1._stroke_rect(pixels, x1, y1, x2, y2, color, 3)
        base_v1._draw_text(
            pixels,
            x1 + 8,
            y1 + 10,
            str(region.get("label", "")).upper(),
            (26, 32, 44),
            2,
        )
        if region.get("occluded") is True:
            base_v1._fill_rect(
                pixels,
                x1 + (x2 - x1) // 2,
                y1 + 5,
                x2 - 5,
                y2 - 5,
                (55, 58, 64),
            )
    return base_v1._encode_png(IMAGE_WIDTH, IMAGE_HEIGHT, bytes(pixels))


def expected_screenshot_receipts() -> list[dict[str, Any]]:
    receipts: list[dict[str, Any]] = []
    for split in ("train", "validation"):
        for record in expected_dataset(split)["records"]:
            if record["observation_mode"] == "uia_only":
                continue
            payload = render_training_png(record)
            receipts.append(
                {
                    "case_id": record["case_id"],
                    "path": (
                        f"{TRAINING_SCREENSHOT_ROOT}/{split}/{record['case_id']}.png"
                    ),
                    "bytes": len(payload),
                    "sha256": sha256_bytes(payload),
                }
            )
    if len(receipts) != SCREENSHOT_RECORDS:
        _fail("SCREENSHOT_COUNT_MISMATCH", "$.screenshots")
    return receipts


def audit_eval_isolation(
    *,
    train: Mapping[str, Any],
    validation: Mapping[str, Any],
    eval_suite: Mapping[str, Any],
    eval_screenshot_payloads: Mapping[str, bytes],
) -> dict[str, Any]:
    """Prove exact identity separation without making semantic quality claims."""

    train_validated = validate_dataset(train, split="train")
    validation_validated = validate_dataset(validation, split="validation")
    gui_grounding_eval.validate_suite(eval_suite)
    training_records = [
        *train_validated["records"],
        *validation_validated["records"],
    ]
    eval_records = cast(list[Mapping[str, Any]], eval_suite["cases"])

    def values(records: Sequence[Mapping[str, Any]], key: str) -> set[str]:
        return {str(record[key]) for record in records}

    def digests(records: Sequence[Mapping[str, Any]], key: str) -> set[str]:
        return {
            sha256_bytes(canonical_json_bytes(_mapping(record[key], f"$.{key}")))
            for record in records
        }

    overlaps = {
        "case_ids": sorted(
            values(training_records, "case_id") & values(eval_records, "case_id")
        ),
        "family_ids": sorted(
            values(training_records, "family_id") & values(eval_records, "family_id")
        ),
        "instructions": sorted(
            {
                str(_mapping(record["model_input"], "$.model_input")["instruction"])
                for record in training_records
            }
            & {
                str(_mapping(record["model_input"], "$.model_input")["instruction"])
                for record in eval_records
            }
        ),
        "model_inputs": sorted(
            digests(training_records, "model_input")
            & digests(eval_records, "model_input")
        ),
        "targets": sorted(
            digests(training_records, "target") & digests(eval_records, "gold")
        ),
        "screenshots": sorted(
            {receipt["sha256"] for receipt in expected_screenshot_receipts()}
            & {sha256_bytes(payload) for payload in eval_screenshot_payloads.values()}
        ),
    }
    train_families = values(train_validated["records"], "family_id")
    validation_families = values(validation_validated["records"], "family_id")
    overlaps["train_validation_families"] = sorted(train_families & validation_families)
    passed = all(not value for value in overlaps.values())
    return {
        "eval_case_count": len(eval_records),
        "overlaps": overlaps,
        "passed": passed,
        "train_records": len(train_validated["records"]),
        "validation_records": len(validation_validated["records"]),
    }


def expected_preregistration(
    *,
    freeze_status: str,
    model_files: Sequence[Mapping[str, Any]],
    train_receipt: Mapping[str, Any],
    validation_receipt: Mapping[str, Any],
    screenshot_receipts: Sequence[Mapping[str, Any]],
    eval_screenshot_receipts: Sequence[Mapping[str, Any]],
    source_hashes: Mapping[str, str],
    isolation_audit: Mapping[str, Any],
) -> dict[str, Any]:
    model_manifest = base_v1._validate_model_manifest(model_files)
    _validate_receipt(train_receipt, TRAIN_DATASET_PATH, "$.train")
    _validate_receipt(validation_receipt, VALIDATION_DATASET_PATH, "$.validation")
    if list(screenshot_receipts) != expected_screenshot_receipts():
        _fail("TRAINING_SCREENSHOT_RECEIPT_MISMATCH", "$.training_screenshots")
    base_v1._validate_screenshot_manifest(eval_screenshot_receipts)
    if set(source_hashes) != set(PROTOCOL_SOURCE_PATHS):
        _fail("INVALID_SOURCE_KEYS", "$.protocol_sources")
    for name, digest in source_hashes.items():
        _validate_sha256(digest, f"$.protocol_sources.{name}")
    if dict(isolation_audit) != {
        "eval_case_count": 9,
        "overlaps": {
            "case_ids": [],
            "family_ids": [],
            "instructions": [],
            "model_inputs": [],
            "targets": [],
            "screenshots": [],
            "train_validation_families": [],
        },
        "passed": True,
        "train_records": TRAIN_RECORDS,
        "validation_records": VALIDATION_RECORDS,
    }:
        _fail("EVAL_ISOLATION_AUDIT_FAILED", "$.eval_isolation")
    return {
        "preregistration_version": PREREGISTRATION_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "gate_id": GATE_ID,
        "freeze_status": freeze_status,
        "decision": "outcome_neutral_qlora_training_and_measurement_protocol",
        "authority_contract": {
            "model_output_has_execution_authority": False,
            "direct_desktop_execution": False,
            "runtime_policy_or_approval_bypass": False,
            "runtime_integration_changed": False,
        },
        "model": {
            "repo_id": MODEL_ID,
            "revision": MODEL_REVISION,
            "license": MODEL_LICENSE,
            "license_scope": MODEL_LICENSE_SCOPE,
            "architecture": MODEL_ARCHITECTURE,
            "files": model_manifest,
        },
        "source_lineage": {
            "protocol_sources": {
                name: {
                    "path": PROTOCOL_SOURCE_PATHS[name],
                    "sha256": source_hashes[name],
                }
                for name in sorted(PROTOCOL_SOURCE_PATHS)
            },
            "negative_baseline": BASELINE_V2_EVIDENCE,
            "baseline_preregistration": BASELINE_V2_PREREGISTRATION,
            "training_data": dict(train_receipt),
            "validation_data": dict(validation_receipt),
            "training_screenshots": list(screenshot_receipts),
            "unchanged_mm002_eval": {
                "path": baseline.MM002_SUITE_PATH,
                "file_sha256": baseline.MM002_SUITE_FILE_SHA256,
                "canonical_sha256": baseline.MM002_SUITE_CANONICAL_SHA256,
                "case_order": list(baseline.CASE_ORDER),
                "screenshots": list(eval_screenshot_receipts),
            },
            "eval_isolation": dict(isolation_audit),
            "bitsandbytes_wheel": BITSANDBYTES_WHEEL,
        },
        "environment": LOCKED_ENVIRONMENT,
        "compatibility_smoke": {
            "completed_before_freeze": True,
            "eval_data_used": False,
            "adapter_saved": False,
            "linear_4bit_modules": 414,
            "trainable_parameters": 7_372_800,
            "gradient_checkpointing": True,
            "finite_loss": True,
            "nonzero_finite_lora_gradient": True,
            "peak_cuda_allocated_bytes": 3_941_332_480,
            "peak_cuda_reserved_bytes": 4_273_995_776,
        },
        "training_protocol": {
            "seed": TRAINING_SEED,
            "quantization": {
                "load_in_4bit": True,
                "type": "nf4",
                "double_quant": True,
                "compute_dtype": "bfloat16",
            },
            "lora": {
                "rank": 16,
                "alpha": 32,
                "dropout": 0.05,
                "bias": "none",
                "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj"],
            },
            "optimizer": "adamw",
            "learning_rate": 0.0002,
            "weight_decay": 0.0,
            "scheduler": "cosine",
            "warmup_ratio": 0.1,
            "epochs": 3,
            "micro_batch_size": 1,
            "gradient_accumulation_steps": 3,
            "effective_batch_size": 3,
            "gradient_checkpointing": True,
            "max_grad_norm": 1.0,
            "train_on_prompt": False,
            "image_policy": {
                "min_pixels": 256 * 28 * 28,
                "max_pixels": 1280 * 28 * 28,
                "use_fast": False,
            },
            "network_used": False,
            "accepted_training_runs": 1,
            "retry_count": 0,
        },
        "evaluation_protocol": {
            "fresh_base_loads_after_training": 1,
            "independent_adapter_loads": 1,
            "full_eval_runs": 1,
            "generate_calls": 9,
            "retry_count": 0,
            "network_used": False,
            "suite_prompt_compiler_generation_unchanged": True,
            "quality_threshold_required": False,
        },
        "outputs": {
            "adapter_directory": ADAPTER_OUTPUT_ROOT,
            "required_adapter_files": [
                "README.md",
                "adapter_config.json",
                "adapter_model.safetensors",
            ],
            "training_run": TRAINING_RUN_ARTIFACT,
            "predictions": PREDICTIONS_ARTIFACT,
            "evidence": EVIDENCE_ARTIFACT,
            "failure": FAILURE_ARTIFACT,
            "writes_are_exclusive": True,
        },
        "resource_caps": {
            "elapsed_seconds": 1800.0,
            "peak_gpu_allocated_bytes": 16_500_000_000,
            "peak_gpu_reserved_bytes": 16_500_000_000,
        },
        "formal_gate": {
            "required_gates": [
                "protocol_integrity",
                "exact_model_files",
                "locked_environment",
                "training_fixture_integrity",
                "eval_isolation",
                "offline_single_training_run",
                "adapter_artifact_integrity",
                "independent_adapter_load",
                "unchanged_mm002_eval",
                "total_scoring",
                "resource_caps",
                "fail_closed_claims",
            ],
            "quality_threshold_required": False,
            "formal_gate_passed": False,
        },
        "claims": {
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
        },
        "next_gate_after_freeze": {
            "gate_id": EXECUTION_GATE_ID,
            "action": (
                "execute the frozen QLoRA training exactly once, save the Adapter, "
                "independently reload base plus Adapter, and run the unchanged "
                "nine-case MM-002 evaluation with zero retries"
            ),
        },
        "runtime_eligible": False,
    }


def validate_preregistration(
    value: Mapping[str, Any], *, require_frozen: bool = True
) -> dict[str, Any]:
    model = _mapping(value.get("model"), "$.model")
    lineage = _mapping(value.get("source_lineage"), "$.source_lineage")
    sources = _mapping(lineage.get("protocol_sources"), "$.protocol_sources")
    source_hashes = {
        name: str(_mapping(sources.get(name), f"$.protocol_sources.{name}")["sha256"])
        for name in PROTOCOL_SOURCE_PATHS
    }
    expected = expected_preregistration(
        freeze_status=str(value.get("freeze_status")),
        model_files=_sequence(model.get("files"), "$.model.files"),
        train_receipt=_mapping(lineage.get("training_data"), "$.training_data"),
        validation_receipt=_mapping(
            lineage.get("validation_data"), "$.validation_data"
        ),
        screenshot_receipts=_sequence(
            lineage.get("training_screenshots"), "$.training_screenshots"
        ),
        eval_screenshot_receipts=_sequence(
            _mapping(lineage.get("unchanged_mm002_eval"), "$.unchanged_mm002_eval").get(
                "screenshots"
            ),
            "$.unchanged_mm002_eval.screenshots",
        ),
        source_hashes=source_hashes,
        isolation_audit=_mapping(lineage.get("eval_isolation"), "$.eval_isolation"),
    )
    if dict(value) != expected:
        _fail("PREREGISTRATION_RECOMPUTATION_MISMATCH", "$.preregistration")
    if require_frozen and value.get("freeze_status") != "frozen":
        _fail("PREREGISTRATION_NOT_FROZEN", "$.freeze_status")
    return expected


def file_receipt(path: Path, *, relative_path: str) -> dict[str, Any]:
    payload = path.read_bytes()
    return {
        "path": relative_path,
        "bytes": len(payload),
        "sha256": sha256_bytes(payload),
    }


def _build_training_record(
    *,
    split: str,
    index: int,
    repeat: int,
    mode: str,
    disposition: str,
) -> dict[str, Any]:
    token = f"{split[0]}{index:02d}"
    case_id = f"pt-{split}-{index:03d}"
    x1 = 34 + (index * 29) % 170
    y1 = 72 + (index * 37) % 190
    bbox = [x1, y1, x1 + 132, y1 + 62]
    distractor_bbox = [268, 318 - (index % 3) * 54, 412, 366 - (index % 3) * 54]
    target_ref = f"ref-open-{token}"
    target_label = f"OPEN {token}"
    if disposition == "act":
        instruction = f"Activate the reviewed synthetic {target_label} control."
        reason = None
    elif disposition == "reject":
        instruction = f"Activate the expired synthetic {target_label} reference."
        reason = "stale_ref"
    else:
        instruction = f"Activate the absent synthetic {target_label} control."
        reason = "insufficient_grounding"
    uia_controls: list[dict[str, Any]] = []
    screenshot_regions: list[dict[str, Any]] = []
    if mode in {"uia_only", "fused"}:
        uia_controls = [
            {
                "ref": target_ref,
                "role": "button",
                "name": target_label,
                "state": "enabled" if disposition == "act" else "stale",
                "bbox": bbox,
            },
            {
                "ref": f"ref-close-{token}",
                "role": "button",
                "name": f"CLOSE {token}",
                "state": "enabled",
                "bbox": distractor_bbox,
            },
        ]
    if mode in {"screenshot_only", "fused"}:
        screenshot_regions = [
            {
                "label": target_label
                if disposition != "fallback"
                else f"OTHER {token}",
                "bbox": bbox,
                "occluded": disposition == "reject",
            },
            {
                "label": f"CLOSE {token}",
                "bbox": distractor_bbox,
                "occluded": False,
            },
        ]
    if disposition == "act":
        target = {
            "case_id": case_id,
            "disposition": "act",
            "tool": "click",
            "arguments": {"button": "left"},
            "ref": target_ref if mode in {"uia_only", "fused"} else None,
            "bbox": bbox if mode in {"screenshot_only", "fused"} else None,
            "reason": None,
        }
    else:
        target = {
            "case_id": case_id,
            "disposition": disposition,
            "tool": None,
            "arguments": None,
            "ref": None,
            "bbox": None,
            "reason": reason,
        }
    return {
        "case_id": case_id,
        "family_id": f"pt-{split}-family-{index:03d}",
        "observation_mode": mode,
        "training_repeat_group": repeat,
        "model_input": {
            "instruction": instruction,
            "available_tools": ["click"],
            "observation": {
                "uia_controls": uia_controls,
                "screenshot_regions": screenshot_regions,
                "ocr_text": (
                    f"{target_label} CLOSE {token}"
                    if disposition != "fallback"
                    else f"OTHER {token} CLOSE {token}"
                ),
                "grounding_cue": {
                    "ref": target_ref if mode in {"uia_only", "fused"} else None,
                    "bbox": bbox if mode in {"screenshot_only", "fused"} else None,
                },
            },
        },
        "target": target,
    }


def _validate_receipt(
    receipt: Mapping[str, Any], expected_path: str, location: str
) -> None:
    if set(receipt) != {"path", "bytes", "sha256"}:
        _fail("INVALID_RECEIPT_FIELDS", location)
    if receipt.get("path") != expected_path:
        _fail("RECEIPT_PATH_MISMATCH", f"{location}.path")
    if type(receipt.get("bytes")) is not int or int(receipt["bytes"]) <= 0:
        _fail("INVALID_RECEIPT_BYTES", f"{location}.bytes")
    _validate_sha256(receipt.get("sha256"), f"{location}.sha256")


def _validate_sha256(value: object, location: str) -> None:
    if not isinstance(value, str) or SHA256_PATTERN.fullmatch(value) is None:
        _fail("INVALID_SHA256", location)


def _mapping(value: object, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail("EXPECTED_OBJECT", location)
    return value


def _sequence(value: object, location: str) -> Sequence[Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        _fail("EXPECTED_ARRAY", location)
    return cast(Sequence[Mapping[str, Any]], value)


def _fail(code: str, location: str) -> NoReturn:
    raise MM003PostTrainingProtocolError(code, location)


__all__ = [
    "EXECUTION_GATE_ID",
    "GATE_ID",
    "LOCKED_ENVIRONMENT",
    "MODEL_ID",
    "MODEL_REVISION",
    "PREREGISTRATION_PATH",
    "PROTOCOL_SOURCE_PATHS",
    "TRAIN_DATASET_PATH",
    "TRAINING_SCREENSHOT_ROOT",
    "VALIDATION_DATASET_PATH",
    "artifact_json_bytes",
    "audit_eval_isolation",
    "expected_dataset",
    "expected_preregistration",
    "expected_screenshot_receipts",
    "file_receipt",
    "parse_strict_json_bytes",
    "render_training_input",
    "render_training_png",
    "render_training_target",
    "sha256_bytes",
    "validate_dataset",
    "validate_preregistration",
]
