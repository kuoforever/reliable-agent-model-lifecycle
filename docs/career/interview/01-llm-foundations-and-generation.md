# 01｜LLM 基础、Decoder-only Transformer 与生成

> 本章是面试学习材料，不是项目进度 tracker。项目当前状态只以根目录
> `PROJECT_STATUS.md` 为准。

证据标签：`[原理]` 表示可白板推导的通用原理；`[通用工程]` 表示可迁移的工程
方法；`[本仓库已实现]` 只指冻结代码、测试或报告已有证据的能力；
`[本仓库待实施]` 表示 roadmap/面试知识，不能写成项目经历。

## 1. 面试定位与学习目标

这一章要解决一个核心问题：给定一段文本，Decoder-only LLM 如何把它变成下一
token 的概率分布，并高效地连续生成结果？

完成后应能做到：

- `[原理]` 从 Tokenizer、Embedding、Transformer block 一直讲到 LM head、logits
  与 Causal LM loss；
- `[原理]` 在白板上标出 `Q/K/V`、attention score、mask、head 拼接的 tensor
  shape；
- `[原理]` 解释 MHA、MQA、GQA 的质量、显存与带宽 trade-off；
- `[原理]` 解释 RoPE、RMSNorm、SwiGLU 和 residual 分别解决什么问题；
- `[通用工程]` 区分 `prefill` 与 `decode`，估算 KV cache，并解释为什么 decode
  常受 memory bandwidth 限制；
- `[通用工程]` 为自然语言、创意采样、Tool Use/JSON 分别选择 decoding 策略；
- `[通用工程]` 说明“生成了合法 JSON”为什么不等于“语义、权限和动作安全均
  合法”。

一条适合面试开场的总数据流是：

```text
raw text
  -> tokenizer -> input_ids [B, T]
  -> token embedding (+ positional information) [B, T, d_model]
  -> N x decoder block [B, T, d_model]
  -> final norm -> LM head -> logits [B, T, V]
  -> logits processors / sampling -> next token [B, 1]
  -> append token and repeat, usually with KV cache
```

其中 `B` 是 batch size，`T` 是当前序列长度，`d_model` 是 hidden size，`V` 是
vocabulary size。

## 2. 原理：从文本到下一个 token

### 2.1 Tokenizer：模型看到的不是“词”

`[原理]` Tokenizer 将字符串映射为离散 token IDs。现代 LLM 常采用 byte-level
BPE、BPE 或 Unigram 一类 subword 方法，目标是在词表大小、序列长度、未知字符
覆盖和多语言公平性之间折中。

以 BPE 为例，训练时反复合并语料中高频相邻符号；推理时使用冻结的词表和 merge
规则分词。Tokenizer 本身不是神经网络 forward 的一部分，但它决定了：

- 相同字符串会变成多少 token，进而决定训练和推理成本；
- 数字、代码、中文、空格与 Unicode 边界如何表达；
- `BOS/EOS/PAD`、role delimiter、tool delimiter 等 special tokens 的 ID；
- 模型看到的 chat template 是否与训练时一致。

`[通用工程]` 必须把以下内容作为模型 artifact 的一部分绑定：Tokenizer 文件、
版本/哈希、special-token 映射、normalization 规则和 chat template。只固定权重而
不固定 Tokenizer，不能保证可复现。

常见误区：

- token 不等于英文单词，也不等于 Unicode 字符；
- `decode(encode(x))` 对规范化、空格或特殊 token 未必逐字节恒等；
- 新增 special token 后必须同步扩展 embedding/LM-head vocabulary；
- “上下文 8K”指 token 数，不是字符数。

### 2.2 Token Embedding 与位置

`[原理]` 设词表 embedding 矩阵为：

```text
E in R^(V x d_model)
H0 = E[input_ids] in R^(B x T x d_model)
```

embedding lookup 不是 one-hot 矩阵乘法的实际实现，但数学上等价。相同 token 在
lookup 后得到相同向量；其位置关系由位置编码注入。很多 Decoder-only 模型会
weight tying，即输出 LM head 使用 `E^T`：这减少参数量，并让输入与输出 token
空间共享表示，但二者仍承担不同计算角色。

绝对位置 embedding 直接把位置向量加到 token embedding；RoPE 则旋转 Q/K，
不是给 hidden state 简单相加。两者不能混为一谈。

### 2.3 Decoder-only Transformer block

设：

```text
B       batch size
T       sequence length
d       d_model / hidden size
h_q     query head count
h_kv    key/value head count
d_h     head dimension, normally d / h_q
d_ff    MLP intermediate size
```

典型 pre-norm block 可概括为：

```text
X1 = X + Attention(RMSNorm(X))
Y  = X1 + MLP(RMSNorm(X1))
```

`[原理]` residual 提供恒等信息路径和梯度通路；normalization 控制激活尺度；
attention 负责 token 间的信息混合；MLP 负责每个位置上的非线性通道变换。一个
block 的输入输出 shape 均为 `[B, T, d]`。

#### Q、K、V 到底是什么

对输入 `X in R^(B x T x d)`，先做线性投影：

```text
Q = X W_Q
K = X W_K
V = X W_V
```

在标准 MHA 中，把结果 reshape 为：

```text
Q, K, V: [B, h_q, T, d_h]
```

单个 head 的 scaled dot-product attention 为：

```text
S = Q K^T / sqrt(d_h) + M              [B, h_q, T, T]
P = softmax(S, dim=-1)                 [B, h_q, T, T]
O = P V                                [B, h_q, T, d_h]
```

变量含义：`S` 是 query 位置对 key 位置的匹配分数；除以 `sqrt(d_h)` 防止维度变大
时 dot product 方差过大、softmax 过度饱和；`M` 是 mask；`P` 是每行归一化后的
注意力权重；`O` 是对 value 的加权和。所有 head 拼接后：

```text
Concat(O_1, ..., O_h) in R^(B x T x d)
Attention(X) = Concat(O) W_O
```

直觉上，Q 是“当前位置要找什么”，K 是“各位置可按什么被匹配”，V 是“匹配后
真正取回的内容”。它们均由数据学习，不是人工指定的语义槽位。

#### Causal mask

`[原理]` 自回归训练时，第 `i` 个位置不能读取未来位置 `j > i`。加性 mask 通常为：

```text
M[i, j] = 0        if j <= i
M[i, j] = -inf     if j > i
```

softmax 后未来位置概率变为 0。还可能同时存在 padding mask。工程中需确认布尔
mask 的 True/False 语义、加性 mask 的 dtype，以及 SDPA/FlashAttention 对 mask
shape 和 causal flag 的约定；方向写反会造成训练泄漏或推理异常。

#### MHA、MQA、GQA

`[原理]` 三者差异主要在 K/V head 数量：

| 结构 | `h_q` | `h_kv` | KV cache | 主要 trade-off |
|---|---:|---:|---:|---|
| MHA | `h` | `h` | 最大 | 表达灵活，cache/带宽成本高 |
| MQA | `h` | `1` | 最小 | decode 高效，但共享 K/V 可能损失质量 |
| GQA | `h` | `1 < g < h` | 居中 | 常见的质量与吞吐折中 |

GQA 中多组 query heads 共享一组 K/V head。若 `h_q=32, h_kv=8`，每 4 个 query
heads 共享一对 K/V heads。它减少的主要是 KV cache 与 decode 带宽，并不按同样
比例减少 Q 投影或 MLP 计算。

#### RoPE：把相对位置写进 Q/K 的相位

`[原理]` Rotary Positional Embedding 对每对通道施加二维旋转。对位置 `p`、频率
`theta_i` 和二维向量 `(x_2i, x_2i+1)`：

```text
[x'_2i    ]   [ cos(p theta_i)  -sin(p theta_i) ] [x_2i    ]
[x'_(2i+1)] = [ sin(p theta_i)   cos(p theta_i) ] [x_(2i+1)]
```

旋转应用于 Q 和 K。由于旋转矩阵满足组合关系，`RoPE(q_p)^T RoPE(k_s)` 的相位
取决于相对位置 `p-s`。优势是无需训练绝对位置表且相对位置信息自然进入 attention
score；限制是超出训练上下文直接外推可能退化，需要谨慎使用 scaling/插值方案并
重新评测。

#### RMSNorm

`[原理]` 对 hidden vector `x in R^d`：

```text
rms(x) = sqrt((1/d) * sum_i x_i^2 + epsilon)
RMSNorm(x) = g elementwise_mul x / rms(x)
```

`g` 是可学习缩放，`epsilon` 防止除零。RMSNorm 不减均值；LayerNorm 还会中心化。
它计算更简单，但 dtype、归约次序和 kernel 实现仍可能带来数值差异。

#### SwiGLU / MLP

`[原理]` 常见 gated MLP：

```text
gate = SiLU(X W_gate)
up   = X W_up
H    = gate elementwise_mul up
MLP(X) = H W_down
```

shape 通常为：

```text
X:       [B, T, d]
gate/up: [B, T, d_ff]
output:  [B, T, d]
```

`SiLU(z)=z*sigmoid(z)`。与普通 `GELU(XW1)W2` 相比，SwiGLU 多一条投影和门控，
通常有更强表达能力，但参数与算力预算也不同。`d_ff` 不能只凭经典 Transformer
的 `4d` 假设，应读具体模型 config。

### 2.4 LM head、logits 与 Causal LM loss

`[原理]` 最后一层 hidden states 经过 final norm 和 LM head：

```text
Z = H W_vocab^T + b        [B, T, V]
p(y_t | y_<t) = softmax(Z[:, t-1, :])
```

`Z` 是 logits，不是概率；softmax 前可为任意实数。训练采用 teacher forcing：一次
并行计算整段序列，但 label 相对 input 向左移动一位。负对数似然为：

```text
L = -(1/N) * sum_(b,t in supervised positions)
        log softmax(Z[b,t,:])[label[b,t]]
```

`N` 是参与 loss 的 token 数。padding、用户 prompt、system/tool schema 等不希望
监督的 token 通常设为 ignore index，仅 assistant target token 参与 loss。模型
内部看到完整 causal prefix，但 loss mask 决定哪些位置贡献梯度。

Perplexity `PPL = exp(mean NLL)` 只是在同一 Tokenizer、同一数据与同一 masking
口径下有可比性。Tool Router 等结构化任务不能仅凭 PPL 判断是否可用。

### 2.5 生成策略

给定当前 logits `z_i`：

#### Greedy decoding

```text
token = argmax_i z_i
```

确定性强、易复现，适合 Tool Use、分类式输出和严格回归；缺点是不能表达多样性，
也不保证全序列的全局最优。

#### Temperature

```text
p_i = softmax(z_i / tau)
```

`tau > 1` 使分布更平，`0 < tau < 1` 更尖。严格说 `tau=0` 不应直接做除法；工程
通常把“temperature 0”路由到 greedy。

#### Top-k

只保留 logits 最大的 `k` 个 token，再归一化采样。`k` 是固定候选数，无法适应
分布有时尖锐、有时平坦的变化。

#### Top-p / nucleus sampling

按概率降序，保留累计概率首次达到 `p` 的最小 token 集合，再归一化采样。候选集
大小自适应。创意生成常把 temperature 与 top-p 组合；实验必须固定其处理顺序、
seed 和全部 logits processors。

`[通用工程]` 采样 seed 相同不必然跨设备、库版本或 kernel 得到相同结果；greedy
也可能因接近的 logits 边界和浮点差异产生 token flip。

### 2.6 KV cache、prefill 与 decode

`[原理]` 自回归第 `t` 步若每次重算全部历史，计算会大量重复。KV cache 保存每层
历史 token 的 K/V：新 token 只计算自己的 Q/K/V，Q 与历史 K 做 attention，再用
历史 V 聚合。

两个阶段：

- `prefill`：一次处理长度 `T_prompt` 的 prompt，构建每层 KV cache；矩阵较大、
  并行度高，通常更 compute-bound；
- `decode`：每次输入一个新 token，读取增长的 KV cache 并输出下一个 token；小
  batch 时矩阵窄且需反复搬运权重/cache，通常更 memory-bandwidth-bound。

不含 allocator 与 metadata 的 KV cache 粗略估算：

```text
bytes = B * T * L * 2 * h_kv * d_h * bytes_per_element
```

`L` 是层数，`2` 代表 K 和 V。例：`B=1, T=8192, L=28, h_kv=4,
d_h=128, BF16=2 bytes`，约为：

```text
1 * 8192 * 28 * 2 * 4 * 128 * 2 = 469,762,048 bytes ~= 448 MiB
```

实际还受 block/page 管理、对齐、并发序列和 cache dtype 影响。

KV cache 不保存最终 logits，也不是把所有 hidden states 简单保存下来。使用 cache
时 position IDs、cache position、mask 和序列截断必须同步，否则结果会漂移。

### 2.7 Structured generation 基础

`[通用工程]` 结构化输出可分三层：

1. prompt 约束：在 instruction 中给 schema/example；简单但无语法保证；
2. constrained decoding：用 JSON grammar、FSM 或 token mask 限制下一 token；能
   保证语法集合，但不能保证字段语义；
3. post-generation validator/compiler：解析 JSON，做 schema、交叉字段、registry、
   权限和业务不变量校验，必要时 fail closed。

例如 `{"selected_tool":"delete_file"}` 可以是合法 JSON，却可能违反 tool registry、
参数 schema、用户授权或 Runtime policy。模型 proposal 不是执行 authority。

## 3. 应用与选型 trade-off

| 场景 | 建议 | 为什么 | 主要风险 |
|---|---|---|---|
| Tool Router / JSON 决策 | greedy 或严格低随机性 + schema constrained decoding + 独立 validator | 可复现、便于逐例回归 | 接近 logit 边界仍可因数值变化 flip；语法合法不等于安全 |
| 事实问答 | 较低 temperature/top-p，结合检索与引用验证 | 降低随机性但保留表达空间 | 解码设置不能消除幻觉 |
| 创意写作 | temperature + top-p，可设重复惩罚 | 提升多样性 | 不易复现、可能跑题 |
| 长上下文服务 | GQA/MQA、paged KV cache、prefix caching | 降低 cache 和带宽成本 | 需验证质量、隔离租户 cache |
| 批量离线生成 | 大 prefill batch、长度分桶 | 提升硬件利用率 | padding 浪费与长尾阻塞 |
| 严格安全动作 | 模型只提议，确定性 compiler + Runtime policy/approval 执行 | 把模型不确定性隔离在受控边界 | 不可把 validator 当成完整权限系统 |

选择 attention/生成方案时先问四个问题：质量门槛是什么、上下文/并发多大、延迟
目标是 TTFT 还是 TPOT、输出错误的代价是什么。没有脱离工作负载的“最佳参数”。

## 4. 工程实现

### 4.1 最小 attention 伪代码

以下是 PyTorch 风格伪代码，表达数据流，不断言某个库版本的具体 API：

```python
def causal_attention(x, q_proj, k_proj, v_proj, o_proj, n_heads):
    # x: [B, T, d]
    b, t, d = x.shape
    d_h = d // n_heads

    q = q_proj(x).view(b, t, n_heads, d_h).transpose(1, 2)
    k = k_proj(x).view(b, t, n_heads, d_h).transpose(1, 2)
    v = v_proj(x).view(b, t, n_heads, d_h).transpose(1, 2)
    # q/k/v: [B, h, T, d_h]

    score = (q @ k.transpose(-2, -1)) / math.sqrt(d_h)
    # score: [B, h, T, T]
    future = torch.triu(
        torch.ones(t, t, dtype=torch.bool, device=x.device), diagonal=1
    )
    score = score.masked_fill(future, float("-inf"))
    prob = torch.softmax(score.float(), dim=-1).to(x.dtype)
    context = prob @ v
    context = context.transpose(1, 2).contiguous().view(b, t, d)
    return o_proj(context)
```

生产实现通常使用 fused SDPA/FlashAttention，而不是显式物化 `[T,T]` score。验证
自写实现时，应以小 shape 和高精度 reference 比较 forward、causal 性、backward，
并覆盖不同 mask、dtype、非连续 tensor 和极端 logits。

### 4.2 训练数据流伪代码

```python
text = render_chat(messages, frozen_template)
input_ids = tokenizer(text, add_special_tokens=locked_policy)
labels = input_ids.clone()
labels[not_assistant_target_positions] = IGNORE_INDEX

logits = model(input_ids).logits          # [B, T, V]
loss = cross_entropy(
    logits[:, :-1, :].reshape(-1, vocab_size),
    labels[:, 1:].reshape(-1),
    ignore_index=IGNORE_INDEX,
)
```

必须做一个人工可视化样本：逐 token 打印 token、role、label 和是否参与 loss，验证
shift 没有 off-by-one，prompt 没有被错误监督，EOS 确实参与目标。

### 4.3 带 KV cache 的生成流程

```python
cache = None
tokens = prompt_ids

# prefill
out = model(tokens, past_key_values=None, use_cache=True)
cache = out.past_key_values
next_token = select(out.logits[:, -1, :], generation_config)

# decode
while not stop(next_token):
    out = model(next_token[:, None], past_key_values=cache, use_cache=True)
    cache = out.past_key_values
    next_token = select(out.logits[:, -1, :], generation_config)
```

`[通用工程]` 验证 cache 正确性的最小 gate：相同模型、token prefix、dtype 与 decoding
配置下，分别运行 `use_cache=false` 和 `use_cache=true`，逐步比较 logits/token；还要
覆盖 batch 中不同长度、EOS、截断和 cache 重排。

### 4.4 Structured output 的 fail-closed 管线

```text
model text
 -> exact JSON parse
 -> schema validation (type / required / additionalProperties)
 -> semantic invariants (cross-field consistency)
 -> tool registry and argument validation
 -> risk / policy / approval / budget checks in Runtime
 -> execute or reject
```

自动 retry 必须计入延迟、成本与执行次数；formal eval 应预注册是否允许 retry，避免
只保留成功样本造成选择偏差。Parser 不应静默修补未知字段；compiler 只应推导真正
冗余且有单一 source of truth 的字段。

### 4.5 资源估算与验证清单

- 参数内存粗估：`parameter_count * bytes_per_parameter`，推理还要加 KV cache、
  activation/workspace、allocator fragmentation；
- attention 训练的朴素 score 内存随 `T^2` 增长，FlashAttention 通过 IO-aware
  分块避免保存完整 score matrix，但不改变 attention 语义；
- 记录 prompt tokens、generated tokens、batch、dtype、attention backend、
  `use_cache`、全部 decoding 参数；
- 将 raw output、token IDs、必要的 logits 摘要、config 与 artifact hash 绑定；
- 不用一次 wall-clock 样本宣称稳定加速，先 warmup，再报告分布与硬件环境。

## 5. Metrics 与 gates

### 模型/语言层

- token-average NLL、perplexity；
- eval loss，但必须固定 Tokenizer、masking 和切分；
- 长上下文 retrieval/needle 等任务指标，不能只看训练 context length。

### 任务层

- JSON/schema validity；
- tool accuracy、argument exact match、argument field F1；
- semantic invariant pass rate；
- dangerous action candidates、dangerous false approvals、false refusal；
- 按风险、任务族、长度分桶的 slice metrics。

### 推理系统层

- TTFT（time to first token）：主要受排队与 prefill 影响；
- TPOT / inter-token latency：主要反映 decode；
- end-to-end latency 的 p50/p95/p99；
- request/s、output tokens/s、goodput；
- KV cache 使用率、cache hit rate、preemption/recompute rate；
- OOM、invalid output、retry 和 timeout rate。

### 推荐 gate

```text
functional: 固定输入得到预期 schema 与任务结果
regression: 冻结逐例正确项不得回退
safety: 危险动作/越权不得增加
performance: 在锁定硬件和负载下满足 TTFT/TPOT/显存预算
reproducibility: config/tokenizer/model/output provenance 可重算
```

## 6. 常见失败与排障

| 症状 | 优先检查 | 为什么 |
|---|---|---|
| loss 很低但生成很差 | label shift、loss mask、chat template、train/eval prompt 一致性 | 模型可能学的是 prompt 复述或错一位 label |
| 输出总在未来 token 上“作弊” | causal mask 方向和 backend causal flag | mask 反向或漏 mask 会泄漏 |
| cache on/off 不一致 | position IDs、cache position、attention mask、cache 重排 | cache 状态与序列身份错位 |
| JSON 合法但字段冲突 | schema 之外的 semantic invariants | grammar 不理解业务关系 |
| greedy 跨 dtype 出现一个 token flip | 比较原始 logits、top-1 margin、逐层注册边界 | argmax 在近边界对微小数值差敏感 |
| NaN/Inf | mask 全为 `-inf`、softmax dtype、异常 activation | 全屏蔽行和低精度溢出常见 |
| 长上下文突然 OOM | KV cache 公式、并发、allocator、max tokens | 权重不是唯一显存消费者 |
| 吞吐高但用户延迟差 | 分开看 queue、TTFT、TPOT、tail latency | aggregate tokens/s 掩盖长尾 |
| 重复或无法停止 | EOS/template、stop sequence、repetition penalty | 训练终止格式和推理配置不一致 |

排障顺序建议：先固定单样本 greedy 与所有 config，再比较 tokenization；然后比较
raw logits 而非 decoded string；再用 AB/ABBA fresh lifecycle 确认重复性；最后才加
module hooks 缩小注册边界。观察到的第一个注册差异，只是 probe plan 内的最早
差异，不自动等于全图第一个 operation 或唯一 root cause。

## 7. 与相邻概念比较

| 概念 A | 概念 B | 关键区别 |
|---|---|---|
| Tokenizer | Embedding | 前者把字符串离散化；后者把 token ID 映射为可学习向量 |
| logits | probability | logits 是 softmax 前分数；概率归一化且和为 1 |
| causal mask | padding mask | 前者阻止看未来；后者阻止读取无效 padding |
| RoPE | absolute position embedding | 前者旋转 Q/K 表达相对相位；后者向 hidden state 加位置表 |
| RMSNorm | LayerNorm | RMSNorm 不减均值；LayerNorm 中心化并缩放 |
| MHA | GQA/MQA | query head 数可相同，主要减少的是 K/V heads 与 cache |
| prefill | decode | 前者并行处理 prompt；后者逐 token、强依赖 cache/带宽 |
| greedy | beam search | greedy 每步局部 argmax；beam 保留多个累计分数候选，LLM 对话未必更好 |
| constrained decoding | validator | 前者限制可生成语法；后者检查生成后的语义/策略不变量 |
| model proposal | execution authority | 模型给候选；Runtime policy/approval 才决定是否执行 |

## 8. 高频问题与分层答案

### Q1：请从输入到输出讲一遍 Decoder-only Transformer

**30 秒答案**

Tokenizer 把文本变成 `[B,T]` token IDs，embedding 得到 `[B,T,d]`。每层先做
causal self-attention 混合历史信息，再做逐位置 gated MLP，两段都有 norm 和
residual。final norm 后 LM head 得到 `[B,T,V]` logits，取最后位置按 greedy 或
采样选下一个 token。训练用 shift 后的 next-token cross-entropy，推理用 KV cache
避免重算历史 K/V。

**2 分钟展开**

补充 Q/K/V shape、`QK^T/sqrt(d_h)`、causal mask、MHA/GQA、RoPE、RMSNorm、
SwiGLU，以及 prefill/decode 区别。最后说明 Tool Use 还需 constrained decoding、
schema/semantic validator 和 Runtime authority。

**深挖要点**

- 为什么 `sqrt(d_h)`；
- GQA 如何改变 cache 公式；
- pre-norm 对梯度路径的影响；
- cache on/off 等价性如何测试；
- near-tie logits 为什么会因 dtype/执行图改变 argmax。

### Q2：KV cache 为什么加速？代价是什么？

**30 秒答案**

它缓存每层历史 token 的 K/V，decode 时只算新 token 的 Q/K/V，不再重算整个
prefix。代价是显存随 batch、序列长度、层数和 KV heads 线性增长，长上下文和高
并发时 cache 会成为容量瓶颈。

**2 分钟展开**

写出 `B*T*L*2*h_kv*d_h*bytes`，解释 MHA/MQA/GQA；再区分 prefill 的大矩阵
计算和 decode 的带宽/调度瓶颈，提到 paged cache、prefix cache 与 cache 隔离。

**深挖要点**

- beam/batch 重排时 cache 如何跟序列对应；
- speculative decoding 或 sliding window 对 cache 的影响；
- prefix cache 的哈希键和租户数据隔离；
- 为什么 returned logits dtype 不能证明所有内部 kernel dtype。

### Q3：如何保证模型输出合法 JSON？

**30 秒答案**

prompt 只提供软约束；生产上用 grammar/FSM constrained decoding 保证语法，再用
JSON Schema、跨字段语义校验、tool registry 和 Runtime policy fail closed。合法
JSON 不是合法动作。

**2 分钟展开**

说明 token-level grammar 的边界、未知字段/数值范围、compiler 的单一 source of
truth、retry 的预算和 eval 口径，并强调模型 proposal 不拥有执行权限。

**深挖要点**

- 字符串 escaping 与 tokenizer token 边界；
- schema valid 但 semantic invalid 的例子；
- constrained decoding 对 latency/吞吐的影响；
- validator/compiler 如何版本化和做 mutation tests。

### Q4：为什么 greedy 仍可能不复现？

**30 秒答案**

greedy 只规定对当前 logits 取 argmax；它没有保证不同 dtype、kernel、执行顺序或
库版本产生完全相同 logits。当 top-1/top-2 很接近时，微小数值差就会翻转 token，
之后自回归轨迹会放大差异。

**2 分钟展开**

区分 within-path nondeterminism 与 deterministic cross-path drift；先 fresh repeat，
再锁定 prompt/tokenizer/backend，抓 raw logits 和 processed scores，定位首个生成
边界，最后用预注册 hooks/control 缩小原因范围。

**深挖要点**

- TF32/autocast/deterministic algorithms；
- fused kernel 与 reduction order；
- first observed boundary 与 unique root cause 的区别；
- token exact、logit tolerance 和任务 metric 各回答什么问题。

## 9. 本项目映射与证据边界

### `[本仓库已实现]`

- 冻结的 Tool Router 使用 pinned `Qwen/Qwen2.5-1.5B-Instruct` 与固定 revision；
  项目使用了已有 Decoder-only 模型，不等于本仓库从零实现或预训练了 Qwen。
- 冻结推理/诊断锁定 greedy decoding、`use_cache=true`、高层 Transformers `sdpa`
  dispatch、prompt/tokenizer/config 与输出证据。`eval-001` 的一个诊断点记录了
  339-token 输入、48 个生成 token，以及 shape `[1,151936]` 的逐步 logits。
- LoRA v2 的 raw JSON 出现三个交叉字段冲突；离线 decision compiler 以
  `selected_tool` 为单一 disposition 派生冗余 terminal flags，使冻结 20-case 的
  semantic validity 从 `0.85` 到 `1.00`，但这被明确分类为 contract compilation，
  不是模型能力提升，也不是 Runtime integration。
- BF16 attached 与 safe-merged 路径在 `eval-001` 的 generated-token index 45 发生
  `true/false` argmax flip；后续同 dtype FP32 attached/merged 比较虽有大量微小
  logit 差异，却保持全部 48 token 相同。这正说明数值差异、token 差异与任务差异
  是不同层级的证据。

冻结证据入口：[decision compilation](../../FC-MVP-001-decision-compilation-v1.md)、
[BF16 merge stability](../../FC-MVP-001-bf16-merge-stability-v1.md)、
[FP32 attached/merge isolation](../../FC-MVP-001-fp32-attached-merge-isolation-v1.md)。

### `[本仓库待实施]`

- Tiny Transformer Lab 中从零实现并系统验证 Tokenizer/Decoder block、
  MHA/MQA/GQA、RoPE 与 KV cache；
- 结构化 constrained decoding 服务化、continuous batching、prefix cache 与正式
  serving benchmark；
- 长上下文、attention kernel、模型架构和 KV-cache 系统对照实验。

因此面试可说“我基于冻结的 Qwen 模型做过 Tool Router 生成与深入数值诊断”，不应
说“我已经从零训练大模型”或“我实现了生产级 vLLM serving”。

## 10. 自测题与实践

### 白板自测

1. 写出 `X=[2,128,1024]`、`h=16` 时 Q/K/V、attention score 和 concat 后的
   shape。
2. 为什么 causal training 可以并行处理所有位置，而 inference 仍需逐 token？
3. 推导 KV cache 估算式，并说明 GQA 改变哪个因子。
4. 解释 RoPE 为什么能让 dot product 携带相对位置信息。
5. 对比 RMSNorm、LayerNorm 和 BatchNorm；为什么 LLM 不常用 BatchNorm？
6. temperature、top-k、top-p 分别在什么分布上作用？
7. 为什么 grammar constrained decoding 无法阻止未授权工具调用？
8. 为什么“首个不同模块”不能直接叫 root cause？

### 最小实践

- 实现一个两层 Decoder-only Transformer，在小语料上过拟合，并打印每个关键
  tensor shape；
- 写 `cache=false` 与 `cache=true` 两条 greedy 路径，逐 token 比较 logits；
- 对一个固定 logits 向量手算 temperature/top-k/top-p 后的候选集合；
- 写一个只允许简单 JSON object 的 token/字符级 FSM，再故意生成 schema-valid
  but semantic-invalid 样本交给 validator 拒绝；
- 测量 prompt length 从 128 到 4096 时 TTFT、TPOT 与 KV cache 显存曲线；
- 人为构造 top-1/top-2 只差 `1e-5` 的 logits，观察微小扰动如何改变 greedy
  结果。

### 掌握标准

- 能在 5 分钟内无资料画完 forward 与 generate 数据流；
- shape、mask、loss shift、cache 公式无错误；
- 能为一个真实 workload 解释 decoding 选型，而不是只背定义；
- 能用 metrics 和受控实验区分“语法错误、语义错误、数值漂移、系统性能问题”；
- 能准确陈述本项目已实现与待实施的边界。
