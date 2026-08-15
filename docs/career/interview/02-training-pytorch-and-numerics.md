# 02｜训练工程、PyTorch、精度与数值诊断

> 本章是面试学习材料，不是项目进度 tracker。项目当前状态只以根目录
> `PROJECT_STATUS.md` 为准。

证据标签：`[原理]` 表示可推导的通用原理；`[通用工程]` 表示可迁移的实践；
`[本仓库已实现]` 仅指冻结代码、测试、指标或 artifact 已证明的内容；
`[本仓库待实施]` 是 roadmap，不能包装成项目经验。

## 1. 面试定位与学习目标

会调用 `Trainer` 不等于会做训练工程。面试真正考察的是：梯度如何产生，optimizer
如何更新参数，显存花在哪里，低精度为什么能训练，以及出现 NaN、OOM、不可复现
或同权重不同输出时如何建立可证伪的诊断链。

完成本章后，应能：

- `[原理]` 解释 reverse-mode autograd、leaf tensor、梯度累积和 graph lifetime；
- `[原理]` 写出 AdamW、warmup、scheduler、global-norm clipping 的公式；
- `[通用工程]` 正确比较 gradient accumulation 与 gradient checkpointing；
- `[原理]` 从 exponent/mantissa 解释 FP32、TF32、FP16、BF16，而不是只说“BF16
  更稳定”；
- `[通用工程]` 设计 AMP/loss scaling、checkpoint/resume、RNG 和 determinism
  合同；
- `[通用工程]` 用 memory ledger 排查 OOM，用 profiler 区分 compute、memory、
  synchronization 与 input pipeline；
- `[通用工程]` 区分 repeatability、numerical closeness、token identity 和 task
  quality；
- `[本仓库已实现]` 准确讲清本项目的 BF16/FP32、attached/merged、ABBA controls，
  并坚持 `first observed boundary != unique root cause`。

## 2. 原理：训练、精度与误差传播

### 2.1 Reverse-mode autograd

`[原理]` 神经网络训练通常计算标量 loss `L` 对大量参数 `theta` 的梯度。Forward
构建由 primitive operations 组成的动态图；backward 从 `dL/dL=1` 开始，按反向
拓扑顺序应用 chain rule：

```text
y = f(x), z = g(y)
dL/dx = dL/dz * dz/dy * dy/dx
```

对矩阵 `Y=XW`，若上游梯度为 `G=dL/dY`：

```text
dL/dX = G W^T
dL/dW = X^T G
```

PyTorch 心智模型：

- `requires_grad=True` 的 leaf parameter 保存 `.grad`；
- 中间 tensor 通常不保存 `.grad`，但 autograd 保存 backward 所需值；
- `.backward()` 默认把新梯度加到已有 `.grad`，不会自动清零；
- 多数 graph backward 后被释放；只有确有多次 backward 需要时才保留 graph；
- `detach()` 切断梯度边，`no_grad/inference_mode` 关闭训练图构建；
- in-place 修改若破坏 backward 所需版本，会报错或改变语义。

`[通用工程]` 训练 step 的正确边界是：zero gradients → forward → normalized loss
backward → optional unscale/clip → optimizer step → scheduler step。若做 accumulation，
zero/step 只发生在 accumulation window 边界。

### 2.2 AdamW 与 decoupled weight decay

`[原理]` 第 `t` 步梯度为 `g_t`，Adam 的一、二阶指数移动平均为：

```text
m_t = beta1 * m_(t-1) + (1-beta1) * g_t
v_t = beta2 * v_(t-1) + (1-beta2) * g_t^2
m_hat = m_t / (1-beta1^t)
v_hat = v_t / (1-beta2^t)
```

AdamW 的参数更新可写为（衰减项与 adaptive gradient 都基于更新前的
`theta_(t-1)`）：

```text
theta_t = (1 - lr_t * weight_decay) * theta_(t-1)
        - lr_t * m_hat / (sqrt(v_hat) + epsilon)
```

第一项包含 decoupled weight decay。它与把 `lambda*theta` 加到梯度的 L2 regularization
在自适应 optimizer 中不等价，因为后者还会被 Adam 的二阶缩放改变。

常见 parameter groups：bias 和 normalization scale 常设 `weight_decay=0`；matrix
weights 使用非零 decay。但这是一种待验证的 policy，不应脱离模型/任务照抄。

关键超参数：

- `lr` 决定更新尺度；
- `beta1` 平滑方向，`beta2` 平滑平方梯度；
- `epsilon` 防止除零并影响极小梯度区域；
- `weight_decay` 约束权重尺度；
- optimizer state 通常是显存大头之一。

### 2.3 Warmup 与 scheduler

`[原理]` 初始化阶段参数、activation 与 optimizer moments 尚未稳定，直接使用峰值
learning rate 可能造成更新过大。Linear warmup 示例：

```text
lr(t) = lr_peak * t / warmup_steps,  0 <= t <= warmup_steps
```

之后可用 constant、linear decay 或 cosine decay。例如 cosine：

```text
progress = (t - warmup_steps) / (total_steps - warmup_steps)
lr(t) = lr_min + 0.5 * (lr_peak-lr_min) * (1 + cos(pi*progress))
```

`total_steps` 应按 optimizer steps 而不是 micro-batches 计算。改变 dataset size、
packing 或 accumulation 后如果不重算 scheduler，实际学习率轨迹就变了。

### 2.4 Gradient clipping

`[原理]` Global norm：

```text
norm = sqrt(sum_parameters sum_elements g_i^2)
scale = min(1, max_norm / (norm + epsilon))
g_i <- scale * g_i
```

它限制整个梯度向量的 L2 norm，不是逐元素截断。AMP 下必须先 unscale 再计算和
clip，否则 clip 的是被 loss scale 放大的梯度。Clipping 能缓解爆炸性 step，不能
修复错误数据、NaN activation、过高学习率或错误 loss mask。

### 2.5 Gradient accumulation

`[原理]` 设 micro-batch 数为 `K`。若每个 micro-batch loss 都是相同口径的 mean，
常用：

```text
for k in 1..K:
    (loss_k / K).backward()
optimizer.step()
```

effective batch 粗略为：

```text
micro_batch_per_device * accumulation_steps * data_parallel_world_size
```

与一个大 batch 严格等价需要更多条件：样本/token loss 权重一致、dropout/RNG
语义可比、BatchNorm 等 batch-dependent layer 不改变、optimizer/scheduler 只在
window 末 step、gradient clipping 时点一致。变长序列若按“每个 micro-batch mean”
再平均，会与按全部非 mask token 的全局 mean 不同；更稳妥的是按 supervised token
总数归一化。

### 2.6 Gradient checkpointing

`[原理]` 也叫 activation checkpointing。Forward 不保存某些中间 activation，
backward 时重算它们，用额外计算换显存。它与训练状态 checkpoint 完全不同：

- gradient/activation checkpointing：单个 step 内的重算策略；
- training checkpoint：持久化到磁盘，用于中断恢复。

启用后常见代价是 step time 增加；若重算段包含随机操作，框架需正确保存/恢复 RNG
状态，否则 forward 与 recompute 不一致。

### 2.7 FP32、TF32、FP16 与 BF16

`[原理]` IEEE-like floating point 可粗略看成 sign、exponent、fraction：exponent
决定动态范围，fraction/mantissa 决定有效精度。

| 格式 | 总位数 | exponent bits | fraction bits | 关键性质 |
|---|---:|---:|---:|---|
| FP32 | 32 | 8 | 23 | 范围和精度都较高，内存/带宽成本大 |
| TF32 | Tensor Core 计算格式 | 8 | 约 10 | 常用于 FP32 matrix multiply 的加速路径；存储仍常为 FP32 |
| FP16 | 16 | 5 | 10 | 精度尚可但范围窄，梯度容易 underflow/overflow |
| BF16 | 16 | 8 | 7 | 动态范围接近 FP32，精度较粗，通常无需 loss scaling |

表中 fraction bits 未计隐含 leading bit。不能仅从 tensor 的 storage dtype 推断每个
算子的实际 accumulation dtype；kernel、autocast 和硬件路径都可能影响计算。

为什么 FP16 常用 loss scaling？若小梯度在 FP16 表示范围内下溢为 0，先把 loss
乘以 `S`，则 gradient 也乘以 `S`；backward 后检查 finite，再除以 `S`，可保留更多
小梯度：

```text
scaled_loss = S * loss
scaled_grad = S * grad
optimizer_grad = scaled_grad / S
```

Dynamic loss scaling 在 overflow 时减小 `S`，持续稳定时逐渐增大。BF16 exponent
范围较大，通常不依赖 loss scaling，但低 mantissa 仍会造成 rounding、吸收小更新
和 near-boundary 输出变化。

### 2.8 AMP 与常见训练状态

`[通用工程]` Automatic Mixed Precision 通常让矩阵乘在较低精度运行，同时把某些
reduction/normalization/loss 保持在更安全精度。常见状态组合包括：

- low-precision model/compute weights；
- FP32 master weights（具体 optimizer/框架策略不同）；
- FP32 optimizer moments；
- low-precision activations，部分 op 自动升精度；
- FP16 时的 GradScaler 状态。

因此“BF16 参数只需 2 bytes，所以训练显存就是 `2P`”是错误估算。还要计算 gradients、
optimizer states、master copies、activations、temporary workspaces、communication
buffers、KV/cache（若适用）和 allocator fragmentation。

### 2.9 浮点误差与执行图

`[原理]` 浮点数只近似实数。核心现象：

- rounding：结果映射到最近可表示值；
- absorption：小增量加到大数后舍入回原值；
- non-associativity：`(a+b)+c` 不一定等于 `a+(b+c)`；
- reduction order：并行归约顺序改变末位；
- fused operation：FMA 或 fused kernel 的中间舍入点不同；
- algorithm/kernel selection：shape、dtype、library 或 workspace 可能选择不同实现；
- autoregressive amplification：一次 argmax flip 后，后续 prefix 已不同，不能再把
  后续差异当作独立同输入比较。

LoRA 的两个数学上等价执行图在浮点中未必 bitwise 等价。设 base weight `W`，LoRA
matrices `A in R^(r x d_in)`、`B in R^(d_out x r)`，scale `s=alpha/r`：

```text
attached: x W^T + s * (x A^T) B^T
merged:   x (W + s * B A)^T
```

它们在实数代数上相等，但 matrix multiplication 分组、delta materialization 和加法
舍入点不同。因此输出可以有微小 deterministic drift；是否影响 token 取决于 logit
margin，而不是“有无任何非零差异”。

### 2.10 Determinism、RNG 与可复现

需要区分：

- repeatability：同一环境、同一路径重复是否一致；
- reproducibility：独立环境按冻结合同是否得到同一结果；
- determinism：给定状态后计算路径是否固定；
- statistical reproducibility：多 seed 的结论方向和区间是否稳定。

`[通用工程]` 至少绑定：Python/NumPy/PyTorch/CUDA RNG states，sampler state，data
order/epoch/offset，model/optimizer/scheduler/scaler states，global step，gradient
accumulation phase，library/driver/hardware，precision/backend flags，dataset/config/
code hashes。

只设置一个 seed 不够。数据 loader workers、dropout、sampling、distributed sampler、
non-deterministic kernels 和恢复时点都可能改变随机序列。

### 2.11 Training checkpoint 与 exact resume

一个可恢复 checkpoint 至少应包含：

```text
model/adapters
optimizer states
scheduler state
GradScaler state if used
global optimizer step and consumed samples/tokens
gradient-accumulation boundary
RNG states for all relevant generators/devices
sampler/dataloader progress
config, code commit, dataset identity, tokenizer identity
```

恢复验证不能只看“loss 继续下降”。严格测试是在一个小实验中比较 uninterrupted run
与 interrupted→resume run 的后续 batch IDs、LR、loss、parameter/optimizer digests。
如果在 accumulation window 中间保存，还需保存 accumulated gradients，或明确只在
optimizer-step 边界 checkpoint。

### 2.12 OOM 的内存账本

粗略分解：

```text
peak = parameters
     + gradients
     + optimizer states/master weights
     + saved activations
     + temporary workspaces
     + communication buffers
     + framework/allocator overhead
```

对 dense full fine-tuning，AdamW 的持久状态常可粗略达到每参数十余 bytes，但具体值
取决于参数/梯度/optimizer state dtype、是否有 master copy 和 sharding。不能把这个
经验数当固定公式。LoRA 只训练少量参数，可显著减少 trainable gradients/optimizer
states，但 frozen base weights 和 activation 仍占显存；QLoRA 才进一步量化 base
storage。

## 3. 应用与选型 trade-off

| 选择 | 适合 | 收益 | 代价/风险 |
|---|---|---|---|
| FP32 | 数值 reference、小模型诊断、敏感 reduction | 精度较高、便于隔离 | 显存/带宽约为 16-bit 两倍，仍非绝对实数 |
| BF16 | 支持 BF16 的现代 GPU 上训练/推理 | FP32 级动态范围、性能好 | mantissa 粗，小更新/近边界会舍入 |
| FP16 + scaling | 硬件/算子偏好 FP16 | mantissa 比 BF16 多 | 动态范围小，scaler 与 overflow 管理复杂 |
| TF32 | 可接受近似的 FP32 matmul 加速 | Tensor Core 性能 | 不是完整 FP32 mantissa；严格 reference 应显式控制 |
| gradient accumulation | 显存容不下目标 effective batch | 不增加单步 activation 峰值 | 训练更慢，normalization/scheduler 容易写错 |
| activation checkpointing | activation 是峰值瓶颈 | 显著降 activation memory | backward 重算，吞吐下降、RNG 更复杂 |
| global-norm clipping | 偶发大梯度 | 限制 step 尺度 | 掩盖而非修复根因 |
| attached LoRA | 多 adapter、保留独立 artifact、避免 merge rounding | 灵活切换，base 不变 | 额外算子/服务复杂度，需精确绑定 base+adapter |
| merged LoRA | 单一部署权重、可能简化 serving | 去掉运行时 adapter 分支 | materialization rounding、不可逆组合、需重新全量验证 |

选型不能只看单点 accuracy。至少联合考虑 quality/safety、峰值显存、tokens/s、恢复
能力、artifact 形式、跨机复现和生产 serving compatibility。

## 4. 工程实现

### 4.1 显式训练 loop 伪代码

以下为 PyTorch 风格、版本无关的控制流伪代码：

```python
model.train()
optimizer.zero_grad(set_to_none=True)

for micro_step, batch in enumerate(loader):
    with autocast_context(dtype=chosen_dtype):
        output = model(**batch)
        # 更严格的变长序列实现应按 supervised token 总数归一化
        loss = output.loss / accumulation_steps

    scaled_loss = scaler.scale(loss) if use_fp16_scaler else loss
    scaled_loss.backward()

    if (micro_step + 1) % accumulation_steps != 0:
        continue

    if use_fp16_scaler:
        scaler.unscale_(optimizer)
    grad_norm = clip_grad_norm_(trainable_parameters, max_norm)

    finite = gradients_are_finite(trainable_parameters)
    if use_fp16_scaler:
        # 概念 helper：overflow 时跳过 optimizer update，但仍更新 dynamic scale。
        updated = scaler_step_if_finite(scaler, optimizer, finite)
        scaler.update()
    elif finite:
        optimizer.step()
        updated = True
    else:
        handle_non_finite_step_fail_closed()
        updated = False

    if updated:
        scheduler.step()
        global_step += 1

    optimizer.zero_grad(set_to_none=True)
```

应记录 optimizer step，而不是只记录 micro-step。日志至少含 LR、token-normalized
loss、grad norm、skipped steps、throughput、allocated/reserved memory、data position。

### 4.2 AdamW parameter groups

```python
decay, no_decay = [], []
for name, parameter in model.named_parameters():
    if not parameter.requires_grad:
        continue
    if is_bias_or_norm_scale(name, parameter):
        no_decay.append(parameter)
    else:
        decay.append(parameter)

groups = [
    {"params": decay, "weight_decay": wd},
    {"params": no_decay, "weight_decay": 0.0},
]
optimizer = AdamW(groups, lr=peak_lr, betas=betas, eps=eps)
```

`is_bias_or_norm_scale` 必须由模型结构和命名验证，不要仅用模糊字符串导致参数漏分组。
启动时输出每组 parameter names/counts，并与总 trainable parameter count 对账。

### 4.3 Checkpoint/resume 合同

```python
state = {
    "model": model.state_dict(),
    "optimizer": optimizer.state_dict(),
    "scheduler": scheduler.state_dict(),
    "scaler": scaler.state_dict() if scaler else None,
    "global_step": global_step,
    "consumed_tokens": consumed_tokens,
    "sampler": sampler.state_dict(),
    "rng": capture_all_rng_states(),
    "identities": {
        "code_commit": commit,
        "dataset_digest": dataset_digest,
        "tokenizer_digest": tokenizer_digest,
        "config_digest": config_digest,
    },
}
atomic_save_then_fsync(state, checkpoint_path)
```

`[通用工程]` 保存时先写临时文件并完成校验，再原子替换；保留 last-known-good；加载
时 fail closed 检查 identity，不静默接受 dataset/config 漂移。大规模 checkpoint
还要考虑 shard 完整性、manifest 和 distributed rank 协调。

### 4.4 OOM 排障顺序

1. 先记录失败发生在 load、forward、backward、optimizer step 还是 eval/generate；
2. 记录 allocated、reserved、peak、sequence/token count 和具体 batch；
3. 确认是否意外保留 graph，例如把带 grad 的 loss/tensor 塞入 list；
4. 降低 micro-batch，不先改变 effective batch；
5. 按长度分桶或限制异常长样本；
6. 开 activation checkpointing / memory-efficient attention；
7. 检查 optimizer/base precision、LoRA/QLoRA、sharding/offload 选项；
8. 最后才把 allocator tuning 当主要修复，避免掩盖真实峰值。

`empty_cache()` 只把未占用的 cached blocks 交还 allocator，不会释放仍被 tensor
引用的内存，也不能降低真实 live-tensor 峰值。

### 4.5 Profiling 方法

先提出假设，再采 profile：

- CPU input pipeline：GPU utilization 出现空洞，data loading/tokenization 占比高；
- compute-bound：Tensor Core/GEMM 活跃，高 arithmetic intensity；
- memory-bound：带宽高而 compute units 未满，decode/elementwise 常见；
- synchronization-bound：频繁 `.item()`、logging、barrier、small kernels；
- allocator/fragmentation：reserved 远高于 allocated，并随 shape 抖动。

预热后采有限 step；使用 trace、operator time、shape、memory 和 kernel 统计。Profiler
本身会改变时序，不应把 profile run 的 wall time 当正式性能基准。

### 4.6 数值误差隔离 protocol

一个可辩护的诊断顺序：

```text
freeze input/model/config/backend
 -> fresh repeat each path to test within-path stability
 -> compare tokens and decoded output
 -> capture raw logits and processed scores at the first token boundary
 -> change one factor at a time (dtype OR execution form)
 -> ABBA fresh-load ordering to reduce order/lifecycle confounding
 -> pre-register a bounded module capture plan
 -> verify predecessor equality and observed boundary inequality
 -> replay the local operation with captured values
 -> state exactly what is and is not causally isolated
```

为什么用 ABBA？设 A、B 是两条路径。顺序 `A1, B1, B2, A2` 能同时检查每条路径
repeat stability，并让单调的时间/温度/allocator 顺序效应不完全与 A/B 重合。ABBA
不是随机试验，也不能排除所有环境 confounder；它只是比一次 A→B 更强的 lifecycle
control。

### 4.7 本项目数值案例的正确讲法

`[本仓库已实现]` 需要先定义四条路径：

```text
BF16 attached:
  stored BF16 checkpoint -> BF16 base/inference + stored FP32 Adapter, factorized

BF16 merged:
  stored BF16 checkpoint -> materialize LoRA delta into BF16 base weight

FP32 attached:
  widen the same stored BF16 checkpoint values to FP32
  -> FP32 base/inference + FP32 Adapter, factorized

FP32 merged:
  widen stored BF16 values to FP32 -> materialize FP32 LoRA delta -> FP32 inference
```

这里的 FP32 不是 pristine FP32 pretrained checkpoint；已经存成 BF16 的 base values
被 widened 后，丢失的原始精度不会恢复。Adapter storage/runtime 是 FP32。
`autocast_adapter_dtype` 是 PEFT 加载 Adapter 时的 dtype policy，不是 generation AMP。
项目的 generation autocast 和 TF32 均明确禁用。

冻结证据链：

1. BF16 attached 与 BF16 safe-merged 各自 fresh repeat 稳定，但在 `eval-001` 的
   zero-based generated token index 45 分别选择 `true` 与 `false`；这是 deterministic
   cross-path boundary，不是 within-path nondeterminism。
2. BF16 merge audit 覆盖 112 个 Q/K/V/O LoRA target modules；PEFT actual merged
   weights 与复现 merge 算法一致。大量理想非零 Adapter updates 在 materialize 成
   BF16 时舍入回 base value，分类为 BF16 safe-merge weight rounding，而不是未经
   证据的“PEFT bug”。
3. 直接比较 BF16 attached 与 FP32 merged 同时改变 dtype 和 execution form，因此
   即使 raw-logit argmax flip，也不能归因给其中一个因素。
4. 固定 FP32 dtype，只比较 attached 与 merged：两条路径 48 tokens 完全相同，但
   index 45 的 `151,936` 维 raw-logit 中 `150,968` 个元素不同，最大绝对差约
   `1.7357e-4`。这证明 deterministic execution-form numerical drift，没有证明
   same-dtype token drift。
5. 四次 FP32 ABBA run 在预注册 13-stage plan 中，前一阶段 input RMSNorm output
   相同，首个不同的注册输出是 layer-0 `q_proj`。captured replay 同时复现 factorized
   attached graph 与 materialized-linear graph；这支持“execution-form drift”，不
   证明唯一 CUDA/kernel/非结合性 root cause，也未隔离两条 counterfactual 各自向
   后传播。
6. 固定 attached execution form，只改变 base/inference dtype，BF16/FP32 各两次
   ABBA repeat 稳定，index 45 的 raw-logit argmax 从 `true` 翻到 `false`。这是
   total dtype effect on one frozen path，不是 pristine checkpoint 比较。
7. 在预注册 module plan 中，embedding canonical FP32 output 相同，首个不同注册
   output 是 layer-0 `input_layernorm`。随后 same-input、same-weight 的 standalone
   `Qwen2RMSNorm` BF16/FP32 control 精确复现该 boundary output delta。这说明所锁定
   dtype arithmetic 足以产生该边界差异；不证明它独立造成 LM-head/token flip，也
   不命名唯一 low-level root cause。

一句必须坚持的 claim boundary：

```text
first observed unequal output in a preregistered capture plan
!= first unequal operation in the complete execution history
!= unique root cause of downstream token or task behavior
```

## 5. Metrics 与 gates

### 训练健康度

- token-normalized train/validation loss；
- learning rate、gradient global norm、clipped-step rate；
- NaN/Inf、GradScaler skipped steps；
- tokens/s、samples/s、step-time 分布；
- allocated/reserved/peak memory；
- trainable parameter count 与 optimizer-state bytes；
- data tokens、truncation/packing rate。

### 可复现性

- uninterrupted vs resume 的 batch/LR/loss/parameter digest；
- 同 path fresh-repeat token/logit/capture identity；
- code/config/data/tokenizer/base/adapter/checkpoint hashes；
- environment、driver、GPU、backend、dtype 与 flags；
- 多 seed 的 mean/std/confidence interval（若要声称统计稳定性）。

### 数值比较

- exact equality：元素或 digest 完全相同；
- `max_abs`、`mean_abs`、RMS error；
- relative error，但接近 0 时需单独处理；
- differing element count/density；
- cosine similarity 只反映方向，可能掩盖局部关键差异；
- top-1/top-2 logit margin、rank/argmax；
- token exact match、decoded exact match；
- 最终 task/safety metrics。

### 推荐 gates

```text
finite gate: loss/grad/weights/logits all finite
resource gate: peak memory and elapsed/throughput within preregistered cap
resume gate: interrupted path reproduces registered continuation
repeat gate: each path is stable before cross-path attribution
isolation gate: one factor changed, other identities locked
task gate: numerical change cannot be promoted without quality/safety eval
artifact gate: attached/merged are separate candidate identities
```

## 6. 常见失败与排障

| 症状 | 常见原因 | 排障/修复 |
|---|---|---|
| `.grad` 越来越大 | 忘记 zero gradients 或 accumulation 边界错误 | 对账 micro-step/optimizer-step，`set_to_none=True` |
| loss 是 NaN | 输入/label 错、LR 高、overflow、全 mask softmax | 先找首个非 finite tensor/step，不只降低 LR |
| FP16 step 被跳过 | gradient overflow | 看 scaler、grad norm、异常 batch；动态调 scale |
| clipping 无效 | AMP 下未先 unscale | unscale 后再 global-norm clip |
| accumulation 后结果变化 | loss 归一化、dropout、scheduler/clipping 时点不同 | 按 supervised tokens 对账，锁 step 语义 |
| resume 后立即漂移 | 漏 optimizer/scheduler/RNG/sampler/accumulation state | 用 uninterrupted vs resume 小实验逐项 digest |
| 显存逐步上涨 | 保留带 graph tensor、缓存无限增长 | `detach/item` 后记录，检查容器与 hooks 生命周期 |
| reserved 高、allocated 低 | allocator caching/fragmentation | 先检查动态 shape/live tensor，再考虑 allocator 配置 |
| 同权重输出不同 | dtype/backend/mode/template/cache/adapter form 不同 | 建完整 identity ledger，fresh repeats 后单变量 control |
| module hook 首先看到差异 | 前面有未注册 functional op 或历史 cache 已不同 | 只称“first registered boundary”，扩 plan/做 intervention |
| merged 与 attached 不同 | materialization rounding、operation grouping、mode/config | 分离 dtype 与 form，比较 weights、local replay、full eval |
| 单次 FP32 更快 | warmup/噪声/频率/缓存差异 | 不宣称 speedup；增加独立重复和 latency distribution |

## 7. 与相邻概念比较

| 概念 A | 概念 B | 关键区别 |
|---|---|---|
| AdamW weight decay | L2 penalty | AdamW 与自适应梯度缩放解耦；L2 进入梯度后会被缩放 |
| gradient accumulation | activation checkpointing | 前者拆 batch 累积梯度；后者重算 activation 省单步显存 |
| activation checkpoint | training checkpoint | 前者是 step 内重算；后者是磁盘恢复状态 |
| BF16 | FP16 | BF16 范围大、精度粗；FP16 范围小、fraction 更多 |
| TF32 | FP32 storage | TF32 是特定 matmul 计算路径，不等于把 tensor 存成 TF32 |
| AMP | Adapter autocast dtype | AMP 控制算子混合精度；后者是 Adapter load-time dtype policy |
| repeatability | reproducibility | 前者同环境同路径；后者独立环境按合同复现 |
| deterministic | accurate | 稳定地重复错误仍是 deterministic，不代表正确 |
| exact equality | tolerance closeness | 前者 bit/值完全相同；后者只在阈值内接近 |
| attached LoRA | merged LoRA | 前者运行时 base+低秩分支；后者先把 delta 物化进权重 |
| observed boundary | root cause | 前者是测量计划中的差异位置；后者需要干预/排除替代解释 |

## 8. 高频问题与分层答案

### Q1：PyTorch autograd 和训练 step 如何工作？

**30 秒答案**

Forward 动态记录需要求导的运算；标量 loss backward 用 reverse-mode chain rule
计算每个 leaf parameter 的梯度并累加到 `.grad`。一个 optimizer step 前要清梯度，
forward/backward，AMP 时先 unscale，再 clipping，最后 optimizer 和 scheduler step。

**2 分钟展开**

补充矩阵乘 backward、graph 释放、detach/in-place、gradient accumulation 边界，
以及为什么 scheduler 按 optimizer step 计数。

**深挖要点**

- vector-Jacobian product；
- custom autograd function 的 forward/backward 验证；
- checkpoint recomputation 与 RNG；
- distributed accumulation 的 synchronization 时点。

### Q2：为什么大模型训练常选 BF16，而不是 FP16 或 FP32？

**30 秒答案**

BF16 与 FP32 都有 8-bit exponent，动态范围大，训练时比 FP16 少依赖 loss scaling；
同时它只用 16 bits，显存和带宽优于 FP32。代价是 fraction 只有 7 bits，舍入误差
更大，所以 normalization、reduction、optimizer state 和数值边界仍需管理。

**2 分钟展开**

对比 exponent/fraction、AMP op policy、FP32 optimizer moments，强调 storage dtype
不等于所有 internal compute dtype，并举 near-tie logits 或小 LoRA update 被吸收的
例子。

**深挖要点**

- FP16 dynamic loss scaling；
- BF16 accumulation dtype；
- TF32 与禁用 TF32 的诊断意义；
- stochastic rounding 的作用与验证。

### Q3：gradient accumulation 与 checkpointing 如何省显存？

**30 秒答案**

Accumulation 用多个小 micro-batches 累加梯度，降低单次 activation 峰值但保持较大
effective batch；activation checkpointing 不保存部分中间值，backward 时重算，
直接用计算换 activation 显存。二者可组合，但都降低吞吐并增加正确性条件。

**2 分钟展开**

给出 effective batch 公式，解释 loss 除以 accumulation steps、变长 token normalization、
optimizer/scheduler/clipping 时点；再解释 checkpoint segment 与 RNG preservation。

**深挖要点**

- 为什么 accumulation 不总与大 batch 等价；
- DDP `no_sync` 的意义；
- checkpoint 粒度如何影响重算和峰值；
- 如何实测 memory/throughput Pareto curve。

### Q4：如何让训练可恢复且可复现？

**30 秒答案**

不仅保存模型，还要保存 optimizer、scheduler、scaler、global step、sampler/data
position、所有 RNG 和 accumulation phase，并绑定 code/data/tokenizer/config。用
uninterrupted 与 interrupt-resume 的小实验逐步比较 batch、LR、loss 和参数 digest。

**2 分钟展开**

补充原子写、manifest/hash、last-known-good、distributed shard closure 和环境锁定；
区分同机 repeatability、跨机 reproducibility 与多 seed statistical stability。

**深挖要点**

- worker RNG 与 prefetch；
- mid-window checkpoint 如何处理 gradients；
- library/kernel nondeterminism；
- 为什么 hash 一致只能证明内容一致，不能自动证明来源可信。

### Q5：你如何诊断本项目 BF16 merge drift？

**30 秒答案**

先证明 BF16 attached 和 merged 各自 fresh-repeat 稳定，再定位到 `eval-001` index 45
的 raw-logit argmax flip。之后用同 dtype FP32 attached/merged 隔离 execution form，
再固定 attached 比 BF16/FP32 隔离 dtype；两组都采用 ABBA fresh lifecycle。hooks
和 replay 只支持预注册边界内的 execution-form/dtype effect，没有把首个观察差异
夸成唯一 CUDA root cause。

**2 分钟展开**

说明 BF16 merge 中很多非零 delta 被舍入回 base，但 actual merge 与 PEFT 算法一致；
FP32 attached/merged 在 `q_proj` 首先出现注册差异但 token 相同；attached BF16/FP32
在 `input_layernorm` 出现注册差异，同值 RMSNorm control 可复现。强调 FP32 是 widen
BF16 checkpoint values，不是 pristine FP32。

**深挖要点**

- attached/merged 两个公式的 operation grouping；
- ABBA 控制了什么、没控制什么；
- raw logits vs processed scores；
- 为什么局部 control 未证明 downstream causal propagation；
- 何时才允许 full eval、merge artifact 或 Runtime promotion。

## 9. 本项目映射与证据边界

### `[本仓库已实现]`

- LoRA SFT v1/v2 均使用 BF16 base training path，Adapter 为独立 artifact；冻结
  config 包含 optimizer steps、batch/accumulation、LR、cosine/warmup、seed、显存、
  train/validation loss 与 artifact digest。
- v1：`micro batch=2`、`accumulation=4`、effective batch `8`，5 epochs/100
  optimizer steps；v2 保持相同 batch/LR policy，3 epochs/66 steps。两次峰值 allocated
  GPU memory 均为 `5,217,494,016` bytes。
- 项目完成了 BF16 attached/merged、FP32 attached/merged、attached BF16/FP32 的
  fresh-repeat、ABBA、logit、module-boundary 和 standalone RMSNorm control；相关
  claim boundary 均冻结在 evidence 中。
- FP32 attached full eval 只做一次预注册 20-case run；峰值显存相对 BF16 reference
  为 `1.989608741...x`。单次 elapsed ratio 小于 1 被明确禁止解释为稳定 speedup。
- 当前 preferred candidate 身份包含 fixed compiler、FP32 attached execution form
  和资源上限；merged artifact、serving 与 Runtime readiness 仍为 false。

冻结证据入口：[BF16 merge numerics](../../FC-MVP-001-bf16-merge-numerics-v1.md)、
[FP32 attached/merge numerics](../../FC-MVP-001-fp32-attached-merge-numerics-v1.md)、
[attached dtype isolation](../../FC-MVP-001-attached-dtype-isolation-v1.md)、
[attached dtype boundary control](../../FC-MVP-001-attached-dtype-boundary-control-v1.md)。

### `[本仓库待实施]`

- Tiny Transformer 的完整 pretraining、checkpoint/resume 对照与系统 profiling lab；
- 大规模多 seed、不同 hardware/backend 的统计复现；
- DDP/FSDP/ZeRO、kernel 和正式 serving 性能工作；
- LoRA vs QLoRA、rank/alpha/target-module 系统消融。

可以说“我做过可证伪的低精度与 Adapter execution-form 数值诊断”；不能说“证明了
PEFT/CUDA 有 bug”“FP32 修复了所有输出”或“完成了大规模训练系统”。

## 10. 自测题与实践

### 白板自测

1. 推导 `Y=XW` 对 `X/W` 的梯度。
2. 写出 AdamW 的 moments、bias correction 与 decoupled decay。
3. `micro_batch=2, accumulation=8, world_size=4` 的 effective batch 是多少？哪些
   条件会让它不等价于一次大 batch？
4. 为什么 FP16 常需 loss scaling，而 BF16 通常不需要？
5. 列出一个 exact-resume checkpoint 的所有状态。
6. 给出 training memory ledger，说明 LoRA 减少了什么、没有减少什么。
7. 为什么 `empty_cache()` 通常不能修复真实 OOM？
8. 解释 ABBA control 的价值和局限。
9. 为什么首个 registered unequal module 不是 unique root cause？
10. attached 与 merged LoRA 在实数中等价，为什么浮点中可能不同？

### 最小实践

- 手写一个 linear regression training loop，用 finite difference 检查 autograd
  gradient；
- 比较一个大 batch 与 accumulation，在关闭 dropout 时逐步比较 gradients/weights，
  再打开 dropout 解释差异；
- 做 uninterrupted 20 steps 与 10+resume+10 steps 的 exact-resume test；
- 在 FP32/FP16/BF16 上构造大数加小增量，观察 absorption/overflow/underflow；
- 对相同矩阵计算 `(xA)B` 与 `x(BA)`，记录 exact/max/RMS difference；
- 设计 A/B、ABBA fresh lifecycle probe，分别报告 within-path repeat 与 cross-path
  difference；
- 用 profiler 比较 prefill-like 大矩阵和 decode-like 窄矩阵的 compute/带宽特征；
- 故意保留带 graph 的 loss tensor，复现显存增长并用引用生命周期修复。

### 掌握标准

- 能从公式讲到可运行的训练 step，并准确说明每个状态的生命周期；
- 能在 OOM/NaN/漂移时先建立证据，不靠随机改超参数；
- 能区分 dtype storage、compute、accumulation 和 returned tensor dtype；
- 能把本项目数值故事讲成控制变量与 claim boundary，而不是“换 FP32 就好了”；
- 能明确哪些结果只来自单 case/单 run，哪些才支持 full-eval 或跨机结论。
