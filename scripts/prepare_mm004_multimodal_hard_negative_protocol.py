"""Build or check the frozen MM-004 hard-negative data protocol."""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from fullcycle_bridge import multimodal_hard_negative as contract  # noqa: E402

OUTPUT_PATH = ROOT / "configs" / "mm004_multimodal_hard_negative_data_protocol_v1.json"
SOURCE_PATHS = {
    "contract": ("src/fullcycle_bridge/multimodal_hard_negative.py", "protocol_source"),
    "builder": ("scripts/prepare_mm004_multimodal_hard_negative_protocol.py", "protocol_source"),
    "mm002_suite": ("fixtures/gui_grounding_eval_v1/valid/suite.json", "read_only_exclusion"),
    "mm003_train": ("fixtures/mm003_post_training_v1/train.json", "read_only_exclusion"),
    "mm003_validation": ("fixtures/mm003_post_training_v1/validation.json", "read_only_exclusion"),
    "mm003_adapter_readme": ("baseline/adapters/mm003-qwen2.5-vl-3b-qlora-sft-v2/README.md", "read_only_adapter"),
    "mm003_adapter_config": ("baseline/adapters/mm003-qwen2.5-vl-3b-qlora-sft-v2/adapter_config.json", "read_only_adapter"),
    "mm003_adapter_weights": ("baseline/adapters/mm003-qwen2.5-vl-3b-qlora-sft-v2/adapter_model.safetensors", "read_only_adapter"),
}


def all_source_paths() -> dict[str, tuple[str, str]]:
    """Return the closed tracked source set, including every upstream image."""

    paths = dict(SOURCE_PATHS)
    image_roots = (
        ROOT / "fixtures" / "mm003_baseline_v1" / "screenshots",
        ROOT / "fixtures" / "mm003_post_training_v1" / "screenshots",
    )
    images = sorted(
        path
        for image_root in image_roots
        for path in image_root.rglob("*.png")
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
    result: dict[str, set[str]] = {kind: set() for kind in contract.IDENTITY_KINDS}
    suite = _load_json(ROOT / SOURCE_PATHS["mm002_suite"][0])
    datasets = [
        _load_json(ROOT / SOURCE_PATHS["mm003_train"][0]),
        _load_json(ROOT / SOURCE_PATHS["mm003_validation"][0]),
    ]
    for case in suite["cases"]:
        _add_record_exclusions(result, case, candidate_key="gold")
    for dataset in datasets:
        for record in dataset["records"]:
            _add_record_exclusions(result, record, candidate_key="target")
    receipts = source_receipts()
    for name, receipt in receipts.items():
        if name.startswith("upstream_image_"):
            result["image_sha256"].add(receipt["sha256"])
    return {kind: sorted(values) for kind, values in result.items()}


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
            raise SystemExit("MM-004 frozen protocol is stale")
        print(f"MM-004 protocol verified: {contract.sha256_bytes(payload)}")
        return 0
    OUTPUT_PATH.write_bytes(payload)
    print(f"MM-004 protocol frozen: {contract.sha256_bytes(payload)}")
    return 0


def _add_record_exclusions(
    result: dict[str, set[str]], record: dict[str, Any], *, candidate_key: str
) -> None:
    result["case_ids"].add(record["case_id"])
    result["family_ids"].add(record["family_id"])
    model_input = record["model_input"]
    result["instruction_sha256"].add(
        contract.identity("instruction", model_input["instruction"])
    )
    result["observation_sha256"].add(
        contract.identity("observation", model_input["observation"])
    )
    result["candidate_sha256"].add(
        contract.identity("candidate", record[candidate_key])
    )


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
