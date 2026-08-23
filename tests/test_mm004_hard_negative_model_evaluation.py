from __future__ import annotations

import ast
import copy
import json
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

from fullcycle_bridge import (  # noqa: E402
    mm004_hard_negative_model_evaluation as contract,
)
from scripts import run_mm004_hard_negative_model_evaluation as runner  # noqa: E402
from scripts import validate_offline as offline_gate  # noqa: E402


class MM004HardNegativeModelEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.context = runner.load_authenticated_context()
        cls.source_receipts = runner.source_receipts()
        cls.records = cls.context["records"]
        cls.preregistration = contract.expected_preregistration(
            freeze_status="frozen",
            generation_evidence=cls.context["generation_evidence"],
            candidate_repeatability_protocol=cls.context[
                "candidate_repeatability_protocol"
            ],
            candidate_result_review=cls.context["candidate_result_review"],
            records=cls.records,
            source_receipts=cls.source_receipts,
        )
        cls.preregistration_payload = contract.artifact_json_bytes(
            cls.preregistration
        )

    def build_cases(self, *, mode: str = "perfect") -> list[dict[str, Any]]:
        cases: list[dict[str, Any]] = []
        for record in self.records:
            expected = record["verifier"]["verdict"]
            if mode == "perfect":
                predicted = expected
            elif mode == "opposite":
                predicted = "reject" if expected == "accept" else "accept"
            elif mode == "invalid":
                predicted = None
            else:
                raise AssertionError(mode)
            raw_output = (
                "not-json"
                if predicted is None
                else json.dumps({"verdict": predicted}, separators=(",", ":"))
            )
            cases.append(
                contract.build_case_result(
                    record=record,
                    raw_output=raw_output,
                    generated_tokens=4,
                    latency_seconds=0.01,
                )
            )
        return cases

    def build_candidate(
        self,
        *,
        cases: list[dict[str, Any]] | None = None,
        resources: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return contract.build_evaluation_candidate(
            protocol_freeze_commit="a" * 40,
            preregistration_payload=self.preregistration_payload,
            cases=cases or self.build_cases(),
            records=self.records,
            execution=contract.expected_execution_counters(),
            resources=resources
            or {
                "elapsed_seconds": 1.0,
                "peak_gpu_allocated_bytes": 1,
                "peak_gpu_reserved_bytes": 1,
            },
        )

    def owner_payload(self) -> bytes:
        return contract.artifact_json_bytes(
            contract.build_attempt_owner(
                protocol_freeze_commit="a" * 40,
                preregistration_payload=self.preregistration_payload,
                attempt_id="b" * 64,
            )
        )

    def build_evidence(
        self, candidate: dict[str, Any], *, timestamp: str = "2026-08-22T00:00:00+00:00"
    ) -> dict[str, Any]:
        candidate_payload = contract.artifact_json_bytes(candidate)
        predictions_payload = contract.artifact_json_bytes(
            contract.build_predictions(candidate)
        )
        return contract.build_evidence(
            protocol_freeze_commit="a" * 40,
            preregistration_payload=self.preregistration_payload,
            attempt_owner_payload=self.owner_payload(),
            evaluation_candidate_payload=candidate_payload,
            predictions_payload=predictions_payload,
            records=self.records,
            captured_at_utc=timestamp,
        )

    def test_preregistration_is_deterministic_outcome_neutral_and_frozen(self) -> None:
        rebuilt = contract.expected_preregistration(
            freeze_status="frozen",
            generation_evidence=self.context["generation_evidence"],
            candidate_repeatability_protocol=self.context[
                "candidate_repeatability_protocol"
            ],
            candidate_result_review=self.context["candidate_result_review"],
            records=self.records,
            source_receipts=self.source_receipts,
        )
        self.assertEqual(rebuilt, self.preregistration)
        self.assertEqual(rebuilt["input_suite"]["record_count"], 56)
        self.assertEqual(rebuilt["execution_protocol"]["generate_calls"], 56)
        self.assertTrue(all(value is False for value in rebuilt["claims"].values()))
        self.assertFalse(rebuilt["formal_gate"]["accuracy_threshold_gate"])
        self.assertEqual(rebuilt["next_gate"], contract.EXECUTION_GATE_ID)
        predecessor = rebuilt["source_lineage"]["predecessor_protocol"]
        self.assertFalse(predecessor["attempt_consumed"])
        self.assertFalse(predecessor["model_imported"])
        self.assertEqual(predecessor["model_calls"], 0)
        self.assertTrue(predecessor["output_absent"])

    def test_tracked_protocol_recomputes_and_unified_gate_is_freeze_only(self) -> None:
        result = runner.prepare_protocol(freeze_status="frozen", check=True)
        self.assertTrue(result["valid"])
        self.assertEqual(result["case_count"], 56)
        summary = offline_gate._validate_mm004_hard_negative_model_evaluation_protocol()
        self.assertTrue(summary["protocol_frozen"])
        self.assertFalse(summary["evaluation_executed"])
        self.assertFalse(summary["model_evaluated"])
        self.assertFalse(summary["training_executed"])
        self.assertFalse(summary["runtime_eligible"])

    def test_prompt_projection_excludes_gold_identity_and_image_receipts(self) -> None:
        clean = self.records[0]
        negative = self.records[1]
        clean_projection = contract.prompt_projection(clean)
        negative_projection = contract.prompt_projection(negative)
        self.assertEqual(tuple(clean_projection), contract.PROMPT_PROJECTION_KEYS)
        self.assertEqual(
            clean_projection["instruction"], negative_projection["instruction"]
        )
        self.assertEqual(
            clean_projection["observation"], negative_projection["observation"]
        )
        self.assertNotEqual(
            clean_projection["candidate_action"],
            negative_projection["candidate_action"],
        )
        self.assertNotIn("image_path", clean_projection["observation"])
        self.assertNotIn("image_sha256", clean_projection["observation"])
        relabelled = copy.deepcopy(clean)
        relabelled["verifier"]["verdict"] = "reject"
        relabelled["variant"] = "hard_negative"
        relabelled["record_id"] = "different"
        self.assertEqual(
            contract.build_user_prompt(clean), contract.build_user_prompt(relabelled)
        )

    def test_compiler_accepts_only_the_registered_single_key_json_shape(self) -> None:
        for verdict in contract.ALLOWED_VERDICTS:
            compiled = contract.compile_raw_verdict(f'{{"verdict":"{verdict}"}}')
            self.assertEqual(compiled["verdict"], verdict)
            self.assertFalse(compiled["compiler_fallback"])
        invalid = (
            "",
            "accept",
            "```json\n{\"verdict\":\"accept\"}\n```",
            '{"verdict":"ACCEPT"}',
            '{"verdict":"accept","reason":"x"}',
            '{"verdict":"accept","verdict":"reject"}',
            '{"verdict":NaN}',
            "[]",
        )
        for raw in invalid:
            compiled = contract.compile_raw_verdict(raw)
            self.assertEqual(compiled["verdict"], "invalid", raw)
            self.assertTrue(compiled["compiler_fallback"], raw)

    def test_git_lfs_pointer_and_hydrated_adapter_are_both_exactly_bound(self) -> None:
        receipt = contract.ADAPTER_RECEIPTS["weights"]
        pointer = contract.git_lfs_pointer_bytes(receipt)
        hydrated = (ROOT / contract.ADAPTER_LFS_PATH).read_bytes()
        self.assertEqual(len(pointer), 133)
        self.assertEqual(len(hydrated), receipt["bytes"])
        self.assertEqual(contract.sha256_bytes(hydrated), receipt["sha256"])
        self.assertTrue(
            runner._tracked_payload_matches_receipt(
                contract.ADAPTER_LFS_PATH, pointer, receipt
            )
        )
        self.assertFalse(
            runner._tracked_payload_matches_receipt(
                contract.ADAPTER_LFS_PATH, hydrated, receipt
            )
        )
        tampered = pointer.replace(b"d93d2ea2", b"093d2ea2", 1)
        self.assertFalse(
            runner._tracked_payload_matches_receipt(
                contract.ADAPTER_LFS_PATH, tampered, receipt
            )
        )

    def test_perfect_adverse_and_invalid_outputs_are_totally_scored(self) -> None:
        perfect = contract.score_case_results(self.records, self.build_cases())
        self.assertEqual(perfect["overall_accuracy"]["value"], 1.0)
        self.assertEqual(perfect["pair_exact_accuracy"]["value"], 1.0)
        self.assertEqual(perfect["compiler_validity"]["value"], 1.0)

        adverse = contract.score_case_results(
            self.records, self.build_cases(mode="opposite")
        )
        self.assertEqual(adverse["overall_accuracy"]["value"], 0.0)
        self.assertEqual(adverse["pair_exact_accuracy"]["value"], 0.0)
        self.assertEqual(adverse["hard_negative_false_accepts"], 28)
        self.assertEqual(adverse["clean_false_rejects"], 28)

        invalid = contract.score_case_results(
            self.records, self.build_cases(mode="invalid")
        )
        self.assertEqual(invalid["overall_accuracy"]["value"], 0.0)
        self.assertEqual(invalid["compiler_validity"]["value"], 0.0)
        self.assertEqual(set(invalid["per_category"]), set(contract.parent.CATEGORY_IDS))

    def test_preregistration_and_candidate_tamper_fail_closed(self) -> None:
        tampered_protocol = copy.deepcopy(self.preregistration)
        tampered_protocol["claims"]["model_evaluated"] = True
        with self.assertRaisesRegex(
            contract.MM004ModelEvaluationError, "PREREGISTRATION_MISMATCH"
        ):
            contract.validate_preregistration(
                tampered_protocol,
                generation_evidence=self.context["generation_evidence"],
                candidate_repeatability_protocol=self.context[
                    "candidate_repeatability_protocol"
                ],
                candidate_result_review=self.context["candidate_result_review"],
                records=self.records,
                source_receipts=self.source_receipts,
            )
        candidate = self.build_candidate()
        candidate["cases"][0]["compiled_prediction"]["verdict"] = "reject"
        with self.assertRaisesRegex(
            contract.MM004ModelEvaluationError, "CASE_COMPILED_PREDICTION"
        ):
            contract.validate_evaluation_candidate(
                candidate,
                protocol_freeze_commit="a" * 40,
                preregistration_payload=self.preregistration_payload,
                records=self.records,
            )

    def test_resource_cap_failure_preserves_metrics_but_not_formal_claim(self) -> None:
        candidate = self.build_candidate(
            resources={
                "elapsed_seconds": contract.RESOURCE_CAPS["elapsed_seconds"] + 1,
                "peak_gpu_allocated_bytes": 1,
                "peak_gpu_reserved_bytes": 1,
            }
        )
        evidence = self.build_evidence(candidate)
        self.assertEqual(evidence["metrics"]["overall_accuracy"]["value"], 1.0)
        self.assertFalse(evidence["formal_gate_passed"])
        self.assertFalse(evidence["required_gates"]["resource_caps"])
        self.assertTrue(evidence["claims"]["model_evaluated"])
        self.assertFalse(evidence["claims"]["formal_measurement_complete"])
        self.assertFalse(evidence["claims"]["runtime_eligible"])

    def test_evidence_rejects_prediction_or_claim_resealing(self) -> None:
        candidate = self.build_candidate()
        evidence = self.build_evidence(candidate)
        evidence["claims"]["safety_established"] = True
        candidate_payload = contract.artifact_json_bytes(candidate)
        predictions_payload = contract.artifact_json_bytes(
            contract.build_predictions(candidate)
        )
        with self.assertRaisesRegex(
            contract.MM004ModelEvaluationError, "EVIDENCE_MISMATCH"
        ):
            contract.validate_evidence(
                evidence,
                protocol_freeze_commit="a" * 40,
                preregistration_payload=self.preregistration_payload,
                attempt_owner_payload=self.owner_payload(),
                evaluation_candidate_payload=candidate_payload,
                predictions_payload=predictions_payload,
                records=self.records,
            )

    def test_failure_receipt_binds_owner_and_completed_order_prefix(self) -> None:
        counters = contract.expected_execution_counters()
        completed = [str(record["record_id"]) for record in self.records]
        failure = contract.build_failure(
            protocol_freeze_commit="a" * 40,
            preregistration_payload=self.preregistration_payload,
            attempt_owner_payload=self.owner_payload(),
            stage="scoring",
            exception_type="RuntimeError",
            counters=counters,
            completed_record_ids=completed,
            evaluation_candidate_payload=None,
            predictions_payload=None,
        )
        self.assertFalse(failure["claims"]["formal_measurement_complete"])
        self.assertEqual(failure["next_gate"], contract.FAILURE_CLASSIFICATION_GATE_ID)
        self.assertEqual(
            contract.validate_failure(
                failure,
                protocol_freeze_commit="a" * 40,
                preregistration_payload=self.preregistration_payload,
                attempt_owner_payload=self.owner_payload(),
                evaluation_candidate_payload=None,
                predictions_payload=None,
            ),
            failure,
        )
        reordered = list(completed)
        reordered[0], reordered[1] = reordered[1], reordered[0]
        with self.assertRaisesRegex(
            contract.MM004ModelEvaluationError, "FAILURE_COMPLETED_PREFIX"
        ):
            contract.build_failure(
                protocol_freeze_commit="a" * 40,
                preregistration_payload=self.preregistration_payload,
                attempt_owner_payload=self.owner_payload(),
                stage="scoring",
                exception_type="RuntimeError",
                counters=counters,
                completed_record_ids=reordered,
                evaluation_candidate_payload=None,
                predictions_payload=None,
            )
        wrong_owner = contract.artifact_json_bytes(
            contract.build_attempt_owner(
                protocol_freeze_commit="c" * 40,
                preregistration_payload=self.preregistration_payload,
                attempt_id="b" * 64,
            )
        )
        with self.assertRaisesRegex(
            contract.MM004ModelEvaluationError, "ATTEMPT_OWNER_MISMATCH"
        ):
            contract.build_failure(
                protocol_freeze_commit="a" * 40,
                preregistration_payload=self.preregistration_payload,
                attempt_owner_payload=wrong_owner,
                stage="scoring",
                exception_type="RuntimeError",
                counters=counters,
                completed_record_ids=completed,
                evaluation_candidate_payload=None,
                predictions_payload=None,
            )

    def test_fake_model_lifecycle_runs_exactly_fifty_six_ordered_calls(self) -> None:
        counters = runner._new_counters()
        counters["run_attempts"] = 1
        completed: list[str] = []
        observed_prompts: list[str] = []

        def fake_generate(**kwargs: Any) -> tuple[str, int]:
            index = len(observed_prompts)
            messages = kwargs["messages"]
            observed_prompts.append(messages[1]["content"][1]["text"])
            verdict = self.records[index]["verifier"]["verdict"]
            return json.dumps({"verdict": verdict}, separators=(",", ":")), 4

        dependencies = (
            _FakeTorch(),
            _FakeImageClass,
            _FakePeftClass,
            _FakeProcessorClass,
            _FakeModelClass,
            _FakeBitsAndBytesConfig,
        )
        with (
            mock.patch.object(runner.upstream_runner, "_seed_all"),
            mock.patch.object(
                runner.upstream_runner, "_quantization_config", return_value=object()
            ),
            mock.patch.object(runner.base_runner, "_generate_one", side_effect=fake_generate),
        ):
            cases = runner._run_model_evaluation(
                dependencies=dependencies,
                records=self.records,
                image_payloads=self.context["generation_output_payloads"],
                counters=counters,
                completed_record_ids=completed,
            )
        expected_ids = [str(record["record_id"]) for record in self.records]
        self.assertEqual(completed, expected_ids)
        self.assertEqual(len(cases), 56)
        self.assertEqual(len(observed_prompts), 56)
        self.assertEqual(counters, contract.expected_execution_counters())
        self.assertTrue(all("verifier" not in prompt for prompt in observed_prompts))

    def test_owner_marked_success_and_scoring_failure_are_durable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            success_root = Path(directory) / "success"
            summary = self._execute_with_fakes(success_root)
            output = success_root / contract.RUN_OUTPUT_ROOT
            self.assertTrue(summary["formal_gate_passed"])
            self.assertEqual(
                {path.name for path in output.iterdir()},
                {
                    "attempt-owner.json",
                    "evaluation-candidate.json",
                    "predictions.json",
                    "evidence.json",
                },
            )
        with tempfile.TemporaryDirectory() as directory:
            failure_root = Path(directory) / "failure"
            with self.assertRaisesRegex(RuntimeError, "scoring failed"):
                self._execute_with_fakes(failure_root, scoring_failure=True)
            output = failure_root / contract.RUN_OUTPUT_ROOT
            self.assertEqual(
                {path.name for path in output.iterdir()},
                {
                    "attempt-owner.json",
                    "evaluation-candidate.json",
                    "failure.json",
                },
            )
            failure = json.loads((output / "failure.json").read_text(encoding="utf-8"))
            self.assertEqual(failure["stage"], "scoring")
            self.assertFalse(failure["claims"]["formal_measurement_complete"])

    def test_contract_and_runner_have_no_training_or_model_save_path(self) -> None:
        forbidden_imports = {"torch", "transformers", "peft", "bitsandbytes"}
        forbidden_calls = {
            "train",
            "backward",
            "step",
            "save",
            "save_pretrained",
            "push_to_hub",
        }
        for relative in (
            "src/fullcycle_bridge/mm004_hard_negative_model_evaluation.py",
            "scripts/run_mm004_hard_negative_model_evaluation.py",
        ):
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

    def _execute_with_fakes(
        self, temp_root: Path, *, scoring_failure: bool = False
    ) -> dict[str, Any]:
        preregistration_path = temp_root / contract.PREREGISTRATION_PATH
        preregistration_path.parent.mkdir(parents=True)
        preregistration_path.write_bytes(self.preregistration_payload)
        (temp_root / "work").mkdir()
        cases = self.build_cases()
        fake_model_inputs = _FakeFrozenModelInputs()
        fake_generation_inputs = _FakeFrozenGenerationInputs(
            self.context["generation_output_payloads"]
        )

        def fake_run(**kwargs: Any) -> list[dict[str, Any]]:
            kwargs["counters"].update(contract.expected_execution_counters())
            kwargs["completed_record_ids"].extend(
                str(record["record_id"]) for record in self.records
            )
            return copy.deepcopy(cases)

        def ensure_parent() -> None:
            (temp_root / contract.RUN_OUTPUT_ROOT).parent.mkdir(parents=True)

        dependencies = (_FakeTorch(), None, None, None, None, None)
        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(runner, "ROOT", temp_root))
            stack.enter_context(
                mock.patch.object(runner.repeat_runner, "ROOT", temp_root)
            )
            stack.enter_context(
                mock.patch.object(
                    runner, "load_authenticated_context", return_value=self.context
                )
            )
            stack.enter_context(
                mock.patch.object(
                    runner, "source_receipts", return_value=self.source_receipts
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
                    return_value=self.preregistration["candidate"]["environment"],
                )
            )
            stack.enter_context(
                mock.patch.object(
                    runner.repeat_runner,
                    "_FrozenInputFileSet",
                    return_value=fake_model_inputs,
                )
            )
            stack.enter_context(
                mock.patch.object(
                    runner,
                    "_FrozenGeneratedInputSet",
                    return_value=fake_generation_inputs,
                )
            )
            stack.enter_context(
                mock.patch.object(
                    runner.repeat_runner, "_ensure_output_parent", side_effect=ensure_parent
                )
            )
            stack.enter_context(
                mock.patch.object(
                    runner.repeat_runner,
                    "_load_eval_dependencies",
                    return_value=dependencies,
                )
            )
            stack.enter_context(
                mock.patch.object(runner, "_run_model_evaluation", side_effect=fake_run)
            )
            if scoring_failure:
                stack.enter_context(
                    mock.patch.object(
                        contract,
                        "score_case_results",
                        side_effect=RuntimeError("scoring failed"),
                    )
                )
            return runner.execute_frozen_protocol(protocol_freeze_commit="a" * 40)


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
    cuda = _FakeCuda()

    @staticmethod
    def inference_mode() -> Any:
        return nullcontext()


class _FakeImage:
    def convert(self, _mode: str) -> _FakeImage:
        return self

    def close(self) -> None:
        return None


class _FakeImageClass:
    @staticmethod
    def open(_stream: Any) -> _FakeImage:
        return _FakeImage()


class _FakeModel:
    def __init__(self) -> None:
        self.config = SimpleNamespace(use_cache=False)
        self.training = False

    def eval(self) -> _FakeModel:
        return self

    @staticmethod
    def parameters() -> list[Any]:
        return [SimpleNamespace(requires_grad=False)]


class _FakeModelClass:
    @staticmethod
    def from_pretrained(*_args: Any, **_kwargs: Any) -> _FakeModel:
        return _FakeModel()


class _FakePeftClass:
    @staticmethod
    def from_pretrained(*_args: Any, **_kwargs: Any) -> _FakeModel:
        return _FakeModel()


class _FakeProcessorClass:
    @staticmethod
    def from_pretrained(*_args: Any, **_kwargs: Any) -> object:
        return object()


class _FakeBitsAndBytesConfig:
    pass


class _FakeFrozenModelInputs:
    def __enter__(self) -> _FakeFrozenModelInputs:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    @staticmethod
    def verify() -> None:
        return None


class _FakeFrozenGenerationInputs:
    def __init__(self, payloads: dict[str, bytes]) -> None:
        self.payloads = payloads

    def __enter__(self) -> _FakeFrozenGenerationInputs:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    @staticmethod
    def verify() -> None:
        return None


if __name__ == "__main__":
    unittest.main()
