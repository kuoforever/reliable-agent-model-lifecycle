# MM-005 Document/Chart/PDF model-evaluation result review v1

## Outcome

PR #56 merged the frozen evaluation protocol as
`3be0083c3197111d57a4a5e5f70feced9f2c96f9`. All six Linux Python-matrix
checks passed, the pull request had no reviews, comments, or review threads,
and both feature-branch copies were deleted before execution.

The exact merged-master command then consumed the single registered
owner-marked attempt. It loaded one fresh Qwen2.5-VL base model and one
independent read-only Adapter, made all 32 ordered offline generation calls,
used zero retry, and persisted one mutually exclusive success terminal. The
formal gate passed because the complete registered measurement finished within
its resource caps. No accuracy threshold was registered, so this is not a
quality acceptance decision.

The fixed-suite result is 19/32 joint exact with strong task-family skew. The
result-review classification is
`fixed_synthetic_suite_joint_exact_19_of_32_with_task_family_skew`.

## Frozen artifacts

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `baseline/mm005-document-chart-pdf-model-eval-v1-attempt-owner.json` | 656 | `ca9e420fbce5582cab5944e0c290e569f97cad85ad3a5cf9e3c53aa13989d00b` |
| `baseline/mm005-document-chart-pdf-model-eval-v1-evaluation-candidate.json` | 32,190 | `e26f6a9ca03e826f627ae90aca5b2fdcf5bbed770d9752aa9ba74982ed7d12ea` |
| `baseline/mm005-document-chart-pdf-model-eval-v1-predictions.json` | 18,543 | `f9a545175688451fc5025eb1e90a1e1354a59c536887a54fe62deb80a019fff7` |
| `baseline/mm005-document-chart-pdf-model-eval-v1-evidence.json` | 7,495 | `5e330dde1debe7a207638d164aade8ab2c63fbcd8149b3178d64a16afd0fc78e` |
| `baseline/mm005-document-chart-pdf-model-eval-v1-result-review.json` | 15,235 | `7cc4990f900787123f078d2387855e4708b5eadb8d6705bb6364d8cab2f935a7` |

All five files are strict canonical JSON. The model-free validator reopens the
58,414-byte preregistration and exact 32-record suite, validates the owner and
candidate identity, recompiles the frozen raw outputs, reruns the deterministic
Verifier and total scorer, and rebuilds the 7,495-byte execution evidence and
15,235-byte review exactly. A success review also requires the registered
failure artifact to remain absent.

## Fixed-suite metrics

| Metric | Result |
|---|---:|
| Compiler validity | 28/32 (`0.875`) |
| Answer exact | 19/32 (`0.59375`) |
| Evidence exact | 28/32 (`0.875`) |
| Page exact | 28/32 (`0.875`) |
| Joint exact | 19/32 (`0.59375`) |
| Compiler-invalid outputs | 4 |

Split results are 14/24 joint exact on train and 5/8 on validation. The
task-family and source-kind results expose a non-uniform fixed-suite behavior:

| Group | Joint exact | Compiler valid |
|---|---:|---:|
| Chart value evidence grounding | 8/8 | 8/8 |
| Table-cell evidence grounding | 8/8 | 8/8 |
| Document-text evidence grounding | 0/8 | 8/8 |
| Page-region selection | 3/8 | 4/8 |
| Synthetic bar chart | 5/6 | 5/6 |
| Synthetic single-page PDF | 9/14 | 13/14 |
| Synthetic table document | 4/6 | 4/6 |
| Synthetic text document | 1/6 | 6/6 |

The exact bad-case taxonomy contains 19 correct cases, nine compiler-valid
`answer_only_wrong` cases, and four `compiler_invalid` cases. All 13 incorrect
cases are concentrated in document text (eight) and page-region selection
(five). Evidence and page matching remain correct for every compiler-valid
wrong answer; this observation does not establish that those subcomponents
generalize beyond the fixed synthetic suite.

## Execution and resources

| Counter | Observed |
|---|---:|
| Run attempts | 1 |
| Fresh base load attempts / loads | 1 / 1 |
| Independent Adapter load attempts / loads | 1 / 1 |
| Generate attempts / calls | 32 / 32 |
| Retry, network, training, optimizer, backward, Adapter writes | 0 each |

| Resource | Observed | Registered cap |
|---|---:|---:|
| Elapsed | `216.03030519999447` seconds | `1,800` seconds |
| Peak CUDA allocated | `6,458,204,160` bytes | `16,500,000,000` bytes |
| Peak CUDA reserved | `6,777,995,264` bytes | `16,500,000,000` bytes |

The 32 case latencies sum to `173.1301044000429` seconds, with minimum
`3.9176065` and maximum `11.8071423` seconds. The calls generated 1,091 tokens
in total, with minimum 22 and maximum 96 per case. These are single-run
diagnostics, not latency, throughput, or resource-repeatability claims.

## Claims and limitations

The result review establishes only these positive facts:

- the registered attempt was consumed and reached one success terminal;
- the fixed 32-case evaluation and every registered model call completed;
- the formal measurement gate passed within the registered caps;
- the exact fixed-suite metrics and task-family skew above were observed;
- the persisted artifacts reconstruct byte for byte without a model reload.

It does not establish quality improvement, generalized quality, safety,
same-machine evaluation repeatability, training or resource repeatability,
cross-machine reproducibility, real-content behavior, Serving eligibility,
promotion eligibility, or Runtime eligibility. The model and Adapter were not
modified. Model output has no execution authority, and Runtime remains the sole
policy, approval, WAL, grounding, budget, recovery, and desktop-dispatch
boundary.

## Next gate

The single next gate is
`MM-005-document-chart-pdf-model-evaluation-repeatability-protocol-v1`.
Before any second model import or call, it must freeze an outcome-neutral
same-machine replay of the unchanged candidate, environment, 32-case order,
prompt/image payloads, compiler, Verifier, generation settings, and
zero-retry owner-marked lifecycle. It must compare raw outputs, compiled
predictions, verdicts, metrics, generated-token counts, and resource
diagnostics against this immutable baseline without making equality a
measurement-completion threshold.

Do not delete, reopen, reuse, overwrite, or retry the consumed baseline output.
A later replay can establish only the explicitly compared, same-machine,
registered-environment fixed-suite layers; it cannot by itself establish
training/resource repeatability, cross-machine reproducibility, generalized
quality, safety, Serving, promotion, or Runtime eligibility.

## Model-free verification

```powershell
python -I -B -X pycache_prefix=NUL .\scripts\validate_mm005_document_chart_pdf_model_evaluation_result.py
```

The validator reads tracked artifacts only. It does not import ML dependencies,
load the base model or Adapter, use CUDA, call the network, or execute a second
attempt.

## Validation results

The protocol/result-focused suites pass 15/15 and 12/12 tests. The complete
MM-005 chain passes 91/91 tests. Tests cover historical freeze reconstruction,
consumed-output replay rejection before model context, exact artifact and
review recomputation, resealed tamper attempts against the preregistration,
candidate, predictions, and evidence, failure-artifact rejection, narrow
claims, and an AST proof that result review does not load or call the model.

Full-repository Ruff, scoped strict Mypy with import following isolated,
`py_compile`, the default result validator, and `git diff --check` pass. Local
CPython 3.11.15, 3.12.12, and 3.13.7 each pass the unified 751-test gate with
four expected Windows privilege skips, 60 audited source files, and
`valid=true`. These are model-free reconstruction results, not repeated model
execution evidence.
