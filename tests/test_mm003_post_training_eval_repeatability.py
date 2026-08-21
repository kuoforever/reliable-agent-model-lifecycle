from __future__ import annotations

import ast
import copy
import json
import os
import socket
import sys
import tempfile
import unittest
from contextlib import ExitStack, nullcontext
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SRC))

from fullcycle_bridge import gui_grounding_eval_v2 as scorer  # noqa: E402
from fullcycle_bridge import (  # noqa: E402
    mm003_post_training_eval_repeatability as contract,
)
from scripts import run_mm003_post_training_eval_repeatability as runner  # noqa: E402


class MM003PostTrainingEvalRepeatabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.context = runner.load_authenticated_context()
        cls.source_hashes = runner.protocol_source_hashes()
        cls.preregistration = contract.expected_preregistration(
            freeze_status="frozen",
            source_hashes=cls.source_hashes,
            upstream_preregistration=cls.context["upstream_preregistration"],
            reference_evidence=cls.context["reference_evidence"],
            reference_predictions=cls.context["reference_predictions"],
            result_review=cls.context["result_review"],
            suite=cls.context["suite"],
        )
        cls.preregistration_payload = contract.artifact_json_bytes(cls.preregistration)
        cls.reference = cls.context["reference_evidence"]["evaluation"]

    def replay_from_reference(self) -> dict[str, Any]:
        replay = copy.deepcopy(self.reference)
        replay["execution"] = contract.expected_replay_execution()
        return replay

    def attempt_owner_payload(self, owner_token: str = "a" * 64) -> bytes:
        return contract.artifact_json_bytes(
            contract.build_attempt_owner(
                protocol_freeze_commit="1" * 40,
                preregistration_payload=self.preregistration_payload,
                owner_token=owner_token,
            )
        )

    def evidence(
        self,
        replay: dict[str, Any],
        *,
        resources: dict[str, Any] | None = None,
        adapter_receipts: dict[str, Any] | None = None,
        model_files: list[dict[str, Any]] | None = None,
        captured_at_utc: str = "2026-08-20T00:00:00+00:00",
    ) -> dict[str, Any]:
        candidate = contract.build_evaluation_candidate(
            protocol_freeze_commit="1" * 40,
            preregistration_payload=self.preregistration_payload,
            execution=replay["execution"],
            cases=replay["cases"],
            predictions=replay["predictions"],
            suite=self.context["suite"],
            screenshot_receipts=self.context["screenshot_receipts"],
        )
        return contract.build_evidence(
            preregistration_payload=self.preregistration_payload,
            attempt_owner_payload=self.attempt_owner_payload(),
            evaluation_candidate_payload=contract.artifact_json_bytes(candidate),
            predictions_payload=contract.artifact_json_bytes(replay["predictions"]),
            protocol_freeze_commit="1" * 40,
            reference_evaluation=self.reference,
            replay_evaluation=replay,
            preregistration=self.preregistration,
            suite=self.context["suite"],
            screenshot_receipts=self.context["screenshot_receipts"],
            environment=contract.LOCKED_ENVIRONMENT,
            model_files=(model_files or self.preregistration["model"]["files"]),
            adapter_receipts=(adapter_receipts or contract.ADAPTER_RECEIPTS),
            resources=(
                resources
                or {
                    "elapsed_seconds": 1.0,
                    "peak_gpu_allocated_bytes": 1,
                    "peak_gpu_reserved_bytes": 1,
                }
            ),
            captured_at_utc=captured_at_utc,
        )

    def execute_with_fakes(
        self,
        temp_root: Path,
        *,
        scoring_failure: bool = False,
        interrupt_after_evidence_write: bool = False,
        interrupt_after_output_claim: bool = False,
    ) -> dict[str, Any]:
        preregistration_path = temp_root / contract.PREREGISTRATION_PATH
        preregistration_path.parent.mkdir(parents=True, exist_ok=True)
        preregistration_path.write_bytes(self.preregistration_payload)
        (temp_root / "work").mkdir(exist_ok=True)
        replay = self.replay_from_reference()
        candidate = contract.build_evaluation_candidate(
            protocol_freeze_commit="1" * 40,
            preregistration_payload=self.preregistration_payload,
            execution=replay["execution"],
            cases=replay["cases"],
            predictions=replay["predictions"],
            suite=self.context["suite"],
            screenshot_receipts=self.context["screenshot_receipts"],
        )
        frozen_inputs = _FakeFrozenInputs(
            model_receipts=self.preregistration["model"]["files"],
            adapter_receipts=contract.ADAPTER_RECEIPTS,
        )

        def fake_eval_only(**kwargs: Any) -> dict[str, Any]:
            kwargs["counters"].update(contract.expected_replay_execution())
            kwargs["completed_case_ids"].extend(contract.CASE_ORDER)
            return copy.deepcopy(candidate)

        original_write = runner._write_output_artifact
        original_score = runner.scorer.score_predictions
        original_rename = os.rename
        score_calls = 0

        def score_with_execution_failure(
            suite: dict[str, Any], predictions: dict[str, Any]
        ) -> dict[str, Any]:
            nonlocal score_calls
            score_calls += 1
            if score_calls >= 2:
                raise RuntimeError("scoring failed")
            return original_score(suite, predictions)

        def write_with_optional_interrupt(
            guard: Any, path: Path, payload: bytes
        ) -> None:
            original_write(guard, path, payload)
            if (
                interrupt_after_evidence_write
                and path.name == Path(contract.EVIDENCE_ARTIFACT).name
            ):
                raise KeyboardInterrupt

        def rename_then_interrupt(source: Path, destination: Path) -> None:
            original_rename(source, destination)
            raise KeyboardInterrupt

        dependencies = (
            _FakeTorch(),
            _FakeImageClass,
            _RecordingPeftClass(),
            _FakeProcessorClass,
            _RecordingModelClass(),
            _FakeBitsAndBytesConfig,
        )
        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(runner, "ROOT", temp_root))
            stack.enter_context(
                mock.patch.object(
                    runner, "load_authenticated_context", return_value=self.context
                )
            )
            stack.enter_context(
                mock.patch.object(
                    runner, "protocol_source_hashes", return_value=self.source_hashes
                )
            )
            stack.enter_context(
                mock.patch.object(runner, "_validate_formal_python_execution_mode")
            )
            stack.enter_context(
                mock.patch.object(runner, "_validate_protocol_freeze_commit")
            )
            stack.enter_context(
                mock.patch.object(
                    runner.upstream_runner, "_validate_local_dependency_wheel"
                )
            )
            stack.enter_context(
                mock.patch.object(runner.upstream_runner, "_enable_offline_execution")
            )
            stack.enter_context(
                mock.patch.object(
                    runner.upstream_runner,
                    "observed_environment",
                    return_value=contract.LOCKED_ENVIRONMENT,
                )
            )
            stack.enter_context(
                mock.patch.object(
                    runner, "_FrozenInputFileSet", return_value=frozen_inputs
                )
            )
            stack.enter_context(
                mock.patch.object(
                    runner, "_load_eval_dependencies", return_value=dependencies
                )
            )
            stack.enter_context(
                mock.patch.object(runner, "_run_eval_only", side_effect=fake_eval_only)
            )
            if scoring_failure:
                stack.enter_context(
                    mock.patch.object(
                        runner.scorer,
                        "score_predictions",
                        side_effect=score_with_execution_failure,
                    )
                )
            if interrupt_after_evidence_write:
                stack.enter_context(
                    mock.patch.object(
                        runner,
                        "_write_output_artifact",
                        side_effect=write_with_optional_interrupt,
                    )
                )
            if interrupt_after_output_claim:
                stack.enter_context(
                    mock.patch.object(
                        runner.os, "rename", side_effect=rename_then_interrupt
                    )
                )
            return runner.execute_frozen_protocol(
                model_snapshot=temp_root / contract.MODEL_SNAPSHOT_ROOT,
                preregistration_path=preregistration_path,
                protocol_freeze_commit="1" * 40,
                output_dir=temp_root / contract.RUN_OUTPUT_ROOT,
            )

    def test_builder_is_deterministic_and_frozen_claims_are_negative(self) -> None:
        rebuilt = contract.expected_preregistration(
            freeze_status="frozen",
            source_hashes=self.source_hashes,
            upstream_preregistration=self.context["upstream_preregistration"],
            reference_evidence=self.context["reference_evidence"],
            reference_predictions=self.context["reference_predictions"],
            result_review=self.context["result_review"],
            suite=self.context["suite"],
        )
        self.assertEqual(rebuilt, self.preregistration)
        self.assertEqual(
            contract.validate_preregistration(
                rebuilt,
                source_hashes=self.source_hashes,
                upstream_preregistration=self.context["upstream_preregistration"],
                reference_evidence=self.context["reference_evidence"],
                reference_predictions=self.context["reference_predictions"],
                result_review=self.context["result_review"],
                suite=self.context["suite"],
            ),
            rebuilt,
        )
        self.assertTrue(all(value is False for value in rebuilt["claims"].values()))
        self.assertEqual(
            rebuilt["next_gate_after_freeze"]["gate_id"],
            contract.EXECUTION_GATE_ID,
        )
        self.assertFalse(rebuilt["runtime_eligible"])

    def test_frozen_preregistration_bytes_hash_and_prepare_check(self) -> None:
        path = ROOT / contract.PREREGISTRATION_PATH
        payload = path.read_bytes()
        self.assertEqual(len(payload), 22_951)
        self.assertEqual(
            contract.sha256_bytes(payload),
            "sha256:723db665f98e53ef2fe968ee7c6fe663b42d79b86176eef5cf70f11ccc4a312b",
        )
        self.assertEqual(payload, contract.artifact_json_bytes(self.preregistration))
        self.assertEqual(
            runner.prepare_protocol(
                output_path=path,
                freeze_status="frozen",
                check=True,
            ),
            {
                "case_count": 9,
                "freeze_status": "frozen",
                "next_gate": contract.EXECUTION_GATE_ID,
                "protocol_sources": 17,
                "sha256": contract.sha256_bytes(payload),
                "valid": True,
            },
        )

    def test_attempt_owner_is_closed_and_recovery_requires_exact_process_token(
        self,
    ) -> None:
        payload = self.attempt_owner_payload()
        self.assertEqual(
            contract.artifact_json_bytes(
                contract.validate_attempt_owner(
                    payload,
                    protocol_freeze_commit="1" * 40,
                    preregistration_payload=self.preregistration_payload,
                )
            ),
            payload,
        )
        tampered = contract.parse_strict_json_bytes(
            payload, location="$.attempt_owner"
        )
        tampered["output_id"] = "forged-output"
        with self.assertRaisesRegex(
            contract.MM003EvalRepeatabilityError,
            "ATTEMPT_OWNER_BINDING_MISMATCH",
        ):
            contract.validate_attempt_owner(
                contract.artifact_json_bytes(tampered),
                protocol_freeze_commit="1" * 40,
                preregistration_payload=self.preregistration_payload,
            )

        fixture_parent = ROOT / "work" / "test-fixtures"
        fixture_parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=fixture_parent) as temp_dir:
            owner_path = Path(temp_dir) / "attempt-owner.json"
            owner_path.write_bytes(payload)
            different_process = self.attempt_owner_payload("b" * 64)
            self.assertIsNone(
                runner._observe_attempt_owner(
                    owner_path, different_process, strict=False
                )
            )
            with self.assertRaisesRegex(RuntimeError, "differs from this process"):
                runner._observe_attempt_owner(
                    owner_path, different_process, strict=True
                )

    def test_preregistration_tamper_and_self_reseal_fail_closed(self) -> None:
        candidate = copy.deepcopy(self.preregistration)
        candidate["execution_protocol"]["retry_count"] = 1
        with self.assertRaisesRegex(
            contract.MM003EvalRepeatabilityError, "PREREGISTRATION_MISMATCH"
        ):
            contract.validate_preregistration(
                candidate,
                source_hashes=self.source_hashes,
                upstream_preregistration=self.context["upstream_preregistration"],
                reference_evidence=self.context["reference_evidence"],
                reference_predictions=self.context["reference_predictions"],
                result_review=self.context["result_review"],
                suite=self.context["suite"],
            )

        resealed_hashes = dict(self.source_hashes)
        resealed_hashes["repeatability_runner"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(
            contract.MM003EvalRepeatabilityError, "PREREGISTRATION_MISMATCH"
        ):
            contract.validate_preregistration(
                self.preregistration,
                source_hashes=resealed_hashes,
                upstream_preregistration=self.context["upstream_preregistration"],
                reference_evidence=self.context["reference_evidence"],
                reference_predictions=self.context["reference_predictions"],
                result_review=self.context["result_review"],
                suite=self.context["suite"],
            )

    def test_strict_json_rejects_duplicate_and_nonfinite_values(self) -> None:
        for payload in (b'{"a":1,"a":2}', b'{"value":NaN}'):
            with self.subTest(payload=payload):
                with self.assertRaises(Exception):
                    contract.parse_strict_json_bytes(payload, location="$.test")

    def test_json_contract_equality_is_type_strict(self) -> None:
        preregistration = copy.deepcopy(self.preregistration)
        preregistration["execution_protocol"]["run_count"] = True
        with self.assertRaisesRegex(
            contract.MM003EvalRepeatabilityError, "PREREGISTRATION_MISMATCH"
        ):
            contract.validate_preregistration(
                preregistration,
                source_hashes=self.source_hashes,
                upstream_preregistration=self.context["upstream_preregistration"],
                reference_evidence=self.context["reference_evidence"],
                reference_predictions=self.context["reference_predictions"],
                result_review=self.context["result_review"],
                suite=self.context["suite"],
            )

        replay = self.replay_from_reference()
        replay["execution"]["training_runs"] = False
        with self.assertRaisesRegex(
            contract.MM003EvalRepeatabilityError, "EVALUATION_EXECUTION_MISMATCH"
        ):
            contract.validate_completed_evaluation(
                replay,
                suite=self.context["suite"],
                screenshot_receipts=self.context["screenshot_receipts"],
            )

        replay = self.replay_from_reference()
        replay["score"]["metrics"]["action_accuracy"]["correct"] = 3.0
        with self.assertRaisesRegex(
            contract.MM003EvalRepeatabilityError,
            "EVALUATION_SCORE_RECOMPUTATION_MISMATCH",
        ):
            contract.validate_completed_evaluation(
                replay,
                suite=self.context["suite"],
                screenshot_receipts=self.context["screenshot_receipts"],
            )

        model_files = copy.deepcopy(self.preregistration["model"]["files"])
        model_files[0]["bytes"] = float(model_files[0]["bytes"])
        evidence = self.evidence(self.replay_from_reference(), model_files=model_files)
        self.assertFalse(evidence["gates"]["exact_model_files"])
        self.assertFalse(evidence["formal_gate_passed"])

    def test_captured_timestamp_is_canonical_utc_and_machine_path_safe(self) -> None:
        for value in (
            r"C:\\Users\\secret",
            "2026-08-20T00:00:00",
            "2026-08-20T08:00:00+08:00",
            "2026-08-20T00:00:00Z",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    contract.MM003EvalRepeatabilityError, "CAPTURED_AT_UTC_INVALID"
                ),
            ):
                self.evidence(self.replay_from_reference(), captured_at_utc=value)

    def test_exact_replay_is_measurement_complete_not_self_authorized(self) -> None:
        evidence = self.evidence(self.replay_from_reference())
        comparison = evidence["comparison"]
        self.assertTrue(comparison["all_layers_exact"])
        self.assertEqual(comparison["raw_outputs"]["exact"], 9)
        self.assertEqual(comparison["compiled_predictions"]["exact"], 9)
        self.assertTrue(comparison["metrics"]["exact"])
        self.assertTrue(evidence["formal_gate_passed"])
        self.assertTrue(evidence["claims"]["formal_measurement_complete"])
        self.assertFalse(
            evidence["claims"]["same_machine_eval_repeatability_established"]
        )
        self.assertEqual(evidence["next_gate"], contract.RESULT_REVIEW_GATE_ID)

    def test_raw_only_drift_remains_a_valid_completed_measurement(self) -> None:
        replay = self.replay_from_reference()
        replay["cases"][0]["raw_output"] = " " + replay["cases"][0]["raw_output"]
        evidence = self.evidence(replay)
        comparison = evidence["comparison"]
        self.assertFalse(comparison["all_layers_exact"])
        self.assertTrue(comparison["raw_drift_compiled_and_metrics_exact"])
        self.assertEqual(comparison["raw_outputs"]["mismatch_case_ids"], ["ground-001"])
        self.assertEqual(comparison["compiled_predictions"]["exact"], 9)
        self.assertTrue(comparison["metrics"]["exact"])
        self.assertTrue(evidence["formal_gate_passed"])
        self.assertEqual(evidence["next_gate"], contract.RESULT_REVIEW_GATE_ID)

    def test_generated_token_drift_is_diagnostic_not_raw_output_drift(self) -> None:
        replay = self.replay_from_reference()
        replay["cases"][0]["generated_tokens"] += 1
        evidence = self.evidence(replay)
        comparison = evidence["comparison"]
        self.assertTrue(comparison["all_layers_exact"])
        self.assertEqual(comparison["raw_outputs"]["exact"], 9)
        self.assertFalse(comparison["raw_outputs"]["token_counts_exact"])
        self.assertEqual(
            comparison["raw_outputs"]["generated_token_mismatch_case_ids"],
            ["ground-001"],
        )
        self.assertTrue(evidence["formal_gate_passed"])

    def test_compiled_or_metric_drift_is_visible_even_when_measurement_completes(
        self,
    ) -> None:
        replay = self.replay_from_reference()
        raw = json.loads(replay["cases"][0]["raw_output"])
        raw.update(
            {
                "disposition": "fallback",
                "tool": None,
                "arguments": None,
                "ref": None,
                "bbox": None,
                "reason": "insufficient_evidence",
            }
        )
        raw_output = json.dumps(raw, ensure_ascii=False, separators=(",", ":"))
        compiled = contract.upstream.baseline.compile_raw_prediction(
            raw_output, self.context["suite"]["cases"][0]
        )
        replay["cases"][0]["raw_output"] = raw_output
        replay["cases"][0]["compiled_prediction"] = compiled
        replay["cases"][0]["compiler_fallback"] = False
        replay["predictions"]["records"][0] = compiled
        replay["score"] = scorer.score_predictions(
            self.context["suite"], replay["predictions"]
        )
        evidence = self.evidence(replay)
        comparison = evidence["comparison"]
        self.assertTrue(comparison["metric_drift"])
        self.assertIn("action_accuracy", comparison["metrics"]["mismatch_metric_names"])
        self.assertTrue(evidence["formal_gate_passed"])

    def test_stored_compiler_or_score_forgery_fails_closed(self) -> None:
        replay = self.replay_from_reference()
        replay["cases"][0]["compiled_prediction"]["reason"] = "forged"
        with self.assertRaisesRegex(
            contract.MM003EvalRepeatabilityError,
            "EVALUATION_CASE_BINDING_MISMATCH",
        ):
            contract.validate_completed_evaluation(
                replay,
                suite=self.context["suite"],
                screenshot_receipts=self.context["screenshot_receipts"],
            )

        replay = self.replay_from_reference()
        replay["cases"][0]["machine_path"] = r"C:\\Users\\attacker"
        with self.assertRaisesRegex(
            contract.MM003EvalRepeatabilityError,
            "EVALUATION_CASE_BINDING_MISMATCH",
        ):
            contract.validate_completed_evaluation(
                replay,
                suite=self.context["suite"],
                screenshot_receipts=self.context["screenshot_receipts"],
            )

        replay = self.replay_from_reference()
        replay["score"]["metrics"]["action_accuracy"]["value"] = 1.0
        with self.assertRaisesRegex(
            contract.MM003EvalRepeatabilityError,
            "EVALUATION_SCORE_RECOMPUTATION_MISMATCH",
        ):
            contract.validate_completed_evaluation(
                replay,
                suite=self.context["suite"],
                screenshot_receipts=self.context["screenshot_receipts"],
            )

    def test_candidate_and_predictions_artifacts_are_exactly_bound(self) -> None:
        replay = self.replay_from_reference()
        candidate = contract.build_evaluation_candidate(
            protocol_freeze_commit="1" * 40,
            preregistration_payload=self.preregistration_payload,
            execution=replay["execution"],
            cases=replay["cases"],
            predictions=replay["predictions"],
            suite=self.context["suite"],
            screenshot_receipts=self.context["screenshot_receipts"],
        )
        payload = contract.artifact_json_bytes(candidate)
        self.assertEqual(
            contract.validate_evaluation_candidate(
                payload,
                protocol_freeze_commit="1" * 40,
                preregistration_payload=self.preregistration_payload,
                replay_evaluation=replay,
                suite=self.context["suite"],
                screenshot_receipts=self.context["screenshot_receipts"],
            ),
            candidate,
        )
        tampered = copy.deepcopy(candidate)
        tampered["output_id"] = "forged-output"
        with self.assertRaisesRegex(
            contract.MM003EvalRepeatabilityError,
            "EVALUATION_CANDIDATE_BINDING_MISMATCH",
        ):
            contract.validate_evaluation_candidate(
                contract.artifact_json_bytes(tampered),
                protocol_freeze_commit="1" * 40,
                preregistration_payload=self.preregistration_payload,
                replay_evaluation=replay,
                suite=self.context["suite"],
                screenshot_receipts=self.context["screenshot_receipts"],
            )
        forged_predictions = copy.deepcopy(replay["predictions"])
        forged_predictions["producer"]["model_id"] = "unrelated/model"
        with self.assertRaisesRegex(
            contract.MM003EvalRepeatabilityError,
            "PREDICTIONS_ARTIFACT_BINDING_MISMATCH",
        ):
            contract.build_evidence(
                preregistration_payload=self.preregistration_payload,
                attempt_owner_payload=self.attempt_owner_payload(),
                evaluation_candidate_payload=payload,
                predictions_payload=contract.artifact_json_bytes(forged_predictions),
                protocol_freeze_commit="1" * 40,
                reference_evaluation=self.reference,
                replay_evaluation=replay,
                preregistration=self.preregistration,
                suite=self.context["suite"],
                screenshot_receipts=self.context["screenshot_receipts"],
                environment=contract.LOCKED_ENVIRONMENT,
                model_files=self.preregistration["model"]["files"],
                adapter_receipts=contract.ADAPTER_RECEIPTS,
                resources={
                    "elapsed_seconds": 1.0,
                    "peak_gpu_allocated_bytes": 1,
                    "peak_gpu_reserved_bytes": 1,
                },
                captured_at_utc="2026-08-20T00:00:00+00:00",
            )

        forged_replay = self.replay_from_reference()
        forged_record = copy.deepcopy(forged_replay["predictions"]["records"][0])
        forged_record["reason"] = "forged_reason"
        forged_replay["predictions"]["records"][0] = forged_record
        forged_replay["cases"][0]["compiled_prediction"] = forged_record
        with self.assertRaisesRegex(
            contract.MM003EvalRepeatabilityError,
            "FAILURE_CANDIDATE_AUTHENTICATED_INPUT_MISMATCH",
        ):
            contract.build_evaluation_candidate(
                protocol_freeze_commit="1" * 40,
                preregistration_payload=self.preregistration_payload,
                execution=forged_replay["execution"],
                cases=forged_replay["cases"],
                predictions=forged_replay["predictions"],
                suite=self.context["suite"],
                screenshot_receipts=self.context["screenshot_receipts"],
            )

    def test_resource_or_integrity_failure_routes_to_registered_classification(
        self,
    ) -> None:
        at_caps = copy.deepcopy(contract.RESOURCE_CAPS)
        self.assertTrue(
            self.evidence(self.replay_from_reference(), resources=at_caps)[
                "formal_gate_passed"
            ]
        )
        for name in contract.RESOURCE_CAPS:
            over = copy.deepcopy(contract.RESOURCE_CAPS)
            over[name] += 1
            with self.subTest(over_cap=name):
                exceeded = self.evidence(self.replay_from_reference(), resources=over)
                self.assertFalse(exceeded["formal_gate_passed"])
                self.assertEqual(
                    exceeded["classification"],
                    contract.RESOURCE_EXCEEDED_CLASSIFICATION,
                )

        resources = {
            "elapsed_seconds": contract.RESOURCE_CAPS["elapsed_seconds"] + 1,
            "peak_gpu_allocated_bytes": 1,
            "peak_gpu_reserved_bytes": 1,
        }
        evidence = self.evidence(self.replay_from_reference(), resources=resources)
        self.assertFalse(evidence["formal_gate_passed"])
        self.assertEqual(
            evidence["classification"], contract.RESOURCE_EXCEEDED_CLASSIFICATION
        )
        self.assertEqual(evidence["next_gate"], contract.FAILURE_CLASSIFICATION_GATE_ID)

        receipts = copy.deepcopy(contract.ADAPTER_RECEIPTS)
        receipts["readme"]["bytes"] += 1
        evidence = self.evidence(
            self.replay_from_reference(), adapter_receipts=receipts
        )
        self.assertFalse(evidence["formal_gate_passed"])
        self.assertEqual(
            evidence["classification"], contract.INTEGRITY_FAILURE_CLASSIFICATION
        )

        for invalid in (True, float("nan"), float("inf")):
            resources = {
                "elapsed_seconds": invalid,
                "peak_gpu_allocated_bytes": 1,
                "peak_gpu_reserved_bytes": 1,
            }
            with (
                self.subTest(invalid_resource=invalid),
                self.assertRaises(contract.MM003EvalRepeatabilityError),
            ):
                self.evidence(self.replay_from_reference(), resources=resources)

    def test_claim_gate_is_independent_and_never_emits_positive_deployment_claims(
        self,
    ) -> None:
        forged = contract.execution_claims(formal_gate_passed=True)
        forged["promotion_eligible"] = True
        with mock.patch.object(contract, "execution_claims", return_value=forged):
            evidence = self.evidence(self.replay_from_reference())
        self.assertFalse(evidence["gates"]["fail_closed_claims"])
        self.assertFalse(evidence["formal_gate_passed"])
        self.assertFalse(evidence["claims"]["promotion_eligible"])
        self.assertFalse(evidence["claims"]["runtime_eligible"])

    def test_consumed_failure_receipt_is_closed_typed_and_stage_bound(self) -> None:
        counters = runner._new_counters()
        failure = contract.build_failure(
            protocol_freeze_commit="1" * 40,
            preregistration_payload=self.preregistration_payload,
            attempt_owner_payload=self.attempt_owner_payload(),
            stage="output_reservation",
            exception_type="KeyboardInterrupt",
            exception_code=None,
            exception_location=None,
            counters=counters,
            completed_case_ids=[],
            suite=self.context["suite"],
            screenshot_receipts=self.context["screenshot_receipts"],
            evaluation_candidate_payload=None,
            predictions_payload=None,
        )
        payload = contract.artifact_json_bytes(failure)
        self.assertEqual(
            contract.validate_failure(
                payload,
                protocol_freeze_commit="1" * 40,
                preregistration_payload=self.preregistration_payload,
                attempt_owner_payload=self.attempt_owner_payload(),
                suite=self.context["suite"],
                screenshot_receipts=self.context["screenshot_receipts"],
                evaluation_candidate_payload=None,
                predictions_payload=None,
            ),
            failure,
        )
        tampered = copy.deepcopy(failure)
        tampered["failure_version"] = True
        with self.assertRaisesRegex(
            contract.MM003EvalRepeatabilityError, "FAILURE_RECEIPT_MISMATCH"
        ):
            contract.validate_failure(
                contract.artifact_json_bytes(tampered),
                protocol_freeze_commit="1" * 40,
                preregistration_payload=self.preregistration_payload,
                attempt_owner_payload=self.attempt_owner_payload(),
                suite=self.context["suite"],
                screenshot_receipts=self.context["screenshot_receipts"],
                evaluation_candidate_payload=None,
                predictions_payload=None,
            )

        impossible = runner._new_counters()
        impossible["independent_adapter_load_attempts"] = 1
        with self.assertRaisesRegex(
            contract.MM003EvalRepeatabilityError,
            "FAILURE_CROSS_STAGE_COUNTER_CAUSALITY_INVALID",
        ):
            contract.build_failure(
                protocol_freeze_commit="1" * 40,
                preregistration_payload=self.preregistration_payload,
                attempt_owner_payload=self.attempt_owner_payload(),
                stage="independent_adapter_load_and_eval",
                exception_type="RuntimeError",
                exception_code=None,
                exception_location=None,
                counters=impossible,
                completed_case_ids=[],
                suite=self.context["suite"],
                screenshot_receipts=self.context["screenshot_receipts"],
                evaluation_candidate_payload=None,
                predictions_payload=None,
            )

        tampered_suite = copy.deepcopy(self.context["suite"])
        tampered_suite["suite_id"] += "-forged"
        with self.assertRaisesRegex(
            contract.MM003EvalRepeatabilityError,
            "PREREGISTRATION_MM002_INPUT_BINDING_MISMATCH",
        ):
            contract.build_failure(
                protocol_freeze_commit="1" * 40,
                preregistration_payload=self.preregistration_payload,
                attempt_owner_payload=self.attempt_owner_payload(),
                stage="output_reservation",
                exception_type="RuntimeError",
                exception_code=None,
                exception_location=None,
                counters=runner._new_counters(),
                completed_case_ids=[],
                suite=tampered_suite,
                screenshot_receipts=self.context["screenshot_receipts"],
                evaluation_candidate_payload=None,
                predictions_payload=None,
            )

        progress_gap = runner._new_counters()
        progress_gap["fresh_base_load_attempts"] = 1
        progress_gap["fresh_base_loads"] = 1
        progress_gap["independent_adapter_load_attempts"] = 1
        progress_gap["independent_adapter_loads"] = 1
        progress_gap["full_eval_run_attempts"] = 1
        progress_gap["generate_attempts"] = 3
        with self.assertRaisesRegex(
            contract.MM003EvalRepeatabilityError,
            "FAILURE_GENERATE_PROGRESS_INVALID",
        ):
            contract.build_failure(
                protocol_freeze_commit="1" * 40,
                preregistration_payload=self.preregistration_payload,
                attempt_owner_payload=self.attempt_owner_payload(),
                stage="independent_adapter_load_and_eval",
                exception_type="RuntimeError",
                exception_code=None,
                exception_location=None,
                counters=progress_gap,
                completed_case_ids=[],
                suite=self.context["suite"],
                screenshot_receipts=self.context["screenshot_receipts"],
                evaluation_candidate_payload=None,
                predictions_payload=None,
            )

        stage_mismatch = runner._new_counters()
        stage_mismatch["fresh_base_load_attempts"] = 1
        with self.assertRaisesRegex(
            contract.MM003EvalRepeatabilityError,
            "FAILURE_STAGE_COUNTER_ENVELOPE_INVALID",
        ):
            contract.build_failure(
                protocol_freeze_commit="1" * 40,
                preregistration_payload=self.preregistration_payload,
                attempt_owner_payload=self.attempt_owner_payload(),
                stage="output_reservation",
                exception_type="RuntimeError",
                exception_code=None,
                exception_location=None,
                counters=stage_mismatch,
                completed_case_ids=[],
                suite=self.context["suite"],
                screenshot_receipts=self.context["screenshot_receipts"],
                evaluation_candidate_payload=None,
                predictions_payload=None,
            )

    def test_scoring_failure_binds_candidate_and_allows_blocked_network_receipt(
        self,
    ) -> None:
        replay = self.replay_from_reference()
        candidate = contract.build_evaluation_candidate(
            protocol_freeze_commit="1" * 40,
            preregistration_payload=self.preregistration_payload,
            execution=replay["execution"],
            cases=replay["cases"],
            predictions=replay["predictions"],
            suite=self.context["suite"],
            screenshot_receipts=self.context["screenshot_receipts"],
        )
        candidate_payload = contract.artifact_json_bytes(candidate)
        final_counters = contract.expected_replay_execution()
        final_counters["network_attempts"] = 2
        failure = contract.build_failure(
            protocol_freeze_commit="1" * 40,
            preregistration_payload=self.preregistration_payload,
            attempt_owner_payload=self.attempt_owner_payload(),
            stage="total_scoring",
            exception_type="RuntimeError",
            exception_code=None,
            exception_location=None,
            counters=final_counters,
            completed_case_ids=list(contract.CASE_ORDER),
            suite=self.context["suite"],
            screenshot_receipts=self.context["screenshot_receipts"],
            evaluation_candidate_payload=candidate_payload,
            predictions_payload=None,
        )
        self.assertEqual(failure["counters"]["network_attempts"], 2)
        self.assertIsNotNone(failure["artifacts"]["evaluation_candidate"])
        self.assertIsNone(failure["artifacts"]["predictions"])

        forged = copy.deepcopy(candidate)
        forged["cases"][0]["machine_path"] = r"C:\\secret"
        with self.assertRaisesRegex(
            contract.MM003EvalRepeatabilityError,
            "FAILURE_CANDIDATE_CASE_FIELD_SET_MISMATCH",
        ):
            contract.build_failure(
                protocol_freeze_commit="1" * 40,
                preregistration_payload=self.preregistration_payload,
                attempt_owner_payload=self.attempt_owner_payload(),
                stage="total_scoring",
                exception_type="RuntimeError",
                exception_code=None,
                exception_location=None,
                counters=final_counters,
                completed_case_ids=list(contract.CASE_ORDER),
                suite=self.context["suite"],
                screenshot_receipts=self.context["screenshot_receipts"],
                evaluation_candidate_payload=contract.artifact_json_bytes(forged),
                predictions_payload=None,
            )

    def test_eval_only_runner_ast_forbids_training_and_model_save_calls(self) -> None:
        source = (
            ROOT / contract.PROTOCOL_SOURCE_PATHS["repeatability_runner"]
        ).read_text(encoding="utf-8")
        tree = ast.parse(source)
        forbidden_imports = {
            "LoraConfig",
            "TaskType",
            "get_peft_model",
            "prepare_model_for_kbit_training",
        }
        imported = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            for alias in node.names
        }
        self.assertTrue(forbidden_imports.isdisjoint(imported))
        forbidden_calls = {"train", "backward", "step", "save_pretrained"}
        calls = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        self.assertTrue(forbidden_calls.isdisjoint(calls))
        self.assertNotIn("fixtures/mm003_post_training_v1", source)

    def test_fake_eval_loads_once_calls_nine_times_and_never_retries(self) -> None:
        torch = _FakeTorch()
        model_class = _RecordingModelClass()
        peft_class = _RecordingPeftClass()
        dependencies = (
            torch,
            _FakeImageClass,
            peft_class,
            _FakeProcessorClass,
            model_class,
            _FakeBitsAndBytesConfig,
        )
        outputs = [
            (item["raw_output"], item["generated_tokens"])
            for item in self.reference["cases"]
        ]
        counters = runner._new_counters()
        completed: list[str] = []
        with (
            mock.patch.object(runner.upstream_runner, "_seed_all"),
            mock.patch.object(
                runner.upstream_runner,
                "_quantization_config",
                return_value={"frozen": True},
            ),
            mock.patch.object(
                runner.base_runner, "_generate_one", side_effect=outputs
            ) as generate,
        ):
            candidate = runner._run_eval_only(
                dependencies=dependencies,
                model_snapshot=Path("frozen-model"),
                adapter_dir=Path("frozen-adapter"),
                suite=self.context["suite"],
                screenshot_receipts=self.context["screenshot_receipts"],
                screenshot_payloads=self.context["screenshot_payloads"],
                counters=counters,
                completed_case_ids=completed,
                protocol_freeze_commit="1" * 40,
                preregistration_payload=self.preregistration_payload,
            )
        self.assertEqual(generate.call_count, 9)
        self.assertEqual(completed, list(contract.CASE_ORDER))
        self.assertEqual(candidate["execution"], contract.expected_replay_execution())
        self.assertEqual(model_class.calls, 1)
        self.assertEqual(peft_class.calls, 1)
        self.assertTrue(model_class.kwargs["local_files_only"])
        self.assertTrue(peft_class.kwargs["local_files_only"])
        self.assertFalse(peft_class.kwargs["is_trainable"])

    def test_fake_eval_failure_has_no_internal_retry(self) -> None:
        outputs: list[object] = [
            (item["raw_output"], item["generated_tokens"])
            for item in self.reference["cases"][:3]
        ]
        outputs.append(RuntimeError("fourth call fails"))
        counters = runner._new_counters()
        completed: list[str] = []
        with (
            mock.patch.object(runner.upstream_runner, "_seed_all"),
            mock.patch.object(
                runner.upstream_runner,
                "_quantization_config",
                return_value={"frozen": True},
            ),
            mock.patch.object(
                runner.base_runner, "_generate_one", side_effect=outputs
            ) as generate,
            self.assertRaisesRegex(RuntimeError, "fourth call fails"),
        ):
            runner._run_eval_only(
                dependencies=(
                    _FakeTorch(),
                    _FakeImageClass,
                    _RecordingPeftClass(),
                    _FakeProcessorClass,
                    _RecordingModelClass(),
                    _FakeBitsAndBytesConfig,
                ),
                model_snapshot=Path("frozen-model"),
                adapter_dir=Path("frozen-adapter"),
                suite=self.context["suite"],
                screenshot_receipts=self.context["screenshot_receipts"],
                screenshot_payloads=self.context["screenshot_payloads"],
                counters=counters,
                completed_case_ids=completed,
                protocol_freeze_commit="1" * 40,
                preregistration_payload=self.preregistration_payload,
            )
        self.assertEqual(generate.call_count, 4)
        self.assertEqual(counters["generate_attempts"], 4)
        self.assertEqual(counters["generate_calls"], 3)
        self.assertEqual(completed, list(contract.CASE_ORDER[:3]))

    def test_socket_guard_denies_and_counts_outbound_attempt(self) -> None:
        counters = runner._new_counters()
        original = socket.socket.connect
        client = socket.socket()
        try:
            with self.assertRaisesRegex(RuntimeError, "network attempt blocked"):
                with runner._OfflineSocketGuard(counters):
                    client.connect(("127.0.0.1", 9))
        finally:
            client.close()
        self.assertEqual(counters["network_attempts"], 1)
        self.assertIs(socket.socket.connect, original)

    def test_output_reservation_is_exclusive_and_consumption_is_durable(self) -> None:
        fixture_parent = ROOT / "work" / "test-fixtures"
        fixture_parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=fixture_parent) as temp_dir:
            output = Path(temp_dir) / "evaluation-output"
            reservation = runner._prepare_output_reservation(output)
            os.mkdir(reservation[0])
            guard = runner._ConsumedOutputDirectoryGuard(reservation)
            guard.open()
            guard.verify()
            with self.assertRaisesRegex(RuntimeError, "already exists"):
                runner._prepare_output_reservation(output)
            guard.close()

    def test_frozen_input_handles_verify_bytes_and_cleanup_on_preflight_fault(
        self,
    ) -> None:
        fixture_parent = ROOT / "work" / "test-fixtures"
        fixture_parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=fixture_parent) as temp_dir:
            temp_root = Path(temp_dir)
            model_root = temp_root / "model"
            adapter_root = temp_root / "adapter"
            model_root.mkdir()
            adapter_root.mkdir()
            model_path = model_root / "model.bin"
            adapter_path = adapter_root / "adapter.bin"
            model_payload = b"frozen-model"
            adapter_payload = b"frozen-adapter"
            model_path.write_bytes(model_payload)
            adapter_path.write_bytes(adapter_payload)
            model_receipts = [contract.artifact_receipt("model.bin", model_payload)]
            adapter_receipts = {
                "weights": contract.artifact_receipt(
                    "adapter/adapter.bin", adapter_payload
                )
            }
            with (
                mock.patch.object(runner, "ROOT", temp_root),
                mock.patch.object(contract, "ADAPTER_ROOT", "adapter"),
            ):
                with runner._FrozenInputFileSet(
                    model_snapshot=model_root,
                    model_receipts=model_receipts,
                    adapter_receipts=adapter_receipts,
                ) as guard:
                    self.assertEqual(guard.verify()[0], model_receipts)
                    if os.name == "nt":
                        with self.assertRaises(OSError):
                            model_path.write_bytes(b"mutated")

                original_hash = runner._hash_locked_handle
                calls = 0

                def fail_first_hash(handle: Any) -> str:
                    nonlocal calls
                    calls += 1
                    if calls == 1:
                        raise RuntimeError("hash fault")
                    return original_hash(handle)

                with (
                    mock.patch.object(
                        runner, "_hash_locked_handle", side_effect=fail_first_hash
                    ),
                    self.assertRaisesRegex(RuntimeError, "hash fault"),
                ):
                    with runner._FrozenInputFileSet(
                        model_snapshot=model_root,
                        model_receipts=model_receipts,
                        adapter_receipts=adapter_receipts,
                    ):
                        self.fail("fault injection must abort preflight")
                model_path.write_bytes(model_payload)

    def test_output_guard_rejects_extra_children_and_locks_written_artifacts(
        self,
    ) -> None:
        fixture_parent = ROOT / "work" / "test-fixtures"
        fixture_parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=fixture_parent) as temp_dir:
            output = Path(temp_dir) / "evaluation-output"
            reservation = runner._prepare_output_reservation(output)
            os.mkdir(output)
            guard = runner._ConsumedOutputDirectoryGuard(reservation)
            guard.open()
            artifact = output / "candidate.json"
            runner._write_output_artifact(guard, artifact, b"{}\n")
            if os.name == "nt":
                with self.assertRaises(OSError):
                    artifact.write_bytes(b"tampered\n")
            extra = output / "unexpected.txt"
            extra.write_bytes(b"unexpected")
            with self.assertRaisesRegex(RuntimeError, "artifact set changed"):
                guard.verify()
            guard.close()

    def test_top_level_fake_success_writes_single_authenticated_terminal(self) -> None:
        fixture_parent = ROOT / "work" / "test-fixtures"
        fixture_parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=fixture_parent) as temp_dir:
            temp_root = Path(temp_dir)
            summary = self.execute_with_fakes(temp_root)
            output = temp_root / contract.RUN_OUTPUT_ROOT
            self.assertTrue(summary["formal_gate_passed"])
            self.assertEqual(summary["next_gate"], contract.RESULT_REVIEW_GATE_ID)
            self.assertTrue((output / "evaluation-candidate.json").is_file())
            self.assertTrue((output / "predictions.json").is_file())
            self.assertTrue((output / "evidence.json").is_file())
            self.assertFalse((output / "failure.json").exists())
            self.assertEqual(
                {path.name for path in output.iterdir()},
                {
                    "attempt-owner.json",
                    "evaluation-candidate.json",
                    "predictions.json",
                    "evidence.json",
                },
            )

    def test_top_level_scoring_failure_writes_closed_receipt_and_never_retries(
        self,
    ) -> None:
        fixture_parent = ROOT / "work" / "test-fixtures"
        fixture_parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=fixture_parent) as temp_dir:
            temp_root = Path(temp_dir)
            with self.assertRaisesRegex(RuntimeError, "scoring failed"):
                self.execute_with_fakes(temp_root, scoring_failure=True)
            output = temp_root / contract.RUN_OUTPUT_ROOT
            candidate_payload = (output / "evaluation-candidate.json").read_bytes()
            failure_payload = (output / "failure.json").read_bytes()
            failure = contract.validate_failure(
                failure_payload,
                protocol_freeze_commit="1" * 40,
                preregistration_payload=self.preregistration_payload,
                attempt_owner_payload=(output / "attempt-owner.json").read_bytes(),
                suite=self.context["suite"],
                screenshot_receipts=self.context["screenshot_receipts"],
                evaluation_candidate_payload=candidate_payload,
                predictions_payload=None,
            )
            self.assertEqual(failure["stage"], "total_scoring")
            self.assertFalse((output / "evidence.json").exists())
            self.assertEqual(
                {path.name for path in output.iterdir()},
                {"attempt-owner.json", "evaluation-candidate.json", "failure.json"},
            )
            with self.assertRaisesRegex(RuntimeError, "must be absent"):
                self.execute_with_fakes(temp_root, scoring_failure=True)

    def test_interrupt_after_atomic_output_claim_recovers_owned_failure(self) -> None:
        fixture_parent = ROOT / "work" / "test-fixtures"
        fixture_parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=fixture_parent) as temp_dir:
            temp_root = Path(temp_dir)
            with self.assertRaises(KeyboardInterrupt):
                self.execute_with_fakes(
                    temp_root, interrupt_after_output_claim=True
                )
            output = temp_root / contract.RUN_OUTPUT_ROOT
            owner_payload = (output / "attempt-owner.json").read_bytes()
            failure_payload = (output / "failure.json").read_bytes()
            failure = contract.validate_failure(
                failure_payload,
                protocol_freeze_commit="1" * 40,
                preregistration_payload=self.preregistration_payload,
                attempt_owner_payload=owner_payload,
                suite=self.context["suite"],
                screenshot_receipts=self.context["screenshot_receipts"],
                evaluation_candidate_payload=None,
                predictions_payload=None,
            )
            self.assertEqual(failure["stage"], "output_reservation")
            self.assertEqual(
                {path.name for path in output.iterdir()},
                {"attempt-owner.json", "failure.json"},
            )

    def test_durable_evidence_interrupt_recovers_success_without_dual_terminal(
        self,
    ) -> None:
        fixture_parent = ROOT / "work" / "test-fixtures"
        fixture_parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=fixture_parent) as temp_dir:
            temp_root = Path(temp_dir)
            summary = self.execute_with_fakes(
                temp_root, interrupt_after_evidence_write=True
            )
            output = temp_root / contract.RUN_OUTPUT_ROOT
            self.assertTrue(summary["formal_gate_passed"])
            self.assertTrue((output / "evidence.json").is_file())
            self.assertFalse((output / "failure.json").exists())

    def test_freeze_commit_requires_exact_merged_master_state(self) -> None:
        with (
            mock.patch.object(
                runner, "_git_text", side_effect=["feature", "1" * 40, "1" * 40]
            ),
            self.assertRaisesRegex(RuntimeError, "requires freeze commit"),
        ):
            runner._validate_protocol_freeze_commit(
                protocol_freeze_commit="1" * 40,
                preregistration_payload=self.preregistration_payload,
                source_hashes=self.source_hashes,
            )

        with (
            mock.patch.object(
                runner,
                "_git_text",
                side_effect=["master", "2" * 40, "2" * 40],
            ),
            self.assertRaisesRegex(RuntimeError, "requires freeze commit"),
        ):
            runner._validate_protocol_freeze_commit(
                protocol_freeze_commit="1" * 40,
                preregistration_payload=self.preregistration_payload,
                source_hashes=self.source_hashes,
            )


class _FakeCuda:
    @staticmethod
    def synchronize() -> None:
        return None

    @staticmethod
    def empty_cache() -> None:
        return None

    @staticmethod
    def reset_peak_memory_stats() -> None:
        return None

    @staticmethod
    def max_memory_allocated() -> int:
        return 1

    @staticmethod
    def max_memory_reserved() -> int:
        return 1


class _FakeTorch:
    def __init__(self) -> None:
        self.cuda = _FakeCuda()

    @staticmethod
    def inference_mode() -> nullcontext[None]:
        return nullcontext()


class _FakeImage:
    def convert(self, _mode: str) -> _FakeImage:
        return self

    def close(self) -> None:
        return None


class _FakeImageClass:
    @staticmethod
    def open(_path: Path) -> _FakeImage:
        return _FakeImage()


class _FakeProcessorClass:
    @staticmethod
    def from_pretrained(_path: Path, **_kwargs: object) -> object:
        return object()


class _FakeEvalModel:
    def __init__(self) -> None:
        self.training = False
        self.config = SimpleNamespace(use_cache=False)

    def eval(self) -> _FakeEvalModel:
        return self

    @staticmethod
    def parameters() -> list[object]:
        return []


class _RecordingModelClass:
    def __init__(self) -> None:
        self.calls = 0
        self.kwargs: dict[str, object] = {}

    def from_pretrained(self, _path: Path, **kwargs: object) -> object:
        self.calls += 1
        self.kwargs = kwargs
        return object()


class _RecordingPeftClass:
    def __init__(self) -> None:
        self.calls = 0
        self.kwargs: dict[str, object] = {}

    def from_pretrained(
        self, _base_model: object, _path: Path, **kwargs: object
    ) -> _FakeEvalModel:
        self.calls += 1
        self.kwargs = kwargs
        return _FakeEvalModel()


class _FakeBitsAndBytesConfig:
    def __init__(self, **_kwargs: object) -> None:
        return None


class _FakeFrozenInputs:
    def __init__(
        self,
        *,
        model_receipts: list[dict[str, Any]],
        adapter_receipts: dict[str, dict[str, Any]],
    ) -> None:
        self.model_receipts = copy.deepcopy(model_receipts)
        self.adapter_receipts = copy.deepcopy(adapter_receipts)

    def __enter__(self) -> _FakeFrozenInputs:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    def verify(
        self,
    ) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
        return copy.deepcopy(self.model_receipts), copy.deepcopy(self.adapter_receipts)


if __name__ == "__main__":
    unittest.main()
