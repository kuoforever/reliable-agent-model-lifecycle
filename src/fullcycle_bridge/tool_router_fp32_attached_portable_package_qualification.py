"""Fail-closed cross-machine qualification for the FP32 attached package.

The protocol deliberately reuses the frozen clean-location replay validator.
It adds only a privacy-preserving target-machine receipt and a categorical
portable-package decision.  It is operational evidence, not hardware-backed
remote attestation or external execution-count attestation.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from collections.abc import Mapping
from typing import Any, NoReturn

from fullcycle_bridge.consumer import canonical_json_bytes


PREREGISTRATION_VERSION = 1
EVIDENCE_VERSION = 1
MACHINE_RECEIPT_VERSION = 1
GATE_ID = "FC-MVP-001-fp32-attached-portable-package-qualification-v1"
EXPERIMENT_ID = "fc-mvp-001-fp32-attached-portable-package-qualification-v1"
PACKAGE_ID = "fc-mvp-001-fp32-attached-factorized-lora-package-v1"
CANDIDATE_ID = "fp32-attached-factorized-lora"

PASS_CLASSIFICATION = (
    "fp32_attached_portable_package_qualified_for_distinct_windows_machine_"
    "under_locked_environment_fixed_compiler_and_attached_execution"
)
INCOMPLETE_CLASSIFICATION = "fp32_attached_portable_package_qualification_incomplete"
PASS_NEXT_GATE_ID = "FC-MVP-001-fp32-attached-offline-package-promotion-decision-v1"
FAILURE_NEXT_GATE_ID = (
    "FC-MVP-001-fp32-attached-portable-package-qualification-failure-classification-v1"
)

PREREGISTRATION_PATH = (
    "configs/tool_router_fp32_attached_portable_package_qualification_v1.json"
)
CONTRACT_SOURCE_PATH = (
    "src/fullcycle_bridge/tool_router_fp32_attached_portable_package_qualification.py"
)
BUILDER_SOURCE_PATH = "scripts/qualify_tool_router_fp32_attached_portable_package.py"
PROTOCOL_SOURCE_PATHS = {
    "builder_source": BUILDER_SOURCE_PATH,
    "contract_source": CONTRACT_SOURCE_PATH,
}

PREFERRED_EVIDENCE_PATH = (
    "baseline/fc-mvp-001-fp32-attached-preferred-offline-candidate-decision-v1.json"
)
PREFERRED_EVIDENCE_SHA256 = (
    "sha256:02f66ed79edce17803ddc1ed172c35a995be4ee8ed984cdd49b4e24bc5748c55"
)
PREFERRED_PREREGISTRATION_SHA256 = (
    "sha256:75f25ceebb6a9428ad3d92f4ecc778d8725e1d52e32367ff8db3cb2ac3125f21"
)
PREFERRED_FREEZE_COMMIT = "1f9aeecda71ad7f758a905b1eec3dccb3885e10f"

REPLAY_PREREGISTRATION_PATH = (
    "configs/tool_router_fp32_attached_offline_package_reproducibility_v1.json"
)
REPLAY_PREREGISTRATION_SHA256 = (
    "sha256:982d039b2b591d2dab80d489bbbada252c764c82fce94334580807616b22ffff"
)
REPLAY_FREEZE_COMMIT = "eafd3f646e4ec08dd0a1f76443ccfd416e81fa22"
REPLAY_LOGICAL_ARTIFACT_PATH = (
    "tool-router-fp32-attached-offline-package-reproducibility-v1-predictions.json"
)
REPLAY_LOGICAL_EVIDENCE_PATH = (
    "fc-mvp-001-fp32-attached-offline-package-reproducibility-v1.json"
)
ORIGIN_REPLAY_ARTIFACT_SHA256 = (
    "sha256:a0e99e80e091d3d6c191e3863449a6a5298d7f0d3a23cc6d786968562e6d2a46"
)
ORIGIN_REPLAY_EVIDENCE_SHA256 = (
    "sha256:0e0d2174f4723ab42a5c11375cee10a819e32737810f63111d098decc2984044"
)

IDENTITY_ALGORITHM = "domain-separated-sha256-v1"
MACHINE_GUID_DOMAIN = f"{EXPERIMENT_ID}/windows-machine-guid/v1"
GPU_UUID_DOMAIN = f"{EXPERIMENT_ID}/nvidia-gpu-uuid/v1"
CONTROLLER_MACHINE_GUID_SHA256 = (
    "sha256:2a67b96eab2f42d1f359f3b739ebf3c77d19715301a49859460175f418fe5761"
)
CONTROLLER_GPU_UUID_SHA256 = (
    "sha256:7dde9753023c6e9502c0581a5beb4e1b6fccbed2d42e1fa21e9fb59debeb91cb"
)
CONTROLLER_COMBINED_IDENTITY_SHA256 = (
    "sha256:91cbeb9c6da4642e0a0e8d891c0b19fd52277f8e296c4d1113840d44826c8eb3"
)
CONTROLLER_ANCHOR_DATE = "2026-08-10"

LOCKED_ENVIRONMENT = {
    "accelerate": "1.3.0",
    "compute_capability": "8.9",
    "device": "cuda",
    "gpu": "NVIDIA GeForce RTX 4090 Laptop GPU",
    "gpu_vram_bytes": 17_170_956_288,
    "huggingface_hub": "0.29.3",
    "peft": "0.14.0",
    "python": "3.12.12",
    "safetensors": "0.5.3",
    "tokenizers": "0.21.4",
    "torch": "2.6.0+cu124",
    "transformers": "4.49.0",
}
EXPECTED_RAW_OUTPUT_DIGEST = (
    "sha256:0ea00c3d73ba40a158d8fb54862d334c42d37be0f895455ea12788240fa2af28"
)
EXPECTED_COMPILED_OUTPUT_DIGEST = (
    "sha256:e6ae4e8f825085e72be476fe340a37a8b1d3f2488a078474c5766e085d6e4e0c"
)

EXPECTED_PREFERRED_VALIDATION: dict[str, Any] = {
    "frozen_gate_valid": True,
    "classification": (
        "fp32_attached_preferred_offline_candidate_under_fixed_compiler_"
        "attached_execution_and_registered_resource_caps"
    ),
    "formal_gate_passed": True,
    "offline_artifact_eligible": True,
    "preferred_offline_candidate": True,
    "portable_package_eligible": False,
    "remaining_blocking_findings": [],
    "downstream_open_findings": [
        "cross_machine_reproducibility_unestablished",
        "portable_package_eligibility_unestablished",
    ],
    "next_gate": GATE_ID,
    "runtime_eligible": False,
}
EXPECTED_TARGET_REPLAY_VALIDATION: dict[str, Any] = {
    "frozen_gate_valid": True,
    "classification": (
        "fp32_attached_same_environment_clean_location_behavior_exactly_reproduced"
    ),
    "formal_gate_passed": True,
    "clean_location_resolution_established": True,
    "behavioral_reproducibility_established": True,
    "remaining_blocking_findings": ["remote_revision_origin_unverified"],
    "next_gate": ("FC-MVP-001-fp32-attached-remote-revision-origin-attestation-v1"),
    "runtime_eligible": False,
}

REQUIREMENT_KEYS = (
    "attached_execution_contract_passed",
    "cross_machine_compiled_outputs_exact",
    "cross_machine_raw_outputs_exact",
    "limitations_disclosed",
    "locked_environment_reproduced",
    "offline_execution_passed",
    "package_identity_and_clean_resolution_passed",
    "preferred_candidate_gate_valid",
    "protocol_integrity",
    "registered_resource_caps_passed",
    "target_machine_identity_receipt_valid",
    "target_machine_is_distinct",
    "target_replay_gate_valid",
)
REQUIREMENT_BLOCKERS = {
    "attached_execution_contract_passed": "attached_execution_contract_failed",
    "cross_machine_compiled_outputs_exact": "cross_machine_compiled_output_drift",
    "cross_machine_raw_outputs_exact": "cross_machine_raw_output_drift",
    "limitations_disclosed": "portable_qualification_limitations_incomplete",
    "locked_environment_reproduced": "target_locked_environment_mismatch",
    "offline_execution_passed": "target_execution_not_offline",
    "package_identity_and_clean_resolution_passed": (
        "target_package_identity_or_clean_resolution_failed"
    ),
    "preferred_candidate_gate_valid": "preferred_candidate_gate_invalid",
    "protocol_integrity": "portable_qualification_protocol_integrity_failed",
    "registered_resource_caps_passed": "target_registered_resource_cap_failed",
    "target_machine_identity_receipt_valid": "target_machine_receipt_invalid",
    "target_machine_is_distinct": "target_machine_not_distinct_from_controller",
    "target_replay_gate_valid": "target_replay_gate_invalid",
}

ZERO_SHA256 = "sha256:" + "0" * 64
SHA256_PATTERN = re.compile(r"sha256:[0-9a-f]{64}")
GIT_COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}")
UTC_SECONDS_PATTERN = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z"
)
MAX_JSON_BYTES = 4 * 1024 * 1024


class PortablePackageQualificationError(ValueError):
    """Raised when a qualification trust root or categorical gate drifts."""


def artifact_json_bytes(value: Mapping[str, Any]) -> bytes:
    """Serialize one tracked artifact using the repository JSON convention."""

    return (
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    ).encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    """Return one project-prefixed SHA-256 identity."""

    return "sha256:" + hashlib.sha256(payload).hexdigest()


def identity_source_digest(domain: str, raw_identifier: str) -> str:
    """Hash one normalized raw identifier without retaining the identifier."""

    if not isinstance(domain, str) or not domain or "\x00" in domain:
        _fail("INVALID_IDENTITY_DOMAIN", "$.identity.domain", repr(domain))
    if not isinstance(raw_identifier, str) or not raw_identifier.strip():
        _fail("INVALID_RAW_IDENTIFIER", "$.identity.raw", "empty")
    normalized = raw_identifier.strip().lower()
    return sha256_bytes((domain + "\x00" + normalized).encode("utf-8"))


def combined_machine_identity(machine_guid_sha256: str, gpu_uuid_sha256: str) -> str:
    """Bind the two privacy-preserving identity digests canonically."""

    _validate_sha256(machine_guid_sha256, "$.identity.machine_guid_sha256")
    _validate_sha256(gpu_uuid_sha256, "$.identity.gpu_uuid_sha256")
    return sha256_bytes(
        canonical_json_bytes(
            {
                "gpu_uuid_sha256": gpu_uuid_sha256,
                "machine_guid_sha256": machine_guid_sha256,
            }
        )
    )


def parse_strict_json_bytes(
    payload: bytes, *, path: str, max_bytes: int = MAX_JSON_BYTES
) -> Any:
    """Parse bounded UTF-8 JSON while rejecting duplicates and non-finite values."""

    if not isinstance(payload, bytes) or not payload or len(payload) > max_bytes:
        _fail("INVALID_JSON_PAYLOAD", path, repr(type(payload).__name__))
    try:
        value = json.loads(
            payload,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_json_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise PortablePackageQualificationError(
            f"INVALID_JSON at {path}: {exc}"
        ) from exc
    _validate_finite_json(value, path)
    return value


def expected_preregistration(
    *, freeze_status: str, protocol_source_hashes: Mapping[str, str]
) -> dict[str, Any]:
    """Build the exact draft or frozen portable qualification protocol."""

    if freeze_status not in {"draft", "frozen"}:
        _fail("INVALID_FREEZE_STATUS", "$.freeze_status", freeze_status)
    if set(protocol_source_hashes) != set(PROTOCOL_SOURCE_PATHS):
        _fail(
            "INVALID_PROTOCOL_SOURCE_KEYS",
            "$.source_lineage.protocol_sources",
            repr(sorted(protocol_source_hashes)),
        )
    for name, value in protocol_source_hashes.items():
        _validate_sha256(value, f"$.source_lineage.protocol_sources.{name}.sha256")

    return {
        "preregistration_version": PREREGISTRATION_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "gate_id": GATE_ID,
        "package_id": PACKAGE_ID,
        "candidate_id": CANDIDATE_ID,
        "freeze_status": freeze_status,
        "qualification_scope": {
            "decision": "portable_package_eligibility_only",
            "cross_machine_scope": (
                "one_operationally_distinct_windows_target_machine_exact_"
                "twenty_case_replay_under_the_locked_user_space_environment_"
                "same_gpu_class_fixed_compiler_and_attached_execution"
            ),
            "target_replay_is_new": True,
            "same_machine_wsl_or_second_path_is_acceptable": False,
            "cross_driver_claim": False,
            "cross_library_claim": False,
            "hardware_backed_attestation_claim": False,
            "external_execution_count_attestation_claim": False,
            "promotion_serving_or_runtime_decision": False,
        },
        "controller_machine_anchor": {
            "observation_date": CONTROLLER_ANCHOR_DATE,
            "purpose": (
                "controller_separation_anchor_not_historical_reference_"
                "execution_attestation"
            ),
            "identity_algorithm": IDENTITY_ALGORITHM,
            "machine_guid_sha256": CONTROLLER_MACHINE_GUID_SHA256,
            "gpu_uuid_sha256": CONTROLLER_GPU_UUID_SHA256,
            "combined_identity_sha256": CONTROLLER_COMBINED_IDENTITY_SHA256,
            "raw_identifiers_recorded": False,
            "historical_reference_execution_identity_attested": False,
        },
        "target_machine_policy": {
            "platform_system": "Windows",
            "identity_algorithm": IDENTITY_ALGORITHM,
            "machine_guid_domain": MACHINE_GUID_DOMAIN,
            "gpu_uuid_domain": GPU_UUID_DOMAIN,
            "machine_guid_digest_must_differ": True,
            "gpu_uuid_digest_must_differ": True,
            "combined_identity_digest_must_differ": True,
            "raw_identifiers_must_not_be_recorded": True,
            "builder_collects_identity_locally": True,
            "receipt_is_hardware_backed_attestation": False,
        },
        "target_replay_protocol": {
            "preregistration": {
                "path": REPLAY_PREREGISTRATION_PATH,
                "sha256": REPLAY_PREREGISTRATION_SHA256,
                "freeze_commit": REPLAY_FREEZE_COMMIT,
            },
            "logical_artifact_path": REPLAY_LOGICAL_ARTIFACT_PATH,
            "logical_evidence_path": REPLAY_LOGICAL_EVIDENCE_PATH,
            "origin_artifact_sha256_prohibited": ORIGIN_REPLAY_ARTIFACT_SHA256,
            "origin_evidence_sha256_prohibited": ORIGIN_REPLAY_EVIDENCE_SHA256,
            "environment": copy.deepcopy(LOCKED_ENVIRONMENT),
            "fresh_model_loads": 1,
            "full_eval_runs": 1,
            "generate_calls": 20,
            "retry_count": 0,
            "execution_form": "attached_factorized_lora",
            "fixed_compiler_required": True,
            "network_enabled_during_execution": False,
            "raw_output_comparison": "exact_utf8_bytes",
            "compiled_output_comparison": "exact_canonical_json_bytes",
            "registered_resource_caps_reused": True,
        },
        "source_lineage": {
            "preferred_candidate_evidence": {
                "path": PREFERRED_EVIDENCE_PATH,
                "sha256": PREFERRED_EVIDENCE_SHA256,
                "preregistration_sha256": PREFERRED_PREREGISTRATION_SHA256,
                "freeze_commit": PREFERRED_FREEZE_COMMIT,
            },
            "protocol_sources": {
                name: {
                    "path": PROTOCOL_SOURCE_PATHS[name],
                    "sha256": protocol_source_hashes[name],
                }
                for name in sorted(PROTOCOL_SOURCE_PATHS)
            },
        },
        "qualification_requirements": list(REQUIREMENT_KEYS),
        "outcome_classifications": {
            "qualified": PASS_CLASSIFICATION,
            "incomplete": INCOMPLETE_CLASSIFICATION,
        },
        "outcome_next_actions": {
            "qualified": {
                "gate_id": PASS_NEXT_GATE_ID,
                "action": (
                    "make a separate offline-package promotion decision without "
                    "inferring serving or Runtime readiness"
                ),
            },
            "incomplete": {
                "gate_id": FAILURE_NEXT_GATE_ID,
                "action": (
                    "classify the first failed frozen portability requirement "
                    "before changing any package byte or execution contract"
                ),
            },
        },
        "constraints": _constraints(),
        "claims": {
            **_false_claims(),
            "offline_artifact_eligible": True,
            "preferred_offline_candidate": True,
        },
        "runtime_eligible": False,
    }


def validate_preregistration(
    preregistration: Mapping[str, Any], *, require_frozen: bool = True
) -> dict[str, Any]:
    """Recompute every protocol field from its source hash receipts."""

    lineage = _mapping(preregistration.get("source_lineage"), "$.source_lineage")
    sources = _mapping(
        lineage.get("protocol_sources"), "$.source_lineage.protocol_sources"
    )
    if set(sources) != set(PROTOCOL_SOURCE_PATHS):
        _fail(
            "INVALID_PROTOCOL_SOURCE_KEYS",
            "$.source_lineage.protocol_sources",
            repr(sorted(sources)),
        )
    hashes: dict[str, str] = {}
    for name, relative in PROTOCOL_SOURCE_PATHS.items():
        receipt = _mapping(sources.get(name), f"$.protocol_sources.{name}")
        if receipt.get("path") != relative:
            _fail(
                "PROTOCOL_SOURCE_PATH_MISMATCH",
                f"$.protocol_sources.{name}.path",
                repr(receipt.get("path")),
            )
        digest = receipt.get("sha256")
        if not isinstance(digest, str):
            _fail("INVALID_SHA256", f"$.protocol_sources.{name}.sha256", repr(digest))
        _validate_sha256(digest, f"$.protocol_sources.{name}.sha256")
        hashes[name] = digest
    status = preregistration.get("freeze_status")
    if not isinstance(status, str):
        _fail("INVALID_FREEZE_STATUS", "$.freeze_status", repr(status))
    expected = expected_preregistration(
        freeze_status=status, protocol_source_hashes=hashes
    )
    if dict(preregistration) != expected:
        _fail(
            "PREREGISTRATION_RECOMPUTATION_MISMATCH",
            "$.preregistration",
            "fields drifted",
        )
    if require_frozen and status != "frozen":
        _fail("PREREGISTRATION_NOT_FROZEN", "$.freeze_status", status)
    return expected


def validate_machine_receipt(
    preregistration: Mapping[str, Any],
    receipt: Mapping[str, Any],
    *,
    replay_artifact_payload: bytes,
    replay_evidence_payload: bytes,
) -> dict[str, Any]:
    """Validate a target-local privacy-preserving receipt and artifact binding."""

    prereg = validate_preregistration(preregistration)
    expected_keys = {
        "receipt_version",
        "gate_id",
        "captured_at_utc",
        "platform",
        "identity",
        "target_artifacts",
        "limitations",
    }
    value = _mapping(receipt, "$.target_machine_receipt")
    if set(value) != expected_keys:
        _fail(
            "INVALID_MACHINE_RECEIPT_KEYS",
            "$.target_machine_receipt",
            repr(sorted(value)),
        )
    captured = value.get("captured_at_utc")
    if not isinstance(captured, str) or UTC_SECONDS_PATTERN.fullmatch(captured) is None:
        _fail(
            "INVALID_CAPTURE_TIME",
            "$.target_machine_receipt.captured_at_utc",
            repr(captured),
        )
    platform_value = _mapping(
        value.get("platform"), "$.target_machine_receipt.platform"
    )
    if set(platform_value) != {
        "system",
        "release",
        "version",
        "machine",
        "python",
        "nvidia_driver_version",
    }:
        _fail(
            "INVALID_PLATFORM_RECEIPT",
            "$.target_machine_receipt.platform",
            repr(sorted(platform_value)),
        )
    for key, item in platform_value.items():
        if not isinstance(item, str) or not item:
            _fail(
                "INVALID_PLATFORM_VALUE",
                f"$.target_machine_receipt.platform.{key}",
                repr(item),
            )
    identity = _mapping(value.get("identity"), "$.target_machine_receipt.identity")
    identity_keys = {
        "algorithm",
        "machine_guid_sha256",
        "gpu_uuid_sha256",
        "combined_identity_sha256",
        "raw_identifiers_recorded",
        "hardware_backed_attestation",
    }
    if frozenset(identity) not in {
        frozenset(identity_keys),
        frozenset((*identity_keys, "distinct_from_controller")),
    }:
        _fail(
            "INVALID_IDENTITY_RECEIPT",
            "$.target_machine_receipt.identity",
            repr(sorted(identity)),
        )
    machine_digest = identity.get("machine_guid_sha256")
    gpu_digest = identity.get("gpu_uuid_sha256")
    combined_digest = identity.get("combined_identity_sha256")
    if (
        not isinstance(machine_digest, str)
        or not isinstance(gpu_digest, str)
        or not isinstance(combined_digest, str)
    ):
        _fail(
            "INVALID_IDENTITY_DIGEST", "$.target_machine_receipt.identity", "non-string"
        )
    _validate_sha256(
        machine_digest, "$.target_machine_receipt.identity.machine_guid_sha256"
    )
    _validate_sha256(gpu_digest, "$.target_machine_receipt.identity.gpu_uuid_sha256")
    _validate_sha256(
        combined_digest, "$.target_machine_receipt.identity.combined_identity_sha256"
    )
    artifacts = _mapping(
        value.get("target_artifacts"), "$.target_machine_receipt.target_artifacts"
    )
    if set(artifacts) != {"replay_artifact", "replay_evidence"}:
        _fail(
            "INVALID_TARGET_ARTIFACT_KEYS",
            "$.target_machine_receipt.target_artifacts",
            repr(sorted(artifacts)),
        )
    expected_artifacts = {
        "replay_artifact": {
            "logical_path": REPLAY_LOGICAL_ARTIFACT_PATH,
            "bytes": len(replay_artifact_payload),
            "sha256": sha256_bytes(replay_artifact_payload),
        },
        "replay_evidence": {
            "logical_path": REPLAY_LOGICAL_EVIDENCE_PATH,
            "bytes": len(replay_evidence_payload),
            "sha256": sha256_bytes(replay_evidence_payload),
        },
    }
    expected_limitations = {
        "hardware_backed_attestation": False,
        "external_execution_count_attested": False,
        "alternate_execution_excluded": False,
        "raw_identifiers_retained": False,
    }
    if (
        value.get("receipt_version") != MACHINE_RECEIPT_VERSION
        or value.get("gate_id") != GATE_ID
        or platform_value.get("system")
        != prereg["target_machine_policy"]["platform_system"]
        or platform_value.get("python") != LOCKED_ENVIRONMENT["python"]
        or identity.get("algorithm") != IDENTITY_ALGORITHM
        or identity.get("raw_identifiers_recorded") is not False
        or identity.get("hardware_backed_attestation") is not False
        or combined_digest != combined_machine_identity(machine_digest, gpu_digest)
        or artifacts != expected_artifacts
        or value.get("limitations") != expected_limitations
        or expected_artifacts["replay_artifact"]["sha256"]
        == ORIGIN_REPLAY_ARTIFACT_SHA256
        or expected_artifacts["replay_evidence"]["sha256"]
        == ORIGIN_REPLAY_EVIDENCE_SHA256
    ):
        _fail(
            "MACHINE_RECEIPT_RECOMPUTATION_MISMATCH",
            "$.target_machine_receipt",
            "fields drifted",
        )
    distinct = (
        machine_digest != CONTROLLER_MACHINE_GUID_SHA256
        and gpu_digest != CONTROLLER_GPU_UUID_SHA256
        and combined_digest != CONTROLLER_COMBINED_IDENTITY_SHA256
    )
    if (
        "distinct_from_controller" in identity
        and identity.get("distinct_from_controller") is not distinct
    ):
        _fail(
            "DISTINCT_MACHINE_DECISION_MISMATCH",
            "$.target_machine_receipt.identity.distinct_from_controller",
            repr(identity.get("distinct_from_controller")),
        )
    result = copy.deepcopy(dict(value))
    result["identity"]["distinct_from_controller"] = distinct
    return result


def classify_qualification(requirements: Mapping[str, bool]) -> dict[str, Any]:
    """Apply the frozen all-requirements portable qualification rubric."""

    if set(requirements) != set(REQUIREMENT_KEYS) or any(
        type(value) is not bool for value in requirements.values()
    ):
        _fail(
            "INVALID_QUALIFICATION_REQUIREMENTS", "$.requirements", repr(requirements)
        )
    blockers = sorted(
        REQUIREMENT_BLOCKERS[name]
        for name, passed in requirements.items()
        if not passed
    )
    qualified = not blockers
    return {
        "requirements": dict(sorted(requirements.items())),
        "blocking_findings": blockers,
        "blocking_finding_count": len(blockers),
        "portable_package_eligible": qualified,
        "classification": PASS_CLASSIFICATION
        if qualified
        else INCOMPLETE_CLASSIFICATION,
    }


def build_qualification_evidence(
    preregistration: Mapping[str, Any],
    *,
    preregistration_sha256: str,
    protocol_freeze_commit: str,
    preferred_evidence_payload: bytes,
    preferred_validation: Mapping[str, Any],
    replay_artifact_payload: bytes,
    replay_evidence_payload: bytes,
    target_replay_validation: Mapping[str, Any],
    target_machine_receipt: Mapping[str, Any],
    protocol_source_payloads: Mapping[str, bytes],
) -> dict[str, Any]:
    """Build one categorical qualification from independently validated inputs."""

    prereg = validate_preregistration(preregistration)
    _validate_sha256(preregistration_sha256, "$.preregistration.sha256")
    if GIT_COMMIT_PATTERN.fullmatch(protocol_freeze_commit) is None:
        _fail(
            "INVALID_PROTOCOL_FREEZE_COMMIT",
            "$.protocol_freeze_commit",
            protocol_freeze_commit,
        )
    _require_payload_sha256(
        preferred_evidence_payload, PREFERRED_EVIDENCE_SHA256, "$.preferred_evidence"
    )
    if copy.deepcopy(dict(preferred_validation)) != EXPECTED_PREFERRED_VALIDATION:
        _fail(
            "PREFERRED_VALIDATION_MISMATCH",
            "$.preferred_validation",
            "canonical projection drifted",
        )
    if (
        copy.deepcopy(dict(target_replay_validation))
        != EXPECTED_TARGET_REPLAY_VALIDATION
    ):
        _fail(
            "TARGET_REPLAY_VALIDATION_MISMATCH",
            "$.target_replay_validation",
            "canonical projection drifted",
        )
    protocol_receipts = _validate_protocol_sources(prereg, protocol_source_payloads)
    receipt = validate_machine_receipt(
        prereg,
        target_machine_receipt,
        replay_artifact_payload=replay_artifact_payload,
        replay_evidence_payload=replay_evidence_payload,
    )
    replay = _mapping(
        parse_strict_json_bytes(
            replay_artifact_payload, path="$.target_replay_artifact"
        ),
        "$.target_replay_artifact",
    )
    replay_evidence = _mapping(
        parse_strict_json_bytes(
            replay_evidence_payload, path="$.target_replay_evidence"
        ),
        "$.target_replay_evidence",
    )
    if artifact_json_bytes(replay) != replay_artifact_payload:
        _fail(
            "TARGET_REPLAY_ARTIFACT_ENCODING_MISMATCH",
            "$.target_replay_artifact",
            "not canonical tracked encoding",
        )
    if artifact_json_bytes(replay_evidence) != replay_evidence_payload:
        _fail(
            "TARGET_REPLAY_EVIDENCE_ENCODING_MISMATCH",
            "$.target_replay_evidence",
            "not canonical tracked encoding",
        )
    comparison = _mapping(
        replay_evidence.get("comparison"), "$.target_replay_evidence.comparison"
    )
    replay_receipt = _mapping(
        replay_evidence.get("replay_artifact"),
        "$.target_replay_evidence.replay_artifact",
    )
    replay_gates = _mapping(
        replay_evidence.get("gates"), "$.target_replay_evidence.gates"
    )
    replay_resources = _mapping(
        replay_evidence.get("resources"), "$.target_replay_evidence.resources"
    )
    run = _mapping(replay.get("run"), "$.target_replay_artifact.run")
    target_environment = _mapping(
        replay.get("environment"), "$.target_replay_artifact.environment"
    )
    precision = _mapping(
        replay.get("precision_audit"), "$.target_replay_artifact.precision_audit"
    )

    raw_exact = (
        comparison.get("records_expected") == 20
        and comparison.get("records_observed") == 20
        and comparison.get("raw_outputs_exact") == 20
        and comparison.get("raw_outputs_digest_reference") == EXPECTED_RAW_OUTPUT_DIGEST
        and comparison.get("raw_outputs_digest_observed") == EXPECTED_RAW_OUTPUT_DIGEST
        and comparison.get("raw_mismatch_example_ids") == []
    )
    compiled_exact = (
        comparison.get("compiled_outputs_exact") == 20
        and comparison.get("compiled_outputs_digest_reference")
        == EXPECTED_COMPILED_OUTPUT_DIGEST
        and comparison.get("compiled_outputs_digest_observed")
        == EXPECTED_COMPILED_OUTPUT_DIGEST
        and comparison.get("compiled_mismatch_example_ids") == []
        and comparison.get("compilation_failures") == []
    )
    execution_passed = (
        run.get("fresh_model_loads") == 1
        and run.get("full_eval_runs") == 1
        and run.get("generate_calls") == 20
        and run.get("retries") == 0
        and run.get("completed") is True
        and precision.get("attached_execution_form") == "attached_factorized_lora"
        and replay.get("historical_adapter_base_path_used") is False
        and replay.get("model_artifact_saved") is False
        and replay.get("tensor_payload_saved") is False
    )
    package_passed = all(
        replay_gates.get(name) is True
        for name in (
            "metadata_validation",
            "materialization",
            "clean_location_resolution",
        )
    )
    replay_receipt_passed = replay_receipt == {
        "path": REPLAY_LOGICAL_ARTIFACT_PATH,
        "bytes": len(replay_artifact_payload),
        "sha256": sha256_bytes(replay_artifact_payload),
    }
    offline_passed = (
        replay.get("execution_network_used") is False
        and replay_evidence.get("offline_execution") is True
    )
    limitations_disclosed = all(
        prereg["qualification_scope"].get(name) is False
        for name in (
            "cross_driver_claim",
            "cross_library_claim",
            "hardware_backed_attestation_claim",
            "external_execution_count_attestation_claim",
            "promotion_serving_or_runtime_decision",
        )
    )
    requirements = {
        "attached_execution_contract_passed": execution_passed
        and replay_gates.get("execution_contract") is True,
        "cross_machine_compiled_outputs_exact": compiled_exact,
        "cross_machine_raw_outputs_exact": raw_exact,
        "limitations_disclosed": limitations_disclosed,
        "locked_environment_reproduced": dict(target_environment) == LOCKED_ENVIRONMENT
        and replay_gates.get("environment") is True,
        "offline_execution_passed": offline_passed,
        "package_identity_and_clean_resolution_passed": (
            package_passed and replay_receipt_passed
        ),
        "preferred_candidate_gate_valid": True,
        "protocol_integrity": True,
        "registered_resource_caps_passed": replay_gates.get("resources") is True
        and replay_resources.get("passed") is True,
        "target_machine_identity_receipt_valid": True,
        "target_machine_is_distinct": receipt["identity"]["distinct_from_controller"]
        is True,
        "target_replay_gate_valid": True,
    }
    decision = classify_qualification(requirements)
    qualified = decision["portable_package_eligible"] is True
    next_gate = PASS_NEXT_GATE_ID if qualified else FAILURE_NEXT_GATE_ID

    evidence: dict[str, Any] = {
        "evidence_version": EVIDENCE_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "gate_id": GATE_ID,
        "package_id": PACKAGE_ID,
        "candidate_id": CANDIDATE_ID,
        "preregistration": {
            "path": PREREGISTRATION_PATH,
            "sha256": preregistration_sha256,
            "freeze_status": "frozen",
        },
        "protocol_freeze_commit": protocol_freeze_commit,
        "protocol_sources": protocol_receipts,
        "preferred_candidate_evidence": {
            "path": PREFERRED_EVIDENCE_PATH,
            "sha256": PREFERRED_EVIDENCE_SHA256,
            "validation": copy.deepcopy(dict(preferred_validation)),
        },
        "target_replay": {
            "artifact": copy.deepcopy(receipt["target_artifacts"]["replay_artifact"]),
            "evidence": copy.deepcopy(receipt["target_artifacts"]["replay_evidence"]),
            "validation": copy.deepcopy(dict(target_replay_validation)),
            "environment": copy.deepcopy(dict(target_environment)),
            "run": copy.deepcopy(dict(run)),
            "comparison": copy.deepcopy(dict(comparison)),
            "resources": copy.deepcopy(dict(replay_resources)),
        },
        "target_machine_receipt": receipt,
        "qualification_decision": decision,
        "gates": dict(sorted(requirements.items())),
        "classification": decision["classification"],
        "formal_gate_passed": qualified,
        "derived_claims": {
            "offline_artifact_eligible": True,
            "preferred_offline_candidate": True,
            "cross_machine_reproducibility_established": qualified,
            "cross_machine_reproducibility_scope": (
                "one_operationally_distinct_windows_target_exact_twenty_case_"
                "replay_under_locked_user_space_environment_and_same_gpu_class"
            ),
            "portable_package_eligible": qualified,
            "portable_package_eligibility_scope": (
                "fixed_compiler_attached_execution_locked_environment_only"
            ),
            "serving_readiness_established": False,
            "artifact_promotion_allowed": False,
            "merged_artifact_allowed": False,
            "runtime_eligible": False,
        },
        "remaining_blocking_findings": copy.deepcopy(decision["blocking_findings"]),
        "remaining_blocking_finding_count": decision["blocking_finding_count"],
        "locked_next_action": {
            "gate_id": next_gate,
            "action": prereg["outcome_next_actions"][
                "qualified" if qualified else "incomplete"
            ]["action"],
            "eligible_to_start": qualified,
            "classification": decision["classification"],
            "formal_gate_passed": qualified,
            "portable_package_eligible": qualified,
            "artifact_promotion_allowed": False,
            "serving_integration_allowed": False,
            "runtime_integration_allowed": False,
        },
        "limitations": {
            "controller_anchor_is_historical_reference_execution_attestation": False,
            "target_receipt_is_hardware_backed_attestation": False,
            "external_execution_count_attested": False,
            "alternate_execution_excluded": False,
            "cross_driver_reproducibility_established": False,
            "cross_library_reproducibility_established": False,
            "repeat_variance_established": False,
            "generalization_established": False,
            "serving_capacity_latency_or_cost_established": False,
        },
        "constraints": _constraints(),
        "claims": {
            **_false_claims(),
            "offline_artifact_eligible": True,
            "preferred_offline_candidate": True,
            "cross_machine_reproducibility_established": qualified,
            "portable_package_eligible": qualified,
            "target_replay_validator_recomputed": True,
            "preferred_candidate_validator_recomputed": True,
            "network_used_during_target_execution": False,
        },
        "model_artifact_saved": False,
        "tensor_payload_saved": False,
        "runtime_eligible": False,
    }
    evidence["report_digest"] = sha256_bytes(canonical_json_bytes(evidence))
    return evidence


def validate_qualification_evidence(
    preregistration_payload: bytes,
    evidence_payload: bytes,
    *,
    expected_preregistration_sha256: str,
    expected_evidence_sha256: str,
    expected_protocol_freeze_commit: str,
    preferred_evidence_payload: bytes,
    preferred_validation: Mapping[str, Any],
    replay_artifact_payload: bytes,
    replay_evidence_payload: bytes,
    target_replay_validation: Mapping[str, Any],
    protocol_source_payloads: Mapping[str, bytes],
) -> dict[str, Any]:
    """Authenticate and recompute one formal qualification artifact."""

    _require_payload_sha256(
        preregistration_payload, expected_preregistration_sha256, "$.preregistration"
    )
    _require_payload_sha256(evidence_payload, expected_evidence_sha256, "$.evidence")
    prereg = _mapping(
        parse_strict_json_bytes(preregistration_payload, path="$.preregistration"),
        "$.preregistration",
    )
    actual = _mapping(
        parse_strict_json_bytes(evidence_payload, path="$.evidence"), "$.evidence"
    )
    machine_receipt = _mapping(
        actual.get("target_machine_receipt"), "$.evidence.target_machine_receipt"
    )
    expected = build_qualification_evidence(
        prereg,
        preregistration_sha256=expected_preregistration_sha256,
        protocol_freeze_commit=expected_protocol_freeze_commit,
        preferred_evidence_payload=preferred_evidence_payload,
        preferred_validation=preferred_validation,
        replay_artifact_payload=replay_artifact_payload,
        replay_evidence_payload=replay_evidence_payload,
        target_replay_validation=target_replay_validation,
        target_machine_receipt=machine_receipt,
        protocol_source_payloads=protocol_source_payloads,
    )
    if actual != expected:
        _fail("EVIDENCE_RECOMPUTATION_MISMATCH", "$.evidence", "fields drifted")
    if artifact_json_bytes(actual) != evidence_payload:
        _fail(
            "EVIDENCE_ENCODING_MISMATCH", "$.evidence", "not canonical tracked encoding"
        )
    return {
        "frozen_gate_valid": True,
        "classification": expected["classification"],
        "formal_gate_passed": expected["formal_gate_passed"],
        "offline_artifact_eligible": expected["derived_claims"][
            "offline_artifact_eligible"
        ],
        "preferred_offline_candidate": expected["derived_claims"][
            "preferred_offline_candidate"
        ],
        "cross_machine_reproducibility_established": expected["derived_claims"][
            "cross_machine_reproducibility_established"
        ],
        "portable_package_eligible": expected["derived_claims"][
            "portable_package_eligible"
        ],
        "remaining_blocking_findings": expected["remaining_blocking_findings"],
        "next_gate": expected["locked_next_action"]["gate_id"],
        "runtime_eligible": False,
    }


def _validate_protocol_sources(
    preregistration: Mapping[str, Any], payloads: Mapping[str, bytes]
) -> dict[str, dict[str, Any]]:
    if set(payloads) != set(PROTOCOL_SOURCE_PATHS):
        _fail(
            "INVALID_PROTOCOL_SOURCE_KEYS", "$.protocol_sources", repr(sorted(payloads))
        )
    expected = _mapping(
        _mapping(preregistration.get("source_lineage"), "$.source_lineage").get(
            "protocol_sources"
        ),
        "$.source_lineage.protocol_sources",
    )
    receipts: dict[str, dict[str, Any]] = {}
    for name, relative in PROTOCOL_SOURCE_PATHS.items():
        payload = payloads[name]
        actual_sha = sha256_bytes(payload)
        expected_receipt = _mapping(expected.get(name), f"$.protocol_sources.{name}")
        if expected_receipt != {"path": relative, "sha256": actual_sha}:
            _fail(
                "PROTOCOL_SOURCE_HASH_MISMATCH",
                f"$.protocol_sources.{name}",
                actual_sha,
            )
        receipts[name] = {"path": relative, "bytes": len(payload), "sha256": actual_sha}
    return dict(sorted(receipts.items()))


def _constraints() -> dict[str, bool]:
    return {
        "adapter_or_weight_mutation": False,
        "artifact_promotion": False,
        "base_or_tokenizer_substitution": False,
        "decision_compiler_change": False,
        "desktop_integration": False,
        "eval_answer_tuning": False,
        "execution_form_change": False,
        "generation_change": False,
        "mcp_integration": False,
        "merged_weight_creation": False,
        "new_data": False,
        "precision_change": False,
        "prompt_change": False,
        "provider_integration": False,
        "runtime_integration": False,
        "serving_integration": False,
        "training": False,
    }


def _false_claims() -> dict[str, bool]:
    return {
        "artifact_promotion_allowed": False,
        "cross_driver_reproducibility_established": False,
        "cross_library_reproducibility_established": False,
        "cross_machine_reproducibility_established": False,
        "hardware_backed_machine_attestation": False,
        "merged_artifact_allowed": False,
        "offline_artifact_eligible": False,
        "portable_package_eligible": False,
        "preferred_offline_candidate": False,
        "runtime_eligible": False,
        "serving_readiness_established": False,
    }


def _require_payload_sha256(payload: bytes, expected: str, path: str) -> None:
    _validate_sha256(expected, f"{path}.sha256")
    actual = sha256_bytes(payload)
    if actual != expected:
        _fail("PAYLOAD_SHA256_MISMATCH", path, actual)


def _validate_sha256(value: str, path: str) -> None:
    if (
        not isinstance(value, str)
        or SHA256_PATTERN.fullmatch(value) is None
        or value == ZERO_SHA256
    ):
        _fail("INVALID_SHA256", path, repr(value))


def _mapping(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail("INVALID_OBJECT", path, type(value).__name__)
    return value


def _validate_finite_json(value: Any, path: str) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        _fail("NONFINITE_NUMBER", path, repr(value))
    if isinstance(value, dict):
        for key, nested in value.items():
            if not isinstance(key, str):
                _fail("INVALID_JSON_KEY", path, repr(key))
            _validate_finite_json(nested, f"{path}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _validate_finite_json(nested, f"{path}[{index}]")


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate key: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> NoReturn:
    raise ValueError(f"non-finite JSON constant: {value}")


def _fail(code: str, path: str, detail: str) -> NoReturn:
    raise PortablePackageQualificationError(f"{code} at {path}: {detail}")


__all__ = [
    "PortablePackageQualificationError",
    "artifact_json_bytes",
    "build_qualification_evidence",
    "classify_qualification",
    "combined_machine_identity",
    "expected_preregistration",
    "identity_source_digest",
    "parse_strict_json_bytes",
    "sha256_bytes",
    "validate_machine_receipt",
    "validate_preregistration",
    "validate_qualification_evidence",
]
