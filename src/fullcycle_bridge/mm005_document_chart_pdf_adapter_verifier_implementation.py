"""Evidence contract for the implemented MM-005 Adapter and Verifier."""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any, NoReturn

from . import mm005_document_chart_pdf_adapter_verifier as implementation
from . import mm005_document_chart_pdf_adapter_verifier_protocol as protocol
from . import mm005_document_chart_pdf_data as data

EVIDENCE_VERSION = 1
GATE_ID = protocol.NEXT_GATE
PROTOCOL_MERGE_COMMIT = "db8c6833f43c02a0b255c436558e0269a8bde3b4"
EVIDENCE_PATH = (
    "baseline/mm005-document-chart-pdf-adapter-verifier-implementation-v1.json"
)
NEXT_GATE = "MM-005-document-chart-pdf-model-evaluation-protocol-v1"

IMPLEMENTATION_CLAIMS = {
    **protocol.PROTOCOL_CLAIMS,
    "environment_adapter_implemented": True,
    "environment_adapter_executed": True,
    "verifier_implemented": True,
    "verifier_executed": True,
}

REQUIRED_GATES = (
    "protocol_merge_and_receipt_integrity",
    "implementation_source_receipt_integrity",
    "consumed_dataset_tree_integrity",
    "adapter_api_closed",
    "adapter_projection_registry_exact",
    "adapter_image_bytes_exact",
    "model_payload_gold_and_path_isolation",
    "strict_output_compiler_total",
    "verifier_case_registry_exact",
    "verifier_positive_controls_exact",
    "verifier_negative_controls_exact",
    "model_and_network_absence",
    "runtime_authority_preserved",
    "model_execution_deferred",
    "fail_closed_claims",
)


class MM005AdapterVerifierImplementationError(ValueError):
    """Stable fail-closed error for implementation evidence drift."""

    def __init__(self, code: str, location: str = "$") -> None:
        self.code = code
        self.location = location
        super().__init__(f"{code} at {location}")


@dataclass(frozen=True)
class AdapterVerifierImplementationSummary:
    evidence_version: int
    source_receipt_count: int
    record_count: int
    image_count: int
    adapter_projection_count: int
    model_payload_bytes: int
    image_bytes: int
    verifier_case_count: int
    compiler_valid_count: int
    compiler_invalid_count: int
    positive_case_count: int
    negative_case_count: int
    environment_adapter_implemented: bool
    environment_adapter_executed: bool
    verifier_implemented: bool
    verifier_executed: bool
    model_evaluated: bool
    next_gate: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def artifact_json_bytes(value: object) -> bytes:
    return implementation.artifact_json_bytes(value)


def sha256_bytes(payload: bytes) -> str:
    return implementation.sha256_bytes(payload)


def expected_evidence(
    *,
    implementation_source_receipts: Mapping[str, Mapping[str, Any]],
    protocol_payload: bytes,
    protocol_source_receipts: Mapping[str, Mapping[str, Any]],
    generation_evidence_payload: bytes,
    generation_protocol_payload: bytes,
    generation_source_receipts: Mapping[str, Mapping[str, Any]],
    data_protocol_payload: bytes,
    data_source_receipts: Mapping[str, Mapping[str, Any]],
    parent_protocol_receipt: Mapping[str, Any],
    output_payloads: Mapping[str, bytes],
    exclusions: Mapping[str, Sequence[str]],
) -> dict[str, Any]:
    sources = _closed_receipts(
        implementation_source_receipts, "$.implementation_source_receipts"
    )
    protocol_value = _json_object(protocol_payload, "$.protocol")
    protocol_summary = protocol.validate_protocol(
        protocol_value,
        source_receipts=protocol_source_receipts,
        generation_evidence_payload=generation_evidence_payload,
        generation_protocol_payload=generation_protocol_payload,
        generation_source_receipts=generation_source_receipts,
        data_protocol_payload=data_protocol_payload,
        data_source_receipts=data_source_receipts,
        parent_protocol_receipt=parent_protocol_receipt,
        output_payloads=output_payloads,
        exclusions=exclusions,
    )
    if (
        protocol_summary.next_gate != GATE_ID
        or protocol_value.get("claims") != protocol.PROTOCOL_CLAIMS
        or protocol_value.get("freeze_status") != "frozen"
    ):
        _fail("UPSTREAM_PROTOCOL_BOUNDARY_INVALID", "$.protocol")

    records, image_receipts, dataset_receipts = protocol.dataset_context(
        output_payloads
    )
    images = {
        path: output_payloads[path]
        for path in sorted(image_receipts)
        if path in output_payloads
    }
    if len(images) != len(image_receipts):
        _fail("IMPLEMENTATION_IMAGE_SET_INVALID", "$.output_payloads")

    frozen_projection_registry = _array(
        protocol_value.get("adapter_projection_registry"),
        "$.protocol.adapter_projection_registry",
    )
    observed_projection_registry: list[dict[str, Any]] = []
    adapter_execution_registry: list[dict[str, Any]] = []
    model_payload_bytes = 0
    image_bytes = 0
    for record in sorted(records, key=lambda item: str(item.get("record_id"))):
        adapted = implementation.adapt_record(record, images)
        receipt = implementation.projection_receipt(record, adapted)
        observed_projection_registry.append(receipt)
        model_payload_bytes += len(adapted.model_payload_json)
        image_bytes += len(adapted.image_bytes)
        model_payload = adapted.model_payload()
        audit_projection = adapted.audit_projection()
        image_binding = _object(
            audit_projection.get("image_binding"), "$.audit_projection.image_binding"
        )
        if (
            set(model_payload) != set(protocol.MODEL_PAYLOAD_KEYS)
            or image_binding.get("path", "").encode("utf-8")
            in adapted.model_payload_json
        ):
            _fail("IMPLEMENTATION_MODEL_PAYLOAD_LEAKAGE", "$.adapter_execution")
        adapter_execution_registry.append(
            {
                "record_id": record["record_id"],
                "model_payload": _payload_receipt(adapted.model_payload_json),
                "image_payload": _payload_receipt(adapted.image_bytes),
                "projection": _payload_receipt(adapted.audit_projection_json),
                "gold_or_verifier_fields_exposed_to_model": False,
                "real_file_path_exposed_to_model": False,
            }
        )
    if observed_projection_registry != frozen_projection_registry:
        _fail("IMPLEMENTATION_PROJECTION_REGISTRY_MISMATCH", "$.adapter_execution")

    frozen_cases = _array(
        protocol_value.get("verifier_case_registry"),
        "$.protocol.verifier_case_registry",
    )
    records_by_id = {str(record["record_id"]): record for record in records}
    verifier_execution_registry: list[dict[str, Any]] = []
    case_distribution: Counter[str] = Counter()
    compiler_valid_count = 0
    joint_correct_count = 0
    for index, raw_case in enumerate(frozen_cases):
        case = _object(raw_case, f"$.protocol.verifier_case_registry[{index}]")
        record_id = str(case.get("record_id"))
        case_record = records_by_id.get(record_id)
        if case_record is None:
            _fail("IMPLEMENTATION_CASE_RECORD_MISSING", f"$.verifier_cases[{index}]")
        raw_output = case.get("raw_output")
        compiled = implementation.compile_candidate_output(raw_output)
        verdict = implementation.verify_candidate(compiled, case_record)
        if (
            compiled["valid"] != case.get("compiler_valid")
            or compiled["error_code"] != case.get("compiler_error_code")
            or verdict != case.get("verdict")
        ):
            _fail(
                "IMPLEMENTATION_VERIFIER_CASE_MISMATCH",
                f"$.verifier_cases[{index}]",
            )
        case_kind = str(case.get("case_kind"))
        case_distribution[case_kind] += 1
        compiler_valid_count += int(compiled["valid"] is True)
        joint_correct_count += int(verdict["joint_correct"] is True)
        verifier_execution_registry.append(
            {
                "case_id": case["case_id"],
                "record_id": record_id,
                "case_kind": case_kind,
                "compiled_output": _payload_receipt(artifact_json_bytes(compiled)),
                "verdict": _payload_receipt(artifact_json_bytes(verdict)),
                "compiler_valid": compiled["valid"],
                "compiler_error_code": compiled["error_code"],
                "joint_correct": verdict["joint_correct"],
            }
        )
    expected_distribution = Counter(
        {kind: protocol_summary.record_count for kind in protocol.VERIFIER_CASE_KINDS}
    )
    if (
        case_distribution != expected_distribution
        or joint_correct_count != protocol_summary.positive_case_count
    ):
        _fail("IMPLEMENTATION_VERIFIER_DISTRIBUTION_INVALID", "$.verifier_execution")

    summary = AdapterVerifierImplementationSummary(
        evidence_version=EVIDENCE_VERSION,
        source_receipt_count=len(sources),
        record_count=len(records),
        image_count=len(images),
        adapter_projection_count=len(observed_projection_registry),
        model_payload_bytes=model_payload_bytes,
        image_bytes=image_bytes,
        verifier_case_count=len(verifier_execution_registry),
        compiler_valid_count=compiler_valid_count,
        compiler_invalid_count=len(verifier_execution_registry) - compiler_valid_count,
        positive_case_count=joint_correct_count,
        negative_case_count=len(verifier_execution_registry) - joint_correct_count,
        environment_adapter_implemented=True,
        environment_adapter_executed=True,
        verifier_implemented=True,
        verifier_executed=True,
        model_evaluated=False,
        next_gate=NEXT_GATE,
    )
    return {
        "mm005_document_chart_pdf_adapter_verifier_implementation_evidence_version": (
            EVIDENCE_VERSION
        ),
        "gate_id": GATE_ID,
        "decision": "adapter_and_verifier_implemented_without_model_execution",
        "protocol": {
            "receipt": _receipt(protocol.PROTOCOL_PATH, protocol_payload),
            "merge_commit": PROTOCOL_MERGE_COMMIT,
            "gate_id": protocol.GATE_ID,
            "required_before_implementation": True,
        },
        "implementation_source_receipts": sources,
        "consumed_inputs": {
            "dataset_receipts": dataset_receipts,
            "generation_evidence": _closed_receipt(
                _object(
                    _object(protocol_value.get("upstream"), "$.protocol.upstream").get(
                        "generation_evidence"
                    ),
                    "$.protocol.upstream.generation_evidence",
                ),
                expected_path=data.EVIDENCE_PATH,
                location="$.protocol.upstream.generation_evidence",
            ),
            "read_only": True,
            "generation_rerun": False,
        },
        "adapter_implementation": {
            "implementation_version": implementation.IMPLEMENTATION_VERSION,
            "adapter_version": implementation.ADAPTER_VERSION,
            "model_payload_exact_keys": list(implementation.MODEL_PAYLOAD_KEYS),
            "image_bytes_outside_model_payload": True,
            "real_file_path_exposed_to_model": False,
            "gold_or_verifier_fields_exposed_to_model": False,
            "projection_registry_exact": True,
            "execution_registry": adapter_execution_registry,
            "execution_registry_receipt": _payload_receipt(
                artifact_json_bytes(adapter_execution_registry)
            ),
        },
        "verifier_implementation": {
            "compiler_version": implementation.COMPILER_VERSION,
            "verifier_version": implementation.VERIFIER_VERSION,
            "model_or_llm_judge_used": False,
            "invalid_output_is_wrong": True,
            "case_registry_exact": True,
            "case_distribution": dict(sorted(case_distribution.items())),
            "execution_registry": verifier_execution_registry,
            "execution_registry_receipt": _payload_receipt(
                artifact_json_bytes(verifier_execution_registry)
            ),
        },
        "required_gates": list(REQUIRED_GATES),
        "gate_results": {gate: True for gate in REQUIRED_GATES},
        "authority_contract": {
            "model_output_has_execution_authority": False,
            "runtime_is_sole_policy_approval_wal_grounding_budget_dispatch_boundary": (
                True
            ),
            "runtime_repository_changed": False,
            "runtime_integration_authorized": False,
            "capture_authorized": False,
        },
        "summary": summary.to_dict(),
        "claims": dict(IMPLEMENTATION_CLAIMS),
        "next_gate": NEXT_GATE,
    }


def validate_evidence(
    value: object,
    *,
    implementation_source_receipts: Mapping[str, Mapping[str, Any]],
    protocol_payload: bytes,
    protocol_source_receipts: Mapping[str, Mapping[str, Any]],
    generation_evidence_payload: bytes,
    generation_protocol_payload: bytes,
    generation_source_receipts: Mapping[str, Mapping[str, Any]],
    data_protocol_payload: bytes,
    data_source_receipts: Mapping[str, Mapping[str, Any]],
    parent_protocol_receipt: Mapping[str, Any],
    output_payloads: Mapping[str, bytes],
    exclusions: Mapping[str, Sequence[str]],
) -> AdapterVerifierImplementationSummary:
    expected = expected_evidence(
        implementation_source_receipts=implementation_source_receipts,
        protocol_payload=protocol_payload,
        protocol_source_receipts=protocol_source_receipts,
        generation_evidence_payload=generation_evidence_payload,
        generation_protocol_payload=generation_protocol_payload,
        generation_source_receipts=generation_source_receipts,
        data_protocol_payload=data_protocol_payload,
        data_source_receipts=data_source_receipts,
        parent_protocol_receipt=parent_protocol_receipt,
        output_payloads=output_payloads,
        exclusions=exclusions,
    )
    if value != expected:
        _fail("IMPLEMENTATION_EVIDENCE_MISMATCH")
    summary = _object(expected["summary"], "$.summary")
    return AdapterVerifierImplementationSummary(**summary)


def _payload_receipt(payload: bytes) -> dict[str, Any]:
    return {"bytes": len(payload), "sha256": sha256_bytes(payload)}


def _receipt(path: str, payload: bytes) -> dict[str, Any]:
    return {"path": path, "bytes": len(payload), "sha256": sha256_bytes(payload)}


def _closed_receipts(
    values: Mapping[str, Any], location: str
) -> dict[str, dict[str, Any]]:
    if not values:
        _fail("RECEIPTS_EMPTY", location)
    return {
        name: _closed_receipt(
            _object(value, f"{location}.{name}"),
            expected_path=(name if "/" in name else None),
            location=f"{location}.{name}",
        )
        for name, value in sorted(values.items())
    }


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
    if (
        not isinstance(path, str)
        or not path
        or (expected_path and path != expected_path)
    ):
        _fail("RECEIPT_PATH_INVALID", location)
    if type(byte_count) is not int or byte_count <= 0:
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
        value = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MM005AdapterVerifierImplementationError("JSON_INVALID", location) from exc
    if not isinstance(value, dict) or artifact_json_bytes(value) != payload:
        _fail("JSON_NOT_CANONICAL_OBJECT", location)
    return value


def _object(value: object, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail("EXPECTED_OBJECT", location)
    return value


def _array(value: object, location: str) -> list[Any]:
    if not isinstance(value, list):
        _fail("EXPECTED_ARRAY", location)
    return value


def _fail(code: str, location: str = "$") -> NoReturn:
    raise MM005AdapterVerifierImplementationError(code, location)
