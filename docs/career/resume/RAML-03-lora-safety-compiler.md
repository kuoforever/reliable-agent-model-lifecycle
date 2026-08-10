# RAML-03 — LoRA safety repair and decision compilation

> **Status: current candidate resume item; frozen local training/eval evidence.**

- **JD tags:** LoRA SFT, post-training, safety evaluation, structured output,
  error analysis, compiler.
- **Candidate bullet (ZH):** 在冻结的 176/48 数据与 20-case eval 上完成 Qwen
  Tool Router LoRA SFT v2，tool accuracy 达 0.95、dangerous-action candidate 降至
  0；随后以离线 decision compiler 消除冗余 flag 冲突，使 semantic validity 达
  1.0、false refusal 从 3 降至 0，同时保持 raw model output 不变。
- **Candidate bullet (EN):** Trained a frozen Qwen Tool Router LoRA SFT v2 that
  reached 0.95 tool accuracy with zero dangerous-action candidates, then added
  an offline decision compiler that raised semantic validity to 1.0 and reduced
  false refusals from three to zero without rewriting raw predictions.
- **Sources:** [LoRA SFT v2](../../FC-MVP-001-lora-sft-v2.md),
  [failure classification](../../FC-MVP-001-v2-failure-classification.md), and
  [decision compilation](../../FC-MVP-001-decision-compilation-v1.md).
- **Do not claim:** Runtime eligibility, deployment, broad statistical
  generalization, removal of compiler dependency, or that the merged BF16
  artifact was safe.
- **Interview expansion:** distinguish model quality from contract consistency,
  explain why a compiler can fix redundant fields without changing the model,
  and name the frozen negative results.
