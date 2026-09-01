"""Protocol-only recovery for the exhausted MM-005 diagnostic identity.

This module freezes a new experiment, run, and output identity plus the exact
output-parent preparation boundary required by a future v2 implementation.  It
does not contain a runner, execution authority, result contract, model import,
CUDA operation, browser, network client, or Runtime integration.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import PurePosixPath
from typing import Any, NoReturn, cast

from . import mm005_browser_research_model_evaluation_protocol_v2 as original_v2
from . import (
    mm005_browser_research_model_evaluation_generation_failure_diagnostic as v1_protocol,
)
from . import (
    mm005_browser_research_model_evaluation_generation_failure_diagnostic_invocation_closeout as v1_closeout,
)
from . import (
    mm005_browser_research_model_evaluation_generation_failure_diagnostic_result as v1_result_contract,
)

PROTOCOL_VERSION = 2
GATE_ID = v1_closeout.NEW_IDENTITY_PROTOCOL_GATE_ID
IMPLEMENTATION_GATE_ID = v1_closeout.NEW_IDENTITY_IMPLEMENTATION_GATE_ID
AUTHORITY_GATE_ID = v1_closeout.NEW_IDENTITY_AUTHORITY_GATE_ID
EXECUTION_GATE_ID = v1_closeout.NEW_IDENTITY_EXECUTION_GATE_ID

EXPERIMENT_ID = "mm005-browser-research-model-eval-v2-generation-failure-diagnostic-v2"
RUN_ID = "mm005-browser-research-model-eval-v2-generation-failure-diagnostic-r2"
PREREGISTRATION_PATH = (
    "configs/mm005_browser_research_model_evaluation_generation_failure_"
    "diagnostic_protocol_v2.json"
)
RUN_OUTPUT_ROOT = (
    "work/evaluation-runs/mm005-browser-research-model-eval-v2-generation-"
    "failure-diagnostic-v2"
)
ATTEMPT_OWNER_PATH = f"{RUN_OUTPUT_ROOT}/attempt-owner.json"
PROGRESS_PATH = f"{RUN_OUTPUT_ROOT}/progress.json"
SUCCESS_RESULT_PATH = f"{RUN_OUTPUT_ROOT}/diagnostic-result.json"
FAILURE_PATH = f"{RUN_OUTPUT_ROOT}/diagnostic-failure.json"
LIFECYCLE_LEASE_ROOT = f"{RUN_OUTPUT_ROOT}.lifecycle"
LIFECYCLE_LEASE_PATH = f"{LIFECYCLE_LEASE_ROOT}/lease"
OUTPUT_PARENT_PATH = "work/evaluation-runs"
WORK_ROOT_PATH = "work"
PREDECESSOR_RUNTIME_ROOTS = (
    original_v2.RUN_OUTPUT_ROOT,
    original_v2.LIFECYCLE_LEASE_ROOT,
    v1_protocol.RUN_OUTPUT_ROOT,
    v1_protocol.LIFECYCLE_LEASE_ROOT,
)

ORIGINAL_V2_INTRODUCTION_COMMIT = "91b637c6b365ea8632b31335f5c74ac6c60e6b71"
STATIC_RESULT_COMMIT = v1_protocol.RESULT_PUBLICATION_COMMIT
V1_PROTOCOL_COMMIT = "9c90c5e68d4386b30db613930ec7dc0147999c04"
V1_IMPLEMENTATION_COMMIT = "7da39396c951a9248fe49c1bd69080923b827fa1"
V1_AUTHORITY_COMMIT = v1_closeout.AUTHORITY_INTRODUCTION_COMMIT
V1_CLOSEOUT_COMMIT = "fd552896df1aea817ba4d2ece3bf43a8f248424f"
MAINTENANCE_MERGE_COMMIT = "266e9b695af0f93ae4c82e36ac484cb2d3d3a521"

COMMIT_PARENT_CHAIN = {
    V1_PROTOCOL_COMMIT: STATIC_RESULT_COMMIT,
    V1_IMPLEMENTATION_COMMIT: V1_PROTOCOL_COMMIT,
    V1_AUTHORITY_COMMIT: V1_IMPLEMENTATION_COMMIT,
    V1_CLOSEOUT_COMMIT: V1_AUTHORITY_COMMIT,
    MAINTENANCE_MERGE_COMMIT: V1_CLOSEOUT_COMMIT,
}
COMMIT_ANCESTOR_RELATIONS = (
    (ORIGINAL_V2_INTRODUCTION_COMMIT, STATIC_RESULT_COMMIT),
    (STATIC_RESULT_COMMIT, MAINTENANCE_MERGE_COMMIT),
)

V1_PROTOCOL_BYTES = 57_143
V1_PROTOCOL_SHA256 = (
    "sha256:13d1808168819414df2a0ca33d1f59e5e8efd52de6f0b49946d02cf070c992d6"
)
V1_CLOSEOUT_BYTES = 6_507
V1_CLOSEOUT_SHA256 = (
    "sha256:d8a64be5b0361322246faf4eeccde04f9921e0a9c586f3498b188a6477d1ddce"
)
V1_CLOSEOUT_CONTRACT_PATH = (
    "src/fullcycle_bridge/mm005_browser_research_model_evaluation_generation_"
    "failure_diagnostic_invocation_closeout.py"
)
V1_CLOSEOUT_CONTRACT_BYTES = 15_144
V1_CLOSEOUT_CONTRACT_SHA256 = (
    "sha256:115c1bb180a496c03c199d209d3b7a25514b58956a1d4222e25eec225394e649"
)
V1_AUTHORITY_BYTES = v1_closeout.AUTHORITY_BYTES
V1_AUTHORITY_SHA256 = v1_closeout.AUTHORITY_SHA256
STATIC_RESULT_BYTES = v1_protocol.PUBLISHED_RESULT_BYTES
STATIC_RESULT_SHA256 = v1_protocol.PUBLISHED_RESULT_SHA256
STATIC_RESULT_REPORT_DIGEST = v1_protocol.PUBLISHED_RESULT_REPORT_DIGEST
ORIGINAL_V2_PREREGISTRATION_BYTES = v1_protocol.V2_PREREGISTRATION_BYTES
ORIGINAL_V2_PREREGISTRATION_SHA256 = v1_protocol.V2_PREREGISTRATION_SHA256
RECORD_REGISTRY_BYTES = v1_protocol.REGISTERED_RECORD_REGISTRY_BYTES
RECORD_REGISTRY_SHA256 = v1_protocol.REGISTERED_RECORD_REGISTRY_SHA256

V1_RUNNER_BYTES = v1_closeout.RUNNER_BYTES
V1_RUNNER_SHA256 = v1_closeout.RUNNER_SHA256
RECOVERY_IO_BYTES = v1_closeout.RECOVERY_IO_BYTES
RECOVERY_IO_SHA256 = v1_closeout.RECOVERY_IO_SHA256
V1_PROTOCOL_CONTRACT_PATH = (
    "src/fullcycle_bridge/mm005_browser_research_model_evaluation_generation_"
    "failure_diagnostic.py"
)
V1_PROTOCOL_CONTRACT_BYTES = 50_585
V1_PROTOCOL_CONTRACT_SHA256 = (
    "sha256:8b014e475d9e13c66727e369ad4f8fde5be75dd784cf09e7d5aadff2614f22a1"
)
V1_RESULT_CONTRACT_PATH = (
    "src/fullcycle_bridge/mm005_browser_research_model_evaluation_generation_"
    "failure_diagnostic_result.py"
)
V1_RESULT_CONTRACT_BYTES = 77_454
V1_RESULT_CONTRACT_SHA256 = (
    "sha256:d81fd557d2b2426d9f61ddeda58a04110a1b9d9e7e6581d3d5009e86d7fbde40"
)
V1_PROTOCOL_TEST_PATH = (
    "tests/test_mm005_browser_research_model_evaluation_generation_failure_"
    "diagnostic.py"
)
V1_PROTOCOL_TEST_BYTES = 40_922
V1_PROTOCOL_TEST_SHA256 = (
    "sha256:50ebaf1afa2d2c0fd02e1fbcb8fed54af19ef30c3e4561365f991a4153107d46"
)
V1_RESULT_TEST_PATH = (
    "tests/test_mm005_browser_research_model_evaluation_generation_failure_"
    "diagnostic_result.py"
)
V1_RESULT_TEST_BYTES = 74_885
V1_RESULT_TEST_SHA256 = (
    "sha256:6c7b9307d715aa3ac12eb03c0566b83f9591ceafb21e9ea320172e29ffebc35c"
)

LINEAGE_BINDINGS: dict[str, dict[str, object]] = {
    "original_v2_preregistration": {
        "commit": ORIGINAL_V2_INTRODUCTION_COMMIT,
        "role": "unique_first_parent_introduction",
        "path": v1_protocol.V2_PREREGISTRATION_PATH,
        "bytes": ORIGINAL_V2_PREREGISTRATION_BYTES,
        "sha256": ORIGINAL_V2_PREREGISTRATION_SHA256,
    },
    "original_v2_static_result_binding": {
        "commit": STATIC_RESULT_COMMIT,
        "role": "static_result_publication_binding",
        "path": v1_protocol.V2_PREREGISTRATION_PATH,
        "bytes": ORIGINAL_V2_PREREGISTRATION_BYTES,
        "sha256": ORIGINAL_V2_PREREGISTRATION_SHA256,
    },
    "original_v2_protocol_v2_base": {
        "commit": MAINTENANCE_MERGE_COMMIT,
        "role": "protocol_v2_base_inherited_blob",
        "path": v1_protocol.V2_PREREGISTRATION_PATH,
        "bytes": ORIGINAL_V2_PREREGISTRATION_BYTES,
        "sha256": ORIGINAL_V2_PREREGISTRATION_SHA256,
    },
    "published_static_result": {
        "commit": STATIC_RESULT_COMMIT,
        "role": "static_result_publication",
        "path": v1_protocol.PUBLISHED_RESULT_PATH,
        "bytes": STATIC_RESULT_BYTES,
        "sha256": STATIC_RESULT_SHA256,
    },
    "v1_diagnostic_protocol": {
        "commit": V1_PROTOCOL_COMMIT,
        "role": "v1_protocol_freeze",
        "path": v1_protocol.PREREGISTRATION_PATH,
        "bytes": V1_PROTOCOL_BYTES,
        "sha256": V1_PROTOCOL_SHA256,
    },
    "v1_diagnostic_runner": {
        "commit": V1_IMPLEMENTATION_COMMIT,
        "role": "v1_implementation_freeze",
        "path": v1_closeout.RUNNER_PATH,
        "bytes": V1_RUNNER_BYTES,
        "sha256": V1_RUNNER_SHA256,
    },
    "v1_diagnostic_protocol_contract": {
        "commit": V1_IMPLEMENTATION_COMMIT,
        "role": "v1_implementation_freeze",
        "path": V1_PROTOCOL_CONTRACT_PATH,
        "bytes": V1_PROTOCOL_CONTRACT_BYTES,
        "sha256": V1_PROTOCOL_CONTRACT_SHA256,
    },
    "v1_diagnostic_result_contract": {
        "commit": V1_IMPLEMENTATION_COMMIT,
        "role": "v1_implementation_freeze",
        "path": V1_RESULT_CONTRACT_PATH,
        "bytes": V1_RESULT_CONTRACT_BYTES,
        "sha256": V1_RESULT_CONTRACT_SHA256,
    },
    "v1_diagnostic_protocol_test": {
        "commit": V1_IMPLEMENTATION_COMMIT,
        "role": "v1_implementation_freeze",
        "path": V1_PROTOCOL_TEST_PATH,
        "bytes": V1_PROTOCOL_TEST_BYTES,
        "sha256": V1_PROTOCOL_TEST_SHA256,
    },
    "v1_diagnostic_result_test": {
        "commit": V1_IMPLEMENTATION_COMMIT,
        "role": "v1_implementation_freeze",
        "path": V1_RESULT_TEST_PATH,
        "bytes": V1_RESULT_TEST_BYTES,
        "sha256": V1_RESULT_TEST_SHA256,
    },
    "v1_execution_authority": {
        "commit": V1_AUTHORITY_COMMIT,
        "role": "v1_execution_authority_introduction",
        "path": v1_result_contract.EXECUTION_AUTHORITY_PATH,
        "bytes": V1_AUTHORITY_BYTES,
        "sha256": V1_AUTHORITY_SHA256,
    },
    "v1_invocation_closeout": {
        "commit": V1_CLOSEOUT_COMMIT,
        "role": "v1_invocation_closeout",
        "path": v1_closeout.CLOSEOUT_PATH,
        "bytes": V1_CLOSEOUT_BYTES,
        "sha256": V1_CLOSEOUT_SHA256,
    },
    "v1_invocation_closeout_contract": {
        "commit": V1_CLOSEOUT_COMMIT,
        "role": "v1_invocation_closeout_contract",
        "path": V1_CLOSEOUT_CONTRACT_PATH,
        "bytes": V1_CLOSEOUT_CONTRACT_BYTES,
        "sha256": V1_CLOSEOUT_CONTRACT_SHA256,
    },
    "v1_recovery_io": {
        "commit": V1_IMPLEMENTATION_COMMIT,
        "role": "v1_implementation_dependency_snapshot",
        "path": v1_closeout.RECOVERY_IO_PATH,
        "bytes": RECOVERY_IO_BYTES,
        "sha256": RECOVERY_IO_SHA256,
    },
}

PROTOCOL_SOURCE_PATHS = {
    "diagnostic_protocol_v2_builder": (
        "scripts/prepare_mm005_browser_research_model_evaluation_generation_"
        "failure_diagnostic_protocol_v2.py"
    ),
    "diagnostic_protocol_v2_contract": (
        "src/fullcycle_bridge/mm005_browser_research_model_evaluation_"
        "generation_failure_diagnostic_protocol_v2.py"
    ),
}

PROTOCOL_SLICE_PATHS = frozenset(
    {
        "AI_Infra_LLM_Agent_待做任务清单.md",
        "PROJECT_STATUS.md",
        "README.md",
        PREREGISTRATION_PATH,
        (
            "docs/MM-005-browser-research-model-evaluation-generation-failure-"
            "diagnostic-protocol-v2.md"
        ),
        "docs/repository-ci-lfs-maintenance-v1.md",
        "docs/README.md",
        PROTOCOL_SOURCE_PATHS["diagnostic_protocol_v2_builder"],
        "scripts/validate_offline.py",
        PROTOCOL_SOURCE_PATHS["diagnostic_protocol_v2_contract"],
        (
            "tests/test_mm005_browser_research_model_evaluation_generation_"
            "failure_diagnostic_protocol_v2.py"
        ),
    }
)

IMMUTABLE_V1_SUBTREE_NAMES = (
    "decision_rubric",
    "diagnostic_checkpoint_contract",
    "evidence_boundary",
    "record_control_registry",
    "resource_contract",
    "terminal_contract",
)

REQUIRED_GATES = (
    "maintenance_closeout_lineage_integrity",
    "v1_exhausted_invocation_closeout_integrity",
    "new_experiment_run_and_output_identity",
    "immutable_scientific_contract_equality",
    "missing_output_parent_is_valid_for_plan_check_and_freeze",
    "future_output_parent_preparation_is_closed_and_ordered",
    "future_implementation_real_filesystem_regression_required",
    "zero_execution_and_zero_retry_at_protocol_freeze",
    "separate_implementation_then_authority_then_execution",
    "runtime_authority_preserved",
    "fail_closed_claims",
)


class MM005GenerationFailureDiagnosticProtocolV2Error(ValueError):
    """Stable fail-closed error for v2 diagnostic-protocol drift."""

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
        raise MM005GenerationFailureDiagnosticProtocolV2Error(
            "JSON_INVALID", location
        ) from exc
    if not isinstance(value, dict):
        _fail("JSON_OBJECT_REQUIRED", location)
    return value


def expected_preregistration(
    *,
    lineage_current_payloads: Mapping[str, bytes],
    lineage_blob_payloads: Mapping[str, bytes],
    source_payloads: Mapping[str, bytes],
    v1_expected_preregistration: Mapping[str, Any],
    planned_output_absent: bool,
    planned_lifecycle_absent: bool,
) -> dict[str, Any]:
    """Build the exact model-free new-identity protocol."""

    if planned_output_absent is not True:
        _fail("PLANNED_OUTPUT_PRESENT_AT_FREEZE", "$.freeze_preconditions")
    if planned_lifecycle_absent is not True:
        _fail("PLANNED_LIFECYCLE_PRESENT_AT_FREEZE", "$.freeze_preconditions")
    lineage, v1_preregistration = _validated_lineage(
        lineage_current_payloads=lineage_current_payloads,
        lineage_blob_payloads=lineage_blob_payloads,
        source_payloads=source_payloads,
        v1_expected_preregistration=v1_expected_preregistration,
    )
    identity = _validated_identity_separation()
    immutable_subtrees = {
        name: _mapping(v1_preregistration.get(name), f"$.v1_protocol.{name}")
        for name in IMMUTABLE_V1_SUBTREE_NAMES
    }
    subtree_digests = {
        name: sha256_bytes(artifact_json_bytes(dict(value)))
        for name, value in immutable_subtrees.items()
    }
    checkpoints = immutable_subtrees["diagnostic_checkpoint_contract"]
    resource = immutable_subtrees["resource_contract"]
    terminal = immutable_subtrees["terminal_contract"]
    rubric = immutable_subtrees["decision_rubric"]
    registry = immutable_subtrees["record_control_registry"]
    scientific_inputs = _mapping(
        resource.get("scientific_inputs"),
        "$.v1_protocol.resource_contract.scientific_inputs",
    )
    success_grammar = _mapping(
        terminal.get("success_grammar"),
        "$.v1_protocol.terminal_contract.success_grammar",
    )
    session_events = _string_sequence(
        success_grammar.get("session_lifecycle_events"),
        "$.v1_protocol.terminal_contract.success_grammar.session_lifecycle_events",
    )
    checkpoint_count = checkpoints.get("full_success_durable_substage_event_count")
    if type(checkpoint_count) is not int:
        _fail("CHECKPOINT_COUNT_INVALID", "$.immutable_scientific_contract")
    success_frame_count = len(session_events) + checkpoint_count + 1

    return {
        "mm005_browser_research_generation_failure_diagnostic_protocol_version": (
            PROTOCOL_VERSION
        ),
        "gate_id": GATE_ID,
        "freeze_status": "frozen",
        "decision": "outcome_neutral_new_identity_output_parent_repair_protocol",
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
            "artifact_names": {
                "attempt_owner": "attempt-owner.json",
                "progress": "progress.json",
                "success_result": "diagnostic-result.json",
                "failure": "diagnostic-failure.json",
            },
        },
        "source_lineage": lineage,
        "freeze_preconditions": {
            "maintenance_merge_is_ancestor": True,
            "linear_v1_publication_chain_verified": True,
            "all_bound_payloads_match_binding_commit_blobs": True,
            "v1_invocation_budget_spent": True,
            "v1_diagnostic_attempt_unconsumed": True,
            "v1_retry_authorized": False,
            "v1_terminal_synthesis_authorized": False,
            "new_experiment_id": identity["new_experiment_id"],
            "new_run_id": identity["new_run_id"],
            "new_output_root": identity["new_output_root"],
            "planned_output_absent": planned_output_absent,
            "planned_lifecycle_absent": planned_lifecycle_absent,
            "work_root_presence_required_for_plan_check_or_freeze": False,
            "output_parent_presence_required_for_plan_check_or_freeze": False,
            "plan_check_and_freeze_create_output_parent": False,
            "formal_diagnostic_invocations": 0,
            "diagnostic_attempts_consumed": 0,
            "model_processor_pil_torch_or_cuda_used": False,
            "browser_or_network_used": False,
        },
        "identity_separation": identity,
        "immutable_scientific_contract": {
            "source_gate_id": v1_protocol.GATE_ID,
            "source_protocol_sha256": V1_PROTOCOL_SHA256,
            "subtree_names": list(IMMUTABLE_V1_SUBTREE_NAMES),
            "subtree_sha256": subtree_digests,
            "subtrees": {
                name: dict(immutable_subtrees[name])
                for name in IMMUTABLE_V1_SUBTREE_NAMES
            },
            "semantic_equality_required": True,
            "record_count": registry.get("record_count"),
            "record_registry_bytes": RECORD_REGISTRY_BYTES,
            "record_registry_sha256": RECORD_REGISTRY_SHA256,
            "required_environment_field_count": len(
                v1_protocol.OBSERVED_ENVIRONMENT_FIELDS
            ),
            "required_environment_fields": list(
                v1_protocol.OBSERVED_ENVIRONMENT_FIELDS
            ),
            "diagnostic_substage_count": len(v1_protocol.DIAGNOSTIC_SUBSTAGES),
            "diagnostic_substages": list(v1_protocol.DIAGNOSTIC_SUBSTAGES),
            "durable_substage_checkpoint_count": checkpoint_count,
            "success_frame_count": success_frame_count,
            "failure_scopes": terminal.get("failure_scopes"),
            "allowed_outcomes": rubric.get("allowed_outcomes"),
            "seed": scientific_inputs.get("seed"),
            "resource_caps": resource.get("resource_caps"),
            "no_new_scientific_variable": True,
        },
        "execution_protocol": {
            "implementation_frozen_by_this_protocol": False,
            "execution_authority_frozen_by_this_protocol": False,
            "diagnostic_execution_authorized": False,
            "formal_invocation_budget": 1,
            "formal_invocation_budget_spent": 0,
            "retry_budget": 0,
            "per_record_attempt_budget": 1,
            "v1_command_path_identity_or_output_reuse": False,
            "original_v2_output_reuse": False,
            "network": False,
            "live_browser": False,
            "capture_real_content": False,
            "training_backward_optimizer_or_adapter_write": False,
        },
        "output_parent_preparation_contract": {
            "scope": "future_execution_v2_only",
            "mutable_during_plan_check_or_protocol_freeze": False,
            "mutation_preconditions": [
                "published_execution_authority_v2",
                "clean_aligned_master_head",
                "exact_protocol_implementation_and_authority_lineage",
                "unclaimed_output_topology",
            ],
            "required_existing_directories": [
                {
                    "path": "repository_root",
                    "must_exist": True,
                    "ordinary_directory": True,
                    "symlink_or_reparse_forbidden": True,
                },
                {
                    "path": WORK_ROOT_PATH,
                    "must_exist": True,
                    "ordinary_directory": True,
                    "symlink_or_reparse_forbidden": True,
                },
            ],
            "initial_output_parent_state": {
                "path": OUTPUT_PARENT_PATH,
                "must_be_absent": True,
                "collision_forbidden": True,
            },
            "ordered_steps": [
                {
                    "index": 0,
                    "operation": "construct_and_verify_directory_tree_guard",
                    "guard_root": "repository_root",
                    "guard_target": WORK_ROOT_PATH,
                    "mutates_filesystem": False,
                },
                {
                    "index": 1,
                    "operation": "exclusive_single_directory_create",
                    "primitive": "os.mkdir",
                    "path": OUTPUT_PARENT_PATH,
                    "parents_created": False,
                    "exist_ok": False,
                    "mutates_filesystem": True,
                },
                {
                    "index": 2,
                    "operation": (
                        "revalidate_authority_lineage_remaining_topology_and_ancestry"
                    ),
                    "published_execution_authority_v2_revalidated": True,
                    "clean_aligned_head_revalidated": True,
                    "exact_lineage_revalidated": True,
                    "planned_output_root_lifecycle_owner_and_progress_unclaimed": True,
                    "created_parent_excluded_from_precreate_absence_predicate": True,
                    "windows_casefold_identity": True,
                    "symlink_or_reparse_forbidden": True,
                    "mutates_filesystem": False,
                },
                {
                    "index": 3,
                    "operation": "construct_and_verify_directory_tree_guard",
                    "guard_root": "repository_root",
                    "guard_target": OUTPUT_PARENT_PATH,
                    "mutates_filesystem": False,
                },
                {
                    "index": 4,
                    "operation": "enter_lifecycle_lease",
                    "path": LIFECYCLE_LEASE_PATH,
                    "mutates_filesystem": True,
                },
                {
                    "index": 5,
                    "operation": "atomic_attempt_owner_and_genesis_claim",
                    "owner_path": ATTEMPT_OWNER_PATH,
                    "progress_path": PROGRESS_PATH,
                    "genesis_event": "attempt_claimed",
                    "mutates_filesystem": True,
                },
                {
                    "index": 6,
                    "operation": "enter_first_heavy_dependency_boundary",
                    "mutates_filesystem": False,
                },
            ],
            "directory_guard_verified_before_lifecycle": True,
            "authority_lineage_and_remaining_unclaimed_topology_revalidated_after_create_before_lifecycle": (
                True
            ),
            "lifecycle_entered_before_owner_and_genesis_claim": True,
            "parent_creation_is_attempt_claim": False,
            "parent_creation_is_formal_telemetry": False,
            "collision_unsafe_identity_drift_or_guard_failure_precedes_lifecycle": (
                True
            ),
            "collision_unsafe_identity_drift_or_guard_failure_precedes_claim": True,
            "collision_unsafe_identity_drift_or_guard_failure_precedes_heavy_import": (
                True
            ),
            "collision_unsafe_identity_drift_or_guard_failure_precedes_model_or_cuda": (
                True
            ),
            "pre_owner_failure_terminal_synthesis_authorized": False,
            "pre_owner_failure_scope": None,
            "pre_owner_failure_outcome": None,
            "pre_owner_failure_spends_formal_invocation_budget": True,
            "pre_owner_failure_retry_authorized": False,
            "same_privilege_toctou_eliminated": False,
            "same_privilege_toctou_limit": (
                "identity guards detect observed replacement but cannot exclude every "
                "same-privilege mutation between checks"
            ),
        },
        "implementation_v2_regression_contract": {
            "mandatory": True,
            "scope": "model_free_temporary_filesystem_only",
            "real_temporary_filesystem": True,
            "initial_topology": {
                "repository_root_exists": True,
                "work_root_exists": True,
                "work_root_is_ordinary_non_reparse_directory": True,
                "output_parent_absent": True,
                "output_root_absent": True,
                "lifecycle_root_absent": True,
            },
            "output_parent_helper_mocked": False,
            "directory_tree_guard_mocked": False,
            "exercise_execute_path": True,
            "must_reach": [
                "output_parent_exclusive_create",
                "output_parent_guard_verification",
                "lifecycle_lease",
                "attempt_owner",
                "attempt_claimed_genesis",
            ],
            "controlled_exception_boundary": "first_heavy_dependency_boundary",
            "model_import_entered": False,
            "model_load_entered": False,
            "cuda_entered": False,
            "network_entered": False,
            "expected_failure_scope": "pre_record_lifecycle",
            "establishes_formal_execution_authority": False,
            "consumes_formal_invocation_budget": False,
        },
        "formal_gate": {
            "required_gates": list(REQUIRED_GATES),
            "protocol_freeze_is_not_diagnostic_execution": True,
            "protocol_freeze_is_not_formal_model_measurement": True,
            "quality_threshold_gate": False,
        },
        "authority_contract": {
            "protocol_freeze_authorized": True,
            "diagnostic_implementation_v2_freeze_authorized_after_clean_merge": True,
            "diagnostic_execution_authority_v2_freeze_authorized_by_this_gate": False,
            "diagnostic_execution_authorized": False,
            "processor_execution_authorized": False,
            "model_or_cuda_execution_authorized": False,
            "live_browser_or_network_authorized": False,
            "capture_authorized": False,
            "training_authorized": False,
            "v1_retry_authorized": False,
            "v2_retry_authorized": False,
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
            "diagnostic_protocol_v2_frozen": True,
            "v1_invocation_budget_spent": True,
            "v1_diagnostic_attempt_consumed": False,
            "v1_diagnostic_executed": False,
            "v1_terminal_published": False,
            "v2_diagnostic_attempt_consumed": False,
            "v2_diagnostic_executed": False,
            "v2_diagnostic_execution_authorized": False,
            "formal_measurement_complete": False,
            "historical_runtime_health_established": False,
            "failed_runtime_substage_isolated": False,
            "runtime_root_cause_established": False,
            "remediation_delta_established": False,
            "recovery_v3_justified": False,
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
            "action": "freeze_diagnostic_implementation_v2_without_execution",
            "eligible_to_start_after_clean_protocol_merge": True,
            "implementation_freeze_only": True,
            "mandatory_regression_contract": True,
            "execution_authority_v2_deferred": True,
            "diagnostic_execution_authorized": False,
            "v1_retry_authorized": False,
            "v2_retry_authorized": False,
            "recovery_v3_authorized": False,
        },
        "publication": {
            "slice_paths": sorted(PROTOCOL_SLICE_PATHS),
            "slice_path_count": len(PROTOCOL_SLICE_PATHS),
            "v1_runner_modified": False,
            "v1_recovery_io_modified": False,
            "runner_result_or_authority_added": False,
            "runtime_output_added_to_git": False,
            "model_or_cuda_execution_by_protocol": False,
        },
        "next_gate": IMPLEMENTATION_GATE_ID,
        "runtime_eligible": False,
    }


def validate_preregistration(value: Mapping[str, Any], **inputs: Any) -> dict[str, Any]:
    expected = expected_preregistration(**inputs)
    if artifact_json_bytes(dict(value)) != artifact_json_bytes(expected):
        _fail("PREREGISTRATION_MISMATCH", "$.preregistration")
    return expected


def _validated_lineage(
    *,
    lineage_current_payloads: Mapping[str, bytes],
    lineage_blob_payloads: Mapping[str, bytes],
    source_payloads: Mapping[str, bytes],
    v1_expected_preregistration: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    expected_names = set(LINEAGE_BINDINGS)
    if set(lineage_current_payloads) != expected_names:
        _fail("LINEAGE_CURRENT_KEYS", "$.source_lineage")
    if set(lineage_blob_payloads) != expected_names:
        _fail("LINEAGE_BLOB_KEYS", "$.source_lineage")

    receipts: dict[str, dict[str, object]] = {}
    for name, binding in sorted(LINEAGE_BINDINGS.items()):
        current = lineage_current_payloads[name]
        blob = lineage_blob_payloads[name]
        expected_bytes = binding["bytes"]
        expected_sha256 = binding["sha256"]
        expected_role = binding["role"]
        if (
            not isinstance(current, bytes)
            or not isinstance(blob, bytes)
            or not isinstance(expected_role, str)
            or current != blob
            or len(blob) != expected_bytes
            or sha256_bytes(blob) != expected_sha256
        ):
            _fail("LINEAGE_PAYLOAD_MISMATCH", f"$.source_lineage.{name}")
        receipts[name] = {
            "binding_commit": binding["commit"],
            "binding_role": expected_role,
            "path": binding["path"],
            "bytes": expected_bytes,
            "sha256": expected_sha256,
            "current_bytes_equal_binding_commit_blob": True,
        }

    v1_payload = lineage_current_payloads["v1_diagnostic_protocol"]
    v1_value = parse_strict_json_bytes(v1_payload, location="$.v1_protocol")
    if (
        artifact_json_bytes(v1_value) != v1_payload
        or artifact_json_bytes(dict(v1_expected_preregistration)) != v1_payload
        or v1_value.get("gate_id") != v1_protocol.GATE_ID
        or v1_value.get("experiment_id") != v1_protocol.EXPERIMENT_ID
        or v1_value.get("run_id") != v1_protocol.RUN_ID
    ):
        _fail("V1_PROTOCOL_SEMANTIC_MISMATCH", "$.source_lineage.v1_protocol")

    closeout = v1_closeout.parse_and_validate_invocation_closeout(
        lineage_current_payloads["v1_invocation_closeout"],
        authority_payload=lineage_current_payloads["v1_execution_authority"],
        runner_payload=lineage_current_payloads["v1_diagnostic_runner"],
        recovery_io_payload=lineage_current_payloads["v1_recovery_io"],
    )
    invocation = _mapping(closeout.get("invocation"), "$.v1_closeout.invocation")
    grammar = _mapping(
        closeout.get("frozen_failure_grammar"), "$.v1_closeout.failure_grammar"
    )
    claims = _mapping(closeout.get("claims"), "$.v1_closeout.claims")
    outcome = _mapping(closeout.get("formal_outcome"), "$.v1_closeout.outcome")
    if (
        invocation.get("formal_invocation_budget_remaining") != 0
        or invocation.get("retry_budget") != 0
        or invocation.get("retries_observed") != 0
        or grammar.get("zero_owner_failure_representable") is not False
        or grammar.get("terminal_synthesis_authorized") is not False
        or claims.get("diagnostic_attempt_consumed") is not False
        or claims.get("diagnostic_executed") is not False
        or outcome.get("selected_outcome") is not None
    ):
        _fail("V1_CLOSEOUT_SEMANTIC_MISMATCH", "$.source_lineage.v1_closeout")

    static_result = parse_strict_json_bytes(
        lineage_current_payloads["published_static_result"],
        location="$.published_static_result",
    )
    static_decision = _mapping(
        static_result.get("decision"), "$.published_static_result.decision"
    )
    if (
        static_result.get("report_digest") != STATIC_RESULT_REPORT_DIGEST
        or static_decision.get("selected_outcome")
        != v1_protocol.PUBLISHED_RESULT_OUTCOME
    ):
        _fail("STATIC_RESULT_SEMANTIC_MISMATCH", "$.source_lineage.static_result")

    original = parse_strict_json_bytes(
        lineage_current_payloads["original_v2_preregistration"],
        location="$.original_v2_preregistration",
    )
    for name, expected_digest in v1_protocol.V2_BOUND_SUBTREE_SHA256.items():
        if sha256_bytes(artifact_json_bytes(original.get(name))) != expected_digest:
            _fail(
                "ORIGINAL_V2_SUBTREE_MISMATCH",
                f"$.source_lineage.original_v2_preregistration.{name}",
            )

    if set(source_payloads) != set(PROTOCOL_SOURCE_PATHS):
        _fail("PROTOCOL_SOURCE_KEYS", "$.source_lineage.protocol_sources")
    protocol_sources: dict[str, dict[str, object]] = {}
    for name, path in sorted(PROTOCOL_SOURCE_PATHS.items()):
        payload = source_payloads[name]
        if not isinstance(payload, bytes):
            _fail("PROTOCOL_SOURCE_BYTES", f"$.source_lineage.{name}")
        protocol_sources[name] = _receipt(path, payload)

    commit_chain = [
        {
            "commit": child,
            "parent": parent,
            "unique_first_parent": True,
        }
        for child, parent in COMMIT_PARENT_CHAIN.items()
    ]
    lineage = {
        "original_v2_preregistration": {
            "path": v1_protocol.V2_PREREGISTRATION_PATH,
            "bytes": ORIGINAL_V2_PREREGISTRATION_BYTES,
            "sha256": ORIGINAL_V2_PREREGISTRATION_SHA256,
            "introduction_commit": ORIGINAL_V2_INTRODUCTION_COMMIT,
            "unique_first_parent_introduction": True,
            "static_result_binding_commit": STATIC_RESULT_COMMIT,
            "protocol_v2_base_commit": MAINTENANCE_MERGE_COMMIT,
            "introduction_blob_equals_static_result_binding_blob": True,
            "static_result_binding_blob_equals_protocol_v2_base_blob": True,
            "current_bytes_equal_protocol_v2_base_blob": True,
        },
        "static_result_publication_commit": STATIC_RESULT_COMMIT,
        "v1_protocol_merge_commit": V1_PROTOCOL_COMMIT,
        "v1_implementation_freeze_commit": V1_IMPLEMENTATION_COMMIT,
        "v1_execution_authority_commit": V1_AUTHORITY_COMMIT,
        "v1_invocation_closeout_commit": V1_CLOSEOUT_COMMIT,
        "maintenance_merge_commit": MAINTENANCE_MERGE_COMMIT,
        "commit_parent_chain": commit_chain,
        "commit_ancestor_relations": [
            {"ancestor": ancestor, "descendant": descendant}
            for ancestor, descendant in COMMIT_ANCESTOR_RELATIONS
        ],
        "bound_artifacts": receipts,
        "protocol_sources": protocol_sources,
        "static_result_report_digest": STATIC_RESULT_REPORT_DIGEST,
        "record_registry": {
            "bytes": RECORD_REGISTRY_BYTES,
            "sha256": RECORD_REGISTRY_SHA256,
        },
        "v1_invocation_is_exhausted_and_not_retryable": True,
        "v2_is_additive_new_identity": True,
    }
    return lineage, v1_value


def _validated_identity_separation() -> dict[str, Any]:
    predecessor_experiment_ids = (
        original_v2.EXPERIMENT_ID,
        v1_protocol.EXPERIMENT_ID,
    )
    predecessor_run_ids = (original_v2.RUN_ID, v1_protocol.RUN_ID)
    predecessor_roots = PREDECESSOR_RUNTIME_ROOTS
    if EXPERIMENT_ID.casefold() in {
        value.casefold() for value in predecessor_experiment_ids
    }:
        _fail("EXPERIMENT_ID_REUSED", "$.identity_separation")
    if RUN_ID.casefold() in {value.casefold() for value in predecessor_run_ids}:
        _fail("RUN_ID_REUSED", "$.identity_separation")

    new_roots = (RUN_OUTPUT_ROOT, LIFECYCLE_LEASE_ROOT)
    derived_paths = (
        RUN_OUTPUT_ROOT,
        ATTEMPT_OWNER_PATH,
        PROGRESS_PATH,
        SUCCESS_RESULT_PATH,
        FAILURE_PATH,
        LIFECYCLE_LEASE_ROOT,
        LIFECYCLE_LEASE_PATH,
        OUTPUT_PARENT_PATH,
        WORK_ROOT_PATH,
    )
    for path in (*derived_paths, *predecessor_roots):
        _windows_path_parts(path)
    if _paths_overlap_windows(*new_roots):
        _fail("NEW_OUTPUT_AND_LIFECYCLE_OVERLAP", "$.identity_separation")
    for new_path in new_roots:
        for predecessor in predecessor_roots:
            if _paths_overlap_windows(new_path, predecessor):
                _fail("PREDECESSOR_PATH_OVERLAP", "$.identity_separation")

    expected_artifacts = {
        "attempt_owner": (ATTEMPT_OWNER_PATH, f"{RUN_OUTPUT_ROOT}/attempt-owner.json"),
        "progress": (PROGRESS_PATH, f"{RUN_OUTPUT_ROOT}/progress.json"),
        "success_result": (
            SUCCESS_RESULT_PATH,
            f"{RUN_OUTPUT_ROOT}/diagnostic-result.json",
        ),
        "failure": (FAILURE_PATH, f"{RUN_OUTPUT_ROOT}/diagnostic-failure.json"),
        "lifecycle_root": (
            LIFECYCLE_LEASE_ROOT,
            f"{RUN_OUTPUT_ROOT}.lifecycle",
        ),
        "lifecycle_lease": (
            LIFECYCLE_LEASE_PATH,
            f"{RUN_OUTPUT_ROOT}.lifecycle/lease",
        ),
    }
    if any(actual != expected for actual, expected in expected_artifacts.values()):
        _fail("DERIVED_ARTIFACT_NAME_MISMATCH", "$.identity_separation")
    if (
        PurePosixPath(RUN_OUTPUT_ROOT).parent.as_posix() != OUTPUT_PARENT_PATH
        or PurePosixPath(OUTPUT_PARENT_PATH).parent.as_posix() != WORK_ROOT_PATH
    ):
        _fail("OUTPUT_PARENT_IDENTITY_MISMATCH", "$.identity_separation")

    v1_command_digest = sha256_bytes(
        artifact_json_bytes(list(v1_closeout.FORMAL_COMMAND))
    )
    return {
        "new_experiment_id": True,
        "new_run_id": True,
        "new_output_root": True,
        "new_output_and_lifecycle_roots_do_not_overlap": True,
        "windows_casefold_and_ancestor_unique_from_original_v2_and_v1": True,
        "fixed_artifact_names": True,
        "v1_formal_command_sha256": v1_command_digest,
        "v1_formal_command_repeated": False,
        "v1_path_identity_or_output_reused": False,
        "predecessor_experiment_ids": list(predecessor_experiment_ids),
        "predecessor_run_ids": list(predecessor_run_ids),
        "predecessor_runtime_roots": list(predecessor_roots),
    }


def _paths_overlap_windows(left: str, right: str) -> bool:
    left_parts = _windows_path_parts(left)
    right_parts = _windows_path_parts(right)
    length = min(len(left_parts), len(right_parts))
    return left_parts[:length] == right_parts[:length]


def _windows_path_parts(value: str) -> tuple[str, ...]:
    path = PurePosixPath(value)
    if (
        not value
        or "\\" in value
        or ":" in value
        or path.is_absolute()
        or path.as_posix() != value
        or "." in path.parts
        or ".." in path.parts
    ):
        _fail("PATH_IDENTITY_INVALID", "$.identity_separation")
    normalized = tuple(part.rstrip(" .").casefold() for part in path.parts)
    if any(not part for part in normalized):
        _fail("PATH_IDENTITY_INVALID", "$.identity_separation")
    return normalized


def _receipt(path: str, payload: bytes) -> dict[str, object]:
    return {"path": path, "bytes": len(payload), "sha256": sha256_bytes(payload)}


def _mapping(value: object, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail("OBJECT_REQUIRED", location)
    return cast(Mapping[str, Any], value)


def _string_sequence(value: object, location: str) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        _fail("STRING_ARRAY_REQUIRED", location)
    items = list(value)
    if any(type(item) is not str for item in items):
        _fail("STRING_ARRAY_REQUIRED", location)
    return cast(list[str], items)


def _unique_object(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail("DUPLICATE_JSON_KEY", f"$.{key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> NoReturn:
    _fail("NONFINITE_JSON_NUMBER", f"$.{value}")


def _fail(code: str, location: str = "$") -> NoReturn:
    raise MM005GenerationFailureDiagnosticProtocolV2Error(code, location)


__all__ = [
    "ATTEMPT_OWNER_PATH",
    "AUTHORITY_GATE_ID",
    "COMMIT_ANCESTOR_RELATIONS",
    "COMMIT_PARENT_CHAIN",
    "EXPERIMENT_ID",
    "FAILURE_PATH",
    "GATE_ID",
    "IMPLEMENTATION_GATE_ID",
    "IMMUTABLE_V1_SUBTREE_NAMES",
    "LIFECYCLE_LEASE_PATH",
    "LIFECYCLE_LEASE_ROOT",
    "LINEAGE_BINDINGS",
    "MAINTENANCE_MERGE_COMMIT",
    "MM005GenerationFailureDiagnosticProtocolV2Error",
    "OUTPUT_PARENT_PATH",
    "ORIGINAL_V2_INTRODUCTION_COMMIT",
    "PREDECESSOR_RUNTIME_ROOTS",
    "PREREGISTRATION_PATH",
    "PROGRESS_PATH",
    "PROTOCOL_SLICE_PATHS",
    "PROTOCOL_SOURCE_PATHS",
    "RUN_ID",
    "RUN_OUTPUT_ROOT",
    "SUCCESS_RESULT_PATH",
    "V1_CLOSEOUT_COMMIT",
    "V1_IMPLEMENTATION_COMMIT",
    "V1_PROTOCOL_COMMIT",
    "WORK_ROOT_PATH",
    "artifact_json_bytes",
    "expected_preregistration",
    "parse_strict_json_bytes",
    "sha256_bytes",
    "validate_preregistration",
]
