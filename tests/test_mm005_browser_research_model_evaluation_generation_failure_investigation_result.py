from __future__ import annotations

import ast
import copy
import os
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, ClassVar
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

sys.path.insert(0, str(SRC))
sys.path.insert(0, str(ROOT))

from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_model_evaluation_generation_failure_investigation as protocol,
)
from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_model_evaluation_generation_failure_investigation_result as result_contract,
)
from scripts import (  # noqa: E402
    prepare_mm005_browser_research_model_evaluation_generation_failure_investigation_protocol_v1 as protocol_builder,
)
from scripts import (  # noqa: E402
    run_mm005_browser_research_model_evaluation_generation_failure_investigation_v1 as runner,
)
from scripts import validate_offline as unified_validator  # noqa: E402


class MM005BrowserResearchGenerationFailureInvestigationResultV1Tests(
    unittest.TestCase
):
    protocol_context: ClassVar[dict[str, Any]]
    implementation_context: ClassVar[dict[str, Any]]
    result_inputs: ClassVar[dict[str, Any]]
    result: ClassVar[dict[str, Any]]

    @classmethod
    def setUpClass(cls) -> None:
        cls.protocol_context = runner._published_protocol_context()
        implementation_bindings: dict[str, dict[str, Any]] = {}
        for name, relative in sorted(
            result_contract.IMPLEMENTATION_SOURCE_PATHS.items()
        ):
            payload = (ROOT / relative).read_bytes()
            implementation_bindings[name] = {
                "path": relative,
                "bytes": len(payload),
                "sha256": protocol.sha256_bytes(payload),
                "tracked_bytes_equal_implementation_freeze_commit_blob": True,
            }
        cls.implementation_context = {
            "freeze_commit": "a" * 40,
            "source_bindings": implementation_bindings,
        }
        cls.result_inputs = runner._result_inputs(
            protocol_context=cls.protocol_context,
            implementation_context=cls.implementation_context,
            executed_at_utc="2026-08-29T12:34:56Z",
        )
        cls.result = result_contract.build_static_investigation_result(
            **cls.result_inputs
        )

    def test_contract_closes_schema_truth_table_claims_and_routes(self) -> None:
        contract = result_contract.result_contract()
        self.assertEqual(contract["result_version"], 1)
        self.assertEqual(
            contract["required_top_level_keys"],
            list(result_contract.RESULT_REQUIRED_TOP_LEVEL_KEYS),
        )
        self.assertEqual(
            contract["outcome_selection"]["allowed_outcomes"],
            list(protocol.DECISION_OUTCOMES),
        )
        self.assertEqual(
            contract["outcome_selection"]["precedence"],
            list(result_contract.OUTCOME_PRECEDENCE),
        )
        comparison = contract["structural_comparison_contract"]
        self.assertEqual(
            comparison["closed_fields"],
            list(result_contract.STRUCTURAL_COMPARISON_FIELDS),
        )
        self.assertFalse(comparison["content_identity_difference_is_causal"])
        self.assertTrue(
            comparison["difference_outcome_requires_closed_field_difference"]
        )
        observation = contract["static_plan_observation_contract"]
        self.assertEqual(observation["steps"], list(protocol.STATIC_DIAGNOSTIC_STEPS))
        self.assertEqual(
            observation["deterministic_failure_domain_step_by_error_code"],
            result_contract.DETERMINISTIC_FAILURE_DOMAIN_STEP_BY_CODE,
        )
        self.assertEqual(
            observation["monolithic_registry_failure_terminal_step"],
            protocol.STATIC_DIAGNOSTIC_STEPS[1],
        )
        self.assertTrue(
            observation["failure_domain_step_does_not_prove_prior_steps_completed"]
        )
        self.assertFalse(observation["unknown_or_unexpected_failure_publishes_result"])
        self.assertFalse(observation["caller_supplied_outcome_or_observations_allowed"])
        for route in contract["outcome_routes"].values():
            self.assertTrue(route["protocol_freeze_only"])
            self.assertFalse(route["execution_authorized"])
        claims = contract["claims_contract"]
        for name in (
            "formal_measurement_complete",
            "model_evaluated",
            "historical_runtime_health_established",
            "static_root_cause_reproduced",
            "failed_runtime_substage_isolated",
            "remediation_delta_established",
            "recovery_v3_justified",
            "diagnostic_model_or_cuda_execution_authorized",
            "runtime_eligible",
        ):
            self.assertFalse(claims[name], name)

    def test_five_outcomes_are_mutually_exclusive(self) -> None:
        trusted = {
            "protocol_and_lineage_valid": True,
            "authority_boundary_preserved": True,
            "static_plan_complete": False,
            "deterministic_static_input_or_message_failure_reproduced": False,
            "closed_structural_difference_observed": False,
            "static_pipeline_reconstructed_without_contract_violation": False,
        }
        cases = {
            "protocol_or_lineage_invalid": {
                **trusted,
                "protocol_and_lineage_valid": False,
            },
            "deterministic_static_input_or_message_failure_reproduced": {
                **trusted,
                "static_plan_complete": True,
                "deterministic_static_input_or_message_failure_reproduced": True,
            },
            "static_difference_observed_without_causal_failure": {
                **trusted,
                "static_plan_complete": True,
                "closed_structural_difference_observed": True,
            },
            "static_pipeline_reconstructed_without_contract_violation": {
                **trusted,
                "static_plan_complete": True,
                "static_pipeline_reconstructed_without_contract_violation": True,
            },
            "static_investigation_inconclusive": trusted,
        }
        for expected, observations in cases.items():
            with self.subTest(expected=expected):
                predicates = result_contract.outcome_predicates(observations)
                self.assertEqual(sum(predicates.values()), 1)
                self.assertTrue(predicates[expected])
                self.assertEqual(result_contract.select_outcome(observations), expected)

    def test_bool_integer_aliases_and_contradictions_are_rejected(self) -> None:
        valid: dict[str, object] = {
            "protocol_and_lineage_valid": True,
            "authority_boundary_preserved": True,
            "static_plan_complete": True,
            "deterministic_static_input_or_message_failure_reproduced": False,
            "closed_structural_difference_observed": False,
            "static_pipeline_reconstructed_without_contract_violation": True,
        }
        for name in result_contract.OBSERVATION_KEYS:
            changed = dict(valid)
            changed[name] = int(bool(valid[name]))
            with (
                self.subTest(name=name),
                self.assertRaises(
                    result_contract.MM005GenerationFailureInvestigationResultError
                ),
            ):
                result_contract.select_outcome(changed)
        for changed in (
            {
                **valid,
                "deterministic_static_input_or_message_failure_reproduced": True,
            },
            {
                **valid,
                "closed_structural_difference_observed": True,
            },
            {
                **valid,
                "static_plan_complete": False,
            },
        ):
            with self.assertRaises(
                result_contract.MM005GenerationFailureInvestigationResultError
            ):
                result_contract.select_outcome(changed)

    def test_real_static_inputs_recompute_to_the_narrow_pass_outcome(self) -> None:
        checked = result_contract.validate_static_investigation_result(
            self.result, **self.result_inputs
        )
        self.assertEqual(checked, self.result)
        self.assertEqual(
            self.result["decision"]["selected_outcome"],
            "static_pipeline_reconstructed_without_contract_violation",
        )
        self.assertTrue(self.result["formal_gate"]["passed"])
        self.assertTrue(all(self.result["formal_gate"]["gates"].values()))
        self.assertTrue(self.result["claims"]["investigation_executed"])
        self.assertTrue(self.result["claims"]["static_investigation_complete"])
        self.assertFalse(self.result["claims"]["formal_measurement_complete"])
        self.assertFalse(self.result["claims"]["model_evaluated"])
        self.assertTrue(self.result["decision"]["runtime_root_cause_unresolved"])
        self.assertEqual(
            self.result["locked_next_action"]["next_gate_id"],
            result_contract.DIAGNOSTIC_PROTOCOL_GATE_ID,
        )
        self.assertFalse(
            self.result["locked_next_action"]["diagnostic_execution_authorized"]
        )

        without_digest = copy.deepcopy(self.result)
        digest = without_digest.pop("report_digest")
        self.assertEqual(
            digest,
            protocol.sha256_bytes(protocol.artifact_json_bytes(without_digest)),
        )

    def test_expected_content_differences_are_not_structural_or_causal(self) -> None:
        comparison = self.result["structural_comparison"]
        self.assertFalse(comparison["closed_structural_difference_observed"])
        self.assertTrue(comparison["content_identity_differences_observed"])
        self.assertFalse(comparison["content_identity_difference_is_causal"])
        self.assertEqual(len(comparison["controls"]), 3)
        for control in comparison["controls"]:
            self.assertTrue(control["matches_target_closed_dimensions"])
            self.assertTrue(control["content_identity_differs_from_target"])

    def test_formal_builder_keeps_publishable_outcomes_reachable(self) -> None:
        deterministic_error = protocol.MM005GenerationFailureInvestigationError(
            "RUNTIME_MESSAGE_TRANSPORT_PROJECTION_MISMATCH",
            "$.runtime_messages",
        )
        with mock.patch.object(
            protocol,
            "build_static_record_registry",
            side_effect=deterministic_error,
        ):
            deterministic = result_contract.build_static_investigation_result(
                **self.result_inputs
            )
            result_contract.validate_static_investigation_result(
                deterministic, **self.result_inputs
            )
        self.assertEqual(
            deterministic["decision"]["selected_outcome"],
            "deterministic_static_input_or_message_failure_reproduced",
        )
        self.assertTrue(
            deterministic["claims"]["deterministic_static_failure_reproduced"]
        )
        self.assertEqual(
            deterministic["record_registry"]["observation_status"],
            "deterministic_failure_before_registry_completed",
        )
        self.assertIsNone(deterministic["record_registry"]["observed"])
        failed_steps = [
            item
            for item in deterministic["execution"]["steps"]
            if item["status"] == "deterministic_failure"
        ]
        self.assertEqual(failed_steps[0]["step"], protocol.STATIC_DIAGNOSTIC_STEPS[1])
        self.assertEqual(
            deterministic["static_plan_observation"]["deterministic_failure"][
                "failure_domain_step"
            ],
            protocol.STATIC_DIAGNOSTIC_STEPS[6],
        )
        passed_steps = [
            item["step"]
            for item in deterministic["execution"]["steps"]
            if item["status"] == "passed"
        ]
        self.assertEqual(
            passed_steps,
            [
                protocol.STATIC_DIAGNOSTIC_STEPS[0],
                protocol.STATIC_DIAGNOSTIC_STEPS[-1],
            ],
        )

        structural = copy.deepcopy(self.result["structural_comparison"])
        structural["closed_structural_difference_observed"] = True
        structural["controls"][0]["matches_target_closed_dimensions"] = False
        with mock.patch.object(
            result_contract,
            "build_structural_comparison",
            return_value=structural,
        ):
            difference = result_contract.build_static_investigation_result(
                **self.result_inputs
            )
            result_contract.validate_static_investigation_result(
                difference, **self.result_inputs
            )
        self.assertEqual(
            difference["decision"]["selected_outcome"],
            "static_difference_observed_without_causal_failure",
        )
        self.assertTrue(difference["claims"]["closed_structural_difference_observed"])
        self.assertFalse(
            difference["decision"]["content_identity_difference_is_causal"]
        )

        inconclusive_error = result_contract._StaticPlanInconclusive(
            "TEST_CONTROL_FLOW_INCONCLUSIVE", "$.control_flow"
        )
        with mock.patch.object(
            result_contract,
            "build_control_flow_observation",
            side_effect=inconclusive_error,
        ):
            inconclusive = result_contract.build_static_investigation_result(
                **self.result_inputs
            )
            result_contract.validate_static_investigation_result(
                inconclusive, **self.result_inputs
            )
        self.assertEqual(
            inconclusive["decision"]["selected_outcome"],
            "static_investigation_inconclusive",
        )
        self.assertEqual(
            inconclusive["static_plan_observation"]["inconclusive_reason_codes"],
            ["TEST_CONTROL_FLOW_INCONCLUSIVE"],
        )
        self.assertTrue(inconclusive["formal_gate"]["passed"])

    def test_trust_and_unexpected_failures_never_become_results(self) -> None:
        untrusted = dict(self.result_inputs)
        untrusted["preregistration_payload"] = b"{}\n"
        with self.assertRaises(
            result_contract.MM005GenerationFailureInvestigationResultError
        ):
            result_contract.build_static_investigation_result(**untrusted)

        with (
            mock.patch.object(
                protocol,
                "build_static_record_registry",
                side_effect=RuntimeError("unexpected implementation defect"),
            ),
            self.assertRaisesRegex(RuntimeError, "unexpected implementation defect"),
        ):
            result_contract.build_static_investigation_result(**self.result_inputs)

        unknown_domain_error = protocol.MM005GenerationFailureInvestigationError(
            "UNKNOWN_FUTURE_INTERNAL_CODE", "$.internal"
        )
        with (
            mock.patch.object(
                protocol,
                "build_static_record_registry",
                side_effect=unknown_domain_error,
            ),
            self.assertRaises(
                protocol.MM005GenerationFailureInvestigationError
            ) as caught,
        ):
            result_contract.build_static_investigation_result(**self.result_inputs)
        self.assertIs(caught.exception, unknown_domain_error)

    def test_candidate_tamper_and_invalid_timestamp_are_rejected(self) -> None:
        changed = copy.deepcopy(self.result)
        changed["claims"]["formal_measurement_complete"] = 0
        with self.assertRaises(
            result_contract.MM005GenerationFailureInvestigationResultError
        ):
            result_contract.validate_static_investigation_result(
                changed, **self.result_inputs
            )
        invalid_inputs = dict(self.result_inputs)
        invalid_inputs["executed_at_utc"] = "2026-99-99T12:34:56Z"
        with self.assertRaises(
            result_contract.MM005GenerationFailureInvestigationResultError
        ):
            result_contract.build_static_investigation_result(**invalid_inputs)

    def test_control_flow_requires_exact_marker_counts_and_order(self) -> None:
        source_payloads = self.protocol_context["source_payloads"]
        originals = {
            name: source_payloads[name]
            for name in ("v2_runner", "shared_generation_helper")
        }
        observation = result_contract.build_control_flow_observation(originals)
        self.assertTrue(observation["outer_markers_unique_and_ordered"])
        self.assertTrue(observation["inner_markers_unique_and_ordered"])
        self.assertFalse(observation["checkpoint_proves_model_generate_entered"])

        helper = originals["shared_generation_helper"].decode("utf-8")
        missing = helper.replace("model.generate(", "model.gen_erate(", 1)
        duplicate = helper.replace(
            "processor.batch_decode(",
            "processor.batch_decode(\n# processor.batch_decode(",
            1,
        )
        reordered = helper.replace(
            "processor.apply_chat_template(", "__FIRST_MARKER__(", 1
        ).replace('processor(**kwargs).to("cuda")', "__SECOND_MARKER__", 1)
        reordered = reordered.replace(
            "__FIRST_MARKER__(", 'processor(**kwargs).to("cuda")', 1
        ).replace("__SECOND_MARKER__", "processor.apply_chat_template(", 1)
        for changed in (missing, duplicate, reordered):
            with (
                self.subTest(change=changed[:40]),
                self.assertRaises(
                    result_contract.MM005GenerationFailureInvestigationResultError
                ),
            ):
                result_contract.build_control_flow_observation(
                    {
                        **originals,
                        "shared_generation_helper": changed.encode("utf-8"),
                    }
                )

    def test_protocol_merge_commit_config_and_ten_sources_are_git_bound(self) -> None:
        completed = runner._git_process(
            "merge-base",
            "--is-ancestor",
            result_contract.PROTOCOL_MERGE_COMMIT,
            "HEAD",
        )
        self.assertEqual(completed.returncode, 0)
        payload = self.protocol_context["preregistration_payload"]
        self.assertEqual(len(payload), result_contract.PROTOCOL_BYTES)
        self.assertEqual(
            protocol.sha256_bytes(payload), result_contract.PROTOCOL_SHA256
        )
        self.assertEqual(
            runner._git_blob_bytes(
                result_contract.PROTOCOL_MERGE_COMMIT,
                protocol.PREREGISTRATION_PATH,
            ),
            payload,
        )
        bindings = self.protocol_context["source_bindings"]
        self.assertEqual(set(bindings), set(protocol.PROTOCOL_SOURCE_PATHS))
        self.assertEqual(len(bindings), 10)
        for binding in bindings.values():
            self.assertTrue(binding["tracked_bytes_equal_protocol_merge_commit_blob"])

    def test_worker_local_historical_contexts_bind_git_blobs(self) -> None:
        with (
            mock.patch.object(
                runner,
                "_read_repository_file",
                side_effect=AssertionError("worker context read current source"),
            ),
            mock.patch.object(
                protocol_builder,
                "protocol_inputs",
                return_value=self.protocol_context["protocol_inputs"],
            ),
        ):
            historical_protocol = runner._historical_protocol_context(self.result)
        self.assertEqual(
            historical_protocol["preregistration_payload"],
            self.protocol_context["preregistration_payload"],
        )
        self.assertEqual(
            historical_protocol["source_bindings"],
            self.protocol_context["source_bindings"],
        )

        payloads = {
            relative: (ROOT / relative).read_bytes()
            for relative in result_contract.IMPLEMENTATION_SOURCE_PATHS.values()
        }

        def implementation_blob(_commit: str, relative: str) -> bytes:
            return payloads[relative]

        with (
            mock.patch.object(runner, "_require_commit_ancestor"),
            mock.patch.object(
                runner, "_git_blob_bytes", side_effect=implementation_blob
            ),
            mock.patch.object(
                runner,
                "_read_repository_file",
                side_effect=AssertionError("historical check read current source"),
            ),
        ):
            historical_implementation = (
                runner._historical_implementation_source_context(self.result)
            )
        self.assertEqual(
            historical_implementation["source_bindings"],
            self.implementation_context["source_bindings"],
        )

        changed = copy.deepcopy(self.result)
        changed["implementation_lineage"]["implementation_sources"]["result_runner"][
            "sha256"
        ] = "sha256:" + "0" * 64
        with (
            mock.patch.object(runner, "_require_commit_ancestor"),
            mock.patch.object(
                runner, "_git_blob_bytes", side_effect=implementation_blob
            ),
            self.assertRaisesRegex(RuntimeError, "historical implementation source"),
        ):
            runner._historical_implementation_source_context(changed)

    def test_check_delegates_without_running_current_result_semantics(self) -> None:
        freeze_commit = self.implementation_context["freeze_commit"]
        worker_summary = {
            "checked": True,
            "diagnostic_records": 7,
            "gate_id": result_contract.GATE_ID,
            "implementation_freeze_commit": freeze_commit,
            "model_free": True,
            "next_gate": result_contract.DIAGNOSTIC_PROTOCOL_GATE_ID,
            "protocol_merge_commit": result_contract.PROTOCOL_MERGE_COMMIT,
            "protocol_sha256": result_contract.PROTOCOL_SHA256,
            "report_digest": self.result["report_digest"],
            "runtime_eligible": False,
            "runtime_root_cause_unresolved": True,
            "selected_outcome": result_contract.OUTCOME_PRECEDENCE[3],
            "static_investigation_complete": True,
            "target_record": protocol.TARGET_RECORD_ID,
            "valid": True,
        }
        payload = protocol.artifact_json_bytes(self.result)
        with (
            mock.patch.object(
                runner,
                "_historical_implementation_source_context",
                return_value=self.implementation_context,
            ),
            mock.patch.object(
                runner,
                "_require_historical_implementation_introduction_commit",
            ) as introduction_mock,
            mock.patch.object(
                runner,
                "_require_historical_implementation_slice",
            ) as slice_mock,
            mock.patch.object(
                runner,
                "_require_historical_protocol_bootstrap",
            ) as bootstrap_mock,
            mock.patch.object(
                runner,
                "_git_process",
                return_value=mock.Mock(returncode=0),
            ),
            mock.patch.object(
                runner,
                "_invoke_historical_worker",
                return_value=worker_summary,
            ) as invoke_mock,
            mock.patch.object(
                runner,
                "_historical_protocol_context",
                side_effect=AssertionError(
                    "parent executed current protocol semantics"
                ),
            ),
            mock.patch.object(
                result_contract,
                "build_static_investigation_result",
                side_effect=AssertionError("parent executed current result semantics"),
            ),
        ):
            summary = runner._delegate_historical_check(payload)

        invoke_mock.assert_called_once_with(payload, freeze_commit)
        introduction_mock.assert_called_once_with(freeze_commit)
        slice_mock.assert_called_once_with(freeze_commit)
        bootstrap_mock.assert_called_once_with(self.result, freeze_commit)
        self.assertEqual(summary, worker_summary)

    def test_historical_freeze_commit_is_the_unique_source_introduction(
        self,
    ) -> None:
        freeze_commit = "b" * 40
        matching = [
            mock.Mock(
                returncode=0,
                stdout=(freeze_commit + "\n" + ("d" * 40) + "\n").encode("ascii"),
            )
            for _ in runner._HISTORICAL_IMPLEMENTATION_SOURCE_PATHS
        ]
        with mock.patch.object(
            runner, "_git_process", side_effect=matching
        ) as process_mock:
            runner._require_historical_implementation_introduction_commit(freeze_commit)
        self.assertEqual(
            process_mock.call_count,
            len(runner._HISTORICAL_IMPLEMENTATION_SOURCE_PATHS),
        )
        for call in process_mock.call_args_list:
            self.assertEqual(call.args[1], runner._HISTORICAL_TRUSTED_MAINLINE_REF)
            self.assertIn("--first-parent", call.args)
            self.assertIn("--reverse", call.args)

        mismatched = list(matching)
        mismatched[-1] = mock.Mock(
            returncode=0,
            stdout=(("c" * 40) + "\n").encode("ascii"),
        )
        with (
            mock.patch.object(runner, "_git_process", side_effect=mismatched),
            self.assertRaisesRegex(RuntimeError, "freeze commit is not trusted"),
        ):
            runner._require_historical_implementation_introduction_commit(freeze_commit)

    def test_historical_freeze_has_the_exact_reviewed_slice_diff(self) -> None:
        freeze_commit = "b" * 40
        payload = (
            b"\0".join(
                path.encode("utf-8")
                for path in sorted(runner._HISTORICAL_IMPLEMENTATION_SLICE_PATHS)
            )
            + b"\0"
        )
        with mock.patch.object(
            runner,
            "_git_process",
            return_value=mock.Mock(returncode=0, stdout=payload),
        ) as process_mock:
            runner._require_historical_implementation_slice(freeze_commit)
        self.assertEqual(process_mock.call_args.args[0], "diff")
        self.assertIn(
            runner._HISTORICAL_PROTOCOL_MERGE_COMMIT, process_mock.call_args.args
        )
        self.assertIn(freeze_commit, process_mock.call_args.args)

        untrusted = payload.removesuffix(b"\0") + b"\0unexpected.py\0"
        with (
            mock.patch.object(
                runner,
                "_git_process",
                return_value=mock.Mock(returncode=0, stdout=untrusted),
            ),
            self.assertRaisesRegex(RuntimeError, "slice is not trusted"),
        ):
            runner._require_historical_implementation_slice(freeze_commit)

    def test_parent_binds_protocol_bootstrap_before_historical_execution(
        self,
    ) -> None:
        freeze_commit = self.implementation_context["freeze_commit"]
        payload_by_path = {
            runner._HISTORICAL_PROTOCOL_PATH: self.protocol_context[
                "preregistration_payload"
            ],
            **{
                relative: self.protocol_context["source_payloads"][name]
                for name, relative in runner._HISTORICAL_PROTOCOL_SOURCE_PATHS.items()
            },
        }

        def git_blob(commit: str, relative: str) -> bytes:
            self.assertIn(
                commit,
                (runner._HISTORICAL_PROTOCOL_MERGE_COMMIT, freeze_commit),
            )
            return payload_by_path[relative]

        with mock.patch.object(runner, "_git_blob_bytes", side_effect=git_blob):
            runner._require_historical_protocol_bootstrap(self.result, freeze_commit)

        drift_path = runner._HISTORICAL_PROTOCOL_SOURCE_PATHS["investigation_builder"]

        def drifted_git_blob(commit: str, relative: str) -> bytes:
            payload = payload_by_path[relative]
            if commit == freeze_commit and relative == drift_path:
                return payload + b"\n"
            return payload

        with (
            mock.patch.object(runner, "_git_blob_bytes", side_effect=drifted_git_blob),
            self.assertRaisesRegex(RuntimeError, "bootstrap source mismatch"),
        ):
            runner._require_historical_protocol_bootstrap(self.result, freeze_commit)

    def test_historical_worker_command_is_isolated_and_check_only(self) -> None:
        freeze_commit = self.implementation_context["freeze_commit"]
        runner_relative = result_contract.IMPLEMENTATION_SOURCE_PATHS["result_runner"]
        with mock.patch.object(
            runner,
            "_git_blob_bytes",
            return_value=(ROOT / runner_relative).read_bytes(),
        ):
            command = runner._historical_worker_command(
                ROOT,
                runner_relative,
                freeze_commit,
            )
        self.assertEqual(command[:4], [sys.executable, "-I", "-S", "-B"])
        self.assertEqual(command[-1], "--historical-check-worker")
        self.assertNotIn("--plan", command)
        self.assertNotIn("--check", command)
        with (
            mock.patch.object(runner, "_git_blob_bytes", return_value=b"changed"),
            self.assertRaisesRegex(RuntimeError, "checkout bytes mismatch"),
        ):
            runner._historical_worker_command(
                ROOT,
                runner_relative,
                freeze_commit,
            )

    def test_historical_checkout_disables_lfs_and_inherited_git_controls(
        self,
    ) -> None:
        freeze_commit = "b" * 40
        completed = (
            mock.Mock(returncode=0, stdout=b"", stderr=b""),
            mock.Mock(returncode=0, stdout=b"", stderr=b""),
            mock.Mock(
                returncode=0,
                stdout=(freeze_commit + "\n").encode("ascii"),
                stderr=b"",
            ),
        )
        with (
            tempfile.TemporaryDirectory() as directory,
            mock.patch.object(runner, "ROOT", Path(directory)),
            mock.patch.dict(
                os.environ,
                {"GIT_SSH_COMMAND": "must-not-survive"},
            ),
            mock.patch.object(
                runner,
                "_run_bounded_process",
                side_effect=completed,
            ) as process_mock,
        ):
            runner._clone_historical_checkout(
                Path(directory) / "checkout", freeze_commit
            )

        self.assertEqual(process_mock.call_count, 3)
        self.assertIn("--local", process_mock.call_args_list[0].args[0])
        for call in process_mock.call_args_list:
            command = call.args[0]
            environment = call.kwargs["environment"]
            self.assertIn("filter.lfs.process=", command)
            self.assertIn("filter.lfs.smudge=", command)
            self.assertIn("filter.lfs.required=false", command)
            self.assertIn("core.symlinks=false", command)
            self.assertEqual(environment["GIT_LFS_SKIP_SMUDGE"], "1")
            self.assertEqual(environment["GIT_NO_LAZY_FETCH"], "1")
            self.assertEqual(environment["GIT_TERMINAL_PROMPT"], "0")
            self.assertNotIn("GIT_SSH_COMMAND", environment)

    def test_parent_git_reads_are_sanitized_and_disable_lazy_fetch(self) -> None:
        completed = mock.Mock(returncode=0, stdout=b"", stderr=b"")
        with (
            mock.patch.dict(
                os.environ,
                {
                    "GIT_DIR": "must-not-survive",
                    "GIT_SSH_COMMAND": "must-not-survive",
                },
            ),
            mock.patch.object(
                runner.subprocess,
                "run",
                return_value=completed,
            ) as run_mock,
        ):
            self.assertIs(runner._git_process("rev-parse", "HEAD"), completed)
        environment = run_mock.call_args.kwargs["env"]
        self.assertNotIn("GIT_DIR", environment)
        self.assertNotIn("GIT_SSH_COMMAND", environment)
        self.assertEqual(environment["GIT_NO_LAZY_FETCH"], "1")

    def test_historical_worker_process_uses_sanitized_environment(self) -> None:
        freeze_commit = self.implementation_context["freeze_commit"]
        summary = {
            "checked": True,
            "diagnostic_records": 7,
            "gate_id": result_contract.GATE_ID,
            "implementation_freeze_commit": freeze_commit,
            "model_free": True,
            "next_gate": result_contract.DIAGNOSTIC_PROTOCOL_GATE_ID,
            "protocol_merge_commit": result_contract.PROTOCOL_MERGE_COMMIT,
            "protocol_sha256": result_contract.PROTOCOL_SHA256,
            "report_digest": self.result["report_digest"],
            "runtime_eligible": False,
            "runtime_root_cause_unresolved": True,
            "selected_outcome": result_contract.OUTCOME_PRECEDENCE[3],
            "static_investigation_complete": True,
            "target_record": protocol.TARGET_RECORD_ID,
            "valid": True,
        }

        def create_checkout(checkout: Path, _: str) -> None:
            (checkout / "baseline").mkdir(parents=True)

        completed = mock.Mock(
            returncode=0,
            stdout=protocol.artifact_json_bytes(summary),
            stderr=b"",
        )
        with (
            mock.patch.dict(
                os.environ,
                {
                    "GIT_DIR": "must-not-survive",
                    "GIT_SSH_COMMAND": "must-not-survive",
                },
            ),
            mock.patch.object(
                runner,
                "_clone_historical_checkout",
                side_effect=create_checkout,
            ),
            mock.patch.object(
                runner,
                "_historical_worker_command",
                return_value=[sys.executable, "worker.py"],
            ),
            mock.patch.object(
                runner,
                "_run_bounded_process",
                return_value=completed,
            ) as process_mock,
        ):
            observed = runner._invoke_historical_worker(b"{}\n", freeze_commit)

        self.assertEqual(observed, summary)
        environment = process_mock.call_args.kwargs["environment"]
        self.assertNotIn("GIT_DIR", environment)
        self.assertNotIn("GIT_SSH_COMMAND", environment)
        self.assertEqual(environment["GIT_NO_LAZY_FETCH"], "1")
        self.assertEqual(environment[runner._HISTORICAL_WORKER_ENV], "1")
        self.assertEqual(
            environment[runner._HISTORICAL_WORKER_COMMIT_ENV], freeze_commit
        )

    def test_historical_worker_summary_has_closed_route_and_receipts(self) -> None:
        freeze_commit = self.implementation_context["freeze_commit"]
        summary = {
            "checked": True,
            "diagnostic_records": 7,
            "gate_id": result_contract.GATE_ID,
            "implementation_freeze_commit": freeze_commit,
            "model_free": True,
            "next_gate": result_contract.DIAGNOSTIC_PROTOCOL_GATE_ID,
            "protocol_merge_commit": result_contract.PROTOCOL_MERGE_COMMIT,
            "protocol_sha256": result_contract.PROTOCOL_SHA256,
            "report_digest": self.result["report_digest"],
            "runtime_eligible": False,
            "runtime_root_cause_unresolved": True,
            "selected_outcome": result_contract.OUTCOME_PRECEDENCE[3],
            "static_investigation_complete": True,
            "target_record": protocol.TARGET_RECORD_ID,
            "valid": True,
        }
        runner._validate_historical_worker_summary(summary, freeze_commit)
        for key, value in (
            ("next_gate", result_contract.STATIC_REMEDIATION_PROTOCOL_GATE_ID),
            ("target_record", "sha256:" + "0" * 64),
            ("report_digest", "not-a-receipt"),
        ):
            with self.subTest(key=key):
                changed = dict(summary)
                changed[key] = value
                with self.assertRaisesRegex(RuntimeError, "summary mismatch"):
                    runner._validate_historical_worker_summary(changed, freeze_commit)

    def test_plan_is_read_only_and_formal_path_fails_closed_before_merge(self) -> None:
        output = ROOT / result_contract.RESULT_PATH
        before = output.read_bytes() if output.exists() else None
        summary = runner.run(plan=True)
        after = output.read_bytes() if output.exists() else None
        self.assertEqual(before, after)
        self.assertTrue(summary["plan_only"])
        self.assertFalse(summary["formal_execution_eligible"])
        self.assertFalse(summary["runtime_eligible"])

        if output.exists():
            checked = runner.run(check=True)
            self.assertTrue(checked["checked"])
            self.assertTrue(checked["valid"])
        else:
            with (
                mock.patch.object(
                    runner,
                    "_published_protocol_context",
                    return_value=self.protocol_context,
                ),
                mock.patch.object(
                    runner,
                    "_require_aligned_merged_master",
                    side_effect=RuntimeError("implementation not merged"),
                ),
                self.assertRaisesRegex(RuntimeError, "implementation not merged"),
            ):
                runner.run()
            self.assertFalse(output.exists())

    def test_check_rejects_late_result_swap(self) -> None:
        initial = protocol.artifact_json_bytes(self.result)
        with (
            mock.patch.object(
                runner,
                "_read_regular_file_once",
                side_effect=(initial, initial + b" "),
            ),
            mock.patch.object(
                runner,
                "_delegate_historical_check",
                return_value={"checked": True},
            ) as delegate_mock,
            self.assertRaisesRegex(RuntimeError, "changed during check"),
        ):
            runner.run(check=True)
        delegate_mock.assert_called_once_with(initial)

    def test_unified_state_rejects_late_result_route_changes(self) -> None:
        absent_implementation = {
            "result_present": False,
            "runner_plan_valid": True,
        }
        with (
            mock.patch.object(
                unified_validator.os.path,
                "lexists",
                side_effect=(False, True),
            ),
            mock.patch.object(
                unified_validator,
                "_validate_mm005_browser_research_generation_failure_investigation_protocol",
                return_value={},
            ),
            mock.patch.object(
                unified_validator,
                "_validate_mm005_browser_research_generation_failure_investigation_implementation",
                return_value=absent_implementation,
            ),
            self.assertRaisesRegex(
                unified_validator.GateError, "pre-result state changed"
            ),
        ):
            unified_validator._validate_mm005_browser_research_generation_failure_investigation_state()

        present_implementation = {
            "result_present": True,
            "protocol_frozen": True,
            "model_free": True,
            "diagnostic_records": 7,
            "target_record": protocol.TARGET_RECORD_ID,
            "next_gate": result_contract.DIAGNOSTIC_PROTOCOL_GATE_ID,
            "protocol_sha256": result_contract.PROTOCOL_SHA256,
        }
        with (
            mock.patch.object(
                unified_validator.os.path,
                "lexists",
                side_effect=(True, False),
            ),
            mock.patch.object(
                unified_validator,
                "_validate_mm005_browser_research_generation_failure_investigation_implementation",
                return_value=present_implementation,
            ),
            self.assertRaisesRegex(
                unified_validator.GateError, "historical result state changed"
            ),
        ):
            unified_validator._validate_mm005_browser_research_generation_failure_investigation_state()

    def test_formal_path_rejects_untrusted_slice_before_build_or_write(self) -> None:
        freeze_commit = "b" * 40
        with (
            mock.patch.object(
                runner,
                "_published_protocol_context",
                return_value=self.protocol_context,
            ),
            mock.patch.object(runner.os.path, "lexists", return_value=False),
            mock.patch.object(
                runner,
                "_require_aligned_merged_master",
                return_value=freeze_commit,
            ),
            mock.patch.object(
                runner,
                "_require_historical_implementation_introduction_commit",
            ) as introduction_mock,
            mock.patch.object(
                runner,
                "_require_historical_implementation_slice",
                side_effect=RuntimeError(
                    "historical implementation slice is not trusted"
                ),
            ) as slice_mock,
            mock.patch.object(
                runner,
                "_implementation_source_context",
                side_effect=AssertionError("untrusted slice reached result build"),
            ),
            mock.patch.object(
                runner,
                "_write_exclusive_result",
                side_effect=AssertionError("untrusted slice reached result write"),
            ) as write_mock,
            self.assertRaisesRegex(RuntimeError, "slice is not trusted"),
        ):
            runner.run(executed_at_utc="2026-08-29T12:34:56Z")

        introduction_mock.assert_called_once_with(freeze_commit)
        slice_mock.assert_called_once_with(freeze_commit)
        write_mock.assert_not_called()

    def test_unified_present_result_uses_historical_check_without_plan(self) -> None:
        checked = {
            "checked": True,
            "diagnostic_records": 7,
            "gate_id": result_contract.GATE_ID,
            "implementation_freeze_commit": self.implementation_context[
                "freeze_commit"
            ],
            "model_free": True,
            "valid": True,
            "static_investigation_complete": True,
            "selected_outcome": result_contract.OUTCOME_PRECEDENCE[3],
            "runtime_root_cause_unresolved": True,
            "runtime_eligible": False,
            "next_gate": result_contract.DIAGNOSTIC_PROTOCOL_GATE_ID,
            "protocol_merge_commit": result_contract.PROTOCOL_MERGE_COMMIT,
            "protocol_sha256": result_contract.PROTOCOL_SHA256,
            "report_digest": self.result["report_digest"],
            "target_record": protocol.TARGET_RECORD_ID,
        }
        with (
            mock.patch.object(unified_validator.os.path, "lexists", return_value=True),
            mock.patch.object(runner, "run", return_value=checked) as run_mock,
        ):
            summary = unified_validator._validate_mm005_browser_research_generation_failure_investigation_implementation()

        run_mock.assert_called_once_with(check=True)
        self.assertFalse(summary["runner_plan_valid"])
        self.assertTrue(summary["runner_check_valid"])
        self.assertTrue(summary["result_present"])
        self.assertTrue(summary["result_valid"])

        for key, value in (
            ("next_gate", result_contract.STATIC_REMEDIATION_PROTOCOL_GATE_ID),
            ("target_record", "sha256:" + "0" * 64),
            ("report_digest", "not-a-receipt"),
        ):
            with (
                self.subTest(key=key),
                mock.patch.object(
                    unified_validator.os.path, "lexists", return_value=True
                ),
                mock.patch.object(
                    runner,
                    "run",
                    return_value={**checked, key: value},
                ),
                self.assertRaisesRegex(
                    unified_validator.GateError, "result check boundary mismatch"
                ),
            ):
                unified_validator._validate_mm005_browser_research_generation_failure_investigation_implementation()

        with (
            mock.patch.object(unified_validator.os.path, "lexists", return_value=True),
            mock.patch.object(
                unified_validator,
                "_validate_mm005_browser_research_generation_failure_investigation_protocol",
                side_effect=AssertionError("present result ran current protocol"),
            ),
            mock.patch.object(
                unified_validator,
                "_validate_mm005_browser_research_generation_failure_investigation_implementation",
                return_value=summary,
            ),
        ):
            protocol_summary, implementation_summary = (
                unified_validator._validate_mm005_browser_research_generation_failure_investigation_state()
            )
        self.assertIs(implementation_summary, summary)
        self.assertTrue(protocol_summary["protocol_frozen"])
        self.assertFalse(protocol_summary["investigation_executed"])

    def test_formal_execution_requires_clean_aligned_master(self) -> None:
        commit = "b" * 40
        with (
            mock.patch.object(
                runner, "_git_text", side_effect=("master", commit, commit)
            ),
            mock.patch.object(
                runner,
                "_git_process",
                return_value=mock.Mock(returncode=0, stdout=b" M AGENTS.md\n"),
            ),
            self.assertRaisesRegex(RuntimeError, "clean worktree"),
        ):
            runner._require_aligned_merged_master()
        with (
            mock.patch.object(
                runner, "_git_text", side_effect=("master", commit, commit)
            ),
            mock.patch.object(
                runner,
                "_git_process",
                return_value=mock.Mock(returncode=0, stdout=b""),
            ),
        ):
            self.assertEqual(runner._require_aligned_merged_master(), commit)

    def test_exclusive_write_never_overwrites_and_bound_reads_reject_links(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "baseline").mkdir()
            output = root / "baseline" / "result.json"
            with (
                mock.patch.object(runner, "ROOT", root),
                mock.patch.object(
                    result_contract, "RESULT_PATH", "baseline/result.json"
                ),
            ):
                runner._write_exclusive_result(output, b"{}\n")
                self.assertEqual(output.read_bytes(), b"{}\n")
                with self.assertRaises(FileExistsError):
                    runner._write_exclusive_result(output, b"changed\n")
                self.assertEqual(output.read_bytes(), b"{}\n")

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
                runner._read_regular_file_once(linked)
            with (
                mock.patch.object(Path, "is_symlink", return_value=True),
                self.assertRaises(RuntimeError),
            ):
                runner._read_regular_file_once(original)

    def test_unsafe_repository_paths_are_rejected(self) -> None:
        for relative in ("", "../outside", "/absolute", "a\\b", "a/./b"):
            with self.subTest(relative=relative), self.assertRaises(RuntimeError):
                runner._validate_repository_relative_path(relative)

    def test_result_does_not_repeat_private_attempt_identity(self) -> None:
        inputs = protocol_builder.protocol_inputs()
        owner = protocol.parse_strict_json_bytes(
            inputs["attempt_owner_payload"], location="$.attempt_owner"
        )
        attempt_id = owner["attempt_id"]
        self.assertIsInstance(attempt_id, str)
        self.assertNotIn(
            attempt_id.encode("utf-8"), protocol.artifact_json_bytes(self.result)
        )

    def test_implementation_sources_have_no_model_network_or_retry_capability(
        self,
    ) -> None:
        imported: set[str] = set()
        called_attributes: set[str] = set()
        called_names: set[str] = set()
        for relative in (
            result_contract.IMPLEMENTATION_SOURCE_PATHS["result_contract"],
            result_contract.IMPLEMENTATION_SOURCE_PATHS["result_runner"],
        ):
            tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported.add(node.module.split(".")[0])
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute):
                        called_attributes.add(node.func.attr)
                    elif isinstance(node.func, ast.Name):
                        called_names.add(node.func.id)
        self.assertTrue(
            imported.isdisjoint(
                {
                    "torch",
                    "transformers",
                    "peft",
                    "bitsandbytes",
                    "PIL",
                    "socket",
                    "urllib",
                    "requests",
                }
            )
        )
        self.assertTrue(
            called_attributes.isdisjoint(
                {
                    "generate",
                    "apply_chat_template",
                    "from_pretrained",
                    "synchronize",
                    "create_connection",
                    "urlopen",
                    "request",
                }
            )
        )
        self.assertNotIn("retry", called_names)


if __name__ == "__main__":
    unittest.main()
