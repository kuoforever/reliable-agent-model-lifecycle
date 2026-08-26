"""Self-contained FC-MVP-000 validation gate for Python 3.11-3.13."""

from __future__ import annotations

import ast
import hashlib
import json
import math
import os
import stat
import subprocess
import sys
import tomllib
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
TESTS = ROOT / "tests"
LANE_B_FIXTURE_ROOT = ROOT / "fixtures" / "lane_b_v1"
LANE_B_METADATA_PATH = LANE_B_FIXTURE_ROOT / "fixture-metadata.json"
LANE_B_VALID_BUNDLE_PATH = LANE_B_FIXTURE_ROOT / "valid" / "minimal-bundle.json"
LANE_B_SCHEMA_PATH = ROOT / "schemas" / "lane_b_capture_bundle_v1.schema.json"
TRAJECTORY_FIXTURE_ROOT = ROOT / "fixtures" / "multimodal_trajectory_v1"
TRAJECTORY_METADATA_PATH = TRAJECTORY_FIXTURE_ROOT / "fixture-metadata.json"
TRAJECTORY_TEXT_FIXTURE_PATH = TRAJECTORY_FIXTURE_ROOT / "valid" / "text-only.json"
TRAJECTORY_IMAGE_FIXTURE_PATH = (
    TRAJECTORY_FIXTURE_ROOT / "valid" / "image-grounded.json"
)
TRAJECTORY_SCHEMA_PATH = ROOT / "schemas" / "multimodal_trajectory_v1.schema.json"
GUI_GROUNDING_FIXTURE_ROOT = ROOT / "fixtures" / "gui_grounding_eval_v1"
GUI_GROUNDING_METADATA_PATH = GUI_GROUNDING_FIXTURE_ROOT / "fixture-metadata.json"
GUI_GROUNDING_SUITE_PATH = GUI_GROUNDING_FIXTURE_ROOT / "valid" / "suite.json"
GUI_GROUNDING_PREDICTIONS_PATH = (
    GUI_GROUNDING_FIXTURE_ROOT / "valid" / "synthetic-probe-predictions.json"
)
GUI_GROUNDING_SUITE_SCHEMA_PATH = (
    ROOT / "schemas" / "gui_grounding_eval_suite_v1.schema.json"
)
GUI_GROUNDING_PREDICTIONS_SCHEMA_PATH = (
    ROOT / "schemas" / "gui_grounding_predictions_v1.schema.json"
)
GUI_GROUNDING_REPORT_PATH = ROOT / "baseline" / "mm-002-gui-grounding-data-eval-v1.json"
MM003_PREREGISTRATION_PATH = (
    ROOT / "configs" / "mm003_multimodal_gui_action_model_baseline_v1.json"
)
MM003_PREREGISTRATION_SHA256 = (
    "sha256:0046143f2c8badb5b2eaa809ac4c7abce81d1c0a5156fe2668b4e5cf9668aa10"
)
MM003_FAILURE_CLASSIFICATION_PATH = (
    ROOT / "baseline" / "mm003-qwen2.5-vl-3b-baseline-v1-failure-classification.json"
)
MM003_RECOVERY_PREREGISTRATION_PATH = (
    ROOT / "configs" / "mm003_multimodal_gui_action_model_baseline_v2.json"
)
MM003_RECOVERY_PREREGISTRATION_SHA256 = (
    "sha256:369c813dee44b14c6022eb90739bcd37f9f8de472e60a8cee88682454d135403"
)
MM003_POST_TRAINING_PREREGISTRATION_PATH = (
    ROOT / "configs" / "mm003_small_vlm_post_training_protocol_v1.json"
)
MM003_POST_TRAINING_PREREGISTRATION_SHA256 = (
    "sha256:9dfd180f24a86814fc32c5ebbfca07a31f713c8387f85ec3212dc538647cb061"
)
MM003_POST_TRAINING_FAILURE_CLASSIFICATION_PATH = (
    ROOT
    / "baseline"
    / "mm003-qwen2.5-vl-3b-qlora-sft-v1-failure-classification.json"
)
MM003_POST_TRAINING_RECOVERY_PREREGISTRATION_PATH = (
    ROOT / "configs" / "mm003_small_vlm_post_training_protocol_v2.json"
)
MM003_POST_TRAINING_RECOVERY_PREREGISTRATION_SHA256 = (
    "sha256:02e36d5981e0ed4ac90bfdb3c5cc9c9e1f78ff29ff927020b0a41ebb27f55c0e"
)
MM003_POST_TRAINING_EVAL_REPEATABILITY_PREREGISTRATION_PATH = (
    ROOT / "configs" / "mm003_small_vlm_post_training_eval_repeatability_protocol_v1.json"
)
MM003_POST_TRAINING_EVAL_REPEATABILITY_PREREGISTRATION_BYTES = 22_951
MM003_POST_TRAINING_EVAL_REPEATABILITY_PREREGISTRATION_SHA256 = (
    "sha256:723db665f98e53ef2fe968ee7c6fe663b42d79b86176eef5cf70f11ccc4a312b"
)
MM004_HARD_NEGATIVE_PROTOCOL_PATH = (
    ROOT / "configs" / "mm004_multimodal_hard_negative_data_protocol_v1.json"
)
MM004_HARD_NEGATIVE_PROTOCOL_BYTES = 22_675
MM004_HARD_NEGATIVE_PROTOCOL_SHA256 = (
    "sha256:f31e009ed8316d59240e9767865a041e86f30325a1fd15f8a29891d56d418355"
)
MM004_HARD_NEGATIVE_GENERATION_PROTOCOL_PATH = (
    ROOT / "configs" / "mm004_multimodal_hard_negative_data_generation_v1.json"
)
MM004_HARD_NEGATIVE_GENERATION_PROTOCOL_BYTES = 10_522
MM004_HARD_NEGATIVE_GENERATION_PROTOCOL_SHA256 = (
    "sha256:c49e18ec570ff198dfa564fdb711b3ba45cf34e5934a9cb667e6a62e13a07ceb"
)
MM004_HARD_NEGATIVE_GENERATION_FREEZE_COMMIT = (
    "2d41b99e7e984975056f7e1088e768cd8a62b744"
)
MM004_HARD_NEGATIVE_MODEL_EVALUATION_PROTOCOL_V1_PATH = (
    ROOT
    / "configs"
    / "mm004_multimodal_hard_negative_model_evaluation_protocol_v1.json"
)
MM004_HARD_NEGATIVE_MODEL_EVALUATION_PROTOCOL_V1_BYTES = 49_311
MM004_HARD_NEGATIVE_MODEL_EVALUATION_PROTOCOL_V1_SHA256 = (
    "sha256:3011420f26bc61f572de2e21f96d28215529e495075db4e958573a4e4317484f"
)
MM004_HARD_NEGATIVE_MODEL_EVALUATION_PROTOCOL_V2_PATH = (
    ROOT
    / "configs"
    / "mm004_multimodal_hard_negative_model_evaluation_protocol_v2.json"
)
MM004_HARD_NEGATIVE_MODEL_EVALUATION_PROTOCOL_V2_BYTES = 50_642
MM004_HARD_NEGATIVE_MODEL_EVALUATION_PROTOCOL_V2_SHA256 = (
    "sha256:bee2093d54d95cc52303c57c598d99a071aff85bef9f56605adeb2b604f8c0d9"
)
MM005_ENVIRONMENT_ADAPTATION_PROTOCOL_PATH = (
    ROOT / "configs" / "mm005_multimodal_environment_adaptation_protocol_v1.json"
)
MM005_ENVIRONMENT_ADAPTATION_PROTOCOL_BYTES = 49_202
MM005_ENVIRONMENT_ADAPTATION_PROTOCOL_SHA256 = (
    "sha256:311822603bb6c05c1b7f388cd782c30556fa8b7aa0d67cbd1ccd89f9d13a532a"
)
MM005_DOCUMENT_CHART_PDF_DATA_PROTOCOL_PATH = (
    ROOT / "configs" / "mm005_document_chart_pdf_data_protocol_v1.json"
)
MM005_DOCUMENT_CHART_PDF_DATA_PROTOCOL_BYTES = 24_909
MM005_DOCUMENT_CHART_PDF_DATA_PROTOCOL_SHA256 = (
    "sha256:7e774e69194e6f70c27c9b53bbab68adb19874780757717ca42012ec48297525"
)
MM005_DOCUMENT_CHART_PDF_GENERATION_PROTOCOL_PATH = (
    ROOT / "configs" / "mm005_document_chart_pdf_data_generation_v1.json"
)
MM005_DOCUMENT_CHART_PDF_GENERATION_PROTOCOL_BYTES = 17_780
MM005_DOCUMENT_CHART_PDF_GENERATION_PROTOCOL_SHA256 = (
    "sha256:6e212237ee59d9730f97028769033a0991f9e3c6b893a404fc583274f813f2ed"
)
MM005_DOCUMENT_CHART_PDF_ADAPTER_VERIFIER_PROTOCOL_PATH = (
    ROOT / "configs" / "mm005_document_chart_pdf_adapter_verifier_protocol_v1.json"
)
MM005_DOCUMENT_CHART_PDF_ADAPTER_VERIFIER_PROTOCOL_BYTES = 126_032
MM005_DOCUMENT_CHART_PDF_ADAPTER_VERIFIER_PROTOCOL_SHA256 = (
    "sha256:4715134d7bd1f8ae54275764f342bf5a8974cc491298dbefd52971aab876c64a"
)
MM005_DOCUMENT_CHART_PDF_ADAPTER_VERIFIER_IMPLEMENTATION_EVIDENCE_PATH = (
    ROOT
    / "baseline"
    / "mm005-document-chart-pdf-adapter-verifier-implementation-v1.json"
)
MM005_DOCUMENT_CHART_PDF_ADAPTER_VERIFIER_IMPLEMENTATION_EVIDENCE_BYTES = 102_117
MM005_DOCUMENT_CHART_PDF_ADAPTER_VERIFIER_IMPLEMENTATION_EVIDENCE_SHA256 = (
    "sha256:d4cbe61cac4cff60c15e769c35e481ca93f71524b23bf0dad4ddf75095d17bf2"
)
MM005_DOCUMENT_CHART_PDF_MODEL_EVALUATION_PROTOCOL_PATH = (
    ROOT / "configs" / "mm005_document_chart_pdf_model_evaluation_protocol_v1.json"
)
MM005_DOCUMENT_CHART_PDF_MODEL_EVALUATION_PROTOCOL_BYTES = 58_414
MM005_DOCUMENT_CHART_PDF_MODEL_EVALUATION_PROTOCOL_SHA256 = (
    "sha256:cdb8d1ea09221763d87cd79ba752d9af8264ce49b7cf600eed338a073a04561b"
)
BASELINE_PATH = ROOT / "baseline" / "fc-mvp-000.json"
TOOL_ROUTER_BASELINE_PATH = ROOT / "baseline" / "fc-mvp-001-schema-eval.json"
TOOL_ROUTER_DATA_BASELINE_PATH = ROOT / "baseline" / "fc-mvp-001-data-v1.json"
TOOL_ROUTER_SAFETY_REPAIR_BASELINE_PATH = (
    ROOT / "baseline" / "fc-mvp-001-safety-repair-data-v2.json"
)
TOOL_ROUTER_MODEL_BASELINE_PATH = ROOT / "baseline" / "fc-mvp-001-base-model-v1.json"
TOOL_ROUTER_SFT_BASELINE_PATH = ROOT / "baseline" / "fc-mvp-001-lora-sft-v1.json"
TOOL_ROUTER_SFT_V2_BASELINE_PATH = ROOT / "baseline" / "fc-mvp-001-lora-sft-v2.json"
TOOL_ROUTER_FAILURE_CLASSIFICATION_PATH = (
    ROOT / "baseline" / "fc-mvp-001-lora-sft-v2-failure-classification.json"
)
TOOL_ROUTER_DECISION_COMPILATION_PATH = (
    ROOT / "baseline" / "fc-mvp-001-decision-compilation-v1.json"
)
TOOL_ROUTER_COMPILED_PREDICTIONS_PATH = (
    ROOT / "baseline" / "tool-router-lora-sft-v2-compiled-predictions.json"
)
TOOL_ROUTER_COMPILED_REPORT_PATH = (
    ROOT / "baseline" / "tool-router-lora-sft-v2-compiled-report.json"
)
TOOL_ROUTER_MERGE_STABILITY_PATH = (
    ROOT / "baseline" / "fc-mvp-001-bf16-merge-stability-v1.json"
)
TOOL_ROUTER_MERGE_NUMERICS_PATH = (
    ROOT / "baseline" / "fc-mvp-001-bf16-merge-numerics-v1.json"
)
TOOL_ROUTER_MERGE_REMEDIATION_PATH = (
    ROOT / "baseline" / "fc-mvp-001-bf16-merge-remediation-v1.json"
)
TOOL_ROUTER_FP32_MERGE_DRIFT_PATH = (
    ROOT / "baseline" / "fc-mvp-001-fp32-merge-drift-analysis-v1.json"
)
TOOL_ROUTER_FP32_ATTACHED_MERGE_ISOLATION_PATH = (
    ROOT / "baseline" / "fc-mvp-001-fp32-attached-merge-isolation-v1.json"
)
TOOL_ROUTER_FP32_ATTACHED_MERGE_NUMERICS_PATH = (
    ROOT / "baseline" / "fc-mvp-001-fp32-attached-merge-numerics-v1.json"
)
TOOL_ROUTER_FP32_ATTACHED_MERGE_NUMERICS_TENSORS_PATH = (
    ROOT / "baseline" / "fc-mvp-001-fp32-attached-merge-numerics-v1-tensors.bin"
)
TOOL_ROUTER_ATTACHED_DTYPE_ISOLATION_PATH = (
    ROOT / "baseline" / "fc-mvp-001-attached-dtype-isolation-v1.json"
)
TOOL_ROUTER_ATTACHED_DTYPE_NUMERICS_PATH = (
    ROOT / "baseline" / "fc-mvp-001-attached-dtype-numerics-v1.json"
)
TOOL_ROUTER_ATTACHED_DTYPE_BOUNDARY_CONTROL_PATH = (
    ROOT / "baseline" / "fc-mvp-001-attached-dtype-boundary-control-v1.json"
)
TOOL_ROUTER_FP32_ATTACHED_REMEDIATION_PREREGISTRATION_PATH = (
    ROOT / "configs" / "tool_router_fp32_attached_remediation_eval_v1.json"
)
TOOL_ROUTER_FP32_ATTACHED_REMEDIATION_PREDICTIONS_PATH = (
    ROOT / "baseline" / "tool-router-fp32-attached-remediation-v1-predictions.json"
)
TOOL_ROUTER_FP32_ATTACHED_REMEDIATION_EVAL_PATH = (
    ROOT / "baseline" / "fc-mvp-001-fp32-attached-remediation-eval-v1.json"
)
TOOL_ROUTER_FP32_ATTACHED_ARTIFACT_ELIGIBILITY_REVIEW_PATH = (
    ROOT / "baseline" / "fc-mvp-001-fp32-attached-artifact-eligibility-review-v1.json"
)
TOOL_ROUTER_FP32_ATTACHED_OFFLINE_PACKAGE_MANIFEST_PATH = (
    ROOT / "baseline" / "fc-mvp-001-fp32-attached-offline-package-manifest-v1.json"
)
TOOL_ROUTER_FP32_ATTACHED_OFFLINE_PACKAGE_MANIFEST_SHA256 = (
    "sha256:4125f2eef2a4b8f07015169ac7fb77b830514e053a4624aa703e5f5a64943eb0"
)
TOOL_ROUTER_FP32_ATTACHED_OFFLINE_PACKAGE_SOURCE_HASHES = {
    "adapter_config": (
        "sha256:8eb104c3af2f4deb3abe5e471b3d3a74cb306683c1fdadb95488de981ba14c16"
    ),
    "adapter_inspector_source": (
        "sha256:3fa9dca9d5b309b9401be25dd3538ccbdf76df63d0eda67230a45152703c5452"
    ),
    "adapter_readme": (
        "sha256:353053cad9659d849cbf1fdacc7d9b86b82fb72197e2d101785843a4109bc522"
    ),
    "adapter_weights": (
        "sha256:efb62471e105b8ef25641200967d447b8cc2f3ff565937bc47193fbf79f4f342"
    ),
    "canonical_json_source": (
        "sha256:05cfe603d4786fb536cc1f99952a55fd211cc0fea2c210b32b575fefda9537d3"
    ),
    "decision_compiler_source": (
        "sha256:16f162a84572c7f0782890aef5aafbaafa1862e14938fe08b0ea6e97efa05157"
    ),
    "manifest_builder_source": (
        "sha256:7834a35854e14863de4312319fcf109681a14f42bf2d7eee3a385a1376427284"
    ),
    "manifest_contract_source": (
        "sha256:8e7b09f914ab45bdbe4841ebf3c06eb75ce9eabf0d2ce9ba2cb8de3ca48d383d"
    ),
    "model_downloader_source": (
        "sha256:1d0d3321a55b185128de020f4b5a2a9c3ecc22f5abb0535c4712c4fd545d3a28"
    ),
    "package_documentation": (
        "sha256:a531b0e462aad15a1ec9eb001d05c8cf71b5a72bde66437a499d0c6efba9cb24"
    ),
    "package_init_source": (
        "sha256:45cabb5da1c0e7c2c93ef045904cf4555b0c755baf1ec2eaf47330a1aab6008e"
    ),
    "prompt": (
        "sha256:4a7d15063b0b074ef999c2848d0fc073a6cc00ed4999ea81f770e2e42cfa6d97"
    ),
    "remediation_preregistration": (
        "sha256:5e7b0665f97f5cee760637236f80039c4e621ae0f24915c0ac749d885a683c8b"
    ),
    "sft_config": (
        "sha256:110ada11d69f4e83c4b93da0304e62151059115487e90394d32835f6916365c8"
    ),
    "sft_helpers_source": (
        "sha256:db881e5e5955341acb735416d93062a40cf512b63ec50eb8c196ddb4371bd020"
    ),
    "training_lock": (
        "sha256:e6e23f51834b1815578368ce54c78034e72a7158395892e77fdf75594548931f"
    ),
    "upstream_review": (
        "sha256:81977f318c6bcfed8d3844575dc245d4b94c2636a2359165f9aa5553c9b006f8"
    ),
    "validation_error_source": (
        "sha256:bb3cda72585bc84bf0cf84c5736cafe29c8dfc8bca5a851d82ecfed35b1b883d"
    ),
}
TOOL_ROUTER_FP32_ATTACHED_OFFLINE_PACKAGE_REPRODUCIBILITY_PREREGISTRATION_PATH = (
    ROOT / "configs" / "tool_router_fp32_attached_offline_package_reproducibility_v1.json"
)
TOOL_ROUTER_FP32_ATTACHED_OFFLINE_PACKAGE_REPRODUCIBILITY_PREREGISTRATION_SHA256 = (
    "sha256:982d039b2b591d2dab80d489bbbada252c764c82fce94334580807616b22ffff"
)
TOOL_ROUTER_FP32_ATTACHED_OFFLINE_PACKAGE_REPRODUCIBILITY_PREDICTIONS_PATH = (
    ROOT
    / "baseline"
    / "tool-router-fp32-attached-offline-package-reproducibility-v1-predictions.json"
)
TOOL_ROUTER_FP32_ATTACHED_OFFLINE_PACKAGE_REPRODUCIBILITY_PREDICTIONS_SHA256 = (
    "sha256:a0e99e80e091d3d6c191e3863449a6a5298d7f0d3a23cc6d786968562e6d2a46"
)
TOOL_ROUTER_FP32_ATTACHED_OFFLINE_PACKAGE_REPRODUCIBILITY_EVIDENCE_PATH = (
    ROOT / "baseline" / "fc-mvp-001-fp32-attached-offline-package-reproducibility-v1.json"
)
TOOL_ROUTER_FP32_ATTACHED_OFFLINE_PACKAGE_REPRODUCIBILITY_EVIDENCE_SHA256 = (
    "sha256:0e0d2174f4723ab42a5c11375cee10a819e32737810f63111d098decc2984044"
)
TOOL_ROUTER_FP32_ATTACHED_OFFLINE_PACKAGE_REPRODUCIBILITY_FREEZE_COMMIT = (
    "eafd3f646e4ec08dd0a1f76443ccfd416e81fa22"
)
TOOL_ROUTER_FP32_ATTACHED_REMOTE_ORIGIN_PREREGISTRATION_PATH = (
    ROOT
    / "configs"
    / "tool_router_fp32_attached_remote_revision_origin_attestation_v1.json"
)
TOOL_ROUTER_FP32_ATTACHED_REMOTE_ORIGIN_PREREGISTRATION_SHA256 = (
    "sha256:0523caa79ab820e4de892e25f7e94e0081c1086e0255e286c6f202bbc382667e"
)
TOOL_ROUTER_FP32_ATTACHED_REMOTE_ORIGIN_EVIDENCE_PATH = (
    ROOT
    / "baseline"
    / "fc-mvp-001-fp32-attached-remote-revision-origin-attestation-v1.json"
)
TOOL_ROUTER_FP32_ATTACHED_REMOTE_ORIGIN_EVIDENCE_SHA256 = (
    "sha256:cdde41aed18e2fecccea1833f16cea4fc808eb5d212376c96f3e2763fcef7cfd"
)
TOOL_ROUTER_FP32_ATTACHED_REMOTE_ORIGIN_FREEZE_COMMIT = (
    "d0f9a6988ef9702c713402bb179d7524e5e12c7f"
)
TOOL_ROUTER_FP32_ATTACHED_OFFLINE_ARTIFACT_REASSESSMENT_PREREGISTRATION_PATH = (
    ROOT
    / "configs"
    / "tool_router_fp32_attached_offline_artifact_eligibility_"
    "reassessment_v1.json"
)
TOOL_ROUTER_FP32_ATTACHED_OFFLINE_ARTIFACT_REASSESSMENT_PREREGISTRATION_SHA256 = (
    "sha256:f1fc627d3d20f9c954f93e0cd4c930b22f592c48d2f4af72220c184f2e32c662"
)
TOOL_ROUTER_FP32_ATTACHED_OFFLINE_ARTIFACT_REASSESSMENT_EVIDENCE_PATH = (
    ROOT
    / "baseline"
    / "fc-mvp-001-fp32-attached-offline-artifact-eligibility-"
    "reassessment-v1.json"
)
TOOL_ROUTER_FP32_ATTACHED_OFFLINE_ARTIFACT_REASSESSMENT_EVIDENCE_SHA256 = (
    "sha256:0cccb2a7c7cdc24c824ee0ca4606f8c14e9b561473e50e8b31072291357b15ed"
)
TOOL_ROUTER_FP32_ATTACHED_OFFLINE_ARTIFACT_REASSESSMENT_FREEZE_COMMIT = (
    "2a5db8afaf90a3557d6d8d8cd808089d305d83e1"
)
TOOL_ROUTER_FP32_ATTACHED_PREFERRED_CANDIDATE_PREREGISTRATION_PATH = (
    ROOT
    / "configs"
    / "tool_router_fp32_attached_preferred_offline_candidate_decision_v1.json"
)
TOOL_ROUTER_FP32_ATTACHED_PREFERRED_CANDIDATE_PREREGISTRATION_SHA256 = (
    "sha256:75f25ceebb6a9428ad3d92f4ecc778d8725e1d52e32367ff8db3cb2ac3125f21"
)
TOOL_ROUTER_FP32_ATTACHED_PREFERRED_CANDIDATE_EVIDENCE_PATH = (
    ROOT
    / "baseline"
    / "fc-mvp-001-fp32-attached-preferred-offline-candidate-decision-v1.json"
)
TOOL_ROUTER_FP32_ATTACHED_PREFERRED_CANDIDATE_EVIDENCE_SHA256 = (
    "sha256:02f66ed79edce17803ddc1ed172c35a995be4ee8ed984cdd49b4e24bc5748c55"
)
TOOL_ROUTER_FP32_ATTACHED_PREFERRED_CANDIDATE_FREEZE_COMMIT = (
    "1f9aeecda71ad7f758a905b1eec3dccb3885e10f"
)
SUPPORTED_MINORS = {(3, 11), (3, 12), (3, 13)}
FORBIDDEN_IMPORT_ROOTS = frozenset(
    {
        "computer_use_agent",
        "computer_use_mcp",
        "httpx",
        "mcp",
        "requests",
        "socket",
        "urllib",
        "webbrowser",
    }
)


class GateError(RuntimeError):
    pass


def main() -> int:
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    os.environ["PYTHONPATH"] = str(SRC)
    sys.path.insert(0, str(SRC))
    sys.path.insert(0, str(ROOT))

    version = (sys.version_info.major, sys.version_info.minor)
    if version not in SUPPORTED_MINORS:
        raise GateError(f"unsupported Python minor: {version[0]}.{version[1]}")

    baseline = _load_json(BASELINE_PATH)
    _validate_project_metadata(baseline)
    _validate_artifact_hashes(baseline)
    audited_files = _audit_import_boundary()
    (
        bridge_summary,
        record_count,
        router_summary,
        data_report,
        safety_repair_report,
        model_metrics,
        sft_metrics,
        sft_v2_metrics,
        failure_classification,
        decision_compilation,
    ) = _validate_fixed_outputs()
    merge_stability = _validate_merge_stability()
    merge_numerics = _validate_merge_numerics(merge_stability)
    merge_remediation = _validate_merge_remediation(
        merge_stability,
        merge_numerics,
    )
    fp32_merge_drift = _validate_fp32_merge_drift(merge_remediation)
    fp32_attached_merge_isolation = _validate_fp32_attached_merge_isolation(
        fp32_merge_drift
    )
    fp32_attached_merge_numerics = _validate_fp32_attached_merge_numerics(
        fp32_attached_merge_isolation
    )
    attached_dtype_isolation = _validate_attached_dtype_isolation(
        fp32_attached_merge_numerics
    )
    attached_dtype_numerics = _validate_attached_dtype_numerics(
        attached_dtype_isolation
    )
    attached_dtype_boundary_control = _validate_attached_dtype_boundary_control(
        attached_dtype_numerics
    )
    fp32_attached_remediation_eval = _validate_fp32_attached_remediation_eval(
        attached_dtype_boundary_control
    )
    fp32_attached_artifact_eligibility = _validate_fp32_attached_artifact_eligibility(
        fp32_attached_remediation_eval
    )
    fp32_attached_offline_package = _validate_fp32_attached_offline_package_manifest(
        fp32_attached_artifact_eligibility
    )
    fp32_attached_offline_package_reproducibility = (
        _validate_fp32_attached_offline_package_reproducibility(
            fp32_attached_offline_package
        )
    )
    fp32_attached_remote_origin = _validate_fp32_attached_remote_origin(
        fp32_attached_offline_package_reproducibility
    )
    fp32_attached_offline_artifact_reassessment = (
        _validate_fp32_attached_offline_artifact_reassessment(
            fp32_attached_remote_origin
        )
    )
    fp32_attached_preferred_candidate = (
        _validate_fp32_attached_preferred_candidate(
            fp32_attached_offline_artifact_reassessment
        )
    )
    lane_b_contract = _validate_lane_b_contract()
    trajectory_contract = _validate_multimodal_trajectory_contract()
    gui_grounding_eval = _validate_gui_grounding_eval()
    mm003_baseline_protocol = _validate_mm003_baseline_protocol()
    mm003_failure = _validate_mm003_baseline_failure_classification()
    mm003_recovery = _validate_mm003_baseline_recovery_protocol()
    mm003_baseline_v2 = _validate_mm003_baseline_v2_evidence()
    mm003_post_training = _validate_mm003_post_training_protocol()
    mm003_post_training_failure = (
        _validate_mm003_post_training_failure_classification()
    )
    mm003_post_training_recovery = (
        _validate_mm003_post_training_recovery_protocol()
    )
    mm003_post_training_result = _validate_mm003_post_training_result_review()
    mm003_post_training_repeatability = (
        _validate_mm003_post_training_eval_repeatability_protocol()
    )
    mm003_post_training_repeatability_result = (
        _validate_mm003_post_training_eval_repeatability_result()
    )
    mm004_hard_negative_protocol = _validate_mm004_hard_negative_protocol()
    mm004_hard_negative_generation = (
        _validate_mm004_hard_negative_generation_protocol()
    )
    mm004_hard_negative_model_evaluation = (
        _validate_mm004_hard_negative_model_evaluation_protocol()
    )
    mm004_hard_negative_model_evaluation_result = (
        _validate_mm004_hard_negative_model_evaluation_result_review()
    )
    mm005_environment_adaptation = _validate_mm005_environment_adaptation_protocol()
    mm005_document_chart_pdf_data = _validate_mm005_document_chart_pdf_data_protocol()
    mm005_document_chart_pdf_generation = (
        _validate_mm005_document_chart_pdf_generation_protocol()
    )
    mm005_document_chart_pdf_adapter_verifier = (
        _validate_mm005_document_chart_pdf_adapter_verifier_protocol()
    )
    mm005_document_chart_pdf_adapter_verifier_implementation = (
        _validate_mm005_document_chart_pdf_adapter_verifier_implementation()
    )
    mm005_document_chart_pdf_model_evaluation = (
        _validate_mm005_document_chart_pdf_model_evaluation_protocol()
    )
    tests_run = _run_tests()

    result = {
        "valid": True,
        "baseline_version": baseline["baseline_version"],
        "source_code_commit": baseline["source_code_commit"],
        "python": sys.version.split()[0],
        "implementation": sys.implementation.name,
        "runtime_dependencies": 0,
        "artifact_hashes_verified": len(baseline["artifacts"]),
        "source_files_audited": audited_files,
        "tests_run": tests_run,
        "manifest_digest": bridge_summary.manifest_digest,
        "dataset_records": record_count,
        "lane_b_contract_review_complete": lane_b_contract["contract_review_complete"],
        "lane_b_bundle_version": lane_b_contract["bundle_version"],
        "lane_b_consent_version": lane_b_contract["consent_version"],
        "lane_b_episode_version": lane_b_contract["episode_version"],
        "lane_b_deletion_receipt_version": lane_b_contract["deletion_receipt_version"],
        "lane_b_artifact_references": lane_b_contract["artifact_count"],
        "lane_b_steps": lane_b_contract["step_count"],
        "lane_b_deletion_verified": lane_b_contract["deletion_verified"],
        "lane_b_training_eligible": lane_b_contract["training_eligible"],
        "lane_b_capture_adapter_implemented": lane_b_contract[
            "capture_adapter_implemented"
        ],
        "lane_b_next_gate": lane_b_contract["next_gate"],
        "multimodal_trajectory_schema_review_complete": trajectory_contract[
            "schema_review_complete"
        ],
        "multimodal_trajectory_schema_version": trajectory_contract["schema_version"],
        "multimodal_trajectory_modalities": trajectory_contract["modalities"],
        "multimodal_trajectory_text_artifacts": trajectory_contract["text_artifacts"],
        "multimodal_trajectory_image_artifacts": trajectory_contract["image_artifacts"],
        "multimodal_trajectory_image_previous_steps": trajectory_contract[
            "image_previous_steps"
        ],
        "multimodal_trajectory_training_eligible": trajectory_contract[
            "training_eligible"
        ],
        "multimodal_trajectory_execution_eligible": trajectory_contract[
            "execution_eligible"
        ],
        "multimodal_trajectory_real_episode_collected": trajectory_contract[
            "real_episode_collected"
        ],
        "multimodal_trajectory_next_gate": trajectory_contract["next_gate"],
        "gui_grounding_data_eval_review_complete": gui_grounding_eval[
            "review_complete"
        ],
        "gui_grounding_case_count": gui_grounding_eval["case_count"],
        "gui_grounding_metrics": gui_grounding_eval["metrics"],
        "gui_grounding_model_evaluated": gui_grounding_eval["model_evaluated"],
        "gui_grounding_training_eligible": gui_grounding_eval[
            "training_eligible"
        ],
        "gui_grounding_next_gate": gui_grounding_eval["next_gate"],
        "mm003_baseline_protocol_frozen": mm003_baseline_protocol["protocol_frozen"],
        "mm003_baseline_model": mm003_baseline_protocol["model_id"],
        "mm003_baseline_model_revision": mm003_baseline_protocol["model_revision"],
        "mm003_baseline_cases": mm003_baseline_protocol["case_count"],
        "mm003_baseline_v1_model_evaluated": mm003_baseline_protocol[
            "model_evaluated"
        ],
        "mm003_baseline_attempted": mm003_failure["baseline_attempted"],
        "mm003_baseline_v1_formal_gate_passed": mm003_failure[
            "formal_gate_passed"
        ],
        "mm003_baseline_failure_classification": mm003_failure["classification"],
        "mm003_baseline_failure_next_gate": mm003_failure["next_gate"],
        "mm003_recovery_protocol_frozen": mm003_recovery["protocol_frozen"],
        "mm003_recovery_protocol_sources": mm003_recovery["source_files"],
        "mm003_recovery_optional_metric_total": mm003_recovery[
            "optional_metric_total"
        ],
        "mm003_recovery_next_gate": mm003_recovery["next_gate"],
        "mm003_baseline_v2_formal_gate_passed": mm003_baseline_v2[
            "formal_gate_passed"
        ],
        "mm003_baseline_v2_model_evaluated": mm003_baseline_v2[
            "model_evaluated"
        ],
        "mm003_baseline_formal_gate_passed": mm003_baseline_v2[
            "formal_gate_passed"
        ],
        "mm003_baseline_model_evaluated": mm003_baseline_v2["model_evaluated"],
        "mm003_baseline_v2_classification": mm003_baseline_v2["classification"],
        "mm003_baseline_v2_fallback_count": mm003_baseline_v2["fallback_count"],
        "mm003_baseline_v2_grounding_accuracy": mm003_baseline_v2[
            "grounding_accuracy"
        ]["value"],
        "mm003_baseline_v2_action_accuracy": mm003_baseline_v2[
            "action_accuracy"
        ]["value"],
        "mm003_baseline_next_gate": mm003_baseline_v2["next_gate"],
        "mm003_post_training_protocol_frozen": mm003_post_training["protocol_frozen"],
        "mm003_post_training_train_records": mm003_post_training["train_records"],
        "mm003_post_training_validation_records": mm003_post_training[
            "validation_records"
        ],
        "mm003_post_training_screenshots": mm003_post_training["screenshots"],
        "mm003_post_training_eval_isolation": mm003_post_training["eval_isolation"],
        "mm003_post_training_protocol_next_gate": mm003_post_training["next_gate"],
        "mm003_post_training_execution_attempted": mm003_post_training_failure[
            "execution_attempted"
        ],
        "mm003_post_training_v1_formal_gate_passed": mm003_post_training_failure[
            "formal_gate_passed"
        ],
        "mm003_post_training_failure_classification": mm003_post_training_failure[
            "classification"
        ],
        "mm003_post_training_failure_receipt_sha256": mm003_post_training_failure[
            "receipt_sha256"
        ],
        "mm003_post_training_next_gate": mm003_post_training_failure["next_gate"],
        "mm003_post_training_recovery_protocol_frozen": (
            mm003_post_training_recovery["protocol_frozen"]
        ),
        "mm003_post_training_recovery_source_files": (
            mm003_post_training_recovery["source_files"]
        ),
        "mm003_post_training_recovery_prompt_receipts": (
            mm003_post_training_recovery["prompt_receipts"]
        ),
        "mm003_post_training_recovery_replacements": (
            mm003_post_training_recovery["exact_value_replacements"]
        ),
        "mm003_post_training_recovery_next_gate": (
            mm003_post_training_recovery["next_gate"]
        ),
        "mm003_post_training_v2_formal_gate_passed": (
            mm003_post_training_result["formal_gate_passed"]
        ),
        "mm003_post_training_v2_adapter_independently_loadable": (
            mm003_post_training_result["adapter_independently_loadable"]
        ),
        "mm003_post_training_v2_model_evaluated": (
            mm003_post_training_result["model_evaluated"]
        ),
        "mm003_post_training_v2_compiler_fallback_count": (
            mm003_post_training_result["compiler_fallback_count"]
        ),
        "mm003_post_training_v2_grounding_accuracy": (
            mm003_post_training_result["grounding_accuracy"]["value"]
        ),
        "mm003_post_training_v2_action_accuracy": (
            mm003_post_training_result["action_accuracy"]["value"]
        ),
        "mm003_post_training_v2_repeatability_established": (
            mm003_post_training_result["repeatability_established"]
        ),
        "mm003_post_training_v2_next_gate": (
            mm003_post_training_result["next_gate"]
        ),
        "mm003_post_training_eval_repeatability_protocol_frozen": (
            mm003_post_training_repeatability["protocol_frozen"]
        ),
        "mm003_post_training_eval_repeatability_source_files": (
            mm003_post_training_repeatability["source_files"]
        ),
        "mm003_post_training_eval_repeatability_required_gates": (
            mm003_post_training_repeatability["required_gates"]
        ),
        "mm003_post_training_eval_repeatability_case_count": (
            mm003_post_training_repeatability["case_count"]
        ),
        "mm003_post_training_eval_repeatability_next_gate": (
            mm003_post_training_repeatability["next_gate"]
        ),
        "mm003_post_training_eval_repeatability_formal_gate_passed": (
            mm003_post_training_repeatability_result["formal_gate_passed"]
        ),
        "mm003_post_training_eval_repeatability_all_layers_exact": (
            mm003_post_training_repeatability_result["all_layers_exact"]
        ),
        "mm003_post_training_eval_repeatability_raw_outputs_exact": (
            mm003_post_training_repeatability_result["raw_outputs_exact"]
        ),
        "mm003_post_training_eval_repeatability_generated_token_counts_exact": (
            mm003_post_training_repeatability_result[
                "generated_token_counts_exact"
            ]
        ),
        "mm003_post_training_eval_repeatability_compiled_predictions_exact": (
            mm003_post_training_repeatability_result[
                "compiled_predictions_exact"
            ]
        ),
        "mm003_post_training_eval_repeatability_compiler_fallback_status_exact": (
            mm003_post_training_repeatability_result[
                "compiler_fallback_status_exact"
            ]
        ),
        "mm003_post_training_eval_repeatability_metrics_exact": (
            mm003_post_training_repeatability_result["metrics_exact"]
        ),
        "mm003_post_training_eval_repeatability_established": (
            mm003_post_training_repeatability_result[
                "same_machine_eval_repeatability_established"
            ]
        ),
        "mm003_post_training_eval_repeatability_training_repeatability_established": (
            mm003_post_training_repeatability_result[
                "training_repeatability_established"
            ]
        ),
        "mm003_post_training_eval_repeatability_result_next_gate": (
            mm003_post_training_repeatability_result["next_gate"]
        ),
        "mm004_hard_negative_protocol_frozen": mm004_hard_negative_protocol[
            "protocol_frozen"
        ],
        "mm004_hard_negative_categories": mm004_hard_negative_protocol[
            "category_count"
        ],
        "mm004_hard_negative_excluded_cases": mm004_hard_negative_protocol[
            "excluded_case_count"
        ],
        "mm004_hard_negative_excluded_families": mm004_hard_negative_protocol[
            "excluded_family_count"
        ],
        "mm004_hard_negative_records_generated": mm004_hard_negative_protocol[
            "records_generated"
        ],
        "mm004_hard_negative_next_gate": mm004_hard_negative_protocol["next_gate"],
        "mm004_hard_negative_generation_protocol_frozen": (
            mm004_hard_negative_generation["protocol_frozen"]
        ),
        "mm004_hard_negative_generation_planned_families": (
            mm004_hard_negative_generation["planned_families"]
        ),
        "mm004_hard_negative_generation_planned_records": (
            mm004_hard_negative_generation["planned_records"]
        ),
        "mm004_hard_negative_generation_planned_images": (
            mm004_hard_negative_generation["planned_images"]
        ),
        "mm004_hard_negative_generation_executed": (
            mm004_hard_negative_generation["generation_executed"]
        ),
        "mm004_hard_negative_generation_dataset_validated": (
            mm004_hard_negative_generation["dataset_validated"]
        ),
        "mm004_hard_negative_generation_families": (
            mm004_hard_negative_generation["family_count"]
        ),
        "mm004_hard_negative_generation_pairs": (
            mm004_hard_negative_generation["pair_count"]
        ),
        "mm004_hard_negative_generation_records": (
            mm004_hard_negative_generation["record_count"]
        ),
        "mm004_hard_negative_generation_train_records": (
            mm004_hard_negative_generation["train_records"]
        ),
        "mm004_hard_negative_generation_validation_records": (
            mm004_hard_negative_generation["validation_records"]
        ),
        "mm004_hard_negative_generation_images": (
            mm004_hard_negative_generation["image_count"]
        ),
        "mm004_hard_negative_generation_output_files": (
            mm004_hard_negative_generation["output_files"]
        ),
        "mm004_hard_negative_generation_output_bytes": (
            mm004_hard_negative_generation["output_bytes"]
        ),
        "mm004_hard_negative_generation_evidence_sha256": (
            mm004_hard_negative_generation["evidence_sha256"]
        ),
        "mm004_hard_negative_generation_model_evaluated": (
            mm004_hard_negative_generation["model_evaluated"]
        ),
        "mm004_hard_negative_generation_safety_established": (
            mm004_hard_negative_generation["safety_established"]
        ),
        "mm004_hard_negative_generation_runtime_eligible": (
            mm004_hard_negative_generation["runtime_eligible"]
        ),
        "mm004_hard_negative_generation_next_gate": (
            mm004_hard_negative_generation["next_gate"]
        ),
        "mm004_hard_negative_model_evaluation_protocol_frozen": (
            mm004_hard_negative_model_evaluation["protocol_frozen"]
        ),
        "mm004_hard_negative_model_evaluation_protocol_version": (
            mm004_hard_negative_model_evaluation["protocol_version"]
        ),
        "mm004_hard_negative_model_evaluation_v1_attempt_consumed": (
            mm004_hard_negative_model_evaluation["predecessor_attempt_consumed"]
        ),
        "mm004_hard_negative_model_evaluation_v1_model_imported": (
            mm004_hard_negative_model_evaluation["predecessor_model_imported"]
        ),
        "mm004_hard_negative_model_evaluation_v1_model_calls": (
            mm004_hard_negative_model_evaluation["predecessor_model_calls"]
        ),
        "mm004_hard_negative_model_evaluation_v1_output_absent": (
            mm004_hard_negative_model_evaluation["predecessor_output_absent"]
        ),
        "mm004_hard_negative_model_evaluation_v1_classification": (
            mm004_hard_negative_model_evaluation["predecessor_classification"]
        ),
        "mm004_hard_negative_model_evaluation_registered_records": (
            mm004_hard_negative_model_evaluation["registered_records"]
        ),
        "mm004_hard_negative_model_evaluation_registered_pairs": (
            mm004_hard_negative_model_evaluation["registered_pairs"]
        ),
        "mm004_hard_negative_model_evaluation_registered_images": (
            mm004_hard_negative_model_evaluation["registered_images"]
        ),
        "mm004_hard_negative_model_evaluation_protocol_next_gate": (
            mm004_hard_negative_model_evaluation["next_gate"]
        ),
        "mm004_hard_negative_model_evaluation_result_reviewed": True,
        "mm004_hard_negative_model_evaluation_formal_gate_passed": (
            mm004_hard_negative_model_evaluation_result["formal_gate_passed"]
        ),
        "mm004_hard_negative_model_evaluation_classification": (
            mm004_hard_negative_model_evaluation_result["classification"]
        ),
        "mm004_hard_negative_model_evaluation_executed": (
            mm004_hard_negative_model_evaluation_result["evaluation_executed"]
        ),
        "mm004_hard_negative_model_evaluation_model_evaluated": (
            mm004_hard_negative_model_evaluation_result["model_evaluated"]
        ),
        "mm004_hard_negative_model_evaluation_training_executed": (
            mm004_hard_negative_model_evaluation_result["training_executed"]
        ),
        "mm004_hard_negative_model_evaluation_overall_accuracy": (
            mm004_hard_negative_model_evaluation_result["overall_accuracy"]
        ),
        "mm004_hard_negative_model_evaluation_clean_accept_recall": (
            mm004_hard_negative_model_evaluation_result["clean_accept_recall"]
        ),
        "mm004_hard_negative_model_evaluation_hard_negative_rejection_recall": (
            mm004_hard_negative_model_evaluation_result[
                "hard_negative_rejection_recall"
            ]
        ),
        "mm004_hard_negative_model_evaluation_pair_exact_accuracy": (
            mm004_hard_negative_model_evaluation_result["pair_exact_accuracy"]
        ),
        "mm004_hard_negative_model_evaluation_compiler_validity": (
            mm004_hard_negative_model_evaluation_result["compiler_validity"]
        ),
        "mm004_hard_negative_model_evaluation_clean_false_rejects": (
            mm004_hard_negative_model_evaluation_result["clean_false_rejects"]
        ),
        "mm004_hard_negative_model_evaluation_clean_invalid_outputs": (
            mm004_hard_negative_model_evaluation_result["clean_invalid_outputs"]
        ),
        "mm004_hard_negative_model_evaluation_hard_negative_false_accepts": (
            mm004_hard_negative_model_evaluation_result[
                "hard_negative_false_accepts"
            ]
        ),
        "mm004_hard_negative_model_evaluation_quality_improved": (
            mm004_hard_negative_model_evaluation_result["quality_improved"]
        ),
        "mm004_hard_negative_model_evaluation_evidence_sha256": (
            mm004_hard_negative_model_evaluation_result["evidence_sha256"]
        ),
        "mm004_hard_negative_model_evaluation_review_sha256": (
            mm004_hard_negative_model_evaluation_result["review_sha256"]
        ),
        "mm004_hard_negative_model_evaluation_runtime_eligible": (
            mm004_hard_negative_model_evaluation_result["runtime_eligible"]
        ),
        "mm004_hard_negative_model_evaluation_next_gate": (
            mm004_hard_negative_model_evaluation_result["next_gate"]
        ),
        "mm005_environment_adaptation_protocol_frozen": (
            mm005_environment_adaptation["protocol_frozen"]
        ),
        "mm005_environment_adaptation_selected_environment": (
            mm005_environment_adaptation["selected_environment"]
        ),
        "mm005_environment_adaptation_task_families": (
            mm005_environment_adaptation["task_family_count"]
        ),
        "mm005_environment_adaptation_source_receipts": (
            mm005_environment_adaptation["source_receipt_count"]
        ),
        "mm005_environment_adaptation_excluded_cases": (
            mm005_environment_adaptation["excluded_case_count"]
        ),
        "mm005_environment_adaptation_excluded_families": (
            mm005_environment_adaptation["excluded_family_count"]
        ),
        "mm005_environment_adaptation_excluded_images": (
            mm005_environment_adaptation["excluded_image_count"]
        ),
        "mm005_environment_adaptation_dataset_generated": (
            mm005_environment_adaptation["dataset_generated"]
        ),
        "mm005_environment_adaptation_next_gate": (
            mm005_environment_adaptation["next_gate"]
        ),
        "mm005_document_chart_pdf_data_protocol_frozen": (
            mm005_document_chart_pdf_data["protocol_frozen"]
        ),
        "mm005_document_chart_pdf_data_seed": (
            mm005_document_chart_pdf_data["seed"]
        ),
        "mm005_document_chart_pdf_data_templates": (
            mm005_document_chart_pdf_data["template_count"]
        ),
        "mm005_document_chart_pdf_data_records": (
            mm005_document_chart_pdf_data["record_count"]
        ),
        "mm005_document_chart_pdf_data_images": (
            mm005_document_chart_pdf_data["image_count"]
        ),
        "mm005_document_chart_pdf_data_source_artifacts": (
            mm005_document_chart_pdf_data["source_artifact_count"]
        ),
        "mm005_document_chart_pdf_data_train_records": (
            mm005_document_chart_pdf_data["train_records"]
        ),
        "mm005_document_chart_pdf_data_validation_records": (
            mm005_document_chart_pdf_data["validation_records"]
        ),
        "mm005_document_chart_pdf_data_output_files": (
            mm005_document_chart_pdf_data["output_file_count"]
        ),
        "mm005_document_chart_pdf_data_output_bytes": (
            mm005_document_chart_pdf_data["output_bytes"]
        ),
        "mm005_document_chart_pdf_data_generation_executed": (
            mm005_document_chart_pdf_data["generation_executed"]
        ),
        "mm005_document_chart_pdf_data_dataset_validated": (
            mm005_document_chart_pdf_data["dataset_validated"]
        ),
        "mm005_document_chart_pdf_data_next_gate": (
            mm005_document_chart_pdf_data["next_gate"]
        ),
        "mm005_document_chart_pdf_generation_protocol_frozen": (
            mm005_document_chart_pdf_generation["protocol_frozen"]
        ),
        "mm005_document_chart_pdf_generation_planned_output_files": (
            mm005_document_chart_pdf_generation["output_file_count"]
        ),
        "mm005_document_chart_pdf_generation_planned_output_bytes": (
            mm005_document_chart_pdf_generation["output_bytes"]
        ),
        "mm005_document_chart_pdf_generation_executed": (
            mm005_document_chart_pdf_generation["generation_executed"]
        ),
        "mm005_document_chart_pdf_generation_dataset_validated": (
            mm005_document_chart_pdf_generation["dataset_validated"]
        ),
        "mm005_document_chart_pdf_generation_next_gate": (
            mm005_document_chart_pdf_generation["next_gate"]
        ),
        "mm005_document_chart_pdf_adapter_verifier_protocol_frozen": (
            mm005_document_chart_pdf_adapter_verifier["protocol_frozen"]
        ),
        "mm005_document_chart_pdf_adapter_projections": (
            mm005_document_chart_pdf_adapter_verifier["adapter_projection_count"]
        ),
        "mm005_document_chart_pdf_verifier_cases": (
            mm005_document_chart_pdf_adapter_verifier["verifier_case_count"]
        ),
        "mm005_document_chart_pdf_verifier_positive_cases": (
            mm005_document_chart_pdf_adapter_verifier["positive_case_count"]
        ),
        "mm005_document_chart_pdf_verifier_negative_cases": (
            mm005_document_chart_pdf_adapter_verifier["negative_case_count"]
        ),
        "mm005_document_chart_pdf_adapter_implemented": (
            mm005_document_chart_pdf_adapter_verifier["environment_adapter_implemented"]
        ),
        "mm005_document_chart_pdf_verifier_implemented": (
            mm005_document_chart_pdf_adapter_verifier["verifier_implemented"]
        ),
        "mm005_document_chart_pdf_adapter_verifier_next_gate": (
            mm005_document_chart_pdf_adapter_verifier["next_gate"]
        ),
        "mm005_document_chart_pdf_adapter_verifier_implementation_evidence_valid": (
            mm005_document_chart_pdf_adapter_verifier_implementation[
                "evidence_valid"
            ]
        ),
        "mm005_document_chart_pdf_implemented_adapter_projections": (
            mm005_document_chart_pdf_adapter_verifier_implementation[
                "adapter_projection_count"
            ]
        ),
        "mm005_document_chart_pdf_implemented_model_payload_bytes": (
            mm005_document_chart_pdf_adapter_verifier_implementation[
                "model_payload_bytes"
            ]
        ),
        "mm005_document_chart_pdf_implemented_image_bytes": (
            mm005_document_chart_pdf_adapter_verifier_implementation["image_bytes"]
        ),
        "mm005_document_chart_pdf_implemented_verifier_cases": (
            mm005_document_chart_pdf_adapter_verifier_implementation[
                "verifier_case_count"
            ]
        ),
        "mm005_document_chart_pdf_implemented_compiler_valid_cases": (
            mm005_document_chart_pdf_adapter_verifier_implementation[
                "compiler_valid_count"
            ]
        ),
        "mm005_document_chart_pdf_implemented_compiler_invalid_cases": (
            mm005_document_chart_pdf_adapter_verifier_implementation[
                "compiler_invalid_count"
            ]
        ),
        "mm005_document_chart_pdf_environment_adapter_implemented": (
            mm005_document_chart_pdf_adapter_verifier_implementation[
                "environment_adapter_implemented"
            ]
        ),
        "mm005_document_chart_pdf_environment_adapter_executed": (
            mm005_document_chart_pdf_adapter_verifier_implementation[
                "environment_adapter_executed"
            ]
        ),
        "mm005_document_chart_pdf_deterministic_verifier_implemented": (
            mm005_document_chart_pdf_adapter_verifier_implementation[
                "verifier_implemented"
            ]
        ),
        "mm005_document_chart_pdf_deterministic_verifier_executed": (
            mm005_document_chart_pdf_adapter_verifier_implementation[
                "verifier_executed"
            ]
        ),
        "mm005_document_chart_pdf_implementation_model_evaluated": (
            mm005_document_chart_pdf_adapter_verifier_implementation[
                "model_evaluated"
            ]
        ),
        "mm005_document_chart_pdf_implementation_next_gate": (
            mm005_document_chart_pdf_adapter_verifier_implementation["next_gate"]
        ),
        "mm005_document_chart_pdf_model_evaluation_protocol_frozen": (
            mm005_document_chart_pdf_model_evaluation["protocol_frozen"]
        ),
        "mm005_document_chart_pdf_model_evaluation_prompt_projections": (
            mm005_document_chart_pdf_model_evaluation["prompt_projection_count"]
        ),
        "mm005_document_chart_pdf_model_evaluation_model_payload_bytes": (
            mm005_document_chart_pdf_model_evaluation["model_payload_bytes"]
        ),
        "mm005_document_chart_pdf_model_evaluation_image_bytes": (
            mm005_document_chart_pdf_model_evaluation["image_bytes"]
        ),
        "mm005_document_chart_pdf_model_evaluation_generate_calls": (
            mm005_document_chart_pdf_model_evaluation["generate_calls"]
        ),
        "mm005_document_chart_pdf_model_evaluation_attempt_consumed": (
            mm005_document_chart_pdf_model_evaluation["attempt_consumed"]
        ),
        "mm005_document_chart_pdf_model_evaluated": (
            mm005_document_chart_pdf_model_evaluation["model_evaluated"]
        ),
        "mm005_document_chart_pdf_model_evaluation_next_gate": (
            mm005_document_chart_pdf_model_evaluation["next_gate"]
        ),
        "tool_router_seed_records": router_summary["seed_records"],
        "tool_router_eval_records": router_summary["eval_records"],
        "tool_router_eval_digest": router_summary["eval_digest"],
        "tool_router_dangerous_false_approvals": router_summary["baseline"][
            "dangerous_false_approvals"
        ],
        "tool_router_train_records": data_report["train_records"],
        "tool_router_validation_records": data_report["validation_records"],
        "tool_router_task_families": data_report["task_families"],
        "tool_router_data_report_digest": data_report["report_digest"],
        "tool_router_safety_repair_train_records": safety_repair_report[
            "train_records"
        ],
        "tool_router_safety_repair_validation_records": safety_repair_report[
            "validation_records"
        ],
        "tool_router_safety_repair_task_families": safety_repair_report[
            "task_families"
        ],
        "tool_router_safety_repair_dangerous_action_candidates": (
            safety_repair_report["dangerous_action_candidates"]
        ),
        "tool_router_safety_repair_report_digest": safety_repair_report[
            "report_digest"
        ],
        "tool_router_base_model_json_validity": model_metrics["json_validity"],
        "tool_router_base_model_tool_accuracy": model_metrics["tool_accuracy"],
        "tool_router_base_model_dangerous_action_candidates": model_metrics[
            "dangerous_action_candidates"
        ],
        "tool_router_lora_sft_tool_accuracy": sft_metrics["tool_accuracy"],
        "tool_router_lora_sft_dangerous_action_candidates": sft_metrics[
            "dangerous_action_candidates"
        ],
        "tool_router_lora_sft_v2_tool_accuracy": sft_v2_metrics["tool_accuracy"],
        "tool_router_lora_sft_v2_dangerous_action_candidates": sft_v2_metrics[
            "dangerous_action_candidates"
        ],
        "tool_router_lora_sft_v2_decision_semantic_validity": sft_v2_metrics[
            "decision_semantic_validity"
        ],
        "tool_router_lora_sft_v2_failure_report_digest": failure_classification[
            "report_digest"
        ],
        "tool_router_failure_classification_next_gate": failure_classification[
            "locked_next_action"
        ]["gate_id"],
        "tool_router_compiled_decision_semantic_validity": decision_compilation[
            "metrics"
        ]["decision_semantic_validity"],
        "tool_router_compiled_false_refusals": decision_compilation["metrics"][
            "false_refusals"
        ],
        "tool_router_decision_compilation_next_gate": decision_compilation[
            "locked_next_action"
        ]["gate_id"],
        "tool_router_merge_classification": merge_stability["classification"],
        "tool_router_merge_first_divergent_token_index": merge_stability[
            "token_analysis"
        ]["first_divergent_token_index"],
        "tool_router_merge_stability_next_gate": merge_stability["locked_next_action"][
            "gate_id"
        ],
        "tool_router_merge_numerics_classification": merge_numerics["classification"],
        "tool_router_merge_numerics_first_module": merge_numerics["module_analysis"][
            "first_divergent_module"
        ],
        "tool_router_merge_numerics_next_gate": merge_numerics["locked_next_action"][
            "gate_id"
        ],
        "tool_router_merge_remediation_classification": merge_remediation[
            "classification"
        ],
        "tool_router_merge_remediation_passed": merge_remediation["remediation_gate"][
            "passed"
        ],
        "tool_router_merge_remediation_matches_bf16_merged": merge_remediation[
            "remediation_gate"
        ]["frozen_bf16_merged_token_identity"],
        "tool_router_merge_remediation_next_gate": merge_remediation[
            "locked_next_action"
        ]["gate_id"],
        "tool_router_fp32_merge_drift_classification": fp32_merge_drift[
            "classification"
        ],
        "tool_router_fp32_merge_drift_first_token_index": fp32_merge_drift[
            "token_analysis"
        ]["first_divergent_token_index"],
        "tool_router_fp32_merge_drift_analysis_passed": fp32_merge_drift[
            "analysis_gate"
        ]["passed"],
        "tool_router_fp32_merge_drift_remediation_passed": fp32_merge_drift[
            "remediation_gate"
        ]["passed"],
        "tool_router_fp32_attached_merge_isolation_classification": (
            fp32_attached_merge_isolation["classification"]
        ),
        "tool_router_fp32_attached_merge_token_identity": (
            fp32_attached_merge_isolation["same_dtype_token_analysis"][
                "cross_path_identical"
            ]
        ),
        "tool_router_fp32_attached_merge_comparison_step": (
            fp32_attached_merge_isolation["comparison_step"]["step_index"]
        ),
        "tool_router_fp32_attached_merge_isolation_passed": (
            fp32_attached_merge_isolation["isolation_gate"]["passed"]
        ),
        "tool_router_fp32_attached_merge_remediation_passed": (
            fp32_attached_merge_isolation["remediation_gate"]["passed"]
        ),
        "tool_router_fp32_attached_merge_numerics_classification": (
            fp32_attached_merge_numerics["classification"]
        ),
        "tool_router_fp32_attached_merge_numerics_first_module": (
            fp32_attached_merge_numerics["module_analysis"]["first_divergent_module"]
        ),
        "tool_router_fp32_attached_merge_numerics_passed": (
            fp32_attached_merge_numerics["numerics_gate"]["passed"]
        ),
        "tool_router_fp32_attached_merge_numerics_records": (
            fp32_attached_merge_numerics["tensor_archive"]["record_count"]
        ),
        "tool_router_attached_dtype_isolation_classification": (
            attached_dtype_isolation["classification"]
        ),
        "tool_router_attached_dtype_isolation_comparison_step": (
            attached_dtype_isolation["comparison_step"]["step_index"]
        ),
        "tool_router_attached_dtype_isolation_bf16_token_id": (
            attached_dtype_isolation["cross_dtype_token_analysis"]["bf16_token_id"]
        ),
        "tool_router_attached_dtype_isolation_fp32_token_id": (
            attached_dtype_isolation["cross_dtype_token_analysis"]["fp32_token_id"]
        ),
        "tool_router_attached_dtype_isolation_passed": (
            attached_dtype_isolation["dtype_isolation_gate"]["passed"]
        ),
        "tool_router_attached_dtype_numerics_classification": (
            attached_dtype_numerics["classification"]
        ),
        "tool_router_attached_dtype_numerics_first_module": (
            attached_dtype_numerics["module_analysis"]["first_unequal_module"]
        ),
        "tool_router_attached_dtype_numerics_passed": (
            attached_dtype_numerics["numerics_gate"]["passed"]
        ),
        "tool_router_attached_dtype_numerics_capture_records": sum(
            run["capture_record_count"] for run in attached_dtype_numerics["runs"]
        ),
        "tool_router_attached_dtype_boundary_control_classification": (
            attached_dtype_boundary_control["classification"]
        ),
        "tool_router_attached_dtype_boundary_control_passed": (
            attached_dtype_boundary_control["boundary_control_gate"]["passed"]
        ),
        "tool_router_attached_dtype_boundary_control_actual_runs": len(
            attached_dtype_boundary_control["actual_runs"]
        ),
        "tool_router_attached_dtype_boundary_control_control_runs": len(
            attached_dtype_boundary_control["control_runs"]
        ),
        "tool_router_attached_dtype_boundary_control_capture_records": sum(
            run["capture_record_count"]
            for run in [
                *attached_dtype_boundary_control["actual_runs"],
                *attached_dtype_boundary_control["control_runs"],
            ]
        ),
        "tool_router_attached_dtype_boundary_control_current_forward_sufficient": (
            attached_dtype_boundary_control["boundary_analysis"][
                "current_forward_boundary_sufficiency_observed"
            ]
        ),
        "tool_router_fp32_attached_remediation_eval_classification": (
            fp32_attached_remediation_eval["assessment"]["classification"]
        ),
        "tool_router_fp32_attached_remediation_eval_passed": (
            fp32_attached_remediation_eval["assessment"]["evaluation_gate_passed"]
        ),
        "tool_router_fp32_attached_remediation_raw_semantic_validity": (
            fp32_attached_remediation_eval["raw_metrics"]["decision_semantic_validity"]
        ),
        "tool_router_fp32_attached_remediation_argument_exact_match": (
            fp32_attached_remediation_eval["compiled_metrics"]["argument_exact_match"]
        ),
        "tool_router_fp32_attached_remediation_argument_field_f1": (
            fp32_attached_remediation_eval["compiled_metrics"]["argument_field_f1"]
        ),
        "tool_router_fp32_attached_remediation_elapsed_seconds": (
            fp32_attached_remediation_eval["resources"]["performance"][
                "elapsed_seconds"
            ]
        ),
        "tool_router_fp32_attached_remediation_peak_gpu_memory_bytes": (
            fp32_attached_remediation_eval["resources"]["performance"][
                "peak_gpu_memory_bytes"
            ]
        ),
        "tool_router_fp32_attached_artifact_eligibility_classification": (
            fp32_attached_artifact_eligibility["eligibility_decision"]["classification"]
        ),
        "tool_router_fp32_attached_repository_local_evidence_usable": (
            fp32_attached_artifact_eligibility["eligibility_decision"][
                "repository_local_evidence_usable"
            ]
        ),
        "tool_router_fp32_attached_offline_artifact_eligible": (
            fp32_attached_offline_artifact_reassessment["derived_claims"][
                "offline_artifact_eligible"
            ]
        ),
        "tool_router_fp32_attached_artifact_blocking_findings": (
            fp32_attached_artifact_eligibility["packaging_review"]["blocking_findings"]
        ),
        "tool_router_fp32_attached_preferred_offline_candidate": (
            fp32_attached_preferred_candidate["derived_claims"][
                "preferred_offline_candidate"
            ]
        ),
        "tool_router_fp32_attached_artifact_eligibility_report_digest": (
            fp32_attached_artifact_eligibility["report_digest"]
        ),
        "tool_router_fp32_attached_offline_package_manifest_sha256": (
            fp32_attached_offline_package["validation"]["manifest_file_sha256"]
        ),
        "tool_router_fp32_attached_offline_package_metadata_complete": (
            fp32_attached_offline_package["validation"]["metadata_complete"]
        ),
        "tool_router_fp32_attached_offline_package_identity_complete": (
            fp32_attached_offline_package["validation"][
                "offline_package_identity_complete"
            ]
        ),
        "tool_router_fp32_attached_offline_package_classification": (
            fp32_attached_offline_package["validation"]["classification"]
        ),
        "tool_router_fp32_attached_offline_package_local_components_resolved": (
            fp32_attached_offline_package["resolution"]["resolved"]
        ),
        "tool_router_fp32_attached_offline_package_reproducibility_test_eligible": (
            fp32_attached_offline_package["resolution"][
                "eligible_for_clean_location_reproducibility_test"
            ]
        ),
        "tool_router_fp32_attached_offline_package_remote_origin_attested": (
            fp32_attached_remote_origin["derived_claims"][
                "remote_revision_origin_attested"
            ]
        ),
        "tool_router_fp32_attached_offline_package_behavior_reproduced": (
            fp32_attached_offline_package_reproducibility["derived_claims"][
                "behavioral_reproducibility_established"
            ]
        ),
        "tool_router_fp32_attached_offline_package_remaining_blocking_findings": (
            fp32_attached_remote_origin["remaining_blocking_findings"]
        ),
        "tool_router_fp32_attached_offline_package_reproducibility_classification": (
            fp32_attached_offline_package_reproducibility["classification"]
        ),
        "tool_router_fp32_attached_offline_package_reproducibility_gate_passed": (
            fp32_attached_offline_package_reproducibility["formal_gate_passed"]
        ),
        "tool_router_fp32_attached_offline_package_clean_location_resolved": (
            fp32_attached_offline_package_reproducibility["derived_claims"][
                "clean_location_resolution_established"
            ]
        ),
        "tool_router_fp32_attached_offline_package_raw_outputs_exact": (
            fp32_attached_offline_package_reproducibility["comparison"][
                "raw_outputs_exact"
            ]
        ),
        "tool_router_fp32_attached_offline_package_compiled_outputs_exact": (
            fp32_attached_offline_package_reproducibility["comparison"][
                "compiled_outputs_exact"
            ]
        ),
        "tool_router_fp32_attached_offline_package_replay_elapsed_seconds": (
            fp32_attached_offline_package_reproducibility["resources"][
                "performance"
            ]["elapsed_seconds"]
        ),
        "tool_router_fp32_attached_offline_package_replay_peak_gpu_memory_bytes": (
            fp32_attached_offline_package_reproducibility["resources"][
                "performance"
            ]["peak_gpu_memory_bytes"]
        ),
        "tool_router_fp32_attached_offline_package_replay_sha256": (
            TOOL_ROUTER_FP32_ATTACHED_OFFLINE_PACKAGE_REPRODUCIBILITY_PREDICTIONS_SHA256
        ),
        "tool_router_fp32_attached_offline_package_evidence_sha256": (
            TOOL_ROUTER_FP32_ATTACHED_OFFLINE_PACKAGE_REPRODUCIBILITY_EVIDENCE_SHA256
        ),
        "tool_router_fp32_attached_remote_origin_classification": (
            fp32_attached_remote_origin["classification"]
        ),
        "tool_router_fp32_attached_remote_origin_gate_passed": (
            fp32_attached_remote_origin["formal_gate_passed"]
        ),
        "tool_router_fp32_attached_remote_origin_evidence_sha256": (
            TOOL_ROUTER_FP32_ATTACHED_REMOTE_ORIGIN_EVIDENCE_SHA256
        ),
        "tool_router_fp32_attached_remote_origin_offline_artifact_eligible": (
            fp32_attached_remote_origin["derived_claims"][
                "offline_artifact_eligible"
            ]
        ),
        "tool_router_fp32_attached_remote_origin_portable_package_eligible": (
            fp32_attached_remote_origin["derived_claims"][
                "portable_package_eligible"
            ]
        ),
        "tool_router_fp32_attached_offline_artifact_reassessment_classification": (
            fp32_attached_offline_artifact_reassessment["classification"]
        ),
        "tool_router_fp32_attached_offline_artifact_reassessment_gate_passed": (
            fp32_attached_offline_artifact_reassessment["formal_gate_passed"]
        ),
        "tool_router_fp32_attached_offline_artifact_reassessment_evidence_sha256": (
            TOOL_ROUTER_FP32_ATTACHED_OFFLINE_ARTIFACT_REASSESSMENT_EVIDENCE_SHA256
        ),
        "tool_router_fp32_attached_offline_artifact_reassessment_remaining_blocking_findings": (
            fp32_attached_offline_artifact_reassessment[
                "remaining_blocking_findings"
            ]
        ),
        "tool_router_fp32_attached_offline_artifact_reassessment_portable_package_eligible": (
            fp32_attached_offline_artifact_reassessment["derived_claims"][
                "portable_package_eligible"
            ]
        ),
        "tool_router_fp32_attached_preferred_candidate_classification": (
            fp32_attached_preferred_candidate["classification"]
        ),
        "tool_router_fp32_attached_preferred_candidate_gate_passed": (
            fp32_attached_preferred_candidate["formal_gate_passed"]
        ),
        "tool_router_fp32_attached_preferred_candidate_evidence_sha256": (
            TOOL_ROUTER_FP32_ATTACHED_PREFERRED_CANDIDATE_EVIDENCE_SHA256
        ),
        "tool_router_fp32_attached_preferred_candidate_remaining_blocking_findings": (
            fp32_attached_preferred_candidate["remaining_blocking_findings"]
        ),
        "tool_router_fp32_attached_preferred_candidate_downstream_open_findings": (
            fp32_attached_preferred_candidate["downstream_open_findings"]
        ),
        "tool_router_fp32_attached_preferred_candidate_portable_package_eligible": (
            fp32_attached_preferred_candidate["derived_claims"][
                "portable_package_eligible"
            ]
        ),
        "tool_router_next_gate": fp32_attached_preferred_candidate[
            "locked_next_action"
        ]["gate_id"],
    }
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


def _validate_project_metadata(baseline: dict[str, Any]) -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = pyproject["project"]
    expected_minors = [f"{major}.{minor}" for major, minor in sorted(SUPPORTED_MINORS)]
    if project["requires-python"] != baseline["python_requires"]:
        raise GateError("python_requires does not match baseline")
    if project["version"] != baseline["package_version"]:
        raise GateError("package version does not match baseline")
    if project["dependencies"] != baseline["runtime_dependencies"]:
        raise GateError("runtime dependencies do not match baseline")
    if baseline["required_python_minors"] != expected_minors:
        raise GateError("Python matrix does not match gate")
    lock_lines = [
        line.strip()
        for line in (ROOT / "requirements" / "runtime.lock")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if lock_lines:
        raise GateError("runtime.lock must remain empty for the stdlib baseline")


def _validate_artifact_hashes(baseline: dict[str, Any]) -> None:
    artifacts = baseline.get("artifacts")
    if not isinstance(artifacts, dict) or not artifacts:
        raise GateError("baseline artifacts are missing")
    for relative, expected in artifacts.items():
        path = ROOT / relative
        if not path.is_file() or path.is_symlink():
            raise GateError(f"unsafe or missing baseline artifact: {relative}")
        actual = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise GateError(f"baseline artifact digest mismatch: {relative}")


def _audit_import_boundary() -> int:
    count = 0
    for path in sorted((SRC / "fullcycle_bridge").glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        count += 1
        for node in ast.walk(tree):
            imported: str | None = None
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.partition(".")[0]
                    if root in FORBIDDEN_IMPORT_ROOTS:
                        raise GateError(f"forbidden import {root} in {path.name}")
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                imported = node.module.partition(".")[0]
            if imported in FORBIDDEN_IMPORT_ROOTS:
                raise GateError(f"forbidden import {imported} in {path.name}")
    return count


def _validate_fixed_outputs() -> tuple[
    Any,
    int,
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    from fullcycle_bridge import validate_files
    from fullcycle_bridge.consumer import canonical_json_bytes
    from fullcycle_bridge.dataset import map_many
    from fullcycle_bridge.tool_router import (
        baseline_predict,
        evaluate,
        fixture_digest,
        load_fixture,
    )
    from fullcycle_bridge.tool_router_dataset import (
        audit_dataset,
        load_family_manifest,
    )
    from fullcycle_bridge.tool_router_model_eval import score_raw_outputs
    from fullcycle_bridge.tool_router_decision_compilation import (
        compile_frozen_v2_outputs,
    )
    from fullcycle_bridge.tool_router_failure_classification import (
        classify_v2_failures,
    )
    from fullcycle_bridge.tool_router_safety_repair import (
        audit_safety_repair_dataset,
        load_badcase_taxonomy,
    )
    from fullcycle_bridge.tool_router_sft import (
        canonical_config_sha256,
        directory_artifact_manifest,
        file_sha256,
    )

    manifest = ROOT / "fixtures" / "bridge_v1" / "valid" / "runtime-manifest.json"
    minimal = ROOT / "fixtures" / "bridge_v1" / "valid" / "minimal-run-export.json"
    input_root = ROOT / "fixtures" / "reliability_dataset_v1" / "inputs"
    inputs = [
        input_root / "failure-denial-recovery-budget-sequence.json",
        input_root / "unknown-outcome.json",
    ]
    summary = validate_files(manifest, minimal)
    records = map_many(manifest, inputs)
    actual = b"".join(canonical_json_bytes(record) + b"\n" for record in records)
    expected = (
        ROOT / "fixtures" / "reliability_dataset_v1" / "expected-records.jsonl"
    ).read_bytes()
    if actual != expected:
        raise GateError("dataset JSONL differs from the frozen fixture")
    router_baseline = _load_json(TOOL_ROUTER_BASELINE_PATH)
    _validate_named_hashes(router_baseline["artifact_hashes"])
    seed = load_fixture(ROOT / "fixtures" / "tool_router_v1" / "seed.json")
    evaluation = load_fixture(ROOT / "fixtures" / "tool_router_v1" / "eval.json")
    router_summary: dict[str, Any] = {
        "seed_records": len(seed),
        "eval_records": len(evaluation),
        "seed_digest": fixture_digest(seed),
        "eval_digest": fixture_digest(evaluation),
        "baseline": evaluate(
            evaluation, [baseline_predict(record) for record in evaluation]
        ),
    }
    for key in ("seed_records", "eval_records", "seed_digest", "eval_digest"):
        if router_summary[key] != router_baseline[key]:
            raise GateError(f"Tool Router baseline mismatch: {key}")
    if router_summary["baseline"] != router_baseline["deterministic_rule_baseline"]:
        raise GateError("Tool Router metrics differ from the frozen baseline")
    data_baseline = _load_json(TOOL_ROUTER_DATA_BASELINE_PATH)
    _validate_named_hashes(data_baseline["artifact_hashes"])
    train = load_fixture(ROOT / "fixtures" / "tool_router_v1" / "train.json")
    validation = load_fixture(ROOT / "fixtures" / "tool_router_v1" / "validation.json")
    family_manifest = load_family_manifest(
        ROOT / "fixtures" / "tool_router_v1" / "family-manifest.json"
    )
    data_report = audit_dataset(
        train,
        validation,
        evaluation,
        family_manifest,
        router_summary["eval_digest"],
    )
    if data_report != data_baseline["expected_report"]:
        raise GateError("Tool Router data audit differs from the frozen baseline")
    safety_repair_baseline = _load_json(TOOL_ROUTER_SAFETY_REPAIR_BASELINE_PATH)
    _validate_named_hashes(safety_repair_baseline["base_artifact_hashes"])
    _validate_named_hashes(safety_repair_baseline["artifact_hashes"])
    taxonomy_source = safety_repair_baseline["source_badcase_taxonomy"]
    _validate_named_hashes({taxonomy_source["path"]: taxonomy_source["sha256"]})
    safety_repair_train = load_fixture(
        ROOT / "fixtures" / "tool_router_v2" / "train.json"
    )
    safety_repair_validation = load_fixture(
        ROOT / "fixtures" / "tool_router_v2" / "validation.json"
    )
    safety_repair_manifest = load_family_manifest(
        ROOT / "fixtures" / "tool_router_v2" / "family-manifest.json"
    )
    safety_repair_taxonomy = load_badcase_taxonomy(ROOT / taxonomy_source["path"])
    if (
        safety_repair_taxonomy["source_prediction_sha256"]
        != taxonomy_source["source_prediction_sha256"]
        or safety_repair_taxonomy["source_report_sha256"]
        != taxonomy_source["source_report_sha256"]
    ):
        raise GateError("Tool Router safety-repair source provenance mismatch")
    safety_repair_report = audit_safety_repair_dataset(
        train,
        validation,
        safety_repair_train,
        safety_repair_validation,
        evaluation,
        family_manifest,
        safety_repair_manifest,
        safety_repair_taxonomy,
        router_summary["eval_digest"],
    )
    if safety_repair_report != safety_repair_baseline["expected_report"]:
        raise GateError("Tool Router safety-repair audit differs from frozen baseline")
    model_baseline = _load_json(TOOL_ROUTER_MODEL_BASELINE_PATH)
    _validate_named_hashes(model_baseline["artifact_hashes"])
    prediction_artifact = _load_json(
        ROOT / "baseline" / "tool-router-qwen2.5-1.5b-instruct-predictions.json"
    )
    frozen_report = _load_json(
        ROOT / "baseline" / "tool-router-qwen2.5-1.5b-instruct-report.json"
    )
    raw_outputs = [
        {
            "example_id": item["example_id"],
            "raw_output": item["raw_output"],
        }
        for item in prediction_artifact["outputs"]
    ]
    model_metrics, parsed_outputs = score_raw_outputs(evaluation, raw_outputs)
    if model_metrics != model_baseline["metrics"]:
        raise GateError("Tool Router model metrics differ from the frozen baseline")
    if model_metrics != frozen_report["metrics"]:
        raise GateError("Tool Router frozen model report metrics mismatch")
    if parsed_outputs != frozen_report["parsed_outputs"]:
        raise GateError("Tool Router frozen parsed outputs mismatch")
    sft_baseline = _load_json(TOOL_ROUTER_SFT_BASELINE_PATH)
    _validate_named_hashes(sft_baseline["artifact_hashes"])
    sft_config = _load_json(ROOT / "configs" / "tool_router_lora_sft_v1.json")
    sft_evidence = _load_json(
        ROOT / "baseline" / "fc-mvp-001-lora-sft-v1-training.json"
    )
    sft_predictions = _load_json(
        ROOT / "baseline" / "tool-router-qwen2.5-1.5b-lora-sft-v1-predictions.json"
    )
    sft_report = _load_json(
        ROOT / "baseline" / "tool-router-qwen2.5-1.5b-lora-sft-v1-report.json"
    )
    config_digest = canonical_config_sha256(sft_config)
    if config_digest != sft_baseline["canonical_config_sha256"]:
        raise GateError("Tool Router SFT config digest mismatch")
    if sft_evidence["config_sha256"] != config_digest:
        raise GateError("Tool Router SFT evidence config mismatch")
    if sft_predictions["config_sha256"] != config_digest:
        raise GateError("Tool Router SFT prediction config mismatch")
    adapter_dir = ROOT / "baseline" / "adapters" / "fc-mvp-001-lora-sft-v1"
    if (
        directory_artifact_manifest(adapter_dir)
        != sft_evidence["final_adapter"]["files"]
    ):
        raise GateError("Tool Router SFT adapter manifest mismatch")
    adapter_weight = adapter_dir / "adapter_model.safetensors"
    if file_sha256(adapter_weight) != sft_baseline["adapter"]["adapter_weight_sha256"]:
        raise GateError("Tool Router SFT adapter weight digest mismatch")
    sft_raw_outputs = [
        {
            "example_id": item["example_id"],
            "raw_output": item["raw_output"],
        }
        for item in sft_predictions["outputs"]
    ]
    sft_metrics, sft_parsed = score_raw_outputs(evaluation, sft_raw_outputs)
    if sft_metrics != sft_baseline["metrics"]:
        raise GateError("Tool Router SFT metrics differ from the frozen baseline")
    if sft_metrics != sft_report["metrics"]:
        raise GateError("Tool Router SFT report metrics mismatch")
    if sft_parsed != sft_report["parsed_outputs"]:
        raise GateError("Tool Router SFT parsed outputs mismatch")
    if sft_report["runtime_eligible"] is not False:
        raise GateError("Tool Router SFT must remain Runtime ineligible")
    sft_v2_baseline = _load_json(TOOL_ROUTER_SFT_V2_BASELINE_PATH)
    _validate_named_hashes(sft_v2_baseline["artifact_hashes"])
    sft_v2_config = _load_json(ROOT / "configs" / "tool_router_lora_sft_v2.json")
    sft_v2_evidence = _load_json(
        ROOT / "baseline" / "fc-mvp-001-lora-sft-v2-training.json"
    )
    sft_v2_predictions = _load_json(
        ROOT / "baseline" / "tool-router-qwen2.5-1.5b-lora-sft-v2-predictions.json"
    )
    sft_v2_report = _load_json(
        ROOT / "baseline" / "tool-router-qwen2.5-1.5b-lora-sft-v2-report.json"
    )
    sft_v2_load_merge = _load_json(
        ROOT / "baseline" / "fc-mvp-001-lora-sft-v2-load-merge.json"
    )
    sft_v2_config_digest = canonical_config_sha256(sft_v2_config)
    if sft_v2_config_digest != sft_v2_baseline["canonical_config_sha256"]:
        raise GateError("Tool Router SFT v2 config digest mismatch")
    if sft_v2_evidence["config_sha256"] != sft_v2_config_digest:
        raise GateError("Tool Router SFT v2 evidence config mismatch")
    sft_v2_adapter_dir = ROOT / "baseline" / "adapters" / "fc-mvp-001-lora-sft-v2"
    if (
        directory_artifact_manifest(sft_v2_adapter_dir)
        != sft_v2_evidence["final_adapter"]["files"]
    ):
        raise GateError("Tool Router SFT v2 adapter manifest mismatch")
    sft_v2_raw_outputs = [
        {
            "example_id": item["example_id"],
            "raw_output": item["raw_output"],
        }
        for item in sft_v2_predictions["outputs"]
    ]
    sft_v2_metrics, sft_v2_parsed = score_raw_outputs(evaluation, sft_v2_raw_outputs)
    if sft_v2_metrics != sft_v2_baseline["metrics"]:
        raise GateError("Tool Router SFT v2 metrics differ from frozen baseline")
    if sft_v2_metrics != sft_v2_report["metrics"]:
        raise GateError("Tool Router SFT v2 report metrics mismatch")
    if sft_v2_parsed != sft_v2_report["parsed_outputs"]:
        raise GateError("Tool Router SFT v2 parsed outputs mismatch")
    if not sft_v2_report["safety_gate_passed"]:
        raise GateError("Tool Router SFT v2 safety gate must remain passed")
    if sft_v2_report["runtime_eligible"] is not False:
        raise GateError("Tool Router SFT v2 must remain Runtime ineligible")
    if (
        sft_v2_load_merge["outputs_identical"] is not False
        or sft_v2_load_merge["safe_merge"] is not True
        or sft_v2_load_merge["remaining_adapter_parameter_tensors"] != 0
    ):
        raise GateError("Tool Router SFT v2 load/merge evidence mismatch")
    failure_baseline = _load_json(TOOL_ROUTER_FAILURE_CLASSIFICATION_PATH)
    failure_source_paths = {
        "predictions": (
            ROOT / "baseline" / "tool-router-qwen2.5-1.5b-lora-sft-v2-predictions.json"
        ),
        "report": (
            ROOT / "baseline" / "tool-router-qwen2.5-1.5b-lora-sft-v2-report.json"
        ),
        "training": ROOT / "baseline" / "fc-mvp-001-lora-sft-v2-training.json",
        "load_merge": ROOT / "baseline" / "fc-mvp-001-lora-sft-v2-load-merge.json",
    }
    failure_source_hashes = {
        name: "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
        for name, path in failure_source_paths.items()
    }
    failure_classification = classify_v2_failures(
        sft_v2_predictions,
        sft_v2_report,
        sft_v2_evidence,
        sft_v2_load_merge,
        failure_source_hashes,
    )
    if failure_classification != failure_baseline:
        raise GateError("Tool Router SFT v2 failure classification drift")
    decision_compilation = _load_json(TOOL_ROUTER_DECISION_COMPILATION_PATH)
    compiled_predictions = _load_json(TOOL_ROUTER_COMPILED_PREDICTIONS_PATH)
    compiled_report = _load_json(TOOL_ROUTER_COMPILED_REPORT_PATH)
    classification_path = TOOL_ROUTER_FAILURE_CLASSIFICATION_PATH
    compilation_source_hashes = {
        "predictions": failure_source_hashes["predictions"],
        "report": failure_source_hashes["report"],
        "classification": (
            "sha256:" + hashlib.sha256(classification_path.read_bytes()).hexdigest()
        ),
    }
    if decision_compilation["source_hashes"] != compilation_source_hashes:
        raise GateError("Tool Router decision compilation source drift")
    _validate_named_hashes(decision_compilation["artifact_hashes"])
    reproduced_compilation = compile_frozen_v2_outputs(
        sft_v2_predictions,
        sft_v2_report,
        failure_classification,
        compilation_source_hashes,
    )
    if reproduced_compilation != compiled_predictions:
        raise GateError("Tool Router compiled predictions drift")
    compiled_raw_outputs = [
        {"example_id": item["example_id"], "raw_output": item["raw_output"]}
        for item in compiled_predictions["outputs"]
    ]
    compiled_metrics, compiled_parsed = score_raw_outputs(
        evaluation, compiled_raw_outputs
    )
    if (
        compiled_metrics != compiled_report["metrics"]
        or compiled_metrics != decision_compilation["metrics"]
        or compiled_parsed != compiled_report["parsed_outputs"]
        or compiled_report["acceptance"] != decision_compilation["acceptance"]
    ):
        raise GateError("Tool Router decision compilation report drift")
    if (
        decision_compilation["runtime_eligible"] is not False
        or compiled_report["runtime_eligible"] is not False
    ):
        raise GateError("Tool Router compiled output must remain Runtime ineligible")
    return (
        summary,
        len(records),
        router_summary,
        data_report,
        safety_repair_report,
        model_metrics,
        sft_metrics,
        sft_v2_metrics,
        failure_classification,
        decision_compilation,
    )


def _validate_lane_b_contract() -> dict[str, Any]:
    from fullcycle_bridge.lane_b import (
        LaneBValidationError,
        validate_bundle_file,
    )

    metadata = _load_json(LANE_B_METADATA_PATH)
    expected_versions = {
        "lane_b_bundle_version": 1,
        "lane_b_consent_version": 1,
        "lane_b_episode_version": 1,
        "lane_b_deletion_receipt_version": 1,
    }
    for key, expected in expected_versions.items():
        if metadata.get(key) != expected:
            raise GateError(f"Lane B metadata version mismatch: {key}")
    if metadata.get("review_id") != "FC-BRIDGE-003":
        raise GateError("Lane B review ID mismatch")
    if metadata.get("runtime_freeze_commit") != (
        "324ff2fb5911e332ddb5c5f90eb41296e8faf7a9"
    ):
        raise GateError("Lane B Runtime freeze binding mismatch")

    for key, expected_path in {
        "schema": LANE_B_SCHEMA_PATH,
        "valid_fixture": LANE_B_VALID_BUNDLE_PATH,
    }.items():
        record = metadata.get(key)
        if not isinstance(record, dict):
            raise GateError(f"Lane B metadata record missing: {key}")
        expected_relative = expected_path.relative_to(ROOT).as_posix()
        payload = _read_regular_file_once(expected_path, f"Lane B {key}")
        if (
            record.get("path") != expected_relative
            or record.get("bytes") != len(payload)
            or record.get("sha256") != "sha256:" + hashlib.sha256(payload).hexdigest()
        ):
            raise GateError(f"Lane B metadata binding mismatch: {key}")

    schema = _load_json(LANE_B_SCHEMA_PATH)
    if (
        schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema"
        or schema.get("additionalProperties") is not False
        or schema.get("properties", {}).get("lane_b_bundle_version", {}).get("const")
        != 1
    ):
        raise GateError("Lane B schema boundary mismatch")

    summary = validate_bundle_file(LANE_B_VALID_BUNDLE_PATH.resolve())
    invalid_fixtures = metadata.get("invalid_fixtures")
    if not isinstance(invalid_fixtures, dict) or not invalid_fixtures:
        raise GateError("Lane B invalid fixture metadata missing")
    for filename, expected_code in invalid_fixtures.items():
        if not isinstance(filename, str) or not isinstance(expected_code, str):
            raise GateError("Lane B invalid fixture metadata malformed")
        try:
            validate_bundle_file((LANE_B_FIXTURE_ROOT / "invalid" / filename).resolve())
        except LaneBValidationError as exc:
            if exc.code != expected_code:
                raise GateError(
                    f"Lane B invalid fixture code mismatch: {filename}"
                ) from exc
        else:
            raise GateError(f"Lane B invalid fixture passed: {filename}")

    expected_outcome = {
        "contract_review_complete": True,
        "lane_b_disabled_by_default": True,
        "automatic_lane_a_export_changed": False,
        "runtime_repository_changed": False,
        "capture_adapter_implemented": False,
        "real_episode_collected": False,
        "real_deletion_executed": False,
        "dataset_split_assigned": False,
        "license_approved": False,
        "training_eligible": False,
        "runtime_eligible": False,
    }
    if metadata.get("review_outcome") != expected_outcome:
        raise GateError("Lane B review outcome mismatch")
    next_gate = metadata.get("next_gate")
    if next_gate != "MM-001-multimodal-trajectory-schema-v1":
        raise GateError("Lane B next gate mismatch")
    return {
        "contract_review_complete": True,
        "bundle_version": summary.bundle_version,
        "consent_version": metadata["lane_b_consent_version"],
        "episode_version": metadata["lane_b_episode_version"],
        "deletion_receipt_version": metadata["lane_b_deletion_receipt_version"],
        "artifact_count": summary.artifact_count,
        "step_count": summary.step_count,
        "deletion_verified": summary.deletion_verified,
        "training_eligible": summary.training_eligible,
        "capture_adapter_implemented": False,
        "next_gate": next_gate,
    }


def _validate_multimodal_trajectory_contract() -> dict[str, Any]:
    from fullcycle_bridge.multimodal_trajectory import (
        TrajectoryValidationError,
        validate_trajectory_file,
    )

    metadata = _load_json(TRAJECTORY_METADATA_PATH)
    expected_versions = {
        "multimodal_trajectory_schema_version": 1,
        "compatible_lane_b_bundle_version": 1,
        "compatible_lane_b_episode_version": 1,
    }
    for key, expected in expected_versions.items():
        if metadata.get(key) != expected:
            raise GateError(f"MM-001 metadata version mismatch: {key}")
    if metadata.get("review_id") != "MM-001":
        raise GateError("MM-001 review ID mismatch")
    if metadata.get("runtime_freeze_commit") != (
        "324ff2fb5911e332ddb5c5f90eb41296e8faf7a9"
    ):
        raise GateError("MM-001 Runtime freeze binding mismatch")
    if metadata.get("lane_b_contract_merge_commit") != (
        "d1a8e787951c52c7650b23c71ea3df2b6a9ee00d"
    ):
        raise GateError("MM-001 Lane B contract binding mismatch")

    records = {
        "schema": (metadata.get("schema"), TRAJECTORY_SCHEMA_PATH),
        "text_only": (
            metadata.get("valid_fixtures", {}).get("text_only"),
            TRAJECTORY_TEXT_FIXTURE_PATH,
        ),
        "image_grounded": (
            metadata.get("valid_fixtures", {}).get("image_grounded"),
            TRAJECTORY_IMAGE_FIXTURE_PATH,
        ),
    }
    for key, (record, expected_path) in records.items():
        if not isinstance(record, dict):
            raise GateError(f"MM-001 metadata record missing: {key}")
        expected_relative = expected_path.relative_to(ROOT).as_posix()
        payload = _read_regular_file_once(expected_path, f"MM-001 {key}")
        if (
            record.get("path") != expected_relative
            or record.get("bytes") != len(payload)
            or record.get("sha256") != "sha256:" + hashlib.sha256(payload).hexdigest()
        ):
            raise GateError(f"MM-001 metadata binding mismatch: {key}")

    schema = _load_json(TRAJECTORY_SCHEMA_PATH)
    schema_properties = schema.get("properties", {})
    versions_schema = schema.get("$defs", {}).get("versions", {})
    if (
        schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema"
        or schema.get("additionalProperties") is not False
        or schema_properties.get("multimodal_trajectory_schema_version", {}).get(
            "const"
        )
        != 1
        or versions_schema.get("additionalProperties") is not False
    ):
        raise GateError("MM-001 schema boundary mismatch")

    text_summary = validate_trajectory_file(TRAJECTORY_TEXT_FIXTURE_PATH.resolve())
    image_summary = validate_trajectory_file(TRAJECTORY_IMAGE_FIXTURE_PATH.resolve())
    expected_summaries = {
        "text_only": {
            "schema_version": 1,
            "modality": "text_only",
            "artifact_count": 10,
            "available_tool_count": 1,
            "previous_step_count": 0,
            "transition_sequence": 1,
            "dispatched": True,
            "verifier_label": "success",
            "training_eligible": False,
            "execution_eligible": False,
        },
        "image_grounded": {
            "schema_version": 1,
            "modality": "image_grounded",
            "artifact_count": 17,
            "available_tool_count": 1,
            "previous_step_count": 1,
            "transition_sequence": 2,
            "dispatched": True,
            "verifier_label": "success",
            "training_eligible": False,
            "execution_eligible": False,
        },
    }
    for key, summary in {
        "text_only": text_summary,
        "image_grounded": image_summary,
    }.items():
        observed = summary.to_dict()
        observed.pop("trajectory_id")
        if observed != expected_summaries[key]:
            raise GateError(f"MM-001 valid fixture summary mismatch: {key}")

    invalid_fixtures = metadata.get("invalid_fixtures")
    if not isinstance(invalid_fixtures, dict) or not invalid_fixtures:
        raise GateError("MM-001 invalid fixture metadata missing")
    for filename, expected_code in invalid_fixtures.items():
        if not isinstance(filename, str) or not isinstance(expected_code, str):
            raise GateError("MM-001 invalid fixture metadata malformed")
        try:
            validate_trajectory_file(
                (TRAJECTORY_FIXTURE_ROOT / "invalid" / filename).resolve()
            )
        except TrajectoryValidationError as exc:
            if exc.code != expected_code:
                raise GateError(
                    f"MM-001 invalid fixture code mismatch: {filename}"
                ) from exc
        else:
            raise GateError(f"MM-001 invalid fixture passed: {filename}")

    expected_outcome = {
        "schema_review_complete": True,
        "text_only_fixture_validated": True,
        "image_grounded_fixture_validated": True,
        "shared_versioned_topology": True,
        "synthetic_only": True,
        "runtime_repository_changed": False,
        "capture_adapter_implemented": False,
        "real_episode_collected": False,
        "dataset_split_assigned": False,
        "license_approved": False,
        "training_eligible": False,
        "execution_eligible": False,
        "runtime_eligible": False,
    }
    if metadata.get("review_outcome") != expected_outcome:
        raise GateError("MM-001 review outcome mismatch")
    next_gate = metadata.get("next_gate")
    if next_gate != "MM-002-gui-grounding-data-eval-v1":
        raise GateError("MM-001 next gate mismatch")
    return {
        "schema_review_complete": True,
        "schema_version": text_summary.schema_version,
        "modalities": [text_summary.modality, image_summary.modality],
        "text_artifacts": text_summary.artifact_count,
        "image_artifacts": image_summary.artifact_count,
        "image_previous_steps": image_summary.previous_step_count,
        "training_eligible": False,
        "execution_eligible": False,
        "real_episode_collected": False,
        "next_gate": next_gate,
    }


def _validate_gui_grounding_eval() -> dict[str, Any]:
    from fullcycle_bridge.gui_grounding_eval import (
        GuiGroundingValidationError,
        load_predictions_file,
        load_suite_file,
        score_predictions,
    )

    metadata = _load_json(GUI_GROUNDING_METADATA_PATH)
    expected_versions = {
        "gui_grounding_eval_version": 1,
        "gui_grounding_prediction_version": 1,
        "report_version": 1,
    }
    for key, expected in expected_versions.items():
        if metadata.get(key) != expected:
            raise GateError(f"MM-002 metadata version mismatch: {key}")
    if metadata.get("review_id") != "MM-002":
        raise GateError("MM-002 review ID mismatch")
    if metadata.get("runtime_freeze_commit") != (
        "324ff2fb5911e332ddb5c5f90eb41296e8faf7a9"
    ):
        raise GateError("MM-002 Runtime freeze binding mismatch")
    if metadata.get("multimodal_trajectory_schema_merge_commit") != (
        "3e5908a7ba92d00facb48847915834c1f8fbca30"
    ):
        raise GateError("MM-002 trajectory schema commit binding mismatch")
    trajectory_schema_payload = _read_regular_file_once(
        TRAJECTORY_SCHEMA_PATH, "MM-002 trajectory schema"
    )
    trajectory_schema_sha256 = (
        "sha256:" + hashlib.sha256(trajectory_schema_payload).hexdigest()
    )
    if metadata.get("multimodal_trajectory_schema_sha256") != (
        trajectory_schema_sha256
    ):
        raise GateError("MM-002 trajectory schema hash binding mismatch")

    expected_paths = {
        "suite_schema": GUI_GROUNDING_SUITE_SCHEMA_PATH,
        "predictions_schema": GUI_GROUNDING_PREDICTIONS_SCHEMA_PATH,
        "suite": GUI_GROUNDING_SUITE_PATH,
        "predictions": GUI_GROUNDING_PREDICTIONS_PATH,
        "report": GUI_GROUNDING_REPORT_PATH,
    }
    artifacts = metadata.get("artifacts")
    if not isinstance(artifacts, dict) or set(artifacts) != set(expected_paths):
        raise GateError("MM-002 artifact metadata mismatch")
    for key, expected_path in expected_paths.items():
        record = artifacts.get(key)
        if not isinstance(record, dict):
            raise GateError(f"MM-002 artifact metadata missing: {key}")
        payload = _read_regular_file_once(expected_path, f"MM-002 {key}")
        if (
            record.get("path") != expected_path.relative_to(ROOT).as_posix()
            or record.get("bytes") != len(payload)
            or record.get("sha256")
            != "sha256:" + hashlib.sha256(payload).hexdigest()
        ):
            raise GateError(f"MM-002 artifact binding mismatch: {key}")

    suite_schema = _load_json(GUI_GROUNDING_SUITE_SCHEMA_PATH)
    predictions_schema = _load_json(GUI_GROUNDING_PREDICTIONS_SCHEMA_PATH)
    if (
        suite_schema.get("$schema")
        != "https://json-schema.org/draft/2020-12/schema"
        or suite_schema.get("additionalProperties") is not False
        or suite_schema.get("properties", {})
        .get("gui_grounding_eval_version", {})
        .get("const")
        != 1
        or predictions_schema.get("$schema")
        != "https://json-schema.org/draft/2020-12/schema"
        or predictions_schema.get("additionalProperties") is not False
        or predictions_schema.get("properties", {})
        .get("gui_grounding_prediction_version", {})
        .get("const")
        != 1
    ):
        raise GateError("MM-002 schema boundary mismatch")

    suite = load_suite_file(GUI_GROUNDING_SUITE_PATH.resolve())
    predictions = load_predictions_file(GUI_GROUNDING_PREDICTIONS_PATH.resolve())
    report = score_predictions(suite, predictions)
    if report != _load_json(GUI_GROUNDING_REPORT_PATH):
        raise GateError("MM-002 frozen report recomputation mismatch")
    if report.get("metrics") != metadata.get("expected_metrics"):
        raise GateError("MM-002 expected metrics mismatch")
    if report.get("coverage") != {
        "observation_modes": ["fused", "screenshot_only", "uia_only"],
        "capabilities": ["bbox_grounding", "fused_grounding", "ref_grounding"],
        "ocr_conditions": ["clean", "missing", "noisy"],
        "perturbations": [
            "coordinate_ref_disagreement",
            "moved",
            "none",
            "occluded",
            "stale_ref",
        ],
    }:
        raise GateError("MM-002 coverage mismatch")

    invalid_fixtures = metadata.get("invalid_fixtures")
    if not isinstance(invalid_fixtures, dict) or not invalid_fixtures:
        raise GateError("MM-002 invalid fixture metadata missing")
    for filename, expected_code in invalid_fixtures.items():
        if not isinstance(filename, str) or not isinstance(expected_code, str):
            raise GateError("MM-002 invalid fixture metadata malformed")
        try:
            load_suite_file((GUI_GROUNDING_FIXTURE_ROOT / "invalid" / filename).resolve())
        except GuiGroundingValidationError as exc:
            if exc.code != expected_code:
                raise GateError(
                    f"MM-002 invalid fixture code mismatch: {filename}"
                ) from exc
        else:
            raise GateError(f"MM-002 invalid fixture passed: {filename}")

    expected_outcome = {
        "data_eval_review_complete": True,
        "case_count": 9,
        "family_count": 9,
        "synthetic_eval_only": True,
        "synthetic_probe_only": True,
        "model_predictions_declared": False,
        "model_evaluated": False,
        "real_content_collected": False,
        "capture_adapter_implemented": False,
        "runtime_repository_changed": False,
        "dataset_split": "eval",
        "training_use_prohibited": True,
        "training_eligible": False,
        "execution_eligible": False,
        "runtime_eligible": False,
    }
    if metadata.get("review_outcome") != expected_outcome:
        raise GateError("MM-002 review outcome mismatch")
    claims = report.get("claims")
    if not isinstance(claims, dict) or claims != {
        "synthetic_eval_only": True,
        "synthetic_probe_only": True,
        "model_predictions_declared": False,
        "model_evaluated": False,
        "real_content_collected": False,
        "capture_adapter_implemented": False,
        "training_eligible": False,
        "execution_eligible": False,
        "runtime_eligible": False,
    }:
        raise GateError("MM-002 report claim mismatch")
    next_gate = metadata.get("next_gate")
    if next_gate != "MM-003-multimodal-gui-action-model-v1":
        raise GateError("MM-002 next gate mismatch")
    return {
        "review_complete": True,
        "case_count": report["case_count"],
        "metrics": report["metrics"],
        "model_evaluated": False,
        "training_eligible": False,
        "next_gate": next_gate,
    }


def _validate_mm003_baseline_protocol() -> dict[str, Any]:
    from fullcycle_bridge import mm003_baseline_protocol as contract
    from fullcycle_bridge.gui_grounding_eval import load_suite_file, sha256_json

    preregistration_payload = _read_regular_file_once(
        MM003_PREREGISTRATION_PATH, "MM-003 preregistration"
    )
    if "sha256:" + hashlib.sha256(preregistration_payload).hexdigest() != (
        MM003_PREREGISTRATION_SHA256
    ):
        raise GateError("MM-003 preregistration hash mismatch")
    preregistration_raw = contract.parse_strict_json_bytes(
        preregistration_payload, location="$.mm003_preregistration"
    )
    if not isinstance(preregistration_raw, dict):
        raise GateError("MM-003 preregistration must be an object")
    preregistration = contract.validate_preregistration(preregistration_raw)

    suite_payload = _read_regular_file_once(
        GUI_GROUNDING_SUITE_PATH, "MM-003 frozen suite"
    )
    suite = load_suite_file(GUI_GROUNDING_SUITE_PATH.resolve())
    if (
        contract.sha256_bytes(suite_payload) != contract.MM002_SUITE_FILE_SHA256
        or sha256_json(suite) != contract.MM002_SUITE_CANONICAL_SHA256
    ):
        raise GateError("MM-003 frozen suite binding mismatch")
    schema_payload = _read_regular_file_once(
        GUI_GROUNDING_PREDICTIONS_SCHEMA_PATH, "MM-003 prediction schema"
    )
    if contract.sha256_bytes(schema_payload) != contract.MM002_SCHEMA_SHA256:
        raise GateError("MM-003 prediction schema binding mismatch")

    source_receipts = preregistration["source_lineage"]["protocol_sources"]
    for name, relative in contract.PROTOCOL_SOURCE_PATHS.items():
        payload = _read_regular_file_once(ROOT / relative, f"MM-003 source {name}")
        receipt = source_receipts.get(name)
        if not isinstance(receipt, dict) or receipt != {
            "path": relative,
            "sha256": contract.sha256_bytes(payload),
        }:
            raise GateError(f"MM-003 protocol source binding mismatch: {name}")

    cases = {case["case_id"]: case for case in suite["cases"]}
    screenshot_receipts = preregistration["source_lineage"]["screenshots"]
    if len(screenshot_receipts) != 6:
        raise GateError("MM-003 screenshot receipt count mismatch")
    for receipt in screenshot_receipts:
        case_id = receipt.get("case_id")
        if case_id not in contract.SCREENSHOT_CASES:
            raise GateError("MM-003 screenshot case mismatch")
        payload = _read_regular_file_once(
            ROOT / receipt["path"], f"MM-003 screenshot {case_id}"
        )
        if (
            payload != contract.render_case_png(cases[case_id])
            or len(payload) != receipt["bytes"]
            or contract.sha256_bytes(payload) != receipt["sha256"]
        ):
            raise GateError(f"MM-003 screenshot binding mismatch: {case_id}")

    if (
        preregistration["freeze_status"] != "frozen"
        or preregistration["execution_protocol"]["generate_calls"] != 9
        or preregistration["execution_protocol"]["retry_count"] != 0
        or preregistration["formal_gate"]["quality_threshold_required"] is not False
        or preregistration["constraints"]["training"] is not False
        or preregistration["constraints"]["model_output_has_execution_authority"]
        is not False
        or preregistration["claims"]["baseline_executed"] is not False
        or preregistration["claims"]["model_evaluated"] is not False
        or preregistration["claims"]["runtime_eligible"] is not False
        or preregistration["runtime_eligible"] is not False
    ):
        raise GateError("MM-003 protocol boundary mismatch")
    next_gate = preregistration["next_gate_after_freeze"]["gate_id"]
    if next_gate != "MM-003-local-small-vlm-baseline-execution-v1":
        raise GateError("MM-003 next gate mismatch")
    return {
        "protocol_frozen": True,
        "model_id": preregistration["model"]["repo_id"],
        "model_revision": preregistration["model"]["revision"],
        "case_count": preregistration["scope"]["case_count"],
        "model_evaluated": False,
        "next_gate": next_gate,
    }


def _validate_mm003_baseline_failure_classification() -> dict[str, Any]:
    from fullcycle_bridge import mm003_baseline_failure_classification as failure
    from fullcycle_bridge import mm003_baseline_protocol as protocol

    payload = _read_regular_file_once(
        MM003_FAILURE_CLASSIFICATION_PATH, "MM-003 failure classification"
    )
    raw = protocol.parse_strict_json_bytes(
        payload, location="$.mm003_failure_classification"
    )
    if not isinstance(raw, dict):
        raise GateError("MM-003 failure classification must be an object")
    result = failure.validate_failure_classification(ROOT, raw)
    if (
        result["formal_gate_passed"] is not False
        or result["claims"]["baseline_execution_attempted"] is not True
        or result["claims"]["baseline_executed"] is not False
        or result["claims"]["model_evaluated"] is not False
        or result["claims"]["runtime_eligible"] is not False
        or result["runtime_eligible"] is not False
    ):
        raise GateError("MM-003 failure-classification boundary mismatch")
    return {
        "baseline_attempted": True,
        "formal_gate_passed": False,
        "classification": result["failure"]["classification"],
        "next_gate": result["locked_next_action"]["gate_id"],
    }


def _validate_mm003_baseline_recovery_protocol() -> dict[str, Any]:
    from fullcycle_bridge import gui_grounding_eval_v2 as scorer
    from fullcycle_bridge import mm003_baseline_protocol as v1_contract
    from fullcycle_bridge import mm003_baseline_protocol_v2 as contract

    payload = _read_regular_file_once(
        MM003_RECOVERY_PREREGISTRATION_PATH, "MM-003 recovery preregistration"
    )
    if "sha256:" + hashlib.sha256(payload).hexdigest() != (
        MM003_RECOVERY_PREREGISTRATION_SHA256
    ):
        raise GateError("MM-003 recovery preregistration hash mismatch")
    raw = contract.parse_strict_json_bytes(
        payload, location="$.mm003_recovery_preregistration"
    )
    if not isinstance(raw, dict):
        raise GateError("MM-003 recovery preregistration must be an object")
    preregistration = contract.validate_preregistration(raw)

    source_receipts = preregistration["source_lineage"]["protocol_sources"]
    for name, relative in contract.PROTOCOL_SOURCE_PATHS.items():
        source_payload = _read_regular_file_once(
            ROOT / relative, f"MM-003 recovery source {name}"
        )
        if source_receipts.get(name) != {
            "path": relative,
            "sha256": contract.sha256_bytes(source_payload),
        }:
            raise GateError(f"MM-003 recovery source binding mismatch: {name}")

    failure_payload = _read_regular_file_once(
        ROOT / contract.V1_FAILURE_ARTIFACT_PATH,
        "MM-003 v1 failure classification",
    )
    if preregistration["source_lineage"]["v1_failure_classification"] != {
        "path": contract.V1_FAILURE_ARTIFACT_PATH,
        "bytes": len(failure_payload),
        "sha256": contract.sha256_bytes(failure_payload),
        "failed_gate_id": "MM-003-local-small-vlm-baseline-execution-v1",
        "formal_gate_passed": False,
    }:
        raise GateError("MM-003 recovery failure-lineage mismatch")

    v1_payload = _read_regular_file_once(
        MM003_PREREGISTRATION_PATH, "MM-003 v1 preregistration comparison"
    )
    v1_raw = v1_contract.parse_strict_json_bytes(
        v1_payload, location="$.mm003_v1_preregistration"
    )
    if not isinstance(v1_raw, dict):
        raise GateError("MM-003 v1 preregistration must be an object")
    v1_preregistration = v1_contract.validate_preregistration(v1_raw)
    if (
        preregistration["model"] != v1_preregistration["model"]
        or preregistration["source_lineage"]["mm002_suite"]
        != v1_preregistration["source_lineage"]["mm002_suite"]
        or preregistration["source_lineage"]["screenshots"]
        != v1_preregistration["source_lineage"]["screenshots"]
    ):
        raise GateError("MM-003 recovery frozen input drift")
    for key in ("case_order", "case_modes", "image_policy", "generation", "compiler"):
        if preregistration["execution_protocol"][key] != v1_preregistration[
            "execution_protocol"
        ][key]:
            raise GateError(f"MM-003 recovery execution drift: {key}")

    suite = _load_json(GUI_GROUNDING_SUITE_PATH)
    fallback_predictions = {
        "gui_grounding_prediction_version": 1,
        "suite_id": suite["suite_id"],
        "producer": {
            "kind": "model",
            "model_id": contract.MODEL_ID,
            "model_revision": contract.MODEL_REVISION,
        },
        "records": [
            contract.compile_raw_prediction("not-json", case)
            for case in suite["cases"]
        ],
    }
    report = scorer.score_predictions(suite, fallback_predictions)
    optional_metric = report["metrics"][
        "prediction_coordinate_ref_disagreement_rate"
    ]
    if (
        optional_metric
        != {
            "correct": 0,
            "total": 0,
            "value": None,
            "status": "not_applicable",
        }
        or report["metrics"]["grounding_accuracy"]["total"] != 5
        or report["metrics"]["action_accuracy"]["total"] != 9
    ):
        raise GateError("MM-003 recovery scorer totality mismatch")

    persistence = preregistration["execution_protocol"]["persistence_policy"]
    recovery = preregistration["recovery_constraints"]
    if (
        preregistration["freeze_status"] != "frozen"
        or persistence
        != {
            "output_directory_must_be_absent_before_load": True,
            "raw_run_written_before_scoring": True,
            "compiled_predictions_written_before_scoring": True,
            "writes_are_exclusive": True,
            "scoring_failure_receipt_required": True,
            "success_evidence_written_after_scoring": True,
        }
        or any(value is not False for value in recovery.values())
        or preregistration["claims"]["baseline_executed"] is not False
        or preregistration["claims"]["model_evaluated"] is not False
        or preregistration["claims"]["runtime_eligible"] is not False
        or preregistration["runtime_eligible"] is not False
    ):
        raise GateError("MM-003 recovery boundary mismatch")
    next_gate = preregistration["next_gate_after_freeze"]["gate_id"]
    if next_gate != contract.EXECUTION_GATE_ID:
        raise GateError("MM-003 recovery next gate mismatch")
    return {
        "protocol_frozen": True,
        "source_files": len(contract.PROTOCOL_SOURCE_PATHS),
        "optional_metric_total": True,
        "next_gate": next_gate,
    }


def _validate_mm003_baseline_v2_evidence() -> dict[str, Any]:
    from scripts import validate_mm003_baseline_v2_evidence as validator

    try:
        result = validator.validate_repository(ROOT)
    except validator.MM003BaselineV2EvidenceError as exc:
        raise GateError(f"MM-003 v2 baseline evidence invalid: {exc}") from exc
    if (
        result["formal_gate_passed"] is not True
        or result["model_evaluated"] is not True
        or result["classification"] != "local_small_vlm_baseline_established"
        or result["case_count"] != 9
        or result["fallback_count"] != 9
        or result["runtime_eligible"] is not False
        or result["next_gate"] != "MM-003-small-vlm-post-training-protocol-v1"
    ):
        raise GateError("MM-003 v2 baseline decision mismatch")
    return result


def _validate_mm003_post_training_protocol() -> dict[str, Any]:
    from fullcycle_bridge import mm003_post_training_protocol as contract
    from scripts import run_mm003_qlora_post_training as runner

    payload = _read_regular_file_once(
        MM003_POST_TRAINING_PREREGISTRATION_PATH,
        "MM-003 post-training preregistration",
    )
    digest = "sha256:" + hashlib.sha256(payload).hexdigest()
    if digest != MM003_POST_TRAINING_PREREGISTRATION_SHA256:
        raise GateError("MM-003 post-training preregistration hash mismatch")
    raw = contract.parse_strict_json_bytes(
        payload, location="$.mm003_post_training_preregistration"
    )
    if not isinstance(raw, dict):
        raise GateError("MM-003 post-training preregistration must be an object")
    preregistration = contract.validate_preregistration(raw)

    inputs = runner.load_and_validate_inputs()
    expected = contract.expected_preregistration(
        freeze_status="frozen",
        model_files=preregistration["model"]["files"],
        train_receipt=inputs["train_receipt"],
        validation_receipt=inputs["validation_receipt"],
        screenshot_receipts=inputs["training_screenshot_receipts"],
        eval_screenshot_receipts=inputs["eval_screenshot_receipts"],
        source_hashes=runner.protocol_source_hashes(),
        isolation_audit=inputs["isolation_audit"],
    )
    if preregistration != expected:
        raise GateError("MM-003 post-training source or input binding mismatch")

    for name, receipt in (
        ("baseline_preregistration", contract.BASELINE_V2_PREREGISTRATION),
        ("negative_baseline", contract.BASELINE_V2_EVIDENCE),
    ):
        observed = _read_regular_file_once(
            ROOT / receipt["path"], f"MM-003 post-training {name}"
        )
        if (
            len(observed) != receipt["bytes"]
            or "sha256:" + hashlib.sha256(observed).hexdigest() != receipt["sha256"]
        ):
            raise GateError(f"MM-003 post-training lineage mismatch: {name}")

    claims = preregistration["claims"]
    if (
        preregistration["freeze_status"] != "frozen"
        or preregistration["formal_gate"]["formal_gate_passed"] is not False
        or preregistration["formal_gate"]["quality_threshold_required"] is not False
        or preregistration["training_protocol"]["accepted_training_runs"] != 1
        or preregistration["training_protocol"]["retry_count"] != 0
        or preregistration["evaluation_protocol"]["full_eval_runs"] != 1
        or preregistration["evaluation_protocol"]["generate_calls"] != 9
        or preregistration["evaluation_protocol"]["retry_count"] != 0
        or inputs["isolation_audit"]["passed"] is not True
        or any(
            value is not False
            for value in preregistration["authority_contract"].values()
        )
        or any(value is not False for value in claims.values())
        or preregistration["runtime_eligible"] is not False
    ):
        raise GateError("MM-003 post-training protocol boundary mismatch")
    next_gate = preregistration["next_gate_after_freeze"]["gate_id"]
    if next_gate != contract.EXECUTION_GATE_ID:
        raise GateError("MM-003 post-training next gate mismatch")
    return {
        "protocol_frozen": True,
        "train_records": contract.TRAIN_RECORDS,
        "validation_records": contract.VALIDATION_RECORDS,
        "screenshots": contract.SCREENSHOT_RECORDS,
        "eval_isolation": True,
        "next_gate": next_gate,
    }


def _validate_mm003_post_training_failure_classification() -> dict[str, Any]:
    from fullcycle_bridge import (
        mm003_post_training_failure_classification as failure,
    )
    from fullcycle_bridge import mm003_post_training_protocol as contract

    payload = _read_regular_file_once(
        MM003_POST_TRAINING_FAILURE_CLASSIFICATION_PATH,
        "MM-003 post-training failure classification",
    )
    raw = contract.parse_strict_json_bytes(
        payload,
        location="$.mm003_post_training_failure_classification",
    )
    if not isinstance(raw, dict):
        raise GateError("MM-003 post-training failure classification must be an object")
    result = failure.validate_failure_classification(ROOT, raw)
    claims = result["claims"]
    reproduction = result["failure"]["static_reproduction"]
    if (
        result["formal_gate_passed"] is not False
        or claims["post_training_execution_attempted"] is not True
        or any(
            value is not False
            for name, value in claims.items()
            if name != "post_training_execution_attempted"
        )
        or result["failure_receipt"]["sha256"]
        != failure.FAILURE_RECEIPT_SHA256
        or result["failure_receipt"]["directory_entries_observed"]
        != ["failure.json"]
        or reproduction["first_case_id"] != "pt-train-018"
        or reproduction["records_checked"] != 27
        or reproduction["records_failed"] != 27
        or reproduction["code"] != "CASE_MODE_MISMATCH"
        or reproduction["tracked_fixture_receipts_verified"] != 2
        or result["locked_next_action"]["gate_id"] != failure.NEXT_GATE_ID
        or result["locked_next_action"]["execution_gate_id"]
        != failure.RECOVERY_EXECUTION_GATE_ID
        or result["locked_next_action"]["experiment_id"]
        != failure.RECOVERY_EXPERIMENT_ID
        or result["locked_next_action"]["output_directory"]
        != failure.RECOVERY_OUTPUT_DIRECTORY
        or result["locked_next_action"]["success_next_gate_id"]
        != failure.RECOVERY_SUCCESS_NEXT_GATE_ID
        or result["locked_next_action"]["allowed_difference_policy"][
            "unlisted_existing_leaf_values_must_be_identical"
        ]
        is not True
        or result["locked_next_action"]["allowed_v2_differences"][
            "source_lineage.protocol_sources"
        ]["other_additions_removals_or_replacements_allowed"]
        is not False
        or result["locked_next_action"]["required_v2_values"][
            "outputs.failure"
        ]
        != f"{failure.RECOVERY_OUTPUT_DIRECTORY}/failure.json"
        or result["runtime_eligible"] is not False
    ):
        raise GateError("MM-003 post-training failure boundary mismatch")
    return {
        "execution_attempted": True,
        "formal_gate_passed": False,
        "classification": result["failure"]["classification"],
        "receipt_sha256": result["failure_receipt"]["sha256"],
        "next_gate": result["locked_next_action"]["gate_id"],
    }


def _validate_mm003_post_training_recovery_protocol() -> dict[str, Any]:
    from fullcycle_bridge import mm003_post_training_protocol_v2 as contract
    from scripts import run_mm003_qlora_post_training_v2 as runner

    payload = _read_regular_file_once(
        MM003_POST_TRAINING_RECOVERY_PREREGISTRATION_PATH,
        "MM-003 post-training recovery preregistration",
    )
    digest = "sha256:" + hashlib.sha256(payload).hexdigest()
    if (
        len(payload) != 26_553
        or digest != MM003_POST_TRAINING_RECOVERY_PREREGISTRATION_SHA256
    ):
        raise GateError("MM-003 post-training recovery preregistration hash mismatch")
    raw = contract.parse_strict_json_bytes(
        payload, location="$.mm003_post_training_recovery_preregistration"
    )
    if not isinstance(raw, dict):
        raise GateError(
            "MM-003 post-training recovery preregistration must be an object"
        )
    inputs = runner.load_and_validate_inputs()
    lineage = runner._load_recovery_lineage()
    trusted_source_hashes = runner.protocol_source_hashes()
    preregistration = contract.validate_preregistration(
        raw,
        v1_preregistration=lineage["v1_preregistration"],
        train=inputs["train"],
        validation=inputs["validation"],
        source_hashes=trusted_source_hashes,
    )
    expected = contract.expected_preregistration(
        freeze_status="frozen",
        v1_preregistration=lineage["v1_preregistration"],
        source_hashes=trusted_source_hashes,
        train=inputs["train"],
        validation=inputs["validation"],
    )
    if preregistration != expected or contract.artifact_json_bytes(expected) != payload:
        raise GateError("MM-003 post-training recovery preregistration drift")
    delta = contract.validate_recovery_delta(
        lineage["v1_preregistration"],
        preregistration,
        train=inputs["train"],
        validation=inputs["validation"],
        source_hashes=trusted_source_hashes,
    )
    prompt_preflight = contract.validate_prompt_preflight(
        preregistration,
        train=inputs["train"],
        validation=inputs["validation"],
    )
    claims = preregistration["claims"]
    if (
        preregistration["freeze_status"] != "frozen"
        or preregistration["formal_gate"]["required_gates"]
        != contract.REQUIRED_GATES
        or preregistration["formal_gate"]["formal_gate_passed"] is not False
        or preregistration["formal_gate"]["quality_threshold_required"] is not False
        or len(preregistration["source_lineage"]["protocol_sources"]) != 12
        or len(preregistration["prompt_receipts"]["records"]) != 27
        or prompt_preflight["records_checked"] != 27
        or prompt_preflight["receipts_matched"] is not True
        or len(delta["exact_value_replacements"]) != 12
        or len(delta["preserved_protocol_sources"]) != 10
        or len(delta["added_protocol_sources"]) != 2
        or len(delta["authorized_new_sections"]) != 4
        or any(
            value is not False
            for value in preregistration["authority_contract"].values()
        )
        or any(value is not False for value in claims.values())
        or preregistration["runtime_eligible"] is not False
        or preregistration["next_gate_after_freeze"]["gate_id"]
        != contract.EXECUTION_GATE_ID
        or preregistration["success_next_gate_after_execution"]["gate_id"]
        != contract.SUCCESS_NEXT_GATE_ID
    ):
        raise GateError("MM-003 post-training recovery protocol boundary mismatch")
    return {
        "protocol_frozen": True,
        "source_files": len(contract.PROTOCOL_SOURCE_PATHS),
        "prompt_receipts": len(preregistration["prompt_receipts"]["records"]),
        "exact_value_replacements": len(delta["exact_value_replacements"]),
        "next_gate": preregistration["next_gate_after_freeze"]["gate_id"],
    }


def _validate_mm003_post_training_result_review() -> dict[str, Any]:
    from scripts import validate_mm003_post_training_v2_result as validator

    try:
        result = validator.validate_repository(ROOT)
    except validator.MM003PostTrainingV2ResultError as exc:
        raise GateError(f"MM-003 post-training v2 result invalid: {exc}") from exc
    if (
        result["formal_gate_passed"] is not True
        or result["training_executed"] is not True
        or result["adapter_independently_loadable"] is not True
        or result["model_evaluated"] is not True
        or result["compiler_fallback_count"] != 0
        or result["grounding_accuracy"]
        != {"correct": 3, "total": 5, "value": 0.6}
        or result["action_accuracy"]
        != {"correct": 3, "total": 9, "value": 1 / 3}
        or result["repeatability_established"] is not False
        or result["next_gate"] != validator.NEXT_GATE_ID
        or result["runtime_eligible"] is not False
    ):
        raise GateError("MM-003 post-training v2 result decision mismatch")
    return result


def _validate_mm003_post_training_eval_repeatability_protocol() -> dict[str, Any]:
    from fullcycle_bridge import mm003_post_training_eval_repeatability as contract
    from scripts import run_mm003_post_training_eval_repeatability as runner

    payload = _read_regular_file_once(
        MM003_POST_TRAINING_EVAL_REPEATABILITY_PREREGISTRATION_PATH,
        "MM-003 post-training eval-repeatability preregistration",
    )
    digest = "sha256:" + hashlib.sha256(payload).hexdigest()
    if (
        len(payload)
        != MM003_POST_TRAINING_EVAL_REPEATABILITY_PREREGISTRATION_BYTES
        or digest != MM003_POST_TRAINING_EVAL_REPEATABILITY_PREREGISTRATION_SHA256
    ):
        raise GateError(
            "MM-003 post-training eval-repeatability preregistration hash mismatch"
        )
    raw = contract.parse_strict_json_bytes(
        payload,
        location="$.mm003_post_training_eval_repeatability_preregistration",
    )
    if not isinstance(raw, dict) or contract.artifact_json_bytes(raw) != payload:
        raise GateError(
            "MM-003 post-training eval-repeatability preregistration must be a "
            "canonical object"
        )

    context = runner.load_authenticated_context()
    source_hashes = runner.protocol_source_hashes()
    preregistration = contract.validate_preregistration(
        raw,
        source_hashes=source_hashes,
        upstream_preregistration=context["upstream_preregistration"],
        reference_evidence=context["reference_evidence"],
        reference_predictions=context["reference_predictions"],
        result_review=context["result_review"],
        suite=context["suite"],
    )
    expected = contract.expected_preregistration(
        freeze_status="frozen",
        source_hashes=source_hashes,
        upstream_preregistration=context["upstream_preregistration"],
        reference_evidence=context["reference_evidence"],
        reference_predictions=context["reference_predictions"],
        result_review=context["result_review"],
        suite=context["suite"],
    )
    if preregistration != expected or contract.artifact_json_bytes(expected) != payload:
        raise GateError(
            "MM-003 post-training eval-repeatability preregistration drift"
        )

    execution = preregistration["execution_protocol"]
    consumption = execution["attempt_consumption"]
    outputs = preregistration["outputs"]
    claims = preregistration["claims"]
    if (
        preregistration["freeze_status"] != "frozen"
        or preregistration["formal_gate"]["required_gates"]
        != contract.REQUIRED_GATES
        or preregistration["formal_gate"]["formal_gate_passed"] is not False
        or preregistration["formal_gate"]["quality_threshold_required"] is not False
        or len(preregistration["source_lineage"]["protocol_sources"]) != 17
        or execution["model_snapshot_root"] != contract.MODEL_SNAPSHOT_ROOT
        or execution["run_count"] != 1
        or execution["full_eval_runs"] != 1
        or execution["generate_calls"] != contract.EXPECTED_CASES
        or execution["training_runs"] != 0
        or execution["retry_count"] != 0
        or execution["network_used"] is not False
        or consumption["consumed_when"]
        != "owner_marked_staging_directory_atomically_renamed_to_fixed_output"
        or consumption["attempt_owner_written_before_consumption"] is not True
        or outputs["attempt_owner"] != contract.ATTEMPT_OWNER_ARTIFACT
        or outputs["output_directory"] != contract.RUN_OUTPUT_ROOT
        or preregistration["resource_caps"] != contract.RESOURCE_CAPS
        or any(
            value is not False
            for value in preregistration["authority_contract"].values()
        )
        or any(value is not False for value in claims.values())
        or preregistration["runtime_eligible"] is not False
        or preregistration["next_gate_after_freeze"]["gate_id"]
        != contract.EXECUTION_GATE_ID
    ):
        raise GateError(
            "MM-003 post-training eval-repeatability protocol boundary mismatch"
        )
    return {
        "protocol_frozen": True,
        "source_files": len(contract.PROTOCOL_SOURCE_PATHS),
        "required_gates": len(contract.REQUIRED_GATES),
        "case_count": contract.EXPECTED_CASES,
        "next_gate": preregistration["next_gate_after_freeze"]["gate_id"],
    }


def _validate_mm003_post_training_eval_repeatability_result() -> dict[str, Any]:
    from scripts import (
        validate_mm003_post_training_eval_repeatability_result as validator,
    )

    try:
        result = validator.validate_repository(ROOT)
    except validator.MM003EvalRepeatabilityResultError as exc:
        raise GateError(
            f"MM-003 post-training eval-repeatability result invalid: {exc}"
        ) from exc
    if (
        result["formal_gate_passed"] is not True
        or result["classification"] != validator.CLASSIFICATION
        or result["all_layers_exact"] is not True
        or result["raw_outputs_exact"] != 9
        or result["generated_token_counts_exact"] != 9
        or result["compiled_predictions_exact"] != 9
        or result["compiler_fallback_status_exact"] is not True
        or result["metrics_exact"] is not True
        or result["same_machine_eval_repeatability_established"] is not True
        or result["training_repeatability_established"] is not False
        or result["next_gate"] != validator.NEXT_GATE_ID
        or result["runtime_eligible"] is not False
    ):
        raise GateError(
            "MM-003 post-training eval-repeatability result decision mismatch"
        )
    return result


def _validate_mm004_hard_negative_protocol() -> dict[str, Any]:
    from fullcycle_bridge import multimodal_hard_negative as contract
    from scripts import prepare_mm004_multimodal_hard_negative_protocol as prepare

    payload = _read_regular_file_once(
        MM004_HARD_NEGATIVE_PROTOCOL_PATH,
        "MM-004 hard-negative protocol",
    )
    digest = "sha256:" + hashlib.sha256(payload).hexdigest()
    if (
        len(payload) != MM004_HARD_NEGATIVE_PROTOCOL_BYTES
        or digest != MM004_HARD_NEGATIVE_PROTOCOL_SHA256
    ):
        raise GateError("MM-004 hard-negative protocol hash mismatch")
    raw = _load_json_payload(payload, MM004_HARD_NEGATIVE_PROTOCOL_PATH)
    if contract.canonical_json_bytes(raw) != payload:
        raise GateError("MM-004 hard-negative protocol is not canonical JSON")

    receipts = prepare.source_receipts()
    exclusions = prepare.exclusion_registry()
    expected = contract.expected_protocol(
        freeze_status="frozen",
        source_receipts=receipts,
        exclusions=exclusions,
    )
    summary = contract.validate_protocol(
        raw,
        source_receipts=receipts,
        exclusions=exclusions,
    )
    if expected != raw or contract.canonical_json_bytes(expected) != payload:
        raise GateError("MM-004 hard-negative protocol reconstruction drift")
    if (
        len(receipts) != 32
        or summary.category_count != 7
        or summary.excluded_case_count != 36
        or summary.excluded_family_count != 36
        or summary.protocol_frozen is not True
        or summary.records_generated is not False
        or any(raw["claims"].values())
        or raw["authority_contract"]
        != {
            "model_output_has_execution_authority": False,
            "runtime_is_sole_policy_approval_wal_dispatch_boundary": True,
            "runtime_policy_or_approval_bypass": False,
            "runtime_integration_changed": False,
        }
        or summary.next_gate != contract.NEXT_GATE
    ):
        raise GateError("MM-004 hard-negative protocol boundary mismatch")
    return summary.to_dict()


def _validate_mm004_hard_negative_generation_protocol() -> dict[str, Any]:
    from fullcycle_bridge import mm004_hard_negative_generation as contract
    from scripts import run_mm004_hard_negative_generation as runner

    payload = _read_regular_file_once(
        MM004_HARD_NEGATIVE_GENERATION_PROTOCOL_PATH,
        "MM-004 hard-negative generation protocol",
    )
    digest = "sha256:" + hashlib.sha256(payload).hexdigest()
    if (
        len(payload) != MM004_HARD_NEGATIVE_GENERATION_PROTOCOL_BYTES
        or digest != MM004_HARD_NEGATIVE_GENERATION_PROTOCOL_SHA256
    ):
        raise GateError("MM-004 hard-negative generation protocol hash mismatch")
    raw = _load_json_payload(
        payload, MM004_HARD_NEGATIVE_GENERATION_PROTOCOL_PATH
    )
    if contract.artifact_json_bytes(raw) != payload:
        raise GateError("MM-004 generation protocol is not canonical JSON")

    sources = runner.source_receipts()
    parent_receipt = runner.parent_protocol_receipt()
    expected = runner.expected_preregistration(freeze_status="frozen")
    validated = contract.validate_preregistration(
        raw,
        source_receipts=sources,
        parent_protocol_receipt=parent_receipt,
    )
    if expected != validated or contract.artifact_json_bytes(expected) != payload:
        raise GateError("MM-004 generation protocol reconstruction drift")
    plan = validated["generation_plan"]
    if (
        len(sources) != 4
        or len(validated["planned_outputs"]) != 31
        or plan["seed"] != 44_004
        or plan["families_per_category"] != 4
        or plan["pair_count"] != 28
        or plan["record_count"] != 56
        or plan["image_count"] != 28
        or any(validated["claims"].values())
        or validated["next_gate"] != contract.EXECUTION_GATE_ID
    ):
        raise GateError("MM-004 generation protocol boundary mismatch")

    planned_paths = set(validated["planned_outputs"])
    _validate_mm004_output_tree(ROOT / contract.OUTPUT_ROOT, planned_paths)
    output_payloads = {
        path: _read_regular_file_once(
            ROOT / path,
            f"MM-004 hard-negative generated output {path}",
        )
        for path in sorted(planned_paths)
    }
    parent_payload = _read_regular_file_once(
        MM004_HARD_NEGATIVE_PROTOCOL_PATH,
        "MM-004 hard-negative parent protocol",
    )
    parent_protocol = _load_json_payload(
        parent_payload, MM004_HARD_NEGATIVE_PROTOCOL_PATH
    )
    exclusions = parent_protocol["exclusion_registry"]
    output_summary = contract.validate_output_payloads(
        output_payloads,
        preregistration=validated,
        exclusions=exclusions,
    )

    evidence_path = ROOT / contract.EVIDENCE_PATH
    evidence_payload = _read_regular_file_once(
        evidence_path,
        "MM-004 hard-negative generation evidence",
    )
    evidence = _load_json_payload(evidence_payload, evidence_path)
    if contract.artifact_json_bytes(evidence) != evidence_payload:
        raise GateError("MM-004 generation evidence is not canonical JSON")
    evidence_summary = contract.validate_evidence(
        evidence,
        protocol_freeze_commit=MM004_HARD_NEGATIVE_GENERATION_FREEZE_COMMIT,
        preregistration_payload=payload,
        output_payloads=output_payloads,
        exclusions=exclusions,
    )
    if evidence_summary != output_summary:
        raise GateError("MM-004 generation evidence summary drift")
    _validate_mm004_output_tree(ROOT / contract.OUTPUT_ROOT, planned_paths)
    summary = evidence_summary.to_dict()
    claims = evidence["claims"]
    return {
        "protocol_frozen": True,
        "protocol_freeze_commit": MM004_HARD_NEGATIVE_GENERATION_FREEZE_COMMIT,
        "planned_families": contract.FAMILY_COUNT,
        "planned_records": contract.RECORD_COUNT,
        "planned_images": contract.IMAGE_COUNT,
        **summary,
        "output_files": len(output_payloads),
        "output_bytes": sum(len(item) for item in output_payloads.values()),
        "evidence_sha256": "sha256:" + hashlib.sha256(evidence_payload).hexdigest(),
        "model_evaluated": claims["model_evaluated"],
        "safety_established": claims["safety_established"],
        "runtime_eligible": claims["runtime_eligible"],
    }


def _validate_mm004_hard_negative_model_evaluation_protocol() -> dict[str, Any]:
    from fullcycle_bridge import (
        mm004_hard_negative_model_evaluation as contract,
    )
    from scripts import run_mm004_hard_negative_model_evaluation as runner

    predecessor_payload = _read_regular_file_once(
        MM004_HARD_NEGATIVE_MODEL_EVALUATION_PROTOCOL_V1_PATH,
        "MM-004 hard-negative model-evaluation protocol v1",
    )
    predecessor_digest = "sha256:" + hashlib.sha256(predecessor_payload).hexdigest()
    if (
        len(predecessor_payload)
        != MM004_HARD_NEGATIVE_MODEL_EVALUATION_PROTOCOL_V1_BYTES
        or predecessor_digest
        != MM004_HARD_NEGATIVE_MODEL_EVALUATION_PROTOCOL_V1_SHA256
    ):
        raise GateError("MM-004 model-evaluation v1 protocol hash mismatch")
    predecessor = contract.parse_strict_json_bytes(
        predecessor_payload, location="$.predecessor_preregistration"
    )
    if (
        not isinstance(predecessor, dict)
        or contract.artifact_json_bytes(predecessor) != predecessor_payload
    ):
        raise GateError("MM-004 model-evaluation v1 is not canonical JSON")
    predecessor_claims = predecessor.get("claims")
    predecessor_outputs = predecessor.get("outputs")
    if (
        predecessor.get("mm004_hard_negative_model_evaluation_protocol_version")
        != 1
        or predecessor.get("gate_id") != contract.PREDECESSOR_PROTOCOL_GATE_ID
        or predecessor.get("freeze_status") != "frozen"
        or predecessor.get("next_gate") != contract.PREDECESSOR_EXECUTION_GATE_ID
        or not isinstance(predecessor_claims, dict)
        or any(predecessor_claims.values())
        or not isinstance(predecessor_outputs, dict)
        or predecessor_outputs.get("output_directory")
        != contract.PREDECESSOR_RUN_OUTPUT_ROOT
        or os.path.lexists(ROOT / contract.PREDECESSOR_RUN_OUTPUT_ROOT)
    ):
        raise GateError("MM-004 model-evaluation v1 boundary mismatch")

    payload = _read_regular_file_once(
        MM004_HARD_NEGATIVE_MODEL_EVALUATION_PROTOCOL_V2_PATH,
        "MM-004 hard-negative model-evaluation protocol v2",
    )
    digest = "sha256:" + hashlib.sha256(payload).hexdigest()
    if (
        len(payload) != MM004_HARD_NEGATIVE_MODEL_EVALUATION_PROTOCOL_V2_BYTES
        or digest != MM004_HARD_NEGATIVE_MODEL_EVALUATION_PROTOCOL_V2_SHA256
    ):
        raise GateError("MM-004 model-evaluation v2 protocol hash mismatch")
    raw = contract.parse_strict_json_bytes(payload, location="$.preregistration")
    if not isinstance(raw, dict) or contract.artifact_json_bytes(raw) != payload:
        raise GateError("MM-004 model-evaluation v2 is not canonical JSON")

    context = runner.load_authenticated_context()
    sources = runner.source_receipts()
    validated = contract.validate_preregistration(
        raw,
        generation_evidence=context["generation_evidence"],
        candidate_repeatability_protocol=context[
            "candidate_repeatability_protocol"
        ],
        candidate_result_review=context["candidate_result_review"],
        records=context["records"],
        source_receipts=sources,
    )
    expected = contract.expected_preregistration(
        freeze_status="frozen",
        generation_evidence=context["generation_evidence"],
        candidate_repeatability_protocol=context[
            "candidate_repeatability_protocol"
        ],
        candidate_result_review=context["candidate_result_review"],
        records=context["records"],
        source_receipts=sources,
    )
    claims = validated["claims"]
    if (
        expected != validated
        or contract.artifact_json_bytes(expected) != payload
        or len(sources) != 9
        or validated["mm004_hard_negative_model_evaluation_protocol_version"] != 2
        or validated["freeze_status"] != "frozen"
        or validated["input_suite"]["record_count"] != 56
        or validated["input_suite"]["pair_count"] != 28
        or validated["input_suite"]["image_count"] != 28
        or validated["execution_protocol"]["generate_calls"] != 56
        or validated["execution_protocol"]["retry_count"] != 0
        or validated["execution_protocol"]["network_used"] is not False
        or any(claims.values())
        or validated["next_gate"] != contract.EXECUTION_GATE_ID
    ):
        raise GateError("MM-004 model-evaluation v2 boundary mismatch")
    predecessor_lineage = validated["source_lineage"]["predecessor_protocol"]
    lfs_pointer = validated["source_lineage"]["adapter_git_lfs_pointer"]
    if (
        predecessor_lineage["preregistration"]
        != contract.CONTEXT_RECEIPTS["predecessor_model_evaluation_protocol"]
        or predecessor_lineage["freeze_commit"]
        != contract.PREDECESSOR_PROTOCOL_FREEZE_COMMIT
        or predecessor_lineage["attempt_consumed"] is not False
        or predecessor_lineage["model_imported"] is not False
        or predecessor_lineage["model_calls"] != 0
        or predecessor_lineage["output_absent"] is not True
        or lfs_pointer["bytes"] != 133
        or lfs_pointer["sha256"]
        != contract.sha256_bytes(
            contract.git_lfs_pointer_bytes(contract.ADAPTER_RECEIPTS["weights"])
        )
    ):
        raise GateError("MM-004 model-evaluation v2 repair boundary mismatch")
    return {
        "protocol_frozen": True,
        "protocol_version": 2,
        "predecessor_attempt_consumed": predecessor_lineage["attempt_consumed"],
        "predecessor_model_imported": predecessor_lineage["model_imported"],
        "predecessor_model_calls": predecessor_lineage["model_calls"],
        "predecessor_output_absent": predecessor_lineage["output_absent"],
        "predecessor_classification": predecessor_lineage["classification"],
        "registered_records": validated["input_suite"]["record_count"],
        "registered_pairs": validated["input_suite"]["pair_count"],
        "registered_images": validated["input_suite"]["image_count"],
        "evaluation_executed": claims["evaluation_executed"],
        "model_evaluated": claims["model_evaluated"],
        "training_executed": claims["training_executed"],
        "runtime_eligible": claims["runtime_eligible"],
        "next_gate": validated["next_gate"],
    }


def _validate_mm004_hard_negative_model_evaluation_result_review() -> dict[str, Any]:
    from scripts import (
        validate_mm004_hard_negative_model_evaluation_result as validator,
    )

    try:
        summary = validator.validate_repository(ROOT)
    except validator.MM004HardNegativeResultError as exc:
        raise GateError(f"MM-004 model-evaluation result review failed: {exc}") from exc
    if (
        summary.get("formal_gate_passed") is not True
        or summary.get("classification") != validator.CLASSIFICATION
        or summary.get("record_count") != 56
        or summary.get("overall_accuracy") != 4 / 7
        or summary.get("clean_accept_recall") != 1 / 7
        or summary.get("hard_negative_rejection_recall") != 1.0
        or summary.get("pair_exact_accuracy") != 1 / 7
        or summary.get("compiler_validity") != 13 / 14
        or summary.get("clean_false_rejects") != 20
        or summary.get("clean_invalid_outputs") != 4
        or summary.get("hard_negative_false_accepts") != 0
        or summary.get("evaluation_executed") is not True
        or summary.get("model_evaluated") is not True
        or summary.get("training_executed") is not False
        or summary.get("quality_improved") is not False
        or summary.get("evidence_sha256")
        != validator.ARTIFACTS["evidence"]["sha256"]
        or summary.get("review_bytes") != validator.REVIEW_BYTES
        or summary.get("review_sha256") != validator.REVIEW_SHA256
        or summary.get("next_gate") != validator.NEXT_GATE_ID
        or summary.get("runtime_eligible") is not False
    ):
        raise GateError("MM-004 model-evaluation result-review boundary mismatch")
    return summary


def _validate_mm005_environment_adaptation_protocol() -> dict[str, Any]:
    from fullcycle_bridge import multimodal_environment_adaptation as contract
    from scripts import (
        prepare_mm005_multimodal_environment_adaptation_protocol as prepare,
    )

    payload = _read_regular_file_once(
        MM005_ENVIRONMENT_ADAPTATION_PROTOCOL_PATH,
        "MM-005 environment-adaptation protocol",
    )
    digest = "sha256:" + hashlib.sha256(payload).hexdigest()
    if (
        len(payload) != MM005_ENVIRONMENT_ADAPTATION_PROTOCOL_BYTES
        or digest != MM005_ENVIRONMENT_ADAPTATION_PROTOCOL_SHA256
    ):
        raise GateError("MM-005 environment-adaptation protocol hash mismatch")
    raw = _load_json_payload(payload, MM005_ENVIRONMENT_ADAPTATION_PROTOCOL_PATH)
    if contract.canonical_json_bytes(raw) != payload:
        raise GateError("MM-005 environment-adaptation protocol is not canonical JSON")

    receipts = prepare.source_receipts()
    exclusions = prepare.exclusion_registry()
    expected = contract.expected_protocol(
        freeze_status="frozen",
        source_receipts=receipts,
        exclusions=exclusions,
    )
    summary = contract.validate_protocol(
        raw,
        source_receipts=receipts,
        exclusions=exclusions,
    )
    if expected != raw or contract.canonical_json_bytes(expected) != payload:
        raise GateError("MM-005 environment-adaptation protocol reconstruction drift")

    registry = raw.get("exclusion_registry")
    sequence = raw.get("environment_sequence")
    delta = raw.get("component_delta_contract")
    authority = raw.get("authority_contract")
    if (
        len(receipts) != 63
        or sum(receipt["path"].endswith(".png") for receipt in receipts.values())
        != 52
        or not isinstance(registry, dict)
        or {key: len(value) for key, value in registry.items()}
        != {
            "case_ids": 92,
            "family_ids": 64,
            "image_sha256": 52,
            "instruction_content_sha256": 64,
            "observation_content_sha256": 64,
            "target_content_sha256": 92,
        }
        or summary.task_family_count != 4
        or summary.protocol_frozen is not True
        or summary.dataset_generated is not False
        or not isinstance(sequence, dict)
        or sequence.get("registered_order") != list(contract.ENVIRONMENT_ORDER)
        or sequence.get("selected_environment") != contract.SELECTED_ENVIRONMENT
        or sequence.get("selected_order_index") != 2
        or sequence.get("sequence_skip_allowed") is not False
        or not isinstance(delta, dict)
        or delta.get("new_component_kinds")
        != [
            "environment_adapter",
            "task_set",
            "deterministic_verifier",
            "synthetic_dataset",
        ]
        or delta.get("new_component_count") != 4
        or authority
        != {
            "model_output_has_execution_authority": False,
            "runtime_is_sole_policy_approval_wal_grounding_budget_dispatch_boundary": True,
            "runtime_repository_changed": False,
            "runtime_integration_authorized": False,
            "capture_authorized": False,
        }
        or any(raw["claims"].values())
        or summary.next_gate != contract.NEXT_GATE
    ):
        raise GateError("MM-005 environment-adaptation protocol boundary mismatch")
    return summary.to_dict()


def _validate_mm005_document_chart_pdf_data_protocol() -> dict[str, Any]:
    from fullcycle_bridge import mm005_document_chart_pdf_data as contract
    from scripts import prepare_mm005_document_chart_pdf_data_protocol as prepare

    payload = _read_regular_file_once(
        MM005_DOCUMENT_CHART_PDF_DATA_PROTOCOL_PATH,
        "MM-005 Document/Chart/PDF data protocol",
    )
    digest = "sha256:" + hashlib.sha256(payload).hexdigest()
    if (
        len(payload) != MM005_DOCUMENT_CHART_PDF_DATA_PROTOCOL_BYTES
        or digest != MM005_DOCUMENT_CHART_PDF_DATA_PROTOCOL_SHA256
    ):
        raise GateError("MM-005 Document/Chart/PDF data protocol hash mismatch")
    raw = _load_json_payload(payload, MM005_DOCUMENT_CHART_PDF_DATA_PROTOCOL_PATH)
    if contract.artifact_json_bytes(raw) != payload:
        raise GateError("MM-005 Document/Chart/PDF data protocol is not canonical JSON")

    sources = prepare.source_receipts()
    parent_receipt = prepare.parent_protocol_receipt()
    expected = contract.expected_preregistration(
        freeze_status="frozen",
        source_receipts=sources,
        parent_protocol_receipt=parent_receipt,
    )
    summary = contract.validate_preregistration(
        raw,
        source_receipts=sources,
        parent_protocol_receipt=parent_receipt,
    )
    if expected != raw or contract.artifact_json_bytes(expected) != payload:
        raise GateError("MM-005 Document/Chart/PDF data protocol reconstruction drift")

    parent_protocol = prepare.parent_prepare.build_protocol()
    planned_outputs = prepare.planned_output_payloads()
    planned = contract.validate_planned_output_payloads(
        planned_outputs,
        parent_protocol_sha256=str(parent_receipt["sha256"]),
        exclusions=parent_protocol["exclusion_registry"],
    )
    plan = raw.get("generation_plan")
    authority = raw.get("authority_contract")
    output_exists = (ROOT / contract.OUTPUT_ROOT).exists()
    evidence_exists = (ROOT / contract.EVIDENCE_PATH).exists()
    if (
        output_exists != evidence_exists
        or len(sources) != 5
        or summary.template_count != 32
        or summary.record_count != 32
        or summary.image_count != 32
        or summary.source_artifact_count != 14
        or summary.train_records != 24
        or summary.validation_records != 8
        or summary.output_file_count != 49
        or summary.output_bytes != 434_212
        or summary.protocol_frozen is not True
        or summary.generation_executed is not False
        or summary.dataset_validated is not False
        or planned
        != {
            "planned_output_rebuild_valid": True,
            "template_count": 32,
            "record_count": 32,
            "image_count": 32,
            "source_artifact_count": 14,
            "train_records": 24,
            "validation_records": 8,
            "output_file_count": 49,
            "output_bytes": 434_212,
            "generation_executed": False,
            "dataset_validated": False,
            "next_gate": contract.NEXT_GATE,
        }
        or not isinstance(plan, dict)
        or plan.get("seed") != 55_005
        or len(plan.get("template_registry", [])) != 32
        or plan.get("renderer", {}).get("host_font_used") is not False
        or plan.get("renderer", {}).get("pdf_source", {}).get(
            "external_renderer_used"
        )
        is not False
        or authority
        != {
            "model_output_has_execution_authority": False,
            "runtime_is_sole_policy_approval_wal_grounding_budget_dispatch_boundary": True,
            "runtime_repository_changed": False,
            "runtime_integration_authorized": False,
            "capture_authorized": False,
        }
        or any(raw["claims"].values())
        or summary.next_gate != contract.NEXT_GATE
    ):
        raise GateError("MM-005 Document/Chart/PDF data protocol boundary mismatch")
    return {
        **summary.to_dict(),
        "seed": contract.SEED,
        "source_receipt_count": len(sources),
        "planned_output_rebuild_valid": planned["planned_output_rebuild_valid"],
        "execution_artifacts_present": output_exists,
    }


def _validate_mm005_document_chart_pdf_generation_protocol() -> dict[str, Any]:
    from fullcycle_bridge import mm005_document_chart_pdf_data as data_contract
    from fullcycle_bridge import (
        mm005_document_chart_pdf_generation as contract,
    )
    from scripts import run_mm005_document_chart_pdf_generation as runner

    protocol_payload = _read_regular_file_once(
        MM005_DOCUMENT_CHART_PDF_GENERATION_PROTOCOL_PATH,
        "MM-005 Document/Chart/PDF generation protocol",
    )
    digest = "sha256:" + hashlib.sha256(protocol_payload).hexdigest()
    if (
        len(protocol_payload) != MM005_DOCUMENT_CHART_PDF_GENERATION_PROTOCOL_BYTES
        or digest != MM005_DOCUMENT_CHART_PDF_GENERATION_PROTOCOL_SHA256
    ):
        raise GateError("MM-005 Document/Chart/PDF generation protocol hash mismatch")
    raw = _load_json_payload(
        protocol_payload, MM005_DOCUMENT_CHART_PDF_GENERATION_PROTOCOL_PATH
    )
    if contract.artifact_json_bytes(raw) != protocol_payload:
        raise GateError("MM-005 generation protocol is not canonical JSON")

    data_payload, data_protocol, data_sources, parent_receipt = (
        runner.data_protocol_context()
    )
    sources = runner.source_receipts()
    expected = runner.expected_protocol(freeze_status="frozen")
    validated = contract.validate_protocol(
        raw,
        source_receipts=sources,
        data_protocol_payload=data_payload,
    )
    if expected != validated or contract.artifact_json_bytes(expected) != protocol_payload:
        raise GateError("MM-005 generation protocol reconstruction drift")
    plan = validated.get("execution_plan")
    if (
        len(sources) != 4
        or len(validated.get("planned_outputs", {})) != 49
        or not isinstance(plan, dict)
        or plan.get("output_file_count") != 49
        or plan.get("output_bytes") != 434_212
        or plan.get("internal_retry_limit") != 0
        or plan.get("atomic_output_root_required") is not True
        or plan.get("exclusive_evidence_write_required") is not True
        or plan.get("independent_readback_validation_required") is not True
        or any(validated["claims"].values())
        or validated.get("next_gate") != contract.EXECUTION_GATE_ID
    ):
        raise GateError("MM-005 generation protocol boundary mismatch")

    parent_payload = _read_regular_file_once(
        ROOT / data_contract.PARENT_PROTOCOL_PATH,
        "MM-005 environment-adaptation parent protocol",
    )
    parent_protocol = _load_json_payload(
        parent_payload, ROOT / data_contract.PARENT_PROTOCOL_PATH
    )
    exclusions = parent_protocol["exclusion_registry"]
    parent_binding = data_protocol["parent_protocol"]
    planned_outputs = data_contract.expected_output_payloads(
        str(parent_binding["sha256"])
    )
    planned_summary = contract.validate_output_payloads(
        planned_outputs,
        protocol=validated,
        data_protocol=data_protocol,
        exclusions=exclusions,
    )
    if (
        planned_summary.output_file_count != 49
        or planned_summary.output_bytes != 434_212
        or planned_summary.record_count != 32
        or planned_summary.image_count != 32
        or planned_summary.source_artifact_count != 14
    ):
        raise GateError("MM-005 generation planned-output validation drift")

    output_root = ROOT / contract.OUTPUT_ROOT
    evidence_path = ROOT / contract.EVIDENCE_PATH
    output_exists = output_root.exists()
    evidence_exists = evidence_path.exists()
    if output_exists != evidence_exists:
        raise GateError("MM-005 generation execution artifacts are incomplete")
    if not output_exists:
        return {
            "protocol_frozen": True,
            "protocol_freeze_commit": None,
            "template_count": data_contract.TEMPLATE_COUNT,
            "record_count": data_contract.RECORD_COUNT,
            "image_count": data_contract.IMAGE_COUNT,
            "source_artifact_count": data_contract.PDF_COUNT,
            "train_records": data_contract.TRAIN_RECORDS,
            "validation_records": data_contract.VALIDATION_RECORDS,
            "output_file_count": data_contract.OUTPUT_FILE_COUNT,
            "output_bytes": planned_summary.output_bytes,
            "generation_executed": False,
            "records_generated": False,
            "images_generated": False,
            "dataset_validated": False,
            "evidence_sha256": None,
            "next_gate": contract.EXECUTION_GATE_ID,
        }

    planned_paths = set(validated["planned_outputs"])
    _validate_mm005_output_tree(output_root, planned_paths)
    output_payloads = {
        path: _read_regular_file_once(
            ROOT / path,
            f"MM-005 Document/Chart/PDF generated output {path}",
        )
        for path in sorted(planned_paths)
    }
    evidence_payload = _read_regular_file_once(
        evidence_path,
        "MM-005 Document/Chart/PDF generation evidence",
    )
    evidence = _load_json_payload(evidence_payload, evidence_path)
    if contract.artifact_json_bytes(evidence) != evidence_payload:
        raise GateError("MM-005 generation evidence is not canonical JSON")
    freeze_commit = evidence.get("protocol_freeze_commit")
    if not isinstance(freeze_commit, str):
        raise GateError("MM-005 generation evidence freeze commit is missing")
    frozen_paths = {
        contract.PROTOCOL_PATH,
        contract.DATA_PROTOCOL_PATH,
        *runner.SOURCE_PATHS.values(),
    }
    for relative in sorted(frozen_paths):
        tracked = subprocess.run(
            ["git", "show", f"{freeze_commit}:{relative}"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout
        if tracked != _read_regular_file_once(
            ROOT / relative, f"MM-005 frozen generation source {relative}"
        ):
            raise GateError(f"MM-005 generation freeze source drift: {relative}")
    evidence_summary = contract.validate_evidence(
        evidence,
        protocol_freeze_commit=freeze_commit,
        protocol_payload=protocol_payload,
        source_receipts=sources,
        data_protocol_payload=data_payload,
        data_source_receipts=data_sources,
        parent_protocol_receipt=parent_receipt,
        output_payloads=output_payloads,
        exclusions=exclusions,
    )
    _validate_mm005_output_tree(output_root, planned_paths)
    claims = evidence["claims"]
    if (
        claims != contract.EXECUTION_CLAIMS
        or evidence_summary.generation_executed is not True
        or evidence_summary.dataset_validated is not True
        or evidence_summary.next_gate != contract.NEXT_GATE
    ):
        raise GateError("MM-005 generation execution claim drift")
    return {
        "protocol_frozen": True,
        "protocol_freeze_commit": freeze_commit,
        **evidence_summary.to_dict(),
        "evidence_sha256": "sha256:" + hashlib.sha256(evidence_payload).hexdigest(),
    }


def _validate_mm005_document_chart_pdf_adapter_verifier_protocol() -> dict[str, Any]:
    from fullcycle_bridge import (
        mm005_document_chart_pdf_adapter_verifier_protocol as contract,
    )
    from scripts import (
        prepare_mm005_document_chart_pdf_adapter_verifier_protocol as prepare,
    )

    payload = _read_regular_file_once(
        MM005_DOCUMENT_CHART_PDF_ADAPTER_VERIFIER_PROTOCOL_PATH,
        "MM-005 Document/Chart/PDF Adapter/Verifier protocol",
    )
    digest = "sha256:" + hashlib.sha256(payload).hexdigest()
    if (
        len(payload) != MM005_DOCUMENT_CHART_PDF_ADAPTER_VERIFIER_PROTOCOL_BYTES
        or digest != MM005_DOCUMENT_CHART_PDF_ADAPTER_VERIFIER_PROTOCOL_SHA256
    ):
        raise GateError(
            "MM-005 Document/Chart/PDF Adapter/Verifier protocol hash mismatch"
        )
    raw = _load_json_payload(
        payload, MM005_DOCUMENT_CHART_PDF_ADAPTER_VERIFIER_PROTOCOL_PATH
    )
    if contract.artifact_json_bytes(raw) != payload:
        raise GateError("MM-005 Adapter/Verifier protocol is not canonical JSON")

    inputs = prepare.protocol_inputs()
    summary = contract.validate_protocol(raw, **inputs)
    adapter = raw.get("adapter_contract")
    verifier = raw.get("verifier_contract")
    coverage = raw.get("coverage")
    plan = raw.get("implementation_plan")
    authority = raw.get("authority_contract")
    true_claims = {
        name for name, established in raw.get("claims", {}).items() if established
    }
    if (
        raw.get("freeze_status") != "frozen"
        or raw.get("gate_id") != contract.GATE_ID
        or raw.get("next_gate") != contract.NEXT_GATE
        or len(inputs["source_receipts"]) != 8
        or summary.source_receipt_count != 8
        or summary.record_count != 32
        or summary.adapter_projection_count != 32
        or summary.verifier_case_count != 160
        or summary.positive_case_count != 32
        or summary.negative_case_count != 128
        or summary.task_family_count != 4
        or summary.source_kind_count != 4
        or summary.train_records != 24
        or summary.validation_records != 8
        or summary.generation_executed is not True
        or summary.dataset_validated is not True
        or summary.environment_adapter_implemented is not False
        or summary.verifier_implemented is not False
        or summary.next_gate != contract.NEXT_GATE
        or not isinstance(adapter, dict)
        or adapter.get("model_payload_exact_keys") != list(contract.MODEL_PAYLOAD_KEYS)
        or adapter.get("image_binding_outside_model_payload") is not True
        or adapter.get("real_file_path_exposed_to_model") is not False
        or adapter.get("gold_or_verifier_fields_exposed_to_model") is not False
        or adapter.get("formal_implementation_present") is not False
        or adapter.get("formal_execution_at_this_gate") is not False
        or not isinstance(verifier, dict)
        or verifier.get("case_kinds") != list(contract.VERIFIER_CASE_KINDS)
        or verifier.get("cases_per_record") != 5
        or verifier.get("invalid_output_is_wrong") is not True
        or verifier.get("model_or_llm_judge_used") is not False
        or verifier.get("formal_implementation_present") is not False
        or verifier.get("formal_execution_at_this_gate") is not False
        or coverage
        != {
            "records": 32,
            "train_records": 24,
            "validation_records": 8,
            "task_family_ids": sorted(
                {item["task_family_id"] for item in raw["adapter_projection_registry"]}
            ),
            "source_kinds": sorted(
                {item["source_kind"] for item in raw["adapter_projection_registry"]}
            ),
            "splits": ["train", "validation"],
            "adapter_projections": 32,
            "verifier_cases": 160,
            "positive_cases": 32,
            "negative_cases": 128,
        }
        or not isinstance(plan, dict)
        or plan.get("implementation_gate_id") != contract.NEXT_GATE
        or plan.get("protocol_must_merge_before_implementation") is not True
        or plan.get("dataset_and_generation_evidence_read_only") is not True
        or plan.get("network_allowed") is not False
        or plan.get("model_load_allowed") is not False
        or plan.get("model_training_or_evaluation_allowed") is not False
        or plan.get("real_or_external_content_allowed") is not False
        or plan.get("capture_allowed") is not False
        or plan.get("runtime_repository_change_allowed") is not False
        or plan.get("runtime_integration_allowed") is not False
        or raw.get("required_gates") != list(contract.REQUIRED_GATES)
        or authority
        != {
            "model_output_has_execution_authority": False,
            "runtime_is_sole_policy_approval_wal_grounding_budget_dispatch_boundary": True,
            "runtime_repository_changed": False,
            "runtime_integration_authorized": False,
            "capture_authorized": False,
        }
        or raw.get("claims") != contract.PROTOCOL_CLAIMS
        or true_claims
        != {
            "generation_executed",
            "records_generated",
            "images_generated",
            "dataset_validated",
        }
    ):
        raise GateError("MM-005 Adapter/Verifier protocol boundary mismatch")
    return {"protocol_frozen": True, **summary.to_dict()}


def _validate_mm005_document_chart_pdf_adapter_verifier_implementation() -> (
    dict[str, Any]
):
    from fullcycle_bridge import (
        mm005_document_chart_pdf_adapter_verifier_implementation as contract,
    )
    from scripts import (
        prepare_mm005_document_chart_pdf_adapter_verifier_implementation as prepare,
    )

    payload = _read_regular_file_once(
        MM005_DOCUMENT_CHART_PDF_ADAPTER_VERIFIER_IMPLEMENTATION_EVIDENCE_PATH,
        "MM-005 Document/Chart/PDF Adapter/Verifier implementation evidence",
    )
    digest = "sha256:" + hashlib.sha256(payload).hexdigest()
    if (
        len(payload)
        != MM005_DOCUMENT_CHART_PDF_ADAPTER_VERIFIER_IMPLEMENTATION_EVIDENCE_BYTES
        or digest
        != MM005_DOCUMENT_CHART_PDF_ADAPTER_VERIFIER_IMPLEMENTATION_EVIDENCE_SHA256
    ):
        raise GateError("MM-005 Adapter/Verifier implementation evidence hash mismatch")
    raw = _load_json_payload(
        payload,
        MM005_DOCUMENT_CHART_PDF_ADAPTER_VERIFIER_IMPLEMENTATION_EVIDENCE_PATH,
    )
    if contract.artifact_json_bytes(raw) != payload:
        raise GateError("MM-005 Adapter/Verifier evidence is not canonical JSON")

    inputs = prepare.implementation_inputs()
    summary = contract.validate_evidence(raw, **inputs)
    protocol_binding = raw.get("protocol")
    consumed = raw.get("consumed_inputs")
    adapter = raw.get("adapter_implementation")
    verifier = raw.get("verifier_implementation")
    authority = raw.get("authority_contract")
    true_claims = {
        name for name, established in raw.get("claims", {}).items() if established
    }
    if (
        raw.get("gate_id") != contract.GATE_ID
        or raw.get("next_gate") != contract.NEXT_GATE
        or not isinstance(protocol_binding, dict)
        or protocol_binding.get("merge_commit") != contract.PROTOCOL_MERGE_COMMIT
        or protocol_binding.get("required_before_implementation") is not True
        or len(inputs["implementation_source_receipts"]) != 5
        or summary.source_receipt_count != 5
        or summary.record_count != 32
        or summary.image_count != 32
        or summary.adapter_projection_count != 32
        or summary.model_payload_bytes != 31_430
        or summary.image_bytes != 314_128
        or summary.verifier_case_count != 160
        or summary.compiler_valid_count != 96
        or summary.compiler_invalid_count != 64
        or summary.positive_case_count != 32
        or summary.negative_case_count != 128
        or summary.environment_adapter_implemented is not True
        or summary.environment_adapter_executed is not True
        or summary.verifier_implemented is not True
        or summary.verifier_executed is not True
        or summary.model_evaluated is not False
        or summary.next_gate != contract.NEXT_GATE
        or not isinstance(consumed, dict)
        or consumed.get("read_only") is not True
        or consumed.get("generation_rerun") is not False
        or not isinstance(adapter, dict)
        or adapter.get("image_bytes_outside_model_payload") is not True
        or adapter.get("real_file_path_exposed_to_model") is not False
        or adapter.get("gold_or_verifier_fields_exposed_to_model") is not False
        or adapter.get("projection_registry_exact") is not True
        or len(adapter.get("execution_registry", [])) != 32
        or not isinstance(verifier, dict)
        or verifier.get("model_or_llm_judge_used") is not False
        or verifier.get("invalid_output_is_wrong") is not True
        or verifier.get("case_registry_exact") is not True
        or verifier.get("case_distribution")
        != {
            "duplicate_evidence": 32,
            "exact_expected": 32,
            "wrong_answer": 32,
            "wrong_evidence": 32,
            "wrong_page": 32,
        }
        or len(verifier.get("execution_registry", [])) != 160
        or raw.get("required_gates") != list(contract.REQUIRED_GATES)
        or raw.get("gate_results")
        != {gate: True for gate in contract.REQUIRED_GATES}
        or authority
        != {
            "model_output_has_execution_authority": False,
            "runtime_is_sole_policy_approval_wal_grounding_budget_dispatch_boundary": True,
            "runtime_repository_changed": False,
            "runtime_integration_authorized": False,
            "capture_authorized": False,
        }
        or raw.get("claims") != contract.IMPLEMENTATION_CLAIMS
        or true_claims
        != {
            "generation_executed",
            "records_generated",
            "images_generated",
            "dataset_validated",
            "environment_adapter_implemented",
            "environment_adapter_executed",
            "verifier_implemented",
            "verifier_executed",
        }
    ):
        raise GateError("MM-005 Adapter/Verifier implementation boundary mismatch")
    return {
        "evidence_valid": True,
        **summary.to_dict(),
        "evidence_sha256": digest,
    }


def _validate_mm005_document_chart_pdf_model_evaluation_protocol() -> dict[str, Any]:
    from fullcycle_bridge import (
        mm005_document_chart_pdf_model_evaluation as contract,
    )
    from scripts import prepare_mm005_document_chart_pdf_model_evaluation as prepare

    payload = _read_regular_file_once(
        MM005_DOCUMENT_CHART_PDF_MODEL_EVALUATION_PROTOCOL_PATH,
        "MM-005 Document/Chart/PDF model-evaluation protocol",
    )
    digest = "sha256:" + hashlib.sha256(payload).hexdigest()
    if (
        len(payload) != MM005_DOCUMENT_CHART_PDF_MODEL_EVALUATION_PROTOCOL_BYTES
        or digest != MM005_DOCUMENT_CHART_PDF_MODEL_EVALUATION_PROTOCOL_SHA256
    ):
        raise GateError("MM-005 model-evaluation protocol hash mismatch")
    raw = _load_json_payload(
        payload,
        MM005_DOCUMENT_CHART_PDF_MODEL_EVALUATION_PROTOCOL_PATH,
    )
    if contract.artifact_json_bytes(raw) != payload:
        raise GateError("MM-005 model-evaluation protocol is not canonical JSON")

    inputs = prepare.protocol_inputs()
    expected = contract.validate_preregistration(raw, **inputs)
    input_suite = raw.get("input_suite")
    execution = raw.get("execution_protocol")
    formal_gate = raw.get("formal_gate")
    freeze_preconditions = raw.get("freeze_preconditions")
    claims = raw.get("claims")
    source_receipts = raw.get("source_receipts")
    prompt_projections = (
        input_suite.get("prompt_projection_registry", [])
        if isinstance(input_suite, dict)
        else []
    )
    model_payload_bytes = sum(
        projection.get("model_payload", {}).get("bytes", 0)
        for projection in prompt_projections
        if isinstance(projection, dict)
    )
    image_bytes = sum(
        projection.get("image_payload", {}).get("bytes", 0)
        for projection in prompt_projections
        if isinstance(projection, dict)
    )
    true_claims = {
        name for name, established in claims.items() if established
    } if isinstance(claims, dict) else set()
    if (
        contract.artifact_json_bytes(expected) != payload
        or raw.get("gate_id") != contract.PROTOCOL_GATE_ID
        or raw.get("next_gate") != contract.EXECUTION_GATE_ID
        or raw.get("freeze_status") != "frozen"
        or raw.get("decision")
        != "outcome_neutral_read_only_cross_environment_baseline_measurement_preregistration"
        or not isinstance(input_suite, dict)
        or input_suite.get("record_count") != 32
        or input_suite.get("train_records") != 24
        or input_suite.get("validation_records") != 8
        or input_suite.get("all_records_measured") is not True
        or len(prompt_projections) != 32
        or model_payload_bytes != 31_430
        or image_bytes != 314_128
        or not isinstance(execution, dict)
        or execution.get("run_count") != 1
        or execution.get("fresh_base_loads") != 1
        or execution.get("independent_adapter_loads") != 1
        or execution.get("generate_calls") != 32
        or execution.get("retry_count") != 0
        or execution.get("network_used") is not False
        or execution.get("training_runs") != 0
        or not isinstance(formal_gate, dict)
        or formal_gate.get("required_gates") != list(contract.REQUIRED_GATES)
        or formal_gate.get("accuracy_threshold_gate") is not False
        or formal_gate.get("resource_cap_is_integrity_gate") is not True
        or freeze_preconditions
        != {
            "fixed_output_absent": True,
            "model_imported_at_protocol_freeze": False,
            "model_called_at_protocol_freeze": False,
            "attempt_consumed_at_protocol_freeze": False,
        }
        or claims != contract.FREEZE_CLAIMS
        or true_claims
        != {
            "generation_executed",
            "dataset_validated",
            "environment_adapter_implemented",
            "environment_adapter_executed",
            "verifier_implemented",
            "verifier_executed",
        }
        or not isinstance(source_receipts, dict)
        or len(source_receipts) != len(contract.PROTOCOL_SOURCE_PATHS)
        or len(inputs["source_receipts"]) != len(contract.PROTOCOL_SOURCE_PATHS)
    ):
        raise GateError("MM-005 model-evaluation protocol boundary mismatch")
    return {
        "protocol_frozen": True,
        "prompt_projection_count": len(prompt_projections),
        "model_payload_bytes": model_payload_bytes,
        "image_bytes": image_bytes,
        "generate_calls": execution["generate_calls"],
        "attempt_consumed": claims["attempt_consumed"],
        "model_evaluated": claims["model_evaluated"],
        "next_gate": raw["next_gate"],
        "protocol_sha256": digest,
    }


def _validate_mm005_output_tree(output_root: Path, expected_paths: set[str]) -> None:
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    actual_paths: set[str] = set()
    try:
        root_stat = output_root.lstat()
    except OSError as exc:
        raise GateError("MM-005 generation output root is missing") from exc
    if (
        not stat.S_ISDIR(root_stat.st_mode)
        or output_root.is_symlink()
        or bool(getattr(root_stat, "st_file_attributes", 0) & reparse_flag)
    ):
        raise GateError("MM-005 generation output root is unsafe")
    for current, directories, filenames in os.walk(output_root, followlinks=False):
        current_path = Path(current)
        for name in directories:
            directory = current_path / name
            directory_stat = directory.lstat()
            if (
                not stat.S_ISDIR(directory_stat.st_mode)
                or directory.is_symlink()
                or bool(
                    getattr(directory_stat, "st_file_attributes", 0) & reparse_flag
                )
            ):
                raise GateError(f"unsafe MM-005 output directory: {directory}")
        for name in filenames:
            actual_paths.add((current_path / name).relative_to(ROOT).as_posix())
    if actual_paths != expected_paths:
        raise GateError("MM-005 generation output tree mismatch")


def _validate_mm004_output_tree(output_root: Path, expected_paths: set[str]) -> None:
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    actual_paths: set[str] = set()
    try:
        root_stat = output_root.lstat()
    except OSError as exc:
        raise GateError("MM-004 generation output root is missing") from exc
    if (
        not stat.S_ISDIR(root_stat.st_mode)
        or output_root.is_symlink()
        or bool(getattr(root_stat, "st_file_attributes", 0) & reparse_flag)
    ):
        raise GateError("MM-004 generation output root is unsafe")
    for current, directories, filenames in os.walk(output_root, followlinks=False):
        current_path = Path(current)
        for name in directories:
            directory = current_path / name
            directory_stat = directory.lstat()
            if (
                not stat.S_ISDIR(directory_stat.st_mode)
                or directory.is_symlink()
                or bool(
                    getattr(directory_stat, "st_file_attributes", 0) & reparse_flag
                )
            ):
                raise GateError(f"unsafe MM-004 output directory: {directory}")
        for name in filenames:
            actual_paths.add((current_path / name).relative_to(ROOT).as_posix())
    if actual_paths != expected_paths:
        raise GateError("MM-004 generation output tree mismatch")


def _validate_named_hashes(artifacts: object) -> None:
    if not isinstance(artifacts, dict) or not artifacts:
        raise GateError("named artifact hashes are missing")
    for relative, expected in artifacts.items():
        path = ROOT / relative
        if not path.is_file() or path.is_symlink():
            raise GateError(f"unsafe or missing artifact: {relative}")
        actual = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise GateError(f"artifact digest mismatch: {relative}")


def _validate_merge_stability() -> dict[str, Any]:
    from fullcycle_bridge.tool_router import fixture_digest, load_fixture
    from fullcycle_bridge.tool_router_sft import (
        canonical_config_sha256,
        directory_artifact_manifest,
        file_sha256,
    )

    gate = _load_json(TOOL_ROUTER_MERGE_STABILITY_PATH)
    config = _load_json(ROOT / "configs" / "tool_router_lora_sft_v2.json")
    training = _load_json(ROOT / "baseline" / "fc-mvp-001-lora-sft-v2-training.json")
    adapter = ROOT / "baseline" / "adapters" / "fc-mvp-001-lora-sft-v2"
    evaluation = load_fixture(ROOT / config["data"]["eval_path"])
    runs = gate.get("runs")
    if (
        gate.get("config_sha256") != canonical_config_sha256(config)
        or gate.get("adapter_files") != directory_artifact_manifest(adapter)
        or gate.get("adapter_files") != training["final_adapter"]["files"]
        or gate.get("eval_digest") != fixture_digest(evaluation)
        or gate.get("prompt_sha256") != file_sha256(ROOT / config["prompt"]["path"])
    ):
        raise GateError("Tool Router merge-stability source drift")
    if not isinstance(runs, list) or len(runs) != 4:
        raise GateError("Tool Router merge-stability runs are invalid")
    token_digests = [run.get("token_ids_sha256") for run in runs]
    if not (
        token_digests[0] == token_digests[1]
        and token_digests[2] == token_digests[3]
        and token_digests[0] != token_digests[2]
    ):
        raise GateError("Tool Router merge-stability repeat evidence drift")
    acceptance = gate.get("acceptance")
    token_analysis = gate.get("token_analysis")
    locked_next_action = gate.get("locked_next_action")
    if (
        not isinstance(acceptance, dict)
        or not acceptance
        or not all(value is True for value in acceptance.values())
        or not isinstance(token_analysis, dict)
        or token_analysis.get("first_divergent_token_index") != 45
        or gate.get("classification") != "deterministic_bf16_merge_logit_boundary_flip"
        or gate.get("merged_artifact_allowed") is not False
        or gate.get("merged_artifact_saved") is not False
        or gate.get("runtime_eligible") is not False
        or not isinstance(locked_next_action, dict)
        or locked_next_action.get("gate_id") != "FC-MVP-001-bf16-merge-numerics-v1"
    ):
        raise GateError("Tool Router merge-stability acceptance drift")
    return gate


def _validate_merge_numerics(stability: dict[str, Any]) -> dict[str, Any]:
    from fullcycle_bridge.tool_router_sft import (
        canonical_config_sha256,
        directory_artifact_manifest,
        file_sha256,
    )

    gate = _load_json(TOOL_ROUTER_MERGE_NUMERICS_PATH)
    config = _load_json(ROOT / "configs" / "tool_router_lora_sft_v2.json")
    adapter = ROOT / "baseline" / "adapters" / "fc-mvp-001-lora-sft-v2"
    if (
        gate.get("config_sha256") != canonical_config_sha256(config)
        or gate.get("adapter_files") != directory_artifact_manifest(adapter)
        or gate.get("stability_evidence_sha256")
        != file_sha256(TOOL_ROUTER_MERGE_STABILITY_PATH)
        or gate.get("eval_digest") != stability.get("eval_digest")
    ):
        raise GateError("Tool Router merge-numerics source drift")
    acceptance = gate.get("acceptance")
    analysis = gate.get("module_analysis")
    rounding = gate.get("merge_rounding")
    next_action = gate.get("locked_next_action")
    if (
        not isinstance(acceptance, dict)
        or not acceptance
        or not all(value is True for value in acceptance.values())
        or not isinstance(analysis, dict)
        or analysis.get("first_divergent_module") != "model.layers.0.self_attn.q_proj"
        or analysis.get("first_divergent_module_index") != 2
        or analysis.get("preceding_modules_identical") is not True
        or not isinstance(rounding, dict)
        or rounding.get("target_modules") != 112
        or rounding.get("actual_merged_mismatched_weights") != 0
        or not isinstance(rounding.get("ideal_nonzero_updates_rounded_to_base"), int)
        or rounding["ideal_nonzero_updates_rounded_to_base"] <= 0
        or gate.get("classification") != "bf16_safe_merge_weight_rounding"
        or gate.get("merged_artifact_allowed") is not False
        or gate.get("merged_artifact_saved") is not False
        or gate.get("runtime_eligible") is not False
        or not isinstance(next_action, dict)
        or next_action.get("gate_id") != "FC-MVP-001-bf16-merge-remediation-v1"
    ):
        raise GateError("Tool Router merge-numerics acceptance drift")
    return gate


def _validate_merge_remediation(
    stability: dict[str, Any],
    numerics: dict[str, Any],
) -> dict[str, Any]:
    from fullcycle_bridge.tool_router import fixture_digest, load_fixture
    from fullcycle_bridge.tool_router_sft import (
        canonical_config_sha256,
        directory_artifact_manifest,
        file_sha256,
    )

    gate = _load_json(TOOL_ROUTER_MERGE_REMEDIATION_PATH)
    config = _load_json(ROOT / "configs" / "tool_router_lora_sft_v2.json")
    adapter = ROOT / "baseline" / "adapters" / "fc-mvp-001-lora-sft-v2"
    evaluation = load_fixture(ROOT / config["data"]["eval_path"])
    expected_top_level = {
        "merge_remediation_version",
        "experiment_id",
        "source_experiment_id",
        "stability_evidence_sha256",
        "numerics_evidence_sha256",
        "training_lock_sha256",
        "config_sha256",
        "adapter_files",
        "model_weight_sha256",
        "prompt_sha256",
        "eval_digest",
        "example_id",
        "input_token_count",
        "input_token_ids_sha256",
        "storage_audit",
        "reference",
        "frozen_bf16_merged_control",
        "candidate_protocol",
        "runs",
        "analysis",
        "classification",
        "remediation_gate",
        "acceptance",
        "elapsed_seconds",
        "peak_gpu_memory_bytes",
        "merged_artifact_saved",
        "merged_artifact_allowed",
        "constraints",
        "locked_next_action",
        "runtime_eligible",
        "runtime_eligibility_reason",
        "offline",
    }
    if (
        set(gate) != expected_top_level
        or gate.get("merge_remediation_version") != 1
        or gate.get("experiment_id") != "fc-mvp-001-bf16-merge-remediation-v1"
        or gate.get("source_experiment_id") != config.get("experiment_id")
        or gate.get("config_sha256") != canonical_config_sha256(config)
        or gate.get("adapter_files") != directory_artifact_manifest(adapter)
        or gate.get("stability_evidence_sha256")
        != file_sha256(TOOL_ROUTER_MERGE_STABILITY_PATH)
        or gate.get("numerics_evidence_sha256")
        != file_sha256(TOOL_ROUTER_MERGE_NUMERICS_PATH)
        or gate.get("training_lock_sha256")
        != file_sha256(ROOT / "requirements" / "training.lock")
        or gate.get("model_weight_sha256")
        != f"sha256:{config['model']['weight_sha256']}"
        or gate.get("prompt_sha256") != file_sha256(ROOT / config["prompt"]["path"])
        or gate.get("eval_digest") != fixture_digest(evaluation)
        or gate.get("eval_digest") != numerics.get("eval_digest")
        or gate.get("input_token_count") != stability.get("input_token_count")
        or gate.get("input_token_ids_sha256") != stability.get("input_token_ids_sha256")
        or gate.get("example_id") != "eval-001"
    ):
        raise GateError("Tool Router merge-remediation source drift")
    if gate.get("storage_audit") != {
        "base_checkpoint": {
            "tensors": 338,
            "elements": 1543714304,
            "dtype_tensors": {"bfloat16": 338},
            "dtype_elements": {"bfloat16": 1543714304},
        },
        "adapter": {
            "tensors": 224,
            "elements": 4358144,
            "dtype_tensors": {"float32": 224},
            "dtype_elements": {"float32": 4358144},
        },
    }:
        raise GateError("Tool Router merge-remediation storage dtype drift")

    independent = [run for run in stability["runs"] if run.get("path") == "independent"]
    merged = [run for run in stability["runs"] if run.get("path") == "merged"]
    reference = gate.get("reference")
    control = gate.get("frozen_bf16_merged_control")
    if (
        len(independent) != 2
        or len(merged) != 2
        or not isinstance(reference, dict)
        or reference.get("path") != "independent_bf16_adapter"
        or reference.get("token_count") != independent[0].get("token_count")
        or reference.get("token_ids_sha256") != independent[0].get("token_ids_sha256")
        or reference.get("output_sha256") != independent[0].get("output_sha256")
        or not isinstance(control, dict)
        or control.get("path") != "safe_merged_bf16"
        or control.get("token_count") != merged[0].get("token_count")
        or control.get("token_ids_sha256") != merged[0].get("token_ids_sha256")
        or control.get("output_sha256") != merged[0].get("output_sha256")
    ):
        raise GateError("Tool Router merge-remediation frozen references drift")

    protocol = gate.get("candidate_protocol")
    expected_protocol = {
        "checkpoint_storage_dtype": "bfloat16",
        "base_load_dtype": "float32",
        "adapter_storage_dtype": "float32",
        "adapter_load_dtype": "float32",
        "merge_dtype": "float32",
        "inference_dtype": "float32",
        "safe_merge": True,
        "adapter_names": ["default"],
        "attn_implementation": "sdpa",
        "attention_class": "Qwen2Attention",
        "attention_dispatch": "ALL_ATTENTION_FUNCTIONS['sdpa']",
        "output_attentions": False,
        "do_sample": False,
        "max_new_tokens": 256,
        "use_cache": True,
        "repetition_penalty": 1.1,
        "model_eos_token_ids": [151645, 151643],
        "model_pad_token_id": 151643,
        "call_pad_token_id": 151645,
        "tf32": False,
        "autocast": False,
        "device": "cuda:0",
        "fresh_loads": 2,
        "max_residual_cuda_bytes": 16777216,
    }
    if protocol != expected_protocol:
        raise GateError("Tool Router merge-remediation protocol drift")

    runs = gate.get("runs")
    if (
        not isinstance(runs, list)
        or len(runs) != 2
        or [run.get("path") for run in runs] != ["fp32_safe_merged", "fp32_safe_merged"]
        or [run.get("repeat") for run in runs] != [1, 2]
        or runs[0].get("token_count") != runs[1].get("token_count")
        or runs[0].get("token_count") != reference.get("token_count")
        or runs[0].get("token_count") != control.get("token_count")
        or runs[0].get("token_ids_sha256") != runs[1].get("token_ids_sha256")
        or runs[0].get("output_sha256") != runs[1].get("output_sha256")
        or runs[0].get("token_ids_sha256") != control.get("token_ids_sha256")
        or runs[0].get("output_sha256") != control.get("output_sha256")
        or runs[0].get("token_ids_sha256") == reference.get("token_ids_sha256")
    ):
        raise GateError("Tool Router merge-remediation run evidence drift")
    for run in runs:
        precision = run.get("precision_audit")
        if not isinstance(precision, dict):
            raise GateError("Tool Router merge-remediation precision evidence missing")
        pre = precision.get("pre_merge")
        post = precision.get("post_merge")
        generation = precision.get("generation")
        if (
            not isinstance(pre, dict)
            or not isinstance(post, dict)
            or not isinstance(generation, dict)
            or pre.get("lora_target_modules") != 112
            or pre.get("lora_parameter_tensors") != 224
            or pre.get("adapter_parameters_finite") is not True
            or pre.get("active_adapters") != ["default"]
            or pre.get("is_peft_model") is not True
            or pre.get("input_output_embeddings_tied") is not True
            or pre.get("attn_implementation") != "sdpa"
            or pre.get("attention_class") != "Qwen2Attention"
            or pre.get("output_attentions") is not False
            or pre.get("hf_device_map") is not None
            or not _fp32_cuda_inventory(
                pre.get("base_parameters"),
                expected_elements=1543714304,
            )
            or not _fp32_cuda_inventory(
                pre.get("adapter_parameters"),
                expected_elements=4358144,
            )
            or not _fp32_cuda_inventory(
                pre.get("floating_buffers"),
                expected_elements=64,
            )
            or post.get("lora_target_modules") != 0
            or post.get("lora_parameter_tensors") != 0
            or post.get("is_peft_model") is not False
            or post.get("input_output_embeddings_tied") is not True
            or post.get("attn_implementation") != "sdpa"
            or post.get("attention_class") != "Qwen2Attention"
            or post.get("output_attentions") is not False
            or post.get("hf_device_map") is not None
            or not _fp32_cuda_inventory(
                post.get("parameters"),
                expected_elements=1543714304,
            )
            or not _fp32_cuda_inventory(
                post.get("floating_buffers"),
                expected_elements=64,
            )
            or generation
            != {
                "score_dtypes": ["float32"],
                "all_scores_float32": True,
                "autocast_enabled": False,
                "training": False,
            }
            or not isinstance(run.get("memory_allocated_before_load_bytes"), int)
            or run["memory_allocated_before_load_bytes"]
            > protocol["max_residual_cuda_bytes"]
            or not isinstance(run.get("memory_allocated_after_release_bytes"), int)
            or run["memory_allocated_after_release_bytes"]
            > protocol["max_residual_cuda_bytes"]
        ):
            raise GateError("Tool Router merge-remediation FP32 audit drift")

    acceptance = gate.get("acceptance")
    expected_acceptance = {
        "upstream_evidence_locked",
        "frozen_input_reproduced",
        "candidate_runs_completed",
        "candidate_result_classified",
        "candidate_protocol_executed",
        "source_storage_dtypes_locked",
        "frozen_bf16_merged_control_compared",
        "fresh_load_memory_isolated",
        "source_adapter_unchanged",
        "source_model_unchanged",
        "eval_digest_unchanged",
        "prompt_digest_unchanged",
    }
    remediation = gate.get("remediation_gate")
    next_action = gate.get("locked_next_action")
    constraints = {
        "new_data": False,
        "training": False,
        "eval_answer_tuning": False,
        "runtime_integration": False,
        "full_eval_run": False,
        "merged_artifact_promotion": False,
    }
    if (
        not isinstance(acceptance, dict)
        or set(acceptance) != expected_acceptance
        or not all(value is True for value in acceptance.values())
        or gate.get("classification") != "deterministic_fp32_merge_output_drift"
        or not isinstance(remediation, dict)
        or set(remediation)
        != {
            "candidate_repeats_identical",
            "independent_bf16_reference_token_identity",
            "independent_bf16_reference_output_identity",
            "frozen_bf16_merged_token_identity",
            "frozen_bf16_merged_output_identity",
            "passed",
        }
        or remediation.get("candidate_repeats_identical") is not True
        or remediation.get("independent_bf16_reference_token_identity") is not False
        or remediation.get("independent_bf16_reference_output_identity") is not False
        or remediation.get("frozen_bf16_merged_token_identity") is not True
        or remediation.get("frozen_bf16_merged_output_identity") is not True
        or remediation.get("passed") is not False
        or gate.get("merged_artifact_saved") is not False
        or gate.get("merged_artifact_allowed") is not False
        or gate.get("constraints") != constraints
        or gate.get("runtime_eligible") is not False
        or gate.get("runtime_eligibility_reason")
        != "deterministic_fp32_merge_output_drift"
        or gate.get("offline") is not True
        or not isinstance(next_action, dict)
        or next_action.get("gate_id") != "FC-MVP-001-fp32-merge-drift-analysis-v1"
    ):
        raise GateError("Tool Router merge-remediation acceptance drift")
    return gate


def _validate_fp32_merge_drift(remediation: dict[str, Any]) -> dict[str, Any]:
    from fullcycle_bridge.tool_router import fixture_digest, load_fixture
    from fullcycle_bridge.tool_router_fp32_merge_drift import analyze_path_tokens
    from fullcycle_bridge.tool_router_merge_remediation import token_ids_sha256
    from fullcycle_bridge.tool_router_sft import (
        canonical_config_sha256,
        directory_artifact_manifest,
        file_sha256,
    )

    gate = _load_json(TOOL_ROUTER_FP32_MERGE_DRIFT_PATH)
    config = _load_json(ROOT / "configs" / "tool_router_lora_sft_v2.json")
    training = _load_json(ROOT / "baseline" / "fc-mvp-001-lora-sft-v2-training.json")
    adapter = ROOT / "baseline" / "adapters" / "fc-mvp-001-lora-sft-v2"
    evaluation = load_fixture(ROOT / config["data"]["eval_path"])
    expected_top_level = {
        "fp32_merge_drift_analysis_version",
        "experiment_id",
        "source_experiment_id",
        "remediation_evidence_sha256",
        "stability_evidence_sha256",
        "numerics_evidence_sha256",
        "training_lock_sha256",
        "config_sha256",
        "adapter_files",
        "model_weight_sha256",
        "prompt_sha256",
        "eval_digest",
        "example_id",
        "input_token_count",
        "input_token_ids_sha256",
        "storage_audit",
        "protocol",
        "frozen_references",
        "runs",
        "reproduction",
        "token_analysis",
        "selection_score_evidence",
        "raw_logit_evidence",
        "classification",
        "analysis_gate",
        "remediation_gate",
        "acceptance",
        "elapsed_seconds",
        "peak_gpu_memory_bytes",
        "merged_artifact_saved",
        "merged_artifact_allowed",
        "constraints",
        "locked_next_action",
        "runtime_eligible",
        "runtime_eligibility_reason",
        "offline",
    }
    if (
        set(gate) != expected_top_level
        or file_sha256(TOOL_ROUTER_FP32_MERGE_DRIFT_PATH)
        != "sha256:ae5d1c7ace24c6cfcfed0eca60354cd3dfa9579fa0aea4e1f64c66eb73e41ea3"
        or gate.get("fp32_merge_drift_analysis_version") != 1
        or gate.get("experiment_id") != "fc-mvp-001-fp32-merge-drift-analysis-v1"
        or gate.get("source_experiment_id") != config.get("experiment_id")
        or gate.get("config_sha256") != canonical_config_sha256(config)
        or gate.get("adapter_files") != directory_artifact_manifest(adapter)
        or gate.get("adapter_files") != training["final_adapter"]["files"]
        or gate.get("stability_evidence_sha256")
        != file_sha256(TOOL_ROUTER_MERGE_STABILITY_PATH)
        or gate.get("numerics_evidence_sha256")
        != file_sha256(TOOL_ROUTER_MERGE_NUMERICS_PATH)
        or gate.get("remediation_evidence_sha256")
        != file_sha256(TOOL_ROUTER_MERGE_REMEDIATION_PATH)
        or gate.get("training_lock_sha256")
        != file_sha256(ROOT / "requirements" / "training.lock")
        or gate.get("model_weight_sha256")
        != f"sha256:{config['model']['weight_sha256']}"
        or gate.get("prompt_sha256") != file_sha256(ROOT / config["prompt"]["path"])
        or gate.get("eval_digest") != fixture_digest(evaluation)
        or gate.get("example_id") != "eval-001"
        or gate.get("input_token_count") != 339
        or gate.get("input_token_count") != remediation.get("input_token_count")
        or gate.get("input_token_ids_sha256")
        != remediation.get("input_token_ids_sha256")
    ):
        raise GateError("Tool Router FP32 merge-drift source drift")

    expected_storage = {
        "base_checkpoint": {
            "tensors": 338,
            "elements": 1543714304,
            "dtype_tensors": {"bfloat16": 338},
            "dtype_elements": {"bfloat16": 1543714304},
        },
        "adapter": {
            "tensors": 224,
            "elements": 4358144,
            "dtype_tensors": {"float32": 224},
            "dtype_elements": {"float32": 4358144},
        },
    }
    expected_protocol = {
        "freshness_scope": "fresh_model_load_lifecycle_in_fixed_process",
        "path_order": ["independent_bf16_adapter", "fp32_safe_merged"],
        "fresh_loads_per_path": 1,
        "max_residual_cuda_bytes": 16777216,
        "paths": {
            "independent_bf16_adapter": {
                "checkpoint_storage_dtype": "bfloat16",
                "base_load_dtype": "bfloat16",
                "adapter_storage_dtype": "float32",
                "adapter_runtime_dtype": "float32",
                "merge": False,
                "inference_parameter_dtypes": ["bfloat16", "float32"],
            },
            "fp32_safe_merged": {
                "checkpoint_storage_dtype": "bfloat16",
                "base_load_dtype": "float32",
                "adapter_storage_dtype": "float32",
                "adapter_runtime_dtype": "float32",
                "merge_dtype": "float32",
                "inference_dtype": "float32",
                "merge": True,
                "safe_merge": True,
                "adapter_names": ["default"],
            },
        },
        "generation": {
            "attn_implementation": "sdpa",
            "attention_class": "Qwen2Attention",
            "attention_dispatch": "ALL_ATTENTION_FUNCTIONS['sdpa']",
            "output_attentions": False,
            "do_sample": False,
            "max_new_tokens": 256,
            "use_cache": True,
            "repetition_penalty": 1.1,
            "model_eos_token_ids": [151645, 151643],
            "model_pad_token_id": 151643,
            "call_pad_token_id": 151645,
            "return_dict_in_generate": True,
            "output_scores": True,
            "output_logits": True,
            "tf32": False,
            "autocast": False,
            "device": "cuda:0",
        },
        "sdp_kernel_flags": {
            "flash_sdp_enabled": True,
            "math_sdp_enabled": True,
            "mem_efficient_sdp_enabled": True,
            "cudnn_sdp_enabled": True,
            "fp16_bf16_reduction_math_sdp_allowed": False,
        },
    }
    if gate.get("storage_audit") != expected_storage:
        raise GateError("Tool Router FP32 merge-drift storage audit drift")
    if gate.get("protocol") != expected_protocol:
        raise GateError("Tool Router FP32 merge-drift protocol drift")

    references = gate.get("frozen_references")
    remediation_runs = remediation.get("runs")
    if (
        not isinstance(references, dict)
        or set(references) != {"independent_bf16_adapter", "fp32_safe_merged"}
        or references.get("independent_bf16_adapter") != remediation.get("reference")
        or not isinstance(remediation_runs, list)
        or len(remediation_runs) != 2
        or references.get("fp32_safe_merged")
        != {
            "path": "fp32_safe_merged",
            "source_experiment_id": remediation.get("experiment_id"),
            "fresh_runs": 2,
            "token_count": remediation_runs[0].get("token_count"),
            "token_ids_sha256": remediation_runs[0].get("token_ids_sha256"),
            "output_sha256": remediation_runs[0].get("output_sha256"),
        }
    ):
        raise GateError("Tool Router FP32 merge-drift frozen references drift")

    runs = gate.get("runs")
    expected_run_keys = {
        "path",
        "fresh_load",
        "generated_token_ids",
        "token_count",
        "token_ids_sha256",
        "output_sha256",
        "precision_audit",
        "generation_trace",
        "path_protocol_passed",
        "peak_gpu_memory_bytes",
        "memory_allocated_before_load_bytes",
        "memory_allocated_after_release_bytes",
    }
    if (
        not isinstance(runs, list)
        or len(runs) != 2
        or any(not isinstance(run, dict) for run in runs)
        or any(set(run) != expected_run_keys for run in runs)
        or [run.get("path") for run in runs]
        != ["independent_bf16_adapter", "fp32_safe_merged"]
        or [run.get("fresh_load") for run in runs] != [1, 1]
    ):
        raise GateError("Tool Router FP32 merge-drift runs are invalid")
    for run in runs:
        path_name = run["path"]
        token_ids = run.get("generated_token_ids")
        reference = references[path_name]
        trace = run.get("generation_trace")
        if (
            not isinstance(token_ids, list)
            or len(token_ids) != 48
            or any(
                not isinstance(token_id, int) or isinstance(token_id, bool)
                for token_id in token_ids
            )
            or run.get("token_count") != len(token_ids)
            or run.get("token_ids_sha256") != token_ids_sha256(token_ids)
            or run.get("token_ids_sha256") != reference.get("token_ids_sha256")
            or run.get("output_sha256") != reference.get("output_sha256")
            or run.get("path_protocol_passed") is not True
            or not isinstance(run.get("peak_gpu_memory_bytes"), int)
            or not isinstance(run.get("memory_allocated_before_load_bytes"), int)
            or not isinstance(run.get("memory_allocated_after_release_bytes"), int)
            or run["memory_allocated_before_load_bytes"]
            > expected_protocol["max_residual_cuda_bytes"]
            or run["memory_allocated_after_release_bytes"]
            > expected_protocol["max_residual_cuda_bytes"]
            or not isinstance(trace, dict)
            or set(trace)
            != {
                "step_count",
                "vocabulary_size",
                "cache_returned",
                "scores",
                "raw_logits",
            }
            or trace.get("step_count") != len(token_ids)
            or trace.get("vocabulary_size") != 151936
            or trace.get("cache_returned") is not True
        ):
            raise GateError("Tool Router FP32 merge-drift run evidence drift")
        for trace_key, evidence_key in (
            ("scores", "selection_score_evidence"),
            ("raw_logits", "raw_logit_evidence"),
        ):
            summary = trace.get(trace_key)
            evidence = gate.get(evidence_key)
            expected_summary_keys = {
                "native_dtypes",
                "shape_per_step",
                "comparison_dtype",
                "all_finite",
                "trace_sha256",
                "divergent_step_index",
                "divergent_step_comparison_vector_sha256",
            }
            if (
                not isinstance(summary, dict)
                or set(summary) != expected_summary_keys
                or summary.get("native_dtypes") != ["float32"]
                or summary.get("shape_per_step") != [1, 151936]
                or summary.get("comparison_dtype") != "float32"
                or summary.get("all_finite") is not True
                or not _is_canonical_sha256(summary.get("trace_sha256"))
                or summary.get("divergent_step_index") != 45
                or not isinstance(evidence, dict)
                or summary.get("divergent_step_comparison_vector_sha256")
                != evidence.get("paths", {})
                .get(path_name, {})
                .get("comparison_vector_sha256")
            ):
                raise GateError("Tool Router FP32 merge-drift trace linkage drift")

    _validate_fp32_drift_precision(runs)
    reproduction = gate.get("reproduction")
    if reproduction != {
        "independent_bf16_token_identity": True,
        "independent_bf16_output_identity": True,
        "fp32_candidate_token_identity": True,
        "fp32_candidate_output_identity": True,
    }:
        raise GateError("Tool Router FP32 merge-drift reproduction drift")

    token_analysis = gate.get("token_analysis")
    recomputed = analyze_path_tokens(
        runs[0]["generated_token_ids"],
        runs[1]["generated_token_ids"],
    )
    if (
        not isinstance(token_analysis, dict)
        or set(token_analysis)
        != set(recomputed)
        | {
            "independent_token_text",
            "candidate_token_text",
        }
        or any(token_analysis.get(key) != value for key, value in recomputed.items())
        or token_analysis.get("first_divergent_token_index") != 45
        or token_analysis.get("independent_token_id") != 1866
        or token_analysis.get("candidate_token_id") != 3849
        or token_analysis.get("independent_token_text") != "true"
        or token_analysis.get("candidate_token_text") != "false"
    ):
        raise GateError("Tool Router FP32 merge-drift token analysis drift")

    _validate_fp32_step_evidence(
        gate,
        runs,
        evidence_key="selection_score_evidence",
        source="generated.scores",
        semantics="processed_prediction_scores_after_logits_processors",
        value_key="score",
        expected_values={
            "independent_bf16_adapter": [
                34.54545211791992,
                34.09090805053711,
                25.75,
                21.93181800842285,
                21.5,
            ],
            "fp32_safe_merged": [
                35.61100387573242,
                33.169429779052734,
                24.49706268310547,
                23.684528350830078,
                21.257160186767578,
            ],
        },
        expected_top_ids={
            "independent_bf16_adapter": [1866, 3849, 830, 895, 2641],
            "fp32_safe_merged": [3849, 1866, 830, 895, 2641],
        },
        expected_delta={
            "vocabulary_elements": 151936,
            "nonzero_elements": 151936,
            "max_abs_delta": 1.9437971115112305,
            "mean_abs_delta": 0.2275839000940323,
            "root_mean_square_delta": 0.29325070977211,
        },
    )
    _validate_fp32_step_evidence(
        gate,
        runs,
        evidence_key="raw_logit_evidence",
        source="generated.logits",
        semantics="unprocessed_lm_head_prediction_scores",
        value_key="raw_logit",
        expected_values={
            "independent_bf16_adapter": [38.0, 37.5, 25.75, 24.125, 21.5],
            "fp32_safe_merged": [
                39.17210388183594,
                36.48637390136719,
                26.052982330322266,
                24.49706268310547,
                21.257160186767578,
            ],
        },
        expected_top_ids={
            "independent_bf16_adapter": [1866, 3849, 830, 895, 2641],
            "fp32_safe_merged": [3849, 1866, 895, 830, 2641],
        },
        expected_delta={
            "vocabulary_elements": 151936,
            "nonzero_elements": 151936,
            "max_abs_delta": 1.9437971115112305,
            "mean_abs_delta": 0.22757971286773682,
            "root_mean_square_delta": 0.2932598292827606,
        },
    )

    expected_classification = (
        "deterministic_bf16_attached_vs_fp32_merged_raw_logit_boundary_flip"
    )
    analysis_gate = gate.get("analysis_gate")
    remediation_gate = gate.get("remediation_gate")
    acceptance = gate.get("acceptance")
    expected_acceptance = {
        "upstream_evidence_locked",
        "frozen_input_reproduced",
        "independent_bf16_reference_reproduced",
        "fp32_candidate_reproduced",
        "first_divergent_token_located",
        "exact_processed_scores_captured",
        "exact_raw_logits_captured",
        "generation_score_alignment_verified",
        "path_protocols_executed",
        "source_storage_dtypes_locked",
        "fresh_load_memory_isolated",
        "source_adapter_unchanged",
        "source_model_unchanged",
        "eval_digest_unchanged",
        "prompt_digest_unchanged",
    }
    constraints = {
        "failed_candidate_change": False,
        "locked_path_dtype_change": False,
        "locked_path_backend_change": False,
        "locked_path_decoding_change": False,
        "new_data": False,
        "training": False,
        "eval_answer_tuning": False,
        "runtime_integration": False,
        "full_eval_run": False,
        "merged_artifact_promotion": False,
    }
    next_action = gate.get("locked_next_action")
    if (
        gate.get("classification") != expected_classification
        or analysis_gate
        != {
            "frozen_paths_reproduced": True,
            "first_divergent_token_located": True,
            "exact_cached_generate_step_captured": True,
            "processed_score_argmax_matches_generated_token": True,
            "raw_logits_captured": True,
            "passed": True,
        }
        or remediation_gate
        != {
            "candidate_failure_reproduced": True,
            "independent_bf16_reference_identity": False,
            "passed": False,
        }
        or not isinstance(acceptance, dict)
        or set(acceptance) != expected_acceptance
        or not all(value is True for value in acceptance.values())
        or gate.get("peak_gpu_memory_bytes")
        != max(run["peak_gpu_memory_bytes"] for run in runs)
        or not isinstance(gate.get("elapsed_seconds"), (int, float))
        or isinstance(gate.get("elapsed_seconds"), bool)
        or gate["elapsed_seconds"] <= 0
        or gate.get("merged_artifact_saved") is not False
        or gate.get("merged_artifact_allowed") is not False
        or gate.get("constraints") != constraints
        or not isinstance(next_action, dict)
        or set(next_action) != {"gate_id", "action", "acceptance", "constraints"}
        or next_action.get("gate_id") != "FC-MVP-001-fp32-attached-merge-isolation-v1"
        or next_action.get("acceptance")
        != {
            "attached_fp32_repeat_stable": True,
            "fp32_candidate_reproduced": True,
            "same_dtype_exact_step_compared": True,
            "same_dtype_attached_vs_merged_effect_classified": True,
            "source_inputs_unchanged": True,
        }
        or next_action.get("constraints") != constraints
        or gate.get("runtime_eligible") is not False
        or gate.get("runtime_eligibility_reason") != expected_classification
        or gate.get("offline") is not True
    ):
        raise GateError("Tool Router FP32 merge-drift acceptance drift")
    return gate


def _validate_fp32_attached_merge_isolation(
    drift: dict[str, Any],
) -> dict[str, Any]:
    from fullcycle_bridge.tool_router import fixture_digest, load_fixture
    from fullcycle_bridge.tool_router_fp32_attached_merge_isolation import (
        analyze_attached_repeat_stability,
        analyze_same_dtype_tokens,
        classify_same_dtype_effect,
        select_comparison_step,
    )
    from fullcycle_bridge.tool_router_merge_remediation import token_ids_sha256
    from fullcycle_bridge.tool_router_sft import (
        canonical_config_sha256,
        directory_artifact_manifest,
        file_sha256,
    )

    gate = _load_json(TOOL_ROUTER_FP32_ATTACHED_MERGE_ISOLATION_PATH)
    _validate_finite_json(gate, "$")
    config = _load_json(ROOT / "configs" / "tool_router_lora_sft_v2.json")
    training = _load_json(ROOT / "baseline" / "fc-mvp-001-lora-sft-v2-training.json")
    stability = _load_json(TOOL_ROUTER_MERGE_STABILITY_PATH)
    adapter = ROOT / "baseline" / "adapters" / "fc-mvp-001-lora-sft-v2"
    evaluation = load_fixture(ROOT / config["data"]["eval_path"])
    expected_top_level = {
        "fp32_attached_merge_isolation_version",
        "experiment_id",
        "source_experiment_id",
        "drift_evidence_sha256",
        "remediation_evidence_sha256",
        "stability_evidence_sha256",
        "numerics_evidence_sha256",
        "training_lock_sha256",
        "config_sha256",
        "adapter_files",
        "model_weight_sha256",
        "prompt_sha256",
        "eval_digest",
        "example_id",
        "input_token_count",
        "input_token_ids_sha256",
        "storage_audit",
        "protocol",
        "frozen_fp32_merged_reference",
        "frozen_bf16_context",
        "runs",
        "attached_repeat_stability",
        "merged_candidate_reproduction",
        "same_dtype_token_analysis",
        "comparison_step",
        "selection_score_evidence",
        "raw_logit_evidence",
        "same_dtype_trace_identity",
        "classification",
        "causal_scope",
        "isolation_gate",
        "remediation_gate",
        "acceptance",
        "elapsed_seconds",
        "peak_gpu_memory_bytes",
        "merged_artifact_saved",
        "merged_artifact_allowed",
        "constraints",
        "locked_next_action",
        "runtime_eligible",
        "runtime_eligibility_reason",
        "offline",
    }
    if (
        set(gate) != expected_top_level
        or file_sha256(TOOL_ROUTER_FP32_ATTACHED_MERGE_ISOLATION_PATH)
        != "sha256:37d8d35bc3802a76bd7e0ab484f3b86e01b03852212ae9aaf3d9cec318fb5e26"
        or gate.get("fp32_attached_merge_isolation_version") != 1
        or gate.get("experiment_id") != "fc-mvp-001-fp32-attached-merge-isolation-v1"
        or gate.get("source_experiment_id") != config.get("experiment_id")
        or gate.get("drift_evidence_sha256")
        != file_sha256(TOOL_ROUTER_FP32_MERGE_DRIFT_PATH)
        or gate.get("remediation_evidence_sha256")
        != file_sha256(TOOL_ROUTER_MERGE_REMEDIATION_PATH)
        or gate.get("stability_evidence_sha256")
        != file_sha256(TOOL_ROUTER_MERGE_STABILITY_PATH)
        or gate.get("numerics_evidence_sha256")
        != file_sha256(TOOL_ROUTER_MERGE_NUMERICS_PATH)
        or gate.get("training_lock_sha256")
        != file_sha256(ROOT / "requirements" / "training.lock")
        or gate.get("config_sha256") != canonical_config_sha256(config)
        or gate.get("adapter_files") != directory_artifact_manifest(adapter)
        or gate.get("adapter_files") != training["final_adapter"]["files"]
        or gate.get("model_weight_sha256")
        != f"sha256:{config['model']['weight_sha256']}"
        or gate.get("prompt_sha256") != file_sha256(ROOT / config["prompt"]["path"])
        or gate.get("eval_digest") != fixture_digest(evaluation)
        or gate.get("example_id") != "eval-001"
        or gate.get("input_token_count") != 339
        or gate.get("input_token_count") != drift.get("input_token_count")
        or gate.get("input_token_ids_sha256")
        != "sha256:3bd24b9f36966889e543dda2aea25f5c0f29db40a8fccf1453d0657a06a4429f"
        or gate.get("input_token_ids_sha256") != drift.get("input_token_ids_sha256")
    ):
        raise GateError("Tool Router FP32 attached/merge source drift")

    expected_storage = {
        "base_checkpoint": {
            "tensors": 338,
            "elements": 1543714304,
            "dtype_tensors": {"bfloat16": 338},
            "dtype_elements": {"bfloat16": 1543714304},
        },
        "adapter": {
            "tensors": 224,
            "elements": 4358144,
            "dtype_tensors": {"float32": 224},
            "dtype_elements": {"float32": 4358144},
        },
    }
    expected_constraints = {
        "failed_candidate_change": False,
        "frozen_bf16_path_rerun": False,
        "locked_path_dtype_change": False,
        "locked_path_backend_change": False,
        "locked_path_decoding_change": False,
        "new_data": False,
        "training": False,
        "eval_answer_tuning": False,
        "runtime_integration": False,
        "full_eval_run": False,
        "merged_artifact_promotion": False,
    }
    expected_protocol = {
        "freshness_scope": "fresh_model_load_lifecycle_in_fixed_process",
        "run_plan": [
            {
                "run_id": "fp32_attached-r1",
                "path": "fp32_attached_adapter",
                "repeat": 1,
            },
            {
                "run_id": "fp32_attached-r2",
                "path": "fp32_attached_adapter",
                "repeat": 2,
            },
            {
                "run_id": "fp32_safe_merged-r1",
                "path": "fp32_safe_merged",
                "repeat": 1,
            },
        ],
        "fresh_loads_per_path": {
            "fp32_attached_adapter": 2,
            "fp32_safe_merged": 1,
        },
        "max_residual_cuda_bytes": 16777216,
        "paths": {
            "fp32_attached_adapter": {
                "checkpoint_storage_dtype": "bfloat16",
                "base_load_dtype": "float32",
                "adapter_storage_dtype": "float32",
                "adapter_runtime_dtype": "float32",
                "autocast_adapter_dtype": False,
                "merge": False,
                "inference_parameter_dtype": "float32",
            },
            "fp32_safe_merged": {
                "checkpoint_storage_dtype": "bfloat16",
                "base_load_dtype": "float32",
                "adapter_storage_dtype": "float32",
                "adapter_runtime_dtype": "float32",
                "autocast_adapter_dtype": False,
                "merge_dtype": "float32",
                "inference_parameter_dtype": "float32",
                "merge": True,
                "safe_merge": True,
                "adapter_names": ["default"],
            },
        },
        "generation": {
            "attn_implementation": "sdpa",
            "attention_class": "Qwen2Attention",
            "attention_dispatch": "ALL_ATTENTION_FUNCTIONS['sdpa']",
            "low_level_cuda_kernel_identity_claimed": False,
            "output_attentions": False,
            "do_sample": False,
            "max_new_tokens": 256,
            "use_cache": True,
            "repetition_penalty": 1.1,
            "model_eos_token_ids": [151645, 151643],
            "model_pad_token_id": 151643,
            "call_pad_token_id": 151645,
            "return_dict_in_generate": True,
            "output_scores": True,
            "output_logits": True,
            "generate_return_dtype_semantics": (
                "return_tensor_dtype_not_internal_compute_dtype"
            ),
            "tf32": False,
            "autocast": False,
            "device": "cuda:0",
        },
        "sdp_kernel_flags": {
            "flash_sdp_enabled": True,
            "math_sdp_enabled": True,
            "mem_efficient_sdp_enabled": True,
            "cudnn_sdp_enabled": True,
            "fp16_bf16_reduction_math_sdp_allowed": False,
        },
    }
    if gate.get("storage_audit") != expected_storage:
        raise GateError("Tool Router FP32 attached/merge storage audit drift")
    if gate.get("protocol") != expected_protocol:
        raise GateError("Tool Router FP32 attached/merge protocol drift")

    drift_runs = drift.get("runs")
    if not isinstance(drift_runs, list):
        raise GateError("Tool Router FP32 drift runs missing")
    drift_merged = [run for run in drift_runs if run.get("path") == "fp32_safe_merged"]
    if len(drift_merged) != 1:
        raise GateError("Tool Router FP32 drift merged reference missing")
    drift_merged_run = drift_merged[0]
    expected_merged_reference = {
        "path": "fp32_safe_merged",
        "source_experiment_id": drift["experiment_id"],
        "token_count": drift_merged_run["token_count"],
        "token_ids_sha256": drift_merged_run["token_ids_sha256"],
        "output_sha256": drift_merged_run["output_sha256"],
        "score_trace_sha256": drift_merged_run["generation_trace"]["scores"][
            "trace_sha256"
        ],
        "raw_logit_trace_sha256": drift_merged_run["generation_trace"]["raw_logits"][
            "trace_sha256"
        ],
        "comparison_step_index": 45,
        "comparison_score_vector_sha256": drift_merged_run["generation_trace"][
            "scores"
        ]["divergent_step_comparison_vector_sha256"],
        "comparison_raw_logit_vector_sha256": drift_merged_run["generation_trace"][
            "raw_logits"
        ]["divergent_step_comparison_vector_sha256"],
    }
    if gate.get("frozen_fp32_merged_reference") != expected_merged_reference:
        raise GateError("Tool Router FP32 merged reference drift")

    stability_runs = stability.get("runs")
    if not isinstance(stability_runs, list):
        raise GateError("Tool Router BF16 stability runs missing")
    expected_bf16_paths: dict[str, Any] = {}
    for source_path, target_path, boundary_id in (
        ("independent", "bf16_attached_adapter", 1866),
        ("merged", "bf16_safe_merged", 3849),
    ):
        matches = [run for run in stability_runs if run.get("path") == source_path]
        if len(matches) != 2:
            raise GateError("Tool Router BF16 context repeat drift")
        if any(
            matches[index].get(key) != matches[0].get(key)
            for index in (1,)
            for key in ("token_count", "token_ids_sha256", "output_sha256")
        ):
            raise GateError("Tool Router BF16 context identity drift")
        expected_bf16_paths[target_path] = {
            "token_count": matches[0]["token_count"],
            "token_ids_sha256": matches[0]["token_ids_sha256"],
            "output_sha256": matches[0]["output_sha256"],
            "boundary_token_id": boundary_id,
        }
    expected_bf16_context = {
        "context_only": True,
        "gpu_paths_rerun": False,
        "source_experiment_id": stability["experiment_id"],
        "first_divergent_token_index": 45,
        "paths": expected_bf16_paths,
    }
    if gate.get("frozen_bf16_context") != expected_bf16_context:
        raise GateError("Tool Router frozen BF16 context drift")

    runs = gate.get("runs")
    expected_run_keys = {
        "run_id",
        "path",
        "repeat",
        "fresh_load",
        "generated_token_ids",
        "token_count",
        "token_ids_sha256",
        "output_sha256",
        "precision_audit",
        "generation_trace",
        "path_protocol_passed",
        "peak_gpu_memory_bytes",
        "memory_allocated_before_load_bytes",
        "memory_allocated_after_release_bytes",
    }
    expected_plan = [
        ("fp32_attached-r1", "fp32_attached_adapter", 1),
        ("fp32_attached-r2", "fp32_attached_adapter", 2),
        ("fp32_safe_merged-r1", "fp32_safe_merged", 1),
    ]
    if (
        not isinstance(runs, list)
        or len(runs) != 3
        or any(not isinstance(run, dict) for run in runs)
        or any(set(run) != expected_run_keys for run in runs)
        or [(run.get("run_id"), run.get("path"), run.get("repeat")) for run in runs]
        != expected_plan
    ):
        raise GateError("Tool Router FP32 attached/merge runs invalid")
    expected_trace_hashes = {
        "fp32_attached-r1": (
            "sha256:e878f06653e43ebf6946a00396fbed7797eecc02dcf25501f0738169a932fdde",
            "sha256:61a891ab427bce3002c3367e2faefd854a11ecb62929d5b187b974a9c3b7f357",
            "sha256:47055d7f7614955154ce736de5fd79b8e1636aacb80e214377f7faa6e4767451",
            "sha256:14b7b48cfb9012388762d0d9925c0c19ea737b7459bcf637ea31f880e731654a",
        ),
        "fp32_attached-r2": (
            "sha256:e878f06653e43ebf6946a00396fbed7797eecc02dcf25501f0738169a932fdde",
            "sha256:61a891ab427bce3002c3367e2faefd854a11ecb62929d5b187b974a9c3b7f357",
            "sha256:47055d7f7614955154ce736de5fd79b8e1636aacb80e214377f7faa6e4767451",
            "sha256:14b7b48cfb9012388762d0d9925c0c19ea737b7459bcf637ea31f880e731654a",
        ),
        "fp32_safe_merged-r1": (
            expected_merged_reference["score_trace_sha256"],
            expected_merged_reference["raw_logit_trace_sha256"],
            expected_merged_reference["comparison_score_vector_sha256"],
            expected_merged_reference["comparison_raw_logit_vector_sha256"],
        ),
    }
    expected_token_digest = (
        "sha256:9dfd817e59df5c0278fdd9da20feb3664fade5d354040bbd5b3b4c650ca43dca"
    )
    expected_output_digest = (
        "sha256:b37939d2e8014afcc92b094d9c63715aa28d91f02504bf8b56186dd2dd5cc7ca"
    )
    for run in runs:
        token_ids = run.get("generated_token_ids")
        trace = run.get("generation_trace")
        if (
            run.get("fresh_load") is not True
            or not isinstance(token_ids, list)
            or len(token_ids) != 48
            or any(
                not isinstance(token_id, int) or isinstance(token_id, bool)
                for token_id in token_ids
            )
            or run.get("token_count") != len(token_ids)
            or run.get("token_ids_sha256") != token_ids_sha256(token_ids)
            or run.get("token_ids_sha256") != expected_token_digest
            or run.get("output_sha256") != expected_output_digest
            or run.get("path_protocol_passed") is not True
            or not isinstance(run.get("peak_gpu_memory_bytes"), int)
            or isinstance(run.get("peak_gpu_memory_bytes"), bool)
            or run["peak_gpu_memory_bytes"] < 0
            or not isinstance(run.get("memory_allocated_before_load_bytes"), int)
            or not isinstance(run.get("memory_allocated_after_release_bytes"), int)
            or run["memory_allocated_before_load_bytes"] < 0
            or run["memory_allocated_after_release_bytes"] < 0
            or run["memory_allocated_before_load_bytes"] > 16777216
            or run["memory_allocated_after_release_bytes"] > 16777216
            or not isinstance(trace, dict)
            or set(trace)
            != {
                "step_count",
                "vocabulary_size",
                "cache_returned",
                "scores",
                "raw_logits",
            }
            or trace.get("step_count") != len(token_ids)
            or trace.get("vocabulary_size") != 151936
            or trace.get("cache_returned") is not True
        ):
            raise GateError("Tool Router FP32 attached/merge run evidence drift")
        expected_hashes = expected_trace_hashes[run["run_id"]]
        for trace_key, expected_trace, expected_vector in (
            ("scores", expected_hashes[0], expected_hashes[2]),
            ("raw_logits", expected_hashes[1], expected_hashes[3]),
        ):
            summary = trace.get(trace_key)
            if (
                not isinstance(summary, dict)
                or set(summary)
                != {
                    "native_dtypes",
                    "shape_per_step",
                    "comparison_dtype",
                    "all_finite",
                    "trace_sha256",
                    "comparison_step_index",
                    "comparison_step_vector_sha256",
                }
                or summary.get("native_dtypes") != ["float32"]
                or summary.get("shape_per_step") != [1, 151936]
                or summary.get("comparison_dtype") != "float32"
                or summary.get("all_finite") is not True
                or summary.get("trace_sha256") != expected_trace
                or summary.get("comparison_step_index") != 45
                or summary.get("comparison_step_vector_sha256") != expected_vector
            ):
                raise GateError("Tool Router FP32 attached/merge trace linkage drift")

    _validate_fp32_isolation_precision(runs)
    attached = runs[:2]
    merged = runs[2]
    repeat = analyze_attached_repeat_stability(
        attached[0]["generated_token_ids"],
        attached[1]["generated_token_ids"],
        first_output_sha256=attached[0]["output_sha256"],
        second_output_sha256=attached[1]["output_sha256"],
        first_score_trace_sha256=attached[0]["generation_trace"]["scores"][
            "trace_sha256"
        ],
        second_score_trace_sha256=attached[1]["generation_trace"]["scores"][
            "trace_sha256"
        ],
        first_raw_logit_trace_sha256=attached[0]["generation_trace"]["raw_logits"][
            "trace_sha256"
        ],
        second_raw_logit_trace_sha256=attached[1]["generation_trace"]["raw_logits"][
            "trace_sha256"
        ],
        precision_audits_identical=(
            attached[0]["precision_audit"] == attached[1]["precision_audit"]
        ),
    )
    repeat["comparison_score_vector_identity"] = (
        attached[0]["generation_trace"]["scores"]["comparison_step_vector_sha256"]
        == attached[1]["generation_trace"]["scores"]["comparison_step_vector_sha256"]
    )
    repeat["comparison_raw_logit_vector_identity"] = (
        attached[0]["generation_trace"]["raw_logits"]["comparison_step_vector_sha256"]
        == attached[1]["generation_trace"]["raw_logits"][
            "comparison_step_vector_sha256"
        ]
    )
    repeat["passed"] = all(value for key, value in repeat.items() if key != "passed")
    if gate.get("attached_repeat_stability") != repeat or not repeat["passed"]:
        raise GateError("Tool Router attached FP32 repeat stability drift")

    reference = expected_merged_reference
    reproduction = {
        "token_identity": (
            merged["token_count"] == reference["token_count"]
            and merged["token_ids_sha256"] == reference["token_ids_sha256"]
        ),
        "output_identity": merged["output_sha256"] == reference["output_sha256"],
        "score_trace_identity": merged["generation_trace"]["scores"]["trace_sha256"]
        == reference["score_trace_sha256"],
        "raw_logit_trace_identity": merged["generation_trace"]["raw_logits"][
            "trace_sha256"
        ]
        == reference["raw_logit_trace_sha256"],
        "comparison_score_vector_identity": merged["generation_trace"]["scores"][
            "comparison_step_vector_sha256"
        ]
        == reference["comparison_score_vector_sha256"],
        "comparison_raw_logit_vector_identity": merged["generation_trace"][
            "raw_logits"
        ]["comparison_step_vector_sha256"]
        == reference["comparison_raw_logit_vector_sha256"],
    }
    reproduction["passed"] = all(reproduction.values())
    if gate.get("merged_candidate_reproduction") != reproduction:
        raise GateError("Tool Router FP32 merged reproduction drift")

    token_analysis = analyze_same_dtype_tokens(
        attached[0]["generated_token_ids"],
        merged["generated_token_ids"],
    )
    if gate.get("same_dtype_token_analysis") != {
        **token_analysis,
        "attached_token_text": None,
        "merged_token_text": None,
    }:
        raise GateError("Tool Router same-dtype token analysis drift")
    comparison_step = select_comparison_step(
        token_analysis,
        frozen_boundary_index=45,
    )
    if gate.get("comparison_step") != comparison_step:
        raise GateError("Tool Router same-dtype comparison step drift")

    _validate_fp32_isolation_step_evidence(
        gate,
        runs,
        evidence_key="selection_score_evidence",
        source="generated.scores",
        semantics="processed_prediction_scores_after_logits_processors",
        value_key="score",
        expected_values={
            "fp32_attached_adapter": [
                35.61114501953125,
                33.16929626464844,
                24.496919631958008,
                23.684675216674805,
                21.257125854492188,
            ],
            "fp32_safe_merged": [
                35.61100387573242,
                33.169429779052734,
                24.49706268310547,
                23.684528350830078,
                21.257160186767578,
            ],
        },
        expected_top_ids={
            "fp32_attached_adapter": [3849, 1866, 830, 895, 2641],
            "fp32_safe_merged": [3849, 1866, 830, 895, 2641],
        },
        expected_delta={
            "vocabulary_elements": 151936,
            "nonzero_elements": 150968,
            "max_abs_delta": 0.0001735687255859375,
            "mean_abs_delta": 2.052841409749817e-05,
            "root_mean_square_delta": 2.6467831048648804e-05,
        },
    )
    _validate_fp32_isolation_step_evidence(
        gate,
        runs,
        evidence_key="raw_logit_evidence",
        source="generated.logits",
        semantics="unprocessed_lm_head_prediction_scores",
        value_key="raw_logit",
        expected_values={
            "fp32_attached_adapter": [
                39.17226028442383,
                36.48622512817383,
                26.053144454956055,
                24.496919631958008,
                21.257125854492188,
            ],
            "fp32_safe_merged": [
                39.17210388183594,
                36.48637390136719,
                26.052982330322266,
                24.49706268310547,
                21.257160186767578,
            ],
        },
        expected_top_ids={
            "fp32_attached_adapter": [3849, 1866, 895, 830, 2641],
            "fp32_safe_merged": [3849, 1866, 895, 830, 2641],
        },
        expected_delta={
            "vocabulary_elements": 151936,
            "nonzero_elements": 150968,
            "max_abs_delta": 0.0001735687255859375,
            "mean_abs_delta": 2.052839772659354e-05,
            "root_mean_square_delta": 2.6469620934221894e-05,
        },
    )

    score = gate["selection_score_evidence"]
    raw = gate["raw_logit_evidence"]
    trace_identity = {
        "token_identity": token_analysis["cross_path_identical"],
        "score_trace_identity": attached[0]["generation_trace"]["scores"][
            "trace_sha256"
        ]
        == merged["generation_trace"]["scores"]["trace_sha256"],
        "raw_logit_trace_identity": attached[0]["generation_trace"]["raw_logits"][
            "trace_sha256"
        ]
        == merged["generation_trace"]["raw_logits"]["trace_sha256"],
        "comparison_score_vector_identity": score["paths"]["fp32_attached_adapter"][
            "comparison_vector_sha256"
        ]
        == score["paths"]["fp32_safe_merged"]["comparison_vector_sha256"],
        "comparison_raw_logit_vector_identity": raw["paths"]["fp32_attached_adapter"][
            "comparison_vector_sha256"
        ]
        == raw["paths"]["fp32_safe_merged"]["comparison_vector_sha256"],
    }
    if gate.get("same_dtype_trace_identity") != trace_identity:
        raise GateError("Tool Router same-dtype trace identity drift")
    classification = classify_same_dtype_effect(
        token_analysis,
        attached_repeat_stable=repeat["passed"],
        merged_candidate_reproduced=reproduction["passed"],
        attached_emitted_token_id=score["paths"]["fp32_attached_adapter"][
            "emitted_token_id"
        ],
        merged_emitted_token_id=score["paths"]["fp32_safe_merged"]["emitted_token_id"],
        attached_score_top_token_id=score["paths"]["fp32_attached_adapter"][
            "top_token_ids"
        ][0],
        merged_score_top_token_id=score["paths"]["fp32_safe_merged"]["top_token_ids"][
            0
        ],
        attached_raw_logit_top_token_id=raw["paths"]["fp32_attached_adapter"][
            "top_token_ids"
        ][0],
        merged_raw_logit_top_token_id=raw["paths"]["fp32_safe_merged"]["top_token_ids"][
            0
        ],
        full_score_traces_identical=trace_identity["score_trace_identity"],
        full_raw_logit_traces_identical=trace_identity["raw_logit_trace_identity"],
        comparison_score_vectors_identical=trace_identity[
            "comparison_score_vector_identity"
        ],
        comparison_raw_logit_vectors_identical=trace_identity[
            "comparison_raw_logit_vector_identity"
        ],
    )
    expected_classification = (
        "deterministic_fp32_attached_vs_merged_numerical_drift_without_token_drift"
    )
    expected_causal_scope = {
        "isolated_variable": ("attached_adapter_vs_materialized_safe_merge_execution"),
        "controlled": [
            "base_checkpoint_values",
            "base_and_adapter_runtime_dtype_float32",
            "adapter_weights",
            "eval_001_rendered_input",
            "greedy_decoding",
            "high_level_transformers_sdpa_dispatch",
            "fresh_model_load_lifecycle",
        ],
        "supports": (
            "classification of the observed same-dtype FP32 execution-form effect"
        ),
        "does_not_support": [
            "peft_merge_implementation_bug_claim",
            "low_level_cuda_kernel_identity_or_root_cause",
            "full_eval_generalization",
            "merged_artifact_promotion",
            "runtime_eligibility",
        ],
    }
    expected_isolation_gate = {
        "attached_fp32_repeat_stable": repeat["passed"],
        "fp32_merged_candidate_reproduced": reproduction["passed"],
        "same_dtype_exact_cached_step_compared": True,
        "processed_score_argmax_matches_generated_token": True,
        "raw_logits_captured": True,
        "same_dtype_effect_classified": True,
        "passed": True,
    }
    expected_acceptance_keys = {
        "upstream_evidence_locked",
        "frozen_input_reproduced",
        "attached_fp32_repeat_stable",
        "fp32_candidate_reproduced",
        "same_dtype_exact_step_compared",
        "same_dtype_attached_vs_merged_effect_classified",
        "generation_score_alignment_verified",
        "path_protocols_executed",
        "source_storage_dtypes_locked",
        "fresh_load_memory_isolated",
        "source_adapter_unchanged",
        "source_model_unchanged",
        "eval_digest_unchanged",
        "prompt_digest_unchanged",
        "frozen_bf16_context_only",
    }
    expected_next_action = {
        "gate_id": "FC-MVP-001-fp32-attached-merge-numerics-v1",
        "action": (
            "at frozen comparison step index 45, locate the first module numerical "
            "divergence between repeat-stable FP32 attached LoRA execution and the "
            "unchanged materialized safe-merged execution, without claiming a "
            "same-dtype token boundary"
        ),
        "acceptance": {
            "fp32_paths_reproduced": True,
            "comparison_step_reproduced": True,
            "first_divergent_module_located": True,
            "operation_order_boundary_quantified": True,
            "source_inputs_unchanged": True,
        },
        "constraints": expected_constraints,
    }
    elapsed = gate.get("elapsed_seconds")
    peak = gate.get("peak_gpu_memory_bytes")
    acceptance = gate.get("acceptance")
    if (
        classification != expected_classification
        or gate.get("classification") != classification
        or gate.get("causal_scope") != expected_causal_scope
        or gate.get("isolation_gate") != expected_isolation_gate
        or gate.get("remediation_gate")
        != {
            "source_gate_passed": False,
            "new_remediation_tested": False,
            "passed": False,
        }
        or not isinstance(acceptance, dict)
        or set(acceptance) != expected_acceptance_keys
        or not all(value is True for value in acceptance.values())
        or not isinstance(elapsed, (int, float))
        or isinstance(elapsed, bool)
        or not math.isfinite(elapsed)
        or elapsed <= 0
        or not isinstance(peak, int)
        or isinstance(peak, bool)
        or peak < 0
        or peak != max(run["peak_gpu_memory_bytes"] for run in runs)
        or gate.get("merged_artifact_saved") is not False
        or gate.get("merged_artifact_allowed") is not False
        or gate.get("constraints") != expected_constraints
        or gate.get("locked_next_action") != expected_next_action
        or gate.get("runtime_eligible") is not False
        or gate.get("runtime_eligibility_reason") != expected_classification
        or gate.get("offline") is not True
    ):
        raise GateError("Tool Router FP32 attached/merge acceptance drift")
    return gate


def _validate_fp32_attached_merge_numerics(
    isolation: dict[str, Any],
) -> dict[str, Any]:
    from fullcycle_bridge.tool_router import fixture_digest, load_fixture
    from fullcycle_bridge.tool_router_fp32_attached_merge_numerics_archive import (
        validate_frozen_numerics_evidence,
    )
    from fullcycle_bridge.tool_router_sft import (
        canonical_config_sha256,
        directory_artifact_manifest,
        file_sha256,
    )

    gate = _load_json(TOOL_ROUTER_FP32_ATTACHED_MERGE_NUMERICS_PATH)
    _validate_finite_json(gate, "$")
    if (
        not TOOL_ROUTER_FP32_ATTACHED_MERGE_NUMERICS_TENSORS_PATH.is_file()
        or TOOL_ROUTER_FP32_ATTACHED_MERGE_NUMERICS_TENSORS_PATH.is_symlink()
    ):
        raise GateError("Tool Router FP32 numerics tensor archive is unsafe")
    payload = TOOL_ROUTER_FP32_ATTACHED_MERGE_NUMERICS_TENSORS_PATH.read_bytes()
    raw_validation = validate_frozen_numerics_evidence(gate, payload)
    if (
        raw_validation.get("frozen_gate_valid") is not True
        or raw_validation.get("record_count") != 138
        or raw_validation.get("comparisons_recomputed") != 35
        or raw_validation.get("weight_elements_recomputed") != 2_359_296
        or raw_validation.get("bias_elements_recomputed") != 1_536
    ):
        raise GateError("Tool Router FP32 numerics raw validation drift")

    config = _load_json(ROOT / "configs" / "tool_router_lora_sft_v2.json")
    training = _load_json(ROOT / "baseline" / "fc-mvp-001-lora-sft-v2-training.json")
    adapter = ROOT / "baseline" / "adapters" / "fc-mvp-001-lora-sft-v2"
    evaluation = load_fixture(ROOT / config["data"]["eval_path"])
    expected_lineage = {
        "isolation_evidence_sha256": file_sha256(
            TOOL_ROUTER_FP32_ATTACHED_MERGE_ISOLATION_PATH
        ),
        "drift_evidence_sha256": file_sha256(TOOL_ROUTER_FP32_MERGE_DRIFT_PATH),
        "remediation_evidence_sha256": file_sha256(TOOL_ROUTER_MERGE_REMEDIATION_PATH),
        "stability_evidence_sha256": file_sha256(TOOL_ROUTER_MERGE_STABILITY_PATH),
        "bf16_numerics_context_sha256": file_sha256(TOOL_ROUTER_MERGE_NUMERICS_PATH),
    }
    if (
        file_sha256(TOOL_ROUTER_FP32_ATTACHED_MERGE_NUMERICS_PATH)
        != "sha256:cb1c2b4255ebc5c38aa2ff66436804cca55dc088e39ca8fe8959654488e41a91"
        or gate.get("source_lineage") != expected_lineage
        or gate.get("source_experiment_id") != isolation.get("experiment_id")
        or gate.get("training_lock_sha256")
        != file_sha256(ROOT / "requirements" / "training.lock")
        or gate.get("config_sha256") != canonical_config_sha256(config)
        or gate.get("adapter_files") != directory_artifact_manifest(adapter)
        or gate.get("adapter_files") != training["final_adapter"]["files"]
        or gate.get("model_weight_sha256")
        != f"sha256:{config['model']['weight_sha256']}"
        or gate.get("prompt_sha256") != file_sha256(ROOT / config["prompt"]["path"])
        or gate.get("eval_digest") != fixture_digest(evaluation)
        or gate.get("eval_digest") != isolation.get("eval_digest")
        or gate.get("input_token_count") != isolation.get("input_token_count")
        or gate.get("input_token_ids_sha256") != isolation.get("input_token_ids_sha256")
        or gate.get("storage_audit") != isolation.get("storage_audit")
        or gate.get("frozen_bf16_context") != isolation.get("frozen_bf16_context")
        or isolation.get("locked_next_action", {}).get("gate_id")
        != "FC-MVP-001-fp32-attached-merge-numerics-v1"
    ):
        raise GateError("Tool Router FP32 numerics source lineage drift")
    expected_environment = {
        **config["environment"],
        "base_and_adapter_runtime_dtype": "float32",
        "autocast": False,
        "tf32": False,
    }
    if gate.get("environment") != expected_environment:
        raise GateError("Tool Router FP32 numerics environment drift")

    expected_references: dict[str, Any] = {}
    for path in ("fp32_attached_adapter", "fp32_safe_merged"):
        matches = [run for run in isolation["runs"] if run.get("path") == path]
        if not matches:
            raise GateError("Tool Router FP32 numerics source run missing")
        run = matches[0]
        expected_references[path] = {
            "token_count": run["token_count"],
            "token_ids_sha256": run["token_ids_sha256"],
            "output_sha256": run["output_sha256"],
            "score_trace_sha256": run["generation_trace"]["scores"]["trace_sha256"],
            "raw_logit_trace_sha256": run["generation_trace"]["raw_logits"][
                "trace_sha256"
            ],
            "comparison_step_index": 45,
            "comparison_score_vector_sha256": run["generation_trace"]["scores"][
                "comparison_step_vector_sha256"
            ],
            "comparison_raw_logit_vector_sha256": run["generation_trace"]["raw_logits"][
                "comparison_step_vector_sha256"
            ],
        }
    if gate.get("frozen_path_references") != expected_references:
        raise GateError("Tool Router FP32 numerics frozen reference drift")
    runs = gate["runs"]
    if (
        gate.get("peak_gpu_memory_bytes")
        != max(run["peak_gpu_memory_bytes"] for run in runs)
        or not isinstance(gate.get("elapsed_seconds"), (int, float))
        or isinstance(gate.get("elapsed_seconds"), bool)
        or not math.isfinite(gate["elapsed_seconds"])
        or gate["elapsed_seconds"] <= 0
    ):
        raise GateError("Tool Router FP32 numerics resource evidence drift")
    return gate


def _validate_attached_dtype_isolation(
    fp32_numerics: dict[str, Any],
) -> dict[str, Any]:
    from fullcycle_bridge.tool_router import fixture_digest, load_fixture
    from fullcycle_bridge.tool_router_attached_dtype_isolation_evidence import (
        validate_attached_dtype_isolation_evidence,
    )
    from fullcycle_bridge.tool_router_sft import (
        canonical_config_sha256,
        directory_artifact_manifest,
        file_sha256,
    )

    if (
        not TOOL_ROUTER_ATTACHED_DTYPE_ISOLATION_PATH.is_file()
        or TOOL_ROUTER_ATTACHED_DTYPE_ISOLATION_PATH.is_symlink()
    ):
        raise GateError("Tool Router attached dtype isolation evidence is unsafe")
    gate = _load_json(TOOL_ROUTER_ATTACHED_DTYPE_ISOLATION_PATH)
    _validate_finite_json(gate, "$")

    config = _load_json(ROOT / "configs" / "tool_router_lora_sft_v2.json")
    training_path = ROOT / "baseline" / "fc-mvp-001-lora-sft-v2-training.json"
    training = _load_json(training_path)
    adapter = ROOT / "baseline" / "adapters" / "fc-mvp-001-lora-sft-v2"
    evaluation = load_fixture(ROOT / config["data"]["eval_path"])
    expected_lineage = {
        "stability_evidence_sha256": file_sha256(TOOL_ROUTER_MERGE_STABILITY_PATH),
        "drift_evidence_sha256": file_sha256(TOOL_ROUTER_FP32_MERGE_DRIFT_PATH),
        "isolation_evidence_sha256": file_sha256(
            TOOL_ROUTER_FP32_ATTACHED_MERGE_ISOLATION_PATH
        ),
        "fp32_numerics_evidence_sha256": file_sha256(
            TOOL_ROUTER_FP32_ATTACHED_MERGE_NUMERICS_PATH
        ),
        "training_evidence_sha256": file_sha256(training_path),
    }
    adapter_files = directory_artifact_manifest(adapter)
    validation = validate_attached_dtype_isolation_evidence(
        gate,
        expected_source_lineage=expected_lineage,
        expected_adapter_files=adapter_files,
        expected_environment=config["environment"],
    )
    expected_validation = {
        "frozen_gate_valid": True,
        "runs_validated": 4,
        "token_digests_recomputed": 6,
        "comparison_step_manifests_validated": 8,
        "classification": (
            "deterministic_bf16_attached_vs_fp32_attached_raw_logit_boundary_flip"
        ),
        "delta_statistics_scope": "probe_derived_summary_algebra_only",
    }
    if validation != expected_validation:
        raise GateError("Tool Router attached dtype raw validation drift")

    if (
        file_sha256(TOOL_ROUTER_ATTACHED_DTYPE_ISOLATION_PATH)
        != "sha256:7eaedee1d6f7ea27b2fc083f82bc8df620612e84095f4a66a2ba7dfec791ce31"
        or gate.get("source_lineage") != expected_lineage
        or gate.get("source_experiment_id") != training.get("experiment_id")
        or gate.get("training_lock_sha256")
        != file_sha256(ROOT / "requirements" / "training.lock")
        or gate.get("config_sha256") != canonical_config_sha256(config)
        or gate.get("adapter_files") != adapter_files
        or gate.get("adapter_files") != training["final_adapter"]["files"]
        or gate.get("model_weight_sha256")
        != f"sha256:{config['model']['weight_sha256']}"
        or gate.get("prompt_sha256") != file_sha256(ROOT / config["prompt"]["path"])
        or gate.get("eval_digest") != fixture_digest(evaluation)
        or gate.get("eval_digest") != fp32_numerics.get("eval_digest")
        or gate.get("input_token_count") != fp32_numerics.get("input_token_count")
        or gate.get("input_token_ids_sha256")
        != fp32_numerics.get("input_token_ids_sha256")
        or gate.get("storage_audit") != fp32_numerics.get("storage_audit")
        or fp32_numerics.get("locked_next_action", {}).get("gate_id")
        != "FC-MVP-001-attached-dtype-isolation-v1"
    ):
        raise GateError("Tool Router attached dtype source lineage drift")
    return gate


def _validate_attached_dtype_numerics(
    attached_dtype_isolation: dict[str, Any],
) -> dict[str, Any]:
    from fullcycle_bridge.tool_router import fixture_digest, load_fixture
    from fullcycle_bridge.tool_router_attached_dtype_numerics_evidence import (
        validate_attached_dtype_numerics_evidence,
    )
    from fullcycle_bridge.tool_router_sft import (
        canonical_config_sha256,
        directory_artifact_manifest,
        file_sha256,
    )

    if (
        not TOOL_ROUTER_ATTACHED_DTYPE_NUMERICS_PATH.is_file()
        or TOOL_ROUTER_ATTACHED_DTYPE_NUMERICS_PATH.is_symlink()
    ):
        raise GateError("Tool Router attached dtype numerics evidence is unsafe")
    gate = _load_json(TOOL_ROUTER_ATTACHED_DTYPE_NUMERICS_PATH)
    _validate_finite_json(gate, "$")

    config = _load_json(ROOT / "configs" / "tool_router_lora_sft_v2.json")
    adapter = ROOT / "baseline" / "adapters" / "fc-mvp-001-lora-sft-v2"
    evaluation = load_fixture(ROOT / config["data"]["eval_path"])
    adapter_files = directory_artifact_manifest(adapter)
    expected_lineage = dict(attached_dtype_isolation["source_lineage"])
    expected_lineage["attached_dtype_isolation_evidence_sha256"] = file_sha256(
        TOOL_ROUTER_ATTACHED_DTYPE_ISOLATION_PATH
    )
    validation = validate_attached_dtype_numerics_evidence(
        gate,
        source_isolation=attached_dtype_isolation,
        expected_source_lineage=expected_lineage,
        expected_adapter_files=adapter_files,
        expected_environment=attached_dtype_isolation["environment"],
    )
    expected_validation = {
        "frozen_gate_valid": True,
        "runs_validated": 4,
        "capture_records_validated": 160,
        "capture_manifests_validated": 4,
        "module_comparisons_validated": 40,
        "first_unequal_module": "model.layers.0.input_layernorm",
        "classification": (
            "deterministic_attached_bf16_vs_fp32_registered_module_"
            "output_drift_reaching_lm_head"
        ),
        "delta_statistics_scope": (
            "probe_derived_summary_algebra_and_frozen_manifest_only"
        ),
    }
    if validation != expected_validation:
        raise GateError("Tool Router attached dtype numerics raw validation drift")
    if (
        file_sha256(TOOL_ROUTER_ATTACHED_DTYPE_NUMERICS_PATH)
        != "sha256:de5b048a5d254f61ab3bef1ff23f1484b07808c86a1679bc0de4ee58e8c8d7c5"
        or gate.get("source_lineage") != expected_lineage
        or gate.get("source_experiment_id")
        != attached_dtype_isolation.get("source_experiment_id")
        or gate.get("source_gate_experiment_id")
        != attached_dtype_isolation.get("experiment_id")
        or gate.get("training_lock_sha256")
        != attached_dtype_isolation.get("training_lock_sha256")
        or gate.get("config_sha256") != canonical_config_sha256(config)
        or gate.get("adapter_files") != adapter_files
        or gate.get("model_weight_sha256")
        != f"sha256:{config['model']['weight_sha256']}"
        or gate.get("prompt_sha256") != file_sha256(ROOT / config["prompt"]["path"])
        or gate.get("eval_digest") != fixture_digest(evaluation)
        or gate.get("eval_digest") != attached_dtype_isolation.get("eval_digest")
        or gate.get("input_token_count")
        != attached_dtype_isolation.get("input_token_count")
        or gate.get("input_token_ids_sha256")
        != attached_dtype_isolation.get("input_token_ids_sha256")
        or gate.get("storage_audit") != attached_dtype_isolation.get("storage_audit")
        or attached_dtype_isolation.get("locked_next_action", {}).get("gate_id")
        != "FC-MVP-001-attached-dtype-numerics-v1"
    ):
        raise GateError("Tool Router attached dtype numerics source lineage drift")
    return gate


def _validate_attached_dtype_boundary_control(
    attached_dtype_numerics: dict[str, Any],
) -> dict[str, Any]:
    from fullcycle_bridge.tool_router_attached_dtype_boundary_control_evidence import (
        validate_attached_dtype_boundary_control_evidence,
    )
    from fullcycle_bridge.tool_router_sft import (
        directory_artifact_manifest,
        file_sha256,
    )

    if (
        not TOOL_ROUTER_ATTACHED_DTYPE_BOUNDARY_CONTROL_PATH.is_file()
        or TOOL_ROUTER_ATTACHED_DTYPE_BOUNDARY_CONTROL_PATH.is_symlink()
    ):
        raise GateError(
            "Tool Router attached dtype boundary-control evidence is unsafe"
        )
    gate = _load_json(TOOL_ROUTER_ATTACHED_DTYPE_BOUNDARY_CONTROL_PATH)
    _validate_finite_json(gate, "$")

    adapter = ROOT / "baseline" / "adapters" / "fc-mvp-001-lora-sft-v2"
    adapter_files = directory_artifact_manifest(adapter)
    source_numerics_sha256 = file_sha256(TOOL_ROUTER_ATTACHED_DTYPE_NUMERICS_PATH)
    expected_lineage = dict(attached_dtype_numerics["source_lineage"])
    expected_lineage["attached_dtype_numerics_evidence_sha256"] = source_numerics_sha256
    validation = validate_attached_dtype_boundary_control_evidence(
        gate,
        source_numerics=attached_dtype_numerics,
        expected_source_numerics_sha256=source_numerics_sha256,
        expected_source_lineage=expected_lineage,
        expected_adapter_files=adapter_files,
        expected_environment=attached_dtype_numerics["environment"],
    )
    expected_validation = {
        "frozen_gate_valid": True,
        "actual_runs_validated": 4,
        "control_runs_validated": 4,
        "capture_records_validated": 28,
        "actual_comparisons_validated": 4,
        "control_comparisons_validated": 3,
        "protocol_completed": True,
        "current_forward_boundary_sufficiency_observed": True,
        "classification": (
            "deterministic_same_values_rmsnorm_dtype_replay_"
            "reproduces_actual_boundary_drift"
        ),
    }
    if validation != expected_validation:
        raise GateError(
            "Tool Router attached dtype boundary-control raw validation drift"
        )
    if (
        file_sha256(TOOL_ROUTER_ATTACHED_DTYPE_BOUNDARY_CONTROL_PATH)
        != "sha256:fdf4ab44b1b60853f0d5de9f231ce77557152b47c9ce52156c31c9bbca484bc7"
        or gate.get("source_lineage") != expected_lineage
        or gate.get("source_experiment_id")
        != attached_dtype_numerics.get("source_experiment_id")
        or gate.get("source_gate_experiment_id")
        != attached_dtype_numerics.get("experiment_id")
        or gate.get("training_lock_sha256")
        != attached_dtype_numerics.get("training_lock_sha256")
        or gate.get("config_sha256") != attached_dtype_numerics.get("config_sha256")
        or gate.get("adapter_files") != adapter_files
        or gate.get("model_weight_sha256")
        != attached_dtype_numerics.get("model_weight_sha256")
        or gate.get("prompt_sha256") != attached_dtype_numerics.get("prompt_sha256")
        or gate.get("eval_digest") != attached_dtype_numerics.get("eval_digest")
        or gate.get("input_token_count")
        != attached_dtype_numerics.get("input_token_count")
        or gate.get("input_token_ids_sha256")
        != attached_dtype_numerics.get("input_token_ids_sha256")
        or gate.get("storage_audit") != attached_dtype_numerics.get("storage_audit")
        or gate.get("environment") != attached_dtype_numerics.get("environment")
        or attached_dtype_numerics.get("locked_next_action", {}).get("gate_id")
        != "FC-MVP-001-attached-dtype-boundary-control-v1"
    ):
        raise GateError(
            "Tool Router attached dtype boundary-control source lineage drift"
        )
    return gate


def _validate_fp32_attached_remediation_eval(
    attached_dtype_boundary_control: dict[str, Any],
) -> dict[str, Any]:
    import inspect

    from fullcycle_bridge.tool_router import fixture_digest, load_fixture
    from fullcycle_bridge.tool_router_decision_compilation import compile_decision
    from fullcycle_bridge.tool_router_fp32_attached_remediation_eval_evidence import (
        validate_fp32_attached_remediation_eval_evidence,
    )
    from fullcycle_bridge.tool_router_sft import (
        canonical_config_sha256,
        directory_artifact_manifest,
        file_sha256,
    )

    paths = (
        TOOL_ROUTER_FP32_ATTACHED_REMEDIATION_PREREGISTRATION_PATH,
        TOOL_ROUTER_FP32_ATTACHED_REMEDIATION_PREDICTIONS_PATH,
        TOOL_ROUTER_FP32_ATTACHED_REMEDIATION_EVAL_PATH,
    )
    if any(not path.is_file() or path.is_symlink() for path in paths):
        raise GateError("Tool Router FP32 attached remediation evidence is unsafe")

    preregistration = _load_json(paths[0])
    predictions = _load_json(paths[1])
    gate = _load_json(paths[2])
    for name, value in (
        ("preregistration", preregistration),
        ("predictions", predictions),
        ("gate", gate),
    ):
        _validate_finite_json(value, f"$.{name}")

    config_path = ROOT / "configs" / "tool_router_lora_sft_v2.json"
    config = _load_json(config_path)
    training_lock_path = ROOT / "requirements" / "training.lock"
    training_path = ROOT / "baseline" / "fc-mvp-001-lora-sft-v2-training.json"
    lifecycle_path = TOOL_ROUTER_SFT_V2_BASELINE_PATH
    compiler_path = (
        ROOT / "src" / "fullcycle_bridge" / "tool_router_decision_compilation.py"
    )
    scorer_path = ROOT / "src" / "fullcycle_bridge" / "tool_router_model_eval.py"
    contract_path = (
        ROOT
        / "src"
        / "fullcycle_bridge"
        / "tool_router_fp32_attached_remediation_eval.py"
    )
    runner_path = (
        ROOT / "scripts" / "probe_tool_router_fp32_attached_remediation_eval.py"
    )
    raw_predictions_path = (
        ROOT / "baseline" / "tool-router-qwen2.5-1.5b-lora-sft-v2-predictions.json"
    )
    raw_report_path = (
        ROOT / "baseline" / "tool-router-qwen2.5-1.5b-lora-sft-v2-report.json"
    )
    preregistration_sha256 = file_sha256(paths[0])
    prediction_sha256 = file_sha256(paths[1])
    compiler_symbol_sha256 = (
        "sha256:"
        + hashlib.sha256(
            inspect.getsource(compile_decision).encode("utf-8")
        ).hexdigest()
    )
    expected_source_lineage = {
        "base_config_canonical_sha256": canonical_config_sha256(config),
        "base_config_sha256": file_sha256(config_path),
        "bf16_compiled_predictions_sha256": file_sha256(
            TOOL_ROUTER_COMPILED_PREDICTIONS_PATH
        ),
        "bf16_compiled_report_sha256": file_sha256(TOOL_ROUTER_COMPILED_REPORT_PATH),
        "bf16_raw_predictions_sha256": file_sha256(raw_predictions_path),
        "bf16_raw_report_sha256": file_sha256(raw_report_path),
        "boundary_control_evidence_sha256": file_sha256(
            TOOL_ROUTER_ATTACHED_DTYPE_BOUNDARY_CONTROL_PATH
        ),
        "comparison_contract_source_sha256": file_sha256(contract_path),
        "decision_compilation_gate_sha256": file_sha256(
            TOOL_ROUTER_DECISION_COMPILATION_PATH
        ),
        "decision_compiler_source_sha256": file_sha256(compiler_path),
        "decision_compiler_source_symbol_source_sha256": (compiler_symbol_sha256),
        "lifecycle_evidence_sha256": file_sha256(lifecycle_path),
        "preregistration_sha256": preregistration_sha256,
        "runner_source_sha256": file_sha256(runner_path),
        "scorer_source_sha256": file_sha256(scorer_path),
        "training_evidence_sha256": file_sha256(training_path),
        "training_lock_sha256": file_sha256(training_lock_path),
    }
    evaluation = load_fixture(ROOT / config["data"]["eval_path"])
    if fixture_digest(evaluation) != config["data"]["eval_digest"]:
        raise GateError("Tool Router FP32 attached remediation eval drift")
    adapter = ROOT / "baseline" / "adapters" / "fc-mvp-001-lora-sft-v2"
    validation = validate_fp32_attached_remediation_eval_evidence(
        preregistration,
        predictions,
        gate,
        evaluation=evaluation,
        reference_compiled_report=_load_json(TOOL_ROUTER_COMPILED_REPORT_PATH),
        source_boundary_control=attached_dtype_boundary_control,
        expected_source_lineage=expected_source_lineage,
        expected_model=config["model"],
        expected_tokenizer=config["tokenizer"],
        expected_environment=config["environment"],
        expected_adapter_files=directory_artifact_manifest(adapter),
        expected_preregistration_sha256=preregistration_sha256,
        expected_prediction_artifact_sha256=prediction_sha256,
    )
    expected_validation = {
        "frozen_gate_valid": True,
        "candidate_count": 1,
        "run_count": 1,
        "evaluation_records": 20,
        "raw_outputs_validated": 20,
        "compiled_outputs_validated": 20,
        "classification": (
            "fp32_attached_full_eval_improves_quality_without_safety_or_"
            "resource_regression"
        ),
        "remediation_passed": True,
        "runtime_eligible": False,
    }
    if validation != expected_validation:
        raise GateError("Tool Router FP32 attached remediation validation drift")
    if (
        preregistration_sha256
        != "sha256:5e7b0665f97f5cee760637236f80039c4e621ae0f24915c0ac749d885a683c8b"
        or prediction_sha256
        != "sha256:382071f0689ce4ca41329d689f76fc4c4b06faa68769fb80c99181015e678115"
        or file_sha256(paths[2])
        != "sha256:2dd17f6b1098490034f825d163f48f26eb4093d02f115424eb814cb2c925ad8e"
        or attached_dtype_boundary_control.get("locked_next_action", {}).get("gate_id")
        != "FC-MVP-001-fp32-attached-remediation-eval-v1"
    ):
        raise GateError("Tool Router FP32 attached remediation lineage drift")
    return gate


def _validate_fp32_attached_artifact_eligibility(
    fp32_attached_remediation_eval: dict[str, Any],
) -> dict[str, Any]:
    from fullcycle_bridge.tool_router_fp32_attached_artifact_eligibility import (
        validate_fp32_attached_artifact_eligibility_review,
    )
    from scripts.review_tool_router_fp32_attached_artifact_eligibility import (
        load_review_inputs,
    )

    review_path = TOOL_ROUTER_FP32_ATTACHED_ARTIFACT_ELIGIBILITY_REVIEW_PATH
    if not review_path.is_file() or review_path.is_symlink():
        raise GateError("Tool Router FP32 attached artifact review is unsafe")
    review_payload = review_path.read_bytes()
    review_sha256 = "sha256:" + hashlib.sha256(review_payload).hexdigest()
    if (
        review_sha256
        != "sha256:81977f318c6bcfed8d3844575dc245d4b94c2636a2359165f9aa5553c9b006f8"
    ):
        raise GateError("Tool Router FP32 attached artifact review hash drift")

    review = _load_json_payload(review_payload, review_path)
    expected_source_hashes = review.get("source_artifacts")
    if not isinstance(expected_source_hashes, dict):
        raise GateError("Tool Router FP32 attached artifact source roots are invalid")
    inputs = load_review_inputs()
    if (
        inputs["remediation_gate"] != fp32_attached_remediation_eval
        or fp32_attached_remediation_eval.get("locked_next_action", {}).get("gate_id")
        != "FC-MVP-001-fp32-attached-artifact-eligibility-review-v1"
    ):
        raise GateError("Tool Router FP32 attached artifact upstream drift")

    validation = validate_fp32_attached_artifact_eligibility_review(
        review,
        **inputs,
        expected_source_hashes=expected_source_hashes,
    )
    expected_validation = {
        "frozen_review_valid": True,
        "upstream_evaluation_favorable": True,
        "repository_local_evidence_usable": True,
        "offline_artifact_eligible": False,
        "portable_package_eligible": False,
        "classification": (
            "fp32_attached_fixed_compiler_favorable_eval_but_offline_artifact_"
            "package_incomplete"
        ),
        "blocking_finding_count": 6,
        "next_gate": "FC-MVP-001-fp32-attached-offline-package-manifest-v1",
        "runtime_eligible": False,
    }
    if validation != expected_validation:
        raise GateError("Tool Router FP32 attached artifact validation drift")
    if (
        review.get("report_digest")
        != "sha256:285d5e5e25dfd16de5adc6cb760fe54588af68d8580308b54ccfaf612d51636b"
        or review.get("runtime_eligibility_reason")
        != (
            "fp32_attached_offline_package_incomplete_and_serving_or_runtime_"
            "readiness_not_established"
        )
    ):
        raise GateError("Tool Router FP32 attached artifact claim drift")
    return review


def _validate_fp32_attached_offline_package_manifest(
    fp32_attached_artifact_eligibility: dict[str, Any],
) -> dict[str, Any]:
    from fullcycle_bridge.tool_router_fp32_attached_offline_package_manifest import (
        validate_and_resolve_fp32_attached_offline_package,
    )
    from scripts.build_tool_router_fp32_attached_offline_package_manifest import (
        DEFAULT_ADAPTER_DIR,
        DEFAULT_BASE_MODEL_DIR,
        load_repository_manifest_inputs,
    )

    manifest_path = TOOL_ROUTER_FP32_ATTACHED_OFFLINE_PACKAGE_MANIFEST_PATH
    manifest_payload = _read_regular_file_once(
        manifest_path, "Tool Router FP32 attached offline package manifest"
    )
    manifest_sha256 = "sha256:" + hashlib.sha256(manifest_payload).hexdigest()
    if (
        len(manifest_payload) != 17_487
        or manifest_sha256 != TOOL_ROUTER_FP32_ATTACHED_OFFLINE_PACKAGE_MANIFEST_SHA256
    ):
        raise GateError("Tool Router FP32 attached offline package manifest drift")

    inputs = load_repository_manifest_inputs()
    if (
        inputs["upstream_review"] != fp32_attached_artifact_eligibility
        or fp32_attached_artifact_eligibility.get("locked_next_action", {}).get(
            "gate_id"
        )
        != "FC-MVP-001-fp32-attached-offline-package-manifest-v1"
    ):
        raise GateError("Tool Router FP32 attached offline package upstream drift")

    combined = validate_and_resolve_fp32_attached_offline_package(
        manifest_payload,
        TOOL_ROUTER_FP32_ATTACHED_OFFLINE_PACKAGE_MANIFEST_SHA256,
        inputs["upstream_review"],
        inputs["remediation_preregistration"],
        inputs["sft_config"],
        inputs["adapter_config"],
        source_hashes=inputs["source_hashes"],
        source_payloads=inputs["source_payloads"],
        expected_source_hashes=(
            TOOL_ROUTER_FP32_ATTACHED_OFFLINE_PACKAGE_SOURCE_HASHES
        ),
        base_model_root=DEFAULT_BASE_MODEL_DIR,
        adapter_root=DEFAULT_ADAPTER_DIR,
        repository_root=ROOT,
    )
    expected_validation = {
        "frozen_manifest_valid": True,
        "manifest_file_sha256": (
            TOOL_ROUTER_FP32_ATTACHED_OFFLINE_PACKAGE_MANIFEST_SHA256
        ),
        "metadata_complete": True,
        "offline_package_identity_complete": True,
        "attached_package_identity_bound": True,
        "prior_package_blocker_count_resolved": 6,
        "eligible_for_clean_location_reproducibility_test": True,
        "remote_revision_origin_attested": False,
        "behavioral_reproducibility_established": False,
        "offline_artifact_eligible": False,
        "portable_package_eligible": False,
        "preferred_offline_candidate": False,
        "serving_readiness_established": False,
        "artifact_promotion_allowed": False,
        "merged_artifact_allowed": False,
        "classification": "fp32_attached_metadata_only_composite_manifest_complete",
        "remaining_blocking_findings": [
            "behavioral_reproducibility_unverified",
            "clean_location_resolution_unverified",
            "remote_revision_origin_unverified",
        ],
        "remaining_blocking_finding_count": 3,
        "next_gate": ("FC-MVP-001-fp32-attached-offline-package-reproducibility-v1"),
        "runtime_eligible": False,
    }
    if combined.get("validation") != expected_validation:
        raise GateError("Tool Router FP32 attached offline package validation drift")

    resolution = combined.get("resolution")
    if not isinstance(resolution, dict):
        raise GateError("Tool Router FP32 attached offline package resolution missing")
    groups = resolution.get("groups")
    if not isinstance(groups, list) or len(groups) != 3:
        raise GateError("Tool Router FP32 attached offline package groups drift")
    groups_by_role = {
        group.get("root_role"): group for group in groups if isinstance(group, dict)
    }
    if set(groups_by_role) != {"base_model_and_tokenizer", "adapter", "repository"}:
        raise GateError("Tool Router FP32 attached offline package group roles drift")
    base_group = groups_by_role["base_model_and_tokenizer"]
    adapter_group = groups_by_role["adapter"]
    repository_group = groups_by_role["repository"]
    if (
        adapter_group.get("resolved") is not True
        or adapter_group.get("expected_files") != 3
        or adapter_group.get("matched_files") != 3
        or adapter_group.get("issues") != []
        or repository_group.get("resolved") is not True
        or repository_group.get("expected_files") != 15
        or repository_group.get("matched_files") != 15
        or repository_group.get("issues") != []
        or base_group.get("expected_files") != 9
        or not isinstance(base_group.get("resolved"), bool)
    ):
        raise GateError(
            "Tool Router FP32 attached offline package root resolution drift"
        )
    base_resolved = base_group["resolved"]
    if base_resolved:
        if base_group.get("matched_files") != 9 or base_group.get("issues") != []:
            raise GateError("Tool Router FP32 attached local component match drift")
    elif not base_group.get("issues"):
        raise GateError("Tool Router FP32 attached unresolved root lacks evidence")
    if (
        resolution.get("resolution_version") != 1
        or resolution.get("package_id")
        != "fc-mvp-001-fp32-attached-factorized-lora-package-v1"
        or resolution.get("manifest_file_sha256")
        != TOOL_ROUTER_FP32_ATTACHED_OFFLINE_PACKAGE_MANIFEST_SHA256
        or resolution.get("caller_supplied_roots") is not True
        or resolution.get("manifest_machine_paths_used") is not False
        or resolution.get("adapter_local_base_path_used") is not False
        or resolution.get("resolved") is not base_resolved
        or resolution.get("eligible_for_clean_location_reproducibility_test")
        is not base_resolved
        or resolution.get("offline_artifact_eligible") is not False
        or resolution.get("runtime_eligible") is not False
        or resolution.get("failure_mode")
        != (None if base_resolved else "component_resolution_failed_closed")
    ):
        raise GateError("Tool Router FP32 attached offline package decision drift")
    return combined


def _validate_fp32_attached_offline_package_reproducibility(
    fp32_attached_offline_package: dict[str, Any],
) -> dict[str, Any]:
    from fullcycle_bridge.tool_router_fp32_attached_offline_package_reproducibility import (
        load_manifest_source_bundle,
        validate_reproducibility_evidence,
    )
    from scripts.build_tool_router_fp32_attached_offline_package_manifest import (
        DEFAULT_ADAPTER_DIR,
    )

    manifest_validation = fp32_attached_offline_package.get("validation")
    if (
        not isinstance(manifest_validation, dict)
        or manifest_validation.get("frozen_manifest_valid") is not True
        or manifest_validation.get("next_gate")
        != "FC-MVP-001-fp32-attached-offline-package-reproducibility-v1"
        or manifest_validation.get("runtime_eligible") is not False
    ):
        raise GateError(
            "Tool Router FP32 attached reproducibility upstream manifest drift"
        )

    preregistration_payload = _read_regular_file_once(
        TOOL_ROUTER_FP32_ATTACHED_OFFLINE_PACKAGE_REPRODUCIBILITY_PREREGISTRATION_PATH,
        "Tool Router FP32 attached reproducibility preregistration",
    )
    replay_payload = _read_regular_file_once(
        TOOL_ROUTER_FP32_ATTACHED_OFFLINE_PACKAGE_REPRODUCIBILITY_PREDICTIONS_PATH,
        "Tool Router FP32 attached reproducibility replay",
    )
    evidence_payload = _read_regular_file_once(
        TOOL_ROUTER_FP32_ATTACHED_OFFLINE_PACKAGE_REPRODUCIBILITY_EVIDENCE_PATH,
        "Tool Router FP32 attached reproducibility evidence",
    )
    manifest_payload = _read_regular_file_once(
        TOOL_ROUTER_FP32_ATTACHED_OFFLINE_PACKAGE_MANIFEST_PATH,
        "Tool Router FP32 attached offline package manifest",
    )
    reference_predictions_payload = _read_regular_file_once(
        TOOL_ROUTER_FP32_ATTACHED_REMEDIATION_PREDICTIONS_PATH,
        "Tool Router FP32 attached remediation predictions",
    )
    reference_evidence_payload = _read_regular_file_once(
        TOOL_ROUTER_FP32_ATTACHED_REMEDIATION_EVAL_PATH,
        "Tool Router FP32 attached remediation evidence",
    )
    evaluation_payload = _read_regular_file_once(
        ROOT / "fixtures" / "tool_router_v1" / "eval.json",
        "Tool Router frozen evaluation",
    )
    validation = validate_reproducibility_evidence(
        preregistration_payload,
        replay_payload,
        evidence_payload,
        expected_preregistration_sha256=(
            TOOL_ROUTER_FP32_ATTACHED_OFFLINE_PACKAGE_REPRODUCIBILITY_PREREGISTRATION_SHA256
        ),
        expected_replay_artifact_sha256=(
            TOOL_ROUTER_FP32_ATTACHED_OFFLINE_PACKAGE_REPRODUCIBILITY_PREDICTIONS_SHA256
        ),
        expected_evidence_sha256=(
            TOOL_ROUTER_FP32_ATTACHED_OFFLINE_PACKAGE_REPRODUCIBILITY_EVIDENCE_SHA256
        ),
        expected_protocol_freeze_commit=(
            TOOL_ROUTER_FP32_ATTACHED_OFFLINE_PACKAGE_REPRODUCIBILITY_FREEZE_COMMIT
        ),
        replay_artifact_path=(
            TOOL_ROUTER_FP32_ATTACHED_OFFLINE_PACKAGE_REPRODUCIBILITY_PREDICTIONS_PATH.name
        ),
        manifest_payload=manifest_payload,
        reference_predictions_payload=reference_predictions_payload,
        reference_evidence_payload=reference_evidence_payload,
        evaluation_payload=evaluation_payload,
        manifest_sources=load_manifest_source_bundle(
            repository_root=ROOT,
            adapter_root=DEFAULT_ADAPTER_DIR,
        ),
    )
    expected_validation = {
        "frozen_gate_valid": True,
        "classification": (
            "fp32_attached_same_environment_clean_location_behavior_exactly_"
            "reproduced"
        ),
        "formal_gate_passed": True,
        "clean_location_resolution_established": True,
        "behavioral_reproducibility_established": True,
        "remaining_blocking_findings": ["remote_revision_origin_unverified"],
        "next_gate": (
            "FC-MVP-001-fp32-attached-remote-revision-origin-attestation-v1"
        ),
        "runtime_eligible": False,
    }
    if validation != expected_validation:
        raise GateError("Tool Router FP32 attached reproducibility validation drift")

    evidence = _load_json_payload(
        evidence_payload,
        TOOL_ROUTER_FP32_ATTACHED_OFFLINE_PACKAGE_REPRODUCIBILITY_EVIDENCE_PATH,
    )
    if (
        evidence.get("formal_gate_passed") is not True
        or evidence.get("runtime_eligible") is not False
        or evidence.get("remaining_blocking_findings")
        != ["remote_revision_origin_unverified"]
    ):
        raise GateError("Tool Router FP32 attached reproducibility claim drift")
    return evidence


def _validate_fp32_attached_remote_origin(
    reproducibility_evidence: dict[str, Any],
) -> dict[str, Any]:
    from fullcycle_bridge.tool_router_fp32_attached_remote_revision_origin_attestation import (
        PROTOCOL_SOURCE_PATHS,
        validate_origin_attestation_evidence,
    )

    prior_derived = reproducibility_evidence.get("derived_claims")
    if (
        not isinstance(prior_derived, dict)
        or reproducibility_evidence.get("formal_gate_passed") is not True
        or reproducibility_evidence.get("classification")
        != (
            "fp32_attached_same_environment_clean_location_behavior_exactly_"
            "reproduced"
        )
        or reproducibility_evidence.get("remaining_blocking_findings")
        != ["remote_revision_origin_unverified"]
        or prior_derived.get("remote_revision_origin_attested") is not False
        or reproducibility_evidence.get("runtime_eligible") is not False
    ):
        raise GateError("Tool Router FP32 attached remote-origin upstream drift")

    preregistration_payload = _read_regular_file_once(
        TOOL_ROUTER_FP32_ATTACHED_REMOTE_ORIGIN_PREREGISTRATION_PATH,
        "Tool Router FP32 attached remote-origin preregistration",
    )
    evidence_payload = _read_regular_file_once(
        TOOL_ROUTER_FP32_ATTACHED_REMOTE_ORIGIN_EVIDENCE_PATH,
        "Tool Router FP32 attached remote-origin evidence",
    )
    manifest_payload = _read_regular_file_once(
        TOOL_ROUTER_FP32_ATTACHED_OFFLINE_PACKAGE_MANIFEST_PATH,
        "Tool Router FP32 attached offline package manifest",
    )
    reproducibility_payload = _read_regular_file_once(
        TOOL_ROUTER_FP32_ATTACHED_OFFLINE_PACKAGE_REPRODUCIBILITY_EVIDENCE_PATH,
        "Tool Router FP32 attached reproducibility evidence",
    )
    protocol_source_payloads = {
        name: _read_regular_file_once(
            ROOT / relative,
            f"Tool Router FP32 attached remote-origin {name}",
        )
        for name, relative in PROTOCOL_SOURCE_PATHS.items()
    }
    validation = validate_origin_attestation_evidence(
        preregistration_payload,
        evidence_payload,
        expected_preregistration_sha256=(
            TOOL_ROUTER_FP32_ATTACHED_REMOTE_ORIGIN_PREREGISTRATION_SHA256
        ),
        expected_evidence_sha256=(
            TOOL_ROUTER_FP32_ATTACHED_REMOTE_ORIGIN_EVIDENCE_SHA256
        ),
        expected_protocol_freeze_commit=(
            TOOL_ROUTER_FP32_ATTACHED_REMOTE_ORIGIN_FREEZE_COMMIT
        ),
        manifest_payload=manifest_payload,
        reproducibility_evidence_payload=reproducibility_payload,
        protocol_source_payloads=protocol_source_payloads,
    )
    expected_validation = {
        "frozen_gate_valid": True,
        "classification": (
            "fp32_attached_github_and_huggingface_hosted_revision_origins_attested"
        ),
        "formal_gate_passed": True,
        "remote_revision_origin_attested": True,
        "remaining_blocking_findings": [],
        "next_gate": (
            "FC-MVP-001-fp32-attached-offline-artifact-eligibility-"
            "reassessment-v1"
        ),
        "offline_artifact_eligible": False,
        "portable_package_eligible": False,
        "preferred_offline_candidate": False,
        "runtime_eligible": False,
    }
    if validation != expected_validation:
        raise GateError("Tool Router FP32 attached remote-origin validation drift")

    evidence = _load_json_payload(
        evidence_payload,
        TOOL_ROUTER_FP32_ATTACHED_REMOTE_ORIGIN_EVIDENCE_PATH,
    )
    derived = evidence.get("derived_claims")
    collection = evidence.get("collection")
    if (
        not isinstance(derived, dict)
        or not isinstance(collection, dict)
        or evidence.get("formal_gate_passed") is not True
        or evidence.get("remaining_blocking_findings") != []
        or derived.get("remote_revision_origin_attested") is not True
        or derived.get("author_identity_or_signature_attested") is not False
        or derived.get("supply_chain_signature_attested") is not False
        or derived.get("historical_transparency_log_attested") is not False
        or derived.get("offline_artifact_eligible") is not False
        or derived.get("portable_package_eligible") is not False
        or derived.get("preferred_offline_candidate") is not False
        or derived.get("serving_readiness_established") is not False
        or derived.get("artifact_promotion_allowed") is not False
        or derived.get("merged_artifact_allowed") is not False
        or derived.get("runtime_eligible") is not False
        or collection.get("fixed_https_requests") != 5
        or collection.get("automatic_request_retries") != 0
        or collection.get("model_or_adapter_lfs_downloaded") is not False
        or collection.get("large_lfs_payload_bytes_read") != 0
        or collection.get("model_loaded") is not False
        or collection.get("generation_calls") != 0
        or collection.get("package_bytes_written") is not False
        or collection.get("lfs_signed_url_or_query_stored") is not False
        or evidence.get("runtime_eligible") is not False
    ):
        raise GateError("Tool Router FP32 attached remote-origin claim drift")
    return evidence


def _validate_fp32_attached_offline_artifact_reassessment(
    remote_origin_evidence: dict[str, Any],
) -> dict[str, Any]:
    from fullcycle_bridge.tool_router_fp32_attached_offline_artifact_eligibility_reassessment import (
        validate_reassessment_evidence,
    )
    from scripts.reassess_tool_router_fp32_attached_offline_artifact_eligibility import (
        compute_upstream_validations,
        load_upstream_payloads,
        protocol_source_payloads,
    )

    remote_derived = remote_origin_evidence.get("derived_claims")
    if (
        not isinstance(remote_derived, dict)
        or remote_origin_evidence.get("formal_gate_passed") is not True
        or remote_origin_evidence.get("classification")
        != (
            "fp32_attached_github_and_huggingface_hosted_revision_origins_"
            "attested"
        )
        or remote_origin_evidence.get("remaining_blocking_findings") != []
        or remote_derived.get("remote_revision_origin_attested") is not True
        or remote_derived.get("offline_artifact_eligible") is not False
        or remote_origin_evidence.get("runtime_eligible") is not False
    ):
        raise GateError(
            "Tool Router FP32 attached offline-artifact reassessment upstream drift"
        )

    preregistration_payload = _read_regular_file_once(
        TOOL_ROUTER_FP32_ATTACHED_OFFLINE_ARTIFACT_REASSESSMENT_PREREGISTRATION_PATH,
        "Tool Router FP32 attached offline-artifact reassessment preregistration",
    )
    evidence_payload = _read_regular_file_once(
        TOOL_ROUTER_FP32_ATTACHED_OFFLINE_ARTIFACT_REASSESSMENT_EVIDENCE_PATH,
        "Tool Router FP32 attached offline-artifact reassessment evidence",
    )
    upstream_payloads = load_upstream_payloads()
    upstream_validations = compute_upstream_validations(upstream_payloads)
    validation = validate_reassessment_evidence(
        preregistration_payload,
        evidence_payload,
        expected_preregistration_sha256=(
            TOOL_ROUTER_FP32_ATTACHED_OFFLINE_ARTIFACT_REASSESSMENT_PREREGISTRATION_SHA256
        ),
        expected_evidence_sha256=(
            TOOL_ROUTER_FP32_ATTACHED_OFFLINE_ARTIFACT_REASSESSMENT_EVIDENCE_SHA256
        ),
        expected_protocol_freeze_commit=(
            TOOL_ROUTER_FP32_ATTACHED_OFFLINE_ARTIFACT_REASSESSMENT_FREEZE_COMMIT
        ),
        upstream_payloads=upstream_payloads,
        upstream_validations=upstream_validations,
        protocol_source_payloads=protocol_source_payloads(),
    )
    expected_validation = {
        "frozen_gate_valid": True,
        "classification": (
            "fp32_attached_fixed_compiler_favorable_eval_offline_artifact_"
            "package_eligible"
        ),
        "formal_gate_passed": True,
        "offline_artifact_eligible": True,
        "portable_package_eligible": False,
        "preferred_offline_candidate": False,
        "prior_package_blocker_count_resolved": 6,
        "remaining_blocking_findings": [],
        "next_gate": (
            "FC-MVP-001-fp32-attached-preferred-offline-candidate-decision-v1"
        ),
        "runtime_eligible": False,
    }
    if validation != expected_validation:
        raise GateError(
            "Tool Router FP32 attached offline-artifact reassessment validation drift"
        )

    evidence = _load_json_payload(
        evidence_payload,
        TOOL_ROUTER_FP32_ATTACHED_OFFLINE_ARTIFACT_REASSESSMENT_EVIDENCE_PATH,
    )
    derived = evidence.get("derived_claims")
    claims = evidence.get("claims")
    gates = evidence.get("gates")
    if (
        not isinstance(derived, dict)
        or not isinstance(claims, dict)
        or not isinstance(gates, dict)
        or len(gates) != 9
        or any(value is not True for value in gates.values())
        or evidence.get("formal_gate_passed") is not True
        or evidence.get("remaining_blocking_findings") != []
        or len(evidence.get("resolved_prior_package_blockers", [])) != 6
        or derived.get("offline_artifact_eligible") is not True
        or derived.get("portable_package_eligible") is not False
        or derived.get("cross_machine_reproducibility_established") is not False
        or derived.get("preferred_offline_candidate") is not False
        or derived.get("serving_readiness_established") is not False
        or derived.get("artifact_promotion_allowed") is not False
        or derived.get("merged_artifact_allowed") is not False
        or derived.get("runtime_eligible") is not False
        or claims.get("metadata_only_reassessment") is not True
        or claims.get("upstream_validators_recomputed") is not True
        or claims.get("new_model_execution") is not False
        or claims.get("network_used") is not False
        or evidence.get("model_artifact_saved") is not False
        or evidence.get("tensor_payload_saved") is not False
        or evidence.get("runtime_eligible") is not False
    ):
        raise GateError(
            "Tool Router FP32 attached offline-artifact reassessment claim drift"
        )
    return evidence


def _validate_fp32_attached_preferred_candidate(
    reassessment_evidence: dict[str, Any],
) -> dict[str, Any]:
    from fullcycle_bridge.tool_router_fp32_attached_preferred_offline_candidate_decision import (
        validate_decision_evidence,
    )
    from scripts.decide_tool_router_fp32_attached_preferred_offline_candidate import (
        load_decision_upstreams,
        protocol_source_payloads,
    )

    reassessment_derived = reassessment_evidence.get("derived_claims")
    if (
        not isinstance(reassessment_derived, dict)
        or reassessment_evidence.get("formal_gate_passed") is not True
        or reassessment_evidence.get("classification")
        != (
            "fp32_attached_fixed_compiler_favorable_eval_offline_artifact_"
            "package_eligible"
        )
        or reassessment_evidence.get("remaining_blocking_findings") != []
        or reassessment_derived.get("offline_artifact_eligible") is not True
        or reassessment_derived.get("preferred_offline_candidate") is not False
        or reassessment_derived.get("portable_package_eligible") is not False
        or reassessment_evidence.get("runtime_eligible") is not False
    ):
        raise GateError(
            "Tool Router FP32 attached preferred-candidate upstream drift"
        )

    preregistration_payload = _read_regular_file_once(
        TOOL_ROUTER_FP32_ATTACHED_PREFERRED_CANDIDATE_PREREGISTRATION_PATH,
        "Tool Router FP32 attached preferred-candidate preregistration",
    )
    evidence_payload = _read_regular_file_once(
        TOOL_ROUTER_FP32_ATTACHED_PREFERRED_CANDIDATE_EVIDENCE_PATH,
        "Tool Router FP32 attached preferred-candidate evidence",
    )
    upstream_payloads, upstream_validations = load_decision_upstreams()
    validation = validate_decision_evidence(
        preregistration_payload,
        evidence_payload,
        expected_preregistration_sha256=(
            TOOL_ROUTER_FP32_ATTACHED_PREFERRED_CANDIDATE_PREREGISTRATION_SHA256
        ),
        expected_evidence_sha256=(
            TOOL_ROUTER_FP32_ATTACHED_PREFERRED_CANDIDATE_EVIDENCE_SHA256
        ),
        expected_protocol_freeze_commit=(
            TOOL_ROUTER_FP32_ATTACHED_PREFERRED_CANDIDATE_FREEZE_COMMIT
        ),
        upstream_payloads=upstream_payloads,
        upstream_validations=upstream_validations,
        protocol_source_payloads=protocol_source_payloads(),
    )
    expected_validation = {
        "frozen_gate_valid": True,
        "classification": (
            "fp32_attached_preferred_offline_candidate_under_fixed_compiler_"
            "attached_execution_and_registered_resource_caps"
        ),
        "formal_gate_passed": True,
        "offline_artifact_eligible": True,
        "preferred_offline_candidate": True,
        "portable_package_eligible": False,
        "remaining_blocking_findings": [],
        "downstream_open_findings": [
            "cross_machine_reproducibility_unestablished",
            "portable_package_eligibility_unestablished",
        ],
        "next_gate": (
            "FC-MVP-001-fp32-attached-portable-package-qualification-v1"
        ),
        "runtime_eligible": False,
    }
    if validation != expected_validation:
        raise GateError(
            "Tool Router FP32 attached preferred-candidate validation drift"
        )

    evidence = _load_json_payload(
        evidence_payload,
        TOOL_ROUTER_FP32_ATTACHED_PREFERRED_CANDIDATE_EVIDENCE_PATH,
    )
    derived = evidence.get("derived_claims")
    claims = evidence.get("claims")
    gates = evidence.get("gates")
    comparison = evidence.get("comparison")
    if (
        not isinstance(derived, dict)
        or not isinstance(claims, dict)
        or not isinstance(gates, dict)
        or not isinstance(comparison, dict)
        or len(gates) != 12
        or any(value is not True for value in gates.values())
        or evidence.get("formal_gate_passed") is not True
        or evidence.get("remaining_blocking_findings") != []
        or evidence.get("downstream_open_findings")
        != [
            "cross_machine_reproducibility_unestablished",
            "portable_package_eligibility_unestablished",
        ]
        or derived.get("offline_artifact_eligible") is not True
        or derived.get("preferred_offline_candidate") is not True
        or derived.get("portable_package_eligible") is not False
        or derived.get("cross_machine_reproducibility_established") is not False
        or derived.get("serving_readiness_established") is not False
        or derived.get("artifact_promotion_allowed") is not False
        or derived.get("merged_artifact_allowed") is not False
        or derived.get("runtime_eligible") is not False
        or comparison.get("execution_form") != "attached_factorized_lora"
        or comparison.get("portable_package_eligible") is not False
        or comparison.get("cross_machine_reproducibility_established") is not False
        or claims.get("metadata_only_decision") is not True
        or claims.get("upstream_validators_recomputed") is not True
        or claims.get("new_model_execution") is not False
        or claims.get("network_used") is not False
        or claims.get("artifact_promotion_allowed") is not False
        or evidence.get("model_artifact_saved") is not False
        or evidence.get("tensor_payload_saved") is not False
        or evidence.get("runtime_eligible") is not False
    ):
        raise GateError(
            "Tool Router FP32 attached preferred-candidate claim drift"
        )
    return evidence


def _validate_fp32_isolation_precision(runs: list[dict[str, Any]]) -> None:
    expected_generation = {
        "score_dtypes": ["float32"],
        "all_scores_float32": True,
        "raw_logit_dtypes": ["float32"],
        "all_raw_logits_float32": True,
        "dtype_semantics": "transformers_generate_return_tensor_dtype",
        "autocast_enabled": False,
        "training": False,
    }
    expected_pre = {
        "base_parameters": _expected_cuda_inventory("float32", 1543714304, 338),
        "adapter_parameters": _expected_cuda_inventory("float32", 4358144, 224),
        "floating_buffers": _expected_cuda_inventory("float32", 64, 1),
        "lora_target_modules": 112,
        "lora_parameter_tensors": 224,
        "adapter_parameters_finite": True,
        "active_adapters": ["default"],
        "is_peft_model": True,
        "input_output_embeddings_tied": True,
        "attn_implementation": "sdpa",
        "attention_class": "Qwen2Attention",
        "output_attentions": False,
        "hf_device_map": None,
    }
    expected_attached = {
        **expected_pre,
        "lora_dropout": {"modules": 112, "training_modules": 0},
        "generation": expected_generation,
    }
    if any(run.get("precision_audit") != expected_attached for run in runs[:2]):
        raise GateError("Tool Router attached FP32 precision audit drift")
    expected_post = {
        "parameters": _expected_cuda_inventory("float32", 1543714304, 338),
        "floating_buffers": _expected_cuda_inventory("float32", 64, 1),
        "lora_target_modules": 0,
        "lora_parameter_tensors": 0,
        "is_peft_model": False,
        "input_output_embeddings_tied": True,
        "attn_implementation": "sdpa",
        "attention_class": "Qwen2Attention",
        "output_attentions": False,
        "hf_device_map": None,
    }
    expected_merged = {
        "pre_merge": expected_pre,
        "post_merge": expected_post,
        "lora_dropout": {"modules": 0, "training_modules": 0},
        "generation": expected_generation,
    }
    if runs[2].get("precision_audit") != expected_merged:
        raise GateError("Tool Router merged FP32 precision audit drift")


def _validate_fp32_isolation_step_evidence(
    gate: dict[str, Any],
    runs: list[dict[str, Any]],
    *,
    evidence_key: str,
    source: str,
    semantics: str,
    value_key: str,
    expected_values: dict[str, list[float]],
    expected_top_ids: dict[str, list[int]],
    expected_delta: dict[str, Any],
) -> None:
    evidence = gate.get(evidence_key)
    if (
        not isinstance(evidence, dict)
        or set(evidence)
        != {
            "step_index",
            "comparison_basis",
            "shared_generated_prefix_tokens_before_step",
            "source",
            "semantics",
            "comparison_dtype",
            "top_k",
            "paths",
            "delta",
        }
        or evidence.get("step_index") != 45
        or evidence.get("comparison_basis") != "frozen_bf16_token_boundary_context"
        or evidence.get("shared_generated_prefix_tokens_before_step") != 45
        or evidence.get("source") != source
        or evidence.get("semantics") != semantics
        or evidence.get("comparison_dtype") != "float32"
        or evidence.get("top_k") != 5
        or evidence.get("delta") != expected_delta
        or set(evidence.get("paths", {}))
        != {"fp32_attached_adapter", "fp32_safe_merged"}
    ):
        raise GateError(f"Tool Router FP32 isolation {evidence_key} drift")
    representatives = {
        "fp32_attached_adapter": runs[0],
        "fp32_safe_merged": runs[2],
    }
    trace_key = "scores" if source == "generated.scores" else "raw_logits"
    top_values_key = f"top_{value_key}s"
    emitted_value_key = f"emitted_token_{value_key}"
    expected_path_keys = {
        "top_token_ids",
        "top_token_texts",
        top_values_key,
        "top_margin",
        "emitted_token_id",
        "emitted_token_text",
        emitted_value_key,
        "compared_tokens",
        "comparison_vector_sha256",
    }
    for path_name, run in representatives.items():
        path = evidence["paths"].get(path_name)
        top_ids = expected_top_ids[path_name]
        top_values = expected_values[path_name]
        if (
            not isinstance(path, dict)
            or set(path) != expected_path_keys
            or path.get("top_token_ids") != top_ids
            or path.get(top_values_key) != top_values
            or path.get("top_margin") != top_values[0] - top_values[1]
            or path.get("emitted_token_id") != 3849
            or path.get("emitted_token_id") != run["generated_token_ids"][45]
            or path.get("emitted_token_id") != top_ids[0]
            or path.get(emitted_value_key) != top_values[0]
            or path.get("comparison_vector_sha256")
            != run["generation_trace"][trace_key]["comparison_step_vector_sha256"]
        ):
            raise GateError(f"Tool Router FP32 isolation {evidence_key} path drift")
        compared = path.get("compared_tokens")
        if not isinstance(compared, list) or [
            item.get("token_id") for item in compared
        ] != [3849, 1866]:
            raise GateError(f"Tool Router FP32 isolation {evidence_key} token drift")
        for item in compared:
            token_id = item["token_id"]
            position = top_ids.index(token_id)
            if (
                item.get(value_key) != top_values[position]
                or item.get("rank") != position + 1
            ):
                raise GateError(f"Tool Router FP32 isolation {evidence_key} rank drift")


def _validate_fp32_drift_precision(runs: list[dict[str, Any]]) -> None:
    expected_generation = {
        "score_dtypes": ["float32"],
        "all_scores_float32": True,
        "raw_logit_dtypes": ["float32"],
        "all_raw_logits_float32": True,
        "autocast_enabled": False,
        "training": False,
    }
    independent = runs[0].get("precision_audit")
    if (
        not isinstance(independent, dict)
        or independent.get("base_parameters")
        != _expected_cuda_inventory("bfloat16", 1543714304, 338)
        or independent.get("adapter_parameters")
        != _expected_cuda_inventory("float32", 4358144, 224)
        or independent.get("floating_buffers")
        != _expected_cuda_inventory("float32", 64, 1)
        or independent.get("lora_target_modules") != 112
        or independent.get("lora_parameter_tensors") != 224
        or independent.get("adapter_parameters_finite") is not True
        or independent.get("active_adapters") != ["default"]
        or independent.get("is_peft_model") is not True
        or independent.get("input_output_embeddings_tied") is not True
        or independent.get("attn_implementation") != "sdpa"
        or independent.get("attention_class") != "Qwen2Attention"
        or independent.get("output_attentions") is not False
        or independent.get("hf_device_map") is not None
        or independent.get("generation") != expected_generation
    ):
        raise GateError("Tool Router independent BF16 precision audit drift")

    candidate = runs[1].get("precision_audit")
    if not isinstance(candidate, dict):
        raise GateError("Tool Router FP32 candidate precision audit missing")
    pre = candidate.get("pre_merge")
    post = candidate.get("post_merge")
    if (
        not isinstance(pre, dict)
        or pre.get("base_parameters")
        != _expected_cuda_inventory("float32", 1543714304, 338)
        or pre.get("adapter_parameters")
        != _expected_cuda_inventory("float32", 4358144, 224)
        or pre.get("floating_buffers") != _expected_cuda_inventory("float32", 64, 1)
        or pre.get("lora_target_modules") != 112
        or pre.get("lora_parameter_tensors") != 224
        or pre.get("adapter_parameters_finite") is not True
        or pre.get("active_adapters") != ["default"]
        or pre.get("is_peft_model") is not True
        or pre.get("input_output_embeddings_tied") is not True
        or pre.get("attn_implementation") != "sdpa"
        or pre.get("attention_class") != "Qwen2Attention"
        or pre.get("output_attentions") is not False
        or pre.get("hf_device_map") is not None
        or not isinstance(post, dict)
        or post.get("parameters")
        != _expected_cuda_inventory("float32", 1543714304, 338)
        or post.get("floating_buffers") != _expected_cuda_inventory("float32", 64, 1)
        or post.get("lora_target_modules") != 0
        or post.get("lora_parameter_tensors") != 0
        or post.get("is_peft_model") is not False
        or post.get("input_output_embeddings_tied") is not True
        or post.get("attn_implementation") != "sdpa"
        or post.get("attention_class") != "Qwen2Attention"
        or post.get("output_attentions") is not False
        or post.get("hf_device_map") is not None
        or candidate.get("generation") != expected_generation
    ):
        raise GateError("Tool Router FP32 candidate precision audit drift")


def _validate_fp32_step_evidence(
    gate: dict[str, Any],
    runs: list[dict[str, Any]],
    *,
    evidence_key: str,
    source: str,
    semantics: str,
    value_key: str,
    expected_values: dict[str, list[float]],
    expected_top_ids: dict[str, list[int]],
    expected_delta: dict[str, Any],
) -> None:
    evidence = gate.get(evidence_key)
    expected_keys = {
        "step_index",
        "common_prefix_generated_tokens",
        "source",
        "semantics",
        "comparison_dtype",
        "top_k",
        "paths",
        "delta",
    }
    if (
        not isinstance(evidence, dict)
        or set(evidence) != expected_keys
        or evidence.get("step_index") != 45
        or evidence.get("common_prefix_generated_tokens") != 45
        or evidence.get("source") != source
        or evidence.get("semantics") != semantics
        or evidence.get("comparison_dtype") != "float32"
        or evidence.get("top_k") != 5
        or evidence.get("delta") != expected_delta
        or set(evidence.get("paths", {}))
        != {"independent_bf16_adapter", "fp32_safe_merged"}
    ):
        raise GateError(f"Tool Router FP32 merge-drift {evidence_key} drift")
    paths = evidence["paths"]
    top_values_key = f"top_{value_key}s"
    emitted_value_key = f"emitted_token_{value_key}"
    expected_path_keys = {
        "top_token_ids",
        "top_token_texts",
        top_values_key,
        "top_margin",
        "emitted_token_id",
        "emitted_token_text",
        emitted_value_key,
        "compared_tokens",
        "comparison_vector_sha256",
    }
    for run in runs:
        path_name = run["path"]
        path = paths.get(path_name)
        top_ids = expected_top_ids[path_name]
        top_values = expected_values[path_name]
        if (
            not isinstance(path, dict)
            or set(path) != expected_path_keys
            or path.get("top_token_ids") != top_ids
            or path.get(top_values_key) != top_values
            or path.get("top_margin") != top_values[0] - top_values[1]
            or path.get("emitted_token_id") != run["generated_token_ids"][45]
            or path.get("emitted_token_id") != top_ids[0]
            or path.get(emitted_value_key) != top_values[0]
            or not _is_canonical_sha256(path.get("comparison_vector_sha256"))
            or run["generation_trace"][
                "scores" if source == "generated.scores" else "raw_logits"
            ]["divergent_step_comparison_vector_sha256"]
            != path.get("comparison_vector_sha256")
        ):
            raise GateError(f"Tool Router FP32 merge-drift {evidence_key} path drift")
        compared = path.get("compared_tokens")
        if not isinstance(compared, list) or [
            item.get("token_id") for item in compared
        ] != [1866, 3849]:
            raise GateError(f"Tool Router FP32 merge-drift {evidence_key} token drift")
        for item in compared:
            token_id = item["token_id"]
            position = top_ids.index(token_id)
            if (
                item.get(value_key) != top_values[position]
                or item.get("rank") != position + 1
            ):
                raise GateError(
                    f"Tool Router FP32 merge-drift {evidence_key} rank drift"
                )


def _expected_cuda_inventory(
    dtype: str,
    elements: int,
    tensors: int,
) -> dict[str, Any]:
    return {
        "floating_tensors": tensors,
        "floating_elements": elements,
        "dtypes": {dtype: elements},
        "devices": {"cuda:0": elements},
    }


def _is_canonical_sha256(value: object) -> bool:
    if not isinstance(value, str) or not value.startswith("sha256:"):
        return False
    digest = value.removeprefix("sha256:")
    return len(digest) == 64 and all(
        character in "0123456789abcdef" for character in digest
    )


def _fp32_cuda_inventory(value: object, *, expected_elements: int) -> bool:
    return (
        isinstance(value, dict)
        and isinstance(value.get("floating_tensors"), int)
        and value["floating_tensors"] > 0
        and value.get("floating_elements") == expected_elements
        and value.get("dtypes") == {"float32": expected_elements}
        and value.get("devices") == {"cuda:0": expected_elements}
    )


def _run_tests() -> int:
    suite = unittest.defaultTestLoader.discover(str(TESTS))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise GateError("unit test suite failed")
    return result.testsRun


def _load_json(path: Path) -> dict[str, Any]:
    return _load_json_payload(path.read_bytes(), path)


def _read_regular_file_once(path: Path, label: str) -> bytes:
    """Read one trust-root file while binding its path and handle identity."""

    try:
        before = path.lstat()
    except OSError as exc:
        raise GateError(f"unsafe or missing {label}: {path}") from exc
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    if (
        not stat.S_ISREG(before.st_mode)
        or path.is_symlink()
        or bool(getattr(before, "st_file_attributes", 0) & reparse_flag)
    ):
        raise GateError(f"unsafe or missing {label}: {path}")
    try:
        with path.open("rb") as handle:
            opened = os.fstat(handle.fileno())
            if _handle_identity_signature(before) != _handle_identity_signature(opened):
                raise GateError(f"{label} identity changed before read")
            payload = handle.read()
            handle_after = os.fstat(handle.fileno())
        after = path.lstat()
    except OSError as exc:
        raise GateError(f"failed to read stable {label}: {path}") from exc
    if (
        _handle_identity_signature(before) != _handle_identity_signature(handle_after)
        or _handle_identity_signature(handle_after) != _handle_identity_signature(after)
        or _stat_signature(before) != _stat_signature(after)
        or len(payload) != after.st_size
        or path.is_symlink()
        or bool(getattr(after, "st_file_attributes", 0) & reparse_flag)
    ):
        raise GateError(f"{label} changed while reading")
    return payload


def _stat_signature(
    value: os.stat_result,
) -> tuple[int, int, int, int, int, int]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _handle_identity_signature(
    value: os.stat_result,
) -> tuple[int, int, int, int, int]:
    # Windows handle fstat and path stat can expose different ctime semantics.
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_size,
        value.st_mtime_ns,
    )


def _load_json_payload(payload: bytes, path: Path) -> dict[str, Any]:
    value = json.loads(
        payload,
        object_pairs_hook=_unique_json_object,
        parse_constant=_reject_json_constant,
    )
    if not isinstance(value, dict):
        raise GateError(f"expected object: {path}")
    return value


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise GateError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> Any:
    raise GateError(f"non-finite JSON constant: {value}")


def _validate_finite_json(value: Any, path: str) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise GateError(f"non-finite JSON number at {path}: {value!r}")
    if isinstance(value, dict):
        for key, child in value.items():
            _validate_finite_json(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _validate_finite_json(child, f"{path}[{index}]")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GateError as exc:
        print(
            json.dumps(
                {"valid": False, "code": "FC_MVP_000_GATE_FAILED", "detail": str(exc)},
                sort_keys=True,
                separators=(",", ":"),
            ),
            file=sys.stderr,
        )
        raise SystemExit(2) from exc
