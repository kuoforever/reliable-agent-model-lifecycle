from __future__ import annotations

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

from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_model_evaluation as protocol,
)
from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_model_evaluation_failure_classification as failure,
)

ARTIFACT = ROOT / failure.ARTIFACT_PATH


class MM005BrowserResearchModelEvaluationFailureClassificationTests(
    unittest.TestCase
):
    def load_artifact(self) -> dict[str, object]:
        value = protocol.parse_strict_json_bytes(
            ARTIFACT.read_bytes(), location="$.failure_classification"
        )
        self.assertIsInstance(value, dict)
        return value

    def test_artifact_recomputes_exactly(self) -> None:
        artifact = self.load_artifact()
        self.assertEqual(failure.build_failure_classification(ROOT), artifact)
        self.assertEqual(
            failure.validate_failure_classification(ROOT, artifact), artifact
        )

    def test_owner_only_attempt_is_bound_without_repeating_attempt_id(self) -> None:
        artifact = self.load_artifact()
        owner = artifact["attempt_owner"]
        self.assertIsInstance(owner, dict)
        self.assertEqual(owner["bytes"], failure.ATTEMPT_OWNER_BYTES)
        self.assertEqual(owner["sha256"], failure.ATTEMPT_OWNER_SHA256)
        self.assertTrue(owner["contract_valid"])
        self.assertFalse(owner["attempt_id_repeated_in_classification"])
        self.assertNotIn("attempt_id", owner)
        attempt = artifact["attempt"]
        self.assertIsInstance(attempt, dict)
        self.assertEqual(attempt["directory_entries_observed"], ["attempt-owner.json"])
        self.assertFalse(attempt["failure_receipt_present"])
        self.assertEqual(attempt["exact_execution_progress"], "unknown")

    def test_local_owner_tree_is_checked_when_present(self) -> None:
        result = failure.verify_local_attempt_owner_if_present(ROOT)
        self.assertTrue(result["tracked_owner_valid"])
        self.assertEqual(result["expected_entries"], ["attempt-owner.json"])
        local_path = ROOT / failure.LOCAL_ATTEMPT_OWNER_PATH
        self.assertEqual(result["local_directory_present"], local_path.exists())
        with tempfile.TemporaryDirectory() as directory:
            clean_root = Path(directory)
            self._copy_owner_inputs(clean_root, include_local=False)
            clean_result = failure.verify_local_attempt_owner_if_present(clean_root)
        self.assertFalse(clean_result["local_directory_present"])
        self.assertTrue(clean_result["tracked_owner_valid"])
        self.assertEqual(clean_result["owner"]["sha256"], failure.ATTEMPT_OWNER_SHA256)

    def test_local_owner_tree_rejects_extra_terminal_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp_root = Path(directory)
            self._copy_owner_inputs(temp_root)
            extra = temp_root / protocol.RUN_OUTPUT_ROOT / "failure.json"
            extra.write_bytes(b"{}\n")
            with self.assertRaises(protocol.MM005ModelEvaluationError) as raised:
                failure.verify_local_attempt_owner_if_present(temp_root)
        self.assertEqual(raised.exception.code, "UNEXPECTED_LOCAL_ATTEMPT_ENTRIES")

    def test_hardlinked_bound_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.json"
            linked = root / "linked.json"
            source.write_bytes(b"{}\n")
            os.link(source, linked)
            with self.assertRaises(protocol.MM005ModelEvaluationError) as raised:
                failure._read_regular_file(linked, "hardlinked test file")
        self.assertEqual(raised.exception.code, "UNSAFE_BOUND_FILE")

    def test_freeze_reader_uses_cat_file_blob(self) -> None:
        completed = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=b"payload", stderr=b""
        )
        with mock.patch.object(
            failure.subprocess, "run", return_value=completed
        ) as run:
            payload = failure._read_git_blob(
                ROOT,
                failure.PROTOCOL_FREEZE_COMMIT,
                protocol.PREREGISTRATION_PATH,
            )
        self.assertEqual(payload, b"payload")
        command = run.call_args.args[0]
        self.assertEqual(command[0:3], ["git", "cat-file", "blob"])
        self.assertNotIn("show", command)

    def test_freeze_blob_drift_is_rejected(self) -> None:
        original = failure._read_git_blob

        def tamper(root: Path, commit: str, relative_path: str) -> bytes:
            payload = original(root, commit, relative_path)
            if relative_path == protocol.PREREGISTRATION_PATH:
                return payload + b"drift"
            return payload

        with mock.patch.object(failure, "_read_git_blob", side_effect=tamper):
            with self.assertRaises(protocol.MM005ModelEvaluationError) as raised:
                failure.build_failure_classification(ROOT)
        self.assertEqual(raised.exception.code, "FROZEN_PREREGISTRATION_MISMATCH")

    def test_claims_and_v2_recovery_remain_fail_closed(self) -> None:
        artifact = self.load_artifact()
        self.assertFalse(artifact["formal_gate_passed"])
        claims = artifact["claims"]
        self.assertIsInstance(claims, dict)
        self.assertTrue(claims["evaluation_execution_attempted"])
        self.assertTrue(claims["attempt_consumed"])
        for name, value in claims.items():
            if name not in {"evaluation_execution_attempted", "attempt_consumed"}:
                self.assertIs(value, False, name)
        recovery = artifact["locked_next_action"]
        self.assertIsInstance(recovery, dict)
        self.assertEqual(recovery["gate_id"], failure.NEXT_GATE_ID)
        self.assertEqual(
            recovery["execution_gate_id"], failure.RECOVERY_EXECUTION_GATE_ID
        )
        self.assertEqual(recovery["experiment_id"], failure.RECOVERY_EXPERIMENT_ID)
        self.assertTrue(recovery["new_experiment_not_v1_retry"])
        self.assertIn("candidate", recovery["v1_subtrees_exactly_preserved"])
        self.assertIn("decision", recovery["v1_subtrees_exactly_preserved"])
        self.assertIn(
            "freeze_preconditions", recovery["v1_subtrees_exactly_preserved"]
        )
        self.assertEqual(
            recovery["required_v2_values"][
                "mm005_browser_research_model_evaluation_protocol_version"
            ],
            2,
        )
        self.assertFalse(
            recovery["allowed_v2_differences"][
                "other_candidate_data_prompt_verifier_metric_or_resource_changes"
            ]
        )

    def test_artifact_drift_is_rejected(self) -> None:
        artifact = copy.deepcopy(self.load_artifact())
        artifact["formal_gate_passed"] = True
        with self.assertRaises(protocol.MM005ModelEvaluationError) as raised:
            failure.validate_failure_classification(ROOT, artifact)
        self.assertEqual(raised.exception.code, "FAILURE_CLASSIFICATION_MISMATCH")

    @staticmethod
    def _copy_owner_inputs(temp_root: Path, *, include_local: bool = True) -> None:
        relative_paths = [
            protocol.PREREGISTRATION_PATH,
            failure.TRACKED_ATTEMPT_OWNER_PATH,
        ]
        if include_local:
            relative_paths.append(failure.LOCAL_ATTEMPT_OWNER_PATH)
        for relative in relative_paths:
            source = ROOT / relative
            target = temp_root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())


if __name__ == "__main__":
    unittest.main()
