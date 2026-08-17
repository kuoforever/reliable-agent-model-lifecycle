from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SRC))

from fullcycle_bridge import mm003_baseline_protocol as ground_v1  # noqa: E402
from fullcycle_bridge import mm003_post_training_protocol_v2 as contract  # noqa: E402
from scripts import run_mm003_qlora_post_training_v2 as runner  # noqa: E402


def _value_at(value: dict[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = value
    for segment in path:
        current = current[segment]
    return current


def _set_at(value: dict[str, Any], path: tuple[str, ...], replacement: Any) -> None:
    current: dict[str, Any] = value
    for segment in path[:-1]:
        current = current[segment]
    current[path[-1]] = replacement


class MM003PostTrainingRecoveryProtocolV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.v1_preregistration = contract.parse_strict_json_bytes(
            (ROOT / contract.V1_PREREGISTRATION_RECEIPT["path"]).read_bytes(),
            location="$.v1_preregistration",
        )
        cls.train = contract.validate_dataset(
            contract.parse_strict_json_bytes(
                (ROOT / contract.TRAIN_DATASET_PATH).read_bytes(), location="$.train"
            ),
            split="train",
        )
        cls.validation = contract.validate_dataset(
            contract.parse_strict_json_bytes(
                (ROOT / contract.VALIDATION_DATASET_PATH).read_bytes(),
                location="$.validation",
            ),
            split="validation",
        )
        cls.source_hashes = {
            name: contract.sha256_bytes((ROOT / path).read_bytes())
            for name, path in contract.PROTOCOL_SOURCE_PATHS.items()
        }
        cls.preregistration = contract.expected_preregistration(
            freeze_status="frozen",
            v1_preregistration=cls.v1_preregistration,
            source_hashes=cls.source_hashes,
            train=cls.train,
            validation=cls.validation,
        )
        cls.inputs = runner.load_and_validate_inputs()
        cls.lineage = contract.validate_recovery_lineage_payloads(
            v1_preregistration_payload=(
                ROOT / contract.V1_PREREGISTRATION_RECEIPT["path"]
            ).read_bytes(),
            v1_failure_payload=(
                ROOT / contract.V1_FAILURE_RECEIPT["path"]
            ).read_bytes(),
            v1_failure_classification_payload=(
                ROOT / contract.V1_FAILURE_CLASSIFICATION_RECEIPT["path"]
            ).read_bytes(),
        )

    def _validate_delta(self, candidate: dict[str, Any]) -> dict[str, Any]:
        return contract.validate_recovery_delta(
            self.v1_preregistration,
            candidate,
            train=self.train,
            validation=self.validation,
            source_hashes=self.source_hashes,
        )

    def test_lineage_payloads_and_failure_classification_are_exactly_bound(self) -> None:
        self.assertEqual(
            self.lineage["v1_preregistration"], self.v1_preregistration
        )
        self.assertEqual(
            self.lineage["v1_failure_receipt"]["retry_count"], 0
        )
        self.assertFalse(
            self.lineage["v1_failure_receipt"]["formal_gate_passed"]
        )
        self.assertEqual(
            self.lineage["v1_failure_classification"]["report_digest"],
            contract.V1_FAILURE_CLASSIFICATION_RECEIPT["report_digest"],
        )
        self.assertEqual(
            self.preregistration["source_lineage"]["v1_failure_lineage"],
            contract.expected_v1_failure_lineage(),
        )
        policy_report = contract.validate_failure_classification_recovery_policy(
            self.lineage["v1_failure_classification"]
        )
        self.assertEqual(
            policy_report,
            {
                "comparison_unit": "recursive_json_leaf",
                "exact_value_replacements": 12,
                "preserved_protocol_sources": 10,
                "added_protocol_sources": 2,
                "authorized_new_sections": 4,
                "required_gates": 13,
            },
        )
        changed = copy.deepcopy(self.lineage["v1_failure_classification"])
        changed["locked_next_action"]["required_v2_values"]["experiment_id"] = (
            "self-attested-drift"
        )
        with self.assertRaises(contract.MM003PostTrainingProtocolError):
            contract.validate_failure_classification_recovery_policy(changed)

    def test_preregistration_recomputes_and_delta_is_closed(self) -> None:
        self.assertEqual(
            contract.validate_preregistration(
                self.preregistration,
                v1_preregistration=self.v1_preregistration,
                train=self.train,
                validation=self.validation,
                source_hashes=self.source_hashes,
            ),
            self.preregistration,
        )
        report = self._validate_delta(self.preregistration)
        self.assertEqual(len(report["exact_value_replacements"]), 12)
        self.assertEqual(len(report["preserved_protocol_sources"]), 10)
        self.assertEqual(
            report["added_protocol_sources"],
            ["post_training_contract_v2", "post_training_runner_v2"],
        )
        self.assertEqual(len(report["authorized_new_sections"]), 4)
        self.assertEqual(report["required_gates"], contract.REQUIRED_GATES)
        self.assertEqual(len(contract.REQUIRED_GATES), 13)

    def test_every_authorized_replacement_has_the_exact_required_value(self) -> None:
        for path, required in contract.ALLOWED_VALUE_REPLACEMENTS.items():
            with self.subTest(path=".".join(path)):
                self.assertEqual(_value_at(self.preregistration, path), required)

    def test_all_twelve_replacement_values_are_mandatory_and_exact(self) -> None:
        for path, required in contract.ALLOWED_VALUE_REPLACEMENTS.items():
            with self.subTest(path=".".join(path)):
                changed = copy.deepcopy(self.preregistration)
                if isinstance(required, list):
                    wrong: Any = list(reversed(required))
                elif isinstance(required, int):
                    wrong = required + 1
                else:
                    wrong = f"{required}-tampered"
                _set_at(changed, path, wrong)
                with self.assertRaises(contract.MM003PostTrainingProtocolError):
                    self._validate_delta(changed)

    def test_unlisted_changes_additions_removals_and_containers_are_rejected(self) -> None:
        mutations: list[tuple[str, dict[str, Any]]] = []
        changed = copy.deepcopy(self.preregistration)
        changed["model"]["revision"] = "tampered"
        mutations.append(("preserved leaf drift", changed))
        changed = copy.deepcopy(self.preregistration)
        del changed["training_protocol"]["epochs"]
        mutations.append(("v1 field removal", changed))
        changed = copy.deepcopy(self.preregistration)
        changed["training_protocol"]["unknown"] = True
        mutations.append(("unknown nested addition", changed))
        changed = copy.deepcopy(self.preregistration)
        changed["unknown"] = True
        mutations.append(("unknown root addition", changed))
        changed = copy.deepcopy(self.preregistration)
        changed["model"] = "not-an-object"
        mutations.append(("mapping to scalar", changed))
        changed = copy.deepcopy(self.preregistration)
        changed["decision"] = {"value": changed["decision"]}
        mutations.append(("scalar to mapping", changed))
        for label, candidate in mutations:
            with self.subTest(label=label):
                with self.assertRaises(contract.MM003PostTrainingProtocolError):
                    self._validate_delta(candidate)

    def test_comparator_rejects_a_candidate_self_attested_v1_comparison_base(self) -> None:
        changed_base = copy.deepcopy(self.v1_preregistration)
        changed_candidate = copy.deepcopy(self.preregistration)
        changed_base["model"]["revision"] = "self-attested-base"
        changed_candidate["model"]["revision"] = "self-attested-base"
        with self.assertRaises(contract.MM003PostTrainingProtocolError):
            contract.validate_recovery_delta(
                changed_base,
                changed_candidate,
                train=self.train,
                validation=self.validation,
                source_hashes=self.source_hashes,
            )

    def test_json_leaves_reject_type_coercion_and_signed_zero_drift(self) -> None:
        mutations = []
        changed = copy.deepcopy(self.preregistration)
        changed["authority_contract"]["model_output_has_execution_authority"] = 0
        mutations.append(("false to zero", changed))
        changed = copy.deepcopy(self.preregistration)
        changed["compatibility_smoke"]["completed_before_freeze"] = 1
        mutations.append(("true to one", changed))
        changed = copy.deepcopy(self.preregistration)
        changed["preregistration_version"] = 2.0
        mutations.append(("required int to float", changed))
        changed = copy.deepcopy(self.preregistration)
        changed["training_protocol"]["epochs"] = 3.0
        mutations.append(("preserved int to float", changed))
        changed = copy.deepcopy(self.preregistration)
        changed["training_protocol"]["weight_decay"] = -0.0
        mutations.append(("preserved positive to negative zero", changed))
        for label, candidate in mutations:
            with self.subTest(label=label):
                with self.assertRaises(contract.MM003PostTrainingProtocolError):
                    self._validate_delta(candidate)
                with self.assertRaises(contract.MM003PostTrainingProtocolError):
                    contract.validate_preregistration(
                        candidate,
                        v1_preregistration=self.v1_preregistration,
                        train=self.train,
                        validation=self.validation,
                        source_hashes=self.source_hashes,
                    )

    def test_protocol_source_closure_rejects_drift_removal_extra_or_wide_receipt(self) -> None:
        sources_path = ("source_lineage", "protocol_sources")
        old_source = contract.V1_PROTOCOL_SOURCE_KEYS[0]
        mutations: list[tuple[str, dict[str, Any]]] = []
        changed = copy.deepcopy(self.preregistration)
        changed["source_lineage"]["protocol_sources"][old_source]["sha256"] = (
            "sha256:" + "0" * 64
        )
        mutations.append(("old source hash drift", changed))
        changed = copy.deepcopy(self.preregistration)
        changed["source_lineage"]["protocol_sources"][
            "post_training_contract_v2"
        ]["sha256"] = "sha256:" + "0" * 64
        mutations.append(("candidate self-reported new source hash", changed))
        changed = copy.deepcopy(self.preregistration)
        del changed["source_lineage"]["protocol_sources"][old_source]
        mutations.append(("old source removal", changed))
        changed = copy.deepcopy(self.preregistration)
        changed["source_lineage"]["protocol_sources"]["third_v2_source"] = {
            "path": "src/third.py",
            "sha256": "sha256:" + "0" * 64,
        }
        mutations.append(("third source", changed))
        changed = copy.deepcopy(self.preregistration)
        changed["source_lineage"]["protocol_sources"][
            "post_training_contract_v2"
        ]["extra"] = True
        mutations.append(("new source receipt extra field", changed))
        for label, candidate in mutations:
            with self.subTest(label=label, path=sources_path):
                with self.assertRaises(contract.MM003PostTrainingProtocolError):
                    self._validate_delta(candidate)
        self_attested = copy.deepcopy(self.preregistration)
        self_attested["source_lineage"]["protocol_sources"][
            "post_training_runner_v2"
        ]["sha256"] = "sha256:" + "0" * 64
        with self.assertRaises(contract.MM003PostTrainingProtocolError):
            contract.validate_preregistration(
                self_attested,
                v1_preregistration=self.v1_preregistration,
                train=self.train,
                validation=self.validation,
                source_hashes=self.source_hashes,
            )

    def test_four_new_sections_are_closed_exact_and_mandatory(self) -> None:
        for path in contract.AUTHORIZED_NEW_SECTION_PATHS:
            with self.subTest(path=".".join(path)):
                changed = copy.deepcopy(self.preregistration)
                parent = changed
                for segment in path[:-1]:
                    parent = parent[segment]
                del parent[path[-1]]
                with self.assertRaises(contract.MM003PostTrainingProtocolError):
                    self._validate_delta(changed)
        changed = copy.deepcopy(self.preregistration)
        changed["prompt_projection"]["extra"] = True
        with self.assertRaises(contract.MM003PostTrainingProtocolError):
            self._validate_delta(changed)
        changed = copy.deepcopy(self.preregistration)
        changed["source_lineage"]["v1_failure_lineage"]["v1_failure_receipt"][
            "bytes"
        ] += 1
        with self.assertRaises(contract.MM003PostTrainingProtocolError):
            self._validate_delta(changed)

    def test_prompt_registry_and_projection_cover_all_27_records_without_leakage(self) -> None:
        records = [*self.train["records"], *self.validation["records"]]
        self.assertEqual(len(records), 27)
        self.assertEqual(len(contract.POST_TRAINING_CASE_MODES), 27)
        self.assertEqual(
            [record["case_id"] for record in records],
            [item["case_id"] for item in self.preregistration["prompt_receipts"]["records"]],
        )
        for record in records:
            with self.subTest(case_id=record["case_id"]):
                projected = contract.project_training_prompt(record)
                self.assertEqual(list(projected), contract.PROMPT_PAYLOAD_ROOT_FIELDS)
                self.assertNotIn("family_id", projected)
                self.assertNotIn("training_repeat_group", projected)
                self.assertNotIn("target", projected)
                self.assertNotIn("screenshot_regions", projected["observation"])
                expected_observation_keys = {"ocr_text", "grounding_cue"}
                if record["observation_mode"] in {"uia_only", "fused"}:
                    expected_observation_keys.add("uia_controls")
                self.assertEqual(set(projected["observation"]), expected_observation_keys)
                prompt = contract.render_training_input(record)
                self.assertTrue(prompt.startswith("SYNTHETIC_CASE="))
                parsed = json.loads(prompt.removeprefix("SYNTHETIC_CASE="))
                self.assertEqual(parsed, projected)

    def test_prompt_builder_rejects_fixture_id_mode_record_or_order_tamper(self) -> None:
        changed_record = copy.deepcopy(self.train["records"][0])
        changed_record["family_id"] = "secret-sentinel"
        with self.assertRaises(contract.MM003PostTrainingProtocolError):
            contract.render_training_input(changed_record)

        changed_train = copy.deepcopy(self.train)
        changed_train["records"][0]["observation_mode"] = "fused"
        with self.assertRaises(contract.MM003PostTrainingProtocolError):
            contract.expected_prompt_receipts(changed_train, self.validation)

        changed_train = copy.deepcopy(self.train)
        changed_train["records"][1]["case_id"] = changed_train["records"][0]["case_id"]
        with self.assertRaises(contract.MM003PostTrainingProtocolError):
            contract.expected_prompt_receipts(changed_train, self.validation)

        changed_train = copy.deepcopy(self.train)
        changed_train["records"][0], changed_train["records"][1] = (
            changed_train["records"][1],
            changed_train["records"][0],
        )
        with self.assertRaises(contract.MM003PostTrainingProtocolError):
            contract.expected_prompt_receipts(changed_train, self.validation)

    def test_prompt_receipts_bytes_hash_order_and_aggregate_are_recomputed(self) -> None:
        expected = contract.expected_prompt_receipts(self.train, self.validation)
        self.assertEqual(self.preregistration["prompt_receipts"], expected)
        self.assertEqual(len(expected["records"]), 27)
        for record, receipt in zip(
            [*self.train["records"], *self.validation["records"]],
            expected["records"],
            strict=True,
        ):
            payload = contract.render_training_input(record).encode("utf-8")
            self.assertEqual(receipt["bytes"], len(payload))
            self.assertEqual(receipt["sha256"], contract.sha256_bytes(payload))
            self.assertEqual(
                set(receipt), {"case_id", "observation_mode", "bytes", "sha256"}
            )
        self.assertEqual(
            expected["aggregate_sha256"],
            contract.sha256_bytes(
                contract.PROMPT_RECEIPT_DOMAIN
                + contract.canonical_json_bytes(expected["records"])
            ),
        )

    def test_prompt_receipt_or_projection_tamper_fails_preregistration(self) -> None:
        mutations = []
        changed = copy.deepcopy(self.preregistration)
        changed["prompt_receipts"]["records"][0]["bytes"] += 1
        mutations.append(changed)
        changed = copy.deepcopy(self.preregistration)
        changed["prompt_receipts"]["records"].reverse()
        mutations.append(changed)
        changed = copy.deepcopy(self.preregistration)
        changed["prompt_receipts"]["aggregate_sha256"] = "sha256:" + "0" * 64
        mutations.append(changed)
        changed = copy.deepcopy(self.preregistration)
        changed["prompt_projection"]["registry_records"] = 26
        mutations.append(changed)
        for candidate in mutations:
            with self.subTest():
                with self.assertRaises(contract.MM003PostTrainingProtocolError):
                    contract.validate_preregistration(
                        candidate,
                        v1_preregistration=self.v1_preregistration,
                        train=self.train,
                        validation=self.validation,
                        source_hashes=self.source_hashes,
                    )

    def test_baseline_ground_registry_is_not_extended_or_mutated(self) -> None:
        before = dict(ground_v1.CASE_MODES)
        for record in [*self.train["records"], *self.validation["records"]]:
            contract.render_training_input(record)
        self.assertEqual(ground_v1.CASE_MODES, before)
        self.assertTrue(all(not key.startswith("pt-") for key in ground_v1.CASE_MODES))
        self.assertEqual(len(ground_v1.CASE_MODES), 9)

    def test_lineage_byte_or_report_tamper_is_rejected(self) -> None:
        v1_payload = (ROOT / contract.V1_PREREGISTRATION_RECEIPT["path"]).read_bytes()
        failure_payload = (ROOT / contract.V1_FAILURE_RECEIPT["path"]).read_bytes()
        classification_payload = (
            ROOT / contract.V1_FAILURE_CLASSIFICATION_RECEIPT["path"]
        ).read_bytes()
        with self.assertRaises(contract.MM003PostTrainingProtocolError):
            contract.validate_recovery_lineage_payloads(
                v1_preregistration_payload=v1_payload,
                v1_failure_payload=failure_payload + b" ",
                v1_failure_classification_payload=classification_payload,
            )
        with self.assertRaises(contract.MM003PostTrainingProtocolError):
            contract.validate_recovery_lineage_payloads(
                v1_preregistration_payload=v1_payload,
                v1_failure_payload=failure_payload,
                v1_failure_classification_payload=classification_payload.replace(
                    contract.V1_FAILURE_CLASSIFICATION_RECEIPT[
                        "report_digest"
                    ].encode(),
                    ("sha256:" + "0" * 64).encode(),
                    1,
                ),
            )

    def test_prompt_preflight_failure_precedes_model_manifest_dependency_and_cuda(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output_dir = root / contract.RUN_OUTPUT_ROOT
            preregistration_path = root / "preregistration.json"
            preregistration_path.parent.mkdir(parents=True, exist_ok=True)
            preregistration_path.write_bytes(
                contract.artifact_json_bytes(self.preregistration)
            )
            secret = "must-not-appear-in-failure-receipt"
            failure = contract.MM003PostTrainingProtocolError(
                "PROMPT_RECEIPT_MISMATCH", "$.prompt_receipts", secret
            )
            with (
                mock.patch.object(runner, "ROOT", root),
                mock.patch.object(
                    runner, "_load_recovery_lineage", return_value=self.lineage
                ),
                mock.patch.object(
                    runner,
                    "_validate_protocol_sources",
                    return_value=self.source_hashes,
                ),
                mock.patch.object(runner, "_validate_local_dependency_wheel"),
                mock.patch.object(
                    runner, "load_and_validate_inputs", return_value=self.inputs
                ),
                mock.patch.object(
                    runner.contract,
                    "validate_prompt_preflight",
                    side_effect=failure,
                ),
                mock.patch.object(
                    runner.base_runner, "model_file_manifest"
                ) as model_manifest,
                mock.patch.object(runner, "_load_ml_dependencies") as dependencies,
            ):
                with self.assertRaises(contract.MM003PostTrainingProtocolError):
                    runner.execute_frozen_protocol(
                        model_snapshot=root / "model",
                        preregistration_path=preregistration_path,
                        protocol_freeze_commit="a" * 40,
                        output_dir=output_dir,
                    )
            model_manifest.assert_not_called()
            dependencies.assert_not_called()
            self.assertEqual([path.name for path in output_dir.iterdir()], ["failure.json"])
            payload = (output_dir / "failure.json").read_bytes()
            self.assertNotIn(secret.encode(), payload)
            receipt = contract.parse_strict_json_bytes(payload, location="$.failure")
            self.assertEqual(receipt["failure_version"], 2)
            self.assertEqual(receipt["stage"], "training_prompt_preflight")
            self.assertEqual(receipt["exception_code"], "PROMPT_RECEIPT_MISMATCH")
            self.assertEqual(receipt["exception_location"], "$.prompt_receipts")
            self.assertEqual(receipt["retry_count"], 0)
            self.assertFalse(receipt["formal_gate_passed"])
            self.assertTrue(all(value is False for value in receipt["claims"].values()))

    def test_later_stage_failures_write_bound_v2_receipts_without_messages(self) -> None:
        preregistration_payload = contract.artifact_json_bytes(self.preregistration)
        expected_sha256 = contract.sha256_bytes(preregistration_payload)
        for expected_stage in (
            "training",
            "independent_adapter_load_and_eval",
            "resource_accounting",
            "evidence",
        ):
            with self.subTest(stage=expected_stage), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                output_dir = root / contract.RUN_OUTPUT_ROOT
                preregistration_path = root / "preregistration.json"
                preregistration_path.write_bytes(preregistration_payload)
                fake_torch = mock.Mock()
                fake_torch.cuda.synchronize.return_value = None
                fake_torch.cuda.max_memory_allocated.return_value = 0
                fake_torch.cuda.max_memory_reserved.return_value = 0
                with (
                    mock.patch.object(runner, "ROOT", root),
                    mock.patch.object(
                        runner, "_load_recovery_lineage", return_value=self.lineage
                    ),
                    mock.patch.object(
                        runner,
                        "_validate_protocol_sources",
                        return_value=self.source_hashes,
                    ),
                    mock.patch.object(runner, "_validate_local_dependency_wheel"),
                    mock.patch.object(
                        runner, "load_and_validate_inputs", return_value=self.inputs
                    ),
                    mock.patch.object(
                        runner.base_runner,
                        "model_file_manifest",
                        return_value=self.preregistration["model"]["files"],
                    ),
                    mock.patch.object(
                        runner,
                        "_load_ml_dependencies",
                        return_value=(object(), fake_torch),
                    ),
                    mock.patch.object(
                        runner,
                        "observed_environment",
                        return_value=contract.LOCKED_ENVIRONMENT,
                    ),
                    mock.patch.object(
                        runner,
                        "_train_adapter",
                        return_value={"training": True},
                    ) as train_adapter,
                    mock.patch.object(
                        runner,
                        "_independent_load_and_eval",
                        return_value={"evaluation": True},
                    ) as independent_eval,
                    mock.patch.object(runner, "build_evidence") as build_evidence,
                ):
                    error = RuntimeError(f"secret {expected_stage} message")
                    if expected_stage == "training":
                        train_adapter.side_effect = error
                    elif expected_stage == "independent_adapter_load_and_eval":
                        independent_eval.side_effect = error
                    elif expected_stage == "resource_accounting":
                        fake_torch.cuda.synchronize.side_effect = error
                    else:
                        build_evidence.side_effect = error
                    with self.assertRaisesRegex(RuntimeError, expected_stage):
                        runner.execute_frozen_protocol(
                            model_snapshot=root / "model",
                            preregistration_path=preregistration_path,
                            protocol_freeze_commit="a" * 40,
                            output_dir=output_dir,
                        )
                payload = (output_dir / "failure.json").read_bytes()
                self.assertNotIn(b"secret", payload)
                receipt = contract.parse_strict_json_bytes(
                    payload, location="$.failure"
                )
                self.assertEqual(receipt["failure_version"], 2)
                self.assertEqual(receipt["stage"], expected_stage)
                self.assertEqual(receipt["preregistration_sha256"], expected_sha256)
                self.assertEqual(receipt["exception_type"], "RuntimeError")
                self.assertIsNone(receipt["exception_code"])
                self.assertIsNone(receipt["exception_location"])
                self.assertEqual(receipt["retry_count"], 0)
                self.assertFalse(receipt["formal_gate_passed"])
                self.assertFalse(receipt["runtime_eligible"])

    def test_failure_diagnostics_are_bounded_and_generic_errors_leak_nothing(self) -> None:
        self.assertEqual(
            runner._safe_exception_diagnostic(RuntimeError("secret path C:\\hidden")),
            ("RuntimeError", None, None),
        )
        unsafe = contract.MM003PostTrainingProtocolError(
            "unsafe-code", "C:\\hidden", "secret"
        )
        self.assertEqual(
            runner._safe_exception_diagnostic(unsafe),
            ("MM003ProtocolError", None, None),
        )

    def test_prepare_writes_then_checks_the_exact_recovery_preregistration(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "preregistration.json"
            with mock.patch.object(
                runner.base_runner,
                "model_file_manifest",
                return_value=self.v1_preregistration["model"]["files"],
            ), mock.patch.object(runner, "_validate_local_dependency_wheel"):
                written = runner.prepare_protocol(
                    model_snapshot=Path(temporary),
                    output_path=output,
                    freeze_status="frozen",
                    check=False,
                )
                checked = runner.prepare_protocol(
                    model_snapshot=Path(temporary),
                    output_path=output,
                    freeze_status="frozen",
                    check=True,
                )
        self.assertEqual(written, checked)
        self.assertEqual(written["source_files"], 12)
        self.assertEqual(written["train_records"], 18)
        self.assertEqual(written["validation_records"], 9)
        self.assertTrue(written["valid"])

    def test_formal_invocation_rejection_does_not_consume_v1_or_v2_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            v2_output = root / contract.RUN_OUTPUT_ROOT
            wrong_output = root / "wrong-output"
            with mock.patch.object(runner, "ROOT", root):
                with self.assertRaisesRegex(RuntimeError, "lowercase 40-hex"):
                    runner.execute_frozen_protocol(
                        model_snapshot=root / "model",
                        preregistration_path=root / "preregistration.json",
                        protocol_freeze_commit="invalid",
                        output_dir=v2_output,
                    )
                self.assertFalse(v2_output.exists())
                with self.assertRaisesRegex(RuntimeError, "differs from frozen protocol"):
                    runner.execute_frozen_protocol(
                        model_snapshot=root / "model",
                        preregistration_path=root / "preregistration.json",
                        protocol_freeze_commit="a" * 40,
                        output_dir=wrong_output,
                    )
                self.assertFalse(v2_output.exists())
                self.assertFalse(wrong_output.exists())
                v2_output.mkdir(parents=True)
                marker = v2_output / "preserve.txt"
                marker.write_text("preserve", encoding="utf-8")
                with self.assertRaisesRegex(RuntimeError, "must be absent"):
                    runner.execute_frozen_protocol(
                        model_snapshot=root / "model",
                        preregistration_path=root / "preregistration.json",
                        protocol_freeze_commit="a" * 40,
                        output_dir=v2_output,
                    )
                self.assertEqual(list(v2_output.iterdir()), [marker])

    def test_evidence_requires_the_exact_prompt_gate_and_remains_outcome_neutral(self) -> None:
        payload = contract.artifact_json_bytes(self.preregistration)
        training = {
            "protocol": {
                "preregistration_sha256": contract.sha256_bytes(payload),
                "freeze_commit": "a" * 40,
            },
            "data": {"train_records": 18, "validation_records": 9},
            "execution": {
                "fresh_train_model_loads": 1,
                "full_training_runs": 1,
                "network_used": False,
                "retry_count": 0,
                "training_completed": True,
            },
            "adapter_manifest": [
                {"path": name, "bytes": 1, "sha256": "sha256:" + "1" * 64}
                for name in self.preregistration["outputs"]["required_adapter_files"]
            ],
        }
        evaluation = {
            "execution": {
                "fresh_base_loads": 1,
                "full_eval_runs": 1,
                "generate_calls": 9,
                "independent_adapter_loads": 1,
                "network_used": False,
                "retry_count": 0,
            },
            "score": {"case_count": 9},
        }
        prompt_preflight = contract.validate_prompt_preflight(
            self.preregistration, train=self.train, validation=self.validation
        )
        evidence = runner.build_evidence(
            preregistration=self.preregistration,
            preregistration_payload=payload,
            protocol_freeze_commit="a" * 40,
            training=training,
            evaluation=evaluation,
            environment=contract.LOCKED_ENVIRONMENT,
            model_manifest=self.preregistration["model"]["files"],
            isolation_audit=self.inputs["isolation_audit"],
            prompt_preflight=prompt_preflight,
            lifecycle_resources={
                "elapsed_seconds": 100.0,
                "peak_gpu_allocated_bytes": 10_000_000_000,
                "peak_gpu_reserved_bytes": 11_000_000_000,
            },
        )
        self.assertTrue(evidence["formal_gate_passed"])
        self.assertEqual(list(evidence["gates"]), contract.REQUIRED_GATES)
        self.assertTrue(evidence["gates"][contract.RECOVERY_PROMPT_GATE])
        self.assertEqual(evidence["prompt_preflight"], prompt_preflight)
        self.assertEqual(evidence["next_gate"], contract.SUCCESS_NEXT_GATE_ID)
        self.assertFalse(evidence["claims"]["quality_improved"])
        self.assertFalse(evidence["runtime_eligible"])

        changed_preflight = copy.deepcopy(prompt_preflight)
        changed_preflight["records_checked"] = 26
        failed = runner.build_evidence(
            preregistration=self.preregistration,
            preregistration_payload=payload,
            protocol_freeze_commit="a" * 40,
            training=training,
            evaluation=evaluation,
            environment=contract.LOCKED_ENVIRONMENT,
            model_manifest=self.preregistration["model"]["files"],
            isolation_audit=self.inputs["isolation_audit"],
            prompt_preflight=changed_preflight,
            lifecycle_resources={
                "elapsed_seconds": 100.0,
                "peak_gpu_allocated_bytes": 10_000_000_000,
                "peak_gpu_reserved_bytes": 11_000_000_000,
            },
        )
        self.assertFalse(failed["formal_gate_passed"])
        self.assertTrue(all(value is False for value in failed["claims"].values()))
        self.assertIsNone(failed["next_gate"])

    def test_runner_identity_and_prompt_order_are_v2_only(self) -> None:
        source = (ROOT / "scripts/run_mm003_qlora_post_training_v2.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("mm003-qlora-sft-v1", source)
        self.assertNotIn("result-review-v1", source)
        preflight = source.index('stage = "training_prompt_preflight"')
        model_manifest = source.index('stage = "model_manifest"', preflight)
        dependency_import = source.index('stage = "dependency_import"', model_manifest)
        training = source.index('stage = "training"', dependency_import)
        self.assertLess(preflight, model_manifest)
        self.assertLess(model_manifest, dependency_import)
        self.assertLess(dependency_import, training)
        self.assertIn("contract.ADAPTER_MODEL_ID", source)
        self.assertIn("contract.SUCCESS_NEXT_GATE_ID", source)

    def test_tracked_preregistration_matches_current_sources_when_present(self) -> None:
        path = ROOT / contract.PREREGISTRATION_PATH
        if not path.exists():
            self.skipTest("tracked recovery preregistration is frozen after sources stabilize")
        observed = contract.parse_strict_json_bytes(
            path.read_bytes(), location="$.preregistration"
        )
        self.assertEqual(observed, self.preregistration)
        self.assertEqual(
            contract.validate_preregistration(
                observed,
                v1_preregistration=self.v1_preregistration,
                train=self.train,
                validation=self.validation,
                source_hashes=self.source_hashes,
            ),
            observed,
        )


if __name__ == "__main__":
    unittest.main()
