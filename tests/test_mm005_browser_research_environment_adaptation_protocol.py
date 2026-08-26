from __future__ import annotations

import ast
import copy
import json
import sys
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SRC))

from fullcycle_bridge import (  # noqa: E402
    browser_research_environment_adaptation as contract,
)
from scripts import (  # noqa: E402
    prepare_mm005_browser_research_environment_adaptation_protocol as prepare,
)


class MM005BrowserResearchEnvironmentAdaptationProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.receipts = prepare.source_receipts()
        cls.exclusions = prepare.exclusion_registry()
        cls.protocol = prepare.build_protocol()

    def records(self) -> list[dict[str, Any]]:
        records = []
        for index, (task_family_id, source_kind) in enumerate(
            zip(contract.TASK_FAMILY_IDS, contract.SOURCE_KINDS, strict=True),
            1,
        ):
            source_count = 1 if index == 1 else 2
            sources = [
                _source(
                    record_index=index,
                    source_index=source_index,
                    published_at=(
                        "2026-07-15T00:00:00Z"
                        if index == 4 and source_index == 2
                        else "2026-07-01T00:00:00Z"
                    ),
                )
                for source_index in range(1, source_count + 1)
            ]
            citation_refs = [str(source["dom_nodes"][1]["ref"]) for source in sources]
            records.append(
                contract.build_record(
                    template_id=f"browser-template-{index}",
                    split="train" if index <= 2 else "validation",
                    task_family_id=task_family_id,
                    source_kind=source_kind,
                    instruction=f"Answer synthetic browser research question {index}.",
                    observation={
                        "snapshot_at": "2026-08-01T00:00:00Z",
                        "snapshot_source": (
                            "deterministic_reviewed_synthetic_not_live_browser"
                        ),
                        "sources": sources,
                    },
                    expected_output={
                        "answer": f"supported-value-{index}",
                        "citation_refs": citation_refs,
                    },
                    provenance=_provenance(),
                )
            )
        return records

    def rebuild(self, record: dict[str, Any], **overrides: Any) -> dict[str, Any]:
        values = {
            "template_id": record["template_id"],
            "split": record["split"],
            "task_family_id": record["task_family_id"],
            "source_kind": record["source_kind"],
            "instruction": record["instruction"],
            "observation": record["observation"],
            "expected_output": record["expected_output"],
            "provenance": record["provenance"],
        }
        values.update(overrides)
        return contract.build_record(**values)

    def test_frozen_protocol_rebuilds_exactly_with_closed_receipts(self) -> None:
        payload = prepare.OUTPUT_PATH.read_bytes()
        frozen = json.loads(payload)
        summary = contract.validate_protocol(
            frozen,
            source_receipts=self.receipts,
            exclusions=self.exclusions,
        )
        self.assertEqual(frozen, self.protocol)
        self.assertEqual(contract.canonical_json_bytes(frozen), payload)
        self.assertEqual(summary.source_receipt_count, 102)
        self.assertEqual(summary.excluded_case_count, 124)
        self.assertEqual(summary.excluded_family_count, 96)
        self.assertEqual(summary.excluded_image_count, 84)
        self.assertTrue(summary.protocol_frozen)
        self.assertFalse(summary.dataset_generated)
        self.assertFalse(summary.live_browser_used)

    def test_prior_environment_closure_is_exact_and_read_only(self) -> None:
        closure = self.protocol["prior_environment_closure"]
        self.assertEqual(
            closure["result_publication_merge_commit"],
            "5f60cbf44a311b46b312090d62d2783424c1dc85",
        )
        self.assertEqual(
            closure["closure_record_merge_commit"],
            "0a608f01e7d92ae20878da356443d80d1de0fff8",
        )
        self.assertTrue(
            closure["bounded_same_machine_fixed_suite_repeatability_established"]
        )
        self.assertFalse(closure["resource_repeatability_established"])
        self.assertTrue(closure["prior_evidence_read_only"])

    def test_environment_sequence_and_static_scope_are_bounded(self) -> None:
        sequence = self.protocol["environment_sequence"]
        scope = self.protocol["selected_scope"]
        self.assertEqual(sequence["registered_order"], list(contract.ENVIRONMENT_ORDER))
        self.assertEqual(
            sequence["completed_environments"],
            ["desktop_gui", "document_chart_pdf"],
        )
        self.assertEqual(sequence["selected_environment"], "browser_research")
        self.assertEqual(sequence["selected_order_index"], 3)
        self.assertFalse(sequence["sequence_skip_allowed"])
        self.assertEqual(
            scope["observation_modalities"], ["dom", "screenshot", "page_text"]
        )
        self.assertEqual(scope["max_sources_per_record"], 3)
        self.assertIn("live_search_or_network_retrieval", scope["deferred"])
        self.assertIn("real_user_or_external_web_content", scope["deferred"])
        self.assertIn("prompt_injection_robustness_or_safety_claims", scope["deferred"])

    def test_only_four_environment_components_are_new(self) -> None:
        delta = self.protocol["component_delta_contract"]
        self.assertEqual(
            delta["new_component_kinds"],
            [
                "environment_adapter",
                "task_set",
                "deterministic_verifier",
                "synthetic_dataset",
            ],
        )
        self.assertEqual(delta["new_component_count"], 4)
        self.assertIn("training_orchestration", delta["inherited_without_duplication"])
        self.assertIn(
            "serving_and_model_routing", delta["inherited_without_duplication"]
        )
        self.assertFalse(
            delta["environment_specific_live_browser_or_network_stack_allowed"]
        )

    def test_interfaces_authority_and_claims_remain_fail_closed(self) -> None:
        self.assertEqual(
            self.protocol["adapter_contract"]["output_projection"]["exact_keys"],
            ["answer", "citation_refs"],
        )
        self.assertEqual(
            self.protocol["task_set_contract"]["task_family_ids"],
            list(contract.TASK_FAMILY_IDS),
        )
        self.assertFalse(self.protocol["verifier_contract"]["model_or_llm_judge_used"])
        authority = self.protocol["authority_contract"]
        self.assertFalse(
            authority["page_content_has_instruction_or_execution_authority"]
        )
        self.assertFalse(authority["live_browser_navigation_authorized"])
        self.assertFalse(authority["network_retrieval_authorized"])
        self.assertTrue(
            authority[
                "runtime_is_sole_policy_approval_wal_grounding_budget_dispatch_boundary"
            ]
        )
        self.assertTrue(
            all(value is False for value in self.protocol["claims"].values())
        )
        self.assertEqual(self.protocol["next_gate"], contract.NEXT_GATE)

    def test_protocol_tamper_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.protocol)
        tampered["claims"]["live_browser_used"] = True
        with self.assertRaisesRegex(
            contract.MM005BrowserResearchProtocolError, "PROTOCOL_MISMATCH"
        ):
            contract.validate_protocol(
                tampered,
                source_receipts=self.receipts,
                exclusions=self.exclusions,
            )

    def test_future_records_cover_families_sources_splits_and_snapshots(self) -> None:
        self.assertEqual(
            contract.validate_records(self.records(), self.exclusions),
            {
                "record_count": 4,
                "family_count": 4,
                "task_family_count": 4,
                "source_kind_count": 4,
                "source_snapshot_count": 7,
                "splits": ["train", "validation"],
            },
        )

    def test_record_source_and_cross_stage_identities_are_deterministic(self) -> None:
        left = self.records()[0]
        right = self.records()[0]
        self.assertEqual(left, right)
        source = left["observation"]["sources"][0]
        self.assertEqual(
            left["identities"]["source_url_sha256"][0],
            contract.browser_identity("source_url", source["url"]),
        )
        self.assertEqual(
            left["record_id"],
            contract.browser_identity(
                "record",
                {key: value for key, value in left.items() if key != "record_id"},
            ),
        )

    def test_dom_or_page_text_tamper_is_rejected(self) -> None:
        record = self.records()[0]
        observation = copy.deepcopy(record["observation"])
        observation["sources"][0]["page_text"] = "tampered"
        with self.assertRaisesRegex(
            contract.MM005BrowserResearchProtocolError, "PAGE_TEXT_DOM_MISMATCH"
        ):
            self.rebuild(record, observation=observation)

    def test_cross_split_source_reuse_is_rejected(self) -> None:
        records = self.records()
        observation = copy.deepcopy(records[2]["observation"])
        observation["sources"][0] = copy.deepcopy(
            records[0]["observation"]["sources"][0]
        )
        expected = {
            **records[2]["expected_output"],
            "citation_refs": [
                observation["sources"][0]["dom_nodes"][1]["ref"],
                observation["sources"][1]["dom_nodes"][1]["ref"],
            ],
        }
        records[2] = self.rebuild(
            records[2], observation=observation, expected_output=expected
        )
        with self.assertRaisesRegex(
            contract.MM005BrowserResearchProtocolError, "CROSS_SPLIT_LEAKAGE"
        ):
            contract.validate_records(records, self.exclusions)

    def test_prior_document_content_reuse_is_rejected(self) -> None:
        records = self.records()
        upstream = prepare._load_json(
            ROOT / prepare.SOURCE_PATHS["mm005_document_train"][0]
        )
        records[0] = self.rebuild(
            records[0], instruction=upstream["records"][0]["instruction"]
        )
        with self.assertRaisesRegex(
            contract.MM005BrowserResearchProtocolError,
            "PRIOR_EXCLUSION_COLLISION",
        ):
            contract.validate_records(records, self.exclusions)

    def test_real_live_network_or_capture_provenance_is_rejected(self) -> None:
        record = self.records()[0]
        for key in (
            "real_content",
            "external_content",
            "network_accessed",
            "live_browser_used",
            "capture_adapter_used",
        ):
            provenance = {**record["provenance"], key: True}
            with (
                self.subTest(key=key),
                self.assertRaisesRegex(
                    contract.MM005BrowserResearchProtocolError, "PROVENANCE_INVALID"
                ),
            ):
                self.rebuild(record, provenance=provenance)

    def test_only_static_invalid_domain_urls_are_allowed(self) -> None:
        record = self.records()[0]
        for invalid_url in (
            "http://source.invalid/page",
            "https://example.com/page",
            "https://source.invalid/page?q=live",
            "https://user@source.invalid/page",
            "https://source.invalid:443/page",
        ):
            observation = copy.deepcopy(record["observation"])
            observation["sources"][0]["url"] = invalid_url
            with (
                self.subTest(url=invalid_url),
                self.assertRaisesRegex(
                    contract.MM005BrowserResearchProtocolError, "SYNTHETIC_URL_INVALID"
                ),
            ):
                self.rebuild(record, observation=observation)

    def test_source_published_after_snapshot_is_rejected(self) -> None:
        record = self.records()[0]
        observation = copy.deepcopy(record["observation"])
        observation["sources"][0]["published_at"] = "2026-09-01T00:00:00Z"
        with self.assertRaisesRegex(
            contract.MM005BrowserResearchProtocolError,
            "SOURCE_PUBLISHED_AFTER_SNAPSHOT",
        ):
            self.rebuild(record, observation=observation)

    def test_citations_must_exist_and_cover_multi_source_tasks(self) -> None:
        single = self.records()[0]
        missing = {**single["expected_output"], "citation_refs": ["missing-ref"]}
        with self.assertRaisesRegex(
            contract.MM005BrowserResearchProtocolError,
            "EXPECTED_CITATION_REF_MISSING",
        ):
            self.rebuild(single, expected_output=missing)

        multi = self.records()[1]
        one_source = {
            **multi["expected_output"],
            "citation_refs": [
                multi["observation"]["sources"][0]["dom_nodes"][1]["ref"]
            ],
        }
        with self.assertRaisesRegex(
            contract.MM005BrowserResearchProtocolError,
            "MULTI_SOURCE_CITATION_COVERAGE_INVALID",
        ):
            self.rebuild(multi, expected_output=one_source)

    def test_freshness_task_must_cite_the_latest_source(self) -> None:
        record = self.records()[3]
        observation = copy.deepcopy(record["observation"])
        older_third_source = _source(
            record_index=4,
            source_index=3,
            published_at="2026-06-15T00:00:00Z",
        )
        observation["sources"].append(older_third_source)
        expected = {
            **record["expected_output"],
            "citation_refs": [
                observation["sources"][0]["dom_nodes"][1]["ref"],
                observation["sources"][2]["dom_nodes"][1]["ref"],
            ],
        }
        with self.assertRaisesRegex(
            contract.MM005BrowserResearchProtocolError,
            "LATEST_SOURCE_CITATION_MISSING",
        ):
            self.rebuild(
                record,
                observation=observation,
                expected_output=expected,
            )

    def test_strict_compiler_and_verifier_are_total_and_model_free(self) -> None:
        record = self.records()[0]
        valid_raw = json.dumps(record["expected_output"])
        compiled = contract.compile_candidate_output(valid_raw)
        self.assertTrue(compiled["valid"])
        self.assertTrue(contract.verify_candidate(compiled, record)["joint_correct"])

        wrong = contract.compile_candidate_output(
            json.dumps({**record["expected_output"], "answer": "wrong"})
        )
        self.assertFalse(contract.verify_candidate(wrong, record)["joint_correct"])
        for invalid_raw in (
            "not-json",
            '{"answer":"x","answer":"y","citation_refs":["source-1-1-fact"]}',
            '{"answer":"x","citation_refs":["source-1-1-fact"],"extra":0}',
            "\ud800",
        ):
            invalid = contract.compile_candidate_output(invalid_raw)
            self.assertFalse(invalid["valid"])
            self.assertFalse(
                contract.verify_candidate(invalid, record)["joint_correct"]
            )
        self.assertFalse(
            contract.verify_candidate({"valid": True}, record)["joint_correct"]
        )

        forbidden_roots = {
            "httpx",
            "playwright",
            "requests",
            "selenium",
            "socket",
            "subprocess",
            "torch",
            "transformers",
        }
        for relative in (
            "src/fullcycle_bridge/browser_research_environment_adaptation.py",
            "scripts/prepare_mm005_browser_research_environment_adaptation_protocol.py",
        ):
            tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
            import_roots = {
                alias.name.partition(".")[0]
                for node in ast.walk(tree)
                if isinstance(node, ast.Import)
                for alias in node.names
            } | {
                node.module.partition(".")[0]
                for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom) and node.module
            }
            self.assertTrue(forbidden_roots.isdisjoint(import_roots))


def _source(
    *, record_index: int, source_index: int, published_at: str
) -> dict[str, Any]:
    source_id = f"source-{record_index}-{source_index}"
    nodes = [
        {
            "bbox": [80, 80, 920, 180],
            "ref": f"{source_id}-title",
            "tag": "h1",
            "text": f"Synthetic Research Source {record_index}-{source_index}",
        },
        {
            "bbox": [100, 240, 900, 420],
            "ref": f"{source_id}-fact",
            "tag": "p",
            "text": f"Supported fact {record_index}-{source_index}",
        },
    ]
    return {
        "dom_nodes": nodes,
        "page_text": "\n".join(str(node["text"]) for node in nodes),
        "published_at": published_at,
        "screenshot_sha256": contract.sha256_bytes(
            f"browser-screenshot-{record_index}-{source_index}".encode()
        ),
        "source_id": source_id,
        "title": f"Synthetic Source {record_index}-{source_index}",
        "url": (
            f"https://source-{record_index}-{source_index}.invalid/research/"
            f"page-{record_index}"
        ),
    }


def _provenance() -> dict[str, Any]:
    return {
        "source": "deterministic_reviewed_synthetic_browser_snapshot_generation",
        "license": "repository_generated_synthetic",
        "synthetic_only": True,
        "real_content": False,
        "external_content": False,
        "network_accessed": False,
        "live_browser_used": False,
        "capture_adapter_used": False,
        "page_content_has_execution_authority": False,
        "model_output_has_execution_authority": False,
        "runtime_integration_authorized": False,
    }


if __name__ == "__main__":
    unittest.main()
