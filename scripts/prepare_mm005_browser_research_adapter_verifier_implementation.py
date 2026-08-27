"""Build or check MM-005 Browser Adapter/Verifier implementation evidence."""

from __future__ import annotations

import argparse
import os
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(ROOT))

from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_adapter_verifier_implementation as evidence,
)
from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_adapter_verifier_protocol as protocol,
)
from scripts import (  # noqa: E402
    prepare_mm005_browser_research_adapter_verifier_protocol as protocol_prepare,
)

SOURCE_PATHS = {
    "adapter_verifier_component": (
        "src/fullcycle_bridge/mm005_browser_research_adapter_verifier.py"
    ),
    "implementation_builder": (
        "scripts/prepare_mm005_browser_research_adapter_verifier_implementation.py"
    ),
    "implementation_evidence_contract": (
        "src/fullcycle_bridge/"
        "mm005_browser_research_adapter_verifier_implementation.py"
    ),
    "protocol_builder": (
        "scripts/prepare_mm005_browser_research_adapter_verifier_protocol.py"
    ),
    "protocol_contract": (
        "src/fullcycle_bridge/mm005_browser_research_adapter_verifier_protocol.py"
    ),
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    payload = evidence.artifact_json_bytes(build_evidence())
    output_path = ROOT / evidence.EVIDENCE_PATH
    if args.check:
        if _read_regular_file_once(output_path) != payload:
            raise SystemExit(
                "MM-005 Browser Adapter/Verifier implementation evidence is stale"
            )
        print(
            "MM-005 Browser Adapter/Verifier implementation evidence verified: "
            f"{evidence.sha256_bytes(payload)}"
        )
        return 0
    if output_path.exists():
        raise FileExistsError(output_path)
    output_path.write_bytes(payload)
    print(
        "MM-005 Browser Adapter/Verifier implementation evidence written: "
        f"{evidence.sha256_bytes(payload)}"
    )
    return 0


def build_evidence() -> dict[str, Any]:
    return evidence.expected_evidence(**implementation_inputs())


def implementation_inputs() -> dict[str, Any]:
    _validate_protocol_merge()
    protocol_inputs = protocol_prepare.protocol_inputs()
    return {
        "implementation_source_receipts": source_receipts(),
        "protocol_payload": _read_regular_file_once(ROOT / protocol.PROTOCOL_PATH),
        "protocol_source_receipts": protocol_inputs["source_receipts"],
        "generation_evidence_payload": protocol_inputs["generation_evidence_payload"],
        "generation_protocol_payload": protocol_inputs["generation_protocol_payload"],
        "generation_source_receipts": protocol_inputs["generation_source_receipts"],
        "data_protocol_payload": protocol_inputs["data_protocol_payload"],
        "data_source_receipts": protocol_inputs["data_source_receipts"],
        "parent_protocol_receipt": protocol_inputs["parent_protocol_receipt"],
        "output_payloads": protocol_inputs["output_payloads"],
        "exclusions": protocol_inputs["exclusions"],
    }


def source_receipts() -> dict[str, dict[str, Any]]:
    return {
        name: _receipt(relative, _read_regular_file_once(ROOT / relative))
        for name, relative in sorted(SOURCE_PATHS.items())
    }


def _validate_protocol_merge() -> None:
    ancestor = subprocess.run(
        [
            "git",
            "merge-base",
            "--is-ancestor",
            evidence.PROTOCOL_MERGE_COMMIT,
            "HEAD",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    if ancestor.returncode != 0:
        raise RuntimeError("Browser Adapter/Verifier protocol merge is not an ancestor")
    frozen = subprocess.run(
        [
            "git",
            "show",
            f"{evidence.PROTOCOL_MERGE_COMMIT}:{protocol.PROTOCOL_PATH}",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout
    current = _read_regular_file_once(ROOT / protocol.PROTOCOL_PATH)
    if frozen != current:
        raise RuntimeError("Browser Adapter/Verifier protocol changed after merge")


def _receipt(path: str, payload: bytes) -> dict[str, Any]:
    return {
        "path": path,
        "bytes": len(payload),
        "sha256": evidence.sha256_bytes(payload),
    }


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
