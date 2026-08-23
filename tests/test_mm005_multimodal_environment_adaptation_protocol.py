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
    multimodal_environment_adaptation as contract,
)
from scripts import (  # noqa: E402
    prepare_mm005_multimodal_environment_adaptation_protocol as prepare,
)


class MM005EnvironmentAdaptationProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.receipts = prepare.source_receipts()
        cls.exclusions = prepare.exclusion_registry()
        cls.protocol = prepare.build_protocol()

    def records(self) -> list[dict[str, Any]]:
        records = []
        source_kinds = (
            "synthetic_text_document",
            "synthetic_table_document",
            "synthetic_bar_chart",
            "synthetic_single_page_pdf",
        )
        for index, (task_family_id, source_kind) in enumerate(
            zip(contract.TASK_FAMILY_IDS, source_kinds, strict=True),
            1,
        ):
            ref = f"evidence-{index}"
            records.append(
                contract.build_record(
                    template_id=f"template-{index}",
                    split="train" if index <= 2 else "validation",
                    task_family_id=task_family_id,
                    source_kind=source_kind,
                    instruction=f"Answer synthetic document question {index}.",
                    observation={
                        "image_sha256": contract.sha256_bytes(
                            f"mm005-image-{index}".encode()
                        ),
                        "layout_source": "synthetic_ground_truth_not_runtime_ocr",
                        "page_count": 1,
                        "page_number": 1,
                        "regions": [
                            {
                                "bbox": [100, 100, 500, 300],
                                "ref": ref,
                                "role": "text" if index == 1 else "table_cell",
                                "visible_text": f"synthetic value {index}",
                            }
                        ],
                    },
                    expected_output={
                        "answer": ref if index == 4 else f"value-{index}",
                        "evidence_refs": [ref],
                        "page_number": 1,
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
        self.assertEqual(summary.source_receipt_count, 63)
        self.assertEqual(summary.excluded_case_count, 92)
        self.assertEqual(summary.excluded_family_count, 64)
        self.assertEqual(summary.excluded_image_count, 52)
        self.assertTrue(summary.protocol_frozen)
        self.assertFalse(summary.dataset_generated)

    def test_environment_sequence_and_vertical_scope_are_bounded(self) -> None:
        sequence = self.protocol["environment_sequence"]
        scope = self.protocol["selected_scope"]
        self.assertEqual(sequence["registered_order"], list(contract.ENVIRONMENT_ORDER))
        self.assertEqual(sequence["selected_environment"], "document_chart_pdf")
        self.assertEqual(sequence["selected_order_index"], 2)
        self.assertFalse(sequence["sequence_skip_allowed"])
        self.assertEqual(scope["page_count"], 1)
        self.assertEqual(scope["content_language"], "en")
        self.assertIn("real_user_or_external_documents", scope["deferred"])
        self.assertIn("tool_or_desktop_execution", scope["deferred"])

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
        self.assertIn("serving_and_model_routing", delta["inherited_without_duplication"])
        self.assertFalse(delta["environment_specific_training_pipeline_allowed"])

    def test_interfaces_authority_and_claims_remain_fail_closed(self) -> None:
        self.assertEqual(
            self.protocol["adapter_contract"]["output_projection"]["exact_keys"],
            ["answer", "evidence_refs", "page_number"],
        )
        self.assertEqual(
            self.protocol["task_set_contract"]["task_family_ids"],
            list(contract.TASK_FAMILY_IDS),
        )
        self.assertFalse(self.protocol["verifier_contract"]["model_or_llm_judge_used"])
        authority = self.protocol["authority_contract"]
        self.assertTrue(
            authority[
                "runtime_is_sole_policy_approval_wal_grounding_budget_dispatch_boundary"
            ]
        )
        self.assertFalse(authority["runtime_integration_authorized"])
        self.assertTrue(all(value is False for value in self.protocol["claims"].values()))
        self.assertEqual(self.protocol["next_gate"], contract.NEXT_GATE)

    def test_protocol_tamper_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.protocol)
        tampered["claims"]["dataset_generated"] = True
        with self.assertRaisesRegex(contract.MM005ProtocolError, "PROTOCOL_MISMATCH"):
            contract.validate_protocol(
                tampered,
                source_receipts=self.receipts,
                exclusions=self.exclusions,
            )

    def test_future_records_cover_all_families_sources_and_splits(self) -> None:
        self.assertEqual(
            contract.validate_records(self.records(), self.exclusions),
            {
                "record_count": 4,
                "family_count": 4,
                "task_family_count": 4,
                "source_kind_count": 4,
                "splits": ["train", "validation"],
            },
        )

    def test_record_and_cross_stage_identities_are_deterministic(self) -> None:
        left = self.records()[0]
        right = self.records()[0]
        self.assertEqual(left, right)
        self.assertEqual(
            left["identities"]["instruction_content_sha256"],
            contract.content_identity("instruction", left["instruction"]),
        )
        self.assertEqual(
            left["record_id"],
            contract.local_identity(
                "record", {key: value for key, value in left.items() if key != "record_id"}
            ),
        )

    def test_record_tamper_is_detected(self) -> None:
        records = self.records()
        records[0]["observation"]["regions"][0]["visible_text"] = "tampered"
        with self.assertRaisesRegex(contract.MM005ProtocolError, "CONTENT_IDENTITY_MISMATCH"):
            contract.validate_records(records, self.exclusions)

    def test_cross_split_content_reuse_is_rejected(self) -> None:
        records = self.records()
        records[2] = self.rebuild(records[2], instruction=records[0]["instruction"])
        with self.assertRaisesRegex(contract.MM005ProtocolError, "CROSS_SPLIT_LEAKAGE"):
            contract.validate_records(records, self.exclusions)

    def test_prior_stage_content_reuse_is_rejected(self) -> None:
        records = self.records()
        upstream = prepare._load_json(ROOT / prepare.SOURCE_PATHS["mm004_train"][0])
        records[0] = self.rebuild(
            records[0], instruction=upstream["records"][0]["instruction"]
        )
        with self.assertRaisesRegex(contract.MM005ProtocolError, "PRIOR_EXCLUSION_COLLISION"):
            contract.validate_records(records, self.exclusions)

    def test_real_or_capture_provenance_is_rejected(self) -> None:
        record = self.records()[0]
        provenance = {**record["provenance"], "real_content": True}
        with self.assertRaisesRegex(contract.MM005ProtocolError, "PROVENANCE_INVALID"):
            self.rebuild(record, provenance=provenance)

    def test_expected_evidence_must_reference_an_observed_region(self) -> None:
        record = self.records()[0]
        expected = {**record["expected_output"], "evidence_refs": ["missing-ref"]}
        with self.assertRaisesRegex(
            contract.MM005ProtocolError, "EXPECTED_EVIDENCE_REF_MISSING"
        ):
            self.rebuild(record, expected_output=expected)

    def test_multi_page_record_is_rejected(self) -> None:
        record = self.records()[0]
        observation = {**record["observation"], "page_count": 2}
        with self.assertRaisesRegex(
            contract.MM005ProtocolError, "SINGLE_PAGE_SCOPE_VIOLATION"
        ):
            self.rebuild(record, observation=observation)

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
            '{"answer":"x","answer":"y","evidence_refs":["evidence-1"],"page_number":1}',
            '{"answer":"x","evidence_refs":["evidence-1"],"page_number":1,"extra":0}',
            "\ud800",
        ):
            invalid = contract.compile_candidate_output(invalid_raw)
            self.assertFalse(invalid["valid"])
            self.assertFalse(contract.verify_candidate(invalid, record)["joint_correct"])
        self.assertFalse(contract.verify_candidate({"valid": True}, record)["joint_correct"])

        forbidden_roots = {
            "httpx",
            "requests",
            "socket",
            "subprocess",
            "torch",
            "transformers",
            "urllib",
        }
        for relative in (
            "src/fullcycle_bridge/multimodal_environment_adaptation.py",
            "scripts/prepare_mm005_multimodal_environment_adaptation_protocol.py",
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


def _provenance() -> dict[str, Any]:
    return {
        "source": "deterministic_reviewed_synthetic_generation",
        "license": "repository_generated_synthetic",
        "synthetic_only": True,
        "real_content": False,
        "capture_adapter_used": False,
        "runtime_ocr_used": False,
        "model_output_has_execution_authority": False,
        "runtime_integration_authorized": False,
    }


if __name__ == "__main__":
    unittest.main()
