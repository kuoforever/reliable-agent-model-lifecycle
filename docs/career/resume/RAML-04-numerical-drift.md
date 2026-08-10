# RAML-04 — BF16/FP32 numerical drift isolation

> **Status: current candidate resume item; repeat-stable single-example diagnostic lineage.**

- **JD tags:** ML systems, numerical precision, BF16, FP32, LoRA merge,
  PyTorch hooks, root-cause analysis.
- **Candidate bullet (ZH):** 将 LoRA Adapter 与 safe-merged BF16 路径的稳定输出差异
  定位到冻结样本 token index 45 的 raw-logit argmax flip，并通过 attached/merged、
  BF16/FP32 ABBA control、module hook 与 standalone `Qwen2RMSNorm` replay，将首个
  registered inequality 收窄到 layer 0 `input_layernorm` 的 dtype arithmetic boundary。
- **Candidate bullet (EN):** Isolated a repeat-stable LoRA attached-versus-merged
  token divergence to a raw-logit argmax flip at token 45, then used BF16/FP32
  ABBA controls, module hooks, and standalone `Qwen2RMSNorm` replay to locate the
  first registered inequality at layer-0 input normalization.
- **Sources:** [BF16 merge stability](../../FC-MVP-001-bf16-merge-stability-v1.md),
  [attached dtype isolation](../../FC-MVP-001-attached-dtype-isolation-v1.md),
  [dtype numerics](../../FC-MVP-001-attached-dtype-numerics-v1.md), and
  [boundary control](../../FC-MVP-001-attached-dtype-boundary-control-v1.md).
- **Do not claim:** a unique kernel/internal-operation root cause, independent
  downstream causality, general model behavior, or that FP32 removes all drift.
- **Interview expansion:** explain controlled variables, processed-vs-raw logits,
  first observed boundary versus causal root, and why negative isolation results matter.
