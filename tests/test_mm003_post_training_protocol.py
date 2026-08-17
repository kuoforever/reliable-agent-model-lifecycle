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
            ):
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
        self.assertTrue(written["eval_isolation"])
        self.assertEqual(written["train_records"], 18)

    def test_runner_requires_save_then_fresh_independent_reload(self) -> None:
        source = (ROOT / "scripts/run_mm003_qlora_post_training.py").read_text(
            encoding="utf-8"
        )
        train_call = source.index("training = _train_adapter(")
        eval_call = source.index("evaluation = _independent_load_and_eval(")
        self.assertLess(train_call, eval_call)
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
