"""Model-free MM-005 Browser Research Adapter and deterministic Verifier."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, NoReturn, cast

from . import browser_research_environment_adaptation as parent

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
        "path",
        "provenance",
        "record_id",
        "screenshot_path",
        "source_snapshot_identity_sha256",
        "source_snapshot_path",
        "source_url_identity_sha256",
        "split",
        "template_id",
        "verifier",
    }
)

_SNAPSHOT_KEYS = frozenset(
    {
        "dataset_id",
        "gate_id",
        "mm005_browser_research_source_snapshot_version",
        "screenshot_path",
        "source",
        "source_kind",
        "source_snapshot_identity_sha256",
        "source_url_identity_sha256",
        "split",
        "task_family_id",
        "template_id",
    }
)
_ID = re.compile(r"[a-z0-9][a-z0-9._-]{0,127}\Z")
_SHA256 = re.compile(r"sha256:[0-9a-f]{64}\Z")


class MM005BrowserResearchAdapterVerifierError(ValueError):
    """Stable fail-closed error for Adapter or Verifier boundary violations."""

    def __init__(self, code: str, location: str = "$") -> None:
        self.code = code
        self.location = location
        super().__init__(f"{code} at {location}")


@dataclass(frozen=True)
class AdaptedBrowserResearchInput:
    """Immutable separation between model-facing inputs and audit metadata."""

    implementation_version: int
    model_payload_json: bytes
    screenshot_payloads: tuple[bytes, ...]
    source_snapshot_payloads: tuple[bytes, ...]
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
        raise MM005BrowserResearchAdapterVerifierError(
            "JSON_SERIALIZATION_INVALID"
        ) from exc


def sha256_bytes(payload: bytes) -> str:
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def adapt_record(
    record: Mapping[str, Any],
    screenshot_payloads: Mapping[str, bytes],
    source_snapshot_payloads: Mapping[str, bytes],
) -> AdaptedBrowserResearchInput:
    """Project one validated record without exposing gold or artifact paths."""

    _validate_record(record, "$.record")
    screenshots = _screenshot_registry(screenshot_payloads)
    snapshots = _snapshot_registry(source_snapshot_payloads, screenshot_payloads)
    observation = _mapping(record["observation"], "$.record.observation")
    sources = _sequence(observation.get("sources"), "$.record.observation.sources")

    bindings: list[dict[str, Any]] = []
    selected_screenshots: list[bytes] = []
    selected_snapshots: list[bytes] = []
    for index, raw_source in enumerate(sources):
        source = _mapping(raw_source, f"$.record.observation.sources[{index}]")
        source_id = str(source["source_id"])
        screenshot_matches = [
            item
            for item in screenshots
            if item[2]["sha256"] == source.get("screenshot_sha256")
        ]
        if len(screenshot_matches) != 1:
            _fail(
                "RECORD_SCREENSHOT_BINDING_INVALID",
                f"$.record.observation.sources[{index}].screenshot_sha256",
            )
        screenshot_path, screenshot_bytes, screenshot_receipt = screenshot_matches[0]

        snapshot_matches = [
            item for item in snapshots if item[2].get("source", {}).get("source_id") == source_id
        ]
        if len(snapshot_matches) != 1:
            _fail(
                "RECORD_SOURCE_SNAPSHOT_BINDING_INVALID",
                f"$.record.observation.sources[{index}]",
            )
        snapshot_path, snapshot_bytes, snapshot = snapshot_matches[0]
        _validate_selected_snapshot(
            snapshot,
            record=record,
            source=source,
            screenshot_path=screenshot_path,
            location=f"$.source_snapshot_payloads.{snapshot_path}",
        )
        bindings.append(
            {
                "source_id": source_id,
                "screenshot": screenshot_receipt,
                "source_snapshot": _receipt(snapshot_path, snapshot_bytes),
            }
        )
        selected_screenshots.append(screenshot_bytes)
        selected_snapshots.append(snapshot_bytes)

    model_payload = {
        "instruction": record["instruction"],
        "observation": _json_copy(record["observation"]),
        "source_kind": record["source_kind"],
        "task_family_id": record["task_family_id"],
    }
    if set(model_payload) != set(MODEL_PAYLOAD_KEYS):
        _fail("MODEL_PAYLOAD_SHAPE_INVALID", "$.model_payload")
    if _contains_forbidden_key(model_payload):
        _fail("MODEL_PAYLOAD_GOLD_LEAKAGE", "$.model_payload")
    model_payload_json = artifact_json_bytes(model_payload)
    for binding in bindings:
        for receipt_kind in ("screenshot", "source_snapshot"):
            path = str(_mapping(binding[receipt_kind], "$.binding")["path"])
            if path.encode("utf-8") in model_payload_json:
                _fail("MODEL_PAYLOAD_PATH_LEAKAGE", "$.model_payload")

    audit_projection = {
        "adapter_projection_version": ADAPTER_VERSION,
        "record_id": record["record_id"],
        "source_bindings": bindings,
        "model_payload": model_payload,
        "authority": {
            "page_content_has_execution_authority": False,
            "model_output_has_execution_authority": False,
            "runtime_integration_authorized": False,
            "gold_or_verifier_fields_exposed_to_model": False,
            "artifact_paths_exposed_to_model": False,
        },
    }
    return AdaptedBrowserResearchInput(
        implementation_version=IMPLEMENTATION_VERSION,
        model_payload_json=model_payload_json,
        screenshot_payloads=tuple(selected_screenshots),
        source_snapshot_payloads=tuple(selected_snapshots),
        audit_projection_json=artifact_json_bytes(audit_projection),
    )


def projection_receipt(
    record: Mapping[str, Any], adapted: AdaptedBrowserResearchInput
) -> dict[str, Any]:
    """Return the protocol-facing receipt for one independently adapted input."""

    _validate_record(record, "$.record")
    projection = adapted.audit_projection()
    bindings = _sequence(projection.get("source_bindings"), "$.source_bindings")
    if (
        len(bindings) != len(adapted.screenshot_payloads)
        or len(bindings) != len(adapted.source_snapshot_payloads)
    ):
        _fail("ADAPTED_SOURCE_COUNT_INVALID", "$.source_bindings")

    screenshot_sha256: list[str] = []
    source_snapshot_sha256: list[str] = []
    for index, raw_binding in enumerate(bindings):
        binding = _mapping(raw_binding, f"$.source_bindings[{index}]")
        screenshot = _mapping(binding.get("screenshot"), f"$.source_bindings[{index}]")
        snapshot = _mapping(
            binding.get("source_snapshot"), f"$.source_bindings[{index}]"
        )
        if sha256_bytes(adapted.screenshot_payloads[index]) != screenshot.get("sha256"):
            _fail("ADAPTED_SCREENSHOT_RECEIPT_MISMATCH", f"$.source_bindings[{index}]")
        if (
            sha256_bytes(adapted.source_snapshot_payloads[index])
            != snapshot.get("sha256")
        ):
            _fail(
                "ADAPTED_SOURCE_SNAPSHOT_RECEIPT_MISMATCH",
                f"$.source_bindings[{index}]",
            )
        screenshot_sha256.append(str(screenshot["sha256"]))
        source_snapshot_sha256.append(str(snapshot["sha256"]))

    projection_payload = adapted.audit_projection_json
    return {
        "record_id": record["record_id"],
        "split": record["split"],
        "task_family_id": record["task_family_id"],
        "source_kind": record["source_kind"],
        "source_count": len(bindings),
        "screenshot_sha256": screenshot_sha256,
        "source_snapshot_sha256": source_snapshot_sha256,
        "projection_bytes": len(projection_payload),
        "projection_sha256": sha256_bytes(projection_payload),
    }


def compile_candidate_output(raw_output: object) -> dict[str, Any]:
    """Compile the exact two-key Browser answer contract or return invalid."""

    invalid: dict[str, Any] = {
        "compiler_version": COMPILER_VERSION,
        "valid": False,
        "answer": "",
        "citation_refs": [],
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
    if not isinstance(parsed, dict) or set(parsed) != {"answer", "citation_refs"}:
        return invalid
    answer = parsed.get("answer")
    refs = parsed.get("citation_refs")
    if (
        type(answer) is not str
        or not answer
        or len(answer) > 1_024
        or not isinstance(refs, list)
        or not refs
        or len(refs) > 12
        or any(type(ref) is not str or not _ID.fullmatch(ref) for ref in refs)
        or len(set(refs)) != len(refs)
    ):
        return invalid
    return {
        "compiler_version": COMPILER_VERSION,
        "valid": True,
        "answer": answer,
        "citation_refs": list(refs),
        "error_code": None,
    }


def verify_candidate(compiled: object, record: Mapping[str, Any]) -> dict[str, Any]:
    """Score a compiled candidate with exact deterministic comparisons."""

    _validate_record(record, "$.record")
    expected = _mapping(record["expected_output"], "$.record.expected_output")
    candidate = compiled if isinstance(compiled, Mapping) else {}
    valid = _compiled_output_is_well_formed(candidate) and candidate["valid"] is True
    answer_exact = valid and _normalize_answer(str(candidate["answer"])) == (
        _normalize_answer(str(expected["answer"]))
    )
    citation_exact = valid and candidate["citation_refs"] == expected["citation_refs"]
    return {
        "verifier_version": VERIFIER_VERSION,
        "valid_output": valid,
        "answer_exact": answer_exact,
        "citation_exact": citation_exact,
        "joint_correct": answer_exact and citation_exact,
        "model_judge_used": False,
    }


def verify_raw_output(raw_output: object, record: Mapping[str, Any]) -> dict[str, Any]:
    return verify_candidate(compile_candidate_output(raw_output), record)


def citation_semantics(
    compiled: object, record: Mapping[str, Any]
) -> dict[str, Any]:
    """Independently derive source binding, coverage, and freshness diagnostics."""

    _validate_record(record, "$.record")
    candidate = compiled if isinstance(compiled, Mapping) else {}
    valid = _compiled_output_is_well_formed(candidate) and candidate.get("valid") is True
    refs = candidate.get("citation_refs") if valid else []
    checked_refs = refs if isinstance(refs, list) else []
    observation = _mapping(record["observation"], "$.record.observation")
    ref_to_source = _observed_ref_to_source(observation)
    all_bound = valid and bool(checked_refs) and all(
        isinstance(ref, str) and ref in ref_to_source for ref in checked_refs
    )
    cited_sources: list[str] = []
    if all_bound:
        for ref in checked_refs:
            source_id = ref_to_source[str(ref)]
            if source_id not in cited_sources:
                cited_sources.append(source_id)
    minimum = 1 if record["task_family_id"] == "single_source_fact_citation" else 2
    minimum_coverage = all_bound and len(cited_sources) >= minimum
    latest_source_cited: bool | None = None
    if record["task_family_id"] == "freshness_conflict_resolution":
        published = _source_published_at(observation)
        latest = max(published.values())
        latest_ids = {
            source_id for source_id, timestamp in published.items() if timestamp == latest
        }
        latest_source_cited = all_bound and bool(set(cited_sources) & latest_ids)
    return {
        "all_citation_refs_bound": all_bound,
        "cited_source_ids": cited_sources,
        "minimum_source_coverage_met": minimum_coverage,
        "latest_source_cited": latest_source_cited,
    }


def _screenshot_registry(
    values: Mapping[str, bytes],
) -> list[tuple[str, bytes, dict[str, Any]]]:
    if not values:
        _fail("SCREENSHOT_PAYLOADS_EMPTY", "$.screenshot_payloads")
    result: list[tuple[str, bytes, dict[str, Any]]] = []
    for path, payload in sorted(values.items()):
        _validate_relative_path(path, ".png", "$.screenshot_payloads")
        if type(payload) is not bytes or not payload:
            _fail("SCREENSHOT_PAYLOAD_INVALID", f"$.screenshot_payloads.{path}")
        result.append((path, payload, _receipt(path, payload)))
    return result


def _snapshot_registry(
    values: Mapping[str, bytes], screenshot_payloads: Mapping[str, bytes]
) -> list[tuple[str, bytes, dict[str, Any]]]:
    if not values:
        _fail("SOURCE_SNAPSHOT_PAYLOADS_EMPTY", "$.source_snapshot_payloads")
    result: list[tuple[str, bytes, dict[str, Any]]] = []
    for path, payload in sorted(values.items()):
        _validate_relative_path(path, ".json", "$.source_snapshot_payloads")
        if type(payload) is not bytes or not payload:
            _fail("SOURCE_SNAPSHOT_PAYLOAD_INVALID", f"$.source_snapshot_payloads.{path}")
        snapshot = _json_dict(payload, f"$.source_snapshot_payloads.{path}")
        if set(snapshot) != _SNAPSHOT_KEYS:
            _fail("SOURCE_SNAPSHOT_KEYS_INVALID", f"$.source_snapshot_payloads.{path}")
        screenshot_path = snapshot.get("screenshot_path")
        _validate_relative_path(
            screenshot_path, ".png", f"$.source_snapshot_payloads.{path}.screenshot_path"
        )
        if screenshot_path not in screenshot_payloads:
            _fail(
                "SOURCE_SNAPSHOT_SCREENSHOT_MISSING",
                f"$.source_snapshot_payloads.{path}.screenshot_path",
            )
        source = snapshot.get("source")
        if not isinstance(source, Mapping) or not isinstance(source.get("source_id"), str):
            _fail("SOURCE_SNAPSHOT_SOURCE_INVALID", f"$.source_snapshot_payloads.{path}")
        result.append((path, payload, snapshot))
    return result


def _validate_selected_snapshot(
    snapshot: Mapping[str, Any],
    *,
    record: Mapping[str, Any],
    source: Mapping[str, Any],
    screenshot_path: str,
    location: str,
) -> None:
    expected = {
        "dataset_id": "mm005-browser-research-v1",
        "gate_id": "MM-005-browser-research-data-generation-v1",
        "mm005_browser_research_source_snapshot_version": 1,
        "screenshot_path": screenshot_path,
        "source": source,
        "source_kind": record["source_kind"],
        "source_snapshot_identity_sha256": parent.browser_identity(
            "source_snapshot", source
        ),
        "source_url_identity_sha256": parent.browser_identity("source_url", source["url"]),
        "split": record["split"],
        "task_family_id": record["task_family_id"],
        "template_id": record["template_id"],
    }
    if snapshot != expected:
        _fail("SOURCE_SNAPSHOT_RECORD_MISMATCH", location)


def _validate_record(record: Mapping[str, Any], location: str) -> None:
    try:
        parent.verify_candidate({}, record)
    except (KeyError, TypeError, parent.MM005BrowserResearchProtocolError) as exc:
        raise MM005BrowserResearchAdapterVerifierError(
            "RECORD_CONTRACT_INVALID", location
        ) from exc


def _compiled_output_is_well_formed(value: Mapping[str, Any]) -> bool:
    if set(value) != {
        "compiler_version",
        "valid",
        "answer",
        "citation_refs",
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
        return bool(
            value["answer"] == ""
            and value["citation_refs"] == []
            and value["error_code"] == "invalid_output"
        )
    refs = value["citation_refs"]
    return (
        type(value["answer"]) is str
        and bool(value["answer"])
        and len(value["answer"]) <= 1_024
        and isinstance(refs, list)
        and 0 < len(refs) <= 12
        and all(type(ref) is str and _ID.fullmatch(ref) for ref in refs)
        and len(set(refs)) == len(refs)
        and value["error_code"] is None
    )


def _observed_ref_to_source(observation: Mapping[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw_source in _sequence(observation.get("sources"), "$.observation.sources"):
        source = _mapping(raw_source, "$.observation.sources[]")
        source_id = str(source["source_id"])
        for raw_node in _sequence(source.get("dom_nodes"), "$.source.dom_nodes"):
            node = _mapping(raw_node, "$.source.dom_nodes[]")
            ref = str(node["ref"])
            if ref in result:
                _fail("DUPLICATE_OBSERVED_REF", "$.observation.sources")
            result[ref] = source_id
    return result


def _source_published_at(observation: Mapping[str, Any]) -> dict[str, datetime]:
    result: dict[str, datetime] = {}
    for raw_source in _sequence(observation.get("sources"), "$.observation.sources"):
        source = _mapping(raw_source, "$.observation.sources[]")
        try:
            timestamp = datetime.strptime(
                str(source["published_at"]), "%Y-%m-%dT%H:%M:%SZ"
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise MM005BrowserResearchAdapterVerifierError(
                "SOURCE_PUBLISHED_AT_INVALID", "$.observation.sources"
            ) from exc
        result[str(source["source_id"])] = timestamp
    return result


def _contains_forbidden_key(value: object) -> bool:
    if isinstance(value, Mapping):
        return any(
            str(key) in FORBIDDEN_MODEL_PAYLOAD_KEYS or _contains_forbidden_key(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_forbidden_key(item) for item in value)
    return False


def _validate_relative_path(value: object, suffix: str, location: str) -> None:
    if (
        type(value) is not str
        or not value
        or "\\" in value
        or ":" in value
        or "\x00" in value
        or value.startswith("/")
        or not value.endswith(suffix)
        or any(part in {"", ".", ".."} for part in value.split("/"))
    ):
        _fail("ARTIFACT_PATH_INVALID", location)


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
        raise MM005BrowserResearchAdapterVerifierError("JSON_INVALID", location) from exc
    if not isinstance(value, dict) or artifact_json_bytes(value) != payload:
        _fail("JSON_NOT_CANONICAL_OBJECT", location)
    return cast(dict[str, Any], value)


def _mapping(value: object, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail("EXPECTED_OBJECT", location)
    return value


def _sequence(value: object, location: str) -> Sequence[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        _fail("EXPECTED_ARRAY", location)
    return value


def _receipt(path: str, payload: bytes) -> dict[str, Any]:
    return {"path": path, "bytes": len(payload), "sha256": sha256_bytes(payload)}


def _fail(code: str, location: str = "$") -> NoReturn:
    raise MM005BrowserResearchAdapterVerifierError(code, location)
