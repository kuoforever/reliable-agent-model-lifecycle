# 分层面试题库与答案标尺

> 题库用于闭卷复述、白板推导和 mock interview，不是另一个学习进度 tracker。
> 完整原理与工程解释见各主题章节。

## 1. 使用方式

每道题分三级：

- `L1`：一分钟内定义正确，变量和边界清楚；
- `L2`：能比较方案、写公式或 data flow，并给出工程选择；
- `L3`：能处理故障、性能、安全、实验设计和 claim boundary。

建议让对方随机抽题，不要顺序背诵。回答后用四项各 0–2 分自评：

| 维度 | 0 | 1 | 2 |
| --- | --- | --- | --- |
| Correctness | 核心错误 | 大致正确 | 定义、公式、边界准确 |
| Depth | 只有名词 | 有原理或应用 | 原理、应用、工程贯通 |
| Trade-off | 无 | 说出一个 | 能基于 workload 选型 |
| Evidence | 夸大或无证据 | 有例子 | 指标、限制、下一 gate 完整 |

---

## 2. LLM 原理与生成（12 题）

### Q01 `[L1]` Tokenizer 为什么不是无关紧要的预处理？

答案标尺：说明 tokenization 决定序列长度、词表、embedding/LM head identity、
多语言和数字/代码切分、cost 与 truncation；模型与 tokenizer revision 必须绑定。

### Q02 `[L2]` 写出 scaled dot-product attention，并标注 shape。

答案标尺：`Q=XW_Q, K=XW_K, V=XW_V`；单 head `Q,K∈R^{T×d_k}`、
`V∈R^{T×d_v}`；`softmax(QK^T/sqrt(d_k) + M)V`；解释 scale 和 additive causal
mask，不能把有限 mask 项也除以 `sqrt(d_k)`。

### Q03 `[L2]` MHA、MQA、GQA 的差别是什么？

答案标尺：query head 数与共享 K/V head 数；质量、KV Cache memory、bandwidth、
kernel/layout trade-off；不是简单说“GQA 更快”。

### Q04 `[L2]` RoPE 怎样编码相对位置信息？

答案标尺：对 Q/K 成对维度施加位置相关 rotation；dot product 中出现相对位置；
说明 extrapolation 仍依赖训练长度、frequency scaling 和模型设计。

### Q05 `[L1]` RMSNorm 与 LayerNorm 有什么不同？

答案标尺：RMSNorm 不减均值，按 root mean square 缩放后乘 weight；参数/计算与
数值特征；不能笼统说一定更稳定。

### Q06 `[L2]` SwiGLU/MLP 为什么常比普通 ReLU FFN 强？

答案标尺：门控分支 `silu(XW_g) ⊙ (XW_u)` 再 down projection；参数量、hidden
dimension 与计算成本；表达能力是经验结论，不能只背名字。

### Q07 `[L2]` Causal LM loss 为什么通常要 shift labels？

答案标尺：位置 `t` 的 logits 预测 token `t+1`；teacher forcing、cross-entropy、
padding/assistant-only loss mask；off-by-one 和 prompt token 误训风险。

### Q08 `[L2]` temperature、top-k、top-p 分别怎样改变分布？

答案标尺：`softmax(z/τ)`；top-k 固定候选数，top-p 取最小累计概率集合；greedy
是 argmax；顺序、renormalization、reproducibility 与 task type。

### Q09 `[L2]` KV Cache 节省了什么，又付出了什么？

答案标尺：decode 不重算历史 K/V，降低每步 attention projection/历史计算；
memory 约随 layers × tokens × KV heads × head dim × bytes 增长；增加 bandwidth、
fragmentation 和 serving capacity 压力。

### Q10 `[L2]` Prefill 与 Decode 为什么是两种不同 workload？

答案标尺：prefill 处理整段 prompt、矩阵更大、较 compute-bound；decode 每步一个
token、读取大权重/KV、常 memory-bandwidth/launch-bound；优化与 batching 不同。

### Q11 `[L3]` 两次 greedy generation 为什么仍可能不同？

答案标尺：model/config/tokenizer/revision、dtype、execution form、kernel、TF32/
autocast、device、library、cache、并发/未初始化状态；先固定输入与环境，再定位首个
raw-logit boundary。

### Q12 `[L3]` JSON mode 是否等于语义正确和工具安全？

答案标尺：语法约束、schema/semantic invariants、tool availability、authorization、
side-effect policy 是独立层；structured decoding 不能替代 deterministic Runtime。

---

## 3. 训练、数值与后训练（14 题）

### Q13 `[L1]` AdamW 为什么把 weight decay 与 gradient update 解耦？

答案标尺：区别 L2 regularization 在 adaptive optimizer 中的缩放；参数更新中单独
衰减；bias/norm 参数常单独 group，但要依据实验而非习惯。

### Q14 `[L2]` warmup 解决什么问题？

答案标尺：训练早期 optimizer moments/activation 尚不稳定，大 LR 易发散；说明
step/ratio、scheduler 和 total steps 耦合，warmup 不是万能修复。

### Q15 `[L2]` gradient accumulation 是否等同于更大 batch？

答案标尺：理想梯度平均近似相同；但 BatchNorm、dropout/RNG、optimizer step
frequency、scheduler、gradient clipping、loss normalization 和 distributed sync
会造成差异。

### Q16 `[L2]` activation checkpointing 节省什么、增加什么？

答案标尺：不保存部分 forward activations，backward recompute；memory 换 compute；
RNG/dropout 与 graph partition 的正确性、wall time、communication overlap。

### Q17 `[L2]` BF16 与 FP16 如何选择？

答案标尺：BF16 exponent 接近 FP32、mantissa 更少；FP16 mantissa 更多、range 小，
常需 loss scaling；结合 hardware、operator support、training/inference，而非“一定”。

### Q18 `[L3]` mixed precision 中哪些状态常保留 FP32？

答案标尺：master weights/optimizer moments/reductions 或敏感 ops 的常见策略；实际
由 framework/config 决定，必须 audit，而不是凭模型 dtype 推断所有 tensor dtype。

### Q19 `[L3]` 怎样做可恢复 checkpoint？

答案标尺：model/adapter、optimizer、scheduler、scaler、global step/epoch、sampler、
Python/NumPy/PyTorch CPU/CUDA RNG、config/data digest；atomic write、resume test。

### Q20 `[L3]` OOM 时你的排查和处理顺序？

答案标尺：先测 peak 与 allocator，区分 parameter/optimizer/activation/KV；减少
microbatch/sequence、accumulate、checkpoint、precision、offload/shard；避免只调用
`empty_cache` 掩盖 leak，需验证 throughput/quality。

### Q21 `[L2]` LoRA 的公式、rank 与 alpha 分别是什么？

答案标尺：`W' = W + (α/r)BA`，`B∈R^{d_out×r}`、`A∈R^{r×d_in}`；rank 控制
capacity/cost，alpha 控制 update scale；target modules 与 task 更关键，非单调。

### Q22 `[L2]` LoRA 和 QLoRA 的核心区别？

答案标尺：QLoRA 以 4-bit 形式存储 frozen Base，forward 时按 block 反量化到
BF16/FP16 compute dtype，再训练较高精度 adapter；NF4 与 double quantization 是
核心内存设计，paged optimizer 是常见配套优化而非定义本身；它节省 Base memory，
但不是“全程 4-bit arithmetic”，并有 kernel/quality/merge/serving trade-off。

### Q23 `[L3]` attached Adapter 与 merged model 为什么可能不等价？

答案标尺：factorized `xW + x(BA)` 与 materialized `x(W+BA)` 的 operation order、
rounding/dtype/kernel 不同；需同 dtype/form 对照和 behavioral equivalence gate。

### Q24 `[L2]` CPT、SFT、DPO 各改变什么？

答案标尺：CPT 用 domain tokens 延续 next-token objective；SFT 学示范条件分布；
DPO 用 preference pairs 相对 reference 优化；数据、遗忘、安全和评测目标不同。

### Q25 `[L2]` sequence/logits/feature distillation 怎么选？

答案标尺：sequence 只需 teacher outputs、易工程化但丢暗知识；logits 用完整分布和
temperature、存储昂贵；feature 要对齐中间表示/架构，耦合最强。

### Q26 `[L3]` DPO、KTO、ORPO、GRPO 的选择依据？

答案标尺：preference pair/单样本 desirability/verifiable reward、reference model、
on-policy rollout、group relative advantage、compute 和 reward hacking；先说明数据
与目标，不能用“新方法更好”作答案。

---

## 4. 数据、评测与实验（12 题）

### Q27 `[L1]` 数据 pipeline 最少要记录哪些 lineage？

答案标尺：source/license/consent、snapshot/revision、schema、transform code/config、
filter/dedup/redaction、split manifest、counts/distribution、digest、known bias。

### Q28 `[L2]` exact dedup 与 near dedup 各怎么做？

答案标尺：canonical bytes/hash；MinHash/LSH、n-gram/Jaccard、embedding 等近似方法；
阈值、false positive/negative、跨 split 优先、保留 provenance。

### Q29 `[L3]` PII redaction 怎样验证？

答案标尺：规则+NER/分类器、precision/recall、人工抽样、quarantine、不可逆处理、
delete/retention、false negative 风险；“跑了 regex”不是完整答案。

### Q30 `[L2]` packing 提高什么效率，最容易引入什么 bug？

答案标尺：减少 padding、提高 token utilization；需要 attention/loss boundary，防止
跨样本 attention 或把 prompt/padding 计入 loss；记录 packed/unpacked token stats。

### Q31 `[L2]` 为什么 task-family split 常优于 random split？

答案标尺：模板/生成机制跨 row 泄漏；group-level generalization；family definition
仍可能错误，需要 duplicate/semantic audit 和外部 test。

### Q32 `[L3]` frozen eval 能防什么，不能防什么？

答案标尺：防静默换题与事后选择；不能保证 label quality、coverage、无污染、统计
功效；反复人工查看 bad cases 仍会形成 adaptive overfitting。

### Q33 `[L2]` exact match、field F1 与 semantic validity 为什么要一起看？

答案标尺：exact match 严格；field F1 给部分 credit；semantic validity 检查 contract；
都可能掩盖 safety/class imbalance，需要 per-category/per-case gate。

### Q34 `[L2]` Macro F1 与 Micro F1 的区别？

答案标尺：Macro 对每类等权、关注少数类；Micro 聚合 TP/FP/FN、受大类主导；类
分布、zero-support handling 和 confusion matrix。

### Q35 `[L3]` 20 条 eval 上提高 1 条应怎样表述？

答案标尺：绝对提升 5 percentage points 与 exact case-level delta；不能称统计稳健
generalization；报告 regression、CI/重复/扩充计划和 frozen identity。

### Q36 `[L3]` preregistration 要锁什么？

答案标尺：hypothesis、candidate、inputs/digests、controlled variable、run count、
metrics、thresholds、exclusions、resource caps、failure classification、next action；
必须 outcome-neutral 且在结果前固化。

### Q37 `[L3]` ablation 和 control 有什么差别？

答案标尺：ablation 去掉/替换组件估计贡献；control 固定其他变量建立对照；二者都
要求明确 counterfactual，多个轴一起变不能做因果归因。

### Q38 `[L3]` artifact hash 能证明什么？

答案标尺：对指定 hash algorithm 与 bytes 的 identity；不能证明语义正确、作者、
来源、运行次数、运行环境、行为、portable 或 production readiness。

---

## 5. Agent、安全、检索与 Verifier（14 题）

### Q39 `[L1]` Router、Planner、Executor 的责任边界？

答案标尺：Router 选能力/模型，Planner 分解任务，Executor 驱动有副作用 action；
生产中 authority、policy 与 state 不应由模型自由文本隐式拥有。

### Q40 `[L2]` Function calling 与 MCP 是同一层吗？

答案标尺：function/tool calling 是模型输出工具调用的接口模式；MCP 是 context/tool/
resource 交互协议生态；都不自动提供权限、sandbox、idempotency 或业务事务语义。

### Q41 `[L3]` 工具调用如何避免重复副作用？

答案标尺：stable operation/idempotency key、WAL before effect、attempt/result state、
dedup store、reconciliation；timeout 后标 Unknown Outcome，不盲目 retry。

### Q42 `[L3]` Unknown Outcome 与 ordinary failure 有何不同？

答案标尺：failure 已知未生效或已失败；unknown 无法确定 side effect 是否发生；需
query/reconcile/人工介入，retry policy 必须考虑操作幂等性。

### Q43 `[L2]` Prompt Injection 为什么不能只靠 system prompt？

答案标尺：不可信内容进入模型上下文；模型无法成为完美 security monitor；使用
data/instruction separation、least privilege、allowlist、approval、sandbox、output
validation、secret isolation 和 audit。

### Q44 `[L2]` Context、Memory、RAG 的区别？

答案标尺：context 是本次模型可见 token；memory 是跨时段选择/存储机制；RAG 从
外部 corpus 检索证据注入 context；分别有生命周期、权限、freshness 和 poisoning。

### Q45 `[L3]` Agent eval 为什么不能只看最终 success？

答案标尺：成功路径可能包含未授权 action、重复副作用、过量 tool calls 或不可恢复
state；同时测 task success、policy violation、side effects、cost、latency、recovery、
human intervention 和 trace completeness。

### Q46 `[L2]` Lane A 和 Lane B 为什么分开？

答案标尺：Lane A 只有 redacted reliability facts，不含原始任务/模型文本/tool result/
screenshot/memory，适合 reliability/verifier；Lane B 是默认关闭、逐次 consent、可见
capture、redaction/retention/delete 的 rich trajectory，才可能用于 multimodal behavior。

### Q47 `[L2]` Bi-encoder 与 Cross-encoder 怎样组合？

答案标尺：bi-encoder 独立编码、支持 ANN 大规模 recall；cross-encoder 联合编码，
质量高但 O(candidates) expensive；retrieve top-K 再 rerank top-N。

### Q48 `[L2]` InfoNCE 与 hard negatives 的作用？

答案标尺：拉近 positive、推远 batch/explicit negatives；temperature、false negative、
in-batch bias；hard negatives 增加边界学习但错误标注会伤害模型。

### Q49 `[L2]` Recall@K、MRR、NDCG 分别关注什么？

答案标尺：是否召回、首个 relevant 的倒数排名、带 graded relevance 的位置折扣；
还需 end-to-end task metric，离线检索提升未必改善 Agent。

### Q50 `[L2]` Outcome Verifier 与 Process Verifier 的区别？

答案标尺：终态结果 vs 中间步骤；label cost、credit assignment、reward hacking、
错误过程得到正确答案；对 Agent 应优先使用可观察 state，不信模型 self-report。

### Q51 `[L3]` Verifier threshold 怎样选？

答案标尺：calibration set、cost-sensitive ROC/PR、precision/recall、coverage-risk、
abstention、distribution shift；阈值和 model version 一起冻结，线上监控/回滚。

### Q52 `[L3]` GUI Agent 的 grounding 应怎样评测？

答案标尺：element/bbox accuracy、click-point containment、action/argument exactness、
state change verification、OCR/UIA disagreement、resolution/DPI/window shift、safety
policy；不能只用 model-reported success。

---

## 6. Serving、分布式与性能（14 题）

### Q53 `[L1]` TTFT、TPOT、tokens/s 各表示什么？

答案标尺：first-token latency、inter-token latency、吞吐；同时报告 queue/network/
tokenization、p50/p95/p99、prompt/output length、concurrency、hardware 和 precision。

### Q54 `[L2]` Continuous batching 为什么有效？

答案标尺：不同 request 在 token step 级动态加入/退出，提高 GPU utilization；带来
scheduler、fairness、KV memory、tail latency 和 cancellation complexity。

### Q55 `[L2]` PagedAttention 解决什么问题？

答案标尺：把逻辑连续 KV 映射到非连续固定块，减少 fragmentation、支持动态共享/
调度；metadata/indirection 与 block size trade-off，概念不等于某版本 API。

### Q56 `[L3]` 估算 KV Cache memory。

答案标尺：近似 `2 × layers × tokens × kv_heads × head_dim × bytes × sequences`；
2 是 K/V；说明 GQA、block overhead、beam/speculation 和 allocator reserve。

### Q57 `[L2]` Weight-only quantization 与 activation quantization 区别？

答案标尺：storage/bandwidth vs operator input/output；calibration、outlier、dequant
kernel、hardware support、quality/latency；模型变小不保证更快。

### Q58 `[L2]` GPTQ 与 AWQ 的思想差别？

答案标尺：GPTQ 近似二阶、逐层重构 quantization error；AWQ 用 activation-aware
scaling 保护 salient weights；说明 calibration dependence 与 kernel compatibility。

### Q59 `[L3]` 怎样做量化 benchmark？

答案标尺：同 model/task/prompts/generation；quality/per-case/safety、TTFT/TPOT/
throughput、peak/steady memory、load time、artifact size、concurrency、warm/cold；
预设 non-inferiority gate。

### Q60 `[L3]` Admission control 和 backpressure 的区别？

答案标尺：入口是否接纳 vs 上游降低速率/等待；依据 token budget/KV capacity/SLO，
排队、429/retry-after、priority、deadline、cancellation、load shedding。

### Q61 `[L2]` DDP 每张卡保存什么？

答案标尺：完整 parameters/gradients/optimizer states（典型情形），data shard 不同；
backward all-reduce gradients；通信可与 backward overlap，memory 不随 world size 降低。

### Q62 `[L2]` FSDP 与 ZeRO-1/2/3 怎样比较？

答案标尺：分别 shard optimizer、gradient、parameter 的阶段；FSDP module wrapping、
all-gather/reduce-scatter；memory、通信、CPU offload、checkpoint complexity。

### Q63 `[L2]` TP 与 PP 分别切什么？

答案标尺：TP 切单层 tensor/matmul、每层 collectives 多；PP 切 layers/stages、产生
bubble 和 activation transfer；结合 node topology、model size、batch/microbatch。

### Q64 `[L3]` 怎样判断训练是 compute-bound、memory-bound 还是 communication-bound？

答案标尺：profiler timeline、SM/TC utilization、HBM bandwidth、kernel occupancy、
collective overlap、step decomposition；roofline 用 arithmetic intensity 与硬件 ceilings，
不要凭 GPU utilization 单值猜。

### Q65 `[L3]` 写 Triton/kernel 优化前要先做什么？

答案标尺：锁 correctness oracle/tolerance/dtypes/shapes、profile 证明热点、建立 eager/
compiled baseline；之后 benchmark warmup/repeat/distribution，并做 numerical/backward/
edge-shape regression；无热点证据不优化。

### Q66 `[L3]` 分布式训练 checkpoint 怎样避免 world-size coupling？

答案标尺：明确 sharded/full/state-dict format、metadata、atomic completion marker、
optimizer/scheduler/RNG/sampler；支持 reshard 或固定 world size，实际做 kill/restart
和 partial-write tests。

---

## 7. MLOps、可靠性与 Multi-Agent（12 题）

### Q67 `[L2]` Data registry、Model registry 与 artifact store 有何区别？

答案标尺：logical version/metadata/lineage/approval vs immutable bytes storage；一个
model candidate identity 还要绑定 base/tokenizer/adapter/compiler/config/eval。

### Q68 `[L3]` CI、CD、CT 在模型生命周期中分别测什么？

答案标尺：code/schema/unit/offline determinism；artifact promotion/deploy；受控 retrain；
GPU behavior、data approval 和 production rollout 需独立 gate，不能由普通 CI 替代。

### Q69 `[L2]` Model Card 最少应包含什么？

答案标尺：identity/base/license、task/data、training/config、eval/safety、intended/
out-of-scope use、resource/precision、limitations/bias、artifact hashes、promotion/rollback。

### Q70 `[L3]` 一次模型 rollout 怎样设计？

答案标尺：offline gate→shadow→canary→staged traffic；quality/safety/SLO guardrail、
versioned route、automatic/manual rollback、state/schema compatibility、badcase capture。

### Q71 `[L2]` Trace、Metric、Log 分别擅长什么？

答案标尺：请求/Agent step causal path；聚合 trend/SLO；离散事件/debug detail；统一
trace/task/model/dataset/tool identifiers，PII/redaction 与 cardinality 控制。

### Q72 `[L3]` 怎样定义 LLM service 的 SLO 和 error budget？

答案标尺：availability 与 correctness/safety、TTFT/TPOT percentiles、deadline/stream
completion；按 workload 分层；error budget 驱动 rollout pace，不能只看 HTTP 200。

### Q73 `[L3]` Kubernetes 自动扩缩 GPU Serving 有哪些陷阱？

答案标尺：冷启动/model download、GPU type/topology、KV state、queue signal、KEDA
lag、bin packing、preemption、PDB、drain/cancellation、minimum warm replicas 和 cost。

### Q74 `[L2]` WAL 与 checkpoint 的区别？

答案标尺：WAL 在 side effect 前记录 intent/transition，支持 crash recovery/reconcile；
checkpoint 保存较完整可恢复 state；二者的 durability、frequency、replay semantics。

### Q75 `[L2]` Multi-Agent 相比 single-agent 多了什么必要状态？

答案标尺：identity/role/capability/authority、typed task/result/artifact、ownership/
handoff、shared durable state、lease/heartbeat、budget/cancel、conflict/reviewer decision。

### Q76 `[L3]` 什么时候不该用 Multi-Agent？

答案标尺：任务不可并行、协调成本高、共享状态不清、验证困难、单 Agent 已满足 SLO；
必须有 single-agent control，比较 quality/latency/cost/failure surface。

### Q77 `[L3]` Coordinator 挂掉怎么办？

答案标尺：durable task graph、leader lease/epoch fencing、idempotent assignment、worker
heartbeats、requeue/reconcile、result dedup；避免 split brain 和重复副作用。

### Q78 `[L3]` Reviewer Agent 是否能成为最终安全 authority？

答案标尺：模型 reviewer 仍会错且受 injection；它可提供 score/evidence，最终 policy、
approval、schema 和 side-effect authority 应 deterministic/human-controlled；评测
reviewer calibration 与 correlated failure。

---

## 8. 项目答辩（12 题）

### Q79 `[L1]` 用一分钟介绍这个项目。

答案标尺：一个 flagship lifecycle；当前实现到 text Tool Router、data/SFT/eval、
offline artifact eligibility 与 preferred-candidate decision；cross-machine portable
qualification 仍等待独立合格主机。Runtime authority 分仓；主动排除 serving、
multimodal、production 和 Runtime integration 的完成性声明。

### Q80 `[L2]` 为什么 deterministic baseline tool accuracy 1.0，仍要训练模型？

答案标尺：它只在窄规则/状态上选 tool，argument 指标为零，不代表开放语言理解或
generalization；baseline 是 sanity/control，不是目标模型。

### Q81 `[L2]` LoRA v2 最成功和最失败的结果分别是什么？

答案标尺：tool `0.95`、dangerous candidates `0`；argument `0.20`、semantic `0.85`、
3 false refusals/conflicts、merge drift；narrow safety pass ≠ Runtime eligible。

### Q82 `[L3]` Decision compiler 是否造成 eval hacking？

答案标尺：规则来自 failure class、结果前冻结、不读 gold、只派生 redundant terminal
fields、source bytes 不变、changed cohort 固定；仍明确 dependency 和小 eval 限制。

### Q83 `[L3]` 为什么你不能说 BF16 merge bug 的 root cause 是 RMSNorm？

答案标尺：RMSNorm 属于 fixed attached BF16/FP32 axis 的首个 registered boundary；
merge axis 首差是 q_proj；未注册 ops/internal kernels/causal propagation 未隔离。

### Q84 `[L3]` `30,640,994` 个 update round-back 能否证明 token flip 的原因？

答案标尺：证明 reproduced BF16 materialization 的大量 update loss，与 q_proj boundary
相关；不能独立证明这些具体元素造成 token 45 flip，需 causal intervention。

### Q85 `[L2]` 为什么选 FP32 candidate，代价是什么？

答案标尺：fixed compiler 下 argument exact `0.20→0.25`、field F1
`0.2609→0.2979`，无 compiled regression/safety regression；raw semantic `0.85→0.80`，
peak memory `1.9896x`，one run，无 stable speedup。

### Q86 `[L3]` “one pre-registered run”能证明只运行了一次吗？

答案标尺：repository 记录 operational protocol 与 selected artifact，hash 防替换；
无 external ledger/cryptographic execution-count attestation，不能排除 alternate run。

### Q87 `[L2]` origin attestation 完成后为什么 commit author 仍未认证？

答案标尺：hosted revision 与 content hash binding ≠ digital signature；commit 被报告
unsigned，无 author identity、supply-chain signature 或 transparency log。

### Q88 `[L3]` WSL 为什么不算 portable qualification target？

答案标尺：仍在同 controller/hardware identity，不能建立 operationally distinct
machine；frozen protocol 要 native Windows、不同 MachineGuid/GPU UUID digest、同
GPU class 与 locked user-space env。

### Q89 `[L3]` 如果独立机器 19/20 exact replay，怎样处理？

答案标尺：按冻结 13 categorical requirements fail，不事后放宽；保留 artifact，
定位 case/token/raw logits/environment delta，形成新 hypothesis 和预注册 gate；不宣称
portable，不立刻调 eval/weights/compiler。

### Q90 `[L3]` 这个项目下一步若做 Serving，你会怎样设计 gate？

答案标尺：先 portable qualification；再冻结 artifact/API/workload，测 semantic/safety
equivalence、TTFT/TPOT/throughput/memory/cold start/concurrency/overload，canary/
rollback；不绕过 Runtime policy；当前回答是设计，不是已实现经验。

---

## 9. 三道综合系统设计题

### A. 设计一个企业 Tool-Use Agent 平台

合格答案至少包含：typed tool registry、router/planner、context/RAG、untrusted content
boundary、policy/approval、WAL/idempotency/unknown outcome、state verifier、budget/
cancellation、trace/eval、model registry、canary/rollback，以及 model proposal 与
execution authority 分离。

### B. 把一个 7B 模型做成多租户 LoRA Serving

合格答案至少包含：base/adapter identity、compatible target modules、adapter cache/
hot swap、KV capacity、continuous batching、tenant isolation、quantization compatibility、
TTFT/TPOT/SLO、admission control、fallback、quality/safety regression 和 rollback。

### C. 设计从 bad case 到 model vN+1 的闭环

合格答案至少包含：consent/redaction、trace-to-dataset mapping、failure taxonomy、
family split、frozen eval、training config、ablation、artifact lineage、offline gate、
shadow/canary、production monitoring、human review 和 deletion/retention policy。
