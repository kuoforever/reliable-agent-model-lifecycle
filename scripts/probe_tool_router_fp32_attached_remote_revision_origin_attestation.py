"""Collect one fixed remote revision-origin attestation observation."""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
import re
import ssl
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, NoReturn


sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fullcycle_bridge import (  # noqa: E402
    tool_router_fp32_attached_remote_revision_origin_attestation as contract,
)


RESULT_FILENAME = (
    "fc-mvp-001-fp32-attached-remote-revision-origin-attestation-v1.json"
)
MAX_HTTP_BYTES = 4 * 1024 * 1024
MAX_LOCAL_FILE_BYTES = 16 * 1024 * 1024
REPARSE_POINT_ATTRIBUTE = 0x400
GIT_COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}")


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Reject every redirect so authority endpoints cannot silently change."""

    def redirect_request(
        self,
        request: urllib.request.Request,
        file_pointer: Any,
        code: int,
        message: str,
        headers: http.client.HTTPMessage,
        new_url: str,
    ) -> NoReturn:
        del request, file_pointer, message, headers
        raise RuntimeError(f"unexpected HTTP redirect {code} to {new_url!r}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preregistration", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--base-model-root", type=Path, required=True)
    parser.add_argument("--freeze-commit", required=True)
    parser.add_argument("--result-output", type=Path, required=True)
    parser.add_argument("--plan", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run(args)
    if result.get("plan_only") is True:
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 0
    print(
        json.dumps(
            {
                "classification": result["classification"],
                "formal_gate_passed": result["formal_gate_passed"],
                "remote_revision_origin_attested": result["derived_claims"][
                    "remote_revision_origin_attested"
                ],
                "runtime_eligible": False,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


def run(
    args: argparse.Namespace,
    *,
    request_json: Any | None = None,
) -> dict[str, Any]:
    """Collect fixed authority projections, recompute evidence, then write once."""

    request_json = _request_json if request_json is None else request_json
    repository_root = _resolve_repository_root(args.repository_root)
    preregistration_path = _resolve_input_path(
        repository_root, args.preregistration, "preregistration"
    )
    loaded = contract.load_and_validate_preregistration(preregistration_path)
    freeze_commit = _validate_git_commit(args.freeze_commit, "freeze commit")
    result_output = _resolve_result_output(repository_root, args.result_output)
    base_model_root = _resolve_base_model_root(args.base_model_root)
    _require_commit_exists(repository_root, freeze_commit)
    _require_head_matches(repository_root, freeze_commit)

    if args.plan:
        if os.path.lexists(result_output):
            raise RuntimeError("result output already exists")
        return {
            "plan_only": True,
            "gate_id": contract.GATE_ID,
            "freeze_commit": freeze_commit,
            "fixed_https_requests": 5,
            "network_used": False,
            "model_or_adapter_lfs_download": False,
            "model_execution": False,
            "large_lfs_payload_bytes_read": 0,
            "result_output_role": "direct_baseline_child",
            "remote_revision_origin_attested": False,
        }

    if os.path.lexists(result_output):
        raise RuntimeError("result output already exists")
    source_lineage = loaded.data["source_lineage"]
    manifest_payload = _git_blob(
        repository_root, freeze_commit, source_lineage["manifest"]["path"]
    )
    reproducibility_payload = _git_blob(
        repository_root,
        freeze_commit,
        source_lineage["reproducibility_evidence"]["path"],
    )
    protocol_source_payloads = {
        name: _git_blob(repository_root, freeze_commit, record["path"])
        for name, record in source_lineage["protocol_sources"].items()
    }

    authority = loaded.data["authority_contract"]
    github_expected = authority["github"]
    github_repository_raw = request_json(
        method="GET",
        url=(
            f"{contract.GITHUB_API_BASE}/repos/{contract.GITHUB_REPOSITORY}"
        ),
        body=None,
        headers=_github_headers(),
    )
    github_commit_raw = request_json(
        method="GET",
        url=(
            f"{contract.GITHUB_API_BASE}/repos/{contract.GITHUB_REPOSITORY}/"
            f"git/commits/{contract.GITHUB_PACKAGE_COMMIT}"
        ),
        body=None,
        headers=_github_headers(),
    )
    github_tree_raw = request_json(
        method="GET",
        url=(
            f"{contract.GITHUB_API_BASE}/repos/{contract.GITHUB_REPOSITORY}/"
            f"git/trees/{contract.GITHUB_PACKAGE_TREE}?recursive=1"
        ),
        body=None,
        headers=_github_headers(),
    )
    lfs_body = contract.canonical_json_bytes(
        {
            "operation": "download",
            "transfers": ["basic"],
            "ref": {"name": contract.GITHUB_PACKAGE_COMMIT},
            "objects": [
                {
                    "oid": contract.ADAPTER_LFS_OID.removeprefix("sha256:"),
                    "size": contract.ADAPTER_LFS_BYTES,
                }
            ],
            "hash_algo": "sha256",
        }
    )
    github_lfs_raw = request_json(
        method="POST",
        url=contract.GITHUB_LFS_BATCH_ENDPOINT,
        body=lfs_body,
        headers={
            "Accept": "application/vnd.git-lfs+json",
            "Content-Type": "application/vnd.git-lfs+json",
            "User-Agent": "reliable-agent-model-lifecycle-origin-attestation/1",
        },
    )
    hf_repo_path = urllib.parse.quote(contract.HUGGINGFACE_REPOSITORY, safe="/")
    huggingface_raw = request_json(
        method="GET",
        url=(
            f"{contract.HUGGINGFACE_API_BASE}/api/models/{hf_repo_path}/revision/"
            f"{contract.HUGGINGFACE_REVISION}?blobs=true"
        ),
        body=None,
        headers={
            "Accept": "application/json",
            "User-Agent": "reliable-agent-model-lifecycle-origin-attestation/1",
        },
    )

    observations = {
        "github": {
            "api_base": contract.GITHUB_API_BASE,
            "repository": _project_github_repository(github_repository_raw),
            "commit": _project_github_commit(github_commit_raw),
            "tree": _project_github_tree(
                github_tree_raw,
                selected_paths={
                    item["path"] for item in github_expected["tree"]["selected_entries"]
                },
            ),
            "adapter_lfs": _project_github_lfs(github_lfs_raw),
            "content_bindings": _collect_github_content_bindings(repository_root),
        },
        "huggingface": {
            "api_base": contract.HUGGINGFACE_API_BASE,
            "repository": _project_huggingface_repository(huggingface_raw),
            "revision": contract.HUGGINGFACE_REVISION,
            "full_sibling_count": len(_list(huggingface_raw.get("siblings"), "siblings")),
            "remote_files": _project_huggingface_files(huggingface_raw),
            "content_bindings": _collect_huggingface_content_bindings(
                base_model_root, huggingface_raw
            ),
        },
    }
    observed_at_utc = (
        datetime.now(timezone.utc).isoformat(timespec="microseconds").replace(
            "+00:00", "Z"
        )
    )
    evidence = contract.build_origin_attestation_evidence(
        loaded.data,
        preregistration_sha256=loaded.sha256,
        protocol_freeze_commit=freeze_commit,
        observed_at_utc=observed_at_utc,
        observations=observations,
        manifest_payload=manifest_payload,
        reproducibility_evidence_payload=reproducibility_payload,
        protocol_source_payloads=protocol_source_payloads,
    )
    _require_safe_final_evidence(evidence)
    payload = contract.artifact_json_bytes(evidence)
    _write_exclusive(result_output, payload)
    if result_output.read_bytes() != payload:
        raise RuntimeError("result output readback mismatch")
    return evidence


def _request_json(
    *,
    method: str,
    url: str,
    body: bytes | None,
    headers: Mapping[str, str],
) -> dict[str, Any]:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise RuntimeError("authority request must use an explicit HTTPS host")
    context = ssl.create_default_context()
    opener = urllib.request.build_opener(
        NoRedirectHandler(), urllib.request.HTTPSHandler(context=context)
    )
    request = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers=dict(headers),
    )
    try:
        with opener.open(request, timeout=30) as response:
            if response.status != 200 or response.geturl() != url:
                raise RuntimeError("authority response status or final URL mismatch")
            payload = response.read(MAX_HTTP_BYTES + 1)
    except (urllib.error.URLError, http.client.IncompleteRead, OSError) as exc:
        raise RuntimeError(f"authority request failed: {exc}") from exc
    if len(payload) > MAX_HTTP_BYTES:
        raise RuntimeError("authority response exceeded the byte cap")
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"authority response was not valid UTF-8 JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise RuntimeError("authority response root must be an object")
    return value


def _github_headers() -> dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "reliable-agent-model-lifecycle-origin-attestation/1",
    }


def _project_github_repository(value: Mapping[str, Any]) -> dict[str, Any]:
    owner = _mapping(value.get("owner"), "github repository owner")
    return {
        "id": value.get("id"),
        "node_id": value.get("node_id"),
        "name": value.get("name"),
        "full_name": value.get("full_name"),
        "owner": {
            "login": owner.get("login"),
            "id": owner.get("id"),
            "node_id": owner.get("node_id"),
            "type": owner.get("type"),
        },
        "private": value.get("private"),
        "html_url": value.get("html_url"),
        "clone_url": value.get("clone_url"),
        "ssh_url": value.get("ssh_url"),
        "default_branch": value.get("default_branch"),
        "archived": value.get("archived"),
        "disabled": value.get("disabled"),
        "visibility": value.get("visibility"),
    }


def _project_github_commit(value: Mapping[str, Any]) -> dict[str, Any]:
    tree = _mapping(value.get("tree"), "github commit tree")
    parents = _list(value.get("parents"), "github commit parents")
    verification = _mapping(value.get("verification"), "github verification")
    return {
        "sha": value.get("sha"),
        "tree": tree.get("sha"),
        "parents": [_mapping(item, "github parent").get("sha") for item in parents],
        "verification": {
            "verified": verification.get("verified"),
            "reason": verification.get("reason"),
            "signature": verification.get("signature"),
            "payload": verification.get("payload"),
            "verified_at": verification.get("verified_at"),
        },
    }


def _project_github_tree(
    value: Mapping[str, Any], *, selected_paths: set[str]
) -> dict[str, Any]:
    entries = _list(value.get("tree"), "github tree entries")
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in entries:
        item = _mapping(raw, "github tree entry")
        path = item.get("path")
        if path not in selected_paths:
            continue
        if not isinstance(path, str) or path in seen:
            raise RuntimeError("duplicate or invalid selected GitHub tree path")
        seen.add(path)
        selected.append(
            {
                "path": path,
                "mode": item.get("mode"),
                "type": item.get("type"),
                "sha": item.get("sha"),
                "size": item.get("size"),
            }
        )
    if seen != selected_paths:
        raise RuntimeError("GitHub tree did not contain every selected package path")
    selected.sort(key=lambda item: str(item["path"]))
    return {
        "sha": value.get("sha"),
        "full_entry_count": len(entries),
        "truncated": value.get("truncated"),
        "selected_entries": selected,
    }


def _project_github_lfs(value: Mapping[str, Any]) -> dict[str, Any]:
    objects = _list(value.get("objects"), "GitHub LFS objects")
    if len(objects) != 1:
        raise RuntimeError("GitHub LFS response must contain exactly one object")
    item = _mapping(objects[0], "GitHub LFS object")
    actions = _mapping(item.get("actions"), "GitHub LFS actions")
    download = _mapping(actions.get("download"), "GitHub LFS download action")
    href = download.get("href")
    if not isinstance(href, str):
        raise RuntimeError("GitHub LFS download action is missing href")
    parsed = urllib.parse.urlsplit(href)
    oid = item.get("oid")
    return {
        "batch_endpoint": contract.GITHUB_LFS_BATCH_ENDPOINT,
        "ref": contract.GITHUB_PACKAGE_COMMIT,
        "oid": oid,
        "size": item.get("size"),
        "status": 200,
        "response_media_type": "application/json",
        "error": item.get("error"),
        "action_keys": sorted(actions),
        "download_scheme": parsed.scheme,
        "download_host": parsed.hostname,
        "download_path_ends_with_oid": (
            isinstance(oid, str) and parsed.path.endswith(oid)
        ),
        "signed_query_present": bool(parsed.query),
        "signed_query_recorded": False,
    }


def _project_huggingface_repository(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": value.get("id"),
        "model_id": value.get("modelId"),
        "author": value.get("author"),
        "sha": value.get("sha"),
        "private": value.get("private"),
        "gated": value.get("gated"),
        "disabled": value.get("disabled"),
    }


def _project_huggingface_files(value: Mapping[str, Any]) -> list[dict[str, Any]]:
    siblings = _list(value.get("siblings"), "Hugging Face siblings")
    result: list[dict[str, Any]] = []
    for raw in siblings:
        item = _mapping(raw, "Hugging Face sibling")
        lfs_raw = item.get("lfs")
        lfs = None
        if lfs_raw is not None:
            lfs_item = _mapping(lfs_raw, "Hugging Face LFS metadata")
            lfs = {
                "pointer_size": lfs_item.get("pointerSize"),
                "sha256": lfs_item.get("sha256"),
                "size": lfs_item.get("size"),
            }
        result.append(
            {
                "rfilename": item.get("rfilename"),
                "size": item.get("size"),
                "blob_id": item.get("blobId"),
                "lfs": lfs,
            }
        )
    result.sort(key=lambda item: str(item["rfilename"]))
    return result


def _collect_github_content_bindings(repository_root: Path) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for expected in contract.GITHUB_CONTENT_BINDINGS:
        payload = _git_blob(
            repository_root, contract.GITHUB_PACKAGE_COMMIT, expected["path"]
        )
        blob_sha1 = contract.git_blob_sha1(payload)
        if expected["binding_kind"] == "git_blob":
            item = {
                "path": expected["path"],
                "role": expected["role"],
                "binding_kind": "git_blob",
                "bytes": len(payload),
                "sha256": "sha256:" + hashlib.sha256(payload).hexdigest(),
                "git_blob_sha1": blob_sha1,
            }
        else:
            pointer = _parse_lfs_pointer(payload)
            item = {
                "path": expected["path"],
                "role": expected["role"],
                "binding_kind": "git_lfs_pointer",
                "pointer_bytes": len(payload),
                "pointer_sha256": (
                    "sha256:" + hashlib.sha256(payload).hexdigest()
                ),
                "git_blob_sha1": blob_sha1,
                "lfs_oid": pointer["oid"],
                "lfs_bytes": pointer["size"],
            }
        result.append(item)
    return result


def _collect_huggingface_content_bindings(
    base_model_root: Path, remote: Mapping[str, Any]
) -> list[dict[str, Any]]:
    remote_files = {
        item["rfilename"]: item for item in _project_huggingface_files(remote)
    }
    result: list[dict[str, Any]] = []
    for expected in contract.HUGGINGFACE_FILES:
        if expected["package_component"] is not True:
            continue
        if expected["binding_kind"] == "git_blob":
            payload = _read_safe_local_file(
                base_model_root, str(expected["path"]), MAX_LOCAL_FILE_BYTES
            )
            item = {
                "path": expected["path"],
                "package_component": True,
                "binding_kind": "git_blob",
                "bytes": len(payload),
                "sha256": "sha256:" + hashlib.sha256(payload).hexdigest(),
                "git_blob_sha1": contract.git_blob_sha1(payload),
            }
        else:
            remote_item = remote_files.get(expected["path"])
            if not isinstance(remote_item, Mapping):
                raise RuntimeError("Hugging Face LFS package file is missing")
            lfs = _mapping(remote_item.get("lfs"), "Hugging Face package LFS")
            item = {
                "path": expected["path"],
                "package_component": True,
                "binding_kind": "git_lfs",
                "bytes": lfs.get("size"),
                "sha256": "sha256:" + str(lfs.get("sha256")),
                "git_blob_sha1": remote_item.get("blob_id"),
                "lfs_pointer_bytes": lfs.get("pointer_size"),
            }
        result.append(item)
    return result


def _parse_lfs_pointer(payload: bytes) -> dict[str, Any]:
    try:
        text = payload.decode("ascii")
    except UnicodeDecodeError as exc:
        raise RuntimeError("Git LFS pointer was not ASCII") from exc
    lines = text.splitlines()
    if (
        len(lines) != 3
        or lines[0] != "version https://git-lfs.github.com/spec/v1"
        or not lines[1].startswith("oid sha256:")
        or not lines[2].startswith("size ")
    ):
        raise RuntimeError("Git LFS pointer schema mismatch")
    oid = lines[1].removeprefix("oid ")
    try:
        size = int(lines[2].removeprefix("size "))
    except ValueError as exc:
        raise RuntimeError("Git LFS pointer size was not an integer") from exc
    return {"oid": oid, "size": size}


def _resolve_repository_root(path: Path) -> Path:
    resolved = path.resolve(strict=True)
    if not resolved.is_dir() or not (resolved / ".git").exists():
        raise RuntimeError("repository root is not a Git worktree")
    return resolved


def _resolve_base_model_root(path: Path) -> Path:
    resolved = path.resolve(strict=True)
    if not resolved.is_dir() or resolved.is_symlink() or _is_reparse_point(resolved):
        raise RuntimeError("base model root is not a safe regular directory")
    return resolved


def _resolve_input_path(root: Path, path: Path, label: str) -> Path:
    candidate = path if path.is_absolute() else root / path
    resolved = candidate.resolve(strict=True)
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise RuntimeError(f"{label} escaped the repository root")
    return resolved


def _resolve_result_output(root: Path, path: Path) -> Path:
    candidate = path if path.is_absolute() else root / path
    resolved = candidate.resolve(strict=False)
    expected_parent = (root / "baseline").resolve(strict=True)
    if (
        resolved.parent != expected_parent
        or resolved.name != RESULT_FILENAME
        or resolved.suffix != ".json"
    ):
        raise RuntimeError("result output must be the fixed direct baseline child")
    return resolved


def _read_safe_local_file(root: Path, relative: str, maximum: int) -> bytes:
    pure = PurePosixPath(relative)
    if (
        pure.is_absolute()
        or str(pure) != relative
        or any(part in {"", ".", ".."} for part in pure.parts)
    ):
        raise RuntimeError("unsafe local package relative path")
    candidate = root.joinpath(*pure.parts)
    if candidate.is_symlink() or _is_reparse_point(candidate):
        raise RuntimeError("local package file is a symlink or reparse point")
    resolved = candidate.resolve(strict=True)
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise RuntimeError("local package file escaped its root")
    metadata = resolved.stat()
    if metadata.st_size > maximum:
        raise RuntimeError("local package file exceeded the read cap")
    if metadata.st_nlink != 1:
        raise RuntimeError("local package file has multiple hard links")
    return resolved.read_bytes()


def _is_reparse_point(path: Path) -> bool:
    try:
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
    except OSError:
        return False
    return bool(attributes & REPARSE_POINT_ATTRIBUTE)


def _git_blob(repository_root: Path, commit: str, relative_path: str) -> bytes:
    pure = PurePosixPath(relative_path)
    if (
        pure.is_absolute()
        or str(pure) != relative_path
        or any(part in {"", ".", ".."} for part in pure.parts)
    ):
        raise RuntimeError("unsafe Git blob relative path")
    result = subprocess.run(
        ["git", "cat-file", "blob", f"{commit}:{relative_path}"],
        cwd=repository_root,
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError("required Git blob could not be read")
    return result.stdout


def _require_commit_exists(repository_root: Path, commit: str) -> None:
    result = subprocess.run(
        ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
        cwd=repository_root,
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError("protocol freeze commit is missing")


def _require_head_matches(repository_root: Path, freeze_commit: str) -> None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    )
    if result.stdout.strip() != freeze_commit:
        raise RuntimeError("repository HEAD does not match protocol freeze commit")


def _validate_git_commit(value: object, label: str) -> str:
    if not isinstance(value, str) or GIT_COMMIT_PATTERN.fullmatch(value) is None:
        raise RuntimeError(f"invalid {label}")
    return value


def _write_exclusive(path: Path, payload: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        try:
            path.unlink(missing_ok=True)
        finally:
            raise


def _require_safe_final_evidence(value: Mapping[str, Any]) -> None:
    if value.get("formal_gate_passed") is not True:
        raise RuntimeError("formal gate did not pass")
    derived = _mapping(value.get("derived_claims"), "derived claims")
    if derived.get("remote_revision_origin_attested") is not True:
        raise RuntimeError("remote revision origin was not attested")
    for name in (
        "offline_artifact_eligible",
        "portable_package_eligible",
        "preferred_offline_candidate",
        "serving_readiness_established",
        "artifact_promotion_allowed",
        "merged_artifact_allowed",
        "runtime_eligible",
    ):
        if derived.get(name) is not False:
            raise RuntimeError(f"unsafe downstream eligibility flag: {name}")
    if value.get("runtime_eligible") is not False:
        raise RuntimeError("unsafe Runtime eligibility")


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise RuntimeError(f"{label} must be an object")
    return dict(value)


def _list(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise RuntimeError(f"{label} must be an array")
    return value


if __name__ == "__main__":
    raise SystemExit(main())
