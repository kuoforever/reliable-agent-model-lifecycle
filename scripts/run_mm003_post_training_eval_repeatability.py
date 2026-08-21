"""Prepare or execute the frozen MM-003 eval-only repeatability protocol."""

from __future__ import annotations

import argparse
import gc
import hashlib
import io
import json
import os
import re
import secrets
import socket
import stat
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NoReturn

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SRC))

from fullcycle_bridge import gui_grounding_eval_v2 as scorer  # noqa: E402
from fullcycle_bridge import (  # noqa: E402
    mm003_post_training_eval_repeatability as contract,
)
from scripts import run_mm003_multimodal_gui_action_baseline as base_runner  # noqa: E402
from scripts import run_mm003_qlora_post_training_v2 as upstream_runner  # noqa: E402
from scripts import validate_mm003_post_training_v2_result as result_validator  # noqa: E402

MAX_SOURCE_BYTES = 4 * 1024 * 1024
MAX_PREREGISTRATION_BYTES = 4 * 1024 * 1024


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare")
    prepare.add_argument(
        "--output", type=Path, default=ROOT / contract.PREREGISTRATION_PATH
    )
    prepare.add_argument("--freeze-status", choices=("draft", "frozen"), required=True)
    prepare.add_argument("--check", action="store_true")

    run = subparsers.add_parser("run")
    run.add_argument("--model-snapshot", type=Path, required=True)
    run.add_argument(
        "--preregistration",
        type=Path,
        default=ROOT / contract.PREREGISTRATION_PATH,
    )
    run.add_argument("--protocol-freeze-commit", required=True)
    run.add_argument("--output-dir", type=Path, default=ROOT / contract.RUN_OUTPUT_ROOT)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "prepare":
        result = prepare_protocol(
            output_path=args.output,
            freeze_status=args.freeze_status,
            check=args.check,
        )
    else:
        result = execute_frozen_protocol(
            model_snapshot=args.model_snapshot,
            preregistration_path=args.preregistration,
            protocol_freeze_commit=args.protocol_freeze_commit,
            output_dir=args.output_dir,
        )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


def prepare_protocol(
    *, output_path: Path, freeze_status: str, check: bool
) -> dict[str, Any]:
    context = load_authenticated_context()
    source_hashes = protocol_source_hashes()
    preregistration = contract.expected_preregistration(
        freeze_status=freeze_status,
        source_hashes=source_hashes,
        upstream_preregistration=context["upstream_preregistration"],
        reference_evidence=context["reference_evidence"],
        reference_predictions=context["reference_predictions"],
        result_review=context["result_review"],
        suite=context["suite"],
    )
    payload = contract.artifact_json_bytes(preregistration)
    expected_path = ROOT / contract.PREREGISTRATION_PATH
    _require_exact_repo_path(output_path, expected_path, "preregistration")
    if check:
        observed = _read_bounded_regular(
            expected_path,
            label="repeatability preregistration",
            max_bytes=MAX_PREREGISTRATION_BYTES,
        )
        if observed != payload:
            raise RuntimeError(
                "repeatability preregistration differs from recomputation"
            )
    else:
        result_validator._write_exclusive(ROOT, expected_path, payload)
    return {
        "case_count": contract.EXPECTED_CASES,
        "freeze_status": freeze_status,
        "next_gate": contract.EXECUTION_GATE_ID,
        "protocol_sources": len(source_hashes),
        "sha256": contract.sha256_bytes(payload),
        "valid": True,
    }


def execute_frozen_protocol(
    *,
    model_snapshot: Path,
    preregistration_path: Path,
    protocol_freeze_commit: str,
    output_dir: Path,
) -> dict[str, Any]:
    """Execute the single registered eval-only replay; never train or save a model."""

    if not base_runner.re_full_commit(protocol_freeze_commit):
        raise RuntimeError("protocol freeze commit must be a lowercase 40-hex commit")
    _require_exact_repo_path(
        model_snapshot,
        ROOT / contract.MODEL_SNAPSHOT_ROOT,
        "model snapshot",
    )
    _validate_formal_python_execution_mode()
    expected_output = ROOT / contract.RUN_OUTPUT_ROOT
    _require_exact_repo_path(output_dir, expected_output, "output directory")
    expected_preregistration_path = ROOT / contract.PREREGISTRATION_PATH
    _require_exact_repo_path(
        preregistration_path, expected_preregistration_path, "preregistration"
    )
    if os.path.lexists(expected_output):
        raise RuntimeError("output directory must be absent before formal replay")

    # Every operation above and below this block is CPU-only preflight until the
    # Atomic claim of the owner-marked fixed directory is the one-shot boundary.
    context = load_authenticated_context()
    source_hashes = protocol_source_hashes()
    preregistration_payload = _read_bounded_regular(
        expected_preregistration_path,
        label="repeatability preregistration",
        max_bytes=MAX_PREREGISTRATION_BYTES,
    )
    raw = contract.parse_strict_json_bytes(
        preregistration_payload, location="$.preregistration"
    )
    if not isinstance(raw, Mapping):
        raise RuntimeError("repeatability preregistration must be an object")
    preregistration = contract.validate_preregistration(
        raw,
        source_hashes=source_hashes,
        upstream_preregistration=context["upstream_preregistration"],
        reference_evidence=context["reference_evidence"],
        reference_predictions=context["reference_predictions"],
        result_review=context["result_review"],
        suite=context["suite"],
    )
    if contract.artifact_json_bytes(preregistration) != preregistration_payload:
        raise RuntimeError("repeatability preregistration must be canonical JSON")
    _validate_protocol_freeze_commit(
        protocol_freeze_commit=protocol_freeze_commit,
        preregistration_payload=preregistration_payload,
        source_hashes=source_hashes,
    )
    upstream_runner._validate_local_dependency_wheel()
    if (
        context["screenshot_receipts"]
        != preregistration["source_lineage"]["unchanged_mm002_eval"]["screenshots"]
    ):
        raise RuntimeError("MM-002 screenshot receipts differ from preregistration")

    with _FrozenInputFileSet(
        model_snapshot=model_snapshot,
        model_receipts=preregistration["model"]["files"],
        adapter_receipts=contract.ADAPTER_RECEIPTS,
    ) as frozen_inputs:
        model_manifest = frozen_inputs.model_receipts
        adapter_before = frozen_inputs.adapter_receipts
        _ensure_output_parent()
        reservation = _prepare_output_reservation(expected_output)
        attempt_consumed = False
        output_guard: _ConsumedOutputDirectoryGuard | None = None
        owner_token = secrets.token_hex(32)
        attempt_owner_intended_payload = contract.artifact_json_bytes(
            contract.build_attempt_owner(
                protocol_freeze_commit=protocol_freeze_commit,
                preregistration_payload=preregistration_payload,
                owner_token=owner_token,
            )
        )
        owner_staging_path = expected_output.with_name(
            f".{expected_output.name}.owner-{owner_token}"
        )
        owner_staging_reservation = _prepare_output_reservation(owner_staging_path)
        attempt_owner_written_payload: bytes | None = None
        lifecycle_started = 0.0
        stage = "output_reservation"
        counters = _new_counters()
        completed_case_ids: list[str] = []
        candidate_intended_payload: bytes | None = None
        candidate_written_payload: bytes | None = None
        predictions_intended_payload: bytes | None = None
        predictions_written_payload: bytes | None = None
        evidence_intended_payload: bytes | None = None
        evidence_written_payload: bytes | None = None
        evidence_object: dict[str, Any] | None = None
        try:
            os.mkdir(owner_staging_reservation[0])
            result_validator._write_exclusive(
                ROOT,
                owner_staging_path / Path(contract.ATTEMPT_OWNER_ARTIFACT).name,
                attempt_owner_intended_payload,
            )
            os.rename(owner_staging_path, reservation[0])
            attempt_consumed = True
            attempt_owner_written_payload = attempt_owner_intended_payload
            output_guard = _ConsumedOutputDirectoryGuard(
                reservation,
                initial_artifacts={
                    ROOT / contract.ATTEMPT_OWNER_ARTIFACT: (
                        attempt_owner_written_payload
                    )
                },
            )
            output_guard.open()
            lifecycle_started = time.perf_counter()
            stage = "dependency_import"
            upstream_runner._enable_offline_execution()
            with _OfflineSocketGuard(counters):
                dependencies = _load_eval_dependencies()
                torch = dependencies[0]
                stage = "locked_environment"
                environment = upstream_runner.observed_environment(torch)
                if environment != contract.LOCKED_ENVIRONMENT:
                    raise RuntimeError("locked environment mismatch")
                torch.cuda.empty_cache()
                torch.cuda.reset_peak_memory_stats()
                stage = "independent_adapter_load_and_eval"
                candidate = _run_eval_only(
                    dependencies=dependencies,
                    model_snapshot=model_snapshot,
                    adapter_dir=ROOT / contract.ADAPTER_ROOT,
                    suite=context["suite"],
                    screenshot_receipts=context["screenshot_receipts"],
                    screenshot_payloads=context["screenshot_payloads"],
                    counters=counters,
                    completed_case_ids=completed_case_ids,
                    protocol_freeze_commit=protocol_freeze_commit,
                    preregistration_payload=preregistration_payload,
                )
                stage = "evaluation_candidate"
                candidate_payload = contract.artifact_json_bytes(candidate)
                candidate_intended_payload = candidate_payload
                _write_output_artifact(
                    output_guard,
                    ROOT / contract.EVALUATION_CANDIDATE_ARTIFACT,
                    candidate_payload,
                )
                candidate_written_payload = candidate_payload
                stage = "total_scoring"
                report = scorer.score_predictions(
                    context["suite"], candidate["predictions"]
                )
                evaluation = {
                    "execution": candidate["execution"],
                    "cases": candidate["cases"],
                    "predictions": candidate["predictions"],
                    "score": report,
                }
                contract.validate_completed_evaluation(
                    evaluation,
                    suite=context["suite"],
                    screenshot_receipts=context["screenshot_receipts"],
                )
                stage = "predictions"
                predictions_payload = contract.artifact_json_bytes(
                    evaluation["predictions"]
                )
                predictions_intended_payload = predictions_payload
                _write_output_artifact(
                    output_guard,
                    ROOT / contract.PREDICTIONS_ARTIFACT,
                    predictions_payload,
                )
                predictions_written_payload = predictions_payload
                stage = "adapter_postcondition"
                model_after, adapter_after = frozen_inputs.verify()
                if model_after != model_manifest or adapter_after != adapter_before:
                    raise RuntimeError("frozen model or Adapter changed during replay")
                torch.cuda.synchronize()
                resources = {
                    "elapsed_seconds": time.perf_counter() - lifecycle_started,
                    "peak_gpu_allocated_bytes": int(torch.cuda.max_memory_allocated()),
                    "peak_gpu_reserved_bytes": int(torch.cuda.max_memory_reserved()),
                }
            stage = "evidence"
            evidence = contract.build_evidence(
                preregistration_payload=preregistration_payload,
                attempt_owner_payload=attempt_owner_written_payload,
                evaluation_candidate_payload=candidate_written_payload,
                predictions_payload=predictions_written_payload,
                protocol_freeze_commit=protocol_freeze_commit,
                reference_evaluation=context["reference_evidence"]["evaluation"],
                replay_evaluation=evaluation,
                preregistration=preregistration,
                suite=context["suite"],
                screenshot_receipts=context["screenshot_receipts"],
                environment=environment,
                model_files=model_manifest,
                adapter_receipts=adapter_after,
                resources=resources,
                captured_at_utc=datetime.now(timezone.utc).isoformat(),
            )
            evidence_payload = contract.artifact_json_bytes(evidence)
            evidence_object = evidence
            evidence_intended_payload = evidence_payload
            _write_output_artifact(
                output_guard, ROOT / contract.EVIDENCE_ARTIFACT, evidence_payload
            )
            evidence_written_payload = evidence_payload
            return _success_summary(evidence)
        except BaseException as exc:
            if (
                not attempt_consumed
                and not isinstance(exc, Exception)
                and os.path.lexists(reservation[0])
            ):
                attempt_owner_written_payload = _observe_attempt_owner(
                    ROOT / contract.ATTEMPT_OWNER_ARTIFACT,
                    attempt_owner_intended_payload,
                    strict=False,
                )
                attempt_consumed = attempt_owner_written_payload is not None
            if attempt_consumed and attempt_owner_written_payload is None:
                attempt_owner_written_payload = _observe_attempt_owner(
                    ROOT / contract.ATTEMPT_OWNER_ARTIFACT,
                    attempt_owner_intended_payload,
                    strict=True,
                )
                if attempt_owner_written_payload is None:
                    result_validator._write_exclusive(
                        ROOT,
                        ROOT / contract.ATTEMPT_OWNER_ARTIFACT,
                        attempt_owner_intended_payload,
                    )
                    attempt_owner_written_payload = attempt_owner_intended_payload
            if attempt_consumed and (
                output_guard is None or not output_guard.is_open
            ):
                assert attempt_owner_written_payload is not None
                output_guard = _ConsumedOutputDirectoryGuard(
                    reservation,
                    initial_artifacts={
                        ROOT / contract.ATTEMPT_OWNER_ARTIFACT: (
                            attempt_owner_written_payload
                        )
                    },
                )
                output_guard.open()
            if attempt_consumed and candidate_written_payload is None:
                candidate_written_payload = _recover_exclusive_artifact(
                    output_guard,
                    ROOT / contract.EVALUATION_CANDIDATE_ARTIFACT,
                    candidate_intended_payload,
                    "evaluation candidate",
                )
            if attempt_consumed and predictions_written_payload is None:
                predictions_written_payload = _recover_exclusive_artifact(
                    output_guard,
                    ROOT / contract.PREDICTIONS_ARTIFACT,
                    predictions_intended_payload,
                    "predictions",
                )
            if attempt_consumed and evidence_written_payload is None:
                evidence_written_payload = _recover_exclusive_artifact(
                    output_guard,
                    ROOT / contract.EVIDENCE_ARTIFACT,
                    evidence_intended_payload,
                    "evidence",
                )
            if evidence_written_payload is not None:
                if evidence_object is None:
                    raise RuntimeError(
                        "durable evidence exists without authenticated evidence object"
                    ) from exc
                return _success_summary(evidence_object)
            exception_type, exception_code, exception_location = (
                _safe_exception_diagnostic(exc)
            )
            if attempt_consumed:
                failure = contract.build_failure(
                    protocol_freeze_commit=protocol_freeze_commit,
                    preregistration_payload=preregistration_payload,
                    attempt_owner_payload=attempt_owner_written_payload,
                    stage=stage,
                    exception_type=exception_type,
                    exception_code=exception_code,
                    exception_location=exception_location,
                    counters=counters,
                    completed_case_ids=completed_case_ids,
                    suite=context["suite"],
                    screenshot_receipts=context["screenshot_receipts"],
                    evaluation_candidate_payload=candidate_written_payload,
                    predictions_payload=predictions_written_payload,
                )
                assert output_guard is not None
                _write_output_artifact(
                    output_guard,
                    ROOT / contract.FAILURE_ARTIFACT,
                    contract.artifact_json_bytes(failure),
                )
            raise
        finally:
            if output_guard is not None:
                output_guard.close()
            gc.collect()


def load_authenticated_context() -> dict[str, Any]:
    summary = result_validator.validate_repository(ROOT)
    if (
        summary.get("formal_gate_passed") is not True
        or summary.get("next_gate") != contract.PROTOCOL_GATE_ID
    ):
        raise RuntimeError("upstream result review does not authorize this protocol")
    suite = result_validator._load_safe_mm002_suite(ROOT)
    upstream_payload = result_validator._read_exact(
        ROOT,
        ROOT / str(contract.UPSTREAM_PREREGISTRATION_RECEIPT["path"]),
        expected_bytes=int(contract.UPSTREAM_PREREGISTRATION_RECEIPT["bytes"]),
        expected_sha256=str(contract.UPSTREAM_PREREGISTRATION_RECEIPT["sha256"]),
        label="upstream preregistration",
    )
    evidence_payload = result_validator._read_exact(
        ROOT,
        ROOT / str(contract.REFERENCE_EVIDENCE_RECEIPT["path"]),
        expected_bytes=int(contract.REFERENCE_EVIDENCE_RECEIPT["bytes"]),
        expected_sha256=str(contract.REFERENCE_EVIDENCE_RECEIPT["sha256"]),
        label="reference evidence",
    )
    predictions_payload = result_validator._read_exact(
        ROOT,
        ROOT / str(contract.REFERENCE_PREDICTIONS_RECEIPT["path"]),
        expected_bytes=int(contract.REFERENCE_PREDICTIONS_RECEIPT["bytes"]),
        expected_sha256=str(contract.REFERENCE_PREDICTIONS_RECEIPT["sha256"]),
        label="reference predictions",
    )
    review_payload = result_validator._read_exact(
        ROOT,
        ROOT / str(contract.RESULT_REVIEW_RECEIPT["path"]),
        expected_bytes=int(contract.RESULT_REVIEW_RECEIPT["bytes"]),
        expected_sha256=str(contract.RESULT_REVIEW_RECEIPT["sha256"]),
        label="upstream result review",
    )
    objects = {
        "upstream_preregistration": _parse_object(
            upstream_payload, "$.upstream_preregistration"
        ),
        "reference_evidence": _parse_object(evidence_payload, "$.reference_evidence"),
        "reference_predictions": _parse_object(
            predictions_payload, "$.reference_predictions"
        ),
        "result_review": _parse_object(review_payload, "$.result_review"),
    }
    screenshot_receipts, screenshot_payloads = upstream_runner._eval_screenshots(suite)
    contract.validate_reference_payloads(
        upstream_preregistration=objects["upstream_preregistration"],
        reference_evidence=objects["reference_evidence"],
        reference_predictions=objects["reference_predictions"],
        result_review=objects["result_review"],
        suite=suite,
    )
    return {
        **objects,
        "suite": suite,
        "screenshot_receipts": screenshot_receipts,
        "screenshot_payloads": screenshot_payloads,
    }


def protocol_source_hashes() -> dict[str, str]:
    return {
        name: contract.sha256_bytes(
            _read_bounded_regular(
                ROOT / path,
                label=f"protocol source {name}",
                max_bytes=MAX_SOURCE_BYTES,
            )
        )
        for name, path in contract.PROTOCOL_SOURCE_PATHS.items()
    }


def _run_eval_only(
    *,
    dependencies: tuple[Any, ...],
    model_snapshot: Path,
    adapter_dir: Path,
    suite: Mapping[str, Any],
    screenshot_receipts: Sequence[Mapping[str, Any]],
    screenshot_payloads: Mapping[str, bytes],
    counters: dict[str, int | bool],
    completed_case_ids: list[str],
    protocol_freeze_commit: str,
    preregistration_payload: bytes,
) -> dict[str, Any]:
    torch, image_class, peft_model_class, processor_class, model_class, bnb_class = (
        dependencies
    )
    if [case.get("case_id") for case in suite["cases"]] != list(contract.CASE_ORDER):
        raise RuntimeError("MM-002 case order differs from frozen protocol")
    upstream_runner._seed_all(torch, contract.SEED)
    processor = processor_class.from_pretrained(
        model_snapshot,
        local_files_only=True,
        min_pixels=256 * 28 * 28,
        max_pixels=1280 * 28 * 28,
        use_fast=False,
    )
    counters["fresh_base_load_attempts"] = 1
    base_model = model_class.from_pretrained(
        model_snapshot,
        quantization_config=upstream_runner._quantization_config(torch, bnb_class),
        attn_implementation="sdpa",
        device_map={"": 0},
        local_files_only=True,
        low_cpu_mem_usage=True,
    )
    counters["fresh_base_loads"] = 1
    counters["independent_adapter_load_attempts"] = 1
    model = peft_model_class.from_pretrained(
        base_model,
        adapter_dir,
        is_trainable=False,
        local_files_only=True,
    ).eval()
    counters["independent_adapter_loads"] = 1
    model.config.use_cache = True
    if model.training is not False or any(
        parameter.requires_grad for parameter in model.parameters()
    ):
        raise RuntimeError("eval-only model has trainable state")

    screenshot_hashes = {
        item["case_id"]: item["sha256"] for item in screenshot_receipts
    }
    case_results: list[dict[str, Any]] = []
    prediction_records: list[dict[str, Any]] = []
    counters["full_eval_run_attempts"] = 1
    with torch.inference_mode():
        for case in suite["cases"]:
            case_id = str(case["case_id"])
            counters["generate_attempts"] = int(counters["generate_attempts"]) + 1
            content: list[dict[str, Any]] = []
            images: list[Any] | None = None
            image = None
            try:
                if case["observation_mode"] != "uia_only":
                    payload = screenshot_payloads.get(case_id)
                    if not isinstance(payload, bytes):
                        raise RuntimeError("authenticated screenshot payload missing")
                    image = image_class.open(io.BytesIO(payload)).convert("RGB")
                    images = [image]
                    content.append({"type": "image", "image": image})
                content.append(
                    {
                        "type": "text",
                        "text": upstream_runner.contract.baseline.build_user_prompt(
                            case
                        ),
                    }
                )
                messages = [
                    {
                        "role": "system",
                        "content": upstream_runner.contract.baseline.SYSTEM_PROMPT,
                    },
                    {"role": "user", "content": content},
                ]
                torch.cuda.synchronize()
                started = time.perf_counter()
                raw_output, generated_tokens = base_runner._generate_one(
                    torch=torch,
                    model=model,
                    processor=processor,
                    messages=messages,
                    images=images,
                    max_new_tokens=256,
                )
                counters["generate_calls"] = int(counters["generate_calls"]) + 1
                torch.cuda.synchronize()
                compiled = upstream_runner.contract.baseline.compile_raw_prediction(
                    raw_output, case
                )
                completed_case_ids.append(case_id)
                prediction_records.append(compiled)
                case_results.append(
                    {
                        "case_id": case_id,
                        "observation_mode": case["observation_mode"],
                        "raw_output": raw_output,
                        "compiled_prediction": compiled,
                        "compiler_fallback": (
                            compiled["reason"] == "model_output_invalid"
                        ),
                        "generated_tokens": generated_tokens,
                        "latency_seconds": time.perf_counter() - started,
                        "screenshot_sha256": screenshot_hashes.get(case_id),
                    }
                )
            finally:
                if image is not None:
                    image.close()
    counters["full_eval_runs"] = 1
    predictions = {
        "gui_grounding_prediction_version": 1,
        "suite_id": suite["suite_id"],
        "producer": {
            "kind": "model",
            "model_id": contract.ADAPTER_MODEL_ID,
            "model_revision": contract.MODEL_REVISION,
        },
        "records": prediction_records,
    }
    execution = dict(counters)
    if execution != contract.expected_replay_execution():
        raise RuntimeError("eval-only execution counters differ from protocol")
    del model, base_model, processor
    gc.collect()
    torch.cuda.empty_cache()
    return contract.build_evaluation_candidate(
        protocol_freeze_commit=protocol_freeze_commit,
        preregistration_payload=preregistration_payload,
        execution=execution,
        cases=case_results,
        predictions=predictions,
        suite=suite,
        screenshot_receipts=screenshot_receipts,
    )


def _load_eval_dependencies() -> tuple[Any, ...]:
    import torch
    from peft import PeftModel  # type: ignore[import-not-found]
    from PIL import Image
    from transformers import (  # type: ignore[import-untyped]
        AutoProcessor,
        BitsAndBytesConfig,
        Qwen2_5_VLForConditionalGeneration,
    )

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable")
    return (
        torch,
        Image,
        PeftModel,
        AutoProcessor,
        Qwen2_5_VLForConditionalGeneration,
        BitsAndBytesConfig,
    )


def _validate_protocol_freeze_commit(
    *,
    protocol_freeze_commit: str,
    preregistration_payload: bytes,
    source_hashes: Mapping[str, str],
) -> None:
    branch = _git_text(["rev-parse", "--abbrev-ref", "HEAD"])
    head = _git_text(["rev-parse", "HEAD"])
    origin_master = _git_text(["rev-parse", "refs/remotes/origin/master"])
    if branch != "master" or head != origin_master or head != protocol_freeze_commit:
        raise RuntimeError(
            "formal replay requires freeze commit, master, and origin/master aligned"
        )
    for descendant in (head, origin_master):
        completed = subprocess.run(
            ["git", "merge-base", "--is-ancestor", protocol_freeze_commit, descendant],
            cwd=ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if completed.returncode != 0 or completed.stdout or completed.stderr:
            raise RuntimeError("protocol freeze commit is not merged into master")
    prereg_at_commit = _git_show_bytes(
        protocol_freeze_commit, contract.PREREGISTRATION_PATH
    )
    if prereg_at_commit != preregistration_payload:
        raise RuntimeError("freeze commit preregistration differs from working bytes")
    for name, path in contract.PROTOCOL_SOURCE_PATHS.items():
        payload = _git_show_bytes(protocol_freeze_commit, path)
        if contract.sha256_bytes(payload) != source_hashes[name]:
            raise RuntimeError(f"freeze commit protocol source differs: {name}")


def _git_text(arguments: Sequence[str]) -> str:
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


def _git_show_bytes(commit: str, path: str) -> bytes:
    completed = subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0 or completed.stderr:
        raise RuntimeError("unable to read protocol source from freeze commit")
    return completed.stdout


def _validate_formal_python_execution_mode() -> None:
    _require_exact_repo_path(Path.cwd(), ROOT, "working directory")
    _require_exact_repo_path(
        Path(sys.executable),
        ROOT / contract.FORMAL_PYTHON_PATH,
        "Python executable",
    )
    if (
        sys.flags.isolated != 1
        or sys.flags.dont_write_bytecode != 1
        or sys.flags.safe_path is not True
        or sys.pycache_prefix != "NUL"
    ):
        raise RuntimeError("formal replay requires -I -B -X pycache_prefix=NUL")


def _new_counters() -> dict[str, int | bool]:
    return {
        "fresh_base_load_attempts": 0,
        "fresh_base_loads": 0,
        "independent_adapter_load_attempts": 0,
        "independent_adapter_loads": 0,
        "full_eval_run_attempts": 0,
        "full_eval_runs": 0,
        "generate_attempts": 0,
        "generate_calls": 0,
        "training_runs": 0,
        "optimizer_steps": 0,
        "backward_calls": 0,
        "adapter_writes": 0,
        "network_attempts": 0,
        "network_used": False,
        "retry_count": 0,
    }


def _safe_exception_diagnostic(
    exc: BaseException,
) -> tuple[str, str | None, str | None]:
    exception_type = type(exc).__name__
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,95}", exception_type) is None:
        exception_type = "BaseException"
    if isinstance(exc, contract.MM003EvalRepeatabilityError):
        code = str(exc)
        if re.fullmatch(r"[A-Z][A-Z0-9_]{0,95}", code) is not None:
            return exception_type, code, None
        return exception_type, None, None
    if isinstance(exc, Exception):
        return upstream_runner._safe_exception_diagnostic(exc)
    return exception_type, None, None


class _OfflineSocketGuard:
    def __init__(self, counters: dict[str, int | bool]) -> None:
        self.counters = counters
        self.original_connect: object | None = None
        self.original_connect_ex: object | None = None
        self.original_create_connection: object | None = None

    def __enter__(self) -> _OfflineSocketGuard:
        self.original_connect = socket.socket.connect
        self.original_connect_ex = socket.socket.connect_ex
        self.original_create_connection = socket.create_connection

        def deny(*_args: object, **_kwargs: object) -> NoReturn:
            self.counters["network_attempts"] = (
                int(self.counters["network_attempts"]) + 1
            )
            raise RuntimeError("outbound network attempt blocked")

        setattr(socket.socket, "connect", deny)
        setattr(socket.socket, "connect_ex", deny)
        setattr(socket, "create_connection", deny)
        return self

    def __exit__(self, *_exc: object) -> None:
        assert self.original_connect is not None
        assert self.original_connect_ex is not None
        assert self.original_create_connection is not None
        setattr(socket.socket, "connect", self.original_connect)
        setattr(socket.socket, "connect_ex", self.original_connect_ex)
        setattr(socket, "create_connection", self.original_create_connection)


class _FrozenInputFileSet:
    """Hold authenticated model and Adapter files read-only across evaluation."""

    def __init__(
        self,
        *,
        model_snapshot: Path,
        model_receipts: Sequence[Mapping[str, Any]],
        adapter_receipts: Mapping[str, Mapping[str, Any]],
    ) -> None:
        self.model_root = Path(os.path.abspath(model_snapshot))
        self.adapter_root = Path(os.path.abspath(ROOT / contract.ADAPTER_ROOT))
        self.expected_model_receipts = [dict(item) for item in model_receipts]
        self.expected_adapter_receipts = {
            name: dict(receipt) for name, receipt in adapter_receipts.items()
        }
        self.model_receipts: list[dict[str, Any]] = []
        self.adapter_receipts: dict[str, dict[str, Any]] = {}
        self._handles: list[
            tuple[str, str, Path, Any, tuple[int, int, int, int, int]]
        ] = []
        self._roots: list[
            tuple[
                Path,
                tuple[int, int, int, int, int],
                list[tuple[Path, tuple[int, int, int, int, int, int]]],
                tuple[str, ...],
            ]
        ] = []

    def __enter__(self) -> _FrozenInputFileSet:
        try:
            self._open_root(
                kind="model",
                root=self.model_root,
                expected_names=tuple(
                    sorted(str(item["path"]) for item in self.expected_model_receipts)
                ),
            )
            self._open_root(
                kind="adapter",
                root=self.adapter_root,
                expected_names=tuple(
                    sorted(
                        Path(str(item["path"])).name
                        for item in self.expected_adapter_receipts.values()
                    )
                ),
            )
            self.model_receipts = [
                self._open_receipt(
                    kind="model",
                    name=str(receipt["path"]),
                    path=self.model_root / str(receipt["path"]),
                    expected=receipt,
                )
                for receipt in self.expected_model_receipts
            ]
            self.adapter_receipts = {
                name: self._open_receipt(
                    kind="adapter",
                    name=name,
                    path=ROOT / str(receipt["path"]),
                    expected=receipt,
                )
                for name, receipt in self.expected_adapter_receipts.items()
            }
            if (
                self.model_receipts != self.expected_model_receipts
                or self.adapter_receipts != self.expected_adapter_receipts
            ):
                raise RuntimeError("frozen input receipts differ from protocol")
            return self
        except BaseException:
            self.close()
            raise

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def verify(
        self,
    ) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
        model: list[dict[str, Any]] = []
        adapter: dict[str, dict[str, Any]] = {}
        for kind, name, path, handle, before_identity in self._handles:
            opened = os.fstat(handle.fileno())
            after = path.lstat()
            if (
                not stat.S_ISREG(after.st_mode)
                or result_validator._metadata_is_reparse(after)
                or after.st_nlink != 1
                or result_validator._handle_identity_signature(opened)
                != before_identity
                or result_validator._handle_identity_signature(after) != before_identity
            ):
                raise RuntimeError("frozen input file identity changed")
            receipt = {
                "path": (
                    name
                    if kind == "model"
                    else self.expected_adapter_receipts[name]["path"]
                ),
                "bytes": opened.st_size,
                "sha256": _hash_locked_handle(handle),
            }
            expected = (
                next(
                    item
                    for item in self.expected_model_receipts
                    if item["path"] == name
                )
                if kind == "model"
                else self.expected_adapter_receipts[name]
            )
            if receipt != expected:
                raise RuntimeError("frozen input file content changed")
            if kind == "model":
                model.append(receipt)
            else:
                adapter[name] = receipt
        for root, before_identity, parent_chain, expected_names in self._roots:
            after = root.lstat()
            if (
                not stat.S_ISDIR(after.st_mode)
                or result_validator._metadata_is_reparse(after)
                or result_validator._handle_identity_signature(after) != before_identity
                or tuple(sorted(path.name for path in root.iterdir())) != expected_names
            ):
                raise RuntimeError("frozen input directory identity changed")
            result_validator._recheck_repository_parent_chain(
                parent_chain, "frozen input", identity_only=True
            )
        if model != self.expected_model_receipts:
            raise RuntimeError("frozen model receipt order changed")
        return model, adapter

    def close(self) -> None:
        while self._handles:
            _kind, _name, _path, handle, _identity = self._handles.pop()
            handle.close()

    def _open_root(
        self, *, kind: str, root: Path, expected_names: tuple[str, ...]
    ) -> None:
        safe_root, parent_chain = result_validator._safe_repository_parent_chain(
            ROOT, root, f"repeatability {kind} root"
        )
        metadata = safe_root.lstat()
        observed_names = tuple(sorted(path.name for path in safe_root.iterdir()))
        if (
            not stat.S_ISDIR(metadata.st_mode)
            or result_validator._metadata_is_reparse(metadata)
            or observed_names != expected_names
        ):
            raise RuntimeError(f"unsafe or mismatched repeatability {kind} root")
        self._roots.append(
            (
                safe_root,
                result_validator._handle_identity_signature(metadata),
                parent_chain,
                expected_names,
            )
        )

    def _open_receipt(
        self,
        *,
        kind: str,
        name: str,
        path: Path,
        expected: Mapping[str, Any],
    ) -> dict[str, Any]:
        safe_path, parent_chain = result_validator._safe_repository_parent_chain(
            ROOT, path, f"repeatability {kind} file"
        )
        before = safe_path.lstat()
        if (
            not stat.S_ISREG(before.st_mode)
            or result_validator._metadata_is_reparse(before)
            or before.st_nlink != 1
            or before.st_size != expected.get("bytes")
        ):
            raise RuntimeError(f"unsafe repeatability {kind} file")
        handle = _open_locked_regular(safe_path)
        try:
            opened = os.fstat(handle.fileno())
            before_identity = result_validator._handle_identity_signature(before)
            if (
                result_validator._handle_identity_signature(opened) != before_identity
                or opened.st_nlink != 1
            ):
                raise RuntimeError(f"unstable repeatability {kind} file")
            receipt = {
                "path": expected["path"],
                "bytes": opened.st_size,
                "sha256": _hash_locked_handle(handle),
            }
            if not contract.canonical_json_bytes(
                receipt
            ) == contract.canonical_json_bytes(dict(expected)):
                raise RuntimeError(f"repeatability {kind} receipt mismatch")
            result_validator._recheck_repository_parent_chain(
                parent_chain, f"repeatability {kind} file", identity_only=True
            )
        except BaseException:
            handle.close()
            raise
        self._handles.append((kind, name, safe_path, handle, before_identity))
        return receipt


def _open_locked_regular(path: Path) -> Any:
    if os.name != "nt":
        handle = path.open("rb")
        try:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_SH)
        except BaseException:
            handle.close()
            raise
        return handle

    import ctypes
    import msvcrt

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_file = kernel32.CreateFileW
    create_file.argtypes = (
        ctypes.c_wchar_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
    )
    create_file.restype = ctypes.c_void_p
    raw_handle = create_file(
        str(path),
        0x80000000,  # GENERIC_READ
        0x00000001,  # FILE_SHARE_READ; deny write/delete while held
        None,
        3,  # OPEN_EXISTING
        0x00000080 | 0x00200000,  # NORMAL | OPEN_REPARSE_POINT
        None,
    )
    invalid_handle = ctypes.c_void_p(-1).value
    if raw_handle in (None, invalid_handle):
        raise OSError(ctypes.get_last_error(), f"unable to lock frozen input: {path}")
    try:
        descriptor = msvcrt.open_osfhandle(
            int(raw_handle), os.O_RDONLY | getattr(os, "O_BINARY", 0)
        )
    except BaseException:
        kernel32.CloseHandle(ctypes.c_void_p(raw_handle))
        raise
    return os.fdopen(descriptor, "rb")


def _hash_locked_handle(handle: Any) -> str:
    digest = hashlib.sha256()
    handle.seek(0)
    while True:
        chunk = handle.read(8 * 1024 * 1024)
        if not chunk:
            break
        digest.update(chunk)
    handle.seek(0)
    return f"sha256:{digest.hexdigest()}"


def _ensure_output_parent() -> None:
    parent = (ROOT / contract.RUN_OUTPUT_ROOT).parent
    if not os.path.lexists(parent):
        safe_parent, parent_chain = result_validator._safe_repository_parent_chain(
            ROOT, parent, "repeatability output parent"
        )
        os.mkdir(safe_parent)
        result_validator._recheck_repository_parent_chain(
            parent_chain, "repeatability output parent", identity_only=True
        )
    metadata = parent.lstat()
    if not stat.S_ISDIR(metadata.st_mode) or result_validator._metadata_is_reparse(
        metadata
    ):
        raise RuntimeError("unsafe repeatability output parent")


def _prepare_output_reservation(
    path: Path,
) -> tuple[Path, list[tuple[Path, tuple[int, int, int, int, int, int]]]]:
    safe_path, parent_chain = result_validator._safe_repository_parent_chain(
        ROOT, path, "repeatability output"
    )
    if os.path.lexists(safe_path):
        raise RuntimeError("repeatability output reservation already exists")
    result_validator._recheck_repository_parent_chain(
        parent_chain, "repeatability output"
    )
    return safe_path, parent_chain


class _ConsumedOutputDirectoryGuard:
    """Bind every output artifact to the directory this process consumed."""

    def __init__(
        self,
        reservation: tuple[
            Path, list[tuple[Path, tuple[int, int, int, int, int, int]]]
        ],
        *,
        initial_artifacts: Mapping[Path, bytes] | None = None,
    ) -> None:
        self.path, self.parent_chain = reservation
        self.initial_artifacts = {
            Path(os.path.abspath(path)): payload
            for path, payload in (initial_artifacts or {}).items()
        }
        self.identity: tuple[int, int, int] | None = None
        self.posix_descriptor: int | None = None
        self.windows_handle: int | None = None
        self.artifact_handles: dict[
            Path, tuple[Any, tuple[int, int, int, int, int], int, str]
        ] = {}

    @property
    def is_open(self) -> bool:
        if self.identity is None:
            return False
        if os.name == "nt":
            return self.windows_handle is not None
        return self.posix_descriptor is not None

    def open(self) -> None:
        if self.identity is not None:
            raise RuntimeError("consumed output guard already open")
        metadata = self.path.lstat()
        if not stat.S_ISDIR(metadata.st_mode) or result_validator._metadata_is_reparse(
            metadata
        ):
            raise RuntimeError("unsafe consumed repeatability output directory")
        identity = (metadata.st_dev, metadata.st_ino, metadata.st_mode)
        try:
            if os.name == "nt":
                windows_handle = _open_locked_directory_windows(self.path)
                self.windows_handle = windows_handle
            else:
                flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
                posix_descriptor = os.open(self.path, flags)
                self.posix_descriptor = posix_descriptor
                opened = os.fstat(posix_descriptor)
                if (opened.st_dev, opened.st_ino, opened.st_mode) != identity:
                    raise RuntimeError("unstable consumed output directory")
            self.identity = identity
            for path, payload in self.initial_artifacts.items():
                self._track_artifact_without_verify(path, payload)
            self.verify()
        except BaseException:
            self.close()
            raise

    def verify(self) -> None:
        if self.identity is None:
            raise RuntimeError("consumed output guard is not open")
        metadata = self.path.lstat()
        if (
            not stat.S_ISDIR(metadata.st_mode)
            or result_validator._metadata_is_reparse(metadata)
            or (metadata.st_dev, metadata.st_ino, metadata.st_mode) != self.identity
        ):
            raise RuntimeError("consumed output directory identity changed")
        if self.posix_descriptor is not None:
            opened = os.fstat(self.posix_descriptor)
            if (opened.st_dev, opened.st_ino, opened.st_mode) != self.identity:
                raise RuntimeError("consumed output handle identity changed")
        elif self.windows_handle is None:
            raise RuntimeError("consumed output directory lock is absent")
        for path, (
            handle,
            before_identity,
            expected_bytes,
            expected_sha256,
        ) in self.artifact_handles.items():
            opened = os.fstat(handle.fileno())
            after = path.lstat()
            if (
                result_validator._handle_identity_signature(opened) != before_identity
                or result_validator._handle_identity_signature(after) != before_identity
                or after.st_nlink != 1
                or result_validator._metadata_is_reparse(after)
                or opened.st_size != expected_bytes
                or _hash_locked_handle(handle) != expected_sha256
            ):
                raise RuntimeError("consumed output artifact changed")
        observed_names = tuple(sorted(item.name for item in self.path.iterdir()))
        expected_names = tuple(sorted(item.name for item in self.artifact_handles))
        if observed_names != expected_names:
            raise RuntimeError("consumed output artifact set changed")
        result_validator._recheck_repository_parent_chain(
            self.parent_chain, "repeatability output", identity_only=True
        )

    def close(self) -> None:
        while self.artifact_handles:
            _path, (handle, _identity, _bytes, _sha256) = (
                self.artifact_handles.popitem()
            )
            handle.close()
        if self.posix_descriptor is not None:
            os.close(self.posix_descriptor)
            self.posix_descriptor = None
        if self.windows_handle is not None:
            import ctypes

            ctypes.WinDLL("kernel32", use_last_error=True).CloseHandle(
                ctypes.c_void_p(self.windows_handle)
            )
            self.windows_handle = None
        self.identity = None

    def track_artifact(self, path: Path, payload: bytes) -> None:
        self._track_artifact_without_verify(path, payload)
        self.verify()

    def _track_artifact_without_verify(self, path: Path, payload: bytes) -> None:
        safe_path = Path(os.path.abspath(path))
        if safe_path.parent != self.path:
            raise RuntimeError("tracked artifact is outside consumed directory")
        if safe_path in self.artifact_handles:
            return
        before = safe_path.lstat()
        if (
            not stat.S_ISREG(before.st_mode)
            or result_validator._metadata_is_reparse(before)
            or before.st_nlink != 1
            or before.st_size != len(payload)
        ):
            raise RuntimeError("unsafe consumed output artifact")
        handle = _open_locked_regular(safe_path)
        try:
            opened = os.fstat(handle.fileno())
            before_identity = result_validator._handle_identity_signature(before)
            expected_sha256 = contract.sha256_bytes(payload)
            if (
                result_validator._handle_identity_signature(opened) != before_identity
                or opened.st_nlink != 1
                or _hash_locked_handle(handle) != expected_sha256
            ):
                raise RuntimeError("unstable consumed output artifact")
            self.artifact_handles[safe_path] = (
                handle,
                before_identity,
                len(payload),
                expected_sha256,
            )
        except BaseException:
            handle.close()
            raise


def _open_locked_directory_windows(path: Path) -> int:
    import ctypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_file = kernel32.CreateFileW
    create_file.argtypes = (
        ctypes.c_wchar_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
    )
    create_file.restype = ctypes.c_void_p
    raw_handle = create_file(
        str(path),
        0x00000080,  # FILE_READ_ATTRIBUTES
        0x00000001 | 0x00000002,  # share read/write, deny delete/rename
        None,
        3,
        0x02000000 | 0x00200000,  # BACKUP_SEMANTICS | OPEN_REPARSE_POINT
        None,
    )
    invalid_handle = ctypes.c_void_p(-1).value
    if raw_handle in (None, invalid_handle):
        raise OSError(
            ctypes.get_last_error(), f"unable to lock consumed output: {path}"
        )
    return int(raw_handle)


def _write_output_artifact(
    guard: _ConsumedOutputDirectoryGuard, path: Path, payload: bytes
) -> None:
    guard.verify()
    if Path(os.path.abspath(path)).parent != guard.path:
        raise RuntimeError("output artifact is outside consumed directory")
    result_validator._write_exclusive(ROOT, path, payload)
    guard.track_artifact(path, payload)
    guard.verify()


def _recover_exclusive_artifact(
    guard: _ConsumedOutputDirectoryGuard,
    path: Path,
    intended_payload: bytes | None,
    label: str,
) -> bytes | None:
    if not os.path.lexists(path):
        return None
    if intended_payload is None:
        raise RuntimeError(f"unexpected {label} exists after consumed failure")
    observed = _read_bounded_regular(
        path,
        label=f"recovered {label}",
        max_bytes=max(len(intended_payload), 1),
    )
    if observed != intended_payload:
        raise RuntimeError(f"recovered {label} differs from intended bytes")
    guard.track_artifact(path, observed)
    return observed


def _observe_attempt_owner(
    path: Path, intended_payload: bytes, *, strict: bool
) -> bytes | None:
    if not os.path.lexists(path):
        return None
    try:
        observed = _read_bounded_regular(
            path,
            label="repeatability attempt owner",
            max_bytes=max(len(intended_payload), 1),
        )
    except Exception:
        if strict:
            raise
        return None
    if observed != intended_payload:
        if strict:
            raise RuntimeError("repeatability attempt owner differs from this process")
        return None
    return observed


def _success_summary(evidence: Mapping[str, Any]) -> dict[str, Any]:
    comparison = evidence["comparison"]
    return {
        "classification": evidence["classification"],
        "formal_gate_passed": evidence["formal_gate_passed"],
        "next_gate": evidence["next_gate"],
        "raw_outputs_exact": comparison["raw_outputs"]["exact"],
        "compiled_predictions_exact": comparison["compiled_predictions"]["exact"],
        "metrics_exact": comparison["metrics"]["exact"],
        "valid": evidence["formal_gate_passed"],
    }


def _read_bounded_regular(path: Path, *, label: str, max_bytes: int) -> bytes:
    safe_path, parent_chain = result_validator._safe_repository_parent_chain(
        ROOT, path, label
    )
    before = safe_path.lstat()
    if (
        not stat.S_ISREG(before.st_mode)
        or result_validator._metadata_is_reparse(before)
        or before.st_nlink != 1
        or before.st_size > max_bytes
    ):
        raise RuntimeError(f"unsafe or oversized {label}")
    with safe_path.open("rb") as handle:
        opened = os.fstat(handle.fileno())
        if result_validator._handle_identity_signature(
            before
        ) != result_validator._handle_identity_signature(opened):
            raise RuntimeError(f"unstable {label}")
        payload = handle.read(max_bytes + 1)
        after_handle = os.fstat(handle.fileno())
    after = safe_path.lstat()
    if (
        len(payload) != before.st_size
        or result_validator._stat_signature(before)
        != result_validator._stat_signature(after)
        or result_validator._handle_identity_signature(opened)
        != result_validator._handle_identity_signature(after_handle)
        or result_validator._handle_identity_signature(after_handle)
        != result_validator._handle_identity_signature(after)
        or after_handle.st_nlink != 1
        or after.st_nlink != 1
        or result_validator._metadata_is_reparse(after)
    ):
        raise RuntimeError(f"unstable {label}")
    result_validator._recheck_repository_parent_chain(parent_chain, label)
    return payload


def _require_exact_repo_path(observed: Path, expected: Path, label: str) -> None:
    observed_absolute = Path(os.path.abspath(observed))
    expected_absolute = Path(os.path.abspath(expected))
    if os.path.normcase(str(observed_absolute)) != os.path.normcase(
        str(expected_absolute)
    ):
        raise RuntimeError(f"{label} differs from frozen protocol")


def _parse_object(payload: bytes, location: str) -> dict[str, Any]:
    value = contract.parse_strict_json_bytes(payload, location=location)
    if not isinstance(value, dict):
        raise RuntimeError(f"expected object at {location}")
    if contract.artifact_json_bytes(value) != payload:
        raise RuntimeError(f"noncanonical JSON at {location}")
    return value


if __name__ == "__main__":
    raise SystemExit(main())
