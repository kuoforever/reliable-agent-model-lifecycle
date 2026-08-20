# MM-003 small-VLM post-training result review v2

> **Decision: FORMAL MEASUREMENT PASSED; SPECIFIC SYNTHETIC METRICS IMPROVED;
> REJECTION SAFETY AND REPEATABILITY REMAIN OPEN.**

## Registered execution

The one registered recovery-v2 execution completed on 2026-08-20 after
recovery protocol PR #40 merged. It binds merge commit
`3751a041ff12886a337df0066232379016fdbd9c`, preregistration SHA-256
`02e36d5981e0ed4ac90bfdb3c5cc9c9e1f78ff29ff927020b0a41ebb27f55c0e`,
and the exact 14-file Qwen2.5-VL-3B-Instruct snapshot at revision
`66285546d2b821cf421d4f5eb2576359d3770cd3`.

The run used one fresh training-model load, one three-epoch QLoRA lifecycle,
zero retries, and no execution network. It saved the registered Adapter file
set, released the training model, then used one fresh base load plus one
independent Adapter load for the unchanged nine-case MM-002 evaluation. The
evaluation made nine ordered generation calls with zero retries.

The dedicated v2 output directory was absent before invocation. Its exclusive
creation consumed the registered lifecycle; no second invocation occurred.
All 12 frozen protocol sources revalidated exactly. A pre-existing,
user-owned `AGENTS.md` working-tree change was outside that source closure and
was preserved rather than included in this result.

## Frozen artifacts

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `baseline/mm003-qwen2.5-vl-3b-qlora-sft-v2-training-run.json` | 6,853 | `474595081a20c46a62f664459b734d57ec03c8ddf121c9aedc055e16a052c516` |
| `baseline/mm003-qwen2.5-vl-3b-qlora-sft-v2-predictions.json` | 2,241 | `c2c703e5896fe64df9e156bda9d38975b92c1bf18c72f74f5a232dcbbbc4a028` |
| `baseline/mm003-qwen2.5-vl-3b-qlora-sft-v2-evidence.json` | 21,122 | `2190281e3e8acf97139e08c9949535a07b326897e23c5999a7f4750fccedabd5` |
| `baseline/adapters/mm003-qwen2.5-vl-3b-qlora-sft-v2/README.md` | 206 | `a73f9a4e826eca0a56f08ac2e7d415670b29eaae02bf501aa838ac23aaf3ebdb` |
| `baseline/adapters/mm003-qwen2.5-vl-3b-qlora-sft-v2/adapter_config.json` | 791 | `e8edf34169cc15c25e98965a5873e27c6eb54f4f95543e60d0452ec2fec60055` |
| `baseline/adapters/mm003-qwen2.5-vl-3b-qlora-sft-v2/adapter_model.safetensors` | 29,529,752 | `d93d2ea2d9f05564093cbb0b1286d2c368c54b01e847f1c37a98e00fb2914701` |
| `baseline/mm003-qwen2.5-vl-3b-qlora-sft-v2-result-review.json` | 11,311 | `3dff57b17eb4fc9966ab53fe92faea8921fb34b485e389aaa19af64610db957d` |

All 13 registered execution gates are true. The classification is
`local_qlora_adapter_measurement_established`, and the success-only result
review independently derives
`specific_synthetic_metric_improvement_with_rejection_failures_and_repeatability_unestablished`.

The offline review does not reload the model. It validates the execution's
independent-load evidence, recomputes the scorer and all non-time-dependent
evidence fields, and audits the Adapter bytes. The safetensors file contains
288 contiguous F32 tensors across 36 layers and Q/K/V/O LoRA A/B factors,
totalling 7,372,800 parameters. Its three registered shapes are
`16x2048` (144 tensors), `2048x16` (72), and `256x16` (72).
Every decoded F32 value is finite. The prediction producer is semantically
bound to `Qwen/Qwen2.5-VL-3B-Instruct+mm003-qlora-sft-v2` at the frozen model
revision, rather than inferred from a colocated artifact hash.

Repository reads are bounded by frozen byte counts before opening, reject
path escape, reparse ancestors, symlinks, and hardlinks, and recheck file and
parent identity after reading. Exclusive review generation binds its write
handle to the final path and verifies a content-addressed readback.

## Training measurement

| Epoch | Mean train loss | Mean validation loss | Optimizer steps completed |
|---:|---:|---:|---:|
| 1 | `0.42811885641680825` | `0.18540121532148784` | 6 |
| 2 | `0.1380899747212728` | `0.08482394470936722` | 12 |
| 3 | `0.06990893899152677` | `0.0682467356738117` | 18 |

Both recorded loss series decrease across the three measured epochs. This is
a description of one frozen run, not a variance estimate, convergence proof,
or generalization result.

## Unchanged MM-002 result

| Metric | Zero-shot baseline | Post-training v2 | Descriptive delta |
|---|---:|---:|---:|
| Grounding Accuracy | 0/5 | 3/5 | +0.6 |
| mean IoU | 0/1 | 1/2 | +0.5 value; eligible denominator changed |
| Action Accuracy | 0/9 | 3/9 | +0.3333333333333333 |
| Tool Accuracy | 0/5 | 5/5 | +1.0 |
| Argument Exact Match | 0/5 | 5/5 | +1.0 |
| stale-ref rejection | 0/2 | 0/2 | unchanged |
| coordinate/ref disagreement rejection | 0/1 | 0/1 | unchanged |
| prediction coordinate/ref disagreement | not applicable | not applicable | not comparable |

The strict compiler accepted all nine model outputs, reducing compiler
fallbacks from 9/9 in the zero-shot baseline to 0/9. That separates the
remaining errors from the earlier schema/compiler failure mode.

The six Action failures form a complete review-only taxonomy:

- `ground-003` and `ground-006`: fused act candidates carry the correct ref
  but omit the required bbox;
- `ground-004`, `ground-007`, and `ground-009`: required rejection is
  downgraded to fallback;
- `ground-005`: fallback disposition is correct but the reason vocabulary is
  not the frozen gold reason.

The taxonomy may guide a later data-only design, but MM-002 eval answers and
case-specific targets remain prohibited from training data.

## Resources and boundaries

The complete train/save/fresh-reload/eval lifecycle took
`130.3286408999993` seconds. Peak CUDA allocated and reserved memory were
`6,486,660,096` and `7,153,385,472` bytes, below the registered
`16,500,000,000`-byte caps and 1,800-second elapsed cap. The training substage
took `50.4985038000159` seconds and peaked at `4,924,369,920` allocated bytes.

This result establishes exactly one local synthetic training and evaluation
lifecycle, one saved Adapter, and one execution-observed independent Adapter
load. It does not establish:

- a registered global quality threshold or generalized quality improvement;
- successful stale-ref or coordinate/ref disagreement rejection;
- training or evaluation repeatability;
- real-content behavior or task success through desktop execution;
- cross-machine reproducibility or a portable artifact;
- commercial use, serving readiness, promotion, or Runtime eligibility.

The raw execution deliberately retains `quality_improved=false`,
`repeatability_established=false`, and every deployment/authority claim as
false. The result review does not rewrite those facts.

## Exact next action

The single next gate is
`MM-003-small-vlm-post-training-eval-repeatability-protocol-v1`.

Freeze an outcome-neutral same-environment replay protocol before any repeat
execution. It must bind the unchanged v2 Adapter bytes, MM-002 suite and
screenshots, prompt/compiler/generation/environment, one fresh base-plus-
Adapter load, nine ordered calls, offline execution, zero retries, a new
exclusive output directory, and layered raw/compiled/metric comparisons to
this first run. It must not retrain, modify the Adapter, add data, or describe
the replay as an execution-v2 retry.

## Reproduction

```powershell
python -I .\scripts\validate_mm003_post_training_v2_result.py
python -I .\scripts\validate_offline.py
```

The focused result-review suite contains 11 tests. The unified gate also
recomputes the prior protocol and failure lineage, the new raw evidence and
Adapter receipts, the scorer, the review decision, and all repository tests.

Locally, CPython 3.11.15 and 3.13.7 each pass the unified 571-test gate with
`valid=true`, four expected Windows privilege skips, and 49 audited source
files. Full-repository Ruff, Python 3.11 `py_compile`, and `git diff --check`
also pass. CPython 3.12 remains delegated to the pull-request Linux matrix;
the unavailable local 3.12 environment is not represented as a passed check.
