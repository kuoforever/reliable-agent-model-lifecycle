"""Fail-closed protocol for the MM-005 Document/Chart/PDF Adapter and Verifier."""

from __future__ import annotations

import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any, NoReturn

from . import mm005_document_chart_pdf_data as data
from . import mm005_document_chart_pdf_generation as generation
from . import multimodal_environment_adaptation as parent

PROTOCOL_VERSION = 1
ADAPTER_PROJECTION_VERSION = 1
VERIFIER_CASE_VERSION = 1

GATE_ID = "MM-005-document-chart-pdf-adapter-verifier-protocol-v1"
NEXT_GATE = "MM-005-document-chart-pdf-adapter-verifier-implementation-v1"
PROTOCOL_PATH = "configs/mm005_document_chart_pdf_adapter_verifier_protocol_v1.json"

MODEL_PAYLOAD_KEYS = (
    "instruction",
    "observation",
    "source_kind",
    "task_family_id",
)
FORBIDDEN_MODEL_PAYLOAD_KEYS = frozenset(
    {
        "expected_output",
        "family_id",
        "identities",
        "provenance",
        "record_id",
        "split",
        "template_id",
        "verifier",
    }
)
VERIFIER_CASE_KINDS = (
    "exact_expected",
    "wrong_answer",
    "wrong_evidence",
    "duplicate_evidence",
    "wrong_page",
)

PROTOCOL_CLAIMS = {
    **generation.EXECUTION_CLAIMS,
    "environment_adapter_executed": False,
    "verifier_implemented": False,
}

REQUIRED_GATES = (
    "generation_evidence_integrity",
    "source_receipt_integrity",
    "dataset_tree_integrity",
    "record_contract_integrity",
    "adapter_projection_closure",
    "model_payload_gold_isolation",
    "image_receipt_binding",
    "output_compiler_contract",
    "verifier_case_closure",
    "verifier_positive_controls",
    "verifier_negative_controls",
    "task_source_split_coverage",
    "model_and_network_absence",
    "runtime_authority_preserved",
    "implementation_deferred",
    "fail_closed_claims",
)


class MM005AdapterVerifierProtocolError(ValueError):
    """Stable fail-closed error for Adapter/Verifier protocol drift."""

    def __init__(self, code: str, location: str = "$") -> None:
        self.code = code
        self.location = location
        super().__init__(f"{code} at {location}")


@dataclass(frozen=True)
class AdapterVerifierProtocolSummary:
    protocol_version: int
    source_receipt_count: int
    record_count: int
    adapter_projection_count: int
    verifier_case_count: int
    positive_case_count: int
    negative_case_count: int
    task_family_count: int
    source_kind_count: int
    train_records: int
    validation_records: int
    generation_executed: bool
    dataset_validated: bool
    environment_adapter_implemented: bool
    verifier_implemented: bool
    next_gate: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def artifact_json_bytes(value: object) -> bytes:
    return generation.artifact_json_bytes(value)


def sha256_bytes(payload: bytes) -> str:
    return generation.sha256_bytes(payload)


def expected_protocol(
    *,
    freeze_status: str,
    source_receipts: Mapping[str, Mapping[str, Any]],
    generation_evidence_payload: bytes,
    generation_protocol_payload: bytes,
    generation_source_receipts: Mapping[str, Mapping[str, Any]],
    data_protocol_payload: bytes,
    data_source_receipts: Mapping[str, Mapping[str, Any]],
    parent_protocol_receipt: Mapping[str, Any],
    output_payloads: Mapping[str, bytes],
    exclusions: Mapping[str, Sequence[str]],
) -> dict[str, Any]:
    if freeze_status not in {"draft", "frozen"}:
        _fail("FREEZE_STATUS_INVALID", "$.freeze_status")
    sources = _closed_receipts(source_receipts, "$.source_receipts")
    generation_evidence = _json_object(
        generation_evidence_payload, "$.generation_evidence"
    )
    _json_object(generation_protocol_payload, "$.generation_protocol")
    _json_object(data_protocol_payload, "$.data_protocol")
    freeze_commit = generation_evidence.get("protocol_freeze_commit")
    if not isinstance(freeze_commit, str):
        _fail(
            "GENERATION_FREEZE_COMMIT_INVALID",
            "$.generation_evidence.protocol_freeze_commit",
        )
    generation_summary = generation.validate_evidence(
        generation_evidence,
        protocol_freeze_commit=freeze_commit,
        protocol_payload=generation_protocol_payload,
        source_receipts=generation_source_receipts,
        data_protocol_payload=data_protocol_payload,
        data_source_receipts=data_source_receipts,
        parent_protocol_receipt=parent_protocol_receipt,
        output_payloads=output_payloads,
        exclusions=exclusions,
    )
    if (
        generation_summary.generation_executed is not True
        or generation_summary.dataset_validated is not True
        or generation_summary.next_gate != GATE_ID
        or generation_evidence.get("claims") != generation.EXECUTION_CLAIMS
    ):
        _fail("GENERATION_EVIDENCE_BOUNDARY_INVALID", "$.generation_evidence")

    records, image_receipts, dataset_receipts = dataset_context(output_payloads)
    try:
        record_summary = parent.validate_records(records, exclusions)
    except parent.MM005ProtocolError as exc:
        raise MM005AdapterVerifierProtocolError(
            "RECORD_CONTRACT_INVALID", "$.dataset.records"
        ) from exc
    projections = adapter_projection_registry(records, image_receipts)
    verifier_cases = verifier_case_registry(records)
    positive_cases = sum(
        1 for case in verifier_cases if case["case_kind"] == "exact_expected"
    )
    negative_cases = len(verifier_cases) - positive_cases
    if positive_cases != len(records) or negative_cases != len(records) * 4:
        _fail("VERIFIER_CASE_DISTRIBUTION_INVALID", "$.verifier_case_registry")

    split_counts = {
        split: sum(1 for record in records if record.get("split") == split)
        for split in sorted(parent.SPLITS)
    }
    summary = AdapterVerifierProtocolSummary(
        protocol_version=PROTOCOL_VERSION,
        source_receipt_count=len(sources),
        record_count=len(records),
        adapter_projection_count=len(projections),
        verifier_case_count=len(verifier_cases),
        positive_case_count=positive_cases,
        negative_case_count=negative_cases,
        task_family_count=int(record_summary["task_family_count"]),
        source_kind_count=int(record_summary["source_kind_count"]),
        train_records=split_counts["train"],
        validation_records=split_counts["validation"],
        generation_executed=True,
        dataset_validated=True,
        environment_adapter_implemented=False,
        verifier_implemented=False,
        next_gate=NEXT_GATE,
    )
    return {
        "mm005_document_chart_pdf_adapter_verifier_protocol_version": (
            PROTOCOL_VERSION
        ),
        "gate_id": GATE_ID,
        "freeze_status": freeze_status,
        "decision": (
            "freeze_model_free_adapter_projection_and_deterministic_verifier_"
            "before_implementation"
        ),
        "source_receipts": sources,
        "upstream": {
            "generation_evidence": _receipt(
                data.EVIDENCE_PATH, generation_evidence_payload
            ),
            "generation_protocol": _receipt(
                generation.PROTOCOL_PATH, generation_protocol_payload
            ),
            "data_protocol": _receipt(data.PREREGISTRATION_PATH, data_protocol_payload),
            "parent_protocol": _closed_receipt(
                parent_protocol_receipt,
                expected_path=data.PARENT_PROTOCOL_PATH,
                location="$.parent_protocol_receipt",
            ),
            "datasets": dataset_receipts,
            "generation_protocol_freeze_commit": freeze_commit,
            "generation_claims": dict(generation.EXECUTION_CLAIMS),
        },
        "adapter_contract": {
            "adapter_projection_version": ADAPTER_PROJECTION_VERSION,
            "projection_exact_keys": [
                "adapter_projection_version",
                "authority",
                "image_binding",
                "model_payload",
                "record_id",
            ],
            "model_payload_exact_keys": list(MODEL_PAYLOAD_KEYS),
            "forbidden_model_payload_keys": sorted(FORBIDDEN_MODEL_PAYLOAD_KEYS),
            "image_binding_outside_model_payload": True,
            "real_file_path_exposed_to_model": False,
            "gold_or_verifier_fields_exposed_to_model": False,
            "formal_implementation_present": False,
            "formal_execution_at_this_gate": False,
            "output_compiler": {
                "compiler_version": parent.COMPILER_VERSION,
                "format": "strict_json_object",
                "exact_keys": ["answer", "evidence_refs", "page_number"],
                "extra_keys_allowed": False,
                "duplicate_keys_allowed": False,
                "nonfinite_values_allowed": False,
                "utf8_byte_limit": 8_192,
                "invalid_output_is_wrong": True,
            },
        },
        "adapter_projection_registry": projections,
        "verifier_contract": {
            "verifier_case_version": VERIFIER_CASE_VERSION,
            "verifier_version": parent.VERIFIER_VERSION,
            "case_kinds": list(VERIFIER_CASE_KINDS),
            "cases_per_record": len(VERIFIER_CASE_KINDS),
            "answer_match": "unicode_nfc_then_ascii_space_trim_exact",
            "evidence_match": "exact_ordered_unique_region_refs",
            "page_match": "exact_integer",
            "invalid_output_is_wrong": True,
            "model_or_llm_judge_used": False,
            "record_expected_output_is_model_hidden": True,
            "formal_implementation_present": False,
            "formal_execution_at_this_gate": False,
        },
        "verifier_case_registry": verifier_cases,
        "coverage": {
            "records": len(records),
            "train_records": split_counts["train"],
            "validation_records": split_counts["validation"],
            "task_family_ids": sorted(
                {str(record["task_family_id"]) for record in records}
            ),
            "source_kinds": sorted({str(record["source_kind"]) for record in records}),
            "splits": sorted({str(record["split"]) for record in records}),
            "adapter_projections": len(projections),
            "verifier_cases": len(verifier_cases),
            "positive_cases": positive_cases,
            "negative_cases": negative_cases,
        },
        "implementation_plan": {
            "implementation_gate_id": NEXT_GATE,
            "protocol_must_merge_before_implementation": True,
            "dataset_and_generation_evidence_read_only": True,
            "adapter_must_match_projection_registry": True,
            "verifier_must_match_case_registry": True,
            "network_allowed": False,
            "model_load_allowed": False,
            "model_training_or_evaluation_allowed": False,
            "real_or_external_content_allowed": False,
            "capture_allowed": False,
            "runtime_repository_change_allowed": False,
            "runtime_integration_allowed": False,
        },
        "required_gates": list(REQUIRED_GATES),
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
        "claims": dict(PROTOCOL_CLAIMS),
        "next_gate": NEXT_GATE,
    }


def validate_protocol(
    value: object,
    *,
    source_receipts: Mapping[str, Mapping[str, Any]],
    generation_evidence_payload: bytes,
    generation_protocol_payload: bytes,
    generation_source_receipts: Mapping[str, Mapping[str, Any]],
    data_protocol_payload: bytes,
    data_source_receipts: Mapping[str, Mapping[str, Any]],
    parent_protocol_receipt: Mapping[str, Any],
    output_payloads: Mapping[str, bytes],
    exclusions: Mapping[str, Sequence[str]],
) -> AdapterVerifierProtocolSummary:
    expected = expected_protocol(
        freeze_status="frozen",
        source_receipts=source_receipts,
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
        _fail("ADAPTER_VERIFIER_PROTOCOL_MISMATCH")
    summary = _object(expected["summary"], "$.summary")
    return AdapterVerifierProtocolSummary(**summary)


def dataset_context(
    output_payloads: Mapping[str, bytes],
) -> tuple[
    list[Mapping[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
]:
    records: list[Mapping[str, Any]] = []
    image_receipts: dict[str, dict[str, Any]] = {}
    dataset_receipts: dict[str, dict[str, Any]] = {}
    for split, path in (
        ("train", data.TRAIN_PATH),
        ("validation", data.VALIDATION_PATH),
    ):
        payload = output_payloads.get(path)
        if payload is None:
            _fail("DATASET_PAYLOAD_MISSING", f"$.output_payloads.{path}")
        dataset = _json_object(payload, f"$.output_payloads.{path}")
        if dataset.get("split") != split:
            _fail("DATASET_SPLIT_INVALID", f"$.output_payloads.{path}.split")
        for index, raw_record in enumerate(
            _array(dataset.get("records"), f"$.output_payloads.{path}.records")
        ):
            records.append(
                _object(
                    raw_record,
                    f"$.output_payloads.{path}.records[{index}]",
                )
            )
        receipt_values = _object(
            dataset.get("image_receipts"),
            f"$.output_payloads.{path}.image_receipts",
        )
        for image_path, raw_receipt in sorted(receipt_values.items()):
            if image_path in image_receipts:
                _fail(
                    "DUPLICATE_IMAGE_RECEIPT",
                    f"$.output_payloads.{path}.image_receipts.{image_path}",
                )
            receipt = _closed_receipt(
                _object(
                    raw_receipt,
                    f"$.output_payloads.{path}.image_receipts.{image_path}",
                ),
                expected_path=image_path,
                location=f"$.output_payloads.{path}.image_receipts.{image_path}",
            )
            image_payload = output_payloads.get(image_path)
            if image_payload is None or receipt != _receipt(image_path, image_payload):
                _fail(
                    "IMAGE_RECEIPT_MISMATCH",
                    f"$.output_payloads.{path}.image_receipts.{image_path}",
                )
            image_receipts[image_path] = receipt
        dataset_receipts[split] = _receipt(path, payload)
    manifest_payload = output_payloads.get(data.MANIFEST_PATH)
    if manifest_payload is None:
        _fail("MANIFEST_PAYLOAD_MISSING", "$.output_payloads")
    _json_object(manifest_payload, "$.output_payloads.manifest")
    dataset_receipts["manifest"] = _receipt(data.MANIFEST_PATH, manifest_payload)
    if len(records) != data.RECORD_COUNT or len(image_receipts) != data.IMAGE_COUNT:
        _fail("DATASET_COUNT_INVALID", "$.output_payloads")
    if len({receipt["sha256"] for receipt in image_receipts.values()}) != len(
        image_receipts
    ):
        _fail("IMAGE_RECEIPT_HASH_COLLISION", "$.output_payloads")
    return records, image_receipts, dataset_receipts


def project_record(
    record: Mapping[str, Any],
    image_receipts: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    _validate_record(record, "$.record")
    observation = _object(record["observation"], "$.record.observation")
    image_sha256 = observation.get("image_sha256")
    matching = [
        _closed_receipt(
            receipt,
            expected_path=path,
            location=f"$.image_receipts.{path}",
        )
        for path, receipt in sorted(image_receipts.items())
        if receipt.get("sha256") == image_sha256
    ]
    if len(matching) != 1:
        _fail("RECORD_IMAGE_BINDING_INVALID", "$.record.observation.image_sha256")
    image_binding = matching[0]
    model_payload = {
        "instruction": record["instruction"],
        "observation": _json_copy(record["observation"]),
        "source_kind": record["source_kind"],
        "task_family_id": record["task_family_id"],
    }
    if set(model_payload) != set(MODEL_PAYLOAD_KEYS):
        _fail("MODEL_PAYLOAD_SHAPE_INVALID", "$.model_payload")
    if _contains_forbidden_key(model_payload):
        _fail("MODEL_PAYLOAD_GOLD_LEAKAGE", "$.model_payload")
    model_payload_bytes = artifact_json_bytes(model_payload)
    if str(image_binding["path"]).encode("utf-8") in model_payload_bytes:
        _fail("MODEL_PAYLOAD_PATH_LEAKAGE", "$.model_payload")
    return {
        "adapter_projection_version": ADAPTER_PROJECTION_VERSION,
        "record_id": record["record_id"],
        "image_binding": image_binding,
        "model_payload": model_payload,
        "authority": {
            "model_output_has_execution_authority": False,
            "runtime_integration_authorized": False,
            "gold_or_verifier_fields_exposed_to_model": False,
            "real_file_path_exposed_to_model": False,
        },
    }


def adapter_projection_registry(
    records: Sequence[Mapping[str, Any]],
    image_receipts: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    registry: list[dict[str, Any]] = []
    seen_records: set[str] = set()
    for record in sorted(records, key=lambda item: str(item.get("record_id"))):
        projection = project_record(record, image_receipts)
        record_id = str(record["record_id"])
        if record_id in seen_records:
            _fail("DUPLICATE_PROJECTION_RECORD_ID", "$.adapter_projection_registry")
        seen_records.add(record_id)
        payload = artifact_json_bytes(projection)
        registry.append(
            {
                "record_id": record_id,
                "split": record["split"],
                "task_family_id": record["task_family_id"],
                "source_kind": record["source_kind"],
                "image_sha256": projection["image_binding"]["sha256"],
                "projection_bytes": len(payload),
                "projection_sha256": sha256_bytes(payload),
            }
        )
    if len(registry) != len(records):
        _fail("PROJECTION_COUNT_INVALID", "$.adapter_projection_registry")
    return registry


def verifier_cases_for_record(record: Mapping[str, Any]) -> list[dict[str, Any]]:
    _validate_record(record, "$.record")
    expected = _object(record["expected_output"], "$.record.expected_output")
    observation = _object(record["observation"], "$.record.observation")
    expected_refs = [
        str(value)
        for value in _array(expected.get("evidence_refs"), "$.record.expected_output")
    ]
    observed_refs = [
        str(_object(region, "$.record.observation.regions[]")["ref"])
        for region in _array(observation.get("regions"), "$.record.observation.regions")
    ]
    alternate_refs = [ref for ref in observed_refs if ref not in expected_refs]
    if not expected_refs or not alternate_refs:
        _fail("VERIFIER_CASE_EVIDENCE_UNAVAILABLE", "$.record")
    wrong_answer = f"wrong-{str(record['record_id'])[7:19]}"
    if _normalize_answer(wrong_answer) == _normalize_answer(str(expected["answer"])):
        _fail("VERIFIER_WRONG_ANSWER_COLLISION", "$.record.expected_output.answer")
    case_payloads: dict[str, dict[str, Any]] = {
        "exact_expected": dict(expected),
        "wrong_answer": {**expected, "answer": wrong_answer},
        "wrong_evidence": {**expected, "evidence_refs": [alternate_refs[0]]},
        "duplicate_evidence": {
            **expected,
            "evidence_refs": [expected_refs[0], expected_refs[0]],
        },
        "wrong_page": {**expected, "page_number": 2},
    }
    expected_outcomes = {
        "exact_expected": (True, True, True, True, True),
        "wrong_answer": (True, False, True, True, False),
        "wrong_evidence": (True, True, False, True, False),
        "duplicate_evidence": (False, False, False, False, False),
        "wrong_page": (False, False, False, False, False),
    }
    cases: list[dict[str, Any]] = []
    for case_kind in VERIFIER_CASE_KINDS:
        raw_output = artifact_json_bytes(case_payloads[case_kind]).decode("utf-8")
        compiled = parent.compile_candidate_output(raw_output)
        verdict = parent.verify_candidate(compiled, record)
        observed_outcome = (
            compiled["valid"],
            verdict["answer_exact"],
            verdict["evidence_exact"],
            verdict["page_exact"],
            verdict["joint_correct"],
        )
        if observed_outcome != expected_outcomes[case_kind]:
            _fail(
                "REFERENCE_VERIFIER_OUTCOME_MISMATCH",
                f"$.record.{case_kind}",
            )
        case_identity = {
            "record_id": record["record_id"],
            "case_kind": case_kind,
            "raw_output": raw_output,
        }
        cases.append(
            {
                "verifier_case_version": VERIFIER_CASE_VERSION,
                "case_id": sha256_bytes(artifact_json_bytes(case_identity)),
                "record_id": record["record_id"],
                "case_kind": case_kind,
                "raw_output": raw_output,
                "raw_output_bytes": len(raw_output.encode("utf-8")),
                "raw_output_sha256": sha256_bytes(raw_output.encode("utf-8")),
                "compiler_valid": compiled["valid"],
                "compiler_error_code": compiled["error_code"],
                "verdict": verdict,
            }
        )
    return cases


def verifier_case_registry(
    records: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    registry: list[dict[str, Any]] = []
    for record in sorted(records, key=lambda item: str(item.get("record_id"))):
        registry.extend(verifier_cases_for_record(record))
    if len(registry) != len(records) * len(VERIFIER_CASE_KINDS):
        _fail("VERIFIER_CASE_COUNT_INVALID", "$.verifier_case_registry")
    case_ids = {str(case["case_id"]) for case in registry}
    if len(case_ids) != len(registry):
        _fail("DUPLICATE_VERIFIER_CASE_ID", "$.verifier_case_registry")
    return registry


def _validate_record(record: Mapping[str, Any], location: str) -> None:
    try:
        parent.verify_candidate({}, record)
    except (KeyError, TypeError, parent.MM005ProtocolError) as exc:
        raise MM005AdapterVerifierProtocolError(
            "RECORD_CONTRACT_INVALID", location
        ) from exc


def _contains_forbidden_key(value: object) -> bool:
    if isinstance(value, Mapping):
        return any(
            str(key) in FORBIDDEN_MODEL_PAYLOAD_KEYS or _contains_forbidden_key(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_forbidden_key(item) for item in value)
    return False


def _json_copy(value: object) -> object:
    import json

    return json.loads(artifact_json_bytes(value))


def _normalize_answer(value: str) -> str:
    return unicodedata.normalize("NFC", value).strip(" ")


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
    import json

    try:
        value = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MM005AdapterVerifierProtocolError("JSON_INVALID", location) from exc
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
    raise MM005AdapterVerifierProtocolError(code, location)
