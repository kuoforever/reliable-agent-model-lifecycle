"""Build or check the MM-005 generation-diagnostic execution authority."""

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
    mm005_browser_research_model_evaluation_generation_failure_diagnostic as protocol,
)
from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_model_evaluation_generation_failure_diagnostic_result as contract,
)
from scripts import (  # noqa: E402
    run_mm005_browser_research_model_evaluation_generation_failure_diagnostic_v1 as runner,
)

IMPLEMENTATION_FREEZE_COMMIT = "7da39396c951a9248fe49c1bd69080923b827fa1"
V2_PREREGISTRATION_PATH = (
    "configs/mm005_browser_research_model_evaluation_protocol_v2.json"
)
MAX_BOUND_FILE_BYTES = 64 * 1024 * 1024


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    authority, snapshot = _capture_authority()
    payload = contract.artifact_json_bytes(authority)
    output_path = ROOT / contract.EXECUTION_AUTHORITY_PATH
    if args.check:
        if _read_regular_file_once(output_path) != payload:
            raise SystemExit("MM-005 diagnostic execution authority is stale")
        _revalidate_authority_inputs(snapshot)
        if _read_regular_file_once(output_path) != payload:
            raise RuntimeError("diagnostic execution authority changed during check")
    else:
        if os.path.lexists(output_path):
            raise FileExistsError(output_path)
        _revalidate_authority_inputs(snapshot)
        _require_safe_parent_chain(contract.EXECUTION_AUTHORITY_PATH)
        if os.path.lexists(output_path):
            raise FileExistsError(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())

    print(
        contract.artifact_json_bytes(
            {
                "authority_frozen": True,
                "authority_sha256": contract.sha256_bytes(payload),
                "diagnostic_attempt_consumed": False,
                "diagnostic_executed": False,
                "gate_id": contract.EXECUTION_AUTHORITY_GATE_ID,
                "implementation_freeze_commit": IMPLEMENTATION_FREEZE_COMMIT,
                "next_gate": contract.EXECUTION_GATE_ID,
                "valid": True,
            }
        )
        .decode("utf-8")
        .rstrip()
    )
    return 0


def build_authority() -> dict[str, Any]:
    authority, snapshot = _capture_authority()
    _revalidate_authority_inputs(snapshot)
    return authority


def authority_inputs() -> dict[str, Any]:
    authority, snapshot = _capture_authority()
    _revalidate_authority_inputs(snapshot)
    return {
        "critical_execution_dependency_receipts": authority[
            "critical_execution_dependency_receipts"
        ],
        "expected_environment": authority["resource_preflight"]["expected_environment"],
        "implementation_freeze_commit": IMPLEMENTATION_FREEZE_COMMIT,
    }


def _capture_authority() -> tuple[dict[str, Any], dict[str, Any]]:
    head_commit = _git_head_commit()
    _require_implementation_lineage(head_commit)
    _require_runtime_state_absent()

    v2_payload = _read_repository_file(V2_PREREGISTRATION_PATH)
    if (
        _git_blob_bytes(IMPLEMENTATION_FREEZE_COMMIT, V2_PREREGISTRATION_PATH)
        != v2_payload
    ):
        raise RuntimeError("v2 preregistration changed after implementation freeze")
    v2_preregistration = contract.parse_strict_json_bytes(
        v2_payload, location="$.v2_preregistration"
    )
    if contract.artifact_json_bytes(v2_preregistration) != v2_payload:
        raise RuntimeError("v2 preregistration is not canonical")
    candidate = _mapping(v2_preregistration.get("candidate"), "$.candidate")
    observed_environment = _mapping(
        candidate.get("environment"), "$.candidate.environment"
    )
    expected_environment = {
        name: observed_environment[name]
        for name in protocol.OBSERVED_ENVIRONMENT_FIELDS
    }

    dependency_payloads: dict[str, bytes] = {}
    dependency_receipts: dict[str, dict[str, Any]] = {}
    for name, relative in sorted(
        contract.CRITICAL_EXECUTION_DEPENDENCY_SOURCE_PATHS.items()
    ):
        current = _read_repository_file(relative)
        if _git_blob_bytes(IMPLEMENTATION_FREEZE_COMMIT, relative) != current:
            raise RuntimeError(
                f"critical execution dependency changed after implementation freeze: {name}"
            )
        dependency_payloads[name] = current
        dependency_receipts[name] = {
            "path": relative,
            "bytes": len(current),
            "sha256": contract.sha256_bytes(current),
        }

    authority = contract.build_execution_authority_contract(
        implementation_freeze_commit=IMPLEMENTATION_FREEZE_COMMIT,
        expected_environment=expected_environment,
        critical_execution_dependency_receipts=dependency_receipts,
    )
    snapshot = {
        "dependency_payloads": dependency_payloads,
        "head_commit": head_commit,
        "v2_preregistration_payload": v2_payload,
    }
    return authority, snapshot


def _revalidate_authority_inputs(snapshot: Mapping[str, Any]) -> None:
    expected_head = snapshot.get("head_commit")
    if not isinstance(expected_head, str) or _git_head_commit() != expected_head:
        raise RuntimeError("HEAD changed during authority construction")
    _require_implementation_lineage(expected_head)
    if _read_repository_file(V2_PREREGISTRATION_PATH) != snapshot.get(
        "v2_preregistration_payload"
    ):
        raise RuntimeError("v2 preregistration changed during authority construction")
    dependency_payloads = snapshot.get("dependency_payloads")
    if not isinstance(dependency_payloads, Mapping):
        raise RuntimeError("invalid authority dependency snapshot")
    for name, relative in sorted(
        contract.CRITICAL_EXECUTION_DEPENDENCY_SOURCE_PATHS.items()
    ):
        if _read_repository_file(relative) != dependency_payloads.get(name):
            raise RuntimeError(
                f"critical execution dependency changed during authority construction: {name}"
            )
    _require_runtime_state_absent()


def _require_implementation_lineage(head_commit: str) -> None:
    if re.fullmatch(r"[0-9a-f]{40}", head_commit) is None:
        raise RuntimeError("unsafe HEAD commit")
    ancestor = _git_process(
        "merge-base", "--is-ancestor", IMPLEMENTATION_FREEZE_COMMIT, head_commit
    )
    replacements = _git_process("replace", "-l")
    if ancestor.returncode != 0:
        raise RuntimeError("implementation freeze is not an ancestor of HEAD")
    if replacements.returncode != 0 or replacements.stdout.strip():
        raise RuntimeError("Git replace refs are forbidden for authority lineage")
    for relative in contract.IMPLEMENTATION_SOURCE_PATHS.values():
        if _read_repository_file(relative) != _git_blob_bytes(
            IMPLEMENTATION_FREEZE_COMMIT, relative
        ):
            raise RuntimeError(
                f"implementation source changed after implementation freeze: {relative}"
            )


def _require_runtime_state_absent() -> None:
    for relative in (protocol.RUN_OUTPUT_ROOT, protocol.LIFECYCLE_LEASE_ROOT):
        _validate_repository_relative_path(relative)
        _require_safe_parent_chain(relative)
        if os.path.lexists(ROOT / PurePosixPath(relative)):
            raise RuntimeError(
                f"diagnostic runtime state exists before authority freeze: {relative}"
            )
    if runner._reserved_sibling_staging_names():
        raise RuntimeError("reserved diagnostic sibling staging requires review")


def _git_head_commit() -> str:
    completed = _git_process("rev-parse", "--verify", "HEAD^{commit}")
    try:
        value = completed.stdout.decode("ascii").strip()
    except UnicodeDecodeError as exc:
        raise RuntimeError("unable to resolve exact HEAD commit") from exc
    if completed.returncode != 0 or re.fullmatch(r"[0-9a-f]{40}", value) is None:
        raise RuntimeError("unable to resolve exact HEAD commit")
    return value


def _git_blob_bytes(commit: str, relative: str) -> bytes:
    _validate_repository_relative_path(relative)
    if re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        raise RuntimeError("unsafe Git blob commit")
    completed = _git_process("cat-file", "blob", f"{commit}:{relative}")
    if completed.returncode != 0 or len(completed.stdout) > MAX_BOUND_FILE_BYTES:
        raise RuntimeError("unable to read authority-lineage Git blob")
    return completed.stdout


def _git_process(*args: str) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(
            ["git", "-c", "core.commitGraph=false", *args],
            cwd=ROOT,
            env=_git_environment(),
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError("unable to inspect authority Git lineage") from exc


def _git_environment() -> dict[str, str]:
    environment = {
        name: value for name, value in os.environ.items() if not name.startswith("GIT_")
    }
    environment.update(
        {
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_GRAFT_FILE": os.devnull,
            "GIT_LFS_SKIP_SMUDGE": "1",
            "GIT_NO_LAZY_FETCH": "1",
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_TERMINAL_PROMPT": "0",
        }
    )
    return environment


def _read_repository_file(relative: str) -> bytes:
    _validate_repository_relative_path(relative)
    _require_safe_parent_chain(relative)
    return _read_regular_file_once(ROOT / PurePosixPath(relative))


def _require_safe_parent_chain(relative: str) -> None:
    _validate_repository_relative_path(relative)
    absolute_root = Path(os.path.abspath(ROOT))
    candidates = [absolute_root]
    cursor = absolute_root
    for part in PurePosixPath(relative).parts[:-1]:
        cursor /= part
        candidates.append(cursor)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    for candidate in candidates:
        if not os.path.lexists(candidate):
            break
        try:
            metadata = candidate.lstat()
            resolved = candidate.resolve(strict=True)
        except OSError as exc:
            raise RuntimeError(f"unable to inspect bound parent: {candidate}") from exc
        if (
            resolved != candidate
            or candidate.is_symlink()
            or not stat.S_ISDIR(metadata.st_mode)
            or bool(getattr(metadata, "st_file_attributes", 0) & reparse_flag)
        ):
            raise RuntimeError(f"unsafe bound parent: {candidate}")


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
        (item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns, item.st_nlink)
        for item in (before, after_handle, after)
    }
    if len(payload) > MAX_BOUND_FILE_BYTES or len(signatures) != 1:
        raise RuntimeError(f"bound file changed while reading: {path}")
    return payload


def _mapping(value: object, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or not all(isinstance(key, str) for key in value):
        raise RuntimeError(f"mapping required at {location}")
    return value


if __name__ == "__main__":
    raise SystemExit(main())
