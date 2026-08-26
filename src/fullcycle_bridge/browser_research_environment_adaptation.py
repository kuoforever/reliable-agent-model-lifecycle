"""Model-free MM-005 Browser Research scope and interface contract."""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, NoReturn

from . import multimodal_environment_adaptation as parent

PROTOCOL_VERSION = 1
RECORD_VERSION = 1
COMPILER_VERSION = 1
VERIFIER_VERSION = 1

GATE_ID = "MM-005-browser-research-environment-adaptation-protocol-v1"
NEXT_GATE = "MM-005-browser-research-data-protocol-v1"
SCOPE_ID = "synthetic-static-browser-research-citation-grounding-v1"
SELECTED_ENVIRONMENT = "browser_research"

ENVIRONMENT_ORDER = parent.ENVIRONMENT_ORDER
TASK_FAMILY_IDS = (
    "single_source_fact_citation",
    "multi_source_synthesis_citation",
    "cross_source_comparison_citation",
    "freshness_conflict_resolution",
)
SOURCE_KINDS = (
    "synthetic_single_source_snapshot",
    "synthetic_corroborating_source_bundle",
    "synthetic_comparison_source_bundle",
    "synthetic_temporal_revision_bundle",
)
DOM_TAGS = frozenset(
    {
        "article",
        "caption",
        "h1",
        "h2",
        "li",
        "p",
        "table",
        "td",
        "th",
        "tr",
    }
)
SPLITS = frozenset({"train", "validation"})
EXCLUSION_KEYS = (
    *parent.EXCLUSION_KEYS,
    "source_url_sha256",
    "source_snapshot_sha256",
)
CLAIM_KEYS = (
    "environment_adapter_implemented",
    "task_set_materialized",
    "dataset_generated",
    "dataset_validated",
    "verifier_executed",
    "live_browser_used",
    "network_accessed",
    "external_content_collected",
    "model_trained",
    "model_evaluated",
    "quality_improved",
    "safety_established",
    "prompt_injection_safety_established",
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
    "prior_environment_closure_integrity",
    "environment_sequence_integrity",
    "static_research_scope_bounded",
    "dom_screenshot_page_text_contract_closed",
    "source_identity_and_freshness_closed",
    "citation_contract_closed",
    "four_component_delta_closed",
    "adapter_interface_closed",
    "task_record_shape_closed",
    "deterministic_verifier_total",
    "synthetic_source_only",
    "network_live_browser_and_capture_excluded",
    "untrusted_page_content_has_no_authority",
    "prior_content_exclusion_registry",
    "family_content_source_and_image_split_isolation",
    "inherited_systems_not_duplicated",
    "runtime_authority_preserved",
    "fail_closed_claims",
)

_ID = re.compile(r"[a-z0-9][a-z0-9._-]{0,127}\Z")
_SHA256 = re.compile(r"sha256:[0-9a-f]{64}\Z")
_HOST_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\Z")
_URL_PATH = re.compile(r"/[a-z0-9._~/-]{0,511}\Z")
_UTC_TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\Z")


class MM005BrowserResearchProtocolError(ValueError):
    """Stable fail-closed error for Browser Research protocol and records."""

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
    live_browser_used: bool
    next_gate: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


canonical_json_bytes = parent.canonical_json_bytes
sha256_bytes = parent.sha256_bytes
content_identity = parent.content_identity


def browser_identity(kind: str, value: object) -> str:
    if kind not in {"family", "record", "source_url", "source_snapshot"}:
        _fail("BROWSER_IDENTITY_KIND_INVALID", "$.identity.kind")
    payload = (
        b"mm005:browser-research:"
        + kind.encode("ascii")
        + b":v1\0"
        + canonical_json_bytes(value)
    )
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
        "mm005_browser_research_environment_adaptation_protocol_version": (
            PROTOCOL_VERSION
        ),
        "gate_id": GATE_ID,
        "freeze_status": freeze_status,
        "decision": "model_free_bounded_browser_research_scope_protocol",
        "source_lineage": {
            "receipts": receipts,
            "usage": ("read_only_prior_environment_closure_and_cross_stage_exclusion"),
            "parent_environment_protocol_required": True,
            "document_chart_pdf_repeatability_result_required": True,
            "document_chart_pdf_consumed_attempts_may_be_deleted_reused_or_retried": (
                False
            ),
            "runtime_freeze_may_be_silently_advanced": False,
            "lane_b_capture_may_be_enabled": False,
        },
        "prior_environment_closure": {
            "environment": "document_chart_pdf",
            "parent_protocol_merge_commit": (
                "9c57e32736e24bf120d827b0b7fef4dcf04f08b1"
            ),
            "repeatability_protocol_merge_commit": (
                "874f6c1a201a07d6680a3fa12217c1344b14c141"
            ),
            "result_publication_merge_commit": (
                "5f60cbf44a311b46b312090d62d2783424c1dc85"
            ),
            "closure_record_merge_commit": ("0a608f01e7d92ae20878da356443d80d1de0fff8"),
            "repeatability_review_bytes": 18_817,
            "repeatability_review_sha256": (
                "sha256:c5b5f12dfaffb387ca7e394c8acbd2b92fc00e3a256ed8cab0d4e624b28d0ec8"
            ),
            "bounded_same_machine_fixed_suite_repeatability_established": True,
            "resource_repeatability_established": False,
            "prior_evidence_read_only": True,
        },
        "environment_sequence": {
            "registered_order": list(ENVIRONMENT_ORDER),
            "completed_environments": ["desktop_gui", "document_chart_pdf"],
            "prior_environment": "document_chart_pdf",
            "prior_scope_status": (
                "synthetic_document_chart_pdf_fixed_suite_lifecycle_closed_"
                "without_runtime_deployment"
            ),
            "selected_environment": SELECTED_ENVIRONMENT,
            "selected_order_index": 3,
            "deferred_environments": list(ENVIRONMENT_ORDER[3:]),
            "sequence_skip_allowed": False,
        },
        "selected_scope": {
            "scope_id": SCOPE_ID,
            "vertical_mvp": (
                "static_dom_screenshot_page_text_answer_with_exact_citations"
            ),
            "content_language": "en",
            "observation_modalities": ["dom", "screenshot", "page_text"],
            "min_sources_per_record": 1,
            "max_sources_per_record": 3,
            "max_dom_nodes_per_source": 32,
            "max_visible_text_chars_per_node": 512,
            "max_page_text_chars_per_source": 8_192,
            "screenshot_required_per_source": True,
            "source_kinds": list(SOURCE_KINDS),
            "included": [
                "deterministic_repository_generated_invalid_domain_snapshots",
                "aligned_dom_screenshot_and_page_text",
                "single_source_fact_citation",
                "multi_source_synthesis_citation",
                "cross_source_comparison_citation",
                "freshness_conflict_resolution",
                "answer_and_exact_source_bound_citation_grounding",
            ],
            "deferred": [
                "live_search_or_network_retrieval",
                "browser_navigation_or_runtime_execution",
                "javascript_or_dynamic_page_execution",
                "login_cookies_sessions_or_personalized_content",
                "forms_downloads_uploads_or_transactions",
                "real_user_or_external_web_content",
                "prompt_injection_robustness_or_safety_claims",
                "open_web_source_quality_or_trust_ranking",
                "audio_video",
                "robotics_or_autonomous_driving",
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
            "environment_specific_live_browser_or_network_stack_allowed": False,
        },
        "adapter_contract": {
            "adapter_id": "browser-research-static-bundle-projection-v1",
            "adapter_kind": "model_input_and_output_projection_contract",
            "weights_created_at_this_gate": False,
            "browser_or_network_called_at_this_gate": False,
            "input_projection": {
                "required_record_fields": [
                    "instruction",
                    "observation",
                    "task_family_id",
                    "source_kind",
                ],
                "observation_modalities": ["dom", "screenshot", "page_text"],
                "gold_or_verifier_fields_exposed_to_model": False,
                "real_url_or_file_path_exposed_to_model": False,
                "synthetic_invalid_domain_url_exposed_to_model": True,
            },
            "output_projection": {
                "format": "strict_json_object",
                "exact_keys": ["answer", "citation_refs"],
                "extra_keys_allowed": False,
                "invalid_output_is_wrong": True,
                "compiler_version": COMPILER_VERSION,
            },
        },
        "task_set_contract": {
            "task_family_ids": list(TASK_FAMILY_IDS),
            "source_kinds": list(SOURCE_KINDS),
            "task_source_compatibility": _task_source_compatibility(),
            "source_count_by_kind": {
                key: list(value) for key, value in _source_count_by_kind().items()
            },
            "answer_types": [
                "fact_text",
                "synthesized_text",
                "comparison_text",
                "freshest_supported_fact",
            ],
            "citations_required": True,
            "multi_source_tasks_require_multiple_cited_sources": True,
            "freshness_task_requires_latest_source_citation": True,
            "execution_task": False,
            "model_output_has_execution_authority": False,
            "counts_generation_seed_and_rendering_deferred_to_next_gate": True,
        },
        "record_contract": {
            "record_version": RECORD_VERSION,
            "splits": ["train", "validation"],
            "required_fields": [
                "mm005_browser_research_record_version",
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
                "exact_keys": ["snapshot_at", "snapshot_source", "sources"],
                "snapshot_source": (
                    "deterministic_reviewed_synthetic_not_live_browser"
                ),
                "source_exact_keys": [
                    "dom_nodes",
                    "page_text",
                    "published_at",
                    "screenshot_sha256",
                    "source_id",
                    "title",
                    "url",
                ],
                "synthetic_url_policy": (
                    "https_invalid_domain_without_query_fragment_credentials_or_port"
                ),
                "published_at_must_not_follow_snapshot_at": True,
                "page_text_must_equal_visible_dom_text_in_order": True,
                "dom_node_exact_keys": ["bbox", "ref", "tag", "text"],
                "bbox_coordinate_space": "normalized_0_1000_xyxy",
                "allowed_dom_tags": sorted(DOM_TAGS),
                "source_and_dom_refs_unique_within_record": True,
            },
            "expected_output": {
                "exact_keys": ["answer", "citation_refs"],
                "citation_refs_must_exist_in_observation": True,
                "citation_refs_are_source_bound_dom_refs": True,
            },
            "identities": {
                "record_and_family": ("mm005_browser_research_domain_separated_sha256"),
                "cross_stage_content": (
                    "fullcycle_cross_stage_content_domain_sha256_v1"
                ),
                "source_url_and_snapshot": (
                    "mm005_browser_research_domain_separated_sha256_v1"
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
            "citation_match": "exact_ordered_unique_source_bound_dom_refs",
            "source_selection_derived_from_citation_refs": True,
            "freshness_check": "latest_published_source_must_be_cited",
            "extra_output_keys_invalid": True,
            "invalid_output_is_wrong": True,
            "metrics_required_at_future_eval": [
                "answer_exact_accuracy",
                "citation_exact_accuracy",
                "joint_answer_citation_accuracy",
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
            "source_url_disjoint_across_splits": True,
            "source_snapshot_disjoint_across_splits": True,
            "all_prior_exclusion_collisions_prohibited": True,
        },
        "provenance_policy": {
            "deterministic_reviewed_synthetic_only": True,
            "repository_generated_license_only": True,
            "synthetic_invalid_domain_only": True,
            "real_or_external_web_collection": False,
            "live_browser_or_network_access": False,
            "lane_a_rich_content": False,
            "lane_b_capture": False,
            "runtime_browser_or_document_content_claimed": False,
        },
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
        excluded_family_count=len(_sequence(registry["family_ids"], "$.family_ids")),
        excluded_image_count=len(_sequence(registry["image_sha256"], "$.image_sha256")),
        protocol_frozen=True,
        dataset_generated=False,
        live_browser_used=False,
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
    raw_sources = observation.get("sources")
    sources = raw_sources if isinstance(raw_sources, list) else []
    body: dict[str, Any] = {
        "mm005_browser_research_record_version": RECORD_VERSION,
        "family_id": browser_identity("family", family_basis),
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
            "instruction_content_sha256": content_identity("instruction", instruction),
            "observation_content_sha256": content_identity("observation", observation),
            "target_content_sha256": content_identity("target", expected_output),
            "image_sha256": [
                source.get("screenshot_sha256")
                for source in sources
                if isinstance(source, Mapping)
            ],
            "source_url_sha256": [
                browser_identity("source_url", source.get("url"))
                for source in sources
                if isinstance(source, Mapping)
            ],
            "source_snapshot_sha256": [
                browser_identity("source_snapshot", source)
                for source in sources
                if isinstance(source, Mapping)
            ],
        },
    }
    record = {"record_id": browser_identity("record", body), **body}
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
            "source_url_sha256": set(),
            "source_snapshot_sha256": set(),
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
        for key in (
            "instruction_content_sha256",
            "observation_content_sha256",
            "target_content_sha256",
        ):
            digest = str(identities[key])
            if digest in registry[key]:
                _fail("PRIOR_EXCLUSION_COLLISION", f"{location}.identities.{key}")
            split_values[split][key].add(digest)
        for key in (
            "image_sha256",
            "source_url_sha256",
            "source_snapshot_sha256",
        ):
            for digest_value in _sequence(
                identities[key], f"{location}.identities.{key}"
            ):
                digest = str(digest_value)
                if digest in registry[key]:
                    _fail(
                        "PRIOR_EXCLUSION_COLLISION",
                        f"{location}.identities.{key}",
                    )
                split_values[split][key].add(digest)
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
        "source_snapshot_count": sum(
            len(
                _sequence(
                    _mapping(record, "$")["observation"]["sources"],
                    "$.observation.sources",
                )
            )
            for record in records
        ),
        "splits": sorted(observed_splits),
    }


def compile_candidate_output(raw_output: str) -> dict[str, Any]:
    invalid: dict[str, Any] = {
        "compiler_version": COMPILER_VERSION,
        "valid": False,
        "answer": "",
        "citation_refs": [],
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
    if not isinstance(parsed, dict) or set(parsed) != {"answer", "citation_refs"}:
        return invalid
    answer = parsed.get("answer")
    refs = parsed.get("citation_refs")
    if (
        type(answer) is not str
        or not answer
        or len(answer) > 1_024
        or not isinstance(refs, list)
        or not refs
        or len(refs) > 12
        or any(type(ref) is not str or not _ID.fullmatch(ref) for ref in refs)
        or len(set(refs)) != len(refs)
    ):
        return invalid
    return {
        "compiler_version": COMPILER_VERSION,
        "valid": True,
        "answer": answer,
        "citation_refs": list(refs),
        "error_code": None,
    }


def verify_candidate(compiled: object, record: Mapping[str, Any]) -> dict[str, Any]:
    checked_record = _validate_record(record, "$.record")
    expected = _mapping(checked_record["expected_output"], "$.record.expected_output")
    candidate = compiled if isinstance(compiled, Mapping) else {}
    valid = _compiled_output_is_well_formed(candidate) and candidate["valid"] is True
    answer_exact = valid and _normalize_answer(str(candidate["answer"])) == (
        _normalize_answer(str(expected["answer"]))
    )
    citation_exact = valid and candidate["citation_refs"] == expected["citation_refs"]
    return {
        "verifier_version": VERIFIER_VERSION,
        "valid_output": valid,
        "answer_exact": answer_exact,
        "citation_exact": citation_exact,
        "joint_correct": answer_exact and citation_exact,
        "model_judge_used": False,
    }


def _validate_record(value: object, location: str) -> Mapping[str, Any]:
    record = _mapping(value, location)
    required = {
        "mm005_browser_research_record_version",
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
        type(record["mm005_browser_research_record_version"]) is not int
        or record["mm005_browser_research_record_version"] != RECORD_VERSION
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
    observation = _validate_observation(
        record["observation"], f"{location}.observation"
    )
    sources = _sequence(observation["sources"], f"{location}.observation.sources")
    minimum, maximum = _source_count_by_kind()[str(record["source_kind"])]
    if not minimum <= len(sources) <= maximum:
        _fail("SOURCE_COUNT_INCOMPATIBLE", f"{location}.observation.sources")
    expected = _validate_expected_output(
        record["expected_output"],
        observation=observation,
        task_family_id=str(record["task_family_id"]),
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
        "image_sha256": [
            _mapping(source, "$.source")["screenshot_sha256"] for source in sources
        ],
        "source_url_sha256": [
            browser_identity("source_url", _mapping(source, "$.source")["url"])
            for source in sources
        ],
        "source_snapshot_sha256": [
            browser_identity("source_snapshot", _mapping(source, "$.source"))
            for source in sources
        ],
    }
    if identities != expected_identities:
        _fail("CONTENT_IDENTITY_MISMATCH", f"{location}.identities")
    expected_family = browser_identity(
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
    if record["record_id"] != browser_identity("record", body):
        _fail("RECORD_IDENTITY_MISMATCH", f"{location}.record_id")
    return record


def _validate_observation(value: object, location: str) -> Mapping[str, Any]:
    observation = _mapping(value, location)
    if set(observation) != {"snapshot_at", "snapshot_source", "sources"}:
        _fail("OBSERVATION_KEYS_INVALID", location)
    if (
        observation["snapshot_source"]
        != "deterministic_reviewed_synthetic_not_live_browser"
    ):
        _fail("SNAPSHOT_SOURCE_INVALID", f"{location}.snapshot_source")
    snapshot_at = _parse_utc_timestamp(
        observation["snapshot_at"], f"{location}.snapshot_at"
    )
    sources = _sequence(observation["sources"], f"{location}.sources")
    if not 1 <= len(sources) <= 3:
        _fail("SOURCE_COUNT_INVALID", f"{location}.sources")
    source_ids: set[str] = set()
    urls: set[str] = set()
    screenshots: set[str] = set()
    global_refs: set[str] = set()
    for index, raw in enumerate(sources):
        source_location = f"{location}.sources[{index}]"
        source = _mapping(raw, source_location)
        if set(source) != {
            "dom_nodes",
            "page_text",
            "published_at",
            "screenshot_sha256",
            "source_id",
            "title",
            "url",
        }:
            _fail("SOURCE_KEYS_INVALID", source_location)
        source_id = source["source_id"]
        if (
            type(source_id) is not str
            or not _ID.fullmatch(source_id)
            or source_id in source_ids
        ):
            _fail("SOURCE_ID_INVALID", f"{source_location}.source_id")
        source_ids.add(source_id)
        url = _validate_synthetic_url(source["url"], f"{source_location}.url")
        if url in urls:
            _fail("SOURCE_URL_DUPLICATE", f"{source_location}.url")
        urls.add(url)
        title = source["title"]
        if type(title) is not str or not title or len(title) > 256:
            _fail("SOURCE_TITLE_INVALID", f"{source_location}.title")
        published_at = _parse_utc_timestamp(
            source["published_at"], f"{source_location}.published_at"
        )
        if published_at > snapshot_at:
            _fail("SOURCE_PUBLISHED_AFTER_SNAPSHOT", f"{source_location}.published_at")
        screenshot = source["screenshot_sha256"]
        if (
            type(screenshot) is not str
            or not _SHA256.fullmatch(screenshot)
            or screenshot in screenshots
        ):
            _fail("SCREENSHOT_SHA256_INVALID", f"{source_location}.screenshot_sha256")
        screenshots.add(screenshot)
        nodes = _sequence(source["dom_nodes"], f"{source_location}.dom_nodes")
        if not 1 <= len(nodes) <= 32:
            _fail("DOM_NODE_COUNT_INVALID", f"{source_location}.dom_nodes")
        node_texts: list[str] = []
        for node_index, raw_node in enumerate(nodes):
            node_location = f"{source_location}.dom_nodes[{node_index}]"
            node = _mapping(raw_node, node_location)
            if set(node) != {"bbox", "ref", "tag", "text"}:
                _fail("DOM_NODE_KEYS_INVALID", node_location)
            ref = node["ref"]
            if type(ref) is not str or not _ID.fullmatch(ref) or ref in global_refs:
                _fail("DOM_REF_INVALID", f"{node_location}.ref")
            global_refs.add(ref)
            if node["tag"] not in DOM_TAGS:
                _fail("DOM_TAG_INVALID", f"{node_location}.tag")
            bbox = node["bbox"]
            if (
                not isinstance(bbox, list)
                or len(bbox) != 4
                or any(
                    type(item) is not int or item < 0 or item > 1_000 for item in bbox
                )
                or bbox[0] >= bbox[2]
                or bbox[1] >= bbox[3]
            ):
                _fail("DOM_BBOX_INVALID", f"{node_location}.bbox")
            text = node["text"]
            if type(text) is not str or not text or len(text) > 512:
                _fail("DOM_TEXT_INVALID", f"{node_location}.text")
            node_texts.append(text)
        page_text = source["page_text"]
        expected_page_text = "\n".join(node_texts)
        if (
            type(page_text) is not str
            or len(page_text) > 8_192
            or page_text != expected_page_text
        ):
            _fail("PAGE_TEXT_DOM_MISMATCH", f"{source_location}.page_text")
    return observation


def _validate_expected_output(
    value: object,
    *,
    observation: Mapping[str, Any],
    task_family_id: str,
    location: str,
) -> Mapping[str, Any]:
    expected = _mapping(value, location)
    if set(expected) != {"answer", "citation_refs"}:
        _fail("EXPECTED_OUTPUT_KEYS_INVALID", location)
    answer = expected["answer"]
    if type(answer) is not str or not answer or len(answer) > 1_024:
        _fail("EXPECTED_ANSWER_INVALID", f"{location}.answer")
    refs = expected["citation_refs"]
    if (
        not isinstance(refs, list)
        or not refs
        or len(refs) > 12
        or any(type(ref) is not str for ref in refs)
        or len(set(refs)) != len(refs)
    ):
        _fail("EXPECTED_CITATION_REFS_INVALID", f"{location}.citation_refs")
    ref_to_source: dict[str, str] = {}
    source_published: dict[str, datetime] = {}
    for raw_source in _sequence(observation["sources"], "$.observation.sources"):
        source = _mapping(raw_source, "$.source")
        source_id = str(source["source_id"])
        source_published[source_id] = _parse_utc_timestamp(
            source["published_at"], "$.source.published_at"
        )
        for raw_node in _sequence(source["dom_nodes"], "$.source.dom_nodes"):
            node = _mapping(raw_node, "$.node")
            ref_to_source[str(node["ref"])] = source_id
    if any(ref not in ref_to_source for ref in refs):
        _fail("EXPECTED_CITATION_REF_MISSING", f"{location}.citation_refs")
    cited_sources = {ref_to_source[str(ref)] for ref in refs}
    if task_family_id != "single_source_fact_citation" and len(cited_sources) < 2:
        _fail("MULTI_SOURCE_CITATION_COVERAGE_INVALID", f"{location}.citation_refs")
    if task_family_id == "freshness_conflict_resolution":
        latest = max(source_published.values())
        latest_sources = {
            source_id
            for source_id, published_at in source_published.items()
            if published_at == latest
        }
        if not cited_sources & latest_sources:
            _fail("LATEST_SOURCE_CITATION_MISSING", f"{location}.citation_refs")
        if len(set(source_published.values())) < 2:
            _fail("FRESHNESS_VARIATION_MISSING", "$.observation.sources")
    return expected


def _validate_provenance(value: object, location: str) -> None:
    provenance = _mapping(value, location)
    expected = {
        "source": "deterministic_reviewed_synthetic_browser_snapshot_generation",
        "license": "repository_generated_synthetic",
        "synthetic_only": True,
        "real_content": False,
        "external_content": False,
        "network_accessed": False,
        "live_browser_used": False,
        "capture_adapter_used": False,
        "page_content_has_execution_authority": False,
        "model_output_has_execution_authority": False,
        "runtime_integration_authorized": False,
    }
    if provenance != expected:
        _fail("PROVENANCE_INVALID", location)


def _verifier_record() -> dict[str, Any]:
    return {
        "verifier_version": VERIFIER_VERSION,
        "answer_match": "unicode_nfc_then_ascii_space_trim_exact",
        "citation_match": "exact_ordered_unique_source_bound_dom_refs",
        "freshness_check": "latest_published_source_must_be_cited",
        "invalid_output_is_wrong": True,
        "model_or_llm_judge_used": False,
    }


def _task_source_compatibility() -> dict[str, list[str]]:
    return {
        "single_source_fact_citation": ["synthetic_single_source_snapshot"],
        "multi_source_synthesis_citation": ["synthetic_corroborating_source_bundle"],
        "cross_source_comparison_citation": ["synthetic_comparison_source_bundle"],
        "freshness_conflict_resolution": ["synthetic_temporal_revision_bundle"],
    }


def _source_count_by_kind() -> dict[str, tuple[int, int]]:
    return {
        "synthetic_single_source_snapshot": (1, 1),
        "synthetic_corroborating_source_bundle": (2, 3),
        "synthetic_comparison_source_bundle": (2, 3),
        "synthetic_temporal_revision_bundle": (2, 3),
    }


def _parse_utc_timestamp(value: object, location: str) -> datetime:
    if type(value) is not str or not _UTC_TIMESTAMP.fullmatch(value):
        _fail("UTC_TIMESTAMP_INVALID", location)
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        _fail("UTC_TIMESTAMP_INVALID", location)
    return parsed


def _validate_synthetic_url(value: object, location: str) -> str:
    if type(value) is not str or len(value) > 600 or not value.startswith("https://"):
        _fail("SYNTHETIC_URL_INVALID", location)
    remainder = value[len("https://") :]
    host, separator, path_tail = remainder.partition("/")
    if any(character in remainder for character in ("?", "#", "@", ":")):
        _fail("SYNTHETIC_URL_INVALID", location)
    labels = host.split(".")
    if (
        len(labels) < 2
        or labels[-1] != "invalid"
        or any(not _HOST_LABEL.fullmatch(label) for label in labels)
    ):
        _fail("SYNTHETIC_URL_INVALID", location)
    if separator and not _URL_PATH.fullmatch("/" + path_tail):
        _fail("SYNTHETIC_URL_INVALID", location)
    return value


def _normalize_answer(value: str) -> str:
    return unicodedata.normalize("NFC", value).strip(" ")


def _compiled_output_is_well_formed(value: Mapping[str, Any]) -> bool:
    if set(value) != {
        "compiler_version",
        "valid",
        "answer",
        "citation_refs",
        "error_code",
    }:
        return False
    if (
        type(value["compiler_version"]) is not int
        or value["compiler_version"] != COMPILER_VERSION
        or type(value["valid"]) is not bool
    ):
        return False
    if value["valid"] is False:
        return bool(
            value["answer"] == ""
            and value["citation_refs"] == []
            and value["error_code"] == "invalid_output"
        )
    refs = value["citation_refs"]
    return bool(
        type(value["answer"]) is str
        and bool(value["answer"])
        and len(value["answer"]) <= 1_024
        and isinstance(refs, list)
        and 0 < len(refs) <= 12
        and all(type(ref) is str and _ID.fullmatch(ref) for ref in refs)
        and len(set(refs)) == len(refs)
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
        "parent_protocol",
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
    raise MM005BrowserResearchProtocolError(code, location)
