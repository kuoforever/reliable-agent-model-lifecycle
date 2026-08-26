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

from fullcycle_bridge import (  # noqa: E402
    browser_research_environment_adaptation as parent,
)
from fullcycle_bridge import mm005_browser_research_data as contract  # noqa: E402
from scripts import (  # noqa: E402
    prepare_mm005_browser_research_data_protocol as prepare,
)


class MM005BrowserResearchDataProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sources = prepare.source_receipts()
        cls.parent_receipt = prepare.parent_protocol_receipt()
        cls.parent_protocol = prepare.parent_protocol()
        cls.exclusions = prepare.exclusion_registry()
        cls.preregistration = prepare.build_protocol()
        cls.payload = contract.artifact_json_bytes(cls.preregistration)
        cls.outputs = prepare.planned_output_payloads()
        cls.screenshots = {
            path: payload
            for path, payload in cls.outputs.items()
            if path.endswith(".png")
        }
        cls.snapshots = {
            path: payload
            for path, payload in cls.outputs.items()
            if "/snapshots/" in path and path.endswith(".json")
        }
        cls.records = contract.expected_records(cls.screenshots)

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
        self.assertEqual(summary.source_count, 68)
        self.assertEqual(summary.screenshot_count, 68)
        self.assertEqual(summary.source_snapshot_count, 68)
        self.assertEqual(summary.train_sources, 51)
        self.assertEqual(summary.validation_sources, 17)
        self.assertEqual(summary.output_file_count, 139)
        self.assertEqual(summary.output_bytes, 986_989)
        self.assertFalse(summary.generation_executed)
        self.assertFalse(summary.dataset_validated)
        self.assertTrue(all(value is False for value in parsed["claims"].values()))

    def test_parent_and_source_receipts_are_closed_and_exact(self) -> None:
        self.assertEqual(len(self.sources), 5)
        self.assertEqual(
            self.parent_receipt,
            {
                "path": contract.PARENT_PROTOCOL_PATH,
                "bytes": 76_364,
                "sha256": (
                    "sha256:62ef6c554c90d3523b7d9c2a0a102c2a8c783f3d3ba3496cd8c36dfebe04b06e"
                ),
            },
        )
        self.assertEqual(
            self.parent_protocol["gate_id"],
            "MM-005-browser-research-environment-adaptation-protocol-v1",
        )
        for receipt in self.sources.values():
            payload = (ROOT / receipt["path"]).read_bytes()
            self.assertEqual(receipt["bytes"], len(payload))
            self.assertEqual(receipt["sha256"], contract.sha256_bytes(payload))

    def test_template_grid_is_unique_balanced_and_covers_one_to_three_sources(
        self,
    ) -> None:
        templates = contract.expected_templates()
        self.assertEqual(len(templates), 32)
        self.assertEqual(len({item["template_id"] for item in templates}), 32)
        self.assertEqual(len({item["content_seed"] for item in templates}), 32)
        self.assertEqual({item["source_count"] for item in templates}, {1, 2, 3})
        self.assertEqual(
            Counter((item["task_family_id"], item["split"]) for item in templates),
            Counter(
                {(task, "train"): 6 for task in parent.TASK_FAMILY_IDS}
                | {(task, "validation"): 2 for task in parent.TASK_FAMILY_IDS}
            ),
        )
        self.assertEqual(
            templates,
            self.preregistration["generation_plan"]["template_registry"],
        )
        self.assertEqual(
            [
                item["source_count"]
                for item in templates
                if item["task_family_id"] != "single_source_fact_citation"
            ],
            list(contract.MULTI_SOURCE_COUNTS) * 3,
        )

    def test_planned_outputs_rebuild_independently_of_downstream_execution_state(
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
                "source_count": 68,
                "screenshot_count": 68,
                "source_snapshot_count": 68,
                "train_records": 24,
                "validation_records": 8,
                "train_sources": 51,
                "validation_sources": 17,
                "output_file_count": 139,
                "output_bytes": 986_989,
                "generation_executed": False,
                "dataset_validated": False,
                "next_gate": contract.NEXT_GATE,
            },
        )

    def test_every_planned_output_receipt_binds_exact_bytes(self) -> None:
        receipts = self.preregistration["planned_outputs"]
        self.assertEqual(set(receipts), set(self.outputs))
        self.assertEqual(len(receipts), 139)
        for path, payload in self.outputs.items():
            self.assertEqual(
                receipts[path],
                {
                    "path": path,
                    "bytes": len(payload),
                    "sha256": contract.sha256_bytes(payload),
                },
            )

    def test_screenshots_are_unique_fixed_pngs_and_split_disjoint(self) -> None:
        self.assertEqual(len(self.screenshots), 68)
        self.assertEqual(len(set(self.screenshots.values())), 68)
        for payload in self.screenshots.values():
            self.assertTrue(payload.startswith(b"\x89PNG\r\n\x1a\n"))
            self.assertEqual(struct.unpack(">II", payload[16:24]), (1280, 900))
        train = {
            contract.sha256_bytes(payload)
            for path, payload in self.screenshots.items()
            if "/screenshots/train/" in path
        }
        validation = {
            contract.sha256_bytes(payload)
            for path, payload in self.screenshots.items()
            if "/screenshots/validation/" in path
        }
        self.assertEqual(len(train), 51)
        self.assertEqual(len(validation), 17)
        self.assertFalse(train & validation)

    def test_static_snapshots_bind_exact_record_sources_and_screenshots(self) -> None:
        self.assertEqual(len(self.snapshots), 68)
        self.assertEqual(len(set(self.snapshots.values())), 68)
        record_sources = {
            (record["template_id"], source["source_id"]): source
            for record in self.records
            for source in record["observation"]["sources"]
        }
        for path, payload in self.snapshots.items():
            artifact = json.loads(payload)
            self.assertEqual(contract.artifact_json_bytes(artifact), payload)
            source = artifact["source"]
            key = (artifact["template_id"], source["source_id"])
            self.assertEqual(source, record_sources[key])
            screenshot = self.screenshots[artifact["screenshot_path"]]
            self.assertEqual(
                source["screenshot_sha256"], contract.sha256_bytes(screenshot)
            )
            self.assertEqual(
                artifact["source_snapshot_identity_sha256"],
                parent.browser_identity("source_snapshot", source),
            )
            self.assertIn(f"/snapshots/{artifact['split']}/", path)

    def test_records_pass_parent_contract_and_all_prior_exclusions(self) -> None:
        self.assertEqual(
            parent.validate_records(self.records, self.exclusions),
            {
                "record_count": 32,
                "family_count": 32,
                "task_family_count": 4,
                "source_kind_count": 4,
                "source_snapshot_count": 68,
                "splits": ["train", "validation"],
            },
        )

    def test_dom_page_text_screenshot_and_citations_share_ground_truth(self) -> None:
        for record in self.records:
            ref_to_source: dict[str, str] = {}
            published: dict[str, str] = {}
            for source in record["observation"]["sources"]:
                self.assertEqual(
                    source["page_text"],
                    "\n".join(node["text"] for node in source["dom_nodes"]),
                )
                published[source["source_id"]] = source["published_at"]
                for node in source["dom_nodes"]:
                    ref_to_source[node["ref"]] = source["source_id"]
            refs = record["expected_output"]["citation_refs"]
            cited_sources = {ref_to_source[ref] for ref in refs}
            if record["task_family_id"] == "single_source_fact_citation":
                self.assertEqual(len(cited_sources), 1)
            else:
                self.assertGreaterEqual(len(cited_sources), 2)
            if record["task_family_id"] == "freshness_conflict_resolution":
                latest = max(published, key=published.__getitem__)
                self.assertIn(latest, cited_sources)

    def test_all_split_identity_classes_are_disjoint(self) -> None:
        keys = (
            "family_id",
            "template_id",
            "instruction_content_sha256",
            "observation_content_sha256",
            "target_content_sha256",
            "image_sha256",
            "source_url_sha256",
            "source_snapshot_sha256",
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
            for key in keys[5:]:
                values[split][key].update(record["identities"][key])
        for key in keys:
            self.assertFalse(values["train"][key] & values["validation"][key], key)

    def test_preregistration_parent_and_source_tamper_fail_closed(self) -> None:
        tampered = copy.deepcopy(self.preregistration)
        tampered["claims"]["records_generated"] = True
        with self.assertRaisesRegex(
            contract.MM005BrowserResearchDataProtocolError,
            "PREREGISTRATION_MISMATCH",
        ):
            contract.validate_preregistration(
                tampered,
                source_receipts=self.sources,
                parent_protocol_receipt=self.parent_receipt,
            )

        parent_receipt = dict(self.parent_receipt)
        parent_receipt["bytes"] += 1
        with self.assertRaisesRegex(
            contract.MM005BrowserResearchDataProtocolError,
            "PREREGISTRATION_MISMATCH",
        ):
            contract.validate_preregistration(
                self.preregistration,
                source_receipts=self.sources,
                parent_protocol_receipt=parent_receipt,
            )

        sources = copy.deepcopy(self.sources)
        sources["data_contract"]["sha256"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(
            contract.MM005BrowserResearchDataProtocolError,
            "PREREGISTRATION_MISMATCH",
        ):
            contract.validate_preregistration(
                self.preregistration,
                source_receipts=sources,
                parent_protocol_receipt=self.parent_receipt,
            )

    def test_output_byte_dom_and_prior_collision_tamper_fail_closed(self) -> None:
        tampered_outputs = dict(self.outputs)
        screenshot_path = next(
            path for path in tampered_outputs if path.endswith(".png")
        )
        payload = tampered_outputs[screenshot_path]
        tampered_outputs[screenshot_path] = payload[:-1] + bytes([payload[-1] ^ 1])
        with self.assertRaisesRegex(
            contract.MM005BrowserResearchDataProtocolError,
            "OUTPUT_PAYLOAD_MISMATCH",
        ):
            contract.validate_planned_output_payloads(
                tampered_outputs,
                parent_protocol_sha256=self.parent_receipt["sha256"],
                exclusions=self.exclusions,
            )

        records = copy.deepcopy(self.records)
        records[0]["observation"]["sources"][0]["page_text"] += " DRIFT"
        with self.assertRaisesRegex(
            parent.MM005BrowserResearchProtocolError, "PAGE_TEXT_DOM"
        ):
            parent.validate_records(records, self.exclusions)

        exclusions = copy.deepcopy(self.exclusions)
        exclusions["case_ids"] = sorted(
            [*exclusions["case_ids"], self.records[0]["record_id"]]
        )
        with self.assertRaisesRegex(
            parent.MM005BrowserResearchProtocolError,
            "PRIOR_EXCLUSION_COLLISION",
        ):
            parent.validate_records(self.records, exclusions)

    def test_seeded_content_and_output_paths_are_fully_registered(self) -> None:
        self.assertEqual(contract.SEED, 55_006)
        self.assertEqual(
            [item["content_seed"] for item in contract.expected_templates()],
            [
                contract.SEED + task_index * 100 + ordinal
                for task_index in range(1, 5)
                for ordinal in range(1, 9)
            ],
        )
        self.assertEqual(
            set(self.outputs), set(self.preregistration["planned_outputs"])
        )
        self.assertEqual(
            self.preregistration["freeze_preconditions"]["expected_absent_paths"],
            [contract.OUTPUT_ROOT, contract.EVIDENCE_PATH],
        )

    def test_protocol_scope_has_no_browser_model_network_or_execution_imports(
        self,
    ) -> None:
        forbidden = {
            "httpx",
            "peft",
            "playwright",
            "requests",
            "selenium",
            "socket",
            "subprocess",
            "torch",
            "transformers",
            "urllib",
        }
        for relative in (
            "src/fullcycle_bridge/mm005_browser_research_data.py",
            "scripts/prepare_mm005_browser_research_data_protocol.py",
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
