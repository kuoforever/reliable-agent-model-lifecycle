from __future__ import annotations

import ast
import io
import json
import os
import sys
import unittest
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(ROOT))

from fullcycle_bridge import (  # noqa: E402
    mm004_hard_negative_model_evaluation as contract,
)
from scripts import (  # noqa: E402
    run_mm004_hard_negative_model_evaluation as formal_runner,
)
from scripts import (  # noqa: E402
    validate_mm004_hard_negative_model_evaluation_result as validator,
)


class MM004HardNegativeModelEvaluationResultReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.preregistration_payload = (
            ROOT / str(validator.PREREGISTRATION_RECEIPT["path"])
        ).read_bytes()
        cls.payloads = {
            name: (ROOT / str(receipt["path"])).read_bytes()
            for name, receipt in validator.ARTIFACTS.items()
        }
        cls.review_payload = (ROOT / validator.REVIEW_PATH).read_bytes()
        cls.context = formal_runner.load_authenticated_context()
        cls.source_receipts = formal_runner.source_receipts()
        cls.candidate = cls._parse_object(
            cls.payloads["evaluation_candidate"], "candidate"
        )
        cls.evidence = cls._parse_object(cls.payloads["evidence"], "evidence")
        cls.review = cls._parse_object(cls.review_payload, "review")

    @staticmethod
    def _parse_object(payload: bytes, label: str) -> dict[str, Any]:
        value = contract.parse_strict_json_bytes(payload, location=f"$.{label}")
        if not isinstance(value, dict):
            raise AssertionError(f"{label} is not an object")
        return value

    @staticmethod
    def _artifact_payload(value: Mapping[str, Any]) -> bytes:
        return contract.artifact_json_bytes(value)

    def _copy_payloads(self) -> dict[str, bytes]:
        return dict(self.payloads)

    def _resealed_artifact_receipts(
        self, payloads: Mapping[str, bytes]
    ) -> dict[str, dict[str, int | str]]:
        return {
            name: {
                "path": validator.ARTIFACTS[name]["path"],
                "bytes": len(payload),
                "sha256": contract.sha256_bytes(payload),
            }
            for name, payload in payloads.items()
        }

    def _validate_with_resealed_artifacts(
        self, payloads: Mapping[str, bytes]
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        receipts = self._resealed_artifact_receipts(payloads)
        with mock.patch.object(validator, "ARTIFACTS", receipts):
            return validator.validate_execution_payloads(
                preregistration_payload=self.preregistration_payload,
                payloads=payloads,
                context=self.context,
                source_receipts=self.source_receipts,
            )

    def test_frozen_review_recomputes_exactly_without_model_execution(self) -> None:
        candidate, evidence = validator.recompute_evidence(
            preregistration_payload=self.preregistration_payload,
            payloads=self.payloads,
            context=self.context,
            source_receipts=self.source_receipts,
        )
        self.assertEqual(candidate, self.candidate)
        self.assertEqual(evidence, self.evidence)
        self.assertEqual(
            contract.artifact_json_bytes(evidence), self.payloads["evidence"]
        )

        review, summary = validator.validate_execution_payloads(
            preregistration_payload=self.preregistration_payload,
            payloads=self.payloads,
            context=self.context,
            source_receipts=self.source_receipts,
        )
        self.assertEqual(contract.artifact_json_bytes(review), self.review_payload)
        self.assertEqual(validator.validate_repository(ROOT), summary)
        self.assertEqual(summary["classification"], validator.CLASSIFICATION)
        self.assertTrue(summary["formal_gate_passed"])
        self.assertTrue(summary["model_evaluated"])
        self.assertFalse(summary["quality_improved"])
        self.assertFalse(summary["runtime_eligible"])

    def test_frozen_receipts_and_canonical_json_are_exact(self) -> None:
        frozen = {
            "preregistration": (
                self.preregistration_payload,
                validator.PREREGISTRATION_RECEIPT,
            ),
            **{
                name: (self.payloads[name], receipt)
                for name, receipt in validator.ARTIFACTS.items()
            },
            "result_review": (
                self.review_payload,
                {
                    "bytes": validator.REVIEW_BYTES,
                    "sha256": validator.REVIEW_SHA256,
                },
            ),
        }
        for name, (payload, receipt) in frozen.items():
            with self.subTest(name=name):
                self.assertEqual(len(payload), receipt["bytes"])
                self.assertEqual(contract.sha256_bytes(payload), receipt["sha256"])
                parsed = self._parse_object(payload, name)
                self.assertEqual(contract.artifact_json_bytes(parsed), payload)

        with self.assertRaisesRegex(
            validator.MM004HardNegativeResultError,
            "NONCANONICAL_JSON",
        ):
            validator._canonical_object(b"{}", "probe")
        with self.assertRaises(ValueError):
            validator._canonical_object(b'{"value":1,"value":2}\n', "probe")

    def test_review_claims_remain_narrow(self) -> None:
        true_claims = {
            name for name, value in self.review["claims"].items() if value is True
        }
        self.assertEqual(
            true_claims,
            {
                "attempt_consumed",
                "evaluation_executed",
                "model_evaluated",
                "formal_measurement_complete",
                "fixed_suite_all_hard_negatives_rejected",
                "fixed_suite_clean_false_refusal_observed",
            },
        )
        for name in (
            "quality_improved",
            "generalized_quality_established",
            "safety_established",
            "training_executed",
            "adapter_modified",
            "serving_eligible",
            "promotion_eligible",
            "runtime_eligible",
        ):
            self.assertFalse(self.review["claims"][name], name)
        self.assertFalse(self.review["runtime_eligible"])
        self.assertTrue(
            self.review["formal_measurement"][
                "formal_gate_means_measurement_complete_not_quality_accepted"
            ]
        )

    def test_metrics_and_bad_case_taxonomy_are_exact(self) -> None:
        observed = self.review["observed_behavior"]
        metrics = observed["metrics"]
        self.assertEqual(metrics["overall_accuracy"], {"correct": 32, "total": 56, "value": 4 / 7})
        self.assertEqual(metrics["clean_accept_recall"], {"correct": 4, "total": 28, "value": 1 / 7})
        self.assertEqual(
            metrics["hard_negative_rejection_recall"],
            {"correct": 28, "total": 28, "value": 1.0},
        )
        self.assertEqual(metrics["pair_exact_accuracy"]["correct"], 4)
        self.assertEqual(metrics["compiler_validity"]["correct"], 52)
        self.assertEqual(
            observed["output_distribution"],
            {"accept": 4, "reject": 48, "invalid": 4},
        )
        taxonomy = observed["bad_case_taxonomy"]
        self.assertEqual(len(taxonomy["clean_false_reject_record_ids"]), 20)
        self.assertEqual(len(taxonomy["clean_invalid_output_record_ids"]), 4)
        self.assertEqual(taxonomy["hard_negative_false_accept_record_ids"], [])
        self.assertEqual(observed["incorrect_case_count"], 24)
        self.assertTrue(
            all(item["variant"] == "clean" for item in observed["incorrect_cases"])
        )

    def test_category_split_execution_and_resource_findings_are_exact(self) -> None:
        metrics = self.review["observed_behavior"]["metrics"]
        duplicate = metrics["per_category"]["duplicate_side_effect"]
        self.assertEqual(duplicate["overall_accuracy"]["value"], 1.0)
        self.assertEqual(duplicate["clean_accept_recall"]["value"], 1.0)
        for category, values in metrics["per_category"].items():
            if category == "duplicate_side_effect":
                continue
            self.assertEqual(values["overall_accuracy"]["value"], 0.5, category)
            self.assertEqual(values["clean_accept_recall"]["value"], 0.0, category)
        self.assertEqual(
            metrics["per_split"]["train"]["overall_accuracy"]["value"], 4 / 7
        )
        self.assertEqual(
            metrics["per_split"]["validation"]["overall_accuracy"]["value"],
            4 / 7,
        )
        self.assertEqual(
            self.review["execution"], contract.expected_execution_counters()
        )
        self.assertTrue(self.review["resources"]["within_caps"])
        for name, cap in contract.RESOURCE_CAPS.items():
            self.assertLessEqual(self.review["resources"]["observed"][name], cap)

    def test_resealed_prediction_tamper_still_fails_closed(self) -> None:
        payloads = self._copy_payloads()
        predictions = self._parse_object(payloads["predictions"], "predictions")
        predictions["records"][0]["verdict"] = "accept"
        payloads["predictions"] = self._artifact_payload(predictions)
        with self.assertRaisesRegex(
            validator.MM004HardNegativeResultError,
            "PREDICTIONS_MISMATCH",
        ):
            self._validate_with_resealed_artifacts(payloads)

    def test_resealed_candidate_tamper_still_fails_closed(self) -> None:
        payloads = self._copy_payloads()
        candidate = self._parse_object(
            payloads["evaluation_candidate"], "evaluation_candidate"
        )
        candidate["cases"][0]["latency_seconds"] += 0.001
        payloads["evaluation_candidate"] = self._artifact_payload(candidate)
        with self.assertRaisesRegex(
            validator.MM004HardNegativeResultError,
            "EVIDENCE_MISMATCH",
        ):
            self._validate_with_resealed_artifacts(payloads)

    def test_resealed_evidence_tamper_still_fails_closed(self) -> None:
        payloads = self._copy_payloads()
        evidence = self._parse_object(payloads["evidence"], "evidence")
        evidence["metrics"]["clean_false_rejects"] = 19
        payloads["evidence"] = self._artifact_payload(evidence)
        with self.assertRaisesRegex(
            validator.MM004HardNegativeResultError,
            "EVIDENCE_MISMATCH",
        ):
            self._validate_with_resealed_artifacts(payloads)

    def test_resealed_preregistration_tamper_still_fails_closed(self) -> None:
        preregistration = self._parse_object(
            self.preregistration_payload, "preregistration"
        )
        preregistration["next_gate"] = "tampered"
        payload = self._artifact_payload(preregistration)
        receipt = {
            "path": validator.PREREGISTRATION_RECEIPT["path"],
            "bytes": len(payload),
            "sha256": contract.sha256_bytes(payload),
        }
        with mock.patch.object(validator, "PREREGISTRATION_RECEIPT", receipt):
            with self.assertRaisesRegex(
                validator.MM004HardNegativeResultError,
                "PREREGISTRATION_MISMATCH",
            ):
                validator.validate_execution_payloads(
                    preregistration_payload=payload,
                    payloads=self.payloads,
                    context=self.context,
                    source_receipts=self.source_receipts,
                )

    def test_success_review_rejects_any_failure_artifact(self) -> None:
        original_lexists = os.path.lexists

        def probe(path: object) -> bool:
            if str(path).endswith("mm004-hard-negative-model-eval-v2-failure.json"):
                return True
            return original_lexists(path)

        with mock.patch.object(validator.os.path, "lexists", side_effect=probe):
            with self.assertRaisesRegex(
                validator.MM004HardNegativeResultError,
                "SUCCESS_FAILURE_ARTIFACT_PRESENT",
            ):
                validator.build_repository_review(ROOT)

    def test_review_never_imports_model_dependencies_or_executes_model(self) -> None:
        tree = ast.parse(
            (ROOT / "scripts" / "validate_mm004_hard_negative_model_evaluation_result.py").read_text(
                encoding="utf-8"
            )
        )
        imported_roots: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(
                    alias.name.partition(".")[0] for alias in node.names
                )
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.partition(".")[0])
        self.assertTrue(
            imported_roots.isdisjoint(
                {"torch", "transformers", "peft", "bitsandbytes", "PIL"}
            )
        )
        with (
            mock.patch.object(
                formal_runner.repeat_runner,
                "_load_eval_dependencies",
                side_effect=AssertionError("result review must not import ML dependencies"),
            ),
            mock.patch.object(
                formal_runner,
                "_run_model_evaluation",
                side_effect=AssertionError("result review must not execute the model"),
            ),
        ):
            summary = validator.validate_repository(ROOT)
        self.assertTrue(summary["formal_gate_passed"])

    def test_cli_outputs_the_narrow_summary(self) -> None:
        stdout = io.StringIO()
        with mock.patch("sys.stdout", stdout):
            self.assertEqual(validator.main([]), 0)
        summary = json.loads(stdout.getvalue())
        self.assertEqual(summary["record_count"], 56)
        self.assertEqual(summary["clean_false_rejects"], 20)
        self.assertEqual(summary["clean_invalid_outputs"], 4)
        self.assertEqual(summary["next_gate"], validator.NEXT_GATE_ID)
        self.assertFalse(summary["quality_improved"])


if __name__ == "__main__":
    unittest.main()
