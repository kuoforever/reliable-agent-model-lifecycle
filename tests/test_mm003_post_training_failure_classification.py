from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from fullcycle_bridge import mm003_post_training_failure_classification as failure  # noqa: E402
from fullcycle_bridge import mm003_post_training_protocol as protocol  # noqa: E402

ARTIFACT = ROOT / failure.ARTIFACT_PATH


class MM003PostTrainingFailureClassificationTests(unittest.TestCase):
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

    def test_exact_failure_receipt_and_directory_are_bound(self) -> None:
        artifact = self.load_artifact()
        receipt = artifact["failure_receipt"]
        self.assertIsInstance(receipt, dict)
        self.assertEqual(receipt["bytes"], failure.FAILURE_RECEIPT_BYTES)
        self.assertEqual(receipt["sha256"], failure.FAILURE_RECEIPT_SHA256)
        self.assertEqual(receipt["directory_entries_observed"], ["failure.json"])
        content = receipt["content"]
        self.assertIsInstance(content, dict)
        self.assertEqual(content["retry_count"], 0)
        self.assertFalse(content["formal_gate_passed"])
        if (ROOT / failure.LOCAL_FAILURE_RECEIPT_PATH).exists():
            self.assertEqual(failure.verify_local_failure_receipt(ROOT), receipt)

    def test_static_root_cause_reproduces_all_records(self) -> None:
        artifact = self.load_artifact()
        diagnosis = artifact["failure"]
        self.assertIsInstance(diagnosis, dict)
        reproduction = diagnosis["static_reproduction"]
        self.assertIsInstance(reproduction, dict)
        self.assertEqual(reproduction["first_case_id"], "pt-train-018")
        self.assertEqual(reproduction["first_case_observation_mode"], "fused")
        self.assertEqual(reproduction["records_checked"], 27)
        self.assertEqual(reproduction["records_failed"], 27)
        self.assertEqual(reproduction["code"], "CASE_MODE_MISMATCH")
        self.assertEqual(reproduction["location"], "$.case")
        self.assertEqual(reproduction["tracked_fixture_receipts_verified"], 2)
        self.assertFalse(diagnosis["training_fixture_mode_invalid"])

    def test_static_reproduction_reads_the_tracked_fixtures(self) -> None:
        original = failure._read_regular_file

        def tamper(path: Path, label: str) -> bytes:
            payload = original(path, label)
            if path == ROOT / protocol.TRAIN_DATASET_PATH:
                return payload.replace(b'"pt-train-001"', b'"pt-train-999"', 1)
            return payload

        with mock.patch.object(failure, "_read_regular_file", side_effect=tamper):
            with self.assertRaises(protocol.MM003PostTrainingProtocolError) as raised:
                failure.build_failure_classification(ROOT)
        self.assertEqual(raised.exception.code, "DATASET_RECEIPT_BINDING_MISMATCH")

    def test_failure_boundary_and_next_gate_remain_fail_closed(self) -> None:
        artifact = self.load_artifact()
        self.assertFalse(artifact["formal_gate_passed"])
        claims = artifact["claims"]
        self.assertIsInstance(claims, dict)
        self.assertTrue(claims["post_training_execution_attempted"])
        for key, value in claims.items():
            if key != "post_training_execution_attempted":
                self.assertIs(value, False, key)
        action = artifact["locked_next_action"]
        self.assertIsInstance(action, dict)
        self.assertEqual(action["gate_id"], failure.NEXT_GATE_ID)
        self.assertEqual(
            action["execution_gate_id"], failure.RECOVERY_EXECUTION_GATE_ID
        )
        self.assertEqual(action["experiment_id"], failure.RECOVERY_EXPERIMENT_ID)
        self.assertEqual(
            action["output_directory"], failure.RECOVERY_OUTPUT_DIRECTORY
        )
        self.assertEqual(
            action["success_next_gate_id"],
            failure.RECOVERY_SUCCESS_NEXT_GATE_ID,
        )
        self.assertIn("resource_caps", action["v1_sections_exactly_preserved"])
        policy = action["allowed_difference_policy"]
        self.assertTrue(policy["unlisted_existing_leaf_values_must_be_identical"])
        self.assertFalse(policy["unlisted_v1_fields_may_be_removed"])
        self.assertFalse(policy["unlisted_v2_fields_may_be_added"])
        required = action["required_v2_values"]
        self.assertEqual(
            required["outputs.failure"],
            f"{failure.RECOVERY_OUTPUT_DIRECTORY}/failure.json",
        )
        self.assertEqual(
            required["next_gate_after_freeze.gate_id"],
            failure.RECOVERY_EXECUTION_GATE_ID,
        )
        self.assertEqual(
            required["success_next_gate_after_execution"]["gate_id"],
            failure.RECOVERY_SUCCESS_NEXT_GATE_ID,
        )
        self.assertEqual(
            required["formal_gate.required_gates"].count(
                failure.RECOVERY_PROMPT_GATE
            ),
            1,
        )
        differences = action["allowed_v2_differences"]
        self.assertIn(
            "formal_gate.required_gates", differences["exact_value_replacements"]
        )
        self.assertNotIn(
            "next_gate_after_freeze", differences["exact_value_replacements"]
        )
        self.assertIn(
            "next_gate_after_freeze.gate_id",
            differences["exact_value_replacements"],
        )
        self.assertIn(
            "next_gate_after_freeze.action",
            differences["exact_value_replacements"],
        )
        sources = differences["source_lineage.protocol_sources"]
        self.assertFalse(sources["other_additions_removals_or_replacements_allowed"])
        self.assertEqual(
            sorted(sources["required_additions"]),
            ["post_training_contract_v2", "post_training_runner_v2"],
        )
        lineage = action["lineage_requirements"]
        self.assertEqual(
            lineage["v1_failure_receipt"]["sha256"],
            failure.FAILURE_RECEIPT_SHA256,
        )
        self.assertTrue(
            lineage["v1_failure_classification"][
                "file_receipt_required_at_v2_freeze"
            ]
        )
        self.assertEqual(artifact["failed_gate_id"], failure.FAILED_GATE_ID)

    def test_artifact_drift_is_rejected(self) -> None:
        artifact = copy.deepcopy(self.load_artifact())
        artifact["formal_gate_passed"] = True
        with self.assertRaises(protocol.MM003PostTrainingProtocolError) as raised:
            failure.validate_failure_classification(ROOT, artifact)
        self.assertEqual(raised.exception.code, "FAILURE_CLASSIFICATION_MISMATCH")


if __name__ == "__main__":
    unittest.main()
