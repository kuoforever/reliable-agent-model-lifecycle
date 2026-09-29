# Local models, APIs, and GUI collaboration

中文权威版：[本地模型、API 与 GUI 协作设计](../LOCAL_MODEL_API_GUI_ROUTING_DESIGN.md)

Status: design reference consolidated on 2026-09-29 from the 2026-09-10 and
2026-09-17 discussions. Candidate models, a persistent API, and hybrid routing
still require separate validation. [PROJECT_STATUS](../../PROJECT_STATUS.md)
controls sequencing; this document grants no execution authority.

## Existing evidence

The [Word worker](../../scripts/probe_gui_owl_word.py) receives stdin JSON in a
local subprocess, loads GUI-Owl 4B plus experimental LoRA, and returns a
candidate with request/context/image and model/Adapter bindings. Host and
Runtime revalidate the current observation; Policy, Approval, WAL, Runner, and
MCP retain execution authority. See the
[native proposal contract](../NATIVE_GUI_PROPOSAL_ADAPTER_V1.md).

The [LoRA pilot](../GUI_OWL_LORA_PILOT_V1.md) scored 17/24 against a 20/24 gate.
The dated fixed Word write/save/reopen diagnostic is one bounded application
result; its 2.297-second generation time excludes loading and desktop work.
Runtime's separate local_openai client supports text Planner/final only, not
the visual GUI worker path. Source links are retained in the Chinese design.

[MM-004](../MM-004-multimodal-hard-negative-model-evaluation-result-review-v2.md)
scored 32/56 overall, accepting only 4/28 clean cases while rejecting 28/28
hard negatives. That reject bias does not justify a local-first routing claim.

## Candidate selection and API design

The dated selection hypothesis uses Qwen/Qwen3.5-4B post-trained for an
image-text training/evaluation loop and 4-bit Qwen/Qwen3.5-9B as an inference
comparison on a 16GB RTX 4090 Laptop. These are unmeasured candidates, not a
current release ranking. Recheck official model identity, license, and backend
support before implementation. Preserve the frozen Qwen2.5-VL baseline;
independently validate loading, processor, LoRA targets, parsing, peak memory,
save/fresh-reload, and fixed-task quality.

Freeze the existing worker contract before adding a loopback resident service.
Proposed endpoints are GET /readyz, GET /v1/model-info, and POST /v1/gui/proposals.
They are not implemented endpoints. Preserve request/context/image and
model/Adapter identity plus resource metrics. Compare worker/API candidates
under fixed inputs and generation settings; reject timeouts, malformed replies,
stale observations, and resource violations. Inference retries do not authorize
GUI write replay or reuse of a consumed experiment. Residency may reduce load
cost while consuming persistent VRAM; HTTP alone does not speed generation.
GUI-Owl + LoRA compatibility with vLLM remains unverified.

## Routing and measurement

Use deterministic tools for directly checkable state, local models for
validated bounded tasks with unique targets and fresh observations, and cloud
models for unfamiliar interfaces, complex planning, or escalation. A subtask
has preconditions, success/stop conditions, and a step budget. Measure local
coverage and success on independently validated data; self-reported confidence
does not authorize routing or bypass Runtime denial.

Keep stable rules/tools in the cacheable prefix and live state in the suffix.
Recheck provider-specific caching rules and costs. Verified workflow templates
may reduce calls; rich training traces still require Lane B consent controls.

Compare A (optimized all-cloud), B (cloud planning plus local deterministic
flow), and C (B plus local-model escalation) on the same task, initial state,
Runtime, and acceptance criteria. Measure task success, side effects, P50/P95
end-to-end time, escalation, retries, human intervention, coverage, and
cold/warm resource costs. The simplified T_hybrid ≈ T_local + q × T_cloud
illustrates escalation cost, not an end-to-end benchmark. MM-004's 24/28 clean
non-accepts would imply about 86% escalation only under that hypothetical rule.

Cost per successful task includes API, local compute, cold start, recovery,
and human effort across all attempts, divided by independently verified
successes; report it as undefined when there are no successes.

## Integration with the existing checklist

| Existing task | Added acceptance focus |
|---|---|
| MM-003 | Independent candidate compatibility, lifecycle, quality, and VRAM |
| SERV-001 | Worker/API parity, response validation, observation binding |
| SERV-004 | Prefix cache, cold/warm timing, resident memory |
| SERV-010 | A/B/C task-level latency and cost per verified success |
| SERV-012 | Observable routing/escalation, coverage, safety preservation |

Exact requirements remain in the
[Chinese task checklist](../../AI_Infra_LLM_Agent_待做任务清单.md).
The source sessions and evidence boundaries are retained in the Chinese design;
resume from the actual worktree's project status and preserve peer-owned edits.
