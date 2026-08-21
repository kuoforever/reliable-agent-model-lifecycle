# MM-003 post-training eval repeatability protocol v1

> Status: protocol merged; its one registered replay has been consumed and the
> result reviewed. The fixed output must never be deleted, reused, or retried.

## Decision

This gate freezes one outcome-neutral, eval-only replay of the unchanged
MM-003 recovery-v2 Adapter against the unchanged nine-case MM-002 synthetic
suite. It is a new measurement lifecycle, not an execution-v2 retry. It does
not retrain, edit, copy, merge, or save the Adapter or base model.

The frozen preregistration is
`configs/mm003_small_vlm_post_training_eval_repeatability_protocol_v1.json`.
It is 22,951 bytes with SHA-256
`723db665f98e53ef2fe968ee7c6fe663b42d79b86176eef5cf70f11ccc4a312b`.
`prepare --check` recomputes those exact bytes from the frozen sources and
upstream artifacts.

```text
protocol gate=MM-003-small-vlm-post-training-eval-repeatability-protocol-v1
execution gate=MM-003-small-vlm-post-training-eval-repeatability-execution-v1
result review=MM-003-small-vlm-post-training-eval-repeatability-result-review-v1
failure classification=MM-003-small-vlm-post-training-eval-repeatability-failure-classification-v1
experiment=mm003-qwen2.5-vl-3b-qlora-sft-v2-eval-repeatability-v1
output=work/evaluation-runs/mm003-qlora-sft-v2-eval-repeatability-v1
```

At protocol freeze, every execution, repeatability, quality, portability,
serving, promotion, commercial, and Runtime claim remains false.

## External trust roots

The protocol first invokes the strict recovery-v2 result validator. It thereby
recomputes the original protocol, execution evidence, scorer result, Adapter
topology, all 7,372,800 F32 values, and review decision before accepting the
reference observation.

The preregistration also binds these reference receipts explicitly:

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| recovery-v2 preregistration | 26,553 | `02e36d5981e0ed4ac90bfdb3c5cc9c9e1f78ff29ff927020b0a41ebb27f55c0e` |
| training run | 6,853 | `474595081a20c46a62f664459b734d57ec03c8ddf121c9aedc055e16a052c516` |
| first predictions | 2,241 | `c2c703e5896fe64df9e156bda9d38975b92c1bf18c72f74f5a232dcbbbc4a028` |
| first evidence | 21,122 | `2190281e3e8acf97139e08c9949535a07b326897e23c5999a7f4750fccedabd5` |
| result review | 11,311 | `3dff57b17eb4fc9966ab53fe92faea8921fb34b485e389aaa19af64610db957d` |
| Adapter README | 206 | `a73f9a4e826eca0a56f08ac2e7d415670b29eaae02bf501aa838ac23aaf3ebdb` |
| Adapter config | 791 | `e8edf34169cc15c25e98965a5873e27c6eb54f4f95543e60d0452ec2fec60055` |
| Adapter weights | 29,529,752 | `d93d2ea2d9f05564093cbb0b1286d2c368c54b01e847f1c37a98e00fb2914701` |

The Qwen model ID, revision, 14-file manifest, dependency lock and local
bitsandbytes wheel, Windows/CUDA/GPU environment, MM-002 suite raw and
canonical digests, six screenshots, case order, system/user prompt builders,
compiler, scorer, generation parameters, and review-only six-case taxonomy are
also exact. Eval gold remains prohibited from training.

Seventeen source receipts cover the actual execution and validation graph. In
particular, the closure names the v1 base runner that provides `_generate_one`
instead of relying on the older source map's differently named baseline-v2
runner. It also binds the package initializer and consumer imported before the
protocol module, the baseline failure-classification contract, both baseline
contracts and scorers, the post-training contracts and v2 runner, both
upstream result validators, the new contract and runner, and the dependency
lock. This authenticates the static merged source closure; it does not claim
resistance to an actively malicious local repository owner changing source
while the process is running. The formal run therefore requires a trusted
local OS and repository owner.

## Eval-only execution contract

The registered execution has one fresh base load, one independent read-only
Adapter load, one full nine-case run, nine ordered generation calls, zero
retry, and zero network. It preserves the v2 seed, NF4/BF16 quantization,
SDPA, processor pixel limits, greedy generation, 256-token maximum,
repetition penalty, prompt, compiler, and scorer.

The new runner has two no-training layers:

1. Static tests reject training-only imports and calls to `.train()`,
   `.backward()`, `.step()`, or `save_pretrained()`.
2. Runtime requires `PeftModel.from_pretrained(..., is_trainable=False,
   local_files_only=True)`, `model.eval()`, no parameter with
   `requires_grad=True`, and a `torch.inference_mode()` case loop.

The Adapter directory must contain exactly the three frozen files. Each file
is size/hash checked before load, the safetensors topology and all F32 values
are audited during authenticated preflight, and locked file identity,
size/hash, and exact directory membership are reverified after evaluation.
Any mutation fails closed; the postcondition does not claim to rerun the full
tensor-value audit.

The runner records distinct attempt and completion counters for base load,
Adapter load, the full eval, and each generation call. Training runs,
optimizer steps, backward calls, Adapter writes, network attempts, and retries
must all remain zero on a valid completion.

## One-shot lifecycle and output policy

All source, upstream evidence, Adapter, suite, screenshot, wheel, model
manifest, CLI path, Python-launch mode, and freeze-commit checks run as
CPU-only preflight. The fixed output directory must not exist. The runner first
creates a random same-parent staging directory and exclusively writes a
canonical `attempt-owner.json` carrying a 256-bit process token. Its same-volume
atomic rename to the fixed output directory is the only attempt-consumption
boundary. Therefore, the formal directory is never visible without its owner
marker; an asynchronous interrupt after the rename can prove whether this
process owns the consumed attempt.

After the fixed directory is claimed, no failure may delete or reuse it. The
runner locks the directory and every durable child, rechecks their identities,
bytes and hashes, and requires an exact child-name set. It then sets Hugging
Face and Transformers offline modes and installs a socket guard that rejects
and counts any outbound connection attempt. A completed run contains,
exclusively:

1. `attempt-owner.json`, prepared before consumption and authenticated against
   the freeze commit and preregistration bytes;
2. `evaluation-candidate.json` after nine raw/compiled cases and before
   scoring;
3. `predictions.json` after total scoring and validation;
4. `evidence.json` after Adapter postcondition and layered comparison.

Under the registered trusted-local-owner and stable-filesystem assumptions, an
ordinary or asynchronous exception after consumption writes a sanitized
`failure.json` with stage, bounded exception type/code/location, counters,
completed case IDs, zero retry, all-negative claims, and the registered
failure-classification gate. It never serializes an exception message,
traceback, or machine path. If the owner marker, directory identity, or a
durable artifact can no longer be authenticated, the runner refuses to invent
a receipt; the original directory must be preserved for explicit failure
classification and remains permanently ineligible for retry.

## Layered comparison

The first and replay observations are each validated independently. Stored
compiled predictions and scores cannot authorize themselves: the frozen
compiler and scorer recompute both sides from raw outputs.

1. **Raw layer:** exact UTF-8 string equality by case, exact generated-token
   counts as a separate diagnostic, aggregate digests, and mismatch case IDs.
   No normalization is allowed.
2. **Compiled layer:** each raw output is recompiled; stored and recomputed
   predictions must match before type-strict canonical JSON comparison across
   runs. Compiler-fallback drift is recorded separately.
3. **Metric layer:** both prediction sets are rescored. Every metric's exact
   `correct`/`total`/`value`/`status` structure, including null/not-applicable
   semantics, receives its own comparison and mismatch name.

The evidence preserves independent facts for all-layer equality, raw-only
drift with compiled/metric equality, compiled drift with metric equality, and
metric drift. Behavioral inequality is a valid measurement outcome, not a
runner exception.

## Formal gate and claims

The 13 formal gates cover protocol/reference integrity, exact model and
Adapter files, locked environment and MM-002 inputs, offline single replay,
prediction identity, attempt ownership, exact candidate/predictions artifact
binding, complete layered comparison, the inherited 1,800-second and 16.5-GB
allocated/reserved caps, and fail-closed claims.

Equality is deliberately not a formal execution gate. If all measurement and
resource gates pass, either equality or drift routes to the independent
result-review gate. Execution evidence may then set only:

- `replay_executed=true`;
- `model_evaluated=true`;
- `formal_measurement_complete=true`.

It must keep bounded same-machine eval repeatability false until review. The
review may establish that narrow claim only if all registered layers are
exact. It can never establish training repeatability, repeat variance,
cross-machine/driver/library reproducibility, resource repeatability,
generalized quality, rejection safety, real desktop behavior, portable or
commercial eligibility, serving, promotion, or Runtime authority.

A resource or integrity failure, or an incomplete consumed attempt, routes to
the separately registered failure-classification gate and cannot authorize
result review or an automatic rerun.

## Validation, consumed execution, and result

The focused tests exercise deterministic preregistration construction,
external self-reseal rejection, strict JSON, all three comparison layers,
resource/integrity classifications, no-training AST guards, fake one-load/
nine-call execution, zero internal retry, socket denial, owner-token rejection,
atomic-claim interrupt recovery, durable evidence recovery without dual
terminals, and locked exact output sets. Final multi-version counts and the
preregistration's exact bytes/hash are covered by the same gate. The focused
suite passes 29/29 tests on local CPython 3.11.15. The unified gate passes 600
tests on local CPython 3.11.15 and 3.13.7 with `valid=true`, four expected
Windows privilege skips, and 50 audited source files. Ruff, `py_compile`,
`prepare --check`, and `git diff --check` pass. Pull-request CI remains
responsible for the independent CPython 3.12 result.

Those protocol checks did not import ML dependencies, load the model, access
CUDA, or create the formal output directory. After PR #42 merged, the original
Anaconda base was found missing during the initial recovery audit. A CPython
3.12.12 base supplied through uv was restored at the registered path; the
formal preflight then passed the registered environment fields. This did not
recover the original vendor or binary identity and did not create a complete
hash-locked transitive dependency closure.

The following registered command was subsequently invoked exactly once against
freeze commit `c72b3bd1666ed6b03d9425e1dbaacfe115dda4f8`. It is retained only
as historical protocol evidence and **must not be invoked again**:

```powershell
.\work\training-env\Scripts\python.exe -I -B -X pycache_prefix=NUL `
  .\scripts\run_mm003_post_training_eval_repeatability.py run `
  --model-snapshot .\work\model-cache\mm003-model\models--Qwen--Qwen2.5-VL-3B-Instruct\snapshots\66285546d2b821cf421d4f5eb2576359d3770cd3 `
  --preregistration .\configs\mm003_small_vlm_post_training_eval_repeatability_protocol_v1.json `
  --protocol-freeze-commit c72b3bd1666ed6b03d9425e1dbaacfe115dda4f8 `
  --output-dir .\work\evaluation-runs\mm003-qlora-sft-v2-eval-repeatability-v1
```

The replay passed all 13 gates with raw and compiled 9/9 exact, metrics exact,
generated-token counts exact, compiler-fallback status exact, zero retry, and
no training or Adapter write. The model-free result review rebuilt the formal
evidence byte-for-byte and establishes only bounded same-machine fixed-eval
repeatability. `all_layers_exact` names raw / compiled / metric evidence layers,
not Transformer internals, and token-ID sequences were not persisted.

See the [result review](MM-003-small-vlm-post-training-eval-repeatability-result-review-v1.md)
for exact receipts, resource observations, environment-recovery limitations,
and claim boundaries. The single next gate is
`MM-004-multimodal-hard-negative-data-protocol-v1`; the consumed MM-003 output
directory remains permanently ineligible for deletion, reuse, or retry.
