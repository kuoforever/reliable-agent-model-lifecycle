# 09. MLOps、可靠执行与可观测性

> 本文是面试学习材料，不是项目进度 tracker。项目状态与唯一 active objective
> 只以仓库根目录 `PROJECT_STATUS.md` 为准。
>
> 证据标签：`[原理]`、`[通用工程]`、`[本仓库已实现]`、`[本仓库待实施]`。
> 产品名和 API 会演进，本章强调版本无关的控制目标、数据合同和故障语义。
> 仓库证据不自动证明个人作者身份；第一人称示例须先核对本人实际职责。

## 面试定位与学习目标

这一章面向 ML Platform / MLOps / Reliable Agent / Production AI 面试。学完后应能：

1. 设计 data/model/artifact registry 与端到端 lineage；
2. 准确区分 hash、signature、origin binding、provenance 和 attestation；
3. 解释 CI/CD/CT、eval gate、canary、rollback 和 bad-case feedback；
4. 用 OpenTelemetry traces/metrics/logs 定位模型与 Agent 跨组件故障；
5. 定义 SLI/SLO/error budget，并让发布与扩容响应它们；
6. 解释 Kubernetes/KEDA/GPU scheduling 的核心边界；
7. 用 WAL、idempotency 和 reconciliation 处理 crash 与 unknown outcome；
8. 正确讲述本仓库的 evidence state machine，不把 artifact 身份说成生产就绪。

## 1. Registry 与 Lineage：先回答“这是什么”

### 1.1 三类 registry

`[原理]` Registry 不是一个“放模型的文件夹”，而是受版本合同约束的元数据与产物
索引。常见三类视图可以由一个平台实现，但概念应分开：

| Registry | 核心对象 | 至少应绑定 |
|---|---|---|
| Data registry | dataset snapshot / split / manifest | source、license/consent、schema、清洗、sample IDs、digest |
| Model registry | model/Adapter candidate 与 lifecycle state | base、训练配置、数据、eval、owner、status、limitations |
| Artifact registry | 不可变 bytes / image / package / report | digest、media type、size、origin、dependency、signature policy |

模型版本最好不是用户手写的 `model_final_v7`，而是一个 immutable candidate ID，
指向精确 base revision、Adapter/weights、tokenizer、prompt/compiler、generation config、
quantization、environment、eval reports 和 serving compatibility。

### 1.2 Lineage 是有向证据图

`[原理]` Lineage 可以表示为有向无环图：

```text
raw sources
  -> consent/license/redaction
  -> normalized dataset snapshot
  -> train/validation/eval split manifests
  -> code + config + environment + seed + hardware
  -> training run
  -> checkpoint / Adapter candidate
  -> offline eval and safety reports
  -> package / quantized variants
  -> serving deployment revision
  -> online traces and reviewed bad cases
  -> next dataset version
```

每条 edge 都要回答：由哪个可复现 transformation、在何时、由谁/哪个身份、使用
什么配置产生，输入和输出 digest 是什么。只有节点 hash 没有 transformation edge，
无法解释数据怎样进入模型或报告怎样从 prediction 计算。

### 1.3 Manifest 的最小结构

`[通用工程]` 版本无关伪结构：

```json
{
  "schema_version": 1,
  "artifact_id": "immutable-candidate-id",
  "media_type": "model-package",
  "files": [
    {"path": "relative/path", "size": 123, "sha256": "..."}
  ],
  "inputs": {
    "base_revision": "...",
    "dataset_manifest": "sha256:...",
    "code_commit": "...",
    "config_digest": "sha256:..."
  },
  "compatibility": {
    "tokenizer": "...",
    "execution_form": "attached-adapter",
    "required_compiler": "..."
  },
  "evidence": ["quality-report-id", "safety-report-id"],
  "limitations": ["..."]
}
```

Manifest 自己也必须有外部 trust root 或 digest；让文件内部声明自己的 hash 不能独立
证明它没有连同声明一起被替换。解析时拒绝路径穿越、重复路径、未知必需字段、大小
不符、digest 不符和部分下载。

## 2. Hash、Signature、Origin 与 Provenance

### 2.1 Hash 证明什么

`[原理]` Cryptographic hash 把 bytes 映射为固定长度 digest。若从可信位置获得期望
digest，重新计算一致可高置信地证明当前 bytes 与被摘要的 bytes 相同，并检测意外或
恶意修改。

Hash 单独不证明：

- 谁创建了 bytes；
- digest 是谁发布的；
- bytes 是否安全、正确、有许可；
- 某训练/推理真的按宣称方式执行；
- 同一 bytes 在另一机器行为一致；
- artifact 已获准部署。

攻击者若能同时替换文件和旁边的 hash 文本，一致性仍然成立。因此期望 digest 必须
来自独立可信根、签名 manifest、透明日志或其他受控渠道。

### 2.2 Signature 证明什么

`[原理]` Digital signature 通常由私钥对消息或其 digest 签名，验证者用公钥检查：

```text
Verify(public_key, message, signature) -> true / false
```

验证成功说明签名与该公钥和消息匹配；“该公钥属于谁、是否被撤销、签名时身份是否
可信”取决于证书、key management、identity provider 和 trust policy。签名也不证明
模型质量或运行行为。

### 2.3 Origin binding、Provenance 与 Attestation

`[原理]`

- **Origin binding**：把 exact bytes/digest 绑定到一个固定远端 repository/revision
  或发布记录；说明“这些 bytes 对应那个 origin record”。
- **Provenance**：描述 artifact 如何由输入、步骤、builder 和环境产生；可能是自报，
  也可能由受信系统记录。
- **Attestation**：某个身份对一条 statement 签名或以受信机制作证；可信度取决于
  attestor、statement schema、密钥和验证策略。
- **Transparency log**：append-only、可审计的公开/组织日志，帮助发现 equivocation
  或未公开替换；不自动保证 artifact 本身正确。

一个 unsigned hosted commit 可以有内容和 revision origin binding，却没有作者签名。
一个 signed artifact 也可能来自错误数据或失败 eval。供应链和质量门禁必须组合，而
不能互相替代。

## 3. 本项目 Evidence State Machine

### 3.1 面试用的 evidence DAG

`[本仓库已实现]` 本项目把证据 predicates 与决策 gates 分开。Hosted origin 与
same-environment replay 都依赖明确的 package identity，但两者彼此独立；后续
reassessment 才把它们与质量/资源/contract evidence 合取：

```text
byte identity ─┬─> hosted origin binding ───────────┐
               └─> same-environment replay ────────┼─> offline eligibility
quality / resource / contract evidence ────────────┘          │
                                                              └─> preferred decision

preferred package + each gate's own evidence ─┬─> portable qualification
                                               ├─> promotion decision
                                               ├─> serving decision
                                               ├─> merged-artifact decision
                                               └─> Runtime integration decision
```

合取箭头表示 eligibility 同时需要多类证据；下方分支表示每个 downstream decision
还需自己的独立 gate，不能由另一个分支推出。它也不是仓库历史的时间线：项目实际
先取得 same-recorded-environment replay，随后补 remote origin attestation，再通过
reassessment 合取冻结证据。

### 3.2 每一层证明与不证明

| 层级 | 本项目中对应含义 | 仍不证明 |
|---|---|---|
| Byte identity | composite manifest、file sizes 与 SHA-256 指向 exact package bytes | 作者、远端来源、行为、质量、可部署 |
| Origin binding | exact GitHub/Hugging Face hosted revisions 通过远端 metadata、Git blob SHA-1 与 package SHA-256 对应 | 作者签名、供应链签名、行为与 portability |
| Same-env replay | caller-supplied clean roots、同一记录环境重载并精确复现 20/20 raw 与 compiled outputs | cross-machine/driver/library portability、repeat variance |
| Cross-machine portability | 要在 operationally distinct qualifying native Windows target 重放并收集环境/身份 evidence | promotion、online SLO、Runtime safety |
| Promotion decision | owner 允许某 candidate 进入下一 lifecycle state | 服务性能或 Runtime integration 自动成立 |
| Serving decision | 目标引擎/硬件/负载下通过质量、兼容、SLO、容量和回滚 gate | Runtime 可执行高风险动作 |
| Runtime eligibility | model output 与 policy/approval/WAL/grounding/budget 等合同集成后独立批准 | 可由 serving 或 portability 自动推出 |

截至当前 canonical state，byte identity、origin binding、same-env replay、offline
eligibility 与 preferred decision 已有。Cross-machine portable-package formal result
尚不存在，所以 portable 仍为 false；promotion、serving、merged-artifact 和 Runtime
claims 也因各自没有完成独立 gate 而保持 false，不能把它们的状态归因于单一分支。

### 3.3 为什么它适合面试展开

这是一个典型的 **claim boundary** 故事：工程价值不只是“hash 了文件”，而是把
identity、origin、behavior、portability 和 deployment authority 拆成独立 predicates，
每个 predicate 有自己的输入、validator、failure reason 和 downstream consumer。

## 4. CI、CD 与 CT

### 4.1 三者边界

`[原理]`

| 流程 | 主要触发/输出 | 必须回答的问题 |
|---|---|---|
| CI: Continuous Integration | 代码/合同变化 -> build/test/static checks | 变更是否可集成且不破坏合同？ |
| CD: Continuous Delivery/Deployment | 已批准 artifact -> 环境/流量 | artifact 能否安全发布、灰度、回滚？ |
| CT: Continuous Training | 新数据/漂移/计划 -> 新 candidate | 是否应训练、数据是否合法、候选是否优于当前？ |

CT 不应等于“有新日志就自动训练并上线”。新数据先经过 consent、PII、schema、质量、
去重、污染和 split gate；训练只产生 candidate，不能跳过独立 eval 与 promotion。

### 4.2 Pipeline as evidence

`[通用工程]` 每个 stage 输出 machine-readable report，而不只返回 exit code：

```text
source change
 -> unit/schema/static/offline tests
 -> build immutable artifact + SBOM/provenance
 -> artifact integrity/compatibility scan
 -> frozen offline eval + safety + bad-case diff
 -> performance/load/recovery gates
 -> approval/promotion record
 -> canary
 -> progressive rollout
 -> online SLO/eval monitoring
```

Fail-closed 规则：缺报告、digest 不匹配、指标无法计算、样本遗漏、required check 未运行
均视为未通过，而不是“没有发现错误”。

## 5. Eval Gate、Canary 与 Rollback

### 5.1 Offline Eval Gate

`[原理]` 一个模型总分不能覆盖所有风险。门禁通常包含：

- dataset/eval identity 与 leakage audit；
- task quality：accuracy/F1/exact match/ranking/grounding；
- output contract：JSON/schema/semantic consistency；
- safety：false approval、dangerous candidate、false refusal；
- per-slice：语言、长度、工具、风险、tenant/task family；
- per-example regression：关键 case 不允许被 aggregate improvement 掩盖；
- numerical/artifact form：quantized、merged、attached、compiler dependency；
- resource：latency、memory、throughput、cost caps；
- evidence completeness：code/data/config/model/environment/report digests。

Threshold 应在看见 formal result 前锁定；若运行后修改 threshold，必须标为新 protocol，
不能回写原 gate。

### 5.2 Canary

`[通用工程]` Canary 让候选接收小比例真实流量，并保留稳定 control。分流应尽量按
用户/会话粘性，避免同一会话模型漂移。观察：

- request success、TTFT/TPOT/E2E、reject/error；
- task/业务成功 proxy 与人工 review；
- tool schema、安全 policy 事件和 fallback；
- cost、GPU/KV/queue；
- 按输入分布 slice 的漂移。

线上没有即时 label 时，可用 delayed label、verifier、shadow evaluation、抽样人工
review；这些 proxy 需先校准，不能把模型自评当 ground truth。

### 5.3 Rollback

Rollback contract 至少指定：稳定 artifact/config、触发阈值、owner、最大恢复时间、
进行中请求、cache/schema 兼容和数据 migration。模型回滚只能改变后续决策；已发出的
邮件、支付、文件修改等副作用必须由 Runtime 的 WAL/idempotency/reconciliation 处理。

## 6. Bad-case Feedback Loop

`[原理]` 可审计闭环：

```text
online/offline failure
 -> immutable case capture with privacy controls
 -> reproduce and classify
 -> root-cause bucket
 -> choose intervention: code / schema / data / model / policy / serving
 -> reviewed train/validation-only addition
 -> keep frozen eval unchanged
 -> train candidate
 -> full regression and safety gates
```

不要默认“模型错了就加训练数据”。可能根因是：parser/compiler、tool schema、policy、
retrieval、timeout、cache key、precision、serving config 或 label 本身。先做 failure
classification，再选择最小干预。

`[通用工程]` Bad case 记录包含：case ID、输入的受控/脱敏表示、model/config revision、
raw output、compiled decision、tool/runtime outcome、verifier/human label、trace ID、根因、
处置、是否进入 train/validation/eval。生产数据进入训练必须有 consent、retention、
deletion 和 PII policy。

## 7. OpenTelemetry：Traces、Metrics 与 Logs

### 7.1 三种信号的分工

`[原理]`

| 信号 | 最擅长回答 | LLM/Agent 示例 |
|---|---|---|
| Trace | 一次请求经过哪里、哪段慢/错 | gateway -> router -> model -> verifier -> tool |
| Metric | 系统整体是否偏离、频率和分布 | p99 TTFT、queue tokens、false approvals |
| Log | 某离散事件的结构化上下文 | rollout change、policy denial、artifact load error |

三者通过 trace/span ID、request/task ID、artifact/config revision 关联。不要把 prompt、
tool result、PII 或 secret 默认写入 telemetry；高价值 debugging 字段也要分级脱敏。

### 7.2 Trace 设计

`[通用工程]` 一条 Agent request 可拆：

```text
request span
  auth / quota
  prompt build / tokenize
  queue
  model prefill
  repeated decode iterations or aggregate decode span
  output compile / constrained decode
  verifier / policy / approval
  tool prepare / execute / reconcile
  response stream
```

Span attributes 使用低/受控 cardinality 字段：model family、artifact revision、status、
error class、token buckets、tenant class。具体 request ID 可放 trace/log，不要作为
Prometheus label 导致 time-series explosion。

Cross-process context 要显式传播。异步 task、queue message 和 tool call 应携带 trace
context 与业务 correlation ID；重试作为 linked/child attempt 记录，保留原 logical task。

### 7.3 Metrics 设计

`[通用工程]`

- Counter：requests、tokens、errors、retries、policy denials、unknown outcomes；
- Histogram：TTFT、TPOT、queue、tool latency、task duration；
- Gauge：queue tokens、active sequences、KV blocks、workers、leases；
- Up/down counter：in-flight tasks；
- Derived ratio：error rate、cache hit、acceptance、SLO goodput。

Prometheus 抓取/接收时间序列，Grafana 展示 dashboard 与关联 drill-down。Histogram
bucket 要覆盖 SLO 边界；只留平均值无法恢复尾延迟。Dashboard 不是可观测性的全部，
还需要 alert ownership、runbook 和可从图跳到 trace/log 的关联。

### 7.4 Sampling 与成本

Trace 可 head-based 或 tail-based sampling。普通成功请求低采样，error、high latency、
policy event、unknown outcome 和 canary 可高/全采样。Sampling policy 本身要版本化；
若只保留正常请求，incident 时会丢最关键证据。

## 8. SLI、SLO 与 Error Budget

### 8.1 定义

`[原理]`

- **SLI**：实际测量的服务水平，例如 30 秒内成功返回且通过 schema 的请求比例；
- **SLO**：某窗口内 SLI 的目标，例如 30 天 `>= 99.9%`；
- **SLA**：与客户/组织约定并可能有后果的合同；
- **Error budget**：SLO 允许的不良事件预算。

若目标成功率为 `S`，窗口总事件数为 `N`：

```text
allowed_bad_events = (1 - S) * N
```

若按时间可用性，窗口长度为 `W`：

```text
allowed_bad_time = (1 - S) * W
```

99.9% 在 30 天窗口的理论不可用时间约 43.2 分钟，但事件型 SLO 与时间型 SLO
不能混用。

### 8.2 AI 服务的 good event

`[原理]` HTTP 200 不等于成功。可定义：

```text
good = transport_success
    and latency_within_objective
    and output_contract_valid
    and no_policy_violation
```

任务质量 label 可能延迟，因此快速 operational SLO 与慢速 quality SLO 分开。
安全事件常是零容忍 gate，不应用大流量平均稀释。

### 8.3 Burn rate

`[通用工程]` Burn rate 表示当前消耗 error budget 的速度：

```text
burn_rate = observed_bad_fraction / allowed_bad_fraction
```

`burn_rate > 1` 表示按当前速度会耗尽预算。常用短窗口高 burn 捕获突发，长窗口
较低 burn 捕获慢性退化。告警要路由到 owner，并包含 model/config revision 和 runbook。

Error budget 耗尽时可冻结 rollout、降低实验流量、修复可靠性；不能一边 SLO 持续
失败一边以平均 quality 上升为理由继续 promotion。

## 9. Kubernetes、KEDA 与 GPU Scheduling

### 9.1 Kubernetes 中 GPU 工作负载

`[通用工程]` Kubernetes 负责 desired state、placement、restart 和 rollout，不理解
模型质量。GPU 通常通过 device plugin/资源扩展暴露；scheduler 根据 resource request、
node labels/affinity、taints/tolerations、拓扑与配额放置 Pod。

关键配置目标：

- GPU type/memory capability、driver/runtime compatibility；
- CPU/RAM/pinned memory 和本地模型 cache；
- node affinity、anti-affinity、topology spread；
- whole GPU、硬件分区或 time sharing 的隔离语义；
- startup/readiness/liveness probes 分工；
- graceful termination、preStop、stream drain；
- PodDisruptionBudget 与 rollout surge/unavailable；
- model image/package 拉取、验证与冷启动。

Kubernetes 原生资源调度通常看不到实时 KV Cache 或 GPU 显存碎片，serving 层仍需
自己的 admission/scheduler。Pod `Running` 也不等于模型 loaded/readiness passed。

### 9.2 Probes

- **Startup probe**：允许大模型加载较久，加载未完成不触发错误重启循环；
- **Readiness probe**：只有 artifact 校验、模型加载、warm-up 和依赖就绪后接流量；
- **Liveness probe**：检测无法自行恢复的卡死，不应用短暂 overload 触发 restart；
- **Deep health check**：可异步执行 reference inference，不应每次 probe 都昂贵生成。

### 9.3 KEDA / Event-driven Autoscaling

`[通用工程]` KEDA 类 autoscaling 将 queue、stream 或自定义 metric 转为副本需求。
LLM 服务的扩缩容信号可使用 queued tokens、oldest request age、predicted deadline
miss、KV pressure 和 goodput，而非只用 GPU utilization。

简单容量估算：

```text
desired_replicas ~= ceil(arrival_work_per_second
                         / sustainable_work_per_replica_at_SLO)
```

其中 work 最好以分桶 token/compute cost 表示。还要加入冷启动时间、突发安全余量、
scale-up rate limit、scale-down stabilization 和最小热副本。若模型加载 5 分钟，等
queue 爆满才扩容已经太迟，可结合预测/预热或保持 reserve。

### 9.4 GPU 调度风险

`[通用工程]`

- 资源请求与实际 GPU memory 不匹配导致 colocated OOM；
- 多 GPU Pod 未获得期望拓扑；
- 驱动/runtime/kernel 不兼容；
- scale-down 杀死长请求或持有 lease 的 worker；
- 本地 cache 使调度器偏向错误节点或磁盘打满；
- replica 多了但下游 tokenizer/storage/tool 成瓶颈；
- rolling update 同时驻留新旧大模型，峰值资源超预算。

## 10. Durable Execution：WAL、幂等与 Unknown Outcome

### 10.1 为什么“请求重试”不够

`[原理]` 对有副作用工具，客户端超时不能判断操作是否执行：

```text
worker sends "transfer funds"
  -> external system commits
  -> response is lost
  -> worker sees timeout
```

此时 outcome 是 **unknown**。盲目 retry 可能重复转账；直接标失败又可能与外部事实
不一致。Exactly-once 往往不是网络层自然提供的语义，而要由 idempotency、durable
state 和 reconciliation 组合实现“effectively once”。

### 10.2 WAL 状态机

`[原理]` Write-Ahead Log 要在副作用前 durable 地记录 intent：

```text
PLANNED
  -> PREPARED(intent, idempotency_key, approval, expected precondition)
  -> SENT/EXECUTING
  -> SUCCEEDED(result evidence)
     or FAILED(definitive failure)
     or UNKNOWN_OUTCOME(needs reconcile)
```

先写 `PREPARED`，再执行工具；crash 恢复时从 WAL 决定重试、查询或人工处理。状态
transition 应有 compare-and-swap/version 防止两个 worker 同时提交。

### 10.3 Idempotency

`[原理]` Idempotency key 代表同一逻辑操作，而非每次 HTTP attempt。外部系统若支持，
以 key 去重并返回首次结果；key 要绑定 tenant、operation type 和 canonical arguments，
有明确 retention 与冲突处理。

若工具不支持幂等键，可用：

- precondition/conditional write，例如仅当版本仍为 `v`；
- 查询外部唯一业务 ID；
- reservation/commit 两阶段协议；
- compensation，但补偿不一定等价于没发生；
- 将 unknown outcome 交人工而非自动重试。

### 10.4 Reconciliation 伪代码

`[通用工程]`

```python
record = wal.prepare(task_id, canonical_action, idempotency_key, approval)
try:
    result = tool.execute(record.action, key=record.idempotency_key)
except DefiniteRejection as exc:
    wal.fail(record, evidence=exc)
except TimeoutOrDisconnect:
    wal.mark_unknown(record)
    enqueue_reconciliation(record.id)
else:
    wal.succeed(record, canonical_result_digest(result))

def reconcile(record):
    observed = tool.lookup_by_idempotency_key(record.key)
    if observed.committed:
        wal.succeed(record, digest(observed.result))
    elif observed.definitely_absent and retry_policy_allows(record):
        retry_same_logical_operation(record)
    else:
        escalate_without_repeating_side_effect(record)
```

### 10.5 Crash recovery gate

注入 crash 点：WAL 前、WAL durable 后、send 前、外部 commit 后响应前、result 写入前。
对每个点验证最终状态、外部 side-effect count、重复数、unknown outcome 数、reconcile
证据和人工 escalation。没有故障注入就不能声称 crash-safe。

## 11. Incident Debugging

### 11.1 先恢复、再归因

`[通用工程]`

1. 确认安全影响和 blast radius，必要时停止 rollout/高风险工具；
2. 固定 incident 时间、artifact/config/deployment revisions；
3. 比较 control 与 canary，按模型、worker、GPU、tenant、长度切片；
4. 从 SLO alert 跳到 exemplars/trace，再到 structured logs/WAL；
5. 找最早异常事件，而非最后一个 timeout；
6. 选择 rollback、traffic shift、load shedding 或 dependency isolation；
7. 保全 evidence 后复现，区分 correlation、sufficiency 和 root cause；
8. 写 timeline、customer impact、trigger、contributing factors、检测/响应缺口和 action owner。

### 11.2 症状到证据

| 症状 | 首查 | 可能根因 |
|---|---|---|
| p99 latency 上升 | queue/prefill/decode/tool spans | overload、长输入、下游慢、scheduler |
| 错误率仅新 revision 上升 | artifact/config/canary split | 模型、schema、kernel、依赖不兼容 |
| 任务成功下降但 HTTP 正常 | task/verifier/human labels | quality drift、routing、retrieval、compiler |
| 重复副作用 | WAL/idempotency/attempt graph | timeout retry、key 变化、reconcile bug |
| Pending task 永不结束 | lease/heartbeat/state transition | worker crash、lost wakeup、stale ownership |
| Metric 正常但用户报错 | sampling/cardinality/drop path | telemetry 缺口、某 slice 被平均掩盖 |
| OOM 后重启循环 | GPU memory、startup/liveness | admission 失效、probe 误配、rollout 双驻留 |

### 11.3 Postmortem 的证据纪律

“重启后恢复”只证明 mitigation 有效，不证明 root cause。一个 trace 显示某 span 慢，
只定位症状；要通过 counterfactual、配置差异、reproduction 或故障注入建立因果。
Action item 要可验证，例如“新增 unknown-outcome crash test 并保证 side-effect count=1”，
而不是“加强监控”。

## 12. 概念比较速查

| 概念 | 正确边界 |
|---|---|
| Hash vs signature | bytes identity/integrity vs 某私钥对消息的认证声明 |
| Origin vs authorship | hosted revision 对应关系 vs 人/组织身份和授权 |
| Provenance vs reproducibility | 声明/记录如何产生 vs 能否独立重现行为 |
| Reproducibility vs portability | 某固定环境重现 vs 环境/机器变化后仍满足合同 |
| Registry vs object store | 生命周期/元数据/关系视图 vs 存 bytes 的底层介质 |
| CI vs CD vs CT | 集成验证 vs 发布部署 vs 产生新训练候选 |
| Canary vs shadow | 候选真实响应部分流量 vs 候选旁路计算不控制响应 |
| Monitoring vs observability | 预定义指标告警 vs 由 telemetry 推断未知内部状态的能力 |
| Retry vs reconciliation | 再执行一次 attempt vs 先查明 unknown external outcome |
| Exactly-once vs idempotent effect | 强端到端一次语义很难；通常用 key/WAL 达成效果不重复 |
| Pod healthy vs model ready | 进程存活 vs artifact 校验、加载、warm-up 与依赖通过 |

## 13. 高频面试题与分层答案

### Q1：为什么 hash 一致不等于来源可信？

**30 秒答案**

Hash 只把一组 bytes 映射成 digest；如果文件和旁边的 digest 都被替换，它们仍一致。
要证明来源，需要从独立可信根获得期望 digest，并把它绑定到固定 revision、签名身份
或透明日志。即便来源可信，也不自动证明质量、行为或可部署。

**2 分钟答案**

我会分四层：byte identity 说明当前 bytes 是哪一份；origin binding 说明它对应哪个
hosted revision；signature/attestation 说明哪个 key/identity 对 statement 作证；
provenance 说明如何由输入和 builder 产生。每层都有独立 trust assumption。之后还要
same-env replay、cross-machine portability、offline/online eval 和 promotion，不能从
hash 一步跳到 production readiness。

**深挖方向**

- manifest 自摘要为什么不是外部 trust root；
- unsigned commit 能证明和不能证明什么；
- key ownership/revocation；
- Git blob hash 与 package SHA-256 的交叉绑定。

### Q2：CI/CD/CT 怎样避免模型自动上线事故？

**30 秒答案**

CT 只产生 immutable candidate，不能直接更新 production。CI 验证代码和合同，
candidate 再过 frozen offline quality/safety、artifact、性能和恢复门禁，由独立 promotion
记录批准，CD 才 canary、渐进放量并按 SLO 自动停止/回滚。

**2 分钟答案**

每个 stage 输出带 digest 的 report，缺证据 fail-closed。数据触发 CT 前先过 consent、
PII、schema、去重和污染 gate；eval 有 per-slice/per-example safety。Canary 与 control
按会话粘性比较，观察延迟、错误、质量 proxy、工具安全和成本；error budget 高速消耗
就冻结 rollout。模型回滚不负责撤销外部动作，副作用由 Runtime WAL/idempotency 管理。

**深挖方向**

- delayed label 下如何监控 quality；
- threshold preregistration；
- shadow/canary 取舍；
- schema migration 与 rollback compatibility。

### Q3：如何设计一次 LLM/Agent 请求的可观测性？

**30 秒答案**

用 trace 串 gateway、queue、prefill/decode、compiler、verifier、policy 和 tool；用 metric
看 TTFT/TPOT、queue、错误、安全与 unknown outcome 分布；用 structured log 记录发布、
policy 和状态转换。三者绑定 trace ID、task ID、artifact/config revision，同时避免把
PII 和高 cardinality request ID 放进 metric labels。

**2 分钟答案**

我会为异步 queue 传播 trace context，重试保留 logical task 并新增 attempt span。
Latency histogram bucket 围绕 SLO，error/high latency/policy/unknown outcome 用 tail
sampling 全留。Dashboard 可从 SLO burn alert 跳 trace/log/WAL。每个 tool side effect
span 关联 idempotency key 与状态，但参数/result 做脱敏或只存 digest。

**深挖方向**

- head vs tail sampling；
- metric cardinality；
- percentile 聚合；
- trace 丢失如何检测。

### Q4：工具调用超时后为什么不能直接重试？

**30 秒答案**

超时只说明客户端没收到确定结果，外部系统可能已经 commit，属于 unknown outcome。
直接重试可能重复副作用。应先有 WAL 和稳定 idempotency key，超时后查询/reconcile；
只有证明未发生且 policy 允许时才重试，否则人工处理。

**2 分钟答案**

执行前 durable 写 `PREPARED`，记录 canonical action、approval、precondition 和 logical
idempotency key；发送后分别记 success、definite failure 或 unknown。恢复 worker 读取
WAL，用外部 lookup/业务 ID 查结果；同一逻辑操作的 attempt 共享 key。工具不支持
幂等时用 conditional write、reservation/commit 或 escalation。用 crash injection
覆盖外部 commit 后响应丢失，验证 side-effect count。

**深挖方向**

- idempotency key retention；
- CAS/state version；
- compensation 不等于 rollback；
- exactly-once 为什么是系统级 property。

## 14. 本项目映射与证据边界

### `[本仓库已实现]`

- Data/eval/model/config/artifact 使用固定 schema、manifest、revision、SHA-256 和
  reproducible validators；20-case eval 与 train/validation family separation 已冻结。
- FP32 attached package 已完成 composite byte identity、GitHub/Hugging Face remote
  revision-origin binding、same-recorded-environment clean-location exact replay、
  offline artifact eligibility reassessment 和 preferred offline candidate decision。
- Remote origin evidence 明确记录 package commit unsigned，因此没有 author/signature、
  supply-chain signature 或 transparency-log claim。
- Runtime Lane A bridge 消费脱敏 reliability evidence；它不包含原始任务、模型文本、
  tool result 正文、截图或 memory，不能被描述为富训练轨迹。
- 另一个 Runtime 仓库拥有 policy、approval、WAL、grounding、budget、recovery 和
  desktop boundary；本仓库不能绕过这些控制。

### 当前 exact boundary

`[本仓库已实现]` Portable-package qualification protocol 已冻结；
`[本仓库待实施]` 仍需要一台 operationally distinct qualifying native Windows GPU
host 执行 target replay。当前没有 formal cross-machine result。因此：

- `cross_machine_reproducibility_established=false`；
- `portable_package_eligible=false`；
- promotion、serving、merged-artifact 和 Runtime readiness 不得推导；
- target receipt 是 self-observed operational evidence，不是 hardware-backed remote
  attestation。

### `[本仓库待实施]`

- model/data registry 的在线控制面与生产 artifact promotion；
- serving CI/CD、canary、rollback、SLO/error budget；
- OpenTelemetry/Prometheus/Grafana 的模型服务 telemetry；
- Kubernetes/KEDA GPU deployment 与故障实验；
- bad-case 生产回流、显式同意 Lane B；
- 本仓库模型与 Runtime 的正式 eligibility/integration gate。

面试表述示例：

> 我实际完成的是离线 evidence engineering：把 byte identity、hosted origin、
> same-environment replay、offline eligibility 和 candidate preference 分开验证。
> Cross-machine、serving、promotion、Runtime 是独立后续 decision。我能讲完整的
> MLOps/observability/durable-execution 设计，但不会把未部署的系统说成生产经验。

## 15. 自测与实践

### 15.1 口头自测

1. 用一分钟分别定义 hash、signature、origin、provenance、attestation；
2. 解释为什么 same-environment replay 不是 portability；
3. 画出 CT candidate 到 production 的全部 gate；
4. 定义一个同时考虑 latency、schema 和 safety 的 good event；
5. 说明 p95 为什么不能从多个实例 p95 直接平均；
6. 解释 KEDA 为什么不应只看 GPU utilization；
7. 枚举 side effect 在五个 crash point 的恢复状态；
8. 说出本项目 evidence state 的当前终点和所有仍为 false 的 claims。

### 15.2 Manifest 与 lineage 练习

为任一模型 candidate 手写 manifest：

1. 列出 base/tokenizer/Adapter/compiler/config/environment；
2. 为每个输入给 immutable identity 和外部 trust root；
3. 画出 dataset -> train -> eval -> package -> deployment lineage；
4. 为每条 edge 写 transformation owner、code/config 和 output digest；
5. 列出 hash 一致后仍未建立的五个 claims；
6. 设计 schema migration 与旧 validator fail-closed 行为。

### 15.3 最小工程实践

`[本仓库待实施]` 可辩护的最小 MLOps/可靠性实验：

1. 建 immutable candidate registry 和完整 lineage manifest；
2. CI 生成带 digest 的 test/eval/artifact reports；
3. 用一个 control 和 candidate 做 shadow/canary 流量模拟；
4. 建 OTel trace，贯通 queue、model、verifier、policy 与 mock tool；
5. 导出 Prometheus-style counters/histograms，定义两个 SLO 与 burn alerts；
6. 用 bounded queue 指标驱动 event-based scale simulation；
7. 实现 WAL/idempotency mock tool，注入 commit-after-response-loss；
8. 验证 side-effect count、unknown outcome、reconciliation 和 rollback evidence；
9. 输出 incident timeline 与可验证 action items。

完成标准不是“搭了 dashboard”或“文件有 hash”，而是每个线上决定都有可追溯输入，
每个 claim 有独立门禁，每个未知结果有恢复语义，每个告警能落到 owner、runbook 和
可验证修复。
