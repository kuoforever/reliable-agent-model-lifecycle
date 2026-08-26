"""Build or check the MM-005 Document/Chart/PDF model-evaluation protocol."""

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
    mm004_hard_negative_model_evaluation as candidate_protocol,
)
from fullcycle_bridge import (  # noqa: E402
    mm005_document_chart_pdf_adapter_verifier_implementation as implementation,
)
from fullcycle_bridge import (  # noqa: E402
    mm005_document_chart_pdf_adapter_verifier_protocol as adapter_protocol,
)
from fullcycle_bridge import (  # noqa: E402
    mm005_document_chart_pdf_model_evaluation as contract,
)
from scripts import (  # noqa: E402
    prepare_mm005_document_chart_pdf_adapter_verifier_implementation as implementation_prepare,
)
from scripts import (  # noqa: E402
    validate_mm004_hard_negative_model_evaluation_result as candidate_validator,
)

SOURCE_PATHS = contract.PROTOCOL_SOURCE_PATHS
IMPLEMENTATION_MERGED_PATHS = (
    implementation.EVIDENCE_PATH,
    "src/fullcycle_bridge/mm005_document_chart_pdf_adapter_verifier.py",
    (
        "src/fullcycle_bridge/"
        "mm005_document_chart_pdf_adapter_verifier_implementation.py"
    ),
    adapter_protocol.PROTOCOL_PATH,
)
CANDIDATE_MERGED_PATHS = (
    candidate_protocol.PREREGISTRATION_PATH,
    "baseline/mm004-hard-negative-model-eval-v2-evidence.json",
    "baseline/mm004-hard-negative-model-eval-v2-result-review.json",
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
            raise SystemExit("MM-005 model-evaluation protocol is stale")
        print(
            "MM-005 model-evaluation protocol verified: "
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
    print(f"MM-005 model-evaluation protocol written: {contract.sha256_bytes(payload)}")
    return 0


def build_protocol() -> dict[str, Any]:
    return contract.expected_preregistration(
        freeze_status="frozen",
        **protocol_inputs(),
    )


def protocol_inputs() -> dict[str, Any]:
    _validate_merged_lineage()
    implementation_inputs = implementation_prepare.implementation_inputs()
    implementation_expected = implementation.expected_evidence(**implementation_inputs)
    implementation_payload = _read_regular_file_once(
        ROOT / implementation.EVIDENCE_PATH
    )
    if implementation.artifact_json_bytes(implementation_expected) != (
        implementation_payload
    ):
        raise RuntimeError("Adapter/Verifier implementation evidence is stale")

    candidate_review_expected, _summary = candidate_validator.build_repository_review()
    candidate_preregistration_payload = _read_regular_file_once(
        ROOT / candidate_protocol.PREREGISTRATION_PATH
    )
    candidate_result_review_path = (
        "baseline/mm004-hard-negative-model-eval-v2-result-review.json"
    )
    candidate_result_review_payload = _read_regular_file_once(
        ROOT / candidate_result_review_path
    )
    if candidate_protocol.artifact_json_bytes(candidate_review_expected) != (
        candidate_result_review_payload
    ):
        raise RuntimeError("candidate result review is stale")
    candidate_evidence_payload = _read_regular_file_once(
        ROOT / "baseline/mm004-hard-negative-model-eval-v2-evidence.json"
    )

    output_payloads = {
        str(path): bytes(payload)
        for path, payload in implementation_inputs["output_payloads"].items()
    }
    records, _image_receipts, _dataset_receipts = adapter_protocol.dataset_context(
        output_payloads
    )
    return {
        "source_receipts": source_receipts(),
        "implementation_evidence_payload": implementation_payload,
        "implementation_evidence_expected": implementation_expected,
        "candidate_preregistration_payload": candidate_preregistration_payload,
        "candidate_preregistration_expected": (
            contract.parse_strict_json_bytes(
                candidate_preregistration_payload,
                location="$.candidate_preregistration",
            )
        ),
        "candidate_result_review_payload": candidate_result_review_payload,
        "candidate_result_review_expected": candidate_review_expected,
        "candidate_evidence_payload": candidate_evidence_payload,
        "candidate_evidence_expected": contract.parse_strict_json_bytes(
            candidate_evidence_payload, location="$.candidate_evidence"
        ),
        "dataset_output_receipts": {
            path: _receipt(path, payload)
            for path, payload in sorted(output_payloads.items())
        },
        "records": records,
        "image_payloads": output_payloads,
        "output_absent": not os.path.lexists(ROOT / contract.RUN_OUTPUT_ROOT),
    }


def source_receipts() -> dict[str, dict[str, Any]]:
    return {
        name: _receipt(relative, _read_regular_file_once(ROOT / relative))
        for name, relative in sorted(SOURCE_PATHS.items())
    }


def _validate_merged_lineage() -> None:
    _validate_merged_paths(
        contract.IMPLEMENTATION_MERGE_COMMIT,
        IMPLEMENTATION_MERGED_PATHS,
        "Adapter/Verifier implementation",
    )
    _validate_merged_paths(
        contract.CANDIDATE_RESULT_REVIEW_MERGE_COMMIT,
        CANDIDATE_MERGED_PATHS,
        "candidate result review",
    )


def _validate_merged_paths(commit: str, paths: tuple[str, ...], label: str) -> None:
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    if ancestor.returncode != 0:
        raise RuntimeError(f"{label} merge is not an ancestor")
    for relative in paths:
        frozen = subprocess.run(
            ["git", "show", f"{commit}:{relative}"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout
        current = _read_regular_file_once(ROOT / relative)
        if frozen != current:
            raise RuntimeError(f"{label} changed after merge: {relative}")


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
