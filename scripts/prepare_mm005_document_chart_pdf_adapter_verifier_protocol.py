"""Build or check the frozen MM-005 Document/Chart/PDF Adapter/Verifier protocol."""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(ROOT))

from fullcycle_bridge import (  # noqa: E402
    mm005_document_chart_pdf_adapter_verifier_protocol as contract,
)
from fullcycle_bridge import mm005_document_chart_pdf_data as data  # noqa: E402
from fullcycle_bridge import (  # noqa: E402
    mm005_document_chart_pdf_generation as generation,
)
from scripts import (  # noqa: E402
    run_mm005_document_chart_pdf_generation as generation_runner,
)

SOURCE_PATHS = {
    "adapter_verifier_builder": (
        "scripts/prepare_mm005_document_chart_pdf_adapter_verifier_protocol.py"
    ),
    "adapter_verifier_contract": (
        "src/fullcycle_bridge/mm005_document_chart_pdf_adapter_verifier_protocol.py"
    ),
    "data_builder": "scripts/prepare_mm005_document_chart_pdf_data_protocol.py",
    "data_contract": "src/fullcycle_bridge/mm005_document_chart_pdf_data.py",
    "generation_contract": (
        "src/fullcycle_bridge/mm005_document_chart_pdf_generation.py"
    ),
    "generation_runner": "scripts/run_mm005_document_chart_pdf_generation.py",
    "parent_builder": (
        "scripts/prepare_mm005_multimodal_environment_adaptation_protocol.py"
    ),
    "parent_contract": ("src/fullcycle_bridge/multimodal_environment_adaptation.py"),
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    payload = contract.artifact_json_bytes(build_protocol())
    output_path = ROOT / contract.PROTOCOL_PATH
    if args.check:
        if _read_regular_file_once(output_path) != payload:
            raise SystemExit("MM-005 Adapter/Verifier protocol is stale")
        print(
            "MM-005 Adapter/Verifier protocol verified: "
            f"{contract.sha256_bytes(payload)}"
        )
        return 0
    if output_path.exists():
        raise FileExistsError(output_path)
    output_path.write_bytes(payload)
    print(f"MM-005 Adapter/Verifier protocol frozen: {contract.sha256_bytes(payload)}")
    return 0


def build_protocol() -> dict[str, Any]:
    return contract.expected_protocol(
        freeze_status="frozen",
        **protocol_inputs(),
    )


def protocol_inputs() -> dict[str, Any]:
    data_protocol_payload, _, data_sources, parent_receipt = (
        generation_runner.data_protocol_context()
    )
    generation_protocol_payload = _read_regular_file_once(
        ROOT / generation.PROTOCOL_PATH
    )
    generation_evidence_payload = _read_regular_file_once(
        ROOT / generation.EVIDENCE_PATH
    )
    output_payloads = generation_runner.load_tracked_outputs()
    parent_protocol = _json_dict(
        _read_regular_file_once(ROOT / data.PARENT_PROTOCOL_PATH),
        data.PARENT_PROTOCOL_PATH,
    )
    exclusions = cast(
        Mapping[str, Sequence[str]],
        parent_protocol["exclusion_registry"],
    )
    return {
        "source_receipts": source_receipts(),
        "generation_evidence_payload": generation_evidence_payload,
        "generation_protocol_payload": generation_protocol_payload,
        "generation_source_receipts": generation_runner.source_receipts(),
        "data_protocol_payload": data_protocol_payload,
        "data_source_receipts": data_sources,
        "parent_protocol_receipt": parent_receipt,
        "output_payloads": output_payloads,
        "exclusions": exclusions,
    }


def source_receipts() -> dict[str, dict[str, Any]]:
    return {
        name: _receipt(relative, _read_regular_file_once(ROOT / relative))
        for name, relative in sorted(SOURCE_PATHS.items())
    }


def _receipt(path: str, payload: bytes) -> dict[str, Any]:
    return {
        "path": path,
        "bytes": len(payload),
        "sha256": contract.sha256_bytes(payload),
    }


def _json_dict(payload: bytes, location: str) -> dict[str, Any]:
    try:
        value = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"invalid JSON: {location}") from exc
    if not isinstance(value, dict) or contract.artifact_json_bytes(value) != payload:
        raise RuntimeError(f"non-canonical JSON object: {location}")
    return cast(dict[str, Any], value)


def _read_regular_file_once(path: Path) -> bytes:
    resolved = path.resolve(strict=True)
    before = resolved.stat()
    if resolved.is_symlink() or not stat.S_ISREG(before.st_mode):
        raise RuntimeError(f"unsafe file: {path}")
    with resolved.open("rb") as handle:
        payload = handle.read()
        after_handle = os.fstat(handle.fileno())
    after = resolved.stat()
    signatures = {
        (item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns)
        for item in (before, after_handle, after)
    }
    if len(signatures) != 1:
        raise RuntimeError(f"file changed while reading: {path}")
    return payload


if __name__ == "__main__":
    raise SystemExit(main())
