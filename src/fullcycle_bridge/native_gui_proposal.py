"""Offline native click/stop adapter; caller snapshots are not desktop authority."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, DecimalException
from fractions import Fraction
import hashlib
import json
import re
from typing import Any, NoReturn


class NativeProposalError(ValueError):
    """Fixed content-free rejection code."""


def _fail(code: str) -> NoReturn:
    raise NativeProposalError(code)


def _object(value: Any, keys: set[str], code: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != keys:
        _fail(code)
    return value


def _integer(value: Any, low: int, high: int, code: str) -> int:
    if type(value) is not int or not low <= value <= high:
        _fail(code)
    return value


def _text(value: Any, limit: int, code: str) -> str:
    if type(value) is not str or not value.strip() or len(value) > limit:
        _fail(code)
    if any(ord(c) < 32 for c in value):
        _fail(code)
    try:
        value.encode("utf-8")
    except UnicodeError:
        _fail(code)
    return value


def _pattern(value: Any, pattern: str, code: str) -> str:
    if type(value) is not str or not re.fullmatch(pattern, value):
        _fail(code)
    return value


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
    except (TypeError, ValueError, UnicodeError, RecursionError):
        _fail("INVALID_JSON_VALUE")


def _json_types(value: Any) -> None:
    if value is None or type(value) in {str, int, bool}:
        return
    if type(value) is list:
        for item in value:
            _json_types(item)
    elif type(value) is dict and all(type(k) is str for k in value):
        for item in value.values():
            _json_types(item)
    else:
        _fail("INVALID_JSON_VALUE")


def _bounds(value: Any, width: int, height: int) -> list[int]:
    if type(value) is not list or len(value) != 4:
        _fail("INVALID_BOUNDS")
    left, top, right, bottom = value
    _integer(left, 0, width - 1, "INVALID_BOUNDS")
    _integer(top, 0, height - 1, "INVALID_BOUNDS")
    _integer(right, left + 1, width, "INVALID_BOUNDS")
    _integer(bottom, top + 1, height, "INVALID_BOUNDS")
    return value


def validate_context(value: Any) -> dict[str, Any]:
    """Detach one full-primary-screen snapshot; never obtain or authenticate it."""
    try:
        _json_types(value)
    except RecursionError:
        _fail("INVALID_JSON_VALUE")
    encoded = _canonical(value)
    if len(encoded) > 65536:
        _fail("CONTEXT_TOO_LARGE")
    context = _object(
        json.loads(encoded),
        {
            "version",
            "request_id",
            "target_scope",
            "current_epoch",
            "runtime_generation",
            "target",
            "observation",
        },
        "CONTEXT_FIELDS",
    )
    _integer(context["version"], 1, 1, "VERSION")
    _pattern(context["request_id"], r"[a-z0-9][a-z0-9_-]{0,63}", "REQUEST_ID")
    scope = _pattern(context["target_scope"], r"[1-9][0-9]{0,19}", "WINDOW_ID")
    epoch = _integer(context["current_epoch"], 0, 2**31 - 1, "EPOCH")
    _integer(context["runtime_generation"], 0, 2**31 - 1, "GENERATION")
    target = _object(context["target"], {"name", "role"}, "TARGET_FIELDS")
    _text(target["name"], 160, "TARGET_NAME")
    roles = {"button", "edit", "document"}
    if type(target["role"]) is not str or target["role"] not in roles:
        _fail("TARGET_ROLE")
    obs = _object(
        context["observation"],
        {"scope", "epoch", "foreground_scope", "frame", "window_bounds", "controls"},
        "OBSERVATION_FIELDS",
    )
    if obs["scope"] != scope:
        _fail("OBSERVATION_SCOPE")
    _integer(obs["epoch"], 0, epoch, "OBSERVATION_EPOCH")
    if obs["foreground_scope"] is not None:
        _pattern(obs["foreground_scope"], r"[1-9][0-9]{0,19}", "FOREGROUND_SCOPE")
    frame = _object(
        obs["frame"], {"sha256", "width", "height", "coordinate_space"}, "FRAME_FIELDS"
    )
    _pattern(frame["sha256"], r"[a-f0-9]{64}", "FRAME_DIGEST")
    width = _integer(frame["width"], 1, 16384, "FRAME_SIZE")
    height = _integer(frame["height"], 1, 16384, "FRAME_SIZE")
    if frame["coordinate_space"] != "primary_screen_pixels":
        _fail("COORDINATE_SPACE")
    window = _bounds(obs["window_bounds"], width, height)
    if type(obs["controls"]) is not list or len(obs["controls"]) > 64:
        _fail("CONTROLS")
    refs = set()
    for control in obs["controls"]:
        _object(
            control,
            {"ref", "name", "role", "enabled", "visible", "bounds"},
            "CONTROL_FIELDS",
        )
        ref = _pattern(control["ref"], r"ref_[1-9][0-9]{0,9}", "CONTROL_REF")
        if ref in refs:
            _fail("DUPLICATE_REF")
        refs.add(ref)
        _text(control["name"], 160, "CONTROL_NAME")
        if type(control["role"]) is not str or control["role"] not in roles:
            _fail("CONTROL_ROLE")
        if type(control["enabled"]) is not bool or type(control["visible"]) is not bool:
            _fail("CONTROL_STATE")
        box = _bounds(control["bounds"], width, height)
        if not (
            window[0] <= box[0] < box[2] <= window[2]
            and window[1] <= box[1] < box[3] <= window[3]
        ):
            _fail("CONTROL_OUTSIDE_WINDOW")
    return context


def context_digest(context: Any) -> str:
    return hashlib.sha256(
        b"native-gui-proposal-v1\0" + _canonical(validate_context(context))
    ).hexdigest()


def parse_native(raw: Any) -> tuple[Fraction, Fraction] | None:
    """Accept exactly a native left-click or failure stop; never success claims."""
    if type(raw) is not str:
        _fail("RESPONSE_NOT_TEXT")
    try:
        if len(raw.encode()) > 4096:
            _fail("RESPONSE_TOO_LARGE")
    except UnicodeError:
        _fail("RESPONSE_NOT_UTF8")
    match = re.fullmatch(r"\s*<tool_call>\s*(.*?)\s*</tool_call>\s*", raw, re.DOTALL)
    if match is None:
        _fail("NATIVE_ENVELOPE")

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result = {}
        for key, item in items:
            if key in result:
                _fail("DUPLICATE_JSON_KEY")
            result[key] = item
        return result

    def constant(unused: str) -> NoReturn:
        _fail("NONFINITE_NUMBER")

    def decimal(text: str) -> Decimal:
        try:
            value = Decimal(text)
        except DecimalException:
            _fail("NATIVE_POINT_PRECISION")
        exponent = value.as_tuple().exponent
        if not isinstance(exponent, int) or not -12 <= exponent <= 3:
            _fail("NATIVE_POINT_PRECISION")
        return value

    try:
        value = json.loads(
            match.group(1),
            object_pairs_hook=pairs,
            parse_float=decimal,
            parse_constant=constant,
        )
    except NativeProposalError:
        raise
    except (ValueError, RecursionError):
        _fail("NATIVE_JSON")
    value = _object(value, {"name", "arguments"}, "NATIVE_FIELDS")
    if value["name"] != "computer_use":
        _fail("NATIVE_TOOL")
    args = value["arguments"]
    if args == {"action": "terminate", "status": "failure"}:
        return None
    args = _object(args, {"action", "coordinate"}, "NATIVE_ACTION_FIELDS")
    if args["action"] != "left_click":
        _fail("NATIVE_ACTION")
    point = args["coordinate"]
    if type(point) is not list or len(point) != 2:
        _fail("NATIVE_POINT")
    for component in point:
        if type(component) not in {int, Decimal} or not 0 <= component < 1000:
            _fail("NATIVE_POINT_RANGE")
    return Fraction(point[0]), Fraction(point[1])


@dataclass(frozen=True)
class NativeProposal:
    request_id: str
    binding_digest: str
    target_scope: str
    observation_epoch: int
    runtime_generation: int
    frame_sha256: str
    ref: str | None
    pixel_point: tuple[int, int] | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "request_id": self.request_id,
            "binding_digest": self.binding_digest,
            "target_scope": self.target_scope,
            "observation_epoch": self.observation_epoch,
            "runtime_generation": self.runtime_generation,
            "frame_sha256": self.frame_sha256,
            "action": "stop" if self.ref is None else "click_ref",
            "tool": None if self.ref is None else "click",
            "arguments": {} if self.ref is None else {"ref": self.ref},
            "pixel_point": list(self.pixel_point)
            if self.pixel_point is not None
            else None,
            "execution_authorized": False,
        }


def compile_native_response(issued: Any, current: Any, reply: Any) -> NativeProposal:
    """Bind a caller-correlated response; produce no executable capability."""
    context = validate_context(issued)
    binding = context_digest(context)
    if context_digest(current) != binding:
        _fail("CONTEXT_CHANGED")
    response = _object(
        reply, {"request_id", "context_digest", "raw_output"}, "REPLY_FIELDS"
    )
    if (
        type(response["request_id"]) is not str
        or type(response["context_digest"]) is not str
    ):
        _fail("REPLY_FIELDS")
    if (
        response["request_id"] != context["request_id"]
        or response["context_digest"] != binding
    ):
        _fail("REPLY_BINDING_MISMATCH")
    point = parse_native(response["raw_output"])
    obs = context["observation"]
    ref = None
    pixel = None
    if point is not None:
        if obs["epoch"] != context["current_epoch"]:
            _fail("STALE_OBSERVATION")
        if obs["foreground_scope"] != context["target_scope"]:
            _fail("TARGET_NOT_FOREGROUND")
        pixel = (
            int(point[0] * obs["frame"]["width"] // 1000),
            int(point[1] * obs["frame"]["height"] // 1000),
        )

        def contains(bounds: list[int]) -> bool:
            assert pixel is not None
            return (
                bounds[0] <= pixel[0] < bounds[2] and bounds[1] <= pixel[1] < bounds[3]
            )

        if not contains(obs["window_bounds"]):
            _fail("POINT_OUTSIDE_WINDOW")
        targets = [
            c
            for c in obs["controls"]
            if c["visible"]
            and c["enabled"]
            and c["name"] == context["target"]["name"]
            and c["role"] == context["target"]["role"]
        ]
        if len(targets) > 1:
            _fail("TARGET_NOT_UNIQUE")
        hits = [c for c in obs["controls"] if c["visible"] and contains(c["bounds"])]
        if len(hits) != 1:
            _fail("TARGET_NOT_UNIQUE")
        hit = hits[0]
        if not hit["enabled"]:
            _fail("TARGET_DISABLED")
        if (
            hit["name"] != context["target"]["name"]
            or hit["role"] != context["target"]["role"]
        ):
            _fail("TARGET_MISMATCH")
        ref = hit["ref"]
    return NativeProposal(
        context["request_id"],
        binding,
        context["target_scope"],
        context["current_epoch"],
        context["runtime_generation"],
        obs["frame"]["sha256"],
        ref,
        pixel,
    )
