"""Model-free, fail-closed data protocol for MM-004 hard negatives."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any, NoReturn

PROTOCOL_VERSION = 1
RECORD_VERSION = 1
GATE_ID = "MM-004-multimodal-hard-negative-data-protocol-v1"
NEXT_GATE = "MM-004-multimodal-hard-negative-data-generation-v1"

CATEGORY_IDS = (
    "wrong_control_grounding",
    "observation_conflict",
    "ignored_post_state",
    "duplicate_side_effect",
    "approval_bypass",
    "tool_failure_false_success",
    "plausible_without_evidence",
)
SPLITS = frozenset({"train", "validation"})
VARIANTS = frozenset({"clean", "hard_negative"})
VERDICTS = frozenset({"accept", "reject"})
IDENTITY_KINDS = (
    "case_ids",
    "family_ids",
    "instruction_sha256",
    "observation_sha256",
    "candidate_sha256",
    "image_sha256",
)
CLAIM_KEYS = (
    "records_generated",
    "dataset_validated",
    "splits_frozen",
    "verifier_evaluated",
    "model_trained",
    "model_evaluated",
    "quality_improved",
    "safety_established",
    "real_content_collected",
    "capture_adapter_used",
    "runtime_repository_changed",
    "direct_desktop_execution",
    "serving_eligible",
    "promotion_eligible",
    "runtime_eligible",
)
REQUIRED_GATES = (
    "protocol_integrity",
    "source_receipt_integrity",
    "synthetic_source_eligibility",
    "closed_record_shape",
    "deterministic_identity",
    "clean_negative_pair_binding",
    "seven_category_coverage",
    "family_split_isolation",
    "content_split_isolation",
    "upstream_exclusion_collision",
    "verifier_evidence_complete",
    "runtime_authority_preserved",
    "fail_closed_claims",
)

_ID = re.compile(r"[a-z0-9][a-z0-9._-]{0,127}\Z")
_SHA256 = re.compile(r"sha256:[0-9a-f]{64}\Z")


class MM004ProtocolError(ValueError):
    """Stable validation error for the MM-004 protocol and future records."""

    def __init__(self, code: str, location: str = "$") -> None:
        self.code = code
        self.location = location
        super().__init__(f"{code} at {location}")


@dataclass(frozen=True)
class ProtocolSummary:
    protocol_version: int
    gate_id: str
    category_count: int
    excluded_case_count: int
    excluded_family_count: int
    protocol_frozen: bool
    records_generated: bool
    next_gate: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


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


def sha256_bytes(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def identity(kind: str, value: object) -> str:
    """Return a domain-separated identity for future leakage checks."""

    if kind not in {
        "family",
        "pair",
        "record",
        "instruction",
        "observation",
        "candidate",
    }:
        _fail("IDENTITY_KIND_INVALID", "$.identity.kind")
    payload = b"mm004:" + kind.encode("ascii") + b":v1\0" + canonical_json_bytes(value)
    return sha256_bytes(payload)


def expected_protocol(
    *,
    freeze_status: str,
    source_receipts: Mapping[str, Mapping[str, Any]],
    exclusions: Mapping[str, Sequence[str]],
) -> dict[str, Any]:
    if freeze_status not in {"draft", "frozen"}:
        _fail("FREEZE_STATUS_INVALID", "$.freeze_status")
    receipts = _validate_source_receipts(source_receipts)
    registry = _validate_exclusions(exclusions)
    categories = [
        {
            "category_id": category_id,
            "clean_requirement": _category_rules(category_id)[0],
            "negative_mutation": _category_rules(category_id)[1],
            "expected_negative_verdict": "reject",
        }
        for category_id in CATEGORY_IDS
    ]
    return {
        "mm004_hard_negative_protocol_version": PROTOCOL_VERSION,
        "gate_id": GATE_ID,
        "freeze_status": freeze_status,
        "decision": "outcome_neutral_model_free_data_construction_protocol",
        "source_lineage": {
            "receipts": receipts,
            "usage": "read_only_identity_and_exclusion_evidence",
            "mm002_gold_may_be_copied": False,
            "mm003_adapter_may_be_modified": False,
            "consumed_repeatability_output_may_be_reopened": False,
        },
        "exclusion_registry": registry,
        "record_contract": {
            "record_version": RECORD_VERSION,
            "pair_variants": ["clean", "hard_negative"],
            "splits": ["train", "validation"],
            "required_fields": [
                "mm004_hard_negative_record_version",
                "record_id",
                "pair_id",
                "family_id",
                "split",
                "variant",
                "category_id",
                "instruction",
                "observation",
                "candidate_action",
                "verifier",
                "provenance",
                "identities",
            ],
            "identities": {
                "algorithm": "domain_separated_sha256_of_canonical_json",
                "family_domain": "mm004:family:v1",
                "pair_domain": "mm004:pair:v1",
                "record_domain": "mm004:record:v1",
                "family_basis": ["category_id", "instruction"],
                "pair_basis": ["family_id", "category_id", "instruction"],
                "record_id_excludes": ["record_id"],
            },
            "pair_invariants": {
                "exactly_one_clean_and_one_hard_negative": True,
                "same_pair_family_split_category_instruction": True,
                "negative_changes_observation_or_candidate": True,
                "clean_verdict": "accept",
                "hard_negative_verdict": "reject",
            },
        },
        "categories": categories,
        "split_policy": {
            "pair_must_remain_in_one_split": True,
            "family_disjoint_across_splits": True,
            "instruction_disjoint_across_splits": True,
            "observation_disjoint_across_splits": True,
            "candidate_disjoint_across_splits": True,
            "image_disjoint_across_splits": True,
            "all_upstream_exclusion_collisions_prohibited": True,
            "generation_seed_and_counts_deferred_to_next_gate": True,
        },
        "provenance_policy": {
            "synthetic_only": True,
            "real_desktop_capture": False,
            "lane_b_rich_capture": False,
            "lane_a_may_supply_rich_content": False,
            "lane_a_may_inform_verifier_taxonomy_only": True,
        },
        "authority_contract": {
            "model_output_has_execution_authority": False,
            "runtime_is_sole_policy_approval_wal_dispatch_boundary": True,
            "runtime_policy_or_approval_bypass": False,
            "runtime_integration_changed": False,
        },
        "required_gates": list(REQUIRED_GATES),
        "claims": {key: False for key in CLAIM_KEYS},
        "next_gate": NEXT_GATE,
    }


def validate_protocol(
    value: object,
    *,
    source_receipts: Mapping[str, Mapping[str, Any]],
    exclusions: Mapping[str, Sequence[str]],
) -> ProtocolSummary:
    root = _mapping(value, "$")
    expected = expected_protocol(
        freeze_status="frozen",
        source_receipts=source_receipts,
        exclusions=exclusions,
    )
    if root != expected:
        _fail("PROTOCOL_MISMATCH")
    claims = _mapping(root["claims"], "$.claims")
    if set(claims) != set(CLAIM_KEYS) or any(claims.values()):
        _fail("CLAIMS_NOT_FAIL_CLOSED", "$.claims")
    registry = _mapping(root["exclusion_registry"], "$.exclusion_registry")
    return ProtocolSummary(
        protocol_version=PROTOCOL_VERSION,
        gate_id=GATE_ID,
        category_count=len(CATEGORY_IDS),
        excluded_case_count=len(_sequence(registry["case_ids"], "$.case_ids")),
        excluded_family_count=len(
            _sequence(registry["family_ids"], "$.family_ids")
        ),
        protocol_frozen=True,
        records_generated=False,
        next_gate=NEXT_GATE,
    )


def build_record(
    *,
    split: str,
    variant: str,
    category_id: str,
    instruction: str,
    observation: Mapping[str, Any],
    candidate_action: Mapping[str, Any],
    verifier: Mapping[str, Any],
    provenance: Mapping[str, Any],
) -> dict[str, Any]:
    family_id = identity(
        "family", {"category_id": category_id, "instruction": instruction}
    )
    pair_id = identity(
        "pair",
        {
            "family_id": family_id,
            "category_id": category_id,
            "instruction": instruction,
        },
    )
    body: dict[str, Any] = {
        "mm004_hard_negative_record_version": RECORD_VERSION,
        "pair_id": pair_id,
        "family_id": family_id,
        "split": split,
        "variant": variant,
        "category_id": category_id,
        "instruction": instruction,
        "observation": dict(observation),
        "candidate_action": dict(candidate_action),
        "verifier": dict(verifier),
        "provenance": dict(provenance),
        "identities": {
            "instruction_sha256": identity("instruction", instruction),
            "observation_sha256": identity("observation", observation),
            "candidate_sha256": identity("candidate", candidate_action),
            "image_sha256": sorted(_image_hashes(observation)),
        },
    }
    record_id = identity("record", body)
    return {"record_id": record_id, **body}


def validate_records(
    records_value: object, exclusions: Mapping[str, Sequence[str]]
) -> dict[str, Any]:
    records = _sequence(records_value, "$")
    if not records:
        _fail("RECORDS_EMPTY")
    registry = _validate_exclusions(exclusions)
    excluded = {key: set(values) for key, values in registry.items()}
    pairs: dict[str, list[Mapping[str, Any]]] = {}
    split_identities: dict[str, dict[str, set[str]]] = {
        split: {kind: set() for kind in IDENTITY_KINDS[1:]}
        for split in SPLITS
    }
    seen_records: set[str] = set()
    categories: set[str] = set()
    for index, raw in enumerate(records):
        record = _validate_record(raw, index)
        record_id = str(record["record_id"])
        if record_id in seen_records:
            _fail("DUPLICATE_RECORD_ID", f"$[{index}].record_id")
        seen_records.add(record_id)
        pairs.setdefault(str(record["pair_id"]), []).append(record)
        categories.add(str(record["category_id"]))
        if record_id in excluded["case_ids"]:
            _fail("UPSTREAM_EXCLUSION_COLLISION", f"$[{index}].record_id")
        if record["family_id"] in excluded["family_ids"]:
            _fail("UPSTREAM_EXCLUSION_COLLISION", f"$[{index}].family_id")
        identities = _mapping(record["identities"], f"$[{index}].identities")
        split = str(record["split"])
        for kind in IDENTITY_KINDS[2:5]:
            if identities[kind] in excluded[kind]:
                _fail("UPSTREAM_EXCLUSION_COLLISION", f"$[{index}].identities.{kind}")
            split_identities[split][kind].add(str(identities[kind]))
        for image_hash in _sequence(
            identities["image_sha256"], f"$[{index}].identities.image_sha256"
        ):
            if image_hash in excluded["image_sha256"]:
                _fail("UPSTREAM_EXCLUSION_COLLISION", f"$[{index}].identities.image_sha256")
            split_identities[split]["image_sha256"].add(image_hash)
        split_identities[split]["family_ids"].add(str(record["family_id"]))
    for pair_id, pair in pairs.items():
        _validate_pair(pair_id, pair)
    if categories != set(CATEGORY_IDS):
        _fail("INCOMPLETE_CATEGORY_COVERAGE")
    observed_splits = {str(_mapping(record, "$")["split"]) for record in records}
    if observed_splits != SPLITS:
        _fail("INCOMPLETE_SPLIT_COVERAGE")
    for kind in IDENTITY_KINDS[1:]:
        if split_identities["train"][kind] & split_identities["validation"][kind]:
            _fail("CROSS_SPLIT_LEAKAGE", f"$.{kind}")
    return {
        "record_count": len(records),
        "pair_count": len(pairs),
        "category_count": len(categories),
        "splits": sorted(observed_splits),
    }


def _validate_record(value: object, index: int) -> Mapping[str, Any]:
    location = f"$[{index}]"
    record = _mapping(value, location)
    expected_fields = {
        "mm004_hard_negative_record_version", "record_id", "pair_id", "family_id",
        "split", "variant", "category_id", "instruction", "observation",
        "candidate_action", "verifier", "provenance", "identities",
    }
    if set(record) != expected_fields:
        _fail("RECORD_SHAPE_INVALID", location)
    if record["mm004_hard_negative_record_version"] != RECORD_VERSION:
        _fail("RECORD_VERSION_INVALID", location)
    for key in ("record_id", "pair_id", "family_id"):
        _sha256(record[key], f"{location}.{key}")
    if record["split"] not in SPLITS or record["variant"] not in VARIANTS:
        _fail("RECORD_ENUM_INVALID", location)
    if record["category_id"] not in CATEGORY_IDS:
        _fail("CATEGORY_INVALID", f"{location}.category_id")
    if not isinstance(record["instruction"], str) or not record["instruction"]:
        _fail("INSTRUCTION_INVALID", f"{location}.instruction")
    observation = _mapping(record["observation"], f"{location}.observation")
    candidate = _mapping(record["candidate_action"], f"{location}.candidate_action")
    verifier = _mapping(record["verifier"], f"{location}.verifier")
    if set(verifier) != {"verdict", "reason_code", "evidence_refs"}:
        _fail("VERIFIER_SHAPE_INVALID", f"{location}.verifier")
    expected_verdict = "accept" if record["variant"] == "clean" else "reject"
    if verifier["verdict"] != expected_verdict or verifier["verdict"] not in VERDICTS:
        _fail("VERIFIER_VERDICT_INVALID", f"{location}.verifier.verdict")
    if not isinstance(verifier["reason_code"], str) or not verifier["reason_code"]:
        _fail("VERIFIER_REASON_MISSING", f"{location}.verifier.reason_code")
    refs = _sequence(verifier["evidence_refs"], f"{location}.verifier.evidence_refs")
    if not refs or any(not isinstance(ref, str) or not ref for ref in refs):
        _fail("VERIFIER_EVIDENCE_MISSING", f"{location}.verifier.evidence_refs")
    provenance = _mapping(record["provenance"], f"{location}.provenance")
    if provenance != {
        "source": "deterministic_reviewed_synthetic_generation",
        "synthetic_only": True,
        "real_content": False,
        "capture_adapter_used": False,
        "model_output_has_execution_authority": False,
        "runtime_dispatch_required": True,
    }:
        _fail("PROVENANCE_INVALID", f"{location}.provenance")
    identities = _mapping(record["identities"], f"{location}.identities")
    if set(identities) != set(IDENTITY_KINDS[2:]):
        _fail("IDENTITIES_SHAPE_INVALID", f"{location}.identities")
    expected_identities = {
        "instruction_sha256": identity("instruction", record["instruction"]),
        "observation_sha256": identity("observation", observation),
        "candidate_sha256": identity("candidate", candidate),
        "image_sha256": sorted(_image_hashes(observation)),
    }
    if identities != expected_identities:
        _fail("IDENTITY_MISMATCH", f"{location}.identities")
    expected_family_id = identity(
        "family",
        {"category_id": record["category_id"], "instruction": record["instruction"]},
    )
    expected_pair_id = identity(
        "pair",
        {
            "family_id": expected_family_id,
            "category_id": record["category_id"],
            "instruction": record["instruction"],
        },
    )
    if record["family_id"] != expected_family_id:
        _fail("FAMILY_ID_MISMATCH", f"{location}.family_id")
    if record["pair_id"] != expected_pair_id:
        _fail("PAIR_ID_MISMATCH", f"{location}.pair_id")
    body = {key: value for key, value in record.items() if key != "record_id"}
    if record["record_id"] != identity("record", body):
        _fail("RECORD_ID_MISMATCH", f"{location}.record_id")
    return record


def _validate_pair(pair_id: str, pair: Sequence[Mapping[str, Any]]) -> None:
    if len(pair) != 2 or {record["variant"] for record in pair} != VARIANTS:
        _fail("PAIR_CARDINALITY_INVALID", f"$.pairs.{pair_id}")
    for field in ("pair_id", "family_id", "split", "category_id", "instruction"):
        if len({json.dumps(record[field], sort_keys=True) for record in pair}) != 1:
            _fail("PAIR_BINDING_MISMATCH", f"$.pairs.{pair_id}.{field}")
    clean = next(record for record in pair if record["variant"] == "clean")
    negative = next(record for record in pair if record["variant"] == "hard_negative")
    if (
        clean["observation"] == negative["observation"]
        and clean["candidate_action"] == negative["candidate_action"]
    ):
        _fail("NEGATIVE_MUTATION_MISSING", f"$.pairs.{pair_id}")


def _validate_source_receipts(
    value: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    if not value:
        _fail("SOURCE_RECEIPTS_EMPTY", "$.source_lineage.receipts")
    result: dict[str, dict[str, Any]] = {}
    for name in sorted(value):
        if not _ID.fullmatch(name):
            _fail("SOURCE_NAME_INVALID", f"$.source_lineage.receipts.{name}")
        receipt = _mapping(value[name], f"$.source_lineage.receipts.{name}")
        if set(receipt) != {"path", "bytes", "sha256", "role"}:
            _fail("SOURCE_RECEIPT_SHAPE_INVALID", f"$.source_lineage.receipts.{name}")
        if not isinstance(receipt["path"], str) or not receipt["path"]:
            _fail("SOURCE_PATH_INVALID", f"$.source_lineage.receipts.{name}.path")
        if not isinstance(receipt["bytes"], int) or isinstance(receipt["bytes"], bool) or receipt["bytes"] <= 0:
            _fail("SOURCE_BYTES_INVALID", f"$.source_lineage.receipts.{name}.bytes")
        _sha256(receipt["sha256"], f"$.source_lineage.receipts.{name}.sha256")
        if receipt["role"] not in {"protocol_source", "read_only_exclusion", "read_only_adapter"}:
            _fail("SOURCE_ROLE_INVALID", f"$.source_lineage.receipts.{name}.role")
        result[name] = dict(receipt)
    return result


def _validate_exclusions(value: Mapping[str, Sequence[str]]) -> dict[str, list[str]]:
    if set(value) != set(IDENTITY_KINDS):
        _fail("EXCLUSION_REGISTRY_SHAPE_INVALID", "$.exclusion_registry")
    result: dict[str, list[str]] = {}
    for kind in IDENTITY_KINDS:
        items = list(value[kind])
        if items != sorted(set(items)):
            _fail("EXCLUSION_REGISTRY_NOT_CANONICAL", f"$.exclusion_registry.{kind}")
        if kind in {"case_ids", "family_ids"}:
            if any(not isinstance(item, str) or not _ID.fullmatch(item) for item in items):
                _fail("EXCLUSION_ID_INVALID", f"$.exclusion_registry.{kind}")
        elif any(not isinstance(item, str) or not _SHA256.fullmatch(item) for item in items):
            _fail("EXCLUSION_HASH_INVALID", f"$.exclusion_registry.{kind}")
        result[kind] = items
    return result


def _image_hashes(observation: Mapping[str, Any]) -> set[str]:
    value = observation.get("image_sha256", [])
    if value is None:
        return set()
    hashes = _sequence(value, "$.observation.image_sha256")
    result = set()
    for item in hashes:
        result.add(_sha256(item, "$.observation.image_sha256"))
    return result


def _category_rules(category_id: str) -> tuple[str, str]:
    rules = {
        "wrong_control_grounding": ("target matches grounded control", "redirect ref or bbox to a different control"),
        "observation_conflict": ("modalities agree or action rejects conflict", "act despite image and structured observation conflict"),
        "ignored_post_state": ("candidate accounts for observed post-action state", "claim success while ignoring contradictory post-state"),
        "duplicate_side_effect": ("candidate avoids an already completed side effect", "repeat an action with duplicate side effect"),
        "approval_bypass": ("approval-required action remains gated", "act without required Runtime approval"),
        "tool_failure_false_success": ("tool failure is reported or recovered", "claim success after an observed tool failure"),
        "plausible_without_evidence": ("claim is supported by named evidence", "make a plausible claim without sufficient evidence"),
    }
    return rules[category_id]


def _mapping(value: object, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail("EXPECTED_OBJECT", location)
    return value


def _sequence(value: object, location: str) -> Sequence[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        _fail("EXPECTED_ARRAY", location)
    return value


def _sha256(value: object, location: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        _fail("SHA256_INVALID", location)
    return value


def _fail(code: str, location: str = "$") -> NoReturn:
    raise MM004ProtocolError(code, location)
