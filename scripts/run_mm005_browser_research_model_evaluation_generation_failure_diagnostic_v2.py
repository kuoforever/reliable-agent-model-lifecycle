"""Plan or inspect the frozen MM-005 generation-diagnostic implementation v2.

This implementation slice does not contain execution authority.  ``--execute``
therefore fails before any lease, output claim, heavy dependency import, or
model/CUDA call.  The private producer functions freeze the future checkpoint
topology for review; a separate authority/resource-preflight gate must bind and
enable them later.
"""

from __future__ import annotations

import argparse
import gc
import io
import json
import os
import re
import secrets
import stat
import subprocess
import sys
import time
from collections.abc import Callable, Collection, Mapping, Sequence
from contextlib import ExitStack
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Literal, NoReturn

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
    mm005_browser_research_model_evaluation_generation_failure_diagnostic_result_v2 as result_contract,
)
from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_model_evaluation_protocol_v2 as v2,
)
from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_model_evaluation_recovery_io as recovery_io,
)
from scripts import (  # noqa: E402
    prepare_mm005_browser_research_model_evaluation_generation_failure_diagnostic_protocol_v2 as protocol_builder,
)

MAX_BOUND_FILE_BYTES = 64 * 1024 * 1024
MODE_CHOICES = ("plan", "check", "execute")
RUNTIME_OUTPUT_KEYS = frozenset(
    {
        "output_root",
        "attempt_owner",
        "progress",
        "success_result",
        "failure",
        "lifecycle_lease_root",
        "lifecycle_lease",
        "reserved_sibling_staging",
    }
)
IMPLEMENTATION_SLICE_PATHS = frozenset(
    {
        "AI_Infra_LLM_Agent_待做任务清单.md",
        "PROJECT_STATUS.md",
        "README.md",
        "docs/MM-005-browser-research-model-evaluation-generation-failure-"
        "diagnostic-implementation-v2.md",
        "docs/MM-005-browser-research-model-evaluation-generation-failure-"
        "diagnostic-protocol-v2.md",
        "docs/README.md",
        "scripts/validate_offline.py",
        (
            "tests/test_mm005_browser_research_model_evaluation_generation_"
            "failure_diagnostic_protocol_v2.py"
        ),
        *result_contract.IMPLEMENTATION_SOURCE_PATHS.values(),
    }
)
ProgressAppender = Callable[
    [str, str | None, int | None, Mapping[str, Any] | None], None
]
_SHA256_PATTERN = re.compile(r"sha256:[0-9a-f]{64}")


@dataclass(frozen=True)
class _TrackedExecutionSource:
    """One already-validated repository source rebound during execution."""

    name: str
    relative_path: str
    payload: bytes


@dataclass(frozen=True)
class _ValidatedExecutionContext:
    """Closed pre-heavy context produced only after authority preflight.

    Production constructs this value from a published authority.  Focused
    model-free tests may construct the same closed value against a temporary
    Git repository; there is no CLI, environment-variable, or public API
    bypass for authority validation.
    """

    repository_root: Path
    protocol_merge_commit: str
    zero_bandwidth_maintenance_commit: str
    implementation_base_commit: str
    initial_implementation_publication_commit: str
    implementation_freeze_commit: str
    authority_freeze_commit: str
    authority_payload: bytes
    preregistration_payload: bytes
    implementation_context_payload: bytes
    expected_environment_payload: bytes
    tracked_sources: tuple[_TrackedExecutionSource, ...]
    implementation_slice_paths: frozenset[str]
    authority_introduction_paths: frozenset[str]


_ExecutionPhase = Literal["pre_parent", "post_parent", "lifecycle", "claimed"]
_FirstHeavyBoundary = Callable[
    [
        _ValidatedExecutionContext,
        recovery_io.ProgressLease,
        recovery_io.ProgressLease,
        recovery_io.DirectoryTreeGuard,
        recovery_io.DirectoryTreeGuard,
        recovery_io.DirectoryTreeGuard,
        bytes,
    ],
    dict[str, Any],
]


class MM005DiagnosticExecutionAuthorityRequired(RuntimeError):
    """The implementation exists, but this gate grants no execution authority."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--plan", action="store_true")
    modes.add_argument("--check", action="store_true")
    modes.add_argument("--execute", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    mode = "plan" if args.plan else "check" if args.check else "execute"
    summary = run(mode=mode)
    print(json.dumps(summary, sort_keys=True, separators=(",", ":")))
    return 0


def run(*, mode: str) -> dict[str, Any]:
    """Run one explicit mode; there is intentionally no execution default."""

    if type(mode) is not str or mode not in MODE_CHOICES:
        raise RuntimeError("explicit diagnostic runner mode required")
    if mode == "execute":
        return _execute_published_authority()

    head_before = _git_text("rev-parse", "HEAD")
    before = _output_topology()
    _validate_output_topology(before)
    runtime_state_present = any(before[name] for name in RUNTIME_OUTPUT_KEYS)
    protocol_context = _published_protocol_context(
        allow_runtime_state=runtime_state_present
    )
    contract = result_contract.result_contract()
    implementation_sources = _implementation_source_receipts()
    authority_context = (
        _optional_execution_authority_context(allow_runtime_state=runtime_state_present)
        if before["execution_authority"]
        else None
    )
    observed_state = _inspect_read_only_execution_state(before, authority_context)
    after = _output_topology()
    _validate_output_topology(after)
    if after != before:
        raise RuntimeError("diagnostic output topology changed during read-only mode")
    if (
        _git_text("rev-parse", "HEAD") != head_before
        or _read_repository_file(protocol.PREREGISTRATION_PATH)
        != protocol_context["preregistration_payload"]
        or _implementation_source_receipts() != implementation_sources
        or (
            authority_context is not None
            and _read_regular_file_once(ROOT / result_contract.EXECUTION_AUTHORITY_PATH)
            != authority_context["authority_payload"]
        )
    ):
        raise RuntimeError("diagnostic read-only source snapshot changed")
    plan = result_contract.execution_plan()
    return {
        **plan,
        "plan_only": mode == "plan",
        "implementation_check_valid": mode == "check",
        "runner_plan_valid": mode == "plan",
        "runner_check_valid": (
            mode == "check" and observed_state["terminal_artifact_valid"]
        ),
        "execution_path_invoked_by_gate": False,
        "protocol_context_valid": True,
        "protocol_source_files": protocol_context["protocol_source_files"],
        "implementation_source_files": len(implementation_sources),
        "implementation_source_receipts": implementation_sources,
        "execution_authority_valid": authority_context is not None,
        "execution_authority_published": bool(
            authority_context is not None and authority_context["published"]
        ),
        "execution_authority_present": after["execution_authority"],
        "output_parent_present": after["output_parent"],
        "attempt_owner_present": after["attempt_owner"],
        "progress_present": after["progress"],
        "success_result_present": after["success_result"],
        "failure_present": after["failure"],
        "output_root_present": after["output_root"],
        "lifecycle_lease_present": after["lifecycle_lease"],
        "reserved_sibling_staging_present": after["reserved_sibling_staging"],
        "result_valid": observed_state["terminal_artifact_valid"],
        "terminal_reconciliation_required": observed_state[
            "terminal_reconciliation_required"
        ],
        "diagnostic_attempt_consumed": observed_state["diagnostic_attempt_consumed"],
        "diagnostic_executed": observed_state["diagnostic_executed"],
        "selected_outcome": observed_state["selected_outcome"],
        "contract_gate_id": contract["gate_id"],
    }


def _deny_missing_execution_authority() -> NoReturn:
    raise MM005DiagnosticExecutionAuthorityRequired(
        "SEPARATE_EXECUTION_AUTHORITY_AND_RESOURCE_PREFLIGHT_REQUIRED"
    )


def _execute_published_authority() -> dict[str, Any]:
    """Execute only after a separate tracked authority gate cleanly merges."""

    authority_context = _published_execution_authority_context()
    topology = _output_topology()
    _validate_output_topology(topology)
    if topology["output_root"]:
        return _reconcile_claimed_execution(authority_context)
    _require_unclaimed_execution_state(authority_context)
    return _execute_authorized_diagnostic(authority_context)


def _published_execution_authority_context() -> dict[str, Any]:
    """Fail before output/lease/heavy imports unless authority is published."""

    topology = _output_topology()
    _validate_output_topology(topology)
    context = _optional_execution_authority_context(
        allow_runtime_state=any(topology[name] for name in RUNTIME_OUTPUT_KEYS)
    )
    if context is None:
        _deny_missing_execution_authority()
    head = _require_aligned_clean_master()
    if context.get("published") is not True:
        raise RuntimeError(
            "execution authority must be cleanly merged before execution"
        )
    authority_freeze_commit = context.get("authority_freeze_commit")
    if type(authority_freeze_commit) is not str or head != authority_freeze_commit:
        raise RuntimeError(
            "execution requires HEAD equal the authority introduction commit"
        )
    _require_reserved_sibling_staging_absent()
    return context


def _optional_execution_authority_context(
    *, allow_runtime_state: bool = False
) -> dict[str, Any] | None:
    """Validate an absent, draft, or tracked authority without executing it."""

    authority_path = ROOT / result_contract.EXECUTION_AUTHORITY_PATH
    if not os.path.lexists(authority_path):
        return None
    authority_payload = _read_regular_file_once(authority_path)
    authority = result_contract.parse_strict_json_bytes(
        authority_payload, location="$.execution_authority"
    )
    preflight = _mapping(
        authority.get("resource_preflight"), "$.execution_authority.resource_preflight"
    )
    dependency_receipts = _mapping(
        authority.get("critical_execution_dependency_receipts"),
        "$.execution_authority.critical_execution_dependency_receipts",
    )
    expected = result_contract.build_execution_authority_contract(
        implementation_freeze_commit=str(authority.get("implementation_freeze_commit")),
        expected_environment=_mapping(
            preflight.get("expected_environment"),
            "$.execution_authority.resource_preflight.expected_environment",
        ),
        critical_execution_dependency_receipts=dependency_receipts,
    )
    if result_contract.artifact_json_bytes(expected) != authority_payload:
        raise RuntimeError("execution authority artifact is not canonical and exact")
    implementation_freeze_commit = str(authority["implementation_freeze_commit"])
    initial_implementation_publication_commit = str(
        authority["initial_implementation_publication_commit"]
    )
    zero_bandwidth_maintenance_commit = str(
        authority["zero_bandwidth_maintenance_commit"]
    )
    implementation_base_commit = str(authority["implementation_base_commit"])
    if (
        zero_bandwidth_maintenance_commit
        != result_contract.ZERO_BANDWIDTH_MAINTENANCE_COMMIT
    ):
        raise RuntimeError("execution authority zero-bandwidth maintenance differs")
    if implementation_base_commit != result_contract.IMPLEMENTATION_BASE_COMMIT:
        raise RuntimeError("execution authority implementation base differs")
    if (
        initial_implementation_publication_commit
        != result_contract.INITIAL_IMPLEMENTATION_PUBLICATION_COMMIT
    ):
        raise RuntimeError("execution authority initial implementation differs")
    _require_commit_ancestor(implementation_freeze_commit)
    _require_commit_ancestor(initial_implementation_publication_commit)
    _require_commit_ancestor(zero_bandwidth_maintenance_commit)
    _require_commit_ancestor(implementation_base_commit)
    _require_commit_ancestor(result_contract.PROTOCOL_MERGE_COMMIT)
    _require_unique_parent(
        zero_bandwidth_maintenance_commit, result_contract.PROTOCOL_MERGE_COMMIT
    )
    _require_unique_parent(
        implementation_base_commit, zero_bandwidth_maintenance_commit
    )
    _require_unique_parent(
        initial_implementation_publication_commit, implementation_base_commit
    )
    _require_unique_parent(
        implementation_freeze_commit, initial_implementation_publication_commit
    )
    implementation_context = _implementation_source_context(
        implementation_freeze_commit
    )
    protocol_context = _published_protocol_context(
        allow_runtime_state=allow_runtime_state
    )
    _validate_critical_execution_dependency_receipts(authority, commit=None)
    tracked = _git_path_exists("HEAD", result_contract.EXECUTION_AUTHORITY_PATH)
    authority_freeze_commit: str | None = None
    authority_source_context: dict[str, Any] | None = None
    if tracked:
        authority_source_context = _authority_source_context(
            authority_payload=authority_payload,
            implementation_freeze_commit=implementation_freeze_commit,
            authority=authority,
        )
        authority_freeze_commit = str(authority_source_context["freeze_commit"])
    return {
        "authority": authority,
        "authority_payload": authority_payload,
        "authority_freeze_commit": authority_freeze_commit,
        "authority_source_context": authority_source_context,
        "published": tracked,
        "zero_bandwidth_maintenance_commit": zero_bandwidth_maintenance_commit,
        "implementation_base_commit": implementation_base_commit,
        "initial_implementation_publication_commit": (
            initial_implementation_publication_commit
        ),
        "implementation_freeze_commit": implementation_freeze_commit,
        "implementation_context": implementation_context,
        "protocol_context": protocol_context,
    }


def _reconcile_claimed_execution(
    authority_context: Mapping[str, Any],
) -> dict[str, Any]:
    """Terminalize or repair one authenticated consumed attempt without rerun."""

    snapshot = _claimed_execution_snapshot(authority_context)
    lifecycle_path = ROOT / protocol.LIFECYCLE_LEASE_PATH
    with ExitStack() as stack:
        lifecycle = stack.enter_context(recovery_io.ProgressLease(lifecycle_path))
        frozen_model, frozen_dataset = _enter_frozen_input_guards(stack)
        journal = stack.enter_context(
            recovery_io.ProgressLease(ROOT / protocol.PROGRESS_PATH)
        )
        lifecycle.verify()
        snapshot = _claimed_execution_snapshot(authority_context)
        output_guard = snapshot["output_guard"]
        if not isinstance(output_guard, recovery_io.DirectoryTreeGuard):
            raise RuntimeError("diagnostic output guard is invalid")
        _verify_execution_lineage(
            authority_context,
            frozen_model=frozen_model,
            frozen_dataset=frozen_dataset,
        )
        terminal_kind = snapshot["terminal_kind"]
        if terminal_kind in {"success", "failure"}:
            terminal_path = snapshot["terminal_path"]
            terminal_payload = snapshot["terminal_payload"]
            terminal_value = snapshot["terminal_value"]
            if (
                not isinstance(terminal_path, Path)
                or type(terminal_payload) is not bytes
                or not isinstance(terminal_value, Mapping)
            ):
                raise RuntimeError("diagnostic terminal snapshot is invalid")
            lifecycle.verify()
            output_guard.verify()
            _verify_execution_lineage(
                authority_context,
                frozen_model=frozen_model,
                frozen_dataset=frozen_dataset,
            )
            recovery_io.write_or_repair_terminal(terminal_path, terminal_payload)
            if terminal_kind == "success":
                return {
                    **_terminal_summary(terminal_value, kind="success"),
                    "reconciled_without_model_rerun": True,
                }
            raise RuntimeError(
                "diagnostic failure terminal reconciled without model rerun"
            )

        prefix = _bytes_value(
            snapshot.get("authenticated_prefix"), "$.authenticated_prefix"
        )
        tail_receipt = snapshot.get("discarded_tail_receipt")
        if tail_receipt is not None:
            tail_receipt = _mapping(tail_receipt, "$.discarded_tail_receipt")
            journal.truncate_to_authenticated_prefix(prefix)
        elif journal.read() != prefix:
            raise RuntimeError("diagnostic progress changed before reconciliation")
        owner_payload = _bytes_value(snapshot.get("owner_payload"), "$.owner_payload")
        preregistration_payload = _bytes_value(
            snapshot.get("preregistration_payload"), "$.preregistration_payload"
        )
        implementation_freeze_commit = str(snapshot["implementation_freeze_commit"])
        implementation_context = _mapping(
            snapshot.get("implementation_context"), "$.implementation_context"
        )
        _verify_execution_lineage(
            authority_context,
            frozen_model=frozen_model,
            frozen_dataset=frozen_dataset,
        )
        failure_frame = result_contract.build_progress_event(
            previous_journal_payload=prefix,
            implementation_freeze_commit=implementation_freeze_commit,
            preregistration_payload=preregistration_payload,
            attempt_owner_payload=owner_payload,
            event="failure_terminal_ready",
            captured_at_utc=_utc_now(),
            exception_type="InterruptedExecution",
            discarded_progress_tail=tail_receipt,
        )
        lifecycle.verify()
        output_guard.verify()
        failure_progress = journal.append(
            result_contract.artifact_json_bytes(failure_frame)
        )
        _verify_execution_lineage(
            authority_context,
            frozen_model=frozen_model,
            frozen_dataset=frozen_dataset,
        )
        failure = result_contract.build_diagnostic_failure(
            implementation_freeze_commit=implementation_freeze_commit,
            preregistration_payload=preregistration_payload,
            attempt_owner_payload=owner_payload,
            progress_payload=failure_progress,
            implementation_context=implementation_context,
        )
        lifecycle.verify()
        output_guard.verify()
        recovery_io.write_or_repair_terminal(
            ROOT / protocol.FAILURE_PATH,
            result_contract.artifact_json_bytes(failure),
        )
    raise RuntimeError("diagnostic interrupted attempt reconciled without model rerun")


def _enter_frozen_input_guards(stack: ExitStack) -> tuple[Any, Any]:
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
        run_mm005_browser_research_model_evaluation as v1_runner,
    )

    v2_payload = _read_repository_file(v2_contract.PREREGISTRATION_PATH)
    v2_value = v2_contract.parse_strict_json_bytes(
        v2_payload, location="$.v2_preregistration"
    )
    v2_contract.validate_preregistration(v2_value, **v2_builder.protocol_inputs())
    inputs = v2_builder.execution_inputs()
    artifact_payloads = _bytes_mapping(
        inputs.get("artifact_payloads"), "$.artifact_payloads"
    )
    dataset_receipts = _receipt_mapping(
        inputs.get("dataset_output_receipts"), "$.dataset_output_receipts"
    )
    candidate = _mapping(v2_value.get("candidate"), "$.candidate")
    model_receipts = _object_sequence(
        candidate.get("model_files"), "$.candidate.model_files"
    )
    frozen_model = stack.enter_context(
        repeat_runner._FrozenInputFileSet(
            model_snapshot=ROOT / v2_contract.MODEL_SNAPSHOT_ROOT,
            model_receipts=model_receipts,
            adapter_receipts=v2_contract.ADAPTER_RECEIPTS,
        )
    )
    frozen_dataset = stack.enter_context(
        v1_runner._FrozenDatasetInputSet(dataset_receipts)
    )
    if frozen_dataset.payloads != artifact_payloads:
        raise RuntimeError("diagnostic frozen inputs differ from preregistration")
    return frozen_model, frozen_dataset


def _verify_execution_lineage(
    authority_context: Mapping[str, Any], *, frozen_model: Any, frozen_dataset: Any
) -> None:
    frozen_model.verify()
    frozen_dataset.verify()
    authority_payload = _bytes_value(
        authority_context.get("authority_payload"), "$.authority_payload"
    )
    authority = _mapping(authority_context.get("authority"), "$.authority")
    implementation_freeze_commit = str(
        authority_context["implementation_freeze_commit"]
    )
    zero_bandwidth_maintenance_commit = str(
        authority_context["zero_bandwidth_maintenance_commit"]
    )
    implementation_base_commit = str(authority_context["implementation_base_commit"])
    initial_implementation_publication_commit = str(
        authority_context["initial_implementation_publication_commit"]
    )
    authority_freeze_commit = authority_context.get("authority_freeze_commit")
    if type(authority_freeze_commit) is not str:
        raise RuntimeError("published execution authority freeze commit is missing")
    if _require_aligned_clean_master() != authority_freeze_commit:
        raise RuntimeError(
            "execution lineage HEAD differs from authority introduction commit"
        )
    if (
        _read_regular_file_once(ROOT / result_contract.EXECUTION_AUTHORITY_PATH)
        != authority_payload
    ):
        raise RuntimeError("diagnostic execution authority changed")
    current_protocol = _published_protocol_context(allow_runtime_state=True)
    captured_protocol = _mapping(
        authority_context.get("protocol_context"), "$.protocol_context"
    )
    current_implementation = _implementation_source_context(
        implementation_freeze_commit
    )
    captured_implementation = _mapping(
        authority_context.get("implementation_context"), "$.implementation_context"
    )
    current_authority = _authority_source_context(
        authority_payload=authority_payload,
        implementation_freeze_commit=implementation_freeze_commit,
        authority=authority,
    )
    if (
        zero_bandwidth_maintenance_commit
        != result_contract.ZERO_BANDWIDTH_MAINTENANCE_COMMIT
        or implementation_base_commit != result_contract.IMPLEMENTATION_BASE_COMMIT
        or initial_implementation_publication_commit
        != result_contract.INITIAL_IMPLEMENTATION_PUBLICATION_COMMIT
        or authority.get("zero_bandwidth_maintenance_commit")
        != zero_bandwidth_maintenance_commit
        or authority.get("implementation_base_commit") != implementation_base_commit
        or authority.get("initial_implementation_publication_commit")
        != initial_implementation_publication_commit
        or current_protocol.get("zero_bandwidth_maintenance_commit")
        != zero_bandwidth_maintenance_commit
        or current_protocol.get("implementation_base_commit")
        != implementation_base_commit
        or current_implementation.get("zero_bandwidth_maintenance_commit")
        != zero_bandwidth_maintenance_commit
        or current_implementation.get("implementation_base_commit")
        != implementation_base_commit
        or current_implementation.get("initial_implementation_publication_commit")
        != initial_implementation_publication_commit
        or current_protocol != captured_protocol
        or current_implementation != captured_implementation
        or current_authority.get("freeze_commit") != authority_freeze_commit
        or current_authority != authority_context.get("authority_source_context")
    ):
        raise RuntimeError("diagnostic execution lineage changed")


def _execute_authorized_diagnostic(
    authority_context: Mapping[str, Any],
) -> dict[str, Any]:
    """Consume the single authority-bound attempt with zero retry."""

    context = _validated_execution_context_from_published_authority(authority_context)

    def production_heavy_boundary(
        validated: _ValidatedExecutionContext,
        lifecycle: recovery_io.ProgressLease,
        journal: recovery_io.ProgressLease,
        work_guard: recovery_io.DirectoryTreeGuard,
        parent_guard: recovery_io.DirectoryTreeGuard,
        output_guard: recovery_io.DirectoryTreeGuard,
        owner_payload: bytes,
    ) -> dict[str, Any]:
        return _first_heavy_dependency_boundary(
            validated,
            lifecycle,
            journal,
            work_guard,
            parent_guard,
            output_guard,
            owner_payload,
            authority_context=authority_context,
        )

    return _execute_validated_context(
        context, first_heavy_boundary=production_heavy_boundary
    )


def _validated_execution_context_from_published_authority(
    authority_context: Mapping[str, Any],
) -> _ValidatedExecutionContext:
    """Close the public preflight mapping before any filesystem mutation."""

    authority = _mapping(authority_context.get("authority"), "$.authority")
    authority_payload = _bytes_value(
        authority_context.get("authority_payload"), "$.authority_payload"
    )
    authority_freeze_commit = authority_context.get("authority_freeze_commit")
    if type(authority_freeze_commit) is not str:
        raise RuntimeError("published authority introduction commit is missing")
    implementation_freeze_commit = str(
        authority_context["implementation_freeze_commit"]
    )
    zero_bandwidth_maintenance_commit = str(
        authority_context["zero_bandwidth_maintenance_commit"]
    )
    implementation_base_commit = str(authority_context["implementation_base_commit"])
    initial_implementation_publication_commit = str(
        authority_context["initial_implementation_publication_commit"]
    )
    implementation_context = _mapping(
        authority_context.get("implementation_context"), "$.implementation_context"
    )
    protocol_context = _mapping(
        authority_context.get("protocol_context"), "$.protocol_context"
    )
    preregistration_payload = _bytes_value(
        protocol_context.get("preregistration_payload"),
        "$.protocol_context.preregistration_payload",
    )
    preflight = _mapping(
        authority.get("resource_preflight"), "$.authority.resource_preflight"
    )
    expected_environment = _mapping(
        preflight.get("expected_environment"),
        "$.authority.resource_preflight.expected_environment",
    )

    source_paths: dict[str, str] = {
        "protocol_preregistration": protocol.PREREGISTRATION_PATH,
        "execution_authority": result_contract.EXECUTION_AUTHORITY_PATH,
    }
    source_paths.update(
        {
            f"protocol_source:{name}": relative
            for name, relative in sorted(protocol.PROTOCOL_SOURCE_PATHS.items())
        }
    )
    source_paths.update(
        {
            f"implementation_source:{name}": relative
            for name, relative in sorted(
                result_contract.IMPLEMENTATION_SOURCE_PATHS.items()
            )
        }
    )
    source_paths.update(
        {
            f"critical_dependency:{name}": relative
            for name, relative in sorted(
                result_contract.CRITICAL_EXECUTION_DEPENDENCY_SOURCE_PATHS.items()
            )
        }
    )
    tracked_sources = tuple(
        _TrackedExecutionSource(name, relative, _read_repository_file(relative))
        for name, relative in sorted(source_paths.items())
    )
    return _validated_execution_context(
        repository_root=ROOT,
        protocol_merge_commit=result_contract.PROTOCOL_MERGE_COMMIT,
        zero_bandwidth_maintenance_commit=zero_bandwidth_maintenance_commit,
        implementation_base_commit=implementation_base_commit,
        initial_implementation_publication_commit=(
            initial_implementation_publication_commit
        ),
        implementation_freeze_commit=implementation_freeze_commit,
        authority_freeze_commit=authority_freeze_commit,
        authority_payload=authority_payload,
        preregistration_payload=preregistration_payload,
        implementation_context_payload=result_contract.artifact_json_bytes(
            dict(implementation_context)
        ),
        expected_environment_payload=result_contract.artifact_json_bytes(
            dict(expected_environment)
        ),
        tracked_sources=tracked_sources,
        implementation_slice_paths=IMPLEMENTATION_SLICE_PATHS,
        authority_introduction_paths=result_contract.EXECUTION_AUTHORITY_SLICE_PATHS,
    )


def _validated_execution_context(
    *,
    repository_root: Path,
    protocol_merge_commit: str,
    zero_bandwidth_maintenance_commit: str,
    implementation_base_commit: str,
    initial_implementation_publication_commit: str,
    implementation_freeze_commit: str,
    authority_freeze_commit: str,
    authority_payload: bytes,
    preregistration_payload: bytes,
    implementation_context_payload: bytes,
    expected_environment_payload: bytes,
    tracked_sources: Sequence[_TrackedExecutionSource],
    implementation_slice_paths: Collection[str],
    authority_introduction_paths: Collection[str],
) -> _ValidatedExecutionContext:
    """Build the closed internal context; this function grants no authority."""

    root = Path(os.path.abspath(repository_root))
    _require_safe_directory(root)
    work = root / protocol.WORK_ROOT_PATH
    _require_safe_directory(work)
    if (
        initial_implementation_publication_commit
        != result_contract.INITIAL_IMPLEMENTATION_PUBLICATION_COMMIT
    ):
        raise RuntimeError("validated initial implementation commit differs")
    for name, commit in (
        ("protocol", protocol_merge_commit),
        ("zero-bandwidth maintenance", zero_bandwidth_maintenance_commit),
        ("implementation base", implementation_base_commit),
        ("initial implementation", initial_implementation_publication_commit),
        ("implementation", implementation_freeze_commit),
        ("authority", authority_freeze_commit),
    ):
        if re.fullmatch(r"[0-9a-f]{40}", commit) is None:
            raise RuntimeError(f"invalid {name} execution commit")

    if (
        type(preregistration_payload) is not bytes
        or len(preregistration_payload) != result_contract.PROTOCOL_BYTES
        or result_contract.sha256_bytes(preregistration_payload)
        != result_contract.PROTOCOL_SHA256
    ):
        raise RuntimeError("validated context protocol receipt differs")
    preregistration = result_contract.parse_strict_json_bytes(
        preregistration_payload, location="$.preregistration"
    )
    if (
        result_contract.artifact_json_bytes(preregistration) != preregistration_payload
        or preregistration.get("gate_id") != protocol.GATE_ID
        or preregistration.get("next_gate") != protocol.IMPLEMENTATION_GATE_ID
        or preregistration.get("experiment_id") != protocol.EXPERIMENT_ID
        or preregistration.get("run_id") != protocol.RUN_ID
    ):
        raise RuntimeError("validated context protocol identity differs")

    implementation_context = result_contract.parse_strict_json_bytes(
        implementation_context_payload, location="$.implementation_context"
    )
    if (
        result_contract.artifact_json_bytes(implementation_context)
        != implementation_context_payload
        or implementation_context.get("protocol_merge_commit") != protocol_merge_commit
        or implementation_context.get("zero_bandwidth_maintenance_commit")
        != zero_bandwidth_maintenance_commit
        or implementation_context.get("implementation_base_commit")
        != implementation_base_commit
        or implementation_context.get("initial_implementation_publication_commit")
        != initial_implementation_publication_commit
        or implementation_context.get("freeze_commit") != implementation_freeze_commit
    ):
        raise RuntimeError("validated implementation context differs")

    expected_environment = result_contract.parse_strict_json_bytes(
        expected_environment_payload, location="$.expected_environment"
    )
    if set(expected_environment) != set(
        scientific_protocol.OBSERVED_ENVIRONMENT_FIELDS
    ):
        raise RuntimeError("validated execution environment fields differ")

    authority = result_contract.parse_strict_json_bytes(
        authority_payload, location="$.execution_authority"
    )
    preflight = _mapping(
        authority.get("resource_preflight"), "$.execution_authority.resource_preflight"
    )
    dependency_receipts = _mapping(
        authority.get("critical_execution_dependency_receipts"),
        "$.execution_authority.critical_execution_dependency_receipts",
    )
    expected_authority = result_contract.build_execution_authority_contract(
        implementation_freeze_commit=implementation_freeze_commit,
        expected_environment=_mapping(
            preflight.get("expected_environment"),
            "$.execution_authority.resource_preflight.expected_environment",
        ),
        critical_execution_dependency_receipts=dependency_receipts,
    )
    if (
        result_contract.artifact_json_bytes(authority) != authority_payload
        or result_contract.artifact_json_bytes(expected_authority) != authority_payload
        or authority.get("protocol_merge_commit") != protocol_merge_commit
        or authority.get("zero_bandwidth_maintenance_commit")
        != zero_bandwidth_maintenance_commit
        or authority.get("implementation_base_commit") != implementation_base_commit
        or authority.get("initial_implementation_publication_commit")
        != initial_implementation_publication_commit
        or _mapping(
            preflight.get("expected_environment"),
            "$.execution_authority.resource_preflight.expected_environment",
        )
        != expected_environment
    ):
        raise RuntimeError("validated execution authority differs")

    sources = tuple(tracked_sources)
    if not sources:
        raise RuntimeError("validated execution source closure is empty")
    source_names = [item.name for item in sources]
    source_paths = [item.relative_path for item in sources]
    if len(source_names) != len(set(source_names)) or len(source_paths) != len(
        set(source_paths)
    ):
        raise RuntimeError("validated execution source closure is not unique")
    for item in sources:
        if type(item.name) is not str or not item.name:
            raise RuntimeError("validated execution source name is invalid")
        _validate_repository_relative_path(item.relative_path)
        if type(item.payload) is not bytes or not item.payload:
            raise RuntimeError("validated execution source payload is invalid")
    required_paths = {
        protocol.PREREGISTRATION_PATH,
        result_contract.EXECUTION_AUTHORITY_PATH,
        *result_contract.IMPLEMENTATION_SOURCE_PATHS.values(),
        *result_contract.CRITICAL_EXECUTION_DEPENDENCY_SOURCE_PATHS.values(),
        *protocol.PROTOCOL_SOURCE_PATHS.values(),
    }
    if set(source_paths) != required_paths:
        raise RuntimeError("validated execution source closure differs")

    implementation_paths = frozenset(implementation_slice_paths)
    authority_paths = frozenset(authority_introduction_paths)
    for relative in implementation_paths | authority_paths:
        _validate_repository_relative_path(relative)
    if implementation_paths != IMPLEMENTATION_SLICE_PATHS:
        raise RuntimeError("validated implementation slice differs")
    if result_contract.EXECUTION_AUTHORITY_PATH not in authority_paths:
        raise RuntimeError("validated authority introduction omits its artifact")

    return _ValidatedExecutionContext(
        repository_root=root,
        protocol_merge_commit=protocol_merge_commit,
        zero_bandwidth_maintenance_commit=zero_bandwidth_maintenance_commit,
        implementation_base_commit=implementation_base_commit,
        initial_implementation_publication_commit=(
            initial_implementation_publication_commit
        ),
        implementation_freeze_commit=implementation_freeze_commit,
        authority_freeze_commit=authority_freeze_commit,
        authority_payload=authority_payload,
        preregistration_payload=preregistration_payload,
        implementation_context_payload=implementation_context_payload,
        expected_environment_payload=expected_environment_payload,
        tracked_sources=sources,
        implementation_slice_paths=implementation_paths,
        authority_introduction_paths=authority_paths,
    )


def _execute_validated_context(
    context: _ValidatedExecutionContext,
    *,
    first_heavy_boundary: _FirstHeavyBoundary,
) -> dict[str, Any]:
    """Prepare one safe parent, claim once, then enter the heavy boundary.

    The only injectable boundary is first_heavy_boundary. Parent creation,
    both directory guards, lifecycle creation, owner/genesis publication, Git
    revalidation, and failure persistence are always the real implementation.
    """

    if not isinstance(context, _ValidatedExecutionContext) or not callable(
        first_heavy_boundary
    ):
        raise RuntimeError("closed validated execution context required")
    root = context.repository_root
    work = root / protocol.WORK_ROOT_PATH
    output_parent = root / protocol.OUTPUT_PARENT_PATH

    _revalidate_execution_context(context, phase="pre_parent")
    work_guard = recovery_io.DirectoryTreeGuard(root, work)
    work_guard.verify()
    if os.path.lexists(output_parent):
        raise FileExistsError(output_parent)

    # Exactly one new component; no parents and no exist_ok.
    os.mkdir(output_parent)

    _revalidate_execution_context(context, phase="post_parent")
    work_guard.verify()
    parent_guard = recovery_io.DirectoryTreeGuard(root, output_parent)
    work_guard.verify()
    parent_guard.verify()
    _revalidate_execution_context(context, phase="post_parent")

    lifecycle_path = root / protocol.LIFECYCLE_LEASE_PATH
    work_guard.verify()
    parent_guard.verify()
    recovery_io.ensure_lock_directory(
        lifecycle_path,
        _lifecycle_lease_marker(
            authority_freeze_commit=context.authority_freeze_commit,
            authority_payload=context.authority_payload,
        ),
    )

    with recovery_io.ProgressLease(lifecycle_path) as lifecycle:
        work_guard.verify()
        parent_guard.verify()
        lifecycle.verify()
        _revalidate_execution_context(context, phase="lifecycle")

        attempt_id = secrets.token_hex(32)
        owner = result_contract.build_attempt_owner(
            implementation_freeze_commit=context.implementation_freeze_commit,
            preregistration_payload=context.preregistration_payload,
            authority_freeze_commit=context.authority_freeze_commit,
            execution_authority_payload=context.authority_payload,
            attempt_id=attempt_id,
        )
        owner_payload = result_contract.artifact_json_bytes(owner)
        genesis = result_contract.build_progress_event(
            previous_journal_payload=b"",
            implementation_freeze_commit=context.implementation_freeze_commit,
            preregistration_payload=context.preregistration_payload,
            attempt_owner_payload=owner_payload,
            event="attempt_claimed",
        )
        genesis_payload = result_contract.artifact_json_bytes(genesis)

        work_guard.verify()
        parent_guard.verify()
        lifecycle.verify()
        _revalidate_execution_context(context, phase="lifecycle")
        _claim_output(
            root=root,
            attempt_id=attempt_id,
            owner_payload=owner_payload,
            genesis_payload=genesis_payload,
        )

        output_guard = recovery_io.DirectoryTreeGuard(
            root, root / protocol.RUN_OUTPUT_ROOT
        )
        with recovery_io.ProgressLease(root / protocol.PROGRESS_PATH) as journal:
            work_guard.verify()
            parent_guard.verify()
            lifecycle.verify()
            output_guard.verify()
            _revalidate_execution_context(context, phase="claimed")

            # Owner-bound terminal handling begins only after the atomic claim.
            try:
                return first_heavy_boundary(
                    context,
                    lifecycle,
                    journal,
                    work_guard,
                    parent_guard,
                    output_guard,
                    owner_payload,
                )
            except BaseException as exc:
                work_guard.verify()
                parent_guard.verify()
                lifecycle.verify()
                output_guard.verify()
                _revalidate_execution_context(context, phase="claimed")
                events, prefix, tail_receipt = result_contract.recover_progress_prefix(
                    journal.read(),
                    implementation_freeze_commit=context.implementation_freeze_commit,
                    preregistration_payload=context.preregistration_payload,
                    attempt_owner_payload=owner_payload,
                )
                if prefix != journal.read():
                    journal.truncate_to_authenticated_prefix(prefix)
                last = events[-1]
                implementation_context = _mapping(
                    result_contract.parse_strict_json_bytes(
                        context.implementation_context_payload,
                        location="$.implementation_context",
                    ),
                    "$.implementation_context",
                )
                if last.get("event") == "success_terminal_ready":
                    result = result_contract.build_diagnostic_result(
                        implementation_freeze_commit=(
                            context.implementation_freeze_commit
                        ),
                        preregistration_payload=context.preregistration_payload,
                        attempt_owner_payload=owner_payload,
                        progress_payload=prefix,
                        implementation_context=implementation_context,
                    )
                    recovery_io.write_or_repair_terminal(
                        root / protocol.SUCCESS_RESULT_PATH,
                        result_contract.artifact_json_bytes(result),
                    )
                    return _terminal_summary(result, kind="success")
                if last.get("event") == "failure_terminal_ready":
                    failure = result_contract.build_diagnostic_failure(
                        implementation_freeze_commit=(
                            context.implementation_freeze_commit
                        ),
                        preregistration_payload=context.preregistration_payload,
                        attempt_owner_payload=owner_payload,
                        progress_payload=prefix,
                        implementation_context=implementation_context,
                    )
                    recovery_io.write_or_repair_terminal(
                        root / protocol.FAILURE_PATH,
                        result_contract.artifact_json_bytes(failure),
                    )
                    raise RuntimeError(
                        "diagnostic failure terminal already prepared"
                    ) from exc

                failure_frame = result_contract.build_progress_event(
                    previous_journal_payload=prefix,
                    implementation_freeze_commit=context.implementation_freeze_commit,
                    preregistration_payload=context.preregistration_payload,
                    attempt_owner_payload=owner_payload,
                    event="failure_terminal_ready",
                    captured_at_utc=_utc_now(),
                    exception_type=_safe_exception_type(exc),
                    discarded_progress_tail=tail_receipt,
                )
                work_guard.verify()
                parent_guard.verify()
                lifecycle.verify()
                output_guard.verify()
                failure_progress = journal.append(
                    result_contract.artifact_json_bytes(failure_frame)
                )
                _revalidate_execution_context(context, phase="claimed")
                failure = result_contract.build_diagnostic_failure(
                    implementation_freeze_commit=context.implementation_freeze_commit,
                    preregistration_payload=context.preregistration_payload,
                    attempt_owner_payload=owner_payload,
                    progress_payload=failure_progress,
                    implementation_context=implementation_context,
                )
                work_guard.verify()
                parent_guard.verify()
                lifecycle.verify()
                output_guard.verify()
                _revalidate_execution_context(context, phase="claimed")
                recovery_io.write_or_repair_terminal(
                    root / protocol.FAILURE_PATH,
                    result_contract.artifact_json_bytes(failure),
                )
                raise


def _first_heavy_dependency_boundary(
    context: _ValidatedExecutionContext,
    lifecycle: recovery_io.ProgressLease,
    journal: recovery_io.ProgressLease,
    work_guard: recovery_io.DirectoryTreeGuard,
    parent_guard: recovery_io.DirectoryTreeGuard,
    output_guard: recovery_io.DirectoryTreeGuard,
    owner_payload: bytes,
    *,
    authority_context: Mapping[str, Any],
) -> dict[str, Any]:
    """First permitted model/PIL/torch/CUDA/network-capable import boundary."""

    from fullcycle_bridge import (  # noqa: PLC0415
        mm005_browser_research_model_evaluation_protocol_v2 as v2_contract,
    )
    from scripts import (  # noqa: PLC0415
        prepare_mm005_browser_research_model_evaluation_v2 as v2_builder,
    )
    from scripts import (  # noqa: PLC0415
        run_mm003_post_training_eval_repeatability as repeat_runner,
    )
    from scripts import run_mm003_qlora_post_training_v2 as upstream_runner  # noqa: PLC0415
    from scripts import (  # noqa: PLC0415
        run_mm005_browser_research_model_evaluation as v1_runner,
    )
    from scripts import (  # noqa: PLC0415
        run_mm005_browser_research_model_evaluation_v2 as v2_runner,
    )

    expected_environment = _mapping(
        result_contract.parse_strict_json_bytes(
            context.expected_environment_payload,
            location="$.expected_environment",
        ),
        "$.expected_environment",
    )
    implementation_context = _mapping(
        result_contract.parse_strict_json_bytes(
            context.implementation_context_payload,
            location="$.implementation_context",
        ),
        "$.implementation_context",
    )
    v2_preregistration_payload = _read_repository_file(v2_contract.PREREGISTRATION_PATH)
    v2_preregistration = v2_contract.parse_strict_json_bytes(
        v2_preregistration_payload, location="$.v2_preregistration"
    )
    v2_contract.validate_preregistration(
        v2_preregistration, **v2_builder.protocol_inputs()
    )
    execution_inputs = v2_builder.execution_inputs()
    records = _object_sequence(execution_inputs.get("records"), "$.records")
    artifact_payloads = _bytes_mapping(
        execution_inputs.get("artifact_payloads"), "$.artifact_payloads"
    )
    dataset_receipts = _receipt_mapping(
        execution_inputs.get("dataset_output_receipts"),
        "$.dataset_output_receipts",
    )
    candidate = _mapping(v2_preregistration.get("candidate"), "$.candidate")
    model_receipts = _object_sequence(
        candidate.get("model_files"), "$.candidate.model_files"
    )

    v2_runner._validate_formal_python_execution_mode()
    upstream_runner._validate_local_dependency_wheel()
    execution_started = time.perf_counter()
    with (
        repeat_runner._FrozenInputFileSet(
            model_snapshot=ROOT / v2_contract.MODEL_SNAPSHOT_ROOT,
            model_receipts=model_receipts,
            adapter_receipts=v2_contract.ADAPTER_RECEIPTS,
        ) as frozen_model,
        v1_runner._FrozenDatasetInputSet(dataset_receipts) as frozen_dataset,
    ):
        if frozen_dataset.payloads != artifact_payloads:
            raise RuntimeError("diagnostic frozen inputs differ from authority context")
        work_guard.verify()
        parent_guard.verify()
        lifecycle.verify()
        output_guard.verify()
        _verify_execution_lineage(
            authority_context,
            frozen_model=frozen_model,
            frozen_dataset=frozen_dataset,
        )

        def append_progress(
            event: str,
            record_id: str | None,
            diagnostic_index: int | None,
            case_summary: Mapping[str, Any] | None,
        ) -> None:
            work_guard.verify()
            parent_guard.verify()
            lifecycle.verify()
            output_guard.verify()
            frame = result_contract.build_progress_event(
                previous_journal_payload=journal.read(),
                implementation_freeze_commit=context.implementation_freeze_commit,
                preregistration_payload=context.preregistration_payload,
                attempt_owner_payload=owner_payload,
                event=event,
                record_id=record_id,
                diagnostic_index=diagnostic_index,
                observed_environment=(
                    expected_environment
                    if event == "context_preflight_completed"
                    else None
                ),
                case_result=case_summary,
            )
            journal.append(result_contract.artifact_json_bytes(frame))

        upstream_runner._enable_offline_execution()
        with repeat_runner._OfflineSocketGuard({"network_attempts": 0}):
            dependencies = repeat_runner._load_eval_dependencies()
            _summaries, resources = _run_frozen_diagnostic_session(
                dependencies=dependencies,
                expected_environment=expected_environment,
                records=records,
                artifact_payloads=frozen_dataset.payloads,
                append_progress=append_progress,
            )
        _verify_execution_lineage(
            authority_context,
            frozen_model=frozen_model,
            frozen_dataset=frozen_dataset,
        )
        resources = {
            **resources,
            "elapsed_seconds": time.perf_counter() - execution_started,
        }
        success_frame = result_contract.build_progress_event(
            previous_journal_payload=journal.read(),
            implementation_freeze_commit=context.implementation_freeze_commit,
            preregistration_payload=context.preregistration_payload,
            attempt_owner_payload=owner_payload,
            event="success_terminal_ready",
            captured_at_utc=_utc_now(),
            resources=resources,
        )
        work_guard.verify()
        parent_guard.verify()
        lifecycle.verify()
        output_guard.verify()
        progress_payload = journal.append(
            result_contract.artifact_json_bytes(success_frame)
        )
        _verify_execution_lineage(
            authority_context,
            frozen_model=frozen_model,
            frozen_dataset=frozen_dataset,
        )
        result = result_contract.build_diagnostic_result(
            implementation_freeze_commit=context.implementation_freeze_commit,
            preregistration_payload=context.preregistration_payload,
            attempt_owner_payload=owner_payload,
            progress_payload=progress_payload,
            implementation_context=implementation_context,
        )
        result_payload = result_contract.artifact_json_bytes(result)
        work_guard.verify()
        parent_guard.verify()
        lifecycle.verify()
        output_guard.verify()
        _verify_execution_lineage(
            authority_context,
            frozen_model=frozen_model,
            frozen_dataset=frozen_dataset,
        )
        recovery_io.write_or_repair_terminal(
            ROOT / protocol.SUCCESS_RESULT_PATH, result_payload
        )
        return _terminal_summary(result, kind="success")


def _revalidate_execution_context(
    context: _ValidatedExecutionContext, *, phase: _ExecutionPhase
) -> None:
    """Rebind Git, sources, topology, and safe ancestry at every mutation edge."""

    if phase not in {"pre_parent", "post_parent", "lifecycle", "claimed"}:
        raise RuntimeError("invalid execution revalidation phase")
    if (
        context.initial_implementation_publication_commit
        != result_contract.INITIAL_IMPLEMENTATION_PUBLICATION_COMMIT
    ):
        raise RuntimeError("initial implementation publication changed")
    root = context.repository_root
    work = root / protocol.WORK_ROOT_PATH
    parent = root / protocol.OUTPUT_PARENT_PATH
    _require_safe_directory(root)
    _require_safe_directory(work)
    if Path(os.path.abspath(work.parent)) != root:
        raise RuntimeError("work root is not a direct repository child")
    if Path(os.path.abspath(parent.parent)) != work:
        raise RuntimeError("output parent is not the registered single child")
    if phase == "pre_parent":
        if os.path.lexists(parent):
            raise FileExistsError(parent)
    else:
        _require_safe_directory(parent)

    _require_no_hidden_index_flags_at(root)
    branch = _git_text_at(root, "rev-parse", "--abbrev-ref", "HEAD")
    head = _git_text_at(root, "rev-parse", "HEAD")
    local_master = _git_text_at(root, "rev-parse", "refs/heads/master")
    origin_master = _git_text_at(root, "rev-parse", "refs/remotes/origin/master")
    status = _git_text_at(root, "status", "--porcelain=v1", "--untracked-files=all")
    if (
        branch != "master"
        or head != context.authority_freeze_commit
        or local_master != head
        or origin_master != head
        or status
    ):
        raise RuntimeError("execution context is not clean aligned exact master")

    _require_unique_parent_at(
        root,
        context.zero_bandwidth_maintenance_commit,
        context.protocol_merge_commit,
    )
    _require_unique_parent_at(
        root,
        context.implementation_base_commit,
        context.zero_bandwidth_maintenance_commit,
    )
    _require_unique_parent_at(
        root,
        context.initial_implementation_publication_commit,
        context.implementation_base_commit,
    )
    _require_unique_parent_at(
        root,
        context.implementation_freeze_commit,
        context.initial_implementation_publication_commit,
    )
    _require_unique_parent_at(
        root, context.authority_freeze_commit, context.implementation_freeze_commit
    )
    if set(
        _git_name_only_paths_at(
            root,
            context.implementation_base_commit,
            context.initial_implementation_publication_commit,
        )
    ) != set(context.implementation_slice_paths):
        raise RuntimeError("initial implementation slice changed during execution")
    if set(
        _git_name_only_paths_at(
            root,
            context.implementation_base_commit,
            context.implementation_freeze_commit,
        )
    ) != set(context.implementation_slice_paths):
        raise RuntimeError("implementation slice changed during execution")
    compatibility_delta = set(
        _git_name_only_paths_at(
            root,
            context.initial_implementation_publication_commit,
            context.implementation_freeze_commit,
        )
    )
    if not compatibility_delta or not compatibility_delta.issubset(
        context.implementation_slice_paths
    ):
        raise RuntimeError(
            "implementation compatibility delta changed during execution"
        )
    if set(
        _git_name_only_paths_at(
            root,
            context.implementation_freeze_commit,
            context.authority_freeze_commit,
        )
    ) != set(context.authority_introduction_paths):
        raise RuntimeError("authority slice changed during execution")

    for item in context.tracked_sources:
        current = _read_regular_file_once(root / item.relative_path)
        frozen = _git_blob_bytes_at(
            root, context.authority_freeze_commit, item.relative_path
        )
        if current != item.payload or frozen != item.payload:
            raise RuntimeError(f"execution source changed: {item.name}")

    for name, relative in sorted(result_contract.IMPLEMENTATION_SOURCE_PATHS.items()):
        current = _read_regular_file_once(root / relative)
        final_implementation = _git_blob_bytes_at(
            root, context.implementation_freeze_commit, relative
        )
        if current != final_implementation:
            raise RuntimeError(
                f"implementation source differs from final freeze: {name}"
            )
        introduced = tuple(
            line
            for line in _git_text_at(
                root,
                "log",
                "--first-parent",
                "--diff-filter=A",
                "--format=%H",
                "--",
                relative,
            ).splitlines()
            if line
        )
        if introduced != (context.initial_implementation_publication_commit,):
            raise RuntimeError(f"implementation introduction changed: {name}")
    authority_introduction = tuple(
        line
        for line in _git_text_at(
            root,
            "log",
            "--first-parent",
            "--diff-filter=A",
            "--format=%H",
            "--",
            result_contract.EXECUTION_AUTHORITY_PATH,
        ).splitlines()
        if line
    )
    if authority_introduction != (context.authority_freeze_commit,):
        raise RuntimeError("authority introduction changed during execution")

    topology = _output_topology_at(root)
    if topology["reserved_sibling_staging"]:
        raise RuntimeError("reserved diagnostic sibling staging requires review")
    if not topology["execution_authority"]:
        raise RuntimeError("published execution authority disappeared")
    expected_parent = phase != "pre_parent"
    if topology["output_parent"] is not expected_parent:
        raise RuntimeError("output parent topology differs")
    if phase in {"pre_parent", "post_parent"}:
        forbidden = (
            "output_root",
            "attempt_owner",
            "progress",
            "success_result",
            "failure",
            "lifecycle_lease_root",
            "lifecycle_lease",
        )
        if any(topology[name] for name in forbidden):
            raise RuntimeError("pre-owner execution topology is not unclaimed")
    elif phase == "lifecycle":
        if not (
            topology["lifecycle_lease_root"]
            and topology["lifecycle_lease"]
            and not any(
                topology[name]
                for name in (
                    "output_root",
                    "attempt_owner",
                    "progress",
                    "success_result",
                    "failure",
                )
            )
        ):
            raise RuntimeError("lifecycle-only execution topology differs")
    else:
        if not (
            topology["lifecycle_lease_root"]
            and topology["lifecycle_lease"]
            and topology["output_root"]
            and topology["attempt_owner"]
            and topology["progress"]
            and not (topology["success_result"] and topology["failure"])
        ):
            raise RuntimeError("claimed execution topology differs")


def _published_protocol_context(*, allow_runtime_state: bool = False) -> dict[str, Any]:
    """Bind the exact PR #81 protocol/config/source publication."""

    preregistration_payload = _read_repository_file(protocol.PREREGISTRATION_PATH)
    if (
        len(preregistration_payload) != result_contract.PROTOCOL_BYTES
        or protocol.sha256_bytes(preregistration_payload)
        != result_contract.PROTOCOL_SHA256
        or _git_blob_bytes(
            result_contract.PROTOCOL_MERGE_COMMIT, protocol.PREREGISTRATION_PATH
        )
        != preregistration_payload
    ):
        raise RuntimeError("published diagnostic protocol binding mismatch")
    raw = protocol.parse_strict_json_bytes(
        preregistration_payload, location="$.diagnostic_protocol"
    )
    if protocol.artifact_json_bytes(raw) != preregistration_payload:
        raise RuntimeError("published diagnostic protocol is not canonical")
    if not allow_runtime_state:
        inputs = protocol_builder.protocol_inputs()
        protocol.validate_preregistration(raw, **inputs)
    _require_commit_ancestor(result_contract.PROTOCOL_MERGE_COMMIT)
    _require_commit_ancestor(result_contract.ZERO_BANDWIDTH_MAINTENANCE_COMMIT)
    _require_commit_ancestor(result_contract.IMPLEMENTATION_BASE_COMMIT)
    _require_unique_parent(
        result_contract.ZERO_BANDWIDTH_MAINTENANCE_COMMIT,
        result_contract.PROTOCOL_MERGE_COMMIT,
    )
    _require_unique_parent(
        result_contract.IMPLEMENTATION_BASE_COMMIT,
        result_contract.ZERO_BANDWIDTH_MAINTENANCE_COMMIT,
    )
    receipts = _mapping(
        _mapping(raw.get("source_lineage"), "$.source_lineage").get("protocol_sources"),
        "$.source_lineage.protocol_sources",
    )
    if set(receipts) != set(protocol.PROTOCOL_SOURCE_PATHS):
        raise RuntimeError("diagnostic protocol source set mismatch")
    for name, relative in sorted(protocol.PROTOCOL_SOURCE_PATHS.items()):
        current = _read_repository_file(relative)
        frozen = _git_blob_bytes(result_contract.PROTOCOL_MERGE_COMMIT, relative)
        receipt = _mapping(receipts.get(name), f"$.protocol_sources.{name}")
        if current != frozen or receipt != {
            "path": relative,
            "bytes": len(frozen),
            "sha256": protocol.sha256_bytes(frozen),
        }:
            raise RuntimeError(f"published diagnostic source differs: {name}")
    return {
        "protocol_merge_commit": result_contract.PROTOCOL_MERGE_COMMIT,
        "zero_bandwidth_maintenance_commit": (
            result_contract.ZERO_BANDWIDTH_MAINTENANCE_COMMIT
        ),
        "implementation_base_commit": result_contract.IMPLEMENTATION_BASE_COMMIT,
        "zero_bandwidth_maintenance_unique_parent_is_protocol_merge_commit": True,
        "implementation_base_unique_parent_is_zero_bandwidth_maintenance_commit": (
            True
        ),
        "preregistration_payload": preregistration_payload,
        "protocol_source_files": len(protocol.PROTOCOL_SOURCE_PATHS),
        "protocol_sources": {name: dict(value) for name, value in receipts.items()},
    }


def _implementation_source_receipts() -> dict[str, dict[str, Any]]:
    receipts: dict[str, dict[str, Any]] = {}
    for name, relative in sorted(result_contract.IMPLEMENTATION_SOURCE_PATHS.items()):
        payload = _read_repository_file(relative)
        receipts[name] = {
            "path": relative,
            "bytes": len(payload),
            "sha256": protocol.sha256_bytes(payload),
        }
    return receipts


def _output_topology() -> dict[str, bool]:
    return _output_topology_at(ROOT)


def _output_topology_at(root: Path) -> dict[str, bool]:
    return {
        "output_parent": os.path.lexists(root / protocol.OUTPUT_PARENT_PATH),
        "output_root": os.path.lexists(root / protocol.RUN_OUTPUT_ROOT),
        "attempt_owner": os.path.lexists(root / protocol.ATTEMPT_OWNER_PATH),
        "progress": os.path.lexists(root / protocol.PROGRESS_PATH),
        "success_result": os.path.lexists(root / protocol.SUCCESS_RESULT_PATH),
        "failure": os.path.lexists(root / protocol.FAILURE_PATH),
        "lifecycle_lease_root": os.path.lexists(root / protocol.LIFECYCLE_LEASE_ROOT),
        "lifecycle_lease": os.path.lexists(root / protocol.LIFECYCLE_LEASE_PATH),
        "execution_authority": os.path.lexists(
            root / result_contract.EXECUTION_AUTHORITY_PATH
        ),
        "reserved_sibling_staging": bool(_reserved_sibling_staging_names_at(root)),
    }


def _validate_output_topology(topology: Mapping[str, bool]) -> None:
    if set(topology) != set(RUNTIME_OUTPUT_KEYS) | {
        "execution_authority",
        "output_parent",
    } or any(type(value) is not bool for value in topology.values()):
        raise RuntimeError("diagnostic output topology fields are invalid")


def _inspect_read_only_execution_state(
    topology: Mapping[str, bool],
    authority_context: Mapping[str, Any] | None,
) -> dict[str, Any]:
    _validate_output_topology(topology)
    if topology["reserved_sibling_staging"]:
        raise RuntimeError("reserved diagnostic sibling staging requires review")
    claimed_members = {
        name
        for name in ("attempt_owner", "progress", "success_result", "failure")
        if topology[name]
    }
    if not topology["output_root"]:
        if claimed_members:
            raise RuntimeError("diagnostic output members exist without output root")
        lifecycle_present = (
            topology["lifecycle_lease_root"] or topology["lifecycle_lease"]
        )
        if lifecycle_present:
            if not (
                topology["lifecycle_lease_root"]
                and topology["lifecycle_lease"]
                and authority_context is not None
                and authority_context.get("published") is True
            ):
                raise RuntimeError("diagnostic pre-claim lifecycle state is invalid")
            _validate_lifecycle_state(authority_context)
            raise RuntimeError(
                "diagnostic pre-owner lifecycle evidence prohibits continuation"
            )
        return {
            "terminal_artifact_valid": False,
            "terminal_reconciliation_required": lifecycle_present,
            "diagnostic_attempt_consumed": False,
            "diagnostic_executed": False,
            "selected_outcome": None,
        }
    if (
        authority_context is None
        or authority_context.get("published") is not True
        or not topology["attempt_owner"]
        or not topology["progress"]
        or not topology["lifecycle_lease_root"]
        or not topology["lifecycle_lease"]
    ):
        raise RuntimeError("claimed diagnostic output lacks published authority state")
    snapshot = _claimed_execution_snapshot(authority_context)
    terminal_value = snapshot.get("terminal_value")
    diagnostic_executed = False
    selected_outcome: object = None
    if isinstance(terminal_value, Mapping):
        claims = _mapping(terminal_value.get("claims"), "$.terminal.claims")
        decision = _mapping(terminal_value.get("decision"), "$.terminal.decision")
        diagnostic_executed = claims.get("diagnostic_executed") is True
        selected_outcome = decision.get("selected_outcome")
    else:
        events = _object_sequence(snapshot.get("events"), "$.events")
        last = events[-1]
        diagnostic_executed = bool(last.get("completed_record_ids")) or (
            last.get("active_record_id") is not None
        )
    return {
        "terminal_artifact_valid": snapshot["terminal_artifact_valid"],
        "terminal_reconciliation_required": snapshot[
            "terminal_reconciliation_required"
        ],
        "diagnostic_attempt_consumed": True,
        "diagnostic_executed": diagnostic_executed,
        "selected_outcome": selected_outcome,
    }


def _validate_lifecycle_state(authority_context: Mapping[str, Any]) -> None:
    _validate_lifecycle_state_at(ROOT, authority_context)


def _validate_lifecycle_state_at(
    root: Path, authority_context: Mapping[str, Any]
) -> None:
    freeze_commit = authority_context.get("authority_freeze_commit")
    if type(freeze_commit) is not str:
        raise RuntimeError("published execution authority freeze commit is missing")
    authority_payload = _bytes_value(
        authority_context.get("authority_payload"), "$.authority_payload"
    )
    lifecycle_root = root / protocol.LIFECYCLE_LEASE_ROOT
    recovery_io.DirectoryTreeGuard(root, lifecycle_root).verify()
    recovery_io.validate_lock_file(
        root / protocol.LIFECYCLE_LEASE_PATH,
        _lifecycle_lease_marker(
            authority_freeze_commit=freeze_commit,
            authority_payload=authority_payload,
        ),
    )


def _claimed_execution_snapshot(
    authority_context: Mapping[str, Any],
) -> dict[str, Any]:
    topology = _output_topology()
    _validate_output_topology(topology)
    if not all(
        topology[name]
        for name in (
            "execution_authority",
            "output_root",
            "attempt_owner",
            "progress",
            "lifecycle_lease_root",
            "lifecycle_lease",
        )
    ):
        raise RuntimeError("claimed diagnostic topology is incomplete")
    if topology["success_result"] and topology["failure"]:
        raise RuntimeError("diagnostic success and failure artifacts both exist")
    _validate_lifecycle_state(authority_context)
    output_root = ROOT / protocol.RUN_OUTPUT_ROOT
    output_guard = recovery_io.DirectoryTreeGuard(ROOT, output_root)
    allowed_names = {
        Path(protocol.ATTEMPT_OWNER_PATH).name,
        Path(protocol.PROGRESS_PATH).name,
    }
    if topology["success_result"]:
        allowed_names.add(Path(protocol.SUCCESS_RESULT_PATH).name)
    if topology["failure"]:
        allowed_names.add(Path(protocol.FAILURE_PATH).name)
    observed_names = {entry.name for entry in output_root.iterdir()}
    if observed_names != allowed_names:
        raise RuntimeError("diagnostic output tree has unexpected members")
    output_guard.verify()

    implementation_freeze_commit = str(
        authority_context["implementation_freeze_commit"]
    )
    implementation_context = _mapping(
        authority_context.get("implementation_context"), "$.implementation_context"
    )
    protocol_context = _mapping(
        authority_context.get("protocol_context"), "$.protocol_context"
    )
    preregistration_payload = _bytes_value(
        protocol_context.get("preregistration_payload"), "$.preregistration_payload"
    )
    owner_payload = recovery_io.read_regular_file(
        ROOT / protocol.ATTEMPT_OWNER_PATH, max_bytes=64 * 1024
    )
    owner = result_contract.parse_strict_json_bytes(
        owner_payload, location="$.attempt_owner"
    )
    result_contract.validate_attempt_owner(
        owner,
        implementation_freeze_commit=implementation_freeze_commit,
        preregistration_payload=preregistration_payload,
    )
    authority_payload = _bytes_value(
        authority_context.get("authority_payload"), "$.authority_payload"
    )
    authority_freeze_commit = authority_context.get("authority_freeze_commit")
    authority_value = _mapping(authority_context.get("authority"), "$.authority")
    expected_owner_authority = {
        "freeze_commit": authority_freeze_commit,
        "artifact": {
            "path": result_contract.EXECUTION_AUTHORITY_PATH,
            "bytes": len(authority_payload),
            "sha256": protocol.sha256_bytes(authority_payload),
        },
        "contract": dict(authority_value),
    }
    if owner.get("execution_authority") != expected_owner_authority:
        raise RuntimeError("attempt owner is bound to a different execution authority")
    progress_payload = recovery_io.read_regular_file(
        ROOT / protocol.PROGRESS_PATH, max_bytes=8 * 1024 * 1024
    )
    events, prefix, tail_receipt = result_contract.recover_progress_prefix(
        progress_payload,
        implementation_freeze_commit=implementation_freeze_commit,
        preregistration_payload=preregistration_payload,
        attempt_owner_payload=owner_payload,
    )
    last_event = str(events[-1].get("event"))
    terminal_kind: str | None = None
    terminal_value: dict[str, Any] | None = None
    terminal_payload: bytes | None = None
    terminal_path: Path | None = None
    terminal_artifact_valid = False
    terminal_reconciliation_required = True
    if last_event in scientific_protocol.TERMINAL_EVENTS:
        if tail_receipt is not None:
            raise RuntimeError("diagnostic terminal journal has a partial continuation")
        if last_event == "success_terminal_ready":
            terminal_kind = "success"
            terminal_value = result_contract.build_diagnostic_result(
                implementation_freeze_commit=implementation_freeze_commit,
                preregistration_payload=preregistration_payload,
                attempt_owner_payload=owner_payload,
                progress_payload=prefix,
                implementation_context=implementation_context,
            )
            terminal_path = ROOT / protocol.SUCCESS_RESULT_PATH
            if topology["failure"]:
                raise RuntimeError("failure artifact conflicts with success journal")
        else:
            terminal_kind = "failure"
            terminal_value = result_contract.build_diagnostic_failure(
                implementation_freeze_commit=implementation_freeze_commit,
                preregistration_payload=preregistration_payload,
                attempt_owner_payload=owner_payload,
                progress_payload=prefix,
                implementation_context=implementation_context,
            )
            terminal_path = ROOT / protocol.FAILURE_PATH
            if topology["success_result"]:
                raise RuntimeError("success artifact conflicts with failure journal")
        terminal_payload = result_contract.artifact_json_bytes(terminal_value)
        terminal_present = os.path.lexists(terminal_path)
        if terminal_present:
            observed_terminal = recovery_io.read_regular_file(
                terminal_path, max_bytes=max(len(terminal_payload), 1)
            )
            if observed_terminal == terminal_payload:
                terminal_artifact_valid = True
                terminal_reconciliation_required = False
            elif not terminal_payload.startswith(observed_terminal):
                raise RuntimeError(
                    "diagnostic terminal artifact is not an exact prefix"
                )
    elif topology["success_result"] or topology["failure"]:
        raise RuntimeError(
            "diagnostic terminal artifact exists before terminal journal"
        )
    output_guard.verify()
    return {
        "topology": topology,
        "output_guard": output_guard,
        "owner_payload": owner_payload,
        "progress_payload": progress_payload,
        "events": events,
        "authenticated_prefix": prefix,
        "discarded_tail_receipt": tail_receipt,
        "terminal_kind": terminal_kind,
        "terminal_value": terminal_value,
        "terminal_payload": terminal_payload,
        "terminal_path": terminal_path,
        "terminal_artifact_valid": terminal_artifact_valid,
        "terminal_reconciliation_required": terminal_reconciliation_required,
        "implementation_freeze_commit": implementation_freeze_commit,
        "implementation_context": implementation_context,
        "preregistration_payload": preregistration_payload,
    }


def _reserved_sibling_staging_names() -> tuple[str, ...]:
    """Enumerate every reserved durable pre-claim sibling without reading it."""

    return _reserved_sibling_staging_names_at(ROOT)


def _reserved_sibling_staging_names_at(root: Path) -> tuple[str, ...]:
    """Enumerate reserved pre-claim siblings below one validated root."""

    output_dir = root / protocol.RUN_OUTPUT_ROOT
    parent = output_dir.parent
    if not os.path.lexists(parent):
        existing_ancestor = parent.parent
        while not os.path.lexists(existing_ancestor):
            if existing_ancestor == root:
                break
            existing_ancestor = existing_ancestor.parent
        if not os.path.lexists(existing_ancestor):
            raise RuntimeError("diagnostic output ancestry is missing")
        _require_safe_directory(existing_ancestor)
        return ()
    _require_safe_directory(parent)
    reserved_prefix = f".{output_dir.name}.".casefold()
    return tuple(
        sorted(
            entry.name
            for entry in parent.iterdir()
            if entry.name.casefold().startswith(reserved_prefix)
        )
    )


def _require_reserved_sibling_staging_absent() -> None:
    """Reject any durable pre-claim staging evidence under the output parent."""

    _require_reserved_sibling_staging_absent_at(ROOT)


def _require_reserved_sibling_staging_absent_at(root: Path) -> None:
    """Reject any durable pre-claim staging evidence below one root."""

    reserved = _reserved_sibling_staging_names_at(root)
    if reserved:
        raise RuntimeError("reserved diagnostic sibling staging requires review")


def _claim_output(
    *, root: Path, attempt_id: str, owner_payload: bytes, genesis_payload: bytes
) -> None:
    """Future-authority helper: atomically publish owner plus genesis only."""

    _require_reserved_sibling_staging_absent_at(root)
    output_dir = root / protocol.RUN_OUTPUT_ROOT
    parent = output_dir.parent
    _require_safe_directory(parent)
    if os.path.lexists(output_dir):
        raise FileExistsError(output_dir)
    staging = output_dir.with_name(f".{output_dir.name}.owner-{attempt_id}")
    if os.path.lexists(staging):
        raise FileExistsError(staging)
    os.mkdir(staging)
    try:
        recovery_io.write_exclusive_fsync(
            staging / Path(protocol.ATTEMPT_OWNER_PATH).name, owner_payload
        )
        recovery_io.write_exclusive_fsync(
            staging / Path(protocol.PROGRESS_PATH).name, genesis_payload
        )
        os.rename(staging, output_dir)
    except BaseException:
        if os.path.lexists(staging):
            raise RuntimeError("incomplete diagnostic owner staging requires review")
        raise
    observed = {item.name for item in output_dir.iterdir()}
    if observed != {"attempt-owner.json", "progress.json"}:
        raise RuntimeError("diagnostic owner claim topology differs")


def _run_frozen_diagnostic_session(
    *,
    dependencies: tuple[Any, ...],
    expected_environment: Mapping[str, Any],
    records: Sequence[Mapping[str, Any]],
    artifact_payloads: Mapping[str, bytes],
    append_progress: ProgressAppender,
) -> tuple[list[dict[str, Any]], dict[str, float | int]]:
    """Future-authority producer for the exact 7 x 18 checkpoint topology.

    This function is unreachable from every current CLI/run mode.  The later
    authority gate must additionally freeze owner/lease/terminal orchestration
    before calling it.
    """

    from fullcycle_bridge import (  # noqa: PLC0415
        mm005_browser_research_adapter_verifier as adapter_verifier,
    )
    from fullcycle_bridge import (  # noqa: PLC0415
        mm005_browser_research_model_evaluation as evaluation,
    )
    from scripts import run_mm003_qlora_post_training_v2 as upstream_runner  # noqa: PLC0415

    torch, image_class, peft_model_class, processor_class, model_class, bnb_class = (
        dependencies
    )
    observed_environment = upstream_runner.observed_environment(torch)
    observed_projection = {
        name: observed_environment[name]
        for name in scientific_protocol.OBSERVED_ENVIRONMENT_FIELDS
    }
    if observed_projection != dict(expected_environment):
        raise RuntimeError("diagnostic execution environment mismatch")
    append_progress("context_preflight_completed", None, None, None)
    upstream_runner._enable_offline_execution()
    upstream_runner._seed_all(torch, v2.SEED)
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    started = time.perf_counter()
    processor = processor_class.from_pretrained(
        ROOT / v2.MODEL_SNAPSHOT_ROOT,
        local_files_only=True,
        min_pixels=256 * 28 * 28,
        max_pixels=1280 * 28 * 28,
        use_fast=False,
    )
    append_progress("base_load_started", None, None, None)
    base_model = model_class.from_pretrained(
        ROOT / v2.MODEL_SNAPSHOT_ROOT,
        quantization_config=upstream_runner._quantization_config(torch, bnb_class),
        attn_implementation="sdpa",
        device_map={"": 0},
        local_files_only=True,
        low_cpu_mem_usage=True,
    )
    append_progress("base_load_completed", None, None, None)
    append_progress("adapter_load_started", None, None, None)
    model = peft_model_class.from_pretrained(
        base_model,
        ROOT / v2.ADAPTER_ROOT,
        is_trainable=False,
        local_files_only=True,
    ).eval()
    append_progress("adapter_load_completed", None, None, None)
    model.config.use_cache = True
    if model.training is not False or any(
        parameter.requires_grad for parameter in model.parameters()
    ):
        raise RuntimeError("diagnostic model has trainable state")

    by_id = {str(item.get("record_id")): item for item in records}
    if set(scientific_protocol.DIAGNOSTIC_CASE_ORDER) - set(by_id):
        raise RuntimeError("diagnostic record registry is incomplete")
    screenshot_payloads, snapshot_payloads = evaluation.artifact_input_sets(
        artifact_payloads
    )
    summaries: list[dict[str, Any]] = []
    with torch.inference_mode():
        for diagnostic_index, record_id in enumerate(
            scientific_protocol.DIAGNOSTIC_CASE_ORDER
        ):
            record = by_id[record_id]
            summary = _run_one_diagnostic_case(
                torch=torch,
                model=model,
                processor=processor,
                evaluation=evaluation,
                adapter_verifier=adapter_verifier,
                image_class=image_class,
                record=record,
                record_id=record_id,
                diagnostic_index=diagnostic_index,
                artifact_payloads=artifact_payloads,
                screenshot_payloads=screenshot_payloads,
                snapshot_payloads=snapshot_payloads,
                append_progress=append_progress,
            )
            summaries.append(summary)
    resources: dict[str, float | int] = {
        "elapsed_seconds": time.perf_counter() - started,
        "peak_gpu_allocated_bytes": int(torch.cuda.max_memory_allocated()),
        "peak_gpu_reserved_bytes": int(torch.cuda.max_memory_reserved()),
    }
    del model, base_model, processor
    gc.collect()
    torch.cuda.empty_cache()
    return summaries, resources


def _run_one_diagnostic_case(
    *,
    torch: Any,
    model: Any,
    processor: Any,
    evaluation: Any,
    adapter_verifier: Any,
    image_class: Any,
    record: Mapping[str, Any],
    record_id: str,
    diagnostic_index: int,
    artifact_payloads: Mapping[str, bytes],
    screenshot_payloads: Mapping[str, bytes],
    snapshot_payloads: Mapping[str, bytes],
    append_progress: ProgressAppender,
) -> dict[str, Any]:
    def checkpoint(event: str, summary: Mapping[str, Any] | None = None) -> None:
        append_progress(event, record_id, diagnostic_index, summary)

    checkpoint("runtime_messages_build_started")
    adapted = adapter_verifier.adapt_record(
        record, screenshot_payloads, snapshot_payloads
    )
    images: list[Any] = []
    try:
        for payload in adapted.screenshot_payloads:
            source_image = image_class.open(io.BytesIO(payload))
            try:
                converted_image = source_image.convert("RGB")
            except BaseException:
                source_image.close()
                raise
            if converted_image is not source_image:
                source_image.close()
            images.append(converted_image)
        messages = evaluation.build_runtime_messages(adapted.model_payload(), images)
        checkpoint("runtime_messages_build_completed")

        checkpoint("pre_generation_cuda_sync_started")
        torch.cuda.synchronize()
        checkpoint("pre_generation_cuda_sync_completed")

        checkpoint("chat_template_started")
        text = processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        checkpoint("chat_template_completed")

        checkpoint("processor_tensorization_started")
        inputs = processor(
            text=[text], images=list(images), padding=True, return_tensors="pt"
        )
        checkpoint("processor_tensorization_completed")

        checkpoint("processor_device_transfer_started")
        inputs = inputs.to("cuda")
        checkpoint("processor_device_transfer_completed")

        checkpoint("model_generate_started")
        generation_started = time.perf_counter()
        generated = model.generate(
            **inputs,
            do_sample=False,
            max_new_tokens=v2.MAX_NEW_TOKENS,
            repetition_penalty=1.05,
            temperature=None,
            use_cache=True,
        )
        checkpoint("model_generate_completed")

        checkpoint("decode_started")
        trimmed = generated[:, inputs.input_ids.shape[1] :]
        raw_output = processor.batch_decode(
            trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
        )[0]
        generated_tokens = int(trimmed.shape[1])
        checkpoint("decode_completed")

        checkpoint("post_generation_cuda_sync_started")
        torch.cuda.synchronize()
        latency_seconds = time.perf_counter() - generation_started
        checkpoint("post_generation_cuda_sync_completed")

        checkpoint("case_result_build_started")
        case = evaluation.build_case_result(
            record=record,
            artifact_payloads=artifact_payloads,
            raw_output=raw_output,
            generated_tokens=generated_tokens,
            latency_seconds=latency_seconds,
        )
        summary = result_contract.build_case_result_summary(
            case, diagnostic_index=diagnostic_index
        )
        for image in images:
            image.close()
        checkpoint("case_result_build_completed", summary)
        return summary
    finally:
        for image in images:
            try:
                image.close()
            except Exception:
                pass


def _require_commit_ancestor(commit: str) -> None:
    process = _git_process("merge-base", "--is-ancestor", commit, "HEAD")
    if process.returncode != 0 or process.stdout:
        raise RuntimeError("published diagnostic protocol commit is not an ancestor")


def _require_unique_parent(child: str, parent: str) -> None:
    _require_unique_parent_at(ROOT, child, parent)


def _require_unique_parent_at(root: Path, child: str, parent: str) -> None:
    lineage = _git_text_at(root, "rev-list", "--parents", "-n", "1", child).split()
    if lineage != [child, parent]:
        raise RuntimeError("diagnostic lineage unique direct parent differs")


def _require_aligned_clean_master() -> str:
    _require_no_hidden_index_flags()
    branch = _git_text("rev-parse", "--abbrev-ref", "HEAD")
    head = _git_text("rev-parse", "HEAD")
    origin_master = _git_text("rev-parse", "refs/remotes/origin/master")
    status = _git_text("status", "--porcelain=v1", "--untracked-files=all")
    if branch != "master" or head != origin_master or status:
        raise RuntimeError(
            "execution authority requires clean aligned master and origin/master"
        )
    return head


def _implementation_source_context(commit: str) -> dict[str, Any]:
    _require_commit_ancestor(commit)
    initial_commit = result_contract.INITIAL_IMPLEMENTATION_PUBLICATION_COMMIT
    _require_commit_ancestor(initial_commit)
    _require_unique_parent(
        result_contract.ZERO_BANDWIDTH_MAINTENANCE_COMMIT,
        result_contract.PROTOCOL_MERGE_COMMIT,
    )
    _require_unique_parent(
        result_contract.IMPLEMENTATION_BASE_COMMIT,
        result_contract.ZERO_BANDWIDTH_MAINTENANCE_COMMIT,
    )
    _require_unique_parent(initial_commit, result_contract.IMPLEMENTATION_BASE_COMMIT)
    _require_unique_parent(commit, initial_commit)
    initial_diff = set(
        _git_name_only_paths(result_contract.IMPLEMENTATION_BASE_COMMIT, initial_commit)
    )
    final_diff = set(
        _git_name_only_paths(result_contract.IMPLEMENTATION_BASE_COMMIT, commit)
    )
    compatibility_diff = set(_git_name_only_paths(initial_commit, commit))
    if (
        initial_diff != set(IMPLEMENTATION_SLICE_PATHS)
        or final_diff != set(IMPLEMENTATION_SLICE_PATHS)
        or not compatibility_diff
        or not compatibility_diff.issubset(IMPLEMENTATION_SLICE_PATHS)
    ):
        raise RuntimeError("implementation freeze tree delta is not the reviewed slice")
    bindings: dict[str, dict[str, Any]] = {}
    introductions: set[str] = set()
    for name, relative in sorted(result_contract.IMPLEMENTATION_SOURCE_PATHS.items()):
        payload = _git_blob_bytes(commit, relative)
        if _read_repository_file(relative) != payload:
            raise RuntimeError(f"implementation source differs from freeze: {name}")
        introduced = [
            line
            for line in _git_text(
                "log",
                "--first-parent",
                "--diff-filter=A",
                "--format=%H",
                "--",
                relative,
            ).splitlines()
            if line
        ]
        if introduced != [initial_commit]:
            raise RuntimeError(f"implementation source introduction differs: {name}")
        introductions.add(introduced[0])
        bindings[name] = {
            "path": relative,
            "bytes": len(payload),
            "sha256": protocol.sha256_bytes(payload),
            "tracked_bytes_equal_implementation_freeze_commit_blob": True,
        }
    if introductions != {initial_commit}:
        raise RuntimeError("implementation sources do not share one introduction")
    return {
        "protocol_merge_commit": result_contract.PROTOCOL_MERGE_COMMIT,
        "zero_bandwidth_maintenance_commit": (
            result_contract.ZERO_BANDWIDTH_MAINTENANCE_COMMIT
        ),
        "implementation_base_commit": result_contract.IMPLEMENTATION_BASE_COMMIT,
        "initial_implementation_publication_commit": initial_commit,
        "freeze_commit": commit,
        "source_bindings": bindings,
        "protocol_merge_commit_is_ancestor_of_implementation_base": True,
        "zero_bandwidth_maintenance_unique_parent_is_protocol_merge_commit": True,
        "implementation_base_unique_parent_is_zero_bandwidth_maintenance_commit": (
            True
        ),
        "implementation_base_is_unique_parent_of_initial_publication_commit": True,
        "initial_implementation_publication_is_unique_parent_of_freeze_commit": True,
        "three_sources_share_first_parent_introduction_commit": True,
        "initial_exact_reviewed_slice_delta": True,
        "final_exact_reviewed_slice_delta": True,
        "compatibility_delta_is_nonempty_reviewed_slice_subset": True,
    }


def _authority_source_context(
    *,
    authority_payload: bytes,
    implementation_freeze_commit: str,
    authority: Mapping[str, Any],
) -> dict[str, Any]:
    introductions = [
        line
        for line in _git_text(
            "log",
            "--first-parent",
            "--diff-filter=A",
            "--format=%H",
            "--",
            result_contract.EXECUTION_AUTHORITY_PATH,
        ).splitlines()
        if line
    ]
    if len(introductions) != 1:
        raise RuntimeError(
            "execution authority must have one first-parent introduction"
        )
    commit = introductions[0]
    _require_commit_ancestor(commit)
    _require_unique_parent(commit, implementation_freeze_commit)
    if (
        _git_blob_bytes(commit, result_contract.EXECUTION_AUTHORITY_PATH)
        != authority_payload
    ):
        raise RuntimeError("execution authority differs from introduction blob")
    delta = set(_git_name_only_paths(implementation_freeze_commit, commit))
    if delta != set(result_contract.EXECUTION_AUTHORITY_SLICE_PATHS):
        raise RuntimeError("execution authority freeze tree delta is not reviewed")
    dependency_bindings = _validate_critical_execution_dependency_receipts(
        authority, commit=commit
    )
    return {
        "freeze_commit": commit,
        "artifact": {
            "path": result_contract.EXECUTION_AUTHORITY_PATH,
            "bytes": len(authority_payload),
            "sha256": protocol.sha256_bytes(authority_payload),
        },
        "critical_execution_dependency_receipts": dependency_bindings,
        "implementation_freeze_is_unique_parent": True,
        "one_first_parent_introduction_commit": True,
        "exact_reviewed_slice_delta": True,
    }


def _validate_critical_execution_dependency_receipts(
    authority: Mapping[str, Any], *, commit: str | None
) -> dict[str, dict[str, Any]]:
    observed = _mapping(
        authority.get("critical_execution_dependency_receipts"),
        "$.authority.critical_execution_dependency_receipts",
    )
    if set(observed) != set(result_contract.CRITICAL_EXECUTION_DEPENDENCY_SOURCE_PATHS):
        raise RuntimeError("critical execution dependency receipt fields differ")
    bindings: dict[str, dict[str, Any]] = {}
    for name, relative in sorted(
        result_contract.CRITICAL_EXECUTION_DEPENDENCY_SOURCE_PATHS.items()
    ):
        payload = _read_repository_file(relative)
        if commit is not None and _git_blob_bytes(commit, relative) != payload:
            raise RuntimeError(
                f"critical execution dependency differs from freeze: {name}"
            )
        expected = {
            "path": relative,
            "bytes": len(payload),
            "sha256": protocol.sha256_bytes(payload),
        }
        if dict(_mapping(observed.get(name), f"$.authority.source.{name}")) != expected:
            raise RuntimeError(f"critical execution dependency receipt differs: {name}")
        bindings[name] = expected
    return bindings


def _git_path_exists(commit: str, relative: str) -> bool:
    _validate_repository_relative_path(relative)
    process = _git_process("cat-file", "-e", f"{commit}:{relative}")
    if process.stdout:
        raise RuntimeError("unexpected Git output while checking bound path")
    return process.returncode == 0


def _require_unclaimed_execution_state(
    authority_context: Mapping[str, Any],
) -> None:
    _require_unclaimed_execution_state_at(ROOT, authority_context)


def _require_unclaimed_execution_state_at(
    root: Path, authority_context: Mapping[str, Any]
) -> None:
    _require_reserved_sibling_staging_absent_at(root)
    topology = _output_topology_at(root)
    _validate_output_topology(topology)
    if topology["output_parent"]:
        raise RuntimeError("diagnostic parent-only evidence prohibits a new attempt")
    if topology["output_root"] or any(
        topology[name]
        for name in ("attempt_owner", "progress", "success_result", "failure")
    ):
        raise RuntimeError("diagnostic attempt is already claimed")
    lifecycle_pair = (
        topology["lifecycle_lease_root"],
        topology["lifecycle_lease"],
    )
    if lifecycle_pair not in {(False, False), (True, True)}:
        raise RuntimeError("diagnostic lifecycle lease is incomplete")
    if lifecycle_pair == (True, True):
        _validate_lifecycle_state_at(root, authority_context)
        raise RuntimeError(
            "diagnostic pre-owner lifecycle evidence prohibits a new attempt"
        )


def _require_runtime_outputs_absent(*, allow_lifecycle: bool = False) -> None:
    _require_reserved_sibling_staging_absent()
    forbidden = {
        "output_root": os.path.lexists(ROOT / protocol.RUN_OUTPUT_ROOT),
        "attempt_owner": os.path.lexists(ROOT / protocol.ATTEMPT_OWNER_PATH),
        "progress": os.path.lexists(ROOT / protocol.PROGRESS_PATH),
        "success_result": os.path.lexists(ROOT / protocol.SUCCESS_RESULT_PATH),
        "failure": os.path.lexists(ROOT / protocol.FAILURE_PATH),
    }
    if any(forbidden.values()):
        raise RuntimeError("diagnostic runtime output already exists")
    lifecycle_root_present = os.path.lexists(ROOT / protocol.LIFECYCLE_LEASE_ROOT)
    lifecycle_present = os.path.lexists(ROOT / protocol.LIFECYCLE_LEASE_PATH)
    if not allow_lifecycle and (lifecycle_root_present or lifecycle_present):
        raise RuntimeError("diagnostic lifecycle lease already exists")
    if allow_lifecycle and not (lifecycle_root_present and lifecycle_present):
        raise RuntimeError("diagnostic lifecycle lease is incomplete")


def _lifecycle_lease_marker(
    *, authority_freeze_commit: str, authority_payload: bytes
) -> bytes:
    return result_contract.artifact_json_bytes(
        {
            "kind": "mm005_generation_failure_diagnostic_single_writer_lease",
            "authority_freeze_commit": authority_freeze_commit,
            "execution_authority": {
                "path": result_contract.EXECUTION_AUTHORITY_PATH,
                "bytes": len(authority_payload),
                "sha256": protocol.sha256_bytes(authority_payload),
            },
        }
    )


def _terminal_summary(value: Mapping[str, Any], *, kind: str) -> dict[str, Any]:
    if kind not in {"success", "failure"}:
        raise RuntimeError("terminal summary kind invalid")
    return {
        "checked": False,
        "kind": kind,
        "gate_id": value.get("gate_id"),
        "experiment_id": value.get("experiment_id"),
        "run_id": value.get("run_id"),
        "selected_outcome": _mapping(value.get("decision"), "$.terminal.decision").get(
            "selected_outcome"
        ),
        "diagnostic_attempt_consumed": _mapping(
            value.get("claims"), "$.terminal.claims"
        ).get("diagnostic_attempt_consumed"),
        "runtime_eligible": False,
    }


def _safe_exception_type(exc: BaseException) -> str:
    value = type(exc).__name__
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,95}", value) is None:
        return "BaseException"
    return value


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _git_blob_bytes(commit: str, relative: str) -> bytes:
    return _git_blob_bytes_at(ROOT, commit, relative)


def _git_blob_bytes_at(root: Path, commit: str, relative: str) -> bytes:
    _validate_repository_relative_path(relative)
    process = _git_process_at(root, "cat-file", "blob", f"{commit}:{relative}")
    if process.returncode != 0:
        raise RuntimeError(f"unable to read frozen Git blob: {relative}")
    if len(process.stdout) > MAX_BOUND_FILE_BYTES:
        raise RuntimeError(f"frozen Git blob exceeds byte limit: {relative}")
    return process.stdout


def _git_text(*args: str) -> str:
    return _git_text_at(ROOT, *args)


def _git_text_at(root: Path, *args: str) -> str:
    process = _git_process_at(root, *args)
    if process.returncode != 0:
        raise RuntimeError(f"Git command failed: {' '.join(args)}")
    try:
        return process.stdout.decode("utf-8").strip()
    except UnicodeDecodeError as exc:
        raise RuntimeError("Git output is not UTF-8") from exc


def _git_name_only_paths(base: str, head: str) -> tuple[str, ...]:
    """Read exact Git paths without quotePath or newline ambiguity."""

    return _git_name_only_paths_at(ROOT, base, head)


def _git_name_only_paths_at(root: Path, base: str, head: str) -> tuple[str, ...]:
    """Read exact Git paths below one validated repository root."""

    process = _git_process_at(
        root,
        "diff",
        "--no-ext-diff",
        "--no-renames",
        "--name-only",
        "-z",
        base,
        head,
    )
    if process.returncode != 0 or process.stderr:
        raise RuntimeError("Git name-only diff failed")
    payload = process.stdout
    if not payload:
        return ()
    if not payload.endswith(b"\x00"):
        raise RuntimeError("Git name-only diff is not NUL terminated")
    paths: list[str] = []
    for raw_path in payload[:-1].split(b"\x00"):
        if not raw_path:
            raise RuntimeError("Git name-only diff contains an empty path")
        try:
            relative = raw_path.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise RuntimeError("Git path is not UTF-8") from exc
        _validate_repository_relative_path(relative)
        paths.append(relative)
    if len(paths) != len(set(paths)):
        raise RuntimeError("Git name-only diff contains duplicate paths")
    return tuple(paths)


def _require_no_hidden_index_flags() -> None:
    """Reject index flags that can hide tracked worktree drift from status."""

    _require_no_hidden_index_flags_at(ROOT)


def _require_no_hidden_index_flags_at(root: Path) -> None:
    """Reject hidden index flags below one validated repository root."""

    process = _git_process_at(root, "ls-files", "-v", "-z")
    if process.returncode != 0 or process.stderr:
        raise RuntimeError("unable to inspect Git index flags")
    payload = process.stdout
    if payload and not payload.endswith(b"\x00"):
        raise RuntimeError("Git index listing is not NUL terminated")
    entries = payload[:-1].split(b"\x00") if payload else ()
    for entry in entries:
        if len(entry) < 3 or entry[1:2] != b" ":
            raise RuntimeError("Git index listing has an invalid record")
        try:
            tag = entry[:1].decode("ascii")
            relative = entry[2:].decode("utf-8")
        except UnicodeDecodeError as exc:
            raise RuntimeError("Git index listing is not UTF-8") from exc
        _validate_repository_relative_path(relative)
        if tag == "S" or tag.islower():
            raise RuntimeError(
                "Git assume-unchanged or skip-worktree index flag is forbidden"
            )


def _git_process(*args: str) -> subprocess.CompletedProcess[bytes]:
    return _git_process_at(ROOT, *args)


def _git_process_at(root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.upper().startswith("GIT_")
    }
    environment.update(
        {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_NO_LAZY_FETCH": "1",
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_GRAFT_FILE": os.devnull,
        }
    )
    return subprocess.run(
        [
            "git",
            "-c",
            "core.hooksPath=NUL" if os.name == "nt" else "core.hooksPath=/dev/null",
            "-c",
            "filter.lfs.process=",
            "-c",
            "filter.lfs.required=false",
            "-c",
            "core.commitGraph=false",
            "-c",
            "core.fsmonitor=false",
            "-c",
            "advice.graftFileDeprecated=false",
            *args,
        ],
        cwd=root,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=environment,
    )


def _read_repository_file(relative: str) -> bytes:
    _validate_repository_relative_path(relative)
    return _read_regular_file_once(ROOT / relative)


def _validate_repository_relative_path(relative: str) -> None:
    if (
        type(relative) is not str
        or not relative
        or "\\" in relative
        or "\x00" in relative
    ):
        raise RuntimeError("unsafe repository-relative path")
    path = PurePosixPath(relative)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise RuntimeError("unsafe repository-relative path")
    if path.parts[0].endswith(":"):
        raise RuntimeError("unsafe repository-relative path")


def _read_regular_file_once(path: Path) -> bytes:
    if not os.path.lexists(path):
        raise RuntimeError(f"missing bound file: {path.name}")
    before = path.lstat()
    if (
        not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or path.is_symlink()
        or _metadata_is_reparse(before)
    ):
        raise RuntimeError(f"unsafe bound file: {path.name}")
    with path.open("rb") as handle:
        opened = os.fstat(handle.fileno())
        payload = handle.read(MAX_BOUND_FILE_BYTES + 1)
        after_opened = os.fstat(handle.fileno())
    after = path.lstat()
    if len(payload) > MAX_BOUND_FILE_BYTES:
        raise RuntimeError(f"bound file exceeds byte limit: {path.name}")
    identities = {
        (item.st_dev, item.st_ino, item.st_mode, item.st_nlink, item.st_size)
        for item in (before, opened, after_opened, after)
    }
    if len(identities) != 1:
        raise RuntimeError(f"bound file changed while reading: {path.name}")
    return payload


def _require_safe_directory(path: Path) -> None:
    metadata = path.lstat()
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or path.is_symlink()
        or _metadata_is_reparse(metadata)
    ):
        raise RuntimeError("unsafe diagnostic output parent")


def _metadata_is_reparse(metadata: os.stat_result) -> bool:
    attributes = getattr(metadata, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(attributes & reparse_flag)


def _mapping(value: object, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise RuntimeError(f"expected object at {location}")
    return value


def _object_sequence(value: object, location: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise RuntimeError(f"expected object sequence at {location}")
    return [_mapping(item, f"{location}[{index}]") for index, item in enumerate(value)]


def _bytes_value(value: object, location: str) -> bytes:
    if type(value) is not bytes or not value:
        raise RuntimeError(f"expected nonempty bytes at {location}")
    return value


def _bytes_mapping(value: object, location: str) -> dict[str, bytes]:
    observed = _mapping(value, location)
    result: dict[str, bytes] = {}
    for key, item in observed.items():
        if type(key) is not str:
            raise RuntimeError(f"expected string path at {location}")
        result[key] = _bytes_value(item, f"{location}.{key}")
    return result


def _receipt_mapping(value: object, location: str) -> dict[str, Mapping[str, Any]]:
    observed = _mapping(value, location)
    return {
        str(key): _mapping(item, f"{location}.{key}") for key, item in observed.items()
    }


if __name__ == "__main__":
    raise SystemExit(main())
