"""Build or check the MM-005 generation-diagnostic execution authority v2."""

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

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(ROOT))

from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_model_evaluation_generation_failure_diagnostic as scientific_protocol,
)
from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_model_evaluation_generation_failure_diagnostic_result_v2 as contract,
)
from scripts import (  # noqa: E402
    run_mm005_browser_research_model_evaluation_generation_failure_diagnostic_v2 as runner,
)

IMPLEMENTATION_FREEZE_COMMIT = "ac052a3781246deb7365914dacfa271d37cfef59"
V2_PREREGISTRATION_PATH = (
    "configs/mm005_browser_research_model_evaluation_protocol_v2.json"
)
MAX_BOUND_FILE_BYTES = 64 * 1024 * 1024
EXPECTED_ENVIRONMENT: dict[str, str | int] = {
    "accelerate": "1.3.0",
    "compute_capability": "8.9",
    "device": "cuda",
    "gpu": "NVIDIA GeForce RTX 4090 Laptop GPU",
    "gpu_vram_bytes": 17_170_956_288,
    "huggingface_hub": "0.29.3",
    "nvidia_driver": "596.49",
    "pillow": "11.3.0",
    "platform_machine": "AMD64",
    "platform_release": "11",
    "platform_system": "Windows",
    "platform_version": "10.0.26200",
    "python": "3.12.12",
    "safetensors": "0.5.3",
    "tokenizers": "0.21.4",
    "torch": "2.6.0+cu124",
    "transformers": "4.49.0",
}
EXPECTED_RESOURCE_CAPS: dict[str, float | int] = {
    "elapsed_seconds": 1800.0,
    "peak_gpu_allocated_bytes": 16_500_000_000,
    "peak_gpu_reserved_bytes": 16_500_000_000,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    authority, snapshot = _capture_authority()
    payload = contract.artifact_json_bytes(authority)
    output_path = ROOT / contract.EXECUTION_AUTHORITY_PATH
    if args.check:
        before = _read_regular_file_once(output_path)
        if before != payload:
            raise SystemExit("MM-005 diagnostic execution authority v2 is stale")
        _revalidate_authority_inputs(snapshot)
        if _read_regular_file_once(output_path) != before:
            raise RuntimeError("diagnostic execution authority v2 changed during check")
        validated_snapshot = snapshot
    else:
        if os.path.lexists(output_path):
            raise FileExistsError(output_path)
        _revalidate_authority_inputs(snapshot)
        _require_safe_parent_chain(contract.EXECUTION_AUTHORITY_PATH)
        if os.path.lexists(output_path):
            raise FileExistsError(output_path)
        with output_path.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        post_authority, post_snapshot = _capture_authority()
        if (
            contract.artifact_json_bytes(post_authority) != payload
            or post_snapshot.get("authority_output_payload") != payload
        ):
            raise RuntimeError("written diagnostic execution authority v2 differs")
        _revalidate_authority_inputs(post_snapshot)
        if _read_regular_file_once(output_path) != payload:
            raise RuntimeError("written diagnostic execution authority v2 changed")
        validated_snapshot = post_snapshot

    stage = validated_snapshot.get("stage")
    if not isinstance(stage, Mapping):
        raise RuntimeError("invalid validated authority stage snapshot")
    print(
        contract.artifact_json_bytes(
            {
                "authority_frozen": True,
                "authority_tracked_at_head": stage["tracked_at_head"],
                "authority_sha256": contract.sha256_bytes(payload),
                "critical_execution_dependency_receipts": len(
                    contract.CRITICAL_EXECUTION_DEPENDENCY_SOURCE_PATHS
                ),
                "diagnostic_attempt_consumed": False,
                "diagnostic_executed": False,
                "gate_id": contract.EXECUTION_AUTHORITY_GATE_ID,
                "implementation_freeze_commit": IMPLEMENTATION_FREEZE_COMMIT,
                "implementation_source_receipts": len(
                    contract.IMPLEMENTATION_SOURCE_PATHS
                ),
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
        "implementation_source_receipts": snapshot["implementation_source_receipts"],
        "stage": snapshot["stage"],
    }


def _capture_authority() -> tuple[dict[str, Any], dict[str, Any]]:
    head_commit = _git_head_commit()
    stage = _authority_stage_context(head_commit)
    topology = _require_runtime_state_absent()
    protocol_context = runner._published_protocol_context()

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
        for name in scientific_protocol.OBSERVED_ENVIRONMENT_FIELDS
    }
    if expected_environment != EXPECTED_ENVIRONMENT:
        raise RuntimeError("frozen 17-field execution environment differs")

    dependency_payloads: dict[str, bytes] = {}
    dependency_receipts: dict[str, dict[str, Any]] = {}
    for name, relative in sorted(
        contract.CRITICAL_EXECUTION_DEPENDENCY_SOURCE_PATHS.items()
    ):
        frozen = _git_blob_bytes(IMPLEMENTATION_FREEZE_COMMIT, relative)
        current = _read_repository_file(relative)
        if current != frozen:
            raise RuntimeError(
                f"critical execution dependency changed after implementation freeze: {name}"
            )
        dependency_payloads[name] = current
        dependency_receipts[name] = _receipt(relative, frozen)

    implementation_payloads: dict[str, bytes] = {}
    implementation_receipts: dict[str, dict[str, Any]] = {}
    for name, relative in sorted(contract.IMPLEMENTATION_SOURCE_PATHS.items()):
        frozen = _git_blob_bytes(IMPLEMENTATION_FREEZE_COMMIT, relative)
        current = _read_repository_file(relative)
        if current != frozen:
            raise RuntimeError(
                f"implementation source changed after implementation freeze: {name}"
            )
        introductions = _git_first_parent_introductions(relative)
        if introductions != [contract.INITIAL_IMPLEMENTATION_PUBLICATION_COMMIT]:
            raise RuntimeError(f"implementation source introduction differs: {name}")
        implementation_payloads[name] = current
        implementation_receipts[name] = {
            **_receipt(relative, frozen),
            "first_parent_introduction_commit": (
                contract.INITIAL_IMPLEMENTATION_PUBLICATION_COMMIT
            ),
            "freeze_commit": IMPLEMENTATION_FREEZE_COMMIT,
        }

    authority = contract.build_execution_authority_contract(
        implementation_freeze_commit=IMPLEMENTATION_FREEZE_COMMIT,
        expected_environment=expected_environment,
        critical_execution_dependency_receipts=dependency_receipts,
    )
    if authority["resource_preflight"]["resource_caps"] != EXPECTED_RESOURCE_CAPS:
        raise RuntimeError("frozen execution resource caps differ")
    authority_output_payload: bytes | None = None
    authority_output_path = ROOT / contract.EXECUTION_AUTHORITY_PATH
    if os.path.lexists(authority_output_path):
        authority_output_payload = _read_repository_file(
            contract.EXECUTION_AUTHORITY_PATH
        )
    if stage["tracked_at_head"]:
        if authority_output_payload is None:
            raise RuntimeError("tracked authority is missing from the worktree")
        if (
            _git_blob_bytes(head_commit, contract.EXECUTION_AUTHORITY_PATH)
            != authority_output_payload
        ):
            raise RuntimeError("tracked authority differs from introduction blob")
    snapshot = {
        "dependency_payloads": dependency_payloads,
        "head_commit": head_commit,
        "implementation_payloads": implementation_payloads,
        "implementation_source_receipts": implementation_receipts,
        "protocol_context": protocol_context,
        "authority_output_payload": authority_output_payload,
        "stage": stage,
        "topology": topology,
        "v2_preregistration_payload": v2_payload,
    }
    return authority, snapshot


def _revalidate_authority_inputs(snapshot: Mapping[str, Any]) -> None:
    expected_head = snapshot.get("head_commit")
    if not isinstance(expected_head, str) or _git_head_commit() != expected_head:
        raise RuntimeError("HEAD changed during authority construction")
    if _authority_stage_context(expected_head) != snapshot.get("stage"):
        raise RuntimeError("authority publication stage changed during construction")
    authority_output_path = ROOT / contract.EXECUTION_AUTHORITY_PATH
    current_authority_payload = (
        _read_repository_file(contract.EXECUTION_AUTHORITY_PATH)
        if os.path.lexists(authority_output_path)
        else None
    )
    if current_authority_payload != snapshot.get("authority_output_payload"):
        raise RuntimeError("authority artifact changed during construction")
    stage = snapshot.get("stage")
    if (
        isinstance(stage, Mapping)
        and stage.get("tracked_at_head") is True
        and (
            current_authority_payload is None
            or _git_blob_bytes(expected_head, contract.EXECUTION_AUTHORITY_PATH)
            != current_authority_payload
        )
    ):
        raise RuntimeError("tracked authority differs from current HEAD blob")
    if _require_runtime_state_absent() != snapshot.get("topology"):
        raise RuntimeError("diagnostic runtime topology changed during construction")
    if runner._published_protocol_context() != snapshot.get("protocol_context"):
        raise RuntimeError("published diagnostic protocol changed during construction")
    if _read_repository_file(V2_PREREGISTRATION_PATH) != snapshot.get(
        "v2_preregistration_payload"
    ):
        raise RuntimeError("v2 preregistration changed during authority construction")
    for snapshot_key, source_paths, label in (
        (
            "dependency_payloads",
            contract.CRITICAL_EXECUTION_DEPENDENCY_SOURCE_PATHS,
            "critical execution dependency",
        ),
        (
            "implementation_payloads",
            contract.IMPLEMENTATION_SOURCE_PATHS,
            "implementation source",
        ),
    ):
        payloads = snapshot.get(snapshot_key)
        if not isinstance(payloads, Mapping):
            raise RuntimeError(f"invalid authority {label} snapshot")
        for name, relative in sorted(source_paths.items()):
            if _read_repository_file(relative) != payloads.get(name):
                raise RuntimeError(
                    f"{label} changed during authority construction: {name}"
                )


def _authority_stage_context(head_commit: str) -> dict[str, Any]:
    _require_no_hidden_index_flags()
    _require_implementation_lineage()
    tracked = _git_path_exists(head_commit, contract.EXECUTION_AUTHORITY_PATH)
    if not tracked:
        if head_commit != IMPLEMENTATION_FREEZE_COMMIT:
            raise RuntimeError(
                "draft authority requires exact implementation freeze HEAD"
            )
        return {"freeze_commit": None, "tracked_at_head": False}
    introductions = _git_first_parent_introductions(contract.EXECUTION_AUTHORITY_PATH)
    if introductions != [head_commit]:
        raise RuntimeError("authority must be first introduced at current HEAD")
    _require_unique_parent(head_commit, IMPLEMENTATION_FREEZE_COMMIT)
    if set(_git_name_only_paths(IMPLEMENTATION_FREEZE_COMMIT, head_commit)) != set(
        contract.EXECUTION_AUTHORITY_SLICE_PATHS
    ):
        raise RuntimeError("authority tree delta is not the exact reviewed slice")
    return {"freeze_commit": head_commit, "tracked_at_head": True}


def _require_implementation_lineage() -> None:
    _require_unique_parent(
        contract.ZERO_BANDWIDTH_MAINTENANCE_COMMIT, contract.PROTOCOL_MERGE_COMMIT
    )
    _require_unique_parent(
        contract.IMPLEMENTATION_BASE_COMMIT,
        contract.ZERO_BANDWIDTH_MAINTENANCE_COMMIT,
    )
    _require_unique_parent(
        contract.INITIAL_IMPLEMENTATION_PUBLICATION_COMMIT,
        contract.IMPLEMENTATION_BASE_COMMIT,
    )
    _require_unique_parent(
        IMPLEMENTATION_FREEZE_COMMIT,
        contract.INITIAL_IMPLEMENTATION_PUBLICATION_COMMIT,
    )
    _require_commit_ancestor(IMPLEMENTATION_FREEZE_COMMIT)
    initial_delta = set(
        _git_name_only_paths(
            contract.IMPLEMENTATION_BASE_COMMIT,
            contract.INITIAL_IMPLEMENTATION_PUBLICATION_COMMIT,
        )
    )
    final_delta = set(
        _git_name_only_paths(
            contract.IMPLEMENTATION_BASE_COMMIT, IMPLEMENTATION_FREEZE_COMMIT
        )
    )
    compatibility_delta = set(
        _git_name_only_paths(
            contract.INITIAL_IMPLEMENTATION_PUBLICATION_COMMIT,
            IMPLEMENTATION_FREEZE_COMMIT,
        )
    )
    expected = set(runner.IMPLEMENTATION_SLICE_PATHS)
    if (
        initial_delta != expected
        or final_delta != expected
        or not compatibility_delta
        or not compatibility_delta.issubset(expected)
    ):
        raise RuntimeError("implementation publication lineage or slice differs")
    replacements = _git_process("replace", "-l")
    if replacements.returncode != 0 or replacements.stdout.strip():
        raise RuntimeError("Git replace refs are forbidden for authority lineage")


def _require_runtime_state_absent() -> dict[str, bool]:
    topology = runner._output_topology()
    runner._validate_output_topology(topology)
    if topology.get("output_parent") is not False or any(
        topology.get(name) is not False for name in runner.RUNTIME_OUTPUT_KEYS
    ):
        raise RuntimeError("diagnostic runtime, output, lease, or staging state exists")
    return cast(dict[str, bool], topology)


def _require_commit_ancestor(commit: str) -> None:
    completed = _git_process("merge-base", "--is-ancestor", commit, "HEAD")
    if completed.returncode != 0 or completed.stdout:
        raise RuntimeError("implementation freeze is not an ancestor of HEAD")


def _require_unique_parent(child: str, parent: str) -> None:
    completed = _git_process("rev-list", "--parents", "-n", "1", child)
    if completed.returncode != 0:
        raise RuntimeError("unable to inspect diagnostic lineage")
    lineage = _decode_ascii(completed.stdout, "diagnostic lineage").split()
    if lineage != [child, parent]:
        raise RuntimeError("diagnostic lineage unique direct parent differs")


def _git_head_commit() -> str:
    completed = _git_process("rev-parse", "--verify", "HEAD^{commit}")
    value = _decode_ascii(completed.stdout, "HEAD commit").strip()
    if completed.returncode != 0 or re.fullmatch(r"[0-9a-f]{40}", value) is None:
        raise RuntimeError("unable to resolve exact HEAD commit")
    return value


def _git_path_exists(commit: str, relative: str) -> bool:
    _validate_commit(commit)
    _validate_repository_relative_path(relative)
    completed = _git_process("cat-file", "-e", f"{commit}:{relative}")
    if completed.stdout:
        raise RuntimeError("unexpected Git output while checking authority path")
    return completed.returncode == 0


def _git_first_parent_introductions(relative: str) -> list[str]:
    _validate_repository_relative_path(relative)
    completed = _git_process(
        "log", "--first-parent", "--diff-filter=A", "--format=%H", "--", relative
    )
    if completed.returncode != 0:
        raise RuntimeError("unable to inspect first-parent introduction")
    values = [
        line for line in _decode_ascii(completed.stdout, "Git log").splitlines() if line
    ]
    if any(re.fullmatch(r"[0-9a-f]{40}", value) is None for value in values):
        raise RuntimeError("invalid first-parent introduction commit")
    return values


def _git_name_only_paths(old: str, new: str) -> list[str]:
    _validate_commit(old)
    _validate_commit(new)
    completed = _git_process(
        "diff", "--no-ext-diff", "--no-renames", "--name-only", "-z", old, new, "--"
    )
    if completed.returncode != 0:
        raise RuntimeError("unable to inspect reviewed tree delta")
    try:
        decoded = completed.stdout.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RuntimeError("reviewed tree delta is not UTF-8") from exc
    if not decoded:
        return []
    if not decoded.endswith("\0"):
        raise RuntimeError("reviewed tree delta is not NUL terminated")
    paths = decoded[:-1].split("\0")
    for relative in paths:
        _validate_repository_relative_path(relative)
    return paths


def _git_blob_bytes(commit: str, relative: str) -> bytes:
    _validate_commit(commit)
    _validate_repository_relative_path(relative)
    completed = _git_process("cat-file", "blob", f"{commit}:{relative}")
    if completed.returncode != 0 or len(completed.stdout) > MAX_BOUND_FILE_BYTES:
        raise RuntimeError("unable to read authority-lineage Git blob")
    return completed.stdout


def _git_process(*args: str) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(
            [
                "git",
                "-c",
                "core.hooksPath=NUL" if os.name == "nt" else "core.hooksPath=/dev/null",
                "-c",
                "filter.lfs.process=",
                "-c",
                "filter.lfs.required=false",
                "-c",
                "core.commitGraph=false",
                "-c",
                "core.fsmonitor=false",
                "-c",
                "advice.graftFileDeprecated=false",
                *args,
            ],
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
        name: value
        for name, value in os.environ.items()
        if not name.upper().startswith("GIT_")
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


def _require_no_hidden_index_flags() -> None:
    completed = _git_process("ls-files", "-v", "-z")
    if completed.returncode != 0 or completed.stderr:
        raise RuntimeError("unable to inspect Git index flags")
    payload = completed.stdout
    if payload and not payload.endswith(b"\0"):
        raise RuntimeError("Git index listing is not NUL terminated")
    entries = payload[:-1].split(b"\0") if payload else ()
    for entry in entries:
        if len(entry) < 3 or entry[1:2] != b" ":
            raise RuntimeError("Git index listing has an invalid record")
        try:
            tag = entry[:1].decode("ascii")
            relative = entry[2:].decode("utf-8")
        except UnicodeDecodeError as exc:
            raise RuntimeError("Git index listing is not UTF-8") from exc
        _validate_repository_relative_path(relative)
        if tag == "S" or tag.islower():
            raise RuntimeError(
                "Git assume-unchanged or skip-worktree index flag is forbidden"
            )


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
            raise RuntimeError(f"required bound parent is missing: {candidate}")
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


def _validate_commit(value: str) -> None:
    if re.fullmatch(r"[0-9a-f]{40}", value) is None:
        raise RuntimeError("unsafe Git commit")


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


def _decode_ascii(payload: bytes, label: str) -> str:
    try:
        return payload.decode("ascii")
    except UnicodeDecodeError as exc:
        raise RuntimeError(f"{label} is not ASCII") from exc


def _receipt(relative: str, payload: bytes) -> dict[str, Any]:
    return {
        "path": relative,
        "bytes": len(payload),
        "sha256": contract.sha256_bytes(payload),
    }


def _mapping(value: object, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or not all(isinstance(key, str) for key in value):
        raise RuntimeError(f"mapping required at {location}")
    return value


if __name__ == "__main__":
    raise SystemExit(main())
