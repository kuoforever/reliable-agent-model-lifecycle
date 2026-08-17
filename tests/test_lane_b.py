from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from fullcycle_bridge.lane_b import (
    MAX_ARTIFACT_BYTES,
    MAX_TOTAL_ARTIFACT_BYTES,
    LaneBValidationError,
    canonical_json_bytes,
    sha256_json,
    validate_bundle,
    validate_bundle_file,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "lane_b_v1"
VALID_BUNDLE = FIXTURES / "valid" / "minimal-bundle.json"
SCHEMA = ROOT / "schemas" / "lane_b_capture_bundle_v1.schema.json"


def load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


class LaneBContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bundle = load(VALID_BUNDLE)

    def assert_code(
        self, expected: str, value: object, function=validate_bundle
    ) -> LaneBValidationError:
        with self.assertRaises(LaneBValidationError) as raised:
            function(value)
        self.assertEqual(raised.exception.code, expected)
        return raised.exception

    def test_valid_synthetic_bundle_is_quarantined_and_deleted(self) -> None:
        summary = validate_bundle_file(VALID_BUNDLE.resolve())
        self.assertEqual(summary.bundle_version, 1)
        self.assertEqual(summary.consent_id, "consent_fixture_001")
        self.assertEqual(summary.session_id, "session_fixture_001")
        self.assertEqual(summary.episode_id, "episode_fixture_001")
        self.assertEqual(summary.artifact_count, 9)
        self.assertEqual(summary.step_count, 1)
        self.assertEqual(summary.data_class, "explicit_consent_rich_training_episode")
        self.assertEqual(summary.training_use, "quarantine_review_only")
        self.assertFalse(summary.training_eligible)
        self.assertTrue(summary.deletion_verified)

    def test_schema_is_closed_draft_2020_12_and_matches_versions(self) -> None:
        schema = load(SCHEMA)
        self.assertEqual(
            schema["$schema"], "https://json-schema.org/draft/2020-12/schema"
        )
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["properties"]["lane_b_bundle_version"]["const"], 1)
        self.assertEqual(
            schema["$defs"]["consent"]["properties"]["lane_b_consent_version"]["const"],
            1,
        )
        self.assertEqual(
            schema["$defs"]["episode"]["properties"]["lane_b_episode_version"]["const"],
            1,
        )
        self.assertEqual(
            schema["$defs"]["deletionReceipt"]["properties"][
                "lane_b_deletion_receipt_version"
            ]["const"],
            1,
        )
        for definition in (
            "consent",
            "episode",
            "artifact",
            "step",
            "candidateAction",
            "runtimeDecision",
            "verifier",
            "deletionReceipt",
        ):
            with self.subTest(definition=definition):
                self.assertFalse(schema["$defs"][definition]["additionalProperties"])
        self.assertEqual(len(schema["$defs"]["candidateAction"]["allOf"]), 2)
        self.assertEqual(len(schema["$defs"]["runtimeDecision"]["oneOf"]), 4)

    def test_consent_and_episode_digests_are_recomputed(self) -> None:
        consent = self.bundle["consent"]
        episode = self.bundle["episode"]
        self.assertEqual(
            episode["consent_binding"]["consent_sha256"], sha256_json(consent)
        )
        self.assertEqual(
            self.bundle["deletion_receipt"]["episode_sha256"], sha256_json(episode)
        )
        self.assertEqual(
            sha256_json(consent),
            "sha256:"
            + __import__("hashlib").sha256(canonical_json_bytes(consent)).hexdigest(),
        )

    def test_saved_invalid_fixtures_fail_with_stable_codes(self) -> None:
        expected = {
            "unknown-version.json": "UNSUPPORTED_VERSION",
            "unexpected-field.json": "UNKNOWN_FIELD",
            "missing-consent.json": "MISSING_FIELD",
            "malformed.json": "MALFORMED_JSON",
        }
        for filename, code in expected.items():
            with self.subTest(filename=filename):
                with self.assertRaises(LaneBValidationError) as raised:
                    validate_bundle_file((FIXTURES / "invalid" / filename).resolve())
                self.assertEqual(raised.exception.code, code)

    def test_consent_is_explicit_run_scoped_and_visible(self) -> None:
        mutations = (
            ("decision", "denied", "INVALID_VALUE"),
            ("capture_controls.run_scoped", False, "REQUIRED_TRUE"),
            ("capture_controls.disabled_by_default", False, "REQUIRED_TRUE"),
            ("operator_action.visible_indicator_acknowledged", False, "REQUIRED_TRUE"),
            ("capture_controls.background_capture", True, "REQUIRED_FALSE"),
        )
        for dotted, replacement, code in mutations:
            with self.subTest(field=dotted):
                invalid = copy.deepcopy(self.bundle)
                target = invalid["consent"]
                parts = dotted.split(".")
                for part in parts[:-1]:
                    target = target[part]
                target[parts[-1]] = replacement
                self.assert_code(code, invalid)

    def test_consent_scope_rejects_wildcards_network_and_window_drift(self) -> None:
        invalid = copy.deepcopy(self.bundle)
        invalid["consent"]["scope"]["application_scope"] = ["*"]
        self.assert_code("WILDCARD_SCOPE_FORBIDDEN", invalid)

        invalid = copy.deepcopy(self.bundle)
        invalid["consent"]["scope"]["network_upload_allowed"] = True
        self.assert_code("REQUIRED_FALSE", invalid)

        invalid = copy.deepcopy(self.bundle)
        invalid["consent"]["operator_action"]["expires_at_utc"] = "2026-08-17T07:59:59Z"
        self.assert_code("INVALID_CONSENT_WINDOW", invalid)

        invalid = copy.deepcopy(self.bundle)
        invalid["consent"]["retention"]["delete_by_utc"] = "2026-12-17T08:00:00Z"
        self.assert_code("INVALID_RETENTION_WINDOW", invalid)

    def test_all_forbidden_content_and_authority_flags_are_fail_closed(self) -> None:
        for field in self.bundle["consent"]["forbidden_content"]:
            with self.subTest(field=field):
                invalid = copy.deepcopy(self.bundle)
                invalid["consent"]["forbidden_content"][field] = False
                self.assert_code("REQUIRED_TRUE", invalid)
        for field in (
            "model_output_is_authority",
            "grants_execution_permission",
            "runtime_policy_bypass_allowed",
            "runner_mcp_desktop_bypass_allowed",
        ):
            with self.subTest(field=field):
                invalid = copy.deepcopy(self.bundle)
                invalid["consent"]["authority"][field] = True
                self.assert_code("REQUIRED_FALSE", invalid)

    def test_episode_requires_exact_consent_binding_and_window(self) -> None:
        invalid = copy.deepcopy(self.bundle)
        invalid["episode"]["consent_binding"]["consent_id"] = "other"
        self.assert_code("CONSENT_BINDING_MISMATCH", invalid)

        invalid = copy.deepcopy(self.bundle)
        invalid["episode"]["consent_binding"]["consent_sha256"] = "sha256:" + "a" * 64
        self.assert_code("CONSENT_BINDING_MISMATCH", invalid)

        invalid = copy.deepcopy(self.bundle)
        invalid["episode"]["capture"]["captured_at_utc"] = "2026-08-17T10:00:01Z"
        self.assert_code("CAPTURE_OUTSIDE_CONSENT_WINDOW", invalid)

    def test_capture_is_separate_local_sanitized_and_not_automatic(self) -> None:
        mutations = (
            ("indicator_visible", False, "REQUIRED_TRUE"),
            ("sanitization_completed_before_write", False, "REQUIRED_TRUE"),
            ("image_redaction_completed_before_write", False, "REQUIRED_TRUE"),
            ("automatic_runtime_export", True, "REQUIRED_FALSE"),
            ("network_upload_used", True, "REQUIRED_FALSE"),
            ("source_safe_trace_modified", True, "REQUIRED_FALSE"),
        )
        for field, replacement, code in mutations:
            with self.subTest(field=field):
                invalid = copy.deepcopy(self.bundle)
                invalid["episode"]["capture"][field] = replacement
                self.assert_code(code, invalid)

        invalid = copy.deepcopy(self.bundle)
        invalid["episode"]["capture"]["storage_namespace"] = "../lane-a"
        self.assert_code("INVALID_STORAGE_NAMESPACE", invalid)

    def test_every_episode_binds_runtime_model_policy_and_environment_versions(
        self,
    ) -> None:
        for field in self.bundle["episode"]["versions"]:
            with self.subTest(field=field):
                invalid = copy.deepcopy(self.bundle)
                del invalid["episode"]["versions"][field]
                self.assert_code("MISSING_FIELD", invalid)

        invalid = copy.deepcopy(self.bundle)
        invalid["episode"]["versions"]["runtime_git_commit"] = "0" * 40
        self.assert_code("INVALID_COMMIT", invalid)

    def test_artifacts_are_content_addressed_sanitized_and_role_typed(self) -> None:
        invalid = copy.deepcopy(self.bundle)
        invalid["episode"]["artifacts"][0]["content_sha256"] = "sha256:" + "a" * 64
        self.assert_code("ARTIFACT_CONTENT_ADDRESS_MISMATCH", invalid)

        invalid = copy.deepcopy(self.bundle)
        invalid["episode"]["artifacts"][0]["sanitized"] = False
        self.assert_code("REQUIRED_TRUE", invalid)

        invalid = copy.deepcopy(self.bundle)
        invalid["episode"]["artifacts"][2]["image_redacted"] = False
        self.assert_code("REQUIRED_TRUE", invalid)

        invalid = copy.deepcopy(self.bundle)
        invalid["episode"]["artifacts"][0]["media_type"] = "image/png"
        self.assert_code("IMAGE_ROLE_REQUIRED", invalid)

        invalid = copy.deepcopy(self.bundle)
        invalid["episode"]["artifacts"][2]["media_type"] = "text/plain"
        self.assert_code("IMAGE_MEDIA_TYPE_REQUIRED", invalid)

    def test_artifact_counts_bytes_roles_and_duplicates_are_bounded(self) -> None:
        invalid = copy.deepcopy(self.bundle)
        invalid["episode"]["artifacts"][0]["bytes"] = MAX_ARTIFACT_BYTES + 1
        self.assert_code("INVALID_INTEGER", invalid)

        invalid = copy.deepcopy(self.bundle)
        for artifact in invalid["episode"]["artifacts"]:
            artifact["bytes"] = MAX_ARTIFACT_BYTES
        self.assert_code("ARTIFACT_BYTES_EXCEEDED", invalid)
        self.assertEqual(MAX_TOTAL_ARTIFACT_BYTES, 24 * 1024 * 1024)

        invalid = copy.deepcopy(self.bundle)
        invalid["episode"]["artifacts"].append(
            copy.deepcopy(invalid["episode"]["artifacts"][0])
        )
        self.assert_code("DUPLICATE_ARTIFACT", invalid)

        invalid = copy.deepcopy(self.bundle)
        invalid["episode"]["artifacts"] = [
            artifact
            for artifact in invalid["episode"]["artifacts"]
            if artifact["role"] != "state_verifier_evidence"
        ]
        self.assert_code("MISSING_REQUIRED_ARTIFACT_ROLE", invalid)

    def test_steps_bind_candidate_runtime_result_and_observations(self) -> None:
        invalid = copy.deepcopy(self.bundle)
        invalid["episode"]["steps"][0]["candidate_action"]["record_ref"] = (
            "sha256:" + "6" * 64
        )
        self.assert_code("ARTIFACT_ROLE_MISMATCH", invalid)

        invalid = copy.deepcopy(self.bundle)
        invalid["episode"]["steps"][0]["runtime_decision"]["record_ref"] = (
            "sha256:" + "5" * 64
        )
        self.assert_code("ARTIFACT_ROLE_MISMATCH", invalid)

        invalid = copy.deepcopy(self.bundle)
        invalid["episode"]["steps"][0]["pre_observation_ref"] = "sha256:" + "8" * 64
        self.assert_code("ARTIFACT_ROLE_MISMATCH", invalid)

        invalid = copy.deepcopy(self.bundle)
        invalid["episode"]["steps"][0]["tool_result_ref"] = "sha256:" + "0" * 64
        self.assert_code("UNKNOWN_ARTIFACT_REF", invalid)

    def test_candidate_action_never_has_execution_authority(self) -> None:
        invalid = copy.deepcopy(self.bundle)
        invalid["episode"]["steps"][0]["candidate_action"]["execution_authority"] = (
            "execute"
        )
        self.assert_code("INVALID_VALUE", invalid)

        invalid = copy.deepcopy(self.bundle)
        action = invalid["episode"]["steps"][0]["candidate_action"]
        action["should_reject"] = True
        self.assert_code("TERMINAL_ACTION_HAS_EXECUTION_FIELDS", invalid)

        invalid = copy.deepcopy(self.bundle)
        invalid["episode"]["steps"][0]["candidate_action"]["confidence"] = 1.1
        self.assert_code("INVALID_CONFIDENCE", invalid)

        invalid = copy.deepcopy(self.bundle)
        invalid["episode"]["steps"][0]["candidate_action"]["bbox"] = [10, 20, 10, 30]
        self.assert_code("INVALID_BBOX", invalid)

        invalid = copy.deepcopy(self.bundle)
        action = invalid["episode"]["steps"][0]["candidate_action"]
        action["should_reject"] = True
        action["should_fallback"] = True
        action["next_tool"] = None
        action["arguments"] = {}
        action["bbox"] = None
        action["ref"] = None
        self.assert_code("INVALID_CANDIDATE_MODE", invalid)

        invalid = copy.deepcopy(self.bundle)
        action = invalid["episode"]["steps"][0]["candidate_action"]
        action["should_fallback"] = True
        action["requires_approval"] = True
        action["next_tool"] = None
        action["arguments"] = {}
        action["bbox"] = None
        action["ref"] = None
        self.assert_code("TERMINAL_ACTION_REQUIRES_APPROVAL", invalid)

    def test_runtime_is_the_only_dispatch_authority(self) -> None:
        invalid = copy.deepcopy(self.bundle)
        invalid["episode"]["steps"][0]["runtime_decision"]["runtime_is_authority"] = (
            False
        )
        self.assert_code("REQUIRED_TRUE", invalid)

        invalid = copy.deepcopy(self.bundle)
        decision = invalid["episode"]["steps"][0]["runtime_decision"]
        decision["policy_decision"] = "deny"
        self.assert_code("INVALID_RUNTIME_DISPATCH", invalid)

        invalid = copy.deepcopy(self.bundle)
        decision = invalid["episode"]["steps"][0]["runtime_decision"]
        decision["dispatched"] = False
        invalid["episode"]["steps"][0]["tool_result_ref"] = None
        self.assert_code("ALLOW_DECISION_NOT_DISPATCHED", invalid)

        invalid = copy.deepcopy(self.bundle)
        decision = invalid["episode"]["steps"][0]["runtime_decision"]
        decision["policy_decision"] = "approval_required"
        decision["approval_state"] = "approved"
        decision["dispatched"] = False
        invalid["episode"]["steps"][0]["tool_result_ref"] = None
        self.assert_code("INVALID_RUNTIME_STATE", invalid)

        invalid = copy.deepcopy(self.bundle)
        decision = invalid["episode"]["steps"][0]["runtime_decision"]
        decision["policy_decision"] = "defer"
        decision["approval_state"] = "pending"
        decision["dispatched"] = False
        invalid["episode"]["steps"][0]["tool_result_ref"] = None
        self.assert_code("INVALID_RUNTIME_STATE", invalid)

    def test_verifier_is_state_based_and_not_model_self_report(self) -> None:
        invalid = copy.deepcopy(self.bundle)
        invalid["episode"]["steps"][0]["verifier"]["source"] = "model"
        self.assert_code("INVALID_VALUE", invalid)

        invalid = copy.deepcopy(self.bundle)
        invalid["episode"]["steps"][0]["verifier"]["model_self_report_used"] = True
        self.assert_code("REQUIRED_FALSE", invalid)

        invalid = copy.deepcopy(self.bundle)
        invalid["episode"]["steps"][0]["verifier"]["evidence_refs"] = [
            "sha256:" + "8" * 64
        ]
        self.assert_code("VERIFIER_EVIDENCE_INCOMPLETE", invalid)

    def test_governance_remains_unassigned_unlicensed_and_ineligible(self) -> None:
        mutations = (
            ("dataset_split", "train", "INVALID_VALUE"),
            ("license_status", "approved", "INVALID_VALUE"),
            ("training_eligible", True, "REQUIRED_FALSE"),
            ("human_review_required", False, "REQUIRED_TRUE"),
        )
        for field, replacement, code in mutations:
            with self.subTest(field=field):
                invalid = copy.deepcopy(self.bundle)
                invalid["episode"]["governance"][field] = replacement
                self.assert_code(code, invalid)

    def test_deletion_receipt_binds_episode_and_covers_every_artifact(self) -> None:
        invalid = copy.deepcopy(self.bundle)
        invalid["deletion_receipt"]["episode_sha256"] = "sha256:" + "a" * 64
        self.assert_code("DELETION_BINDING_MISMATCH", invalid)

        invalid = copy.deepcopy(self.bundle)
        invalid["deletion_receipt"]["artifacts"].pop()
        self.assert_code("INCOMPLETE_DELETION", invalid)

        invalid = copy.deepcopy(self.bundle)
        invalid["deletion_receipt"]["remaining_artifact_count"] = 1
        self.assert_code("INCOMPLETE_DELETION", invalid)

        invalid = copy.deepcopy(self.bundle)
        invalid["deletion_receipt"]["verifier"]["raw_content_retained"] = True
        self.assert_code("REQUIRED_FALSE", invalid)

        invalid = copy.deepcopy(self.bundle)
        invalid["deletion_receipt"]["completed_at_utc"] = "2026-09-16T08:00:01Z"
        self.assert_code("INVALID_DELETION_TIMELINE", invalid)

    def test_duplicate_keys_and_nonfinite_numbers_are_rejected(self) -> None:
        work = ROOT / "work" / "test-fixtures"
        work.mkdir(parents=True, exist_ok=True)
        duplicate = work / "lane-b-duplicate.json"
        nonfinite = work / "lane-b-nonfinite.json"
        try:
            duplicate.write_text(
                '{"lane_b_bundle_version":1,"lane_b_bundle_version":1}',
                encoding="utf-8",
            )
            nonfinite.write_text('{"lane_b_bundle_version":NaN}', encoding="utf-8")
            with self.assertRaises(LaneBValidationError) as raised:
                validate_bundle_file(duplicate.resolve())
            self.assertEqual(raised.exception.code, "DUPLICATE_JSON_KEY")
            with self.assertRaises(LaneBValidationError) as raised:
                validate_bundle_file(nonfinite.resolve())
            self.assertEqual(raised.exception.code, "NONFINITE_NUMBER")
        finally:
            duplicate.unlink(missing_ok=True)
            nonfinite.unlink(missing_ok=True)

    def test_symlink_input_is_rejected_when_supported(self) -> None:
        work = ROOT / "work" / "test-fixtures"
        work.mkdir(parents=True, exist_ok=True)
        link = work / "lane-b-link.json"
        try:
            try:
                link.symlink_to(VALID_BUNDLE.resolve())
            except OSError as exc:
                self.skipTest(f"symlink unavailable: {exc}")
            with self.assertRaises(LaneBValidationError) as raised:
                validate_bundle_file(link.absolute())
            self.assertEqual(raised.exception.code, "UNSAFE_INPUT_FILE")
        finally:
            link.unlink(missing_ok=True)

    def test_cli_returns_machine_readable_success_and_failure(self) -> None:
        environment = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
        command = [
            sys.executable,
            "-m",
            "fullcycle_bridge.lane_b_cli",
            "--bundle",
            str(VALID_BUNDLE.resolve()),
        ]
        success = subprocess.run(
            command,
            cwd=ROOT,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(success.returncode, 0, success.stderr)
        payload = json.loads(success.stdout)
        self.assertTrue(payload["valid"])
        self.assertFalse(payload["training_eligible"])

        command[-1] = str((FIXTURES / "invalid" / "unknown-version.json").resolve())
        failure = subprocess.run(
            command,
            cwd=ROOT,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(failure.returncode, 2)
        self.assertEqual(json.loads(failure.stderr)["code"], "UNSUPPORTED_VERSION")


if __name__ == "__main__":
    unittest.main()
