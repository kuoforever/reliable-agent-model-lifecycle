from __future__ import annotations

import ast
import copy
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
    mm003_post_training_eval_repeatability as contract,
)
from scripts import run_mm003_post_training_eval_repeatability as formal_runner  # noqa: E402
from scripts import (  # noqa: E402
    validate_mm003_post_training_eval_repeatability_result as validator,
)


class MM003PostTrainingEvalRepeatabilityResultReviewV1Tests(unittest.TestCase):
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
        cls.source_hashes = formal_runner.protocol_source_hashes()
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

    def _resealed_receipts(
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

    def _validate_with_resealed_artifact_receipts(
        self, payloads: Mapping[str, bytes]
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        receipts = self._resealed_receipts(payloads)
        with mock.patch.object(validator, "ARTIFACTS", receipts):
            return validator.validate_execution_payloads(
                preregistration_payload=self.preregistration_payload,
                payloads=payloads,
                context=self.context,
                source_hashes=self.source_hashes,
            )

    def test_frozen_result_review_recomputes_exactly_without_model_execution(
        self,
    ) -> None:
        expected_evidence, candidate, observed_evidence = validator.recompute_evidence(
            preregistration_payload=self.preregistration_payload,
            payloads=self.payloads,
            context=self.context,
            source_hashes=self.source_hashes,
        )
        self.assertEqual(
            contract.artifact_json_bytes(expected_evidence), self.payloads["evidence"]
        )
        self.assertEqual(candidate, self.candidate)
        self.assertEqual(observed_evidence, self.evidence)

        review, summary = validator.validate_execution_payloads(
            preregistration_payload=self.preregistration_payload,
            payloads=self.payloads,
            context=self.context,
            source_hashes=self.source_hashes,
        )
        self.assertEqual(contract.artifact_json_bytes(review), self.review_payload)
        self.assertEqual(validator.validate_repository(ROOT), summary)
        self.assertEqual(summary["classification"], validator.CLASSIFICATION)
        self.assertTrue(summary["formal_gate_passed"])
        self.assertTrue(summary["all_layers_exact"])
        self.assertEqual(summary["raw_outputs_exact"], contract.EXPECTED_CASES)
        self.assertEqual(
            summary["generated_token_counts_exact"], contract.EXPECTED_CASES
        )
        self.assertEqual(summary["compiled_predictions_exact"], contract.EXPECTED_CASES)
        self.assertTrue(summary["compiler_fallback_status_exact"])
        self.assertTrue(summary["metrics_exact"])
        self.assertTrue(summary["same_machine_eval_repeatability_established"])
        self.assertFalse(summary["training_repeatability_established"])
        self.assertFalse(summary["runtime_eligible"])

    def test_frozen_json_receipts_and_canonical_bytes_are_exact(self) -> None:
        frozen_payloads = {
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
        for name, (payload, receipt) in frozen_payloads.items():
            with self.subTest(name=name):
                self.assertEqual(len(payload), receipt["bytes"])
                self.assertEqual(contract.sha256_bytes(payload), receipt["sha256"])
                parsed = self._parse_object(payload, name)
                self.assertEqual(contract.artifact_json_bytes(parsed), payload)

        with self.assertRaisesRegex(
            validator.MM003EvalRepeatabilityResultError,
            "NONCANONICAL_JSON",
        ):
            validator._canonical_object(b"{}", "probe")
        with self.assertRaises(ValueError):
            validator._canonical_object(b'{"value":1,"value":2}\n', "probe")

    def test_review_claims_are_narrow_and_environment_limits_are_explicit(self) -> None:
        execution_true = {
            name for name, value in self.evidence["claims"].items() if value is True
        }
        self.assertEqual(
            execution_true,
            {"replay_executed", "model_evaluated", "formal_measurement_complete"},
        )
        review_true = {
            name for name, value in self.review["claims"].items() if value is True
        }
        self.assertEqual(
            review_true,
            {
                "replay_executed",
                "model_evaluated",
                "formal_measurement_complete",
                "same_machine_eval_repeatability_established",
            },
        )
        self.assertEqual(tuple(self.review["claims"]), contract.CLAIM_KEYS)
        for name in (
            "training_repeatability_established",
            "cross_machine_reproducibility",
            "resource_repeatability_established",
            "generalized_quality_improvement_established",
            "quality_improved",
            "real_content_behavior_established",
            "safety_rejection_success_established",
            "direct_desktop_execution_established",
            "merged_artifact",
            "portable_artifact",
            "commercial_use_eligible",
            "serving_eligible",
            "promotion_eligible",
            "runtime_eligible",
        ):
            with self.subTest(claim=name):
                self.assertFalse(self.review["claims"][name])
        self.assertFalse(self.review["runtime_eligible"])

        recovery = self.review["environment_recovery"]
        self.assertEqual(recovery, validator.ENVIRONMENT_RECOVERY)
        self.assertEqual(
            recovery["evidence_class"], "reviewer_observed_untracked_context"
        )
        self.assertFalse(recovery["independently_recomputable_from_tracked_receipts"])
        self.assertTrue(recovery["formal_environment_gate_passed"])
        self.assertFalse(recovery["original_base"]["available_when_recovery_began"])
        self.assertFalse(recovery["original_base"]["binary_identity_recovered"])
        self.assertEqual(
            recovery["restored_base"]["vendor"],
            "Astral python-build-standalone via uv",
        )
        self.assertTrue(recovery["restored_base"]["available_at_formal_execution"])
        self.assertFalse(recovery["dependency_lock"]["hash_locked"])
        self.assertFalse(recovery["dependency_lock"]["complete_transitive_closure"])
        self.assertFalse(
            recovery["dependency_lock"]["transitive_dependency_hashes_pinned"]
        )
        self.assertFalse(recovery["byte_identical_original_base_established"])
        self.assertFalse(recovery["hermetic_environment_established"])
        self.assertFalse(
            self.review["limitations"]["original_python_base_binary_identity_reproduced"]
        )
        self.assertFalse(
            self.review["limitations"]["complete_transitive_dependency_lock"]
        )
        self.assertFalse(self.review["limitations"]["resource_repeatability_tested"])
        self.assertFalse(
            self.review["limitations"]["full_eval_repeat_variance_established"]
        )
        self.assertFalse(
            self.review["limitations"]["external_execution_count_attested"]
        )

    def test_review_is_model_free_and_contains_no_machine_path_or_token_ids(self) -> None:
        source = (
            ROOT / "scripts/validate_mm003_post_training_eval_repeatability_result.py"
        ).read_text(encoding="utf-8")
        tree = ast.parse(source)
        forbidden_roots = {
            "accelerate",
            "bitsandbytes",
            "numpy",
            "peft",
            "PIL",
            "safetensors",
            "torch",
            "transformers",
        }
        imported_roots: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(
                    alias.name.partition(".")[0] for alias in node.names
                )
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                imported_roots.add(node.module.partition(".")[0])
        self.assertFalse(imported_roots & forbidden_roots)

        with (
            mock.patch.object(
                formal_runner,
                "_load_eval_dependencies",
                side_effect=AssertionError("result review must not import ML dependencies"),
            ),
            mock.patch.object(
                formal_runner,
                "_run_eval_only",
                side_effect=AssertionError("result review must not execute the model"),
            ),
        ):
            summary = validator.validate_repository(ROOT)
        self.assertTrue(summary["formal_gate_passed"])
        self.assertEqual(
            self.review["review_process"],
            {
                "model_reloaded": False,
                "cuda_used": False,
                "scorer_recomputed": True,
                "candidate_binding_recomputed": True,
                "evidence_rebuilt_from_frozen_inputs": True,
                "historical_timestamp_and_resources_reused_from_runner_evidence": True,
                "historical_timestamp_and_resources_independently_remeasured": False,
            },
        )

        serialized = self.review_payload.decode("utf-8")
        for marker in (
            str(ROOT),
            "C:\\Users\\",
            "\\\\",
            "/home/",
            "/tmp/",
            "generated_token_ids",
            '"token_ids"',
            '"hidden_states"',
            '"logits"',
        ):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, serialized)
        self.assertTrue(self.review["comparison"]["all_layers_exact"])
        self.assertEqual(
            self.review["scope"],
            "same_machine_registered_environment_fixed_nine_case_eval",
        )
        self.assertEqual(
            self.review["comparison_semantics"]["all_layers_exact_definition"],
            [
                "raw_utf8_output",
                "canonical_compiled_prediction",
                "canonical_metrics",
            ],
        )
        self.assertFalse(
            self.review["comparison_semantics"]["transformer_internal_layers_compared"]
        )
        self.assertFalse(
            self.review["comparison_semantics"][
                "generated_token_id_sequences_persisted"
            ]
        )
        self.assertEqual(
            self.review["scope_semantics"]["same_machine_definition"],
            "same_windows_host_and_registered_environment_fields",
        )
        self.assertFalse(self.review["scope_semantics"]["machine_id_attested"])
        self.assertFalse(self.review["scope_semantics"]["hardware_identity_attested"])

    def test_artifact_set_and_each_fixed_receipt_fail_closed(self) -> None:
        missing = self._copy_payloads()
        missing.pop("attempt_owner")
        with self.assertRaisesRegex(
            validator.MM003EvalRepeatabilityResultError, "ARTIFACT_SET_MISMATCH"
        ):
            validator.validate_execution_payloads(
                preregistration_payload=self.preregistration_payload,
                payloads=missing,
                context=self.context,
                source_hashes=self.source_hashes,
            )

        extra = self._copy_payloads()
        extra["failure"] = b"{}\n"
        with self.assertRaisesRegex(
            validator.MM003EvalRepeatabilityResultError, "ARTIFACT_SET_MISMATCH"
        ):
            validator.validate_execution_payloads(
                preregistration_payload=self.preregistration_payload,
                payloads=extra,
                context=self.context,
                source_hashes=self.source_hashes,
            )

        for name in validator.ARTIFACTS:
            with self.subTest(receipt=name):
                drifted = self._copy_payloads()
                drifted[name] += b" "
                with self.assertRaisesRegex(
                    validator.MM003EvalRepeatabilityResultError,
                    "RECEIPT_MISMATCH",
                ):
                    validator.validate_execution_payloads(
                        preregistration_payload=self.preregistration_payload,
                        payloads=drifted,
                        context=self.context,
                        source_hashes=self.source_hashes,
                    )

        with self.assertRaisesRegex(
            validator.MM003EvalRepeatabilityResultError,
            "PREREGISTRATION_RECEIPT_MISMATCH",
        ):
            validator.validate_execution_payloads(
                preregistration_payload=self.preregistration_payload + b" ",
                payloads=self.payloads,
                context=self.context,
                source_hashes=self.source_hashes,
            )

    def test_owner_and_preregistration_self_reseal_do_not_authorize_review(self) -> None:
        owner = self._parse_object(self.payloads["attempt_owner"], "owner")
        owner["protocol"]["freeze_commit"] = "0" * 40
        owner_payloads = self._copy_payloads()
        owner_payloads["attempt_owner"] = self._artifact_payload(owner)
        with self.assertRaisesRegex(
            validator.MM003EvalRepeatabilityResultError,
            "ATTEMPT_OWNER_BINDING_MISMATCH",
        ):
            self._validate_with_resealed_artifact_receipts(owner_payloads)

        preregistration = self._parse_object(
            self.preregistration_payload, "preregistration"
        )
        preregistration["execution_protocol"]["retry_count"] = 1
        resealed_preregistration = self._artifact_payload(preregistration)
        preregistration_receipt = {
            "path": validator.PREREGISTRATION_RECEIPT["path"],
            "bytes": len(resealed_preregistration),
            "sha256": contract.sha256_bytes(resealed_preregistration),
        }
        with (
            mock.patch.object(
                validator, "PREREGISTRATION_RECEIPT", preregistration_receipt
            ),
            self.assertRaises(validator.MM003EvalRepeatabilityResultError),
        ):
            validator.validate_execution_payloads(
                preregistration_payload=resealed_preregistration,
                payloads=self.payloads,
                context=self.context,
                source_hashes=self.source_hashes,
            )

    def test_candidate_raw_and_compiled_forgery_fails_after_receipt_reseal(self) -> None:
        candidate = copy.deepcopy(self.candidate)
        candidate["cases"][0]["raw_output"] = "not valid model JSON"
        payloads = self._copy_payloads()
        payloads["evaluation_candidate"] = self._artifact_payload(candidate)
        with self.assertRaises(validator.MM003EvalRepeatabilityResultError):
            self._validate_with_resealed_artifact_receipts(payloads)

        candidate = copy.deepcopy(self.candidate)
        candidate["predictions"]["records"][0]["tool"] = "forged.tool"
        candidate["cases"][0]["compiled_prediction"] = copy.deepcopy(
            candidate["predictions"]["records"][0]
        )
        payloads = self._copy_payloads()
        payloads["evaluation_candidate"] = self._artifact_payload(candidate)
        with self.assertRaises(validator.MM003EvalRepeatabilityResultError):
            self._validate_with_resealed_artifact_receipts(payloads)

    def test_external_predictions_cannot_diverge_from_candidate_or_reference(self) -> None:
        predictions = self._parse_object(self.payloads["predictions"], "predictions")
        predictions["producer"]["model_revision"] = "0" * 40
        payloads = self._copy_payloads()
        payloads["predictions"] = self._artifact_payload(predictions)
        with self.assertRaises(validator.MM003EvalRepeatabilityResultError):
            self._validate_with_resealed_artifact_receipts(payloads)

    def test_evidence_claim_comparison_and_receipt_forgery_fail_after_reseal(
        self,
    ) -> None:
        mutations: list[tuple[str, dict[str, Any]]] = []

        forged_claim = copy.deepcopy(self.evidence)
        forged_claim["claims"]["runtime_eligible"] = True
        mutations.append(("claim", forged_claim))

        forged_comparison = copy.deepcopy(self.evidence)
        forged_comparison["comparison"]["raw_outputs"]["exact"] = 8
        mutations.append(("comparison", forged_comparison))

        forged_gate = copy.deepcopy(self.evidence)
        forged_gate["gates"]["locked_environment"] = False
        mutations.append(("gate", forged_gate))

        forged_receipt = copy.deepcopy(self.evidence)
        forged_receipt["artifacts"]["attempt_owner"]["sha256"] = (
            "sha256:" + "0" * 64
        )
        mutations.append(("artifact_receipt", forged_receipt))

        for name, evidence in mutations:
            with self.subTest(mutation=name):
                payloads = self._copy_payloads()
                payloads["evidence"] = self._artifact_payload(evidence)
                with self.assertRaisesRegex(
                    validator.MM003EvalRepeatabilityResultError,
                    "EXECUTION_EVIDENCE_RECOMPUTATION_MISMATCH",
                ):
                    self._validate_with_resealed_artifact_receipts(payloads)

    def test_invalid_or_over_cap_resources_cannot_authorize_result_review(self) -> None:
        for field, value in (
            ("elapsed_seconds", True),
            ("peak_gpu_allocated_bytes", -1),
            ("peak_gpu_reserved_bytes", -1),
        ):
            with self.subTest(field=field, value=value):
                evidence = copy.deepcopy(self.evidence)
                evidence["resources"][field] = value
                payloads = self._copy_payloads()
                payloads["evidence"] = self._artifact_payload(evidence)
                with self.assertRaises(validator.MM003EvalRepeatabilityResultError):
                    validator.recompute_evidence(
                        preregistration_payload=self.preregistration_payload,
                        payloads=payloads,
                        context=self.context,
                        source_hashes=self.source_hashes,
                    )

        evidence = copy.deepcopy(self.evidence)
        evidence["resources"]["elapsed_seconds"] = (
            contract.RESOURCE_CAPS["elapsed_seconds"] + 1.0
        )
        payloads = self._copy_payloads()
        payloads["evidence"] = self._artifact_payload(evidence)
        expected, candidate, _ = validator.recompute_evidence(
            preregistration_payload=self.preregistration_payload,
            payloads=payloads,
            context=self.context,
            source_hashes=self.source_hashes,
        )
        self.assertFalse(expected["formal_gate_passed"])
        self.assertFalse(expected["gates"]["resource_caps"])
        self.assertEqual(
            expected["classification"], contract.RESOURCE_EXCEEDED_CLASSIFICATION
        )
        with self.assertRaisesRegex(
            validator.MM003EvalRepeatabilityResultError,
            "NARROW_REPEATABILITY_REVIEW_PRECONDITION_MISMATCH",
        ):
            validator.build_review(evidence=expected, candidate=candidate)

    def test_every_exactness_and_terminal_precondition_is_required(self) -> None:
        mutations: list[tuple[str, dict[str, Any]]] = []

        all_layers = copy.deepcopy(self.evidence)
        all_layers["comparison"]["all_layers_exact"] = False
        mutations.append(("all_layers", all_layers))

        tokens = copy.deepcopy(self.evidence)
        tokens["comparison"]["raw_outputs"]["generated_tokens_exact"] = 8
        mutations.append(("generated_tokens", tokens))

        fallback = copy.deepcopy(self.evidence)
        fallback["comparison"]["compiled_predictions"][
            "compiler_fallback_mismatch_case_ids"
        ] = [contract.CASE_ORDER[0]]
        mutations.append(("fallback", fallback))

        metrics = copy.deepcopy(self.evidence)
        metrics["comparison"]["metrics"]["exact"] = False
        mutations.append(("metrics", metrics))

        classification = copy.deepcopy(self.evidence)
        classification["classification"] = contract.RESOURCE_EXCEEDED_CLASSIFICATION
        mutations.append(("classification", classification))

        next_gate = copy.deepcopy(self.evidence)
        next_gate["next_gate"] = contract.FAILURE_CLASSIFICATION_GATE_ID
        mutations.append(("next_gate", next_gate))

        claims = copy.deepcopy(self.evidence)
        claims["claims"]["same_machine_eval_repeatability_established"] = True
        mutations.append(("execution_claim", claims))

        runtime = copy.deepcopy(self.evidence)
        runtime["runtime_eligible"] = True
        mutations.append(("runtime", runtime))

        for name, evidence in mutations:
            with self.subTest(precondition=name):
                with self.assertRaisesRegex(
                    validator.MM003EvalRepeatabilityResultError,
                    "NARROW_REPEATABILITY_REVIEW_PRECONDITION_MISMATCH",
                ):
                    validator.build_review(evidence=evidence, candidate=self.candidate)

        comparison = self.review["comparison"]
        self.assertTrue(comparison["all_layers_exact"])
        self.assertEqual(
            comparison["raw_outputs"]["generated_tokens_exact"],
            contract.EXPECTED_CASES,
        )
        self.assertEqual(
            comparison["compiled_predictions"][
                "compiler_fallback_mismatch_case_ids"
            ],
            [],
        )


if __name__ == "__main__":
    unittest.main()
