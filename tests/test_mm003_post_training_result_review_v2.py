from __future__ import annotations

import copy
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(ROOT))

from fullcycle_bridge import gui_grounding_eval as base_scorer  # noqa: E402
from fullcycle_bridge import mm003_post_training_protocol_v2 as contract  # noqa: E402
from scripts import validate_mm003_post_training_v2_result as validator  # noqa: E402


class MM003PostTrainingResultReviewV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.preregistration_payload = (
            ROOT / contract.PREREGISTRATION_PATH
        ).read_bytes()
        cls.baseline_payload = (
            ROOT / str(validator.BASELINE_RECEIPT["path"])
        ).read_bytes()
        cls.payloads = {
            name: (ROOT / str(receipt["path"])).read_bytes()
            for name, receipt in validator.ARTIFACTS.items()
        }
        cls.review_payload = (ROOT / validator.REVIEW_PATH).read_bytes()
        cls.suite = base_scorer.load_suite_file(
            (ROOT / contract.baseline.MM002_SUITE_PATH).resolve()
        )

    def test_frozen_result_review_recomputes_exactly(self) -> None:
        summary = validator.validate_repository(ROOT)
        self.assertTrue(summary["formal_gate_passed"])
        self.assertTrue(summary["training_executed"])
        self.assertTrue(summary["adapter_independently_loadable"])
        self.assertTrue(summary["model_evaluated"])
        self.assertEqual(summary["compiler_fallback_count"], 0)
        self.assertEqual(
            summary["grounding_accuracy"],
            {"correct": 3, "total": 5, "value": 0.6},
        )
        self.assertEqual(
            summary["action_accuracy"],
            {"correct": 3, "total": 9, "value": 1 / 3},
        )
        self.assertFalse(summary["repeatability_established"])
        self.assertEqual(summary["next_gate"], validator.NEXT_GATE_ID)
        self.assertFalse(summary["runtime_eligible"])

    def test_each_frozen_artifact_receipt_is_exact(self) -> None:
        for name, receipt in validator.ARTIFACTS.items():
            with self.subTest(name=name):
                payload = self.payloads[name]
                self.assertEqual(len(payload), receipt["bytes"])
                self.assertEqual(
                    contract.sha256_bytes(payload),
                    receipt["sha256"],
                )
        self.assertEqual(len(self.review_payload), validator.REVIEW_BYTES)
        self.assertEqual(
            contract.sha256_bytes(self.review_payload),
            validator.REVIEW_SHA256,
        )

    def test_single_byte_raw_artifact_drift_fails_closed(self) -> None:
        for name in validator.ARTIFACTS:
            with self.subTest(name=name):
                payloads = copy.copy(self.payloads)
                payloads[name] = payloads[name] + b" "
                with self.assertRaises(
                    validator.MM003PostTrainingV2ResultError
                ):
                    validator.validate_execution_payloads(
                        preregistration_payload=self.preregistration_payload,
                        baseline_payload=self.baseline_payload,
                        payloads=payloads,
                        suite=self.suite,
                    )

    def test_adapter_topology_drift_fails_closed(self) -> None:
        payload = bytearray(self.payloads["adapter_weights"])
        marker = b"lora_A.weight"
        index = payload.find(marker)
        self.assertGreater(index, 8)
        payload[index + len("lora_")] = ord("X")
        with self.assertRaisesRegex(
            validator.MM003PostTrainingV2ResultError,
            "ADAPTER_TENSOR_TOPOLOGY_MISMATCH",
        ):
            validator.inspect_mm003_adapter_safetensors_bytes(bytes(payload))

    def test_adapter_nonfinite_payload_fails_closed(self) -> None:
        payload = bytearray(self.payloads["adapter_weights"])
        header_bytes = int.from_bytes(payload[:8], "little")
        data_start = 8 + header_bytes
        payload[data_start : data_start + 4] = b"\x00\x00\xc0\x7f"
        with self.assertRaisesRegex(
            validator.MM003PostTrainingV2ResultError,
            "ADAPTER_TENSOR_NONFINITE_VALUES",
        ):
            validator.inspect_mm003_adapter_safetensors_bytes(bytes(payload))

    def test_prediction_producer_is_semantically_bound_to_adapter(self) -> None:
        predictions = contract.parse_strict_json_bytes(
            self.payloads["predictions"], location="$.predictions"
        )
        self.assertIsInstance(predictions, dict)
        assert isinstance(predictions, dict)
        validator._validate_prediction_identity(predictions, self.suite)
        for field, value in (
            ("kind", "probe"),
            ("model_id", contract.MODEL_ID),
            ("model_revision", "0" * 40),
        ):
            with self.subTest(field=field):
                candidate = copy.deepcopy(predictions)
                candidate["producer"][field] = value
                with self.assertRaisesRegex(
                    validator.MM003PostTrainingV2ResultError,
                    "PREDICTION_PRODUCER_IDENTITY_MISMATCH",
                ):
                    validator._validate_prediction_identity(candidate, self.suite)

    def test_exact_reader_rejects_size_before_open(self) -> None:
        fixture_parent = ROOT / "work" / "test-fixtures"
        fixture_parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=fixture_parent) as temp_dir:
            repository = Path(temp_dir) / "repository"
            baseline = repository / "baseline"
            baseline.mkdir(parents=True)
            artifact = baseline / "artifact.json"
            artifact.write_bytes(b"oversized")
            with mock.patch.object(
                Path,
                "open",
                side_effect=AssertionError("oversized file must not be opened"),
            ):
                with self.assertRaisesRegex(
                    validator.MM003PostTrainingV2ResultError,
                    "TEST_ARTIFACT_BYTE_MISMATCH",
                ):
                    validator._read_exact(
                        repository,
                        artifact,
                        expected_bytes=1,
                        expected_sha256="sha256:" + "0" * 64,
                        label="test artifact",
                    )

    def test_repository_path_escape_and_unsafe_parent_fail_closed(self) -> None:
        fixture_parent = ROOT / "work" / "test-fixtures"
        fixture_parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=fixture_parent) as temp_dir:
            parent = Path(temp_dir)
            repository = parent / "repository"
            baseline = repository / "baseline"
            baseline.mkdir(parents=True)
            inside = baseline / "artifact.json"
            inside.write_bytes(b"{}")
            outside = parent / "outside.json"
            outside.write_bytes(b"{}")
            with self.assertRaisesRegex(
                validator.MM003PostTrainingV2ResultError,
                "TEST_ARTIFACT_PATH_ESCAPE",
            ):
                validator._read_exact(
                    repository,
                    outside,
                    expected_bytes=2,
                    expected_sha256=contract.sha256_bytes(b"{}"),
                    label="test artifact",
                )
            with self.assertRaisesRegex(
                validator.MM003PostTrainingV2ResultError,
                "RESULT_REVIEW_PATH_ESCAPE",
            ):
                validator._write_exclusive(repository, outside, b"{}")
            with self.assertRaisesRegex(
                validator.MM003PostTrainingV2ResultError,
                "REPOSITORY_ROOT_MISMATCH",
            ):
                validator.validate_execution_payloads(
                    preregistration_payload=b"",
                    baseline_payload=b"",
                    payloads={},
                    suite={},
                    repository_root=repository,
                )

            hardlink = baseline / "artifact-hardlink.json"
            os.link(inside, hardlink)
            with self.assertRaisesRegex(
                validator.MM003PostTrainingV2ResultError,
                "MISSING_OR_UNSAFE_TEST_ARTIFACT",
            ):
                validator._read_exact(
                    repository,
                    inside,
                    expected_bytes=2,
                    expected_sha256=contract.sha256_bytes(b"{}"),
                    label="test artifact",
                )
            hardlink.unlink()

            written = baseline / "new-review.json"
            validator._write_exclusive(repository, written, b"{}")
            self.assertEqual(written.read_bytes(), b"{}")
            with self.assertRaises(FileExistsError):
                validator._write_exclusive(repository, written, b"{}")

            original = validator._safe_directory_signature

            def reject_baseline(path: Path, label: str) -> tuple[int, ...]:
                if path.name == "baseline":
                    raise validator.MM003PostTrainingV2ResultError(
                        f"UNSAFE_{label.upper().replace(' ', '_')}_PARENT"
                    )
                return original(path, label)

            with mock.patch.object(
                validator,
                "_safe_directory_signature",
                side_effect=reject_baseline,
            ):
                with self.assertRaisesRegex(
                    validator.MM003PostTrainingV2ResultError,
                    "UNSAFE_TEST_ARTIFACT_PARENT",
                ):
                    validator._read_exact(
                        repository,
                        inside,
                        expected_bytes=2,
                        expected_sha256=contract.sha256_bytes(b"{}"),
                        label="test artifact",
                    )
                with self.assertRaisesRegex(
                    validator.MM003PostTrainingV2ResultError,
                    "UNSAFE_RESULT_REVIEW_PARENT",
                ):
                    validator._write_exclusive(
                        repository, baseline / "review.json", b"{}"
                    )

    def test_review_records_exact_bad_case_taxonomy(self) -> None:
        review = contract.parse_strict_json_bytes(
            self.review_payload, location="$.review"
        )
        self.assertIsInstance(review, dict)
        assert isinstance(review, dict)
        taxonomy = review["evaluation"]["bad_case_taxonomy"]
        self.assertEqual(
            taxonomy["fused_grounding_missing_bbox"],
            ["ground-003", "ground-006"],
        )
        self.assertEqual(
            taxonomy["reject_downgraded_to_fallback"],
            ["ground-004", "ground-007", "ground-009"],
        )
        self.assertEqual(
            taxonomy["fallback_reason_vocabulary_mismatch"],
            ["ground-005"],
        )
        self.assertEqual(taxonomy["unclassified_cases"], [])
        self.assertTrue(taxonomy["eval_answers_may_not_be_copied_into_training"])
        self.assertEqual(
            review["evaluation"]["producer"],
            {
                "kind": "model",
                "model_id": contract.ADAPTER_MODEL_ID,
                "model_revision": contract.MODEL_REVISION,
            },
        )

    def test_review_preserves_claim_and_authority_boundaries(self) -> None:
        review = contract.parse_strict_json_bytes(
            self.review_payload, location="$.review"
        )
        evidence = contract.parse_strict_json_bytes(
            self.payloads["evidence"], location="$.evidence"
        )
        self.assertIsInstance(review, dict)
        self.assertIsInstance(evidence, dict)
        assert isinstance(review, dict)
        assert isinstance(evidence, dict)
        self.assertFalse(evidence["claims"]["quality_improved"])
        self.assertFalse(evidence["claims"]["repeatability_established"])
        self.assertFalse(
            review["claims"]["generalized_quality_improvement_established"]
        )
        self.assertFalse(review["claims"]["safety_rejection_success_established"])
        self.assertFalse(review["claims"]["repeatability_established"])
        self.assertFalse(review["claims"]["promotion_eligible"])
        self.assertFalse(review["runtime_eligible"])

    def test_frozen_artifacts_do_not_serialize_machine_paths(self) -> None:
        forbidden = (
            str(ROOT).encode("utf-8"),
            b"C:\\Users\\",
            b"work\\training-runs",
            b"work/training-runs",
        )
        for name, payload in {
            **self.payloads,
            "review": self.review_payload,
        }.items():
            with self.subTest(name=name):
                for marker in forbidden:
                    self.assertNotIn(marker, payload)

        decoded_strings: list[str] = []

        def collect_strings(value: object) -> None:
            if isinstance(value, str):
                decoded_strings.append(value)
            elif isinstance(value, dict):
                for key, item in value.items():
                    collect_strings(key)
                    collect_strings(item)
            elif isinstance(value, list):
                for item in value:
                    collect_strings(item)

        for name in (
            "training_run",
            "predictions",
            "evidence",
            "adapter_config",
        ):
            collect_strings(
                contract.parse_strict_json_bytes(
                    self.payloads[name], location=f"$.{name}"
                )
            )
        collect_strings(
            contract.parse_strict_json_bytes(self.review_payload, location="$.review")
        )
        decoded_strings.append(self.payloads["adapter_readme"].decode("utf-8"))
        for value in decoded_strings:
            self.assertNotRegex(
                value,
                r"(?i)(?:[a-z]:[\\/]|\\\\|/(?:home|users|tmp)/)",
            )


if __name__ == "__main__":
    unittest.main()
