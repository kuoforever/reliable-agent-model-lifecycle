"""Build or check the FP32 attached offline-artifact eligibility reassessment."""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import stat
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fullcycle_bridge import (  # noqa: E402
    tool_router_fp32_attached_artifact_eligibility as review_contract,
)
from fullcycle_bridge import (  # noqa: E402
    tool_router_fp32_attached_offline_artifact_eligibility_reassessment as contract,
)
from fullcycle_bridge import (  # noqa: E402
    tool_router_fp32_attached_offline_package_manifest as manifest_contract,
)
from fullcycle_bridge import (  # noqa: E402
    tool_router_fp32_attached_offline_package_reproducibility as repro_contract,
)
from fullcycle_bridge import (  # noqa: E402
    tool_router_fp32_attached_remote_revision_origin_attestation as origin_contract,
)
from scripts.review_tool_router_fp32_attached_artifact_eligibility import (  # noqa: E402
    load_review_inputs,
)


OUTPUT = (
    ROOT
    / "baseline"
    / "fc-mvp-001-fp32-attached-offline-artifact-eligibility-"
    "reassessment-v1.json"
)
PREREGISTRATION = ROOT / contract.PREREGISTRATION_PATH
ADAPTER_ROOT = ROOT / "baseline" / "adapters" / "fc-mvp-001-lora-sft-v2"
GIT_COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}")
REPARSE_POINT_ATTRIBUTE = 0x400

REPRO_PREREGISTRATION_PATH = (
    ROOT
    / "configs"
    / "tool_router_fp32_attached_offline_package_reproducibility_v1.json"
)
REPRO_REPLAY_PATH = (
    ROOT
    / "baseline"
    / "tool-router-fp32-attached-offline-package-reproducibility-v1-"
    "predictions.json"
)
REPRO_REFERENCE_PREDICTIONS_PATH = ROOT / repro_contract.REFERENCE_PREDICTIONS_PATH
REPRO_REFERENCE_EVIDENCE_PATH = ROOT / repro_contract.REFERENCE_EVIDENCE_PATH
REPRO_EVALUATION_PATH = ROOT / repro_contract.EVALUATION_PATH
REPRO_PREREGISTRATION_SHA256 = (
    "sha256:982d039b2b591d2dab80d489bbbada252c764c82fce94334580807616b22ffff"
)
REPRO_REPLAY_SHA256 = (
    "sha256:a0e99e80e091d3d6c191e3863449a6a5298d7f0d3a23cc6d786968562e6d2a46"
)
REPRO_FREEZE_COMMIT = "eafd3f646e4ec08dd0a1f76443ccfd416e81fa22"

ORIGIN_PREREGISTRATION_PATH = (
    ROOT
    / "configs"
    / "tool_router_fp32_attached_remote_revision_origin_attestation_v1.json"
)
ORIGIN_PREREGISTRATION_SHA256 = (
    "sha256:0523caa79ab820e4de892e25f7e94e0081c1086e0255e286c6f202bbc382667e"
)
ORIGIN_FREEZE_COMMIT = "d0f9a6988ef9702c713402bb179d7524e5e12c7f"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-preregistration", action="store_true")
    parser.add_argument("--freeze-commit")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--preregistration", type=Path, default=PREREGISTRATION)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.write_preregistration:
        if args.check or args.freeze_commit is not None:
            raise RuntimeError(
                "--write-preregistration cannot be combined with --check or "
                "--freeze-commit"
            )
        preregistration = contract.expected_preregistration(
            freeze_status="frozen",
            protocol_source_hashes={
                name: contract.sha256_bytes(payload)
                for name, payload in protocol_source_payloads().items()
            },
        )
        payload = contract.artifact_json_bytes(preregistration)
        _write_exclusive(args.preregistration, payload)
        print(
            json.dumps(
                {
                    "valid": True,
                    "kind": "frozen_preregistration",
                    "path": str(args.preregistration),
                    "bytes": len(payload),
                    "sha256": contract.sha256_bytes(payload),
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 0

    if not isinstance(args.freeze_commit, str) or not GIT_COMMIT_PATTERN.fullmatch(
        args.freeze_commit
    ):
        raise RuntimeError("--freeze-commit must be one full lowercase Git SHA")
    evidence = build_from_repository(
        preregistration_path=args.preregistration,
        protocol_freeze_commit=args.freeze_commit,
    )
    payload = contract.artifact_json_bytes(evidence)
    if args.check:
        observed = _read_regular_file(args.output, "reassessment output")
        if observed != payload:
            raise RuntimeError(f"frozen reassessment differs: {args.output}")
    else:
        _write_exclusive(args.output, payload)
    print(
        json.dumps(
            {
                "valid": True,
                "check": args.check,
                "path": str(args.output),
                "bytes": len(payload),
                "sha256": contract.sha256_bytes(payload),
                "classification": evidence["classification"],
                "formal_gate_passed": evidence["formal_gate_passed"],
                "offline_artifact_eligible": evidence["derived_claims"][
                    "offline_artifact_eligible"
                ],
                "portable_package_eligible": False,
                "runtime_eligible": False,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


def build_from_repository(
    *,
    preregistration_path: Path = PREREGISTRATION,
    protocol_freeze_commit: str,
) -> dict[str, Any]:
    """Recompute every upstream projection, then derive the reassessment."""

    preregistration_payload = _read_regular_file(
        preregistration_path, "reassessment preregistration"
    )
    preregistration_raw = contract.parse_strict_json_bytes(
        preregistration_payload, path="$.preregistration"
    )
    if not isinstance(preregistration_raw, Mapping):
        raise RuntimeError("reassessment preregistration must be an object")
    upstream_payloads = load_upstream_payloads()
    upstream_validations = compute_upstream_validations(upstream_payloads)
    return contract.build_reassessment_evidence(
        dict(preregistration_raw),
        preregistration_sha256=contract.sha256_bytes(preregistration_payload),
        protocol_freeze_commit=protocol_freeze_commit,
        upstream_payloads=upstream_payloads,
        upstream_validations=upstream_validations,
        protocol_source_payloads=protocol_source_payloads(),
    )


def load_upstream_payloads() -> dict[str, bytes]:
    """Single-read the four primary upstream evidence roots."""

    return {
        name: _read_regular_file(ROOT / receipt["path"], name)
        for name, receipt in sorted(contract.UPSTREAM_ARTIFACTS.items())
    }


def protocol_source_payloads() -> dict[str, bytes]:
    """Single-read the exact new protocol source closure."""

    return {
        name: _read_regular_file(ROOT / relative, name)
        for name, relative in sorted(contract.PROTOCOL_SOURCE_PATHS.items())
    }


def compute_upstream_validations(
    upstream_payloads: Mapping[str, bytes],
) -> dict[str, dict[str, Any]]:
    """Run the four canonical validators against authenticated primary bytes."""

    if set(upstream_payloads) != set(contract.UPSTREAM_ARTIFACTS):
        raise RuntimeError("upstream payload keys drifted")

    review_raw = contract.parse_strict_json_bytes(
        upstream_payloads["artifact_eligibility_review"],
        path="$.artifact_eligibility_review",
    )
    if not isinstance(review_raw, Mapping):
        raise RuntimeError("artifact eligibility review must be an object")
    review_inputs = load_review_inputs()
    review_validation = (
        review_contract.validate_fp32_attached_artifact_eligibility_review(
            dict(review_raw),
            **review_inputs,
            expected_source_hashes=copy.deepcopy(review_inputs["source_hashes"]),
        )
    )

    manifest_bundle = repro_contract.load_manifest_source_bundle(
        repository_root=ROOT,
        adapter_root=ADAPTER_ROOT,
    )
    if (
        manifest_bundle.source_payloads["upstream_review"]
        != upstream_payloads["artifact_eligibility_review"]
    ):
        raise RuntimeError("manifest bundle upstream review payload drifted")
    manifest_validation = manifest_contract.validate_fp32_attached_offline_package_manifest(
        upstream_payloads["offline_package_manifest"],
        repro_contract.MANIFEST_SHA256,
        manifest_bundle.upstream_review,
        manifest_bundle.remediation_preregistration,
        manifest_bundle.sft_config,
        manifest_bundle.adapter_config,
        source_hashes=manifest_bundle.source_hashes,
        source_payloads=manifest_bundle.source_payloads,
        expected_source_hashes=repro_contract.EXPECTED_MANIFEST_SOURCE_HASHES,
    )

    repro_preregistration_payload = _read_regular_file(
        REPRO_PREREGISTRATION_PATH, "reproducibility preregistration"
    )
    repro_replay_payload = _read_regular_file(
        REPRO_REPLAY_PATH, "reproducibility replay"
    )
    repro_reference_predictions_payload = _read_regular_file(
        REPRO_REFERENCE_PREDICTIONS_PATH, "reproducibility reference predictions"
    )
    repro_reference_evidence_payload = _read_regular_file(
        REPRO_REFERENCE_EVIDENCE_PATH, "reproducibility reference evidence"
    )
    repro_evaluation_payload = _read_regular_file(
        REPRO_EVALUATION_PATH, "reproducibility evaluation"
    )
    repro_validation = repro_contract.validate_reproducibility_evidence(
        repro_preregistration_payload,
        repro_replay_payload,
        upstream_payloads["offline_package_reproducibility"],
        expected_preregistration_sha256=REPRO_PREREGISTRATION_SHA256,
        expected_replay_artifact_sha256=REPRO_REPLAY_SHA256,
        expected_evidence_sha256=contract.UPSTREAM_ARTIFACTS[
            "offline_package_reproducibility"
        ]["sha256"],
        expected_protocol_freeze_commit=REPRO_FREEZE_COMMIT,
        replay_artifact_path=(
            "tool-router-fp32-attached-offline-package-"
            "reproducibility-v1-predictions.json"
        ),
        manifest_payload=upstream_payloads["offline_package_manifest"],
        reference_predictions_payload=repro_reference_predictions_payload,
        reference_evidence_payload=repro_reference_evidence_payload,
        evaluation_payload=repro_evaluation_payload,
        manifest_sources=manifest_bundle,
    )

    origin_preregistration_payload = _read_regular_file(
        ORIGIN_PREREGISTRATION_PATH, "origin preregistration"
    )
    origin_source_payloads = {
        name: _read_regular_file(ROOT / relative, f"origin {name}")
        for name, relative in sorted(origin_contract.PROTOCOL_SOURCE_PATHS.items())
    }
    origin_validation = origin_contract.validate_origin_attestation_evidence(
        origin_preregistration_payload,
        upstream_payloads["remote_revision_origin_attestation"],
        expected_preregistration_sha256=ORIGIN_PREREGISTRATION_SHA256,
        expected_evidence_sha256=contract.UPSTREAM_ARTIFACTS[
            "remote_revision_origin_attestation"
        ]["sha256"],
        expected_protocol_freeze_commit=ORIGIN_FREEZE_COMMIT,
        manifest_payload=upstream_payloads["offline_package_manifest"],
        reproducibility_evidence_payload=upstream_payloads[
            "offline_package_reproducibility"
        ],
        protocol_source_payloads=origin_source_payloads,
    )

    validations = {
        "artifact_eligibility_review": review_validation,
        "offline_package_manifest": manifest_validation,
        "offline_package_reproducibility": repro_validation,
        "remote_revision_origin_attestation": origin_validation,
    }
    if validations != contract.EXPECTED_UPSTREAM_VALIDATIONS:
        raise RuntimeError("canonical upstream validation projection drifted")
    return validations


def _read_regular_file(path: Path, label: str) -> bytes:
    resolved = path.resolve(strict=True)
    if resolved != path.resolve() or not resolved.is_file() or resolved.is_symlink():
        raise RuntimeError(f"unsafe {label}: {path}")
    file_stat = os.stat(resolved, follow_symlinks=False)
    if not stat.S_ISREG(file_stat.st_mode) or file_stat.st_nlink != 1:
        raise RuntimeError(f"unsafe {label}: {path}")
    if getattr(file_stat, "st_file_attributes", 0) & REPARSE_POINT_ATTRIBUTE:
        raise RuntimeError(f"reparse-point {label}: {path}")
    return resolved.read_bytes()


def _write_exclusive(path: Path, payload: bytes) -> None:
    parent = path.parent.resolve(strict=True)
    resolved = parent / path.name
    if resolved.exists():
        raise RuntimeError(f"refusing to overwrite: {resolved}")
    with resolved.open("xb") as handle:
        handle.write(payload)


if __name__ == "__main__":
    raise SystemExit(main())
