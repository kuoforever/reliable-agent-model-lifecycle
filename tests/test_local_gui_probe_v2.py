from __future__ import annotations

import copy
import json
import hashlib
from pathlib import Path
import unittest

from scripts.probe_local_gui_executor_v2 import CONFIG, messages_for, score, summarize


class LocalGuiProbeV2Tests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.visual = self.config["cases"][0]

    def call(self, arguments):
        return (
            "<tool_call>"
            + json.dumps({"name": "computer_use", "arguments": arguments})
            + "</tool_call>"
        )

    def test_gold_controls_and_projection_isolation(self):
        self.assertEqual(len(self.config["cases"]), 16)
        for case in self.config["cases"]:
            with self.subTest(case=case["id"]):
                messages = messages_for(case)
                self.assertNotIn('"expected"', json.dumps(messages))
                self.assertNotIn('"bbox"', json.dumps(messages))
                if case["group"] == "contract":
                    raw = json.dumps(case["expected"])
                elif case["bbox"] is None:
                    raw = self.call({"action": "terminate", "status": "failure"})
                else:
                    left, top, right, bottom = case["bbox"]
                    raw = self.call(
                        {
                            "action": "left_click",
                            "coordinate": [
                                (left + right) * 500 / case["width"],
                                (top + bottom) * 500 / case["height"],
                            ],
                        }
                    )
                self.assertTrue(score(case, raw)["task_pass"])

    def test_wrong_location_valid_schema_is_not_success(self):
        result = score(
            self.visual, self.call({"action": "left_click", "coordinate": [999, 999]})
        )
        self.assertTrue(result["schema_valid"])
        self.assertFalse(result["task_pass"])

    def test_absent_target_and_false_abstention(self):
        missing = self.config["cases"][6]
        stop = self.call({"action": "terminate", "status": "failure"})
        self.assertTrue(score(missing, stop)["task_pass"])
        self.assertFalse(score(self.visual, stop)["task_pass"])
        self.assertFalse(
            score(
                missing, self.call({"action": "left_click", "coordinate": [100, 100]})
            )["task_pass"]
        )

    def test_extra_calls_fields_and_bad_coordinates_rejected(self):
        good = self.call({"action": "left_click", "coordinate": [500, 110]})
        for raw in [
            good + good,
            "```" + good + "```",
            good + "done",
            self.call({"action": "left_click", "coordinate": [True, 110]}),
            self.call({"action": "left_click", "coordinate": [-1, 110]}),
            self.call({"action": "left_click", "coordinate": [1, 2], "approved": True}),
            '<tool_call>{"name":"computer_use","name":"other","arguments":{}}</tool_call>',
        ]:
            self.assertFalse(score(self.visual, raw)["schema_valid"])

    def test_contract_closed_and_stale_ref_rejected(self):
        case = self.config["cases"][8]
        changed = dict(case["expected"], approval=True)
        self.assertFalse(score(case, json.dumps(changed))["schema_valid"])
        stale = copy.deepcopy(case)
        stale["request"]["observation"]["epoch"] -= 1
        self.assertFalse(score(stale, json.dumps(stale["expected"]))["schema_valid"])

    def test_group_summary_keeps_validity_accuracy_and_latency_separate(self):
        rows = [
            {
                "group": "visual",
                "generation_seconds": t,
                "score": {"schema_valid": True, "task_pass": ok, "abstained": False},
            }
            for t, ok in [(1, True), (3, False)]
        ]
        result = summarize(rows)["visual"]
        self.assertEqual(
            (result["count"], result["schema_valid"], result["task_pass"]), (2, 2, 1)
        )
        self.assertEqual(result["median_generation_seconds"], 2)
        self.assertEqual(summarize([]), {})


class RetainedGuiProbeV2Tests(unittest.TestCase):
    def setUp(self):
        self.bundle = json.loads(
            (
                Path(__file__).resolve().parents[1]
                / "baseline/local-gui-executor-probe-v2.json"
            ).read_text(encoding="utf-8")
        )

    def test_retained_comparison_recomputes_without_models(self):
        from scripts.review_local_gui_probe_v2 import review

        result = review(self.bundle)
        self.assertEqual(result["case_count"], 32)
        self.assertFalse(result["model_loaded"])

    def test_rescoring_detects_changed_output_even_with_updated_hash(self):
        from scripts.review_local_gui_probe_v2 import review

        candidate = self.bundle["candidates"]["qwen"]
        events = [json.loads(line) for line in candidate["events_text"].splitlines()]
        events[6]["raw_output"] = "invalid"
        raw = "".join(json.dumps(e) + "\n" for e in events)
        candidate["events_text"] = raw
        candidate["report"]["events_sha256"] = hashlib.sha256(raw.encode()).hexdigest()
        with self.assertRaisesRegex(ValueError, "score drift"):
            review(self.bundle)

    def test_sampling_cannot_be_reintroduced_into_comparison(self):
        from scripts.review_local_gui_probe_v2 import review

        candidate = self.bundle["candidates"]["qwen"]
        events = [json.loads(line) for line in candidate["events_text"].splitlines()]
        events[2]["effective"]["do_sample"] = True
        raw = "".join(json.dumps(e) + "\n" for e in events)
        candidate["events_text"] = raw
        candidate["report"]["events_sha256"] = hashlib.sha256(raw.encode()).hexdigest()
        with self.assertRaisesRegex(ValueError, "effective greedy"):
            review(self.bundle)

    def test_excluded_attempt_cannot_be_counted_as_formal(self):
        from scripts.review_local_gui_probe_v2 import review

        self.bundle["excluded_attempts"]["gui-owl-v1"]["included_in_comparison"] = True
        with self.assertRaisesRegex(ValueError, "excluded attempt mixing"):
            review(self.bundle)


if __name__ == "__main__":
    unittest.main()
