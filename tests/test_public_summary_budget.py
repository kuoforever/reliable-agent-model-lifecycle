"""Doubled-budget control boundaries with injected processes; no inference."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import probe_public_source_summary as prior  # noqa: E402
from scripts import probe_public_summary_budget as worker  # noqa: E402
from scripts import run_public_summary_budget as parent  # noqa: E402


class BudgetTests(unittest.TestCase):
    def request(self):
        source = "Synthetic reference for an offline budget transport test. " * 6
        return dict(version=1, request_id="budget-test", source_url=worker.SOURCE_URL,
                    source_title=worker.SOURCE_TITLE, source_kind="public_reference_excerpt",
                    source_text=source, source_sha256=worker.sha(source.encode()))

    def error(self):
        return dict(version=4, status="ERROR", code="SUMMARY_WORKER_FAILED",
                    stage="EOS_CHECK", reason="GENERATION_INCOMPLETE", model_requests=1,
                    completion=worker.completion_metrics(320, [7] * 768, [9], 60.0, 1000, 2000))

    def test_budget_indicators_use_new_thresholds(self):
        for tokens, seconds, token_flag, time_flag in [
            (384, 45, False, False), (768, 60, True, False),
            (500, 91, False, True), (768, 91, True, True),
        ]:
            value = worker.completion_metrics(320, [7] * tokens, [9], seconds, 1000, 2000)
            self.assertEqual((value["token_limit_reached"], value["time_limit_reached"]),
                             (token_flag, time_flag))
            parent.validate_response(self.error() | {"completion": value}, {}, 1)
        normal = worker.completion_metrics(320, [7, 9], 9, 1.0, 1000, 50)
        self.assertTrue(normal["eos_reached"])

    def test_unknown_resource_failure_retains_only_valid_observations(self):
        value = worker.completion_metrics(320, [7] * 768, 9, 121.0, 16_000_000_000, 5000)
        result = worker.failure_receipt(ValueError("OUTPUT_RESOURCE_CAP"), [1],
                                       {"stage": "RESOURCE_CHECK", "completion": value})
        parent.validate_response(result, {}, 1)
        self.assertEqual(result["completion"], value)
        for change in [{"output_tokens": True}, {"generation_seconds": float("nan")},
                       {"token_limit_reached": False}, {"private": "raw prose"}]:
            self.assertIsNone(worker.safe_completion(value | change))
        self.assertIsNone(worker.safe_completion(None))

    def test_old_interface_inconsistent_eos_and_unknown_fields_rejected(self):
        for change in [{"version": 3}, {"version": True}, {"raw": "private"},
                       {"completion": None}, {"stage": "GENERATION"}, {"model_requests": 0}]:
            with self.assertRaises(ValueError):
                parent.validate_response(self.error() | change, {}, 1)
        error = self.error()
        error["completion"]["eos_reached"] = True
        with self.assertRaises(ValueError):
            parent.validate_response(error, {}, 1)

    def test_source_prompt_and_shape_contract_are_unchanged(self):
        self.assertEqual(worker.SYSTEM, prior.SYSTEM)
        raw_request = json.dumps(self.request()).encode()
        self.assertEqual(worker.parse_request(raw_request), prior.parse_request(raw_request))
        bullets = ["A shared link opens the document in a browser.",
                   "Coauthors can see each other's presence and changes.",
                   "The editing menu can open the document in the desktop app."]
        raw = json.dumps({"bullets": bullets})
        self.assertEqual(worker.render_brief(raw), prior.render_brief(raw))
        for raw in ['{"bullets":[]}', '{"tool":"type"}', 'x' * 4097]:
            with self.assertRaises(ValueError):
                worker.render_brief(raw)

    def run_fake(self, invoke):
        with tempfile.TemporaryDirectory() as temp:
            request = self.request()
            reference = Path(temp) / "request.json"
            reference.write_text(json.dumps(request), encoding="utf-8")
            target = Path(temp) / "attempt"
            with patch.object(parent, "SOURCE_SHA", request["source_sha256"]):
                result = parent.run(reference, target, invoke=invoke)
                with self.assertRaises(FileExistsError):
                    parent.run(reference, target, invoke=invoke)
            self.assertEqual(result, json.loads((target / "receipt.json").read_text()))
            return result

    def test_one_call_has_fixed_budget_no_credentials_and_no_failure_prose(self):
        calls = []

        def invoke(argv, **kwargs):
            calls.append(argv)
            self.assertEqual(kwargs["timeout"], 240)
            self.assertEqual(argv[-1], "--one-budget-summary")
            self.assertNotIn("OPENAI_API_KEY", kwargs["env"])
            return SimpleNamespace(returncode=1, stdout=json.dumps(self.error()).encode())

        with patch.dict("os.environ", {"OPENAI_API_KEY": "private"}):
            result = self.run_fake(invoke)
        self.assertEqual(len(calls), 1)
        self.assertEqual(result["generation_budget"], dict(max_new_tokens=768, max_time_seconds=90,
                                                         checked_seconds=120, process_timeout_seconds=240))
        self.assertNotIn("private", json.dumps(result))
        self.assertEqual(result["retry_count"], 0)
        self.assertEqual(result["factual_review"], "NOT_ASSESSABLE")

    def test_timeout_and_malformed_output_are_not_retried(self):
        calls = []

        def timeout(*args, **kwargs):
            calls.append(1)
            raise subprocess.TimeoutExpired("private", 240)

        result = self.run_fake(timeout)
        self.assertEqual(calls, [1])
        self.assertEqual(result["code"], "WORKER_TIMEOUT")
        self.assertIsNone(result["model_requests"])
        for raw in [b'{"raw":"private"}', b'x' * 16385]:
            result = self.run_fake(lambda *a, **k: SimpleNamespace(returncode=0, stdout=raw))
            self.assertEqual(result["code"], "PARENT_RESPONSE_REJECTED")
            self.assertNotIn("private", json.dumps(result))

    def test_success_binding_and_caps_are_not_acceptance(self):
        response = dict(version=4, status="OK", request_id=parent.REQUEST_ID,
                        source_sha256=parent.SOURCE_SHA, model_requests=1,
                        model_id="mPLUG/GUI-Owl-1.5-4B-Instruct",
                        revision="3f061c2c562cc860c42bf32542a70e07a7ff4840",
                        adapter_sha256="3654fc21a2cea688754b800f9b10a49ae5e931f6ceb7eec080bfd83931fd0445",
                        execution_authorized=False, raw_output='{"bullets":[]}',
                        input_tokens=320, output_tokens=700, generation_seconds=70.0,
                        peak_allocated_bytes=1000)
        parent.validate_response(response, response, 0)
        for change in [{"request_id": "other"}, {"execution_authorized": True},
                       {"output_tokens": 769}, {"generation_seconds": 121},
                       {"peak_allocated_bytes": 15_000_000_001}, {"raw_output": 'x' * 4097}]:
            with self.assertRaises(ValueError):
                parent.validate_response(response | change, response, 0)

        def invoke(*args, **kwargs):
            request = json.loads(kwargs["input"])
            return SimpleNamespace(returncode=0, stdout=json.dumps(
                response | {"source_sha256": request["source_sha256"]}).encode())

        result = self.run_fake(invoke)
        self.assertEqual(result["code"], "SUMMARY_SHAPE_REJECTED")
        self.assertFalse(result["shape_passed"])
        self.assertEqual(result["factual_review"], "PENDING")

    def test_worker_failure_reports_one_entry_without_retry(self):
        calls = []

        def fail(request, count, progress):
            calls.append(1)
            count[0] += 1
            progress["stage"] = "GENERATION"
            raise RuntimeError("private")

        input_stream = SimpleNamespace(buffer=io.BytesIO(json.dumps(self.request()).encode()))
        output = io.StringIO()
        with patch("sys.stdin", input_stream), contextlib.redirect_stdout(output):
            self.assertEqual(worker.main(["--one-budget-summary"], generator=fail), 1)
        self.assertEqual(calls, [1])
        result = json.loads(output.getvalue())
        parent.validate_response(result, {}, 1)
        self.assertEqual(result["model_requests"], 1)
        self.assertIsNone(result["completion"])
        self.assertNotIn("private", output.getvalue())


if __name__ == "__main__":
    unittest.main()
