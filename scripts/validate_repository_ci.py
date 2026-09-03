"""Validate the repository's split pointer-only and hydrated-LFS CI gates."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import py_compile
import re
import subprocess
import sys
import tempfile
import unittest
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from typing import Any, NoReturn

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
INVENTORY_PATH = ROOT / "configs" / "repository_ci_lfs_inventory_v1.json"
TRUST_ANCHOR_PATH = ROOT / "configs" / "repository_ci_lfs_trust_anchor_v1.json"
GATE_ID = "repository-ci-lfs-maintenance-v1"
TRUST_ANCHOR_GATE_ID = "repository-ci-lfs-zero-bandwidth-v2"
SUPPORTED_PYTHON_MINORS = {(3, 11), (3, 12), (3, 13)}
POINTER_SCOPE = "pointer_and_stdlib_only"
POINTER_METADATA_SCOPE = "pointer_metadata_only"
HYDRATED_SCOPE = "hydrated_lfs_integrity_preflight"
POINTER_JOB_CONTEXTS = (
    "python-matrix (3.11)",
    "python-matrix (3.12)",
    "python-matrix (3.13)",
)
POINTER_PYTHON_VERSIONS = ("3.11", "3.12", "3.13")
HYDRATED_JOB_CONTEXT = "hydrated-lfs-integrity"
HYDRATED_PYTHON_VERSION = "3.11"
CORE_TEST_MODULES = (
    "tests.test_bridge_consumer",
    "tests.test_reliability_dataset",
    "tests.test_runtime_freeze",
    "tests.test_lane_b",
    "tests.test_multimodal_trajectory",
    "tests.test_gui_grounding_eval",
    "tests.test_tool_router",
)
CORE_TEST_COUNT = 107
EXPECTED_GITATTRIBUTES = {
    "blob_oid": "sha1:e56bb119162726eed715ec43223d308318c46ead",
    "bytes": 390,
    "path": ".gitattributes",
    "sha256": (
        "sha256:25d24c1558f50fca6c058483faf4e5a9ab564252cca921e2b37393d631d00ce2"
    ),
}
EXPECTED_LFS_OBJECTS = (
    {
        "oid": (
            "sha256:1c58a3d08598250cc01bd35a3367fbcc778c551782e6117f686394ede3d65659"
        ),
        "path": ("baseline/adapters/fc-mvp-001-lora-sft-v1/adapter_model.safetensors"),
        "pointer_bytes": 133,
        "pointer_git_blob_oid": ("sha1:5945ce72f96244d9ee16cbdedc7f13d1f7684b1e"),
        "size": 17_462_432,
    },
    {
        "oid": (
            "sha256:efb62471e105b8ef25641200967d447b8cc2f3ff565937bc47193fbf79f4f342"
        ),
        "path": ("baseline/adapters/fc-mvp-001-lora-sft-v2/adapter_model.safetensors"),
        "pointer_bytes": 133,
        "pointer_git_blob_oid": ("sha1:db6f62d5d65595819e7b367f9f9c64c530c1cd26"),
        "size": 17_462_432,
    },
    {
        "oid": (
            "sha256:d93d2ea2d9f05564093cbb0b1286d2c368c54b01e847f1c37a98e00fb2914701"
        ),
        "path": (
            "baseline/adapters/mm003-qwen2.5-vl-3b-qlora-sft-v2/"
            "adapter_model.safetensors"
        ),
        "pointer_bytes": 133,
        "pointer_git_blob_oid": ("sha1:2f5baf6575c863e5939aab12f4ec445a4ab17354"),
        "size": 29_529_752,
    },
    {
        "oid": (
            "sha256:550175dfcfe14b0739aabf17573825a124180a6e21826e25d4b5ff733fb298a9"
        ),
        "path": "baseline/fc-mvp-001-fp32-attached-merge-numerics-v1-tensors.bin",
        "pointer_bytes": 133,
        "pointer_git_blob_oid": ("sha1:368b55bb2726683b7422ea9fa8f05eb1b99aa241"),
        "size": 46_069_904,
    },
)
TOTAL_LFS_PAYLOAD_BYTES = 110_524_520
TRUST_ANCHOR_COMMIT = "eb2aea3ca1eb5d82e823f7fc7a6aac7b5beb3fc9"
TRUST_ANCHOR_TREE = "bddfdadcc650b6ac94787ea2bfbb0e2f2f09a77d"
TRUST_ANCHOR_WORKFLOW_RUN_ID = 33_501_136_645
TRUST_ANCHOR_HYDRATED_JOB_ID = 99_834_499_141
MANUAL_LFS_ACKNOWLEDGEMENT = "DOWNLOAD 110524520 LFS BYTES"
EXACT_HEAD_CHECKOUT_GATE_ID = "repository-ci-exact-head-checkout-v1"
EXACT_HEAD_CHECKOUT_BASE_COMMIT = "e5e618b491a3dc38dbed9cdcd4c6c384f2df0f54"
EXACT_HEAD_ENVIRONMENT = "EXPECTED_HEAD_SHA"
EXACT_HEAD_GITHUB_SHA_EXPRESSION = (
    "${{ github.event_name == 'pull_request' && "
    "github.event.pull_request.head.sha || github.sha }}"
)
EXACT_HEAD_JOB_IDS = ("python-matrix", HYDRATED_JOB_CONTEXT)
EXACT_HEAD_SCOPE = "exact_github_event_head_checkout"
EXACT_HEAD_VERIFICATION_COMMAND = (
    "python -I scripts/validate_repository_ci.py --mode exact-checkout "
    '--expected-head "$EXPECTED_HEAD_SHA"'
)
PROTECTED_LFS_PATHS = (
    ".gitattributes",
    "configs/repository_ci_lfs_inventory_v1.json",
    "baseline/adapters/fc-mvp-001-lora-sft-v1/adapter_model.safetensors",
    "baseline/adapters/fc-mvp-001-lora-sft-v2/adapter_model.safetensors",
    "baseline/adapters/mm003-qwen2.5-vl-3b-qlora-sft-v2/adapter_model.safetensors",
    "baseline/fc-mvp-001-fp32-attached-merge-numerics-v1-tensors.bin",
)
EXPECTED_ATTRIBUTE_CONTROL_PATHS = (".gitattributes",)
FORBIDDEN_LFS_CONFIG_PATH = ".lfsconfig"
DIAGNOSTIC_V2_PROTOCOL_TEST_MODULE = (
    "tests.test_mm005_browser_research_model_evaluation_generation_failure_"
    "diagnostic_protocol_v2"
)
DIAGNOSTIC_V2_RESULT_TEST_MODULE = (
    "tests.test_mm005_browser_research_model_evaluation_generation_failure_"
    "diagnostic_result_v2"
)
DIAGNOSTIC_V2_IMPLEMENTATION_PATHS = (
    "docs/MM-005-browser-research-model-evaluation-generation-failure-"
    "diagnostic-implementation-v2.md",
    "scripts/run_mm005_browser_research_model_evaluation_generation_failure_"
    "diagnostic_v2.py",
    "src/fullcycle_bridge/mm005_browser_research_model_evaluation_generation_"
    "failure_diagnostic_result_v2.py",
    "tests/test_mm005_browser_research_model_evaluation_generation_failure_"
    "diagnostic_result_v2.py",
)
DIAGNOSTIC_V2_PROTOCOL_ONLY_TEST_COUNT = 18
DIAGNOSTIC_V2_IMPLEMENTATION_PROTOCOL_TEST_COUNT = 19
DIAGNOSTIC_V2_IMPLEMENTATION_TEST_COUNT = 62


class RepositoryCIValidationError(RuntimeError):
    """Fail-closed repository CI contract violation."""

    def __init__(self, code: str, location: str) -> None:
        self.code = code
        self.location = location
        super().__init__(f"{code} at {location}")


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def expected_inventory() -> dict[str, Any]:
    paths = [item["path"] for item in EXPECTED_LFS_OBJECTS]
    return {
        "gate_id": GATE_ID,
        "gitattributes": dict(EXPECTED_GITATTRIBUTES),
        "hydrated_gate": {
            "job_context": HYDRATED_JOB_CONTEXT,
            "lfs_include_paths": paths,
            "pointer_preflight_mode": "pointer-metadata",
            "python_version": HYDRATED_PYTHON_VERSION,
        },
        "lfs_objects": [dict(item) for item in EXPECTED_LFS_OBJECTS],
        "pointer_gate": {
            "full_integrity_verified": False,
            "job_contexts": list(POINTER_JOB_CONTEXTS),
            "lfs_payloads_read": 0,
            "python_versions": list(POINTER_PYTHON_VERSIONS),
            "scope": POINTER_SCOPE,
            "stdlib_test_count": CORE_TEST_COUNT,
            "stdlib_test_modules": list(CORE_TEST_MODULES),
        },
        "schema_version": 1,
        "total_lfs_payload_bytes": TOTAL_LFS_PAYLOAD_BYTES,
    }


def expected_trust_anchor() -> dict[str, Any]:
    return {
        "automatic_gate": {
            "content_identity_inherited": True,
            "current_hydration_verified": False,
            "current_payload_integrity_verified": False,
            "full_integrity_verified": False,
            "job_context": HYDRATED_JOB_CONTEXT,
            "lfs_payload_bytes_read": 0,
            "remote_availability_verified": False,
            "scope": "immutable_hydrated_anchor_and_pointer_no_drift",
        },
        "diagnostic_v2_focused_gate": {
            "implementation_complete_paths": list(DIAGNOSTIC_V2_IMPLEMENTATION_PATHS),
            "implementation_protocol_test_count": (
                DIAGNOSTIC_V2_IMPLEMENTATION_PROTOCOL_TEST_COUNT
            ),
            "implementation_test_count": DIAGNOSTIC_V2_IMPLEMENTATION_TEST_COUNT,
            "modules_when_implemented": [
                DIAGNOSTIC_V2_PROTOCOL_TEST_MODULE,
                DIAGNOSTIC_V2_RESULT_TEST_MODULE,
            ],
            "protocol_only_test_count": DIAGNOSTIC_V2_PROTOCOL_ONLY_TEST_COUNT,
            "protocol_test_module": DIAGNOSTIC_V2_PROTOCOL_TEST_MODULE,
            "python_versions": list(POINTER_PYTHON_VERSIONS),
        },
        "exact_head_checkout": {
            "base_commit": EXACT_HEAD_CHECKOUT_BASE_COMMIT,
            "expected_head_environment": EXACT_HEAD_ENVIRONMENT,
            "gate_id": EXACT_HEAD_CHECKOUT_GATE_ID,
            "github_sha_expression": EXACT_HEAD_GITHUB_SHA_EXPRESSION,
            "job_ids": list(EXACT_HEAD_JOB_IDS),
            "persist_credentials": False,
            "pull_request_target_allowed": False,
            "scope": EXACT_HEAD_SCOPE,
            "synthetic_merge_ref_allowed": False,
            "verification_command": EXACT_HEAD_VERIFICATION_COMMAND,
            "verification_mode": "exact-checkout",
        },
        "forbidden_lfs_config_path": FORBIDDEN_LFS_CONFIG_PATH,
        "gate_id": TRUST_ANCHOR_GATE_ID,
        "manual_gate": {
            "acknowledgement": MANUAL_LFS_ACKNOWLEDGEMENT,
            "job_context": "manual-hydrated-lfs-integrity",
            "lfs_payload_bytes": TOTAL_LFS_PAYLOAD_BYTES,
            "trigger": "workflow_dispatch",
        },
        "protected_attribute_control_paths": list(EXPECTED_ATTRIBUTE_CONTROL_PATHS),
        "protected_lfs_paths": list(PROTECTED_LFS_PATHS),
        "schema_version": 1,
        "trust_anchor": {
            "commit": TRUST_ANCHOR_COMMIT,
            "conclusion": "success",
            "hydrated_job_context": HYDRATED_JOB_CONTEXT,
            "hydrated_job_id": TRUST_ANCHOR_HYDRATED_JOB_ID,
            "tree": TRUST_ANCHOR_TREE,
            "workflow_run_id": TRUST_ANCHOR_WORKFLOW_RUN_ID,
        },
    }


def _load_canonical_object(payload: bytes, *, location: str) -> dict[str, Any]:
    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                _fail("DUPLICATE_KEY", f"{location}.{key}")
            result[key] = value
        return result

    try:
        value = json.loads(payload.decode("utf-8"), object_pairs_hook=unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RepositoryCIValidationError("INVALID_JSON", location) from exc
    if type(value) is not dict:
        _fail("NOT_OBJECT", location)
    if canonical_json_bytes(value) != payload:
        _fail("NOT_CANONICAL", location)
    return value


def load_inventory(payload: bytes) -> dict[str, Any]:
    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                _fail("INVENTORY_DUPLICATE_KEY", f"$.{key}")
            result[key] = value
        return result

    try:
        value = json.loads(payload.decode("utf-8"), object_pairs_hook=unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RepositoryCIValidationError("INVENTORY_INVALID_JSON", "$") from exc
    if type(value) is not dict:
        _fail("INVENTORY_NOT_OBJECT", "$")
    if canonical_json_bytes(value) != payload:
        _fail("INVENTORY_NOT_CANONICAL", "$")
    if value != expected_inventory():
        _fail("INVENTORY_MISMATCH", "$")
    return value


def load_trust_anchor(payload: bytes) -> dict[str, Any]:
    value = _load_canonical_object(payload, location="$.trust_anchor_contract")
    if value != expected_trust_anchor():
        _fail("TRUST_ANCHOR_CONTRACT_MISMATCH", "$.trust_anchor_contract")
    return value


def lfs_pointer_bytes(item: dict[str, Any]) -> bytes:
    return (
        "version https://git-lfs.github.com/spec/v1\n"
        f"oid {item['oid']}\n"
        f"size {item['size']}\n"
    ).encode("ascii")


def git_blob_oid(payload: bytes) -> str:
    header = f"blob {len(payload)}\0".encode("ascii")
    return "sha1:" + hashlib.sha1(header + payload).hexdigest()


def _safe_relative_path(relative: str) -> Path:
    if type(relative) is not str or "\\" in relative or ":" in relative:
        _fail("UNSAFE_REPOSITORY_PATH", f"$.path[{relative!r}]")
    logical = PurePosixPath(relative)
    if (
        logical.is_absolute()
        or not logical.parts
        or any(part in {"", ".", ".."} for part in logical.parts)
    ):
        _fail("UNSAFE_REPOSITORY_PATH", f"$.path[{relative!r}]")
    if logical.as_posix() != relative:
        _fail("NONCANONICAL_REPOSITORY_PATH", f"$.path[{relative!r}]")
    candidate = ROOT.joinpath(*logical.parts)
    resolved_root = ROOT.resolve()
    if not candidate.resolve().is_relative_to(resolved_root):
        _fail("REPOSITORY_PATH_ESCAPE", f"$.path[{relative!r}]")
    return candidate


def _run_git(*args: str, input_payload: bytes | None = None) -> bytes:
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        input=input_payload,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        command = " ".join(args[:3])
        _fail("GIT_COMMAND_FAILED", f"$.git[{command!r}]")
    return completed.stdout


def _git_blob(relative: str) -> bytes:
    _safe_relative_path(relative)
    return _run_git("cat-file", "blob", f"HEAD:{relative}")


def _git_object_id(relative: str) -> str:
    _safe_relative_path(relative)
    value = _run_git("rev-parse", f"HEAD:{relative}").decode("ascii").strip()
    if len(value) != 40 or any(
        character not in "0123456789abcdef" for character in value
    ):
        _fail("INVALID_GIT_OBJECT_ID", f"$.git[{relative!r}]")
    return "sha1:" + value


def _tracked_paths() -> tuple[str, ...]:
    raw = _run_git("ls-files", "-z")
    parts = raw.split(b"\0")
    if parts[-1] != b"":
        _fail("TRACKED_PATH_WIRE_INVALID", "$.git.ls_files")
    try:
        paths = tuple(part.decode("utf-8") for part in parts[:-1])
    except UnicodeDecodeError as exc:
        raise RepositoryCIValidationError(
            "TRACKED_PATH_NOT_UTF8", "$.git.ls_files"
        ) from exc
    if tuple(sorted(paths)) != paths or len(set(paths)) != len(paths):
        _fail("TRACKED_PATH_ORDER_INVALID", "$.git.ls_files")
    return paths


def _discover_lfs_paths(tracked_paths: tuple[str, ...]) -> tuple[str, ...]:
    request = b"\0".join(path.encode("utf-8") for path in tracked_paths) + b"\0"
    raw = _run_git(
        "check-attr", "--cached", "-z", "filter", "--stdin", input_payload=request
    )
    fields = raw.split(b"\0")
    if fields[-1] != b"" or (len(fields) - 1) % 3:
        _fail("GIT_ATTRIBUTE_WIRE_INVALID", "$.gitattributes.filter")
    lfs_paths: list[str] = []
    for index in range(0, len(fields) - 1, 3):
        path, attribute, value = fields[index : index + 3]
        if attribute != b"filter":
            _fail("GIT_ATTRIBUTE_NAME_INVALID", "$.gitattributes.filter")
        if value == b"lfs":
            try:
                lfs_paths.append(path.decode("utf-8"))
            except UnicodeDecodeError as exc:
                raise RepositoryCIValidationError(
                    "LFS_PATH_NOT_UTF8", "$.gitattributes.filter"
                ) from exc
    return tuple(lfs_paths)


def _validate_lfs_attributes(relative: str) -> None:
    raw = _run_git(
        "check-attr",
        "--cached",
        "-z",
        "filter",
        "diff",
        "merge",
        "text",
        "--",
        relative,
    )
    fields = raw.split(b"\0")
    if fields[-1] != b"" or len(fields) != 13:
        _fail("LFS_ATTRIBUTE_WIRE_INVALID", f"$.lfs_objects[{relative!r}]")
    observed: dict[str, str] = {}
    for index in range(0, 12, 3):
        path, attribute, value = fields[index : index + 3]
        if path.decode("utf-8") != relative:
            _fail("LFS_ATTRIBUTE_PATH_MISMATCH", f"$.lfs_objects[{relative!r}]")
        observed[attribute.decode("ascii")] = value.decode("ascii")
    if observed != {"diff": "lfs", "filter": "lfs", "merge": "lfs", "text": "unset"}:
        _fail("LFS_ATTRIBUTES_MISMATCH", f"$.lfs_objects[{relative!r}]")


def validate_exact_checkout(expected_head: str, *, base_commit: str) -> str:
    if re.fullmatch(r"[0-9a-f]{40}", expected_head) is None:
        _fail("EXPECTED_HEAD_INVALID", "$.exact_head_checkout.expected_head")
    if re.fullmatch(r"[0-9a-f]{40}", base_commit) is None:
        _fail("EXACT_CHECKOUT_BASE_INVALID", "$.exact_head_checkout.base_commit")
    actual_head = _run_git("rev-parse", "HEAD").decode("ascii").strip()
    if re.fullmatch(r"[0-9a-f]{40}", actual_head) is None:
        _fail("INVALID_HEAD", "$.git.head")
    if actual_head != expected_head:
        _fail("EXACT_CHECKOUT_HEAD_MISMATCH", "$.exact_head_checkout.expected_head")
    base_type = _run_git("cat-file", "-t", base_commit).decode("ascii").strip()
    if base_type != "commit":
        _fail("EXACT_CHECKOUT_BASE_NOT_COMMIT", "$.exact_head_checkout.base_commit")
    if _git_exit_code("merge-base", "--is-ancestor", base_commit, actual_head):
        _fail("EXACT_CHECKOUT_BASE_NOT_ANCESTOR", "$.exact_head_checkout.base_commit")
    return actual_head


def validate_git_metadata(inventory: dict[str, Any]) -> str:
    top_level = Path(
        _run_git("rev-parse", "--show-toplevel").decode("utf-8").strip()
    ).resolve()
    if top_level != ROOT.resolve():
        _fail("UNEXPECTED_REPOSITORY_ROOT", "$.git.top_level")
    head = _run_git("rev-parse", "HEAD").decode("ascii").strip()
    if len(head) != 40 or any(
        character not in "0123456789abcdef" for character in head
    ):
        _fail("INVALID_HEAD", "$.git.head")

    attributes = inventory["gitattributes"]
    attributes_payload = _git_blob(attributes["path"])
    if (
        len(attributes_payload) != attributes["bytes"]
        or "sha256:" + hashlib.sha256(attributes_payload).hexdigest()
        != attributes["sha256"]
        or git_blob_oid(attributes_payload) != attributes["blob_oid"]
        or _git_object_id(attributes["path"]) != attributes["blob_oid"]
    ):
        _fail("GITATTRIBUTES_RECEIPT_MISMATCH", "$.gitattributes")

    expected_paths = tuple(item["path"] for item in inventory["lfs_objects"])
    tracked_paths = _tracked_paths()
    if _discover_lfs_paths(tracked_paths) != expected_paths:
        _fail("LFS_TRACKED_PATH_INVENTORY_MISMATCH", "$.lfs_objects")
    for item in inventory["lfs_objects"]:
        pointer = _git_blob(item["path"])
        if (
            pointer != lfs_pointer_bytes(item)
            or len(pointer) != item["pointer_bytes"]
            or git_blob_oid(pointer) != item["pointer_git_blob_oid"]
            or _git_object_id(item["path"]) != item["pointer_git_blob_oid"]
        ):
            _fail("LFS_POINTER_MISMATCH", f"$.lfs_objects[{item['path']!r}]")
        _validate_lfs_attributes(item["path"])
    return head


def _git_exit_code(*args: str) -> int:
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode not in {0, 1}:
        command = " ".join(args[:3])
        _fail("GIT_COMMAND_FAILED", f"$.git[{command!r}]")
    return completed.returncode


def _attribute_control_paths(tracked_paths: tuple[str, ...]) -> tuple[str, ...]:
    controls = tuple(
        path
        for path in tracked_paths
        if PurePosixPath(path).name.casefold() == ".gitattributes"
    )
    if controls != EXPECTED_ATTRIBUTE_CONTROL_PATHS:
        _fail("GITATTRIBUTES_PATH_SET_DRIFT", "$.protected_attribute_control_paths")
    return controls


def validate_lfs_control_paths(tracked_paths: tuple[str, ...]) -> tuple[str, ...]:
    attribute_controls = _attribute_control_paths(tracked_paths)
    if any(
        PurePosixPath(path).name.casefold() == FORBIDDEN_LFS_CONFIG_PATH
        for path in tracked_paths
    ):
        _fail("LFS_CONFIG_FORBIDDEN", "$.forbidden_lfs_config_path")
    return attribute_controls


def validate_trust_anchor(
    contract: dict[str, Any], *, current_head: str
) -> dict[str, Any]:
    anchor = contract["trust_anchor"]
    anchor_commit = anchor["commit"]
    anchor_type = _run_git("cat-file", "-t", anchor_commit).decode("ascii").strip()
    if anchor_type != "commit":
        _fail("TRUST_ANCHOR_NOT_COMMIT", "$.trust_anchor.commit")
    anchor_tree = (
        _run_git("rev-parse", f"{anchor_commit}^{{tree}}").decode("ascii").strip()
    )
    if anchor_tree != anchor["tree"]:
        _fail("TRUST_ANCHOR_TREE_MISMATCH", "$.trust_anchor.tree")
    if _git_exit_code("merge-base", "--is-ancestor", anchor_commit, current_head):
        _fail("TRUST_ANCHOR_NOT_ANCESTOR", "$.trust_anchor.commit")

    tracked_paths = _tracked_paths()
    attribute_controls = validate_lfs_control_paths(tracked_paths)
    if _git_exit_code(
        "diff",
        "--quiet",
        "--no-ext-diff",
        "--no-renames",
        anchor_commit,
        current_head,
        "--",
        *contract["protected_lfs_paths"],
        FORBIDDEN_LFS_CONFIG_PATH,
    ):
        _fail("PROTECTED_LFS_PATH_DRIFT", "$.protected_lfs_paths")

    return {
        "attribute_control_paths": list(attribute_controls),
        "content_identity_inherited": True,
        "current_hydration_verified": False,
        "current_payload_integrity_verified": False,
        "full_integrity_verified": False,
        "lfs_payload_bytes_read": 0,
        "protected_lfs_paths_unchanged": True,
        "remote_availability_verified": False,
        "trust_anchor_commit": anchor_commit,
        "trust_anchor_hydrated_job_id": anchor["hydrated_job_id"],
        "trust_anchor_tree": anchor_tree,
        "trust_anchor_workflow_run_id": anchor["workflow_run_id"],
    }


def validate_pointer_worktree(inventory: dict[str, Any]) -> int:
    pointer_bytes_read = 0
    for item in inventory["lfs_objects"]:
        path = _safe_relative_path(item["path"])
        if not path.is_file() or path.is_symlink():
            _fail("UNSAFE_OR_MISSING_POINTER", f"$.lfs_objects[{item['path']!r}]")
        if path.stat().st_size != item["pointer_bytes"]:
            _fail("HYDRATED_PAYLOAD_FORBIDDEN", f"$.lfs_objects[{item['path']!r}]")
        payload = path.read_bytes()
        if payload != lfs_pointer_bytes(item):
            _fail("WORKTREE_POINTER_MISMATCH", f"$.lfs_objects[{item['path']!r}]")
        pointer_bytes_read += len(payload)
    return pointer_bytes_read


def validate_hydrated_worktree(inventory: dict[str, Any]) -> tuple[int, int]:
    payloads_read = 0
    payload_bytes_read = 0
    for item in inventory["lfs_objects"]:
        path = _safe_relative_path(item["path"])
        if not path.is_file() or path.is_symlink():
            _fail("UNSAFE_OR_MISSING_PAYLOAD", f"$.lfs_objects[{item['path']!r}]")
        if path.stat().st_size != item["size"]:
            _fail("LFS_PAYLOAD_SIZE_MISMATCH", f"$.lfs_objects[{item['path']!r}]")
        digest = hashlib.sha256()
        observed_bytes = 0
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
                observed_bytes += len(chunk)
        if (
            observed_bytes != item["size"]
            or "sha256:" + digest.hexdigest() != item["oid"]
        ):
            _fail("LFS_PAYLOAD_DIGEST_MISMATCH", f"$.lfs_objects[{item['path']!r}]")
        payloads_read += 1
        payload_bytes_read += observed_bytes
    if payload_bytes_read != inventory["total_lfs_payload_bytes"]:
        _fail("LFS_PAYLOAD_TOTAL_MISMATCH", "$.total_lfs_payload_bytes")
    return payloads_read, payload_bytes_read


def compile_tracked_python() -> int:
    raw = _run_git("ls-files", "-z", "--", "*.py")
    fields = raw.split(b"\0")
    if fields[-1] != b"":
        _fail("PYTHON_PATH_WIRE_INVALID", "$.tracked_python")
    paths = tuple(field.decode("utf-8") for field in fields[:-1])
    if not paths or tuple(sorted(paths)) != paths or len(set(paths)) != len(paths):
        _fail("PYTHON_PATH_INVENTORY_INVALID", "$.tracked_python")
    with tempfile.TemporaryDirectory(prefix="repository-ci-pycompile-") as temporary:
        target_root = Path(temporary)
        for relative in paths:
            source = _safe_relative_path(relative)
            if not source.is_file() or source.is_symlink():
                _fail("UNSAFE_OR_MISSING_PYTHON", f"$.tracked_python[{relative!r}]")
            target = target_root / (
                hashlib.sha256(relative.encode("utf-8")).hexdigest() + ".pyc"
            )
            try:
                py_compile.compile(
                    str(source),
                    cfile=str(target),
                    dfile=relative,
                    doraise=True,
                )
            except py_compile.PyCompileError as exc:
                raise RepositoryCIValidationError(
                    "PYTHON_COMPILE_FAILED", f"$.tracked_python[{relative!r}]"
                ) from exc
    return len(paths)


@contextmanager
def _core_test_subprocess_environment() -> Iterator[None]:
    previous = os.environ.get("PYTHONPATH")
    had_previous = "PYTHONPATH" in os.environ
    os.environ["PYTHONPATH"] = str(SRC)
    try:
        yield
    finally:
        if had_previous:
            assert previous is not None
            os.environ["PYTHONPATH"] = previous
        else:
            os.environ.pop("PYTHONPATH", None)


def run_core_tests() -> tuple[int, int]:
    sys.path.insert(0, str(SRC))
    sys.path.insert(0, str(ROOT))
    suite = unittest.defaultTestLoader.loadTestsFromNames(CORE_TEST_MODULES)
    if suite.countTestCases() != CORE_TEST_COUNT:
        _fail("CORE_TEST_COUNT_MISMATCH", "$.pointer_gate.stdlib_test_count")
    with _core_test_subprocess_environment():
        result = unittest.TextTestRunner(stream=sys.stderr, verbosity=1).run(suite)
    if not result.wasSuccessful() or result.testsRun != CORE_TEST_COUNT:
        _fail("CORE_TESTS_FAILED", "$.pointer_gate.stdlib_test_modules")
    return result.testsRun, len(result.skipped)


def diagnostic_v2_test_plan(
    tracked_paths: tuple[str, ...],
) -> tuple[str, tuple[str, ...], int]:
    tracked_path_set = set(tracked_paths)
    implementation_paths = set(DIAGNOSTIC_V2_IMPLEMENTATION_PATHS)
    present_paths = implementation_paths & tracked_path_set
    if not present_paths:
        state = "protocol_only"
        modules: tuple[str, ...] = (DIAGNOSTIC_V2_PROTOCOL_TEST_MODULE,)
        expected_count = DIAGNOSTIC_V2_PROTOCOL_ONLY_TEST_COUNT
    elif present_paths == implementation_paths:
        state = "implementation_complete"
        modules = (
            DIAGNOSTIC_V2_PROTOCOL_TEST_MODULE,
            DIAGNOSTIC_V2_RESULT_TEST_MODULE,
        )
        expected_count = DIAGNOSTIC_V2_IMPLEMENTATION_TEST_COUNT
    else:
        _fail("DIAGNOSTIC_V2_IMPLEMENTATION_TOPOLOGY_PARTIAL", "$.diagnostic_v2")
    return state, modules, expected_count


def run_diagnostic_v2_focused_tests() -> tuple[str, int, int]:
    state, modules, expected_count = diagnostic_v2_test_plan(_tracked_paths())
    if state == "implementation_complete":
        for relative in DIAGNOSTIC_V2_IMPLEMENTATION_PATHS:
            path = _safe_relative_path(relative)
            if not path.is_file() or path.is_symlink():
                _fail(
                    "DIAGNOSTIC_V2_IMPLEMENTATION_PATH_UNSAFE",
                    f"$.path[{relative!r}]",
                )

    sys.path.insert(0, str(SRC))
    sys.path.insert(0, str(ROOT))
    if state == "implementation_complete":
        protocol_count = unittest.defaultTestLoader.loadTestsFromName(
            DIAGNOSTIC_V2_PROTOCOL_TEST_MODULE
        ).countTestCases()
        if protocol_count != DIAGNOSTIC_V2_IMPLEMENTATION_PROTOCOL_TEST_COUNT:
            _fail(
                "DIAGNOSTIC_V2_PROTOCOL_TEST_COUNT_MISMATCH",
                "$.diagnostic_v2.protocol_test_count",
            )
    suite = unittest.defaultTestLoader.loadTestsFromNames(modules)
    if suite.countTestCases() != expected_count:
        _fail("DIAGNOSTIC_V2_TEST_COUNT_MISMATCH", "$.diagnostic_v2.test_count")
    with _core_test_subprocess_environment():
        result = unittest.TextTestRunner(stream=sys.stderr, verbosity=1).run(suite)
    if not result.wasSuccessful() or result.testsRun != expected_count:
        _fail("DIAGNOSTIC_V2_TESTS_FAILED", "$.diagnostic_v2.test_modules")
    return state, result.testsRun, len(result.skipped)


def _fail(code: str, location: str) -> NoReturn:
    raise RepositoryCIValidationError(code, location)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=(
            "exact-checkout",
            "pointer",
            "pointer-metadata",
            "trusted-anchor",
            "diagnostic-v2-focused",
            "hydrated-lfs",
        ),
        default="pointer",
    )
    parser.add_argument("--expected-head")
    arguments = parser.parse_args(argv)

    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    sys.dont_write_bytecode = True
    if arguments.mode == "exact-checkout":
        if arguments.expected_head is None:
            _fail("EXPECTED_HEAD_REQUIRED", "$.exact_head_checkout.expected_head")
        contract = load_trust_anchor(TRUST_ANCHOR_PATH.read_bytes())
        policy = contract["exact_head_checkout"]
        head = validate_exact_checkout(
            arguments.expected_head, base_commit=policy["base_commit"]
        )
        summary = {
            "base_commit": policy["base_commit"],
            "expected_head": arguments.expected_head,
            "gate_id": policy["gate_id"],
            "git_head": head,
            "persist_credentials": policy["persist_credentials"],
            "scope": policy["scope"],
            "valid": True,
        }
        sys.stdout.buffer.write(canonical_json_bytes(summary))
        return 0
    if arguments.expected_head is not None:
        _fail("EXPECTED_HEAD_UNEXPECTED", "$.exact_head_checkout.expected_head")
    version = (sys.version_info.major, sys.version_info.minor)
    if version not in SUPPORTED_PYTHON_MINORS:
        _fail("UNSUPPORTED_PYTHON", "$.python")

    inventory = load_inventory(INVENTORY_PATH.read_bytes())
    head = validate_git_metadata(inventory)
    if arguments.mode in {"pointer", "pointer-metadata"}:
        pointer_bytes_read = validate_pointer_worktree(inventory)
        summary = {
            "full_integrity_verified": False,
            "gate_id": GATE_ID,
            "git_head": head,
            "lfs_object_count": len(inventory["lfs_objects"]),
            "lfs_payload_bytes_read": 0,
            "lfs_payloads_read": 0,
            "pointer_bytes_read": pointer_bytes_read,
            "python": sys.version.split()[0],
            "scope": (
                POINTER_SCOPE if arguments.mode == "pointer" else POINTER_METADATA_SCOPE
            ),
            "valid": True,
        }
        if arguments.mode == "pointer":
            python_files_compiled = compile_tracked_python()
            tests_run, tests_skipped = run_core_tests()
            pointer_bytes_after_tests = validate_pointer_worktree(inventory)
            if pointer_bytes_after_tests != pointer_bytes_read:
                _fail("POINTER_BYTE_COUNT_DRIFT", "$.pointer_gate")
            summary.update(
                {
                    "python_files_compiled": python_files_compiled,
                    "stdlib_core_tests_run": tests_run,
                    "stdlib_core_tests_skipped": tests_skipped,
                }
            )
    elif arguments.mode == "trusted-anchor":
        contract = load_trust_anchor(TRUST_ANCHOR_PATH.read_bytes())
        pointer_bytes_read = validate_pointer_worktree(inventory)
        inherited = validate_trust_anchor(contract, current_head=head)
        pointer_bytes_after = validate_pointer_worktree(inventory)
        if pointer_bytes_after != pointer_bytes_read:
            _fail("POINTER_BYTE_COUNT_DRIFT", "$.automatic_gate")
        summary = {
            **inherited,
            "gate_id": TRUST_ANCHOR_GATE_ID,
            "git_head": head,
            "lfs_object_count": len(inventory["lfs_objects"]),
            "lfs_payloads_read": 0,
            "pointer_bytes_read": pointer_bytes_read,
            "python": sys.version.split()[0],
            "scope": contract["automatic_gate"]["scope"],
            "valid": True,
        }
    elif arguments.mode == "diagnostic-v2-focused":
        load_trust_anchor(TRUST_ANCHOR_PATH.read_bytes())
        pointer_bytes_read = validate_pointer_worktree(inventory)
        state, tests_run, tests_skipped = run_diagnostic_v2_focused_tests()
        pointer_bytes_after = validate_pointer_worktree(inventory)
        if pointer_bytes_after != pointer_bytes_read:
            _fail("POINTER_BYTE_COUNT_DRIFT", "$.diagnostic_v2_focused_gate")
        summary = {
            "diagnostic_v2_state": state,
            "focused_tests_run": tests_run,
            "focused_tests_skipped": tests_skipped,
            "full_integrity_verified": False,
            "gate_id": TRUST_ANCHOR_GATE_ID,
            "git_head": head,
            "lfs_object_count": len(inventory["lfs_objects"]),
            "lfs_payload_bytes_read": 0,
            "lfs_payloads_read": 0,
            "pointer_bytes_read": pointer_bytes_read,
            "python": sys.version.split()[0],
            "scope": "diagnostic_v2_focused_pointer_only",
            "valid": True,
        }
    else:
        payloads_read, payload_bytes_read = validate_hydrated_worktree(inventory)
        summary = {
            "full_integrity_verified": False,
            "gate_id": GATE_ID,
            "git_head": head,
            "lfs_object_count": len(inventory["lfs_objects"]),
            "lfs_payload_bytes_read": payload_bytes_read,
            "lfs_payloads_read": payloads_read,
            "payload_integrity_verified": True,
            "python": sys.version.split()[0],
            "scope": HYDRATED_SCOPE,
            "valid": True,
        }
    sys.stdout.buffer.write(canonical_json_bytes(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
