"""Fail-closed execution contract for MM-005 Browser Research data generation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any, NoReturn

from . import mm005_browser_research_data as data

GENERATION_PROTOCOL_VERSION = 1
EVIDENCE_VERSION = 1
GATE_ID = data.EXECUTION_GATE_ID
EXECUTION_GATE_ID = "MM-005-browser-research-data-generation-execution-v1"
NEXT_GATE = "MM-005-browser-research-adapter-verifier-protocol-v1"

PROTOCOL_PATH = "configs/mm005_browser_research_data_generation_v1.json"
DATA_PROTOCOL_PATH = data.PREREGISTRATION_PATH
DATA_PROTOCOL_MERGE_COMMIT = "9518d5b59fb11dbea237caa17fd245f4dcd5c2db"
OUTPUT_ROOT = data.OUTPUT_ROOT
EVIDENCE_PATH = data.EVIDENCE_PATH

SOURCE_RECEIPT_NAMES = {
    "data_builder",
    "data_contract",
    "generation_contract",
    "generation_runner",
}
FREEZE_CLAIMS = data.FREEZE_CLAIMS
EXECUTION_CLAIMS = {
    "generation_executed": True,
    "records_generated": True,
    "source_snapshots_generated": True,
    "screenshots_generated": True,
    "dataset_validated": True,
    "environment_adapter_implemented": False,
    "verifier_executed": False,
    "live_browser_used": False,
    "network_accessed": False,
    "external_content_collected": False,
    "model_trained": False,
    "model_evaluated": False,
    "quality_improved": False,
    "safety_established": False,
    "prompt_injection_safety_established": False,
    "real_content_collected": False,
    "capture_adapter_used": False,
    "runtime_repository_changed": False,
    "runtime_integration_changed": False,
    "serving_eligible": False,
    "promotion_eligible": False,
    "runtime_eligible": False,
}

REQUIRED_GATES = (
    "data_protocol_integrity",
    "data_protocol_publication_integrity",
    "freeze_commit_integrity",
    "source_receipt_integrity",
    "execution_target_absence",
    "deterministic_output_rebuild",
    "planned_output_receipt_integrity",
    "atomic_output_materialization",
    "exact_output_tree",
    "independent_persisted_byte_validation",
    "parent_record_and_exclusion_validation",
    "split_identity_isolation",
    "dom_page_text_screenshot_alignment",
    "screenshot_png_integrity",
    "static_source_snapshot_integrity",
    "citation_and_freshness_semantics",
    "exclusive_execution_evidence",
    "network_live_browser_model_and_capture_excluded",
    "runtime_authority_preserved",
    "fail_closed_claims",
)


class MM005BrowserResearchGenerationError(ValueError):
    """Stable fail-closed error for generation protocol and evidence drift."""

    def __init__(self, code: str, location: str = "$") -> None:
        self.code = code
        self.location = location
        super().__init__(f"{code} at {location}")


@dataclass(frozen=True)
class GenerationSummary:
    protocol_version: int
    template_count: int
    record_count: int
    source_count: int
    screenshot_count: int
    source_snapshot_count: int
    train_records: int
    validation_records: int
    train_sources: int
    validation_sources: int
    output_file_count: int
    output_bytes: int
    generation_executed: bool
    records_generated: bool
    source_snapshots_generated: bool
    screenshots_generated: bool
    dataset_validated: bool
    next_gate: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def artifact_json_bytes(value: object) -> bytes:
    return data.artifact_json_bytes(value)


def sha256_bytes(payload: bytes) -> str:
    return data.sha256_bytes(payload)


def expected_protocol(
    *,
    freeze_status: str,
    source_receipts: Mapping[str, Mapping[str, Any]],
    data_protocol_payload: bytes,
) -> dict[str, Any]:
    if freeze_status not in {"draft", "frozen"}:
        _fail("FREEZE_STATUS_INVALID", "$.freeze_status")
    if set(source_receipts) != SOURCE_RECEIPT_NAMES:
        _fail("SOURCE_RECEIPT_SET_INVALID", "$.source_receipts")
    sources = _closed_receipts(source_receipts, "$.source_receipts")
    data_protocol = _json_object(data_protocol_payload, "$.data_protocol")
    if (
        data_protocol.get("gate_id") != data.GATE_ID
        or data_protocol.get("freeze_status") != "frozen"
        or data_protocol.get("next_gate") != GATE_ID
    ):
        _fail("DATA_PROTOCOL_BOUNDARY_INVALID", "$.data_protocol")
    planned_outputs = _closed_receipts(
        _object(data_protocol.get("planned_outputs"), "$.data_protocol.planned_outputs"),
        "$.data_protocol.planned_outputs",
    )
    if len(planned_outputs) != data.OUTPUT_FILE_COUNT:
        _fail("OUTPUT_COUNT_INVALID", "$.data_protocol.planned_outputs")
    output_bytes = sum(int(receipt["bytes"]) for receipt in planned_outputs.values())
    return {
        "mm005_browser_research_generation_protocol_version": (
            GENERATION_PROTOCOL_VERSION
        ),
        "gate_id": GATE_ID,
        "freeze_status": freeze_status,
        "decision": "one_shot_model_free_static_browser_data_materialization",
        "data_protocol_publication": {
            "merge_commit": DATA_PROTOCOL_MERGE_COMMIT,
            "generation_freeze_commit_must_descend_from_merge": True,
            "published_protocol_bytes_must_match_current": True,
        },
        "data_protocol": _receipt(DATA_PROTOCOL_PATH, data_protocol_payload),
        "source_receipts": sources,
        "planned_outputs": planned_outputs,
        "execution_plan": {
            "execution_gate_id": EXECUTION_GATE_ID,
            "required_branch": "master",
            "commit_alignment": (
                "HEAD == origin/master == supplied protocol freeze commit"
            ),
            "output_root": OUTPUT_ROOT,
            "evidence_path": EVIDENCE_PATH,
            "output_file_count": data.OUTPUT_FILE_COUNT,
            "output_bytes": output_bytes,
            "internal_retry_limit": 0,
            "network_allowed": False,
            "live_browser_allowed": False,
            "javascript_allowed": False,
            "model_dependencies_allowed": False,
            "real_or_external_content_allowed": False,
            "capture_allowed": False,
            "atomic_output_root_required": True,
            "exclusive_evidence_write_required": True,
            "exact_output_tree_required": True,
            "independent_persisted_byte_validation_required": True,
            "execution_targets_must_be_absent": True,
        },
        "required_gates": list(REQUIRED_GATES),
        "authority_contract": {
            "page_content_has_instruction_or_execution_authority": False,
            "model_output_has_execution_authority": False,
            "runtime_is_sole_policy_approval_wal_grounding_budget_dispatch_boundary": (
                True
            ),
            "live_browser_navigation_authorized": False,
            "network_retrieval_authorized": False,
            "runtime_repository_changed": False,
            "runtime_integration_authorized": False,
            "capture_authorized": False,
        },
        "claims": {key: False for key in FREEZE_CLAIMS},
        "next_gate": EXECUTION_GATE_ID,
    }


def validate_protocol(
    value: object,
    *,
    source_receipts: Mapping[str, Mapping[str, Any]],
    data_protocol_payload: bytes,
) -> dict[str, Any]:
    expected = expected_protocol(
        freeze_status="frozen",
        source_receipts=source_receipts,
        data_protocol_payload=data_protocol_payload,
    )
    if value != expected:
        _fail("GENERATION_PROTOCOL_MISMATCH")
    return expected


def validate_output_payloads(
    payloads: Mapping[str, bytes],
    *,
    protocol: Mapping[str, Any],
    data_protocol: Mapping[str, Any],
    exclusions: Mapping[str, Sequence[str]],
) -> GenerationSummary:
    protocol_receipts = _closed_receipts(
        _object(protocol.get("planned_outputs"), "$.protocol.planned_outputs"),
        "$.protocol.planned_outputs",
    )
    data_receipts = _closed_receipts(
        _object(data_protocol.get("planned_outputs"), "$.data_protocol.planned_outputs"),
        "$.data_protocol.planned_outputs",
    )
    if protocol_receipts != data_receipts:
        _fail("PLANNED_OUTPUT_BINDING_MISMATCH")
    actual_receipts = {
        path: _receipt(path, payload) for path, payload in sorted(payloads.items())
    }
    if actual_receipts != protocol_receipts:
        _fail("ACTUAL_OUTPUT_RECEIPT_MISMATCH")
    parent_protocol = _object(data_protocol.get("parent_protocol"), "$.parent_protocol")
    validation = data.validate_planned_output_payloads(
        payloads,
        parent_protocol_sha256=str(parent_protocol.get("sha256")),
        exclusions=exclusions,
    )
    expected_validation = {
        "planned_output_rebuild_valid": True,
        "template_count": data.TEMPLATE_COUNT,
        "record_count": data.RECORD_COUNT,
        "source_count": data.SOURCE_COUNT,
        "screenshot_count": data.SCREENSHOT_COUNT,
        "source_snapshot_count": data.SOURCE_SNAPSHOT_COUNT,
        "train_records": data.TRAIN_RECORDS,
        "validation_records": data.VALIDATION_RECORDS,
        "train_sources": data.TRAIN_SOURCE_COUNT,
        "validation_sources": data.VALIDATION_SOURCE_COUNT,
        "output_file_count": data.OUTPUT_FILE_COUNT,
        "output_bytes": sum(len(payload) for payload in payloads.values()),
        "generation_executed": False,
        "dataset_validated": False,
        "next_gate": data.NEXT_GATE,
    }
    if validation != expected_validation:
        _fail("DATA_VALIDATION_SUMMARY_MISMATCH")
    return GenerationSummary(
        protocol_version=GENERATION_PROTOCOL_VERSION,
        template_count=data.TEMPLATE_COUNT,
        record_count=data.RECORD_COUNT,
        source_count=data.SOURCE_COUNT,
        screenshot_count=data.SCREENSHOT_COUNT,
        source_snapshot_count=data.SOURCE_SNAPSHOT_COUNT,
        train_records=data.TRAIN_RECORDS,
        validation_records=data.VALIDATION_RECORDS,
        train_sources=data.TRAIN_SOURCE_COUNT,
        validation_sources=data.VALIDATION_SOURCE_COUNT,
        output_file_count=len(actual_receipts),
        output_bytes=sum(len(payload) for payload in payloads.values()),
        generation_executed=True,
        records_generated=True,
        source_snapshots_generated=True,
        screenshots_generated=True,
        dataset_validated=True,
        next_gate=NEXT_GATE,
    )


def build_evidence(
    *,
    protocol_freeze_commit: str,
    protocol_payload: bytes,
    source_receipts: Mapping[str, Mapping[str, Any]],
    data_protocol_payload: bytes,
    data_source_receipts: Mapping[str, Mapping[str, Any]],
    parent_protocol_receipt: Mapping[str, Any],
    output_payloads: Mapping[str, bytes],
    exclusions: Mapping[str, Sequence[str]],
) -> dict[str, Any]:
    _validate_commit(protocol_freeze_commit)
    protocol = _json_object(protocol_payload, "$.protocol")
    validate_protocol(
        protocol,
        source_receipts=source_receipts,
        data_protocol_payload=data_protocol_payload,
    )
    data_protocol = _json_object(data_protocol_payload, "$.data_protocol")
    data.validate_preregistration(
        data_protocol,
        source_receipts=data_source_receipts,
        parent_protocol_receipt=parent_protocol_receipt,
    )
    summary = validate_output_payloads(
        output_payloads,
        protocol=protocol,
        data_protocol=data_protocol,
        exclusions=exclusions,
    )
    return {
        "mm005_browser_research_generation_evidence_version": EVIDENCE_VERSION,
        "gate_id": EXECUTION_GATE_ID,
        "protocol_freeze_commit": protocol_freeze_commit,
        "data_protocol_merge_commit": DATA_PROTOCOL_MERGE_COMMIT,
        "generation_protocol": _receipt(PROTOCOL_PATH, protocol_payload),
        "data_protocol": _receipt(DATA_PROTOCOL_PATH, data_protocol_payload),
        "outputs": {
            path: _receipt(path, payload)
            for path, payload in sorted(output_payloads.items())
        },
        "required_gates": {gate: True for gate in REQUIRED_GATES},
        "summary": summary.to_dict(),
        "claims": dict(EXECUTION_CLAIMS),
        "next_gate": NEXT_GATE,
    }


def validate_evidence(
    value: object,
    *,
    protocol_freeze_commit: str,
    protocol_payload: bytes,
    source_receipts: Mapping[str, Mapping[str, Any]],
    data_protocol_payload: bytes,
    data_source_receipts: Mapping[str, Mapping[str, Any]],
    parent_protocol_receipt: Mapping[str, Any],
    output_payloads: Mapping[str, bytes],
    exclusions: Mapping[str, Sequence[str]],
) -> GenerationSummary:
    expected = build_evidence(
        protocol_freeze_commit=protocol_freeze_commit,
        protocol_payload=protocol_payload,
        source_receipts=source_receipts,
        data_protocol_payload=data_protocol_payload,
        data_source_receipts=data_source_receipts,
        parent_protocol_receipt=parent_protocol_receipt,
        output_payloads=output_payloads,
        exclusions=exclusions,
    )
    if value != expected:
        _fail("EVIDENCE_MISMATCH")
    return GenerationSummary(**_object(expected["summary"], "$.summary"))


def _validate_commit(value: str) -> None:
    if len(value) != 40 or any(
        character not in "0123456789abcdef" for character in value
    ):
        _fail("FREEZE_COMMIT_INVALID", "$.protocol_freeze_commit")


def _receipt(path: str, payload: bytes) -> dict[str, Any]:
    return {"path": path, "bytes": len(payload), "sha256": sha256_bytes(payload)}


def _closed_receipts(
    values: Mapping[str, Any], location: str
) -> dict[str, dict[str, Any]]:
    if not values:
        _fail("RECEIPTS_EMPTY", location)
    result: dict[str, dict[str, Any]] = {}
    for name, value in sorted(values.items()):
        result[name] = _closed_receipt(
            _object(value, f"{location}.{name}"),
            expected_path=(name if "/" in name else None),
            location=f"{location}.{name}",
        )
    return result


def _closed_receipt(
    value: Mapping[str, Any],
    *,
    expected_path: str | None,
    location: str,
) -> dict[str, Any]:
    if set(value) != {"path", "bytes", "sha256"}:
        _fail("RECEIPT_SHAPE_INVALID", location)
    path = value.get("path")
    byte_count = value.get("bytes")
    digest = value.get("sha256")
    if not isinstance(path, str) or not path or (expected_path and path != expected_path):
        _fail("RECEIPT_PATH_INVALID", location)
    if not isinstance(byte_count, int) or isinstance(byte_count, bool) or byte_count <= 0:
        _fail("RECEIPT_BYTES_INVALID", location)
    if (
        not isinstance(digest, str)
        or len(digest) != 71
        or not digest.startswith("sha256:")
        or any(character not in "0123456789abcdef" for character in digest[7:])
    ):
        _fail("RECEIPT_SHA256_INVALID", location)
    return dict(value)


def _json_object(payload: bytes, location: str) -> Mapping[str, Any]:
    try:
        import json

        value = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MM005BrowserResearchGenerationError("JSON_INVALID", location) from exc
    if not isinstance(value, dict) or artifact_json_bytes(value) != payload:
        _fail("JSON_NOT_CANONICAL_OBJECT", location)
    return value


def _object(value: object, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail("EXPECTED_OBJECT", location)
    return value


def _fail(code: str, location: str = "$") -> NoReturn:
    raise MM005BrowserResearchGenerationError(code, location)
