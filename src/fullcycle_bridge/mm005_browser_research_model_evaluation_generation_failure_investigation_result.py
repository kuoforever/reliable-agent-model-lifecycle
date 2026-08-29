"""Closed result contract for the MM-005 Browser static investigation."""

from __future__ import annotations

import copy
import re
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any, NoReturn

from . import (
    mm005_browser_research_model_evaluation_generation_failure_investigation as protocol,
)

RESULT_VERSION = 1
GATE_ID = protocol.INVESTIGATION_GATE_ID
INVESTIGATION_ID = protocol.INVESTIGATION_ID
RESULT_PATH = protocol.RESULT_PATH
PROTOCOL_MERGE_COMMIT = "fe430710924537a18e677b75202f0c19806d3f12"
PROTOCOL_BYTES = 33_476
PROTOCOL_SHA256 = (
    "sha256:be8ecd067e884a8d60c9664013943d6887c769ac35a389934509b73338247494"
)

DIAGNOSTIC_PROTOCOL_GATE_ID = (
    "MM-005-browser-research-model-evaluation-generation-failure-diagnostic-protocol-v1"
)
STATIC_REMEDIATION_PROTOCOL_GATE_ID = (
    "MM-005-browser-research-model-evaluation-generation-failure-"
    "static-remediation-protocol-v1"
)
STATIC_DIFFERENCE_PROTOCOL_GATE_ID = (
    "MM-005-browser-research-model-evaluation-generation-failure-"
    "static-difference-isolation-protocol-v1"
)

IMPLEMENTATION_SOURCE_PATHS = {
    "focused_tests": (
        "tests/test_mm005_browser_research_model_evaluation_generation_failure_"
        "investigation_result.py"
    ),
    "result_contract": (
        "src/fullcycle_bridge/"
        "mm005_browser_research_model_evaluation_generation_failure_"
        "investigation_result.py"
    ),
    "result_runner": (
        "scripts/run_mm005_browser_research_model_evaluation_generation_failure_"
        "investigation_v1.py"
    ),
}

OUTCOME_PRECEDENCE = (
    "protocol_or_lineage_invalid",
    "deterministic_static_input_or_message_failure_reproduced",
    "static_difference_observed_without_causal_failure",
    "static_pipeline_reconstructed_without_contract_violation",
    "static_investigation_inconclusive",
)

OBSERVATION_KEYS = (
    "protocol_and_lineage_valid",
    "authority_boundary_preserved",
    "static_plan_complete",
    "deterministic_static_input_or_message_failure_reproduced",
    "closed_structural_difference_observed",
    "static_pipeline_reconstructed_without_contract_violation",
)

STRUCTURAL_COMPARISON_FIELDS = (
    "task_family_id",
    "source_kind",
    "source_count",
    "model_payload_bytes",
    "prompt_projection_bytes",
    "message_count",
    "system_messages",
    "user_messages",
    "image_channels",
    "text_parts",
    "opaque_sentinels_only",
)

EXCLUDED_CONTENT_IDENTITY_FIELDS = (
    "record.sha256",
    "adapter_audit_projection.sha256",
    "model_payload.sha256",
    "prompt_projection.sha256",
    "runtime_message_transport_projection.sha256",
    "screenshot_payloads[*].sha256",
    "source_snapshot_payloads[*].sha256",
)

DETERMINISTIC_FAILURE_DOMAIN_STEP_BY_CODE = {
    "CASE_ORDER_MISMATCH": protocol.STATIC_DIAGNOSTIC_STEPS[1],
    "TARGET_CASE_ORDER_MISMATCH": protocol.STATIC_DIAGNOSTIC_STEPS[1],
    "PROMPT_REGISTRY_CLOSURE_MISMATCH": protocol.STATIC_DIAGNOSTIC_STEPS[1],
    "DIAGNOSTIC_RECORD_IDS_NOT_UNIQUE": protocol.STATIC_DIAGNOSTIC_STEPS[2],
    "DIAGNOSTIC_RECORD_MISSING": protocol.STATIC_DIAGNOSTIC_STEPS[2],
    "DATASET_RECORD_ID_NOT_UNIQUE": protocol.STATIC_DIAGNOSTIC_STEPS[2],
    "DATASET_RECORD_INDEX_MISSING": protocol.STATIC_DIAGNOSTIC_STEPS[2],
    "TARGET_RECORD_CONTRACT_MISMATCH": protocol.STATIC_DIAGNOSTIC_STEPS[2],
    "STATIC_ARTIFACT_RECEIPT_MISMATCH": protocol.STATIC_DIAGNOSTIC_STEPS[3],
    "REGISTERED_ARTIFACT_RECEIPT_MISMATCH": protocol.STATIC_DIAGNOSTIC_STEPS[3],
    "PNG_HEADER_INVALID": protocol.STATIC_DIAGNOSTIC_STEPS[3],
    "PNG_FORMAT_INVALID": protocol.STATIC_DIAGNOSTIC_STEPS[3],
    "ADAPTER_STATIC_RECONSTRUCTION_FAILED": protocol.STATIC_DIAGNOSTIC_STEPS[4],
    "REGISTERED_PROJECTION_MISMATCH": protocol.STATIC_DIAGNOSTIC_STEPS[4],
    "REGISTERED_PROJECTION_RECEIPT_MISMATCH": protocol.STATIC_DIAGNOSTIC_STEPS[5],
    "RUNTIME_MESSAGE_TRANSPORT_PROJECTION_MISMATCH": (
        protocol.STATIC_DIAGNOSTIC_STEPS[6]
    ),
    "RUNTIME_MESSAGE_COUNT": protocol.STATIC_DIAGNOSTIC_STEPS[6],
    "RUNTIME_IMAGE_SENTINEL_MISMATCH": protocol.STATIC_DIAGNOSTIC_STEPS[6],
    "RUNTIME_MESSAGE_CONTENT_INVALID": protocol.STATIC_DIAGNOSTIC_STEPS[6],
    "RUNTIME_IMAGE_SENTINEL_COUNT": protocol.STATIC_DIAGNOSTIC_STEPS[6],
}

RESULT_REQUIRED_TOP_LEVEL_KEYS = (
    "claims",
    "decision",
    "evidence_layers",
    "executed_at_utc",
    "execution",
    "formal_gate",
    "gate_id",
    "implementation_lineage",
    "investigation_id",
    "locked_next_action",
    "mm005_browser_research_generation_failure_investigation_result_version",
    "protocol_lineage",
    "record_registry",
    "report_digest",
    "runtime_eligible",
    "static_plan_observation",
    "structural_comparison",
)

FORMAL_RESULT_GATES = (
    "published_protocol_lineage_integrity",
    "implementation_source_lineage_integrity",
    "v2_raw_terminal_artifact_integrity",
    "exact_target_and_control_registry_observation_integrity",
    "record_and_artifact_receipt_observation_integrity",
    "adapter_projection_and_gold_path_observation_integrity",
    "model_payload_and_prompt_projection_observation_integrity",
    "opaque_runtime_message_transport_observation_integrity",
    "frozen_control_flow_boundary_observation_integrity",
    "closed_structural_comparison_observation_integrity",
    "mutually_exclusive_outcome_selection",
    "model_free_capability_boundary",
    "v2_immutable_and_zero_retry",
    "runtime_authority_preserved",
    "fail_closed_claims",
)

_UTC_TIMESTAMP_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")


class MM005GenerationFailureInvestigationResultError(ValueError):
    """Stable fail-closed result-contract error."""

    def __init__(self, code: str, location: str = "$") -> None:
        self.code = code
        self.location = location
        super().__init__(f"{code} at {location}")


class _StaticPlanInconclusive(MM005GenerationFailureInvestigationResultError):
    """A closed observer result, never a catch-all for unexpected failures."""


def result_contract() -> dict[str, Any]:
    """Return the closed schema, decision table, and outcome routing."""

    return {
        "result_version": RESULT_VERSION,
        "gate_id": GATE_ID,
        "investigation_id": INVESTIGATION_ID,
        "fixed_result_path": RESULT_PATH,
        "required_top_level_keys": list(RESULT_REQUIRED_TOP_LEVEL_KEYS),
        "formal_result_gates": list(FORMAL_RESULT_GATES),
        "observation_contract": {
            "required_boolean_keys": list(OBSERVATION_KEYS),
            "python_bool_required_not_integer_alias": True,
            "contradictory_states_rejected": True,
            "protocol_or_implementation_trust_failure_publishes_result": False,
        },
        "structural_comparison_contract": {
            "target_record_id": protocol.TARGET_RECORD_ID,
            "same_shape_control_ids": list(protocol.SAME_SHAPE_CONTROL_IDS),
            "closed_fields": list(STRUCTURAL_COMPARISON_FIELDS),
            "excluded_content_identity_fields": list(EXCLUDED_CONTENT_IDENTITY_FIELDS),
            "content_identity_differences_expected": True,
            "content_identity_difference_is_causal": False,
            "difference_outcome_requires_closed_field_difference": True,
        },
        "static_plan_observation_contract": {
            "steps": list(protocol.STATIC_DIAGNOSTIC_STEPS),
            "allowed_step_statuses": [
                "passed",
                "deterministic_failure",
                "inconclusive",
                "not_reached",
            ],
            "deterministic_failure_domain_step_by_error_code": dict(
                DETERMINISTIC_FAILURE_DOMAIN_STEP_BY_CODE
            ),
            "monolithic_registry_failure_terminal_step": (
                protocol.STATIC_DIAGNOSTIC_STEPS[1]
            ),
            "failure_domain_step_does_not_prove_prior_steps_completed": True,
            "unknown_or_unexpected_failure_publishes_result": False,
            "inconclusive_requires_explicit_closed_observer_reason": True,
            "caller_supplied_outcome_or_observations_allowed": False,
        },
        "outcome_selection": {
            "allowed_outcomes": list(protocol.DECISION_OUTCOMES),
            "precedence": list(OUTCOME_PRECEDENCE),
            "exactly_one_selected": True,
            "runtime_root_cause_unresolved_for_every_publishable_outcome": True,
            "static_pass_does_not_establish_historical_runtime_health": True,
        },
        "outcome_routes": copy.deepcopy(_outcome_routes()),
        "claims_contract": {
            "static_investigation_formal_gate_is_not_model_measurement_gate": True,
            "investigation_executed_may_be_true_after_exclusive_publication": True,
            "static_investigation_complete_may_be_true_after_valid_result": True,
            "formal_measurement_complete": False,
            "model_evaluated": False,
            "historical_runtime_health_established": False,
            "static_root_cause_reproduced": False,
            "failed_runtime_substage_isolated": False,
            "remediation_delta_established": False,
            "recovery_v3_justified": False,
            "diagnostic_model_or_cuda_execution_authorized": False,
            "runtime_eligible": False,
        },
        "publication_contract": {
            "implementation_must_be_clean_merged_before_formal_execution": True,
            "implementation_freeze_commit_recorded_in_result": True,
            "exclusive_create": True,
            "zero_internal_retry": True,
            "check_mode_may_recompute_without_republishing": True,
            "no_mutable_output_override": True,
        },
    }


def outcome_predicates(observations: Mapping[str, object]) -> dict[str, bool]:
    """Evaluate mutually exclusive predicates over a closed Boolean input set."""

    checked = _validated_observations(observations)
    trusted = (
        checked["protocol_and_lineage_valid"]
        and checked["authority_boundary_preserved"]
    )
    plan_complete = checked["static_plan_complete"]
    deterministic_failure = checked[
        "deterministic_static_input_or_message_failure_reproduced"
    ]
    structural_difference = checked["closed_structural_difference_observed"]
    pipeline_reconstructed = checked[
        "static_pipeline_reconstructed_without_contract_violation"
    ]
    predicates = {
        "protocol_or_lineage_invalid": not trusted,
        "deterministic_static_input_or_message_failure_reproduced": (
            trusted and plan_complete and deterministic_failure
        ),
        "static_difference_observed_without_causal_failure": (
            trusted
            and plan_complete
            and not deterministic_failure
            and structural_difference
        ),
        "static_pipeline_reconstructed_without_contract_violation": (
            trusted
            and plan_complete
            and not deterministic_failure
            and not structural_difference
            and pipeline_reconstructed
        ),
        "static_investigation_inconclusive": (
            trusted
            and not deterministic_failure
            and not structural_difference
            and not (plan_complete and pipeline_reconstructed)
        ),
    }
    if set(predicates) != set(protocol.DECISION_OUTCOMES):
        _fail("OUTCOME_SET_MISMATCH", "$.outcome_predicates")
    if sum(value is True for value in predicates.values()) != 1:
        _fail("OUTCOME_NOT_MUTUALLY_EXCLUSIVE", "$.outcome_predicates")
    return predicates


def select_outcome(observations: Mapping[str, object]) -> str:
    predicates = outcome_predicates(observations)
    selected = [name for name in OUTCOME_PRECEDENCE if predicates[name]]
    if len(selected) != 1:
        _fail("OUTCOME_SELECTION_INVALID", "$.outcome")
    return selected[0]


def build_structural_comparison(
    record_registry: Mapping[str, object],
) -> dict[str, Any]:
    """Compare only preregistered same-shape dimensions, never content identity."""

    records = _object_sequence(record_registry.get("records"), "$.record_registry")
    by_id = {str(item.get("record_id")): item for item in records}
    if len(by_id) != len(records):
        _fail("RECORD_ID_NOT_UNIQUE", "$.record_registry")
    target = by_id.get(protocol.TARGET_RECORD_ID)
    if target is None:
        _fail("TARGET_RECORD_MISSING", "$.record_registry")
    target_projection = _structural_projection(target)
    controls: list[dict[str, Any]] = []
    for record_id in protocol.SAME_SHAPE_CONTROL_IDS:
        control = by_id.get(record_id)
        if control is None:
            _fail("SAME_SHAPE_CONTROL_MISSING", f"$.record_registry.{record_id}")
        projection = _structural_projection(control)
        controls.append(
            {
                "record_id": record_id,
                "projection": projection,
                "matches_target_closed_dimensions": projection == target_projection,
                "content_identity_differs_from_target": _content_identity_differs(
                    target, control
                ),
            }
        )
    closed_difference = any(
        not item["matches_target_closed_dimensions"] for item in controls
    )
    content_differences = all(
        item["content_identity_differs_from_target"] for item in controls
    )
    return {
        "status": "observed",
        "target_record_id": protocol.TARGET_RECORD_ID,
        "same_shape_control_ids": list(protocol.SAME_SHAPE_CONTROL_IDS),
        "closed_fields": list(STRUCTURAL_COMPARISON_FIELDS),
        "target_projection": target_projection,
        "controls": controls,
        "closed_structural_difference_observed": closed_difference,
        "excluded_content_identity_fields": list(EXCLUDED_CONTENT_IDENTITY_FIELDS),
        "content_identity_differences_observed": content_differences,
        "content_identity_difference_is_causal": False,
    }


def build_control_flow_observation(
    source_payloads: Mapping[str, bytes],
) -> dict[str, Any]:
    """Verify frozen source order without importing the runtime runner."""

    if set(source_payloads) != {"v2_runner", "shared_generation_helper"}:
        _fail("CONTROL_FLOW_SOURCE_SET_MISMATCH", "$.control_flow")
    try:
        runner = source_payloads["v2_runner"].decode("utf-8")
        helper = source_payloads["shared_generation_helper"].decode("utf-8")
    except (KeyError, UnicodeDecodeError) as exc:
        raise MM005GenerationFailureInvestigationResultError(
            "CONTROL_FLOW_SOURCE_INVALID", "$.control_flow"
        ) from exc
    loop_start = _marker_position_after(runner, "for record in ordered:", 0)
    loop_end = _marker_position_after(
        runner, "    if counters != contract.expected_execution_counters():", loop_start
    )
    loop_body = runner[loop_start:loop_end]
    outer_markers = (
        "adapted = adapter_verifier.adapt_record(",
        "images = [",
        '"generation_started", counters, completed_record_ids, record_id',
        "messages = v1_contract.build_runtime_messages(",
        "torch.cuda.synchronize()",
        "raw_output, generated_tokens = base_runner._generate_one(",
        "torch.cuda.synchronize()",
        "case = v1_contract.build_case_result(",
        '"generation_completed", counters, completed_record_ids, record_id',
    )
    for marker in set(outer_markers):
        expected_count = 2 if marker == "torch.cuda.synchronize()" else 1
        if loop_body.count(marker) != expected_count:
            _inconclusive("V2_RUNNER_MARKER_COUNT_MISMATCH", "$.control_flow.v2_runner")
    outer_positions: list[int] = []
    cursor = 0
    for marker in outer_markers:
        position = _marker_position_after(loop_body, marker, cursor)
        outer_positions.append(position)
        cursor = position + len(marker)
    if outer_positions != sorted(outer_positions):
        _inconclusive("V2_RUNNER_MARKER_ORDER_MISMATCH", "$.control_flow.v2_runner")
    helper_start = _marker_position_after(helper, "def _generate_one(", 0)
    helper_end = _marker_position_after(
        helper, "\ndef _load_ml_dependencies", helper_start
    )
    helper_body = helper[helper_start:helper_end]
    inner_markers = (
        "processor.apply_chat_template(",
        'processor(**kwargs).to("cuda")',
        "model.generate(",
        "processor.batch_decode(",
    )
    if any(helper_body.count(marker) != 1 for marker in inner_markers):
        _inconclusive(
            "GENERATION_HELPER_MARKER_COUNT_MISMATCH", "$.control_flow.helper"
        )
    inner_positions = [
        _marker_position_after(helper_body, marker, 0) for marker in inner_markers
    ]
    if inner_positions != sorted(inner_positions):
        _inconclusive(
            "GENERATION_HELPER_MARKER_ORDER_MISMATCH", "$.control_flow.helper"
        )
    return {
        "frozen_historical_stage_order": list(
            protocol.HISTORICAL_GENERATION_STAGE_ORDER
        ),
        "outer_markers_unique_and_ordered": True,
        "inner_markers_unique_and_ordered": True,
        "durably_authenticated_through": (
            "generation_started_checkpoint_durably_persisted"
        ),
        "checkpoint_proves_model_generate_entered": False,
        "source_order_proves_async_error_origin": False,
    }


def _execute_static_plan(
    *,
    registered_registry: Mapping[str, Any],
    records: Sequence[Mapping[str, Any]],
    artifact_payloads: Mapping[str, bytes],
    v2_preregistration: Mapping[str, Any],
    control_flow_source_payloads: Mapping[str, bytes],
) -> dict[str, Any]:
    """Derive a closed observation bundle only from the frozen inputs."""

    try:
        observed_registry = protocol.build_static_record_registry(
            records, artifact_payloads, v2_preregistration
        )
    except protocol.MM005GenerationFailureInvestigationError as exc:
        failure_domain_step = DETERMINISTIC_FAILURE_DOMAIN_STEP_BY_CODE.get(exc.code)
        if failure_domain_step is None:
            raise
        terminal_step = protocol.STATIC_DIAGNOSTIC_STEPS[1]
        return {
            "step_observations": _step_observations(
                terminal_step=terminal_step,
                terminal_status="deterministic_failure",
                reason_code=exc.code,
                location=exc.location,
            ),
            "static_plan_complete": True,
            "deterministic_static_input_or_message_failure_reproduced": True,
            "closed_structural_difference_observed": False,
            "static_pipeline_reconstructed_without_contract_violation": False,
            "deterministic_failure": {
                "step": terminal_step,
                "failure_domain_step": failure_domain_step,
                "error_code": exc.code,
                "location": exc.location,
            },
            "inconclusive_reason_codes": [],
            "observed_registry_status": (
                "deterministic_failure_before_registry_completed"
            ),
            "observed_registry": None,
            "observed_registry_matches_registered": None,
            "structural_comparison": _unobserved_structural_comparison(
                "not_reached_due_to_deterministic_failure"
            ),
            "control_flow_status": ("not_reached_due_to_deterministic_failure"),
            "control_flow_observation": None,
        }

    if protocol.artifact_json_bytes(observed_registry) != protocol.artifact_json_bytes(
        dict(registered_registry)
    ):
        _fail("STATIC_REGISTRY_RECOMPUTATION_MISMATCH", "$.record_registry")
    structural = build_structural_comparison(observed_registry)
    closed_difference = structural.get("closed_structural_difference_observed")
    if type(closed_difference) is not bool:
        _fail("STRUCTURAL_COMPARISON_BOOL_REQUIRED", "$.structural_comparison")
    try:
        control_flow = build_control_flow_observation(control_flow_source_payloads)
    except _StaticPlanInconclusive as exc:
        return {
            "step_observations": _step_observations(
                terminal_step=protocol.STATIC_DIAGNOSTIC_STEPS[7],
                terminal_status="inconclusive",
                reason_code=exc.code,
                location=exc.location,
            ),
            "static_plan_complete": True,
            "deterministic_static_input_or_message_failure_reproduced": False,
            "closed_structural_difference_observed": closed_difference,
            "static_pipeline_reconstructed_without_contract_violation": False,
            "deterministic_failure": None,
            "inconclusive_reason_codes": [exc.code],
            "observed_registry_status": "exactly_recomputed",
            "observed_registry": observed_registry,
            "observed_registry_matches_registered": True,
            "structural_comparison": structural,
            "control_flow_status": "inconclusive",
            "control_flow_observation": None,
        }

    return {
        "step_observations": _step_observations(),
        "static_plan_complete": True,
        "deterministic_static_input_or_message_failure_reproduced": False,
        "closed_structural_difference_observed": closed_difference,
        "static_pipeline_reconstructed_without_contract_violation": (
            not closed_difference
        ),
        "deterministic_failure": None,
        "inconclusive_reason_codes": [],
        "observed_registry_status": "exactly_recomputed",
        "observed_registry": observed_registry,
        "observed_registry_matches_registered": True,
        "structural_comparison": structural,
        "control_flow_status": "observed",
        "control_flow_observation": control_flow,
    }


def _step_observations(
    *,
    terminal_step: str | None = None,
    terminal_status: str | None = None,
    reason_code: str | None = None,
    location: str | None = None,
) -> list[dict[str, Any]]:
    allowed_statuses = {
        "passed",
        "deterministic_failure",
        "inconclusive",
        "not_reached",
    }
    if terminal_step is None:
        if any(value is not None for value in (terminal_status, reason_code, location)):
            _fail("STEP_OBSERVATION_INPUT_INVALID", "$.step_observations")
        return [
            {
                "step": step,
                "status": "passed",
                "reason_code": None,
                "location": None,
            }
            for step in protocol.STATIC_DIAGNOSTIC_STEPS
        ]
    if (
        terminal_step not in protocol.STATIC_DIAGNOSTIC_STEPS
        or terminal_status not in allowed_statuses - {"passed", "not_reached"}
        or not isinstance(reason_code, str)
        or not reason_code
        or not isinstance(location, str)
        or not location
    ):
        _fail("STEP_OBSERVATION_INPUT_INVALID", "$.step_observations")
    terminal_index = protocol.STATIC_DIAGNOSTIC_STEPS.index(terminal_step)
    rubric_index = len(protocol.STATIC_DIAGNOSTIC_STEPS) - 1
    result: list[dict[str, Any]] = []
    for index, step in enumerate(protocol.STATIC_DIAGNOSTIC_STEPS):
        if index < terminal_index or index == rubric_index:
            status = "passed"
            step_reason = None
            step_location = None
        elif index == terminal_index:
            status = terminal_status
            step_reason = reason_code
            step_location = location
        else:
            status = "not_reached"
            step_reason = "blocked_by_prior_closed_observation"
            step_location = None
        result.append(
            {
                "step": step,
                "status": status,
                "reason_code": step_reason,
                "location": step_location,
            }
        )
    return result


def _unobserved_structural_comparison(status: str) -> dict[str, Any]:
    if status != "not_reached_due_to_deterministic_failure":
        _fail("STRUCTURAL_OBSERVATION_STATUS_INVALID", "$.structural_comparison")
    return {
        "status": status,
        "target_record_id": protocol.TARGET_RECORD_ID,
        "same_shape_control_ids": list(protocol.SAME_SHAPE_CONTROL_IDS),
        "closed_fields": list(STRUCTURAL_COMPARISON_FIELDS),
        "target_projection": None,
        "controls": [],
        "closed_structural_difference_observed": False,
        "excluded_content_identity_fields": list(EXCLUDED_CONTENT_IDENTITY_FIELDS),
        "content_identity_differences_observed": False,
        "content_identity_difference_is_causal": False,
    }


def _published_static_plan_observation(
    observation: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "step_observations": copy.deepcopy(observation["step_observations"]),
        "static_plan_complete": observation["static_plan_complete"],
        "deterministic_static_input_or_message_failure_reproduced": observation[
            "deterministic_static_input_or_message_failure_reproduced"
        ],
        "closed_structural_difference_observed": observation[
            "closed_structural_difference_observed"
        ],
        "static_pipeline_reconstructed_without_contract_violation": observation[
            "static_pipeline_reconstructed_without_contract_violation"
        ],
        "deterministic_failure": copy.deepcopy(observation["deterministic_failure"]),
        "inconclusive_reason_codes": list(observation["inconclusive_reason_codes"]),
        "observed_registry_status": observation["observed_registry_status"],
        "control_flow_status": observation["control_flow_status"],
    }


def _formal_gate_observations(
    observation: Mapping[str, Any], predicates: Mapping[str, bool]
) -> dict[str, bool]:
    registry_closed = observation.get("observed_registry_status") in {
        "exactly_recomputed",
        "deterministic_failure_before_registry_completed",
    }
    structural_closed = _mapping(
        observation.get("structural_comparison"), "$.structural_comparison"
    ).get("status") in {"observed", "not_reached_due_to_deterministic_failure"}
    control_flow_closed = observation.get("control_flow_status") in {
        "observed",
        "inconclusive",
        "not_reached_due_to_deterministic_failure",
    }
    plan_complete = observation.get("static_plan_complete") is True
    outcome_closed = (
        set(predicates) == set(protocol.DECISION_OUTCOMES)
        and sum(value is True for value in predicates.values()) == 1
    )
    gates = {
        "published_protocol_lineage_integrity": True,
        "implementation_source_lineage_integrity": True,
        "v2_raw_terminal_artifact_integrity": True,
        "exact_target_and_control_registry_observation_integrity": registry_closed,
        "record_and_artifact_receipt_observation_integrity": registry_closed,
        "adapter_projection_and_gold_path_observation_integrity": registry_closed,
        "model_payload_and_prompt_projection_observation_integrity": registry_closed,
        "opaque_runtime_message_transport_observation_integrity": registry_closed,
        "frozen_control_flow_boundary_observation_integrity": control_flow_closed,
        "closed_structural_comparison_observation_integrity": structural_closed,
        "mutually_exclusive_outcome_selection": outcome_closed,
        "model_free_capability_boundary": plan_complete,
        "v2_immutable_and_zero_retry": plan_complete,
        "runtime_authority_preserved": plan_complete,
        "fail_closed_claims": plan_complete,
    }
    if tuple(gates) != FORMAL_RESULT_GATES:
        _fail("FORMAL_GATE_SET_MISMATCH", "$.formal_gate")
    return gates


def build_static_investigation_result(
    *,
    preregistration: Mapping[str, Any],
    preregistration_payload: bytes,
    implementation_freeze_commit: str,
    executed_at_utc: str,
    protocol_source_bindings: Mapping[str, Mapping[str, Any]],
    implementation_source_bindings: Mapping[str, Mapping[str, Any]],
    records: Sequence[Mapping[str, Any]],
    artifact_payloads: Mapping[str, bytes],
    v2_preregistration: Mapping[str, Any],
    control_flow_source_payloads: Mapping[str, bytes],
) -> dict[str, Any]:
    """Execute the frozen pure-static plan in memory and derive one result."""

    _validate_protocol_binding(preregistration, preregistration_payload)
    _validate_commit(implementation_freeze_commit, "$.implementation_freeze_commit")
    _validate_timestamp(executed_at_utc)
    protocol_bindings = _validated_source_bindings(
        protocol_source_bindings,
        expected_paths=protocol.PROTOCOL_SOURCE_PATHS,
        location="$.protocol_source_bindings",
        equality_key="tracked_bytes_equal_protocol_merge_commit_blob",
    )
    implementation_bindings = _validated_source_bindings(
        implementation_source_bindings,
        expected_paths=IMPLEMENTATION_SOURCE_PATHS,
        location="$.implementation_source_bindings",
        equality_key="tracked_bytes_equal_implementation_freeze_commit_blob",
    )

    registered_registry = _mapping(
        _mapping(
            preregistration.get("static_investigation_plan"),
            "$.preregistration.static_investigation_plan",
        ).get("record_registry"),
        "$.preregistration.static_investigation_plan.record_registry",
    )
    static_observation = _execute_static_plan(
        registered_registry=registered_registry,
        records=records,
        artifact_payloads=artifact_payloads,
        v2_preregistration=v2_preregistration,
        control_flow_source_payloads=control_flow_source_payloads,
    )
    structural = _mapping(
        static_observation.get("structural_comparison"),
        "$.static_plan_observation.structural_comparison",
    )
    observed_registry = static_observation.get("observed_registry")
    observations = {
        "protocol_and_lineage_valid": True,
        "authority_boundary_preserved": True,
        "static_plan_complete": static_observation["static_plan_complete"],
        "deterministic_static_input_or_message_failure_reproduced": (
            static_observation[
                "deterministic_static_input_or_message_failure_reproduced"
            ]
        ),
        "closed_structural_difference_observed": static_observation[
            "closed_structural_difference_observed"
        ],
        "static_pipeline_reconstructed_without_contract_violation": (
            static_observation[
                "static_pipeline_reconstructed_without_contract_violation"
            ]
        ),
    }
    predicates = outcome_predicates(observations)
    selected_outcome = select_outcome(observations)

    gates = _formal_gate_observations(static_observation, predicates)
    formal_gate_passed = all(gates.values())
    claims = _result_claims(selected_outcome, formal_gate_passed)
    route = copy.deepcopy(_outcome_routes()[selected_outcome])
    registered_registry_payload = protocol.artifact_json_bytes(
        dict(registered_registry)
    )
    observed_registry_mapping = (
        None
        if observed_registry is None
        else dict(_mapping(observed_registry, "$.static_plan_observation.registry"))
    )
    registry_recomputed = observed_registry_mapping is not None
    result: dict[str, Any] = {
        "mm005_browser_research_generation_failure_investigation_result_version": (
            RESULT_VERSION
        ),
        "gate_id": GATE_ID,
        "investigation_id": INVESTIGATION_ID,
        "executed_at_utc": executed_at_utc,
        "protocol_lineage": {
            "protocol_merge_commit": PROTOCOL_MERGE_COMMIT,
            "preregistration": {
                "path": protocol.PREREGISTRATION_PATH,
                "bytes": len(preregistration_payload),
                "sha256": protocol.sha256_bytes(preregistration_payload),
                "canonical_json": True,
                "tracked_bytes_equal_protocol_merge_commit_blob": True,
            },
            "protocol_sources": protocol_bindings,
        },
        "implementation_lineage": {
            "implementation_freeze_commit": implementation_freeze_commit,
            "implementation_sources": implementation_bindings,
            "formal_execution_started_from_aligned_merged_master": True,
        },
        "execution": {
            "formal_static_investigation_invocations": 1,
            "internal_retries": 0,
            "steps": copy.deepcopy(static_observation["step_observations"]),
            "fixed_result_path": RESULT_PATH,
            "exclusive_publication": True,
            "model_free": True,
            "pil_image_decode_used": False,
            "processor_loaded_or_called": False,
            "model_imported_or_called": False,
            "torch_imported": False,
            "cuda_used": False,
            "network_used": False,
            "live_browser_used": False,
            "training_used": False,
            "v1_or_v2_retried": False,
        },
        "evidence_layers": {
            "durable_authenticated_facts": copy.deepcopy(
                preregistration["authenticated_failure_boundary"]
            ),
            "frozen_control_flow_inference": {
                **copy.deepcopy(preregistration["historical_control_flow_boundary"]),
                "execution_observation": copy.deepcopy(
                    static_observation["control_flow_observation"]
                ),
            },
            "static_recomputation": {
                "record_count": (
                    len(observed_registry_mapping["records"])
                    if observed_registry_mapping is not None
                    else 0
                ),
                "target_and_controls_exactly_recomputed": registry_recomputed,
                "record_and_artifact_receipts_exactly_recomputed": (
                    registry_recomputed
                ),
                "adapter_projection_exactly_recomputed": registry_recomputed,
                "gold_real_paths_and_snapshots_excluded_from_transport": (
                    registry_recomputed
                ),
                "model_payload_exactly_recomputed": registry_recomputed,
                "prompt_projection_exactly_recomputed": registry_recomputed,
                "opaque_runtime_message_transport_exactly_recomputed": (
                    registry_recomputed
                ),
                "png_ihdr_checked_without_pixel_decode": registry_recomputed,
            },
            "unresolved_runtime_substages": copy.deepcopy(
                preregistration["historical_control_flow_boundary"][
                    "post_checkpoint_substages_not_individually_authenticated"
                ]
            ),
        },
        "record_registry": {
            "registered_reference": {
                "bytes": len(registered_registry_payload),
                "sha256": protocol.sha256_bytes(registered_registry_payload),
            },
            "observation_status": static_observation["observed_registry_status"],
            "observed": observed_registry_mapping,
            "exactly_matches_registered": static_observation[
                "observed_registry_matches_registered"
            ],
        },
        "static_plan_observation": _published_static_plan_observation(
            static_observation
        ),
        "structural_comparison": dict(structural),
        "decision": {
            "allowed_outcomes": list(protocol.DECISION_OUTCOMES),
            "precedence": list(OUTCOME_PRECEDENCE),
            "observations": observations,
            "outcome_predicates": predicates,
            "selected_outcome": selected_outcome,
            "exactly_one_outcome_selected": True,
            "runtime_root_cause_unresolved": True,
            "historical_runtime_health_established": False,
            "content_identity_difference_is_causal": False,
        },
        "formal_gate": {
            "gates": gates,
            "passed": formal_gate_passed,
            "is_static_investigation_gate_not_model_measurement_gate": True,
        },
        "claims": claims,
        "locked_next_action": {
            **route,
            "selected_outcome": selected_outcome,
            "eligible_to_start": formal_gate_passed
            and route["next_gate_id"] is not None,
            "diagnostic_execution_authorized": False,
            "recovery_v3_authorized": False,
            "v2_retry_authorized": False,
        },
        "runtime_eligible": False,
    }
    result["report_digest"] = protocol.sha256_bytes(
        protocol.artifact_json_bytes(result)
    )
    if tuple(sorted(result)) != tuple(sorted(RESULT_REQUIRED_TOP_LEVEL_KEYS)):
        _fail("RESULT_TOP_LEVEL_SCHEMA_MISMATCH", "$.result")
    return result


def validate_static_investigation_result(
    value: Mapping[str, Any],
    **inputs: Any,
) -> dict[str, Any]:
    """Recompute the result exactly, including its self-excluding report digest."""

    expected = build_static_investigation_result(**inputs)
    if protocol.artifact_json_bytes(dict(value)) != protocol.artifact_json_bytes(
        expected
    ):
        _fail("STATIC_INVESTIGATION_RESULT_MISMATCH", "$.result")
    return expected


def _validated_observations(
    observations: Mapping[str, object],
) -> dict[str, bool]:
    if set(observations) != set(OBSERVATION_KEYS):
        _fail("OBSERVATION_SET_MISMATCH", "$.observations")
    checked: dict[str, bool] = {}
    for name in OBSERVATION_KEYS:
        value = observations[name]
        if type(value) is not bool:
            _fail("OBSERVATION_BOOL_REQUIRED", f"$.observations.{name}")
        checked[name] = value
    if checked["deterministic_static_input_or_message_failure_reproduced"] and (
        checked["closed_structural_difference_observed"]
        or checked["static_pipeline_reconstructed_without_contract_violation"]
    ):
        _fail("CONTRADICTORY_STATIC_FAILURE_STATE", "$.observations")
    if (
        checked["closed_structural_difference_observed"]
        and checked["static_pipeline_reconstructed_without_contract_violation"]
    ):
        _fail("CONTRADICTORY_STRUCTURAL_DIFFERENCE_STATE", "$.observations")
    if (
        checked["deterministic_static_input_or_message_failure_reproduced"]
        or checked["closed_structural_difference_observed"]
        or checked["static_pipeline_reconstructed_without_contract_violation"]
    ) and not checked["static_plan_complete"]:
        _fail("INCOMPLETE_PLAN_WITH_FINAL_OBSERVATION", "$.observations")
    return checked


def _validate_protocol_binding(
    preregistration: Mapping[str, Any], preregistration_payload: bytes
) -> None:
    if (
        not isinstance(preregistration_payload, bytes)
        or len(preregistration_payload) != PROTOCOL_BYTES
        or protocol.sha256_bytes(preregistration_payload) != PROTOCOL_SHA256
        or protocol.artifact_json_bytes(dict(preregistration))
        != preregistration_payload
        or preregistration.get("gate_id") != protocol.GATE_ID
        or preregistration.get("investigation_id") != INVESTIGATION_ID
        or preregistration.get("next_gate") != GATE_ID
        or preregistration.get("runtime_eligible") is not False
    ):
        _fail("PROTOCOL_BINDING_MISMATCH", "$.protocol")
    static_contract = _mapping(
        preregistration.get("static_investigation_contract"), "$.protocol.contract"
    )
    if (
        static_contract.get("gate_id") != GATE_ID
        or static_contract.get("fixed_result_path") != RESULT_PATH
        or static_contract.get("exclusive_result_publication") is not True
        or static_contract.get("zero_internal_retry") is not True
        or static_contract.get("model_import_or_call") is not False
        or static_contract.get("processor_load_or_call") is not False
        or static_contract.get("pil_image_decode") is not False
        or static_contract.get("cuda") is not False
        or static_contract.get("network") is not False
    ):
        _fail("STATIC_CONTRACT_BINDING_MISMATCH", "$.protocol.contract")


def _validated_source_bindings(
    bindings: Mapping[str, Mapping[str, Any]],
    *,
    expected_paths: Mapping[str, str],
    location: str,
    equality_key: str,
) -> dict[str, dict[str, Any]]:
    if set(bindings) != set(expected_paths):
        _fail("SOURCE_BINDING_SET_MISMATCH", location)
    result: dict[str, dict[str, Any]] = {}
    for name, path in sorted(expected_paths.items()):
        value = dict(_mapping(bindings.get(name), f"{location}.{name}"))
        if (
            set(value) != {"path", "bytes", "sha256", equality_key}
            or value.get("path") != path
            or type(value.get("bytes")) is not int
            or value.get("bytes", 0) <= 0
            or not isinstance(value.get("sha256"), str)
            or re.fullmatch(r"sha256:[0-9a-f]{64}", value["sha256"]) is None
            or value.get(equality_key) is not True
        ):
            _fail("SOURCE_BINDING_INVALID", f"{location}.{name}")
        result[name] = value
    return result


def _structural_projection(record: Mapping[str, Any]) -> dict[str, Any]:
    model_payload = _mapping(record.get("model_payload"), "$.record.model_payload")
    prompt = _mapping(record.get("prompt_projection"), "$.record.prompt_projection")
    shape = _mapping(record.get("runtime_message_shape"), "$.record.message_shape")
    return {
        "task_family_id": record.get("task_family_id"),
        "source_kind": record.get("source_kind"),
        "source_count": record.get("source_count"),
        "model_payload_bytes": model_payload.get("bytes"),
        "prompt_projection_bytes": prompt.get("bytes"),
        "message_count": shape.get("message_count"),
        "system_messages": shape.get("system_messages"),
        "user_messages": shape.get("user_messages"),
        "image_channels": shape.get("image_channels"),
        "text_parts": shape.get("text_parts"),
        "opaque_sentinels_only": shape.get("opaque_sentinels_only"),
    }


def _content_identity_differs(
    target: Mapping[str, Any], control: Mapping[str, Any]
) -> bool:
    for name in (
        "record",
        "adapter_audit_projection",
        "model_payload",
        "prompt_projection",
        "runtime_message_transport_projection",
    ):
        target_receipt = _mapping(target.get(name), f"$.target.{name}")
        control_receipt = _mapping(control.get(name), f"$.control.{name}")
        if target_receipt.get("sha256") == control_receipt.get("sha256"):
            return False
    return True


def _marker_position_after(source: str, marker: str, start: int) -> int:
    position = source.find(marker, start)
    if position < 0:
        _inconclusive("CONTROL_FLOW_MARKER_MISSING", f"$.control_flow.{marker}")
    return position


def _result_claims(outcome: str, formal_gate_passed: bool) -> dict[str, Any]:
    if (
        outcome not in protocol.DECISION_OUTCOMES
        or type(formal_gate_passed) is not bool
    ):
        _fail("RESULT_CLAIM_INPUT_INVALID", "$.claims")
    diagnostic_protocol = outcome in {
        "static_pipeline_reconstructed_without_contract_violation",
        "static_investigation_inconclusive",
    }
    return {
        "investigation_protocol_frozen": True,
        "investigation_executed": formal_gate_passed,
        "static_investigation_complete": formal_gate_passed,
        "static_investigation_formal_gate_passed": formal_gate_passed,
        "deterministic_static_failure_reproduced": (
            formal_gate_passed
            and outcome == "deterministic_static_input_or_message_failure_reproduced"
        ),
        "closed_structural_difference_observed": (
            formal_gate_passed
            and outcome == "static_difference_observed_without_causal_failure"
        ),
        "diagnostic_protocol_freeze_justified": (
            formal_gate_passed and diagnostic_protocol
        ),
        "historical_runtime_health_established": False,
        "static_root_cause_reproduced": False,
        "failed_runtime_substage_isolated": False,
        "remediation_delta_established": False,
        "recovery_v3_justified": False,
        "diagnostic_model_or_cuda_execution_authorized": False,
        "v2_attempt_consumed": True,
        "v2_execution_retried": False,
        "formal_measurement_complete": False,
        "model_evaluated": False,
        "quality_established": False,
        "safety_established": False,
        "evaluation_repeatability_established": False,
        "resource_repeatability_established": False,
        "cross_machine_reproducibility_established": False,
        "serving_eligible": False,
        "promotion_eligible": False,
        "runtime_eligible": False,
    }


def _outcome_routes() -> dict[str, dict[str, Any]]:
    return {
        "protocol_or_lineage_invalid": {
            "next_gate_id": None,
            "action": "stop_without_result_publication_and_repair_protocol_lineage",
            "protocol_freeze_only": True,
            "execution_authorized": False,
        },
        "deterministic_static_input_or_message_failure_reproduced": {
            "next_gate_id": STATIC_REMEDIATION_PROTOCOL_GATE_ID,
            "action": "freeze_a_static_remediation_protocol_before_any_change",
            "protocol_freeze_only": True,
            "execution_authorized": False,
        },
        "static_difference_observed_without_causal_failure": {
            "next_gate_id": STATIC_DIFFERENCE_PROTOCOL_GATE_ID,
            "action": "freeze_a_static_difference_isolation_protocol",
            "protocol_freeze_only": True,
            "execution_authorized": False,
        },
        "static_pipeline_reconstructed_without_contract_violation": {
            "next_gate_id": DIAGNOSTIC_PROTOCOL_GATE_ID,
            "action": (
                "freeze_a_new_identity_and_output_diagnostic_experiment_protocol"
            ),
            "protocol_freeze_only": True,
            "execution_authorized": False,
        },
        "static_investigation_inconclusive": {
            "next_gate_id": DIAGNOSTIC_PROTOCOL_GATE_ID,
            "action": (
                "freeze_a_new_identity_and_output_diagnostic_experiment_protocol"
            ),
            "protocol_freeze_only": True,
            "execution_authorized": False,
        },
    }


def _validate_commit(value: str, location: str) -> None:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{40}", value) is None:
        _fail("GIT_COMMIT_INVALID", location)


def _validate_timestamp(value: str) -> None:
    if not isinstance(value, str) or _UTC_TIMESTAMP_PATTERN.fullmatch(value) is None:
        _fail("EXECUTED_AT_INVALID", "$.executed_at_utc")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
    except ValueError as exc:
        raise MM005GenerationFailureInvestigationResultError(
            "EXECUTED_AT_INVALID", "$.executed_at_utc"
        ) from exc
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        _fail("EXECUTED_AT_INVALID", "$.executed_at_utc")


def _mapping(value: object, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        _fail("OBJECT_REQUIRED", location)
    return value


def _object_sequence(value: object, location: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        _fail("ARRAY_REQUIRED", location)
    return [_mapping(item, f"{location}[{index}]") for index, item in enumerate(value)]


def _fail(code: str, location: str = "$") -> NoReturn:
    raise MM005GenerationFailureInvestigationResultError(code, location)


def _inconclusive(code: str, location: str) -> NoReturn:
    raise _StaticPlanInconclusive(code, location)


__all__ = [
    "DETERMINISTIC_FAILURE_DOMAIN_STEP_BY_CODE",
    "DIAGNOSTIC_PROTOCOL_GATE_ID",
    "EXCLUDED_CONTENT_IDENTITY_FIELDS",
    "FORMAL_RESULT_GATES",
    "GATE_ID",
    "IMPLEMENTATION_SOURCE_PATHS",
    "INVESTIGATION_ID",
    "MM005GenerationFailureInvestigationResultError",
    "OBSERVATION_KEYS",
    "OUTCOME_PRECEDENCE",
    "PROTOCOL_BYTES",
    "PROTOCOL_MERGE_COMMIT",
    "PROTOCOL_SHA256",
    "RESULT_PATH",
    "RESULT_REQUIRED_TOP_LEVEL_KEYS",
    "RESULT_VERSION",
    "STATIC_DIFFERENCE_PROTOCOL_GATE_ID",
    "STATIC_REMEDIATION_PROTOCOL_GATE_ID",
    "STRUCTURAL_COMPARISON_FIELDS",
    "build_control_flow_observation",
    "build_static_investigation_result",
    "build_structural_comparison",
    "outcome_predicates",
    "result_contract",
    "select_outcome",
    "validate_static_investigation_result",
]
