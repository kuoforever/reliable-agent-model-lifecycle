# MM-005 Browser Research generation-failure diagnostic protocol v1

## Status and scope

This artifact freezes the outcome-neutral protocol gate
`MM-005-browser-research-model-evaluation-generation-failure-diagnostic-protocol-v1`.
It is a protocol-only slice: there is no diagnostic runner, no result contract,
and no diagnostic execution. It does not import or call a processor, model,
PIL, torch, or CUDA; use a browser or network; capture real content; train;
write an Adapter; retry v1/v2; or change the Runtime repository.

The next gate is the separate
`MM-005-browser-research-model-evaluation-generation-failure-diagnostic-implementation-v1`.
That gate may freeze implementation and result semantics after this protocol is
cleanly merged, but it still may not execute the diagnostic without separate
authority and a complete resource preflight.

## Immutable predecessor

The protocol binds the PR #75 signed squash merge
`c8541147717870992c60c6d2ea1c2f4ff68ee1d2` and the immutable result:

- path:
  `baseline/mm005-browser-research-model-eval-v2-generation-failure-investigation-v1.json`
- bytes: `39,843`
- file SHA-256:
  `2be8caf8dbc35d2741d81d408f21fea08d7961cc970590a25922bc757485ca93`
- report digest:
  `001b44cdb9d0a11a4be48e10f6653074e4bf407a43daaad1930c6d92e5f8cde7`
- selected outcome:
  `static_pipeline_reconstructed_without_contract_violation`
- investigation implementation freeze:
  `c2b04f68dfbb0f96423ecf83a8d73529fdf9d055`

It also binds the exact 120,315-byte v2 preregistration at that commit,
SHA-256
`512b3523196bf80e7e137c7777c205fa92a57acf371464f3f65671c406706c2e`,
plus ten canonical semantic-subtree digests. A selected 20-file c854
predecessor/publication closure is directly checked against its commit blobs;
the exact v2 preregistration and source-receipt subtree preserve the wider v2
source identity without claiming that this slice directly re-reads every
transitive source blob. Every directly bound source must equal its c854 blob;
it cannot drift and then self-seal under a fresh receipt.

The static pipeline reconstructed without reproducing the claimed generation
failure. That is not evidence that the historical failure did not occur, that
the historical Runtime was healthy, or that a model, CUDA runtime, driver,
processor, data record, or Adapter was or was not causal. The Runtime root
cause and failed runtime substage remain unresolved.

## New identity and output

The diagnostic cannot be disguised as a retry of the consumed v2 attempt. It
uses:

- experiment ID:
  `mm005-browser-research-model-eval-v2-generation-failure-diagnostic-v1`
- run ID:
  `mm005-browser-research-model-eval-v2-generation-failure-diagnostic-r1`
- output root:
  `work/evaluation-runs/mm005-browser-research-model-eval-v2-generation-failure-diagnostic-v1`

The output and sibling lifecycle-lease root must both be absent at protocol
freeze. Identity comparison is Windows case-insensitive and rejects equality
or ancestor/descendant overlap with every v1/v2 output or lease root, including
cross-collisions. The builder uses exclusive config creation. Both creation and
`--check` snapshot the exact HEAD, c854 blobs, current source bytes, and output
absence, then revalidate them immediately before write or `valid=true`.
Inherited `GIT_*` variables are discarded; global/system config, legacy grafts,
replace objects, and commit-graph acceleration are disabled; and every existing
parent directory must be an ordinary non-reparse directory.

The portable pathname check does not establish resistance to a same-privilege
concurrent actor replacing a repository ancestor between parent observation and
exclusive create. No such actor or reparse parent is present in this validation.
A hostile-concurrent-filesystem threat model would require a separate Windows
handle-relative/no-reparse creation primitive before relying on the builder.

## Records and execution order

The fixed result's 22,354-byte seven-record registry is bound by SHA-256
`c3057651c41be738257db7ae0af4c8bcdf3419493d22064b8ea9eb935d758886`.
The new diagnostic order is closed:

1. the three authenticated completed-prefix controls, preserving their exact
   historical order;
2. the target record
   `sha256:26b3a9da0467d1c18cc4a050ec10dc03a415a9c3a38a2a37de8b9805c67adaf7`
   as the fourth generation attempt;
3. the three same-shape static controls.

The protocol freezes one fresh runtime session, one formal invocation budget,
one attempt per record, zero retry, and stop-on-first-exception behavior. A
failure therefore cannot be followed by unregistered continuation or result
shopping. Content digest differences remain excluded from causal evidence;
only the previously closed structural fields may be compared structurally.

## Durable diagnostic checkpoints

Each record has exactly nine ordered runtime substages and one unique
`started -> completed` durable pair:

| Substage | Started checkpoint | Completed checkpoint |
| --- | --- | --- |
| runtime messages build | `runtime_messages_build_started` | `runtime_messages_build_completed` |
| pre-generation CUDA sync | `pre_generation_cuda_sync_started` | `pre_generation_cuda_sync_completed` |
| chat template | `chat_template_started` | `chat_template_completed` |
| processor tensorization | `processor_tensorization_started` | `processor_tensorization_completed` |
| processor device transfer | `processor_device_transfer_started` | `processor_device_transfer_completed` |
| model generate | `model_generate_started` | `model_generate_completed` |
| decode | `decode_started` | `decode_completed` |
| post-generation CUDA sync | `post_generation_cuda_sync_started` | `post_generation_cuda_sync_completed` |
| case result build | `case_result_build_started` | `case_result_build_completed` |

The 18-event per-record set, order, record ID, and diagnostic index are exact.
Seven explicit per-record plans therefore close a 126-event maximum and exact
success grammar. A completed record requires all 18 events; completed record
IDs must be an exact case-order prefix; the active record must be the first
incomplete record; and a failed active record may contain only a non-empty
proper prefix of its own plan. Events are
canonical JSONL, append-only, monotonically sequenced, SHA-256 chained, flushed
and fsynced before entering the next substage, and protected by a single-writer
lifecycle lease acquired before the attempt claim.

A failure terminal has one of four disjoint scopes. A pre-record lifecycle
failure permits only an exact session-event prefix and no record checkpoint
reference; an inter-record transition failure permits an exact completed-record
prefix but no active-record event; an active-record failure requires a proper
event prefix and may reference only the latest started/completed checkpoint in
that same record. The completed checkpoint is nullable when the first substage
has started but none has completed. A post-record terminalization failure
requires the full seven-record order, no active record, exactly 126 durable
substage events, exact final-record `case_result_build_started` and
`case_result_build_completed` references, and an absent success-terminal-ready
event. Every failure scope ends only with `failure_terminal_ready`; the
post-record scope permits only `diagnostic_inconclusive`. This narrows where an
error was observed without fabricating a cross-scope checkpoint. It does not
prove that an asynchronous accelerator error originated in that interval or at
a CUDA synchronization call. `failed_runtime_substage_isolated` and
`runtime_root_cause_established` therefore remain false at protocol freeze.

## Resource, terminal, and authority contracts

The scientific inputs bind the v2 base model/revision/snapshot, Adapter
receipts, seed, maximum new tokens, formal Python path, CUDA device map, and
the registered 1,800-second / 16.5-GB integrity caps. The resource contract is
independent from the consumed v2 attempt. Exact package, platform, driver,
CUDA, GPU, and capability values were not durably authenticated by the
predecessor result, so this protocol does not invent them. A future
implementation preflight must bind every required value exactly; any missing
or unverifiable value blocks execution. Resource comparison is diagnostic,
not a quality or repeatability claim.

Success and failure terminals are mutually exclusive and exclusively created
after a matching terminal-ready checkpoint. A future failure artifact may
persist only safe `exception_type` text plus closed receipts and checkpoint
state; message, traceback, absolute path, and secret text are forbidden. The
exact terminal/result schemas are intentionally deferred to the implementation
gate.

The protocol authorizes only its own freeze and, after a clean merge, the
implementation-freeze gate. Diagnostic execution, processor/model/CUDA use,
live browser/network, capture, training, v1/v2 retry, and recovery v3 all
remain unauthorized. The Runtime remains the sole policy, approval, WAL,
grounding, budget, and desktop-dispatch boundary.

At freeze, diagnostic attempt consumption/execution, historical Runtime
health, static root-cause reproduction, failed-substage isolation, Runtime
root-cause establishment, remediation delta, recovery-v3 justification,
formal model measurement, model evaluation, quality, safety, evaluation or
resource repeatability, cross-machine reproducibility, Serving, promotion, and
Runtime eligibility all remain false.

## Outcome-neutral rubric

No outcome is selected at freeze. A later closed result contract may select
exactly one of:

- `diagnostic_protocol_or_lineage_invalid`
- `diagnostic_completed_without_observed_runtime_failure`
- `diagnostic_failure_observed_between_durable_checkpoints`
- `diagnostic_inconclusive`

None of those names alone establishes historical Runtime health or causal
origin. Recovery or remediation routing is not selected by this protocol.

## Validation

The 57,143-byte canonical config has SHA-256
`13d1808168819414df2a0ca33d1f59e5e8efd52de6f0b49946d02cf070c992d6`.
On local CPython 3.11.15, 3.12.12, and 3.13.7, all 26 focused tests pass and
the canonical builder check reconstructs the same bytes. Each complete unified
gate passes 987 tests with four expected Windows privilege skips, 75 audited
source files, and `valid=true`. Ruff 0.15.22 check, format checks on the new
contract/builder/tests, scoped strict Mypy 2.3.0 on the typed contract/builder,
`py_compile`, and `git diff --check` also pass.

This evidence establishes deterministic protocol reconstruction and fail-closed
validation only. The frozen config still has `diagnostic_output_absent=true`,
`diagnostic_executed=false`, `runtime_eligible=false`, and a 126-event maximum;
no diagnostic result or earlier draft result is carried forward.

```powershell
$pythons = @(
    "work\python-matrix\conda311\python.exe",
    "work\training-env\Scripts\python.exe",
    "python"
)
foreach ($python in $pythons) {
    & $python -I -B tests\test_mm005_browser_research_model_evaluation_generation_failure_diagnostic.py -v
    & $python -I -B scripts\prepare_mm005_browser_research_model_evaluation_generation_failure_diagnostic_protocol_v1.py --check
    & $python -I -B scripts\validate_offline.py
}
```
