"""Deterministic, model-free MM-005 Document/Chart/PDF data preregistration."""

from __future__ import annotations

import json
import struct
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any, NoReturn

from . import mm003_baseline_protocol as raster
from . import multimodal_environment_adaptation as parent

DATA_PROTOCOL_VERSION = 1
DATASET_VERSION = 1
MANIFEST_VERSION = 1
GATE_ID = "MM-005-document-chart-pdf-data-protocol-v1"
EXECUTION_GATE_ID = "MM-005-document-chart-pdf-data-generation-v1"
NEXT_GATE = EXECUTION_GATE_ID
PREREGISTRATION_PATH = "configs/mm005_document_chart_pdf_data_protocol_v1.json"
PARENT_PROTOCOL_PATH = (
    "configs/mm005_multimodal_environment_adaptation_protocol_v1.json"
)
OUTPUT_ROOT = "fixtures/mm005_document_chart_pdf_v1"
TRAIN_PATH = f"{OUTPUT_ROOT}/train.json"
VALIDATION_PATH = f"{OUTPUT_ROOT}/validation.json"
MANIFEST_PATH = f"{OUTPUT_ROOT}/manifest.json"
EVIDENCE_PATH = "baseline/mm005-document-chart-pdf-data-generation-v1.json"

SEED = 55_005
TEMPLATES_PER_TASK = 8
TRAIN_TEMPLATES_PER_TASK = 6
VALIDATION_TEMPLATES_PER_TASK = 2
TEMPLATE_COUNT = len(parent.TASK_FAMILY_IDS) * TEMPLATES_PER_TASK
RECORD_COUNT = TEMPLATE_COUNT
IMAGE_COUNT = TEMPLATE_COUNT
TRAIN_RECORDS = len(parent.TASK_FAMILY_IDS) * TRAIN_TEMPLATES_PER_TASK
VALIDATION_RECORDS = len(parent.TASK_FAMILY_IDS) * VALIDATION_TEMPLATES_PER_TASK

TASK_SLUGS = {
    "document_text_evidence_grounding": "document-text",
    "table_cell_evidence_grounding": "table-cell",
    "chart_value_evidence_grounding": "chart-value",
    "page_region_selection": "page-region",
}
SOURCE_PLANS = {
    "document_text_evidence_grounding": (
        "synthetic_text_document",
        "synthetic_text_document",
        "synthetic_text_document",
        "synthetic_single_page_pdf",
        "synthetic_single_page_pdf",
        "synthetic_single_page_pdf",
        "synthetic_text_document",
        "synthetic_single_page_pdf",
    ),
    "table_cell_evidence_grounding": (
        "synthetic_table_document",
        "synthetic_table_document",
        "synthetic_table_document",
        "synthetic_single_page_pdf",
        "synthetic_single_page_pdf",
        "synthetic_single_page_pdf",
        "synthetic_table_document",
        "synthetic_single_page_pdf",
    ),
    "chart_value_evidence_grounding": (
        "synthetic_bar_chart",
        "synthetic_bar_chart",
        "synthetic_bar_chart",
        "synthetic_single_page_pdf",
        "synthetic_single_page_pdf",
        "synthetic_single_page_pdf",
        "synthetic_bar_chart",
        "synthetic_single_page_pdf",
    ),
    "page_region_selection": (
        "synthetic_text_document",
        "synthetic_text_document",
        "synthetic_table_document",
        "synthetic_table_document",
        "synthetic_bar_chart",
        "synthetic_single_page_pdf",
        "synthetic_bar_chart",
        "synthetic_single_page_pdf",
    ),
}
PDF_COUNT = sum(
    source_kind == "synthetic_single_page_pdf"
    for source_plan in SOURCE_PLANS.values()
    for source_kind in source_plan
)
OUTPUT_FILE_COUNT = IMAGE_COUNT + PDF_COUNT + 3

FREEZE_CLAIMS = (
    "generation_executed",
    "records_generated",
    "images_generated",
    "dataset_validated",
    "environment_adapter_implemented",
    "verifier_executed",
    "model_trained",
    "model_evaluated",
    "quality_improved",
    "safety_established",
    "real_content_collected",
    "external_content_downloaded",
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
    "deterministic_output_rebuild",
    "planned_output_receipt_integrity",
    "record_contract",
    "task_and_source_coverage",
    "split_distribution",
    "family_template_content_and_image_split_isolation",
    "prior_stage_content_exclusion",
    "synthetic_png_integrity",
    "answer_evidence_semantics",
    "fixed_outputs_absent_at_freeze",
    "runtime_authority_preserved",
    "fail_closed_claims",
)


class MM005DataProtocolError(ValueError):
    """Stable fail-closed error for the data preregistration and planned bytes."""

    def __init__(self, code: str, location: str = "$") -> None:
        self.code = code
        self.location = location
        super().__init__(f"{code} at {location}")


@dataclass(frozen=True)
class DataProtocolSummary:
    protocol_version: int
    template_count: int
    record_count: int
    image_count: int
    source_artifact_count: int
    train_records: int
    validation_records: int
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
        source_plan = SOURCE_PLANS[task_family_id]
        if len(source_plan) != TEMPLATES_PER_TASK:
            _fail("SOURCE_PLAN_COUNT_INVALID", f"$.source_plans.{task_family_id}")
        for ordinal, source_kind in enumerate(source_plan, 1):
            templates.append(
                {
                    "template_id": f"mm005-{TASK_SLUGS[task_family_id]}-{ordinal:02d}",
                    "ordinal": ordinal,
                    "content_seed": SEED + task_index * 100 + ordinal,
                    "split": (
                        "train"
                        if ordinal <= TRAIN_TEMPLATES_PER_TASK
                        else "validation"
                    ),
                    "task_family_id": task_family_id,
                    "source_kind": source_kind,
                }
            )
    return templates


def expected_images() -> dict[str, bytes]:
    result = {}
    for template in expected_templates():
        materialized = _materialize_template(template)
        path = _image_path(template)
        result[path] = _render_png(template, materialized["regions"])
    return dict(sorted(result.items()))


def expected_source_artifacts() -> dict[str, bytes]:
    result = {}
    for template in expected_templates():
        if template["source_kind"] == "synthetic_single_page_pdf":
            materialized = _materialize_template(template)
            result[_pdf_path(template)] = _render_pdf(
                template, materialized["regions"]
            )
    return dict(sorted(result.items()))


def expected_records(images: Mapping[str, bytes]) -> list[dict[str, Any]]:
    records = []
    for template in expected_templates():
        materialized = _materialize_template(template)
        image_path = _image_path(template)
        if image_path not in images:
            _fail("PLANNED_IMAGE_MISSING", f"$.images.{image_path}")
        observation = {
            "image_sha256": sha256_bytes(images[image_path]),
            "layout_source": "synthetic_ground_truth_not_runtime_ocr",
            "page_count": 1,
            "page_number": 1,
            "regions": materialized["regions"],
        }
        records.append(
            parent.build_record(
                template_id=str(template["template_id"]),
                split=str(template["split"]),
                task_family_id=str(template["task_family_id"]),
                source_kind=str(template["source_kind"]),
                instruction=str(materialized["instruction"]),
                observation=observation,
                expected_output=_object(materialized["expected_output"], "$.expected"),
                provenance=_record_provenance(),
            )
        )
    return records


def expected_output_payloads(parent_protocol_sha256: str) -> dict[str, bytes]:
    """Rebuild every future output byte in memory without writing a file."""

    images = expected_images()
    source_artifacts = expected_source_artifacts()
    records = expected_records(images)
    payloads = {**images, **source_artifacts}
    for split, path in (("train", TRAIN_PATH), ("validation", VALIDATION_PATH)):
        split_records = [record for record in records if record["split"] == split]
        split_images = {
            image_path: _receipt(image_path, payload)
            for image_path, payload in images.items()
            if f"/images/{split}/" in image_path
        }
        split_source_artifacts = {
            source_path: _receipt(source_path, payload)
            for source_path, payload in source_artifacts.items()
            if f"/sources/{split}/" in source_path
        }
        payloads[path] = artifact_json_bytes(
            {
                "mm005_document_chart_pdf_dataset_version": DATASET_VERSION,
                "dataset_id": "mm005-document-chart-pdf-v1",
                "gate_id": EXECUTION_GATE_ID,
                "parent_protocol_sha256": parent_protocol_sha256,
                "seed": SEED,
                "split": split,
                "provenance": _dataset_provenance(),
                "image_receipts": dict(sorted(split_images.items())),
                "source_artifact_receipts": dict(
                    sorted(split_source_artifacts.items())
                ),
                "records": split_records,
            }
        )
    manifest_receipts = {
        path: _receipt(path, payload) for path, payload in sorted(payloads.items())
    }
    payloads[MANIFEST_PATH] = artifact_json_bytes(
        {
            "mm005_document_chart_pdf_manifest_version": MANIFEST_VERSION,
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
        "mm005_document_chart_pdf_data_protocol_version": DATA_PROTOCOL_VERSION,
        "gate_id": GATE_ID,
        "freeze_status": freeze_status,
        "decision": "outcome_neutral_deterministic_synthetic_data_preregistration",
        "parent_protocol": parent_receipt,
        "source_receipts": sources,
        "generation_plan": {
            "seed": SEED,
            "dataset_id": "mm005-document-chart-pdf-v1",
            "output_root": OUTPUT_ROOT,
            "task_family_ids": list(parent.TASK_FAMILY_IDS),
            "source_kinds": list(parent.SOURCE_KINDS),
            "templates_per_task": TEMPLATES_PER_TASK,
            "train_templates_per_task": TRAIN_TEMPLATES_PER_TASK,
            "validation_templates_per_task": VALIDATION_TEMPLATES_PER_TASK,
            "template_count": TEMPLATE_COUNT,
            "record_count": RECORD_COUNT,
            "image_count": IMAGE_COUNT,
            "source_artifact_count": PDF_COUNT,
            "train_records": TRAIN_RECORDS,
            "validation_records": VALIDATION_RECORDS,
            "output_file_count": OUTPUT_FILE_COUNT,
            "template_registry": expected_templates(),
            "renderer": {
                "width": raster.PNG_WIDTH,
                "height": raster.PNG_HEIGHT,
                "color_type": "rgb_8_bit",
                "png_filter": "none_per_row",
                "zlib_level": 9,
                "host_font_used": False,
                "embedded_bitmap_font": True,
                "metadata_chunks": False,
                "pdf_source": {
                    "version": "1.4",
                    "page_width_points": 612,
                    "page_height_points": 792,
                    "base14_font": "Helvetica",
                    "external_renderer_used": False,
                    "png_and_pdf_share_layout_ground_truth": True,
                },
            },
            "network_allowed": False,
            "model_dependencies_allowed": False,
            "real_or_external_content_allowed": False,
            "capture_allowed": False,
            "runtime_ocr_allowed": False,
            "retry_count": 0,
        },
        "planned_outputs": output_receipts,
        "validation_contract": {
            "canonical_json_required": True,
            "exact_output_byte_rebuild_required": True,
            "parent_record_validator_required": True,
            "task_family_and_source_coverage_required": True,
            "per_task_split_distribution": {"train": 6, "validation": 2},
            "family_template_content_and_image_split_isolation_required": True,
            "prior_stage_exclusion_collision_allowed": False,
            "png_signature_dimensions_and_uniqueness_required": True,
            "pdf_signature_page_count_and_template_binding_required": True,
            "answer_must_be_visible_in_evidence_or_equal_region_ref": True,
            "model_or_llm_judge_used": False,
        },
        "freeze_preconditions": {
            "expected_absent_paths": [OUTPUT_ROOT, EVIDENCE_PATH],
            "generation_output_absent": True,
            "execution_evidence_absent": True,
        },
        "required_gates": list(REQUIRED_GATES),
        "authority_contract": {
            "model_output_has_execution_authority": False,
            "runtime_is_sole_policy_approval_wal_grounding_budget_dispatch_boundary": True,
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
        image_count=IMAGE_COUNT,
        source_artifact_count=PDF_COUNT,
        train_records=TRAIN_RECORDS,
        validation_records=VALIDATION_RECORDS,
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
    train_records = _dataset_records(train, "train")
    validation_records = _dataset_records(validation, "validation")
    records = [*train_records, *validation_records]
    record_summary = parent.validate_records(records, exclusions)
    if record_summary != {
        "record_count": RECORD_COUNT,
        "family_count": TEMPLATE_COUNT,
        "task_family_count": len(parent.TASK_FAMILY_IDS),
        "source_kind_count": len(parent.SOURCE_KINDS),
        "splits": ["train", "validation"],
    }:
        _fail("RECORD_SUMMARY_MISMATCH")
    _validate_distribution(records)
    _validate_image_bindings(records, payloads)
    _validate_source_artifact_bindings(payloads)
    _validate_answer_evidence_semantics(records)
    return {
        "planned_output_rebuild_valid": True,
        "template_count": TEMPLATE_COUNT,
        "record_count": RECORD_COUNT,
        "image_count": IMAGE_COUNT,
        "source_artifact_count": PDF_COUNT,
        "train_records": TRAIN_RECORDS,
        "validation_records": VALIDATION_RECORDS,
        "output_file_count": OUTPUT_FILE_COUNT,
        "output_bytes": sum(len(payload) for payload in payloads.values()),
        "generation_executed": False,
        "dataset_validated": False,
        "next_gate": NEXT_GATE,
    }


def _materialize_template(template: Mapping[str, Any]) -> dict[str, Any]:
    template_id = str(template["template_id"])
    ordinal = int(template["ordinal"])
    content_seed = int(template["content_seed"])
    task_family_id = str(template["task_family_id"])
    if task_family_id == "document_text_evidence_grounding":
        status = ("READY", "PENDING", "REVIEW", "APPROVED")[content_seed % 4]
        answer = f"{status}-{ordinal:02d}"
        evidence_ref = f"status-{ordinal:02d}"
        regions = [
            _region("page-01", "page", [30, 70, 970, 950], None),
            _region(
                f"title-{ordinal:02d}",
                "title",
                [80, 130, 920, 240],
                f"SYNTHETIC REPORT {ordinal:02d}",
            ),
            _region(
                evidence_ref,
                "text",
                [100, 330, 510, 470],
                f"STATUS {answer}",
            ),
            _region(
                f"owner-{ordinal:02d}",
                "text",
                [540, 330, 900, 470],
                f"OWNER TEAM {chr(64 + ordinal)}",
            ),
        ]
        instruction = (
            f"Return the status in synthetic report {ordinal:02d} and cite its "
            "evidence region."
        )
        expected_output = _expected(answer, evidence_ref)
    elif task_family_id == "table_cell_evidence_grounding":
        q1 = 100 + content_seed % 71
        q2 = 200 + content_seed % 83
        evidence_ref = f"alpha-q2-{ordinal:02d}"
        regions = [
            _region("page-01", "page", [30, 70, 970, 950], None),
            _region(
                f"title-{ordinal:02d}",
                "title",
                [80, 110, 920, 210],
                f"SYNTHETIC TABLE {ordinal:02d}",
            ),
            _region(f"head-item-{ordinal:02d}", "table_header", [100, 300, 360, 410], "ITEM"),
            _region(f"head-q1-{ordinal:02d}", "table_header", [360, 300, 610, 410], "Q1"),
            _region(f"head-q2-{ordinal:02d}", "table_header", [610, 300, 880, 410], "Q2"),
            _region(f"alpha-{ordinal:02d}", "table_cell", [100, 410, 360, 540], "ALPHA"),
            _region(f"alpha-q1-{ordinal:02d}", "table_cell", [360, 410, 610, 540], str(q1)),
            _region(evidence_ref, "table_cell", [610, 410, 880, 540], str(q2)),
            _region(f"beta-{ordinal:02d}", "table_cell", [100, 540, 360, 670], "BETA"),
            _region(f"beta-q1-{ordinal:02d}", "table_cell", [360, 540, 610, 670], str(q1 + 13)),
            _region(f"beta-q2-{ordinal:02d}", "table_cell", [610, 540, 880, 670], str(q2 + 17)),
        ]
        instruction = (
            f"Return the Q2 value for ALPHA in synthetic table {ordinal:02d} "
            "and cite the cell."
        )
        expected_output = _expected(str(q2), evidence_ref)
    elif task_family_id == "chart_value_evidence_grounding":
        alpha = 30 + content_seed % 25
        beta = 55 + content_seed % 23
        alpha_top = 800 - alpha * 7
        beta_top = 800 - beta * 7
        evidence_ref = f"beta-mark-{ordinal:02d}"
        regions = [
            _region("page-01", "page", [30, 70, 970, 950], None),
            _region(
                f"title-{ordinal:02d}",
                "title",
                [80, 110, 920, 210],
                f"SYNTHETIC BAR CHART {ordinal:02d}",
            ),
            _region(f"axis-y-{ordinal:02d}", "chart_axis", [120, 250, 140, 830], None),
            _region(f"alpha-mark-{ordinal:02d}", "chart_mark", [260, alpha_top, 470, 800], f"ALPHA {alpha}"),
            _region(evidence_ref, "chart_mark", [560, beta_top, 770, 800], f"BETA {beta}"),
            _region(f"legend-alpha-{ordinal:02d}", "chart_legend", [250, 830, 480, 900], "ALPHA"),
            _region(f"legend-beta-{ordinal:02d}", "chart_legend", [550, 830, 780, 900], "BETA"),
        ]
        instruction = (
            f"Return the BETA value in synthetic bar chart {ordinal:02d} and "
            "cite its mark."
        )
        expected_output = _expected(str(beta), evidence_ref)
    elif task_family_id == "page_region_selection":
        target_index = content_seed % 3 + 1
        refs = [f"block-{ordinal:02d}-{index}" for index in range(1, 4)]
        regions = [
            _region("page-01", "page", [30, 70, 970, 950], None),
            _region(
                f"title-{ordinal:02d}",
                "title",
                [80, 110, 920, 210],
                f"SYNTHETIC PAGE {ordinal:02d}",
            ),
        ]
        for index, ref in enumerate(refs, 1):
            x1 = 80 + (index - 1) * 300
            text = (
                f"TARGET BLOCK {ordinal:02d}"
                if index == target_index
                else f"DECOY BLOCK {ordinal:02d}-{index}"
            )
            regions.append(_region(ref, "text", [x1, 370, x1 + 250, 590], text))
        evidence_ref = refs[target_index - 1]
        instruction = (
            f"Select the region containing TARGET BLOCK {ordinal:02d} on the "
            "synthetic page and cite it."
        )
        expected_output = _expected(evidence_ref, evidence_ref)
    else:
        _fail("TASK_FAMILY_INVALID", "$.template.task_family_id")
    return {
        "template_id": template_id,
        "instruction": instruction,
        "regions": regions,
        "expected_output": expected_output,
    }


def _render_png(
    template: Mapping[str, Any], regions_value: object
) -> bytes:
    regions = _array(regions_value, "$.regions")
    pixels = bytearray((242, 245, 249) * (raster.PNG_WIDTH * raster.PNG_HEIGHT))
    raster._fill_rect(pixels, 0, 0, raster.PNG_WIDTH, 72, (38, 50, 68))
    raster._draw_text(
        pixels,
        22,
        20,
        f"SYNTHETIC {template['template_id']}".upper(),
        (255, 255, 255),
        3,
    )
    colors = {
        "page": (104, 117, 132),
        "title": (44, 112, 190),
        "text": (46, 139, 87),
        "table_header": (88, 96, 105),
        "table_cell": (151, 83, 176),
        "chart_axis": (58, 64, 72),
        "chart_mark": (226, 112, 45),
        "chart_legend": (44, 112, 190),
    }
    for raw in regions:
        region = _object(raw, "$.regions[]")
        bbox = [int(item) for item in _array(region["bbox"], "$.region.bbox")]
        x1, y1, x2, y2 = _pixel_bbox(bbox)
        role = str(region["role"])
        color = colors[role]
        if role == "chart_axis":
            raster._fill_rect(pixels, x1, y1, x2, y2, color)
        elif role == "chart_mark":
            raster._fill_rect(pixels, x1, y1, x2, y2, color)
            raster._stroke_rect(pixels, x1, y1, x2, y2, (122, 67, 26), 3)
        elif role == "page":
            raster._fill_rect(pixels, x1, y1, x2, y2, (255, 255, 255))
            raster._stroke_rect(pixels, x1, y1, x2, y2, color, 3)
        else:
            fill = (226, 230, 235) if role == "table_header" else (255, 255, 255)
            raster._fill_rect(pixels, x1, y1, x2, y2, fill)
            raster._stroke_rect(pixels, x1, y1, x2, y2, color, 3)
        visible_text = region["visible_text"]
        if visible_text:
            raster._draw_text(
                pixels,
                x1 + 8,
                y1 + 8,
                str(visible_text).upper(),
                (26, 32, 44),
                2,
            )
    raster._draw_text(
        pixels,
        30,
        raster.PNG_HEIGHT - 34,
        str(template["source_kind"]).replace("_", " ").upper(),
        (55, 64, 74),
        2,
    )
    return raster._encode_png(raster.PNG_WIDTH, raster.PNG_HEIGHT, bytes(pixels))


def _render_pdf(template: Mapping[str, Any], regions_value: object) -> bytes:
    regions = _array(regions_value, "$.regions")
    commands = ["q", "1 1 1 rg", "0 0 612 792 re f", "0 0 0 RG", "1 w"]
    commands.extend(
        [
            "0.15 0.20 0.27 rg",
            "0 735 612 57 re f",
            "1 1 1 rg",
            "BT /F1 14 Tf 18 757 Td "
            f"({_pdf_escape('SYNTHETIC ' + str(template['template_id']).upper())}) Tj ET",
        ]
    )
    for raw in regions:
        region = _object(raw, "$.regions[]")
        bbox = [int(item) for item in _array(region["bbox"], "$.region.bbox")]
        x1 = bbox[0] * 612 // 1_000
        x2 = bbox[2] * 612 // 1_000
        y1 = 792 - bbox[3] * 792 // 1_000
        y2 = 792 - bbox[1] * 792 // 1_000
        commands.extend(["0 0 0 RG", f"{x1} {y1} {x2 - x1} {y2 - y1} re S"])
        visible_text = region["visible_text"]
        if visible_text:
            text_y = max(y1 + 5, y2 - 15)
            commands.append(
                "0 0 0 rg BT /F1 9 Tf "
                f"{x1 + 5} {text_y} Td ({_pdf_escape(str(visible_text))}) Tj ET"
            )
    commands.extend(
        [
            "0 0 0 rg",
            "BT /F1 8 Tf 18 18 Td "
            f"({_pdf_escape(str(template['source_kind']))}) Tj ET",
            "Q",
        ]
    )
    stream = ("\n".join(commands) + "\n").encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>"
        ),
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n"
        + stream
        + b"endstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    payload = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(payload))
        payload.extend(f"{index} 0 obj\n".encode("ascii"))
        payload.extend(obj)
        payload.extend(b"\nendobj\n")
    xref_offset = len(payload)
    payload.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    payload.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        payload.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    payload.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(payload)


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
    expected_sources = Counter(
        (str(template["source_kind"]), str(template["split"]))
        for template in expected_templates()
    )
    actual_sources = Counter(
        (str(record["source_kind"]), str(record["split"])) for record in records
    )
    if actual_sources != expected_sources:
        _fail("SOURCE_SPLIT_DISTRIBUTION_MISMATCH")


def _validate_image_bindings(
    records: Sequence[Mapping[str, Any]], payloads: Mapping[str, bytes]
) -> None:
    images = {
        path: payload for path, payload in payloads.items() if path.endswith(".png")
    }
    if len(images) != IMAGE_COUNT or len(set(images.values())) != IMAGE_COUNT:
        _fail("IMAGE_COUNT_OR_UNIQUENESS_MISMATCH")
    hashes: dict[str, str] = {}
    for path, payload in images.items():
        if not payload.startswith(b"\x89PNG\r\n\x1a\n") or len(payload) < 24:
            _fail("PNG_SIGNATURE_INVALID", f"$.images.{path}")
        width, height = struct.unpack(">II", payload[16:24])
        if (width, height) != (raster.PNG_WIDTH, raster.PNG_HEIGHT):
            _fail("PNG_DIMENSIONS_INVALID", f"$.images.{path}")
        digest = sha256_bytes(payload)
        if digest in hashes:
            _fail("IMAGE_HASH_DUPLICATE", f"$.images.{path}")
        hashes[digest] = path
    for record in records:
        observation = _object(record["observation"], "$.record.observation")
        digest = str(observation["image_sha256"])
        bound_path = hashes.get(digest)
        if bound_path is None or f"/images/{record['split']}/" not in bound_path:
            _fail("RECORD_IMAGE_BINDING_INVALID", "$.record.observation.image_sha256")


def _validate_source_artifact_bindings(payloads: Mapping[str, bytes]) -> None:
    pdfs = {path: payload for path, payload in payloads.items() if path.endswith(".pdf")}
    expected_paths = {
        _pdf_path(template)
        for template in expected_templates()
        if template["source_kind"] == "synthetic_single_page_pdf"
    }
    if set(pdfs) != expected_paths or len(set(pdfs.values())) != PDF_COUNT:
        _fail("PDF_COUNT_PATH_OR_UNIQUENESS_MISMATCH")
    for path, payload in pdfs.items():
        if (
            not payload.startswith(b"%PDF-1.4\n")
            or not payload.endswith(b"%%EOF\n")
            or payload.count(b"/Type /Page ") != 1
            or payload.count(b"/Type /Pages ") != 1
        ):
            _fail("PDF_STRUCTURE_INVALID", f"$.source_artifacts.{path}")


def _validate_answer_evidence_semantics(
    records: Sequence[Mapping[str, Any]],
) -> None:
    for record in records:
        observation = _object(record["observation"], "$.record.observation")
        expected = _object(record["expected_output"], "$.record.expected_output")
        regions = {
            str(region["ref"]): region
            for raw in _array(observation["regions"], "$.record.observation.regions")
            for region in [_object(raw, "$.region")]
        }
        refs = [str(ref) for ref in _array(expected["evidence_refs"], "$.evidence_refs")]
        answer = str(expected["answer"])
        visible = " ".join(
            str(regions[ref]["visible_text"] or "") for ref in refs
        )
        if record["task_family_id"] == "page_region_selection":
            if answer not in refs:
                _fail("REGION_SELECTION_ANSWER_NOT_EVIDENCE")
        elif answer not in visible:
            _fail("ANSWER_NOT_VISIBLE_IN_EVIDENCE")


def _dataset_records(value: Mapping[str, Any], split: str) -> list[Mapping[str, Any]]:
    expected_keys = {
        "mm005_document_chart_pdf_dataset_version",
        "dataset_id",
        "gate_id",
        "parent_protocol_sha256",
        "seed",
        "split",
        "provenance",
        "image_receipts",
        "source_artifact_receipts",
        "records",
    }
    if set(value) != expected_keys:
        _fail("DATASET_KEYS_INVALID", f"$.datasets.{split}")
    if (
        type(value["mm005_document_chart_pdf_dataset_version"]) is not int
        or value["mm005_document_chart_pdf_dataset_version"] != DATASET_VERSION
        or value["dataset_id"] != "mm005-document-chart-pdf-v1"
        or value["gate_id"] != EXECUTION_GATE_ID
        or type(value["seed"]) is not int
        or value["seed"] != SEED
        or value["split"] != split
        or value["provenance"] != _dataset_provenance()
    ):
        _fail("DATASET_VALUE_INVALID", f"$.datasets.{split}")
    records = [
        _object(raw, f"$.datasets.{split}.records[]")
        for raw in _array(value["records"], f"$.datasets.{split}.records")
    ]
    expected_count = TRAIN_RECORDS if split == "train" else VALIDATION_RECORDS
    if len(records) != expected_count or any(record["split"] != split for record in records):
        _fail("DATASET_RECORD_COUNT_INVALID", f"$.datasets.{split}.records")
    return records


def _image_path(template: Mapping[str, Any]) -> str:
    return (
        f"{OUTPUT_ROOT}/images/{template['split']}/{template['task_family_id']}/"
        f"{template['template_id']}.png"
    )


def _pdf_path(template: Mapping[str, Any]) -> str:
    return (
        f"{OUTPUT_ROOT}/sources/{template['split']}/"
        f"{template['template_id']}.pdf"
    )


def _pdf_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _pixel_bbox(bbox: Sequence[int]) -> tuple[int, int, int, int]:
    return (
        bbox[0] * raster.PNG_WIDTH // 1_000,
        bbox[1] * raster.PNG_HEIGHT // 1_000,
        bbox[2] * raster.PNG_WIDTH // 1_000,
        bbox[3] * raster.PNG_HEIGHT // 1_000,
    )


def _region(
    ref: str, role: str, bbox: list[int], visible_text: str | None
) -> dict[str, Any]:
    return {"bbox": bbox, "ref": ref, "role": role, "visible_text": visible_text}


def _expected(answer: str, evidence_ref: str) -> dict[str, Any]:
    return {"answer": answer, "evidence_refs": [evidence_ref], "page_number": 1}


def _record_provenance() -> dict[str, Any]:
    return {
        "source": "deterministic_reviewed_synthetic_generation",
        "license": "repository_generated_synthetic",
        "synthetic_only": True,
        "real_content": False,
        "capture_adapter_used": False,
        "runtime_ocr_used": False,
        "model_output_has_execution_authority": False,
        "runtime_integration_authorized": False,
    }


def _dataset_provenance() -> dict[str, Any]:
    return {
        "source": "deterministic_reviewed_synthetic_generation",
        "license": "repository_generated_synthetic",
        "synthetic_only": True,
        "real_content": False,
        "external_content": False,
        "capture_adapter_used": False,
        "runtime_ocr_used": False,
    }


def _expected_counts() -> dict[str, Any]:
    return {
        "template_count": TEMPLATE_COUNT,
        "record_count": RECORD_COUNT,
        "image_count": IMAGE_COUNT,
        "source_artifact_count": PDF_COUNT,
        "train_records": TRAIN_RECORDS,
        "validation_records": VALIDATION_RECORDS,
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
    result = {}
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
        or any(character not in "0123456789abcdef" for character in str(receipt["sha256"])[7:])
    ):
        _fail("RECEIPT_VALUE_INVALID", location)
    return dict(receipt)


def _json_object(payload: bytes, location: str) -> Mapping[str, Any]:
    try:
        value = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MM005DataProtocolError("JSON_INVALID", location) from exc
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
    raise MM005DataProtocolError(code, location)
