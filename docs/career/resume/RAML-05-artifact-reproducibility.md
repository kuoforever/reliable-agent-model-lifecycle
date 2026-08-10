# RAML-05 — Offline artifact reproducibility and provenance

> **Status: current candidate resume item; cross-machine qualification is pending.**

- **JD tags:** MLOps, artifact packaging, reproducibility, provenance, hashing,
  supply chain, qualification.
- **Candidate bullet (ZH):** 为 FP32 attached candidate 构建 metadata-only
  composite manifest、clean-location replay 与 GitHub/Hugging Face revision-origin
  hash binding，在同一记录环境的新路径精确复现 20 个 raw output 和 20 个 compiled
  decision，并以冻结 rubric 选为下一步 portable qualification 的 preferred offline candidate。
- **Candidate bullet (EN):** Built a metadata-only composite manifest,
  clean-location replay, and GitHub/Hugging Face revision-origin hash binding for
  an FP32 attached candidate, exactly reproducing 20 raw outputs and 20 compiled
  decisions in the recorded environment.
- **Sources:** [offline package reproducibility](../../FC-MVP-001-fp32-attached-offline-package-reproducibility-v1.md),
  [origin attestation](../../FC-MVP-001-fp32-attached-remote-revision-origin-attestation-v1.md),
  [preferred decision](../../FC-MVP-001-fp32-attached-preferred-offline-candidate-decision-v1.md), and
  [qualification protocol](../../FC-MVP-001-fp32-attached-portable-package-qualification-v1.md).
- **Do not claim:** independent cross-machine replay, portable qualification,
  hardware-backed attestation, signing/transparency log, promotion, serving,
  deployment, or Runtime eligibility.
- **Interview expansion:** distinguish content identity, origin binding,
  same-environment reproducibility, operationally distinct host evidence, and promotion.
