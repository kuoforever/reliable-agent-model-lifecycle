# 03｜后训练、PEFT、蒸馏与 Alignment

> 本章是面试学习材料，不是项目进度 tracker。项目当前状态只以根目录
> `PROJECT_STATUS.md` 为准。

证据标签：`[原理]` 表示通用理论；`[通用工程]` 表示可迁移的方法；
`[本仓库已实现]` 只表示已有冻结代码、测试、指标与 artifact；
`[本仓库待实施]` 表示 roadmap。特别是 QLoRA、distillation、Reward Model、
RLHF、DPO、ORPO、KTO、GRPO 在本仓库尚未完成，不能写成项目经历。

## 1. 面试定位与学习目标

后训练不是“选一个流行 acronym”。正确流程是先定义行为缺口和可用监督信号，再
选择最小、可评测、可回滚的方法。

完成本章后，应能：

- `[原理]` 区分 Continued Pretraining（CPT）与 Supervised Fine-Tuning（SFT）；
- `[通用工程]` 正确构造 chat template、assistant-only loss mask、EOS 和 packing；
- `[原理]` 推导 LoRA 的低秩更新、trainable parameter count、rank/alpha/target
  modules trade-off；
- `[原理]` 解释 QLoRA、NF4、double quantization 到底量化了什么；
- `[通用工程]` 把 attached Adapter 与 merged weights 当成两个需独立验证的 artifact
  形态；
- `[原理]` 比较 sequence/logits/feature distillation；
- `[原理]` 讲清 Reward Model、RLHF/PPO、DPO、ORPO、KTO、GRPO 所需数据和优化
  目标；
- `[通用工程]` 为一个真实问题选择 CPT/SFT/LoRA/QLoRA/DPO/GRPO，并定义 baseline、
  eval、safety 与 resource gates；
- `[本仓库已实现]` 用精确边界讲 Tool Router Base→LoRA v1→safety repair v2→
  decision compiler，而不把 planned alignment 写成已完成。

先记住一个面试决策树：

```text
缺领域语言/知识分布？             -> CPT，再做 instruction eval
缺格式、工具调用或任务示范？       -> SFT
显存有限、需多任务 Adapter？        -> LoRA；base 仍太大时考虑 QLoRA
要把大模型行为迁移到小模型？       -> distillation
有成对偏好、希望离线直接优化？      -> DPO；也可比较 ORPO
只有 desirable/undesirable 单样本？ -> KTO 一类 unpaired preference 方法
有可在线计算、抗投机的 verifiable reward？ -> GRPO/RL
需要学习通用人工偏好 reward 并在线探索？   -> RM + RLHF/PPO，成本最高
```

## 2. 原理：不同监督信号如何改变模型

### 2.1 CPT 与 SFT

#### Continued Pretraining

`[原理]` CPT 在已有 base model 上继续 next-token prediction：

```text
L_CPT = - sum_t log pi_theta(x_t | x_<t)
```

数据多为领域原始文本、代码或多语语料，无需 instruction/answer pair。它主要改变
模型对数据分布、术语、文体和知识模式的建模。风险包括：

- catastrophic forgetting：领域数据过窄导致通用能力退化；
- 数据许可证、PII、低质重复与 eval contamination；
- 只会续写领域文本，不自动等于会遵循指令；
- 新事实是否可靠写入参数难以验证。

常见控制：混入 general replay data、较低 LR、较短训练、按 token 记录配比、固定
通用与领域 eval、检查 memorization/污染。

#### Supervised Fine-Tuning

`[原理]` SFT 使用 `(instruction/context, target response)`。模型仍做 Causal LM，
但 loss 通常只放在 target tokens：

```text
L_SFT = - sum_(t in assistant target) log pi_theta(y_t | x, y_<t)
```

SFT 更适合学习 chat behavior、输出格式、tool schema、拒绝/澄清策略和任务示范。
它能教“怎么回答”，但有限样本不适合承担大量新知识注入，也不能自动优化开放式
人类偏好。

#### 核心比较

| 维度 | CPT | SFT |
|---|---|---|
| 数据 | 原始 token stream | instruction/context + response |
| loss | 通常所有有效 token | 通常 assistant/target tokens |
| 主要目标 | 适应领域分布/知识/语言 | 学习任务、格式、行为 |
| 关键风险 | 遗忘、版权/PII、污染 | 模板错、label leakage、过拟合、行为偏置 |
| eval | domain LM + downstream + general retention | task/format/safety + general regression |
| 常见顺序 | CPT → SFT | 可直接从 instruct/base 做 SFT |

### 2.2 Chat template、loss mask 与 packing

`[通用工程]` Chat template 把结构化 messages 变成实际 token stream，例如 system、
user、assistant、tool 的 role delimiters。它是模型输入合同，不是展示层。训练和推理
template、special tokens、是否添加 generation prompt 必须一致。

一个样本的 token-level audit 应包含：

```text
token_id | decoded_piece | role | attention_valid | loss_label | supervised?
```

常见 assistant-only mask：system/user/tool schema token label 设为 ignore index，
assistant target JSON 及终止 token 参与 loss。需要显式决定多轮对话中是否监督所有
assistant turns，还是只监督最后一轮。

`[原理]` Packing 把多个短样本放进固定长度序列，减少 padding。它有两种语义：

1. concatenated causal stream：后一个样本可 attention 到前一个样本；实现简单，
   但产生跨样本条件信息；
2. block-diagonal/document mask：每个样本仅看自身 prefix；语义更干净，但 backend
   与 position handling 更复杂。

无论哪种，都要：

- 插入正确 EOS/边界，不能让 answer 与下一 instruction 粘连；
- 每段重新计算 loss mask，避免 prompt token 被监督；
- 明确 position IDs 是否连续或 reset，并与模型/backend 支持一致；
- 按 original example/family 划分 train/validation/eval 后再 packing，不能先拼再切；
- 记录 truncation，尤其防止只截掉答案尾部或安全拒绝字段。

### 2.3 LoRA 数学

`[原理]` 对 frozen linear weight：

```text
W_0 in R^(d_out x d_in)
```

LoRA 不直接训练完整 `Delta W`，而令：

```text
Delta W = s * B A
A in R^(r x d_in)
B in R^(d_out x r)
s = alpha / r                 # 经典 LoRA 常见 scaling
y = x W_0^T + s * x A^T B^T
```

`r << min(d_in,d_out)`。单层 trainable parameter count 为：

```text
r * d_in + d_out * r = r(d_in+d_out)
```

相对 full matrix `d_out*d_in` 大幅减少。实现常随机初始化 `A`、零初始化 `B`，使初始
`Delta W=0`，模型一开始保持 base behavior。具体初始化/scaling 需以所用实现和
冻结 config 为准；某些变体使用不同 scaling，不能仅凭“LoRA”二字假设。

#### rank、alpha、dropout

- `rank r`：低秩容量。更大不必然更好，会增加参数、optimizer state、过拟合风险；
- `alpha`：与 rank 一起决定 scaling。比较 rank 时必须说明 alpha 是否固定、
  `alpha/r` 是否恒定；
- LoRA dropout：只作用于 adapter branch 输入；eval 时必须关闭；
- target modules：决定把容量放在哪里，通常比只调 rank 更重要。

#### target modules

常见选择：

- `q_proj/v_proj`：参数少，常见起点；
- `q/k/v/o_proj`：覆盖整个 attention projection；
- 再加 MLP `gate/up/down_proj`：容量更强、参数和成本更高；
- embedding/LM head：词表/格式适配可能有价值，但 artifact 和 tied weights 更复杂。

不要只按名称匹配后就训练；启动时输出匹配模块列表、shape、trainable parameter
count，并 fail closed 处理零匹配或意外大范围匹配。

### 2.4 QLoRA、NF4 与 double quantization

`[原理]` QLoRA 的核心不是“训练 4-bit LoRA”。它通常：

1. 把 frozen base weights 以 4-bit 形式存储；
2. forward 时按 block dequantize 到 BF16/FP16 等 compute dtype 做矩阵运算；
3. LoRA Adapter 参数与 optimizer states 保持较高精度并参与训练；
4. gradient 通过 dequantized operation 流到 LoRA，不更新 quantized base。

NF4（NormalFloat4）为近似正态分布权重设计非均匀 4-bit codebook，使有限 quantization
levels 更匹配 pretrained weight distribution。它不是任意 activation 的通用无损
压缩，也不意味着每个权重恰好只占 0.5 byte：还存在 block scales、metadata、
padding 和运行时 workspace。

Double quantization 再量化第一层 quantization 的 scale/constant，进一步减少 scale
overhead。它降低 storage，不消除 dequant compute、quantization error 或 kernel
compatibility 风险。

QLoRA 的价值：在有限显存上训练较大 base 的 Adapter。风险：

- base quantization 引入额外误差，可能影响敏感任务；
- kernel/硬件/backend compatibility 与吞吐不一定优于 BF16 LoRA；
- merge/export 时必须定义是 dequant 后 merge、重新量化，还是继续 attached；
- 需要与 BF16 LoRA 在相同数据、steps、eval 和资源口径下对照。

### 2.5 Attached 与 merged Adapter

`[原理]` Attached inference 保留两条计算分支：

```text
y = x W_0^T + s * x A^T B^T
```

Merged inference 先物化：

```text
W_merged = cast_or_round(W_0 + s*BA)
y = x W_merged^T
```

两者实数代数等价，浮点执行图不必 bitwise 等价。Attached 的优点是 Adapter 小、
可切换、base 共用；缺点是额外算子与 serving 管理。Merged 的优点是单权重图，
但 artifact 大、切换不灵活，merge dtype/rounding 可能改变输出。

`[通用工程]` merge 不是“文件格式转换”，而是产生新 candidate identity。至少重做：

- parameter inventory：LoRA tensors 是否完全消失，base/tied weights 是否正确；
- weight-level audit：expected delta/merged weights 与 actual 比较；
- fresh attached/merged repeat；
- raw logits/token/task/safety full eval；
- artifact manifest、load test、资源和 serving benchmark。

### 2.6 Distillation

设 teacher 为 `p_T`，student 为 `p_S`。

#### Sequence-level / output distillation

`[原理]` Teacher 生成完整 response，student 把它当 SFT target：

```text
L_seq = - sum_t log p_S(y_teacher,t | x, y_teacher,<t)
```

优点是适用于只能访问文本 API 的 teacher，数据管线简单；缺点是丢失候选 token 的
dark knowledge，teacher 错误、风格和安全缺陷会直接复制。需要保留 teacher model/
prompt/decoding/provenance、过滤理由和 licensing/usage 边界。

#### Logits distillation

`[原理]` 对 temperature `tau`：

```text
q_T = softmax(z_T / tau)
q_S = softmax(z_S / tau)
L_KD = tau^2 * KL(q_T || q_S)
L = lambda * L_hard + (1-lambda) * L_KD
```

`tau^2` 用于补偿 soft target 梯度随 temperature 缩放。Teacher/student vocabulary、
Tokenizer 或序列对齐不同时，逐 token logits distillation 并不直接成立。全 vocab
logits 存储极大，可只存 top-k logits 加 residual mass，但这是近似且必须验证。

#### Feature distillation

`[原理]` 对齐中间 hidden/attention feature：

```text
L_feat = || P(h_S) - h_T ||_2^2
```

`P` 把 student hidden dimension 投影到 teacher dimension。它提供更密集监督，但需
选择 layer mapping、normalization 和 representation，架构差异大时不稳定，且通常
要求本地访问 teacher internals。

Distillation 的真正 baseline 应是同规模 student 的普通 SFT；只拿 student 对比大
teacher，无法证明 distillation 带来增益。

### 2.7 Preference data 与 Reward Model

成对偏好样本：

```text
(x, y_w, y_l)
```

`y_w` 是 chosen/winner，`y_l` 是 rejected/loser。数据必须定义 preference rubric，
处理 tie、annotator disagreement、position/order bias、长度偏差和 safety policy。

`[原理]` 标量 Reward Model `r_phi(x,y)` 常用 Bradley-Terry pairwise loss：

```text
P(y_w > y_l | x) = sigmoid(r_phi(x,y_w) - r_phi(x,y_l))
L_RM = -log sigmoid(r_w - r_l)
```

它学的是相对排序，不自动具有跨 prompt 可比的绝对刻度。要看 pairwise accuracy、
按 slice 的 calibration/ranking、长度相关性和 adversarial reward hacking。RM 不是
Runtime verifier：高 reward 也不等于动作已被环境证明成功。

### 2.8 RLHF / PPO

`[原理]` 经典 RLHF 流程：SFT policy → preference data → Reward Model → online
rollouts → PPO-style policy optimization。概念目标：

```text
maximize E_[y~pi_theta(.|x)] [ r_phi(x,y)
                               - beta * KL(pi_theta(.|x) || pi_ref(.|x)) ]
```

reward 推动偏好，KL 项约束 policy 不要远离 reference。PPO 还需 old policy ratio、
advantage、clipping 和通常的 value/critic：

```text
rho_t = pi_theta(a_t|s_t) / pi_old(a_t|s_t)
L_clip = -E[min(rho_t A_t, clip(rho_t,1-eps,1+eps) A_t)]
```

`A_t` 是 advantage。工程成本高：policy/reference/reward/critic、多轮 generation、
变长序列、reward/KL/advantage 计算、分布式 rollout 与训练不同步。主要风险是 reward
hacking、KL collapse、mode collapse、长度投机和 RM distribution shift。

### 2.9 DPO

`[原理]` Direct Preference Optimization 直接用 preference pairs 优化 policy，无需
显式训练 RM 或在线 PPO。设：

```text
Delta_theta = [log pi_theta(y_w|x) - log pi_theta(y_l|x)]
            - [log pi_ref(y_w|x)   - log pi_ref(y_l|x)]
L_DPO = -log sigmoid(beta * Delta_theta)
```

`pi_ref` 是冻结 reference，常为 SFT policy；`beta` 控制偏离 reference 的强度。
sequence log probability 是 assistant response token log-prob 之和（或实现规定的
归一化），必须对 chosen/rejected 使用一致 template、mask 和 truncation。

DPO 优点：离线、稳定、比 PPO 简单；局限：只能学习数据覆盖的 pairwise preference，
对 preference noise、长度偏差、reference identity、beta 敏感，不会在线探索新的
策略轨迹，也不能替代可执行环境验证。

### 2.10 ORPO

`[原理]` ORPO 类方法在一个训练阶段组合 chosen response 的 SFT likelihood 与
chosen-vs-rejected 的 odds-ratio preference penalty：

```text
L_ORPO = L_SFT(chosen) + lambda * L_OR(chosen, rejected)
```

`L_OR` 推高 chosen 相对 rejected 的 log-odds。其价值是无需单独 reference model，
训练管线较轻；但具体 sequence probability/odds normalization 是实现细节，必须以
所用算法定义为准。没有 reference 并不代表没有过拟合、长度偏差或 safety regression。

适合在相同 SFT+preference 数据上与“两阶段 SFT→DPO”做资源和质量对照，而不是因
少一个 model 就默认更好。

### 2.11 KTO

`[原理]` KTO 类方法面向不成对的 binary feedback：

```text
(x, y, label in {desirable, undesirable})
```

常以 policy/reference log-ratio：

```text
r_theta(x,y) = log pi_theta(y|x) - log pi_ref(y|x)
```

相对一个 KL-derived baseline 构造 prospect-theory 风格 value：desirable 样本希望
`r_theta` 高于 baseline，undesirable 希望低于 baseline，并对两类设置权重。具体
baseline、normalization 与 loss 以选定实现/论文合同为准。

优势是能利用 thumbs-up/down 或 moderation label，无需人为配对；风险是 class
imbalance、不同 prompt 难度混杂、binary label 粗糙，以及隐式 pair 信号更弱。若
能得到高质量同 prompt pairs，DPO 往往是更直接的基线。

### 2.12 GRPO

`[原理]` Group Relative Policy Optimization 对同一 prompt 采样一组 `G` 个 response，
用组内 reward 形成相对 advantage，典型形式：

```text
A_i = (r_i - mean(r_1...r_G)) / (std(r_1...r_G) + epsilon)
rho_i,t = pi_theta(token_i,t | prefix) / pi_old(token_i,t | prefix)
L_policy = -mean min(rho_i,t*A_i,
                     clip(rho_i,t,1-eps,1+eps)*A_i)
L = L_policy + beta * KL_to_reference
```

它通常不训练单独 value model，以组内相对 reward 代替 critic estimate，因而比某些
PPO 配置节省内存。但仍需要 rollout、old/reference policy 语义、reward、KL、group
sampling 和稳定训练，不是“无成本 RL”。

尤其适合数学、代码测试、schema/env outcome 等可验证 reward。若 reward 只检查
最终格式，模型会学会投机格式；若所有 group reward 相同，advantage 信号接近 0。
需要监控 reward variance、KL、entropy、response length、pass rate 与 hacking cases。

### 2.13 方法关系总表

| 方法 | 监督信号 | 是否在线 rollout | 是否需 reference | 是否需 RM/critic | 最适合 |
|---|---|---:|---:|---:|---|
| CPT | raw tokens | 否 | 否 | 否 | 领域分布适配 |
| SFT | gold responses | 否 | 否 | 否 | 指令、格式、技能示范 |
| LoRA/QLoRA | 参数化方式，不是新 loss | 取决于上层算法 | 取决于上层算法 | 取决于上层算法 | 低成本适配 |
| Distillation | teacher outputs/logits/features | 可离线 | teacher | 否 | 能力压缩/迁移 |
| RM | preference pairs | 否 | 否 | 训练 RM 本身 | 学习偏好评分 |
| RLHF/PPO | RM/env reward | 是 | 通常是 | RM + 常有 critic | 通用在线偏好优化 |
| DPO | preference pairs | 否 | 是 | 否 | 简洁稳定的离线 pair 优化 |
| ORPO | gold chosen + pairs | 否 | 否 | 否 | 单阶段 SFT+preference |
| KTO | binary feedback | 否 | 是 | 否 | 无天然 pair 的反馈 |
| GRPO | group reward | 是 | 通常是 | 无显式 critic | 可验证任务的在线相对优化 |

## 3. 应用与选型 trade-off

### 3.1 先诊断问题，不先选算法

| 观察到的问题 | 首选起点 | 不应直接跳到 |
|---|---|---|
| 不懂领域术语/代码分布 | 检索 baseline；确认需参数化后做小规模 CPT | RLHF |
| 知道内容但不按 JSON/tool schema 输出 | 高质量 SFT + constrained decoding/validator | CPT |
| 少量任务、显存有限 | LoRA SFT | full fine-tuning |
| base weights 仍放不进显存 | QLoRA 对照 | 盲目缩短所有数据 |
| 大 teacher 好、小 student 弱 | sequence distill 起点；有 logits 再做 KD | preference RL |
| 同 prompt 有可靠 chosen/rejected | SFT baseline 后 DPO | 昂贵 PPO |
| 只有分散 thumbs-up/down | KTO 或先构造可靠 pairs | 假配对 DPO |
| 有单元测试/环境 outcome | GRPO/RL 对照，先防 reward hacking | 纯 RM 主观打分 |
| 安全决策要求可执行证据 | Runtime policy/verifier + frozen safety eval | 让 RM 直接授权动作 |

### 3.2 Full fine-tune、LoRA 与 QLoRA

| 维度 | Full FT | BF16 LoRA | QLoRA |
|---|---|---|---|
| trainable params | 全部 | 低秩 Adapter | 低秩 Adapter |
| base storage | 通常 16/32-bit | 通常 16-bit | 通常 4-bit + scales |
| optimizer state | 最大 | 仅 Adapter | 仅 Adapter |
| activation | 仍显著 | 仍显著 | 仍显著 |
| 容量 | 最大 | 受 rank/targets 约束 | 同 LoRA 且受量化误差影响 |
| artifact | 全模型 | 小 Adapter/可 merge | 小 Adapter + quantized base contract |
| 适合 | 有资源且需广泛改变 | 多任务、快速迭代 | 单卡显存严格受限 |

选 QLoRA 不能只报告“能跑”。要报告相对 BF16 LoRA 的 peak memory、step time、
quality/safety、adapter size、load/merge/serve behavior。

### 3.3 Alignment 方法选择原则

- 数据只有几千个高质量 demonstration：先 SFT，别用 RL 放大噪声；
- preference pairs 高质量但无在线环境：DPO 是强基线；
- chosen response 同时是可靠 gold：比较 ORPO 与 SFT→DPO；
- 只有独立 binary feedback：考虑 KTO，但先检查 label calibration 与 class balance；
- reward 能被程序或环境验证：GRPO 有意义，但必须做 exploit tests；
- reward 主观、任务开放且需要探索：RM+RLHF/PPO 可表达更广，成本与风险也最高；
- Tool/GUI Agent 的 reward 应由实际 post-state/verifier 提供，不能相信模型 self-report。

## 4. 工程实现

### 4.1 SFT data pipeline

```text
source inventory/license/consent
 -> normalize + redact PII
 -> exact/near duplicate grouping
 -> split by task family/source before augmentation
 -> render frozen chat template
 -> tokenize and construct assistant-only labels
 -> length/truncation/packing audit
 -> immutable dataset manifest + hashes
 -> train/validation only iteration
 -> one frozen eval protocol
```

PyTorch/HF 风格伪代码：

```python
def encode_sft(example, tokenizer, template, max_length):
    rendered, role_spans = template.render_with_spans(example["messages"])
    ids, offsets = tokenizer_with_offsets(rendered)
    labels = [IGNORE_INDEX] * len(ids)

    for span in assistant_target_spans(role_spans):
        for token_index in tokens_overlapping(offsets, span):
            labels[token_index] = ids[token_index]

    ids, labels = truncate_with_locked_policy(ids, labels, max_length)
    assert at_least_one_supervised_token(labels)
    return {"input_ids": ids, "labels": labels}
```

模板/Tokenizer 未必提供稳定 character offsets，因此实际实现也可逐 message tokenization
后拼接；关键是用 golden cases 对 token IDs 和 labels 做 exact test，而不是依赖肉眼。

### 4.2 LoRA 配置与启动审计

版本无关伪配置：

```python
lora = {
    "rank": 16,
    "alpha": 32,
    "dropout": 0.05,
    "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj"],
    "bias_policy": "none",
    "task": "causal_lm",
}

model = load_frozen_base(base_identity, training_dtype)
model = attach_lora(model, lora)

matched = audit_lora_modules(model)
assert matched.names == preregistered_target_names
assert count_trainable(model) == expected_trainable_parameters
assert all_frozen_except_adapter(model)
```

资源粗估：某个 target `d_out x d_in` 的 Adapter 参数为 `r(d_in+d_out)`；所有 target
求和后再乘 Adapter dtype bytes，得到 weight payload 下界。训练时还要加 gradients
与 Adam moments。Base frozen 不代表它不占 GPU memory，也不代表 activation 免费。

### 4.3 QLoRA pipeline

```python
quantized_base = load_base(
    identity=base_identity,
    weight_storage="4bit_nf4",
    compute_dtype="bf16",
    double_quant=True,
)
prepared = prepare_frozen_quantized_base_for_adapter_training(quantized_base)
model = attach_lora(prepared, lora_config)
assert base_parameters_are_frozen(model)
assert adapter_parameters_have_expected_dtype(model)
```

验证项：quantization config/hash、actual module inventory、base/adapter dtype、peak
allocated/reserved memory、throughput、finite loss/grad、checkpoint load、same frozen eval。
API 名称随库版本变化，上述仅表达合同，不是可直接复制的版本断言。

### 4.4 Merge 验证

```python
attached = fresh_load(base, adapter, dtype=locked_dtype, merge=False)
merged = fresh_load(base, adapter, dtype=locked_dtype, merge=True)

assert adapter_parameter_count(attached) == expected
assert adapter_parameter_count(merged) == 0
assert expected_merged_weight_matches_audited_actual(merged)

for case in frozen_eval:
    a = capture_tokens_logits_and_output(attached, case)
    m = capture_tokens_logits_and_output(merged, case)
    compare_under_preregistered_contract(a, m)
```

若目标是 bitwise/token identity，就不能在出现差异后改成宽松 tolerance 宣布 pass。
若目标是 task equivalence，也仍要单独报告 numerical/token differences，并重跑完整
quality/safety/resource gates。

### 4.5 Distillation loop

```python
with no_grad():
    teacher_logits, teacher_features = teacher(batch)

student_logits, student_features = student(batch)
hard = causal_lm_loss(student_logits, hard_labels, assistant_mask)
soft = kl_divergence(
    softmax(teacher_logits / tau),
    log_softmax(student_logits / tau),
) * (tau * tau)
feature = mse(project(student_features), teacher_features)
loss = w_hard * hard + w_soft * soft + w_feature * feature
```

正式实验要做 `hard-only student`、`sequence distill`、`logits KD` 等 ablation；teacher
必须 eval/no-grad，logits/token alignment 必须 exact。缓存 teacher logits 时绑定
teacher/checkpoint/prompt/tokenizer/dataset，并预算存储。

### 4.6 DPO loop

```python
chosen = encode(prompt, chosen_response, assistant_only=True)
rejected = encode(prompt, rejected_response, assistant_only=True)

theta_c = sequence_logprob(policy, chosen)
theta_r = sequence_logprob(policy, rejected)
with no_grad():
    ref_c = sequence_logprob(reference, chosen)
    ref_r = sequence_logprob(reference, rejected)

delta = (theta_c - theta_r) - (ref_c - ref_r)
loss = -logsigmoid(beta * delta).mean()
```

工程要点：chosen/rejected 共享完全相同 prompt tokens；只对 response tokens 求
logprob；truncation 不能不对称；reference identity 冻结；报告 chosen/rejected length
distribution、preference accuracy、KL proxy 和通用/safety regression。

### 4.7 RM + RL / GRPO loop

```text
sample prompts from frozen/controlled prompt distribution
 -> generate G responses with recorded policy/version/config
 -> score with environment/verifier/reward components
 -> retain raw component rewards and terminal evidence
 -> normalize/estimate advantages under locked method
 -> policy update with clipping + KL
 -> evaluate on separate deterministic and stochastic suites
 -> mine reward exploits, do not train on held-out answers
```

Reward 建议分解记录，而不是只留总分：format、task success、safety violation、cost、
latency、duplicate side effect。硬 safety violation 通常应 fail closed，不应让高 task
reward 抵消。

### 4.8 数据与评测前提

任何后训练方法比较前，至少锁定：

- base/reference/teacher/reward/verifier identities；
- train/validation/eval split，按 task family/source/user 隔离；
- exact/near duplicate 与 contamination audit；
- prompt/chat template、Tokenizer、max length、truncation、packing、loss normalization；
- hyperparameter search 预算和 checkpoint selection rule；
- eval 只读协议，不用 eval answers 生成 repair data；
- quality、safety、calibration、resource、artifact 与 reproducibility metrics；
- seed/hardware/software 和 raw predictions/rollouts。

后训练最常见的伪提升来自数据泄漏、模板变化、不同 decoding、挑 checkpoint/seed、
不同 retry 次数或只报告 aggregate metric。

## 5. Metrics 与 gates

### SFT/CPT

- train/validation token NLL、perplexity（同口径）；
- supervised token count、truncation、packing utilization；
- downstream task exact/F1/pass rate；
- general capability retention、catastrophic-forgetting slices；
- safety violations、false refusal、calibration；
- trainable params、peak memory、tokens/s、elapsed、artifact bytes。

### Tool Use

- JSON/schema/semantic validity；
- tool accuracy、argument exact match、field F1；
- dangerous action candidate/false approval；
- false refusal/fallback/rejection recall；
- duplicate action、unknown tool、unauthorized argument；
- raw 与 compiler/validator 后指标必须分开。

### Distillation

- student vs same-size no-distill baseline；
- task/safety retention 相对 teacher；
- hard-label CE、teacher-student KL、top-k agreement；
- latency、memory、throughput、model size 的真实收益；
- teacher error imitation 和 disagreement slices。

### Preference/RL

- held-out pairwise preference accuracy / win rate；
- reward mean/std/distribution，而非只看 mean；
- KL to reference、entropy、response length；
- policy ratio/clipping fraction、advantage/reward variance；
- task success、verifier pass、safety/cost violations；
- reward hacking/adversarial set；
- 多 seed confidence interval 与 baseline significance。

### Gate 顺序

```text
data gate
 -> training-health gate
 -> frozen task/safety eval
 -> regression slices
 -> artifact load/attached/merge gate
 -> resource/performance gate
 -> reproducibility gate
 -> only then promotion review
```

任何 aggregate improvement 都不能抵消 hard safety regression；模型 artifact、compiler、
prompt 和 execution form 共同构成 candidate identity。

## 6. 常见失败与排障

| 失败 | 原因 | 诊断/修复 |
|---|---|---|
| SFT loss 很低但输出错 | chat template/loss mask/shift 错 | token-level golden audit |
| 模型复述 user prompt | user tokens 被纳入 labels | 检查 ignore mask 与 role spans |
| 输出不结束 | EOS 未监督或 template 不一致 | 对账 target 尾部和 generation stop |
| packing 后指标掉 | 跨样本 attention、position/mask 错 | 单样本 vs packed exact test |
| validation 好、eval 异常高 | duplicate/family leakage | 以 source/family 聚类后重切 |
| LoRA 没学到 | target 零匹配、LR/rank 太小、labels 空 | audit modules/grad norms/supervised tokens |
| LoRA 过拟合 | 数据少、rank/epochs/LR 过大 | 预注册 early selection，扩真实 family 而非抄 eval |
| QLoRA 比 BF16 差 | quant error/backend/compute dtype | 同 config 对照，分离 storage 与 compute |
| merge 后输出变 | dtype materialization/执行图变化 | fresh repeat、weight audit、logits/full eval |
| KD 没收益 | teacher 不强、Tokenizer 不齐、tau/weights 错 | same-size baseline、alignment audit、ablation |
| DPO 只学会更长 | preference length bias、sequence sum | length slices/normalization 与 matched pairs |
| DPO 训练发散 | beta/LR、reference/mask 错、label noise | 检查 log-ratio 分布和 pair identity |
| RM accuracy 高但 RL 崩 | distribution shift/reward hacking | adversarial OOD、reward components、human/environment eval |
| GRPO reward 上升任务不升 | reward 可投机、group variance 弱 | exploit tests、真实 outcome verifier、reward ablation |
| safety 与 helpfulness 冲突 | hard negatives/threshold/rubric 不平衡 | 分开报 dangerous approval 与 false refusal，不用单一均值 |

排障时先验证 data/template/mask/reference identity，再看 optimization；不要用更复杂
alignment 算法掩盖基础 SFT pipeline 错误。

## 7. 与相邻概念比较

| 概念 A | 概念 B | 关键区别 |
|---|---|---|
| CPT | SFT | CPT 学 token 分布；SFT 学 instruction→response 行为 |
| PEFT | LoRA | PEFT 是参数高效方法总称；LoRA 是其中低秩更新方法 |
| LoRA | QLoRA | loss/adapter 可相同；QLoRA 额外量化 frozen base storage |
| rank | alpha | rank 决定低秩容量/参数量；alpha 参与更新 scaling |
| attached | merged | 运行时 factorized branch vs delta 预物化到 base weight |
| sequence KD | logits KD | 前者学 teacher 输出 token；后者学完整 soft distribution |
| feature KD | logits KD | 对齐中间 representation vs 输出分布 |
| RM | verifier | RM 近似偏好评分；verifier 应用明确证据判断结果/过程，边界更可审计 |
| RLHF/PPO | DPO | 在线 reward optimization + critic/rollout vs 离线 pairwise objective |
| DPO | ORPO | DPO 依赖 reference、常在 SFT 后；ORPO 合并 SFT 与 odds preference |
| DPO | KTO | paired chosen/rejected vs unpaired desirable/undesirable |
| PPO | GRPO | 常用 learned critic advantage vs group-relative reward、可不需 critic |
| outcome reward | process reward | 只看终局 vs 评价中间步骤；后者标注/防投机更难 |
| model safety score | Runtime authority | 模型信号是输入；policy/approval/environment evidence 才授权执行 |

## 8. 高频问题与分层答案

### Q1：CPT 和 SFT 怎么选？

**30 秒答案**

CPT 用原始领域 token 做 next-token training，解决领域分布、术语和语言模式；SFT
用 instruction-response 且通常只监督 assistant tokens，解决任务行为、格式和工具
使用。如果模型不懂领域先考虑检索/CPT，如果懂内容但不按 schema 做事就做 SFT。

**2 分钟展开**

补充数据规模、LR、general replay、catastrophic forgetting；SFT 的 chat template、
loss mask、packing；两者都必须做 contamination audit 和通用回归，常见顺序是
CPT→SFT。

**深挖要点**

- 参数化知识与 RAG 的更新/引用 trade-off；
- CPT 数据 mixture 和 token budget；
- SFT 多轮 loss policy；
- 如何证明领域提升不是 eval 泄漏。

### Q2：请推导 LoRA，并解释 rank/alpha/target modules

**30 秒答案**

LoRA 冻结 `W0`，学习 `DeltaW=(alpha/r)BA`，其中 `A` 是 `r×d_in`、`B` 是
`d_out×r`，参数从 `d_out*d_in` 降到 `r(d_in+d_out)`。rank 控制容量，alpha 控制
scaling，target modules 决定容量放在 attention 还是 MLP；三者需联合消融。

**2 分钟展开**

说明常见 A 随机/B 零初始化、dropout、q/v vs q/k/v/o vs MLP、optimizer state
节省，以及 attached/merged 的浮点执行图和 artifact trade-off。

**深挖要点**

- rank 改变时如何公平控制 scaling/steps；
- singular spectrum 与低秩假设；
- multiple adapters composition；
- 为什么 trainable params 少但 activation 仍大。

### Q3：QLoRA 为什么省显存？NF4/double quant 是什么？

**30 秒答案**

QLoRA 把 frozen base 以 4-bit 存储，计算时按 block dequantize 到 BF16/FP16，梯度
只更新较高精度 LoRA Adapter。NF4 的 codebook 针对近似正态权重，double quant
再压缩 quantization scales。主要省 base storage，不会消除 activation 或 Adapter
optimizer state。

**2 分钟展开**

补充 0.5 byte/parameter 只是下界，还有 scales/metadata/workspace；量化误差、kernel
兼容、吞吐、merge/requantize 都需与 BF16 LoRA 同 eval 对照。

**深挖要点**

- compute dtype vs storage dtype；
- block size/scale/outlier；
- dequantized matmul backward；
- QLoRA artifact 如何部署与复现。

### Q4：DPO 为什么不需要显式 Reward Model？

**30 秒答案**

DPO 用同 prompt 的 chosen/rejected pair，直接提高 policy 相对 reference 对 chosen
的 log-prob margin。loss 是 `-log sigmoid(beta*((logπc-logπr)-(logπref,c-logπref,r)))`。
它把 KL-regularized preference optimization 化为离线分类式目标，无需在线 PPO/RM。

**2 分钟展开**

说明 assistant-only sequence logprob、reference identity、beta、pair noise/length bias；
DPO 简单稳定但不在线探索，也无法超过数据与 preference rubric 的证据边界。

**深挖要点**

- reference-free 近似与标准 DPO 的区别；
- sequence sum/length normalization；
- label smoothing/IPO 等变体为何出现；
- KL、win rate 与 safety 如何联合监控。

### Q5：DPO、ORPO、KTO、GRPO 怎么选？

**30 秒答案**

有高质量同 prompt pairs，先做 DPO；想把 chosen SFT 与 preference 合成单阶段可对照
ORPO；只有独立好/坏标签用 KTO；有可在线计算的 verifiable reward，且能同 prompt
采样一组输出时考虑 GRPO。选择由数据形态和 reward 可验证性决定。

**2 分钟展开**

补充 reference model、online rollout、critic、group advantage、成本和 reward hacking；
所有方法都先需要 SFT/base baseline、独立 eval、多 seed 与 safety gates。

**深挖要点**

- group reward std 为 0；
- KTO class imbalance/KL baseline；
- ORPO odds 的实现口径；
- online policy staleness 与 rollout provenance。

### Q6：讲一个你做过的 LoRA 后训练闭环

**30 秒答案**

本项目先冻结 Qwen2.5-1.5B Tool Router base、数据和 20-case eval；BF16 LoRA v1 把
tool accuracy 从 `0.20` 提到 `0.80`，但仍有危险动作候选。我们只用冻结 bad cases
分类来设计 train/validation hard negatives，不复制 eval answers；v2 达到 `0.95`
tool accuracy、危险候选归零，但暴露字段冲突、false refusal 和 merge drift，因此
没有宣称 Runtime ready。

**2 分钟展开**

补充 v1 160/40、v2 176/48、eval 20 保持不变；`r=16, alpha=32`、Q/K/V/O、
assistant JSON-only loss；v1 validation epoch 3 最低但按预注册取 final，v2 基于既有
证据提前锁 3 epochs。离线 compiler 只派生冗余 flags，把 semantic validity 从
`0.85` 变为 `1.0`，不冒充模型改进；attached/merged 分开验证。

**深挖要点**

- 数据 family separation 和 leakage gate；
- 为什么 v2 argument exact 从 `0.35` 降到 `0.20` 仍不能只报 tool accuracy；
- compiler 如何 fail closed；
- 何时能进入 artifact/portable/Runtime promotion；
- 目前没有做 QLoRA/DPO/GRPO，下一实验如何设计。

## 9. 本项目映射与证据边界

### `[本仓库已实现]`

- Base：pinned `Qwen/Qwen2.5-1.5B-Instruct` 在冻结 20-case eval 上 JSON validity
  `1.0`，tool accuracy `0.20`，两条危险请求都产生危险动作候选；明确不具 Runtime
  eligibility。
- LoRA v1：冻结 160 train / 40 validation / 20 eval；BF16 LoRA，`r=16`、
  `alpha=32`、dropout `0.05`，targets 为 Q/K/V/O，sequence length 448，5 epochs，
  micro-batch 2、accumulation 4、LR `2e-4`、cosine/warmup `0.1`。loss 只作用于
  canonical assistant decision JSON；prompt 排除 category/split/example ID/gold。
- v1 有 `4,358,144` trainable parameters（`0.281521%`），tool accuracy `0.80`，
  argument exact `0.35`，但仍有一个 dangerous action candidate。validation loss 在
  epoch 3 最低，实验按事前合同保留 final epoch，没有看 eval 后倒选 checkpoint。
- Safety repair v2：只给 train/validation 新增 reviewed 16/8 examples，保持 eval
  digest 不变；训练锁 3 epochs/66 optimizer steps。tool accuracy `0.95`、危险动作
  candidate 归零，但 raw semantic validity `0.85`、三条 conflicting flags、三条
  false refusal，argument exact 由 v1 `0.35` 降为 `0.20`，所以仍不具 Runtime
  eligibility。
- Decision compiler：不改 raw model output，以 `selected_tool` 派生冗余 terminal
  fields；冻结 20-case semantic validity `0.85→1.00`、false refusals `3→0`，tool
  accuracy 保持 `0.95`。它是 candidate contract 的组成，不是模型能力提升。
- Attached/merge：独立 Adapter artifact、safe-merge verification 和后续 BF16/FP32
  数值诊断均已完成；当前 preferred offline candidate 明确限定为 FP32 attached +
  fixed compiler。Offline artifact eligibility 已建立，但独立机器 portable-package
  qualification 尚未完成；merged/serving/promotion/Runtime claims 保持 false。

冻结证据入口：[LoRA SFT v1](../../FC-MVP-001-lora-sft-v1.md)、
[LoRA SFT v2](../../FC-MVP-001-lora-sft-v2.md)、
[decision compilation](../../FC-MVP-001-decision-compilation-v1.md)、
[portable-package qualification protocol](../../FC-MVP-001-fp32-attached-portable-package-qualification-v1.md)。

### `[本仓库待实施]`

- CPT 与 catastrophic-forgetting 对照；
- QLoRA、LoRA-vs-QLoRA、rank/alpha/target modules 的系统 ablation；
- sequence/logits/feature distillation；
- preference dataset、Reward Model、RLHF/PPO、DPO、ORPO、KTO、GRPO；
- 多模态 post-training、verifier 与在线 Agentic RL；
- 生产 serving、量化部署与多 Adapter 热切换。

因此简历和面试可写“完成 LoRA SFT、bad-case-driven safety repair、独立评测、
compiler 与 Adapter 数值/artifact 诊断”；不能写“完成 QLoRA/DPO/GRPO/RLHF”或
“已部署生产 Runtime”。

## 10. 自测题与实践

### 白板自测

1. 同一个领域客服任务，什么时候选 RAG、CPT、SFT？分别如何评测？
2. 给出一段两轮 chat，逐 token 标出 assistant-only loss mask。
3. packing 为什么可能造成跨样本信息泄漏？block-diagonal mask 如何解决？
4. 对 `W:4096×4096, r=16`，LoRA trainable parameters 是多少？相对 full matrix
   占比多少？
5. rank 翻倍但 alpha 不变时，经典 `alpha/r` scaling 如何变化？怎样公平做 ablation？
6. 解释 NF4 与 double quantization；QLoRA 哪些内存没有省？
7. 推导 DPO loss 中 policy/reference 的四个 sequence log probabilities。
8. ORPO、KTO、GRPO 分别要求什么数据？
9. 为什么 RM pairwise accuracy 高不代表在线 policy 安全？
10. 为什么 merged Adapter 是新 candidate，而不是等价导出？

### 最小实践

- 做 20 个 chat examples 的 token/loss-mask 可视化，并为 role/EOS/truncation 写
  golden tests；
- 在固定小数据上对比 full FT、LoRA `r={4,16,64}`，记录 trainable params、显存、
  step time、validation/task metrics；
- 在同一 base/data/config 下对比 BF16 LoRA 与 NF4 QLoRA；
- 对一个 LoRA linear layer比较 attached 与 FP32/BF16 merged weights、outputs、
  logits margin；
- 用本地 teacher 生成 sequence targets，再加入 logits KL，必须保留 same-size
  hard-label-only baseline；
- 构造 100 个 chosen/rejected pairs，手算一个 batch 的 DPO log-ratio，检查
  chosen/rejected prompt tokens 完全相同；
- 从同一批偏好构造 paired DPO 与 unpaired KTO 输入，比较丢失了哪些信息；
- 为可执行小任务定义 GRPO reward，先写至少五种 reward-hacking tests，再训练；
- 做完整 experiment card：data/config/code/model hashes、seed、raw outputs、metrics、
  failure cases、claim boundary。

### 掌握标准

- 不看资料能画出 CPT/SFT/LoRA/QLoRA/DPO/GRPO 的数据与优化流；
- 能根据监督信号和风险选方法，而不是按流行度；
- 能检查 chat template、loss mask、packing、reference identity 这些高频工程错误；
- 能同时报告 quality、safety、resource 与 artifact trade-off；
- 能把本项目已经验证的 LoRA 闭环讲深，并主动声明所有 planned alignment 边界。
