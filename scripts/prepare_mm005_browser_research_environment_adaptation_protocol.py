"""Build or check the frozen MM-005 Browser Research adaptation protocol."""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from fullcycle_bridge import (  # noqa: E402
    browser_research_environment_adaptation as contract,
)

OUTPUT_PATH = (
    ROOT / "configs" / "mm005_browser_research_environment_adaptation_protocol_v1.json"
)
SOURCE_PATHS = {
    "contract": (
        "src/fullcycle_bridge/browser_research_environment_adaptation.py",
        "protocol_source",
    ),
    "builder": (
        "scripts/prepare_mm005_browser_research_environment_adaptation_protocol.py",
        "protocol_source",
    ),
    "parent_contract": (
        "src/fullcycle_bridge/multimodal_environment_adaptation.py",
        "parent_protocol",
    ),
    "parent_builder": (
        "scripts/prepare_mm005_multimodal_environment_adaptation_protocol.py",
        "parent_protocol",
    ),
    "parent_protocol": (
        "configs/mm005_multimodal_environment_adaptation_protocol_v1.json",
        "parent_protocol",
    ),
    "document_repeatability_protocol": (
        "configs/mm005_document_chart_pdf_model_evaluation_repeatability_protocol_v1.json",
        "sequencing_evidence",
    ),
    "document_repeatability_review": (
        "baseline/mm005-document-chart-pdf-model-eval-repeatability-v1-result-review.json",
        "sequencing_evidence",
    ),
    "document_generation_evidence": (
        "baseline/mm005-document-chart-pdf-data-generation-v1.json",
        "sequencing_evidence",
    ),
    "document_dataset_manifest": (
        "fixtures/mm005_document_chart_pdf_v1/manifest.json",
        "sequencing_evidence",
    ),
    "runtime_freeze": (
        "baseline/runtime-freeze-v1.json",
        "runtime_boundary",
    ),
    "lane_b_capture_schema": (
        "schemas/lane_b_capture_bundle_v1.schema.json",
        "capture_boundary",
    ),
    "mm002_suite": (
        "fixtures/gui_grounding_eval_v1/valid/suite.json",
        "read_only_exclusion",
    ),
    "mm003_train": (
        "fixtures/mm003_post_training_v1/train.json",
        "read_only_exclusion",
    ),
    "mm003_validation": (
        "fixtures/mm003_post_training_v1/validation.json",
        "read_only_exclusion",
    ),
    "mm004_train": (
        "fixtures/mm004_hard_negative_v1/train.json",
        "read_only_exclusion",
    ),
    "mm004_validation": (
        "fixtures/mm004_hard_negative_v1/validation.json",
        "read_only_exclusion",
    ),
    "mm005_document_train": (
        "fixtures/mm005_document_chart_pdf_v1/train.json",
        "read_only_exclusion",
    ),
    "mm005_document_validation": (
        "fixtures/mm005_document_chart_pdf_v1/validation.json",
        "read_only_exclusion",
    ),
}
IMAGE_ROOTS = (
    "fixtures/mm003_baseline_v1/screenshots",
    "fixtures/mm003_post_training_v1/screenshots",
    "fixtures/mm004_hard_negative_v1/images",
    "fixtures/mm005_document_chart_pdf_v1/images",
)


def all_source_paths() -> dict[str, tuple[str, str]]:
    """Return the closed source set, including every prior synthetic image."""

    paths = dict(SOURCE_PATHS)
    images = sorted(
        path
        for relative_root in IMAGE_ROOTS
        for path in (ROOT / relative_root).rglob("*.png")
    )
    for index, path in enumerate(images, 1):
        paths[f"upstream_image_{index:03d}"] = (
            path.relative_to(ROOT).as_posix(),
            "read_only_exclusion",
        )
    return paths


def source_receipts() -> dict[str, dict[str, Any]]:
    result = {}
    for name, (relative, role) in all_source_paths().items():
        payload = _read_regular_file_once(ROOT / relative)
        result[name] = {
            "path": relative,
            "bytes": len(payload),
            "sha256": contract.sha256_bytes(payload),
            "role": role,
        }
    return result


def exclusion_registry() -> dict[str, list[str]]:
    """Recompute prior identities from source content rather than copied IDs."""

    result: dict[str, set[str]] = {key: set() for key in contract.EXCLUSION_KEYS}
    suite = _load_json(ROOT / SOURCE_PATHS["mm002_suite"][0])
    for case in _object_list(suite, "cases"):
        _add_upstream_record(
            result,
            record=case,
            record_id_key="case_id",
            instruction=case["model_input"]["instruction"],
            observation=case["model_input"]["observation"],
            target=case["gold"],
        )

    for name in ("mm003_train", "mm003_validation"):
        dataset = _load_json(ROOT / SOURCE_PATHS[name][0])
        for record in _object_list(dataset, "records"):
            _add_upstream_record(
                result,
                record=record,
                record_id_key="case_id",
                instruction=record["model_input"]["instruction"],
                observation=record["model_input"]["observation"],
                target=record["target"],
            )

    for name in ("mm004_train", "mm004_validation"):
        dataset = _load_json(ROOT / SOURCE_PATHS[name][0])
        for record in _object_list(dataset, "records"):
            _add_upstream_record(
                result,
                record=record,
                record_id_key="record_id",
                instruction=record["instruction"],
                observation=record["observation"],
                target=record["candidate_action"],
            )

    for name in ("mm005_document_train", "mm005_document_validation"):
        dataset = _load_json(ROOT / SOURCE_PATHS[name][0])
        for record in _object_list(dataset, "records"):
            _add_upstream_record(
                result,
                record=record,
                record_id_key="record_id",
                instruction=record["instruction"],
                observation=record["observation"],
                target=record["expected_output"],
            )

    for name, receipt in source_receipts().items():
        if name.startswith("upstream_image_"):
            result["image_sha256"].add(str(receipt["sha256"]))
    return {key: sorted(values) for key, values in result.items()}


def build_protocol() -> dict[str, Any]:
    return contract.expected_protocol(
        freeze_status="frozen",
        source_receipts=source_receipts(),
        exclusions=exclusion_registry(),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    payload = contract.canonical_json_bytes(build_protocol())
    if args.check:
        if _read_regular_file_once(OUTPUT_PATH) != payload:
            raise SystemExit("MM-005 Browser Research frozen protocol is stale")
        print(
            "MM-005 Browser Research protocol verified: "
            f"{contract.sha256_bytes(payload)}"
        )
        return 0
    OUTPUT_PATH.write_bytes(payload)
    print(f"MM-005 Browser Research protocol frozen: {contract.sha256_bytes(payload)}")
    return 0


def _add_upstream_record(
    result: dict[str, set[str]],
    *,
    record: Mapping[str, Any],
    record_id_key: str,
    instruction: object,
    observation: object,
    target: object,
) -> None:
    record_id = record.get(record_id_key)
    family_id = record.get("family_id")
    if type(record_id) is not str or not record_id:
        raise ValueError(f"invalid upstream {record_id_key}")
    if type(family_id) is not str or not family_id:
        raise ValueError("invalid upstream family_id")
    result["case_ids"].add(record_id)
    result["family_ids"].add(family_id)
    result["instruction_content_sha256"].add(
        contract.content_identity("instruction", instruction)
    )
    result["observation_content_sha256"].add(
        contract.content_identity("observation", observation)
    )
    result["target_content_sha256"].add(contract.content_identity("target", target))


def _object_list(value: Mapping[str, Any], key: str) -> list[dict[str, Any]]:
    raw = value.get(key)
    if (
        not isinstance(raw, list)
        or not raw
        or any(not isinstance(item, dict) for item in raw)
    ):
        raise ValueError(f"expected non-empty object array: {key}")
    return raw


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(_read_regular_file_once(path))
    if not isinstance(value, dict):
        raise ValueError(f"expected object: {path}")
    return value


def _read_regular_file_once(path: Path) -> bytes:
    resolved = path.resolve(strict=True)
    before = resolved.stat()
    if not stat.S_ISREG(before.st_mode) or resolved.is_symlink():
        raise ValueError(f"not a regular file: {path}")
    with resolved.open("rb") as handle:
        payload = handle.read()
        after_handle = os.fstat(handle.fileno())
    after_path = resolved.stat()
    if _stat_signature(before) != _stat_signature(after_handle) or _stat_signature(
        before
    ) != _stat_signature(after_path):
        raise ValueError(f"file changed while reading: {path}")
    return payload


def _stat_signature(value: os.stat_result) -> tuple[int, int, int, int]:
    return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)


if __name__ == "__main__":
    raise SystemExit(main())
