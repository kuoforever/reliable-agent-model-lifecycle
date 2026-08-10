# RAML-06 — Pre-registered evidence engineering

> **Status: current candidate resume item; process claims stay tied to exact gates.**

- **JD tags:** experiment design, pre-registration, evaluation infrastructure,
  CI, reproducibility, negative results.
- **Candidate bullet (ZH):** 以 outcome-neutral preregistration、immutable baseline、
  strict recomputation 和 Python 3.11/3.12/3.13 matrix 构建 fail-closed 实验门禁，
  将数据、模型、compiler、dtype、execution form、artifact 与硬件声明逐层解耦，并
  保留失败和未证实结论而非事后放宽 gate。
- **Candidate bullet (EN):** Built fail-closed experiment gates using
  outcome-neutral preregistration, immutable baselines, strict recomputation,
  and a Python 3.11-3.13 matrix, separating data, model, compiler, dtype,
  execution-form, artifact, and hardware claims.
- **Sources:** [project status](../../../PROJECT_STATUS.md),
  [writing templates](../../en/writing-execution-templates.md), and the frozen
  preregistration/evidence pairs linked by each technical item.
- **Do not claim:** external attestation where none exists, independent rerun
  counts from repository bytes alone, complete experiment governance, or CI as
  proof of GPU/model behavior.
- **Interview expansion:** explain why protocols freeze before outcomes, how
  strict validators recompute rather than trust summaries, and why a failed gate
  is useful evidence.
