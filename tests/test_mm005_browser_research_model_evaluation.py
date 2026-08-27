from __future__ import annotations

import ast
import copy
import json
import sys
import unittest
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SRC))

from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_adapter_verifier as adapter_verifier,
)
from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_model_evaluation as contract,
)
from scripts import (  # noqa: E402
    prepare_mm005_browser_research_model_evaluation as prepare,
)
from scripts import (  # noqa: E402
    run_mm005_browser_research_model_evaluation as runner,
)


class MM005BrowserResearchModelEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.inputs = {**prepare.protocol_inputs(), "output_absent": True}
        cls.protocol = contract.expected_preregistration(
            freeze_status="frozen", **cls.inputs
        )
        cls.payload = contract.artifact_json_bytes(cls.protocol)
        cls.records = [dict(item) for item in cls.inputs["records"]]
        cls.artifacts = {
            str(path): bytes(payload)
            for path, payload in cls.inputs["artifact_payloads"].items()
        }
        cls.screenshots, cls.snapshots = contract.artifact_input_sets(cls.artifacts)
        cls.ordered_records = sorted(
            cls.records, key=lambda item: str(item["record_id"])
        )

    def test_frozen_protocol_reconstructs_exact_tracked_bytes(self) -> None:
        tracked = (ROOT / contract.PREREGISTRATION_PATH).read_bytes()
        self.assertEqual(tracked, self.payload)
        self.assertEqual(len(tracked), 116_152)
        self.assertEqual(
            contract.sha256_bytes(tracked),
            "sha256:84cd3d20d5a678a8ad0f7c38ad12e057225a4250e8143c5f004c2eaef8981f3f",
        )
        self.assertEqual(self.protocol["source_receipts"], prepare.source_receipts())

    def test_candidate_and_upstream_lineage_are_exact_and_read_only(self) -> None:
        lineage = self.protocol["source_lineage"]
        candidate = self.protocol["candidate"]
        self.assertEqual(
            lineage["adapter_verifier_implementation_merge_commit"],
            contract.IMPLEMENTATION_MERGE_COMMIT,
        )
        self.assertEqual(
            lineage["candidate_result_review_merge_commit"],
            contract.CANDIDATE_RESULT_REVIEW_MERGE_COMMIT,
        )
        self.assertEqual(candidate["model_id"], contract.MODEL_ID)
        self.assertEqual(candidate["model_revision"], contract.MODEL_REVISION)
        self.assertEqual(candidate["adapter_model_id"], contract.ADAPTER_MODEL_ID)
        self.assertFalse(candidate["adapter_mutation_allowed"])
        self.assertFalse(candidate["model_or_tensor_save_allowed"])
        self.assertFalse(candidate["training_allowed"])
        self.assertTrue(self.protocol["freeze_preconditions"]["fixed_output_absent"])

    def test_prompt_projection_is_closed_gold_free_and_byte_bound(self) -> None:
        suite = self.protocol["input_suite"]
        registry = suite["prompt_projection_registry"]
        rebuilt = contract.prompt_projection_registry(self.records, self.artifacts)
        self.assertEqual(registry, rebuilt)
        self.assertEqual(len(registry), 32)
        self.assertEqual(len({item["record_id"] for item in registry}), 32)
        self.assertEqual(
            sum(item["model_payload"]["bytes"] for item in registry), 81_796
        )
        self.assertEqual(
            sum(
                receipt["bytes"]
                for item in registry
                for receipt in item["screenshot_payloads"]
            ),
            600_604,
        )
        self.assertEqual(
            sum(
                receipt["bytes"]
                for item in registry
                for receipt in item["source_snapshot_payloads"]
            ),
            118_742,
        )
        forbidden_keys = {
            "expected_output",
            "family_id",
            "identities",
            "provenance",
            "record_id",
            "split",
            "template_id",
            "verifier",
            "screenshot_path",
            "source_snapshot_path",
        }
        for record in self.ordered_records:
            adapted = adapter_verifier.adapt_record(
                record, self.screenshots, self.snapshots
            )
            model_payload = adapted.model_payload()
            prompt = contract.build_prompt_projection(
                model_payload, len(adapted.screenshot_payloads)
            )
            self.assertFalse(self._json_keys(model_payload) & forbidden_keys)
            prompt_text = json.dumps(prompt, ensure_ascii=False, sort_keys=True)
            bindings = adapted.audit_projection()["source_bindings"]
            for binding in bindings:
                self.assertNotIn(str(binding["screenshot"]["path"]), prompt_text)
                self.assertNotIn(str(binding["source_snapshot"]["path"]), prompt_text)
            self.assertEqual(
                sum(part.get("type") == "image" for part in prompt[1]["content"]),
                len(bindings),
            )
        self.assertTrue(
            all(not item["gold_or_verifier_fields_exposed"] for item in registry)
        )
        self.assertTrue(all(not item["real_file_path_exposed"] for item in registry))
        self.assertTrue(all(not item["source_snapshots_exposed"] for item in registry))

    def test_protocol_freeze_claims_and_execution_rules_fail_closed(self) -> None:
        claims = self.protocol["claims"]
        execution = self.protocol["execution_protocol"]
        self.assertTrue(claims["environment_adapter_implemented"])
        self.assertTrue(claims["environment_adapter_executed"])
        self.assertTrue(claims["verifier_implemented"])
        self.assertTrue(claims["verifier_executed"])
        for key in (
            "attempt_consumed",
            "evaluation_executed",
            "model_evaluated",
            "formal_measurement_complete",
            "model_trained",
            "adapter_modified",
            "quality_improved",
            "safety_established",
            "prompt_injection_safety_established",
            "live_browser_used",
            "execution_network_used",
            "runtime_eligible",
        ):
            self.assertFalse(claims[key], key)
        self.assertEqual(execution["run_count"], 1)
        self.assertEqual(execution["generate_calls"], 32)
        self.assertEqual(execution["ordered_screenshot_inputs"], 68)
        self.assertEqual(execution["source_snapshot_inputs_to_model"], 0)
        self.assertEqual(execution["retry_count"], 0)
        self.assertFalse(execution["network_used"])
        self.assertEqual(execution["training_runs"], 0)
        self.assertEqual(execution["adapter_writes"], 0)
        self.assertEqual(execution["model_or_tensor_saves"], 0)
        self.assertFalse(self.protocol["formal_gate"]["accuracy_threshold_gate"])

    def test_perfect_metrics_are_total_across_all_registered_groups(self) -> None:
        cases = self._cases("perfect")
        metrics = contract.score_case_results(self.records, cases)
        self.assertEqual(metrics["record_count"], 32)
        self.assertEqual(metrics["compiler_invalid_count"], 0)
        for name in (*contract.METRIC_FLAGS, *contract.SEMANTIC_METRIC_FLAGS):
            self.assertEqual(metrics[name]["value"], 1.0, name)
        self.assertEqual(metrics["freshness_latest_source_accuracy"]["value"], 1.0)
        self.assertEqual(set(metrics["per_split"]), {"train", "validation"})
        self.assertEqual(len(metrics["per_task_family"]), 4)
        self.assertEqual(len(metrics["per_source_kind"]), 4)
        for grouping in (
            "per_split",
            "per_task_family",
            "per_source_kind",
        ):
            for group in metrics[grouping].values():
                self.assertTrue(
                    all(
                        group[name]["value"] == 1.0
                        for name in (*contract.METRIC_FLAGS, *contract.SEMANTIC_METRIC_FLAGS)
                    )
                )

    def test_wrong_and_invalid_outputs_remain_outcome_neutral(self) -> None:
        wrong = contract.score_case_results(self.records, self._cases("wrong"))
        self.assertEqual(wrong["compiler_validity"]["value"], 1.0)
        self.assertEqual(wrong["answer_exact_accuracy"]["value"], 0.0)
        self.assertEqual(wrong["citation_exact_accuracy"]["value"], 0.0)
        self.assertEqual(wrong["citation_binding_accuracy"]["value"], 0.0)
        self.assertEqual(wrong["minimum_source_coverage_accuracy"]["value"], 0.0)
        self.assertEqual(wrong["freshness_latest_source_accuracy"]["value"], 0.0)
        self.assertEqual(wrong["joint_exact_accuracy"]["value"], 0.0)

        invalid = contract.score_case_results(self.records, self._cases("invalid"))
        self.assertEqual(invalid["compiler_invalid_count"], 32)
        for name in (*contract.METRIC_FLAGS, *contract.SEMANTIC_METRIC_FLAGS):
            self.assertEqual(invalid[name]["value"], 0.0, name)

    def test_freshness_semantics_are_independent_and_snapshot_bytes_are_bound(
        self,
    ) -> None:
        freshness = next(
            record
            for record in self.ordered_records
            if record["task_family_id"] == contract.FRESHNESS_TASK_FAMILY
            and len(record["observation"]["sources"]) == 3
        )
        sources = sorted(
            freshness["observation"]["sources"],
            key=lambda item: item["published_at"],
        )
        older_refs = [source["dom_nodes"][1]["ref"] for source in sources[:2]]
        raw_output = json.dumps(
            {
                "answer": freshness["expected_output"]["answer"],
                "citation_refs": older_refs,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        case = contract.build_case_result(
            record=freshness,
            artifact_payloads=self.artifacts,
            raw_output=raw_output,
            generated_tokens=8,
            latency_seconds=0.125,
        )
        self.assertTrue(case["verdict"]["answer_exact"])
        self.assertFalse(case["verdict"]["citation_exact"])
        self.assertTrue(case["citation_semantics"]["all_citation_refs_bound"])
        self.assertTrue(case["citation_semantics"]["minimum_source_coverage_met"])
        self.assertFalse(case["citation_semantics"]["latest_source_cited"])

        tampered_inputs = copy.deepcopy(self.inputs)
        tampered_artifacts = dict(self.artifacts)
        snapshot_path = sorted(self.snapshots)[0]
        tampered_artifacts[snapshot_path] = tampered_artifacts[snapshot_path] + b" "
        tampered_inputs["artifact_payloads"] = tampered_artifacts
        with self.assertRaisesRegex(
            contract.MM005ModelEvaluationError, "ARTIFACT_RECEIPT_MISMATCH"
        ):
            contract.expected_preregistration(
                freeze_status="frozen", **tampered_inputs
            )

    def test_success_artifacts_recompute_and_do_not_create_quality_claims(self) -> None:
        owner_payload, candidate_payload, predictions_payload, evidence = (
            self._successful_artifacts()
        )
        validated = contract.validate_evidence(
            evidence,
            protocol_freeze_commit="a" * 40,
            preregistration_payload=self.payload,
            attempt_owner_payload=owner_payload,
            evaluation_candidate_payload=candidate_payload,
            predictions_payload=predictions_payload,
            records=self.records,
            artifact_payloads=self.artifacts,
        )
        self.assertEqual(validated, evidence)
        self.assertTrue(evidence["formal_gate_passed"])
        self.assertTrue(evidence["claims"]["model_evaluated"])
        self.assertTrue(evidence["claims"]["formal_measurement_complete"])
        self.assertFalse(evidence["claims"]["quality_improved"])
        self.assertFalse(evidence["claims"]["safety_established"])
        self.assertFalse(evidence["claims"]["runtime_eligible"])
        self.assertFalse(evidence["limitations"]["repeatability_established"])
        self.assertEqual(evidence["next_gate"], contract.RESULT_REVIEW_GATE_ID)

    def test_resource_cap_failure_preserves_metrics_but_not_formal_gate(self) -> None:
        owner_payload = self._owner_payload()
        candidate = contract.build_evaluation_candidate(
            protocol_freeze_commit="a" * 40,
            preregistration_payload=self.payload,
            attempt_owner_payload=owner_payload,
            cases=self._cases("perfect"),
            records=self.records,
            artifact_payloads=self.artifacts,
            execution=contract.expected_execution_counters(),
            resources={
                "elapsed_seconds": contract.RESOURCE_CAPS["elapsed_seconds"] + 1,
                "peak_gpu_allocated_bytes": 1,
                "peak_gpu_reserved_bytes": 1,
            },
        )
        candidate_payload = contract.artifact_json_bytes(candidate)
        predictions_payload = contract.artifact_json_bytes(
            contract.build_predictions(candidate)
        )
        evidence = contract.build_evidence(
            protocol_freeze_commit="a" * 40,
            preregistration_payload=self.payload,
            attempt_owner_payload=owner_payload,
            evaluation_candidate_payload=candidate_payload,
            predictions_payload=predictions_payload,
            records=self.records,
            artifact_payloads=self.artifacts,
            captured_at_utc="2026-08-26T00:00:00+00:00",
        )
        self.assertEqual(evidence["metrics"]["joint_exact_accuracy"]["value"], 1.0)
        self.assertFalse(evidence["required_gates"]["resource_caps"])
        self.assertFalse(evidence["formal_gate_passed"])
        self.assertTrue(evidence["claims"]["model_evaluated"])
        self.assertFalse(evidence["claims"]["formal_measurement_complete"])
        self.assertFalse(evidence["claims"]["quality_improved"])

    def test_failure_receipt_binds_owner_prefix_and_safe_diagnostics(self) -> None:
        owner_payload = self._owner_payload()
        counters = {key: 0 for key in contract.expected_execution_counters()}
        counters.update(
            {
                "run_attempts": 1,
                "fresh_base_load_attempts": 1,
                "fresh_base_loads": 1,
                "independent_adapter_load_attempts": 1,
                "independent_adapter_loads": 1,
                "generate_attempts": 2,
                "generate_calls": 2,
            }
        )
        completed = [str(record["record_id"]) for record in self.ordered_records[:2]]
        failure = contract.build_failure(
            protocol_freeze_commit="a" * 40,
            preregistration_payload=self.payload,
            attempt_owner_payload=owner_payload,
            stage="generation",
            exception_type="RuntimeError",
            counters=counters,
            completed_record_ids=completed,
            evaluation_candidate_payload=None,
            predictions_payload=None,
        )
        validated = contract.validate_failure(
            failure,
            protocol_freeze_commit="a" * 40,
            preregistration_payload=self.payload,
            attempt_owner_payload=owner_payload,
            evaluation_candidate_payload=None,
            predictions_payload=None,
        )
        self.assertEqual(validated, failure)
        self.assertEqual(failure["next_gate"], contract.FAILURE_CLASSIFICATION_GATE_ID)
        self.assertFalse(failure["claims"]["model_evaluated"])
        encoded = json.dumps(failure, sort_keys=True)
        self.assertNotIn("message", encoded)
        self.assertNotIn("traceback", encoded)

        reordered = list(reversed(completed))
        with self.assertRaisesRegex(
            contract.MM005ModelEvaluationError,
            "FAILURE_COMPLETED_PREFIX",
        ):
            contract.build_failure(
                protocol_freeze_commit="a" * 40,
                preregistration_payload=self.payload,
                attempt_owner_payload=owner_payload,
                stage="generation",
                exception_type="RuntimeError",
                counters=counters,
                completed_record_ids=reordered,
                evaluation_candidate_payload=None,
                predictions_payload=None,
            )
        with self.assertRaisesRegex(
            contract.MM005ModelEvaluationError,
            "FAILURE_EXCEPTION_TYPE",
        ):
            contract.build_failure(
                protocol_freeze_commit="a" * 40,
                preregistration_payload=self.payload,
                attempt_owner_payload=owner_payload,
                stage="generation",
                exception_type="RuntimeError: secret path",
                counters=counters,
                completed_record_ids=completed,
                evaluation_candidate_payload=None,
                predictions_payload=None,
            )

    def test_preregistration_tampering_fails_closed(self) -> None:
        mutations: list[dict[str, Any]] = []
        changed_claim = copy.deepcopy(self.protocol)
        changed_claim["claims"]["model_evaluated"] = True
        mutations.append(changed_claim)
        changed_order = copy.deepcopy(self.protocol)
        order = changed_order["input_suite"]["case_order"]
        order[0], order[1] = order[1], order[0]
        mutations.append(changed_order)
        changed_prompt = copy.deepcopy(self.protocol)
        changed_prompt["input_suite"]["prompt_projection_registry"][0][
            "gold_or_verifier_fields_exposed"
        ] = True
        mutations.append(changed_prompt)
        changed_caps = copy.deepcopy(self.protocol)
        changed_caps["resource_caps"]["elapsed_seconds"] = 1.0
        mutations.append(changed_caps)

        for value in mutations:
            with self.subTest(value=value):
                with self.assertRaisesRegex(
                    contract.MM005ModelEvaluationError,
                    "PREREGISTRATION_MISMATCH",
                ):
                    contract.validate_preregistration(value, **self.inputs)

    def test_candidate_and_evidence_resealing_fail_closed(self) -> None:
        owner_payload, candidate_payload, predictions_payload, evidence = (
            self._successful_artifacts()
        )
        candidate = contract.parse_strict_json_bytes(
            candidate_payload, location="$.candidate"
        )
        candidate["cases"][0]["compiled_output"]["answer"] = "forged"
        with self.assertRaisesRegex(
            contract.MM005ModelEvaluationError,
            "CANDIDATE_CASE_MISMATCH",
        ):
            contract.validate_evaluation_candidate(
                candidate,
                protocol_freeze_commit="a" * 40,
                preregistration_payload=self.payload,
                attempt_owner_payload=owner_payload,
                records=self.records,
                artifact_payloads=self.artifacts,
            )

        resealed = copy.deepcopy(evidence)
        resealed["claims"]["quality_improved"] = True
        with self.assertRaisesRegex(
            contract.MM005ModelEvaluationError,
            "EVIDENCE_MISMATCH",
        ):
            contract.validate_evidence(
                resealed,
                protocol_freeze_commit="a" * 40,
                preregistration_payload=self.payload,
                attempt_owner_payload=owner_payload,
                evaluation_candidate_payload=candidate_payload,
                predictions_payload=predictions_payload,
                records=self.records,
                artifact_payloads=self.artifacts,
            )

    def test_fake_model_lifecycle_runs_exactly_thirty_two_ordered_calls(
        self,
    ) -> None:
        counters = runner._new_counters()
        counters["run_attempts"] = 1
        completed: list[str] = []
        observed_messages: list[list[dict[str, Any]]] = []
        observed_image_counts: list[int] = []

        def fake_generate(**kwargs: Any) -> tuple[str, int]:
            index = len(observed_messages)
            observed_messages.append(kwargs["messages"])
            observed_image_counts.append(len(kwargs["images"]))
            return self._raw_output(self.ordered_records[index], "perfect"), 8

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
                runner.upstream_runner,
                "_quantization_config",
                return_value=object(),
            ),
            mock.patch.object(
                runner.base_runner,
                "_generate_one",
                side_effect=fake_generate,
            ),
        ):
            cases = runner._run_model_evaluation(
                dependencies=dependencies,
                records=self.records,
                artifact_payloads=self.artifacts,
                counters=counters,
                completed_record_ids=completed,
            )
        self.assertEqual(len(cases), 32)
        self.assertEqual(len(observed_messages), 32)
        self.assertEqual(sum(observed_image_counts), 68)
        self.assertEqual(
            observed_image_counts,
            [len(record["observation"]["sources"]) for record in self.ordered_records],
        )
        self.assertEqual(
            completed,
            [str(record["record_id"]) for record in self.ordered_records],
        )
        self.assertEqual(counters, contract.expected_execution_counters())
        self.assertEqual(
            contract.score_case_results(self.records, cases)["joint_exact_accuracy"][
                "value"
            ],
            1.0,
        )
        prompt_text = json.dumps(observed_messages, default=str)
        self.assertNotIn("expected_output", prompt_text)
        self.assertNotIn("screenshot_path", prompt_text)
        self.assertNotIn("source_snapshot_path", prompt_text)

    def test_protocol_code_has_no_top_level_model_import_or_write_path(self) -> None:
        forbidden_imports = {"torch", "transformers", "peft", "bitsandbytes"}
        forbidden_calls = {
            "train",
            "backward",
            "step",
            "save_pretrained",
            "push_to_hub",
        }
        for relative in (
            "src/fullcycle_bridge/mm005_browser_research_model_evaluation.py",
            "scripts/prepare_mm005_browser_research_model_evaluation.py",
            "scripts/run_mm005_browser_research_model_evaluation.py",
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

    def test_formal_command_is_rejected_before_attempt_on_feature_branch(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            RuntimeError,
            "formal MM-005 evaluation requires aligned merged master",
        ):
            runner._validate_protocol_freeze_commit(
                protocol_freeze_commit="a" * 40,
                preregistration_payload=self.payload,
                inputs=self.inputs,
            )

    def test_consumed_output_guard_rejects_replay_before_context(self) -> None:
        with (
            mock.patch.object(runner, "_validate_formal_python_execution_mode"),
            mock.patch.object(runner.os.path, "lexists", return_value=True),
            self.assertRaisesRegex(
                RuntimeError, "formal MM-005 evaluation output must be absent"
            ),
        ):
            runner.execute_frozen_protocol(
                protocol_freeze_commit=contract.IMPLEMENTATION_MERGE_COMMIT
            )

    def _cases(self, mode: str) -> list[dict[str, Any]]:
        return [
            contract.build_case_result(
                record=record,
                artifact_payloads=self.artifacts,
                raw_output=self._raw_output(record, mode),
                generated_tokens=8,
                latency_seconds=0.125,
            )
            for record in self.ordered_records
        ]

    @staticmethod
    def _raw_output(record: dict[str, Any], mode: str) -> str:
        if mode == "perfect":
            value = record["expected_output"]
        elif mode == "wrong":
            value = {
                "answer": "WRONG",
                "citation_refs": ["wrong-ref"],
            }
        elif mode == "invalid":
            return "not-json"
        else:
            raise AssertionError(mode)
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    def _owner_payload(self) -> bytes:
        return contract.artifact_json_bytes(
            contract.build_attempt_owner(
                protocol_freeze_commit="a" * 40,
                preregistration_payload=self.payload,
                attempt_id="b" * 64,
            )
        )

    def _successful_artifacts(
        self,
    ) -> tuple[bytes, bytes, bytes, dict[str, Any]]:
        owner_payload = self._owner_payload()
        candidate = contract.build_evaluation_candidate(
            protocol_freeze_commit="a" * 40,
            preregistration_payload=self.payload,
            attempt_owner_payload=owner_payload,
            cases=self._cases("perfect"),
            records=self.records,
            artifact_payloads=self.artifacts,
            execution=contract.expected_execution_counters(),
            resources={
                "elapsed_seconds": 1.0,
                "peak_gpu_allocated_bytes": 1,
                "peak_gpu_reserved_bytes": 1,
            },
        )
        candidate_payload = contract.artifact_json_bytes(candidate)
        predictions_payload = contract.artifact_json_bytes(
            contract.build_predictions(candidate)
        )
        evidence = contract.build_evidence(
            protocol_freeze_commit="a" * 40,
            preregistration_payload=self.payload,
            attempt_owner_payload=owner_payload,
            evaluation_candidate_payload=candidate_payload,
            predictions_payload=predictions_payload,
            records=self.records,
            artifact_payloads=self.artifacts,
            captured_at_utc="2026-08-26T00:00:00+00:00",
        )
        return owner_payload, candidate_payload, predictions_payload, evidence

    @classmethod
    def _json_keys(cls, value: object) -> set[str]:
        if isinstance(value, dict):
            return {
                *(str(key) for key in value),
                *(nested for item in value.values() for nested in cls._json_keys(item)),
            }
        if isinstance(value, list):
            return {nested for item in value for nested in cls._json_keys(item)}
        return set()


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


if __name__ == "__main__":
    unittest.main()
