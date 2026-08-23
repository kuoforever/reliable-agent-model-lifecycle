"""Model-free MM-005 environment-adaptation scope and interface contract."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any, NoReturn

PROTOCOL_VERSION = 1
RECORD_VERSION = 1
COMPILER_VERSION = 1
VERIFIER_VERSION = 1

GATE_ID = "MM-005-multimodal-environment-adaptation-protocol-v1"
NEXT_GATE = "MM-005-document-chart-pdf-data-protocol-v1"
SCOPE_ID = "synthetic-single-page-document-chart-pdf-visual-evidence-v1"
SELECTED_ENVIRONMENT = "document_chart_pdf"

ENVIRONMENT_ORDER = (
    "desktop_gui",
    "document_chart_pdf",
    "browser_research",
    "audio_video",
    "robotics_autonomous_driving_simulation_optional",
)
TASK_FAMILY_IDS = (
    "document_text_evidence_grounding",
    "table_cell_evidence_grounding",
    "chart_value_evidence_grounding",
    "page_region_selection",
)
SOURCE_KINDS = (
    "synthetic_text_document",
    "synthetic_table_document",
    "synthetic_bar_chart",
    "synthetic_single_page_pdf",
)
REGION_ROLES = frozenset(
    {
        "page",
        "title",
        "text",
        "table_header",
        "table_cell",
        "chart_axis",
        "chart_mark",
        "chart_legend",
    }
)
SPLITS = frozenset({"train", "validation"})
EXCLUSION_KEYS = (
    "case_ids",
    "family_ids",
    "instruction_content_sha256",
    "observation_content_sha256",
    "target_content_sha256",
    "image_sha256",
)
CONTENT_IDENTITY_KINDS = {
    "instruction": "instruction_content_sha256",
    "observation": "observation_content_sha256",
    "target": "target_content_sha256",
}
CLAIM_KEYS = (
    "environment_adapter_implemented",
    "task_set_materialized",
    "dataset_generated",
    "dataset_validated",
    "verifier_executed",
    "model_trained",
    "model_evaluated",
    "quality_improved",
    "safety_established",
    "real_content_collected",
    "capture_adapter_used",
    "runtime_repository_changed",
    "runtime_integration_changed",
    "serving_eligible",
    "promotion_eligible",
    "runtime_eligible",
)
REQUIRED_GATES = (
    "protocol_integrity",
    "source_receipt_integrity",
    "environment_sequence_integrity",
    "single_vertical_scope_bounded",
    "four_component_delta_closed",
    "adapter_interface_closed",
    "task_record_shape_closed",
    "deterministic_verifier_total",
    "synthetic_source_only",
    "real_content_and_capture_excluded",
    "prior_content_exclusion_registry",
    "family_and_content_split_isolation",
    "inherited_systems_not_duplicated",
    "runtime_authority_preserved",
    "fail_closed_claims",
)

_ID = re.compile(r"[a-z0-9][a-z0-9._-]{0,127}\Z")
_SHA256 = re.compile(r"sha256:[0-9a-f]{64}\Z")


class MM005ProtocolError(ValueError):
    """Stable fail-closed error for MM-005 protocol and future records."""

    def __init__(self, code: str, location: str = "$") -> None:
        self.code = code
        self.location = location
        super().__init__(f"{code} at {location}")


@dataclass(frozen=True)
class ProtocolSummary:
    protocol_version: int
    gate_id: str
    selected_environment: str
    task_family_count: int
    source_receipt_count: int
    excluded_case_count: int
    excluded_family_count: int
    excluded_image_count: int
    protocol_frozen: bool
    dataset_generated: bool
    next_gate: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )


def sha256_bytes(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def content_identity(kind: str, value: object) -> str:
    """Return the shared cross-stage content identity used for exclusions."""

    if kind not in CONTENT_IDENTITY_KINDS:
        _fail("CONTENT_IDENTITY_KIND_INVALID", "$.identity.kind")
    payload = (
        b"fullcycle:cross-stage-content:"
        + kind.encode("ascii")
        + b":v1\0"
        + canonical_json_bytes(value)
    )
    return sha256_bytes(payload)


def local_identity(kind: str, value: object) -> str:
    if kind not in {"family", "record"}:
        _fail("LOCAL_IDENTITY_KIND_INVALID", "$.identity.kind")
    payload = b"mm005:" + kind.encode("ascii") + b":v1\0" + canonical_json_bytes(value)
    return sha256_bytes(payload)


def expected_protocol(
    *,
    freeze_status: str,
    source_receipts: Mapping[str, Mapping[str, Any]],
    exclusions: Mapping[str, Sequence[str]],
) -> dict[str, Any]:
    if freeze_status not in {"draft", "frozen"}:
        _fail("FREEZE_STATUS_INVALID", "$.freeze_status")
    receipts = _validate_source_receipts(source_receipts)
    registry = _validate_exclusions(exclusions)
    return {
        "mm005_environment_adaptation_protocol_version": PROTOCOL_VERSION,
        "gate_id": GATE_ID,
        "freeze_status": freeze_status,
        "decision": "model_free_bounded_environment_adapter_scope_protocol",
        "source_lineage": {
            "receipts": receipts,
            "usage": "read_only_sequence_boundary_and_cross_stage_exclusion",
            "mm004_result_review_required": True,
            "mm004_consumed_output_may_be_deleted_reused_or_retried": False,
            "runtime_freeze_may_be_silently_advanced": False,
            "lane_b_capture_may_be_enabled": False,
        },
        "environment_sequence": {
            "registered_order": list(ENVIRONMENT_ORDER),
            "prior_environment": "desktop_gui",
            "prior_scope_status": (
                "synthetic_mm001_through_mm004_measurement_chain_complete_"
                "without_runtime_deployment"
            ),
            "selected_environment": SELECTED_ENVIRONMENT,
            "selected_order_index": 2,
            "deferred_environments": list(ENVIRONMENT_ORDER[2:]),
            "sequence_skip_allowed": False,
        },
        "selected_scope": {
            "scope_id": SCOPE_ID,
            "vertical_mvp": "single_page_visual_answer_with_exact_evidence_refs",
            "content_language": "en",
            "page_count": 1,
            "page_image_required": True,
            "sanitized_layout_observation_required": True,
            "source_kinds": list(SOURCE_KINDS),
            "max_layout_regions": 64,
            "max_visible_text_chars_per_region": 512,
            "max_table_rows": 8,
            "max_table_columns": 6,
            "max_chart_series": 2,
            "max_chart_marks": 8,
            "included": [
                "synthetic_rendered_text",
                "synthetic_tables",
                "synthetic_bar_charts",
                "synthetic_single_page_pdf_rendering",
                "answer_and_region_evidence_grounding",
            ],
            "deferred": [
                "multi_page_documents",
                "scanned_or_noisy_ocr",
                "handwriting",
                "real_user_or_external_documents",
                "browser_research",
                "audio_video",
                "robotics_or_autonomous_driving",
                "tool_or_desktop_execution",
            ],
        },
        "component_delta_contract": {
            "new_component_kinds": [
                "environment_adapter",
                "task_set",
                "deterministic_verifier",
                "synthetic_dataset",
            ],
            "new_component_count": 4,
            "inherited_without_duplication": [
                "training_orchestration",
                "evaluation_lifecycle",
                "serving_and_model_routing",
                "policy",
                "approval",
                "write_ahead_log",
                "grounding_authority",
                "budgets",
                "recovery",
                "desktop_dispatch",
            ],
            "environment_specific_training_pipeline_allowed": False,
            "environment_specific_serving_stack_allowed": False,
            "environment_specific_policy_approval_wal_or_recovery_allowed": False,
        },
        "adapter_contract": {
            "adapter_id": "document-chart-pdf-input-projection-v1",
            "adapter_kind": "model_input_and_output_projection_contract",
            "weights_created_at_this_gate": False,
            "input_projection": {
                "required_record_fields": [
                    "instruction",
                    "observation",
                    "task_family_id",
                    "source_kind",
                ],
                "gold_or_verifier_fields_exposed_to_model": False,
                "real_file_path_exposed_to_model": False,
            },
            "output_projection": {
                "format": "strict_json_object",
                "exact_keys": ["answer", "evidence_refs", "page_number"],
                "extra_keys_allowed": False,
                "invalid_output_is_wrong": True,
                "compiler_version": COMPILER_VERSION,
            },
        },
        "task_set_contract": {
            "task_family_ids": list(TASK_FAMILY_IDS),
            "source_kinds": list(SOURCE_KINDS),
            "task_source_compatibility": _task_source_compatibility(),
            "answer_types": ["text_span", "scalar", "region_id"],
            "execution_task": False,
            "model_output_has_execution_authority": False,
            "counts_and_generation_seed_deferred_to_next_gate": True,
        },
        "record_contract": {
            "record_version": RECORD_VERSION,
            "splits": ["train", "validation"],
            "required_fields": [
                "mm005_document_page_record_version",
                "record_id",
                "family_id",
                "template_id",
                "split",
                "task_family_id",
                "source_kind",
                "instruction",
                "observation",
                "expected_output",
                "verifier",
                "provenance",
                "identities",
            ],
            "observation": {
                "exact_keys": [
                    "image_sha256",
                    "layout_source",
                    "page_count",
                    "page_number",
                    "regions",
                ],
                "page_number": 1,
                "page_count": 1,
                "layout_source": "synthetic_ground_truth_not_runtime_ocr",
                "bbox_coordinate_space": "normalized_0_1000_xyxy",
                "allowed_region_roles": sorted(REGION_ROLES),
            },
            "expected_output": {
                "exact_keys": ["answer", "evidence_refs", "page_number"],
                "evidence_refs_must_exist_in_observation": True,
                "page_number": 1,
            },
            "identities": {
                "record_and_family": "mm005_domain_separated_sha256",
                "cross_stage_content": (
                    "fullcycle_cross_stage_content_domain_sha256_v1"
                ),
                "family_basis": [
                    "task_family_id",
                    "source_kind",
                    "template_id",
                ],
                "record_id_excludes": ["record_id"],
            },
        },
        "verifier_contract": {
            "verifier_version": VERIFIER_VERSION,
            "model_or_llm_judge_used": False,
            "answer_match": "unicode_nfc_then_ascii_space_trim_exact",
            "evidence_match": "exact_ordered_unique_region_refs",
            "page_match": "exact_integer",
            "extra_output_keys_invalid": True,
            "invalid_output_is_wrong": True,
            "metrics_required_at_future_eval": [
                "answer_exact_accuracy",
                "evidence_exact_accuracy",
                "joint_answer_evidence_accuracy",
                "compiler_validity",
                "per_task_family",
                "per_source_kind",
                "per_split",
            ],
            "quality_threshold_deferred": True,
        },
        "exclusion_registry": registry,
        "split_policy": {
            "family_disjoint_across_splits": True,
            "template_disjoint_across_splits": True,
            "instruction_content_disjoint_across_splits": True,
            "observation_content_disjoint_across_splits": True,
            "target_content_disjoint_across_splits": True,
            "image_disjoint_across_splits": True,
            "all_prior_exclusion_collisions_prohibited": True,
        },
        "provenance_policy": {
            "deterministic_reviewed_synthetic_only": True,
            "repository_generated_license_only": True,
            "real_document_collection": False,
            "external_document_download": False,
            "lane_a_rich_content": False,
            "lane_b_capture": False,
            "runtime_ocr_or_document_text_claimed": False,
        },
        "authority_contract": {
            "model_output_has_execution_authority": False,
            "runtime_is_sole_policy_approval_wal_grounding_budget_dispatch_boundary": True,
            "runtime_repository_changed": False,
            "runtime_integration_authorized": False,
            "capture_authorized": False,
        },
        "required_gates": list(REQUIRED_GATES),
        "claims": {key: False for key in CLAIM_KEYS},
        "next_gate": NEXT_GATE,
    }


def validate_protocol(
    value: object,
    *,
    source_receipts: Mapping[str, Mapping[str, Any]],
    exclusions: Mapping[str, Sequence[str]],
) -> ProtocolSummary:
    root = _mapping(value, "$")
    expected = expected_protocol(
        freeze_status="frozen",
        source_receipts=source_receipts,
        exclusions=exclusions,
    )
    if root != expected:
        _fail("PROTOCOL_MISMATCH")
    claims = _mapping(root["claims"], "$.claims")
    if set(claims) != set(CLAIM_KEYS) or any(claims.values()):
        _fail("CLAIMS_NOT_FAIL_CLOSED", "$.claims")
    registry = _mapping(root["exclusion_registry"], "$.exclusion_registry")
    return ProtocolSummary(
        protocol_version=PROTOCOL_VERSION,
        gate_id=GATE_ID,
        selected_environment=SELECTED_ENVIRONMENT,
        task_family_count=len(TASK_FAMILY_IDS),
        source_receipt_count=len(source_receipts),
        excluded_case_count=len(_sequence(registry["case_ids"], "$.case_ids")),
        excluded_family_count=len(
            _sequence(registry["family_ids"], "$.family_ids")
        ),
        excluded_image_count=len(
            _sequence(registry["image_sha256"], "$.image_sha256")
        ),
        protocol_frozen=True,
        dataset_generated=False,
        next_gate=NEXT_GATE,
    )


def build_record(
    *,
    template_id: str,
    split: str,
    task_family_id: str,
    source_kind: str,
    instruction: str,
    observation: Mapping[str, Any],
    expected_output: Mapping[str, Any],
    provenance: Mapping[str, Any],
) -> dict[str, Any]:
    family_basis = {
        "task_family_id": task_family_id,
        "source_kind": source_kind,
        "template_id": template_id,
    }
    body: dict[str, Any] = {
        "mm005_document_page_record_version": RECORD_VERSION,
        "family_id": local_identity("family", family_basis),
        "template_id": template_id,
        "split": split,
        "task_family_id": task_family_id,
        "source_kind": source_kind,
        "instruction": instruction,
        "observation": dict(observation),
        "expected_output": dict(expected_output),
        "verifier": _verifier_record(),
        "provenance": dict(provenance),
        "identities": {
            "instruction_content_sha256": content_identity(
                "instruction", instruction
            ),
            "observation_content_sha256": content_identity(
                "observation", observation
            ),
            "target_content_sha256": content_identity("target", expected_output),
            "image_sha256": [observation.get("image_sha256")],
        },
    }
    record = {"record_id": local_identity("record", body), **body}
    _validate_record(record, "$")
    return record


def validate_records(
    records_value: object, exclusions: Mapping[str, Sequence[str]]
) -> dict[str, Any]:
    records = _sequence(records_value, "$")
    if not records:
        _fail("RECORDS_EMPTY")
    registry = {
        key: set(values) for key, values in _validate_exclusions(exclusions).items()
    }
    split_values: dict[str, dict[str, set[str]]] = {
        split: {
            "family_ids": set(),
            "template_ids": set(),
            "instruction_content_sha256": set(),
            "observation_content_sha256": set(),
            "target_content_sha256": set(),
            "image_sha256": set(),
        }
        for split in SPLITS
    }
    seen_records: set[str] = set()
    task_families: set[str] = set()
    source_kinds: set[str] = set()
    for index, raw in enumerate(records):
        location = f"$[{index}]"
        record = _validate_record(raw, location)
        record_id = str(record["record_id"])
        family_id = str(record["family_id"])
        if record_id in seen_records:
            _fail("DUPLICATE_RECORD_ID", f"{location}.record_id")
        seen_records.add(record_id)
        if record_id in registry["case_ids"] or family_id in registry["family_ids"]:
            _fail("PRIOR_EXCLUSION_COLLISION", location)
        task_families.add(str(record["task_family_id"]))
        source_kinds.add(str(record["source_kind"]))
        split = str(record["split"])
        identities = _mapping(record["identities"], f"{location}.identities")
        split_values[split]["family_ids"].add(family_id)
        split_values[split]["template_ids"].add(str(record["template_id"]))
        for key in EXCLUSION_KEYS[2:5]:
            value = str(identities[key])
            if value in registry[key]:
                _fail("PRIOR_EXCLUSION_COLLISION", f"{location}.identities.{key}")
            split_values[split][key].add(value)
        for image_hash in _sequence(
            identities["image_sha256"], f"{location}.identities.image_sha256"
        ):
            if image_hash in registry["image_sha256"]:
                _fail(
                    "PRIOR_EXCLUSION_COLLISION",
                    f"{location}.identities.image_sha256",
                )
            split_values[split]["image_sha256"].add(image_hash)
    if task_families != set(TASK_FAMILY_IDS):
        _fail("INCOMPLETE_TASK_FAMILY_COVERAGE")
    if source_kinds != set(SOURCE_KINDS):
        _fail("INCOMPLETE_SOURCE_KIND_COVERAGE")
    observed_splits = {str(_mapping(record, "$")["split"]) for record in records}
    if observed_splits != SPLITS:
        _fail("INCOMPLETE_SPLIT_COVERAGE")
    for key in split_values["train"]:
        if split_values["train"][key] & split_values["validation"][key]:
            _fail("CROSS_SPLIT_LEAKAGE", f"$.{key}")
    return {
        "record_count": len(records),
        "family_count": len(
            {str(_mapping(record, "$")["family_id"]) for record in records}
        ),
        "task_family_count": len(task_families),
        "source_kind_count": len(source_kinds),
        "splits": sorted(observed_splits),
    }


def compile_candidate_output(raw_output: str) -> dict[str, Any]:
    invalid: dict[str, Any] = {
        "compiler_version": COMPILER_VERSION,
        "valid": False,
        "answer": "",
        "evidence_refs": [],
        "page_number": None,
        "error_code": "invalid_output",
    }
    if not isinstance(raw_output, str):
        return invalid
    try:
        if len(raw_output.encode("utf-8")) > 8_192:
            return invalid
    except UnicodeEncodeError:
        return invalid
    try:
        parsed = json.loads(
            raw_output,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (TypeError, ValueError, json.JSONDecodeError):
        return invalid
    if not isinstance(parsed, dict) or set(parsed) != {
        "answer",
        "evidence_refs",
        "page_number",
    }:
        return invalid
    answer = parsed.get("answer")
    refs = parsed.get("evidence_refs")
    page_number = parsed.get("page_number")
    if (
        type(answer) is not str
        or not answer
        or len(answer) > 512
        or not isinstance(refs, list)
        or not refs
        or len(refs) > 16
        or any(type(ref) is not str or not _ID.fullmatch(ref) for ref in refs)
        or len(set(refs)) != len(refs)
        or type(page_number) is not int
        or page_number != 1
    ):
        return invalid
    return {
        "compiler_version": COMPILER_VERSION,
        "valid": True,
        "answer": answer,
        "evidence_refs": list(refs),
        "page_number": page_number,
        "error_code": None,
    }


def verify_candidate(
    compiled: object, record: Mapping[str, Any]
) -> dict[str, Any]:
    checked_record = _validate_record(record, "$.record")
    expected = _mapping(checked_record["expected_output"], "$.record.expected_output")
    candidate = compiled if isinstance(compiled, Mapping) else {}
    valid = _compiled_output_is_well_formed(candidate) and candidate["valid"] is True
    answer_exact = valid and _normalize_answer(str(candidate["answer"])) == (
        _normalize_answer(str(expected["answer"]))
    )
    evidence_exact = valid and candidate["evidence_refs"] == expected["evidence_refs"]
    page_exact = valid and candidate["page_number"] == expected["page_number"]
    return {
        "verifier_version": VERIFIER_VERSION,
        "valid_output": valid,
        "answer_exact": answer_exact,
        "evidence_exact": evidence_exact,
        "page_exact": page_exact,
        "joint_correct": answer_exact and evidence_exact and page_exact,
        "model_judge_used": False,
    }


def _validate_record(value: object, location: str) -> Mapping[str, Any]:
    record = _mapping(value, location)
    required = {
        "mm005_document_page_record_version",
        "record_id",
        "family_id",
        "template_id",
        "split",
        "task_family_id",
        "source_kind",
        "instruction",
        "observation",
        "expected_output",
        "verifier",
        "provenance",
        "identities",
    }
    if set(record) != required:
        _fail("RECORD_KEYS_INVALID", location)
    if (
        type(record["mm005_document_page_record_version"]) is not int
        or record["mm005_document_page_record_version"] != RECORD_VERSION
    ):
        _fail("RECORD_VERSION_INVALID", f"{location}.version")
    for key in ("record_id", "family_id"):
        if type(record[key]) is not str or not _SHA256.fullmatch(str(record[key])):
            _fail("RECORD_ID_INVALID", f"{location}.{key}")
    for key in ("template_id", "task_family_id", "source_kind"):
        if type(record[key]) is not str or not _ID.fullmatch(str(record[key])):
            _fail("RECORD_ENUM_INVALID", f"{location}.{key}")
    if record["split"] not in SPLITS:
        _fail("RECORD_SPLIT_INVALID", f"{location}.split")
    if record["task_family_id"] not in TASK_FAMILY_IDS:
        _fail("TASK_FAMILY_INVALID", f"{location}.task_family_id")
    if record["source_kind"] not in SOURCE_KINDS:
        _fail("SOURCE_KIND_INVALID", f"{location}.source_kind")
    compatibility = _task_source_compatibility()[str(record["task_family_id"])]
    if record["source_kind"] not in compatibility:
        _fail("TASK_SOURCE_INCOMPATIBLE", location)
    instruction = record["instruction"]
    if type(instruction) is not str or not instruction or len(instruction) > 1_024:
        _fail("INSTRUCTION_INVALID", f"{location}.instruction")
    observation = _validate_observation(record["observation"], f"{location}.observation")
    expected = _validate_expected_output(
        record["expected_output"],
        observation=observation,
        location=f"{location}.expected_output",
    )
    if record["verifier"] != _verifier_record():
        _fail("VERIFIER_CONTRACT_INVALID", f"{location}.verifier")
    _validate_provenance(record["provenance"], f"{location}.provenance")
    identities = _mapping(record["identities"], f"{location}.identities")
    expected_identities = {
        "instruction_content_sha256": content_identity("instruction", instruction),
        "observation_content_sha256": content_identity("observation", observation),
        "target_content_sha256": content_identity("target", expected),
        "image_sha256": [observation["image_sha256"]],
    }
    if identities != expected_identities:
        _fail("CONTENT_IDENTITY_MISMATCH", f"{location}.identities")
    expected_family = local_identity(
        "family",
        {
            "task_family_id": record["task_family_id"],
            "source_kind": record["source_kind"],
            "template_id": record["template_id"],
        },
    )
    if record["family_id"] != expected_family:
        _fail("FAMILY_IDENTITY_MISMATCH", f"{location}.family_id")
    body = {key: record[key] for key in record if key != "record_id"}
    if record["record_id"] != local_identity("record", body):
        _fail("RECORD_IDENTITY_MISMATCH", f"{location}.record_id")
    return record


def _validate_observation(value: object, location: str) -> Mapping[str, Any]:
    observation = _mapping(value, location)
    if set(observation) != {
        "image_sha256",
        "layout_source",
        "page_count",
        "page_number",
        "regions",
    }:
        _fail("OBSERVATION_KEYS_INVALID", location)
    if (
        type(observation["page_number"]) is not int
        or type(observation["page_count"]) is not int
        or observation["page_number"] != 1
        or observation["page_count"] != 1
    ):
        _fail("SINGLE_PAGE_SCOPE_VIOLATION", location)
    if observation["layout_source"] != "synthetic_ground_truth_not_runtime_ocr":
        _fail("LAYOUT_SOURCE_INVALID", f"{location}.layout_source")
    if type(observation["image_sha256"]) is not str or not _SHA256.fullmatch(
        str(observation["image_sha256"])
    ):
        _fail("IMAGE_SHA256_INVALID", f"{location}.image_sha256")
    regions = _sequence(observation["regions"], f"{location}.regions")
    if not regions or len(regions) > 64:
        _fail("REGION_COUNT_INVALID", f"{location}.regions")
    refs: set[str] = set()
    for index, raw in enumerate(regions):
        region_location = f"{location}.regions[{index}]"
        region = _mapping(raw, region_location)
        if set(region) != {"bbox", "ref", "role", "visible_text"}:
            _fail("REGION_KEYS_INVALID", region_location)
        ref = region["ref"]
        if type(ref) is not str or not _ID.fullmatch(str(ref)) or ref in refs:
            _fail("REGION_REF_INVALID", f"{region_location}.ref")
        refs.add(str(ref))
        if region["role"] not in REGION_ROLES:
            _fail("REGION_ROLE_INVALID", f"{region_location}.role")
        bbox = region["bbox"]
        if (
            not isinstance(bbox, list)
            or len(bbox) != 4
            or any(type(item) is not int or item < 0 or item > 1_000 for item in bbox)
            or bbox[0] >= bbox[2]
            or bbox[1] >= bbox[3]
        ):
            _fail("REGION_BBOX_INVALID", f"{region_location}.bbox")
        visible_text = region["visible_text"]
        if visible_text is not None and (
            type(visible_text) is not str or len(visible_text) > 512
        ):
            _fail("REGION_TEXT_INVALID", f"{region_location}.visible_text")
    return observation


def _validate_expected_output(
    value: object, *, observation: Mapping[str, Any], location: str
) -> Mapping[str, Any]:
    expected = _mapping(value, location)
    if set(expected) != {"answer", "evidence_refs", "page_number"}:
        _fail("EXPECTED_OUTPUT_KEYS_INVALID", location)
    if (
        type(expected["answer"]) is not str
        or not expected["answer"]
        or len(expected["answer"]) > 512
        or type(expected["page_number"]) is not int
        or expected["page_number"] != 1
    ):
        _fail("EXPECTED_OUTPUT_VALUE_INVALID", location)
    refs = expected["evidence_refs"]
    if (
        not isinstance(refs, list)
        or not refs
        or len(refs) > 16
        or any(type(ref) is not str for ref in refs)
        or len(set(refs)) != len(refs)
    ):
        _fail("EXPECTED_EVIDENCE_REFS_INVALID", f"{location}.evidence_refs")
    observed_refs = {
        str(_mapping(region, "$.region")["ref"])
        for region in _sequence(observation["regions"], "$.observation.regions")
    }
    if any(ref not in observed_refs for ref in refs):
        _fail("EXPECTED_EVIDENCE_REF_MISSING", f"{location}.evidence_refs")
    return expected


def _validate_provenance(value: object, location: str) -> None:
    provenance = _mapping(value, location)
    expected = {
        "source": "deterministic_reviewed_synthetic_generation",
        "license": "repository_generated_synthetic",
        "synthetic_only": True,
        "real_content": False,
        "capture_adapter_used": False,
        "runtime_ocr_used": False,
        "model_output_has_execution_authority": False,
        "runtime_integration_authorized": False,
    }
    if provenance != expected:
        _fail("PROVENANCE_INVALID", location)


def _verifier_record() -> dict[str, Any]:
    return {
        "verifier_version": VERIFIER_VERSION,
        "answer_match": "unicode_nfc_then_ascii_space_trim_exact",
        "evidence_match": "exact_ordered_unique_region_refs",
        "page_match": "exact_integer",
        "invalid_output_is_wrong": True,
        "model_or_llm_judge_used": False,
    }


def _task_source_compatibility() -> dict[str, list[str]]:
    return {
        "document_text_evidence_grounding": [
            "synthetic_text_document",
            "synthetic_single_page_pdf",
        ],
        "table_cell_evidence_grounding": [
            "synthetic_table_document",
            "synthetic_single_page_pdf",
        ],
        "chart_value_evidence_grounding": [
            "synthetic_bar_chart",
            "synthetic_single_page_pdf",
        ],
        "page_region_selection": list(SOURCE_KINDS),
    }


def _normalize_answer(value: str) -> str:
    return unicodedata.normalize("NFC", value).strip(" ")


def _compiled_output_is_well_formed(value: Mapping[str, Any]) -> bool:
    if set(value) != {
        "compiler_version",
        "valid",
        "answer",
        "evidence_refs",
        "page_number",
        "error_code",
    }:
        return False
    if type(value["compiler_version"]) is not int or (
        value["compiler_version"] != COMPILER_VERSION
    ):
        return False
    if type(value["valid"]) is not bool:
        return False
    if value["valid"] is False:
        return (
            value["answer"] == ""
            and value["evidence_refs"] == []
            and value["page_number"] is None
            and value["error_code"] == "invalid_output"
        )
    refs = value["evidence_refs"]
    return (
        type(value["answer"]) is str
        and bool(value["answer"])
        and len(value["answer"]) <= 512
        and isinstance(refs, list)
        and 0 < len(refs) <= 16
        and all(type(ref) is str and _ID.fullmatch(ref) for ref in refs)
        and len(set(refs)) == len(refs)
        and type(value["page_number"]) is int
        and value["page_number"] == 1
        and value["error_code"] is None
    )


def _unique_object(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def _reject_constant(value: str) -> NoReturn:
    raise ValueError(f"invalid JSON constant: {value}")


def _validate_source_receipts(
    value: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    if not value:
        _fail("SOURCE_RECEIPTS_EMPTY", "$.source_receipts")
    allowed_roles = {
        "protocol_source",
        "sequencing_evidence",
        "read_only_exclusion",
        "runtime_boundary",
        "capture_boundary",
    }
    result: dict[str, dict[str, Any]] = {}
    for name, raw in sorted(value.items()):
        if not _ID.fullmatch(name):
            _fail("SOURCE_RECEIPT_NAME_INVALID", f"$.source_receipts.{name}")
        receipt = _mapping(raw, f"$.source_receipts.{name}")
        if set(receipt) != {"path", "bytes", "sha256", "role"}:
            _fail("SOURCE_RECEIPT_KEYS_INVALID", f"$.source_receipts.{name}")
        if (
            type(receipt["path"]) is not str
            or not receipt["path"]
            or type(receipt["bytes"]) is not int
            or receipt["bytes"] <= 0
            or type(receipt["sha256"]) is not str
            or not _SHA256.fullmatch(str(receipt["sha256"]))
            or receipt["role"] not in allowed_roles
        ):
            _fail("SOURCE_RECEIPT_VALUE_INVALID", f"$.source_receipts.{name}")
        result[name] = dict(receipt)
    return result


def _validate_exclusions(
    value: Mapping[str, Sequence[str]],
) -> dict[str, list[str]]:
    if set(value) != set(EXCLUSION_KEYS):
        _fail("EXCLUSION_KEYS_INVALID", "$.exclusions")
    result: dict[str, list[str]] = {}
    for key in EXCLUSION_KEYS:
        raw = value[key]
        if isinstance(raw, (str, bytes, bytearray)) or not isinstance(raw, Sequence):
            _fail("EXCLUSION_VALUES_INVALID", f"$.exclusions.{key}")
        items = list(raw)
        if any(type(item) is not str or not item for item in items):
            _fail("EXCLUSION_VALUES_INVALID", f"$.exclusions.{key}")
        if items != sorted(set(items)):
            _fail("EXCLUSION_ORDER_INVALID", f"$.exclusions.{key}")
        if key in {"case_ids", "family_ids"} and any(
            not (_ID.fullmatch(item) or _SHA256.fullmatch(item)) for item in items
        ):
            _fail("EXCLUSION_ID_INVALID", f"$.exclusions.{key}")
        if key not in {"case_ids", "family_ids"} and any(
            not _SHA256.fullmatch(item) for item in items
        ):
            _fail("EXCLUSION_SHA256_INVALID", f"$.exclusions.{key}")
        result[key] = items
    return result


def _mapping(value: object, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail("EXPECTED_OBJECT", location)
    return value


def _sequence(value: object, location: str) -> list[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        _fail("EXPECTED_ARRAY", location)
    return list(value)


def _fail(code: str, location: str = "$") -> NoReturn:
    raise MM005ProtocolError(code, location)
