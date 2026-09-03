from __future__ import annotations

import copy
import hashlib
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import validate_repository_ci as ci

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "offline-baseline.yml"
MANUAL_WORKFLOW_PATH = (
    ROOT / ".github" / "workflows" / "manual-hydrated-lfs-integrity.yml"
)


class RepositoryCILFSMaintenanceV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = ci.INVENTORY_PATH.read_bytes()
        self.inventory = ci.load_inventory(self.payload)
        self.trust_payload = ci.TRUST_ANCHOR_PATH.read_bytes()
        self.trust = ci.load_trust_anchor(self.trust_payload)

    def test_inventory_is_canonical_and_exact(self) -> None:
        self.assertEqual(ci.canonical_json_bytes(self.inventory), self.payload)
        self.assertEqual(self.inventory, ci.expected_inventory())
        self.assertEqual(len(self.inventory["lfs_objects"]), 4)
        self.assertEqual(
            sum(item["size"] for item in self.inventory["lfs_objects"]),
            110_524_520,
        )
        self.assertEqual(
            self.inventory["pointer_gate"]["scope"],
            "pointer_and_stdlib_only",
        )
        self.assertFalse(self.inventory["pointer_gate"]["full_integrity_verified"])
        self.assertEqual(self.inventory["pointer_gate"]["lfs_payloads_read"], 0)

    def test_inventory_oid_size_and_cardinality_drift_fail_closed(self) -> None:
        changed_size = copy.deepcopy(self.inventory)
        changed_size["lfs_objects"][0]["size"] += 1
        changed_oid = copy.deepcopy(self.inventory)
        changed_oid["lfs_objects"][0]["oid"] = "sha256:" + "0" * 64
        changed_total = copy.deepcopy(self.inventory)
        changed_total["total_lfs_payload_bytes"] += 1
        missing_object = copy.deepcopy(self.inventory)
        missing_object["lfs_objects"].pop()
        extra_object = copy.deepcopy(self.inventory)
        extra_object["lfs_objects"].append(
            {
                "oid": "sha256:" + "0" * 64,
                "path": "baseline/unregistered.bin",
                "pointer_bytes": 133,
                "pointer_git_blob_oid": "sha1:" + "0" * 40,
                "size": 1,
            }
        )
        for name, changed in (
            ("size", changed_size),
            ("oid", changed_oid),
            ("total", changed_total),
            ("missing", missing_object),
            ("extra", extra_object),
        ):
            with (
                self.subTest(name=name),
                self.assertRaises(ci.RepositoryCIValidationError) as caught,
            ):
                ci.load_inventory(ci.canonical_json_bytes(changed))
            self.assertEqual(caught.exception.code, "INVENTORY_MISMATCH")

    def test_duplicate_inventory_key_fails_closed(self) -> None:
        with self.assertRaises(ci.RepositoryCIValidationError) as caught:
            ci.load_inventory(b'{"schema_version":1,"schema_version":1}\n')
        self.assertEqual(caught.exception.code, "INVENTORY_DUPLICATE_KEY")

    def test_trust_anchor_contract_is_canonical_exact_and_truthful(self) -> None:
        self.assertEqual(ci.canonical_json_bytes(self.trust), self.trust_payload)
        self.assertEqual(self.trust, ci.expected_trust_anchor())
        automatic = self.trust["automatic_gate"]
        self.assertTrue(automatic["content_identity_inherited"])
        self.assertFalse(automatic["current_hydration_verified"])
        self.assertFalse(automatic["current_payload_integrity_verified"])
        self.assertFalse(automatic["full_integrity_verified"])
        self.assertFalse(automatic["remote_availability_verified"])
        self.assertEqual(automatic["lfs_payload_bytes_read"], 0)
        anchor = self.trust["trust_anchor"]
        self.assertEqual(anchor["commit"], ci.TRUST_ANCHOR_COMMIT)
        self.assertEqual(anchor["tree"], ci.TRUST_ANCHOR_TREE)
        self.assertEqual(anchor["workflow_run_id"], 33_501_136_645)
        self.assertEqual(anchor["hydrated_job_id"], 99_834_499_141)

    def test_trust_anchor_contract_drift_and_duplicate_key_fail_closed(self) -> None:
        changed = copy.deepcopy(self.trust)
        changed["automatic_gate"]["remote_availability_verified"] = True
        with self.assertRaises(ci.RepositoryCIValidationError) as caught:
            ci.load_trust_anchor(ci.canonical_json_bytes(changed))
        self.assertEqual(caught.exception.code, "TRUST_ANCHOR_CONTRACT_MISMATCH")

        with self.assertRaises(ci.RepositoryCIValidationError) as caught:
            ci.load_trust_anchor(b'{"schema_version":1,"schema_version":1}\n')
        self.assertEqual(caught.exception.code, "DUPLICATE_KEY")

    def test_head_blobs_and_gitattributes_match_the_frozen_inventory(self) -> None:
        head = ci.validate_git_metadata(self.inventory)
        self.assertRegex(head, r"^[0-9a-f]{40}$")
        for item in self.inventory["lfs_objects"]:
            pointer = ci.lfs_pointer_bytes(item)
            self.assertEqual(len(pointer), 133)
            self.assertEqual(ci.git_blob_oid(pointer), item["pointer_git_blob_oid"])

    def test_current_head_inherits_the_exact_hydrated_anchor(self) -> None:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        inherited = ci.validate_trust_anchor(self.trust, current_head=head)
        self.assertEqual(inherited["trust_anchor_commit"], ci.TRUST_ANCHOR_COMMIT)
        self.assertEqual(inherited["trust_anchor_tree"], ci.TRUST_ANCHOR_TREE)
        self.assertTrue(inherited["content_identity_inherited"])
        self.assertTrue(inherited["protected_lfs_paths_unchanged"])
        self.assertFalse(inherited["current_hydration_verified"])
        self.assertFalse(inherited["remote_availability_verified"])
        self.assertEqual(inherited["lfs_payload_bytes_read"], 0)

    def test_lfs_control_path_additions_fail_closed(self) -> None:
        self.assertEqual(
            ci.validate_lfs_control_paths((".gitattributes", "README.md")),
            (".gitattributes",),
        )
        for paths, code in (
            (
                (".gitattributes", "nested/.gitattributes"),
                "GITATTRIBUTES_PATH_SET_DRIFT",
            ),
            ((".gitattributes", ".lfsconfig"), "LFS_CONFIG_FORBIDDEN"),
            ((".gitattributes", "nested/.LFSCONFIG"), "LFS_CONFIG_FORBIDDEN"),
        ):
            with (
                self.subTest(paths=paths),
                self.assertRaises(ci.RepositoryCIValidationError) as caught,
            ):
                ci.validate_lfs_control_paths(paths)
            self.assertEqual(caught.exception.code, code)

    def test_anchor_ancestry_tree_and_protected_drift_fail_closed(self) -> None:
        def anchor_git(*arguments: str, input_payload: bytes | None = None) -> bytes:
            del input_payload
            if arguments[:2] == ("cat-file", "-t"):
                return b"commit\n"
            if arguments[:2] == ("rev-parse", f"{ci.TRUST_ANCHOR_COMMIT}^{{tree}}"):
                return (ci.TRUST_ANCHOR_TREE + "\n").encode("ascii")
            self.fail(f"unexpected git call: {arguments}")

        tracked = (".gitattributes", "README.md")
        scenarios = (
            ("ancestor", (1,), "TRUST_ANCHOR_NOT_ANCESTOR"),
            ("protected", (0, 1), "PROTECTED_LFS_PATH_DRIFT"),
        )
        for name, exit_codes, expected_code in scenarios:
            with (
                self.subTest(name=name),
                mock.patch.object(ci, "_run_git", side_effect=anchor_git),
                mock.patch.object(ci, "_tracked_paths", return_value=tracked),
                mock.patch.object(ci, "_git_exit_code", side_effect=exit_codes),
                self.assertRaises(ci.RepositoryCIValidationError) as caught,
            ):
                ci.validate_trust_anchor(self.trust, current_head="f" * 40)
            self.assertEqual(caught.exception.code, expected_code)

        wrong_tree_git = mock.Mock(side_effect=(b"commit\n", b"0" * 40 + b"\n"))
        with (
            mock.patch.object(ci, "_run_git", wrong_tree_git),
            self.assertRaises(ci.RepositoryCIValidationError) as caught,
        ):
            ci.validate_trust_anchor(self.trust, current_head="f" * 40)
        self.assertEqual(caught.exception.code, "TRUST_ANCHOR_TREE_MISMATCH")

    def test_diagnostic_v2_focused_topology_is_zero_or_complete(self) -> None:
        state, modules, count = ci.diagnostic_v2_test_plan(("README.md",))
        self.assertEqual(state, "protocol_only")
        self.assertEqual(modules, (ci.DIAGNOSTIC_V2_PROTOCOL_TEST_MODULE,))
        self.assertEqual(count, 18)

        complete = tuple(sorted(("README.md", *ci.DIAGNOSTIC_V2_IMPLEMENTATION_PATHS)))
        state, modules, count = ci.diagnostic_v2_test_plan(complete)
        self.assertEqual(state, "implementation_complete")
        self.assertEqual(
            modules,
            (
                ci.DIAGNOSTIC_V2_PROTOCOL_TEST_MODULE,
                ci.DIAGNOSTIC_V2_RESULT_TEST_MODULE,
            ),
        )
        self.assertEqual(
            self.trust["diagnostic_v2_focused_gate"][
                "implementation_protocol_test_count"
            ],
            19,
        )
        self.assertEqual(count, 62)

        for relative in ci.DIAGNOSTIC_V2_IMPLEMENTATION_PATHS:
            with (
                self.subTest(relative=relative),
                self.assertRaises(ci.RepositoryCIValidationError) as caught,
            ):
                ci.diagnostic_v2_test_plan((relative,))
            self.assertEqual(
                caught.exception.code,
                "DIAGNOSTIC_V2_IMPLEMENTATION_TOPOLOGY_PARTIAL",
            )

    def test_real_git_metadata_rejects_extra_lfs_path_and_head_pointer_drift(
        self,
    ) -> None:
        def git(repository: Path, *arguments: str) -> bytes:
            completed = subprocess.run(
                [
                    "git",
                    "-c",
                    "user.name=Repository CI Test",
                    "-c",
                    "user.email=repository-ci@example.invalid",
                    *arguments,
                ],
                cwd=repository,
                check=False,
                capture_output=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr.decode())
            return completed.stdout

        def index_payload(repository: Path, relative: str, payload: bytes) -> None:
            path = repository.joinpath(*relative.split("/"))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
            oid = git(repository, "hash-object", "-w", "--", relative).decode().strip()
            git(
                repository,
                "update-index",
                "--add",
                "--cacheinfo",
                f"100644,{oid},{relative}",
            )

        with tempfile.TemporaryDirectory() as temporary:
            repository = Path(temporary) / "repository"
            repository.mkdir()
            git(repository, "init", "--initial-branch=master")
            index_payload(repository, ".gitattributes", ci._git_blob(".gitattributes"))
            for item in self.inventory["lfs_objects"]:
                index_payload(repository, item["path"], ci.lfs_pointer_bytes(item))
            git(repository, "commit", "-m", "exact inventory")

            with mock.patch.object(ci, "ROOT", repository):
                ci.validate_git_metadata(self.inventory)

                extra = "baseline/adapters/extra/adapter_model.safetensors"
                index_payload(
                    repository,
                    extra,
                    ci.lfs_pointer_bytes(self.inventory["lfs_objects"][0]),
                )
                git(repository, "commit", "-m", "add unregistered LFS path")
                with self.assertRaises(ci.RepositoryCIValidationError) as caught:
                    ci.validate_git_metadata(self.inventory)
                self.assertEqual(
                    caught.exception.code,
                    "LFS_TRACKED_PATH_INVENTORY_MISMATCH",
                )

                git(repository, "update-index", "--force-remove", "--", extra)
                git(repository, "commit", "-m", "remove unregistered LFS path")
                item = self.inventory["lfs_objects"][0]
                drift = ci.lfs_pointer_bytes(item).replace(b"sha256:", b"sha257:", 1)
                index_payload(repository, item["path"], drift)
                git(repository, "commit", "-m", "drift pointer blob")
                with self.assertRaises(ci.RepositoryCIValidationError) as caught:
                    ci.validate_git_metadata(self.inventory)
                self.assertEqual(caught.exception.code, "LFS_POINTER_MISMATCH")

    def test_pointer_mode_reads_only_canonical_pointer_bytes(self) -> None:
        item = dict(self.inventory["lfs_objects"][0])
        local_inventory = {"lfs_objects": [item]}
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "pointer"
            pointer = ci.lfs_pointer_bytes(item)
            path.write_bytes(pointer)
            with mock.patch.object(ci, "_safe_relative_path", return_value=path):
                self.assertEqual(
                    ci.validate_pointer_worktree(local_inventory), len(pointer)
                )

            path.write_bytes(pointer.replace(b"sha256:", b"sha257:", 1))
            with (
                mock.patch.object(ci, "_safe_relative_path", return_value=path),
                self.assertRaises(ci.RepositoryCIValidationError) as caught,
            ):
                ci.validate_pointer_worktree(local_inventory)
            self.assertEqual(caught.exception.code, "WORKTREE_POINTER_MISMATCH")

            path.write_bytes(b"hydrated-payload")
            with (
                mock.patch.object(ci, "_safe_relative_path", return_value=path),
                self.assertRaises(ci.RepositoryCIValidationError) as caught,
            ):
                ci.validate_pointer_worktree(local_inventory)
            self.assertEqual(caught.exception.code, "HYDRATED_PAYLOAD_FORBIDDEN")

    def test_hydrated_mode_hashes_the_registered_payload(self) -> None:
        payload = b"registered-hydrated-payload"
        item = {
            "oid": "sha256:" + hashlib.sha256(payload).hexdigest(),
            "path": "payload.bin",
            "size": len(payload),
        }
        local_inventory = {
            "lfs_objects": [item],
            "total_lfs_payload_bytes": len(payload),
        }
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "payload"
            path.write_bytes(payload)
            with mock.patch.object(ci, "_safe_relative_path", return_value=path):
                self.assertEqual(
                    ci.validate_hydrated_worktree(local_inventory),
                    (1, len(payload)),
                )

            path.write_bytes(payload + b"drift")
            with (
                mock.patch.object(ci, "_safe_relative_path", return_value=path),
                self.assertRaises(ci.RepositoryCIValidationError) as caught,
            ):
                ci.validate_hydrated_worktree(local_inventory)
            self.assertEqual(caught.exception.code, "LFS_PAYLOAD_SIZE_MISMATCH")

            path.write_bytes(bytes([payload[0] ^ 1]) + payload[1:])
            with (
                mock.patch.object(ci, "_safe_relative_path", return_value=path),
                self.assertRaises(ci.RepositoryCIValidationError) as caught,
            ):
                ci.validate_hydrated_worktree(local_inventory)
            self.assertEqual(caught.exception.code, "LFS_PAYLOAD_DIGEST_MISMATCH")

    def test_core_test_child_import_uses_exact_src_path_and_restores_env(self) -> None:
        inherited = "untrusted-inherited-path"
        with mock.patch.dict(os.environ, {"PYTHONPATH": inherited}, clear=False):
            with ci._core_test_subprocess_environment():
                self.assertEqual(os.environ["PYTHONPATH"], str(ci.SRC))
                child = subprocess.run(
                    [sys.executable, "-c", "import fullcycle_bridge"],
                    cwd=ROOT,
                    check=False,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(child.returncode, 0, child.stderr)
            self.assertEqual(os.environ["PYTHONPATH"], inherited)

    def test_pointer_main_revalidates_after_core_suite(self) -> None:
        with (
            mock.patch.object(ci, "load_inventory", return_value=self.inventory),
            mock.patch.object(ci, "validate_git_metadata", return_value="0" * 40),
            mock.patch.object(ci, "compile_tracked_python", return_value=231),
            mock.patch.object(ci, "run_core_tests", return_value=(107, 3)),
            mock.patch.object(ci, "canonical_json_bytes", return_value=b"{}\n"),
            mock.patch.object(ci.sys, "stdout", mock.Mock()),
            mock.patch.object(
                ci,
                "validate_pointer_worktree",
                side_effect=(532, 532),
            ) as validate_pointers,
        ):
            self.assertEqual(ci.main(["--mode", "pointer"]), 0)
        self.assertEqual(validate_pointers.call_count, 2)

        with (
            mock.patch.object(ci, "load_inventory", return_value=self.inventory),
            mock.patch.object(ci, "validate_git_metadata", return_value="0" * 40),
            mock.patch.object(ci, "compile_tracked_python", return_value=231),
            mock.patch.object(ci, "run_core_tests", return_value=(107, 3)),
            mock.patch.object(
                ci,
                "validate_pointer_worktree",
                side_effect=(532, 531),
            ),
            self.assertRaises(ci.RepositoryCIValidationError) as caught,
        ):
            ci.main(["--mode", "pointer"])
        self.assertEqual(caught.exception.code, "POINTER_BYTE_COUNT_DRIFT")

    def test_windows_and_noncanonical_paths_fail_closed(self) -> None:
        for relative in (
            "../escape",
            "..\\escape",
            "C:\\escape",
            "C:/escape",
            "/absolute",
            "./relative",
            "nested//path",
            "nested/../escape",
        ):
            with (
                self.subTest(relative=relative),
                self.assertRaises(ci.RepositoryCIValidationError),
            ):
                ci._safe_relative_path(relative)

    def test_resolved_symlink_escape_fails_closed_when_supported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            root = parent / "root"
            outside = parent / "outside"
            root.mkdir()
            outside.mkdir()
            link = root / "link"
            try:
                link.symlink_to(outside, target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"symlink creation unavailable: {exc}")
            with (
                mock.patch.object(ci, "ROOT", root),
                self.assertRaises(ci.RepositoryCIValidationError) as caught,
            ):
                ci._safe_relative_path("link/payload.bin")
            self.assertEqual(caught.exception.code, "REPOSITORY_PATH_ESCAPE")

    def test_automatic_workflow_is_zero_bandwidth_and_preserves_contexts(self) -> None:
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn(
            "on:\n  push:\n    branches:\n      - master\n"
            "  pull_request:\n    branches:\n      - master\n",
            workflow,
        )
        self.assertIn("cancel-in-progress: true", workflow)
        self.assertIn("fail-fast: false", workflow)
        self.assertNotIn("workflow_dispatch", workflow)
        self.assertEqual(
            re.findall(r'^          - "(3\.[0-9]+)"$', workflow, flags=re.MULTILINE),
            ["3.11", "3.12", "3.13"],
        )
        for forbidden_key in (
            "paths",
            "paths-ignore",
            "needs",
            "if",
            "continue-on-error",
        ):
            self.assertNotRegex(
                workflow,
                rf"(?m)^\s*{re.escape(forbidden_key)}:\s*",
            )
        self.assertIn(
            "group: ${{ github.workflow }}-"
            "${{ github.event.pull_request.number || github.ref }}",
            workflow,
        )
        self.assertIn("name: python-matrix (${{ matrix.python-version }})", workflow)
        self.assertIn("name: hydrated-lfs-integrity", workflow)
        self.assertEqual(workflow.count("timeout-minutes: 15"), 2)
        self.assertNotIn("timeout-minutes: 30", workflow)
        self.assertEqual(workflow.count("fetch-depth: 0"), 2)
        self.assertEqual(workflow.count("lfs: false"), 2)
        self.assertEqual(workflow.count('GIT_LFS_SKIP_SMUDGE: "1"'), 2)
        self.assertNotIn("lfs: true", workflow)
        for forbidden in (
            "git lfs pull",
            "git lfs fsck",
            "--mode hydrated-lfs",
            "scripts/validate_offline.py",
        ):
            self.assertNotIn(forbidden, workflow)

        pointer_job, inherited_job = workflow.split(
            "\n  hydrated-lfs-integrity:\n", maxsplit=1
        )
        self.assertIn(
            "python -I scripts/validate_repository_ci.py --mode pointer",
            pointer_job,
        )
        self.assertIn(
            "python -I scripts/validate_repository_ci.py --mode diagnostic-v2-focused",
            pointer_job,
        )
        self.assertIn(
            "python -I scripts/validate_repository_ci.py --mode trusted-anchor",
            inherited_job,
        )

    def test_manual_workflow_is_explicit_exact_and_context_separate(self) -> None:
        workflow = MANUAL_WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("on:\n  workflow_dispatch:\n", workflow)
        self.assertNotRegex(workflow, r"(?m)^  (push|pull_request):")
        self.assertIn("name: manual-hydrated-lfs-integrity", workflow)
        self.assertNotIn("\n    name: hydrated-lfs-integrity\n", workflow)
        self.assertIn("cancel-in-progress: false", workflow)
        self.assertNotRegex(workflow, r"(?m)^\s*if:\s*")
        self.assertGreaterEqual(workflow.count(ci.MANUAL_LFS_ACKNOWLEDGEMENT), 2)
        self.assertEqual(workflow.count('GIT_LFS_SKIP_SMUDGE: "1"'), 1)
        checkout_step, hydration_step = workflow.split(
            "      - name: Hydrate and fsck the exact LFS inventory\n", maxsplit=1
        )
        self.assertIn('GIT_LFS_SKIP_SMUDGE: "1"', checkout_step)
        self.assertNotIn("GIT_LFS_SKIP_SMUDGE", hydration_step)

        include = ",".join(self.inventory["hydrated_gate"]["lfs_include_paths"])
        pull = f"git lfs pull origin --include=\"{include}\" --exclude=''"
        fsck = "git lfs fsck --objects --pointers HEAD"
        pointer_preflight = (
            "python -I scripts/validate_repository_ci.py --mode pointer-metadata"
        )
        hydrated_validation = (
            "python -I scripts/validate_repository_ci.py --mode hydrated-lfs"
        )
        complete_validation = "python -I scripts/validate_offline.py"
        for step in (
            "Require exact LFS bandwidth acknowledgement",
            "Checkout pointer-only repository",
            "Set up Python 3.11",
            pointer_preflight,
            pull,
            fsck,
            hydrated_validation,
            complete_validation,
        ):
            self.assertIn(step, workflow)
        positions = [
            workflow.index(step)
            for step in (
                "Require exact LFS bandwidth acknowledgement",
                "Checkout pointer-only repository",
                "Set up Python 3.11",
                pointer_preflight,
                pull,
                fsck,
                hydrated_validation,
                complete_validation,
            )
        ]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(workflow.count(pull), 1)
        self.assertEqual(workflow.count(fsck), 1)
        self.assertEqual(workflow.count(hydrated_validation), 1)
        self.assertEqual(workflow.count(complete_validation), 1)

    def test_workflow_actions_are_immutable_node24_sha_pins(self) -> None:
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        manual = MANUAL_WORKFLOW_PATH.read_text(encoding="utf-8")
        combined = workflow + manual
        checkout = "actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803"
        setup = "actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1"
        self.assertEqual(combined.count(checkout), 3)
        self.assertEqual(combined.count(setup), 3)
        uses = re.findall(r"uses: ([^\s#]+)", combined)
        self.assertEqual(len(uses), 6)
        self.assertTrue(all(re.search(r"@[0-9a-f]{40}$", item) for item in uses))
        self.assertNotIn("actions/checkout@v4", combined)
        self.assertNotIn("actions/setup-python@v5", combined)


if __name__ == "__main__":
    unittest.main()
