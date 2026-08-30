# MM-005 Browser Research generation-failure investigation protocol v1

> **Result: PROTOCOL PUBLISHED THROUGH PR #73; IMPLEMENTATION THROUGH PR #74;
> FIXED RESULT THROUGH PR #75 — the outcome-neutral model-free protocol is
> frozen at `fe430710924537a18e677b75202f0c19806d3f12`. The later static result
> reconstructed the pipeline without reproducing the claimed failure; the
> Runtime substage/root cause remains unresolved and diagnostic execution,
> remediation, retry, and model/CUDA use remain unauthorized.**

## Predecessor and protocol identity

PR #72 published the exact v2 failure classification as signed squash commit
`e52060ff82b62f6042ec371b72f011e5fa5c0681`. The classification binds the
consumed v2 attempt to three completed generation calls followed by a durable
fourth `generation_started` checkpoint and a broad `RuntimeError` terminal.
It does not authenticate the failing generation substage or root cause.

This separate protocol has gate ID
`MM-005-browser-research-model-evaluation-generation-failure-investigation-protocol-v1`
and investigation ID
`mm005-browser-research-model-eval-v2-generation-failure-static-v1`. Its
33,476-byte canonical preregistration is
[`configs/mm005_browser_research_model_evaluation_generation_failure_investigation_protocol_v1.json`](../configs/mm005_browser_research_model_evaluation_generation_failure_investigation_protocol_v1.json)
with SHA-256
`be8ecd067e884a8d60c9664013943d6887c769ac35a389934509b73338247494`.
At the PR #73 protocol freeze, the future result path was fixed separately as
`baseline/mm005-browser-research-model-eval-v2-generation-failure-investigation-v1.json`;
no result existed then. PR #75 later published the immutable 39,843-byte result
at that exact path. PR #73 passed all six Linux Python-matrix checks with no
blocking review, comment, thread, conflict, or merge-state finding; both
feature-branch copies were deleted before the implementation successor began.

The builder requires the PR #72 merge to be an ancestor and compares the v2
preregistration, owner, progress, failure, classification, classifier,
classification contract, and classification tests against their exact Git
blobs. It then independently validates the immutable v2 protocol and all three
raw terminal artifacts before reconstructing this preregistration. The private
attempt identifier is not copied into the derived protocol.

## Evidence layers

The protocol keeps four evidence classes separate:

1. **Durable authenticated facts.** The journal has 14 frames, the first three
   frozen records completed, the fourth record has a durable
   `generation_started` checkpoint but no durable completion, and the terminal
   records `stage=generation` plus `exception_type=RuntimeError`.
2. **Frozen-control-flow inference.** In the exact frozen runner, record
   adaptation and all three `Image.open(...).convert("RGB")` calls occur before
   the durable start checkpoint. Their return is therefore implied by the
   frozen source order and checkpoint, not directly recorded as individual
   journal events.
3. **Current model-free static recomputation.** The frozen dataset, Adapter
   projection, model payload, prompt projection, ordered screenshot/snapshot
   receipts, PNG headers, and runtime-message transport shape can be rebuilt
   exactly without PIL decode, processor, model, CUDA, or network.
4. **Unresolved runtime substages.** Message construction, pre-generation CUDA
   synchronization, chat-template rendering, processor tensorization, device
   transfer, `model.generate`, decode, post-generation synchronization, case
   construction, and durable completion are not individually authenticated for
   the fourth record.

Static source order does not identify an asynchronous CUDA error's origin. The
non-authenticated controller text remains excluded from causal evidence.

## Frozen target and controls

The target is the exact fourth sorted case:

- record ID
  `sha256:26b3a9da0467d1c18cc4a050ec10dc03a415a9c3a38a2a37de8b9805c67adaf7`;
- original train-array index `17`, template
  `mm005-browser-cross-comparison-06`, task family
  `cross_source_comparison_citation`, and three sources;
- canonical record receipt: 5,630 bytes,
  `sha256:3f1374169ef910194af3ec8423988a6f0edaccdaf38e7500734b868c2882099c`;
- Adapter audit projection: 5,748 bytes,
  `sha256:ad48e91f1440dcc2bbbc196d0bdcd387e4dd8de76d2540d2590dde235c958406`;
- model payload: 3,441 bytes,
  `sha256:1490af3bcf899b4cadaa141a3f1bd4d4c3e4fbb61b8f39911d4d04f0380864c3`;
- prompt and opaque-sentinel runtime-message transport projection: 4,532
  bytes,
  `sha256:266a804f7c155d3c7f8ef451c6bf756d9b99ea95a5fada90b518992d13808865`;
- three exact PNGs of 8,849, 8,826, and 8,850 bytes, each `1280x900`, RGB8,
  non-interlaced; and
- three audit-only source snapshots of 1,742, 1,740, and 1,742 bytes.

The first three authenticated completed records are frozen as execution
controls. Three additional `cross_source_comparison_citation` records are
selected before investigation because each has the same three-image,
3,441-byte model-payload, and 4,532-byte prompt shape as the target. Shape
similarity or difference is diagnostic context only; it cannot establish
historical causality.

## Static plan and decision rubric

At protocol freeze, the next gate was
`MM-005-browser-research-model-evaluation-generation-failure-investigation-v1`.
It could implement and execute only the frozen static plan:

- validate the published failure lineage and raw terminal artifacts;
- rebuild the exact dataset and artifact context;
- select the fixed target and controls;
- recompute record, artifact, Adapter, model-payload, prompt, and
  opaque-sentinel runtime-message projections;
- verify the frozen source/checkpoint boundary; and
- select exactly one preregistered outcome.

Allowed outcomes are:

- `protocol_or_lineage_invalid`;
- `deterministic_static_input_or_message_failure_reproduced`;
- `static_pipeline_reconstructed_without_contract_violation`;
- `static_difference_observed_without_causal_failure`; or
- `static_investigation_inconclusive`.

No outcome is selected at freeze. A static failure can support only a
deterministic static reproduction. A static pass does not establish historical
runtime health, and a static difference does not establish causality.

The investigation implementation is a separate bounded slice conforming to
this plan. This protocol did not freeze or silently pre-author that source.
The current implementation closes the schema, mutually exclusive predicates,
precedence, claim transitions, structural comparison dimensions, and
protocol-only routing, and binds its result contract, runner, and focused test
as a three-file implementation closure. Its read-only `--plan` validates the
published protocol without executing the investigation. Result publication
remains exclusive, zero-retry, clean-merged-master-only, and bound to the fixed
result path. Before build or write, the runner derives the three-file
introduction from canonical `origin/master` first-parent history and requires
the complete PR #73-to-freeze delta to equal the exact ten reviewed slice
paths. Historical checking binds PR #73 config/ten-source receipts before an
isolated local/no-lazy-fetch `python -I -S -B` worker executes the exact freeze
runner blob.

## Authority and future routing

This protocol and its builder do not import or call `torch`, `transformers`,
PEFT, bitsandbytes, PIL, a processor, a model, CUDA, a browser, or a network.
They do not retry v1 or v2, train, write an Adapter, save tensors or model
weights, capture real content, or change the Runtime repository. The Runtime
remains the sole policy, approval, WAL, grounding, budget, and desktop-dispatch
boundary.

The validated static result selected
`static_pipeline_reconstructed_without_contract_violation` and justified only
the separate diagnostic-protocol freeze. PR #75 published that immutable
result as signed squash commit `c8541147717870992c60c6d2ea1c2f4ff68ee1d2`.
The new diagnostic protocol artifact uses a new experiment ID, run ID, and
output root, binds the published result, freezes independent authority/resource
contracts, and closes seven explicit 18-event per-record plans around message
build, CUDA synchronization, chat template, processor tensorization/device
transfer, generation, decode, post-synchronization, and case construction. The
full-success grammar therefore contains 126 durable events. Its 57,143-byte
canonical config has SHA-256
`13d1808168819414df2a0ca33d1f59e5e8efd52de6f0b49946d02cf070c992d6`;
26 focused tests and all three 987-test unified gates pass with four expected
Windows privilege skips and 75 audited source files. It cannot reuse or retry
v2. After its clean merge, the locked successor is
`MM-005-browser-research-model-evaluation-generation-failure-diagnostic-implementation-v1`.
Diagnostic execution remains unauthorized. Observing an error at a
synchronization checkpoint would still not by itself prove the asynchronous
error originated there.

Recovery-v3 remains unjustified because v2 durable progress and terminal
persistence succeeded, while neither a failed substage nor a remediating
semantic delta is authenticated.

## Validation

```powershell
work\python-matrix\conda311\python.exe -I -B tests\test_mm005_browser_research_model_evaluation_generation_failure_investigation.py -v
work\python-matrix\conda311\python.exe -I -B tests\test_mm005_browser_research_model_evaluation_generation_failure_investigation_result.py -v
work\python-matrix\conda311\python.exe -I -B scripts\prepare_mm005_browser_research_model_evaluation_generation_failure_investigation_protocol_v1.py --check
work\python-matrix\conda311\python.exe -I -B scripts\run_mm005_browser_research_model_evaluation_generation_failure_investigation_v1.py --plan
work\python-matrix\conda311\python.exe -I -B scripts\validate_offline.py
work\training-env\Scripts\python.exe -I -B scripts\validate_offline.py
python -I -B scripts\validate_offline.py
```

The focused tests cover canonical recomputation, published Git lineage, raw
artifact and classification drift, exact target/control selection, image and
prompt receipts, opaque-sentinel message reconstruction, checkpoint source
order, claim and authority closure, conditional successor routing, type-strict
boolean/integer rejection, missing/extra/path/source drift, hardlink/symlink
guards, overwrite refusal, attempt-ID privacy, and absence of model/network/
CUDA capability.

The published protocol's 16 focused tests pass on local CPython 3.11.15,
3.12.12, and 3.13.7. The published result slice adds 32 focused tests. PR #75
publication validation passed those tests, Ruff 0.15.22, Ruff format check,
scoped strict Mypy 2.3.0, `py_compile`, protocol `--check`, real historical
`--check`, and the complete CPython 3.11.15, 3.12.12, and 3.13.7 unified
offline gates. Each unified gate passes 961 tests with four expected Windows
privilege skips, 74 audited source files, `result_present=true`,
`investigation_executed=true`, `runner_plan_valid=false`,
`runner_check_valid=true`, and `valid=true`.

The static investigation result selects
`static_pipeline_reconstructed_without_contract_violation` and permits only a
separate diagnostic-protocol freeze. That successor is now specified by
[the diagnostic protocol](MM-005-browser-research-model-evaluation-generation-failure-diagnostic-protocol-v1.md),
without a runner or execution authority. Model evaluation, completed formal
measurement, quality, safety, repeatability, diagnostic execution, Serving,
promotion, and Runtime eligibility all remain false.
