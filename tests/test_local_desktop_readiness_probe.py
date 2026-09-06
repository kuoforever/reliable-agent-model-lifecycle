"""Model-free evidence-boundary tests for the exploratory probe."""

import json
from pathlib import Path
import unittest

from scripts.probe_local_desktop_readiness import messages_for, score, strict_object

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads(
    (ROOT / "configs/local_desktop_readiness_probe_v1.json").read_text(encoding="utf-8")
)["cases"]


class ReadinessProbeTests(unittest.TestCase):
    def test_duplicate_and_nonfinite_json_rejected(self):
        for raw in ['{"tool":"click","tool":"key"}', '{"a":NaN}', "[]"]:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                strict_object(raw)

    def test_gold_not_in_model_message(self):
        for case in CASES:
            copied = dict(case, expected={"secret": "GOLD_SENTINEL"})
            self.assertNotIn("GOLD_SENTINEL", json.dumps(messages_for(copied, {})))

    def test_schema_valid_wrong_target_is_not_success(self):
        case = next(c for c in CASES if c["id"] == "gui-relocated-editor")
        result = score(
            case, '{"tool":"click","arguments":{"ref":"ref_7"}}', lambda *a: None
        )
        self.assertTrue(result["tool_schema_valid"])
        self.assertFalse(result["task_pass"])

    def test_fence_diagnostic_does_not_promote_raw_compliance(self):
        case = CASES[0]
        result = score(case, "```json\n" + json.dumps(case["expected"]) + "\n```", None)
        self.assertTrue(result["task_pass"])
        self.assertFalse(result["raw_json_valid"])
        self.assertFalse(result["strict_task_pass"])

    def test_unknown_fields_and_bad_arguments_fail(self):
        case = next(c for c in CASES if c["id"] == "gui-editor")
        self.assertFalse(
            score(
                case,
                '{"tool":"click","arguments":{"ref":"ref_7"},"approval":true}',
                lambda *a: None,
            )["task_pass"]
        )

        def reject(*unused):
            raise ValueError("invalid runtime schema")

        self.assertFalse(
            score(case, json.dumps(case["expected"]), reject)["tool_schema_valid"]
        )

    def test_coverage_and_unique_ids(self):
        self.assertEqual(len(CASES), 12)
        self.assertEqual(len({c["id"] for c in CASES}), 12)
        self.assertEqual(
            {
                g: sum(c["group"] == g for c in CASES)
                for g in {c["group"] for c in CASES}
            },
            {"reading": 2, "summary": 2, "planner": 2, "executor": 6},
        )


if __name__ == "__main__":
    unittest.main()
