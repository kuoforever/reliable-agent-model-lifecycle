"""Prepare, check, or execute frozen MM-005 Browser Research data generation."""

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
from pathlib import Path, PurePosixPath
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(ROOT))

from fullcycle_bridge import mm005_browser_research_data as data  # noqa: E402
from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_generation as contract,
)
from scripts import (  # noqa: E402
    prepare_mm005_browser_research_data_protocol as data_prepare,
)

SOURCE_PATHS = {
    "data_builder": "scripts/prepare_mm005_browser_research_data_protocol.py",
    "data_contract": "src/fullcycle_bridge/mm005_browser_research_data.py",
    "generation_contract": (
        "src/fullcycle_bridge/mm005_browser_research_generation.py"
    ),
    "generation_runner": "scripts/run_mm005_browser_research_generation.py",
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
            raise RuntimeError("MM-005 Browser Research generation protocol is stale")
        print(
            "MM-005 Browser Research generation protocol verified: "
            f"{contract.sha256_bytes(payload)}"
        )
        return 0
    _assert_execution_targets_absent()
    if output_path.exists():
        raise FileExistsError(output_path)
    output_path.write_bytes(payload)
    print(
        "MM-005 Browser Research generation protocol frozen: "
        f"{contract.sha256_bytes(payload)}"
    )
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
    exclusions = cast(
        Mapping[str, Sequence[str]],
        data_prepare.exclusion_registry(),
    )
    parent_binding = cast(Mapping[str, Any], data_protocol["parent_protocol"])
    expected_outputs = data.expected_output_payloads(str(parent_binding["sha256"]))
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
    persisted_outputs = _load_output_tree(set(expected_outputs))
    summary = contract.validate_evidence(
        persisted_evidence,
        protocol_freeze_commit=protocol_freeze_commit,
        protocol_payload=protocol_payload,
        source_receipts=source_receipts(),
        data_protocol_payload=data_payload,
        data_source_receipts=data_sources,
        parent_protocol_receipt=parent_receipt,
        output_payloads=persisted_outputs,
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
        if _path_entry_exists(ROOT / relative):
            raise FileExistsError(ROOT / relative)


def _materialize_output_root(payloads: Mapping[str, bytes]) -> None:
    output_root = ROOT / contract.OUTPUT_ROOT
    output_root_io = _io_path(output_root)
    if _path_entry_exists(output_root):
        raise FileExistsError(output_root)
    staging = output_root.parent / f".{output_root.name}.staging-{uuid.uuid4().hex}"
    staging_io = _io_path(staging)
    staging_io.mkdir(parents=False, exist_ok=False)
    try:
        for relative, payload in sorted(payloads.items()):
            relative_path = Path(relative)
            try:
                destination_suffix = relative_path.relative_to(contract.OUTPUT_ROOT)
            except ValueError as exc:
                raise RuntimeError(f"output path escapes fixed root: {relative}") from exc
            if destination_suffix.is_absolute() or ".." in destination_suffix.parts:
                raise RuntimeError(f"unsafe output path: {relative}")
            destination = _io_path(staging / destination_suffix)
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("xb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
        os.rename(staging_io, output_root_io)
    except BaseException:
        if staging_io.exists():
            shutil.rmtree(staging_io)
        raise


def _load_output_tree(expected_paths: set[str]) -> dict[str, bytes]:
    output_root = ROOT / contract.OUTPUT_ROOT
    _assert_safe_directory(output_root)
    output_root_io = _io_path(output_root)
    actual_paths: set[str] = set()
    actual_directories = {contract.OUTPUT_ROOT}
    for current, directories, filenames in os.walk(
        output_root_io, followlinks=False
    ):
        current_path = Path(current)
        for name in directories:
            directory = current_path / name
            _assert_safe_directory(directory)
            suffix = directory.relative_to(output_root_io).as_posix()
            actual_directories.add(f"{contract.OUTPUT_ROOT}/{suffix}")
        for name in filenames:
            path = current_path / name
            _assert_safe_regular_file(path)
            suffix = path.relative_to(output_root_io).as_posix()
            actual_paths.add(f"{contract.OUTPUT_ROOT}/{suffix}")
    expected_directories = _expected_output_directories(expected_paths)
    if actual_paths != expected_paths or actual_directories != expected_directories:
        raise RuntimeError("MM-005 Browser Research output tree mismatch")
    return {
        relative: _read_regular_file_once(ROOT / relative)
        for relative in sorted(actual_paths)
    }


def _write_evidence_atomically(payload: bytes) -> None:
    evidence_path = ROOT / contract.EVIDENCE_PATH
    evidence_path_io = _io_path(evidence_path)
    if _path_entry_exists(evidence_path):
        raise FileExistsError(evidence_path)
    _io_path(evidence_path.parent).mkdir(parents=True, exist_ok=True)
    staging = evidence_path.parent / f".{evidence_path.name}.staging-{uuid.uuid4().hex}"
    staging_io = _io_path(staging)
    try:
        with staging_io.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.rename(staging_io, evidence_path_io)
    except BaseException:
        if staging_io.exists():
            staging_io.unlink()
        raise


def _validate_freeze_commit(commit: str) -> None:
    if len(commit) != 40 or any(
        character not in "0123456789abcdef" for character in commit
    ):
        raise RuntimeError("protocol freeze commit must be lowercase 40-hex")
    branch = _git("branch", "--show-current")
    head = _git("rev-parse", "HEAD")
    origin = _git("rev-parse", "origin/master")
    if branch != "master" or head != origin or head != commit:
        raise RuntimeError("generation requires aligned merged master freeze commit")
    if not _git_is_ancestor(contract.DATA_PROTOCOL_MERGE_COMMIT, commit):
        raise RuntimeError("published data protocol is not an ancestor of freeze commit")
    frozen_paths = {
        contract.PROTOCOL_PATH,
        contract.DATA_PROTOCOL_PATH,
        *SOURCE_PATHS.values(),
    }
    for relative in sorted(frozen_paths):
        tracked = _git_show(commit, relative)
        if tracked != _read_regular_file_once(ROOT / relative):
            raise RuntimeError(f"freeze commit source differs: {relative}")
    published_data_protocol = _git_show(
        contract.DATA_PROTOCOL_MERGE_COMMIT,
        contract.DATA_PROTOCOL_PATH,
    )
    if published_data_protocol != _read_regular_file_once(
        ROOT / contract.DATA_PROTOCOL_PATH
    ):
        raise RuntimeError("published data protocol bytes differ from current protocol")


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def _git_is_ancestor(ancestor: str, descendant: str) -> bool:
    completed = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    return completed.returncode == 0


def _git_show(commit: str, relative: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{commit}:{relative}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout


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
    _assert_safe_regular_file(path)
    resolved = _io_path(path).resolve(strict=True)
    before = resolved.stat()
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


def _assert_safe_regular_file(path: Path) -> None:
    path_io = _io_path(path)
    try:
        value = path_io.lstat()
    except OSError as exc:
        raise RuntimeError(f"missing or unreadable file: {path}") from exc
    if (
        not stat.S_ISREG(value.st_mode)
        or path_io.is_symlink()
        or _is_reparse_point(value)
    ):
        raise RuntimeError(f"unsafe file: {path}")


def _assert_safe_directory(path: Path) -> None:
    path_io = _io_path(path)
    try:
        value = path_io.lstat()
    except OSError as exc:
        raise RuntimeError(f"missing or unreadable directory: {path}") from exc
    if (
        not stat.S_ISDIR(value.st_mode)
        or path_io.is_symlink()
        or _is_reparse_point(value)
    ):
        raise RuntimeError(f"unsafe directory: {path}")


def _is_reparse_point(value: os.stat_result) -> bool:
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(getattr(value, "st_file_attributes", 0) & reparse_flag)


def _path_entry_exists(path: Path) -> bool:
    try:
        _io_path(path).lstat()
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise RuntimeError(f"cannot determine path absence: {path}") from exc
    return True


def _expected_output_directories(expected_paths: set[str]) -> set[str]:
    root = PurePosixPath(contract.OUTPUT_ROOT)
    directories = {root.as_posix()}
    for relative in expected_paths:
        path = PurePosixPath(relative)
        if root not in path.parents:
            raise RuntimeError(f"expected output path escapes fixed root: {relative}")
        parent = path.parent
        while True:
            directories.add(parent.as_posix())
            if parent == root:
                break
            parent = parent.parent
    return directories


def _io_path(path: Path) -> Path:
    """Use an extended-length Windows path without changing logical receipts."""

    if os.name != "nt":
        return path
    absolute = os.path.abspath(path)
    if absolute.startswith("\\\\?\\"):
        return Path(absolute)
    if absolute.startswith("\\\\"):
        return Path("\\\\?\\UNC\\" + absolute[2:])
    return Path("\\\\?\\" + absolute)


if __name__ == "__main__":
    raise SystemExit(main())
