# 04 数据、评测与实验设计

> 本章是面试学习资料，不是项目进度 tracker。项目顺序与事实状态只以
> PROJECT_STATUS.md 为准。
>
> 证据标签：**[原理]** 表示稳定的理论知识；**[通用工程]** 表示可迁移的工程
> 做法；**[本仓库已实现]** 只表示已有代码、测试、指标或冻结 artifact 支撑；
> **[本仓库待实施]** 表示规划能力，不能在面试中说成做过。
> 仓库证据不自动证明个人作者身份；第一人称示例须先核对本人实际职责。

## 1. 面试定位与学习目标

数据与评测不是训练的附属工作，而是决定结论是否可信的 measurement system。
高级面试通常不只问“用了多少数据、F1 是多少”，而会继续追问：

- 数据是否有合法来源、明确用途和可追溯 provenance？
- train、validation、eval 是否存在 task-family 或语义泄漏？
- 指标是否匹配产品损失，类别不平衡时为什么使用 Macro F1？
- 改进是否来自模型，而不是 compiler、prompt、切分或评测代码变化？
- 小样本结果的不确定性多大，是否有 paired significance test？
- artifact hash 一致能证明哪些事实，又不能证明哪些事实？

学完本章应能：

1. 设计 acquisition 到 frozen eval 的可复现数据流水线；
2. 解释 normalization、dedup、quality、packing 和 token statistics 的取舍；
3. 根据任务单位选择 random、group、task-family 或 temporal split；
4. 手算并解释 Exact Match、field F1、Macro/Micro F1、calibration 与置信区间；
5. 用 preregistration、one-variable experiment、ablation 和 paired comparison
   控制实验；
6. 用 digest、manifest、lineage 和 claim boundary 写出可辩护结论。

## 2. 端到端数据流

**[通用工程]** 一条可审计的数据流可以写成：

~~~text
source registry
  -> acquisition and license/consent gate
  -> immutable raw landing zone
  -> parsing and canonical normalization
  -> PII detection and redaction
  -> exact/near/semantic deduplication
  -> quality and safety filters
  -> group-aware split
  -> tokenizer statistics and packing
  -> versioned train/validation artifacts
  -> separately frozen eval
  -> training and one-way scoring
  -> bad-case taxonomy
  -> reviewed data vN+1
~~~

关键原则有三条：

- 原始数据、清洗后数据、训练数据和评测数据是不同 artifact，不覆盖写；
- 每次变换都记录输入 digest、代码版本、配置、输出 digest 和拒绝原因；
- eval 只能向报告流动，不能把答案、逐例标签或措辞反向流入训练。

## 3. Acquisition、license、consent 与 provenance

### 3.1 Source registry

**[通用工程]** 每个 source 至少记录：

| 字段 | 作用 |
|---|---|
| source_id / URI | 稳定定位来源 |
| owner / provider | 责任主体 |
| acquired_at | 获取时间 |
| revision / snapshot | 避免上游静默变化 |
| license / terms | 允许的训练、派生、再分发范围 |
| consent basis | 用户数据是否有明确同意 |
| allowed_use | pretraining、SFT、eval、reliability-only 等 |
| retention / deletion | 保存期限与删除机制 |
| geography / policy class | 合规边界 |
| raw digest | 锁定实际收到的 bytes |

License 是数据“可以做什么”的 contract，不只是仓库里的一行名字。同一个公开可读
页面未必允许批量训练或再分发；用户同意使用产品也不自动等于同意生成训练轨迹。
真实业务中应由 legal/privacy owner 确认，本章不是法律意见。

### 3.2 Raw landing 与不可变性

**[通用工程]** raw zone 应 append-only，并将下载时间、HTTP metadata、revision、
content length 和 cryptographic digest 写入 manifest。后续修复应生成新版本，不应
偷偷“清理”原文件，否则无法重现旧 dataset。

### 3.3 PII 与 secret redaction

PII 包括姓名、邮箱、电话、地址、账号、设备标识等；secret 包括 token、cookie、
API key、private key 和内部 credential。可靠流程通常组合：

1. deterministic pattern rules：高 precision 识别邮箱、卡号、token pattern；
2. NER / classifier：覆盖上下文相关实体；
3. allowlist 与 denylist：处理领域术语和已知 secret prefix；
4. human sampling：估计漏删率和误删率；
5. irreversible replacement：用类型占位符而非可逆 hash；
6. audit log：只记录类别和计数，不把 secret 再写进日志。

Redaction 的两类错误：

- false negative 会泄露隐私，通常是 fail-closed gate；
- false positive 会破坏任务语义，应通过 sampling、分层规则和 synthetic
  replacement 控制。

## 4. Schema、normalization 与可验证变换

### 4.1 为什么先有 schema

**[原理]** Schema 把“看起来像一条数据”变成 machine-checkable contract。它应
约束版本、必填字段、枚举、长度、嵌套深度、未知字段和跨字段语义。

一个通用的 Agent SFT record 可以包含：

~~~json
{
  "schema_version": 1,
  "example_id": "train-000123",
  "source": {"source_id": "reviewed-seed-v2", "license": "internal-approved"},
  "task_family": "tool_failure/database",
  "instruction": "...",
  "available_tools": ["database_query", "fallback_to_strong_model"],
  "state": {"failed_tools": ["database_query"], "attempt": 2},
  "target": {
    "selected_tool": "fallback_to_strong_model",
    "arguments": {"failed_tool": "database_query"}
  },
  "privacy": {"pii_redacted": true},
  "quality": {"review_status": "accepted"}
}
~~~

这只是通用示例，不是本仓库 schema 的逐字段复制。

### 4.2 Canonical normalization

**[通用工程]** 常见步骤：

- 统一 Unicode normalization，例如 NFC；
- 统一换行与末尾空白，但不要破坏代码缩进；
- 将时间、locale、单位和 enum 映射到明确格式；
- JSON object 使用 canonical key order 和稳定序列化；
- 区分缺失、null、空字符串和空列表；
- 保留 raw_text 或 raw digest，避免变换不可追溯；
- 对 instruction、observation、target 分字段处理，不能把 target 文本混入输入。

Normalization 的危险是“语义误合并”。例如大小写可能决定文件路径，空格可能决定
Python 代码，URL query order 也可能有语义。因此 normalization 必须按 modality 和
field 定义，而不是全局一条正则。

## 5. Dedup、quality 与 token statistics

### 5.1 三层去重

**[原理]**

1. Exact dedup：对 canonical bytes 求 hash，消除完全重复；
2. Near dedup：用 token shingles、MinHash、SimHash 或 edit similarity 找轻微改写；
3. Semantic dedup：用 embedding 相似度或 learned classifier 找释义重复。

若 token 集合分别为 A 与 B，Jaccard similarity 为：

$$
J(A,B)=\frac{|A\cap B|}{|A\cup B|}
$$

其中 A、B 是两个样本的去重 token 集合。阈值越低，泄漏风险越小，但误删不同任务的
概率越高。阈值必须在看结果前锁定，并报告最大 cross-split similarity。

语义 embedding 去重不能替代 exact 检查：embedding 模型和阈值会漂移，而且两个包含
同一答案的样本可能表面相似度不高。最佳实践是多层 fail-closed audit。

### 5.2 Quality filtering

质量不是一个神秘总分，应拆成可解释维度：

- parse/schema validity；
- instruction 是否完整、可解、无歧义；
- target 是否与可用工具、状态和安全规则一致；
- language、length、format 和 domain 分布；
- toxicity、PII、copyright 或 policy 风险；
- reviewer agreement 和 reject reason；
- synthetic source 的 teacher/version/prompt provenance。

训练一个 quality classifier 可以扩展规模，但 classifier score 不能冒充人工真值。
对高风险样本仍需要 review，并监控 filter 对少数类、语言和困难样本的系统性删除。

### 5.3 Packing 与 token statistics

设样本 i 的 token 长度为 $l_i$，最大序列长度为 $L$。未 packing 时 padding waste
可写为：

$$
\text{waste}=1-\frac{\sum_i l_i}{B\cdot L}
$$

其中 B 是 batch 中序列数。Packing 把多个短样本放入一条长度 L 的序列，可显著减少
padding，但必须处理：

- 每个样本的 BOS/EOS 与 chat template；
- label mask，避免对 system/user 或 padding 计算 loss；
- attention boundary，防止不同样本无意互相注意；
- 过长样本的 truncation policy；
- position ids 与 flash-attention 支持；
- packed 和 unpacked eval 的一致性。

需要记录的 token statistics 包括 count、mean、median、P90/P95/P99、max、截断率、
空 target 率、按 task family 的长度分布和每 epoch 实际 supervised tokens。
只报告 record 数会掩盖十倍以上的 token 差异。

## 6. Split：random 何时不够

### 6.1 四种常见切分

| Split | 适用 | 主要风险 |
|---|---|---|
| Random record split | 样本近似 i.i.d. 且无组结构 | 同源模板或用户泄漏 |
| Group split | 同一用户、文档、session 必须同侧 | group 分布不均 |
| Task-family split | 测试组合/模板外泛化 | family 定义需要人工治理 |
| Temporal split | 未来流量、版本迁移 | 时间同时改变多个因素 |

**[原理]** 切分单位应等于模型可能“记住”的最小相关群组。Agent 数据中，同一任务模板
只替换文件名，不能当作独立样本随机拆开；同一 episode 的多个 step 也不能跨 split。

### 6.2 Leakage 与 contamination taxonomy

- exact leakage：相同 instruction/target 跨 split；
- template leakage：同一模板只替换实体；
- family leakage：同一任务策略出现在 train 和 eval；
- answer leakage：eval target、reason code 或答案措辞进入训练；
- provenance leakage：同一个原始 episode 的派生样本跨 split；
- preprocessing leakage：在全数据上拟合 vocabulary、threshold 或 normalizer；
- evaluator leakage：根据逐例 eval 失败反复改 prompt、compiler 或数据；
- benchmark contamination：预训练语料已包含公开 benchmark。

发现 leakage 时应废弃受污染的结论并重新 version 数据，而不是只删除几条后继续沿用旧
指标。

### 6.3 本仓库的 family-aware 例子

**[本仓库已实现]** Tool Router v1 首先冻结 20 个 reviewed seed 和 20 个 eval，
eval 有 10 类、每类 2 例。之后建立 160/40 train/validation、60 个显式
task families，family overlap 与 exact duplicate 均为零。

**[本仓库已实现]** Safety repair v2 只在 train/validation 侧追加 16/8 hard
negatives，得到 176/48、68 个 families；v1 保持 exact prefix，20-case eval digest
不变。最大 cross-split instruction token Jaccard 是 0.4166666666666667，低于预先
规定的 0.8 rejection threshold。这个结果证明注册审计通过，不证明数据覆盖了真实世界。

## 7. Frozen eval 与 offline/online 指标

### 7.1 Frozen eval contract

**[通用工程]** Frozen eval 应绑定：

- case IDs、raw bytes 和 digest；
- scorer source/version 和 metric definitions；
- prompt、compiler、decoding 与 tool registry；
- model/base/adapter revision；
- precision、hardware、seed 和 dependency lock；
- allowed run count、retry policy 和 overwrite policy；
- predeclared gates 与 claim boundary。

一旦逐例答案被用于针对性修改，原集合就从 unbiased test 退化为 development set。
此时应创建新的 holdout，而不是继续称其为 test。

### 7.2 Offline metrics

Offline eval 便于冻结、重放和逐例诊断，常见指标包括格式正确率、tool accuracy、
argument metrics、risk F1、安全计数、latency 和 memory。它的弱点是覆盖有限、环境
简化，以及无法完全反映真实 side effect。

### 7.3 Online metrics

Online eval 包括 shadow、canary、A/B 和 production monitoring，关注 task success、
human escalation、policy denial、duplicate side effect、recovery、latency、cost 和
用户反馈。它更接近真实分布，但受流量选择、季节性、产品变更和 delayed label 影响。

离线通过是进入在线小流量验证的必要条件，不是充分条件。高风险动作通常还要求
deterministic policy gate，不允许只靠平均在线指标。

## 8. Metric 原理与公式

### 8.1 Accuracy 与 Exact Match

$$
\text{Accuracy}=\frac{1}{N}\sum_{i=1}^{N}\mathbb{1}[\hat y_i=y_i]
$$

其中 N 是样本数，$y_i$ 是 gold，$\hat y_i$ 是 prediction。

Argument Exact Match 要求 canonicalized argument object 全部相等。它严格、易解释，
但一个可选字段错误会让整例为零，因此应同时报告 field-level 指标和逐例错误。

### 8.2 Precision、Recall、F1

$$
P=\frac{TP}{TP+FP},\quad
R=\frac{TP}{TP+FN},\quad
F1=\frac{2PR}{P+R}
$$

TP、FP、FN 分别是真阳性、假阳性、假阴性。

对 argument field，可把 canonical key-value pair 当作 item：

- predicted 与 gold 都有且相等：TP；
- 多预测或值错误：FP；
- gold 中缺失或值错误：FN。

Micro F1 先汇总所有类的 TP/FP/FN，再计算 F1，容易被大类主导。Macro F1 先计算每一类
F1，再平均：

$$
F1_{\text{macro}}=\frac{1}{C}\sum_{c=1}^{C}F1_c
$$

其中 C 是类别数。Risk level 等少数类重要的任务应优先看 Macro F1，同时报告每类
support；Micro F1 适合衡量总体实例贡献。不存在“永远更好的 F1”，选择取决于产品损失。

### 8.3 Calibration

分类置信度应回答“预测 0.8 的样本约有 80% 正确吗”。Brier score 为：

$$
\text{Brier}=\frac{1}{N}\sum_{i=1}^{N}(p_i-y_i)^2
$$

其中 $p_i$ 是正类概率，$y_i\in\{0,1\}$。越低越好。

Expected Calibration Error 将样本按置信度分为 M 个 bin：

$$
\text{ECE}=\sum_{m=1}^{M}\frac{|B_m|}{N}
\left|\operatorname{acc}(B_m)-\operatorname{conf}(B_m)\right|
$$

$B_m$ 是第 m 个 bin。ECE 依赖 binning，小数据下不稳定，应配 reliability diagram、
Brier/NLL 和 sample count。

### 8.4 Confidence interval 与 significance

单个 accuracy 的近似区间可用 Wilson interval；模型对比更适合 paired bootstrap：

1. 以 case 为单位有放回抽样 N 个 paired cases；
2. 每次重算候选与基线差值 $\Delta_b$；
3. 重复 B 次；
4. 用 $\Delta_b$ 的 2.5% 和 97.5% 分位数形成 95% CI。

同一分类样本的正确/错误变化还可用 McNemar test，核心只看“基线对、候选错”和“基线错、
候选对”的 discordant pairs。不要用两个独立 t-test 忽略配对结构。

在 20-case eval 上，一例变化就是 0.05 accuracy。即使从 0.20 到 0.25，也只能说
“该冻结集合多正确一例”，不能直接说总体能力稳定提升。应报告逐例变化、置信区间、
effect size 和未建立的 generalization。

## 9. Experimentation：从相关性到可归因

### 9.1 Preregistration

**[通用工程]** 在结果出现前冻结：

- hypothesis 与唯一 primary metric；
- candidate、baseline 和唯一变化；
- dataset/eval digest；
- run count、seed、retry 与 early stop；
- inclusion/exclusion rules；
- pass/fail gate 和 resource cap；
- allowed conclusion 与明确禁止的 claim。

Preregistration 不是官僚文档，而是降低 outcome-driven selection 和 p-hacking 的工程
机制。

### 9.2 One-variable experiment

若想研究 dtype，必须固定 model values、adapter、execution form、prompt、decode 和
case；若同时把 attached 改成 merged，就无法区分 dtype 与 execution-form effect。
工程面试中应主动指出 confounder，并设计 same-dtype 或 same-form control。

### 9.3 Ablation

Ablation 回答“哪个组成部分贡献了变化”。例如：

- Base -> LoRA；
- LoRA -> LoRA + hard negatives；
- raw output -> fixed compiler；
- BM25 -> dense retrieval -> dense + reranker；
- screenshot only -> screenshot + UIA/OCR。

每个 ablation 必须复用同一 eval、scorer 和 gates。一次删多个模块只能得到组合效应。

### 9.4 Bad-case taxonomy

不要把所有错误都叫“数据不够”。建议先按可观察边界分类：

| 层 | 例子 | 下一证据 |
|---|---|---|
| Data | label conflict、family gap | source review、coverage audit |
| Contract | flags 互相矛盾 | validator/compiler counterfactual |
| Model | wrong tool/arguments | raw prediction、logits/probability |
| Numerics | dtype/merge drift | repeat run、same-variable control |
| Runtime | duplicate/unknown outcome | WAL、dispatch receipt、reconcile |
| Evaluator | scorer bug | independent recomputation、negative tests |

只有证据定位到某层，才在该层修复。

## 10. Artifact digest、provenance 与 claim boundary

### 10.1 Hash 能证明什么

若 $H(x)$ 是 SHA-256，重新计算得到 $H(x)=d$ 可以证明“当前 bytes x 与被信任的 digest
d 一致”，并能检测意外或恶意改动。它适合：

- immutable dataset/eval identity；
- manifest 中的 component binding；
- exact replay comparison；
- source/config/report lineage。

### 10.2 Hash 不能单独证明什么

单独的 digest 不能证明：

- 谁创建了文件；
- 文件来自哪个 remote revision；
- creator 有合法授权；
- 某程序真的执行过且只执行一次；
- bytes 在生成前没有被挑选；
- artifact 在另一台机器行为相同；
- 模型安全、可推广、可上线。

这些问题分别需要 signature/identity、remote metadata attestation、license record、
external execution ledger、preregistration、cross-machine replay 和独立 promotion gate。
“hash 一致”等于 identity/integrity 证据，不等于可信来源或完整供应链证明。

### 10.3 Evidence chain

**[通用工程]** 一个最小 evidence graph 应连接：

~~~text
source revisions + raw digests
  -> transform code/config digest
  -> dataset manifest/digest
  -> train config + base revision + adapter digest
  -> eval digest + scorer/compiler digest
  -> raw predictions
  -> independently recomputed report
  -> categorical gate
  -> bounded claim and open blockers
~~~

每个 gate 只回答一个问题。例如“offline artifact eligible”不能自动推出
“cross-machine portable”，更不能自动推出“serving/Runtime ready”。

## 11. 工程落地：pipeline、伪代码与验证

### 11.1 Fail-closed builder

~~~python
def build_dataset(raw_records, source_manifest, config):
    verify_license_and_allowed_use(source_manifest)
    verify_digest(raw_records, source_manifest.raw_digest)

    accepted = []
    rejects = []
    for raw in raw_records:
        try:
            record = parse_and_validate_schema(raw)
            record = normalize_by_field(record)
            record = redact_pii_and_secrets(record)
            verify_target_semantics(record)
            accepted.append(record)
        except DataError as exc:
            rejects.append({"record_id": safe_id(raw), "reason": exc.code})

    accepted = exact_dedup(accepted)
    accepted = near_dedup_with_audit(accepted, config.near_dup_threshold)
    splits = group_split(accepted, key=lambda x: x["task_family"])
    assert_no_cross_split_family_overlap(splits)
    assert_no_eval_answer_leakage(splits, config.frozen_eval)

    stats = compute_token_and_distribution_stats(splits)
    artifacts = canonical_write(splits, stats, rejects)
    return bind_manifest(artifacts, source_manifest, config)
~~~

要点是任何验证错误都有稳定 error code；builder 不静默修复 target；输出使用 canonical
serialization；manifest 绑定所有直接输入。

### 11.2 Independent scorer

~~~python
def score_frozen_eval(predictions, eval_set, scorer_contract):
    verify_all_hashes(predictions, eval_set, scorer_contract)
    paired = align_by_example_id(predictions, eval_set)
    metrics = {
        "tool_accuracy": accuracy(
            [p.tool for p, _ in paired],
            [g.tool for _, g in paired],
        ),
        "argument_exact_match": argument_em(
            [p.args for p, _ in paired],
            [g.args for _, g in paired],
        ),
        "argument_field_f1": field_f1(
            [p.args for p, _ in paired],
            [g.args for _, g in paired],
        ),
        "risk_macro_f1": macro_f1(
            [p.risk for p, _ in paired],
            [g.risk for _, g in paired],
        ),
    }
    safety = recompute_safety_counts(paired)
    return canonical_report(metrics, safety, per_case_diffs=paired)
~~~

真实实现应避免报告“自报 pass”。Validator 必须从 raw predictions 和 frozen gold 重新
计算指标、gate、classification 和 next action，并用 negative tests 验证篡改会失败。

## 12. Metrics 与 gates

一个 Agent data/eval gate 可以包含：

| Gate | 示例条件 | 为什么 |
|---|---|---|
| Schema | 100% valid，未知字段 fail closed | 避免脏数据静默进入 |
| Provenance | 所有 source/revision/license 可解析 | 保证可审计 |
| Privacy | secret 为零；PII sampling 达阈值 | 控制隐私风险 |
| Split | group/family overlap 为零 | 防止虚高 |
| Leakage | exact 为零，near-dup 低于预注册阈值 | 保护 holdout |
| Distribution | 每类 support、长度、tool 分布在预算内 | 防止样本塌缩 |
| Quality | label conflict 与 dangerous target 为零 | 保证 target 可信 |
| Functional | primary metric 达阈值 | 验证能力 |
| Regression | 逐例关键维度不退化 | 防止平均数掩盖退化 |
| Safety | dangerous false approvals/action candidates 为零 | 高风险硬门禁 |
| Performance | latency/memory/cost 在 cap 内 | 保证可运行 |

Gate 阈值应在看候选结果前固定。Safety 指标通常不是与质量加权求和，而是必须独立通过。

## 13. Failure modes 与排障

| 现象 | 常见原因 | 最先检查 |
|---|---|---|
| Validation 很高、eval 很低 | family/template leakage 或过拟合 | split manifest、near-dup audit |
| Exact Match 低、field F1 高 | 少数字段缺失或 normalization 差异 | per-field confusion |
| Micro F1 高、Macro F1 低 | 大类主导、少数类失败 | per-class support/F1 |
| 指标突然全部变化 | eval/scorer/prompt/compiler 漂移 | direct digests、git diff |
| 重跑差异 | sampling、seed、kernel、依赖或输入顺序 | execution audit |
| 数据量增加但变差 | label conflict、distribution shift、hard-negative 失真 | reject taxonomy、family slice |
| Calibration 变差 | temperature/decoding 改变或 overconfidence | reliability diagram、Brier |
| Hash 相同但来源仍有争议 | 只有 content identity，无 origin trust | remote revision/signature chain |
| 在线成功率升、安全事故也升 | 平均目标掩盖 tail risk | safety hard gate、side-effect audit |

排障顺序应从 identity 和 measurement system 开始，再看数据和模型；否则可能在修一个
scorer bug。

## 14. 概念比较速查

| 概念 A | 概念 B | 核心差异 |
|---|---|---|
| Validation set | Test/frozen eval | 前者可用于选型；后者只做最终无偏评估 |
| Random split | Group/task-family split | 后者按潜在记忆单位隔离 |
| Exact dedup | Semantic dedup | bytes/规范化相同 vs 含义近似 |
| Exact Match | Field F1 | 整体全对 vs 局部键值质量 |
| Macro F1 | Micro F1 | 类别等权 vs 实例/事件等权 |
| Accuracy | Calibration | 预测对不对 vs 置信度是否可信 |
| Offline eval | Online eval | 可控可重现 vs 真实分布和副作用 |
| Ablation | Hyperparameter sweep | 组件因果贡献 vs 配置搜索 |
| Digest | Signature | 内容身份/完整性 vs 签名者身份与授权链 |
| Reproducibility | Generalization | 同条件复现 vs 新分布仍有效 |

## 15. 高频面试问题与分层回答

### Q1：为什么不能 random split？

**30 秒回答**

Agent 数据有强 group 结构：同一 task template、用户、文档或 episode 的多个 step 高度
相关。Random split 会把几乎相同的策略放在 train 和 eval，指标虚高。我会以模型可能
记住的最小群组做 group/task-family split，再做 exact、near-duplicate 和 provenance
leakage audit。

**2 分钟回答**

先定义 family key，例如工具失败类型加业务场景；同一 source episode 的派生数据也绑定
同一 group。切分后检查 family overlap 为零、exact duplicate 为零、cross-split
Jaccard/MinHash 低于预注册阈值，并单独锁定 eval digest。项目中 v1 的 160/40 数据按
60 families 切分；v2 追加后是 176/48、68 families，eval 仍是独立 20 cases。最大
cross-split token Jaccard 0.4167，低于 0.8 gate。

**深挖追问**

若 family 定义过粗会损失样本效率，过细仍会泄漏。我会抽样查看临界 pair，并做
template/source/session 多键审计。对于未来分布还会增加 temporal holdout，而不是用一个
split 回答所有问题。

### Q2：20-case 上 accuracy 提升 0.05，怎么解释？

**30 秒回答**

它等于多正确一例，只能说明该冻结集合上的 paired improvement，不能直接声称总体能力
提升。我会报告改变的是哪一例、是否有其他维度退化、paired CI/显著性，以及结果只属于
固定 eval、compiler 和运行环境。

**2 分钟回答**

项目 FP32 compiled argument exact match 从 0.20 到 0.25，严格改善只有
eval-016.arguments；field F1 同时从约 0.2609 到 0.2979，安全和逐例 regression gate
没有退化。但 raw semantic validity 反而从 0.85 到 0.80，所以不能说 FP32 修复了
decision consistency，fixed compiler 仍是 candidate identity 的一部分。下一步需要
更大独立 holdout 或新分布验证。

**深挖追问**

小样本可做 exact paired bootstrap 或 McNemar test，但无论 p-value 如何，都要看
effect size 和产品重要性。不能通过反复跑 seed 或改数据挑一个更好结果。

### Q3：Macro F1 和 Micro F1 怎么选？

**30 秒回答**

Macro F1 让每个类别等权，适合 risk level 等少数类也关键的场景；Micro F1 汇总所有
事件，更反映总体样本贡献，但会被大类主导。我会同时报告 per-class support 和 confusion
matrix，不靠单个平均数。

**2 分钟回答**

先从产品成本定义类别。例如 critical risk 漏判即使只占 1%，也不能被 normal 类的高
准确率淹没，因此 risk classification 用 Macro F1 并加危险 false approval 硬门禁。
Argument field 由大量 key-value event 构成时可用 Micro F1，但还要配 Exact Match 看
完整调用是否正确。

**深挖追问**

若某类没有 predicted positive，precision 的零除定义必须固定；类别 support 很小时
Macro F1 方差大，应给 bootstrap interval，并避免通过重定义 label 改善数字。

### Q4：hash 一致为什么不等于来源可信？

**30 秒回答**

SHA-256 一致说明 bytes 与一个被信任的 digest 一致，解决 identity/integrity；它不说明
谁创建、从哪来、是否合法，也不证明程序真的执行过。Origin 还要绑定 remote
revision/metadata，作者身份要 signature，执行事实要 ledger/attestation。

**2 分钟回答**

我会把 trust root 写清：谁提供 expected digest、digest 绑定哪些直接文件、是否独立重算。
项目先做 metadata manifest 和 same-environment replay，之后才独立绑定 GitHub commit/
tree/LFS 与 Hugging Face revision/file metadata。即使 origin gate 通过，GitHub commit
仍是 unsigned，所以 author/signature 和 supply-chain transparency claim 继续为 false。

**深挖追问**

即使签名有效，也只证明某 key 对某 bytes 签名；还需 key ownership、revocation、
transparency log 和构建 provenance。Cross-machine behavior 又是另一道 gate。

## 16. 本项目证据映射

### [本仓库已实现]

- Tool Router decision schema v1：20 reviewed seed、20 frozen eval、10 类各 2 例；
- v1 data：160/40 train/validation，60 task families，family overlap 和 exact
  instruction duplicate 均为零；
- safety repair v2：只追加 train/validation 16/8，形成 176/48、68 families，
  v1 保持 exact prefix，eval digest 不变；
- cross-split 最大 instruction token Jaccard 0.4166666666666667，预注册拒绝阈值
  为 0.8；
- frozen eval 的 deterministic scorer、schema validation、distribution/leakage
  audit、dangerous-action checks 和 negative tests；
- Base、LoRA v1、LoRA v2、compiler、BF16/FP32 数值路径与 artifact gates 的冻结
  raw evidence；
- FP32 fixed-compiler 20-case 结果：argument Exact Match 0.20 -> 0.25，
  field F1 0.2608695652173913 -> 0.29787234042553196；严格改善仅一例；
- manifest、clean-location exact replay、remote revision origin 与 offline artifact
  eligibility 已分别形成独立 gate；
- 当前 portable-package qualification protocol 已冻结，但没有独立机器结果。

### [本仓库待实施]

- 大规模 licensed acquisition、通用 PII/secret redaction engine、token packing lab；
- 公开 benchmark contamination 检测和更大独立 holdout；
- online A/B、canary、生产 calibration/drift monitoring；
- 多 seed 统计功效研究与跨机器 portable-package 正式结果；
- Data Engine/CPT 的 DATA-001 至 DATA-005 完整流水线。

面试时可以说“我已经实现并验证了 task-family split、frozen eval、泄漏审计和
artifact evidence chain”，不能说“已经建成通用数据平台或在线评测系统”。

## 17. 自测与实践

### 自测题

1. 为什么同一用户的 session step 不能随机拆到 train 和 eval？
2. Jaccard 0.4 是否一定无泄漏？还需检查哪些维度？
3. Argument Exact Match 与 field F1 分别捕获什么错误？
4. 为什么 risk Macro F1 通过仍不能取消 dangerous false approval gate？
5. frozen eval 被用于三轮逐例调参后应如何处理？
6. Paired bootstrap 为什么按 case pair 一起重采样？
7. digest、signature、origin attestation、replay 分别回答什么问题？
8. 为什么 compiler 改善不能记成 model improvement？

### 实践任务

1. 为一个 1000 条 tool-use 数据集设计 source manifest 和 reject taxonomy；
2. 实现 exact hash + token Jaccard 的 split leakage audit，并构造三个 negative tests；
3. 对一组 gold/prediction 手算 Exact Match、field F1、Macro/Micro F1；
4. 对两个模型的 paired correctness 做 10,000 次 bootstrap，输出差值和 95% CI；
5. 写一页 preregistration，只允许改变一个变量，并列出至少五个禁止 claim；
6. 画出 dataset -> model -> prediction -> report 的 digest lineage，并指出每个 trust root。

完成标准不是“能背定义”，而是能面对一个漂亮指标，先检查数据身份、切分、scorer、
不确定性和 claim boundary，再决定它是否值得相信。
