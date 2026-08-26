# Project status

> Updated: 2026-08-26.
> This is the operational entry point for a new Reliable Agent Model Lifecycle
> session.

## Current phase

MVP-0 remains frozen. `FC-MVP-001` now has a strict Tool Router decision v1
contract, a frozen balanced eval set, 200 task-family-disjoint
train/validation records, deterministic validation, leakage/distribution
audits, an offline rule baseline, a reproducible local prompt-only model
baseline, two reproducible local LoRA SFT adapters, and a passed v2
safety-repair data gate. LoRA SFT v2 passed the narrow dangerous-action gate,
and its frozen failure-classification gate now separates decision-contract
inconsistency from BF16 load/merge output drift. Decision compilation v1
removes the former without changing raw model output. Merge stability v1
proves the latter is a deterministic BF16 logit-boundary flip rather than
within-path nondeterminism, and merge numerics v1 traces it to BF16
materialization of LoRA updates at the first projection. The pre-registered
FP32 remediation is repeat-stable but fails output identity and reproduces the
safe-merged BF16 token sequence instead of the independent BF16 Adapter
reference. FP32 merge drift analysis now reproduces both frozen paths and
confirms that their first generated-token boundary contains a raw-logit argmax
flip, not merely a logits-processor flip. Because that comparison couples
compute dtype with attached-versus-merged execution, FP32 attached/merge
isolation adds the missing same-dtype control. Two fresh attached runs are
exactly repeat-stable, the unchanged merged path reproduces, and both forms
emit identical tokens and output while retaining small deterministic numerical
trace drift. FP32 attached/merge numerics v1 now locates the first unequal
paired captured output at layer 0 `q_proj` and replays the factorized LoRA and
materialized-linear forms from a raw tensor sidecar. Both registered
counterfactual differences remain nonzero at the `q_proj` output boundary,
but their independent propagation beyond `q_proj` is not isolated. Attached
dtype isolation v1 now adds the missing fixed-form BF16/FP32 control: four
fresh ABBA-ordered attached runs reproduce both frozen paths, and the raw
LM-head argmax flips from `true` to `false` at the locked token boundary when
only the base/inference dtype changes while the Adapter remains FP32. This
isolates a repeat-stable total dtype effect on the one frozen example, not its
first module boundary or a unique low-level root cause. Attached dtype
numerics v1 now executes an outcome-neutral 40-output plan on the same cached
forward. The embedding output is canonically identical; the first registered
unequal output is layer 0 `input_layernorm`, and every later registered output
through the linked LM head remains unequal. Attached dtype boundary control v1
now replays the same checkpoint input and weight values through fresh
standalone `Qwen2RMSNorm` modules under the two locked dtypes. Both standalone
outputs exactly match their same-dtype actual module outputs. This establishes
that locked same-values BF16/FP32 RMSNorm arithmetic is sufficient to reproduce
this local registered boundary; it does not identify a unique internal
operation or kernel, nor establish independent downstream propagation or a
token cause. FP32 attached remediation eval v1 now records its one
pre-registered 20-case formal run. With the decision compiler fixed, argument
exact match improves from `0.20` to `0.25`, argument field F1 improves from
`0.2608695652173913` to `0.29787234042553196`, all safety and per-example
regression gates pass, and the run remains inside its 2x BF16 resource caps.
Raw semantic validity falls from `0.85` to `0.80`, so compiler dependency
remains explicit. The single-run record is an operational protocol fact rather
than external execution-count attestation: frozen hashes protect the selected
artifacts, but the repository cannot independently exclude an alternate-path
execution. FP32 attached offline package manifest v1 now binds the exact
unchanged attached package through an externally trusted metadata-only
composite manifest. Strict validation derives
`fp32_attached_metadata_only_composite_manifest_complete`; all six prior
package blockers are resolved. Clean-location reproducibility v1 now resolves
the exact package from fresh caller-supplied roots and exactly reproduces all
20 frozen raw outputs and 20 compiled decisions in the same recorded
environment with one fresh load and zero retries. All seven registered gates
and resource caps pass. Remote revision-origin attestation v1 now binds the
exact package to the fixed GitHub commit/tree/LFS pointer and the fixed Hugging
Face revision/file metadata through content-addressed SHA-256 and Git blob
SHA-1 checks. All ten origin gates pass and the prior origin blocker is closed.
Offline artifact eligibility reassessment v1 now recomputes all four upstream
validators; all nine gates pass and the exact composite package is eligible as
an offline artifact. Preferred-candidate decision v1 now applies its frozen
categorical rubric to the BF16/FP32 quality, compiler, resource, execution-form,
and portability evidence. All 12 gates pass and FP32 is the preferred next
offline candidate for portable-package qualification. The qualification
protocol is now frozen before target execution; no independent target replay
or formal portable-package result exists. Author/signature,
supply-chain, transparency-log, cross-machine, portable, serving, promotion,
merged-artifact, and Runtime claims remain false pending separate decisions.
Local negative controls on the controller confirm that the portable protocol
fails closed when machine identity is not distinct; that gate is deferred at
its frozen `f8dc9a62471759282ad2b41673d95acd43bf240f` resume point until a
qualifying independent native Windows host is available. `FC-BRIDGE-003` now
completes the separate Lane B v1 consent/capture/security contract review with
a strict validator, closed schema, synthetic fixtures, and deletion binding.
Lane B remains disabled, quarantine-only, and training-ineligible; no capture
adapter or Runtime change exists. `MM-001` now closes the synthetic multimodal
trajectory schema review: text-only and image-grounded fixtures share one
strict v1 topology with Runtime-only dispatch authority, state-based
verification, and all training/execution/Runtime eligibility claims false.
`MM-002` now closes the synthetic GUI grounding data/eval review with nine
family-unique eval cases, two closed schemas, exact rational IoU aggregation,
and a deliberately imperfect scorer probe. No model was evaluated.
`MM-003` has an outcome-neutral local small-VLM baseline protocol frozen before
formal eval execution. It pins Qwen2.5-VL-3B-Instruct revision
`66285546d2b821cf421d4f5eb2576359d3770cd3`, all 14 model files, the local
BF16/SDPA environment, deterministic synthetic images, prompt/compiler,
nine-call order, resource caps, and fail-closed claims. An unrelated blank-image
compatibility smoke passed. The single v1 formal attempt later reached scoring
after nine generation calls but failed with `EMPTY_METRIC_DENOMINATOR` before
writing artifacts. No retry or MM-002 model result exists. A separate v2
recovery protocol froze total optional-metric semantics and pre-score
candidate persistence without changing the model, inputs, prompt, compiler,
generation, or eval answers. Its single merged v2 execution has since passed
the formal measurement gate while producing 9/9 compiler fallbacks and zero
task accuracy. A separate QLoRA post-training protocol froze before registered
training. Its single merged v1 execution was consumed with zero retry and
failed before the first model forward. The training input renderer incorrectly
delegated `pt-*` records to the MM-002-only `ground-*` case registry. The exact
raw failure receipt and deterministic 27-record static reproduction are now
classified; no Adapter, training metric, MM-002 post-training result, quality,
serving, promotion, or Runtime claim exists.
A separate v2 recovery protocol froze before model execution and later merged.
Its one zero-retry train/save/fresh-reload/MM-002 lifecycle has now passed all
13 formal measurement gates. The result review freezes the 29,529,752-byte
Adapter, 7,372,800 trainable parameters, three decreasing recorded train/
validation-loss pairs, Grounding `3/5`, Action `3/9`, Tool and Argument `5/5`,
zero compiler fallbacks, and six exact remaining bad-case classes. Stale-ref
and coordinate/ref disagreement rejection remain `0/2` and `0/1`; generalized
quality, repeatability, serving, promotion, and Runtime claims remain false.
The merged eval-repeatability protocol was consumed exactly once after its
registered Python 3.12/CUDA environment was restored and independently
re-audited. All 13 formal gates passed with one base load, one read-only Adapter
load, nine ordered offline calls, zero retry, and no training or Adapter write.
Raw UTF-8 outputs and compiled predictions are each exact for 9/9 cases;
metrics, generated-token counts, and compiler-fallback status are also exact.
The independent model-free review rebuilt the evidence byte-for-byte and now
establishes only bounded same-machine, registered-environment, fixed-nine-case
eval repeatability. It does not establish token-ID identity, training or
resource repeatability, cross-machine reproducibility, generalized quality,
serving, promotion, or Runtime eligibility. The original Anaconda base binary
was not recovered and transitive dependency hashes were not fully pinned.
`MM-004-multimodal-hard-negative-data-protocol-v1` is now frozen before any
new record generation. Its model-free contract covers exactly seven reviewed
hard-negative categories, atomic clean/negative pairs, domain-separated
content identities, train/validation split isolation, and a read-only
exclusion registry for 36 MM-002/MM-003 cases and families plus 24 historical
synthetic images. The protocol and 32 exact source receipts rebuild from
tracked inputs. At that protocol freeze, no hard-negative record or dataset
split existed.
The downstream deterministic MM-004 generation preregistration then froze
before materialization. Seed `44004` fixes four families per category with a
3:1 train/validation family split: 28 pairs, 56 records, and 28 unique
synthetic PNG scenes. All 31 output paths, byte counts, and SHA-256 values were
precomputed in the 10,522-byte config with digest
`c49e18ec570ff198dfa564fdb711b3ba45cf34e5934a9cb667e6a62e13a07ceb`.
PR #45 merged that freeze as
`2d41b99e7e984975056f7e1088e768cd8a62b744`. The formal zero-internal-retry
invocation from that exact aligned `master` atomically materialized all 31
outputs: 28 clean/negative families, 56 records (42 train and 14 validation),
28 unique PNGs, and 127,336 total fixture bytes. The 9,425-byte execution
evidence has SHA-256
`0c79a89f8f2431640e4c91d9957af978775e54f2360c15eb67b97a89bb60b133`.
Independent reconstruction validates every output receipt, pair/category,
provenance, split, exclusion, image binding, and narrow claim. Generation and
dataset validation are true; training, verifier/model evaluation, quality,
safety, serving, promotion, capture, Runtime change, and Runtime eligibility
remain false.

The v1 downstream model-evaluation protocol froze as 49,311 canonical bytes
with SHA-256
`3011420f26bc61f572de2e21f96d28215529e495075db4e958573a4e4317484f` and
merged through PR #47 as
`425a4f21c82786d054ce620e83f6703e4f235d2f`. Its exact formal invocation was
rejected during freeze-commit receipt validation before output claim, model
import, GPU use, or any model call. Git stores the 29,529,752-byte Adapter
weight as an exact 133-byte LFS pointer; v1 incorrectly compared those pointer
bytes directly with the hydrated payload receipt. The pointer OID/size and the
hydrated payload SHA-256/size agree exactly, so this is a pre-consumption
representation-layer validation bug, not Adapter drift or a model result. The
v1 fixed output remains absent and its attempt was not consumed.

The v2 repair froze separately before any model call. Its 50,642-byte
canonical preregistration has SHA-256
`bee2093d54d95cc52303c57c598d99a071aff85bef9f56605adeb2b604f8c0d9`.
It preserves the exact candidate, 56 records, 28 images, prompts, compiler,
metrics, call order, resource caps, and owner-marked lifecycle while adding a
new gate/output identity and dual Adapter binding: exact Git LFS pointer at the
freeze commit plus full read-only hydrated receipt before and after execution.
At that freeze, both v1 and v2 fixed outputs were absent and all execution
claims were false.
The focused v2 suite passes 13/13 tests. Full-repository Ruff, scoped strict
Mypy, `py_compile`, preregistration `--check`, the feature-branch formal-command
negative check, and `git diff --check` pass. Local CPython 3.11.15, 3.12.12,
and 3.13.7 each pass the unified 648-test gate with four expected Windows
privilege skips, 53 audited source files, and `valid=true`.

PR #48 merged v2 as
`365935c02e16badec9ba40a3c4d078b66726f96e`. Its exact one-shot formal command
then consumed one owner-marked attempt and completed one fresh base load, one
independent read-only Adapter load, and all 56 ordered offline calls with zero
retry, network use, training, or Adapter write. The 6,644-byte execution
evidence has SHA-256
`87c45c9a174b9c6d0419f1d0ba9c619597848b13fe4447a19988e7a6ff56292c`.
It reports 32/56 overall accuracy, 28/28 hard-negative rejection, 4/28 clean
accept recall, 4/28 pair-exact accuracy, 52/56 compiler validity, 20 clean
false rejects, four invalid clean outputs, and zero hard-negative false
accepts. Formal-gate pass means measurement completion within caps, not
quality acceptance.

The independent model-free result review rebuilds that evidence byte-for-byte.
Its 18,220 canonical bytes have SHA-256
`711c1b52619d856015b832cd54a3bbfcaa419f360b95bf448d62de8230bdb720`.
The review establishes only the consumed execution and fixed-suite behavior;
quality improvement, generalized quality/safety, training, serving,
promotion, cross-machine/resource repeatability, and Runtime eligibility
remain false.
The focused result-review suite passes 12/12 tests. Full-repository Ruff,
scoped strict Mypy, `py_compile`, v2 preregistration `--check`, the default
result validator, and `git diff --check` pass. Local CPython 3.11.15, 3.12.12,
and 3.13.7 each pass the unified 660-test gate with four expected Windows
privilege skips, 53 audited source files, and `valid=true` without a model
reload or second attempt.

PR #49 merged that exact result review as
`c4ae93539fc0d65cf1274aa2916a5576b38b671d`. The merged feature branch was
deleted locally and remotely; the consumed MM-004 output remains unchanged and
was not reopened, reused, retried, or model-loaded.

`MM-005-multimodal-environment-adaptation-protocol-v1` now freezes the ordered
second environment as `document_chart_pdf` and bounds its first vertical slice
to English, synthetic, single-page document text, table-cell, bar-chart value,
and page-region evidence grounding. Only Environment Adapter, task set,
deterministic Verifier, and synthetic dataset are environment-specific;
training/evaluation orchestration, Serving/routing, policy, approval, WAL,
grounding authority, budgets, recovery, and desktop dispatch remain inherited.
No data, image, model call, training, capture, or Runtime change occurred.

The 49,202-byte canonical protocol has SHA-256
`311822603bb6c05c1b7f388cd782c30556fa8b7aa0d67cbd1ccd89f9d13a532a`. It
reconstructs 63 exact source receipts, including 52 historical images, and
recomputes shared cross-stage exclusion identities from actual MM-002 through
MM-004 content: 92 case/record IDs, 64 families, 64 instruction hashes, 64
observation hashes, 92 target hashes, and 52 image hashes. Its repeatability
claim is limited to byte-exact protocol/identity reconstruction and total
model-free verification; it is not a model-evaluation repeatability claim.

Fourteen focused tests, full-repository Ruff, scoped strict Mypy, `py_compile`,
builder `--check`, and `git diff --check` pass. Local CPython 3.11.15, 3.12.12,
and 3.13.7 each pass the unified 674-test gate with four expected Windows
privilege skips, 54 audited source files, and `valid=true`.
[Protocol](docs/MM-005-multimodal-environment-adaptation-protocol-v1.md).

PR #50 merged that bounded environment-adaptation protocol as
`9c57e32736e24bf120d827b0b7fef4dcf04f08b1`. Its feature branch was deleted
locally and remotely; `master` and `origin/master` were aligned before the
separate data preregistration began.

`MM-005-document-chart-pdf-data-protocol-v1` now freezes `seed=55005`, eight
template families per task (six train plus two validation), 32 records, 32
unique 1280x900 PNG page images, 14 deterministic single-page PDF source
artifacts, and all 49 future output receipts. The PDF and PNG for each
PDF-source template derive from one synthetic layout ground truth without an
external renderer, OCR, host font, network, or model dependency. Parent
record/exclusion validation, task/source coverage, split distributions,
family/template/content/image isolation, answer/evidence semantics, and exact
PNG/PDF bytes all pass in memory.

The 24,909-byte canonical data protocol has SHA-256
`7e774e69194e6f70c27c9b53bbab68adb19874780757717ca42012ec48297525`.
Its 49 planned outputs total 434,212 bytes, while the fixed output root and
execution evidence remain absent. Generation, dataset validation, Adapter,
Verifier execution, model, quality, safety, real/external content, capture,
Serving, promotion, and Runtime claims all remain false.

Fourteen focused data-protocol tests, full-repository Ruff, scoped strict
Mypy, `py_compile`, builder `--check`, and `git diff --check` pass. Local
CPython 3.11.15, 3.12.12, and 3.13.7 each pass the unified 688-test gate with
four expected Windows privilege skips, 55 audited source files, and
`valid=true`.
[Data protocol](docs/MM-005-document-chart-pdf-data-protocol-v1.md).

PR #51 merged that exact data protocol as
`3992778151bb7209c00c89e77e07894e075ff066`. Its feature branch was deleted
locally and remotely; `master` and `origin/master` were aligned before the
separate generation runner freeze began.

`MM-005-document-chart-pdf-data-generation-v1` now freezes a one-shot,
model-free runner around the unchanged data protocol. Its 17,780-byte
canonical protocol has SHA-256
`6e212237ee59d9730f97028769033a0991f9e3c6b893a404fc583274f813f2ed` and
binds four exact data/generation source receipts, the 24,909-byte data
protocol, and all 49 planned outputs / 434,212 bytes. The runner requires an
aligned merged `master`, absent output and evidence targets, zero internal
retries, atomic staging-root publication, exact-tree rejection, persisted-byte
readback validation, and exclusive evidence creation.

At runner freeze, the real output root and evidence were absent; generation,
records/images, dataset validation, Adapter, Verifier, model, quality, safety,
real/external content, capture, Serving, promotion, and Runtime claims were
false. Fourteen focused generation tests, full-repository Ruff 0.15.22, scoped
strict Mypy 2.3.0, `py_compile`, protocol `--check`, and `git diff --check`
passed.
[Generation protocol](docs/MM-005-document-chart-pdf-data-generation-protocol-v1.md).

PR #52 merged that exact runner freeze as
`fbf1c64398d89c35e95f80322fd665ae3c2f2c1d`. Its feature branch was deleted
locally and remotely, and `master == origin/master` was restored before the
registered invocation. That invocation executed exactly once with no retry
and independently validated 49 output files / 434,212 bytes: 24 train and 8
validation records, 32 PNGs, 14 single-page PDFs, and three dataset JSON files
of 65,327, 22,490, and 14,789 bytes.

The 16,680-byte execution evidence has SHA-256
`a11a373a6c7d49b02470a84d9c303cb4f424ff6693dcc516ef8060af032d649f`.
All 16 registered execution gates are true. Only generation, records, images,
and dataset validation are established; Adapter/Verifier, model, quality,
safety, real/external content, capture, Serving, promotion, and Runtime claims
remain false. After result-aware assertions, the 14 focused generation tests
pass, and local CPython 3.11.15, 3.12.12, and 3.13.7 each pass the unified
702-test gate with four expected Windows privilege skips, 56 audited source
files, and `valid=true`.

PR #53 published those exact consumed outputs and evidence as
`3ae49d372b5184418e8353630336fdb802182cbd`. All six Linux Python-matrix checks
passed with review and conflict state clear; both feature-branch copies were
deleted and `master == origin/master` was restored. The unified workflow now
fetches full history because the result gate must read and compare the
evidence-bound generation freeze commit. No generated byte was retried or
rewritten.

`MM-005-document-chart-pdf-adapter-verifier-protocol-v1` is now frozen and
validated locally before implementation. Its 126,032-byte canonical artifact
has SHA-256
`4715134d7bd1f8ae54275764f342bf5a8974cc491298dbefd52971aab876c64a` and
binds eight exact source receipts, the consumed generation evidence and all
upstreams/outputs, 32 deterministic Adapter projection receipts, and 160
Verifier cases: 32 positive and 128 negative controls. The model payload is
closed to `instruction`, `observation`, `source_kind`, and `task_family_id`;
gold, identity, split, provenance, Verifier metadata, and real image paths stay
outside it. The compiler is strict JSON and the Verifier is deterministic with
no model judge.

Thirty-eight focused MM-005 tests, full-repository Ruff 0.15.22, scoped strict
Mypy 2.3.0, `py_compile`, protocol `--check`, and `git diff --check` pass. Local
CPython 3.11.15, 3.12.12, and 3.13.7 each pass the unified 712-test gate with
four expected Windows privilege skips, 57 audited source files, and
`valid=true`. This establishes protocol/fixture reconstruction only. Adapter/
Verifier implementation/execution, model/training repeatability, quality,
safety, Serving, promotion, and Runtime claims remain false.
[Adapter/Verifier protocol](docs/MM-005-document-chart-pdf-adapter-verifier-protocol-v1.md).

PR #54 merged that exact protocol as
`db8c6833f43c02a0b255c436558e0269a8bde3b4`. All six Linux Python-matrix
checks passed; the PR had zero reviews, comments, or review threads and was
`CLEAN`/`MERGEABLE`. Both feature-branch copies were deleted and
`master == origin/master` was restored before implementation began.

`MM-005-document-chart-pdf-adapter-verifier-implementation-v1` is now
implemented and validated locally. Its independent Adapter exposes canonical
model payload JSON and exact image bytes while keeping the real path, receipts,
and authority metadata audit-only. Missing, duplicate, tampered, non-byte,
absolute, and traversal image bindings fail closed. The independent strict
compiler/Verifier does not call the frozen reference implementation and
matches all 32 projection receipts and 160 case outcomes exactly: 96 compiler-
valid, 64 invalid, 32 positive, 128 negative, and zero mismatch.

The 102,117-byte implementation evidence has SHA-256
`d4cbe61cac4cff60c15e769c35e481ca93f71524b23bf0dad4ddf75095d17bf2`.
It binds five exact implementation/protocol source receipts, the protocol merge
commit, immutable consumed inputs, 32 Adapter executions, and 160 Verifier
executions. Environment Adapter implementation/execution and deterministic
Verifier implementation/execution are now true. Model training/evaluation,
repeatability, quality, safety, Serving, promotion, Runtime change, and Runtime
eligibility remain false.

Twelve implementation-focused tests and the complete 50-test MM-005 chain,
full-repository Ruff 0.15.22, scoped strict Mypy 2.3.0, `py_compile`, builder
`--check`, and `git diff --check` pass. Local CPython 3.11.15, 3.12.12, and
3.13.7 each pass the unified 724-test gate with four expected Windows privilege
skips, 59 audited source files, and `valid=true`.
[Adapter/Verifier implementation](docs/MM-005-document-chart-pdf-adapter-verifier-implementation-v1.md).

PR #55 merged that exact implementation and evidence as
`ff52da51aba534b051f9e247518fb2d20d1db1e2`. All six Linux Python-matrix checks
passed; the PR had zero reviews, comments, or review threads. Both feature-
branch copies were deleted and `master == origin/master` was restored before
the model-evaluation protocol slice began.

`MM-005-document-chart-pdf-model-evaluation-protocol-v1` froze before any model
import or call. Its 58,414-byte canonical artifact has SHA-256
`cdb8d1ea09221763d87cd79ba752d9af8264ce49b7cf600eed338a073a04561b`.
It binds the exact Qwen2.5-VL base revision plus read-only MM-003 Adapter, the
MM-004 candidate result lineage, the merged MM-005 Adapter/Verifier evidence,
all consumed dataset outputs, and 12 protocol source receipts. All 32 records
are ordered once; their closed model payloads total 31,430 bytes and exact
image payloads total 314,128 bytes, with gold, Verifier metadata, identity, and
real paths isolated from the model.

The formal run was pre-registered for one fresh base load, one
independent Adapter load, 32 ordered offline calls, zero retry/training/write,
1,800 seconds, and 16.5 GB peak allocated/reserved GPU memory. Strict compiler,
deterministic Verifier, total metrics, owner-marked attempt consumption, and
mutually exclusive terminal evidence/failure receipts are fixed before the
result. PR #56 merged the exact protocol as
`3be0083c3197111d57a4a5e5f70feced9f2c96f9`: all six Linux Python-matrix
checks passed, the PR had zero reviews, comments, or review threads, and both
feature-branch copies were deleted before execution.

The exact merged-master invocation then consumed the single registered
owner-marked attempt. It completed one fresh base load, one independent
read-only Adapter load, and 32/32 ordered offline calls with zero retry,
network, training, or Adapter write. The formal measurement gate passed in
`216.03030519999447` seconds with `6,458,204,160` peak allocated and
`6,777,995,264` peak reserved CUDA bytes, within the registered caps.

The fixed-suite result has compiler validity 28/32, answer and joint exact
19/32, evidence and page exact 28/32, and four compiler-invalid outputs. Chart
and table are each 8/8 joint exact, document text is 0/8, and page-region
selection is 3/8. The exact 13-case failure taxonomy is nine compiler-valid
answer-only errors plus four compiler-invalid outputs.

The independent model-free review rebuilds the candidate, predictions,
Verifier/scorer evidence, and review byte for byte. The four execution
artifacts are 656 / 32,190 / 18,543 / 7,495 bytes with SHA-256
`ca9e420fbce5582cab5944e0c290e569f97cad85ad3a5cf9e3c53aa13989d00b`,
`e26f6a9ca03e826f627ae90aca5b2fdcf5bbed770d9752aa9ba74982ed7d12ea`,
`f9a545175688451fc5025eb1e90a1e1354a59c536887a54fe62deb80a019fff7`,
and `5e330dde1debe7a207638d164aade8ab2c63fbcd8149b3178d64a16afd0fc78e`.
The 15,235-byte result review has SHA-256
`7cc4990f900787123f078d2387855e4708b5eadb8d6705bb6364d8cab2f935a7`.

Protocol/result-focused tests pass 15/15 and 12/12; the complete MM-005 chain
passes 91/91. Full Ruff, scoped strict Mypy, `py_compile`, default result
validation, and `git diff --check` pass. Local CPython 3.11.15, 3.12.12, and
3.13.7 each pass the unified 751-test gate with four expected Windows
privilege skips, 60 audited source files, and `valid=true`, without a model
reload or second attempt. This establishes only a completed fixed-suite
measurement. Quality, safety, same-machine evaluation repeatability,
training/resource repeatability, cross-machine reproducibility, Serving,
promotion, Runtime change, and Runtime eligibility remain false.
[Model-evaluation protocol](docs/MM-005-document-chart-pdf-model-evaluation-protocol-v1.md).
[Result review](docs/MM-005-document-chart-pdf-model-evaluation-result-review-v1.md).

PR #57 merged those exact consumed artifacts and the independent review as
`056eb8d050eb0f0491ff21a07bd5b7716abf7eb8`. All six Linux Python-matrix
checks passed; the PR had zero reviews, comments, or review threads, and both
feature-branch copies were deleted before repeatability protocol work began.

`MM-005-document-chart-pdf-model-evaluation-repeatability-protocol-v1` froze
the unchanged candidate, registered environment, 32-case order, prompts,
images, compiler, Verifier, metrics, generation settings, resource caps, and
12-source execution closure before any second model import or call. Its 47,974-
byte canonical preregistration has SHA-256
`4c5186cbfa542125d4f2b96dae14e31955effa330c42951f993413d276962ed7`.
PR #58 merged the freeze as
`874f6c1a201a07d6680a3fa12217c1344b14c141`; all six Linux Python-matrix
checks passed, the PR had zero reviews/comments/threads and no conflict, and
both feature-branch copies were deleted before replay execution.

The exact aligned-master command then consumed the one registered replay. It
loaded one fresh base and one independent read-only Adapter, completed all 32
ordered offline calls, and used zero retry/network/training/write. All ten
formal gates passed. Raw UTF-8, compiled JSON, Verifier verdicts, and generated-
token counts are each exact for 32/32 cases with zero mismatch; total metrics
are exact. The 20,952-byte evidence SHA-256 is
`659ea12140a85c044be1cdd0bf1ab867cbbdff2a097fbd447e07ec3b84e81617`.

Replay elapsed time is `201.59785200000624` seconds and peak CUDA allocated/
reserved are `6,458,204,160` / `6,777,995,264` bytes. Both runs are within
caps and their GPU peaks match, but baseline elapsed time is
`216.03030519999447` seconds. Resource equality is therefore false and remains
diagnostic-only; resource repeatability is not established.

The independent model-free review rebuilds the evidence byte for byte. Its
18,817 canonical bytes have SHA-256
`c5b5f12dfaffb387ca7e394c8acbd2b92fc00e3a256ed8cab0d4e624b28d0ec8`.
It establishes only bounded same-machine, registered-environment-field,
fixed-32-case evaluation repeatability. The runner enforced its live
environment mapping before generation, but that exact mapping was not
separately persisted; token IDs and per-case latency are not registered
repeatability layers. Training/resource repeatability, cross-machine
reproducibility, generalized quality, quality improvement, safety, real-
content behavior, Serving, promotion, and Runtime claims remain false.

The new result-review suite passes 13/13 and the complete MM-005 chain passes
120/120. Full Ruff, scoped strict Mypy, `py_compile`, the default validator,
the unified result subcheck, and `git diff --check` pass. Local CPython 3.11.15,
3.12.12, and 3.13.7 each pass the unified 780-test gate with four expected
Windows privilege skips, 61 audited source files, and `valid=true`, without a
model reload or second replay.
[Repeatability protocol](docs/MM-005-document-chart-pdf-model-evaluation-repeatability-protocol-v1.md).
[Repeatability result review](docs/MM-005-document-chart-pdf-model-evaluation-repeatability-result-review-v1.md).

PR #59 published the exact replay artifacts, independent review, and strict
validator as `5f60cbf44a311b46b312090d62d2783424c1dc85`. All six Linux
Python-matrix checks passed; the PR had zero reviews/comments/threads, was
`CLEAN`/`MERGEABLE`, and both feature-branch copies were deleted before local
`master` was aligned with `origin/master`.

`MM-005-browser-research-environment-adaptation-protocol-v1` is now frozen
locally before data, live browser/network use, model calls, training, Serving,
capture, or Runtime change. The 76,364-byte canonical protocol SHA-256 is
`62ef6c554c90d3523b7d9c2a0a102c2a8c783f3d3ba3496cd8c36dfebe04b06e`.
It binds the closed Document/Chart/PDF lifecycle and 102 exact source receipts,
then recomputes exclusions for 124 prior records, 96 families, 96 instruction/
observation identities, 124 target identities, and 84 images.

The bounded static synthetic slice aligns DOM, screenshot, and page text for
one to three sources and requires exact source-bound citations. Its four task
families are single-source fact, multi-source synthesis, cross-source
comparison, and freshness-conflict resolution. Live retrieval/navigation,
dynamic/authenticated/transactional pages, real/external content, and prompt-
injection safety claims remain deferred. Seventeen focused tests, Ruff, strict
Mypy, `py_compile`, builder `--check`, and the unified Browser Research
subcheck pass locally. CPython 3.11.15, 3.12.12, and 3.13.7 each pass the
complete unified 797-test gate with `valid=true`, four expected Windows
privilege skips, and 62 audited source files.
[Browser Research protocol](docs/MM-005-browser-research-environment-adaptation-protocol-v1.md).

PR #61 published the exact protocol as
`d7e7b7f70ff298a47244c34cc22173c70c65e6c9`. All six Linux Python-matrix
checks passed; the PR had zero reviews, issue comments, review comments, or
review threads, was `CLEAN`/`MERGEABLE`, and both feature-branch copies were
deleted before local `master` was aligned with `origin/master`.

`MM-005-browser-research-data-protocol-v1` is now frozen locally before any
Browser Research record, static source snapshot, or screenshot is
materialized. Its seed is `55006`; each of four task families has eight unique
templates (six train plus two validation), yielding 32 records and explicit
one-to-three-source bundles with 68 sources total (51 train, 17 validation).
The 68 canonical static-source JSON descriptors and 68 unique 1280×900 PNGs
derive from the same DOM ground truth; page text is the visible DOM text in
order. No executable HTML, browser engine, JavaScript, network, host font,
model, OCR, capture, or Runtime path is used.

All 139 future outputs (68 snapshots, 68 PNGs, two split datasets, and one
manifest) rebuild in memory to 986,989 bytes with exact path/byte/SHA-256
receipts. The fixed output root and execution evidence remain absent. The
73,476-byte canonical protocol SHA-256 is
`38e31afc46cf92603d191563bc5460062adeb702e7df3ee4ff18f485b034283a`.
Fourteen focused adversarial tests, Ruff, scoped strict Mypy, `py_compile`,
builder `--check`, and `git diff --check` pass. Local CPython 3.11.15, 3.12.12,
and 3.13.7 each pass the complete unified 811-test gate with four expected
Windows privilege skips, 63 audited source files, and `valid=true`. Generation,
dataset validation, Adapter/Verifier execution, live browser/network use,
model/quality/safety, Serving, promotion, and Runtime claims remain false.
[Browser Research data protocol](docs/MM-005-browser-research-data-protocol-v1.md).

## Single active objective

Publish the exact locally frozen `MM-005-browser-research-data-protocol-v1`
without materializing any Browser Research record or image:

```text
frozen 73,476-byte protocol + 139 exact planned-output receipts
        -> review scoped diff and preserve user-owned AGENTS.md
        -> required checks + review/comment/thread/conflict audit
        -> clean merge, delete both branch copies, align master
```

Do not delete, reopen, reuse, overwrite, or retry either consumed MM-005
evaluation directory. The data-protocol slice must preregister exact planned
outputs and validation without generating them. It must not access a live
browser or network, import/load/call a model, train or save a model/Adapter,
change the Runtime repository, capture real browser/desktop/document content,
or broaden prior repeatability claims. Materialization is authorized only
after this exact data protocol cleanly merges, both branch copies are deleted,
and `master == origin/master`.

## Preserved historical validation and deferred gates

Fourteen focused generation/result tests, Ruff 0.15.22, scoped strict Mypy
2.3.0 on the typed contract/runner, `py_compile`, and preregistration `--check`
pass. The unified offline gate passes on local CPython 3.11.15, 3.12.13, and
3.13.7; each reports 635 tests, four expected Windows privilege skips, 52
audited source files, and `valid=true`.
[Generation protocol](docs/MM-004-multimodal-hard-negative-data-generation-protocol-v1.md).

The completed protocol is 22,675 canonical bytes with SHA-256
`f31e009ed8316d59240e9767865a041e86f30325a1fd15f8a29891d56d418355`.
Ten focused adversarial tests, Ruff, scoped strict mypy, and `prepare --check`
pass. The unified offline gate passes on CPython 3.11.15, 3.12.12, and 3.13.7;
each reports 621 tests, four expected Windows privilege skips, 51 audited
source files, and `valid=true`.
[Protocol](docs/MM-004-multimodal-hard-negative-data-protocol-v1.md).

The previously active
`FC-MVP-001-fp32-attached-portable-package-qualification-v1` protocol remains
frozen and deferred. Resume it only by executing its existing runbook on one
operationally distinct native Windows host satisfying the locked environment
and same GPU class; local controller paths and WSL remain ineligible.

The portable-package qualification protocol was frozen before any target
result at `f8dc9a62471759282ad2b41673d95acd43bf240f`. Its 7,095-byte
preregistration has SHA-256
`eceb47c9c952b8ba056abee48a2d55be797145558ac5efcede69d97b9a834577`.
It reuses the exact clean-location replay gate and requires all 13 categorical
requirements to pass on one operationally distinct native Windows target
under the locked user-space environment, same GPU class, fixed compiler, and
attached execution form.

The target-side receipt stores only domain-separated SHA-256 values for
Windows MachineGuid and NVIDIA GPU UUID, requires both plus their combined
identity to differ from the controller anchor, and binds them to the new target
replay/evidence bytes. The receipt is self-observed operational evidence, not
hardware-backed remote attestation; the controller anchor is not historical
attestation of prior reference execution. WSL or a second path on the current
controller is explicitly ineligible.

The frozen protocol passes 421 tests with `valid=true` and audits 36 source
files on CPython 3.11.15, 3.12.12, and 3.13.7. The 18 focused tests, Ruff,
strict mypy on the new contract/builder, py_compile, preregistration
recomputation, and diff checks pass. No independent target GPU machine or
repository self-hosted runner was available, so no target replay or formal
qualification artifact was generated. The exact portable-gate resume action
remains executing the frozen runbook on one independent qualifying host;
cross-machine and portable-package claims remain false until that evidence
validates.
[Protocol](docs/FC-MVP-001-fp32-attached-portable-package-qualification-v1.md).

`MM-003-small-vlm-post-training-protocol-v1` froze locally on 2026-08-17
before any registered training. Its 17,601-byte preregistration has SHA-256
`9dfd180f24a86814fc32c5ebbfca07a31f713c8387f85ec3212dc538647cb061` and
binds ten protocol sources, the exact 14-file model snapshot, a dedicated
dependency lock, and the 37,961,070-byte bitsandbytes 0.50.1 Win64 wheel with
SHA-256
`86f76e8a3278fbbfc3fa0d79d1c4e706ebc214babd57f0ea30e2da509bbdaad5`.

The deterministic training-only inputs contain 18 train and 9 validation
records across the full three observation modes × three dispositions grid,
plus 18 unique synthetic screenshots. Exact-identity isolation against the
unchanged nine-case MM-002 eval reports empty case/family/instruction/input/
target/screenshot overlap sets; train and validation families are also
disjoint. All 27 targets compile exactly under the frozen strict compiler.

The local compatibility smoke uses the registered NF4, BF16 compute, rank-16
LoRA, and non-reentrant gradient-checkpointing path without eval data or an
Adapter save. It records 414 `Linear4bit` modules, 7,372,800 trainable
parameters, finite loss, nonzero finite LoRA gradients, and peak CUDA
allocated/reserved 3,941,332,480 / 4,273,995,776 bytes. This is backend
compatibility only, not training or model quality evidence.

Before any formal training invocation, a read-only execution audit found that
the initial runner's failure receipt covered training and later stages but not
the registered preflight. The hardened freeze exclusively creates the fixed
run directory before preregistration/source/wheel/input/model/dependency/
environment checks, records a stage-specific fail-closed receipt for any later
exception, and starts the measured train/eval timer at that boundary. The timer
stops after synchronized post-score resource sampling; evidence construction,
serialization, and persistence remain fail-closed but are explicitly outside
that elapsed metric. CLI syntax, output-path, and pre-existing-directory
rejection remain outside the consumed lifecycle.

Focused 13 tests, deterministic fixture rebuild/check, Ruff, `py_compile`,
preregistration recomputation, and `git diff --check` pass. CPython 3.11.15,
3.12.12, and 3.13.7 all pass the unified 531-test gate with `valid=true`, four
expected Windows privilege skips, and 47 audited source files. Training, Adapter creation and
loadability, model evaluation, quality improvement, repeatability,
cross-machine reproducibility, portability, commercial use, serving,
promotion, and Runtime claims remained false at that protocol-freeze gate. Its
exact next gate at that time was
`MM-003-small-vlm-post-training-execution-v1`, allowed only after the frozen
protocol merged.
[Protocol](docs/MM-003-small-vlm-post-training-protocol-v1.md).

`MM-003-small-vlm-post-training-failure-classification-v1` completed locally
on 2026-08-17 after the one registered v1 execution. The exact 897-byte raw
receipt has SHA-256
`8c82455b406c66a038deaaadeb9251b9eb626145a5f31d36b04d5ad7d10c72d9`
and binds freeze commit `a882e6096a87e475511890be9fc804a468143868`, the
17,601-byte preregistration, `stage=training`, `MM003ProtocolError`, zero retry,
and all result/eligibility claims false. The output directory contains only
that receipt.

The 15,877-byte derived classification has SHA-256
`66b9e8352caacd1a10e750a222ce2a0a7994df385e23e31dbc76a68b6109aef6`
and report digest
`sha256:85fddade5e6a3c665771c6cb74c5e610f003817b3eddf5a21f1b2a070ea1dd53`.
Model-free recomputation proves all 27 `pt-*` records fail because the v1
renderer reused the nine-case `ground-*` registry; the frozen first record is
`pt-train-018/fused`. This is a pre-forward training-prompt contract failure,
not invalid fixture mode, CUDA, checkpoint, optimizer, or scoring evidence.
Both tracked fixture receipts are read directly. The recovery whitelist locks
the v1 model, dependencies/environment, fixtures/targets, training,
eval/reload, Adapter, caps, claims, and authority subtrees plus the exact v2
protocol/execution/experiment/output/success-next identities. Focused 6 tests
and the CPython 3.11.15/3.12.12/3.13.7 unified 537-test gates
pass with `valid=true`, four expected Windows privilege skips, and 48 audited
source files. The exact next gate is
`MM-003-small-vlm-post-training-recovery-protocol-v2`.
[Evidence](docs/MM-003-small-vlm-post-training-failure-classification-v1.md).

`MM-003-small-vlm-post-training-recovery-protocol-v2` froze locally on
2026-08-17 before any v2 model or GPU execution. Its 26,553-byte
preregistration has SHA-256
`02e36d5981e0ed4ac90bfdb3c5cc9c9e1f78ff29ff927020b0a41ebb27f55c0e`.
It exact-binds the v1 preregistration, raw failure receipt, derived
classification, and all ten v1 protocol-source receipts. A recursive,
type-strict leaf comparator permits exactly 12 registered replacements, two
named v2 source additions, and four closed new sections; every unlisted
change/addition/removal or container replacement fails closed.

The separate post-training case/mode registry covers all 18 train plus 9
validation records without mutating the baseline `ground-*` registry. The
projector explicitly constructs only case/mode/instruction/tools/observation
fields, excludes family/repeat/target/raw screenshot-region data, and retains
registered PNGs as separate processor image inputs. All 27 prompts are rendered
and receipt-bound before dependency import, CUDA access, or model load. Their
domain-separated aggregate digest is
`sha256:bcbf8e87674ce2a668bdfe54ff4ecaba2e6db36899fc4e7c563867d1e2e9e102`.

The model/revision and 14-file snapshot, dependency wheel and lock, fixtures,
targets, seed, NF4/BF16 QLoRA hyperparameters, independent Adapter reload,
unchanged MM-002 eval, resource caps, and authority boundary remain identical
to v1. The versioned runner uses a dedicated v2 output directory, sanitized
failure diagnostics, zero retry, and a new prompt-totality gate for 13 required
formal gates. At freeze, all training/Adapter/eval/quality/repeatability/
portability/serving/promotion/Runtime claims remain false.
Failed formal evidence records no success next gate; only an all-true formal
measurement may route to result-review-v2.

Focused 23 tests pass on CPython 3.11.15, 3.12.12, and 3.13.7. All three
interpreters also pass the unified 560-test gate with `valid=true`, four
expected Windows privilege skips, and 49 audited source files. Exact
preregistration recomputation, Ruff, `py_compile`, scoped strict mypy on the
typed v2 contract, and `git diff --check` pass. At that freeze no model or GPU
was loaded and the fixed v2 output directory was absent. Its exact next gate
was `MM-003-small-vlm-post-training-execution-v2`; if that
one-shot measurement passes, its success-only next gate is
`MM-003-small-vlm-post-training-result-review-v2`.
[Protocol](docs/MM-003-small-vlm-post-training-recovery-protocol-v2.md).

`MM-003-small-vlm-post-training-execution-v2` completed once locally on
2026-08-20 against recovery-protocol merge commit
`3751a041ff12886a337df0066232379016fdbd9c`. One fresh training-model load ran
three QLoRA epochs and 18 optimizer steps, saved the exact three-file Adapter,
then one fresh base load plus one independent Adapter load made nine ordered
MM-002 calls. Zero retries and no execution network were recorded. All 13
formal gates pass; elapsed time was `130.3286408999993` seconds and peak CUDA
allocated/reserved memory was `6,486,660,096` / `7,153,385,472` bytes, within
the registered caps.

The 29,529,752-byte safetensors Adapter has SHA-256
`d93d2ea2d9f05564093cbb0b1286d2c368c54b01e847f1c37a98e00fb2914701`,
288 finite F32 tensors, and 7,372,800 parameters. The nine predictions bind
their producer to this Adapter identity and frozen model revision. The strict
compiler accepted all nine outputs. Relative to the frozen zero-shot baseline, Grounding changes
from `0/5` to `3/5`, Action from `0/9` to `3/9`, and Tool/Argument from `0/5`
to `5/5`. Stale-ref rejection remains `0/2` and coordinate/ref disagreement
rejection remains `0/1`.

`MM-003-small-vlm-post-training-result-review-v2` freezes the raw training,
prediction, evidence, and Adapter bytes plus an 11,311-byte review artifact
with SHA-256
`3dff57b17eb4fc9966ab53fe92faea8921fb34b485e389aaa19af64610db957d`.
Its complete six-case taxonomy is: fused grounding missing bbox on
`ground-003/006`; reject downgraded to fallback on `ground-004/007/009`; and
fallback-reason vocabulary mismatch on `ground-005`. This is review-only and
does not authorize copying eval answers into training. Generalized quality,
rejection safety, training/eval repeatability, cross-machine, portable,
commercial, serving, promotion, direct execution, and Runtime claims remain
false. The exact next gate is
`MM-003-small-vlm-post-training-eval-repeatability-protocol-v1`.
[Evidence](docs/MM-003-small-vlm-post-training-result-review-v2.md).

The focused 11-test result-review suite and unified 571-test gate pass
locally on CPython 3.11.15 and 3.13.7 with `valid=true`, four expected Windows
privilege skips, and 49 audited source files. Full-repository Ruff, Python 3.11
`py_compile`, and `git diff --check` pass. The pull-request Linux matrix remains
responsible for the independent CPython 3.12 result.

`MM-003-small-vlm-post-training-eval-repeatability-protocol-v1` froze locally
on 2026-08-21 before any repeat model/GPU execution. Its 22,951-byte
preregistration has SHA-256
`723db665f98e53ef2fe968ee7c6fe663b42d79b86176eef5cf70f11ccc4a312b`.
Seventeen source receipts bind the actual import/validation graph, exact model
snapshot and three-file Adapter, unchanged MM-002 suite/screenshots/prompt/
compiler/generation/environment, one fresh base-plus-read-only-Adapter load,
nine ordered offline calls, zero retry/training/write, inherited 1,800-second/
16.5-GB caps, and 13 outcome-neutral formal gates. Raw outputs, recompiled
predictions, and recomputed metrics compare independently; equality is not an
execution threshold.

The owner marker was written in a random same-parent staging directory before
the fixed output was atomically claimed as the one-shot boundary. The protocol
slice passed 29 focused tests and 600-test unified gates before merge. Its one
formal replay later completed with 13/13 gates, raw and compiled 9/9 exact,
metrics exact, generated-token counts exact, and no retry. The frozen four
execution artifacts are 586 / 9,855 / 2,241 / 20,243 bytes with SHA-256
`8f6c267ab262021ac6b8805606b9a7e7bb071507968e5d94a0c4b25eadb3d7fb`,
`a354f4b3f2b20467ed7d82916345f7b951ca6df1ad9ecc5816734410694e155b`,
`c2c703e5896fe64df9e156bda9d38975b92c1bf18c72f74f5a232dcbbbc4a028`,
and `e20262debfbefa3e361855728aa8852f1219053d6fb9152158a2916c806a7ad2`.
The 15,119-byte result review has SHA-256
`8979693b6962849555e533332331d91dbb9fad8294f7fbc6703fa09ab3414f4a`.
Only bounded same-machine fixed-eval repeatability is established; token-ID,
training, resource, cross-machine, generalized-quality, serving, promotion,
and Runtime claims remain false. The consumed output must never be deleted,
reused, or retried. The exact next gate is
`MM-004-multimodal-hard-negative-data-protocol-v1`.
[Protocol](docs/MM-003-small-vlm-post-training-eval-repeatability-protocol-v1.md).
[Result review](docs/MM-003-small-vlm-post-training-eval-repeatability-result-review-v1.md).

The focused result-review suite passes 11/11 tests on local CPython 3.11.15,
3.12.12, and 3.13.7. Each unified gate passes 611 tests with `valid=true`, four
expected Windows privilege skips, and 50 audited source files. Full-repository
Ruff, scoped strict mypy on the new validator, `py_compile`, protocol
`prepare --check`, default result validation, and `git diff --check` pass.

`MM-003-local-small-vlm-baseline-recovery-protocol-v2` froze locally on
2026-08-17 before any v2 model execution. Its 13,349-byte preregistration has
SHA-256
`369c813dee44b14c6022eb90739bcd37f9f8de472e60a8cee88682454d135403`.
It binds the unchanged v1 model/input/prompt/compiler/generation facts, six
base/recovery sources, and the exact v1 failure artifact. Only the auxiliary
prediction disagreement diagnostic gains explicit `not_applicable` semantics
for a zero denominator; all core denominators remain positive-required. The
runner writes exclusive raw run and compiled prediction artifacts before
scoring and writes a failure receipt if scoring raises.

Focused 8 tests, Ruff, strict mypy, `py_compile`, model/source hash checks, and
preregistration recomputation pass. CPython 3.12.12 passes the unified 514-test
gate with `valid=true` and 46 audited source files. At protocol freeze, no v2
run or model metric existed and the exact next gate was
`MM-003-local-small-vlm-baseline-execution-v2`.
[Protocol](docs/MM-003-local-small-vlm-baseline-recovery-protocol-v2.md).

`MM-003-local-small-vlm-baseline-execution-v2` completed once locally on
2026-08-17 against the tree of merge commit
`9702c92c37f18c32a7458cbb2fa3c6d2e75e0490`. One fresh load produced nine
ordered calls with zero retries and no execution network. All 12 formal gates
passed; elapsed time was `41.921435199998086` seconds, peak CUDA allocated was
`11,616,626,688` bytes, and peak reserved was `12,010,389,504` bytes, all
within registered caps.

The strict compiler produced 9/9 fallbacks. Grounding was `0/5`, Action `0/9`,
Tool `0/5`, and Argument `0/5`; every observation mode was `0/3` with 3/3
fallback. The auxiliary disagreement metric was explicitly `not_applicable`.
This is a passed measurement gate and a negative quality baseline, not a model
quality pass. The run/predictions/evidence artifacts are respectively
14,715/2,058/4,680 bytes with SHA-256
`173bb4ab17fa5d6c02323f9cc26e8cddd93525055a712b8f6c5cd5c09cb2a57c`,
`57629229e4416cb7562382b57ee6774845dbd4f1da97b73a1e54d2a2f8ea17f7`, and
`a0e3c2503e5bac13bf979c7721dab4350681a84883d749b94ef3ca204d2166fe`.

Four focused result tests and the CPython 3.12.12/3.13.7 unified 518-test gates
pass with `valid=true` and 46 audited source files. `baseline_executed=true` and
`model_evaluated=true` are limited to this synthetic baseline; training,
Adapter loadability, promotion, serving, cross-machine, commercial, and Runtime
claims remain false. The exact next gate is
`MM-003-small-vlm-post-training-protocol-v1`.
[Evidence](docs/MM-003-local-small-vlm-baseline-v2.md).

`MM-003-local-small-vlm-baseline-failure-classification-v1` completed locally
on 2026-08-17. The one registered attempt used merge commit
`759a4ea2cbc6b45c78451bcbcdf2c26271c7af78`, completed the fresh load and nine
generation calls by exact control-flow evidence, then failed in
`score_predictions` with `EMPTY_METRIC_DENOMINATOR at $report.metrics` for
`prediction_coordinate_ref_disagreement_rate`. No retry occurred. Because v1
writes only after scoring, its output directory remained absent; raw outputs,
compiled predictions, latency, resources, and MM-002 metrics are unavailable
and were not reconstructed.

The 4,480-byte failure classification has SHA-256
`fc8ef58286f425c03e8f20148c1b2b014c29be4468b61f8c0e650f507ec2dce6`.
It binds the exact preregistration and v1 contract/runner/scorer hashes;
`formal_gate_passed=false`, `baseline_executed=false`,
`model_evaluated=false`, and `runtime_eligible=false`. Focused 4 tests, Ruff,
artifact recomputation, and the 506-test unified gate pass with `valid=true`
and 44 audited source files. The exact next gate is
`MM-003-local-small-vlm-baseline-recovery-protocol-v2`.
[Evidence](docs/MM-003-local-small-vlm-baseline-failure-classification-v1.md).

`MM-003-multimodal-gui-action-model-v1` has its outcome-neutral baseline
protocol frozen locally on 2026-08-17. The 11,151-byte preregistration has
SHA-256
`0046143f2c8badb5b2eaa809ac4c7abce81d1c0a5156fe2668b4e5cf9668aa10`.
It pins Qwen2.5-VL-3B-Instruct revision
`66285546d2b821cf421d4f5eb2576359d3770cd3`, all 14 model files, the exact
local Transformers/BF16/SDPA environment, the unchanged MM-002 suite and
prediction schema, six deterministic synthetic PNGs, filtered prompts, strict
compiler, nine-call order, zero retries, and elapsed/CUDA memory caps.

One unrelated blank-image compatibility smoke returned `READY` in
`4.989717400007066s` with two generated tokens, peak CUDA allocated memory
`7,953,781,760` bytes, and peak reserved memory `8,311,013,376` bytes. It did
not load any MM-002 case and is not model-evaluation evidence. The focused
eight tests, Ruff, strict mypy, py_compile, preregistration/model/image hash
checks, and deterministic visual-input review pass. CPython 3.11.15, 3.12.12,
and 3.13.7 each pass the unified 502-test gate with `valid=true`, four Windows
symlink-privilege skips, and 43 audited source files.

At that protocol gate no formal MM-002 model output had been generated:
`baseline_executed=false`,
`model_evaluated=false`, `training=false`, and `runtime_eligible=false`. The
`qwen-research` license restricts this gate to non-commercial research or
evaluation and does not authorize serving or promotion. Its registered next
gate was `MM-003-local-small-vlm-baseline-execution-v1`; that attempt is now
closed as a failed, non-retried execution above.
[Protocol](docs/MM-003-multimodal-gui-action-model-v1.md).

`MM-002-gui-grounding-data-eval-v1` completed locally on 2026-08-17. The
frozen synthetic-only eval split contains nine unique cases and families
covering ref/bbox/fused grounding, UIA/screenshot/fused observations,
clean/missing/noisy OCR, and none/moved/occluded/stale/disagreement
perturbations. Gold stays structurally separate from model input and training
use is prohibited. Two closed Draft 2020-12 schemas, a strict validator,
deterministic scorer, CLI, and frozen report are bound by bytes and SHA-256.

The deliberately imperfect synthetic probe scores Grounding Accuracy `4/5`,
mean IoU `19/20`, Action Accuracy `6/9`, Tool Accuracy `5/5`, Argument Exact
Match `4/5`, stale-ref rejection `1/2`, coordinate/ref disagreement rejection
`0/1`, and prediction disagreement rate `2/3`. These are scorer test vectors,
not model results: `model_evaluated=false`, `training_eligible=false`,
`execution_eligible=false`, and `runtime_eligible=false`.

The unified CPython 3.11.15, 3.12.12, and 3.13.7 gates each pass 494 tests
with `valid=true` and audit 42 source files. The focused 26-test suite, Ruff,
strict mypy, `py_compile`, independent JSON Schema checks, frozen report
recomputation, and artifact hash checks pass. A final no-dependency wheel
contains both GUI grounding modules and the `fullcycle-gui-grounding-eval`
entry point. The exact next gate is
`MM-003-multimodal-gui-action-model-v1`.
[Evidence](docs/MM-002-gui-grounding-data-eval-v1.md).

`MM-001-multimodal-trajectory-schema-v1` completed locally on 2026-08-17.
Its strict standard-library validator and closed Draft 2020-12 schema accept
one shared v1 topology for synthetic text-only and image-grounded records.
Both fixtures bind the frozen Runtime, Lane B versions, model, policy,
environment, pre/post observations, candidate action, Runtime decision, tool
result, and state verifier. Candidate outputs carry no execution authority;
Runtime remains the sole dispatch authority.

The 21,091-byte schema has SHA-256
`2109dcd2b06e01bda30ea19bc548cb34031811319e23f0bce5dd91a60c32964c`.
The 7,387-byte text fixture has SHA-256
`9162a2e322961434532b320670bacca3267bfe8cd4f5f823a177361ff5207706`
and ten artifacts. The 11,145-byte image fixture has SHA-256
`89c45460a6ffd4804f9ef855680fd74be18321afa89e94842bffb6ba833f5963`,
17 artifacts, and one bound previous step. Four invalid fixtures pin parser
failures. The unified CPython 3.11.15, 3.12.12, and 3.13.7 gates each pass 468
tests with `valid=true` and audit 40 source files; the focused 26-test suite,
Ruff, strict mypy, `py_compile`, independent JSON Schema checks, and metadata
hash recomputation pass. A final no-dependency wheel contains both trajectory
modules and the `fullcycle-trajectory` entry point.

This closes only the synthetic schema review. Capture, real episodes, dataset
split/license approval, GUI grounding quality, model training/execution,
cross-machine, portable-package, serving, promotion, and Runtime eligibility
remain unestablished or false. The exact next gate is
recorded historically as `MM-002-gui-grounding-data-eval-v1`; that gate has
since completed.
[Evidence](docs/MM-001-multimodal-trajectory-schema-v1.md).

The `FC-BRIDGE-003` Lane B v1 consent/capture/security contract review
completed locally on 2026-08-17. The standard-library validator accepts one
closed review bundle containing separately versioned explicit consent,
quarantined episode, and deletion-receipt records. It requires visible,
run-scoped consent; bounded application/retention scope; separate storage;
sanitization and image-redaction declarations completed before write;
content-addressed artifact references; Runtime-only dispatch authority;
state-based verification; and deletion coverage for every artifact.

The 23,929-byte Draft 2020-12 schema has SHA-256
`634089a84a3d9f63ede12ab8bd0ce905b03a8891dfaf2dedd547a73f2ee49368`.
The 11,820-byte synthetic valid fixture has SHA-256
`c0d90c1b355e902c730a1048cdd5baec03f73d174c662389943d2d4649909074`;
it contains nine artifact references and one transition, and its synthetic
deletion receipt covers all nine. The unified CPython 3.11.15, 3.12.12, and
3.13.7 gates each pass 442 tests with `valid=true` and audit 38 source files;
the focused 21-test suite, Ruff, strict mypy, and `py_compile` pass. Windows
symlink probes account for two unified and one focused privilege skips. The
final no-dependency wheel build contains both Lane B modules and the
`fullcycle-lane-b` console entry point.

This closes only the contract review. `capture_adapter_implemented=false`,
`real_episode_collected=false`, `real_deletion_executed=false`,
`dataset_split_assigned=false`, `license_approved=false`,
`training_eligible=false`, and `runtime_eligible=false`. The exact next gate is
recorded historically as `MM-001-multimodal-trajectory-schema-v1`; that gate
has since completed.
[Evidence](docs/FC-BRIDGE-003-lane-b-consent-capture-security-v1.md).

The `FC-MVP-001-fp32-attached-preferred-offline-candidate-decision-v1` gate
completed locally on 2026-08-10. Its outcome-neutral categorical protocol was
frozen before formal evidence generation at
`1f9aeecda71ad7f758a905b1eec3dccb3885e10f`. The 5,158-byte preregistration
has SHA-256
`75f25ceebb6a9428ad3d92f4ecc778d8725e1d52e32367ff8db3cb2ac3125f21`;
the 9,619-byte formal evidence has SHA-256
`02f66ed79edce17803ddc1ed172c35a995be4ee8ed984cdd49b4e24bc5748c55`.

The decision recomputes the frozen artifact review and offline eligibility
validators. FP32 improves compiled argument exact match from `0.20` to `0.25`
and argument field F1 from `0.2608695652173913` to
`0.29787234042553196`; `eval-016.arguments` is the only strict per-example
improvement. There are zero compiled regression events and all seven safety
checks pass. Raw semantic validity falls from `0.85` to `0.80`, so the fixed
compiler remains part of the candidate identity.

Peak allocated GPU memory rises from `3,150,315,520` to `6,267,895,296` bytes,
a ratio of `1.9896087411587269`, while remaining inside the preregistered cap.
The one elapsed ratio is `0.9308972201805388`, but stable speedup and repeat
variance are not established. All 12 registered gates pass with no blocker in
the preference scope. Strict recomputation derives
`fp32_attached_preferred_offline_candidate_under_fixed_compiler_attached_execution_and_registered_resource_caps`,
`formal_gate_passed=true`, and `preferred_offline_candidate=true` only for the
next portable-package qualification step.

The gate uses no network, model load, generation, training, or new evaluation.
Cross-machine reproducibility and portable-package eligibility remain the two
exact downstream open findings; promotion, serving, merged-artifact, and
Runtime claims remain false. The unified offline gate passes 403 tests with
`valid=true` and audits 35 source files on local CPython 3.11.15, 3.12.12, and
3.13.7. The 12 focused tests, Ruff, strict mypy, py_compile, builder `--check`,
and `git diff --check` pass. The clean pull-request CI matrix independently
passes the same gate on CPython 3.11.15, 3.12.13, and 3.13.14.
[Evidence](docs/FC-MVP-001-fp32-attached-preferred-offline-candidate-decision-v1.md).

The `FC-MVP-001-fp32-attached-offline-artifact-eligibility-reassessment-v1`
gate completed locally on 2026-08-10. Its outcome-neutral metadata-only
protocol was frozen before formal evidence generation at
`2a5db8afaf90a3557d6d8d8cd808089d305d83e1`. The 4,920-byte preregistration
has SHA-256
`f1fc627d3d20f9c954f93e0cd4c930b22f592c48d2f4af72220c184f2e32c662`;
the 9,747-byte formal evidence has SHA-256
`0cccb2a7c7cdc24c824ee0ca4606f8c14e9b561473e50e8b31072291357b15ed`.

The reassessment binds and recomputes the canonical validators for the frozen
artifact review (`81977f...b006f8`), composite manifest
(`4125f2...943eb0`), clean-location reproducibility evidence
(`0e0d21...84044`), and remote revision-origin evidence
(`cdde41...b15ed`). The manifest resolves the review's six exact package
blockers; the later gates establish same-recorded-environment exact 20-case
raw and compiled replay plus the fixed GitHub and Hugging Face hosted origins.
All nine registered gates pass with no remaining blocker inside the declared
eligibility scope.

Strict recomputation derives
`fp32_attached_fixed_compiler_favorable_eval_offline_artifact_package_eligible`,
`formal_gate_passed=true`, and `offline_artifact_eligible=true`. The gate uses
no network, model load, generation, training, or new evaluation and saves no
model or tensor payload. At that reassessment gate, portable-package,
cross-machine reproducibility, preferred-candidate, serving, promotion,
merged-artifact, and Runtime claims remained false. The unified offline gate
passes 391 tests with `valid=true` and
audits 34 source files on local CPython 3.11.15, 3.12.12, and 3.13.7. The 12
focused tests, Ruff, strict mypy on the typed reassessment scope, py_compile,
builder `--check`, and `git diff --check` pass. The clean pull-request CI matrix
independently passes the same gate on CPython 3.11.15, 3.12.13, and 3.13.14.
[Evidence](docs/FC-MVP-001-fp32-attached-offline-artifact-eligibility-reassessment-v1.md).

The `FC-MVP-001-fp32-attached-remote-revision-origin-attestation-v1` gate
completed locally on 2026-08-09. Its metadata-only contract and collector were
frozen before formal observation at
`d0f9a6988ef9702c713402bb179d7524e5e12c7f`. The 17,479-byte preregistration
has SHA-256
`0523caa79ab820e4de892e25f7e94e0081c1086e0255e286c6f202bbc382667e`;
the 18,348-byte evidence has SHA-256
`cdde41aed18e2fecccea1833f16cea4fc808eb5d212376c96f3e2763fcef7cfd`.

One accepted observation makes five fixed HTTPS metadata requests with zero
automatic retries. GitHub repository ID `1315085157`, package commit
`eafd3f646e4ec08dd0a1f76443ccfd416e81fa22`, tree
`175fc22f53392992dc6c6c32093898399702efeb`, all `18/18` selected blobs, and
the Adapter LFS pointer/batch oid and size bind exactly. Hugging Face repository
`Qwen/Qwen2.5-1.5B-Instruct`, revision
`989aa7980e4cf806f80c7fef2b1adb7bc71aa306`, all ten siblings, and all nine
package files bind exactly. The collector downloads no LFS payload, reads no
large LFS bytes, loads no model, makes no generation call, writes no package
bytes, and stores no signed URL/query.

Strict recomputation derives
`fp32_attached_github_and_huggingface_hosted_revision_origins_attested`,
`formal_gate_passed=true`, `remote_revision_origin_attested=true`, and no
remaining origin blockers. GitHub reports the package commit unsigned, so
author/signature, supply-chain signature, and transparency-log claims remain
false. At that gate, offline-artifact, portable, preferred, serving, promotion,
merged, and Runtime claims also remained false pending reassessment. The
unified offline gate
passes 379 tests with `valid=true` and audits 33 source files on local CPython
3.12.12, 3.12.13, and 3.13.7; the clean pull-request CI matrix independently
passes the same gate on CPython 3.11.15, 3.12.13, and 3.13.14. The 28 focused
tests, Ruff, strict mypy on the typed contract/collector, py_compile, and
`git diff --check` pass.
[Evidence](docs/FC-MVP-001-fp32-attached-remote-revision-origin-attestation-v1.md).

The `FC-MVP-001-fp32-attached-offline-package-reproducibility-v1` gate
completed locally on 2026-08-06. Its materialization, execution, and comparison
protocol was frozen before formal execution at
`eafd3f646e4ec08dd0a1f76443ccfd416e81fa22`; the preregistration SHA-256 is
`982d039b2b591d2dab80d489bbbada252c764c82fce94334580807616b22ffff`.
A fresh checkout and pinned model download resolve base plus tokenizer `9/9`
at 3,098,971,928 bytes, Adapter `3/3` at 17,468,332 bytes, and repository
sources `15/15` at 233,571 bytes. The preflight is eligible without importing
the runtime, loading a model, making a generation call, or creating outputs.

The one formal offline replay uses one fresh FP32 attached-model load, 20
ordered generation calls, and zero retries. It reproduces raw outputs `20/20`
and compiled outputs `20/20` exactly. Measured elapsed time is
`38.108256999985315s`; peak allocated GPU memory is `6,267,895,296 bytes`,
with `0` bytes before load and `8,519,680` bytes after release. Every registered
resource cap passes. The predictions artifact SHA-256 is
`a0e99e80e091d3d6c191e3863449a6a5298d7f0d3a23cc6d786968562e6d2a46`;
the evidence SHA-256 is
`0e0d2174f4723ab42a5c11375cee10a819e32737810f63111d098decc2984044`.

Strict post-run recomputation derives
`fp32_attached_same_environment_clean_location_behavior_exactly_reproduced`
and `formal_gate_passed=true`. At that gate, the only remaining blocker was
`remote_revision_origin_unverified`. Cross-machine portability, repeat
variance, offline-artifact/portable/preferred eligibility, serving, promotion,
merged-artifact permission, and Runtime eligibility remain unestablished or
false. The unified offline gate passes 351 tests with `valid=true` on CPython
3.11.15, 3.12.12, and 3.13.7 and audits 32 source files. The 56 focused tests,
Ruff, strict mypy on the typed core/materializer/runner scope, py_compile, and
`git diff --check` pass. Independent read-only audit found no P0, P1, or P2
issue. A WSL Ubuntu Python 3.12.3 run also passes all 351 registered tests with
four explicit Win32-only transport/handle skips.
[Evidence](docs/FC-MVP-001-fp32-attached-offline-package-reproducibility-v1.md).

The `FC-MVP-001-fp32-attached-offline-package-manifest-v1` gate completed
locally on 2026-08-06. Its contract and builder were frozen before artifact
generation at `60d28be26436bc616e874692c4624d9d38a0d7a5`. The 17,487-byte
external metadata-only manifest has SHA-256
`4125f2eef2a4b8f07015169ac7fb77b830514e053a4624aa703e5f5a64943eb0`.
It binds 12 component files totaling 3,116,440,260 bytes, 18 direct source
roots, and 15 fixed repository paths. The exact Adapter remains unchanged at
three files, 224 F32 tensors, and 4,358,144 parameters.

External raw-file SHA validation and strict recomputation derive
`metadata_complete=true`, `offline_package_identity_complete=true`, and
`fp32_attached_metadata_only_composite_manifest_complete`; all six prior
package blockers are resolved. The manifest itself contains no self-digest,
passed/eligible/Runtime decision, or next-gate decision. Current-machine exact
resolution succeeds at base plus tokenizer `9/9`, Adapter `3/3`, and repository
sources `15/15`, but this was not clean-location attestation. At that manifest
gate, the remaining blockers were exactly `behavioral_reproducibility_unverified`,
`clean_location_resolution_unverified`, and
`remote_revision_origin_unverified`. Offline-artifact, portable-package,
preferred-candidate, serving, promotion, merged-artifact, and Runtime claims
were false.

The unified offline gate passes 295 tests with `valid=true` on CPython 3.11.9,
3.12.12, and 3.13.7 and audits 31 source files. The 27 focused manifest tests,
Ruff, scoped mypy 2.3.0, py_compile, builder `--check`, and `git diff --check`
pass. An independent read-only review found no remaining freeze blocker.
[Evidence](docs/FC-MVP-001-fp32-attached-offline-package-manifest-v1.md).

The `FC-MVP-001-fp32-attached-artifact-eligibility-review-v1` gate completed
locally on 2026-08-05. Its contract and builder were frozen before artifact
generation at `a36cc965531cef781cd66aff3c0ff4c481d56520`. The 15,278-byte review
artifact has SHA-256
`81977f318c6bcfed8d3844575dc245d4b94c2636a2359165f9aa5553c9b006f8`
and internal report digest
`285d5e5e25dfd16de5adc6cb760fe54588af68d8580308b54ccfaf612d51636b`.
It classified the reviewed state as
`fp32_attached_fixed_compiler_favorable_eval_but_offline_artifact_package_incomplete`.
The fixed-compiler quality evidence and repository-local evidence remain usable.
At that review, six blockers remained: composite manifest; portable base
identity; base revision; tokenizer file manifest; required compiler binding;
and complete use and limitations documentation. Accordingly offline/portable eligibility,
preferred-candidate status, serving readiness, promotion, merged artifacts, and
Runtime eligibility were all false at that gate.

The validator binds 25 direct sources through single-read raw payloads, then
requires parsed JSON/text, Adapter manifest, safetensors audit, observed hashes,
and the external review-file trust root to agree. The exact Adapter remains
unchanged at three files, 224 F32 tensors, and 4,358,144 parameters. The unified
offline gate passes 268 tests with `valid=true` on Python 3.11.15, 3.12.12, and
3.13.7 and audits 30 source files. Ruff, scoped mypy 2.3.0, py_compile, builder
`--check`, and `git diff --check` pass.
[Evidence](docs/FC-MVP-001-fp32-attached-artifact-eligibility-review-v1.md).

The `FC-MVP-001-fp32-attached-remediation-eval-v1` gate completed locally on
2026-08-05. Its protocol was committed before result generation at
`0638557d3bedc3bf00eef6ae4763f09d8878c4f5`. One fresh FP32 attached load
executes 20 ordered generation calls with no retry. Compiled argument exact
match and field F1 improve to `0.25` and `0.29787234042553196`; tool accuracy
and risk macro F1 remain `0.95` and `0.7095238095238096`; all safety counts and
eight-dimension per-example regression checks pass. The strict outcome is
`fp32_attached_full_eval_improves_quality_without_safety_or_resource_regression`.

The run takes `71.6701673999778` seconds, peaks at `6,267,895,296` allocated
GPU bytes, begins with zero allocated CUDA bytes, and releases to `8,519,680`
bytes. Raw semantic validity is `0.80`, below the BF16 raw `0.85`; the fixed
compiler is therefore still required. The prediction and gate SHA-256 values
are respectively
`382071f0689ce4ca41329d689f76fc4c4b06faa68769fb80c99181015e678115`
and `2dd17f6b1098490034f825d163f48f26eb4093d02f115424eb814cb2c925ad8e`.
No model or Adapter artifact is created or promoted, and
`runtime_eligible=false`.
The unified offline gate passes 260 tests with `valid=true` on Python 3.11.15,
3.12.12, and 3.13.7 and audits 29 source files. Ruff passes the repository,
mypy reports no issues in 31 current source/runner/validator files, and
py_compile plus `git diff --check` pass.
[Evidence](docs/FC-MVP-001-fp32-attached-remediation-eval-v1.md).

The `FC-MVP-001-attached-dtype-boundary-control-v1` gate completed locally on
2026-08-05. Four fresh attached runs execute in ABBA order, reproduce both
frozen 48-token paths and the exact cached call/step `45`, and capture embedding
output plus layer-0 `input_layernorm` input, weight, and output. After all
attached models unload, four fresh standalone `Qwen2RMSNorm` executions run in
ABBA order from the same checkpoint input and weight values. The actual and
control input/weight comparisons are equal; both actual and control outputs
differ in `1,536/1,536` elements with maximum/mean/RMS absolute deltas
`0.012537479400634766`/`0.0005440729593146898`/
`0.0009270972900508952`. Their BF16 and FP32 canonical output SHA-256 values
are respectively
`fcf241d93faf88fa991d10e987d879b33ce01ab94426e73dfab62048bfafa897`
and `b37c6dc89813c2bc0977d130ef0a1befdfffeeb77474f7682be8b267d19cb499`;
each control output exactly matches its same-dtype actual output. The
classification is
`deterministic_same_values_rmsnorm_dtype_replay_reproduces_actual_boundary_drift`.
`boundary_control_gate.passed=true`, `remediation_gate.passed=false`, and
`runtime_eligible=false`. The JSON record contains 28 execution capture
summaries plus two checkpoint-source records, is `142,760` bytes, and has
SHA-256
`fdf4ab44b1b60853f0d5de9f231ce77557152b47c9ce52156c31c9bbca484bc7`;
no module tensor payload or sidecar exists. The probe took
`32.9616448999732` seconds, peaked at `6,285,152,256` allocated GPU bytes, and
every released lifecycle stayed below 16 MiB. The unified offline gate passes
249 tests with `valid=true` on Python 3.11.15, 3.12.12, and 3.13.7, with 27
source files audited. Ruff, py_compile, and mypy 2.3.0 pass. This proves
current-forward sufficiency only for the local
registered RMSNorm boundary, not a unique internal operation/kernel root,
independent downstream propagation or token cause, pristine-FP32 checkpoint,
full-eval remediation, artifact promotion, or Runtime eligibility.
[Evidence](docs/FC-MVP-001-attached-dtype-boundary-control-v1.md).

The `FC-MVP-001-attached-dtype-numerics-v1` gate completed locally on
2026-08-05. Four fresh attached runs execute in ABBA order and reproduce both
frozen 48-token paths, every processed-score/raw-logit manifest, the exact
cached call `45`, input token `788`, cache/position `383`, and all precision
controls. The outcome-neutral plan registers 40 outputs: embedding, a detailed
layer-0 spine, all 28 decoder-layer outputs, final norm, and LM head. Its
canonical SHA-256 is
`945dc2b468edf361b73189e7adf1f4ef61599da4fd942942591fdc13c073b38a`.
All 40 native and canonical capture records are exact across the two repeats
of each dtype. The embedding's `1,536` canonical FP32 values are identical;
the first unequal registered output is index `1`,
`model.layers.0.input_layernorm`, where `1,536/1,536` elements differ with
maximum/mean/RMS absolute deltas `0.012537479400634766`/
`0.0005440729593146898`/`0.0009270972900508952`. Every one of the 38 later
registered outputs remains unequal. At the linked LM head, all `151,936`
elements differ, with maximum/mean/RMS deltas `1.943955421447754`/
`0.22759762689943575`/`0.29328314971734404`; both LM-head vector digests match
the prior frozen raw-logit vectors exactly. The LM-head-to-first-stage RMS
ratio is `316.34560133515606`, but it is only a descriptive cross-stage ratio,
not an amplification or independent causal-propagation estimate. The
classification is
`deterministic_attached_bf16_vs_fp32_registered_module_output_drift_reaching_lm_head`.
`numerics_gate.passed=true`, `remediation_gate.passed=false`, and
`runtime_eligible=false`. The JSON record contains 160 summary-only capture
records, is `393,662` bytes, and has SHA-256
`de5b048a5d254f61ab3bef1ff23f1484b07808c86a1679bc0de4ee58e8c8d7c5`;
no module tensor payload or sidecar exists. The stdlib validator closes source,
ABBA, trace, target, capture, repeat, comparison, LM-head, gate, and policy
links, but without raw module tensors it cannot independently recompute
intermediate full-vector counts or moments. The probe took
`35.3808942000032` seconds, peaked at `6,286,024,192` allocated GPU bytes,
and each released lifecycle retained `8,519,680` bytes. The unified offline
gate passes 181 tests on Python 3.11.15, 3.12.12, and 3.13.7. Ruff passes the
repository, py_compile passes the new source/script/test files, and mypy 2.3.0
reports no issues in all 46 source/script files.
[Evidence](docs/FC-MVP-001-attached-dtype-numerics-v1.md).

The `FC-MVP-001-attached-dtype-isolation-v1` gate completed locally on
2026-08-05. Four fresh runs execute in ABBA order: BF16 attached, FP32
attached, FP32 attached, BF16 attached. Each dtype is exactly repeat-stable
and reproduces its frozen 48-token, decoded-output, processed-score,
raw-logit, and target-forward references. Both paths keep the same attached
factorized LoRA form and FP32 Adapter runtime values; PEFT
`autocast_adapter_dtype=true` is a locked load-time policy that would upcast
FP16/BF16 Adapter weights, while these stored FP32 values remain FP32.
Generation autocast remains disabled. The paths share generated indices
`0`–`44`; at index `45`, BF16 emits token `1866` (`true`) and FP32 emits token
`3849` (`false`). Processed-score margins are `0.4545440673828125` and
`2.4418487548828125`; raw-logit margins are `0.5` and `2.68603515625`.
All `151,936` vocabulary elements differ in both comparison vectors, with
maximum absolute delta `1.943955421447754`. The classification is
`deterministic_bf16_attached_vs_fp32_attached_raw_logit_boundary_flip`.
`dtype_isolation_gate.passed=true`, `remediation_gate.passed=false`, and
`runtime_eligible=false`. The probe took `37.87893820001045` seconds and
peaked at `6,285,127,680` allocated GPU bytes; every released lifecycle stays
at `8,519,680` bytes, below the 16 MiB ceiling. The JSON-only validator closes
the source chain, ABBA protocol, 48-step manifests, target/LM-head linkage,
top-k algebra, classification, gates, and policy. Without raw vector payloads,
its full-vector delta checks are limited to probe-derived summary algebra and
do not independently recompute maximum/mean/RMS statistics. The evidence does
not support a pristine-FP32 checkpoint claim, first module or unique CUDA root
cause, PEFT bug, full-eval generalization, artifact promotion, or Runtime
eligibility. The canonical record SHA-256 is
`7eaedee1d6f7ea27b2fc083f82bc8df620612e84095f4a66a2ba7dfec791ce31`.
The unified offline gate passes 144 tests on Python 3.11.15, 3.12.12, and
3.13.7. Ruff passes the repository, py_compile passes the new source/script/
test files, and mypy 2.3.0 reports no issues in all 43 source/script files.
[Evidence](docs/FC-MVP-001-attached-dtype-isolation-v1.md).

The `FC-MVP-001-fp32-attached-merge-numerics-v1` gate completed locally on
2026-08-05. Four fresh runs execute in ABBA order: attached, merged, merged,
attached. Every run reproduces its frozen 48-token, decoded-output,
processed-score, raw-logit, and target-forward references, and all captured
tensors are bitwise repeat-stable within each path. The 13-stage paired output
comparison first differs at index `2`,
`model.layers.0.self_attn.q_proj`, after bitwise-identical embedding, layer 0
input normalization, and `q_proj` input tensors. Its output differs in
`1,261/1,536` elements, with maximum/mean/RMS absolute deltas
`3.814697265625e-06`/`1.6505699325837972e-07`/
`2.990363292409807e-07`. Probe-captured linear replays match both actual
outputs, while the stdlib gate independently recomputes their comparisons and
the scalar/add identities.
The factorized LoRA term versus delta-weight linear comparison differs in
`1,355` elements with maximum delta `3.259629011154175e-09`, and that axis
survives base addition in 53 elements. Split base-plus-delta versus the
materialized-weight linear differs in `1,260` elements with maximum delta
`3.814697265625e-06`. The representative `q_proj` audit recomputes all
`2,359,296` merged weights with zero mismatches; 21 nonzero archived FP32 delta
updates round back to the base value. The classification is
`deterministic_fp32_factorized_lora_and_materialized_linear_execution_form_drift`.
The Git LFS tensor sidecar contains 138 bound records and `46,069,904` bytes,
with SHA-256
`550175dfcfe14b0739aabf17573825a124180a6e21826e25d4b5ff733fb298a9`;
the JSON record SHA-256 is
`cb1c2b4255ebc5c38aa2ff66436804cca55dc088e39ca8fe8959654488e41a91`.
`numerics_gate.passed=true`, `remediation_gate.passed=false`, and
`runtime_eligible=false`. The probe took `29.912574299960397` seconds and
peaked at `6,286,505,472` allocated GPU bytes. It does not claim the earliest
temporal or unregistered functional divergence, independent propagation of
either counterfactual beyond `q_proj`, a unique floating-point or CUDA root
cause, a PEFT bug, full-eval generalization, merged-artifact promotion, or
Runtime eligibility. The unified offline gate passes 124 tests on Python
3.11.15, 3.12.12, and 3.13.7; Ruff passes the repository, py_compile passes the
new source/test files, and mypy 2.3.0 reports no issues in all 40 source/script
files.
[Evidence](docs/FC-MVP-001-fp32-attached-merge-numerics-v1.md).

The `FC-MVP-001-fp32-attached-merge-isolation-v1` gate completed locally on
2026-08-04. Two fresh independent FP32 attached-Adapter loads are exactly
repeat-stable across 48 generated tokens, decoded output, all processed-score
and raw-logit vectors, precision audit, and frozen-step vectors. One fresh
unchanged FP32 safe-merged load reproduces its frozen token/output/full-trace
and index-45 vector digests. All three runs share token digest
`sha256:9dfd817e59df5c0278fdd9da20feb3664fade5d354040bbd5b3b4c650ca43dca`
and output digest
`sha256:b37939d2e8014afcc92b094d9c63715aa28d91f02504bf8b56186dd2dd5cc7ca`,
so there is no same-dtype token boundary. At the pre-registered BF16 context
step `45`, both FP32 forms emit `false`, but `150,968/151,936` processed-score
and raw-logit elements differ. Both have maximum absolute delta
`0.0001735687255859375`; processed-score mean/RMS deltas are
`0.00002052841409749817`/`0.000026467831048648804`, and raw-logit mean/RMS
deltas are `0.00002052839772659354`/`0.000026469620934221894`. The
classification is
`deterministic_fp32_attached_vs_merged_numerical_drift_without_token_drift`,
`isolation_gate.passed=true`, `remediation_gate.passed=false`, and
`runtime_eligible=false`. The run took `29.405898299999535` seconds and peaked
at `6,285,651,968` allocated GPU bytes. The gate record SHA-256 is
`37d8d35bc3802a76bd7e0ab484f3b86e01b03852212ae9aaf3d9cec318fb5e26`.
No BF16 GPU path was rerun, and no merged artifact was saved or permitted. The
unified offline gate passes 106 tests on Python 3.11.15, 3.12.12, and 3.13.7;
Ruff passes the repository and mypy reports no issues in 37 source/script
files.
[Evidence](docs/FC-MVP-001-fp32-attached-merge-isolation-v1.md).

The `FC-MVP-001-fp32-merge-drift-analysis-v1` gate completed locally on
2026-08-04. One fresh independent BF16 attached-Adapter path and one fresh
locked FP32 safe-merged path each reproduce their frozen 48-token and decoded
output digests. Their first generated-token boundary remains zero-based index
`45`: BF16 attached chooses token `1866` (`true`), while FP32 merged chooses
token `3849` (`false`). Processed generation-score margins are
`0.4545440673828125` and `2.4415740966796875`; raw-logit margins from the same
cached `generate` call are `0.5` and `2.68572998046875`. The raw-logit vector's
maximum absolute delta is `1.9437971115112305`, mean absolute delta is
`0.22757971286773682`, and all `151,936` vocabulary elements differ at this
step. The classification is
`deterministic_bf16_attached_vs_fp32_merged_raw_logit_boundary_flip`,
`analysis_gate.passed=true`, and `remediation_gate.passed=false`. This locates
the first token/argmax boundary but does not isolate dtype from merge execution
or claim earlier logits are identical. The run took `13.201921800035052`
seconds and peaked at `6,268,076,032` allocated GPU bytes. The gate record
SHA-256 is
`ae5d1c7ace24c6cfcfed0eca60354cd3dfa9579fa0aea4e1f64c66eb73e41ea3`.
No merged artifact was saved or permitted, and Runtime eligibility remains
false. The unified offline gate passes 95 tests on Python 3.11.15, 3.12.12,
and 3.13.7; Ruff passes the repository and mypy reports no issues in 35
source/script files.
[Evidence](docs/FC-MVP-001-fp32-merge-drift-analysis-v1.md).

The `FC-MVP-001-bf16-merge-remediation-v1` gate completed locally on
2026-08-04 and falsified its sole pre-registered candidate. Two fresh FP32
safe-merged loads are token-identical at 48 generated tokens, both with digest
`sha256:9dfd817e59df5c0278fdd9da20feb3664fade5d354040bbd5b3b4c650ca43dca`.
They do not match the frozen independent BF16 Adapter digest
`sha256:e23b3f5ed71ec57f44ccacfadf8d79abfb21be622f13cae83cf14274cc54e173`;
instead, they match the prior safe-merged BF16 token and output digests. Both
runs verify 338 FP32 base tensors, 224 FP32 LoRA tensors across 112 targets,
zero LoRA tensors after FP32 safe merge, FP32 generation scores, greedy SDPA,
disabled autocast/TF32, tied embeddings, and isolated fresh-load lifecycles.
The classification is `deterministic_fp32_merge_output_drift` and
`remediation_gate.passed=false`. The run took `18.06072970002424` seconds and
peaked at `6,248,754,688` allocated GPU bytes. The gate record SHA-256 is
`7f3c5aff55e69c08a7676d33636a52a5a2bb43f025dae8a2db362041354050b3`.
No merged artifact was saved or permitted, and Runtime eligibility remains
false. The unified offline gate passes 87 tests on Python 3.11.15, 3.12.12,
and 3.13.7; Ruff passes the repository and mypy reports no issues in 33
source/script files.
[Evidence](docs/FC-MVP-001-bf16-merge-remediation-v1.md).

The `FC-MVP-001-bf16-merge-numerics-v1` gate completed locally on 2026-08-04.
At the exact cached generation step for token index `45`, the embedding and
layer 0 input normalization are element-identical across paths. The first
difference is layer 0 `q_proj`: `569/1536` output elements differ, with maximum
absolute delta `0.0625`. Across all `112` Q/K/V/O LoRA targets and
`154,140,672` weights, the reproduced PEFT safe-merge algorithm has zero
weight mismatches with the actual merged model. However, `30,640,994` nonzero
ideal updates round back to their base BF16 values, or
`0.19878591161195924` of all nonzero updates. The classification is
`bf16_safe_merge_weight_rounding`. The gate record SHA-256 is
`eb39674127ac93fea2ce6415b3a2fea0d20f6da916b76f1532392533db3e805f`.
No merged artifact was saved or permitted, and Runtime eligibility remains
false. The unified offline gate passes 81 tests; Ruff passes the repository
and mypy reports no issues in 31 source/script files.
[Evidence](docs/FC-MVP-001-bf16-merge-numerics-v1.md).

The `FC-MVP-001-bf16-merge-stability-v1` gate completed locally on 2026-08-04.
Two fresh independent Adapter loads are token-identical to each other, and two
fresh safe-merged BF16 loads are token-identical to each other. The paths first
diverge at zero-based generated token index `45`: independent loading chooses
token `1866` (`true`) while safe merge chooses token `3849` (`false`). Scores
captured from the exact cached generation step confirm a deterministic argmax
flip: the independent margin is `0.4545440673828125`, the merged margin is
`4.090908050537109`, maximum absolute logit delta is `3.0`, and mean absolute
delta is `0.3340962529182434`. The gate record SHA-256 is
`82bc73310625855770d6cc90aab6b5ed0e78fc1cd3c7684fd007ac8379c67abc`.
No merged artifact was saved or permitted, and Runtime eligibility remains
false. The unified offline gate passes 77 tests; Ruff passes the repository
and mypy reports no issues in 29 source/script files.
[Evidence](docs/FC-MVP-001-bf16-merge-stability-v1.md).

The `FC-MVP-001-decision-compilation-v1` gate completed locally on 2026-08-03.
It compiles redundant terminal fields from `selected_tool` without modifying
the frozen raw prediction artifact. Exactly `eval-001`, `eval-014`, and
`eval-020` change `expected_result` and `should_reject`; no selected tool,
argument, risk, approval, instruction, or source artifact changes. On the same
eval digest, decision semantic validity rises from `0.85` to `1.0`, rejection
accuracy from `0.85` to `1.0`, false refusals fall from three to zero, tool
accuracy remains `0.95`, and dangerous action candidates and false approvals
remain zero. The gate record SHA-256 is
`0e798d3404acd4fc6965d773a5ee2f8b3c593eb7865774a0acaadf7d2073a6de`.
The unified offline gate passes 71 tests on Python 3.11.15, 3.12.12, and
3.13.7; Ruff passes the repository and mypy reports no issues in 27
source/script files. The compiled output remains Runtime ineligible because
merge drift is still unresolved.
[Evidence](docs/FC-MVP-001-decision-compilation-v1.md).

The `FC-MVP-001` v2 failure-classification gate completed locally on
2026-08-03. The three semantic conflicts are exactly `eval-001`, `eval-014`,
and `eval-020`; all select fallback while setting both fallback and rejection
flags. The aggregate false-refusal count is also three, so both failure groups
belong to decision-contract consistency without opening per-case eval labels.
The safe BF16 merge separately changes only `$.should_reject` on `eval-001`
despite removing all adapter tensors, so merged output remains prohibited and
belongs to adapter-merge stability. Frozen aggregate evidence does not support
a data-coverage diagnosis. The canonical classification report digest is
`sha256:671e4fad7e2b9987b0cbf3f3fdb078c11431efa5887109a204874ec136316a9a`.
The unified offline gate passes 67 tests on Python 3.11.15, 3.12.12, and
3.13.7; Ruff passes the repository and mypy reports no issues in 25
source/script files. [Evidence](docs/FC-MVP-001-v2-failure-classification.md).

The `FC-MVP-001` LoRA SFT v2 gate completed locally on 2026-08-03. The locked
three-epoch BF16 LoRA run trained for 66 optimizer steps on the passed 176/48
data in `169.527236` seconds with `5,217,494,016` peak allocated GPU bytes.
On the unchanged eval, Tool Accuracy improved from `0.8` to `0.95`, dangerous
action candidates fell from one to zero, and dangerous false approvals stayed
zero. The narrow safety gate passed. Decision semantic validity is only
`0.85`, with three `CONFLICTING_DECISION_FLAGS` outputs and three false
refusals. `safe_merge` removed all adapter tensors but changed one boolean on
`eval-001`, so output identity failed. The adapter and all raw evidence are
frozen, and `runtime_eligible=false`. The unified offline gate passed `63`
tests on Python 3.11.15, 3.12.12, and 3.13.7; Ruff and mypy passed.

The `FC-MVP-001` safety-repair data gate completed locally on 2026-08-03. The
frozen SFT v1 diagnosis records one dangerous action candidate, four semantic
inconsistencies across four eval cases, and validation overfitting after epoch
3. A reviewed train/validation-only increment added 16/8 records and eight
disjoint repair families, producing 176/48 records across 68 families while
preserving v1 as the exact prefix and keeping the eval digest unchanged. Eval
answers are excluded, maximum cross-split instruction token Jaccard is
`0.4166666666666667` under the `0.8` rejection threshold, and dangerous action
candidates and dangerous false approvals are both zero. The pinned repair
report digest is
`sha256:2383731556a66ba81de670378c18afcd0493d368dc157d6a5a4e51e5904ee4b2`.

The first `FC-MVP-001` SFT gate completed locally on 2026-07-29. BF16 LoRA
rank 16 / alpha 32 targeted Q/K/V/O projections for 5 epochs and 100 optimizer
steps on the frozen 160/40 data. Training took `216.825720` seconds, peak
allocated GPU memory was `5,217,494,016` bytes, and 4,358,144 parameters
(`0.281521%`) were trainable. The independent Adapter directory is 17,468,332
bytes; its 17,462,432-byte weight file has SHA-256
`1c58a3d08598250cc01bd35a3367fbcc778c551782e6117f686394ede3d65659`.
Independent loading and safe merge produced identical verification output.
On the unchanged eval, Tool Accuracy improved from `0.2` to `0.8`, argument
exact match from `0.0` to `0.35`, and risk Macro F1 from
`0.4257518796992481` to `0.7373015873015873`. One dangerous action candidate
remains, so `safety_gate_passed=false` and `runtime_eligible=false`.

The `FC-MVP-001` schema/eval gate completed locally on 2026-07-29:
`tool_router_schema_version=1`, 20 reviewed seed records, 20 frozen eval
records, ten categories with two eval cases each, and canonical eval digest
`sha256:02221fedccb331466eb7b4a354c725a0ab31ac121f022298f42d3782b5e56a7a`.
The deterministic non-model baseline produced tool accuracy `1.0`, argument
exact match/F1 `0.0/0.0`, risk Macro F1 `0.8641148325358852`, approval,
rejection, and fallback accuracy `1.0`, and zero dangerous false approvals.
The unified offline gate passed `31 tests` on Python 3.11.15, 3.12.12, and
3.13.7; Ruff passed and mypy passed all nine source/script files.

The `FC-MVP-001` data-expansion gate completed locally on 2026-07-29 with 160
train and 40 validation records across 60 explicit task families. Every
category contributes 16 train and four validation records; task-family overlap
and exact instruction duplicates are zero. Maximum cross-split instruction
token Jaccard is `0.4166666666666667` under the `0.8` rejection threshold,
dangerous false approvals remain zero, and the frozen eval digest is unchanged.
The pinned data report digest is
`sha256:b58af24bdc3cfd34eb4309f91e977f2f4fc6f76a53a229eaa8d3f757d1ebf9a4`.
The unified offline gate passed `40 tests` on Python 3.11.15, 3.12.12, and
3.13.7; Ruff passed and mypy passed all 12 source/script files.

The `FC-MVP-001` inference-baseline gate completed locally on 2026-07-29 with
`Qwen/Qwen2.5-1.5B-Instruct` at Hub revision
`989aa7980e4cf806f80c7fef2b1adb7bc71aa306` under Apache-2.0. BF16 greedy SDPA
inference on an RTX 4090 Laptop GPU completed 20 cases in `74.492267` seconds
with `3,132,882,944` peak allocated GPU bytes and empty stderr. A second run
was byte-identical to prediction artifact SHA-256
`6182e70cdab772597a68d6b7e0bcbbff8b74c20626fa197c68dbced82e0d5f0d`.
JSON validity was `1.0`, but decision semantic validity was `0.7`, tool
accuracy was `0.2`, rejection recall was `0.0`, and both dangerous cases
produced dangerous action candidates. The model is explicitly
`runtime_eligible=false`. Frozen prediction scoring is reproduced by the
standard-library gate. The unified offline gate passed `45 tests` on Python
3.11.15, 3.12.12, and 3.13.7; Ruff passed and mypy passed all 16
source/script files.

`FC-BRIDGE-001` completed on 2026-07-28 with consumer schema `1.0.0`, Runtime
commit `8ace897f746a4aa3dd3f8b10af392ea9ba81941d`, one valid producer-pinned
manifest, one minimal valid run export, and eight invalid fixtures. Validation
on Python 3.13.7: `12 tests` passed, Ruff passed, mypy passed, and the offline
CLI accepted the valid fixture with the pinned manifest digest. The repository
is published as the GitHub repository
`kuoforever/reliable-agent-model-lifecycle`.

`FC-BRIDGE-002` completed on 2026-07-28 with
`reliability_dataset_schema_version=1`, a strict Draft 2020-12 JSON Schema, a
canonical JSONL mapper, two exact input/output fixtures, and deterministic
failure, unknown-outcome, policy-denial, recovery, budget-limit, and
tool-sequence signals. Validation on Python 3.13.7: `21 tests` passed, Ruff
passed, mypy passed, the JSON Schema and two records validated, and the offline
script reproduced both JSONL records byte-for-byte.

`FC-BRIDGE-004` completed locally on 2026-08-02. The canonical
`baseline/runtime-freeze-v1.json` pins Runtime commit
`324ff2fb5911e332ddb5c5f90eb41296e8faf7a9`, package `0.1.0`, every Lane A
contract version, consumer schema `1.0.0`, and manifest digest
`sha256:6abe3431ea0e6b4065f21e9a6c6fe34de772f9c3c86a2437f8d14f95a5d6f522`.
The Runtime clean preflight passed `1566` tests with `8` skips on CPython
3.13.7; its sanitized report SHA-256 is
`dc78f08030b4d3c4fac255a91fb7badf2b06fdb0eb0c487073e1f825260c6d0e`.
The coordinated consumer offline gate passed `53 tests`, all seven frozen
artifact hashes, and exact bridge/dataset reproduction on Python 3.13.7; Ruff
passed and mypy reported no issues in 21 source/script files.
The old `8ace897` fixture pin remains immutable generation provenance. At that
freeze, Lane B was explicitly deferred to `FC-BRIDGE-003`; its later contract
review did not change the freeze or enable capture.

`FC-MVP-000` local gates completed on 2026-07-28 at implementation commit
`01167034d797d4d6855b1ba916b60564d29ba210`: Python 3.11.15, 3.12.12, and
3.13.7 each passed `21 tests`, seven artifact hashes, five source import-boundary
audits, and two exact dataset records with zero runtime dependencies. Ruff
0.15.22 and mypy 2.3.0 also passed.

`FC-MVP-000` remote gate completed on 2026-07-28. The repository is
`kuoforever/reliable-agent-model-lifecycle`; Actions run `30369941536` at head
`80bafb4a5bd5039115519ad7239584be39acb037` passed the Python 3.11, 3.12, and
3.13 matrix jobs. The exact run and job IDs are recorded in
`baseline/validation-2026-07-28.json`.

## Project backlog

| ID | Status | Deliverable |
|---|---|---|
| `FC-PM-000` | Complete | Project structure, MVP roadmap, scenario matrix, Project H, cross-repo management |
| `FC-BRIDGE-001` | Complete | Strict manifest/run-export consumer and offline compatibility fixtures |
| `FC-BRIDGE-002` | Complete | Lane A reliability/Verifier dataset mapping |
| `FC-BRIDGE-003` | Complete locally | Lane B v1 explicit-consent capture/security contract review; capture remains unimplemented |
| `FC-BRIDGE-004` | Complete locally | Runtime freeze pin, contract compatibility, and cross-repository handoff |
| `FC-MVP-000` | Complete | Runtime consumer baseline, locked environment, local/remote Python matrix |
| `FC-MVP-001` | In progress | Text Tool Router closed loop; portable-package qualification frozen and deferred pending an independent target |
| `FC-MVP-002` | In progress | Multimodal lifecycle; Document/Chart/PDF lifecycle closed through PR #59, Browser Research adaptation protocol published through PR #61, data protocol frozen locally and publication next |

Detailed technical tasks remain in
`AI_Infra_LLM_Agent_待做任务清单.md`. This file owns only sequencing and the
single active objective.

## Session start

1. Read `AGENTS.md` or `CLAUDE.md`.
2. Read this file.
3. Read `README.md`.
4. Read only the roadmap or task section required by the active item.
5. Inspect the target repository's status before editing.

## Session end

1. Record modified files and validation results.
2. Update one backlog status.
3. Set one exact next objective.
4. Do not report planned capabilities as implemented.
5. If Runtime contracts changed, update
   `Desktop_Runtime_依赖与集成.md` and the consumer fixture together.

## Current decisions

- The official display name is `Reliable Agent Model Lifecycle`; it names the
  complete target system while implementation claims remain evidence-backed.
- The local directory and the remote repository slug are
  `reliable-agent-model-lifecycle`, renamed on 2026-07-31 from
  `LLM-FullCycle-Learning` to match the display name. GitHub redirects the
  former slug, so frozen evidence URLs such as the `FC-MVP-000` Actions run
  URL in `baseline/validation-2026-07-28.json` stay resolvable and are left
  unedited.
- The remote repository is public. Earlier status and environment lines
  described it as private; that claim was found to contradict the repository
  on 2026-07-31 and was corrected rather than the visibility being changed.
- Existing `FC-*` IDs, `fullcycle_*` contracts, and package/CLI names remain
  unchanged for compatibility.
- One flagship project and four depth Labs.
- Desktop GUI is the first environment, not the permanent product boundary.
- Runtime owns execution safety; Reliable Agent Model Lifecycle owns models and
  datasets.
- Automatic Runtime export is redacted reliability evidence only.
- Rich multimodal episodes require explicit consent; the v1 contract review is
  complete, while capture, governance approval, and training use remain open.
- Runtime freeze commit `324ff2fb5911e332ddb5c5f90eb41296e8faf7a9`
  is pinned by `baseline/runtime-freeze-v1.json`; the later Lane B contract
  review did not change the immutable Lane A fixture provenance.
- Multi-Agent is formal Project H but does not block the first closed loop.
- Runtime Lane A producer v1 passed `1428` tests plus Ruff, mypy, docs, wheel
  build/install, and offline release gates, then PR #219 passed the Python
  3.11-3.13 and wheel CI gates and merged as `8ace897` on 2026-07-28.
