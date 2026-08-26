from __future__ import annotations

import ast
import copy
import io
import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SRC))

from fullcycle_bridge import (  # noqa: E402
    mm005_document_chart_pdf_model_evaluation_repeatability as contract,
)
from scripts import (  # noqa: E402
    prepare_mm005_document_chart_pdf_model_evaluation_repeatability as protocol_builder,
)
from scripts import (  # noqa: E402
    validate_mm005_document_chart_pdf_model_evaluation_repeatability_result as validator,
)


class MM005DocumentChartPdfRepeatabilityResultReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.inputs = {**protocol_builder.protocol_inputs(), "output_absent": True}
        cls.preregistration_payload = (
            ROOT / str(validator.PREREGISTRATION_RECEIPT["path"])
        ).read_bytes()
        cls.payloads = {
            name: (ROOT / str(receipt["path"])).read_bytes()
            for name, receipt in validator.ARTIFACTS.items()
        }
        cls.review_payload = (ROOT / validator.REVIEW_PATH).read_bytes()
        cls.preregistration = cls._parse_object(
            cls.preregistration_payload, "preregistration"
        )
        cls.candidate = cls._parse_object(
            cls.payloads["evaluation_candidate"], "candidate"
        )
        cls.evidence = cls._parse_object(cls.payloads["evidence"], "evidence")
        cls.review = cls._parse_object(cls.review_payload, "review")

    @staticmethod
    def _parse_object(payload: bytes, label: str) -> dict[str, object]:
        value = contract.parse_strict_json_bytes(payload, location=f"$.{label}")
        if not isinstance(value, dict):
            raise AssertionError(f"{label} is not an object")
        return value

    @staticmethod
    def _artifact_payload(value: object) -> bytes:
        return contract.artifact_json_bytes(value)

    def _copy_payloads(self) -> dict[str, bytes]:
        return dict(self.payloads)

    def _validate_with_resealed_artifacts(
        self, payloads: dict[str, bytes]
    ) -> tuple[dict[str, object], dict[str, object]]:
        receipts = {
            name: {
                "path": validator.ARTIFACTS[name]["path"],
                "bytes": len(payload),
                "sha256": contract.sha256_bytes(payload),
            }
            for name, payload in payloads.items()
        }
        with mock.patch.object(validator, "ARTIFACTS", receipts):
            return validator.validate_execution_payloads(
                preregistration_payload=self.preregistration_payload,
                payloads=payloads,
                inputs=self.inputs,
            )

    def test_frozen_review_recomputes_exactly_without_model_execution(self) -> None:
        preregistration, candidate, evidence = validator.recompute_evidence(
            preregistration_payload=self.preregistration_payload,
            payloads=self.payloads,
            inputs=self.inputs,
        )
        self.assertEqual(preregistration, self.preregistration)
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
        self.assertTrue(summary["same_machine_fixed_suite_repeatability_established"])
        self.assertFalse(summary["resource_repeatability_established"])

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
            validator.MM005EvaluationRepeatabilityResultError,
            "NONCANONICAL_JSON",
        ):
            validator._canonical_object(b"{}", "probe")
        with self.assertRaises(ValueError):
            validator._canonical_object(b'{"value":1,"value":2}\n', "probe")

    def test_review_establishes_only_the_registered_repeatability_scope(self) -> None:
        true_claims = {
            name for name, value in self.review["claims"].items() if value is True
        }
        self.assertEqual(
            true_claims,
            {
                "baseline_attempt_consumed",
                "replay_attempt_consumed",
                "replay_executed",
                "model_evaluated",
                "formal_measurement_complete",
                "raw_outputs_exact_32_of_32",
                "compiled_outputs_exact_32_of_32",
                "verifier_verdicts_exact_32_of_32",
                "metrics_exact",
                "generated_token_counts_exact_32_of_32",
                "same_machine_fixed_suite_repeatability_established",
            },
        )
        for name in (
            "training_repeatability_established",
            "resource_repeatability_established",
            "cross_machine_reproducibility_established",
            "quality_improved",
            "generalized_quality_established",
            "safety_established",
            "real_content_behavior_established",
            "serving_eligible",
            "promotion_eligible",
            "runtime_eligible",
        ):
            self.assertFalse(self.review["claims"][name], name)
        self.assertFalse(self.review["runtime_eligible"])

    def test_environment_evidence_limit_is_explicit(self) -> None:
        environment = self.review["environment_evidence"]
        self.assertTrue(environment["formal_runner_observed_environment_gate_passed"])
        self.assertTrue(
            environment["frozen_runner_requires_live_mapping_exact_before_generation"]
        )
        self.assertFalse(environment["observed_environment_mapping_separately_persisted"])
        self.assertFalse(
            environment["post_run_exact_observed_mapping_independently_recoverable"]
        )
        self.assertEqual(
            environment["preflight_evidence_class"],
            "reviewer_observed_untracked_context",
        )
        self.assertEqual(
            self.review["registered_environment"], self.preregistration["environment"]
        )
        self.assertFalse(self.review["scope_semantics"]["machine_id_attested"])
        self.assertFalse(self.review["scope_semantics"]["hardware_identity_attested"])
        self.assertTrue(
            self.review["limitations"][
                "observed_environment_mapping_not_separately_persisted"
            ]
        )

    def test_five_registered_layers_are_exact_and_token_scope_is_bounded(self) -> None:
        comparison = self.review["comparison"]
        self.assertTrue(comparison["all_registered_layers_exact"])
        for name in (
            "raw_outputs",
            "compiled_outputs",
            "verifier_verdicts",
            "generated_token_counts",
        ):
            layer = comparison[name]
            self.assertTrue(layer["exact"], name)
            self.assertEqual(layer["exact_count"], 32)
            self.assertEqual(layer["total"], 32)
            self.assertEqual(layer["mismatch_record_ids"], [])
            self.assertEqual(layer["reference_sha256"], layer["replay_sha256"])
        self.assertTrue(comparison["metrics"]["exact"])
        self.assertEqual(comparison["metrics"]["mismatch_names"], [])
        semantics = self.review["comparison_semantics"]
        self.assertFalse(semantics["transformer_internal_layers_compared"])
        self.assertFalse(semantics["generated_token_id_sequences_persisted"])
        self.assertFalse(semantics["generated_token_sequence_exact_claimed"])
        self.assertFalse(semantics["per_case_latency_registered_as_repeatability_layer"])

    def test_execution_caps_and_resource_diagnostic_are_exact(self) -> None:
        self.assertEqual(
            self.review["execution"], contract.expected_execution_counters()
        )
        resources = self.review["resources"]
        self.assertTrue(resources["both_runs_within_caps"])
        self.assertFalse(resources["measurements_exact"])
        self.assertTrue(resources["diagnostic_only"])
        self.assertEqual(resources["absolute_delta"]["peak_gpu_allocated_bytes"], 0)
        self.assertEqual(resources["absolute_delta"]["peak_gpu_reserved_bytes"], 0)
        self.assertAlmostEqual(
            resources["absolute_delta"]["elapsed_seconds"],
            -14.432453199988231,
        )
        for run in ("baseline", "replay"):
            for name, cap in contract.RESOURCE_CAPS.items():
                self.assertLessEqual(resources[run][name], cap)

    def test_artifact_set_and_resealed_prediction_tamper_fail_closed(self) -> None:
        missing = self._copy_payloads()
        missing.pop("predictions")
        with self.assertRaisesRegex(
            validator.MM005EvaluationRepeatabilityResultError,
            "ARTIFACT_SET_MISMATCH",
        ):
            validator.validate_execution_payloads(
                preregistration_payload=self.preregistration_payload,
                payloads=missing,
                inputs=self.inputs,
            )

        payloads = self._copy_payloads()
        predictions = self._parse_object(payloads["predictions"], "predictions")
        predictions["records"][0]["raw_output"] += " "  # type: ignore[index]
        payloads["predictions"] = self._artifact_payload(predictions)
        with self.assertRaisesRegex(
            validator.MM005EvaluationRepeatabilityResultError,
            "PREDICTIONS_MISMATCH",
        ):
            self._validate_with_resealed_artifacts(payloads)

    def test_resealed_candidate_and_evidence_tamper_fail_closed(self) -> None:
        payloads = self._copy_payloads()
        candidate = self._parse_object(payloads["evaluation_candidate"], "candidate")
        candidate["cases"][0]["raw_output"] += " "  # type: ignore[index]
        payloads["evaluation_candidate"] = self._artifact_payload(candidate)
        with self.assertRaisesRegex(
            validator.MM005EvaluationRepeatabilityResultError,
            "PREDICTIONS_MISMATCH",
        ):
            self._validate_with_resealed_artifacts(payloads)

        payloads = self._copy_payloads()
        evidence = self._parse_object(payloads["evidence"], "evidence")
        evidence["comparison"]["all_registered_layers_exact"] = False  # type: ignore[index]
        payloads["evidence"] = self._artifact_payload(evidence)
        with self.assertRaisesRegex(
            validator.MM005EvaluationRepeatabilityResultError,
            "EXECUTION_EVIDENCE_RECOMPUTATION_MISMATCH",
        ):
            self._validate_with_resealed_artifacts(payloads)

    def test_resealed_preregistration_does_not_authorize_review(self) -> None:
        preregistration = copy.deepcopy(self.preregistration)
        preregistration["next_gate"] = "tampered"
        payload = self._artifact_payload(preregistration)
        receipt = {
            "path": validator.PREREGISTRATION_RECEIPT["path"],
            "bytes": len(payload),
            "sha256": contract.sha256_bytes(payload),
        }
        with mock.patch.object(validator, "PREREGISTRATION_RECEIPT", receipt):
            with self.assertRaisesRegex(
                validator.MM005EvaluationRepeatabilityResultError,
                "MISMATCH",
            ):
                validator.validate_execution_payloads(
                    preregistration_payload=payload,
                    payloads=self.payloads,
                    inputs=self.inputs,
                )

    def test_every_exactness_and_resource_boundary_is_required(self) -> None:
        for name in (
            "raw_outputs",
            "compiled_outputs",
            "verifier_verdicts",
            "generated_token_counts",
        ):
            with self.subTest(layer=name):
                evidence = copy.deepcopy(self.evidence)
                evidence["comparison"][name]["exact"] = False
                with self.assertRaisesRegex(
                    validator.MM005EvaluationRepeatabilityResultError,
                    "REPEATABILITY_MISMATCH",
                ):
                    validator.build_review(
                        preregistration=self.preregistration,
                        evidence=evidence,
                        candidate=self.candidate,
                    )

        evidence = copy.deepcopy(self.evidence)
        evidence["comparison"]["resources"]["exact"] = True
        with self.assertRaisesRegex(
            validator.MM005EvaluationRepeatabilityResultError,
            "RESOURCE_DIAGNOSTIC_BOUNDARY_MISMATCH",
        ):
            validator.build_review(
                preregistration=self.preregistration,
                evidence=evidence,
                candidate=self.candidate,
            )

    def test_success_review_rejects_any_failure_artifact(self) -> None:
        original_lexists = os.path.lexists

        def probe(path: object) -> bool:
            if str(path).endswith(
                "mm005-document-chart-pdf-model-eval-repeatability-v1-failure.json"
            ):
                return True
            return original_lexists(path)

        with mock.patch.object(validator.os.path, "lexists", side_effect=probe):
            with self.assertRaisesRegex(
                validator.MM005EvaluationRepeatabilityResultError,
                "SUCCESS_FAILURE_ARTIFACT_PRESENT",
            ):
                validator.build_repository_review(ROOT)

    def test_review_is_model_free_and_contains_no_machine_path_or_token_ids(self) -> None:
        tree = ast.parse(
            (
                ROOT
                / "scripts"
                / "validate_mm005_document_chart_pdf_model_evaluation_repeatability_result.py"
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
            call_names.isdisjoint({"generate", "from_pretrained", "_run_model_evaluation"})
        )
        serialized = self.review_payload.decode("utf-8")
        self.assertNotIn("C:\\\\Users", serialized)
        self.assertNotIn('"generated_token_ids":[', serialized)

    def test_cli_outputs_the_narrow_summary(self) -> None:
        expected = {
            "formal_gate_passed": True,
            "record_count": 32,
            "next_gate": validator.NEXT_GATE_ID,
            "same_machine_fixed_suite_repeatability_established": True,
            "resource_repeatability_established": False,
            "runtime_eligible": False,
        }
        stdout = io.StringIO()
        with (
            mock.patch.object(validator, "validate_repository", return_value=expected),
            mock.patch("sys.stdout", stdout),
        ):
            self.assertEqual(validator.main([]), 0)
        self.assertEqual(json.loads(stdout.getvalue()), expected)


if __name__ == "__main__":
    unittest.main()
