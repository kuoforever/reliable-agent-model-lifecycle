"""Frozen MM-003 small-VLM baseline protocol and deterministic input helpers."""

from __future__ import annotations

import binascii
import hashlib
import json
import math
import re
import struct
import zlib
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, NoReturn

PREREGISTRATION_VERSION = 1
GATE_ID = "MM-003-multimodal-gui-action-model-v1"
EXPERIMENT_ID = "mm003-qwen2.5-vl-3b-instruct-baseline-v1"
MODEL_ID = "Qwen/Qwen2.5-VL-3B-Instruct"
MODEL_REVISION = "66285546d2b821cf421d4f5eb2576359d3770cd3"
MODEL_LICENSE = "qwen-research"
MODEL_LICENSE_SCOPE = "non_commercial_research_or_evaluation_only"
MODEL_ARCHITECTURE = "Qwen2_5_VLForConditionalGeneration"
MODEL_WEIGHT_SHA256 = {
    "model-00001-of-00002.safetensors": (
        "sha256:41a8895c164b4d32bae6b302f4603fcbc1797f32dafa45c7e9bcda23c6755df8"
    ),
    "model-00002-of-00002.safetensors": (
        "sha256:365531ff8752420e89dee707b79d021fb2d6e25abafe486f080555a4fe6972e4"
    ),
}
MODEL_FILE_SIZES = {
    ".gitattributes": 1519,
    "LICENSE": 7387,
    "README.md": 18276,
    "chat_template.json": 1050,
    "config.json": 1373,
    "generation_config.json": 216,
    "merges.txt": 1671839,
    "model-00001-of-00002.safetensors": 3982649232,
    "model-00002-of-00002.safetensors": 3526688744,
    "model.safetensors.index.json": 65448,
    "preprocessor_config.json": 350,
    "tokenizer.json": 7031645,
    "tokenizer_config.json": 5702,
    "vocab.json": 2776833,
}

MM002_SUITE_PATH = "fixtures/gui_grounding_eval_v1/valid/suite.json"
MM002_SUITE_FILE_SHA256 = (
    "sha256:c59ea8314cad0ae936fadd6648cc270e3332d40115ed1ca6f9c00730c85c7b2e"
)
MM002_SUITE_CANONICAL_SHA256 = (
    "sha256:0774ae2c4d835ab613f46344b33ec0dac5ec1bf12d38db72fca2fdde94431b00"
)
MM002_SCHEMA_PATH = "schemas/gui_grounding_predictions_v1.schema.json"
MM002_SCHEMA_SHA256 = (
    "sha256:a4ab293cb0831475899d208b06a4a7c2835405a112538695f83ac3a595357b46"
)
PREREGISTRATION_PATH = "configs/mm003_multimodal_gui_action_model_baseline_v1.json"
SCREENSHOT_ROOT = "fixtures/mm003_baseline_v1/screenshots"
RUN_ARTIFACT_PATH = "baseline/mm003-qwen2.5-vl-3b-baseline-v1-run.json"
PREDICTIONS_ARTIFACT_PATH = "baseline/mm003-qwen2.5-vl-3b-baseline-v1-predictions.json"
EVIDENCE_ARTIFACT_PATH = "baseline/mm003-qwen2.5-vl-3b-baseline-v1.json"
CONTRACT_SOURCE_PATH = "src/fullcycle_bridge/mm003_baseline_protocol.py"
RUNNER_SOURCE_PATH = "scripts/run_mm003_multimodal_gui_action_baseline.py"
SCORER_SOURCE_PATH = "src/fullcycle_bridge/gui_grounding_eval.py"
PROTOCOL_SOURCE_PATHS = {
    "contract": CONTRACT_SOURCE_PATH,
    "runner": RUNNER_SOURCE_PATH,
    "scorer": SCORER_SOURCE_PATH,
}

LOCKED_ENVIRONMENT = {
    "accelerate": "1.3.0",
    "compute_capability": "8.9",
    "device": "cuda",
    "gpu": "NVIDIA GeForce RTX 4090 Laptop GPU",
    "gpu_vram_bytes": 17_170_956_288,
    "huggingface_hub": "0.29.3",
    "nvidia_driver": "596.49",
    "pillow": "11.3.0",
    "platform_machine": "AMD64",
    "platform_release": "11",
    "platform_system": "Windows",
    "platform_version": "10.0.26200",
    "python": "3.12.12",
    "safetensors": "0.5.3",
    "tokenizers": "0.21.4",
    "torch": "2.6.0+cu124",
    "transformers": "4.49.0",
}
CASE_ORDER = tuple(f"ground-{index:03d}" for index in range(1, 10))
CASE_MODES = {
    "ground-001": "uia_only",
    "ground-002": "screenshot_only",
    "ground-003": "fused",
    "ground-004": "uia_only",
    "ground-005": "screenshot_only",
    "ground-006": "fused",
    "ground-007": "fused",
    "ground-008": "screenshot_only",
    "ground-009": "uia_only",
}
SCREENSHOT_CASES = tuple(
    case_id for case_id in CASE_ORDER if CASE_MODES[case_id] != "uia_only"
)
MAX_JSON_BYTES = 4 * 1024 * 1024
SHA256_PATTERN = re.compile(r"sha256:[0-9a-f]{64}")
IDENTIFIER_PATTERN = re.compile(r"[a-z0-9][a-z0-9._-]{0,95}")
PNG_WIDTH = 1280
PNG_HEIGHT = 900

SYSTEM_PROMPT = """You generate a candidate GUI action for evaluation only.
You never execute actions. Use only the supplied synthetic observation.
Return exactly one JSON object and no prose with these keys:
case_id, disposition, tool, arguments, ref, bbox, reason.
disposition is act, reject, or fallback. For act, tool must be click and
arguments must be {\"button\":\"left\"}; provide the required ref and/or bbox.
For reject or fallback, tool, arguments, ref, and bbox must be null and reason
must be a short snake_case identifier. Never invent unavailable evidence."""


class MM003ProtocolError(ValueError):
    """Raised when a frozen protocol, input, or compiled output drifts."""

    def __init__(self, code: str, location: str, detail: str = "") -> None:
        self.code = code
        self.location = location
        self.detail = detail
        message = f"{code} at {location}"
        if detail:
            message += f": {detail}"
        super().__init__(message)


def artifact_json_bytes(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    ).encode("utf-8")


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def parse_strict_json_bytes(payload: bytes, *, location: str) -> Any:
    if not payload or len(payload) > MAX_JSON_BYTES:
        _fail("INVALID_JSON_SIZE", location)
    try:
        value = json.loads(
            payload,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise MM003ProtocolError("INVALID_JSON", location, str(exc)) from exc
    _validate_finite(value, location)
    return value


def expected_preregistration(
    *,
    freeze_status: str,
    model_files: Sequence[Mapping[str, Any]],
    screenshot_files: Sequence[Mapping[str, Any]],
    protocol_source_hashes: Mapping[str, str],
) -> dict[str, Any]:
    """Construct the complete outcome-neutral protocol from validated receipts."""

    if freeze_status not in {"draft", "frozen"}:
        _fail("INVALID_FREEZE_STATUS", "$.freeze_status")
    model_manifest = _validate_model_manifest(model_files)
    screenshot_manifest = _validate_screenshot_manifest(screenshot_files)
    if set(protocol_source_hashes) != set(PROTOCOL_SOURCE_PATHS):
        _fail("INVALID_SOURCE_KEYS", "$.source_lineage.protocol_sources")
    for name, digest in protocol_source_hashes.items():
        _sha256(digest, f"$.source_lineage.protocol_sources.{name}.sha256")

    return {
        "preregistration_version": PREREGISTRATION_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "gate_id": GATE_ID,
        "freeze_status": freeze_status,
        "scope": {
            "decision": "local_small_vlm_baseline_measurement_only",
            "case_count": 9,
            "observation_mode_counts": {
                "fused": 3,
                "screenshot_only": 3,
                "uia_only": 3,
            },
            "quality_threshold_registered": False,
            "post_training": False,
            "real_content": False,
            "direct_execution": False,
            "runtime_change": False,
        },
        "model": {
            "repo_id": MODEL_ID,
            "revision": MODEL_REVISION,
            "architecture": MODEL_ARCHITECTURE,
            "parameter_band": "0.5B-3B",
            "license": MODEL_LICENSE,
            "license_scope": MODEL_LICENSE_SCOPE,
            "backend": "transformers",
            "dtype": "bfloat16",
            "attention_implementation": "sdpa",
            "local_files_only_during_execution": True,
            "files": model_manifest,
        },
        "source_lineage": {
            "mm002_suite": {
                "path": MM002_SUITE_PATH,
                "file_sha256": MM002_SUITE_FILE_SHA256,
                "canonical_sha256": MM002_SUITE_CANONICAL_SHA256,
                "split": "eval",
                "training_use_prohibited": True,
                "gold_excluded_from_prompt": True,
            },
            "mm002_prediction_schema": {
                "path": MM002_SCHEMA_PATH,
                "sha256": MM002_SCHEMA_SHA256,
            },
            "protocol_sources": {
                name: {
                    "path": PROTOCOL_SOURCE_PATHS[name],
                    "sha256": protocol_source_hashes[name],
                }
                for name in sorted(PROTOCOL_SOURCE_PATHS)
            },
            "screenshots": screenshot_manifest,
        },
        "execution_protocol": {
            "environment": dict(LOCKED_ENVIRONMENT),
            "fresh_model_loads": 1,
            "full_eval_runs": 1,
            "generate_calls": 9,
            "retry_count": 0,
            "case_order": list(CASE_ORDER),
            "case_modes": dict(CASE_MODES),
            "history_steps": 0,
            "prompt_template": SYSTEM_PROMPT,
            "prompt_payload": "filtered_model_input_without_gold_or_raw_screenshot_regions",
            "image_policy": {
                "width": PNG_WIDTH,
                "height": PNG_HEIGHT,
                "uia_only_image_count": 0,
                "screenshot_only_image_count": 3,
                "fused_image_count": 3,
                "min_pixels": 256 * 28 * 28,
                "max_pixels": 1280 * 28 * 28,
                "use_fast": False,
                "full_synthetic_frame": True,
                "crop_used": False,
            },
            "generation": {
                "do_sample": False,
                "max_new_tokens": 256,
                "repetition_penalty": 1.05,
                "temperature": None,
                "use_cache": True,
                "seed": 20260817,
            },
            "compiler": {
                "json_object_extraction": "first_json_object",
                "schema_validation": "strict_no_type_coercion",
                "invalid_output_disposition": "fallback",
                "invalid_output_reason": "model_output_invalid",
            },
            "network_allowed_during_model_materialization": True,
            "network_allowed_during_execution": False,
            "outputs": {
                "run": RUN_ARTIFACT_PATH,
                "predictions": PREDICTIONS_ARTIFACT_PATH,
                "evidence": EVIDENCE_ARTIFACT_PATH,
            },
        },
        "measurements": {
            "overall_and_per_mode": [
                "grounding_accuracy",
                "mean_iou",
                "action_accuracy",
                "tool_accuracy",
                "argument_exact_match",
                "stale_ref_rejection",
                "coordinate_ref_disagreement_rejection",
            ],
            "operational": [
                "candidate_steps",
                "fallback_rate",
                "latency_seconds",
                "peak_gpu_allocated_bytes",
                "peak_gpu_reserved_bytes",
            ],
        },
        "resource_caps": {
            "elapsed_seconds": 1200.0,
            "peak_gpu_allocated_bytes": 16_500_000_000,
            "peak_gpu_reserved_bytes": 16_500_000_000,
        },
        "formal_gate": {
            "requires_protocol_integrity": True,
            "requires_exact_model_files": True,
            "requires_exact_synthetic_inputs": True,
            "requires_locked_environment": True,
            "requires_one_complete_nine_case_run": True,
            "requires_zero_retries": True,
            "requires_offline_execution": True,
            "requires_resource_caps": True,
            "requires_prediction_schema_validity": True,
            "quality_threshold_required": False,
        },
        "constraints": {
            "adapter_created": False,
            "training": False,
            "eval_gold_used_for_training": False,
            "model_output_has_execution_authority": False,
            "runtime_integration": False,
            "mcp_integration": False,
            "serving_integration": False,
            "promotion_decision": False,
            "commercial_use_allowed_by_this_gate": False,
        },
        "claims": {
            "baseline_executed": False,
            "model_evaluated": False,
            "post_training_complete": False,
            "adapter_loadable": False,
            "real_content_collected": False,
            "cross_machine_reproducibility_established": False,
            "portable_package_eligible": False,
            "serving_readiness_established": False,
            "artifact_promotion_allowed": False,
            "runtime_eligible": False,
        },
        "next_gate_after_freeze": {
            "gate_id": "MM-003-local-small-vlm-baseline-execution-v1",
            "action": (
                "execute the frozen nine-case local baseline exactly once and "
                "record raw outputs, compiled predictions, metrics, latency, and GPU memory"
            ),
        },
        "runtime_eligible": False,
    }


def validate_preregistration(
    value: Mapping[str, Any], *, require_frozen: bool = True
) -> dict[str, Any]:
    """Recompute the protocol while treating only frozen content receipts as inputs."""

    model = _mapping(value.get("model"), "$.model")
    lineage = _mapping(value.get("source_lineage"), "$.source_lineage")
    sources = _mapping(
        lineage.get("protocol_sources"), "$.source_lineage.protocol_sources"
    )
    hashes: dict[str, str] = {}
    for name, path in PROTOCOL_SOURCE_PATHS.items():
        receipt = _mapping(
            sources.get(name), f"$.source_lineage.protocol_sources.{name}"
        )
        if receipt.get("path") != path:
            _fail(
                "SOURCE_PATH_MISMATCH", f"$.source_lineage.protocol_sources.{name}.path"
            )
        digest = receipt.get("sha256")
        _sha256(digest, f"$.source_lineage.protocol_sources.{name}.sha256")
        hashes[name] = str(digest)
    status = value.get("freeze_status")
    expected = expected_preregistration(
        freeze_status=str(status),
        model_files=_sequence(model.get("files"), "$.model.files"),
        screenshot_files=_sequence(
            lineage.get("screenshots"), "$.source_lineage.screenshots"
        ),
        protocol_source_hashes=hashes,
    )
    if dict(value) != expected:
        _fail("PREREGISTRATION_RECOMPUTATION_MISMATCH", "$.preregistration")
    if require_frozen and status != "frozen":
        _fail("PREREGISTRATION_NOT_FROZEN", "$.freeze_status")
    return expected


def filtered_model_input(case: Mapping[str, Any]) -> dict[str, Any]:
    """Return the exact prompt payload without gold or structured image regions."""

    case_id = case.get("case_id")
    mode = case.get("observation_mode")
    if case_id not in CASE_MODES or CASE_MODES[case_id] != mode:
        _fail("CASE_MODE_MISMATCH", "$.case")
    model_input = _mapping(case.get("model_input"), "$.case.model_input")
    observation = _mapping(
        model_input.get("observation"), "$.case.model_input.observation"
    )
    filtered_observation: dict[str, Any] = {
        "ocr_text": observation.get("ocr_text"),
        "grounding_cue": observation.get("grounding_cue"),
    }
    if mode in {"uia_only", "fused"}:
        filtered_observation["uia_controls"] = observation.get("uia_controls")
    return {
        "case_id": case_id,
        "observation_mode": mode,
        "instruction": model_input.get("instruction"),
        "available_tools": model_input.get("available_tools"),
        "observation": filtered_observation,
    }


def build_user_prompt(case: Mapping[str, Any]) -> str:
    payload = filtered_model_input(case)
    return "SYNTHETIC_CASE=" + canonical_json_bytes(payload).decode("utf-8").rstrip(
        "\n"
    )


def compile_raw_prediction(raw_output: str, case: Mapping[str, Any]) -> dict[str, Any]:
    """Compile one raw model output or fail closed to a deterministic fallback."""

    case_id = case.get("case_id")
    if not isinstance(raw_output, str) or not isinstance(case_id, str):
        return _fallback_record(str(case_id))
    try:
        start = raw_output.index("{")
        parsed, _ = json.JSONDecoder(
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_constant,
        ).raw_decode(raw_output[start:])
        record = _mapping(parsed, "$.model_output")
        _validate_compiled_record(record, case_id)
        return dict(record)
    except (ValueError, json.JSONDecodeError, MM003ProtocolError):
        return _fallback_record(case_id)


def render_case_png(case: Mapping[str, Any]) -> bytes:
    """Render one deterministic synthetic screenshot without Pillow or host fonts."""

    case_id = case.get("case_id")
    if case_id not in SCREENSHOT_CASES:
        _fail("SCREENSHOT_NOT_REGISTERED", "$.case.case_id", repr(case_id))
    observation = _mapping(
        _mapping(case.get("model_input"), "$.case.model_input").get("observation"),
        "$.case.model_input.observation",
    )
    regions = _sequence(observation.get("screenshot_regions"), "$.screenshot_regions")
    pixels = bytearray((242, 245, 249) * (PNG_WIDTH * PNG_HEIGHT))
    _fill_rect(pixels, 0, 0, PNG_WIDTH, 48, (38, 50, 68))
    _draw_text(pixels, 18, 14, f"SYNTHETIC {case_id}".upper(), (255, 255, 255), 3)
    colors = ((44, 112, 190), (151, 83, 176), (46, 139, 87))
    for index, raw_region in enumerate(regions):
        region = _mapping(raw_region, f"$.screenshot_regions[{index}]")
        bbox = _sequence(region.get("bbox"), f"$.screenshot_regions[{index}].bbox")
        if len(bbox) != 4 or any(type(item) is not int for item in bbox):
            _fail("INVALID_SCREENSHOT_BBOX", f"$.screenshot_regions[{index}].bbox")
        x1, y1, x2, y2 = (int(item) for item in bbox)
        color = colors[index % len(colors)]
        _fill_rect(pixels, x1, y1, x2, y2, (255, 255, 255))
        _stroke_rect(pixels, x1, y1, x2, y2, color, 4)
        label = str(region.get("label", "")).upper()
        _draw_text(pixels, x1 + 10, y1 + 12, label, (26, 32, 44), 3)
        if region.get("occluded") is True:
            overlay_start = x1 + (x2 - x1) // 2
            _fill_rect(pixels, overlay_start, y1 + 6, x2 - 6, y2 - 6, (55, 58, 64))
    return _encode_png(PNG_WIDTH, PNG_HEIGHT, bytes(pixels))


def file_receipt(path: Path, *, relative_path: str) -> dict[str, Any]:
    payload = path.read_bytes()
    return {
        "path": relative_path,
        "bytes": len(payload),
        "sha256": sha256_bytes(payload),
    }


def _validate_model_manifest(
    files: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    if len(files) != len(MODEL_FILE_SIZES):
        _fail("MODEL_FILE_COUNT_MISMATCH", "$.model.files")
    records: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(files):
        record = _mapping(raw, f"$.model.files[{index}]")
        if set(record) != {"path", "bytes", "sha256"}:
            _fail("INVALID_MODEL_FILE_FIELDS", f"$.model.files[{index}]")
        name = record.get("path")
        if not isinstance(name, str) or name in records:
            _fail("INVALID_MODEL_FILE_PATH", f"$.model.files[{index}].path")
        if MODEL_FILE_SIZES.get(name) != record.get("bytes"):
            _fail("MODEL_FILE_SIZE_MISMATCH", f"$.model.files[{index}].bytes")
        _sha256(record.get("sha256"), f"$.model.files[{index}].sha256")
        if (
            name in MODEL_WEIGHT_SHA256
            and record["sha256"] != MODEL_WEIGHT_SHA256[name]
        ):
            _fail("MODEL_WEIGHT_HASH_MISMATCH", f"$.model.files[{index}].sha256")
        records[name] = dict(record)
    if set(records) != set(MODEL_FILE_SIZES):
        _fail("MODEL_FILE_SET_MISMATCH", "$.model.files")
    return [records[name] for name in sorted(records)]


def _validate_screenshot_manifest(
    files: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    if len(files) != len(SCREENSHOT_CASES):
        _fail("SCREENSHOT_COUNT_MISMATCH", "$.source_lineage.screenshots")
    records: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(files):
        record = _mapping(raw, f"$.source_lineage.screenshots[{index}]")
        if set(record) != {"case_id", "path", "bytes", "sha256"}:
            _fail("INVALID_SCREENSHOT_FIELDS", f"$.source_lineage.screenshots[{index}]")
        case_id = record.get("case_id")
        expected_path = f"{SCREENSHOT_ROOT}/{case_id}.png"
        if case_id not in SCREENSHOT_CASES or case_id in records:
            _fail(
                "INVALID_SCREENSHOT_CASE",
                f"$.source_lineage.screenshots[{index}].case_id",
            )
        if (
            record.get("path") != expected_path
            or not isinstance(record.get("bytes"), int)
            or record["bytes"] <= 0
        ):
            _fail(
                "INVALID_SCREENSHOT_RECEIPT", f"$.source_lineage.screenshots[{index}]"
            )
        _sha256(record.get("sha256"), f"$.source_lineage.screenshots[{index}].sha256")
        records[str(case_id)] = dict(record)
    return [records[case_id] for case_id in SCREENSHOT_CASES]


def _validate_compiled_record(record: Mapping[str, Any], case_id: str) -> None:
    expected = {"case_id", "disposition", "tool", "arguments", "ref", "bbox", "reason"}
    if set(record) != expected or record.get("case_id") != case_id:
        _fail("INVALID_PREDICTION_SHAPE", "$.model_output")
    disposition = record.get("disposition")
    if disposition not in {"act", "reject", "fallback"}:
        _fail("INVALID_DISPOSITION", "$.model_output.disposition")
    if disposition == "act":
        if (
            record.get("tool") != "click"
            or record.get("arguments") != {"button": "left"}
            or record.get("reason") is not None
        ):
            _fail("INVALID_ACT_FIELDS", "$.model_output")
        ref = record.get("ref")
        bbox = record.get("bbox")
        if ref is not None and (
            not isinstance(ref, str) or IDENTIFIER_PATTERN.fullmatch(ref) is None
        ):
            _fail("INVALID_REF", "$.model_output.ref")
        if bbox is not None and (
            not isinstance(bbox, list)
            or len(bbox) != 4
            or any(type(item) is not int or item < 0 or item > 4096 for item in bbox)
        ):
            _fail("INVALID_BBOX", "$.model_output.bbox")
        if ref is None and bbox is None:
            _fail("MISSING_GROUNDING", "$.model_output")
    else:
        if any(
            record.get(key) is not None for key in ("tool", "arguments", "ref", "bbox")
        ):
            _fail("INVALID_NON_ACT_FIELDS", "$.model_output")
        reason = record.get("reason")
        if not isinstance(reason, str) or IDENTIFIER_PATTERN.fullmatch(reason) is None:
            _fail("INVALID_REASON", "$.model_output.reason")


def _fallback_record(case_id: str) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "disposition": "fallback",
        "tool": None,
        "arguments": None,
        "ref": None,
        "bbox": None,
        "reason": "model_output_invalid",
    }


def _encode_png(width: int, height: int, pixels: bytes) -> bytes:
    stride = width * 3
    raw = b"".join(
        b"\x00" + pixels[row * stride : (row + 1) * stride] for row in range(height)
    )
    signature = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        signature
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", zlib.compress(raw, 9))
        + _png_chunk(b"IEND", b"")
    )


def _png_chunk(kind: bytes, payload: bytes) -> bytes:
    return (
        struct.pack(">I", len(payload))
        + kind
        + payload
        + struct.pack(">I", binascii.crc32(kind + payload) & 0xFFFFFFFF)
    )


def _fill_rect(
    pixels: bytearray, x1: int, y1: int, x2: int, y2: int, color: tuple[int, int, int]
) -> None:
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(PNG_WIDTH, x2), min(PNG_HEIGHT, y2)
    row = bytes(color) * max(0, x2 - x1)
    for y in range(y1, y2):
        offset = (y * PNG_WIDTH + x1) * 3
        pixels[offset : offset + len(row)] = row


def _stroke_rect(
    pixels: bytearray,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    color: tuple[int, int, int],
    width: int,
) -> None:
    _fill_rect(pixels, x1, y1, x2, y1 + width, color)
    _fill_rect(pixels, x1, y2 - width, x2, y2, color)
    _fill_rect(pixels, x1, y1, x1 + width, y2, color)
    _fill_rect(pixels, x2 - width, y1, x2, y2, color)


_FONT = {
    " ": ("00000",) * 7,
    "?": ("01110", "10001", "00001", "00010", "00100", "00000", "00100"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    **{
        char: tuple(rows.split("/"))
        for char, rows in {
            "0": "01110/10001/10011/10101/11001/10001/01110",
            "1": "00100/01100/00100/00100/00100/00100/01110",
            "2": "01110/10001/00001/00010/00100/01000/11111",
            "3": "11110/00001/00001/01110/00001/00001/11110",
            "4": "00010/00110/01010/10010/11111/00010/00010",
            "5": "11111/10000/10000/11110/00001/00001/11110",
            "6": "01110/10000/10000/11110/10001/10001/01110",
            "7": "11111/00001/00010/00100/01000/01000/01000",
            "8": "01110/10001/10001/01110/10001/10001/01110",
            "9": "01110/10001/10001/01111/00001/00001/01110",
            "A": "01110/10001/10001/11111/10001/10001/10001",
            "B": "11110/10001/10001/11110/10001/10001/11110",
            "C": "01111/10000/10000/10000/10000/10000/01111",
            "D": "11110/10001/10001/10001/10001/10001/11110",
            "E": "11111/10000/10000/11110/10000/10000/11111",
            "F": "11111/10000/10000/11110/10000/10000/10000",
            "G": "01111/10000/10000/10111/10001/10001/01111",
            "H": "10001/10001/10001/11111/10001/10001/10001",
            "I": "01110/00100/00100/00100/00100/00100/01110",
            "J": "00111/00010/00010/00010/10010/10010/01100",
            "K": "10001/10010/10100/11000/10100/10010/10001",
            "L": "10000/10000/10000/10000/10000/10000/11111",
            "M": "10001/11011/10101/10101/10001/10001/10001",
            "N": "10001/11001/10101/10011/10001/10001/10001",
            "O": "01110/10001/10001/10001/10001/10001/01110",
            "P": "11110/10001/10001/11110/10000/10000/10000",
            "Q": "01110/10001/10001/10001/10101/10010/01101",
            "R": "11110/10001/10001/11110/10100/10010/10001",
            "S": "01111/10000/10000/01110/00001/00001/11110",
            "T": "11111/00100/00100/00100/00100/00100/00100",
            "U": "10001/10001/10001/10001/10001/10001/01110",
            "V": "10001/10001/10001/10001/10001/01010/00100",
            "W": "10001/10001/10001/10101/10101/10101/01010",
            "X": "10001/10001/01010/00100/01010/10001/10001",
            "Y": "10001/10001/01010/00100/00100/00100/00100",
            "Z": "11111/00001/00010/00100/01000/10000/11111",
        }.items()
    },
}


def _draw_text(
    pixels: bytearray,
    x: int,
    y: int,
    text: str,
    color: tuple[int, int, int],
    scale: int,
) -> None:
    cursor = x
    for char in text:
        glyph = _FONT.get(char, _FONT["?"])
        for row_index, row in enumerate(glyph):
            for col_index, bit in enumerate(row):
                if bit == "1":
                    _fill_rect(
                        pixels,
                        cursor + col_index * scale,
                        y + row_index * scale,
                        cursor + (col_index + 1) * scale,
                        y + (row_index + 1) * scale,
                        color,
                    )
        cursor += 6 * scale


def _mapping(value: object, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail("EXPECTED_OBJECT", location)
    return value


def _sequence(value: object, location: str) -> Sequence[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        _fail("EXPECTED_ARRAY", location)
    return value


def _sha256(value: object, location: str) -> None:
    if not isinstance(value, str) or SHA256_PATTERN.fullmatch(value) is None:
        _fail("INVALID_SHA256", location)


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> NoReturn:
    raise ValueError(f"non-finite value: {value}")


def _validate_finite(value: Any, location: str) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        _fail("NONFINITE_NUMBER", location)
    if isinstance(value, Mapping):
        for key, item in value.items():
            _validate_finite(item, f"{location}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _validate_finite(item, f"{location}[{index}]")


def _fail(code: str, location: str, detail: str = "") -> NoReturn:
    raise MM003ProtocolError(code, location, detail)
