# 06 Multimodal GUI、Retrieval 与 Verifier

> 本章是面试学习资料，不是项目进度 tracker。项目顺序与事实状态只以
> PROJECT_STATUS.md 为准。
>
> 证据标签：**[原理]**、**[通用工程]**、**[本仓库已实现]**、
> **[本仓库待实施]**。本章的 GUI VLM、Embedding/Reranker、learned
> Verifier/Reward Model 大部分属于通用面试知识与后续计划；除明确标记的 Lane A
> mapper 和当前文本 Tool Router 外，不得表述为本仓库已训练或上线。
> 仓库证据不自动证明个人作者身份；第一人称示例须先核对本人实际职责。

## 1. 面试定位与学习目标

本章覆盖三条经常在 Multimodal/Agent 岗位交叉出现的链路：

~~~text
screen perception
  -> GUI grounding
  -> action proposal
  -> Runtime gate and execution

query
  -> candidate retrieval
  -> reranking
  -> grounded context/action candidates

state + candidate/trajectory
  -> verifier or reward score
  -> threshold/abstain
  -> deterministic Agent gate
~~~

面试官通常会追问：

- Vision encoder 如何把 image 转成 LLM 可消费的 tokens？
- GUI 中 screenshot、OCR 和 UIA 为什么需要融合？
- 坐标 grounding 与最终 task success 为什么必须分别评测？
- Bi-encoder 为什么快，Cross-Encoder 为什么适合 reranking？
- Recall@K、MRR、NDCG 分别衡量什么？
- Outcome reward 与 process reward 有什么偏差？
- Verifier accuracy 很高，为什么仍可能不适合做 gate？
- 如何用 calibration、threshold 和 coverage-risk 控制拒答/回退？

学完应能：

1. 解释 VLM 的 vision encoder、projector、token budget 和 multimodal SFT；
2. 设计 screenshot/UIA/OCR 融合与 GUI action representation；
3. 推导 contrastive learning/InfoNCE，并设计 retrieval + reranking pipeline；
4. 计算 Recall@K、MRR、NDCG，理解 ANN 的 latency/recall/memory trade-off；
5. 区分 Verifier、Reward Model、Outcome/Process reward 和 deterministic oracle；
6. 设计 calibrated Agent gate，并准确陈述本项目的现有与待实施边界。

## 2. VLM 基础：从像素到语言 token

### 2.1 Vision encoder

**[原理]** 常见 vision encoder 是 ViT 或其变体。对高 H、宽 W 的图像，以 P × P
patch 划分，若 padding 到 patch 整数倍，patch token 数近似为：

$$
N_{\text{patch}}=
\left\lceil\frac{H}{P}\right\rceil
\times
\left\lceil\frac{W}{P}\right\rceil
$$

其中 H、W 是像素尺寸，P 是 patch size。每个 patch 展平后经 linear projection 得到
$d_v$ 维视觉向量，并加入 position information，再经过 Transformer blocks。

GUI screenshot 通常高分辨率且文字密集。若 P 太大，细小文字和 icon 消失；若 P 太小，
token 数按面积增长，attention cost 和 LLM context 快速上升。工程上常用：

- resize + fixed resolution；
- dynamic resolution；
- tiling/cropping；
- token pooling/resampler；
- region proposal 后只编码相关区域；
- OCR/UIA 辅助，减少仅靠像素理解文字的压力。

### 2.2 Projector / connector

Vision encoder 输出维度 $d_v$，LLM hidden size 为 $d_l$，需要 projector 映射：

$$
Z = f_{\theta}(V),\quad
V\in\mathbb{R}^{N_v\times d_v},\quad
Z\in\mathbb{R}^{N'_v\times d_l}
$$

其中 V 是视觉特征，$f_{\theta}$ 可以是 linear、MLP、Q-Former、Perceiver resampler 或
cross-attention connector；$N'_v$ 可以等于或小于原视觉 token 数。

Projector 不只是“对齐维度”。它还决定视觉信息压缩、token budget 和梯度如何流回
vision tower。只训练 projector 成本低，但领域适配能力有限；解冻部分 vision encoder
或 LLM 能力更强，显存和灾难性遗忘风险也更高。

### 2.3 三种融合形态

| 形态 | 做法 | 优点 | 代价 |
|---|---|---|---|
| Prefix visual tokens | 视觉 tokens 拼入 LLM sequence | 结构简单、复用 decoder | context 成本高 |
| Cross-attention | LLM layers 读取独立视觉 memory | 图文流分离 | 架构改动和 serving 复杂 |
| Unified tokenizer | 图像离散 token 与文本同一序列 | 统一生成接口 | tokenizer/训练成本高 |

Prefix VLM 中，语言序列 attention 复杂度近似随 $(N_t+N_v)^2$ 增长，其中 $N_t$ 是文本
token 数，$N_v$ 是视觉 token 数。GUI 长 context 场景必须监控 image tokens 占比。

### 2.4 Multimodal tokenization

除了 patch tokens，还需要定义：

- image start/end 和 image placeholder tokens；
- 多图的 image index；
- coordinate/box 表示：连续数值、离散 bins 或 special location tokens；
- OCR/UIA serialization；
- action/result/post-state 的 role/template；
- 哪些 token 参与 supervised loss。

坐标可归一化到 $[0,1]$：

$$
x_n=\frac{x}{W},\quad y_n=\frac{y}{H}
$$

其中 $(x,y)$ 是当前 coordinate frame 中的像素坐标。若离散为 K 个 bins：

$$
b_x=\operatorname{round}(x_n(K-1))
$$

必须记录 frame 是全屏、窗口、crop 还是 content area，并绑定 screenshot dimensions、
DPI scaling、window offset 和 observation revision。只保存一个裸坐标无法重放。

## 3. GUI perception：Screenshot、OCR 与 UIA 融合

### 3.1 三种 observation 的互补性

| Signal | 强项 | 典型失败 |
|---|---|---|
| Screenshot | 真实视觉、布局、图标、canvas | 无结构、文字小、坐标/DPI 敏感 |
| OCR | 图中文字与 box | 误识别、阅读顺序、遮挡、同名文本 |
| UIA/accessibility tree | role、name、state、控件层级 | 缺失、陈旧、自绘控件不可见 |

**[原理]** 三者不是谁替代谁，而是 multiple noisy views。Screenshot 是像素事实，UIA
提供语义和 stable element 属性，OCR 弥补 accessibility 缺失。融合模型还需显式处理
冲突：例如 UIA 说按钮 enabled，但 screenshot 已弹出遮罩。

### 3.2 Fusion 设计

常见方案：

1. Early fusion：把 screenshot tokens 与序列化 UIA/OCR 一起送入 VLM；
2. Region fusion：将 UIA/OCR box 与视觉 region feature 对齐；
3. Candidate fusion：先由 UIA/OCR 生成候选元素，再用 VLM 选择；
4. Late ensemble：像素 grounding 与结构 grounding 独立打分，再 deterministic merge。

工程上应为每个 element 构造稳定 record：

~~~json
{
  "element_id": "obs-42:uianode-108",
  "role": "button",
  "name": "Save",
  "state": {"enabled": true, "visible": true},
  "bbox_norm": [0.71, 0.91, 0.79, 0.96],
  "uia_path": ["Window", "Dialog", "Button"],
  "ocr_text": "Save",
  "source_confidence": {"uia": 1.0, "ocr": 0.96},
  "observation_revision": "sha256:..."
}
~~~

这只是通用示例。element_id 必须属于一次 observation，不能假设跨帧永久稳定。

### 3.3 Grounding

Grounding 是把自然语言 target 映射到屏幕实体或区域：

$$
g:(I,T,U,O)\rightarrow(e,b,p,c)
$$

其中 I 是 screenshot，T 是任务文本，U 是 UIA tree，O 是 OCR，e 是 element ID，
b 是 bounding box，p 是 click point，c 是 confidence。

常见 supervision：

- point grounding；
- box prediction；
- element classification；
- referring expression matching；
- next-action target；
- post-state change。

Point-in-box accuracy 可定义为：

$$
\text{PointAcc}=
\frac{1}{N}\sum_i
\mathbb{1}[p_i\in b_i^{gold}]
$$

Intersection over Union：

$$
\operatorname{IoU}(A,B)=\frac{|A\cap B|}{|A\cup B|}
$$

IoU 衡量 box 几何重合，但小按钮上轻微偏移可能导致巨大 IoU 变化；最终还要看点是否落在
可点击区域和动作后状态。

### 3.4 Action representation

一个 GUI action candidate 应至少表达：

- action type：click、type、scroll、select、shortcut、wait、clarify、reject；
- target element ID 和/或 normalized point/box；
- coordinate frame 与 observation revision；
- text/value 等 arguments；
- expected precondition/postcondition；
- risk、approval、fallback；
- evidence references。

优先使用 stable element reference + geometry backup，而不是只输出绝对像素。执行前由
Runtime re-observe/ground，检查窗口、焦点、DPI、遮挡、target revision 和 approval。

## 4. Multimodal SFT 与 hard negatives

### 4.1 Episode schema

**[通用工程]** 一个富 GUI episode 可以包含：

~~~json
{
  "episode_id": "ep-...",
  "consent": {"capture_id": "...", "scope": "gui_training", "granted": true},
  "instruction": "...",
  "observation": {
    "screenshot_ref": "sha256:...",
    "uia_ref": "sha256:...",
    "ocr_ref": "sha256:...",
    "frame": {"width": 2560, "height": 1440, "dpi_scale": 1.5}
  },
  "candidate_action": {
    "type": "click",
    "target_element": "obs-42:uianode-108",
    "point_norm": [0.75, 0.94]
  },
  "runtime_decision": {"policy": "allow", "approval_id": null},
  "result": {"dispatch_status": "succeeded"},
  "post_state": {"verifier_label": "goal_progressed"},
  "privacy": {"redacted": true, "masked_regions": 3}
}
~~~

Schema 必须绑定 consent、source/revision、redaction、retention 和 deletion lineage。模型
自报“成功”不能成为 label；需要 UI/state oracle、deterministic assertion 或 human review。

### 4.2 SFT objective

自回归 action generation 的 token-level cross-entropy：

$$
\mathcal{L}_{\text{SFT}}
=-\sum_{t\in\mathcal{T}_{target}}
\log p_{\theta}(y_t\mid y_{<t},x,I)
$$

其中 x 是文本/结构 context，I 是视觉 observation，$y_t$ 是 target action token，
$\mathcal{T}_{target}$ 只包含需要监督的 assistant/action tokens。System、user、image
placeholder 和 padding 通常 mask 掉。

也可拆成 multi-task loss：

$$
\mathcal{L}
=\lambda_a\mathcal{L}_{action}
+\lambda_g\mathcal{L}_{grounding}
+\lambda_r\mathcal{L}_{risk}
+\lambda_v\mathcal{L}_{validity}
$$

$\lambda$ 是各任务权重。必须做 ablation，避免一个辅助 loss 提升 proxy metric 却伤害
task success。

### 4.3 Hard negatives

有效 hard negative 与正例表面接近，但行为错误：

- 相邻同类按钮；
- 同名元素但错误窗口/对话框；
- stale screenshot 上曾存在的元素；
- OCR 文本相同、role 不同；
- 正确 action type、错误 argument；
- click point 在 box 附近但不可交互；
- destructive action 替代 safe clarification/rejection；
- tool result 自报成功但 post-state 未变化；
- instruction injection 指向不相关敏感操作。

Hard negative 不能由随意扰动生成后直接当真值。需要保证负例确实错误、没有 false negative，
且不泄露 eval answer。训练时可做 ranking、classification 或 contrastive objective。

### 4.4 数据增强

GUI 可用 resize、crop、DPI、theme、font、window position、轻度 blur/compression 等增强，
但 box/point 必须同步变换。不能使用会改变语义的 augmentation，例如遮掉关键状态、把
disabled 变 enabled 或改变 OCR 文本却保留原 label。

## 5. GUI 应用与评测

### 5.1 分层指标

| 层级 | 指标 |
|---|---|
| Perception | OCR CER/WER、UIA coverage、element detection recall |
| Grounding | PointAcc、IoU@threshold、element accuracy |
| Action | action type accuracy、argument EM/F1、validity |
| Safety | dangerous false approval、wrong-target destructive action |
| Runtime | duplicate side effect、grounding rejection、unknown outcome |
| Task | independently verified task success、steps/cost/latency |

只看 action exact match 会低估多个合法动作路径；只看 task success 又无法定位 perception、
grounding 或 execution 问题。最佳实践是层级 metric + end-to-end gate。

### 5.2 Scenario slices

至少按以下 slice 报告：

- resolution/DPI/theme/language；
- native control vs custom canvas；
- text-rich vs icon-only；
- occlusion/modal dialog；
- dynamic/stale UI；
- single vs multiple monitors；
- dangerous/approval-required；
- OCR/UIA missing 或 conflicting；
- unseen app/task family。

### 5.3 工程验证

- 所有坐标随 image transform 做 property test；
- screenshot/UIA/OCR revision 必须一致；
- 目标 box 不得越界，point 必须属于声明 frame；
- 每个 action 绑定 pre-state 与 post-state；
- stale observation 强制拒绝或 re-ground；
- replay 必须区分模型 proposal 与 Runtime execution；
- UI 操作测试若可能被用户 mouse/keyboard/focus 干预，应作废该 attempt 后重新观察和执行，
  不能直接归因为模型/代码失败。

最后一条是 live desktop evidence 的 attribution 规则，不等于新增产品 capability。

## 6. Embedding 与 contrastive learning

### 6.1 Embedding

Embedding model 将 query/document 映射到低维向量：

$$
q=f_{\theta}(x_q),\quad d=g_{\phi}(x_d)
$$

相似度常用 dot product 或 cosine：

$$
\operatorname{cos}(q,d)=
\frac{q^\top d}{\|q\|_2\|d\|_2}
$$

若向量已 L2-normalized，cosine 等于 dot product。是否 normalize 必须与训练和 index
配置一致。

### 6.2 Bi-encoder

Bi-encoder 独立编码 query 和 document，可以预计算 document embeddings 并用 ANN 检索。
复杂度低、吞吐高，适合第一阶段召回；但 query-document token 不能做完整交互，对细粒度
条件和否定词可能较弱。

### 6.3 InfoNCE

一个 batch 中，第 i 个 query 的正例为 $d_i^+$，候选 documents 为 $d_j$：

$$
\mathcal{L}_i
=-\log
\frac{\exp(s(q_i,d_i^+)/\tau)}
{\sum_{j=1}^{B}\exp(s(q_i,d_j)/\tau)}
$$

其中 s 是相似度，$\tau>0$ 是 temperature，B 是 batch size。总 loss 是 batch 平均。

Temperature 越小，分布越尖锐，hard negative 梯度更强，也更易受 mislabeled negative
影响。In-batch negatives 高效，但 batch 中可能包含语义上也相关的 false negatives。

### 6.4 Negative mining

- Random negatives：容易，训练信号很快饱和；
- BM25 negatives：词面相似；
- Existing retriever hard negatives：模型容易混淆；
- Cross-encoder mined negatives：质量高但成本大；
- In-domain adversarial negatives：最接近部署分布；
- Multi-positive：避免把多个正确文档误当负例。

Mining model/version 和 retrieval corpus 必须记录，否则 dataset 会随着 index 漂移。

## 7. Retrieval pipeline 与 ANN

### 7.1 两阶段架构

~~~text
query
  -> normalize and ACL filter
  -> sparse/dense/hybrid retrieval
  -> top K candidates
  -> cross-encoder reranker
  -> top N evidence
  -> context assembly with provenance
  -> answer/action proposal
~~~

Recall stage 的目标是“不漏掉正确文档”，reranker 的目标是把最相关候选排前。若正确文档
没进入 top K，再强的 reranker 也无法恢复。

### 7.2 Sparse、Dense 与 Hybrid

| 方法 | 优点 | 弱点 |
|---|---|---|
| BM25/sparse | exact term、ID、稀有词强，可解释 | 语义改写弱 |
| Dense embedding | 语义召回、跨措辞 | exact identifier、distribution shift |
| Hybrid | 兼顾词面和语义 | 融合与调参复杂 |

Hybrid 可用 score normalization、weighted sum 或 Reciprocal Rank Fusion。RRF：

$$
\operatorname{RRF}(d)=\sum_{r\in R}\frac{1}{k+\operatorname{rank}_r(d)}
$$

R 是多个 ranked lists，k 是平滑常数。RRF 不依赖不同 retriever 的 raw score 同尺度。

### 7.3 ANN 选型

| Index | 核心思想 | 优点 | 代价 |
|---|---|---|---|
| Flat exact | 全量相似度 | recall 基准 | latency/compute 高 |
| HNSW | 多层近邻图搜索 | 高 recall、低延迟 | memory 和 build 成本 |
| IVF | coarse centroid 分桶 | 可控扫描量 | 需训练、nprobe 调优 |
| PQ | 向量子空间量化 | 大幅省内存 | quantization recall loss |
| IVF-PQ | 分桶 + 压缩 | 超大规模 | 调参和精度损失 |

ANN benchmark 必须同时报告 recall against exact search、P50/P95/P99 latency、QPS、
index size、build time、update/delete 和 filter performance。只报 QPS 可能是通过牺牲
recall 得到。

### 7.4 Metadata 与 ACL

检索必须在用户权限范围内。常见做法：

- index-time tenant/ACL metadata；
- query-time filter；
- retrieval 后再次 authorization check；
- source revision/freshness；
- delete/tombstone propagation；
- context 中保留 citation/provenance。

先检索全库再让 LLM“不要泄露”不是安全设计。

## 8. Reranker / Cross-Encoder

Cross-encoder 将 query 和 document 拼接后联合编码：

$$
r_{\psi}(q,d)=\operatorname{MLP}(h_{\text{CLS}}(q,d))
$$

因为 token 可做 full interaction，它通常比 bi-encoder 排序精确，但每个 query-document
pair 都要 forward，成本约随 candidate 数线性增长。因此典型部署是 bi-encoder 召回
top 50/100，再 cross-encoder 排 top 5/10。

训练目标：

- pointwise binary/relevance regression；
- pairwise margin/ranking loss；
- listwise softmax；
- distillation from stronger teacher。

Pairwise logistic loss 示例：

$$
\mathcal{L}
=-\log\sigma(r(q,d^+)-r(q,d^-))
$$

$d^+$、$d^-$ 是相关/不相关文档，$\sigma$ 是 sigmoid。若 negative 实际也相关，模型会
学到错误偏好，所以 relevance judgment 与 multi-positive 标注很关键。

## 9. Retrieval metrics

设 query 集合为 Q，相关文档集合为 $R_q$，top K 检索结果为 $S_q^K$。

### 9.1 Recall@K

$$
\operatorname{Recall@K}
=\frac{1}{|Q|}\sum_{q\in Q}
\frac{|R_q\cap S_q^K|}{|R_q|}
$$

它衡量相关文档被召回多少。若每个 query 只有一个 relevant item，常见的 Hit@K 与
Recall@K 数值相同；多相关文档时不能混用。

### 9.2 MRR

$$
\operatorname{MRR}
=\frac{1}{|Q|}
\sum_{q\in Q}\frac{1}{\operatorname{rank}_q}
$$

$\operatorname{rank}_q$ 是第一个相关结果的 rank；若 top cutoff 内没有则贡献 0。MRR
强调第一个正确结果，适合只需要一个答案/工具候选的场景，不关心后续相关项。

### 9.3 NDCG@K

$$
\operatorname{DCG@K}
=\sum_{i=1}^{K}
\frac{2^{rel_i}-1}{\log_2(i+1)}
$$

$rel_i$ 是第 i 位结果的 graded relevance。归一化：

$$
\operatorname{NDCG@K}
=\frac{\operatorname{DCG@K}}{\operatorname{IDCG@K}}
$$

IDCG 是同一 query 的理想排序 DCG。NDCG 适合多级相关性和整条 top list 质量。

### 9.4 指标陷阱

- query-level macro average 与把所有 documents pooled 起来不同；
- 没有完整 relevance judgment 会把未标注相关文档当负例；
- 只看 reranker NDCG，忽略 first-stage Recall@K；
- index corpus、ACL 或 duplicate 变化导致不可比；
- ANN 与 exact search 未做 recall comparison；
- K 选择与下游 context budget 不一致；
- offline relevance 高但最终 task success 不升。

## 10. Verifier 与 Reward Model

### 10.1 Verifier

Verifier 对 candidate answer/action/trajectory 进行 correctness、safety、constraint 或
outcome 判断。输入可能是：

$$
v_{\omega}(s,a,o,\tau)\rightarrow
\{\text{label},\text{score},\text{reason}\}
$$

其中 s 是 pre-state，a 是 action，o 是 observation/result，$\tau$ 是 trajectory。

Verifier 可以是：

- deterministic rule/schema checker；
- executable unit test / environment oracle；
- learned classifier/ranker；
- LLM-as-judge；
- human review。

可靠系统优先使用能直接观察的 deterministic oracle；learned verifier 用于规则难覆盖的
语义层，并需要 calibration 和 abstention。

### 10.2 Reward Model

Reward Model 将 response/trajectory 映射为 scalar reward，常用于 preference
optimization 或 RL。Pairwise Bradley-Terry 形式：

$$
P(y_a\succ y_b)
=\sigma(r_{\omega}(x,y_a)-r_{\omega}(x,y_b))
$$

其中 x 是 context，$y_a,y_b$ 是两个候选，$r_{\omega}$ 是 reward score。训练目标最大化
observed preference likelihood。

Reward score 不是绝对真值，跨 prompt/domain/model version 不一定可比。对训练策略优化
时尤其要防 distribution shift 与 reward hacking。

### 10.3 Outcome reward vs Process reward

| Reward | 定义 | 优点 | 风险 |
|---|---|---|---|
| Outcome reward | 只看最终状态/答案 | 目标直接、较少规范错误路径 | 稀疏、credit assignment 难 |
| Process reward | 对中间 step 打分 | dense signal、便于长 horizon | 标注贵、可能奖励表面步骤 |

Outcome reward 应来自环境 post-state、test、transaction receipt 等，而不是模型自报。
Process reward 需要明确哪些路径等价，避免把一种 reviewer 偏好变成唯一“正确思路”。
实践中常用最终 outcome hard gate + calibrated process score 辅助搜索。

### 10.4 Verifier vs Runtime policy

Learned verifier 可以判断“这条操作看起来有 98% 概率正确”，但不能覆盖 deterministic
policy denial、权限、approval 或 budget。一个合理顺序：

~~~text
schema/contract checks
  -> deterministic policy and authorization
  -> learned verifier score
  -> accept / abstain / fallback / human review
  -> Runtime grounding and execution
  -> independent post-state verification
~~~

Verifier 是 gate 的一个 signal，不是唯一 authority。

## 11. Calibration、threshold 与 coverage-risk

### 11.1 为什么 accuracy 不够

若 verifier accuracy 95%，错误可能集中在高置信度 dangerous actions 上；此时无法安全
设阈值。需要 calibration、class-conditional recall、cost-sensitive metrics 和 tail
slice。

### 11.2 Threshold selection

对 binary verifier，score $p$，阈值 t：

- $p\ge t$：accept；
- 中间区间：abstain/fallback/human；
- 低分：reject。

阈值应在独立 calibration set 上按业务成本选，不在 final eval 上调。若 false accept
成本 $C_{FA}$、false reject 成本 $C_{FR}$，可最小化：

$$
\hat R(t)
=C_{FA}\cdot \widehat{P}(\text{FA}\mid t)
+C_{FR}\cdot \widehat{P}(\text{FR}\mid t)
$$

高风险场景仍应有 categorical zero-tolerance gate，不能只靠平均 expected cost。

### 11.3 Coverage-risk

选择性预测只接受置信度满足阈值的样本。设接受集合：

$$
A_t=\{i:c_i\ge t\}
$$

Coverage：

$$
\operatorname{Coverage}(t)=\frac{|A_t|}{N}
$$

Selective Risk：

$$
\operatorname{Risk}(t)
=\frac{1}{|A_t|}
\sum_{i\in A_t}\ell(\hat y_i,y_i)
$$

$c_i$ 是 confidence，$\ell$ 是错误 loss。提高阈值通常降低 coverage 和 risk，但只有
confidence 排序可靠时成立。应画 risk-coverage curve，并按 dangerous/normal、
seen/unseen family 分 slice。

### 11.4 Calibration 方法

- Temperature scaling：只调 logits temperature，简单、保持 ranking；
- Platt scaling：对 score 做 logistic calibration；
- Isotonic regression：非参数、数据需求高；
- Beta calibration：适合概率形态；
- Conformal prediction：在 exchangeability 等假设下提供 coverage guarantee。

Calibration model/version 也必须进入 artifact identity；部署 distribution shift 后需要
重新验证，而不是在线偷偷重调 final-eval 阈值。

## 12. Verifier 工程 pipeline

### 12.1 数据来源

- 环境/单元测试确定的 outcome；
- Runtime receipt 与 post-state；
- policy denial、unknown outcome、recovery；
- reviewed success/failure pairs；
- model-generated hard negatives，经独立 verifier/human 审核；
- adversarial reward-hacking trajectories。

Label 必须标明 source 和 confidence。规则生成 operational signal 不能说成人工语义
ground truth。

### 12.2 Pair/group split

同一 task 的多个 candidate、同一 trajectory 的扰动、同一 source episode 必须在同一
split。否则 verifier 记住 instruction 或 visual scene 就能得到虚高成绩。

### 12.3 伪代码

~~~python
def gate_candidate(task, observation, candidate, runtime, verifier):
    validate_closed_action_schema(candidate)
    runtime.policy.require_allowed(task.scope, candidate)
    runtime.approval.require_if_needed(candidate)

    features = build_verifier_input(
        pre_state=observation,
        candidate=candidate,
        provenance=task.provenance,
    )
    score = verifier.predict(features)
    calibrated = calibrator.transform(score)

    if calibrated < THRESHOLD_REJECT:
        return runtime.reject("verifier_low_confidence")
    if calibrated < THRESHOLD_ACCEPT:
        return runtime.fallback_or_human_review("verifier_abstain")

    grounded = runtime.reobserve_and_ground(candidate)
    return runtime.execute_with_wal(grounded)
~~~

注意 deterministic policy 在 verifier 之前。即使 verifier 高分，越权 action 仍拒绝。
执行后还要做 post-state verification；pre-action verifier 不能证明实际 side effect 成功。

### 12.4 Gate 指标

| Gate | 示例 |
|---|---|
| Dataset | source/group leakage 为零，label provenance 完整 |
| Classification | AUROC/AUPRC、per-class precision/recall/F1 |
| Calibration | Brier/ECE、reliability diagram、high-confidence error |
| Selective | target coverage 下 risk 不超过阈值 |
| Safety | dangerous false accepts 为零 |
| Robustness | injection、OOD、tool failure slice 达标 |
| Agent | task success 不退化，side effects/recovery 通过 |
| Performance | verifier latency/cost 在 action budget 内 |

类别高度不平衡时 AUPRC 比 AUROC 更敏感；仍需报告实际 false accept counts。

## 13. 工程选型

### 13.1 Screenshot-only 还是 UIA/OCR fusion

- Screenshot-only：跨应用统一，但小字/结构/稳定引用弱；
- UIA-first：可解释、低成本，但 custom canvas 和陈旧 tree 失败；
- Fusion：覆盖最好，但需要 revision alignment、conflict handling 和更多 token。

Desktop Agent 通常以 fusion 为主，并保留 fallback/reobserve。

### 13.2 Generative grounding 还是 candidate classification

- Generative coordinate：开放空间、能处理未知 UI，但精度和格式较难；
- Candidate classification：在元素集合中选择，更稳定易评测，但依赖候选召回；
- Two-stage：先候选召回，再 VLM/reranker 选择，是常见工程折中。

### 13.3 Bi-encoder 还是 Cross-Encoder

- corpus 大、低 latency：bi-encoder/ANN first stage；
- top K 小、相关性细：cross-encoder rerank；
- 极小 corpus：可直接 cross-encode，但要测 concurrency；
- identifier/search-heavy：加 BM25 hybrid；
- 部署时同时优化 Recall@K、NDCG、latency、memory 和 task success。

### 13.4 Rule verifier 还是 learned verifier

- 能直接写 invariant/test：优先 rule/executable oracle；
- 语义质量或模糊视觉状态：learned verifier；
- 高风险：rule/policy hard gate + calibrated learned model + HITL；
- 没有可靠 label：先改善 observation/label，不要训练一个看似精确的 judge。

## 14. Failure modes 与排障

### 14.1 Multimodal

| 现象 | 常见原因 | 最先检查 |
|---|---|---|
| 坐标整体偏移 | DPI/frame/window offset 错 | coordinate manifest、transform test |
| 同名按钮选错 | OCR 无 role/hierarchy | UIA fusion、window scope |
| 训练 grounding 高、真实低 | template/app leakage | app/task-family split |
| 小字识别差 | resize/patch 太粗 | OCR、tiling、dynamic resolution |
| UIA target 执行失败 | tree stale/遮挡 | reobserve、screenshot conflict |
| 视觉 token 爆炸 | 原图直接高分辨率 prefix | crop/resampler/token budget |
| Hard negative 伤模型 | false negatives 或过难 | human audit、multi-positive |
| Agent 自报成功 | label 来自 response text | post-state oracle |

### 14.2 Retrieval

| 现象 | 常见原因 | 最先检查 |
|---|---|---|
| Recall@K 低 | embedding/domain 或 ANN 参数 | exact-search upper bound |
| Exact 高、ANN 低 | HNSW efSearch/IVF nprobe 太低 | recall-latency sweep |
| Recall 高、NDCG 低 | first stage 可召回但排序差 | reranker/hard negatives |
| Offline 好、线上差 | corpus/query drift、ACL/freshness | slice 与 source revision |
| ID/代码名搜不到 | dense 对 exact token 弱 | BM25/hybrid |
| Reranker 无提升 | candidate 太差或 label noise | oracle candidate recall |
| 泄露私有文档 | ACL 在 prompt 层处理 | index/query auth filter |

### 14.3 Verifier

| 现象 | 常见原因 | 最先检查 |
|---|---|---|
| Accuracy 高但 gate 不安全 | 类别不平衡、高置信危险错误 | dangerous slice、AUPRC |
| 阈值换模型后失效 | score 未校准/分布漂移 | calibration set、reliability |
| Process reward 被刷 | 学到表面格式 | adversarial trajectories |
| Outcome reward 稀疏 | 长 horizon credit assignment | process auxiliary signal |
| Verifier 与 policy 冲突 | authority 设计错误 | deterministic policy precedence |
| 同任务 train/test | candidate pair 被拆开 | group split |
| Judge 偏向长答案 | stylistic bias | counterfactual length control |
| 高分但 post-state 失败 | pre-action score 当执行事实 | post-state verifier |

## 15. 概念比较速查

| 概念 A | 概念 B | 核心差异 |
|---|---|---|
| Vision encoder | Projector | 提取视觉特征 vs 对齐/压缩到 LLM space |
| OCR | UIA | 像素文字识别 vs accessibility 结构 |
| Grounding | Planning | 定位目标 vs 决定多步策略 |
| PointAcc | IoU | 点是否可点 vs box 重合程度 |
| Multimodal SFT | Contrastive learning | 生成 action tokens vs 学相似度空间 |
| Bi-encoder | Cross-encoder | 独立可预计算 vs 联合精确交互 |
| Exact search | ANN | 精确上界 vs 速度/内存折中 |
| Recall@K | MRR | 召回多少相关项 vs 第一个相关项多靠前 |
| MRR | NDCG | 第一相关项 vs 多级相关整条排序 |
| Verifier | Reward Model | 判断/gate 输出 vs 提供优化 scalar |
| Outcome reward | Process reward | 最终结果 vs 中间步骤 |
| Accuracy | Calibration | 对错比例 vs 置信度可信度 |
| Threshold | Coverage-risk | 一个 operating point vs 全部拒答折中曲线 |
| Learned gate | Runtime policy | 概率判断 vs 确定性 authority |

## 16. 高频面试问题与分层回答

### Q1：VLM 如何处理一张 screenshot？

**30 秒回答**

Screenshot 先被 vision encoder 切成 patch tokens 并编码，projector 把视觉 hidden size
映射到 LLM space，随后以 prefix tokens 或 cross-attention 与文本融合。GUI 高分辨率、
小字多，关键 trade-off 是 patch 分辨率、视觉 token budget 和 OCR/UIA 辅助。

**2 分钟回答**

若 H×W 图像用 P×P patches，token 数近似为 ceil(H/P)×ceil(W/P)，分辨率翻倍会让
token 按面积增长。Projector 可是 MLP 或 resampler，既做维度对齐也做 token 压缩。
GUI 中我会保留 screenshot 像素事实，同时序列化 OCR 和 UIA 的 role/name/state/bbox，
绑定同一 observation revision。模型输出 element reference + normalized geometry，
Runtime 执行前 re-ground。

**深挖追问**

要测 screenshot-only、UIA-only、fusion ablation；按 DPI、theme、language、custom
canvas 和 stale UI 分 slice。最终不能只看 grounding IoU，还看 post-state task success
与 wrong-target safety。

### Q2：GUI action 为什么不能只输出 x、y？

**30 秒回答**

裸坐标没有 coordinate frame、DPI、window offset 或 observation revision，UI 变化后会
点击错误目标。我会输出 element ID、normalized point/box、frame 和 precondition，执行前
由 Runtime re-observe/ground。

**2 分钟回答**

坐标应明确属于 screen/window/crop/content frame，并绑定 width、height、DPI 和 screenshot
digest。优先 element reference，geometry 作 backup。审批也绑定这份 action snapshot；
若弹窗、焦点或 revision 改变则重新审批/ground。评测同时看 PointAcc、element accuracy、
wrong-target action 和 post-state。

**深挖追问**

Remote desktop、multi-monitor 和 OS scaling 会进一步改变映射。需要端到端 coordinate
transform property tests，而不是在失败后手调 offset。

### Q3：Bi-encoder 和 Cross-Encoder 怎么选？

**30 秒回答**

Bi-encoder 独立编码 query/document，可预计算并走 ANN，适合大规模召回；Cross-Encoder
联合编码 pair，相关性更精确但每个 candidate 都要 forward。常见是 bi-encoder top K，
再 cross-encoder rerank top N。

**2 分钟回答**

先用 exact search 测 embedding upper bound，再调 HNSW/IVF 的 recall-latency。对于 ID、
代码名和专有词，加 BM25 hybrid。First stage 用 Recall@K 保证正确文档进候选；reranker
看 NDCG/MRR；最终还要看 RAG/Agent task success、ACL 和 latency。若 recall 低，换
reranker无效。

**深挖追问**

Hard negatives 应来自当前 retriever 误召回，但要审查 false negative；同 query 多个
relevant documents 用 multi-positive loss。Index revision、embedding normalization 和
distance metric 必须一致。

### Q4：Recall@K、MRR、NDCG 的区别？

**30 秒回答**

Recall@K 看 top K 覆盖了多少相关项；MRR 只强调第一个相关项的 reciprocal rank；NDCG
支持 graded relevance，并按位置折损评价整条排序。第一阶段召回优先 Recall，单答案场景
可看 MRR，reranker 多级排序常看 NDCG。

**2 分钟回答**

选择 metric 要对应下游：如果 RAG 只需要任一证据，Hit/Recall@K；需要多份互补证据，
query-level Recall@K；用户只点第一项，MRR；多个文档有 0/1/2/3 相关等级，NDCG。
同时报告 query slices 和 support，避免高频 query 主导。

**深挖追问**

Incomplete judgments 会把未标注相关文档算错。可用 pooling + human review，或报告
judged@K。NDCG 的 gain function 和 cutoff 必须冻结。

### Q5：Verifier accuracy 95%，可以直接放行吗？

**30 秒回答**

不可以。要看 dangerous false accepts、calibration、OOD slice 和 threshold 下的
coverage-risk；deterministic policy/permission 仍是硬门禁。Verifier 高分也不能证明
实际 side effect 成功，执行后还需 post-state verification。

**2 分钟回答**

先按 source/task group split，避免同一 trajectory 泄漏。报告 AUPRC、per-class recall、
Brier/ECE、high-confidence errors 和 risk-coverage curve，在独立 calibration set 上定
accept/abstain 阈值。危险 false accept 设为零容忍；中间分数 fallback/HITL。Policy
deny 永远优先于 learned score。

**深挖追问**

部署模型或数据分布变化会破坏 calibration，需要 drift detection 和重新 gate。Temperature
scaling 保 ranking 但不能修错排序；conformal guarantee 也依赖 exchangeability 等假设。

### Q6：Outcome reward 与 process reward 如何组合？

**30 秒回答**

Outcome reward 直接看最终状态，可靠但稀疏；process reward 给中间步骤 dense signal，
但容易把 reviewer 偏好或表面格式当正确。我会用环境 outcome 做 hard target/process
score 辅助 search，并通过 adversarial eval 防 reward hacking。

**2 分钟回答**

桌面任务的 outcome 可由窗口/文件/transaction post-state 验证，不能用模型自报。Process
reward 对 grounding、tool choice、policy compliance 分步打分，改善 credit assignment。
训练时做 weight ablation，评测仍以 end-to-end outcome、安全和 side effects 为准。
Verifier threshold 经 calibration，且不覆盖 Runtime authority。

**深挖追问**

若只有 outcome，可用 rejection sampling、trajectory segmentation、value learning 或
credit assignment；若 process label 成本高，可主动采样 disagreement/hard cases。必须
防 evaluator model 与 policy model 共用偏差。

## 17. 本项目证据映射

### [本仓库已实现]

- 当前是 text Tool Router 闭环，不是 multimodal GUI action model；
- Tool Router 已有 closed schema、20 reviewed seed、20 frozen eval、176/48 v2
  train/validation 和 deterministic scorer/compiler；
- Runtime Lane A offline consumer 已冻结，明确拒绝 screenshot、原始 task、model text、
  tool-result body、Memory 和 Continuation；
- Lane A reliability dataset v1 已确定性映射 failure、unknown outcome、policy denial、
  recovery、budget、tool sequence/outcome 等可观察 signals；
- Lane A mapper 可为后续 Verifier 数据设计提供 operational features，但当前没有
  learned verifier baseline、calibration 或 Agent gate；
- Runtime 是 screenshot/UIA/OCR、grounding、policy、approval、WAL、recovery 与 Desktop
  execution boundary 的 owner；本仓库只能消费已批准 contract；
- FC-MVP-001 当前 active objective 是 preferred FP32 attached package 的独立机器
  portable qualification，尚无正式 cross-machine 结果。

### [本仓库待实施]

- FC-BRIDGE-003 Lane B consent/capture/security contract，当前 pending review；
- FC-MVP-002 screenshot/UIA/OCR GUI Action Model；
- vision encoder/projector 的 multimodal SFT、grounding eval 与 hard negatives；
- Embedding/contrastive learning、ANN index、Cross-Encoder Reranker；
- learned Verifier/Reward Model、pairwise data、calibration、threshold 和 Agent gate；
- Multimodal post-training、DPO/GRPO、online serving 与 production rollout。

因此面试中可以说：

> 我已经实现文本 Tool Router 与 Lane A reliability evidence contract，并为 GUI、
> retrieval 和 verifier 设计了明确的数据、安全和评测边界；多模态模型、retriever 和
> learned verifier 仍是下一阶段，尚未把计划写成经验。

不能说：

> 已训练 GUI VLM、上线 RAG/Reranker、完成 Reward Model 或用 Verifier 控制真实桌面。

## 18. 自测与实践

### 自测题

1. 图像分辨率翻倍为什么可能让视觉 token 约增加四倍？
2. Projector 除了 hidden-size 对齐，还影响哪些工程量？
3. Screenshot、OCR、UIA 分别有什么不可替代信息？
4. 为什么 element ID 和 observation revision 要一起保存？
5. PointAcc、IoU、action accuracy 与 task success 的失败含义有何不同？
6. Hard negative 如何避免变成 false negative？
7. InfoNCE 中 temperature 和 in-batch negatives 各有什么风险？
8. Bi-encoder Recall@K 很低时，为什么加 Cross-Encoder 无法补救？
9. HNSW/IVF/PQ 的主要 latency、memory、recall trade-off 是什么？
10. MRR 与 NDCG 分别忽略了什么？
11. Verifier accuracy 高为什么仍可能 calibration 很差？
12. Process reward 为什么更容易 reward hacking？
13. Learned verifier 为什么不能覆盖 Runtime policy deny？
14. Lane A 缺少哪些字段，因此不能做 multimodal SFT？

### 实践任务

1. 给一张 2560×1440 screenshot 设计三种 patch/resampler token budget，计算数量与
   attention 代价的相对变化；
2. 实现 screen/window/crop 三层 coordinate transform 的 property tests；
3. 构造 screenshot、OCR、UIA 相互冲突的 20-case grounding eval；
4. 写一个 synthetic GUI episode schema，并加入 consent、redaction、retention 和
   deletion lineage；
5. 用一个小语料实现 BM25、bi-encoder exact search、HNSW 和 cross-encoder reranking，
   报告 Recall@K、MRR、NDCG、P95 latency 和 index size；
6. 构造 random、BM25、mined hard negatives，抽样审查 false-negative rate；
7. 训练一个 binary verifier，画 reliability diagram 和 risk-coverage curve；
8. 构造一个高 reward 但实际 post-state 失败的 trajectory，解释 reward hacking；
9. 写一个 Agent gate：deterministic policy 优先，verifier 只决定 accept/abstain，
   execution 后由 post-state oracle 再验证；
10. 用两分钟口述“当前项目为什么不是多模态项目完成态”，列出已实现事实和三个 open
    blockers。

掌握本章的标准不是能列出 VLM、RAG 和 Reward Model 名词，而是能把 perception、
retrieval、verification 与 deterministic execution 放在正确边界中，为每个 metric
说明它测量什么、漏掉什么，并且不把 roadmap 能力讲成项目经验。
