"""Build or check the MM-005 Browser eval v2 static investigation protocol."""

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
    mm005_browser_research_model_evaluation_failure_classification_v2 as failure,
)
from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_model_evaluation_generation_failure_investigation as contract,
)
from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_model_evaluation_protocol_v2 as v2,
)
from scripts import (  # noqa: E402
    prepare_mm005_browser_research_model_evaluation_v2 as prepare_v2,
)

MAX_BOUND_FILE_BYTES = 64 * 1024 * 1024
CLASSIFICATION_MERGED_PATHS = (
    v2.PREREGISTRATION_PATH,
    failure.TRACKED_ATTEMPT_OWNER_PATH,
    failure.TRACKED_PROGRESS_PATH,
    failure.TRACKED_FAILURE_PATH,
    failure.ARTIFACT_PATH,
    (
        "src/fullcycle_bridge/"
        "mm005_browser_research_model_evaluation_failure_classification_v2.py"
    ),
    "scripts/classify_mm005_browser_research_model_evaluation_failure_v2.py",
    "tests/test_mm005_browser_research_model_evaluation_failure_classification_v2.py",
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
            raise SystemExit(
                "MM-005 Browser generation-failure investigation protocol is stale"
            )
    else:
        if os.path.lexists(output_path):
            raise FileExistsError(output_path)
        if os.path.lexists(ROOT / contract.RESULT_PATH):
            raise RuntimeError(
                "investigation result already exists before protocol freeze"
            )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())

    print(
        contract.artifact_json_bytes(
            {
                "gate_id": protocol["gate_id"],
                "investigation_id": protocol["investigation_id"],
                "next_gate": protocol["next_gate"],
                "protocol_sha256": contract.sha256_bytes(payload),
                "valid": True,
            }
        )
        .decode("utf-8")
        .rstrip()
    )
    return 0


def build_protocol() -> dict[str, Any]:
    return contract.expected_preregistration(
        freeze_status="frozen",
        output_absent=True,
        **protocol_inputs(),
    )


def protocol_inputs() -> dict[str, Any]:
    """Load independent tracked inputs without model, processor, CUDA, or network."""

    _validate_published_classification_lineage()
    failure_context = failure.load_tracked_failure_context(ROOT)
    classification_payload = _read_repository_file(failure.ARTIFACT_PATH)
    classification = contract.parse_strict_json_bytes(
        classification_payload, location="$.classification"
    )
    failure.validate_failure_classification(ROOT, classification)
    if contract.artifact_json_bytes(classification) != classification_payload:
        raise RuntimeError("v2 failure classification is not canonical")

    execution_inputs = prepare_v2.execution_inputs()
    preregistration_payload = _bytes_value(
        failure_context.get("preregistration_payload"),
        "$.failure_context.preregistration_payload",
    )
    preregistration = _mapping(
        failure_context.get("preregistration"), "$.failure_context.preregistration"
    )
    records = execution_inputs.get("records")
    artifact_payloads = execution_inputs.get("artifact_payloads")
    if not isinstance(records, list):
        raise RuntimeError("frozen evaluation records are not an array")
    if not isinstance(artifact_payloads, Mapping):
        raise RuntimeError("frozen artifact payloads are not an object")

    return {
        "v2_preregistration": preregistration,
        "v2_preregistration_payload": preregistration_payload,
        "attempt_owner_payload": _bytes_value(
            failure_context.get("owner_payload"), "$.failure_context.owner_payload"
        ),
        "progress_payload": _bytes_value(
            failure_context.get("progress_payload"),
            "$.failure_context.progress_payload",
        ),
        "failure_payload": _bytes_value(
            failure_context.get("failure_payload"),
            "$.failure_context.failure_payload",
        ),
        "classification": classification,
        "classification_payload": classification_payload,
        "source_receipts": source_receipts(),
        "records": records,
        "artifact_payloads": artifact_payloads,
    }


def source_receipts() -> dict[str, dict[str, Any]]:
    return {
        name: _receipt(path, _read_repository_file(path))
        for name, path in sorted(contract.PROTOCOL_SOURCE_PATHS.items())
    }


def _validate_published_classification_lineage() -> None:
    commit = contract.CLASSIFICATION_MERGE_COMMIT
    if re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        raise RuntimeError("unsafe classification merge commit")
    try:
        ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
            cwd=ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError("unable to verify classification merge ancestry") from exc
    if ancestor.returncode != 0:
        raise RuntimeError("classification merge is not an ancestor of HEAD")
    for relative in CLASSIFICATION_MERGED_PATHS:
        frozen = _git_blob_bytes(commit, relative)
        current = _read_repository_file(relative)
        if frozen != current:
            raise RuntimeError(
                f"classification lineage changed after clean merge: {relative}"
            )


def _git_blob_bytes(commit: str, relative: str) -> bytes:
    _validate_repository_relative_path(relative)
    if re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        raise RuntimeError("unsafe Git blob commit")
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
        raise RuntimeError("unable to read classification Git blob") from exc
    if completed.returncode != 0 or len(completed.stdout) > MAX_BOUND_FILE_BYTES:
        raise RuntimeError("unable to read classification Git blob")
    return completed.stdout


def _read_repository_file(relative: str) -> bytes:
    _validate_repository_relative_path(relative)
    return _read_regular_file_once(ROOT / PurePosixPath(relative))


def _validate_repository_relative_path(relative: str) -> None:
    path = PurePosixPath(relative)
    if (
        not relative
        or "\\" in relative
        or path.is_absolute()
        or path.as_posix() != relative
        or ".." in path.parts
        or "." in path.parts
    ):
        raise RuntimeError("unsafe repository-relative path")


def _read_regular_file_once(path: Path) -> bytes:
    absolute = Path(os.path.abspath(path))
    try:
        before = absolute.lstat()
        resolved = absolute.resolve(strict=True)
    except OSError as exc:
        raise RuntimeError(f"unable to inspect bound file: {path}") from exc
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    if (
        resolved != absolute
        or absolute.is_symlink()
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or before.st_size > MAX_BOUND_FILE_BYTES
        or bool(getattr(before, "st_file_attributes", 0) & reparse_flag)
    ):
        raise RuntimeError(f"unsafe bound file: {path}")
    try:
        with resolved.open("rb") as handle:
            payload = handle.read(MAX_BOUND_FILE_BYTES + 1)
            after_handle = os.fstat(handle.fileno())
        after = resolved.stat()
    except OSError as exc:
        raise RuntimeError(f"unable to read bound file: {path}") from exc
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
    if len(payload) > MAX_BOUND_FILE_BYTES or len(signatures) != 1:
        raise RuntimeError(f"bound file changed while reading: {path}")
    return payload


def _mapping(value: object, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise RuntimeError(f"expected object: {location}")
    return value


def _bytes_value(value: object, location: str) -> bytes:
    if not isinstance(value, bytes):
        raise RuntimeError(f"expected bytes: {location}")
    return value


def _receipt(path: str, payload: bytes) -> dict[str, Any]:
    return {
        "path": path,
        "bytes": len(payload),
        "sha256": contract.sha256_bytes(payload),
    }


if __name__ == "__main__":
    raise SystemExit(main())
