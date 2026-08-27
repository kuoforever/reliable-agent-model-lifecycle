# MM-005 Browser Research model-evaluation protocol v1

## Outcome

The outcome-neutral read-only model-evaluation protocol is frozen before any
model import or call. Its canonical preregistration is
`configs/mm005_browser_research_model_evaluation_protocol_v1.json`: 116,152
bytes with SHA-256
`84cd3d20d5a678a8ad0f7c38ad12e057225a4250e8143c5f004c2eaef8981f3f`.

PR #68 first published the independent Adapter/Verifier implementation as
`1177d5649952af6c04f713f5cfbbde47388e3769`. All six Linux Python-matrix
checks passed, there were no reviews, comments, review threads, or conflicts,
and both feature-branch copies were deleted before this protocol slice began.

At protocol freeze, the fixed evaluation output directory is absent. No
attempt has been claimed, no model has been imported or called, and no GPU
measurement has occurred.

## Read-only candidate and closed lineage

The only registered candidate is local
`Qwen/Qwen2.5-VL-3B-Instruct` revision
`66285546d2b821cf421d4f5eb2576359d3770cd3` plus the read-only
`mm003-qlora-sft-v2` Adapter. The model and Adapter receipts, MM-004 candidate
protocol/evidence/result review, Browser Research Adapter/Verifier evidence,
merged lineage commits, all generated dataset artifacts, and 12 protocol
source receipts are closed inputs.

The registered execution environment is Python 3.12.12, PyTorch 2.6.0+cu124,
Transformers 4.49.0, bitsandbytes 0.50.1, and the RTX 4090 Laptop GPU. Training,
Adapter mutation, model/tensor saving, network access, live-browser access,
capture, and Runtime integration are forbidden.

## Input and prompt isolation

All 32 synthetic records are measured once in frozen record-ID order: 24 train
and eight validation records across four task families and four source kinds.
The protocol binds 68 ordered source relationships. Its 32 canonical model
payloads total 81,796 bytes, the 68 ordered screenshot inputs total 600,604
bytes, and the corresponding 68 source snapshots total 118,742 audit-only
bytes.

The model sees only:

- the fixed Browser Research system prompt;
- canonical JSON with `instruction`, `observation`, `source_kind`, and
  `task_family_id`; and
- one to three exact PNG screenshot channels in the record's frozen source
  order.

Expected output, record/split/provenance identity, Verifier metadata, receipts,
real repository paths, and source-snapshot bytes remain outside the model
payload. Source snapshots are independently byte-bound to the frozen dataset
but are never opened or passed to the model. Every model payload, prompt
projection, screenshot, and audit snapshot has a preregistered byte count and
SHA-256 receipt.

## Compiler, Verifier, and metrics

The strict compiler accepts only one UTF-8 JSON object with exactly `answer`
and `citation_refs`. Citation refs must be ordered, unique, syntactically valid,
and observed in the supplied static DOM projection. Duplicate keys, extra keys,
non-finite values, wrong scalar types, malformed JSON, and oversized output are
invalid and score as wrong.

The independent deterministic Verifier uses no model judge. It registers:

- compiler validity, normalized answer exactness, ordered citation exactness,
  and joint exactness;
- citation-to-observed-source binding and minimum distinct-source coverage;
- latest-published-source accuracy on the eight freshness cases; and
- total per-split, per-task-family, and per-source-kind metrics.

Accuracy thresholds cannot change whether the formal measurement completed.
An unfavorable result must still be persisted and reviewed; it cannot be
discarded or retried as a failed experiment.

## Single-attempt execution contract

The future formal runner is registered for exactly one owner-marked run:

| Counter or cap | Frozen value |
|---|---:|
| Fresh base-model loads | 1 |
| Independent Adapter loads | 1 |
| Ordered generation calls | 32 |
| Ordered screenshot inputs | 68 |
| Source-snapshot inputs to the model | 0 |
| Retries | 0 |
| Network / training / backward / optimizer operations | 0 |
| Elapsed-time cap | 1,800 seconds |
| Peak allocated/reserved GPU-memory cap | 16.5 GB |

The attempt becomes consumed only when the fixed output directory is atomically
claimed with an exclusive owner receipt. Before that claim, a failed preflight
may be corrected; after it, retry is forbidden. Formal execution additionally
requires this exact protocol to merge and the supplied freeze commit, local
`master`, and `origin/master` to be identical.

The registered invocation form is:

```powershell
work\training-env\Scripts\python.exe -I -B -X pycache_prefix=NUL scripts\run_mm005_browser_research_model_evaluation.py --protocol-freeze-commit <merged-protocol-commit>
```

This command is not authorized from the protocol feature branch.

## Terminal evidence and failure handling

A successful terminal must persist the owner, evaluation candidate,
predictions, and evidence under the fixed output directory. A consumed failure
instead persists one mutually exclusive failure receipt. Failure receipts keep
only the safe exception type, stage, owner binding, counters, and completed-
record prefix; they exclude exception messages, tracebacks, secrets, and
machine paths.

Resource-cap failure preserves completed measurements but fails the integrity
gate. It does not authorize a retry or turn a partial result into evidence of
quality.

## Claim and Runtime boundary

At protocol freeze, generation/dataset validation and model-free Adapter/
Verifier implementation/execution remain established. `attempt_consumed`,
`evaluation_executed`, `model_evaluated`, and `formal_measurement_complete` are
false. Model training, Adapter mutation, quality improvement, generalized
quality, safety, prompt-injection safety, real-content behavior, Serving,
promotion, cross-machine reproducibility, and Runtime eligibility are also
false.

Page content and model output have no execution authority. Runtime remains the
sole policy, approval, WAL, grounding, budget, recovery, and desktop-dispatch
boundary; no Runtime repository or integration change is authorized.

## Validation evidence at freeze

Sixteen focused adversarial tests cover byte-exact reconstruction, upstream
lineage, prompt closure and gold/path/snapshot isolation, fake-dependency
32-call and 68-image lifecycle, strict compilation, citation binding, source
coverage, latest-source freshness, total metrics, resource caps, owner/failure
receipts, artifact resealing, dataset-byte tampering, feature-branch formal
rejection, and absence of top-level model imports or write paths.

Ruff, scoped strict Mypy on the contract/builder/runner, `py_compile`, and
protocol `--check` pass at local freeze. Local CPython 3.11.15, 3.12.12, and
3.13.7 each pass the complete unified 868-test gate with four expected Windows
privilege skips, 68 audited source files, and `valid=true`. Clean PR checks,
review/conflict audit, merge, branch cleanup, and master alignment remain
publication gates.

These checks establish a frozen measurement contract and deterministic
reconstruction of its repository-bound inputs. They do not establish model-
load success, model quality, safety, model-evaluation or training
repeatability, cross-machine reproducibility, Serving, promotion, or Runtime
eligibility.

## Next gate

Only after this exact protocol passes the complete local and PR validation
matrices, merges cleanly, deletes both feature-branch copies, and leaves local
`master` aligned with `origin/master` may
`MM-005-browser-research-model-evaluation-execution-v1` become active. It may
consume exactly one offline, zero-retry, read-only formal attempt. This protocol
branch authorizes no model execution.
