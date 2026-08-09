"""Fail-closed remote revision-origin attestation for the FP32 package.

The contract is deliberately network-neutral.  An online collector supplies
small, sanitized projections from the GitHub and Hugging Face HTTPS APIs plus
content-address bindings computed from already-authenticated local bytes.  This
module authenticates the frozen preregistration and prior evidence, recomputes
every decision, and never downloads, executes, or mutates model artifacts.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, NoReturn


PREREGISTRATION_VERSION = 1
EVIDENCE_VERSION = 1
GATE_ID = "FC-MVP-001-fp32-attached-remote-revision-origin-attestation-v1"
EXPERIMENT_ID = "fc-mvp-001-fp32-attached-remote-revision-origin-attestation-v1"
PACKAGE_ID = "fc-mvp-001-fp32-attached-factorized-lora-package-v1"
CANDIDATE_ID = "fp32-attached-factorized-lora"

PASS_CLASSIFICATION = (
    "fp32_attached_github_and_huggingface_hosted_revision_origins_attested"
)
TRUST_ROOT_INVALID_CLASSIFICATION = (
    "fp32_attached_remote_revision_origin_trust_root_invalid"
)
GITHUB_ORIGIN_FAILED_CLASSIFICATION = (
    "fp32_attached_github_hosted_revision_origin_attestation_failed"
)
HUGGINGFACE_ORIGIN_FAILED_CLASSIFICATION = (
    "fp32_attached_huggingface_hosted_revision_origin_attestation_failed"
)

PASS_NEXT_GATE_ID = (
    "FC-MVP-001-fp32-attached-offline-artifact-eligibility-reassessment-v1"
)
FAILURE_NEXT_GATE_ID = (
    "FC-MVP-001-fp32-attached-remote-revision-origin-failure-classification-v1"
)

PREREGISTRATION_PATH = (
    "configs/tool_router_fp32_attached_remote_revision_origin_attestation_v1.json"
)
CONTRACT_SOURCE_PATH = (
    "src/fullcycle_bridge/"
    "tool_router_fp32_attached_remote_revision_origin_attestation.py"
)
COLLECTOR_SOURCE_PATH = (
    "scripts/probe_tool_router_fp32_attached_remote_revision_origin_attestation.py"
)
PROTOCOL_SOURCE_PATHS = {
    "collector_source": COLLECTOR_SOURCE_PATH,
    "contract_source": CONTRACT_SOURCE_PATH,
}

MANIFEST_PATH = "baseline/fc-mvp-001-fp32-attached-offline-package-manifest-v1.json"
MANIFEST_SHA256 = (
    "sha256:4125f2eef2a4b8f07015169ac7fb77b830514e053a4624aa703e5f5a64943eb0"
)
REPRODUCIBILITY_EVIDENCE_PATH = (
    "baseline/fc-mvp-001-fp32-attached-offline-package-reproducibility-v1.json"
)
REPRODUCIBILITY_EVIDENCE_SHA256 = (
    "sha256:0e0d2174f4723ab42a5c11375cee10a819e32737810f63111d098decc2984044"
)
REPRODUCIBILITY_CLASSIFICATION = (
    "fp32_attached_same_environment_clean_location_behavior_exactly_reproduced"
)

GITHUB_API_BASE = "https://api.github.com"
GITHUB_REPOSITORY = "kuoforever/reliable-agent-model-lifecycle"
GITHUB_REPOSITORY_ID = 1_315_085_157
GITHUB_OWNER_ID = 150_589_656
GITHUB_PACKAGE_COMMIT = "eafd3f646e4ec08dd0a1f76443ccfd416e81fa22"
GITHUB_PACKAGE_PARENT = "782906d44dc75c05b91db92a9ed89355af3203f2"
GITHUB_PACKAGE_TREE = "175fc22f53392992dc6c6c32093898399702efeb"
GITHUB_FULL_TREE_ENTRY_COUNT = 247
GITHUB_REMOTE_URL = (
    "https://github.com/kuoforever/reliable-agent-model-lifecycle.git"
)
GITHUB_LFS_BATCH_ENDPOINT = GITHUB_REMOTE_URL + "/info/lfs/objects/batch"
GITHUB_LFS_DOWNLOAD_HOST = "github-cloud.githubusercontent.com"

HUGGINGFACE_API_BASE = "https://huggingface.co"
HUGGINGFACE_REPOSITORY = "Qwen/Qwen2.5-1.5B-Instruct"
HUGGINGFACE_AUTHOR = "Qwen"
HUGGINGFACE_REVISION = "989aa7980e4cf806f80c7fef2b1adb7bc71aa306"
HUGGINGFACE_FULL_SIBLING_COUNT = 10

ADAPTER_LFS_OID = (
    "sha256:efb62471e105b8ef25641200967d447b8cc2f3ff565937bc47193fbf79f4f342"
)
ADAPTER_LFS_BYTES = 17_462_432
BASE_LFS_SHA256 = (
    "sha256:dd924a11b4c220f385b51ffa522daea7c9f3d850e31b162bb5661df483c6d3ee"
)
BASE_LFS_BYTES = 3_087_467_144
FORMAL_COLLECTION_DATE_UTC = "2026-08-09"
ZERO_SHA256 = "sha256:" + "0" * 64

SHA256_PATTERN = re.compile(r"sha256:[0-9a-f]{64}")
SHA1_PATTERN = re.compile(r"[0-9a-f]{40}")
GIT_COMMIT_PATTERN = SHA1_PATTERN
UTC_TIMESTAMP_PATTERN = re.compile(
    r"2026-08-09T(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9](?:\.[0-9]+)?Z"
)
MAX_JSON_BYTES = 4 * 1024 * 1024


GITHUB_CONTENT_BINDINGS: tuple[dict[str, Any], ...] = (
    {
        "path": "baseline/adapters/fc-mvp-001-lora-sft-v2/README.md",
        "role": "historical_adapter_card",
        "binding_kind": "git_blob",
        "bytes": 5_107,
        "sha256": "sha256:353053cad9659d849cbf1fdacc7d9b86b82fb72197e2d101785843a4109bc522",
        "git_blob_sha1": "d4d5cffe55bb9df55c65d116e4186573c3b5b63e",
    },
    {
        "path": "baseline/adapters/fc-mvp-001-lora-sft-v2/adapter_config.json",
        "role": "peft_adapter_config",
        "binding_kind": "git_blob",
        "bytes": 793,
        "sha256": "sha256:8eb104c3af2f4deb3abe5e471b3d3a74cb306683c1fdadb95488de981ba14c16",
        "git_blob_sha1": "f0f102e9538e8309fecae291e12db38e8b84ccb5",
    },
    {
        "path": "baseline/adapters/fc-mvp-001-lora-sft-v2/adapter_model.safetensors",
        "role": "fp32_lora_weights",
        "binding_kind": "git_lfs_pointer",
        "pointer_bytes": 133,
        "pointer_sha256": "sha256:705884b955cd417fa2b02ce5a618feab140a60edf4f9be4c7ea00e37ffb1fecb",
        "git_blob_sha1": "db6f62d5d65595819e7b367f9f9c64c530c1cd26",
        "lfs_oid": ADAPTER_LFS_OID,
        "lfs_bytes": ADAPTER_LFS_BYTES,
    },
    {
        "path": "baseline/fc-mvp-001-fp32-attached-artifact-eligibility-review-v1.json",
        "role": "upstream_review",
        "binding_kind": "git_blob",
        "bytes": 15_278,
        "sha256": "sha256:81977f318c6bcfed8d3844575dc245d4b94c2636a2359165f9aa5553c9b006f8",
        "git_blob_sha1": "ebc3648e202758418f61e684ed8d007e78fda5c2",
    },
    {
        "path": "configs/tool_router_fp32_attached_remediation_eval_v1.json",
        "role": "remediation_preregistration",
        "binding_kind": "git_blob",
        "bytes": 14_276,
        "sha256": "sha256:5e7b0665f97f5cee760637236f80039c4e621ae0f24915c0ac749d885a683c8b",
        "git_blob_sha1": "f20e7229106d1139f23e0748abfbe05b0fb03dc2",
    },
    {
        "path": "configs/tool_router_lora_sft_v2.json",
        "role": "sft_config",
        "binding_kind": "git_blob",
        "bytes": 2_494,
        "sha256": "sha256:110ada11d69f4e83c4b93da0304e62151059115487e90394d32835f6916365c8",
        "git_blob_sha1": "ad750b7d5a5b5c6d1d31a83a69cafa43da674733",
    },
    {
        "path": "docs/FC-MVP-001-fp32-attached-offline-package-use-v1.md",
        "role": "package_documentation",
        "binding_kind": "git_blob",
        "bytes": 4_814,
        "sha256": "sha256:a531b0e462aad15a1ec9eb001d05c8cf71b5a72bde66437a499d0c6efba9cb24",
        "git_blob_sha1": "9333780876ebf61a0e5b65c7ebd9ef0da60cba6c",
    },
    {
        "path": "prompts/tool_router_v1.txt",
        "role": "prompt",
        "binding_kind": "git_blob",
        "bytes": 1_335,
        "sha256": "sha256:4a7d15063b0b074ef999c2848d0fc073a6cc00ed4999ea81f770e2e42cfa6d97",
        "git_blob_sha1": "9032d64181387a2601e5d6f7ab66ca2d11666613",
    },
    {
        "path": "requirements/training.lock",
        "role": "training_lock",
        "binding_kind": "git_blob",
        "bytes": 321,
        "sha256": "sha256:e6e23f51834b1815578368ce54c78034e72a7158395892e77fdf75594548931f",
        "git_blob_sha1": "03d0ab2df26f894878416fe5e7300f056303635b",
    },
    {
        "path": "scripts/build_tool_router_fp32_attached_offline_package_manifest.py",
        "role": "manifest_builder_source",
        "binding_kind": "git_blob",
        "bytes": 20_352,
        "sha256": "sha256:7834a35854e14863de4312319fcf109681a14f42bf2d7eee3a385a1376427284",
        "git_blob_sha1": "ff0b784b8600a97b04d33ffe78d9923df0c36a3c",
    },
    {
        "path": "scripts/download_pinned_tool_router_model.py",
        "role": "model_downloader_source",
        "binding_kind": "git_blob",
        "bytes": 1_355,
        "sha256": "sha256:1d0d3321a55b185128de020f4b5a2a9c3ecc22f5abb0535c4712c4fd545d3a28",
        "git_blob_sha1": "ad8ce19426a22bb4ce8dface5c9920725b559903",
    },
    {
        "path": "src/fullcycle_bridge/__init__.py",
        "role": "package_init_source",
        "binding_kind": "git_blob",
        "bytes": 507,
        "sha256": "sha256:45cabb5da1c0e7c2c93ef045904cf4555b0c755baf1ec2eaf47330a1aab6008e",
        "git_blob_sha1": "15e9fe5b6c43037576e987cd19fccab8614d001b",
    },
    {
        "path": "src/fullcycle_bridge/consumer.py",
        "role": "canonical_json_source",
        "binding_kind": "git_blob",
        "bytes": 22_342,
        "sha256": "sha256:05cfe603d4786fb536cc1f99952a55fd211cc0fea2c210b32b575fefda9537d3",
        "git_blob_sha1": "9a1aaa8a0c138656420f28ea344584ed73c684c0",
    },
    {
        "path": "src/fullcycle_bridge/tool_router.py",
        "role": "validation_error_source",
        "binding_kind": "git_blob",
        "bytes": 18_499,
        "sha256": "sha256:bb3cda72585bc84bf0cf84c5736cafe29c8dfc8bca5a851d82ecfed35b1b883d",
        "git_blob_sha1": "21a9fbc83a875bc457d9fabb70d233754bbce9a2",
    },
    {
        "path": "src/fullcycle_bridge/tool_router_decision_compilation.py",
        "role": "decision_compiler_source",
        "binding_kind": "git_blob",
        "bytes": 9_575,
        "sha256": "sha256:16f162a84572c7f0782890aef5aafbaafa1862e14938fe08b0ea6e97efa05157",
        "git_blob_sha1": "57cdca810d906da9740a17f980acf4fca4de34ee",
    },
    {
        "path": "src/fullcycle_bridge/tool_router_fp32_attached_artifact_eligibility.py",
        "role": "adapter_inspector_source",
        "binding_kind": "git_blob",
        "bytes": 65_074,
        "sha256": "sha256:3fa9dca9d5b309b9401be25dd3538ccbdf76df63d0eda67230a45152703c5452",
        "git_blob_sha1": "8fa28633011e1682bc3776e7c6a11155e7ba067d",
    },
    {
        "path": "src/fullcycle_bridge/tool_router_fp32_attached_offline_package_manifest.py",
        "role": "manifest_contract_source",
        "binding_kind": "git_blob",
        "bytes": 54_580,
        "sha256": "sha256:8e7b09f914ab45bdbe4841ebf3c06eb75ce9eabf0d2ce9ba2cb8de3ca48d383d",
        "git_blob_sha1": "e75047b173e405177c43b0d6383647b2e05d828a",
    },
    {
        "path": "src/fullcycle_bridge/tool_router_sft.py",
        "role": "sft_helpers_source",
        "binding_kind": "git_blob",
        "bytes": 2_769,
        "sha256": "sha256:db881e5e5955341acb735416d93062a40cf512b63ec50eb8c196ddb4371bd020",
        "git_blob_sha1": "70afe533036664a615a386b34e462d4cc3c390c6",
    },
)


HUGGINGFACE_FILES: tuple[dict[str, Any], ...] = (
    {
        "path": ".gitattributes",
        "package_component": False,
        "binding_kind": "git_blob",
        "bytes": 1_519,
        "git_blob_sha1": "a6344aac8c09253b3b630fb776ae94478aa0275b",
    },
    {
        "path": "LICENSE",
        "package_component": True,
        "binding_kind": "git_blob",
        "bytes": 11_343,
        "sha256": "sha256:832dd9e00a68dd83b3c3fb9f5588dad7dcf337a0db50f7d9483f310cd292e92e",
        "git_blob_sha1": "6634c8cc3133b3848ec74b9f275acaaa1ea618ab",
    },
    {
        "path": "README.md",
        "package_component": True,
        "binding_kind": "git_blob",
        "bytes": 4_917,
        "sha256": "sha256:2e1bcd8bd964728a820be709fa0f7b9dd54817a94fd2254c535df70c5e67fada",
        "git_blob_sha1": "b3327a17e2ffa52e0fd941a2810b18a9fd0e7d94",
    },
    {
        "path": "config.json",
        "package_component": True,
        "binding_kind": "git_blob",
        "bytes": 660,
        "sha256": "sha256:98d2ff8cc47488d08a2b0b3acf4eb99ef210779b42bd48605f6b8e36acdbf670",
        "git_blob_sha1": "f81ead14ab072d65a07817f83a3ee0e5a1890d10",
    },
    {
        "path": "generation_config.json",
        "package_component": True,
        "binding_kind": "git_blob",
        "bytes": 242,
        "sha256": "sha256:e558847a8b4402616f1273797b015104dc266fe4b520056fca88823ba8f8ebe6",
        "git_blob_sha1": "dfc11073787daf1b0f9c0f1499487ab5f4c93738",
    },
    {
        "path": "merges.txt",
        "package_component": True,
        "binding_kind": "git_blob",
        "bytes": 1_671_839,
        "sha256": "sha256:599bab54075088774b1733fde865d5bd747cbcc7a547c5bc12610e874e26f5e3",
        "git_blob_sha1": "20024bfe7c83998e9aeaf98a0cd6a2ce6306c2f0",
    },
    {
        "path": "model.safetensors",
        "package_component": True,
        "binding_kind": "git_lfs",
        "bytes": BASE_LFS_BYTES,
        "sha256": BASE_LFS_SHA256,
        "git_blob_sha1": "9127f71e7314df0064f469223749e5f237e06463",
        "lfs_pointer_bytes": 135,
    },
    {
        "path": "tokenizer.json",
        "package_component": True,
        "binding_kind": "git_blob",
        "bytes": 7_031_645,
        "sha256": "sha256:c0382117ea329cdf097041132f6d735924b697924d6f6fc3945713e96ce87539",
        "git_blob_sha1": "443909a61d429dff23010e5bddd28ff530edda00",
    },
    {
        "path": "tokenizer_config.json",
        "package_component": True,
        "binding_kind": "git_blob",
        "bytes": 7_305,
        "sha256": "sha256:5b5d4f65d0acd3b2d56a35b56d374a36cbc1c8fa5cf3b3febbbfabf22f359583",
        "git_blob_sha1": "07bfe0640cb5a0037f9322287fbfc682806cf672",
    },
    {
        "path": "vocab.json",
        "package_component": True,
        "binding_kind": "git_blob",
        "bytes": 2_776_833,
        "sha256": "sha256:ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910",
        "git_blob_sha1": "4783fe10ac3adce15ac8f358ef5462739852c569",
    },
)


class OriginAttestationError(ValueError):
    """One deterministic origin-attestation contract failure."""

    def __init__(self, code: str, path: str, detail: str) -> None:
        self.code = code
        self.path = path
        self.detail = detail
        super().__init__(f"{code} at {path}: {detail}")


@dataclass(frozen=True)
class LoadedPreregistration:
    """One raw-byte-bound preregistration snapshot."""

    data: dict[str, Any]
    payload: bytes
    sha256: str


def expected_github_tree_entries() -> list[dict[str, Any]]:
    """Return the immutable selected tree entries expected from GitHub."""

    result: list[dict[str, Any]] = []
    for item in GITHUB_CONTENT_BINDINGS:
        size = item.get("pointer_bytes", item.get("bytes"))
        result.append(
            {
                "path": item["path"],
                "mode": "100644",
                "type": "blob",
                "sha": item["git_blob_sha1"],
                "size": size,
            }
        )
    return result


def expected_huggingface_remote_files() -> list[dict[str, Any]]:
    """Return the immutable Hub sibling projection for the pinned revision."""

    result: list[dict[str, Any]] = []
    for item in HUGGINGFACE_FILES:
        lfs: dict[str, Any] | None = None
        if item["binding_kind"] == "git_lfs":
            lfs = {
                "pointer_size": item["lfs_pointer_bytes"],
                "sha256": str(item["sha256"]).removeprefix("sha256:"),
                "size": item["bytes"],
            }
        result.append(
            {
                "rfilename": item["path"],
                "size": item["bytes"],
                "blob_id": item["git_blob_sha1"],
                "lfs": lfs,
            }
        )
    return result


def expected_preregistration(
    *,
    freeze_status: str,
    protocol_source_hashes: Mapping[str, str],
) -> dict[str, Any]:
    """Build the sole accepted preregistration object."""

    if freeze_status not in {"draft", "frozen"}:
        _fail("INVALID_FREEZE_STATUS", "$.freeze_status", repr(freeze_status))
    if set(protocol_source_hashes) != set(PROTOCOL_SOURCE_PATHS):
        _fail(
            "INVALID_PROTOCOL_SOURCE_SET",
            "$.source_lineage.protocol_sources",
            repr(sorted(protocol_source_hashes)),
        )
    protocol_sources = {
        name: {
            "path": PROTOCOL_SOURCE_PATHS[name],
            "sha256": protocol_source_hashes[name],
        }
        for name in sorted(PROTOCOL_SOURCE_PATHS)
    }
    return {
        "preregistration_version": PREREGISTRATION_VERSION,
        "freeze_status": freeze_status,
        "gate_id": GATE_ID,
        "experiment_id": EXPERIMENT_ID,
        "package_id": PACKAGE_ID,
        "candidate_id": CANDIDATE_ID,
        "accepted_observation_runs": 1,
        "formal_collection_date_utc": FORMAL_COLLECTION_DATE_UTC,
        "source_lineage": {
            "manifest": {"path": MANIFEST_PATH, "sha256": MANIFEST_SHA256},
            "reproducibility_evidence": {
                "path": REPRODUCIBILITY_EVIDENCE_PATH,
                "sha256": REPRODUCIBILITY_EVIDENCE_SHA256,
                "classification": REPRODUCIBILITY_CLASSIFICATION,
            },
            "protocol_sources": protocol_sources,
        },
        "authority_contract": {
            "github": {
                "api_base": GITHUB_API_BASE,
                "repository": {
                    "id": GITHUB_REPOSITORY_ID,
                    "node_id": "R_kgDOTmKbZQ",
                    "name": "reliable-agent-model-lifecycle",
                    "full_name": GITHUB_REPOSITORY,
                    "owner": {
                        "login": "kuoforever",
                        "id": GITHUB_OWNER_ID,
                        "node_id": "U_kgDOCPnQ2A",
                        "type": "User",
                    },
                    "private": False,
                    "html_url": "https://github.com/" + GITHUB_REPOSITORY,
                    "clone_url": GITHUB_REMOTE_URL,
                    "ssh_url": (
                        "git@github.com:kuoforever/"
                        "reliable-agent-model-lifecycle.git"
                    ),
                    "default_branch": "master",
                    "archived": False,
                    "disabled": False,
                    "visibility": "public",
                },
                "commit": {
                    "sha": GITHUB_PACKAGE_COMMIT,
                    "tree": GITHUB_PACKAGE_TREE,
                    "parents": [GITHUB_PACKAGE_PARENT],
                    "verification": {
                        "verified": False,
                        "reason": "unsigned",
                        "signature": None,
                        "payload": None,
                        "verified_at": None,
                    },
                },
                "tree": {
                    "sha": GITHUB_PACKAGE_TREE,
                    "full_entry_count": GITHUB_FULL_TREE_ENTRY_COUNT,
                    "truncated": False,
                    "selected_entries": expected_github_tree_entries(),
                },
                "adapter_lfs": {
                    "batch_endpoint": GITHUB_LFS_BATCH_ENDPOINT,
                    "ref": GITHUB_PACKAGE_COMMIT,
                    "oid": ADAPTER_LFS_OID.removeprefix("sha256:"),
                    "size": ADAPTER_LFS_BYTES,
                    "status": 200,
                    "response_media_type": "application/json",
                    "error": None,
                    "action_keys": ["download"],
                    "download_scheme": "https",
                    "download_host": GITHUB_LFS_DOWNLOAD_HOST,
                    "download_path_ends_with_oid": True,
                    "signed_query_present": True,
                    "signed_query_recorded": False,
                },
                "content_bindings": copy.deepcopy(list(GITHUB_CONTENT_BINDINGS)),
            },
            "huggingface": {
                "api_base": HUGGINGFACE_API_BASE,
                "repository": {
                    "id": HUGGINGFACE_REPOSITORY,
                    "model_id": HUGGINGFACE_REPOSITORY,
                    "author": HUGGINGFACE_AUTHOR,
                    "sha": HUGGINGFACE_REVISION,
                    "private": False,
                    "gated": False,
                    "disabled": False,
                },
                "revision": HUGGINGFACE_REVISION,
                "full_sibling_count": HUGGINGFACE_FULL_SIBLING_COUNT,
                "remote_files": expected_huggingface_remote_files(),
                "content_bindings": copy.deepcopy(
                    [item for item in HUGGINGFACE_FILES if item["package_component"]]
                ),
            },
        },
        "collection_protocol": {
            "formal_collection_authorized": freeze_status == "frozen",
            "https_only": True,
            "system_ca_and_hostname_verification_required": True,
            "fixed_requests": [
                "github_repository_metadata",
                "github_commit_metadata",
                "github_recursive_tree_metadata",
                "github_adapter_lfs_batch_metadata",
                "huggingface_revision_file_metadata",
            ],
            "alternate_repository_or_revision_allowed": False,
            "automatic_request_retry_count": 0,
            "artifact_write_after_all_gates_only": True,
            "raw_response_bodies_stored": False,
            "lfs_signed_url_or_query_stored": False,
            "model_or_adapter_lfs_download": False,
            "model_execution": False,
            "package_mutation_or_copy": False,
            "local_binding_bytes": {
                "github_frozen_git_blobs": 239_604,
                "huggingface_non_lfs_package_files": 11_504_784,
                "large_lfs_payload_bytes_read": 0,
            },
        },
        "acceptance_criteria": {
            "required_gates": [
                "prior_evidence",
                "protocol_integrity",
                "github_repository",
                "github_commit",
                "github_tree",
                "github_content_bindings",
                "github_adapter_lfs",
                "huggingface_repository",
                "huggingface_tree",
                "huggingface_content_bindings",
            ],
            "github_selected_entries": len(GITHUB_CONTENT_BINDINGS),
            "huggingface_package_files": sum(
                bool(item["package_component"]) for item in HUGGINGFACE_FILES
            ),
            "remaining_blocking_findings_on_pass": [],
        },
        "outcome_classifications": {
            "passed": PASS_CLASSIFICATION,
            "trust_root_invalid": TRUST_ROOT_INVALID_CLASSIFICATION,
            "github_origin_failed": GITHUB_ORIGIN_FAILED_CLASSIFICATION,
            "huggingface_origin_failed": HUGGINGFACE_ORIGIN_FAILED_CLASSIFICATION,
        },
        "outcome_next_actions": {
            "passed": {
                "gate_id": PASS_NEXT_GATE_ID,
                "action": (
                    "reassess offline artifact eligibility without inferring "
                    "preferred candidate promotion serving or Runtime readiness"
                ),
            },
            "adverse": {
                "gate_id": FAILURE_NEXT_GATE_ID,
                "action": (
                    "classify the fixed-authority mismatch before changing any "
                    "repository revision package byte or downstream decision"
                ),
            },
        },
        "constraints": {
            "new_data": False,
            "training": False,
            "eval_answer_tuning": False,
            "decision_compiler_change": False,
            "prompt_change": False,
            "generation_change": False,
            "precision_change": False,
            "execution_form_change": False,
            "base_or_tokenizer_substitution": False,
            "adapter_or_weight_mutation": False,
            "merged_weight_creation": False,
            "artifact_promotion": False,
            "serving_integration": False,
            "runtime_integration": False,
            "provider_integration": False,
            "mcp_integration": False,
            "desktop_integration": False,
        },
        "claims": {
            "transport_success_alone_is_origin_attestation": False,
            "manifest_hash_match_alone_is_origin_attestation": False,
            "hosted_revision_origin_scope": (
                "github_and_huggingface_https_service_authorities"
            ),
            "author_identity_or_signature_attested": False,
            "supply_chain_signature_attested": False,
            "historical_transparency_log_attested": False,
            "cross_machine_reproducibility_established": False,
            "transitive_dependency_hashes_pinned": False,
            "full_eval_repeat_variance_established": False,
            "external_execution_count_attested": False,
            "offline_artifact_eligible": False,
            "portable_package_eligible": False,
            "preferred_offline_candidate": False,
            "serving_readiness_established": False,
            "artifact_promotion_allowed": False,
            "merged_artifact_allowed": False,
        },
        "runtime_eligible": False,
    }


def validate_preregistration(
    value: object,
    *,
    require_frozen: bool = True,
) -> dict[str, Any]:
    """Validate a closed preregistration and reject draft formal collection."""

    preregistration = _mapping(value, "$.preregistration")
    _validate_finite_json(preregistration, "$.preregistration")
    status = preregistration.get("freeze_status")
    if status not in {"draft", "frozen"}:
        _fail("INVALID_FREEZE_STATUS", "$.freeze_status", repr(status))
    lineage = _mapping(preregistration.get("source_lineage"), "$.source_lineage")
    sources = _mapping(
        lineage.get("protocol_sources"), "$.source_lineage.protocol_sources"
    )
    hashes: dict[str, str] = {}
    if set(sources) != set(PROTOCOL_SOURCE_PATHS):
        _fail(
            "INVALID_PROTOCOL_SOURCE_SET",
            "$.source_lineage.protocol_sources",
            repr(sorted(sources)),
        )
    for name in sorted(PROTOCOL_SOURCE_PATHS):
        record = _mapping(
            sources.get(name), f"$.source_lineage.protocol_sources.{name}"
        )
        digest = record.get("sha256")
        _validate_sha256(digest, f"$.source_lineage.protocol_sources.{name}.sha256")
        hashes[name] = str(digest)
    expected = expected_preregistration(
        freeze_status=str(status), protocol_source_hashes=hashes
    )
    if preregistration != expected:
        _fail(
            "PREREGISTRATION_RECOMPUTATION_MISMATCH",
            "$.preregistration",
            _first_difference(preregistration, expected),
        )
    if status == "draft":
        if any(digest != ZERO_SHA256 for digest in hashes.values()):
            _fail(
                "DRAFT_SOURCE_HASH_NOT_PLACEHOLDER",
                "$.source_lineage.protocol_sources",
                repr(hashes),
            )
        if require_frozen:
            _fail(
                "PREREGISTRATION_NOT_FROZEN",
                "$.freeze_status",
                "draft cannot authorize formal collection",
            )
    elif any(digest == ZERO_SHA256 for digest in hashes.values()):
        _fail(
            "UNBOUND_PROTOCOL_SOURCE",
            "$.source_lineage.protocol_sources",
            repr(hashes),
        )
    return copy.deepcopy(preregistration)


def load_and_validate_preregistration(
    path: Path,
    *,
    require_frozen: bool = True,
) -> LoadedPreregistration:
    """Read, authenticate, and validate one preregistration file."""

    payload = _read_regular_file(path, "preregistration", MAX_JSON_BYTES)
    value = parse_strict_json_bytes(payload, path="$.preregistration")
    validated = validate_preregistration(value, require_frozen=require_frozen)
    if artifact_json_bytes(validated) != payload:
        _fail(
            "PREREGISTRATION_ENCODING_MISMATCH",
            "$.preregistration",
            "not canonical tracked encoding",
        )
    return LoadedPreregistration(
        data=validated,
        payload=payload,
        sha256="sha256:" + hashlib.sha256(payload).hexdigest(),
    )


def validate_prior_evidence_inputs(
    preregistration: Mapping[str, Any],
    *,
    manifest_payload: bytes,
    reproducibility_evidence_payload: bytes,
) -> dict[str, Any]:
    """Authenticate the prior package and clean replay artifacts by raw bytes."""

    lineage = preregistration["source_lineage"]
    _require_payload_sha256(
        manifest_payload,
        lineage["manifest"]["sha256"],
        "$.manifest_payload",
    )
    _require_payload_sha256(
        reproducibility_evidence_payload,
        lineage["reproducibility_evidence"]["sha256"],
        "$.reproducibility_evidence_payload",
    )
    manifest = _mapping(
        parse_strict_json_bytes(manifest_payload, path="$.manifest"), "$.manifest"
    )
    evidence = _mapping(
        parse_strict_json_bytes(
            reproducibility_evidence_payload, path="$.reproducibility_evidence"
        ),
        "$.reproducibility_evidence",
    )
    components = _mapping(manifest.get("components"), "$.manifest.components")
    base = _mapping(components.get("base_model"), "$.manifest.components.base_model")
    tokenizer = _mapping(
        components.get("tokenizer"), "$.manifest.components.tokenizer"
    )
    if (
        manifest.get("gate_id")
        != "FC-MVP-001-fp32-attached-offline-package-manifest-v1"
        or base.get("repo_id") != HUGGINGFACE_REPOSITORY
        or base.get("revision") != HUGGINGFACE_REVISION
        or tokenizer.get("repo_id") != HUGGINGFACE_REPOSITORY
        or tokenizer.get("revision") != HUGGINGFACE_REVISION
    ):
        _fail(
            "MANIFEST_REMOTE_IDENTITY_MISMATCH",
            "$.manifest.components",
            "base or tokenizer remote identity drift",
        )
    derived = _mapping(
        evidence.get("derived_claims"),
        "$.reproducibility_evidence.derived_claims",
    )
    if (
        evidence.get("gate_id")
        != "FC-MVP-001-fp32-attached-offline-package-reproducibility-v1"
        or evidence.get("classification") != REPRODUCIBILITY_CLASSIFICATION
        or evidence.get("formal_gate_passed") is not True
        or evidence.get("remaining_blocking_findings")
        != ["remote_revision_origin_unverified"]
        or derived.get("clean_location_resolution_established") is not True
        or derived.get("behavioral_reproducibility_established") is not True
        or derived.get("remote_revision_origin_attested") is not False
        or evidence.get("runtime_eligible") is not False
    ):
        _fail(
            "REPRODUCIBILITY_EVIDENCE_NOT_ELIGIBLE",
            "$.reproducibility_evidence",
            "prior gate decisions drifted",
        )
    return {
        "manifest": {
            "path": lineage["manifest"]["path"],
            "sha256": lineage["manifest"]["sha256"],
            "base_repository": HUGGINGFACE_REPOSITORY,
            "base_revision": HUGGINGFACE_REVISION,
        },
        "reproducibility_evidence": {
            "path": lineage["reproducibility_evidence"]["path"],
            "sha256": lineage["reproducibility_evidence"]["sha256"],
            "classification": REPRODUCIBILITY_CLASSIFICATION,
            "formal_gate_passed": True,
            "clean_location_resolution_established": True,
            "behavioral_reproducibility_established": True,
            "remote_revision_origin_attested": False,
            "remaining_blocking_findings": [
                "remote_revision_origin_unverified"
            ],
            "runtime_eligible": False,
        },
    }


def build_origin_attestation_evidence(
    preregistration: Mapping[str, Any],
    *,
    preregistration_sha256: str,
    protocol_freeze_commit: str,
    observed_at_utc: str,
    observations: Mapping[str, Any],
    manifest_payload: bytes,
    reproducibility_evidence_payload: bytes,
    protocol_source_payloads: Mapping[str, bytes],
) -> dict[str, Any]:
    """Validate one accepted online observation and derive the evidence object."""

    prereg = validate_preregistration(preregistration)
    _validate_sha256(preregistration_sha256, "$.preregistration_sha256")
    _validate_git_commit(protocol_freeze_commit, "$.protocol_freeze_commit")
    if UTC_TIMESTAMP_PATTERN.fullmatch(observed_at_utc) is None:
        _fail(
            "INVALID_OBSERVATION_TIMESTAMP",
            "$.observed_at_utc",
            repr(observed_at_utc),
        )
    prior = validate_prior_evidence_inputs(
        prereg,
        manifest_payload=manifest_payload,
        reproducibility_evidence_payload=reproducibility_evidence_payload,
    )
    expected_observations = copy.deepcopy(prereg["authority_contract"])
    observed = _mapping(observations, "$.observations")
    if observed != expected_observations:
        _fail(
            "REMOTE_AUTHORITY_OBSERVATION_MISMATCH",
            "$.observations",
            _first_difference(observed, expected_observations),
        )
    source_receipts = _protocol_source_receipts(
        prereg, protocol_source_payloads=protocol_source_payloads
    )
    gates = {
        "prior_evidence": True,
        "protocol_integrity": True,
        "github_repository": True,
        "github_commit": True,
        "github_tree": True,
        "github_content_bindings": True,
        "github_adapter_lfs": True,
        "huggingface_repository": True,
        "huggingface_tree": True,
        "huggingface_content_bindings": True,
    }
    classification = classify_origin_attestation_gates(gates)
    passed = classification == PASS_CLASSIFICATION
    remaining: list[str] = [] if passed else ["remote_revision_origin_unverified"]
    next_action = prereg["outcome_next_actions"]["passed" if passed else "adverse"]
    derived_claims = {
        "metadata_complete": True,
        "offline_package_identity_complete": True,
        "clean_location_resolution_established": True,
        "behavioral_reproducibility_established": True,
        "behavioral_reproducibility_scope": (
            "same_recorded_environment_exact_twenty_case_raw_and_compiled_output"
        ),
        "remote_revision_origin_attested": passed,
        "remote_revision_origin_scope": (
            "github_and_huggingface_https_hosted_revision_authorities"
        ),
        "author_identity_or_signature_attested": False,
        "supply_chain_signature_attested": False,
        "historical_transparency_log_attested": False,
        "cross_machine_reproducibility_established": False,
        "offline_artifact_eligible": False,
        "portable_package_eligible": False,
        "preferred_offline_candidate": False,
        "serving_readiness_established": False,
        "artifact_promotion_allowed": False,
        "merged_artifact_allowed": False,
        "runtime_eligible": False,
    }
    return {
        "evidence_version": EVIDENCE_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "gate_id": GATE_ID,
        "package_id": PACKAGE_ID,
        "candidate_id": CANDIDATE_ID,
        "preregistration": {
            "path": PREREGISTRATION_PATH,
            "sha256": preregistration_sha256,
            "freeze_status": "frozen",
        },
        "protocol_freeze_commit": protocol_freeze_commit,
        "protocol_sources": source_receipts,
        "observed_at_utc": observed_at_utc,
        "prior_evidence": prior,
        "collection": {
            "accepted_observation_runs": 1,
            "network_used": True,
            "fixed_https_requests": 5,
            "automatic_request_retries": 0,
            "alternate_repository_or_revision_used": False,
            "raw_response_bodies_stored": False,
            "lfs_signed_url_or_query_stored": False,
            "model_or_adapter_lfs_downloaded": False,
            "large_lfs_payload_bytes_read": 0,
            "model_loaded": False,
            "generation_calls": 0,
            "package_bytes_written": False,
        },
        "observations": copy.deepcopy(observed),
        "gates": gates,
        "classification": classification,
        "formal_gate_passed": passed,
        "derived_claims": derived_claims,
        "remaining_blocking_findings": remaining,
        "remaining_blocking_finding_count": len(remaining),
        "locked_next_action": {
            **copy.deepcopy(next_action),
            "classification": classification,
            "formal_gate_passed": passed,
            "eligible_to_start": passed,
            "remaining_blocking_findings": remaining,
            "artifact_promotion_allowed": False,
            "runtime_integration_allowed": False,
        },
        "constraints": copy.deepcopy(prereg["constraints"]),
        "claims": copy.deepcopy(prereg["claims"]),
        "model_artifact_saved": False,
        "tensor_payload_saved": False,
        "runtime_eligible": False,
    }


def classify_origin_attestation_gates(gates: Mapping[str, object]) -> str:
    """Derive one outcome classification from the closed Boolean gate set."""

    expected_keys = {
        "prior_evidence",
        "protocol_integrity",
        "github_repository",
        "github_commit",
        "github_tree",
        "github_content_bindings",
        "github_adapter_lfs",
        "huggingface_repository",
        "huggingface_tree",
        "huggingface_content_bindings",
    }
    if set(gates) != expected_keys or any(
        not isinstance(gates[key], bool) for key in expected_keys
    ):
        _fail("INVALID_GATE_SET", "$.gates", repr(gates))
    if not gates["prior_evidence"] or not gates["protocol_integrity"]:
        return TRUST_ROOT_INVALID_CLASSIFICATION
    if any(not gates[name] for name in expected_keys if name.startswith("github_")):
        return GITHUB_ORIGIN_FAILED_CLASSIFICATION
    if any(
        not gates[name] for name in expected_keys if name.startswith("huggingface_")
    ):
        return HUGGINGFACE_ORIGIN_FAILED_CLASSIFICATION
    return PASS_CLASSIFICATION


def validate_origin_attestation_evidence(
    preregistration_payload: bytes,
    evidence_payload: bytes,
    *,
    expected_preregistration_sha256: str,
    expected_evidence_sha256: str,
    expected_protocol_freeze_commit: str,
    manifest_payload: bytes,
    reproducibility_evidence_payload: bytes,
    protocol_source_payloads: Mapping[str, bytes],
) -> dict[str, Any]:
    """Authenticate the tracked artifact and independently rebuild all decisions."""

    _require_payload_sha256(
        preregistration_payload,
        expected_preregistration_sha256,
        "$.preregistration_payload",
    )
    _require_payload_sha256(
        evidence_payload, expected_evidence_sha256, "$.evidence_payload"
    )
    _validate_git_commit(
        expected_protocol_freeze_commit, "$.expected_protocol_freeze_commit"
    )
    preregistration = validate_preregistration(
        parse_strict_json_bytes(
            preregistration_payload, path="$.preregistration_payload"
        )
    )
    evidence = _mapping(
        parse_strict_json_bytes(evidence_payload, path="$.evidence_payload"),
        "$.evidence",
    )
    expected = build_origin_attestation_evidence(
        preregistration,
        preregistration_sha256=expected_preregistration_sha256,
        protocol_freeze_commit=expected_protocol_freeze_commit,
        observed_at_utc=str(evidence.get("observed_at_utc")),
        observations=_mapping(evidence.get("observations"), "$.evidence.observations"),
        manifest_payload=manifest_payload,
        reproducibility_evidence_payload=reproducibility_evidence_payload,
        protocol_source_payloads=protocol_source_payloads,
    )
    if evidence != expected:
        _fail(
            "EVIDENCE_RECOMPUTATION_MISMATCH",
            "$.evidence",
            _first_difference(evidence, expected),
        )
    if artifact_json_bytes(preregistration) != preregistration_payload:
        _fail(
            "PREREGISTRATION_ENCODING_MISMATCH",
            "$.preregistration",
            "not canonical tracked encoding",
        )
    if artifact_json_bytes(evidence) != evidence_payload:
        _fail(
            "EVIDENCE_ENCODING_MISMATCH",
            "$.evidence",
            "not canonical tracked encoding",
        )
    return {
        "frozen_gate_valid": True,
        "classification": expected["classification"],
        "formal_gate_passed": expected["formal_gate_passed"],
        "remote_revision_origin_attested": expected["derived_claims"][
            "remote_revision_origin_attested"
        ],
        "remaining_blocking_findings": expected["remaining_blocking_findings"],
        "next_gate": expected["locked_next_action"]["gate_id"],
        "offline_artifact_eligible": False,
        "portable_package_eligible": False,
        "preferred_offline_candidate": False,
        "runtime_eligible": False,
    }


def git_blob_sha1(payload: bytes) -> str:
    """Compute the Git blob object id for exact raw bytes."""

    header = f"blob {len(payload)}\0".encode("ascii")
    return hashlib.sha1(header + payload).hexdigest()  # noqa: S324


def artifact_json_bytes(value: object) -> bytes:
    """Return the tracked canonical JSON encoding with one final newline."""

    return canonical_json_bytes(value) + b"\n"


def canonical_json_bytes(value: object) -> bytes:
    """Return finite canonical UTF-8 JSON bytes."""

    _validate_finite_json(value, "$")
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def parse_strict_json_bytes(payload: bytes, *, path: str) -> Any:
    """Parse one finite UTF-8 JSON value while rejecting duplicate keys."""

    if len(payload) > MAX_JSON_BYTES:
        _fail("JSON_TOO_LARGE", path, str(len(payload)))
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        _fail("INVALID_UTF8", path, str(exc))
    try:
        value = json.loads(text, object_pairs_hook=_unique_object_pairs)
    except (json.JSONDecodeError, OriginAttestationError) as exc:
        if isinstance(exc, OriginAttestationError):
            raise
        _fail("INVALID_JSON", path, str(exc))
    _validate_finite_json(value, path)
    return value


def _protocol_source_receipts(
    preregistration: Mapping[str, Any],
    *,
    protocol_source_payloads: Mapping[str, bytes],
) -> dict[str, dict[str, Any]]:
    expected = preregistration["source_lineage"]["protocol_sources"]
    if set(protocol_source_payloads) != set(expected):
        _fail(
            "PROTOCOL_SOURCE_PAYLOAD_SET_MISMATCH",
            "$.protocol_source_payloads",
            repr(sorted(protocol_source_payloads)),
        )
    receipts: dict[str, dict[str, Any]] = {}
    for name in sorted(expected):
        payload = protocol_source_payloads[name]
        digest = "sha256:" + hashlib.sha256(payload).hexdigest()
        if digest != expected[name]["sha256"]:
            _fail(
                "PROTOCOL_SOURCE_HASH_MISMATCH",
                f"$.protocol_source_payloads.{name}",
                digest,
            )
        receipts[name] = {
            "path": expected[name]["path"],
            "sha256": digest,
            "bytes": len(payload),
        }
    return receipts


def _read_regular_file(path: Path, label: str, maximum: int) -> bytes:
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        _fail("MISSING_FILE", f"$.{label}", str(exc))
    if not resolved.is_file() or resolved.is_symlink():
        _fail("UNSAFE_FILE", f"$.{label}", str(resolved))
    size = resolved.stat().st_size
    if size > maximum:
        _fail("FILE_TOO_LARGE", f"$.{label}", str(size))
    return resolved.read_bytes()


def _mapping(value: object, path: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        _fail("EXPECTED_OBJECT", path, repr(value))
    return dict(value)


def _unique_object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail("DUPLICATE_JSON_KEY", "$", repr(key))
        result[key] = value
    return result


def _validate_finite_json(value: object, path: str) -> None:
    if isinstance(value, float):
        if not math.isfinite(value):
            _fail("NON_FINITE_NUMBER", path, repr(value))
        return
    if value is None or isinstance(value, (str, int, bool)):
        return
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                _fail("NON_STRING_KEY", path, repr(key))
            _validate_finite_json(child, f"{path}.{key}")
        return
    if isinstance(value, list | tuple):
        for index, child in enumerate(value):
            _validate_finite_json(child, f"{path}[{index}]")
        return
    _fail("INVALID_JSON_TYPE", path, type(value).__name__)


def _validate_sha256(value: object, path: str) -> None:
    if not isinstance(value, str) or SHA256_PATTERN.fullmatch(value) is None:
        _fail("INVALID_SHA256", path, repr(value))


def _validate_git_commit(value: object, path: str) -> None:
    if not isinstance(value, str) or GIT_COMMIT_PATTERN.fullmatch(value) is None:
        _fail("INVALID_GIT_COMMIT", path, repr(value))


def _require_payload_sha256(payload: bytes, expected: object, path: str) -> None:
    _validate_sha256(expected, path + ".expected_sha256")
    observed = "sha256:" + hashlib.sha256(payload).hexdigest()
    if observed != expected:
        _fail("PAYLOAD_SHA256_MISMATCH", path, observed)


def _first_difference(left: object, right: object, path: str = "$") -> str:
    if type(left) is not type(right):
        return f"{path}: type {type(left).__name__} != {type(right).__name__}"
    if isinstance(left, Mapping) and isinstance(right, Mapping):
        if set(left) != set(right):
            return f"{path}: keys {sorted(left)} != {sorted(right)}"
        for key in sorted(left):
            difference = _first_difference(left[key], right[key], f"{path}.{key}")
            if difference:
                return difference
        return ""
    if isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            return f"{path}: length {len(left)} != {len(right)}"
        for index, (left_item, right_item) in enumerate(zip(left, right, strict=True)):
            difference = _first_difference(
                left_item, right_item, f"{path}[{index}]"
            )
            if difference:
                return difference
        return ""
    if left != right:
        return f"{path}: {left!r} != {right!r}"
    return ""


def _fail(code: str, path: str, detail: str) -> NoReturn:
    raise OriginAttestationError(code, path, detail)


__all__ = [
    "COLLECTOR_SOURCE_PATH",
    "CONTRACT_SOURCE_PATH",
    "EVIDENCE_VERSION",
    "EXPERIMENT_ID",
    "GATE_ID",
    "GITHUB_CONTENT_BINDINGS",
    "HUGGINGFACE_FILES",
    "LoadedPreregistration",
    "OriginAttestationError",
    "PASS_CLASSIFICATION",
    "PASS_NEXT_GATE_ID",
    "PREREGISTRATION_PATH",
    "PROTOCOL_SOURCE_PATHS",
    "ZERO_SHA256",
    "artifact_json_bytes",
    "build_origin_attestation_evidence",
    "canonical_json_bytes",
    "classify_origin_attestation_gates",
    "expected_github_tree_entries",
    "expected_huggingface_remote_files",
    "expected_preregistration",
    "git_blob_sha1",
    "load_and_validate_preregistration",
    "parse_strict_json_bytes",
    "validate_origin_attestation_evidence",
    "validate_preregistration",
]
