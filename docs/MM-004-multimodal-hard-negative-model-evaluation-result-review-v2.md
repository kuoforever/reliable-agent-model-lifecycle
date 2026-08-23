# MM-004 multimodal hard-negative model-evaluation result review v2

## Outcome

The single v2 execution completed from merged protocol freeze commit
`365935c02e16badec9ba40a3c4d078b66726f96e`. It consumed one owner-marked
attempt, loaded one fresh base plus one independent read-only Adapter, made all
56 registered offline model calls, used zero retry, and persisted the exact
candidate, predictions, and evidence.

The formal gate passed because the registered measurement completed within its
resource caps. No accuracy threshold was registered, so this is not a quality
acceptance decision. The model rejected all 28 fixed hard negatives but
accepted only 4 of 28 clean counterparts. The result-review classification is
`fixed_suite_all_hard_negatives_rejected_with_clean_accept_recall_4_of_28`.

## Frozen artifacts

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `baseline/mm004-hard-negative-model-eval-v2-attempt-owner.json` | 644 | `80d121c5e196e4cd6c7af68f08ba9a940af559909fe41b4a0b0e858068f59098` |
| `baseline/mm004-hard-negative-model-eval-v2-evaluation-candidate.json` | 34,700 | `246b5708362df0c51ea5362b0817b2a3c2984fbfc0f0e6148966b6612b8b20fe` |
| `baseline/mm004-hard-negative-model-eval-v2-predictions.json` | 7,761 | `cbf07b21abe620098f5f442778e0c3ef29a948e2c5ffd5c70a1baa9adda98618` |
| `baseline/mm004-hard-negative-model-eval-v2-evidence.json` | 6,644 | `87c45c9a174b9c6d0419f1d0ba9c619597848b13fe4447a19988e7a6ff56292c` |
| `baseline/mm004-hard-negative-model-eval-v2-result-review.json` | 18,220 | `711c1b52619d856015b832cd54a3bbfcaa419f360b95bf448d62de8230bdb720` |

All five files are strict canonical JSON. The model-free validator reopens the
frozen v2 preregistration and authenticated 56-record suite, validates owner
and candidate identity, reconstructs predictions from the candidate, reruns
the scorer, and rebuilds the 6,644-byte evidence exactly. A success review also
requires the registered failure artifact to remain absent.

## Fixed-suite metrics

| Metric | Result |
|---|---:|
| Overall accuracy | 32/56 (`0.5714285714285714`) |
| Clean accept recall | 4/28 (`0.14285714285714285`) |
| Hard-negative rejection recall | 28/28 (`1.0`) |
| Pair-exact accuracy | 4/28 (`0.14285714285714285`) |
| Compiler validity | 52/56 (`0.9285714285714286`) |
| Clean false rejects | 20 |
| Clean invalid outputs | 4 |
| Hard-negative false accepts | 0 |

The compiled output distribution is four `accept`, 48 `reject`, and four
`invalid`. Every incorrect case is a clean record: 20 are explicit false
rejects and four are invalid compiler fallbacks. The model therefore exhibits
a strong reject bias on this paired suite. Perfect hard-negative rejection
does not establish calibrated verification or safety because the same behavior
rejects most valid clean actions.

Train and validation splits have the same measured overall accuracy:
24/42 and 8/14, respectively. `duplicate_side_effect` is the only category
with 8/8 overall and 4/4 clean acceptance. Each of the other six categories is
4/8 overall with 0/4 clean acceptance; `observation_conflict` additionally has
only 4/8 compiler-valid outputs.

## Execution and resources

| Counter | Observed |
|---|---:|
| Run attempts | 1 |
| Fresh base load attempts / loads | 1 / 1 |
| Independent Adapter load attempts / loads | 1 / 1 |
| Generate attempts / calls | 56 / 56 |
| Retry, network, training, optimizer, backward, Adapter writes | 0 each |

| Resource | Observed | Registered cap |
|---|---:|---:|
| Elapsed | `87.70168950001244` seconds | `1,800` seconds |
| Peak CUDA allocated | `2,720,160,768` bytes | `16,500,000,000` bytes |
| Peak CUDA reserved | `3,078,619,136` bytes | `16,500,000,000` bytes |

Per-case generation latency sums to `51.83709889987949` seconds, with mean
`0.925662480354991`, minimum `0.7740325999911875`, and maximum
`1.7016468000074383`. The 56 calls generated 420 tokens in total: mean `7.5`,
minimum `7`, and maximum `14`. These are single-run observations, not latency,
throughput, or resource-repeatability claims.

## Claims and limitations

The result review establishes only these positive facts:

- the v2 attempt was consumed exactly once;
- evaluation and all registered model calls completed;
- the formal measurement gate passed within caps;
- all 28 fixed synthetic hard negatives were rejected;
- severe clean false refusal was observed on the paired suite.

It does not establish quality improvement, generalized quality, calibrated
safety, cross-machine or resource repeatability, real-content behavior,
training success, serving eligibility, promotion eligibility, or Runtime
eligibility. The Adapter and model were not modified. Model outputs retain no
execution authority, and Runtime remains the sole policy, approval, WAL,
grounding, budget, and desktop-dispatch boundary.

## Next gate

The reviewed result closes the registered MM-004 data/generation/evaluation
measurement chain without a quality claim. The next canonical checklist item
is `MM-005`; its first gate is
`MM-005-multimodal-environment-adaptation-protocol-v1`.

Before adding another environment, modality, training run, or Runtime change,
freeze one bounded, model-free MM-005 scope and acceptance protocol. Do not
delete, reuse, or retry the consumed MM-004 output.

## Model-free verification

```powershell
python -I -B -X pycache_prefix=NUL .\scripts\validate_mm004_hard_negative_model_evaluation_result.py
```

The validator reads tracked artifacts only, does not import ML dependencies,
does not load the model or Adapter, and does not use CUDA.

## Validation results

The focused result-review suite passes 12/12 tests, including resealed tamper
tests for the preregistration, candidate, predictions, and evidence; failure
artifact rejection; narrow-claim checks; and explicit proof that the review
does not import ML dependencies or call the model. Full-repository Ruff,
scoped strict Mypy, `py_compile`, v2 preregistration `--check`, the default
result validator, and `git diff --check` pass.

Local CPython 3.11.15, 3.12.12, and 3.13.7 each pass the unified 660-test gate
with four expected Windows privilege skips, 53 audited source files, and
`valid=true`. These are model-free reconstruction results, not repeated model
executions or cross-machine inference evidence.
