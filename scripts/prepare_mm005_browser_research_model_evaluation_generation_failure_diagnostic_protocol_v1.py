"""Build or check the MM-005 generation-failure diagnostic protocol."""

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
    mm005_browser_research_model_evaluation_generation_failure_diagnostic as contract,
)

MAX_BOUND_FILE_BYTES = 64 * 1024 * 1024


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
            raise SystemExit("MM-005 generation-failure diagnostic protocol is stale")
        _revalidate_protocol_inputs(snapshot)
        if _read_regular_file_once(output_path) != payload:
            raise RuntimeError("diagnostic protocol changed during final validation")
    else:
        if os.path.lexists(output_path):
            raise FileExistsError(output_path)
        _revalidate_protocol_inputs(snapshot)
        _require_safe_parent_chain(contract.PREREGISTRATION_PATH)
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
    """Load immutable result lineage and current protocol sources model-free."""

    inputs, snapshot = _capture_protocol_inputs()
    _revalidate_protocol_inputs(snapshot)
    return inputs


def _capture_protocol_inputs() -> tuple[dict[str, Any], dict[str, Any]]:
    head_commit, publication_current, publication_blobs = (
        _validate_published_result_lineage()
    )
    _require_planned_outputs_absent()
    source_payloads = {
        name: _read_repository_file(path)
        for name, path in sorted(contract.PROTOCOL_SOURCE_PATHS.items())
    }
    inputs = {
        "publication_current_payloads": publication_current,
        "publication_blob_payloads": publication_blobs,
        "source_payloads": source_payloads,
        "diagnostic_output_absent": True,
        "lifecycle_lease_absent": True,
    }
    snapshot = {
        "head_commit": head_commit,
        "publication_current_payloads": dict(publication_current),
        "publication_blob_payloads": dict(publication_blobs),
        "source_payloads": dict(source_payloads),
    }
    return inputs, snapshot


def _validate_published_result_lineage() -> tuple[
    str, dict[str, bytes], dict[str, bytes]
]:
    commit = contract.RESULT_PUBLICATION_COMMIT
    if re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        raise RuntimeError("unsafe result publication commit")
    head_commit = _git_head_commit()
    _require_git_lineage_state(head_commit)
    current_payloads: dict[str, bytes] = {}
    blob_payloads: dict[str, bytes] = {}
    for relative in contract.RESULT_PUBLICATION_BOUND_PATHS:
        frozen = _git_blob_bytes(commit, relative)
        current = _read_repository_file(relative)
        if frozen != current:
            raise RuntimeError(
                f"result publication lineage changed after clean merge: {relative}"
            )
        current_payloads[relative] = current
        blob_payloads[relative] = frozen
    published_result_blob = blob_payloads.get(contract.PUBLISHED_RESULT_PATH)
    if published_result_blob is None:
        raise RuntimeError("published result is absent from bound lineage")
    if (
        len(published_result_blob) != contract.PUBLISHED_RESULT_BYTES
        or contract.sha256_bytes(published_result_blob)
        != contract.PUBLISHED_RESULT_SHA256
    ):
        raise RuntimeError("published result receipt differs from protocol constants")
    return head_commit, current_payloads, blob_payloads


def _revalidate_protocol_inputs(snapshot: Mapping[str, Any]) -> None:
    expected_head = snapshot.get("head_commit")
    if not isinstance(expected_head, str) or _git_head_commit() != expected_head:
        raise RuntimeError("HEAD changed during diagnostic protocol construction")
    _require_git_lineage_state(expected_head)
    for snapshot_key, paths in (
        (
            "publication_current_payloads",
            contract.RESULT_PUBLICATION_BOUND_PATHS,
        ),
        ("source_payloads", tuple(sorted(contract.PROTOCOL_SOURCE_PATHS))),
    ):
        expected = snapshot.get(snapshot_key)
        if not isinstance(expected, Mapping):
            raise RuntimeError("invalid diagnostic protocol input snapshot")
        for key in paths:
            relative = (
                contract.PROTOCOL_SOURCE_PATHS[key]
                if snapshot_key == "source_payloads"
                else key
            )
            if _read_repository_file(relative) != expected.get(key):
                raise RuntimeError(
                    f"diagnostic protocol input changed before final validation: {relative}"
                )
    expected_blobs = snapshot.get("publication_blob_payloads")
    if not isinstance(expected_blobs, Mapping):
        raise RuntimeError("invalid diagnostic protocol blob snapshot")
    for relative in contract.RESULT_PUBLICATION_BOUND_PATHS:
        if _git_blob_bytes(
            contract.RESULT_PUBLICATION_COMMIT, relative
        ) != expected_blobs.get(relative):
            raise RuntimeError(
                f"result publication blob changed before final validation: {relative}"
            )
    _require_planned_outputs_absent()


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
    ancestor = _git_process(
        "merge-base", "--is-ancestor", contract.RESULT_PUBLICATION_COMMIT, head_commit
    )
    replacements = _git_process("replace", "-l")
    if ancestor.returncode != 0:
        raise RuntimeError("result publication commit is not an ancestor of HEAD")
    if replacements.returncode != 0 or replacements.stdout.strip():
        raise RuntimeError("Git replace refs are forbidden for protocol lineage")


def _require_planned_outputs_absent() -> None:
    for relative in (contract.RUN_OUTPUT_ROOT, contract.LIFECYCLE_LEASE_ROOT):
        _validate_repository_relative_path(relative)
        _require_safe_parent_chain(relative)
        if os.path.lexists(ROOT / PurePosixPath(relative)):
            raise RuntimeError(
                f"diagnostic output exists before execution authority: {relative}"
            )


def _git_blob_bytes(commit: str, relative: str) -> bytes:
    _validate_repository_relative_path(relative)
    if re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        raise RuntimeError("unsafe Git blob commit")
    completed = _git_process("cat-file", "blob", f"{commit}:{relative}")
    if completed.returncode != 0 or len(completed.stdout) > MAX_BOUND_FILE_BYTES:
        raise RuntimeError("unable to read result-publication Git blob")
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
        raise RuntimeError("unable to inspect result-publication Git lineage") from exc


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


if __name__ == "__main__":
    raise SystemExit(main())
