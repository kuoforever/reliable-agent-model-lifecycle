"""Build or check the model-free MM-005 diagnostic invocation closeout."""

from __future__ import annotations

import argparse
import ast
import os
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(ROOT))

from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_model_evaluation_generation_failure_diagnostic_invocation_closeout as contract,
)
from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_model_evaluation_generation_failure_diagnostic_result as result_contract,
)
from scripts import (  # noqa: E402
    prepare_mm005_browser_research_model_evaluation_generation_failure_diagnostic_execution_authority_v1 as authority_builder,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    closeout, snapshot = _capture_closeout()
    payload = contract.artifact_json_bytes(closeout)
    output_path = ROOT / contract.CLOSEOUT_PATH
    if args.check:
        if _read_regular_file(output_path) != payload:
            raise SystemExit("MM-005 diagnostic invocation closeout is stale")
        _revalidate_inputs(snapshot)
        if _read_regular_file(output_path) != payload:
            raise RuntimeError("diagnostic invocation closeout changed during check")
    else:
        if os.path.lexists(output_path):
            raise FileExistsError(output_path)
        _revalidate_inputs(snapshot)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("xb") as handle:
            written = handle.write(payload)
            if written != len(payload):
                raise RuntimeError("short invocation closeout write")
            handle.flush()
            os.fsync(handle.fileno())

    print(
        contract.artifact_json_bytes(
            {
                "classification": contract.CLASSIFICATION,
                "diagnostic_attempt_consumed": False,
                "diagnostic_executed": False,
                "formal_invocation_budget_remaining": 0,
                "formal_invocation_budget_spent": True,
                "formal_outcome_selected": False,
                "gate_id": contract.GATE_ID,
                "next_gate": contract.NEXT_GATE_ID,
                "retry_authorized": False,
                "valid": True,
            }
        )
        .decode("utf-8")
        .rstrip()
    )
    return 0


def build_closeout() -> dict[str, Any]:
    closeout, snapshot = _capture_closeout()
    _revalidate_inputs(snapshot)
    return closeout


def _capture_closeout() -> tuple[dict[str, Any], dict[str, bytes]]:
    authority_payload = _read_repository_file(result_contract.EXECUTION_AUTHORITY_PATH)
    authority_blob = authority_builder._git_blob_bytes(  # noqa: SLF001
        contract.AUTHORITY_INTRODUCTION_COMMIT,
        result_contract.EXECUTION_AUTHORITY_PATH,
    )
    if authority_payload != authority_blob:
        raise RuntimeError("execution authority differs from introduction commit")

    runner_payload = _read_repository_file(contract.RUNNER_PATH)
    runner_blob = authority_builder._git_blob_bytes(  # noqa: SLF001
        contract.AUTHORITY_PARENT_COMMIT, contract.RUNNER_PATH
    )
    if runner_payload != runner_blob:
        raise RuntimeError("diagnostic v1 runner changed after implementation freeze")

    recovery_io_payload = _read_repository_file(contract.RECOVERY_IO_PATH)
    recovery_io_blob = authority_builder._git_blob_bytes(  # noqa: SLF001
        contract.AUTHORITY_PARENT_COMMIT, contract.RECOVERY_IO_PATH
    )
    if recovery_io_payload != recovery_io_blob:
        raise RuntimeError("recovery I/O changed after implementation freeze")

    _validate_authority_introduction()
    _validate_preclaim_defect(runner_payload, recovery_io_payload)
    closeout = contract.build_invocation_closeout(
        authority_payload=authority_payload,
        runner_payload=runner_payload,
        recovery_io_payload=recovery_io_payload,
    )
    return closeout, {
        "authority_payload": authority_payload,
        "runner_payload": runner_payload,
        "recovery_io_payload": recovery_io_payload,
    }


def _revalidate_inputs(snapshot: Mapping[str, bytes]) -> None:
    for name, relative in (
        ("authority_payload", result_contract.EXECUTION_AUTHORITY_PATH),
        ("runner_payload", contract.RUNNER_PATH),
        ("recovery_io_payload", contract.RECOVERY_IO_PATH),
    ):
        if _read_repository_file(relative) != snapshot.get(name):
            raise RuntimeError(f"{name} changed during closeout construction")
    _validate_authority_introduction()
    _validate_preclaim_defect(
        snapshot["runner_payload"], snapshot["recovery_io_payload"]
    )


def _validate_authority_introduction() -> None:
    introductions = authority_builder._git_process(  # noqa: SLF001
        "log",
        "--first-parent",
        "--diff-filter=A",
        "--format=%H",
        "--",
        result_contract.EXECUTION_AUTHORITY_PATH,
    )
    parents = authority_builder._git_process(  # noqa: SLF001
        "show", "-s", "--format=%P", contract.AUTHORITY_INTRODUCTION_COMMIT
    )
    if introductions.returncode != 0 or parents.returncode != 0:
        raise RuntimeError("unable to validate authority introduction")
    try:
        introduction_values = introductions.stdout.decode("ascii").splitlines()
        parent_values = parents.stdout.decode("ascii").split()
    except UnicodeDecodeError as exc:
        raise RuntimeError("non-ASCII authority lineage") from exc
    if introduction_values != [contract.AUTHORITY_INTRODUCTION_COMMIT]:
        raise RuntimeError("authority artifact introduction is not unique")
    if parent_values != [contract.AUTHORITY_PARENT_COMMIT]:
        raise RuntimeError("authority introduction parent differs")


def _validate_preclaim_defect(
    runner_payload: bytes, recovery_io_payload: bytes
) -> None:
    try:
        runner_source = runner_payload.decode("utf-8")
        recovery_source = recovery_io_payload.decode("utf-8")
        tree = ast.parse(runner_source, filename=contract.RUNNER_PATH)
    except (UnicodeDecodeError, SyntaxError) as exc:
        raise RuntimeError("invalid frozen diagnostic source") from exc
    functions = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "_execute_authorized_diagnostic"
    ]
    if len(functions) != 1:
        raise RuntimeError("diagnostic execution function differs")
    function_source = ast.get_source_segment(runner_source, functions[0])
    if function_source is None:
        raise RuntimeError("unable to isolate diagnostic execution function")

    guard = "output_parent_guard = recovery_io.DirectoryTreeGuard("
    lifecycle = "recovery_io.ensure_lock_directory("
    claim = "_claim_output("
    terminal_handler = "except BaseException as exc:"
    if (
        guard not in function_source
        or lifecycle not in function_source
        or claim not in function_source
        or terminal_handler not in function_source
        or "_ensure_output_parent(" in function_source
        or not (
            function_source.index(guard)
            < function_source.index(lifecycle)
            < function_source.index(claim)
            < function_source.index(terminal_handler)
        )
    ):
        raise RuntimeError("frozen pre-claim output-parent defect boundary differs")
    if (
        'raise RecoveryIOError(f"missing {label}")' not in recovery_source
        or "class DirectoryTreeGuard:" not in recovery_source
        or '_directory_path_identity(current, "guarded directory")'
        not in recovery_source
    ):
        raise RuntimeError("directory guard missing-target behavior differs")


def _read_repository_file(relative: str) -> bytes:
    path = ROOT / relative
    return _read_regular_file(path)


def _read_regular_file(path: Path) -> bytes:
    if not path.is_file() or path.is_symlink():
        raise RuntimeError(f"unsafe repository file: {path.name}")
    return path.read_bytes()


if __name__ == "__main__":
    raise SystemExit(main())
