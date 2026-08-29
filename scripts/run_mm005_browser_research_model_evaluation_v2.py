"""Execute the frozen MM-005 Browser Research recovery experiment v2 once."""

from __future__ import annotations

import argparse
import gc
import io
import json
import os
import secrets
import stat
import subprocess
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SRC))

from fullcycle_bridge import (  # noqa: E402
    mm004_hard_negative_model_evaluation as candidate_protocol,
)
from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_adapter_verifier as adapter_verifier,
)
from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_model_evaluation as v1_contract,
)
from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_model_evaluation_protocol_v2 as contract,
)
from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_model_evaluation_recovery_io as recovery_io,
)
from scripts import (  # noqa: E402
    prepare_mm005_browser_research_model_evaluation_v2 as protocol_builder,
)
from scripts import run_mm003_multimodal_gui_action_baseline as base_runner  # noqa: E402
from scripts import (  # noqa: E402
    run_mm003_post_training_eval_repeatability as repeat_runner,
)
from scripts import run_mm003_qlora_post_training_v2 as upstream_runner  # noqa: E402
from scripts import (  # noqa: E402
    run_mm005_browser_research_model_evaluation as v1_runner,
)
from scripts import validate_mm003_post_training_v2_result as file_validator  # noqa: E402

MAX_JSON_BYTES = 8 * 1024 * 1024
ProgressAppender = Callable[[str, Mapping[str, Any], Sequence[str], str | None], bytes]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol-freeze-commit", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = execute_frozen_protocol(
        protocol_freeze_commit=str(args.protocol_freeze_commit)
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


def execute_frozen_protocol(*, protocol_freeze_commit: str) -> dict[str, Any]:
    """Consume the one owner/progress-marked offline v2 evaluation attempt."""

    _validate_commit(protocol_freeze_commit)
    _validate_formal_python_execution_mode()
    output_dir = ROOT / contract.RUN_OUTPUT_ROOT
    if os.path.lexists(output_dir):
        raise RuntimeError("formal MM-005 v2 evaluation output must be absent")

    protocol_inputs = protocol_builder.protocol_inputs()
    preregistration_payload = recovery_io.read_regular_file(
        ROOT / contract.PREREGISTRATION_PATH,
        max_bytes=MAX_JSON_BYTES,
    )
    preregistration = contract.parse_strict_json_bytes(
        preregistration_payload, location="$.preregistration"
    )
    contract.validate_preregistration(preregistration, **protocol_inputs)
    if contract.artifact_json_bytes(preregistration) != preregistration_payload:
        raise RuntimeError("MM-005 v2 preregistration is not canonical")

    execution_inputs = protocol_builder.execution_inputs()
    _validate_protocol_freeze_commit(
        protocol_freeze_commit=protocol_freeze_commit,
        preregistration_payload=preregistration_payload,
        protocol_inputs=protocol_inputs,
        execution_inputs=execution_inputs,
    )
    upstream_runner._validate_local_dependency_wheel()
    _ensure_output_parent()
    lifecycle_path = ROOT / contract.LIFECYCLE_LEASE_PATH
    recovery_io.ensure_lock_directory(lifecycle_path, contract.LIFECYCLE_LEASE_MARKER)

    candidate = _mapping(preregistration.get("candidate"), "$.candidate")
    model_receipts = _object_sequence(
        candidate.get("model_files"), "$.candidate.model_files"
    )
    dataset_receipts = _receipt_mapping(
        execution_inputs["dataset_output_receipts"], "$.dataset_output_receipts"
    )
    records = _object_sequence(execution_inputs["records"], "$.records")
    expected_payloads = _bytes_mapping(
        execution_inputs["artifact_payloads"], "$.artifact_payloads"
    )

    with (
        repeat_runner._FrozenInputFileSet(
            model_snapshot=ROOT / contract.MODEL_SNAPSHOT_ROOT,
            model_receipts=model_receipts,
            adapter_receipts=contract.ADAPTER_RECEIPTS,
        ) as frozen_model,
        v1_runner._FrozenDatasetInputSet(dataset_receipts) as frozen_dataset,
        recovery_io.ProgressLease(lifecycle_path) as lifecycle,
    ):
        recovery_io.validate_lock_file(lifecycle_path, contract.LIFECYCLE_LEASE_MARKER)
        if os.path.lexists(output_dir):
            raise RuntimeError(
                "formal MM-005 v2 evaluation output appeared before claim"
            )
        if frozen_dataset.payloads != expected_payloads:
            raise RuntimeError("frozen MM-005 inputs differ from authenticated context")
        attempt_id = secrets.token_hex(32)
        counters = _new_counters()
        counters["run_attempts"] = 1
        completed_record_ids: list[str] = []
        artifact_states: dict[str, Any] = {
            "evaluation_candidate": None,
            "predictions": None,
        }
        owner_payload = contract.artifact_json_bytes(
            contract.build_attempt_owner(
                protocol_freeze_commit=protocol_freeze_commit,
                preregistration_payload=preregistration_payload,
                attempt_id=attempt_id,
            )
        )
        initial_event = contract.build_progress_event(
            previous_journal_payload=b"",
            protocol_freeze_commit=protocol_freeze_commit,
            preregistration_payload=preregistration_payload,
            attempt_owner_payload=owner_payload,
            event="attempt_claimed",
            counters=counters,
            completed_record_ids=completed_record_ids,
        )
        initial_progress = contract.artifact_json_bytes(initial_event)
        lifecycle.verify()
        _claim_output(
            output_dir=output_dir,
            attempt_id=attempt_id,
            owner_payload=owner_payload,
            progress_payload=initial_progress,
        )
        output_guard = recovery_io.DirectoryTreeGuard(ROOT, output_dir)

        candidate_payload: bytes | None = None
        predictions_payload: bytes | None = None
        stage = "context_preflight"
        started = 0.0
        with recovery_io.ProgressLease(ROOT / contract.PROGRESS_PATH) as journal:

            def append_progress(
                event: str,
                current_counters: Mapping[str, Any],
                current_completed: Sequence[str],
                record_id: str | None = None,
            ) -> bytes:
                lifecycle.verify()
                output_guard.verify()
                event_value = contract.build_progress_event(
                    previous_journal_payload=journal.read(),
                    protocol_freeze_commit=protocol_freeze_commit,
                    preregistration_payload=preregistration_payload,
                    attempt_owner_payload=owner_payload,
                    event=event,
                    counters=current_counters,
                    completed_record_ids=current_completed,
                    record_id=record_id,
                    artifact_states=artifact_states,
                )
                return journal.append(contract.artifact_json_bytes(event_value))

            append_progress(
                "context_preflight_completed", counters, completed_record_ids
            )
            started = time.perf_counter()
            try:
                stage = "model_load"
                upstream_runner._enable_offline_execution()
                with repeat_runner._OfflineSocketGuard(counters):
                    dependencies = repeat_runner._load_eval_dependencies()
                    torch = dependencies[0]
                    observed_environment = upstream_runner.observed_environment(torch)
                    if observed_environment != candidate.get("environment"):
                        raise RuntimeError("formal MM-005 v2 environment mismatch")
                    torch.cuda.empty_cache()
                    torch.cuda.reset_peak_memory_stats()
                    stage = "generation"
                    cases = _run_model_evaluation(
                        dependencies=dependencies,
                        records=records,
                        artifact_payloads=frozen_dataset.payloads,
                        counters=counters,
                        completed_record_ids=completed_record_ids,
                        append_progress=append_progress,
                    )
                    frozen_model.verify()
                    frozen_dataset.verify()
                    torch.cuda.synchronize()
                    resources = {
                        "elapsed_seconds": time.perf_counter() - started,
                        "peak_gpu_allocated_bytes": int(
                            torch.cuda.max_memory_allocated()
                        ),
                        "peak_gpu_reserved_bytes": int(
                            torch.cuda.max_memory_reserved()
                        ),
                    }

                stage = "candidate_persistence"
                candidate_object = contract.build_evaluation_candidate(
                    protocol_freeze_commit=protocol_freeze_commit,
                    preregistration_payload=preregistration_payload,
                    attempt_owner_payload=owner_payload,
                    cases=cases,
                    records=records,
                    artifact_payloads=frozen_dataset.payloads,
                    execution=counters,
                    resources=resources,
                )
                candidate_payload = contract.artifact_json_bytes(candidate_object)
                lifecycle.verify()
                output_guard.verify()
                recovery_io.write_exclusive_fsync(
                    ROOT / contract.EVALUATION_CANDIDATE_PATH, candidate_payload
                )
                artifact_states["evaluation_candidate"] = contract.artifact_state(
                    contract.EVALUATION_CANDIDATE_PATH,
                    candidate_payload,
                    state="validated",
                )
                append_progress("candidate_persisted", counters, completed_record_ids)

                stage = "scoring"
                v1_contract.score_case_results(records, cases)
                predictions_object = contract.build_predictions(candidate_object)
                predictions_payload = contract.artifact_json_bytes(predictions_object)
                stage = "predictions_persistence"
                lifecycle.verify()
                output_guard.verify()
                recovery_io.write_exclusive_fsync(
                    ROOT / contract.PREDICTIONS_PATH, predictions_payload
                )
                artifact_states["predictions"] = contract.artifact_state(
                    contract.PREDICTIONS_PATH,
                    predictions_payload,
                    state="validated",
                )
                append_progress("predictions_persisted", counters, completed_record_ids)

                stage = "evidence_persistence"
                captured_at_utc = datetime.now(timezone.utc).isoformat()
                success_terminal = contract.terminal_event(
                    kind="success", captured_at_utc=captured_at_utc
                )
                success_event = contract.build_progress_event(
                    previous_journal_payload=journal.read(),
                    protocol_freeze_commit=protocol_freeze_commit,
                    preregistration_payload=preregistration_payload,
                    attempt_owner_payload=owner_payload,
                    event="success_terminal_ready",
                    counters=counters,
                    completed_record_ids=completed_record_ids,
                    artifact_states=artifact_states,
                    terminal=success_terminal,
                )
                success_frame = contract.artifact_json_bytes(success_event)
                planned_progress = journal.read() + success_frame
                evidence_object = contract.build_evidence(
                    protocol_freeze_commit=protocol_freeze_commit,
                    preregistration_payload=preregistration_payload,
                    attempt_owner_payload=owner_payload,
                    progress_payload=planned_progress,
                    evaluation_candidate_payload=candidate_payload,
                    predictions_payload=predictions_payload,
                    records=records,
                    artifact_payloads=frozen_dataset.payloads,
                    captured_at_utc=captured_at_utc,
                )
                evidence_payload = contract.artifact_json_bytes(evidence_object)
                lifecycle.verify()
                output_guard.verify()
                journal.append(success_frame)
                lifecycle.verify()
                output_guard.verify()
                recovery_io.write_or_repair_terminal(
                    ROOT / contract.EVIDENCE_PATH, evidence_payload
                )
                return _success_summary(evidence_object)
            except BaseException as exc:
                last_events, authenticated_prefix, tail_receipt = (
                    contract.recover_progress_prefix(
                        journal.read(),
                        protocol_freeze_commit=protocol_freeze_commit,
                        preregistration_payload=preregistration_payload,
                        attempt_owner_payload=owner_payload,
                    )
                )
                if authenticated_prefix != journal.read():
                    journal.truncate_to_authenticated_prefix(authenticated_prefix)
                last_event = last_events[-1]
                if last_event.get("event") == "success_terminal_ready":
                    if candidate_payload is None or predictions_payload is None:
                        raise RuntimeError(
                            "success terminal lacks in-process artifact payloads"
                        ) from exc
                    terminal_data = _mapping(
                        last_event.get("terminal"), "$.progress.terminal"
                    )
                    evidence_object = contract.build_evidence(
                        protocol_freeze_commit=protocol_freeze_commit,
                        preregistration_payload=preregistration_payload,
                        attempt_owner_payload=owner_payload,
                        progress_payload=authenticated_prefix,
                        evaluation_candidate_payload=candidate_payload,
                        predictions_payload=predictions_payload,
                        records=records,
                        artifact_payloads=frozen_dataset.payloads,
                        captured_at_utc=str(terminal_data["captured_at_utc"]),
                    )
                    evidence_payload = contract.artifact_json_bytes(evidence_object)
                    lifecycle.verify()
                    output_guard.verify()
                    recovery_io.write_or_repair_terminal(
                        ROOT / contract.EVIDENCE_PATH, evidence_payload
                    )
                    return _success_summary(evidence_object)
                if last_event.get("event") == "failure_terminal_ready":
                    raise RuntimeError("failure terminal was already prepared") from exc
                lifecycle.verify()
                output_guard.verify()
                candidate_payload, predictions_payload, artifact_states = (
                    _observe_nonterminal_artifacts(
                        protocol_freeze_commit=protocol_freeze_commit,
                        preregistration_payload=preregistration_payload,
                        attempt_owner_payload=owner_payload,
                        records=records,
                        dataset_payloads=frozen_dataset.payloads,
                    )
                )
                failed_after = str(last_event["event"])
                failure_terminal = contract.terminal_event(
                    kind="failure",
                    captured_at_utc=datetime.now(timezone.utc).isoformat(),
                    stage=stage,
                    exception_type=_safe_exception_type(exc),
                    external_controller_interruption=False,
                    interrupted_after_event=failed_after,
                    discarded_progress_tail=tail_receipt,
                )
                failure_event = contract.build_progress_event(
                    previous_journal_payload=journal.read(),
                    protocol_freeze_commit=protocol_freeze_commit,
                    preregistration_payload=preregistration_payload,
                    attempt_owner_payload=owner_payload,
                    event="failure_terminal_ready",
                    counters=_mapping(last_event["counters"], "$.progress.counters"),
                    completed_record_ids=_string_sequence(
                        last_event["completed_record_ids"],
                        "$.progress.completed_record_ids",
                    ),
                    artifact_states=artifact_states,
                    terminal=failure_terminal,
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
                raise
            finally:
                gc.collect()


def _run_model_evaluation(
    *,
    dependencies: tuple[Any, ...],
    records: Sequence[Mapping[str, Any]],
    artifact_payloads: Mapping[str, bytes],
    counters: dict[str, int],
    completed_record_ids: list[str],
    append_progress: ProgressAppender,
) -> list[dict[str, Any]]:
    torch, image_class, peft_model_class, processor_class, model_class, bnb_class = (
        dependencies
    )
    upstream_runner._seed_all(torch, contract.SEED)
    model_snapshot = ROOT / contract.MODEL_SNAPSHOT_ROOT
    processor = processor_class.from_pretrained(
        model_snapshot,
        local_files_only=True,
        min_pixels=256 * 28 * 28,
        max_pixels=1280 * 28 * 28,
        use_fast=False,
    )
    counters["fresh_base_load_attempts"] = 1
    append_progress("base_load_started", counters, completed_record_ids, None)
    base_model = model_class.from_pretrained(
        model_snapshot,
        quantization_config=upstream_runner._quantization_config(torch, bnb_class),
        attn_implementation="sdpa",
        device_map={"": 0},
        local_files_only=True,
        low_cpu_mem_usage=True,
    )
    counters["fresh_base_loads"] = 1
    append_progress("base_load_completed", counters, completed_record_ids, None)
    counters["independent_adapter_load_attempts"] = 1
    append_progress("adapter_load_started", counters, completed_record_ids, None)
    model = peft_model_class.from_pretrained(
        base_model,
        ROOT / contract.ADAPTER_ROOT,
        is_trainable=False,
        local_files_only=True,
    ).eval()
    counters["independent_adapter_loads"] = 1
    append_progress("adapter_load_completed", counters, completed_record_ids, None)
    model.config.use_cache = True
    if model.training is not False or any(
        parameter.requires_grad for parameter in model.parameters()
    ):
        raise RuntimeError("MM-005 v2 evaluation model has trainable state")

    cases: list[dict[str, Any]] = []
    ordered = sorted(records, key=lambda item: str(item.get("record_id")))
    screenshot_payloads, source_snapshot_payloads = v1_contract.artifact_input_sets(
        artifact_payloads
    )
    with torch.inference_mode():
        for record in ordered:
            adapted = adapter_verifier.adapt_record(
                record, screenshot_payloads, source_snapshot_payloads
            )
            record_id = str(record["record_id"])
            images = [
                image_class.open(io.BytesIO(payload)).convert("RGB")
                for payload in adapted.screenshot_payloads
            ]
            try:
                counters["generate_attempts"] += 1
                counters["screenshot_inputs"] += len(images)
                append_progress(
                    "generation_started", counters, completed_record_ids, record_id
                )
                messages = v1_contract.build_runtime_messages(
                    adapted.model_payload(), images
                )
                torch.cuda.synchronize()
                started = time.perf_counter()
                raw_output, generated_tokens = base_runner._generate_one(
                    torch=torch,
                    model=model,
                    processor=processor,
                    messages=messages,
                    images=images,
                    max_new_tokens=contract.MAX_NEW_TOKENS,
                )
                torch.cuda.synchronize()
                case = v1_contract.build_case_result(
                    record=record,
                    artifact_payloads=artifact_payloads,
                    raw_output=raw_output,
                    generated_tokens=generated_tokens,
                    latency_seconds=time.perf_counter() - started,
                )
                counters["generate_calls"] += 1
                cases.append(case)
                completed_record_ids.append(record_id)
                append_progress(
                    "generation_completed", counters, completed_record_ids, record_id
                )
            finally:
                for image in images:
                    image.close()
    if counters != contract.expected_execution_counters():
        raise RuntimeError("MM-005 v2 evaluation counters differ from protocol")
    append_progress("model_evaluation_completed", counters, completed_record_ids, None)
    del model, base_model, processor
    gc.collect()
    torch.cuda.empty_cache()
    return cases


def _claim_output(
    *, output_dir: Path, attempt_id: str, owner_payload: bytes, progress_payload: bytes
) -> None:
    reservation = repeat_runner._prepare_output_reservation(output_dir)
    staging = output_dir.with_name(f".{output_dir.name}.owner-{attempt_id}")
    staging_reservation = repeat_runner._prepare_output_reservation(staging)
    os.mkdir(staging_reservation[0])
    recovery_io.write_exclusive_fsync(
        staging / Path(contract.ATTEMPT_OWNER_PATH).name, owner_payload
    )
    recovery_io.write_exclusive_fsync(
        staging / Path(contract.PROGRESS_PATH).name, progress_payload
    )
    os.rename(staging, reservation[0])
    observed = {item.name for item in output_dir.iterdir()}
    if observed != {"attempt-owner.json", "progress.json"}:
        raise RuntimeError("atomic v2 owner claim topology differs")


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


def _validate_protocol_freeze_commit(
    *,
    protocol_freeze_commit: str,
    preregistration_payload: bytes,
    protocol_inputs: Mapping[str, Any],
    execution_inputs: Mapping[str, Any],
) -> None:
    branch = _git_text("rev-parse", "--abbrev-ref", "HEAD")
    head = _git_text("rev-parse", "HEAD")
    origin_master = _git_text("rev-parse", "refs/remotes/origin/master")
    if branch != "master" or head != origin_master or head != protocol_freeze_commit:
        raise RuntimeError(
            "formal MM-005 v2 evaluation requires aligned merged master freeze commit"
        )
    tracked: dict[str, Mapping[str, Any]] = {
        contract.PREREGISTRATION_PATH: _receipt(
            contract.PREREGISTRATION_PATH, preregistration_payload
        )
    }
    tracked.update(
        {
            str(receipt["path"]): receipt
            for receipt in _receipt_mapping(
                protocol_inputs["source_receipts"], "$.source_receipts"
            ).values()
        }
    )
    for key in (
        "v1_preregistration_payload",
        "v1_attempt_owner_payload",
        "v1_failure_classification_payload",
    ):
        payload = _bytes_value(protocol_inputs[key], f"$.{key}")
        path = {
            "v1_preregistration_payload": v1_contract.PREREGISTRATION_PATH,
            "v1_attempt_owner_payload": contract.V1_ATTEMPT_OWNER_RECEIPT["path"],
            "v1_failure_classification_payload": contract.V1_FAILURE_CLASSIFICATION_RECEIPT[
                "path"
            ],
        }[key]
        tracked[path] = _receipt(path, payload)
    tracked.update(
        {
            str(path): receipt
            for path, receipt in _receipt_mapping(
                execution_inputs["dataset_output_receipts"],
                "$.dataset_output_receipts",
            ).items()
        }
    )
    tracked.update(
        {
            str(receipt["path"]): receipt
            for receipt in contract.ADAPTER_RECEIPTS.values()
        }
    )
    for path, expected in sorted(tracked.items()):
        payload = _git_blob_bytes(protocol_freeze_commit, path)
        if path == contract.ADAPTER_LFS_PATH:
            matches = payload == candidate_protocol.git_lfs_pointer_bytes(expected)
        else:
            matches = _receipt(path, payload) == dict(expected)
        if not matches:
            raise RuntimeError(f"freeze commit tracked receipt differs: {path}")


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
    if len(completed.stdout) > 64 * 1024 * 1024:
        raise RuntimeError("freeze-commit blob exceeds byte limit")
    return completed.stdout


def _validate_formal_python_execution_mode() -> None:
    repeat_runner._require_exact_repo_path(Path.cwd(), ROOT, "working directory")
    repeat_runner._require_exact_repo_path(
        Path(sys.executable), ROOT / contract.FORMAL_PYTHON_PATH, "Python executable"
    )
    if (
        sys.flags.isolated != 1
        or sys.flags.dont_write_bytecode != 1
        or sys.flags.safe_path is not True
        or sys.pycache_prefix != "NUL"
    ):
        raise RuntimeError("formal MM-005 v2 evaluation requires isolated Python args")


def _ensure_output_parent() -> None:
    parent = (ROOT / contract.RUN_OUTPUT_ROOT).parent
    if not os.path.lexists(parent):
        safe_parent, parent_chain = file_validator._safe_repository_parent_chain(
            ROOT, parent, "MM-005 v2 evaluation output parent"
        )
        os.mkdir(safe_parent)
        file_validator._recheck_repository_parent_chain(
            parent_chain,
            "MM-005 v2 evaluation output parent",
            identity_only=True,
        )
    metadata = parent.lstat()
    if not stat.S_ISDIR(metadata.st_mode) or file_validator._metadata_is_reparse(
        metadata
    ):
        raise RuntimeError("unsafe MM-005 v2 evaluation output parent")


def _new_counters() -> dict[str, int]:
    return {key: 0 for key in contract.expected_execution_counters()}


def _read_optional(path: Path) -> bytes | None:
    if not os.path.lexists(path):
        return None
    return recovery_io.read_regular_file(path, max_bytes=64 * 1024 * 1024)


def _safe_exception_type(exc: BaseException) -> str:
    value = type(exc).__name__
    return value if value.isidentifier() and len(value) <= 128 else "BaseException"


def _success_summary(evidence: Mapping[str, Any]) -> dict[str, Any]:
    metrics = _mapping(evidence.get("metrics"), "$.evidence.metrics")
    joint = _mapping(
        metrics.get("joint_exact_accuracy"), "$.metrics.joint_exact_accuracy"
    )
    return {
        "classification": evidence["classification"],
        "formal_gate_passed": evidence["formal_gate_passed"],
        "joint_exact_accuracy": joint["value"],
        "record_count": metrics["record_count"],
        "next_gate": evidence["next_gate"],
        "valid": evidence["formal_gate_passed"],
    }


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


def _receipt(path: str, payload: bytes) -> dict[str, Any]:
    return {
        "path": path,
        "bytes": len(payload),
        "sha256": contract.sha256_bytes(payload),
    }


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


def _receipt_mapping(value: object, location: str) -> dict[str, Mapping[str, Any]]:
    mapping = _mapping(value, location)
    return {
        str(name): _mapping(receipt, f"{location}.{name}")
        for name, receipt in mapping.items()
    }


def _bytes_mapping(value: object, location: str) -> dict[str, bytes]:
    mapping = _mapping(value, location)
    result: dict[str, bytes] = {}
    for name, payload in mapping.items():
        if not isinstance(payload, bytes):
            raise RuntimeError(f"expected bytes at {location}.{name}")
        result[str(name)] = payload
    return result


def _bytes_value(value: object, location: str) -> bytes:
    if not isinstance(value, bytes):
        raise RuntimeError(f"expected bytes at {location}")
    return value


def _validate_commit(value: str) -> None:
    if len(value) != 40 or any(item not in "0123456789abcdef" for item in value):
        raise RuntimeError("invalid protocol freeze commit")


if __name__ == "__main__":
    raise SystemExit(main())
