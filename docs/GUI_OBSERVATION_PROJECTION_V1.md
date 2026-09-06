# GUI observation projection v1

The model-side projector now consumes a bounded representation of existing
Runtime observation results. **Existing `list_windows`, `ui_snapshot` and
`screenshot` results alone remain incomplete.** A positive synthetic control
shows the required supplementary Host contract; it does not implement or prove
a live producer of those facts.

## Verified producer facts and gaps

Read-only inspection pins Runtime commit
`0237f3104a1aeb9263627782df4c3fadc7e6ffe0` and five source-file hashes in the
retained report. The existing formats establish the following:

| Input | Extracted facts | Required facts not established by that input |
|---|---|---|
| `list_windows` text | Numeric IDs and exactly one foreground marker | Window rectangle; bounds exist internally in `Window` but the tool text omits them |
| `ui_snapshot` text | Ref, role, name, `(x,y,w,h)` rectangle, reported states | Successful state reads, complete/coherent observation and visibility; absence of `offscreen` is not a verified visible flag |
| Screenshot PNG | SHA-256 of supplied bytes and IHDR dimensions | Actual coordinate origin and coherence with the window/UIA calls |
| ToolResult + caller-owned stamps | Successful/dispatched outcome, call identity, tool arguments, generation, epoch | ToolResult itself does not contain all those stamps; the future Host producer must attach genuine call/state metadata |

`WindowsDriver._states` defaults a failed `IsEnabled` read to true and a failed
`IsOffscreen` read to false. Those output strings cannot attest successful reads.
Offscreen status is also not a proof of occlusion-free visibility. A union of
control rectangles is not the window rectangle. The projector fabricates none
of these missing facts and makes no new visibility or occlusion claim.

## API

`project_observation(task, results, image_bytes, host_facts=None)` is pure,
standard-library-only code. `task` contains the native adapter's version,
request ID, target window/name/role, current epoch and Runtime generation.
`results` has exactly `windows`, `snapshot` and `screenshot`; each contains
`call_id`, `tool`, `status`, `dispatch`, `generation`, `epoch`, `arguments`, and
`text`. Screenshot bytes are passed separately and never copied to the report.

The bounded v1 sequence is `list_windows({})` then
`ui_snapshot({"scope": numeric_window_id})` then `screenshot({})`, with distinct
call IDs, strictly increasing epochs, one Runtime generation, and the screenshot
at the current epoch. This validates the supplied stamps; it does not authenticate
them or prove no intervening changes. Dynamic scopes, `find` subsets, region
captures, failed or uncertain results are rejected.

UIA rectangles convert from `(x,y,w,h)` to `[left,top,right,bottom]` without
clipping. Recognized controls are only button/edit/document, matching the native
adapter. Unsupported roles reject the projection rather than silently removing
possible overlaps. Truncated/incomplete footers, duplicate refs, malformed or
ambiguous quoted text, unknown/conflicting states and names of length 100 or
more are rejected. The driver can truncate names at 100 without a marker, so
that last limit is deliberately conservative. An explicitly empty snapshot is
supported. Optional values are parsed for grammar but omitted from the model
context; process names and window titles are also omitted from that context.

Legacy text is not an authenticated serialization. In particular the producer
does not escape every name/title/value delimiter. This parser supports a strict
unambiguous subset; it is not a general round-trip parser or protection against
all spoofed UIA text. Future Host facts must come from a reviewed producer and
bind the actual observed controls, not model-authored metadata.

With no supplementary facts the result has `status="incomplete"`, `context=null`
and these explicit gaps:

- `window_bounds`
- `primary_frame_origin`
- `coherent_complete_projection`
- `verified_control_states`

The caller may supply a closed `host_facts` object containing the exact
`binding_digest`, `window_bounds`, `frame_origin`,
`coherent_complete_projection` and per-ref `control_states` with exact bool
`enabled`/`visible` fields. The binding hashes the task, all supplied result
records and image bytes. Changed task/text/image/stamps cannot reuse facts.
Only `[0,0]` origin is supported; negative/multi-monitor origins are not remapped.
The producer must explicitly establish a complete/coherent projection. Merely
setting this field to true is not verification or authority.

Facts must cover every reported control, not contradict reported states, and
pass the native adapter's rectangle/window/schema checks. Inconsistent state
reads require a fresh coherent observation; no conflicting value is silently
overridden. A completed projection returns a detached native context, with
`execution_authorized=false`. No action is proposed by the projector itself.

PNG validation here is bounded IHDR/header validation, consistent with the
current ImageContent boundary; it is not full decoding, CRC checking or proof
that arbitrary PNG bytes are safe to render. SHA-256 binds the supplied bytes.
The real collector must retain the Runtime's existing image/redaction validation
and use the same image bytes for model input. No crop, hidden image substitution,
raw capture export, training-data collection or automatic Lane A expansion is
introduced.

## Validation and retained evidence

The synthetic fixture produces the expected incomplete result. Supplementary
synthetic Host facts produce a valid native context; an offline native click
then compiles to `click(ref_1)` with no execution authority. Twelve retained
negative controls cover wrong scope, mixed generation, failed result, wrong
sequence, truncation, incomplete footer, unsupported role, wrong binding/origin,
unconfirmed coherence, missing states and invalid window bounds.

Eighteen unit tests add empty snapshots, exact rectangle conversion, value
omission, ambiguous windows/names, image headers, bool epochs, coordinate caps,
state conflicts and receipt-promotion rejection. Strict mypy and repository
Ruff pass, as do all 82 focused tests (18 new, 64 prior) and 83 production import
boundary audits. Existing native/model/LoRA evidence replays unchanged.
The model-free reviewer reproduces the projector/control outcomes
and checks the pinned Runtime receipt; it does not independently execute Runtime.

The explicit conformance run uses real `Session.ui_snapshot()` with a fake
`get_tree` driver and real Runtime `Node`, `Rect`, `TreeResult`, `ToolResult`
and `ImageContent` types. It verifies the actual UIA formatter and all three
result-type conversions. The window text matches the inspected server format;
the server's live `list_windows` function is not invoked. No Windows driver,
MCP session, Runner, local model, cloud provider or desktop operation runs.

```powershell
python -I -B scripts/validate_gui_observation_projection.py --unit-tests --check
C:\Users\Alienware\guarded-desktop-agent\.venv\Scripts\python.exe -I -B scripts/validate_gui_observation_projection.py --runtime-root C:\Users\Alienware\guarded-desktop-agent --check
```

Source, image, Runtime hashes, the exact synthetic task/results/Host facts,
projected context, inert proposal and failures are retained in
`baseline/gui-observation-projection-v1.json`. Runtime and historical model,
LoRA, native-adapter and diagnostic artifacts remain unchanged.

The next item is a Runtime observation-producer handoff: activate one bounded
offline Host/collector slice in its canonical tracker to obtain the four missing
fact groups and genuine call/state stamps. Preserve its completed maintenance,
paused Provider/Formal Demo and Full Cycle resume states. The model-side
projector is ready for that contract; live collection and execution are not
enabled by this document.
