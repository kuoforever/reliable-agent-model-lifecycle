# Local desktop readiness probe v1

## Purpose and scope

The owner selected a bounded Chrome-to-Word flagship demonstration and asked
to screen existing local models before spending time on serving or desktop
integration. This new exploratory probe is independent of every historical
MM-002/MM-003/MM-005 attempt. It does not reopen or retry them.

The twelve new inputs are synthetic English text in Runtime-style window and
UIA layouts: two reading cases, two summaries, two enumerated-stage planning
cases, and six single-action executor cases. They are not observations from
a currently running desktop, screenshots, or the public Microsoft webpage.
The two short team guides are invented test content. A successful screen
cannot establish multi-step autonomy, screenshot grounding, application
completion, prompt-injection robustness, or generalization.

## Candidate and fixed procedure

- Base: cached `Qwen/Qwen2.5-VL-3B-Instruct`, revision
  `66285546d2b821cf421d4f5eb2576359d3770cd3`.
- Adapter: the unchanged MM-003 QLoRA SFT v2 Adapter, attached read-only to a
  fresh base load. Training and Adapter writes are absent.
- Both candidates use BF16 / SDPA, the same processor, the same input order,
  seed `66006`, greedy generation, 512 new-token cap, and 4096 input-token cap.
  This is a new BF16 screen, not reproduction of the earlier 4-bit inference
  results. No screenshot is passed to the VLM.
- Each process uses local-only model resolution. After dependency import,
  Python socket connect APIs fail closed. No cloud provider or desktop
  dispatch port is constructed. This is not OS-level network attestation.
- Each candidate has a fresh output directory and load. Before dependency
  execution its plan binds the complete local base/Adapter file hashes, suite,
  harness, Runtime commit/tool-registry hash, prompts, schemas and environment.
  Gold answers are kept out of model messages. Every completed response is
  flushed and synced before proceeding; raw text and generated token IDs are
  retained. Failures retain a traceback locally instead of disappearing.
- `max_time=90` is a generation stopping criterion, not a hard wall-clock
  interruption. A 1200-second check runs between cases; load/hash/import and
  individual kernel blocking are not protected by an external watchdog.
- Existing output directories are refused. New explicit exploratory runs must
  retain their own identity and history; there is no single-execution or
  external execution-count attestation claim.

## Scoring and interpretation

The raw response must be one JSON object with no duplicate keys or nonfinite
numbers. Raw compliance is reported separately from a diagnostic score after
removing exactly one enclosing Markdown JSON fence. No prose extraction,
argument correction, semantic repair or generation retry is performed.

Executor arguments are checked by the actual current Runtime
`validate_tool_arguments`; correct tool and target are then compared with the
case answer. Schema validity alone does not establish current grounding,
policy, human approval or permission to execute. The expected action for every
executor case was independently accepted by the same Runtime schema checker
before interpreting model results.

Summary automation measures only source-label preservation, three 24–180
character bullets, and lexical fact coverage. Paraphrases such as `6 PM` for
`18:00` can fail that proxy despite factual equivalence. Human review must
separately identify formatting failures, supported paraphrases, contradictions,
and invented facts. Scores must not be renamed factual accuracy.

The planner tests supply a small stage vocabulary; some executor tasks name
the required tool. These are basic interface/instruction-following controls,
not evidence that the model discovered a plan or inferred every next action.
All safety-related cases are explicitly prompted and remain diagnostic only.

## Future planner / executor boundary

Keep two responsibilities separate when selecting the next implementation:

1. Planner input: user objective and bounded task state. Output: ordered
   subgoals and completion criteria, treated as untrusted proposals.
2. Local executor input: one current subgoal, fresh bounded observation and
   reviewed tools. Output: one typed action proposal or a request to reobserve.

The planner may later be local or cloud-hosted without changing desktop
authority. Runtime alone owns policy, approval, grounding, WAL, budgets,
dispatch and post-state verification. This document is a design boundary,
not an implemented provider or serving endpoint. Real-content cloud transfer
and Lane B capture are not enabled by this probe.

## Validation and result

Run the model-free harness tests with:

```powershell
python -B -m unittest tests.test_local_desktop_readiness_probe
```

The standalone harness accepts caller-supplied cached `--model-root`,
`--adapter-root`, `--runtime-root`, a fresh `--output`, and
`--candidate base` or `--candidate adapter`. It requires the existing local
Torch/Transformers/PEFT environment; dependencies are not installed by it.

Both candidates completed all twelve cases on 2026-09-06, with no generation
retry, Adapter write, cloud model, live capture, or desktop dispatch. The
[retained bundle](../baseline/local-desktop-readiness-probe-v1.json) preserves
both complete pre-execution plans, all 24 raw responses and token-ID arrays,
exact original JSONL bytes, per-case scores, resource measurements, and human
summary review. It binds Runtime `0237f3104a1aeb9263627782df4c3fadc7e6ffe0`.

| Measure | Base | Adapter |
| --- | ---: | ---: |
| Raw JSON protocol compliance | 8/12 | 12/12 |
| Reading, diagnostic fence normalization allowed | 1/2 | 1/2 |
| Enumerated-stage planning | 1/2 | 0/2 |
| Executor tool/argument schema validity | 2/6 | 4/6 |
| Executor exact next action and target | 0/6 | 1/6 |
| Summary shape plus lexical proxy | 0/2 | 0/2 |
| Peak allocated GPU memory | 7,854,183,424 bytes | 7,883,674,112 bytes |

The 59.469-second base and 55.844-second Adapter measurements include model
load and generation but exclude the earlier file hashing and dependency import.
They are single-run observations, not evidence of a speedup or resource
repeatability. The model comes with a sampling temperature that Transformers
warned is unused under greedy generation; both candidates kept the same
configuration and `do_sample=false`.

Human inspection found all three source facts supported in both summaries
from each candidate. For guide A, `6 PM` correctly paraphrases `18:00`, which
fails the frozen lexical proxy. For guide B, the first two bullets are shorter
than the required 24 characters; current facts are retained and obsolete facts
are omitted. These findings do not revise the automated score or establish
open-ended summarization quality.

The Adapter's useful changes are narrower than readiness: it emits unfenced
JSON consistently, selects the current relocated editor ref, requests a fresh
snapshot for stale grounding, and produces `key {combo: Ctrl+S}` in the save
case. Its two clicks still combine mutually exclusive refs and coordinates;
its snapshot/read proposals use `foreground` or `all` instead of the specific
target window. It also omits final verification from the full plan and produces
`compose_brief` instead of the required save/verify suffix on resume. Neither
candidate follows the injected email instruction, but the resulting `all`
scope still fails the exact target check. One prompted example is not a
prompt-injection robustness claim.

The window-reading prompt named scopes without explicitly spelling out that
the numeric first column was required. Both candidates returned executable
names; this may reflect interface ambiguity as well as model capability.
The input remains unchanged and the failure is retained. The small,
instruction-heavy set cannot separate prompt design, BF16 execution-form
effects, training specialization, and underlying model capability.

Decision: **not ready for live desktop under this interface**. The single next
item is `FC-MVP-002-local-gui-executor-contract-v1`: define a narrow one-subgoal
executor envelope with explicit window/epoch binding and mutually exclusive
action arguments, plus fresh held-out contract cases before another screen.
Keep planner replacement as a separate port. Do not build a serving platform,
train, or widen Runtime execution on the basis of these results.

Model-free result recomputation uses:

```powershell
python -I -B scripts/review_local_desktop_readiness.py --runtime-root C:\Users\Alienware\guarded-desktop-agent
```

It validates original plan/output hashes, paired controls, the historical base
identity, semantic prompt projection, the actual Runtime tool schemas, all
24 case scores and group totals. It does not reload a model or independently
attest that generation occurred. The original live input strings remain in
the plan; semantic reconstruction allows JSON property order differences.
