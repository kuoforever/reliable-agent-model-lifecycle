from __future__ import annotations

import copy
import hashlib
import math
import sys
import unittest
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fullcycle_bridge import (  # noqa: E402
    tool_router_fp32_attached_preferred_offline_candidate_decision as contract,
)
from fullcycle_bridge.consumer import canonical_json_bytes  # noqa: E402
from scripts import (  # noqa: E402
    decide_tool_router_fp32_attached_preferred_offline_candidate as builder,
)


CONFIG = ROOT / contract.PREREGISTRATION_PATH


def _sha256(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


class PreferredOfflineCandidateDecisionTests(unittest.TestCase):
    source_payloads: dict[str, bytes]
    preregistration: dict[str, Any]
    preregistration_payload: bytes
    upstream_payloads: dict[str, bytes]
    upstream_validations: dict[str, dict[str, Any]]
    freeze_commit: str

    @classmethod
    def setUpClass(cls) -> None:
        cls.source_payloads = {
            "builder_source": b"builder source",
            "contract_source": b"contract source",
        }
        cls.preregistration = contract.expected_preregistration(
            freeze_status="frozen",
            protocol_source_hashes={
                name: _sha256(payload)
                for name, payload in cls.source_payloads.items()
            },
        )
        cls.preregistration_payload = contract.artifact_json_bytes(
            cls.preregistration
        )
        cls.upstream_payloads = {
            name: (ROOT / receipt["path"]).read_bytes()
            for name, receipt in contract.UPSTREAM_ARTIFACTS.items()
        }
        cls.upstream_validations = copy.deepcopy(
            contract.EXPECTED_UPSTREAM_VALIDATIONS
        )
        cls.freeze_commit = "f" * 40

    def _build(self) -> dict[str, Any]:
        return contract.build_decision_evidence(
            self.preregistration,
            preregistration_sha256=_sha256(self.preregistration_payload),
            protocol_freeze_commit=self.freeze_commit,
            upstream_payloads=copy.deepcopy(self.upstream_payloads),
            upstream_validations=copy.deepcopy(self.upstream_validations),
            protocol_source_payloads=copy.deepcopy(self.source_payloads),
        )

    def _validate(
        self,
        evidence_payload: bytes,
        *,
        expected_evidence_sha256: str | None = None,
        upstream_payloads: dict[str, bytes] | None = None,
        upstream_validations: dict[str, dict[str, Any]] | None = None,
        source_payloads: dict[str, bytes] | None = None,
    ) -> dict[str, Any]:
        return contract.validate_decision_evidence(
            self.preregistration_payload,
            evidence_payload,
            expected_preregistration_sha256=_sha256(
                self.preregistration_payload
            ),
            expected_evidence_sha256=(
                _sha256(evidence_payload)
                if expected_evidence_sha256 is None
                else expected_evidence_sha256
            ),
            expected_protocol_freeze_commit=self.freeze_commit,
            upstream_payloads=(
                copy.deepcopy(self.upstream_payloads)
                if upstream_payloads is None
                else upstream_payloads
            ),
            upstream_validations=(
                copy.deepcopy(self.upstream_validations)
                if upstream_validations is None
                else upstream_validations
            ),
            protocol_source_payloads=(
                copy.deepcopy(self.source_payloads)
                if source_payloads is None
                else source_payloads
            ),
        )

    def assert_code(self, code: str, callback: Callable[[], object]) -> None:
        with self.assertRaisesRegex(
            contract.PreferredCandidateDecisionError, code
        ):
            callback()

    def test_categorical_rubric_requires_every_fixed_requirement(self) -> None:
        complete = {name: True for name in contract.REQUIREMENT_KEYS}
        decision = contract.classify_preferred_candidate(complete)
        self.assertTrue(decision["preferred_offline_candidate"])
        self.assertEqual(decision["blocking_findings"], [])
        self.assertEqual(decision["classification"], contract.PASS_CLASSIFICATION)

        for missing in contract.REQUIREMENT_KEYS:
            with self.subTest(missing=missing):
                incomplete = contract.classify_preferred_candidate(
                    {**complete, missing: False}
                )
                self.assertFalse(incomplete["preferred_offline_candidate"])
                self.assertEqual(incomplete["blocking_finding_count"], 1)
                self.assertEqual(
                    incomplete["classification"],
                    contract.INCOMPLETE_CLASSIFICATION,
                )

    def test_draft_preregistration_cannot_authorize_formal_decision(self) -> None:
        draft = contract.expected_preregistration(
            freeze_status="draft",
            protocol_source_hashes={
                name: _sha256(payload)
                for name, payload in self.source_payloads.items()
            },
        )
        self.assertEqual(
            contract.validate_preregistration(draft, require_frozen=False)[
                "freeze_status"
            ],
            "draft",
        )
        self.assert_code(
            "PREREGISTRATION_NOT_FROZEN",
            lambda: contract.build_decision_evidence(
                draft,
                preregistration_sha256=_sha256(
                    contract.artifact_json_bytes(draft)
                ),
                protocol_freeze_commit=self.freeze_commit,
                upstream_payloads=self.upstream_payloads,
                upstream_validations=self.upstream_validations,
                protocol_source_payloads=self.source_payloads,
            ),
        )

    def test_pass_selects_only_bounded_preferred_scope(self) -> None:
        evidence = self._build()
        derived = evidence["derived_claims"]

        self.assertTrue(evidence["formal_gate_passed"])
        self.assertEqual(evidence["classification"], contract.PASS_CLASSIFICATION)
        self.assertTrue(derived["offline_artifact_eligible"])
        self.assertTrue(derived["preferred_offline_candidate"])
        self.assertFalse(derived["portable_package_eligible"])
        self.assertFalse(derived["cross_machine_reproducibility_established"])
        self.assertFalse(derived["serving_readiness_established"])
        self.assertFalse(derived["artifact_promotion_allowed"])
        self.assertFalse(derived["merged_artifact_allowed"])
        self.assertFalse(derived["runtime_eligible"])
        self.assertEqual(
            evidence["locked_next_action"]["gate_id"], contract.PASS_NEXT_GATE_ID
        )
        self.assertEqual(
            evidence["downstream_open_findings"],
            [
                "cross_machine_reproducibility_unestablished",
                "portable_package_eligibility_unestablished",
            ],
        )

    def test_evidence_round_trip_recomputes_exactly(self) -> None:
        evidence_payload = contract.artifact_json_bytes(self._build())
        validation = self._validate(evidence_payload)
        self.assertEqual(
            validation,
            {
                "frozen_gate_valid": True,
                "classification": contract.PASS_CLASSIFICATION,
                "formal_gate_passed": True,
                "offline_artifact_eligible": True,
                "preferred_offline_candidate": True,
                "portable_package_eligible": False,
                "remaining_blocking_findings": [],
                "downstream_open_findings": [
                    "cross_machine_reproducibility_unestablished",
                    "portable_package_eligibility_unestablished",
                ],
                "next_gate": contract.PASS_NEXT_GATE_ID,
                "runtime_eligible": False,
            },
        )

    def test_raw_evidence_hash_tamper_fails_first(self) -> None:
        payload = contract.artifact_json_bytes(self._build())
        self.assert_code(
            "PAYLOAD_SHA256_MISMATCH",
            lambda: self._validate(
                payload + b" ", expected_evidence_sha256=_sha256(payload)
            ),
        )

    def test_resealed_portability_or_promotion_forgery_fails(self) -> None:
        forged = copy.deepcopy(self._build())
        forged["derived_claims"]["portable_package_eligible"] = True
        forged["claims"]["artifact_promotion_allowed"] = True
        forged.pop("report_digest")
        forged["report_digest"] = _sha256(canonical_json_bytes(forged))
        payload = contract.artifact_json_bytes(forged)
        self.assert_code(
            "EVIDENCE_RECOMPUTATION_MISMATCH", lambda: self._validate(payload)
        )

    def test_upstream_payload_and_projection_drift_fail_closed(self) -> None:
        payload = contract.artifact_json_bytes(self._build())
        changed_payloads = copy.deepcopy(self.upstream_payloads)
        changed_payloads["artifact_eligibility_review"] += b" "
        self.assert_code(
            "PAYLOAD_SHA256_MISMATCH",
            lambda: self._validate(payload, upstream_payloads=changed_payloads),
        )

        changed_validations = copy.deepcopy(self.upstream_validations)
        changed_validations["offline_artifact_eligibility_reassessment"][
            "preferred_offline_candidate"
        ] = True
        self.assert_code(
            "UPSTREAM_VALIDATION_MISMATCH",
            lambda: self._validate(
                payload, upstream_validations=changed_validations
            ),
        )

    def test_protocol_source_drift_fails_closed(self) -> None:
        payload = contract.artifact_json_bytes(self._build())
        changed = copy.deepcopy(self.source_payloads)
        changed["contract_source"] += b" "
        self.assert_code(
            "PROTOCOL_SOURCE_HASH_MISMATCH",
            lambda: self._validate(payload, source_payloads=changed),
        )

    def test_duplicate_and_nonfinite_json_are_rejected(self) -> None:
        self.assert_code(
            "INVALID_JSON",
            lambda: contract.parse_strict_json_bytes(
                b'{"a":1,"a":2}', path="$"
            ),
        )
        changed = copy.deepcopy(self.upstream_validations)
        changed["artifact_eligibility_review"]["blocking_finding_count"] = math.nan
        self.assert_code(
            "NONFINITE_NUMBER",
            lambda: contract.build_decision_evidence(
                self.preregistration,
                preregistration_sha256=_sha256(self.preregistration_payload),
                protocol_freeze_commit=self.freeze_commit,
                upstream_payloads=self.upstream_payloads,
                upstream_validations=changed,
                protocol_source_payloads=self.source_payloads,
            ),
        )

    def test_tracked_preregistration_is_frozen_and_source_bound(self) -> None:
        payload = CONFIG.read_bytes()
        raw = contract.parse_strict_json_bytes(payload, path="$.preregistration")
        self.assertIsInstance(raw, dict)
        validated = contract.validate_preregistration(raw)
        self.assertEqual(validated["freeze_status"], "frozen")
        for name, relative in contract.PROTOCOL_SOURCE_PATHS.items():
            self.assertEqual(
                validated["source_lineage"]["protocol_sources"][name]["sha256"],
                _sha256((ROOT / relative).read_bytes()),
            )

    def test_repository_adapter_recomputes_canonical_upstreams(self) -> None:
        payloads, validations = builder.load_decision_upstreams()
        self.assertEqual(validations, contract.EXPECTED_UPSTREAM_VALIDATIONS)
        evidence = builder.build_from_repository(
            protocol_freeze_commit=self.freeze_commit
        )
        self.assertTrue(evidence["formal_gate_passed"])
        self.assertTrue(evidence["derived_claims"]["preferred_offline_candidate"])
        self.assertEqual(set(payloads), set(contract.UPSTREAM_ARTIFACTS))

    def test_protocol_has_no_model_or_network_runtime_imports(self) -> None:
        forbidden = ("torch", "transformers", "peft", "requests", "urllib")
        for relative in contract.PROTOCOL_SOURCE_PATHS.values():
            source = (ROOT / relative).read_text(encoding="utf-8")
            for module in forbidden:
                self.assertNotIn(f"import {module}", source)
                self.assertNotIn(f"from {module}", source)


if __name__ == "__main__":
    unittest.main()
