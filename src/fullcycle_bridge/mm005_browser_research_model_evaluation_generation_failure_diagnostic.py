"""Outcome-neutral protocol contract for the MM-005 generation diagnostic.

This module freezes evidence, identity, lifecycle, checkpoint, resource, and
authority boundaries only.  It deliberately contains no diagnostic runner and
does not import a model, processor, PIL, torch, CUDA, browser, or network stack.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any, NoReturn

from . import (
    mm005_browser_research_model_evaluation_failure_classification_v2 as failure_v2,
)
from . import (
    mm005_browser_research_model_evaluation_generation_failure_investigation as investigation,
)
from . import (
    mm005_browser_research_model_evaluation_generation_failure_investigation_result as published_result,
)
from . import mm005_browser_research_model_evaluation as v1
from . import mm005_browser_research_model_evaluation_protocol_v2 as v2

PROTOCOL_VERSION = 1
GATE_ID = published_result.DIAGNOSTIC_PROTOCOL_GATE_ID
IMPLEMENTATION_GATE_ID = (
    "MM-005-browser-research-model-evaluation-generation-failure-"
    "diagnostic-implementation-v1"
)
EXPERIMENT_ID = "mm005-browser-research-model-eval-v2-generation-failure-diagnostic-v1"
RUN_ID = "mm005-browser-research-model-eval-v2-generation-failure-diagnostic-r1"

PREREGISTRATION_PATH = (
    "configs/mm005_browser_research_model_evaluation_generation_failure_"
    "diagnostic_protocol_v1.json"
)
RUN_OUTPUT_ROOT = (
    "work/evaluation-runs/mm005-browser-research-model-eval-v2-generation-"
    "failure-diagnostic-v1"
)
ATTEMPT_OWNER_PATH = f"{RUN_OUTPUT_ROOT}/attempt-owner.json"
PROGRESS_PATH = f"{RUN_OUTPUT_ROOT}/progress.json"
SUCCESS_RESULT_PATH = f"{RUN_OUTPUT_ROOT}/diagnostic-result.json"
FAILURE_PATH = f"{RUN_OUTPUT_ROOT}/diagnostic-failure.json"
LIFECYCLE_LEASE_ROOT = f"{RUN_OUTPUT_ROOT}.lifecycle"
LIFECYCLE_LEASE_PATH = f"{LIFECYCLE_LEASE_ROOT}/lease"

RESULT_PUBLICATION_COMMIT = "c8541147717870992c60c6d2ea1c2f4ff68ee1d2"
PUBLISHED_RESULT_PATH = published_result.RESULT_PATH
PUBLISHED_RESULT_BYTES = 39_843
PUBLISHED_RESULT_SHA256 = (
    "sha256:2be8caf8dbc35d2741d81d408f21fea08d7961cc970590a25922bc757485ca93"
)
PUBLISHED_RESULT_REPORT_DIGEST = (
    "sha256:001b44cdb9d0a11a4be48e10f6653074e4bf407a43daaad1930c6d92e5f8cde7"
)
PUBLISHED_RESULT_OUTCOME = "static_pipeline_reconstructed_without_contract_violation"
IMPLEMENTATION_FREEZE_COMMIT = "c2b04f68dfbb0f96423ecf83a8d73529fdf9d055"
V2_PREREGISTRATION_PATH = v2.PREREGISTRATION_PATH
V2_PREREGISTRATION_BYTES = 120_315
V2_PREREGISTRATION_SHA256 = (
    "sha256:512b3523196bf80e7e137c7777c205fa92a57acf371464f3f65671c406706c2e"
)
V2_BOUND_SUBTREE_SHA256 = {
    "authority_contract": (
        "sha256:9d3c11031ad61ecc5b5cdbb2791e7055227249ade35ea435a6f4d633abcd8fbd"
    ),
    "candidate": (
        "sha256:bc59d9ef99ef80f7391c3b7f49c55827fb06a391cb6356ca2ab852ce465d98d1"
    ),
    "compiler": (
        "sha256:d44f7d6020269f179dfb6421fed7af22e30f30c33f8097a65d766b0b67ffa862"
    ),
    "execution_protocol": (
        "sha256:5f0360fa4636ce989c8e076e117aab1d875eeb19cd034c087fe218e37521726f"
    ),
    "input_suite": (
        "sha256:c18ff05c5c18ed52bcd91b766df054e632059f8368099e19ee9d2952eb949ad7"
    ),
    "metrics": (
        "sha256:03c1b83f1b78c94b4e2f5092b8296f5bd0d92cb42018ec511a7698c3777bf402"
    ),
    "prompt_contract": (
        "sha256:fff8fa49e0ff7fa5de018a8bc25a5b6ddf6785e867df38526430489c41ad2e9a"
    ),
    "resource_caps": (
        "sha256:b1e77badc589ac159d924f1cd3f43139f652e4b70bc91c3e4181499b51525334"
    ),
    "source_receipts": (
        "sha256:8115c0c8521b6ce67a0069e2d45ec185772f33e028e15f485e6c3a193a518fef"
    ),
    "verifier": (
        "sha256:3cb2cfd9f59e52ad6de27422bebc240f97d65cffd2ffc558eb5f33687815fcd4"
    ),
}

TARGET_RECORD_ID = investigation.TARGET_RECORD_ID
COMPLETED_PREFIX_CONTROL_IDS = investigation.COMPLETED_PREFIX_CONTROL_IDS
SAME_SHAPE_CONTROL_IDS = investigation.SAME_SHAPE_CONTROL_IDS
REGISTERED_RECORD_REGISTRY_BYTES = 22_354
REGISTERED_RECORD_REGISTRY_SHA256 = (
    "sha256:c3057651c41be738257db7ae0af4c8bcdf3419493d22064b8ea9eb935d758886"
)
DIAGNOSTIC_CASE_ORDER = (
    *COMPLETED_PREFIX_CONTROL_IDS,
    TARGET_RECORD_ID,
    *SAME_SHAPE_CONTROL_IDS,
)
TARGET_DIAGNOSTIC_INDEX = 3

PROTOCOL_SOURCE_PATHS = {
    "adapter_verifier": investigation.PROTOCOL_SOURCE_PATHS["adapter_verifier"],
    "browser_data_contract": investigation.PROTOCOL_SOURCE_PATHS[
        "browser_data_contract"
    ],
    "diagnostic_builder": (
        "scripts/prepare_mm005_browser_research_model_evaluation_generation_"
        "failure_diagnostic_protocol_v1.py"
    ),
    "diagnostic_contract": (
        "src/fullcycle_bridge/mm005_browser_research_model_evaluation_"
        "generation_failure_diagnostic.py"
    ),
    "failure_classification_v2": investigation.PROTOCOL_SOURCE_PATHS[
        "failure_classification_v2"
    ],
    "investigation_builder": investigation.PROTOCOL_SOURCE_PATHS[
        "investigation_builder"
    ],
    "investigation_protocol_contract": (
        "src/fullcycle_bridge/mm005_browser_research_model_evaluation_"
        "generation_failure_investigation.py"
    ),
    "investigation_result_contract": (
        "src/fullcycle_bridge/mm005_browser_research_model_evaluation_"
        "generation_failure_investigation_result.py"
    ),
    "model_evaluation_contract_v1": (
        "src/fullcycle_bridge/mm005_browser_research_model_evaluation.py"
    ),
    "model_evaluation_recovery_contract_v2": (
        "src/fullcycle_bridge/mm005_browser_research_model_evaluation_protocol_v2.py"
    ),
    "model_evaluation_recovery_protocol_builder_v2": (
        investigation.PROTOCOL_SOURCE_PATHS["recovery_protocol_builder_v2"]
    ),
    "model_evaluation_recovery_runner_v2": (
        "scripts/run_mm005_browser_research_model_evaluation_v2.py"
    ),
    "shared_generation_helper": ("scripts/run_mm003_multimodal_gui_action_baseline.py"),
}

RESULT_PUBLICATION_BOUND_PATHS = (
    PUBLISHED_RESULT_PATH,
    V2_PREREGISTRATION_PATH,
    investigation.PREREGISTRATION_PATH,
    failure_v2.TRACKED_ATTEMPT_OWNER_PATH,
    failure_v2.TRACKED_PROGRESS_PATH,
    failure_v2.TRACKED_FAILURE_PATH,
    failure_v2.ARTIFACT_PATH,
    *tuple(
        path
        for name, path in sorted(PROTOCOL_SOURCE_PATHS.items())
        if name not in {"diagnostic_builder", "diagnostic_contract"}
    ),
    (
        "scripts/run_mm005_browser_research_model_evaluation_generation_failure_"
        "investigation_v1.py"
    ),
    (
        "tests/test_mm005_browser_research_model_evaluation_generation_failure_"
        "investigation_result.py"
    ),
)

DIAGNOSTIC_SUBSTAGES = (
    "runtime_messages_build",
    "pre_generation_cuda_sync",
    "chat_template",
    "processor_tensorization",
    "processor_device_transfer",
    "model_generate",
    "decode",
    "post_generation_cuda_sync",
    "case_result_build",
)
HISTORICAL_UNRESOLVED_SUBSTAGES = tuple(
    investigation.HISTORICAL_GENERATION_STAGE_ORDER[3:-1]
)
HISTORICAL_TO_DIAGNOSTIC_SUBSTAGE = dict(
    zip(HISTORICAL_UNRESOLVED_SUBSTAGES, DIAGNOSTIC_SUBSTAGES, strict=True)
)
DIAGNOSTIC_CHECKPOINTS = investigation.FUTURE_DIAGNOSTIC_CHECKPOINT_REQUIREMENTS
CHECKPOINT_PAIRS = tuple(
    {
        "substage": substage,
        "started": DIAGNOSTIC_CHECKPOINTS[index * 2],
        "completed": DIAGNOSTIC_CHECKPOINTS[index * 2 + 1],
    }
    for index, substage in enumerate(DIAGNOSTIC_SUBSTAGES)
)
EVENT_IDENTITY_FIELDS = ("record_id", "diagnostic_index", "event")
PER_RECORD_CHECKPOINT_PLANS: tuple[dict[str, Any], ...] = tuple(
    {
        "record_id": record_id,
        "diagnostic_index": diagnostic_index,
        "durable_events": tuple(
            {
                "record_id": record_id,
                "diagnostic_index": diagnostic_index,
                "event": event,
            }
            for event in DIAGNOSTIC_CHECKPOINTS
        ),
    }
    for diagnostic_index, record_id in enumerate(DIAGNOSTIC_CASE_ORDER)
)
FULL_SUCCESS_DURABLE_SUBSTAGE_EVENT_COUNT = len(DIAGNOSTIC_CASE_ORDER) * len(
    DIAGNOSTIC_CHECKPOINTS
)
SESSION_LIFECYCLE_EVENTS = (
    "attempt_claimed",
    "context_preflight_completed",
    "base_load_started",
    "base_load_completed",
    "adapter_load_started",
    "adapter_load_completed",
)
TERMINAL_EVENTS = ("success_terminal_ready", "failure_terminal_ready")
PRE_RECORD_SESSION_PREFIXES = tuple(
    SESSION_LIFECYCLE_EVENTS[:length]
    for length in range(1, len(SESSION_LIFECYCLE_EVENTS) + 1)
)

OBSERVED_ENVIRONMENT_FIELDS = (
    "accelerate",
    "compute_capability",
    "device",
    "gpu",
    "gpu_vram_bytes",
    "huggingface_hub",
    "nvidia_driver",
    "pillow",
    "platform_machine",
    "platform_release",
    "platform_system",
    "platform_version",
    "python",
    "safetensors",
    "tokenizers",
    "torch",
    "transformers",
)

ALLOWED_OUTCOMES = (
    "diagnostic_protocol_or_lineage_invalid",
    "diagnostic_completed_without_observed_runtime_failure",
    "diagnostic_failure_observed_between_durable_checkpoints",
    "diagnostic_inconclusive",
)

REQUIRED_GATES = (
    "published_static_result_lineage_integrity",
    "published_static_result_semantic_boundary_integrity",
    "new_experiment_run_and_output_identity",
    "exact_target_and_control_registry",
    "historical_prefix_and_target_order_integrity",
    "durable_substage_checkpoint_closure",
    "append_only_hash_chain_and_single_writer_lifecycle",
    "safe_mutually_exclusive_terminal_contract",
    "independent_resource_contract",
    "outcome_neutral_decision_rubric",
    "zero_execution_and_zero_retry_at_protocol_freeze",
    "runtime_authority_preserved",
    "fail_closed_claims",
)


class MM005GenerationFailureDiagnosticProtocolError(ValueError):
    """Stable fail-closed error for diagnostic-protocol drift."""

    def __init__(self, code: str, location: str = "$") -> None:
        self.code = code
        self.location = location
        super().__init__(f"{code} at {location}")


def artifact_json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )


def sha256_bytes(payload: bytes) -> str:
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def parse_strict_json_bytes(payload: bytes, *, location: str) -> dict[str, Any]:
    if not isinstance(payload, bytes) or len(payload) > 8 * 1024 * 1024:
        _fail("JSON_BYTES_INVALID", location)
    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
        raise MM005GenerationFailureDiagnosticProtocolError(
            "JSON_INVALID", location
        ) from exc
    if not isinstance(value, dict):
        _fail("JSON_OBJECT_REQUIRED", location)
    return value


def expected_preregistration(
    *,
    publication_current_payloads: Mapping[str, bytes],
    publication_blob_payloads: Mapping[str, bytes],
    source_payloads: Mapping[str, bytes],
    diagnostic_output_absent: bool,
    lifecycle_lease_absent: bool,
) -> dict[str, Any]:
    """Build the exact model-free diagnostic protocol."""

    if diagnostic_output_absent is not True:
        _fail("DIAGNOSTIC_OUTPUT_PRESENT_AT_FREEZE", "$.freeze_preconditions")
    if lifecycle_lease_absent is not True:
        _fail("LIFECYCLE_LEASE_PRESENT_AT_FREEZE", "$.freeze_preconditions")
    result, v2_preregistration, publication_receipts = _validated_publication_boundary(
        publication_current_payloads, publication_blob_payloads
    )
    identity_separation = _validated_identity_separation()
    scientific_inputs = _validated_v2_scientific_inputs(v2_preregistration)
    protocol_sources = _validated_source_payloads(
        source_payloads, publication_current_payloads
    )
    registry = _record_registry_projection(result)
    durable_facts = _mapping(
        _mapping(result.get("evidence_layers"), "$.result.evidence_layers").get(
            "durable_authenticated_facts"
        ),
        "$.result.evidence_layers.durable_authenticated_facts",
    )
    unresolved = _string_sequence(
        _mapping(result.get("evidence_layers"), "$.result.evidence_layers").get(
            "unresolved_runtime_substages"
        ),
        "$.result.evidence_layers.unresolved_runtime_substages",
    )
    if unresolved != list(HISTORICAL_UNRESOLVED_SUBSTAGES):
        _fail("UNRESOLVED_SUBSTAGE_SET_MISMATCH", "$.result.evidence_layers")

    return {
        "mm005_browser_research_generation_failure_diagnostic_protocol_version": (
            PROTOCOL_VERSION
        ),
        "gate_id": GATE_ID,
        "freeze_status": "frozen",
        "decision": "outcome_neutral_generation_failure_diagnostic_preregistration",
        "experiment_id": EXPERIMENT_ID,
        "run_id": RUN_ID,
        "outputs": {
            "output_root": RUN_OUTPUT_ROOT,
            "attempt_owner": ATTEMPT_OWNER_PATH,
            "progress": PROGRESS_PATH,
            "success_result": SUCCESS_RESULT_PATH,
            "failure": FAILURE_PATH,
            "lifecycle_lease_root": LIFECYCLE_LEASE_ROOT,
            "lifecycle_lease": LIFECYCLE_LEASE_PATH,
        },
        "source_lineage": {
            "result_publication_commit": RESULT_PUBLICATION_COMMIT,
            "published_static_result": {
                **publication_receipts[PUBLISHED_RESULT_PATH],
                "report_digest": PUBLISHED_RESULT_REPORT_DIGEST,
                "selected_outcome": PUBLISHED_RESULT_OUTCOME,
                "canonical_json": True,
                "tracked_bytes_equal_result_publication_commit_blob": True,
            },
            "v2_preregistration": {
                **publication_receipts[V2_PREREGISTRATION_PATH],
                "canonical_json": True,
                "scientific_inputs_projected_from_frozen_payload": True,
                "bound_subtree_sha256": dict(V2_BOUND_SUBTREE_SHA256),
                "tracked_bytes_equal_result_publication_commit_blob": True,
            },
            "result_publication_bound_receipts": publication_receipts,
            "investigation_protocol_merge_commit": (
                published_result.PROTOCOL_MERGE_COMMIT
            ),
            "investigation_implementation_freeze_commit": (
                IMPLEMENTATION_FREEZE_COMMIT
            ),
            "protocol_sources": protocol_sources,
        },
        "freeze_preconditions": {
            "result_publication_commit_is_ancestor": True,
            "published_result_matches_commit_blob": True,
            "published_result_next_gate_matches": True,
            "v2_preregistration_matches_commit_blob": True,
            "inherited_source_closure_matches_commit_blobs": True,
            "diagnostic_protocol_freeze_justified": True,
            "new_experiment_id": identity_separation["new_experiment_id"],
            "new_run_id": identity_separation["new_run_id"],
            "new_output_root": identity_separation["new_output_root"],
            "diagnostic_output_absent": diagnostic_output_absent,
            "lifecycle_lease_absent": lifecycle_lease_absent,
            "formal_diagnostic_invocations": 0,
            "v1_or_v2_execution_retried": False,
            "model_processor_pil_torch_or_cuda_used": False,
            "browser_or_network_used": False,
        },
        "identity_separation": identity_separation,
        "evidence_boundary": {
            "durable_authenticated_facts": {
                "event_count": durable_facts.get("event_count"),
                "terminal_sequence": durable_facts.get("terminal_sequence"),
                "completed_record_ids": durable_facts.get("completed_record_ids"),
                "active_record_id": durable_facts.get("active_record_id"),
                "active_record_durable_completion": False,
                "counters": durable_facts.get("counters"),
                "stage": durable_facts.get("stage"),
                "exception_type": durable_facts.get("exception_type"),
                "root_cause_authenticated": False,
                "failed_runtime_substage_authenticated": False,
                "checkpoint_proves_model_generate_entered": False,
                "controller_console_text_authenticated": False,
            },
            "static_investigation": {
                "formal_invocations": 1,
                "internal_retries": 0,
                "selected_outcome": PUBLISHED_RESULT_OUTCOME,
                "static_plan_complete": True,
                "deterministic_static_input_or_message_failure_reproduced": False,
                "closed_structural_difference_observed": False,
                "runtime_root_cause_unresolved": True,
                "historical_runtime_health_established": False,
            },
            "unresolved_runtime_substages": list(HISTORICAL_UNRESOLVED_SUBSTAGES),
            "historical_to_diagnostic_substage": dict(
                HISTORICAL_TO_DIAGNOSTIC_SUBSTAGE
            ),
            "checkpoint_observation_does_not_prove_async_error_origin": True,
            "content_identity_difference_is_causal": False,
        },
        "record_control_registry": {
            "registered_reference": {
                "bytes": REGISTERED_RECORD_REGISTRY_BYTES,
                "sha256": REGISTERED_RECORD_REGISTRY_SHA256,
            },
            "record_count": len(DIAGNOSTIC_CASE_ORDER),
            "published_registry_order": [
                TARGET_RECORD_ID,
                *COMPLETED_PREFIX_CONTROL_IDS,
                *SAME_SHAPE_CONTROL_IDS,
            ],
            "diagnostic_case_order": list(DIAGNOSTIC_CASE_ORDER),
            "target_record_id": TARGET_RECORD_ID,
            "target_diagnostic_index": TARGET_DIAGNOSTIC_INDEX,
            "completed_prefix_control_ids": list(COMPLETED_PREFIX_CONTROL_IDS),
            "same_shape_control_ids": list(SAME_SHAPE_CONTROL_IDS),
            "records": registry,
            "exactly_matches_published_registry": True,
            "structural_comparison_fields": list(
                published_result.STRUCTURAL_COMPARISON_FIELDS
            ),
            "content_digest_differences_are_not_causal_evidence": True,
        },
        "execution_protocol": {
            "implementation_frozen_by_this_protocol": False,
            "diagnostic_execution_authorized": False,
            "single_fresh_runtime_session": True,
            "historical_completed_prefix_precedes_target": True,
            "target_is_fourth_generation_attempt": True,
            "same_shape_controls_follow_target": True,
            "stop_on_first_exception": True,
            "continue_after_failure": False,
            "formal_invocation_budget": 1,
            "retry_budget": 0,
            "per_record_attempt_budget": 1,
            "v1_or_v2_identity_or_output_reuse": False,
            "v2_output_read_only": True,
            "network": False,
            "live_browser": False,
            "capture_real_content": False,
            "training_backward_optimizer_or_adapter_write": False,
        },
        "diagnostic_checkpoint_contract": {
            "session_lifecycle_events": list(SESSION_LIFECYCLE_EVENTS),
            "substage_order": list(DIAGNOSTIC_SUBSTAGES),
            "checkpoint_pairs": [dict(item) for item in CHECKPOINT_PAIRS],
            "durable_substage_events": list(DIAGNOSTIC_CHECKPOINTS),
            "event_identity_fields": list(EVENT_IDENTITY_FIELDS),
            "per_record_checkpoint_plans": [
                {
                    "record_id": plan["record_id"],
                    "diagnostic_index": plan["diagnostic_index"],
                    "durable_events": [dict(event) for event in plan["durable_events"]],
                }
                for plan in PER_RECORD_CHECKPOINT_PLANS
            ],
            "per_record_durable_substage_event_count": len(DIAGNOSTIC_CHECKPOINTS),
            "full_success_record_count": len(DIAGNOSTIC_CASE_ORDER),
            "full_success_durable_substage_event_count": (
                FULL_SUCCESS_DURABLE_SUBSTAGE_EVENT_COUNT
            ),
            "maximum_durable_substage_event_count": (
                FULL_SUCCESS_DURABLE_SUBSTAGE_EVENT_COUNT
            ),
            "each_substage_has_unique_started_then_completed_pair": True,
            "sequence_monotonic_from_zero": True,
            "record_may_start_only_after_previous_record_completed": True,
            "completed_record_ids_must_equal_case_order_prefix": True,
            "active_record_must_equal_first_incomplete_record": True,
            "completed_record_requires_exact_full_event_plan": True,
            "active_failure_record_requires_proper_event_prefix": True,
            "checkpoint_persisted_before_next_substage": True,
            "checkpoint_flush_and_fsync_required": True,
            "format": "canonical_jsonl_append_only_sha256_chain",
            "previous_event_sha256_required_after_genesis": True,
            "single_writer_exclusive_lease": True,
            "lease_acquired_before_attempt_claim": True,
            "durable_claim_scope": ("checkpointed_facts_only_not_uncheckpointed_work"),
            "failure_interval_uses_last_started_and_completed_checkpoints": True,
            "checkpoint_observation_does_not_prove_async_error_origin": True,
            "failed_runtime_substage_isolated_at_protocol_freeze": False,
            "root_cause_authenticated_at_protocol_freeze": False,
        },
        "resource_contract": {
            "independent_from_v2_attempt": True,
            "scientific_inputs": scientific_inputs,
            "resource_caps": dict(v2.RESOURCE_CAPS),
            "scientific_inputs_bound_to_exact_v2_preregistration_blob": True,
            "resource_caps_are_integrity_gates": True,
            "required_observed_environment_fields": list(OBSERVED_ENVIRONMENT_FIELDS),
            "execution_environment_values_recorded_at_protocol_freeze": False,
            "execution_preflight_must_bind_exact_nonempty_values": True,
            "missing_or_unverifiable_execution_resource_blocks_execution": True,
            "resource_comparison_is_diagnostic_only": True,
            "resource_repeatability_claimed": False,
        },
        "terminal_contract": {
            "terminal_events": list(TERMINAL_EVENTS),
            "success_and_failure_are_mutually_exclusive": True,
            "terminal_ready_checkpoint_precedes_exact_terminal_artifact": True,
            "terminal_artifact_exclusive_create": True,
            "success_grammar": {
                "session_lifecycle_events": list(SESSION_LIFECYCLE_EVENTS),
                "completed_record_ids": list(DIAGNOSTIC_CASE_ORDER),
                "active_record_id": None,
                "active_record_diagnostic_index": None,
                "every_record_requires_exact_full_event_plan": True,
                "durable_substage_event_count": (
                    FULL_SUCCESS_DURABLE_SUBSTAGE_EVENT_COUNT
                ),
                "terminal_event": "success_terminal_ready",
            },
            "failure_scope_field": "failure_scope",
            "failure_scopes": [
                "pre_record_lifecycle",
                "inter_record_transition",
                "active_record_substage",
                "post_record_terminalization",
            ],
            "pre_record_lifecycle_failure_grammar": {
                "allowed_session_event_prefixes": [
                    list(prefix) for prefix in PRE_RECORD_SESSION_PREFIXES
                ],
                "completed_record_ids": [],
                "active_record_id": None,
                "active_record_diagnostic_index": None,
                "active_record_events": [],
                "last_started_checkpoint": None,
                "last_completed_checkpoint": None,
                "terminal_event": "failure_terminal_ready",
                "allowed_outcome": "diagnostic_inconclusive",
            },
            "inter_record_transition_failure_grammar": {
                "session_lifecycle_events": list(SESSION_LIFECYCLE_EVENTS),
                "completed_record_ids_must_be_strict_case_order_prefix": True,
                "active_record_is_first_incomplete_record": True,
                "active_record_events": [],
                "last_started_checkpoint": None,
                "last_completed_checkpoint": None,
                "terminal_event": "failure_terminal_ready",
                "allowed_outcome": "diagnostic_inconclusive",
            },
            "active_record_substage_failure_grammar": {
                "session_lifecycle_events": list(SESSION_LIFECYCLE_EVENTS),
                "completed_record_ids_must_be_strict_case_order_prefix": True,
                "active_record_is_first_incomplete_record": True,
                "active_record_events_must_be_nonempty_proper_prefix_of_plan": True,
                "last_started_checkpoint_is_latest_started_in_active_record": True,
                "last_completed_checkpoint_is_latest_completed_in_active_record_or_null": True,
                "cross_record_or_session_checkpoint_reference_forbidden": True,
                "terminal_event": "failure_terminal_ready",
                "allowed_outcome": (
                    "diagnostic_failure_observed_between_durable_checkpoints"
                ),
            },
            "post_record_terminalization_failure_grammar": {
                "session_lifecycle_events": list(SESSION_LIFECYCLE_EVENTS),
                "completed_record_ids": list(DIAGNOSTIC_CASE_ORDER),
                "active_record_id": None,
                "active_record_diagnostic_index": None,
                "active_record_events": [],
                "durable_substage_event_count": (
                    FULL_SUCCESS_DURABLE_SUBSTAGE_EVENT_COUNT
                ),
                "last_started_checkpoint": dict(
                    PER_RECORD_CHECKPOINT_PLANS[-1]["durable_events"][-2]
                ),
                "last_completed_checkpoint": dict(
                    PER_RECORD_CHECKPOINT_PLANS[-1]["durable_events"][-1]
                ),
                "success_terminal_ready_absent": True,
                "terminal_event": "failure_terminal_ready",
                "allowed_outcome": "diagnostic_inconclusive",
            },
            "failure_requires_first_uncompleted_record_when_record_scope_exists": True,
            "completed_record_ids_always_exact_case_order_prefix": True,
            "failure_before_attempt_claim_forbids_terminal_artifact": True,
            "failure_last_checkpoint_fields_are_scope_safe_and_nullable": True,
            "failure_requires_safe_exception_type": True,
            "failure_allowed_text_fields": ["exception_type"],
            "failure_message_traceback_absolute_path_or_secret_forbidden": True,
            "partial_terminal_repair": "exact_expected_canonical_prefix_only",
            "result_and_failure_schema_frozen_by_this_protocol": False,
            "implementation_and_result_contract_deferred_to_next_gate": True,
        },
        "decision_rubric": {
            "allowed_outcomes": list(ALLOWED_OUTCOMES),
            "outcome_selected_at_protocol_freeze": None,
            "exactly_one_outcome_required_after_authorized_execution": True,
            "checkpoint_interval_is_observation_not_causal_origin": True,
            "runtime_root_cause_requires_separately_authenticated_evidence": True,
            "static_pass_does_not_establish_historical_runtime_health": True,
            "no_recovery_or_remediation_route_selected_at_protocol_freeze": True,
        },
        "formal_gate": {
            "required_gates": list(REQUIRED_GATES),
            "protocol_freeze_is_not_diagnostic_execution": True,
            "protocol_freeze_is_not_formal_model_measurement": True,
            "quality_threshold_gate": False,
        },
        "authority_contract": {
            "protocol_freeze_authorized": True,
            "diagnostic_implementation_freeze_authorized_after_clean_merge": True,
            "diagnostic_execution_authorized": False,
            "processor_execution_authorized": False,
            "model_or_cuda_execution_authorized": False,
            "live_browser_or_network_authorized": False,
            "capture_authorized": False,
            "training_authorized": False,
            "v1_or_v2_retry_authorized": False,
            "recovery_v3_authorized": False,
            "model_output_has_execution_authority": False,
            "page_content_has_execution_authority": False,
            "runtime_repository_changed": False,
            "runtime_integration_changed": False,
            "runtime_policy_or_approval_bypass": False,
            "runtime_is_sole_policy_approval_wal_grounding_budget_dispatch_boundary": (
                True
            ),
        },
        "claims": {
            "diagnostic_protocol_frozen": True,
            "diagnostic_protocol_freeze_justified": True,
            "investigation_protocol_frozen": True,
            "investigation_executed": True,
            "static_investigation_complete": True,
            "static_investigation_formal_gate_passed": True,
            "v2_attempt_consumed": True,
            "diagnostic_attempt_consumed": False,
            "diagnostic_executed": False,
            "diagnostic_execution_authorized": False,
            "historical_runtime_health_established": False,
            "static_root_cause_reproduced": False,
            "failed_runtime_substage_isolated": False,
            "runtime_root_cause_established": False,
            "remediation_delta_established": False,
            "recovery_v3_justified": False,
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
        },
        "locked_next_action": {
            "next_gate_id": IMPLEMENTATION_GATE_ID,
            "action": (
                "freeze_diagnostic_implementation_and_result_contract_without_execution"
            ),
            "eligible_to_start_after_clean_protocol_merge": True,
            "implementation_freeze_only": True,
            "diagnostic_execution_authorized": False,
            "recovery_v3_authorized": False,
            "v2_retry_authorized": False,
        },
        "next_gate": IMPLEMENTATION_GATE_ID,
        "runtime_eligible": False,
    }


def validate_preregistration(value: Mapping[str, Any], **inputs: Any) -> dict[str, Any]:
    """Fail closed unless the tracked protocol exactly recomputes."""

    expected = expected_preregistration(**inputs)
    if artifact_json_bytes(dict(value)) != artifact_json_bytes(expected):
        _fail("PREREGISTRATION_MISMATCH", "$.preregistration")
    return expected


def _validated_publication_boundary(
    current_payloads: Mapping[str, bytes], blob_payloads: Mapping[str, bytes]
) -> tuple[dict[str, Any], dict[str, Any], dict[str, dict[str, Any]]]:
    expected_paths = set(RESULT_PUBLICATION_BOUND_PATHS)
    if set(current_payloads) != expected_paths or set(blob_payloads) != expected_paths:
        _fail("RESULT_PUBLICATION_SOURCE_SET_MISMATCH", "$.publication_payloads")
    receipts: dict[str, dict[str, Any]] = {}
    for path in RESULT_PUBLICATION_BOUND_PATHS:
        current = current_payloads.get(path)
        blob = blob_payloads.get(path)
        if (
            not isinstance(current, bytes)
            or not current
            or not isinstance(blob, bytes)
            or current != blob
        ):
            _fail("RESULT_PUBLICATION_BLOB_MISMATCH", f"$.publication.{path}")
        receipts[path] = _receipt(path, current)
    result = _validated_published_result(
        current_payloads[PUBLISHED_RESULT_PATH], blob_payloads[PUBLISHED_RESULT_PATH]
    )
    v2_preregistration = _validated_v2_preregistration(
        current_payloads[V2_PREREGISTRATION_PATH],
        blob_payloads[V2_PREREGISTRATION_PATH],
    )
    return result, v2_preregistration, receipts


def _validated_published_result(
    payload: bytes, publication_blob_payload: bytes
) -> dict[str, Any]:
    if (
        not isinstance(payload, bytes)
        or not isinstance(publication_blob_payload, bytes)
        or payload != publication_blob_payload
        or len(payload) != PUBLISHED_RESULT_BYTES
        or sha256_bytes(payload) != PUBLISHED_RESULT_SHA256
    ):
        _fail("PUBLISHED_RESULT_BINDING_MISMATCH", "$.published_result")
    result = parse_strict_json_bytes(payload, location="$.published_result")
    if artifact_json_bytes(result) != payload:
        _fail("PUBLISHED_RESULT_NOT_CANONICAL", "$.published_result")
    if set(result) != set(published_result.RESULT_REQUIRED_TOP_LEVEL_KEYS):
        _fail("PUBLISHED_RESULT_SCHEMA_MISMATCH", "$.published_result")
    decision = _mapping(result.get("decision"), "$.published_result.decision")
    action = _mapping(
        result.get("locked_next_action"), "$.published_result.locked_next_action"
    )
    execution = _mapping(result.get("execution"), "$.published_result.execution")
    claims = _mapping(result.get("claims"), "$.published_result.claims")
    implementation = _mapping(
        result.get("implementation_lineage"),
        "$.published_result.implementation_lineage",
    )
    if (
        result.get(
            "mm005_browser_research_generation_failure_investigation_result_version"
        )
        != published_result.RESULT_VERSION
        or result.get("gate_id") != published_result.GATE_ID
        or result.get("investigation_id") != published_result.INVESTIGATION_ID
        or result.get("report_digest") != PUBLISHED_RESULT_REPORT_DIGEST
        or result.get("runtime_eligible") is not False
        or decision.get("selected_outcome") != PUBLISHED_RESULT_OUTCOME
        or decision.get("runtime_root_cause_unresolved") is not True
        or decision.get("historical_runtime_health_established") is not False
        or action.get("next_gate_id") != GATE_ID
        or action.get("eligible_to_start") is not True
        or action.get("diagnostic_execution_authorized") is not False
        or execution.get("formal_static_investigation_invocations") != 1
        or execution.get("internal_retries") != 0
        or execution.get("model_free") is not True
        or implementation.get("implementation_freeze_commit")
        != IMPLEMENTATION_FREEZE_COMMIT
        or claims.get("diagnostic_protocol_freeze_justified") is not True
        or claims.get("failed_runtime_substage_isolated") is not False
        or claims.get("diagnostic_model_or_cuda_execution_authorized") is not False
        or claims.get("v2_attempt_consumed") is not True
        or claims.get("v2_execution_retried") is not False
    ):
        _fail("PUBLISHED_RESULT_BOUNDARY_MISMATCH", "$.published_result")
    return result


def _validated_v2_preregistration(
    payload: bytes, publication_blob_payload: bytes
) -> dict[str, Any]:
    if (
        not isinstance(payload, bytes)
        or not isinstance(publication_blob_payload, bytes)
        or payload != publication_blob_payload
        or len(payload) != V2_PREREGISTRATION_BYTES
        or sha256_bytes(payload) != V2_PREREGISTRATION_SHA256
    ):
        _fail("V2_PREREGISTRATION_BINDING_MISMATCH", "$.v2_preregistration")
    value = parse_strict_json_bytes(payload, location="$.v2_preregistration")
    if artifact_json_bytes(value) != payload:
        _fail("V2_PREREGISTRATION_NOT_CANONICAL", "$.v2_preregistration")
    return value


def _validated_v2_scientific_inputs(value: Mapping[str, Any]) -> dict[str, Any]:
    for name, expected_digest in V2_BOUND_SUBTREE_SHA256.items():
        if sha256_bytes(artifact_json_bytes(value.get(name))) != expected_digest:
            _fail("V2_BOUND_SUBTREE_MISMATCH", f"$.v2_preregistration.{name}")
    candidate = _mapping(value.get("candidate"), "$.v2_preregistration.candidate")
    environment = _mapping(
        candidate.get("environment"), "$.v2_preregistration.candidate.environment"
    )
    execution = _mapping(
        value.get("execution_protocol"), "$.v2_preregistration.execution_protocol"
    )
    generation = _mapping(
        execution.get("generation"),
        "$.v2_preregistration.execution_protocol.generation",
    )
    python_invocation = _mapping(
        execution.get("python_invocation"),
        "$.v2_preregistration.execution_protocol.python_invocation",
    )
    outputs = _mapping(value.get("outputs"), "$.v2_preregistration.outputs")
    input_suite = _mapping(value.get("input_suite"), "$.v2_preregistration.input_suite")
    prompt_contract = _mapping(
        value.get("prompt_contract"), "$.v2_preregistration.prompt_contract"
    )
    adapter_receipts = _mapping(
        candidate.get("adapter_files"),
        "$.v2_preregistration.candidate.adapter_files",
    )
    resource_caps = _mapping(
        value.get("resource_caps"), "$.v2_preregistration.resource_caps"
    )
    if (
        value.get("mm005_browser_research_model_evaluation_protocol_version")
        != v2.PROTOCOL_VERSION
        or value.get("gate_id") != v2.PROTOCOL_GATE_ID
        or value.get("freeze_status") != "frozen"
        or value.get("experiment_id") != v2.EXPERIMENT_ID
        or value.get("run_id") != v2.RUN_ID
        or outputs.get("output_directory") != v2.RUN_OUTPUT_ROOT
        or candidate.get("model_id") != v2.MODEL_ID
        or candidate.get("model_revision") != v2.MODEL_REVISION
        or candidate.get("adapter_model_id") != v2.ADAPTER_MODEL_ID
        or dict(adapter_receipts) != v2.ADAPTER_RECEIPTS
        or candidate.get("execution_form") != "nf4_base_plus_read_only_lora_adapter"
        or candidate.get("adapter_mutation_allowed") is not False
        or candidate.get("training_allowed") is not False
        or candidate.get("model_or_tensor_save_allowed") is not False
        or input_suite.get("suite_id") != v2.SUITE_ID
        or input_suite.get("record_count") != v2.EXPECTED_RECORDS
        or input_suite.get("train_records") != v1.EXPECTED_TRAIN_RECORDS
        or input_suite.get("validation_records") != v1.EXPECTED_VALIDATION_RECORDS
        or input_suite.get("source_binding_count") != v2.EXPECTED_SOURCE_BINDINGS
        or input_suite.get("screenshot_binding_count") != v2.EXPECTED_SOURCE_BINDINGS
        or input_suite.get("audit_only_source_snapshot_binding_count")
        != v2.EXPECTED_SOURCE_BINDINGS
        or prompt_contract.get("system_prompt") != v1.SYSTEM_PROMPT
        or execution.get("model_snapshot_root") != v2.MODEL_SNAPSHOT_ROOT
        or execution.get("adapter_root") != v2.ADAPTER_ROOT
        or python_invocation.get("executable") != v2.FORMAL_PYTHON_PATH
        or generation.get("seed") != v2.SEED
        or generation.get("max_new_tokens") != v2.MAX_NEW_TOKENS
        or generation.get("device_map") != {"": 0}
        or environment.get("device") != "cuda"
        or dict(resource_caps) != v2.RESOURCE_CAPS
    ):
        _fail("V2_SCIENTIFIC_INPUT_BOUNDARY_MISMATCH", "$.v2_preregistration")
    return {
        "model_id": candidate["model_id"],
        "model_revision": candidate["model_revision"],
        "model_snapshot_root": execution["model_snapshot_root"],
        "adapter_root": execution["adapter_root"],
        "adapter_receipts": dict(adapter_receipts),
        "formal_python_path": python_invocation["executable"],
        "seed": generation["seed"],
        "max_new_tokens": generation["max_new_tokens"],
        "device": environment["device"],
        "device_map": dict(
            _mapping(
                generation["device_map"],
                "$.v2_preregistration.execution_protocol.generation.device_map",
            )
        ),
    }


def _validated_identity_separation() -> dict[str, Any]:
    forbidden_prior_ids = (
        v1.EXPERIMENT_ID,
        v1.RUN_ID,
        v2.EXPERIMENT_ID,
        v2.RUN_ID,
        investigation.INVESTIGATION_ID,
    )
    if (
        not isinstance(EXPERIMENT_ID, str)
        or not EXPERIMENT_ID
        or EXPERIMENT_ID.casefold() in {item.casefold() for item in forbidden_prior_ids}
        or not isinstance(RUN_ID, str)
        or not RUN_ID
        or RUN_ID.casefold() in {item.casefold() for item in forbidden_prior_ids}
        or EXPERIMENT_ID.casefold() == RUN_ID.casefold()
    ):
        _fail("DIAGNOSTIC_IDENTITY_REUSE", "$.identity_separation")

    expected_derived_paths = {
        ATTEMPT_OWNER_PATH: f"{RUN_OUTPUT_ROOT}/attempt-owner.json",
        PROGRESS_PATH: f"{RUN_OUTPUT_ROOT}/progress.json",
        SUCCESS_RESULT_PATH: f"{RUN_OUTPUT_ROOT}/diagnostic-result.json",
        FAILURE_PATH: f"{RUN_OUTPUT_ROOT}/diagnostic-failure.json",
        LIFECYCLE_LEASE_ROOT: f"{RUN_OUTPUT_ROOT}.lifecycle",
        LIFECYCLE_LEASE_PATH: f"{RUN_OUTPUT_ROOT}.lifecycle/lease",
    }
    if any(actual != expected for actual, expected in expected_derived_paths.items()):
        _fail("DIAGNOSTIC_DERIVED_PATH_MISMATCH", "$.identity_separation")

    prior_roots = (
        v1.RUN_OUTPUT_ROOT,
        v2.RUN_OUTPUT_ROOT,
        v2.LIFECYCLE_LEASE_ROOT,
        investigation.PREREGISTRATION_PATH,
        investigation.RESULT_PATH,
    )
    new_roots = (RUN_OUTPUT_ROOT, LIFECYCLE_LEASE_ROOT)
    if _paths_overlap(*new_roots) or any(
        _paths_overlap(new_root, prior_root)
        for new_root in new_roots
        for prior_root in prior_roots
    ):
        _fail("DIAGNOSTIC_OUTPUT_IDENTITY_REUSE", "$.identity_separation")
    return {
        "comparison": "windows_case_insensitive_posix_path_identity_and_overlap",
        "forbidden_prior_experiment_or_investigation_ids": list(forbidden_prior_ids),
        "forbidden_prior_run_or_investigation_ids": list(forbidden_prior_ids),
        "forbidden_prior_output_or_lease_roots": list(prior_roots),
        "new_experiment_id": True,
        "new_run_id": True,
        "new_output_root": True,
        "new_output_and_lease_roots_do_not_overlap": True,
    }


def _paths_overlap(left: str, right: str) -> bool:
    left_parts = _validated_path_identity_parts(left)
    right_parts = _validated_path_identity_parts(right)
    shared = min(len(left_parts), len(right_parts))
    return left_parts[:shared] == right_parts[:shared]


def _validated_path_identity_parts(value: str) -> tuple[str, ...]:
    if not isinstance(value, str) or not value or "\\" in value:
        _fail("PATH_IDENTITY_INVALID", "$.identity_separation")
    parts = tuple(part.casefold() for part in value.split("/"))
    if any(not part or part in {".", ".."} for part in parts):
        _fail("PATH_IDENTITY_INVALID", "$.identity_separation")
    return parts


def _validated_source_payloads(
    source_payloads: Mapping[str, bytes],
    publication_current_payloads: Mapping[str, bytes],
) -> dict[str, dict[str, Any]]:
    if set(source_payloads) != set(PROTOCOL_SOURCE_PATHS):
        _fail("PROTOCOL_SOURCE_SET_MISMATCH", "$.source_payloads")
    receipts: dict[str, dict[str, Any]] = {}
    for name, path in sorted(PROTOCOL_SOURCE_PATHS.items()):
        payload = source_payloads.get(name)
        if not isinstance(payload, bytes) or not payload:
            _fail("PROTOCOL_SOURCE_BYTES_INVALID", f"$.source_payloads.{name}")
        if (
            path in publication_current_payloads
            and payload != publication_current_payloads[path]
        ):
            _fail("INHERITED_PROTOCOL_SOURCE_MISMATCH", f"$.source_payloads.{name}")
        receipts[name] = _receipt(path, payload)
    return receipts


def _record_registry_projection(result: Mapping[str, Any]) -> list[dict[str, Any]]:
    registry = _mapping(
        result.get("record_registry"), "$.published_result.record_registry"
    )
    reference = _mapping(
        registry.get("registered_reference"),
        "$.published_result.record_registry.registered_reference",
    )
    observed = _mapping(
        registry.get("observed"), "$.published_result.record_registry.observed"
    )
    records = _object_sequence(
        observed.get("records"), "$.published_result.record_registry.observed.records"
    )
    published_order = (
        TARGET_RECORD_ID,
        *COMPLETED_PREFIX_CONTROL_IDS,
        *SAME_SHAPE_CONTROL_IDS,
    )
    if (
        reference.get("bytes") != REGISTERED_RECORD_REGISTRY_BYTES
        or reference.get("sha256") != REGISTERED_RECORD_REGISTRY_SHA256
        or registry.get("exactly_matches_registered") is not True
        or len(records) != len(published_order)
        or tuple(item.get("record_id") for item in records) != published_order
    ):
        _fail(
            "PUBLISHED_RECORD_REGISTRY_MISMATCH", "$.published_result.record_registry"
        )
    by_id = {str(item.get("record_id")): item for item in records}
    if set(by_id) != set(DIAGNOSTIC_CASE_ORDER):
        _fail("PUBLISHED_RECORD_SET_MISMATCH", "$.published_result.record_registry")
    projected: list[dict[str, Any]] = []
    for diagnostic_index, record_id in enumerate(DIAGNOSTIC_CASE_ORDER):
        item = by_id[record_id]
        role = item.get("role")
        expected_role = (
            "target"
            if record_id == TARGET_RECORD_ID
            else (
                "authenticated_completed_prefix_control"
                if record_id in COMPLETED_PREFIX_CONTROL_IDS
                else "same_shape_static_control"
            )
        )
        if role != expected_role:
            _fail("PUBLISHED_RECORD_ROLE_MISMATCH", f"$.record.{record_id}")
        model_payload = _mapping(
            item.get("model_payload"), f"$.record.{record_id}.model_payload"
        )
        prompt_projection = _mapping(
            item.get("prompt_projection"),
            f"$.record.{record_id}.prompt_projection",
        )
        message_shape = _mapping(
            item.get("runtime_message_shape"),
            f"$.record.{record_id}.runtime_message_shape",
        )
        projected.append(
            {
                "record_id": record_id,
                "role": role,
                "diagnostic_index": diagnostic_index,
                "published_case_order_index": item.get("case_order_index"),
                "dataset_record_index": item.get("dataset_record_index"),
                "split": item.get("split"),
                "template_id": item.get("template_id"),
                "task_family_id": item.get("task_family_id"),
                "source_kind": item.get("source_kind"),
                "source_count": item.get("source_count"),
                "model_payload": dict(model_payload),
                "prompt_projection": dict(prompt_projection),
                "runtime_message_shape": dict(message_shape),
            }
        )
    target = projected[TARGET_DIAGNOSTIC_INDEX]
    if (
        target.get("record_id") != TARGET_RECORD_ID
        or target.get("published_case_order_index") != 3
        or target.get("dataset_record_index")
        != investigation.TARGET_DATASET_RECORD_INDEX
    ):
        _fail("TARGET_DIAGNOSTIC_ORDER_MISMATCH", "$.record_control_registry")
    return projected


def _receipt(path: str, payload: bytes) -> dict[str, Any]:
    return {"path": path, "bytes": len(payload), "sha256": sha256_bytes(payload)}


def _mapping(value: object, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        _fail("OBJECT_REQUIRED", location)
    return value


def _object_sequence(value: object, location: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        _fail("ARRAY_REQUIRED", location)
    return [_mapping(item, f"{location}[{index}]") for index, item in enumerate(value)]


def _string_sequence(value: object, location: str) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        _fail("STRING_ARRAY_REQUIRED", location)
    if any(not isinstance(item, str) for item in value):
        _fail("STRING_ARRAY_REQUIRED", location)
    return list(value)


def _unique_object(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail("JSON_DUPLICATE_KEY", "$.json")
        result[key] = value
    return result


def _reject_constant(value: str) -> NoReturn:
    _fail("JSON_NONFINITE", f"$.json.{value}")


def _fail(code: str, location: str = "$") -> NoReturn:
    raise MM005GenerationFailureDiagnosticProtocolError(code, location)


__all__ = [
    "ALLOWED_OUTCOMES",
    "ATTEMPT_OWNER_PATH",
    "CHECKPOINT_PAIRS",
    "COMPLETED_PREFIX_CONTROL_IDS",
    "DIAGNOSTIC_CASE_ORDER",
    "DIAGNOSTIC_CHECKPOINTS",
    "DIAGNOSTIC_SUBSTAGES",
    "EVENT_IDENTITY_FIELDS",
    "EXPERIMENT_ID",
    "FAILURE_PATH",
    "GATE_ID",
    "HISTORICAL_TO_DIAGNOSTIC_SUBSTAGE",
    "HISTORICAL_UNRESOLVED_SUBSTAGES",
    "IMPLEMENTATION_GATE_ID",
    "LIFECYCLE_LEASE_PATH",
    "LIFECYCLE_LEASE_ROOT",
    "MM005GenerationFailureDiagnosticProtocolError",
    "OBSERVED_ENVIRONMENT_FIELDS",
    "PER_RECORD_CHECKPOINT_PLANS",
    "PREREGISTRATION_PATH",
    "PROGRESS_PATH",
    "PROTOCOL_SOURCE_PATHS",
    "PROTOCOL_VERSION",
    "PUBLISHED_RESULT_BYTES",
    "PUBLISHED_RESULT_PATH",
    "PUBLISHED_RESULT_REPORT_DIGEST",
    "PUBLISHED_RESULT_SHA256",
    "REGISTERED_RECORD_REGISTRY_BYTES",
    "REGISTERED_RECORD_REGISTRY_SHA256",
    "REQUIRED_GATES",
    "RESULT_PUBLICATION_BOUND_PATHS",
    "RESULT_PUBLICATION_COMMIT",
    "RUN_ID",
    "RUN_OUTPUT_ROOT",
    "SAME_SHAPE_CONTROL_IDS",
    "SESSION_LIFECYCLE_EVENTS",
    "SUCCESS_RESULT_PATH",
    "TARGET_DIAGNOSTIC_INDEX",
    "TARGET_RECORD_ID",
    "TERMINAL_EVENTS",
    "V2_BOUND_SUBTREE_SHA256",
    "V2_PREREGISTRATION_BYTES",
    "V2_PREREGISTRATION_PATH",
    "V2_PREREGISTRATION_SHA256",
    "artifact_json_bytes",
    "expected_preregistration",
    "parse_strict_json_bytes",
    "sha256_bytes",
    "validate_preregistration",
]
