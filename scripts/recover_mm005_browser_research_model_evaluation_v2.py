"""Model-free terminal recovery for an interrupted MM-005 Browser v2 attempt."""

from __future__ import annotations

import argparse
import json
import os
import stat
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any

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
    prepare_mm005_browser_research_model_evaluation_v2 as protocol_builder,
)

MAX_JSON_BYTES = 64 * 1024 * 1024
ALLOWED_OUTPUT_NAMES = {
    "attempt-owner.json",
    "progress.json",
    "evaluation-candidate.json",
    "predictions.json",
    "evidence.json",
    "failure.json",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol-freeze-commit", required=True)
    parser.add_argument("--attempt-id", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = recover_interrupted_attempt(
        protocol_freeze_commit=str(args.protocol_freeze_commit),
        attempt_id=str(args.attempt_id),
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


def recover_interrupted_attempt(
    *, protocol_freeze_commit: str, attempt_id: str
) -> dict[str, Any]:
    """Finalize or validate one consumed attempt without model/GPU/network use."""

    _validate_commit(protocol_freeze_commit)
    _validate_attempt_id(attempt_id)
    _validate_aligned_freeze_commit(protocol_freeze_commit)
    output_dir = ROOT / contract.RUN_OUTPUT_ROOT
    _validate_output_tree(output_dir)
    lifecycle_path = ROOT / contract.LIFECYCLE_LEASE_PATH
    with recovery_io.ProgressLease(lifecycle_path) as lifecycle:
        return _recover_interrupted_attempt_locked(
            protocol_freeze_commit=protocol_freeze_commit,
            attempt_id=attempt_id,
            lifecycle=lifecycle,
        )


def _recover_interrupted_attempt_locked(
    *,
    protocol_freeze_commit: str,
    attempt_id: str,
    lifecycle: recovery_io.ProgressLease,
) -> dict[str, Any]:
    """Recover only after the executor-wide lifecycle lease is held."""

    output_dir = ROOT / contract.RUN_OUTPUT_ROOT
    _validate_output_tree(output_dir)
    recovery_io.validate_lock_file(
        ROOT / contract.LIFECYCLE_LEASE_PATH,
        contract.LIFECYCLE_LEASE_MARKER,
    )
    lifecycle.verify()
    output_guard = recovery_io.DirectoryTreeGuard(ROOT, output_dir)

    protocol_inputs = protocol_builder.protocol_inputs(freeze_output_absent=True)
    preregistration_payload = recovery_io.read_regular_file(
        ROOT / contract.PREREGISTRATION_PATH, max_bytes=MAX_JSON_BYTES
    )
    preregistration = contract.parse_strict_json_bytes(
        preregistration_payload, location="$.preregistration"
    )
    contract.validate_preregistration(preregistration, **protocol_inputs)
    owner_payload = recovery_io.read_regular_file(
        ROOT / contract.ATTEMPT_OWNER_PATH, max_bytes=MAX_JSON_BYTES
    )
    owner = contract.parse_strict_json_bytes(owner_payload, location="$.attempt_owner")
    checked_owner = contract.validate_attempt_owner(
        owner,
        protocol_freeze_commit=protocol_freeze_commit,
        preregistration_payload=preregistration_payload,
    )
    if checked_owner.get("attempt_id") != attempt_id:
        raise RuntimeError("recovery attempt ID does not match durable owner")

    execution_inputs = protocol_builder.execution_inputs()
    records = _object_sequence(execution_inputs["records"], "$.records")
    dataset_payloads = _bytes_mapping(
        execution_inputs["artifact_payloads"], "$.artifact_payloads"
    )

    with recovery_io.ProgressLease(ROOT / contract.PROGRESS_PATH) as journal:
        lifecycle.verify()
        output_guard.verify()
        raw_progress = journal.read()
        events, authenticated_prefix, tail_receipt = contract.recover_progress_prefix(
            raw_progress,
            protocol_freeze_commit=protocol_freeze_commit,
            preregistration_payload=preregistration_payload,
            attempt_owner_payload=owner_payload,
        )
        if events[-1].get("event") in contract.TERMINAL_EVENTS and tail_receipt:
            raise RuntimeError("terminal progress contains an unexpected torn tail")
        if authenticated_prefix != raw_progress:
            lifecycle.verify()
            output_guard.verify()
            journal.truncate_to_authenticated_prefix(authenticated_prefix)
        last = events[-1]
        lifecycle.verify()
        output_guard.verify()
        evidence_payload = _read_optional(ROOT / contract.EVIDENCE_PATH)
        failure_payload = _read_optional(ROOT / contract.FAILURE_PATH)
        if evidence_payload is not None and failure_payload is not None:
            raise RuntimeError("success and failure terminals both exist")

        candidate_payload, predictions_payload, artifact_states = (
            _observe_nonterminal_artifacts(
                protocol_freeze_commit=protocol_freeze_commit,
                preregistration_payload=preregistration_payload,
                attempt_owner_payload=owner_payload,
                records=records,
                dataset_payloads=dataset_payloads,
            )
        )

        if last.get("event") == "success_terminal_ready":
            if failure_payload is not None:
                raise RuntimeError("failure exists for a success terminal")
            if candidate_payload is None or predictions_payload is None:
                raise RuntimeError("success terminal is missing required artifacts")
            terminal = _mapping(last.get("terminal"), "$.progress.terminal")
            evidence_object = contract.build_evidence(
                protocol_freeze_commit=protocol_freeze_commit,
                preregistration_payload=preregistration_payload,
                attempt_owner_payload=owner_payload,
                progress_payload=journal.read(),
                evaluation_candidate_payload=candidate_payload,
                predictions_payload=predictions_payload,
                records=records,
                artifact_payloads=dataset_payloads,
                captured_at_utc=str(terminal["captured_at_utc"]),
            )
            expected_evidence_payload = contract.artifact_json_bytes(evidence_object)
            lifecycle.verify()
            output_guard.verify()
            recovery_io.write_or_repair_terminal(
                ROOT / contract.EVIDENCE_PATH, expected_evidence_payload
            )
            checked_evidence = _validate_existing_evidence(
                payload=expected_evidence_payload,
                last_event=last,
                protocol_freeze_commit=protocol_freeze_commit,
                preregistration_payload=preregistration_payload,
                attempt_owner_payload=owner_payload,
                progress_payload=journal.read(),
                candidate_payload=candidate_payload,
                predictions_payload=predictions_payload,
                records=records,
                dataset_payloads=dataset_payloads,
            )
            return _success_summary(
                checked_evidence,
                recovered=evidence_payload != expected_evidence_payload,
            )
        if last.get("event") == "failure_terminal_ready":
            if evidence_payload is not None:
                raise RuntimeError("evidence exists for a failure terminal")
            failure_object = contract.build_failure(
                protocol_freeze_commit=protocol_freeze_commit,
                preregistration_payload=preregistration_payload,
                attempt_owner_payload=owner_payload,
                progress_payload=journal.read(),
                artifact_payloads={
                    "evaluation_candidate": candidate_payload,
                    "predictions": predictions_payload,
                },
            )
            expected_failure_payload = contract.artifact_json_bytes(failure_object)
            lifecycle.verify()
            output_guard.verify()
            recovery_io.write_or_repair_terminal(
                ROOT / contract.FAILURE_PATH,
                expected_failure_payload,
            )
            checked_failure = contract.parse_strict_json_bytes(
                expected_failure_payload, location="$.failure"
            )
            contract.validate_failure(
                checked_failure,
                protocol_freeze_commit=protocol_freeze_commit,
                preregistration_payload=preregistration_payload,
                attempt_owner_payload=owner_payload,
                progress_payload=journal.read(),
                artifact_payloads={
                    "evaluation_candidate": candidate_payload,
                    "predictions": predictions_payload,
                },
            )
            return _failure_summary(
                checked_failure,
                recovered=failure_payload != expected_failure_payload,
            )

        if evidence_payload is not None or failure_payload is not None:
            raise RuntimeError(
                "terminal artifact exists before terminal-ready progress"
            )

        interrupted_after = str(last["event"])
        terminal = contract.terminal_event(
            kind="failure",
            captured_at_utc=_utc_now(),
            stage="external_interruption_recovery",
            exception_type="ExternalControllerInterruption",
            external_controller_interruption=True,
            interrupted_after_event=interrupted_after,
            discarded_progress_tail=tail_receipt,
        )
        failure_event = contract.build_progress_event(
            previous_journal_payload=journal.read(),
            protocol_freeze_commit=protocol_freeze_commit,
            preregistration_payload=preregistration_payload,
            attempt_owner_payload=owner_payload,
            event="failure_terminal_ready",
            counters=_mapping(last["counters"], "$.progress.counters"),
            completed_record_ids=_string_sequence(
                last["completed_record_ids"], "$.progress.completed_record_ids"
            ),
            artifact_states=artifact_states,
            terminal=terminal,
        )
        failure_frame = contract.artifact_json_bytes(failure_event)
        planned_progress = journal.read() + failure_frame
        failure_object = contract.build_failure(
            protocol_freeze_commit=protocol_freeze_commit,
            preregistration_payload=preregistration_payload,
            attempt_owner_payload=owner_payload,
            progress_payload=planned_progress,
            artifact_payloads={
                "evaluation_candidate": candidate_payload,
                "predictions": predictions_payload,
            },
        )
        lifecycle.verify()
        output_guard.verify()
        journal.append(failure_frame)
        lifecycle.verify()
        output_guard.verify()
        recovery_io.write_or_repair_terminal(
            ROOT / contract.FAILURE_PATH,
            contract.artifact_json_bytes(failure_object),
        )
        return _failure_summary(failure_object, recovered=True)


def _validate_existing_evidence(
    *,
    payload: bytes,
    last_event: Mapping[str, Any],
    protocol_freeze_commit: str,
    preregistration_payload: bytes,
    attempt_owner_payload: bytes,
    progress_payload: bytes,
    candidate_payload: bytes | None,
    predictions_payload: bytes | None,
    records: Sequence[Mapping[str, Any]],
    dataset_payloads: Mapping[str, bytes],
) -> dict[str, Any]:
    if (
        last_event.get("event") != "success_terminal_ready"
        or candidate_payload is None
        or predictions_payload is None
    ):
        raise RuntimeError("evidence exists without a success terminal")
    evidence = contract.parse_strict_json_bytes(payload, location="$.evidence")
    contract.validate_evidence(
        evidence,
        protocol_freeze_commit=protocol_freeze_commit,
        preregistration_payload=preregistration_payload,
        attempt_owner_payload=attempt_owner_payload,
        progress_payload=progress_payload,
        evaluation_candidate_payload=candidate_payload,
        predictions_payload=predictions_payload,
        records=records,
        artifact_payloads=dataset_payloads,
    )
    return evidence


def _observe_nonterminal_artifacts(
    *,
    protocol_freeze_commit: str,
    preregistration_payload: bytes,
    attempt_owner_payload: bytes,
    records: Sequence[Mapping[str, Any]],
    dataset_payloads: Mapping[str, bytes],
) -> tuple[bytes | None, bytes | None, dict[str, Any]]:
    states: dict[str, Any] = {"evaluation_candidate": None, "predictions": None}
    candidate_payload = _read_optional(ROOT / contract.EVALUATION_CANDIDATE_PATH)
    predictions_payload = _read_optional(ROOT / contract.PREDICTIONS_PATH)
    candidate_object: dict[str, Any] | None = None
    if candidate_payload is not None:
        state = "observed_unvalidated"
        try:
            candidate_object = contract.parse_strict_json_bytes(
                candidate_payload, location="$.evaluation_candidate"
            )
            contract.validate_evaluation_candidate(
                candidate_object,
                protocol_freeze_commit=protocol_freeze_commit,
                preregistration_payload=preregistration_payload,
                attempt_owner_payload=attempt_owner_payload,
                records=records,
                artifact_payloads=dataset_payloads,
            )
            state = "validated"
        except Exception:
            candidate_object = None
        states["evaluation_candidate"] = contract.artifact_state(
            contract.EVALUATION_CANDIDATE_PATH, candidate_payload, state=state
        )
    if predictions_payload is not None:
        state = "observed_unvalidated"
        try:
            predictions = contract.parse_strict_json_bytes(
                predictions_payload, location="$.predictions"
            )
            if (
                candidate_object is not None
                and predictions == contract.build_predictions(candidate_object)
            ):
                state = "validated"
        except Exception:
            pass
        states["predictions"] = contract.artifact_state(
            contract.PREDICTIONS_PATH, predictions_payload, state=state
        )
    return candidate_payload, predictions_payload, states


def _validate_output_tree(output_dir: Path) -> None:
    if not os.path.lexists(output_dir):
        raise RuntimeError("consumed v2 output directory is absent")
    metadata = output_dir.lstat()
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    if (
        not output_dir.is_dir()
        or output_dir.is_symlink()
        or metadata.st_nlink < 1
        or bool(getattr(metadata, "st_file_attributes", 0) & reparse_flag)
    ):
        raise RuntimeError("unsafe consumed v2 output directory")
    observed = {item.name for item in output_dir.iterdir()}
    if not {"attempt-owner.json", "progress.json"}.issubset(observed):
        raise RuntimeError("consumed v2 output lacks owner/progress genesis")
    if not observed.issubset(ALLOWED_OUTPUT_NAMES):
        raise RuntimeError("consumed v2 output contains unregistered artifacts")


def _validate_aligned_freeze_commit(protocol_freeze_commit: str) -> None:
    branch = _git_text("rev-parse", "--abbrev-ref", "HEAD")
    head = _git_text("rev-parse", "HEAD")
    origin_master = _git_text("rev-parse", "refs/remotes/origin/master")
    if branch != "master" or head != origin_master or head != protocol_freeze_commit:
        raise RuntimeError("model-free recovery requires aligned merged master")
    preregistration_payload = recovery_io.read_regular_file(
        ROOT / contract.PREREGISTRATION_PATH, max_bytes=MAX_JSON_BYTES
    )
    preregistration = contract.parse_strict_json_bytes(
        preregistration_payload, location="$.preregistration"
    )
    receipts = _mapping(preregistration.get("source_receipts"), "$.source_receipts")
    tracked = {
        contract.PREREGISTRATION_PATH: {
            "path": contract.PREREGISTRATION_PATH,
            "bytes": len(preregistration_payload),
            "sha256": contract.sha256_bytes(preregistration_payload),
        },
        **{
            str(_mapping(value, f"$.source_receipts.{name}")["path"]): _mapping(
                value, f"$.source_receipts.{name}"
            )
            for name, value in receipts.items()
        },
    }
    for path, expected in tracked.items():
        payload = _git_blob_bytes(protocol_freeze_commit, path)
        receipt = {
            "path": path,
            "bytes": len(payload),
            "sha256": contract.sha256_bytes(payload),
        }
        if receipt != dict(expected):
            raise RuntimeError("model-free recovery freeze source differs")


def _git_blob_bytes(commit: str, path: str) -> bytes:
    relative = PurePosixPath(path)
    if not path or "\\" in path or relative.is_absolute() or ".." in relative.parts:
        raise RuntimeError("unsafe freeze-commit path")
    try:
        completed = subprocess.run(
            ["git", "cat-file", "blob", f"{commit}:{path}"],
            cwd=ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError("unable to read freeze-commit blob") from exc
    if completed.returncode != 0:
        raise RuntimeError("unable to read freeze-commit blob")
    if len(completed.stdout) > MAX_JSON_BYTES:
        raise RuntimeError("freeze-commit blob exceeds byte limit")
    return completed.stdout


def _read_optional(path: Path) -> bytes | None:
    if not os.path.lexists(path):
        return None
    return recovery_io.read_regular_file(path, max_bytes=MAX_JSON_BYTES)


def _success_summary(evidence: Mapping[str, Any], *, recovered: bool) -> dict[str, Any]:
    return {
        "classification": evidence["classification"],
        "formal_gate_passed": evidence["formal_gate_passed"],
        "next_gate": evidence["next_gate"],
        "terminal": "success",
        "terminal_recovered": recovered,
        "valid": evidence["formal_gate_passed"],
    }


def _failure_summary(failure: Mapping[str, Any], *, recovered: bool) -> dict[str, Any]:
    return {
        "stage": failure["stage"],
        "next_gate": failure["next_gate"],
        "terminal": "failure",
        "terminal_recovered": recovered,
        "valid": True,
    }


def _utc_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _git_text(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode != 0 or completed.stderr:
        raise RuntimeError("unable to validate merged protocol state")
    value = completed.stdout.strip()
    if not value:
        raise RuntimeError("empty merged protocol state")
    return value


def _mapping(value: object, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise RuntimeError(f"expected object at {location}")
    return value


def _object_sequence(value: object, location: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        raise RuntimeError(f"expected array at {location}")
    return [_mapping(item, f"{location}[{index}]") for index, item in enumerate(value)]


def _string_sequence(value: object, location: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise RuntimeError(f"expected string array at {location}")
    return list(value)


def _bytes_mapping(value: object, location: str) -> dict[str, bytes]:
    mapping = _mapping(value, location)
    result: dict[str, bytes] = {}
    for name, payload in mapping.items():
        if not isinstance(payload, bytes):
            raise RuntimeError(f"expected bytes at {location}.{name}")
        result[str(name)] = payload
    return result


def _validate_commit(value: str) -> None:
    if len(value) != 40 or any(item not in "0123456789abcdef" for item in value):
        raise RuntimeError("invalid protocol freeze commit")


def _validate_attempt_id(value: str) -> None:
    if len(value) != 64 or any(item not in "0123456789abcdef" for item in value):
        raise RuntimeError("invalid attempt ID")


if __name__ == "__main__":
    raise SystemExit(main())
