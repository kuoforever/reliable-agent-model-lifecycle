# 07. 推理服务、量化与在线系统

> 本文是面试学习材料，不是项目进度 tracker。项目状态与唯一 active objective
> 只以仓库根目录 `PROJECT_STATUS.md` 为准。
>
> 证据标签：`[原理]` 表示稳定的理论知识；`[通用工程]` 表示需要结合具体框架、
> 硬件和版本验证的行业做法；`[本仓库已实现]` 只引用已有代码、测试、指标和产物；
> `[本仓库待实施]` 表示路线图能力，不能在面试中说成已经完成。
> 仓库证据不自动证明个人作者身份；第一人称示例须先核对本人实际职责。

## 面试定位与学习目标

这一章面向 LLM Inference / AI Infra / Agent Platform 面试。学完后应能：

1. 从 autoregressive generation 数据流解释 `prefill`、`decode` 和 KV Cache；
2. 区分量化的对象、时机、粒度与校准方法，并设计质量/性能双门禁；
3. 解释 PagedAttention、continuous batching、prefix cache、speculative decoding；
4. 用 TTFT、TPOT、吞吐、显存和排队模型做容量估算，而不是只报 tokens/s；
5. 设计 admission control、backpressure、routing、fallback、canary 和 rollback；
6. 清楚说明本仓库只有离线模型证据，尚无 serving 证据。

## 1. 在线生成的数据流

### 1.1 从请求到 token

`[原理]` Decoder-only LLM 的一次在线请求可抽象为：

```text
request
  -> authentication / quota / request validation
  -> tokenizer and prompt construction
  -> admission control and queue
  -> scheduler forms a batch
  -> prefill: process all prompt tokens, create KV Cache
  -> decode: repeatedly predict one next token per active sequence
  -> stopping / constrained decoding / detokenization
  -> stream response and record metrics
```

对长度为 `T_in` 的输入和 `T_out` 的输出，模型不是一次性产生全部输出。
Prefill 处理整个 prompt；随后 decode 每一步只新增一个 token，但会读取此前的
KV Cache。两阶段的负载形态不同，因此必须分别度量和调优。

### 1.2 Prefill 与 Decode

`[原理]` Prefill 对 prompt 中多个 token 做大矩阵运算，并为每层生成 K/V。
在常见负载上它更容易利用 GPU 并行度，往往偏 compute-heavy；decode 每一步的
query 很短，却要反复读取模型权重和已有 KV，往往更容易受 memory bandwidth、
调度间隙和小矩阵利用率限制。这里的“往往”不是硬件无关定律：长上下文、特殊
attention kernel、并行拓扑和 batch 形状都可能改变瓶颈，必须以 profile 为准。

| 维度 | Prefill | Decode |
|---|---|---|
| 输入 | 整段 prompt | 每个活跃序列一个新 token |
| 首要用户指标 | TTFT | TPOT / inter-token latency |
| 典型优化 | prompt batching、prefix reuse、attention kernel | continuous batching、KV 管理、调度 |
| 资源压力 | 计算和临时激活 | 权重/KV 读带宽和 KV 容量 |
| 过载表现 | 首 token 排队变长 | token 间隔抖动、尾延迟恶化 |

将两阶段混成一个平均 latency 会掩盖问题。例如，短回答可能 TTFT 很差但总时延
尚可；长回答可能 TTFT 很好但 TPOT 在高并发时恶化。

### 1.3 KV Cache 的作用与显存估算

`[原理]` 自回归第 `t` 步如果重新计算前 `t-1` 个 token 的 K/V，会产生大量重复
计算。KV Cache 保存每层历史 token 的 key/value，使新一步只计算新增 token 的
投影，然后与历史 K/V 做 attention。

单条序列 KV payload 的一阶估算为：

```text
M_kv = 2 * L * T * H_kv * D_head * B_dtype
```

变量定义：

- `2`：分别保存 key 和 value；
- `L`：Transformer 层数；
- `T`：该序列已缓存的 token 数；
- `H_kv`：KV head 数；MHA 通常等于 query head 数，GQA/MQA 更少；
- `D_head`：每个 head 的维度；
- `B_dtype`：每个 KV 元素的字节数，例如某种 16-bit 格式通常为 2 bytes。

总 KV payload 近似为所有活跃序列之和。实际预留还要加入 page/block 内部碎片、
allocator metadata、CUDA workspace、临时激活和安全余量：

```text
M_total ~= M_weights + sum(M_kv_i) + M_workspace + M_runtime + M_margin
```

权重的一阶估算是 `M_weights ~= P * B_weight`，其中 `P` 为参数量，
`B_weight` 为平均每参数存储字节；量化 scale、zero-point、packing 对齐和未量化
层会让实际值高于理想 bit-width。容量评估必须测真实进程峰值，不能只做除法。

## 2. 量化：对象、时机、粒度与校准

### 2.1 量化的统一表达

`[原理]` 常见 affine quantization 可写为：

```text
q = clamp(round(x / s) + z, q_min, q_max)
x_hat = s * (q - z)
```

其中 `x` 是浮点值，`q` 是整数码，`s > 0` 是 scale，`z` 是 zero-point，
`[q_min, q_max]` 是整数范围，`x_hat` 是反量化近似值。对称量化通常令 `z=0`；
非对称量化能更贴合偏移分布，但 metadata 和 kernel 处理可能更复杂。

量化误差不是单一“精度损失”。它会经过层归一化、残差、softmax、采样和 argmax
传播，在小 logit margin 处可能改变 token。必须以任务指标、逐例回归和安全指标
评估，而不是只比较平均 tensor error。

### 2.2 Dynamic、Static 与 Weight-only

`[原理]` 这些术语回答不同问题：

| 方法 | 权重参数 | activation 参数 | 校准 | 典型取舍 |
|---|---|---|---|---|
| Dynamic quantization | 通常提前量化 | 运行时按当前输入求 scale | 通常不需离线校准集 | 接入简单，但运行时转换有成本 |
| Static quantization | 提前量化 | 使用离线校准确定范围 | 需要代表性校准集 | kernel 友好，但分布漂移更敏感 |
| Weight-only | 权重量化 | activation 保持较高精度 | 方法相关 | 主要减少权重带宽/显存，常用于 LLM |
| Weight + activation | 两者都量化 | 运行时使用既定或动态参数 | 通常更依赖校准 | 潜在收益更大，质量和 kernel 风险更高 |

Dynamic/static 描述量化参数何时获得；weight-only 描述量化对象。它们不是互斥的
同一分类轴。

### 2.3 粒度

`[原理]` 常见粒度包括 per-tensor、per-channel 和 group-wise：

- per-tensor：整张量共享 scale，metadata 少，但 outlier 影响大；
- per-channel：每个输出通道等维度独立 scale，通常误差更低；
- group-wise：把通道内元素再分组，是质量、metadata 和 kernel 效率的折中；
- token-wise activation：按 token 动态缩放，可适应输入差异，但增加运行时工作。

粒度越细通常越能拟合分布，却不保证端到端更快。额外 scale 读取、unpack、
dequant 和不匹配的 kernel 都可能抵消带宽收益。

### 2.4 GPTQ、AWQ 与 bitsandbytes 的面试边界

`[通用工程]` 版本无关地理解三者：

- **GPTQ**：典型 post-training weight-only 路线，用少量校准数据和近似二阶信息
  逐块选择权重量化误差，使层输出重构更好；离线转换成本较高，效果依赖校准、
  group size、damping、执行顺序和部署 kernel。
- **AWQ**：利用 activation 统计寻找重要权重/通道，通过缩放或保护 salient
  weights 减少量化伤害；仍需要代表性校准和匹配的推理实现。
- **bitsandbytes 类运行时量化**：强调便捷加载、低比特权重表示或训练时低显存；
  “能加载”不等于目标 serving engine 上有最佳 kernel，也不等于得到可部署产物。

不要把库名当算法结论。面试时先说清：bit-width、量化对象、粒度、校准数据、
计算 dtype、目标 kernel、模型架构、质量门禁和硬件，最后再说工具。

### 2.5 校准集设计

`[通用工程]` 校准集至少应覆盖：

- 线上 prompt 长度和语言分布；
- system prompt、tool schema、结构化输出等真实模板；
- 长上下文、代码、数字、稀有 token 与 outlier-heavy 样本；
- 安全拒绝和高风险工具调用；
- 不进入最终 test 的独立样本，防止以测试答案调量化参数。

校准过程应绑定数据版本、抽样 seed、tokenizer、preprocessing、算法配置和产物 hash。
门禁应比较未量化 reference 与候选在同一 frozen eval 上的质量、逐例变化、延迟、
吞吐、显存和失败率。

## 3. KV 管理与批处理调度

### 3.1 PagedAttention 的核心思想

`[原理]` PagedAttention 类设计把每条序列的逻辑 KV 地址映射到非连续的固定大小
物理 block/page，类似虚拟内存页表。调度器按需分配 block，kernel 通过 block
table 访问逻辑连续的历史 token。

价值主要是：

- 避免为最大长度预留一整块连续 KV；
- 降低不同序列长度造成的外部碎片；
- 支持序列增长、回收和共享前缀 block；
- 让调度器以 token/block 而不是“请求个数”做容量管理。

代价包括地址映射、block 内部碎片、复杂 kernel 与元数据一致性。Page size 太小会
增加元数据和访问开销，太大又浪费尾部空间，必须按真实长度分布 benchmark。

### 3.2 Continuous batching

`[原理]` 静态 batching 等整批完成再接收下一批，短序列会被长序列拖住。
Continuous batching 在 decode 迭代边界移除已完成序列并插入新序列，使 GPU
持续服务动态请求集合。

调度不能只追求总 tokens/s。若长 prefill 一次占满预算，正在流式输出的 decode
可能出现 TPOT 尖峰；若永远优先 decode，长 prompt 会饥饿。常见控制量包括：

- 每轮最大 scheduled tokens；
- prefill chunk 大小；
- 同时活跃序列/KV block 上限；
- prefill 与 decode 的优先级或时间预算；
- tenant、公平性、deadline 和 age；
- 已生成 token、最大输出和取消状态。

### 3.3 Prefix cache

`[通用工程]` Prefix cache 在多个请求具有完全一致的 token 前缀和兼容模型配置时，
复用已计算 KV。适用于固定 system prompt、相同工具 schema 或共享文档前缀。

Cache key 至少应绑定：模型/Adapter 版本、tokenizer、精确 token IDs、position/RoPE
配置、attention 相关参数和影响 forward 的输入。文本相同但 tokenization、Adapter
或 position 不同不能复用。收益看“可复用 token 比例”和命中后的真实 TTFT，不能
只看 request hit rate。还要处理租户隔离、敏感前缀残留、TTL 和显存驱逐。

### 3.4 Speculative decoding

`[原理]` Speculative decoding 用较便宜的 draft model 一次提出多个候选 token，
target model 并行验证；按接受规则保留前缀，遇到拒绝后由 target 修正。正确实现的
目标是保持 target distribution，而不是让 draft 替代 target 做最终决定。

粗略收益取决于：

```text
effective_speedup = useful_accepted_tokens / total_target_time_with_overheads
```

必须观测 acceptance rate、每次 draft 长度、verification batch 效率、额外 KV、
draft 开销和端到端 TPOT。小模型未必总是更快：若接受率低、target 已高度优化或
请求很短，额外调度会退化。

### 3.5 Structured / constrained decoding

`[原理]` 受约束解码把 JSON Schema、grammar、正则或 finite-state machine 编译为
当前前缀下的合法 token 集，在 logits 上屏蔽非法 token：

```text
logits'_i = logits_i,  if token i is allowed
logits'_i = -infinity, otherwise
```

它可以保证语法或 schema 层合法，不保证语义正确、参数真实、授权充分或工具安全。
Tokenizer token 与 grammar 字符边界不一一对应，因此实现需维护增量 parser 状态，
并处理 UTF-8、转义、空合法集合、停止条件和流式输出。

## 4. 在线系统架构与控制面

### 4.1 参考架构

`[通用工程]`

```text
Client
  -> Gateway: auth, schema, rate limit, idempotency/correlation id
  -> Router: model/Adapter selection, fallback policy
  -> Admission controller: queue/token/KV/SLO budget
  -> Scheduler: continuous batching, prefill/decode policy
  -> Model workers: weights, KV manager, constrained decoder
  -> Stream multiplexer
  -> telemetry + eval sampling + artifact registry
```

控制面管理模型版本、Adapter、流量权重、配额和 rollout；数据面处理 token。不要让
每个请求同步访问控制数据库，否则控制面抖动会进入 TPOT。配置应有可审计快照并
随 trace 记录生效版本。

### 4.2 Admission control 与 backpressure

`[原理]` Admission control 在系统尚能给出有界行为时拒绝或排队，而不是把所有
请求塞进 worker 直到 OOM。请求成本至少由 prompt tokens、最大输出 tokens、
模型/Adapter、优先级、deadline 和预计 KV 占用估算。

```python
# 版本无关伪代码
cost = estimate_tokens(request) + estimate_kv_blocks(request)
if queue_age(request) > deadline_budget:
    reject("deadline_would_be_missed")
elif tenant_budget_exhausted(request.tenant):
    reject("quota_exceeded")
elif not capacity.reserve(cost):
    retry_after_or_shed(request)
else:
    enqueue(request, reservation=cost)
```

Backpressure 要沿调用链传播：有界队列、超时、取消、`Retry-After`、客户端并发限制、
最大 prompt/output 和负载分级。无界队列只会把错误从“明确拒绝”变成“超时风暴”。

### 4.3 Model routing 与 fallback

`[通用工程]` Router 可依据 task type、风险、上下文长度、语言、tenant、成本、
质量阈值和实时健康度选择模型。路由策略必须有固定评测与审计字段：为什么选、
候选集合、版本、置信/门禁、fallback 原因。

Fallback 不是简单“失败就换小模型”。需要规定：

- 哪些错误可重试，哪些错误可能已产生外部副作用；
- fallback 是否满足相同 tool/schema/安全合同；
- 上下文能否无损迁移，tokenizer 和窗口是否兼容；
- 质量降级是否对用户显式；
- 是否会在两个 unhealthy backend 间形成 retry amplification。

### 4.4 Multi-LoRA Serving

`[通用工程]` 多 Adapter 服务可共享 base 权重，并按请求选择 LoRA。第 `j` 个线性层
可写为：

```text
y = W x + scale * B(Ax)
```

其中 `W` 是共享 base，`A/B` 是 Adapter 低秩矩阵。每个请求绑定 immutable
Adapter version；batch 内若混合 Adapter，kernel/调度必须正确选择对应权重。

权衡：减少 base 复制和冷启动，但会增加 Adapter 显存、加载/驱逐、混合 batch
效率、租户隔离和版本路由复杂度。热切换必须先校验 manifest、兼容 base revision、
rank/target modules、质量门禁，再原子发布；不能在一个请求中途换 Adapter。

### 4.5 配置示例

`[通用工程]` 以下只是表达设计意图的伪配置，不对应某个框架的稳定 API：

```yaml
service:
  request_timeout_ms: 30000
  max_prompt_tokens: 8192
  max_output_tokens: 1024
  bounded_queue_tokens: 200000

scheduler:
  max_scheduled_tokens_per_iteration: 4096
  prefill_chunk_tokens: 1024
  fairness: tenant_weighted_deadline

memory:
  kv_block_tokens: 16
  reserve_fraction_for_runtime: 0.10

rollout:
  canary_traffic_fraction: 0.01
  automatic_rollback_on:
    - safety_gate_failure
    - error_rate_budget_exhausted
    - p99_ttft_regression
```

真实值必须由目标模型、GPU、上下文分布和 benchmark 得出，不能复制示例。

## 5. 指标、容量与成本

### 5.1 用户侧与系统侧指标

`[原理]`

| 指标 | 定义 | 常见误区 |
|---|---|---|
| TTFT | 接收请求到首个可见 token 的时间 | 不拆 queue、tokenize、prefill |
| TPOT | 首 token 后相邻输出 token 的平均/分布 | 只报平均，掩盖 stall |
| E2E latency | 请求到完成的总时间 | 不按输入/输出长度分桶 |
| Throughput | 单位时间完成的 requests 或 generated tokens | 混淆 input 与 output tokens |
| Goodput | 满足质量和 SLO 的有效吞吐 | 只追求 raw throughput |
| Queue time | admission 后到执行开始 | 与 compute latency 混在一起 |
| KV utilization | 有效 KV payload / 可用 KV 容量 | 忽略碎片与 reserve |
| Error/reject rate | 按原因分类的失败/主动拒绝 | 把 overload rejection 当模型错误 |

所有 latency 都至少报告 p50/p95/p99，并按模型、版本、prompt/output bucket、
tenant/priority 和冷/热 cache 分层。Percentile 不能相加；要从端到端 trace 或原始
样本重新计算整条路径分位数。

### 5.2 容量估算

`[原理]` Little's Law 在稳定系统中给出：

```text
N = lambda * W
```

`N` 为系统平均在途请求数，`lambda` 为平均到达/完成率，`W` 为平均停留时间。
它用于 sanity check，不替代尾延迟与突发流量测试。

显存上限给出另一个约束：

```text
max_active ~= floor((M_gpu - M_weights - M_runtime - M_margin)
                   / E[M_kv_per_request])
```

但实际 admission 应按 token/block 预留而不是平均请求。容量报告至少扫描：并发、
输入/输出长度、arrival pattern、cache hit、Adapter mix、quantization、SLO 和 error。

### 5.3 成本模型

`[通用工程]` 一阶 GPU 成本：

```text
cost_per_1M_output_tokens
  = gpu_hour_price * gpu_count / output_tokens_per_hour * 1,000,000
```

还需计入闲置冗余、CPU/RAM、网络、存储、control plane、失败/重试、canary 和
工程运维。若 quality 或 SLO 未过，便宜的 raw token 不是有效成本优势，应比较
`cost per successful SLO-compliant task`。

## 6. 发布门禁、Canary 与 Rollback

`[通用工程]` 候选服务发布至少分离以下门禁：

1. artifact gate：来源、hash、格式、依赖、license、签名策略；
2. offline quality gate：固定 eval、逐例 regression、安全与 schema；
3. load/correctness gate：模型可加载、reference outputs、约束解码；
4. performance gate：目标硬件上 TTFT/TPOT/throughput/VRAM；
5. stress/soak gate：突发、长上下文、取消、OOM 防护、内存泄漏；
6. canary gate：小流量对比错误、SLO、质量 proxy 和业务成功；
7. promotion decision：由明确 owner 基于所有证据决定，不由“测试通过”自动推导。

Rollback 要提前验证：旧 artifact 仍可解析、配置与 schema 向后兼容、流量权重可
原子切换、进行中请求如何完成、cache 是否隔离、数据库/工具副作用是否可恢复。
模型回滚不能撤销已经执行的外部动作，因此 Agent Runtime 仍需 policy、approval、
WAL 和幂等控制。

## 7. 故障模式与排障

### 7.1 常见故障矩阵

| 症状 | 优先假设 | 关键证据 | 常见处置 |
|---|---|---|---|
| TTFT p99 上升，TPOT 稳定 | 排队或长 prefill | queue span、prompt bucket | 限长、chunked prefill、扩容/削峰 |
| TTFT 稳定，TPOT 抖动 | decode 调度/KV/带宽 | iteration gap、active seq、KV | 调整 token budget、公平性、并发 |
| 吞吐上升但 goodput 下降 | 过度 batching 导致 SLO 违约 | SLO-compliant tokens | 降 batch 或分服务等级 |
| 随长度增长 OOM | KV 估算/释放错误 | block ledger、取消 trace | token admission、泄漏修复 |
| 量化后少数工具参数翻转 | 小 margin/outlier/校准缺口 | paired logits、case diff | 调粒度/保留敏感层/扩校准 |
| Prefix 命中但输出错误 | cache key 不完整 | model/Adapter/token key | 扩 key、清 cache、隔离版本 |
| Speculative 变慢 | 接受率低或 draft 开销高 | acceptance、draft/verify spans | 缩 draft、换模型或关闭 |
| Canary error 激增 | artifact/config/kernel 差异 | revision、effective config | 自动停止流量并回滚 |

### 7.2 排障顺序

`[通用工程]`

1. 冻结时间窗口、request IDs、模型/Adapter/config revision；
2. 按 queue、prefill、decode、stream、downstream 拆 trace；
3. 按长度、tenant、cache、worker、GPU 分桶，不只看全局平均；
4. 核对 admission reservation 与实际 token/KV 使用；
5. 对一个失败请求用相同 artifact/config 做离线重放；
6. 若涉及数值差异，比较 token、raw logits、processed logits 和 decoding state；
7. 先恢复 SLO/安全，再做根因分析；记录是否只是相关性而非因果隔离。

## 8. 概念比较速查

| 容易混淆的概念 | 正确边界 |
|---|---|
| TTFT vs E2E latency | 首 token 响应 vs 完整回答完成 |
| TPOT vs tokens/s | 单请求 token 间隔 vs 系统聚合吞吐 |
| Static batching vs continuous batching | 整批结束换批 vs 迭代边界动态增删序列 |
| Prefix cache vs response cache | 复用中间 KV 计算 vs 直接复用最终答案 |
| PagedAttention vs FlashAttention | KV 内存组织/访问抽象 vs attention 计算 IO 优化；可组合 |
| Quantized storage vs quantized compute | 权重低比特保存不代表算术全在该低比特执行 |
| Structured output vs semantic validity | schema/grammar 合法不代表工具选择、参数和授权正确 |
| Retry vs fallback | 同候选重试 vs 切换模型/策略；都需副作用语义 |
| Throughput vs goodput | 原始处理量 vs 满足质量和 SLO 的有效处理量 |

## 9. 高频面试题与分层答案

### Q1：为什么 LLM serving 要区分 prefill 和 decode？

**30 秒答案**

Prefill 一次处理整段 prompt 并创建 KV，通常矩阵较大；decode 每步只生成一个
token，却反复读权重和 KV。它们的瓶颈、指标和调度目标不同：TTFT 主要受排队和
prefill 影响，TPOT 主要受 decode 调度、KV 与带宽影响，所以要分别预算和监控。

**2 分钟答案**

补充 continuous batching：scheduler 每个迭代要在新 prefill 与在途 decode 之间
分配 token budget。长 prefill 若无 chunk 会阻塞流式 decode；过度偏向 decode 又
会饿死新请求。容量还受 KV Cache 约束，KV 随层数、token 数、KV heads 和 dtype
线性增长。因此线上优化是 TTFT、TPOT、throughput、fairness 和显存的多目标问题。

**深挖方向**

- 如何按 prompt/output bucket 设计 benchmark；
- chunked prefill 的收益与调度复杂度；
- GQA/MQA 如何改变 KV 容量；
- 为什么不同硬件上 compute/memory 判断必须 profile。

### Q2：你会怎样评估 4-bit weight-only 量化？

**30 秒答案**

先固定 reference、校准集和 frozen eval，说明粒度、group size、compute dtype 与
kernel；然后同时看任务质量、逐例和安全回归、显存、TTFT、TPOT、吞吐、加载时间。
只有目标硬件上的质量与性能双门禁都过，才有部署价值。

**2 分钟答案**

校准集要覆盖真实长度、模板、语言、工具 schema 和危险动作，且不能用 test 答案。
我会将量化 artifact 与数据、算法配置、base revision、kernel 路径绑定；对低 margin
bad case 比较 token/logits，检查敏感层是否保留高精度。还会做并发和长上下文压测，
因为理论 4-bit 权重大小不包含 scale、packing、workspace 和 KV，也不保证 kernel
加速。最后 canary，出现质量或 p99 回归自动停止流量并回滚。

**深挖方向**

- GPTQ 与 AWQ 使用校准信息的差异；
- per-channel/group-wise 的 metadata 与 kernel trade-off；
- 为什么 perplexity 相近仍可能工具调用失败；
- 量化后 structured output 和 safety case 如何做 gate。

### Q3：PagedAttention 和 continuous batching 分别解决什么？

**30 秒答案**

PagedAttention 主要解决动态 KV Cache 的分配、碎片和共享问题，把逻辑 token 映射
到物理 block；continuous batching 主要解决调度问题，在每个 decode 迭代动态加入
新请求、移除完成请求。前者提高内存利用，后者提高设备利用，它们常一起工作。

**2 分钟答案**

说明 page size、block table 和内部碎片，再说明 scheduler 按 scheduled tokens、KV
blocks、deadline、公平性分配预算。内存利用率提高不等于 p99 自动改善：若 admission
过松或长 prefill 抢占，仍会造成尾延迟。因此要把 block ledger、queue、iteration
和 TTFT/TPOT trace 关联起来。

**深挖方向**

- prefix sharing 的正确 cache key；
- cancellation 后 block 回收；
- page size benchmark；
- OOM 前主动拒绝和无界队列的差异。

### Q4：如何设计模型服务的过载保护？

**30 秒答案**

用 token/KV 成本而不是请求数做 admission，设置有界队列、deadline、tenant quota、
最大输入输出和取消传播；容量不足时明确 reject/retry-after 或降级。监控 queue time、
p99、reject reason 和 goodput，防止重试风暴。

**2 分钟答案**

入口先估 prompt 与最大输出，预留 KV block；scheduler 再按实际增长修正。不同优先级
独立预算，长 prompt 可 chunk，低优先流量可 shed。Fallback 必须满足同一 schema 和
安全合同，并限制 retry 次数。扩容信号优先用 queue tokens、deadline miss risk 和
goodput，而非单一 GPU utilization。所有拒绝都带可观测 reason，canary 和 rollback
不绕过 admission。

**深挖方向**

- 突发流量下 Little's Law 的局限；
- token reservation 估计偏差；
- load shedding 的公平性；
- 外部工具已执行时为何不能盲目 retry。

## 10. 本项目映射与证据边界

### `[本仓库已实现]` 可以怎么说

- 已有 1.5B 模型在单张 RTX 4090 Laptop GPU 上的离线 BF16/FP32 attached 推理与
  峰值显存证据；FP32 full eval 的一次注册运行峰值为 `6,267,895,296 bytes`。
- 已冻结 prompt、generation、compiler、模型/Adapter identity、raw outputs、
  compiled decisions、质量与安全指标，并完成同一记录环境的 clean-location replay。
- 已把 byte identity、remote hosted revision origin、offline artifact eligibility 和
  preferred offline candidate 分开做决策；这体现 artifact/eval gate discipline。
- 已观察并隔离 BF16/FP32 与 attached/merged 数值路径的部分差异，但没有把候选
  merged artifact 或模型发布到服务。

这些数字只来自 20-case 离线 eval 和已声明的单机路径。不能从一次 elapsed time
推导线上 QPS、p95/p99、multi-tenant capacity、stable speedup 或 cost。

### `[本仓库待实施]` 必须如实说明

- Serving gateway、vLLM 类服务引擎与在线 model routing；
- GPTQ/AWQ/其他量化基准与目标硬件 kernel 验证；
- continuous batching、prefix cache、speculative decoding、multi-LoRA；
- admission control、backpressure、结构化解码在线门禁；
- SLO、容量/成本实验、canary、rollback 和生产 observability。

面试表述示例：

> 我在当前项目完成的是离线模型、数值诊断、评测和 artifact evidence chain，
> serving 仍是 `[本仓库待实施]`。因此我可以完整讲出设计与验收方案，但不会把
> TTFT、TPOT、online throughput 或 vLLM 部署说成已有项目结果。

## 11. 自测与实践

### 11.1 口头自测

1. 不看文档写出 KV Cache 显存公式，并解释 GQA 为什么减少 KV；
2. 用一分钟区分 dynamic/static、weight-only 和 weight+activation；
3. 解释为什么 structured decoding 不能替代 policy/approval；
4. 给出 TTFT 上升但 TPOT 稳定的三种假设和所需 trace；
5. 解释为何 throughput 最高的配置不一定有最高 goodput；
6. 说明 hash、模型 revision、量化 config 和 kernel 为什么都要绑定到 artifact。

### 11.2 纸面容量练习

任选一个公开模型配置，记录 `L`、`H_kv`、`D_head`、weight bytes，并计算：

1. 2K、8K、32K token 单序列 KV payload；
2. 预留 10% runtime margin 后理论活跃序列上限；
3. 平均输入/输出与 p95 输入/输出下的差异；
4. 若 prefix cache 复用 1K token，节省的是何种工作和何种显存；
5. 哪些 allocator/kernel 开销没有进入公式。

### 11.3 最小工程实践

`[本仓库待实施]` 实践应先预注册 protocol，再运行：

1. 固定一个未量化 reference 和至少两个量化候选；
2. 冻结校准集与独立 eval，记录数据和配置 hash；
3. 在相同硬件扫描 prompt/output 长度和并发；
4. 记录 TTFT/TPOT/E2E 的 p50/p95/p99、input/output tokens/s、VRAM、错误；
5. 对每个质量变化生成逐例 diff，并单列安全/tool-schema gates；
6. 做突发、取消、长上下文和 OOM 前 admission 故障实验；
7. 只把门禁通过的候选送入 canary，保留一键 rollback 证据。

完成标准不是“服务启动了”，而是能回答：在什么负载、硬件、artifact、质量约束和
SLO 下，它为什么可用；失败时怎样拒绝、降级、回滚并保留可审计证据。
