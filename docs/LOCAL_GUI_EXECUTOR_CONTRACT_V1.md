# Local GUI executor contract v1

`FC-MVP-002-local-gui-executor-contract-v1` prepares a narrow local executor
interface for the supervised Chrome-to-Word flagship. It is an offline contract,
not a model evaluation or an online desktop loop.

## Why this follows the first probe

The [first screen](LOCAL_DESKTOP_READINESS_PROBE_V1.md) measured exact executor
actions at 0/6 for the base model and 1/6 for the existing Adapter. This slice
reduces the interface burden before a new measurement: the task planner supplies
one subgoal, the local executor selects an action and observed control reference,
and Runtime retains dispatch authority. A future cloud planner can produce the
same subgoal input; no cloud provider or serving integration exists here.

The action menu deliberately exposes the action appropriate to the supplied
subgoal plus `observe` and `stop`. Therefore a later evaluation of this interface
measures constrained execution/grounding and abstention, not independent task
planning. It cannot be compared directly with the first probe as model-only
improvement.

## Input, output, and responsibility

The Host supplies a validated request with a request ID, one subgoal, numeric
window scope, current observation epoch, Runtime generation, and an observation.
The observation contains text, control references and states, foreground scope,
and a caller-supplied content-verification fact. A write subgoal also binds the
reviewed text payload. There are no screenshot inputs in v1.

The model returns one JSON object containing `request_id`, `observation_epoch`,
and `action`. Only `click_ref` and `type_text` additionally require `ref`.
Unexpected fields, duplicate JSON keys, invented windows, coordinates, text,
arbitrary key combinations, approvals, and completion claims are rejected.

| Planner subgoal | Model action | Compiled Runtime proposal |
|---|---|---|
| `activate_target` | `activate` | `activate_window` with bound window |
| `read_source` / `read_word` | `read_text` | `document_text` with bound scope |
| `focus_editor` | `click_ref` | `click` with unique observed editor ref |
| `write_brief` | `type_text` | `type` with focused editor ref and bound text |
| `save_word` | `save` | `key` with fixed `Ctrl+S`, after supplied verification |
| Any | `observe` | `ui_snapshot` with bound scope |
| Any | `stop` | No tool proposal |

For example, a request to focus Word's editor can yield:

```json
{"request_id":"contract-focus-new","observation_epoch":43,"action":"click_ref","ref":"ref_941"}
```

The compiler requires equality of the issued and current caller-supplied
request snapshots, including generation, scope, subgoal, payload, and
observation. A changed request is rejected. A stale observation permits
`observe` or `stop`, but cannot support a desktop action. Click/type require a
unique enabled editor matching the requested label and target foreground;
typing also requires the editor to be focused. These are explicit contract
rules, not corrections to a model's invalid response.

## Retained evidence and reproduction

[The retained report](../baseline/local-gui-executor-contract-v1.json) binds
the compiler, validator, fixtures, model-input projection, and inspected Runtime
tool registry by content hash. The Runtime checkout was
`0237f3104a1aeb9263627782df4c3fadc7e6ffe0`.

Twelve manually authored synthetic cases cover relocated references/windows,
stale observations, reading, activation, writing, saving, ambiguous editors,
untrusted observed instructions, and late responses. Nine tool proposals pass
the actual Runtime argument validator, one stops, and two reject with the
expected errors. These are gold contract controls, not generated model answers,
a statistical held-out evaluation, or evidence of training-data separation.

```powershell
python -I -B scripts/validate_local_gui_executor.py --unit-tests
python -I -B scripts/validate_local_gui_executor.py --runtime-root C:\Users\Alienware\guarded-desktop-agent --check-report baseline/local-gui-executor-contract-v1.json
python -I -B scripts/review_local_desktop_readiness.py --runtime-root C:\Users\Alienware\guarded-desktop-agent
```

The unit command runs 15 new adversarial contract tests and 6 prior probe tests.
The Python 3.11/3.12/3.13 CI matrix includes this command. Broader local checks
also cover the existing bridge, reliability dataset, GUI grounding, CI contract,
source import boundary, strict core typing, and repository lint.

## What remains unproved

The compiler consumes snapshots supplied by its caller; it does not authenticate
that caller, observe live Windows state, or prove that verification actually
occurred. Its digest is a consistency binding, not an authorization token.
Repeated compilation returns another inert value; durable deduplication and
exactly-once execution are not implemented here.

Runtime must recheck current state at dispatch and enforce policy, approval,
WAL, grounding, budgets, and its sole desktop boundary. This slice does not
close a time-of-check/time-of-use race, validate an on-disk save, implement a
new-document Save As dialog, or establish Chrome-to-Word task success. Those
belong to subsequent Runtime integration and state verification.

No model was loaded, no desktop action was dispatched, no Runtime source was
changed, and no training, rich capture, or cloud call occurred. The next bounded
objective is to screen the unchanged local candidates through this contract,
retaining raw outputs and separating schema acceptance, action/ref correctness,
abstention, and latency. Project sequencing remains in `PROJECT_STATUS.md`.
