# Reliable Agent Model Lifecycle

> A complete target system for multimodal data, post-training, evaluation,
> serving, reliable agent execution, and bad-case-driven model iteration.

中文：[README.zh-CN.md](README.zh-CN.md)

## Documentation

| Document | Purpose |
|---|---|
| [Project status](PROJECT_STATUS.md) | Current phase, single active objective, and latest validation evidence |
| [Documentation index](docs/README.md) | Implemented evidence, maintenance contracts, and development references |
| [Career and learning hub](docs/career/) | Full interview handbook, per-item JD evidence, and teaching-oriented collaboration modules |
| [Task checklist](docs/en/task-checklist.md) | English map of task IDs, dependencies, and Definition of Done |
| [Desktop Runtime integration](docs/en/desktop-runtime-integration.md) | Cross-repository ownership, safety boundaries, and version pins |

## Positioning

`Reliable Agent Model Lifecycle` names the complete system being built, not a
single MVP. It is not tied to autonomous driving or one business scenario.
Desktop GUI is the first verifiable environment; the architecture extends to
documents, browsers, charts, audio/video, and optional simulation as the
corresponding stages are implemented.

The goal is a reproducible lifecycle:

```text
multimodal data and agent traces
→ cleaning, redaction, quality, and versioning
→ SFT / QLoRA / distillation / preference optimization
→ action model / tool router / retriever / verifier
→ quantization / serving / routing / fallback
→ reliable agent runtime
→ traces / evaluation / bad cases / human review
→ dataset vN+1 / model vN+1
```

This repository owns model and dataset work. The separate
`guarded-desktop-agent` repository owns execution policy, approvals,
grounding, write-ahead logging, budgets, recovery, and the sole desktop
boundary. Models may propose actions but never bypass those controls.

## One flagship project and four depth labs

| Area | What it demonstrates |
|---|---|
| Flagship lifecycle | Data, post-training, evaluation, serving, runtime integration, and bad-case feedback |
| Tiny Transformer & Pretraining | Decoder internals, operator graphs, MHA/MQA/GQA, RoPE, KV cache, continued pretraining, and resumable training |
| Multimodal Post-training & Agentic RL | QLoRA, DPO/GRPO, verifiable rewards, verifier models, and ablations |
| Distributed Training & Inference | DDP/FSDP, collectives, vLLM, quantization, profiling, and correctness-gated Triton kernel experiments |
| Multi-Agent Systems | Coordination, typed handoffs, leases, conflict handling, recovery, and single-agent controls |

Only capabilities backed by code, tests, metrics, and artifacts are described
as implemented. Planned labs remain roadmap items.

The existing `FC-*` task IDs, `fullcycle_*` contract fields, Python package,
and CLI names remain unchanged for compatibility with frozen artifacts.

## MVP progression

Each MVP keeps a vertical loop and adds one primary variable:

| Version | Goal |
|---|---|
| MVP-0 | Freeze the reliable execution baseline |
| MVP-1 | Close the text Tool Router loop |
| MVP-2 | Add a screenshot/UIA/OCR GUI action model |
| MVP-3 | Add multimodal post-training and a verifier |
| MVP-4 | Add multi-model serving, quantization, routing, and rollout controls |
| MVP-5 | Use the Runtime as an Agentic RL environment |
| MVP-6 | Add environments and modalities |
| MVP-7 | Deepen model architecture, operator/kernel, distributed training, and inference systems work |
| MVP-8 | Add reliable multi-agent coordination |

See the [English roadmap companion](docs/en/mvp-roadmap.md) and
[scenario coverage companion](docs/en/scenario-coverage.md).

## Four gates

Every version must pass:

1. Functional gate: the new capability works on fixed tasks.
2. Regression gate: existing behavior and safety contracts stay intact.
3. Safety gate: false approvals, unauthorized actions, and duplicate side
   effects do not increase.
4. Performance gate: memory, latency, throughput, and cost stay within budget.

An experiment must bind the code commit, dataset version, model version,
configuration, seed, hardware, evaluation report, serving benchmark, failure
report, and demonstration evidence.

## Implemented evidence

### Runtime Lane A bridge

`FC-BRIDGE-001` implements a strict offline consumer for versioned Runtime
manifests and redacted run exports. It validates schema versions and digests,
rejects unknown or incomplete inputs, and never starts the provider, MCP,
desktop, or network layers. See [FC-BRIDGE-001](docs/en/FC-BRIDGE-001.md).

The offline Runtime dependency is frozen locally at
`324ff2fb5911e332ddb5c5f90eb41296e8faf7a9`; the exact contract and preflight
pin is retained in `baseline/runtime-freeze-v1.json`.

### Lane B consent/capture/security contract v1

`FC-BRIDGE-003` completes the local contract review for a separate,
disabled-by-default rich-episode lane. Its strict standard-library validator
requires explicit run-scoped consent, a visible indicator, local sanitization
and image redaction before write, content-addressed references, Runtime-only
dispatch authority, state-based verification, and complete deletion receipts.
The frozen fixture remains quarantine-only and training-ineligible. No capture
adapter, real episode, real deletion, dataset license, Runtime change, or
training eligibility is claimed. See the
[Lane B v1 review](docs/FC-BRIDGE-003-lane-b-consent-capture-security-v1.md).

### Multimodal trajectory schema v1

`MM-001` defines one strict, versioned topology for synthetic text-only and
image-grounded trajectories. Records bind Runtime/model/policy/environment,
pre/post observations, previous results, candidate tool/arguments/ref/bbox,
risk/approval/fallback/evidence, the Runtime decision, and state-based
verification. Runtime remains the only dispatch authority. No capture
adapter, real episode, dataset approval, training, execution, Runtime change,
or cross-machine claim is included. See the
[MM-001 review](docs/MM-001-multimodal-trajectory-schema-v1.md).

### Reliability/Verifier Dataset v1

`FC-BRIDGE-002` deterministically maps accepted Runtime evidence to canonical
JSONL. Version 1 emits only signals supported by Runtime facts: failure,
unknown outcome, policy denial, recovery, budget limits, and tool
sequence/outcome features. See [ADR-0001](docs/en/adr/ADR-0001-lane-a-reliability-dataset-v1.md).

### Tool Router schema and evaluation

`FC-MVP-001` defines Tool Router decision schema v1, 20 reviewed seed records,
20 frozen evaluation records, and 200 train/validation records across 60
explicit task families. Offline audits enforce family separation, duplicate
and near-duplicate rejection, distribution checks, and dangerous-action
checks. See [schema/eval gate](docs/FC-MVP-001-schema-eval.md).

### Local base-model baseline

The baseline pins `Qwen/Qwen2.5-1.5B-Instruct`, its Hub revision, inference
configuration, raw predictions, and an independent scorer. Measured on the
frozen 20-case evaluation set, JSON validity was 1.0, but tool accuracy was
0.20 and both dangerous cases produced dangerous action candidates. The model
is explicitly not Runtime eligible. See
[base-model baseline](docs/FC-MVP-001-base-model-v1.md).

### First local LoRA SFT

BF16 LoRA SFT on the frozen 160/40 train/validation data improved tool
accuracy from 0.20 to 0.80, argument exact match from 0.00 to 0.35, and risk
Macro F1 from 0.4258 to 0.7373, measured on the same unchanged 20-case
evaluation set with the same independent scorer. One dangerous-action
candidate remained, so `safety_gate_passed=false` and
`runtime_eligible=false`. The repository keeps the independent adapter,
configuration, raw predictions, reports, and safe-merge verification. See
[LoRA SFT v1](docs/FC-MVP-001-lora-sft-v1.md).

### Safety-repair data gate

The frozen SFT v1 bad cases are classified into four repair targets without
copying eval answers into training data. A reviewed train/validation-only v2
increment adds 16 train and eight validation examples across eight disjoint
families. The combined 176/48 data preserves v1 as an exact prefix, keeps the
20-case eval digest unchanged, and passes fail-closed leakage and
dangerous-action audits. No retraining occurred in this gate. See
[safety-repair data v2](docs/FC-MVP-001-safety-repair-data-v2.md).

### Safety-repair LoRA SFT v2

The locked three-epoch v2 run trained locally on the passed 176/48 data and
scored once on the unchanged eval. Tool accuracy reached 0.95 and dangerous
action candidates fell to zero. The adapter is still not Runtime eligible:
three decisions contain conflicting flags, three are false refusals, and a
safe merge changed one generated boolean on `eval-001`. These failures are
frozen as evidence rather than waived. See
[LoRA SFT v2](docs/FC-MVP-001-lora-sft-v2.md).

### LoRA SFT v2 failure classification

The frozen v2 evidence assigns the three conflicting decisions and the
count-aligned false refusals to decision-contract consistency. The one-field
load/merge drift is a separate BF16 adapter-merge stability failure. The
frozen artifacts do not justify a data-coverage diagnosis. One offline-only
decision-compilation gate was locked from this evidence and is now complete;
no v3 data or training has started.
See [failure classification](docs/FC-MVP-001-v2-failure-classification.md).

### Decision compilation v1

An offline compiler now derives the redundant terminal flags from the selected
tool under decision schema v1. On the unchanged frozen v2 outputs, semantic
validity reaches 1.0, false refusals fall from three to zero, tool accuracy
stays 0.95, and dangerous action candidates remain zero. Raw model predictions
are unchanged and the merged adapter remains prohibited. See
[decision compilation](docs/FC-MVP-001-decision-compilation-v1.md).

### BF16 merge stability v1

Two fresh independent Adapter loads and two fresh safe-merged BF16 loads are
each token-identical within their own path on frozen `eval-001`. The paths
diverge deterministically at generated token index 45: the independent path
selects `true`, while the merged path selects `false`. Processed generation
scores captured from the exact cached generation step confirm an argmax
boundary flip. The merged form remains prohibited and Runtime eligibility
remains false. See
[BF16 merge stability](docs/FC-MVP-001-bf16-merge-stability-v1.md).

### BF16 merge numerics v1

Paired hooks on the exact divergent cached generation step locate the first
module difference at layer 0 `q_proj`, after identical embedding and input
normalization outputs. Across all 112 LoRA target modules, PEFT safe merge
matches the reproduced algorithm exactly, but BF16 materialization rounds
30,640,994 nonzero Adapter updates back to their base values. The merged model
remains prohibited and Runtime eligibility remains false. See
[BF16 merge numerics](docs/FC-MVP-001-bf16-merge-numerics-v1.md).

### FP32 merge remediation v1

The pre-registered candidate materializes the pinned BF16 checkpoint values in
FP32, loads and safe-merges the FP32 Adapter, and retains FP32 for greedy SDPA
generation. Two fresh candidate loads are token-identical to each other on
frozen `eval-001`, but they do not match the independent BF16 Adapter reference.
Their token digest instead matches the prior safe-merged BF16 control. This is
classified as `deterministic_fp32_merge_output_drift`; full eval, merged-weight
promotion, and Runtime eligibility remain prohibited. See
[FP32 merge remediation](docs/FC-MVP-001-bf16-merge-remediation-v1.md).

### FP32 merge drift analysis v1

One fresh independent BF16 attached-Adapter path and one fresh locked FP32
safe-merged path each reproduce their frozen token and output digests on
`eval-001`. They first diverge at generated token index 45 (`true` versus
`false`). The same cached `generate(use_cache=True)` call captures both
processed generation scores and raw LM-head logits; both contain the argmax
flip. The classification is
`deterministic_bf16_attached_vs_fp32_merged_raw_logit_boundary_flip`.
Because this comparison changes dtype and attached/merged execution together,
it does not isolate a root cause. The analysis gate passes, the remediation
gate remains failed, and Runtime eligibility remains false. See
[FP32 merge drift analysis](docs/FC-MVP-001-fp32-merge-drift-analysis-v1.md).

### FP32 attached/merge isolation v1

Two fresh FP32 attached-Adapter runs are exactly repeat-stable across tokens,
decoded output, all processed-score vectors, all raw-logit vectors, and the
precision audit. The unchanged FP32 safe-merged path reproduces its frozen
evidence. All three runs emit the same 48 tokens and output, so there is no
same-dtype token boundary. At the pre-registered BF16 context step 45,
attached and merged FP32 retain the same `false` argmax but differ in 150,968
of 151,936 score and raw-logit elements, with maximum absolute delta
`0.0001735687255859375`. This isolates a small deterministic execution-form
numerical effect without proving a PEFT bug or a token-level remediation.
The isolation gate passes; remediation and Runtime eligibility remain false.
See [FP32 attached/merge isolation](docs/FC-MVP-001-fp32-attached-merge-isolation-v1.md).

### FP32 attached/merge numerics v1

Four fresh ABBA-ordered FP32 runs reproduce the attached and safe-merged
paths and are bitwise repeat-stable within each path. A pre-registered
13-stage paired capture plan first differs at layer 0 `q_proj`, after
bitwise-identical inputs. Its attached and merged outputs differ in 1,261 of
1,536 elements with maximum absolute delta `3.814697265625e-06`. Probe-captured
linear replays match both actual outputs; the stdlib gate recomputes their
comparisons and scalar/add identities. The evidence shows two counterfactual
differences that remain nonzero at the `q_proj` output boundary: factorized
LoRA versus a delta-weight linear, and split base-plus-delta versus a
materialized-weight linear. Their independent propagation beyond `q_proj` is
not isolated. The Git LFS sidecar binds 138 raw records,
including representative full weights and biases. This classifies a
deterministic FP32 execution-form drift, not a CUDA root cause, PEFT bug, or
same-dtype token boundary. The numerics gate passes; remediation and Runtime
eligibility remain false. See
[FP32 attached/merge numerics](docs/FC-MVP-001-fp32-attached-merge-numerics-v1.md).

### Attached BF16/FP32 dtype isolation v1

Four fresh ABBA-ordered attached-Adapter runs hold the factorized LoRA
execution form fixed while changing the base/inference dtype from BF16 to
FP32. Both paths keep the source Adapter at FP32 runtime precision. PEFT
`autocast_adapter_dtype=true` is locked as a load-time policy: it would upcast
FP16/BF16 Adapter weights, while these stored FP32 values remain FP32. Model
generation autocast remains disabled.

Each dtype is bitwise repeat-stable and reproduces its frozen 48-token path.
The paths share 45 generated tokens, then BF16 emits token `1866` (`true`)
while FP32 emits token `3849` (`false`) at index `45`. The raw LM-head argmax
also flips, and all `151,936` elements of the compared raw-logit vector differ.
This classifies a deterministic total dtype effect on one frozen attached
path, not a pristine-FP32 checkpoint comparison, unique operation/CUDA root
cause, full-eval improvement, or Runtime eligibility. See
[attached dtype isolation](docs/FC-MVP-001-attached-dtype-isolation-v1.md).

### Attached BF16/FP32 dtype numerics v1

Four fresh ABBA-ordered attached runs reproduce both frozen 48-token paths and
the exact cached forward that predicts generated token index 45. An
outcome-neutral 40-output plan covers the embedding, a detailed layer-0 spine,
all 28 decoder-layer outputs, final norm, and LM head. The embedding output is
canonically identical after conversion to FP32; the first unequal registered
output is layer 0 `input_layernorm`, where all 1,536 elements differ and the
RMS delta is `0.0009270972900508952`. All 38 later registered outputs remain
unequal. At the linked LM head, all 151,936 values differ and the RMS delta is
`0.29328314971734404`; both capture digests match the prior frozen raw-logit
vectors.

The JSON-only gate locks 160 repeat-exact capture summaries and all comparison
manifests without saving module tensors. It establishes a descriptive
registered total-dtype delta profile, not independent causal propagation from
RMSNorm, the first unregistered operation, a unique CUDA root cause, or
Runtime eligibility. See
[attached dtype numerics](docs/FC-MVP-001-attached-dtype-numerics-v1.md).

### Attached BF16/FP32 dtype boundary control v1

Four fresh attached runs reproduce the frozen BF16/FP32 paths and layer-0
`input_layernorm` boundary at cached call/step 45. After all attached models
are unloaded, four fresh standalone `Qwen2RMSNorm` executions replay the same
checkpoint input and weight values under the two locked dtypes. The standalone
BF16 and FP32 outputs exactly match their same-dtype actual outputs. Both
actual and control comparisons retain the frozen `1,536/1,536` unequal values
and RMS delta `0.0009270972900508952`.

This shows that locked same-values BF16/FP32 RMSNorm arithmetic is sufficient
to reproduce this local registered boundary. It does not identify a unique
internal operation or CUDA kernel, prove independent downstream propagation or
a token cause, establish pristine-FP32 checkpoint behavior, or pass a full
remediation evaluation. The boundary-control gate passes; remediation and
Runtime eligibility remain false. See
[attached dtype boundary control](docs/FC-MVP-001-attached-dtype-boundary-control-v1.md).

### FP32 attached remediation eval v1

The registered formal execution uses the one pre-registered FP32
attached-Adapter candidate and records one ordered pass over the unchanged
20-case eval with no retry. After the fixed decision compiler, argument exact
match improves from `0.20` to `0.25` and
argument field F1 improves from `0.2608695652173913` to
`0.29787234042553196`; tool accuracy remains `0.95`, every safety gate passes,
and no per-example correctness dimension regresses. The run takes
`71.6701673999778` seconds and peaks at `6,267,895,296` allocated GPU bytes,
within the pre-registered 2x BF16 ceilings.

Raw decision semantic validity falls from `0.85` to `0.80`, so the favorable
compiled result does not show that FP32 removes decision inconsistency. The
unchanged compiler remains necessary. Runtime eligibility and artifact
promotion remain false. See
[FP32 attached remediation eval](docs/FC-MVP-001-fp32-attached-remediation-eval-v1.md).

### FP32 attached artifact eligibility review v1

The offline review preserves the favorable fixed-compiler result while
separately recording the package state at that gate. Repository-local evidence
remains usable, but `offline_artifact_eligible=false`: at that review, the
package lacked an authoritative composite manifest, portable base/revision
binding, a tokenizer file manifest, required compiler binding, and complete
use/limitations documentation. The exact Adapter remains unchanged and structurally valid at
`224` F32 tensors and `4,358,144` parameters.

At that gate, the classification was
`fp32_attached_fixed_compiler_favorable_eval_but_offline_artifact_package_incomplete`.
Preferred-candidate, serving-readiness, promotion, merged-artifact, and Runtime
claims were all false. See
[FP32 attached artifact eligibility review](docs/FC-MVP-001-fp32-attached-artifact-eligibility-review-v1.md).

### FP32 attached offline package manifest v1

The externally authenticated metadata-only composite manifest binds the exact
unchanged attached package: pinned base and tokenizer files, the three-file
FP32 Adapter, required compiler and dependencies, prompt, generation,
precision, environment, and use/limitations contract. External raw-byte
SHA-256 validation and strict recomputation derive
`fp32_attached_metadata_only_composite_manifest_complete`; all six prior
package blockers are resolved.

At that manifest gate, this established metadata completeness and offline
package identity only. Remote revision origin, clean-location resolution, and
behavioral reproducibility remained unverified. Offline-artifact eligibility,
portable-package eligibility, preferred-candidate status, serving readiness,
promotion, merged-artifact permission, and Runtime eligibility remained false.
See the
[manifest evidence](docs/FC-MVP-001-fp32-attached-offline-package-manifest-v1.md)
and [use/limitations contract](docs/FC-MVP-001-fp32-attached-offline-package-use-v1.md).

### FP32 attached offline package reproducibility v1

A fresh checkout at frozen commit `eafd3f646e4ec08dd0a1f76443ccfd416e81fa22`
and a freshly downloaded pinned base snapshot resolve the exact package from
caller-supplied clean roots: base plus tokenizer `9/9`, Adapter `3/3`, and
repository sources `15/15`. The one pre-registered offline replay uses one
fresh FP32 attached-model load, 20 ordered generation calls, and zero retries.
It exactly reproduces all `20/20` raw UTF-8 outputs and all `20/20` compiled
canonical decisions from the frozen reference.

The classification is
`fp32_attached_same_environment_clean_location_behavior_exactly_reproduced`.
The measured replay takes `38.108256999985315` seconds and peaks at
`6,267,895,296` allocated GPU bytes; all registered resource caps pass. This
establishes clean-location resolution and exact 20-case behavioral replay only
in the same recorded environment. At that gate,
`remote_revision_origin_unverified` was the sole remaining blocker.
Offline-artifact, portable-package, preferred,
serving, promotion, merged-artifact, and Runtime claims remain false. See
[offline package reproducibility evidence](docs/FC-MVP-001-fp32-attached-offline-package-reproducibility-v1.md).

### FP32 attached remote revision-origin attestation v1

One frozen metadata-only observation binds the package to both hosted
revision authorities. GitHub resolves repository ID `1315085157` and commit
`eafd3f646e4ec08dd0a1f76443ccfd416e81fa22` to the exact 18-entry package
source closure, including the Adapter Git LFS pointer and advertised oid/size.
Hugging Face resolves `Qwen/Qwen2.5-1.5B-Instruct` revision
`989aa7980e4cf806f80c7fef2b1adb7bc71aa306` to all ten repository siblings and
the exact nine package files. Manifest SHA-256 values and independently
computed Git blob SHA-1 values close both content-address bindings.

The classification is
`fp32_attached_github_and_huggingface_hosted_revision_origins_attested` and the
prior `remote_revision_origin_unverified` blocker is closed. The observation
makes five fixed HTTPS metadata requests, downloads no model or Adapter LFS
payload, loads no model, makes no generation call, and stores no signed URL or
query. GitHub reports the package commit as unsigned, so author identity,
supply-chain signature, and transparency-log claims remain false.

At that origin gate, offline-artifact, portable-package, preferred, serving,
promotion, merged-artifact, and Runtime eligibility remained false pending
separate decisions. See the
[remote revision-origin evidence](docs/FC-MVP-001-fp32-attached-remote-revision-origin-attestation-v1.md).

### FP32 attached offline artifact eligibility reassessment v1

The frozen metadata-only reassessment recomputes the earlier artifact review,
composite manifest, clean-location replay, and remote-origin validators. All
nine preregistered gates pass: the fixed-compiler quality evidence is
favorable, repository-local evidence is usable, the exact package identity and
metadata are complete, all six historical package blockers are resolved, the
same recorded environment exactly reproduces all 20 raw and 20 compiled
outputs from a clean location, and both hosted revision origins are attested.

The classification is
`fp32_attached_fixed_compiler_favorable_eval_offline_artifact_package_eligible`
and `offline_artifact_eligible=true`. This is a package eligibility decision,
not a preferred-candidate or deployment decision. At that reassessment gate,
portable-package, cross-machine reproducibility, preferred, serving,
promotion, merged-artifact, and Runtime claims remained false. The
reassessment uses no network, model load, generation, training, or new
evaluation. See the
[offline artifact eligibility evidence](docs/FC-MVP-001-fp32-attached-offline-artifact-eligibility-reassessment-v1.md).

### FP32 attached preferred offline candidate decision v1

The frozen categorical decision recomputes the artifact review and offline
eligibility validators. All 12 gates pass. Relative to the frozen BF16
compiled reference, FP32 improves argument exact match from `0.20` to `0.25`
and argument field F1 from `0.2608695652173913` to
`0.29787234042553196`, with zero compiled regression events and all safety
checks passing. It remains inside the already registered resource cap.

The classification is
`fp32_attached_preferred_offline_candidate_under_fixed_compiler_attached_execution_and_registered_resource_caps`
and `preferred_offline_candidate=true`. This means preferred only as the next
offline candidate for portable-package qualification. The raw semantic value
falls from `0.85` to `0.80`, the compiler remains required, peak allocated GPU
memory is `1.9896087411587269x` BF16, and only one registered full-eval run
exists. Portable-package, cross-machine, serving, promotion, merged-artifact,
and Runtime claims remain false. See the
[preferred candidate evidence](docs/FC-MVP-001-fp32-attached-preferred-offline-candidate-decision-v1.md).

### Scale boundary of the current model evidence

Every model number above comes from a single RTX 4090 Laptop GPU, a 1.5B
base model, LoRA rank 16 over Q/K/V/O projections, a 100-step v1 run or
66-step v2 run, and a 20-case evaluation set built as ten categories with two
cases each. The frozen records and derived metrics are reproducible under the
locked data and evaluation contracts; model-execution repeatability applies
only where a gate explicitly establishes it. At this sample size the results
indicate direction only and do not establish generalization. The recent merge
and numerics diagnostic gates run only frozen `eval-001`, not the complete
20-case eval. These results are not a claim about large-scale pretraining,
post-training, or serving infrastructure, none of which is implemented.

The FP32 attached full eval operationally consumes its one pre-registered run.
Its metrics are reproducible from the frozen outputs, but the repository has
no external execution ledger or cryptographic execution-count attestation.
It therefore does not independently prove that no alternate output path was
ever executed; full-eval repeatability and variance are also intentionally not
estimated by this gate.

The clean-location gate adds one exact same-recorded-environment replay of the
frozen 20-case raw and compiled outputs. It does not estimate repeat variance
or establish cross-machine, cross-driver, or cross-library portability.

The origin gate adds content-addressed GitHub and Hugging Face hosted-revision
bindings. It does not establish author identity, a signed software supply
chain, a transparency log, or any new behavioral portability result.

The eligibility reassessment combines only those frozen evidence layers to
decide that the exact composite package is eligible as an offline artifact.
It adds no execution sample and therefore does not estimate variance,
cross-machine portability, relative candidate preference, serving readiness,
or production capacity, latency, and cost.

The preference decision adds no execution sample either. It selects the FP32
package only under its fixed compiler, attached execution form, and registered
resource caps. It does not turn a single strict case-level improvement into a
generalization, stable speedup, portable-package, capacity, latency, cost,
promotion, or deployment claim.

The portable-package qualification protocol is frozen at
`f8dc9a62471759282ad2b41673d95acd43bf240f`. It requires a new exact replay on
one operationally distinct native Windows machine under the locked user-space
environment and same GPU class. Its machine receipt stores only
domain-separated hashes of Windows MachineGuid and NVIDIA GPU UUID, binds them
to the target replay artifacts, and is explicitly not hardware-backed remote
attestation. No independent target execution has occurred, so cross-machine
reproducibility and portable-package eligibility remain false.

That frozen portable-package gate is deferred until an operationally distinct
native Windows target with the locked RTX 4090 Laptop GPU class is available.
The exact resume point remains commit
`f8dc9a62471759282ad2b41673d95acd43bf240f`; local controller evidence cannot
replace the required cross-machine replay.

## Reproducible offline gate

```powershell
python -I .\scripts\validate_offline.py
```

The gate validates frozen artifact hashes, dependency boundaries, unit tests,
bridge fixtures, and exact dataset JSONL on Python 3.11–3.13. Environment
details are in [environment.md](docs/environment.md).

## Current boundary

The current local work is `MM-002-gui-grounding-data-eval-v1`. Build a
reviewed synthetic evaluation set and deterministic scorer covering ref and
bbox grounding, UIA-only/screenshot-only/fused observations, OCR absence or
noise, moved or occluded controls, stale refs, and coordinate/ref disagreement.
Report Grounding Accuracy/IoU, Action Accuracy, Tool/Argument Accuracy, and
stale-ref rejection without implementing capture, collecting real user
content, changing Runtime, training a model, or making data training-eligible.

The portable-package qualification remains frozen and deferred, not passed.
Its exact resume action is still the independent native Windows target replay
defined by the
[portable-package qualification protocol](docs/FC-MVP-001-fp32-attached-portable-package-qualification-v1.md).
