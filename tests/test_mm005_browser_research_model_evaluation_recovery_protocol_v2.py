from __future__ import annotations

import ast
import copy
import os
import subprocess
import sys
import tempfile
import unittest
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SRC))

from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_model_evaluation_protocol_v2 as contract,
)
from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_model_evaluation_recovery_io as recovery_io,
)
from scripts import (  # noqa: E402
    prepare_mm005_browser_research_model_evaluation_v2 as builder,
)
from scripts import (  # noqa: E402
    recover_mm005_browser_research_model_evaluation_v2 as terminalizer,
)
from scripts import (  # noqa: E402
    run_mm005_browser_research_model_evaluation_v2 as runner,
)


LOCKED_V1_RECEIPTS = (
    {
        "path": "configs/mm005_browser_research_model_evaluation_protocol_v1.json",
        "bytes": 116_152,
        "sha256": (
            "sha256:84cd3d20d5a678a8ad0f7c38ad12e057225a4250e8143c5f004c2eaef8981f3f"
        ),
    },
    {
        "path": "baseline/mm005-browser-research-model-eval-v1-attempt-owner.json",
        "bytes": 649,
        "sha256": (
            "sha256:c5649806987521be26304e6abf81d545ab2522d71289d700d2c49305828b9ca6"
        ),
    },
    {
        "path": (
            "baseline/mm005-browser-research-model-eval-v1-failure-classification.json"
        ),
        "bytes": 11_936,
        "sha256": (
            "sha256:628f9a24267c292d318ca279eb0642c72fbc705b1211629ef8b9edf6318e6e11"
        ),
    },
)


def _value_at(value: Mapping[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = value
    for segment in path:
        current = current[segment]
    return current


def _set_at(value: dict[str, Any], path: tuple[str, ...], replacement: Any) -> None:
    current = value
    for segment in path[:-1]:
        current = current[segment]
    current[path[-1]] = replacement


def _call_name(value: ast.expr) -> str:
    if isinstance(value, ast.Name):
        return value.id
    if isinstance(value, ast.Attribute):
        prefix = _call_name(value.value)
        return f"{prefix}.{value.attr}" if prefix else value.attr
    return ""


def _function_node(tree: ast.Module, name: str) -> ast.FunctionDef:
    matches = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == name
    ]
    if len(matches) != 1:
        raise AssertionError(f"expected one function named {name}")
    return matches[0]


class MM005BrowserResearchRecoveryProtocolV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.protocol_inputs = builder.protocol_inputs(freeze_output_absent=True)
        cls.v1_preregistration = cls.protocol_inputs["v1_preregistration"]
        cls.preregistration = contract.expected_preregistration(
            freeze_status="frozen", **cls.protocol_inputs
        )
        cls.preregistration_payload = contract.artifact_json_bytes(cls.preregistration)
        cls.protocol_freeze_commit = "a" * 40
        cls.attempt_id = "b" * 64
        cls.attempt_owner = contract.build_attempt_owner(
            protocol_freeze_commit=cls.protocol_freeze_commit,
            preregistration_payload=cls.preregistration_payload,
            attempt_id=cls.attempt_id,
        )
        cls.attempt_owner_payload = contract.artifact_json_bytes(cls.attempt_owner)
        cls.initial_counters = {
            name: 0 for name in contract.expected_execution_counters()
        }
        cls.initial_counters["run_attempts"] = 1
        cls.initial_event = contract.build_progress_event(
            previous_journal_payload=b"",
            protocol_freeze_commit=cls.protocol_freeze_commit,
            preregistration_payload=cls.preregistration_payload,
            attempt_owner_payload=cls.attempt_owner_payload,
            event="attempt_claimed",
            counters=cls.initial_counters,
            completed_record_ids=[],
        )
        cls.initial_journal = contract.artifact_json_bytes(cls.initial_event)
        cls.v1_payloads_before = {
            str(receipt["path"]): (ROOT / str(receipt["path"])).read_bytes()
            for receipt in LOCKED_V1_RECEIPTS
        }

    @classmethod
    def tearDownClass(cls) -> None:
        observed = {path: (ROOT / path).read_bytes() for path in cls.v1_payloads_before}
        if observed != cls.v1_payloads_before:
            raise AssertionError("a model-free v2 test changed locked v1 evidence")

    def _validate_delta(
        self,
        candidate: Mapping[str, Any],
        *,
        base: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        return contract.validate_recovery_delta(
            self.v1_preregistration if base is None else base,
            candidate,
            source_receipts=self.protocol_inputs["source_receipts"],
            recovery_lineage=self.preregistration["source_lineage"]["recovery_lineage"],
        )

    def _validate_journal(self, payload: bytes) -> list[dict[str, Any]]:
        return contract.validate_progress_journal(
            payload,
            protocol_freeze_commit=self.protocol_freeze_commit,
            preregistration_payload=self.preregistration_payload,
            attempt_owner_payload=self.attempt_owner_payload,
        )

    def _screenshot_count(self, record_id: str) -> int:
        registry = self.preregistration["input_suite"]["prompt_projection_registry"]
        matching = [item for item in registry if item.get("record_id") == record_id]
        self.assertEqual(len(matching), 1)
        return len(matching[0]["screenshot_payloads"])

    def _append_event(
        self,
        journal: bytes,
        *,
        event: str,
        counters: Mapping[str, Any],
        completed_record_ids: list[str],
        record_id: str | None = None,
    ) -> bytes:
        value = contract.build_progress_event(
            previous_journal_payload=journal,
            protocol_freeze_commit=self.protocol_freeze_commit,
            preregistration_payload=self.preregistration_payload,
            attempt_owner_payload=self.attempt_owner_payload,
            event=event,
            counters=counters,
            completed_record_ids=completed_record_ids,
            record_id=record_id,
        )
        return journal + contract.artifact_json_bytes(value)

    def _journal_through_first_generation(self) -> bytes:
        counters = copy.deepcopy(self.initial_counters)
        journal = self._append_event(
            self.initial_journal,
            event="context_preflight_completed",
            counters=counters,
            completed_record_ids=[],
        )
        counters["fresh_base_load_attempts"] = 1
        journal = self._append_event(
            journal,
            event="base_load_started",
            counters=counters,
            completed_record_ids=[],
        )
        counters["fresh_base_loads"] = 1
        journal = self._append_event(
            journal,
            event="base_load_completed",
            counters=counters,
            completed_record_ids=[],
        )
        counters["independent_adapter_load_attempts"] = 1
        journal = self._append_event(
            journal,
            event="adapter_load_started",
            counters=counters,
            completed_record_ids=[],
        )
        counters["independent_adapter_loads"] = 1
        journal = self._append_event(
            journal,
            event="adapter_load_completed",
            counters=counters,
            completed_record_ids=[],
        )
        record_id = self.preregistration["input_suite"]["case_order"][0]
        counters["generate_attempts"] = 1
        counters["screenshot_inputs"] = self._screenshot_count(record_id)
        journal = self._append_event(
            journal,
            event="generation_started",
            counters=counters,
            completed_record_ids=[],
            record_id=record_id,
        )
        counters["generate_calls"] = 1
        return self._append_event(
            journal,
            event="generation_completed",
            counters=counters,
            completed_record_ids=[record_id],
            record_id=record_id,
        )

    def _mutate_last_event(
        self, payload: bytes, mutation: Callable[[dict[str, Any]], None]
    ) -> bytes:
        lines = payload.splitlines(keepends=True)
        event = contract.parse_strict_json_bytes(
            lines[-1], location="$.test.last_event"
        )
        mutation(event)
        lines[-1] = contract.artifact_json_bytes(event)
        return b"".join(lines)

    def test_preregistration_recomputes_and_delta_is_strictly_closed(self) -> None:
        self.assertEqual(
            contract.validate_preregistration(
                self.preregistration, **self.protocol_inputs
            ),
            self.preregistration,
        )
        report = self._validate_delta(self.preregistration)
        self.assertTrue(report["arrays_compared_atomically"])
        self.assertEqual(
            set(report["exact_value_replacements"]),
            {".".join(path) for path in contract.ALLOWED_VALUE_REPLACEMENTS},
        )
        self.assertEqual(
            set(report["added_protocol_sources"]),
            set(contract.V2_PROTOCOL_SOURCE_KEYS),
        )
        self.assertEqual(
            set(report["preserved_protocol_sources"]),
            set(contract.V1_PROTOCOL_SOURCE_KEYS),
        )

        for path, required in contract.ALLOWED_VALUE_REPLACEMENTS.items():
            with self.subTest(path=".".join(path)):
                self.assertEqual(_value_at(self.preregistration, path), required)
                changed = copy.deepcopy(self.preregistration)
                if isinstance(required, list):
                    wrong: Any = list(reversed(required))
                elif type(required) is int:
                    wrong = required + 1
                else:
                    wrong = f"{required}-tampered"
                _set_at(changed, path, wrong)
                with self.assertRaises(contract.MM005BrowserResearchRecoveryError):
                    self._validate_delta(changed)

    def test_delta_rejects_array_type_and_signed_zero_drift(self) -> None:
        mutations: list[tuple[str, dict[str, Any]]] = []
        changed = copy.deepcopy(self.preregistration)
        changed["input_suite"]["case_order"][0:2] = reversed(
            changed["input_suite"]["case_order"][0:2]
        )
        mutations.append(("preserved array order", changed))
        changed = copy.deepcopy(self.preregistration)
        changed["authority_contract"]["model_output_has_execution_authority"] = 0
        mutations.append(("false to zero", changed))
        changed = copy.deepcopy(self.preregistration)
        changed["mm005_browser_research_model_evaluation_protocol_version"] = 2.0
        mutations.append(("required int to float", changed))
        changed = copy.deepcopy(self.preregistration)
        changed["execution_protocol"]["adapter_writes"] = 0.0
        mutations.append(("preserved int to float", changed))
        for label, candidate in mutations:
            with self.subTest(label=label):
                with self.assertRaises(contract.MM005BrowserResearchRecoveryError):
                    self._validate_delta(candidate)

        signed_zero_base = copy.deepcopy(self.v1_preregistration)
        signed_zero_candidate = copy.deepcopy(self.preregistration)
        signed_zero_base["resource_caps"]["elapsed_seconds"] = 0.0
        signed_zero_candidate["resource_caps"]["elapsed_seconds"] = -0.0
        with self.assertRaises(contract.MM005BrowserResearchRecoveryError):
            self._validate_delta(signed_zero_candidate, base=signed_zero_base)

    def test_lineage_payloads_are_exact_and_base_cannot_be_self_attested(self) -> None:
        payloads = {
            "v1_preregistration_payload": self.protocol_inputs[
                "v1_preregistration_payload"
            ],
            "v1_attempt_owner_payload": self.protocol_inputs[
                "v1_attempt_owner_payload"
            ],
            "v1_failure_classification_payload": self.protocol_inputs[
                "v1_failure_classification_payload"
            ],
        }
        validated = contract.validate_recovery_lineage_payloads(**payloads)
        self.assertEqual(validated["v1_preregistration"], self.v1_preregistration)
        contract.validate_failure_classification_recovery_policy(
            validated["v1_failure_classification"]
        )
        for name, payload in payloads.items():
            with self.subTest(payload=name):
                changed = dict(payloads)
                changed[name] = bytes([payload[0] ^ 1]) + payload[1:]
                with self.assertRaises(
                    contract.MM005BrowserResearchRecoveryError
                ) as raised:
                    contract.validate_recovery_lineage_payloads(**changed)
                self.assertEqual(
                    raised.exception.code, "RECOVERY_LINEAGE_RECEIPT_MISMATCH"
                )

        changed_base = copy.deepcopy(self.v1_preregistration)
        changed_base["candidate"]["model_revision"] = "self-attested-drift"
        changed_inputs = dict(self.protocol_inputs)
        changed_inputs["v1_preregistration"] = changed_base
        with self.assertRaises(contract.MM005BrowserResearchRecoveryError):
            contract.expected_preregistration(freeze_status="frozen", **changed_inputs)

    def test_source_receipt_closure_rejects_drift_removal_extra_and_width(self) -> None:
        observed = builder.source_receipts(self.v1_preregistration)
        self.assertEqual(observed, self.protocol_inputs["source_receipts"])
        self.assertEqual(set(observed), set(contract.PROTOCOL_SOURCE_PATHS))
        for name, relative in contract.PROTOCOL_SOURCE_PATHS.items():
            payload = (ROOT / relative).read_bytes()
            self.assertEqual(
                observed[name],
                {
                    "path": relative,
                    "bytes": len(payload),
                    "sha256": contract.sha256_bytes(payload),
                },
            )

        added_source = contract.V2_PROTOCOL_SOURCE_KEYS[0]
        source_mutations: list[tuple[str, dict[str, Any]]] = []
        changed = copy.deepcopy(self.preregistration)
        changed["source_receipts"][added_source]["sha256"] = "sha256:" + "0" * 64
        source_mutations.append(("new source digest drift", changed))
        changed = copy.deepcopy(self.preregistration)
        del changed["source_receipts"][added_source]
        source_mutations.append(("source removal", changed))
        changed = copy.deepcopy(self.preregistration)
        changed["source_receipts"]["unregistered_source"] = {
            "path": "src/unregistered.py",
            "bytes": 0,
            "sha256": "sha256:" + "0" * 64,
        }
        source_mutations.append(("extra source", changed))
        changed = copy.deepcopy(self.preregistration)
        changed["source_receipts"][added_source]["extra"] = True
        source_mutations.append(("wide receipt", changed))
        for label, candidate in source_mutations:
            with self.subTest(label=label):
                with self.assertRaises(contract.MM005BrowserResearchRecoveryError):
                    self._validate_delta(candidate)

        changed_inputs = dict(self.protocol_inputs)
        changed_receipts = copy.deepcopy(self.protocol_inputs["source_receipts"])
        changed_receipts[contract.V1_PROTOCOL_SOURCE_KEYS[0]]["bytes"] += 1
        changed_inputs["source_receipts"] = changed_receipts
        with self.assertRaises(contract.MM005BrowserResearchRecoveryError):
            contract.expected_preregistration(freeze_status="frozen", **changed_inputs)

    def test_builder_uses_cat_file_blob_and_never_a_git_show_command(self) -> None:
        completed = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=b"frozen blob", stderr=b""
        )
        with mock.patch.object(
            builder.subprocess, "run", return_value=completed
        ) as run:
            self.assertEqual(
                builder._git_blob_bytes("c" * 40, "configs/frozen.json"),
                b"frozen blob",
            )
        command = run.call_args.args[0]
        self.assertEqual(command[:3], ["git", "cat-file", "blob"])
        self.assertNotIn("show", command)
        self.assertEqual(
            contract.FREEZE_BLOB_READER["command"],
            "git cat-file blob <commit>:<path>",
        )
        source = (
            ROOT / "scripts/prepare_mm005_browser_research_model_evaluation_v2.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn('"git", "show"', source)
        self.assertNotIn("git show", source)

    def test_lifecycle_lease_marker_path_and_protocol_section_are_closed(self) -> None:
        self.assertEqual(
            contract.LIFECYCLE_LEASE_ROOT,
            f"{contract.RUN_OUTPUT_ROOT}.lifecycle",
        )
        self.assertEqual(
            contract.LIFECYCLE_LEASE_PATH,
            f"{contract.LIFECYCLE_LEASE_ROOT}/lease",
        )
        self.assertEqual(
            contract.LIFECYCLE_LEASE_MARKER,
            b"MM-005-browser-research-model-evaluation-recovery-lifecycle-v1\n",
        )
        self.assertEqual(
            contract.DURABLE_RECOVERY_CONTRACT["lifecycle_lease_path"],
            contract.LIFECYCLE_LEASE_PATH,
        )
        self.assertTrue(
            contract.DURABLE_RECOVERY_CONTRACT[
                "lifecycle_lease_acquired_before_attempt_claim"
            ]
        )
        self.assertEqual(
            self.preregistration["durable_recovery_contract"],
            contract.DURABLE_RECOVERY_CONTRACT,
        )
        changed = copy.deepcopy(self.preregistration)
        changed["durable_recovery_contract"]["lifecycle_lease_path"] += ".drift"
        with self.assertRaises(contract.MM005BrowserResearchRecoveryError):
            self._validate_delta(changed)

    def test_runner_enters_lifecycle_lease_before_attempt_claim(self) -> None:
        source_path = Path(runner.__file__).resolve()
        tree = ast.parse(source_path.read_text(encoding="utf-8"), str(source_path))
        execute = _function_node(tree, "execute_frozen_protocol")
        claim_calls = [
            node
            for node in ast.walk(execute)
            if isinstance(node, ast.Call) and _call_name(node.func) == "_claim_output"
        ]
        self.assertEqual(len(claim_calls), 1)
        claim = claim_calls[0]
        lease_scopes = []
        for node in ast.walk(execute):
            if not isinstance(node, ast.With):
                continue
            for item in node.items:
                expression = item.context_expr
                if (
                    isinstance(expression, ast.Call)
                    and _call_name(expression.func) == "recovery_io.ProgressLease"
                    and len(expression.args) == 1
                    and ast.unparse(expression.args[0]) == "lifecycle_path"
                ):
                    lease_scopes.append(node)
        self.assertEqual(len(lease_scopes), 1)
        lifecycle_scope = lease_scopes[0]
        self.assertLess(lifecycle_scope.lineno, claim.lineno)
        self.assertLessEqual(
            claim.end_lineno or claim.lineno, lifecycle_scope.end_lineno
        )
        self.assertIn(claim, list(ast.walk(lifecycle_scope)))

        ensure_calls = [
            node
            for node in ast.walk(execute)
            if isinstance(node, ast.Call)
            and _call_name(node.func) == "recovery_io.ensure_lock_directory"
        ]
        self.assertEqual(len(ensure_calls), 1)
        ensure = ensure_calls[0]
        self.assertLess(ensure.lineno, lifecycle_scope.lineno)
        self.assertEqual(ast.unparse(ensure.args[0]), "lifecycle_path")
        self.assertEqual(ast.unparse(ensure.args[1]), "contract.LIFECYCLE_LEASE_MARKER")
        marker_calls = [
            node
            for node in ast.walk(execute)
            if isinstance(node, ast.Call)
            and _call_name(node.func) == "recovery_io.validate_lock_file"
        ]
        self.assertEqual(len(marker_calls), 1)
        marker_call = marker_calls[0]
        self.assertIn(marker_call, list(ast.walk(lifecycle_scope)))
        self.assertLess(marker_call.lineno, claim.lineno)
        self.assertEqual(ast.unparse(marker_call.args[0]), "lifecycle_path")
        self.assertEqual(
            ast.unparse(marker_call.args[1]),
            "contract.LIFECYCLE_LEASE_MARKER",
        )

    def test_recovery_holds_lifecycle_lease_before_any_progress_access(self) -> None:
        source_path = Path(terminalizer.__file__).resolve()
        tree = ast.parse(source_path.read_text(encoding="utf-8"), str(source_path))
        public = _function_node(tree, "recover_interrupted_attempt")
        locked = _function_node(tree, "_recover_interrupted_attempt_locked")
        lifecycle_scopes = []
        for node in ast.walk(public):
            if not isinstance(node, ast.With):
                continue
            for item in node.items:
                expression = item.context_expr
                if (
                    isinstance(expression, ast.Call)
                    and _call_name(expression.func) == "recovery_io.ProgressLease"
                    and len(expression.args) == 1
                    and ast.unparse(expression.args[0]) == "lifecycle_path"
                ):
                    lifecycle_scopes.append(node)
        self.assertEqual(len(lifecycle_scopes), 1)
        lifecycle_scope = lifecycle_scopes[0]
        locked_calls = [
            node
            for node in ast.walk(public)
            if isinstance(node, ast.Call)
            and _call_name(node.func) == "_recover_interrupted_attempt_locked"
        ]
        self.assertEqual(len(locked_calls), 1)
        self.assertIn(locked_calls[0], list(ast.walk(lifecycle_scope)))

        progress_scopes = []
        for node in ast.walk(locked):
            if not isinstance(node, ast.With):
                continue
            for item in node.items:
                expression = item.context_expr
                if (
                    isinstance(expression, ast.Call)
                    and _call_name(expression.func) == "recovery_io.ProgressLease"
                    and len(expression.args) == 1
                    and ast.unparse(expression.args[0])
                    == "ROOT / contract.PROGRESS_PATH"
                ):
                    progress_scopes.append(node)
        self.assertEqual(len(progress_scopes), 1)
        progress_scope = progress_scopes[0]
        marker_calls = [
            node
            for node in ast.walk(locked)
            if isinstance(node, ast.Call)
            and _call_name(node.func) == "recovery_io.validate_lock_file"
        ]
        self.assertEqual(len(marker_calls), 1)
        marker_call = marker_calls[0]
        self.assertLess(marker_call.lineno, progress_scope.lineno)
        self.assertEqual(
            ast.unparse(marker_call.args[0]),
            "ROOT / contract.LIFECYCLE_LEASE_PATH",
        )
        self.assertEqual(
            ast.unparse(marker_call.args[1]),
            "contract.LIFECYCLE_LEASE_MARKER",
        )
        scoped_nodes = {id(node) for node in ast.walk(progress_scope)}
        journal_calls = [
            node
            for node in ast.walk(locked)
            if isinstance(node, ast.Call)
            and _call_name(node.func)
            in {
                "journal.append",
                "journal.read",
                "journal.truncate_to_authenticated_prefix",
            }
        ]
        self.assertTrue(journal_calls)
        self.assertTrue(all(id(call) in scoped_nodes for call in journal_calls))

        events: list[str] = []
        state = {"lifecycle_held": False}
        expected_lifecycle_path = terminalizer.ROOT / contract.LIFECYCLE_LEASE_PATH
        expected_progress_path = terminalizer.ROOT / contract.PROGRESS_PATH

        class ProgressBoundaryReached(RuntimeError):
            pass

        class ObservedRecoveryLease:
            def __init__(self, path: Path) -> None:
                self.path = path

            def __enter__(self) -> ObservedRecoveryLease:
                if self.path == expected_lifecycle_path:
                    self.assert_lifecycle_available()
                    state["lifecycle_held"] = True
                    events.append("lifecycle_entered")
                    return self
                if self.path == expected_progress_path:
                    if not state["lifecycle_held"]:
                        raise AssertionError("progress opened without lifecycle lease")
                    self.assert_marker_validated()
                    events.append("progress_enter_attempt")
                    raise ProgressBoundaryReached
                raise AssertionError("recovery used an unregistered lease path")

            def __exit__(self, *_exc: object) -> None:
                if self.path == expected_lifecycle_path:
                    state["lifecycle_held"] = False
                    events.append("lifecycle_released")

            def verify(self) -> None:
                if self.path != expected_lifecycle_path or not state["lifecycle_held"]:
                    raise AssertionError("lifecycle lease verification failed")

            def assert_lifecycle_available(self) -> None:
                if state["lifecycle_held"]:
                    raise AssertionError("lifecycle lease entered twice")

            def assert_marker_validated(self) -> None:
                if events[-1] != "marker_validated":
                    raise AssertionError("progress opened before marker validation")

        def validate_marker(path: Path, marker: bytes) -> bytes:
            self.assertTrue(state["lifecycle_held"])
            self.assertEqual(path, expected_lifecycle_path)
            self.assertEqual(marker, contract.LIFECYCLE_LEASE_MARKER)
            events.append("marker_validated")
            return marker

        def read_bound_file(path: Path, *, max_bytes: int) -> bytes:
            self.assertGreater(max_bytes, 0)
            if path == terminalizer.ROOT / contract.PREREGISTRATION_PATH:
                return self.preregistration_payload
            if path == terminalizer.ROOT / contract.ATTEMPT_OWNER_PATH:
                return self.attempt_owner_payload
            raise AssertionError(f"unexpected pre-progress read: {path}")

        class StableDirectoryGuard:
            def __init__(self, _root: Path, _target: Path) -> None:
                pass

            def verify(self) -> None:
                pass

        with (
            mock.patch.object(terminalizer, "_validate_aligned_freeze_commit"),
            mock.patch.object(terminalizer, "_validate_output_tree"),
            mock.patch.object(
                terminalizer.recovery_io,
                "validate_lock_file",
                side_effect=validate_marker,
            ),
            mock.patch.object(
                terminalizer.recovery_io,
                "ProgressLease",
                ObservedRecoveryLease,
            ),
            mock.patch.object(
                terminalizer.recovery_io,
                "read_regular_file",
                side_effect=read_bound_file,
            ),
            mock.patch.object(
                terminalizer.recovery_io,
                "DirectoryTreeGuard",
                StableDirectoryGuard,
            ),
            mock.patch.object(
                terminalizer.protocol_builder,
                "protocol_inputs",
                return_value=self.protocol_inputs,
            ),
            mock.patch.object(
                terminalizer.protocol_builder,
                "execution_inputs",
                return_value={"records": [], "artifact_payloads": {}},
            ),
        ):
            with self.assertRaises(ProgressBoundaryReached):
                terminalizer.recover_interrupted_attempt(
                    protocol_freeze_commit=self.protocol_freeze_commit,
                    attempt_id=self.attempt_id,
                )
        self.assertEqual(
            events,
            [
                "lifecycle_entered",
                "marker_validated",
                "progress_enter_attempt",
                "lifecycle_released",
            ],
        )

    def test_owner_and_genesis_are_published_as_one_atomic_topology(self) -> None:
        self.assertEqual(len(self._validate_journal(self.initial_journal)), 1)
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            output_dir = Path(temporary) / "claimed"
            runner._claim_output(
                output_dir=output_dir,
                attempt_id=self.attempt_id,
                owner_payload=self.attempt_owner_payload,
                progress_payload=self.initial_journal,
            )
            self.assertEqual(
                {item.name for item in output_dir.iterdir()},
                {"attempt-owner.json", "progress.json"},
            )
            self.assertEqual(
                (output_dir / "attempt-owner.json").read_bytes(),
                self.attempt_owner_payload,
            )
            observed_progress = (output_dir / "progress.json").read_bytes()
            self.assertEqual(observed_progress, self.initial_journal)
            self.assertEqual(len(self._validate_journal(observed_progress)), 1)

    def test_failed_genesis_staging_never_publishes_an_owner_only_output(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            output_dir = Path(temporary) / "claimed"
            original = recovery_io.write_exclusive_fsync
            calls = 0

            def fail_second_write(path: Path, payload: bytes) -> bytes:
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise recovery_io.RecoveryIOError("injected progress write failure")
                return original(path, payload)

            with mock.patch.object(
                runner.recovery_io,
                "write_exclusive_fsync",
                side_effect=fail_second_write,
            ):
                with self.assertRaises(recovery_io.RecoveryIOError):
                    runner._claim_output(
                        output_dir=output_dir,
                        attempt_id=self.attempt_id,
                        owner_payload=self.attempt_owner_payload,
                        progress_payload=self.initial_journal,
                    )
            self.assertFalse(os.path.lexists(output_dir))
            staging = output_dir.with_name(
                f".{output_dir.name}.owner-{self.attempt_id}"
            )
            self.assertTrue(staging.is_dir())
            self.assertEqual(
                {item.name for item in staging.iterdir()}, {"attempt-owner.json"}
            )

    def test_owner_and_freeze_bindings_reject_tamper(self) -> None:
        changed_owner = copy.deepcopy(self.attempt_owner)
        changed_owner["protocol_freeze_commit"] = "d" * 40
        with self.assertRaises(
            contract.MM005BrowserResearchRecoveryError
        ) as owner_error:
            contract.validate_attempt_owner(
                changed_owner,
                protocol_freeze_commit=self.protocol_freeze_commit,
                preregistration_payload=self.preregistration_payload,
            )
        self.assertEqual(owner_error.exception.code, "ATTEMPT_OWNER_MISMATCH")

        mutations: list[tuple[str, Callable[[dict[str, Any]], None], str]] = [
            (
                "attempt ID",
                lambda value: value.__setitem__("attempt_id", "e" * 64),
                "PROGRESS_OWNER_MISMATCH",
            ),
            (
                "freeze commit",
                lambda value: value["protocol"].__setitem__("freeze_commit", "f" * 40),
                "PROGRESS_OWNER_BINDING",
            ),
            (
                "owner receipt",
                lambda value: value["protocol"]["attempt_owner"].__setitem__(
                    "sha256", "sha256:" + "0" * 64
                ),
                "PROGRESS_OWNER_BINDING",
            ),
        ]
        for label, mutation, code in mutations:
            with self.subTest(label=label):
                payload = self._mutate_last_event(self.initial_journal, mutation)
                with self.assertRaises(
                    contract.MM005BrowserResearchRecoveryError
                ) as raised:
                    self._validate_journal(payload)
                self.assertEqual(raised.exception.code, code)

    def test_journal_rejects_hash_sequence_counter_and_transition_tamper(self) -> None:
        journal = self._journal_through_first_generation()
        self.assertEqual(len(self._validate_journal(journal)), 8)

        def corrupt_hash(value: dict[str, Any]) -> None:
            value["previous_event_sha256"] = "sha256:" + "0" * 64

        def corrupt_sequence(value: dict[str, Any]) -> None:
            value["sequence"] += 1

        def corrupt_counter(value: dict[str, Any]) -> None:
            value["counters"]["generate_calls"] = 0

        def corrupt_transition(value: dict[str, Any]) -> None:
            value["event"] = "base_load_started"
            value["record_id"] = None

        mutations = (
            ("hash", corrupt_hash, "PROGRESS_CHAIN"),
            ("sequence", corrupt_sequence, "PROGRESS_CHAIN"),
            ("counter", corrupt_counter, "PROGRESS_COMPLETED_RECORD_COUNT"),
            ("transition", corrupt_transition, "PROGRESS_TRANSITION"),
        )
        for label, mutation, code in mutations:
            with self.subTest(label=label):
                payload = self._mutate_last_event(journal, mutation)
                with self.assertRaises(
                    contract.MM005BrowserResearchRecoveryError
                ) as raised:
                    self._validate_journal(payload)
                self.assertEqual(raised.exception.code, code)

    def test_generation_start_rejects_wrong_record_or_screenshot_count(self) -> None:
        journal = self._journal_through_first_generation()
        lines = journal.splitlines(keepends=True)
        started = contract.parse_strict_json_bytes(
            lines[-2], location="$.test.generation_started"
        )

        wrong_record = copy.deepcopy(started)
        wrong_record["record_id"] = self.preregistration["input_suite"]["case_order"][1]
        record_lines = list(lines)
        record_lines[-2] = contract.artifact_json_bytes(wrong_record)
        with self.assertRaises(
            contract.MM005BrowserResearchRecoveryError
        ) as record_error:
            self._validate_journal(b"".join(record_lines))
        self.assertEqual(
            record_error.exception.code, "PROGRESS_GENERATION_RECORD_ORDER"
        )

        wrong_screenshot_count = copy.deepcopy(started)
        wrong_screenshot_count["counters"]["screenshot_inputs"] += 1
        screenshot_lines = list(lines)
        screenshot_lines[-2] = contract.artifact_json_bytes(wrong_screenshot_count)
        with self.assertRaises(
            contract.MM005BrowserResearchRecoveryError
        ) as screenshot_error:
            self._validate_journal(b"".join(screenshot_lines))
        self.assertEqual(screenshot_error.exception.code, "PROGRESS_SCREENSHOT_COUNTER")

    def test_failure_terminal_rejects_counter_inflation(self) -> None:
        terminal = contract.terminal_event(
            kind="failure",
            captured_at_utc="2026-08-28T00:00:00+00:00",
            stage="external_interruption_recovery",
            exception_type="ExternalControllerInterruption",
            external_controller_interruption=True,
            interrupted_after_event="attempt_claimed",
        )
        failure_event = contract.build_progress_event(
            previous_journal_payload=self.initial_journal,
            protocol_freeze_commit=self.protocol_freeze_commit,
            preregistration_payload=self.preregistration_payload,
            attempt_owner_payload=self.attempt_owner_payload,
            event="failure_terminal_ready",
            counters=self.initial_counters,
            completed_record_ids=[],
            terminal=terminal,
        )
        journal = self.initial_journal + contract.artifact_json_bytes(failure_event)
        self.assertEqual(len(self._validate_journal(journal)), 2)
        inflated = self._mutate_last_event(
            journal,
            lambda value: value["counters"].__setitem__("fresh_base_load_attempts", 1),
        )
        with self.assertRaises(contract.MM005BrowserResearchRecoveryError) as raised:
            self._validate_journal(inflated)
        self.assertEqual(raised.exception.code, "PROGRESS_FAILURE_COUNTER_CHANGE")

    def test_completed_record_validator_rejects_nonprefix_completion(self) -> None:
        counters = copy.deepcopy(self.initial_counters)
        counters["generate_attempts"] = 1
        counters["generate_calls"] = 1
        case_order = self.preregistration["input_suite"]["case_order"]
        validate_completed = getattr(contract, "_validate_completed_record_ids")
        self.assertEqual(
            validate_completed([case_order[0]], counters, self.preregistration_payload),
            [case_order[0]],
        )
        with self.assertRaises(contract.MM005BrowserResearchRecoveryError) as raised:
            validate_completed([case_order[1]], counters, self.preregistration_payload)
        self.assertEqual(raised.exception.code, "PROGRESS_COMPLETED_RECORD_PREFIX")

    def test_torn_tail_is_bound_but_complete_invalid_frame_is_not_discarded(
        self,
    ) -> None:
        tail = b'{"partial":"frame"'
        events, prefix, receipt = contract.recover_progress_prefix(
            self.initial_journal + tail,
            protocol_freeze_commit=self.protocol_freeze_commit,
            preregistration_payload=self.preregistration_payload,
            attempt_owner_payload=self.attempt_owner_payload,
        )
        self.assertEqual(events, [self.initial_event])
        self.assertEqual(prefix, self.initial_journal)
        self.assertEqual(
            receipt,
            {
                "bytes": len(tail),
                "sha256": contract.sha256_bytes(tail),
                "authenticated_event": False,
                "execution_fact_claimed": False,
            },
        )
        with self.assertRaises(contract.MM005BrowserResearchRecoveryError):
            contract.recover_progress_prefix(
                self.initial_journal + b"{}\n",
                protocol_freeze_commit=self.protocol_freeze_commit,
                preregistration_payload=self.preregistration_payload,
                attempt_owner_payload=self.attempt_owner_payload,
            )

    def test_lifecycle_directory_survives_stale_staging_and_rejects_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            lifecycle_root = Path(temporary) / "attempt.lifecycle"
            lifecycle = lifecycle_root / "lease"
            marker = contract.LIFECYCLE_LEASE_MARKER
            stale_staging = lifecycle_root.with_name(
                f".{lifecycle_root.name}.staging-{'0' * 32}"
            )
            stale_staging.mkdir()
            stale_payload = marker[: len(marker) // 2]
            (stale_staging / lifecycle.name).write_bytes(stale_payload)

            with mock.patch.object(
                recovery_io.secrets, "token_hex", return_value="1" * 32
            ) as token_hex:
                self.assertEqual(
                    recovery_io.ensure_lock_directory(lifecycle, marker), marker
                )
            token_hex.assert_called_once_with(16)
            self.assertTrue(lifecycle_root.is_dir())
            self.assertEqual(
                {item.name for item in lifecycle_root.iterdir()}, {"lease"}
            )
            self.assertEqual(lifecycle.read_bytes(), marker)
            self.assertEqual(
                (stale_staging / lifecycle.name).read_bytes(), stale_payload
            )
            self.assertEqual(
                recovery_io.ensure_lock_directory(lifecycle, marker), marker
            )

            drift = marker[:-2] + b"X\n"
            self.assertEqual(len(drift), len(marker))
            lifecycle.write_bytes(drift)
            with self.assertRaises(recovery_io.RecoveryIOError):
                recovery_io.ensure_lock_directory(lifecycle, marker)
            self.assertEqual(lifecycle.read_bytes(), drift)
            lifecycle.write_bytes(marker)

            with recovery_io.ProgressLease(lifecycle) as first:
                self.assertEqual(first.read(), marker)
                second = recovery_io.ProgressLease(lifecycle)
                with self.assertRaises(recovery_io.RecoveryIOError):
                    second.open()
                self.assertIsNone(second.handle)
            with recovery_io.ProgressLease(lifecycle) as reopened:
                self.assertEqual(reopened.read(), marker)

    def test_terminal_repair_accepts_only_an_exact_canonical_prefix(self) -> None:
        expected = contract.artifact_json_bytes(
            {"kind": "failure", "receipt": "preauthenticated"}
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            partial = root / "failure.json"
            partial.write_bytes(expected[: len(expected) // 2])
            self.assertEqual(
                recovery_io.write_or_repair_terminal(partial, expected), expected
            )
            self.assertEqual(partial.read_bytes(), expected)
            self.assertEqual(
                recovery_io.write_or_repair_terminal(partial, expected), expected
            )

            absent = root / "evidence.json"
            self.assertEqual(
                recovery_io.write_or_repair_terminal(absent, expected), expected
            )
            self.assertEqual(absent.read_bytes(), expected)

            empty = root / "empty.json"
            empty.write_bytes(b"")
            self.assertEqual(
                recovery_io.write_or_repair_terminal(empty, expected), expected
            )
            self.assertEqual(empty.read_bytes(), expected)

            for name, observed in (
                ("wrong.json", b"not-a-prefix"),
                ("long.json", expected + b"extra"),
            ):
                with self.subTest(name=name):
                    path = root / name
                    path.write_bytes(observed)
                    with self.assertRaises(recovery_io.RecoveryIOError):
                        recovery_io.write_or_repair_terminal(path, expected)
                    self.assertEqual(path.read_bytes(), observed)

    def test_terminalizer_repairs_only_the_expected_failure_terminal_prefix(
        self,
    ) -> None:
        terminal = contract.terminal_event(
            kind="failure",
            captured_at_utc="2026-08-28T00:00:00+00:00",
            stage="external_interruption_recovery",
            exception_type="ExternalControllerInterruption",
            external_controller_interruption=True,
            interrupted_after_event="attempt_claimed",
        )
        failure_event = contract.build_progress_event(
            previous_journal_payload=self.initial_journal,
            protocol_freeze_commit=self.protocol_freeze_commit,
            preregistration_payload=self.preregistration_payload,
            attempt_owner_payload=self.attempt_owner_payload,
            event="failure_terminal_ready",
            counters=self.initial_counters,
            completed_record_ids=[],
            terminal=terminal,
        )
        progress_payload = self.initial_journal + contract.artifact_json_bytes(
            failure_event
        )
        failure_object = contract.build_failure(
            protocol_freeze_commit=self.protocol_freeze_commit,
            preregistration_payload=self.preregistration_payload,
            attempt_owner_payload=self.attempt_owner_payload,
            progress_payload=progress_payload,
            artifact_payloads={
                "evaluation_candidate": None,
                "predictions": None,
            },
        )
        expected_failure = contract.artifact_json_bytes(failure_object)
        partial_failure = expected_failure[: len(expected_failure) // 2]

        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary)
            preregistration_path = temporary_root / contract.PREREGISTRATION_PATH
            preregistration_path.parent.mkdir(parents=True)
            preregistration_path.write_bytes(self.preregistration_payload)
            output_dir = temporary_root / contract.RUN_OUTPUT_ROOT
            output_dir.mkdir(parents=True)
            (temporary_root / contract.ATTEMPT_OWNER_PATH).write_bytes(
                self.attempt_owner_payload
            )
            (temporary_root / contract.PROGRESS_PATH).write_bytes(progress_payload)
            failure_path = temporary_root / contract.FAILURE_PATH
            failure_path.write_bytes(partial_failure)
            lifecycle_path = temporary_root / contract.LIFECYCLE_LEASE_PATH
            recovery_io.ensure_lock_directory(
                lifecycle_path, contract.LIFECYCLE_LEASE_MARKER
            )

            with (
                mock.patch.object(terminalizer, "ROOT", temporary_root),
                mock.patch.object(terminalizer, "_validate_aligned_freeze_commit"),
                mock.patch.object(
                    terminalizer.protocol_builder,
                    "protocol_inputs",
                    return_value=self.protocol_inputs,
                ),
                mock.patch.object(
                    terminalizer.protocol_builder,
                    "execution_inputs",
                    return_value={"records": [], "artifact_payloads": {}},
                ),
            ):
                repaired = terminalizer.recover_interrupted_attempt(
                    protocol_freeze_commit=self.protocol_freeze_commit,
                    attempt_id=self.attempt_id,
                )
                repeated = terminalizer.recover_interrupted_attempt(
                    protocol_freeze_commit=self.protocol_freeze_commit,
                    attempt_id=self.attempt_id,
                )

            self.assertEqual(failure_path.read_bytes(), expected_failure)
            self.assertEqual(repaired["terminal"], "failure")
            self.assertTrue(repaired["terminal_recovered"])
            self.assertEqual(repeated["terminal"], "failure")
            self.assertFalse(repeated["terminal_recovered"])

    def test_terminalizer_has_no_ml_cuda_network_or_retry_capability(self) -> None:
        source_path = Path(terminalizer.__file__).resolve()
        source = source_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(source_path))
        imported_roots: set[str] = set()
        calls: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".")[0])
            elif isinstance(node, ast.Call):
                name = _call_name(node.func)
                if name:
                    calls.add(name)

        forbidden_imports = {
            "aiohttp",
            "httpx",
            "peft",
            "requests",
            "socket",
            "torch",
            "transformers",
            "urllib",
        }
        self.assertTrue(imported_roots.isdisjoint(forbidden_imports))
        forbidden_call_segments = {
            "_load_eval_dependencies",
            "_run_model_evaluation",
            "cuda",
            "generate",
            "retry",
            "urlopen",
        }
        for call in calls:
            with self.subTest(call=call):
                self.assertTrue(
                    set(call.split(".")).isdisjoint(forbidden_call_segments)
                )
        self.assertNotIn("run_mm005_browser_research_model_evaluation_v2", source)
        self.assertFalse(
            contract.DURABLE_RECOVERY_CONTRACT["recovery_imports_or_calls_model"]
        )
        self.assertFalse(contract.DURABLE_RECOVERY_CONTRACT["recovery_uses_network"])
        self.assertFalse(
            contract.DURABLE_RECOVERY_CONTRACT[
                "recovery_retries_v1_or_v2_model_execution"
            ]
        )

    def test_locked_v1_lineage_hashes_are_unchanged(self) -> None:
        expected_contract_receipts = (
            contract.V1_PREREGISTRATION_RECEIPT,
            contract.V1_ATTEMPT_OWNER_RECEIPT,
            {
                key: contract.V1_FAILURE_CLASSIFICATION_RECEIPT[key]
                for key in ("path", "bytes", "sha256")
            },
        )
        self.assertEqual(expected_contract_receipts, LOCKED_V1_RECEIPTS)
        for receipt in LOCKED_V1_RECEIPTS:
            with self.subTest(path=receipt["path"]):
                payload = (ROOT / str(receipt["path"])).read_bytes()
                self.assertEqual(len(payload), receipt["bytes"])
                self.assertEqual(contract.sha256_bytes(payload), receipt["sha256"])
                self.assertEqual(payload, self.v1_payloads_before[str(receipt["path"])])


if __name__ == "__main__":
    unittest.main()
