from __future__ import annotations

import ast
import copy
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

sys.path.insert(0, str(SRC))

from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_model_evaluation_failure_classification_v2 as failure,
)
from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_model_evaluation_protocol_v2 as protocol,
)

ARTIFACT = ROOT / failure.ARTIFACT_PATH


class MM005BrowserResearchModelEvaluationFailureClassificationV2Tests(
    unittest.TestCase
):
    def _artifact(self) -> dict[str, object]:
        return protocol.parse_strict_json_bytes(
            ARTIFACT.read_bytes(), location="$.failure_classification"
        )

    def test_artifact_recomputes_exactly(self) -> None:
        artifact = self._artifact()
        self.assertEqual(failure.build_failure_classification(ROOT), artifact)
        self.assertEqual(
            failure.validate_failure_classification(ROOT, artifact), artifact
        )
        self.assertEqual(protocol.artifact_json_bytes(artifact), ARTIFACT.read_bytes())

    def test_three_raw_artifacts_are_exactly_bound(self) -> None:
        raw = self._artifact()["raw_artifacts"]
        self.assertIsInstance(raw, dict)
        assert isinstance(raw, dict)
        expected = {
            "attempt_owner": (
                failure.TRACKED_ATTEMPT_OWNER_PATH,
                failure.ATTEMPT_OWNER_BYTES,
                failure.ATTEMPT_OWNER_SHA256,
            ),
            "progress": (
                failure.TRACKED_PROGRESS_PATH,
                failure.PROGRESS_BYTES,
                failure.PROGRESS_SHA256,
            ),
            "failure": (
                failure.TRACKED_FAILURE_PATH,
                failure.FAILURE_BYTES,
                failure.FAILURE_SHA256,
            ),
        }
        for name, (path, size, digest) in expected.items():
            binding = raw[name]
            self.assertIsInstance(binding, dict)
            assert isinstance(binding, dict)
            self.assertEqual(binding["path"], path)
            self.assertEqual(binding["bytes"], size)
            self.assertEqual(binding["sha256"], digest)
            self.assertTrue(binding["contract_valid"])

    def test_authenticated_progress_boundary_is_exact(self) -> None:
        artifact = self._artifact()
        progress = artifact["authenticated_progress"]
        self.assertIsInstance(progress, dict)
        assert isinstance(progress, dict)
        self.assertEqual(progress["event_count"], failure.EXPECTED_EVENT_COUNT)
        self.assertEqual(
            progress["terminal_sequence"], failure.EXPECTED_EVENT_COUNT - 1
        )
        self.assertEqual(progress["last_event"], "failure_terminal_ready")
        self.assertEqual(progress["active_record_id"], failure.FAILED_RECORD_ID)
        self.assertFalse(progress["active_record_durable_completion"])
        self.assertEqual(
            progress["completed_record_ids"], list(failure.COMPLETED_RECORD_IDS)
        )
        self.assertEqual(progress["counters"], failure.EXPECTED_COUNTERS)

    def test_failure_and_claims_remain_fail_closed(self) -> None:
        artifact = self._artifact()
        observed_failure = artifact["failure"]
        claims = artifact["claims"]
        self.assertIsInstance(observed_failure, dict)
        self.assertIsInstance(claims, dict)
        assert isinstance(observed_failure, dict)
        assert isinstance(claims, dict)
        self.assertEqual(observed_failure["stage"], "generation")
        self.assertEqual(observed_failure["exception_type"], "RuntimeError")
        self.assertFalse(observed_failure["root_cause_authenticated"])
        for name, value in observed_failure.items():
            if name.endswith("_cause_attributed"):
                self.assertFalse(value, name)
        self.assertTrue(claims["attempt_consumed"])
        self.assertTrue(claims["authenticated_partial_generation_progress"])
        self.assertEqual(claims["completed_generate_calls"], 3)
        self.assertTrue(claims["fourth_generation_attempt_started"])
        for name in (
            "evaluation_executed",
            "formal_measurement_complete",
            "model_evaluated",
            "evaluation_result_available",
            "quality_established",
            "safety_established",
            "serving_eligible",
            "promotion_eligible",
            "runtime_eligible",
        ):
            self.assertFalse(claims[name], name)

    def test_controller_cuda_text_is_explicitly_non_authenticated(self) -> None:
        observation = self._artifact()[
            "transient_non_authenticated_controller_observation"
        ]
        self.assertIsInstance(observation, dict)
        assert isinstance(observation, dict)
        self.assertTrue(observation["cuda_illegal_memory_access_text_seen"])
        self.assertFalse(observation["captured_in_protocol_artifact"])
        self.assertFalse(observation["exception_message_or_traceback_persisted"])
        self.assertFalse(observation["formal_cause_derived_from_observation"])

    def test_attempt_id_is_not_repeated_in_derived_classification(self) -> None:
        context = failure.load_tracked_failure_context(ROOT)
        owner = context["owner"]
        self.assertIsInstance(owner, dict)
        assert isinstance(owner, dict)
        attempt_id = owner["attempt_id"]
        self.assertIsInstance(attempt_id, str)
        assert isinstance(attempt_id, str)
        self.assertNotIn(attempt_id.encode("utf-8"), ARTIFACT.read_bytes())

    def test_local_consumed_tree_is_checked_when_present(self) -> None:
        result = failure.verify_local_consumed_tree_if_present(ROOT)
        self.assertEqual(
            result["expected_entries"], list(failure.EXPECTED_LOCAL_ENTRIES)
        )
        self.assertTrue(result["tracked_artifacts_valid"])

    def test_local_tree_rejects_an_extra_artifact(self) -> None:
        context = failure.load_tracked_failure_context(ROOT)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / protocol.RUN_OUTPUT_ROOT
            output.mkdir(parents=True)
            lifecycle = root / protocol.LIFECYCLE_LEASE_PATH
            lifecycle.parent.mkdir(parents=True)
            lifecycle.write_bytes(protocol.LIFECYCLE_LEASE_MARKER)
            payload_names = {
                "attempt-owner.json": "owner_payload",
                "progress.json": "progress_payload",
                "failure.json": "failure_payload",
            }
            for name, key in payload_names.items():
                payload = context[key]
                self.assertIsInstance(payload, bytes)
                assert isinstance(payload, bytes)
                (output / name).write_bytes(payload)
            (output / "evidence.json").write_bytes(b"{}\n")
            with (
                mock.patch.object(
                    failure, "load_tracked_failure_context", return_value=context
                ),
                self.assertRaises(protocol.MM005BrowserResearchRecoveryError),
            ):
                failure.verify_local_consumed_tree_if_present(root)

    @unittest.skipUnless(hasattr(os, "link"), "hardlink support required")
    def test_hardlinked_tracked_artifact_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = root / "original.json"
            linked = root / "linked.json"
            original.write_bytes(b"{}\n")
            try:
                os.link(original, linked)
            except OSError as exc:
                self.skipTest(f"hardlinks unavailable: {exc}")
            with self.assertRaises(protocol.MM005BrowserResearchRecoveryError):
                failure._read_regular_file(linked, "hardlinked artifact")

    def test_tracked_progress_tamper_is_rejected(self) -> None:
        original = failure._read_regular_file

        def changed(path: Path, label: str) -> bytes:
            payload = original(path, label)
            if path == ROOT / failure.TRACKED_PROGRESS_PATH:
                return payload[:-1] + b" "
            return payload

        with (
            mock.patch.object(failure, "_read_regular_file", side_effect=changed),
            self.assertRaises(protocol.MM005BrowserResearchRecoveryError),
        ):
            failure.load_tracked_failure_context(ROOT)

    def test_freeze_blob_drift_is_rejected(self) -> None:
        original = failure._read_git_blob

        def changed(root: Path, commit: str, relative: str) -> bytes:
            payload = original(root, commit, relative)
            if relative == protocol.PREREGISTRATION_PATH:
                return payload + b" "
            return payload

        with (
            mock.patch.object(failure, "_read_git_blob", side_effect=changed),
            self.assertRaises(protocol.MM005BrowserResearchRecoveryError),
        ):
            failure.load_tracked_failure_context(ROOT)

    def test_artifact_drift_is_rejected(self) -> None:
        changed = copy.deepcopy(self._artifact())
        changed["formal_gate_passed"] = True
        with self.assertRaises(protocol.MM005BrowserResearchRecoveryError):
            failure.validate_failure_classification(ROOT, changed)

    def test_bool_integer_type_drift_is_rejected(self) -> None:
        artifact = self._artifact()
        for path, replacement in (
            (("formal_gate_passed",), 0),
            (("attempt", "attempt_consumed"), 1),
        ):
            changed = copy.deepcopy(artifact)
            target = changed
            for key in path[:-1]:
                nested = target[key]
                self.assertIsInstance(nested, dict)
                assert isinstance(nested, dict)
                target = nested
            target[path[-1]] = replacement
            self.assertEqual(changed, artifact)
            with self.assertRaises(protocol.MM005BrowserResearchRecoveryError):
                failure.validate_failure_classification(ROOT, changed)

    def test_next_gate_is_model_free_investigation_not_retry(self) -> None:
        action = self._artifact()["locked_next_action"]
        self.assertIsInstance(action, dict)
        assert isinstance(action, dict)
        self.assertEqual(action["gate_id"], failure.NEXT_GATE_ID)
        self.assertTrue(action["protocol_freeze_is_model_free"])
        self.assertFalse(action["model_or_cuda_execution_authorized_by_classification"])
        constraints = action["constraints"]
        self.assertIsInstance(constraints, dict)
        assert isinstance(constraints, dict)
        self.assertFalse(constraints["v2_execution_retried"])
        self.assertFalse(constraints["runtime_integration"])

    def test_classifier_has_no_model_network_recovery_or_retry_capability(self) -> None:
        paths = [
            ROOT
            / "src/fullcycle_bridge/mm005_browser_research_model_evaluation_failure_classification_v2.py",
            ROOT
            / "scripts/classify_mm005_browser_research_model_evaluation_failure_v2.py",
        ]
        imported: set[str] = set()
        source = ""
        for path in paths:
            text = path.read_text(encoding="utf-8")
            source += text
            tree = ast.parse(text)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported.add(node.module.split(".")[0])
        self.assertTrue(
            imported.isdisjoint(
                {"torch", "transformers", "peft", "bitsandbytes", "socket", "urllib"}
            )
        )
        for forbidden in (
            "execute_frozen_protocol",
            "_load_eval_dependencies",
            "model.generate",
            "cuda.",
            "create_connection",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
