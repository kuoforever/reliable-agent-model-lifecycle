# Project documentation index

中文：[README.zh-CN.md](README.zh-CN.md)

The repository keeps project descriptions, implementation evidence,
maintenance contracts, and documents used during development. English-native
technical reports are shared directly; Chinese operational sources have
English companion documents.

## Project and maintenance

| Document | English default | Chinese / source |
|---|---|---|
| Main README | [README.md](../README.md) | [README.zh-CN.md](../README.zh-CN.md) |
| Project status | [PROJECT_STATUS](../PROJECT_STATUS.md) | English source |
| Desktop Runtime integration | [English companion](en/desktop-runtime-integration.md) | [Chinese source](../Desktop_Runtime_依赖与集成.md) |
| Agent instructions | [AGENTS](../AGENTS.md) | English source |
| Career and learning hub | [Career index](career/) | Chinese-first working material derived from frozen evidence |
| Interview handbook | [Principles, applications, and engineering](career/interview/) | Chinese-first interview material with explicit implementation boundaries |

## Implemented technical evidence

| Topic | English default | Chinese / source |
|---|---|---|
| Runtime bridge consumer | [English version](en/FC-BRIDGE-001.md) | [Chinese source](FC-BRIDGE-001.md) |
| Runtime freeze pin | [Desktop Runtime integration](en/desktop-runtime-integration.md) | [Canonical record](../baseline/runtime-freeze-v1.json) |
| Lane A reliability dataset | [English version](en/adr/ADR-0001-lane-a-reliability-dataset-v1.md) | [Chinese source](adr/ADR-0001-lane-a-reliability-dataset-v1.md) |
| Lane B consent/capture/security contract v1 | [FC-BRIDGE-003 review](FC-BRIDGE-003-lane-b-consent-capture-security-v1.md) | Contract review complete; capture remains unimplemented |
| Multimodal trajectory schema v1 | [MM-001 review](MM-001-multimodal-trajectory-schema-v1.md) | Synthetic text/image topology; no capture or training eligibility |
| GUI grounding data/eval v1 | [MM-002 review](MM-002-gui-grounding-data-eval-v1.md) | Frozen synthetic eval and scorer; no model result |
| Local small-VLM baseline protocol v1 | [MM-003 protocol](MM-003-multimodal-gui-action-model-v1.md) | Frozen protocol; first formal attempt failed after generation |
| Local small-VLM baseline failure classification v1 | [MM-003 failure classification](MM-003-local-small-vlm-baseline-failure-classification-v1.md) | Scoring-totality failure bound; no model metric recovered |
| Local small-VLM recovery protocol v2 | [MM-003 recovery protocol](MM-003-local-small-vlm-baseline-recovery-protocol-v2.md) | Total optional metric + pre-score persistence frozen before execution |
| Local small-VLM baseline v2 evidence | [MM-003 baseline v2](MM-003-local-small-vlm-baseline-v2.md) | Formal execution gate passed; strict compiler fallback 9/9 and quality 0 |
| Local small-VLM QLoRA post-training protocol v1 | [MM-003 post-training protocol](MM-003-small-vlm-post-training-protocol-v1.md) | Training-only fixtures, exact QLoRA pins, independent Adapter reload, and unchanged eval frozen before training |
| Local small-VLM QLoRA post-training failure classification v1 | [MM-003 post-training failure classification](MM-003-small-vlm-post-training-failure-classification-v1.md) | Pre-forward prompt-registry mismatch bound; v1 consumed with no retry or result |
| Local small-VLM QLoRA post-training recovery protocol v2 | [MM-003 post-training recovery protocol](MM-003-small-vlm-post-training-recovery-protocol-v2.md) | Closed v1 delta, 27 prompt receipts, and pre-load prompt totality frozen before execution-v2 |
| Local small-VLM QLoRA post-training result review v2 | [MM-003 post-training result review](MM-003-small-vlm-post-training-result-review-v2.md) | Formal lifecycle passed; specific synthetic metrics improved while rejection safety and repeatability remain open |
| Local small-VLM post-training eval repeatability protocol v1 | [MM-003 eval repeatability protocol](MM-003-small-vlm-post-training-eval-repeatability-protocol-v1.md) | Outcome-neutral same-machine replay frozen before execution; its one-shot result is now reviewed |
| Local small-VLM post-training eval repeatability result review v1 | [MM-003 eval repeatability result review](MM-003-small-vlm-post-training-eval-repeatability-result-review-v1.md) | Formal replay passed; bounded same-machine fixed-nine-case eval repeatability established |
| Multimodal hard-negative data protocol v1 | [MM-004 protocol](MM-004-multimodal-hard-negative-data-protocol-v1.md) | Frozen model-free pair, identity, exclusion, split, provenance, and authority contract; downstream generation now validated |
| Multimodal hard-negative generation protocol v1 | [MM-004 generation protocol](MM-004-multimodal-hard-negative-data-generation-protocol-v1.md) | Seed, counts, and 31 receipts frozen before execution; exact merged-master materialization and result validation passed |
| Multimodal hard-negative model-evaluation protocol v2 | [MM-004 model-evaluation protocol](MM-004-multimodal-hard-negative-model-evaluation-protocol-v2.md) | Git LFS-aware v2 repair frozen and executed once from its exact merged commit |
| Multimodal hard-negative model-evaluation result review v2 | [MM-004 model-evaluation result review](MM-004-multimodal-hard-negative-model-evaluation-result-review-v2.md) | Formal measurement complete; 28/28 negatives rejected but clean accept recall is only 4/28, with no quality or Runtime claim |
| Multimodal environment-adaptation protocol v1 | [MM-005 environment-adaptation protocol](MM-005-multimodal-environment-adaptation-protocol-v1.md) | Frozen model-free Document/Chart/PDF scope, four-component delta, shared content exclusions, deterministic verifier, and unchanged Runtime authority; no data generated |
| Document/Chart/PDF data protocol v1 | [MM-005 data protocol](MM-005-document-chart-pdf-data-protocol-v1.md) | Seeded 32-record / 32-PNG / 14-PDF / 49-output preregistration with exact receipts and all execution claims false |
| Standard-library offline baseline | [ADR-0002](adr/ADR-0002-stdlib-offline-baseline.md) | English source |
| Environment baseline | [environment.md](environment.md) | English source |
| Tool Router schema/eval | [FC-MVP-001 schema/eval](FC-MVP-001-schema-eval.md) | English source |
| Base-model baseline | [FC-MVP-001 base model](FC-MVP-001-base-model-v1.md) | English source |
| LoRA SFT v1 | [FC-MVP-001 LoRA SFT](FC-MVP-001-lora-sft-v1.md) | English source |
| Safety-repair data v2 | [FC-MVP-001 safety repair](FC-MVP-001-safety-repair-data-v2.md) | English source |
| LoRA SFT v2 | [FC-MVP-001 LoRA SFT v2](FC-MVP-001-lora-sft-v2.md) | English source |
| LoRA SFT v2 failure classification | [FC-MVP-001 failure classification](FC-MVP-001-v2-failure-classification.md) | English source |
| Decision compilation v1 | [FC-MVP-001 decision compilation](FC-MVP-001-decision-compilation-v1.md) | English source |
| BF16 merge stability v1 | [FC-MVP-001 BF16 merge stability](FC-MVP-001-bf16-merge-stability-v1.md) | English source |
| BF16 merge numerics v1 | [FC-MVP-001 BF16 merge numerics](FC-MVP-001-bf16-merge-numerics-v1.md) | English source |
| BF16 merge remediation v1 | [FC-MVP-001 BF16 merge remediation](FC-MVP-001-bf16-merge-remediation-v1.md) | English source |
| FP32 merge drift analysis v1 | [FC-MVP-001 FP32 merge drift analysis](FC-MVP-001-fp32-merge-drift-analysis-v1.md) | English source |
| FP32 attached/merge isolation v1 | [FC-MVP-001 FP32 attached/merge isolation](FC-MVP-001-fp32-attached-merge-isolation-v1.md) | English source |
| FP32 attached/merge numerics v1 | [FC-MVP-001 FP32 attached/merge numerics](FC-MVP-001-fp32-attached-merge-numerics-v1.md) | English source |
| Attached BF16/FP32 dtype isolation v1 | [FC-MVP-001 attached dtype isolation](FC-MVP-001-attached-dtype-isolation-v1.md) | English source |
| Attached BF16/FP32 dtype numerics v1 | [FC-MVP-001 attached dtype numerics](FC-MVP-001-attached-dtype-numerics-v1.md) | English source |
| Attached BF16/FP32 dtype boundary control v1 | [FC-MVP-001 attached dtype boundary control](FC-MVP-001-attached-dtype-boundary-control-v1.md) | English source |
| FP32 attached remediation eval v1 | [FC-MVP-001 FP32 attached remediation eval](FC-MVP-001-fp32-attached-remediation-eval-v1.md) | English source |
| FP32 attached artifact eligibility review v1 | [FC-MVP-001 FP32 attached artifact eligibility review](FC-MVP-001-fp32-attached-artifact-eligibility-review-v1.md) | English source |
| FP32 attached offline package manifest v1 | [FC-MVP-001 FP32 attached offline package manifest](FC-MVP-001-fp32-attached-offline-package-manifest-v1.md) | [Use and limitations](FC-MVP-001-fp32-attached-offline-package-use-v1.md) |
| FP32 attached offline package reproducibility v1 | [FC-MVP-001 FP32 attached offline package reproducibility](FC-MVP-001-fp32-attached-offline-package-reproducibility-v1.md) | English source |
| FP32 attached remote revision-origin attestation v1 | [FC-MVP-001 FP32 attached remote revision-origin attestation](FC-MVP-001-fp32-attached-remote-revision-origin-attestation-v1.md) | English source |
| FP32 attached offline artifact eligibility reassessment v1 | [FC-MVP-001 FP32 attached offline artifact eligibility reassessment](FC-MVP-001-fp32-attached-offline-artifact-eligibility-reassessment-v1.md) | English source |
| FP32 attached preferred offline candidate decision v1 | [FC-MVP-001 FP32 attached preferred offline candidate decision](FC-MVP-001-fp32-attached-preferred-offline-candidate-decision-v1.md) | English source |
| FP32 attached portable-package qualification v1 | [FC-MVP-001 FP32 attached portable-package qualification](FC-MVP-001-fp32-attached-portable-package-qualification-v1.md) | Protocol frozen; target execution pending |

## Development references

| English companion | Chinese authoritative source |
|---|---|
| [Roadmap companion](en/mvp-roadmap.md) | [MVP roadmap](../多模态LLM全周期_MVP演进路线.md) |
| [Scenario companion](en/scenario-coverage.md) | [Scenario coverage matrix](../多模态与业务场景覆盖矩阵.md) |
| [Task map](en/task-checklist.md) | [Task checklist](../AI_Infra_LLM_Agent_待做任务清单.md) |
| [Template guide](en/writing-execution-templates.md) | [Writing and execution templates](../AI_Infra_LLM_Agent_写作与执行模块模板.md) |

`PROJECT_STATUS.md` remains the source of truth for sequencing and the single
active objective. The Chinese checklist remains authoritative for exact task
acceptance wording; its English companion is a stable navigation and usage
guide, not a second tracker.
