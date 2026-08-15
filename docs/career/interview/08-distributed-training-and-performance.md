# 08. 分布式训练、并行边界与性能工程

> 本文是面试学习材料，不是项目进度 tracker。项目状态与唯一 active objective
> 只以仓库根目录 `PROJECT_STATUS.md` 为准。
>
> 证据标签：`[原理]`、`[通用工程]`、`[本仓库已实现]`、`[本仓库待实施]`。
> 公式中的变量均在正文定义；框架 API 与硬件特性会演进，工程结论必须在目标版本、
> 拓扑和模型上重测。

## 面试定位与学习目标

这一章面向 LLM Training Infra / Distributed Systems / GPU Performance 面试。
学完后应能：

1. 用 memory、compute、communication 三个约束选择并行策略；
2. 解释 DDP、FSDP/ZeRO、TP、PP、sequence/context parallel 的边界；
3. 估算参数、优化器、activation 和 collective 的数量级；
4. 正确使用 mixed precision、gradient accumulation、activation checkpointing；
5. 设计可恢复 checkpoint，并保证 distributed eval 不重不漏；
6. 用 roofline、arithmetic intensity 和 timeline 找瓶颈；
7. 对 Triton/custom kernel 先做 correctness gate，再谈加速；
8. 明确本仓库只有单卡 1.5B 证据，没有分布式实现证据。

## 1. 先从约束选择并行方式

`[原理]` 分布式不是“GPU 越多越快”，而是为了解决一个或多个约束：

- **模型状态放不下**：参数、梯度、优化器状态超出单卡显存；
- **activation 放不下**：长序列、大 micro-batch 或深网络占用过高；
- **单卡计算太慢**：希望缩短 time-to-train；
- **单卡吞吐不够**：希望扩大 global batch 或处理更多 token；
- **单设备上下文上限**：attention/KV 或序列本身需要跨卡；
- **故障域与资源池**：任务需要跨节点调度和恢复。

选择顺序通常是：先准确量内存与 profile，再采用最简单能解除约束的方案。每多一种
并行维度，就多一套 collective、切分规则、checkpoint 格式和正确性风险。

## 2. Collectives：分布式训练的通信积木

### 2.1 基本操作

`[原理]`

| Collective | 输入到输出 | 典型用途 |
|---|---|---|
| Broadcast | 一份数据复制到所有 rank | 初始化参数、控制信息 |
| Reduce | 多 rank 聚合到一个 rank | 汇总标量或张量 |
| All-reduce | 聚合后每个 rank 都拿到结果 | DDP 梯度同步 |
| Reduce-scatter | 聚合并把结果分片给各 rank | ZeRO/FSDP 梯度分片 |
| All-gather | 收集所有 rank 的分片到每个 rank | 参数临时重建、结果收集 |
| All-to-all | 每个 rank 向每个 rank 发送不同分片 | MoE token routing、某些并行转换 |
| Point-to-point | rank 间 send/recv | Pipeline stage 传 activation/gradient |

Rank 数记为 `N`，单个待聚合张量大小记为 `S` bytes。理想 ring all-reduce 每个 rank
的传输量数量级为：

```text
V_ring ~= 2 * (N - 1) / N * S
```

两倍来自 reduce-scatter 和 all-gather。真实耗时可用 latency-bandwidth 模型理解：

```text
T_comm ~= R * alpha + V / BW_effective
```

- `R`：算法通信轮数；
- `alpha`：每轮固定 latency；
- `V`：传输字节数；
- `BW_effective`：包含拓扑与竞争后的有效带宽。

小 tensor 更容易被 `alpha` 主导，大 tensor 更容易被带宽主导。跨机通信还受到
NIC、PCIe、GPU direct、交换拓扑、拥塞和 collective algorithm 影响，不能把链路
标称带宽直接当有效带宽。

### 2.2 拓扑意识

`[通用工程]` 应记录 rank 到 GPU、NUMA、PCIe switch、主机、NIC 的映射。常见问题：

- 同机快链路没有被优先使用；
- process 绑定到错误 NUMA node；
- 多任务共享 NIC 或 PCIe root，带宽抖动；
- collective bucket 太小导致 latency 主导，太大导致 overlap 太晚；
- 某 rank 输入更慢，所有 rank 在 collective barrier 等待。

排障要看每个 rank 的 timeline 和 collective duration，不能只看 rank 0 总耗时。

## 3. Data Parallel 与 DDP

### 3.1 数据并行语义

`[原理]` Data Parallel 在每个 rank 复制完整模型，各自处理不同 micro-batch，
backward 后聚合梯度。若第 `r` 个 rank 的 local gradient 为 `g_r`，平均梯度为：

```text
g = (1 / D) * sum(g_r),  r = 1 ... D
```

其中 `D` 是 data-parallel world size。框架可能让 collective 直接求和或平均，
optimizer step 前必须知道真实语义，否则 learning rate 和 loss scaling 会错。

全局 batch（以样本数或序列数计）为：

```text
B_global = B_micro * G_accum * D
```

- `B_micro`：每 rank 每次 forward 的 micro-batch；
- `G_accum`：gradient accumulation steps；
- `D`：data-parallel ranks。

若样本长度差异大，最好同时记录 global tokens per optimizer step；仅按 sequences
对齐可能造成 token batch 和 loss normalization 不一致。

### 3.2 DDP 的关键点

`[原理]` Distributed Data Parallel 通常在 backward 中按 bucket 触发 gradient
all-reduce，使较早就绪的梯度通信与后续 backward 计算重叠。它主要提高吞吐，不
减少每 rank 的参数、梯度和 optimizer state 复制。

`[通用工程]` 正确性检查：

- sampler 确保训练样本按预期分片，epoch/seed 一致；
- 所有 rank 执行相同 collective 顺序，避免 deadlock；
- unused/conditional parameter 路径有明确处理；
- loss denominator 按有效 token 而非 padding 或 rank 平均误算；
- `no_sync` 类 accumulation 只在非 step micro-batch 跳过同步；
- optimizer、scheduler、gradient clipping 发生在同步后正确位置；
- rank-local random augmentation 不产生意外重复。

### 3.3 DDP 的适用边界

选择 DDP 当完整模型状态和 activation 能放进每卡，目标主要是数据吞吐，且网络可
承受每 step 的梯度 all-reduce。若单卡已经放不下模型状态，单纯 DDP 无法解决。

## 4. 模型状态显存与 FSDP / ZeRO

### 4.1 训练状态的一阶估算

`[原理]` 对参数量 `P`，典型 mixed-precision Adam 类训练常见的一阶 payload 为：

```text
parameter copy      ~= 2P bytes   # 例如 BF16/FP16 参数
gradient            ~= 2P bytes
FP32 master weights ~= 4P bytes   # 若优化器维护
first moment        ~= 4P bytes
second moment       ~= 4P bytes
--------------------------------
model states        ~= 16P bytes
```

这不是普适常数。optimizer、低精度状态、参数保留策略、gradient dtype、flatten、
alignment 和 framework metadata 都会改变实际值。还没有包含 activation、临时 buffer、
communication bucket、allocator fragmentation 和 kernel workspace。

### 4.2 ZeRO 的分片层级

`[原理]`

| 策略 | 参数 | 梯度 | Optimizer states | 主要代价 |
|---|---|---|---|---|
| DDP | 复制 | 复制/同步 | 复制 | 简单、通信主要是梯度 |
| ZeRO-1 | 复制 | 复制 | 分片 | step 前后需同步更新参数 |
| ZeRO-2 | 复制 | 分片 | 分片 | reduce-scatter/all-gather 增加 |
| ZeRO-3 | 分片 | 分片 | 分片 | forward/backward 按层收集参数，通信更频繁 |

若理想均匀分片且忽略临时重建，sharded state 的每 rank payload 可近似除以 data
parallel world size `D`；但 ZeRO-3/FSDP forward 时仍需临时 all-gather 当前单元参数，
峰值由 wrapping unit、prefetch、同时在途 unit 和通信 buffer 决定。

### 4.3 FSDP 的理解方式

`[原理]` Fully Sharded Data Parallel 与 ZeRO-3 的共同核心是对参数、梯度和优化器
状态做 full sharding，并按计算需要 all-gather 参数、reduce-scatter 梯度。具体 API、
state dict 类型和实现细节会变，面试应说明不变的状态/通信生命周期。

`[通用工程]` Wrap 粒度过大，单次 all-gather 峰值高且 overlap 差；过小，collective
数量和 latency 增大。还要决定：

- parameter/gradient reduction dtype；
- forward/backward prefetch；
- CPU/NVMe offload 是否值得额外传输；
- sharded checkpoint 如何保存、重分片与恢复；
- tied weights、shared modules、frozen parameters 如何保持语义；
- topology 改变时能否从旧 world size 恢复。

## 5. Tensor、Pipeline、Sequence 与 Context Parallel

### 5.1 Tensor Parallel（TP）

`[原理]` TP 把单层大矩阵沿输入或输出维切到多卡。以线性层 `Y = XW` 为例，
可按 `W` 的列切分让每卡产生一部分输出，或按行切分后对部分结果做 reduce。
Transformer 每层通常需要 collective，因此 TP 更依赖低 latency、高带宽的局部互联。

适用：单层权重/activation 过大，或单卡矩阵计算需要横向扩展。代价：每层通信、
切分约束、kernel shape 变化和 checkpoint layout 复杂度。跨慢速节点使用高 TP degree
往往代价很高。

### 5.2 Pipeline Parallel（PP）

`[原理]` PP 把连续层分到 `p` 个 stage，micro-batch 在 stage 间流动。若采用简单
GPipe 式 schedule，`m` 个 micro-batches 的理想 bubble fraction 可近似：

```text
bubble_fraction ~= (p - 1) / (m + p - 1)
```

- `p`：pipeline stages；
- `m`：每个 global step 的 pipeline micro-batches。

增加 `m` 可摊薄 warm-up/drain bubble，但提高 activation、调度和 batch 约束。
1F1B 等 schedule 可以降低 peak activation 和改变 bubble 行为。实际还受 stage
不均衡、send/recv、recompute 和跨节点链路影响。

### 5.3 Sequence Parallel（SP）

`[原理]` “Sequence parallel”常指把本来在 TP ranks 上复制的 sequence-dimension
activation（例如某些 norm/dropout 区域）分片，从而减少 activation 内存；它通常
是 TP 的补充，并不自动解决 attention 对整个上下文的依赖。

术语在不同系统中可能不同。回答时必须说明具体张量形状、沿哪个维度切、何时
all-gather/reduce-scatter，而不是只说启用了 SP。

### 5.4 Context Parallel（CP）

`[原理]` CP 为长上下文把 token/context 维跨设备切分，并让 attention 获得远端
K/V 或等价的分块计算结果。它解决单设备放不下长序列 attention state 的问题，
但带来 causal mask、position、load balance、通信和数值稳定性挑战。

需要区分：

- 把非 attention activation 沿 sequence 切分的 SP；
- 真正让 attention context 跨设备协作的 CP；
- 推理中的 KV 分片或 sequence parallel serving，语义又不同。

### 5.5 组合成多维并行

`[通用工程]` 常见总 world size 关系：

```text
W = D * T * P * C
```

`D/T/P/C` 分别表示 data/tensor/pipeline/context parallel degree。不是所有系统都
按此完全正交组合，但它有助于检查 rank group。每个 collective 必须发生在正确的
process group 中；group 构造错误可能不报错却混合了不应聚合的数据。

选择经验：优先在快互联域内放通信频繁的 TP/CP，把 PP stage 边界或 DP 扩到较慢
节点；最终仍需以模型 shape、拓扑和 profile 决定。

## 6. Activation、Mixed Precision 与有效 batch

### 6.1 Activation memory

`[原理]` Activation 内存依赖 batch、sequence length、hidden size、层数、attention
实现以及为 backward 保存的中间量。粗略写成：

```text
M_activation = O(B_micro * T * H * L * B_dtype * K_saved)
```

`T` 是序列长度，`H` 是 hidden size，`L` 是层数，`K_saved` 表示实现保存的多个
中间张量因子。Attention 若显式保存 `T x T` 矩阵会有平方项；memory-efficient
attention 可避免完整 materialization，但不消除所有 activation。

### 6.2 Activation checkpointing

`[原理]` Checkpointing 只保存选定边界 activation，backward 时重新 forward 中间
段，以额外 FLOPs 换显存。它不同于训练状态 checkpoint：前者是单 step 内的
recomputation 技术，后者用于进程失败后恢复。

`[通用工程]` 需要验证 dropout/RNG、autocast、stateful layer、缓存和副作用在重算
时语义一致。选择重算边界时应测 peak memory 与 step time，而非假设“全重算最好”。

### 6.3 Gradient accumulation

`[原理]` accumulation 用多次 micro-batch backward 后再 optimizer step，以较小
activation 峰值获得较大 `B_global`。但它不减少每个 optimizer step 的总计算，且
过多 accumulation 会减少 step 频率、改变 scheduler 语义、降低通信/计算利用率。

Loss normalization 要按目标定义处理：若每个 micro-batch 有不同有效 token 数，
先对各自 mean loss 再简单平均可能偏置短样本。可累计 loss numerator 和有效 token
denominator，确保与单大 batch 语义一致。

### 6.4 Mixed precision

`[原理]` FP16/BF16 降低内存和提高适配硬件的吞吐；FP32 常用于部分累积、optimizer
state 或数值敏感运算。FP16 指数范围较小，常需要 loss scaling；BF16 指数范围接近
FP32，通常不依赖同样的 scaling，但 mantissa 更短，舍入误差仍然存在。

动态 loss scaling 的基本流程：放大 loss、backward、检查 gradient 是否 finite、
反缩放、clip/step；overflow 时跳过 step 并降低 scale。所有 rank 必须一致决定是否
step，否则参数状态会分叉。

`[通用工程]` 精度门禁包含：loss curve、gradient norm、non-finite count、skipped
steps、reference batch 输出/梯度差、最终固定 eval 和逐例安全差异。能训练完成不代表
数值路径等价。

## 7. 分布式训练参考流程

`[通用工程]` 版本无关伪代码：

```python
topology = init_process_groups(dp=D, tp=T, pp=P, cp=C)
model = build_model(config, topology)
optimizer = build_optimizer(model.sharded_parameters())
state = load_checkpoint_or_initialize()

for batch in distributed_data_iterator(state.data_cursor):
    optimizer.zero_grad_if_new_step()
    for microbatch in split_for_accumulation(batch):
        with mixed_precision_policy():
            loss_sum, valid_tokens = forward_loss(model, microbatch)
        backward(loss_sum)  # denominator handled consistently

    globally_normalize_gradients(valid_tokens)
    assert_all_ranks_finite_or_skip_together()
    clip_gradients_if_configured()
    optimizer.step()
    scheduler.step()
    advance_data_cursor()

    if durable_checkpoint_due():
        save_atomic_sharded_checkpoint(all_required_state())
```

配置快照至少绑定：模型、tokenizer、数据 manifest、sample order、seed、global/micro
batch、accumulation、precision、parallel degrees、optimizer/scheduler、checkpoint
格式、代码 revision、container/dependencies、GPU/driver/topology。

## 8. Checkpoint、故障恢复与弹性

### 8.1 完整恢复状态

`[原理]` 想从 step `k` 等价恢复，通常需要：

- 模型参数和 Adapter；
- optimizer states、master weights、scheduler；
- loss scaler 与已累计但尚未 step 的状态；
- global step、epoch、tokens seen；
- Python/CPU/GPU/RNG states；
- distributed sampler、shuffle seed、data cursor；
- parallel topology、shard metadata 与 schema version；
- 数据、代码、配置、环境和 artifact digest。

只保存模型权重通常只能 warm-start，不能声称 exact resume。

### 8.2 原子性与一致性

`[通用工程]` Sharded checkpoint 要有 manifest：预期 ranks/shards、每个文件 digest、
逻辑 tensor 到 shard 的映射、写入状态。推荐先写临时 generation，所有 shard 完成并
校验后再原子发布 manifest。读端只承认 complete manifest，不扫描“看起来存在”的
文件猜测完成。

故障实验至少包括：

- 某 rank 在写 shard 中途退出；
- manifest 写前/写后进程 crash；
- 一个 shard 损坏或来自不同 step；
- topology/world size 改变后重分片；
- 数据 iterator 在边界处恢复，检查无重复/遗漏；
- 恢复后若干 step 与 uninterrupted control 比较。

### 8.3 Straggler 与 hang

`[通用工程]` Collective timeout 往往是后果，不一定是网络根因。某 rank 可能先发生
OOM、data loader 卡住、kernel assert、不同 control flow 或进程被抢占。排障应收集
所有 rank 的最后成功 step、last collective、GPU error、data sample ID 和 heartbeat。
不要只延长 timeout 掩盖问题。

## 9. Profiling、Roofline 与通信重叠

### 9.1 Roofline 模型

`[原理]` 算术强度（Arithmetic Intensity）定义为：

```text
AI = FLOPs / bytes_moved
```

Roofline 对可达性能的上界近似为：

```text
P_attainable <= min(P_peak, BW_memory * AI)
```

- `P_peak`：目标 dtype 下硬件峰值计算吞吐；
- `BW_memory`：有效内存带宽；
- `AI`：算子每搬运一字节完成的 FLOPs。

低 `AI` 算子更可能 memory-bound，高 `AI` 算子更可能 compute-bound。实际还受
occupancy、launch overhead、shape、alignment、cache、fusion 和同步影响。Roofline
用于形成假设，不是只凭公式下结论。

### 9.2 性能指标

`[通用工程]`

- tokens/s、samples/s、step time 的 p50/p95；
- time-to-train / time-to-target-quality；
- peak allocated/reserved memory；
- GPU active time、SM/compute utilization、memory bandwidth；
- collective bytes/time、overlap ratio、wait time；
- data loader time、host-to-device time；
- samples/tokens per optimizer step；
- Model FLOPs Utilization（MFU），同时说明 FLOPs 估算口径；
- scaling efficiency：`E_N = throughput_N / (N * throughput_1)`。

Scaling efficiency 必须在等价 global batch/optimization 语义或明确的 weak/strong
scaling 设置下比较。扩大 batch 后 tokens/s 更高但收敛 step 数变化，不能直接说
training 更快；最终看 time-to-quality。

### 9.3 Profile 顺序

1. 建立单卡 reference，固定 shape、precision、数据和 loss；
2. 检查 CPU/data loader 是否喂满；
3. 看 GPU timeline，找空洞、同步、短 kernel 和大 memcpy；
4. 分解 forward/backward/optimizer/collective；
5. 观察每 rank，而非仅聚合平均；
6. 验证 overlap 是否真实减少 critical path；
7. 每次只改一个主要变量，重新做 correctness 和性能 gate。

## 10. Operator / Kernel / Triton Correctness Gate

### 10.1 为什么正确性先于速度

`[原理]` Custom kernel 可能在常见 shape 上看起来正确，却在非连续 stride、尾块、
极值、alias、不同 dtype、不同 device capability 或并发下产生 silent error。LLM 的
小数值差可能在 logit margin 边界改变 token，因此“平均误差很小”不足以发布。

### 10.2 分层门禁

`[通用工程]`

1. **Specification**：写清输入 shape/stride/dtype/device、广播、mask、输出和异常；
2. **Reference**：用简单可信实现产生 oracle，不与候选共享可疑代码；
3. **Forward correctness**：随机、结构化和 adversarial values；
4. **Backward correctness**：解析梯度 reference、有限差分或适用的 grad check；
5. **Shape matrix**：最小、非整块、prime、长宽极端、空/单元素（若合法）；
6. **Layout matrix**：contiguous、transposed、sliced、misaligned（按 contract）；
7. **Numerics**：absolute/relative error、ULP 或 task-specific bound，检查 NaN/Inf；
8. **Determinism/race**：重复、不同 launch order、stream、并发压力；
9. **Integration**：替换真实层后比较 loss、gradient、固定生成和 eval；
10. **Performance**：正确性全部通过后 warm-up、同步、重复统计和真实 shape 分布。

容差需随 dtype、归约长度和数学重排定义。不能事后看见结果再放宽 tolerance；应在
运行前注册允许的误差和任务级 gate。

### 10.3 性能对照

Benchmark 必须包含：reference kernel、候选 kernel、端到端模型；报告 latency 分布、
有效 bandwidth/FLOPs、compile/warm-up、峰值显存和 shape 权重。Microbenchmark
加速不代表 end-to-end 加速：若算子只占 2% step time，即使无限加速理论总收益也受
Amdahl's Law 限制。

## 11. Distributed Eval 的正确性

### 11.1 不重不漏

`[原理]` Eval 的第一条要求是每个 canonical sample ID 恰好计一次。某些 distributed
sampler 为整除 world size 会 padding/重复末尾样本；若不去重，指标被静默改变。

推荐每 rank 输出：sample ID、prediction、source dataset digest、model/config revision。
聚合端验证期望 ID 集合、重复数、遗漏数和顺序无关 digest，再计算指标。

### 11.2 非线性指标不能平均 rank 指标

`[原理]` Accuracy 若每 rank 样本数相同，可由正确数/总数的 sufficient statistics
聚合；Macro F1、AUC、percentile 等通常不能简单平均各 rank 的局部结果。

正确方式是：

- 汇总 confusion counts 后全局计算 F1；
- 收集必要 prediction/label 或可证明充分的统计量；
- latency percentile 从全局原始样本或 mergeable sketch 计算，不能平均 p95；
- loss 按有效 token 数加权，而非平均 rank mean。

### 11.3 生成评测的一致性

`[通用工程]`

- deterministic decoding 仍需绑定 dtype、kernel、model form 和 environment；
- sampling seed 要按 sample ID 派生，避免 world size 改变结果；
- generation stop、max tokens、prompt/tokenizer 与单卡 reference 一致；
- 每 rank 错误需进入最终 failure count，不能因 rank 0 成功而通过；
- artifact 合并必须原子，保留 rank outputs 便于审计；
- 对同一固定小集做 single-rank vs multi-rank exact/registered-tolerance control。

## 12. 故障模式与排障矩阵

| 症状 | 可能原因 | 证据 | 处置 |
|---|---|---|---|
| 多卡比单卡还慢 | batch 太小、collective/launch 主导 | compute/comm timeline | 调 batch/bucket/拓扑或减少并行维 |
| 固定 step hang | collective 顺序不一致、某 rank 先失败 | all-rank last event | 找首个异常 rank，不只加 timeout |
| Loss 多卡与单卡偏离 | global normalization/seed/sampler 错 | sample IDs、grad control | 修正 denominator 和分片语义 |
| 周期性 step spike | checkpoint、dataloader、GC/通信拥塞 | synchronized timeline | 异步/错峰但保持一致性 |
| FSDP 峰值 OOM | wrap/prefetch 导致多 unit 同驻 | all-gather lifetime | 调 wrap、prefetch、limit in-flight |
| Resume 后曲线跳变 | optimizer/RNG/data cursor 缺失 | checkpoint manifest | 补齐状态并做 uninterrupted control |
| Eval 指标随 world size 变 | 重复 padding 或局部指标平均 | ID audit、global counts | 去重并重算充分统计量 |
| Kernel 偶发错误 | race、尾块、stride/精度假设 | shape/layout/repeat matrix | 收紧 contract 或修 kernel |

## 13. 概念比较速查

| 概念 | 核心差别 |
|---|---|
| Data Parallel vs Tensor Parallel | 不同数据上的完整模型 vs 单层张量跨卡切分 |
| FSDP/ZeRO vs TP | 分片模型状态并按需重建 vs 分片单层计算本身 |
| Pipeline Parallel vs TP | 按层/stage 切分 vs 层内矩阵切分 |
| Sequence Parallel vs Context Parallel | 常为 TP 补充的 activation sequence 分片 vs attention context 跨设备 |
| Gradient accumulation vs Data Parallel | 时间上累积 micro-batch vs 空间上并行不同数据 |
| Activation checkpointing vs Training checkpoint | step 内重算省显存 vs crash 后恢复状态 |
| Strong scaling vs Weak scaling | 固定总工作量加资源 vs 每设备工作量近似固定 |
| Raw throughput vs Time-to-quality | 每秒处理量 vs 达到目标指标的总时间 |
| Microbenchmark vs End-to-end | 局部算子速度 vs 完整 critical path |

## 14. 高频面试题与分层答案

### Q1：DDP、FSDP/ZeRO-3 和 Tensor Parallel 怎么选？

**30 秒答案**

先看单卡是否放得下完整模型状态和单层计算。放得下、主要扩数据吞吐，优先 DDP；
模型状态放不下，用 FSDP/ZeRO 分片参数、梯度和 optimizer；单层或单个矩阵本身放不下，
或需要层内算力扩展，用 TP。TP 每层通信频繁，通常放在快互联域内。

**2 分钟答案**

说明 DDP 每卡复制状态并 all-reduce 梯度；FSDP/ZeRO-3 按层 all-gather 参数、
reduce-scatter 梯度，以通信和临时重建换显存；TP 切矩阵，改变每层计算图。
若模型很深还可加 PP，以 stage 切层但承担 bubble。最终依据参数/activation 峰值、
collective volume、互联拓扑、batch/sequence 和 time-to-quality profile，采用最少的
并行维度并做单卡数值 control。

**深挖方向**

- ZeRO 各 stage 分片哪些状态；
- FSDP wrap unit 如何影响峰值和 collective；
- TP row/column split 的 collective；
- 多维 rank group 与 checkpoint 重分片。

### Q2：为什么梯度累积不等于更大 data parallel？

**30 秒答案**

两者都能增大 global batch，但 accumulation 在同一 rank 上串行执行多个 micro-batch，
主要降 activation 峰值；data parallel 同时在多个 rank 计算，主要提高吞吐并引入
梯度通信。它们对 step time、通信频率、利用率和故障域不同。

**2 分钟答案**

给出 `B_global = B_micro * G_accum * D`，说明非 step micro-batch 通常跳过 DDP
同步，最后一次再同步。还要保证 loss 按有效 token 正确归一化，scheduler 按 optimizer
step 而非 micro-step 更新。过高 accumulation 会降低 optimizer step 频率和并行度；
扩大 D 又可能受 all-reduce 限制。选择要看显存、网络和收敛。

**深挖方向**

- variable-length token normalization；
- gradient clipping 和 unscale 的顺序；
- batch 扩大后 learning rate/收敛如何验证；
- no-sync 使用错误造成什么。

### Q3：如何证明一个 Triton kernel 可以替换 reference？

**30 秒答案**

先冻结输入/输出 contract 和容差，用独立 reference 覆盖 dtype、shape、stride、尾块、
极值、NaN/Inf、重复和并发；若有 backward，再验证梯度。然后做真实层和固定 eval
集成门禁，最后才在真实 shape 分布上测性能和端到端收益。

**2 分钟答案**

容差必须事前定义并考虑 reduction 与低精度，不只看平均误差。对 race 要不同 stream、
launch order 和多次运行；对 out-of-bounds 用边界 shape。性能测量包含 warm-up/compile、
同步、p50/p95、有效带宽/FLOPs和显存。再用 Amdahl's Law 检查局部加速能否影响 step
critical path。任何 task/safety regression 都阻止替换。

**深挖方向**

- absolute/relative/ULP tolerance；
- atomic reduction 与 determinism；
- autotune config 如何进入 artifact provenance；
- backward reference 和有限差分的局限。

### Q4：为什么 distributed eval 会悄悄算错？

**30 秒答案**

常见原因是 sampler 为整除 world size 重复样本、rank 失败未计入、按 rank 平均非线性
指标，或 loss 未按有效 token 加权。正确做法是先审计 canonical sample IDs 不重不漏，
汇总充分统计量或原始 prediction，再在一个地方计算全局指标。

**2 分钟答案**

Macro F1 要汇总 confusion counts，p95 不能平均各 rank p95，sampling seed 应按 sample
ID 派生以保持 world-size 不变性。生成评测还要绑定 tokenizer、prompt、dtype、kernel
和 decoding。最后用固定小集比较 single-rank 与 multi-rank outputs/metrics，并保存
每 rank artifact 和完整合并 manifest。

**深挖方向**

- exact sample set digest；
- partial rank failure 的 fail-closed 语义；
- duplicate padding 如何发现；
- distributed AUC/percentile 的聚合方法。

## 15. 本项目映射与证据边界

### `[本仓库已实现]` 可以怎么说

- 当前模型实验是 `Qwen2.5-1.5B-Instruct`、LoRA rank 16、单张 RTX 4090 Laptop
  GPU；有 BF16 LoRA 训练、FP32/BF16 attached/merged 数值诊断和峰值显存记录。
- LoRA v1 为 100 optimizer steps，v2 为 66 optimizer steps；仓库绑定了数据、配置、
  模型/Adapter、raw outputs、指标和环境证据。
- 已对重复执行、precision、模块边界、raw logits 和 token argmax 做细粒度数值诊断；
  这些经验可用于解释 mixed precision correctness gate。
- unified offline gate 在多个 Python 版本运行，但这是软件兼容 CI，不是多 GPU 训练。

### 不能越界的说法

- 没有 DDP/FSDP/ZeRO/TP/PP/SP/CP 的项目运行、scaling curve 或通信 profile；
- 没有多节点 checkpoint/recovery、distributed eval 或 topology 证据；
- 没有 custom Triton kernel 的项目实现或端到端加速数字；
- 单机 1.5B 的 LoRA 指标不能证明 large-scale pretraining 或 distributed systems 经验。

### `[本仓库待实施]`

- Tiny Transformer lab 的 operator graph、profile 与 correctness-gated kernel 实验；
- 固定模型/数据上的 DDP → FSDP/ZeRO 对照；
- collective/topology/overlap profile 与强/弱扩展曲线；
- sharded checkpoint、world-size change recovery 和故障注入；
- single-rank vs distributed eval exactness gate。

面试表述示例：

> 当前仓库的真实证据是单卡 1.5B LoRA 和数值诊断，分布式模块仍是
> `[本仓库待实施]`。我会从状态显存和通信模型说明为什么选 DDP/FSDP/TP，
> 并给出 correctness、scaling、recovery 的验收方案，但不会引用不存在的多卡数字。

## 16. 自测与实践

### 16.1 口头自测

1. 写出 ring all-reduce 每 rank 的近似传输量，并解释 latency 项；
2. 从 16 bytes/parameter 的示例拆出每一项，并说明何时不成立；
3. 用张量 shape 解释 row/column TP 的 collective；
4. 区分 SP、CP 与推理 KV sharding；
5. 说明 activation checkpointing 为什么可能改变 RNG 语义；
6. 举例解释为什么各 rank Macro F1 的平均值不是 global Macro F1；
7. 列出 exact resume 必须保存的状态；
8. 说明 microbenchmark 快 2 倍为何端到端可能不变。

### 16.2 纸面估算

任选一个模型参数量和目标 GPU，计算并写出假设：

1. DDP 下每 rank model-state payload；
2. ZeRO-1/2/3 理想分片后的数量级与临时 all-gather 峰值；
3. 不同 `B_micro/G_accum/D` 的 global sequences 和 global tokens；
4. 一个 `S` bytes gradient bucket 在 `N` ranks ring all-reduce 的传输量；
5. TP/PP degrees 改变后 world-size group；
6. 所有未计入的 activation、buffer、fragmentation 与 topology 风险。

### 16.3 最小工程实践

`[本仓库待实施]` 一个可辩护的最小实验应：

1. 固定单卡 reference：样本 IDs、loss、梯度摘要、step time、peak memory；
2. 在两个 data-parallel ranks 保持等价 global batch，验证若干 step 数值和样本覆盖；
3. 再引入 full sharding，记录 memory、collective、step time 与 checkpoint；
4. 注入 rank crash 和 partial checkpoint，证明 fail-closed 与 resume；
5. 用固定 eval 做 single-rank/multi-rank 不重不漏和指标复算；
6. Profile 一个热点算子，写 reference 与候选 correctness matrix；
7. 只在 correctness gate 通过后报告 kernel 与端到端性能；
8. 输出 scaling efficiency 和 time-to-quality，不只报峰值 tokens/s。

完成标准不是“多卡启动成功”，而是能解释每一份状态在哪张卡、每次 collective 为什么
发生、失败后从哪一状态恢复、指标如何全局复算，以及性能提升是否在正确性和收敛语义
不变的前提下成立。
