from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(ROOT))

from fullcycle_bridge import (  # noqa: E402
    tool_router_fp32_attached_portable_package_qualification as contract,
)
from scripts import (  # noqa: E402
    qualify_tool_router_fp32_attached_portable_package as builder,
)


class PortablePackageQualificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.preferred_payload = (ROOT / contract.PREFERRED_EVIDENCE_PATH).read_bytes()
        cls.source_payloads = {
            name: (ROOT / relative).read_bytes()
            for name, relative in contract.PROTOCOL_SOURCE_PATHS.items()
        }
        cls.source_hashes = {
            name: contract.sha256_bytes(payload)
            for name, payload in cls.source_payloads.items()
        }
        cls.preregistration = contract.expected_preregistration(
            freeze_status="frozen",
            protocol_source_hashes=cls.source_hashes,
        )
        cls.preregistration_payload = contract.artifact_json_bytes(cls.preregistration)
        cls.replay_artifact_payload, cls.replay_evidence_payload = (
            cls._target_payloads()
        )

    @classmethod
    def _target_payloads(cls, *, raw_outputs_exact: int = 20) -> tuple[bytes, bytes]:
        replay = json.loads(
            (
                ROOT / "baseline" / "tool-router-fp32-attached-offline-package-"
                "reproducibility-v1-predictions.json"
            ).read_text(encoding="utf-8")
        )
        replay["performance"]["elapsed_seconds"] = 39.0
        replay_payload = contract.artifact_json_bytes(replay)

        evidence = json.loads(
            (
                ROOT / "baseline" / "fc-mvp-001-fp32-attached-offline-package-"
                "reproducibility-v1.json"
            ).read_text(encoding="utf-8")
        )
        evidence["replay_artifact"]["bytes"] = len(replay_payload)
        evidence["replay_artifact"]["sha256"] = contract.sha256_bytes(replay_payload)
        evidence["resources"]["performance"]["elapsed_seconds"] = 39.0
        evidence["comparison"]["raw_outputs_exact"] = raw_outputs_exact
        if raw_outputs_exact != 20:
            evidence["comparison"]["raw_outputs_digest_observed"] = "sha256:" + "1" * 64
            evidence["comparison"]["raw_mismatch_example_ids"] = ["eval-001"]
        return replay_payload, contract.artifact_json_bytes(evidence)

    @classmethod
    def _machine_receipt(
        cls,
        replay_artifact_payload: bytes | None = None,
        replay_evidence_payload: bytes | None = None,
        *,
        same_controller: bool = False,
    ) -> dict[str, object]:
        artifact_payload = (
            cls.replay_artifact_payload
            if replay_artifact_payload is None
            else replay_artifact_payload
        )
        evidence_payload = (
            cls.replay_evidence_payload
            if replay_evidence_payload is None
            else replay_evidence_payload
        )
        if same_controller:
            machine_digest = contract.CONTROLLER_MACHINE_GUID_SHA256
            gpu_digest = contract.CONTROLLER_GPU_UUID_SHA256
        else:
            machine_digest = contract.identity_source_digest(
                contract.MACHINE_GUID_DOMAIN,
                "11111111-1111-1111-1111-111111111111",
            )
            gpu_digest = contract.identity_source_digest(
                contract.GPU_UUID_DOMAIN,
                "gpu-22222222-2222-2222-2222-222222222222",
            )
        return {
            "receipt_version": contract.MACHINE_RECEIPT_VERSION,
            "gate_id": contract.GATE_ID,
            "captured_at_utc": "2026-08-10T03:00:00Z",
            "platform": {
                "system": "Windows",
                "release": "11",
                "version": "10.0.26200",
                "machine": "AMD64",
                "python": "3.12.12",
                "nvidia_driver_version": "596.49",
            },
            "identity": {
                "algorithm": contract.IDENTITY_ALGORITHM,
                "machine_guid_sha256": machine_digest,
                "gpu_uuid_sha256": gpu_digest,
                "combined_identity_sha256": contract.combined_machine_identity(
                    machine_digest, gpu_digest
                ),
                "raw_identifiers_recorded": False,
                "hardware_backed_attestation": False,
            },
            "target_artifacts": {
                "replay_artifact": {
                    "logical_path": contract.REPLAY_LOGICAL_ARTIFACT_PATH,
                    "bytes": len(artifact_payload),
                    "sha256": contract.sha256_bytes(artifact_payload),
                },
                "replay_evidence": {
                    "logical_path": contract.REPLAY_LOGICAL_EVIDENCE_PATH,
                    "bytes": len(evidence_payload),
                    "sha256": contract.sha256_bytes(evidence_payload),
                },
            },
            "limitations": {
                "hardware_backed_attestation": False,
                "external_execution_count_attested": False,
                "alternate_execution_excluded": False,
                "raw_identifiers_retained": False,
            },
        }

    def _build(
        self,
        *,
        replay_artifact_payload: bytes | None = None,
        replay_evidence_payload: bytes | None = None,
        receipt: dict[str, object] | None = None,
    ) -> dict[str, object]:
        artifact_payload = (
            self.replay_artifact_payload
            if replay_artifact_payload is None
            else replay_artifact_payload
        )
        evidence_payload = (
            self.replay_evidence_payload
            if replay_evidence_payload is None
            else replay_evidence_payload
        )
        machine_receipt = (
            self._machine_receipt(artifact_payload, evidence_payload)
            if receipt is None
            else receipt
        )
        return contract.build_qualification_evidence(
            self.preregistration,
            preregistration_sha256=contract.sha256_bytes(self.preregistration_payload),
            protocol_freeze_commit="a" * 40,
            preferred_evidence_payload=self.preferred_payload,
            preferred_validation=contract.EXPECTED_PREFERRED_VALIDATION,
            replay_artifact_payload=artifact_payload,
            replay_evidence_payload=evidence_payload,
            target_replay_validation=contract.EXPECTED_TARGET_REPLAY_VALIDATION,
            target_machine_receipt=machine_receipt,
            protocol_source_payloads=self.source_payloads,
        )

    def test_controller_anchor_recomputes_exactly(self) -> None:
        self.assertEqual(
            contract.combined_machine_identity(
                contract.CONTROLLER_MACHINE_GUID_SHA256,
                contract.CONTROLLER_GPU_UUID_SHA256,
            ),
            contract.CONTROLLER_COMBINED_IDENTITY_SHA256,
        )

    def test_identity_source_digest_normalizes_case_and_whitespace(self) -> None:
        left = contract.identity_source_digest("domain", " ABC ")
        right = contract.identity_source_digest("domain", "abc")
        self.assertEqual(left, right)

    def test_preregistration_round_trip_is_exact(self) -> None:
        self.assertEqual(
            contract.validate_preregistration(self.preregistration),
            self.preregistration,
        )
        self.assertTrue(self.preregistration["claims"]["offline_artifact_eligible"])
        self.assertTrue(self.preregistration["claims"]["preferred_offline_candidate"])
        self.assertFalse(self.preregistration["claims"]["portable_package_eligible"])

    def test_tracked_preregistration_matches_frozen_sources(self) -> None:
        payload = (ROOT / contract.PREREGISTRATION_PATH).read_bytes()
        tracked = contract.parse_strict_json_bytes(payload, path="$.preregistration")
        self.assertEqual(tracked, self.preregistration)
        self.assertEqual(contract.validate_preregistration(tracked), tracked)

    def test_preregistration_rejects_claim_drift(self) -> None:
        changed = copy.deepcopy(self.preregistration)
        changed["claims"]["portable_package_eligible"] = True
        with self.assertRaisesRegex(
            contract.PortablePackageQualificationError,
            "PREREGISTRATION_RECOMPUTATION_MISMATCH",
        ):
            contract.validate_preregistration(changed)

    def test_machine_receipt_binds_artifacts_and_is_distinct(self) -> None:
        validated = contract.validate_machine_receipt(
            self.preregistration,
            self._machine_receipt(),
            replay_artifact_payload=self.replay_artifact_payload,
            replay_evidence_payload=self.replay_evidence_payload,
        )
        self.assertTrue(validated["identity"]["distinct_from_controller"])
        self.assertNotIn("MachineGuid", json.dumps(validated))
        self.assertNotIn("GPU-", json.dumps(validated))

    def test_machine_receipt_rejects_artifact_hash_drift(self) -> None:
        receipt = self._machine_receipt()
        receipt["target_artifacts"]["replay_artifact"]["sha256"] = "sha256:" + "3" * 64
        with self.assertRaisesRegex(
            contract.PortablePackageQualificationError,
            "MACHINE_RECEIPT_RECOMPUTATION_MISMATCH",
        ):
            contract.validate_machine_receipt(
                self.preregistration,
                receipt,
                replay_artifact_payload=self.replay_artifact_payload,
                replay_evidence_payload=self.replay_evidence_payload,
            )

    def test_machine_receipt_rejects_builder_python_drift(self) -> None:
        receipt = self._machine_receipt()
        receipt["platform"]["python"] = "3.13.7"
        with self.assertRaisesRegex(
            contract.PortablePackageQualificationError,
            "MACHINE_RECEIPT_RECOMPUTATION_MISMATCH",
        ):
            contract.validate_machine_receipt(
                self.preregistration,
                receipt,
                replay_artifact_payload=self.replay_artifact_payload,
                replay_evidence_payload=self.replay_evidence_payload,
            )

    def test_machine_receipt_rejects_raw_identifier_field(self) -> None:
        receipt = self._machine_receipt()
        receipt["identity"]["machine_guid"] = "forbidden"
        with self.assertRaisesRegex(
            contract.PortablePackageQualificationError,
            "INVALID_IDENTITY_RECEIPT",
        ):
            contract.validate_machine_receipt(
                self.preregistration,
                receipt,
                replay_artifact_payload=self.replay_artifact_payload,
                replay_evidence_payload=self.replay_evidence_payload,
            )

    def test_qualification_passes_all_frozen_requirements(self) -> None:
        evidence = self._build()
        self.assertTrue(evidence["formal_gate_passed"])
        self.assertEqual(evidence["classification"], contract.PASS_CLASSIFICATION)
        self.assertTrue(all(evidence["gates"].values()))
        self.assertEqual(evidence["remaining_blocking_findings"], [])
        self.assertTrue(evidence["derived_claims"]["portable_package_eligible"])
        self.assertFalse(evidence["runtime_eligible"])
        self.assertFalse(evidence["claims"]["artifact_promotion_allowed"])

    def test_same_controller_machine_fails_closed(self) -> None:
        evidence = self._build(receipt=self._machine_receipt(same_controller=True))
        self.assertFalse(evidence["formal_gate_passed"])
        self.assertEqual(evidence["classification"], contract.INCOMPLETE_CLASSIFICATION)
        self.assertEqual(
            evidence["remaining_blocking_findings"],
            ["target_machine_not_distinct_from_controller"],
        )
        self.assertFalse(evidence["derived_claims"]["portable_package_eligible"])

    def test_raw_output_drift_fails_closed(self) -> None:
        artifact_payload, evidence_payload = self._target_payloads(raw_outputs_exact=19)
        evidence = self._build(
            replay_artifact_payload=artifact_payload,
            replay_evidence_payload=evidence_payload,
        )
        self.assertFalse(evidence["formal_gate_passed"])
        self.assertIn(
            "cross_machine_raw_output_drift",
            evidence["remaining_blocking_findings"],
        )

    def test_replay_receipt_drift_fails_closed(self) -> None:
        replay = json.loads(self.replay_evidence_payload)
        replay["replay_artifact"]["bytes"] += 1
        replay_payload = contract.artifact_json_bytes(replay)
        evidence = self._build(
            replay_evidence_payload=replay_payload,
        )
        self.assertFalse(evidence["formal_gate_passed"])
        self.assertIn(
            "target_package_identity_or_clean_resolution_failed",
            evidence["remaining_blocking_findings"],
        )

    def test_origin_artifact_reuse_is_rejected(self) -> None:
        origin_artifact = (
            ROOT / "baseline" / "tool-router-fp32-attached-offline-package-"
            "reproducibility-v1-predictions.json"
        ).read_bytes()
        receipt = self._machine_receipt(origin_artifact, self.replay_evidence_payload)
        with self.assertRaisesRegex(
            contract.PortablePackageQualificationError,
            "MACHINE_RECEIPT_RECOMPUTATION_MISMATCH",
        ):
            contract.validate_machine_receipt(
                self.preregistration,
                receipt,
                replay_artifact_payload=origin_artifact,
                replay_evidence_payload=self.replay_evidence_payload,
            )

    def test_noncanonical_target_payload_is_rejected(self) -> None:
        changed = self.replay_artifact_payload + b" "
        receipt = self._machine_receipt(changed, self.replay_evidence_payload)
        with self.assertRaisesRegex(
            contract.PortablePackageQualificationError,
            "TARGET_REPLAY_ARTIFACT_ENCODING_MISMATCH",
        ):
            self._build(replay_artifact_payload=changed, receipt=receipt)

    def test_formal_evidence_recomputes_exactly(self) -> None:
        evidence = self._build()
        evidence_payload = contract.artifact_json_bytes(evidence)
        validation = contract.validate_qualification_evidence(
            self.preregistration_payload,
            evidence_payload,
            expected_preregistration_sha256=contract.sha256_bytes(
                self.preregistration_payload
            ),
            expected_evidence_sha256=contract.sha256_bytes(evidence_payload),
            expected_protocol_freeze_commit="a" * 40,
            preferred_evidence_payload=self.preferred_payload,
            preferred_validation=contract.EXPECTED_PREFERRED_VALIDATION,
            replay_artifact_payload=self.replay_artifact_payload,
            replay_evidence_payload=self.replay_evidence_payload,
            target_replay_validation=contract.EXPECTED_TARGET_REPLAY_VALIDATION,
            protocol_source_payloads=self.source_payloads,
        )
        self.assertTrue(validation["frozen_gate_valid"])
        self.assertTrue(validation["portable_package_eligible"])
        self.assertFalse(validation["runtime_eligible"])

    def test_formal_evidence_rejects_tampering(self) -> None:
        evidence = self._build()
        evidence["derived_claims"]["runtime_eligible"] = True
        payload = contract.artifact_json_bytes(evidence)
        with self.assertRaisesRegex(
            contract.PortablePackageQualificationError,
            "EVIDENCE_RECOMPUTATION_MISMATCH",
        ):
            contract.validate_qualification_evidence(
                self.preregistration_payload,
                payload,
                expected_preregistration_sha256=contract.sha256_bytes(
                    self.preregistration_payload
                ),
                expected_evidence_sha256=contract.sha256_bytes(payload),
                expected_protocol_freeze_commit="a" * 40,
                preferred_evidence_payload=self.preferred_payload,
                preferred_validation=contract.EXPECTED_PREFERRED_VALIDATION,
                replay_artifact_payload=self.replay_artifact_payload,
                replay_evidence_payload=self.replay_evidence_payload,
                target_replay_validation=contract.EXPECTED_TARGET_REPLAY_VALIDATION,
                protocol_source_payloads=self.source_payloads,
            )

    def test_builder_refuses_non_windows_receipt_collection(self) -> None:
        with mock.patch.object(builder.platform, "system", return_value="Linux"):
            with self.assertRaisesRegex(RuntimeError, "requires native Windows"):
                builder.collect_machine_receipt(
                    replay_artifact_payload=self.replay_artifact_payload,
                    replay_evidence_payload=self.replay_evidence_payload,
                )


if __name__ == "__main__":
    unittest.main()
