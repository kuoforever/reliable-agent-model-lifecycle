from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(ROOT))

from fullcycle_bridge import gui_grounding_eval as base_scorer  # noqa: E402
from fullcycle_bridge import mm003_baseline_protocol_v2 as contract  # noqa: E402
from scripts import validate_mm003_baseline_v2_evidence as validator  # noqa: E402


class MM003BaselineV2EvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.preregistration_payload = (
            ROOT / contract.PREREGISTRATION_PATH
        ).read_bytes()
        cls.payloads = {
            name: (ROOT / str(receipt["path"])).read_bytes()
            for name, receipt in validator.ARTIFACTS.items()
        }
        cls.suite = base_scorer.load_suite_file(
            (ROOT / contract.MM002_SUITE_PATH).resolve()
        )

    def test_frozen_baseline_recomputes_exactly(self) -> None:
        summary = validator.validate_repository(ROOT)
        self.assertEqual(summary["case_count"], 9)
        self.assertEqual(summary["fallback_count"], 9)
        self.assertTrue(summary["model_evaluated"])
        self.assertEqual(
            summary["grounding_accuracy"],
            {"correct": 0, "total": 5, "value": 0.0},
        )
        self.assertEqual(
            summary["action_accuracy"],
            {"correct": 0, "total": 9, "value": 0.0},
        )
        self.assertFalse(summary["runtime_eligible"])

    def test_each_artifact_receipt_is_exact(self) -> None:
        for name, receipt in validator.ARTIFACTS.items():
            with self.subTest(name=name):
                payload = self.payloads[name]
                self.assertEqual(len(payload), receipt["bytes"])
                self.assertEqual(contract.sha256_bytes(payload), receipt["sha256"])

    def test_single_byte_artifact_drift_fails_closed(self) -> None:
        for name in validator.ARTIFACTS:
            with self.subTest(name=name):
                payloads = copy.copy(self.payloads)
                payloads[name] = payloads[name] + b" "
                with self.assertRaises(validator.MM003BaselineV2EvidenceError):
                    validator.validate_payloads(
                        preregistration_payload=self.preregistration_payload,
                        run_payload=payloads["run"],
                        predictions_payload=payloads["predictions"],
                        evidence_payload=payloads["evidence"],
                        suite=self.suite,
                    )

    def test_artifacts_do_not_serialize_machine_paths(self) -> None:
        forbidden = (
            str(ROOT).encode("utf-8"),
            b"C:\\Users\\",
            b"mm003-formal-v2-9702c92c",
        )
        for name, payload in self.payloads.items():
            with self.subTest(name=name):
                for marker in forbidden:
                    self.assertNotIn(marker, payload)


if __name__ == "__main__":
    unittest.main()
