from __future__ import annotations

import ast
import copy
import json
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
    mm005_browser_research_model_evaluation_generation_failure_diagnostic_protocol_v2 as protocol,
)
from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_model_evaluation_generation_failure_diagnostic_result_review_v2 as contract,
)
from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_model_evaluation_generation_failure_diagnostic_result_v2 as result_contract,
)
from scripts import (  # noqa: E402
    prepare_mm005_browser_research_model_evaluation_generation_failure_diagnostic_result_review_v2 as builder,
)
from scripts import (  # noqa: E402
    run_mm005_browser_research_model_evaluation_generation_failure_diagnostic_v2 as runner,
)
from scripts import validate_offline  # noqa: E402


class MM005GenerationFailureDiagnosticResultReviewV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.authority_payload = (
            ROOT / result_contract.EXECUTION_AUTHORITY_PATH
        ).read_bytes()
        cls.review_payload = (ROOT / contract.REVIEW_PATH).read_bytes()
        cls.review = contract.parse_and_validate_result_review(
            cls.review_payload, authority_payload=cls.authority_payload
        )
        cls.preregistration_payload = (
            ROOT / protocol.PREREGISTRATION_PATH
        ).read_bytes()
        cls.runtime_mode = validate_offline._mm005_diagnostic_v2_runtime_mode(
            runner._output_topology()  # noqa: SLF001
        )
        cls.claimed = None
        if cls.runtime_mode == "failure_terminal":
            authority_context = runner._optional_execution_authority_context(  # noqa: SLF001
                allow_runtime_state=True
            )
            if authority_context is None:
                raise RuntimeError("authority context missing")
            cls.claimed = runner._claimed_execution_snapshot(  # noqa: SLF001
                authority_context
            )

    @staticmethod
    def _builder_input_snapshot() -> dict[str, object]:
        return {
            "topology": {"failure": True},
            "authority_payload": b"authority",
            "preregistration_payload": b"protocol",
            "attempt_owner_payload": b"owner",
            "progress_payload": b"progress",
            "failure_payload": b"failure",
            "lifecycle_lease_payload": b"lease",
            "runtime_summary": {"valid": True},
        }

    def test_review_rebuilds_exactly_from_the_frozen_authority(self) -> None:
        rebuilt = contract.build_result_review(
            authority_payload=self.authority_payload
        )
        self.assertEqual(contract.artifact_json_bytes(rebuilt), self.review_payload)
        self.assertEqual(json.loads(self.review_payload), rebuilt)
        body = {key: value for key, value in rebuilt.items() if key != "report_digest"}
        self.assertEqual(
            rebuilt["report_digest"],
            contract.sha256_bytes(contract.artifact_json_bytes(body)),
        )

    def test_ignored_runtime_terminal_authenticates_without_execution(self) -> None:
        if self.runtime_mode != "failure_terminal":
            self.skipTest("ignored runtime artifacts are absent in a clean clone")
        rebuilt, summary = builder.validate_local_runtime_and_build_review()
        self.assertEqual(contract.artifact_json_bytes(rebuilt), self.review_payload)
        self.assertEqual(summary["event_count"], 2)
        self.assertEqual(summary["failure_scope"], "pre_record_lifecycle")
        self.assertEqual(summary["selected_outcome"], "diagnostic_inconclusive")
        self.assertTrue(summary["diagnostic_attempt_consumed"])
        self.assertFalse(summary["diagnostic_executed"])
        self.assertFalse(summary["model_evaluated"])
        self.assertFalse(summary["formal_measurement_complete"])
        self.assertFalse(summary["root_cause_established"])
        self.assertFalse(summary["retry_authorized"])

    def test_review_binds_exact_raw_receipts_but_copies_no_raw_content(self) -> None:
        artifacts = self.review["authenticated_artifacts"]
        expected = {
            "attempt_owner": (
                protocol.ATTEMPT_OWNER_PATH,
                contract.ATTEMPT_OWNER_BYTES,
                contract.ATTEMPT_OWNER_SHA256,
            ),
            "progress": (
                protocol.PROGRESS_PATH,
                contract.PROGRESS_BYTES,
                contract.PROGRESS_SHA256,
            ),
            "failure": (
                protocol.FAILURE_PATH,
                contract.FAILURE_BYTES,
                contract.FAILURE_SHA256,
            ),
            "lifecycle_lease": (
                protocol.LIFECYCLE_LEASE_PATH,
                contract.LIFECYCLE_LEASE_BYTES,
                contract.LIFECYCLE_LEASE_SHA256,
            ),
        }
        for name, (path, size, digest) in expected.items():
            with self.subTest(name=name):
                self.assertEqual(artifacts[name]["path"], path)
                self.assertEqual(artifacts[name]["bytes"], size)
                self.assertEqual(artifacts[name]["sha256"], digest)
                self.assertFalse(artifacts[name]["copied_into_review"])
        self.assertEqual(artifacts["tracked_raw_artifact_count"], 0)
        self.assertFalse(artifacts["runtime_artifacts_modified_by_review"])

    def test_terminal_and_claims_remain_narrow(self) -> None:
        terminal = self.review["authenticated_terminal"]
        claims = self.review["claims"]
        self.assertEqual(
            terminal["event_names"], ["attempt_claimed", "failure_terminal_ready"]
        )
        self.assertEqual(terminal["event_sequences"], [0, 1])
        self.assertEqual(terminal["completed_record_ids"], [])
        self.assertIsNone(terminal["active_record_id"])
        self.assertIsNone(terminal["observed_environment"])
        self.assertIsNone(terminal["resources"])
        self.assertEqual(terminal["exception_type"], "RuntimeError")
        self.assertTrue(claims["authenticated_failure_terminal_reviewed"])
        self.assertTrue(claims["formal_invocation_budget_spent"])
        self.assertTrue(claims["diagnostic_attempt_consumed"])
        for name in (
            "diagnostic_executed",
            "model_evaluated",
            "formal_measurement_complete",
            "historical_runtime_health_established",
            "failed_runtime_substage_isolated",
            "runtime_root_cause_established",
            "remediation_delta_established",
            "recovery_v3_justified",
            "quality_established",
            "safety_established",
            "serving_eligible",
            "promotion_eligible",
            "runtime_eligible",
        ):
            self.assertFalse(claims[name], name)

    def test_controller_observation_cannot_be_promoted_to_evidence(self) -> None:
        policy = self.review["evidence_policy"]
        self.assertTrue(
            policy["controller_observation_exists_outside_authenticated_artifacts"]
        )
        self.assertFalse(policy["controller_observation_content_copied"])
        self.assertFalse(policy["controller_observation_used_for_root_cause"])
        self.assertFalse(policy["controller_observation_used_for_remediation"])
        self.assertFalse(policy["exception_message_copied"])
        self.assertFalse(policy["traceback_copied"])
        self.assertFalse(policy["absolute_runtime_path_copied"])
        text = self.review_payload.decode("utf-8")
        for forbidden in (
            "isolated Python args",
            "dont_write_bytecode",
            "pycache_prefix",
            "C:\\\\Users",
            "C:/Users",
            "Traceback",
        ):
            self.assertNotIn(forbidden, text)

    def test_no_retry_recovery_or_automatic_successor_is_authorized(self) -> None:
        action = self.review["locked_next_action"]
        invocation = self.review["invocation"]
        self.assertEqual(invocation["formal_invocation_budget_remaining"], 0)
        self.assertFalse(invocation["retry_authorized"])
        self.assertFalse(invocation["same_identity_reinvocation_authorized"])
        self.assertEqual(action["action"], "stop_after_authenticated_result_review")
        self.assertIsNone(action["next_gate_id"])
        self.assertTrue(action["diagnostic_v2_chain_closed"])
        self.assertFalse(action["v2_retry_authorized"])
        self.assertFalse(action["automatic_recovery_authorized"])
        self.assertFalse(action["recovery_v3_authorized"])
        self.assertFalse(action["new_diagnostic_identity_authorized"])
        self.assertTrue(action["separate_roadmap_scope_selection_required"])

    def test_review_tampering_fails_closed(self) -> None:
        for path, replacement in (
            (("invocation", "formal_invocation_budget_remaining"), 1),
            (("claims", "diagnostic_executed"), True),
            (("claims", "runtime_root_cause_established"), True),
            (("locked_next_action", "v2_retry_authorized"), True),
        ):
            changed = copy.deepcopy(self.review)
            changed[path[0]][path[1]] = replacement
            with (
                self.subTest(path=path),
                self.assertRaises(
                    contract.MM005GenerationFailureDiagnosticResultReviewError
                ),
            ):
                contract.validate_result_review(
                    changed, authority_payload=self.authority_payload
                )

    def test_resealed_runtime_byte_tamper_fails_closed(self) -> None:
        if self.claimed is None:
            self.skipTest("ignored runtime artifacts are absent in a clean clone")
        owner_payload = self.claimed["owner_payload"]
        self.assertIsInstance(owner_payload, bytes)
        tampered = bytes(owner_payload) + b" "
        with self.assertRaises(
            contract.MM005GenerationFailureDiagnosticResultReviewError
        ):
            contract.validate_runtime_terminal(
                authority_payload=self.authority_payload,
                preregistration_payload=self.preregistration_payload,
                attempt_owner_payload=tampered,
                progress_payload=self.claimed["progress_payload"],
                failure_payload=self.claimed["terminal_payload"],
                lifecycle_lease_payload=(
                    ROOT / protocol.LIFECYCLE_LEASE_PATH
                ).read_bytes(),
                implementation_context=self.claimed["implementation_context"],
            )

    def test_builder_check_is_read_only_and_reports_the_stop_boundary(self) -> None:
        if self.runtime_mode != "failure_terminal":
            self.skipTest("ignored runtime artifacts are absent in a clean clone")
        tracked_before = self.review_payload
        runtime_before = {
            path: (ROOT / path).read_bytes()
            for path in (
                protocol.ATTEMPT_OWNER_PATH,
                protocol.PROGRESS_PATH,
                protocol.FAILURE_PATH,
                protocol.LIFECYCLE_LEASE_PATH,
            )
        }
        completed = subprocess.run(
            [sys.executable, "-I", str(Path(builder.__file__)), "--check"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
        summary = json.loads(completed.stdout)
        self.assertTrue(summary["result_review_gate_passed"])
        self.assertTrue(summary["diagnostic_attempt_consumed"])
        self.assertFalse(summary["diagnostic_executed"])
        self.assertFalse(summary["model_evaluated"])
        self.assertFalse(summary["root_cause_established"])
        self.assertFalse(summary["retry_authorized"])
        self.assertIsNone(summary["next_gate"])
        self.assertEqual((ROOT / contract.REVIEW_PATH).read_bytes(), tracked_before)
        for path, payload in runtime_before.items():
            self.assertEqual((ROOT / path).read_bytes(), payload)

    def test_builder_check_revalidates_inputs_after_final_output_check(self) -> None:
        payload = contract.artifact_json_bytes(self.review)
        original_read = builder._read_regular_file  # noqa: SLF001
        snapshot = self._builder_input_snapshot()
        drifted_snapshot = copy.deepcopy(snapshot)
        drifted_snapshot["progress_payload"] = b"changed-progress"
        input_drifted = False
        output_reads = 0

        def capture() -> tuple[dict[str, object], dict[str, object]]:
            current = drifted_snapshot if input_drifted else snapshot
            return self.review, current

        def read_then_drift(path: Path, *, max_bytes: int) -> bytes:
            nonlocal input_drifted, output_reads
            persisted = original_read(path, max_bytes=max_bytes)
            output_reads += 1
            if output_reads == 2:
                input_drifted = True
            return persisted

        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary)
            output_path = temporary_root / contract.REVIEW_PATH
            output_path.parent.mkdir(parents=True)
            output_path.write_bytes(payload)
            with (
                mock.patch.object(builder, "ROOT", temporary_root),
                mock.patch.object(builder, "_capture_review", side_effect=capture),
                mock.patch.object(
                    builder, "_read_regular_file", side_effect=read_then_drift
                ),
                self.assertRaisesRegex(
                    RuntimeError, "review input changed: progress_payload"
                ),
            ):
                builder.main(["--check"])
        self.assertEqual(output_reads, 2)

    def test_builder_create_rejects_replaced_persisted_output(self) -> None:
        payload = contract.artifact_json_bytes(self.review)
        tampered = b"[" + payload[1:]
        original_read = builder._read_regular_file  # noqa: SLF001
        snapshot = self._builder_input_snapshot()

        def replace_then_read(path: Path, *, max_bytes: int) -> bytes:
            replacement = path.with_name(f"{path.name}.replacement")
            replacement.write_bytes(tampered)
            os.replace(replacement, path)
            return original_read(path, max_bytes=max_bytes)

        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary)
            output_path = temporary_root / contract.REVIEW_PATH
            output_path.parent.mkdir(parents=True)
            with (
                mock.patch.object(builder, "ROOT", temporary_root),
                mock.patch.object(
                    builder,
                    "_capture_review",
                    return_value=(self.review, snapshot),
                ),
                mock.patch.object(
                    builder, "_read_regular_file", side_effect=replace_then_read
                ),
                self.assertRaisesRegex(RuntimeError, "persistence check"),
            ):
                builder.main([])
            self.assertEqual(output_path.read_bytes(), tampered)

    def test_builder_create_revalidates_inputs_after_persisted_readback(self) -> None:
        original_read = builder._read_regular_file  # noqa: SLF001
        snapshot = self._builder_input_snapshot()
        drifted_snapshot = copy.deepcopy(snapshot)
        drifted_snapshot["lifecycle_lease_payload"] = b"changed-lease"
        input_drifted = False

        def capture() -> tuple[dict[str, object], dict[str, object]]:
            current = drifted_snapshot if input_drifted else snapshot
            return self.review, current

        def read_then_drift(path: Path, *, max_bytes: int) -> bytes:
            nonlocal input_drifted
            persisted = original_read(path, max_bytes=max_bytes)
            input_drifted = True
            return persisted

        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary)
            output_path = temporary_root / contract.REVIEW_PATH
            output_path.parent.mkdir(parents=True)
            with (
                mock.patch.object(builder, "ROOT", temporary_root),
                mock.patch.object(builder, "_capture_review", side_effect=capture),
                mock.patch.object(
                    builder, "_read_regular_file", side_effect=read_then_drift
                ),
                self.assertRaisesRegex(
                    RuntimeError, "review input changed: lifecycle_lease_payload"
                ),
            ):
                builder.main([])
            self.assertEqual(
                output_path.read_bytes(), contract.artifact_json_bytes(self.review)
            )

    def test_slice_is_exactly_twelve_model_free_non_lfs_paths(self) -> None:
        self.assertEqual(len(contract.REVIEW_SLICE_PATHS), 12)
        self.assertEqual(
            self.review["publication"]["slice_paths"],
            sorted(contract.REVIEW_SLICE_PATHS),
        )
        self.assertEqual(
            self.review["publication"]["git_lfs_payload_bytes_required"], 0
        )
        heavy = {"PIL", "bitsandbytes", "peft", "torch", "transformers"}
        for relative in (
            "src/fullcycle_bridge/mm005_browser_research_model_evaluation_"
            "generation_failure_diagnostic_result_review_v2.py",
            "scripts/prepare_mm005_browser_research_model_evaluation_"
            "generation_failure_diagnostic_result_review_v2.py",
        ):
            tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
            imports = {
                alias.name.partition(".")[0]
                for node in ast.walk(tree)
                if isinstance(node, (ast.Import, ast.ImportFrom))
                for alias in node.names
            }
            self.assertTrue(heavy.isdisjoint(imports), relative)
        attributes = subprocess.run(
            ["git", "check-attr", "filter", "--", contract.REVIEW_PATH],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        self.assertIn("unspecified", attributes)

    def test_unified_runtime_mode_accepts_only_absent_or_exact_failure(self) -> None:
        absent = {
            "execution_authority": True,
            "output_parent": False,
            "output_root": False,
            "attempt_owner": False,
            "progress": False,
            "success_result": False,
            "failure": False,
            "lifecycle_lease_root": False,
            "lifecycle_lease": False,
            "reserved_sibling_staging": False,
        }
        failure = {
            **absent,
            "output_parent": True,
            "output_root": True,
            "attempt_owner": True,
            "progress": True,
            "failure": True,
            "lifecycle_lease_root": True,
            "lifecycle_lease": True,
        }
        self.assertEqual(
            validate_offline._mm005_diagnostic_v2_runtime_mode(absent), "absent"
        )
        self.assertEqual(
            validate_offline._mm005_diagnostic_v2_runtime_mode(failure),
            "failure_terminal",
        )
        partial = {**failure, "progress": False}
        with self.assertRaises(validate_offline.GateError):
            validate_offline._mm005_diagnostic_v2_runtime_mode(partial)

    def test_pre_execution_test_skip_policy_is_exact_and_restores_markers(
        self,
    ) -> None:
        suite = unittest.defaultTestLoader.discover(str(validate_offline.TESTS))
        marker_state, spent_skips, historical_skips = (
            validate_offline._prepare_mm005_diagnostic_v2_test_skips(
                suite,
                authenticated_spent_diagnostic_terminal=True,
                historical_execution_authority=False,
            )
        )
        self.assertEqual(spent_skips, 29)
        self.assertEqual(historical_skips, 0)
        self.assertEqual(len(marker_state), 22)
        baseline = [
            (target, name, existed, value)
            for target, name, existed, value in marker_state
        ]
        validate_offline._restore_unittest_skip_markers(marker_state)
        for target, name, existed, value in baseline:
            with self.subTest(restored=name, target=id(target)):
                if existed:
                    self.assertEqual(getattr(target, name), value)
                else:
                    self.assertNotIn(name, vars(target))

        historical_state, spent_skips, historical_skips = (
            validate_offline._prepare_mm005_diagnostic_v2_test_skips(
                suite,
                authenticated_spent_diagnostic_terminal=False,
                historical_execution_authority=True,
            )
        )
        self.assertEqual(spent_skips, 0)
        self.assertEqual(historical_skips, 8)
        self.assertEqual(len(historical_state), 16)
        validate_offline._restore_unittest_skip_markers(historical_state)

        self.assertEqual(
            validate_offline._prepare_mm005_diagnostic_v2_test_skips(
                suite,
                authenticated_spent_diagnostic_terminal=False,
                historical_execution_authority=False,
            ),
            ([], 0, 0),
        )

        original_set_marker = validate_offline._set_unittest_skip_marker
        calls = 0

        def fail_after_second_marker(
            target: type[unittest.TestCase] | object,
            *,
            reason: str,
            marker_state: list[tuple[object, str, bool, object]],
        ) -> None:
            nonlocal calls
            original_set_marker(
                target, reason=reason, marker_state=marker_state
            )
            calls += 1
            if calls == 2:
                raise RuntimeError("controlled marker failure")

        with (
            mock.patch.object(
                validate_offline,
                "_set_unittest_skip_marker",
                side_effect=fail_after_second_marker,
            ),
            self.assertRaisesRegex(RuntimeError, "controlled marker failure"),
        ):
            validate_offline._prepare_mm005_diagnostic_v2_test_skips(
                suite,
                authenticated_spent_diagnostic_terminal=True,
                historical_execution_authority=False,
            )
        for target, name, existed, value in baseline:
            with self.subTest(failure_restored=name, target=id(target)):
                if existed:
                    self.assertEqual(getattr(target, name), value)
                else:
                    self.assertNotIn(name, vars(target))

    def test_unified_review_has_truthful_clean_clone_mode(self) -> None:
        absent = {
            "execution_authority": True,
            "output_parent": False,
            "output_root": False,
            "attempt_owner": False,
            "progress": False,
            "success_result": False,
            "failure": False,
            "lifecycle_lease_root": False,
            "lifecycle_lease": False,
            "reserved_sibling_staging": False,
        }
        with mock.patch.object(runner, "_output_topology", return_value=absent):
            summary = validate_offline._validate_mm005_browser_research_generation_failure_diagnostic_result_review_v2()
        self.assertTrue(summary["result_review_valid"])
        self.assertFalse(summary["raw_runtime_artifacts_revalidated"])
        self.assertFalse(summary["diagnostic_executed"])
        self.assertFalse(summary["root_cause_established"])
        self.assertEqual(summary["git_lfs_payload_bytes_required"], 0)

        pre_review_authority = {
            "authority_valid": True,
            "authority_tracked_at_head": True,
            "head_is_authority_introduction_commit": False,
            "diagnostic_execution_authorized": True,
            "formal_execution_eligible": False,
            "diagnostic_attempt_consumed": False,
            "diagnostic_executed": False,
            "next_gate": result_contract.EXECUTION_GATE_ID,
        }
        closed = (
            validate_offline._close_mm005_diagnostic_v2_authority_state_from_result_review(
                pre_review_authority, summary
            )
        )
        self.assertTrue(closed["published_authority_initially_authorized"])
        self.assertFalse(closed["raw_runtime_terminal_revalidated"])
        self.assertEqual(
            closed["effective_state_source"], "authenticated_tracked_result_review"
        )
        self.assertFalse(closed["diagnostic_execution_authorized"])
        self.assertFalse(closed["formal_execution_eligible"])
        self.assertTrue(closed["diagnostic_attempt_consumed"])
        self.assertFalse(closed["diagnostic_executed"])
        self.assertIsNone(closed["next_gate"])

        valid_spent_authority = {
            **pre_review_authority,
            "diagnostic_attempt_consumed": True,
            "next_gate": contract.GATE_ID,
        }
        spent_review = {**summary, "raw_runtime_artifacts_revalidated": True}
        spent_closed = (
            validate_offline._close_mm005_diagnostic_v2_authority_state_from_result_review(
                valid_spent_authority, spent_review
            )
        )
        self.assertTrue(spent_closed["raw_runtime_terminal_revalidated"])

        contradictory_pre_close_tuples = (
            ({"diagnostic_executed": True}, summary),
            ({"next_gate": contract.GATE_ID}, summary),
            (
                {
                    "diagnostic_attempt_consumed": True,
                    "next_gate": result_contract.EXECUTION_GATE_ID,
                },
                spent_review,
            ),
        )
        for authority_changes, review_state in contradictory_pre_close_tuples:
            with (
                self.subTest(authority_changes=authority_changes),
                self.assertRaisesRegex(
                    validate_offline.GateError,
                    "effective authority state mismatch",
                ),
            ):
                validate_offline._close_mm005_diagnostic_v2_authority_state_from_result_review(
                    {**pre_review_authority, **authority_changes}, review_state
                )

        contradictory = dict(summary)
        contradictory["retry_authorized"] = True
        with self.assertRaisesRegex(
            validate_offline.GateError,
            "effective authority state mismatch",
        ):
            validate_offline._close_mm005_diagnostic_v2_authority_state_from_result_review(
                pre_review_authority, contradictory
            )

        contradictory_raw_state = dict(summary)
        contradictory_raw_state["raw_runtime_artifacts_revalidated"] = True
        with self.assertRaisesRegex(
            validate_offline.GateError,
            "effective authority state mismatch",
        ):
            validate_offline._close_mm005_diagnostic_v2_authority_state_from_result_review(
                pre_review_authority, contradictory_raw_state
            )

        first_snapshot = {
            "topology": absent,
            "authority_payload": b"authority",
            "preregistration_payload": b"protocol",
            "attempt_owner_payload": b"owner",
            "progress_payload": b"progress",
            "failure_payload": b"failure",
            "lifecycle_lease_payload": b"lease",
            "runtime_summary": {"valid": True},
        }
        drifted_snapshot = dict(first_snapshot)
        drifted_snapshot["progress_payload"] = b"changed-progress"
        with (
            mock.patch.object(
                builder,
                "_capture_review",
                side_effect=(
                    (self.review, first_snapshot),
                    (self.review, drifted_snapshot),
                ),
            ),
            self.assertRaisesRegex(
                RuntimeError, "review input changed: progress_payload"
            ),
        ):
            builder.validate_local_runtime_and_build_review()


if __name__ == "__main__":
    unittest.main()
