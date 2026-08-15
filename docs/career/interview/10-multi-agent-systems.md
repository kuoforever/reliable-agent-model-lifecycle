# 10. Multi-Agent 协作与分布式 Agent 工程

> 本文是面试学习材料，不是项目进度 tracker。项目状态与唯一 active objective
> 只以仓库根目录 `PROJECT_STATUS.md` 为准。
>
> 证据标签：`[原理]`、`[通用工程]`、`[本仓库已实现]`、`[本仓库待实施]`。
> 本仓库中的 Project H 是正式 roadmap，但仍是 `[本仓库待实施]`；本章任何参考
> 架构、伪代码或实验设计都不能被描述为项目已经运行的系统。
> 仓库证据不自动证明个人作者身份；第一人称示例须先核对本人实际职责。

## 面试定位与学习目标

这一章面向 Agent Platform / Multi-Agent / Distributed Systems 面试。学完后应能：

1. 判断任务是否值得使用 Multi-Agent，并建立 Single-Agent control；
2. 区分 identity、role、capability 与 authority；
3. 设计 typed message/task/result/artifact/handoff contract；
4. 用 coordinator、task graph 与 routing 安排并行工作；
5. 设计 durable shared state、冲突仲裁、lease、heartbeat 和 crash recovery；
6. 实现分层 budget、cancellation、backpressure 和 loop guard；
7. 分离 worker、reviewer、verifier 与 final decision authority；
8. 用固定评测和 ablation 证明 Multi-Agent 的收益大于协调成本。

## 1. 什么是 Multi-Agent，什么不是

### 1.1 最小定义

`[原理]` 一个可工程化的 Multi-Agent system 至少有多个可独立调度的执行主体；每个
主体有明确 identity、输入合同、能力/权限边界、局部状态和可审计输出，并通过协议
协作完成共同任务。关键不是模型调用次数，而是 ownership、coordination 和 failure
semantics。

以下不自动构成可靠 Multi-Agent：

- 同一个 prompt 连续调用模型三次；
- 一个模型内部的 Mixture-of-Experts；
- 多个采样结果投票但没有 task ownership/typed result；
- 把同一 mutable 文件同时交给多个 worker；
- “让 Agent 互相讨论直到同意”但没有 budget、stop condition 和 verifier。

### 1.2 Single-Agent vs Multi-Agent

`[原理]`

| 维度 | Single-Agent | Multi-Agent |
|---|---|---|
| 上下文 | 一个主体持有主要上下文 | 上下文分片并需 handoff |
| 调度 | 顺序控制较简单 | DAG、routing、并发、取消 |
| 状态 | 较少 ownership 冲突 | 需要 durable shared state/版本 |
| 故障 | 一个执行流恢复 | worker crash、重复领取、部分完成 |
| 成本 | 较易预测 | 协调、重复推理和 review 开销 |
| 优势 | 低延迟、语义连贯 | 专业化、并行、独立验证、故障隔离 |

Multi-Agent 的合理收益来自任务的可分解性、并行度、专业能力差异或独立检查价值，
而不是“更多 Agent 更聪明”。

### 1.3 什么时候不要用

`[原理]` 下列情况通常优先 Single-Agent 或普通 deterministic workflow：

- 任务短、强顺序、共享上下文很大；
- 子任务无法定义独立 acceptance criteria；
- 所有 worker 会频繁修改同一状态，冲突成本高；
- 工具副作用缺少幂等/审批/恢复，增加 worker 只放大风险；
- latency 或成本预算很紧，协调开销超过工作本身；
- 结果可用一个 deterministic parser/rule/solver 可靠完成；
- 隐私/权限不允许把上下文复制给多个主体；
- 没有可靠 verifier，却把“多数同意”误当真值。

## 2. Identity、Role、Capability 与 Authority

### 2.1 四个概念

`[原理]`

- **Identity**：谁在执行。区分稳定 logical agent identity 与一次进程/会话的
  `agent_instance_id`；审计、lease 和消息都要绑定。
- **Role**：期望职责，例如 planner、data worker、implementer、reviewer；Role 是
  工作组织，不等于权限。
- **Capability**：能做什么，例如读代码、执行 GPU eval、解析 PDF；可能受环境和
  当前健康状态限制。
- **Authority**：被允许做什么，例如写哪些路径、调用哪些工具、批准哪个风险等级、
  是否能发布或产生外部副作用。

“模型知道如何删除文件”是 capability，不代表它有 authority。Reviewer role 也不
自动拥有 merge/promotion authority。

### 2.2 Capability declaration

`[通用工程]` Worker 注册可包含：

```json
{
  "logical_agent_id": "reviewer-code",
  "instance_id": "ephemeral-worker-42",
  "roles": ["reviewer"],
  "capabilities": ["python", "static-analysis"],
  "authorities": {
    "read_scopes": ["repo"],
    "write_scopes": [],
    "tools": ["test-runner"],
    "max_risk": "read_only"
  },
  "capacity": {"max_concurrent_tasks": 1},
  "contract_versions": ["task.v1", "result.v1"]
}
```

Coordinator 只能把任务路由给 capability 满足且 authority 覆盖的 worker。动态 prompt
不能扩大 authority；高风险工具调用仍经过独立 policy/approval boundary。

### 2.3 Least privilege 与隔离

`[通用工程]`

- 每个 task 发短期 scoped credential，而非共享长期 secret；
- read/write/tool/network 权限分别声明；
- artifact store 采用 immutable write-once generation 或 CAS；
- worker 不直接修改 coordinator state，只提交 typed transition request；
- reviewer 默认只读，final decider 与 implementer 分离；
- 记录 effective authority，而不只记录配置模板。

## 3. Typed Message、Task、Result、Artifact 与 Handoff

### 3.1 为什么要 Typed Contract

`[原理]` 自然语言适合表达开放任务，但不适合作为唯一控制协议。Typed contract 提供
schema validation、version negotiation、幂等、审计和 fail-closed 行为。自然语言
instruction 应是 typed envelope 中的字段，而不是隐含所有状态。

### 3.2 Message envelope

`[通用工程]`

```json
{
  "message_schema": "agent-message.v1",
  "message_id": "uuid",
  "logical_task_id": "task-123",
  "attempt_id": "attempt-2",
  "sender": "coordinator",
  "recipient": "worker-7",
  "type": "TASK_ASSIGNED",
  "created_at": "monotonic-and-wall-clock-metadata",
  "causation_id": "prior-message-id",
  "correlation_id": "root-task-id",
  "contract": {"task_schema": "task.v1"},
  "payload_digest": "sha256:..."
}
```

`message_id` 用于消息去重；`logical_task_id` 跨 attempts 不变；`attempt_id` 区分重试；
`causation_id` 建因果链；`correlation_id` 关联整次用户任务。接收方验证 schema、大小、
authority、deadline 和 digest 后才处理。

### 3.3 Task contract

一个可调度 task 至少包括：

- objective 与非目标；
- immutable input artifact references；
- allowed read/write/tool scopes；
- acceptance criteria 和 required validations；
- dependencies 与 expected output type；
- deadline、priority、token/cost/time/tool budgets；
- idempotency key、retry/unknown-outcome policy；
- parent task、depth、loop/hop limit；
- cancellation semantics 和 handoff requirements。

如果 acceptance 只能写成“感觉不错”，就很难可靠并行、review 或自动重试。

### 3.4 Result contract

`[通用工程]`

```json
{
  "result_schema": "task-result.v1",
  "logical_task_id": "task-123",
  "attempt_id": "attempt-2",
  "status": "SUCCEEDED",
  "summary": "bounded human-readable result",
  "artifacts": [
    {"uri": "immutable://...", "sha256": "...", "media_type": "text/markdown"}
  ],
  "validations": [
    {"name": "link-check", "status": "PASSED", "evidence_uri": "immutable://..."}
  ],
  "claims": ["what the evidence establishes"],
  "limitations": ["what it does not establish"],
  "changed_resources": ["scoped ownership record"],
  "next_action": "one bounded action"
}
```

`status=SUCCEEDED` 不是 worker 自报就可信。Coordinator/verifier 应重算 required checks、
解析 artifact 和确认 acceptance。Partial、blocked、cancelled、failed、unknown outcome
必须是不同状态，不能全部压成 error string。

### 3.5 Artifact 而非大段消息

`[原理]` 大型代码、数据、报告应写 immutable artifact，并在消息中传 URI、digest、
schema 和摘要。这样可避免 context 复制、截断与多版本混淆。Artifact ACL 仍按 task
scope；digest 不代替权限和 provenance。

### 3.6 Handoff

一个完整 handoff 至少回答：

1. outcome；
2. modified/produced artifacts；
3. exact validation 与结果；
4. unresolved risks/limitations；
5. ownership 是否释放；
6. single next action；
7. effective config/model/data/task revisions。

Handoff 是状态转换，不是聊天摘要。接收者在 durable state 中 accept 后才转移 owner；
发送者崩溃或消息重复时，ownership 仍能从 state/lease 恢复。

## 4. Coordinator、Task Graph 与 Routing

### 4.1 Task graph

`[原理]` 将任务表示为有向图 `G = (V, E)`：`V` 是 tasks，边 `u -> v` 表示 `v`
依赖 `u`。只有所有 required predecessors 成功且产物验证通过，task 才从 `PENDING`
变为 `READY`。

```text
root objective
  -> inspect/evidence freeze
  -> {implementation A, analysis B, test design C}
  -> integration
  -> independent review
  -> final decision
```

若图有 cycle，必须在执行前拒绝或显式建 iterative loop 及停止条件。Critical path
决定理论最短时间；给非 critical 小任务增加 worker 不一定降低总 latency。

### 4.2 Coordinator 职责

`[原理]`

- decomposition：创建有明确 acceptance 的 task；
- readiness：检查依赖与 artifact；
- routing：匹配 capability、authority、locality、cost、health；
- scheduling：priority、deadline、fairness、backpressure；
- ownership：发 lease/fencing token；
- aggregation：验证 typed results，构造下一 task；
- cancellation/recovery：传播停止并处理 stale attempts；
- final handoff：保持 claim boundary 和证据链。

Coordinator 不应把所有业务 logic 写成一个无法测试的 prompt。Deterministic state
transition、schema、budget、policy 和 retry 应由代码控制；模型适合开放 decomposition、
summarization 或语义判断，并由 verifier/limits 包围。

### 4.3 Routing score

`[通用工程]` 版本无关的候选评分可以表示：

```text
score(agent, task)
  = w_cap * capability_match
  + w_loc * data_locality
  + w_q   * historical_quality
  - w_c   * predicted_cost
  - w_l   * predicted_latency
  - w_r   * risk_penalty
```

硬约束（authority、schema、deadline 不可满足、health）先过滤，软评分再排序。历史
quality 要按 task slice 校准，避免一个领域表现好就路由所有任务。学习型 router 上线前
要与固定 heuristic/control 做离线和 canary 对照，并防止 feedback loop。

### 4.4 常见拓扑

`[原理]`

| 拓扑 | 优点 | 风险/适用边界 |
|---|---|---|
| Central coordinator | 状态和 policy 集中、易审计 | 单点/瓶颈，需 durable failover |
| Hierarchical supervisors | 扩展大任务、局部 context | 多级摘要失真、取消传播复杂 |
| Blackboard/shared workspace | 异步协作、artifact 可见 | 冲突、脏读、权限与版本管理 |
| Peer-to-peer negotiation | 去中心、弹性 | deadlock、重复工作、难做全局 budget |
| Fixed workflow/DAG | 可预测、易验证 | 对开放任务适应性较弱 |

生产系统常是混合：durable central task state + scoped worker autonomy + immutable
artifact store，而不是无限制 peer chat。

## 5. Durable Shared State 与冲突仲裁

### 5.1 Task 状态机

`[原理]` 一个最小状态机：

```text
PENDING -> READY -> LEASED -> RUNNING
                     |          |
                     |          +-> SUCCEEDED
                     |          +-> FAILED_RETRYABLE -> READY
                     |          +-> FAILED_FINAL
                     |          +-> UNKNOWN_OUTCOME -> RECONCILING
                     |          +-> CANCELLED
                     +-> lease expired -> READY or RECONCILING
```

每次 transition 带 expected version、actor identity、reason、timestamp、attempt、artifact
references。Event log append-only，materialized view 用于快速查询；两者都要有 schema
version 和 retention。

### 5.2 Optimistic Concurrency 与 CAS

`[原理]` 更新使用 compare-and-swap：

```text
update task
set state = RUNNING, version = 18
where task_id = X and state = LEASED and version = 17 and lease_owner = A
```

若影响行数为 0，说明状态已变化，worker 必须重新读取，不能覆盖。CAS 防止 lost update，
但不自动合并业务内容。

### 5.3 Artifact ownership 与冲突

`[通用工程]` 优先通过任务分片避免冲突：每个 worker 独占不同文件、数据 shard 或
namespace；共同输入 immutable。若必须共享：

- append-only event/artifact；
- content-addressed immutable generations；
- 分支/patch + single integrator；
- versioned document + three-way merge；
- semantic conflict 交 owner/reviewer，而非 last-write-wins；
- final manifest 原子指向完整 generation。

Last-write-wins 对缓存可接受，对代码、安全策略或 label 通常不可接受，因为它静默丢失
另一方有效工作。

### 5.4 Memory 边界

`[原理]` 区分：

- task-local scratch：attempt 结束可丢；
- durable task state：恢复必须保留；
- shared semantic memory：需 provenance、scope、TTL、conflict policy；
- artifact evidence：immutable、可验证；
- user/private context：最小披露、consent、retention/deletion。

把所有对话塞进共享 memory 会增加成本、泄露和 prompt injection surface。Handoff
应传必要事实、artifact refs 和 limitations，而非无限上下文复制。

## 6. Lease、Heartbeat 与 Crash Recovery

### 6.1 Lease 而非永久 ownership

`[原理]` Coordinator 给 worker 一个有截止时间的 lease：

```text
lease = {task_id, owner_instance, attempt_id, fencing_token, expires_at}
```

Worker 在 lease 内工作并 heartbeat 续期。Lease 过期只说明 coordinator 不再信任该
instance 的所有权，不证明它已停止；旧 worker 可能网络分区后继续运行。

### 6.2 Fencing token

`[原理]` 每次新 lease 获得单调递增 `fencing_token`。所有受保护写入/副作用 gateway
拒绝小于当前 token 的请求：

```text
attempt A gets token 41 -> partitioned
attempt B gets token 42 -> becomes current owner
A later writes with 41 -> rejected as stale
```

只有数据库里更新 owner 不够；资源端也必须验证 fencing token，才能阻止 zombie worker。

### 6.3 Heartbeat

Heartbeat 可包含 progress sequence、last safe checkpoint、current phase、budget used、
health 和 lease renewal request。频率是检测速度与控制面负载的折中；expiry 应容忍正常
抖动，但不能无限延长。Heartbeat 不应承载大结果，也不是成功证明。

### 6.4 Crash recovery

`[通用工程]`

1. Lease 超时，coordinator 标记 attempt lost；
2. 检查最后 durable checkpoint、WAL 和 external side effects；
3. 若纯计算且 output 未发布，可安全创建新 attempt；
4. 若可能有副作用，进入 `UNKNOWN_OUTCOME/RECONCILING`；
5. 新 worker 获更高 fencing token，从 validated checkpoint 恢复；
6. 旧 attempt 的迟到 result 被识别为 stale，保留审计但不覆盖 current state；
7. 对恢复后的 output 重新做 acceptance，不因“来自 retry”降低门禁。

### 6.5 故障实验

- worker 在无 checkpoint、写 checkpoint 中、artifact 发布前后 crash；
- heartbeat 丢失但 worker 仍运行；
- coordinator failover；
- duplicate/redelivered message；
- stale worker 晚提交；
- network partition 下两个 worker 都以为自己 owner；
- tool commit 后 response 丢失；
- reviewer crash 后 resume 不重复 final decision。

每个实验检查 task state、artifact generations、side-effect count、lease/fencing、budget
和 audit trail。

## 7. Budget、Cancellation、Backpressure 与 Loop Guard

### 7.1 分层 Budget

`[原理]` Root task budget 分配给子任务，不能让每个 child 都继承完整额度。预算维度：

- wall-clock deadline；
- model tokens / inference cost；
- tool calls 与昂贵资源；
- max concurrent workers；
- artifact/storage bytes；
- network/request retries；
- risk/side-effect approvals；
- task depth、messages/hops。

可用 reservation/commit：创建 child 时预留上限，完成后释放未用部分。Budget record
应 durable，多个 coordinator/worker 用 CAS 更新，避免并发超发。

### 7.2 Cancellation propagation

`[原理]` 取消是状态，不是“发一句停下”。Root cancelled 后：

1. 标记 cancellation epoch/reason；
2. 不再调度新的 descendants；
3. 向 running attempts 发送 cancellation token；
4. worker 在 safe points 停止、保存可用 checkpoint；
5. 正在进行的不可中断 tool 进入 reconcile，而非假装取消成功；
6. late results 标记 cancelled/stale，不能触发 downstream；
7. 释放 lease、reservation 和临时资源。

### 7.3 Backpressure

`[原理]` 使用有界 ready queue、per-tenant/priority quota 和 max in-flight。若到达率
`lambda` 长期大于 worker service rate `mu_total`，队列必然增长；扩容、降载或拒绝
必须发生。Little's Law：

```text
N = lambda * W
```

`N` 是平均在途任务，`W` 是平均停留时间。对重尾 task duration，平均值不足以保护
deadline，还需 oldest age、p95/p99、task cost class 和 critical path。

### 7.4 Loop Guard

`[通用工程]` 防止 planner/reviewer/worker 循环：

- task graph cycle detection；
- max depth、max descendants、max handoff hops；
- same `(objective, input digests, effective config)` 去重；
- consecutive no-progress count；
- repeated message/result digest detection；
- reviewer 只能提出有 acceptance criterion 的 change request；
- max revision rounds，超过后交 final decider/user；
- 每轮必须消耗预算且记录 progress delta；
- model 不能自行提高自己的 budget/authority。

“直到满意”为停止条件不可审计。应定义 test pass、risk threshold、max rounds 或人工决策。

## 8. Reviewer、Verifier 与 Final Decision

### 8.1 三者分工

`[原理]`

| 角色 | 输入 | 输出 | 不应做的事 |
|---|---|---|---|
| Reviewer | artifact、spec、diff、evidence | 有依据的 findings/approval recommendation | 把 worker summary 当验证 |
| Verifier | typed result、deterministic rules/tests | machine-readable pass/fail/metrics | 随意修改 acceptance threshold |
| Final decider | verified evidence、risk、authority | accept/reject/promote/escalate | 从多数 Agent 意见自动推导真值 |

Reviewer 可以是模型或人，但必须独立读取 primary artifact，必要时运行 checks。Verifier
尽量 deterministic、版本化并可重算。Final decision 必须由拥有该 scope authority 的
主体做；高风险场景可能必须人工批准。

### 8.2 独立性

`[原理]` 如果 implementer 与 reviewer 共享同一错误前提、上下文摘要或生成轨迹，
“两个 Agent 同意”不是独立证据。增强独立性：

- reviewer 从 spec/primary files 开始，而非只看 implementation summary；
- 使用不同检查方法或 deterministic oracle；
- 隐藏不必要的候选 rationale，减少 anchoring；
- 固定 acceptance criteria；
- 对 disagreement 分类并交 decider，而不是讨论到同意。

### 8.3 Reviewer loop 伪代码

`[通用工程]`

```python
for round_id in range(max_review_rounds):
    evidence = verifier.run(candidate, frozen_acceptance)
    findings = reviewer.inspect(primary_artifacts(candidate), evidence)
    if evidence.required_gates_pass and not findings.blocking:
        return final_decider.evaluate(candidate, evidence, findings)
    if not findings.actionable or budget.remaining <= 0:
        return escalate(candidate, evidence, findings)
    candidate = assign_scoped_revision(findings, new_attempt=True)

return escalate(reason="review_loop_limit")
```

## 9. 工程架构、配置与容量估算

### 9.1 参考架构

`[通用工程]`

```text
API / User
  -> Root task service
  -> Durable coordinator + task graph store
       -> capability/authority registry
       -> scheduler + budget ledger
       -> lease/heartbeat service
       -> bounded queues
  -> isolated workers
       -> model/tool adapters
       -> local checkpoint
  -> immutable artifact store
  -> deterministic verifier
  -> reviewer pool
  -> final decision / approval boundary
  -> traces, metrics, logs, audit/WAL
```

### 9.2 伪配置

```yaml
coordination:
  max_task_depth: 4
  max_descendants_per_root: 20
  max_review_rounds: 2
  duplicate_input_digest_policy: coalesce

leases:
  ttl_seconds: 60
  heartbeat_interval_seconds: 15
  fencing_required_for_writes: true

budgets:
  root_wall_time_seconds: 1800
  max_model_tokens: 200000
  max_tool_calls: 100
  max_concurrent_workers: 4

queues:
  ready_capacity: 1000
  fairness: tenant_weighted_deadline

recovery:
  retry_limit_by_error_class:
    transient_compute: 2
    invalid_contract: 0
    unknown_side_effect: 0
```

这些值仅用于表达合同。实际 TTL 必须大于健康 worker 的 heartbeat 抖动，且小于业务
允许的检测时间；budget 和 queue 由 task duration/cost 分布与 SLO 决定。

### 9.3 理论并行收益

`[原理]` 若工作中可并行比例为 `p`，使用 `n` 个 worker，忽略额外开销时 Amdahl 上界：

```text
speedup(n) <= 1 / ((1 - p) + p / n)
```

真实 Multi-Agent 还要减去 decomposition、context serialization、queue、handoff、
duplicate work、conflict、review 和 integration。可写端到端时间：

```text
T_total = T_decompose
        + T_critical_path_workers
        + T_coordination
        + T_integration
        + T_verification
        + T_recovery
```

因此“4 个 Agent”绝不自动等于 4 倍。应测 critical-path latency、sum worker time、
coordination overhead ratio 和 wasted work。

### 9.4 Worker capacity

`[通用工程]` 按 task class `k` 估计到达率 `lambda_k`、平均 service time `S_k` 和并发
resource cost。Worker utilization 的简化检查：

```text
rho ~= sum(lambda_k * S_k) / worker_count
```

当 `rho` 接近 1，尾延迟通常快速恶化；重尾任务、优先级和异构 worker 需用负载模拟
而非单一平均。Coordinator 还应限制总 model calls/GPU jobs/tool side effects，避免
CPU worker 空闲但昂贵下游已过载。

## 10. Evaluation、Control 与 Ablation

### 10.1 必须有 Single-Agent control

`[原理]` Multi-Agent 是否有效只能相对 control 判断。Control 应尽量固定：

- 同一 root tasks、数据和 expected results；
- 同一基础模型或明确记录差异；
- 同一 tool/capability/authority；
- 相近 token/cost/time budget；
- 相同 verifier、final decision 和安全 policy；
- 相同最大 retries 与环境。

若 Multi-Agent 使用 10 倍 token 和时间才提高 1%，必须报告成本，而不是只说成功率更高。

### 10.2 指标

`[原理]`

- task success / exact acceptance pass；
- safety violations、false approvals、policy denials；
- end-to-end p50/p95/p99 与 deadline miss；
- total/critical-path model tokens、tool calls、GPU time、money；
- coordination overhead、handoff count/size/error；
- duplicate/redundant work ratio；
- conflict/rework/review rounds；
- worker utilization、queue age、fairness；
- crash recovery success、lost/duplicate side effects、unknown outcomes；
- final claim correctness/calibration；
- human escalation rate。

### 10.3 固定任务集

`[通用工程]` 任务集应按可分解性、共享状态、风险、上下文大小和工具需求分层：

- 可完全并行的独立检索/分析；
- 有依赖的 DAG 实现任务；
- 高冲突共享文件任务；
- 需要独立 review/verifier 的任务；
- worker crash、duplicate message、network partition；
- 高风险 tool 与 unknown outcome；
- 本来就适合 Single-Agent 的短任务。

这样能看到 Multi-Agent 在哪类任务有正收益、在哪类退化，而非只挑最适合展示的案例。

### 10.4 Ablation

`[原理]` 每次拿掉一个组件，判断它的增量价值：

1. Single-Agent control；
2. Multi-Agent 但固定 round-robin routing；
3. 加 capability routing；
4. 加 typed handoff；
5. 加 durable state/lease/fencing；
6. 加 reviewer；
7. 加 deterministic verifier；
8. 加 shared memory 或 learning router。

若移除 coordinator 质量不变但成本下降，说明 coordinator 没产生价值；若 reviewer
提高质量却使 latency 失控，可只用于高风险 slice。Ablation 结论必须带置信区间或至少
重复次数、样本量与逐例差异，不能只报一次 demo。

### 10.5 Evaluation 伪代码

```python
for task in frozen_tasks:
    for system in [single_agent_control, multi_agent_candidate]:
        for seed in registered_seeds:
            result = run_with_equalized_budget(system, task, seed)
            verify_sample_ids_artifacts_and_side_effects(result)
            record_quality_cost_latency_safety_recovery(result)

compare_paired_results_by_task_slice()
run_preregistered_ablations()
publish_failures_and_limitations_not_only_aggregate_wins()
```

## 11. 故障模式与排障

| 症状 | 可能根因 | 关键证据 | 处置 |
|---|---|---|---|
| 两个 worker 修改同一文件 | ownership 分片失败 | lease/write scopes、diff | single owner + integrator/CAS |
| Task 重复执行 | message redelivery、lease race | logical/attempt IDs、fencing | 去重、稳定 idempotency key |
| Zombie worker 覆盖新结果 | 资源端不验证 fencing | token/version audit | 所有写入拒绝 stale token |
| Agent 互相发消息不停止 | task cycle/no-progress | causation graph、digest | hop/depth/no-progress guard |
| Root 已取消仍有副作用 | cancellation 未传播或不可中断 tool | cancellation epoch、WAL | stop scheduling + reconcile |
| Reviewer 总是同意 | 只看 summary、同一错误前提 | reviewer inputs/checks | primary artifact + independent verifier |
| 成功率升但成本爆炸 | 重复 work/过度 review | tokens、worker sum time | task-class routing、budget/ablation |
| Coordinator hang | durable state/leader failover 缺失 | event log、lease service | 恢复 materialized view/leader |
| Shared memory 注入/污染 | 无 provenance/scope | memory writer/source/TTL | typed entries、ACL、review/expiry |
| Majority vote 仍答错 | correlated agents/no oracle | per-agent rationale/evidence | verifier、不同方法、人工决策 |

### 排障顺序

1. 固定 root task、graph version、effective config 与 budget；
2. 从 durable state 重建 logical tasks、attempts、leases 和 causation graph；
3. 区分重复 message、重复 attempt 与重复 external effect；
4. 找 critical path、queue wait、worker time、review/integration overhead；
5. 核对 capability/authority routing 和 artifact digests；
6. 对 conflict 查看 expected/current version 与 owner；
7. 对 timeout 先判断是否 unknown outcome，再决定 retry；
8. 与 Single-Agent control 的逐 task 结果比较，定位结构性退化。

## 12. 概念比较速查

| 概念 | 正确边界 |
|---|---|
| Identity vs role | 谁在执行 vs 被期望承担什么职责 |
| Capability vs authority | 能做什么 vs 被允许做什么 |
| Logical task vs attempt | 用户语义不变的工作 vs 一次具体执行 |
| Message ID vs idempotency key | 消息投递去重 vs 外部逻辑操作去重 |
| Lease vs lock | 有期限、可恢复 ownership vs 常被理解为持有到释放；分布式锁也需 lease/fencing |
| Heartbeat vs progress | 活着/续租信号 vs 有有效产出；不能等同 |
| CAS vs merge | 防止覆盖旧版本 vs 解决两个有效内容的语义冲突 |
| Reviewer vs verifier | 语义审查与 findings vs 规则/测试复算 |
| Consensus vs correctness | 多数/协议达成一致 vs 结论真实；一致也可能共同出错 |
| Multi-Agent vs ensemble | 有任务/状态/权限协作 vs 多个预测聚合 |
| Cancellation vs rollback | 停止后续工作 vs 撤销已发生状态；后者未必可能 |

## 13. 高频面试题与分层答案

### Q1：什么时候 Multi-Agent 比 Single-Agent 更合适？

**30 秒答案**

当任务能切成有独立 acceptance 的子任务、可并行或需要专业能力/独立 review，并且
收益大于 context handoff、重复工作、冲突和调度成本时。短任务、强共享上下文、强顺序
或高副作用但无恢复语义时，我优先 Single-Agent 或 deterministic workflow。

**2 分钟答案**

我会先建同预算 Single-Agent control，再画 task DAG，估 critical path 与协调开销。
每个 child 有 typed input/output、scope、budget、owner 和 verifier；共享输入 immutable，
写入单 owner。用 success、latency、tokens/cost、handoff error、conflict、安全和 recovery
比较。如果只在可并行检索 slice 有收益，就只在那里启用，不做全局 Multi-Agent。

**深挖方向**

- Amdahl's Law 与 coordination overhead；
- task decomposition 的 acceptance criteria；
- context serialization 损失；
- privacy/authority 对并行度的限制。

### Q2：Lease、heartbeat 和 fencing token 为什么缺一不可？

**30 秒答案**

Lease 给 ownership 有期限，heartbeat 让健康 worker 续租；但网络分区后的旧 worker
可能继续运行，所以新 lease 要拿更大的 fencing token，资源端拒绝旧 token 写入。
否则两个 worker 都可能提交，数据库里“当前 owner”也挡不住 zombie side effect。

**2 分钟答案**

Task state 用 CAS 发 lease，包含 owner instance、attempt、expiry 和单调 token。Heartbeat
只续当前 version；超时后 coordinator 检查 checkpoint/WAL，再给新 attempt 更高 token。
所有 artifact publish、state update 和 tool gateway 都校验 token。旧 result 可以保留
审计但标 stale。若工具可能已 commit，则进入 unknown-outcome reconciliation，而不是
把 lease expiry 当成未执行证明。

**深挖方向**

- clock skew 与 lease deadline；
- fencing 必须在哪些资源层验证；
- coordinator failover 如何保持 token 单调；
- heartbeat frequency/TTL trade-off。

### Q3：如何防止 Multi-Agent 无限循环和成本失控？

**30 秒答案**

Root 使用分层 token/time/tool/concurrency budget，child 只能获得预留额度；task graph
做 cycle detection，并限制 depth、descendants、handoff hops 和 review rounds。检测相同
input/result digest 与连续 no-progress，达到阈值停止并交 final decider，而不是让 Agent
自行扩预算。

**2 分钟答案**

预算 durable 且 CAS 扣减，取消带 epoch 沿 descendants 传播；bounded queue 对下游
背压。每次 revision 必须关联 actionable finding 和新的 progress delta，重复 objective+
input+config coalesce。Tool side effect 有独立 approval/idempotency，不因还有 token 就
允许重复。Metrics 监控 total worker time、tokens、duplicate work、review rounds 和
critical-path improvement，以 ablation 决定哪些 task class 值得多 Agent。

**深挖方向**

- reservation/commit budget；
- late result 与 cancellation race；
- no-progress 的定义；
- retry budget 与 unknown outcome 的区别。

### Q4：Reviewer Agent 如何避免成为“橡皮图章”？

**30 秒答案**

Reviewer 必须读取 primary spec/artifact 和独立 evidence，而不是复述 implementer summary；
acceptance 事先冻结，deterministic verifier 重算关键 checks。Reviewer 输出具体 location、
severity、evidence 和 action，final decision 由有 authority 的主体做。

**2 分钟答案**

我会分离 implementer、reviewer、verifier、decider；reviewer 默认只读，用不同方法检查，
必要时盲化 rationale 降低 anchoring。Blocking finding 必须映射 acceptance criterion，
修复后新 attempt 再验证；设 max rounds，无法收敛就 escalation。用 defect detection、
false positive、review cost 和 escaped defects 做 reviewer ablation，而不是只看“是否同意”。

**深挖方向**

- reviewer 与 implementer 使用同一模型的相关错误；
- 多数投票为何不是 oracle；
- 如何校准 verifier threshold；
- 高风险 final human approval。

### Q5：如何评估 Multi-Agent 系统？

**30 秒答案**

用固定任务集与同模型、同工具、相近预算的 Single-Agent control 做 paired comparison；
同时看任务成功、安全、p95 latency、tokens/cost、handoff/conflict/重复工作和 crash
recovery。然后逐项 ablate routing、typed handoff、durable state、reviewer 和 verifier。

**2 分钟答案**

任务按并行度、共享状态、风险和上下文分层，包含本来不适合 Multi-Agent 的 control。
每个结果验证 sample/task IDs、artifact 和 external side-effect count；重复 seeds，报告
逐例差异和不确定性。若总体成功率上升只来自 10 倍成本，或短任务尾延迟恶化，就限制
启用范围。故障集覆盖 worker crash、duplicate message、stale lease 和 unknown outcome。

**深挖方向**

- equalized budget 的定义；
- offline task set 与线上分布漂移；
- task-level paired statistics；
- routing policy 的 exploration 风险。

## 14. 本项目映射与证据边界

### `[本仓库已实现]` 与 Multi-Agent 相关的基础

- 项目已经有严格 schema、immutable artifacts、hash/revision binding、offline validators、
  claim boundary 和跨仓 handoff discipline；这些是未来 Project H 可复用的工程原则。
- Desktop Runtime 侧已有 policy、approval、WAL、recovery、budget 等可靠执行边界，
  本仓库作为 consumer 不得绕过。
- 当前 Tool Router 是单模型/离线闭环证据，不是 Multi-Agent coordination system。

这些基础不能转换成“已实现 coordinator、lease、worker pool 或 Multi-Agent eval”。

### `[本仓库待实施]` Project H

Project H 规划但未实现的能力包括：

- `MA-001` identity/role/capability/authority；
- `MA-002` typed message/task/result/artifact/handoff；
- `MA-003` coordinator、task graph、capability routing；
- `MA-004` durable shared state、memory 与 conflict resolution；
- `MA-005` lease、heartbeat、worker crash recovery；
- `MA-006` budget、cancellation、backpressure、loop guard；
- `MA-007` reviewer、verifier 与 final decision；
- `MA-008` fixed Single-Agent vs Multi-Agent eval；
- 后续多进程/容器 worker、elastic scheduling 和 learning router/RL 实验。

面试表述示例：

> Project H 是我的正式设计路线，但当前还没有实现证据。现阶段能辩护的是已有
> artifact/eval/runtime boundary 如何为 typed handoff 和 durable execution 打基础。
> 我会用 Single-Agent control、故障注入和 ablation 验收 Multi-Agent，而不会把
> 规划文档或一次并行协作说成生产 Multi-Agent 系统。

## 15. 自测与实践

### 15.1 口头自测

1. 各用一句话定义 identity、role、capability、authority；
2. 解释 logical task、attempt、message ID、idempotency key 的区别；
3. 画 task state machine，并指出 unknown outcome 不能直接 retry；
4. 举例说明 lease 过期为什么仍需要 fencing；
5. 列出一个完整 handoff 的七个字段；
6. 说出五种 loop guard 和三个 cancellation race；
7. 解释多数 Agent 同意为什么不等于正确；
8. 给出一个应该拒绝使用 Multi-Agent 的任务及原因；
9. 准确说明 Project H 当前是 planned，而非 implemented。

### 15.2 纸面设计

选择一个“代码实现 + 数据分析 + 独立 review”的 root objective：

1. 画 DAG 和 critical path；
2. 为每个 task 写 input/output schema、acceptance、scope、budget；
3. 分配 identity/role/capability/authority；
4. 设计 lease TTL、heartbeat 和 fencing resource；
5. 指定 shared artifact ownership 与 conflict strategy；
6. 添加 root cancellation 和一个 unknown tool outcome；
7. 定义 Single-Agent control 与 Multi-Agent metrics；
8. 估算 coordination overhead 与可能 speedup。

### 15.3 最小工程实践

`[本仓库待实施]` Project H 的第一个可辩护 vertical slice 应尽量小：

1. 建版本化 `Task/Result/Artifact/Handoff` schemas 和 fail-closed validators；
2. 建 durable task table/event log，CAS transitions；
3. 一个 coordinator、两个只处理不重叠 artifacts 的 worker；
4. bounded queue、root/child budget、cancellation epoch；
5. lease/heartbeat/fencing，并注入 stale worker late write；
6. immutable artifact publish + deterministic verifier；
7. 一个 read-only reviewer 和有 authority 的 final decider；
8. 固定 Single-Agent control，比较质量、成本、latency、duplicate work；
9. 注入 worker crash、duplicate message、coordinator restart、unknown side effect；
10. 输出 machine-readable eval、failure report 和 limitations。

完成标准不是“多个 Agent 能聊天”，而是 task ownership 可恢复、消息可去重、写入可
fence、预算和取消可传播、结果可验证、故障不重复副作用，并且在固定 control 上证明
何种任务获得了可量化净收益。
