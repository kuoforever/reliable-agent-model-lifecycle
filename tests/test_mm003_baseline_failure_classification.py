from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from fullcycle_bridge import mm003_baseline_failure_classification as failure  # noqa: E402
from fullcycle_bridge import mm003_baseline_protocol as protocol  # noqa: E402

ARTIFACT = ROOT / failure.ARTIFACT_PATH


class MM003BaselineFailureClassificationTests(unittest.TestCase):
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

    def test_failure_boundary_remains_fail_closed(self) -> None:
        artifact = self.load_artifact()
        self.assertFalse(artifact["formal_gate_passed"])
        claims = artifact["claims"]
        self.assertIsInstance(claims, dict)
        for key in (
            "baseline_executed",
            "model_evaluated",
            "serving_readiness_established",
            "artifact_promotion_allowed",
            "runtime_eligible",
        ):
            self.assertIs(claims[key], False)

    def test_failure_is_bound_to_new_protocol_gate(self) -> None:
        artifact = self.load_artifact()
        action = artifact["locked_next_action"]
        self.assertIsInstance(action, dict)
        self.assertEqual(action["gate_id"], failure.NEXT_GATE_ID)
        self.assertEqual(artifact["failed_gate_id"], failure.FAILED_GATE_ID)
        self.assertEqual(
            artifact["protocol"]["freeze_commit"],  # type: ignore[index]
            failure.PROTOCOL_FREEZE_COMMIT,
        )

    def test_artifact_drift_is_rejected(self) -> None:
        artifact = copy.deepcopy(self.load_artifact())
        artifact["formal_gate_passed"] = True
        with self.assertRaises(protocol.MM003ProtocolError) as raised:
            failure.validate_failure_classification(ROOT, artifact)
        self.assertEqual(raised.exception.code, "FAILURE_CLASSIFICATION_MISMATCH")


if __name__ == "__main__":
    unittest.main()
