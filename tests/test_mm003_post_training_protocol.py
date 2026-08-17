from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SRC))

from fullcycle_bridge import mm003_post_training_protocol as contract  # noqa: E402
from scripts import build_mm003_post_training_fixture as builder  # noqa: E402
from scripts import run_mm003_qlora_post_training as runner  # noqa: E402


class MM003PostTrainingProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.inputs = runner.load_and_validate_inputs()
        cls.model_files = [
            {
                "path": name,
                "bytes": size,
                "sha256": contract.MODEL_WEIGHT_SHA256.get(
                    name, "sha256:" + f"{index + 1:064x}"
                ),
            }
            for index, (name, size) in enumerate(
                sorted(contract.MODEL_FILE_SIZES.items())
            )
        ]
        cls.preregistration = contract.expected_preregistration(
            freeze_status="frozen",
            model_files=cls.model_files,
            train_receipt=cls.inputs["train_receipt"],
            validation_receipt=cls.inputs["validation_receipt"],
            screenshot_receipts=cls.inputs["training_screenshot_receipts"],
            eval_screenshot_receipts=cls.inputs["eval_screenshot_receipts"],
            source_hashes=runner.protocol_source_hashes(),
            isolation_audit=cls.inputs["isolation_audit"],
        )

    def test_dataset_grid_is_balanced_training_only_and_exact(self) -> None:
        for split, count, repeats in (("train", 18, 2), ("validation", 9, 1)):
            with self.subTest(split=split):
                dataset = contract.expected_dataset(split)
                self.assertEqual(
                    contract.validate_dataset(dataset, split=split), dataset
                )
                self.assertEqual(len(dataset["records"]), count)
                grid = Counter(
                    (record["observation_mode"], record["target"]["disposition"])
                    for record in dataset["records"]
                )
                self.assertEqual(set(grid.values()), {repeats})
                self.assertFalse(dataset["provenance"]["mm002_eval_gold_used"])
                self.assertFalse(
                    dataset["provenance"]["model_output_has_execution_authority"]
                )
                self.assertTrue(dataset["provenance"]["runtime_dispatch_required"])
                self.assertEqual(
                    dataset["split_policy"]["optimizer_use"], split == "train"
                )

    def test_every_target_is_accepted_by_the_frozen_compiler(self) -> None:
        for split in ("train", "validation"):
            for record in contract.expected_dataset(split)["records"]:
                with self.subTest(case_id=record["case_id"]):
                    raw = contract.render_training_target(record)
                    self.assertEqual(
                        contract.baseline.compile_raw_prediction(raw, record),
                        record["target"],
                    )

    def test_renderer_is_deterministic_unique_and_fixture_bound(self) -> None:
        receipts = contract.expected_screenshot_receipts()
        self.assertEqual(len(receipts), 18)
        self.assertEqual(len({item["sha256"] for item in receipts}), 18)
        for receipt in receipts:
            path = ROOT / receipt["path"]
            payload = path.read_bytes()
            self.assertTrue(payload.startswith(b"\x89PNG\r\n\x1a\n"))
            self.assertEqual(len(payload), receipt["bytes"])
            self.assertEqual(contract.sha256_bytes(payload), receipt["sha256"])

    def test_fixture_builder_check_recomputes_all_tracked_bytes(self) -> None:
        self.assertEqual(builder.main.__module__, builder.__name__)
        for split, relative in (
            ("train", contract.TRAIN_DATASET_PATH),
            ("validation", contract.VALIDATION_DATASET_PATH),
        ):
            expected = contract.artifact_json_bytes(contract.expected_dataset(split))
            self.assertEqual((ROOT / relative).read_bytes(), expected)

    def test_eval_isolation_covers_all_exact_identity_classes(self) -> None:
        audit = self.inputs["isolation_audit"]
        self.assertTrue(audit["passed"])
        self.assertEqual(
            audit["overlaps"],
            {
                "case_ids": [],
                "family_ids": [],
                "instructions": [],
                "model_inputs": [],
                "targets": [],
                "screenshots": [],
                "train_validation_families": [],
            },
        )
        first = self.inputs["training_screenshot_receipts"][0]
        collided = contract.audit_eval_isolation(
            train=self.inputs["train"],
            validation=self.inputs["validation"],
            eval_suite=self.inputs["eval_suite"],
            eval_screenshot_payloads={"collision": (ROOT / first["path"]).read_bytes()},
        )
        self.assertFalse(collided["passed"])
        self.assertEqual(collided["overlaps"]["screenshots"], [first["sha256"]])

    def test_preregistration_is_outcome_neutral_and_recomputed(self) -> None:
        self.assertEqual(
            contract.validate_preregistration(self.preregistration),
            self.preregistration,
        )
        self.assertFalse(
            self.preregistration["formal_gate"]["quality_threshold_required"]
        )
        self.assertFalse(self.preregistration["claims"]["training_executed"])
        self.assertFalse(self.preregistration["claims"]["model_evaluated"])
        self.assertFalse(self.preregistration["runtime_eligible"])
        changed = copy.deepcopy(self.preregistration)
        changed["claims"]["promotion_eligible"] = True
        with self.assertRaisesRegex(
            contract.MM003PostTrainingProtocolError,
            "PREREGISTRATION_RECOMPUTATION_MISMATCH",
        ):
            contract.validate_preregistration(changed)

    def test_prepare_writes_then_checks_the_exact_preregistration(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "preregistration.json"
            with mock.patch.object(
                runner.base_runner,
                "model_file_manifest",
                return_value=self.model_files,
            ), mock.patch.object(
                runner,
                "_validate_local_dependency_wheel",
            ) as validate_dependency_wheel:
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
        self.assertEqual(validate_dependency_wheel.call_count, 2)
        self.assertEqual(written, checked)
        self.assertTrue(written["eval_isolation"])
        self.assertEqual(written["train_records"], 18)

    def test_formal_preflight_failure_writes_fail_closed_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output_dir = root / "work/training-runs/mm003-qlora-sft-v1"
            with mock.patch.object(runner, "ROOT", root), mock.patch.object(
                runner,
                "_load_ml_dependencies",
            ) as load_ml_dependencies:
                with self.assertRaises(FileNotFoundError):
                    runner.execute_frozen_protocol(
                        model_snapshot=root / "model",
                        preregistration_path=root / "missing-preregistration.json",
                        protocol_freeze_commit="a" * 40,
                        output_dir=output_dir,
                    )
            load_ml_dependencies.assert_not_called()
            self.assertEqual(
                sorted(path.name for path in output_dir.iterdir()),
                ["failure.json"],
            )
            failure = contract.parse_strict_json_bytes(
                (output_dir / "failure.json").read_bytes(),
                location="$.failure",
            )
        self.assertEqual(failure["stage"], "preregistration")
        self.assertEqual(failure["exception_type"], "FileNotFoundError")
        self.assertIsNone(failure["preregistration_sha256"])
        self.assertEqual(failure["retry_count"], 0)
        self.assertFalse(failure["formal_gate_passed"])
        self.assertTrue(all(value is False for value in failure["claims"].values()))
        self.assertFalse(failure["runtime_eligible"])

    def test_formal_invocation_rejection_does_not_consume_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output_dir = root / "work/training-runs/mm003-qlora-sft-v1"
            wrong_output_dir = root / "wrong-output"
            with mock.patch.object(runner, "ROOT", root):
                with self.assertRaisesRegex(
                    RuntimeError,
                    "protocol freeze commit must be a lowercase 40-hex commit",
                ):
                    runner.execute_frozen_protocol(
                        model_snapshot=root / "model",
                        preregistration_path=root / "preregistration.json",
                        protocol_freeze_commit="invalid",
                        output_dir=output_dir,
                    )
                self.assertFalse(output_dir.exists())

                with self.assertRaisesRegex(
                    RuntimeError,
                    "output directory differs from frozen protocol",
                ):
                    runner.execute_frozen_protocol(
                        model_snapshot=root / "model",
                        preregistration_path=root / "preregistration.json",
                        protocol_freeze_commit="a" * 40,
                        output_dir=wrong_output_dir,
                    )
                self.assertFalse(output_dir.exists())
                self.assertFalse(wrong_output_dir.exists())

                output_dir.mkdir(parents=True)
                marker = output_dir / "user-owned.txt"
                marker.write_text("preserve", encoding="utf-8")
                with self.assertRaisesRegex(
                    RuntimeError,
                    "output directory must be absent before model load",
                ):
                    runner.execute_frozen_protocol(
                        model_snapshot=root / "model",
                        preregistration_path=root / "preregistration.json",
                        protocol_freeze_commit="a" * 40,
                        output_dir=output_dir,
                    )
                self.assertEqual(marker.read_text(encoding="utf-8"), "preserve")
                self.assertEqual(list(output_dir.iterdir()), [marker])

    def test_later_stage_failures_write_exact_preregistration_receipt(self) -> None:
        preregistration_path = ROOT / contract.PREREGISTRATION_PATH
        preregistration_payload = preregistration_path.read_bytes()
        tracked_preregistration = contract.parse_strict_json_bytes(
            preregistration_payload,
            location="$.preregistration",
        )
        expected_sha256 = contract.sha256_bytes(preregistration_payload)
        for expected_stage in (
            "training",
            "independent_adapter_load_and_eval",
            "resource_accounting",
            "evidence",
        ):
            with self.subTest(stage=expected_stage), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                output_dir = root / "work/training-runs/mm003-qlora-sft-v1"
                fake_torch = mock.Mock()
                fake_torch.cuda.synchronize.return_value = None
                fake_torch.cuda.max_memory_allocated.return_value = 0
                fake_torch.cuda.max_memory_reserved.return_value = 0
                with (
                    mock.patch.object(runner, "ROOT", root),
                    mock.patch.object(runner, "_validate_protocol_sources"),
                    mock.patch.object(runner, "_validate_local_dependency_wheel"),
                    mock.patch.object(
                        runner,
                        "load_and_validate_inputs",
                        return_value=self.inputs,
                    ),
                    mock.patch.object(runner, "_validate_preregistered_inputs"),
                    mock.patch.object(
                        runner.base_runner,
                        "model_file_manifest",
                        return_value=tracked_preregistration["model"]["files"],
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
                    error = RuntimeError(f"injected {expected_stage} failure")
                    if expected_stage == "training":
                        train_adapter.side_effect = error
                    elif expected_stage == "independent_adapter_load_and_eval":
                        independent_eval.side_effect = error
                    elif expected_stage == "resource_accounting":
                        fake_torch.cuda.synchronize.side_effect = error
                    else:
                        build_evidence.side_effect = error
                    with self.assertRaisesRegex(RuntimeError, f"injected {expected_stage}"):
                        runner.execute_frozen_protocol(
                            model_snapshot=root / "model",
                            preregistration_path=preregistration_path,
                            protocol_freeze_commit="a" * 40,
                            output_dir=output_dir,
                        )
                failure = contract.parse_strict_json_bytes(
                    (output_dir / "failure.json").read_bytes(),
                    location="$.failure",
                )
                self.assertEqual(failure["stage"], expected_stage)
                self.assertEqual(failure["exception_type"], "RuntimeError")
                self.assertEqual(failure["preregistration_sha256"], expected_sha256)
                self.assertEqual(failure["retry_count"], 0)
                self.assertFalse(failure["formal_gate_passed"])
                self.assertFalse(failure["runtime_eligible"])

    def test_runner_requires_save_then_fresh_independent_reload(self) -> None:
        source = (ROOT / "scripts/run_mm003_qlora_post_training.py").read_text(
            encoding="utf-8"
        )
        run_function = source.index("def execute_frozen_protocol(")
        mkdir = source.index("output_dir.mkdir", run_function)
        timer_start = source.index("lifecycle_started = time.perf_counter()", mkdir)
        train_call = source.index("training = _train_adapter(")
        eval_call = source.index("evaluation = _independent_load_and_eval(")
        resource_accounting = source.index(
            'stage = "resource_accounting"', eval_call
        )
        peak_allocated = source.index(
            "peak_gpu_allocated_bytes = int(torch.cuda.max_memory_allocated())",
            resource_accounting,
        )
        peak_reserved = source.index(
            "peak_gpu_reserved_bytes = int(torch.cuda.max_memory_reserved())",
            peak_allocated,
        )
        timer_stop = source.index(
            '"elapsed_seconds": time.perf_counter() - lifecycle_started',
            peak_reserved,
        )
        evidence_stage = source.index('stage = "evidence"', timer_stop)
        self.assertLess(mkdir, timer_start)
        self.assertLess(timer_start, train_call)
        self.assertLess(train_call, eval_call)
        self.assertLess(eval_call, resource_accounting)
        self.assertLess(resource_accounting, peak_allocated)
        self.assertLess(peak_allocated, peak_reserved)
        self.assertLess(peak_reserved, timer_stop)
        self.assertLess(timer_stop, evidence_stage)
        train_function = source.index("def _train_adapter(")
        save = source.index("model.save_pretrained", train_function)
        delete = source.index("del optimizer, scheduler, model, processor", save)
        eval_function = source.index("def _independent_load_and_eval(")
        fresh_base = source.index(
            "base_model = model_class.from_pretrained", eval_function
        )
        adapter_load = source.index("peft_model_class.from_pretrained", fresh_base)
        self.assertLess(save, delete)
        self.assertLess(delete, eval_function)
        self.assertLess(fresh_base, adapter_load)
        self.assertNotIn(
            "gui_grounding_eval_v1/valid/suite.json",
            (ROOT / "scripts/smoke_mm003_qlora_backend.py").read_text(encoding="utf-8"),
        )

    def test_evidence_is_outcome_neutral_and_caps_full_lifecycle(self) -> None:
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
        evidence = runner.build_evidence(
            preregistration=self.preregistration,
            preregistration_payload=payload,
            protocol_freeze_commit="a" * 40,
            training=training,
            evaluation=evaluation,
            environment=contract.LOCKED_ENVIRONMENT,
            model_manifest=self.model_files,
            isolation_audit=self.inputs["isolation_audit"],
            lifecycle_resources={
                "elapsed_seconds": 100.0,
                "peak_gpu_allocated_bytes": 10_000_000_000,
                "peak_gpu_reserved_bytes": 11_000_000_000,
            },
        )
        self.assertTrue(evidence["formal_gate_passed"])
        self.assertTrue(evidence["claims"]["adapter_independently_loadable"])
        self.assertFalse(evidence["claims"]["quality_improved"])
        self.assertFalse(evidence["claims"]["runtime_eligible"])

        over_cap = copy.deepcopy(evidence["resources"])
        over_cap["peak_gpu_reserved_bytes"] = 17_000_000_000
        failed = runner.build_evidence(
            preregistration=self.preregistration,
            preregistration_payload=payload,
            protocol_freeze_commit="a" * 40,
            training=training,
            evaluation=evaluation,
            environment=contract.LOCKED_ENVIRONMENT,
            model_manifest=self.model_files,
            isolation_audit=self.inputs["isolation_audit"],
            lifecycle_resources=over_cap,
        )
        self.assertFalse(failed["formal_gate_passed"])
        self.assertFalse(failed["claims"]["training_executed"])

    def test_tracked_preregistration_matches_current_sources_when_present(self) -> None:
        path = ROOT / contract.PREREGISTRATION_PATH
        if not path.exists():
            self.skipTest("tracked preregistration is created after sources stabilize")
        tracked = contract.parse_strict_json_bytes(
            path.read_bytes(), location="$.preregistration"
        )
        self.assertEqual(contract.validate_preregistration(tracked), tracked)
        self.assertEqual(
            tracked["source_lineage"], self.preregistration["source_lineage"]
        )
        self.assertEqual(tracked["claims"], self.preregistration["claims"])


if __name__ == "__main__":
    unittest.main()
