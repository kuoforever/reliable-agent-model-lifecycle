from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from fullcycle_bridge.multimodal_trajectory import (
    MAX_ARTIFACT_BYTES,
    TrajectoryValidationError,
    validate_trajectory,
    validate_trajectory_file,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "multimodal_trajectory_v1"
TEXT_FIXTURE = FIXTURES / "valid" / "text-only.json"
IMAGE_FIXTURE = FIXTURES / "valid" / "image-grounded.json"
SCHEMA = ROOT / "schemas" / "multimodal_trajectory_v1.schema.json"


def load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


class MultimodalTrajectoryContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = load(TEXT_FIXTURE)
        cls.image = load(IMAGE_FIXTURE)

    def assert_code(self, expected: str, value: object) -> TrajectoryValidationError:
        with self.assertRaises(TrajectoryValidationError) as raised:
            validate_trajectory(value)
        self.assertEqual(raised.exception.code, expected)
        return raised.exception

    def test_text_and_image_fixtures_share_one_versioned_topology(self) -> None:
        text = validate_trajectory_file(TEXT_FIXTURE.resolve())
        image = validate_trajectory_file(IMAGE_FIXTURE.resolve())
        self.assertEqual(text.schema_version, image.schema_version, 1)
        self.assertEqual(text.modality, "text_only")
        self.assertEqual(image.modality, "image_grounded")
        self.assertEqual(text.artifact_count, 10)
        self.assertEqual(image.artifact_count, 17)
        self.assertEqual(text.previous_step_count, 0)
        self.assertEqual(image.previous_step_count, 1)
        self.assertEqual(text.transition_sequence, 1)
        self.assertEqual(image.transition_sequence, 2)
        self.assertTrue(text.dispatched)
        self.assertTrue(image.dispatched)
        self.assertFalse(text.training_eligible)
        self.assertFalse(image.execution_eligible)
        self.assertEqual(set(self.text), set(self.image))

    def test_schema_is_closed_draft_2020_12_and_pins_shared_topology(self) -> None:
        schema = load(SCHEMA)
        self.assertEqual(
            schema["$schema"], "https://json-schema.org/draft/2020-12/schema"
        )
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(
            schema["properties"]["multimodal_trajectory_schema_version"]["const"],
            1,
        )
        self.assertEqual(len(schema["properties"]["observations"]["prefixItems"]), 2)
        self.assertEqual(len(schema["$defs"]["runtimeDecision"]["oneOf"]), 4)
        for definition in (
            "provenance",
            "versions",
            "artifact",
            "tool",
            "historyStep",
            "inputs",
            "observationBase",
            "candidateAction",
            "runtimeDecision",
            "verifier",
            "transition",
            "governance",
        ):
            with self.subTest(definition=definition):
                self.assertFalse(schema["$defs"][definition]["additionalProperties"])

    def test_versions_bind_runtime_model_policy_environment_and_lane_b(self) -> None:
        for field in self.text["versions"]:
            with self.subTest(field=field):
                invalid = copy.deepcopy(self.text)
                del invalid["versions"][field]
                self.assert_code("MISSING_FIELD", invalid)

        invalid = copy.deepcopy(self.text)
        invalid["multimodal_trajectory_schema_version"] = 2
        self.assert_code("UNSUPPORTED_VERSION", invalid)

        invalid = copy.deepcopy(self.text)
        invalid["versions"]["runtime_git_commit"] = "0" * 40
        self.assert_code("INVALID_COMMIT", invalid)

        invalid = copy.deepcopy(self.text)
        invalid["versions"]["compatible_lane_b_episode_version"] = 2
        self.assert_code("UNSUPPORTED_VERSION", invalid)

    def test_provenance_accepts_only_synthetic_non_lane_a_input(self) -> None:
        mutations = (
            ("source", "lane_b_episode", "INVALID_VALUE"),
            ("real_capture", True, "REQUIRED_FALSE"),
            ("lane_b_bundle_ref", "sha256:" + "a" * 64, "REQUIRED_NULL"),
            ("lane_b_episode_ref", "sha256:" + "b" * 64, "REQUIRED_NULL"),
            ("automatic_lane_a_export_used", True, "REQUIRED_FALSE"),
        )
        for field, replacement, code in mutations:
            with self.subTest(field=field):
                invalid = copy.deepcopy(self.text)
                invalid["provenance"][field] = replacement
                self.assert_code(code, invalid)

    def test_closed_shapes_reject_unknown_and_missing_fields(self) -> None:
        invalid = copy.deepcopy(self.text)
        invalid["unexpected"] = True
        self.assert_code("UNKNOWN_FIELD", invalid)

        invalid = copy.deepcopy(self.text)
        del invalid["transition"]["verifier"]
        self.assert_code("MISSING_FIELD", invalid)

        invalid = copy.deepcopy(self.text)
        invalid["inputs"]["available_tools"][0]["extra"] = None
        self.assert_code("UNKNOWN_FIELD", invalid)

    def test_artifacts_are_bounded_content_addressed_and_role_typed(self) -> None:
        invalid = copy.deepcopy(self.text)
        invalid["artifacts"][0]["content_sha256"] = "sha256:" + "a" * 64
        self.assert_code("ARTIFACT_CONTENT_ADDRESS_MISMATCH", invalid)

        invalid = copy.deepcopy(self.text)
        invalid["artifacts"][0]["bytes"] = MAX_ARTIFACT_BYTES + 1
        self.assert_code("INVALID_INTEGER", invalid)

        invalid = copy.deepcopy(self.text)
        for artifact in invalid["artifacts"]:
            artifact["bytes"] = MAX_ARTIFACT_BYTES
        self.assert_code("ARTIFACT_BYTES_EXCEEDED", invalid)

        invalid = copy.deepcopy(self.text)
        invalid["artifacts"][0]["role"] = "unknown"
        self.assert_code("INVALID_ENUM", invalid)

    def test_every_artifact_must_be_referenced(self) -> None:
        invalid = copy.deepcopy(self.text)
        orphan = copy.deepcopy(invalid["artifacts"][4])
        orphan["artifact_id"] = "sha256:" + "a" * 64
        orphan["content_sha256"] = orphan["artifact_id"]
        invalid["artifacts"].append(orphan)
        self.assert_code("ORPHAN_ARTIFACT", invalid)

    def test_image_artifacts_require_redaction_and_image_media(self) -> None:
        invalid = copy.deepcopy(self.image)
        invalid["artifacts"][9]["image_redacted"] = False
        self.assert_code("REQUIRED_TRUE", invalid)

        invalid = copy.deepcopy(self.image)
        invalid["artifacts"][9]["media_type"] = "application/json"
        self.assert_code("IMAGE_MEDIA_TYPE_REQUIRED", invalid)

        invalid = copy.deepcopy(self.text)
        invalid["artifacts"][0]["media_type"] = "image/png"
        self.assert_code("IMAGE_ROLE_REQUIRED", invalid)

    def test_instruction_policy_and_tool_schema_roles_are_exact(self) -> None:
        invalid = copy.deepcopy(self.text)
        invalid["inputs"]["instruction_ref"] = invalid["inputs"]["policy_context_ref"]
        self.assert_code("ARTIFACT_ROLE_MISMATCH", invalid)

        invalid = copy.deepcopy(self.text)
        invalid["inputs"]["available_tools"][0]["argument_schema_ref"] = invalid[
            "inputs"
        ]["policy_context_ref"]
        self.assert_code("ARTIFACT_ROLE_MISMATCH", invalid)

    def test_available_tools_are_unique_and_candidate_must_select_one(self) -> None:
        invalid = copy.deepcopy(self.text)
        invalid["inputs"]["available_tools"].append(
            copy.deepcopy(invalid["inputs"]["available_tools"][0])
        )
        self.assert_code("DUPLICATE_TOOL", invalid)

        invalid = copy.deepcopy(self.text)
        invalid["transition"]["candidate_action"]["next_tool"] = "missing_tool"
        self.assert_code("UNAVAILABLE_TOOL", invalid)

    def test_previous_steps_are_contiguous_and_bind_results(self) -> None:
        invalid = copy.deepcopy(self.image)
        invalid["inputs"]["previous_steps"][0]["sequence"] = 2
        self.assert_code("NONCONTIGUOUS_HISTORY", invalid)

        invalid = copy.deepcopy(self.image)
        step = invalid["inputs"]["previous_steps"][0]
        step["dispatched"] = False
        self.assert_code("UNDISPATCHED_TOOL_RESULT", invalid)

        invalid = copy.deepcopy(self.image)
        step = invalid["inputs"]["previous_steps"][0]
        step["dispatched"] = False
        step["tool_result_ref"] = None
        step["outcome"] = "success"
        self.assert_code("INVALID_HISTORY_OUTCOME", invalid)

    def test_previous_step_verifier_covers_post_observation(self) -> None:
        invalid = copy.deepcopy(self.image)
        invalid["inputs"]["previous_steps"][0]["verifier_evidence_refs"] = [
            "sha256:" + "28" * 32
        ]
        self.assert_code("VERIFIER_EVIDENCE_INCOMPLETE", invalid)

    def test_observation_stages_and_transition_links_are_exact(self) -> None:
        invalid = copy.deepcopy(self.text)
        invalid["observations"][0]["stage"] = "post_action"
        self.assert_code("INVALID_VALUE", invalid)

        invalid = copy.deepcopy(self.text)
        invalid["transition"]["pre_observation_id"] = invalid["transition"][
            "post_observation_id"
        ]
        self.assert_code("PRE_OBSERVATION_LINK_MISMATCH", invalid)

        invalid = copy.deepcopy(self.image)
        invalid["transition"]["sequence"] = 1
        self.assert_code("NONCONTIGUOUS_TRANSITION", invalid)

    def test_pre_and_post_observations_are_nonempty_and_distinct(self) -> None:
        invalid = copy.deepcopy(self.text)
        pre = invalid["observations"][0]
        pre["uia_refs"] = []
        pre["document_text_refs"] = []
        self.assert_code("EMPTY_OBSERVATION", invalid)

        invalid = copy.deepcopy(self.text)
        invalid["observations"][1]["uia_refs"] = invalid["observations"][0]["uia_refs"]
        self.assert_code("PRE_POST_OBSERVATION_ALIAS", invalid)

    def test_modality_rules_distinguish_text_and_image_grounding(self) -> None:
        invalid = copy.deepcopy(self.image)
        invalid["modality"] = "text_only"
        self.assert_code("TEXT_ONLY_IMAGE_FORBIDDEN", invalid)

        invalid = copy.deepcopy(self.text)
        invalid["modality"] = "image_grounded"
        self.assert_code("IMAGE_GROUNDING_REQUIRED", invalid)

    def test_candidate_evidence_must_come_from_current_pre_observation(self) -> None:
        invalid = copy.deepcopy(self.text)
        invalid["transition"]["candidate_action"]["evidence_refs"] = invalid[
            "observations"
        ][1]["uia_refs"]
        self.assert_code("CANDIDATE_EVIDENCE_NOT_PRE_OBSERVATION", invalid)

    def test_bbox_requires_supported_tool_and_image_evidence(self) -> None:
        invalid = copy.deepcopy(self.text)
        invalid["transition"]["candidate_action"]["bbox"] = [1, 2, 10, 20]
        self.assert_code("BBOX_NOT_SUPPORTED", invalid)

        invalid = copy.deepcopy(self.image)
        invalid["transition"]["candidate_action"]["evidence_refs"] = invalid[
            "observations"
        ][0]["uia_refs"]
        self.assert_code("BBOX_IMAGE_EVIDENCE_REQUIRED", invalid)

    def test_ref_requires_supported_tool_and_structured_text_evidence(self) -> None:
        invalid = copy.deepcopy(self.text)
        invalid["inputs"]["available_tools"][0]["supports_ref"] = False
        self.assert_code("REF_NOT_SUPPORTED", invalid)

        invalid = copy.deepcopy(self.image)
        invalid["transition"]["candidate_action"]["bbox"] = None
        invalid["transition"]["candidate_action"]["evidence_refs"] = invalid[
            "observations"
        ][0]["image_refs"]
        self.assert_code("REF_TEXT_EVIDENCE_REQUIRED", invalid)

    def test_model_candidate_has_no_execution_authority_or_mixed_terminal_mode(
        self,
    ) -> None:
        invalid = copy.deepcopy(self.text)
        invalid["transition"]["candidate_action"]["execution_authority"] = "execute"
        self.assert_code("INVALID_VALUE", invalid)

        invalid = copy.deepcopy(self.text)
        action = invalid["transition"]["candidate_action"]
        action["should_reject"] = True
        action["should_fallback"] = True
        action["next_tool"] = None
        action["arguments"] = {}
        action["bbox"] = None
        action["ref"] = None
        self.assert_code("INVALID_CANDIDATE_MODE", invalid)

    def test_runtime_binds_policy_and_is_the_only_dispatch_authority(self) -> None:
        invalid = copy.deepcopy(self.text)
        invalid["transition"]["runtime_decision"]["policy_context_ref"] = invalid[
            "inputs"
        ]["instruction_ref"]
        self.assert_code("POLICY_CONTEXT_BINDING_MISMATCH", invalid)

        invalid = copy.deepcopy(self.text)
        invalid["transition"]["runtime_decision"]["runtime_is_authority"] = False
        self.assert_code("REQUIRED_TRUE", invalid)

        invalid = copy.deepcopy(self.text)
        decision = invalid["transition"]["runtime_decision"]
        decision["policy_decision"] = "approval_required"
        decision["approval_state"] = "approved"
        decision["dispatched"] = False
        invalid["transition"]["tool_result_ref"] = None
        self.assert_code("INVALID_RUNTIME_STATE", invalid)

    def test_tool_result_exists_only_for_dispatched_transition(self) -> None:
        invalid = copy.deepcopy(self.text)
        decision = invalid["transition"]["runtime_decision"]
        decision["policy_decision"] = "deny"
        decision["approval_state"] = "not_required"
        decision["dispatched"] = False
        self.assert_code("UNDISPATCHED_TOOL_RESULT", invalid)

    def test_verifier_is_state_based_and_covers_post_observation(self) -> None:
        invalid = copy.deepcopy(self.text)
        invalid["transition"]["verifier"]["source"] = "model"
        self.assert_code("INVALID_VALUE", invalid)

        invalid = copy.deepcopy(self.text)
        invalid["transition"]["verifier"]["model_self_report_used"] = True
        self.assert_code("REQUIRED_FALSE", invalid)

        invalid = copy.deepcopy(self.text)
        invalid["transition"]["verifier"]["evidence_refs"] = ["sha256:" + "1a" * 32]
        self.assert_code("VERIFIER_EVIDENCE_INCOMPLETE", invalid)

    def test_governance_remains_unassigned_and_ineligible(self) -> None:
        mutations = (
            ("synthetic_only", False, "REQUIRED_TRUE"),
            ("lane_b_capture_required_for_real_data", False, "REQUIRED_TRUE"),
            ("dataset_split", "train", "INVALID_VALUE"),
            ("license_status", "approved", "INVALID_VALUE"),
            ("training_eligible", True, "REQUIRED_FALSE"),
            ("execution_eligible", True, "REQUIRED_FALSE"),
            ("human_review_required", False, "REQUIRED_TRUE"),
        )
        for field, replacement, code in mutations:
            with self.subTest(field=field):
                invalid = copy.deepcopy(self.text)
                invalid["governance"][field] = replacement
                self.assert_code(code, invalid)

    def test_saved_parser_failures_have_stable_codes(self) -> None:
        expected = {
            "malformed.json": "MALFORMED_JSON",
            "missing-fields.json": "MISSING_FIELD",
            "duplicate-key.json": "DUPLICATE_JSON_KEY",
            "nonfinite.json": "NONFINITE_NUMBER",
        }
        for filename, code in expected.items():
            with self.subTest(filename=filename):
                with self.assertRaises(TrajectoryValidationError) as raised:
                    validate_trajectory_file(
                        (FIXTURES / "invalid" / filename).resolve()
                    )
                self.assertEqual(raised.exception.code, code)

    def test_symlink_input_is_rejected_when_supported(self) -> None:
        work = ROOT / "work" / "test-fixtures"
        work.mkdir(parents=True, exist_ok=True)
        link = work / "trajectory-link.json"
        try:
            try:
                link.symlink_to(TEXT_FIXTURE.resolve())
            except OSError as exc:
                self.skipTest(f"symlink unavailable: {exc}")
            with self.assertRaises(TrajectoryValidationError) as raised:
                validate_trajectory_file(link.absolute())
            self.assertEqual(raised.exception.code, "UNSAFE_INPUT_FILE")
        finally:
            link.unlink(missing_ok=True)

    def test_cli_returns_machine_readable_success_and_failure(self) -> None:
        environment = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
        command = [
            sys.executable,
            "-m",
            "fullcycle_bridge.multimodal_trajectory_cli",
            "--trajectory",
            str(TEXT_FIXTURE.resolve()),
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
        self.assertEqual(payload["modality"], "text_only")
        self.assertFalse(payload["execution_eligible"])

        command[-1] = str((FIXTURES / "invalid" / "nonfinite.json").resolve())
        failure = subprocess.run(
            command,
            cwd=ROOT,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(failure.returncode, 2)
        self.assertEqual(json.loads(failure.stderr)["code"], "NONFINITE_NUMBER")


if __name__ == "__main__":
    unittest.main()
