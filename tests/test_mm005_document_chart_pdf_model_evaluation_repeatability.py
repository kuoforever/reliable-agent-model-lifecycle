from __future__ import annotations

import ast
import copy
import json
import sys
import tempfile
import unittest
from contextlib import nullcontext
from pathlib import Path
from typing import Any
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SRC))

from fullcycle_bridge import (  # noqa: E402
    mm005_document_chart_pdf_model_evaluation as baseline_contract,
)
from fullcycle_bridge import (  # noqa: E402
    mm005_document_chart_pdf_model_evaluation_repeatability as contract,
)
from scripts import (  # noqa: E402
    prepare_mm005_document_chart_pdf_model_evaluation_repeatability as prepare,
)
from scripts import (  # noqa: E402
    run_mm005_document_chart_pdf_model_evaluation_repeatability as runner,
)


class MM005DocumentChartPdfModelEvaluationRepeatabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.inputs = {**prepare.protocol_inputs(), "output_absent": True}
        cls.protocol = contract.expected_preregistration(
            freeze_status="frozen", **cls.inputs
        )
        cls.payload = contract.artifact_json_bytes(cls.protocol)
        cls.baseline = contract.validate_baseline_payloads(
            baseline_preregistration_payload=cls.inputs[
                "baseline_preregistration_payload"
            ],
            baseline_artifact_payloads=cls.inputs["baseline_artifact_payloads"],
            baseline_review_payload=cls.inputs["baseline_review_payload"],
            baseline_inputs=cls.inputs["baseline_inputs"],
        )
        baseline_inputs = cls.inputs["baseline_inputs"]
        cls.records = [dict(item) for item in baseline_inputs["records"]]
        cls.images = {
            str(path): bytes(payload)
            for path, payload in baseline_inputs["image_payloads"].items()
        }
        cls.records_by_id = {str(item["record_id"]): item for item in cls.records}

    def test_baseline_lineage_and_source_receipts_are_exact(self) -> None:
        lineage = self.protocol["source_lineage"]
        self.assertEqual(
            lineage["baseline_protocol_freeze_commit"],
            contract.BASELINE_PROTOCOL_FREEZE_COMMIT,
        )
        self.assertEqual(
            lineage["baseline_result_merge_commit"],
            contract.BASELINE_RESULT_MERGE_COMMIT,
        )
        self.assertEqual(
            set(lineage["baseline_artifacts"]), set(contract.BASELINE_ARTIFACTS)
        )
        self.assertEqual(self.protocol["source_receipts"], prepare.source_receipts())
        self.assertEqual(
            set(self.protocol["source_receipts"]), set(contract.PROTOCOL_SOURCE_PATHS)
        )

    def test_frozen_protocol_reconstructs_exact_tracked_bytes(self) -> None:
        tracked = (ROOT / contract.PREREGISTRATION_PATH).read_bytes()
        self.assertEqual(tracked, self.payload)
        self.assertEqual(len(tracked), 47_974)
        self.assertEqual(
            contract.sha256_bytes(tracked),
            "sha256:4c5186cbfa542125d4f2b96dae14e31955effa330c42951f993413d276962ed7",
        )

    def test_freeze_is_before_replay_and_claims_fail_closed(self) -> None:
        preconditions = self.protocol["freeze_preconditions"]
        claims = self.protocol["claims"]
        self.assertTrue(preconditions["fixed_replay_output_absent"])
        self.assertFalse(preconditions["second_model_imported_at_protocol_freeze"])
        self.assertFalse(preconditions["second_model_called_at_protocol_freeze"])
        self.assertTrue(claims["baseline_attempt_consumed"])
        self.assertTrue(claims["baseline_formal_measurement_complete"])
        self.assertTrue(claims["repeatability_protocol_frozen"])
        for name in (
            "replay_attempt_consumed",
            "replay_executed",
            "replay_model_evaluated",
            "formal_measurement_complete",
            "same_machine_fixed_suite_repeatability_established",
            "training_repeatability_established",
            "resource_repeatability_established",
            "cross_machine_reproducibility_established",
            "quality_improved",
            "safety_established",
            "serving_eligible",
            "promotion_eligible",
            "runtime_eligible",
        ):
            self.assertFalse(claims[name], name)
        self.assertEqual(self.protocol["next_gate"], contract.EXECUTION_GATE_ID)

    def test_execution_comparison_and_resource_semantics_are_outcome_neutral(
        self,
    ) -> None:
        execution = self.protocol["execution_protocol"]
        comparison = self.protocol["comparison_protocol"]
        resources = self.protocol["resource_protocol"]
        self.assertEqual(execution["run_count"], 1)
        self.assertEqual(execution["fresh_base_loads"], 1)
        self.assertEqual(execution["independent_adapter_loads"], 1)
        self.assertEqual(execution["generate_calls"], 32)
        self.assertEqual(execution["retry_count"], 0)
        self.assertEqual(execution["training_runs"], 0)
        self.assertEqual(execution["adapter_writes"], 0)
        self.assertFalse(execution["network_used"])
        self.assertEqual(
            set(comparison["layers"]),
            {
                "raw_output",
                "compiled_output",
                "verifier_verdict",
                "metrics",
                "generated_token_count",
            },
        )
        self.assertFalse(comparison["equality_required_for_measurement_completion"])
        self.assertTrue(comparison["drift_must_be_preserved"])
        self.assertFalse(comparison["drift_authorizes_retry"])
        self.assertTrue(resources["comparison_is_diagnostic_only"])
        self.assertFalse(resources["equality_required"])
        self.assertFalse(resources["resource_repeatability_claimed"])

    def test_exact_replay_completes_measurement_but_defers_repeatability_claim(
        self,
    ) -> None:
        _owner, _candidate, _predictions, evidence = self._replay_artifacts()
        comparison = evidence["comparison"]
        self.assertTrue(evidence["formal_gate_passed"])
        self.assertTrue(comparison["all_registered_layers_exact"])
        for layer in (
            "raw_outputs",
            "compiled_outputs",
            "verifier_verdicts",
            "generated_token_counts",
        ):
            self.assertEqual(comparison[layer]["exact_count"], 32, layer)
        self.assertTrue(comparison["metrics"]["exact"])
        self.assertTrue(evidence["claims"]["formal_measurement_complete"])
        self.assertFalse(
            evidence["claims"]["same_machine_fixed_suite_repeatability_established"]
        )
        self.assertEqual(evidence["next_gate"], contract.RESULT_REVIEW_GATE_ID)

    def test_raw_byte_drift_is_preserved_without_blocking_measurement(self) -> None:
        cases = self._baseline_cases()
        original = cases[0]
        cases[0] = self._rebuild_case(
            original, raw_output=str(original["raw_output"]) + "\n"
        )
        _owner, _candidate, _predictions, evidence = self._replay_artifacts(cases=cases)
        comparison = evidence["comparison"]
        self.assertEqual(comparison["raw_outputs"]["exact_count"], 31)
        self.assertEqual(comparison["compiled_outputs"]["exact_count"], 32)
        self.assertEqual(comparison["verifier_verdicts"]["exact_count"], 32)
        self.assertTrue(comparison["metrics"]["exact"])
        self.assertFalse(comparison["all_registered_layers_exact"])
        self.assertTrue(evidence["formal_gate_passed"])
        self.assertEqual(evidence["next_gate"], contract.RESULT_REVIEW_GATE_ID)

    def test_compiled_verdict_and_metric_drift_are_separately_reported(self) -> None:
        cases = self._baseline_cases()
        changed_index = next(
            index
            for index, item in enumerate(cases)
            if item["verdict"]["joint_correct"] is True
        )
        original = cases[changed_index]
        record = self.records_by_id[str(original["record_id"])]
        changed = copy.deepcopy(record["expected_output"])
        changed["answer"] = f"{changed['answer']} definite-drift"
        raw_output = json.dumps(
            changed,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        cases[changed_index] = self._rebuild_case(original, raw_output=raw_output)
        _owner, _candidate, _predictions, evidence = self._replay_artifacts(cases=cases)
        comparison = evidence["comparison"]
        self.assertEqual(comparison["raw_outputs"]["exact_count"], 31)
        self.assertEqual(comparison["compiled_outputs"]["exact_count"], 31)
        self.assertEqual(comparison["verifier_verdicts"]["exact_count"], 31)
        self.assertFalse(comparison["metrics"]["exact"])
        self.assertTrue(comparison["metrics"]["mismatch_names"])
        self.assertTrue(evidence["formal_gate_passed"])

    def test_generated_token_drift_is_independent_of_output_and_metrics(self) -> None:
        cases = self._baseline_cases()
        original = cases[0]
        current = int(original["generated_tokens"])
        changed = (
            current - 1 if current == baseline_contract.MAX_NEW_TOKENS else current + 1
        )
        cases[0] = self._rebuild_case(original, generated_tokens=changed)
        _owner, _candidate, _predictions, evidence = self._replay_artifacts(cases=cases)
        comparison = evidence["comparison"]
        self.assertEqual(comparison["raw_outputs"]["exact_count"], 32)
        self.assertEqual(comparison["compiled_outputs"]["exact_count"], 32)
        self.assertEqual(comparison["verifier_verdicts"]["exact_count"], 32)
        self.assertEqual(comparison["generated_token_counts"]["exact_count"], 31)
        self.assertTrue(comparison["metrics"]["exact"])
        self.assertTrue(evidence["formal_gate_passed"])

    def test_resource_difference_is_diagnostic_but_caps_are_integrity_gate(
        self,
    ) -> None:
        baseline_resources = copy.deepcopy(self.baseline["candidate"]["resources"])
        changed_resources = copy.deepcopy(baseline_resources)
        changed_resources["elapsed_seconds"] = (
            float(changed_resources["elapsed_seconds"]) + 0.5
        )
        _owner, _candidate, _predictions, diagnostic = self._replay_artifacts(
            resources=changed_resources
        )
        self.assertFalse(diagnostic["comparison"]["resources"]["exact"])
        self.assertTrue(diagnostic["comparison"]["resources"]["diagnostic_only"])
        self.assertTrue(diagnostic["formal_gate_passed"])
        self.assertFalse(diagnostic["claims"]["resource_repeatability_established"])

        exceeded = copy.deepcopy(baseline_resources)
        exceeded["elapsed_seconds"] = contract.RESOURCE_CAPS["elapsed_seconds"] + 1
        _owner, _candidate, _predictions, failed = self._replay_artifacts(
            resources=exceeded
        )
        self.assertTrue(failed["comparison"]["all_registered_layers_exact"])
        self.assertFalse(failed["gates"]["resource_caps"])
        self.assertFalse(failed["formal_gate_passed"])
        self.assertEqual(
            failed["classification"], contract.RESOURCE_EXCEEDED_CLASSIFICATION
        )
        self.assertEqual(failed["next_gate"], contract.FAILURE_CLASSIFICATION_GATE_ID)

    def test_owner_candidate_and_protocol_tampering_fail_closed(self) -> None:
        owner_payload, candidate_payload, _predictions, _evidence = (
            self._replay_artifacts()
        )
        owner = contract.parse_strict_json_bytes(owner_payload, location="$.owner")
        owner["claims"]["retry_allowed"] = True
        with self.assertRaisesRegex(
            contract.MM005EvaluationRepeatabilityError, "ATTEMPT_OWNER_MISMATCH"
        ):
            contract.validate_attempt_owner(
                owner,
                protocol_freeze_commit="a" * 40,
                preregistration_payload=self.payload,
            )

        candidate = contract.parse_strict_json_bytes(
            candidate_payload, location="$.candidate"
        )
        candidate["cases"][0]["compiled_output"]["answer"] = "forged"
        with self.assertRaisesRegex(
            contract.MM005EvaluationRepeatabilityError,
            "CANDIDATE_CASE_RECOMPUTATION_MISMATCH",
        ):
            contract.validate_evaluation_candidate(
                candidate,
                protocol_freeze_commit="a" * 40,
                preregistration_payload=self.payload,
                attempt_owner_payload=owner_payload,
                records=self.records,
                image_payloads=self.images,
            )

        preregistration = copy.deepcopy(self.protocol)
        preregistration["comparison_protocol"][
            "equality_required_for_measurement_completion"
        ] = True
        with self.assertRaisesRegex(
            contract.MM005EvaluationRepeatabilityError, "PREREGISTRATION_MISMATCH"
        ):
            contract.validate_preregistration(preregistration, **self.inputs)

    def test_failure_receipt_binds_progress_artifacts_and_safe_diagnostics(
        self,
    ) -> None:
        owner_payload = self._owner_payload()
        counters = {name: 0 for name in contract.expected_execution_counters()}
        counters.update(
            {
                "run_attempts": 1,
                "fresh_base_load_attempts": 1,
                "fresh_base_loads": 1,
                "independent_adapter_load_attempts": 1,
                "independent_adapter_loads": 1,
                "generate_attempts": 1,
                "generate_calls": 1,
            }
        )
        first_id = str(self.baseline["candidate"]["cases"][0]["record_id"])
        failure = contract.build_failure(
            protocol_freeze_commit="a" * 40,
            preregistration_payload=self.payload,
            attempt_owner_payload=owner_payload,
            stage="model_load_and_generation",
            exception_type="builtins.RuntimeError",
            counters=counters,
            completed_record_ids=[first_id],
            records=self.records,
            image_payloads=self.images,
            evaluation_candidate_payload=None,
            predictions_payload=None,
        )
        self.assertTrue(failure["claims"]["replay_attempt_consumed"])
        self.assertFalse(failure["claims"]["replay_executed"])
        self.assertEqual(failure["completed_record_ids"], [first_id])
        self.assertEqual(
            set(failure["diagnostic_policy"]),
            {
                "exception_message_recorded",
                "traceback_recorded",
                "absolute_paths_recorded",
                "secrets_recorded",
            },
        )
        self.assertTrue(not any(failure["diagnostic_policy"].values()))
        self.assertNotIn("exception_message", failure)
        self.assertNotIn("traceback", failure)
        self.assertNotIn("absolute_path", failure)
        self.assertNotIn("secret", failure)

        wrong_prefix = str(self.baseline["candidate"]["cases"][1]["record_id"])
        with self.assertRaisesRegex(
            contract.MM005EvaluationRepeatabilityError,
            "FAILURE_COMPLETED_PREFIX_MISMATCH",
        ):
            contract.build_failure(
                protocol_freeze_commit="a" * 40,
                preregistration_payload=self.payload,
                attempt_owner_payload=owner_payload,
                stage="model_load_and_generation",
                exception_type="builtins.RuntimeError",
                counters=counters,
                completed_record_ids=[wrong_prefix],
                records=self.records,
                image_payloads=self.images,
                evaluation_candidate_payload=None,
                predictions_payload=None,
            )

    def test_failure_receipt_rejects_unbound_terminal_artifacts(self) -> None:
        owner_payload, candidate_payload, predictions_payload, _evidence = (
            self._replay_artifacts()
        )
        expected_counters = contract.expected_execution_counters()
        tampered_predictions = contract.parse_strict_json_bytes(
            predictions_payload, location="$.predictions"
        )
        tampered_predictions["records"][0]["generated_tokens"] += 1
        with self.assertRaisesRegex(
            contract.MM005EvaluationRepeatabilityError,
            "FAILURE_PREDICTIONS_BINDING_MISMATCH",
        ):
            contract.build_failure(
                protocol_freeze_commit="a" * 40,
                preregistration_payload=self.payload,
                attempt_owner_payload=owner_payload,
                stage="evidence_persistence",
                exception_type="builtins.RuntimeError",
                counters=expected_counters,
                completed_record_ids=self.protocol["input_suite"]["case_order"],
                records=self.records,
                image_payloads=self.images,
                evaluation_candidate_payload=candidate_payload,
                predictions_payload=contract.artifact_json_bytes(tampered_predictions),
            )

    def test_protocol_code_has_no_top_level_model_import_or_training_write(
        self,
    ) -> None:
        forbidden_imports = {"torch", "transformers", "peft", "bitsandbytes"}
        forbidden_calls = {
            "train",
            "backward",
            "step",
            "save_pretrained",
            "push_to_hub",
        }
        for relative in contract.PROTOCOL_SOURCE_PATHS.values():
            if (
                "mm005_document_chart_pdf_model_evaluation_repeatability"
                not in relative
            ):
                continue
            tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
            imports = {
                alias.name.split(".")[0]
                for node in ast.walk(tree)
                if isinstance(node, (ast.Import, ast.ImportFrom))
                for alias in node.names
            }
            calls = {
                node.func.attr
                for node in ast.walk(tree)
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            }
            self.assertFalse(imports & forbidden_imports, relative)
            self.assertFalse(calls & forbidden_calls, relative)

    def test_formal_command_is_rejected_before_attempt_on_feature_branch(self) -> None:
        with self.assertRaisesRegex(
            RuntimeError, "formal MM-005 replay requires aligned merged master"
        ):
            runner._validate_protocol_freeze_commit(
                protocol_freeze_commit="a" * 40,
                preregistration_payload=self.payload,
                preregistration=self.protocol,
            )

    def test_consumed_output_guard_rejects_before_protocol_context(self) -> None:
        with (
            mock.patch.object(runner, "_validate_formal_python_execution_mode"),
            mock.patch.object(runner.os.path, "lexists", return_value=True),
            mock.patch.object(
                runner.protocol_builder,
                "protocol_inputs",
                side_effect=AssertionError("protocol context must not be opened"),
            ),
            self.assertRaisesRegex(
                RuntimeError, "formal MM-005 repeatability output must be absent"
            ),
        ):
            runner.execute_frozen_protocol(protocol_freeze_commit="a" * 40)

    def test_fake_replay_uses_one_delegated_32_call_lifecycle_and_writes_terminal(
        self,
    ) -> None:
        observed_calls = 0

        def fake_model_evaluation(**kwargs: Any) -> list[dict[str, Any]]:
            nonlocal observed_calls
            observed_calls += 1
            counters = kwargs["counters"]
            counters.clear()
            counters.update(contract.expected_execution_counters())
            kwargs["completed_record_ids"].extend(
                self.protocol["input_suite"]["case_order"]
            )
            return self._baseline_cases()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            preregistration_path = temp_root / contract.PREREGISTRATION_PATH
            preregistration_path.parent.mkdir(parents=True)
            preregistration_path.write_bytes(self.payload)
            (temp_root / contract.RUN_OUTPUT_ROOT).parent.mkdir(parents=True)
            frozen_model = _FrozenModel()
            frozen_dataset = _FrozenDataset(self.images)
            with (
                mock.patch.object(runner, "ROOT", temp_root),
                mock.patch.object(runner.attempt_guard, "ROOT", temp_root),
                mock.patch.object(runner, "_validate_formal_python_execution_mode"),
                mock.patch.object(runner, "_validate_protocol_freeze_commit"),
                mock.patch.object(runner, "_ensure_output_parent"),
                mock.patch.object(
                    runner.protocol_builder,
                    "protocol_inputs",
                    return_value=self.inputs,
                ),
                mock.patch.object(
                    runner.upstream_runner, "_validate_local_dependency_wheel"
                ),
                mock.patch.object(runner.upstream_runner, "_enable_offline_execution"),
                mock.patch.object(
                    runner.upstream_runner,
                    "observed_environment",
                    return_value=self.protocol["environment"],
                ),
                mock.patch.object(
                    runner.attempt_guard,
                    "_FrozenInputFileSet",
                    return_value=frozen_model,
                ),
                mock.patch.object(
                    runner.baseline_runner,
                    "_FrozenDatasetInputSet",
                    return_value=frozen_dataset,
                ),
                mock.patch.object(
                    runner.attempt_guard,
                    "_OfflineSocketGuard",
                    return_value=nullcontext(),
                ),
                mock.patch.object(
                    runner.attempt_guard,
                    "_load_eval_dependencies",
                    return_value=(_FakeTorch(),),
                ),
                mock.patch.object(
                    runner.baseline_runner,
                    "_run_model_evaluation",
                    side_effect=fake_model_evaluation,
                ),
                mock.patch.object(runner.secrets, "token_hex", return_value="c" * 64),
            ):
                summary = runner.execute_frozen_protocol(
                    protocol_freeze_commit="a" * 40
                )
            output = temp_root / contract.RUN_OUTPUT_ROOT
            self.assertEqual(observed_calls, 1)
            self.assertTrue(frozen_model.verified)
            self.assertTrue(frozen_dataset.verified)
            self.assertTrue(summary["formal_gate_passed"])
            self.assertTrue(summary["all_registered_layers_exact"])
            self.assertEqual(summary["raw_outputs_exact"], 32)
            self.assertEqual(
                {path.name for path in output.iterdir()},
                {
                    "attempt-owner.json",
                    "evaluation-candidate.json",
                    "predictions.json",
                    "evidence.json",
                },
            )

    def _owner_payload(self) -> bytes:
        return contract.artifact_json_bytes(
            contract.build_attempt_owner(
                protocol_freeze_commit="a" * 40,
                preregistration_payload=self.payload,
                attempt_id="b" * 64,
            )
        )

    def _baseline_cases(self) -> list[dict[str, Any]]:
        return copy.deepcopy(self.baseline["candidate"]["cases"])

    def _rebuild_case(
        self,
        original: dict[str, Any],
        *,
        raw_output: str | None = None,
        generated_tokens: int | None = None,
    ) -> dict[str, Any]:
        return baseline_contract.build_case_result(
            record=self.records_by_id[str(original["record_id"])],
            image_payloads=self.images,
            raw_output=(
                str(original["raw_output"]) if raw_output is None else raw_output
            ),
            generated_tokens=(
                int(original["generated_tokens"])
                if generated_tokens is None
                else generated_tokens
            ),
            latency_seconds=float(original["latency_seconds"]),
        )

    def _replay_artifacts(
        self,
        *,
        cases: list[dict[str, Any]] | None = None,
        resources: dict[str, Any] | None = None,
    ) -> tuple[bytes, bytes, bytes, dict[str, Any]]:
        owner_payload = self._owner_payload()
        candidate = contract.build_evaluation_candidate(
            protocol_freeze_commit="a" * 40,
            preregistration_payload=self.payload,
            attempt_owner_payload=owner_payload,
            cases=self._baseline_cases() if cases is None else cases,
            records=self.records,
            image_payloads=self.images,
            execution=contract.expected_execution_counters(),
            resources=(
                copy.deepcopy(self.baseline["candidate"]["resources"])
                if resources is None
                else resources
            ),
        )
        candidate_payload = contract.artifact_json_bytes(candidate)
        predictions_payload = contract.artifact_json_bytes(
            contract.build_predictions(candidate)
        )
        evidence = contract.build_evidence(
            protocol_freeze_commit="a" * 40,
            preregistration_payload=self.payload,
            preregistration=self.protocol,
            attempt_owner_payload=owner_payload,
            evaluation_candidate_payload=candidate_payload,
            predictions_payload=predictions_payload,
            reference_candidate=self.baseline["candidate"],
            reference_evidence=self.baseline["evidence"],
            records=self.records,
            image_payloads=self.images,
            observed_environment=self.protocol["environment"],
            captured_at_utc="2026-08-26T00:00:00+00:00",
        )
        return owner_payload, candidate_payload, predictions_payload, evidence


class _FrozenModel:
    def __init__(self) -> None:
        self.verified = False

    def __enter__(self) -> _FrozenModel:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def verify(self) -> None:
        self.verified = True


class _FrozenDataset:
    def __init__(self, payloads: dict[str, bytes]) -> None:
        self.payloads = payloads
        self.verified = False

    def __enter__(self) -> _FrozenDataset:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def verify(self) -> None:
        self.verified = True


class _FakeCuda:
    @staticmethod
    def empty_cache() -> None:
        return None

    @staticmethod
    def reset_peak_memory_stats() -> None:
        return None

    @staticmethod
    def synchronize() -> None:
        return None

    @staticmethod
    def max_memory_allocated() -> int:
        return 1

    @staticmethod
    def max_memory_reserved() -> int:
        return 1


class _FakeTorch:
    cuda = _FakeCuda()


if __name__ == "__main__":
    unittest.main()
