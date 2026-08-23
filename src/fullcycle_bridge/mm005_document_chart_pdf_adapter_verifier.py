"""Model-free MM-005 Document/Chart/PDF Adapter and deterministic Verifier."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, NoReturn, cast

from . import multimodal_environment_adaptation as parent

IMPLEMENTATION_VERSION = 1
ADAPTER_VERSION = 1
COMPILER_VERSION = 1
VERIFIER_VERSION = 1

MODEL_PAYLOAD_KEYS = (
    "instruction",
    "observation",
    "source_kind",
    "task_family_id",
)
FORBIDDEN_MODEL_PAYLOAD_KEYS = frozenset(
    {
        "expected_output",
        "family_id",
        "identities",
        "provenance",
        "record_id",
        "split",
        "template_id",
        "verifier",
    }
)

_ID = re.compile(r"[a-z0-9][a-z0-9._-]{0,127}\Z")
_SHA256 = re.compile(r"sha256:[0-9a-f]{64}\Z")


class MM005AdapterVerifierError(ValueError):
    """Stable fail-closed error for Adapter or Verifier boundary violations."""

    def __init__(self, code: str, location: str = "$") -> None:
        self.code = code
        self.location = location
        super().__init__(f"{code} at {location}")


@dataclass(frozen=True)
class AdaptedInput:
    """Immutable separation between model-facing input and audit metadata."""

    implementation_version: int
    model_payload_json: bytes
    image_bytes: bytes
    audit_projection_json: bytes

    def model_payload(self) -> dict[str, Any]:
        return _json_dict(self.model_payload_json, "$.model_payload_json")

    def audit_projection(self) -> dict[str, Any]:
        return _json_dict(self.audit_projection_json, "$.audit_projection_json")


def artifact_json_bytes(value: object) -> bytes:
    try:
        return (
            json.dumps(
                value,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise MM005AdapterVerifierError("JSON_SERIALIZATION_INVALID") from exc


def sha256_bytes(payload: bytes) -> str:
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def adapt_record(
    record: Mapping[str, Any],
    image_payloads: Mapping[str, bytes],
) -> AdaptedInput:
    """Project one validated record without exposing gold or a real image path."""

    _validate_record(record, "$.record")
    observation = _mapping(record["observation"], "$.record.observation")
    image_sha256 = observation.get("image_sha256")
    if not isinstance(image_sha256, str) or not _SHA256.fullmatch(image_sha256):
        _fail("IMAGE_SHA256_INVALID", "$.record.observation.image_sha256")

    matching: list[tuple[dict[str, Any], bytes]] = []
    for path, payload in sorted(image_payloads.items()):
        _validate_relative_path(path, "$.image_payloads")
        if type(payload) is not bytes or not payload:
            _fail("IMAGE_PAYLOAD_INVALID", f"$.image_payloads.{path}")
        receipt = _receipt(path, payload)
        if receipt["sha256"] == image_sha256:
            matching.append((receipt, payload))
    if len(matching) != 1:
        _fail("RECORD_IMAGE_BINDING_INVALID", "$.record.observation.image_sha256")
    image_binding, image_bytes = matching[0]

    model_payload = {
        "instruction": record["instruction"],
        "observation": _json_copy(record["observation"]),
        "source_kind": record["source_kind"],
        "task_family_id": record["task_family_id"],
    }
    if tuple(sorted(model_payload)) != tuple(sorted(MODEL_PAYLOAD_KEYS)):
        _fail("MODEL_PAYLOAD_SHAPE_INVALID", "$.model_payload")
    if _contains_forbidden_key(model_payload):
        _fail("MODEL_PAYLOAD_GOLD_LEAKAGE", "$.model_payload")
    model_payload_json = artifact_json_bytes(model_payload)
    if image_binding["path"].encode("utf-8") in model_payload_json:
        _fail("MODEL_PAYLOAD_PATH_LEAKAGE", "$.model_payload")

    audit_projection = {
        "adapter_projection_version": ADAPTER_VERSION,
        "record_id": record["record_id"],
        "image_binding": image_binding,
        "model_payload": model_payload,
        "authority": {
            "model_output_has_execution_authority": False,
            "runtime_integration_authorized": False,
            "gold_or_verifier_fields_exposed_to_model": False,
            "real_file_path_exposed_to_model": False,
        },
    }
    return AdaptedInput(
        implementation_version=IMPLEMENTATION_VERSION,
        model_payload_json=model_payload_json,
        image_bytes=image_bytes,
        audit_projection_json=artifact_json_bytes(audit_projection),
    )


def projection_receipt(
    record: Mapping[str, Any], adapted: AdaptedInput
) -> dict[str, Any]:
    """Return the protocol-facing receipt for one independently adapted input."""

    _validate_record(record, "$.record")
    projection = adapted.audit_projection()
    image_binding = _mapping(projection.get("image_binding"), "$.image_binding")
    projection_payload = adapted.audit_projection_json
    if sha256_bytes(adapted.image_bytes) != image_binding.get("sha256"):
        _fail("ADAPTED_IMAGE_RECEIPT_MISMATCH", "$.image_binding")
    return {
        "record_id": record["record_id"],
        "split": record["split"],
        "task_family_id": record["task_family_id"],
        "source_kind": record["source_kind"],
        "image_sha256": image_binding["sha256"],
        "projection_bytes": len(projection_payload),
        "projection_sha256": sha256_bytes(projection_payload),
    }


def compile_candidate_output(raw_output: object) -> dict[str, Any]:
    """Compile the exact three-key JSON answer contract or return invalid."""

    invalid: dict[str, Any] = {
        "compiler_version": COMPILER_VERSION,
        "valid": False,
        "answer": "",
        "evidence_refs": [],
        "page_number": None,
        "error_code": "invalid_output",
    }
    if not isinstance(raw_output, str):
        return invalid
    try:
        if len(raw_output.encode("utf-8")) > 8_192:
            return invalid
    except UnicodeEncodeError:
        return invalid
    try:
        parsed = json.loads(
            raw_output,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (TypeError, ValueError, json.JSONDecodeError):
        return invalid
    if not isinstance(parsed, dict) or set(parsed) != {
        "answer",
        "evidence_refs",
        "page_number",
    }:
        return invalid
    answer = parsed.get("answer")
    refs = parsed.get("evidence_refs")
    page_number = parsed.get("page_number")
    if (
        type(answer) is not str
        or not answer
        or len(answer) > 512
        or not isinstance(refs, list)
        or not refs
        or len(refs) > 16
        or any(type(ref) is not str or not _ID.fullmatch(ref) for ref in refs)
        or len(set(refs)) != len(refs)
        or type(page_number) is not int
        or page_number != 1
    ):
        return invalid
    return {
        "compiler_version": COMPILER_VERSION,
        "valid": True,
        "answer": answer,
        "evidence_refs": list(refs),
        "page_number": page_number,
        "error_code": None,
    }


def verify_candidate(
    compiled: object,
    record: Mapping[str, Any],
) -> dict[str, Any]:
    """Score a compiled candidate with exact deterministic comparisons."""

    _validate_record(record, "$.record")
    expected = _mapping(record["expected_output"], "$.record.expected_output")
    candidate = compiled if isinstance(compiled, Mapping) else {}
    valid = _compiled_output_is_well_formed(candidate) and candidate["valid"] is True
    answer_exact = valid and _normalize_answer(str(candidate["answer"])) == (
        _normalize_answer(str(expected["answer"]))
    )
    evidence_exact = valid and candidate["evidence_refs"] == expected["evidence_refs"]
    page_exact = valid and candidate["page_number"] == expected["page_number"]
    return {
        "verifier_version": VERIFIER_VERSION,
        "valid_output": valid,
        "answer_exact": answer_exact,
        "evidence_exact": evidence_exact,
        "page_exact": page_exact,
        "joint_correct": answer_exact and evidence_exact and page_exact,
        "model_judge_used": False,
    }


def verify_raw_output(raw_output: object, record: Mapping[str, Any]) -> dict[str, Any]:
    return verify_candidate(compile_candidate_output(raw_output), record)


def _validate_record(record: Mapping[str, Any], location: str) -> None:
    try:
        parent.verify_candidate({}, record)
    except (KeyError, TypeError, parent.MM005ProtocolError) as exc:
        raise MM005AdapterVerifierError("RECORD_CONTRACT_INVALID", location) from exc


def _compiled_output_is_well_formed(value: Mapping[str, Any]) -> bool:
    if set(value) != {
        "compiler_version",
        "valid",
        "answer",
        "evidence_refs",
        "page_number",
        "error_code",
    }:
        return False
    if (
        type(value["compiler_version"]) is not int
        or value["compiler_version"] != COMPILER_VERSION
        or type(value["valid"]) is not bool
    ):
        return False
    if value["valid"] is False:
        return (
            value["answer"] == ""
            and value["evidence_refs"] == []
            and value["page_number"] is None
            and value["error_code"] == "invalid_output"
        )
    refs = value["evidence_refs"]
    return (
        type(value["answer"]) is str
        and bool(value["answer"])
        and len(value["answer"]) <= 512
        and isinstance(refs, list)
        and 0 < len(refs) <= 16
        and all(type(ref) is str and _ID.fullmatch(ref) for ref in refs)
        and len(set(refs)) == len(refs)
        and type(value["page_number"]) is int
        and value["page_number"] == 1
        and value["error_code"] is None
    )


def _contains_forbidden_key(value: object) -> bool:
    if isinstance(value, Mapping):
        return any(
            str(key) in FORBIDDEN_MODEL_PAYLOAD_KEYS or _contains_forbidden_key(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_forbidden_key(item) for item in value)
    return False


def _validate_relative_path(value: object, location: str) -> None:
    if (
        type(value) is not str
        or not value
        or "\\" in value
        or value.startswith("/")
        or any(part in {"", ".", ".."} for part in value.split("/"))
    ):
        _fail("IMAGE_PATH_INVALID", location)


def _normalize_answer(value: str) -> str:
    return unicodedata.normalize("NFC", value).strip(" ")


def _unique_object(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def _reject_constant(value: str) -> NoReturn:
    raise ValueError(f"invalid JSON constant: {value}")


def _json_copy(value: object) -> object:
    return json.loads(artifact_json_bytes(value))


def _json_dict(payload: bytes, location: str) -> dict[str, Any]:
    try:
        value = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MM005AdapterVerifierError("JSON_INVALID", location) from exc
    if not isinstance(value, dict) or artifact_json_bytes(value) != payload:
        _fail("JSON_NOT_CANONICAL_OBJECT", location)
    return cast(dict[str, Any], value)


def _mapping(value: object, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail("EXPECTED_OBJECT", location)
    return value


def _receipt(path: str, payload: bytes) -> dict[str, Any]:
    return {"path": path, "bytes": len(payload), "sha256": sha256_bytes(payload)}


def _fail(code: str, location: str = "$") -> NoReturn:
    raise MM005AdapterVerifierError(code, location)
