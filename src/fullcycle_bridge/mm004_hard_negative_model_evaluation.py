"""Frozen MM-004 hard-negative model-evaluation protocol and evidence contract."""

from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any, NoReturn

from . import mm004_hard_negative_generation as generation
from . import multimodal_hard_negative as parent

PROTOCOL_VERSION = 2
ATTEMPT_OWNER_VERSION = 1
CANDIDATE_VERSION = 1
PREDICTIONS_VERSION = 1
EVIDENCE_VERSION = 1
FAILURE_VERSION = 1

PREDECESSOR_PROTOCOL_GATE_ID = (
    "MM-004-multimodal-hard-negative-model-evaluation-protocol-v1"
)
PREDECESSOR_EXECUTION_GATE_ID = (
    "MM-004-multimodal-hard-negative-model-evaluation-execution-v1"
)
PROTOCOL_GATE_ID = "MM-004-multimodal-hard-negative-model-evaluation-protocol-v2"
EXECUTION_GATE_ID = "MM-004-multimodal-hard-negative-model-evaluation-execution-v2"
RESULT_REVIEW_GATE_ID = (
    "MM-004-multimodal-hard-negative-model-evaluation-result-review-v2"
)
FAILURE_CLASSIFICATION_GATE_ID = (
    "MM-004-multimodal-hard-negative-model-evaluation-failure-classification-v2"
)
EXPERIMENT_ID = "mm004-hard-negative-model-eval-v2"
RUN_ID = "mm004-hard-negative-model-eval-r2"
SUITE_ID = "mm004-hard-negative-verifier-suite-v1"

PREREGISTRATION_PATH = (
    "configs/mm004_multimodal_hard_negative_model_evaluation_protocol_v2.json"
)
RUN_OUTPUT_ROOT = "work/evaluation-runs/mm004-hard-negative-model-eval-v2"
ATTEMPT_OWNER_PATH = f"{RUN_OUTPUT_ROOT}/attempt-owner.json"
EVALUATION_CANDIDATE_PATH = f"{RUN_OUTPUT_ROOT}/evaluation-candidate.json"
PREDICTIONS_PATH = f"{RUN_OUTPUT_ROOT}/predictions.json"
EVIDENCE_PATH = f"{RUN_OUTPUT_ROOT}/evidence.json"
FAILURE_PATH = f"{RUN_OUTPUT_ROOT}/failure.json"

MODEL_SNAPSHOT_ROOT = (
    "work/model-cache/mm003-model/models--Qwen--Qwen2.5-VL-3B-Instruct/"
    "snapshots/66285546d2b821cf421d4f5eb2576359d3770cd3"
)
ADAPTER_ROOT = "baseline/adapters/mm003-qwen2.5-vl-3b-qlora-sft-v2"
FORMAL_PYTHON_PATH = "work/training-env/Scripts/python.exe"
FORMAL_PYTHON_ARGS = ["-I", "-B", "-X", "pycache_prefix=NUL"]

GENERATION_RESULT_MERGE_COMMIT = "adc48f822ee260f35dd6c30b4d9fc78bb330ab39"
GENERATION_PROTOCOL_FREEZE_COMMIT = "2d41b99e7e984975056f7e1088e768cd8a62b744"
PREDECESSOR_PROTOCOL_FREEZE_COMMIT = "425a4f21c82786d054ce620e83f6703e4f235d2f"
PREDECESSOR_PREREGISTRATION_PATH = (
    "configs/mm004_multimodal_hard_negative_model_evaluation_protocol_v1.json"
)
PREDECESSOR_RUN_OUTPUT_ROOT = "work/evaluation-runs/mm004-hard-negative-model-eval-v1"
SEED = 44_004
EXPECTED_RECORDS = 56
EXPECTED_PAIRS = 28
EXPECTED_IMAGES = 28
EXPECTED_TRAIN_RECORDS = 42
EXPECTED_VALIDATION_RECORDS = 14
MAX_NEW_TOKENS = 64

MODEL_ID = "Qwen/Qwen2.5-VL-3B-Instruct"
MODEL_REVISION = "66285546d2b821cf421d4f5eb2576359d3770cd3"
ADAPTER_MODEL_ID = f"{MODEL_ID}+mm003-qlora-sft-v2"
ADAPTER_LFS_PATH = f"{ADAPTER_ROOT}/adapter_model.safetensors"

SYSTEM_PROMPT = (
    "You are a read-only multimodal candidate-action verifier. Use only the "
    "provided instruction, image, structured observation, and candidate action. "
    "Return exactly one JSON object with the single key verdict and the value "
    "accept or reject. Do not propose, approve, or execute any action."
)
USER_PROMPT_PREFIX = (
    "Evaluate whether this synthetic candidate action is supported by the current "
    "evidence. Return only the required JSON object.\n"
)
ALLOWED_VERDICTS = ("accept", "reject")
PROMPT_PROJECTION_KEYS = ("instruction", "observation", "candidate_action")
EXCLUDED_PROMPT_FIELDS = (
    "mm004_hard_negative_record_version",
    "record_id",
    "family_id",
    "pair_id",
    "split",
    "category_id",
    "variant",
    "verifier",
    "identities",
    "provenance",
    "observation.image_path",
    "observation.image_sha256",
)

RESOURCE_CAPS = {
    "elapsed_seconds": 1_800.0,
    "peak_gpu_allocated_bytes": 16_500_000_000,
    "peak_gpu_reserved_bytes": 16_500_000_000,
}

CONTEXT_RECEIPTS = {
    "parent_protocol": {
        "path": generation.PARENT_PROTOCOL_PATH,
        "bytes": 22_675,
        "sha256": "sha256:f31e009ed8316d59240e9767865a041e86f30325a1fd15f8a29891d56d418355",
    },
    "generation_preregistration": {
        "path": generation.PREREGISTRATION_PATH,
        "bytes": 10_522,
        "sha256": "sha256:c49e18ec570ff198dfa564fdb711b3ba45cf34e5934a9cb667e6a62e13a07ceb",
    },
    "generation_evidence": {
        "path": generation.EVIDENCE_PATH,
        "bytes": 9_425,
        "sha256": "sha256:0c79a89f8f2431640e4c91d9957af978775e54f2360c15eb67b97a89bb60b133",
    },
    "generation_train": {
        "path": generation.TRAIN_PATH,
        "bytes": 86_330,
        "sha256": "sha256:328d3cdc536105a9080718212d429e706aaec1a28a7a3ea5ef56a073bc842eaa",
    },
    "generation_validation": {
        "path": generation.VALIDATION_PATH,
        "bytes": 29_397,
        "sha256": "sha256:e00e671d7f83beecfaba051acb262bfc99f72c99fb4e5d66af47dae819c17bc5",
    },
    "generation_manifest": {
        "path": generation.MANIFEST_PATH,
        "bytes": 8_016,
        "sha256": "sha256:95e1c5878d1a7a7cd50b1be6858814a409b46ed54fb2ecb449dbaab9e8fa222a",
    },
    "candidate_repeatability_protocol": {
        "path": "configs/mm003_small_vlm_post_training_eval_repeatability_protocol_v1.json",
        "bytes": 22_951,
        "sha256": "sha256:723db665f98e53ef2fe968ee7c6fe663b42d79b86176eef5cf70f11ccc4a312b",
    },
    "candidate_result_review": {
        "path": "baseline/mm003-qwen2.5-vl-3b-qlora-sft-v2-result-review.json",
        "bytes": 11_311,
        "sha256": "sha256:3dff57b17eb4fc9966ab53fe92faea8921fb34b485e389aaa19af64610db957d",
    },
    "training_lock": {
        "path": "requirements/mm003_qlora_training.lock",
        "bytes": 333,
        "sha256": "sha256:792d70759560681a4d7c60ae2e4831a422b3825f5308f1124a804ffbb6563c42",
    },
    "predecessor_model_evaluation_protocol": {
        "path": PREDECESSOR_PREREGISTRATION_PATH,
        "bytes": 49_311,
        "sha256": "sha256:3011420f26bc61f572de2e21f96d28215529e495075db4e958573a4e4317484f",
    },
}

ADAPTER_RECEIPTS = {
    "readme": {
        "path": f"{ADAPTER_ROOT}/README.md",
        "bytes": 206,
        "sha256": "sha256:a73f9a4e826eca0a56f08ac2e7d415670b29eaae02bf501aa838ac23aaf3ebdb",
    },
    "config": {
        "path": f"{ADAPTER_ROOT}/adapter_config.json",
        "bytes": 791,
        "sha256": "sha256:e8edf34169cc15c25e98965a5873e27c6eb54f4f95543e60d0452ec2fec60055",
    },
    "weights": {
        "path": f"{ADAPTER_ROOT}/adapter_model.safetensors",
        "bytes": 29_529_752,
        "sha256": "sha256:d93d2ea2d9f05564093cbb0b1286d2c368c54b01e847f1c37a98e00fb2914701",
    },
}

PROTOCOL_SOURCE_PATHS = {
    "base_model_runner": "scripts/run_mm003_multimodal_gui_action_baseline.py",
    "generation_contract": "src/fullcycle_bridge/mm004_hard_negative_generation.py",
    "model_evaluation_contract": (
        "src/fullcycle_bridge/mm004_hard_negative_model_evaluation.py"
    ),
    "model_evaluation_runner": (
        "scripts/run_mm004_hard_negative_model_evaluation.py"
    ),
    "parent_contract": "src/fullcycle_bridge/multimodal_hard_negative.py",
    "post_training_runner_v2": "scripts/run_mm003_qlora_post_training_v2.py",
    "repeatability_contract": (
        "src/fullcycle_bridge/mm003_post_training_eval_repeatability.py"
    ),
    "repeatability_result_validator": (
        "scripts/validate_mm003_post_training_eval_repeatability_result.py"
    ),
    "repeatability_runner": (
        "scripts/run_mm003_post_training_eval_repeatability.py"
    ),
}

REQUIRED_GATES = (
    "protocol_integrity",
    "predecessor_preconsumption_failure",
    "predecessor_output_absent",
    "generation_lineage_integrity",
    "candidate_lineage_integrity",
    "git_lfs_pointer_binding",
    "prompt_label_isolation",
    "case_order_integrity",
    "one_fresh_base_and_adapter_load",
    "fifty_six_ordered_calls",
    "offline_zero_retry",
    "compiler_totality",
    "metric_totality",
    "resource_caps",
    "artifact_persistence",
    "runtime_authority_preserved",
)

FREEZE_CLAIM_KEYS = (
    "predecessor_attempt_consumed",
    "evaluation_executed",
    "model_evaluated",
    "formal_measurement_complete",
    "quality_improved",
    "generalized_quality_established",
    "safety_established",
    "real_content_behavior_established",
    "training_executed",
    "adapter_modified",
    "runtime_repository_changed",
    "serving_eligible",
    "promotion_eligible",
    "runtime_eligible",
)

FAILURE_STAGES = (
    "output_claim",
    "model_load",
    "generation",
    "candidate_persistence",
    "scoring",
    "predictions_persistence",
    "evidence_persistence",
)


class MM004ModelEvaluationError(ValueError):
    """Fail-closed error for the MM-004 model-evaluation lifecycle."""


def canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )


def artifact_json_bytes(value: object) -> bytes:
    return canonical_json_bytes(value)


def sha256_bytes(payload: bytes) -> str:
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def git_lfs_pointer_bytes(receipt: Mapping[str, Any]) -> bytes:
    if receipt.get("path") != ADAPTER_LFS_PATH:
        _fail("LFS_POINTER_PATH")
    size = receipt.get("bytes")
    digest = receipt.get("sha256")
    if type(size) is not int or size <= 0:
        _fail("LFS_POINTER_SIZE")
    _validate_sha256(digest, "LFS_POINTER_SHA256")
    return (
        "version https://git-lfs.github.com/spec/v1\n"
        f"oid {digest}\n"
        f"size {size}\n"
    ).encode("ascii")


def parse_strict_json_bytes(payload: bytes, *, location: str) -> object:
    try:
        return json.loads(
            payload,
            object_pairs_hook=_unique_object,
            parse_constant=lambda value: _fail(f"NONFINITE_JSON:{location}:{value}"),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MM004ModelEvaluationError(f"INVALID_JSON:{location}") from exc


def prompt_projection(record: Mapping[str, Any]) -> dict[str, Any]:
    observation = _mapping(record.get("observation"), "$.record.observation")
    projected_observation = {
        key: value
        for key, value in observation.items()
        if key not in {"image_path", "image_sha256"}
    }
    projection = {
        "instruction": record.get("instruction"),
        "observation": projected_observation,
        "candidate_action": record.get("candidate_action"),
    }
    if tuple(projection) != PROMPT_PROJECTION_KEYS:
        _fail("PROMPT_PROJECTION_KEYS")
    if not isinstance(projection["instruction"], str) or not projection["instruction"]:
        _fail("PROMPT_INSTRUCTION")
    _mapping(projection["candidate_action"], "$.record.candidate_action")
    return projection


def build_user_prompt(record: Mapping[str, Any]) -> str:
    projection = prompt_projection(record)
    return USER_PROMPT_PREFIX + canonical_json_bytes(projection).decode("utf-8")


def compile_raw_verdict(raw_output: str) -> dict[str, Any]:
    compiled = {
        "compiler_version": 1,
        "verdict": "invalid",
        "compiler_fallback": True,
    }
    if not isinstance(raw_output, str):
        return compiled
    try:
        parsed = parse_strict_json_bytes(
            raw_output.strip().encode("utf-8"), location="$.raw_output"
        )
    except (MM004ModelEvaluationError, UnicodeEncodeError):
        return compiled
    if (
        isinstance(parsed, dict)
        and set(parsed) == {"verdict"}
        and type(parsed["verdict"]) is str
        and parsed["verdict"] in ALLOWED_VERDICTS
    ):
        compiled["verdict"] = parsed["verdict"]
        compiled["compiler_fallback"] = False
    return compiled


def expected_preregistration(
    *,
    freeze_status: str,
    generation_evidence: Mapping[str, Any],
    candidate_repeatability_protocol: Mapping[str, Any],
    candidate_result_review: Mapping[str, Any],
    records: Sequence[Mapping[str, Any]],
    source_receipts: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    if freeze_status not in {"draft", "frozen"}:
        _fail("FREEZE_STATUS")
    _validate_upstream_context(
        generation_evidence=generation_evidence,
        candidate_repeatability_protocol=candidate_repeatability_protocol,
        candidate_result_review=candidate_result_review,
        records=records,
    )
    closed_sources = _closed_source_receipts(source_receipts)
    record_order = [str(record["record_id"]) for record in records]
    prompt_receipts = [
        {
            "record_id": str(record["record_id"]),
            **_payload_receipt(
                f"prompt://{record['record_id']}",
                build_user_prompt(record).encode("utf-8"),
            ),
        }
        for record in records
    ]
    image_receipts = [
        receipt
        for path, receipt in sorted(generation_evidence["outputs"].items())
        if str(path).endswith(".png")
    ]
    repeat_execution = _mapping(
        candidate_repeatability_protocol.get("execution_protocol"),
        "$.candidate_repeatability_protocol.execution_protocol",
    )
    repeat_generation = dict(
        _mapping(repeat_execution.get("generation"), "$.repeat_generation")
    )
    repeat_generation["seed"] = SEED
    repeat_generation["max_new_tokens"] = MAX_NEW_TOKENS
    model = _mapping(
        candidate_repeatability_protocol.get("model"),
        "$.candidate_repeatability_protocol.model",
    )
    environment = _mapping(
        candidate_repeatability_protocol.get("environment"),
        "$.candidate_repeatability_protocol.environment",
    )
    wheel = _mapping(
        _mapping(
            candidate_repeatability_protocol.get("source_lineage"),
            "$.candidate_repeatability_protocol.source_lineage",
        ).get("bitsandbytes_wheel"),
        "$.candidate_repeatability_protocol.source_lineage.bitsandbytes_wheel",
    )
    return {
        "mm004_hard_negative_model_evaluation_protocol_version": PROTOCOL_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "gate_id": PROTOCOL_GATE_ID,
        "freeze_status": freeze_status,
        "decision": "outcome_neutral_read_only_candidate_verdict_measurement",
        "source_lineage": {
            "predecessor_protocol": {
                "preregistration": CONTEXT_RECEIPTS[
                    "predecessor_model_evaluation_protocol"
                ],
                "freeze_commit": PREDECESSOR_PROTOCOL_FREEZE_COMMIT,
                "execution_gate": PREDECESSOR_EXECUTION_GATE_ID,
                "output_directory": PREDECESSOR_RUN_OUTPUT_ROOT,
                "attempt_consumed": False,
                "model_imported": False,
                "model_calls": 0,
                "output_absent": True,
                "classification": (
                    "preconsumption_git_lfs_pointer_vs_hydrated_payload_"
                    "receipt_validation_mismatch"
                ),
                "repair": (
                    "compare_tracked_exact_lfs_pointer_oid_and_size_while_"
                    "locking_hydrated_payload_by_full_receipt"
                ),
            },
            "generation_result_merge_commit": GENERATION_RESULT_MERGE_COMMIT,
            "generation_protocol_freeze_commit": GENERATION_PROTOCOL_FREEZE_COMMIT,
            "context_receipts": CONTEXT_RECEIPTS,
            "generation_outputs": generation_evidence["outputs"],
            "adapter": ADAPTER_RECEIPTS,
            "adapter_git_lfs_pointer": _payload_receipt(
                ADAPTER_LFS_PATH,
                git_lfs_pointer_bytes(ADAPTER_RECEIPTS["weights"]),
            ),
            "bitsandbytes_wheel": dict(wheel),
            "protocol_sources": closed_sources,
        },
        "candidate": {
            "model_id": MODEL_ID,
            "model_revision": MODEL_REVISION,
            "adapter_model_id": ADAPTER_MODEL_ID,
            "license": model["license"],
            "license_scope": model["license_scope"],
            "architecture": model["architecture"],
            "model_files": model["files"],
            "adapter_files": ADAPTER_RECEIPTS,
            "execution_form": "nf4_base_plus_read_only_lora_adapter",
            "environment": dict(environment),
            "training_allowed": False,
            "adapter_mutation_allowed": False,
            "model_or_tensor_save_allowed": False,
        },
        "input_suite": {
            "suite_id": SUITE_ID,
            "record_count": EXPECTED_RECORDS,
            "pair_count": EXPECTED_PAIRS,
            "image_count": EXPECTED_IMAGES,
            "train_records": EXPECTED_TRAIN_RECORDS,
            "validation_records": EXPECTED_VALIDATION_RECORDS,
            "categories": list(parent.CATEGORY_IDS),
            "variants": ["clean", "hard_negative"],
            "case_order": record_order,
            "image_receipts": image_receipts,
            "prompt": {
                "system_prompt": _payload_receipt(
                    "prompt://system", SYSTEM_PROMPT.encode("utf-8")
                ),
                "user_prompt_builder": "build_user_prompt",
                "projection_keys": list(PROMPT_PROJECTION_KEYS),
                "excluded_record_fields": list(EXCLUDED_PROMPT_FIELDS),
                "gold_verdict_available_to_model": False,
                "prompt_receipts": prompt_receipts,
                "prompt_receipts_sha256": sha256_bytes(
                    canonical_json_bytes(prompt_receipts)
                ),
            },
        },
        "compiler": {
            "name": "compile_raw_verdict",
            "version": 1,
            "accepted_shape": {"verdict": list(ALLOWED_VERDICTS)},
            "unknown_or_invalid_output": "invalid",
            "extra_keys_allowed": False,
            "duplicate_keys_allowed": False,
            "nonfinite_values_allowed": False,
            "compiler_fallback_is_incorrect": True,
        },
        "metrics": {
            "quality_threshold_required": False,
            "formal_measurement_is_accuracy_independent": True,
            "registered": [
                "overall_accuracy",
                "clean_accept_recall",
                "hard_negative_rejection_recall",
                "balanced_variant_accuracy",
                "pair_exact_accuracy",
                "compiler_validity",
                "hard_negative_false_accepts",
                "clean_false_rejects",
                "per_split",
                "per_category",
            ],
        },
        "execution_protocol": {
            "model_snapshot_root": MODEL_SNAPSHOT_ROOT,
            "adapter_root": ADAPTER_ROOT,
            "python_invocation": {
                "executable": FORMAL_PYTHON_PATH,
                "required_args": FORMAL_PYTHON_ARGS,
                "isolated": True,
                "dont_write_bytecode": True,
                "pycache_prefix": "NUL",
            },
            "run_count": 1,
            "fresh_base_loads": 1,
            "independent_adapter_loads": 1,
            "generate_calls": EXPECTED_RECORDS,
            "case_order": record_order,
            "retry_count": 0,
            "network_used": False,
            "local_files_only": True,
            "training_runs": 0,
            "optimizer_steps": 0,
            "backward_calls": 0,
            "adapter_writes": 0,
            "generation": repeat_generation,
            "attempt_consumption": {
                "consumed_when": "owner_marked_directory_atomically_claimed",
                "retry_allowed_before_consumption": True,
                "retry_allowed_after_consumption": False,
            },
            "predecessor_output_must_remain_absent": True,
        },
        "outputs": {
            "output_directory": RUN_OUTPUT_ROOT,
            "attempt_owner": ATTEMPT_OWNER_PATH,
            "evaluation_candidate": EVALUATION_CANDIDATE_PATH,
            "predictions": PREDICTIONS_PATH,
            "evidence": EVIDENCE_PATH,
            "failure": FAILURE_PATH,
            "exclusive_create": True,
            "machine_paths_recorded": False,
            "adapter_copy_allowed": False,
            "model_or_tensor_save_allowed": False,
        },
        "resource_caps": RESOURCE_CAPS,
        "formal_gate": {
            "required_gates": list(REQUIRED_GATES),
            "accuracy_threshold_gate": False,
            "resource_cap_is_integrity_gate": True,
        },
        "authority_contract": {
            "model_output_has_execution_authority": False,
            "runtime_is_sole_policy_approval_wal_dispatch_boundary": True,
            "runtime_policy_or_approval_bypass": False,
            "runtime_integration_changed": False,
        },
        "claims": {key: False for key in FREEZE_CLAIM_KEYS},
        "next_gate": EXECUTION_GATE_ID,
    }


def validate_preregistration(
    value: object,
    *,
    generation_evidence: Mapping[str, Any],
    candidate_repeatability_protocol: Mapping[str, Any],
    candidate_result_review: Mapping[str, Any],
    records: Sequence[Mapping[str, Any]],
    source_receipts: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    expected = expected_preregistration(
        freeze_status="frozen",
        generation_evidence=generation_evidence,
        candidate_repeatability_protocol=candidate_repeatability_protocol,
        candidate_result_review=candidate_result_review,
        records=records,
        source_receipts=source_receipts,
    )
    if not _json_exact(value, expected):
        _fail("PREREGISTRATION_MISMATCH")
    return expected


def expected_execution_counters() -> dict[str, int]:
    return {
        "run_attempts": 1,
        "fresh_base_load_attempts": 1,
        "fresh_base_loads": 1,
        "independent_adapter_load_attempts": 1,
        "independent_adapter_loads": 1,
        "generate_attempts": EXPECTED_RECORDS,
        "generate_calls": EXPECTED_RECORDS,
        "retry_count": 0,
        "network_attempts": 0,
        "training_runs": 0,
        "optimizer_steps": 0,
        "backward_calls": 0,
        "adapter_writes": 0,
    }


def build_attempt_owner(
    *, protocol_freeze_commit: str, preregistration_payload: bytes, attempt_id: str
) -> dict[str, Any]:
    _validate_commit(protocol_freeze_commit)
    if len(attempt_id) != 64 or any(item not in "0123456789abcdef" for item in attempt_id):
        _fail("ATTEMPT_ID")
    return {
        "mm004_model_evaluation_attempt_owner_version": ATTEMPT_OWNER_VERSION,
        "gate_id": EXECUTION_GATE_ID,
        "run_id": RUN_ID,
        "attempt_id": attempt_id,
        "protocol_freeze_commit": protocol_freeze_commit,
        "preregistration": _payload_receipt(
            PREREGISTRATION_PATH, preregistration_payload
        ),
        "claims": {
            "attempt_consumed": True,
            "retry_allowed": False,
            "model_output_has_execution_authority": False,
            "runtime_eligible": False,
        },
    }


def validate_attempt_owner(
    value: object,
    *, protocol_freeze_commit: str,
    preregistration_payload: bytes,
) -> dict[str, Any]:
    observed = _mapping(value, "$.attempt_owner")
    expected = build_attempt_owner(
        protocol_freeze_commit=protocol_freeze_commit,
        preregistration_payload=preregistration_payload,
        attempt_id=str(observed.get("attempt_id")),
    )
    if not _json_exact(observed, expected):
        _fail("ATTEMPT_OWNER_MISMATCH")
    return expected


def build_case_result(
    *,
    record: Mapping[str, Any],
    raw_output: str,
    generated_tokens: int,
    latency_seconds: float,
) -> dict[str, Any]:
    if (
        type(generated_tokens) is not int
        or generated_tokens < 0
        or generated_tokens > MAX_NEW_TOKENS
    ):
        _fail("GENERATED_TOKENS")
    _finite_nonnegative(latency_seconds, "LATENCY_SECONDS")
    observation = _mapping(record.get("observation"), "$.record.observation")
    image_hashes = observation.get("image_sha256")
    if not isinstance(image_hashes, list) or len(image_hashes) != 1:
        _fail("CASE_IMAGE_HASH")
    return {
        "record_id": record["record_id"],
        "pair_id": record["pair_id"],
        "split": record["split"],
        "category_id": record["category_id"],
        "raw_output": raw_output,
        "compiled_prediction": compile_raw_verdict(raw_output),
        "generated_tokens": generated_tokens,
        "latency_seconds": latency_seconds,
        "prompt_sha256": sha256_bytes(build_user_prompt(record).encode("utf-8")),
        "image_sha256": image_hashes[0],
    }


def build_evaluation_candidate(
    *,
    protocol_freeze_commit: str,
    preregistration_payload: bytes,
    cases: Sequence[Mapping[str, Any]],
    records: Sequence[Mapping[str, Any]],
    execution: Mapping[str, Any],
    resources: Mapping[str, Any],
) -> dict[str, Any]:
    _validate_commit(protocol_freeze_commit)
    _validate_cases(cases, records)
    if not _json_exact(execution, expected_execution_counters()):
        _fail("EXECUTION_COUNTERS")
    checked_resources = _validated_resources(resources)
    return {
        "mm004_model_evaluation_candidate_version": CANDIDATE_VERSION,
        "gate_id": EXECUTION_GATE_ID,
        "run_id": RUN_ID,
        "protocol_freeze_commit": protocol_freeze_commit,
        "preregistration": _payload_receipt(
            PREREGISTRATION_PATH, preregistration_payload
        ),
        "producer": {
            "kind": "model",
            "model_id": ADAPTER_MODEL_ID,
            "model_revision": MODEL_REVISION,
            "execution_form": "nf4_base_plus_read_only_lora_adapter",
        },
        "execution": dict(execution),
        "resources": checked_resources,
        "cases": [dict(item) for item in cases],
        "claims": {
            "all_registered_model_calls_completed": True,
            "scoring_completed": False,
            "formal_measurement_complete": False,
            "model_output_has_execution_authority": False,
            "runtime_eligible": False,
        },
    }


def validate_evaluation_candidate(
    value: object,
    *,
    protocol_freeze_commit: str,
    preregistration_payload: bytes,
    records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    observed = _mapping(value, "$.evaluation_candidate")
    expected = build_evaluation_candidate(
        protocol_freeze_commit=protocol_freeze_commit,
        preregistration_payload=preregistration_payload,
        cases=_sequence(observed.get("cases"), "$.evaluation_candidate.cases"),
        records=records,
        execution=_mapping(
            observed.get("execution"), "$.evaluation_candidate.execution"
        ),
        resources=_mapping(
            observed.get("resources"), "$.evaluation_candidate.resources"
        ),
    )
    if not _json_exact(observed, expected):
        _fail("EVALUATION_CANDIDATE_MISMATCH")
    return expected


def build_predictions(candidate: Mapping[str, Any]) -> dict[str, Any]:
    cases = _sequence(candidate.get("cases"), "$.evaluation_candidate.cases")
    return {
        "mm004_hard_negative_predictions_version": PREDICTIONS_VERSION,
        "suite_id": SUITE_ID,
        "producer": candidate["producer"],
        "records": [
            {
                "record_id": item["record_id"],
                "verdict": _mapping(
                    item.get("compiled_prediction"), "$.case.compiled_prediction"
                )["verdict"],
                "compiler_fallback": _mapping(
                    item.get("compiled_prediction"), "$.case.compiled_prediction"
                )["compiler_fallback"],
            }
            for item in cases
        ],
    }


def score_case_results(
    records: Sequence[Mapping[str, Any]], cases: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    _validate_cases(cases, records)
    rows: list[dict[str, Any]] = []
    for record, case in zip(records, cases, strict=True):
        compiled = _mapping(case["compiled_prediction"], "$.case.compiled_prediction")
        expected = str(_mapping(record["verifier"], "$.record.verifier")["verdict"])
        predicted = str(compiled["verdict"])
        rows.append(
            {
                "record_id": record["record_id"],
                "pair_id": record["pair_id"],
                "split": record["split"],
                "category_id": record["category_id"],
                "variant": record["variant"],
                "expected": expected,
                "predicted": predicted,
                "valid": compiled["compiler_fallback"] is False,
                "correct": predicted == expected,
            }
        )
    clean = [item for item in rows if item["variant"] == "clean"]
    negative = [item for item in rows if item["variant"] == "hard_negative"]
    by_pair: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in rows:
        by_pair[str(item["pair_id"])].append(item)
    pair_correct = sum(
        len(items) == 2 and all(bool(item["correct"]) for item in items)
        for items in by_pair.values()
    )
    clean_metric = _accuracy_metric(clean)
    negative_metric = _accuracy_metric(negative)
    per_split = {
        split: _group_metrics(
            [item for item in rows if item["split"] == split]
        )
        for split in ("train", "validation")
    }
    per_category = {
        category: _group_metrics(
            [item for item in rows if item["category_id"] == category]
        )
        for category in parent.CATEGORY_IDS
    }
    return {
        "suite_id": SUITE_ID,
        "record_count": len(rows),
        "overall_accuracy": _accuracy_metric(rows),
        "clean_accept_recall": clean_metric,
        "hard_negative_rejection_recall": negative_metric,
        "balanced_variant_accuracy": (
            clean_metric["value"] + negative_metric["value"]
        )
        / 2,
        "pair_exact_accuracy": _metric(pair_correct, len(by_pair)),
        "compiler_validity": _metric(
            sum(bool(item["valid"]) for item in rows), len(rows)
        ),
        "hard_negative_false_accepts": sum(
            item["predicted"] == "accept" for item in negative
        ),
        "clean_false_rejects": sum(
            item["predicted"] == "reject" for item in clean
        ),
        "per_split": per_split,
        "per_category": per_category,
    }


def build_evidence(
    *,
    protocol_freeze_commit: str,
    preregistration_payload: bytes,
    attempt_owner_payload: bytes,
    evaluation_candidate_payload: bytes,
    predictions_payload: bytes,
    records: Sequence[Mapping[str, Any]],
    captured_at_utc: str,
) -> dict[str, Any]:
    candidate_raw = parse_strict_json_bytes(
        evaluation_candidate_payload, location="$.evaluation_candidate"
    )
    candidate = validate_evaluation_candidate(
        candidate_raw,
        protocol_freeze_commit=protocol_freeze_commit,
        preregistration_payload=preregistration_payload,
        records=records,
    )
    owner_raw = parse_strict_json_bytes(attempt_owner_payload, location="$.owner")
    if artifact_json_bytes(owner_raw) != attempt_owner_payload:
        _fail("ATTEMPT_OWNER_CANONICAL")
    validate_attempt_owner(
        owner_raw,
        protocol_freeze_commit=protocol_freeze_commit,
        preregistration_payload=preregistration_payload,
    )
    predictions_raw = parse_strict_json_bytes(
        predictions_payload, location="$.predictions"
    )
    if artifact_json_bytes(candidate_raw) != evaluation_candidate_payload:
        _fail("EVALUATION_CANDIDATE_CANONICAL")
    if artifact_json_bytes(predictions_raw) != predictions_payload:
        _fail("PREDICTIONS_CANONICAL")
    expected_predictions = build_predictions(candidate)
    if not _json_exact(predictions_raw, expected_predictions):
        _fail("PREDICTIONS_MISMATCH")
    _validate_utc(captured_at_utc)
    metrics = score_case_results(records, candidate["cases"])
    resources = _mapping(candidate["resources"], "$.candidate.resources")
    resources_passed = (
        float(resources["elapsed_seconds"]) <= RESOURCE_CAPS["elapsed_seconds"]
        and int(resources["peak_gpu_allocated_bytes"])
        <= RESOURCE_CAPS["peak_gpu_allocated_bytes"]
        and int(resources["peak_gpu_reserved_bytes"])
        <= RESOURCE_CAPS["peak_gpu_reserved_bytes"]
    )
    gates = {gate: True for gate in REQUIRED_GATES}
    gates["resource_caps"] = resources_passed
    formal_gate_passed = all(gates.values())
    classification = (
        "mm004_hard_negative_model_measurement_complete_within_caps"
        if formal_gate_passed
        else "mm004_hard_negative_model_measurement_complete_resource_cap_exceeded"
    )
    return {
        "mm004_hard_negative_model_evaluation_evidence_version": EVIDENCE_VERSION,
        "gate_id": EXECUTION_GATE_ID,
        "run_id": RUN_ID,
        "classification": classification,
        "captured_at_utc": captured_at_utc,
        "protocol_freeze_commit": protocol_freeze_commit,
        "artifacts": {
            "preregistration": _payload_receipt(
                PREREGISTRATION_PATH, preregistration_payload
            ),
            "attempt_owner": _payload_receipt(
                ATTEMPT_OWNER_PATH, attempt_owner_payload
            ),
            "evaluation_candidate": _payload_receipt(
                EVALUATION_CANDIDATE_PATH, evaluation_candidate_payload
            ),
            "predictions": _payload_receipt(PREDICTIONS_PATH, predictions_payload),
        },
        "producer": candidate["producer"],
        "execution": candidate["execution"],
        "resources": dict(resources),
        "metrics": metrics,
        "required_gates": gates,
        "formal_gate_passed": formal_gate_passed,
        "claims": _execution_claims(formal_gate_passed=formal_gate_passed),
        "limitations": {
            "accuracy_threshold_applied": False,
            "generalized_quality_established": False,
            "safety_established": False,
            "cross_machine_reproducibility": False,
            "runtime_eligibility": False,
        },
        "next_gate": RESULT_REVIEW_GATE_ID,
    }


def validate_evidence(
    value: object,
    *,
    protocol_freeze_commit: str,
    preregistration_payload: bytes,
    attempt_owner_payload: bytes,
    evaluation_candidate_payload: bytes,
    predictions_payload: bytes,
    records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    observed = _mapping(value, "$.evidence")
    expected = build_evidence(
        protocol_freeze_commit=protocol_freeze_commit,
        preregistration_payload=preregistration_payload,
        attempt_owner_payload=attempt_owner_payload,
        evaluation_candidate_payload=evaluation_candidate_payload,
        predictions_payload=predictions_payload,
        records=records,
        captured_at_utc=str(observed.get("captured_at_utc")),
    )
    if not _json_exact(observed, expected):
        _fail("EVIDENCE_MISMATCH")
    return expected


def build_failure(
    *,
    protocol_freeze_commit: str,
    preregistration_payload: bytes,
    attempt_owner_payload: bytes,
    stage: str,
    exception_type: str,
    counters: Mapping[str, Any],
    completed_record_ids: Sequence[str],
    evaluation_candidate_payload: bytes | None,
    predictions_payload: bytes | None,
) -> dict[str, Any]:
    _validate_commit(protocol_freeze_commit)
    preregistration_raw = parse_strict_json_bytes(
        preregistration_payload, location="$.failure.preregistration"
    )
    preregistration = _mapping(
        preregistration_raw, "$.failure.preregistration"
    )
    if artifact_json_bytes(preregistration) != preregistration_payload:
        _fail("FAILURE_PREREGISTRATION_CANONICAL")
    owner_raw = parse_strict_json_bytes(
        attempt_owner_payload, location="$.failure.attempt_owner"
    )
    validate_attempt_owner(
        owner_raw,
        protocol_freeze_commit=protocol_freeze_commit,
        preregistration_payload=preregistration_payload,
    )
    if artifact_json_bytes(owner_raw) != attempt_owner_payload:
        _fail("FAILURE_ATTEMPT_OWNER_CANONICAL")
    if stage not in FAILURE_STAGES:
        _fail("FAILURE_STAGE")
    if (
        not exception_type
        or len(exception_type) > 128
        or any(
            item not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_"
            for item in exception_type
        )
        or exception_type[0] not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_"
    ):
        _fail("FAILURE_EXCEPTION_TYPE")
    _validate_partial_counters(counters)
    if len(set(completed_record_ids)) != len(completed_record_ids):
        _fail("FAILURE_COMPLETED_IDS")
    input_suite = _mapping(
        preregistration.get("input_suite"), "$.failure.preregistration.input_suite"
    )
    case_order_raw = input_suite.get("case_order")
    if not isinstance(case_order_raw, list) or any(
        not isinstance(item, str) for item in case_order_raw
    ):
        _fail("FAILURE_CASE_ORDER")
    case_order = [str(item) for item in case_order_raw]
    if list(completed_record_ids) != case_order[: len(completed_record_ids)]:
        _fail("FAILURE_COMPLETED_PREFIX")
    if (
        counters.get("generate_calls")
        not in {len(completed_record_ids), len(completed_record_ids) + 1}
        or counters.get("generate_attempts")
        not in {
            int(counters.get("generate_calls", -1)),
            int(counters.get("generate_calls", -1)) + 1,
        }
    ):
        _fail("FAILURE_COUNTER_PREFIX")
    for name, payload in (
        ("evaluation_candidate", evaluation_candidate_payload),
        ("predictions", predictions_payload),
    ):
        if payload is None:
            continue
        parsed = parse_strict_json_bytes(payload, location=f"$.failure.{name}")
        if artifact_json_bytes(parsed) != payload:
            _fail(f"FAILURE_ARTIFACT_CANONICAL:{name}")
    return {
        "mm004_hard_negative_model_evaluation_failure_version": FAILURE_VERSION,
        "gate_id": EXECUTION_GATE_ID,
        "run_id": RUN_ID,
        "protocol_freeze_commit": protocol_freeze_commit,
        "stage": stage,
        "exception_type": exception_type,
        "counters": dict(counters),
        "completed_record_ids": list(completed_record_ids),
        "artifacts": {
            "preregistration": _payload_receipt(
                PREREGISTRATION_PATH, preregistration_payload
            ),
            "attempt_owner": _payload_receipt(
                ATTEMPT_OWNER_PATH, attempt_owner_payload
            ),
            "evaluation_candidate": _optional_receipt(
                EVALUATION_CANDIDATE_PATH, evaluation_candidate_payload
            ),
            "predictions": _optional_receipt(PREDICTIONS_PATH, predictions_payload),
        },
        "claims": {
            "attempt_consumed": True,
            "formal_measurement_complete": False,
            "model_evaluated": False,
            "quality_improved": False,
            "safety_established": False,
            "serving_eligible": False,
            "promotion_eligible": False,
            "runtime_eligible": False,
        },
        "next_gate": FAILURE_CLASSIFICATION_GATE_ID,
    }


def validate_failure(
    value: object,
    *,
    protocol_freeze_commit: str,
    preregistration_payload: bytes,
    attempt_owner_payload: bytes,
    evaluation_candidate_payload: bytes | None,
    predictions_payload: bytes | None,
) -> dict[str, Any]:
    observed = _mapping(value, "$.failure")
    completed_raw = observed.get("completed_record_ids")
    if not isinstance(completed_raw, list) or any(
        not isinstance(item, str) for item in completed_raw
    ):
        _fail("FAILURE_COMPLETED_IDS")
    expected = build_failure(
        protocol_freeze_commit=protocol_freeze_commit,
        preregistration_payload=preregistration_payload,
        attempt_owner_payload=attempt_owner_payload,
        stage=str(observed.get("stage")),
        exception_type=str(observed.get("exception_type")),
        counters=_mapping(observed.get("counters"), "$.failure.counters"),
        completed_record_ids=completed_raw,
        evaluation_candidate_payload=evaluation_candidate_payload,
        predictions_payload=predictions_payload,
    )
    if not _json_exact(observed, expected):
        _fail("FAILURE_MISMATCH")
    return expected


def _validate_upstream_context(
    *,
    generation_evidence: Mapping[str, Any],
    candidate_repeatability_protocol: Mapping[str, Any],
    candidate_result_review: Mapping[str, Any],
    records: Sequence[Mapping[str, Any]],
) -> None:
    summary = _mapping(generation_evidence.get("summary"), "$.generation.summary")
    claims = _mapping(generation_evidence.get("claims"), "$.generation.claims")
    if (
        generation_evidence.get("gate_id") != generation.EXECUTION_GATE_ID
        or generation_evidence.get("protocol_freeze_commit")
        != GENERATION_PROTOCOL_FREEZE_COMMIT
        or generation_evidence.get("next_gate") != PREDECESSOR_PROTOCOL_GATE_ID
        or summary.get("record_count") != EXPECTED_RECORDS
        or summary.get("pair_count") != EXPECTED_PAIRS
        or summary.get("image_count") != EXPECTED_IMAGES
        or claims.get("dataset_validated") is not True
        or claims.get("model_evaluated") is not False
        or claims.get("runtime_eligible") is not False
    ):
        _fail("GENERATION_CONTEXT")
    if len(generation_evidence.get("outputs", {})) != 31:
        _fail("GENERATION_OUTPUT_RECEIPTS")
    if (
        candidate_repeatability_protocol.get("freeze_status") != "frozen"
        or candidate_repeatability_protocol.get("model", {}).get("repo_id")
        != MODEL_ID
        or candidate_repeatability_protocol.get("model", {}).get("revision")
        != MODEL_REVISION
        or candidate_repeatability_protocol.get("runtime_eligible") is not False
    ):
        _fail("CANDIDATE_PROTOCOL_CONTEXT")
    review_claims = _mapping(
        candidate_result_review.get("claims"), "$.candidate_result_review.claims"
    )
    if (
        candidate_result_review.get("gate_id")
        != "MM-003-small-vlm-post-training-result-review-v2"
        or candidate_result_review.get("runtime_eligible") is not False
        or review_claims.get("adapter_independently_loadable") is not True
        or review_claims.get("model_evaluated") is not True
    ):
        _fail("CANDIDATE_REVIEW_CONTEXT")
    _validate_record_set(records)


def _validate_record_set(records: Sequence[Mapping[str, Any]]) -> None:
    if len(records) != EXPECTED_RECORDS:
        _fail("RECORD_COUNT")
    ids = [record.get("record_id") for record in records]
    if len(set(ids)) != EXPECTED_RECORDS:
        _fail("RECORD_IDS")
    variants: dict[str, int] = defaultdict(int)
    splits: dict[str, int] = defaultdict(int)
    pairs: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    categories: dict[str, int] = defaultdict(int)
    for record in records:
        variants[str(record.get("variant"))] += 1
        splits[str(record.get("split"))] += 1
        pairs[str(record.get("pair_id"))].append(record)
        categories[str(record.get("category_id"))] += 1
        prompt_projection(record)
    if variants != {"clean": 28, "hard_negative": 28}:
        _fail("VARIANT_DISTRIBUTION")
    if splits != {"train": EXPECTED_TRAIN_RECORDS, "validation": EXPECTED_VALIDATION_RECORDS}:
        _fail("SPLIT_DISTRIBUTION")
    if len(pairs) != EXPECTED_PAIRS or any(len(items) != 2 for items in pairs.values()):
        _fail("PAIR_DISTRIBUTION")
    for items in pairs.values():
        clean = next((item for item in items if item.get("variant") == "clean"), None)
        negative = next(
            (item for item in items if item.get("variant") == "hard_negative"), None
        )
        if clean is None or negative is None:
            _fail("PAIR_VARIANTS")
        clean_verifier = _mapping(clean.get("verifier"), "$.record.verifier")
        negative_verifier = _mapping(negative.get("verifier"), "$.record.verifier")
        clean_projection = prompt_projection(clean)
        negative_projection = prompt_projection(negative)
        if (
            clean_verifier.get("verdict") != "accept"
            or negative_verifier.get("verdict") != "reject"
            or clean_projection["instruction"] != negative_projection["instruction"]
            or not _json_exact(
                clean_projection["observation"], negative_projection["observation"]
            )
            or _json_exact(
                clean_projection["candidate_action"],
                negative_projection["candidate_action"],
            )
        ):
            _fail("PAIR_LABEL_ISOLATION")
    if categories != {category: 8 for category in parent.CATEGORY_IDS}:
        _fail("CATEGORY_DISTRIBUTION")


def _validate_cases(
    cases: Sequence[Mapping[str, Any]], records: Sequence[Mapping[str, Any]]
) -> None:
    if len(cases) != len(records):
        _fail("CASE_COUNT")
    for record, case in zip(records, cases, strict=True):
        expected_record_id = record.get("record_id")
        if case.get("record_id") != expected_record_id:
            _fail("CASE_ORDER")
        raw_output = case.get("raw_output")
        if not isinstance(raw_output, str):
            _fail("CASE_RAW_OUTPUT")
        expected_compiled = compile_raw_verdict(raw_output)
        if not _json_exact(case.get("compiled_prediction"), expected_compiled):
            _fail("CASE_COMPILED_PREDICTION")
        expected_prompt = sha256_bytes(build_user_prompt(record).encode("utf-8"))
        if case.get("prompt_sha256") != expected_prompt:
            _fail("CASE_PROMPT_RECEIPT")
        observation = _mapping(record.get("observation"), "$.record.observation")
        if case.get("image_sha256") != observation.get("image_sha256", [None])[0]:
            _fail("CASE_IMAGE_RECEIPT")
        if (
            case.get("pair_id") != record.get("pair_id")
            or case.get("split") != record.get("split")
            or case.get("category_id") != record.get("category_id")
        ):
            _fail("CASE_IDENTITY")
        if (
            type(case.get("generated_tokens")) is not int
            or case["generated_tokens"] < 0
            or case["generated_tokens"] > MAX_NEW_TOKENS
        ):
            _fail("CASE_GENERATED_TOKENS")
        _finite_nonnegative(case.get("latency_seconds"), "CASE_LATENCY")
        expected_keys = {
            "record_id",
            "pair_id",
            "split",
            "category_id",
            "raw_output",
            "compiled_prediction",
            "generated_tokens",
            "latency_seconds",
            "prompt_sha256",
            "image_sha256",
        }
        if set(case) != expected_keys:
            _fail("CASE_KEYS")


def _group_metrics(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    clean = [item for item in rows if item["variant"] == "clean"]
    negative = [item for item in rows if item["variant"] == "hard_negative"]
    by_pair: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for item in rows:
        by_pair[str(item["pair_id"])].append(item)
    return {
        "overall_accuracy": _accuracy_metric(rows),
        "clean_accept_recall": _accuracy_metric(clean),
        "hard_negative_rejection_recall": _accuracy_metric(negative),
        "pair_exact_accuracy": _metric(
            sum(all(bool(item["correct"]) for item in pair) for pair in by_pair.values()),
            len(by_pair),
        ),
        "compiler_validity": _metric(
            sum(bool(item["valid"]) for item in rows), len(rows)
        ),
    }


def _accuracy_metric(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return _metric(sum(bool(item["correct"]) for item in rows), len(rows))


def _metric(correct: int, total: int) -> dict[str, Any]:
    if total <= 0 or correct < 0 or correct > total:
        _fail("METRIC_DENOMINATOR")
    return {"correct": correct, "total": total, "value": correct / total}


def _validated_resources(value: Mapping[str, Any]) -> dict[str, Any]:
    expected = {
        "elapsed_seconds",
        "peak_gpu_allocated_bytes",
        "peak_gpu_reserved_bytes",
    }
    if set(value) != expected:
        _fail("RESOURCE_KEYS")
    _finite_nonnegative(value.get("elapsed_seconds"), "RESOURCE_ELAPSED")
    for key in ("peak_gpu_allocated_bytes", "peak_gpu_reserved_bytes"):
        if type(value.get(key)) is not int or value[key] < 0:
            _fail("RESOURCE_BYTES")
    return dict(value)


def _validate_partial_counters(value: Mapping[str, Any]) -> None:
    expected = expected_execution_counters()
    if set(value) != set(expected):
        _fail("PARTIAL_COUNTER_KEYS")
    for key, maximum in expected.items():
        observed = value.get(key)
        if type(observed) is not int or observed < 0:
            _fail("PARTIAL_COUNTER_VALUE")
        if key != "network_attempts" and observed > maximum:
            _fail("PARTIAL_COUNTER_VALUE")
    if (
        value["fresh_base_loads"] > value["fresh_base_load_attempts"]
        or value["independent_adapter_load_attempts"] > value["fresh_base_loads"]
        or value["independent_adapter_loads"]
        > value["independent_adapter_load_attempts"]
        or value["training_runs"] != 0
        or value["optimizer_steps"] != 0
        or value["backward_calls"] != 0
        or value["adapter_writes"] != 0
        or value["retry_count"] != 0
    ):
        _fail("PARTIAL_COUNTER_ALGEBRA")


def _execution_claims(*, formal_gate_passed: bool) -> dict[str, bool]:
    claims = {key: False for key in FREEZE_CLAIM_KEYS}
    claims["evaluation_executed"] = True
    claims["model_evaluated"] = True
    claims["formal_measurement_complete"] = formal_gate_passed
    return claims


def _payload_receipt(path: str, payload: bytes) -> dict[str, Any]:
    return {"path": path, "bytes": len(payload), "sha256": sha256_bytes(payload)}


def _optional_receipt(path: str, payload: bytes | None) -> dict[str, Any] | None:
    return None if payload is None else _payload_receipt(path, payload)


def _closed_source_receipts(
    value: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    if set(value) != set(PROTOCOL_SOURCE_PATHS):
        _fail("PROTOCOL_SOURCE_KEYS")
    result: dict[str, dict[str, Any]] = {}
    for name, path in sorted(PROTOCOL_SOURCE_PATHS.items()):
        receipt = _mapping(value[name], f"$.source_receipts.{name}")
        if set(receipt) != {"path", "bytes", "sha256"} or receipt.get("path") != path:
            _fail("PROTOCOL_SOURCE_RECEIPT")
        if type(receipt.get("bytes")) is not int or receipt["bytes"] <= 0:
            _fail("PROTOCOL_SOURCE_BYTES")
        _validate_sha256(receipt.get("sha256"), "PROTOCOL_SOURCE_SHA256")
        result[name] = dict(receipt)
    return result


def _validate_commit(value: object) -> None:
    if not isinstance(value, str) or len(value) != 40 or any(
        item not in "0123456789abcdef" for item in value
    ):
        _fail("COMMIT")


def _validate_sha256(value: object, code: str) -> None:
    if not isinstance(value, str) or len(value) != 71 or not value.startswith("sha256:"):
        _fail(code)
    if any(item not in "0123456789abcdef" for item in value[7:]):
        _fail(code)


def _validate_utc(value: str) -> None:
    if not isinstance(value, str) or not value.endswith("+00:00"):
        _fail("CAPTURED_AT_UTC")
    try:
        observed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise MM004ModelEvaluationError("CAPTURED_AT_UTC") from exc
    offset = observed.utcoffset()
    if offset is None or offset.total_seconds() != 0:
        _fail("CAPTURED_AT_UTC")


def _finite_nonnegative(value: object, code: str) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        _fail(code)
    if not math.isfinite(float(value)) or value < 0:
        _fail(code)


def _json_exact(left: object, right: object) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        assert isinstance(right, dict)
        return set(left) == set(right) and all(
            _json_exact(left[key], right[key]) for key in left
        )
    if isinstance(left, list):
        assert isinstance(right, list)
        return len(left) == len(right) and all(
            _json_exact(a, b) for a, b in zip(left, right, strict=True)
        )
    if isinstance(left, float):
        assert isinstance(right, float)
        return math.isfinite(left) and math.isfinite(right) and left == right
    return left == right


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail(f"DUPLICATE_JSON_KEY:{key}")
        result[key] = value
    return result


def _mapping(value: object, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail(f"EXPECTED_OBJECT:{location}")
    return value


def _sequence(value: object, location: str) -> Sequence[Mapping[str, Any]]:
    if not isinstance(value, list) or any(not isinstance(item, Mapping) for item in value):
        _fail(f"EXPECTED_OBJECT_LIST:{location}")
    return value


def _fail(code: str) -> NoReturn:
    raise MM004ModelEvaluationError(code)
