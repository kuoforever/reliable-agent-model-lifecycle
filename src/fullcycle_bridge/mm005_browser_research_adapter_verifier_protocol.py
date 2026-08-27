"""Fail-closed protocol for the MM-005 Browser Research Adapter and Verifier."""

from __future__ import annotations

import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, NoReturn

from . import browser_research_environment_adaptation as parent
from . import mm005_browser_research_data as data
from . import mm005_browser_research_generation as generation

PROTOCOL_VERSION = 1
ADAPTER_PROJECTION_VERSION = 1
VERIFIER_CASE_VERSION = 1

GATE_ID = "MM-005-browser-research-adapter-verifier-protocol-v1"
NEXT_GATE = "MM-005-browser-research-adapter-verifier-implementation-v1"
PROTOCOL_PATH = "configs/mm005_browser_research_adapter_verifier_protocol_v1.json"
GENERATION_RESULT_MERGE_COMMIT = "6e990f0cf8ba4f76bd35a57479c3649c4cadc3aa"

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
        "path",
        "provenance",
        "record_id",
        "screenshot_path",
        "source_snapshot_identity_sha256",
        "source_snapshot_path",
        "source_url_identity_sha256",
        "split",
        "template_id",
        "verifier",
    }
)
VERIFIER_CASE_KINDS = (
    "exact_expected",
    "wrong_answer",
    "wrong_dom_ref",
    "unknown_dom_ref",
    "wrong_citation_sequence_or_coverage",
    "duplicate_citation",
    "malformed_json",
)

PROTOCOL_CLAIMS = {
    **generation.EXECUTION_CLAIMS,
    "environment_adapter_executed": False,
    "verifier_implemented": False,
}

REQUIRED_GATES = (
    "generation_result_publication_integrity",
    "generation_evidence_integrity",
    "source_receipt_integrity",
    "dataset_tree_integrity",
    "record_contract_integrity",
    "source_snapshot_receipt_binding",
    "screenshot_receipt_binding",
    "adapter_projection_closure",
    "model_payload_gold_isolation",
    "artifact_paths_outside_model_payload",
    "output_compiler_contract",
    "verifier_case_closure",
    "verifier_positive_controls",
    "verifier_negative_controls",
    "citation_source_binding_controls",
    "multi_source_and_freshness_controls",
    "task_source_split_coverage",
    "model_network_browser_and_capture_absence",
    "runtime_authority_preserved",
    "implementation_deferred",
    "fail_closed_claims",
)


class MM005BrowserResearchAdapterVerifierProtocolError(ValueError):
    """Stable fail-closed error for Browser Adapter/Verifier protocol drift."""

    def __init__(self, code: str, location: str = "$") -> None:
        self.code = code
        self.location = location
        super().__init__(f"{code} at {location}")


@dataclass(frozen=True)
class AdapterVerifierProtocolSummary:
    protocol_version: int
    source_receipt_count: int
    record_count: int
    source_binding_count: int
    screenshot_binding_count: int
    source_snapshot_binding_count: int
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

    records, source_bindings, dataset_receipts = dataset_context(output_payloads)
    try:
        record_summary = parent.validate_records(records, exclusions)
    except parent.MM005BrowserResearchProtocolError as exc:
        raise MM005BrowserResearchAdapterVerifierProtocolError(
            "RECORD_CONTRACT_INVALID", "$.dataset.records"
        ) from exc
    projections = adapter_projection_registry(records, source_bindings)
    verifier_cases = verifier_case_registry(records)
    positive_cases = sum(
        1 for case in verifier_cases if case["case_kind"] == "exact_expected"
    )
    negative_cases = len(verifier_cases) - positive_cases
    if positive_cases != len(records) or negative_cases != len(records) * 6:
        _fail("VERIFIER_CASE_DISTRIBUTION_INVALID", "$.verifier_case_registry")

    split_counts = {
        split: sum(1 for record in records if record.get("split") == split)
        for split in sorted(parent.SPLITS)
    }
    summary = AdapterVerifierProtocolSummary(
        protocol_version=PROTOCOL_VERSION,
        source_receipt_count=len(sources),
        record_count=len(records),
        source_binding_count=len(source_bindings),
        screenshot_binding_count=len(source_bindings),
        source_snapshot_binding_count=len(source_bindings),
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
        "mm005_browser_research_adapter_verifier_protocol_version": (
            PROTOCOL_VERSION
        ),
        "gate_id": GATE_ID,
        "freeze_status": freeze_status,
        "decision": (
            "freeze_model_free_browser_adapter_projection_and_deterministic_"
            "citation_verifier_before_implementation"
        ),
        "source_receipts": sources,
        "upstream": {
            "generation_result_merge_commit": GENERATION_RESULT_MERGE_COMMIT,
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
                "model_payload",
                "record_id",
                "source_bindings",
            ],
            "model_payload_exact_keys": list(MODEL_PAYLOAD_KEYS),
            "forbidden_model_payload_keys": sorted(FORBIDDEN_MODEL_PAYLOAD_KEYS),
            "source_bindings_outside_model_payload": True,
            "screenshot_and_snapshot_paths_exposed_to_model": False,
            "gold_or_verifier_fields_exposed_to_model": False,
            "formal_implementation_present": False,
            "formal_execution_at_this_gate": False,
            "output_compiler": {
                "compiler_version": parent.COMPILER_VERSION,
                "format": "strict_json_object",
                "exact_keys": ["answer", "citation_refs"],
                "extra_keys_allowed": False,
                "duplicate_keys_allowed": False,
                "nonfinite_values_allowed": False,
                "utf8_byte_limit": 8_192,
                "answer_character_limit": 1_024,
                "citation_ref_limit": 12,
                "invalid_output_is_wrong": True,
            },
        },
        "source_artifact_registry": [
            source_bindings[source_id] for source_id in sorted(source_bindings)
        ],
        "adapter_projection_registry": projections,
        "verifier_contract": {
            "verifier_case_version": VERIFIER_CASE_VERSION,
            "verifier_version": parent.VERIFIER_VERSION,
            "case_kinds": list(VERIFIER_CASE_KINDS),
            "cases_per_record": len(VERIFIER_CASE_KINDS),
            "answer_match": "unicode_nfc_then_ascii_space_trim_exact",
            "citation_match": "exact_ordered_unique_source_bound_dom_refs",
            "freshness_check": "latest_published_source_must_be_cited",
            "multi_source_minimum_distinct_sources": 2,
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
            "source_bindings": len(source_bindings),
            "screenshot_bindings": len(source_bindings),
            "source_snapshot_bindings": len(source_bindings),
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
            "live_browser_allowed": False,
            "model_load_allowed": False,
            "model_training_or_evaluation_allowed": False,
            "real_or_external_content_allowed": False,
            "capture_allowed": False,
            "runtime_repository_change_allowed": False,
            "runtime_integration_allowed": False,
        },
        "required_gates": list(REQUIRED_GATES),
        "authority_contract": {
            "page_content_has_execution_authority": False,
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
    return AdapterVerifierProtocolSummary(**_object(expected["summary"], "$.summary"))


def dataset_context(
    output_payloads: Mapping[str, bytes],
) -> tuple[
    list[Mapping[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
]:
    records: list[Mapping[str, Any]] = []
    screenshot_receipts: dict[str, dict[str, Any]] = {}
    snapshot_receipts: dict[str, dict[str, Any]] = {}
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
                _object(raw_record, f"$.output_payloads.{path}.records[{index}]")
            )
        _collect_artifact_receipts(
            dataset.get("screenshot_receipts"),
            output_payloads=output_payloads,
            destination=screenshot_receipts,
            location=f"$.output_payloads.{path}.screenshot_receipts",
            artifact_kind="SCREENSHOT",
        )
        _collect_artifact_receipts(
            dataset.get("source_snapshot_receipts"),
            output_payloads=output_payloads,
            destination=snapshot_receipts,
            location=f"$.output_payloads.{path}.source_snapshot_receipts",
            artifact_kind="SOURCE_SNAPSHOT",
        )
        dataset_receipts[split] = _receipt(path, payload)

    manifest_payload = output_payloads.get(data.MANIFEST_PATH)
    if manifest_payload is None:
        _fail("MANIFEST_PAYLOAD_MISSING", "$.output_payloads")
    _json_object(manifest_payload, "$.output_payloads.manifest")
    dataset_receipts["manifest"] = _receipt(data.MANIFEST_PATH, manifest_payload)
    if (
        len(records) != data.RECORD_COUNT
        or len(screenshot_receipts) != data.SCREENSHOT_COUNT
        or len(snapshot_receipts) != data.SOURCE_SNAPSHOT_COUNT
    ):
        _fail("DATASET_COUNT_INVALID", "$.output_payloads")
    if len({item["sha256"] for item in screenshot_receipts.values()}) != len(
        screenshot_receipts
    ):
        _fail("SCREENSHOT_RECEIPT_HASH_COLLISION", "$.output_payloads")
    if len({item["sha256"] for item in snapshot_receipts.values()}) != len(
        snapshot_receipts
    ):
        _fail("SOURCE_SNAPSHOT_RECEIPT_HASH_COLLISION", "$.output_payloads")

    record_sources: dict[str, Mapping[str, Any]] = {}
    for record in records:
        observation = _object(record.get("observation"), "$.record.observation")
        for raw_source in _array(
            observation.get("sources"), "$.record.observation.sources"
        ):
            source = _object(raw_source, "$.record.observation.sources[]")
            source_id = source.get("source_id")
            if not isinstance(source_id, str) or source_id in record_sources:
                _fail("RECORD_SOURCE_ID_INVALID", "$.record.observation.sources[]")
            record_sources[source_id] = source

    source_bindings: dict[str, dict[str, Any]] = {}
    for snapshot_path, snapshot_receipt in sorted(snapshot_receipts.items()):
        snapshot_payload = output_payloads[snapshot_path]
        snapshot = _json_object(snapshot_payload, f"$.output_payloads.{snapshot_path}")
        snapshot_source = _object(
            snapshot.get("source"), f"$.output_payloads.{snapshot_path}.source"
        )
        source_id = snapshot_source.get("source_id")
        if not isinstance(source_id, str) or source_id in source_bindings:
            _fail("SOURCE_SNAPSHOT_ID_INVALID", f"$.output_payloads.{snapshot_path}")
        expected_source = record_sources.get(source_id)
        if expected_source is None or snapshot_source != expected_source:
            _fail("SOURCE_SNAPSHOT_RECORD_MISMATCH", f"$.output_payloads.{snapshot_path}")
        screenshot_path = snapshot.get("screenshot_path")
        if not isinstance(screenshot_path, str):
            _fail("SOURCE_SCREENSHOT_PATH_INVALID", f"$.output_payloads.{snapshot_path}")
        screenshot_receipt = screenshot_receipts.get(screenshot_path)
        if screenshot_receipt is None or screenshot_receipt["sha256"] != snapshot_source.get(
            "screenshot_sha256"
        ):
            _fail("SOURCE_SCREENSHOT_BINDING_INVALID", f"$.output_payloads.{snapshot_path}")
        source_bindings[source_id] = {
            "source_id": source_id,
            "screenshot": screenshot_receipt,
            "source_snapshot": snapshot_receipt,
        }
    if set(source_bindings) != set(record_sources):
        _fail("SOURCE_BINDING_CLOSURE_INVALID", "$.source_bindings")
    return records, source_bindings, dataset_receipts


def project_record(
    record: Mapping[str, Any],
    source_bindings: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    _validate_record(record, "$.record")
    observation = _object(record["observation"], "$.record.observation")
    bindings: list[dict[str, Any]] = []
    for raw_source in _array(observation.get("sources"), "$.record.observation.sources"):
        source = _object(raw_source, "$.record.observation.sources[]")
        source_id = str(source["source_id"])
        raw_binding = source_bindings.get(source_id)
        if raw_binding is None:
            _fail("RECORD_SOURCE_BINDING_MISSING", f"$.source_bindings.{source_id}")
        binding = _closed_source_binding(raw_binding, source_id=source_id)
        if binding["screenshot"]["sha256"] != source.get("screenshot_sha256"):
            _fail("RECORD_SCREENSHOT_BINDING_INVALID", f"$.source_bindings.{source_id}")
        bindings.append(binding)
    if len(bindings) != len(_array(observation["sources"], "$.observation.sources")):
        _fail("RECORD_SOURCE_BINDING_COUNT_INVALID", "$.record")

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
    for binding in bindings:
        for receipt_kind in ("screenshot", "source_snapshot"):
            if str(binding[receipt_kind]["path"]).encode("utf-8") in model_payload_bytes:
                _fail("MODEL_PAYLOAD_PATH_LEAKAGE", "$.model_payload")
    return {
        "adapter_projection_version": ADAPTER_PROJECTION_VERSION,
        "record_id": record["record_id"],
        "source_bindings": bindings,
        "model_payload": model_payload,
        "authority": {
            "page_content_has_execution_authority": False,
            "model_output_has_execution_authority": False,
            "runtime_integration_authorized": False,
            "gold_or_verifier_fields_exposed_to_model": False,
            "artifact_paths_exposed_to_model": False,
        },
    }


def adapter_projection_registry(
    records: Sequence[Mapping[str, Any]],
    source_bindings: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    registry: list[dict[str, Any]] = []
    seen_records: set[str] = set()
    for record in sorted(records, key=lambda item: str(item.get("record_id"))):
        projection = project_record(record, source_bindings)
        record_id = str(record["record_id"])
        if record_id in seen_records:
            _fail("DUPLICATE_PROJECTION_RECORD_ID", "$.adapter_projection_registry")
        seen_records.add(record_id)
        payload = artifact_json_bytes(projection)
        bindings = _array(projection["source_bindings"], "$.projection.source_bindings")
        registry.append(
            {
                "record_id": record_id,
                "split": record["split"],
                "task_family_id": record["task_family_id"],
                "source_kind": record["source_kind"],
                "source_count": len(bindings),
                "screenshot_sha256": [
                    _object(item, "$.binding")["screenshot"]["sha256"]
                    for item in bindings
                ],
                "source_snapshot_sha256": [
                    _object(item, "$.binding")["source_snapshot"]["sha256"]
                    for item in bindings
                ],
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
        for value in _array(expected.get("citation_refs"), "$.record.expected_output")
    ]
    observed_refs = _observed_ref_to_source(observation)
    alternate_refs = [ref for ref in observed_refs if ref not in expected_refs]
    if not expected_refs or not alternate_refs:
        _fail("VERIFIER_CASE_CITATION_UNAVAILABLE", "$.record")
    wrong_answer = f"wrong-{str(record['record_id'])[7:19]}"
    if _normalize_answer(wrong_answer) == _normalize_answer(str(expected["answer"])):
        _fail("VERIFIER_WRONG_ANSWER_COLLISION", "$.record.expected_output.answer")
    unknown_ref = f"unknown-{str(record['record_id'])[7:19]}"
    if unknown_ref in observed_refs:
        _fail("VERIFIER_UNKNOWN_REF_COLLISION", "$.record")
    sequence_or_coverage = _wrong_sequence_or_coverage_refs(
        record, expected_refs, alternate_refs, observed_refs
    )
    case_payloads: dict[str, dict[str, Any] | str] = {
        "exact_expected": dict(expected),
        "wrong_answer": {**expected, "answer": wrong_answer},
        "wrong_dom_ref": {
            **expected,
            "citation_refs": [alternate_refs[0], *expected_refs[1:]],
        },
        "unknown_dom_ref": {
            **expected,
            "citation_refs": [unknown_ref, *expected_refs[1:]],
        },
        "wrong_citation_sequence_or_coverage": {
            **expected,
            "citation_refs": sequence_or_coverage,
        },
        "duplicate_citation": {
            **expected,
            "citation_refs": [expected_refs[0], expected_refs[0]],
        },
        "malformed_json": '{"answer":',
    }
    expected_outcomes = {
        "exact_expected": (True, True, True, True),
        "wrong_answer": (True, False, True, False),
        "wrong_dom_ref": (True, True, False, False),
        "unknown_dom_ref": (True, True, False, False),
        "wrong_citation_sequence_or_coverage": (True, True, False, False),
        "duplicate_citation": (False, False, False, False),
        "malformed_json": (False, False, False, False),
    }
    cases: list[dict[str, Any]] = []
    for case_kind in VERIFIER_CASE_KINDS:
        case_payload = case_payloads[case_kind]
        raw_output = (
            case_payload
            if isinstance(case_payload, str)
            else artifact_json_bytes(case_payload).decode("utf-8")
        )
        compiled = parent.compile_candidate_output(raw_output)
        verdict = parent.verify_candidate(compiled, record)
        observed_outcome = (
            compiled["valid"],
            verdict["answer_exact"],
            verdict["citation_exact"],
            verdict["joint_correct"],
        )
        if observed_outcome != expected_outcomes[case_kind]:
            _fail("REFERENCE_VERIFIER_OUTCOME_MISMATCH", f"$.record.{case_kind}")
        semantics = citation_semantics(compiled, record)
        if case_kind == "exact_expected" and (
            semantics["all_citation_refs_bound"] is not True
            or semantics["minimum_source_coverage_met"] is not True
            or semantics["latest_source_cited"] is False
        ):
            _fail("REFERENCE_CITATION_SEMANTICS_MISMATCH", f"$.record.{case_kind}")
        if case_kind == "unknown_dom_ref" and semantics["all_citation_refs_bound"]:
            _fail("REFERENCE_UNKNOWN_REF_MISMATCH", f"$.record.{case_kind}")
        if (
            case_kind == "wrong_citation_sequence_or_coverage"
            and record["task_family_id"] == "freshness_conflict_resolution"
            and semantics["latest_source_cited"] is not False
        ):
            _fail("REFERENCE_FRESHNESS_CONTROL_MISMATCH", f"$.record.{case_kind}")
        identity = {
            "record_id": record["record_id"],
            "case_kind": case_kind,
            "raw_output": raw_output,
        }
        raw_bytes = raw_output.encode("utf-8")
        cases.append(
            {
                "verifier_case_version": VERIFIER_CASE_VERSION,
                "case_id": sha256_bytes(artifact_json_bytes(identity)),
                "record_id": record["record_id"],
                "case_kind": case_kind,
                "raw_output": raw_output,
                "raw_output_bytes": len(raw_bytes),
                "raw_output_sha256": sha256_bytes(raw_bytes),
                "compiler_valid": compiled["valid"],
                "compiler_error_code": compiled["error_code"],
                "citation_semantics": semantics,
                "verdict": verdict,
            }
        )
    return cases


def verifier_case_registry(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    registry: list[dict[str, Any]] = []
    for record in sorted(records, key=lambda item: str(item.get("record_id"))):
        registry.extend(verifier_cases_for_record(record))
    if len(registry) != len(records) * len(VERIFIER_CASE_KINDS):
        _fail("VERIFIER_CASE_COUNT_INVALID", "$.verifier_case_registry")
    if len({str(case["case_id"]) for case in registry}) != len(registry):
        _fail("DUPLICATE_VERIFIER_CASE_ID", "$.verifier_case_registry")
    return registry


def citation_semantics(
    compiled: Mapping[str, Any], record: Mapping[str, Any]
) -> dict[str, Any]:
    observation = _object(record["observation"], "$.record.observation")
    ref_to_source = _observed_ref_to_source(observation)
    valid = compiled.get("valid") is True
    raw_refs = compiled.get("citation_refs") if valid else []
    refs = raw_refs if isinstance(raw_refs, list) else []
    all_bound = valid and bool(refs) and all(
        isinstance(ref, str) and ref in ref_to_source for ref in refs
    )
    cited_sources: list[str] = []
    if all_bound:
        for ref in refs:
            source_id = ref_to_source[str(ref)]
            if source_id not in cited_sources:
                cited_sources.append(source_id)
    minimum = 1 if record["task_family_id"] == "single_source_fact_citation" else 2
    minimum_coverage = all_bound and len(cited_sources) >= minimum
    latest_source_cited: bool | None = None
    if record["task_family_id"] == "freshness_conflict_resolution":
        published = _source_published_at(observation)
        latest = max(published.values())
        latest_ids = {
            source_id for source_id, timestamp in published.items() if timestamp == latest
        }
        latest_source_cited = all_bound and bool(set(cited_sources) & latest_ids)
    return {
        "all_citation_refs_bound": all_bound,
        "cited_source_ids": cited_sources,
        "minimum_source_coverage_met": minimum_coverage,
        "latest_source_cited": latest_source_cited,
    }


def _wrong_sequence_or_coverage_refs(
    record: Mapping[str, Any],
    expected_refs: list[str],
    alternate_refs: list[str],
    ref_to_source: Mapping[str, str],
) -> list[str]:
    if record["task_family_id"] == "freshness_conflict_resolution":
        observation = _object(record["observation"], "$.record.observation")
        published = _source_published_at(observation)
        latest = max(published.values())
        latest_ids = {
            source_id for source_id, timestamp in published.items() if timestamp == latest
        }
        result = [ref for ref in expected_refs if ref_to_source[ref] not in latest_ids]
    elif len(expected_refs) > 1:
        result = list(reversed(expected_refs))
    else:
        result = [expected_refs[0], alternate_refs[0]]
    if not result or result == expected_refs or len(set(result)) != len(result):
        _fail("VERIFIER_SEQUENCE_CONTROL_INVALID", "$.record.expected_output")
    return result


def _observed_ref_to_source(observation: Mapping[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw_source in _array(observation.get("sources"), "$.observation.sources"):
        source = _object(raw_source, "$.observation.sources[]")
        source_id = str(source["source_id"])
        for raw_node in _array(source.get("dom_nodes"), "$.source.dom_nodes"):
            node = _object(raw_node, "$.source.dom_nodes[]")
            ref = str(node["ref"])
            if ref in result:
                _fail("DUPLICATE_OBSERVED_REF", "$.observation.sources")
            result[ref] = source_id
    return result


def _source_published_at(observation: Mapping[str, Any]) -> dict[str, datetime]:
    result: dict[str, datetime] = {}
    for raw_source in _array(observation.get("sources"), "$.observation.sources"):
        source = _object(raw_source, "$.observation.sources[]")
        try:
            timestamp = datetime.strptime(
                str(source["published_at"]), "%Y-%m-%dT%H:%M:%SZ"
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise MM005BrowserResearchAdapterVerifierProtocolError(
                "SOURCE_PUBLISHED_AT_INVALID", "$.observation.sources"
            ) from exc
        result[str(source["source_id"])] = timestamp
    return result


def _collect_artifact_receipts(
    value: object,
    *,
    output_payloads: Mapping[str, bytes],
    destination: dict[str, dict[str, Any]],
    location: str,
    artifact_kind: str,
) -> None:
    for artifact_path, raw_receipt in sorted(_object(value, location).items()):
        if artifact_path in destination:
            _fail(f"DUPLICATE_{artifact_kind}_RECEIPT", f"{location}.{artifact_path}")
        receipt = _closed_receipt(
            _object(raw_receipt, f"{location}.{artifact_path}"),
            expected_path=artifact_path,
            location=f"{location}.{artifact_path}",
        )
        payload = output_payloads.get(artifact_path)
        if payload is None or receipt != _receipt(artifact_path, payload):
            _fail(f"{artifact_kind}_RECEIPT_MISMATCH", f"{location}.{artifact_path}")
        destination[artifact_path] = receipt


def _closed_source_binding(
    value: Mapping[str, Any], *, source_id: str
) -> dict[str, Any]:
    if set(value) != {"source_id", "screenshot", "source_snapshot"}:
        _fail("SOURCE_BINDING_SHAPE_INVALID", f"$.source_bindings.{source_id}")
    if value.get("source_id") != source_id:
        _fail("SOURCE_BINDING_ID_INVALID", f"$.source_bindings.{source_id}")
    return {
        "source_id": source_id,
        "screenshot": _closed_receipt(
            _object(value.get("screenshot"), f"$.source_bindings.{source_id}.screenshot"),
            expected_path=None,
            location=f"$.source_bindings.{source_id}.screenshot",
        ),
        "source_snapshot": _closed_receipt(
            _object(
                value.get("source_snapshot"),
                f"$.source_bindings.{source_id}.source_snapshot",
            ),
            expected_path=None,
            location=f"$.source_bindings.{source_id}.source_snapshot",
        ),
    }


def _validate_record(record: Mapping[str, Any], location: str) -> None:
    try:
        parent.verify_candidate({}, record)
    except (KeyError, TypeError, parent.MM005BrowserResearchProtocolError) as exc:
        raise MM005BrowserResearchAdapterVerifierProtocolError(
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
    if not isinstance(path, str) or not path or (expected_path and path != expected_path):
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
        raise MM005BrowserResearchAdapterVerifierProtocolError(
            "JSON_INVALID", location
        ) from exc
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
    raise MM005BrowserResearchAdapterVerifierProtocolError(code, location)
