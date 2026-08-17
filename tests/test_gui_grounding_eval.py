from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from fullcycle_bridge.gui_grounding_eval import (
    GuiGroundingValidationError,
    load_predictions_file,
    load_suite_file,
    score_predictions,
    validate_suite,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "gui_grounding_eval_v1"
SUITE_PATH = FIXTURES / "valid" / "suite.json"
PREDICTIONS_PATH = FIXTURES / "valid" / "synthetic-probe-predictions.json"
REPORT_PATH = ROOT / "baseline" / "mm-002-gui-grounding-data-eval-v1.json"
SUITE_SCHEMA_PATH = ROOT / "schemas" / "gui_grounding_eval_suite_v1.schema.json"
PREDICTIONS_SCHEMA_PATH = ROOT / "schemas" / "gui_grounding_predictions_v1.schema.json"


def load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


class GuiGroundingEvalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.suite = load(SUITE_PATH)
        cls.predictions = load(PREDICTIONS_PATH)
        cls.frozen_report = load(REPORT_PATH)

    def assert_suite_code(
        self, expected: str, value: object
    ) -> GuiGroundingValidationError:
        with self.assertRaises(GuiGroundingValidationError) as raised:
            validate_suite(value)
        self.assertEqual(raised.exception.code, expected)
        return raised.exception

    def assert_score_code(
        self, expected: str, predictions: object, suite: object | None = None
    ) -> GuiGroundingValidationError:
        with self.assertRaises(GuiGroundingValidationError) as raised:
            score_predictions(self.suite if suite is None else suite, predictions)
        self.assertEqual(raised.exception.code, expected)
        return raised.exception

    def test_valid_suite_has_exact_reviewed_coverage(self) -> None:
        summary = validate_suite(self.suite)
        self.assertEqual(summary.version, 1)
        self.assertEqual(summary.case_count, 9)
        self.assertEqual(
            summary.observation_modes, ("fused", "screenshot_only", "uia_only")
        )
        self.assertEqual(
            summary.capabilities,
            ("bbox_grounding", "fused_grounding", "ref_grounding"),
        )
        self.assertEqual(summary.ocr_conditions, ("clean", "missing", "noisy"))
        self.assertEqual(
            summary.perturbations,
            (
                "coordinate_ref_disagreement",
                "moved",
                "none",
                "occluded",
                "stale_ref",
            ),
        )
        self.assertFalse(summary.training_eligible)
        self.assertFalse(summary.real_content)

    def test_frozen_synthetic_probe_report_recomputes_exactly(self) -> None:
        self.assertEqual(
            score_predictions(self.suite, self.predictions), self.frozen_report
        )

    def test_metric_vector_is_sensitive_and_non_model(self) -> None:
        report = score_predictions(self.suite, self.predictions)
        metrics = report["metrics"]
        self.assertEqual(
            metrics["grounding_accuracy"], {"correct": 4, "total": 5, "value": 0.8}
        )
        self.assertEqual(
            metrics["mean_iou"], {"numerator": 19, "denominator": 20, "value": 0.95}
        )
        self.assertEqual(metrics["action_accuracy"]["correct"], 6)
        self.assertEqual(metrics["stale_ref_rejection"]["correct"], 1)
        self.assertEqual(metrics["coordinate_ref_disagreement_rejection"]["correct"], 0)
        self.assertEqual(
            metrics["prediction_coordinate_ref_disagreement_rate"]["correct"], 2
        )
        self.assertFalse(report["claims"]["model_evaluated"])
        self.assertTrue(report["claims"]["synthetic_probe_only"])

    def test_all_eligibility_and_capture_claims_remain_false(self) -> None:
        claims = score_predictions(self.suite, self.predictions)["claims"]
        for key in (
            "model_evaluated",
            "real_content_collected",
            "capture_adapter_implemented",
            "training_eligible",
            "execution_eligible",
            "runtime_eligible",
        ):
            self.assertIs(claims[key], False)

    def test_top_level_shapes_are_closed_and_complete(self) -> None:
        missing = copy.deepcopy(self.suite)
        del missing["bindings"]
        self.assert_suite_code("MISSING_FIELD", missing)
        unknown = copy.deepcopy(self.suite)
        unknown["unexpected"] = True
        self.assert_suite_code("UNKNOWN_FIELD", unknown)

    def test_version_runtime_and_trajectory_bindings_are_exact(self) -> None:
        for path, value, code in (
            (("gui_grounding_eval_version",), 2, "UNSUPPORTED_VERSION"),
            (
                ("bindings", "multimodal_trajectory_schema_version"),
                2,
                "UNSUPPORTED_VERSION",
            ),
            (
                ("bindings", "multimodal_trajectory_schema_sha256"),
                "sha256:" + "0" * 64,
                "VALUE_MISMATCH",
            ),
            (("bindings", "runtime_git_commit"), "0" * 40, "VALUE_MISMATCH"),
        ):
            changed = copy.deepcopy(self.suite)
            target = changed
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
            self.assert_suite_code(code, changed)

    def test_provenance_rejects_real_capture_and_training_use(self) -> None:
        for key, value, code in (
            ("real_content", True, "EXPECTED_FALSE"),
            ("capture_adapter_used", True, "EXPECTED_FALSE"),
            ("automatic_lane_a_export_used", True, "EXPECTED_FALSE"),
            ("training_eligible", True, "EXPECTED_FALSE"),
            ("synthetic_only", False, "EXPECTED_TRUE"),
        ):
            changed = copy.deepcopy(self.suite)
            changed["provenance"][key] = value
            self.assert_suite_code(code, changed)

    def test_eval_split_and_gold_separation_are_fail_closed(self) -> None:
        changed = copy.deepcopy(self.suite)
        changed["split_policy"]["split"] = "train"
        self.assert_suite_code("VALUE_MISMATCH", changed)
        for key in (
            "frozen",
            "gold_separated_from_model_input",
            "training_use_prohibited",
            "family_disjoint",
        ):
            changed = copy.deepcopy(self.suite)
            changed["split_policy"][key] = False
            self.assert_suite_code("EXPECTED_TRUE", changed)

    def test_case_order_count_and_identity_are_frozen(self) -> None:
        changed = copy.deepcopy(self.suite)
        changed["cases"].pop()
        self.assert_suite_code("INVALID_CASE_COUNT", changed)
        changed = copy.deepcopy(self.suite)
        changed["cases"][0]["case_id"] = "ground-009"
        self.assert_suite_code("CASE_ORDER_MISMATCH", changed)

    def test_family_and_instruction_leakage_are_rejected(self) -> None:
        changed = copy.deepcopy(self.suite)
        changed["cases"][1]["family_id"] = changed["cases"][0]["family_id"]
        self.assert_suite_code("FAMILY_LEAKAGE", changed)
        changed = copy.deepcopy(self.suite)
        changed["cases"][1]["model_input"]["instruction"] = changed["cases"][0][
            "model_input"
        ]["instruction"]
        self.assert_suite_code("INSTRUCTION_LEAKAGE", changed)

    def test_observation_modes_require_their_actual_channels(self) -> None:
        changed = copy.deepcopy(self.suite)
        changed["cases"][0]["model_input"]["observation"]["screenshot_regions"] = (
            copy.deepcopy(
                changed["cases"][1]["model_input"]["observation"]["screenshot_regions"]
            )
        )
        self.assert_suite_code("OBSERVATION_MODE_MISMATCH", changed)
        changed = copy.deepcopy(self.suite)
        changed["cases"][2]["model_input"]["observation"]["uia_controls"] = []
        self.assert_suite_code("OBSERVATION_MODE_MISMATCH", changed)

    def test_ocr_condition_matches_empty_and_nonempty_text(self) -> None:
        changed = copy.deepcopy(self.suite)
        changed["cases"][3]["model_input"]["observation"]["ocr_text"] = "unexpected"
        self.assert_suite_code("OCR_CONDITION_MISMATCH", changed)
        changed = copy.deepcopy(self.suite)
        changed["cases"][0]["model_input"]["observation"]["ocr_text"] = ""
        self.assert_suite_code("OCR_CONDITION_MISMATCH", changed)

    def test_capability_requires_matching_ref_and_bbox_cues(self) -> None:
        changed = copy.deepcopy(self.suite)
        changed["cases"][0]["model_input"]["observation"]["grounding_cue"]["bbox"] = [
            100,
            100,
            300,
            200,
        ]
        self.assert_suite_code("CAPABILITY_CUE_MISMATCH", changed)
        changed = copy.deepcopy(self.suite)
        changed["cases"][1]["model_input"]["observation"]["grounding_cue"]["ref"] = (
            "ref-confirm"
        )
        self.assert_suite_code("CAPABILITY_CUE_MISMATCH", changed)

    def test_bbox_bounds_and_geometry_fail_closed(self) -> None:
        for bbox in ([100, 100, 100, 200], [-1, 0, 10, 10], [0, 0, 5000, 10]):
            changed = copy.deepcopy(self.suite)
            changed["cases"][1]["gold"]["bbox"] = bbox
            self.assert_suite_code("INVALID_BBOX", changed)

    def test_catalog_rejects_duplicate_target_ref_or_bbox(self) -> None:
        for key in ("target_id", "ref", "bbox"):
            changed = copy.deepcopy(self.suite)
            catalog = changed["cases"][0]["gold"]["target_catalog"]
            catalog[1][key] = copy.deepcopy(catalog[0][key])
            self.assert_suite_code("DUPLICATE_CATALOG_TARGET", changed)

    def test_gold_target_ref_bbox_and_tool_are_bound(self) -> None:
        changed = copy.deepcopy(self.suite)
        changed["cases"][0]["gold"]["ref"] = "ref-cancel"
        self.assert_suite_code("GOLD_REF_MISMATCH", changed)
        changed = copy.deepcopy(self.suite)
        changed["cases"][1]["gold"]["bbox"] = [340, 100, 540, 300]
        self.assert_suite_code("GOLD_BBOX_MISMATCH", changed)
        changed = copy.deepcopy(self.suite)
        changed["cases"][0]["gold"]["tool"] = "type_text"
        self.assert_suite_code("GOLD_TOOL_UNAVAILABLE", changed)

    def test_terminal_outcomes_are_pinned_to_perturbations(self) -> None:
        changed = copy.deepcopy(self.suite)
        changed["cases"][3]["gold"]["reason"] = "unknown"
        self.assert_suite_code("PERTURBATION_OUTCOME_MISMATCH", changed)
        changed = copy.deepcopy(self.suite)
        changed["cases"][4]["gold"]["disposition"] = "reject"
        self.assert_suite_code("PERTURBATION_OUTCOME_MISMATCH", changed)

    def test_prediction_count_order_and_suite_binding_are_exact(self) -> None:
        changed = copy.deepcopy(self.predictions)
        changed["records"].pop()
        self.assert_score_code("PREDICTION_COUNT_MISMATCH", changed)
        changed = copy.deepcopy(self.predictions)
        changed["records"][0]["case_id"] = "ground-002"
        self.assert_score_code("PREDICTION_ORDER_MISMATCH", changed)
        changed = copy.deepcopy(self.predictions)
        changed["suite_id"] = "other-suite"
        self.assert_score_code("SUITE_BINDING_MISMATCH", changed)

    def test_prediction_act_and_terminal_shapes_are_fail_closed(self) -> None:
        changed = copy.deepcopy(self.predictions)
        changed["records"][0]["ref"] = None
        self.assert_score_code("MISSING_GROUNDING", changed)
        changed = copy.deepcopy(self.predictions)
        changed["records"][3]["tool"] = "click"
        self.assert_score_code("EXPECTED_NULL", changed)
        changed = copy.deepcopy(self.predictions)
        changed["records"][0]["unknown"] = True
        self.assert_score_code("UNKNOWN_FIELD", changed)

    def test_producer_binding_distinguishes_probe_from_model(self) -> None:
        changed = copy.deepcopy(self.predictions)
        changed["producer"]["model_id"] = "forged-model"
        self.assert_score_code("EXPECTED_NULL", changed)
        changed = copy.deepcopy(self.predictions)
        changed["producer"] = {
            "kind": "model",
            "model_id": "model-v1",
            "model_revision": "rev-v1",
        }
        report = score_predictions(self.suite, changed)
        self.assertTrue(report["claims"]["model_predictions_declared"])
        self.assertFalse(report["claims"]["model_evaluated"])
        self.assertFalse(report["claims"]["synthetic_probe_only"])

    def test_metric_arithmetic_recomputes_iou_and_disagreement(self) -> None:
        changed = copy.deepcopy(self.predictions)
        changed["records"][1]["bbox"] = [100, 100, 300, 300]
        report = score_predictions(self.suite, changed)
        self.assertEqual(
            report["metrics"]["mean_iou"],
            {"numerator": 1, "denominator": 1, "value": 1.0},
        )
        changed["records"][5]["ref"] = "ref-report"
        changed["records"][6]["ref"] = "ref-back"
        report = score_predictions(self.suite, changed)
        self.assertEqual(
            report["metrics"]["prediction_coordinate_ref_disagreement_rate"]["correct"],
            0,
        )

    def test_parser_invalid_fixtures_have_stable_codes(self) -> None:
        expected = {
            "malformed.json": "MALFORMED_JSON",
            "duplicate-key.json": "DUPLICATE_JSON_KEY",
            "missing-fields.json": "MISSING_FIELD",
            "nonfinite.json": "NONFINITE_NUMBER",
        }
        for filename, code in expected.items():
            with self.subTest(filename=filename):
                with self.assertRaises(GuiGroundingValidationError) as raised:
                    load_suite_file((FIXTURES / "invalid" / filename).resolve())
                self.assertEqual(raised.exception.code, code)

    def test_schema_files_are_closed_and_pin_versions(self) -> None:
        suite_schema = load(SUITE_SCHEMA_PATH)
        predictions_schema = load(PREDICTIONS_SCHEMA_PATH)
        self.assertIs(suite_schema["additionalProperties"], False)
        self.assertEqual(
            suite_schema["properties"]["gui_grounding_eval_version"]["const"], 1
        )
        self.assertIs(predictions_schema["additionalProperties"], False)
        self.assertEqual(
            predictions_schema["properties"]["gui_grounding_prediction_version"][
                "const"
            ],
            1,
        )

    def test_file_loaders_accept_frozen_files(self) -> None:
        self.assertEqual(
            load_suite_file(SUITE_PATH.resolve())["suite_id"], "mm002-synthetic-eval-v1"
        )
        self.assertEqual(
            load_predictions_file(PREDICTIONS_PATH.resolve())["suite_id"],
            "mm002-synthetic-eval-v1",
        )

    def test_symlink_suite_is_rejected_when_supported(self) -> None:
        link = ROOT / "work" / "test-fixtures" / "gui-grounding-suite-link.json"
        link.parent.mkdir(parents=True, exist_ok=True)
        try:
            link.unlink(missing_ok=True)
            link.symlink_to(SUITE_PATH.resolve())
        except OSError as exc:
            self.skipTest(f"symlink unavailable: {exc}")
        try:
            with self.assertRaises(GuiGroundingValidationError) as raised:
                load_suite_file(link)
            self.assertEqual(raised.exception.code, "UNSAFE_FILE")
        finally:
            link.unlink(missing_ok=True)

    def test_cli_validate_score_and_failure_are_machine_readable(self) -> None:
        env = dict(os.environ)
        env["PYTHONPATH"] = str(ROOT / "src")
        valid = subprocess.run(
            [
                sys.executable,
                "-m",
                "fullcycle_bridge.gui_grounding_eval_cli",
                "validate",
                str(SUITE_PATH.resolve()),
            ],
            cwd=ROOT,
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(valid.returncode, 0, valid.stderr)
        self.assertTrue(json.loads(valid.stdout)["valid"])
        scored = subprocess.run(
            [
                sys.executable,
                "-m",
                "fullcycle_bridge.gui_grounding_eval_cli",
                "score",
                str(SUITE_PATH.resolve()),
                str(PREDICTIONS_PATH.resolve()),
            ],
            cwd=ROOT,
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(scored.returncode, 0, scored.stderr)
        self.assertEqual(
            json.loads(scored.stdout)["metrics"]["grounding_accuracy"]["correct"], 4
        )
        invalid = subprocess.run(
            [
                sys.executable,
                "-m",
                "fullcycle_bridge.gui_grounding_eval_cli",
                "validate",
                str((FIXTURES / "invalid" / "malformed.json").resolve()),
            ],
            cwd=ROOT,
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(invalid.returncode, 2)
        self.assertEqual(json.loads(invalid.stderr)["error"], "MALFORMED_JSON")


if __name__ == "__main__":
    unittest.main()
