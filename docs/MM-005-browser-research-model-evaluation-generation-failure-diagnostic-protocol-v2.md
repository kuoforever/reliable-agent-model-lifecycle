# MM-005 Browser Research generation-failure diagnostic protocol v2

## Status and authority boundary

This protocol-only gate was published through PR #81 as verified signed squash
commit `eb2aea3ca1eb5d82e823f7fc7a6aac7b5beb3fc9`. Its canonical
preregistration is 62,653 bytes with SHA-256
`0d00d89235bae8d0a2271934aaf18008d7c31c3f9a9f3c83a9afdd5d1a474a52`.

The gate freezes a new identity and a future output-parent preparation
contract. It adds no runner, result, failure, owner, progress, execution
authority, or runtime output; it invokes no diagnostic, model, processor,
PIL, torch, CUDA, browser, network, training, Adapter, or Runtime path. The v1
formal command remains permanently exhausted and is not retried.

## New identity

| Field | Frozen value |
|---|---|
| Experiment | `mm005-browser-research-model-eval-v2-generation-failure-diagnostic-v2` |
| Run | `mm005-browser-research-model-eval-v2-generation-failure-diagnostic-r2` |
| Output root | `work/evaluation-runs/mm005-browser-research-model-eval-v2-generation-failure-diagnostic-v2` |
| Attempt owner | `attempt-owner.json` under the output root |
| Progress | `progress.json` under the output root |
| Success | `diagnostic-result.json` under the output root |
| Failure | `diagnostic-failure.json` under the output root |
| Lease | `<output-root>.lifecycle/lease` |

Windows case-folded component identity and ancestor overlap are rejected
against both the original model-evaluation v2 roots and the v1 diagnostic
roots. Backslashes, drive/colon forms, non-canonical POSIX paths, and drifted
derived artifact or parent paths fail closed.

## Frozen lineage

The protocol independently proves the following ancestry and blob receipts:

- original v2 preregistration unique first-parent introduction
  `91b637c6b365ea8632b31335f5c74ac6c60e6b71`, static-result binding
  `c8541147717870992c60c6d2ea1c2f4ff68ee1d2`, and protocol-v2 base
  `266e9b695af0f93ae4c82e36ac484cb2d3d3a521`; all three bind the same
  120,315-byte payload with SHA-256 `512b3523...06c2e`;
- immutable static result at `c8541147...e1d2`, 39,843 bytes, file SHA-256
  `2be8caf8...ca93`, report digest `001b44cd...cde7`;
- v1 protocol at `9c90c5e6...9c04`, 57,143 bytes, SHA-256
  `13d18081...92d6`;
- v1 implementation at `7da39396...7fa1`, including the runner, protocol
  contract, result contract, both implementation test suites, and the frozen
  recovery-I/O dependency;
- v1 authority at `0a271e2c...51acb`, including the 2,706-byte
  `903e681c...e6b` authority artifact;
- v1 invocation closeout at `fd552896...424f`, including the 6,507-byte
  `d8a64be5...ddce` closeout and its validator contract; and
- the maintenance merge at `266e9b69...a521`.

The seven-record registry remains 22,354 bytes with SHA-256
`c3057651...5886`. The v1 closeout remains authoritative: invocation budget is
spent, attempt is unconsumed, and zero-owner failure is outside the terminal
grammar. For that pre-owner event, no retry, terminal synthesis, failure scope,
or outcome is available.

## Immutable scientific contract

The v1 decision rubric, checkpoint contract, evidence boundary, seven-record
control registry, resource contract, and terminal contract are reproduced
semantically exactly and digest-bound. This preserves:

- 17 environment fields, 9 ordered diagnostic substages, and seed 55006;
- the unchanged resource caps and one attempt per record;
- 126 durable substage checkpoint events and the 133-frame success grammar;
- exactly four owner-bound failure scopes and four allowed outcomes; and
- all original-v2 scientific input bindings.

No new scientific variable, result claim, Runtime cause, quality claim, or
recovery-v3 justification is introduced.

## Future output-parent preparation contract

Plan, check, build, and protocol freeze are read-only with respect to `work`.
They neither require nor create `work/evaluation-runs`; a missing parent is a
valid freeze topology. Predecessor roots, if present, are never read, trusted,
reused, or mutated and do not block plan/check; only the new v2 planned output
and lifecycle roots must be absent. Only a future execution-v2 implementation,
after a separately published authority, clean aligned HEAD, exact lineage, and
unclaimed topology, may perform this ordered sequence:

1. require repository root and `work` to be existing ordinary non-symlink,
   non-reparse directories, then verify `DirectoryTreeGuard(ROOT, work)`;
2. create only `work/evaluation-runs` with exclusive `os.mkdir`, without
   parents or `exist_ok`;
3. revalidate authority, clean HEAD, exact lineage, remaining unclaimed
   output/lifecycle/owner/progress topology, and root/work/created-parent
   identity and ancestry; the newly created parent is explicitly excluded from
   the pre-create absence predicate;
4. verify `DirectoryTreeGuard(ROOT, work/evaluation-runs)`;
5. enter the lifecycle lease;
6. atomically publish owner plus the `attempt_claimed` genesis frame; and
7. only then enter the first heavy-dependency boundary.

Collision, unsafe ancestry, identity drift, or guard failure must precede
lifecycle, claim, heavy import, model, and CUDA. Parent creation is neither an
attempt claim nor formal telemetry. A pre-owner failure spends the future
invocation budget but has no terminal, failure scope, outcome, or retry.
Directory identity checks detect observed replacement but do not eliminate
every same-privilege time-of-check/time-of-use mutation.

## Mandatory implementation-v2 regression

The next implementation gate must use a real temporary filesystem with an
existing safe `work` directory and missing `evaluation-runs`. It may not mock
the output-parent helper or `DirectoryTreeGuard`. It must exercise the future
`execute` path through exclusive parent creation, parent guard, lifecycle,
owner, and genesis, then raise a controlled exception at the first heavy
boundary while proving the registered Python socket APIs, model-load-capable
production boundary, and CUDA workload remain uncalled.
This regression is model-free, does not establish authority, and does not
consume the formal invocation budget; after owner/genesis its controlled
failure uses the existing `pre_record_lifecycle` scope.

## Implementation-v2 realization

The separate implementation-v2 slice now freezes that exact ordered core.
Its public `--execute` path can construct the closed internal context only from
a separately published, canonical authority at clean aligned exact `master`.
There is no CLI flag, environment variable, or public API that grants test
authority. Plan and check remain byte- and topology-read-only when the output
parent is missing.

The PR #81 protocol merge
`eb2aea3ca1eb5d82e823f7fc7a6aac7b5beb3fc9` remains the immutable protocol
receipt and ancestor. The non-lifecycle, zero-LFS-bandwidth CI maintenance
merge M1 `e5e618b491a3dc38dbed9cdcd4c6c384f2df0f54` has the protocol merge as
its unique direct parent. The later non-lifecycle exact-head checkout merge M2
`8c679eba08a979fb60bfd87fbe8c73c8725d89c0` is the literal implementation
base and has M1 as its unique direct parent. The implementation freeze must
preserve two publication stages: initial implementation I1
`e185c76e0d0ace44a13e10f06d8644939e1981b8` has M2 as its unique direct
parent, and the compatibility-corrected final implementation I2 has I1 as its
unique direct parent. Both reviewed M2-to-I1 and M2-to-I2 deltas are exactly
the same 11 paths, while I1-to-I2 is non-empty and confined to that set. The
three implementation sources are first introduced at I1 and their final bytes
are bound to I2.

The core revalidates Git, tracked source bytes, first-parent lineage, hidden
index flags, and unclaimed topology before creating anything. It guards
`ROOT -> work`, calls exactly one one-argument `os.mkdir` for
`work/evaluation-runs`, repeats authority/source/topology and root/work/parent
identity checks, constructs and verifies the real parent guard, enters the
lifecycle lease, and atomically renames owner plus genesis into place. Only
after claimed-state revalidation does it call the injectable
`first_heavy_dependency_boundary`.

The mandatory regression uses a real temporary Git clone and filesystem. It
constructs test `master` explicitly from literal I1, verifies the unique chain
from the protocol merge through M1, M2, and I1, then creates a synthetic
test-only I2 and exact-10-path authority lineage. It verifies both M2
implementation deltas and the non-empty I1-to-I2 subset. It begins with safe `work` and no
parent, and mocks none of `os.mkdir`, `DirectoryTreeGuard`, lifecycle, claim,
or filesystem I/O. The sole executed injection is a controlled exception at
the first-heavy boundary after real owner and genesis publication. The
resulting authenticated failure is `pre_record_lifecycle`; the
model/PIL/torch/CUDA/network module set does not change, fail-on-call spies
prove the registered Python socket APIs, model-load-capable production
boundary, and CUDA workload remain uncalled, and no formal invocation budget
is consumed. The claim does not extend to unregistered native or subprocess
networking. An empty intermediate commit
between I1 and the final implementation freeze is rejected before output-parent
mutation.

Phase-negative coverage preserves evidence rather than erasing it: pre-create
failure makes no parent or lease; post-create failure may leave only the new
parent; lifecycle-stage failure may leave lifecycle-only; and owner staging
remains reserved, durable, and non-retryable. No pre-owner phase can publish a
terminal, failure scope, or outcome. A claimed topology routes only to
reconciliation and cannot re-enter the heavy boundary.

## Locked next action and stop conditions

The sole active gate is now the compatibility correction of the separate
`MM-005-browser-research-model-evaluation-generation-failure-diagnostic-implementation-v2`.
I1 remains its immutable initial publication receipt; I2 becomes its final
compatibility freeze without creating authority. After I2's clean merge,
checks, review, conflict, strict-up-to-date state,
branch cleanup, and post-merge observation are clear, the only successor is
`MM-005-browser-research-model-evaluation-generation-failure-diagnostic-execution-authority-v2`.
Authority and exact-once execution remain later independent gates.

Stop if any immutable receipt, scientific subtree, identity, derived path,
parent contract, or exact 11-path implementation slice drifts; if planned
output or lifecycle roots exist; if a v1 path/command/identity is reused; or
if any step would execute a diagnostic or add authority/output state.
