# 六个项目面试故事

> 本章把冻结项目证据翻译成面试叙事，不证明读者个人完成了这些工作。使用前必须
> 核对个人职责。精确状态仍由 [PROJECT_STATUS.md](../../../PROJECT_STATUS.md)
> 和链接的 evidence 文档拥有。

## 1. 怎样使用这些故事

每个故事都有四个层次：

- **一句话**：简历或自我介绍中的定位；
- **两分钟**：完整回答“最有挑战的项目是什么”；
- **深挖**：面试官追问公式、控制变量、failure mode 和 alternative；
- **边界**：主动说明证据没有支持什么。

不要六个故事逐字背诵。先记住同一个骨架：

```text
问题是什么
→ 为什么常见做法不够
→ 锁定哪些变量
→ 只改变什么
→ 用什么 evidence 判断
→ 得到什么正/负结果
→ 最强可辩护结论是什么
→ 下一项实验是什么
```

---

## 故事一：把 Tool Router 从“生成 JSON”变成 typed decision contract

### 一句话版本

我没有把 Tool Router 当作能直接执行工具的聊天模型，而是先定义 closed JSON
Schema 和跨字段语义，把模型限制为 candidate decision；按跨仓 contract，Policy、
Approval、WAL 和 desktop boundary 的执行权保留给独立 Runtime，本 gate 没有连接或
授权 Runtime execution。

### 为什么这是一个工程问题

“模型输出合法 JSON”只验证语法，不验证行为。例如：

- `selected_tool=reject_request`，但 `should_reject=false`；
- 选择了不在 `available_tools` 中的工具；
- duplicate delivery 又产生同一 side effect；
- tool failure 或 loop budget exhausted 后仍继续调用；
- dangerous request 没有拒绝；
- 模型在参数里塞入嵌套对象或未经审查的 rich content。

这些失败不能靠 prompt 里的“请谨慎”解决。它们需要 typed schema、semantic
invariants、fail-closed validator，以及模型与 Runtime 的 authority separation。

### 设计与实现

`tool_router_schema_version=1` 的每条记录绑定 instruction、available tools、
delivery/tool-failure/loop/approval state，并输出：

```text
selected_tool
arguments
risk_level
requires_approval
should_reject
should_fallback
expected_result
```

工程上分四层：

1. **Syntax layer**：closed JSON object、enum、size 和 scalar argument 约束。
2. **Semantic layer**：tool availability 与 rejection/fallback/approval 的跨字段不变量。
3. **Model layer**：只提出 candidate decision，不执行副作用。
4. **Runtime layer**：Policy、Approval、Grounding、WAL、budgets 和 desktop action
   保持 authority。

输入还设置 1 MiB、1,000 records、2,000 instruction characters、20 scalar
argument fields 等显式上限。未知 version、field、tool、nested argument、duplicate
ID 或 semantic contradiction 均 fail closed。

### 可引用证据

| 证据 | 结果 |
| --- | --- |
| Reviewed seed / frozen eval | `20 / 20` records |
| Eval categories | 10 类，每类 2 条 |
| Rule baseline | tool accuracy `1.0`，argument exact/F1 `0/0` |
| Authority | model 只输出 candidate；Runtime controls 未开放 |

rule baseline 的 tool accuracy 很高但 argument 为零，是重要提醒：单个 aggregate
metric 不能代表决策完整性；一个硬编码 router 也不能代表 learned generalization。

### 两分钟回答示例

> 我先把问题定义成 typed decision，而不是自由文本 function calling。Schema
> 关闭所有 object，并限制 available tools、参数类型和输入规模；随后用标准库
> validator 检查跨字段语义，例如拒绝工具必须和 `should_reject`、
> `expected_result` 一致，duplicate delivery 必须拒绝，已耗尽 loop budget 必须
> fallback。模型输出永远只是 candidate，Runtime 的 Policy、Approval 和 WAL
> 才有执行权限。为了在训练前有稳定参照，我冻结了 10 类各 2 条的 20-case eval
> 和一个不读取 gold decision 的 deterministic baseline。这个 baseline 的 tool
> accuracy 是 1.0，但 argument 指标为 0，正好证明不能用一个指标宣称 router
> 完成。该阶段只证明 contract 和 offline eval 可执行，不证明模型泛化、Runtime
> integration 或 production safety。

### 深挖问题

**为什么不让模型同时生成所有 flags？**

如果多个字段表达同一 terminal disposition，独立生成会形成非法状态空间。可以让
模型生成信息量最小的 canonical field，再由 deterministic compiler 派生冗余字段；
但 compiler 必须成为 candidate identity 的一部分并独立验证。

**Schema validation 和 policy enforcement 有什么区别？**

Schema 回答“结构和局部语义是否有效”；Policy 回答“在当前用户、资源、状态与风险
下是否授权”。合法 action 仍可能未获授权，不能把 schema 当作 security boundary。

**为什么 fail closed？**

工具调用会产生真实副作用。未知字段或无法判定状态若被宽松接受，会把协议漂移变成
隐式权限扩大。fail closed 的代价是 availability/false refusal，需要明确 fallback
与人工审批，而不是默认执行。

### Claim boundary

该证据支持 offline schema/eval 和 candidate/authority separation；不支持真实工具
执行、线上 traffic、production safety 或 Runtime 中的模型集成。

**Sources:** [schema/eval gate](../../FC-MVP-001-schema-eval.md)、
[Runtime integration boundary](../../../Desktop_Runtime_依赖与集成.md)。

---

## 故事二：用 task-family split 和 frozen eval 防止“安全修复”变成泄漏

### 一句话版本

我把数据 identity、task family 和 eval identity 都变成可验证 contract：训练与
验证按 family 隔离，评测先冻结，安全 bad case 只生成新的 train/validation family，
不复制 eval 答案，并用 digest、duplicate/Jaccard 和 distribution gate 阻止静默污染。

### 核心风险

随机 row split 对模板化 Agent 数据通常过于乐观。相同任务模板只替换文件名或日期，
就可能跨 train/validation；模型学到模板而不是能力。看到 eval bad case 后直接加入
其答案，更会把“修复”变成 evaluation leakage。

因此切分单位不是 row，而是能代表生成机制或任务语义的 `task_family`。

### 数据演进

| 阶段 | Train | Validation | Eval | Family / 约束 |
| --- | ---:| ---:| ---:| --- |
| v1 | 160 | 40 | 20 | 60 个 train/validation families；eval 不变 |
| safety repair increment | +16 | +8 | +0 | 8 个 disjoint repair families |
| v2 | 176 | 48 | 20 | v1 exact prefix；eval digest 不变 |

审计同时检查：

- task-family overlap 为零；
- exact instruction duplicates 为零；
- cross-split instruction token Jaccard 达到或超过 `0.8` 即拒绝；观测最大值
  `0.4166666666666667`；
- 类别与长度 distribution；
- dangerous false approvals；
- schema、record order、manifest 和 canonical digest；
- eval answer 未进入 repair data。

### 为什么 bad case 仍能指导训练

可以使用 eval 的**错误类型**，不能复制它的**具体答案**。过程是：

```text
frozen bad case
→ 归纳 failure mechanism
→ 设计新的、family-disjoint 的训练场景
→ 人工 review gold behavior
→ 只更新 train/validation
→ 保持 eval bytes/digest 不变
→ 一次运行 locked experiment
```

例如看到 dangerous request 处理失败，可以增加不同措辞、不同工具集合、不同状态组合
的危险请求 family；不能把 `eval-xxx` 原句和 gold JSON 改名后放入训练集。

### 两分钟回答示例

> Agent 数据高度模板化，所以我没有使用普通随机行切分，而是先定义 task family，
> 再保证 train 和 validation family-disjoint。v1 是 160/40、60 个 family，另外
> 冻结 20-case eval。LoRA v1 出现 safety bad case 后，我把错误归纳为四个 repair
> targets，新增 16/8 条并分属八个 train/validation-disjoint families，保留 v1
> exact prefix，也不改 eval。
> 离线 gate 检查 family overlap、exact duplicate、token Jaccard、distribution、
> dangerous false approval 和 digest；最大跨 split Jaccard 是 0.4167，低于预设
> 0.8 threshold。这个设计降低了注册范围内的模板泄漏风险，但不能证明不存在所有
> semantic contamination，也不能用 20 条 eval 推断广泛 generalization。

### 深挖问题

**为什么 Jaccard 不能证明无泄漏？**

它只覆盖定义好的 token 相似度。paraphrase、翻译、同一生成模板的远距离表达、外部
预训练污染都可能逃过。需要 family metadata、semantic search、provenance 和人工
review 组合使用。

**为什么冻结 eval digest？**

为了区分“模型/数据改变带来的结果”与“评测集悄悄改变带来的结果”。Digest 证明
被比较文件的 byte identity，不证明标签正确、覆盖充分或没有上游污染。

**为什么不按 validation loss 事后选 epoch？**

若 epoch selection 规则未预先锁定，再使用 eval 选择最优 checkpoint，会产生隐性
multiple testing。可以用 validation 设计早停，但规则必须在打开 eval 前固定。

### Claim boundary

支持注册 schema 和审计范围内的 family separation、byte identity 与 leakage gate；
不支持大规模覆盖、无偏 generalization、生产数据或任何可能形式的绝对无污染。

**Sources:** [schema/eval](../../FC-MVP-001-schema-eval.md)、
[safety-repair data](../../FC-MVP-001-safety-repair-data-v2.md)。

---

## 故事三：Base → LoRA v1 → safety-repair → LoRA v2

### 一句话版本

我用完全不变的 20-case eval 做纵向对照：prompt-only Base 暴露路由与危险行为，
LoRA v1 在该冻结集合上提高多项注册指标但未过 safety gate，再用
train/validation-only hard negatives 形成 v2，使 tool accuracy 达 `0.95` 且
dangerous-action candidates 降为零，同时保留 argument 和 semantic regression，
而不是只报最好数字。

### 锁定实验

| 配置 | v1 | v2 |
| --- | --- | --- |
| Base | Qwen2.5-1.5B-Instruct，固定 Hub revision | 相同 |
| Method | BF16 LoRA | BF16 LoRA |
| `r / alpha / dropout` | `16 / 32 / 0.05` | 相同 |
| Targets | `q_proj,k_proj,v_proj,o_proj` | 相同 |
| Sequence length | `448` | `448` |
| Effective batch | `2 × 4 = 8` | 相同 |
| LR / scheduler / warmup | `2e-4 / cosine / 0.1` | 相同 |
| Data | `160/40` | `176/48` |
| Epochs | 5 | 3，依据既有 v1 overfit 证据预先锁定 |
| Seed | `20260729` | `20260803` |

v1 与 v2 同属预注册 candidate package，但 data、epoch count 和 seed 都发生了变化。
因此这是一组受控的纵向 lifecycle comparison，而不是 `repair data only` 的单变量
ablation；它能比较两个候选包的整体结果，不能单独识别 repair data 的因果效应。

### 指标全貌

| Metric | Base | LoRA v1 | LoRA v2 |
| --- | ---:| ---:| ---:|
| JSON validity | `1.00` | `1.00` | `1.00` |
| Decision semantic validity | `0.70` | `0.80` | `0.85` |
| Tool accuracy | `0.20` | `0.80` | `0.95` |
| Argument exact match | `0.00` | `0.35` | `0.20` |
| Risk Macro F1 | `0.4258` | `0.7373` | `0.7095` |
| Dangerous action candidates | `2` | `1` | `0` |
| Dangerous false approvals | `1` | `0` | `0` |

v1 的 100 optimizer steps 用时 `216.825720s`，峰值 allocated GPU memory
`5,217,494,016 bytes`；v2 的 66 steps 用时 `169.527236s`，峰值相同。两版
trainable parameters 都是 `4,358,144`，占 Base 的 `0.281521%`。

### 结果怎样解释

正结果：v2 通过了窄定义 dangerous-action gate，Tool selection 大幅优于 Base。

负结果同样重要：

- v2 argument exact match 从 v1 `0.35` 降到 `0.20`；
- Risk Macro F1 从约 `0.7373` 降到 `0.7095`；
- 三条输出存在 conflicting decision flags；
- 三个 false refusals；
- safe merge 改变 `eval-001` 一个 boolean，output identity 失败。

因此 `safety_gate_passed=true` 只属于窄 dangerous-action requirements，整体仍
`runtime_eligible=false`。

### 两分钟回答示例

> 我先在固定 Qwen 1.5B、固定 revision 和 20-case eval 上建立 Base。Base 虽然
> JSON validity 是 1.0，但 tool accuracy 只有 0.2，而且两个危险样本都产生 action
> candidate。v1 用 rank 16、alpha 32 的 BF16 LoRA，只训练 Q/K/V/O projection，
> 0.28% 参数，在 unchanged eval 上把 tool accuracy 提到 0.8，但仍有一个危险
> candidate，所以我没有宣称成功。随后从 bad-case mechanism 设计 16/8 条
> family-disjoint repair data，并依据 v1 validation overfit 预先把 v2 锁为三 epoch；
> v2 同时使用了不同 seed，因此这是两个预注册 candidate package 的纵向比较，不是
> repair-data-only ablation。v2 tool accuracy 到 0.95，危险 candidate 为零，但
> argument exact match 和 risk F1 有回退，且出现三个 conflicting flags。结论是
> v2 package 通过窄 safety gate，而非已经证明某个单变量导致模型全面提升；下一步
> 应该先分类 contract failure，而不是立刻继续加数据或调参。

### 深挖问题

**为什么 LoRA 训练参数这么少？**

对目标 linear layer 的更新写成 `ΔW = (α/r)BA`，其中 rank `r` 远小于输入、输出
维度；冻结 Base，只优化低秩 `A/B`。参数与 optimizer state、gradient memory 因而
显著减少，但 activation memory 仍存在。

**为什么 v2 不能说“全面优于 v1”？**

多个指标方向不同，样本仅 20 条。正确结论必须绑定预设 gate：危险行为改善，
argument/risk 出现 regression，semantic contract 仍失败。

**为什么保留独立 Adapter？**

它体积小、identity 独立、可回滚，也能与 Base revision 明确组合。Merge 会改变
execution form 和 numerical behavior，必须另设 identity/equivalence gate。

### Claim boundary

支持单卡、1.5B、一个 LoRA 配置、固定 176/48 data 与 20-case eval 的本地结果；
不支持 LoRA-vs-QLoRA、rank ablation、大规模 generalization、部署或 Runtime 使用。

**Sources:** [base baseline](../../FC-MVP-001-base-model-v1.md)、
[LoRA v1](../../FC-MVP-001-lora-sft-v1.md)、
[LoRA v2](../../FC-MVP-001-lora-sft-v2.md)。

---

## 故事四：模型错误还是 decision-contract 错误——安全与 false refusal

### 一句话版本

我把 v2 的 failure 拆成两类：三个 conflicting flags 属于冗余决策字段不一致，
另一个是 Adapter merge 数值漂移；随后冻结 deterministic compiler，只从
`selected_tool` 派生 terminal flags，使 semantic validity `0.85→1.0`、false
refusal `3→0`。Compiler 改变了三个 case 的 `expected_result` 与 `should_reject`，
但保持 raw source bytes、`selected_tool`、arguments、risk、approval 以及 dangerous
candidate/false-approval 计数不变。

### 为什么先分类，不先重训

同一个 aggregate failure 可能来自完全不同的层：

```text
模型没有学会任务
结构化输出语法失败
多个冗余字段互相矛盾
post-processing 改错
Adapter load/merge 数值变化
Runtime policy 拒绝
```

如果不分类就加数据，可能用昂贵、不可解释的模型训练去修一个 deterministic
contract bug，还可能引入新的 regressions。

### Compiler contract

`selected_tool` 被定义为 canonical terminal disposition，其他字段确定性派生：

| Tool class | `expected_result` | reject | fallback | approval |
| --- | --- | ---:| ---:| ---:|
| `reject_request` | rejection | true | false | false |
| `fallback_to_strong_model` | fallback | false | true | false |
| `request_clarification` | clarification | false | false | false |
| approval-required tool | approval_required | false | false | true |
| ordinary tool | tool_candidate | false | false | false |

Compiler 在一次 frozen scoring 前固定，不能读取 eval answers；source prediction
artifact byte-unchanged，派生 artifact 单独保存。

### 结果

| Metric | Raw v2 | Compiled v1 |
| --- | ---:| ---:|
| Decision semantic validity | `0.85` | `1.00` |
| Tool accuracy | `0.95` | `0.95` |
| Rejection accuracy | `0.85` | `1.00` |
| False refusals | `3` | `0` |
| Dangerous action candidates | `0` | `0` |
| Dangerous false approvals | `0` | `0` |

只改变 `eval-001/014/020` 的 `expected_result` 和 `should_reject`；instruction、
arguments、selected tool、risk、approval 和 raw bytes 都不变。

### 两分钟回答示例

> LoRA v2 通过窄 safety gate 后仍有三个 false refusals 和 semantic conflicts。
> 我没有直接重训，而是先做 failure classification。三个案例都选择了 fallback，
> 但同时生成了 rejection flags，说明错误在同一 terminal decision 的冗余表示，
> 不是 frozen evidence 支持的数据 coverage 问题。我因此先冻结一个 decision
> compiler，以 `selected_tool` 为 canonical field，确定性派生 reject、fallback 和
> expected result。一次固定评测后 semantic validity 从 0.85 到 1.0，false refusal
> 从 3 到 0，tool accuracy 与危险行为保持不变。这个结果是 contract compilation，
> 不是模型能力提升；compiler 也成为 package identity 的必需部分。另一个
> attached/merged 输出差异被保留为独立数值问题，不能被 compiler 掩盖。

### 深挖问题

**Compiler 是不是“篡改模型答案”？**

如果它改变模型选择的 tool 或根据 gold label 修答案，是。这里它只把同一个 canonical
terminal choice 投影到冗余字段，规则先冻结、source bytes 不变、derived artifact
分开保存。仍必须明确报告 raw 与 compiled metrics。

**为什么 compiler dependency 是 candidate identity 的一部分？**

用户可见决策依赖 `model + prompt + generation + compiler`。漏掉 compiler，另一个
环境可能得到语义非法结果；因此不能只用 Adapter hash 表示完整 candidate。

**false refusal 和 dangerous approval 怎样权衡？**

不能用单一 accuracy。需要分别报告 dangerous action/approval、rejection recall、
false refusal、per-category/per-example regression，并根据风险定义 asymmetric gate。

### Claim boundary

支持 deterministic contract repair；不证明 raw model semantics 改善、compiler 可
泛化到新 schema、merged artifact 安全或 Runtime eligible。

**Sources:** [failure classification](../../FC-MVP-001-v2-failure-classification.md)、
[decision compilation](../../FC-MVP-001-decision-compilation-v1.md)。

---

## 故事五：BF16 merge drift 的逐层数值诊断

### 一句话版本

我把一个 safe-merged Adapter 的单 boolean 差异从“偶发生成问题”逐步收窄为
repeat-stable raw-logit argmax flip，再用 execution-form 与 dtype 的正交对照、ABBA
ordering、module hooks 和 standalone RMSNorm replay，定位首个 registered boundary，
同时拒绝把“首个差异”夸大成唯一 CUDA/kernel root cause。

### 初始现象

LoRA v2 的 independently attached Adapter 与 BF16 safe-merged model 在
`eval-001` 只差一个 boolean。常见但错误的结论是“merge 有 bug”或“GPU nondeterminism”。

正确诊断先拆变量：

```text
axis A: attached factorized LoRA vs materialized merged linear
axis B: BF16 vs FP32 base/inference dtype
axis C: repeated fresh load / run order
axis D: processed generation score vs raw LM-head logits
```

### 证据链

1. **Repeat stability**：两次 attached 和两次 merged 各自 token-identical；排除本
   路径内随机抖动。首个 token divergence 在 zero-based index `45`。
2. **Raw-logit capture**：不只是 logits processor；同一 cached generation step 的
   raw LM-head argmax 也从 `true` 翻到 `false`。
3. **BF16 merge numerics**：首个 paired module difference 在 layer 0 `q_proj`；
   `154,140,672` 个目标权重中，有 `30,640,994` 个非零理想 update 在 BF16
   materialization 后 round back 到 base value。
4. **FP32 attached/merged control**：保持 FP32 后，两种 form 输出相同 token，但
   logits 仍有小而稳定的 numerical drift；在这个 locked FP32 control 中，execution
   form effect 没有形成 token flip，但这不排除它与 dtype 的 interaction。
5. **Attached BF16/FP32 control**：保持 attached form，改变 dtype，ABBA 四次复现
   token index 45 的 `true/false` flip；隔离 total dtype effect。
6. **40-output trace**：embedding canonical equal；首个 registered inequality 是
   layer 0 `input_layernorm`，之后直到 LM head 均 unequal。
7. **Standalone control**：用相同 checkpoint input/weight 分别运行 fresh
   `Qwen2RMSNorm`，两种 dtype 输出各自精确匹配实际 module boundary。

### 为什么不同实验看见不同“首个差异”

BF16 attached vs merged 比较固定 dtype、改变 execution form，首差可在 `q_proj`；
BF16 attached vs FP32 attached 固定 form、改变 dtype，首差可在 RMSNorm。它们回答
不同 counterfactual，不矛盾。

### 两分钟回答示例

> 我遇到 attached LoRA 和 safe-merged model 在一个 frozen case 上生成 boolean
> 不同。第一步不是改 precision，而是证明每条路径 repeat-stable；两次 fresh load
> 都复现，首个 token 边界在 index 45。随后捕获同一 cached forward 的 processed
> score 和 raw logits，确认 raw argmax 已翻转，不是 sampling 或 logits processor。
> 为避免 confounding，我分别做 same-dtype attached/merged 和 same-form BF16/FP32
> 对照，并用 ABBA 顺序减少运行顺序影响。FP32 下 form 只造成小 drift、没有 token
> 差异；固定 attached form 改 dtype 则复现 flip。40 个 registered outputs 中，
> embedding 相同，首差在 layer-0 RMSNorm；standalone same-values RMSNorm 又精确
> 复现该 boundary。最强结论是 dtype arithmetic 足以复现这个局部观察边界，不能
> 说 RMSNorm 或某个 CUDA kernel 是唯一 root cause，也不能泛化到整个 eval。

### 深挖问题

**为什么要 ABBA，而不是 AABB？**

ABBA 让两个 condition 都分布在运行前后位置，降低 warm-up、temperature、allocator
state 或 drift 与 condition 完全共线的风险。它不替代更多随机化和统计重复，但对
昂贵 deterministic probe 是更强的顺序控制。

**首个 unequal output 等于 root cause 吗？**

不等。它只是注册的 observation points 中最早出现差异的位置。模块内部未注册算子、
输入 dtype conversion、kernel implementation 或更早的隐藏状态都可能解释它；
下游 unequal 也不证明独立 causal propagation。

**为什么很小误差能改 token？**

Autoregressive decoding 是离散 argmax boundary。若 top-1/top-2 margin 很小，连续
logit perturbation 可能改变第一个 token；之后不同 token 被反馈为输入，序列差异会
扩散。误差绝对值小不等于行为风险小。

**FP32 是不是一定更“正确”？**

FP32 通常有更高数值精度，但“正确”必须由 task-level gate 定义。本项目 FP32
compiled argument metrics 略好，raw semantic validity 却更低，而且显存约为 BF16
的 `1.9896x`。它是受约束下的 preferred candidate，不是普遍真理。

### Claim boundary

这是单个 frozen example、固定模型与硬件上的 repeat-stable diagnostic lineage。
不支持 unique kernel cause、PEFT bug、所有输入 generalization、stable speedup、
merged artifact promotion 或 Runtime eligibility。

**Sources:** [merge stability](../../FC-MVP-001-bf16-merge-stability-v1.md)、
[merge numerics](../../FC-MVP-001-bf16-merge-numerics-v1.md)、
[dtype isolation](../../FC-MVP-001-attached-dtype-isolation-v1.md)、
[dtype numerics](../../FC-MVP-001-attached-dtype-numerics-v1.md)、
[boundary control](../../FC-MVP-001-attached-dtype-boundary-control-v1.md)。

---

## 故事六：hash 相同为什么不等于 artifact 来源可信或可移植

### 一句话版本

我把 artifact qualification 拆成独立 evidence states：composite manifest 绑定
byte identity，hosted revision metadata 绑定 origin，clean-location replay 证明同一
记录环境行为复现，preferred decision 只做候选选择；cross-machine portability、
signing、promotion、serving 与 Runtime readiness 仍需各自门禁。

### 常见错误推理

```text
“文件 hash 对上了”
→ “来源可信”
→ “换机器也能跑”
→ “可以上线”
```

每个箭头都缺证据。

### Evidence state machine

| State | 回答的问题 | 不回答的问题 |
| --- | --- | --- |
| Composite manifest | package 包含哪些 exact bytes/config/dependencies？ | hosted origin、作者、行为 |
| Origin binding | 这些 bytes 是否绑定固定 GitHub/HF revision？ | 签名作者、执行结果 |
| Clean-location replay | 新路径、同记录环境能否 exact replay？ | cross-machine portability |
| Offline eligibility | 已注册 package/behavior/origin gates 是否完整？ | 候选偏好、部署 |
| Preferred candidate | 在固定 rubric 下下一步测哪个？ | portable、promoted、served |
| Portable qualification | 独立合格机器是否通过冻结 replay？ | serving capacity、Runtime safety |
| Promotion/serving/Runtime | 各自质量、性能、rollout、安全 integration 是否通过？ | 其他未注册环境 |

### 已完成证据

- metadata-only composite manifest 绑定 Base/tokenizer `9/9`、Adapter `3/3`、
  repository sources `15/15`、compiler、prompt/generation/precision/environment；
- fresh caller-supplied roots 中，一次 fresh FP32 attached load、20 次 ordered
  generation、zero retry，raw `20/20` 与 compiled `20/20` exact replay；
- GitHub package closure 的 `18/18` entries 全部绑定：普通 blobs 逐一核对，Adapter
  weight entry 是一个精确的 133-byte Git LFS pointer；Hugging Face pinned revision
  的 9 个 package files 同样进入内容身份核对；
- offline eligibility 的 9 gates 全通过；preferred decision 的 12 gates 全通过；
- GitHub 明确报告 package commit unsigned，因此 author/signature、supply-chain
  signature、transparency log 均未建立。

### 当前未完成的关键证据

portable protocol 已在 target result 前冻结，但尚无 independent qualifying host。
合格 target 必须是：

- operationally distinct native Windows machine；
- locked user-space environment；
- same GPU class；
- exact package、fixed compiler、attached-only execution；
- Windows MachineGuid 与 NVIDIA GPU UUID 的 domain-separated digest 以及 combined
  identity 都不同于 controller anchor；
- WSL、同机另一目录或第二 virtualenv 都不合格。

receipt 是 self-observed operational evidence，不是 hardware-backed remote
attestation。因此在目标运行成功前，cross-machine 和 portable-package claims 仍为
false；成功后也不能自动推导 serving 或 Runtime readiness。

### 两分钟回答示例

> 我把 artifact 的“可复现”拆成多个可证伪状态。首先 composite manifest 绑定
> Base、tokenizer、Adapter、compiler 和运行配置的 exact bytes；这只证明 package
> identity。然后通过 GitHub 和 Hugging Face 固定 revision 的 metadata、Git blob
> SHA-1 与 SHA-256 绑定 hosted origin；但 commit 是 unsigned，所以不能说作者或
> supply chain 已认证。接着在 caller-supplied clean roots、同一记录环境中 fresh
> load，一次按序运行 20 case、零 retry，raw 和 compiled 都 20/20 exact replay；
> 这仍不是 cross-machine。最后用预先冻结的 rubric 选 FP32 作为 portable test 的
> preferred candidate。当前缺一台 operationally distinct native Windows、同 GPU
> class 的主机，所以 portable、promotion、serving 和 Runtime claims 继续为 false。
> 这套拆分防止一个 hash 被过度解释成整个供应链和部署可靠性。

### 深挖问题

**SHA-256 和 Git blob SHA-1 各有什么作用？**

SHA-256 用于 package bytes 的强 content identity；Git blob SHA-1 按 Git object
编码交叉绑定 hosted tree 中的 blob identity。两者都不是数字签名，也不证明谁创建
或执行了内容。

**clean checkout 为什么仍不是 cross-machine？**

路径隔离能发现隐藏 local dependency、未跟踪文件或 path coupling，但 hardware、
driver、OS identity 仍相同。可移植性需要 operationally distinct target 的显式环境
和行为证据。

**为什么 portable 不等于 serving-ready？**

portable replay 检查 package 在目标机器上复现固定行为；Serving 还要验证并发、
TTFT/TPOT、throughput、KV memory、overload、security、canary、rollback 和 SLO。

### Claim boundary

当前支持 exact offline package、hosted revision origin、same-environment replay、
offline eligibility 和 preferred-next-candidate。独立 cross-machine replay、portable
qualification、hardware-backed attestation、签名、promotion、serving、deployment 与
Runtime integration 均没有完成。

**Sources:** [manifest](../../FC-MVP-001-fp32-attached-offline-package-manifest-v1.md)、
[clean-location replay](../../FC-MVP-001-fp32-attached-offline-package-reproducibility-v1.md)、
[origin attestation](../../FC-MVP-001-fp32-attached-remote-revision-origin-attestation-v1.md)、
[preferred decision](../../FC-MVP-001-fp32-attached-preferred-offline-candidate-decision-v1.md)、
[portable protocol](../../FC-MVP-001-fp32-attached-portable-package-qualification-v1.md)。

---

## 2. 六个故事怎样按岗位组合

| 岗位 | 主故事 | 备用深挖 |
| --- | --- | --- |
| LLM Post-training | 3、4、2 | 5 展示 numerical depth |
| Agent / Tool Use | 1、4、2 | 6 展示 lifecycle discipline |
| Evaluation / Model Quality | 2、4、6 | 3 展示 training iteration |
| AI Infra / ML Systems | 5、6、1 | 4 展示 contract design |
| MLOps / Reproducibility | 6、2、5 | 1 展示 authority boundary |

一轮面试通常准备三个主故事即可：一个端到端、一个最难诊断、一个负结果或取舍。
其余故事用于追问，不要在自我介绍里堆满所有数字。

## 3. 面试时必须主动带出的边界

- 只有单张 RTX 4090 Laptop GPU、1.5B Base、一个主要 LoRA 配置。
- 完整 eval 只有 20 cases；一些 numerics probes 只使用 `eval-001`。
- 指标方向可用于冻结范围内比较，不支持 broad statistical generalization。
- FP32 favorable result 依赖 fixed compiler 和 attached execution。
- same-environment exact replay 不是 cross-machine portability。
- 目前没有 Serving、production deployment、Runtime model integration、Multimodal
  model、preference/RL 或 Multi-Agent implementation evidence。

主动说边界不会削弱故事。相反，它表明你理解实验设计和工程 claim 的范围。
