from __future__ import annotations

import ast
import copy
import json
import sys
import tempfile
import unittest
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, cast
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SRC))

from fullcycle_bridge import mm005_browser_research_data as data  # noqa: E402
from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_generation as contract,
)
from scripts import (  # noqa: E402
    prepare_mm005_browser_research_data_protocol as data_prepare,
)
from scripts import run_mm005_browser_research_generation as runner  # noqa: E402

PROTOCOL_FREEZE_COMMIT = "9739e2b86d8473d9b8e99ea32e541db6055e4523"
EVIDENCE_SHA256 = (
    "sha256:1c5a7898f9811171c963db95b13a4fd33427b7ec58a4058ab5d4f077110f7fea"
)


class MM005BrowserResearchGenerationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        (
            cls.data_payload,
            cls.data_protocol,
            cls.data_sources,
            cls.parent_receipt,
        ) = runner.data_protocol_context()
        cls.protocol = runner.expected_protocol(freeze_status="frozen")
        cls.protocol_payload = contract.artifact_json_bytes(cls.protocol)
        cls.sources = runner.source_receipts()
        cls.outputs = data_prepare.planned_output_payloads()
        cls.exclusions = cast(
            Mapping[str, Sequence[str]], data_prepare.exclusion_registry()
        )

    def test_protocol_is_frozen_deterministic_and_outcome_neutral(self) -> None:
        rebuilt = runner.expected_protocol(freeze_status="frozen")
        self.assertEqual(rebuilt, self.protocol)
        self.assertEqual(rebuilt["gate_id"], data.EXECUTION_GATE_ID)
        self.assertEqual(rebuilt["next_gate"], contract.EXECUTION_GATE_ID)
        self.assertEqual(rebuilt["execution_plan"]["internal_retry_limit"], 0)
        self.assertEqual(rebuilt["execution_plan"]["output_file_count"], 139)
        self.assertEqual(rebuilt["execution_plan"]["output_bytes"], 986_989)
        self.assertTrue(all(value is False for value in rebuilt["claims"].values()))

    def test_tracked_protocol_matches_current_sources(self) -> None:
        self.assertEqual(
            runner.prepare_protocol(freeze_status="frozen", check=True), 0
        )

    def test_protocol_binds_publication_sources_and_all_planned_outputs(self) -> None:
        self.assertEqual(len(self.protocol["source_receipts"]), 4)
        self.assertEqual(
            self.protocol["data_protocol_publication"],
            {
                "merge_commit": contract.DATA_PROTOCOL_MERGE_COMMIT,
                "generation_freeze_commit_must_descend_from_merge": True,
                "published_protocol_bytes_must_match_current": True,
            },
        )
        self.assertEqual(
            self.protocol["data_protocol"],
            {
                "path": contract.DATA_PROTOCOL_PATH,
                "bytes": len(self.data_payload),
                "sha256": contract.sha256_bytes(self.data_payload),
            },
        )
        self.assertEqual(
            self.protocol["planned_outputs"], self.data_protocol["planned_outputs"]
        )

    def test_protocol_claim_source_or_publication_tamper_fails_closed(self) -> None:
        for mutation in ("claim", "source", "publication"):
            tampered = copy.deepcopy(self.protocol)
            sources = copy.deepcopy(self.sources)
            if mutation == "claim":
                tampered["claims"]["dataset_validated"] = True
            elif mutation == "source":
                next(iter(sources.values()))["bytes"] += 1
            else:
                tampered["data_protocol_publication"]["merge_commit"] = "a" * 40
            with self.assertRaisesRegex(
                contract.MM005BrowserResearchGenerationError,
                "GENERATION_PROTOCOL_MISMATCH",
            ):
                contract.validate_protocol(
                    tampered,
                    source_receipts=sources,
                    data_protocol_payload=self.data_payload,
                )

    def test_actual_outputs_validate_exact_receipts_and_semantics(self) -> None:
        summary = contract.validate_output_payloads(
            self.outputs,
            protocol=self.protocol,
            data_protocol=self.data_protocol,
            exclusions=self.exclusions,
        )
        self.assertEqual(
            summary.to_dict(),
            {
                "protocol_version": 1,
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
                "generation_executed": True,
                "records_generated": True,
                "source_snapshots_generated": True,
                "screenshots_generated": True,
                "dataset_validated": True,
                "next_gate": contract.NEXT_GATE,
            },
        )

    def test_single_byte_screenshot_drift_fails_closed(self) -> None:
        tampered = dict(self.outputs)
        path = next(name for name in tampered if name.endswith(".png"))
        payload = tampered[path]
        tampered[path] = payload[:-1] + bytes([payload[-1] ^ 1])
        with self.assertRaisesRegex(
            contract.MM005BrowserResearchGenerationError,
            "ACTUAL_OUTPUT_RECEIPT_MISMATCH",
        ):
            contract.validate_output_payloads(
                tampered,
                protocol=self.protocol,
                data_protocol=self.data_protocol,
                exclusions=self.exclusions,
            )

    def test_missing_or_extra_output_fails_closed(self) -> None:
        missing = dict(self.outputs)
        missing.pop(next(iter(missing)))
        extra = {**self.outputs, f"{contract.OUTPUT_ROOT}/extra.json": b"{}"}
        for payloads in (missing, extra):
            with self.assertRaisesRegex(
                contract.MM005BrowserResearchGenerationError,
                "ACTUAL_OUTPUT_RECEIPT_MISMATCH",
            ):
                contract.validate_output_payloads(
                    payloads,
                    protocol=self.protocol,
                    data_protocol=self.data_protocol,
                    exclusions=self.exclusions,
                )

    def test_evidence_binds_freeze_commit_outputs_and_narrow_claims(self) -> None:
        evidence = self._build_evidence()
        summary = contract.validate_evidence(
            evidence,
            protocol_freeze_commit="a" * 40,
            protocol_payload=self.protocol_payload,
            source_receipts=self.sources,
            data_protocol_payload=self.data_payload,
            data_source_receipts=self.data_sources,
            parent_protocol_receipt=self.parent_receipt,
            output_payloads=self.outputs,
            exclusions=self.exclusions,
        )
        self.assertTrue(summary.dataset_validated)
        self.assertEqual(
            evidence["data_protocol_merge_commit"],
            contract.DATA_PROTOCOL_MERGE_COMMIT,
        )
        self.assertTrue(evidence["claims"]["generation_executed"])
        self.assertTrue(evidence["claims"]["source_snapshots_generated"])
        self.assertTrue(evidence["claims"]["screenshots_generated"])
        self.assertFalse(evidence["claims"]["live_browser_used"])
        self.assertFalse(evidence["claims"]["network_accessed"])
        self.assertFalse(evidence["claims"]["model_evaluated"])
        self.assertFalse(evidence["claims"]["runtime_eligible"])

    def test_evidence_tamper_fails_after_reseal_attempt(self) -> None:
        evidence = self._build_evidence()
        evidence["claims"]["safety_established"] = True
        with self.assertRaisesRegex(
            contract.MM005BrowserResearchGenerationError, "EVIDENCE_MISMATCH"
        ):
            contract.validate_evidence(
                evidence,
                protocol_freeze_commit="a" * 40,
                protocol_payload=self.protocol_payload,
                source_receipts=self.sources,
                data_protocol_payload=self.data_payload,
                data_source_receipts=self.data_sources,
                parent_protocol_receipt=self.parent_receipt,
                output_payloads=self.outputs,
                exclusions=self.exclusions,
            )

    def test_materialization_is_atomic_exclusive_and_exact(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            temp_root = Path(temp_directory)
            (temp_root / "fixtures").mkdir()
            with mock.patch.object(runner, "ROOT", temp_root):
                runner._materialize_output_root(self.outputs)
                loaded = runner._load_output_tree(set(self.outputs))
                self.assertEqual(loaded, self.outputs)
                with self.assertRaises(FileExistsError):
                    runner._materialize_output_root(self.outputs)
                extra = temp_root / contract.OUTPUT_ROOT / "extra.json"
                extra.write_bytes(b"{}")
                with self.assertRaisesRegex(RuntimeError, "output tree mismatch"):
                    runner._load_output_tree(set(self.outputs))
                extra.unlink()
                (temp_root / contract.OUTPUT_ROOT / "empty-extra-directory").mkdir()
                with self.assertRaisesRegex(RuntimeError, "output tree mismatch"):
                    runner._load_output_tree(set(self.outputs))

    def test_materialization_rejects_path_escape_and_cleans_staging(self) -> None:
        malicious = {f"{contract.OUTPUT_ROOT}/../escape.json": b"{}"}
        with tempfile.TemporaryDirectory() as temp_directory:
            temp_root = Path(temp_directory)
            (temp_root / "fixtures").mkdir()
            with mock.patch.object(runner, "ROOT", temp_root):
                with self.assertRaisesRegex(RuntimeError, "unsafe output path"):
                    runner._materialize_output_root(malicious)
                self.assertFalse((temp_root / "fixtures" / "escape.json").exists())
                self.assertEqual(list((temp_root / "fixtures").iterdir()), [])

    def test_evidence_write_is_atomic_and_exclusive(self) -> None:
        payload = contract.artifact_json_bytes(self._build_evidence())
        with tempfile.TemporaryDirectory() as temp_directory:
            temp_root = Path(temp_directory)
            with mock.patch.object(runner, "ROOT", temp_root):
                runner._write_evidence_atomically(payload)
                self.assertEqual(
                    (temp_root / contract.EVIDENCE_PATH).read_bytes(), payload
                )
                with self.assertRaises(FileExistsError):
                    runner._write_evidence_atomically(payload)

    def test_formal_execution_requires_aligned_merged_master(self) -> None:
        with mock.patch.object(
            runner,
            "_git",
            side_effect=("feature", "a" * 40, "a" * 40),
        ):
            with self.assertRaisesRegex(RuntimeError, "aligned merged master"):
                runner._validate_freeze_commit("a" * 40)

    def test_formal_execution_requires_published_data_ancestor(self) -> None:
        with (
            mock.patch.object(
                runner,
                "_git",
                side_effect=("master", "a" * 40, "a" * 40),
            ),
            mock.patch.object(runner, "_git_is_ancestor", return_value=False),
        ):
            with self.assertRaisesRegex(RuntimeError, "not an ancestor"):
                runner._validate_freeze_commit("a" * 40)

    def test_invalid_freeze_commit_fails_before_evidence(self) -> None:
        with self.assertRaisesRegex(
            contract.MM005BrowserResearchGenerationError, "FREEZE_COMMIT_INVALID"
        ):
            contract.build_evidence(
                protocol_freeze_commit="A" * 40,
                protocol_payload=self.protocol_payload,
                source_receipts=self.sources,
                data_protocol_payload=self.data_payload,
                data_source_receipts=self.data_sources,
                parent_protocol_receipt=self.parent_receipt,
                output_payloads=self.outputs,
                exclusions=self.exclusions,
            )

    def test_tracked_execution_artifacts_rebuild_exactly(self) -> None:
        tracked_outputs = runner.load_tracked_outputs()
        self.assertEqual(tracked_outputs, self.outputs)
        evidence_payload = (ROOT / contract.EVIDENCE_PATH).read_bytes()
        evidence = json.loads(evidence_payload)
        self.assertEqual(contract.artifact_json_bytes(evidence), evidence_payload)
        self.assertEqual(contract.sha256_bytes(evidence_payload), EVIDENCE_SHA256)
        summary = contract.validate_evidence(
            evidence,
            protocol_freeze_commit=PROTOCOL_FREEZE_COMMIT,
            protocol_payload=self.protocol_payload,
            source_receipts=self.sources,
            data_protocol_payload=self.data_payload,
            data_source_receipts=self.data_sources,
            parent_protocol_receipt=self.parent_receipt,
            output_payloads=tracked_outputs,
            exclusions=self.exclusions,
        )
        self.assertEqual(summary.output_file_count, 139)
        self.assertEqual(summary.output_bytes, 986_989)
        self.assertTrue(summary.generation_executed)
        self.assertTrue(summary.dataset_validated)
        self.assertEqual(evidence["protocol_freeze_commit"], PROTOCOL_FREEZE_COMMIT)
        self.assertTrue(evidence["claims"]["source_snapshots_generated"])
        self.assertTrue(evidence["claims"]["screenshots_generated"])
        self.assertFalse(evidence["claims"]["environment_adapter_implemented"])
        self.assertFalse(evidence["claims"]["verifier_executed"])
        self.assertFalse(evidence["claims"]["model_evaluated"])
        self.assertFalse(evidence["claims"]["quality_improved"])
        self.assertFalse(evidence["claims"]["runtime_eligible"])

    def test_generation_scope_has_no_model_browser_or_network_imports(self) -> None:
        forbidden = {
            "torch",
            "transformers",
            "peft",
            "requests",
            "socket",
            "urllib",
            "selenium",
            "playwright",
        }
        for relative in (
            "src/fullcycle_bridge/mm005_browser_research_generation.py",
            "scripts/run_mm005_browser_research_generation.py",
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

    def _build_evidence(self) -> dict[str, Any]:
        return contract.build_evidence(
            protocol_freeze_commit="a" * 40,
            protocol_payload=self.protocol_payload,
            source_receipts=self.sources,
            data_protocol_payload=self.data_payload,
            data_source_receipts=self.data_sources,
            parent_protocol_receipt=self.parent_receipt,
            output_payloads=self.outputs,
            exclusions=self.exclusions,
        )


if __name__ == "__main__":
    unittest.main()
