# MM-004 multimodal hard-negative model-evaluation protocol v1

## Outcome

The outcome-neutral protocol was frozen before any model call. Its canonical
49,311-byte preregistration is
`configs/mm004_multimodal_hard_negative_model_evaluation_protocol_v1.json`,
with SHA-256
`3011420f26bc61f572de2e21f96d28215529e495075db4e958573a4e4317484f`.

The fixed output directory
`work/evaluation-runs/mm004-hard-negative-model-eval-v1` remains absent. This
protocol freeze therefore establishes no model-evaluation, quality, safety,
serving, promotion, or Runtime result.

## Frozen candidate and inputs

- base model: `Qwen/Qwen2.5-VL-3B-Instruct`
- exact revision: `66285546d2b821cf421d4f5eb2576359d3770cd3`
- candidate form: one NF4 base load plus the read-only
  `baseline/adapters/mm003-qwen2.5-vl-3b-qlora-sft-v2` Adapter
- environment: the already reviewed Python 3.12.12 / Torch 2.6.0+cu124 /
  Transformers 4.49.0 / bitsandbytes 0.50.1 registered environment
- suite: all 56 generated records in stored train-then-validation order
- images: 28 exact generated PNG receipts
- calls: one fresh base load, one independent Adapter load, and 56 generation
  calls, with no retry, training, backward pass, optimizer step, or model write

The protocol binds exact receipts for the generated datasets and evidence,
candidate review evidence, Adapter files, dependency lock and wheel, model
snapshot files, and nine implementation sources.

## Label-isolated prompt and compiler

Each model input contains only the image plus:

- instruction
- structured observation without repository image path or image hash
- candidate action

Record identity, pair/category/split, clean/hard-negative variant, verifier gold
verdict, provenance, and content identities are excluded. Paired records share
instruction, observation, and image but differ in candidate action; the gold
accept/reject label is never provided to the model.

The compiler accepts only a JSON object with one key, `verdict`, whose value is
exactly `accept` or `reject`. Duplicate keys, extra keys, markdown fences,
non-finite JSON values, and every other malformed or unknown output compile to
`invalid`; compiler fallback is always scored incorrect.

## Registered metrics

All results, including uniformly wrong or uniformly invalid outputs, receive a
total score:

- overall accuracy
- clean accept recall
- hard-negative rejection recall
- balanced variant accuracy
- exact clean/negative pair accuracy
- compiler validity
- hard-negative false accepts and clean false rejects
- per-split and per-category metrics

No quality threshold determines measurement completion. Accuracy is an observed
result, not a condition that can alter the registered suite or trigger an
internal retry. Resource caps remain integrity gates: 1,800 elapsed seconds and
16.5 GB each for peak allocated and reserved GPU memory.

## One-shot persistence and failure boundary

Formal execution is allowed only from the fixed isolated Python invocation on
`master` when `HEAD == origin/master ==` the supplied merged freeze commit.
Before model import, the runner authenticates the freeze commit, config,
sources, upstream artifacts, generated output tree, model snapshot, Adapter,
and local wheel. Model, Adapter, and all 31 generated files are held read-only
through evaluation; outbound socket attempts are blocked and counted.

The fixed output directory is atomically claimed with an owner artifact. That
rename consumes the only attempt. Success persists the unscored model candidate
before scoring, then predictions and final evidence. A consumed failure
persists a typed receipt bound to the owner, preregistration, completed case
prefix, counters, and any already durable candidate/predictions. The runner
never deletes, reuses, or retries a consumed output.

## Validation evidence at freeze

Twelve focused tests cover deterministic reconstruction, label isolation,
strict compiler totality, perfect/adverse/invalid total scoring, protocol and
artifact tamper, resource-cap claim algebra, owner/failure binding, an exact
56-call fake model lifecycle, and durable success/scoring-failure terminals.
Full-repository Ruff, scoped strict Mypy on the new contract and runner,
`py_compile`, preregistration `--check`, and `git diff --check` pass.

The unified offline gate passes on CPython 3.11.15, 3.12.12, and 3.13.7. Each
run reports 647 tests, four expected Windows privilege skips, 53 audited source
files, and `valid=true`. The gate also requires the fixed execution directory
to be absent and reports protocol frozen while `evaluation_executed`,
`model_evaluated`, `training_executed`, and `runtime_eligible` remain false.

A separate model-free read-only preflight successfully opened, locked, and
re-authenticated 14 model snapshot files, three Adapter files, all 31 generated
inputs, and the local dependency wheel using the formal runner's paths. This
proves local byte and lock readiness, not model-load or inference success. The
exact formal Python invocation was also negatively tested on the feature
branch: it rejected the unmerged state before model import or output claim and
left the fixed output absent.

## Claims and next gate

At freeze, every execution, model, training, quality, safety, serving,
promotion, and Runtime claim is false. Model outputs never gain execution
authority; Runtime remains the sole policy, approval, WAL, grounding, budget,
and desktop-dispatch boundary.

After the exact protocol is merged, the next gate is
`MM-004-multimodal-hard-negative-model-evaluation-execution-v1`. A successful
run routes to the separate model-free result-review gate; a consumed failure
routes to the registered failure-classification gate.
