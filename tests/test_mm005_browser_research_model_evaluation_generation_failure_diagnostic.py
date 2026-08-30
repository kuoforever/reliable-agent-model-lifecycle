from __future__ import annotations

import ast
import copy
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

sys.path.insert(0, str(SRC))
sys.path.insert(0, str(ROOT))

from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_model_evaluation as v1,
)
from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_model_evaluation_generation_failure_investigation as investigation,
)
from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_model_evaluation_generation_failure_diagnostic as contract,
)
from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_model_evaluation_protocol_v2 as v2,
)
from scripts import (  # noqa: E402
    prepare_mm005_browser_research_model_evaluation_generation_failure_diagnostic_protocol_v1 as builder,
)

PROTOCOL_PATH = ROOT / contract.PREREGISTRATION_PATH


class MM005BrowserResearchGenerationFailureDiagnosticProtocolV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.protocol_payload = PROTOCOL_PATH.read_bytes()
        cls.protocol = contract.parse_strict_json_bytes(
            cls.protocol_payload, location="$.diagnostic_protocol"
        )
        cls.inputs = builder.protocol_inputs()

    def _validation_inputs(self) -> dict[str, object]:
        return copy.deepcopy(self.inputs)

    def test_protocol_recomputes_exactly_and_builder_check_passes(self) -> None:
        recomputed = contract.expected_preregistration(**self._validation_inputs())
        self.assertEqual(
            contract.artifact_json_bytes(recomputed), self.protocol_payload
        )
        self.assertEqual(
            contract.validate_preregistration(
                self.protocol, **self._validation_inputs()
            ),
            recomputed,
        )
        self.assertEqual(builder.main(["--check"]), 0)

    def test_published_result_lineage_and_semantics_are_exact(self) -> None:
        head_commit, current_payloads, blob_payloads = (
            builder._validate_published_result_lineage()
        )
        published_blob = blob_payloads[contract.PUBLISHED_RESULT_PATH]
        self.assertEqual(current_payloads, blob_payloads)
        self.assertEqual(head_commit, builder._git_head_commit())
        self.assertEqual(len(published_blob), contract.PUBLISHED_RESULT_BYTES)
        self.assertEqual(
            contract.sha256_bytes(published_blob), contract.PUBLISHED_RESULT_SHA256
        )
        lineage = self.protocol["source_lineage"]
        self.assertEqual(
            lineage["result_publication_commit"], contract.RESULT_PUBLICATION_COMMIT
        )
        self.assertEqual(
            lineage["published_static_result"]["report_digest"],
            contract.PUBLISHED_RESULT_REPORT_DIGEST,
        )
        self.assertEqual(
            lineage["published_static_result"]["selected_outcome"],
            "static_pipeline_reconstructed_without_contract_violation",
        )
        self.assertEqual(
            lineage["investigation_implementation_freeze_commit"],
            "c2b04f68dfbb0f96423ecf83a8d73529fdf9d055",
        )
        self.assertEqual(
            lineage["v2_preregistration"],
            {
                "bound_subtree_sha256": dict(contract.V2_BOUND_SUBTREE_SHA256),
                "bytes": contract.V2_PREREGISTRATION_BYTES,
                "canonical_json": True,
                "path": contract.V2_PREREGISTRATION_PATH,
                "scientific_inputs_projected_from_frozen_payload": True,
                "sha256": contract.V2_PREREGISTRATION_SHA256,
                "tracked_bytes_equal_result_publication_commit_blob": True,
            },
        )

    def test_result_payload_tamper_and_reseal_are_rejected(self) -> None:
        changed = self._validation_inputs()
        current = changed["publication_current_payloads"]
        self.assertIsInstance(current, dict)
        assert isinstance(current, dict)
        payload = current[contract.PUBLISHED_RESULT_PATH]
        self.assertIsInstance(payload, bytes)
        assert isinstance(payload, bytes)
        current[contract.PUBLISHED_RESULT_PATH] = payload[:-1] + b" "
        with self.assertRaises(contract.MM005GenerationFailureDiagnosticProtocolError):
            contract.expected_preregistration(**changed)

        changed = self._validation_inputs()
        current = changed["publication_current_payloads"]
        self.assertIsInstance(current, dict)
        assert isinstance(current, dict)
        result = contract.parse_strict_json_bytes(
            payload, location="$.published_result"
        )
        result["report_digest"] = "sha256:" + "0" * 64
        resealed = contract.artifact_json_bytes(result)
        current[contract.PUBLISHED_RESULT_PATH] = resealed
        blobs = changed["publication_blob_payloads"]
        self.assertIsInstance(blobs, dict)
        assert isinstance(blobs, dict)
        blobs[contract.PUBLISHED_RESULT_PATH] = resealed
        with self.assertRaises(contract.MM005GenerationFailureDiagnosticProtocolError):
            contract.expected_preregistration(**changed)

    def test_v2_preregistration_and_publication_source_closure_are_exact(self) -> None:
        for mutation in ("v2_current", "v2_resealed", "missing", "extra"):
            changed = self._validation_inputs()
            current = changed["publication_current_payloads"]
            blobs = changed["publication_blob_payloads"]
            self.assertIsInstance(current, dict)
            self.assertIsInstance(blobs, dict)
            assert isinstance(current, dict)
            assert isinstance(blobs, dict)
            if mutation == "v2_current":
                current[contract.V2_PREREGISTRATION_PATH] += b" "
            elif mutation == "v2_resealed":
                tampered = current[contract.V2_PREREGISTRATION_PATH][:-1] + b" \n"
                current[contract.V2_PREREGISTRATION_PATH] = tampered
                blobs[contract.V2_PREREGISTRATION_PATH] = tampered
            elif mutation == "missing":
                current.pop(contract.V2_PREREGISTRATION_PATH)
            else:
                current["extra/path"] = b"x"
                blobs["extra/path"] = b"x"
            with (
                self.subTest(mutation=mutation),
                self.assertRaises(
                    contract.MM005GenerationFailureDiagnosticProtocolError
                ),
            ):
                contract.expected_preregistration(**changed)

        lineage = self.protocol["source_lineage"]
        self.assertEqual(
            set(lineage["result_publication_bound_receipts"]),
            set(contract.RESULT_PUBLICATION_BOUND_PATHS),
        )
        self.assertEqual(len(contract.RESULT_PUBLICATION_BOUND_PATHS), 20)

    def test_new_identity_and_output_do_not_reuse_any_predecessor(self) -> None:
        outputs = self.protocol["outputs"]
        self.assertNotEqual(self.protocol["experiment_id"], v2.EXPERIMENT_ID)
        self.assertNotEqual(self.protocol["experiment_id"], v1.EXPERIMENT_ID)
        self.assertNotEqual(
            self.protocol["experiment_id"], investigation.INVESTIGATION_ID
        )
        self.assertNotEqual(self.protocol["run_id"], v2.RUN_ID)
        self.assertNotEqual(self.protocol["run_id"], v1.RUN_ID)
        self.assertNotEqual(outputs["output_root"], v2.RUN_OUTPUT_ROOT)
        self.assertFalse(outputs["output_root"].startswith(v2.RUN_OUTPUT_ROOT + "/"))
        self.assertEqual(self.protocol["experiment_id"], contract.EXPERIMENT_ID)
        self.assertEqual(self.protocol["run_id"], contract.RUN_ID)
        self.assertTrue(self.protocol["freeze_preconditions"]["new_output_root"])
        separation = self.protocol["identity_separation"]
        self.assertEqual(
            separation["comparison"],
            "windows_case_insensitive_posix_path_identity_and_overlap",
        )
        self.assertTrue(separation["new_output_and_lease_roots_do_not_overlap"])

    def test_identity_reuse_case_variants_and_path_overlap_are_rejected(self) -> None:
        for field, reused in (
            ("EXPERIMENT_ID", v1.EXPERIMENT_ID),
            ("EXPERIMENT_ID", v2.EXPERIMENT_ID.upper()),
            ("EXPERIMENT_ID", investigation.INVESTIGATION_ID),
            ("RUN_ID", v1.RUN_ID),
            ("RUN_ID", v2.RUN_ID.upper()),
        ):
            with (
                self.subTest(field=field, reused=reused),
                mock.patch.object(contract, field, reused),
                self.assertRaises(
                    contract.MM005GenerationFailureDiagnosticProtocolError
                ),
            ):
                contract.expected_preregistration(**self._validation_inputs())

        for reused_root in (
            "work/evaluation-runs",
            v1.RUN_OUTPUT_ROOT.upper(),
            f"{v2.RUN_OUTPUT_ROOT}/nested",
            f"{v2.LIFECYCLE_LEASE_ROOT}/nested",
        ):
            replacements = {
                "RUN_OUTPUT_ROOT": reused_root,
                "ATTEMPT_OWNER_PATH": f"{reused_root}/attempt-owner.json",
                "PROGRESS_PATH": f"{reused_root}/progress.json",
                "SUCCESS_RESULT_PATH": f"{reused_root}/diagnostic-result.json",
                "FAILURE_PATH": f"{reused_root}/diagnostic-failure.json",
                "LIFECYCLE_LEASE_ROOT": f"{reused_root}.lifecycle",
                "LIFECYCLE_LEASE_PATH": f"{reused_root}.lifecycle/lease",
            }
            with (
                self.subTest(reused_root=reused_root),
                mock.patch.multiple(contract, **replacements),
                self.assertRaises(
                    contract.MM005GenerationFailureDiagnosticProtocolError
                ),
            ):
                contract.expected_preregistration(**self._validation_inputs())

    def test_exact_seven_record_order_preserves_historical_target_position(
        self,
    ) -> None:
        registry = self.protocol["record_control_registry"]
        self.assertEqual(registry["record_count"], 7)
        self.assertEqual(
            registry["diagnostic_case_order"], list(contract.DIAGNOSTIC_CASE_ORDER)
        )
        self.assertEqual(
            registry["diagnostic_case_order"][:3],
            list(contract.COMPLETED_PREFIX_CONTROL_IDS),
        )
        self.assertEqual(
            registry["diagnostic_case_order"][3], contract.TARGET_RECORD_ID
        )
        self.assertEqual(
            registry["diagnostic_case_order"][4:],
            list(contract.SAME_SHAPE_CONTROL_IDS),
        )
        self.assertEqual(
            [item["diagnostic_index"] for item in registry["records"]],
            list(range(7)),
        )
        self.assertEqual(
            registry["registered_reference"],
            {
                "bytes": contract.REGISTERED_RECORD_REGISTRY_BYTES,
                "sha256": contract.REGISTERED_RECORD_REGISTRY_SHA256,
            },
        )

    def test_historical_and_diagnostic_substage_names_are_explicitly_mapped(
        self,
    ) -> None:
        boundary = self.protocol["evidence_boundary"]
        self.assertEqual(
            boundary["unresolved_runtime_substages"],
            list(contract.HISTORICAL_UNRESOLVED_SUBSTAGES),
        )
        self.assertEqual(
            boundary["historical_to_diagnostic_substage"],
            contract.HISTORICAL_TO_DIAGNOSTIC_SUBSTAGE,
        )
        self.assertTrue(
            boundary["checkpoint_observation_does_not_prove_async_error_origin"]
        )

    def test_all_eighteen_checkpoint_events_are_closed_ordered_pairs(self) -> None:
        checkpoints = self.protocol["diagnostic_checkpoint_contract"]
        self.assertEqual(checkpoints["per_record_durable_substage_event_count"], 18)
        self.assertEqual(
            checkpoints["durable_substage_events"],
            list(contract.DIAGNOSTIC_CHECKPOINTS),
        )
        self.assertEqual(len(checkpoints["checkpoint_pairs"]), 9)
        flattened: list[str] = []
        for index, pair in enumerate(checkpoints["checkpoint_pairs"]):
            self.assertEqual(pair["substage"], contract.DIAGNOSTIC_SUBSTAGES[index])
            flattened.extend((pair["started"], pair["completed"]))
        self.assertEqual(flattened, list(contract.DIAGNOSTIC_CHECKPOINTS))
        self.assertEqual(len(set(flattened)), 18)
        self.assertTrue(
            checkpoints["checkpoint_observation_does_not_prove_async_error_origin"]
        )
        self.assertFalse(
            checkpoints["failed_runtime_substage_isolated_at_protocol_freeze"]
        )

    def test_all_seven_records_bind_exact_18_event_identity_plans(self) -> None:
        checkpoints = self.protocol["diagnostic_checkpoint_contract"]
        plans = checkpoints["per_record_checkpoint_plans"]
        self.assertEqual(
            checkpoints["event_identity_fields"], list(contract.EVENT_IDENTITY_FIELDS)
        )
        self.assertEqual(len(plans), 7)
        self.assertEqual(checkpoints["full_success_record_count"], 7)
        self.assertEqual(checkpoints["full_success_durable_substage_event_count"], 126)
        self.assertEqual(checkpoints["maximum_durable_substage_event_count"], 126)
        flattened: list[dict[str, object]] = []
        for diagnostic_index, plan in enumerate(plans):
            record_id = contract.DIAGNOSTIC_CASE_ORDER[diagnostic_index]
            self.assertEqual(plan["record_id"], record_id)
            self.assertEqual(plan["diagnostic_index"], diagnostic_index)
            self.assertEqual(len(plan["durable_events"]), 18)
            for event_index, event in enumerate(plan["durable_events"]):
                self.assertEqual(
                    event,
                    {
                        "record_id": record_id,
                        "diagnostic_index": diagnostic_index,
                        "event": contract.DIAGNOSTIC_CHECKPOINTS[event_index],
                    },
                )
                flattened.append(event)
        self.assertEqual(len(flattened), 126)
        self.assertEqual(
            len(
                {
                    (item["record_id"], item["diagnostic_index"], item["event"])
                    for item in flattened
                }
            ),
            126,
        )

    def test_checkpoint_missing_extra_and_order_drift_are_rejected(self) -> None:
        for mutation in ("missing", "extra", "order"):
            changed = copy.deepcopy(self.protocol)
            events = changed["diagnostic_checkpoint_contract"][
                "durable_substage_events"
            ]
            if mutation == "missing":
                events.pop()
            elif mutation == "extra":
                events.append("unexpected_checkpoint")
            else:
                events[0], events[1] = events[1], events[0]
            with (
                self.subTest(mutation=mutation),
                self.assertRaises(
                    contract.MM005GenerationFailureDiagnosticProtocolError
                ),
            ):
                contract.validate_preregistration(changed, **self._validation_inputs())

        for mutation in ("record_missing", "record_identity", "cross_record_event"):
            changed = copy.deepcopy(self.protocol)
            plans = changed["diagnostic_checkpoint_contract"][
                "per_record_checkpoint_plans"
            ]
            if mutation == "record_missing":
                plans[0]["durable_events"].pop()
            elif mutation == "record_identity":
                plans[1]["record_id"] = plans[0]["record_id"]
            else:
                plans[1]["durable_events"][0]["record_id"] = plans[0]["record_id"]
            with (
                self.subTest(mutation=mutation),
                self.assertRaises(
                    contract.MM005GenerationFailureDiagnosticProtocolError
                ),
            ):
                contract.validate_preregistration(changed, **self._validation_inputs())

    def test_journal_lease_and_terminal_contracts_fail_closed(self) -> None:
        checkpoints = self.protocol["diagnostic_checkpoint_contract"]
        self.assertEqual(
            checkpoints["format"], "canonical_jsonl_append_only_sha256_chain"
        )
        self.assertTrue(checkpoints["single_writer_exclusive_lease"])
        self.assertTrue(checkpoints["lease_acquired_before_attempt_claim"])
        terminal = self.protocol["terminal_contract"]
        self.assertTrue(terminal["success_and_failure_are_mutually_exclusive"])
        self.assertTrue(
            terminal["failure_last_checkpoint_fields_are_scope_safe_and_nullable"]
        )
        self.assertEqual(terminal["failure_allowed_text_fields"], ["exception_type"])
        self.assertTrue(
            terminal["failure_message_traceback_absolute_path_or_secret_forbidden"]
        )
        self.assertFalse(terminal["result_and_failure_schema_frozen_by_this_protocol"])

    def test_terminal_grammar_distinguishes_lifecycle_transition_and_record_scope(
        self,
    ) -> None:
        terminal = self.protocol["terminal_contract"]
        pre_record = terminal["pre_record_lifecycle_failure_grammar"]
        self.assertEqual(
            pre_record["allowed_session_event_prefixes"],
            [
                list(contract.SESSION_LIFECYCLE_EVENTS[:length])
                for length in range(1, len(contract.SESSION_LIFECYCLE_EVENTS) + 1)
            ],
        )
        self.assertIsNone(pre_record["active_record_id"])
        self.assertIsNone(pre_record["last_started_checkpoint"])
        self.assertIsNone(pre_record["last_completed_checkpoint"])
        self.assertEqual(pre_record["allowed_outcome"], "diagnostic_inconclusive")

        transition = terminal["inter_record_transition_failure_grammar"]
        self.assertTrue(
            transition["completed_record_ids_must_be_strict_case_order_prefix"]
        )
        self.assertEqual(transition["active_record_events"], [])
        active = terminal["active_record_substage_failure_grammar"]
        self.assertTrue(
            active["active_record_events_must_be_nonempty_proper_prefix_of_plan"]
        )
        self.assertTrue(
            active["cross_record_or_session_checkpoint_reference_forbidden"]
        )
        self.assertTrue(
            active["last_started_checkpoint_is_latest_started_in_active_record"]
        )
        self.assertTrue(
            active[
                "last_completed_checkpoint_is_latest_completed_in_active_record_or_null"
            ]
        )
        terminalization = terminal["post_record_terminalization_failure_grammar"]
        self.assertEqual(
            terminal["failure_scopes"],
            [
                "pre_record_lifecycle",
                "inter_record_transition",
                "active_record_substage",
                "post_record_terminalization",
            ],
        )
        self.assertEqual(
            terminalization["completed_record_ids"],
            list(contract.DIAGNOSTIC_CASE_ORDER),
        )
        self.assertIsNone(terminalization["active_record_id"])
        self.assertIsNone(terminalization["active_record_diagnostic_index"])
        self.assertEqual(terminalization["active_record_events"], [])
        self.assertEqual(terminalization["durable_substage_event_count"], 126)
        final_events = contract.PER_RECORD_CHECKPOINT_PLANS[-1]["durable_events"]
        self.assertEqual(terminalization["last_started_checkpoint"], final_events[-2])
        self.assertEqual(terminalization["last_completed_checkpoint"], final_events[-1])
        self.assertTrue(terminalization["success_terminal_ready_absent"])
        self.assertEqual(terminalization["allowed_outcome"], "diagnostic_inconclusive")
        for grammar in (pre_record, transition, active, terminalization):
            self.assertEqual(grammar["terminal_event"], "failure_terminal_ready")
        success = terminal["success_grammar"]
        self.assertEqual(
            success["completed_record_ids"], list(contract.DIAGNOSTIC_CASE_ORDER)
        )
        self.assertEqual(success["durable_substage_event_count"], 126)

        for location, replacement in (
            (
                "pre_record_lifecycle_failure_grammar",
                {**pre_record, "last_completed_checkpoint": "cross_scope"},
            ),
            (
                "active_record_substage_failure_grammar",
                {
                    **active,
                    "cross_record_or_session_checkpoint_reference_forbidden": False,
                },
            ),
            (
                "post_record_terminalization_failure_grammar",
                {**terminalization, "durable_substage_event_count": 125},
            ),
            (
                "post_record_terminalization_failure_grammar",
                {
                    **terminalization,
                    "completed_record_ids": list(contract.DIAGNOSTIC_CASE_ORDER[:-1]),
                },
            ),
            (
                "post_record_terminalization_failure_grammar",
                {
                    **terminalization,
                    "active_record_id": contract.DIAGNOSTIC_CASE_ORDER[-1],
                },
            ),
            (
                "post_record_terminalization_failure_grammar",
                {
                    **terminalization,
                    "last_started_checkpoint": contract.PER_RECORD_CHECKPOINT_PLANS[0][
                        "durable_events"
                    ][-2],
                },
            ),
            (
                "post_record_terminalization_failure_grammar",
                {
                    **terminalization,
                    "last_completed_checkpoint": final_events[-2],
                },
            ),
            (
                "post_record_terminalization_failure_grammar",
                {**terminalization, "terminal_event": "success_terminal_ready"},
            ),
            ("success_grammar", {**success, "durable_substage_event_count": 125}),
        ):
            changed = copy.deepcopy(self.protocol)
            changed["terminal_contract"][location] = replacement
            with (
                self.subTest(location=location),
                self.assertRaises(
                    contract.MM005GenerationFailureDiagnosticProtocolError
                ),
            ):
                contract.validate_preregistration(changed, **self._validation_inputs())

    def test_resource_contract_is_independent_but_execution_preflight_is_deferred(
        self,
    ) -> None:
        resources = self.protocol["resource_contract"]
        scientific = resources["scientific_inputs"]
        self.assertTrue(resources["independent_from_v2_attempt"])
        self.assertEqual(scientific["model_id"], v2.MODEL_ID)
        self.assertEqual(scientific["model_revision"], v2.MODEL_REVISION)
        self.assertEqual(scientific["adapter_root"], v2.ADAPTER_ROOT)
        self.assertEqual(resources["resource_caps"], v2.RESOURCE_CAPS)
        self.assertFalse(
            resources["execution_environment_values_recorded_at_protocol_freeze"]
        )
        self.assertTrue(
            resources["missing_or_unverifiable_execution_resource_blocks_execution"]
        )
        self.assertFalse(resources["resource_repeatability_claimed"])

    def test_execution_budget_and_capabilities_are_not_authorized(self) -> None:
        execution = self.protocol["execution_protocol"]
        self.assertEqual(execution["formal_invocation_budget"], 1)
        self.assertEqual(execution["retry_budget"], 0)
        self.assertEqual(execution["per_record_attempt_budget"], 1)
        self.assertTrue(execution["stop_on_first_exception"])
        self.assertFalse(execution["continue_after_failure"])
        self.assertFalse(execution["diagnostic_execution_authorized"])
        self.assertFalse(execution["v1_or_v2_identity_or_output_reuse"])
        self.assertFalse(execution["network"])
        self.assertFalse(execution["live_browser"])
        self.assertFalse(execution["capture_real_content"])

    def test_claims_and_authority_preserve_protocol_only_boundary(self) -> None:
        claims = self.protocol["claims"]
        for name in (
            "diagnostic_protocol_frozen",
            "diagnostic_protocol_freeze_justified",
            "investigation_protocol_frozen",
            "investigation_executed",
            "static_investigation_complete",
            "static_investigation_formal_gate_passed",
            "v2_attempt_consumed",
        ):
            self.assertIs(claims[name], True, name)
        for name in (
            "diagnostic_attempt_consumed",
            "diagnostic_executed",
            "diagnostic_execution_authorized",
            "historical_runtime_health_established",
            "static_root_cause_reproduced",
            "failed_runtime_substage_isolated",
            "runtime_root_cause_established",
            "remediation_delta_established",
            "recovery_v3_justified",
            "v2_execution_retried",
            "formal_measurement_complete",
            "model_evaluated",
            "quality_established",
            "safety_established",
            "evaluation_repeatability_established",
            "resource_repeatability_established",
            "cross_machine_reproducibility_established",
            "serving_eligible",
            "promotion_eligible",
            "runtime_eligible",
        ):
            self.assertIs(claims[name], False, name)
        authority = self.protocol["authority_contract"]
        self.assertTrue(authority["protocol_freeze_authorized"])
        self.assertTrue(
            authority["diagnostic_implementation_freeze_authorized_after_clean_merge"]
        )
        for name in (
            "diagnostic_execution_authorized",
            "processor_execution_authorized",
            "model_or_cuda_execution_authorized",
            "live_browser_or_network_authorized",
            "capture_authorized",
            "training_authorized",
            "v1_or_v2_retry_authorized",
            "recovery_v3_authorized",
            "runtime_repository_changed",
            "runtime_integration_changed",
            "runtime_policy_or_approval_bypass",
        ):
            self.assertIs(authority[name], False, name)

    def test_outcome_is_neutral_and_next_gate_is_implementation_only(self) -> None:
        rubric = self.protocol["decision_rubric"]
        self.assertEqual(rubric["allowed_outcomes"], list(contract.ALLOWED_OUTCOMES))
        self.assertIsNone(rubric["outcome_selected_at_protocol_freeze"])
        self.assertTrue(rubric["checkpoint_interval_is_observation_not_causal_origin"])
        self.assertEqual(self.protocol["next_gate"], contract.IMPLEMENTATION_GATE_ID)
        action = self.protocol["locked_next_action"]
        self.assertTrue(action["implementation_freeze_only"])
        self.assertTrue(action["eligible_to_start_after_clean_protocol_merge"])
        self.assertFalse(action["diagnostic_execution_authorized"])

    def test_bool_integer_alias_and_candidate_drift_are_rejected(self) -> None:
        for path, replacement in (
            (("claims", "diagnostic_executed"), 0),
            (("execution_protocol", "retry_budget"), False),
            (("freeze_preconditions", "formal_diagnostic_invocations"), False),
        ):
            changed = copy.deepcopy(self.protocol)
            target = changed
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = replacement
            self.assertEqual(changed, self.protocol)
            with (
                self.subTest(path=path),
                self.assertRaises(
                    contract.MM005GenerationFailureDiagnosticProtocolError
                ),
            ):
                contract.validate_preregistration(changed, **self._validation_inputs())
        for name in ("diagnostic_output_absent", "lifecycle_lease_absent"):
            changed_inputs = self._validation_inputs()
            changed_inputs[name] = 1
            with self.assertRaises(
                contract.MM005GenerationFailureDiagnosticProtocolError
            ):
                contract.expected_preregistration(**changed_inputs)

    def test_source_payload_closure_and_drift_are_rejected(self) -> None:
        for mutation in ("missing", "extra", "changed"):
            changed = self._validation_inputs()
            sources = changed["source_payloads"]
            self.assertIsInstance(sources, dict)
            assert isinstance(sources, dict)
            if mutation == "missing":
                sources.pop("shared_generation_helper")
                expected_error = True
            elif mutation == "extra":
                sources["extra"] = b"x"
                expected_error = True
            else:
                sources["shared_generation_helper"] += b" "
                expected_error = True
            if expected_error:
                with (
                    self.subTest(mutation=mutation),
                    self.assertRaises(
                        contract.MM005GenerationFailureDiagnosticProtocolError
                    ),
                ):
                    contract.expected_preregistration(**changed)

    def test_freeze_blob_drift_and_unsafe_paths_are_rejected(self) -> None:
        original = builder._git_blob_bytes
        for tampered_path in (
            contract.PUBLISHED_RESULT_PATH,
            contract.V2_PREREGISTRATION_PATH,
            contract.PROTOCOL_SOURCE_PATHS["model_evaluation_contract_v1"],
            contract.PROTOCOL_SOURCE_PATHS["model_evaluation_recovery_contract_v2"],
            contract.PROTOCOL_SOURCE_PATHS["shared_generation_helper"],
        ):

            def changed(commit: str, relative: str) -> bytes:
                payload = original(commit, relative)
                if relative == tampered_path:
                    return payload + b" "
                return payload

            with (
                self.subTest(tampered_path=tampered_path),
                mock.patch.object(builder, "_git_blob_bytes", side_effect=changed),
                self.assertRaises(RuntimeError),
            ):
                builder._validate_published_result_lineage()
        for path in ("", "../outside", "/absolute", "a\\b", "a/./b"):
            with self.subTest(path=path), self.assertRaises(RuntimeError):
                builder._validate_repository_relative_path(path)

    def test_git_environment_is_hermetic_and_replace_refs_are_rejected(self) -> None:
        polluted = {
            "GIT_DIR": "outside",
            "GIT_NAMESPACE": "shadow",
            "GIT_REPLACE_REF_BASE": "refs/evil/",
            "GIT_CONFIG_GLOBAL": "outside.cfg",
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "core.repositoryformatversion",
            "GIT_CONFIG_VALUE_0": "999",
            "GIT_GRAFT_FILE": "outside.grafts",
            "GIT_SHALLOW_FILE": "outside.shallow",
        }
        with mock.patch.dict(os.environ, polluted, clear=False):
            environment = builder._git_environment()
        inherited_git_keys = set(polluted) & set(environment)
        self.assertEqual(inherited_git_keys, {"GIT_CONFIG_GLOBAL", "GIT_GRAFT_FILE"})
        self.assertEqual(environment["GIT_CONFIG_GLOBAL"], os.devnull)
        self.assertEqual(environment["GIT_CONFIG_NOSYSTEM"], "1")
        self.assertEqual(environment["GIT_GRAFT_FILE"], os.devnull)
        self.assertEqual(environment["GIT_NO_REPLACE_OBJECTS"], "1")
        self.assertEqual(environment["GIT_NO_LAZY_FETCH"], "1")
        self.assertEqual(environment["GIT_TERMINAL_PROMPT"], "0")
        self.assertEqual(
            {key for key in environment if key.startswith("GIT_")},
            {
                "GIT_CONFIG_GLOBAL",
                "GIT_CONFIG_NOSYSTEM",
                "GIT_GRAFT_FILE",
                "GIT_LFS_SKIP_SMUDGE",
                "GIT_NO_LAZY_FETCH",
                "GIT_NO_REPLACE_OBJECTS",
                "GIT_TERMINAL_PROMPT",
            },
        )

        def git_process(*args: str) -> subprocess.CompletedProcess[bytes]:
            stdout = b"deadbeef\n" if args == ("replace", "-l") else b""
            return subprocess.CompletedProcess(["git", *args], 0, stdout, b"")

        with (
            mock.patch.object(builder, "_git_process", side_effect=git_process),
            self.assertRaises(RuntimeError),
        ):
            builder._require_git_lineage_state("a" * 40)

        completed = subprocess.CompletedProcess(["git"], 0, b"", b"")
        with mock.patch.object(
            builder.subprocess, "run", return_value=completed
        ) as run:
            builder._git_process("rev-parse", "--verify", "HEAD^{commit}")
        self.assertEqual(
            run.call_args.args[0],
            [
                "git",
                "-c",
                "core.commitGraph=false",
                "rev-parse",
                "--verify",
                "HEAD^{commit}",
            ],
        )

    def test_symlink_and_hardlink_bound_files_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = root / "original.json"
            original.write_bytes(b"{}\n")
            linked = root / "linked.json"
            try:
                os.link(original, linked)
            except OSError as exc:
                self.skipTest(f"hardlinks unavailable: {exc}")
            with self.assertRaises(RuntimeError):
                builder._read_regular_file_once(linked)

        with tempfile.TemporaryDirectory() as directory:
            original = Path(directory) / "original.json"
            original.write_bytes(b"{}\n")
            with (
                mock.patch.object(Path, "is_symlink", return_value=True),
                self.assertRaises(RuntimeError),
            ):
                builder._read_regular_file_once(original)

    def test_existing_protocol_or_planned_output_is_never_overwritten(self) -> None:
        with (
            mock.patch.object(builder, "build_protocol", return_value=self.protocol),
            self.assertRaises(FileExistsError),
        ):
            builder.main([])

        def exists(path: object) -> bool:
            return str(path).replace("\\", "/").endswith(contract.RUN_OUTPUT_ROOT)

        with (
            mock.patch.object(builder.os.path, "lexists", side_effect=exists),
            self.assertRaises(RuntimeError),
        ):
            builder._require_planned_outputs_absent()

    def test_final_snapshot_recheck_detects_source_head_blob_and_output_drift(
        self,
    ) -> None:
        _, snapshot = builder._capture_protocol_inputs()
        original_read = builder._read_repository_file
        changed_source = contract.PROTOCOL_SOURCE_PATHS["diagnostic_contract"]

        def changed_read(relative: str) -> bytes:
            payload = original_read(relative)
            return payload + b" " if relative == changed_source else payload

        with (
            mock.patch.object(
                builder, "_read_repository_file", side_effect=changed_read
            ),
            self.assertRaisesRegex(RuntimeError, "input changed"),
        ):
            builder._revalidate_protocol_inputs(snapshot)

        with (
            mock.patch.object(builder, "_git_head_commit", return_value="f" * 40),
            self.assertRaisesRegex(RuntimeError, "HEAD changed"),
        ):
            builder._revalidate_protocol_inputs(snapshot)

        original_blob = builder._git_blob_bytes

        def changed_blob(commit: str, relative: str) -> bytes:
            payload = original_blob(commit, relative)
            if relative == contract.V2_PREREGISTRATION_PATH:
                return payload + b" "
            return payload

        with (
            mock.patch.object(builder, "_git_blob_bytes", side_effect=changed_blob),
            self.assertRaisesRegex(RuntimeError, "blob changed"),
        ):
            builder._revalidate_protocol_inputs(snapshot)

        with (
            mock.patch.object(
                builder,
                "_require_planned_outputs_absent",
                side_effect=RuntimeError("late output"),
            ),
            self.assertRaisesRegex(RuntimeError, "late output"),
        ):
            builder._revalidate_protocol_inputs(snapshot)

    def test_planned_output_parent_symlink_or_reparse_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            unsafe_parent = root / "work" / "evaluation-runs"
            unsafe_parent.mkdir(parents=True)
            original_is_symlink = Path.is_symlink

            def is_symlink(path: Path) -> bool:
                if path == unsafe_parent:
                    return True
                return original_is_symlink(path)

            with (
                mock.patch.object(builder, "ROOT", root),
                mock.patch.object(
                    Path, "is_symlink", autospec=True, side_effect=is_symlink
                ),
                self.assertRaisesRegex(RuntimeError, "unsafe bound parent"),
            ):
                builder._require_planned_outputs_absent()

    def test_new_sources_have_no_execution_or_network_capability(self) -> None:
        paths = (
            ROOT
            / "src/fullcycle_bridge/mm005_browser_research_model_evaluation_generation_failure_diagnostic.py",
            ROOT
            / "scripts/prepare_mm005_browser_research_model_evaluation_generation_failure_diagnostic_protocol_v1.py",
        )
        expected_imports = {
            paths[0]: {"__future__", ".", "collections", "hashlib", "json", "typing"},
            paths[1]: {
                "__future__",
                "argparse",
                "collections",
                "fullcycle_bridge",
                "os",
                "pathlib",
                "re",
                "stat",
                "subprocess",
                "sys",
                "typing",
            },
        }
        forbidden_calls = {
            "__import__",
            "breakpoint",
            "compile",
            "eval",
            "exec",
            "input",
            "open",
            "os.popen",
            "os.remove",
            "os.rename",
            "os.replace",
            "os.startfile",
            "os.system",
            "os.unlink",
            "subprocess.Popen",
            "subprocess.call",
            "subprocess.check_call",
            "subprocess.check_output",
        }

        def dotted_name(node: ast.expr) -> str | None:
            if isinstance(node, ast.Name):
                return node.id
            if isinstance(node, ast.Attribute):
                parent = dotted_name(node.value)
                return f"{parent}.{node.attr}" if parent else node.attr
            return None

        for path in paths:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            imported: set[str] = set()
            calls: list[tuple[str, ast.Call]] = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    imported.add(node.module.split(".")[0] if node.module else ".")
                elif isinstance(node, ast.Call):
                    name = dotted_name(node.func)
                    if name:
                        calls.append((name, node))
            self.assertEqual(imported, expected_imports[path])
            self.assertTrue(forbidden_calls.isdisjoint(name for name, _ in calls), path)
            subprocess_calls = [
                item for item in calls if item[0].startswith("subprocess.")
            ]
            if path == paths[0]:
                self.assertEqual(subprocess_calls, [])
            else:
                self.assertEqual(
                    {name for name, _ in subprocess_calls}, {"subprocess.run"}
                )
                for _, call in subprocess_calls:
                    self.assertIsInstance(call.args[0], ast.List)
                    command = call.args[0]
                    assert isinstance(command, ast.List)
                    self.assertIsInstance(command.elts[0], ast.Constant)
                    self.assertEqual(command.elts[0].value, "git")
        self.assertTrue(
            (
                ROOT
                / "scripts/run_mm005_browser_research_model_evaluation_generation_failure_diagnostic_v1.py"
            ).is_file()
        )


if __name__ == "__main__":
    unittest.main()
