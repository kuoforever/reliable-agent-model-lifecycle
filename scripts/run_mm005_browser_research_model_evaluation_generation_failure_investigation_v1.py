"""Run or check the frozen MM-005 Browser static failure investigation."""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(ROOT))

from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_model_evaluation_generation_failure_investigation as protocol,
)
from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_model_evaluation_generation_failure_investigation_result as result_contract,
)

MAX_BOUND_FILE_BYTES = 64 * 1024 * 1024
MAX_HISTORICAL_WORKER_OUTPUT_BYTES = 64 * 1024
_GIT_COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}")
_HISTORICAL_WORKER_ARGUMENT = "--historical-check-worker"
_HISTORICAL_WORKER_ENV = "MM005_GENERATION_FAILURE_HISTORICAL_WORKER"
_HISTORICAL_WORKER_COMMIT_ENV = "MM005_GENERATION_FAILURE_HISTORICAL_WORKER_COMMIT"
_HISTORICAL_PROTOCOL_MERGE_COMMIT = "fe430710924537a18e677b75202f0c19806d3f12"
_HISTORICAL_PROTOCOL_PATH = (
    "configs/mm005_browser_research_model_evaluation_generation_failure_"
    "investigation_protocol_v1.json"
)
_HISTORICAL_PROTOCOL_BYTES = 33_476
_HISTORICAL_PROTOCOL_SHA256 = (
    "sha256:be8ecd067e884a8d60c9664013943d6887c769ac35a389934509b73338247494"
)
_HISTORICAL_TRUSTED_MAINLINE_REF = "refs/remotes/origin/master"
_HISTORICAL_PROTOCOL_SOURCE_PATHS = {
    "adapter_verifier": (
        "src/fullcycle_bridge/mm005_browser_research_adapter_verifier.py"
    ),
    "browser_data_contract": "src/fullcycle_bridge/mm005_browser_research_data.py",
    "failure_classification_v2": (
        "src/fullcycle_bridge/"
        "mm005_browser_research_model_evaluation_failure_classification_v2.py"
    ),
    "investigation_builder": (
        "scripts/prepare_mm005_browser_research_model_evaluation_generation_"
        "failure_investigation_protocol_v1.py"
    ),
    "investigation_contract": (
        "src/fullcycle_bridge/"
        "mm005_browser_research_model_evaluation_generation_failure_"
        "investigation.py"
    ),
    "model_evaluation_contract_v1": (
        "src/fullcycle_bridge/mm005_browser_research_model_evaluation.py"
    ),
    "recovery_contract_v2": (
        "src/fullcycle_bridge/mm005_browser_research_model_evaluation_protocol_v2.py"
    ),
    "recovery_protocol_builder_v2": (
        "scripts/prepare_mm005_browser_research_model_evaluation_v2.py"
    ),
    "shared_generation_helper": ("scripts/run_mm003_multimodal_gui_action_baseline.py"),
    "v2_runner": "scripts/run_mm005_browser_research_model_evaluation_v2.py",
}
_HISTORICAL_TARGET_RECORD_ID = (
    "sha256:26b3a9da0467d1c18cc4a050ec10dc03a415a9c3a38a2a37de8b9805c67adaf7"
)
_HISTORICAL_IMPLEMENTATION_SOURCE_PATHS = (
    "scripts/run_mm005_browser_research_model_evaluation_generation_failure_"
    "investigation_v1.py",
    "src/fullcycle_bridge/mm005_browser_research_model_evaluation_generation_"
    "failure_investigation_result.py",
    "tests/test_mm005_browser_research_model_evaluation_generation_failure_"
    "investigation_result.py",
)
_HISTORICAL_IMPLEMENTATION_SLICE_PATHS = frozenset(
    {
        "AI_Infra_LLM_Agent_待做任务清单.md",
        "PROJECT_STATUS.md",
        "README.md",
        "docs/MM-005-browser-research-model-evaluation-generation-failure-"
        "investigation-implementation-v1.md",
        "docs/MM-005-browser-research-model-evaluation-generation-failure-"
        "investigation-protocol-v1.md",
        "docs/README.md",
        "scripts/validate_offline.py",
        *_HISTORICAL_IMPLEMENTATION_SOURCE_PATHS,
    }
)
_HISTORICAL_OUTCOME_NEXT_GATE: dict[str, str | None] = {
    "protocol_or_lineage_invalid": None,
    "deterministic_static_input_or_message_failure_reproduced": (
        "MM-005-browser-research-model-evaluation-generation-failure-"
        "static-remediation-protocol-v1"
    ),
    "static_difference_observed_without_causal_failure": (
        "MM-005-browser-research-model-evaluation-generation-failure-"
        "static-difference-isolation-protocol-v1"
    ),
    "static_pipeline_reconstructed_without_contract_violation": (
        "MM-005-browser-research-model-evaluation-generation-failure-"
        "diagnostic-protocol-v1"
    ),
    "static_investigation_inconclusive": (
        "MM-005-browser-research-model-evaluation-generation-failure-"
        "diagnostic-protocol-v1"
    ),
}
_SHA256_RECEIPT_PATTERN = re.compile(r"sha256:[0-9a-f]{64}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--plan", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument(
        _HISTORICAL_WORKER_ARGUMENT,
        action="store_true",
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args(argv)

    summary = run(
        plan=args.plan,
        check=args.check,
        historical_check_worker=args.historical_check_worker,
    )
    print(json.dumps(summary, sort_keys=True, separators=(",", ":")))
    return 0


def run(
    *,
    plan: bool = False,
    check: bool = False,
    historical_check_worker: bool = False,
    executed_at_utc: str | None = None,
) -> dict[str, Any]:
    """Plan, exclusively publish once, or validate without republishing."""

    modes = (plan, check, historical_check_worker)
    if any(type(mode) is not bool for mode in modes) or sum(modes) > 1:
        raise RuntimeError("invalid investigation mode")
    output = ROOT / result_contract.RESULT_PATH
    if historical_check_worker:
        return _run_historical_check_worker(output)
    if check:
        result_payload = _read_regular_file_once(output)
        summary = _delegate_historical_check(result_payload)
        if _read_regular_file_once(output) != result_payload:
            raise RuntimeError("static investigation result changed during check")
        return summary

    protocol_context = _published_protocol_context()
    if plan:
        return {
            "plan_only": True,
            "gate_id": result_contract.GATE_ID,
            "investigation_id": result_contract.INVESTIGATION_ID,
            "fixed_result_path": result_contract.RESULT_PATH,
            "result_present": os.path.lexists(output),
            "formal_execution_eligible": False,
            "eligibility_reason": (
                "implementation_contract_runner_and_tests_must_cleanly_merge_"
                "before_formal_execution"
            ),
            "outcome_precedence": list(result_contract.OUTCOME_PRECEDENCE),
            "model_processor_pil_cuda_network_browser_authorized": False,
            "runtime_eligible": False,
        }

    if os.path.lexists(output):
        raise FileExistsError(output)
    implementation_freeze_commit = _require_aligned_merged_master()
    _require_historical_implementation_introduction_commit(implementation_freeze_commit)
    _require_historical_implementation_slice(implementation_freeze_commit)
    implementation_context = _implementation_source_context(
        implementation_freeze_commit
    )
    observed_at = (
        _utc_now() if executed_at_utc is None else _validate_timestamp(executed_at_utc)
    )
    result = _build_result(
        protocol_context=protocol_context,
        implementation_context=implementation_context,
        executed_at_utc=observed_at,
    )
    payload = protocol.artifact_json_bytes(result)
    _write_exclusive_result(output, payload)
    return _summary(result, checked=False)


def _delegate_historical_check(result_payload: bytes) -> dict[str, Any]:
    """Validate trust here, then run exact result semantics at its freeze commit."""

    result = protocol.parse_strict_json_bytes(
        result_payload, location="$.static_investigation_result"
    )
    implementation_context = _historical_implementation_source_context(result)
    freeze_commit = implementation_context.get("freeze_commit")
    if not isinstance(freeze_commit, str):
        raise RuntimeError("historical implementation freeze commit is invalid")
    _require_historical_implementation_introduction_commit(freeze_commit)
    _require_historical_implementation_slice(freeze_commit)
    protocol_ancestor = _git_process(
        "merge-base",
        "--is-ancestor",
        _HISTORICAL_PROTOCOL_MERGE_COMMIT,
        freeze_commit,
    )
    if protocol_ancestor.returncode != 0:
        raise RuntimeError("protocol merge is not an implementation ancestor")
    _require_historical_protocol_bootstrap(result, freeze_commit)
    summary = _invoke_historical_worker(result_payload, freeze_commit)
    _validate_historical_worker_summary(summary, freeze_commit)
    return summary


def _run_historical_check_worker(output: Path) -> dict[str, Any]:
    """Run only inside the isolated checkout selected by the parent checker."""

    freeze_commit = os.environ.get(_HISTORICAL_WORKER_COMMIT_ENV)
    if os.environ.get(_HISTORICAL_WORKER_ENV) != "1" or not isinstance(
        freeze_commit, str
    ):
        raise RuntimeError("historical check worker is not authorized")
    _validate_git_commit(freeze_commit)
    if _git_text("rev-parse", "HEAD") != freeze_commit:
        raise RuntimeError("historical check worker commit mismatch")
    result_payload = _read_regular_file_once(output)
    result = protocol.parse_strict_json_bytes(
        result_payload, location="$.static_investigation_result"
    )
    implementation = _mapping(
        result.get("implementation_lineage"), "$.implementation_lineage"
    )
    if implementation.get("implementation_freeze_commit") != freeze_commit:
        raise RuntimeError("historical worker result commit mismatch")
    return _check_result_in_current_checkout(result_payload, result)


def _check_result_in_current_checkout(
    result_payload: bytes,
    result: Mapping[str, Any],
) -> dict[str, Any]:
    """Recompute only when the checkout itself is the recorded historical tree."""

    protocol_context = _historical_protocol_context(result)
    implementation_context = _historical_implementation_source_context(result)
    result_inputs = _result_inputs(
        protocol_context=protocol_context,
        implementation_context=implementation_context,
        executed_at_utc=str(result.get("executed_at_utc")),
    )
    expected = _build_result(
        protocol_context=protocol_context,
        implementation_context=implementation_context,
        executed_at_utc=str(result.get("executed_at_utc")),
    )
    result_contract.validate_static_investigation_result(result, **result_inputs)
    if protocol.artifact_json_bytes(expected) != result_payload:
        raise RuntimeError("static investigation result differs from recomputation")
    return _summary(expected, checked=True)


def _invoke_historical_worker(
    result_payload: bytes,
    freeze_commit: str,
) -> dict[str, Any]:
    _validate_git_commit(freeze_commit)
    with tempfile.TemporaryDirectory(
        prefix="mm005-generation-failure-historical-check-"
    ) as directory:
        temporary_root = Path(directory).resolve(strict=True)
        checkout = temporary_root / "checkout"
        _clone_historical_checkout(checkout, freeze_commit)
        if checkout.resolve(strict=True).parent != temporary_root:
            raise RuntimeError("historical checkout escaped temporary root")
        _write_historical_worker_result(checkout, result_payload)
        runner_relative = result_contract.IMPLEMENTATION_SOURCE_PATHS["result_runner"]
        command = _historical_worker_command(checkout, runner_relative, freeze_commit)
        worker_environment = _historical_git_environment()
        worker_environment[_HISTORICAL_WORKER_ENV] = "1"
        worker_environment[_HISTORICAL_WORKER_COMMIT_ENV] = freeze_commit
        completed = _run_bounded_process(
            command,
            cwd=checkout,
            timeout=120,
            environment=worker_environment,
        )
        if (
            completed.returncode != 0
            or completed.stderr
            or not completed.stdout.endswith(b"\n")
            or completed.stdout.count(b"\n") != 1
            or len(completed.stdout) > MAX_HISTORICAL_WORKER_OUTPUT_BYTES
        ):
            raise RuntimeError("historical check worker failed")
        summary = protocol.parse_strict_json_bytes(
            completed.stdout, location="$.historical_check_worker_summary"
        )
        if protocol.artifact_json_bytes(summary) != completed.stdout:
            raise RuntimeError("historical check worker summary is not canonical")
        return dict(summary)


def _clone_historical_checkout(checkout: Path, freeze_commit: str) -> None:
    if os.path.lexists(checkout):
        raise RuntimeError("historical checkout target already exists")
    repository = ROOT.resolve(strict=True)
    git_environment = _historical_git_environment()
    filter_overrides = [
        "-c",
        f"core.hooksPath={os.devnull}",
        "-c",
        "filter.lfs.process=",
        "-c",
        "filter.lfs.smudge=",
        "-c",
        "filter.lfs.clean=",
        "-c",
        "filter.lfs.required=false",
        "-c",
        "core.symlinks=false",
    ]
    clone = _run_bounded_process(
        [
            "git",
            *filter_overrides,
            "clone",
            "--quiet",
            "--no-checkout",
            "--local",
            "--shared",
            "--",
            str(repository),
            str(checkout),
        ],
        cwd=repository,
        timeout=120,
        environment=git_environment,
    )
    if clone.returncode != 0:
        raise RuntimeError("unable to create local historical clone")
    checked_out = _run_bounded_process(
        [
            "git",
            *filter_overrides,
            "checkout",
            "--quiet",
            "--detach",
            freeze_commit,
        ],
        cwd=checkout,
        timeout=120,
        environment=git_environment,
    )
    if checked_out.returncode != 0:
        raise RuntimeError("unable to checkout historical implementation commit")
    observed = _run_bounded_process(
        ["git", *filter_overrides, "rev-parse", "HEAD"],
        cwd=checkout,
        timeout=30,
        environment=git_environment,
    )
    if (
        observed.returncode != 0
        or observed.stdout.decode("ascii").strip() != freeze_commit
    ):
        raise RuntimeError("historical checkout identity mismatch")


def _historical_git_environment() -> dict[str, str]:
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.upper().startswith("GIT_")
    }
    environment.update(
        {
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_LFS_SKIP_SMUDGE": "1",
            "GIT_NO_LAZY_FETCH": "1",
            "GIT_TERMINAL_PROMPT": "0",
        }
    )
    return environment


def _write_historical_worker_result(checkout: Path, payload: bytes) -> None:
    _validate_repository_relative_path(result_contract.RESULT_PATH)
    checkout_root = checkout.resolve(strict=True)
    candidate = Path(
        os.path.abspath(checkout_root / PurePosixPath(result_contract.RESULT_PATH))
    )
    if not candidate.is_relative_to(checkout_root) or os.path.lexists(candidate):
        raise RuntimeError("unsafe historical worker result path")
    parent = candidate.parent
    try:
        parent_stat = parent.lstat()
        parent_resolved = parent.resolve(strict=True)
    except OSError as exc:
        raise RuntimeError("unable to inspect historical result parent") from exc
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    if (
        parent_resolved != parent
        or parent.is_symlink()
        or not stat.S_ISDIR(parent_stat.st_mode)
        or bool(getattr(parent_stat, "st_file_attributes", 0) & reparse_flag)
    ):
        raise RuntimeError("unsafe historical result parent")
    with candidate.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def _historical_worker_command(
    checkout: Path,
    runner_relative: str,
    freeze_commit: str,
) -> list[str]:
    _validate_repository_relative_path(runner_relative)
    _validate_git_commit(freeze_commit)
    runner_path = Path(os.path.abspath(checkout / PurePosixPath(runner_relative)))
    checkout_root = checkout.resolve(strict=True)
    if not runner_path.is_relative_to(checkout_root):
        raise RuntimeError("historical runner escaped checkout")
    runner_payload = _read_regular_file_once(runner_path)
    if runner_payload != _git_blob_bytes(freeze_commit, runner_relative):
        raise RuntimeError("historical runner checkout bytes mismatch")
    return [
        sys.executable,
        "-I",
        "-S",
        "-B",
        str(runner_path),
        _HISTORICAL_WORKER_ARGUMENT,
    ]


def _validate_historical_worker_summary(
    summary: Mapping[str, Any], freeze_commit: str
) -> None:
    expected_keys = {
        "checked",
        "diagnostic_records",
        "gate_id",
        "implementation_freeze_commit",
        "model_free",
        "next_gate",
        "protocol_merge_commit",
        "protocol_sha256",
        "report_digest",
        "runtime_eligible",
        "runtime_root_cause_unresolved",
        "selected_outcome",
        "static_investigation_complete",
        "target_record",
        "valid",
    }
    selected_outcome = summary.get("selected_outcome")
    report_digest = summary.get("report_digest")
    if (
        set(summary) != expected_keys
        or summary.get("checked") is not True
        or summary.get("valid") is not True
        or summary.get("gate_id") != result_contract.GATE_ID
        or summary.get("protocol_merge_commit") != result_contract.PROTOCOL_MERGE_COMMIT
        or summary.get("implementation_freeze_commit") != freeze_commit
        or summary.get("protocol_sha256") != result_contract.PROTOCOL_SHA256
        or summary.get("diagnostic_records") != 7
        or summary.get("target_record") != _HISTORICAL_TARGET_RECORD_ID
        or not isinstance(selected_outcome, str)
        or selected_outcome not in _HISTORICAL_OUTCOME_NEXT_GATE
        or summary.get("next_gate")
        != _HISTORICAL_OUTCOME_NEXT_GATE.get(selected_outcome)
        or not isinstance(report_digest, str)
        or _SHA256_RECEIPT_PATTERN.fullmatch(report_digest) is None
        or summary.get("model_free") is not True
        or summary.get("static_investigation_complete") is not True
        or summary.get("runtime_root_cause_unresolved") is not True
        or summary.get("runtime_eligible") is not False
    ):
        raise RuntimeError("historical check worker summary mismatch")


def _run_bounded_process(
    command: Sequence[str],
    *,
    cwd: Path,
    timeout: int,
    environment: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(
            list(command),
            cwd=cwd,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            env=None if environment is None else dict(environment),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError("unable to run bounded historical process") from exc


def _published_protocol_context() -> dict[str, Any]:
    """Bind the PR #73 protocol/config/sources and independently recompute it."""

    from scripts import (
        prepare_mm005_browser_research_model_evaluation_generation_failure_investigation_protocol_v1 as protocol_builder,
    )

    commit = result_contract.PROTOCOL_MERGE_COMMIT
    _require_commit_ancestor(commit)
    preregistration_payload = _read_repository_file(protocol.PREREGISTRATION_PATH)
    if (
        len(preregistration_payload) != result_contract.PROTOCOL_BYTES
        or protocol.sha256_bytes(preregistration_payload)
        != result_contract.PROTOCOL_SHA256
        or _git_blob_bytes(commit, protocol.PREREGISTRATION_PATH)
        != preregistration_payload
    ):
        raise RuntimeError("published investigation protocol binding mismatch")
    preregistration = protocol.parse_strict_json_bytes(
        preregistration_payload, location="$.investigation_protocol"
    )
    if protocol.artifact_json_bytes(preregistration) != preregistration_payload:
        raise RuntimeError("published investigation protocol is not canonical")

    lineage = _mapping(preregistration.get("source_lineage"), "$.source_lineage")
    registered_sources = _mapping(
        lineage.get("protocol_sources"), "$.source_lineage.protocol_sources"
    )
    if set(registered_sources) != set(protocol.PROTOCOL_SOURCE_PATHS):
        raise RuntimeError("published protocol source closure mismatch")
    source_payloads: dict[str, bytes] = {}
    bindings: dict[str, dict[str, Any]] = {}
    for name, relative in sorted(protocol.PROTOCOL_SOURCE_PATHS.items()):
        payload = _read_repository_file(relative)
        receipt = _receipt(relative, payload)
        if (
            dict(_mapping(registered_sources.get(name), f"$.protocol_sources.{name}"))
            != receipt
        ):
            raise RuntimeError(f"published protocol source receipt mismatch: {name}")
        if _git_blob_bytes(commit, relative) != payload:
            raise RuntimeError(f"published protocol source Git blob mismatch: {name}")
        source_payloads[name] = payload
        bindings[name] = {
            **receipt,
            "tracked_bytes_equal_protocol_merge_commit_blob": True,
        }

    inputs = protocol_builder.protocol_inputs()
    protocol.validate_preregistration(
        preregistration,
        freeze_status="frozen",
        output_absent=True,
        **inputs,
    )
    return {
        "preregistration": preregistration,
        "preregistration_payload": preregistration_payload,
        "protocol_inputs": inputs,
        "source_payloads": source_payloads,
        "source_bindings": bindings,
    }


def _historical_protocol_context(result: Mapping[str, Any]) -> dict[str, Any]:
    """Rebuild protocol evidence from its historical Git commit, not the tree."""

    from scripts import (
        prepare_mm005_browser_research_model_evaluation_generation_failure_investigation_protocol_v1 as protocol_builder,
    )

    candidate_lineage = _mapping(result.get("protocol_lineage"), "$.protocol_lineage")
    if (
        candidate_lineage.get("protocol_merge_commit")
        != result_contract.PROTOCOL_MERGE_COMMIT
    ):
        raise RuntimeError("result protocol merge commit mismatch")
    commit = result_contract.PROTOCOL_MERGE_COMMIT
    _require_commit_ancestor(commit)
    preregistration_payload = _git_blob_bytes(commit, protocol.PREREGISTRATION_PATH)
    preregistration = protocol.parse_strict_json_bytes(
        preregistration_payload, location="$.investigation_protocol"
    )
    expected_preregistration_binding = {
        "path": protocol.PREREGISTRATION_PATH,
        "bytes": len(preregistration_payload),
        "sha256": protocol.sha256_bytes(preregistration_payload),
        "canonical_json": (
            protocol.artifact_json_bytes(preregistration) == preregistration_payload
        ),
        "tracked_bytes_equal_protocol_merge_commit_blob": True,
    }
    if (
        len(preregistration_payload) != result_contract.PROTOCOL_BYTES
        or protocol.sha256_bytes(preregistration_payload)
        != result_contract.PROTOCOL_SHA256
        or dict(
            _mapping(
                candidate_lineage.get("preregistration"),
                "$.protocol_lineage.preregistration",
            )
        )
        != expected_preregistration_binding
        or expected_preregistration_binding["canonical_json"] is not True
    ):
        raise RuntimeError("historical investigation protocol binding mismatch")

    registered_sources = _mapping(
        _mapping(preregistration.get("source_lineage"), "$.source_lineage").get(
            "protocol_sources"
        ),
        "$.source_lineage.protocol_sources",
    )
    candidate_sources = _mapping(
        candidate_lineage.get("protocol_sources"),
        "$.protocol_lineage.protocol_sources",
    )
    if set(registered_sources) != set(protocol.PROTOCOL_SOURCE_PATHS) or set(
        candidate_sources
    ) != set(protocol.PROTOCOL_SOURCE_PATHS):
        raise RuntimeError("historical protocol source closure mismatch")
    source_payloads: dict[str, bytes] = {}
    bindings: dict[str, dict[str, Any]] = {}
    for name, relative in sorted(protocol.PROTOCOL_SOURCE_PATHS.items()):
        payload = _git_blob_bytes(commit, relative)
        receipt = _receipt(relative, payload)
        binding = {
            **receipt,
            "tracked_bytes_equal_protocol_merge_commit_blob": True,
        }
        if (
            dict(
                _mapping(
                    registered_sources.get(name),
                    f"$.source_lineage.protocol_sources.{name}",
                )
            )
            != receipt
            or dict(
                _mapping(
                    candidate_sources.get(name),
                    f"$.protocol_lineage.protocol_sources.{name}",
                )
            )
            != binding
        ):
            raise RuntimeError(f"historical protocol source mismatch: {name}")
        source_payloads[name] = payload
        bindings[name] = binding

    inputs = protocol_builder.protocol_inputs()
    protocol.validate_preregistration(
        preregistration,
        freeze_status="frozen",
        output_absent=True,
        **inputs,
    )
    return {
        "preregistration": preregistration,
        "preregistration_payload": preregistration_payload,
        "protocol_inputs": inputs,
        "source_payloads": source_payloads,
        "source_bindings": bindings,
    }


def _historical_implementation_source_context(
    result: Mapping[str, Any],
) -> dict[str, Any]:
    implementation = _mapping(
        result.get("implementation_lineage"), "$.implementation_lineage"
    )
    freeze_commit = implementation.get("implementation_freeze_commit")
    if not isinstance(freeze_commit, str):
        raise RuntimeError("implementation freeze commit is invalid")
    _validate_git_commit(freeze_commit)
    _require_commit_ancestor(freeze_commit)
    candidate_sources = _mapping(
        implementation.get("implementation_sources"),
        "$.implementation_lineage.implementation_sources",
    )
    if implementation.get(
        "formal_execution_started_from_aligned_merged_master"
    ) is not True or set(candidate_sources) != set(
        result_contract.IMPLEMENTATION_SOURCE_PATHS
    ):
        raise RuntimeError("historical implementation lineage mismatch")
    bindings: dict[str, dict[str, Any]] = {}
    for name, relative in sorted(result_contract.IMPLEMENTATION_SOURCE_PATHS.items()):
        payload = _git_blob_bytes(freeze_commit, relative)
        binding = {
            **_receipt(relative, payload),
            "tracked_bytes_equal_implementation_freeze_commit_blob": True,
        }
        if (
            dict(
                _mapping(
                    candidate_sources.get(name),
                    f"$.implementation_lineage.implementation_sources.{name}",
                )
            )
            != binding
        ):
            raise RuntimeError(f"historical implementation source mismatch: {name}")
        bindings[name] = binding
    return {"freeze_commit": freeze_commit, "source_bindings": bindings}


def _implementation_source_context(commit: str) -> dict[str, Any]:
    _validate_git_commit(commit)
    _require_commit_ancestor(commit)
    bindings: dict[str, dict[str, Any]] = {}
    for name, relative in sorted(result_contract.IMPLEMENTATION_SOURCE_PATHS.items()):
        payload = _read_repository_file(relative)
        if _git_blob_bytes(commit, relative) != payload:
            raise RuntimeError(f"implementation source Git blob mismatch: {name}")
        bindings[name] = {
            **_receipt(relative, payload),
            "tracked_bytes_equal_implementation_freeze_commit_blob": True,
        }
    return {"freeze_commit": commit, "source_bindings": bindings}


def _build_result(
    *,
    protocol_context: Mapping[str, Any],
    implementation_context: Mapping[str, Any],
    executed_at_utc: str,
) -> dict[str, Any]:
    return result_contract.build_static_investigation_result(
        **_result_inputs(
            protocol_context=protocol_context,
            implementation_context=implementation_context,
            executed_at_utc=executed_at_utc,
        )
    )


def _result_inputs(
    *,
    protocol_context: Mapping[str, Any],
    implementation_context: Mapping[str, Any],
    executed_at_utc: str,
) -> dict[str, Any]:
    inputs = _mapping(protocol_context.get("protocol_inputs"), "$.protocol_inputs")
    records = inputs.get("records")
    artifact_payloads = inputs.get("artifact_payloads")
    v2_preregistration = inputs.get("v2_preregistration")
    if not isinstance(records, Sequence) or isinstance(
        records, (str, bytes, bytearray)
    ):
        raise RuntimeError("protocol records are not an array")
    if not isinstance(artifact_payloads, Mapping) or not isinstance(
        v2_preregistration, Mapping
    ):
        raise RuntimeError("protocol static inputs are invalid")
    source_payloads = _mapping(
        protocol_context.get("source_payloads"), "$.source_payloads"
    )
    control_flow_payloads = {
        name: _bytes_value(source_payloads.get(name), f"$.source_payloads.{name}")
        for name in ("v2_runner", "shared_generation_helper")
    }
    return {
        "preregistration": _mapping(
            protocol_context.get("preregistration"), "$.preregistration"
        ),
        "preregistration_payload": _bytes_value(
            protocol_context.get("preregistration_payload"),
            "$.preregistration_payload",
        ),
        "implementation_freeze_commit": str(
            implementation_context.get("freeze_commit")
        ),
        "executed_at_utc": _validate_timestamp(executed_at_utc),
        "protocol_source_bindings": _mapping(
            protocol_context.get("source_bindings"), "$.protocol_source_bindings"
        ),
        "implementation_source_bindings": _mapping(
            implementation_context.get("source_bindings"),
            "$.implementation_source_bindings",
        ),
        "records": records,
        "artifact_payloads": artifact_payloads,
        "v2_preregistration": v2_preregistration,
        "control_flow_source_payloads": control_flow_payloads,
    }


def _require_aligned_merged_master() -> str:
    branch = _git_text("symbolic-ref", "--quiet", "--short", "HEAD")
    if branch != "master":
        raise RuntimeError("formal investigation must start from master")
    head = _git_text("rev-parse", "HEAD")
    remote = _git_text("rev-parse", "refs/remotes/origin/master")
    if head != remote:
        raise RuntimeError("master and origin/master are not aligned")
    status = _git_process("status", "--porcelain=v1", "--untracked-files=all")
    if status.returncode != 0 or status.stdout:
        raise RuntimeError("formal investigation requires a clean worktree")
    return head


def _require_commit_ancestor(commit: str) -> None:
    _validate_git_commit(commit)
    completed = _git_process("merge-base", "--is-ancestor", commit, "HEAD")
    if completed.returncode != 0:
        raise RuntimeError(f"required commit is not an ancestor of HEAD: {commit}")


def _require_historical_implementation_introduction_commit(
    freeze_commit: str,
) -> None:
    _validate_git_commit(freeze_commit)
    if set(result_contract.IMPLEMENTATION_SOURCE_PATHS.values()) != set(
        _HISTORICAL_IMPLEMENTATION_SOURCE_PATHS
    ):
        raise RuntimeError("historical implementation source closure mismatch")
    introductions: set[str] = set()
    for relative in _HISTORICAL_IMPLEMENTATION_SOURCE_PATHS:
        completed = _git_process(
            "log",
            _HISTORICAL_TRUSTED_MAINLINE_REF,
            "--first-parent",
            "--reverse",
            "--format=%H",
            "--diff-filter=A",
            "--no-renames",
            "--",
            relative,
        )
        try:
            commits = completed.stdout.decode("ascii").splitlines()
        except UnicodeDecodeError as exc:
            raise RuntimeError(
                "historical implementation introduction is invalid"
            ) from exc
        if (
            completed.returncode != 0
            or not commits
            or any(_GIT_COMMIT_PATTERN.fullmatch(commit) is None for commit in commits)
        ):
            raise RuntimeError("historical implementation introduction is invalid")
        introductions.add(commits[0])
    if introductions != {freeze_commit}:
        raise RuntimeError("historical implementation freeze commit is not trusted")


def _require_historical_implementation_slice(freeze_commit: str) -> None:
    _validate_git_commit(freeze_commit)
    completed = _git_process(
        "diff",
        "--name-only",
        "--no-renames",
        "-z",
        _HISTORICAL_PROTOCOL_MERGE_COMMIT,
        freeze_commit,
        "--",
    )
    if completed.returncode != 0 or not completed.stdout.endswith(b"\0"):
        raise RuntimeError("historical implementation slice is invalid")
    try:
        paths = [
            value.decode("utf-8")
            for value in completed.stdout.removesuffix(b"\0").split(b"\0")
        ]
    except UnicodeDecodeError as exc:
        raise RuntimeError("historical implementation slice is invalid") from exc
    if len(paths) != len(set(paths)) or set(paths) != set(
        _HISTORICAL_IMPLEMENTATION_SLICE_PATHS
    ):
        raise RuntimeError("historical implementation slice is not trusted")


def _require_historical_protocol_bootstrap(
    result: Mapping[str, Any],
    freeze_commit: str,
) -> None:
    """Bind every historical Python dependency before executing that checkout."""

    lineage = _mapping(result.get("protocol_lineage"), "$.protocol_lineage")
    preregistration = _mapping(
        lineage.get("preregistration"), "$.protocol_lineage.preregistration"
    )
    candidate_sources = _mapping(
        lineage.get("protocol_sources"), "$.protocol_lineage.protocol_sources"
    )
    published_protocol = _git_blob_bytes(
        _HISTORICAL_PROTOCOL_MERGE_COMMIT, _HISTORICAL_PROTOCOL_PATH
    )
    freeze_protocol = _git_blob_bytes(freeze_commit, _HISTORICAL_PROTOCOL_PATH)
    expected_preregistration = {
        "path": _HISTORICAL_PROTOCOL_PATH,
        "bytes": len(published_protocol),
        "sha256": _receipt(_HISTORICAL_PROTOCOL_PATH, published_protocol)["sha256"],
        "canonical_json": True,
        "tracked_bytes_equal_protocol_merge_commit_blob": True,
    }
    if (
        lineage.get("protocol_merge_commit") != _HISTORICAL_PROTOCOL_MERGE_COMMIT
        or len(published_protocol) != _HISTORICAL_PROTOCOL_BYTES
        or expected_preregistration["sha256"] != _HISTORICAL_PROTOCOL_SHA256
        or freeze_protocol != published_protocol
        or dict(preregistration) != expected_preregistration
        or set(candidate_sources) != set(_HISTORICAL_PROTOCOL_SOURCE_PATHS)
    ):
        raise RuntimeError("historical protocol bootstrap binding mismatch")

    for name, relative in sorted(_HISTORICAL_PROTOCOL_SOURCE_PATHS.items()):
        published_payload = _git_blob_bytes(_HISTORICAL_PROTOCOL_MERGE_COMMIT, relative)
        freeze_payload = _git_blob_bytes(freeze_commit, relative)
        expected_binding = {
            **_receipt(relative, published_payload),
            "tracked_bytes_equal_protocol_merge_commit_blob": True,
        }
        if (
            freeze_payload != published_payload
            or dict(
                _mapping(
                    candidate_sources.get(name),
                    f"$.protocol_lineage.protocol_sources.{name}",
                )
            )
            != expected_binding
        ):
            raise RuntimeError(f"historical protocol bootstrap source mismatch: {name}")


def _git_blob_bytes(commit: str, relative: str) -> bytes:
    _validate_git_commit(commit)
    _validate_repository_relative_path(relative)
    completed = _git_process("cat-file", "blob", f"{commit}:{relative}")
    if completed.returncode != 0 or len(completed.stdout) > MAX_BOUND_FILE_BYTES:
        raise RuntimeError(f"unable to read Git blob: {relative}")
    return completed.stdout


def _git_text(*args: str) -> str:
    completed = _git_process(*args)
    if completed.returncode != 0:
        raise RuntimeError(f"Git command failed: {' '.join(args)}")
    try:
        return completed.stdout.decode("utf-8").strip()
    except UnicodeDecodeError as exc:
        raise RuntimeError("Git output is not UTF-8") from exc


def _git_process(*args: str) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(
            ["git", *args],
            cwd=ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            env=_historical_git_environment(),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError(f"unable to run Git command: {' '.join(args)}") from exc


def _read_repository_file(relative: str) -> bytes:
    _validate_repository_relative_path(relative)
    return _read_regular_file_once(ROOT / PurePosixPath(relative))


def _validate_repository_relative_path(relative: str) -> None:
    path = PurePosixPath(relative)
    if (
        not relative
        or "\\" in relative
        or path.is_absolute()
        or path.as_posix() != relative
        or ".." in path.parts
        or "." in path.parts
    ):
        raise RuntimeError("unsafe repository-relative path")


def _read_regular_file_once(path: Path) -> bytes:
    absolute = Path(os.path.abspath(path))
    try:
        before = absolute.lstat()
        resolved = absolute.resolve(strict=True)
    except OSError as exc:
        raise RuntimeError(f"unable to inspect bound file: {path}") from exc
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    if (
        resolved != absolute
        or absolute.is_symlink()
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or before.st_size > MAX_BOUND_FILE_BYTES
        or bool(getattr(before, "st_file_attributes", 0) & reparse_flag)
    ):
        raise RuntimeError(f"unsafe bound file: {path}")
    try:
        with resolved.open("rb") as handle:
            payload = handle.read(MAX_BOUND_FILE_BYTES + 1)
            after_handle = os.fstat(handle.fileno())
        after = resolved.stat()
    except OSError as exc:
        raise RuntimeError(f"unable to read bound file: {path}") from exc
    signatures = {
        (item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns, item.st_nlink)
        for item in (before, after_handle, after)
    }
    if len(payload) > MAX_BOUND_FILE_BYTES or len(signatures) != 1:
        raise RuntimeError(f"bound file changed while reading: {path}")
    return payload


def _write_exclusive_result(path: Path, payload: bytes) -> None:
    expected = Path(os.path.abspath(ROOT / result_contract.RESULT_PATH))
    candidate = Path(os.path.abspath(path))
    if candidate != expected or os.path.lexists(candidate):
        raise FileExistsError(candidate)
    parent = candidate.parent
    try:
        parent_stat = parent.lstat()
        parent_resolved = parent.resolve(strict=True)
    except OSError as exc:
        raise RuntimeError("unable to inspect result parent") from exc
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    if (
        parent_resolved != parent
        or parent.is_symlink()
        or not stat.S_ISDIR(parent_stat.st_mode)
        or bool(getattr(parent_stat, "st_file_attributes", 0) & reparse_flag)
    ):
        raise RuntimeError("unsafe result parent")
    with candidate.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def _summary(result: Mapping[str, Any], *, checked: bool) -> dict[str, Any]:
    decision = _mapping(result.get("decision"), "$.decision")
    claims = _mapping(result.get("claims"), "$.claims")
    action = _mapping(result.get("locked_next_action"), "$.locked_next_action")
    protocol_lineage = _mapping(result.get("protocol_lineage"), "$.protocol_lineage")
    preregistration = _mapping(
        protocol_lineage.get("preregistration"), "$.protocol_lineage.preregistration"
    )
    implementation_lineage = _mapping(
        result.get("implementation_lineage"), "$.implementation_lineage"
    )
    execution = _mapping(result.get("execution"), "$.execution")
    return {
        "checked": checked,
        "diagnostic_records": 1
        + len(protocol.COMPLETED_PREFIX_CONTROL_IDS)
        + len(protocol.SAME_SHAPE_CONTROL_IDS),
        "gate_id": result.get("gate_id"),
        "implementation_freeze_commit": implementation_lineage.get(
            "implementation_freeze_commit"
        ),
        "model_free": execution.get("model_free"),
        "selected_outcome": decision.get("selected_outcome"),
        "static_investigation_complete": claims.get("static_investigation_complete"),
        "runtime_root_cause_unresolved": decision.get("runtime_root_cause_unresolved"),
        "next_gate": action.get("next_gate_id"),
        "protocol_merge_commit": protocol_lineage.get("protocol_merge_commit"),
        "protocol_sha256": preregistration.get("sha256"),
        "report_digest": result.get("report_digest"),
        "runtime_eligible": False,
        "target_record": protocol.TARGET_RECORD_ID,
        "valid": True,
    }


def _utc_now() -> str:
    return (
        datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
    )


def _validate_timestamp(value: str) -> str:
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value) is None:
        raise RuntimeError("invalid UTC timestamp")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
    except ValueError as exc:
        raise RuntimeError("invalid UTC timestamp") from exc
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise RuntimeError("non-canonical UTC timestamp")
    return value


def _validate_git_commit(value: str) -> None:
    if _GIT_COMMIT_PATTERN.fullmatch(value) is None:
        raise RuntimeError("unsafe Git commit")


def _receipt(path: str, payload: bytes) -> dict[str, Any]:
    return {
        "path": path,
        "bytes": len(payload),
        "sha256": protocol.sha256_bytes(payload),
    }


def _mapping(value: object, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise RuntimeError(f"expected object: {location}")
    return value


def _bytes_value(value: object, location: str) -> bytes:
    if not isinstance(value, bytes):
        raise RuntimeError(f"expected bytes: {location}")
    return value


if __name__ == "__main__":
    raise SystemExit(main())
