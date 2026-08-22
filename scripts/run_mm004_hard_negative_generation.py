"""Prepare, check, or execute the frozen MM-004 generation protocol."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(ROOT))

from fullcycle_bridge import mm004_hard_negative_generation as contract  # noqa: E402
from fullcycle_bridge import multimodal_hard_negative as parent_contract  # noqa: E402
from scripts import (  # noqa: E402
    prepare_mm004_multimodal_hard_negative_protocol as parent_prepare,
)

SOURCE_PATHS = {
    "parent_contract": "src/fullcycle_bridge/multimodal_hard_negative.py",
    "generation_contract": "src/fullcycle_bridge/mm004_hard_negative_generation.py",
    "generation_runner": "scripts/run_mm004_hard_negative_generation.py",
    "parent_prepare": "scripts/prepare_mm004_multimodal_hard_negative_protocol.py",
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
    preregistration = expected_preregistration(freeze_status=freeze_status)
    payload = contract.artifact_json_bytes(preregistration)
    output_path = ROOT / contract.PREREGISTRATION_PATH
    if check:
        if _read_regular_file_once(output_path) != payload:
            raise RuntimeError("MM-004 generation preregistration is stale")
        print(f"MM-004 generation protocol verified: {contract.sha256_bytes(payload)}")
        return 0
    if output_path.exists():
        raise FileExistsError(output_path)
    output_path.write_bytes(payload)
    print(f"MM-004 generation protocol frozen: {contract.sha256_bytes(payload)}")
    return 0


def expected_preregistration(*, freeze_status: str) -> dict[str, Any]:
    return contract.expected_preregistration(
        freeze_status=freeze_status,
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
    parent = json.loads(payload)
    expected = parent_prepare.build_protocol()
    if parent != expected or parent_contract.canonical_json_bytes(expected) != payload:
        raise RuntimeError("parent MM-004 protocol drift")
    return _receipt(path, payload)


def execute_protocol(*, protocol_freeze_commit: str) -> int:
    _validate_freeze_commit(protocol_freeze_commit)
    preregistration_path = ROOT / contract.PREREGISTRATION_PATH
    preregistration_payload = _read_regular_file_once(preregistration_path)
    preregistration = json.loads(preregistration_payload)
    contract.validate_preregistration(
        preregistration,
        source_receipts=source_receipts(),
        parent_protocol_receipt=parent_protocol_receipt(),
    )
    parent_protocol = json.loads(
        _read_regular_file_once(ROOT / contract.PARENT_PROTOCOL_PATH)
    )
    exclusions = parent_protocol["exclusion_registry"]
    output_payloads = contract.expected_output_payloads(
        preregistration["parent_protocol"]["sha256"]
    )
    contract.validate_output_payloads(
        output_payloads,
        preregistration=preregistration,
        exclusions=exclusions,
    )
    _materialize_output_root(output_payloads)
    evidence = contract.build_evidence(
        protocol_freeze_commit=protocol_freeze_commit,
        preregistration_payload=preregistration_payload,
        output_payloads=output_payloads,
        exclusions=exclusions,
    )
    evidence_path = ROOT / contract.EVIDENCE_PATH
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    with evidence_path.open("xb") as handle:
        handle.write(contract.artifact_json_bytes(evidence))
        handle.flush()
        os.fsync(handle.fileno())
    print(json.dumps(evidence["summary"], sort_keys=True))
    return 0


def load_tracked_outputs() -> dict[str, bytes]:
    preregistration = json.loads(
        _read_regular_file_once(ROOT / contract.PREREGISTRATION_PATH)
    )
    return {
        path: _read_regular_file_once(ROOT / path)
        for path in preregistration["planned_outputs"]
    }


def _materialize_output_root(payloads: dict[str, bytes]) -> None:
    output_root = ROOT / contract.OUTPUT_ROOT
    if output_root.exists():
        raise FileExistsError(output_root)
    staging = output_root.parent / f".{output_root.name}.staging-{uuid.uuid4().hex}"
    staging.mkdir(parents=False, exist_ok=False)
    try:
        for relative, payload in payloads.items():
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


def _validate_freeze_commit(commit: str) -> None:
    if len(commit) != 40 or any(character not in "0123456789abcdef" for character in commit):
        raise RuntimeError("protocol freeze commit must be lowercase 40-hex")
    branch = _git("branch", "--show-current")
    head = _git("rev-parse", "HEAD")
    origin = _git("rev-parse", "origin/master")
    if branch != "master" or head != origin or head != commit:
        raise RuntimeError("generation requires aligned merged master freeze commit")
    for relative in [contract.PREREGISTRATION_PATH, *SOURCE_PATHS.values()]:
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
