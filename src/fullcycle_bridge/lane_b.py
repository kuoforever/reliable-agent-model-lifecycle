"""Fail-closed Lane B consent, capture, and deletion contract v1.

Lane B is deliberately separate from the automatic redacted Runtime export.
This module validates a quarantine-stage review bundle; it does not capture a
desktop, grant execution authority, or make an episode eligible for training.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, NoReturn, Sequence

LANE_B_BUNDLE_VERSION = 1
LANE_B_CONSENT_VERSION = 1
LANE_B_EPISODE_VERSION = 1
LANE_B_DELETION_RECEIPT_VERSION = 1

MAX_BUNDLE_BYTES = 2 * 1024 * 1024
MAX_ARTIFACT_BYTES = 16 * 1024 * 1024
MAX_TOTAL_ARTIFACT_BYTES = 24 * 1024 * 1024
MAX_ARTIFACTS = 32
MAX_STEPS = 128
MAX_ARGUMENT_FIELDS = 20
MAX_TEXT_LENGTH = 4096

SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
IDENTIFIER_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
UTC_SECONDS_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

DATA_CLASSES = (
    "sanitized_instruction",
    "uia_document_ocr_observation",
    "screenshot_or_crop_reference",
    "model_candidate_action",
    "runtime_policy_or_approval_decision",
    "tool_result_and_post_action_observation",
    "state_verifier_label",
)
PURPOSES = ("multimodal_training_and_evaluation_review",)
FORBIDDEN_CONTENT_FIELDS = frozenset(
    {
        "api_keys_or_tokens",
        "assigned_secret_plaintext",
        "memory_database",
        "continuation_data",
        "cooperative_control_record",
        "authority_handoff_or_resume_state",
        "unredacted_sensitive_content",
    }
)
ARTIFACT_ROLES = frozenset(
    {
        "sanitized_instruction",
        "uia_document_ocr",
        "screenshot_or_crop",
        "model_candidate_action",
        "runtime_policy_decision",
        "tool_result",
        "pre_action_observation",
        "post_action_observation",
        "state_verifier_evidence",
    }
)
REQUIRED_ARTIFACT_ROLES = frozenset(
    {
        "sanitized_instruction",
        "pre_action_observation",
        "post_action_observation",
        "state_verifier_evidence",
    }
)


class LaneBValidationError(ValueError):
    """Stable fail-closed validation error for fixtures and offline CI."""

    def __init__(self, code: str, location: str, detail: str = "") -> None:
        self.code = code
        self.location = location
        self.detail = detail
        message = f"{code} at {location}"
        if detail:
            message += f": {detail}"
        super().__init__(message)


@dataclass(frozen=True)
class LaneBValidationSummary:
    bundle_version: int
    consent_id: str
    session_id: str
    episode_id: str
    artifact_count: int
    step_count: int
    data_class: str
    training_use: str
    training_eligible: bool
    deletion_verified: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_json(value: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def validate_bundle_file(path: Path) -> LaneBValidationSummary:
    payload = _read_regular_file_once(path)
    value = _parse_strict_json_bytes(payload)
    return validate_bundle(value)


def validate_bundle(value: object) -> LaneBValidationSummary:
    bundle = _mapping(value, "$")
    _exact_fields(
        bundle,
        {
            "lane_b_bundle_version",
            "consent",
            "episode",
            "deletion_receipt",
        },
        "$",
    )
    _exact_integer(
        bundle.get("lane_b_bundle_version"),
        LANE_B_BUNDLE_VERSION,
        "$.lane_b_bundle_version",
        "UNSUPPORTED_VERSION",
    )
    consent = validate_consent(bundle.get("consent"))
    episode = validate_episode(bundle.get("episode"), consent)
    deletion = validate_deletion_receipt(
        bundle.get("deletion_receipt"), consent, episode
    )
    return LaneBValidationSummary(
        bundle_version=LANE_B_BUNDLE_VERSION,
        consent_id=consent["consent_id"],
        session_id=consent["session_id"],
        episode_id=episode["episode_id"],
        artifact_count=len(episode["artifacts"]),
        step_count=len(episode["steps"]),
        data_class=episode["data_class"],
        training_use=episode["training_use"],
        training_eligible=episode["governance"]["training_eligible"],
        deletion_verified=deletion["verifier"]["deletion_verified"],
    )


def validate_consent(value: object) -> dict[str, Any]:
    location = "$.consent"
    consent = _mapping(value, location)
    _exact_fields(
        consent,
        {
            "lane_b_consent_version",
            "consent_id",
            "session_id",
            "decision",
            "operator_action",
            "scope",
            "capture_controls",
            "retention",
            "forbidden_content",
            "authority",
        },
        location,
    )
    _exact_integer(
        consent.get("lane_b_consent_version"),
        LANE_B_CONSENT_VERSION,
        f"{location}.lane_b_consent_version",
        "UNSUPPORTED_VERSION",
    )
    _identifier(consent.get("consent_id"), f"{location}.consent_id")
    _identifier(consent.get("session_id"), f"{location}.session_id")
    _exact_string(consent.get("decision"), "granted", f"{location}.decision")

    operator = _mapping(consent.get("operator_action"), f"{location}.operator_action")
    _exact_fields(
        operator,
        {"granted_at_utc", "expires_at_utc", "visible_indicator_acknowledged"},
        f"{location}.operator_action",
    )
    granted_at = _timestamp(
        operator.get("granted_at_utc"), f"{location}.operator_action.granted_at_utc"
    )
    expires_at = _timestamp(
        operator.get("expires_at_utc"), f"{location}.operator_action.expires_at_utc"
    )
    _require_true(
        operator.get("visible_indicator_acknowledged"),
        f"{location}.operator_action.visible_indicator_acknowledged",
    )
    if expires_at <= granted_at:
        _fail("INVALID_CONSENT_WINDOW", f"{location}.operator_action")

    scope = _mapping(consent.get("scope"), f"{location}.scope")
    _exact_fields(
        scope,
        {"data_classes", "purposes", "application_scope", "network_upload_allowed"},
        f"{location}.scope",
    )
    _exact_string_list(
        scope.get("data_classes"), DATA_CLASSES, f"{location}.scope.data_classes"
    )
    _exact_string_list(scope.get("purposes"), PURPOSES, f"{location}.scope.purposes")
    applications = _nonempty_unique_string_list(
        scope.get("application_scope"), f"{location}.scope.application_scope"
    )
    if any("*" in item or item.lower() == "all" for item in applications):
        _fail("WILDCARD_SCOPE_FORBIDDEN", f"{location}.scope.application_scope")
    _require_false(
        scope.get("network_upload_allowed"),
        f"{location}.scope.network_upload_allowed",
    )

    controls = _mapping(consent.get("capture_controls"), f"{location}.capture_controls")
    true_controls = {
        "disabled_by_default",
        "run_scoped",
        "separate_adapter",
        "separate_storage_namespace",
        "visible_indicator_required",
        "local_sanitization_before_write",
        "image_redaction_before_write",
        "content_addressed_artifacts",
        "deletion_supported",
    }
    false_controls = {"automatic_runtime_export", "background_capture"}
    _exact_fields(
        controls, true_controls | false_controls, f"{location}.capture_controls"
    )
    for key in true_controls:
        _require_true(controls.get(key), f"{location}.capture_controls.{key}")
    for key in false_controls:
        _require_false(controls.get(key), f"{location}.capture_controls.{key}")

    retention = _mapping(consent.get("retention"), f"{location}.retention")
    _exact_fields(
        retention,
        {"policy_id", "max_days", "delete_by_utc", "operator_delete_on_request"},
        f"{location}.retention",
    )
    _identifier(retention.get("policy_id"), f"{location}.retention.policy_id")
    max_days = _bounded_integer(
        retention.get("max_days"), 1, 90, f"{location}.retention.max_days"
    )
    delete_by = _timestamp(
        retention.get("delete_by_utc"), f"{location}.retention.delete_by_utc"
    )
    _require_true(
        retention.get("operator_delete_on_request"),
        f"{location}.retention.operator_delete_on_request",
    )
    if delete_by < expires_at or delete_by > granted_at + timedelta(days=max_days):
        _fail("INVALID_RETENTION_WINDOW", f"{location}.retention")

    forbidden = _mapping(
        consent.get("forbidden_content"), f"{location}.forbidden_content"
    )
    _exact_fields(forbidden, FORBIDDEN_CONTENT_FIELDS, f"{location}.forbidden_content")
    for key in FORBIDDEN_CONTENT_FIELDS:
        _require_true(forbidden.get(key), f"{location}.forbidden_content.{key}")

    authority = _mapping(consent.get("authority"), f"{location}.authority")
    _exact_fields(
        authority,
        {
            "model_output_is_authority",
            "grants_execution_permission",
            "runtime_policy_bypass_allowed",
            "runner_mcp_desktop_bypass_allowed",
            "state_verifier_required",
        },
        f"{location}.authority",
    )
    for key in {
        "model_output_is_authority",
        "grants_execution_permission",
        "runtime_policy_bypass_allowed",
        "runner_mcp_desktop_bypass_allowed",
    }:
        _require_false(authority.get(key), f"{location}.authority.{key}")
    _require_true(
        authority.get("state_verifier_required"),
        f"{location}.authority.state_verifier_required",
    )
    return dict(consent)


def validate_episode(value: object, consent: Mapping[str, Any]) -> dict[str, Any]:
    location = "$.episode"
    episode = _mapping(value, location)
    _exact_fields(
        episode,
        {
            "lane_b_episode_version",
            "episode_id",
            "consent_binding",
            "data_class",
            "training_use",
            "capture",
            "versions",
            "artifacts",
            "steps",
            "governance",
        },
        location,
    )
    _exact_integer(
        episode.get("lane_b_episode_version"),
        LANE_B_EPISODE_VERSION,
        f"{location}.lane_b_episode_version",
        "UNSUPPORTED_VERSION",
    )
    _identifier(episode.get("episode_id"), f"{location}.episode_id")

    binding = _mapping(episode.get("consent_binding"), f"{location}.consent_binding")
    _exact_fields(
        binding,
        {"consent_id", "session_id", "consent_sha256"},
        f"{location}.consent_binding",
    )
    if (
        binding.get("consent_id") != consent["consent_id"]
        or binding.get("session_id") != consent["session_id"]
        or binding.get("consent_sha256") != sha256_json(consent)
    ):
        _fail("CONSENT_BINDING_MISMATCH", f"{location}.consent_binding")
    _exact_string(
        episode.get("data_class"),
        "explicit_consent_rich_training_episode",
        f"{location}.data_class",
    )
    _exact_string(
        episode.get("training_use"),
        "quarantine_review_only",
        f"{location}.training_use",
    )

    capture = _mapping(episode.get("capture"), f"{location}.capture")
    _exact_fields(
        capture,
        {
            "captured_at_utc",
            "adapter_id",
            "storage_namespace",
            "indicator_visible",
            "sanitization_completed_before_write",
            "image_redaction_completed_before_write",
            "automatic_runtime_export",
            "network_upload_used",
            "source_safe_trace_modified",
        },
        f"{location}.capture",
    )
    captured_at = _timestamp(
        capture.get("captured_at_utc"), f"{location}.capture.captured_at_utc"
    )
    granted_at = _timestamp(
        consent["operator_action"]["granted_at_utc"],
        "$.consent.operator_action.granted_at_utc",
    )
    expires_at = _timestamp(
        consent["operator_action"]["expires_at_utc"],
        "$.consent.operator_action.expires_at_utc",
    )
    if captured_at < granted_at or captured_at > expires_at:
        _fail("CAPTURE_OUTSIDE_CONSENT_WINDOW", f"{location}.capture.captured_at_utc")
    _identifier(capture.get("adapter_id"), f"{location}.capture.adapter_id")
    namespace = _string(
        capture.get("storage_namespace"), f"{location}.capture.storage_namespace"
    )
    if not namespace.startswith("lane-b/") or _unsafe_relative_path(namespace):
        _fail("INVALID_STORAGE_NAMESPACE", f"{location}.capture.storage_namespace")
    for key in {
        "indicator_visible",
        "sanitization_completed_before_write",
        "image_redaction_completed_before_write",
    }:
        _require_true(capture.get(key), f"{location}.capture.{key}")
    for key in {
        "automatic_runtime_export",
        "network_upload_used",
        "source_safe_trace_modified",
    }:
        _require_false(capture.get(key), f"{location}.capture.{key}")

    _validate_versions(episode.get("versions"), location)
    artifacts, artifact_roles = _validate_artifacts(episode.get("artifacts"), location)
    _validate_steps(episode.get("steps"), artifacts, artifact_roles, location)
    governance = _mapping(episode.get("governance"), f"{location}.governance")
    _exact_fields(
        governance,
        {
            "dataset_split",
            "license_status",
            "training_eligible",
            "human_review_required",
            "retention_enforced",
            "deletion_supported",
        },
        f"{location}.governance",
    )
    _exact_string(
        governance.get("dataset_split"),
        "unassigned",
        f"{location}.governance.dataset_split",
    )
    _exact_string(
        governance.get("license_status"),
        "pending_review",
        f"{location}.governance.license_status",
    )
    _require_false(
        governance.get("training_eligible"), f"{location}.governance.training_eligible"
    )
    for key in {"human_review_required", "retention_enforced", "deletion_supported"}:
        _require_true(governance.get(key), f"{location}.governance.{key}")
    return dict(episode)


def validate_deletion_receipt(
    value: object,
    consent: Mapping[str, Any],
    episode: Mapping[str, Any],
) -> dict[str, Any]:
    location = "$.deletion_receipt"
    receipt = _mapping(value, location)
    _exact_fields(
        receipt,
        {
            "lane_b_deletion_receipt_version",
            "deletion_id",
            "consent_id",
            "session_id",
            "episode_id",
            "episode_sha256",
            "requested_at_utc",
            "completed_at_utc",
            "reason",
            "artifacts",
            "storage_namespace_deleted",
            "remaining_artifact_count",
            "verifier",
        },
        location,
    )
    _exact_integer(
        receipt.get("lane_b_deletion_receipt_version"),
        LANE_B_DELETION_RECEIPT_VERSION,
        f"{location}.lane_b_deletion_receipt_version",
        "UNSUPPORTED_VERSION",
    )
    _identifier(receipt.get("deletion_id"), f"{location}.deletion_id")
    if (
        receipt.get("consent_id") != consent["consent_id"]
        or receipt.get("session_id") != consent["session_id"]
        or receipt.get("episode_id") != episode["episode_id"]
        or receipt.get("episode_sha256") != sha256_json(episode)
    ):
        _fail("DELETION_BINDING_MISMATCH", location)
    requested = _timestamp(
        receipt.get("requested_at_utc"), f"{location}.requested_at_utc"
    )
    completed = _timestamp(
        receipt.get("completed_at_utc"), f"{location}.completed_at_utc"
    )
    captured = _timestamp(
        episode["capture"]["captured_at_utc"], "$.episode.capture.captured_at_utc"
    )
    delete_by = _timestamp(
        consent["retention"]["delete_by_utc"],
        "$.consent.retention.delete_by_utc",
    )
    if requested < captured or completed < requested or completed > delete_by:
        _fail("INVALID_DELETION_TIMELINE", location)
    if receipt.get("reason") not in {
        "fixture_cleanup",
        "operator_request",
        "retention_expiry",
    }:
        _fail("INVALID_ENUM", f"{location}.reason")

    deleted = _sequence(receipt.get("artifacts"), f"{location}.artifacts")
    expected_artifacts = {
        (artifact["artifact_id"], artifact["content_sha256"])
        for artifact in episode["artifacts"]
    }
    observed_artifacts: set[tuple[str, str]] = set()
    for index, item in enumerate(deleted):
        item_location = f"{location}.artifacts[{index}]"
        artifact = _mapping(item, item_location)
        _exact_fields(
            artifact, {"artifact_id", "content_sha256", "status"}, item_location
        )
        _sha256(artifact.get("artifact_id"), f"{item_location}.artifact_id")
        _sha256(artifact.get("content_sha256"), f"{item_location}.content_sha256")
        _exact_string(artifact.get("status"), "deleted", f"{item_location}.status")
        pair = (artifact["artifact_id"], artifact["content_sha256"])
        if pair in observed_artifacts:
            _fail("DUPLICATE_DELETION_ARTIFACT", item_location)
        observed_artifacts.add(pair)
    if observed_artifacts != expected_artifacts:
        _fail("INCOMPLETE_DELETION", f"{location}.artifacts")
    _require_true(
        receipt.get("storage_namespace_deleted"),
        f"{location}.storage_namespace_deleted",
    )
    _exact_integer(
        receipt.get("remaining_artifact_count"),
        0,
        f"{location}.remaining_artifact_count",
        "INCOMPLETE_DELETION",
    )
    verifier = _mapping(receipt.get("verifier"), f"{location}.verifier")
    _exact_fields(
        verifier,
        {"source", "raw_content_retained", "deletion_verified"},
        f"{location}.verifier",
    )
    _exact_string(
        verifier.get("source"),
        "local_storage_state_verifier",
        f"{location}.verifier.source",
    )
    _require_false(
        verifier.get("raw_content_retained"),
        f"{location}.verifier.raw_content_retained",
    )
    _require_true(
        verifier.get("deletion_verified"), f"{location}.verifier.deletion_verified"
    )
    return dict(receipt)


def _validate_versions(value: object, parent: str) -> None:
    location = f"{parent}.versions"
    versions = _mapping(value, location)
    _exact_fields(
        versions,
        {
            "runtime_git_commit",
            "agent_contract_version",
            "driver_contract_version",
            "policy_version",
            "environment_id",
            "model_id",
            "model_revision",
            "lane_b_consent_version",
            "lane_b_episode_version",
        },
        location,
    )
    commit = _string(
        versions.get("runtime_git_commit"), f"{location}.runtime_git_commit"
    )
    if COMMIT_PATTERN.fullmatch(commit) is None or commit == "0" * 40:
        _fail("INVALID_COMMIT", f"{location}.runtime_git_commit")
    for key in {
        "agent_contract_version",
        "driver_contract_version",
        "policy_version",
        "environment_id",
        "model_id",
        "model_revision",
    }:
        _bounded_string(versions.get(key), f"{location}.{key}")
    _exact_integer(
        versions.get("lane_b_consent_version"),
        LANE_B_CONSENT_VERSION,
        f"{location}.lane_b_consent_version",
        "UNSUPPORTED_VERSION",
    )
    _exact_integer(
        versions.get("lane_b_episode_version"),
        LANE_B_EPISODE_VERSION,
        f"{location}.lane_b_episode_version",
        "UNSUPPORTED_VERSION",
    )


def _validate_artifacts(
    value: object, parent: str
) -> tuple[dict[str, Mapping[str, Any]], dict[str, str]]:
    location = f"{parent}.artifacts"
    items = _sequence(value, location)
    if not 1 <= len(items) <= MAX_ARTIFACTS:
        _fail("INVALID_ARTIFACT_COUNT", location)
    artifacts: dict[str, Mapping[str, Any]] = {}
    roles: dict[str, str] = {}
    total_bytes = 0
    for index, item in enumerate(items):
        item_location = f"{location}[{index}]"
        artifact = _mapping(item, item_location)
        _exact_fields(
            artifact,
            {
                "artifact_id",
                "role",
                "media_type",
                "bytes",
                "content_sha256",
                "sanitized",
                "image_redacted",
            },
            item_location,
        )
        artifact_id = _sha256(
            artifact.get("artifact_id"), f"{item_location}.artifact_id"
        )
        content_sha = _sha256(
            artifact.get("content_sha256"), f"{item_location}.content_sha256"
        )
        if artifact_id != content_sha:
            _fail("ARTIFACT_CONTENT_ADDRESS_MISMATCH", item_location)
        if artifact_id in artifacts:
            _fail("DUPLICATE_ARTIFACT", f"{item_location}.artifact_id")
        role = artifact.get("role")
        if role not in ARTIFACT_ROLES:
            _fail("INVALID_ENUM", f"{item_location}.role")
        media_type = artifact.get("media_type")
        if media_type not in {
            "application/json",
            "text/plain",
            "image/png",
            "image/jpeg",
        }:
            _fail("INVALID_ENUM", f"{item_location}.media_type")
        size = _bounded_integer(
            artifact.get("bytes"), 1, MAX_ARTIFACT_BYTES, f"{item_location}.bytes"
        )
        total_bytes += size
        _require_true(artifact.get("sanitized"), f"{item_location}.sanitized")
        if role == "screenshot_or_crop":
            if media_type not in {"image/png", "image/jpeg"}:
                _fail("IMAGE_MEDIA_TYPE_REQUIRED", f"{item_location}.media_type")
            _require_true(
                artifact.get("image_redacted"), f"{item_location}.image_redacted"
            )
        else:
            if media_type in {"image/png", "image/jpeg"}:
                _fail("IMAGE_ROLE_REQUIRED", f"{item_location}.role")
            _require_false(
                artifact.get("image_redacted"), f"{item_location}.image_redacted"
            )
        artifacts[artifact_id] = artifact
        roles[artifact_id] = str(role)
    if total_bytes > MAX_TOTAL_ARTIFACT_BYTES:
        _fail("ARTIFACT_BYTES_EXCEEDED", location)
    if not REQUIRED_ARTIFACT_ROLES.issubset(roles.values()):
        _fail("MISSING_REQUIRED_ARTIFACT_ROLE", location)
    return artifacts, roles


def _validate_steps(
    value: object,
    artifacts: Mapping[str, Mapping[str, Any]],
    roles: Mapping[str, str],
    parent: str,
) -> None:
    location = f"{parent}.steps"
    steps = _sequence(value, location)
    if not 1 <= len(steps) <= MAX_STEPS:
        _fail("INVALID_STEP_COUNT", location)
    for index, item in enumerate(steps):
        step_location = f"{location}[{index}]"
        step = _mapping(item, step_location)
        _exact_fields(
            step,
            {
                "sequence",
                "pre_observation_ref",
                "candidate_action",
                "runtime_decision",
                "tool_result_ref",
                "post_observation_ref",
                "verifier",
            },
            step_location,
        )
        _exact_integer(
            step.get("sequence"),
            index + 1,
            f"{step_location}.sequence",
            "NONCONTIGUOUS_STEPS",
        )
        _artifact_ref(
            step.get("pre_observation_ref"),
            "pre_action_observation",
            artifacts,
            roles,
            f"{step_location}.pre_observation_ref",
        )
        _validate_candidate_action(
            step.get("candidate_action"), artifacts, roles, step_location
        )
        decision = _validate_runtime_decision(
            step.get("runtime_decision"), artifacts, roles, step_location
        )
        tool_result_ref = step.get("tool_result_ref")
        if decision["dispatched"]:
            _artifact_ref(
                tool_result_ref,
                "tool_result",
                artifacts,
                roles,
                f"{step_location}.tool_result_ref",
            )
        elif tool_result_ref is not None:
            _fail("UNDISPATCHED_TOOL_RESULT", f"{step_location}.tool_result_ref")
        _artifact_ref(
            step.get("post_observation_ref"),
            "post_action_observation",
            artifacts,
            roles,
            f"{step_location}.post_observation_ref",
        )
        _validate_verifier(step.get("verifier"), artifacts, roles, step, step_location)


def _validate_candidate_action(
    value: object,
    artifacts: Mapping[str, Mapping[str, Any]],
    roles: Mapping[str, str],
    parent: str,
) -> None:
    location = f"{parent}.candidate_action"
    action = _mapping(value, location)
    _exact_fields(
        action,
        {
            "record_ref",
            "next_tool",
            "arguments",
            "bbox",
            "ref",
            "risk_level",
            "requires_approval",
            "confidence",
            "should_reject",
            "should_fallback",
            "evidence_refs",
            "execution_authority",
        },
        location,
    )
    _artifact_ref(
        action.get("record_ref"),
        "model_candidate_action",
        artifacts,
        roles,
        f"{location}.record_ref",
    )
    next_tool = action.get("next_tool")
    if next_tool is not None:
        _bounded_string(next_tool, f"{location}.next_tool")
    arguments = _mapping(action.get("arguments"), f"{location}.arguments")
    if len(arguments) > MAX_ARGUMENT_FIELDS:
        _fail("TOO_MANY_ARGUMENTS", f"{location}.arguments")
    for key, item in arguments.items():
        _bounded_string(key, f"{location}.arguments.key")
        _scalar(item, f"{location}.arguments.{key}")
    _bbox(action.get("bbox"), f"{location}.bbox")
    if action.get("ref") is not None:
        _bounded_string(action.get("ref"), f"{location}.ref")
    if action.get("risk_level") not in {"low", "medium", "high", "critical"}:
        _fail("INVALID_ENUM", f"{location}.risk_level")
    requires_approval = _boolean(
        action.get("requires_approval"), f"{location}.requires_approval"
    )
    should_reject = _boolean(action.get("should_reject"), f"{location}.should_reject")
    should_fallback = _boolean(
        action.get("should_fallback"), f"{location}.should_fallback"
    )
    confidence = action.get("confidence")
    if (
        isinstance(confidence, bool)
        or not isinstance(confidence, (int, float))
        or not math.isfinite(confidence)
        or not 0 <= confidence <= 1
    ):
        _fail("INVALID_CONFIDENCE", f"{location}.confidence")
    evidence_refs = _nonempty_unique_string_list(
        action.get("evidence_refs"), f"{location}.evidence_refs"
    )
    for artifact_id in evidence_refs:
        _sha256(artifact_id, f"{location}.evidence_refs")
        if artifact_id not in artifacts:
            _fail("UNKNOWN_ARTIFACT_REF", f"{location}.evidence_refs")
    _exact_string(
        action.get("execution_authority"), "none", f"{location}.execution_authority"
    )
    if should_reject and should_fallback:
        _fail("INVALID_CANDIDATE_MODE", location)
    terminal = should_reject or should_fallback
    if terminal and (
        next_tool is not None
        or arguments
        or action.get("bbox") is not None
        or action.get("ref") is not None
    ):
        _fail("TERMINAL_ACTION_HAS_EXECUTION_FIELDS", location)
    if terminal and requires_approval:
        _fail("TERMINAL_ACTION_REQUIRES_APPROVAL", location)
    if not terminal and next_tool is None:
        _fail("ACTION_TOOL_REQUIRED", f"{location}.next_tool")


def _validate_runtime_decision(
    value: object,
    artifacts: Mapping[str, Mapping[str, Any]],
    roles: Mapping[str, str],
    parent: str,
) -> Mapping[str, Any]:
    location = f"{parent}.runtime_decision"
    decision = _mapping(value, location)
    _exact_fields(
        decision,
        {
            "record_ref",
            "policy_decision",
            "approval_state",
            "dispatched",
            "runtime_is_authority",
        },
        location,
    )
    _artifact_ref(
        decision.get("record_ref"),
        "runtime_policy_decision",
        artifacts,
        roles,
        f"{location}.record_ref",
    )
    if decision.get("policy_decision") not in {
        "allow",
        "deny",
        "approval_required",
        "reobserve",
        "defer",
    }:
        _fail("INVALID_ENUM", f"{location}.policy_decision")
    if decision.get("approval_state") not in {
        "not_required",
        "pending",
        "approved",
        "denied",
    }:
        _fail("INVALID_ENUM", f"{location}.approval_state")
    dispatched = _boolean(decision.get("dispatched"), f"{location}.dispatched")
    _require_true(
        decision.get("runtime_is_authority"), f"{location}.runtime_is_authority"
    )
    if dispatched and (
        decision.get("policy_decision") != "allow"
        or decision.get("approval_state") not in {"not_required", "approved"}
    ):
        _fail("INVALID_RUNTIME_DISPATCH", location)
    if (
        not dispatched
        and decision.get("policy_decision") == "allow"
        and decision.get("approval_state") in {"not_required", "approved"}
    ):
        _fail("ALLOW_DECISION_NOT_DISPATCHED", location)
    state = (
        decision.get("policy_decision"),
        decision.get("approval_state"),
        dispatched,
    )
    allowed_states = {
        ("allow", "not_required", True),
        ("allow", "approved", True),
        ("deny", "not_required", False),
        ("deny", "denied", False),
        ("approval_required", "pending", False),
        ("reobserve", "not_required", False),
        ("defer", "not_required", False),
    }
    if state not in allowed_states:
        _fail("INVALID_RUNTIME_STATE", location)
    return decision


def _validate_verifier(
    value: object,
    artifacts: Mapping[str, Mapping[str, Any]],
    roles: Mapping[str, str],
    step: Mapping[str, Any],
    parent: str,
) -> None:
    location = f"{parent}.verifier"
    verifier = _mapping(value, location)
    _exact_fields(
        verifier,
        {"source", "label", "evidence_refs", "model_self_report_used"},
        location,
    )
    _exact_string(verifier.get("source"), "state_based", f"{location}.source")
    if verifier.get("label") not in {"success", "failure", "unknown"}:
        _fail("INVALID_ENUM", f"{location}.label")
    refs = _nonempty_unique_string_list(
        verifier.get("evidence_refs"), f"{location}.evidence_refs"
    )
    ref_roles: set[str] = set()
    for artifact_id in refs:
        _sha256(artifact_id, f"{location}.evidence_refs")
        if artifact_id not in artifacts:
            _fail("UNKNOWN_ARTIFACT_REF", f"{location}.evidence_refs")
        ref_roles.add(roles[artifact_id])
    if (
        step["post_observation_ref"] not in refs
        or "state_verifier_evidence" not in ref_roles
    ):
        _fail("VERIFIER_EVIDENCE_INCOMPLETE", f"{location}.evidence_refs")
    _require_false(
        verifier.get("model_self_report_used"), f"{location}.model_self_report_used"
    )


def _artifact_ref(
    value: object,
    expected_role: str,
    artifacts: Mapping[str, Mapping[str, Any]],
    roles: Mapping[str, str],
    location: str,
) -> str:
    artifact_id = _sha256(value, location)
    if artifact_id not in artifacts:
        _fail("UNKNOWN_ARTIFACT_REF", location)
    if roles[artifact_id] != expected_role:
        _fail("ARTIFACT_ROLE_MISMATCH", location)
    return artifact_id


def _parse_strict_json_bytes(payload: bytes) -> object:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        _fail("INVALID_UTF8", "$", str(exc))

    def reject_constant(value: str) -> NoReturn:
        _fail("NONFINITE_NUMBER", "$", value)

    def reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, item in pairs:
            if key in result:
                _fail("DUPLICATE_JSON_KEY", "$", key)
            result[key] = item
        return result

    try:
        return json.loads(
            text,
            object_pairs_hook=reject_duplicates,
            parse_constant=reject_constant,
        )
    except LaneBValidationError:
        raise
    except (json.JSONDecodeError, RecursionError) as exc:
        _fail("MALFORMED_JSON", "$", str(exc))


def _read_regular_file_once(path: Path) -> bytes:
    try:
        before = path.lstat()
    except OSError as exc:
        _fail("UNSAFE_INPUT_FILE", str(path), str(exc))
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    if (
        not path.is_absolute()
        or not stat.S_ISREG(before.st_mode)
        or path.is_symlink()
        or bool(getattr(before, "st_file_attributes", 0) & reparse_flag)
        or before.st_nlink != 1
        or before.st_size <= 0
        or before.st_size > MAX_BUNDLE_BYTES
    ):
        _fail("UNSAFE_INPUT_FILE", str(path))
    try:
        with path.open("rb") as stream:
            opened = os.fstat(stream.fileno())
            payload = stream.read()
            opened_after = os.fstat(stream.fileno())
        after = path.lstat()
    except OSError as exc:
        _fail("UNSAFE_INPUT_FILE", str(path), str(exc))
    signatures = {
        (item.st_dev, item.st_ino, item.st_mode, item.st_size, item.st_mtime_ns)
        for item in (before, opened, opened_after, after)
    }
    if len(signatures) != 1 or len(payload) != after.st_size:
        _fail("INPUT_CHANGED_DURING_READ", str(path))
    return payload


def _mapping(value: object, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail("EXPECTED_OBJECT", location)
    return value


def _sequence(value: object, location: str) -> Sequence[Any]:
    if not isinstance(value, list):
        _fail("EXPECTED_ARRAY", location)
    return value


def _exact_fields(
    value: Mapping[str, Any], expected: set[str] | frozenset[str], location: str
) -> None:
    missing = sorted(set(expected) - set(value))
    unknown = sorted(set(value) - set(expected))
    if missing:
        _fail("MISSING_FIELD", location, ",".join(missing))
    if unknown:
        _fail("UNKNOWN_FIELD", location, ",".join(unknown))


def _string(value: object, location: str) -> str:
    if not isinstance(value, str):
        _fail("EXPECTED_STRING", location)
    return value


def _bounded_string(value: object, location: str) -> str:
    text = _string(value, location)
    if not text or len(text) > MAX_TEXT_LENGTH or "\x00" in text:
        _fail("INVALID_STRING", location)
    return text


def _identifier(value: object, location: str) -> str:
    text = _string(value, location)
    if IDENTIFIER_PATTERN.fullmatch(text) is None:
        _fail("INVALID_IDENTIFIER", location)
    return text


def _sha256(value: object, location: str) -> str:
    text = _string(value, location)
    if SHA256_PATTERN.fullmatch(text) is None:
        _fail("INVALID_SHA256", location)
    return text


def _exact_string(value: object, expected: str, location: str) -> None:
    if value != expected:
        _fail("INVALID_VALUE", location, repr(value))


def _boolean(value: object, location: str) -> bool:
    if type(value) is not bool:
        _fail("EXPECTED_BOOLEAN", location)
    return value


def _require_true(value: object, location: str) -> None:
    if value is not True:
        _fail("REQUIRED_TRUE", location)


def _require_false(value: object, location: str) -> None:
    if value is not False:
        _fail("REQUIRED_FALSE", location)


def _bounded_integer(value: object, minimum: int, maximum: int, location: str) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        _fail("INVALID_INTEGER", location)
    return value


def _exact_integer(value: object, expected: int, location: str, code: str) -> None:
    if type(value) is not int or value != expected:
        _fail(code, location, repr(value))


def _timestamp(value: object, location: str) -> datetime:
    text = _string(value, location)
    if UTC_SECONDS_PATTERN.fullmatch(text) is None:
        _fail("INVALID_TIMESTAMP", location)
    try:
        parsed = datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
    except ValueError as exc:
        _fail("INVALID_TIMESTAMP", location, str(exc))
    return parsed


def _exact_string_list(value: object, expected: Sequence[str], location: str) -> None:
    items = _sequence(value, location)
    if list(items) != list(expected):
        _fail("INVALID_VALUE", location)


def _nonempty_unique_string_list(value: object, location: str) -> list[str]:
    items = _sequence(value, location)
    if not items:
        _fail("EMPTY_ARRAY", location)
    result: list[str] = []
    for index, item in enumerate(items):
        result.append(_bounded_string(item, f"{location}[{index}]"))
    if len(set(result)) != len(result):
        _fail("DUPLICATE_ARRAY_ITEM", location)
    return result


def _scalar(value: object, location: str) -> None:
    if value is None or type(value) in {bool, int}:
        return
    if isinstance(value, float):
        if math.isfinite(value):
            return
        _fail("NONFINITE_NUMBER", location)
    if isinstance(value, str) and len(value) <= MAX_TEXT_LENGTH and "\x00" not in value:
        return
    _fail("INVALID_ARGUMENT_VALUE", location)


def _bbox(value: object, location: str) -> None:
    if value is None:
        return
    items = _sequence(value, location)
    if len(items) != 4 or any(type(item) is not int or item < 0 for item in items):
        _fail("INVALID_BBOX", location)
    if items[2] <= items[0] or items[3] <= items[1]:
        _fail("INVALID_BBOX", location)


def _unsafe_relative_path(value: str) -> bool:
    return (
        value.startswith(("/", "\\"))
        or ":" in value
        or "\\" in value
        or any(part in {"", ".", ".."} for part in value.split("/"))
    )


def _fail(code: str, location: str, detail: str = "") -> NoReturn:
    raise LaneBValidationError(code, location, detail)


__all__ = [
    "LANE_B_BUNDLE_VERSION",
    "LANE_B_CONSENT_VERSION",
    "LANE_B_DELETION_RECEIPT_VERSION",
    "LANE_B_EPISODE_VERSION",
    "LaneBValidationError",
    "LaneBValidationSummary",
    "canonical_json_bytes",
    "sha256_json",
    "validate_bundle",
    "validate_bundle_file",
    "validate_consent",
    "validate_deletion_receipt",
    "validate_episode",
]
