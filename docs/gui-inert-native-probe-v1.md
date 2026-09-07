# GUI-Owl real-window inert proposal v1

On 2026-09-07, the retained GUI-Owl 4B + experimental LoRA generated one
screenshot-conditioned proposal for a real, synthetic native Windows fixture.
The unchanged consumer projector/compiler accepted its coordinate as an inert
`click_ref` for the unique enabled target. The model received only the screenshot
and fixed target instruction, with no UIA coordinates or refs in its prompt.

[Safe receipt](../baseline/gui-inert-native-2026-09-07.json) records one generation,
2.344 seconds, 781 input / 27 output tokens, and 9,317,841,408 peak allocated
bytes. Runtime performed three read calls and recorded zero Host provider turns
and zero side effects. Last-input ticks were unchanged; the fixture was closed.
Source/response hashes bind the retained record. Raw screenshot/model prose were
not saved, so the actual response cannot be independently recompiled afterward.

## Implementation and limits

`scripts/probe_gui_owl_single.py --one-inert-proposal` accepts one bounded JSON
request over stdin and responds over stdout. It is a development worker with no
desktop interface. The Runtime-owned `scripts/probe_gui_inert_model.py` checks
the fixed consumer sources, obtains the actual observation through the existing
Host/Runner/stdio MCP/Windows driver, closes that Session, projects the bundle in
memory and makes exactly one isolated local worker invocation. Generation count
is separate from the Host ledger; missing worker response means unknown count.

The worker verifies the published model/adapter file hashes and environment,
loads offline with `trust_remote_code=False`, and uses the existing visual system
prompt. The fixed instruction is `Click the center of the Observation target
button.` Greedy BF16/SDPA inference uses seed 17, at most 4096 input tokens and
192 new tokens, a 45-second generation soft deadline, a 60-second measured
acceptance cap, a 15 GB allocated-memory acceptance cap and 180-second parent
process timeout. No training, model replacement or dependency changes occurred.

The parent validates request/context/image identity, model/adapter identity,
schema, types and limits before compilation. A stop/malformed/missed-target
response is a valid negative and is not retried. Input changes invalidate the
attempt. The compiler's two contexts represent the same captured snapshot;
no post-inference desktop state is reacquired and no proposal can be executed.
Ordinary Runtime routes and policies remain unchanged. The process is trusted
local code, not an OS sandbox; resource acceptance limits are not hard GPU limits.

This is one snapshot-relative grounding diagnostic. It does not establish a
task success rate, fresh dispatch eligibility, a persistent Provider integration,
Chrome/Word coverage, planning or summary quality. The previous LoRA admission
gate remains failed at 17/24 against 20/24, with `runtime_eligible=false`.
The small probe therefore does not supersede the frozen pilot report.

## Checks

```powershell
python -I -B tests/test_gui_owl_single.py
python -I -B scripts/validate_gui_observation_projection.py --unit-tests --check
python -I -B scripts/validate_native_gui_proposal.py --unit-tests --check
python -I -B scripts/review_gui_owl_lora_pilot.py --unit-tests --check
```

Transport tests need only the standard library and perform no model load.
The existing pure projection/compiler gates keep their historical Runtime pins.
The new real diagnostic is recorded separately, never substituted for them.
The canonical `PROJECT_STATUS.md` owns sequencing and any successor activation.
