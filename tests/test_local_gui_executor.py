"""Offline adversarial checks of a model-side contract, with no desktop ports."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from fullcycle_bridge.local_gui_executor import (
    ExecutorContractError,
    compile_response,
    model_request,
    parse_response,
    request_digest,
    validate_request,
)

ROOT = Path(__file__).resolve().parents[1]


def cases():
    return json.loads(
        (ROOT / "fixtures/local_gui_executor_v1/cases.json").read_text(encoding="utf-8")
    )["cases"]


class LocalGuiExecutorTests(unittest.TestCase):
    def setUp(self):
        first = cases()[0]
        self.request = first["request"]
        self.response = first["response"]

    def compile(self, request=None, response=None, current=None):
        request = self.request if request is None else request
        response = self.response if response is None else response
        return compile_response(
            request, request if current is None else current, json.dumps(response)
        )

    def assert_code(self, code, callback, *args):
        with self.assertRaisesRegex(ExecutorContractError, "^" + code + "$"):
            callback(*args)

    def test_new_fixture_controls(self):
        self.assertEqual(len(cases()), 12)
        self.assertEqual(len({c["id"] for c in cases()}), 12)
        for case in cases():
            with self.subTest(case=case["id"]):
                if "error" in case["expected"]:
                    self.assert_code(
                        case["expected"]["error"],
                        self.compile,
                        case["request"],
                        case["response"],
                        case["current_request"],
                    )
                else:
                    output = self.compile(
                        case["request"], case["response"], case["current_request"]
                    ).to_dict()
                    self.assertEqual(
                        {k: output[k] for k in ["tool", "arguments"]}, case["expected"]
                    )
                    self.assertFalse(output["execution_authorized"])

    def test_unknown_authority_coordinates_scope_and_text_rejected(self):
        for key, value in [
            ("x", 12),
            ("y", 19),
            ("scope", "all"),
            ("approval", True),
            ("text", "INJECTED"),
            ("tool", "shell"),
        ]:
            response = dict(self.response, **{key: value})
            with self.subTest(key=key):
                self.assert_code("RESPONSE_FIELDS", self.compile, None, response)

    def test_wrong_request_or_response_epoch(self):
        self.assert_code(
            "REQUEST_MISMATCH",
            self.compile,
            None,
            dict(self.response, request_id="another"),
        )
        self.assert_code(
            "RESPONSE_EPOCH_MISMATCH",
            self.compile,
            None,
            dict(self.response, observation_epoch=42),
        )

    def test_any_changed_context_rejects_old_response(self):
        changes = [
            lambda r: r.update(current_epoch=44),
            lambda r: r.update(runtime_generation=10),
            lambda r: r["observation"].update(text="changed"),
            lambda r: r["observation"].update(foreground_scope="9903"),
        ]
        for change in changes:
            current = copy.deepcopy(self.request)
            change(current)
            self.assert_code("CONTEXT_CHANGED", self.compile, None, None, current)

    def test_payload_change_rejects_late_write(self):
        case = next(c for c in cases() if c["id"] == "contract-write-new")
        current = copy.deepcopy(case["request"])
        current["subgoal"]["text"] = "different text"
        self.assert_code(
            "CONTEXT_CHANGED", self.compile, case["request"], case["response"], current
        )

    def test_stale_action_fails_and_observe_is_explicit(self):
        self.request["observation"]["epoch"] = 42
        self.assert_code("STALE_OBSERVATION", self.compile)
        response = {
            "request_id": self.request["request_id"],
            "observation_epoch": 43,
            "action": "observe",
        }
        self.assertEqual(
            dict(self.compile(response=response).arguments), {"scope": "7601"}
        )

    def test_model_cannot_choose_subgoal_or_finish(self):
        response = {k: v for k, v in self.response.items() if k != "ref"}
        self.assert_code(
            "ACTION_OUTSIDE_SUBGOAL", self.compile, None, dict(response, action="save")
        )
        self.assert_code(
            "UNKNOWN_ACTION", self.compile, None, dict(response, action="complete")
        )

    def test_ambiguous_disabled_wrong_role_and_unknown_targets_fail(self):
        changes = [
            lambda c: c[0].update(enabled=False),
            lambda c: c[0].update(role="button"),
            lambda c: c[1].update(name="Page 2 content"),
            lambda c: c[0].update(ref="ref_970"),
        ]
        for change in changes:
            request = copy.deepcopy(self.request)
            change(request["observation"]["controls"])
            self.assert_code("TARGET_NOT_UNIQUE_OR_MISMATCHED", self.compile, request)

    def test_foreground_and_focus_required_for_write(self):
        case = next(c for c in cases() if c["id"] == "contract-write-new")
        request = case["request"]
        request["observation"]["foreground_scope"] = "9903"
        self.assert_code(
            "TARGET_NOT_FOREGROUND", self.compile, request, case["response"]
        )
        request["observation"]["foreground_scope"] = "7601"
        request["observation"]["controls"][0]["focused"] = False
        self.assert_code("EDITOR_NOT_FOCUSED", self.compile, request, case["response"])

    def test_exact_types_windows_and_version(self):
        for key, value, code in [
            ("version", True, "INVALID_VERSION"),
            ("current_epoch", True, "INVALID_EPOCH"),
            ("runtime_generation", -1, "INVALID_EPOCH"),
            ("target_scope", "foreground", "INVALID_WINDOW"),
            ("target_scope", "07601", "INVALID_WINDOW"),
        ]:
            request = copy.deepcopy(self.request)
            request[key] = value
            self.assert_code(code, validate_request, request)

    def test_snapshot_scope_future_epoch_and_duplicate_ref_rejected(self):
        for updates, code in [
            ({"scope": "9903"}, "OBSERVATION_SCOPE_MISMATCH"),
            ({"epoch": 44}, "FUTURE_OBSERVATION"),
            ({"text_verified": 1}, "INVALID_VERIFICATION_FACT"),
        ]:
            request = copy.deepcopy(self.request)
            request["observation"].update(updates)
            self.assert_code(code, validate_request, request)
        self.request["observation"]["controls"][1]["ref"] = "ref_941"
        self.assert_code("DUPLICATE_REF", validate_request, self.request)

    def test_raw_json_boundary(self):
        for raw, code in [
            ("```json\n{}\n```", "INVALID_RESPONSE_JSON"),
            ("[]", "RESPONSE_FIELDS"),
            ('{"action":"stop","action":"save"}', "DUPLICATE_JSON_KEY"),
            ('{"action":NaN}', "NONFINITE_JSON"),
            ("x" * 4097, "RESPONSE_TOO_LARGE"),
        ]:
            self.assert_code(code, parse_response, raw)

    def test_request_budget_and_non_json_types(self):
        self.request["observation"]["text"] = "x" * 32769
        self.assert_code("REQUEST_TOO_LARGE", validate_request, self.request)
        request = cases()[0]["request"]
        request["observation"]["controls"] = tuple(request["observation"]["controls"])
        self.assert_code("INVALID_JSON_VALUE", validate_request, request)

    def test_input_and_result_are_detached_not_authority(self):
        before = copy.deepcopy(self.request)
        validated = validate_request(self.request)
        validated["observation"]["controls"].clear()
        self.assertEqual(self.request, before)
        proposal = self.compile()
        projection = proposal.to_dict()
        projection["arguments"]["ref"] = "ref_999"
        self.assertEqual(dict(proposal.arguments), {"ref": "ref_941"})
        self.assertFalse(proposal.to_dict()["execution_authorized"])
        # Pure compilation is repeatable; it is not a deduplication or execution ledger.
        self.assertEqual(self.compile(), proposal)

    def test_model_projection_separates_untrusted_text_and_closed_actions(self):
        case = next(c for c in cases() if c["id"] == "contract-injection-new")
        projection = model_request(case["request"])
        self.assertEqual(
            projection["allowed_actions"], ["read_text", "observe", "stop"]
        )
        self.assertNotIn("expected", projection)
        self.assertIn("UNTRUSTED", projection["request"]["observation"]["text"])
        self.assertEqual(
            request_digest(case["request"]),
            request_digest(copy.deepcopy(case["request"])),
        )


if __name__ == "__main__":
    unittest.main()
