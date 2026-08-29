from __future__ import annotations

import ast
import copy
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

sys.path.insert(0, str(SRC))
sys.path.insert(0, str(ROOT))

from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_model_evaluation_failure_classification_v2 as failure,
)
from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_model_evaluation_generation_failure_investigation as contract,
)
from scripts import (  # noqa: E402
    prepare_mm005_browser_research_model_evaluation_generation_failure_investigation_protocol_v1 as builder,
)

PROTOCOL_PATH = ROOT / contract.PREREGISTRATION_PATH


class MM005BrowserResearchGenerationFailureInvestigationProtocolV1Tests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls) -> None:
        cls.protocol_payload = PROTOCOL_PATH.read_bytes()
        cls.protocol = contract.parse_strict_json_bytes(
            cls.protocol_payload, location="$.investigation_protocol"
        )
        cls.inputs = builder.protocol_inputs()

    def _validation_inputs(self) -> dict[str, object]:
        return {
            **copy.deepcopy(self.inputs),
            "freeze_status": "frozen",
            "output_absent": True,
        }

    def test_protocol_recomputes_exactly_and_builder_check_passes(self) -> None:
        recomputed = contract.expected_preregistration(**self._validation_inputs())
        self.assertEqual(recomputed, self.protocol)
        self.assertEqual(
            contract.artifact_json_bytes(recomputed), self.protocol_payload
        )
        self.assertEqual(
            contract.validate_preregistration(
                self.protocol, **self._validation_inputs()
            ),
            self.protocol,
        )
        self.assertEqual(builder.main(["--check"]), 0)

    def test_published_failure_lineage_is_exact_and_ancestor_bound(self) -> None:
        self.assertEqual(
            self.protocol["source_lineage"]["classification_merge_commit"],
            contract.CLASSIFICATION_MERGE_COMMIT,
        )
        builder._validate_published_classification_lineage()
        upstream = self.protocol["source_lineage"]["upstream_artifacts"]
        expected = {
            "v2_preregistration": (
                failure.PREREGISTRATION_BYTES,
                failure.PREREGISTRATION_SHA256,
            ),
            "attempt_owner": (
                failure.ATTEMPT_OWNER_BYTES,
                failure.ATTEMPT_OWNER_SHA256,
            ),
            "progress": (failure.PROGRESS_BYTES, failure.PROGRESS_SHA256),
            "failure": (failure.FAILURE_BYTES, failure.FAILURE_SHA256),
            "classification": (
                contract.CLASSIFICATION_BYTES,
                contract.CLASSIFICATION_SHA256,
            ),
        }
        for name, (byte_count, digest) in expected.items():
            self.assertEqual(upstream[name]["bytes"], byte_count)
            self.assertEqual(upstream[name]["sha256"], digest)

    def test_exact_fourth_record_and_static_artifacts_are_frozen(self) -> None:
        registry = self.protocol["static_investigation_plan"]["record_registry"]
        records = registry["records"]
        self.assertEqual(len(records), 7)
        target = records[0]
        self.assertEqual(target["record_id"], contract.TARGET_RECORD_ID)
        self.assertEqual(target["case_order_index"], 3)
        self.assertEqual(target["dataset_record_index"], 17)
        self.assertEqual(target["template_id"], "mm005-browser-cross-comparison-06")
        self.assertEqual(
            target["record"],
            {
                "bytes": 5630,
                "sha256": (
                    "sha256:3f1374169ef910194af3ec8423988a6f0edaccdaf38e750"
                    "0734b868c2882099c"
                ),
            },
        )
        self.assertEqual(
            target["adapter_audit_projection"]["sha256"],
            "sha256:ad48e91f1440dcc2bbbc196d0bdcd387e4dd8de76d2540d2590dde235c958406",
        )
        self.assertEqual(
            target["model_payload"]["sha256"],
            "sha256:1490af3bcf899b4cadaa141a3f1bd4d4c3e4fbb61b8f39911d4d04f0380864c3",
        )
        self.assertEqual(
            target["prompt_projection"]["sha256"],
            "sha256:266a804f7c155d3c7f8ef451c6bf756d9b99ea95a5fada90b518992d13808865",
        )
        self.assertEqual(
            [item["bytes"] for item in target["screenshot_payloads"]],
            [8849, 8826, 8850],
        )
        self.assertEqual(
            [item["bytes"] for item in target["source_snapshot_payloads"]],
            [1742, 1740, 1742],
        )
        for screenshot in target["screenshot_payloads"]:
            self.assertEqual(
                screenshot["png"],
                {
                    "width": 1280,
                    "height": 900,
                    "bit_depth": 8,
                    "color_type": 2,
                    "interlace": 0,
                },
            )

    def test_controls_are_preselected_and_same_shape_is_not_causality(self) -> None:
        registry = self.protocol["static_investigation_plan"]["record_registry"]
        records = registry["records"]
        self.assertEqual(
            [item["record_id"] for item in records[1:4]],
            list(contract.COMPLETED_PREFIX_CONTROL_IDS),
        )
        self.assertEqual(
            [item["record_id"] for item in records[4:]],
            list(contract.SAME_SHAPE_CONTROL_IDS),
        )
        target = records[0]
        for control in records[4:]:
            self.assertEqual(control["source_count"], target["source_count"])
            self.assertEqual(
                control["model_payload"]["bytes"], target["model_payload"]["bytes"]
            )
            self.assertEqual(
                control["prompt_projection"]["bytes"],
                target["prompt_projection"]["bytes"],
            )
        rubric = self.protocol["static_investigation_plan"]["decision_rubric"]
        self.assertTrue(rubric["static_difference_does_not_establish_causality"])
        self.assertTrue(
            rubric["static_pass_does_not_establish_historical_runtime_health"]
        )

    def test_runtime_messages_reconstruct_with_opaque_image_sentinels(self) -> None:
        records = self.protocol["static_investigation_plan"]["record_registry"][
            "records"
        ]
        for record in records:
            self.assertEqual(
                record["runtime_message_transport_projection"],
                record["prompt_projection"],
            )
            self.assertTrue(record["runtime_message_shape"]["opaque_sentinels_only"])
            self.assertEqual(
                record["runtime_message_shape"]["image_channels"],
                record["source_count"],
            )
            self.assertFalse(record["gold_or_verifier_fields_exposed"])
            self.assertFalse(record["real_file_path_exposed"])
            self.assertFalse(record["source_snapshots_exposed"])

    def test_checkpoint_boundary_matches_frozen_source_order(self) -> None:
        runner = (
            ROOT / "scripts/run_mm005_browser_research_model_evaluation_v2.py"
        ).read_text(encoding="utf-8")
        markers = (
            "adapted = adapter_verifier.adapt_record(",
            "images = [",
            '"generation_started", counters, completed_record_ids, record_id',
            "messages = v1_contract.build_runtime_messages(",
            "torch.cuda.synchronize()",
            "raw_output, generated_tokens = base_runner._generate_one(",
            "case = v1_contract.build_case_result(",
            '"generation_completed", counters, completed_record_ids, record_id',
        )
        loop_start = runner.index("for record in ordered:")
        positions = [runner.index(marker, loop_start) for marker in markers]
        self.assertEqual(positions, sorted(positions))

        base_runner = (
            ROOT / "scripts/run_mm003_multimodal_gui_action_baseline.py"
        ).read_text(encoding="utf-8")
        start = base_runner.index("def _generate_one(")
        end = base_runner.index("\ndef _load_ml_dependencies", start)
        body = base_runner[start:end]
        inner_markers = (
            "processor.apply_chat_template(",
            'processor(**kwargs).to("cuda")',
            "model.generate(",
            "processor.batch_decode(",
        )
        inner_positions = [body.index(marker) for marker in inner_markers]
        self.assertEqual(inner_positions, sorted(inner_positions))

        boundary = self.protocol["historical_control_flow_boundary"]
        self.assertEqual(
            boundary["durably_authenticated_through"],
            "generation_started_checkpoint_durably_persisted",
        )
        self.assertFalse(
            boundary["historical_root_cause_inferred_from_static_control_flow"]
        )
        self.assertIn(
            "model_generate",
            boundary["post_checkpoint_substages_not_individually_authenticated"],
        )

    def test_claims_and_authority_remain_fail_closed(self) -> None:
        claims = self.protocol["claims"]
        self.assertTrue(claims["investigation_protocol_frozen"])
        self.assertTrue(claims["v2_attempt_consumed"])
        for name in (
            "investigation_executed",
            "static_root_cause_reproduced",
            "failed_runtime_substage_isolated",
            "remediation_delta_established",
            "recovery_v3_justified",
            "diagnostic_model_or_cuda_execution_authorized",
            "formal_measurement_complete",
            "model_evaluated",
            "quality_established",
            "safety_established",
            "evaluation_repeatability_established",
            "resource_repeatability_established",
            "cross_machine_reproducibility_established",
            "serving_eligible",
            "promotion_eligible",
            "runtime_eligible",
        ):
            self.assertFalse(claims[name], name)
        authority = self.protocol["authority_contract"]
        for name in (
            "model_or_cuda_execution_authorized",
            "processor_execution_authorized",
            "live_browser_or_network_authorized",
            "capture_authorized",
            "v1_or_v2_retry_authorized",
            "recovery_v3_authorized",
            "runtime_repository_changed",
            "runtime_integration_changed",
            "runtime_policy_or_approval_bypass",
        ):
            self.assertFalse(authority[name], name)

    def test_only_static_investigation_is_next_and_diagnostic_is_conditional(
        self,
    ) -> None:
        self.assertEqual(self.protocol["next_gate"], contract.INVESTIGATION_GATE_ID)
        future = self.protocol["future_diagnostic_experiment_policy"]
        self.assertFalse(future["currently_justified"])
        self.assertFalse(future["execution_authorized"])
        self.assertIsNone(future["experiment_id"])
        self.assertIsNone(future["run_id"])
        self.assertIsNone(future["output_root"])
        self.assertTrue(future["new_identity_and_output_required"])
        self.assertTrue(future["separate_protocol_clean_merge_required"])
        self.assertEqual(
            self.protocol["static_investigation_contract"]["fixed_result_path"],
            contract.RESULT_PATH,
        )
        self.assertFalse(
            self.protocol["static_investigation_contract"][
                "implementation_source_frozen_by_this_protocol"
            ]
        )

    def test_raw_or_classification_payload_tamper_is_rejected(self) -> None:
        for name in (
            "v2_preregistration_payload",
            "attempt_owner_payload",
            "progress_payload",
            "failure_payload",
            "classification_payload",
        ):
            changed = self._validation_inputs()
            payload = changed[name]
            self.assertIsInstance(payload, bytes)
            assert isinstance(payload, bytes)
            changed[name] = payload[:-1] + b" "
            with (
                self.subTest(name=name),
                self.assertRaises(contract.MM005GenerationFailureInvestigationError),
            ):
                contract.expected_preregistration(**changed)

    def test_candidate_drift_and_bool_integer_aliases_are_rejected(self) -> None:
        for path, replacement in (
            (("claims", "investigation_executed"), 0),
            (("static_investigation_contract", "zero_internal_retry"), 1),
        ):
            changed = copy.deepcopy(self.protocol)
            target = changed
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = replacement
            self.assertEqual(changed, self.protocol)
            with (
                self.subTest(path=path),
                self.assertRaises(contract.MM005GenerationFailureInvestigationError),
            ):
                contract.validate_preregistration(changed, **self._validation_inputs())

    def test_record_order_or_source_closure_drift_is_rejected(self) -> None:
        changed = self._validation_inputs()
        records = changed["records"]
        self.assertIsInstance(records, list)
        assert isinstance(records, list)
        records[17], records[16] = records[16], records[17]
        with self.assertRaises(contract.MM005GenerationFailureInvestigationError):
            contract.expected_preregistration(**changed)

        for mutation in ("missing", "extra", "path", "digest"):
            changed = self._validation_inputs()
            receipts = changed["source_receipts"]
            self.assertIsInstance(receipts, dict)
            assert isinstance(receipts, dict)
            if mutation == "missing":
                receipts.pop("v2_runner")
            elif mutation == "extra":
                receipts["extra"] = {
                    "path": "README.md",
                    "bytes": 0,
                    "sha256": "sha256:" + "0" * 64,
                }
            elif mutation == "path":
                receipts["v2_runner"]["path"] = "../outside.py"
            else:
                receipts["v2_runner"]["sha256"] = "sha256:" + "0" * 64
            with (
                self.subTest(mutation=mutation),
                self.assertRaises(contract.MM005GenerationFailureInvestigationError),
            ):
                contract.validate_preregistration(self.protocol, **changed)

    def test_freeze_blob_drift_and_unsafe_paths_are_rejected(self) -> None:
        original = builder._git_blob_bytes

        def changed(commit: str, relative: str) -> bytes:
            payload = original(commit, relative)
            if relative == failure.ARTIFACT_PATH:
                return payload + b" "
            return payload

        with (
            mock.patch.object(builder, "_git_blob_bytes", side_effect=changed),
            self.assertRaises(RuntimeError),
        ):
            builder._validate_published_classification_lineage()
        for path in ("", "../outside", "/absolute", "a\\b", "a/./b"):
            with self.subTest(path=path), self.assertRaises(RuntimeError):
                builder._validate_repository_relative_path(path)

    def test_symlink_and_hardlink_bound_files_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = root / "original.json"
            original.write_bytes(b"{}\n")
            linked = root / "linked.json"
            try:
                os.link(original, linked)
            except OSError as exc:
                self.skipTest(f"hardlinks unavailable: {exc}")
            with self.assertRaises(RuntimeError):
                builder._read_regular_file_once(linked)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = root / "original.json"
            original.write_bytes(b"{}\n")
            with (
                mock.patch.object(Path, "is_symlink", return_value=True),
                self.assertRaises(RuntimeError),
            ):
                builder._read_regular_file_once(original)

    def test_existing_protocol_is_never_overwritten(self) -> None:
        with (
            mock.patch.object(builder, "build_protocol", return_value=self.protocol),
            self.assertRaises(FileExistsError),
        ):
            builder.main([])

    def test_protocol_does_not_repeat_plaintext_attempt_identity(self) -> None:
        owner_payload = self.inputs["attempt_owner_payload"]
        self.assertIsInstance(owner_payload, bytes)
        assert isinstance(owner_payload, bytes)
        owner = contract.parse_strict_json_bytes(owner_payload, location="$.owner")
        attempt_id = owner["attempt_id"]
        self.assertIsInstance(attempt_id, str)
        assert isinstance(attempt_id, str)
        self.assertNotIn(attempt_id.encode("utf-8"), self.protocol_payload)

    def test_new_sources_have_no_model_network_or_cuda_capability(self) -> None:
        paths = (
            ROOT
            / "src/fullcycle_bridge/mm005_browser_research_model_evaluation_generation_failure_investigation.py",
            ROOT
            / "scripts/prepare_mm005_browser_research_model_evaluation_generation_failure_investigation_protocol_v1.py",
        )
        imported: set[str] = set()
        called_attributes: set[str] = set()
        for path in paths:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported.add(node.module.split(".")[0])
                elif isinstance(node, ast.Call) and isinstance(
                    node.func, ast.Attribute
                ):
                    called_attributes.add(node.func.attr)
        self.assertTrue(
            imported.isdisjoint(
                {
                    "torch",
                    "transformers",
                    "peft",
                    "bitsandbytes",
                    "PIL",
                    "socket",
                    "urllib",
                }
            )
        )
        self.assertTrue(
            called_attributes.isdisjoint(
                {
                    "generate",
                    "apply_chat_template",
                    "from_pretrained",
                    "synchronize",
                    "create_connection",
                    "urlopen",
                }
            )
        )


if __name__ == "__main__":
    unittest.main()
