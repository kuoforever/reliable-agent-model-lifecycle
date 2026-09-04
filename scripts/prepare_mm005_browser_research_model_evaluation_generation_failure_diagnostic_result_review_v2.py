"""Build or check the safe MM-005 diagnostic-v2 terminal result review."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(ROOT))

from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_model_evaluation_generation_failure_diagnostic_protocol_v2 as protocol,
)
from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_model_evaluation_generation_failure_diagnostic_result_review_v2 as contract,
)
from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_model_evaluation_generation_failure_diagnostic_result_v2 as result_contract,
)
from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_model_evaluation_recovery_io as recovery_io,
)
from scripts import (  # noqa: E402
    run_mm005_browser_research_model_evaluation_generation_failure_diagnostic_v2 as runner,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    review, snapshot = _capture_review()
    payload = contract.artifact_json_bytes(review)
    output_path = ROOT / contract.REVIEW_PATH
    if args.check:
        _validate_persisted_review(output_path, payload, stale_is_exit=True)
        _revalidate_inputs(snapshot)
        _validate_persisted_review(output_path, payload)
        _revalidate_inputs(snapshot)
    else:
        if os.path.lexists(output_path):
            raise FileExistsError(output_path)
        _revalidate_inputs(snapshot)
        with output_path.open("xb") as handle:
            written = handle.write(payload)
            if written != len(payload):
                raise RuntimeError("short diagnostic-v2 result-review write")
            handle.flush()
            os.fsync(handle.fileno())
        _validate_persisted_review(output_path, payload)
        _revalidate_inputs(snapshot)

    summary = _summary(review)
    print(json.dumps(summary, sort_keys=True, separators=(",", ":")))
    return 0


def build_review() -> dict[str, Any]:
    review, snapshot = _capture_review()
    _revalidate_inputs(snapshot)
    return review


def validate_local_runtime_and_build_review() -> tuple[dict[str, Any], dict[str, Any]]:
    """Authenticate the ignored runtime terminal and return the safe review."""

    review, snapshot = _capture_review()
    _revalidate_inputs(snapshot)
    return review, _runtime_summary(snapshot)


def _capture_review() -> tuple[dict[str, Any], dict[str, Any]]:
    topology = runner._output_topology()  # noqa: SLF001
    runner._validate_output_topology(topology)  # noqa: SLF001
    _require_terminal_topology(topology)

    authority_context = runner._optional_execution_authority_context(  # noqa: SLF001
        allow_runtime_state=True
    )
    if authority_context is None or authority_context.get("published") is not True:
        raise RuntimeError("published diagnostic-v2 authority is required")
    claimed = runner._claimed_execution_snapshot(authority_context)  # noqa: SLF001
    if (
        claimed.get("terminal_kind") != "failure"
        or claimed.get("terminal_artifact_valid") is not True
        or claimed.get("terminal_reconciliation_required") is not False
        or claimed.get("discarded_tail_receipt") is not None
    ):
        raise RuntimeError("diagnostic-v2 terminal is not a complete failure")

    authority_payload = _read_repository_file(
        result_contract.EXECUTION_AUTHORITY_PATH, max_bytes=64 * 1024
    )
    preregistration_payload = _read_repository_file(
        protocol.PREREGISTRATION_PATH, max_bytes=128 * 1024
    )
    owner_payload = _bytes(claimed.get("owner_payload"), "$.owner_payload")
    progress_payload = _bytes(claimed.get("progress_payload"), "$.progress_payload")
    failure_payload = _bytes(claimed.get("terminal_payload"), "$.failure_payload")
    lifecycle_lease_payload = _read_repository_file(
        protocol.LIFECYCLE_LEASE_PATH, max_bytes=64 * 1024
    )
    implementation_context = _mapping(
        claimed.get("implementation_context"), "$.implementation_context"
    )

    runtime_summary = contract.validate_runtime_terminal(
        authority_payload=authority_payload,
        preregistration_payload=preregistration_payload,
        attempt_owner_payload=owner_payload,
        progress_payload=progress_payload,
        failure_payload=failure_payload,
        lifecycle_lease_payload=lifecycle_lease_payload,
        implementation_context=implementation_context,
    )
    _validate_authority_introduction(authority_payload)
    review = contract.build_result_review(authority_payload=authority_payload)
    return review, {
        "topology": dict(topology),
        "authority_payload": authority_payload,
        "preregistration_payload": preregistration_payload,
        "attempt_owner_payload": owner_payload,
        "progress_payload": progress_payload,
        "failure_payload": failure_payload,
        "lifecycle_lease_payload": lifecycle_lease_payload,
        "runtime_summary": runtime_summary,
    }


def _revalidate_inputs(snapshot: Mapping[str, Any]) -> None:
    _, current = _capture_review()
    for name in (
        "topology",
        "authority_payload",
        "preregistration_payload",
        "attempt_owner_payload",
        "progress_payload",
        "failure_payload",
        "lifecycle_lease_payload",
        "runtime_summary",
    ):
        if current.get(name) != snapshot.get(name):
            raise RuntimeError(f"diagnostic-v2 review input changed: {name}")


def _validate_persisted_review(
    output_path: Path, payload: bytes, *, stale_is_exit: bool = False
) -> None:
    persisted = _read_regular_file(output_path, max_bytes=max(len(payload), 1))
    if (
        persisted != payload
        or contract.sha256_bytes(persisted) != contract.sha256_bytes(payload)
    ):
        if stale_is_exit:
            raise SystemExit("MM-005 diagnostic-v2 result review is stale")
        raise RuntimeError("diagnostic-v2 result review changed during persistence check")


def _validate_authority_introduction(authority_payload: bytes) -> None:
    frozen = runner._git_blob_bytes(  # noqa: SLF001
        contract.AUTHORITY_INTRODUCTION_COMMIT,
        result_contract.EXECUTION_AUTHORITY_PATH,
    )
    introductions = runner._git_process(  # noqa: SLF001
        "log",
        "--first-parent",
        "--diff-filter=A",
        "--format=%H",
        "--",
        result_contract.EXECUTION_AUTHORITY_PATH,
    )
    parents = runner._git_process(  # noqa: SLF001
        "show", "-s", "--format=%P", contract.AUTHORITY_INTRODUCTION_COMMIT
    )
    if frozen != authority_payload or introductions.returncode != 0 or parents.returncode != 0:
        raise RuntimeError("unable to validate diagnostic-v2 authority lineage")
    try:
        introduction_values = introductions.stdout.decode("ascii").splitlines()
        parent_values = parents.stdout.decode("ascii").split()
    except UnicodeDecodeError as exc:
        raise RuntimeError("non-ASCII diagnostic-v2 authority lineage") from exc
    if introduction_values != [contract.AUTHORITY_INTRODUCTION_COMMIT]:
        raise RuntimeError("diagnostic-v2 authority introduction is not unique")
    if parent_values != [contract.AUTHORITY_PARENT_COMMIT]:
        raise RuntimeError("diagnostic-v2 authority parent differs")


def _require_terminal_topology(topology: Mapping[str, bool]) -> None:
    required = {
        "execution_authority",
        "output_parent",
        "output_root",
        "attempt_owner",
        "progress",
        "failure",
        "lifecycle_lease_root",
        "lifecycle_lease",
    }
    forbidden = {"success_result", "reserved_sibling_staging"}
    if any(topology.get(name) is not True for name in required) or any(
        topology.get(name) is not False for name in forbidden
    ):
        raise RuntimeError("diagnostic-v2 result-review topology mismatch")


def _runtime_summary(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    return dict(_mapping(snapshot.get("runtime_summary"), "$.runtime_summary"))


def _summary(review: Mapping[str, Any]) -> dict[str, Any]:
    claims = _mapping(review.get("claims"), "$.review.claims")
    decision = _mapping(review.get("decision"), "$.review.decision")
    action = _mapping(review.get("locked_next_action"), "$.review.locked_next_action")
    return {
        "classification": review["classification"],
        "diagnostic_attempt_consumed": claims["diagnostic_attempt_consumed"],
        "diagnostic_executed": claims["diagnostic_executed"],
        "formal_invocation_budget_remaining": review["invocation"][
            "formal_invocation_budget_remaining"
        ],
        "formal_measurement_complete": claims["formal_measurement_complete"],
        "gate_id": review["gate_id"],
        "model_evaluated": claims["model_evaluated"],
        "next_gate": action["next_gate_id"],
        "result_review_gate_passed": decision["result_review_gate_passed"],
        "retry_authorized": review["invocation"]["retry_authorized"],
        "root_cause_established": claims["runtime_root_cause_established"],
        "valid": True,
    }


def _read_repository_file(relative: str, *, max_bytes: int) -> bytes:
    return _read_regular_file(ROOT / relative, max_bytes=max_bytes)


def _read_regular_file(path: Path, *, max_bytes: int) -> bytes:
    return cast(bytes, recovery_io.read_regular_file(path, max_bytes=max_bytes))


def _bytes(value: object, location: str) -> bytes:
    if type(value) is not bytes:
        raise RuntimeError(f"bytes required at {location}")
    return value


def _mapping(value: object, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise RuntimeError(f"object required at {location}")
    return value


if __name__ == "__main__":
    raise SystemExit(main())
