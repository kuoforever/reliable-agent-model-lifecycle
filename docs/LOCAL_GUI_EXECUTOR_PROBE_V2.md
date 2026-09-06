# Local GUI executor replacement screen v2

The owner approved a small local comparison before deciding whether to replace
the current Qwen2.5-VL/Adapter. This is a fresh exploratory screening identity,
not a retry of any historical experiment.

## Preregistered scope

- GUI specialist: `mPLUG/GUI-Owl-1.5-4B-Instruct`, revision
  `3f061c2c562cc860c42bf32542a70e07a7ff4840`.
- General-model control: `Qwen/Qwen3-VL-4B-Instruct`, revision
  `ebb281ec70b05090aa6165b016eac8ec08e71b17`. This is a same-family control,
  not an assertion that it is the specialist's exact training parent.
- Native Windows, RTX 4090 Laptop, 16,376 MiB VRAM; Transformers 4.57.6,
  Torch 2.6.0+cu124, BF16/SDPA, batch size 1, deterministic greedy decoding.
- Separate virtual environment with new Transformers/tokenizers/Hub/torchvision
  packages and read-only access to prior Torch/supporting site-packages. The
  old environment is not upgraded. Execute with `-B` to disable bytecode writes.
- Corrected attempt revision 2: one excluded blank-image compatibility generation, followed by 16 fixed
  cases per candidate: 8 screenshot-grounding tasks over 4 synthetic PNGs,
  and 8 text/ref contract tasks. Each candidate gets one fresh model load and
  no case retry. Run GUI-Owl first, then Qwen; order is not counterbalanced.
- At most 192 output tokens, 4,096 input tokens, 45-second generation stopping
  limit, 900-second candidate cap, 15-billion-byte Torch allocated-memory cap.
  Generation stopping is cooperative, not a hard process deadline. Allocated
  memory excludes other processes and some driver/library allocations.

The exact tasks, expected answers, and outcome-neutral scoring rules live in
[the configuration](../configs/local_gui_executor_probe_v2.json). They are
fixed before any model load. Source/model/image hashes, exact messages, rendered
prompts, dependency versions, raw outputs, generated token IDs, and timing are
retained. Events are flushed and synced after each start/completion. Existing
output directories are never overwritten. Network download retries do not
constitute model inference retries.

## Scoring and interpretation

Visual tasks use a single `computer_use` tool-call envelope and coordinates
normalized to 0–1000, following the publisher's action convention. A click
passes only when it lies inside the registered target rectangle. Two absent
targets require explicit failure termination. Report schema validity, positive
target hits and absent-target abstention separately. The prompt is a short
shared project prompt, not an exact reproduction of either publisher's
benchmark recipe. Each model uses its own native chat template; retain this
interface difference when interpreting results.

Text/ref tasks use the unchanged v1 compiler. Compiler acceptance and exact
action/ref responses are separate measurements. The planner already supplies
the subgoal/action menu. Stale state requires re-observation; ambiguous targets
or unverified saving require stopping in the registered cases. These controls
are derived from v1 with new identifiers; they are not statistically held-out
or evidence of model-training-data separation.

All images are visibly marked **SYNTHETIC TEST**. They are simple constructed
interfaces, not screenshots of actual Chrome or Word. Success demonstrates
only feasibility on these synthetic single-step tasks. It does not establish
real Windows accuracy, Chinese UI support, long-horizon planning, repeatability,
speed under load, or Chrome-to-Word completion. Latency excludes model loading
and CPU image processing; it includes synchronized generation, and the blank
warmup is excluded from formal group summaries.

No proposals are executed. Coordinate-to-ref mapping is not implemented by this
screen, and native coordinate output does not bypass the closed v1 compiler.
Runtime retains policy, approval, grounding, WAL and budgets. A model selection
for real integration requires a separately reviewed observation/action adapter
and actual desktop validation under the Runtime tracker.

## Reproduction

The initial `gui-owl-v1` attempt completed 16 cases but is **excluded from the
paired comparison**: Transformers 4.57.6 filled the global-default
`GenerationConfig(do_sample=False)` with the model's `do_sample=True` default.
The warning and a model-free call to the installed library's actual
`GenerationMixin._prepare_generation_config` reproduced this override.
Revision 2 explicitly passes `use_model_defaults=False` and `do_sample=False`
to `generate`, checks the effective configuration, and records it before the
warmup. Tasks, expected answers, weights, dtype, prompt, and scorer remain
unchanged. Both candidates receive new `*-v2` identities; no `qwen-v1` run
occurred. The excluded raw attempt is retained separately, not silently
overwritten, relabeled as greedy, or included in aggregate results.

```powershell
work/gui-probe-v2-env/Scripts/python.exe -B scripts/probe_local_gui_executor_v2.py --candidate gui-owl --model-root work/gui-probe-v2/models/gui-owl --metadata work/gui-probe-v2/hub-metadata.json --output work/gui-probe-v2/runs/gui-owl-v2
work/gui-probe-v2-env/Scripts/python.exe -B scripts/probe_local_gui_executor_v2.py --candidate qwen --model-root work/gui-probe-v2/models/qwen --metadata work/gui-probe-v2/hub-metadata.json --output work/gui-probe-v2/runs/qwen-v2
```

These are registered output identities, not instructions to rerun an already
completed attempt. Model files must match the locked Hub revision and published
LFS SHA-256 values. Full dependency versions are retained in each pre-load plan.
The fixture generator requires Pillow and Windows Segoe UI; the committed PNGs
are the authoritative evaluation inputs rather than cross-platform font renders.

Publisher references: [GUI-Owl model card](https://huggingface.co/mPLUG/GUI-Owl-1.5-4B-Instruct),
[Qwen model card](https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct),
[GUI-Owl usage and coordinate convention](https://github.com/X-PLUG/MobileAgent/tree/main/Mobile-Agent-v3.5).

## Result

Corrected attempt revision 2 completed on 2026-09-06. The retained
[evidence bundle](../baseline/local-gui-executor-probe-v2.json) includes both
pre-load plans, 32 formal responses, effective generation configurations,
timings, token IDs, model/source receipts, and the separately excluded initial
GUI-Owl attempt. In total, three fresh loads and 51 generations occurred:
32 compared cases, 16 excluded cases, and three excluded blank warmups.

| Measurement | GUI-Owl 1.5 4B | Qwen3-VL 4B |
|---|---:|---:|
| Visible synthetic target hits | 6/6 | 6/6 |
| Absent-target correct stops | 2/2 | 2/2 |
| Visual output-schema acceptance | 8/8 | 8/8 |
| Text/ref compiler acceptance | 2/8 | 3/8 |
| Text/ref exact expected response | 1/8 | 2/8 |
| Visual generation median | 1.672 s | 1.625 s |
| Text/ref generation median | 1.437 s | 1.578 s |
| Model load time, excluding file hashing | 4.594 s | 4.125 s |
| Peak Torch allocated memory | 9,308,010,496 bytes | 9,308,010,496 bytes |

Both corrected attempts pass their resource caps. The latency differences are
diagnostic single-run observations, not a significant speed ranking. Network
preparation was not timed as inference; GUI-Owl ran while the remaining Qwen
payload download was active. Neither model was quantized or newly trained.

GUI-Owl has five `RESPONSE_FIELDS` rejections and one `CONTENT_NOT_VERIFIED`;
Qwen has four and one, respectively. For example, Qwen emits `click_ref` without
the required `ref`, while both candidates propose saving the unverified case.
The compiler rejects these proposals. One accepted but non-exact response from
each candidate re-observes instead of taking the expected progress action;
those safe alternatives are not classified as unsafe execution.

**Decision:** both are feasible local visual candidates for this restricted
screen, and neither is a drop-in executor replacement. The small, easy synthetic
image set does not separate their visual quality. The original 3B/Adapter was
not rerun on this image set, so this is not a controlled model-size improvement
claim. Before more training or a larger candidate search, prioritize a shared
native-proposal adapter that binds observations and passes Runtime grounding.
The model's native coordinate envelope must not be silently inserted into the
old ref-only contract or treated as execution permission. The canonical next
objective is recorded in `PROJECT_STATUS.md`.

Downloads initially encountered incomplete HTTP responses and stalled Xet
transfers. The weights were then obtained from the publisher's ModelScope
repositories (`iic/GUI-Owl-1.5-4B-Instruct` and `Qwen/Qwen3-VL-4B-Instruct`),
with all four complete weight files matching the SHA-256 and sizes of the
locked Hugging Face revisions. Small config/tokenizer files remain from the
locked Hugging Face revisions. The bundle retains the exact transport URLs,
hashes and sizes; it does not rely on mutable model names for weight identity.

The model-free reviewer reproduces all 32 scores and aggregates, checks the
effective greedy configuration and excluded-attempt separation, and requires
the cases, prompts and GUI-Owl weights to match across the configuration fix.
It checks retained consistency rather than independently attesting execution
or rehashing current model payloads. Ten scoring/evidence regression tests
cover wrong locations, absent targets, malformed proposals, changed outputs
with updated hashes, reintroduced sampling, and excluded-attempt mixing.
The focused local regression runs 88 tests with two Windows symlink-privilege
skips. All 81 source import boundaries and repository Ruff checks pass; the
prior 24-output model screen and v1 Runtime conformance report still reproduce.
The Python 3.11/3.12/3.13 CI matrix now checks this evidence bundle directly.

```powershell
python -I -B scripts/review_local_gui_probe_v2.py --unit-tests
python -I -B scripts/review_local_gui_probe_v2.py --check baseline/local-gui-executor-probe-v2.json
```
