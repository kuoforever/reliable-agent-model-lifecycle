"""Observation completeness and transformation boundaries, without desktop IO."""

import copy
import json
import unittest

from scripts.validate_gui_observation_projection import (
    REPORT,
    check_runtime_receipt,
    fixture,
    replay,
)
from fullcycle_bridge.gui_observation_projection import (
    ObservationProjectionError,
    inspect_observations,
    project_observation,
)
from fullcycle_bridge.native_gui_proposal import NativeProposalError


class ProjectionTests(unittest.TestCase):
    def setUp(self):
        self.task, self.results, self.image, self.facts = fixture()

    def refresh(self):
        self.facts["binding_digest"] = inspect_observations(
            self.task, self.results, self.image
        )["binding_digest"]

    def project(self, supplied=True):
        return project_observation(
            self.task, self.results, self.image, self.facts if supplied else None
        )

    def test_legacy_results_do_not_invent_context(self):
        result = self.project(False)
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(len(result["missing"]), 4)
        self.assertIsNone(result["context"])
        self.assertFalse(result["execution_authorized"])

    def test_rectangle_conversion_and_no_value_leak(self):
        self.results["snapshot"]["text"] += ' | value="Synthetic private draft"'
        self.refresh()
        control = self.project()["context"]["observation"]["controls"][0]
        self.assertEqual(control["bounds"], [100, 100, 300, 250])
        self.assertNotIn("value", control)
        self.assertNotIn("Synthetic private draft", str(control))

    def test_supplied_facts_produce_only_inert_context(self):
        result = self.project()
        self.assertEqual(result["status"], "projected")
        self.assertEqual(result["context"]["observation"]["epoch"], 3)
        self.assertFalse(result["execution_authorized"])

    def test_negative_controls(self):
        self.assertEqual(len(replay()["negatives"]), 12)

    def test_all_result_failures_rejected(self):
        for key in self.results:
            for field, value in [
                ("status", "action_error"),
                ("dispatch", "unknown"),
                ("generation", 9),
            ]:
                results = copy.deepcopy(self.results)
                results[key][field] = value
                with (
                    self.subTest(key=key, field=field),
                    self.assertRaises(ObservationProjectionError),
                ):
                    project_observation(self.task, results, self.image)

    def test_binding_covers_image_text_task(self):
        for kind in ["image", "text", "task"]:
            task, results, image, facts = fixture()
            if kind == "image":
                image = image + b"different"
            elif kind == "text":
                results["windows"]["text"] = '* 314 | word.exe | "Changed title"'
            else:
                task["request_id"] = "another-task"
            with (
                self.subTest(kind=kind),
                self.assertRaisesRegex(
                    ObservationProjectionError, "HOST_FACT_BINDING_MISMATCH"
                ),
            ):
                project_observation(task, results, image, facts)

    def test_no_implicit_visible_or_enabled(self):
        self.facts["control_states"] = {}
        with self.assertRaisesRegex(ObservationProjectionError, "CONTROL_FACT_SET"):
            self.project()

    def test_state_conflicts(self):
        self.facts["control_states"]["ref_1"]["enabled"] = False
        with self.assertRaisesRegex(
            ObservationProjectionError, "CONTROL_FACT_CONFLICT"
        ):
            self.project()

    def test_offscreen_must_not_be_promoted(self):
        self.results["snapshot"]["text"] += ",offscreen"
        self.refresh()
        with self.assertRaisesRegex(
            ObservationProjectionError, "CONTROL_FACT_CONFLICT"
        ):
            self.project()
        self.facts["control_states"]["ref_1"]["visible"] = False
        self.assertFalse(
            self.project()["context"]["observation"]["controls"][0]["visible"]
        )

    def test_missing_or_ambiguous_windows(self):
        for text in [
            "(no windows)",
            '  314 | word.exe | "x"',
            '* 314 | word.exe | "x"\n* 315 | chrome.exe | "y"',
            '* 314 | word.exe | "x"\n  314 | word.exe | "x"',
        ]:
            self.results["windows"]["text"] = text
            with self.subTest(text=text), self.assertRaises(ObservationProjectionError):
                self.project(False)

    def test_incomplete_and_ambiguous_snapshot_grammar(self):
        original = self.results["snapshot"]["text"]
        for text in [
            original + "\n# incomplete: unavailable",
            original + "\n# … 1 more truncated — narrow with find()",
            original + "\n" + original,
            original.replace("Document page", 'Unescaped "quote"'),
            original.replace("Document page", "x" * 100),
            original.replace("edit", "checkbox"),
            original.replace("enabled,focused", "enabled,disabled"),
        ]:
            self.results["snapshot"]["text"] = text
            with self.subTest(text=text), self.assertRaises(ObservationProjectionError):
                self.project(False)

    def test_empty_snapshot_requires_explicit_empty_states(self):
        self.results["snapshot"]["text"] = "# (no interactive elements in scope)"
        self.refresh()
        self.facts["control_states"] = {}
        self.assertEqual(self.project()["context"]["observation"]["controls"], [])

    def test_image_header_and_dimensions(self):
        for image in [b"", b"bad" * 20, self.image[:16] + bytes(8) + self.image[24:]]:
            with (
                self.subTest(size=len(image)),
                self.assertRaises(ObservationProjectionError),
            ):
                project_observation(self.task, self.results, image)

    def test_crop_dynamic_scope_and_unknown_fields(self):
        for key, args in [
            ("snapshot", {"scope": "foreground"}),
            ("screenshot", {"x": 0, "y": 0, "w": 100, "h": 100}),
        ]:
            result = copy.deepcopy(self.results)
            result[key]["arguments"] = args
            with self.assertRaises(ObservationProjectionError):
                project_observation(self.task, result, self.image)
        self.results["snapshot"]["approved"] = True
        with self.assertRaises(ObservationProjectionError):
            self.project()

    def test_boolean_epochs_and_future_results(self):
        for value in [True, 4, -1, 1]:
            self.results["snapshot"]["epoch"] = value
            with (
                self.subTest(value=value),
                self.assertRaises(ObservationProjectionError),
            ):
                self.project(False)

    def test_no_rectangle_clipping(self):
        self.facts["window_bounds"] = [0, 0, 150, 150]
        with self.assertRaises(NativeProposalError):
            self.project()

    def test_receipt_rejects_desktop_claim(self):
        value = json.loads(REPORT.read_text(encoding="utf-8"))["runtime"]
        check_runtime_receipt(value)
        value["desktop_calls"] = 1
        with self.assertRaisesRegex(ValueError, "Runtime receipt drift"):
            check_runtime_receipt(value)

    def test_giant_rectangle_digits_rejected(self):
        self.results["snapshot"]["text"] = self.results["snapshot"]["text"].replace(
            "(100,", "(" + "9" * 5000 + ","
        )
        with self.assertRaisesRegex(ObservationProjectionError, "SNAPSHOT_GRAMMAR"):
            self.project(False)


if __name__ == "__main__":
    unittest.main()
