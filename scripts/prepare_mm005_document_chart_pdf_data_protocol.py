"""Build or check the frozen MM-005 Document/Chart/PDF data protocol."""

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
sys.path.insert(0, str(ROOT))

from fullcycle_bridge import mm005_document_chart_pdf_data as contract  # noqa: E402
from fullcycle_bridge import (  # noqa: E402
    multimodal_environment_adaptation as parent_contract,
)
from scripts import (  # noqa: E402
    prepare_mm005_multimodal_environment_adaptation_protocol as parent_prepare,
)

SOURCE_PATHS = {
    "parent_contract": "src/fullcycle_bridge/multimodal_environment_adaptation.py",
    "data_contract": "src/fullcycle_bridge/mm005_document_chart_pdf_data.py",
    "data_builder": "scripts/prepare_mm005_document_chart_pdf_data_protocol.py",
    "parent_builder": (
        "scripts/prepare_mm005_multimodal_environment_adaptation_protocol.py"
    ),
    "shared_raster": "src/fullcycle_bridge/mm003_baseline_protocol.py",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    payload = contract.artifact_json_bytes(build_protocol())
    output_path = ROOT / contract.PREREGISTRATION_PATH
    if args.check:
        if _read_regular_file_once(output_path) != payload:
            raise SystemExit("MM-005 Document/Chart/PDF data protocol is stale")
        print(f"MM-005 data protocol verified: {contract.sha256_bytes(payload)}")
        return 0
    assert_fixed_outputs_absent()
    if output_path.exists():
        raise FileExistsError(output_path)
    output_path.write_bytes(payload)
    print(f"MM-005 data protocol frozen: {contract.sha256_bytes(payload)}")
    return 0


def build_protocol() -> dict[str, Any]:
    return contract.expected_preregistration(
        freeze_status="frozen",
        source_receipts=source_receipts(),
        parent_protocol_receipt=parent_protocol_receipt(),
    )


def source_receipts() -> dict[str, dict[str, Any]]:
    return {
        name: _receipt(relative, _read_regular_file_once(ROOT / relative))
        for name, relative in sorted(SOURCE_PATHS.items())
    }


def parent_protocol_receipt() -> dict[str, Any]:
    path = contract.PARENT_PROTOCOL_PATH
    payload = _read_regular_file_once(ROOT / path)
    parsed = json.loads(payload)
    expected = parent_prepare.build_protocol()
    if parsed != expected or parent_contract.canonical_json_bytes(expected) != payload:
        raise RuntimeError("parent MM-005 environment-adaptation protocol drift")
    return _receipt(path, payload)


def planned_output_payloads() -> dict[str, bytes]:
    return contract.expected_output_payloads(parent_protocol_receipt()["sha256"])


def assert_fixed_outputs_absent() -> None:
    for relative in (contract.OUTPUT_ROOT, contract.EVIDENCE_PATH):
        if (ROOT / relative).exists():
            raise FileExistsError(f"fixed output already exists: {relative}")


def _receipt(path: str, payload: bytes) -> dict[str, Any]:
    return {
        "path": path,
        "bytes": len(payload),
        "sha256": contract.sha256_bytes(payload),
    }


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
