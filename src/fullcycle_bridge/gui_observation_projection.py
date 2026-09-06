"""Project bounded Runtime result text plus explicit Host facts, without IO."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, NoReturn

from .native_gui_proposal import validate_context


class ObservationProjectionError(ValueError):
    """Fixed errors never echo observations."""


def _fail(code: str) -> NoReturn:
    raise ObservationProjectionError(code)


def _obj(value: Any, keys: set[str], code: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != keys:
        _fail(code)
    return value


def _integer(value: Any, low: int, high: int, code: str) -> int:
    if type(value) is not int or not low <= value <= high:
        _fail(code)
    return value


def _pattern(value: Any, pattern: str, code: str) -> str:
    if type(value) is not str or not re.fullmatch(pattern, value):
        _fail(code)
    return value


def _text(value: Any, limit: int, code: str) -> str:
    if type(value) is not str or len(value) > limit:
        _fail(code)
    try:
        value.encode()
    except UnicodeError:
        _fail(code)
    return value


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
    except (ValueError, TypeError, UnicodeError, RecursionError):
        _fail("INVALID_JSON_VALUE")


def _snapshot(text: str) -> list[dict[str, Any]]:
    if text == "# (no interactive elements in scope)":
        return []
    lines = text.splitlines()
    if not lines or len(lines) > 64:
        _fail("SNAPSHOT_SIZE")
    if any(line.startswith("#") for line in lines):
        _fail("SNAPSHOT_INCOMPLETE")
    pattern = r'ref_([1-9][0-9]{0,9}) \| ([a-z]+) "([^"\r\n]*)" \| \((-?[0-9]{1,6}),(-?[0-9]{1,6}),([0-9]{1,6}),([0-9]{1,6})\) \| ([a-z,]+)(?: \| value="[^"\r\n]*")?'
    result = []
    refs = set()
    for line in lines:
        match = re.fullmatch(pattern, line)
        if match is None:
            _fail("SNAPSHOT_GRAMMAR")
        number, role, name, x, y, w, h, state_text = match.groups()
        ref = "ref_" + number
        if ref in refs:
            _fail("DUPLICATE_REF")
        refs.add(ref)
        if role not in {"button", "edit", "document"}:
            _fail("UNSUPPORTED_CONTROL_ROLE")
        if not name.strip() or len(name) >= 100 or any(ord(c) < 32 for c in name):
            _fail("CONTROL_NAME_INCOMPLETE")
        states = state_text.split(",")
        if (
            len(states) != len(set(states))
            or not set(states)
            <= {"enabled", "disabled", "focused", "selected", "offscreen"}
            or len(set(states) & {"enabled", "disabled"}) != 1
        ):
            _fail("CONTROL_STATES")
        xx, yy, ww, hh = (int(v) for v in (x, y, w, h))
        if not (
            -16384 <= xx <= 16384
            and -16384 <= yy <= 16384
            and 0 < ww <= 16384
            and 0 < hh <= 16384
        ):
            _fail("CONTROL_BOUNDS")
        result.append(
            dict(
                ref=ref,
                role=role,
                name=name,
                bounds=[xx, yy, xx + ww, yy + hh],
                reported_enabled="enabled" in states,
                reported_offscreen="offscreen" in states,
            )
        )
    return result


def _windows(text: str, scope: str) -> str:
    lines = text.splitlines()
    if not lines or len(lines) > 128:
        _fail("WINDOW_LIST_SIZE")
    ids = set()
    foreground = []
    for line in lines:
        match = re.fullmatch(
            r'([ *]) ([1-9][0-9]{0,19}) \| [^|"\r\n]+ \| "[^"\r\n]*"', line
        )
        if match is None:
            _fail("WINDOW_LIST_GRAMMAR")
        marker, identity = match.groups()
        if identity in ids:
            _fail("DUPLICATE_WINDOW")
        ids.add(identity)
        if marker == "*":
            foreground.append(identity)
    if scope not in ids or len(foreground) != 1:
        _fail("WINDOW_FACTS_INCOMPLETE")
    return foreground[0]


def inspect_observations(task: Any, results: Any, image: bytes) -> dict[str, Any]:
    """Extract reported facts; no claim that the three calls were coherent."""
    task = _obj(
        task,
        {
            "version",
            "request_id",
            "target_scope",
            "current_epoch",
            "runtime_generation",
            "target",
        },
        "TASK_FIELDS",
    )
    _integer(task["version"], 1, 1, "VERSION")
    _pattern(task["request_id"], r"[a-z0-9][a-z0-9_-]{0,63}", "REQUEST_ID")
    scope = _pattern(task["target_scope"], r"[1-9][0-9]{0,19}", "WINDOW_ID")
    epoch = _integer(task["current_epoch"], 0, 2**31 - 1, "EPOCH")
    generation = _integer(task["runtime_generation"], 0, 2**31 - 1, "GENERATION")
    target = _obj(task["target"], {"name", "role"}, "TARGET_FIELDS")
    name = _text(target["name"], 160, "TARGET_NAME")
    if (
        not name.strip()
        or any(ord(c) < 32 for c in name)
        or type(target["role"]) is not str
        or target["role"] not in {"button", "edit", "document"}
    ):
        _fail("TARGET_INVALID")
    results = _obj(results, {"windows", "snapshot", "screenshot"}, "RESULT_SET")
    stamps, identities = [], set()
    for key, tool, arguments in [
        ("windows", "list_windows", {}),
        ("snapshot", "ui_snapshot", {"scope": scope}),
        ("screenshot", "screenshot", {}),
    ]:
        row = _obj(
            results[key],
            {
                "call_id",
                "tool",
                "status",
                "dispatch",
                "generation",
                "epoch",
                "arguments",
                "text",
            },
            "RESULT_FIELDS",
        )
        identity = _pattern(row["call_id"], r"[a-z0-9][a-z0-9_-]{0,63}", "CALL_ID")
        if identity in identities:
            _fail("DUPLICATE_CALL")
        identities.add(identity)
        if (
            row["tool"] != tool
            or row["arguments"] != arguments
            or type(row["arguments"]) is not dict
        ):
            _fail("OBSERVATION_CALL_MISMATCH")
        if row["status"] != "success" or row["dispatch"] != "dispatched":
            _fail("OBSERVATION_NOT_SUCCESSFUL")
        if _integer(row["generation"], 0, 2**31 - 1, "GENERATION") != generation:
            _fail("MIXED_GENERATION")
        stamps.append(_integer(row["epoch"], 0, epoch, "RESULT_EPOCH"))
        _text(row["text"], 32768, "RESULT_TEXT")
    if not stamps[0] < stamps[1] < stamps[2] == epoch:
        _fail("OBSERVATION_SEQUENCE")
    if (
        type(image) is not bytes
        or not 24 <= len(image) <= 16 * 1024 * 1024
        or image[:8] != b"\x89PNG\r\n\x1a\n"
        or image[12:16] != b"IHDR"
    ):
        _fail("IMAGE_HEADER")
    width, height = (
        int.from_bytes(image[16:20], "big"),
        int.from_bytes(image[20:24], "big"),
    )
    _integer(width, 1, 16384, "IMAGE_SIZE")
    _integer(height, 1, 16384, "IMAGE_SIZE")
    encoded = _canonical(
        dict(task=task, results=results, image_sha256=hashlib.sha256(image).hexdigest())
    )
    if len(encoded) > 65536:
        _fail("OBSERVATION_TOO_LARGE")
    return dict(
        binding_digest=hashlib.sha256(
            b"gui-observation-projection-v1\0" + encoded
        ).hexdigest(),
        foreground_scope=_windows(results["windows"]["text"], scope),
        controls=_snapshot(results["snapshot"]["text"]),
        frame=dict(
            sha256=hashlib.sha256(image).hexdigest(), width=width, height=height
        ),
    )


def project_observation(
    task: Any, results: Any, image: bytes, host_facts: Any = None
) -> dict[str, Any]:
    """Incomplete legacy observations cannot synthesize a native action context."""
    inspected = inspect_observations(task, results, image)
    missing = [
        "window_bounds",
        "primary_frame_origin",
        "coherent_complete_projection",
        "verified_control_states",
    ]
    if host_facts is None:
        return dict(
            status="incomplete",
            missing=missing,
            reported=inspected,
            context=None,
            execution_authorized=False,
        )
    facts = _obj(
        host_facts,
        {
            "binding_digest",
            "window_bounds",
            "frame_origin",
            "coherent_complete_projection",
            "control_states",
        },
        "HOST_FACT_FIELDS",
    )
    if (
        type(facts["binding_digest"]) is not str
        or facts["binding_digest"] != inspected["binding_digest"]
    ):
        _fail("HOST_FACT_BINDING_MISMATCH")
    origin = facts["frame_origin"]
    if (
        type(origin) is not list
        or len(origin) != 2
        or any(type(v) is not int for v in origin)
        or origin != [0, 0]
    ):
        _fail("UNSUPPORTED_FRAME_ORIGIN")
    if facts["coherent_complete_projection"] is not True:
        _fail("OBSERVATIONS_NOT_COHERENT")
    states = facts["control_states"]
    if type(states) is not dict or set(states) != {
        c["ref"] for c in inspected["controls"]
    }:
        _fail("CONTROL_FACT_SET")
    controls = []
    for control in inspected["controls"]:
        state = _obj(
            states[control["ref"]], {"enabled", "visible"}, "CONTROL_FACT_FIELDS"
        )
        if type(state["enabled"]) is not bool or type(state["visible"]) is not bool:
            _fail("CONTROL_FACT_TYPES")
        if state["enabled"] != control["reported_enabled"] or (
            control["reported_offscreen"] and state["visible"]
        ):
            _fail("CONTROL_FACT_CONFLICT")
        controls.append(
            {k: control[k] for k in ["ref", "role", "name", "bounds"]} | state
        )
    context = validate_context(
        dict(
            task,
            observation=dict(
                scope=task["target_scope"],
                epoch=task["current_epoch"],
                foreground_scope=inspected["foreground_scope"],
                frame=inspected["frame"]
                | {"coordinate_space": "primary_screen_pixels"},
                window_bounds=facts["window_bounds"],
                controls=controls,
            ),
        )
    )
    return dict(
        status="projected",
        missing=[],
        reported=inspected,
        context=context,
        execution_authorized=False,
    )
