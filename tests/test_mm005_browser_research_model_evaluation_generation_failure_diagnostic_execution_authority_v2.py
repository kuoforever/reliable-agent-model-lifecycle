from __future__ import annotations

import ast
import json
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
    mm005_browser_research_model_evaluation_generation_failure_diagnostic as scientific_protocol,
)
from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_model_evaluation_generation_failure_diagnostic_protocol_v2 as protocol,
)
from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_model_evaluation_generation_failure_diagnostic_result_v2 as contract,
)
from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_model_evaluation_protocol_v2 as v2,
)
from scripts import (  # noqa: E402
    prepare_mm005_browser_research_model_evaluation_generation_failure_diagnostic_execution_authority_v2 as builder,
)
from scripts import (  # noqa: E402
    run_mm005_browser_research_model_evaluation_generation_failure_diagnostic_v2 as runner,
)


class MM005GenerationFailureDiagnosticExecutionAuthorityV2Tests(unittest.TestCase):
    def test_builder_reproduces_closed_canonical_authority(self) -> None:
        payload = (ROOT / contract.EXECUTION_AUTHORITY_PATH).read_bytes()
        authority = builder.build_authority()
        self.assertEqual(len(payload), 2_944)
        self.assertEqual(
            contract.sha256_bytes(payload),
            "sha256:b638a7a73b401d6d968f9edc1b351e13394602b7d68dae7789f4485d996f39f0",
        )
        self.assertEqual(contract.artifact_json_bytes(authority), payload)
        self.assertEqual(json.loads(payload), authority)
        self.assertEqual(
            set(authority),
            {
                "mm005_browser_research_generation_failure_diagnostic_execution_authority_version",
                "gate_id",
                "next_gate",
                "protocol_merge_commit",
                "zero_bandwidth_maintenance_commit",
                "implementation_base_commit",
                "initial_implementation_publication_commit",
                "implementation_freeze_commit",
                "critical_execution_dependency_receipts",
                "resource_preflight",
                "budgets",
                "authority_contract",
                "claims",
            },
        )
        serialized = payload.decode("utf-8")
        self.assertEqual(
            set(authority["resource_preflight"]),
            {
                "expected_environment",
                "resource_caps",
                "exact_environment_match_required_before_model_load_or_cuda_workload",
                "read_only_cuda_capability_observation_allowed_for_exact_match",
                "missing_or_unverifiable_resource_blocks_execution",
            },
        )
        self.assertEqual(
            set(authority["budgets"]),
            {"formal_invocations", "retries", "per_record_attempts"},
        )
        self.assertEqual(
            set(authority["authority_contract"]),
            {
                "diagnostic_execution_authorized",
                "v1_or_v2_retry_authorized",
                "recovery_v3_authorized",
                "live_browser_or_network_authorized",
                "training_authorized",
                "runtime_integration_changed",
                "runtime_policy_or_approval_bypass",
                "current_head_equals_authority_introduction_commit",
                "assume_unchanged_or_skip_worktree_index_flags_forbidden",
                "git_fsmonitor_disabled",
                "reserved_sibling_staging_blocks_execution",
            },
        )
        self.assertEqual(
            set(authority["claims"]),
            {
                "authority_frozen",
                "diagnostic_attempt_consumed",
                "diagnostic_executed",
                "model_evaluated",
                "runtime_eligible",
            },
        )
        for receipt in authority["critical_execution_dependency_receipts"].values():
            self.assertEqual(set(receipt), {"path", "bytes", "sha256"})
        self.assertNotIn("implementation_source_receipts", authority)
        for forbidden in (
            '"authority_freeze_commit"',
            '"attempt_id"',
            '"captured_at_utc"',
            '"executed_at_utc"',
            '"failure_scope"',
            '"formal_invocation_budget_spent"',
            '"lifecycle_lease"',
            '"observed_environment"',
            '"output_root"',
            '"owner"',
            '"progress"',
            '"resources"',
            '"result"',
            '"runtime_output"',
            '"selected_outcome"',
        ):
            self.assertNotIn(forbidden, serialized)

    def test_authority_binds_i2_exact_environment_caps_and_budgets(self) -> None:
        authority = builder.build_authority()
        self.assertEqual(
            authority[
                "mm005_browser_research_generation_failure_diagnostic_execution_authority_version"
            ],
            2,
        )
        self.assertEqual(
            authority["implementation_freeze_commit"],
            "ac052a3781246deb7365914dacfa271d37cfef59",
        )
        self.assertEqual(
            authority["implementation_freeze_commit"],
            builder.IMPLEMENTATION_FREEZE_COMMIT,
        )
        self.assertEqual(authority["gate_id"], contract.EXECUTION_AUTHORITY_GATE_ID)
        self.assertEqual(authority["next_gate"], contract.EXECUTION_GATE_ID)
        self.assertEqual(
            authority["resource_preflight"]["expected_environment"],
            builder.EXPECTED_ENVIRONMENT,
        )
        self.assertEqual(
            set(builder.EXPECTED_ENVIRONMENT),
            set(scientific_protocol.OBSERVED_ENVIRONMENT_FIELDS),
        )
        self.assertNotIn("bitsandbytes", builder.EXPECTED_ENVIRONMENT)
        self.assertEqual(
            authority["resource_preflight"]["resource_caps"],
            {
                "elapsed_seconds": 1800.0,
                "peak_gpu_allocated_bytes": 16_500_000_000,
                "peak_gpu_reserved_bytes": 16_500_000_000,
            },
        )
        self.assertEqual(
            authority["resource_preflight"]["resource_caps"], v2.RESOURCE_CAPS
        )
        self.assertEqual(
            authority["budgets"],
            {"formal_invocations": 1, "retries": 0, "per_record_attempts": 1},
        )
        self.assertEqual(
            authority["claims"],
            {
                "authority_frozen": True,
                "diagnostic_attempt_consumed": False,
                "diagnostic_executed": False,
                "model_evaluated": False,
                "runtime_eligible": False,
            },
        )

    def test_four_critical_dependency_receipts_bind_i2_blobs(self) -> None:
        authority = builder.build_authority()
        receipts = authority["critical_execution_dependency_receipts"]
        expected = {
            "recovery_io": (
                13_995,
                "sha256:7ffd029ebf4e4995b1f45aed735a7d5303df273f450d8ad13f106eb044d73e64",
            ),
            "repeatability_runner": (
                56_740,
                "sha256:3330e84fa00752a0a3933ddc58592cea788afdb243c2e50684f7d305aecc88b0",
            ),
            "upstream_model_runner": (
                41_803,
                "sha256:2a86ac6bdf365dc99ab28c3823be073169bc9d5cc974c20b0d85f43052d723af",
            ),
            "v1_dataset_runner": (
                29_571,
                "sha256:0286e274ed9a9ef833f7b541cb2df606b4c1c69aed719b26cc50c3d52f5af71c",
            ),
        }
        self.assertEqual(set(receipts), set(expected))
        for name, relative in sorted(
            contract.CRITICAL_EXECUTION_DEPENDENCY_SOURCE_PATHS.items()
        ):
            payload = (ROOT / relative).read_bytes()
            frozen = builder._git_blob_bytes(
                builder.IMPLEMENTATION_FREEZE_COMMIT, relative
            )
            self.assertEqual(payload, frozen)
            self.assertEqual(receipts[name]["path"], relative)
            self.assertEqual(
                (receipts[name]["bytes"], receipts[name]["sha256"]), expected[name]
            )

    def test_three_implementation_source_receipts_bind_i2_and_i1_introduction(
        self,
    ) -> None:
        receipts = builder.authority_inputs()["implementation_source_receipts"]
        self.assertEqual(set(receipts), set(contract.IMPLEMENTATION_SOURCE_PATHS))
        self.assertEqual(len(receipts), 3)
        expected = {
            "diagnostic_result_contract": (
                84_964,
                "sha256:8a850a3ebf60c067fe933476058c2dca6b9645d625d9c881167f5d7b3590177d",
            ),
            "diagnostic_runner": (
                108_172,
                "sha256:8116987a0fa5d79f1a504d37d105311cb6f75496c1ca3921093300a9c1aba1c1",
            ),
            "diagnostic_result_tests": (
                119_143,
                "sha256:0cdd4b557e9be9e1a1c67e4b7b96a9d97ac139e768e98a45bd1aaf5c8bb35ade",
            ),
        }
        for name, relative in sorted(contract.IMPLEMENTATION_SOURCE_PATHS.items()):
            payload = (ROOT / relative).read_bytes()
            frozen = builder._git_blob_bytes(
                builder.IMPLEMENTATION_FREEZE_COMMIT, relative
            )
            self.assertEqual(payload, frozen)
            self.assertEqual(
                receipts[name],
                {
                    "path": relative,
                    "bytes": len(frozen),
                    "sha256": contract.sha256_bytes(frozen),
                    "first_parent_introduction_commit": (
                        contract.INITIAL_IMPLEMENTATION_PUBLICATION_COMMIT
                    ),
                    "freeze_commit": builder.IMPLEMENTATION_FREEZE_COMMIT,
                },
            )
            self.assertEqual(
                (receipts[name]["bytes"], receipts[name]["sha256"]), expected[name]
            )

    def test_authority_slice_and_two_stage_lineage_are_exact(self) -> None:
        expected = {
            "AI_Infra_LLM_Agent_待做任务清单.md",
            "PROJECT_STATUS.md",
            "README.md",
            contract.EXECUTION_AUTHORITY_PATH,
            "docs/MM-005-browser-research-model-evaluation-generation-failure-diagnostic-execution-authority-v2.md",
            "docs/MM-005-browser-research-model-evaluation-generation-failure-diagnostic-implementation-v2.md",
            "docs/README.md",
            "scripts/prepare_mm005_browser_research_model_evaluation_generation_failure_diagnostic_execution_authority_v2.py",
            "scripts/validate_offline.py",
            "tests/test_mm005_browser_research_model_evaluation_generation_failure_diagnostic_execution_authority_v2.py",
        }
        self.assertEqual(set(contract.EXECUTION_AUTHORITY_SLICE_PATHS), expected)
        self.assertEqual(len(contract.EXECUTION_AUTHORITY_SLICE_PATHS), 10)
        self.assertEqual(len(expected), 10)
        head = builder._git_head_commit()
        stage = builder.authority_inputs()["stage"]
        if stage["tracked_at_head"]:
            self.assertEqual(stage["freeze_commit"], head)
            builder._require_unique_parent(head, builder.IMPLEMENTATION_FREEZE_COMMIT)
            self.assertEqual(
                set(
                    builder._git_name_only_paths(
                        builder.IMPLEMENTATION_FREEZE_COMMIT, head
                    )
                ),
                expected,
            )
            self.assertEqual(
                builder._git_first_parent_introductions(
                    contract.EXECUTION_AUTHORITY_PATH
                ),
                [head],
            )
        else:
            self.assertEqual(head, builder.IMPLEMENTATION_FREEZE_COMMIT)
            self.assertIsNone(stage["freeze_commit"])

    def test_default_builder_is_exclusive_and_never_creates_parents(self) -> None:
        payload = (ROOT / contract.EXECUTION_AUTHORITY_PATH).read_bytes()
        with self.assertRaises(FileExistsError):
            builder.main([])
        self.assertEqual(
            (ROOT / contract.EXECUTION_AUTHORITY_PATH).read_bytes(), payload
        )

        source = Path(builder.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        top_level_imports = {
            alias.name.partition(".")[0]
            for node in tree.body
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        self.assertFalse(
            top_level_imports
            & {
                "PIL",
                "bitsandbytes",
                "http",
                "peft",
                "requests",
                "socket",
                "torch",
                "transformers",
                "urllib",
            }
        )
        lowered_source = source.lower()
        for forbidden in ('mode="execute"', "git lfs", "nvidia-smi"):
            self.assertNotIn(forbidden, lowered_source)
        main = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "main"
        )
        mkdir_calls = [
            node
            for node in ast.walk(main)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "mkdir"
        ]
        exclusive_opens = [
            node
            for node in ast.walk(main)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "open"
            and any(
                isinstance(argument, ast.Constant) and argument.value == "xb"
                for argument in node.args
            )
        ]
        self.assertEqual(mkdir_calls, [])
        self.assertEqual(len(exclusive_opens), 1)

        authority = json.loads(payload)
        stage = {"freeze_commit": None, "tracked_at_head": False}
        initial_snapshot = {
            "authority_output_payload": None,
            "stage": stage,
        }
        post_snapshot = {
            "authority_output_payload": payload,
            "stage": stage,
        }
        with tempfile.TemporaryDirectory() as directory:
            temporary_root = Path(directory)
            (temporary_root / "configs").mkdir()
            target = temporary_root / contract.EXECUTION_AUTHORITY_PATH
            with (
                mock.patch.object(builder, "ROOT", temporary_root),
                mock.patch.object(
                    builder,
                    "_capture_authority",
                    side_effect=[
                        (authority, initial_snapshot),
                        (authority, post_snapshot),
                    ],
                ) as capture,
                mock.patch.object(
                    builder, "_revalidate_authority_inputs"
                ) as revalidate,
                mock.patch.object(
                    builder,
                    "_git_head_commit",
                    return_value=builder.IMPLEMENTATION_FREEZE_COMMIT,
                ) as git_head,
                mock.patch.object(
                    builder, "_authority_stage_context", return_value=stage
                ) as stage_context,
                mock.patch("builtins.print"),
            ):
                self.assertEqual(builder.main([]), 0)
            self.assertEqual(target.read_bytes(), payload)
            self.assertEqual(capture.call_count, 2)
            self.assertEqual(
                [call.args[0] for call in revalidate.call_args_list],
                [initial_snapshot, post_snapshot],
            )
            git_head.assert_not_called()
            stage_context.assert_not_called()
            self.assertEqual(
                sorted(
                    path.relative_to(temporary_root).as_posix()
                    for path in temporary_root.rglob("*")
                ),
                ["configs", contract.EXECUTION_AUTHORITY_PATH],
            )

    def test_stage_and_revalidation_fail_closed_on_lineage_or_byte_drift(self) -> None:
        other = "f" * 40
        with (
            mock.patch.object(builder, "_require_no_hidden_index_flags"),
            mock.patch.object(builder, "_require_implementation_lineage"),
            mock.patch.object(builder, "_git_path_exists", return_value=False),
            self.assertRaisesRegex(RuntimeError, "exact implementation freeze HEAD"),
        ):
            builder._authority_stage_context(other)

        head = "a" * 40
        with (
            mock.patch.object(builder, "_require_no_hidden_index_flags"),
            mock.patch.object(builder, "_require_implementation_lineage"),
            mock.patch.object(builder, "_git_path_exists", return_value=True),
            mock.patch.object(
                builder, "_git_first_parent_introductions", return_value=["b" * 40]
            ),
            self.assertRaisesRegex(RuntimeError, "first introduced at current HEAD"),
        ):
            builder._authority_stage_context(head)

        expected_paths = list(contract.EXECUTION_AUTHORITY_SLICE_PATHS)
        for bad_delta in (expected_paths[:-1], [*expected_paths, "extra"]):
            with (
                self.subTest(delta_count=len(bad_delta)),
                mock.patch.object(builder, "_require_no_hidden_index_flags"),
                mock.patch.object(builder, "_require_implementation_lineage"),
                mock.patch.object(builder, "_git_path_exists", return_value=True),
                mock.patch.object(
                    builder, "_git_first_parent_introductions", return_value=[head]
                ),
                mock.patch.object(builder, "_require_unique_parent"),
                mock.patch.object(
                    builder, "_git_name_only_paths", return_value=bad_delta
                ),
                self.assertRaisesRegex(RuntimeError, "exact reviewed slice"),
            ):
                builder._authority_stage_context(head)

        with (
            mock.patch.object(builder, "_require_no_hidden_index_flags"),
            mock.patch.object(builder, "_require_implementation_lineage"),
            mock.patch.object(builder, "_git_path_exists", return_value=True),
            mock.patch.object(
                builder, "_git_first_parent_introductions", return_value=[head]
            ),
            mock.patch.object(
                builder,
                "_require_unique_parent",
                side_effect=RuntimeError("wrong parent"),
            ),
            self.assertRaisesRegex(RuntimeError, "wrong parent"),
        ):
            builder._authority_stage_context(head)

        stage = {"freeze_commit": None, "tracked_at_head": False}
        snapshot = {
            "head_commit": builder.IMPLEMENTATION_FREEZE_COMMIT,
            "stage": stage,
            "authority_output_payload": b"before",
        }
        with (
            mock.patch.object(
                builder,
                "_git_head_commit",
                return_value=builder.IMPLEMENTATION_FREEZE_COMMIT,
            ),
            mock.patch.object(builder, "_authority_stage_context", return_value=stage),
            mock.patch.object(builder.os.path, "lexists", return_value=True),
            mock.patch.object(builder, "_read_repository_file", return_value=b"after"),
            self.assertRaisesRegex(RuntimeError, "artifact changed"),
        ):
            builder._revalidate_authority_inputs(snapshot)

    def test_git_reads_disable_lfs_fsmonitor_hooks_and_ambient_git_env(self) -> None:
        completed = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=b"", stderr=b""
        )
        with (
            mock.patch.dict(
                builder.os.environ,
                {
                    "PATH": "safe-path",
                    "Git_Dir": "forbidden",
                    "gIt_Index_File": "bad",
                },
                clear=True,
            ),
            mock.patch.object(builder.subprocess, "run", return_value=completed) as run,
        ):
            self.assertIs(builder._git_process("status", "--porcelain=v1"), completed)
        command = run.call_args.args[0]
        environment = run.call_args.kwargs["env"]
        self.assertIn("core.fsmonitor=false", command)
        self.assertIn("filter.lfs.process=", command)
        self.assertIn("filter.lfs.required=false", command)
        self.assertIn(
            "core.hooksPath=NUL"
            if builder.os.name == "nt"
            else "core.hooksPath=/dev/null",
            command,
        )
        self.assertNotIn("Git_Dir", environment)
        self.assertNotIn("gIt_Index_File", environment)
        self.assertEqual(environment["GIT_LFS_SKIP_SMUDGE"], "1")
        self.assertEqual(environment["GIT_NO_LAZY_FETCH"], "1")
        command_text = " ".join(command).lower()
        for forbidden in ("lfs pull", "lfs fetch", "lfs fsck", "http", "https"):
            self.assertNotIn(forbidden, command_text)

        hidden = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=b"h PROJECT_STATUS.md\0", stderr=b""
        )
        with (
            mock.patch.object(builder, "_git_process", return_value=hidden),
            self.assertRaisesRegex(RuntimeError, "index flag is forbidden"),
        ):
            builder._require_no_hidden_index_flags()

    def test_builder_check_and_runner_plan_check_are_read_only(self) -> None:
        authority_path = ROOT / contract.EXECUTION_AUTHORITY_PATH
        before_payload = authority_path.read_bytes()
        before_topology = runner._output_topology()
        before_status = builder._git_process(
            "status", "--porcelain=v1", "--untracked-files=all"
        ).stdout
        completed = subprocess.run(
            [sys.executable, "-I", "-B", str(Path(builder.__file__)), "--check"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
        summary = json.loads(completed.stdout)
        stage = builder.authority_inputs()["stage"]
        self.assertTrue(summary["authority_frozen"])
        self.assertEqual(summary["authority_tracked_at_head"], stage["tracked_at_head"])
        self.assertEqual(summary["critical_execution_dependency_receipts"], 4)
        self.assertEqual(summary["implementation_source_receipts"], 3)
        self.assertFalse(summary["diagnostic_attempt_consumed"])
        self.assertFalse(summary["diagnostic_executed"])

        plan = runner.run(mode="plan")
        check = runner.run(mode="check")
        self.assertTrue(plan["runner_plan_valid"])
        self.assertTrue(check["implementation_check_valid"])
        self.assertTrue(plan["execution_authority_valid"])
        self.assertEqual(
            plan["execution_authority_published"], stage["tracked_at_head"]
        )
        self.assertFalse(plan["execution_path_invoked_by_gate"])
        self.assertFalse(check["execution_path_invoked_by_gate"])
        self.assertEqual(runner._output_topology(), before_topology)
        self.assertEqual(authority_path.read_bytes(), before_payload)
        self.assertEqual(
            builder._git_process(
                "status", "--porcelain=v1", "--untracked-files=all"
            ).stdout,
            before_status,
        )

    def test_runtime_output_lease_and_reserved_state_are_absent(self) -> None:
        topology = builder._require_runtime_state_absent()
        self.assertTrue(topology["execution_authority"])
        self.assertFalse(topology["output_parent"])
        for name in runner.RUNTIME_OUTPUT_KEYS:
            self.assertFalse(topology[name], name)
        self.assertEqual(protocol.OUTPUT_PARENT_PATH, "work/evaluation-runs")


if __name__ == "__main__":
    unittest.main()
