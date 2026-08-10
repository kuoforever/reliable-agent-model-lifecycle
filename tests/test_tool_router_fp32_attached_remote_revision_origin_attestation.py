from __future__ import annotations

import copy
import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SRC))

from fullcycle_bridge import (  # noqa: E402
    tool_router_fp32_attached_remote_revision_origin_attestation as contract,
)
from scripts import (  # noqa: E402
    probe_tool_router_fp32_attached_remote_revision_origin_attestation as collector,
)


def _sha256(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


class OriginAttestationContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source_payloads = {
            "collector_source": b"collector source",
            "contract_source": b"contract source",
        }
        self.preregistration = contract.expected_preregistration(
            freeze_status="frozen",
            protocol_source_hashes={
                name: _sha256(payload)
                for name, payload in self.source_payloads.items()
            },
        )
        self.preregistration_payload = contract.artifact_json_bytes(
            self.preregistration
        )
        self.manifest_payload = (
            ROOT
            / "baseline/fc-mvp-001-fp32-attached-offline-package-manifest-v1.json"
        ).read_bytes()
        self.reproducibility_payload = (
            ROOT
            / "baseline/fc-mvp-001-fp32-attached-offline-package-"
            "reproducibility-v1.json"
        ).read_bytes()
        self.freeze_commit = "f" * 40
        self.observed_at = "2026-08-09T14:15:16.123456Z"

    def _build(self, **overrides: object) -> dict[str, object]:
        arguments: dict[str, object] = {
            "preregistration_sha256": _sha256(self.preregistration_payload),
            "protocol_freeze_commit": self.freeze_commit,
            "observed_at_utc": self.observed_at,
            "observations": copy.deepcopy(
                self.preregistration["authority_contract"]
            ),
            "manifest_payload": self.manifest_payload,
            "reproducibility_evidence_payload": self.reproducibility_payload,
            "protocol_source_payloads": self.source_payloads,
        }
        arguments.update(overrides)
        return contract.build_origin_attestation_evidence(  # type: ignore[arg-type]
            self.preregistration, **arguments
        )

    def test_expected_draft_is_not_formally_eligible(self) -> None:
        draft = contract.expected_preregistration(
            freeze_status="draft",
            protocol_source_hashes={
                name: contract.ZERO_SHA256 for name in contract.PROTOCOL_SOURCE_PATHS
            },
        )
        self.assertEqual(
            contract.validate_preregistration(draft, require_frozen=False)[
                "freeze_status"
            ],
            "draft",
        )
        with self.assertRaisesRegex(
            contract.OriginAttestationError, "PREREGISTRATION_NOT_FROZEN"
        ):
            contract.validate_preregistration(draft)

    def test_frozen_preregistration_recomputes_exactly(self) -> None:
        validated = contract.validate_preregistration(self.preregistration)
        self.assertEqual(validated, self.preregistration)
        self.assertTrue(
            validated["collection_protocol"]["formal_collection_authorized"]
        )

    def test_tracked_preregistration_is_frozen_and_source_bound(self) -> None:
        loaded = contract.load_and_validate_preregistration(
            ROOT
            / "configs/"
            "tool_router_fp32_attached_remote_revision_origin_attestation_v1.json"
        )
        self.assertEqual(loaded.data["freeze_status"], "frozen")
        sources = loaded.data["source_lineage"]["protocol_sources"]
        for name, relative in contract.PROTOCOL_SOURCE_PATHS.items():
            self.assertEqual(
                sources[name]["sha256"],
                _sha256((ROOT / relative).read_bytes()),
            )

    def test_preregistration_claim_drift_fails_closed(self) -> None:
        changed = copy.deepcopy(self.preregistration)
        changed["claims"]["offline_artifact_eligible"] = True
        with self.assertRaisesRegex(
            contract.OriginAttestationError,
            "PREREGISTRATION_RECOMPUTATION_MISMATCH",
        ):
            contract.validate_preregistration(changed)

    def test_prior_manifest_and_reproducibility_evidence_are_authenticated(self) -> None:
        observed = contract.validate_prior_evidence_inputs(
            self.preregistration,
            manifest_payload=self.manifest_payload,
            reproducibility_evidence_payload=self.reproducibility_payload,
        )
        self.assertEqual(
            observed["reproducibility_evidence"]["remaining_blocking_findings"],
            ["remote_revision_origin_unverified"],
        )

    def test_changed_prior_evidence_bytes_fail_closed(self) -> None:
        with self.assertRaisesRegex(
            contract.OriginAttestationError, "PAYLOAD_SHA256_MISMATCH"
        ):
            contract.validate_prior_evidence_inputs(
                self.preregistration,
                manifest_payload=self.manifest_payload,
                reproducibility_evidence_payload=self.reproducibility_payload + b" ",
            )

    def test_pass_evidence_closes_only_hosted_origin_scope(self) -> None:
        evidence = self._build()
        self.assertTrue(evidence["formal_gate_passed"])
        self.assertEqual(evidence["classification"], contract.PASS_CLASSIFICATION)
        self.assertEqual(evidence["remaining_blocking_findings"], [])
        derived = evidence["derived_claims"]
        self.assertTrue(derived["remote_revision_origin_attested"])
        self.assertFalse(derived["author_identity_or_signature_attested"])
        self.assertFalse(derived["supply_chain_signature_attested"])
        for name in (
            "offline_artifact_eligible",
            "portable_package_eligible",
            "preferred_offline_candidate",
            "serving_readiness_established",
            "artifact_promotion_allowed",
            "merged_artifact_allowed",
            "runtime_eligible",
        ):
            self.assertFalse(derived[name], name)

    def test_unsigned_github_commit_is_not_promoted_to_author_signature(self) -> None:
        evidence = self._build()
        verification = evidence["observations"]["github"]["commit"]["verification"]
        self.assertFalse(verification["verified"])
        self.assertEqual(verification["reason"], "unsigned")
        self.assertFalse(
            evidence["derived_claims"]["author_identity_or_signature_attested"]
        )

    def test_github_commit_drift_fails_closed(self) -> None:
        observations = copy.deepcopy(self.preregistration["authority_contract"])
        observations["github"]["commit"]["sha"] = "0" * 40
        with self.assertRaisesRegex(
            contract.OriginAttestationError,
            "REMOTE_AUTHORITY_OBSERVATION_MISMATCH",
        ):
            self._build(observations=observations)

    def test_github_tree_blob_drift_fails_closed(self) -> None:
        observations = copy.deepcopy(self.preregistration["authority_contract"])
        observations["github"]["tree"]["selected_entries"][0]["sha"] = "0" * 40
        with self.assertRaisesRegex(
            contract.OriginAttestationError,
            "REMOTE_AUTHORITY_OBSERVATION_MISMATCH",
        ):
            self._build(observations=observations)

    def test_github_lfs_oid_drift_fails_closed(self) -> None:
        observations = copy.deepcopy(self.preregistration["authority_contract"])
        observations["github"]["adapter_lfs"]["oid"] = "0" * 64
        with self.assertRaisesRegex(
            contract.OriginAttestationError,
            "REMOTE_AUTHORITY_OBSERVATION_MISMATCH",
        ):
            self._build(observations=observations)

    def test_huggingface_revision_drift_fails_closed(self) -> None:
        observations = copy.deepcopy(self.preregistration["authority_contract"])
        observations["huggingface"]["repository"]["sha"] = "0" * 40
        with self.assertRaisesRegex(
            contract.OriginAttestationError,
            "REMOTE_AUTHORITY_OBSERVATION_MISMATCH",
        ):
            self._build(observations=observations)

    def test_huggingface_file_blob_drift_fails_closed(self) -> None:
        observations = copy.deepcopy(self.preregistration["authority_contract"])
        observations["huggingface"]["remote_files"][1]["blob_id"] = "0" * 40
        with self.assertRaisesRegex(
            contract.OriginAttestationError,
            "REMOTE_AUTHORITY_OBSERVATION_MISMATCH",
        ):
            self._build(observations=observations)

    def test_protocol_source_payload_drift_fails_closed(self) -> None:
        changed = dict(self.source_payloads)
        changed["contract_source"] += b" changed"
        with self.assertRaisesRegex(
            contract.OriginAttestationError, "PROTOCOL_SOURCE_HASH_MISMATCH"
        ):
            self._build(protocol_source_payloads=changed)

    def test_invalid_observation_timestamp_fails_closed(self) -> None:
        with self.assertRaisesRegex(
            contract.OriginAttestationError, "INVALID_OBSERVATION_TIMESTAMP"
        ):
            self._build(observed_at_utc="2026-08-10T00:00:00Z")

    def test_gate_classification_distinguishes_authorities(self) -> None:
        passed = self._build()["gates"]
        github_failed = dict(passed)
        github_failed["github_tree"] = False
        hf_failed = dict(passed)
        hf_failed["huggingface_tree"] = False
        trust_failed = dict(passed)
        trust_failed["prior_evidence"] = False
        self.assertEqual(
            contract.classify_origin_attestation_gates(passed),
            contract.PASS_CLASSIFICATION,
        )
        self.assertEqual(
            contract.classify_origin_attestation_gates(github_failed),
            contract.GITHUB_ORIGIN_FAILED_CLASSIFICATION,
        )
        self.assertEqual(
            contract.classify_origin_attestation_gates(hf_failed),
            contract.HUGGINGFACE_ORIGIN_FAILED_CLASSIFICATION,
        )
        self.assertEqual(
            contract.classify_origin_attestation_gates(trust_failed),
            contract.TRUST_ROOT_INVALID_CLASSIFICATION,
        )

    def test_tracked_evidence_recomputes_exactly(self) -> None:
        evidence = self._build()
        evidence_payload = contract.artifact_json_bytes(evidence)
        result = contract.validate_origin_attestation_evidence(
            self.preregistration_payload,
            evidence_payload,
            expected_preregistration_sha256=_sha256(
                self.preregistration_payload
            ),
            expected_evidence_sha256=_sha256(evidence_payload),
            expected_protocol_freeze_commit=self.freeze_commit,
            manifest_payload=self.manifest_payload,
            reproducibility_evidence_payload=self.reproducibility_payload,
            protocol_source_payloads=self.source_payloads,
        )
        self.assertTrue(result["frozen_gate_valid"])
        self.assertTrue(result["remote_revision_origin_attested"])
        self.assertFalse(result["runtime_eligible"])

    def test_tampered_tracked_evidence_fails_hash_authentication(self) -> None:
        evidence_payload = contract.artifact_json_bytes(self._build())
        with self.assertRaisesRegex(
            contract.OriginAttestationError, "PAYLOAD_SHA256_MISMATCH"
        ):
            contract.validate_origin_attestation_evidence(
                self.preregistration_payload,
                evidence_payload + b" ",
                expected_preregistration_sha256=_sha256(
                    self.preregistration_payload
                ),
                expected_evidence_sha256=_sha256(evidence_payload),
                expected_protocol_freeze_commit=self.freeze_commit,
                manifest_payload=self.manifest_payload,
                reproducibility_evidence_payload=self.reproducibility_payload,
                protocol_source_payloads=self.source_payloads,
            )

    def test_duplicate_json_key_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            contract.OriginAttestationError, "DUPLICATE_JSON_KEY"
        ):
            contract.parse_strict_json_bytes(b'{"a":1,"a":2}', path="$")

    def test_git_blob_sha1_matches_known_git_object(self) -> None:
        self.assertEqual(
            contract.git_blob_sha1(b"hello\n"),
            "ce013625030ba8dba906f756967f9e9ca394464a",
        )


class OriginAttestationCollectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.authority = contract.expected_preregistration(
            freeze_status="draft",
            protocol_source_hashes={
                name: contract.ZERO_SHA256 for name in contract.PROTOCOL_SOURCE_PATHS
            },
        )["authority_contract"]

    def test_github_repository_projection_is_exact(self) -> None:
        expected = self.authority["github"]["repository"]
        raw = copy.deepcopy(expected)
        raw["owner"] = copy.deepcopy(expected["owner"])
        raw["ignored"] = "mutable field"
        self.assertEqual(collector._project_github_repository(raw), expected)

    def test_github_commit_projection_preserves_unsigned_boundary(self) -> None:
        expected = self.authority["github"]["commit"]
        raw = {
            "sha": expected["sha"],
            "tree": {"sha": expected["tree"], "url": "ignored"},
            "parents": [{"sha": expected["parents"][0], "url": "ignored"}],
            "verification": copy.deepcopy(expected["verification"]),
        }
        self.assertEqual(collector._project_github_commit(raw), expected)

    def test_github_tree_projection_requires_every_selected_path(self) -> None:
        expected = self.authority["github"]["tree"]
        filler_count = expected["full_entry_count"] - len(
            expected["selected_entries"]
        )
        raw = {
            "sha": expected["sha"],
            "truncated": False,
            "tree": copy.deepcopy(expected["selected_entries"])
            + [
                {
                    "path": f"ignored/{index}",
                    "mode": "100644",
                    "type": "blob",
                    "sha": f"{index + 1:040x}",
                    "size": index,
                }
                for index in range(filler_count)
            ],
        }
        selected_paths = {item["path"] for item in expected["selected_entries"]}
        self.assertEqual(
            collector._project_github_tree(raw, selected_paths=selected_paths),
            expected,
        )
        raw["tree"] = raw["tree"][1:]
        with self.assertRaisesRegex(RuntimeError, "every selected package path"):
            collector._project_github_tree(raw, selected_paths=selected_paths)

    def test_github_lfs_projection_does_not_store_signed_query(self) -> None:
        oid = contract.ADAPTER_LFS_OID.removeprefix("sha256:")
        raw = {
            "objects": [
                {
                    "oid": oid,
                    "size": contract.ADAPTER_LFS_BYTES,
                    "actions": {
                        "download": {
                            "href": (
                                "https://github-cloud.githubusercontent.com/"
                                f"object/{oid}?token=must-not-be-recorded"
                            )
                        }
                    },
                }
            ]
        }
        projected = collector._project_github_lfs(raw)
        self.assertTrue(projected["signed_query_present"])
        self.assertFalse(projected["signed_query_recorded"])
        self.assertNotIn("href", json.dumps(projected))

    def test_huggingface_file_projection_normalizes_lfs_keys(self) -> None:
        expected = self.authority["huggingface"]["remote_files"]
        raw_files = []
        for item in expected:
            lfs = item["lfs"]
            raw_files.append(
                {
                    "rfilename": item["rfilename"],
                    "size": item["size"],
                    "blobId": item["blob_id"],
                    "lfs": (
                        None
                        if lfs is None
                        else {
                            "pointerSize": lfs["pointer_size"],
                            "sha256": lfs["sha256"],
                            "size": lfs["size"],
                        }
                    ),
                }
            )
        self.assertEqual(
            collector._project_huggingface_files({"siblings": raw_files}),
            expected,
        )

    def test_lfs_pointer_parser_rejects_noncanonical_pointer(self) -> None:
        valid = (
            b"version https://git-lfs.github.com/spec/v1\n"
            + b"oid "
            + contract.ADAPTER_LFS_OID.encode("ascii")
            + b"\nsize 17462432\n"
        )
        self.assertEqual(
            collector._parse_lfs_pointer(valid),
            {"oid": contract.ADAPTER_LFS_OID, "size": contract.ADAPTER_LFS_BYTES},
        )
        with self.assertRaisesRegex(RuntimeError, "schema mismatch"):
            collector._parse_lfs_pointer(b"not a pointer")

    def test_request_json_rejects_non_https_without_network(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "explicit HTTPS host"):
            collector._request_json(
                method="GET",
                url="http://api.github.com/example",
                body=None,
                headers={},
            )

    @unittest.skipUnless(hasattr(os, "link"), "hard links unavailable")
    def test_safe_local_file_rejects_hard_link(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            source = root / "source.txt"
            source.write_bytes(b"payload")
            linked = root / "linked.txt"
            os.link(source, linked)
            with self.assertRaisesRegex(RuntimeError, "multiple hard links"):
                collector._read_safe_local_file(root, "linked.txt", 100)


if __name__ == "__main__":
    unittest.main()
