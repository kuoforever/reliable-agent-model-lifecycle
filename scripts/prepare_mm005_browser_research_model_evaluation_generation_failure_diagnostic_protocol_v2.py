"""Build or check the MM-005 generation-failure diagnostic protocol v2."""

from __future__ import annotations

import argparse
import os
import re
import stat
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(ROOT))

from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_model_evaluation_generation_failure_diagnostic as v1_contract,
)
from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_model_evaluation_generation_failure_diagnostic_protocol_v2 as contract,
)

MAX_BOUND_FILE_BYTES = 8 * 1024 * 1024


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    inputs, snapshot = _capture_protocol_inputs()
    protocol = contract.expected_preregistration(**inputs)
    payload = contract.artifact_json_bytes(protocol)
    output_path = ROOT / contract.PREREGISTRATION_PATH
    if args.check:
        if _read_regular_file_once(output_path) != payload:
            raise SystemExit(
                "MM-005 generation-failure diagnostic protocol v2 is stale"
            )
        _revalidate_protocol_inputs(snapshot)
        if _read_regular_file_once(output_path) != payload:
            raise RuntimeError("diagnostic protocol v2 changed during final validation")
    else:
        if os.path.lexists(output_path):
            raise FileExistsError(output_path)
        _revalidate_protocol_inputs(snapshot)
        _require_safe_parent_chain(contract.PREREGISTRATION_PATH)
        if os.path.lexists(output_path):
            raise FileExistsError(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("xb") as handle:
            written = handle.write(payload)
            if written != len(payload):
                raise RuntimeError("short diagnostic protocol v2 write")
            handle.flush()
            os.fsync(handle.fileno())

    print(
        contract.artifact_json_bytes(
            {
                "diagnostic_execution_authorized": False,
                "experiment_id": protocol["experiment_id"],
                "gate_id": protocol["gate_id"],
                "next_gate": protocol["next_gate"],
                "protocol_sha256": contract.sha256_bytes(payload),
                "run_id": protocol["run_id"],
                "valid": True,
            }
        )
        .decode("utf-8")
        .rstrip()
    )
    return 0


def build_protocol() -> dict[str, Any]:
    inputs, snapshot = _capture_protocol_inputs()
    protocol = contract.expected_preregistration(**inputs)
    _revalidate_protocol_inputs(snapshot)
    return protocol


def protocol_inputs() -> dict[str, Any]:
    inputs, snapshot = _capture_protocol_inputs()
    _revalidate_protocol_inputs(snapshot)
    return inputs


def _capture_protocol_inputs() -> tuple[dict[str, Any], dict[str, Any]]:
    head_commit = _git_head_commit()
    _require_git_lineage_state(head_commit)
    current_payloads: dict[str, bytes] = {}
    blob_payloads: dict[str, bytes] = {}
    for name, binding in sorted(contract.LINEAGE_BINDINGS.items()):
        commit = _string_binding(binding, "commit")
        relative = _string_binding(binding, "path")
        current = _read_repository_file(relative)
        blob = _git_blob_bytes(commit, relative)
        if current != blob:
            raise RuntimeError(f"lineage payload differs from frozen blob: {relative}")
        current_payloads[name] = current
        blob_payloads[name] = blob

    source_payloads = {
        name: _read_repository_file(path)
        for name, path in sorted(contract.PROTOCOL_SOURCE_PATHS.items())
    }
    v1_expected = _rebuild_frozen_v1_protocol_without_runtime_topology()
    v1_payload = current_payloads["v1_diagnostic_protocol"]
    if v1_contract.artifact_json_bytes(v1_expected) != v1_payload:
        raise RuntimeError("v1 diagnostic protocol no longer rebuilds exactly")

    presence = _require_planned_outputs_absent()
    inputs = {
        "lineage_current_payloads": current_payloads,
        "lineage_blob_payloads": blob_payloads,
        "source_payloads": source_payloads,
        "v1_expected_preregistration": v1_expected,
        **presence,
    }
    snapshot = {
        "head_commit": head_commit,
        "lineage_current_payloads": dict(current_payloads),
        "lineage_blob_payloads": dict(blob_payloads),
        "source_payloads": dict(source_payloads),
        "v1_expected_payload": v1_contract.artifact_json_bytes(v1_expected),
        "presence": dict(presence),
    }
    return inputs, snapshot


def _revalidate_protocol_inputs(snapshot: Mapping[str, Any]) -> None:
    expected_head = snapshot.get("head_commit")
    if not isinstance(expected_head, str) or _git_head_commit() != expected_head:
        raise RuntimeError("HEAD changed during diagnostic protocol v2 construction")
    _require_git_lineage_state(expected_head)

    current = snapshot.get("lineage_current_payloads")
    blobs = snapshot.get("lineage_blob_payloads")
    sources = snapshot.get("source_payloads")
    if not all(isinstance(value, Mapping) for value in (current, blobs, sources)):
        raise RuntimeError("invalid diagnostic protocol v2 input snapshot")
    assert isinstance(current, Mapping)
    assert isinstance(blobs, Mapping)
    assert isinstance(sources, Mapping)
    for name, binding in sorted(contract.LINEAGE_BINDINGS.items()):
        commit = _string_binding(binding, "commit")
        relative = _string_binding(binding, "path")
        if _read_repository_file(relative) != current.get(name):
            raise RuntimeError(
                f"lineage input changed before final snapshot: {relative}"
            )
        if _git_blob_bytes(commit, relative) != blobs.get(name):
            raise RuntimeError(
                f"lineage blob changed before final snapshot: {relative}"
            )
    for name, relative in sorted(contract.PROTOCOL_SOURCE_PATHS.items()):
        if _read_repository_file(relative) != sources.get(name):
            raise RuntimeError(
                f"protocol source changed before final snapshot: {relative}"
            )

    expected_v1_payload = snapshot.get("v1_expected_payload")
    rebuilt_v1 = v1_contract.artifact_json_bytes(
        _rebuild_frozen_v1_protocol_without_runtime_topology()
    )
    if not isinstance(expected_v1_payload, bytes) or rebuilt_v1 != expected_v1_payload:
        raise RuntimeError("v1 diagnostic protocol changed before final snapshot")
    presence = _require_planned_outputs_absent()
    if presence != snapshot.get("presence"):
        raise RuntimeError("planned runtime topology changed before final snapshot")


def _rebuild_frozen_v1_protocol_without_runtime_topology() -> dict[str, Any]:
    publication_current: dict[str, bytes] = {}
    publication_blobs: dict[str, bytes] = {}
    for relative in v1_contract.RESULT_PUBLICATION_BOUND_PATHS:
        current = _read_repository_file(relative)
        blob = _git_blob_bytes(v1_contract.RESULT_PUBLICATION_COMMIT, relative)
        if current != blob:
            raise RuntimeError(
                f"v1 publication lineage differs from frozen blob: {relative}"
            )
        publication_current[relative] = current
        publication_blobs[relative] = blob
    source_payloads = {
        name: _read_repository_file(path)
        for name, path in sorted(v1_contract.PROTOCOL_SOURCE_PATHS.items())
    }
    rebuilt = v1_contract.expected_preregistration(
        publication_current_payloads=publication_current,
        publication_blob_payloads=publication_blobs,
        source_payloads=source_payloads,
        diagnostic_output_absent=True,
        lifecycle_lease_absent=True,
    )
    if not isinstance(rebuilt, dict) or not all(
        isinstance(key, str) for key in rebuilt
    ):
        raise RuntimeError("v1 diagnostic protocol rebuild is not an object")
    return cast(dict[str, Any], rebuilt)


def _git_head_commit() -> str:
    completed = _git_process("rev-parse", "--verify", "HEAD^{commit}")
    try:
        value = completed.stdout.decode("ascii").strip()
    except UnicodeDecodeError as exc:
        raise RuntimeError("unable to resolve exact HEAD commit") from exc
    if completed.returncode != 0 or re.fullmatch(r"[0-9a-f]{40}", value) is None:
        raise RuntimeError("unable to resolve exact HEAD commit")
    return value


def _require_git_lineage_state(head_commit: str) -> None:
    if re.fullmatch(r"[0-9a-f]{40}", head_commit) is None:
        raise RuntimeError("unsafe HEAD commit")
    replacements = _git_process("replace", "-l")
    if replacements.returncode != 0 or replacements.stdout.strip():
        raise RuntimeError("Git replace refs are forbidden for protocol lineage")
    for binding in contract.LINEAGE_BINDINGS.values():
        commit = _string_binding(binding, "commit")
        if not _commit_is_ancestor(commit, head_commit):
            raise RuntimeError(f"bound artifact commit is not an ancestor: {commit}")
    for child, parent in contract.COMMIT_PARENT_CHAIN.items():
        if not _commit_is_ancestor(child, head_commit):
            raise RuntimeError(f"required protocol lineage is not an ancestor: {child}")
        completed = _git_process("rev-list", "--parents", "-n", "1", child)
        try:
            fields = completed.stdout.decode("ascii").strip().split()
        except UnicodeDecodeError as exc:
            raise RuntimeError("unable to read protocol first-parent lineage") from exc
        if completed.returncode != 0 or fields != [child, parent]:
            raise RuntimeError(f"protocol first-parent lineage drifted: {child}")
    for ancestor, descendant in contract.COMMIT_ANCESTOR_RELATIONS:
        if not _commit_is_ancestor(ancestor, descendant):
            raise RuntimeError(
                f"protocol ancestor relation drifted: {ancestor} -> {descendant}"
            )
    _require_unique_first_parent_introduction(
        contract.ORIGINAL_V2_INTRODUCTION_COMMIT,
        v1_contract.V2_PREREGISTRATION_PATH,
    )


def _require_unique_first_parent_introduction(commit: str, relative: str) -> None:
    _validate_repository_relative_path(relative)
    if re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        raise RuntimeError("unsafe introduction commit")
    completed = _git_process(
        "log",
        "--first-parent",
        "--format=%H",
        "--diff-filter=A",
        contract.MAINTENANCE_MERGE_COMMIT,
        "--",
        relative,
    )
    try:
        introductions = completed.stdout.decode("ascii").strip().splitlines()
    except UnicodeDecodeError as exc:
        raise RuntimeError("unable to inspect protocol introduction") from exc
    if completed.returncode != 0 or introductions != [commit]:
        raise RuntimeError("protocol introduction lineage drifted")


def _commit_is_ancestor(commit: str, head_commit: str) -> bool:
    if re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        raise RuntimeError("unsafe protocol lineage commit")
    return (
        _git_process("merge-base", "--is-ancestor", commit, head_commit).returncode == 0
    )


def _require_planned_outputs_absent() -> dict[str, bool]:
    planned = (contract.RUN_OUTPUT_ROOT, contract.LIFECYCLE_LEASE_ROOT)
    for relative in planned:
        _validate_repository_relative_path(relative)
        _require_safe_parent_chain(relative)
        if os.path.lexists(ROOT / PurePosixPath(relative)):
            raise RuntimeError(
                f"diagnostic runtime exists before v2 authority: {relative}"
            )
    return {
        "planned_output_absent": True,
        "planned_lifecycle_absent": True,
    }


def _git_blob_bytes(commit: str, relative: str) -> bytes:
    _validate_repository_relative_path(relative)
    if re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        raise RuntimeError("unsafe Git blob commit")
    completed = _git_process("cat-file", "blob", f"{commit}:{relative}")
    if completed.returncode != 0 or len(completed.stdout) > MAX_BOUND_FILE_BYTES:
        raise RuntimeError("unable to read frozen protocol Git blob")
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
        raise RuntimeError("unable to inspect frozen protocol Git lineage") from exc


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
        or ":" in relative
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


def _string_binding(binding: Mapping[str, object], key: str) -> str:
    value = binding.get(key)
    if not isinstance(value, str):
        raise RuntimeError(f"invalid lineage binding: {key}")
    return value


if __name__ == "__main__":
    raise SystemExit(main())
