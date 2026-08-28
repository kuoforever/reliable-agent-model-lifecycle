"""Build or check the MM-005 Browser Research recovery protocol v2."""

from __future__ import annotations

import argparse
import os
import re
import stat
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(ROOT))

from fullcycle_bridge import (  # noqa: E402
    mm004_hard_negative_model_evaluation as candidate_protocol,
)
from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_adapter_verifier_implementation as implementation,
)
from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_adapter_verifier_protocol as adapter_protocol,
)
from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_model_evaluation as v1,
)
from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_model_evaluation_failure_classification as failure,
)
from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_model_evaluation_protocol_v2 as contract,
)

SOURCE_PATHS = contract.PROTOCOL_SOURCE_PATHS
MAX_BOUND_FILE_BYTES = 64 * 1024 * 1024
IMPLEMENTATION_MERGED_PATHS = (
    implementation.EVIDENCE_PATH,
    "src/fullcycle_bridge/mm005_browser_research_adapter_verifier.py",
    ("src/fullcycle_bridge/mm005_browser_research_adapter_verifier_implementation.py"),
    adapter_protocol.PROTOCOL_PATH,
)
CANDIDATE_MERGED_PATHS = (
    candidate_protocol.PREREGISTRATION_PATH,
    "baseline/mm004-hard-negative-model-eval-v2-evidence.json",
    "baseline/mm004-hard-negative-model-eval-v2-result-review.json",
)
CLASSIFICATION_MERGED_PATHS = (
    v1.PREREGISTRATION_PATH,
    failure.TRACKED_ATTEMPT_OWNER_PATH,
    failure.ARTIFACT_PATH,
    (
        "src/fullcycle_bridge/"
        "mm005_browser_research_model_evaluation_failure_classification.py"
    ),
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
            raise SystemExit("MM-005 Browser Research recovery protocol v2 is stale")
        print(
            "MM-005 Browser Research recovery protocol v2 verified: "
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
        "MM-005 Browser Research recovery protocol v2 written: "
        f"{contract.sha256_bytes(payload)}"
    )
    return 0


def build_protocol() -> dict[str, Any]:
    return contract.expected_preregistration(
        freeze_status="frozen",
        **protocol_inputs(),
    )


def protocol_inputs(*, freeze_output_absent: bool | None = None) -> dict[str, Any]:
    _validate_published_classification_lineage()
    v1_preregistration_payload = _read_regular_file_once(ROOT / v1.PREREGISTRATION_PATH)
    v1_attempt_owner_payload = _read_regular_file_once(
        ROOT / failure.TRACKED_ATTEMPT_OWNER_PATH
    )
    v1_failure_classification_payload = _read_regular_file_once(
        ROOT / failure.ARTIFACT_PATH
    )
    v1_preregistration = contract.parse_strict_json_bytes(
        v1_preregistration_payload, location="$.v1_preregistration"
    )
    contract.validate_recovery_lineage_payloads(
        v1_preregistration_payload=v1_preregistration_payload,
        v1_attempt_owner_payload=v1_attempt_owner_payload,
        v1_failure_classification_payload=v1_failure_classification_payload,
    )
    receipts = source_receipts(v1_preregistration)
    return {
        "v1_preregistration": v1_preregistration,
        "source_receipts": receipts,
        "v1_preregistration_payload": v1_preregistration_payload,
        "v1_attempt_owner_payload": v1_attempt_owner_payload,
        "v1_failure_classification_payload": v1_failure_classification_payload,
        "output_absent": (
            not os.path.lexists(ROOT / contract.RUN_OUTPUT_ROOT)
            if freeze_output_absent is None
            else freeze_output_absent
        ),
    }


def execution_inputs() -> dict[str, Any]:
    """Rebuild the unchanged v1 inputs through the long-path-safe blob reader."""

    _validate_scientific_lineage()
    payload = _read_regular_file_once(ROOT / v1.PREREGISTRATION_PATH)
    preregistration = contract.parse_strict_json_bytes(
        payload, location="$.v1_preregistration"
    )
    source_lineage = _mapping(
        preregistration.get("source_lineage"), "$.v1_preregistration.source_lineage"
    )
    implementation_payload = _read_bound_payload(
        implementation.EVIDENCE_PATH,
        source_lineage.get("adapter_verifier_implementation_evidence"),
    )
    candidate_preregistration_payload = _read_bound_payload(
        candidate_protocol.PREREGISTRATION_PATH,
        source_lineage.get("candidate_preregistration"),
    )
    candidate_result_review_payload = _read_bound_payload(
        "baseline/mm004-hard-negative-model-eval-v2-result-review.json",
        source_lineage.get("candidate_result_review"),
    )
    candidate_evidence_payload = _read_bound_payload(
        "baseline/mm004-hard-negative-model-eval-v2-evidence.json",
        source_lineage.get("candidate_evidence"),
    )
    dataset_receipts = _receipt_mapping(
        source_lineage.get("dataset_outputs"),
        "$.v1_preregistration.source_lineage.dataset_outputs",
    )
    output_payloads = {
        path: _read_bound_payload(path, receipt)
        for path, receipt in sorted(dataset_receipts.items())
    }
    records, _source_bindings, _observed_dataset_receipts = (
        adapter_protocol.dataset_context(output_payloads)
    )
    inputs = {
        "source_receipts": _v1_source_receipts(preregistration),
        "implementation_evidence_payload": implementation_payload,
        "implementation_evidence_expected": contract.parse_strict_json_bytes(
            implementation_payload, location="$.implementation_evidence"
        ),
        "candidate_preregistration_payload": candidate_preregistration_payload,
        "candidate_preregistration_expected": contract.parse_strict_json_bytes(
            candidate_preregistration_payload, location="$.candidate_preregistration"
        ),
        "candidate_result_review_payload": candidate_result_review_payload,
        "candidate_result_review_expected": contract.parse_strict_json_bytes(
            candidate_result_review_payload, location="$.candidate_result_review"
        ),
        "candidate_evidence_payload": candidate_evidence_payload,
        "candidate_evidence_expected": contract.parse_strict_json_bytes(
            candidate_evidence_payload, location="$.candidate_evidence"
        ),
        "dataset_output_receipts": dataset_receipts,
        "records": records,
        "artifact_payloads": output_payloads,
        "output_absent": True,
    }
    v1.validate_preregistration(preregistration, **inputs)
    if v1.artifact_json_bytes(preregistration) != payload:
        raise RuntimeError("v1 model-evaluation preregistration is not canonical")
    return inputs


def _v1_source_receipts(
    preregistration: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    expected = _receipt_mapping(
        preregistration.get("source_receipts"),
        "$.v1_preregistration.source_receipts",
    )
    observed = {
        name: _receipt(path, _read_regular_file_once(ROOT / path))
        for name, path in sorted(v1.PROTOCOL_SOURCE_PATHS.items())
    }
    if observed != expected:
        raise RuntimeError("v1 model-evaluation source closure changed")
    return observed


def source_receipts(
    v1_preregistration: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    raw_v1_receipts = v1_preregistration.get("source_receipts")
    if not isinstance(raw_v1_receipts, Mapping):
        raise RuntimeError("v1 source receipts are not an object")
    result: dict[str, dict[str, Any]] = {}
    for name, relative in sorted(SOURCE_PATHS.items()):
        payload = _read_regular_file_once(ROOT / relative)
        receipt = _receipt(relative, payload)
        if name in contract.V1_PROTOCOL_SOURCE_KEYS:
            expected = raw_v1_receipts.get(name)
            if not isinstance(expected, Mapping) or dict(expected) != receipt:
                raise RuntimeError(f"v1 protocol source changed: {relative}")
        result[name] = receipt
    return result


def _validate_published_classification_lineage() -> None:
    ancestor = subprocess.run(
        [
            "git",
            "merge-base",
            "--is-ancestor",
            contract.CLASSIFICATION_MERGE_COMMIT,
            "HEAD",
        ],
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if ancestor.returncode != 0 or ancestor.stderr:
        raise RuntimeError("failure-classification merge is not an ancestor")
    for relative in CLASSIFICATION_MERGED_PATHS:
        frozen = _git_blob_bytes(contract.CLASSIFICATION_MERGE_COMMIT, relative)
        current = _read_regular_file_once(ROOT / relative)
        if frozen != current:
            raise RuntimeError(
                f"failure-classification lineage changed after merge: {relative}"
            )


def _validate_scientific_lineage() -> None:
    _validate_merged_paths(
        v1.IMPLEMENTATION_MERGE_COMMIT,
        IMPLEMENTATION_MERGED_PATHS,
        "Adapter/Verifier implementation",
    )
    _validate_merged_paths(
        v1.CANDIDATE_RESULT_REVIEW_MERGE_COMMIT,
        CANDIDATE_MERGED_PATHS,
        "candidate result review",
    )


def _validate_merged_paths(commit: str, paths: tuple[str, ...], label: str) -> None:
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
    )
    if ancestor.returncode != 0:
        raise RuntimeError(f"{label} merge is not an ancestor")
    for relative in paths:
        frozen = _git_blob_bytes(commit, relative)
        current = _read_regular_file_once(ROOT / relative)
        if frozen != current:
            raise RuntimeError(f"{label} changed after merge: {relative}")


def _git_blob_bytes(commit: str, relative: str) -> bytes:
    path = PurePosixPath(relative)
    if (
        re.fullmatch(r"[0-9a-f]{40}", commit) is None
        or not relative
        or "\\" in relative
        or path.is_absolute()
        or ".." in path.parts
    ):
        raise RuntimeError("unsafe Git blob identity")
    try:
        completed = subprocess.run(
            ["git", "cat-file", "blob", f"{commit}:{relative}"],
            cwd=ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError("unable to read merged Git blob") from exc
    if completed.returncode != 0 or len(completed.stdout) > MAX_BOUND_FILE_BYTES:
        raise RuntimeError("unable to read merged Git blob")
    return completed.stdout


def _read_bound_payload(path: str, receipt: object) -> bytes:
    expected = _receipt_value(receipt, f"$.receipt.{path}")
    if expected["path"] != path:
        raise RuntimeError("bound artifact path differs")
    payload = _read_regular_file_once(ROOT / path)
    if _receipt(path, payload) != expected:
        raise RuntimeError(f"bound artifact receipt differs: {path}")
    return payload


def _receipt_mapping(value: object, location: str) -> dict[str, dict[str, Any]]:
    mapping = _mapping(value, location)
    result: dict[str, dict[str, Any]] = {}
    for name, receipt in mapping.items():
        if not isinstance(name, str):
            raise RuntimeError(f"receipt key is not text: {location}")
        result[name] = _receipt_value(receipt, f"{location}.{name}")
    return result


def _receipt_value(value: object, location: str) -> dict[str, Any]:
    receipt = _mapping(value, location)
    if (
        set(receipt) != {"path", "bytes", "sha256"}
        or not isinstance(receipt.get("path"), str)
        or not isinstance(receipt.get("bytes"), int)
        or isinstance(receipt.get("bytes"), bool)
        or not isinstance(receipt.get("sha256"), str)
    ):
        raise RuntimeError(f"invalid receipt: {location}")
    return dict(receipt)


def _mapping(value: object, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or not all(isinstance(key, str) for key in value):
        raise RuntimeError(f"expected object: {location}")
    return value


def _receipt(path: str, payload: bytes) -> dict[str, Any]:
    return {
        "path": path,
        "bytes": len(payload),
        "sha256": contract.sha256_bytes(payload),
    }


def _read_regular_file_once(path: Path) -> bytes:
    absolute = Path(os.path.abspath(path))
    before = absolute.lstat()
    resolved = absolute.resolve(strict=True)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    if (
        resolved != absolute
        or absolute.is_symlink()
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or bool(getattr(before, "st_file_attributes", 0) & reparse_flag)
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
