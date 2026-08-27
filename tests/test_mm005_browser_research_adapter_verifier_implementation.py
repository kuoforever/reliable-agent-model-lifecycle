from __future__ import annotations

import ast
import copy
import json
import subprocess
import sys
import unittest
from collections import Counter
from collections.abc import Mapping
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(ROOT))

from fullcycle_bridge import (  # noqa: E402
    browser_research_environment_adaptation as parent,
)
from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_adapter_verifier as implementation,
)
from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_adapter_verifier_implementation as evidence,
)
from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_adapter_verifier_protocol as protocol,
)
from scripts import (  # noqa: E402
    prepare_mm005_browser_research_adapter_verifier_implementation as prepare,
)

EXPECTED_EVIDENCE_BYTES = 195_994
EXPECTED_EVIDENCE_SHA256 = (
    "sha256:77634e6202354641eef84cf1640c17588e902c073f804b535dfb3ada52d09876"
)


class MM005BrowserResearchAdapterVerifierImplementationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.inputs = prepare.implementation_inputs()
        cls.evidence_payload = (ROOT / evidence.EVIDENCE_PATH).read_bytes()
        cls.evidence_value = json.loads(cls.evidence_payload)
        cls.protocol_value = json.loads(cls.inputs["protocol_payload"])
        cls.records, cls.source_bindings, _ = protocol.dataset_context(
            cls.inputs["output_payloads"]
        )
        cls.screenshot_payloads = {
            str(binding["screenshot"]["path"]): cls.inputs["output_payloads"][
                str(binding["screenshot"]["path"])
            ]
            for binding in cls.source_bindings.values()
        }
        cls.source_snapshot_payloads = {
            str(binding["source_snapshot"]["path"]): cls.inputs["output_payloads"][
                str(binding["source_snapshot"]["path"])
            ]
            for binding in cls.source_bindings.values()
        }

    def test_tracked_evidence_rebuilds_and_validates_exactly(self) -> None:
        self.assertEqual(len(self.evidence_payload), EXPECTED_EVIDENCE_BYTES)
        self.assertEqual(
            evidence.sha256_bytes(self.evidence_payload), EXPECTED_EVIDENCE_SHA256
        )
        self.assertEqual(
            evidence.artifact_json_bytes(self.evidence_value), self.evidence_payload
        )
        summary = evidence.validate_evidence(self.evidence_value, **self.inputs)
        self.assertEqual(summary.record_count, 32)
        self.assertEqual(summary.source_binding_count, 68)
        self.assertEqual(summary.adapter_projection_count, 32)
        self.assertEqual(summary.verifier_case_count, 224)
        self.assertEqual(summary.positive_case_count, 32)
        self.assertEqual(summary.negative_case_count, 192)
        self.assertEqual(summary.freshness_negative_count, 8)
        self.assertEqual(summary.next_gate, evidence.NEXT_GATE)

    def test_protocol_was_merged_first_and_consumed_sources_are_exact(self) -> None:
        ancestor = subprocess.run(
            [
                "git",
                "merge-base",
                "--is-ancestor",
                evidence.PROTOCOL_MERGE_COMMIT,
                "HEAD",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
        )
        self.assertEqual(ancestor.returncode, 0)
        frozen_protocol = subprocess.run(
            [
                "git",
                "show",
                f"{evidence.PROTOCOL_MERGE_COMMIT}:{protocol.PROTOCOL_PATH}",
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout
        self.assertEqual(frozen_protocol, self.inputs["protocol_payload"])
        self.assertEqual(
            self.evidence_value["protocol"]["merge_commit"],
            evidence.PROTOCOL_MERGE_COMMIT,
        )
        self.assertTrue(self.evidence_value["consumed_inputs"]["read_only"])
        self.assertFalse(self.evidence_value["consumed_inputs"]["generation_rerun"])
        self.assertEqual(len(self.evidence_value["implementation_source_receipts"]), 5)
        for name, path in prepare.SOURCE_PATHS.items():
            payload = (ROOT / path).read_bytes()
            self.assertEqual(
                self.evidence_value["implementation_source_receipts"][name],
                {
                    "path": path,
                    "bytes": len(payload),
                    "sha256": evidence.sha256_bytes(payload),
                },
            )

    def test_all_adapter_projections_match_the_frozen_registry(self) -> None:
        observed: list[dict[str, object]] = []
        for record in sorted(self.records, key=lambda item: str(item["record_id"])):
            adapted = implementation.adapt_record(
                record, self.screenshot_payloads, self.source_snapshot_payloads
            )
            observed.append(implementation.projection_receipt(record, adapted))
            projection = adapted.audit_projection()
            model_payload = adapted.model_payload()
            self.assertEqual(set(model_payload), set(protocol.MODEL_PAYLOAD_KEYS))
            self.assertFalse(_contains_forbidden_key(model_payload))
            self.assertEqual(
                len(adapted.screenshot_payloads), len(projection["source_bindings"])
            )
            self.assertEqual(
                len(adapted.source_snapshot_payloads),
                len(projection["source_bindings"]),
            )
            for index, binding in enumerate(projection["source_bindings"]):
                self.assertEqual(
                    implementation.sha256_bytes(adapted.screenshot_payloads[index]),
                    binding["screenshot"]["sha256"],
                )
                self.assertEqual(
                    implementation.sha256_bytes(
                        adapted.source_snapshot_payloads[index]
                    ),
                    binding["source_snapshot"]["sha256"],
                )
                self.assertNotIn(
                    binding["screenshot"]["path"].encode(), adapted.model_payload_json
                )
                self.assertNotIn(
                    binding["source_snapshot"]["path"].encode(),
                    adapted.model_payload_json,
                )
            mutable_copy = adapted.audit_projection()
            mutable_copy["record_id"] = "tampered"
            self.assertNotEqual(
                mutable_copy["record_id"], adapted.audit_projection()["record_id"]
            )
        self.assertEqual(observed, self.protocol_value["adapter_projection_registry"])

    def test_adapter_rejects_missing_duplicate_tampered_or_unsafe_artifacts(
        self,
    ) -> None:
        record = self.records[0]
        adapted = implementation.adapt_record(
            record, self.screenshot_payloads, self.source_snapshot_payloads
        )
        binding = adapted.audit_projection()["source_bindings"][0]
        screenshot_path = binding["screenshot"]["path"]
        snapshot_path = binding["source_snapshot"]["path"]

        missing_screenshot = dict(self.screenshot_payloads)
        del missing_screenshot[screenshot_path]
        with self.assertRaisesRegex(
            implementation.MM005BrowserResearchAdapterVerifierError,
            "SOURCE_SNAPSHOT_SCREENSHOT_MISSING|RECORD_SCREENSHOT_BINDING_INVALID",
        ):
            implementation.adapt_record(
                record, missing_screenshot, self.source_snapshot_payloads
            )

        duplicate_screenshot = dict(self.screenshot_payloads)
        duplicate_screenshot["fixtures/mm005_browser_research_v1/duplicate.png"] = (
            self.screenshot_payloads[screenshot_path]
        )
        with self.assertRaisesRegex(
            implementation.MM005BrowserResearchAdapterVerifierError,
            "RECORD_SCREENSHOT_BINDING_INVALID",
        ):
            implementation.adapt_record(
                record, duplicate_screenshot, self.source_snapshot_payloads
            )

        tampered_screenshot = dict(self.screenshot_payloads)
        screenshot_bytes = tampered_screenshot[screenshot_path]
        tampered_screenshot[screenshot_path] = screenshot_bytes[:-1] + bytes(
            [screenshot_bytes[-1] ^ 1]
        )
        with self.assertRaisesRegex(
            implementation.MM005BrowserResearchAdapterVerifierError,
            "RECORD_SCREENSHOT_BINDING_INVALID",
        ):
            implementation.adapt_record(
                record, tampered_screenshot, self.source_snapshot_payloads
            )

        missing_snapshot = dict(self.source_snapshot_payloads)
        del missing_snapshot[snapshot_path]
        with self.assertRaisesRegex(
            implementation.MM005BrowserResearchAdapterVerifierError,
            "RECORD_SOURCE_SNAPSHOT_BINDING_INVALID",
        ):
            implementation.adapt_record(record, self.screenshot_payloads, missing_snapshot)

        duplicate_snapshot = dict(self.source_snapshot_payloads)
        duplicate_snapshot[
            "fixtures/mm005_browser_research_v1/snapshots/duplicate.json"
        ] = self.source_snapshot_payloads[snapshot_path]
        with self.assertRaisesRegex(
            implementation.MM005BrowserResearchAdapterVerifierError,
            "RECORD_SOURCE_SNAPSHOT_BINDING_INVALID",
        ):
            implementation.adapt_record(
                record, self.screenshot_payloads, duplicate_snapshot
            )

        tampered_snapshot = dict(self.source_snapshot_payloads)
        snapshot = json.loads(tampered_snapshot[snapshot_path])
        snapshot["template_id"] = "tampered-template"
        tampered_snapshot[snapshot_path] = implementation.artifact_json_bytes(snapshot)
        with self.assertRaisesRegex(
            implementation.MM005BrowserResearchAdapterVerifierError,
            "SOURCE_SNAPSHOT_RECORD_MISMATCH",
        ):
            implementation.adapt_record(record, self.screenshot_payloads, tampered_snapshot)

        for unsafe_path in ("../escape.png", "C:/escape.png", "bad\\escape.png"):
            unsafe_screenshot = dict(self.screenshot_payloads)
            unsafe_screenshot[unsafe_path] = b"unsafe"
            with self.subTest(unsafe_path=unsafe_path), self.assertRaisesRegex(
                implementation.MM005BrowserResearchAdapterVerifierError,
                "ARTIFACT_PATH_INVALID",
            ):
                implementation.adapt_record(
                    record, unsafe_screenshot, self.source_snapshot_payloads
                )

    def test_compiler_is_independent_and_matches_reference_on_all_edges(self) -> None:
        for case in self.protocol_value["verifier_case_registry"]:
            raw_output = case["raw_output"]
            self.assertEqual(
                implementation.compile_candidate_output(raw_output),
                parent.compile_candidate_output(raw_output),
            )

        expected = self.records[0]["expected_output"]
        valid_raw = implementation.artifact_json_bytes(expected).decode("utf-8")
        self.assertTrue(implementation.compile_candidate_output(valid_raw)["valid"])
        invalid_outputs: tuple[object, ...] = (
            None,
            1,
            "not-json",
            "[]",
            '{"answer":"x","citation_refs":["ref-1"],"extra":true}',
            '{"answer":"x","answer":"y","citation_refs":["ref-1"]}',
            '{"answer":NaN,"citation_refs":["ref-1"]}',
            '{"answer":"x","citation_refs":["ref-1","ref-1"]}',
            '{"answer":"x","citation_refs":[]}',
            '{"answer":true,"citation_refs":["ref-1"]}',
            '{"answer":"x","citation_refs":[true]}',
            json.dumps({"answer": "x" * 1_025, "citation_refs": ["ref-1"]}),
            " " * 8_193,
            "\ud800",
        )
        for raw_output in invalid_outputs:
            with self.subTest(raw_output=repr(raw_output)[:80]):
                compiled = implementation.compile_candidate_output(raw_output)
                self.assertFalse(compiled["valid"])
                self.assertEqual(compiled["error_code"], "invalid_output")

        tree = ast.parse(
            (ROOT / prepare.SOURCE_PATHS["adapter_verifier_component"]).read_text(
                encoding="utf-8"
            )
        )
        functions = {
            node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)
        }
        for function_name in (
            "compile_candidate_output",
            "verify_candidate",
            "citation_semantics",
        ):
            direct_parent_calls = [
                node
                for node in ast.walk(functions[function_name])
                if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "parent"
            ]
            self.assertEqual(direct_parent_calls, [], function_name)

    def test_all_verifier_cases_match_the_frozen_reference(self) -> None:
        records = {str(record["record_id"]): record for record in self.records}
        distribution: Counter[str] = Counter()
        outcomes: Counter[tuple[bool, bool]] = Counter()
        freshness_negatives = 0
        for case in self.protocol_value["verifier_case_registry"]:
            record = records[case["record_id"]]
            compiled = implementation.compile_candidate_output(case["raw_output"])
            verdict = implementation.verify_candidate(compiled, record)
            semantics = implementation.citation_semantics(compiled, record)
            self.assertEqual(compiled["valid"], case["compiler_valid"])
            self.assertEqual(compiled["error_code"], case["compiler_error_code"])
            self.assertEqual(verdict, case["verdict"])
            self.assertEqual(semantics, case["citation_semantics"])
            distribution[case["case_kind"]] += 1
            outcomes[(compiled["valid"], verdict["joint_correct"])] += 1
            if (
                case["case_kind"] == "wrong_citation_sequence_or_coverage"
                and record["task_family_id"] == "freshness_conflict_resolution"
            ):
                freshness_negatives += 1
                self.assertFalse(semantics["latest_source_cited"])
        self.assertEqual(
            distribution,
            Counter({kind: 32 for kind in protocol.VERIFIER_CASE_KINDS}),
        )
        self.assertEqual(
            outcomes,
            Counter({(True, True): 32, (True, False): 128, (False, False): 64}),
        )
        self.assertEqual(freshness_negatives, 8)

    def test_verifier_rejects_forged_compiled_objects(self) -> None:
        record = self.records[0]
        valid = implementation.compile_candidate_output(
            implementation.artifact_json_bytes(record["expected_output"]).decode()
        )
        forged_values: list[object] = [
            {},
            [],
            {**valid, "extra": True},
            {key: value for key, value in valid.items() if key != "error_code"},
            {**valid, "compiler_version": True},
            {**valid, "compiler_version": 2},
            {**valid, "valid": 1},
            {**valid, "answer": ""},
            {**valid, "answer": "x" * 1_025},
            {**valid, "citation_refs": []},
            {**valid, "citation_refs": ["ref-1", "ref-1"]},
            {**valid, "error_code": "forged"},
            {
                "compiler_version": 1,
                "valid": False,
                "answer": "forged",
                "citation_refs": [],
                "error_code": "invalid_output",
            },
        ]
        for forged in forged_values:
            with self.subTest(forged=forged):
                verdict = implementation.verify_candidate(forged, record)
                semantics = implementation.citation_semantics(forged, record)
                self.assertFalse(verdict["valid_output"])
                self.assertFalse(verdict["joint_correct"])
                self.assertFalse(semantics["all_citation_refs_bound"])
                self.assertEqual(semantics["cited_source_ids"], [])

    def test_answer_normalization_is_nfc_ascii_space_trim_exact(self) -> None:
        record = self.records[0]
        expected = record["expected_output"]
        with_space = {**expected, "answer": f" {expected['answer']} "}
        compiled_space = implementation.compile_candidate_output(
            implementation.artifact_json_bytes(with_space).decode()
        )
        self.assertTrue(implementation.verify_candidate(compiled_space, record)["joint_correct"])

        with_tab = {**expected, "answer": f"{expected['answer']}\t"}
        compiled_tab = implementation.compile_candidate_output(
            implementation.artifact_json_bytes(with_tab).decode()
        )
        self.assertFalse(implementation.verify_candidate(compiled_tab, record)["joint_correct"])

        unicode_record = copy.deepcopy(record)
        unicode_expected = {
            "answer": "Caf\u00e9",
            "citation_refs": list(expected["citation_refs"]),
        }
        unicode_record["expected_output"] = unicode_expected
        unicode_record["identities"]["target_content_sha256"] = parent.content_identity(
            "target", unicode_expected
        )
        body = {key: unicode_record[key] for key in unicode_record if key != "record_id"}
        unicode_record["record_id"] = parent.browser_identity("record", body)
        decomposed = {
            "answer": "Cafe\u0301",
            "citation_refs": list(expected["citation_refs"]),
        }
        compiled_unicode = implementation.compile_candidate_output(
            implementation.artifact_json_bytes(decomposed).decode()
        )
        self.assertTrue(
            implementation.verify_candidate(compiled_unicode, unicode_record)[
                "joint_correct"
            ]
        )

    def test_citation_semantics_cover_binding_multi_source_and_freshness(self) -> None:
        records_by_family: dict[str, Mapping[str, object]] = {}
        for record in self.records:
            records_by_family.setdefault(str(record["task_family_id"]), record)

        for family, minimum_sources in (
            ("single_source_fact_citation", 1),
            ("multi_source_synthesis_citation", 2),
            ("cross_source_comparison_citation", 2),
            ("freshness_conflict_resolution", 2),
        ):
            record = records_by_family[family]
            compiled = implementation.compile_candidate_output(
                implementation.artifact_json_bytes(record["expected_output"]).decode()
            )
            semantics = implementation.citation_semantics(compiled, record)
            self.assertTrue(semantics["all_citation_refs_bound"])
            self.assertTrue(semantics["minimum_source_coverage_met"])
            self.assertGreaterEqual(len(semantics["cited_source_ids"]), minimum_sources)
            if family == "freshness_conflict_resolution":
                self.assertTrue(semantics["latest_source_cited"])
            else:
                self.assertIsNone(semantics["latest_source_cited"])

    def test_evidence_registries_receipts_and_distributions_are_exact(self) -> None:
        adapter = self.evidence_value["adapter_implementation"]
        verifier = self.evidence_value["verifier_implementation"]
        self.assertEqual(len(adapter["execution_registry"]), 32)
        self.assertEqual(len(verifier["execution_registry"]), 224)
        self.assertEqual(
            adapter["execution_registry_receipt"],
            _payload_receipt(
                evidence.artifact_json_bytes(adapter["execution_registry"])
            ),
        )
        self.assertEqual(
            verifier["execution_registry_receipt"],
            _payload_receipt(
                evidence.artifact_json_bytes(verifier["execution_registry"])
            ),
        )
        self.assertEqual(
            verifier["case_distribution"],
            {kind: 32 for kind in sorted(protocol.VERIFIER_CASE_KINDS)},
        )
        summary = self.evidence_value["summary"]
        self.assertEqual(summary["model_payload_bytes"], 81_796)
        self.assertEqual(summary["screenshot_bytes"], 600_604)
        self.assertEqual(summary["source_snapshot_bytes"], 118_742)
        self.assertEqual(summary["compiler_valid_count"], 160)
        self.assertEqual(summary["compiler_invalid_count"], 64)

    def test_claims_authority_and_next_gate_are_narrow(self) -> None:
        claims = self.evidence_value["claims"]
        true_claims = {name for name, established in claims.items() if established}
        self.assertEqual(
            true_claims,
            {
                "dataset_validated",
                "environment_adapter_executed",
                "environment_adapter_implemented",
                "generation_executed",
                "records_generated",
                "screenshots_generated",
                "source_snapshots_generated",
                "verifier_executed",
                "verifier_implemented",
            },
        )
        for claim in (
            "model_evaluated",
            "model_trained",
            "quality_improved",
            "safety_established",
            "prompt_injection_safety_established",
            "network_accessed",
            "live_browser_used",
            "real_content_collected",
            "external_content_collected",
            "runtime_repository_changed",
            "runtime_integration_changed",
            "serving_eligible",
            "promotion_eligible",
            "runtime_eligible",
        ):
            self.assertFalse(claims[claim], claim)
        self.assertEqual(len(evidence.REQUIRED_GATES), 18)
        self.assertEqual(
            self.evidence_value["gate_results"],
            {gate: True for gate in evidence.REQUIRED_GATES},
        )
        self.assertEqual(
            self.evidence_value["authority_contract"],
            {
                "page_content_has_execution_authority": False,
                "model_output_has_execution_authority": False,
                "runtime_is_sole_policy_approval_wal_grounding_budget_dispatch_boundary": True,
                "runtime_repository_changed": False,
                "runtime_integration_authorized": False,
                "capture_authorized": False,
            },
        )
        self.assertEqual(self.evidence_value["next_gate"], evidence.NEXT_GATE)

    def test_resealed_evidence_tamper_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.evidence_value)
        tampered["summary"]["verifier_case_count"] += 1
        with self.assertRaisesRegex(
            evidence.MM005BrowserResearchAdapterVerifierImplementationError,
            "IMPLEMENTATION_EVIDENCE_MISMATCH",
        ):
            evidence.validate_evidence(tampered, **self.inputs)

    def test_implementation_scope_has_no_model_network_browser_or_runtime_imports(
        self,
    ) -> None:
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
                    "scripts/prepare_mm005_browser_research_adapter_verifier_implementation",
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


def _payload_receipt(payload: bytes) -> dict[str, object]:
    return {"bytes": len(payload), "sha256": evidence.sha256_bytes(payload)}


def _contains_forbidden_key(value: object) -> bool:
    if isinstance(value, Mapping):
        return any(
            str(key) in implementation.FORBIDDEN_MODEL_PAYLOAD_KEYS
            or _contains_forbidden_key(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_forbidden_key(item) for item in value)
    return False


if __name__ == "__main__":
    unittest.main()
