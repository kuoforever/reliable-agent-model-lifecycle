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
    mm005_document_chart_pdf_model_evaluation as contract,
)
from scripts import (  # noqa: E402
    prepare_mm005_document_chart_pdf_model_evaluation as protocol_builder,
)
from scripts import (  # noqa: E402
    validate_mm005_document_chart_pdf_model_evaluation_result as validator,
)


class MM005DocumentChartPdfModelEvaluationResultReviewTests(unittest.TestCase):
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
        cls.inputs = {**protocol_builder.protocol_inputs(), "output_absent": True}
        cls.candidate = cls._parse_object(
            cls.payloads["evaluation_candidate"], "candidate"
        )
        cls.evidence = cls._parse_object(cls.payloads["evidence"], "evidence")
        cls.review = cls._parse_object(cls.review_payload, "review")

    @staticmethod
    def _parse_object(payload: bytes, label: str) -> dict[str, Any]:
        return contract.parse_strict_json_bytes(payload, location=f"$.{label}")

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
                inputs=self.inputs,
            )

    def test_frozen_review_recomputes_exactly_without_model_execution(self) -> None:
        candidate, evidence = validator.recompute_evidence(
            preregistration_payload=self.preregistration_payload,
            payloads=self.payloads,
            inputs=self.inputs,
        )
        self.assertEqual(candidate, self.candidate)
        self.assertEqual(evidence, self.evidence)
        self.assertEqual(
            contract.artifact_json_bytes(evidence), self.payloads["evidence"]
        )

        review, summary = validator.validate_execution_payloads(
            preregistration_payload=self.preregistration_payload,
            payloads=self.payloads,
            inputs=self.inputs,
        )
        self.assertEqual(contract.artifact_json_bytes(review), self.review_payload)
        self.assertEqual(validator.validate_repository(ROOT), summary)
        self.assertEqual(summary["classification"], validator.CLASSIFICATION)
        self.assertTrue(summary["formal_gate_passed"])
        self.assertTrue(summary["model_evaluated"])
        self.assertFalse(summary["quality_improved"])
        self.assertFalse(summary["repeatability_established"])

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
            validator.MM005DocumentChartPdfResultError,
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
                "fixed_suite_joint_exact_19_of_32_observed",
                "task_family_skew_observed",
                "chart_and_table_joint_exact_16_of_16_observed",
                "document_text_joint_exact_0_of_8_observed",
            },
        )
        for name in (
            "quality_improved",
            "generalized_quality_established",
            "safety_established",
            "repeatability_established",
            "training_repeatability_established",
            "cross_machine_reproducibility_established",
            "training_executed",
            "adapter_modified",
            "real_content_behavior_established",
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
        self.assertEqual(
            metrics["joint_exact_accuracy"],
            {"correct": 19, "total": 32, "value": 19 / 32},
        )
        self.assertEqual(
            metrics["compiler_validity"],
            {"correct": 28, "total": 32, "value": 7 / 8},
        )
        self.assertEqual(metrics["compiler_invalid_count"], 4)
        self.assertEqual(
            observed["output_distribution"],
            {
                "compiler_valid": 28,
                "compiler_invalid": 4,
                "joint_correct": 19,
                "joint_incorrect": 13,
            },
        )
        taxonomy = observed["bad_case_taxonomy"]
        self.assertEqual(len(taxonomy["compiler_invalid_record_ids"]), 4)
        self.assertEqual(len(taxonomy["answer_only_wrong_record_ids"]), 9)
        self.assertEqual(taxonomy["other_wrong_record_ids"], [])
        self.assertEqual(
            taxonomy["incorrect_by_task_family"],
            {
                "document_text_evidence_grounding": 8,
                "page_region_selection": 5,
            },
        )
        self.assertEqual(observed["incorrect_case_count"], 13)

    def test_group_execution_and_resource_findings_are_exact(self) -> None:
        metrics = self.review["observed_behavior"]["metrics"]
        per_family = metrics["per_task_family"]
        self.assertEqual(
            per_family["chart_value_evidence_grounding"]["joint_exact_accuracy"][
                "correct"
            ],
            8,
        )
        self.assertEqual(
            per_family["table_cell_evidence_grounding"]["joint_exact_accuracy"][
                "correct"
            ],
            8,
        )
        self.assertEqual(
            per_family["document_text_evidence_grounding"]["joint_exact_accuracy"][
                "correct"
            ],
            0,
        )
        self.assertEqual(
            per_family["page_region_selection"]["joint_exact_accuracy"]["correct"],
            3,
        )
        self.assertEqual(
            metrics["per_split"]["train"]["joint_exact_accuracy"]["correct"], 14
        )
        self.assertEqual(
            metrics["per_split"]["validation"]["joint_exact_accuracy"]["correct"],
            5,
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
        predictions["records"][0]["raw_output"] += " "
        payloads["predictions"] = self._artifact_payload(predictions)
        with self.assertRaisesRegex(
            validator.MM005DocumentChartPdfResultError,
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
            validator.MM005DocumentChartPdfResultError,
            "PREDICTIONS_MISMATCH",
        ):
            self._validate_with_resealed_artifacts(payloads)

    def test_resealed_evidence_tamper_still_fails_closed(self) -> None:
        payloads = self._copy_payloads()
        evidence = self._parse_object(payloads["evidence"], "evidence")
        evidence["metrics"]["joint_exact_accuracy"]["correct"] = 18
        payloads["evidence"] = self._artifact_payload(evidence)
        with self.assertRaisesRegex(
            validator.MM005DocumentChartPdfResultError,
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
                validator.MM005DocumentChartPdfResultError,
                "PREREGISTRATION_MISMATCH",
            ):
                validator.validate_execution_payloads(
                    preregistration_payload=payload,
                    payloads=self.payloads,
                    inputs=self.inputs,
                )

    def test_success_review_rejects_any_failure_artifact(self) -> None:
        original_lexists = os.path.lexists

        def probe(path: object) -> bool:
            if str(path).endswith(
                "mm005-document-chart-pdf-model-eval-v1-failure.json"
            ):
                return True
            return original_lexists(path)

        with mock.patch.object(validator.os.path, "lexists", side_effect=probe):
            with self.assertRaisesRegex(
                validator.MM005DocumentChartPdfResultError,
                "SUCCESS_FAILURE_ARTIFACT_PRESENT",
            ):
                validator.build_repository_review(ROOT)

    def test_review_never_imports_model_dependencies_or_executes_model(self) -> None:
        tree = ast.parse(
            (
                ROOT
                / "scripts"
                / "validate_mm005_document_chart_pdf_model_evaluation_result.py"
            ).read_text(encoding="utf-8")
        )
        imported_roots: set[str] = set()
        call_names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(
                    alias.name.partition(".")[0] for alias in node.names
                )
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.partition(".")[0])
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    call_names.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    call_names.add(node.func.attr)
        self.assertTrue(
            imported_roots.isdisjoint(
                {"torch", "transformers", "peft", "bitsandbytes", "PIL"}
            )
        )
        self.assertTrue(
            call_names.isdisjoint(
                {"generate", "from_pretrained", "_run_model_evaluation"}
            )
        )
        summary = validator.validate_repository(ROOT)
        self.assertTrue(summary["formal_gate_passed"])

    def test_cli_outputs_the_narrow_summary(self) -> None:
        stdout = io.StringIO()
        with mock.patch("sys.stdout", stdout):
            self.assertEqual(validator.main([]), 0)
        summary = json.loads(stdout.getvalue())
        self.assertEqual(summary["record_count"], 32)
        self.assertEqual(summary["incorrect_case_count"], 13)
        self.assertEqual(summary["compiler_invalid_count"], 4)
        self.assertEqual(summary["next_gate"], validator.NEXT_GATE_ID)
        self.assertFalse(summary["quality_improved"])
        self.assertFalse(summary["repeatability_established"])


if __name__ == "__main__":
    unittest.main()
