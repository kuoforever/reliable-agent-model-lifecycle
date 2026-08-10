# RAML-02 — Dataset and frozen evaluation governance

> **Status: current candidate resume item; repository-local versioned artifacts.**

- **JD tags:** dataset engineering, evaluation, leakage, split governance,
  reproducibility, Tool Router.
- **Candidate bullet (ZH):** 建立 20-case frozen eval 与 160/40、60 个
  task-family-disjoint train/validation 基线，并在不复制 eval 答案的前提下增加
  16/8 safety-repair 数据；通过 schema、distribution/leakage audit 与 digest
  binding 阻止评测污染和静默漂移。
- **Candidate bullet (EN):** Built a frozen 20-case evaluation and a 160/40
  train/validation baseline across 60 task-family-disjoint families, then added
  a 16/8 safety-repair increment with schema, distribution, leakage, and digest gates.
- **Sources:** [schema/eval](../../FC-MVP-001-schema-eval.md),
  [safety-repair data](../../FC-MVP-001-safety-repair-data-v2.md), and
  [project status](../../../PROJECT_STATUS.md).
- **Do not claim:** large-scale dataset coverage, unbiased generalization,
  production data, multimodal data, or leakage-free behavior outside registered audits.
- **Interview expansion:** discuss task-family split versus random split, why eval
  answers cannot enter repair data, and what a digest does not prove.
