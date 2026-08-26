"""Execute the frozen MM-005 fixed-suite evaluation replay exactly once."""

from __future__ import annotations

import argparse
import gc
import json
import os
import secrets
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
    mm005_document_chart_pdf_model_evaluation as baseline_contract,
)
from fullcycle_bridge import (  # noqa: E402
    mm005_document_chart_pdf_model_evaluation_repeatability as contract,
)
from scripts import (  # noqa: E402
    prepare_mm005_document_chart_pdf_model_evaluation_repeatability as protocol_builder,
)
from scripts import (  # noqa: E402
    run_mm003_post_training_eval_repeatability as attempt_guard,
)
from scripts import run_mm003_qlora_post_training_v2 as upstream_runner  # noqa: E402
from scripts import (  # noqa: E402
    run_mm005_document_chart_pdf_model_evaluation as baseline_runner,
)
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
    """Consume one owner-marked unchanged replay with zero retry."""

    _validate_commit(protocol_freeze_commit)
    _validate_formal_python_execution_mode()
    output_dir = ROOT / contract.RUN_OUTPUT_ROOT
    if os.path.lexists(output_dir):
        raise RuntimeError("formal MM-005 repeatability output must be absent")

    inputs = protocol_builder.protocol_inputs()
    preregistration_payload = attempt_guard._read_bounded_regular(
        ROOT / contract.PREREGISTRATION_PATH,
        label="MM-005 evaluation repeatability preregistration",
        max_bytes=MAX_JSON_BYTES,
    )
    preregistration = contract.parse_strict_json_bytes(
        preregistration_payload, location="$.preregistration"
    )
    contract.validate_preregistration(preregistration, **inputs)
    if contract.artifact_json_bytes(preregistration) != preregistration_payload:
        raise RuntimeError("MM-005 repeatability preregistration is not canonical")
    _validate_protocol_freeze_commit(
        protocol_freeze_commit=protocol_freeze_commit,
        preregistration_payload=preregistration_payload,
        preregistration=preregistration,
    )
    upstream_runner._validate_local_dependency_wheel()

    baseline_state = contract.validate_baseline_payloads(
        baseline_preregistration_payload=inputs["baseline_preregistration_payload"],
        baseline_artifact_payloads=inputs["baseline_artifact_payloads"],
        baseline_review_payload=inputs["baseline_review_payload"],
        baseline_inputs=inputs["baseline_inputs"],
    )
    baseline_inputs = _mapping(inputs["baseline_inputs"], "$.baseline_inputs")
    candidate = _mapping(preregistration.get("candidate"), "$.candidate")
    model_receipts = _object_sequence(
        candidate.get("model_files"), "$.candidate.model_files"
    )
    dataset_receipts = _receipt_mapping(
        baseline_inputs["dataset_output_receipts"], "$.dataset_output_receipts"
    )
    records = _object_sequence(baseline_inputs["records"], "$.records")
    expected_payloads = _bytes_mapping(
        baseline_inputs["image_payloads"], "$.image_payloads"
    )

    with (
        attempt_guard._FrozenInputFileSet(
            model_snapshot=ROOT / baseline_contract.MODEL_SNAPSHOT_ROOT,
            model_receipts=model_receipts,
            adapter_receipts=baseline_contract.ADAPTER_RECEIPTS,
        ) as frozen_model,
        baseline_runner._FrozenDatasetInputSet(dataset_receipts) as frozen_dataset,
    ):
        if frozen_dataset.payloads != expected_payloads:
            raise RuntimeError("frozen replay inputs differ from authenticated context")
        _ensure_output_parent()
        reservation = attempt_guard._prepare_output_reservation(output_dir)
        attempt_id = secrets.token_hex(32)
        owner_payload = contract.artifact_json_bytes(
            contract.build_attempt_owner(
                protocol_freeze_commit=protocol_freeze_commit,
                preregistration_payload=preregistration_payload,
                attempt_id=attempt_id,
            )
        )
        owner_staging = output_dir.with_name(f".{output_dir.name}.owner-{attempt_id}")
        owner_staging_reservation = attempt_guard._prepare_output_reservation(
            owner_staging
        )
        attempt_consumed = False
        output_guard: attempt_guard._ConsumedOutputDirectoryGuard | None = None
        owner_written: bytes | None = None
        candidate_intended: bytes | None = None
        candidate_written: bytes | None = None
        predictions_intended: bytes | None = None
        predictions_written: bytes | None = None
        evidence_intended: bytes | None = None
        evidence_written: bytes | None = None
        evidence_object: dict[str, Any] | None = None
        completed_record_ids: list[str] = []
        counters = baseline_runner._new_counters()
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
            output_guard = attempt_guard._ConsumedOutputDirectoryGuard(
                reservation,
                initial_artifacts={ROOT / contract.ATTEMPT_OWNER_PATH: owner_written},
            )
            output_guard.open()
            counters["run_attempts"] = 1
            started = time.perf_counter()

            stage = "dependency_and_environment_validation"
            upstream_runner._enable_offline_execution()
            with attempt_guard._OfflineSocketGuard(counters):
                dependencies = attempt_guard._load_eval_dependencies()
                torch = dependencies[0]
                observed_environment = upstream_runner.observed_environment(torch)
                if observed_environment != preregistration.get("environment"):
                    raise RuntimeError("formal replay environment mismatch")
                torch.cuda.empty_cache()
                torch.cuda.reset_peak_memory_stats()
                stage = "model_load_and_generation"
                cases = baseline_runner._run_model_evaluation(
                    dependencies=dependencies,
                    records=records,
                    image_payloads=frozen_dataset.payloads,
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
                image_payloads=frozen_dataset.payloads,
                execution=counters,
                resources=resources,
            )
            candidate_intended = contract.artifact_json_bytes(candidate_object)
            attempt_guard._write_output_artifact(
                output_guard,
                ROOT / contract.EVALUATION_CANDIDATE_PATH,
                candidate_intended,
            )
            candidate_written = candidate_intended

            stage = "scoring"
            baseline_contract.score_case_results(records, cases)
            predictions_object = contract.build_predictions(candidate_object)
            predictions_intended = contract.artifact_json_bytes(predictions_object)
            stage = "predictions_persistence"
            attempt_guard._write_output_artifact(
                output_guard,
                ROOT / contract.PREDICTIONS_PATH,
                predictions_intended,
            )
            predictions_written = predictions_intended

            stage = "evidence_persistence"
            evidence_object = contract.build_evidence(
                protocol_freeze_commit=protocol_freeze_commit,
                preregistration_payload=preregistration_payload,
                preregistration=preregistration,
                attempt_owner_payload=owner_written,
                evaluation_candidate_payload=candidate_written,
                predictions_payload=predictions_written,
                reference_candidate=baseline_state["candidate"],
                reference_evidence=baseline_state["evidence"],
                records=records,
                image_payloads=frozen_dataset.payloads,
                observed_environment=observed_environment,
                captured_at_utc=datetime.now(timezone.utc).isoformat(),
            )
            evidence_intended = contract.artifact_json_bytes(evidence_object)
            attempt_guard._write_output_artifact(
                output_guard,
                ROOT / contract.EVIDENCE_PATH,
                evidence_intended,
            )
            evidence_written = evidence_intended
            return _success_summary(evidence_object)
        except BaseException as exc:
            if attempt_consumed and owner_written is None:
                owner_written = attempt_guard._observe_attempt_owner(
                    ROOT / contract.ATTEMPT_OWNER_PATH, owner_payload, strict=True
                )
            if attempt_consumed and (output_guard is None or not output_guard.is_open):
                if owner_written is None:
                    raise RuntimeError(
                        "consumed replay has no authenticated owner"
                    ) from exc
                output_guard = attempt_guard._ConsumedOutputDirectoryGuard(
                    reservation,
                    initial_artifacts={
                        ROOT / contract.ATTEMPT_OWNER_PATH: owner_written
                    },
                )
                output_guard.open()
            if attempt_consumed:
                if output_guard is None:
                    raise RuntimeError("consumed replay has no output guard") from exc
                if candidate_written is None:
                    candidate_written = attempt_guard._recover_exclusive_artifact(
                        output_guard,
                        ROOT / contract.EVALUATION_CANDIDATE_PATH,
                        candidate_intended,
                        "MM-005 repeatability candidate",
                    )
                if predictions_written is None:
                    predictions_written = attempt_guard._recover_exclusive_artifact(
                        output_guard,
                        ROOT / contract.PREDICTIONS_PATH,
                        predictions_intended,
                        "MM-005 repeatability predictions",
                    )
                if evidence_written is None:
                    evidence_written = attempt_guard._recover_exclusive_artifact(
                        output_guard,
                        ROOT / contract.EVIDENCE_PATH,
                        evidence_intended,
                        "MM-005 repeatability evidence",
                    )
            if evidence_written is not None:
                if evidence_object is None:
                    raise RuntimeError(
                        "durable repeatability evidence lacks authenticated object"
                    ) from exc
                return _success_summary(evidence_object)
            if attempt_consumed:
                if owner_written is None or output_guard is None:
                    raise RuntimeError(
                        "consumed replay cannot persist failure"
                    ) from exc
                failure = contract.build_failure(
                    protocol_freeze_commit=protocol_freeze_commit,
                    preregistration_payload=preregistration_payload,
                    attempt_owner_payload=owner_written,
                    stage=stage,
                    exception_type=_safe_exception_type(exc),
                    counters=counters,
                    completed_record_ids=completed_record_ids,
                    records=records,
                    image_payloads=frozen_dataset.payloads,
                    evaluation_candidate_payload=candidate_written,
                    predictions_payload=predictions_written,
                )
                attempt_guard._write_output_artifact(
                    output_guard,
                    ROOT / contract.FAILURE_PATH,
                    contract.artifact_json_bytes(failure),
                )
            raise
        finally:
            if output_guard is not None:
                output_guard.close()
            gc.collect()


def _validate_protocol_freeze_commit(
    *,
    protocol_freeze_commit: str,
    preregistration_payload: bytes,
    preregistration: Mapping[str, Any],
) -> None:
    branch = _git_text("rev-parse", "--abbrev-ref", "HEAD")
    head = _git_text("rev-parse", "HEAD")
    origin_master = _git_text("rev-parse", "refs/remotes/origin/master")
    if branch != "master" or head != origin_master or head != protocol_freeze_commit:
        raise RuntimeError(
            "formal MM-005 replay requires aligned merged master freeze commit"
        )
    if _git_show_bytes(protocol_freeze_commit, contract.PREREGISTRATION_PATH) != (
        preregistration_payload
    ):
        raise RuntimeError("freeze commit repeatability protocol differs")
    receipts = _mapping(preregistration.get("source_receipts"), "$.source_receipts")
    for name, relative in contract.PROTOCOL_SOURCE_PATHS.items():
        receipt = _mapping(receipts.get(name), f"$.source_receipts.{name}")
        payload = _git_show_bytes(protocol_freeze_commit, relative)
        if (
            receipt.get("path") != relative
            or receipt.get("bytes") != len(payload)
            or receipt.get("sha256") != contract.sha256_bytes(payload)
        ):
            raise RuntimeError(f"freeze commit protocol source differs: {name}")


def _validate_formal_python_execution_mode() -> None:
    baseline_runner._validate_formal_python_execution_mode()


def _ensure_output_parent() -> None:
    baseline_runner._ensure_output_parent()


def _success_summary(evidence: Mapping[str, Any]) -> dict[str, Any]:
    comparison = _mapping(evidence.get("comparison"), "$.evidence.comparison")
    return {
        "valid": True,
        "formal_gate_passed": evidence["formal_gate_passed"],
        "classification": evidence["classification"],
        "record_count": contract.EXPECTED_RECORDS,
        "all_registered_layers_exact": comparison["all_registered_layers_exact"],
        "raw_outputs_exact": comparison["raw_outputs"]["exact_count"],
        "compiled_outputs_exact": comparison["compiled_outputs"]["exact_count"],
        "verifier_verdicts_exact": comparison["verifier_verdicts"]["exact_count"],
        "generated_token_counts_exact": comparison["generated_token_counts"][
            "exact_count"
        ],
        "metrics_exact": comparison["metrics"]["exact"],
        "next_gate": evidence["next_gate"],
    }


def _safe_exception_type(exc: BaseException) -> str:
    return f"{type(exc).__module__}.{type(exc).__qualname__}"


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
        raise RuntimeError("unable to validate merged repeatability state")
    value = completed.stdout.strip()
    if not value:
        raise RuntimeError("empty git result while validating repeatability state")
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
        raise RuntimeError(f"unable to read frozen path: {path}")
    return completed.stdout


def _mapping(value: object, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise RuntimeError(f"expected object at {location}")
    return value


def _object_sequence(value: object, location: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise RuntimeError(f"expected object array at {location}")
    if not all(isinstance(item, Mapping) for item in value):
        raise RuntimeError(f"expected object items at {location}")
    return list(value)


def _receipt_mapping(value: object, location: str) -> dict[str, Mapping[str, Any]]:
    mapping = _mapping(value, location)
    if not all(
        isinstance(key, str) and isinstance(item, Mapping)
        for key, item in mapping.items()
    ):
        raise RuntimeError(f"expected receipt mapping at {location}")
    return dict(mapping)


def _bytes_mapping(value: object, location: str) -> dict[str, bytes]:
    mapping = _mapping(value, location)
    if not all(
        isinstance(key, str) and isinstance(item, bytes)
        for key, item in mapping.items()
    ):
        raise RuntimeError(f"expected byte mapping at {location}")
    return dict(mapping)


def _validate_commit(value: str) -> None:
    if len(value) != 40 or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise ValueError("invalid protocol freeze commit")


if __name__ == "__main__":
    raise SystemExit(main())
