"""Execute the frozen MM-005 Browser Research model evaluation once."""

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

from fullcycle_bridge import (  # noqa: E402
    mm004_hard_negative_model_evaluation as candidate_protocol,
)
from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_adapter_verifier as adapter_verifier,
)
from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_data as data_contract,
)
from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_adapter_verifier_implementation as implementation_contract,
)
from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_model_evaluation as contract,
)
from scripts import (  # noqa: E402
    prepare_mm005_browser_research_model_evaluation as protocol_builder,
)
from scripts import run_mm003_multimodal_gui_action_baseline as base_runner  # noqa: E402
from scripts import (  # noqa: E402
    run_mm003_post_training_eval_repeatability as repeat_runner,
)
from scripts import run_mm003_qlora_post_training_v2 as upstream_runner  # noqa: E402
from scripts import validate_mm003_post_training_v2_result as file_validator  # noqa: E402

MAX_JSON_BYTES = 4 * 1024 * 1024


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
    """Consume one owner-marked, offline, read-only formal evaluation attempt."""

    _validate_commit(protocol_freeze_commit)
    _validate_formal_python_execution_mode()
    output_dir = ROOT / contract.RUN_OUTPUT_ROOT
    if os.path.lexists(output_dir):
        raise RuntimeError("formal MM-005 evaluation output must be absent")

    inputs = protocol_builder.protocol_inputs()
    preregistration_payload = repeat_runner._read_bounded_regular(
        ROOT / contract.PREREGISTRATION_PATH,
        label="MM-005 model-evaluation preregistration",
        max_bytes=MAX_JSON_BYTES,
    )
    preregistration = contract.parse_strict_json_bytes(
        preregistration_payload, location="$.preregistration"
    )
    contract.validate_preregistration(preregistration, **inputs)
    if contract.artifact_json_bytes(preregistration) != preregistration_payload:
        raise RuntimeError("MM-005 model-evaluation preregistration is not canonical")
    _validate_protocol_freeze_commit(
        protocol_freeze_commit=protocol_freeze_commit,
        preregistration_payload=preregistration_payload,
        inputs=inputs,
    )
    upstream_runner._validate_local_dependency_wheel()

    candidate = _mapping(preregistration.get("candidate"), "$.candidate")
    model_receipts = _object_sequence(
        candidate.get("model_files"), "$.candidate.model_files"
    )
    dataset_receipts = _receipt_mapping(
        inputs["dataset_output_receipts"], "$.dataset_output_receipts"
    )
    records = _object_sequence(inputs["records"], "$.records")
    expected_payloads = _bytes_mapping(
        inputs["artifact_payloads"], "$.artifact_payloads"
    )

    with (
        repeat_runner._FrozenInputFileSet(
            model_snapshot=ROOT / contract.MODEL_SNAPSHOT_ROOT,
            model_receipts=model_receipts,
            adapter_receipts=contract.ADAPTER_RECEIPTS,
        ) as frozen_model,
        _FrozenDatasetInputSet(dataset_receipts) as frozen_dataset,
    ):
        if frozen_dataset.payloads != expected_payloads:
            raise RuntimeError("frozen MM-005 inputs differ from authenticated context")
        _ensure_output_parent()
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
            file_validator._write_exclusive(
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
                observed_environment = upstream_runner.observed_environment(torch)
                if observed_environment != candidate.get("environment"):
                    raise RuntimeError("formal MM-005 evaluation environment mismatch")
                torch.cuda.empty_cache()
                torch.cuda.reset_peak_memory_stats()
                stage = "generation"
                cases = _run_model_evaluation(
                    dependencies=dependencies,
                    records=records,
                    artifact_payloads=frozen_dataset.payloads,
                    counters=counters,
                    completed_record_ids=completed_record_ids,
                )
                frozen_model.verify()
                frozen_dataset.verify()
                torch.cuda.synchronize()
                resources = {
                    "elapsed_seconds": time.perf_counter() - started,
                    "peak_gpu_allocated_bytes": int(torch.cuda.max_memory_allocated()),
                    "peak_gpu_reserved_bytes": int(torch.cuda.max_memory_reserved()),
                }

            stage = "candidate_persistence"
            candidate_object = contract.build_evaluation_candidate(
                protocol_freeze_commit=protocol_freeze_commit,
                preregistration_payload=preregistration_payload,
                attempt_owner_payload=owner_written,
                cases=cases,
                records=records,
                artifact_payloads=frozen_dataset.payloads,
                execution=counters,
                resources=resources,
            )
            candidate_intended = contract.artifact_json_bytes(candidate_object)
            repeat_runner._write_output_artifact(
                output_guard,
                ROOT / contract.EVALUATION_CANDIDATE_PATH,
                candidate_intended,
            )
            candidate_written = candidate_intended

            stage = "scoring"
            contract.score_case_results(records, cases)
            predictions_object = contract.build_predictions(candidate_object)
            predictions_intended = contract.artifact_json_bytes(predictions_object)
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
                records=records,
                artifact_payloads=frozen_dataset.payloads,
                captured_at_utc=datetime.now(timezone.utc).isoformat(),
            )
            evidence_intended = contract.artifact_json_bytes(evidence_object)
            repeat_runner._write_output_artifact(
                output_guard,
                ROOT / contract.EVIDENCE_PATH,
                evidence_intended,
            )
            evidence_written = evidence_intended
            return _success_summary(evidence_object)
        except BaseException as exc:
            if attempt_consumed and owner_written is None:
                owner_written = repeat_runner._observe_attempt_owner(
                    ROOT / contract.ATTEMPT_OWNER_PATH, owner_payload, strict=True
                )
            if attempt_consumed and (output_guard is None or not output_guard.is_open):
                if owner_written is None:
                    raise RuntimeError(
                        "consumed attempt has no authenticated owner"
                    ) from exc
                output_guard = repeat_runner._ConsumedOutputDirectoryGuard(
                    reservation,
                    initial_artifacts={
                        ROOT / contract.ATTEMPT_OWNER_PATH: owner_written
                    },
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
                        "MM-005 evaluation candidate",
                    )
                if predictions_written is None:
                    predictions_written = repeat_runner._recover_exclusive_artifact(
                        output_guard,
                        ROOT / contract.PREDICTIONS_PATH,
                        predictions_intended,
                        "MM-005 predictions",
                    )
                if evidence_written is None:
                    evidence_written = repeat_runner._recover_exclusive_artifact(
                        output_guard,
                        ROOT / contract.EVIDENCE_PATH,
                        evidence_intended,
                        "MM-005 evidence",
                    )
            if evidence_written is not None:
                if evidence_object is None:
                    raise RuntimeError(
                        "durable evidence exists without authenticated object"
                    ) from exc
                return _success_summary(evidence_object)
            if attempt_consumed:
                if owner_written is None or output_guard is None:
                    raise RuntimeError(
                        "consumed attempt cannot persist failure"
                    ) from exc
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


def _run_model_evaluation(
    *,
    dependencies: tuple[Any, ...],
    records: Sequence[Mapping[str, Any]],
    artifact_payloads: Mapping[str, bytes],
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
        raise RuntimeError("MM-005 evaluation model has trainable state")

    cases: list[dict[str, Any]] = []
    ordered = sorted(records, key=lambda item: str(item.get("record_id")))
    screenshot_payloads, source_snapshot_payloads = contract.artifact_input_sets(
        artifact_payloads
    )
    with torch.inference_mode():
        for record in ordered:
            adapted = adapter_verifier.adapt_record(
                record, screenshot_payloads, source_snapshot_payloads
            )
            counters["generate_attempts"] += 1
            images = [
                image_class.open(io.BytesIO(payload)).convert("RGB")
                for payload in adapted.screenshot_payloads
            ]
            try:
                messages = contract.build_runtime_messages(
                    adapted.model_payload(), images
                )
                counters["screenshot_inputs"] += len(images)
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
                counters["generate_calls"] += 1
                torch.cuda.synchronize()
                case = contract.build_case_result(
                    record=record,
                    artifact_payloads=artifact_payloads,
                    raw_output=raw_output,
                    generated_tokens=generated_tokens,
                    latency_seconds=time.perf_counter() - started,
                )
                cases.append(case)
                completed_record_ids.append(str(record["record_id"]))
            finally:
                for image in images:
                    image.close()
    if counters != contract.expected_execution_counters():
        raise RuntimeError("MM-005 evaluation counters differ from protocol")
    del model, base_model, processor
    gc.collect()
    torch.cuda.empty_cache()
    return cases


def _validate_protocol_freeze_commit(
    *,
    protocol_freeze_commit: str,
    preregistration_payload: bytes,
    inputs: Mapping[str, Any],
) -> None:
    branch = _git_text("rev-parse", "--abbrev-ref", "HEAD")
    head = _git_text("rev-parse", "HEAD")
    origin_master = _git_text("rev-parse", "refs/remotes/origin/master")
    if branch != "master" or head != origin_master or head != protocol_freeze_commit:
        raise RuntimeError(
            "formal MM-005 evaluation requires aligned merged master freeze commit"
        )
    tracked: dict[str, Mapping[str, Any]] = {
        contract.PREREGISTRATION_PATH: _receipt(
            contract.PREREGISTRATION_PATH, preregistration_payload
        ),
        implementation_contract.EVIDENCE_PATH: _receipt(
            implementation_contract.EVIDENCE_PATH,
            _bytes_value(
                inputs["implementation_evidence_payload"],
                "$.implementation_evidence_payload",
            ),
        ),
        candidate_protocol.PREREGISTRATION_PATH: _receipt(
            candidate_protocol.PREREGISTRATION_PATH,
            _bytes_value(
                inputs["candidate_preregistration_payload"],
                "$.candidate_preregistration_payload",
            ),
        ),
        "baseline/mm004-hard-negative-model-eval-v2-result-review.json": _receipt(
            "baseline/mm004-hard-negative-model-eval-v2-result-review.json",
            _bytes_value(
                inputs["candidate_result_review_payload"],
                "$.candidate_result_review_payload",
            ),
        ),
        "baseline/mm004-hard-negative-model-eval-v2-evidence.json": _receipt(
            "baseline/mm004-hard-negative-model-eval-v2-evidence.json",
            _bytes_value(
                inputs["candidate_evidence_payload"],
                "$.candidate_evidence_payload",
            ),
        ),
    }
    tracked.update(
        {
            str(receipt["path"]): receipt
            for receipt in _receipt_mapping(
                inputs["source_receipts"], "$.source_receipts"
            ).values()
        }
    )
    tracked.update(
        {
            str(path): receipt
            for path, receipt in _receipt_mapping(
                inputs["dataset_output_receipts"], "$.dataset_output_receipts"
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
        payload = _git_show_bytes(protocol_freeze_commit, path)
        if path == contract.ADAPTER_LFS_PATH:
            matches = payload == candidate_protocol.git_lfs_pointer_bytes(expected)
        else:
            matches = _receipt(path, payload) == dict(expected)
        if not matches:
            raise RuntimeError(f"freeze commit tracked receipt differs: {path}")


def _validate_formal_python_execution_mode() -> None:
    repeat_runner._require_exact_repo_path(Path.cwd(), ROOT, "working directory")
    repeat_runner._require_exact_repo_path(
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
        raise RuntimeError("formal MM-005 evaluation requires isolated Python args")


def _ensure_output_parent() -> None:
    parent = (ROOT / contract.RUN_OUTPUT_ROOT).parent
    if not os.path.lexists(parent):
        safe_parent, parent_chain = file_validator._safe_repository_parent_chain(
            ROOT, parent, "MM-005 evaluation output parent"
        )
        os.mkdir(safe_parent)
        file_validator._recheck_repository_parent_chain(
            parent_chain, "MM-005 evaluation output parent", identity_only=True
        )
    metadata = parent.lstat()
    if not stat.S_ISDIR(metadata.st_mode) or file_validator._metadata_is_reparse(
        metadata
    ):
        raise RuntimeError("unsafe MM-005 evaluation output parent")


def _validate_dataset_tree(expected_paths: set[str]) -> None:
    root = ROOT / data_contract.OUTPUT_ROOT
    safe_root, parent_chain = file_validator._safe_repository_parent_chain(
        ROOT, root, "MM-005 frozen dataset root"
    )
    metadata = safe_root.lstat()
    if not stat.S_ISDIR(metadata.st_mode) or file_validator._metadata_is_reparse(
        metadata
    ):
        raise RuntimeError("unsafe MM-005 dataset root")
    observed: set[str] = set()
    for path in safe_root.rglob("*"):
        item = path.lstat()
        if file_validator._metadata_is_reparse(item):
            raise RuntimeError("MM-005 dataset contains a reparse point")
        if stat.S_ISDIR(item.st_mode):
            continue
        if not stat.S_ISREG(item.st_mode) or item.st_nlink != 1:
            raise RuntimeError("MM-005 dataset contains an unsafe file")
        observed.add(path.relative_to(ROOT).as_posix())
    if observed != expected_paths:
        raise RuntimeError("MM-005 dataset file set differs")
    file_validator._recheck_repository_parent_chain(
        parent_chain, "MM-005 frozen dataset root"
    )


class _FrozenDatasetInputSet:
    """Hold all registered MM-005 generated inputs read-only during evaluation."""

    def __init__(self, receipts: Mapping[str, Mapping[str, Any]]) -> None:
        self.receipts = {str(path): dict(value) for path, value in receipts.items()}
        self.payloads: dict[str, bytes] = {}
        self.handles: list[
            tuple[Path, Any, tuple[int, int, int, int, int], Mapping[str, Any]]
        ] = []
        self.tree_signature: dict[str, tuple[int, int, int, int, int, int]] = {}

    def __enter__(self) -> _FrozenDatasetInputSet:
        try:
            _validate_dataset_tree(set(self.receipts))
            self.tree_signature = self._observe_tree()
            for relative, expected in sorted(self.receipts.items()):
                path, parent_chain = file_validator._safe_repository_parent_chain(
                    ROOT, ROOT / relative, f"frozen MM-005 input {relative}"
                )
                before = path.lstat()
                if (
                    not stat.S_ISREG(before.st_mode)
                    or file_validator._metadata_is_reparse(before)
                    or before.st_nlink != 1
                ):
                    raise RuntimeError("unsafe frozen MM-005 input")
                handle = repeat_runner._open_locked_regular(path)
                opened = os.fstat(handle.fileno())
                identity = file_validator._handle_identity_signature(before)
                if file_validator._handle_identity_signature(opened) != identity:
                    handle.close()
                    raise RuntimeError("unstable frozen MM-005 input")
                handle.seek(0)
                payload = handle.read()
                handle.seek(0)
                if _receipt(relative, payload) != expected:
                    handle.close()
                    raise RuntimeError("frozen MM-005 input receipt mismatch")
                file_validator._recheck_repository_parent_chain(
                    parent_chain, f"frozen MM-005 input {relative}"
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
        _validate_dataset_tree(set(self.receipts))
        if self._observe_tree() != self.tree_signature:
            raise RuntimeError("frozen MM-005 dataset tree changed")
        for path, handle, identity, expected in self.handles:
            opened = os.fstat(handle.fileno())
            after = path.lstat()
            if (
                file_validator._handle_identity_signature(opened) != identity
                or file_validator._handle_identity_signature(after) != identity
                or after.st_nlink != 1
                or file_validator._metadata_is_reparse(after)
            ):
                raise RuntimeError("frozen MM-005 input identity changed")
            handle.seek(0)
            payload = handle.read()
            handle.seek(0)
            relative = path.relative_to(ROOT).as_posix()
            if _receipt(relative, payload) != expected:
                raise RuntimeError("frozen MM-005 input content changed")

    def close(self) -> None:
        while self.handles:
            _path, handle, _identity, _expected = self.handles.pop()
            handle.close()

    @staticmethod
    def _observe_tree() -> dict[str, tuple[int, int, int, int, int, int]]:
        root = ROOT / data_contract.OUTPUT_ROOT
        return {
            path.relative_to(ROOT).as_posix(): file_validator._stat_signature(
                path.lstat()
            )
            for path in [root, *sorted(root.rglob("*"))]
        }


def _new_counters() -> dict[str, int]:
    return {key: 0 for key in contract.expected_execution_counters()}


def _safe_exception_type(exc: BaseException) -> str:
    value = type(exc).__name__
    if not value.isidentifier() or len(value) > 128:
        return "BaseException"
    return value


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


def _git_show_bytes(commit: str, path: str) -> bytes:
    completed = subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0 or completed.stderr:
        raise RuntimeError(f"unable to read freeze-commit path: {path}")
    return completed.stdout


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
