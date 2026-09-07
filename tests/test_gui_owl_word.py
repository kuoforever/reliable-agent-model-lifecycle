"""Worker transport boundaries; no model import, download, or inference."""
import base64
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.probe_gui_owl_word import MAX_INPUT_BYTES, parse_request  # noqa: E402


class WorkerTests(unittest.TestCase):
    def request(self):
        return dict(version=1, request_id="gui-word-test", context_digest="a" * 64,
                    image_base64=base64.b64encode(b"\x89PNG\r\n\x1a\nheader-only").decode())

    def test_transport_decodes_png_header_before_model_layer(self):
        request, image = parse_request(json.dumps(self.request()).encode())
        self.assertEqual(request, self.request())
        self.assertTrue(image.startswith(b"\x89PNG"))

    def test_bad_fields_and_types(self):
        for key, value in [("version", True), ("request_id", "../other"),
                           ("context_digest", "bad"), ("image_base64", "bad!"),
                           ("image_base64", "YWJj"), ("image_base64", None),
                           ("coordinates", [500, 500])]:
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                parse_request(json.dumps(self.request() | {key: value}).encode())

    def test_size_limit_and_duplicates(self):
        for value in [b"x" * (MAX_INPUT_BYTES + 1), b'{"version":1,"version":1}', b"null", b"[]"]:
            with self.assertRaises(ValueError):
                parse_request(value)

    def test_cli_missing_opt_in_does_not_load_model(self):
        result = subprocess.run([sys.executable, "-I", "-B", str(ROOT / "scripts/probe_gui_owl_word.py")],
                                capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, b"")

    def test_bad_request_returns_fixed_error_zero_requests(self):
        result = subprocess.run([sys.executable, "-I", "-B", str(ROOT / "scripts/probe_gui_owl_word.py"),
                                 "--one-inert-proposal"], input=b"{}", capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout), dict(
            version=1, status="ERROR", code="MODEL_WORKER_FAILED", model_requests=0))


if __name__ == "__main__":
    unittest.main()
