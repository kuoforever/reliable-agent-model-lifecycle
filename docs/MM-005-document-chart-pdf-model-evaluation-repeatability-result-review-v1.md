# MM-005 Document/Chart/PDF model-evaluation repeatability result review v1

## Outcome

PR #58 merged the 47,974-byte outcome-neutral repeatability protocol as
`874f6c1a201a07d6680a3fa12217c1344b14c141`. After branch cleanup and exact
`master == origin/master` alignment, the registered command consumed its one
owner-marked replay attempt exactly once. It loaded one fresh Qwen2.5-VL base
model and one independent read-only Adapter, completed all 32 ordered offline
generation calls, and used zero retry, network, training, optimizer, backward,
model save, or Adapter write operations.

All ten formal measurement gates passed. The independent model-free review
rebuilds the execution evidence byte for byte and classifies the result as
`bounded_same_machine_registered_environment_fixed_32_case_evaluation_repeatability_established`.
This establishes only the five registered fixed-suite behavior layers on the
same Windows host and registered environment fields.

## Frozen replay artifacts

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `baseline/mm005-document-chart-pdf-model-eval-repeatability-v1-attempt-owner.json` | 783 | `4ac65e8f492a0988a0dbf7bface864c51d153f3e11b0fd48647d02226a7f4928` |
| `baseline/mm005-document-chart-pdf-model-eval-repeatability-v1-evaluation-candidate.json` | 32,390 | `de0bf6c2400a06f0edd912d024c50cb711c3686082834c10e1f7c25ef44e7e98` |
| `baseline/mm005-document-chart-pdf-model-eval-repeatability-v1-predictions.json` | 18,660 | `8664ffa2430680412c19733b49fc77920572a0b8960828e35f5365218ecfaa2e` |
| `baseline/mm005-document-chart-pdf-model-eval-repeatability-v1-evidence.json` | 20,952 | `659ea12140a85c044be1cdd0bf1ab867cbbdff2a097fbd447e07ec3b84e81617` |
| `baseline/mm005-document-chart-pdf-model-eval-repeatability-v1-result-review.json` | 18,817 | `c5b5f12dfaffb387ca7e394c8acbd2b92fc00e3a256ed8cab0d4e624b28d0ec8` |

All five files are strict canonical JSON. The review authenticates the frozen
preregistration and baseline lineage, revalidates the replay owner, candidate,
and predictions, recompiles raw model outputs, reruns the deterministic
Verifier and total scorer, and reconstructs the 20,952-byte evidence exactly.
The success path also requires the mutually exclusive failure artifact to be
absent.

## Registered comparisons

| Layer | Exact | Mismatches |
|---|---:|---:|
| Raw UTF-8 model output | 32/32 | 0 |
| Canonical compiled JSON | 32/32 | 0 |
| Deterministic Verifier verdict | 32/32 | 0 |
| Total metrics | Exact | 0 fields |
| Generated-token count | 32/32 | 0 |

The baseline and replay metrics are therefore identical: compiler validity is
28/32, answer and joint exact are 19/32, evidence and page exact are 28/32,
chart and table are each 8/8 joint exact, document text is 0/8, and page-region
selection is 3/8. Exact repetition of these fixed-suite outcomes does not turn
the weak document-text or page-region scores into a quality acceptance claim.

`all_registered_layers_exact` refers only to the five rows above. Transformer
internal activations and generated token-ID sequences were not persisted or
compared. Per-case latency was not a registered repeatability layer.

## Execution and resource diagnostics

| Counter | Observed |
|---|---:|
| Run attempts | 1 |
| Fresh base load attempts / loads | 1 / 1 |
| Independent Adapter load attempts / loads | 1 / 1 |
| Generate attempts / calls | 32 / 32 |
| Retry, network, training, optimizer, backward, saves, Adapter writes | 0 each |

| Resource | Baseline | Replay | Delta |
|---|---:|---:|---:|
| Elapsed seconds | `216.03030519999447` | `201.59785200000624` | `-14.432453199988231` |
| Peak CUDA allocated bytes | `6,458,204,160` | `6,458,204,160` | `0` |
| Peak CUDA reserved bytes | `6,777,995,264` | `6,777,995,264` | `0` |

Both runs remain below the registered 1,800-second and 16.5-GB integrity caps.
The full resource vector is not exact because elapsed time differs, so resource
repeatability remains false. GPU peak equality is a diagnostic observation,
not an independent resource-repeatability conclusion.

## Environment evidence boundary

The frozen formal runner observes the live environment after dependency load,
requires exact equality with the registered environment before generation, and
persisted a true `exact_candidate_and_environment` gate. The independent
preflight also observed the registered fields before the formal invocation.

The exact live environment mapping supplied to `build_evidence` was not stored
as a separate artifact. Post-run review can authenticate the frozen runner,
registered mapping, and passed gate, but it cannot recover that exact live
mapping from the evidence file alone. The preflight observation is therefore
classified as `reviewer_observed_untracked_context`. Machine ID and hardware
identity are not attested, and the complete transitive dependency closure is
not hash-locked. These are explicit limits on the narrow same-machine claim,
not hidden evidence.

## Claims and limitations

The result review establishes only that:

- the immutable baseline and one immutable replay were consumed;
- the registered replay completed within its integrity caps;
- the five registered fixed-32-case layers are exact between those two runs;
- model-free reconstruction reproduces the persisted evidence byte for byte;
- bounded same-machine, registered-environment-field, fixed-suite evaluation
  repeatability is established.

It does not establish training repeatability, resource repeatability, full
variance, token-sequence identity, cross-machine reproducibility, generalized
quality, quality improvement, safety, real-content behavior, Serving or
promotion eligibility, or Runtime eligibility. The Adapter remained read-only,
and model output has no execution authority.

## Model-free verification

```powershell
python -I -B -X pycache_prefix=NUL .\scripts\validate_mm005_document_chart_pdf_model_evaluation_repeatability_result.py
```

The command reads tracked artifacts only. It does not import ML dependencies,
load the base model or Adapter, use CUDA, access the network, or execute another
attempt.

## Validation results

The new result-review suite passes 13/13 tests, and the complete MM-005 chain
passes 120/120. Tests cover exact evidence/review reconstruction, every frozen
receipt, canonical JSON, artifact-set closure, resealed preregistration,
candidate, predictions and evidence tampering, required exactness and resource
semantics, failure-terminal exclusion, narrow claims, the environment evidence
limit, and an AST proof that review cannot load or call the model.

Full-repository Ruff 0.15.22, scoped strict Mypy 2.3.0, `py_compile`, the default
result validator, the unified result-review subcheck, and `git diff --check`
pass. Local CPython 3.11.15, 3.12.12, and 3.13.7 each pass the unified 780-test
gate with four expected Windows privilege skips, 61 audited source files, and
`valid=true`. No validation command reloads or reruns the formal model.

## Next gate

After this exact result slice is published and the feature branch is deleted
locally and remotely, the single next gate is
`MM-005-browser-research-environment-adaptation-protocol-v1`. It must remain
model-free and freeze Browser Research boundaries before new data generation,
model calls, training, Serving work, or Runtime changes.

Do not delete, reopen, reuse, overwrite, or retry either consumed MM-005
evaluation directory.
