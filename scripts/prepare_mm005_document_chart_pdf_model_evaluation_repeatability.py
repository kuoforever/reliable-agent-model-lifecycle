"""Build or check the MM-005 model-evaluation repeatability protocol."""

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
    mm005_document_chart_pdf_model_evaluation_repeatability as contract,
)
from scripts import (  # noqa: E402
    prepare_mm005_document_chart_pdf_model_evaluation as baseline_builder,
)
from scripts import (  # noqa: E402
    validate_mm005_document_chart_pdf_model_evaluation_result as result_validator,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    protocol = build_protocol()
    payload = contract.artifact_json_bytes(protocol)
    output_path = ROOT / contract.PREREGISTRATION_PATH
    if args.check:
        if _read_regular_file_once(output_path) != payload:
            raise SystemExit("MM-005 evaluation repeatability protocol is stale")
        print(
            "MM-005 evaluation repeatability protocol verified: "
            f"{contract.sha256_bytes(payload)}"
        )
        return 0
    if os.path.lexists(output_path):
        raise FileExistsError(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    print(
        "MM-005 evaluation repeatability protocol written: "
        f"{contract.sha256_bytes(payload)}"
    )
    return 0


def build_protocol() -> dict[str, Any]:
    return contract.expected_preregistration(
        freeze_status="frozen",
        **protocol_inputs(),
    )


def protocol_inputs() -> dict[str, Any]:
    _validate_baseline_lineage()
    summary = result_validator.validate_repository(ROOT)
    if (
        summary.get("formal_gate_passed") is not True
        or summary.get("next_gate") != contract.PROTOCOL_GATE_ID
        or summary.get("repeatability_established") is not False
    ):
        raise RuntimeError("baseline result review does not authorize repeatability")
    baseline_inputs = {
        **baseline_builder.protocol_inputs(),
        "output_absent": True,
    }
    baseline_preregistration_payload = _read_regular_file_once(
        ROOT / str(contract.BASELINE_PREREGISTRATION_RECEIPT["path"])
    )
    baseline_artifact_payloads = {
        name: _read_regular_file_once(ROOT / str(receipt["path"]))
        for name, receipt in contract.BASELINE_ARTIFACTS.items()
    }
    baseline_review_payload = _read_regular_file_once(
        ROOT / str(contract.BASELINE_REVIEW_RECEIPT["path"])
    )
    contract.validate_baseline_payloads(
        baseline_preregistration_payload=baseline_preregistration_payload,
        baseline_artifact_payloads=baseline_artifact_payloads,
        baseline_review_payload=baseline_review_payload,
        baseline_inputs=baseline_inputs,
    )
    return {
        "source_receipts": source_receipts(),
        "baseline_preregistration_payload": baseline_preregistration_payload,
        "baseline_artifact_payloads": baseline_artifact_payloads,
        "baseline_review_payload": baseline_review_payload,
        "baseline_inputs": baseline_inputs,
        "output_absent": not os.path.lexists(ROOT / contract.RUN_OUTPUT_ROOT),
    }


def source_receipts() -> dict[str, dict[str, Any]]:
    return {
        name: _receipt(relative, _read_regular_file_once(ROOT / relative))
        for name, relative in sorted(contract.PROTOCOL_SOURCE_PATHS.items())
    }


def _validate_baseline_lineage() -> None:
    ancestor = subprocess.run(
        [
            "git",
            "merge-base",
            "--is-ancestor",
            contract.BASELINE_RESULT_MERGE_COMMIT,
            "HEAD",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    if ancestor.returncode != 0 or ancestor.stdout or ancestor.stderr:
        raise RuntimeError("baseline result merge is not an ancestor")
    paths = (
        str(contract.BASELINE_PREREGISTRATION_RECEIPT["path"]),
        *(str(item["path"]) for item in contract.BASELINE_ARTIFACTS.values()),
        str(contract.BASELINE_REVIEW_RECEIPT["path"]),
    )
    for relative in paths:
        frozen = subprocess.run(
            ["git", "show", f"{contract.BASELINE_RESULT_MERGE_COMMIT}:{relative}"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout
        current = _read_regular_file_once(ROOT / relative)
        if frozen != current:
            raise RuntimeError(f"baseline result changed after merge: {relative}")


def _receipt(path: str, payload: bytes) -> dict[str, Any]:
    return {
        "path": path,
        "bytes": len(payload),
        "sha256": contract.sha256_bytes(payload),
    }


def _read_regular_file_once(path: Path) -> bytes:
    resolved = path.resolve(strict=True)
    before = resolved.stat()
    if (
        resolved.is_symlink()
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
    ):
        raise RuntimeError(f"unsafe file: {path}")
    with resolved.open("rb") as handle:
        payload = handle.read()
        after_handle = os.fstat(handle.fileno())
    after = resolved.stat()
    signatures = {
        (
            item.st_dev,
            item.st_ino,
            item.st_size,
            item.st_mtime_ns,
            item.st_nlink,
        )
        for item in (before, after_handle, after)
    }
    if len(signatures) != 1:
        raise RuntimeError(f"file changed while reading: {path}")
    return payload


if __name__ == "__main__":
    raise SystemExit(main())
