"""Parent trust/consumption controls with injected processes, never inference."""
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
from scripts import run_public_summary_diagnostic as probe  # noqa: E402
from scripts.probe_public_source_summary import SOURCE_TITLE, SOURCE_URL, sha  # noqa: E402


class ParentTests(unittest.TestCase):
    def error(self):
        return dict(version=2, status="ERROR", code="SUMMARY_WORKER_FAILED",
                    stage="EOS_CHECK", reason="GENERATION_INCOMPLETE", model_requests=1)

    def test_error_is_classified_without_losing_count(self):
        probe.validate_response(self.error(), {}, 1)

    def test_rejects_legacy_unknown_and_ambiguous_error(self):
        for changes in [{"version": 1}, {"version": True}, {"stage": "secret"},
                        {"reason": "private traceback"}, {"model_requests": True},
                        {"model_requests": None}, {"extra": "raw"}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                probe.validate_response(self.error() | changes, {}, 1)
        with self.assertRaises(ValueError):
            probe.validate_response(self.error(), {}, 0)

    def run_fake(self, invoke):
        with tempfile.TemporaryDirectory() as temp:
            source = "Synthetic source for transport failure testing. " * 10
            request = dict(version=1, request_id="parent-test", source_url=SOURCE_URL,
                           source_title=SOURCE_TITLE, source_kind="public_reference_excerpt",
                           source_text=source, source_sha256=sha(source.encode()))
            reference = Path(temp) / "reference.json"
            reference.write_text(json.dumps(request), encoding="utf-8")
            output = Path(temp) / "attempt"
            with patch.object(probe, "SOURCE_SHA", request["source_sha256"]):
                receipt = probe.run(reference, output, invoke=invoke)
                with self.assertRaises(FileExistsError):
                    probe.run(reference, output, invoke=invoke)
            self.assertEqual(receipt, json.loads((output / "receipt.json").read_text()))
            return receipt

    def test_one_process_error_receipt_and_exclusive_consumption(self):
        calls = []

        def invoke(argv, **kwargs):
            calls.append(argv)
            self.assertEqual(kwargs["timeout"], 180)
            self.assertNotIn("OPENAI_API_KEY", kwargs["env"])
            self.assertEqual(json.loads(kwargs["input"])["request_id"], probe.REQUEST_ID)
            return SimpleNamespace(returncode=1, stdout=json.dumps(self.error()).encode())

        with patch.dict("os.environ", {"OPENAI_API_KEY": "private-key"}):
            receipt = self.run_fake(invoke)
        self.assertEqual(len(calls), 1)
        self.assertEqual(receipt["stage"], "EOS_CHECK")
        self.assertEqual(receipt["model_requests"], 1)
        self.assertEqual(receipt["retry_count"], 0)
        self.assertNotIn("private-key", json.dumps(receipt))

    def test_timeout_is_unknown_count_and_never_retried(self):
        calls = []

        def invoke(*args, **kwargs):
            calls.append(1)
            raise subprocess.TimeoutExpired("private command", 180)

        receipt = self.run_fake(invoke)
        self.assertEqual(calls, [1])
        self.assertEqual(receipt["code"], "WORKER_TIMEOUT")
        self.assertIsNone(receipt["model_requests"])
        self.assertNotIn("private", json.dumps(receipt))

    def test_malformed_and_oversized_output_remain_unassessable(self):
        for raw in [b'{"raw":"secret"}', b"x" * 16385]:
            receipt = self.run_fake(lambda *a, **k: SimpleNamespace(returncode=0, stdout=raw))
            self.assertEqual(receipt["code"], "PARENT_RESPONSE_REJECTED")
            self.assertIsNone(receipt["shape_passed"])
            self.assertNotIn("secret", json.dumps(receipt))

    def success(self):
        return dict(version=2, status="OK", request_id=probe.REQUEST_ID,
                    source_sha256=probe.SOURCE_SHA, model_requests=1,
                    model_id="mPLUG/GUI-Owl-1.5-4B-Instruct",
                    revision="3f061c2c562cc860c42bf32542a70e07a7ff4840",
                    adapter_sha256="3654fc21a2cea688754b800f9b10a49ae5e931f6ceb7eec080bfd83931fd0445",
                    execution_authorized=False, raw_output='{"bullets":[]}',
                    input_tokens=100, output_tokens=10, generation_seconds=2.0,
                    peak_allocated_bytes=1000)

    def test_transport_success_is_distinct_from_summary_shape(self):
        # Transport accepts a bounded response; render_brief separately rejects empty bullets.
        probe.validate_response(self.success(), self.success(), 0)
        with self.assertRaises(ValueError):
            probe.render_brief(self.success()["raw_output"])

    def test_success_cannot_change_binding_or_authority(self):
        for changes in [{"request_id": "other"}, {"source_sha256": "0" * 64},
                        {"model_id": "other"}, {"execution_authorized": True},
                        {"model_requests": True}, {"extra": "data"}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                probe.validate_response(self.success() | changes, self.success(), 0)

    def test_success_resource_claims_are_strict_and_bounded(self):
        for changes in [{"input_tokens": True}, {"output_tokens": 385},
                        {"generation_seconds": float("nan")}, {"generation_seconds": 61},
                        {"peak_allocated_bytes": 15_000_000_001}, {"raw_output": "x" * 4097}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                probe.validate_response(self.success() | changes, self.success(), 0)


if __name__ == "__main__":
    unittest.main()
