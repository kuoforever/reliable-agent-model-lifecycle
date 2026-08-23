"""Prepare, check, or execute frozen MM-005 synthetic data generation."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import subprocess
import sys
import uuid
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(ROOT))

from fullcycle_bridge import mm005_document_chart_pdf_data as data  # noqa: E402
from fullcycle_bridge import (  # noqa: E402
    mm005_document_chart_pdf_generation as contract,
)
from scripts import (  # noqa: E402
    prepare_mm005_document_chart_pdf_data_protocol as data_prepare,
)

SOURCE_PATHS = {
    "data_builder": "scripts/prepare_mm005_document_chart_pdf_data_protocol.py",
    "data_contract": "src/fullcycle_bridge/mm005_document_chart_pdf_data.py",
    "generation_contract": (
        "src/fullcycle_bridge/mm005_document_chart_pdf_generation.py"
    ),
    "generation_runner": "scripts/run_mm005_document_chart_pdf_generation.py",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("--freeze-status", choices=("draft", "frozen"), required=True)
    prepare.add_argument("--check", action="store_true")
    execute = subparsers.add_parser("execute")
    execute.add_argument("--protocol-freeze-commit", required=True)
    args = parser.parse_args(argv)
    if args.command == "prepare":
        return prepare_protocol(freeze_status=args.freeze_status, check=args.check)
    return execute_protocol(protocol_freeze_commit=args.protocol_freeze_commit)


def prepare_protocol(*, freeze_status: str, check: bool) -> int:
    protocol = expected_protocol(freeze_status=freeze_status)
    payload = contract.artifact_json_bytes(protocol)
    output_path = ROOT / contract.PROTOCOL_PATH
    if check:
        if _read_regular_file_once(output_path) != payload:
            raise RuntimeError("MM-005 generation protocol is stale")
        print(f"MM-005 generation protocol verified: {contract.sha256_bytes(payload)}")
        return 0
    if output_path.exists():
        raise FileExistsError(output_path)
    output_path.write_bytes(payload)
    print(f"MM-005 generation protocol frozen: {contract.sha256_bytes(payload)}")
    return 0


def expected_protocol(*, freeze_status: str) -> dict[str, Any]:
    data_protocol_payload, _, _, _ = data_protocol_context()
    return contract.expected_protocol(
        freeze_status=freeze_status,
        source_receipts=source_receipts(),
        data_protocol_payload=data_protocol_payload,
    )


def source_receipts() -> dict[str, dict[str, Any]]:
    return {
        name: _receipt(relative, _read_regular_file_once(ROOT / relative))
        for name, relative in sorted(SOURCE_PATHS.items())
    }


def data_protocol_context() -> tuple[
    bytes,
    dict[str, Any],
    dict[str, dict[str, Any]],
    dict[str, Any],
]:
    payload = _read_regular_file_once(ROOT / contract.DATA_PROTOCOL_PATH)
    value = _json_dict(payload, contract.DATA_PROTOCOL_PATH)
    data_sources = data_prepare.source_receipts()
    parent_receipt = data_prepare.parent_protocol_receipt()
    data.validate_preregistration(
        value,
        source_receipts=data_sources,
        parent_protocol_receipt=parent_receipt,
    )
    return payload, value, data_sources, parent_receipt


def execute_protocol(*, protocol_freeze_commit: str) -> int:
    _validate_freeze_commit(protocol_freeze_commit)
    _assert_execution_targets_absent()
    protocol_payload = _read_regular_file_once(ROOT / contract.PROTOCOL_PATH)
    protocol = _json_dict(protocol_payload, contract.PROTOCOL_PATH)
    data_payload, data_protocol, data_sources, parent_receipt = data_protocol_context()
    contract.validate_protocol(
        protocol,
        source_receipts=source_receipts(),
        data_protocol_payload=data_payload,
    )
    parent_protocol = _json_dict(
        _read_regular_file_once(ROOT / data.PARENT_PROTOCOL_PATH),
        data.PARENT_PROTOCOL_PATH,
    )
    exclusions = cast(
        Mapping[str, Sequence[str]],
        parent_protocol["exclusion_registry"],
    )
    parent_protocol_binding = cast(Mapping[str, Any], data_protocol["parent_protocol"])
    expected_outputs = data.expected_output_payloads(
        str(parent_protocol_binding["sha256"])
    )
    contract.validate_output_payloads(
        expected_outputs,
        protocol=protocol,
        data_protocol=data_protocol,
        exclusions=exclusions,
    )
    _materialize_output_root(expected_outputs)
    actual_outputs = _load_output_tree(set(expected_outputs))
    contract.validate_output_payloads(
        actual_outputs,
        protocol=protocol,
        data_protocol=data_protocol,
        exclusions=exclusions,
    )
    evidence = contract.build_evidence(
        protocol_freeze_commit=protocol_freeze_commit,
        protocol_payload=protocol_payload,
        source_receipts=source_receipts(),
        data_protocol_payload=data_payload,
        data_source_receipts=data_sources,
        parent_protocol_receipt=parent_receipt,
        output_payloads=actual_outputs,
        exclusions=exclusions,
    )
    evidence_payload = contract.artifact_json_bytes(evidence)
    _write_evidence_atomically(evidence_payload)
    persisted_evidence_payload = _read_regular_file_once(ROOT / contract.EVIDENCE_PATH)
    persisted_evidence = _json_dict(
        persisted_evidence_payload, contract.EVIDENCE_PATH
    )
    summary = contract.validate_evidence(
        persisted_evidence,
        protocol_freeze_commit=protocol_freeze_commit,
        protocol_payload=protocol_payload,
        source_receipts=source_receipts(),
        data_protocol_payload=data_payload,
        data_source_receipts=data_sources,
        parent_protocol_receipt=parent_receipt,
        output_payloads=actual_outputs,
        exclusions=exclusions,
    )
    print(json.dumps(summary.to_dict(), sort_keys=True))
    return 0


def load_tracked_outputs() -> dict[str, bytes]:
    _, data_protocol, _, _ = data_protocol_context()
    planned = cast(Mapping[str, Any], data_protocol["planned_outputs"])
    return _load_output_tree(set(planned))


def _assert_execution_targets_absent() -> None:
    for relative in (contract.OUTPUT_ROOT, contract.EVIDENCE_PATH):
        if (ROOT / relative).exists():
            raise FileExistsError(ROOT / relative)


def _materialize_output_root(payloads: Mapping[str, bytes]) -> None:
    output_root = ROOT / contract.OUTPUT_ROOT
    if output_root.exists():
        raise FileExistsError(output_root)
    staging = output_root.parent / f".{output_root.name}.staging-{uuid.uuid4().hex}"
    staging.mkdir(parents=False, exist_ok=False)
    try:
        for relative, payload in sorted(payloads.items()):
            destination = staging / Path(relative).relative_to(contract.OUTPUT_ROOT)
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("xb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
        os.rename(staging, output_root)
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def _load_output_tree(expected_paths: set[str]) -> dict[str, bytes]:
    output_root = ROOT / contract.OUTPUT_ROOT
    if output_root.is_symlink() or not output_root.is_dir():
        raise RuntimeError("MM-005 output root is not a safe directory")
    actual_paths: set[str] = set()
    for path in output_root.rglob("*"):
        if path.is_symlink():
            raise RuntimeError(f"unsafe output path: {path}")
        if path.is_file():
            actual_paths.add(path.relative_to(ROOT).as_posix())
    if actual_paths != expected_paths:
        raise RuntimeError("MM-005 output tree mismatch")
    return {
        relative: _read_regular_file_once(ROOT / relative)
        for relative in sorted(actual_paths)
    }


def _write_evidence_atomically(payload: bytes) -> None:
    evidence_path = ROOT / contract.EVIDENCE_PATH
    if evidence_path.exists():
        raise FileExistsError(evidence_path)
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    staging = evidence_path.parent / f".{evidence_path.name}.staging-{uuid.uuid4().hex}"
    try:
        with staging.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.rename(staging, evidence_path)
    except BaseException:
        if staging.exists():
            staging.unlink()
        raise


def _validate_freeze_commit(commit: str) -> None:
    if len(commit) != 40 or any(character not in "0123456789abcdef" for character in commit):
        raise RuntimeError("protocol freeze commit must be lowercase 40-hex")
    branch = _git("branch", "--show-current")
    head = _git("rev-parse", "HEAD")
    origin = _git("rev-parse", "origin/master")
    if branch != "master" or head != origin or head != commit:
        raise RuntimeError("generation requires aligned merged master freeze commit")
    frozen_paths = {
        contract.PROTOCOL_PATH,
        contract.DATA_PROTOCOL_PATH,
        *SOURCE_PATHS.values(),
    }
    for relative in sorted(frozen_paths):
        tracked = subprocess.run(
            ["git", "show", f"{commit}:{relative}"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout
        if tracked != _read_regular_file_once(ROOT / relative):
            raise RuntimeError(f"freeze commit source differs: {relative}")


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def _receipt(path: str, payload: bytes) -> dict[str, Any]:
    return {"path": path, "bytes": len(payload), "sha256": contract.sha256_bytes(payload)}


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
