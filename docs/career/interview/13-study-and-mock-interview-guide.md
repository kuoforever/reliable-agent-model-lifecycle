# 复习与模拟面试指南

> 默认读者已有 ML/DL 基础。本章给出使用方法和演练产物，不记录项目进度，也不
> 替代 `PROJECT_STATUS.md`。

## 1. 面试能力不是阅读量

同一个知识点需要经过五种转换：

```text
看懂
→ 闭卷讲懂
→ 白板推导
→ 写出最小实现
→ 在失败场景中做工程决策
```

只有“看懂”时，面试官一旦换一个 workload 或追问 trade-off，答案就会断。建议
每个主题保留四类临时练习输出：一页手写推导、一段可运行最小代码、一张系统图、
一次录音复述。它们是练习，不写入本仓库的 canonical tracker。

## 2. 六周完整路线

### 第 1 周：Transformer 与 generation

阅读第 01 章，并完成：

1. 从 `input_ids [B,T]` 开始，写出 embedding、Q/K/V、head reshape、attention、
   MLP、LM head 的所有 shape。
2. 手算一个 `T=3,d_k=2` 的 causal attention。
3. 写一个不依赖高级 attention API 的 single-head implementation，对照 PyTorch
   reference，检查 mask 与 softmax axis。
4. 写出无 cache 与 KV Cache decode 的伪代码，并估算一个给定模型的 cache memory。
5. 闭卷回答 greedy、temperature、top-k、top-p 与 structured decoding 的区别。

验收标准：十分钟白板讲完整 decoder block；能解释 prefill/decode 为什么性能特征
不同；能指出 tokenizer/model revision mismatch 的工程后果。

### 第 2 周：训练、数值与 PEFT

阅读第 02、03 章，并完成：

1. 手写 AMP train loop：zero grad、forward、scale loss、backward、unscale gradients、
   finite check/global-norm clip、optimizer/scaler step、scaler update；只有 optimizer
   真正更新后才推进 scheduler，最后按语义边界 checkpoint，并解释顺序错误的影响。
2. 计算一个 1.5B/7B 模型在 FP32/BF16 下 parameter、gradient、Adam states 的
   粗略显存，再加入 activation/KV 的独立项。
3. 给一个 linear layer 写 LoRA forward，核对 `A/B` shape、`α/r` 与参数量。
4. 比较 full FT、LoRA、QLoRA、SFT、DPO、distillation 的数据和资源条件。
5. 复述项目 BF16/FP32 diagnostic：每个 gate 只改变哪一个轴、证明到哪里。

验收标准：看到 OOM、NaN、loss divergence、resume drift 或 output mismatch，能够先
定义证据和控制变量，而不是随机修改 batch、dtype 和 seed。

### 第 3 周：数据、评测与 Agent

阅读第 04、05 章，并完成：

1. 给一个 Tool Router 数据集设计 schema、family manifest、dedup、PII、split、
   frozen eval 与 version contract。
2. 从 confusion matrix 手算 precision、recall、Macro/Micro F1；解释何时 exact match
   太严、field F1 又可能太宽。
3. 设计一个 preregistered experiment：只允许一个 primary variable，事先写明 gate、
   resource cap、run count、failure meaning。
4. 画出 `model proposal → schema → policy → approval → WAL → executor → verifier`
   控制流，并为 timeout 写 Unknown Outcome 状态转移。
5. 分析一个 prompt injection：哪些内容不可信、secret/authority 在哪一层隔离。

验收标准：能够解释 frozen eval 与 leakage audit 各自的能力边界；能够设计一次不会
因 retry 产生重复副作用的工具执行。

### 第 4 周：Multimodal、retrieval、verifier

阅读第 06 章，并完成：

1. 画 VLM 的 vision encoder/projector/LLM token flow，说明 resolution 和 visual
   token 数怎样影响 memory/latency。
2. 设计 screenshot + OCR + UIA fusion schema；列出 DPI、遮挡、窗口移动、 stale
   observation 的 failure modes。
3. 写 bi-encoder InfoNCE 伪代码，设计 hard-negative mining 和 false-negative audit。
4. 为两阶段 retrieval 选择 Recall@K、MRR/NDCG 与 end-to-end task metric。
5. 为 Verifier 画 calibration/threshold/abstention 曲线，并设计 state-based label。

验收标准：能说明 embedding、reranker 和 verifier 的输入/输出/成本差异；不把模型
self-report 当成任务成功标签。

### 第 5 周：Serving、分布式与 MLOps

阅读第 07–09 章，并完成：

1. 给定 layers、KV heads、head dim、context、concurrency 和 dtype，估算 KV memory。
2. 设计 benchmark matrix：prompt/output length、concurrency、quantization、warm/cold、
   p50/p95/p99 TTFT/TPOT/throughput/quality/safety。
3. 用同一 7B training workload 比较 DDP、FSDP/ZeRO、TP/PP 的 memory 与 collectives。
4. 从 profiler timeline 判断 compute、HBM、communication 或 CPU scheduling 瓶颈。
5. 画出 registry → offline gate → shadow → canary → rollback → badcase feedback。
6. 为 model service 定义 SLI/SLO、error budget、admission control 与 overload behavior。

验收标准：任何“更快/更省显存”结论都带 workload、hardware、precision 和 quality
gate；能说明普通 CI 为什么不证明 GPU model behavior。

### 第 6 周：Multi-Agent 与项目答辩

阅读第 10–12 章，并完成：

1. 为一个可并行研究任务画 single-agent baseline 与 multi-agent task graph。
2. 定义 identity、authority、typed handoff、lease、heartbeat、fencing、budget、
   cancellation 和 result dedup。
3. 分别演练六个项目故事的 30 秒、2 分钟与 10 分钟版本。
4. 从题库随机抽 20 题，限时回答；对每题按 correctness/depth/trade-off/evidence
   评分。
5. 完成一次 45 分钟 mock：基础 10 分钟、项目 15 分钟、系统设计 15 分钟、反问
   5 分钟。

验收标准：能主动说明本项目未实现的 Serving、分布式、Multimodal、RL 和 Multi-Agent
边界，同时仍给出可信的工程设计与验证方案。

## 3. 两周冲刺路线

时间紧时，不要平均阅读：

| 天 | 上午 | 下午/晚上 |
| ---:| --- | --- |
| 1 | 第 01 章核心公式 | attention + KV cache 白板 |
| 2 | 第 02 章训练 loop | precision/OOM/checkpoint 诊断 |
| 3 | 第 03 章 LoRA/QLoRA | alignment/distillation 选型 |
| 4 | 第 04 章数据治理 | metrics/preregistration |
| 5 | 第 05 章 Agent | safety/unknown outcome 系统图 |
| 6 | 第 06 章 | retrieval/verifier 练习 |
| 7 | 第 07 章 | KV/latency/capacity 计算 |
| 8 | 第 08 章 | parallelism/roofline 白板 |
| 9 | 第 09、10 章 | rollout 与 multi-agent trade-off |
| 10 | 项目故事 1–3 | 录音、删掉夸大表述 |
| 11 | 项目故事 4–6 | 数值与 provenance 深挖 |
| 12 | 题库 Q01–Q52 | 纠错与补弱项 |
| 13 | 题库 Q53–Q90 | 综合系统设计 |
| 14 | 两次 mock | 复盘，不再扩新知识 |

## 4. 四种必练形式

### 4.1 白板题

至少能不看资料完成：

- Attention、MHA/GQA 与 KV Cache shape/complexity；
- Causal LM loss 和 assistant-only loss mask；
- LoRA 参数量与 scaling；
- Adam memory 粗估；
- KV Cache memory 粗估；
- DDP/FSDP/TP/PP data/communication flow；
- Agent authority、WAL 和 Unknown Outcome 状态机；
- artifact evidence state machine。

白板回答先定义 symbols，再代数字。跳过变量定义会让公式看起来像背诵。

### 4.2 Coding 题

建议练习的最小实现：

1. masked self-attention 和 shape assertions；
2. top-k/top-p filtering；
3. LoRA linear wrapper 与 merge equivalence test；
4. assistant-only label masking；
5. exact/field F1 与 confusion matrix；
6. canonical JSON + SHA-256；
7. idempotent tool operation + WAL state machine；
8. latency percentile 和 token-throughput report。

评分不仅看 happy path，还看 empty input、padding、dtype/device、NaN、duplicate ID、
partial write、timeout/cancellation 和 deterministic test。

### 4.3 项目深挖

面试搭档从以下角度攻击你的结论：

- 如果换一个 split 或 seed 呢？
- 为什么这个 metric 能代表目标？
- 有没有只报 aggregate、隐藏 regression？
- control 是否同时改变两个变量？
- hash/CI/replay 到底证明什么？
- failure 是模型、compiler、Runtime 还是 artifact 层？
- 为什么这个结果能写进简历？你的个人贡献是什么？

合格回答不需要防御所有质疑，而要说明已有 evidence、剩余未知和最小 next gate。

### 4.4 系统设计

在开始画组件前，先问清：

- workload：模型大小、context、输入输出长度、QPS/concurrency；
- objective：quality、safety、latency、throughput、cost 哪些是硬约束；
- state：无状态请求、长会话、工具副作用、多租户；
- failure semantics：deadline、cancel、worker crash、partial effect；
- compliance：PII、retention、audit、approval；
- deployment：hardware、region、availability、rollout/rollback。

之后再画 data plane/control plane，不要一上来罗列 Kafka、Kubernetes 和 vector DB。

## 5. Mock interview 脚本

### Round 1：基础与推导，45 分钟

1. Attention shape 与 causal mask，8 分钟。
2. KV Cache memory 与 prefill/decode，8 分钟。
3. LoRA/QLoRA 数学和选型，8 分钟。
4. mixed precision 与 checkpoint，8 分钟。
5. data split 与 eval metrics，8 分钟。
6. 追问与总结，5 分钟。

### Round 2：项目深挖，45 分钟

1. 一分钟项目介绍。
2. 面试官任选一个故事，连续追问 15 分钟。
3. 给一个相反解释，要求设计区分实验。
4. 给一个负结果，要求决定 fix、rollback、defer 或 reject。
5. 要求指出简历 bullet 中每个数字的 source 和 limitation。

### Round 3：系统设计，60 分钟

题目：设计一个支持 structured tool call、multi-LoRA 和可靠副作用执行的企业 Agent
平台。

必须覆盖：

```text
requirements/non-goals
model/router/adapter serving
tool registry/schema/compiler
policy/approval/sandbox
WAL/idempotency/recovery
RAG/context/memory security
verifier/eval
capacity/admission control
observability/SLO
artifact lineage/rollout/rollback
```

最后强制回答：当 model output、compiler、policy 与 post-state verifier 相互冲突时，
谁是 authority，怎样保留 audit evidence。

## 6. 常见弱回答与修正

| 弱回答 | 问题 | 修正方向 |
| --- | --- | --- |
| “LoRA 就是少训一些参数” | 无公式和工程后果 | 写 `BA`、shape、memory、target、merge trade-off |
| “BF16 更快，FP32 更准” | 绝对化 | 绑定 hardware/operator/workload，用 quality gate 判断“准” |
| “用了 hash，所以可复现” | 混淆 evidence states | 区分 bytes、origin、environment、behavior、portable |
| “模型输出 JSON 就安全” | 把语法当权限 | schema、semantic、policy、approval、WAL、verifier 分层 |
| “准确率提高 5%” | 缺 baseline/sample/metric | 给绝对计数、eval identity、regression 和 CI/限制 |
| “多 Agent 提升效果” | 无 single-agent control | 同预算/任务/模型比较 quality、latency、cost、failure |
| “上 Kubernetes 就能扩容” | 忽略 GPU/冷启动/state | queue signal、KV、model load、drain、SLO、cost |
| “首个差异模块就是 root cause” | observation 当 causality | 说 registered boundary，设计 intervention/control |

## 7. 如何诚实回答“你没做过的部分”

推荐结构：

> 这部分在当前仓库是 planned，我没有把它写成完成经验。原理上它解决……；如果在
> 当前系统落地，我会先锁定……，采用……，用……指标与 failure test 验证；最大的
> trade-off 是……。我已完成的相邻证据是……，两者的边界是……。

这比假装做过更强，因为它同时展示知识、工程判断和 evidence discipline。

例：

> 当前项目没有部署 vLLM。若进入 Serving gate，我会先保持 exact FP32 attached
> package 和 compiler 不变，固定 prompt/output length 与 concurrency matrix，先做
> semantic/safety equivalence，再测 TTFT、TPOT、throughput、KV memory、overload、
> cold start 和 rollback。当前 clean-location replay 严格证明的只是同一记录环境、
> 固定 20-case 下 raw `20/20` 与 compiled `20/20` exact replay，不能当作
> cross-machine portability 或 serving readiness。

## 8. 面试前最后一天

- 不再扩展新主题，只复习第 11 章的三个主故事与三个备用故事。
- 每个数字都能说出 denominator、baseline、eval identity 和 source。
- 复写 Attention、LoRA、KV memory、parallelism 四张白板。
- 从第 12 章随机回答 15 题，优先修复概念错误，不追求漂亮措辞。
- 准备两个 negative results、一个系统 trade-off、一个主动承认的未实现边界。
- 确认简历只保留本人真正负责并能解释的 evidence。
