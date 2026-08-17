"""Strict synthetic GUI grounding evaluation contract for MM-002."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
from dataclasses import asdict, dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any, Mapping, NoReturn, Sequence

GUI_GROUNDING_EVAL_VERSION = 1
REPORT_VERSION = 1
EXPECTED_CASE_COUNT = 9
MAX_SUITE_BYTES = 2 * 1024 * 1024
MAX_PREDICTIONS_BYTES = 1024 * 1024
MAX_CASES = 64
MAX_CONTROLS = 32
MAX_TOOLS = 16
MAX_ARGUMENTS = 16
MAX_STRING = 2048
RUNTIME_FREEZE_COMMIT = "324ff2fb5911e332ddb5c5f90eb41296e8faf7a9"
TRAJECTORY_SCHEMA_SHA256 = (
    "sha256:2109dcd2b06e01bda30ea19bc548cb34031811319e23f0bce5dd91a60c32964c"
)

ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,95}$")
SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
OBSERVATION_MODES = frozenset({"uia_only", "screenshot_only", "fused"})
CAPABILITIES = frozenset({"ref_grounding", "bbox_grounding", "fused_grounding"})
OCR_CONDITIONS = frozenset({"clean", "missing", "noisy"})
PERTURBATIONS = frozenset(
    {"none", "moved", "occluded", "stale_ref", "coordinate_ref_disagreement"}
)
DISPOSITIONS = frozenset({"act", "reject", "fallback"})


class GuiGroundingValidationError(ValueError):
    """Stable fail-closed validation error."""

    def __init__(self, code: str, location: str, detail: str = "") -> None:
        self.code = code
        self.location = location
        self.detail = detail
        message = f"{code} at {location}"
        if detail:
            message += f": {detail}"
        super().__init__(message)


@dataclass(frozen=True)
class GuiGroundingSuiteSummary:
    version: int
    suite_id: str
    case_count: int
    observation_modes: tuple[str, ...]
    capabilities: tuple[str, ...]
    ocr_conditions: tuple[str, ...]
    perturbations: tuple[str, ...]
    training_eligible: bool
    real_content: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
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


def sha256_json(value: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def load_suite_file(path: Path) -> dict[str, Any]:
    value = _parse_strict_json_bytes(_read_regular_file_once(path, MAX_SUITE_BYTES))
    suite = dict(_mapping(value, "$"))
    validate_suite(suite)
    return suite


def load_predictions_file(path: Path) -> dict[str, Any]:
    value = _parse_strict_json_bytes(
        _read_regular_file_once(path, MAX_PREDICTIONS_BYTES)
    )
    return dict(_mapping(value, "$"))


def validate_suite(value: object) -> GuiGroundingSuiteSummary:
    root = _mapping(value, "$")
    _exact_fields(
        root,
        {
            "gui_grounding_eval_version",
            "suite_id",
            "provenance",
            "bindings",
            "split_policy",
            "thresholds",
            "cases",
        },
        "$",
    )
    _exact_integer(
        root.get("gui_grounding_eval_version"),
        GUI_GROUNDING_EVAL_VERSION,
        "$.gui_grounding_eval_version",
        "UNSUPPORTED_VERSION",
    )
    suite_id = _identifier(root.get("suite_id"), "$.suite_id")
    training_eligible, real_content = _validate_provenance(root.get("provenance"))
    _validate_bindings(root.get("bindings"))
    _validate_split_policy(root.get("split_policy"))
    _validate_thresholds(root.get("thresholds"))

    cases = _sequence(root.get("cases"), "$.cases")
    if len(cases) != EXPECTED_CASE_COUNT or len(cases) > MAX_CASES:
        _fail("INVALID_CASE_COUNT", "$.cases")
    case_ids: set[str] = set()
    family_ids: set[str] = set()
    instructions: set[str] = set()
    observation_modes: set[str] = set()
    capabilities: set[str] = set()
    ocr_conditions: set[str] = set()
    perturbations: set[str] = set()
    for index, case_value in enumerate(cases):
        case = _validate_case(case_value, index)
        expected_case_id = f"ground-{index + 1:03d}"
        if case["case_id"] != expected_case_id:
            _fail("CASE_ORDER_MISMATCH", f"$.cases[{index}].case_id")
        for key, seen, code in (
            (case["case_id"], case_ids, "DUPLICATE_CASE_ID"),
            (case["family_id"], family_ids, "FAMILY_LEAKAGE"),
            (case["instruction"], instructions, "INSTRUCTION_LEAKAGE"),
        ):
            if key in seen:
                _fail(code, f"$.cases[{index}]")
            seen.add(key)
        observation_modes.add(case["observation_mode"])
        capabilities.add(case["capability"])
        ocr_conditions.add(case["ocr_condition"])
        perturbations.add(case["perturbation"])
    if observation_modes != OBSERVATION_MODES:
        _fail("INCOMPLETE_OBSERVATION_COVERAGE", "$.cases")
    if capabilities != CAPABILITIES:
        _fail("INCOMPLETE_CAPABILITY_COVERAGE", "$.cases")
    if ocr_conditions != OCR_CONDITIONS:
        _fail("INCOMPLETE_OCR_COVERAGE", "$.cases")
    if perturbations != PERTURBATIONS:
        _fail("INCOMPLETE_PERTURBATION_COVERAGE", "$.cases")
    return GuiGroundingSuiteSummary(
        version=GUI_GROUNDING_EVAL_VERSION,
        suite_id=suite_id,
        case_count=len(cases),
        observation_modes=tuple(sorted(observation_modes)),
        capabilities=tuple(sorted(capabilities)),
        ocr_conditions=tuple(sorted(ocr_conditions)),
        perturbations=tuple(sorted(perturbations)),
        training_eligible=training_eligible,
        real_content=real_content,
    )


def score_predictions(suite_value: object, predictions_value: object) -> dict[str, Any]:
    suite = _mapping(suite_value, "$")
    suite_summary = validate_suite(suite)
    predictions = _mapping(predictions_value, "$predictions")
    _exact_fields(
        predictions,
        {"gui_grounding_prediction_version", "suite_id", "producer", "records"},
        "$predictions",
    )
    _exact_integer(
        predictions.get("gui_grounding_prediction_version"),
        GUI_GROUNDING_EVAL_VERSION,
        "$predictions.gui_grounding_prediction_version",
        "UNSUPPORTED_VERSION",
    )
    if _identifier(predictions.get("suite_id"), "$predictions.suite_id") != (
        suite_summary.suite_id
    ):
        _fail("SUITE_BINDING_MISMATCH", "$predictions.suite_id")
    producer_kind = _validate_producer(predictions.get("producer"))
    records = _sequence(predictions.get("records"), "$predictions.records")
    cases = _sequence(suite.get("cases"), "$.cases")
    if len(records) != len(cases):
        _fail("PREDICTION_COUNT_MISMATCH", "$predictions.records")

    grounding_correct = 0
    grounding_total = 0
    iou_sum = Fraction(0, 1)
    iou_total = 0
    action_correct = 0
    tool_correct = 0
    tool_total = 0
    argument_correct = 0
    argument_total = 0
    stale_correct = 0
    stale_total = 0
    disagreement_rejection_correct = 0
    disagreement_rejection_total = 0
    prediction_disagreements = 0
    prediction_disagreement_total = 0

    threshold = Fraction(str(_mapping(suite["thresholds"], "$.thresholds")["bbox_iou"]))
    for index, (case_value, record_value) in enumerate(
        zip(cases, records, strict=True)
    ):
        case = _mapping(case_value, f"$.cases[{index}]")
        record = _validate_prediction(record_value, case, index)
        gold = _mapping(case["gold"], f"$.cases[{index}].gold")
        catalog = _sequence(
            gold["target_catalog"], f"$.cases[{index}].gold.target_catalog"
        )
        ref_target = _resolve_ref(record.get("ref"), catalog)
        bbox_target = _resolve_bbox(record.get("bbox"), catalog, threshold)
        expected_target = gold.get("target_id")
        capability = case["capability"]
        grounding_match = False
        if gold["disposition"] == "act":
            grounding_total += 1
            if capability == "ref_grounding":
                grounding_match = ref_target == expected_target
            elif capability == "bbox_grounding":
                grounding_match = bbox_target == expected_target
            else:
                grounding_match = (
                    ref_target == expected_target and bbox_target == expected_target
                )
            grounding_correct += int(grounding_match)
            tool_total += 1
            argument_total += 1
            tool_correct += int(
                record["disposition"] == "act" and record["tool"] == gold["tool"]
            )
            argument_correct += int(
                record["disposition"] == "act"
                and record["arguments"] == gold["arguments"]
            )
            if gold["bbox"] is not None:
                iou_total += 1
                iou_sum += _bbox_iou(record.get("bbox"), gold["bbox"])
            action_correct += int(record["disposition"] == "act" and grounding_match)
        else:
            action_correct += int(
                record["disposition"] == gold["disposition"]
                and record["reason"] == gold["reason"]
            )

        perturbation = case["perturbation"]
        if perturbation == "stale_ref":
            stale_total += 1
            stale_correct += int(
                record["disposition"] == "reject" and record["reason"] == "stale_ref"
            )
        if perturbation == "coordinate_ref_disagreement":
            disagreement_rejection_total += 1
            disagreement_rejection_correct += int(
                record["disposition"] == "reject"
                and record["reason"] == "coordinate_ref_disagreement"
            )
        if record.get("ref") is not None and record.get("bbox") is not None:
            prediction_disagreement_total += 1
            prediction_disagreements += int(
                ref_target is None or bbox_target is None or ref_target != bbox_target
            )

    report: dict[str, Any] = {
        "report_version": REPORT_VERSION,
        "suite_id": suite_summary.suite_id,
        "suite_sha256": sha256_json(suite),
        "predictions_sha256": sha256_json(predictions),
        "case_count": suite_summary.case_count,
        "producer_kind": producer_kind,
        "metrics": {
            "grounding_accuracy": _ratio(grounding_correct, grounding_total),
            "mean_iou": _fraction_metric(iou_sum, iou_total),
            "action_accuracy": _ratio(action_correct, len(cases)),
            "tool_accuracy": _ratio(tool_correct, tool_total),
            "argument_exact_match": _ratio(argument_correct, argument_total),
            "stale_ref_rejection": _ratio(stale_correct, stale_total),
            "coordinate_ref_disagreement_rejection": _ratio(
                disagreement_rejection_correct, disagreement_rejection_total
            ),
            "prediction_coordinate_ref_disagreement_rate": _ratio(
                prediction_disagreements, prediction_disagreement_total
            ),
        },
        "coverage": {
            "observation_modes": list(suite_summary.observation_modes),
            "capabilities": list(suite_summary.capabilities),
            "ocr_conditions": list(suite_summary.ocr_conditions),
            "perturbations": list(suite_summary.perturbations),
        },
        "claims": {
            "synthetic_eval_only": True,
            "synthetic_probe_only": producer_kind == "synthetic_probe",
            "model_predictions_declared": producer_kind == "model",
            "model_evaluated": False,
            "real_content_collected": False,
            "capture_adapter_implemented": False,
            "training_eligible": False,
            "execution_eligible": False,
            "runtime_eligible": False,
        },
    }
    return report


def score_files(suite_path: Path, predictions_path: Path) -> dict[str, Any]:
    return score_predictions(
        load_suite_file(suite_path), load_predictions_file(predictions_path)
    )


def _validate_provenance(value: object) -> tuple[bool, bool]:
    location = "$.provenance"
    provenance = _mapping(value, location)
    _exact_fields(
        provenance,
        {
            "source",
            "synthetic_only",
            "real_content",
            "capture_adapter_used",
            "automatic_lane_a_export_used",
            "training_eligible",
        },
        location,
    )
    _exact_string(
        provenance.get("source"), "reviewed_synthetic_fixture", f"{location}.source"
    )
    for key in (
        "real_content",
        "capture_adapter_used",
        "automatic_lane_a_export_used",
        "training_eligible",
    ):
        _require_false(provenance.get(key), f"{location}.{key}")
    _require_true(provenance.get("synthetic_only"), f"{location}.synthetic_only")
    return False, False


def _validate_bindings(value: object) -> None:
    location = "$.bindings"
    bindings = _mapping(value, location)
    _exact_fields(
        bindings,
        {
            "multimodal_trajectory_schema_version",
            "multimodal_trajectory_schema_sha256",
            "runtime_git_commit",
            "policy_version",
            "environment_id",
        },
        location,
    )
    _exact_integer(
        bindings.get("multimodal_trajectory_schema_version"),
        1,
        f"{location}.multimodal_trajectory_schema_version",
        "UNSUPPORTED_VERSION",
    )
    _exact_string(
        bindings.get("multimodal_trajectory_schema_sha256"),
        TRAJECTORY_SCHEMA_SHA256,
        f"{location}.multimodal_trajectory_schema_sha256",
    )
    _exact_string(
        bindings.get("runtime_git_commit"),
        RUNTIME_FREEZE_COMMIT,
        f"{location}.runtime_git_commit",
    )
    _bounded_string(bindings.get("policy_version"), f"{location}.policy_version")
    _bounded_string(bindings.get("environment_id"), f"{location}.environment_id")


def _validate_split_policy(value: object) -> None:
    location = "$.split_policy"
    policy = _mapping(value, location)
    _exact_fields(
        policy,
        {
            "split",
            "frozen",
            "gold_separated_from_model_input",
            "training_use_prohibited",
            "family_disjoint",
        },
        location,
    )
    _exact_string(policy.get("split"), "eval", f"{location}.split")
    for key in (
        "frozen",
        "gold_separated_from_model_input",
        "training_use_prohibited",
        "family_disjoint",
    ):
        _require_true(policy.get(key), f"{location}.{key}")


def _validate_thresholds(value: object) -> None:
    location = "$.thresholds"
    thresholds = _mapping(value, location)
    _exact_fields(thresholds, {"bbox_iou"}, location)
    number = thresholds.get("bbox_iou")
    if (
        isinstance(number, bool)
        or not isinstance(number, (int, float))
        or not math.isfinite(number)
        or number != 0.5
    ):
        _fail("INVALID_THRESHOLD", f"{location}.bbox_iou")


def _validate_case(value: object, index: int) -> dict[str, str]:
    location = f"$.cases[{index}]"
    case = _mapping(value, location)
    _exact_fields(
        case,
        {
            "case_id",
            "family_id",
            "capability",
            "observation_mode",
            "ocr_condition",
            "perturbation",
            "model_input",
            "gold",
        },
        location,
    )
    case_id = _identifier(case.get("case_id"), f"{location}.case_id")
    family_id = _identifier(case.get("family_id"), f"{location}.family_id")
    capability = _enum(case.get("capability"), CAPABILITIES, f"{location}.capability")
    observation_mode = _enum(
        case.get("observation_mode"), OBSERVATION_MODES, f"{location}.observation_mode"
    )
    ocr_condition = _enum(
        case.get("ocr_condition"), OCR_CONDITIONS, f"{location}.ocr_condition"
    )
    perturbation = _enum(
        case.get("perturbation"), PERTURBATIONS, f"{location}.perturbation"
    )
    instruction = _validate_model_input(
        case.get("model_input"), observation_mode, capability, ocr_condition, location
    )
    _validate_gold(
        case.get("gold"), capability, perturbation, case.get("model_input"), location
    )
    return {
        "case_id": case_id,
        "family_id": family_id,
        "capability": capability,
        "observation_mode": observation_mode,
        "ocr_condition": ocr_condition,
        "perturbation": perturbation,
        "instruction": instruction,
    }


def _validate_model_input(
    value: object,
    observation_mode: str,
    capability: str,
    ocr_condition: str,
    case_location: str,
) -> str:
    location = f"{case_location}.model_input"
    model_input = _mapping(value, location)
    _exact_fields(
        model_input, {"instruction", "available_tools", "observation"}, location
    )
    instruction = _bounded_string(
        model_input.get("instruction"), f"{location}.instruction"
    )
    tools = _sequence(model_input.get("available_tools"), f"{location}.available_tools")
    if not tools or len(tools) > MAX_TOOLS:
        _fail("INVALID_TOOL_COUNT", f"{location}.available_tools")
    parsed_tools = [
        _identifier(item, f"{location}.available_tools[{i}]")
        for i, item in enumerate(tools)
    ]
    if len(set(parsed_tools)) != len(parsed_tools):
        _fail("DUPLICATE_TOOL", f"{location}.available_tools")
    observation = _mapping(model_input.get("observation"), f"{location}.observation")
    _exact_fields(
        observation,
        {"uia_controls", "screenshot_regions", "ocr_text", "grounding_cue"},
        f"{location}.observation",
    )
    uia = _validate_uia_controls(
        observation.get("uia_controls"), f"{location}.observation.uia_controls"
    )
    regions = _validate_regions(
        observation.get("screenshot_regions"),
        f"{location}.observation.screenshot_regions",
    )
    if observation_mode == "uia_only" and (not uia or regions):
        _fail("OBSERVATION_MODE_MISMATCH", f"{location}.observation")
    if observation_mode == "screenshot_only" and (uia or not regions):
        _fail("OBSERVATION_MODE_MISMATCH", f"{location}.observation")
    if observation_mode == "fused" and (not uia or not regions):
        _fail("OBSERVATION_MODE_MISMATCH", f"{location}.observation")
    ocr_text = observation.get("ocr_text")
    if not isinstance(ocr_text, str) or len(ocr_text) > MAX_STRING:
        _fail("INVALID_STRING", f"{location}.observation.ocr_text")
    if (ocr_condition == "missing") != (ocr_text == ""):
        _fail("OCR_CONDITION_MISMATCH", f"{location}.observation.ocr_text")
    cue = _mapping(
        observation.get("grounding_cue"), f"{location}.observation.grounding_cue"
    )
    _exact_fields(cue, {"ref", "bbox"}, f"{location}.observation.grounding_cue")
    cue_ref = _nullable_identifier(
        cue.get("ref"), f"{location}.observation.grounding_cue.ref"
    )
    cue_bbox = _nullable_bbox(
        cue.get("bbox"), f"{location}.observation.grounding_cue.bbox"
    )
    if capability == "ref_grounding" and (cue_ref is None or cue_bbox is not None):
        _fail("CAPABILITY_CUE_MISMATCH", f"{location}.observation.grounding_cue")
    if capability == "bbox_grounding" and (cue_ref is not None or cue_bbox is None):
        _fail("CAPABILITY_CUE_MISMATCH", f"{location}.observation.grounding_cue")
    if capability == "fused_grounding" and (cue_ref is None or cue_bbox is None):
        _fail("CAPABILITY_CUE_MISMATCH", f"{location}.observation.grounding_cue")
    return instruction


def _validate_uia_controls(value: object, location: str) -> list[Mapping[str, Any]]:
    controls = _sequence(value, location)
    if len(controls) > MAX_CONTROLS:
        _fail("TOO_MANY_CONTROLS", location)
    result: list[Mapping[str, Any]] = []
    refs: set[str] = set()
    for index, item in enumerate(controls):
        item_location = f"{location}[{index}]"
        control = _mapping(item, item_location)
        _exact_fields(control, {"ref", "role", "name", "state", "bbox"}, item_location)
        ref = _identifier(control.get("ref"), f"{item_location}.ref")
        if ref in refs:
            _fail("DUPLICATE_REF", f"{item_location}.ref")
        refs.add(ref)
        _bounded_string(control.get("role"), f"{item_location}.role")
        _bounded_string(control.get("name"), f"{item_location}.name")
        _enum(
            control.get("state"),
            frozenset({"enabled", "disabled", "stale"}),
            f"{item_location}.state",
        )
        _nullable_bbox(control.get("bbox"), f"{item_location}.bbox")
        result.append(control)
    return result


def _validate_regions(value: object, location: str) -> list[Mapping[str, Any]]:
    regions = _sequence(value, location)
    if len(regions) > MAX_CONTROLS:
        _fail("TOO_MANY_REGIONS", location)
    result: list[Mapping[str, Any]] = []
    ids: set[str] = set()
    for index, item in enumerate(regions):
        item_location = f"{location}[{index}]"
        region = _mapping(item, item_location)
        _exact_fields(region, {"region_id", "label", "bbox", "occluded"}, item_location)
        region_id = _identifier(region.get("region_id"), f"{item_location}.region_id")
        if region_id in ids:
            _fail("DUPLICATE_REGION", f"{item_location}.region_id")
        ids.add(region_id)
        _bounded_string(region.get("label"), f"{item_location}.label")
        _bbox(region.get("bbox"), f"{item_location}.bbox")
        _boolean(region.get("occluded"), f"{item_location}.occluded")
        result.append(region)
    return result


def _validate_gold(
    value: object,
    capability: str,
    perturbation: str,
    model_input_value: object,
    case_location: str,
) -> None:
    location = f"{case_location}.gold"
    gold = _mapping(value, location)
    _exact_fields(
        gold,
        {
            "disposition",
            "tool",
            "arguments",
            "ref",
            "bbox",
            "target_id",
            "reason",
            "target_catalog",
        },
        location,
    )
    disposition = _enum(
        gold.get("disposition"), DISPOSITIONS, f"{location}.disposition"
    )
    catalog = _validate_catalog(
        gold.get("target_catalog"), f"{location}.target_catalog"
    )
    if disposition == "act":
        tool = _identifier(gold.get("tool"), f"{location}.tool")
        model_input = _mapping(model_input_value, f"{case_location}.model_input")
        if tool not in _sequence(
            model_input["available_tools"],
            f"{case_location}.model_input.available_tools",
        ):
            _fail("GOLD_TOOL_UNAVAILABLE", f"{location}.tool")
        _arguments(gold.get("arguments"), f"{location}.arguments")
        ref = _nullable_identifier(gold.get("ref"), f"{location}.ref")
        bbox = _nullable_bbox(gold.get("bbox"), f"{location}.bbox")
        target_id = _identifier(gold.get("target_id"), f"{location}.target_id")
        _require_none(gold.get("reason"), f"{location}.reason")
        if target_id not in {item["target_id"] for item in catalog}:
            _fail("UNKNOWN_TARGET", f"{location}.target_id")
        if capability == "ref_grounding" and (ref is None or bbox is not None):
            _fail("GOLD_CAPABILITY_MISMATCH", location)
        if capability == "bbox_grounding" and (ref is not None or bbox is None):
            _fail("GOLD_CAPABILITY_MISMATCH", location)
        if capability == "fused_grounding" and (ref is None or bbox is None):
            _fail("GOLD_CAPABILITY_MISMATCH", location)
        expected = next(item for item in catalog if item["target_id"] == target_id)
        if ref is not None and ref != expected["ref"]:
            _fail("GOLD_REF_MISMATCH", f"{location}.ref")
        if bbox is not None and bbox != expected["bbox"]:
            _fail("GOLD_BBOX_MISMATCH", f"{location}.bbox")
        if perturbation in {"stale_ref", "occluded", "coordinate_ref_disagreement"}:
            _fail("PERTURBATION_OUTCOME_MISMATCH", location)
    else:
        for key in ("tool", "arguments", "ref", "bbox", "target_id"):
            _require_none(gold.get(key), f"{location}.{key}")
        reason = _identifier(gold.get("reason"), f"{location}.reason")
        expected_terminal = {
            "stale_ref": ("reject", "stale_ref"),
            "coordinate_ref_disagreement": ("reject", "coordinate_ref_disagreement"),
            "occluded": ("fallback", "insufficient_visual_evidence"),
        }.get(perturbation)
        if expected_terminal != (disposition, reason):
            _fail("PERTURBATION_OUTCOME_MISMATCH", location)


def _validate_catalog(value: object, location: str) -> list[Mapping[str, Any]]:
    items = _sequence(value, location)
    if not items or len(items) > MAX_CONTROLS:
        _fail("INVALID_CATALOG_COUNT", location)
    result: list[Mapping[str, Any]] = []
    target_ids: set[str] = set()
    refs: set[str] = set()
    boxes: set[tuple[int, int, int, int]] = set()
    for index, item in enumerate(items):
        item_location = f"{location}[{index}]"
        target = _mapping(item, item_location)
        _exact_fields(target, {"target_id", "ref", "bbox"}, item_location)
        target_id = _identifier(target.get("target_id"), f"{item_location}.target_id")
        ref = _identifier(target.get("ref"), f"{item_location}.ref")
        bbox = _bbox(target.get("bbox"), f"{item_location}.bbox")
        if target_id in target_ids or ref in refs or bbox in boxes:
            _fail("DUPLICATE_CATALOG_TARGET", item_location)
        target_ids.add(target_id)
        refs.add(ref)
        boxes.add(bbox)
        result.append({"target_id": target_id, "ref": ref, "bbox": bbox})
    return result


def _validate_producer(value: object) -> str:
    location = "$predictions.producer"
    producer = _mapping(value, location)
    _exact_fields(producer, {"kind", "model_id", "model_revision"}, location)
    kind = _enum(
        producer.get("kind"),
        frozenset({"synthetic_probe", "model"}),
        f"{location}.kind",
    )
    if kind == "synthetic_probe":
        _require_none(producer.get("model_id"), f"{location}.model_id")
        _require_none(producer.get("model_revision"), f"{location}.model_revision")
    else:
        _bounded_string(producer.get("model_id"), f"{location}.model_id")
        _bounded_string(producer.get("model_revision"), f"{location}.model_revision")
    return kind


def _validate_prediction(
    value: object, case: Mapping[str, Any], index: int
) -> Mapping[str, Any]:
    location = f"$predictions.records[{index}]"
    record = _mapping(value, location)
    _exact_fields(
        record,
        {"case_id", "disposition", "tool", "arguments", "ref", "bbox", "reason"},
        location,
    )
    if _identifier(record.get("case_id"), f"{location}.case_id") != case["case_id"]:
        _fail("PREDICTION_ORDER_MISMATCH", f"{location}.case_id")
    disposition = _enum(
        record.get("disposition"), DISPOSITIONS, f"{location}.disposition"
    )
    if disposition == "act":
        _identifier(record.get("tool"), f"{location}.tool")
        _arguments(record.get("arguments"), f"{location}.arguments")
        ref = _nullable_identifier(record.get("ref"), f"{location}.ref")
        bbox = _nullable_bbox(record.get("bbox"), f"{location}.bbox")
        if ref is None and bbox is None:
            _fail("MISSING_GROUNDING", location)
        _require_none(record.get("reason"), f"{location}.reason")
    else:
        for key in ("tool", "arguments", "ref", "bbox"):
            _require_none(record.get(key), f"{location}.{key}")
        _identifier(record.get("reason"), f"{location}.reason")
    return record


def _resolve_ref(value: object, catalog: Sequence[Any]) -> str | None:
    if not isinstance(value, str):
        return None
    for item in catalog:
        target = _mapping(item, "$catalog")
        if target["ref"] == value:
            return str(target["target_id"])
    return None


def _resolve_bbox(
    value: object, catalog: Sequence[Any], threshold: Fraction
) -> str | None:
    if value is None:
        return None
    try:
        _bbox(value, "$prediction.bbox")
    except GuiGroundingValidationError:
        return None
    scored = [
        (
            _bbox_iou(value, _mapping(item, "$catalog")["bbox"]),
            str(_mapping(item, "$catalog")["target_id"]),
        )
        for item in catalog
    ]
    best = max(score for score, _ in scored)
    if best < threshold or sum(score == best for score, _ in scored) != 1:
        return None
    return next(target for score, target in scored if score == best)


def _bbox_iou(left_value: object, right_value: object) -> Fraction:
    if left_value is None:
        return Fraction(0, 1)
    try:
        left = _bbox(left_value, "$left_bbox")
        right = _bbox(right_value, "$right_bbox")
    except GuiGroundingValidationError:
        return Fraction(0, 1)
    x1 = max(left[0], right[0])
    y1 = max(left[1], right[1])
    x2 = min(left[2], right[2])
    y2 = min(left[3], right[3])
    intersection = max(0, x2 - x1) * max(0, y2 - y1)
    left_area = (left[2] - left[0]) * (left[3] - left[1])
    right_area = (right[2] - right[0]) * (right[3] - right[1])
    union = left_area + right_area - intersection
    return Fraction(intersection, union)


def _ratio(correct: int, total: int) -> dict[str, int | float]:
    if total <= 0:
        _fail("EMPTY_METRIC_DENOMINATOR", "$report.metrics")
    return {"correct": correct, "total": total, "value": correct / total}


def _fraction_metric(total_value: Fraction, count: int) -> dict[str, int | float]:
    if count <= 0:
        _fail("EMPTY_METRIC_DENOMINATOR", "$report.metrics.mean_iou")
    mean = total_value / count
    return {
        "numerator": mean.numerator,
        "denominator": mean.denominator,
        "value": float(mean),
    }


def _arguments(value: object, location: str) -> Mapping[str, Any]:
    arguments = _mapping(value, location)
    if len(arguments) > MAX_ARGUMENTS:
        _fail("TOO_MANY_ARGUMENTS", location)
    for key, item in arguments.items():
        _identifier(key, f"{location}.key")
        if isinstance(item, bool) or item is None:
            continue
        if isinstance(item, str):
            if len(item) > MAX_STRING:
                _fail("STRING_TOO_LONG", f"{location}.{key}")
            continue
        if isinstance(item, int):
            continue
        if isinstance(item, float) and math.isfinite(item):
            continue
        _fail("INVALID_ARGUMENT_VALUE", f"{location}.{key}")
    return arguments


def _bbox(value: object, location: str) -> tuple[int, int, int, int]:
    coordinates = _sequence(value, location)
    if len(coordinates) != 4:
        _fail("INVALID_BBOX", location)
    parsed: list[int] = []
    for index, coordinate in enumerate(coordinates):
        if (
            isinstance(coordinate, bool)
            or not isinstance(coordinate, int)
            or not 0 <= coordinate <= 4096
        ):
            _fail("INVALID_BBOX", f"{location}[{index}]")
        parsed.append(coordinate)
    if parsed[0] >= parsed[2] or parsed[1] >= parsed[3]:
        _fail("INVALID_BBOX", location)
    return parsed[0], parsed[1], parsed[2], parsed[3]


def _nullable_bbox(value: object, location: str) -> tuple[int, int, int, int] | None:
    if value is None:
        return None
    return _bbox(value, location)


def _mapping(value: object, location: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        _fail("EXPECTED_OBJECT", location)
    return value


def _sequence(value: object, location: str) -> Sequence[Any]:
    if not isinstance(value, list):
        _fail("EXPECTED_ARRAY", location)
    return value


def _exact_fields(value: Mapping[str, Any], expected: set[str], location: str) -> None:
    actual = set(value)
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    if missing:
        _fail("MISSING_FIELD", location, ",".join(missing))
    if unknown:
        _fail("UNKNOWN_FIELD", location, ",".join(unknown))


def _string(value: object, location: str) -> str:
    if not isinstance(value, str):
        _fail("EXPECTED_STRING", location)
    return value


def _bounded_string(value: object, location: str) -> str:
    text = _string(value, location)
    if not text or len(text) > MAX_STRING:
        _fail("INVALID_STRING", location)
    return text


def _identifier(value: object, location: str) -> str:
    text = _string(value, location)
    if ID_PATTERN.fullmatch(text) is None:
        _fail("INVALID_IDENTIFIER", location)
    return text


def _nullable_identifier(value: object, location: str) -> str | None:
    if value is None:
        return None
    return _identifier(value, location)


def _enum(value: object, allowed: frozenset[str], location: str) -> str:
    text = _string(value, location)
    if text not in allowed:
        _fail("INVALID_ENUM", location)
    return text


def _boolean(value: object, location: str) -> bool:
    if not isinstance(value, bool):
        _fail("EXPECTED_BOOLEAN", location)
    return value


def _require_true(value: object, location: str) -> None:
    if value is not True:
        _fail("EXPECTED_TRUE", location)


def _require_false(value: object, location: str) -> None:
    if value is not False:
        _fail("EXPECTED_FALSE", location)


def _require_none(value: object, location: str) -> None:
    if value is not None:
        _fail("EXPECTED_NULL", location)


def _exact_integer(value: object, expected: int, location: str, code: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value != expected:
        _fail(code, location)


def _exact_string(value: object, expected: str, location: str) -> None:
    if value != expected:
        _fail("VALUE_MISMATCH", location)


def _parse_strict_json_bytes(payload: bytes) -> object:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        _fail("INVALID_UTF8", "$", str(exc))

    def reject_constant(value: str) -> NoReturn:
        _fail("NONFINITE_NUMBER", "$", value)

    def reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, item in pairs:
            if key in result:
                _fail("DUPLICATE_JSON_KEY", "$", key)
            result[key] = item
        return result

    try:
        return json.loads(
            text, object_pairs_hook=reject_duplicates, parse_constant=reject_constant
        )
    except GuiGroundingValidationError:
        raise
    except (json.JSONDecodeError, RecursionError) as exc:
        _fail("MALFORMED_JSON", "$", str(exc))


def _read_regular_file_once(path: Path, maximum_bytes: int) -> bytes:
    try:
        before = path.lstat()
    except OSError as exc:
        _fail("UNSAFE_FILE", "$file", str(exc))
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    if (
        not stat.S_ISREG(before.st_mode)
        or path.is_symlink()
        or bool(getattr(before, "st_file_attributes", 0) & reparse_flag)
        or before.st_nlink != 1
        or before.st_size > maximum_bytes
    ):
        _fail("UNSAFE_FILE", "$file")
    try:
        with path.open("rb") as handle:
            opened = os.fstat(handle.fileno())
            if (before.st_dev, before.st_ino, before.st_size) != (
                opened.st_dev,
                opened.st_ino,
                opened.st_size,
            ):
                _fail("FILE_IDENTITY_CHANGED", "$file")
            payload = handle.read(maximum_bytes + 1)
            opened_after = os.fstat(handle.fileno())
        after = path.lstat()
    except OSError as exc:
        _fail("UNSAFE_FILE", "$file", str(exc))
    if (
        len(payload) > maximum_bytes
        or (opened.st_dev, opened.st_ino, opened.st_size)
        != (opened_after.st_dev, opened_after.st_ino, opened_after.st_size)
        or (before.st_dev, before.st_ino, before.st_size)
        != (after.st_dev, after.st_ino, after.st_size)
    ):
        _fail("FILE_IDENTITY_CHANGED", "$file")
    return payload


def _fail(code: str, location: str, detail: str = "") -> NoReturn:
    raise GuiGroundingValidationError(code, location, detail)


__all__ = [
    "EXPECTED_CASE_COUNT",
    "GUI_GROUNDING_EVAL_VERSION",
    "GuiGroundingSuiteSummary",
    "GuiGroundingValidationError",
    "canonical_json_bytes",
    "load_predictions_file",
    "load_suite_file",
    "score_files",
    "score_predictions",
    "sha256_json",
    "validate_suite",
]
