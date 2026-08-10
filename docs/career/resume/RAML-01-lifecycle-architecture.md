# RAML-01 — Reliable model-lifecycle vertical slice

> **Status: current candidate resume item; offline MVP path, not full target system.**

- **JD tags:** LLM lifecycle, Agent model, data pipeline, evaluation, safety,
  reproducibility, system architecture.
- **Candidate bullet (ZH):** 构建从 redacted Runtime evidence、数据治理、Tool
  Router post-training、冻结评测到 artifact qualification 的可复现纵向切片，
  用版本化 schema/digest 将模型候选与确定性 Runtime authority 分离。
- **Candidate bullet (EN):** Built a reproducible vertical slice from redacted
  Runtime evidence through Tool Router data governance, post-training, frozen
  evaluation, and offline artifact qualification, keeping model candidates
  separate from deterministic Runtime authority.
- **Sources:** [project status](../../../PROJECT_STATUS.md),
  [main overview](../../../README.md), and
  [Runtime bridge](../../FC-BRIDGE-001.md).
- **Do not claim:** completed multimodal lifecycle, serving, deployment,
  production users, Runtime integration of the model candidate, or large-scale
  foundation-model pretraining.
- **Interview expansion:** explain why the model and Runtime have separate
  authority/evidence boundaries and which artifact identity travels across stages.
