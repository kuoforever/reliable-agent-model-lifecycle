from __future__ import annotations

import ast
import copy
import json
import struct
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SRC))

from fullcycle_bridge import mm005_document_chart_pdf_data as contract  # noqa: E402
from fullcycle_bridge import (  # noqa: E402
    multimodal_environment_adaptation as parent,
)
from scripts import (  # noqa: E402
    prepare_mm005_document_chart_pdf_data_protocol as prepare,
)


class MM005DocumentChartPdfDataProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sources = prepare.source_receipts()
        cls.parent_receipt = prepare.parent_protocol_receipt()
        cls.parent_protocol = prepare.parent_prepare.build_protocol()
        cls.exclusions = cls.parent_protocol["exclusion_registry"]
        cls.preregistration = prepare.build_protocol()
        cls.payload = contract.artifact_json_bytes(cls.preregistration)
        cls.outputs = prepare.planned_output_payloads()
        cls.images = {
            path: payload
            for path, payload in cls.outputs.items()
            if path.endswith(".png")
        }
        cls.records = contract.expected_records(cls.images)

    def test_tracked_preregistration_rebuilds_exactly_and_claims_stay_false(
        self,
    ) -> None:
        tracked = (ROOT / contract.PREREGISTRATION_PATH).read_bytes()
        parsed = json.loads(tracked)
        summary = contract.validate_preregistration(
            parsed,
            source_receipts=self.sources,
            parent_protocol_receipt=self.parent_receipt,
        )
        self.assertEqual(tracked, self.payload)
        self.assertEqual(parsed, self.preregistration)
        self.assertEqual(summary.template_count, 32)
        self.assertEqual(summary.record_count, 32)
        self.assertEqual(summary.image_count, 32)
        self.assertEqual(summary.source_artifact_count, 14)
        self.assertEqual(summary.output_file_count, 49)
        self.assertEqual(summary.output_bytes, 434_212)
        self.assertFalse(summary.generation_executed)
        self.assertFalse(summary.dataset_validated)
        self.assertTrue(all(value is False for value in parsed["claims"].values()))

    def test_parent_and_source_receipts_are_closed_and_exact(self) -> None:
        self.assertEqual(len(self.sources), 5)
        self.assertEqual(
            self.parent_receipt,
            {
                "path": contract.PARENT_PROTOCOL_PATH,
                "bytes": 49_202,
                "sha256": (
                    "sha256:311822603bb6c05c1b7f388cd782c30556fa8b7aa0d67cbd1ccd89f9d13a532a"
                ),
            },
        )
        for receipt in self.sources.values():
            payload = (ROOT / receipt["path"]).read_bytes()
            self.assertEqual(receipt["bytes"], len(payload))
            self.assertEqual(receipt["sha256"], contract.sha256_bytes(payload))

    def test_template_grid_is_unique_balanced_and_compatible(self) -> None:
        templates = contract.expected_templates()
        self.assertEqual(len(templates), 32)
        self.assertEqual(len({item["template_id"] for item in templates}), 32)
        self.assertEqual(len({item["content_seed"] for item in templates}), 32)
        self.assertEqual(
            Counter((item["task_family_id"], item["split"]) for item in templates),
            Counter(
                {
                    (task, "train"): 6
                    for task in parent.TASK_FAMILY_IDS
                }
                | {
                    (task, "validation"): 2
                    for task in parent.TASK_FAMILY_IDS
                }
            ),
        )
        compatibility = self.preregistration["generation_plan"]["template_registry"]
        self.assertEqual(templates, compatibility)
        self.assertEqual(
            {item["source_kind"] for item in templates}, set(parent.SOURCE_KINDS)
        )

    def test_planned_outputs_rebuild_and_validate_without_filesystem_writes(
        self,
    ) -> None:
        summary = contract.validate_planned_output_payloads(
            self.outputs,
            parent_protocol_sha256=self.parent_receipt["sha256"],
            exclusions=self.exclusions,
        )
        self.assertEqual(
            summary,
            {
                "planned_output_rebuild_valid": True,
                "template_count": 32,
                "record_count": 32,
                "image_count": 32,
                "source_artifact_count": 14,
                "train_records": 24,
                "validation_records": 8,
                "output_file_count": 49,
                "output_bytes": 434_212,
                "generation_executed": False,
                "dataset_validated": False,
                "next_gate": contract.NEXT_GATE,
            },
        )
        prepare.assert_fixed_outputs_absent()

    def test_every_planned_output_receipt_binds_exact_bytes(self) -> None:
        receipts = self.preregistration["planned_outputs"]
        self.assertEqual(set(receipts), set(self.outputs))
        self.assertEqual(len(receipts), 49)
        for path, payload in self.outputs.items():
            self.assertEqual(
                receipts[path],
                {
                    "path": path,
                    "bytes": len(payload),
                    "sha256": contract.sha256_bytes(payload),
                },
            )

    def test_planned_images_are_unique_fixed_pngs_and_split_disjoint(self) -> None:
        self.assertEqual(len(self.images), 32)
        self.assertEqual(len(set(self.images.values())), 32)
        for payload in self.images.values():
            self.assertTrue(payload.startswith(b"\x89PNG\r\n\x1a\n"))
            self.assertEqual(struct.unpack(">II", payload[16:24]), (1280, 900))
        train = {
            contract.sha256_bytes(payload)
            for path, payload in self.images.items()
            if "/images/train/" in path
        }
        validation = {
            contract.sha256_bytes(payload)
            for path, payload in self.images.items()
            if "/images/validation/" in path
        }
        self.assertEqual(len(train), 24)
        self.assertEqual(len(validation), 8)
        self.assertFalse(train & validation)
        pdfs = {
            path: payload
            for path, payload in self.outputs.items()
            if path.endswith(".pdf")
        }
        self.assertEqual(len(pdfs), 14)
        self.assertEqual(len(set(pdfs.values())), 14)
        for path, payload in pdfs.items():
            self.assertTrue(payload.startswith(b"%PDF-1.4\n"), path)
            self.assertTrue(payload.endswith(b"%%EOF\n"), path)
            self.assertEqual(payload.count(b"/Type /Page "), 1, path)

    def test_records_pass_parent_contract_and_all_prior_exclusions(self) -> None:
        self.assertEqual(
            parent.validate_records(self.records, self.exclusions),
            {
                "record_count": 32,
                "family_count": 32,
                "task_family_count": 4,
                "source_kind_count": 4,
                "splits": ["train", "validation"],
            },
        )

    def test_answers_are_bound_to_visible_evidence_or_selected_region(self) -> None:
        for record in self.records:
            expected = record["expected_output"]
            region_by_ref = {
                region["ref"]: region for region in record["observation"]["regions"]
            }
            refs = expected["evidence_refs"]
            if record["task_family_id"] == "page_region_selection":
                self.assertIn(expected["answer"], refs)
            else:
                visible = " ".join(
                    region_by_ref[ref]["visible_text"] or "" for ref in refs
                )
                self.assertIn(expected["answer"], visible)

    def test_all_split_identity_classes_are_disjoint(self) -> None:
        keys = (
            "family_id",
            "template_id",
            "instruction_content_sha256",
            "observation_content_sha256",
            "target_content_sha256",
            "image_sha256",
        )
        values: dict[str, dict[str, set[str]]] = {
            split: {key: set() for key in keys} for split in ("train", "validation")
        }
        for record in self.records:
            split = record["split"]
            values[split]["family_id"].add(record["family_id"])
            values[split]["template_id"].add(record["template_id"])
            for key in keys[2:5]:
                values[split][key].add(record["identities"][key])
            values[split]["image_sha256"].update(
                record["identities"]["image_sha256"]
            )
        for key in keys:
            self.assertFalse(values["train"][key] & values["validation"][key])

    def test_preregistration_tamper_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.preregistration)
        tampered["claims"]["records_generated"] = True
        with self.assertRaisesRegex(
            contract.MM005DataProtocolError, "PREREGISTRATION_MISMATCH"
        ):
            contract.validate_preregistration(
                tampered,
                source_receipts=self.sources,
                parent_protocol_receipt=self.parent_receipt,
            )

    def test_parent_or_source_receipt_tamper_fails_closed(self) -> None:
        parent_receipt = dict(self.parent_receipt)
        parent_receipt["bytes"] += 1
        with self.assertRaisesRegex(
            contract.MM005DataProtocolError, "PREREGISTRATION_MISMATCH"
        ):
            contract.validate_preregistration(
                self.preregistration,
                source_receipts=self.sources,
                parent_protocol_receipt=parent_receipt,
            )

    def test_single_byte_planned_output_drift_fails_closed(self) -> None:
        tampered = dict(self.outputs)
        image_path = next(path for path in tampered if path.endswith(".png"))
        payload = tampered[image_path]
        tampered[image_path] = payload[:-1] + bytes([payload[-1] ^ 1])
        with self.assertRaisesRegex(
            contract.MM005DataProtocolError, "OUTPUT_PAYLOAD_MISMATCH"
        ):
            contract.validate_planned_output_payloads(
                tampered,
                parent_protocol_sha256=self.parent_receipt["sha256"],
                exclusions=self.exclusions,
            )

    def test_seeded_content_changes_across_every_template_family(self) -> None:
        expected_outputs = [record["expected_output"] for record in self.records]
        self.assertEqual(len({json.dumps(item, sort_keys=True) for item in expected_outputs}), 32)
        self.assertEqual(
            [item["content_seed"] for item in contract.expected_templates()],
            [
                contract.SEED + task_index * 100 + ordinal
                for task_index in range(1, 5)
                for ordinal in range(1, 9)
            ],
        )

    def test_protocol_scope_has_no_model_network_or_execution_imports(self) -> None:
        forbidden = {
            "httpx",
            "peft",
            "requests",
            "socket",
            "subprocess",
            "torch",
            "transformers",
            "urllib",
        }
        for relative in (
            "src/fullcycle_bridge/mm005_document_chart_pdf_data.py",
            "scripts/prepare_mm005_document_chart_pdf_data_protocol.py",
        ):
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
            self.assertTrue(forbidden.isdisjoint(roots))
        self.assertFalse(hasattr(contract, "materialize_outputs"))


if __name__ == "__main__":
    unittest.main()
