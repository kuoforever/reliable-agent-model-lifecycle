# Reliable Agent Model Lifecycle 面试手册

> 面向已经学过 Machine Learning / Deep Learning、希望准备 LLM post-training、
> Agent、evaluation、AI infrastructure 与 ML systems 面试的读者。
>
> 本目录是知识与面试材料，不是项目进度 tracker。项目完成状态与唯一 active
> objective 只看 [PROJECT_STATUS.md](../../../PROJECT_STATUS.md)。

## 1. 这套资料解决什么问题

很多面试准备只停在两层：背定义，或者背项目结果。真正有区分度的回答需要同时
打通四层：

1. **原理**：能写公式、说明 tensor shape、推导数据流，而不是只背术语。
2. **应用**：知道问题适合哪种方法，也知道什么时候不该用它。
3. **工程**：能把方法落到数据、训练、评测、Serving、可靠性与故障诊断。
4. **证据**：能说清楚自己做了什么、结果证明什么，以及没有证明什么。

这套手册因此不按论文目录组织，而按一次真实模型生命周期组织：

```text
tokens / Transformer / generation
        ↓
training numerics / checkpoint / profiling
        ↓
SFT / LoRA / QLoRA / preference / distillation
        ↓
data governance / frozen evaluation / experiment design
        ↓
Tool Use / Agent / Runtime safety / multimodal / retrieval / verifier
        ↓
quantization / serving / distributed systems / MLOps / observability
        ↓
multi-agent coordination
        ↓
project evidence → interview story → defensible claim
```

## 2. 证据标签

正文使用四种标签，阅读时必须区分：

| 标签 | 含义 | 面试中可以怎样说 |
| --- | --- | --- |
| `[原理]` | 稳定的模型、算法或系统原理 | “原理上……” |
| `[通用工程]` | 行业常见工程模式或建议，并非本仓库完成事实 | “工程上通常……” |
| `[本仓库已实现]` | 有代码、测试、冻结指标或 artifact 支持 | 核对个人贡献后说“项目中……” |
| `[本仓库待实施]` | 路线图知识，尚不能作为经验 | “下一步设计会……”，不能说“我做过……” |

仓库证据证明项目行为，不自动证明个人作者身份。投递或面试前，还要确认你本人
负责的范围。以下状态不能互相替代：

```text
byte identity
≠ hosted origin binding
≠ same-environment replay
≠ cross-machine portability
≠ artifact promotion
≠ serving readiness
≠ Runtime integration
≠ production impact
```

## 3. 全套章节

| 章 | 主题 | 你应该能回答的核心问题 |
| --- | --- | --- |
| 00 | [工程基础与 GPU 工作台](00-engineering-foundations.md) | Python/PyTorch、Git、OS、CUDA、测试与可复现性怎样共同支撑可信实验？ |
| 01 | [LLM 原理与生成](01-llm-foundations-and-generation.md) | 一个 token 如何经过 Decoder 得到下一个 token？KV Cache 为什么改变复杂度和显存？ |
| 02 | [训练、PyTorch 与数值工程](02-training-pytorch-and-numerics.md) | 训练 loop 如何正确、可恢复、可复现？BF16/FP32 漂移怎样隔离？ |
| 03 | [后训练、PEFT 与对齐](03-post-training-peft-and-alignment.md) | SFT、LoRA、QLoRA、distillation、DPO/GRPO 各解决什么问题？ |
| 04 | [数据、评测与实验设计](04-data-evaluation-and-experimentation.md) | 怎样防 leakage，冻结 eval，设计能支持结论的指标与对照？ |
| 05 | [Tool Use、Agent 与安全 Runtime](05-tool-use-agents-and-safety.md) | 模型建议、结构化决策和有权限的副作用为什么必须分层？ |
| 06 | [多模态、检索与 Verifier](06-multimodal-retrieval-and-verifiers.md) | VLM、Embedding、Reranker、Verifier 如何进入 Agent 闭环？ |
| 07 | [量化、Serving 与推理系统](07-serving-quantization-and-inference.md) | TTFT、TPOT、KV Cache、batching、admission control 如何共同决定服务表现？ |
| 08 | [分布式训练与性能](08-distributed-training-and-performance.md) | DDP/FSDP/ZeRO/TP/PP 分别切什么，瓶颈怎样测而不是猜？ |
| 09 | [MLOps、可靠性与可观测性](09-mlops-reliability-and-observability.md) | 一个模型 artifact 怎样获得 lineage、门禁、回滚和运行证据？ |
| 10 | [Multi-Agent Systems](10-multi-agent-systems.md) | 多 Agent 何时值得使用，怎样处理 authority、共享状态和 worker failure？ |
| 11 | [六个项目面试故事](11-project-interview-stories.md) | 如何用真实证据讲问题、实验、负结果、边界和下一步？ |
| 12 | [分层题库与答案标尺](12-question-bank.md) | 面试官从基础、应用到系统深挖时，合格答案包含什么？ |
| 13 | [复习与模拟面试方法](13-study-and-mock-interview-guide.md) | 怎样把知识转成白板、代码、系统设计和项目答辩能力？ |

## 4. 推荐阅读顺序

### 路线 A：LLM Post-training / Applied ML

```text
00 → 01 → 02 → 03 → 04 → 05 → 11 → 12
```

重点是 causal LM、训练稳定性、data/eval governance、LoRA/QLoRA、alignment
以及 bad-case-driven iteration。Serving 与分布式至少读到能解释边界和成本。

### 路线 B：Agent / Tool-use / Evaluation

```text
00 → 04 → 05 → 06 → 09 → 01 → 03 → 11 → 12
```

重点是 typed decision contract、structured output、model/Runtime authority、
failure taxonomy、安全 gate、Verifier 与 end-to-end task success。

### 路线 C：AI Infra / ML Systems

```text
00 → 02 → 07 → 08 → 09 → 05 → 11 → 12
```

重点是 memory/compute/communication、latency decomposition、batching、
admission control、artifact lineage、observability、failure recovery 和
correctness-first optimization。

### 路线 D：全栈 LLM Engineer

按 00–13 顺序读。每读完一章，用三种形式复述：

- 30 秒：定义、价值、一个关键 trade-off；
- 2 分钟：数据流、工程选择、指标、故障；
- 10 分钟：白板推导或系统设计，再连接一个真实项目证据。

## 5. 每类面试题的答题骨架

### 原理题

```text
定义 → 输入/输出与 shape → 公式 → 计算/内存复杂度
→ 为什么有效 → 边界条件 → 与相邻方法比较
```

例：回答 Attention 时，不止说“计算相关性”，还要交代 `QK^T / sqrt(d_k)`、
causal mask、softmax、与 `V` 的乘法、head 拆分以及长序列的时间和显存成本。

### 应用选型题

```text
业务目标 → 约束 → 候选方案 → 决策维度
→ 选择 → 放弃项 → 指标与回滚条件
```

例：问 LoRA 还是 full fine-tuning，至少比较数据规模、显存、训练目标偏移、
多租户 adapter、部署形态、可回滚性，以及是否需要改变全部权重。

### 工程诊断题

```text
先定义失败 → 收集可观测证据 → 缩小变量
→ 构造最小对照 → 复现 → 定位首个可观察边界
→ 修复候选 → 回归与负结果 → 剩余未知
```

“首个观察到差异的模块”不等于“唯一 root cause”；“一次跑通”也不等于稳定、
跨机器或生产可用。

### 项目题

统一使用现有 [Interview translation](../teaching/INTERVIEW_TRANSLATION.md)：

```text
problem → locked variables → hypothesis → experiment
→ metric/gate → negative result → limitation → next falsifiable gate
```

不要用流水账回答“先写脚本、再训练、再看结果”。面试官关心的是你为何这样
定义问题、控制了什么、证据支持多强的结论。

### 系统设计题

```text
requirements / non-goals
→ workload and SLO
→ data/control plane
→ state and ownership
→ capacity model
→ failure semantics and security
→ observability
→ rollout/rollback
→ bottleneck and trade-off
```

对 Agent 系统还必须明确：谁能提出 action，谁能授权，谁执行，谁验证结果，
unknown outcome 如何恢复，以及怎样避免重复副作用。

## 6. 从“知道”到“面试可用”的完成标准

一个主题达到面试可用，不是“看过”，而是能独立完成以下动作：

1. 不看资料写出核心公式或数据流，并定义变量。
2. 给一个 workload，选方案并说出至少两个 trade-off。
3. 写出最小伪代码或关键 configuration，不依赖背 API 名字。
4. 给一个失败现象，列出观测、对照、定位与验证顺序。
5. 选择正确 metric，并说明 aggregate metric 会掩盖什么。
6. 连接到一个真实证据；若没有做过，明确说是通用知识或设计方案。
7. 说出结论的 claim boundary 和下一项可证伪实验。

## 7. 本仓库可以支撑的面试证据

当前最强证据集中在六条线：

1. Tool Router typed decision contract 与 model/Runtime authority 分层。
2. task-family-disjoint 数据、frozen eval、leakage/distribution gate。
3. Base → LoRA v1 → safety-repair data → LoRA v2 的闭环。
4. raw output 与 decision compiler 分层，以及 safety/false-refusal 权衡。
5. BF16/FP32、attached/merged 的数值漂移隔离与负结果。
6. manifest、origin binding、same-environment replay 与 portability 边界。

精确故事见[第 11 章](11-project-interview-stories.md)，可用于简历的短版本见
[resume evidence index](../resume/)。本仓库目前没有完成 Serving、production
deployment、large-scale distributed training、Multimodal GUI model、preference/RL
或 Multi-Agent Lab；这些章节用于面试知识和后续工程设计。

## 8. 使用原则

- 先理解，再背术语；先定义 claim，再引用数字。
- 公式必须和 tensor/data flow 对得上。
- 性能结论必须带 workload、hardware、precision、batch/concurrency 和 percentile。
- 模型指标必须带 dataset/eval identity、baseline、compiler 与 safety condition。
- hash 只能回答对应字节身份问题，不能自动回答作者、来源、执行者或可移植性。
- CI 的 CPU/offline tests 不能替代 GPU model behavior evidence。
- negative result 是诊断信息，不是需要隐藏的失败。
- 若被问到未实现能力，先明确经验边界，再给出工程设计和验证计划。
