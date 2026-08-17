from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(ROOT))

from fullcycle_bridge import gui_grounding_eval as base_scorer  # noqa: E402
from fullcycle_bridge import gui_grounding_eval_v2 as scorer  # noqa: E402
from fullcycle_bridge import mm003_baseline_protocol as v1_contract  # noqa: E402
from fullcycle_bridge import mm003_baseline_protocol_v2 as contract  # noqa: E402
from scripts import run_mm003_multimodal_gui_action_baseline_v2 as runner  # noqa: E402

SUITE_PATH = ROOT / contract.MM002_SUITE_PATH
PREDICTIONS_PATH = (
    ROOT
    / "fixtures"
    / "gui_grounding_eval_v1"
    / "valid"
    / "synthetic-probe-predictions.json"
)


class MM003BaselineRecoveryProtocolV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.suite = base_scorer.load_suite_file(SUITE_PATH.resolve())
        cls.model_files = [
            {
                "path": name,
                "bytes": size,
                "sha256": contract.MODEL_WEIGHT_SHA256.get(
                    name, "sha256:" + f"{index + 1:064x}"
                ),
            }
            for index, (name, size) in enumerate(
                sorted(contract.MODEL_FILE_SIZES.items())
            )
        ]
        cases = {case["case_id"]: case for case in cls.suite["cases"]}
        cls.screenshot_files = []
        for case_id in contract.SCREENSHOT_CASES:
            payload = contract.render_case_png(cases[case_id])
            cls.screenshot_files.append(
                {
                    "case_id": case_id,
                    "path": f"{contract.SCREENSHOT_ROOT}/{case_id}.png",
                    "bytes": len(payload),
                    "sha256": contract.sha256_bytes(payload),
                }
            )
        cls.source_hashes = runner.protocol_source_hashes()
        cls.preregistration = contract.expected_preregistration(
            freeze_status="frozen",
            model_files=cls.model_files,
            screenshot_files=cls.screenshot_files,
            protocol_source_hashes=cls.source_hashes,
        )
        cls.preregistration_payload = contract.artifact_json_bytes(cls.preregistration)

    def test_recovery_scorer_preserves_nonempty_v1_metric_values(self) -> None:
        predictions = json.loads(PREDICTIONS_PATH.read_text(encoding="utf-8"))
        v1_report = base_scorer.score_predictions(self.suite, predictions)
        v2_report = scorer.score_predictions(self.suite, predictions)
        expected = copy.deepcopy(v1_report)
        expected["report_version"] = 2
        self.assertEqual(v2_report, expected)

    def test_zero_prediction_diagnostic_is_explicitly_not_applicable(self) -> None:
        predictions = {
            "gui_grounding_prediction_version": 1,
            "suite_id": self.suite["suite_id"],
            "producer": {
                "kind": "model",
                "model_id": contract.MODEL_ID,
                "model_revision": contract.MODEL_REVISION,
            },
            "records": [
                contract.compile_raw_prediction("not-json", case)
                for case in self.suite["cases"]
            ],
        }
        report = scorer.score_predictions(self.suite, predictions)
        self.assertEqual(
            report["metrics"]["prediction_coordinate_ref_disagreement_rate"],
            {
                "correct": 0,
                "total": 0,
                "value": None,
                "status": "not_applicable",
            },
        )
        self.assertEqual(
            report["metrics"]["grounding_accuracy"],
            {"correct": 0, "total": 5, "value": 0.0},
        )
        self.assertFalse(report["claims"]["model_evaluated"])

    def test_preregistration_changes_only_registered_recovery_boundaries(self) -> None:
        base = v1_contract.expected_preregistration(
            freeze_status="frozen",
            model_files=self.model_files,
            screenshot_files=self.screenshot_files,
            protocol_source_hashes={
                "contract": self.source_hashes["base_contract"],
                "runner": self.source_hashes["base_runner"],
                "scorer": self.source_hashes["base_scorer"],
            },
        )
        current = self.preregistration
        self.assertEqual(current["model"], base["model"])
        for key in ("image_policy", "generation", "compiler", "case_order"):
            self.assertEqual(
                current["execution_protocol"][key], base["execution_protocol"][key]
            )
        self.assertEqual(
            current["source_lineage"]["mm002_suite"],
            base["source_lineage"]["mm002_suite"],
        )
        self.assertEqual(
            current["next_gate_after_freeze"]["gate_id"],
            contract.EXECUTION_GATE_ID,
        )
        self.assertEqual(contract.validate_preregistration(current), current)

    def test_runner_persists_candidates_before_scoring_and_has_failure_path(
        self,
    ) -> None:
        source = (ROOT / contract.RUNNER_SOURCE_PATH).read_text(encoding="utf-8")
        scoring = source.index("score = score_with_failure_persistence")
        self.assertLess(source.index("base_runner._write_exclusive(run_path"), scoring)
        self.assertLess(
            source.index("base_runner._write_exclusive(predictions_path"), scoring
        )
        self.assertGreater(source.index("def score_with_failure_persistence"), scoring)
        self.assertIn("output directory must be absent before model load", source)

    def test_evidence_accepts_quality_neutral_total_scoring(self) -> None:
        predictions = json.loads(PREDICTIONS_PATH.read_text(encoding="utf-8"))
        predictions["producer"] = {
            "kind": "model",
            "model_id": contract.MODEL_ID,
            "model_revision": contract.MODEL_REVISION,
        }
        score = scorer.score_predictions(self.suite, predictions)
        screenshot_hashes = {
            item["case_id"]: item["sha256"] for item in self.screenshot_files
        }
        case_results = []
        for case, record in zip(
            self.suite["cases"], predictions["records"], strict=True
        ):
            case_results.append(
                {
                    "case_id": record["case_id"],
                    "observation_mode": case["observation_mode"],
                    "prompt_sha256": contract.sha256_bytes(
                        contract.build_user_prompt(case).encode("utf-8")
                    ),
                    "screenshot_sha256": screenshot_hashes.get(record["case_id"]),
                    "compiled_prediction": record,
                    "compiler_fallback": False,
                    "candidate_steps": 1,
                    "latency_seconds": 1.0,
                }
            )
        run_artifact = {
            "protocol": {
                "preregistration_sha256": contract.sha256_bytes(
                    self.preregistration_payload
                ),
                "freeze_commit": "a" * 40,
            },
            "model_resolution": {
                "repo_id": contract.MODEL_ID,
                "revision": contract.MODEL_REVISION,
                "files": self.model_files,
            },
            "inputs": {
                "suite_file_sha256": contract.MM002_SUITE_FILE_SHA256,
                "suite_canonical_sha256": contract.MM002_SUITE_CANONICAL_SHA256,
                "screenshots": self.screenshot_files,
            },
            "environment": contract.LOCKED_ENVIRONMENT,
            "execution": {
                "fresh_model_loads": 1,
                "full_eval_runs": 1,
                "generate_calls": 9,
                "retry_count": 0,
                "network_used": False,
                "generation_completed": True,
            },
            "persistence": {
                "stage": "pre_score_candidates",
                "raw_run_written_before_scoring": True,
                "compiled_predictions_written_before_scoring": True,
                "writes_are_exclusive": True,
                "scoring_failure_receipt_required": True,
            },
            "cases": case_results,
            "resources": {
                "elapsed_seconds": 30.0,
                "peak_gpu_allocated_bytes": 8_000_000_000,
                "peak_gpu_reserved_bytes": 9_000_000_000,
            },
        }
        run_payload = contract.artifact_json_bytes(run_artifact)
        predictions_payload = contract.artifact_json_bytes(predictions)
        receipts = {
            "run": runner._receipt(contract.RUN_ARTIFACT_PATH, run_payload),
            "predictions": runner._receipt(
                contract.PREDICTIONS_ARTIFACT_PATH, predictions_payload
            ),
        }
        evidence = runner.build_evidence(
            preregistration=self.preregistration,
            preregistration_payload=self.preregistration_payload,
            protocol_freeze_commit="a" * 40,
            run_artifact=run_artifact,
            predictions=predictions,
            score=score,
            suite=self.suite,
            run_payload=run_payload,
            predictions_payload=predictions_payload,
            artifact_receipts=receipts,
        )
        self.assertTrue(evidence["formal_gate_passed"])
        self.assertTrue(evidence["claims"]["model_evaluated"])
        self.assertFalse(evidence["claims"]["runtime_eligible"])

        drifted = copy.deepcopy(receipts)
        drifted["run"]["sha256"] = "sha256:" + "0" * 64
        rejected = runner.build_evidence(
            preregistration=self.preregistration,
            preregistration_payload=self.preregistration_payload,
            protocol_freeze_commit="a" * 40,
            run_artifact=run_artifact,
            predictions=predictions,
            score=score,
            suite=self.suite,
            run_payload=run_payload,
            predictions_payload=predictions_payload,
            artifact_receipts=drifted,
        )
        self.assertFalse(rejected["gates"]["prescore_candidate_persistence"])
        self.assertFalse(rejected["formal_gate_passed"])

    def test_scoring_failure_receipt_preserves_candidates_and_denies_claims(
        self,
    ) -> None:
        exception = base_scorer.GuiGroundingValidationError(
            "SYNTHETIC_SCORING_FAILURE", "$.report.metrics", "test"
        )
        receipt = runner.build_scoring_failure_receipt(
            protocol_freeze_commit="b" * 40,
            preregistration_payload=self.preregistration_payload,
            run_artifact={
                "execution": {
                    "fresh_model_loads": 1,
                    "full_eval_runs": 1,
                    "generate_calls": 9,
                    "retry_count": 0,
                    "network_used": False,
                    "generation_completed": True,
                }
            },
            artifact_receipts={
                "run": {"path": "run", "bytes": 1, "sha256": "sha256:" + "1" * 64},
                "predictions": {
                    "path": "predictions",
                    "bytes": 1,
                    "sha256": "sha256:" + "2" * 64,
                },
            },
            exception=exception,
        )
        self.assertEqual(receipt["failure"]["code"], "SYNTHETIC_SCORING_FAILURE")
        self.assertFalse(receipt["formal_gate_passed"])
        self.assertFalse(receipt["claims"]["model_evaluated"])
        self.assertFalse(receipt["runtime_eligible"])

    def test_scoring_exception_writes_bound_failure_receipt(self) -> None:
        execution = {
            "fresh_model_loads": 1,
            "full_eval_runs": 1,
            "generate_calls": 9,
            "retry_count": 0,
            "network_used": False,
            "generation_completed": True,
        }
        cases = (
            (
                base_scorer.GuiGroundingValidationError(
                    "SYNTHETIC_SCORING_FAILURE", "$.report.metrics", "test"
                ),
                "SYNTHETIC_SCORING_FAILURE",
            ),
            (ValueError("C:\\private\\machine-path"), "UNEXPECTED_SCORING_EXCEPTION"),
        )
        for exception, expected_code in cases:
            with self.subTest(expected_code=expected_code):
                with tempfile.TemporaryDirectory() as temporary:
                    output_dir = Path(temporary)
                    with mock.patch.object(
                        scorer, "score_predictions", side_effect=exception
                    ):
                        with self.assertRaises(RuntimeError):
                            runner.score_with_failure_persistence(
                                output_dir=output_dir,
                                suite=self.suite,
                                predictions={"records": []},
                                protocol_freeze_commit="c" * 40,
                                preregistration_payload=self.preregistration_payload,
                                run_artifact={"execution": execution},
                                artifact_receipts={
                                    "run": {
                                        "path": contract.RUN_ARTIFACT_PATH,
                                        "bytes": 1,
                                        "sha256": "sha256:" + "1" * 64,
                                    },
                                    "predictions": {
                                        "path": contract.PREDICTIONS_ARTIFACT_PATH,
                                        "bytes": 1,
                                        "sha256": "sha256:" + "2" * 64,
                                    },
                                },
                            )
                    failure_path = (
                        output_dir / Path(contract.FAILURE_ARTIFACT_PATH).name
                    )
                    self.assertTrue(failure_path.is_file())
                    raw = contract.parse_strict_json_bytes(
                        failure_path.read_bytes(), location="$.failure"
                    )
                    self.assertEqual(raw["failure"]["code"], expected_code)
                    self.assertNotIn("private", raw["failure"]["detail"])
                    self.assertEqual(raw["execution"], execution)
                    self.assertFalse(raw["formal_gate_passed"])
                    self.assertFalse(raw["claims"]["model_evaluated"])

    def test_tracked_preregistration_matches_recomputation_when_present(self) -> None:
        path = ROOT / contract.PREREGISTRATION_PATH
        if not path.exists():
            self.skipTest("tracked v2 preregistration is created after source freeze")
        raw = contract.parse_strict_json_bytes(
            path.read_bytes(), location="$.preregistration"
        )
        self.assertIsInstance(raw, dict)
        self.assertEqual(contract.validate_preregistration(raw), raw)
        self.assertEqual(
            raw["source_lineage"]["protocol_sources"],
            {
                name: {"path": path, "sha256": self.source_hashes[name]}
                for name, path in sorted(contract.PROTOCOL_SOURCE_PATHS.items())
            },
        )


if __name__ == "__main__":
    unittest.main()
