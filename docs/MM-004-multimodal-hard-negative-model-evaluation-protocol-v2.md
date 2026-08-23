# MM-004 multimodal hard-negative model-evaluation protocol v2

## Outcome

The v2 preflight repair was frozen before any model import or call. Its
canonical 50,642-byte preregistration is
`configs/mm004_multimodal_hard_negative_model_evaluation_protocol_v2.json`,
with SHA-256
`bee2093d54d95cc52303c57c598d99a071aff85bef9f56605adeb2b604f8c0d9`.

Both the predecessor v1 output and the new v2 output remain absent. Every
execution, model, training, quality, safety, serving, promotion, and Runtime
claim is false.

## Preserved evaluation contract

V2 changes no candidate, input, prompt, compiler, metric, generation, resource,
or terminal-evidence semantics:

- exact `Qwen/Qwen2.5-VL-3B-Instruct` revision plus read-only MM-003 Adapter
- 56 generated records and 28 images in fixed train-then-validation order
- image plus instruction, path/hash-free observation, and candidate action only
- strict single-key `accept` / `reject` JSON compiler; invalid fallback is wrong
- total overall, variant, pair, split, category, and compiler metrics
- one fresh base load, one independent Adapter load, 56 offline calls, no retry
- 1,800 seconds and 16.5 GB allocated/reserved integrity caps
- owner-marked single attempt with durable candidate before scoring, then
  predictions/evidence or a fail-closed failure receipt

No accuracy threshold changes measurement completion or permits a retry.

## V1 predecessor classification

The exact v1 protocol and merge commit are inputs to v2. V1 reached only
freeze-commit receipt validation. It created no output owner, imported no
model, used no GPU, made zero model calls, and did not consume its attempt.

The failure was representation-specific. The tracked Adapter weight is a
133-byte Git LFS pointer whose OID and declared size bind the hydrated
29,529,752-byte safetensors payload. V1 compared the pointer bytes directly to
the hydrated receipt even though both identities agreed.

## Exact repair

At the merged v2 freeze commit, the runner requires the tracked Adapter entry
to equal the canonical Git LFS pointer constructed from the registered
hydrated SHA-256 and byte count. Independently, before and after evaluation, it
opens and holds the hydrated Adapter read-only and verifies its full payload
receipt. This separates Git storage representation from execution bytes without
weakening either check.

All other tracked protocol/context/generated receipts still compare directly
against the v2 freeze commit. The v1 output must remain absent, and the v2
output must be absent before formal execution.

## Validation evidence at freeze

The focused v2 suite passes 13/13 tests, including independent verification of
the exact 133-byte Git LFS pointer and the 29,529,752-byte hydrated payload.
Full-repository Ruff, scoped strict Mypy on the contract and runner,
`py_compile`, preregistration `--check`, the feature-branch formal-command
negative check, and `git diff --check` pass.

Local CPython 3.11.15, 3.12.12, and 3.13.7 each pass the unified 648-test gate
with four expected Windows privilege skips, 53 audited source files, and
`valid=true`. The gate independently reconstructs v2, binds the exact v1
predecessor/classification, verifies that v1 consumed no attempt or model
call, and requires both fixed outputs to remain absent. These results prove
the repaired preflight contract, not model-load or evaluation success.

## Next gate

After the exact v2 protocol is merged with checks, reviews, and conflicts
clear, the next gate is
`MM-004-multimodal-hard-negative-model-evaluation-execution-v2`. A successful
terminal routes to the v2 result-review gate; a consumed failure routes to the
v2 failure-classification gate. The execution remains read-only and has no
Runtime authority.
