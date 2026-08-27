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

### GUI grounding data and evaluation v1

`MM-002` freezes nine synthetic, family-unique eval cases spanning ref/bbox/
fused grounding, UIA/screenshot/fused observations, clean/missing/noisy OCR,
and moved/occluded/stale/disagreement perturbations. Its standard-library
scorer reports exact grounding, IoU, action, tool, argument, stale-ref, and
coordinate/ref disagreement metrics. The deliberately imperfect predictions
are a scorer probe, not a model run; `model_evaluated=false` and all training,
execution, and Runtime eligibility claims remain false. See the
[MM-002 review](docs/MM-002-gui-grounding-data-eval-v1.md).

### Local small-VLM baseline protocol v1

`MM-003` now has an outcome-neutral protocol for one local nine-case baseline.
It pins `Qwen/Qwen2.5-VL-3B-Instruct` at revision
`66285546d2b821cf421d4f5eb2576359d3770cd3`, all 14 model-file hashes, the
Transformers BF16/SDPA environment, deterministic UIA/screenshot/fused inputs,
strict output compilation, resource caps, and fail-closed claims. A blank-image
compatibility smoke passed. The first formal attempt later completed nine
generation calls but failed in scoring because a prediction-dependent metric
had no applicable `ref`+`bbox` pair. No result artifact or model metric was
recovered, no retry occurred, and `model_evaluated=false` and
`runtime_eligible=false`. See the [MM-003 protocol](docs/MM-003-multimodal-gui-action-model-v1.md)
and [failure classification](docs/MM-003-local-small-vlm-baseline-failure-classification-v1.md).

### Local small-VLM baseline recovery protocol v2

`MM-003` froze a separate recovery protocol without editing v1 or
changing the model/revision, MM-002 inputs, prompt, compiler, generation, or
eval answers. The prediction-dependent disagreement diagnostic reports
explicit `not_applicable` when no prediction supplies both `ref` and `bbox`;
all core task-metric denominators remain fail-closed. The runner persists raw
and compiled candidate artifacts before scoring and writes a bound failure
receipt if scoring raises.

The single merged v2 execution then passed all 12 formal gates with one load,
nine ordered calls, zero retries, offline inference, and resource compliance.
All nine strict compilations fell back, so Grounding Accuracy was `0/5` and
Action Accuracy was `0/9`. This establishes the measurement baseline, not
model quality or Runtime eligibility. See the
[recovery protocol](docs/MM-003-local-small-vlm-baseline-recovery-protocol-v2.md)
and [v2 evidence](docs/MM-003-local-small-vlm-baseline-v2.md).

### Local small-VLM QLoRA post-training protocol v1

`MM-003` now freezes the post-training contract before any registered
training. Deterministic reviewed fixtures provide 18 train and 9 validation
records across the complete `uia_only / screenshot_only / fused × act /
reject / fallback` grid, plus 18 synthetic screenshots. Exact-identity audits
show no overlap with the frozen MM-002 case, family, instruction, complete
input, target, or screenshot sets.

The protocol pins a local 4-bit NF4 QLoRA lifecycle, seed and hyperparameters,
the bitsandbytes wheel, resource caps, exact Adapter filenames, and a fresh
base-plus-Adapter reload before the unchanged nine-case eval. Its single
merged v1 execution was consumed with zero retry and failed before the first
model forward: the training renderer incorrectly sent `pt-*` records through
the MM-002-only `ground-*` case registry. The exact raw receipt and a
model-free 27-record root-cause reproduction are tracked; no Adapter,
post-training metric, quality, serving, promotion, or Runtime result exists.
See the [post-training protocol](docs/MM-003-small-vlm-post-training-protocol-v1.md)
and [failure classification](docs/MM-003-small-vlm-post-training-failure-classification-v1.md).

### Local small-VLM QLoRA post-training recovery protocol v2

`MM-003` now freezes a separate recovery lifecycle without editing v1. A
closed recursive-leaf comparator permits exactly 12 registered identity,
output, gate, and next-action changes; all model, data, target, training,
reload, eval, cap, claim, and authority facts remain fixed. Ten v1 source
receipts remain exact and only the versioned recovery contract and runner are
added.

A post-training-only registry renders all 27 `pt-*` prompts before dependency
import, CUDA access, or model load. Per-record byte/hash receipts and a fixed
aggregate digest bind their order and contents, while family/repeat/target/raw
region fields remain excluded. The baseline `ground-*` registry is unchanged.
The recovery protocol was outcome-neutral at freeze; its later one-shot result
is reviewed separately. See the
[recovery protocol](docs/MM-003-small-vlm-post-training-recovery-protocol-v2.md).

### Local small-VLM QLoRA post-training result review v2

The single merged v2 execution completed one offline train/save/fresh-reload/
MM-002 lifecycle with zero retries. All 13 measurement gates passed; the
29,529,752-byte Adapter contains 7,372,800 LoRA parameters and was independently
loaded for nine ordered eval calls. Grounding rose from `0/5` to `3/5`, Action
from `0/9` to `3/9`, and Tool and Argument Exact Match from `0/5` to `5/5`,
with zero compiler fallbacks.

The result is mixed: stale-ref rejection remains `0/2`, coordinate/ref
disagreement rejection remains `0/1`, and only one local run exists. The raw
evidence therefore keeps generalized quality, repeatability, serving,
promotion, and Runtime claims false. The exact next gate is a frozen
same-environment eval-repeatability protocol for the unchanged Adapter, not
retraining or a retry. See the
[result review](docs/MM-003-small-vlm-post-training-result-review-v2.md).

### Local small-VLM post-training eval repeatability result v1

The merged `MM-003` replay protocol was consumed exactly once after restoration
and audit of its registered Python 3.12/CUDA environment. All 13 formal gates
passed with one base load, one read-only Adapter load, nine ordered offline
calls, zero retry, and no training or Adapter write. Raw UTF-8 outputs and
compiled predictions are each exact for 9/9 cases; metrics, generated-token
counts, and compiler-fallback status are exact as separately checked facts.

The model-free result review rebuilt the frozen execution evidence byte for
byte and establishes only bounded same-machine, registered-environment,
fixed-nine-case eval repeatability. `all_layers_exact` means raw / compiled /
metrics evidence layers, not Transformer internals; token-ID sequences were
not persisted. The original Anaconda base binary was not recovered, the
transitive dependency closure is not hash-locked, and resource, training, and
cross-machine repeatability remain untested. Serving, promotion, and Runtime
eligibility remain false. The next gate is the model-free MM-004 hard-negative
data protocol. See the [frozen protocol](docs/MM-003-small-vlm-post-training-eval-repeatability-protocol-v1.md)
and [result review](docs/MM-003-small-vlm-post-training-eval-repeatability-result-review-v1.md).

### Multimodal hard-negative data protocol v1

The model-free MM-004 protocol was frozen before data generation. It defines
exact clean/hard-negative pairs for seven reviewed failure categories,
domain-separated content identities, train/validation leakage checks, and a
read-only exclusion registry covering the existing 9 MM-002 eval, 18 MM-003
train, 9 MM-003 validation records, and 24 historical synthetic images.

No records existed at that protocol freeze. The separate downstream generation
gate has since materialized and validated the synthetic dataset without
training or model evaluation. See the
[protocol review](docs/MM-004-multimodal-hard-negative-data-protocol-v1.md).

### Multimodal hard-negative generation protocol v1

The generation preregistration freezes seed `44004`, four families per
category, a 3:1 train/validation family split, 28 pairs, 56 records, 28 unique
synthetic PNGs, and all 31 planned output receipts. The output bytes are
deterministically reconstructable in memory; no fixture or execution evidence
existed at freeze.

After PR #45 merged the preregistration as
`2d41b99e7e984975056f7e1088e768cd8a62b744`, the formal invocation from that
exact `master` materialized and independently validated 31 files / 127,336
bytes: 42 train records, 14 validation records, and 28 unique PNGs. The
execution evidence SHA-256 is
`0c79a89f8f2431640e4c91d9957af978775e54f2360c15eb67b97a89bb60b133`.
Generation and dataset validation are true; model evaluation, training,
quality, safety, serving, promotion, capture, and Runtime claims remain false.
The next gate is a separately frozen model-evaluation protocol. See the
[generation protocol](docs/MM-004-multimodal-hard-negative-data-generation-protocol-v1.md).

### Multimodal hard-negative model-evaluation protocol v1 and v2 repair

The 49,311-byte v1 protocol merged through PR #47, but its exact formal command
was rejected before output claim or model import. Git held the Adapter weight
as a 133-byte LFS pointer while v1 compared those bytes to the hydrated
29,529,752-byte payload receipt. OID, size, and hydrated SHA-256 all agree; no
attempt was consumed and no model call ran.

The separate 50,642-byte v2 repair kept the registered candidate, suite,
prompt isolation, compiler, total metrics, 56 ordered calls, zero retry,
resources, and terminal evidence unchanged. It added a new gate/output identity
and validated the exact Git LFS pointer separately from the full read-only
hydrated Adapter receipt. PR #48 merged v2 as
`365935c02e16badec9ba40a3c4d078b66726f96e`; its exact one-shot execution then
completed all 56 offline calls with zero retry, training, network use, or
Adapter write.

The model-free result review reconstructs the 6,644-byte evidence exactly and
freezes its SHA-256 as
`87c45c9a174b9c6d0419f1d0ba9c619597848b13fe4447a19988e7a6ff56292c`.
Overall accuracy is 32/56. All 28 hard negatives were rejected, but only 4/28
clean counterparts were accepted; there are 20 clean false rejects and four
invalid clean outputs. The formal gate means measurement complete within caps,
not quality accepted. Quality, generalized safety, training, serving,
promotion, and Runtime claims remain false.
The focused review suite passes 12/12 tests, and local CPython 3.11.15,
3.12.12, and 3.13.7 each pass the unified 660-test model-free gate with four
expected skips, 53 audited source files, and `valid=true`.
See the [v1 protocol](docs/MM-004-multimodal-hard-negative-model-evaluation-protocol-v1.md)
the [v2 repair](docs/MM-004-multimodal-hard-negative-model-evaluation-protocol-v2.md),
and the [result review](docs/MM-004-multimodal-hard-negative-model-evaluation-result-review-v2.md).

### Multimodal environment-adaptation protocol v1

MM-005 selects `Document / Chart / PDF` as the second environment after the
completed synthetic Desktop GUI depth chain. Its first vertical slice is
model-free, English, synthetic, and single-page: document text, table-cell,
bar-chart value, and page-region evidence grounding. Multi-page/noisy OCR,
handwriting, real or external documents, later environments, capture, Runtime
integration, and execution remain deferred.

Only four environment-specific component kinds are new: Environment Adapter,
task set, deterministic Verifier, and synthetic dataset. Training/evaluation
orchestration, Serving/routing, policy, approval, WAL, grounding authority,
budgets, recovery, and desktop dispatch remain inherited. The 49,202-byte
canonical protocol binds 63 source receipts and recomputed cross-stage content
exclusions for 92 prior cases/records, 64 families, and 52 images. No new data
was generated at that protocol freeze, and every training/model/quality/
safety/Serving/Runtime claim remained false. See the
[MM-005 protocol](docs/MM-005-multimodal-environment-adaptation-protocol-v1.md).

### Document/Chart/PDF data protocol v1

The separate MM-005 data preregistration freezes seed `55005`, eight template
families per task (six train and two validation), 32 records, 32 unique
1280×900 PNG page images, 14 deterministic single-page PDF source artifacts,
and all 49 future output receipts. All bytes reconstruct in memory from the
parent protocol and five source receipts; the fixed output and execution
evidence paths were absent at preregistration freeze.

PDF-source templates derive their PDF and PNG from one shared synthetic layout
ground truth without external rendering, OCR, network access, host fonts, or
model dependencies. Parent cross-stage exclusions and family/template/content/
image split isolation validate the full planned record set. At this gate,
generation, dataset validation, Adapter/Verifier execution, training/
evaluation, quality, safety, capture, Serving, promotion, and Runtime claims
were false. The downstream one-shot generation has since completed; see the
[MM-005 data protocol](docs/MM-005-document-chart-pdf-data-protocol-v1.md).

### Document/Chart/PDF data generation protocol v1

The one-shot generation boundary is frozen separately from the data plan. Its
17,780-byte protocol binds four execution-source receipts, the exact data
protocol, and all 49 planned outputs / 434,212 bytes. The runner requires an
aligned merged `master`, absent fixed targets, zero internal retries, atomic
output-root publication, exact-tree rejection of unregistered files,
independent persisted-byte validation, and exclusive evidence creation. PR
#52 merged the freeze as
`fbf1c64398d89c35e95f80322fd665ae3c2f2c1d`; the exact aligned-master
invocation then ran once with no retry.

The tracked result contains 32 records/images, 14 single-page PDFs, three JSON
files, and 49 total files / 434,212 bytes. Its 16,680-byte evidence has SHA-256
`a11a373a6c7d49b02470a84d9c303cb4f424ff6693dcc516ef8060af032d649f`.
Generation, records, images, and dataset validation are true. Adapter,
Verifier, model, quality, safety, real/external content, capture, Serving,
promotion, and Runtime claims remain false. The consumed invocation must not
be retried. See the
[MM-005 generation protocol](docs/MM-005-document-chart-pdf-data-generation-protocol-v1.md).

### Document/Chart/PDF Adapter/Verifier protocol v1

The separate model-free protocol freezes 32 deterministic Adapter projection
receipts and 160 Verifier reference cases before implementation. A model sees
only `instruction`, `observation`, `source_kind`, and `task_family_id`; gold,
record/split/provenance/Verifier metadata, and the real image path remain
outside its payload. Image path/bytes/SHA-256 binding stays Adapter-side.

The strict output compiler accepts only the exact `answer`, `evidence_refs`,
and `page_number` JSON shape. The model-free Verifier freezes 32 exact positive
controls plus 128 wrong-answer, wrong-evidence, duplicate-evidence, and
wrong-page controls with no model judge. The 126,032-byte protocol has SHA-256
`4715134d7bd1f8ae54275764f342bf5a8974cc491298dbefd52971aab876c64a`.
At protocol freeze, Adapter/Verifier implementation and execution, model/
training, quality, safety, Serving, promotion, and Runtime claims were false.
See the
[MM-005 Adapter/Verifier protocol](docs/MM-005-document-chart-pdf-adapter-verifier-protocol-v1.md).

### Document/Chart/PDF Adapter/Verifier implementation v1

PR #54 merged the protocol as
`db8c6833f43c02a0b255c436558e0269a8bde3b4` before implementation began. The
independent model-free Adapter now returns canonical model payload JSON plus
exact image bytes while keeping path and audit metadata separate. Its strict
compiler and deterministic Verifier independently reproduce all 32 projection
receipts and all 160 reference cases with zero mismatch.

The 102,117-byte implementation evidence has SHA-256
`d4cbe61cac4cff60c15e769c35e481ca93f71524b23bf0dad4ddf75095d17bf2`.
Adapter/Verifier implementation and bounded conformance execution are now
true; model training/evaluation, repeatability, quality, safety, Serving,
promotion, and Runtime eligibility remain false. See the
[MM-005 Adapter/Verifier implementation](docs/MM-005-document-chart-pdf-adapter-verifier-implementation-v1.md).

### Document/Chart/PDF model-evaluation protocol and result review v1

PR #55 merged the exact Adapter/Verifier implementation and conformance
evidence as `ff52da51aba534b051f9e247518fb2d20d1db1e2` before evaluation protocol
work began. The outcome-neutral read-only preregistration is now frozen as
58,414 canonical bytes with SHA-256
`cdb8d1ea09221763d87cd79ba752d9af8264ce49b7cf600eed338a073a04561b`.

It binds one exact Qwen2.5-VL base-plus-read-only-Adapter candidate, all 32
synthetic records in fixed order, 32 gold/path-isolated prompt projections,
strict compilation, deterministic total metrics, 1,800-second / 16.5-GB
integrity caps, one owner-marked zero-retry attempt, and mutually exclusive
terminal success/failure receipts. PR #56 merged the freeze as
`3be0083c3197111d57a4a5e5f70feced9f2c96f9`, after which its exact one-shot
command completed all 32 calls with zero retry.

The model-free review reconstructs the persisted result exactly. Compiler
validity is 28/32 and joint exact is 19/32. Chart and table are each 8/8 joint
exact, document text is 0/8, and page-region selection is 3/8. The 13 bad cases
are nine compiler-valid answer errors plus four compiler-invalid outputs.
Elapsed time was `216.03030519999447` seconds and peak allocated/reserved CUDA
memory was `6,458,204,160` / `6,777,995,264` bytes, inside the registered caps.
This establishes a completed fixed-suite measurement, not quality, safety,
repeatability, Serving, promotion, or Runtime eligibility. See the
[protocol](docs/MM-005-document-chart-pdf-model-evaluation-protocol-v1.md) and
[result review](docs/MM-005-document-chart-pdf-model-evaluation-result-review-v1.md).

### Document/Chart/PDF model-evaluation repeatability result v1

PR #57 merged the exact baseline execution artifacts and independent result
review as `056eb8d050eb0f0491ff21a07bd5b7716abf7eb8` before any repeat model
call. The unchanged same-machine fixed-suite replay was frozen as 47,974
canonical bytes with SHA-256
`4c5186cbfa542125d4f2b96dae14e31955effa330c42951f993413d276962ed7`.

The protocol authenticates the baseline, candidate, environment, 32-case
order, prompts, images, compiler, Verifier, metrics, generation settings, and
12-source execution closure. It permits one fresh base load, one independent
read-only Adapter load, 32 ordered offline calls, and zero retry, training,
network, or model/Adapter writes. Raw UTF-8, compiled JSON, Verifier verdicts,
metrics, and generated-token counts compare independently. Equality is an
observed result rather than a measurement-completion gate; resource equality
is diagnostic-only while the inherited caps remain integrity gates.

PR #58 merged that freeze as
`874f6c1a201a07d6680a3fa12217c1344b14c141`. Its one registered replay then
completed exactly once: one fresh base, one independent read-only Adapter, 32
ordered calls, and zero retry/network/training/write. Raw UTF-8, canonical
compiled JSON, deterministic Verifier verdicts, total metrics, and
generated-token counts are each exact for 32/32 cases.

The model-free review rebuilds the 20,952-byte evidence byte for byte and now
establishes only bounded same-machine, registered-environment-field, fixed-32-
case evaluation repeatability. Baseline/replay elapsed time is
`216.03030519999447` / `201.59785200000624` seconds, so resource repeatability
remains false even though allocated/reserved CUDA peaks are identical. The live
environment mapping was enforced by the frozen runner but not separately
persisted, and token IDs were not recorded. Training/resource repeatability,
cross-machine reproducibility, generalized quality, safety, Serving,
promotion, and Runtime claims remain false.

The new review suite passes 13/13 tests and the complete MM-005 chain passes
120/120. CPython 3.11.15, 3.12.12, and 3.13.7 each pass the unified 780-test
gate with four expected Windows privilege skips, 61 audited source files, and
`valid=true`. See the [repeatability protocol](docs/MM-005-document-chart-pdf-model-evaluation-repeatability-protocol-v1.md)
and [result review](docs/MM-005-document-chart-pdf-model-evaluation-repeatability-result-review-v1.md).

PR #59 published the exact replay artifacts, independent review, and strict
validator as `5f60cbf44a311b46b312090d62d2783424c1dc85`. All six checks
passed with no review, comment, thread, or merge-conflict blocker; both feature-
branch copies were deleted and local `master` was aligned with `origin/master`.

### Browser Research environment-adaptation protocol v1

The model-free third-environment protocol is published before any new data
generation, live browser/network use, model call, training, Serving work,
capture, or Runtime change. Its first vertical slice consumes one static
synthetic research bundle with one to three sources. Every source aligns DOM
nodes, an exact screenshot binding, and page text; strict output contains only
an answer plus ordered source-bound citation refs.

The four task families cover single-source fact citation, multi-source
synthesis, cross-source comparison, and freshness conflict resolution. All
URLs are HTTPS `.invalid` identities with fixed publication/snapshot times.
Live navigation/retrieval, JavaScript, login/session state, transactions, real
or external webpages, prompt-injection safety claims, and open-web source
ranking remain deferred.

The 76,364-byte canonical protocol has SHA-256
`62ef6c554c90d3523b7d9c2a0a102c2a8c783f3d3ba3496cd8c36dfebe04b06e`.
It reconstructs 102 exact source receipts and excludes 124 prior records, 96
families, 96 instruction/observation identities, 124 target identities, and 84
images. Adapter/Verifier implementation, data, browsing, model, quality,
safety, Serving, promotion, and Runtime claims remain false. See the
[Browser Research protocol](docs/MM-005-browser-research-environment-adaptation-protocol-v1.md).
The 17 focused tests and complete unified 797-test gate pass on local CPython
3.11.15, 3.12.12, and 3.13.7 with `valid=true`, four expected Windows privilege
skips, and 62 audited source files.

PR #61 published the exact protocol as
`d7e7b7f70ff298a47244c34cc22173c70c65e6c9`; all six Linux Python-matrix
checks passed with no review, comment, thread, or merge-conflict blocker. Both
feature-branch copies were deleted and local `master` was aligned with
`origin/master`. The single next gate is the model-free
`MM-005-browser-research-data-protocol-v1`; no Browser Research record or image
may be materialized before that protocol cleanly merges.

### Browser Research data protocol v1

The separate model-free preregistration is published as 73,476 canonical bytes
with SHA-256
`38e31afc46cf92603d191563bc5460062adeb702e7df3ee4ff18f485b034283a`.
Seed `55006` defines eight template families per task (six train and two
validation), 32 records, and explicit one-to-three-source bundles containing
68 static source snapshots and 68 unique 1280×900 PNG screenshots.

Every source descriptor, DOM, page text, screenshot, record, split dataset, and
manifest byte was rebuilt in memory before materialization. The 139 planned
outputs total 986,989 bytes and have exact path/byte/SHA-256 receipts. At this
data-protocol freeze the fixed output root and execution evidence were absent.
The static descriptors are canonical JSON, not executable HTML; no live
browser, JavaScript, network, model, capture, or Runtime path is used. See the
[Browser Research data protocol](docs/MM-005-browser-research-data-protocol-v1.md).
Fourteen focused tests pass, and local CPython 3.11.15, 3.12.12, and 3.13.7
each pass the complete unified 811-test gate with four expected Windows
privilege skips, 63 audited source files, and `valid=true`.

PR #63 merged the exact protocol as
`9518d5b59fb11dbea237caa17fd245f4dcd5c2db`; all six Linux matrix checks
passed with no review/comment/thread/conflict blocker. Both feature-branch
copies were deleted and local `master` was aligned with `origin/master` before
the separate generation-runner protocol begins.

### Browser Research data generation protocol v1

The separate one-shot, model-free runner merged through PR #65 as
`9739e2b86d8473d9b8e99ea32e541db6055e4523`. Both feature-branch copies were
deleted, and the single registered invocation then ran from that exact aligned
`master` with zero retry. Its 64,590-byte canonical protocol has SHA-256
`78c60102d042b65e8046523e9c78cc03137bbf3bf8edbb45a0e067bd3e16aa0d`.
It binds the published PR #63 merge commit, four exact data/generation source
receipts, the unchanged data protocol, and all 986,989 planned output bytes.

Formal execution requires aligned merged `master`, published-data ancestry,
absent output/evidence targets, zero retry, same-parent staging-root atomic
publication, exact-tree rejection, and independent persisted-byte readback.
The Windows runner uses extended-length physical paths while preserving the
same logical receipt paths, so deep screenshot paths do not depend on legacy
`MAX_PATH` behavior. No live browser, network, JavaScript, model, capture, or
Runtime path is available. See the
[Browser Research generation protocol](docs/MM-005-browser-research-data-generation-protocol-v1.md).

The tracked result contains 32 records, 68 static source snapshots, 68 PNG
screenshots, and exactly 139 files / 986,989 bytes. Its 63,294-byte execution
evidence has SHA-256
`1c5a7898f9811171c963db95b13a4fd33427b7ec58a4058ab5d4f077110f7fea`.
Only generation, records, source snapshots, screenshots, and dataset
validation are true. Adapter/Verifier, live browser/network, model, quality,
safety, real/external content, capture, Serving, promotion, and Runtime claims
remain false. The consumed invocation must not be retried or overwritten.

Seventeen focused adversarial tests pass. Ruff, scoped strict Mypy,
`py_compile`, protocol `--check`, `git diff --check`, and local CPython 3.11.15,
3.12.12, and 3.13.7 complete unified 828-test gates pass with four expected
Windows privilege skips, 64 audited source files, and `valid=true`. PR #66
published those exact result bytes as
`6e990f0cf8ba4f76bd35a57479c3649c4cadc3aa`; all six Linux matrix checks
passed, no review/comment/thread/conflict blocker existed, both feature-branch
copies were deleted, and local `master` was aligned with `origin/master`.

### Browser Research Adapter/Verifier protocol v1

The separate model-free protocol is frozen as 271,406 canonical bytes with
SHA-256
`a64f5d3d174ab2e8c7a003626d76981f43c15b9e739f8c999c4198df0c77156b`.
It binds PR #66's consumed result, eight source receipts, all upstream
protocol/evidence/dataset bytes, 68 screenshot plus 68 source-snapshot
bindings, 32 deterministic Adapter projection receipts, and 224 Verifier
controls. The 32 model payloads contain only instruction, static observation,
source kind, and task family; expected outputs, Verifier fields, identities,
splits, provenance, and repository artifact paths remain hidden.

The strict compiler accepts only `answer` plus unique ordered
`citation_refs`. Seven cases per record produce 32 positive and 192 negative
controls across wrong answers, wrong or unknown DOM refs, citation
order/coverage drift, missing latest freshness sources, duplicates, and
malformed JSON. No model or LLM judge is used. See the
[Browser Research Adapter/Verifier protocol](docs/MM-005-browser-research-adapter-verifier-protocol-v1.md).

Eleven focused adversarial tests, Ruff, scoped strict Mypy, `py_compile`, and
builder `--check` pass. Local CPython 3.11.15, 3.12.12, and 3.13.7 each pass
the complete unified 839-test gate with four expected Windows privilege skips,
65 audited source files, and `valid=true`. Adapter/Verifier
implementation/execution, live browser/network, model evaluation or
repeatability, quality, safety,
cross-machine reproducibility, Serving, promotion, and Runtime claims remain
false. After this protocol cleanly merges and both branch copies are deleted,
the next gate is the model-free
`MM-005-browser-research-adapter-verifier-implementation-v1`.

### Browser Research Adapter/Verifier implementation v1

The protocol merged through PR #67 as
`403cc240fec14d3d9123b6f207112a5290f4fc34`. The independent model-free
implementation now reproduces all 32 frozen Adapter projections and all 224
compiler/Verifier/citation-semantics controls. Its 195,994-byte canonical
evidence has SHA-256
`77634e6202354641eef84cf1640c17588e902c073f804b535dfb3ada52d09876`.

The Adapter exposes only canonical instruction/observation/source-kind/task-
family JSON plus 68 ordered screenshot byte channels. Exact source-snapshot
bytes and all repository paths remain audit-only. Missing, duplicate,
tampered, unsafe, or cross-record bindings fail closed. The independent strict
compiler and deterministic Verifier reproduce 160 compiler-valid and 64
compiler-invalid cases, 32 joint-correct positives, 192 negatives, and all
eight latest-source-removal freshness controls without a model or LLM judge.
See the [Browser Research Adapter/Verifier implementation](docs/MM-005-browser-research-adapter-verifier-implementation-v1.md).

Thirteen implementation-focused adversarial tests, full-repository Ruff,
scoped strict Mypy, `py_compile`, builder `--check`, and `git diff --check`
pass. Local CPython 3.11.15, 3.12.12, and 3.13.7 each pass the complete unified
852-test gate with four expected Windows privilege skips, 67 audited source
files, and `valid=true`. Model training or evaluation, model-evaluation
repeatability, quality, safety, live browser, network, real/external content,
capture, cross-machine reproducibility, Serving, promotion, Runtime changes,
and Runtime eligibility remain false. PR #68 published the exact implementation
as `1177d5649952af6c04f713f5cfbbde47388e3769`; all six Linux matrix checks
passed, no review/comment/thread/conflict blocker existed, both feature-branch
copies were deleted, and local `master` was aligned with `origin/master` before
the separate outcome-neutral model-evaluation protocol began.

### Browser Research model-evaluation protocol v1

The protocol is frozen locally before any model import or call as 116,152
canonical bytes with SHA-256
`84cd3d20d5a678a8ad0f7c38ad12e057225a4250e8143c5f004c2eaef8981f3f`.
It closes 12 source receipts, the exact PR #68 implementation lineage, the
read-only MM-004 candidate, and all immutable Browser Research dataset bytes.
The fixed 32-record suite contains 24 train and eight validation records with
68 ordered source bindings.

The model payloads total 81,796 bytes and expose only instruction,
observation, source kind, and task family. Exactly 68 ordered PNG screenshots
totaling 600,604 bytes are registered as visual inputs. The corresponding
118,742 source-snapshot bytes are independently receipt-bound audit evidence
and never enter the model. The strict two-key `answer`/`citation_refs`
compiler and deterministic Verifier register answer/citation joint exactness,
citation binding, minimum source coverage, latest-source freshness, and total
per-group metrics without an LLM judge.

The future owner-marked execution permits one fresh base load, one independent
Adapter load, 32 ordered calls, zero retries, no network or training, 1,800
seconds, and 16.5 GB peak allocated/reserved GPU memory. Accuracy cannot change
measurement completion. Sixteen focused adversarial tests, Ruff, scoped strict
Mypy, `py_compile`, and protocol `--check` pass locally. Local CPython 3.11.15,
3.12.12, and 3.13.7 each pass the complete unified 868-test gate with four
expected Windows privilege skips, 68 audited source files, and `valid=true`.
See the
[Browser Research model-evaluation protocol](docs/MM-005-browser-research-model-evaluation-protocol-v1.md).

No attempt is consumed and no model is evaluated at freeze. Clean PR
publication, review/conflict audit, merge, branch cleanup, and master alignment
remain required before the single successor
`MM-005-browser-research-model-evaluation-execution-v1` may run.

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

The MM-003 eval-repeatability lifecycle is closed: its one-shot replay passed
and its model-free review established only bounded same-machine fixed-eval
repeatability. The consumed output is immutable and permanently ineligible for
deletion, reuse, or retry. Training/resource repeatability, cross-machine
reproducibility, generalized quality, serving, promotion, commercial, and
Runtime claims remain false.

The MM-004 data/generation lifecycle, one-shot v2 model measurement, and exact
model-free result review are complete. The paired suite exposed a reject-biased
verifier: 28/28 hard negatives rejected, clean accept recall 4/28. The bounded
MM-005 environment-adaptation protocol now freezes the second environment and
its interfaces before expansion. The separate model-free
`MM-005-document-chart-pdf-data-protocol-v1` has merged with frozen counts,
seed, templates, receipts, and validation. Its separate one-shot generation
runner merged through PR #52 and the exact merged-master invocation completed
once: 49 files / 434,212 bytes and narrow execution evidence now exist and
validate exactly. PR #53 published those exact consumed bytes; they must remain
immutable. The separate
`MM-005-document-chart-pdf-adapter-verifier-protocol-v1` merged through PR #54
with 32 projections and 160 deterministic controls. The independent Adapter/
Verifier implementation now reproduces them exactly; PR #55 published its
102,117-byte evidence as
`ff52da51aba534b051f9e247518fb2d20d1db1e2`. The separate 58,414-byte
`MM-005-document-chart-pdf-model-evaluation-protocol-v1` merged through PR #56
as `3be0083c3197111d57a4a5e5f70feced9f2c96f9`. Its exact owner-marked
zero-retry baseline attempt is consumed and the model-free review records
19/32 joint exact, with chart/table 16/16 but document text 0/8 and page-region
3/8. The separate repeatability protocol merged through PR #58 as
`874f6c1a201a07d6680a3fa12217c1344b14c141`; its one replay is also consumed.
All five registered behavior layers are exact for 32/32 cases, and the new
model-free review establishes only bounded same-machine fixed-suite evaluation
repeatability. PR #59 published those exact artifacts and review as
`5f60cbf44a311b46b312090d62d2783424c1dc85`, closing this lifecycle.
Existing MM-002/MM-003/MM-004 evidence, the Adapter, generated data, and both
consumed MM-005 attempts remain read-only. The Browser Research environment and
data/generation lifecycle is published, its one-shot 139-file generation is
consumed, and its exact result is immutable. PR #67 published the model-free
Adapter/Verifier protocol; PR #68 then published the independent implementation
that reproduces all 32 projections and 224 citation/source/freshness controls.
The separate 116,152-byte
`MM-005-browser-research-model-evaluation-protocol-v1` is now frozen locally
before any model import or call. Publishing this exact preregistration without
consuming its attempt is the single active objective. It authorizes no live
browser/network use, training, Runtime change, real browser/desktop/document
capture, generalized quality/safety claim, repeatability claim, or reuse/retry
of any consumed attempt. Only its exact clean merge and branch cleanup may
activate the one registered zero-retry model-evaluation execution.

The portable-package qualification remains frozen and deferred, not passed.
Its exact resume action is still the independent native Windows target replay
defined by the
[portable-package qualification protocol](docs/FC-MVP-001-fp32-attached-portable-package-qualification-v1.md).
