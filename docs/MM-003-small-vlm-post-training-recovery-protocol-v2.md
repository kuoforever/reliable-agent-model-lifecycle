# MM-003 small-VLM post-training recovery protocol v2

> Status: frozen before any v2 model or GPU execution, then merged in PR #40.
> Its one registered execution has since passed; see the separate result review.

## Decision

This gate freezes a separate, outcome-neutral recovery lifecycle after the
single v1 execution was consumed with zero retry. It is not a retry of v1 and
does not edit or reuse the v1 output directory. The v1 failure lineage remains
read-only and exact.

The 26,553-byte preregistration is
`configs/mm003_small_vlm_post_training_protocol_v2.json`, with SHA-256
`02e36d5981e0ed4ac90bfdb3c5cc9c9e1f78ff29ff927020b0a41ebb27f55c0e`.
Its gate, experiment, and fixed output root are:

```text
gate=MM-003-small-vlm-post-training-recovery-protocol-v2
experiment=mm003-qwen2.5-vl-3b-qlora-sft-v2
output=work/training-runs/mm003-qlora-sft-v2
```

At freeze, all training, Adapter, evaluation, quality, repeatability,
portability, serving, promotion, and Runtime claims remain false.

## Exact recovery delta

The classification artifact defines a recursive JSON-leaf comparison against
the exact 17,601-byte v1 preregistration. Mappings are compared recursively,
arrays are atomic, JSON scalar types are strict, and floating-point signed zero
is distinct. Unlisted changes, additions, removals, and container replacements
fail closed.

Exactly 12 existing leaves may change:

1. preregistration version, gate ID, experiment ID, and recovery decision;
2. the five v2 Adapter/run/predictions/evidence/failure output paths;
3. the exact 13-item formal-gate array;
4. the execution-v2 next-gate ID and action.

The ten v1 protocol-source receipts remain exact. Only these two source
receipts are added:

| Source | Bytes | SHA-256 |
|---|---:|---|
| `src/fullcycle_bridge/mm003_post_training_protocol_v2.py` | 31,105 | `6fad583d6e83a273f490da1aa77b002e7d16b6bd356955feaa239ea4d6455dc7` |
| `scripts/run_mm003_qlora_post_training_v2.py` | 41,803 | `2a86ac6bdf365dc99ab28c3823be073169bc9d5cc974c20b0d85f43052d723af` |

Four closed sections are added: exact v1 failure lineage, prompt projection,
per-record prompt receipts, and the success-only result-review gate. Candidate
configuration values cannot serve as their own trust root: the validator reads
the tracked v1 config, raw failure receipt, classification artifact, train and
validation fixtures, and actual source bytes independently.

## Post-training prompt projection

The only failed behavior boundary changed by v2 is training-prompt rendering.
The baseline `ground-*` registry remains unchanged. A separate fixed registry
covers all 27 `pt-*` records and their exact observation modes.

The projector constructs, rather than copies and deletes, a payload with only:

- `case_id`;
- `observation_mode`;
- `instruction`;
- `available_tools`;
- `observation`.

The observation contains `ocr_text` and `grounding_cue`, plus `uia_controls`
only for `uia_only` and `fused`. Family IDs, training repeat groups, targets,
and raw `screenshot_regions` cannot enter the text prompt. Screenshot-only and
fused records still supply their registered PNG as a separate processor image;
the text exclusion is not an image prohibition.

All 18 train prompts followed by all 9 validation prompts are rendered before
dependency import, CUDA access, or model loading. Each receipt binds case ID,
mode, UTF-8 byte count, and SHA-256. The domain-separated aggregate digest is:

```text
sha256:bcbf8e87674ce2a668bdfe54ff4ecaba2e6db36899fc4e7c563867d1e2e9e102
```

Training reuses the same renderer and already validated in-memory records. A
prompt mismatch writes a fail-closed v2 receipt at
`stage=training_prompt_preflight`; it cannot reach model construction.

## Preserved lifecycle

The model revision, 14-file snapshot, dependency lock and wheel, training and
validation fixtures, targets, seed, NF4/BF16 QLoRA hyperparameters, Adapter
file set, independent fresh base-plus-Adapter reload, unchanged nine-case
MM-002 evaluation, scoring, resource caps, and authority contract remain
semantically identical to v1.

The registered v2 execution order is:

1. Validate CLI syntax, exact output path, commit syntax, and directory
   absence without consuming the lifecycle.
2. Exclusively create `work/training-runs/mm003-qlora-sft-v2` and start the
   registered timer.
3. Bind v1 failure lineage, all protocol sources, dependency wheel, fixtures,
   isolation evidence, and the exact v2 preregistration.
4. Render and verify all 27 prompt receipts before model or dependency load.
5. Validate the exact model manifest and locked environment, then run one
   three-epoch training lifecycle with zero retry.
6. Save exactly the registered Adapter files, delete training state, fresh-load
   base plus Adapter, and run the unchanged ordered MM-002 evaluation.
7. Synchronize CUDA, sample peak resources, stop the timer, and persist v2
   predictions/evidence. Evidence construction and persistence remain
   fail-closed but outside the elapsed metric, matching v1.

After lifecycle consumption, a protocol exception may expose only a bounded
project error code and JSONPath location. Generic or unsafe exception details
are recorded as null; messages, tracebacks, secrets, and absolute paths are not
serialized. No failure is retried.

`MM-003-small-vlm-post-training-result-review-v2` is success-only. Completed
evidence with any false formal gate records `next_gate=null`; it cannot
authorize the success review path.

## Formal gates

Execution-v2 requires all 13 gates:

1. protocol integrity;
2. exact model files;
3. locked environment;
4. training fixture integrity;
5. post-training prompt projection totality;
6. eval isolation;
7. offline single training run;
8. Adapter artifact integrity;
9. independent Adapter load;
10. unchanged MM-002 eval;
11. total scoring;
12. resource caps;
13. fail-closed claims.

This list defines completion of the registered measurement lifecycle, not a
required quality improvement. Even a formal pass cannot grant deployment,
commercial, serving, promotion, or Runtime authority.

## Validation and exact next action

The current frozen sources pass:

- 23/23 focused recovery tests on CPython 3.11.15, 3.12.12, and 3.13.7;
- the unified offline gate on all three interpreters: 560 tests, four expected
  Windows privilege skips, 49 audited source files, and `valid=true`;
- exact preregistration recomputation and `prepare --check`;
- Ruff and `py_compile` on the scoped Python files;
- strict mypy on the typed v2 contract with
  `python -m mypy --strict --follow-imports=skip`;
- `git diff --check`.

These checks do not load the model or GPU and do not establish training
success. The fixed v2 output directory remains absent.

After this protocol merges, the one exact next gate is
`MM-003-small-vlm-post-training-execution-v2`:

```powershell
.\work\training-env\Scripts\python.exe -I `
  .\scripts\run_mm003_qlora_post_training_v2.py run `
  --model-snapshot <exact-mm003-model-snapshot> `
  --protocol-freeze-commit <merged-protocol-commit> `
  --output-dir <repo-root>\work\training-runs\mm003-qlora-sft-v2
```

Invoke it exactly once with zero retry. Do not delete or reuse the v1 failure
directory, substitute the incomplete `mm003-metadata` snapshot, use MM-002 gold
as training data, or infer promotion from protocol compliance. If execution-v2
passes, the next gate is
`MM-003-small-vlm-post-training-result-review-v2`.

That registered next action has since completed once against merge commit
`3751a041ff12886a337df0066232379016fdbd9c`. All 13 measurement gates passed;
the outcome and its limits are frozen in
[the result review](MM-003-small-vlm-post-training-result-review-v2.md). The
consumed command above is retained for provenance and must not be invoked
again.
