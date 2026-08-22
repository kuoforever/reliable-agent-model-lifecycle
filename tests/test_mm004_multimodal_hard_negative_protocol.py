from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SRC))

from fullcycle_bridge import multimodal_hard_negative as contract  # noqa: E402
from scripts import (  # noqa: E402
    prepare_mm004_multimodal_hard_negative_protocol as prepare,
)


class MM004HardNegativeProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.receipts = prepare.source_receipts()
        cls.exclusions = prepare.exclusion_registry()
        cls.protocol = prepare.build_protocol()

    def records(self) -> list[dict[str, Any]]:
        records = []
        for index, category_id in enumerate(contract.CATEGORY_IDS):
            split = "train" if index < 4 else "validation"
            instruction = f"Review synthetic hard-negative family {index + 1}."
            for variant in ("clean", "hard_negative"):
                negative = variant == "hard_negative"
                records.append(
                    contract.build_record(
                        split=split,
                        variant=variant,
                        category_id=category_id,
                        instruction=instruction,
                        observation={
                            "family": category_id,
                            "state": "contradictory" if negative else "consistent",
                            "image_sha256": [],
                        },
                        candidate_action={
                            "family": category_id,
                            "disposition": "act" if negative else "reject",
                            "tool": "click" if negative else None,
                        },
                        verifier={
                            "verdict": "reject" if negative else "accept",
                            "reason_code": category_id,
                            "evidence_refs": ["observation.state"],
                        },
                        provenance=_provenance(),
                    )
                )
        return records

    def test_frozen_protocol_rebuilds_exactly_and_claims_remain_false(self) -> None:
        summary = contract.validate_protocol(
            self.protocol,
            source_receipts=self.receipts,
            exclusions=self.exclusions,
        )
        self.assertEqual(summary.category_count, 7)
        self.assertTrue(summary.protocol_frozen)
        self.assertFalse(summary.records_generated)
        self.assertTrue(all(value is False for value in self.protocol["claims"].values()))
        self.assertEqual(
            len(
                [
                    receipt
                    for receipt in self.receipts.values()
                    if receipt["path"].endswith(".png")
                ]
            ),
            24,
        )

    def test_protocol_tamper_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.protocol)
        tampered["claims"]["model_trained"] = True
        with self.assertRaisesRegex(contract.MM004ProtocolError, "PROTOCOL_MISMATCH"):
            contract.validate_protocol(
                tampered,
                source_receipts=self.receipts,
                exclusions=self.exclusions,
            )

    def test_valid_pairs_cover_all_categories_and_both_splits(self) -> None:
        summary = contract.validate_records(self.records(), self.exclusions)
        self.assertEqual(
            summary,
            {"record_count": 14, "pair_count": 7, "category_count": 7, "splits": ["train", "validation"]},
        )

    def test_record_builder_is_deterministic(self) -> None:
        left = self.records()[0]
        right = self.records()[0]
        self.assertEqual(left, right)
        self.assertEqual(left["record_id"], contract.identity("record", {k: v for k, v in left.items() if k != "record_id"}))

    def test_record_tamper_is_detected(self) -> None:
        records = self.records()
        records[0]["candidate_action"]["tool"] = "type_text"
        with self.assertRaisesRegex(contract.MM004ProtocolError, "IDENTITY_MISMATCH"):
            contract.validate_records(records, self.exclusions)

    def test_pair_cannot_cross_splits(self) -> None:
        records = self.records()
        original = records[1]
        records[1] = contract.build_record(
            split="validation",
            variant="hard_negative",
            category_id=original["category_id"],
            instruction=original["instruction"],
            observation=original["observation"],
            candidate_action=original["candidate_action"],
            verifier=original["verifier"],
            provenance=original["provenance"],
        )
        with self.assertRaisesRegex(contract.MM004ProtocolError, "PAIR_BINDING_MISMATCH"):
            contract.validate_records(records, self.exclusions)

    def test_missing_category_pair_is_rejected(self) -> None:
        with self.assertRaisesRegex(contract.MM004ProtocolError, "INCOMPLETE_CATEGORY_COVERAGE"):
            contract.validate_records(self.records()[:-2], self.exclusions)

    def test_upstream_instruction_collision_is_rejected(self) -> None:
        records = self.records()
        upstream_instruction = prepare._load_json(
            ROOT / "fixtures/gui_grounding_eval_v1/valid/suite.json"
        )["cases"][0]["model_input"]["instruction"]
        for offset, variant in enumerate(("clean", "hard_negative")):
            old = records[offset]
            records[offset] = contract.build_record(
                split=old["split"],
                variant=variant,
                category_id=old["category_id"],
                instruction=upstream_instruction,
                observation=old["observation"],
                candidate_action=old["candidate_action"],
                verifier=old["verifier"],
                provenance=old["provenance"],
            )
        with self.assertRaisesRegex(contract.MM004ProtocolError, "UPSTREAM_EXCLUSION_COLLISION"):
            contract.validate_records(records, self.exclusions)

    def test_verifier_evidence_is_required(self) -> None:
        records = self.records()
        old = records[0]
        records[0] = contract.build_record(
            split=old["split"],
            variant=old["variant"],
            category_id=old["category_id"],
            instruction=old["instruction"],
            observation=old["observation"],
            candidate_action=old["candidate_action"],
            verifier={**old["verifier"], "evidence_refs": []},
            provenance=old["provenance"],
        )
        with self.assertRaisesRegex(contract.MM004ProtocolError, "VERIFIER_EVIDENCE_MISSING"):
            contract.validate_records(records, self.exclusions)

    def test_identical_clean_and_negative_is_not_a_hard_negative(self) -> None:
        records = self.records()
        clean = records[0]
        records[1] = contract.build_record(
            split=clean["split"],
            variant="hard_negative",
            category_id=clean["category_id"],
            instruction=clean["instruction"],
            observation=clean["observation"],
            candidate_action=clean["candidate_action"],
            verifier={**clean["verifier"], "verdict": "reject"},
            provenance=clean["provenance"],
        )
        with self.assertRaisesRegex(contract.MM004ProtocolError, "NEGATIVE_MUTATION_MISSING"):
            contract.validate_records(records, self.exclusions)


def _provenance() -> dict[str, Any]:
    return {
        "source": "deterministic_reviewed_synthetic_generation",
        "synthetic_only": True,
        "real_content": False,
        "capture_adapter_used": False,
        "model_output_has_execution_authority": False,
        "runtime_dispatch_required": True,
    }


if __name__ == "__main__":
    unittest.main()
