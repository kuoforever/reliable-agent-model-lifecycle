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

from fullcycle_bridge import gui_grounding_eval  # noqa: E402
from fullcycle_bridge import mm003_baseline_protocol as contract  # noqa: E402
from scripts import run_mm003_multimodal_gui_action_baseline as runner  # noqa: E402

SUITE_PATH = ROOT / contract.MM002_SUITE_PATH
PREDICTIONS_PATH = (
    ROOT
    / "fixtures"
    / "gui_grounding_eval_v1"
    / "valid"
    / "synthetic-probe-predictions.json"
)


class MM003BaselineProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.suite = gui_grounding_eval.load_suite_file(SUITE_PATH.resolve())
        cls.cases = {case["case_id"]: case for case in cls.suite["cases"]}
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
        cls.screenshot_files = [
            {
                "case_id": case_id,
                "path": f"{contract.SCREENSHOT_ROOT}/{case_id}.png",
                "bytes": len(payload),
                "sha256": contract.sha256_bytes(payload),
            }
            for case_id in contract.SCREENSHOT_CASES
            for payload in [contract.render_case_png(cls.cases[case_id])]
        ]
        cls.source_hashes = {
            name: contract.sha256_bytes((ROOT / path).read_bytes())
            for name, path in contract.PROTOCOL_SOURCE_PATHS.items()
        }
        cls.preregistration = contract.expected_preregistration(
            freeze_status="frozen",
            model_files=cls.model_files,
            screenshot_files=cls.screenshot_files,
            protocol_source_hashes=cls.source_hashes,
        )
        cls.preregistration_payload = contract.artifact_json_bytes(cls.preregistration)

    def test_preregistration_round_trip_is_exact_and_outcome_neutral(self) -> None:
        self.assertEqual(
            contract.validate_preregistration(self.preregistration),
            self.preregistration,
        )
        self.assertFalse(
            self.preregistration["formal_gate"]["quality_threshold_required"]
        )
        self.assertFalse(self.preregistration["claims"]["baseline_executed"])
        self.assertFalse(self.preregistration["claims"]["model_evaluated"])
        self.assertFalse(self.preregistration["runtime_eligible"])

    def test_preregistration_rejects_claim_and_weight_drift(self) -> None:
        changed = copy.deepcopy(self.preregistration)
        changed["claims"]["runtime_eligible"] = True
        with self.assertRaisesRegex(
            contract.MM003ProtocolError, "PREREGISTRATION_RECOMPUTATION_MISMATCH"
        ):
            contract.validate_preregistration(changed)

        changed = copy.deepcopy(self.model_files)
        for record in changed:
            if record["path"] == "model-00001-of-00002.safetensors":
                record["sha256"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(
            contract.MM003ProtocolError, "MODEL_WEIGHT_HASH_MISMATCH"
        ):
            contract.expected_preregistration(
                freeze_status="frozen",
                model_files=changed,
                screenshot_files=self.screenshot_files,
                protocol_source_hashes=self.source_hashes,
            )

    def test_prompt_payload_never_contains_gold_or_raw_screenshot_regions(self) -> None:
        for case in self.suite["cases"]:
            with self.subTest(case_id=case["case_id"]):
                filtered = contract.filtered_model_input(case)
                serialized = json.dumps(filtered, sort_keys=True)
                self.assertNotIn('"gold"', serialized)
                self.assertNotIn('"screenshot_regions"', serialized)
                if case["observation_mode"] == "screenshot_only":
                    self.assertNotIn("uia_controls", filtered["observation"])
                else:
                    self.assertIn("uia_controls", filtered["observation"])

    def test_renderer_is_deterministic_valid_and_case_bound(self) -> None:
        payloads = []
        for case_id in contract.SCREENSHOT_CASES:
            left = contract.render_case_png(self.cases[case_id])
            right = contract.render_case_png(self.cases[case_id])
            self.assertEqual(left, right)
            self.assertTrue(left.startswith(b"\x89PNG\r\n\x1a\n"))
            payloads.append(left)
        self.assertEqual(len({contract.sha256_bytes(item) for item in payloads}), 6)

    def test_compiler_accepts_strict_json_and_fails_closed(self) -> None:
        case = self.cases["ground-001"]
        valid = {
            "case_id": "ground-001",
            "disposition": "act",
            "tool": "click",
            "arguments": {"button": "left"},
            "ref": "ref-save",
            "bbox": None,
            "reason": None,
        }
        compiled = contract.compile_raw_prediction(
            "```json\n" + json.dumps(valid) + "\n```", case
        )
        self.assertEqual(compiled, valid)
        fallback = contract.compile_raw_prediction(
            '{"case_id":"ground-001","disposition":"act"}', case
        )
        self.assertEqual(fallback["disposition"], "fallback")
        self.assertEqual(fallback["reason"], "model_output_invalid")

    def test_prepare_writes_then_checks_exact_protocol_and_images(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "preregistration.json"
            screenshots = root / "screenshots"
            with mock.patch.object(
                runner, "model_file_manifest", return_value=self.model_files
            ):
                written = runner.prepare_protocol(
                    model_snapshot=root,
                    suite_path=SUITE_PATH,
                    screenshots_dir=screenshots,
                    output_path=output,
                    freeze_status="frozen",
                    check=False,
                )
                checked = runner.prepare_protocol(
                    model_snapshot=root,
                    suite_path=SUITE_PATH,
                    screenshots_dir=screenshots,
                    output_path=output,
                    freeze_status="frozen",
                    check=True,
                )
            self.assertEqual(written, checked)
            tracked = contract.parse_strict_json_bytes(
                output.read_bytes(), location="$.preregistration"
            )
            self.assertEqual(contract.validate_preregistration(tracked), tracked)

    def test_evidence_gate_is_quality_neutral_and_resource_fail_closed(self) -> None:
        predictions = json.loads(PREDICTIONS_PATH.read_text(encoding="utf-8"))
        predictions["producer"] = {
            "kind": "model",
            "model_id": contract.MODEL_ID,
            "model_revision": contract.MODEL_REVISION,
        }
        score = gui_grounding_eval.score_predictions(self.suite, predictions)
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
                "completed": True,
            },
            "cases": case_results,
            "resources": {
                "elapsed_seconds": 30.0,
                "peak_gpu_allocated_bytes": 8_000_000_000,
                "peak_gpu_reserved_bytes": 9_000_000_000,
            },
        }
        evidence = runner.build_evidence(
            preregistration=self.preregistration,
            preregistration_payload=self.preregistration_payload,
            protocol_freeze_commit="a" * 40,
            run_artifact=run_artifact,
            predictions=predictions,
            score=score,
            suite=self.suite,
        )
        self.assertTrue(evidence["formal_gate_passed"])
        self.assertTrue(evidence["claims"]["model_evaluated"])
        self.assertFalse(evidence["claims"]["runtime_eligible"])
        self.assertEqual(
            set(evidence["quality"]["by_observation_mode"]),
            {"uia_only", "screenshot_only", "fused"},
        )

        over_cap = copy.deepcopy(run_artifact)
        over_cap["resources"]["peak_gpu_reserved_bytes"] = 17_000_000_000
        failed = runner.build_evidence(
            preregistration=self.preregistration,
            preregistration_payload=self.preregistration_payload,
            protocol_freeze_commit="a" * 40,
            run_artifact=over_cap,
            predictions=predictions,
            score=score,
            suite=self.suite,
        )
        self.assertFalse(failed["formal_gate_passed"])
        self.assertFalse(failed["claims"]["model_evaluated"])

        for section, key, replacement, gate in (
            (
                "model_resolution",
                "revision",
                "0" * 40,
                "exact_model_files",
            ),
            (
                "inputs",
                "suite_file_sha256",
                "sha256:" + "0" * 64,
                "exact_synthetic_inputs",
            ),
            ("environment", "torch", "0.0.0", "locked_environment"),
        ):
            with self.subTest(gate=gate):
                changed = copy.deepcopy(run_artifact)
                changed[section][key] = replacement
                rejected = runner.build_evidence(
                    preregistration=self.preregistration,
                    preregistration_payload=self.preregistration_payload,
                    protocol_freeze_commit="a" * 40,
                    run_artifact=changed,
                    predictions=predictions,
                    score=score,
                    suite=self.suite,
                )
                self.assertFalse(rejected["gates"][gate])
                self.assertFalse(rejected["formal_gate_passed"])

    def test_tracked_preregistration_and_screenshots_match_frozen_sources(self) -> None:
        path = ROOT / contract.PREREGISTRATION_PATH
        if not path.exists():
            self.skipTest("tracked preregistration is created after model download")
        tracked = contract.parse_strict_json_bytes(
            path.read_bytes(), location="$.preregistration"
        )
        self.assertEqual(contract.validate_preregistration(tracked), tracked)
        self.assertEqual(
            tracked["source_lineage"]["protocol_sources"],
            {
                name: {"path": relative, "sha256": self.source_hashes[name]}
                for name, relative in sorted(contract.PROTOCOL_SOURCE_PATHS.items())
            },
        )
        self.assertEqual(
            tracked["source_lineage"]["screenshots"], self.screenshot_files
        )


if __name__ == "__main__":
    unittest.main()
