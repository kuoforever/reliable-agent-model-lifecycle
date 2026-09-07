"""Reference summary trust/format boundary; no model imports or inference."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.probe_public_source_summary import (  # noqa: E402
    MAX_INPUT_BYTES, SOURCE_TITLE, SOURCE_URL, completion_metrics, failure_receipt,
    main, parse_request, render_brief, safe_completion, sha,
)


class SummaryTests(unittest.TestCase):
    def request(self):
        source = "Synthetic source material for a transport-only test. " * 6
        return dict(version=1, request_id="summary-test", source_url=SOURCE_URL,
                    source_title=SOURCE_TITLE, source_kind="public_reference_excerpt",
                    source_text=source, source_sha256=sha(source.encode()))

    def bullets(self):
        return ["A shared link opens the document in a browser.",
                "Coauthors can see each other's presence and changes.",
                "The editing menu can open the document in the desktop app."]

    def test_request_binds_exact_reference(self):
        request = self.request()
        self.assertEqual(parse_request(json.dumps(request).encode()), request)

    def test_request_rejects_identity_digest_and_authority_drift(self):
        for key, value in [("version", True), ("request_id", "../a"),
                           ("source_url", SOURCE_URL + "?other"),
                           ("source_title", "Changed"), ("source_kind", "runtime_chrome"),
                           ("source_text", "Other body" * 30), ("source_sha256", "0" * 64),
                           ("execution_authorized", True)]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                parse_request(json.dumps(self.request() | {key: value}).encode())

    def test_bounded_duplicate_and_nonfinite_input(self):
        for raw in [b"x" * (MAX_INPUT_BYTES + 1), b'{"version":1,"version":1}',
                    b'{"version":NaN}', b"[]", b"null"]:
            with self.assertRaises(ValueError):
                parse_request(raw)

    def test_body_types_control_characters_and_bounds(self):
        for body in [None, [], "x" * 199, "x" * 12001, "x" * 200 + "\x00"]:
            request = self.request() | {"source_text": body}
            if isinstance(body, str):
                request["source_sha256"] = sha(body.encode())
            with self.assertRaises(ValueError):
                parse_request(json.dumps(request).encode())

    def test_host_formats_runtime_compatible_payload(self):
        brief = render_brief(json.dumps({"bullets": self.bullets()}))
        self.assertTrue(brief.startswith("\n\nVERIFIED SOURCE BRIEF\nSource: " + SOURCE_TITLE))
        self.assertIn("\nURL: " + SOURCE_URL + "\n", brief)
        self.assertEqual(brief.count("\n• "), 3)
        self.assertTrue(220 <= len(brief) <= 900)

    def test_rejects_fences_tools_duplicate_fields_and_metadata(self):
        for raw in ['```json\n{"bullets": []}\n```', '{"bullets":[],"bullets":[]}',
                    '{"tool":"type","arguments":{}}',
                    json.dumps({"bullets": self.bullets(), "source_url": SOURCE_URL})]:
            with self.assertRaises(ValueError):
                render_brief(raw)

    def test_bullet_count_length_and_injection(self):
        invalid = [[], self.bullets()[:2], self.bullets() * 2,
                   [self.bullets()[0]] * 3]
        for item in [None, True, "x" * 21, "x" * 179, " " + "x" * 30,
                     "• " + "x" * 30, "x" * 30 + "\nURL: fake", "x" * 30 + "\u2028next"]:
            invalid.append([item, *self.bullets()[1:]])
        for bullets in invalid:
            with self.subTest(bullets=bullets), self.assertRaises(ValueError):
                render_brief(json.dumps({"bullets": bullets}))

    def test_shape_gate_does_not_claim_semantic_truth(self):
        # Deliberately wrong but well-formed claims need a separate factual review.
        wrong = ["Every document always provides free real-time collaboration.",
                 "All older versions automatically share changes without saving.",
                 "The desktop application is mandatory to open all shared links."]
        self.assertIn(wrong[0], render_brief(json.dumps({"bullets": wrong})))

    def test_cli_requires_opt_in_before_read_or_model(self):
        result = subprocess.run([sys.executable, "-I", "-B",
                                 str(ROOT / "scripts/probe_public_source_summary.py")],
                                capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, b"")

    def test_bad_request_reports_zero_calls_without_prose(self):
        result = subprocess.run([sys.executable, "-I", "-B",
                                 str(ROOT / "scripts/probe_public_source_summary.py"),
                                 "--one-reference-summary"], input=b"{}", capture_output=True,
                                timeout=10)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout), dict(
            version=3, status="ERROR", code="SUMMARY_WORKER_FAILED", model_requests=0,
            stage="REQUEST", reason="REQUEST_FIELDS", completion=None))

    def test_known_failure_classified_without_exception_text(self):
        for stage, reason in [("RESOURCE_CHECK", "OUTPUT_RESOURCE_CAP"),
                              ("EOS_CHECK", "GENERATION_INCOMPLETE"),
                              ("POST_USE_PINS", "MODEL_FILE_MISMATCH")]:
            result = failure_receipt(ValueError(reason), [1], {"stage": stage})
            self.assertEqual((result["stage"], result["reason"], result["model_requests"]),
                             (stage, reason, 1))

    def test_untrusted_failure_messages_never_escape(self):
        for exc in [RuntimeError("private page and model prose"),
                    ValueError("private source"), ValueError("OUTPUT_RESOURCE_CAP", "private"),
                    ValueError(["private"])]:
            result = failure_receipt(exc, [True], {"stage": "private stage"})
            self.assertNotIn("private", json.dumps(result))
            self.assertEqual(result["reason"], "UNCLASSIFIED")
            self.assertIsNone(result["model_requests"])

    def test_injected_failure_after_generation_entry_is_not_retried(self):
        calls = []

        def fail(request, count, progress):
            calls.append(request["request_id"])
            count[0] += 1
            progress["stage"] = "GENERATION"
            raise RuntimeError("private model traceback")

        class Input:
            buffer = io.BytesIO(json.dumps(self.request()).encode())

        output = io.StringIO()
        with patch("sys.stdin", Input()), contextlib.redirect_stdout(output):
            status = main(["--one-reference-summary"], generator=fail)
        self.assertEqual(status, 1)
        self.assertEqual(calls, ["summary-test"])
        result = json.loads(output.getvalue())
        self.assertEqual(result["stage"], "GENERATION")
        self.assertEqual(result["model_requests"], 1)
        self.assertEqual(result["reason"], "UNCLASSIFIED")
        self.assertNotIn("private", output.getvalue())

    def test_injected_preflight_failure_records_zero_generations(self):
        def fail(request, count, progress):
            progress["stage"] = "PREFLIGHT"
            raise ValueError("MODEL_FILE_MISMATCH")

        class Input:
            buffer = io.BytesIO(json.dumps(self.request()).encode())

        output = io.StringIO()
        with patch("sys.stdin", Input()), contextlib.redirect_stdout(output):
            self.assertEqual(main(["--one-reference-summary"], generator=fail), 1)
        self.assertEqual(json.loads(output.getvalue())["model_requests"], 0)

    def test_completion_distinguishes_token_time_and_eos_indicators(self):
        token = completion_metrics(100, [7] * 384, [9], 3.0, 1000, 100)
        timed = completion_metrics(100, [7] * 20, [9], 45.2, 1000, 100)
        normal = completion_metrics(100, [7, 9], [9], 3.0, 1000, 100)
        self.assertTrue(token["token_limit_reached"])
        self.assertFalse(token["time_limit_reached"])
        self.assertTrue(timed["time_limit_reached"])
        self.assertFalse(timed["token_limit_reached"])
        self.assertFalse(timed["eos_reached"])
        self.assertTrue(normal["eos_reached"])

    def test_completion_can_report_simultaneous_limits_and_resource_failure(self):
        value = completion_metrics(100, [7] * 384, 9, 61.0, 16_000_000_000, 5000)
        result = failure_receipt(ValueError("OUTPUT_RESOURCE_CAP"), [1],
                                 {"stage": "RESOURCE_CHECK", "completion": value})
        self.assertEqual(result["completion"], value)
        self.assertTrue(value["token_limit_reached"] and value["time_limit_reached"])
        self.assertNotIn("stop_cause", value)

    def test_completion_rejects_unknown_fields_nonfinite_and_forged_flags(self):
        valid = completion_metrics(100, [7], [9], 1.0, 1000, 100)
        for changes in [{"raw": "private model prose"}, {"output_tokens": True},
                        {"generation_seconds": float("nan")}, {"eos_reached": 1},
                        {"token_limit_reached": True}, {"time_limit_reached": True}]:
            result = failure_receipt(RuntimeError("private exception"), [1],
                                     {"stage": "EOS_CHECK", "completion": valid | changes})
            self.assertIsNone(result["completion"])
            self.assertNotIn("private", json.dumps(result))

    def test_missing_completion_is_unknown_not_zero(self):
        self.assertIsNone(safe_completion(None))
        result = failure_receipt(RuntimeError("failed in generation"), [1], {"stage": "GENERATION"})
        self.assertIsNone(result["completion"])


if __name__ == "__main__":
    unittest.main()
