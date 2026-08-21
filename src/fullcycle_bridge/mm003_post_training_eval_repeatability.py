"""Fail-closed contract for the MM-003 post-training evaluation replay.

The contract is deliberately training-neutral and execution-neutral.  It
freezes one same-machine replay of the unchanged v2 Adapter and MM-002 suite,
validates completed replay payloads, and derives layered raw, compiled, and
metric comparisons.  It never imports ML dependencies, loads a model, mutates
the Adapter, or writes an artifact.
"""

from __future__ import annotations

import copy
import re
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any, NoReturn, cast

from . import gui_grounding_eval as base_scorer
from . import gui_grounding_eval_v2 as scorer
from . import mm003_post_training_protocol_v2 as upstream

PREREGISTRATION_VERSION = 1
EVIDENCE_VERSION = 1
FAILURE_VERSION = 1
CANDIDATE_VERSION = 1
ATTEMPT_OWNER_VERSION = 1

PROTOCOL_GATE_ID = "MM-003-small-vlm-post-training-eval-repeatability-protocol-v1"
EXECUTION_GATE_ID = "MM-003-small-vlm-post-training-eval-repeatability-execution-v1"
RESULT_REVIEW_GATE_ID = (
    "MM-003-small-vlm-post-training-eval-repeatability-result-review-v1"
)
FAILURE_CLASSIFICATION_GATE_ID = (
    "MM-003-small-vlm-post-training-eval-repeatability-failure-classification-v1"
)
EXPERIMENT_ID = "mm003-qwen2.5-vl-3b-qlora-sft-v2-eval-repeatability-v1"
RUN_ID = "mm003-qwen2.5-vl-3b-qlora-sft-v2-eval-replay-r1"
OUTPUT_ID = "mm003-qlora-sft-v2-eval-repeatability-v1"
MODEL_SNAPSHOT_ROOT = (
    "work/model-cache/mm003-model/"
    "models--Qwen--Qwen2.5-VL-3B-Instruct/snapshots/"
    "66285546d2b821cf421d4f5eb2576359d3770cd3"
)
FORMAL_PYTHON_ARGS = ["-I", "-B", "-X", "pycache_prefix=NUL"]
FORMAL_PYTHON_PATH = "work/training-env/Scripts/python.exe"

PREREGISTRATION_PATH = (
    "configs/mm003_small_vlm_post_training_eval_repeatability_protocol_v1.json"
)
RUN_OUTPUT_ROOT = "work/evaluation-runs/mm003-qlora-sft-v2-eval-repeatability-v1"
PREDICTIONS_ARTIFACT = f"{RUN_OUTPUT_ROOT}/predictions.json"
EVALUATION_CANDIDATE_ARTIFACT = f"{RUN_OUTPUT_ROOT}/evaluation-candidate.json"
ATTEMPT_OWNER_ARTIFACT = f"{RUN_OUTPUT_ROOT}/attempt-owner.json"
EVIDENCE_ARTIFACT = f"{RUN_OUTPUT_ROOT}/evidence.json"
FAILURE_ARTIFACT = f"{RUN_OUTPUT_ROOT}/failure.json"
ADAPTER_ROOT = "baseline/adapters/mm003-qwen2.5-vl-3b-qlora-sft-v2"

UPSTREAM_PREREGISTRATION_RECEIPT = {
    "path": upstream.PREREGISTRATION_PATH,
    "bytes": 26_553,
    "sha256": "sha256:02e36d5981e0ed4ac90bfdb3c5cc9c9e1f78ff29ff927020b0a41ebb27f55c0e",
}
REFERENCE_PREDICTIONS_RECEIPT = {
    "path": "baseline/mm003-qwen2.5-vl-3b-qlora-sft-v2-predictions.json",
    "bytes": 2_241,
    "sha256": "sha256:c2c703e5896fe64df9e156bda9d38975b92c1bf18c72f74f5a232dcbbbc4a028",
}
REFERENCE_TRAINING_RUN_RECEIPT = {
    "path": "baseline/mm003-qwen2.5-vl-3b-qlora-sft-v2-training-run.json",
    "bytes": 6_853,
    "sha256": "sha256:474595081a20c46a62f664459b734d57ec03c8ddf121c9aedc055e16a052c516",
}
REFERENCE_EVIDENCE_RECEIPT = {
    "path": "baseline/mm003-qwen2.5-vl-3b-qlora-sft-v2-evidence.json",
    "bytes": 21_122,
    "sha256": "sha256:2190281e3e8acf97139e08c9949535a07b326897e23c5999a7f4750fccedabd5",
}
RESULT_REVIEW_RECEIPT = {
    "path": "baseline/mm003-qwen2.5-vl-3b-qlora-sft-v2-result-review.json",
    "bytes": 11_311,
    "sha256": "sha256:3dff57b17eb4fc9966ab53fe92faea8921fb34b485e389aaa19af64610db957d",
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
    "bridge_package_init": "src/fullcycle_bridge/__init__.py",
    "bridge_consumer": "src/fullcycle_bridge/consumer.py",
    "base_contract_v1": "src/fullcycle_bridge/mm003_baseline_protocol.py",
    "base_contract_v2": "src/fullcycle_bridge/mm003_baseline_protocol_v2.py",
    "base_runner_v1": "scripts/run_mm003_multimodal_gui_action_baseline.py",
    "base_runner_v2": "scripts/run_mm003_multimodal_gui_action_baseline_v2.py",
    "baseline_failure_classification": (
        "src/fullcycle_bridge/mm003_baseline_failure_classification.py"
    ),
    "base_scorer_v1": "src/fullcycle_bridge/gui_grounding_eval.py",
    "base_scorer_v2": "src/fullcycle_bridge/gui_grounding_eval_v2.py",
    "baseline_result_validator_v2": "scripts/validate_mm003_baseline_v2_evidence.py",
    "post_training_contract_v1": (
        "src/fullcycle_bridge/mm003_post_training_protocol.py"
    ),
    "post_training_contract_v2": (
        "src/fullcycle_bridge/mm003_post_training_protocol_v2.py"
    ),
    "post_training_runner_v2": "scripts/run_mm003_qlora_post_training_v2.py",
    "repeatability_contract": (
        "src/fullcycle_bridge/mm003_post_training_eval_repeatability.py"
    ),
    "repeatability_runner": ("scripts/run_mm003_post_training_eval_repeatability.py"),
    "upstream_result_validator": ("scripts/validate_mm003_post_training_v2_result.py"),
    "training_lock": "requirements/mm003_qlora_training.lock",
}

MODEL_ID = upstream.MODEL_ID
MODEL_REVISION = upstream.MODEL_REVISION
ADAPTER_MODEL_ID = upstream.ADAPTER_MODEL_ID
LOCKED_ENVIRONMENT = upstream.LOCKED_ENVIRONMENT
CASE_ORDER = tuple(upstream.baseline.CASE_ORDER)
EXPECTED_CASES = len(CASE_ORDER)
SEED = upstream.TRAINING_SEED
RESOURCE_CAPS = {
    "elapsed_seconds": 1_800.0,
    "peak_gpu_allocated_bytes": 16_500_000_000,
    "peak_gpu_reserved_bytes": 16_500_000_000,
}

REQUIRED_GATES = [
    "protocol_integrity",
    "reference_result_integrity",
    "exact_model_files",
    "exact_adapter_files",
    "locked_environment",
    "unchanged_mm002_inputs",
    "offline_single_replay",
    "prediction_identity",
    "attempt_ownership",
    "candidate_and_predictions_binding",
    "layered_comparison_complete",
    "resource_caps",
    "fail_closed_claims",
]

MEASUREMENT_CLASSIFICATION = (
    "same_machine_fixed_eval_repeatability_measurement_complete"
)
RESOURCE_EXCEEDED_CLASSIFICATION = (
    "same_machine_fixed_eval_repeatability_measurement_resource_exceeded"
)
INTEGRITY_FAILURE_CLASSIFICATION = (
    "same_machine_fixed_eval_repeatability_measurement_integrity_failed"
)
INCOMPLETE_CLASSIFICATION = "same_machine_fixed_eval_replay_incomplete"
FAILURE_STAGES = (
    "output_reservation",
    "dependency_import",
    "locked_environment",
    "independent_adapter_load_and_eval",
    "evaluation_candidate",
    "total_scoring",
    "predictions",
    "adapter_postcondition",
    "evidence",
)
CLAIM_KEYS = (
    "replay_executed",
    "model_evaluated",
    "formal_measurement_complete",
    "same_machine_eval_repeatability_established",
    "training_repeatability_established",
    "cross_machine_reproducibility",
    "resource_repeatability_established",
    "generalized_quality_improvement_established",
    "quality_improved",
    "real_content_behavior_established",
    "safety_rejection_success_established",
    "direct_desktop_execution_established",
    "merged_artifact",
    "portable_artifact",
    "commercial_use_eligible",
    "serving_eligible",
    "promotion_eligible",
    "runtime_eligible",
)

_SHA256 = re.compile(r"sha256:[0-9a-f]{64}\Z")


class MM003EvalRepeatabilityError(ValueError):
    """Raised when a frozen protocol or replay payload fails closed."""


def artifact_json_bytes(value: Mapping[str, Any]) -> bytes:
    return upstream.artifact_json_bytes(value)


def canonical_json_bytes(value: object) -> bytes:
    return upstream.canonical_json_bytes(value)


def sha256_bytes(payload: bytes) -> str:
    return upstream.sha256_bytes(payload)


def parse_strict_json_bytes(payload: bytes, *, location: str) -> object:
    return upstream.parse_strict_json_bytes(payload, location=location)


def expected_preregistration(
    *,
    freeze_status: str,
    source_hashes: Mapping[str, str],
    upstream_preregistration: Mapping[str, Any],
    reference_evidence: Mapping[str, Any],
    reference_predictions: Mapping[str, Any],
    result_review: Mapping[str, Any],
    suite: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the single exact protocol object from authenticated v2 evidence."""

    if freeze_status not in {"draft", "frozen"}:
        _fail("FREEZE_STATUS_INVALID")
    _validate_source_hashes(source_hashes)
    reference = validate_reference_payloads(
        upstream_preregistration=upstream_preregistration,
        reference_evidence=reference_evidence,
        reference_predictions=reference_predictions,
        result_review=result_review,
        suite=suite,
    )
    upstream_sources = _mapping(
        _mapping(
            upstream_preregistration.get("source_lineage"),
            "$.upstream.source_lineage",
        ).get("protocol_sources"),
        "$.upstream.source_lineage.protocol_sources",
    )
    suite = _mapping(
        _mapping(
            upstream_preregistration.get("source_lineage"),
            "$.upstream.source_lineage",
        ).get("unchanged_mm002_eval"),
        "$.upstream.source_lineage.unchanged_mm002_eval",
    )
    generation = {
        "seed": SEED,
        "processor_min_pixels": 256 * 28 * 28,
        "processor_max_pixels": 1280 * 28 * 28,
        "processor_use_fast": False,
        "quantization": {
            "load_in_4bit": True,
            "bnb_4bit_quant_type": "nf4",
            "bnb_4bit_compute_dtype": "bfloat16",
            "bnb_4bit_use_double_quant": True,
        },
        "attn_implementation": "sdpa",
        "device_map": {"": 0},
        "do_sample": False,
        "max_new_tokens": 256,
        "repetition_penalty": 1.05,
        "temperature": None,
        "use_cache": True,
        "clean_up_tokenization_spaces": False,
    }
    return {
        "preregistration_version": PREREGISTRATION_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "run_id": RUN_ID,
        "output_id": OUTPUT_ID,
        "gate_id": PROTOCOL_GATE_ID,
        "freeze_status": freeze_status,
        "decision": "outcome_neutral_same_machine_fixed_eval_replay_protocol",
        "authority_contract": {
            "model_output_has_execution_authority": False,
            "direct_desktop_execution": False,
            "runtime_policy_or_approval_bypass": False,
            "runtime_integration_changed": False,
        },
        "source_lineage": {
            "upstream_preregistration": copy.deepcopy(UPSTREAM_PREREGISTRATION_RECEIPT),
            "upstream_result_review": copy.deepcopy(RESULT_REVIEW_RECEIPT),
            "reference_bad_case_taxonomy": copy.deepcopy(
                result_review["evaluation"]["bad_case_taxonomy"]
            ),
            "reference_predictions": copy.deepcopy(REFERENCE_PREDICTIONS_RECEIPT),
            "reference_training_run": copy.deepcopy(REFERENCE_TRAINING_RUN_RECEIPT),
            "reference_evidence": copy.deepcopy(REFERENCE_EVIDENCE_RECEIPT),
            "adapter": copy.deepcopy(ADAPTER_RECEIPTS),
            "bitsandbytes_wheel": copy.deepcopy(upstream.BITSANDBYTES_WHEEL),
            "unchanged_mm002_eval": copy.deepcopy(dict(suite)),
            "upstream_protocol_sources": copy.deepcopy(dict(upstream_sources)),
            "protocol_sources": {
                name: {"path": PROTOCOL_SOURCE_PATHS[name], "sha256": digest}
                for name, digest in source_hashes.items()
            },
        },
        "model": copy.deepcopy(upstream_preregistration["model"]),
        "environment": copy.deepcopy(upstream_preregistration["environment"]),
        "execution_protocol": {
            "model_snapshot_root": MODEL_SNAPSHOT_ROOT,
            "python_invocation": {
                "executable": FORMAL_PYTHON_PATH,
                "working_directory": ".",
                "required_args": list(FORMAL_PYTHON_ARGS),
                "isolated": True,
                "safe_path": True,
                "dont_write_bytecode": True,
                "pycache_prefix": "NUL",
                "local_source_pyc_allowed": False,
            },
            "run_count": 1,
            "fresh_base_load_attempts": 1,
            "fresh_base_loads": 1,
            "independent_adapter_load_attempts": 1,
            "independent_adapter_loads": 1,
            "full_eval_run_attempts": 1,
            "full_eval_runs": 1,
            "generate_attempts": EXPECTED_CASES,
            "generate_calls": EXPECTED_CASES,
            "training_runs": 0,
            "optimizer_steps": 0,
            "backward_calls": 0,
            "adapter_writes": 0,
            "network_attempts": 0,
            "case_order": list(CASE_ORDER),
            "retry_count": 0,
            "network_used": False,
            "local_files_only": True,
            "adapter_trainable": False,
            "training_allowed": False,
            "adapter_mutation_allowed": False,
            "generation": generation,
            "prompt": {
                "system_prompt_sha256": sha256_bytes(
                    upstream.baseline.SYSTEM_PROMPT.encode("utf-8")
                ),
                "user_prompt_builder": "build_user_prompt",
                "suite_answers_available_to_model": False,
            },
            "attempt_consumption": {
                "consumed_when": (
                    "owner_marked_staging_directory_atomically_renamed_to_"
                    "fixed_output"
                ),
                "attempt_owner_written_before_consumption": True,
                "retry_allowed_before_consumption": True,
                "retry_allowed_after_consumption": False,
            },
        },
        "comparison_protocol": {
            "scope": "same_recorded_machine_environment_fixed_nine_case_eval",
            "reference_case_order": list(CASE_ORDER),
            "reference_raw_outputs_sha256": reference["raw_outputs_sha256"],
            "reference_compiled_predictions_sha256": reference[
                "compiled_predictions_sha256"
            ],
            "reference_metrics_sha256": reference["metrics_sha256"],
            "raw_output": {
                "comparison": "exact_utf8_string",
                "normalization_allowed": False,
                "required_exact": EXPECTED_CASES,
            },
            "compiled_prediction": {
                "reference_recompiled": True,
                "replay_recompiled": True,
                "comparison": "exact_canonical_json",
                "required_exact": EXPECTED_CASES,
            },
            "metrics": {
                "reference_recomputed": True,
                "replay_recomputed": True,
                "comparison": "exact_structured_equality",
                "quality_threshold_required": False,
                "per_metric_exact_comparison_required": True,
            },
            "resources": {
                "formal_execution_caps_registered": True,
                "cross_run_resource_repeatability_comparison_required": False,
                "repeatability_claimed": False,
            },
        },
        "resource_caps": copy.deepcopy(RESOURCE_CAPS),
        "outputs": {
            "output_id": OUTPUT_ID,
            "output_directory": RUN_OUTPUT_ROOT,
            "predictions": PREDICTIONS_ARTIFACT,
            "evaluation_candidate": EVALUATION_CANDIDATE_ARTIFACT,
            "attempt_owner": ATTEMPT_OWNER_ARTIFACT,
            "evidence": EVIDENCE_ARTIFACT,
            "failure": FAILURE_ARTIFACT,
            "exclusive_create": True,
            "machine_paths_recorded": False,
            "adapter_copy_allowed": False,
            "model_or_tensor_save_allowed": False,
        },
        "formal_gate": {
            "required_gates": list(REQUIRED_GATES),
            "quality_threshold_required": False,
            "formal_gate_passed": False,
        },
        "outcome_classifications": {
            "completed_measurement": MEASUREMENT_CLASSIFICATION,
            "resource_exceeded": RESOURCE_EXCEEDED_CLASSIFICATION,
            "integrity_failed": INTEGRITY_FAILURE_CLASSIFICATION,
            "incomplete_after_consumption": (
                "same_machine_fixed_eval_replay_incomplete"
            ),
        },
        "outcome_next_actions": {
            "protocol_frozen": {
                "gate_id": EXECUTION_GATE_ID,
                "action": (
                    "execute the frozen unchanged Adapter against the fixed "
                    "nine-case MM-002 suite exactly once with zero retries"
                ),
            },
            "completed_measurement": {
                "gate_id": RESULT_REVIEW_GATE_ID,
                "action": (
                    "review the layered raw compiled and metric replay evidence, "
                    "including either equality or drift, without inferring training "
                    "or cross-machine repeatability"
                ),
            },
            "incomplete_after_consumption": {
                "gate_id": FAILURE_CLASSIFICATION_GATE_ID,
                "action": (
                    "preserve the consumed attempt and require an explicit tracker "
                    "decision before changing any input or rerunning"
                ),
            },
        },
        "constraints": {
            "new_data": False,
            "training": False,
            "eval_answer_tuning": False,
            "prompt_change": False,
            "compiler_change": False,
            "generation_change": False,
            "base_or_tokenizer_substitution": False,
            "adapter_or_weight_mutation": False,
            "adapter_copy": False,
            "merged_weight_creation": False,
            "artifact_promotion": False,
            "serving_integration": False,
            "runtime_integration": False,
            "provider_integration": False,
            "mcp_integration": False,
            "desktop_integration": False,
        },
        "threat_model": {
            "local_source_bytecode_cache_disabled": True,
            "authenticated_source_receipts_required": True,
            "concurrent_source_mutation_resistance_established": False,
            "trusted_local_os_and_repository_owner_required": True,
        },
        "claims": negative_protocol_claims(),
        "next_gate_after_freeze": {
            "gate_id": EXECUTION_GATE_ID,
            "action": (
                "perform the single registered offline same-machine fixed-eval "
                "replay only after this protocol is merged"
            ),
        },
        "runtime_eligible": False,
    }


def validate_preregistration(
    raw: Mapping[str, Any],
    *,
    source_hashes: Mapping[str, str],
    upstream_preregistration: Mapping[str, Any],
    reference_evidence: Mapping[str, Any],
    reference_predictions: Mapping[str, Any],
    result_review: Mapping[str, Any],
    suite: Mapping[str, Any],
) -> dict[str, Any]:
    expected = expected_preregistration(
        freeze_status="frozen",
        source_hashes=source_hashes,
        upstream_preregistration=upstream_preregistration,
        reference_evidence=reference_evidence,
        reference_predictions=reference_predictions,
        result_review=result_review,
        suite=suite,
    )
    if not _json_exact(raw, expected):
        _fail("PREREGISTRATION_MISMATCH")
    return copy.deepcopy(expected)


def validate_reference_payloads(
    *,
    upstream_preregistration: Mapping[str, Any],
    reference_evidence: Mapping[str, Any],
    reference_predictions: Mapping[str, Any],
    result_review: Mapping[str, Any],
    suite: Mapping[str, Any],
) -> dict[str, str]:
    """Validate semantic bindings after the upstream result validator passes."""

    if (
        upstream_preregistration.get("freeze_status") != "frozen"
        or upstream_preregistration.get("experiment_id") != upstream.EXPERIMENT_ID
        or upstream_preregistration.get("model", {}).get("repo_id") != MODEL_ID
        or upstream_preregistration.get("model", {}).get("revision") != MODEL_REVISION
        or not _json_exact(
            upstream_preregistration.get("environment"), LOCKED_ENVIRONMENT
        )
    ):
        _fail("UPSTREAM_PREREGISTRATION_BINDING_MISMATCH")
    if (
        reference_evidence.get("formal_gate_passed") is not True
        or reference_evidence.get("classification")
        != "local_qlora_adapter_measurement_established"
        or not _json_exact(
            reference_evidence.get("evaluation", {}).get("predictions"),
            reference_predictions,
        )
    ):
        _fail("REFERENCE_EVIDENCE_BINDING_MISMATCH")
    if (
        result_review.get("gate_id")
        != "MM-003-small-vlm-post-training-result-review-v2"
        or result_review.get("next_gate") != PROTOCOL_GATE_ID
        or result_review.get("claims", {}).get("repeatability_established") is not False
        or result_review.get("runtime_eligible") is not False
    ):
        _fail("RESULT_REVIEW_BINDING_MISMATCH")
    taxonomy = _mapping(
        _mapping(result_review.get("evaluation"), "$.result_review.evaluation").get(
            "bad_case_taxonomy"
        ),
        "$.result_review.evaluation.bad_case_taxonomy",
    )
    if not _json_exact(
        taxonomy,
        {
            "exact_action_cases": ["ground-001", "ground-002", "ground-008"],
            "fused_grounding_missing_bbox": ["ground-003", "ground-006"],
            "reject_downgraded_to_fallback": [
                "ground-004",
                "ground-007",
                "ground-009",
            ],
            "fallback_reason_vocabulary_mismatch": ["ground-005"],
            "unclassified_cases": [],
            "compiler_fallback_cases": [],
            "failed_action_cases": 6,
            "taxonomy_is_review_only": True,
            "eval_answers_may_not_be_copied_into_training": True,
        },
    ):
        _fail("RESULT_REVIEW_TAXONOMY_MISMATCH")
    evaluation = _mapping(
        reference_evidence.get("evaluation"), "$.reference_evidence.evaluation"
    )
    screenshots = cast(
        Sequence[Mapping[str, Any]],
        _mapping(
            upstream_preregistration.get("source_lineage"),
            "$.upstream.source_lineage",
        )["unchanged_mm002_eval"]["screenshots"],
    )
    validate_completed_evaluation(
        evaluation, suite=suite, screenshot_receipts=screenshots, reference=True
    )
    cases = _sequence(evaluation.get("cases"), "$.reference_evaluation.cases")
    records = _sequence(
        reference_predictions.get("records"), "$.reference_predictions.records"
    )
    score = _mapping(evaluation.get("score"), "$.reference_evaluation.score")
    return {
        "raw_outputs_sha256": sha256_bytes(
            canonical_json_bytes(
                [
                    {"case_id": item["case_id"], "raw_output": item["raw_output"]}
                    for item in cases
                ]
            )
        ),
        "compiled_predictions_sha256": sha256_bytes(canonical_json_bytes(records)),
        "metrics_sha256": sha256_bytes(
            canonical_json_bytes(_mapping(score.get("metrics"), "$.score.metrics"))
        ),
    }


def validate_completed_evaluation(
    evaluation: Mapping[str, Any],
    *,
    suite: Mapping[str, Any],
    screenshot_receipts: Sequence[Mapping[str, Any]],
    reference: bool = False,
) -> dict[str, Any]:
    """Validate one complete nine-case evaluation and recompute its score."""

    if set(evaluation) != {"execution", "cases", "predictions", "score"}:
        _fail("EVALUATION_FIELD_SET_MISMATCH")
    execution = evaluation.get("execution")
    expected_execution = (
        _reference_execution() if reference else expected_replay_execution()
    )
    if not _json_exact(execution, expected_execution):
        _fail("EVALUATION_EXECUTION_MISMATCH")
    predictions = _mapping(evaluation.get("predictions"), "$.evaluation.predictions")
    if set(predictions) != {
        "gui_grounding_prediction_version",
        "suite_id",
        "producer",
        "records",
    }:
        _fail("PREDICTION_FIELD_SET_MISMATCH")
    _validate_prediction_identity(predictions)
    cases = _sequence(evaluation.get("cases"), "$.evaluation.cases")
    records = _sequence(predictions.get("records"), "$.predictions.records")
    if len(cases) != EXPECTED_CASES or len(records) != EXPECTED_CASES:
        _fail("EVALUATION_CASE_COUNT_MISMATCH")
    if [
        item.get("case_id") for item in _sequence(suite.get("cases"), "$.suite.cases")
    ] != list(CASE_ORDER):
        _fail("SUITE_CASE_ORDER_MISMATCH")
    suite_cases = {item["case_id"]: item for item in suite["cases"]}
    screenshot_hashes = {
        item["case_id"]: item["sha256"] for item in screenshot_receipts
    }
    for index, (case_result, prediction) in enumerate(zip(cases, records, strict=True)):
        case_id = CASE_ORDER[index]
        raw_output = case_result.get("raw_output")
        expected_screenshot = screenshot_hashes.get(case_id)
        if (
            set(case_result)
            != {
                "case_id",
                "observation_mode",
                "raw_output",
                "compiled_prediction",
                "compiler_fallback",
                "generated_tokens",
                "latency_seconds",
                "screenshot_sha256",
            }
            or case_result.get("case_id") != case_id
            or prediction.get("case_id") != case_id
            or case_result.get("observation_mode")
            != upstream.baseline.CASE_MODES[case_id]
            or not isinstance(raw_output, str)
            or not _json_exact(
                upstream.baseline.compile_raw_prediction(
                    raw_output, suite_cases[case_id]
                ),
                prediction,
            )
            or not _json_exact(case_result.get("compiled_prediction"), prediction)
            or not isinstance(case_result.get("compiler_fallback"), bool)
            or case_result.get("compiler_fallback")
            != (prediction.get("reason") == "model_output_invalid")
            or case_result.get("screenshot_sha256") != expected_screenshot
        ):
            _fail("EVALUATION_CASE_BINDING_MISMATCH")
        _positive_integer(
            case_result.get("generated_tokens"), "GENERATED_TOKENS_INVALID"
        )
        _positive_finite(case_result.get("latency_seconds"), "LATENCY_INVALID")
    recomputed = scorer.score_predictions(suite, predictions)
    if not _json_exact(evaluation.get("score"), recomputed):
        _fail("EVALUATION_SCORE_RECOMPUTATION_MISMATCH")
    if reference and any(item.get("compiler_fallback") for item in cases):
        _fail("REFERENCE_COMPILER_FALLBACK_MISMATCH")
    return copy.deepcopy(dict(evaluation))


def compare_completed_evaluations(
    *,
    reference: Mapping[str, Any],
    replay: Mapping[str, Any],
    suite: Mapping[str, Any],
    screenshot_receipts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    reference_valid = validate_completed_evaluation(
        reference,
        suite=suite,
        screenshot_receipts=screenshot_receipts,
        reference=True,
    )
    replay_valid = validate_completed_evaluation(
        replay, suite=suite, screenshot_receipts=screenshot_receipts
    )
    reference_cases = cast(list[dict[str, Any]], reference_valid["cases"])
    replay_cases = cast(list[dict[str, Any]], replay_valid["cases"])
    reference_records = cast(
        list[dict[str, Any]], reference_valid["predictions"]["records"]
    )
    replay_records = cast(list[dict[str, Any]], replay_valid["predictions"]["records"])
    raw_mismatches = [
        CASE_ORDER[index]
        for index, (left, right) in enumerate(
            zip(reference_cases, replay_cases, strict=True)
        )
        if left["raw_output"].encode("utf-8") != right["raw_output"].encode("utf-8")
    ]
    compiled_mismatches = [
        CASE_ORDER[index]
        for index, (left, right) in enumerate(
            zip(reference_records, replay_records, strict=True)
        )
        if canonical_json_bytes(left) != canonical_json_bytes(right)
    ]
    reference_metrics = reference_valid["score"]["metrics"]
    replay_metrics = replay_valid["score"]["metrics"]
    token_mismatches = [
        CASE_ORDER[index]
        for index, (left, right) in enumerate(
            zip(reference_cases, replay_cases, strict=True)
        )
        if left["generated_tokens"] != right["generated_tokens"]
    ]
    fallback_mismatches = [
        CASE_ORDER[index]
        for index, (left, right) in enumerate(
            zip(reference_cases, replay_cases, strict=True)
        )
        if left["compiler_fallback"] != right["compiler_fallback"]
    ]
    metric_names = list(reference_metrics)
    if list(replay_metrics) != metric_names:
        _fail("METRIC_SET_OR_ORDER_MISMATCH")
    per_metric = {
        name: {
            "reference": copy.deepcopy(reference_metrics[name]),
            "replay": copy.deepcopy(replay_metrics[name]),
            "exact": canonical_json_bytes(reference_metrics[name])
            == canonical_json_bytes(replay_metrics[name]),
        }
        for name in metric_names
    }
    metric_mismatches = [
        name for name in metric_names if per_metric[name]["exact"] is not True
    ]
    raw_exact = not raw_mismatches
    compiled_exact = not compiled_mismatches
    metrics_exact = not metric_mismatches
    return {
        "all_layers_exact": raw_exact and compiled_exact and metrics_exact,
        "raw_drift_compiled_and_metrics_exact": (
            not raw_exact and compiled_exact and metrics_exact
        ),
        "compiled_drift_metrics_exact": not compiled_exact and metrics_exact,
        "metric_drift": not metrics_exact,
        "case_order": list(CASE_ORDER),
        "raw_outputs": {
            "exact": EXPECTED_CASES - len(raw_mismatches),
            "total": EXPECTED_CASES,
            "mismatch_case_ids": raw_mismatches,
            "reference_sha256": _raw_digest(reference_cases),
            "replay_sha256": _raw_digest(replay_cases),
            "generated_tokens_exact": EXPECTED_CASES - len(token_mismatches),
            "token_counts_exact": not token_mismatches,
            "generated_token_mismatch_case_ids": token_mismatches,
        },
        "compiled_predictions": {
            "exact": EXPECTED_CASES - len(compiled_mismatches),
            "total": EXPECTED_CASES,
            "mismatch_case_ids": compiled_mismatches,
            "reference_sha256": sha256_bytes(canonical_json_bytes(reference_records)),
            "replay_sha256": sha256_bytes(canonical_json_bytes(replay_records)),
            "compiler_fallback_mismatch_case_ids": fallback_mismatches,
        },
        "metrics": {
            "exact": not metric_mismatches,
            "mismatch_metric_names": metric_mismatches,
            "per_metric": per_metric,
            "reference_sha256": sha256_bytes(canonical_json_bytes(reference_metrics)),
            "replay_sha256": sha256_bytes(canonical_json_bytes(replay_metrics)),
        },
    }


def build_attempt_owner(
    *,
    protocol_freeze_commit: str,
    preregistration_payload: bytes,
    owner_token: str,
) -> dict[str, Any]:
    _validate_commit(protocol_freeze_commit)
    if re.fullmatch(r"[0-9a-f]{64}", owner_token) is None:
        _fail("ATTEMPT_OWNER_TOKEN_INVALID")
    return {
        "attempt_owner_version": ATTEMPT_OWNER_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "run_id": RUN_ID,
        "output_id": OUTPUT_ID,
        "gate_id": EXECUTION_GATE_ID,
        "protocol": {
            "freeze_commit": protocol_freeze_commit,
            "preregistration_sha256": sha256_bytes(preregistration_payload),
        },
        "owner_token": owner_token,
    }


def validate_attempt_owner(
    payload: bytes,
    *,
    protocol_freeze_commit: str,
    preregistration_payload: bytes,
) -> dict[str, Any]:
    parsed = parse_strict_json_bytes(payload, location="$.attempt_owner")
    if not isinstance(parsed, Mapping) or artifact_json_bytes(parsed) != payload:
        _fail("ATTEMPT_OWNER_INVALID")
    token = parsed.get("owner_token")
    if not isinstance(token, str):
        _fail("ATTEMPT_OWNER_TOKEN_INVALID")
    expected = build_attempt_owner(
        protocol_freeze_commit=protocol_freeze_commit,
        preregistration_payload=preregistration_payload,
        owner_token=token,
    )
    if payload != artifact_json_bytes(expected):
        _fail("ATTEMPT_OWNER_BINDING_MISMATCH")
    return expected


def build_evaluation_candidate(
    *,
    protocol_freeze_commit: str,
    preregistration_payload: bytes,
    execution: Mapping[str, Any],
    cases: Sequence[Mapping[str, Any]],
    predictions: Mapping[str, Any],
    suite: Mapping[str, Any],
    screenshot_receipts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Build the exact pre-scoring replay artifact.

    The candidate deliberately excludes the score so a scoring failure still
    leaves authenticated model output, compiler output, and execution counters.
    """

    _validate_commit(protocol_freeze_commit)
    if not preregistration_payload:
        _fail("PREREGISTRATION_PAYLOAD_EMPTY")
    _validate_protocol_input_binding(
        preregistration_payload,
        suite=suite,
        screenshot_receipts=screenshot_receipts,
    )
    candidate = {
        "candidate_version": CANDIDATE_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "run_id": RUN_ID,
        "output_id": OUTPUT_ID,
        "gate_id": EXECUTION_GATE_ID,
        "protocol": {
            "freeze_commit": protocol_freeze_commit,
            "preregistration_sha256": sha256_bytes(preregistration_payload),
        },
        "execution": copy.deepcopy(dict(execution)),
        "cases": copy.deepcopy(list(cases)),
        "predictions": copy.deepcopy(dict(predictions)),
    }
    _validate_candidate_core(
        candidate,
        protocol_freeze_commit=protocol_freeze_commit,
        preregistration_payload=preregistration_payload,
        suite=suite,
        screenshot_receipts=screenshot_receipts,
    )
    return candidate


def validate_evaluation_candidate(
    payload: bytes,
    *,
    protocol_freeze_commit: str,
    preregistration_payload: bytes,
    replay_evaluation: Mapping[str, Any],
    suite: Mapping[str, Any],
    screenshot_receipts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Strictly parse and bind a candidate to the completed evaluation."""

    parsed = parse_strict_json_bytes(payload, location="$.evaluation_candidate")
    if not isinstance(parsed, Mapping):
        _fail("EVALUATION_CANDIDATE_NOT_OBJECT")
    if artifact_json_bytes(parsed) != payload:
        _fail("EVALUATION_CANDIDATE_NONCANONICAL")
    expected = build_evaluation_candidate(
        protocol_freeze_commit=protocol_freeze_commit,
        preregistration_payload=preregistration_payload,
        execution=_mapping(
            replay_evaluation.get("execution"), "$.evaluation.execution"
        ),
        cases=_sequence(replay_evaluation.get("cases"), "$.evaluation.cases"),
        predictions=_mapping(
            replay_evaluation.get("predictions"), "$.evaluation.predictions"
        ),
        suite=suite,
        screenshot_receipts=screenshot_receipts,
    )
    if payload != artifact_json_bytes(expected):
        _fail("EVALUATION_CANDIDATE_BINDING_MISMATCH")
    return copy.deepcopy(expected)


def build_evidence(
    *,
    preregistration_payload: bytes,
    attempt_owner_payload: bytes,
    evaluation_candidate_payload: bytes,
    predictions_payload: bytes,
    protocol_freeze_commit: str,
    reference_evaluation: Mapping[str, Any],
    replay_evaluation: Mapping[str, Any],
    preregistration: Mapping[str, Any],
    suite: Mapping[str, Any],
    screenshot_receipts: Sequence[Mapping[str, Any]],
    environment: Mapping[str, Any],
    model_files: Sequence[Mapping[str, Any]],
    adapter_receipts: Mapping[str, Mapping[str, Any]],
    resources: Mapping[str, Any],
    captured_at_utc: str,
) -> dict[str, Any]:
    comparison = compare_completed_evaluations(
        reference=reference_evaluation,
        replay=replay_evaluation,
        suite=suite,
        screenshot_receipts=screenshot_receipts,
    )
    _validate_resources(resources)
    _validate_captured_at_utc(captured_at_utc)
    validate_attempt_owner(
        attempt_owner_payload,
        protocol_freeze_commit=protocol_freeze_commit,
        preregistration_payload=preregistration_payload,
    )
    validate_evaluation_candidate(
        evaluation_candidate_payload,
        protocol_freeze_commit=protocol_freeze_commit,
        preregistration_payload=preregistration_payload,
        replay_evaluation=replay_evaluation,
        suite=suite,
        screenshot_receipts=screenshot_receipts,
    )
    expected_predictions_payload = artifact_json_bytes(
        _mapping(replay_evaluation.get("predictions"), "$.evaluation.predictions")
    )
    if predictions_payload != expected_predictions_payload:
        _fail("PREDICTIONS_ARTIFACT_BINDING_MISMATCH")
    comparison_protocol = _mapping(
        preregistration.get("comparison_protocol"), "$.comparison_protocol"
    )
    lineage = _mapping(preregistration.get("source_lineage"), "$.source_lineage")
    suite_receipt = _mapping(
        lineage.get("unchanged_mm002_eval"), "$.source_lineage.unchanged_mm002_eval"
    )
    reference_integrity = (
        comparison["raw_outputs"]["reference_sha256"]
        == comparison_protocol["reference_raw_outputs_sha256"]
        and comparison["compiled_predictions"]["reference_sha256"]
        == comparison_protocol["reference_compiled_predictions_sha256"]
        and comparison["metrics"]["reference_sha256"]
        == comparison_protocol["reference_metrics_sha256"]
    )
    gates: dict[str, bool] = {
        "protocol_integrity": (
            contract_payload_is_exact(preregistration, preregistration_payload)
            and preregistration.get("freeze_status") == "frozen"
            and preregistration.get("gate_id") == PROTOCOL_GATE_ID
            and bool(re.fullmatch(r"[0-9a-f]{40}", protocol_freeze_commit))
        ),
        "reference_result_integrity": reference_integrity,
        "exact_model_files": _json_exact(
            list(model_files),
            cast(Mapping[str, Any], preregistration["model"])["files"],
        ),
        "exact_adapter_files": _json_exact(dict(adapter_receipts), ADAPTER_RECEIPTS),
        "locked_environment": _json_exact(dict(environment), LOCKED_ENVIRONMENT),
        "unchanged_mm002_inputs": (
            [item["case_id"] for item in suite["cases"]] == list(CASE_ORDER)
            and base_scorer.sha256_json(dict(suite))
            == suite_receipt["canonical_sha256"]
            and _json_exact(list(screenshot_receipts), suite_receipt["screenshots"])
        ),
        "offline_single_replay": _json_exact(
            replay_evaluation["execution"], expected_replay_execution()
        ),
        "prediction_identity": _json_exact(
            replay_evaluation["predictions"].get("producer"),
            _expected_producer(),
        ),
        "attempt_ownership": (
            artifact_json_bytes(
                validate_attempt_owner(
                    attempt_owner_payload,
                    protocol_freeze_commit=protocol_freeze_commit,
                    preregistration_payload=preregistration_payload,
                )
            )
            == attempt_owner_payload
        ),
        "candidate_and_predictions_binding": (
            artifact_json_bytes(
                validate_evaluation_candidate(
                    evaluation_candidate_payload,
                    protocol_freeze_commit=protocol_freeze_commit,
                    preregistration_payload=preregistration_payload,
                    replay_evaluation=replay_evaluation,
                    suite=suite,
                    screenshot_receipts=screenshot_receipts,
                )
            )
            == evaluation_candidate_payload
            and expected_predictions_payload == predictions_payload
        ),
        "layered_comparison_complete": (
            comparison["raw_outputs"]["total"] == EXPECTED_CASES
            and comparison["compiled_predictions"]["total"] == EXPECTED_CASES
            and isinstance(comparison["metrics"]["exact"], bool)
        ),
        "resource_caps": (
            resources["elapsed_seconds"] <= RESOURCE_CAPS["elapsed_seconds"]
            and resources["peak_gpu_allocated_bytes"]
            <= RESOURCE_CAPS["peak_gpu_allocated_bytes"]
            and resources["peak_gpu_reserved_bytes"]
            <= RESOURCE_CAPS["peak_gpu_reserved_bytes"]
        ),
    }
    pre_claim_gate_passed = all(gates.values())
    claim_probe = execution_claims(formal_gate_passed=pre_claim_gate_passed)
    gates["fail_closed_claims"] = _claims_are_fail_closed(
        claim_probe, formal_gate_passed=pre_claim_gate_passed
    )
    if list(gates) != REQUIRED_GATES:
        _fail("FORMAL_GATE_SET_OR_ORDER_MISMATCH")
    formal_gate_passed = all(gates.values())
    claims = _frozen_execution_claims(formal_gate_passed=formal_gate_passed)
    integrity_gates = [name for name in REQUIRED_GATES if name != "resource_caps"]
    if not all(gates[name] for name in integrity_gates):
        classification = INTEGRITY_FAILURE_CLASSIFICATION
    elif not gates["resource_caps"]:
        classification = RESOURCE_EXCEEDED_CLASSIFICATION
    else:
        classification = MEASUREMENT_CLASSIFICATION
    return {
        "evidence_version": EVIDENCE_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "run_id": RUN_ID,
        "output_id": OUTPUT_ID,
        "gate_id": EXECUTION_GATE_ID,
        "captured_at_utc": captured_at_utc,
        "protocol": {
            "freeze_commit": protocol_freeze_commit,
            "preregistration_sha256": sha256_bytes(preregistration_payload),
        },
        "artifacts": {
            "attempt_owner": artifact_receipt(
                ATTEMPT_OWNER_ARTIFACT, attempt_owner_payload
            ),
            "evaluation_candidate": artifact_receipt(
                EVALUATION_CANDIDATE_ARTIFACT, evaluation_candidate_payload
            ),
            "predictions": artifact_receipt(PREDICTIONS_ARTIFACT, predictions_payload),
        },
        "reference": {
            "predictions": copy.deepcopy(REFERENCE_PREDICTIONS_RECEIPT),
            "training_run": copy.deepcopy(REFERENCE_TRAINING_RUN_RECEIPT),
            "evidence": copy.deepcopy(REFERENCE_EVIDENCE_RECEIPT),
            "result_review": copy.deepcopy(RESULT_REVIEW_RECEIPT),
        },
        "execution": copy.deepcopy(replay_evaluation["execution"]),
        "comparison": comparison,
        "evaluation": {
            "cases": copy.deepcopy(replay_evaluation["cases"]),
            "predictions": copy.deepcopy(replay_evaluation["predictions"]),
            "score": copy.deepcopy(replay_evaluation["score"]),
        },
        "resources": copy.deepcopy(dict(resources)),
        "gates": gates,
        "formal_gate_passed": formal_gate_passed,
        "classification": classification,
        "claims": claims,
        "limitations": [
            "single_same_machine_environment_replay_only",
            "training_repeatability_unestablished",
            "cross_machine_reproducibility_unestablished",
            "resource_repeatability_unestablished",
            "generalized_quality_unestablished",
            "serving_promotion_and_runtime_eligibility_unestablished",
        ],
        "next_gate": (
            RESULT_REVIEW_GATE_ID
            if formal_gate_passed
            else FAILURE_CLASSIFICATION_GATE_ID
        ),
        "runtime_eligible": False,
    }


def build_failure(
    *,
    protocol_freeze_commit: str,
    preregistration_payload: bytes,
    attempt_owner_payload: bytes,
    stage: str,
    exception_type: str,
    exception_code: str | None,
    exception_location: str | None,
    counters: Mapping[str, Any],
    completed_case_ids: Sequence[str],
    suite: Mapping[str, Any],
    screenshot_receipts: Sequence[Mapping[str, Any]],
    evaluation_candidate_payload: bytes | None,
    predictions_payload: bytes | None,
) -> dict[str, Any]:
    """Build the closed receipt for a consumed but incomplete replay."""

    _validate_commit(protocol_freeze_commit)
    if not preregistration_payload:
        _fail("PREREGISTRATION_PAYLOAD_EMPTY")
    _validate_protocol_input_binding(
        preregistration_payload,
        suite=suite,
        screenshot_receipts=screenshot_receipts,
    )
    validate_attempt_owner(
        attempt_owner_payload,
        protocol_freeze_commit=protocol_freeze_commit,
        preregistration_payload=preregistration_payload,
    )
    if stage not in FAILURE_STAGES:
        _fail("FAILURE_STAGE_INVALID")
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,95}", exception_type) is None:
        _fail("FAILURE_EXCEPTION_TYPE_INVALID")
    if (
        exception_code is not None
        and re.fullmatch(r"[A-Z][A-Z0-9_]{0,95}", exception_code) is None
    ):
        _fail("FAILURE_EXCEPTION_CODE_INVALID")
    if exception_location is not None:
        if (
            len(exception_location) > 256
            or re.fullmatch(
                r"\$(?:\.[A-Za-z_][A-Za-z0-9_]*|\[[0-9]+\])*",
                exception_location,
            )
            is None
        ):
            _fail("FAILURE_EXCEPTION_LOCATION_INVALID")
    if exception_code is None and exception_location is not None:
        _fail("FAILURE_EXCEPTION_DIAGNOSTIC_INCONSISTENT")
    validated_counters = _validate_partial_counters(counters, stage=stage)
    validated_case_ids = _validate_completed_case_ids(
        completed_case_ids, validated_counters
    )
    candidate_receipt: dict[str, Any] | None = None
    predictions_receipt: dict[str, Any] | None = None
    candidate: Mapping[str, Any] | None = None
    if evaluation_candidate_payload is not None:
        candidate = _validate_failure_candidate(
            evaluation_candidate_payload,
            protocol_freeze_commit=protocol_freeze_commit,
            preregistration_payload=preregistration_payload,
            suite=suite,
            screenshot_receipts=screenshot_receipts,
        )
        candidate_expected_counters = dict(validated_counters)
        candidate_expected_counters["network_attempts"] = 0
        if not _json_exact(candidate["execution"], candidate_expected_counters):
            _fail("FAILURE_CANDIDATE_COUNTER_MISMATCH")
        candidate_receipt = artifact_receipt(
            EVALUATION_CANDIDATE_ARTIFACT, evaluation_candidate_payload
        )
    if predictions_payload is not None:
        if candidate is None:
            _fail("FAILURE_PREDICTIONS_WITHOUT_CANDIDATE")
        parsed_predictions = parse_strict_json_bytes(
            predictions_payload, location="$.failure.predictions"
        )
        if (
            not isinstance(parsed_predictions, Mapping)
            or artifact_json_bytes(parsed_predictions) != predictions_payload
            or not _json_exact(parsed_predictions, candidate["predictions"])
        ):
            _fail("FAILURE_PREDICTIONS_BINDING_MISMATCH")
        predictions_receipt = artifact_receipt(
            PREDICTIONS_ARTIFACT, predictions_payload
        )
    candidate_required = stage in {
        "total_scoring",
        "predictions",
        "adapter_postcondition",
        "evidence",
    }
    predictions_required = stage in {"adapter_postcondition", "evidence"}
    artifacts_forbidden = stage in {
        "output_reservation",
        "dependency_import",
        "locked_environment",
        "independent_adapter_load_and_eval",
    }
    if candidate_required and candidate_receipt is None:
        _fail("FAILURE_CANDIDATE_RECEIPT_REQUIRED")
    if predictions_required and predictions_receipt is None:
        _fail("FAILURE_PREDICTIONS_RECEIPT_REQUIRED")
    if artifacts_forbidden and (
        candidate_receipt is not None or predictions_receipt is not None
    ):
        _fail("FAILURE_ARTIFACT_RECEIPT_FORBIDDEN")
    return {
        "failure_version": FAILURE_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "run_id": RUN_ID,
        "output_id": OUTPUT_ID,
        "gate_id": EXECUTION_GATE_ID,
        "classification": INCOMPLETE_CLASSIFICATION,
        "protocol_freeze_commit": protocol_freeze_commit,
        "preregistration_sha256": sha256_bytes(preregistration_payload),
        "stage": stage,
        "exception_type": exception_type,
        "exception_code": exception_code,
        "exception_location": exception_location,
        "attempt_consumed": True,
        "counters": validated_counters,
        "completed_case_ids": validated_case_ids,
        "artifacts": {
            "attempt_owner": artifact_receipt(
                ATTEMPT_OWNER_ARTIFACT, attempt_owner_payload
            ),
            "evaluation_candidate": candidate_receipt,
            "predictions": predictions_receipt,
        },
        "retry_count": 0,
        "formal_gate_passed": False,
        "claims": negative_protocol_claims(),
        "next_gate": FAILURE_CLASSIFICATION_GATE_ID,
        "runtime_eligible": False,
    }


def validate_failure(
    payload: bytes,
    *,
    protocol_freeze_commit: str,
    preregistration_payload: bytes,
    attempt_owner_payload: bytes,
    suite: Mapping[str, Any],
    screenshot_receipts: Sequence[Mapping[str, Any]],
    evaluation_candidate_payload: bytes | None,
    predictions_payload: bytes | None,
) -> dict[str, Any]:
    """Rebuild an exact consumed-failure receipt from its closed fields."""

    parsed = parse_strict_json_bytes(payload, location="$.failure")
    if not isinstance(parsed, Mapping):
        _fail("FAILURE_NOT_OBJECT")
    if artifact_json_bytes(parsed) != payload:
        _fail("FAILURE_NONCANONICAL")
    stage = parsed.get("stage")
    exception_type = parsed.get("exception_type")
    exception_code = parsed.get("exception_code")
    exception_location = parsed.get("exception_location")
    if not isinstance(stage, str) or not isinstance(exception_type, str):
        _fail("FAILURE_DIAGNOSTIC_TYPE_INVALID")
    if exception_code is not None and not isinstance(exception_code, str):
        _fail("FAILURE_DIAGNOSTIC_TYPE_INVALID")
    if exception_location is not None and not isinstance(exception_location, str):
        _fail("FAILURE_DIAGNOSTIC_TYPE_INVALID")
    expected = build_failure(
        protocol_freeze_commit=protocol_freeze_commit,
        preregistration_payload=preregistration_payload,
        attempt_owner_payload=attempt_owner_payload,
        stage=stage,
        exception_type=exception_type,
        exception_code=exception_code,
        exception_location=exception_location,
        counters=_mapping(parsed.get("counters"), "$.failure.counters"),
        completed_case_ids=[
            str(value)
            for value in _sequence_of_strings(
                parsed.get("completed_case_ids"), "$.failure.completed_case_ids"
            )
        ],
        suite=suite,
        screenshot_receipts=screenshot_receipts,
        evaluation_candidate_payload=evaluation_candidate_payload,
        predictions_payload=predictions_payload,
    )
    if payload != artifact_json_bytes(expected):
        _fail("FAILURE_RECEIPT_MISMATCH")
    return copy.deepcopy(expected)


def artifact_receipt(path: str, payload: bytes) -> dict[str, Any]:
    if not isinstance(path, str) or not path or not isinstance(payload, bytes):
        _fail("ARTIFACT_RECEIPT_INPUT_INVALID")
    return {"path": path, "bytes": len(payload), "sha256": sha256_bytes(payload)}


def negative_protocol_claims() -> dict[str, bool]:
    return {name: False for name in CLAIM_KEYS}


def execution_claims(*, formal_gate_passed: bool) -> dict[str, bool]:
    if type(formal_gate_passed) is not bool:
        _fail("FORMAL_GATE_BOOLEAN_INVALID")
    claims = negative_protocol_claims()
    claims["replay_executed"] = True
    claims["model_evaluated"] = True
    claims["formal_measurement_complete"] = formal_gate_passed
    # Equality or drift is interpreted only by the separately frozen result review.
    claims["same_machine_eval_repeatability_established"] = False
    return claims


def _frozen_execution_claims(*, formal_gate_passed: bool) -> dict[str, bool]:
    allowed_true = {"replay_executed", "model_evaluated"}
    if formal_gate_passed:
        allowed_true.add("formal_measurement_complete")
    return {name: name in allowed_true for name in CLAIM_KEYS}


def _claims_are_fail_closed(
    claims: Mapping[str, Any], *, formal_gate_passed: bool
) -> bool:
    if tuple(claims) != CLAIM_KEYS or any(
        type(value) is not bool for value in claims.values()
    ):
        return False
    expected_true = {"replay_executed", "model_evaluated"}
    if formal_gate_passed:
        expected_true.add("formal_measurement_complete")
    return {name for name, value in claims.items() if value} == expected_true


def expected_replay_execution() -> dict[str, int | bool]:
    return {
        "fresh_base_load_attempts": 1,
        "fresh_base_loads": 1,
        "independent_adapter_load_attempts": 1,
        "independent_adapter_loads": 1,
        "full_eval_run_attempts": 1,
        "full_eval_runs": 1,
        "generate_attempts": EXPECTED_CASES,
        "generate_calls": EXPECTED_CASES,
        "training_runs": 0,
        "optimizer_steps": 0,
        "backward_calls": 0,
        "adapter_writes": 0,
        "network_attempts": 0,
        "network_used": False,
        "retry_count": 0,
    }


def _reference_execution() -> dict[str, int | bool]:
    return {
        "fresh_base_loads": 1,
        "full_eval_runs": 1,
        "generate_calls": EXPECTED_CASES,
        "independent_adapter_loads": 1,
        "network_used": False,
        "retry_count": 0,
    }


def _validate_source_hashes(source_hashes: Mapping[str, str]) -> None:
    if set(source_hashes) != set(PROTOCOL_SOURCE_PATHS):
        _fail("PROTOCOL_SOURCE_SET_MISMATCH")
    for name, digest in source_hashes.items():
        if (
            not isinstance(name, str)
            or not isinstance(digest, str)
            or not _SHA256.fullmatch(digest)
        ):
            _fail("PROTOCOL_SOURCE_HASH_INVALID")


def contract_payload_is_exact(
    preregistration: Mapping[str, Any], payload: bytes
) -> bool:
    return artifact_json_bytes(preregistration) == payload


def _json_exact(left: object, right: object) -> bool:
    """Compare JSON values without Python's bool/int or int/float coercion."""

    try:
        return canonical_json_bytes(left) == canonical_json_bytes(right)
    except (TypeError, ValueError):
        return False


def _validate_prediction_identity(predictions: Mapping[str, Any]) -> None:
    if (
        type(predictions.get("gui_grounding_prediction_version")) is not int
        or predictions.get("gui_grounding_prediction_version") != 1
        or predictions.get("suite_id") != "mm002-synthetic-eval-v1"
        or not _json_exact(predictions.get("producer"), _expected_producer())
    ):
        _fail("PREDICTION_IDENTITY_MISMATCH")


def _expected_producer() -> dict[str, str]:
    return {
        "kind": "model",
        "model_id": ADAPTER_MODEL_ID,
        "model_revision": MODEL_REVISION,
    }


def _raw_digest(cases: Sequence[Mapping[str, Any]]) -> str:
    return sha256_bytes(
        canonical_json_bytes(
            [
                {"case_id": item["case_id"], "raw_output": item["raw_output"]}
                for item in cases
            ]
        )
    )


def _validate_resources(resources: Mapping[str, Any]) -> None:
    if set(resources) != {
        "elapsed_seconds",
        "peak_gpu_allocated_bytes",
        "peak_gpu_reserved_bytes",
    }:
        _fail("RESOURCE_FIELD_MISMATCH")
    _positive_finite(resources.get("elapsed_seconds"), "ELAPSED_SECONDS_INVALID")
    for name in ("peak_gpu_allocated_bytes", "peak_gpu_reserved_bytes"):
        value = resources.get(name)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            _fail("RESOURCE_VALUE_INVALID")


def _validate_captured_at_utc(value: object) -> None:
    if not isinstance(value, str) or len(value) > 40:
        _fail("CAPTURED_AT_UTC_INVALID")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        _fail("CAPTURED_AT_UTC_INVALID")
    if (
        parsed.tzinfo is None
        or parsed.utcoffset() != timezone.utc.utcoffset(parsed)
        or parsed.isoformat() != value
        or not value.endswith("+00:00")
    ):
        _fail("CAPTURED_AT_UTC_INVALID")


def _validate_protocol_input_binding(
    preregistration_payload: bytes,
    *,
    suite: Mapping[str, Any],
    screenshot_receipts: Sequence[Mapping[str, Any]],
) -> Mapping[str, Any]:
    parsed = parse_strict_json_bytes(
        preregistration_payload, location="$.failure.preregistration"
    )
    if (
        not isinstance(parsed, Mapping)
        or artifact_json_bytes(parsed) != preregistration_payload
        or type(parsed.get("preregistration_version")) is not int
        or parsed.get("preregistration_version") != PREREGISTRATION_VERSION
        or parsed.get("experiment_id") != EXPERIMENT_ID
        or parsed.get("run_id") != RUN_ID
        or parsed.get("output_id") != OUTPUT_ID
        or parsed.get("gate_id") != PROTOCOL_GATE_ID
        or parsed.get("freeze_status") != "frozen"
    ):
        _fail("PREREGISTRATION_INPUT_BINDING_MISMATCH")
    lineage = _mapping(parsed.get("source_lineage"), "$.preregistration.source_lineage")
    suite_receipt = _mapping(
        lineage.get("unchanged_mm002_eval"),
        "$.preregistration.source_lineage.unchanged_mm002_eval",
    )
    cases = _sequence(suite.get("cases"), "$.candidate.suite.cases")
    if (
        [item.get("case_id") for item in cases] != list(CASE_ORDER)
        or base_scorer.sha256_json(dict(suite)) != suite_receipt.get("canonical_sha256")
        or not _json_exact(list(screenshot_receipts), suite_receipt.get("screenshots"))
    ):
        _fail("PREREGISTRATION_MM002_INPUT_BINDING_MISMATCH")
    return parsed


def _validate_failure_candidate(
    payload: bytes,
    *,
    protocol_freeze_commit: str,
    preregistration_payload: bytes,
    suite: Mapping[str, Any],
    screenshot_receipts: Sequence[Mapping[str, Any]],
) -> Mapping[str, Any]:
    parsed = parse_strict_json_bytes(payload, location="$.failure.candidate")
    if not isinstance(parsed, Mapping) or artifact_json_bytes(parsed) != payload:
        _fail("FAILURE_CANDIDATE_INVALID")
    _validate_candidate_core(
        parsed,
        protocol_freeze_commit=protocol_freeze_commit,
        preregistration_payload=preregistration_payload,
        suite=suite,
        screenshot_receipts=screenshot_receipts,
    )
    return parsed


def _validate_candidate_core(
    parsed: Mapping[str, Any],
    *,
    protocol_freeze_commit: str,
    preregistration_payload: bytes,
    suite: Mapping[str, Any] | None = None,
    screenshot_receipts: Sequence[Mapping[str, Any]] | None = None,
) -> None:
    if set(parsed) != {
        "candidate_version",
        "experiment_id",
        "run_id",
        "output_id",
        "gate_id",
        "protocol",
        "execution",
        "cases",
        "predictions",
    }:
        _fail("FAILURE_CANDIDATE_FIELD_SET_MISMATCH")
    if (
        type(parsed.get("candidate_version")) is not int
        or parsed.get("candidate_version") != CANDIDATE_VERSION
        or parsed.get("experiment_id") != EXPERIMENT_ID
        or parsed.get("run_id") != RUN_ID
        or parsed.get("output_id") != OUTPUT_ID
        or parsed.get("gate_id") != EXECUTION_GATE_ID
        or not _json_exact(
            parsed.get("protocol"),
            {
                "freeze_commit": protocol_freeze_commit,
                "preregistration_sha256": sha256_bytes(preregistration_payload),
            },
        )
        or not _json_exact(parsed.get("execution"), expected_replay_execution())
    ):
        _fail("FAILURE_CANDIDATE_BINDING_MISMATCH")
    cases = _sequence(parsed.get("cases"), "$.failure.candidate.cases")
    predictions = _mapping(parsed.get("predictions"), "$.failure.candidate.predictions")
    if set(predictions) != {
        "gui_grounding_prediction_version",
        "suite_id",
        "producer",
        "records",
    }:
        _fail("FAILURE_CANDIDATE_PREDICTION_FIELD_SET_MISMATCH")
    _validate_prediction_identity(predictions)
    records = _sequence(
        predictions.get("records"), "$.failure.candidate.predictions.records"
    )
    if (suite is None) != (screenshot_receipts is None):
        _fail("FAILURE_CANDIDATE_CONTEXT_INCOMPLETE")
    suite_cases: dict[str, Mapping[str, Any]] | None = None
    screenshot_hashes: dict[str, Any] | None = None
    if suite is not None and screenshot_receipts is not None:
        ordered_suite_cases = _sequence(
            suite.get("cases"), "$.failure.candidate.suite.cases"
        )
        if [item.get("case_id") for item in ordered_suite_cases] != list(CASE_ORDER):
            _fail("FAILURE_CANDIDATE_SUITE_ORDER_MISMATCH")
        suite_cases = {str(item["case_id"]): item for item in ordered_suite_cases}
        screenshot_hashes = {
            str(item.get("case_id")): item.get("sha256") for item in screenshot_receipts
        }
    if len(cases) != EXPECTED_CASES or len(records) != EXPECTED_CASES:
        _fail("FAILURE_CANDIDATE_CASE_COUNT_MISMATCH")
    for index, (case, record) in enumerate(zip(cases, records, strict=True)):
        case_id = CASE_ORDER[index]
        if set(case) != {
            "case_id",
            "observation_mode",
            "raw_output",
            "compiled_prediction",
            "compiler_fallback",
            "generated_tokens",
            "latency_seconds",
            "screenshot_sha256",
        } or set(record) != {
            "case_id",
            "disposition",
            "tool",
            "arguments",
            "ref",
            "bbox",
            "reason",
        }:
            _fail("FAILURE_CANDIDATE_CASE_FIELD_SET_MISMATCH")
        screenshot_sha256 = case.get("screenshot_sha256")
        expected_no_screenshot = upstream.baseline.CASE_MODES[case_id] == "uia_only"
        if (
            case.get("case_id") != case_id
            or record.get("case_id") != case_id
            or case.get("observation_mode") != upstream.baseline.CASE_MODES[case_id]
            or not isinstance(case.get("raw_output"), str)
            or not _json_exact(case.get("compiled_prediction"), record)
            or type(case.get("compiler_fallback")) is not bool
            or case.get("compiler_fallback")
            != (record.get("reason") == "model_output_invalid")
            or (
                screenshot_sha256 is not None
                and (
                    not isinstance(screenshot_sha256, str)
                    or _SHA256.fullmatch(screenshot_sha256) is None
                )
            )
            or expected_no_screenshot != (screenshot_sha256 is None)
        ):
            _fail("FAILURE_CANDIDATE_CASE_BINDING_MISMATCH")
        if suite_cases is not None and screenshot_hashes is not None:
            if not _json_exact(
                upstream.baseline.compile_raw_prediction(
                    cast(str, case.get("raw_output")), suite_cases[case_id]
                ),
                record,
            ) or screenshot_sha256 != screenshot_hashes.get(case_id):
                _fail("FAILURE_CANDIDATE_AUTHENTICATED_INPUT_MISMATCH")
        _positive_integer(
            case.get("generated_tokens"), "FAILURE_CANDIDATE_TOKEN_COUNT_INVALID"
        )
        _positive_finite(
            case.get("latency_seconds"), "FAILURE_CANDIDATE_LATENCY_INVALID"
        )
    if [item.get("case_id") for item in cases] != list(CASE_ORDER) or [
        item.get("case_id") for item in records
    ] != list(CASE_ORDER):
        _fail("FAILURE_CANDIDATE_CASE_ORDER_MISMATCH")


def _validate_partial_counters(
    counters: Mapping[str, Any],
    *,
    stage: str,
) -> dict[str, int | bool]:
    expected_keys = set(expected_replay_execution())
    if set(counters) != expected_keys:
        _fail("FAILURE_COUNTER_FIELD_SET_MISMATCH")
    result: dict[str, int | bool] = {}
    for name in expected_replay_execution():
        value = counters.get(name)
        if name == "network_used":
            if value is not False:
                _fail("FAILURE_NETWORK_USED_INVALID")
            result[name] = False
        else:
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                _fail("FAILURE_COUNTER_VALUE_INVALID")
            result[name] = value
    for name in (
        "fresh_base_load_attempts",
        "fresh_base_loads",
        "independent_adapter_load_attempts",
        "independent_adapter_loads",
        "full_eval_run_attempts",
        "full_eval_runs",
    ):
        if cast(int, result[name]) > 1:
            _fail("FAILURE_SINGLE_ATTEMPT_COUNTER_EXCEEDED")
    for name in ("generate_attempts", "generate_calls"):
        if cast(int, result[name]) > EXPECTED_CASES:
            _fail("FAILURE_GENERATE_COUNTER_EXCEEDED")
    for completed_name, attempted_name in (
        ("fresh_base_loads", "fresh_base_load_attempts"),
        ("independent_adapter_loads", "independent_adapter_load_attempts"),
        ("full_eval_runs", "full_eval_run_attempts"),
        ("generate_calls", "generate_attempts"),
    ):
        if cast(int, result[completed_name]) > cast(int, result[attempted_name]):
            _fail("FAILURE_COUNTER_CAUSALITY_INVALID")
    if (
        cast(int, result["independent_adapter_load_attempts"])
        > cast(int, result["fresh_base_loads"])
        or cast(int, result["full_eval_run_attempts"])
        > cast(int, result["independent_adapter_loads"])
        or (
            cast(int, result["generate_attempts"]) > 0
            and result["full_eval_run_attempts"] != 1
        )
        or (
            result["full_eval_runs"] == 1
            and (
                result["generate_attempts"] != EXPECTED_CASES
                or result["generate_calls"] != EXPECTED_CASES
            )
        )
        or cast(int, result["network_attempts"]) > 1_000_000
    ):
        _fail("FAILURE_CROSS_STAGE_COUNTER_CAUSALITY_INVALID")
    for name in (
        "training_runs",
        "optimizer_steps",
        "backward_calls",
        "adapter_writes",
        "retry_count",
    ):
        if result[name] != 0:
            _fail("FAILURE_FORBIDDEN_COUNTER_NONZERO")
    no_model_counter_names = (
        "fresh_base_load_attempts",
        "fresh_base_loads",
        "independent_adapter_load_attempts",
        "independent_adapter_loads",
        "full_eval_run_attempts",
        "full_eval_runs",
        "generate_attempts",
        "generate_calls",
    )
    if stage in {"output_reservation", "dependency_import", "locked_environment"}:
        if any(result[name] != 0 for name in no_model_counter_names):
            _fail("FAILURE_STAGE_COUNTER_ENVELOPE_INVALID")
        if stage == "output_reservation" and result["network_attempts"] != 0:
            _fail("FAILURE_STAGE_COUNTER_ENVELOPE_INVALID")
    if stage in {
        "evaluation_candidate",
        "total_scoring",
        "predictions",
        "adapter_postcondition",
        "evidence",
    }:
        completed_expected = expected_replay_execution()
        completed_expected["network_attempts"] = cast(int, result["network_attempts"])
        if not _json_exact(result, completed_expected):
            _fail("FAILURE_COMPLETED_COUNTER_ENVELOPE_INVALID")
    return result


def _validate_completed_case_ids(
    values: Sequence[str], counters: Mapping[str, int | bool]
) -> list[str]:
    if any(not isinstance(value, str) for value in values):
        _fail("FAILURE_COMPLETED_CASE_ID_INVALID")
    result = list(values)
    if result != list(CASE_ORDER[: len(result)]):
        _fail("FAILURE_COMPLETED_CASE_ORDER_INVALID")
    if len(result) > cast(int, counters["generate_calls"]):
        _fail("FAILURE_COMPLETED_CASE_COUNT_INVALID")
    if (
        cast(int, counters["generate_attempts"]) - cast(int, counters["generate_calls"])
        > 1
        or cast(int, counters["generate_calls"]) - len(result) > 1
    ):
        _fail("FAILURE_GENERATE_PROGRESS_INVALID")
    if counters["full_eval_runs"] == 1 and result != list(CASE_ORDER):
        _fail("FAILURE_COMPLETED_CASE_COUNT_INVALID")
    return result


def _sequence_of_strings(value: object, location: str) -> Sequence[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        _fail(f"EXPECTED_STRING_ARRAY_AT_{location}")
    if any(not isinstance(item, str) for item in value):
        _fail(f"EXPECTED_STRING_ITEMS_AT_{location}")
    return cast(Sequence[str], value)


def _validate_commit(value: object) -> None:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{40}", value) is None:
        _fail("PROTOCOL_FREEZE_COMMIT_INVALID")


def _mapping(value: object, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail(f"EXPECTED_OBJECT_AT_{location}")
    return value


def _sequence(value: object, location: str) -> Sequence[Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        _fail(f"EXPECTED_ARRAY_AT_{location}")
    for item in value:
        if not isinstance(item, Mapping):
            _fail(f"EXPECTED_OBJECT_ITEMS_AT_{location}")
    return cast(Sequence[Mapping[str, Any]], value)


def _positive_integer(value: object, code: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        _fail(code)


def _positive_finite(value: object, code: str) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        _fail(code)
    numeric = float(value)
    if numeric <= 0 or numeric != numeric or numeric in {float("inf"), float("-inf")}:
        _fail(code)


def _fail(code: str) -> NoReturn:
    raise MM003EvalRepeatabilityError(code)


__all__ = [
    "ADAPTER_MODEL_ID",
    "ADAPTER_RECEIPTS",
    "ADAPTER_ROOT",
    "ATTEMPT_OWNER_ARTIFACT",
    "CASE_ORDER",
    "EVIDENCE_ARTIFACT",
    "EVALUATION_CANDIDATE_ARTIFACT",
    "EXPECTED_CASES",
    "EXECUTION_GATE_ID",
    "EXPERIMENT_ID",
    "FAILURE_ARTIFACT",
    "FAILURE_CLASSIFICATION_GATE_ID",
    "FAILURE_STAGES",
    "FORMAL_PYTHON_ARGS",
    "FORMAL_PYTHON_PATH",
    "LOCKED_ENVIRONMENT",
    "MM003EvalRepeatabilityError",
    "INTEGRITY_FAILURE_CLASSIFICATION",
    "MEASUREMENT_CLASSIFICATION",
    "MODEL_ID",
    "MODEL_REVISION",
    "MODEL_SNAPSHOT_ROOT",
    "OUTPUT_ID",
    "PREDICTIONS_ARTIFACT",
    "PREREGISTRATION_PATH",
    "PROTOCOL_GATE_ID",
    "PROTOCOL_SOURCE_PATHS",
    "REFERENCE_EVIDENCE_RECEIPT",
    "REFERENCE_PREDICTIONS_RECEIPT",
    "REFERENCE_TRAINING_RUN_RECEIPT",
    "REQUIRED_GATES",
    "RESULT_REVIEW_GATE_ID",
    "RESULT_REVIEW_RECEIPT",
    "RESOURCE_CAPS",
    "RESOURCE_EXCEEDED_CLASSIFICATION",
    "RUN_OUTPUT_ROOT",
    "RUN_ID",
    "SEED",
    "UPSTREAM_PREREGISTRATION_RECEIPT",
    "artifact_json_bytes",
    "artifact_receipt",
    "build_attempt_owner",
    "build_evaluation_candidate",
    "build_evidence",
    "build_failure",
    "canonical_json_bytes",
    "compare_completed_evaluations",
    "execution_claims",
    "expected_replay_execution",
    "expected_preregistration",
    "negative_protocol_claims",
    "parse_strict_json_bytes",
    "sha256_bytes",
    "validate_completed_evaluation",
    "validate_attempt_owner",
    "validate_evaluation_candidate",
    "validate_failure",
    "validate_preregistration",
    "validate_reference_payloads",
]
