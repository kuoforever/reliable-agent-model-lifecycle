"""Deterministic, model-free MM-005 Browser Research data preregistration."""

from __future__ import annotations

import json
import struct
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any, NoReturn

from . import browser_research_environment_adaptation as parent
from . import mm003_baseline_protocol as raster

DATA_PROTOCOL_VERSION = 1
DATASET_VERSION = 1
SOURCE_SNAPSHOT_VERSION = 1
MANIFEST_VERSION = 1
GATE_ID = "MM-005-browser-research-data-protocol-v1"
EXECUTION_GATE_ID = "MM-005-browser-research-data-generation-v1"
NEXT_GATE = EXECUTION_GATE_ID
PREREGISTRATION_PATH = "configs/mm005_browser_research_data_protocol_v1.json"
PARENT_PROTOCOL_PATH = (
    "configs/mm005_browser_research_environment_adaptation_protocol_v1.json"
)
OUTPUT_ROOT = "fixtures/mm005_browser_research_v1"
TRAIN_PATH = f"{OUTPUT_ROOT}/train.json"
VALIDATION_PATH = f"{OUTPUT_ROOT}/validation.json"
MANIFEST_PATH = f"{OUTPUT_ROOT}/manifest.json"
EVIDENCE_PATH = "baseline/mm005-browser-research-data-generation-v1.json"

SEED = 55_006
TEMPLATES_PER_TASK = 8
TRAIN_TEMPLATES_PER_TASK = 6
VALIDATION_TEMPLATES_PER_TASK = 2
MULTI_SOURCE_COUNTS = (2, 2, 3, 2, 3, 3, 2, 3)
TEMPLATE_COUNT = len(parent.TASK_FAMILY_IDS) * TEMPLATES_PER_TASK
RECORD_COUNT = TEMPLATE_COUNT
TRAIN_RECORDS = len(parent.TASK_FAMILY_IDS) * TRAIN_TEMPLATES_PER_TASK
VALIDATION_RECORDS = len(parent.TASK_FAMILY_IDS) * VALIDATION_TEMPLATES_PER_TASK

TASK_SLUGS = {
    "single_source_fact_citation": "single-fact",
    "multi_source_synthesis_citation": "multi-synthesis",
    "cross_source_comparison_citation": "cross-comparison",
    "freshness_conflict_resolution": "freshness-conflict",
}
SOURCE_COUNT = TEMPLATES_PER_TASK + (
    (len(parent.TASK_FAMILY_IDS) - 1) * sum(MULTI_SOURCE_COUNTS)
)
TRAIN_SOURCE_COUNT = TRAIN_TEMPLATES_PER_TASK + (
    (len(parent.TASK_FAMILY_IDS) - 1)
    * sum(MULTI_SOURCE_COUNTS[:TRAIN_TEMPLATES_PER_TASK])
)
VALIDATION_SOURCE_COUNT = VALIDATION_TEMPLATES_PER_TASK + (
    (len(parent.TASK_FAMILY_IDS) - 1)
    * sum(MULTI_SOURCE_COUNTS[TRAIN_TEMPLATES_PER_TASK:])
)
SCREENSHOT_COUNT = SOURCE_COUNT
SOURCE_SNAPSHOT_COUNT = SOURCE_COUNT
OUTPUT_FILE_COUNT = SCREENSHOT_COUNT + SOURCE_SNAPSHOT_COUNT + 3

FREEZE_CLAIMS = (
    "generation_executed",
    "records_generated",
    "source_snapshots_generated",
    "screenshots_generated",
    "dataset_validated",
    "environment_adapter_implemented",
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
    "preregistration_integrity",
    "parent_protocol_integrity",
    "source_receipt_integrity",
    "deterministic_template_registry",
    "deterministic_static_source_registry",
    "deterministic_output_rebuild",
    "planned_output_receipt_integrity",
    "parent_record_contract",
    "task_source_and_source_count_coverage",
    "split_distribution",
    "family_template_content_image_url_and_snapshot_split_isolation",
    "prior_stage_content_exclusion",
    "dom_page_text_screenshot_alignment",
    "screenshot_png_integrity",
    "static_source_snapshot_integrity",
    "citation_and_freshness_semantics",
    "fixed_outputs_absent_at_freeze",
    "network_live_browser_model_and_capture_excluded",
    "runtime_authority_preserved",
    "fail_closed_claims",
)


class MM005BrowserResearchDataProtocolError(ValueError):
    """Stable fail-closed error for the data plan and planned bytes."""

    def __init__(self, code: str, location: str = "$") -> None:
        self.code = code
        self.location = location
        super().__init__(f"{code} at {location}")


@dataclass(frozen=True)
class DataProtocolSummary:
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
    task_family_count: int
    source_kind_count: int
    protocol_frozen: bool
    generation_executed: bool
    dataset_validated: bool
    next_gate: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def artifact_json_bytes(value: object) -> bytes:
    return parent.canonical_json_bytes(value)


def sha256_bytes(payload: bytes) -> str:
    return parent.sha256_bytes(payload)


def expected_templates() -> list[dict[str, Any]]:
    templates: list[dict[str, Any]] = []
    for task_index, task_family_id in enumerate(parent.TASK_FAMILY_IDS, 1):
        for ordinal in range(1, TEMPLATES_PER_TASK + 1):
            source_count = (
                1
                if task_family_id == "single_source_fact_citation"
                else MULTI_SOURCE_COUNTS[ordinal - 1]
            )
            templates.append(
                {
                    "template_id": (
                        f"mm005-browser-{TASK_SLUGS[task_family_id]}-{ordinal:02d}"
                    ),
                    "ordinal": ordinal,
                    "content_seed": SEED + task_index * 100 + ordinal,
                    "split": (
                        "train" if ordinal <= TRAIN_TEMPLATES_PER_TASK else "validation"
                    ),
                    "task_family_id": task_family_id,
                    "source_kind": parent.SOURCE_KINDS[task_index - 1],
                    "source_count": source_count,
                }
            )
    return templates


def expected_screenshots() -> dict[str, bytes]:
    result: dict[str, bytes] = {}
    for template in expected_templates():
        materialized = _materialize_blueprint(template)
        for raw_source in _array(materialized["sources"], "$.sources"):
            source = _object(raw_source, "$.source")
            path = _screenshot_path(template, str(source["source_id"]))
            result[path] = _render_png(template, source)
    return dict(sorted(result.items()))


def expected_source_snapshots(screenshots: Mapping[str, bytes]) -> dict[str, bytes]:
    result: dict[str, bytes] = {}
    for template in expected_templates():
        for source in _completed_sources(template, screenshots):
            source_id = str(source["source_id"])
            screenshot_path = _screenshot_path(template, source_id)
            snapshot_path = _snapshot_path(template, source_id)
            result[snapshot_path] = artifact_json_bytes(
                _source_snapshot_artifact(
                    template=template,
                    source=source,
                    screenshot_path=screenshot_path,
                )
            )
    return dict(sorted(result.items()))


def expected_records(screenshots: Mapping[str, bytes]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for template in expected_templates():
        materialized = _materialize_blueprint(template)
        sources = _completed_sources(template, screenshots)
        records.append(
            parent.build_record(
                template_id=str(template["template_id"]),
                split=str(template["split"]),
                task_family_id=str(template["task_family_id"]),
                source_kind=str(template["source_kind"]),
                instruction=str(materialized["instruction"]),
                observation={
                    "snapshot_at": str(materialized["snapshot_at"]),
                    "snapshot_source": (
                        "deterministic_reviewed_synthetic_not_live_browser"
                    ),
                    "sources": sources,
                },
                expected_output=_object(
                    materialized["expected_output"], "$.expected_output"
                ),
                provenance=_record_provenance(),
            )
        )
    return records


def expected_output_payloads(parent_protocol_sha256: str) -> dict[str, bytes]:
    """Rebuild every future output byte in memory without writing a file."""

    screenshots = expected_screenshots()
    source_snapshots = expected_source_snapshots(screenshots)
    records = expected_records(screenshots)
    payloads = {**screenshots, **source_snapshots}
    for split, path in (("train", TRAIN_PATH), ("validation", VALIDATION_PATH)):
        split_records = [record for record in records if record["split"] == split]
        split_screenshots = {
            output_path: _receipt(output_path, payload)
            for output_path, payload in screenshots.items()
            if f"/screenshots/{split}/" in output_path
        }
        split_snapshots = {
            output_path: _receipt(output_path, payload)
            for output_path, payload in source_snapshots.items()
            if f"/snapshots/{split}/" in output_path
        }
        payloads[path] = artifact_json_bytes(
            {
                "mm005_browser_research_dataset_version": DATASET_VERSION,
                "dataset_id": "mm005-browser-research-v1",
                "gate_id": EXECUTION_GATE_ID,
                "parent_protocol_sha256": parent_protocol_sha256,
                "seed": SEED,
                "split": split,
                "source_count": sum(
                    len(_array(record["observation"]["sources"], "$.sources"))
                    for record in split_records
                ),
                "provenance": _dataset_provenance(),
                "screenshot_receipts": dict(sorted(split_screenshots.items())),
                "source_snapshot_receipts": dict(sorted(split_snapshots.items())),
                "records": split_records,
            }
        )
    manifest_receipts = {
        path: _receipt(path, payload) for path, payload in sorted(payloads.items())
    }
    payloads[MANIFEST_PATH] = artifact_json_bytes(
        {
            "mm005_browser_research_manifest_version": MANIFEST_VERSION,
            "gate_id": EXECUTION_GATE_ID,
            "parent_protocol_sha256": parent_protocol_sha256,
            "seed": SEED,
            "outputs": manifest_receipts,
            "summary": _expected_counts(),
        }
    )
    return dict(sorted(payloads.items()))


def expected_preregistration(
    *,
    freeze_status: str,
    source_receipts: Mapping[str, Mapping[str, Any]],
    parent_protocol_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    if freeze_status not in {"draft", "frozen"}:
        _fail("FREEZE_STATUS_INVALID", "$.freeze_status")
    sources = _closed_receipts(source_receipts, "$.source_receipts")
    parent_receipt = _closed_receipt(
        parent_protocol_receipt,
        expected_path=PARENT_PROTOCOL_PATH,
        location="$.parent_protocol",
    )
    outputs = expected_output_payloads(str(parent_receipt["sha256"]))
    output_receipts = {
        path: _receipt(path, payload) for path, payload in outputs.items()
    }
    return {
        "mm005_browser_research_data_protocol_version": DATA_PROTOCOL_VERSION,
        "gate_id": GATE_ID,
        "freeze_status": freeze_status,
        "decision": "outcome_neutral_deterministic_static_browser_data_preregistration",
        "parent_protocol": parent_receipt,
        "source_receipts": sources,
        "generation_plan": {
            "seed": SEED,
            "dataset_id": "mm005-browser-research-v1",
            "output_root": OUTPUT_ROOT,
            "task_family_ids": list(parent.TASK_FAMILY_IDS),
            "source_kinds": list(parent.SOURCE_KINDS),
            "templates_per_task": TEMPLATES_PER_TASK,
            "train_templates_per_task": TRAIN_TEMPLATES_PER_TASK,
            "validation_templates_per_task": VALIDATION_TEMPLATES_PER_TASK,
            "multi_source_counts_by_ordinal": list(MULTI_SOURCE_COUNTS),
            "template_count": TEMPLATE_COUNT,
            "record_count": RECORD_COUNT,
            "source_count": SOURCE_COUNT,
            "screenshot_count": SCREENSHOT_COUNT,
            "source_snapshot_count": SOURCE_SNAPSHOT_COUNT,
            "train_records": TRAIN_RECORDS,
            "validation_records": VALIDATION_RECORDS,
            "train_sources": TRAIN_SOURCE_COUNT,
            "validation_sources": VALIDATION_SOURCE_COUNT,
            "output_file_count": OUTPUT_FILE_COUNT,
            "template_registry": expected_templates(),
            "source_snapshot": {
                "format": "canonical_json_static_source_descriptor",
                "executable_html_or_javascript": False,
                "source_object_matches_record_observation_exactly": True,
                "source_url_policy": "https_invalid_domain_only",
                "external_retrieval_used": False,
            },
            "renderer": {
                "width": raster.PNG_WIDTH,
                "height": raster.PNG_HEIGHT,
                "color_type": "rgb_8_bit",
                "png_filter": "none_per_row",
                "zlib_level": 9,
                "host_font_used": False,
                "embedded_bitmap_font": True,
                "metadata_chunks": False,
                "browser_engine_used": False,
                "dom_page_text_and_screenshot_share_source_ground_truth": True,
            },
            "network_allowed": False,
            "live_browser_allowed": False,
            "javascript_allowed": False,
            "model_dependencies_allowed": False,
            "real_or_external_content_allowed": False,
            "capture_allowed": False,
            "retry_count": 0,
        },
        "planned_outputs": output_receipts,
        "validation_contract": {
            "canonical_json_required": True,
            "exact_output_byte_rebuild_required": True,
            "parent_record_validator_required": True,
            "task_family_source_kind_and_source_count_coverage_required": True,
            "per_task_split_distribution": {"train": 6, "validation": 2},
            "source_count_range_coverage": [1, 2, 3],
            "family_template_content_image_url_and_snapshot_split_isolation_required": (
                True
            ),
            "prior_stage_exclusion_collision_allowed": False,
            "page_text_must_equal_visible_dom_text_in_order": True,
            "screenshot_must_rebuild_from_exact_dom_ground_truth": True,
            "screenshot_signature_dimensions_and_uniqueness_required": True,
            "source_snapshot_must_match_record_source_exactly": True,
            "citation_refs_must_bind_exact_source_dom_nodes": True,
            "multi_source_tasks_must_cite_at_least_two_sources": True,
            "freshness_answer_and_citation_must_bind_latest_source": True,
            "model_or_llm_judge_used": False,
        },
        "freeze_preconditions": {
            "expected_absent_paths": [OUTPUT_ROOT, EVIDENCE_PATH],
            "generation_output_absent": True,
            "execution_evidence_absent": True,
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
        "next_gate": NEXT_GATE,
    }


def validate_preregistration(
    value: object,
    *,
    source_receipts: Mapping[str, Mapping[str, Any]],
    parent_protocol_receipt: Mapping[str, Any],
) -> DataProtocolSummary:
    expected = expected_preregistration(
        freeze_status="frozen",
        source_receipts=source_receipts,
        parent_protocol_receipt=parent_protocol_receipt,
    )
    if value != expected:
        _fail("PREREGISTRATION_MISMATCH")
    planned_outputs = _object(expected["planned_outputs"], "$.planned_outputs")
    return DataProtocolSummary(
        protocol_version=DATA_PROTOCOL_VERSION,
        template_count=TEMPLATE_COUNT,
        record_count=RECORD_COUNT,
        source_count=SOURCE_COUNT,
        screenshot_count=SCREENSHOT_COUNT,
        source_snapshot_count=SOURCE_SNAPSHOT_COUNT,
        train_records=TRAIN_RECORDS,
        validation_records=VALIDATION_RECORDS,
        train_sources=TRAIN_SOURCE_COUNT,
        validation_sources=VALIDATION_SOURCE_COUNT,
        output_file_count=len(planned_outputs),
        output_bytes=sum(
            int(_object(receipt, "$.planned_outputs.receipt")["bytes"])
            for receipt in planned_outputs.values()
        ),
        task_family_count=len(parent.TASK_FAMILY_IDS),
        source_kind_count=len(parent.SOURCE_KINDS),
        protocol_frozen=True,
        generation_executed=False,
        dataset_validated=False,
        next_gate=NEXT_GATE,
    )


def validate_planned_output_payloads(
    payloads: Mapping[str, bytes],
    *,
    parent_protocol_sha256: str,
    exclusions: Mapping[str, Sequence[str]],
) -> dict[str, Any]:
    expected = expected_output_payloads(parent_protocol_sha256)
    if dict(payloads) != expected:
        _fail("OUTPUT_PAYLOAD_MISMATCH")
    train = _json_object(payloads[TRAIN_PATH], TRAIN_PATH)
    validation = _json_object(payloads[VALIDATION_PATH], VALIDATION_PATH)
    train_records = _dataset_records(
        train, "train", parent_protocol_sha256=parent_protocol_sha256
    )
    validation_records = _dataset_records(
        validation,
        "validation",
        parent_protocol_sha256=parent_protocol_sha256,
    )
    records = [*train_records, *validation_records]
    record_summary = parent.validate_records(records, exclusions)
    if record_summary != {
        "record_count": RECORD_COUNT,
        "family_count": TEMPLATE_COUNT,
        "task_family_count": len(parent.TASK_FAMILY_IDS),
        "source_kind_count": len(parent.SOURCE_KINDS),
        "source_snapshot_count": SOURCE_COUNT,
        "splits": ["train", "validation"],
    }:
        _fail("RECORD_SUMMARY_MISMATCH")
    _validate_distribution(records)
    _validate_dataset_receipts(train, "train", payloads)
    _validate_dataset_receipts(validation, "validation", payloads)
    _validate_screenshot_bindings(records, payloads)
    _validate_source_snapshot_bindings(records, payloads)
    _validate_citation_semantics(records)
    _validate_manifest(payloads, parent_protocol_sha256)
    return {
        "planned_output_rebuild_valid": True,
        "template_count": TEMPLATE_COUNT,
        "record_count": RECORD_COUNT,
        "source_count": SOURCE_COUNT,
        "screenshot_count": SCREENSHOT_COUNT,
        "source_snapshot_count": SOURCE_SNAPSHOT_COUNT,
        "train_records": TRAIN_RECORDS,
        "validation_records": VALIDATION_RECORDS,
        "train_sources": TRAIN_SOURCE_COUNT,
        "validation_sources": VALIDATION_SOURCE_COUNT,
        "output_file_count": OUTPUT_FILE_COUNT,
        "output_bytes": sum(len(payload) for payload in payloads.values()),
        "generation_executed": False,
        "dataset_validated": False,
        "next_gate": NEXT_GATE,
    }


def _materialize_blueprint(template: Mapping[str, Any]) -> dict[str, Any]:
    template_id = str(template["template_id"])
    ordinal = int(template["ordinal"])
    content_seed = int(template["content_seed"])
    task_family_id = str(template["task_family_id"])
    source_count = int(template["source_count"])
    snapshot_at = f"2026-04-{ordinal + 10:02d}T12:00:00Z"
    sources: list[dict[str, Any]] = []
    fact_refs: list[str] = []
    fact_values: list[str] = []
    comparison_values: list[tuple[str, int]] = []
    labels = ("ALPHA", "BETA", "GAMMA")
    for source_index in range(1, source_count + 1):
        source_id = f"{template_id}-source-{source_index:02d}"
        fact_ref = f"{source_id}-fact"
        fact_refs.append(fact_ref)
        if task_family_id == "single_source_fact_citation":
            value = f"BEACON-{content_seed % 900 + 100}"
            fact_text = f"REGISTERED BEACON CODE {value}"
            fact_values.append(value)
        elif task_family_id == "multi_source_synthesis_citation":
            value = f"AXIS-{ordinal:02d}-{source_index}-{(content_seed + source_index) % 97:02d}"
            fact_text = f"CONTRIBUTION CODE {value}"
            fact_values.append(value)
        elif task_family_id == "cross_source_comparison_citation":
            label = labels[source_index - 1]
            number = 30 + content_seed % 17 + source_index * 11
            fact_text = f"COMPARISON INDEX {label} {number}"
            comparison_values.append((label, number))
        elif task_family_id == "freshness_conflict_resolution":
            value = (
                f"STATUS-{ordinal:02d}-{source_index}-"
                f"{(content_seed + source_index * 3) % 89:02d}"
            )
            fact_text = f"PUBLISHED STATUS {value}"
            fact_values.append(value)
        else:
            _fail("TASK_FAMILY_INVALID", "$.template.task_family_id")
        title = f"SYNTHETIC {TASK_SLUGS[task_family_id].replace('-', ' ').upper()} SOURCE {source_index}"
        nodes = [
            _node(
                f"{source_id}-title",
                "h1",
                [60, 110, 940, 230],
                title,
            ),
            _node(fact_ref, "p", [80, 300, 920, 440], fact_text),
            _node(
                f"{source_id}-note",
                "p",
                [80, 500, 920, 640],
                f"STATIC SYNTHETIC NOTE {ordinal:02d} {source_index:02d}",
            ),
            _node(
                f"{source_id}-caption",
                "caption",
                [80, 720, 920, 820],
                f"REPOSITORY GENERATED SOURCE {source_index:02d}",
            ),
        ]
        sources.append(
            {
                "dom_nodes": nodes,
                "page_text": "\n".join(str(node["text"]) for node in nodes),
                "published_at": _published_at(ordinal, source_index),
                "source_id": source_id,
                "title": title,
                "url": f"https://{source_id}.research.invalid/snapshot",
            }
        )
    if task_family_id == "single_source_fact_citation":
        instruction = (
            f"Return the registered beacon code in static source {template_id} "
            "and cite its exact DOM ref."
        )
        expected_output = {"answer": fact_values[0], "citation_refs": fact_refs}
    elif task_family_id == "multi_source_synthesis_citation":
        instruction = (
            f"Synthesize the contribution codes for {template_id} in source "
            "order and cite every contributing DOM ref."
        )
        expected_output = {
            "answer": " + ".join(fact_values),
            "citation_refs": fact_refs,
        }
    elif task_family_id == "cross_source_comparison_citation":
        minimum = min(comparison_values, key=lambda item: item[1])
        maximum = max(comparison_values, key=lambda item: item[1])
        minimum_index = comparison_values.index(minimum)
        maximum_index = comparison_values.index(maximum)
        instruction = (
            f"Identify the highest comparison index for {template_id}, state "
            "its lead over the lowest, and cite both exact DOM refs."
        )
        expected_output = {
            "answer": (
                f"{maximum[0]} EXCEEDS {minimum[0]} BY {maximum[1] - minimum[1]}"
            ),
            "citation_refs": [
                fact_refs[maximum_index],
                fact_refs[minimum_index],
            ],
        }
    elif task_family_id == "freshness_conflict_resolution":
        instruction = (
            f"Resolve the conflicting published statuses for {template_id} by "
            "returning the latest status and citing the earliest and latest refs."
        )
        expected_output = {
            "answer": fact_values[-1],
            "citation_refs": [fact_refs[0], fact_refs[-1]],
        }
    else:
        _fail("TASK_FAMILY_INVALID", "$.template.task_family_id")
    return {
        "template_id": template_id,
        "snapshot_at": snapshot_at,
        "instruction": instruction,
        "sources": sources,
        "expected_output": expected_output,
    }


def _completed_sources(
    template: Mapping[str, Any], screenshots: Mapping[str, bytes]
) -> list[dict[str, Any]]:
    materialized = _materialize_blueprint(template)
    result: list[dict[str, Any]] = []
    for raw_source in _array(materialized["sources"], "$.sources"):
        source = dict(_object(raw_source, "$.source"))
        path = _screenshot_path(template, str(source["source_id"]))
        payload = screenshots.get(path)
        if not isinstance(payload, bytes):
            _fail("PLANNED_SCREENSHOT_MISSING", f"$.screenshots.{path}")
        source["screenshot_sha256"] = sha256_bytes(payload)
        result.append(source)
    return result


def _render_png(template: Mapping[str, Any], source: Mapping[str, Any]) -> bytes:
    pixels = bytearray((243, 247, 251) * (raster.PNG_WIDTH * raster.PNG_HEIGHT))
    raster._fill_rect(pixels, 0, 0, raster.PNG_WIDTH, 76, (31, 48, 68))
    raster._draw_text(
        pixels,
        22,
        22,
        f"STATIC {source['source_id']}".upper(),
        (255, 255, 255),
        2,
    )
    colors = {
        "h1": (38, 108, 184),
        "p": (37, 133, 91),
        "caption": (112, 82, 153),
    }
    for raw_node in _array(source["dom_nodes"], "$.source.dom_nodes"):
        node = _object(raw_node, "$.node")
        bbox = [int(item) for item in _array(node["bbox"], "$.node.bbox")]
        x1, y1, x2, y2 = _pixel_bbox(bbox)
        color = colors[str(node["tag"])]
        raster._fill_rect(pixels, x1, y1, x2, y2, (255, 255, 255))
        raster._stroke_rect(pixels, x1, y1, x2, y2, color, 3)
        raster._draw_text(
            pixels,
            x1 + 10,
            y1 + 10,
            str(node["text"]).upper(),
            (24, 31, 43),
            2,
        )
    raster._draw_text(
        pixels,
        28,
        raster.PNG_HEIGHT - 34,
        str(template["task_family_id"]).replace("_", " ").upper(),
        (49, 61, 75),
        2,
    )
    return raster._encode_png(raster.PNG_WIDTH, raster.PNG_HEIGHT, bytes(pixels))


def _source_snapshot_artifact(
    *,
    template: Mapping[str, Any],
    source: Mapping[str, Any],
    screenshot_path: str,
) -> dict[str, Any]:
    return {
        "mm005_browser_research_source_snapshot_version": SOURCE_SNAPSHOT_VERSION,
        "dataset_id": "mm005-browser-research-v1",
        "gate_id": EXECUTION_GATE_ID,
        "template_id": template["template_id"],
        "split": template["split"],
        "task_family_id": template["task_family_id"],
        "source_kind": template["source_kind"],
        "screenshot_path": screenshot_path,
        "source_url_identity_sha256": parent.browser_identity(
            "source_url", source["url"]
        ),
        "source_snapshot_identity_sha256": parent.browser_identity(
            "source_snapshot", source
        ),
        "source": dict(source),
    }


def _validate_distribution(records: Sequence[Mapping[str, Any]]) -> None:
    by_task_split = Counter(
        (str(record["task_family_id"]), str(record["split"])) for record in records
    )
    expected_task_split = {
        (task_family_id, split): count
        for task_family_id in parent.TASK_FAMILY_IDS
        for split, count in (
            ("train", TRAIN_TEMPLATES_PER_TASK),
            ("validation", VALIDATION_TEMPLATES_PER_TASK),
        )
    }
    if dict(by_task_split) != expected_task_split:
        _fail("TASK_SPLIT_DISTRIBUTION_MISMATCH")
    source_counts = Counter(
        (str(record["task_family_id"]), str(record["split"]))
        for record in records
        for _ in _array(record["observation"]["sources"], "$.sources")
    )
    expected_source_counts = {
        (task_family_id, split): (
            count if task_family_id == "single_source_fact_citation" else multi_count
        )
        for task_family_id in parent.TASK_FAMILY_IDS
        for split, count, multi_count in (
            (
                "train",
                TRAIN_TEMPLATES_PER_TASK,
                sum(MULTI_SOURCE_COUNTS[:TRAIN_TEMPLATES_PER_TASK]),
            ),
            (
                "validation",
                VALIDATION_TEMPLATES_PER_TASK,
                sum(MULTI_SOURCE_COUNTS[TRAIN_TEMPLATES_PER_TASK:]),
            ),
        )
    }
    if dict(source_counts) != expected_source_counts:
        _fail("SOURCE_SPLIT_DISTRIBUTION_MISMATCH")
    observed_source_counts = {
        len(_array(record["observation"]["sources"], "$.sources")) for record in records
    }
    if observed_source_counts != {1, 2, 3}:
        _fail("SOURCE_COUNT_RANGE_COVERAGE_MISMATCH")


def _validate_dataset_receipts(
    dataset: Mapping[str, Any], split: str, payloads: Mapping[str, bytes]
) -> None:
    expected_screenshots = {
        path: _receipt(path, payload)
        for path, payload in payloads.items()
        if f"/screenshots/{split}/" in path
    }
    expected_snapshots = {
        path: _receipt(path, payload)
        for path, payload in payloads.items()
        if f"/snapshots/{split}/" in path
    }
    if dataset["screenshot_receipts"] != dict(sorted(expected_screenshots.items())):
        _fail("DATASET_SCREENSHOT_RECEIPTS_INVALID", f"$.datasets.{split}")
    if dataset["source_snapshot_receipts"] != dict(sorted(expected_snapshots.items())):
        _fail("DATASET_SOURCE_SNAPSHOT_RECEIPTS_INVALID", f"$.datasets.{split}")


def _validate_screenshot_bindings(
    records: Sequence[Mapping[str, Any]], payloads: Mapping[str, bytes]
) -> None:
    screenshots = {
        path: payload for path, payload in payloads.items() if path.endswith(".png")
    }
    if (
        len(screenshots) != SCREENSHOT_COUNT
        or len(set(screenshots.values())) != SCREENSHOT_COUNT
    ):
        _fail("SCREENSHOT_COUNT_OR_UNIQUENESS_MISMATCH")
    templates = {str(item["template_id"]): item for item in expected_templates()}
    expected_paths: set[str] = set()
    for record in records:
        template = templates[str(record["template_id"])]
        for raw_source in _array(record["observation"]["sources"], "$.sources"):
            source = _object(raw_source, "$.source")
            path = _screenshot_path(template, str(source["source_id"]))
            expected_paths.add(path)
            payload = screenshots.get(path)
            if payload is None:
                _fail("SCREENSHOT_BINDING_MISSING", f"$.screenshots.{path}")
            if not payload.startswith(b"\x89PNG\r\n\x1a\n") or len(payload) < 24:
                _fail("PNG_SIGNATURE_INVALID", f"$.screenshots.{path}")
            width, height = struct.unpack(">II", payload[16:24])
            if (width, height) != (raster.PNG_WIDTH, raster.PNG_HEIGHT):
                _fail("PNG_DIMENSIONS_INVALID", f"$.screenshots.{path}")
            if source["screenshot_sha256"] != sha256_bytes(payload):
                _fail("SCREENSHOT_HASH_BINDING_INVALID", f"$.screenshots.{path}")
            if _render_png(template, source) != payload:
                _fail("DOM_SCREENSHOT_REBUILD_MISMATCH", f"$.screenshots.{path}")
            node_text = "\n".join(
                str(_object(node, "$.node")["text"])
                for node in _array(source["dom_nodes"], "$.source.dom_nodes")
            )
            if source["page_text"] != node_text:
                _fail("DOM_PAGE_TEXT_MISMATCH", f"$.screenshots.{path}")
    if set(screenshots) != expected_paths:
        _fail("SCREENSHOT_PATH_SET_INVALID")


def _validate_source_snapshot_bindings(
    records: Sequence[Mapping[str, Any]], payloads: Mapping[str, bytes]
) -> None:
    snapshots = {
        path: payload
        for path, payload in payloads.items()
        if "/snapshots/" in path and path.endswith(".json")
    }
    if (
        len(snapshots) != SOURCE_SNAPSHOT_COUNT
        or len(set(snapshots.values())) != SOURCE_SNAPSHOT_COUNT
    ):
        _fail("SOURCE_SNAPSHOT_COUNT_OR_UNIQUENESS_MISMATCH")
    templates = {str(item["template_id"]): item for item in expected_templates()}
    sources: dict[tuple[str, str], Mapping[str, Any]] = {}
    for record in records:
        for raw_source in _array(record["observation"]["sources"], "$.sources"):
            source = _object(raw_source, "$.source")
            sources[(str(record["template_id"]), str(source["source_id"]))] = source
    expected_paths: set[str] = set()
    for (template_id, source_id), source in sources.items():
        template = templates[template_id]
        path = _snapshot_path(template, source_id)
        expected_paths.add(path)
        payload = snapshots.get(path)
        if payload is None:
            _fail("SOURCE_SNAPSHOT_MISSING", f"$.snapshots.{path}")
        artifact = _json_object(payload, path)
        if artifact_json_bytes(artifact) != payload:
            _fail("SOURCE_SNAPSHOT_NOT_CANONICAL", f"$.snapshots.{path}")
        expected = _source_snapshot_artifact(
            template=template,
            source=source,
            screenshot_path=_screenshot_path(template, source_id),
        )
        if artifact != expected:
            _fail("SOURCE_SNAPSHOT_BINDING_INVALID", f"$.snapshots.{path}")
    if set(snapshots) != expected_paths:
        _fail("SOURCE_SNAPSHOT_PATH_SET_INVALID")


def _validate_citation_semantics(records: Sequence[Mapping[str, Any]]) -> None:
    for record in records:
        sources = [
            _object(source, "$.source")
            for source in _array(record["observation"]["sources"], "$.sources")
        ]
        ref_to_node: dict[str, tuple[Mapping[str, Any], Mapping[str, Any]]] = {}
        fact_refs: list[str] = []
        for source in sources:
            for raw_node in _array(source["dom_nodes"], "$.source.dom_nodes"):
                node = _object(raw_node, "$.node")
                ref = str(node["ref"])
                ref_to_node[ref] = (source, node)
                if ref.endswith("-fact"):
                    fact_refs.append(ref)
        expected = _object(record["expected_output"], "$.expected_output")
        refs = [str(ref) for ref in _array(expected["citation_refs"], "$.refs")]
        answer = str(expected["answer"])
        task = str(record["task_family_id"])
        if task == "single_source_fact_citation":
            text = str(ref_to_node[refs[0]][1]["text"])
            if refs != fact_refs or not text.endswith(answer):
                _fail("SINGLE_SOURCE_CITATION_SEMANTICS_INVALID")
        elif task == "multi_source_synthesis_citation":
            codes = [
                str(ref_to_node[ref][1]["text"]).removeprefix("CONTRIBUTION CODE ")
                for ref in fact_refs
            ]
            if refs != fact_refs or answer != " + ".join(codes):
                _fail("MULTI_SOURCE_SYNTHESIS_SEMANTICS_INVALID")
        elif task == "cross_source_comparison_citation":
            values: list[tuple[str, int, str]] = []
            for ref in fact_refs:
                parts = str(ref_to_node[ref][1]["text"]).split()
                if len(parts) != 4:
                    _fail("COMPARISON_FACT_INVALID")
                values.append((parts[2], int(parts[3]), ref))
            minimum = min(values, key=lambda item: item[1])
            maximum = max(values, key=lambda item: item[1])
            if refs != [maximum[2], minimum[2]] or answer != (
                f"{maximum[0]} EXCEEDS {minimum[0]} BY {maximum[1] - minimum[1]}"
            ):
                _fail("CROSS_SOURCE_COMPARISON_SEMANTICS_INVALID")
        elif task == "freshness_conflict_resolution":
            ordered = sorted(sources, key=lambda source: str(source["published_at"]))
            earliest_ref = next(
                str(node["ref"])
                for node in _array(ordered[0]["dom_nodes"], "$.dom_nodes")
                if str(_object(node, "$.node")["ref"]).endswith("-fact")
            )
            latest_ref = next(
                str(node["ref"])
                for node in _array(ordered[-1]["dom_nodes"], "$.dom_nodes")
                if str(_object(node, "$.node")["ref"]).endswith("-fact")
            )
            latest_text = str(ref_to_node[latest_ref][1]["text"])
            if refs != [earliest_ref, latest_ref] or not latest_text.endswith(answer):
                _fail("FRESHNESS_SEMANTICS_INVALID")
        else:
            _fail("TASK_FAMILY_INVALID")


def _validate_manifest(
    payloads: Mapping[str, bytes], parent_protocol_sha256: str
) -> None:
    manifest = _json_object(payloads[MANIFEST_PATH], MANIFEST_PATH)
    expected_outputs = {
        path: _receipt(path, payload)
        for path, payload in sorted(payloads.items())
        if path != MANIFEST_PATH
    }
    expected = {
        "mm005_browser_research_manifest_version": MANIFEST_VERSION,
        "gate_id": EXECUTION_GATE_ID,
        "parent_protocol_sha256": parent_protocol_sha256,
        "seed": SEED,
        "outputs": expected_outputs,
        "summary": _expected_counts(),
    }
    if manifest != expected:
        _fail("MANIFEST_INVALID")


def _dataset_records(
    value: Mapping[str, Any], split: str, *, parent_protocol_sha256: str
) -> list[Mapping[str, Any]]:
    expected_keys = {
        "mm005_browser_research_dataset_version",
        "dataset_id",
        "gate_id",
        "parent_protocol_sha256",
        "seed",
        "split",
        "source_count",
        "provenance",
        "screenshot_receipts",
        "source_snapshot_receipts",
        "records",
    }
    if set(value) != expected_keys:
        _fail("DATASET_KEYS_INVALID", f"$.datasets.{split}")
    expected_sources = (
        TRAIN_SOURCE_COUNT if split == "train" else VALIDATION_SOURCE_COUNT
    )
    if (
        type(value["mm005_browser_research_dataset_version"]) is not int
        or value["mm005_browser_research_dataset_version"] != DATASET_VERSION
        or value["dataset_id"] != "mm005-browser-research-v1"
        or value["gate_id"] != EXECUTION_GATE_ID
        or value["parent_protocol_sha256"] != parent_protocol_sha256
        or type(value["seed"]) is not int
        or value["seed"] != SEED
        or value["split"] != split
        or type(value["source_count"]) is not int
        or value["source_count"] != expected_sources
        or value["provenance"] != _dataset_provenance()
    ):
        _fail("DATASET_VALUE_INVALID", f"$.datasets.{split}")
    records = [
        _object(raw, f"$.datasets.{split}.records[]")
        for raw in _array(value["records"], f"$.datasets.{split}.records")
    ]
    expected_count = TRAIN_RECORDS if split == "train" else VALIDATION_RECORDS
    if len(records) != expected_count or any(
        record["split"] != split for record in records
    ):
        _fail("DATASET_RECORD_COUNT_INVALID", f"$.datasets.{split}.records")
    return records


def _screenshot_path(template: Mapping[str, Any], source_id: str) -> str:
    return (
        f"{OUTPUT_ROOT}/screenshots/{template['split']}/"
        f"{template['task_family_id']}/{template['template_id']}/{source_id}.png"
    )


def _snapshot_path(template: Mapping[str, Any], source_id: str) -> str:
    return (
        f"{OUTPUT_ROOT}/snapshots/{template['split']}/"
        f"{template['task_family_id']}/{template['template_id']}/{source_id}.json"
    )


def _published_at(ordinal: int, source_index: int) -> str:
    return f"2026-03-{ordinal * 2 + source_index:02d}T08:00:00Z"


def _pixel_bbox(bbox: Sequence[int]) -> tuple[int, int, int, int]:
    return (
        bbox[0] * raster.PNG_WIDTH // 1_000,
        bbox[1] * raster.PNG_HEIGHT // 1_000,
        bbox[2] * raster.PNG_WIDTH // 1_000,
        bbox[3] * raster.PNG_HEIGHT // 1_000,
    )


def _node(ref: str, tag: str, bbox: list[int], text: str) -> dict[str, Any]:
    return {"bbox": bbox, "ref": ref, "tag": tag, "text": text}


def _record_provenance() -> dict[str, Any]:
    return {
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


def _dataset_provenance() -> dict[str, Any]:
    return {
        "source": "deterministic_reviewed_synthetic_browser_snapshot_generation",
        "license": "repository_generated_synthetic",
        "synthetic_only": True,
        "real_content": False,
        "external_content": False,
        "network_accessed": False,
        "live_browser_used": False,
        "javascript_executed": False,
        "capture_adapter_used": False,
    }


def _expected_counts() -> dict[str, Any]:
    return {
        "template_count": TEMPLATE_COUNT,
        "record_count": RECORD_COUNT,
        "source_count": SOURCE_COUNT,
        "screenshot_count": SCREENSHOT_COUNT,
        "source_snapshot_count": SOURCE_SNAPSHOT_COUNT,
        "train_records": TRAIN_RECORDS,
        "validation_records": VALIDATION_RECORDS,
        "train_sources": TRAIN_SOURCE_COUNT,
        "validation_sources": VALIDATION_SOURCE_COUNT,
        "task_family_count": len(parent.TASK_FAMILY_IDS),
        "source_kind_count": len(parent.SOURCE_KINDS),
    }


def _receipt(path: str, payload: bytes) -> dict[str, Any]:
    return {"path": path, "bytes": len(payload), "sha256": sha256_bytes(payload)}


def _closed_receipts(
    value: Mapping[str, Mapping[str, Any]], location: str
) -> dict[str, dict[str, Any]]:
    if not value:
        _fail("SOURCE_RECEIPTS_EMPTY", location)
    result: dict[str, dict[str, Any]] = {}
    for name, raw in sorted(value.items()):
        if type(name) is not str or not name:
            _fail("SOURCE_RECEIPT_NAME_INVALID", location)
        result[name] = _closed_receipt(
            raw,
            expected_path=None,
            location=f"{location}.{name}",
        )
    return result


def _closed_receipt(
    value: Mapping[str, Any], *, expected_path: str | None, location: str
) -> dict[str, Any]:
    receipt = _object(value, location)
    if set(receipt) != {"path", "bytes", "sha256"}:
        _fail("RECEIPT_KEYS_INVALID", location)
    if (
        type(receipt["path"]) is not str
        or not receipt["path"]
        or (expected_path is not None and receipt["path"] != expected_path)
        or type(receipt["bytes"]) is not int
        or receipt["bytes"] <= 0
        or type(receipt["sha256"]) is not str
        or not str(receipt["sha256"]).startswith("sha256:")
        or len(str(receipt["sha256"])) != 71
        or any(
            character not in "0123456789abcdef"
            for character in str(receipt["sha256"])[7:]
        )
    ):
        _fail("RECEIPT_VALUE_INVALID", location)
    return dict(receipt)


def _json_object(payload: bytes, location: str) -> Mapping[str, Any]:
    try:
        value = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MM005BrowserResearchDataProtocolError("JSON_INVALID", location) from exc
    return _object(value, location)


def _object(value: object, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail("EXPECTED_OBJECT", location)
    return value


def _array(value: object, location: str) -> list[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        _fail("EXPECTED_ARRAY", location)
    return list(value)


def _fail(code: str, location: str = "$") -> NoReturn:
    raise MM005BrowserResearchDataProtocolError(code, location)
