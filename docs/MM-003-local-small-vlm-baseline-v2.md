# MM-003 local small-VLM baseline v2 evidence

> **Decision: FORMAL GATE PASSED; BASELINE QUALITY IS NEGATIVE.**

## Registered execution

The one registered v2 execution completed on 2026-08-17 after recovery
protocol PR #35 merged. The evidence binds merge commit
`9702c92c37f18c32a7458cbb2fa3c6d2e75e0490`, preregistration SHA-256
`369c813dee44b14c6022eb90739bcd37f9f8de472e60a8cee88682454d135403`,
and the unchanged Qwen2.5-VL-3B-Instruct revision
`66285546d2b821cf421d4f5eb2576359d3770cd3`.

Git Smart HTTP was unavailable locally after merge. Before execution, the
GitHub API-confirmed merge tree and the local execution tree were both
`f3a843b5647830d7c4c492af97f3b37d432d9416`; local HEAD was the exact PR head
and second parent of that merge commit. This establishes byte-identical
protocol-tree execution while avoiding a false claim that the signed merge
object was fetched through Git transport.

The run used one fresh model load, one full nine-case eval, nine ordered
generation calls, zero retries, and no execution network. The output directory
was absent before load. The runner persisted run and compiled candidates before
scoring; scoring completed, so no failure artifact exists.

## Frozen artifacts

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `baseline/mm003-qwen2.5-vl-3b-baseline-v2-run.json` | 14,715 | `173bb4ab17fa5d6c02323f9cc26e8cddd93525055a712b8f6c5cd5c09cb2a57c` |
| `baseline/mm003-qwen2.5-vl-3b-baseline-v2-predictions.json` | 2,058 | `57629229e4416cb7562382b57ee6774845dbd4f1da97b73a1e54d2a2f8ea17f7` |
| `baseline/mm003-qwen2.5-vl-3b-baseline-v2.json` | 4,680 | `a0e3c2503e5bac13bf979c7721dab4350681a84883d749b94ef3ca204d2166fe` |

All 12 registered gates are true, including exact model/input/environment
bindings, one complete run, zero retries, offline execution, resource caps,
schema validity, total diagnostic scoring, and pre-score persistence. The
classification is `local_small_vlm_baseline_established` and
`formal_gate_passed=true`.

## Quality result

| Metric | Result |
|---|---:|
| Grounding Accuracy | 0/5 |
| mean IoU | 0/1 |
| Action Accuracy | 0/9 |
| Tool Accuracy | 0/5 |
| Argument Exact Match | 0/5 |
| stale-ref rejection | 0/2 |
| coordinate/ref disagreement rejection | 0/1 |
| prediction coordinate/ref disagreement | not applicable, 0 eligible predictions |

The model generated nine JSON-looking raw candidates, but none satisfied the
frozen strict action schema. The compiler therefore produced 9/9 deterministic
fallback records, including 3/3 fallback in each of UIA-only,
screenshot-only, and fused modes. The optional prediction disagreement metric
correctly reports `not_applicable`; it is not counted as success.

This is a useful negative baseline: the checkpoint/backend can execute the
frozen multimodal loop, but zero-shot outputs do not satisfy the action
contract. The result does not distinguish prompt-format weakness from model
capability, and the preregistered gate intentionally contains no post-hoc
quality threshold.

## Resources and environment

The Windows CPython 3.12.12 run used Transformers 4.49.0, PyTorch
2.6.0+cu124, BF16/SDPA, NVIDIA driver 596.49, and the local RTX 4090 Laptop
GPU. Elapsed time was `41.921435199998086` seconds. Peak CUDA allocated and
reserved memory were `11,616,626,688` and `12,010,389,504` bytes, both below
the registered `16,500,000,000`-byte caps; elapsed time was below the
1,200-second cap.

## Boundaries and next action

This evidence establishes one same-machine synthetic baseline only. It does
not establish repeated-run variance, generalization, real-content behavior,
cross-machine reproducibility, portable packaging, post-training quality,
Adapter loadability, serving readiness, commercial eligibility, promotion,
direct execution, MCP, Desktop, or Runtime integration.

`baseline_executed=true` and `model_evaluated=true` apply only to this frozen
synthetic eval. `post_training_complete=false`,
`artifact_promotion_allowed=false`, and `runtime_eligible=false` remain
fail-closed.

The single next gate is `MM-003-small-vlm-post-training-protocol-v1`. Freeze
an outcome-neutral QLoRA training/evaluation protocol before any training;
keep MM-002 eval gold excluded from training and do not alter this baseline.

## Reproduction

```powershell
python -I .\scripts\validate_mm003_baseline_v2_evidence.py
python -I .\scripts\validate_offline.py
```

The four focused evidence tests and the unified 518-test offline gate pass on
CPython 3.12.12 and 3.13.7 with `valid=true` and 46 audited source files. PR CI
must also pass CPython 3.11, 3.12, and 3.13.
