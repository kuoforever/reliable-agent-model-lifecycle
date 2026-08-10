"""Build or byte-check one target-machine portable-package qualification."""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import stat
import subprocess
import sys
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(ROOT))

from fullcycle_bridge import (  # noqa: E402
    tool_router_fp32_attached_offline_package_reproducibility as replay_contract,
)
from fullcycle_bridge import (  # noqa: E402
    tool_router_fp32_attached_portable_package_qualification as contract,
)
from fullcycle_bridge import (  # noqa: E402
    tool_router_fp32_attached_preferred_offline_candidate_decision as preferred_contract,
)
from scripts import (  # noqa: E402
    decide_tool_router_fp32_attached_preferred_offline_candidate as preferred_builder,
)


PREREGISTRATION = ROOT / contract.PREREGISTRATION_PATH
PREFERRED_EVIDENCE = ROOT / contract.PREFERRED_EVIDENCE_PATH
REPARSE_POINT_ATTRIBUTE = 0x400
WINDOWS_GUID_PATTERN = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
)
NVIDIA_GPU_UUID_PATTERN = re.compile(
    r"gpu-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol-freeze-commit", required=True)
    parser.add_argument("--clean-repository-root", type=Path, required=True)
    parser.add_argument("--clean-adapter-root", type=Path, required=True)
    parser.add_argument("--target-replay-artifact", type=Path, required=True)
    parser.add_argument("--target-replay-evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output_path = _output_path(args.output, must_exist=args.check)
    replay_artifact_payload = _read_regular_file(
        args.target_replay_artifact, "target replay artifact"
    )
    replay_evidence_payload = _read_regular_file(
        args.target_replay_evidence, "target replay evidence"
    )
    machine_receipt: Mapping[str, Any] | None = None
    if args.check:
        existing_payload = _read_regular_file(output_path, "qualification evidence")
        existing = contract.parse_strict_json_bytes(
            existing_payload, path="$.qualification_evidence"
        )
        if not isinstance(existing, dict) or not isinstance(
            existing.get("target_machine_receipt"), dict
        ):
            raise RuntimeError("qualification evidence lacks a machine receipt")
        machine_receipt = existing["target_machine_receipt"]
    evidence = build_from_repository(
        protocol_freeze_commit=args.protocol_freeze_commit,
        clean_repository_root=args.clean_repository_root,
        clean_adapter_root=args.clean_adapter_root,
        replay_artifact_payload=replay_artifact_payload,
        replay_evidence_payload=replay_evidence_payload,
        machine_receipt=machine_receipt,
    )
    payload = contract.artifact_json_bytes(evidence)
    if args.check:
        if payload != existing_payload:
            raise RuntimeError("qualification evidence differs from recomputation")
    else:
        _write_exclusive(output_path, payload)
    print(
        json.dumps(
            {
                "classification": evidence["classification"],
                "cross_machine_reproducibility_established": evidence["derived_claims"][
                    "cross_machine_reproducibility_established"
                ],
                "portable_package_eligible": evidence["derived_claims"][
                    "portable_package_eligible"
                ],
                "runtime_eligible": False,
                "sha256": contract.sha256_bytes(payload),
                "valid": True,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


def build_from_repository(
    *,
    protocol_freeze_commit: str,
    clean_repository_root: Path,
    clean_adapter_root: Path,
    replay_artifact_payload: bytes,
    replay_evidence_payload: bytes,
    machine_receipt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Recompute upstreams, validate the target replay, then classify it."""

    preregistration_payload = _read_regular_file(
        PREREGISTRATION, "portable qualification preregistration"
    )
    preregistration = contract.parse_strict_json_bytes(
        preregistration_payload, path="$.preregistration"
    )
    if not isinstance(preregistration, dict):
        raise RuntimeError("portable qualification preregistration must be an object")

    preferred_evidence_payload = _read_regular_file(
        PREFERRED_EVIDENCE, "preferred candidate evidence"
    )
    preferred_validation = _validate_preferred_candidate(preferred_evidence_payload)
    target_replay_validation = _validate_target_replay(
        clean_repository_root=clean_repository_root,
        clean_adapter_root=clean_adapter_root,
        replay_artifact_payload=replay_artifact_payload,
        replay_evidence_payload=replay_evidence_payload,
    )
    if machine_receipt is None:
        machine_receipt = collect_machine_receipt(
            replay_artifact_payload=replay_artifact_payload,
            replay_evidence_payload=replay_evidence_payload,
        )
    return contract.build_qualification_evidence(
        preregistration,
        preregistration_sha256=contract.sha256_bytes(preregistration_payload),
        protocol_freeze_commit=protocol_freeze_commit,
        preferred_evidence_payload=preferred_evidence_payload,
        preferred_validation=preferred_validation,
        replay_artifact_payload=replay_artifact_payload,
        replay_evidence_payload=replay_evidence_payload,
        target_replay_validation=target_replay_validation,
        target_machine_receipt=machine_receipt,
        protocol_source_payloads=protocol_source_payloads(),
    )


def collect_machine_receipt(
    *, replay_artifact_payload: bytes, replay_evidence_payload: bytes
) -> dict[str, Any]:
    """Collect target-local hashed identifiers and bind both replay artifacts."""

    if platform.system() != "Windows":
        raise RuntimeError("formal target machine receipt requires native Windows")
    try:
        import winreg
    except ImportError as exc:  # pragma: no cover - native Windows contract
        raise RuntimeError("Windows registry support is unavailable") from exc

    try:
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Cryptography",
            0,
            winreg.KEY_READ,
        ) as key:
            machine_guid_raw, value_type = winreg.QueryValueEx(key, "MachineGuid")
    except OSError as exc:
        raise RuntimeError("Windows MachineGuid is unavailable") from exc
    if value_type not in {winreg.REG_SZ, winreg.REG_EXPAND_SZ}:
        raise RuntimeError("Windows MachineGuid has an unexpected registry type")
    machine_guid = str(machine_guid_raw).strip().lower()
    if WINDOWS_GUID_PATTERN.fullmatch(machine_guid) is None:
        raise RuntimeError("Windows MachineGuid has an invalid format")

    command = [
        "nvidia-smi",
        "--query-gpu=uuid,driver_version",
        "--format=csv,noheader,nounits",
    ]
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="strict",
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError, UnicodeError) as exc:
        raise RuntimeError("nvidia-smi identity query failed") from exc
    lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    if completed.returncode != 0 or completed.stderr or len(lines) != 1:
        raise RuntimeError("exactly one clean NVIDIA GPU identity row is required")
    parts = [part.strip() for part in lines[0].split(",")]
    if len(parts) != 2:
        raise RuntimeError("NVIDIA identity row has an unexpected shape")
    gpu_uuid = parts[0].lower()
    driver_version = parts[1]
    if NVIDIA_GPU_UUID_PATTERN.fullmatch(gpu_uuid) is None or not driver_version:
        raise RuntimeError("NVIDIA identity row has invalid values")

    machine_digest = contract.identity_source_digest(
        contract.MACHINE_GUID_DOMAIN, machine_guid
    )
    gpu_digest = contract.identity_source_digest(contract.GPU_UUID_DOMAIN, gpu_uuid)
    return {
        "receipt_version": contract.MACHINE_RECEIPT_VERSION,
        "gate_id": contract.GATE_ID,
        "captured_at_utc": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "nvidia_driver_version": driver_version,
        },
        "identity": {
            "algorithm": contract.IDENTITY_ALGORITHM,
            "machine_guid_sha256": machine_digest,
            "gpu_uuid_sha256": gpu_digest,
            "combined_identity_sha256": contract.combined_machine_identity(
                machine_digest, gpu_digest
            ),
            "raw_identifiers_recorded": False,
            "hardware_backed_attestation": False,
        },
        "target_artifacts": {
            "replay_artifact": {
                "logical_path": contract.REPLAY_LOGICAL_ARTIFACT_PATH,
                "bytes": len(replay_artifact_payload),
                "sha256": contract.sha256_bytes(replay_artifact_payload),
            },
            "replay_evidence": {
                "logical_path": contract.REPLAY_LOGICAL_EVIDENCE_PATH,
                "bytes": len(replay_evidence_payload),
                "sha256": contract.sha256_bytes(replay_evidence_payload),
            },
        },
        "limitations": {
            "hardware_backed_attestation": False,
            "external_execution_count_attested": False,
            "alternate_execution_excluded": False,
            "raw_identifiers_retained": False,
        },
    }


def protocol_source_payloads() -> dict[str, bytes]:
    return {
        name: _read_regular_file(ROOT / relative, f"protocol {name}")
        for name, relative in sorted(contract.PROTOCOL_SOURCE_PATHS.items())
    }


def _validate_preferred_candidate(payload: bytes) -> dict[str, Any]:
    upstream_payloads, upstream_validations = (
        preferred_builder.load_decision_upstreams()
    )
    return cast(
        dict[str, Any],
        preferred_contract.validate_decision_evidence(
            _read_regular_file(
                ROOT / preferred_contract.PREREGISTRATION_PATH,
                "preferred candidate preregistration",
            ),
            payload,
            expected_preregistration_sha256=contract.PREFERRED_PREREGISTRATION_SHA256,
            expected_evidence_sha256=contract.PREFERRED_EVIDENCE_SHA256,
            expected_protocol_freeze_commit=contract.PREFERRED_FREEZE_COMMIT,
            upstream_payloads=upstream_payloads,
            upstream_validations=upstream_validations,
            protocol_source_payloads=preferred_builder.protocol_source_payloads(),
        ),
    )


def _validate_target_replay(
    *,
    clean_repository_root: Path,
    clean_adapter_root: Path,
    replay_artifact_payload: bytes,
    replay_evidence_payload: bytes,
) -> dict[str, Any]:
    repository_root = _safe_directory(clean_repository_root, "clean repository root")
    adapter_root = _safe_directory(clean_adapter_root, "clean adapter root")
    manifest_sources = replay_contract.load_manifest_source_bundle(
        repository_root=repository_root,
        adapter_root=adapter_root,
    )
    return cast(
        dict[str, Any],
        replay_contract.validate_reproducibility_evidence(
            _read_regular_file(
                repository_root / contract.REPLAY_PREREGISTRATION_PATH,
                "target replay preregistration",
            ),
            replay_artifact_payload,
            replay_evidence_payload,
            expected_preregistration_sha256=contract.REPLAY_PREREGISTRATION_SHA256,
            expected_replay_artifact_sha256=contract.sha256_bytes(
                replay_artifact_payload
            ),
            expected_evidence_sha256=contract.sha256_bytes(replay_evidence_payload),
            expected_protocol_freeze_commit=contract.REPLAY_FREEZE_COMMIT,
            replay_artifact_path=contract.REPLAY_LOGICAL_ARTIFACT_PATH,
            manifest_payload=_read_regular_file(
                repository_root / replay_contract.MANIFEST_PATH, "package manifest"
            ),
            reference_predictions_payload=_read_regular_file(
                repository_root / replay_contract.REFERENCE_PREDICTIONS_PATH,
                "reference predictions",
            ),
            reference_evidence_payload=_read_regular_file(
                repository_root / replay_contract.REFERENCE_EVIDENCE_PATH,
                "reference evidence",
            ),
            evaluation_payload=_read_regular_file(
                repository_root / replay_contract.EVALUATION_PATH, "evaluation"
            ),
            manifest_sources=manifest_sources,
        ),
    )


def _output_path(path: Path, *, must_exist: bool) -> Path:
    raw = path if path.is_absolute() else Path.cwd() / path
    if ".." in raw.parts:
        raise RuntimeError("output path must not contain parent traversal")
    parent = raw.parent.resolve(strict=True)
    _require_safe_directory(parent, "output parent")
    result = parent / raw.name
    if not raw.name or result.exists() is not must_exist:
        state = "existing" if must_exist else "absent"
        raise RuntimeError(f"output must be an {state} regular file path")
    if must_exist:
        _read_regular_file(result, "qualification evidence")
    return result


def _safe_directory(path: Path, label: str) -> Path:
    resolved = path.resolve(strict=True)
    _require_safe_directory(resolved, label)
    return resolved


def _require_safe_directory(path: Path, label: str) -> None:
    metadata = os.stat(path, follow_symlinks=False)
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or path.is_symlink()
        or getattr(metadata, "st_file_attributes", 0) & REPARSE_POINT_ATTRIBUTE
    ):
        raise RuntimeError(f"unsafe {label}: {path}")


def _read_regular_file(path: Path, label: str) -> bytes:
    resolved = path.resolve(strict=True)
    before = os.stat(resolved, follow_symlinks=False)
    if (
        not stat.S_ISREG(before.st_mode)
        or resolved.is_symlink()
        or before.st_nlink != 1
        or getattr(before, "st_file_attributes", 0) & REPARSE_POINT_ATTRIBUTE
        or before.st_size <= 0
        or before.st_size > contract.MAX_JSON_BYTES
    ):
        raise RuntimeError(f"unsafe {label}: {path}")
    with resolved.open("rb") as handle:
        opened = os.fstat(handle.fileno())
        if _identity(before) != _identity(opened):
            raise RuntimeError(f"{label} identity changed before read")
        payload = handle.read()
        after_handle = os.fstat(handle.fileno())
    after = os.stat(resolved, follow_symlinks=False)
    if (
        _identity(before) != _identity(after_handle)
        or _identity(after_handle) != _identity(after)
        or _signature(before) != _signature(after)
        or len(payload) != after.st_size
    ):
        raise RuntimeError(f"{label} changed while reading")
    return payload


def _write_exclusive(path: Path, payload: bytes) -> None:
    with path.open("xb") as handle:
        handle.write(payload)


def _identity(value: os.stat_result) -> tuple[int, int, int]:
    return value.st_dev, value.st_ino, value.st_mode


def _signature(value: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


if __name__ == "__main__":
    raise SystemExit(main())
