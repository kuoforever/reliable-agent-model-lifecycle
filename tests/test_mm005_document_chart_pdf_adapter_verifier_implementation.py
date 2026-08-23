from __future__ import annotations

import ast
import copy
import json
import subprocess
import sys
import unittest
from collections import Counter
from collections.abc import Mapping
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SRC))

from fullcycle_bridge import (  # noqa: E402
    mm005_document_chart_pdf_adapter_verifier as implementation,
)
from fullcycle_bridge import (  # noqa: E402
    mm005_document_chart_pdf_adapter_verifier_implementation as evidence,
)
from fullcycle_bridge import (  # noqa: E402
    mm005_document_chart_pdf_adapter_verifier_protocol as protocol,
)
from fullcycle_bridge import (  # noqa: E402
    multimodal_environment_adaptation as parent,
)
from scripts import (  # noqa: E402
    prepare_mm005_document_chart_pdf_adapter_verifier_implementation as prepare,
)

EVIDENCE_BYTES = 102_117
EVIDENCE_SHA256 = (
    "sha256:d4cbe61cac4cff60c15e769c35e481ca93f71524b23bf0dad4ddf75095d17bf2"
)


class MM005DocumentChartPdfAdapterVerifierImplementationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.inputs = prepare.implementation_inputs()
        cls.expected_evidence = prepare.build_evidence()
        cls.evidence_payload = evidence.artifact_json_bytes(cls.expected_evidence)
        cls.protocol_value = json.loads(cls.inputs["protocol_payload"])
        cls.records, cls.image_receipts, cls.dataset_receipts = (
            protocol.dataset_context(cls.inputs["output_payloads"])
        )
        cls.records_by_id = {record["record_id"]: record for record in cls.records}
        cls.images = {
            path: cls.inputs["output_payloads"][path] for path in cls.image_receipts
        }

    def test_tracked_evidence_rebuilds_and_validates_exactly(self) -> None:
        tracked = (ROOT / evidence.EVIDENCE_PATH).read_bytes()
        parsed = json.loads(tracked)
        summary = evidence.validate_evidence(parsed, **self.inputs)

        self.assertEqual(tracked, self.evidence_payload)
        self.assertEqual(len(tracked), EVIDENCE_BYTES)
        self.assertEqual(evidence.sha256_bytes(tracked), EVIDENCE_SHA256)
        self.assertEqual(evidence.artifact_json_bytes(parsed), tracked)
        self.assertEqual(parsed, self.expected_evidence)
        self.assertEqual(
            summary.to_dict(),
            {
                "evidence_version": 1,
                "source_receipt_count": 5,
                "record_count": 32,
                "image_count": 32,
                "adapter_projection_count": 32,
                "model_payload_bytes": 31_430,
                "image_bytes": 314_128,
                "verifier_case_count": 160,
                "compiler_valid_count": 96,
                "compiler_invalid_count": 64,
                "positive_case_count": 32,
                "negative_case_count": 128,
                "environment_adapter_implemented": True,
                "environment_adapter_executed": True,
                "verifier_implemented": True,
                "verifier_executed": True,
                "model_evaluated": False,
                "next_gate": evidence.NEXT_GATE,
            },
        )

    def test_protocol_was_merged_first_and_sources_are_exact(self) -> None:
        ancestor = subprocess.run(
            [
                "git",
                "merge-base",
                "--is-ancestor",
                evidence.PROTOCOL_MERGE_COMMIT,
                "HEAD",
            ],
            cwd=ROOT,
            check=False,
        )
        self.assertEqual(ancestor.returncode, 0)
        frozen = subprocess.run(
            [
                "git",
                "show",
                f"{evidence.PROTOCOL_MERGE_COMMIT}:{protocol.PROTOCOL_PATH}",
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout
        self.assertEqual(frozen, self.inputs["protocol_payload"])
        self.assertEqual(
            self.expected_evidence["protocol"]["merge_commit"],
            evidence.PROTOCOL_MERGE_COMMIT,
        )

        sources = self.expected_evidence["implementation_source_receipts"]
        self.assertEqual(set(sources), set(prepare.SOURCE_PATHS))
        for name, relative in prepare.SOURCE_PATHS.items():
            payload = (ROOT / relative).read_bytes()
            self.assertEqual(
                sources[name],
                {
                    "path": relative,
                    "bytes": len(payload),
                    "sha256": evidence.sha256_bytes(payload),
                },
            )

    def test_all_adapter_projections_match_the_frozen_registry(self) -> None:
        frozen = {
            item["record_id"]: item
            for item in self.protocol_value["adapter_projection_registry"]
        }
        executed = {
            item["record_id"]: item
            for item in self.expected_evidence["adapter_implementation"][
                "execution_registry"
            ]
        }
        self.assertEqual(len(frozen), 32)
        self.assertEqual(len(executed), 32)

        for record in self.records:
            adapted = implementation.adapt_record(record, self.images)
            receipt = implementation.projection_receipt(record, adapted)
            projection = adapted.audit_projection()
            model_payload = adapted.model_payload()
            model_bytes = adapted.model_payload_json
            image_binding = projection["image_binding"]

            self.assertEqual(receipt, frozen[record["record_id"]])
            self.assertEqual(set(model_payload), set(implementation.MODEL_PAYLOAD_KEYS))
            self.assertFalse(_contains_forbidden_key(model_payload))
            self.assertNotIn(image_binding["path"].encode("utf-8"), model_bytes)
            self.assertEqual(
                implementation.sha256_bytes(adapted.image_bytes),
                image_binding["sha256"],
            )
            execution = executed[record["record_id"]]
            self.assertEqual(execution["model_payload"], _payload_receipt(model_bytes))
            self.assertEqual(
                execution["image_payload"], _payload_receipt(adapted.image_bytes)
            )
            self.assertEqual(
                execution["projection"],
                _payload_receipt(adapted.audit_projection_json),
            )

            changed_copy = adapted.model_payload()
            changed_copy["record_id"] = "attempted-mutation"
            self.assertNotIn("record_id", adapted.model_payload())

    def test_adapter_rejects_missing_duplicate_tampered_or_unsafe_images(self) -> None:
        record = self.records[0]
        bound_hash = record["observation"]["image_sha256"]
        bound_path = next(
            path
            for path, receipt in self.image_receipts.items()
            if receipt["sha256"] == bound_hash
        )
        bound_payload = self.images[bound_path]

        missing = {
            path: payload for path, payload in self.images.items() if path != bound_path
        }
        with self.assertRaisesRegex(
            implementation.MM005AdapterVerifierError,
            "RECORD_IMAGE_BINDING_INVALID",
        ):
            implementation.adapt_record(record, missing)

        duplicate = {**self.images, "fixtures/mm005/duplicate.png": bound_payload}
        with self.assertRaisesRegex(
            implementation.MM005AdapterVerifierError,
            "RECORD_IMAGE_BINDING_INVALID",
        ):
            implementation.adapt_record(record, duplicate)

        tampered = dict(self.images)
        tampered[bound_path] = bound_payload[:-1] + bytes([bound_payload[-1] ^ 1])
        with self.assertRaisesRegex(
            implementation.MM005AdapterVerifierError,
            "RECORD_IMAGE_BINDING_INVALID",
        ):
            implementation.adapt_record(record, tampered)

        unsafe = {**self.images, "../outside.png": b"not-an-image"}
        with self.assertRaisesRegex(
            implementation.MM005AdapterVerifierError,
            "IMAGE_PATH_INVALID",
        ):
            implementation.adapt_record(record, unsafe)

    def test_compiler_is_independent_and_matches_reference_on_all_edges(self) -> None:
        frozen_outputs = [
            case["raw_output"] for case in self.protocol_value["verifier_case_registry"]
        ]
        adversarial_outputs = [
            None,
            True,
            7,
            "",
            "not-json",
            "[]",
            "\ud800",
            '{"answer":"x","evidence_refs":["page-01"],"page_number":1,"extra":true}',
            '{"answer":"x","answer":"y","evidence_refs":["page-01"],"page_number":1}',
            '{"answer":NaN,"evidence_refs":["page-01"],"page_number":1}',
            '{"answer":"x","evidence_refs":["page-01","page-01"],"page_number":1}',
            '{"answer":"x","evidence_refs":["page-01"],"page_number":true}',
            json.dumps(
                {
                    "answer": "x" * 8_193,
                    "evidence_refs": ["page-01"],
                    "page_number": 1,
                }
            ),
        ]
        for raw_output in [*frozen_outputs, *adversarial_outputs]:
            with self.subTest(raw_output=repr(raw_output)[:100]):
                self.assertEqual(
                    implementation.compile_candidate_output(raw_output),
                    parent.compile_candidate_output(raw_output),
                )

    def test_all_verifier_cases_match_the_frozen_reference(self) -> None:
        observed_distribution: Counter[str] = Counter()
        for case in self.protocol_value["verifier_case_registry"]:
            record = self.records_by_id[case["record_id"]]
            compiled = implementation.compile_candidate_output(case["raw_output"])
            verdict = implementation.verify_candidate(compiled, record)
            observed_distribution[case["case_kind"]] += 1
            self.assertEqual(compiled["valid"], case["compiler_valid"])
            self.assertEqual(compiled["error_code"], case["compiler_error_code"])
            self.assertEqual(verdict, case["verdict"])
        self.assertEqual(
            observed_distribution,
            Counter({kind: 32 for kind in protocol.VERIFIER_CASE_KINDS}),
        )

    def test_verifier_rejects_forged_compiled_objects(self) -> None:
        record = self.records[0]
        expected_raw = evidence.artifact_json_bytes(record["expected_output"]).decode(
            "utf-8"
        )
        compiled = implementation.compile_candidate_output(expected_raw)
        self.assertTrue(
            implementation.verify_candidate(compiled, record)["joint_correct"]
        )

        for forged in (
            {**compiled, "extra": True},
            {**compiled, "compiler_version": True},
            {**compiled, "valid": 1},
            {**compiled, "evidence_refs": [compiled["evidence_refs"][0]] * 2},
            {**compiled, "page_number": 2},
        ):
            with self.subTest(forged=forged):
                verdict = implementation.verify_candidate(forged, record)
                self.assertFalse(verdict["valid_output"])
                self.assertFalse(verdict["joint_correct"])

    def test_answer_normalization_remains_nfc_ascii_space_trim_exact(self) -> None:
        record = self.records[0]
        expected = dict(record["expected_output"])
        spaced = {**expected, "answer": f" {expected['answer']} "}
        tabbed = {**expected, "answer": f"{expected['answer']}\t"}
        self.assertTrue(
            implementation.verify_raw_output(
                evidence.artifact_json_bytes(spaced).decode("utf-8"), record
            )["joint_correct"]
        )
        self.assertFalse(
            implementation.verify_raw_output(
                evidence.artifact_json_bytes(tabbed).decode("utf-8"), record
            )["joint_correct"]
        )

    def test_evidence_registries_receipts_and_distributions_are_exact(self) -> None:
        adapter = self.expected_evidence["adapter_implementation"]
        verifier = self.expected_evidence["verifier_implementation"]
        self.assertEqual(
            adapter["execution_registry_receipt"],
            _payload_receipt(
                evidence.artifact_json_bytes(adapter["execution_registry"])
            ),
        )
        self.assertEqual(
            verifier["execution_registry_receipt"],
            _payload_receipt(
                evidence.artifact_json_bytes(verifier["execution_registry"])
            ),
        )
        self.assertEqual(
            verifier["case_distribution"],
            {kind: 32 for kind in sorted(protocol.VERIFIER_CASE_KINDS)},
        )
        self.assertEqual(
            Counter(
                (item["compiler_valid"], item["joint_correct"])
                for item in verifier["execution_registry"]
            ),
            Counter({(True, True): 32, (True, False): 64, (False, False): 64}),
        )

    def test_claims_authority_and_next_gate_are_narrow(self) -> None:
        claims = self.expected_evidence["claims"]
        self.assertEqual(claims, evidence.IMPLEMENTATION_CLAIMS)
        self.assertEqual(
            {name for name, established in claims.items() if established},
            {
                "generation_executed",
                "records_generated",
                "images_generated",
                "dataset_validated",
                "environment_adapter_implemented",
                "environment_adapter_executed",
                "verifier_implemented",
                "verifier_executed",
            },
        )
        self.assertFalse(claims["model_trained"])
        self.assertFalse(claims["model_evaluated"])
        self.assertFalse(claims["quality_improved"])
        self.assertFalse(claims["safety_established"])
        self.assertFalse(claims["runtime_eligible"])
        self.assertEqual(
            self.expected_evidence["authority_contract"],
            {
                "model_output_has_execution_authority": False,
                "runtime_is_sole_policy_approval_wal_grounding_budget_dispatch_boundary": True,
                "runtime_repository_changed": False,
                "runtime_integration_authorized": False,
                "capture_authorized": False,
            },
        )
        self.assertEqual(
            self.expected_evidence["gate_results"],
            {gate: True for gate in evidence.REQUIRED_GATES},
        )
        self.assertEqual(self.expected_evidence["next_gate"], evidence.NEXT_GATE)

    def test_resealed_evidence_tamper_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.expected_evidence)
        tampered["verifier_implementation"]["execution_registry"][0][
            "joint_correct"
        ] = False
        with self.assertRaisesRegex(
            evidence.MM005AdapterVerifierImplementationError,
            "IMPLEMENTATION_EVIDENCE_MISMATCH",
        ):
            evidence.validate_evidence(tampered, **self.inputs)

    def test_implementation_scope_has_no_model_network_or_runtime_imports(self) -> None:
        forbidden = {
            "http",
            "openai",
            "peft",
            "requests",
            "socket",
            "torch",
            "transformers",
            "urllib",
        }
        scoped = (
            "src/fullcycle_bridge/mm005_document_chart_pdf_adapter_verifier.py",
            "src/fullcycle_bridge/"
            "mm005_document_chart_pdf_adapter_verifier_implementation.py",
            "scripts/prepare_mm005_document_chart_pdf_adapter_verifier_implementation.py",
        )
        for relative in scoped:
            tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
            roots = {
                alias.name.partition(".")[0]
                for node in ast.walk(tree)
                if isinstance(node, ast.Import)
                for alias in node.names
            } | {
                node.module.partition(".")[0]
                for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom) and node.module
            }
            self.assertTrue(forbidden.isdisjoint(roots), relative)
        self.assertTrue(self.expected_evidence["consumed_inputs"]["read_only"])
        self.assertFalse(self.expected_evidence["consumed_inputs"]["generation_rerun"])


def _payload_receipt(payload: bytes) -> dict[str, object]:
    return {
        "bytes": len(payload),
        "sha256": evidence.sha256_bytes(payload),
    }


def _contains_forbidden_key(value: object) -> bool:
    if isinstance(value, Mapping):
        return any(
            str(key) in implementation.FORBIDDEN_MODEL_PAYLOAD_KEYS
            or _contains_forbidden_key(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_forbidden_key(item) for item in value)
    return False


if __name__ == "__main__":
    unittest.main()
