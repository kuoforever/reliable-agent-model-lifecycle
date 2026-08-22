from __future__ import annotations

import ast
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SRC))

from fullcycle_bridge import mm004_hard_negative_generation as contract  # noqa: E402
from scripts import run_mm004_hard_negative_generation as runner  # noqa: E402


class MM004HardNegativeGenerationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.preregistration = runner.expected_preregistration(freeze_status="frozen")
        cls.preregistration_payload = contract.artifact_json_bytes(cls.preregistration)
        cls.parent_protocol = json.loads(
            (ROOT / contract.PARENT_PROTOCOL_PATH).read_text(encoding="utf-8")
        )
        cls.exclusions = cls.parent_protocol["exclusion_registry"]
        cls.outputs = contract.expected_output_payloads(
            cls.preregistration["parent_protocol"]["sha256"]
        )

    def test_preregistration_is_frozen_deterministic_and_outcome_neutral(self) -> None:
        rebuilt = runner.expected_preregistration(freeze_status="frozen")
        self.assertEqual(rebuilt, self.preregistration)
        self.assertTrue(all(value is False for value in rebuilt["claims"].values()))
        self.assertEqual(rebuilt["generation_plan"]["seed"], 44_004)
        self.assertEqual(rebuilt["generation_plan"]["record_count"], 56)
        self.assertEqual(len(rebuilt["planned_outputs"]), 31)

    def test_preregistration_source_or_claim_tamper_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.preregistration)
        tampered["claims"]["records_generated"] = True
        with self.assertRaisesRegex(
            contract.MM004GenerationError, "PREREGISTRATION_MISMATCH"
        ):
            contract.validate_preregistration(
                tampered,
                source_receipts=runner.source_receipts(),
                parent_protocol_receipt=runner.parent_protocol_receipt(),
            )

    def test_tracked_preregistration_matches_current_sources(self) -> None:
        self.assertEqual(runner.prepare_protocol(freeze_status="frozen", check=True), 0)

    def test_outputs_validate_exact_counts_distribution_and_splits(self) -> None:
        summary = contract.validate_output_payloads(
            self.outputs,
            preregistration=self.preregistration,
            exclusions=self.exclusions,
        )
        self.assertEqual(
            summary.to_dict(),
            {
                "family_count": 28,
                "pair_count": 28,
                "record_count": 56,
                "image_count": 28,
                "train_records": 42,
                "validation_records": 14,
                "category_count": 7,
                "generation_executed": True,
                "dataset_validated": True,
                "next_gate": contract.NEXT_GATE,
            },
        )

    def test_every_category_has_semantic_clean_negative_pairs(self) -> None:
        records = contract.expected_records(contract.expected_images())
        by_pair: dict[str, list[dict[str, Any]]] = {}
        for record in records:
            by_pair.setdefault(record["pair_id"], []).append(record)
        self.assertEqual(len(by_pair), 28)
        self.assertEqual(
            {record["category_id"] for record in records},
            set(contract.parent.CATEGORY_IDS),
        )
        for pair in by_pair.values():
            clean = next(record for record in pair if record["variant"] == "clean")
            negative = next(
                record for record in pair if record["variant"] == "hard_negative"
            )
            self.assertEqual(clean["verifier"]["verdict"], "accept")
            self.assertEqual(negative["verifier"]["verdict"], "reject")
            self.assertNotEqual(clean["candidate_action"], negative["candidate_action"])

    def test_all_images_are_unique_valid_pngs_and_split_disjoint(self) -> None:
        images = contract.expected_images()
        self.assertEqual(len(images), 28)
        self.assertEqual(len(set(images.values())), 28)
        self.assertTrue(all(payload.startswith(b"\x89PNG\r\n\x1a\n") for payload in images.values()))
        train_hashes = {
            contract.sha256_bytes(payload)
            for path, payload in images.items()
            if "/train/" in path
        }
        validation_hashes = {
            contract.sha256_bytes(payload)
            for path, payload in images.items()
            if "/validation/" in path
        }
        self.assertFalse(train_hashes & validation_hashes)

    def test_single_byte_output_drift_fails_closed(self) -> None:
        tampered = dict(self.outputs)
        image_path = next(path for path in tampered if path.endswith(".png"))
        payload = tampered[image_path]
        tampered[image_path] = payload[:-1] + bytes([payload[-1] ^ 1])
        with self.assertRaisesRegex(contract.MM004GenerationError, "OUTPUT_PAYLOAD_MISMATCH"):
            contract.validate_output_payloads(
                tampered,
                preregistration=self.preregistration,
                exclusions=self.exclusions,
            )

    def test_evidence_binds_freeze_commit_outputs_and_narrow_claims(self) -> None:
        evidence = contract.build_evidence(
            protocol_freeze_commit="a" * 40,
            preregistration_payload=self.preregistration_payload,
            output_payloads=self.outputs,
            exclusions=self.exclusions,
        )
        summary = contract.validate_evidence(
            evidence,
            protocol_freeze_commit="a" * 40,
            preregistration_payload=self.preregistration_payload,
            output_payloads=self.outputs,
            exclusions=self.exclusions,
        )
        self.assertTrue(summary.dataset_validated)
        self.assertTrue(evidence["claims"]["records_generated"])
        self.assertFalse(evidence["claims"]["verifier_evaluated"])
        self.assertFalse(evidence["claims"]["safety_established"])
        self.assertFalse(evidence["claims"]["runtime_eligible"])

    def test_evidence_tamper_fails_after_reseal_attempt(self) -> None:
        evidence = contract.build_evidence(
            protocol_freeze_commit="a" * 40,
            preregistration_payload=self.preregistration_payload,
            output_payloads=self.outputs,
            exclusions=self.exclusions,
        )
        evidence["claims"]["safety_established"] = True
        with self.assertRaisesRegex(contract.MM004GenerationError, "EVIDENCE_MISMATCH"):
            contract.validate_evidence(
                evidence,
                protocol_freeze_commit="a" * 40,
                preregistration_payload=self.preregistration_payload,
                output_payloads=self.outputs,
                exclusions=self.exclusions,
            )

    def test_materialization_is_atomic_and_exclusive(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            temp_root = Path(temp_directory)
            (temp_root / "fixtures").mkdir()
            with mock.patch.object(runner, "ROOT", temp_root):
                runner._materialize_output_root(dict(self.outputs))
                self.assertEqual(
                    (temp_root / contract.MANIFEST_PATH).read_bytes(),
                    self.outputs[contract.MANIFEST_PATH],
                )
                with self.assertRaises(FileExistsError):
                    runner._materialize_output_root(dict(self.outputs))

    def test_formal_execution_requires_aligned_merged_master(self) -> None:
        with mock.patch.object(
            runner,
            "_git",
            side_effect=("feature", "a" * 40, "a" * 40),
        ):
            with self.assertRaisesRegex(RuntimeError, "aligned merged master"):
                runner._validate_freeze_commit("a" * 40)

    def test_generation_contract_has_no_model_or_network_imports(self) -> None:
        tree = ast.parse(
            (SRC / "fullcycle_bridge/mm004_hard_negative_generation.py").read_text(
                encoding="utf-8"
            )
        )
        roots = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        self.assertFalse(
            roots & {"torch", "transformers", "peft", "requests", "socket", "urllib"}
        )


if __name__ == "__main__":
    unittest.main()
