"""Prepare or execute the frozen MM-004 hard-negative model evaluation."""

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
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SRC))

from fullcycle_bridge import mm004_hard_negative_generation as generation  # noqa: E402
from fullcycle_bridge import (  # noqa: E402
    mm004_hard_negative_model_evaluation as contract,
)
from scripts import run_mm003_multimodal_gui_action_baseline as base_runner  # noqa: E402
from scripts import run_mm003_post_training_eval_repeatability as repeat_runner  # noqa: E402
from scripts import run_mm003_qlora_post_training_v2 as upstream_runner  # noqa: E402
from scripts import run_mm004_hard_negative_generation as generation_runner  # noqa: E402
from scripts import validate_mm003_post_training_v2_result as result_validator  # noqa: E402

MAX_JSON_BYTES = 4 * 1024 * 1024
MAX_SOURCE_BYTES = 4 * 1024 * 1024


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("--freeze-status", choices=("draft", "frozen"), required=True)
    prepare.add_argument("--check", action="store_true")

    run = subparsers.add_parser("run")
    run.add_argument("--protocol-freeze-commit", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "prepare":
        result = prepare_protocol(
            freeze_status=str(args.freeze_status), check=bool(args.check)
        )
    else:
        result = execute_frozen_protocol(
            protocol_freeze_commit=str(args.protocol_freeze_commit)
        )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


def prepare_protocol(*, freeze_status: str, check: bool) -> dict[str, Any]:
    context = load_authenticated_context()
    receipts = source_receipts()
    preregistration = contract.expected_preregistration(
        freeze_status=freeze_status,
        generation_evidence=context["generation_evidence"],
        candidate_repeatability_protocol=context["candidate_repeatability_protocol"],
        candidate_result_review=context["candidate_result_review"],
        records=context["records"],
        source_receipts=receipts,
    )
    payload = contract.artifact_json_bytes(preregistration)
    output_path = ROOT / contract.PREREGISTRATION_PATH
    if check:
        observed = repeat_runner._read_bounded_regular(
            output_path,
            label="MM-004 model-evaluation preregistration",
            max_bytes=MAX_JSON_BYTES,
        )
        if observed != payload:
            raise RuntimeError("MM-004 model-evaluation preregistration is stale")
    else:
        result_validator._write_exclusive(ROOT, output_path, payload)
    return {
        "case_count": contract.EXPECTED_RECORDS,
        "freeze_status": freeze_status,
        "next_gate": contract.EXECUTION_GATE_ID,
        "protocol_sources": len(receipts),
        "sha256": contract.sha256_bytes(payload),
        "valid": True,
    }


def execute_frozen_protocol(*, protocol_freeze_commit: str) -> dict[str, Any]:
    """Execute one read-only, offline, owner-marked evaluation attempt."""

    _validate_commit(protocol_freeze_commit)
    _validate_formal_python_execution_mode()
    output_dir = ROOT / contract.RUN_OUTPUT_ROOT
    if os.path.lexists(output_dir):
        raise RuntimeError("formal MM-004 evaluation output must be absent")

    context = load_authenticated_context()
    receipts = source_receipts()
    preregistration_path = ROOT / contract.PREREGISTRATION_PATH
    preregistration_payload = repeat_runner._read_bounded_regular(
        preregistration_path,
        label="MM-004 model-evaluation preregistration",
        max_bytes=MAX_JSON_BYTES,
    )
    preregistration_raw = contract.parse_strict_json_bytes(
        preregistration_payload, location="$.preregistration"
    )
    preregistration = contract.validate_preregistration(
        preregistration_raw,
        generation_evidence=context["generation_evidence"],
        candidate_repeatability_protocol=context["candidate_repeatability_protocol"],
        candidate_result_review=context["candidate_result_review"],
        records=context["records"],
        source_receipts=receipts,
    )
    if contract.artifact_json_bytes(preregistration) != preregistration_payload:
        raise RuntimeError("MM-004 model-evaluation preregistration is not canonical")
    _validate_protocol_freeze_commit(
        protocol_freeze_commit=protocol_freeze_commit,
        preregistration_payload=preregistration_payload,
        source_receipts=receipts,
        generation_output_receipts=context["generation_evidence"]["outputs"],
    )
    upstream_runner._validate_local_dependency_wheel()

    model_receipts = preregistration["candidate"]["model_files"]
    with repeat_runner._FrozenInputFileSet(
        model_snapshot=ROOT / contract.MODEL_SNAPSHOT_ROOT,
        model_receipts=model_receipts,
        adapter_receipts=contract.ADAPTER_RECEIPTS,
    ) as frozen_model, _FrozenGeneratedInputSet(
        context["generation_evidence"]["outputs"]
    ) as frozen_generation:
        if frozen_generation.payloads != context["generation_output_payloads"]:
            raise RuntimeError("frozen generation inputs differ from authenticated context")
        repeat_runner._ensure_output_parent()
        reservation = repeat_runner._prepare_output_reservation(output_dir)
        attempt_id = secrets.token_hex(32)
        owner_payload = contract.artifact_json_bytes(
            contract.build_attempt_owner(
                protocol_freeze_commit=protocol_freeze_commit,
                preregistration_payload=preregistration_payload,
                attempt_id=attempt_id,
            )
        )
        owner_staging = output_dir.with_name(f".{output_dir.name}.owner-{attempt_id}")
        owner_staging_reservation = repeat_runner._prepare_output_reservation(
            owner_staging
        )
        attempt_consumed = False
        output_guard: repeat_runner._ConsumedOutputDirectoryGuard | None = None
        owner_written: bytes | None = None
        candidate_intended: bytes | None = None
        candidate_written: bytes | None = None
        predictions_intended: bytes | None = None
        predictions_written: bytes | None = None
        evidence_intended: bytes | None = None
        evidence_written: bytes | None = None
        evidence_object: dict[str, Any] | None = None
        completed_record_ids: list[str] = []
        counters = _new_counters()
        stage = "output_claim"
        started = 0.0
        try:
            os.mkdir(owner_staging_reservation[0])
            result_validator._write_exclusive(
                ROOT,
                owner_staging / Path(contract.ATTEMPT_OWNER_PATH).name,
                owner_payload,
            )
            os.rename(owner_staging, reservation[0])
            attempt_consumed = True
            owner_written = owner_payload
            output_guard = repeat_runner._ConsumedOutputDirectoryGuard(
                reservation,
                initial_artifacts={ROOT / contract.ATTEMPT_OWNER_PATH: owner_written},
            )
            output_guard.open()
            counters["run_attempts"] = 1
            started = time.perf_counter()

            stage = "model_load"
            upstream_runner._enable_offline_execution()
            with repeat_runner._OfflineSocketGuard(counters):
                dependencies = repeat_runner._load_eval_dependencies()
                torch = dependencies[0]
                environment = upstream_runner.observed_environment(torch)
                if environment != preregistration["candidate"]["environment"]:
                    raise RuntimeError("formal MM-004 evaluation environment mismatch")
                torch.cuda.empty_cache()
                torch.cuda.reset_peak_memory_stats()
                stage = "generation"
                cases = _run_model_evaluation(
                    dependencies=dependencies,
                    records=context["records"],
                    image_payloads=frozen_generation.payloads,
                    counters=counters,
                    completed_record_ids=completed_record_ids,
                )
                frozen_model.verify()
                frozen_generation.verify()
                torch.cuda.synchronize()
                resources = {
                    "elapsed_seconds": time.perf_counter() - started,
                    "peak_gpu_allocated_bytes": int(torch.cuda.max_memory_allocated()),
                    "peak_gpu_reserved_bytes": int(torch.cuda.max_memory_reserved()),
                }

            stage = "candidate_persistence"
            candidate = contract.build_evaluation_candidate(
                protocol_freeze_commit=protocol_freeze_commit,
                preregistration_payload=preregistration_payload,
                cases=cases,
                records=context["records"],
                execution=counters,
                resources=resources,
            )
            candidate_intended = contract.artifact_json_bytes(candidate)
            repeat_runner._write_output_artifact(
                output_guard,
                ROOT / contract.EVALUATION_CANDIDATE_PATH,
                candidate_intended,
            )
            candidate_written = candidate_intended

            stage = "scoring"
            predictions = contract.build_predictions(candidate)
            contract.score_case_results(context["records"], cases)
            predictions_intended = contract.artifact_json_bytes(predictions)
            stage = "predictions_persistence"
            repeat_runner._write_output_artifact(
                output_guard,
                ROOT / contract.PREDICTIONS_PATH,
                predictions_intended,
            )
            predictions_written = predictions_intended

            stage = "evidence_persistence"
            evidence_object = contract.build_evidence(
                protocol_freeze_commit=protocol_freeze_commit,
                preregistration_payload=preregistration_payload,
                attempt_owner_payload=owner_written,
                evaluation_candidate_payload=candidate_written,
                predictions_payload=predictions_written,
                records=context["records"],
                captured_at_utc=datetime.now(timezone.utc).isoformat(),
            )
            evidence_intended = contract.artifact_json_bytes(evidence_object)
            repeat_runner._write_output_artifact(
                output_guard, ROOT / contract.EVIDENCE_PATH, evidence_intended
            )
            evidence_written = evidence_intended
            return _success_summary(evidence_object)
        except BaseException as exc:
            if attempt_consumed and owner_written is None:
                owner_written = repeat_runner._observe_attempt_owner(
                    ROOT / contract.ATTEMPT_OWNER_PATH, owner_payload, strict=True
                )
            if attempt_consumed and (
                output_guard is None or not output_guard.is_open
            ):
                if owner_written is None:
                    raise RuntimeError("consumed attempt has no authenticated owner") from exc
                output_guard = repeat_runner._ConsumedOutputDirectoryGuard(
                    reservation,
                    initial_artifacts={ROOT / contract.ATTEMPT_OWNER_PATH: owner_written},
                )
                output_guard.open()
            if attempt_consumed:
                if output_guard is None:
                    raise RuntimeError("consumed attempt has no output guard") from exc
                if candidate_written is None:
                    candidate_written = repeat_runner._recover_exclusive_artifact(
                        output_guard,
                        ROOT / contract.EVALUATION_CANDIDATE_PATH,
                        candidate_intended,
                        "MM-004 evaluation candidate",
                    )
                if predictions_written is None:
                    predictions_written = repeat_runner._recover_exclusive_artifact(
                        output_guard,
                        ROOT / contract.PREDICTIONS_PATH,
                        predictions_intended,
                        "MM-004 predictions",
                    )
                if evidence_written is None:
                    evidence_written = repeat_runner._recover_exclusive_artifact(
                        output_guard,
                        ROOT / contract.EVIDENCE_PATH,
                        evidence_intended,
                        "MM-004 evidence",
                    )
            if evidence_written is not None:
                if evidence_object is None:
                    raise RuntimeError(
                        "durable evidence exists without authenticated evidence object"
                    ) from exc
                return _success_summary(evidence_object)
            if attempt_consumed:
                if owner_written is None or output_guard is None:
                    raise RuntimeError("consumed attempt cannot persist failure") from exc
                failure = contract.build_failure(
                    protocol_freeze_commit=protocol_freeze_commit,
                    preregistration_payload=preregistration_payload,
                    attempt_owner_payload=owner_written,
                    stage=stage,
                    exception_type=_safe_exception_type(exc),
                    counters=counters,
                    completed_record_ids=completed_record_ids,
                    evaluation_candidate_payload=candidate_written,
                    predictions_payload=predictions_written,
                )
                repeat_runner._write_output_artifact(
                    output_guard,
                    ROOT / contract.FAILURE_PATH,
                    contract.artifact_json_bytes(failure),
                )
            raise
        finally:
            if output_guard is not None:
                output_guard.close()
            gc.collect()


def load_authenticated_context() -> dict[str, Any]:
    payloads = {
        name: _read_expected_receipt(receipt, label=name)
        for name, receipt in contract.CONTEXT_RECEIPTS.items()
    }
    parent_protocol = _parse_object(payloads["parent_protocol"], "$.parent_protocol")
    generation_preregistration = _parse_object(
        payloads["generation_preregistration"], "$.generation_preregistration"
    )
    generation_evidence = _parse_object(
        payloads["generation_evidence"], "$.generation_evidence"
    )
    candidate_repeatability_protocol = _parse_object(
        payloads["candidate_repeatability_protocol"],
        "$.candidate_repeatability_protocol",
    )
    candidate_result_review = _parse_object(
        payloads["candidate_result_review"], "$.candidate_result_review"
    )

    generation.validate_preregistration(
        generation_preregistration,
        source_receipts=generation_runner.source_receipts(),
        parent_protocol_receipt=generation_runner.parent_protocol_receipt(),
    )
    planned_outputs = _mapping(
        generation_preregistration.get("planned_outputs"),
        "$.generation_preregistration.planned_outputs",
    )
    observed_outputs = _mapping(
        generation_evidence.get("outputs"), "$.generation_evidence.outputs"
    )
    if planned_outputs != observed_outputs:
        raise RuntimeError("generation output receipts differ across evidence")
    _validate_generation_output_tree(set(str(path) for path in planned_outputs))
    generation_output_payloads = {
        str(path): _read_expected_receipt(
            _mapping(receipt, f"$.planned_outputs.{path}"), label=f"output {path}"
        )
        for path, receipt in planned_outputs.items()
    }
    exclusions = _mapping(
        parent_protocol.get("exclusion_registry"), "$.parent_protocol.exclusion_registry"
    )
    generation.validate_output_payloads(
        generation_output_payloads,
        preregistration=generation_preregistration,
        exclusions=exclusions,
    )
    generation.validate_evidence(
        generation_evidence,
        protocol_freeze_commit=contract.GENERATION_PROTOCOL_FREEZE_COMMIT,
        preregistration_payload=payloads["generation_preregistration"],
        output_payloads=generation_output_payloads,
        exclusions=exclusions,
    )

    train = _parse_object(
        generation_output_payloads[generation.TRAIN_PATH], "$.generation_train"
    )
    validation = _parse_object(
        generation_output_payloads[generation.VALIDATION_PATH],
        "$.generation_validation",
    )
    records = [
        *(_object_list(train.get("records"), "$.generation_train.records")),
        *(
            _object_list(
                validation.get("records"), "$.generation_validation.records"
            )
        ),
    ]
    for name, receipt in contract.ADAPTER_RECEIPTS.items():
        _read_expected_receipt(receipt, label=f"adapter {name}")
    contract.expected_preregistration(
        freeze_status="frozen",
        generation_evidence=generation_evidence,
        candidate_repeatability_protocol=candidate_repeatability_protocol,
        candidate_result_review=candidate_result_review,
        records=records,
        source_receipts=source_receipts(),
    )
    return {
        "generation_evidence": generation_evidence,
        "generation_output_payloads": generation_output_payloads,
        "candidate_repeatability_protocol": candidate_repeatability_protocol,
        "candidate_result_review": candidate_result_review,
        "records": records,
    }


def source_receipts() -> dict[str, dict[str, Any]]:
    return {
        name: _receipt(
            path,
            repeat_runner._read_bounded_regular(
                ROOT / path,
                label=f"MM-004 model-evaluation source {name}",
                max_bytes=MAX_SOURCE_BYTES,
            ),
        )
        for name, path in sorted(contract.PROTOCOL_SOURCE_PATHS.items())
    }


def _run_model_evaluation(
    *,
    dependencies: tuple[Any, ...],
    records: Sequence[Mapping[str, Any]],
    image_payloads: Mapping[str, bytes],
    counters: dict[str, int],
    completed_record_ids: list[str],
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
        ROOT / contract.ADAPTER_ROOT,
        is_trainable=False,
        local_files_only=True,
    ).eval()
    counters["independent_adapter_loads"] = 1
    model.config.use_cache = True
    if model.training is not False or any(
        parameter.requires_grad for parameter in model.parameters()
    ):
        raise RuntimeError("MM-004 evaluation model has trainable state")

    cases: list[dict[str, Any]] = []
    with torch.inference_mode():
        for record in records:
            observation = _mapping(record.get("observation"), "$.record.observation")
            image_path = str(observation.get("image_path"))
            image_payload = image_payloads.get(image_path)
            if not isinstance(image_payload, bytes):
                raise RuntimeError("authenticated MM-004 image payload missing")
            counters["generate_attempts"] += 1
            image = image_class.open(io.BytesIO(image_payload)).convert("RGB")
            try:
                messages: list[dict[str, Any]] = [
                    {"role": "system", "content": contract.SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": [
                            {"type": "image", "image": image},
                            {"type": "text", "text": contract.build_user_prompt(record)},
                        ],
                    },
                ]
                torch.cuda.synchronize()
                started = time.perf_counter()
                raw_output, generated_tokens = base_runner._generate_one(
                    torch=torch,
                    model=model,
                    processor=processor,
                    messages=messages,
                    images=[image],
                    max_new_tokens=contract.MAX_NEW_TOKENS,
                )
                counters["generate_calls"] += 1
                torch.cuda.synchronize()
                case = contract.build_case_result(
                    record=record,
                    raw_output=raw_output,
                    generated_tokens=generated_tokens,
                    latency_seconds=time.perf_counter() - started,
                )
                cases.append(case)
                completed_record_ids.append(str(record["record_id"]))
            finally:
                image.close()
    if counters != contract.expected_execution_counters():
        raise RuntimeError("MM-004 evaluation counters differ from frozen protocol")
    del model, base_model, processor
    gc.collect()
    torch.cuda.empty_cache()
    return cases


def _validate_protocol_freeze_commit(
    *,
    protocol_freeze_commit: str,
    preregistration_payload: bytes,
    source_receipts: Mapping[str, Mapping[str, Any]],
    generation_output_receipts: Mapping[str, Mapping[str, Any]],
) -> None:
    branch = _git_text("rev-parse", "--abbrev-ref", "HEAD")
    head = _git_text("rev-parse", "HEAD")
    origin_master = _git_text("rev-parse", "refs/remotes/origin/master")
    if branch != "master" or head != origin_master or head != protocol_freeze_commit:
        raise RuntimeError(
            "formal MM-004 evaluation requires aligned merged master freeze commit"
        )
    tracked: dict[str, Mapping[str, Any]] = {
        contract.PREREGISTRATION_PATH: _receipt(
            contract.PREREGISTRATION_PATH, preregistration_payload
        )
    }
    tracked.update({str(item["path"]): item for item in source_receipts.values()})
    tracked.update(
        {str(item["path"]): item for item in contract.CONTEXT_RECEIPTS.values()}
    )
    tracked.update(
        {str(item["path"]): item for item in contract.ADAPTER_RECEIPTS.values()}
    )
    tracked.update(
        {str(path): receipt for path, receipt in generation_output_receipts.items()}
    )
    for path, expected in sorted(tracked.items()):
        observed = _receipt(path, _git_show_bytes(protocol_freeze_commit, path))
        if observed != dict(expected):
            raise RuntimeError(f"freeze commit tracked receipt differs: {path}")


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
        raise RuntimeError("formal MM-004 evaluation requires isolated Python args")


def _new_counters() -> dict[str, int]:
    return {key: 0 for key in contract.expected_execution_counters()}


def _read_expected_receipt(
    receipt: Mapping[str, Any], *, label: str
) -> bytes:
    path = str(receipt.get("path"))
    expected_bytes = receipt.get("bytes")
    expected_sha256 = receipt.get("sha256")
    if type(expected_bytes) is not int or expected_bytes <= 0:
        raise RuntimeError(f"invalid expected byte count for {label}")
    payload = bytes(
        repeat_runner._read_bounded_regular(
            ROOT / path,
            label=label,
            max_bytes=max(expected_bytes, 1),
        )
    )
    if _receipt(path, payload) != {
        "path": path,
        "bytes": expected_bytes,
        "sha256": expected_sha256,
    }:
        raise RuntimeError(f"receipt mismatch for {label}")
    return payload


def _validate_generation_output_tree(expected_paths: set[str]) -> None:
    output_root = ROOT / generation.OUTPUT_ROOT
    safe_root, parent_chain = result_validator._safe_repository_parent_chain(
        ROOT, output_root, "MM-004 generation output root"
    )
    metadata = safe_root.lstat()
    if not stat.S_ISDIR(metadata.st_mode) or result_validator._metadata_is_reparse(
        metadata
    ):
        raise RuntimeError("unsafe MM-004 generation output root")
    observed: set[str] = set()
    for path in safe_root.rglob("*"):
        item = path.lstat()
        if result_validator._metadata_is_reparse(item):
            raise RuntimeError("MM-004 generation output contains a reparse point")
        if stat.S_ISDIR(item.st_mode):
            continue
        if not stat.S_ISREG(item.st_mode) or item.st_nlink != 1:
            raise RuntimeError("MM-004 generation output contains an unsafe file")
        observed.add(path.relative_to(ROOT).as_posix())
    if observed != expected_paths:
        raise RuntimeError("MM-004 generation output file set differs")
    result_validator._recheck_repository_parent_chain(
        parent_chain, "MM-004 generation output root"
    )


class _FrozenGeneratedInputSet:
    """Lock every registered generated input against write/delete during evaluation."""

    def __init__(self, receipts: Mapping[str, Mapping[str, Any]]) -> None:
        self.receipts = {str(path): dict(value) for path, value in receipts.items()}
        self.payloads: dict[str, bytes] = {}
        self.handles: list[
            tuple[Path, Any, tuple[int, int, int, int, int], Mapping[str, Any]]
        ] = []
        self.tree_signature: dict[str, tuple[int, int, int, int, int, int]] = {}

    def __enter__(self) -> _FrozenGeneratedInputSet:
        try:
            _validate_generation_output_tree(set(self.receipts))
            self.tree_signature = self._observe_tree()
            for relative, expected in sorted(self.receipts.items()):
                path, parent_chain = result_validator._safe_repository_parent_chain(
                    ROOT, ROOT / relative, f"frozen generation input {relative}"
                )
                before = path.lstat()
                if (
                    not stat.S_ISREG(before.st_mode)
                    or result_validator._metadata_is_reparse(before)
                    or before.st_nlink != 1
                ):
                    raise RuntimeError("unsafe frozen generation input")
                handle = repeat_runner._open_locked_regular(path)
                opened = os.fstat(handle.fileno())
                identity = result_validator._handle_identity_signature(before)
                if result_validator._handle_identity_signature(opened) != identity:
                    handle.close()
                    raise RuntimeError("unstable frozen generation input")
                handle.seek(0)
                payload = handle.read()
                handle.seek(0)
                if _receipt(relative, payload) != expected:
                    handle.close()
                    raise RuntimeError("frozen generation input receipt mismatch")
                result_validator._recheck_repository_parent_chain(
                    parent_chain, f"frozen generation input {relative}"
                )
                self.handles.append((path, handle, identity, expected))
                self.payloads[relative] = payload
            self.verify()
            return self
        except BaseException:
            self.close()
            raise

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def verify(self) -> None:
        _validate_generation_output_tree(set(self.receipts))
        if self._observe_tree() != self.tree_signature:
            raise RuntimeError("frozen generation input tree changed")
        for path, handle, identity, expected in self.handles:
            opened = os.fstat(handle.fileno())
            after = path.lstat()
            if (
                result_validator._handle_identity_signature(opened) != identity
                or result_validator._handle_identity_signature(after) != identity
                or after.st_nlink != 1
                or result_validator._metadata_is_reparse(after)
            ):
                raise RuntimeError("frozen generation input identity changed")
            handle.seek(0)
            payload = handle.read()
            handle.seek(0)
            relative = path.relative_to(ROOT).as_posix()
            if _receipt(relative, payload) != expected:
                raise RuntimeError("frozen generation input content changed")

    def close(self) -> None:
        while self.handles:
            _path, handle, _identity, _expected = self.handles.pop()
            handle.close()

    @staticmethod
    def _observe_tree() -> dict[str, tuple[int, int, int, int, int, int]]:
        root = ROOT / generation.OUTPUT_ROOT
        return {
            path.relative_to(ROOT).as_posix(): result_validator._stat_signature(
                path.lstat()
            )
            for path in [root, *sorted(root.rglob("*"))]
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
        raise RuntimeError("unable to validate merged MM-004 protocol state")
    value = completed.stdout.strip()
    if not value:
        raise RuntimeError("empty merged MM-004 protocol state")
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
        raise RuntimeError(f"unable to read frozen tracked path: {path}")
    return completed.stdout


def _receipt(path: str, payload: bytes) -> dict[str, Any]:
    return {
        "path": path,
        "bytes": len(payload),
        "sha256": contract.sha256_bytes(payload),
    }


def _parse_object(payload: bytes, location: str) -> dict[str, Any]:
    value = contract.parse_strict_json_bytes(payload, location=location)
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object at {location}")
    return value


def _mapping(value: object, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise RuntimeError(f"expected object at {location}")
    return value


def _object_list(value: object, location: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, list) or any(not isinstance(item, Mapping) for item in value):
        raise RuntimeError(f"expected object list at {location}")
    return value


def _validate_commit(value: str) -> None:
    if len(value) != 40 or any(item not in "0123456789abcdef" for item in value):
        raise RuntimeError("protocol freeze commit must be lowercase 40-hex")


def _safe_exception_type(exc: BaseException) -> str:
    value = type(exc).__name__
    if not value.isidentifier() or len(value) > 128:
        return "BaseException"
    return value


def _success_summary(evidence: Mapping[str, Any]) -> dict[str, Any]:
    metrics = _mapping(evidence.get("metrics"), "$.evidence.metrics")
    overall = _mapping(metrics.get("overall_accuracy"), "$.metrics.overall_accuracy")
    return {
        "classification": evidence["classification"],
        "formal_gate_passed": evidence["formal_gate_passed"],
        "overall_accuracy": overall["value"],
        "record_count": metrics["record_count"],
        "next_gate": evidence["next_gate"],
        "valid": evidence["formal_gate_passed"],
    }


if __name__ == "__main__":
    raise SystemExit(main())
