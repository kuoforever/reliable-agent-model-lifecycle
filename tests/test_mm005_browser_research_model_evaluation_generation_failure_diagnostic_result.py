from __future__ import annotations

import ast
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any, ClassVar
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(ROOT))

from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_model_evaluation_generation_failure_diagnostic as protocol,
)
from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_model_evaluation_generation_failure_diagnostic_result as contract,
)
from scripts import (  # noqa: E402
    run_mm005_browser_research_model_evaluation_generation_failure_diagnostic_v1 as runner,
)


class MM005BrowserResearchGenerationFailureDiagnosticResultV1Tests(unittest.TestCase):
    preregistration_payload: ClassVar[bytes]
    implementation_commit: ClassVar[str]
    owner: ClassVar[dict[str, Any]]
    owner_payload: ClassVar[bytes]
    authority_payload: ClassVar[bytes]
    authority_commit: ClassVar[str]
    dependency_receipts: ClassVar[dict[str, dict[str, Any]]]
    environment: ClassVar[dict[str, Any]]
    resources: ClassVar[dict[str, float | int]]

    @classmethod
    def setUpClass(cls) -> None:
        cls.preregistration_payload = (
            ROOT / protocol.PREREGISTRATION_PATH
        ).read_bytes()
        cls.implementation_commit = "a" * 40
        v2 = json.loads(
            (
                ROOT
                / "configs/mm005_browser_research_model_evaluation_protocol_v2.json"
            ).read_text(encoding="utf-8")
        )
        cls.environment = {
            name: v2["candidate"]["environment"][name]
            for name in protocol.OBSERVED_ENVIRONMENT_FIELDS
        }
        dependency_receipts = {}
        for name, relative in sorted(
            contract.CRITICAL_EXECUTION_DEPENDENCY_SOURCE_PATHS.items()
        ):
            payload = (ROOT / relative).read_bytes()
            dependency_receipts[name] = {
                "path": relative,
                "bytes": len(payload),
                "sha256": contract.sha256_bytes(payload),
            }
        cls.dependency_receipts = dependency_receipts
        cls.authority_commit = "c" * 40
        cls.authority_payload = contract.artifact_json_bytes(
            contract.build_execution_authority_contract(
                implementation_freeze_commit=cls.implementation_commit,
                expected_environment=cls.environment,
                critical_execution_dependency_receipts=dependency_receipts,
            )
        )
        cls.owner = contract.build_attempt_owner(
            implementation_freeze_commit=cls.implementation_commit,
            preregistration_payload=cls.preregistration_payload,
            authority_freeze_commit=cls.authority_commit,
            execution_authority_payload=cls.authority_payload,
            attempt_id="b" * 64,
        )
        cls.owner_payload = contract.artifact_json_bytes(cls.owner)
        cls.resources = {
            "elapsed_seconds": 1.0,
            "peak_gpu_allocated_bytes": 1,
            "peak_gpu_reserved_bytes": 1,
        }

    def _implementation_context(self) -> dict[str, Any]:
        bindings: dict[str, dict[str, Any]] = {}
        for name, relative in sorted(contract.IMPLEMENTATION_SOURCE_PATHS.items()):
            payload = (ROOT / relative).read_bytes()
            bindings[name] = {
                "path": relative,
                "bytes": len(payload),
                "sha256": contract.sha256_bytes(payload),
                "tracked_bytes_equal_implementation_freeze_commit_blob": True,
            }
        return {
            "freeze_commit": self.implementation_commit,
            "source_bindings": bindings,
            "three_sources_share_first_parent_introduction_commit": True,
            "exact_reviewed_slice_delta": True,
        }

    def _append(
        self,
        journal: bytes,
        event: str,
        *,
        record_id: str | None = None,
        diagnostic_index: int | None = None,
        environment: dict[str, Any] | None = None,
        captured_at_utc: str | None = None,
        exception_type: str | None = None,
        resources: dict[str, float | int] | None = None,
        case_result: dict[str, Any] | None = None,
        discarded_progress_tail: dict[str, Any] | None = None,
    ) -> bytes:
        frame = contract.build_progress_event(
            previous_journal_payload=journal,
            implementation_freeze_commit=self.implementation_commit,
            preregistration_payload=self.preregistration_payload,
            attempt_owner_payload=self.owner_payload,
            event=event,
            record_id=record_id,
            diagnostic_index=diagnostic_index,
            observed_environment=environment,
            captured_at_utc=captured_at_utc,
            exception_type=exception_type,
            resources=resources,
            case_result=case_result,
            discarded_progress_tail=discarded_progress_tail,
        )
        return journal + contract.artifact_json_bytes(frame)

    def _session(self, *, length: int = 6) -> bytes:
        journal = b""
        for event in protocol.SESSION_LIFECYCLE_EVENTS[:length]:
            journal = self._append(
                journal,
                event,
                environment=(
                    self.environment if event == "context_preflight_completed" else None
                ),
            )
        return journal

    def _case_summary(self, index: int) -> dict[str, Any]:
        digest = contract.sha256_bytes(f"case-{index}".encode())
        byte_receipt = {"bytes": index + 1, "sha256": digest}
        return {
            "record_id": protocol.DIAGNOSTIC_CASE_ORDER[index],
            "diagnostic_index": index,
            "case_result": dict(byte_receipt),
            "raw_output": dict(byte_receipt),
            "compiled_output": dict(byte_receipt),
            "verdict": dict(byte_receipt),
            "citation_semantics": dict(byte_receipt),
            "generated_tokens": index,
            "latency_seconds": float(index + 1),
            "model_payload_sha256": digest,
            "prompt_projection_sha256": digest,
            "source_count": 1,
            "screenshot_sha256": [digest],
            "source_snapshot_sha256": [digest],
            "arbitrary_model_text_persisted": False,
            "model_output_has_execution_authority": False,
        }

    def _append_record_prefix(self, journal: bytes, index: int, length: int) -> bytes:
        record_id = protocol.DIAGNOSTIC_CASE_ORDER[index]
        for event in protocol.DIAGNOSTIC_CHECKPOINTS[:length]:
            journal = self._append(
                journal,
                event,
                record_id=record_id,
                diagnostic_index=index,
                case_result=(
                    self._case_summary(index)
                    if event == "case_result_build_completed"
                    else None
                ),
            )
        return journal

    def _completed_records(self, count: int) -> bytes:
        journal = self._session()
        for index in range(count):
            journal = self._append_record_prefix(journal, index, 18)
        return journal

    def _success_journal(self) -> bytes:
        journal = self._completed_records(7)
        return self._append(
            journal,
            "success_terminal_ready",
            captured_at_utc="2026-08-30T00:00:00Z",
            resources=self.resources,
        )

    def _failure(self, journal: bytes, exception_type: str = "RuntimeError") -> bytes:
        return self._append(
            journal,
            "failure_terminal_ready",
            captured_at_utc="2026-08-30T00:00:00Z",
            exception_type=exception_type,
        )

    def test_protocol_merge_config_thirteen_sources_and_three_file_closure(
        self,
    ) -> None:
        self.assertEqual(
            contract.PROTOCOL_MERGE_COMMIT, "9c90c5e68d4386b30db613930ec7dc0147999c04"
        )
        self.assertEqual(len(self.preregistration_payload), 57_143)
        self.assertEqual(
            contract.sha256_bytes(self.preregistration_payload),
            contract.PROTOCOL_SHA256,
        )
        self.assertEqual(len(protocol.PROTOCOL_SOURCE_PATHS), 13)
        self.assertEqual(len(contract.IMPLEMENTATION_SOURCE_PATHS), 3)
        self.assertEqual(len(contract.CRITICAL_EXECUTION_DEPENDENCY_SOURCE_PATHS), 4)
        self.assertEqual(len(contract.EXECUTION_AUTHORITY_SLICE_PATHS), 10)
        self.assertEqual(len(runner.IMPLEMENTATION_SLICE_PATHS), 11)
        context = runner._published_protocol_context()
        self.assertEqual(context["protocol_source_files"], 13)
        self.assertEqual(len(runner._implementation_source_receipts()), 3)

    def test_contract_closes_schema_authority_claims_and_routes(self) -> None:
        value = contract.result_contract()
        authority_contract = value["execution_authority_contract"]
        owner_contract = value["owner_contract"]
        self.assertEqual(value["gate_id"], protocol.IMPLEMENTATION_GATE_ID)
        self.assertEqual(value["next_gate_id"], contract.EXECUTION_AUTHORITY_GATE_ID)
        self.assertFalse(
            value["publication_contract"][
                "clean_implementation_merge_alone_authorizes_execution"
            ]
        )
        self.assertTrue(
            value["publication_contract"][
                "separate_execution_authority_and_resource_preflight_required"
            ]
        )
        self.assertEqual(
            value["result_schema"]["required_top_level_keys"],
            list(contract.RESULT_REQUIRED_TOP_LEVEL_KEYS),
        )
        self.assertEqual(
            value["failure_schema"]["required_top_level_keys"],
            list(contract.FAILURE_REQUIRED_TOP_LEVEL_KEYS),
        )
        self.assertEqual(
            value["terminal_contract"]["failure_scopes"], list(contract.FAILURE_SCOPES)
        )
        self.assertTrue(
            all(item is False for item in value["claims_contract"].values())
        )
        self.assertTrue(
            authority_contract["execute_head_must_equal_authority_introduction_commit"]
        )
        self.assertTrue(
            authority_contract[
                "reconcile_head_must_equal_authority_introduction_commit"
            ]
        )
        self.assertTrue(
            authority_contract[
                "assume_unchanged_or_skip_worktree_index_flags_forbidden"
            ]
        )
        self.assertTrue(
            authority_contract["git_fsmonitor_disabled_for_all_execution_checks"]
        )
        authority_payload = json.loads(self.authority_payload)
        self.assertTrue(
            authority_payload["resource_preflight"][
                "exact_environment_match_required_before_model_load_or_cuda_workload"
            ]
        )
        self.assertTrue(
            authority_payload["resource_preflight"][
                "read_only_cuda_capability_observation_allowed_for_exact_match"
            ]
        )
        self.assertTrue(owner_contract["reserved_sibling_staging_blocks_a_new_claim"])

    def test_outcome_selection_is_closed_and_bool_strict(self) -> None:
        cases = {
            "diagnostic_protocol_or_lineage_invalid": (False, None, None),
            "diagnostic_completed_without_observed_runtime_failure": (
                True,
                "success",
                None,
            ),
            "diagnostic_failure_observed_between_durable_checkpoints": (
                True,
                "failure",
                "active_record_substage",
            ),
            "diagnostic_inconclusive": (True, "failure", "pre_record_lifecycle"),
        }
        for expected, values in cases.items():
            with self.subTest(expected=expected):
                self.assertEqual(
                    contract.select_outcome(
                        protocol_and_lineage_valid=values[0],
                        terminal_kind=values[1],
                        failure_scope=values[2],
                    ),
                    expected,
                )
        with self.assertRaises(contract.MM005GenerationFailureDiagnosticResultError):
            contract.select_outcome(
                protocol_and_lineage_valid=1, terminal_kind=None, failure_scope=None
            )
        with self.assertRaises(contract.MM005GenerationFailureDiagnosticResultError):
            contract.select_outcome(
                protocol_and_lineage_valid=False,
                terminal_kind="failure",
                failure_scope="pre_record_lifecycle",
            )

    def test_attempt_owner_is_canonical_private_and_strict(self) -> None:
        checked = contract.validate_attempt_owner(
            self.owner,
            implementation_freeze_commit=self.implementation_commit,
            preregistration_payload=self.preregistration_payload,
        )
        self.assertEqual(checked, self.owner)
        self.assertEqual(self.owner["attempt_id"], "b" * 64)
        self.assertEqual(
            self.owner["execution_authority"]["freeze_commit"],
            self.authority_commit,
        )
        self.assertEqual(
            self.owner["execution_authority"]["artifact"]["sha256"],
            contract.sha256_bytes(self.authority_payload),
        )
        changed = copy.deepcopy(self.owner)
        changed["execution_authority"]["contract"]["authority_contract"][
            "diagnostic_execution_authorized"
        ] = False
        with self.assertRaises(contract.MM005GenerationFailureDiagnosticResultError):
            contract.validate_attempt_owner(
                changed,
                implementation_freeze_commit=self.implementation_commit,
                preregistration_payload=self.preregistration_payload,
            )
        for value in ("B" * 64, "b" * 63, "../secret", True):
            with (
                self.subTest(value=value),
                self.assertRaises(contract.MM005GenerationFailureDiagnosticResultError),
            ):
                contract.build_attempt_owner(
                    implementation_freeze_commit=self.implementation_commit,
                    preregistration_payload=self.preregistration_payload,
                    authority_freeze_commit=self.authority_commit,
                    execution_authority_payload=self.authority_payload,
                    attempt_id=value,  # type: ignore[arg-type]
                )

    def test_critical_dependency_receipts_bind_current_source_bytes(self) -> None:
        authority = json.loads(self.authority_payload)
        checked = runner._validate_critical_execution_dependency_receipts(
            authority, commit=None
        )
        self.assertEqual(checked, self.dependency_receipts)
        changed = copy.deepcopy(authority)
        changed["critical_execution_dependency_receipts"]["recovery_io"]["bytes"] += 1
        with self.assertRaises(RuntimeError):
            runner._validate_critical_execution_dependency_receipts(
                changed, commit=None
            )

    def test_genesis_session_sequence_hash_and_environment_are_exact(self) -> None:
        journal = self._session()
        events = contract.validate_progress_journal(
            journal,
            implementation_freeze_commit=self.implementation_commit,
            preregistration_payload=self.preregistration_payload,
            attempt_owner_payload=self.owner_payload,
        )
        self.assertEqual(len(events), 6)
        self.assertEqual(events[0]["sequence"], 0)
        self.assertIsNone(events[0]["previous_event_sha256"])
        self.assertEqual(
            events[-1]["session_lifecycle_events"],
            list(protocol.SESSION_LIFECYCLE_EVENTS),
        )
        self.assertEqual(events[-1]["observed_environment"], self.environment)
        for index in range(1, len(events)):
            self.assertEqual(
                events[index]["previous_event_sha256"],
                contract.sha256_bytes(contract.artifact_json_bytes(events[index - 1])),
            )
        changed_environment = dict(self.environment)
        changed_environment["python"] = "0.0.0"
        with self.assertRaises(contract.MM005GenerationFailureDiagnosticResultError):
            self._append(
                self._session(length=1),
                "context_preflight_completed",
                environment=changed_environment,
            )

    def test_timestamp_is_utc_and_large_numbers_fail_with_contract_error(self) -> None:
        with self.assertRaises(contract.MM005GenerationFailureDiagnosticResultError):
            self._append(
                self._session(length=1),
                "failure_terminal_ready",
                captured_at_utc="2026-08-30T08:00:00+08:00",
                exception_type="RuntimeError",
            )
        changed = self._case_summary(0)
        changed["latency_seconds"] = 10**400
        with self.assertRaises(contract.MM005GenerationFailureDiagnosticResultError):
            contract._validated_case_summary(changed, 0, "$.case_result")

    def test_strict_json_duplicate_noncanonical_partial_and_reseal_fail(self) -> None:
        journal = self._session(length=1)
        with self.assertRaises(contract.MM005GenerationFailureDiagnosticResultError):
            contract.validate_progress_journal(
                journal[:-1],
                implementation_freeze_commit=self.implementation_commit,
                preregistration_payload=self.preregistration_payload,
                attempt_owner_payload=self.owner_payload,
            )
        value = json.loads(journal)
        value["sequence"] = True
        tampered = contract.artifact_json_bytes(value)
        with self.assertRaises(contract.MM005GenerationFailureDiagnosticResultError):
            contract.validate_progress_journal(
                tampered,
                implementation_freeze_commit=self.implementation_commit,
                preregistration_payload=self.preregistration_payload,
                attempt_owner_payload=self.owner_payload,
            )
        duplicate = b'{"a":1,"a":2}\n'
        with self.assertRaises(contract.MM005GenerationFailureDiagnosticResultError):
            contract.parse_strict_json_bytes(duplicate, location="$.duplicate")

    def test_all_seven_by_eighteen_checkpoints_are_exact(self) -> None:
        journal = self._completed_records(7)
        events = contract.validate_progress_journal(
            journal,
            implementation_freeze_commit=self.implementation_commit,
            preregistration_payload=self.preregistration_payload,
            attempt_owner_payload=self.owner_payload,
        )
        self.assertEqual(len(events), 132)
        self.assertEqual(events[-1]["durable_substage_event_count"], 126)
        self.assertEqual(
            events[-1]["completed_record_ids"], list(protocol.DIAGNOSTIC_CASE_ORDER)
        )
        self.assertIsNone(events[-1]["active_record_id"])
        self.assertEqual(sum(item["case_result"] is not None for item in events), 7)

    def test_full_success_is_133_frames_and_builds_text_free_result(self) -> None:
        journal = self._success_journal()
        events = contract.validate_progress_journal(
            journal,
            implementation_freeze_commit=self.implementation_commit,
            preregistration_payload=self.preregistration_payload,
            attempt_owner_payload=self.owner_payload,
        )
        self.assertEqual(len(events), 133)
        terminal = events[-1]
        self.assertEqual(terminal["sequence"], 132)
        self.assertEqual(terminal["event"], "success_terminal_ready")
        self.assertEqual(terminal["durable_substage_event_count"], 126)
        self.assertEqual(
            terminal["last_completed_checkpoint"],
            dict(protocol.PER_RECORD_CHECKPOINT_PLANS[-1]["durable_events"][-1]),
        )
        result = contract.build_diagnostic_result(
            implementation_freeze_commit=self.implementation_commit,
            preregistration_payload=self.preregistration_payload,
            attempt_owner_payload=self.owner_payload,
            progress_payload=journal,
            implementation_context=self._implementation_context(),
        )
        checked = contract.validate_diagnostic_result(
            result,
            implementation_freeze_commit=self.implementation_commit,
            preregistration_payload=self.preregistration_payload,
            attempt_owner_payload=self.owner_payload,
            progress_payload=journal,
            implementation_context=self._implementation_context(),
        )
        self.assertEqual(checked, result)
        self.assertEqual(len(result["record_results"]), 7)
        encoded = contract.artifact_json_bytes(result).decode()
        self.assertNotIn("do not persist this arbitrary model string", encoded)
        self.assertTrue(
            all(
                set(item["raw_output"]) == {"bytes", "sha256"}
                for item in result["record_results"]
            )
        )
        self.assertTrue(result["claims"]["diagnostic_executed"])
        self.assertFalse(result["claims"]["formal_measurement_complete"])
        completed = b"".join(journal.splitlines(keepends=True)[:-1])
        for invalid_resources in (
            {**self.resources, "elapsed_seconds": 1},
            {
                **self.resources,
                "peak_gpu_allocated_bytes": (
                    protocol.v2.RESOURCE_CAPS["peak_gpu_allocated_bytes"] + 1
                ),
            },
        ):
            with self.assertRaises(
                contract.MM005GenerationFailureDiagnosticResultError
            ):
                self._append(
                    completed,
                    "success_terminal_ready",
                    captured_at_utc="2026-08-30T00:00:00Z",
                    resources=invalid_resources,
                )

    def test_pre_record_failure_covers_all_six_session_prefixes(self) -> None:
        for length in range(1, 7):
            with self.subTest(length=length):
                journal = self._failure(self._session(length=length))
                terminal = contract.validate_progress_journal(
                    journal,
                    implementation_freeze_commit=self.implementation_commit,
                    preregistration_payload=self.preregistration_payload,
                    attempt_owner_payload=self.owner_payload,
                )[-1]
                self.assertEqual(
                    terminal["terminal"]["failure_scope"], "pre_record_lifecycle"
                )
                self.assertIsNone(terminal["last_started_checkpoint"])
                self.assertIsNone(terminal["last_completed_checkpoint"])

    def test_inter_record_failure_covers_completed_prefixes_one_through_six(
        self,
    ) -> None:
        for count in range(1, 7):
            with self.subTest(count=count):
                journal = self._failure(self._completed_records(count))
                terminal = contract.validate_progress_journal(
                    journal,
                    implementation_freeze_commit=self.implementation_commit,
                    preregistration_payload=self.preregistration_payload,
                    attempt_owner_payload=self.owner_payload,
                )[-1]
                self.assertEqual(
                    terminal["terminal"]["failure_scope"], "inter_record_transition"
                )
                self.assertEqual(
                    terminal["completed_record_ids"],
                    list(protocol.DIAGNOSTIC_CASE_ORDER[:count]),
                )
                self.assertEqual(
                    terminal["active_record_id"], protocol.DIAGNOSTIC_CASE_ORDER[count]
                )
                self.assertEqual(terminal["active_record_diagnostic_index"], count)
                self.assertEqual(terminal["active_record_events"], [])

    def test_active_failure_covers_all_seven_by_seventeen_proper_prefixes(self) -> None:
        for index in range(7):
            base = self._completed_records(index)
            for length in range(1, 18):
                with self.subTest(index=index, length=length):
                    journal = self._append_record_prefix(base, index, length)
                    terminal = contract.validate_progress_journal(
                        self._failure(journal),
                        implementation_freeze_commit=self.implementation_commit,
                        preregistration_payload=self.preregistration_payload,
                        attempt_owner_payload=self.owner_payload,
                    )[-1]
                    self.assertEqual(
                        terminal["terminal"]["failure_scope"], "active_record_substage"
                    )
                    self.assertEqual(
                        terminal["active_record_id"],
                        protocol.DIAGNOSTIC_CASE_ORDER[index],
                    )
                    self.assertEqual(len(terminal["active_record_events"]), length)
                    self.assertEqual(
                        terminal["terminal"]["selected_outcome"],
                        "diagnostic_failure_observed_between_durable_checkpoints",
                    )

    def test_post_record_terminalization_is_exact_126_to_success_window(self) -> None:
        journal = self._failure(self._completed_records(7))
        terminal = contract.validate_progress_journal(
            journal,
            implementation_freeze_commit=self.implementation_commit,
            preregistration_payload=self.preregistration_payload,
            attempt_owner_payload=self.owner_payload,
        )[-1]
        self.assertEqual(
            terminal["terminal"]["failure_scope"], "post_record_terminalization"
        )
        self.assertEqual(terminal["durable_substage_event_count"], 126)
        self.assertEqual(
            terminal["last_started_checkpoint"],
            dict(protocol.PER_RECORD_CHECKPOINT_PLANS[-1]["durable_events"][-2]),
        )
        self.assertEqual(
            terminal["last_completed_checkpoint"],
            dict(protocol.PER_RECORD_CHECKPOINT_PLANS[-1]["durable_events"][-1]),
        )

    def test_failure_artifact_is_exception_type_only_and_closed(self) -> None:
        journal = self._failure(self._append_record_prefix(self._session(), 0, 5))
        failure = contract.build_diagnostic_failure(
            implementation_freeze_commit=self.implementation_commit,
            preregistration_payload=self.preregistration_payload,
            attempt_owner_payload=self.owner_payload,
            progress_payload=journal,
            implementation_context=self._implementation_context(),
        )
        contract.validate_diagnostic_failure(
            failure,
            implementation_freeze_commit=self.implementation_commit,
            preregistration_payload=self.preregistration_payload,
            attempt_owner_payload=self.owner_payload,
            progress_payload=journal,
            implementation_context=self._implementation_context(),
        )
        encoded = contract.artifact_json_bytes(failure).decode()
        for forbidden in (
            "private exception detail",
            "Traceback (most recent call last)",
            "sk-secret",
            "C:\\\\private\\\\path",
        ):
            self.assertNotIn(forbidden, encoded)
        self.assertEqual(failure["exception_type"], "RuntimeError")
        self.assertFalse(failure["decision"]["checkpoint_interval_is_causal_origin"])

    def test_unsafe_exception_types_are_rejected(self) -> None:
        base = self._session(length=1)
        for value in (
            "Runtime Error",
            "module.RuntimeError",
            "../RuntimeError",
            "A" * 97,
            "秘密",
        ):
            with (
                self.subTest(value=value),
                self.assertRaises(contract.MM005GenerationFailureDiagnosticResultError),
            ):
                self._failure(base, value)

    def test_case_summary_contains_no_arbitrary_model_text(self) -> None:
        digest = contract.sha256_bytes(b"input")
        case = {
            "record_id": protocol.DIAGNOSTIC_CASE_ORDER[0],
            "raw_output": "do not persist this arbitrary model string",
            "compiled_output": {"answer": "also hidden"},
            "verdict": {"valid": False},
            "citation_semantics": {"safe": True},
            "generated_tokens": 3,
            "latency_seconds": 1.5,
            "model_payload_sha256": digest,
            "prompt_projection_sha256": digest,
            "source_count": 1,
            "screenshot_sha256": [digest],
            "source_snapshot_sha256": [digest],
        }
        summary = contract.build_case_result_summary(case, diagnostic_index=0)
        encoded = contract.artifact_json_bytes(summary).decode()
        self.assertNotIn("do not persist", encoded)
        self.assertNotIn("also hidden", encoded)
        self.assertFalse(summary["arbitrary_model_text_persisted"])

    def test_record_order_cross_record_and_checkpoint_mutations_fail(self) -> None:
        base = self._session()
        wrong_id = protocol.DIAGNOSTIC_CASE_ORDER[1]
        with self.assertRaises(contract.MM005GenerationFailureDiagnosticResultError):
            self._append(
                base,
                protocol.DIAGNOSTIC_CHECKPOINTS[0],
                record_id=wrong_id,
                diagnostic_index=1,
            )
        base = self._append_record_prefix(base, 0, 1)
        with self.assertRaises(contract.MM005GenerationFailureDiagnosticResultError):
            self._append(
                base,
                protocol.DIAGNOSTIC_CHECKPOINTS[1],
                record_id=protocol.DIAGNOSTIC_CASE_ORDER[1],
                diagnostic_index=1,
            )
        with self.assertRaises(contract.MM005GenerationFailureDiagnosticResultError):
            self._append(
                base,
                protocol.DIAGNOSTIC_CHECKPOINTS[2],
                record_id=protocol.DIAGNOSTIC_CASE_ORDER[0],
                diagnostic_index=0,
            )

    def test_terminal_mutations_and_post_terminal_continuation_fail(self) -> None:
        success = self._success_journal()
        with self.assertRaises(contract.MM005GenerationFailureDiagnosticResultError):
            self._append(
                success,
                "failure_terminal_ready",
                captured_at_utc="2026-08-30T00:00:01Z",
                exception_type="RuntimeError",
            )
        failure = self._failure(self._session(length=1))
        with self.assertRaises(contract.MM005GenerationFailureDiagnosticResultError):
            self._append(
                failure, "context_preflight_completed", environment=self.environment
            )
        value = json.loads(failure.splitlines(keepends=True)[-1])
        value["terminal"]["continue_after_failure"] = True
        tampered = b"".join(
            failure.splitlines(keepends=True)[:-1]
        ) + contract.artifact_json_bytes(value)
        with self.assertRaises(contract.MM005GenerationFailureDiagnosticResultError):
            contract.validate_progress_journal(
                tampered,
                implementation_freeze_commit=self.implementation_commit,
                preregistration_payload=self.preregistration_payload,
                attempt_owner_payload=self.owner_payload,
            )

    def test_result_failure_reseal_missing_and_extra_fields_fail(self) -> None:
        result_inputs = {
            "implementation_freeze_commit": self.implementation_commit,
            "preregistration_payload": self.preregistration_payload,
            "attempt_owner_payload": self.owner_payload,
            "progress_payload": self._success_journal(),
            "implementation_context": self._implementation_context(),
        }
        result = contract.build_diagnostic_result(**result_inputs)
        for mutation in ("missing", "extra", "reseal"):
            changed = copy.deepcopy(result)
            if mutation == "missing":
                changed.pop("limitations")
            elif mutation == "extra":
                changed["unexpected"] = False
            else:
                changed["claims"]["runtime_eligible"] = True
                without = {
                    key: value
                    for key, value in changed.items()
                    if key != "report_digest"
                }
                changed["report_digest"] = contract.sha256_bytes(
                    contract.artifact_json_bytes(without)
                )
            with (
                self.subTest(mutation=mutation),
                self.assertRaises(contract.MM005GenerationFailureDiagnosticResultError),
            ):
                contract.validate_diagnostic_result(changed, **result_inputs)

    def test_partial_tail_recovery_binds_without_claiming_it(self) -> None:
        journal = self._session(length=2)
        events, prefix, tail = contract.recover_progress_prefix(
            journal + b'{"partial":',
            implementation_freeze_commit=self.implementation_commit,
            preregistration_payload=self.preregistration_payload,
            attempt_owner_payload=self.owner_payload,
        )
        self.assertEqual(len(events), 2)
        self.assertEqual(prefix, journal)
        self.assertFalse(tail["authenticated_event"])
        self.assertFalse(tail["execution_fact_claimed"])
        terminal_payload = self._append(
            prefix,
            "failure_terminal_ready",
            captured_at_utc="2026-08-30T00:00:00Z",
            exception_type="RuntimeError",
            discarded_progress_tail=tail,
        )
        terminal = contract.validate_progress_journal(
            terminal_payload,
            implementation_freeze_commit=self.implementation_commit,
            preregistration_payload=self.preregistration_payload,
            attempt_owner_payload=self.owner_payload,
        )[-1]
        self.assertEqual(terminal["terminal"]["discarded_progress_tail"], tail)

    def test_runner_plan_and_check_are_read_only_and_ambient_stable(self) -> None:
        before = runner._output_topology()
        plan = runner.run(mode="plan")
        checked = runner.run(mode="check")
        after = runner._output_topology()
        self.assertEqual(before, after)
        self.assertTrue(plan["runner_plan_valid"])
        self.assertTrue(checked["implementation_check_valid"])
        self.assertFalse(plan["formal_execution_eligible"])
        self.assertFalse(plan["diagnostic_execution_authorized"])
        self.assertFalse(plan["execution_path_invoked_by_gate"])

    def test_authority_present_plan_and_check_never_enter_execute_path(self) -> None:
        topology = {name: False for name in runner._output_topology()}
        topology["execution_authority"] = True
        authority_context = {
            "authority_payload": self.authority_payload,
            "published": False,
        }
        original_read = runner._read_regular_file_once

        def read_bound(path: Path) -> bytes:
            if path == ROOT / contract.EXECUTION_AUTHORITY_PATH:
                return self.authority_payload
            return original_read(path)

        with (
            mock.patch.object(runner, "_output_topology", return_value=topology),
            mock.patch.object(
                runner,
                "_optional_execution_authority_context",
                return_value=authority_context,
            ),
            mock.patch.object(
                runner, "_read_regular_file_once", side_effect=read_bound
            ),
            mock.patch.object(
                runner, "_execute_authorized_diagnostic", side_effect=AssertionError
            ),
            mock.patch.object(
                runner, "_reconcile_claimed_execution", side_effect=AssertionError
            ),
        ):
            plan = runner.run(mode="plan")
            checked = runner.run(mode="check")
        self.assertTrue(plan["execution_authority_present"])
        self.assertTrue(plan["execution_authority_valid"])
        self.assertFalse(plan["execution_path_invoked_by_gate"])
        self.assertFalse(checked["runner_check_valid"])

    def test_published_authority_requires_exact_introduction_head(self) -> None:
        topology = {name: False for name in runner._output_topology()}
        context = {
            "published": True,
            "authority_freeze_commit": self.authority_commit,
        }
        with (
            mock.patch.object(runner, "_output_topology", return_value=topology),
            mock.patch.object(
                runner, "_optional_execution_authority_context", return_value=context
            ),
            mock.patch.object(
                runner, "_require_aligned_clean_master", return_value="d" * 40
            ),
            mock.patch.object(
                runner, "_require_reserved_sibling_staging_absent"
            ) as staging_check,
            self.assertRaisesRegex(RuntimeError, "authority introduction commit"),
        ):
            runner._published_execution_authority_context()
        staging_check.assert_not_called()

        with (
            mock.patch.object(runner, "_output_topology", return_value=topology),
            mock.patch.object(
                runner, "_optional_execution_authority_context", return_value=context
            ),
            mock.patch.object(
                runner,
                "_require_aligned_clean_master",
                return_value=self.authority_commit,
            ),
            mock.patch.object(
                runner, "_require_reserved_sibling_staging_absent"
            ) as staging_check,
        ):
            self.assertEqual(runner._published_execution_authority_context(), context)
        staging_check.assert_called_once_with()

    def test_pre_and_post_claim_lineage_drift_block_dependency_load_and_session(
        self,
    ) -> None:
        from fullcycle_bridge import (  # noqa: PLC0415
            mm005_browser_research_model_evaluation_protocol_v2 as v2_contract,
        )
        from scripts import (  # noqa: PLC0415
            prepare_mm005_browser_research_model_evaluation_v2 as v2_builder,
        )
        from scripts import (  # noqa: PLC0415
            run_mm003_post_training_eval_repeatability as repeat_runner,
        )
        from scripts import (  # noqa: PLC0415
            run_mm003_qlora_post_training_v2 as upstream_runner,
        )
        from scripts import (  # noqa: PLC0415
            run_mm005_browser_research_model_evaluation as v1_runner,
        )
        from scripts import (  # noqa: PLC0415
            run_mm005_browser_research_model_evaluation_v2 as v2_runner,
        )

        artifact_payloads = v2_builder.execution_inputs()["artifact_payloads"]
        frozen_model = mock.Mock()
        frozen_dataset = mock.Mock(payloads=artifact_payloads)
        lifecycle = mock.Mock()
        output_parent_guard = mock.Mock()

        class Context:
            def __init__(self, value: object) -> None:
                self.value = value

            def __enter__(self) -> object:
                return self.value

            def __exit__(self, *_args: object) -> None:
                return None

        authority_context = {
            "authority": json.loads(self.authority_payload),
            "authority_payload": self.authority_payload,
            "authority_freeze_commit": self.authority_commit,
            "implementation_freeze_commit": self.implementation_commit,
            "implementation_context": self._implementation_context(),
            "protocol_context": {
                "preregistration_payload": self.preregistration_payload,
            },
        }
        scenarios: tuple[tuple[str, object, int], ...] = (
            (
                "before_claim",
                RuntimeError("HEAD changed before claim"),
                0,
            ),
            (
                "during_claim_publication",
                [None, RuntimeError("HEAD changed during claim publication")],
                1,
            ),
        )
        for name, lineage_effect, expected_claims in scenarios:
            with (
                self.subTest(name=name),
                mock.patch.object(v2_contract, "validate_preregistration"),
                mock.patch.object(v2_runner, "_validate_formal_python_execution_mode"),
                mock.patch.object(upstream_runner, "_validate_local_dependency_wheel"),
                mock.patch.object(runner, "_require_unclaimed_execution_state"),
                mock.patch.object(
                    runner.recovery_io,
                    "DirectoryTreeGuard",
                    return_value=output_parent_guard,
                ),
                mock.patch.object(runner.recovery_io, "ensure_lock_directory"),
                mock.patch.object(
                    repeat_runner,
                    "_FrozenInputFileSet",
                    return_value=Context(frozen_model),
                ),
                mock.patch.object(
                    v1_runner,
                    "_FrozenDatasetInputSet",
                    return_value=Context(frozen_dataset),
                ),
                mock.patch.object(
                    runner.recovery_io,
                    "ProgressLease",
                    return_value=Context(lifecycle),
                ),
                mock.patch.object(runner, "_require_runtime_outputs_absent"),
                mock.patch.object(
                    runner,
                    "_verify_execution_lineage",
                    side_effect=lineage_effect,
                ),
                mock.patch.object(runner, "_claim_output") as claim,
                mock.patch.object(
                    repeat_runner, "_load_eval_dependencies"
                ) as dependency_load,
                mock.patch.object(runner, "_run_frozen_diagnostic_session") as session,
                self.assertRaisesRegex(RuntimeError, "HEAD changed"),
            ):
                runner._execute_authorized_diagnostic(authority_context)
            self.assertEqual(claim.call_count, expected_claims)
            dependency_load.assert_not_called()
            session.assert_not_called()

    def test_claimed_snapshot_rejects_owner_from_different_authority(self) -> None:
        authority = json.loads(self.authority_payload)
        authority_context = {
            "authority": authority,
            "authority_payload": self.authority_payload,
            "authority_freeze_commit": self.authority_commit,
            "published": True,
            "implementation_freeze_commit": self.implementation_commit,
            "implementation_context": self._implementation_context(),
            "protocol_context": {
                "preregistration_payload": self.preregistration_payload,
            },
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            authority_path = root / contract.EXECUTION_AUTHORITY_PATH
            authority_path.parent.mkdir(parents=True)
            authority_path.write_bytes(self.authority_payload)
            lifecycle_path = root / protocol.LIFECYCLE_LEASE_PATH
            lifecycle_path.parent.mkdir(parents=True)
            lifecycle_path.write_bytes(
                runner._lifecycle_lease_marker(
                    authority_freeze_commit=self.authority_commit,
                    authority_payload=self.authority_payload,
                )
            )
            output_root = root / protocol.RUN_OUTPUT_ROOT
            output_root.mkdir(parents=True)
            (root / protocol.ATTEMPT_OWNER_PATH).write_bytes(self.owner_payload)
            (root / protocol.PROGRESS_PATH).write_bytes(self._session(length=1))
            with mock.patch.object(runner, "ROOT", root):
                snapshot = runner._claimed_execution_snapshot(authority_context)
            self.assertFalse(snapshot["terminal_artifact_valid"])

            changed_environment = dict(self.environment)
            changed_environment["python"] = "0.0.0"
            other_authority_payload = contract.artifact_json_bytes(
                contract.build_execution_authority_contract(
                    implementation_freeze_commit=self.implementation_commit,
                    expected_environment=changed_environment,
                    critical_execution_dependency_receipts=self.dependency_receipts,
                )
            )
            other_owner = contract.build_attempt_owner(
                implementation_freeze_commit=self.implementation_commit,
                preregistration_payload=self.preregistration_payload,
                authority_freeze_commit=self.authority_commit,
                execution_authority_payload=other_authority_payload,
                attempt_id="d" * 64,
            )
            other_owner_payload = contract.artifact_json_bytes(other_owner)
            other_genesis = contract.build_progress_event(
                previous_journal_payload=b"",
                implementation_freeze_commit=self.implementation_commit,
                preregistration_payload=self.preregistration_payload,
                attempt_owner_payload=other_owner_payload,
                event="attempt_claimed",
            )
            (root / protocol.ATTEMPT_OWNER_PATH).write_bytes(other_owner_payload)
            (root / protocol.PROGRESS_PATH).write_bytes(
                contract.artifact_json_bytes(other_genesis)
            )
            with (
                mock.patch.object(runner, "ROOT", root),
                self.assertRaises(RuntimeError),
            ):
                runner._claimed_execution_snapshot(authority_context)

    def test_reconciliation_terminalizes_without_rerun_and_lineage_failure_does_not(
        self,
    ) -> None:
        authority = json.loads(self.authority_payload)
        authority_context = {
            "authority": authority,
            "authority_payload": self.authority_payload,
            "authority_freeze_commit": self.authority_commit,
            "published": True,
            "implementation_freeze_commit": self.implementation_commit,
            "implementation_context": self._implementation_context(),
            "protocol_context": {
                "preregistration_payload": self.preregistration_payload,
            },
        }

        def write_claim(root: Path) -> bytes:
            authority_path = root / contract.EXECUTION_AUTHORITY_PATH
            authority_path.parent.mkdir(parents=True)
            authority_path.write_bytes(self.authority_payload)
            lifecycle_path = root / protocol.LIFECYCLE_LEASE_PATH
            lifecycle_path.parent.mkdir(parents=True)
            lifecycle_path.write_bytes(
                runner._lifecycle_lease_marker(
                    authority_freeze_commit=self.authority_commit,
                    authority_payload=self.authority_payload,
                )
            )
            output_root = root / protocol.RUN_OUTPUT_ROOT
            output_root.mkdir(parents=True)
            genesis = self._session(length=1)
            (root / protocol.ATTEMPT_OWNER_PATH).write_bytes(self.owner_payload)
            (root / protocol.PROGRESS_PATH).write_bytes(genesis)
            return genesis

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            genesis = write_claim(root)
            with (
                mock.patch.object(runner, "ROOT", root),
                mock.patch.object(
                    runner,
                    "_enter_frozen_input_guards",
                    return_value=(mock.Mock(), mock.Mock()),
                ),
                mock.patch.object(runner, "_verify_execution_lineage"),
                mock.patch.object(
                    runner, "_run_frozen_diagnostic_session", side_effect=AssertionError
                ),
                self.assertRaises(RuntimeError),
            ):
                runner._reconcile_claimed_execution(authority_context)
            failure_payload = (root / protocol.FAILURE_PATH).read_bytes()
            progress_payload = (root / protocol.PROGRESS_PATH).read_bytes()
            self.assertGreater(len(progress_payload), len(genesis))
            self.assertEqual(
                contract.validate_progress_journal(
                    progress_payload,
                    implementation_freeze_commit=self.implementation_commit,
                    preregistration_payload=self.preregistration_payload,
                    attempt_owner_payload=self.owner_payload,
                )[-1]["event"],
                "failure_terminal_ready",
            )
            self.assertEqual(
                contract.artifact_json_bytes(
                    contract.parse_strict_json_bytes(
                        failure_payload, location="$.diagnostic_failure"
                    )
                ),
                failure_payload,
            )

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            genesis = write_claim(root)
            with (
                mock.patch.object(runner, "ROOT", root),
                mock.patch.object(
                    runner,
                    "_enter_frozen_input_guards",
                    return_value=(mock.Mock(), mock.Mock()),
                ),
                mock.patch.object(
                    runner,
                    "_verify_execution_lineage",
                    side_effect=RuntimeError("frozen input drift"),
                ),
                self.assertRaises(RuntimeError),
            ):
                runner._reconcile_claimed_execution(authority_context)
            self.assertEqual((root / protocol.PROGRESS_PATH).read_bytes(), genesis)
            self.assertFalse((root / protocol.FAILURE_PATH).exists())

    def test_post_claim_lineage_check_is_output_tolerant_and_fail_closed(self) -> None:
        frozen_model = mock.Mock()
        frozen_dataset = mock.Mock()
        authority_source_context = {"freeze_commit": self.authority_commit}
        protocol_context = {"protocol_source_files": 13}
        implementation_context = self._implementation_context()
        authority_context = {
            "authority": json.loads(self.authority_payload),
            "authority_payload": self.authority_payload,
            "authority_freeze_commit": self.authority_commit,
            "authority_source_context": authority_source_context,
            "implementation_freeze_commit": self.implementation_commit,
            "implementation_context": implementation_context,
            "protocol_context": protocol_context,
        }
        with (
            mock.patch.object(
                runner,
                "_read_regular_file_once",
                return_value=self.authority_payload,
            ),
            mock.patch.object(
                runner,
                "_published_protocol_context",
                return_value=protocol_context,
            ),
            mock.patch.object(
                runner,
                "_implementation_source_context",
                return_value=implementation_context,
            ),
            mock.patch.object(
                runner,
                "_authority_source_context",
                return_value=authority_source_context,
            ),
            mock.patch.object(
                runner,
                "_optional_execution_authority_context",
                side_effect=AssertionError,
            ),
            mock.patch.object(
                runner,
                "_require_aligned_clean_master",
                return_value=self.authority_commit,
            ),
        ):
            runner._verify_execution_lineage(
                authority_context,
                frozen_model=frozen_model,
                frozen_dataset=frozen_dataset,
            )
            with (
                mock.patch.object(
                    runner,
                    "_implementation_source_context",
                    return_value={"freeze_commit": "e" * 40},
                ),
                self.assertRaises(RuntimeError),
            ):
                runner._verify_execution_lineage(
                    authority_context,
                    frozen_model=frozen_model,
                    frozen_dataset=frozen_dataset,
                )
        frozen_model.verify.assert_called()
        frozen_dataset.verify.assert_called()

    def test_execute_is_denied_before_topology_git_claim_or_model_body(self) -> None:
        denied = runner.MM005DiagnosticExecutionAuthorityRequired(
            "SEPARATE_EXECUTION_AUTHORITY_AND_RESOURCE_PREFLIGHT_REQUIRED"
        )
        with (
            mock.patch.object(
                runner,
                "_published_execution_authority_context",
                side_effect=denied,
            ),
            mock.patch.object(
                runner, "_execute_authorized_diagnostic", side_effect=AssertionError
            ),
            mock.patch.object(
                runner, "_reconcile_claimed_execution", side_effect=AssertionError
            ),
            self.assertRaises(runner.MM005DiagnosticExecutionAuthorityRequired),
        ):
            runner.run(mode="execute")
        with self.assertRaises(RuntimeError):
            runner.run(mode="")

    def test_execute_with_claimed_output_routes_only_to_reconciliation(self) -> None:
        topology = {name: False for name in runner._output_topology()}
        topology.update(
            {
                "execution_authority": True,
                "output_root": True,
                "attempt_owner": True,
                "progress": True,
                "lifecycle_lease_root": True,
                "lifecycle_lease": True,
            }
        )
        expected = {"reconciled_without_model_rerun": True}
        with (
            mock.patch.object(
                runner,
                "_published_execution_authority_context",
                return_value={"published": True},
            ),
            mock.patch.object(runner, "_output_topology", return_value=topology),
            mock.patch.object(
                runner, "_reconcile_claimed_execution", return_value=expected
            ) as reconcile,
            mock.patch.object(
                runner, "_execute_authorized_diagnostic", side_effect=AssertionError
            ),
        ):
            self.assertEqual(runner.run(mode="execute"), expected)
        reconcile.assert_called_once()

    def test_topology_shape_and_unauthenticated_runtime_state_fail_closed(self) -> None:
        empty = {name: False for name in runner._output_topology()}
        runner._validate_output_topology(empty)
        authority_only = dict(empty)
        authority_only["execution_authority"] = True
        runner._validate_output_topology(authority_only)
        self.assertFalse(
            runner._inspect_read_only_execution_state(authority_only, {})[
                "diagnostic_attempt_consumed"
            ]
        )
        for changed in (
            {key: value for key, value in empty.items() if key != "progress"},
            {**empty, "progress": 1},
        ):
            with self.assertRaises(RuntimeError):
                runner._validate_output_topology(changed)
        output_without_authority = dict(empty)
        output_without_authority["output_root"] = True
        with self.assertRaises(RuntimeError):
            runner._inspect_read_only_execution_state(
                output_without_authority, authority_context=None
            )

    def test_atomic_owner_genesis_claim_is_exclusive(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / Path(protocol.RUN_OUTPUT_ROOT).parent).mkdir(parents=True)
            genesis = self._session(length=1)
            with mock.patch.object(runner, "ROOT", root):
                runner._claim_output(
                    attempt_id="b" * 64,
                    owner_payload=self.owner_payload,
                    genesis_payload=genesis,
                )
                output = root / protocol.RUN_OUTPUT_ROOT
                self.assertEqual(
                    {item.name for item in output.iterdir()},
                    {"attempt-owner.json", "progress.json"},
                )
                with self.assertRaises(FileExistsError):
                    runner._claim_output(
                        attempt_id="b" * 64,
                        owner_payload=self.owner_payload,
                        genesis_payload=genesis,
                    )

    def test_owner_staging_crashes_block_every_later_claim(self) -> None:
        original_write = runner.recovery_io.write_exclusive_fsync
        original_rename = runner.os.rename
        genesis = self._session(length=1)
        for phase in ("after_mkdir", "after_owner", "before_rename"):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                parent = root / Path(protocol.RUN_OUTPUT_ROOT).parent
                parent.mkdir(parents=True)
                write_count = 0

                def crash_write(path: Path, payload: bytes) -> None:
                    nonlocal write_count
                    write_count += 1
                    if phase == "after_mkdir" and write_count == 1:
                        raise RuntimeError("simulated process interruption")
                    if phase == "after_owner" and write_count == 2:
                        raise RuntimeError("simulated process interruption")
                    original_write(path, payload)

                def crash_rename(source: Path, destination: Path) -> None:
                    if phase == "before_rename":
                        raise RuntimeError("simulated process interruption")
                    original_rename(source, destination)

                with (
                    mock.patch.object(runner, "ROOT", root),
                    mock.patch.object(
                        runner.recovery_io,
                        "write_exclusive_fsync",
                        side_effect=crash_write,
                    ),
                    mock.patch.object(runner.os, "rename", side_effect=crash_rename),
                    self.assertRaises(RuntimeError),
                ):
                    runner._claim_output(
                        attempt_id="b" * 64,
                        owner_payload=self.owner_payload,
                        genesis_payload=genesis,
                    )

                reserved = [
                    item
                    for item in parent.iterdir()
                    if item.name.startswith(f".{Path(protocol.RUN_OUTPUT_ROOT).name}.")
                ]
                self.assertEqual(len(reserved), 1)
                self.assertFalse((root / protocol.RUN_OUTPUT_ROOT).exists())
                with (
                    mock.patch.object(runner, "ROOT", root),
                    self.assertRaisesRegex(RuntimeError, "staging requires review"),
                ):
                    runner._claim_output(
                        attempt_id="d" * 64,
                        owner_payload=self.owner_payload,
                        genesis_payload=genesis,
                    )
                self.assertEqual(
                    len(
                        [
                            item
                            for item in parent.iterdir()
                            if item.name.startswith(
                                f".{Path(protocol.RUN_OUTPUT_ROOT).name}."
                            )
                        ]
                    ),
                    1,
                )

    def test_lifecycle_and_unknown_staging_block_every_new_attempt(self) -> None:
        original_write = runner.recovery_io.write_exclusive_fsync
        original_rename = runner.os.rename
        for phase in ("after_mkdir", "before_rename"):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                parent = root / Path(protocol.RUN_OUTPUT_ROOT).parent
                parent.mkdir(parents=True)
                lifecycle_path = root / protocol.LIFECYCLE_LEASE_PATH

                def crash_write(path: Path, payload: bytes) -> None:
                    if phase == "after_mkdir":
                        raise RuntimeError("simulated process interruption")
                    original_write(path, payload)

                def crash_rename(source: Path, destination: Path) -> None:
                    if phase == "before_rename":
                        raise RuntimeError("simulated process interruption")
                    original_rename(source, destination)

                with (
                    mock.patch.object(runner, "ROOT", root),
                    mock.patch.object(
                        runner.recovery_io,
                        "write_exclusive_fsync",
                        side_effect=crash_write,
                    ),
                    mock.patch.object(runner.os, "rename", side_effect=crash_rename),
                    self.assertRaises(RuntimeError),
                ):
                    runner.recovery_io.ensure_lock_directory(lifecycle_path, b"lease")
                with (
                    mock.patch.object(runner, "ROOT", root),
                    self.assertRaisesRegex(RuntimeError, "staging requires review"),
                ):
                    runner._require_unclaimed_execution_state({})

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            parent = root / Path(protocol.RUN_OUTPUT_ROOT).parent
            parent.mkdir(parents=True)
            unknown = parent / f".{Path(protocol.RUN_OUTPUT_ROOT).name}.unknown"
            unknown.mkdir()
            with (
                mock.patch.object(runner, "ROOT", root),
                self.assertRaisesRegex(RuntimeError, "staging requires review"),
            ):
                runner._require_unclaimed_execution_state({})

    def test_plan_check_and_unified_gate_reject_reserved_staging(self) -> None:
        from scripts import validate_offline  # noqa: PLC0415

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            parent = root / Path(protocol.RUN_OUTPUT_ROOT).parent
            parent.mkdir(parents=True)
            reserved = parent / f".{Path(protocol.RUN_OUTPUT_ROOT).name}.owner-stale"
            reserved.mkdir()
            protocol_context = {
                "preregistration_payload": self.preregistration_payload,
                "protocol_source_files": 13,
            }
            with (
                mock.patch.object(runner, "ROOT", root),
                mock.patch.object(runner, "_git_text", return_value="e" * 40),
                mock.patch.object(
                    runner,
                    "_published_protocol_context",
                    return_value=protocol_context,
                ),
                mock.patch.object(
                    runner, "_implementation_source_receipts", return_value={}
                ),
            ):
                for mode in ("plan", "check"):
                    with (
                        self.subTest(mode=mode),
                        self.assertRaisesRegex(RuntimeError, "staging requires review"),
                    ):
                        runner.run(mode=mode)
            with (
                mock.patch.object(runner, "ROOT", root),
                mock.patch.object(validate_offline, "ROOT", root),
                self.assertRaisesRegex(
                    validate_offline.GateError, "authority and outputs absent"
                ),
            ):
                validate_offline._validate_mm005_browser_research_generation_failure_diagnostic_implementation()

    def test_read_only_state_accepts_a_safe_missing_output_parent(self) -> None:
        from scripts import validate_offline  # noqa: PLC0415

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.assertFalse((root / Path(protocol.RUN_OUTPUT_ROOT).parent).exists())
            protocol_context = {
                "preregistration_payload": self.preregistration_payload,
                "protocol_source_files": 13,
            }
            with (
                mock.patch.object(runner, "ROOT", root),
                mock.patch.object(runner, "_git_text", return_value="e" * 40),
                mock.patch.object(
                    runner,
                    "_published_protocol_context",
                    return_value=protocol_context,
                ),
                mock.patch.object(
                    runner, "_implementation_source_receipts", return_value={}
                ),
                mock.patch.object(
                    runner,
                    "_read_repository_file",
                    return_value=self.preregistration_payload,
                ),
            ):
                for mode in ("plan", "check"):
                    summary = runner.run(mode=mode)
                    self.assertFalse(summary["reserved_sibling_staging_present"])
            with (
                mock.patch.object(runner, "ROOT", root),
                mock.patch.object(validate_offline, "ROOT", root),
            ):
                presence = validate_offline._mm005_generation_failure_diagnostic_runtime_presence(
                    protocol=protocol,
                    contract=contract,
                    runner=runner,
                )
            self.assertTrue(all(value is False for value in presence.values()))

    def test_git_name_only_paths_preserve_unicode_with_quotepath_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            def git(*args: str, capture: bool = False) -> str:
                completed = subprocess.run(
                    ["git", *args],
                    cwd=root,
                    check=True,
                    stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                return completed.stdout.strip() if capture else ""

            git("init", "-q")
            git("config", "user.name", "MM005 Test")
            git("config", "user.email", "mm005@example.invalid")
            git("config", "core.quotepath", "true")
            (root / "README.md").write_text("base\n", encoding="utf-8")
            git("add", "README.md")
            git("commit", "-qm", "base")
            base = git("rev-parse", "HEAD", capture=True)
            unicode_path = "AI_Infra_LLM_Agent_待做任务清单.md"
            (root / unicode_path).write_text("scope\n", encoding="utf-8")
            git("add", unicode_path)
            git("commit", "-qm", "unicode")
            head = git("rev-parse", "HEAD", capture=True)
            with mock.patch.object(runner, "ROOT", root):
                self.assertEqual(
                    runner._git_name_only_paths(base, head), (unicode_path,)
                )

    def test_hidden_git_index_flags_are_rejected_in_a_real_repository(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            def git(*args: str) -> None:
                subprocess.run(
                    ["git", *args],
                    cwd=root,
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                )

            git("init", "-q")
            git("config", "user.name", "MM005 Test")
            git("config", "user.email", "mm005@example.invalid")
            (root / "tracked.txt").write_text("tracked\n", encoding="utf-8")
            git("add", "tracked.txt")
            git("commit", "-qm", "tracked")
            with mock.patch.object(runner, "ROOT", root):
                runner._require_no_hidden_index_flags()
                git("update-index", "--assume-unchanged", "tracked.txt")
                with self.assertRaisesRegex(RuntimeError, "index flag"):
                    runner._require_no_hidden_index_flags()
                git("update-index", "--no-assume-unchanged", "tracked.txt")
                git("update-index", "--skip-worktree", "tracked.txt")
                with self.assertRaisesRegex(RuntimeError, "index flag"):
                    runner._require_no_hidden_index_flags()
                git("update-index", "--no-skip-worktree", "tracked.txt")
                runner._require_no_hidden_index_flags()
                git("config", "core.fsmonitor", "true")
                (root / "tracked.txt").write_text("changed\n", encoding="utf-8")
                git("update-index", "--fsmonitor-valid", "tracked.txt")
                self.assertIn(
                    "tracked.txt",
                    runner._git_text(
                        "status", "--porcelain=v1", "--untracked-files=all"
                    ),
                )

    def test_fake_case_producer_emits_exact_eighteen_events_and_closes_images(
        self,
    ) -> None:
        digest = contract.sha256_bytes(b"input")

        class FakeImage:
            closed = False

            def convert(self, _mode: str) -> FakeImage:
                return converted_image

            def close(self) -> None:
                self.closed = True

        source_image = FakeImage()
        converted_image = FakeImage()

        class FakeImageClass:
            @staticmethod
            def open(_stream: object) -> FakeImage:
                return source_image

        class FakeInputs(dict[str, object]):
            def __init__(self) -> None:
                super().__init__({"input_ids": object()})
                self.input_ids = SimpleNamespace(shape=(1, 2))

            def to(self, _device: str) -> FakeInputs:
                return self

        class FakeTrimmed:
            shape = (1, 3)

        class FakeGenerated:
            def __getitem__(self, _key: object) -> FakeTrimmed:
                return FakeTrimmed()

        class FakeProcessor:
            def apply_chat_template(self, *_args: object, **_kwargs: object) -> str:
                return "prompt"

            def __call__(self, **_kwargs: object) -> FakeInputs:
                return FakeInputs()

            def batch_decode(self, *_args: object, **_kwargs: object) -> list[str]:
                return ["synthetic answer"]

        record_id = protocol.DIAGNOSTIC_CASE_ORDER[0]
        case = {
            "record_id": record_id,
            "raw_output": "synthetic answer",
            "compiled_output": None,
            "verdict": {"valid": False},
            "citation_semantics": {"safe": True},
            "generated_tokens": 3,
            "latency_seconds": 0.1,
            "model_payload_sha256": digest,
            "prompt_projection_sha256": digest,
            "source_count": 1,
            "screenshot_sha256": [digest],
            "source_snapshot_sha256": [digest],
        }
        adapted = SimpleNamespace(
            screenshot_payloads=(b"png",), model_payload=lambda: {"instruction": "x"}
        )
        fake_evaluation = SimpleNamespace(
            build_runtime_messages=lambda *_args: [{"role": "user"}],
            build_case_result=lambda **_kwargs: case,
        )
        fake_adapter = SimpleNamespace(adapt_record=lambda *_args: adapted)
        events: list[str] = []

        def append(
            event: str,
            _record_id: str | None,
            _index: int | None,
            summary: dict[str, Any] | None,
        ) -> None:
            if event == "case_result_build_completed":
                self.assertTrue(source_image.closed)
                self.assertTrue(converted_image.closed)
                self.assertIsNotNone(summary)
            events.append(event)

        summary = runner._run_one_diagnostic_case(
            torch=SimpleNamespace(cuda=SimpleNamespace(synchronize=lambda: None)),
            model=SimpleNamespace(generate=lambda **_kwargs: FakeGenerated()),
            processor=FakeProcessor(),
            evaluation=fake_evaluation,
            adapter_verifier=fake_adapter,
            image_class=FakeImageClass,
            record={"record_id": record_id},
            record_id=record_id,
            diagnostic_index=0,
            artifact_payloads={},
            screenshot_payloads={},
            snapshot_payloads={},
            append_progress=append,
        )
        self.assertEqual(events, list(protocol.DIAGNOSTIC_CHECKPOINTS))
        self.assertEqual(summary["record_id"], record_id)
        self.assertFalse(summary["arbitrary_model_text_persisted"])

    def test_runner_ast_has_explicit_modes_lazy_heavy_imports_and_no_authority_bypass(
        self,
    ) -> None:
        source = (
            ROOT / contract.IMPLEMENTATION_SOURCE_PATHS["diagnostic_runner"]
        ).read_text(encoding="utf-8")
        tree = ast.parse(source)
        top_imports = {
            alias.name.split(".")[0]
            for node in tree.body
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        self.assertFalse(
            top_imports & {"torch", "PIL", "transformers", "peft", "bitsandbytes"}
        )
        self.assertIn("add_mutually_exclusive_group(required=True)", source)
        self.assertIn('if mode == "execute":', source)
        self.assertLess(
            source.index('if mode == "execute":'), source.index("_output_topology()")
        )
        self.assertNotIn("os.environ.get", source)
        self.assertNotIn("diagnostic_execution_authorized=True", source)
        self.assertNotIn("retry(", source.lower())
        self.assertLess(
            source.index("_enable_offline_execution()"),
            source.index("_OfflineSocketGuard"),
        )
        self.assertLess(
            source.index("_OfflineSocketGuard"),
            source.index("_load_eval_dependencies()"),
        )
        self.assertLess(
            source.index("output_parent_guard"),
            source.index("ensure_lock_directory"),
        )
        self.assertIn("_reconcile_claimed_execution(authority_context)", source)


if __name__ == "__main__":
    unittest.main()
