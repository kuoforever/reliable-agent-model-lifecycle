"""Build the frozen FP32 attached preferred-offline-candidate decision."""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fullcycle_bridge import (  # noqa: E402
    tool_router_fp32_attached_offline_artifact_eligibility_reassessment
    as reassessment_contract,
)
from fullcycle_bridge import (  # noqa: E402
    tool_router_fp32_attached_preferred_offline_candidate_decision as contract,
)
from scripts import (  # noqa: E402
    reassess_tool_router_fp32_attached_offline_artifact_eligibility
    as reassessment_builder,
)


OUTPUT = (
    ROOT
    / "baseline"
    / "fc-mvp-001-fp32-attached-preferred-offline-candidate-decision-v1.json"
)
PREREGISTRATION = ROOT / contract.PREREGISTRATION_PATH
REASSESSMENT_PREREGISTRATION = ROOT / reassessment_contract.PREREGISTRATION_PATH
REASSESSMENT_EVIDENCE = (
    ROOT
    / "baseline"
    / "fc-mvp-001-fp32-attached-offline-artifact-eligibility-reassessment-v1.json"
)
REASSESSMENT_PREREGISTRATION_SHA256 = (
    "sha256:f1fc627d3d20f9c954f93e0cd4c930b22f592c48d2f4af72220c184f2e32c662"
)
REASSESSMENT_EVIDENCE_SHA256 = (
    "sha256:0cccb2a7c7cdc24c824ee0ca4606f8c14e9b561473e50e8b31072291357b15ed"
)
REASSESSMENT_FREEZE_COMMIT = "2a5db8afaf90a3557d6d8d8cd808089d305d83e1"
GIT_COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}")
REPARSE_POINT_ATTRIBUTE = 0x400


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
        source_payloads = protocol_source_payloads()
        preregistration = contract.expected_preregistration(
            freeze_status="frozen",
            protocol_source_hashes={
                name: contract.sha256_bytes(payload)
                for name, payload in source_payloads.items()
            },
        )
        payload = contract.artifact_json_bytes(preregistration)
        _write_exclusive(args.preregistration, payload)
        print(
            json.dumps(
                {
                    "bytes": len(payload),
                    "path": str(args.preregistration.resolve()),
                    "sha256": contract.sha256_bytes(payload),
                    "written": True,
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
        protocol_freeze_commit=args.freeze_commit,
        preregistration_path=args.preregistration,
    )
    payload = contract.artifact_json_bytes(evidence)
    if args.check:
        existing = _read_regular_file(args.output, "decision evidence")
        if existing != payload:
            raise RuntimeError("tracked decision evidence does not recompute exactly")
    else:
        _write_exclusive(args.output, payload)
    print(
        json.dumps(
            {
                "bytes": len(payload),
                "check": args.check,
                "classification": evidence["classification"],
                "formal_gate_passed": evidence["formal_gate_passed"],
                "offline_artifact_eligible": evidence["derived_claims"][
                    "offline_artifact_eligible"
                ],
                "path": str(args.output.resolve()),
                "portable_package_eligible": evidence["derived_claims"][
                    "portable_package_eligible"
                ],
                "preferred_offline_candidate": evidence["derived_claims"][
                    "preferred_offline_candidate"
                ],
                "runtime_eligible": evidence["runtime_eligible"],
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
    preregistration_path: Path = PREREGISTRATION,
) -> dict[str, Any]:
    preregistration_payload = _read_regular_file(
        preregistration_path, "decision preregistration"
    )
    preregistration = contract.parse_strict_json_bytes(
        preregistration_payload, path="$.preregistration"
    )
    if not isinstance(preregistration, dict):
        raise RuntimeError("decision preregistration must be one JSON object")
    upstream_payloads, upstream_validations = load_decision_upstreams()
    return contract.build_decision_evidence(
        preregistration,
        preregistration_sha256=contract.sha256_bytes(preregistration_payload),
        protocol_freeze_commit=protocol_freeze_commit,
        upstream_payloads=upstream_payloads,
        upstream_validations=upstream_validations,
        protocol_source_payloads=protocol_source_payloads(),
    )


def protocol_source_payloads() -> dict[str, bytes]:
    return {
        name: _read_regular_file(ROOT / relative, f"protocol {name}")
        for name, relative in sorted(contract.PROTOCOL_SOURCE_PATHS.items())
    }


def load_decision_upstreams() -> tuple[
    dict[str, bytes], dict[str, dict[str, Any]]
]:
    reassessment_upstreams = reassessment_builder.load_upstream_payloads()
    reassessment_validations = reassessment_builder.compute_upstream_validations(
        reassessment_upstreams
    )
    reassessment_payload = _read_regular_file(
        REASSESSMENT_EVIDENCE, "eligibility reassessment evidence"
    )
    reassessment_validation = reassessment_contract.validate_reassessment_evidence(
        _read_regular_file(
            REASSESSMENT_PREREGISTRATION, "eligibility reassessment preregistration"
        ),
        reassessment_payload,
        expected_preregistration_sha256=REASSESSMENT_PREREGISTRATION_SHA256,
        expected_evidence_sha256=REASSESSMENT_EVIDENCE_SHA256,
        expected_protocol_freeze_commit=REASSESSMENT_FREEZE_COMMIT,
        upstream_payloads=reassessment_upstreams,
        upstream_validations=reassessment_validations,
        protocol_source_payloads=reassessment_builder.protocol_source_payloads(),
    )
    upstream_payloads = {
        "artifact_eligibility_review": reassessment_upstreams[
            "artifact_eligibility_review"
        ],
        "offline_artifact_eligibility_reassessment": reassessment_payload,
    }
    upstream_validations = {
        "artifact_eligibility_review": reassessment_validations[
            "artifact_eligibility_review"
        ],
        "offline_artifact_eligibility_reassessment": reassessment_validation,
    }
    if upstream_validations != contract.EXPECTED_UPSTREAM_VALIDATIONS:
        raise RuntimeError("canonical decision upstream projection drifted")
    return upstream_payloads, upstream_validations


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
