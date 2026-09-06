# Native GUI proposal adapter v1

The shared GUI-Owl / Qwen native click-or-stop response now compiles into a
bound, inert Runtime proposal. A native coordinate resolves to one observed
UIA ref; it never becomes an ungrounded coordinate dispatch. This closes the
offline proposal-format gap, not the Chrome-to-Word demonstration.

## Contract and ownership

`fullcycle_bridge.native_gui_proposal.compile_native_response(issued, current,
reply)` is a standard-library-only pure function. The caller supplies detached
issued/current contexts containing request ID, target window, observation epoch,
Runtime generation, exact target name/role, foreground window, screenshot hash
and dimensions, window bounds, and bounded UIA controls with refs, visibility,
enabled state and bounds. All objects are closed schemas; integers reject bools,
refs are unique, and rectangles are nonempty and contained within the window.

This version accepts only a full primary-screen pixel coordinate frame. Crops,
virtual-desktop origins, DPI transforms and multi-monitor coordinate conversions
must not be relabeled as this frame. The future observation producer must obtain
and verify these facts. A model-generated bounding box is not an observed UIA box.
Visible parent/child boxes that overlap are conservatively ambiguous here; this
version has no occlusion or UIA-tree disambiguation algorithm.

The caller correlates the asynchronous completion through a separate reply
wrapper with `request_id`, `context_digest` and `raw_output`. The model's native
output itself has no request-binding fields. The digest binds the complete
validated context, including the frame hash and all controls; it detects content
changes but is not authentication, provenance attestation or a capability token.
A caller who invents the snapshots can invent those facts. Runtime must still
own their acquisition and revalidation.

Only these native forms are accepted, without additional prose or tool calls:

```text
<tool_call>{"name":"computer_use","arguments":{"action":"left_click","coordinate":[500,100]}}</tool_call>
<tool_call>{"name":"computer_use","arguments":{"action":"terminate","status":"failure"}}</tool_call>
```

Unknown fields, duplicate keys, success claims, arbitrary tools, key/text
actions, boolean/string coordinates, nonfinite values and excessive decimal
precision are rejected. Coordinate values lie in `[0,1000)`; 1000 denotes the
outside image edge and is rejected rather than silently clamped. Decimal input
uses exact rational arithmetic and floor conversion to pixels. Rectangles use
exclusive right/bottom edges. This is intentionally stricter than the earlier
screen's inclusive normalized range; none of its retained outputs hit that edge.

For a click, issued/current contexts and the reply binding must agree; the
observation must be current and the requested window foreground. The pixel must
be inside that window and exactly one visible control, with the requested name
and role, enabled. Duplicate enabled/visible target names are also ambiguous
even when their rectangles do not overlap. A disabled overlapping control still
causes ambiguity. Missing, hidden, disabled, wrong or ambiguous targets fail
closed; there is no coordinate fallback.

The result carries the context binding, frame hash, window, epoch, generation,
diagnostic pixel point and either `click` with **only** `{"ref":"ref_N"}`, or a
stop with no tool/arguments. `execution_authorized` is always false. Stops may
refer to an already-stale snapshot, but a changed caller context or misbound
reply is rejected even for a stop. No desktop functions, model libraries or
Runtime modules are imported by the production module.

## Evidence

The validator replays 24 existing visual responses: eight GUI-Owl base, eight
Qwen3-VL and eight GUI-Owl LoRA. It does not regenerate responses or select new
checkpoints. The initial excluded sampled attempt remains excluded. Eighteen
visible-target responses produce refs and six absent-target responses stop.
The synthetic UIA projection is deliberately constructed from the same known
visual fixture boxes and manually assigned target labels. Therefore these are
interface controls, not independent grounding-quality or real-UIA evidence.

Thirteen retained negative controls reject stale/new observations, changed
frame/window/generation, mismatched reply, background window, overlap, wrong
target, disabled/hidden control, outside-edge coordinate and success claim.
Twenty unit tests also cover schema/type attacks, repeated tool calls, resource
attacks through decimal exponents, duplicate names, pixel boundaries and the
detached snapshot/digest behavior.

The read-only conformance path imports the actual `validate_tool_arguments`,
`GroundingState`, `ToolCall` and `ToolResult` from Runtime commit
`0237f3104a1aeb9263627782df4c3fadc7e6ffe0`, with source hashes pinned. It feeds
synthetic successful `ui_snapshot` results into `GroundingState.observe`, then
validates all 18 actual compiled click calls. All 18 pass schema and grounding;
invalidation, generation change and unobserved refs reject all 54 negative
checks. No Runner, MCP, driver or desktop is invoked. Runtime's own grounding
is not claimed to verify target semantics, snapshot authenticity or elapsed
freshness; the producer and dispatch path retain those responsibilities.

`baseline/native-gui-proposal-adapter-v1.json` retains source/input hashes,
synthetic contexts, original raw model outputs, compiled proposals and Runtime
results. The model-free CI check recomputes every proposal/control and checks
the retained Runtime receipt's pinned shape and results. Only the explicit
`--runtime-root` path invokes Runtime validators again; model-free replay alone
does not independently attest Runtime execution.

```powershell
python -I -B scripts/validate_native_gui_proposal.py --unit-tests --check
# Use the Runtime environment for its dependencies; no Runtime files are edited.
C:\Users\Alienware\guarded-desktop-agent\.venv\Scripts\python.exe -I -B scripts/validate_native_gui_proposal.py --runtime-root C:\Users\Alienware\guarded-desktop-agent --check
```

The new module passes strict mypy; repository Ruff and all 82 production import
boundary audits pass. All 64 focused tests pass (20 new and 44 existing).
Previous contract/model/LoRA reports remain byte-identical and replay unchanged.
The Runtime repository and its canonical tracker remain unchanged: its local
provider, live desktop and Formal Demo work are not activated by this report.

## Next boundary

The next model-side item is the live-observation **projection contract**:
derive this input from Runtime's existing observation result formats, identify
which window/visibility/frame facts are missing, and test the projection offline
without fabricating those facts. Any needed collector, model-client, Host or
desktop changes must be registered under the Runtime repository's own single
active item before implementation. The experimental LoRA remains ineligible
for promotion after its failed exact-action threshold. The historical consumed
diagnostic chain and deferred Full Cycle gates remain untouched.
