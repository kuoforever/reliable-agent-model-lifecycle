"""Frozen recovery protocol for the MM-003 QLoRA post-training lifecycle.

The v2 protocol preserves the complete v1 preregistration and changes only the
closed recovery delta authorized by the tracked v1 failure classification.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import Any, NoReturn, cast

from . import mm003_baseline_protocol_v2 as baseline
from . import mm003_post_training_protocol as v1

PREREGISTRATION_VERSION = 2
GATE_ID = "MM-003-small-vlm-post-training-recovery-protocol-v2"
EXECUTION_GATE_ID = "MM-003-small-vlm-post-training-execution-v2"
EXPERIMENT_ID = "mm003-qwen2.5-vl-3b-qlora-sft-v2"
SUCCESS_NEXT_GATE_ID = "MM-003-small-vlm-post-training-result-review-v2"
RECOVERY_PROMPT_GATE = "post_training_prompt_projection_totality"

PREREGISTRATION_PATH = "configs/mm003_small_vlm_post_training_protocol_v2.json"
RUN_OUTPUT_ROOT = "work/training-runs/mm003-qlora-sft-v2"
ADAPTER_OUTPUT_ROOT = f"{RUN_OUTPUT_ROOT}/adapter"
TRAINING_RUN_ARTIFACT = f"{RUN_OUTPUT_ROOT}/training-run.json"
PREDICTIONS_ARTIFACT = f"{RUN_OUTPUT_ROOT}/mm002-predictions.json"
EVIDENCE_ARTIFACT = f"{RUN_OUTPUT_ROOT}/evidence.json"
FAILURE_ARTIFACT = f"{RUN_OUTPUT_ROOT}/failure.json"
ADAPTER_MODEL_ID = f"{v1.MODEL_ID}+mm003-qlora-sft-v2"

V1_PREREGISTRATION_RECEIPT = {
    "path": v1.PREREGISTRATION_PATH,
    "bytes": 17_601,
    "sha256": "sha256:9dfd180f24a86814fc32c5ebbfca07a31f713c8387f85ec3212dc538647cb061",
}
V1_FAILURE_RECEIPT = {
    "path": "baseline/mm003-qwen2.5-vl-3b-qlora-sft-v1-failure.json",
    "bytes": 897,
    "sha256": "sha256:8c82455b406c66a038deaaadeb9251b9eb626145a5f31d36b04d5ad7d10c72d9",
}
V1_FAILURE_CLASSIFICATION_RECEIPT = {
    "path": "baseline/mm003-qwen2.5-vl-3b-qlora-sft-v1-failure-classification.json",
    "bytes": 15_877,
    "sha256": "sha256:66b9e8352caacd1a10e750a222ce2a0a7994df385e23e31dbc76a68b6109aef6",
    "report_digest": "sha256:85fddade5e6a3c665771c6cb74c5e610f003817b3eddf5a21f1b2a070ea1dd53",
}

PROTOCOL_SOURCE_PATHS = {
    **v1.PROTOCOL_SOURCE_PATHS,
    "post_training_contract_v2": (
        "src/fullcycle_bridge/mm003_post_training_protocol_v2.py"
    ),
    "post_training_runner_v2": "scripts/run_mm003_qlora_post_training_v2.py",
}
V1_PROTOCOL_SOURCE_KEYS = tuple(sorted(v1.PROTOCOL_SOURCE_PATHS))
V2_PROTOCOL_SOURCE_KEYS = (
    "post_training_contract_v2",
    "post_training_runner_v2",
)

MODEL_ID = v1.MODEL_ID
MODEL_REVISION = v1.MODEL_REVISION
MODEL_LICENSE = v1.MODEL_LICENSE
MODEL_LICENSE_SCOPE = v1.MODEL_LICENSE_SCOPE
MODEL_ARCHITECTURE = v1.MODEL_ARCHITECTURE
MODEL_FILE_SIZES = v1.MODEL_FILE_SIZES
MODEL_WEIGHT_SHA256 = v1.MODEL_WEIGHT_SHA256
LOCKED_ENVIRONMENT = v1.LOCKED_ENVIRONMENT
BITSANDBYTES_WHEEL = v1.BITSANDBYTES_WHEEL
TRAIN_DATASET_PATH = v1.TRAIN_DATASET_PATH
VALIDATION_DATASET_PATH = v1.VALIDATION_DATASET_PATH
TRAINING_SCREENSHOT_ROOT = v1.TRAINING_SCREENSHOT_ROOT
TRAIN_RECORDS = v1.TRAIN_RECORDS
VALIDATION_RECORDS = v1.VALIDATION_RECORDS
SCREENSHOT_RECORDS = v1.SCREENSHOT_RECORDS
SYSTEM_PROMPT = v1.SYSTEM_PROMPT
TRAINING_SEED = v1.TRAINING_SEED
MM003PostTrainingProtocolError = v1.MM003PostTrainingProtocolError
parse_strict_json_bytes = v1.parse_strict_json_bytes
expected_dataset = v1.expected_dataset
validate_dataset = v1.validate_dataset
expected_screenshot_receipts = v1.expected_screenshot_receipts
audit_eval_isolation = v1.audit_eval_isolation
render_training_target = v1.render_training_target
render_training_png = v1.render_training_png


def artifact_json_bytes(value: Mapping[str, Any]) -> bytes:
    payload: object = v1.artifact_json_bytes(value)
    if not isinstance(payload, bytes):
        raise TypeError("v1 artifact serializer returned a non-bytes payload")
    return payload


def canonical_json_bytes(value: object) -> bytes:
    payload: object = v1.canonical_json_bytes(value)
    if not isinstance(payload, bytes):
        raise TypeError("v1 canonical serializer returned a non-bytes payload")
    return payload


def sha256_bytes(payload: bytes) -> str:
    digest: object = v1.sha256_bytes(payload)
    if not isinstance(digest, str):
        raise TypeError("v1 SHA-256 helper returned a non-string digest")
    return digest

PROMPT_RECEIPT_DOMAIN = b"MM003_POST_TRAINING_PROMPT_RECEIPTS_V2\0"
PROMPT_PAYLOAD_ROOT_FIELDS = [
    "case_id",
    "observation_mode",
    "instruction",
    "available_tools",
    "observation",
]
PROMPT_FORBIDDEN_SOURCE_FIELDS = [
    "family_id",
    "training_repeat_group",
    "target",
    "model_input.observation.screenshot_regions",
]


def _expected_records() -> list[dict[str, Any]]:
    return [
        *cast(list[dict[str, Any]], v1.expected_dataset("train")["records"]),
        *cast(list[dict[str, Any]], v1.expected_dataset("validation")["records"]),
    ]


_EXPECTED_RECORDS = _expected_records()
_EXPECTED_RECORD_BY_ID = {str(record["case_id"]): record for record in _EXPECTED_RECORDS}
POST_TRAINING_CASE_MODES = {
    case_id: str(record["observation_mode"])
    for case_id, record in _EXPECTED_RECORD_BY_ID.items()
}
if len(_EXPECTED_RECORD_BY_ID) != TRAIN_RECORDS + VALIDATION_RECORDS:
    raise RuntimeError("post-training case registry contains duplicate identifiers")

REQUIRED_GATES = [
    "protocol_integrity",
    "exact_model_files",
    "locked_environment",
    "training_fixture_integrity",
    RECOVERY_PROMPT_GATE,
    "eval_isolation",
    "offline_single_training_run",
    "adapter_artifact_integrity",
    "independent_adapter_load",
    "unchanged_mm002_eval",
    "total_scoring",
    "resource_caps",
    "fail_closed_claims",
]
NEXT_GATE_ACTION = (
    "execute the separately frozen v2 QLoRA lifecycle exactly once, save the "
    "Adapter, independently reload base plus Adapter, and run the unchanged "
    "nine-case MM-002 evaluation with zero retries"
)
SUCCESS_NEXT_GATE = {
    "gate_id": SUCCESS_NEXT_GATE_ID,
    "action": (
        "review the outcome-neutral v2 training, Adapter, independent reload, "
        "unchanged MM-002 evaluation, and resource evidence without inferring "
        "promotion"
    ),
}

ALLOWED_VALUE_REPLACEMENTS: dict[tuple[str, ...], Any] = {
    ("preregistration_version",): PREREGISTRATION_VERSION,
    ("experiment_id",): EXPERIMENT_ID,
    ("gate_id",): GATE_ID,
    ("decision",): "outcome_neutral_qlora_training_and_measurement_recovery_protocol",
    ("outputs", "adapter_directory"): ADAPTER_OUTPUT_ROOT,
    ("outputs", "training_run"): TRAINING_RUN_ARTIFACT,
    ("outputs", "predictions"): PREDICTIONS_ARTIFACT,
    ("outputs", "evidence"): EVIDENCE_ARTIFACT,
    ("outputs", "failure"): FAILURE_ARTIFACT,
    ("formal_gate", "required_gates"): REQUIRED_GATES,
    ("next_gate_after_freeze", "gate_id"): EXECUTION_GATE_ID,
    ("next_gate_after_freeze", "action"): NEXT_GATE_ACTION,
}
AUTHORIZED_NEW_SECTION_PATHS = (
    ("source_lineage", "v1_failure_lineage"),
    ("prompt_projection",),
    ("prompt_receipts",),
    ("success_next_gate_after_execution",),
)


def project_training_prompt(record: Mapping[str, Any]) -> dict[str, Any]:
    """Project one exact pt-* fixture record without gold or raw image regions."""

    case_id = record.get("case_id")
    if not isinstance(case_id, str) or case_id not in _EXPECTED_RECORD_BY_ID:
        _fail("POST_TRAINING_CASE_REGISTRY_MISMATCH", "$.record.case_id")
    if not _json_equal(dict(record), _EXPECTED_RECORD_BY_ID[case_id]):
        _fail("POST_TRAINING_RECORD_MISMATCH", "$.record")
    mode = record.get("observation_mode")
    if POST_TRAINING_CASE_MODES[case_id] != mode:
        _fail("POST_TRAINING_CASE_MODE_MISMATCH", "$.record.observation_mode")
    model_input = _mapping(record.get("model_input"), "$.record.model_input")
    observation = _mapping(
        model_input.get("observation"), "$.record.model_input.observation"
    )
    filtered_observation: dict[str, Any] = {
        "ocr_text": observation.get("ocr_text"),
        "grounding_cue": observation.get("grounding_cue"),
    }
    if mode in {"uia_only", "fused"}:
        filtered_observation["uia_controls"] = observation.get("uia_controls")
    return {
        "case_id": case_id,
        "observation_mode": mode,
        "instruction": model_input.get("instruction"),
        "available_tools": model_input.get("available_tools"),
        "observation": filtered_observation,
    }


def render_training_input(record: Mapping[str, Any]) -> str:
    projected = project_training_prompt(record)
    payload = canonical_json_bytes(projected)
    return "SYNTHETIC_CASE=" + payload.decode("utf-8").rstrip("\n")


def _validated_records(
    train: Mapping[str, Any], validation: Mapping[str, Any]
) -> list[dict[str, Any]]:
    if not _json_equal(dict(train), v1.expected_dataset("train")):
        _fail("DATASET_RECOMPUTATION_MISMATCH", "$.train")
    if not _json_equal(dict(validation), v1.expected_dataset("validation")):
        _fail("DATASET_RECOMPUTATION_MISMATCH", "$.validation")
    validated_train = v1.validate_dataset(train, split="train")
    validated_validation = v1.validate_dataset(validation, split="validation")
    records = [
        *cast(list[dict[str, Any]], validated_train["records"]),
        *cast(list[dict[str, Any]], validated_validation["records"]),
    ]
    case_ids = [str(record["case_id"]) for record in records]
    if len(records) != 27 or len(set(case_ids)) != 27:
        _fail("POST_TRAINING_CASE_REGISTRY_MISMATCH", "$.records")
    if case_ids != [str(record["case_id"]) for record in _EXPECTED_RECORDS]:
        _fail("POST_TRAINING_CASE_ORDER_MISMATCH", "$.records")
    return records


def expected_prompt_projection(
    train: Mapping[str, Any], validation: Mapping[str, Any]
) -> dict[str, Any]:
    records = _validated_records(train, validation)
    case_modes = {
        str(record["case_id"]): str(record["observation_mode"])
        for record in records
    }
    if not _json_equal(case_modes, POST_TRAINING_CASE_MODES):
        _fail("POST_TRAINING_CASE_MODE_MISMATCH", "$.prompt_projection.case_modes")
    return {
        "registry_records": 27,
        "case_ids_and_modes_from_tracked_fixtures": True,
        "case_modes": case_modes,
        "payload_root_fields": PROMPT_PAYLOAD_ROOT_FIELDS,
        "forbidden_source_fields": PROMPT_FORBIDDEN_SOURCE_FIELDS,
        "baseline_ground_case_registry_unchanged": True,
        "all_prompts_before_dependency_or_model_load": True,
    }


def expected_prompt_receipts(
    train: Mapping[str, Any], validation: Mapping[str, Any]
) -> dict[str, Any]:
    records = []
    for record in _validated_records(train, validation):
        payload = render_training_input(record).encode("utf-8")
        records.append(
            {
                "case_id": record["case_id"],
                "observation_mode": record["observation_mode"],
                "bytes": len(payload),
                "sha256": sha256_bytes(payload),
            }
        )
    return {
        "records": records,
        "aggregate_sha256": sha256_bytes(
            PROMPT_RECEIPT_DOMAIN + canonical_json_bytes(records)
        ),
    }


def expected_v1_failure_lineage() -> dict[str, Any]:
    return {
        "v1_preregistration": dict(V1_PREREGISTRATION_RECEIPT),
        "v1_failure_receipt": dict(V1_FAILURE_RECEIPT),
        "v1_failure_classification": dict(V1_FAILURE_CLASSIFICATION_RECEIPT),
    }


def validate_recovery_lineage_payloads(
    *,
    v1_preregistration_payload: bytes,
    v1_failure_payload: bytes,
    v1_failure_classification_payload: bytes,
) -> dict[str, dict[str, Any]]:
    payloads = {
        "v1_preregistration": (
            v1_preregistration_payload,
            V1_PREREGISTRATION_RECEIPT,
            "$.v1_preregistration",
        ),
        "v1_failure_receipt": (
            v1_failure_payload,
            V1_FAILURE_RECEIPT,
            "$.v1_failure_receipt",
        ),
        "v1_failure_classification": (
            v1_failure_classification_payload,
            V1_FAILURE_CLASSIFICATION_RECEIPT,
            "$.v1_failure_classification",
        ),
    }
    parsed: dict[str, dict[str, Any]] = {}
    for name, (payload, receipt, location) in payloads.items():
        if len(payload) != receipt["bytes"] or sha256_bytes(payload) != receipt["sha256"]:
            _fail("RECOVERY_LINEAGE_RECEIPT_MISMATCH", location)
        raw = parse_strict_json_bytes(payload, location=location)
        if not isinstance(raw, dict):
            _fail("EXPECTED_OBJECT", location)
        parsed[name] = raw
    validated_v1 = v1.validate_preregistration(parsed["v1_preregistration"])
    if not _json_equal(validated_v1, parsed["v1_preregistration"]):
        _fail("V1_PREREGISTRATION_MISMATCH", "$.v1_preregistration")
    if (
        parsed["v1_failure_classification"].get("report_digest")
        != V1_FAILURE_CLASSIFICATION_RECEIPT["report_digest"]
    ):
        _fail(
            "RECOVERY_LINEAGE_REPORT_DIGEST_MISMATCH",
            "$.v1_failure_classification.report_digest",
        )
    validate_failure_classification_recovery_policy(
        parsed["v1_failure_classification"]
    )
    return parsed


def validate_failure_classification_recovery_policy(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    """Cross-check the exact tracked recovery whitelist against this contract."""

    action = _mapping(value.get("locked_next_action"), "$.locked_next_action")
    for key, expected in {
        "gate_id": GATE_ID,
        "execution_gate_id": EXECUTION_GATE_ID,
        "experiment_id": EXPERIMENT_ID,
        "output_directory": RUN_OUTPUT_ROOT,
        "success_next_gate_id": SUCCESS_NEXT_GATE_ID,
    }.items():
        if not _json_equal(action.get(key), expected):
            _fail("RECOVERY_POLICY_IDENTITY_MISMATCH", f"$.locked_next_action.{key}")
    expected_policy = {
        "comparison_base": v1.PREREGISTRATION_PATH,
        "comparison_unit": "recursive_json_leaf",
        "arrays_compared_atomically": True,
        "unlisted_existing_leaf_values_must_be_identical": True,
        "unlisted_v1_fields_may_be_removed": False,
        "unlisted_v2_fields_may_be_added": False,
        "listed_container_replacement_authorized": False,
        "whitelist_diff_test_required": True,
    }
    if not _json_equal(action.get("allowed_difference_policy"), expected_policy):
        _fail(
            "RECOVERY_DIFFERENCE_POLICY_MISMATCH",
            "$.locked_next_action.allowed_difference_policy",
        )
    expected_required_values = {
        **{
            _path_text(path): copy.deepcopy(required)
            for path, required in ALLOWED_VALUE_REPLACEMENTS.items()
        },
        "success_next_gate_after_execution": copy.deepcopy(SUCCESS_NEXT_GATE),
    }
    if not _json_equal(action.get("required_v2_values"), expected_required_values):
        _fail(
            "RECOVERY_REQUIRED_VALUES_MISMATCH",
            "$.locked_next_action.required_v2_values",
        )
    expected_differences = {
        "exact_value_replacements": [
            _path_text(path) for path in ALLOWED_VALUE_REPLACEMENTS
        ],
        "source_lineage.protocol_sources": {
            "v1_receipts_exactly_preserved": list(V1_PROTOCOL_SOURCE_KEYS),
            "required_additions": {
                name: {
                    "path": PROTOCOL_SOURCE_PATHS[name],
                    "sha256_required": True,
                }
                for name in V2_PROTOCOL_SOURCE_KEYS
            },
            "other_additions_removals_or_replacements_allowed": False,
        },
        "authorized_new_sections": {
            "source_lineage.v1_failure_lineage": {
                "closed_schema": True,
                "required_receipts": [
                    "v1_preregistration",
                    "v1_failure_receipt",
                    "v1_failure_classification",
                ],
                "exact_file_receipts_required": True,
            },
            "prompt_projection": {
                "closed_schema": True,
                "deterministic_builder_recomputation_required": True,
                "registry_records": 27,
                "case_ids_and_modes_from_tracked_fixtures": True,
                "payload_root_fields": PROMPT_PAYLOAD_ROOT_FIELDS,
                "forbidden_source_fields": PROMPT_FORBIDDEN_SOURCE_FIELDS,
                "baseline_ground_case_registry_unchanged": True,
                "all_prompts_before_dependency_or_model_load": True,
            },
            "prompt_receipts": {
                "closed_schema": True,
                "deterministic_builder_recomputation_required": True,
                "per_case_receipts": 27,
                "per_case_fields": [
                    "case_id",
                    "observation_mode",
                    "bytes",
                    "sha256",
                ],
                "aggregate_digest_required": True,
            },
            "success_next_gate_after_execution": {
                "exact_value_required": True,
            },
        },
    }
    if not _json_equal(action.get("allowed_v2_differences"), expected_differences):
        _fail(
            "RECOVERY_ALLOWED_DIFFERENCES_MISMATCH",
            "$.locked_next_action.allowed_v2_differences",
        )
    return {
        "comparison_unit": "recursive_json_leaf",
        "exact_value_replacements": len(ALLOWED_VALUE_REPLACEMENTS),
        "preserved_protocol_sources": len(V1_PROTOCOL_SOURCE_KEYS),
        "added_protocol_sources": len(V2_PROTOCOL_SOURCE_KEYS),
        "authorized_new_sections": len(AUTHORIZED_NEW_SECTION_PATHS),
        "required_gates": len(REQUIRED_GATES),
    }


def expected_preregistration(
    *,
    freeze_status: str,
    v1_preregistration: Mapping[str, Any],
    source_hashes: Mapping[str, str],
    train: Mapping[str, Any],
    validation: Mapping[str, Any],
) -> dict[str, Any]:
    base = _validate_v1_preregistration_mapping(v1_preregistration)
    if not _json_equal(freeze_status, base["freeze_status"]):
        _fail("UNAUTHORIZED_VALUE_CHANGE", "$.freeze_status")
    if set(source_hashes) != set(PROTOCOL_SOURCE_PATHS):
        _fail("INVALID_SOURCE_KEYS", "$.source_lineage.protocol_sources")
    base_sources = _mapping(
        _mapping(base["source_lineage"], "$.source_lineage")["protocol_sources"],
        "$.source_lineage.protocol_sources",
    )
    for name in V1_PROTOCOL_SOURCE_KEYS:
        observed = _mapping(
            base_sources.get(name), f"$.source_lineage.protocol_sources.{name}"
        )
        if not _json_equal(source_hashes[name], observed.get("sha256")):
            _fail(
                "V1_PROTOCOL_SOURCE_REPLACEMENT",
                f"$.source_lineage.protocol_sources.{name}",
            )
    for name in V2_PROTOCOL_SOURCE_KEYS:
        _validate_sha256(
            source_hashes[name], f"$.source_lineage.protocol_sources.{name}.sha256"
        )

    prompt_projection = expected_prompt_projection(train, validation)
    prompt_receipts = expected_prompt_receipts(train, validation)
    result = copy.deepcopy(base)
    for path, expected_value in ALLOWED_VALUE_REPLACEMENTS.items():
        _set_path(result, path, copy.deepcopy(expected_value))
    sources = cast(
        dict[str, Any],
        cast(dict[str, Any], result["source_lineage"])["protocol_sources"],
    )
    for name in V2_PROTOCOL_SOURCE_KEYS:
        sources[name] = {
            "path": PROTOCOL_SOURCE_PATHS[name],
            "sha256": source_hashes[name],
        }
    cast(dict[str, Any], result["source_lineage"])["v1_failure_lineage"] = (
        expected_v1_failure_lineage()
    )
    result["prompt_projection"] = prompt_projection
    result["prompt_receipts"] = prompt_receipts
    result["success_next_gate_after_execution"] = copy.deepcopy(SUCCESS_NEXT_GATE)
    validate_recovery_delta(
        base,
        result,
        train=train,
        validation=validation,
        source_hashes=source_hashes,
    )
    return result


def validate_preregistration(
    value: Mapping[str, Any],
    *,
    v1_preregistration: Mapping[str, Any],
    train: Mapping[str, Any],
    validation: Mapping[str, Any],
    source_hashes: Mapping[str, str],
    require_frozen: bool = True,
) -> dict[str, Any]:
    expected = expected_preregistration(
        freeze_status=str(value.get("freeze_status")),
        v1_preregistration=v1_preregistration,
        source_hashes=source_hashes,
        train=train,
        validation=validation,
    )
    if not _json_equal(dict(value), expected):
        _fail("PREREGISTRATION_RECOMPUTATION_MISMATCH", "$.preregistration")
    if require_frozen and value.get("freeze_status") != "frozen":
        _fail("PREREGISTRATION_NOT_FROZEN", "$.freeze_status")
    return expected


def validate_prompt_preflight(
    preregistration: Mapping[str, Any],
    *,
    train: Mapping[str, Any],
    validation: Mapping[str, Any],
) -> dict[str, Any]:
    expected_projection = expected_prompt_projection(train, validation)
    expected_receipts = expected_prompt_receipts(train, validation)
    if not _json_equal(preregistration.get("prompt_projection"), expected_projection):
        _fail("PROMPT_PROJECTION_MISMATCH", "$.prompt_projection")
    if not _json_equal(preregistration.get("prompt_receipts"), expected_receipts):
        _fail("PROMPT_RECEIPT_MISMATCH", "$.prompt_receipts")
    return {
        "records_checked": len(expected_receipts["records"]),
        "receipts_matched": True,
        "aggregate_sha256": expected_receipts["aggregate_sha256"],
    }


def validate_recovery_delta(
    v1_preregistration: Mapping[str, Any],
    v2_preregistration: Mapping[str, Any],
    *,
    train: Mapping[str, Any],
    validation: Mapping[str, Any],
    source_hashes: Mapping[str, str],
) -> dict[str, Any]:
    comparison_base = _validate_v1_preregistration_mapping(v1_preregistration)
    if set(source_hashes) != set(PROTOCOL_SOURCE_PATHS):
        _fail("INVALID_SOURCE_KEYS", "$.recovery_delta.source_hashes")
    expected_new_sections = {
        ("source_lineage", "v1_failure_lineage"): expected_v1_failure_lineage(),
        ("prompt_projection",): expected_prompt_projection(train, validation),
        ("prompt_receipts",): expected_prompt_receipts(train, validation),
        ("success_next_gate_after_execution",): SUCCESS_NEXT_GATE,
    }
    expected_source_additions = {
        name: {
            "path": PROTOCOL_SOURCE_PATHS[name],
            "sha256": source_hashes[name],
        }
        for name in V2_PROTOCOL_SOURCE_KEYS
    }
    base_lineage = _mapping(
        comparison_base.get("source_lineage"), "$.v1.source_lineage"
    )
    base_sources = _mapping(
        base_lineage.get("protocol_sources"),
        "$.v1.source_lineage.protocol_sources",
    )
    for name in V1_PROTOCOL_SOURCE_KEYS:
        base_receipt = _mapping(
            base_sources.get(name), f"$.v1.source_lineage.protocol_sources.{name}"
        )
        if not _json_equal(source_hashes[name], base_receipt.get("sha256")):
            _fail(
                "V1_PROTOCOL_SOURCE_REPLACEMENT",
                f"$.recovery_delta.source_hashes.{name}",
            )
    for name in V2_PROTOCOL_SOURCE_KEYS:
        expected_source = _mapping(
            expected_source_additions[name],
            f"$.recovery_delta.expected_source_additions.{name}",
        )
        if set(expected_source) != {"path", "sha256"}:
            _fail(
                "INVALID_SOURCE_RECEIPT",
                f"$.recovery_delta.expected_source_additions.{name}",
            )
        if not _json_equal(expected_source["path"], PROTOCOL_SOURCE_PATHS[name]):
            _fail(
                "INVALID_SOURCE_RECEIPT",
                f"$.recovery_delta.expected_source_additions.{name}.path",
            )
        _validate_sha256(
            expected_source["sha256"],
            f"$.recovery_delta.expected_source_additions.{name}.sha256",
        )
    observed_replacements: set[tuple[str, ...]] = set()
    observed_source_additions: set[str] = set()
    observed_new_sections: set[tuple[str, ...]] = set()

    def compare(base: Any, candidate: Any, path: tuple[str, ...]) -> None:
        if isinstance(base, Mapping):
            if not isinstance(candidate, Mapping):
                _fail("CONTAINER_REPLACEMENT", _path_label(path))
            base_mapping = cast(Mapping[str, Any], base)
            candidate_mapping = cast(Mapping[str, Any], candidate)
            for key in base_mapping:
                if key not in candidate_mapping:
                    _fail("V1_FIELD_REMOVED", _path_label((*path, key)))
                compare(base_mapping[key], candidate_mapping[key], (*path, key))
            for key in candidate_mapping:
                if key in base_mapping:
                    continue
                added_path = (*path, key)
                if path == ("source_lineage", "protocol_sources"):
                    if key not in V2_PROTOCOL_SOURCE_KEYS:
                        _fail("UNAUTHORIZED_SOURCE_ADDITION", _path_label(added_path))
                    expected_source = expected_source_additions[key]
                    if not _json_equal(
                        dict(_mapping(candidate_mapping[key], _path_label(added_path))),
                        dict(expected_source),
                    ):
                        _fail("INVALID_SOURCE_RECEIPT", _path_label(added_path))
                    observed_source_additions.add(key)
                    continue
                if added_path not in expected_new_sections:
                    _fail("UNAUTHORIZED_FIELD_ADDITION", _path_label(added_path))
                if not _json_equal(
                    candidate_mapping[key], expected_new_sections[added_path]
                ):
                    _fail("RECOVERY_NEW_SECTION_MISMATCH", _path_label(added_path))
                observed_new_sections.add(added_path)
            return
        if isinstance(candidate, Mapping):
            _fail("CONTAINER_REPLACEMENT", _path_label(path))
        if _json_equal(base, candidate):
            return
        if path not in ALLOWED_VALUE_REPLACEMENTS:
            _fail("UNAUTHORIZED_VALUE_CHANGE", _path_label(path))
        if not _json_equal(candidate, ALLOWED_VALUE_REPLACEMENTS[path]):
            _fail("AUTHORIZED_VALUE_MISMATCH", _path_label(path))
        observed_replacements.add(path)

    compare(comparison_base, v2_preregistration, ())
    if observed_replacements != set(ALLOWED_VALUE_REPLACEMENTS):
        _fail("INCOMPLETE_RECOVERY_REPLACEMENTS", "$.recovery_delta")
    if observed_source_additions != set(V2_PROTOCOL_SOURCE_KEYS):
        _fail("INCOMPLETE_RECOVERY_SOURCE_ADDITIONS", "$.recovery_delta")
    if observed_new_sections != set(AUTHORIZED_NEW_SECTION_PATHS):
        _fail("INCOMPLETE_RECOVERY_NEW_SECTIONS", "$.recovery_delta")
    return {
        "comparison_unit": "recursive_json_leaf",
        "arrays_compared_atomically": True,
        "exact_value_replacements": sorted(
            _path_text(path) for path in observed_replacements
        ),
        "preserved_protocol_sources": list(V1_PROTOCOL_SOURCE_KEYS),
        "added_protocol_sources": sorted(observed_source_additions),
        "authorized_new_sections": sorted(
            _path_text(path) for path in observed_new_sections
        ),
        "required_gates": list(REQUIRED_GATES),
    }


def _validate_v1_preregistration_mapping(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    payload = artifact_json_bytes(dict(value))
    if (
        len(payload) != V1_PREREGISTRATION_RECEIPT["bytes"]
        or sha256_bytes(payload) != V1_PREREGISTRATION_RECEIPT["sha256"]
    ):
        _fail("V1_PREREGISTRATION_RECEIPT_MISMATCH", "$.v1_preregistration")
    validated: object = v1.validate_preregistration(value)
    if not isinstance(validated, dict):
        _fail("EXPECTED_OBJECT", "$.v1_preregistration")
    return validated


def _set_path(target: dict[str, Any], path: tuple[str, ...], value: Any) -> None:
    current = target
    for segment in path[:-1]:
        child = current.get(segment)
        if not isinstance(child, dict):
            _fail("EXPECTED_OBJECT", _path_label(path[:-1]))
        current = child
    current[path[-1]] = value


def _path_text(path: tuple[str, ...]) -> str:
    return ".".join(path)


def _path_label(path: tuple[str, ...]) -> str:
    return "$" if not path else "$." + _path_text(path)


def _json_equal(left: object, right: object) -> bool:
    """Compare JSON values recursively without Python numeric coercion."""

    if type(left) is not type(right):
        return False
    if isinstance(left, Mapping):
        if not isinstance(right, Mapping):
            return False
        left_mapping = cast(Mapping[object, object], left)
        right_mapping = cast(Mapping[object, object], right)
        if set(left_mapping) != set(right_mapping):
            return False
        return all(
            isinstance(key, str)
            and _json_equal(left_mapping[key], right_mapping[key])
            for key in left_mapping
        )
    if isinstance(left, list):
        if not isinstance(right, list) or len(left) != len(right):
            return False
        return all(
            _json_equal(left_item, right_item)
            for left_item, right_item in zip(left, right, strict=True)
        )
    if isinstance(left, float) and isinstance(right, float):
        return left.hex() == right.hex()
    return bool(left == right)


def _mapping(value: object, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail("EXPECTED_OBJECT", location)
    return cast(Mapping[str, Any], value)


def _validate_sha256(value: object, location: str) -> None:
    if not isinstance(value, str) or v1.SHA256_PATTERN.fullmatch(value) is None:
        _fail("INVALID_SHA256", location)


def _fail(code: str, location: str) -> NoReturn:
    raise MM003PostTrainingProtocolError(code, location)


__all__ = [
    "ADAPTER_MODEL_ID",
    "ADAPTER_OUTPUT_ROOT",
    "ALLOWED_VALUE_REPLACEMENTS",
    "BITSANDBYTES_WHEEL",
    "EVIDENCE_ARTIFACT",
    "EXECUTION_GATE_ID",
    "EXPERIMENT_ID",
    "FAILURE_ARTIFACT",
    "GATE_ID",
    "LOCKED_ENVIRONMENT",
    "MM003PostTrainingProtocolError",
    "MODEL_ID",
    "POST_TRAINING_CASE_MODES",
    "PREDICTIONS_ARTIFACT",
    "PREREGISTRATION_PATH",
    "PROTOCOL_SOURCE_PATHS",
    "RECOVERY_PROMPT_GATE",
    "REQUIRED_GATES",
    "RUN_OUTPUT_ROOT",
    "SUCCESS_NEXT_GATE_ID",
    "TRAINING_RUN_ARTIFACT",
    "artifact_json_bytes",
    "audit_eval_isolation",
    "baseline",
    "expected_preregistration",
    "expected_prompt_projection",
    "expected_prompt_receipts",
    "expected_screenshot_receipts",
    "parse_strict_json_bytes",
    "project_training_prompt",
    "render_training_input",
    "render_training_png",
    "render_training_target",
    "sha256_bytes",
    "validate_dataset",
    "validate_failure_classification_recovery_policy",
    "validate_preregistration",
    "validate_prompt_preflight",
    "validate_recovery_delta",
    "validate_recovery_lineage_payloads",
]
