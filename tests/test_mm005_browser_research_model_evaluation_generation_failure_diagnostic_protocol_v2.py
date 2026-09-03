from __future__ import annotations

import ast
import copy
import json
import os
import subprocess
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
    mm005_browser_research_model_evaluation_generation_failure_diagnostic as v1,
)
from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_model_evaluation_generation_failure_diagnostic_protocol_v2 as contract,
)
from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_model_evaluation_protocol_v2 as original_v2,
)
from scripts import (  # noqa: E402
    prepare_mm005_browser_research_model_evaluation_generation_failure_diagnostic_protocol_v2 as builder,
)
from scripts import (  # noqa: E402
    prepare_mm005_browser_research_model_evaluation_generation_failure_diagnostic_protocol_v1 as v1_builder,
)

PROTOCOL_PATH = ROOT / contract.PREREGISTRATION_PATH


class MM005GenerationFailureDiagnosticProtocolV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.protocol_payload = PROTOCOL_PATH.read_bytes()
        cls.protocol = contract.parse_strict_json_bytes(
            cls.protocol_payload, location="$.diagnostic_protocol_v2"
        )
        cls.inputs = builder.protocol_inputs()

    def _inputs(self) -> dict[str, object]:
        return copy.deepcopy(self.inputs)

    def _patched_output_identity(self, output_root: str) -> mock._patch:
        return mock.patch.multiple(
            contract,
            RUN_OUTPUT_ROOT=output_root,
            ATTEMPT_OWNER_PATH=f"{output_root}/attempt-owner.json",
            PROGRESS_PATH=f"{output_root}/progress.json",
            SUCCESS_RESULT_PATH=f"{output_root}/diagnostic-result.json",
            FAILURE_PATH=f"{output_root}/diagnostic-failure.json",
            LIFECYCLE_LEASE_ROOT=f"{output_root}.lifecycle",
            LIFECYCLE_LEASE_PATH=f"{output_root}.lifecycle/lease",
        )

    def test_canonical_rebuild_validation_and_builder_check_pass(self) -> None:
        rebuilt = contract.expected_preregistration(**self._inputs())
        self.assertEqual(contract.artifact_json_bytes(rebuilt), self.protocol_payload)
        self.assertEqual(
            contract.validate_preregistration(self.protocol, **self._inputs()), rebuilt
        )
        self.assertEqual(builder.build_protocol(), rebuilt)
        self.assertEqual(builder.main(["--check"]), 0)

        completed = subprocess.run(
            [sys.executable, "-I", str(Path(builder.__file__)), "--check"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
        summary = json.loads(completed.stdout)
        self.assertTrue(summary["valid"])
        self.assertFalse(summary["diagnostic_execution_authorized"])
        self.assertEqual(summary["gate_id"], contract.GATE_ID)
        self.assertEqual(summary["next_gate"], contract.IMPLEMENTATION_GATE_ID)
        self.assertEqual(
            summary["protocol_sha256"], contract.sha256_bytes(self.protocol_payload)
        )

    def test_final_snapshot_rejects_source_drift(self) -> None:
        _, snapshot = builder._capture_protocol_inputs()
        changed = copy.deepcopy(snapshot)
        sources = changed["source_payloads"]
        self.assertIsInstance(sources, dict)
        assert isinstance(sources, dict)
        source_name = next(iter(contract.PROTOCOL_SOURCE_PATHS))
        sources[source_name] += b"\n"
        with self.assertRaisesRegex(RuntimeError, "protocol source changed"):
            builder._revalidate_protocol_inputs(changed)

    def test_lineage_receipts_and_first_parent_chain_are_exact(self) -> None:
        lineage = self.protocol["source_lineage"]
        self.assertEqual(
            lineage["commit_parent_chain"],
            [
                {"commit": child, "parent": parent, "unique_first_parent": True}
                for child, parent in contract.COMMIT_PARENT_CHAIN.items()
            ],
        )
        self.assertEqual(
            lineage["maintenance_merge_commit"], contract.MAINTENANCE_MERGE_COMMIT
        )
        self.assertEqual(
            lineage["original_v2_preregistration"],
            {
                "path": v1.V2_PREREGISTRATION_PATH,
                "bytes": contract.ORIGINAL_V2_PREREGISTRATION_BYTES,
                "sha256": contract.ORIGINAL_V2_PREREGISTRATION_SHA256,
                "introduction_commit": contract.ORIGINAL_V2_INTRODUCTION_COMMIT,
                "unique_first_parent_introduction": True,
                "static_result_binding_commit": contract.STATIC_RESULT_COMMIT,
                "protocol_v2_base_commit": contract.MAINTENANCE_MERGE_COMMIT,
                "introduction_blob_equals_static_result_binding_blob": True,
                "static_result_binding_blob_equals_protocol_v2_base_blob": True,
                "current_bytes_equal_protocol_v2_base_blob": True,
            },
        )
        self.assertEqual(
            set(lineage["bound_artifacts"]), set(contract.LINEAGE_BINDINGS)
        )
        for name, binding in contract.LINEAGE_BINDINGS.items():
            receipt = lineage["bound_artifacts"][name]
            self.assertEqual(receipt["binding_commit"], binding["commit"])
            self.assertEqual(receipt["binding_role"], binding["role"])
            self.assertEqual(receipt["path"], binding["path"])
            self.assertEqual(receipt["bytes"], binding["bytes"])
            self.assertEqual(receipt["sha256"], binding["sha256"])
            self.assertTrue(receipt["current_bytes_equal_binding_commit_blob"])

        for child, parent in contract.COMMIT_PARENT_CHAIN.items():
            completed = builder._git_process("rev-list", "--parents", "-n", "1", child)
            self.assertEqual(completed.returncode, 0)
            self.assertEqual(
                completed.stdout.decode("ascii").strip().split(), [child, parent]
            )

    def test_specified_identities_commits_and_digests_are_literal_anchors(self) -> None:
        self.assertEqual(
            contract.EXPERIMENT_ID,
            "mm005-browser-research-model-eval-v2-generation-failure-diagnostic-v2",
        )
        self.assertEqual(
            contract.RUN_ID,
            "mm005-browser-research-model-eval-v2-generation-failure-diagnostic-r2",
        )
        self.assertEqual(
            contract.RUN_OUTPUT_ROOT,
            "work/evaluation-runs/mm005-browser-research-model-eval-v2-"
            "generation-failure-diagnostic-v2",
        )
        self.assertEqual(
            contract.LIFECYCLE_LEASE_PATH,
            "work/evaluation-runs/mm005-browser-research-model-eval-v2-"
            "generation-failure-diagnostic-v2.lifecycle/lease",
        )
        self.assertEqual(
            contract.ORIGINAL_V2_INTRODUCTION_COMMIT,
            "91b637c6b365ea8632b31335f5c74ac6c60e6b71",
        )
        self.assertEqual(
            contract.STATIC_RESULT_COMMIT,
            "c8541147717870992c60c6d2ea1c2f4ff68ee1d2",
        )
        self.assertEqual(
            contract.V1_PROTOCOL_COMMIT,
            "9c90c5e68d4386b30db613930ec7dc0147999c04",
        )
        self.assertEqual(
            contract.V1_IMPLEMENTATION_COMMIT,
            "7da39396c951a9248fe49c1bd69080923b827fa1",
        )
        self.assertEqual(
            contract.V1_AUTHORITY_COMMIT,
            "0a271e2c27c65e9595953dadb98200ea5ec51acb",
        )
        self.assertEqual(
            contract.V1_CLOSEOUT_COMMIT,
            "fd552896df1aea817ba4d2ece3bf43a8f248424f",
        )
        self.assertEqual(
            contract.MAINTENANCE_MERGE_COMMIT,
            "266e9b695af0f93ae4c82e36ac484cb2d3d3a521",
        )
        self.assertEqual(
            contract.ORIGINAL_V2_PREREGISTRATION_SHA256,
            "sha256:512b3523196bf80e7e137c7777c205fa92a57acf371464f3f65671c406706c2e",
        )
        self.assertEqual(
            contract.STATIC_RESULT_SHA256,
            "sha256:2be8caf8dbc35d2741d81d408f21fea08d7961cc970590a25922bc757485ca93",
        )
        self.assertEqual(
            contract.STATIC_RESULT_REPORT_DIGEST,
            "sha256:001b44cdb9d0a11a4be48e10f6653074e4bf407a43daaad1930c6d92e5f8cde7",
        )
        self.assertEqual(
            contract.RECORD_REGISTRY_SHA256,
            "sha256:c3057651c41be738257db7ae0af4c8bcdf3419493d22064b8ea9eb935d758886",
        )
        self.assertEqual(
            contract.V1_PROTOCOL_SHA256,
            "sha256:13d1808168819414df2a0ca33d1f59e5e8efd52de6f0b49946d02cf070c992d6",
        )
        self.assertEqual(
            contract.V1_CLOSEOUT_SHA256,
            "sha256:d8a64be5b0361322246faf4eeccde04f9921e0a9c586f3498b188a6477d1ddce",
        )
        self.assertEqual(
            contract.V1_CLOSEOUT_CONTRACT_SHA256,
            "sha256:115c1bb180a496c03c199d209d3b7a25514b58956a1d4222e25eec225394e649",
        )
        self.assertEqual(
            contract.V1_AUTHORITY_SHA256,
            "sha256:903e681c2957e185da36ed1f991cc5b339b0e692e8c730da63069690277b9e6b",
        )

    def test_lineage_payload_or_receipt_drift_fails_closed(self) -> None:
        for mutation in ("current", "blob", "missing", "extra"):
            changed = self._inputs()
            current = changed["lineage_current_payloads"]
            blobs = changed["lineage_blob_payloads"]
            self.assertIsInstance(current, dict)
            self.assertIsInstance(blobs, dict)
            assert isinstance(current, dict)
            assert isinstance(blobs, dict)
            name = "v1_invocation_closeout"
            if mutation == "current":
                current[name] += b" "
            elif mutation == "blob":
                blobs[name] += b" "
            elif mutation == "missing":
                current.pop(name)
            else:
                current["extra"] = b"x"
                blobs["extra"] = b"x"
            with (
                self.subTest(mutation=mutation),
                self.assertRaises(
                    contract.MM005GenerationFailureDiagnosticProtocolV2Error
                ),
            ):
                contract.expected_preregistration(**changed)

    def test_v1_scientific_subtrees_are_semantically_immutable(self) -> None:
        v1_payload = self.inputs["lineage_current_payloads"]["v1_diagnostic_protocol"]
        self.assertIsInstance(v1_payload, bytes)
        assert isinstance(v1_payload, bytes)
        v1_protocol = contract.parse_strict_json_bytes(
            v1_payload, location="$.v1_protocol"
        )
        scientific = self.protocol["immutable_scientific_contract"]
        self.assertEqual(
            scientific["subtree_names"], list(contract.IMMUTABLE_V1_SUBTREE_NAMES)
        )
        for name in contract.IMMUTABLE_V1_SUBTREE_NAMES:
            self.assertEqual(scientific["subtrees"][name], v1_protocol[name])
            self.assertEqual(
                scientific["subtree_sha256"][name],
                contract.sha256_bytes(contract.artifact_json_bytes(v1_protocol[name])),
            )
        self.assertEqual(scientific["record_count"], 7)
        self.assertEqual(scientific["required_environment_field_count"], 17)
        self.assertEqual(scientific["diagnostic_substage_count"], 9)
        self.assertEqual(scientific["durable_substage_checkpoint_count"], 126)
        self.assertEqual(scientific["success_frame_count"], 133)
        self.assertEqual(len(scientific["failure_scopes"]), 4)
        self.assertEqual(len(scientific["allowed_outcomes"]), 4)
        self.assertEqual(scientific["seed"], 55006)
        self.assertEqual(
            scientific["record_registry_sha256"], contract.RECORD_REGISTRY_SHA256
        )

    def test_scientific_or_closeout_semantic_drift_is_rejected(self) -> None:
        changed = self._inputs()
        v1_expected = changed["v1_expected_preregistration"]
        self.assertIsInstance(v1_expected, dict)
        assert isinstance(v1_expected, dict)
        v1_expected["resource_contract"]["scientific_inputs"]["seed"] = 1
        with self.assertRaises(
            contract.MM005GenerationFailureDiagnosticProtocolV2Error
        ):
            contract.expected_preregistration(**changed)

        changed = self._inputs()
        current = changed["lineage_current_payloads"]
        blobs = changed["lineage_blob_payloads"]
        self.assertIsInstance(current, dict)
        self.assertIsInstance(blobs, dict)
        assert isinstance(current, dict)
        assert isinstance(blobs, dict)
        closeout = contract.parse_strict_json_bytes(
            current["v1_invocation_closeout"], location="$.closeout"
        )
        closeout["invocation"]["formal_invocation_budget_remaining"] = 1
        resealed = contract.artifact_json_bytes(closeout)
        current["v1_invocation_closeout"] = resealed
        blobs["v1_invocation_closeout"] = resealed
        with self.assertRaises(
            contract.MM005GenerationFailureDiagnosticProtocolV2Error
        ):
            contract.expected_preregistration(**changed)

    def test_new_identity_is_casefold_and_ancestor_unique_from_predecessors(
        self,
    ) -> None:
        self.assertEqual(self.protocol["experiment_id"], contract.EXPERIMENT_ID)
        self.assertEqual(self.protocol["run_id"], contract.RUN_ID)
        self.assertEqual(
            self.protocol["outputs"]["output_root"], contract.RUN_OUTPUT_ROOT
        )
        separation = self.protocol["identity_separation"]
        self.assertTrue(
            separation["windows_casefold_and_ancestor_unique_from_original_v2_and_v1"]
        )
        self.assertEqual(
            separation["predecessor_runtime_roots"],
            list(contract.PREDECESSOR_RUNTIME_ROOTS),
        )
        for field, value in (
            ("EXPERIMENT_ID", original_v2.EXPERIMENT_ID.upper()),
            ("EXPERIMENT_ID", v1.EXPERIMENT_ID),
            ("RUN_ID", original_v2.RUN_ID.upper()),
            ("RUN_ID", v1.RUN_ID),
        ):
            with (
                self.subTest(field=field, value=value),
                mock.patch.object(contract, field, value),
                self.assertRaises(
                    contract.MM005GenerationFailureDiagnosticProtocolV2Error
                ),
            ):
                contract.expected_preregistration(**self._inputs())

        for root in (
            "work/evaluation-runs",
            v1.RUN_OUTPUT_ROOT.upper(),
            f"{original_v2.RUN_OUTPUT_ROOT}/nested",
            f"{v1.LIFECYCLE_LEASE_ROOT}/nested",
            "work\\evaluation-runs\\escape",
            "C:/work/evaluation-runs/escape",
        ):
            with (
                self.subTest(root=root),
                self._patched_output_identity(root),
                self.assertRaises(
                    contract.MM005GenerationFailureDiagnosticProtocolV2Error
                ),
            ):
                contract.expected_preregistration(**self._inputs())

    def test_fixed_artifact_names_and_lease_location_are_closed(self) -> None:
        outputs = self.protocol["outputs"]
        self.assertEqual(
            outputs["artifact_names"],
            {
                "attempt_owner": "attempt-owner.json",
                "progress": "progress.json",
                "success_result": "diagnostic-result.json",
                "failure": "diagnostic-failure.json",
            },
        )
        self.assertEqual(outputs["attempt_owner"], contract.ATTEMPT_OWNER_PATH)
        self.assertEqual(outputs["progress"], contract.PROGRESS_PATH)
        self.assertEqual(outputs["success_result"], contract.SUCCESS_RESULT_PATH)
        self.assertEqual(outputs["failure"], contract.FAILURE_PATH)
        self.assertEqual(outputs["lifecycle_lease"], contract.LIFECYCLE_LEASE_PATH)
        self.assertEqual(
            contract.LIFECYCLE_LEASE_PATH, f"{contract.RUN_OUTPUT_ROOT}.lifecycle/lease"
        )

    def test_output_parent_contract_is_closed_and_strictly_ordered(self) -> None:
        parent = self.protocol["output_parent_preparation_contract"]
        self.assertEqual(parent["scope"], "future_execution_v2_only")
        self.assertFalse(parent["mutable_during_plan_check_or_protocol_freeze"])
        self.assertEqual(
            parent["mutation_preconditions"],
            [
                "published_execution_authority_v2",
                "clean_aligned_master_head",
                "exact_protocol_implementation_and_authority_lineage",
                "unclaimed_output_topology",
            ],
        )
        self.assertEqual(
            parent["required_existing_directories"],
            [
                {
                    "path": "repository_root",
                    "must_exist": True,
                    "ordinary_directory": True,
                    "symlink_or_reparse_forbidden": True,
                },
                {
                    "path": contract.WORK_ROOT_PATH,
                    "must_exist": True,
                    "ordinary_directory": True,
                    "symlink_or_reparse_forbidden": True,
                },
            ],
        )
        self.assertEqual(
            parent["initial_output_parent_state"],
            {
                "path": contract.OUTPUT_PARENT_PATH,
                "must_be_absent": True,
                "collision_forbidden": True,
            },
        )
        self.assertEqual(
            [step["operation"] for step in parent["ordered_steps"]],
            [
                "construct_and_verify_directory_tree_guard",
                "exclusive_single_directory_create",
                "revalidate_authority_lineage_remaining_topology_and_ancestry",
                "construct_and_verify_directory_tree_guard",
                "enter_lifecycle_lease",
                "atomic_attempt_owner_and_genesis_claim",
                "enter_first_heavy_dependency_boundary",
            ],
        )
        self.assertEqual(
            [step["index"] for step in parent["ordered_steps"]], list(range(7))
        )
        self.assertEqual(
            parent["ordered_steps"][0],
            {
                "index": 0,
                "operation": "construct_and_verify_directory_tree_guard",
                "guard_root": "repository_root",
                "guard_target": contract.WORK_ROOT_PATH,
                "mutates_filesystem": False,
            },
        )
        creation = parent["ordered_steps"][1]
        self.assertEqual(creation["primitive"], "os.mkdir")
        self.assertEqual(creation["path"], contract.OUTPUT_PARENT_PATH)
        self.assertFalse(creation["parents_created"])
        self.assertFalse(creation["exist_ok"])
        self.assertTrue(parent["directory_guard_verified_before_lifecycle"])
        self.assertTrue(
            parent[
                "authority_lineage_and_remaining_unclaimed_topology_revalidated_after_create_before_lifecycle"
            ]
        )
        revalidation = parent["ordered_steps"][2]
        self.assertTrue(revalidation["published_execution_authority_v2_revalidated"])
        self.assertTrue(revalidation["clean_aligned_head_revalidated"])
        self.assertTrue(revalidation["exact_lineage_revalidated"])
        self.assertTrue(
            revalidation["planned_output_root_lifecycle_owner_and_progress_unclaimed"]
        )
        self.assertTrue(
            revalidation["created_parent_excluded_from_precreate_absence_predicate"]
        )
        self.assertEqual(
            parent["ordered_steps"][3],
            {
                "index": 3,
                "operation": "construct_and_verify_directory_tree_guard",
                "guard_root": "repository_root",
                "guard_target": contract.OUTPUT_PARENT_PATH,
                "mutates_filesystem": False,
            },
        )
        self.assertTrue(parent["lifecycle_entered_before_owner_and_genesis_claim"])
        self.assertFalse(parent["parent_creation_is_attempt_claim"])
        self.assertFalse(parent["parent_creation_is_formal_telemetry"])
        for key in (
            "collision_unsafe_identity_drift_or_guard_failure_precedes_lifecycle",
            "collision_unsafe_identity_drift_or_guard_failure_precedes_claim",
            "collision_unsafe_identity_drift_or_guard_failure_precedes_heavy_import",
            "collision_unsafe_identity_drift_or_guard_failure_precedes_model_or_cuda",
        ):
            self.assertTrue(parent[key])
        self.assertIsNone(parent["pre_owner_failure_scope"])
        self.assertIsNone(parent["pre_owner_failure_outcome"])
        self.assertFalse(parent["pre_owner_failure_terminal_synthesis_authorized"])
        self.assertTrue(parent["pre_owner_failure_spends_formal_invocation_budget"])
        self.assertFalse(parent["pre_owner_failure_retry_authorized"])
        self.assertFalse(parent["same_privilege_toctou_eliminated"])
        self.assertEqual(
            parent["same_privilege_toctou_limit"],
            "identity guards detect observed replacement but cannot exclude every "
            "same-privilege mutation between checks",
        )

    def test_plan_check_and_freeze_do_not_create_missing_parent(self) -> None:
        work_root = ROOT / contract.WORK_ROOT_PATH
        output_parent = ROOT / contract.OUTPUT_PARENT_PATH
        observed_paths = (
            work_root,
            output_parent,
            ROOT / contract.RUN_OUTPUT_ROOT,
            ROOT / contract.LIFECYCLE_LEASE_ROOT,
            *(ROOT / relative for relative in contract.PREDECESSOR_RUNTIME_ROOTS),
        )

        def topology_signature(path: Path) -> tuple[int, ...] | None:
            if not os.path.lexists(path):
                return None
            metadata = path.lstat()
            return (
                metadata.st_dev,
                metadata.st_ino,
                metadata.st_mode,
                metadata.st_size,
                metadata.st_mtime_ns,
                metadata.st_nlink,
            )

        topology_before = {path: topology_signature(path) for path in observed_paths}
        before = self.protocol_payload
        self.assertEqual(builder.main(["--check"]), 0)
        self.assertEqual(PROTOCOL_PATH.read_bytes(), before)
        self.assertEqual(
            {path: topology_signature(path) for path in observed_paths},
            topology_before,
        )

        with tempfile.TemporaryDirectory() as temporary:
            temp_root = Path(temporary).resolve()
            before = list(temp_root.iterdir())
            with mock.patch.object(builder, "ROOT", temp_root):
                presence = builder._require_planned_outputs_absent()
            self.assertTrue(all(presence.values()))
            self.assertEqual(list(temp_root.iterdir()), before)

        with tempfile.TemporaryDirectory() as temporary:
            temp_root = Path(temporary).resolve()
            (temp_root / contract.WORK_ROOT_PATH).mkdir()
            with mock.patch.object(builder, "ROOT", temp_root):
                presence = builder._require_planned_outputs_absent()
            self.assertEqual(
                presence,
                {
                    "planned_output_absent": True,
                    "planned_lifecycle_absent": True,
                },
            )
            self.assertTrue((temp_root / contract.WORK_ROOT_PATH).is_dir())
            self.assertFalse(os.path.lexists(temp_root / contract.OUTPUT_PARENT_PATH))

        with tempfile.TemporaryDirectory() as temporary:
            temp_root = Path(temporary).resolve()
            (temp_root / contract.OUTPUT_PARENT_PATH).mkdir(parents=True)
            before = sorted(
                path.relative_to(temp_root) for path in temp_root.rglob("*")
            )
            with mock.patch.object(builder, "ROOT", temp_root):
                presence = builder._require_planned_outputs_absent()
            after = sorted(path.relative_to(temp_root) for path in temp_root.rglob("*"))
            self.assertTrue(all(presence.values()))
            self.assertEqual(after, before)

    def test_predecessor_runtime_is_ignored_and_strictly_read_only(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temp_root = Path(temporary).resolve()
            sentinels: dict[Path, bytes] = {}
            for index, relative in enumerate(contract.PREDECESSOR_RUNTIME_ROOTS):
                historical_root = temp_root / relative
                historical_root.mkdir(parents=True, exist_ok=True)
                sentinel = historical_root / f"history-{index}.bin"
                payload = f"immutable-history-{index}".encode("ascii")
                sentinel.write_bytes(payload)
                sentinels[sentinel] = payload
            tree_before = sorted(
                path.relative_to(temp_root) for path in temp_root.rglob("*")
            )
            with mock.patch.object(builder, "ROOT", temp_root):
                presence = builder._require_planned_outputs_absent()
            tree_after = sorted(
                path.relative_to(temp_root) for path in temp_root.rglob("*")
            )
            self.assertTrue(all(presence.values()))
            self.assertEqual(tree_after, tree_before)
            self.assertEqual({path: path.read_bytes() for path in sentinels}, sentinels)
            for relative in (
                contract.RUN_OUTPUT_ROOT,
                contract.LIFECYCLE_LEASE_ROOT,
                contract.ATTEMPT_OWNER_PATH,
                contract.PROGRESS_PATH,
                contract.SUCCESS_RESULT_PATH,
                contract.FAILURE_PATH,
                contract.LIFECYCLE_LEASE_PATH,
            ):
                self.assertFalse(os.path.lexists(temp_root / relative))

        with mock.patch.object(
            v1_builder,
            "_require_planned_outputs_absent",
            side_effect=AssertionError("v1 current runtime topology was consulted"),
        ):
            rebuilt = builder._rebuild_frozen_v1_protocol_without_runtime_topology()
        self.assertEqual(
            v1.artifact_json_bytes(rebuilt),
            self.inputs["lineage_current_payloads"]["v1_diagnostic_protocol"],
        )

    def test_planned_runtime_collision_fails_before_build(self) -> None:
        for relative in (contract.RUN_OUTPUT_ROOT, contract.LIFECYCLE_LEASE_ROOT):
            with tempfile.TemporaryDirectory() as temporary:
                temp_root = Path(temporary).resolve()
                collision = temp_root / relative
                collision.mkdir(parents=True)
                with (
                    self.subTest(relative=relative),
                    mock.patch.object(builder, "ROOT", temp_root),
                    self.assertRaisesRegex(RuntimeError, "runtime exists"),
                ):
                    builder._require_planned_outputs_absent()

    def test_future_implementation_regression_is_mandatory_and_model_free(
        self,
    ) -> None:
        regression = self.protocol["implementation_v2_regression_contract"]
        self.assertTrue(regression["mandatory"])
        self.assertTrue(regression["real_temporary_filesystem"])
        self.assertTrue(regression["initial_topology"]["work_root_exists"])
        self.assertTrue(regression["initial_topology"]["output_parent_absent"])
        self.assertFalse(regression["output_parent_helper_mocked"])
        self.assertFalse(regression["directory_tree_guard_mocked"])
        self.assertTrue(regression["exercise_execute_path"])
        self.assertEqual(
            regression["must_reach"],
            [
                "output_parent_exclusive_create",
                "output_parent_guard_verification",
                "lifecycle_lease",
                "attempt_owner",
                "attempt_claimed_genesis",
            ],
        )
        self.assertEqual(
            regression["controlled_exception_boundary"],
            "first_heavy_dependency_boundary",
        )
        self.assertEqual(regression["expected_failure_scope"], "pre_record_lifecycle")
        for key in (
            "model_import_entered",
            "model_load_entered",
            "cuda_entered",
            "network_entered",
            "establishes_formal_execution_authority",
            "consumes_formal_invocation_budget",
        ):
            self.assertFalse(regression[key])

    def test_every_derived_artifact_and_parent_path_must_match_exactly(self) -> None:
        mutations = (
            ("ATTEMPT_OWNER_PATH", "other/attempt-owner.json"),
            ("PROGRESS_PATH", f"{contract.RUN_OUTPUT_ROOT}/other-progress.json"),
            ("SUCCESS_RESULT_PATH", f"{contract.RUN_OUTPUT_ROOT}/other-result.json"),
            ("FAILURE_PATH", f"{contract.RUN_OUTPUT_ROOT}/other-failure.json"),
            ("LIFECYCLE_LEASE_ROOT", f"{contract.RUN_OUTPUT_ROOT}/.lifecycle"),
            ("LIFECYCLE_LEASE_PATH", f"{contract.RUN_OUTPUT_ROOT}.lifecycle/other"),
            ("OUTPUT_PARENT_PATH", "work/other-parent"),
            ("WORK_ROOT_PATH", "other-work"),
        )
        for field, value in mutations:
            with (
                self.subTest(field=field),
                mock.patch.object(contract, field, value),
                self.assertRaises(
                    contract.MM005GenerationFailureDiagnosticProtocolV2Error
                ),
            ):
                contract.expected_preregistration(**self._inputs())

    def test_protocol_freeze_has_no_execution_retry_or_terminal_synthesis(self) -> None:
        freeze = self.protocol["freeze_preconditions"]
        execution = self.protocol["execution_protocol"]
        authority = self.protocol["authority_contract"]
        claims = self.protocol["claims"]
        self.assertEqual(freeze["formal_diagnostic_invocations"], 0)
        self.assertEqual(freeze["diagnostic_attempts_consumed"], 0)
        self.assertTrue(freeze["v1_invocation_budget_spent"])
        self.assertTrue(freeze["v1_diagnostic_attempt_unconsumed"])
        self.assertFalse(freeze["v1_retry_authorized"])
        self.assertFalse(freeze["v1_terminal_synthesis_authorized"])
        self.assertFalse(execution["diagnostic_execution_authorized"])
        self.assertEqual(execution["formal_invocation_budget_spent"], 0)
        self.assertEqual(execution["retry_budget"], 0)
        self.assertFalse(authority["v1_retry_authorized"])
        self.assertFalse(authority["v2_retry_authorized"])
        self.assertFalse(authority["recovery_v3_authorized"])
        self.assertFalse(claims["v2_diagnostic_attempt_consumed"])
        self.assertFalse(claims["v2_diagnostic_executed"])
        self.assertFalse(claims["formal_measurement_complete"])

    def test_exact_eleven_path_protocol_slice_and_sources_are_model_free(self) -> None:
        self.assertEqual(len(contract.PROTOCOL_SLICE_PATHS), 11)
        self.assertEqual(
            self.protocol["publication"]["slice_paths"],
            sorted(contract.PROTOCOL_SLICE_PATHS),
        )
        self.assertFalse(self.protocol["publication"]["v1_runner_modified"])
        self.assertFalse(self.protocol["publication"]["v1_recovery_io_modified"])
        self.assertFalse(
            self.protocol["publication"]["runner_result_or_authority_added"]
        )

        forbidden_imports = {
            "PIL",
            "aiohttp",
            "bitsandbytes",
            "httpx",
            "peft",
            "requests",
            "socket",
            "torch",
            "transformers",
            "urllib",
        }
        forbidden_git_operations = {
            "clone",
            "fetch",
            "ls-remote",
            "pull",
            "push",
            "remote",
        }
        forbidden_call_names = {
            "cuda",
            "from_pretrained",
            "generate",
            "load_model",
            "request",
            "urlopen",
        }
        for relative in contract.PROTOCOL_SOURCE_PATHS.values():
            source = (ROOT / relative).read_text(encoding="utf-8")
            tree = ast.parse(source)
            imports: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module is not None:
                    imports.add(node.module.split(".")[0])
            strings = {
                node.value
                for node in ast.walk(tree)
                if isinstance(node, ast.Constant) and isinstance(node.value, str)
            }
            loaded_names = {
                node.id
                for node in ast.walk(tree)
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
            }
            called_attributes = {
                node.func.attr
                for node in ast.walk(tree)
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            }
            called_names = {
                node.func.id
                for node in ast.walk(tree)
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            }
            self.assertTrue(forbidden_imports.isdisjoint(imports), relative)
            self.assertTrue(forbidden_imports.isdisjoint(loaded_names), relative)
            self.assertTrue(
                forbidden_call_names.isdisjoint(called_attributes | called_names),
                relative,
            )
            self.assertTrue(forbidden_git_operations.isdisjoint(strings), relative)
            self.assertNotIn("https://", source)
            self.assertNotIn("http://", source)

        for synthetic in (
            "from torch import Tensor\nTensor()\n",
            "from urllib.request import urlopen\nurlopen('https://example.invalid')\n",
            "def generate(): pass\ngenerate()\n",
        ):
            tree = ast.parse(synthetic)
            imports = {
                node.module.split(".")[0]
                for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom) and node.module is not None
            }
            calls = {
                node.func.id
                for node in ast.walk(tree)
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            }
            self.assertTrue(
                bool(forbidden_imports & imports) or bool(forbidden_call_names & calls)
            )

    def test_separate_implementation_v2_freezes_parent_order_without_authority(
        self,
    ) -> None:
        from fullcycle_bridge import (  # noqa: PLC0415
            mm005_browser_research_model_evaluation_generation_failure_diagnostic_result_v2 as result_contract,
        )
        from scripts import (  # noqa: PLC0415
            run_mm005_browser_research_model_evaluation_generation_failure_diagnostic_v2 as runner,
        )

        before = runner._output_topology()
        implementation = result_contract.result_contract()
        base = implementation["implementation_base_binding"]
        authority = implementation["execution_authority_contract"]
        parent = implementation["output_parent_preparation_contract"]
        publication = implementation["publication_contract"]
        regression = implementation["implementation_regression_contract"]
        self.assertEqual(
            result_contract.PROTOCOL_MERGE_COMMIT,
            "eb2aea3ca1eb5d82e823f7fc7a6aac7b5beb3fc9",
        )
        self.assertEqual(
            result_contract.ZERO_BANDWIDTH_MAINTENANCE_COMMIT,
            "e5e618b491a3dc38dbed9cdcd4c6c384f2df0f54",
        )
        self.assertEqual(
            result_contract.IMPLEMENTATION_BASE_COMMIT,
            "8c679eba08a979fb60bfd87fbe8c73c8725d89c0",
        )
        self.assertEqual(implementation["gate_id"], contract.IMPLEMENTATION_GATE_ID)
        self.assertEqual(implementation["next_gate_id"], contract.AUTHORITY_GATE_ID)
        self.assertEqual(base["commit"], result_contract.IMPLEMENTATION_BASE_COMMIT)
        self.assertEqual(
            base["unique_parent"],
            result_contract.ZERO_BANDWIDTH_MAINTENANCE_COMMIT,
        )
        self.assertEqual(
            base["zero_bandwidth_maintenance_commit"],
            result_contract.ZERO_BANDWIDTH_MAINTENANCE_COMMIT,
        )
        self.assertEqual(
            base["zero_bandwidth_maintenance_unique_parent"],
            result_contract.PROTOCOL_MERGE_COMMIT,
        )
        self.assertTrue(base["protocol_merge_commit_remains_receipt_and_ancestor"])
        self.assertTrue(base["implementation_freeze_must_have_base_as_unique_parent"])
        self.assertTrue(authority["exact_implementation_base_commit_required"])
        self.assertTrue(
            authority["authority_introduction_has_implementation_as_unique_parent"]
        )
        self.assertTrue(
            publication[
                "protocol_merge_maintenance_and_implementation_base_recorded_in_owner_and_terminal"
            ]
        )
        self.assertEqual(len(runner.IMPLEMENTATION_SLICE_PATHS), 11)
        self.assertEqual(parent["work_root"], contract.WORK_ROOT_PATH)
        self.assertEqual(parent["output_parent"], contract.OUTPUT_PARENT_PATH)
        self.assertEqual(parent["exclusive_single_component_primitive"], "os.mkdir")
        self.assertTrue(
            parent[
                "authority_lineage_sources_and_remaining_topology_revalidated_after_create"
            ]
        )
        self.assertTrue(parent["atomic_owner_and_genesis_before_first_heavy_boundary"])
        self.assertEqual(
            regression["only_executed_injected_boundary"],
            "first_heavy_dependency_boundary",
        )
        self.assertEqual(
            regression["fail_on_call_spies_required"],
            ["socket", "network", "model_load", "cuda_workload"],
        )
        self.assertFalse(regression["formal_invocation_budget_consumed"])
        plan = runner.run(mode="plan")
        check = runner.run(mode="check")
        checkout_commit = runner._git_text("rev-parse", "HEAD")
        runner._require_unique_parent(
            result_contract.ZERO_BANDWIDTH_MAINTENANCE_COMMIT,
            result_contract.PROTOCOL_MERGE_COMMIT,
        )
        runner._require_unique_parent(
            result_contract.IMPLEMENTATION_BASE_COMMIT,
            result_contract.ZERO_BANDWIDTH_MAINTENANCE_COMMIT,
        )
        self.assertEqual(
            set(
                runner._git_name_only_paths(
                    result_contract.IMPLEMENTATION_BASE_COMMIT,
                    checkout_commit,
                )
            ),
            set(runner.IMPLEMENTATION_SLICE_PATHS),
        )
        self.assertTrue(plan["runner_plan_valid"])
        self.assertTrue(check["implementation_check_valid"])
        self.assertEqual(
            plan["zero_bandwidth_maintenance_commit"],
            result_contract.ZERO_BANDWIDTH_MAINTENANCE_COMMIT,
        )
        self.assertEqual(
            plan["implementation_base_commit"],
            result_contract.IMPLEMENTATION_BASE_COMMIT,
        )
        self.assertEqual(
            check["protocol_merge_commit"], result_contract.PROTOCOL_MERGE_COMMIT
        )
        self.assertEqual(
            check["implementation_base_commit"],
            result_contract.IMPLEMENTATION_BASE_COMMIT,
        )
        self.assertFalse(plan["execution_authority_present"])
        self.assertFalse(check["execution_path_invoked_by_gate"])
        self.assertEqual(runner._output_topology(), before)

    def test_strict_json_and_final_protocol_tamper_fail_closed(self) -> None:
        with self.assertRaises(
            contract.MM005GenerationFailureDiagnosticProtocolV2Error
        ):
            contract.parse_strict_json_bytes(b'{"a":1,"a":2}\n', location="$")
        changed = copy.deepcopy(self.protocol)
        changed["claims"]["v2_diagnostic_executed"] = True
        with self.assertRaises(
            contract.MM005GenerationFailureDiagnosticProtocolV2Error
        ):
            contract.validate_preregistration(changed, **self._inputs())


if __name__ == "__main__":
    unittest.main()
