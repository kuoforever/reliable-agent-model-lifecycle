"""V3 diagnostic metadata validation without inference."""
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
from scripts import run_public_summary_completion as probe  # noqa: E402
from scripts.probe_public_source_summary import SOURCE_TITLE, SOURCE_URL, completion_metrics, sha  # noqa: E402


class CompletionTests(unittest.TestCase):
    def error(self):
        return dict(version=3, status="ERROR", code="SUMMARY_WORKER_FAILED",
                    stage="EOS_CHECK", reason="GENERATION_INCOMPLETE", model_requests=1,
                    completion=completion_metrics(300, [7] * 384, [9], 3.0, 1000, 500))

    def test_accepts_token_and_time_flags_independently(self):
        for tokens, seconds in [(384, 3.0), (50, 46.0), (384, 46.0)]:
            response = self.error() | {"completion": completion_metrics(300, [7] * tokens, 9, seconds, 1000, 500)}
            probe.validate_response(response, {}, 1)

    def test_rejects_legacy_extra_and_bad_exit(self):
        for change in [{"version": 2}, {"version": True}, {"model_requests": True}, {"raw": "private"}]:
            with self.assertRaises(ValueError):
                probe.validate_response(self.error() | change, {}, 1)
        with self.assertRaises(ValueError):
            probe.validate_response(self.error(), {}, 0)

    def test_rejects_missing_post_generation_or_premature_metrics(self):
        for change in [{"completion": None}, {"model_requests": 0}, {"stage": "PREFLIGHT"}]:
            with self.assertRaises(ValueError):
                probe.validate_response(self.error() | change, {}, 1)
        probe.validate_response(self.error() | dict(stage="GENERATION", reason="UNCLASSIFIED", completion=None), {}, 1)

    def test_rejects_malformed_forged_or_contradictory_completion(self):
        for change in [{"eos_reached": True}, {"generation_seconds": float("nan")},
                       {"raw": "private"}, {"token_limit_reached": False}, {"output_tokens": True}]:
            response = self.error()
            response["completion"].update(change)
            with self.assertRaises(ValueError):
                probe.validate_response(response, {}, 1)

    def run_fake(self, invoke):
        with tempfile.TemporaryDirectory() as temp:
            source = "Synthetic source for completion transport testing. " * 10
            request = dict(version=1, request_id="test", source_url=SOURCE_URL,
                           source_title=SOURCE_TITLE, source_kind="public_reference_excerpt",
                           source_text=source, source_sha256=sha(source.encode()))
            path = Path(temp) / "reference.json"
            path.write_text(json.dumps(request), encoding="utf-8")
            target = Path(temp) / "attempt"
            with patch.object(probe, "SOURCE_SHA", request["source_sha256"]):
                result = probe.run(path, target, invoke=invoke)
                with self.assertRaises(FileExistsError):
                    probe.run(path, target, invoke=invoke)
            self.assertEqual(result, json.loads((target / "receipt.json").read_text()))
            return result

    def test_single_process_preserves_validated_counters_only(self):
        calls = []

        def invoke(*args, **kwargs):
            calls.append(1)
            self.assertEqual(kwargs["timeout"], 180)
            self.assertNotIn("OPENAI_API_KEY", kwargs["env"])
            return SimpleNamespace(returncode=1, stdout=json.dumps(self.error()).encode())

        with patch.dict("os.environ", {"OPENAI_API_KEY": "private"}):
            result = self.run_fake(invoke)
        self.assertEqual(calls, [1])
        self.assertEqual(result["completion"]["output_tokens"], 384)
        self.assertEqual(result["retry_count"], 0)
        self.assertNotIn("private", json.dumps(result))

    def test_timeout_does_not_invent_counters_or_retry(self):
        calls = []

        def invoke(*args, **kwargs):
            calls.append(1)
            raise subprocess.TimeoutExpired("private", 180)

        result = self.run_fake(invoke)
        self.assertEqual(calls, [1])
        self.assertEqual(result["code"], "WORKER_TIMEOUT")
        self.assertIsNone(result["model_requests"])
        self.assertNotIn("completion", result)

    def test_success_keeps_binding_resources_and_shape_separate(self):
        response = dict(version=3, status="OK", request_id=probe.REQUEST_ID,
                        source_sha256=probe.SOURCE_SHA, model_requests=1,
                        model_id="mPLUG/GUI-Owl-1.5-4B-Instruct",
                        revision="3f061c2c562cc860c42bf32542a70e07a7ff4840",
                        adapter_sha256="3654fc21a2cea688754b800f9b10a49ae5e931f6ceb7eec080bfd83931fd0445",
                        execution_authorized=False, raw_output='{"bullets":[]}',
                        input_tokens=100, output_tokens=10, generation_seconds=2.0,
                        peak_allocated_bytes=1000)
        probe.validate_response(response, response, 0)
        with self.assertRaises(ValueError):
            probe.render_brief(response["raw_output"])
        for changes in [{"request_id": "other"}, {"source_sha256": "0" * 64},
                        {"execution_authorized": True}, {"model_requests": True},
                        {"output_tokens": 385}, {"generation_seconds": float("nan")},
                        {"generation_seconds": 61}, {"peak_allocated_bytes": 15_000_000_001},
                        {"raw_output": "x" * 4097}, {"completion": None}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                probe.validate_response(response | changes, response, 0)


if __name__ == "__main__":
    unittest.main()
