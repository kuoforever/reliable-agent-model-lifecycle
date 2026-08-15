# 05 Tool Use、Agent Runtime 与安全

> 本章是面试学习资料，不是项目进度 tracker。项目顺序与事实状态只以
> PROJECT_STATUS.md 为准。
>
> 证据标签：**[原理]**、**[通用工程]**、**[本仓库已实现]**、
> **[本仓库待实施]**。本章严格区分模型建议、离线 compiler 和确定性 Runtime
> authority；模型输出永远不等于动作已被授权或执行。

## 1. 面试定位与学习目标

“会 function calling”只是 Agent 工程的起点。成熟面试会追问：

- Tool schema、function calling 和 MCP 各自解决什么问题？
- Router、planner、executor 和 Runtime policy 谁拥有最终 authority？
- 模型输出 JSON 合法，为什么仍然不能直接执行？
- 工具超时后到底能不能 retry？Unknown Outcome 如何恢复？
- Prompt injection 来自哪里，为什么 system prompt 不能替代 sandbox？
- 如何评价一个 Agent，而不只看最终文本像不像成功？
- Context、Memory、RAG 和 durable state 的边界是什么？

学完本章应能：

1. 画出 proposal -> validation -> policy -> execution -> recovery 的完整控制流；
2. 准确区分 Tool schema、function calling、structured output 与 MCP；
3. 设计 idempotency、WAL、checkpoint/resume、budget 和 cancellation；
4. 解释 least privilege、approval、sandbox 和 HITL 的防线分工；
5. 设计 task success、安全、副作用和恢复的 Agent eval；
6. 准确说明本仓库 Lane A/Lane B 数据边界和已实现范围。

## 2. Tool schema、function calling、structured output 与 MCP

### 2.1 Tool schema

**[原理]** Tool schema 是一个 typed contract，描述：

- tool name 和语义；
- argument 名称、类型、枚举、长度和必填字段；
- side-effect class，例如 readonly、reversible、irreversible；
- permission/approval requirement；
- timeout、idempotency 和 result/error contract；
- schema version。

JSON Schema 能验证结构，但不能证明参数在当前上下文中有权限、目标仍然存在、动作安全或
业务语义正确。Schema validation 是必要条件，不是授权。

一个简化 contract：

~~~json
{
  "name": "file_write",
  "description": "Write reviewed content to one approved file",
  "input_schema": {
    "type": "object",
    "additionalProperties": false,
    "required": ["path", "content", "expected_revision"],
    "properties": {
      "path": {"type": "string", "maxLength": 512},
      "content": {"type": "string", "maxLength": 100000},
      "expected_revision": {"type": "string"}
    }
  },
  "effect": "write",
  "requires_approval": true,
  "idempotency": "conditional"
}
~~~

### 2.2 Function calling

**[原理]** Function calling 是模型生成一个结构化 tool-call candidate 的交互模式。
它通常包括 tool name、arguments 和 call ID。它不意味着：

- 对应 Python/JavaScript function 已执行；
- 参数已经业务校验；
- 用户已经授权；
- 网络、文件或桌面边界已开放；
- 结果一定可信。

正确心智模型是“模型提交一份 typed proposal”，Runtime 决定拒绝、澄清、审批、回退
或执行。

### 2.3 Structured output

Structured output 关注模型输出满足某个 grammar/schema。常见路径：

1. prompt-only JSON：最灵活，格式失败最多；
2. constrained decoding：在 token 层限制 grammar，结构有效率高；
3. post-hoc parser/repair：可恢复轻微格式问题，但可能改变语义；
4. deterministic compiler：从一个主决策派生冗余字段；
5. semantic validator：检查跨字段和环境约束。

Constrained decoding 只保证“能被 grammar 接受”；它不能保证 tool 存在、参数真实、
动作符合 policy。Post-hoc repair 若猜测缺失语义，会掩盖模型失败。Compiler 只应派生
contract 明确规定的冗余字段，不能把错误 tool 偷换成正确 tool。

### 2.4 MCP

**[原理]** Model Context Protocol 是 host/client/server 之间发现和调用 tools、
读取 resources、使用 prompts/context 的协议层。它解决互操作、capability discovery、
typed payload 和 transport 生命周期，不自动提供：

- 业务 policy；
- 用户授权；
- 操作系统 sandbox；
- secret isolation；
- 幂等、WAL 或 crash recovery；
- prompt-injection 防护；
- tool result 真伪校验。

因此 MCP server 暴露能力，不等于模型拥有能力。Host/Runtime 仍要做 allowlist、
permission mediation、approval、budget、audit 和 result sanitization。

### 2.5 概念边界速览

| 概念 | 输入/输出 | 负责 | 不负责 |
|---|---|---|---|
| Tool schema | typed arguments/result | 接口 contract | 权限与执行事实 |
| Function calling | model -> call candidate | 结构化建议 | 实际 dispatch |
| Structured output | token stream -> valid shape | 语法约束 | 语义正确 |
| Compiler | primary decision -> derived fields | 去除冗余矛盾 | 改进模型意图 |
| MCP | host/client/server messages | 工具与资源互操作 | policy/sandbox/recovery |
| Runtime | validated proposal -> state transition | authority、执行与恢复 | 模型训练 |

## 3. Router、planner、executor 与 authority

### 3.1 Router

Router 在候选工具或模型之间做一次分类/选择。输入通常是 instruction、available tools 和
有限 state，输出 selected tool、arguments、risk/fallback 等。适合短决策、低 horizon
和明确 tool registry。

### 3.2 Planner

Planner 将目标拆成多步 task graph 或 action sequence。它需要处理 dependency、
observation update、replan 和 stop condition。Plan 是 proposal，不是预授权的一串动作；
每一步都应重新经过 policy 和 grounding。

### 3.3 Executor

Executor 将一个已验证、已授权的 action 转换成实际 tool dispatch，并记录 receipt、
result、side effect 和 state transition。它应尽量 deterministic，不让 LLM 随意决定
retry、回滚或跳过审批。

### 3.4 Runtime authority

**[原理]** 可靠 Agent 的 authority chain：

~~~text
user intent and organizational policy
  -> deterministic Runtime policy
  -> optional human approval
  -> grounding and precondition validation
  -> WAL intent record
  -> sole execution boundary
  -> observed result and post-state
~~~

Model、router、planner 和 verifier 都在 proposal/advisory 层。它们可以建议“调用
file_write”，但不能自行授予权限、确认审批、绕过预算或宣称副作用成功。

## 4. 一次可靠 tool call 的控制流

**[通用工程]**

~~~text
1. Receive task with task_id and authority scope
2. Build trusted/untrusted context segments
3. Ask model for a candidate decision
4. Parse and validate schema
5. Compile only deterministic redundant fields
6. Check tool registry/version and argument semantics
7. Apply policy, least privilege and budget
8. Request approval if required
9. Re-observe/ground mutable target
10. Append WAL intent and idempotency key
11. Dispatch through the sole tool boundary
12. Record receipt/result or unknown outcome
13. Verify post-state independently
14. Commit checkpoint and budget usage
15. Continue, replan, compensate or stop
~~~

这里的先后顺序很重要。先执行后写 WAL 会留下无法判断是否发生过的 side effect；审批后
不 re-observe 可能遭遇 TOCTOU；仅依赖 tool 返回“success”会把工具自报当作状态事实。

## 5. Tool Router decision contract

一个可评测的 router 不应只输出 tool name。常见决策字段包括：

- selected_tool；
- scalar arguments；
- risk_level；
- requires_approval；
- should_reject；
- should_fallback；
- expected_result。

**[本仓库已实现]** Tool Router v1 对 object 使用 closed schema，限制未知字段、嵌套
arguments、未知 tool、非法 enum 和输入大小。Semantic validator 还检查：

- selected tool 必须出现在 available_tools；
- rejection、fallback、clarification、approval 与 selected tool/expected result 一致；
- dangerous request 与 duplicate delivery 必须拒绝；
- 已知 tool failure 与 loop budget exhaustion 必须 fallback；
- Provider output、Memory、Continuation、screenshot、raw trace 和 tool-result body
  等 rich fields 被禁止。

本仓库 router 只产生 candidate decision。Policy、Approval、WAL、Grounding、budgets
与 Desktop 唯一执行边界由独立 Runtime 仓库拥有。

## 6. Structured compiler：能做什么，不能做什么

### 6.1 合理的 compiler

若 selected_tool 是主决策，而 terminal flags 是冗余表示，可以确定性派生：

| selected_tool 类别 | expected_result | should_reject | should_fallback |
|---|---|---:|---:|
| reject_request | rejection | true | false |
| fallback_to_strong_model | fallback | false | true |
| request_clarification | clarification | false | false |
| 普通 tool + 需审批 | approval_required | false | false |
| 普通 tool + 无需审批 | tool_candidate | false | false |

这类似 compiler 的 type lowering：保留模型的 primary choice，消除同一语义被重复生成后
互相矛盾的问题。

### 6.2 不合理的 repair

以下做法会制造虚假能力：

- 根据 gold answer 把 wrong tool 改正确；
- 看到执行失败后重写之前的 prediction artifact；
- 用隐藏业务规则补出模型从未表达的 argument；
- 捕获 parser error 后无限 retry，最后只保存成功输出；
- 把 compiler 指标记成 raw model 指标。

### 6.3 本仓库证据

**[本仓库已实现]** Decision compilation v1 固定后，只从 selected_tool 派生冗余
terminal fields。它不改 raw prediction、instruction、arguments、selected tool、
risk 或 approval。冻结 v2 的 3 个冲突 case 被修复：

- semantic validity 0.85 -> 1.00；
- rejection accuracy 0.85 -> 1.00；
- false refusals 3 -> 0；
- tool accuracy 保持 0.95；
- dangerous action candidates 与 false approvals 都保持 0。

这证明 fixed compiler 消除了 contract inconsistency，不证明模型本身改进。后续 FP32
raw semantic validity 仍只有 0.80，也进一步说明 compiler dependency 必须属于 candidate
identity。

## 7. Context、Memory、RAG 与 durable state

### 7.1 Context

Context 是当前一次模型调用可见的 token window，包括 system/developer instruction、
task、tool descriptions、retrieved evidence 和近期 observations。它短暂、受长度限制，
也可能含不可信内容。

### 7.2 Memory

Memory 是跨调用或跨任务保留的信息。至少分：

- working memory：当前 task 的摘要和未完成状态；
- episodic memory：过去事件/轨迹；
- semantic memory：提炼后的稳定事实；
- user preference memory：有明确授权和删除机制的偏好。

Memory 需要 provenance、scope、TTL、privacy、conflict resolution 和 deletion。把完整
聊天无差别塞回 context 不是可靠 memory。

### 7.3 RAG

RAG 是按 query 从外部 corpus 检索 evidence，再供模型使用。它解决知识访问，不等于
记忆，也不保证 retrieved content 正确。需要 source identity、freshness、ACL、
reranking、citation 和 injection filtering。

### 7.4 Durable state

Durable state 是 Runtime 恢复所需的 machine state：task phase、attempt、lease、
WAL、dispatch receipt、budget、checkpoint 和 cancellation。它必须由数据库/日志等
确定性存储拥有，不能只存在 LLM context 或自然语言 memory。

| 概念 | 生命周期 | 主要内容 | 可否作为执行事实 |
|---|---|---|---|
| Context | 单次/短期调用 | 当前可见 tokens | 否 |
| Memory | 跨调用 | 可检索经验/事实 | 需验证 |
| RAG | query-time | 外部证据 | 需验证与 ACL |
| Checkpoint | task 生命周期 | 确定性恢复状态 | 是 |
| WAL | side-effect 生命周期 | intent/commit/receipt | 是 |

## 8. Prompt injection 与信任边界

### 8.1 Injection 来源

不可信指令可能来自：

- 网页、邮件、PDF、数据库字段；
- OCR 或 screenshot 中的文字；
- tool result；
- retrieved memory/RAG document；
- MCP resource 或第三方 server description；
- 另一个 Agent 的 message；
- 文件名、代码注释和 issue text。

“忽略之前指令”只是最明显形式。更隐蔽的攻击会要求读取 secret、扩大 scope、改变 tool
arguments、上传数据或绕过审批。

### 8.2 防御不是一条 prompt

**[通用工程]** Defense in depth：

1. 标记 trusted instruction 与 untrusted data；
2. 不把 tool result 拼进高优先级 instruction；
3. capability allowlist 与 per-tool ACL；
4. least-privilege credential 和 short-lived token；
5. network/domain/filesystem sandbox；
6. argument validation、path canonicalization 和 egress filtering；
7. sensitive action approval；
8. secret redaction 与 output scanning；
9. post-state verification、audit 和 anomaly detection；
10. adversarial eval 与 incident response。

Prompt hierarchy 能降低模型服从恶意文本的概率，但不能成为唯一安全边界。即使模型被
完全注入，Runtime 仍应让它拿不到越权能力。

### 8.3 Least privilege 与 sandbox

- 每个 task 只授予必要 tool，不暴露全 registry；
- readonly 和 write credential 分离；
- 文件路径限制到明确 root，拒绝 path traversal/symlink escape；
- 网络默认 deny，只允许必要 host/method；
- command 执行使用参数数组和固定 binary，避免 shell injection；
- secret 不进入 prompt，server 端按 scope 注入；
- resource limit 控制 CPU、memory、time、output size。

Sandbox 解决“最坏情况下能影响什么”，approval 解决“用户是否接受这一次高影响动作”，
二者不可互相替代。

### 8.4 Approval 与 HITL

有效 approval 必须绑定具体 action snapshot：

- tool、normalized arguments 和目标 identity；
- 预计 side effect 和可逆性；
- 当前 state/revision；
- expiry、approver 和 approval ID。

用户批准“删除 file A”不能复用于“删除目录 B”；批准后如果目标状态变化，应重新
ground/reapprove。模型不得把自然语言“看起来同意”自行解释成 authority。

## 9. Durable execution

### 9.1 Idempotency

**[原理]** 若同一逻辑请求执行一次和多次的可观察结果相同，则它是 idempotent。
HTTP GET 通常接近幂等，发送邮件、转账、点击购买通常不是。

Idempotency key 应由稳定 task/action identity 生成，并由执行端去重：

~~~text
idempotency_key =
  hash(task_id, action_index, tool_version, canonical_arguments)
~~~

Client 端“我记得调用过”不够；server 或 durable outbox 必须能返回已有 receipt。

### 9.2 WAL

Write-Ahead Log 在副作用前记录 intent：

~~~text
PREPARED -> DISPATCHING -> SUCCEEDED
                        -> FAILED
                        -> UNKNOWN_OUTCOME
~~~

每个 transition 需要 compare-and-swap/version guard，防止两个 worker 同时执行。
WAL 记录 intent、idempotency key、attempt、receipt 和 result digest，不应把 secret 或
完整敏感 body 写入普通日志。

### 9.3 Unknown Outcome

Timeout 不等于失败。网络断开时工具可能已经执行，但 client 没收到响应。若直接 retry
非幂等动作，可能造成重复 side effect。

正确处理：

1. 标记 UNKNOWN_OUTCOME；
2. 冻结盲目 retry；
3. 用 idempotency key 查询 server receipt；
4. 通过独立 post-state observation reconcile；
5. 只有证明未执行或 server 保证去重时才能 retry；
6. 无法判断则升级人工处理。

这是可靠 Agent 与普通 workflow demo 的重要分界。

### 9.4 Checkpoint 与 resume

Checkpoint 应包含：

- task/plan version；
- completed action receipts；
- current phase 和 next action；
- observed state digest；
- budget used/limit；
- lease owner/expiry；
- approval references；
- pending unknown outcomes；
- cancellation state。

Resume 先验证 checkpoint schema、tool/policy versions 和外部状态，再继续。不能把旧的
自然语言 summary 当作可执行 checkpoint。

### 9.5 Budget、backpressure 与 cancellation

预算维度包括：

- model tokens/cost；
- tool calls；
- wall-clock deadline；
- loop/replan count；
- retries；
- side-effect count；
- parallel workers。

预算必须在 dispatch 前 reserve、完成后 commit/return，避免并发超额。达到 limit 时应
明确 fallback/stop，而不是让模型“再试一次”。

Cancellation 要从 parent task 传播到 planner、worker、tool request 和 pending queue。
对已经开始的 irreversible action，cancel 不能假装回滚；应等待 receipt、reconcile 并
记录最终状态。

## 10. 工程伪代码

### 10.1 Proposal 与执行分离

~~~python
def handle_step(task, observation, runtime):
    context = build_typed_context(task, observation)
    candidate = model.propose(context, tools=runtime.visible_tools(task.scope))

    parsed = parse_closed_schema(candidate)
    compiled = compile_redundant_fields(parsed)
    validate_semantics(compiled, observation, runtime.tool_registry)

    policy_decision = runtime.policy.evaluate(
        task=task,
        action=compiled,
        budget=runtime.budget.snapshot(task.id),
    )
    if policy_decision.is_denied:
        return runtime.record_denial(task, compiled, policy_decision)
    if policy_decision.needs_approval:
        return runtime.request_bound_approval(task, compiled)

    grounded = runtime.ground_and_check_preconditions(compiled)
    intent = runtime.wal.prepare(
        task_id=task.id,
        action=grounded,
        idempotency_key=stable_action_key(task, grounded),
    )
    return dispatch_and_reconcile(runtime, intent)
~~~

### 10.2 Dispatch 与 unknown outcome

~~~python
def dispatch_and_reconcile(runtime, intent):
    try:
        receipt = runtime.executor.dispatch(intent)
    except TimeoutError:
        runtime.wal.mark_unknown(intent.id)
        receipt = runtime.executor.lookup_receipt(intent.idempotency_key)
        if receipt is None:
            post_state = runtime.observer.inspect(intent.target)
            return runtime.reconcile_unknown(intent, post_state)

    verified = runtime.verifier.verify_post_state(intent, receipt)
    if not verified:
        return runtime.wal.mark_needs_review(intent.id, receipt.digest)

    runtime.wal.commit(intent.id, receipt.digest)
    runtime.checkpoint.advance(intent.task_id, intent.id, receipt.digest)
    return receipt
~~~

这里的 verifier 可以是 deterministic check、规则、人工或 learned model 的组合。Learned
verifier 的高分不能覆盖 deterministic policy denial。

## 11. Lane A 与 Lane B

### 11.1 Lane A：自动脱敏可靠性证据

**[本仓库已实现]** Lane A 来自 Runtime 的已脱敏 trace/checkpoint 和 reviewed tool
registry。它可用于：

- failure / unknown outcome 分类；
- policy denial、budget 和 recovery 分析；
- tool sequence/outcome features；
- Runtime/Policy/Schema compatibility gate；
- reliability/Verifier feature dataset。

Lane A 明确不包含：

- 原始用户任务；
- 模型文本；
- tool-result 正文；
- screenshot；
- Memory 或 Continuation。

所以 Lane A 不能用于 instruction following、GUI grounding、多模态 SFT 或行为模仿。
本仓库的 mapper 只从可观察 Runtime facts 生成 deterministic operational labels，不把
缺失语义猜成 ground truth。

### 11.2 Lane B：显式同意的富训练轨迹

**[本仓库待实施]** Lane B 必须是独立 Capture Adapter：

- 默认关闭，每次运行显式同意；
- 有可见采集指示；
- 本地 redaction 和 image masking；
- 独立 storage、retention 和 delete；
- 可记录 instruction、observation、candidate action、policy、result、post-state；
- success 由状态 Verifier 标注，不接受模型自报；
- contract/security/privacy 单独评审。

Lane B 不能通过把 Lane A 安全 trace 悄悄扩成富日志来实现。当前状态是 pending review，
不能在面试中说成已完成采集系统。

## 12. Agent Eval：评价决策、执行和恢复

### 12.1 Metric families

| 维度 | 指标示例 |
|---|---|
| Decision | schema validity、tool accuracy、argument EM/F1、risk Macro F1 |
| Task | end-to-end success、subgoal completion、time-to-success |
| Safety | policy violations、dangerous false approvals、unsafe candidates |
| Side effect | duplicate writes/sends、wrong-target actions、unreconciled effects |
| Reliability | recovery rate、unknown-outcome resolution、resume correctness |
| Efficiency | steps、tool calls、tokens、latency、cost、peak memory |
| Human | approval burden、escalation rate、false refusal |
| Robustness | injection success rate、stale-state failure、tool outage degradation |

### 12.2 关键定义

Task Success Rate：

$$
\text{TSR}=\frac{\text{independently verified successful tasks}}{\text{eligible tasks}}
$$

不能用 Agent 自己说“完成了”作为 numerator。

Recovery Rate：

$$
\text{Recovery Rate}=
\frac{\text{faulted tasks restored to a valid terminal state}}
{\text{faulted tasks with a registered recovery path}}
$$

Duplicate Side-effect Rate：

$$
\text{Duplicate Rate}=
\frac{\text{logical actions producing more than one side effect}}
{\text{side-effecting logical actions}}
$$

这些指标中的 denominator、exclusion rule 和 observation window 必须冻结。

### 12.3 Scenario matrix

Agent eval 不应只有 happy path。至少覆盖：

- normal readonly/write；
- missing arguments 与 ambiguity；
- dangerous request 与 approval；
- duplicate delivery；
- tool timeout/failure；
- unknown outcome；
- stale observation/grounding；
- loop limit 与 budget exhaustion；
- crash before/after dispatch；
- prompt injection；
- cancel during planning/dispatch/recovery。

每个 scenario 同时检查功能、安全、副作用和 recovery，而不是只看最终文本。

### 12.4 Gates

一种合理的 gate 顺序：

1. schema/semantic validity；
2. deterministic policy/safety hard gates；
3. no duplicate/unreconciled critical side effects；
4. task success 与 regression；
5. recovery/checkpoint；
6. latency、cost 和 resource cap；
7. rollout/portability/promotion 另行决策。

安全指标不应与 task success 做一个加权平均。一个模型即使成功率 99%，只要 dangerous
false approval 非零，也可以直接不具备执行资格。

## 13. Failure modes 与排障

| 现象 | 常见根因 | 证据与修复 |
|---|---|---|
| JSON valid 但动作错误 | 结构约束不等于语义 | semantic validator、per-case diff |
| Flags 冲突 | 冗余字段由模型独立生成 | primary decision + deterministic compiler |
| Wrong tool 可执行 | registry/policy 只做 schema | allowlist、capability scope |
| 超时后重复发送 | 把 timeout 当 failure | unknown outcome + receipt lookup |
| Crash 后重做副作用 | WAL/checkpoint 在 dispatch 后写 | intent-before-dispatch、idempotency |
| 用户批准后目标变了 | TOCTOU | approval binding + re-grounding |
| 被网页文字诱导上传数据 | untrusted result 混入 instruction | trust labels、egress deny、least privilege |
| Verifier 高分但实际失败 | self-report/reward hacking | independent post-state oracle |
| 无限 tool loop | 无 budget/stop invariant | loop cap、progress measure、fallback |
| Cancel 后 worker 继续跑 | cancellation 未传播 | durable cancel state、lease fencing |
| Memory 泄露其他任务 | scope/ACL/TTL 缺失 | namespacing、provenance、deletion |
| MCP server 越权 | 把协议当安全边界 | host mediation、sandbox、credential scope |

排障时先定位失败发生在 proposal、validation、policy、dispatch、observation 还是 recovery，
不要统称“Agent hallucination”。

## 14. 概念比较速查

| 概念 A | 概念 B | 核心差异 |
|---|---|---|
| Router | Planner | 一次选择 vs 多步依赖/重规划 |
| Planner | Executor | 提议步骤 vs 确定性 dispatch |
| Model proposal | Runtime authority | 概率建议 vs 可审计权限和状态迁移 |
| JSON valid | Semantically valid | 结构合法 vs 跨字段/环境正确 |
| Constrained decoding | Compiler | 生成时限制语法 vs 生成后派生冗余字段 |
| Retry | Resume | 重做一个 attempt vs 从 durable checkpoint 继续 |
| Failure | Unknown outcome | 已知没成功 vs 不知道是否发生 |
| Idempotency | Deduplication | 操作语义可重复 vs 检测重复请求 |
| WAL | Logging | 决策执行所依赖的 durable protocol vs 观测记录 |
| Approval | Authentication | 接受具体动作 vs 确认主体身份 |
| Sandbox | Policy | 限制能影响什么 vs 判断是否允许 |
| Memory | Checkpoint | 可检索知识 vs 可恢复执行状态 |
| Lane A | Lane B | 自动脱敏可靠性证据 vs 显式同意富训练轨迹 |

## 15. 高频面试问题与分层回答

### Q1：Function calling 和 MCP 有什么区别？

**30 秒回答**

Function calling 是模型产生 typed tool-call candidate 的交互方式；MCP 是 host、client、
server 之间发现工具和资源并交换消息的协议。二者都不等于授权或执行，policy、sandbox、
approval、WAL 和 recovery 仍由 Runtime 负责。

**2 分钟回答**

Tool schema 定义 arguments/result contract，function calling 让模型按该 contract 生成
候选。MCP 进一步标准化工具/resource discovery 和 transport，使不同 server 可互操作。
但即使 MCP server 宣布有 file_write，host 也应按 task scope 决定是否展示，校验路径、
申请审批、写 WAL、dispatch 并验证 post-state。协议层不能替代 security/control plane。

**深挖追问**

MCP tool description 本身也可能是不可信输入；要 pin server identity/version、限制
dynamic tool changes、隔离 credential，并将 tool result 当 data 处理。高风险 server
需要独立 sandbox 和 egress policy。

### Q2：为什么模型不能直接执行 tool？

**30 秒回答**

模型是概率 proposer，会受 injection、context 和 sampling 影响；执行需要确定性 authority。
我把模型输出通过 closed schema、semantic validation、policy、approval、grounding、WAL
和 budget 后才交给 sole executor，执行后再独立验证 post-state。

**2 分钟回答**

Model 可以选择 tool/arguments/risk，但不拥有 permission。Runtime 检查 tool 是否在当前
allowlist、参数是否越界、是否需审批、目标 revision 是否仍一致，并在 side effect 前写
intent。超时进入 unknown outcome，不能盲目 retry。这样即使模型被 prompt injection，
最坏影响仍被 capability 和 sandbox 限制。

**深挖追问**

对 readonly tool 也不能完全放松：它可能泄露 secret、触发高成本查询或成为 SSRF。需要
data-access ACL、query cap、network allowlist 和 output redaction。

### Q3：Tool timeout 后你会 retry 吗？

**30 秒回答**

不会直接 retry。Timeout 是 unknown outcome，不代表工具没执行。我先用 idempotency key
查 receipt 或观察 post-state；只有确认未执行，或执行端保证相同 key 去重，才 retry。
无法判断就人工升级。

**2 分钟回答**

Dispatch 前 WAL 写 PREPARED，带 stable idempotency key。若 client 超时，状态改为
UNKNOWN_OUTCOME，停止自动重试。先问 server 的 idempotency store，再用独立 observer
检查目标状态。确认已完成就 commit receipt；确认未发生才 retry；状态矛盾则进入
needs-review。对转账、邮件等非幂等动作尤其如此。

**深挖追问**

如果 server 不支持 idempotency，考虑 transactional outbox、provider request ID 或
业务侧唯一 constraint。仍无法建立 exactly-once 时，应诚实提供 at-least-once 加
dedup/compensation，而不是宣称 exactly-once。

### Q4：Prompt injection 怎么防？

**30 秒回答**

不靠一条 system prompt。我把网页/tool result/RAG 当 untrusted data，使用 capability
allowlist、least privilege、argument/egress validation、sandbox、敏感动作 approval、
secret isolation 和 post-state verification。目标是即使模型被注入，也无权造成越界
side effect。

**2 分钟回答**

先隔离 instruction 与 data，检索结果带 provenance/ACL，不让其中自然语言提升权限。
Host 只暴露当前 task 必要 tools，credential server-side 注入，文件/网络有明确 scope。
高影响动作展示精确 diff 和 target 给用户审批，批准后 re-ground。最后做 adversarial
eval：恶意网页、OCR、邮件和 MCP result 是否能诱导上传 secret 或改变目标。

**深挖追问**

Content sanitization 不可能可靠删除所有自然语言攻击，因此核心是 capability security。
还需防 indirect exfiltration，例如把 secret 编码进 DNS、URL path 或工具 argument。

### Q5：为什么要 compiler，是否在作弊？

**30 秒回答**

如果 compiler 只从一个主决策派生 contract 明确的冗余字段，它是接口规范化，不是作弊。
但必须冻结规则、保留 raw output、分别报告 raw 和 compiled 指标，不能根据 gold 修改
selected tool 或 arguments。

**2 分钟回答**

本项目 selected_tool 是主 terminal disposition，should_reject、should_fallback 和
expected_result 是冗余字段。固定 compiler 消除了 3 个冲突 case，semantic validity
0.85 -> 1.0，tool accuracy 不变。结论是“candidate + compiler”满足 contract，不是
“模型本身修好了”。后续 FP32 raw semantic validity 更低，也保持了这个边界。

**深挖追问**

更好的长期设计可能是减少模型输出冗余字段，或用 constrained state machine 直接生成
single discriminant union。兼容旧 schema 时 compiler 是合理迁移层。

### Q6：Lane A 为什么不能训练 GUI Agent？

**30 秒回答**

Lane A 只有脱敏 checkpoint、事件和工具安全摘要，明确没有原始任务、模型文本、tool
result、screenshot、Memory 或 Continuation。它能做 reliability/Verifier signals，
但没有 observation-action 语义，不能用于 GUI grounding 或 imitation learning。

**2 分钟回答**

本项目 mapper 只从可观察 Runtime facts 生成 failure、unknown outcome、policy denial、
recovery、budget 和 tool sequence labels，并保留 training_use 限制。富 episode 需要
独立 Lane B：默认关闭、逐次显式同意、可见采集、本地遮罩、retention/delete 和
post-state verifier。Lane B 当前待评审，不能把 Lane A 悄悄扩权。

**深挖追问**

即使有 consent，也需处理第三方窗口/旁观者 PII、屏幕变化、secret、版权、撤回和 derived
artifact deletion。Consent 是起点，不是全部 privacy design。

## 16. 本项目证据映射

### [本仓库已实现]

- Tool Router decision schema v1、closed-object validation、大小/枚举/跨字段
  fail-closed checks；
- 20 reviewed seed 与 20 frozen eval，10 类覆盖 normal、ambiguity、dangerous、
  approval、fallback、tool failure、duplicate、loop limit 等；
- deterministic non-model baseline、Base model、两版 LoRA 与统一 scorer；
- v2 在冻结 eval 上 tool accuracy 0.95，dangerous action candidate 与 dangerous
  false approval 均为零，但 raw semantic validity 0.85；
- Decision compilation v1 保留 raw prediction，只派生冗余 terminal fields，使
  compiled semantic validity 1.0、false refusal 3 -> 0；
- Lane A strict offline consumer：验证版本/digest，拒绝 rich fields，不启动 Provider、
  MCP、Desktop 或 network；
- Lane A reliability dataset mapper：deterministic failure、unknown outcome、
  policy denial、recovery、budget 和 tool sequence/outcome signals；
- Runtime 与模型仓库的职责边界已冻结：模型只能 proposal，Runtime 持有 Policy、
  Approval、Grounding、WAL、budget、recovery 和 Desktop boundary；
- 当前 preferred FP32 attached offline candidate 仍未得到 cross-machine portable
  qualification，也不具备 serving、promotion 或 Runtime readiness。

### [本仓库待实施]

- MCP/provider/desktop 的实际在线集成和 Agent serving；
- Lane B consent/capture/security contract 与富多模态 episode；
- 完整 Runtime failure-injection lab、online Agent eval 和 rollout；
- learned planner、long-horizon memory/RAG 与多 Agent coordination；
- learned Verifier/RM 对 action gate 的训练和校准；
- portable-package 独立机器正式执行结果。

面试中可以把 Tool Router、compiler、Lane A bridge 和 evidence gates 讲成已实现；MCP
执行、多模态 capture、learned verifier 和生产 rollout 必须讲成设计方案或下一阶段。

## 17. 自测与实践

### 自测题

1. JSON Schema valid 为什么不等于 action safe？
2. MCP 解决哪些互操作问题，又明确不解决哪些安全问题？
3. Router、planner、executor 的输入输出和 authority 分别是什么？
4. 为什么 approval 必须绑定 action snapshot，且执行前还要 re-ground？
5. Timeout、failure 和 unknown outcome 有什么不同？
6. Client 生成 idempotency key 为什么仍不足以保证 exactly-once？
7. WAL 和普通 observability log 的职责差异是什么？
8. Memory 与 checkpoint 为什么不能混用？
9. Compiler 在什么条件下合理，什么条件下是在隐藏错误？
10. Lane A 为什么只能支持 reliability/Verifier signals？

### 实践任务

1. 为 send_email 设计 schema、permission、approval、idempotency 和 receipt contract；
2. 实现 PREPARED/DISPATCHING/SUCCEEDED/UNKNOWN_OUTCOME 状态机及 crash tests；
3. 构造“server 已执行但 client timeout”的测试，证明盲目 retry 会重复 side effect；
4. 为恶意网页、tool result、OCR 和 MCP resource 写四组 injection eval；
5. 设计 task success、安全、副作用、recovery、latency 五维 Agent report；
6. 把一个冗余 JSON decision 改成 discriminated union，并说明向后兼容 compiler；
7. 为 Lane B 写一页 consent/retention/delete threat model，但不要实际打开采集。

真正可辩护的 Agent 工程不是“LLM 会调工具”，而是任何 proposal 都经过明确 authority，
任何 side effect 都有 durable identity，任何 crash 都有可解释恢复，任何安全结论都有
独立观察证据。
