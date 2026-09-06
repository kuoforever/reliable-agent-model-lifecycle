"""Adversarial boundaries for native response binding and coordinate-to-ref mapping."""

from __future__ import annotations

import copy
import json
import unittest

from scripts.validate_native_gui_proposal import (
    REPORT,
    check_runtime_receipt,
    contexts,
    reply,
    replay,
)
from fullcycle_bridge.native_gui_proposal import (
    NativeProposalError,
    compile_native_response,
    context_digest,
    parse_native,
    validate_context,
)


def click(x=500, y=100):
    return (
        "<tool_call>"
        + json.dumps(
            dict(
                name="computer_use",
                arguments=dict(action="left_click", coordinate=[x, y]),
            )
        )
        + "</tool_call>"
    )


STOP = '<tool_call>{"name":"computer_use","arguments":{"action":"terminate","status":"failure"}}</tool_call>'


class NativeTests(unittest.TestCase):
    def setUp(self):
        self.context = contexts()["browser-address"]

    def compile(self, raw=None, current=None):
        return compile_native_response(
            self.context,
            self.context if current is None else current,
            reply(self.context, click() if raw is None else raw),
        ).to_dict()

    def test_retained_model_outputs(self):
        report = replay()
        self.assertEqual(len(report["cases"]), 24)
        self.assertEqual(report["click_proposals"], 18)
        self.assertEqual(report["stop_proposals"], 6)
        self.assertEqual(len(report["negative_controls"]), 13)

    def test_runtime_receipt_rejects_promotion(self):
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        check_runtime_receipt(report)
        report["runtime"]["dispatch_count"] = 1
        with self.assertRaisesRegex(ValueError, "Runtime receipt drift"):
            check_runtime_receipt(report)

    def test_point_becomes_only_ref(self):
        result = self.compile()
        self.assertEqual(result["pixel_point"], [512, 64])
        self.assertEqual(result["arguments"], {"ref": "ref_1"})
        self.assertEqual(result["tool"], "click")
        self.assertFalse(result["execution_authorized"])
        self.assertEqual(result["target_scope"], "314")

    def test_stop_has_no_tool_or_coordinate(self):
        result = self.compile(STOP)
        self.assertEqual(result["action"], "stop")
        self.assertIsNone(result["tool"])
        self.assertIsNone(result["pixel_point"])
        self.assertEqual(result["arguments"], {})

    def test_native_output_cannot_supply_authority(self):
        for args in [
            dict(action="terminate", status="success"),
            dict(action="left_click", coordinate=[500, 100], approval=True),
            dict(action="left_click", ref="ref_1"),
            dict(action="key", text="Ctrl+S"),
        ]:
            raw = (
                "<tool_call>"
                + json.dumps(dict(name="computer_use", arguments=args))
                + "</tool_call>"
            )
            with self.subTest(args=args), self.assertRaises(NativeProposalError):
                self.compile(raw)

    def test_envelope_and_json_attacks(self):
        for raw in [
            click() + click(),
            "Proceed: " + click(),
            "```json\n" + click() + "\n```",
            '<tool_call>{"name":"other","name":"computer_use","arguments":{}}</tool_call>',
            '<tool_call>{"name":"computer_use","arguments":{"action":"left_click","coordinate":[NaN,1]}}</tool_call>',
            "x" * 4097,
            "\ud800",
        ]:
            with (
                self.subTest(raw=repr(raw)[:60]),
                self.assertRaises(NativeProposalError),
            ):
                parse_native(raw)

    def test_rejects_precision_resource_attacks(self):
        for number in ["1e-99999999", "1e99999999", "1e9999999999999999999999"]:
            raw = (
                '<tool_call>{"name":"computer_use","arguments":{"action":"left_click","coordinate":['
                + number
                + ",1]}}</tool_call>"
            )
            with self.subTest(number=number), self.assertRaises(NativeProposalError):
                parse_native(raw)

    def test_coordinate_range_and_bool(self):
        for x, y in [
            (1000, 10),
            (-1, 10),
            (500, 1000),
            (True, 10),
            ("500", 10),
            (None, 10),
        ]:
            with self.subTest(point=(x, y)), self.assertRaises(NativeProposalError):
                self.compile(click(x, y))

    def test_fractional_pixel_and_exclusive_right_edge(self):
        result = self.compile(click(500.999999999, 100))
        self.assertEqual(result["pixel_point"], [513, 64])
        # x = 940 is the exclusive right edge of the requested control.
        with self.assertRaisesRegex(NativeProposalError, "TARGET_NOT_UNIQUE"):
            self.compile(click(917.96875, 100))

    def test_full_frame_last_pixel_and_zero(self):
        self.context["observation"]["controls"] = [
            dict(
                ref="ref_1",
                name="Address bar",
                role="edit",
                enabled=True,
                visible=True,
                bounds=[0, 0, 1024, 640],
            )
        ]
        self.assertEqual(self.compile(click(0, 0))["pixel_point"], [0, 0])
        self.assertEqual(
            self.compile(click(999.999999999, 999.999999999))["pixel_point"],
            [1023, 639],
        )

    def test_all_context_changes_invalidate_reply(self):
        for kind in [
            "frame",
            "epoch",
            "generation",
            "foreground",
            "bounds",
            "scope",
            "target",
        ]:
            current = copy.deepcopy(self.context)
            if kind == "frame":
                current["observation"]["frame"]["sha256"] = "0" * 64
            elif kind == "epoch":
                current["current_epoch"] += 1
            elif kind == "generation":
                current["runtime_generation"] += 1
            elif kind == "foreground":
                current["observation"]["foreground_scope"] = "315"
            elif kind == "bounds":
                current["observation"]["controls"][1]["bounds"][0] += 1
            elif kind == "scope":
                current["target_scope"] = current["observation"]["scope"] = "315"
            elif kind == "target":
                current["target"]["name"] = "Other"
            with (
                self.subTest(kind=kind),
                self.assertRaisesRegex(NativeProposalError, "CONTEXT_CHANGED"),
            ):
                self.compile(current=current)

    def test_reply_is_bound_to_request_and_frame_digest(self):
        for field in ["request_id", "context_digest"]:
            response = reply(self.context, click())
            response[field] = "wrong"
            with (
                self.subTest(field=field),
                self.assertRaisesRegex(NativeProposalError, "REPLY_BINDING_MISMATCH"),
            ):
                compile_native_response(self.context, self.context, response)

    def test_stale_click_rejected_stop_allowed(self):
        self.context["observation"]["epoch"] = 6
        with self.assertRaisesRegex(NativeProposalError, "STALE_OBSERVATION"):
            self.compile()
        self.assertEqual(self.compile(STOP)["action"], "stop")

    def test_background_click_rejected(self):
        self.context["observation"]["foreground_scope"] = "315"
        with self.assertRaisesRegex(NativeProposalError, "TARGET_NOT_FOREGROUND"):
            self.compile()

    def test_overlap_even_with_wrong_name_is_ambiguous(self):
        self.context["observation"]["controls"].append(
            dict(
                self.context["observation"]["controls"][1],
                ref="ref_99",
                name="Popup",
                enabled=False,
            )
        )
        with self.assertRaisesRegex(NativeProposalError, "TARGET_NOT_UNIQUE"):
            self.compile()

    def test_duplicate_named_targets_even_without_overlap(self):
        self.context["observation"]["controls"].append(
            dict(
                self.context["observation"]["controls"][1],
                ref="ref_99",
                bounds=[110, 200, 940, 250],
            )
        )
        with self.assertRaisesRegex(NativeProposalError, "TARGET_NOT_UNIQUE"):
            self.compile()

    def test_disabled_hidden_wrong_name_and_role(self):
        for field, value, error in [
            ("enabled", False, "TARGET_DISABLED"),
            ("visible", False, "TARGET_NOT_UNIQUE"),
            ("name", "Other", "TARGET_MISMATCH"),
            ("role", "button", "TARGET_MISMATCH"),
        ]:
            current = copy.deepcopy(self.context)
            current["observation"]["controls"][1][field] = value
            with (
                self.subTest(field=field),
                self.assertRaisesRegex(NativeProposalError, error),
            ):
                compile_native_response(current, current, reply(current, click()))

    def test_window_boundary(self):
        self.context["observation"]["controls"] = [
            self.context["observation"]["controls"][1]
        ]
        self.context["observation"]["window_bounds"] = [100, 50, 960, 630]
        with self.assertRaisesRegex(NativeProposalError, "POINT_OUTSIDE_WINDOW"):
            self.compile(click(50, 50))

    def test_closed_schema_and_coordinate_space(self):
        for change in [
            lambda c: c.update(approval=True),
            lambda c: c["observation"]["frame"].update(coordinate_space="crop_pixels"),
            lambda c: c.update(current_epoch=True),
            lambda c: c["observation"]["frame"].update(width=0),
            lambda c: c["observation"]["controls"].append(
                copy.deepcopy(c["observation"]["controls"][0])
            ),
        ]:
            current = copy.deepcopy(self.context)
            change(current)
            with self.assertRaises(NativeProposalError):
                validate_context(current)

    def test_detached_snapshot_and_digest(self):
        detached = validate_context(self.context)
        old = context_digest(detached)
        self.context["observation"]["controls"][1]["name"] = "Changed"
        self.assertEqual(context_digest(detached), old)
        self.assertNotEqual(context_digest(self.context), old)


if __name__ == "__main__":
    unittest.main()
