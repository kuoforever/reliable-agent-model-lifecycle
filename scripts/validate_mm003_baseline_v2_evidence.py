"""Recompute the frozen MM-003 v2 baseline evidence without model imports."""

from __future__ import annotations

import math
import re
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, NoReturn, cast

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SRC))

from fullcycle_bridge import gui_grounding_eval as base_scorer  # noqa: E402
from fullcycle_bridge import gui_grounding_eval_v2 as scorer  # noqa: E402
from fullcycle_bridge import mm003_baseline_protocol_v2 as contract  # noqa: E402
from scripts import run_mm003_multimodal_gui_action_baseline_v2 as runner  # noqa: E402

PROTOCOL_FREEZE_COMMIT = "9702c92c37f18c32a7458cbb2fa3c6d2e75e0490"
PREREGISTRATION_BYTES = 13_349
PREREGISTRATION_SHA256 = (
    "sha256:369c813dee44b14c6022eb90739bcd37f9f8de472e60a8cee88682454d135403"
)
ARTIFACTS: dict[str, dict[str, int | str]] = {
    "run": {
        "path": contract.RUN_ARTIFACT_PATH,
        "bytes": 14_715,
        "sha256": (
            "sha256:173bb4ab17fa5d6c02323f9cc26e8cddd93525055a712b8f6c5cd5c09cb2a57c"
        ),
    },
    "predictions": {
        "path": contract.PREDICTIONS_ARTIFACT_PATH,
        "bytes": 2_058,
        "sha256": (
            "sha256:57629229e4416cb7562382b57ee6774845dbd4f1da97b73a1e54d2a2f8ea17f7"
        ),
    },
    "evidence": {
        "path": contract.EVIDENCE_ARTIFACT_PATH,
        "bytes": 4_680,
        "sha256": (
            "sha256:a0e3c2503e5bac13bf979c7721dab4350681a84883d749b94ef3ca204d2166fe"
        ),
    },
}
_RUN_FIELDS = {
    "run_artifact_version",
    "experiment_id",
    "gate_id",
    "captured_at_utc",
    "protocol",
    "model_resolution",
    "inputs",
    "environment",
    "execution",
    "persistence",
    "cases",
    "resources",
    "claims",
}
_CASE_FIELDS = {
    "case_id",
    "observation_mode",
    "prompt_sha256",
    "screenshot_sha256",
    "raw_output",
    "raw_output_sha256",
    "compiled_prediction",
    "compiler_fallback",
    "candidate_steps",
    "generated_tokens",
    "latency_seconds",
}
_TIMESTAMP = re.compile(r"20[0-9]{2}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z")


class MM003BaselineV2EvidenceError(ValueError):
    """Raised when the frozen result cannot be reproduced exactly."""


def validate_repository(root: Path = ROOT) -> dict[str, Any]:
    preregistration_payload = _read_exact(
        root / contract.PREREGISTRATION_PATH,
        expected_bytes=PREREGISTRATION_BYTES,
        expected_sha256=PREREGISTRATION_SHA256,
        label="preregistration",
    )
    payloads = {
        name: _read_exact(
            root / str(receipt["path"]),
            expected_bytes=int(receipt["bytes"]),
            expected_sha256=str(receipt["sha256"]),
            label=name,
        )
        for name, receipt in ARTIFACTS.items()
    }
    failure_path = root / contract.FAILURE_ARTIFACT_PATH
    if failure_path.exists() or failure_path.is_symlink():
        _fail("SUCCESS_FAILURE_ARTIFACT_PRESENT")
    suite = base_scorer.load_suite_file((root / contract.MM002_SUITE_PATH).resolve())
    summary = validate_payloads(
        preregistration_payload=preregistration_payload,
        run_payload=payloads["run"],
        predictions_payload=payloads["predictions"],
        evidence_payload=payloads["evidence"],
        suite=suite,
    )
    preregistration = _object(preregistration_payload, "$.preregistration")
    source_receipts = _mapping(
        _mapping(preregistration["source_lineage"], "$.source_lineage")[
            "protocol_sources"
        ],
        "$.source_lineage.protocol_sources",
    )
    expected_source_hashes = {
        name: _mapping(receipt, f"$.source_lineage.protocol_sources.{name}")["sha256"]
        for name, receipt in source_receipts.items()
    }
    if runner.protocol_source_hashes() != expected_source_hashes:
        _fail("PROTOCOL_SOURCE_HASH_MISMATCH")
    return summary


def validate_payloads(
    *,
    preregistration_payload: bytes,
    run_payload: bytes,
    predictions_payload: bytes,
    evidence_payload: bytes,
    suite: Mapping[str, Any],
) -> dict[str, Any]:
    _check_payload_receipt(
        preregistration_payload,
        expected_bytes=PREREGISTRATION_BYTES,
        expected_sha256=PREREGISTRATION_SHA256,
        label="preregistration",
    )
    for name, payload in (
        ("run", run_payload),
        ("predictions", predictions_payload),
        ("evidence", evidence_payload),
    ):
        receipt = ARTIFACTS[name]
        _check_payload_receipt(
            payload,
            expected_bytes=int(receipt["bytes"]),
            expected_sha256=str(receipt["sha256"]),
            label=name,
        )

    preregistration = contract.validate_preregistration(
        _object(preregistration_payload, "$.preregistration")
    )
    run_artifact = _object(run_payload, "$.run")
    predictions = _object(predictions_payload, "$.predictions")
    evidence = _object(evidence_payload, "$.evidence")
    for label, value, payload in (
        ("run", run_artifact, run_payload),
        ("predictions", predictions, predictions_payload),
        ("evidence", evidence, evidence_payload),
    ):
        if contract.artifact_json_bytes(value) != payload:
            _fail(f"NONCANONICAL_{label.upper()}_JSON")

    if set(run_artifact) != _RUN_FIELDS:
        _fail("RUN_FIELDS_MISMATCH")
    if (
        run_artifact["run_artifact_version"] != 2
        or run_artifact["experiment_id"] != contract.EXPERIMENT_ID
        or run_artifact["gate_id"] != contract.GATE_ID
        or not isinstance(run_artifact["captured_at_utc"], str)
        or _TIMESTAMP.fullmatch(run_artifact["captured_at_utc"]) is None
    ):
        _fail("RUN_IDENTITY_MISMATCH")
    protocol = _mapping(run_artifact["protocol"], "$.run.protocol")
    if protocol != {
        "preregistration_sha256": PREREGISTRATION_SHA256,
        "freeze_commit": PROTOCOL_FREEZE_COMMIT,
    }:
        _fail("RUN_PROTOCOL_BINDING_MISMATCH")
    execution = _mapping(run_artifact["execution"], "$.run.execution")
    if execution != {
        "fresh_model_loads": 1,
        "full_eval_runs": 1,
        "generate_calls": 9,
        "retry_count": 0,
        "network_used": False,
        "generation_completed": True,
    }:
        _fail("RUN_EXECUTION_MISMATCH")

    records = _sequence(predictions.get("records"), "$.predictions.records")
    cases = _sequence(run_artifact["cases"], "$.run.cases")
    if len(cases) != 9 or len(records) != 9:
        _fail("CASE_COUNT_MISMATCH")
    for index, (case, record) in enumerate(zip(cases, records, strict=True)):
        if set(case) != _CASE_FIELDS:
            _fail("CASE_FIELDS_MISMATCH")
        case_id = contract.CASE_ORDER[index]
        raw_output = case.get("raw_output")
        if (
            case.get("case_id") != case_id
            or record.get("case_id") != case_id
            or case.get("observation_mode") != contract.CASE_MODES[case_id]
            or case.get("compiled_prediction") != record
            or not isinstance(raw_output, str)
            or case.get("raw_output_sha256")
            != contract.sha256_bytes(raw_output.encode("utf-8"))
            or case.get("compiler_fallback")
            is not (record.get("disposition") == "fallback")
        ):
            _fail("CASE_BINDING_MISMATCH")
        _positive_integer(case.get("candidate_steps"), "CASE_STEPS_MISMATCH")
        _positive_integer(case.get("generated_tokens"), "GENERATED_TOKENS_MISMATCH")
        _positive_number(case.get("latency_seconds"), "LATENCY_MISMATCH")

    score = scorer.score_predictions(suite, predictions)
    artifact_receipts = {
        "run": runner._receipt(contract.RUN_ARTIFACT_PATH, run_payload),
        "predictions": runner._receipt(
            contract.PREDICTIONS_ARTIFACT_PATH, predictions_payload
        ),
    }
    recomputed = runner.build_evidence(
        preregistration=preregistration,
        preregistration_payload=preregistration_payload,
        protocol_freeze_commit=PROTOCOL_FREEZE_COMMIT,
        run_artifact=run_artifact,
        predictions=predictions,
        score=score,
        suite=suite,
        run_payload=run_payload,
        predictions_payload=predictions_payload,
        artifact_receipts=artifact_receipts,
    )
    if recomputed != evidence:
        _fail("EVIDENCE_RECOMPUTATION_MISMATCH")
    if (
        not all(evidence["gates"].values())
        or evidence["formal_gate_passed"] is not True
        or evidence["classification"] != "local_small_vlm_baseline_established"
        or evidence["compiler"] != {"fallback_count": 9, "fallback_rate": 1.0}
        or evidence["next_gate"] != "MM-003-small-vlm-post-training-protocol-v1"
        or evidence["runtime_eligible"] is not False
    ):
        _fail("EVIDENCE_DECISION_MISMATCH")
    metrics = _mapping(
        _mapping(evidence["quality"], "$.evidence.quality")["overall"],
        "$.evidence.quality.overall",
    )
    return {
        "formal_gate_passed": True,
        "model_evaluated": True,
        "classification": evidence["classification"],
        "case_count": len(cases),
        "fallback_count": evidence["compiler"]["fallback_count"],
        "grounding_accuracy": metrics["grounding_accuracy"],
        "action_accuracy": metrics["action_accuracy"],
        "next_gate": evidence["next_gate"],
        "runtime_eligible": False,
    }


def _read_exact(
    path: Path, *, expected_bytes: int, expected_sha256: str, label: str
) -> bytes:
    if path.is_symlink() or not path.is_file():
        _fail(f"MISSING_OR_UNSAFE_{label.upper()}")
    payload = path.read_bytes()
    _check_payload_receipt(
        payload,
        expected_bytes=expected_bytes,
        expected_sha256=expected_sha256,
        label=label,
    )
    return payload


def _check_payload_receipt(
    payload: bytes, *, expected_bytes: int, expected_sha256: str, label: str
) -> None:
    if len(payload) != expected_bytes:
        _fail(f"{label.upper()}_BYTE_MISMATCH")
    if contract.sha256_bytes(payload) != expected_sha256:
        _fail(f"{label.upper()}_HASH_MISMATCH")


def _object(payload: bytes, location: str) -> dict[str, Any]:
    value = contract.parse_strict_json_bytes(payload, location=location)
    if not isinstance(value, dict):
        _fail("EXPECTED_OBJECT")
    return value


def _mapping(value: object, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail(f"EXPECTED_OBJECT_AT_{location}")
    return value


def _sequence(value: object, location: str) -> Sequence[Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        _fail(f"EXPECTED_ARRAY_AT_{location}")
    return cast(Sequence[Mapping[str, Any]], value)


def _positive_integer(value: object, code: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        _fail(code)


def _positive_number(value: object, code: str) -> None:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
        or value <= 0
    ):
        _fail(code)


def _fail(code: str) -> NoReturn:
    raise MM003BaselineV2EvidenceError(code)


def main() -> int:
    print(contract.canonical_json_bytes(validate_repository()).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
