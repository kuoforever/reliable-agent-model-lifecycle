from __future__ import annotations

import ast
import copy
import json
import sys
import unittest
from collections import Counter
from collections.abc import Mapping
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for entry in (str(SRC), str(ROOT)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from fullcycle_bridge import (  # noqa: E402
    browser_research_environment_adaptation as parent,
)
from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_adapter_verifier_protocol as contract,
)
from scripts import (  # noqa: E402
    prepare_mm005_browser_research_adapter_verifier_protocol as prepare,
)

PROTOCOL_BYTES = 271_406
PROTOCOL_SHA256 = (
    "sha256:a64f5d3d174ab2e8c7a003626d76981f43c15b9e739f8c999c4198df0c77156b"
)


class MM005BrowserResearchAdapterVerifierProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.inputs = prepare.protocol_inputs()
        cls.protocol = prepare.build_protocol()
        cls.payload = contract.artifact_json_bytes(cls.protocol)
        cls.records, cls.source_bindings, cls.dataset_receipts = (
            contract.dataset_context(cls.inputs["output_payloads"])
        )

    def test_tracked_protocol_rebuilds_and_validates_exactly(self) -> None:
        tracked = (ROOT / contract.PROTOCOL_PATH).read_bytes()
        parsed = json.loads(tracked)
        summary = contract.validate_protocol(parsed, **self.inputs)

        self.assertEqual(tracked, self.payload)
        self.assertEqual(len(tracked), PROTOCOL_BYTES)
        self.assertEqual(contract.sha256_bytes(tracked), PROTOCOL_SHA256)
        self.assertEqual(contract.artifact_json_bytes(parsed), tracked)
        self.assertEqual(parsed, self.protocol)
        self.assertEqual(
            summary.to_dict(),
            {
                "protocol_version": 1,
                "source_receipt_count": 8,
                "record_count": 32,
                "source_binding_count": 68,
                "screenshot_binding_count": 68,
                "source_snapshot_binding_count": 68,
                "adapter_projection_count": 32,
                "verifier_case_count": 224,
                "positive_case_count": 32,
                "negative_case_count": 192,
                "task_family_count": 4,
                "source_kind_count": 4,
                "train_records": 24,
                "validation_records": 8,
                "generation_executed": True,
                "dataset_validated": True,
                "environment_adapter_implemented": False,
                "verifier_implemented": False,
                "next_gate": contract.NEXT_GATE,
            },
        )

    def test_upstream_receipts_publication_and_claims_are_closed(self) -> None:
        sources = self.protocol["source_receipts"]
        self.assertEqual(set(sources), set(prepare.SOURCE_PATHS))
        for name, relative in prepare.SOURCE_PATHS.items():
            payload = (ROOT / relative).read_bytes()
            self.assertEqual(
                sources[name],
                {
                    "path": relative,
                    "bytes": len(payload),
                    "sha256": contract.sha256_bytes(payload),
                },
            )

        upstream = self.protocol["upstream"]
        self.assertEqual(
            upstream["generation_result_merge_commit"],
            contract.GENERATION_RESULT_MERGE_COMMIT,
        )
        self.assertEqual(
            upstream["generation_claims"], contract.generation.EXECUTION_CLAIMS
        )
        self.assertEqual(set(upstream["datasets"]), {"manifest", "train", "validation"})
        self.assertEqual(upstream["datasets"], self.dataset_receipts)
        self.assertEqual(
            {name for name, value in self.protocol["claims"].items() if value},
            {
                "generation_executed",
                "records_generated",
                "source_snapshots_generated",
                "screenshots_generated",
                "dataset_validated",
            },
        )
        self.assertFalse(self.protocol["claims"]["environment_adapter_implemented"])
        self.assertFalse(self.protocol["claims"]["environment_adapter_executed"])
        self.assertFalse(self.protocol["claims"]["verifier_implemented"])
        self.assertFalse(self.protocol["claims"]["verifier_executed"])
        self.assertFalse(self.protocol["claims"]["model_evaluated"])
        self.assertFalse(self.protocol["claims"]["quality_improved"])
        self.assertFalse(self.protocol["claims"]["runtime_eligible"])

    def test_source_artifacts_are_exactly_bound_outside_model_payload(self) -> None:
        registry = {
            item["source_id"]: item for item in self.protocol["source_artifact_registry"]
        }
        self.assertEqual(len(registry), 68)
        self.assertEqual(set(registry), set(self.source_bindings))
        self.assertEqual(registry, self.source_bindings)

        screenshot_paths: set[str] = set()
        snapshot_paths: set[str] = set()
        for source_id, binding in registry.items():
            self.assertEqual(binding["source_id"], source_id)
            screenshot = binding["screenshot"]
            snapshot = binding["source_snapshot"]
            self.assertNotIn(screenshot["path"], screenshot_paths)
            self.assertNotIn(snapshot["path"], snapshot_paths)
            screenshot_paths.add(screenshot["path"])
            snapshot_paths.add(snapshot["path"])
            self.assertEqual(
                screenshot,
                {
                    "path": screenshot["path"],
                    "bytes": len(self.inputs["output_payloads"][screenshot["path"]]),
                    "sha256": contract.sha256_bytes(
                        self.inputs["output_payloads"][screenshot["path"]]
                    ),
                },
            )
            self.assertEqual(
                snapshot,
                {
                    "path": snapshot["path"],
                    "bytes": len(self.inputs["output_payloads"][snapshot["path"]]),
                    "sha256": contract.sha256_bytes(
                        self.inputs["output_payloads"][snapshot["path"]]
                    ),
                },
            )
        self.assertEqual(len(screenshot_paths), 68)
        self.assertEqual(len(snapshot_paths), 68)

    def test_adapter_projection_is_closed_and_gold_and_paths_are_isolated(self) -> None:
        registry = {
            item["record_id"]: item
            for item in self.protocol["adapter_projection_registry"]
        }
        self.assertEqual(len(registry), 32)
        self.assertEqual(
            Counter(item["split"] for item in registry.values()),
            Counter({"train": 24, "validation": 8}),
        )
        self.assertEqual(
            set(item["task_family_id"] for item in registry.values()),
            set(parent.TASK_FAMILY_IDS),
        )
        self.assertEqual(
            set(item["source_kind"] for item in registry.values()),
            set(parent.SOURCE_KINDS),
        )

        for record in self.records:
            projection = contract.project_record(record, self.source_bindings)
            self.assertEqual(
                set(projection),
                {
                    "adapter_projection_version",
                    "authority",
                    "model_payload",
                    "record_id",
                    "source_bindings",
                },
            )
            model_payload = projection["model_payload"]
            self.assertEqual(set(model_payload), set(contract.MODEL_PAYLOAD_KEYS))
            self.assertFalse(_contains_forbidden_key(model_payload))
            self.assertNotIn("split", model_payload)
            self.assertNotIn("record_id", model_payload)
            self.assertNotIn("expected_output", model_payload)
            self.assertNotIn("verifier", model_payload)
            model_bytes = contract.artifact_json_bytes(model_payload)
            for binding in projection["source_bindings"]:
                self.assertNotIn(binding["screenshot"]["path"].encode(), model_bytes)
                self.assertNotIn(
                    binding["source_snapshot"]["path"].encode(), model_bytes
                )
            projection_bytes = contract.artifact_json_bytes(projection)
            frozen = registry[record["record_id"]]
            self.assertEqual(frozen["source_count"], len(projection["source_bindings"]))
            self.assertEqual(frozen["projection_bytes"], len(projection_bytes))
            self.assertEqual(
                frozen["projection_sha256"],
                contract.sha256_bytes(projection_bytes),
            )

    def test_artifact_bytes_and_record_binding_tamper_fail_closed(self) -> None:
        screenshot_tamper = dict(self.inputs["output_payloads"])
        screenshot_path = next(
            path for path in screenshot_tamper if path.endswith(".png")
        )
        screenshot_payload = screenshot_tamper[screenshot_path]
        screenshot_tamper[screenshot_path] = screenshot_payload[:-1] + bytes(
            [screenshot_payload[-1] ^ 1]
        )
        with self.assertRaisesRegex(
            contract.MM005BrowserResearchAdapterVerifierProtocolError,
            "SCREENSHOT_RECEIPT_MISMATCH",
        ):
            contract.dataset_context(screenshot_tamper)

        snapshot_tamper = dict(self.inputs["output_payloads"])
        snapshot_path = next(
            path
            for path in snapshot_tamper
            if "/snapshots/" in path and path.endswith(".json")
        )
        snapshot_payload = snapshot_tamper[snapshot_path]
        snapshot_tamper[snapshot_path] = snapshot_payload[:-2] + b"x\n"
        with self.assertRaisesRegex(
            contract.MM005BrowserResearchAdapterVerifierProtocolError,
            "SOURCE_SNAPSHOT_RECEIPT_MISMATCH",
        ):
            contract.dataset_context(snapshot_tamper)

        record = self.records[0]
        source_id = record["observation"]["sources"][0]["source_id"]
        wrong_bindings = copy.deepcopy(self.source_bindings)
        wrong_bindings[source_id]["screenshot"]["sha256"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(
            contract.MM005BrowserResearchAdapterVerifierProtocolError,
            "RECORD_SCREENSHOT_BINDING_INVALID",
        ):
            contract.project_record(record, wrong_bindings)

    def test_output_compiler_accepts_only_frozen_json_contract(self) -> None:
        expected = self.records[0]["expected_output"]
        valid_raw = contract.artifact_json_bytes(expected).decode("utf-8")
        valid = parent.compile_candidate_output(valid_raw)
        self.assertTrue(valid["valid"])
        self.assertIsNone(valid["error_code"])
        self.assertTrue(parent.verify_candidate(valid, self.records[0])["joint_correct"])

        invalid_outputs = (
            "not-json",
            "[]",
            '{"answer":"x","citation_refs":["ref-1"],"extra":true}',
            '{"answer":"x","answer":"y","citation_refs":["ref-1"]}',
            '{"answer":NaN,"citation_refs":["ref-1"]}',
            '{"answer":"x","citation_refs":["ref-1","ref-1"]}',
            '{"answer":"x","citation_refs":[]}',
            json.dumps({"answer": "x" * 1_025, "citation_refs": ["ref-1"]}),
        )
        for raw_output in invalid_outputs:
            with self.subTest(raw_output=raw_output[:80]):
                compiled = parent.compile_candidate_output(raw_output)
                self.assertFalse(compiled["valid"])
                self.assertEqual(compiled["error_code"], "invalid_output")
                self.assertFalse(
                    parent.verify_candidate(compiled, self.records[0])["joint_correct"]
                )

    def test_answer_normalization_is_nfc_ascii_space_trim_exact(self) -> None:
        record = self.records[0]
        expected = dict(record["expected_output"])

        with_space = {**expected, "answer": f"{expected['answer']} "}
        compiled_space = parent.compile_candidate_output(
            contract.artifact_json_bytes(with_space).decode("utf-8")
        )
        self.assertTrue(parent.verify_candidate(compiled_space, record)["joint_correct"])

        with_tab = {**expected, "answer": f"{expected['answer']}\t"}
        compiled_tab = parent.compile_candidate_output(
            contract.artifact_json_bytes(with_tab).decode("utf-8")
        )
        self.assertTrue(compiled_tab["valid"])
        self.assertFalse(parent.verify_candidate(compiled_tab, record)["joint_correct"])

    def test_verifier_registry_freezes_positive_negative_and_semantic_controls(
        self,
    ) -> None:
        cases = self.protocol["verifier_case_registry"]
        self.assertEqual(len(cases), 224)
        self.assertEqual(len({case["case_id"] for case in cases}), 224)
        self.assertEqual(
            Counter(case["case_kind"] for case in cases),
            Counter({kind: 32 for kind in contract.VERIFIER_CASE_KINDS}),
        )
        self.assertEqual(
            Counter(
                (case["compiler_valid"], case["verdict"]["joint_correct"])
                for case in cases
            ),
            Counter({(True, True): 32, (True, False): 128, (False, False): 64}),
        )

        record_by_id = {record["record_id"]: record for record in self.records}
        freshness_negative_count = 0
        for case in cases:
            raw_bytes = case["raw_output"].encode("utf-8")
            self.assertEqual(case["raw_output_bytes"], len(raw_bytes))
            self.assertEqual(
                case["raw_output_sha256"], contract.sha256_bytes(raw_bytes)
            )
            self.assertFalse(case["verdict"]["model_judge_used"])
            semantics = case["citation_semantics"]
            if case["case_kind"] == "exact_expected":
                self.assertTrue(case["compiler_valid"])
                self.assertTrue(case["verdict"]["joint_correct"])
                self.assertTrue(semantics["all_citation_refs_bound"])
                self.assertTrue(semantics["minimum_source_coverage_met"])
                self.assertIsNot(semantics["latest_source_cited"], False)
            else:
                self.assertFalse(case["verdict"]["joint_correct"])
            if case["case_kind"] == "unknown_dom_ref":
                self.assertFalse(semantics["all_citation_refs_bound"])
            record = record_by_id[case["record_id"]]
            if (
                case["case_kind"] == "wrong_citation_sequence_or_coverage"
                and record["task_family_id"] == "freshness_conflict_resolution"
            ):
                freshness_negative_count += 1
                self.assertFalse(semantics["latest_source_cited"])
        self.assertEqual(freshness_negative_count, 8)

    def test_protocol_registry_tamper_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.protocol)
        tampered["adapter_projection_registry"][0]["projection_bytes"] += 1
        with self.assertRaisesRegex(
            contract.MM005BrowserResearchAdapterVerifierProtocolError,
            "ADAPTER_VERIFIER_PROTOCOL_MISMATCH",
        ):
            contract.validate_protocol(tampered, **self.inputs)

        tampered = copy.deepcopy(self.protocol)
        tampered["verifier_case_registry"][0]["raw_output_bytes"] += 1
        with self.assertRaisesRegex(
            contract.MM005BrowserResearchAdapterVerifierProtocolError,
            "ADAPTER_VERIFIER_PROTOCOL_MISMATCH",
        ):
            contract.validate_protocol(tampered, **self.inputs)

    def test_authority_and_implementation_remain_deferred(self) -> None:
        plan = self.protocol["implementation_plan"]
        self.assertEqual(plan["implementation_gate_id"], contract.NEXT_GATE)
        self.assertTrue(plan["protocol_must_merge_before_implementation"])
        self.assertTrue(plan["dataset_and_generation_evidence_read_only"])
        self.assertFalse(plan["network_allowed"])
        self.assertFalse(plan["live_browser_allowed"])
        self.assertFalse(plan["model_load_allowed"])
        self.assertFalse(plan["model_training_or_evaluation_allowed"])
        self.assertFalse(plan["real_or_external_content_allowed"])
        self.assertFalse(plan["capture_allowed"])
        self.assertFalse(plan["runtime_repository_change_allowed"])
        self.assertFalse(plan["runtime_integration_allowed"])
        self.assertEqual(
            self.protocol["authority_contract"],
            {
                "page_content_has_execution_authority": False,
                "model_output_has_execution_authority": False,
                "runtime_is_sole_policy_approval_wal_grounding_budget_dispatch_boundary": True,
                "runtime_repository_changed": False,
                "runtime_integration_authorized": False,
                "capture_authorized": False,
            },
        )
        self.assertEqual(self.protocol["required_gates"], list(contract.REQUIRED_GATES))
        self.assertEqual(len(contract.REQUIRED_GATES), 21)

    def test_protocol_scope_has_no_model_network_browser_or_runtime_imports(self) -> None:
        forbidden = {
            "http",
            "openai",
            "peft",
            "playwright",
            "requests",
            "selenium",
            "socket",
            "torch",
            "transformers",
            "urllib",
        }
        for relative in prepare.SOURCE_PATHS.values():
            if not relative.startswith(
                (
                    "src/fullcycle_bridge/mm005_browser_research_adapter_verifier",
                    "scripts/prepare_mm005_browser_research_adapter_verifier",
                )
            ):
                continue
            tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
            roots = {
                alias.name.partition(".")[0]
                for node in ast.walk(tree)
                if isinstance(node, ast.Import)
                for alias in node.names
            } | {
                node.module.partition(".")[0]
                for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom) and node.module
            }
            self.assertTrue(forbidden.isdisjoint(roots), relative)


def _contains_forbidden_key(value: object) -> bool:
    if isinstance(value, Mapping):
        return any(
            str(key) in contract.FORBIDDEN_MODEL_PAYLOAD_KEYS
            or _contains_forbidden_key(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_forbidden_key(item) for item in value)
    return False


if __name__ == "__main__":
    unittest.main()
