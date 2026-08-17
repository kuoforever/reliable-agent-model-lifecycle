"""Strict multimodal trajectory contract for synthetic MM-001 fixtures.

The schema represents text-only and image-grounded trajectories with the same
topology. It validates content-addressed references and authority boundaries;
it does not capture real data, execute actions, or authorize training use.
"""

from __future__ import annotations

import json
import math
import os
import re
import stat
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, NoReturn, Sequence

MULTIMODAL_TRAJECTORY_SCHEMA_VERSION = 1
COMPATIBLE_LANE_B_BUNDLE_VERSION = 1
COMPATIBLE_LANE_B_EPISODE_VERSION = 1

MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_ARTIFACT_BYTES = 16 * 1024 * 1024
MAX_TOTAL_ARTIFACT_BYTES = 32 * 1024 * 1024
MAX_ARTIFACTS = 64
MAX_TOOLS = 32
MAX_HISTORY_STEPS = 32
MAX_ARGUMENT_FIELDS = 20
MAX_TEXT_LENGTH = 4096

SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
IDENTIFIER_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")

MODALITIES = frozenset({"text_only", "image_grounded"})
RISK_LEVELS = frozenset({"low", "medium", "high", "critical"})
OBSERVATION_ROLES = frozenset(
    {"uia_tree", "document_text", "ocr_text", "screenshot_or_crop"}
)
ARTIFACT_ROLES = frozenset(
    {
        "sanitized_instruction",
        "available_tool_schema",
        "policy_context",
        "uia_tree",
        "document_text",
        "ocr_text",
        "screenshot_or_crop",
        "model_candidate_action",
        "runtime_policy_decision",
        "tool_result",
        "state_verifier_evidence",
    }
)


class TrajectoryValidationError(ValueError):
    """Stable fail-closed error for MM-001 fixtures and offline CI."""

    def __init__(self, code: str, location: str, detail: str = "") -> None:
        self.code = code
        self.location = location
        self.detail = detail
        message = f"{code} at {location}"
        if detail:
            message += f": {detail}"
        super().__init__(message)


@dataclass(frozen=True)
class TrajectoryValidationSummary:
    schema_version: int
    trajectory_id: str
    modality: str
    artifact_count: int
    available_tool_count: int
    previous_step_count: int
    transition_sequence: int
    dispatched: bool
    verifier_label: str
    training_eligible: bool
    execution_eligible: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_trajectory_file(path: Path) -> TrajectoryValidationSummary:
    payload = _read_regular_file_once(path)
    return validate_trajectory(_parse_strict_json_bytes(payload))


def validate_trajectory(value: object) -> TrajectoryValidationSummary:
    root = _mapping(value, "$")
    _exact_fields(
        root,
        {
            "multimodal_trajectory_schema_version",
            "trajectory_id",
            "modality",
            "provenance",
            "versions",
            "artifacts",
            "inputs",
            "observations",
            "transition",
            "governance",
        },
        "$",
    )
    _exact_integer(
        root.get("multimodal_trajectory_schema_version"),
        MULTIMODAL_TRAJECTORY_SCHEMA_VERSION,
        "$.multimodal_trajectory_schema_version",
        "UNSUPPORTED_VERSION",
    )
    trajectory_id = _identifier(root.get("trajectory_id"), "$.trajectory_id")
    modality = root.get("modality")
    if modality not in MODALITIES:
        _fail("INVALID_ENUM", "$.modality")
    _validate_provenance(root.get("provenance"))
    _validate_versions(root.get("versions"))
    artifacts, roles = _validate_artifacts(root.get("artifacts"))
    referenced: set[str] = set()
    tools, history_count = _validate_inputs(
        root.get("inputs"), artifacts, roles, referenced
    )
    observations = _validate_observations(
        root.get("observations"), str(modality), artifacts, roles, referenced
    )
    transition = _validate_transition(
        root.get("transition"),
        history_count,
        tools,
        observations,
        artifacts,
        roles,
        referenced,
        root["inputs"]["policy_context_ref"],
        str(modality),
    )
    governance = _validate_governance(root.get("governance"))
    orphaned = sorted(set(artifacts) - referenced)
    if orphaned:
        _fail("ORPHAN_ARTIFACT", "$.artifacts", ",".join(orphaned))
    return TrajectoryValidationSummary(
        schema_version=MULTIMODAL_TRAJECTORY_SCHEMA_VERSION,
        trajectory_id=trajectory_id,
        modality=str(modality),
        artifact_count=len(artifacts),
        available_tool_count=len(tools),
        previous_step_count=history_count,
        transition_sequence=transition["sequence"],
        dispatched=transition["runtime_decision"]["dispatched"],
        verifier_label=transition["verifier"]["label"],
        training_eligible=governance["training_eligible"],
        execution_eligible=governance["execution_eligible"],
    )


def _validate_provenance(value: object) -> None:
    location = "$.provenance"
    provenance = _mapping(value, location)
    _exact_fields(
        provenance,
        {
            "source",
            "real_capture",
            "lane_b_bundle_ref",
            "lane_b_episode_ref",
            "automatic_lane_a_export_used",
        },
        location,
    )
    _exact_string(provenance.get("source"), "synthetic_fixture", f"{location}.source")
    _require_false(provenance.get("real_capture"), f"{location}.real_capture")
    _require_none(provenance.get("lane_b_bundle_ref"), f"{location}.lane_b_bundle_ref")
    _require_none(
        provenance.get("lane_b_episode_ref"), f"{location}.lane_b_episode_ref"
    )
    _require_false(
        provenance.get("automatic_lane_a_export_used"),
        f"{location}.automatic_lane_a_export_used",
    )


def _validate_versions(value: object) -> None:
    location = "$.versions"
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
            "multimodal_trajectory_schema_version",
            "compatible_lane_b_bundle_version",
            "compatible_lane_b_episode_version",
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
        versions.get("multimodal_trajectory_schema_version"),
        MULTIMODAL_TRAJECTORY_SCHEMA_VERSION,
        f"{location}.multimodal_trajectory_schema_version",
        "UNSUPPORTED_VERSION",
    )
    _exact_integer(
        versions.get("compatible_lane_b_bundle_version"),
        COMPATIBLE_LANE_B_BUNDLE_VERSION,
        f"{location}.compatible_lane_b_bundle_version",
        "UNSUPPORTED_VERSION",
    )
    _exact_integer(
        versions.get("compatible_lane_b_episode_version"),
        COMPATIBLE_LANE_B_EPISODE_VERSION,
        f"{location}.compatible_lane_b_episode_version",
        "UNSUPPORTED_VERSION",
    )


def _validate_artifacts(
    value: object,
) -> tuple[dict[str, Mapping[str, Any]], dict[str, str]]:
    location = "$.artifacts"
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
            artifact.get("bytes"),
            1,
            MAX_ARTIFACT_BYTES,
            f"{item_location}.bytes",
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
    return artifacts, roles


def _validate_inputs(
    value: object,
    artifacts: Mapping[str, Mapping[str, Any]],
    roles: Mapping[str, str],
    referenced: set[str],
) -> tuple[dict[str, Mapping[str, Any]], int]:
    location = "$.inputs"
    inputs = _mapping(value, location)
    _exact_fields(
        inputs,
        {
            "instruction_ref",
            "available_tools",
            "policy_context_ref",
            "previous_steps",
        },
        location,
    )
    referenced.add(
        _artifact_ref(
            inputs.get("instruction_ref"),
            {"sanitized_instruction"},
            artifacts,
            roles,
            f"{location}.instruction_ref",
        )
    )
    referenced.add(
        _artifact_ref(
            inputs.get("policy_context_ref"),
            {"policy_context"},
            artifacts,
            roles,
            f"{location}.policy_context_ref",
        )
    )
    tool_items = _sequence(inputs.get("available_tools"), f"{location}.available_tools")
    if not 1 <= len(tool_items) <= MAX_TOOLS:
        _fail("INVALID_TOOL_COUNT", f"{location}.available_tools")
    tools: dict[str, Mapping[str, Any]] = {}
    for index, item in enumerate(tool_items):
        item_location = f"{location}.available_tools[{index}]"
        tool = _mapping(item, item_location)
        _exact_fields(
            tool,
            {
                "name",
                "argument_schema_ref",
                "supports_bbox",
                "supports_ref",
                "risk_levels",
            },
            item_location,
        )
        name = _identifier(tool.get("name"), f"{item_location}.name")
        if name in tools:
            _fail("DUPLICATE_TOOL", f"{item_location}.name")
        referenced.add(
            _artifact_ref(
                tool.get("argument_schema_ref"),
                {"available_tool_schema"},
                artifacts,
                roles,
                f"{item_location}.argument_schema_ref",
            )
        )
        _boolean(tool.get("supports_bbox"), f"{item_location}.supports_bbox")
        _boolean(tool.get("supports_ref"), f"{item_location}.supports_ref")
        risk_levels = _nonempty_unique_string_list(
            tool.get("risk_levels"), f"{item_location}.risk_levels"
        )
        if any(level not in RISK_LEVELS for level in risk_levels):
            _fail("INVALID_ENUM", f"{item_location}.risk_levels")
        tools[name] = tool

    history = _sequence(inputs.get("previous_steps"), f"{location}.previous_steps")
    if len(history) > MAX_HISTORY_STEPS:
        _fail("INVALID_HISTORY_COUNT", f"{location}.previous_steps")
    for index, item in enumerate(history):
        item_location = f"{location}.previous_steps[{index}]"
        step = _mapping(item, item_location)
        _exact_fields(
            step,
            {
                "sequence",
                "candidate_action_ref",
                "runtime_decision_ref",
                "dispatched",
                "tool_result_ref",
                "post_observation_refs",
                "verifier_evidence_refs",
                "outcome",
            },
            item_location,
        )
        _exact_integer(
            step.get("sequence"),
            index + 1,
            f"{item_location}.sequence",
            "NONCONTIGUOUS_HISTORY",
        )
        for key, role in {
            "candidate_action_ref": "model_candidate_action",
            "runtime_decision_ref": "runtime_policy_decision",
        }.items():
            referenced.add(
                _artifact_ref(
                    step.get(key),
                    {role},
                    artifacts,
                    roles,
                    f"{item_location}.{key}",
                )
            )
        dispatched = _boolean(step.get("dispatched"), f"{item_location}.dispatched")
        result_ref = step.get("tool_result_ref")
        if dispatched:
            referenced.add(
                _artifact_ref(
                    result_ref,
                    {"tool_result"},
                    artifacts,
                    roles,
                    f"{item_location}.tool_result_ref",
                )
            )
        elif result_ref is not None:
            _fail("UNDISPATCHED_TOOL_RESULT", f"{item_location}.tool_result_ref")
        post_refs = _artifact_ref_list(
            step.get("post_observation_refs"),
            OBSERVATION_ROLES,
            artifacts,
            roles,
            f"{item_location}.post_observation_refs",
        )
        verifier_refs = _artifact_ref_list(
            step.get("verifier_evidence_refs"),
            OBSERVATION_ROLES | {"state_verifier_evidence"},
            artifacts,
            roles,
            f"{item_location}.verifier_evidence_refs",
        )
        if not post_refs.issubset(verifier_refs) or not any(
            roles[artifact_id] == "state_verifier_evidence"
            for artifact_id in verifier_refs
        ):
            _fail("VERIFIER_EVIDENCE_INCOMPLETE", item_location)
        referenced.update(post_refs)
        referenced.update(verifier_refs)
        outcome = step.get("outcome")
        if outcome not in {"success", "failure", "unknown", "denied", "deferred"}:
            _fail("INVALID_ENUM", f"{item_location}.outcome")
        if outcome == "success" and not dispatched:
            _fail("INVALID_HISTORY_OUTCOME", f"{item_location}.outcome")
    return tools, len(history)


def _validate_observations(
    value: object,
    modality: str,
    artifacts: Mapping[str, Mapping[str, Any]],
    roles: Mapping[str, str],
    referenced: set[str],
) -> dict[str, Any]:
    location = "$.observations"
    items = _sequence(value, location)
    if len(items) != 2:
        _fail("INVALID_OBSERVATION_COUNT", location)
    expected_stages = ("pre_action", "post_action")
    observations: dict[str, Any] = {}
    source_sets: list[set[str]] = []
    for index, item in enumerate(items):
        item_location = f"{location}[{index}]"
        observation = _mapping(item, item_location)
        _exact_fields(
            observation,
            {
                "observation_id",
                "stage",
                "uia_refs",
                "document_text_refs",
                "ocr_refs",
                "image_refs",
            },
            item_location,
        )
        observation_id = _identifier(
            observation.get("observation_id"), f"{item_location}.observation_id"
        )
        if observation_id in observations:
            _fail("DUPLICATE_OBSERVATION", f"{item_location}.observation_id")
        _exact_string(
            observation.get("stage"), expected_stages[index], f"{item_location}.stage"
        )
        sources: set[str] = set()
        for key, role in {
            "uia_refs": "uia_tree",
            "document_text_refs": "document_text",
            "ocr_refs": "ocr_text",
            "image_refs": "screenshot_or_crop",
        }.items():
            refs = _artifact_ref_list(
                observation.get(key),
                {role},
                artifacts,
                roles,
                f"{item_location}.{key}",
                allow_empty=True,
            )
            if sources.intersection(refs):
                _fail("DUPLICATE_OBSERVATION_REF", item_location)
            sources.update(refs)
        if not sources:
            _fail("EMPTY_OBSERVATION", item_location)
        if modality == "text_only" and observation.get("image_refs"):
            _fail("TEXT_ONLY_IMAGE_FORBIDDEN", f"{item_location}.image_refs")
        if (
            modality == "image_grounded"
            and index == 0
            and not observation.get("image_refs")
        ):
            _fail("IMAGE_GROUNDING_REQUIRED", f"{item_location}.image_refs")
        observations[observation_id] = {
            "value": observation,
            "sources": sources,
        }
        source_sets.append(sources)
        referenced.update(sources)
    if source_sets[0].intersection(source_sets[1]):
        _fail("PRE_POST_OBSERVATION_ALIAS", location)
    if modality == "text_only" and any(
        role == "screenshot_or_crop" for role in roles.values()
    ):
        _fail("TEXT_ONLY_IMAGE_ARTIFACT_FORBIDDEN", "$.artifacts")
    return observations


def _validate_transition(
    value: object,
    history_count: int,
    tools: Mapping[str, Mapping[str, Any]],
    observations: Mapping[str, Any],
    artifacts: Mapping[str, Mapping[str, Any]],
    roles: Mapping[str, str],
    referenced: set[str],
    policy_context_ref: object,
    modality: str,
) -> dict[str, Any]:
    location = "$.transition"
    transition = _mapping(value, location)
    _exact_fields(
        transition,
        {
            "sequence",
            "pre_observation_id",
            "candidate_action",
            "runtime_decision",
            "tool_result_ref",
            "post_observation_id",
            "verifier",
        },
        location,
    )
    _exact_integer(
        transition.get("sequence"),
        history_count + 1,
        f"{location}.sequence",
        "NONCONTIGUOUS_TRANSITION",
    )
    pre_id = _string(
        transition.get("pre_observation_id"), f"{location}.pre_observation_id"
    )
    post_id = _string(
        transition.get("post_observation_id"), f"{location}.post_observation_id"
    )
    if (
        pre_id not in observations
        or observations[pre_id]["value"]["stage"] != "pre_action"
    ):
        _fail("PRE_OBSERVATION_LINK_MISMATCH", f"{location}.pre_observation_id")
    if (
        post_id not in observations
        or observations[post_id]["value"]["stage"] != "post_action"
    ):
        _fail("POST_OBSERVATION_LINK_MISMATCH", f"{location}.post_observation_id")
    candidate = _validate_candidate_action(
        transition.get("candidate_action"),
        tools,
        observations[pre_id]["sources"],
        artifacts,
        roles,
        referenced,
        modality,
        location,
    )
    runtime_decision = _validate_runtime_decision(
        transition.get("runtime_decision"),
        policy_context_ref,
        artifacts,
        roles,
        referenced,
        location,
    )
    tool_result_ref = transition.get("tool_result_ref")
    if runtime_decision["dispatched"]:
        referenced.add(
            _artifact_ref(
                tool_result_ref,
                {"tool_result"},
                artifacts,
                roles,
                f"{location}.tool_result_ref",
            )
        )
    elif tool_result_ref is not None:
        _fail("UNDISPATCHED_TOOL_RESULT", f"{location}.tool_result_ref")
    verifier = _validate_verifier(
        transition.get("verifier"),
        observations[post_id]["sources"],
        artifacts,
        roles,
        referenced,
        location,
    )
    return {
        "sequence": transition["sequence"],
        "candidate_action": candidate,
        "runtime_decision": runtime_decision,
        "verifier": verifier,
    }


def _validate_candidate_action(
    value: object,
    tools: Mapping[str, Mapping[str, Any]],
    pre_sources: set[str],
    artifacts: Mapping[str, Mapping[str, Any]],
    roles: Mapping[str, str],
    referenced: set[str],
    modality: str,
    parent: str,
) -> Mapping[str, Any]:
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
    referenced.add(
        _artifact_ref(
            action.get("record_ref"),
            {"model_candidate_action"},
            artifacts,
            roles,
            f"{location}.record_ref",
        )
    )
    next_tool = action.get("next_tool")
    selected_tool: Mapping[str, Any] | None = None
    if next_tool is not None:
        tool_name = _identifier(next_tool, f"{location}.next_tool")
        selected_tool = tools.get(tool_name)
        if selected_tool is None:
            _fail("UNAVAILABLE_TOOL", f"{location}.next_tool")
    arguments = _mapping(action.get("arguments"), f"{location}.arguments")
    if len(arguments) > MAX_ARGUMENT_FIELDS:
        _fail("TOO_MANY_ARGUMENTS", f"{location}.arguments")
    for key, item in arguments.items():
        _bounded_string(key, f"{location}.arguments.key")
        _scalar(item, f"{location}.arguments.{key}")
    _bbox(action.get("bbox"), f"{location}.bbox")
    if action.get("ref") is not None:
        _bounded_string(action.get("ref"), f"{location}.ref")
    if action.get("risk_level") not in RISK_LEVELS:
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
    evidence_refs = _artifact_ref_list(
        action.get("evidence_refs"),
        OBSERVATION_ROLES,
        artifacts,
        roles,
        f"{location}.evidence_refs",
    )
    if not evidence_refs.issubset(pre_sources):
        _fail("CANDIDATE_EVIDENCE_NOT_PRE_OBSERVATION", f"{location}.evidence_refs")
    referenced.update(evidence_refs)
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
    if not terminal and selected_tool is None:
        _fail("ACTION_TOOL_REQUIRED", f"{location}.next_tool")
    if action.get("bbox") is not None:
        if (
            modality != "image_grounded"
            or selected_tool is None
            or not selected_tool["supports_bbox"]
        ):
            _fail("BBOX_NOT_SUPPORTED", f"{location}.bbox")
        if not any(
            roles[artifact_id] == "screenshot_or_crop" for artifact_id in evidence_refs
        ):
            _fail("BBOX_IMAGE_EVIDENCE_REQUIRED", f"{location}.evidence_refs")
    if action.get("ref") is not None:
        if selected_tool is None or not selected_tool["supports_ref"]:
            _fail("REF_NOT_SUPPORTED", f"{location}.ref")
        if not any(
            roles[artifact_id] in {"uia_tree", "document_text", "ocr_text"}
            for artifact_id in evidence_refs
        ):
            _fail("REF_TEXT_EVIDENCE_REQUIRED", f"{location}.evidence_refs")
    return action


def _validate_runtime_decision(
    value: object,
    policy_context_ref: object,
    artifacts: Mapping[str, Mapping[str, Any]],
    roles: Mapping[str, str],
    referenced: set[str],
    parent: str,
) -> Mapping[str, Any]:
    location = f"{parent}.runtime_decision"
    decision = _mapping(value, location)
    _exact_fields(
        decision,
        {
            "record_ref",
            "policy_context_ref",
            "policy_decision",
            "approval_state",
            "dispatched",
            "runtime_is_authority",
        },
        location,
    )
    referenced.add(
        _artifact_ref(
            decision.get("record_ref"),
            {"runtime_policy_decision"},
            artifacts,
            roles,
            f"{location}.record_ref",
        )
    )
    if decision.get("policy_context_ref") != policy_context_ref:
        _fail("POLICY_CONTEXT_BINDING_MISMATCH", f"{location}.policy_context_ref")
    _artifact_ref(
        decision.get("policy_context_ref"),
        {"policy_context"},
        artifacts,
        roles,
        f"{location}.policy_context_ref",
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
    post_sources: set[str],
    artifacts: Mapping[str, Mapping[str, Any]],
    roles: Mapping[str, str],
    referenced: set[str],
    parent: str,
) -> Mapping[str, Any]:
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
    refs = _artifact_ref_list(
        verifier.get("evidence_refs"),
        OBSERVATION_ROLES | {"state_verifier_evidence"},
        artifacts,
        roles,
        f"{location}.evidence_refs",
    )
    if not post_sources.issubset(refs) or not any(
        roles[artifact_id] == "state_verifier_evidence" for artifact_id in refs
    ):
        _fail("VERIFIER_EVIDENCE_INCOMPLETE", f"{location}.evidence_refs")
    referenced.update(refs)
    _require_false(
        verifier.get("model_self_report_used"),
        f"{location}.model_self_report_used",
    )
    return verifier


def _validate_governance(value: object) -> Mapping[str, Any]:
    location = "$.governance"
    governance = _mapping(value, location)
    _exact_fields(
        governance,
        {
            "synthetic_only",
            "lane_b_capture_required_for_real_data",
            "dataset_split",
            "license_status",
            "training_eligible",
            "execution_eligible",
            "human_review_required",
        },
        location,
    )
    _require_true(governance.get("synthetic_only"), f"{location}.synthetic_only")
    _require_true(
        governance.get("lane_b_capture_required_for_real_data"),
        f"{location}.lane_b_capture_required_for_real_data",
    )
    _exact_string(
        governance.get("dataset_split"), "unassigned", f"{location}.dataset_split"
    )
    _exact_string(
        governance.get("license_status"),
        "pending_review",
        f"{location}.license_status",
    )
    _require_false(governance.get("training_eligible"), f"{location}.training_eligible")
    _require_false(
        governance.get("execution_eligible"), f"{location}.execution_eligible"
    )
    _require_true(
        governance.get("human_review_required"),
        f"{location}.human_review_required",
    )
    return governance


def _artifact_ref(
    value: object,
    expected_roles: set[str] | frozenset[str],
    artifacts: Mapping[str, Mapping[str, Any]],
    roles: Mapping[str, str],
    location: str,
) -> str:
    artifact_id = _sha256(value, location)
    if artifact_id not in artifacts:
        _fail("UNKNOWN_ARTIFACT_REF", location)
    if roles[artifact_id] not in expected_roles:
        _fail("ARTIFACT_ROLE_MISMATCH", location)
    return artifact_id


def _artifact_ref_list(
    value: object,
    expected_roles: set[str] | frozenset[str],
    artifacts: Mapping[str, Mapping[str, Any]],
    roles: Mapping[str, str],
    location: str,
    *,
    allow_empty: bool = False,
) -> set[str]:
    items = _sequence(value, location)
    if not items and not allow_empty:
        _fail("EMPTY_ARRAY", location)
    result: set[str] = set()
    for index, item in enumerate(items):
        artifact_id = _artifact_ref(
            item,
            expected_roles,
            artifacts,
            roles,
            f"{location}[{index}]",
        )
        if artifact_id in result:
            _fail("DUPLICATE_ARRAY_ITEM", location)
        result.add(artifact_id)
    return result


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
    except TrajectoryValidationError:
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
        or before.st_size > MAX_FILE_BYTES
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
    value: Mapping[str, Any],
    expected: set[str] | frozenset[str],
    location: str,
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


def _require_none(value: object, location: str) -> None:
    if value is not None:
        _fail("REQUIRED_NULL", location)


def _bounded_integer(value: object, minimum: int, maximum: int, location: str) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        _fail("INVALID_INTEGER", location)
    return value


def _exact_integer(value: object, expected: int, location: str, code: str) -> None:
    if type(value) is not int or value != expected:
        _fail(code, location, repr(value))


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


def _fail(code: str, location: str, detail: str = "") -> NoReturn:
    raise TrajectoryValidationError(code, location, detail)


__all__ = [
    "COMPATIBLE_LANE_B_BUNDLE_VERSION",
    "COMPATIBLE_LANE_B_EPISODE_VERSION",
    "MULTIMODAL_TRAJECTORY_SCHEMA_VERSION",
    "TrajectoryValidationError",
    "TrajectoryValidationSummary",
    "validate_trajectory",
    "validate_trajectory_file",
]
