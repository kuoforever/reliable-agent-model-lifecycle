# Multimodal LLM × Agent Infra：待做任务清单

English companion: [docs/en/task-checklist.md](docs/en/task-checklist.md)

> 用途：作为后续 Codex / Claude Code 的统一执行源。  
> 当前状态：`guarded-desktop-agent` 可靠执行基线已存在且完整测试为 `1420 passed, 7 skipped`；模型训练、多模态后训练和 Serving 主线尚待实施。  
> 主目标：以现有 Runtime 为交互环境和安全执行底座，形成可写简历、可演示、可复现的多模态数据 + 后训练 + Eval + Serving + Reliable Agent 闭环。  
> 权威路线：[多模态 LLM 全周期 MVP 演进路线](多模态LLM全周期_MVP演进路线.md)和[多模态与业务场景覆盖矩阵](多模态与业务场景覆盖矩阵.md)。若本清单旧任务顺序与路线冲突，以两份路线文档和本文件第 2、14 节为准。
> Runtime 跨仓库依赖、数据通道和 Pin 规则见：[Desktop Runtime 依赖与集成](Desktop_Runtime_依赖与集成.md)。

## 0. 已确认环境

- 设备：Alienware m18 R1
- GPU：RTX 4090 Laptop GPU，16GB VRAM
- CPU / 内存：i9 / 64GB
- 存储：约 1.5TB；WSL 根目录当前约 1TB 可用
- Windows：NVIDIA 驱动工作正常
- WSL：WSL2 + Ubuntu 24.04，GPU 透传正常
- Ubuntu 当前缺少：PyTorch、pip、nvcc
- Windows 侧已装过 PyTorch，但后续训练和 vLLM 主环境使用 Ubuntu/WSL2

### 禁止事项

- 不在 WSL 内安装 Linux NVIDIA 驱动。
- 暂不执行 `sudo apt install nvidia-cuda-toolkit`。
- 不把训练仓库放到 `/mnt/c`。
- 不把 training、vLLM、runtime 全部塞进同一个 Python 环境。
- 不在没有基线和评测集前开始大规模训练。
- 不把“教师 API 生成数据”描述为 logits 蒸馏。
- 不在本机做 14B+ 训练或完整多机多卡方案。
- 不把 GUI 项目描述为自动驾驶或机器人量产经验。
- 不让模型绕过 Runtime、Policy、Approval 或唯一 MCP 执行边界。
- 不把模型自报成功作为任务完成证据。
- 不把启动 vLLM 或跑通一次压测描述为推理引擎优化。
- 不发布未在同一冻结评测集上重跑的量化或调优模型。
- 不用单请求延迟代表服务容量。

---

# 1. 最终仓库结构

```text
agent-model-factory/
├── README.md
├── pyproject.toml
├── Makefile
├── configs/
├── labs/
│   ├── tiny-transformer/
│   ├── multimodal-post-training/
│   ├── distributed-training-inference/
│   └── multi-agent-distributed-systems/
├── data-engine/
├── post-training/
│   ├── tool-router/
│   ├── gui-action-model/
│   └── agentic-rl/
├── retrieval/
├── verifier/
├── serving/
├── agent-runtime/
├── environments/
│   ├── desktop-gui/
│   ├── document/
│   ├── browser/
│   └── optional-simulation/
├── evals/
├── infra/
├── scripts/
└── docs/
    ├── architecture.md
    ├── roadmap.md
    ├── adr/
    ├── experiments/
    ├── model-cards/
    ├── dataset-cards/
    └── failure-tests.md
```

## 统一工程规范

- Python 3.11 或 3.12，具体由依赖兼容性决定。
- 依赖必须锁定，禁止仅提供一串临时 `pip install` 命令。
- 配置使用 YAML/TOML，禁止关键超参数散落在代码中。
- 所有实验必须记录：Git commit、数据版本、模型版本、配置、随机种子、硬件和结果。
- 所有模块必须有最小单元测试；关键链路必须有集成测试。
- 每个项目至少保留一份 ADR、一份实验报告和一段可复制运行命令。
- 评测集必须固定版本，不能在看过测试结果后直接修改答案。

---

# 2. 里程碑

| 里程碑 | 目标 | 预计完成条件 |
|---|---|---|
| M0 | 冻结 Runtime 与训练环境基线 | Runtime 测试固定；PyTorch CUDA 通过；环境锁定 |
| M1 | 文本 Tool Router 最短闭环 | Trace→Dataset→QLoRA→Eval→Runtime→Badcase |
| M2 | 图文 GUI Action Model | Screenshot/UIA/OCR 联合输入；Grounding、动作、风险和回退可评测 |
| M3 | 多模态后训练与 Verifier | SFT/蒸馏/DPO 或 GRPO/Verifier 使用同一冻结测试集对照 |
| M4 | 多模型推理平台 | vLLM、量化、缓存、路由、灰度、回滚与性能报告 |
| M5 | Agentic RL 环境 | Runtime 状态产生可验证奖励；有 reward-hacking 测试 |
| M6 | 多环境扩展 | 文档或浏览器成为第二环境，不复制训练和执行系统 |
| M7 | 四个深度 Lab | Tiny Transformer、多模态后训练、训练/推理性能、Multi-Agent 均有独立报告 |
| M8 | 简历与演示 | 五种岗位叙事、架构图、3 分钟视频和真实数字 |

---

# 3. Phase 0：环境与基线

## ENV-001：检查并配置 WSL 资源

**产出**

- `.wslconfig` 建议值与修改说明
- `free -h`、磁盘和 GPU 快照
- WSL 网络/代理诊断结果

**验收**

- WSL 可稳定看到 GPU
- 可用内存符合配置
- PyPI、PyTorch、Hugging Face 下载可用

## ENV-002：建立独立 Python 环境

建议：

```text
.venv-dev       Tiny Transformer / 数据处理
.venv-training  Transformers / PEFT / TRL / bitsandbytes
.venv-serving   vLLM / Gateway
.venv-runtime   FastAPI / Temporal / OTel
```

**验收**

- 每个环境均有锁文件
- 环境之间不共享 site-packages
- `make env-check` 输出完整版本矩阵

## ENV-003：安装并验证 PyTorch CUDA

**测试内容**

- `torch.cuda.is_available()`
- GPU 名称和 VRAM
- BF16 支持
- FP16/BF16 矩阵乘法
- 峰值显存
- 10 分钟稳定性测试

**验收**

- CUDA 矩阵测试通过
- 无驱动冲突
- 保存 `docs/environment.md`

## ENV-004：建立实验追踪骨架

**第一版**

- MLflow 本地模式或 W&B offline
- 统一 `run_id`
- Git commit、config、metrics、artifacts 自动记录

**验收**

- 一个 smoke experiment 能被完整重现

---

# 4. Project A：Tiny Transformer & Training Systems Lab

## TT-001：最小 Decoder-only Transformer

实现：

- Token embedding
- Pre-norm Decoder block
- Multi-head causal attention，并保留 MQA / GQA 对照入口
- Causal mask
- RoPE
- RMSNorm
- SwiGLU MLP
- Residual
- LM head 与可选 tied embedding
- Cross entropy

**验收**

- 关键张量 shape 测试
- causal mask 不泄漏未来 token
- 小 batch 可前向、反向并更新参数
- 参数量、FLOPs、activation 和 KV Cache 显存估算可由脚本复核

## TT-002：生成策略

实现：

- greedy
- temperature
- top-k
- top-p
- repetition penalty
- stop token

**验收**

- 固定 seed 可复现
- 保存不同策略输出和延迟对照

## TT-003：KV Cache

**验收**

- 缓存与无缓存输出一致
- 记录逐 token 延迟和显存变化
- 文档说明 prefill / decode 区别

## TT-004：训练工程

实现：

- BF16 / FP16
- gradient accumulation
- gradient clipping
- warmup + scheduler
- gradient checkpointing
- train/validation split

**验收**

- 显存与 tokens/s 对照表
- OOM 后可通过配置调整恢复

## TT-005：Checkpoint 与中断恢复

保存：

- model
- optimizer
- scheduler
- scaler
- global step
- RNG states
- data sampler state（可行时）

**故障注入**

- 训练中途强制结束进程
- 从 checkpoint 恢复

**验收**

- step 连续
- 学习率连续
- loss 无异常跳变
- 固定条件下结果可复现

## TT-006：大模型架构拆解与算子图

目标不是罗列名词，而是把 Decoder-only LLM 的数学、张量 shape、算子和
训练/推理执行路径对应起来。

必须覆盖：

- Dense Decoder 主线，以及 Encoder-only、Encoder-Decoder、MoE 的边界对照
- MHA / MQA / GQA、RoPE、RMSNorm、SwiGLU、Residual 和 tied embedding
- Prefill、Decode、Backward 三条执行路径
- Attention 算子链：Q/K/V GEMM → RoPE → QKᵀ → scale/mask → softmax → PV → O projection
- MLP 算子链：gate/up GEMM → SiLU → elementwise multiply → down GEMM
- Embedding/gather、KV Cache 读写、top-k/top-p sampling、cross entropy
- 量化/反量化，以及 MoE top-k router、dispatch、gather/scatter 的最小示意
- 多卡训练中的 all-reduce、reduce-scatter、all-gather 与参数/梯度/优化器状态归属

**验收**

- 每个核心算子记录输入/输出 shape、dtype、复杂度、显存读写和数值稳定性风险
- 用小张量将显式算子分解与 PyTorch 参考实现逐项对齐
- 保存一份可复现的 operator graph/trace，能区分 compute-bound 与 memory-bound 候选
- 明确哪些内容已实现、哪些只是架构对照，不把示意图当成训练证据

## TT-007：热点算子 Profiling 与 Kernel 最小实验

候选：

- Attention：PyTorch eager / SDPA / FlashAttention（硬件与依赖允许时）
- 融合 RMSNorm、RoPE 或 SwiGLU 中至少一个热点算子
- PyTorch eager / `torch.compile` / Triton kernel 对照
- 不同 batch、sequence length、head dimension、dtype 的 shape sweep

**验收**

- 先用误差阈值、梯度对齐和边界 shape 证明正确，再报告速度
- 固定 warmup、同步、重复次数、硬件、软件版本和输入分布
- 报告 p50/p95 latency、tokens/s、峰值显存，并尽可能记录带宽或 TFLOPS
- PyTorch Profiler 或 Nsight trace 能支持瓶颈判断
- 至少保留一个负结果或反例，禁止只展示最快配置

---

# 5. Project B：Data Engine & Continued Pretraining

## DATA-001：数据清单和许可证字段

每条来源记录：

- source_id
- URL / repository / file
- license
- retrieved_at
- checksum
- deletion_policy
- usage_scope

## DATA-002：解析与标准化

支持：

- Markdown
- HTML
- PDF 文本
- JSONL
- Git 仓库文档
- Agent Trace

**验收**

- 统一 schema
- 解析失败可追踪
- 原始数据与处理数据分离

## DATA-003：清洗、去重、质量和 PII

实现：

- exact dedup
- near dedup（MinHash 或等价方法）
- 长度、字符、语言和模板过滤
- PII 检测/脱敏
- 质量评分

**验收**

- `quality_report.md`
- 去重比例和过滤原因分布

## DATA-004：切分与污染检查

实现：

- train / validation / test
- 文档级隔离
- 与 eval 集的 exact / near duplicate 检查

**验收**

- `contamination_report.md`
- 测试集可冻结和版本化

## DATA-005：Packing 与 Token 统计

**产出**

- 长度分布
- token 总量
- packing 利用率
- 截断比例

## CPT-001：0.5B-0.6B 领域继续预训练

对照：

- Base
- CPT
- SFT
- CPT + SFT

**指标**

- validation loss / perplexity
- 领域任务指标
- 通用能力保留
- 显存和 tokens/s

**验收**

- 不仅展示 loss
- 有灾难性遗忘分析

---

# 6. Project C：Multimodal Tool-Use Post-Training & Distillation

## MM-001：多模态轨迹 Schema

输入至少包含：

- instruction
- screenshot / cropped region
- UIA / document text / OCR
- previous actions and results
- available tools
- policy context

输出至少包含：

- next_tool
- arguments / bbox / ref
- risk_level
- requires_approval
- confidence
- should_reject / should_fallback
- evidence

**验收**

- 文本样本与图文样本使用可兼容的版本化 Schema
- 每条轨迹绑定 runtime/model/policy/environment 版本
- 动作前观察与动作后观察可以关联
- 模型输出不包含任何直接执行权限

**当前进展（2026-08-20）**

- `MM-001-multimodal-trajectory-schema-v1` 已完成本地 synthetic schema review。
  text-only（10 artifacts、0 previous step）与 image-grounded（17 artifacts、1
  previous step）fixture 共享严格 v1 topology，并绑定 Runtime/model/policy/
  environment、pre/post observation、candidate、Runtime decision、tool result 与
  state verifier；Runtime 是唯一 dispatch authority。
- 21,091-byte schema SHA-256 为 `2109dcd2...c32964c`；7,387-byte text fixture
  为 `9162a2e3...07706`；11,145-byte image fixture 为
  `89c45460...5963`。三个 CPython 版本统一门禁均为 468 tests、`valid=true`、
  40 source files；focused 26 tests、Ruff、strict mypy、`py_compile`、JSON Schema
  和 metadata hash 检查通过。
- 该完成项只关闭 synthetic schema review；capture adapter、真实 episode、
  dataset split/license、GUI grounding 质量、训练/执行、Runtime integration、
  cross-machine 与 portable claims 均未建立，`training_eligible=false`、
  `execution_eligible=false`、`runtime_eligible=false`。
- 该 review 完成时下一动作切换为
  `MM-002-gui-grounding-data-eval-v1`；该 gate 现已完成。
- `FC-MVP-001-fp32-attached-portable-package-qualification-v1` 保持冻结并 defer；
  其恢复点仍是 `f8dc9a62471759282ad2b41673d95acd43bf240f` 上的独立原生 Windows
  目标机 runbook，本机/WSL negative control 不构成 cross-machine 或 portable
  证据。

## MM-002：GUI Grounding 数据与评测

构造：

- ref grounding
- bbox grounding
- UIA-only / screenshot-only / fused observation
- OCR 缺失或噪声
- 控件移动、遮挡、过期 ref

指标：

- Grounding Accuracy / IoU
- Action Accuracy
- Tool / Argument Accuracy
- stale-ref rejection
- coordinate/ref disagreement

**当前进展（2026-08-17）**

- `MM-002-gui-grounding-data-eval-v1` 已完成本地 synthetic data/eval review：9 个
  case/family 覆盖 ref/bbox/fused grounding、UIA/screenshot/fused observation、
  clean/missing/noisy OCR 及 moved/occluded/stale/disagreement；gold 与 model input
  结构分离，split 固定为 eval 且禁止训练使用。
- synthetic probe 指标为 Grounding `4/5`、mean IoU `19/20`、Action `6/9`、
  Tool `5/5`、Argument `4/5`、stale-ref rejection `1/2`、disagreement rejection
  `0/1`、prediction disagreement `2/3`。这些只验证 scorer，不是模型结果；
  `model_evaluated=false`。
- 三个 CPython 版本统一门禁均为 494 tests、`valid=true`、42 source files；
  focused 26 tests、Ruff、strict mypy、`py_compile`、两份 JSON Schema、report
  recomputation 与 hashes 通过。训练/执行/Runtime eligibility 继续为 false。
- 当前唯一动作切换为 `MM-003-multimodal-gui-action-model-v1`。

## MM-003：图文 GUI Action Model

实验：

- 0.5B–3B 小型 VLM
- 全屏 vs 局部裁剪
- UIA-only vs screenshot-only vs fusion
- 不同动作历史长度
- 不同置信度 fallback 阈值

**验收**

- QLoRA Adapter 可独立加载
- 固定 GUI 任务集可重复运行
- 有任务成功率、步骤数、回退率、显存和延迟报告
- 所有动作仍经过既有 Runtime/Runner/MCP 边界

**当前进展（2026-08-17）**

- outcome-neutral baseline protocol 已在正式 eval 前冻结：固定
  `Qwen/Qwen2.5-VL-3B-Instruct` revision
  `66285546d2b821cf421d4f5eb2576359d3770cd3`、14 个模型文件、
  Transformers BF16/SDPA 环境、原 MM-002 九例顺序、3×UIA-only / 3×screenshot-only /
  3×fusion、6 张确定性 synthetic PNG、prompt/compiler、零 retry 与资源上限。
- 与 eval 无关的 blank-image compatibility smoke 返回 `READY`；它只证明本机 backend
  可加载/生成，不是 MM-002 model result。v1 正式 attempt 在合并冻结 protocol 后执行
  一次：control flow 证明 fresh load 与 9 个 generation calls 完成，随后 scorer 因
  `prediction_coordinate_ref_disagreement_rate` 零分母抛出
  `EMPTY_METRIC_DENOMINATOR`。runner 尚未写 artifact，raw/compiled output、metrics、
  latency 与资源数字不可恢复；没有 retry。
- 4,480-byte failure classification SHA-256 为
  `fc8ef58286f425c03e8f20148c1b2b014c29be4468b61f8c0e650f507ec2dce6`；focused 4
  tests 与 unified 506-test gate 通过，`valid=true`、44 source files。
  `baseline_executed=false`、`model_evaluated=false`、`training=false`、
  `runtime_eligible=false`。模型 `qwen-research` license 仅支持
  non-commercial research/evaluation，本 gate 不授予 serving、promotion、commercial
  或 Runtime eligibility。
- `MM-003-local-small-vlm-baseline-recovery-protocol-v2` 已在任何 v2 model run 前
  冻结：13,349 bytes，SHA-256
  `369c813dee44b14c6022eb90739bcd37f9f8de472e60a8cee88682454d135403`。
  v2 保留 v1 model/revision、suite、screenshots、prompt、compiler、generation 与 caps；
  仅为 optional prediction diagnostic 增加 `not_applicable` 零分母语义，并在 scoring
  前 exclusive 持久化 raw/compiled candidates，scoring 异常则写 failure receipt。
- recovery focused 8 tests 与 CPython 3.12.12 unified 514-test gate 通过，
  `valid=true`、46 source files；这些是 protocol-freeze 时的验证数字。
- 合并 PR #35 后，`MM-003-local-small-vlm-baseline-execution-v2` 在本机只执行一次：
  one fresh load / nine ordered calls / zero retry / offline execution，12/12 formal
  gates 全 true；elapsed `41.921435199998086s`，peak allocated/reserved
  `11,616,626,688` / `12,010,389,504` bytes，均在 caps 内。
- 严格 compiler 为 9/9 fallback；Grounding `0/5`、Action `0/9`、Tool `0/5`、
  Argument `0/5`，三个 observation mode 均 0/3。optional disagreement metric 为
  `not_applicable`。这是 formal measurement pass 与 negative quality baseline，
  不是模型质量、promotion 或 Runtime pass。
- run/predictions/evidence 为 14,715 / 2,058 / 4,680 bytes，SHA-256 分别为
  `173bb4ab17fa5d6c02323f9cc26e8cddd93525055a712b8f6c5cd5c09cb2a57c`、
  `57629229e4416cb7562382b57ee6774845dbd4f1da97b73a1e54d2a2f8ea17f7`、
  `a0e3c2503e5bac13bf979c7721dab4350681a84883d749b94ef3ca204d2166fe`；
  focused result 4 tests 与 CPython 3.12.12/3.13.7 unified 518-test gates 通过，
  `valid=true`、46 source files。
- `MM-003-small-vlm-post-training-protocol-v1` 已在任何 registered training 前本地
  冻结：17,601 bytes，SHA-256
  `9dfd180f24a86814fc32c5ebbfca07a31f713c8387f85ec3212dc538647cb061`。协议固定
  18 train / 9 validation records、18 张 synthetic PNG、NF4/BF16 QLoRA、seed/
  hyperparameters/caps、Adapter 文件集、fresh independent Adapter load 与不变 MM-002
  九例 eval。case/family/instruction/input/target/screenshot 的 exact overlap 均为空，
  eval gold 未进入训练。
- 同正式设置的 eval-independent gradient-checkpointed smoke 识别 414 个
  `Linear4bit` modules、7,372,800 trainable parameters、finite loss 与 nonzero finite
  LoRA gradient，peak allocated/reserved 为 3,941,332,480 / 4,273,995,776 bytes；
  它没有保存 Adapter，不是 training、loadability、quality 或 repeatability 证据。
- 正式执行前的只读审计发现初版 runner 未把 prereg/source/wheel/input/model/dependency/
  environment preflight 异常纳入 failure receipt。hardened freeze 在固定 run directory
  exclusive create 后覆盖全部这些 stage；measured train/eval timer 从该边界持续到
  post-score resource sampling，evidence persistence 仍 fail-closed 但不进入 elapsed；
  在该 freeze/merge 时仍未运行 training、model eval 或 retry。
- focused 13 tests 与 CPython 3.11.15/3.12.12/3.13.7 unified 531-test gates 通过，`valid=true`、47
  source files、4 个 Windows privilege skips。这些是 v1 protocol freeze 的验证数字。
- 合并 PR #38 后，`MM-003-small-vlm-post-training-execution-v1` 在本机仅调用一次。
  exact preflight 通过后，runner 在 `training` stage 的首条冻结记录
  `pt-train-018/fused` 上抛出 `MM003ProtocolError`；zero retry，输出目录仅有
  897-byte `failure.json`，SHA-256
  `8c82455b406c66a038deaaadeb9251b9eb626145a5f31d36b04d5ad7d10c72d9`。
  Adapter/training-run/predictions/evidence 均不存在，12 项结果/部署 claims 全 false。
- `MM-003-small-vlm-post-training-failure-classification-v1` 已绑定 freeze
  `a882e6096a87e475511890be9fc804a468143868`、17,601-byte preregistration、十个
  source receipts 与 raw failure receipt。model-free 静态复现显示全部 27 个 `pt-*`
  record 都因 training renderer 错用仅接受 `ground-*` 的 baseline registry 而触发
  `CASE_MODE_MISMATCH at $.case`；不是 fixture mode、CUDA、checkpoint、optimizer 或
  scoring failure。15,877-byte classification SHA-256 为
  `66b9e8352caacd1a10e750a222ce2a0a7994df385e23e31dbc76a68b6109aef6`；它直接读取
  两个 tracked fixture receipt，并锁定 v1 完整等价子树、v2 允许差异 whitelist 及
  protocol/execution/experiment/output/success-next 精确身份。
- failure focused 6 tests 与 CPython 3.11.15/3.12.12/3.13.7 unified 537-test gates
  通过，`valid=true`、48 source files、4 个 Windows privilege skips。当前唯一动作切换为
  `MM-003-small-vlm-post-training-recovery-protocol-v2`：保持 v1 不变，冻结独立
  `pt-*` prompt projection、27-case preflight/prompt receipts、新 gate/experiment/
  output dir；合并前不得执行 v2，且 v2 不是 v1 retry。
- `MM-003-small-vlm-post-training-recovery-protocol-v2` 已在任何 v2 model/GPU run
  前本地冻结：26,553 bytes，SHA-256
  `02e36d5981e0ed4ac90bfdb3c5cc9c9e1f78ff29ff927020b0a41ebb27f55c0e`。
  recursive type-strict leaf comparator 保留 v1 完整 lineage 与十个 source receipts，
  只允许 12 个 exact replacements、两个具名 v2 sources、四个 closed new sections；
  candidate 不能用自报 source hash、new section 或伪 v1 base 自证。
- post-training-only registry 覆盖 18 train + 9 validation；27 个 prompt 在 dependency
  import、CUDA/model load 前逐条绑定 bytes/SHA，aggregate 为
  `sha256:bcbf8e87674ce2a668bdfe54ff4ecaba2e6db36899fc4e7c563867d1e2e9e102`。
  family/repeat/target/raw screenshot regions 不进入文本 prompt，registered PNG 仍作为
  独立 processor image；baseline `ground-*` registry 未修改。
- recovery focused 23 tests 在 CPython 3.11.15/3.12.12/3.13.7 各自通过；三版本
  unified 560-test gates 全部 `valid=true`，4 个 expected Windows privilege skips、49
  source files。Ruff、`py_compile`、typed v2 contract scoped strict mypy、preregistration
  recomputation/`prepare --check` 与 `git diff --check` 通过；没有加载模型/GPU，v2
  output dir 仍不存在。
- recovery protocol 通过 PR #40 合并后，
  `MM-003-small-vlm-post-training-execution-v2` 在本机仅运行一次：one fresh train
  model load / three epochs / 18 optimizer steps / zero retry / offline；保存三文件
  Adapter 后 one fresh base + one independent Adapter load 完成 9 个 ordered MM-002
  calls。13/13 formal gates 全 true；完整 lifecycle elapsed
  `130.3286408999993s`，peak allocated/reserved `6,486,660,096` /
  `7,153,385,472` bytes，均在 caps 内。
- Adapter weights 为 29,529,752 bytes、SHA-256
  `d93d2ea2d9f05564093cbb0b1286d2c368c54b01e847f1c37a98e00fb2914701`，含
  288 个 finite F32 tensors / 7,372,800 parameters；prediction producer exact 绑定
  此 Adapter identity 与 frozen model revision。execution evidence 记录 independent
  load 成功，但 result review 不重新加载模型。
- strict compiler 由 zero-shot 的 9/9 fallback 降至 0/9；Grounding `0/5→3/5`、
  Action `0/9→3/9`、Tool/Argument `0/5→5/5`。stale-ref rejection 仍 `0/2`，
  coordinate/ref disagreement rejection 仍 `0/1`。六个 Action failure 已完整归类为
  fused 缺 bbox（`ground-003/006`）、reject 降为 fallback（`ground-004/007/009`）
  与 fallback reason vocabulary mismatch（`ground-005`）；eval answers 不得复制到训练。
- 11,311-byte result review SHA-256 为
  `3dff57b17eb4fc9966ab53fe92faea8921fb34b485e389aaa19af64610db957d`。
  `quality_improved=false` 与 `repeatability_established=false` 仍保留；single synthetic
  run 不建立 generalized quality、safety、serving、promotion 或 Runtime eligibility。
- result-review focused 11 tests 与 unified 571-test gate 在本机 CPython 3.11.15 /
  3.13.7 均通过；`valid=true`、4 个 expected Windows privilege skips、49 audited
  source files。全仓 Ruff、Python 3.11 `py_compile`、`git diff --check` 通过；
  CPython 3.12 由 pull-request Linux matrix 独立验证，不伪装成本地已通过。
- `MM-003-small-vlm-post-training-eval-repeatability-protocol-v1` 已在任何 repeat
  model/GPU execution 前本地冻结：22,951 bytes，SHA-256
  `723db665f98e53ef2fe968ee7c6fe663b42d79b86176eef5cf70f11ccc4a312b`。
  它绑定 17 个 source receipts、unchanged v2 Adapter/model/MM-002
  suite/screenshots/prompt/compiler/generation/environment、one fresh base+Adapter
  load、9 ordered calls、offline/zero retry、原 1,800-second/16.5-GB caps、13 个
  outcome-neutral formal gates，以及首次 v2 raw/compiled/metrics 的分层比较。
- owner-marked staging directory 在原子 claim fixed output 前写入
  `attempt-owner.json`；正式目录一旦出现便可绑定本次 one-shot ownership。focused
  29 tests 与 CPython 3.11.15/3.13.7 unified 600-test gates 通过，`valid=true`、
  4 个 expected Windows privilege skips、50 audited source files；Ruff、
  `py_compile`、`prepare --check`、`git diff --check` 通过。CPython 3.12 由 PR Linux
  matrix 独立验证。没有加载模型/GPU，formal output dir 仍不存在。
- 协议合并后的唯一动作是
  `MM-003-small-vlm-post-training-eval-repeatability-execution-v1`：先恢复并独立复核
  exact locked Python 3.12/CUDA 环境，再对 unchanged Adapter/MM-002 eval 执行一次。
  equality 或 drift 都是可接受 measurement outcome；不得 retrain、修改 Adapter、复用
  consumed output dir 或称为 execution-v2 retry。成功只进入独立 result-review-v1，
  consumed incomplete 则进入已注册 failure-classification-v1。
- 协议经 PR #42 合并后，正式 one-shot replay 已在 freeze commit
  `c72b3bd1666ed6b03d9425e1dbaacfe115dda4f8` 上消费且没有 retry。13/13 formal gates
  全部通过：one fresh base load、one read-only Adapter load、9 ordered offline calls，
  training/optimizer/backward/Adapter write/network/retry 均为零。
- fixed replay 的 raw UTF-8 output、compiled prediction 均为 9/9 exact；metrics、
  generated-token counts 与 compiler-fallback status 也分别 exact。`all_layers_exact`
  只表示 raw/compiled/metrics 三层，不是 Transformer internal layers；token-ID sequence
  未持久化，不能声称 token path 或 logits exact。
- 四个冻结执行 artifact 分别为 586 / 9,855 / 2,241 / 20,243 bytes，SHA-256 为
  `8f6c267ab262021ac6b8805606b9a7e7bb071507968e5d94a0c4b25eadb3d7fb`、
  `a354f4b3f2b20467ed7d82916345f7b951ca6df1ad9ecc5816734410694e155b`、
  `c2c703e5896fe64df9e156bda9d38975b92c1bf18c72f74f5a232dcbbbc4a028`、
  `e20262debfbefa3e361855728aa8852f1219053d6fb9152158a2916c806a7ad2`。
  model-free review 逐字节重建 evidence；15,119-byte result review SHA-256 为
  `8979693b6962849555e533332331d91dbb9fad8294f7fbc6703fa09ab3414f4a`。
- result review 仅新增 bounded
  `same_machine_eval_repeatability_established=true`。这里的 same-machine 是同一本地
  controller 与注册环境字段，不是 MachineGuid/GPU UUID 或 hardware attestation。
  原 Anaconda binary 未恢复，transitive dependency hashes 未完整锁定，恢复记录属于
  `reviewer_observed_untracked_context`；training/resource/cross-machine/generalized
  quality/serving/promotion/Runtime claims 全部保持 false。已消费 output dir 不得删除、
  复用或重跑。单一下一 gate 切换为
  `MM-004-multimodal-hard-negative-data-protocol-v1`。
- result-review focused 11 tests 在本机 CPython 3.11.15、3.12.12、3.13.7 均通过；
  三版本 unified gate 均为 611 tests、`valid=true`、4 个 expected Windows privilege
  skips、50 audited source files。全仓 Ruff、scoped strict mypy、`py_compile`、
  `prepare --check`、默认 result validator 与 `git diff --check` 通过。

## MM-004：多模态困难负样本

- bbox/ref 指向错误控件
- 图像与结构化观察冲突
- 忽略动作后状态
- 重复动作或重复副作用
- 绕过审批
- 工具失败但声称成功
- 看似合理但证据不足

已冻结 `MM-004-multimodal-hard-negative-data-protocol-v1`：七类必须以
`clean` / `hard_negative` 原子 pair 表达，使用 domain-separated SHA-256
内容身份，隔离 train/validation family 与内容，并排除既有 MM-002/MM-003
case、family、instruction、observation、candidate 和 image identity。协议冻结时
未生成数据，training/model evaluation/quality/safety/serving/promotion/Runtime
claims 全部为 false。其 downstream generation gate 已完成。

Generation preregistration 已冻结：`seed=44004`，七类各 4 个 family（3 train +
1 validation），共 28 clean/negative pairs、56 records、28 张 unique synthetic
PNG 和 31 个输出收据。冻结时 fixture/evidence 不存在；PR #45 merge commit
`2d41b99e7e984975056f7e1088e768cd8a62b744` 随后授权 formal materialization。
其 exact aligned `master` invocation 已原子生成并独立验证 31 files / 127,336
bytes、42 train + 14 validation records 与 28 images。9,425-byte evidence
SHA-256 为
`0c79a89f8f2431640e4c91d9957af978775e54f2360c15eb67b97a89bb60b133`。
generation/dataset validation 为 true；training/verifier or model evaluation/
quality/safety/serving/promotion/capture/Runtime claims 仍为 false。

49,311-byte v1 protocol（SHA-256
`3011420f26bc61f572de2e21f96d28215529e495075db4e958573a4e4317484f`）经 PR #47
merge 为 `425a4f21c82786d054ce620e83f6703e4f235d2f`。formal command 在 output claim、
model import/GPU/model call 前被 freeze-commit receipt gate 拒绝：Git 中 Adapter
weight 是 exact 133-byte LFS pointer，而 v1 错把 pointer bytes 与 29,529,752-byte
hydrated payload receipt 逐字比较。pointer OID/size 与 hydrated SHA-256/size 完全
一致，因此是 pre-consumption representation validation bug，不是 Adapter drift
或 model result；v1 output 不存在，attempt 未消费。

50,642-byte v2 repair 已在任何 model call 前独立冻结，SHA-256 为
`bee2093d54d95cc52303c57c598d99a071aff85bef9f56605adeb2b604f8c0d9`。candidate、
56 records / 28 images、label-isolated prompt、strict compiler、total metrics、
56-call order、zero retry、resources 与 terminal lifecycle 不变；新增 v2 gate/output
identity，并分别校验 freeze commit 的 exact LFS pointer 与运行期 read-only hydrated
payload full receipt。v1/v2 outputs 均不存在，所有 execution/training/quality/safety/
serving/promotion/Runtime claims 仍为 false。单一下一动作是 v2 经 PR 合并后，从
`master == origin/master == v2 freeze commit` 执行一次；消费后不得 retry。
focused v2 13/13 tests、全仓 Ruff、scoped strict Mypy、`py_compile`、preregistration
`--check`、feature-branch formal-command negative check 与 `git diff --check` 均通过；
本地 CPython 3.11.15、3.12.12、3.13.7 unified gates 均通过 648 tests、4 个预期
Windows privilege skips、53 个 audited source files，`valid=true`，且未创建任一
fixed output。

v2 经 PR #48 merge 为 `365935c02e16badec9ba40a3c4d078b66726f96e` 后，其 exact
one-shot formal command 已消费一次 owner-marked attempt：one fresh base、one
independent read-only Adapter、56/56 ordered offline calls、zero retry/network/
training/Adapter write。6,644-byte evidence SHA-256 为
`87c45c9a174b9c6d0419f1d0ba9c619597848b13fe4447a19988e7a6ff56292c`；overall
32/56，hard-negative rejection 28/28，clean accept 4/28，pair exact 4/28，
compiler valid 52/56，20 个 clean false rejects、4 个 clean invalid、0 个 negative
false accepts。formal gate 只表示 measurement complete within caps，不表示 quality
pass。

model-free result review 已逐字节重建 evidence；18,220-byte canonical review
SHA-256 为
`711c1b52619d856015b832cd54a3bbfcaa419f360b95bf448d62de8230bdb720`。它仅确认
consumed execution 与 fixed-suite reject bias；quality improvement/generalized
quality/safety/training/serving/promotion/cross-machine or resource repeatability/
Runtime claims 均保持 false。已消费 output 不得删除、复用或 retry。单一下一 gate
为 `MM-005-multimodal-environment-adaptation-protocol-v1`。
result-review focused 12/12 tests、全仓 Ruff、scoped strict Mypy、`py_compile`、
v2 preregistration `--check`、默认 result validator 与 `git diff --check` 均通过；
本地 CPython 3.11.15、3.12.12、3.13.7 unified gates 均通过 660 tests、4 个预期
Windows privilege skips、53 个 audited source files 与 `valid=true`，没有 reload
模型或产生第二次 attempt。

## MM-005：多模态环境适配

扩展顺序：

1. Desktop GUI
2. Document / Chart / PDF
3. Browser Research
4. Audio / Video
5. Robotics / Autonomous Driving Simulation（可选）

每个环境只新增 Adapter、任务集、Verifier 和数据，不复制训练、Serving、审批或恢复系统。

`MM-005-multimodal-environment-adaptation-protocol-v1` 已冻结第二环境
`Document / Chart / PDF` 的 model-free 首个垂直切片：English、synthetic、single-page，
覆盖 document text、table cell、bar-chart value 与 page-region evidence grounding。
仅允许新增 Environment Adapter、task set、deterministic Verifier 和 synthetic
dataset；训练/评测编排、Serving/routing、policy、approval、WAL、grounding、budgets、
recovery 与 desktop dispatch 全部继承且不得复制。63 个 read-only source receipts
覆盖 11 个边界/上游文件与 52 张历史图像；排除 registry 从 MM-002～MM-004 实际内容
重新计算 shared cross-stage hashes，冻结 92 case/record、64 family、64 instruction、
64 observation、92 target 和 52 image identities。协议为 49,202 canonical bytes，
SHA-256 为
`311822603bb6c05c1b7f388cd782c30556fa8b7aa0d67cbd1ccd89f9d13a532a`。
此 gate 未生成数据、未调用模型、未训练、未采集、未修改 Runtime，所有 quality/
safety/Serving/promotion/Runtime claims 为 false。单一下一 gate 为
`MM-005-document-chart-pdf-data-protocol-v1`，必须先冻结 seed、counts、templates、
render constraints、output receipts 与 validation，再允许生成任何数据或图像。

`MM-005-document-chart-pdf-data-protocol-v1` 已按该边界冻结 `seed=55005`：四类
task 各 8 个 template family（6 train + 2 validation），共 32 records、32 张
unique 1280×900 PNG 与 14 份 deterministic single-page PDF source artifacts。
PDF 与 PNG 从同一 synthetic layout ground truth 派生，不使用 external renderer、
OCR、host font、network 或 model dependency。两份 dataset、manifest、PNG 和 PDF
合计 49 个 planned outputs / 434,212 bytes，每份 path/bytes/SHA-256 均在内存重建
并冻结；output root 与 execution evidence 在 preregistration freeze 时不存在。
parent record/exclusion、
四 task/source coverage、每 task 6/2 split、family/template/content/image isolation、
answer/evidence semantics 及 PNG/PDF 结构均验证通过；在该 freeze，generation/dataset
validation/Adapter/Verifier/model/quality/safety/capture/Serving/Runtime claims 均为
false。24,909-byte protocol SHA-256 为
`7e774e69194e6f70c27c9b53bbab68adb19874780757717ca42012ec48297525`。
该 preregistration 注册的 downstream gate 是
`MM-005-document-chart-pdf-data-generation-v1`：只能从合并后的 exact master freeze
commit 原子落盘这 49 个 outputs，并须独立写 execution evidence；该 gate 现已完成。

数据协议已通过 PR #51 合并为
`3992778151bb7209c00c89e77e07894e075ff066`，远近 feature branch 已清理且
`master == origin/master` 后才开始独立 generation slice。
`MM-005-document-chart-pdf-data-generation-v1` 现冻结 17,780-byte protocol，
SHA-256 为
`6e212237ee59d9730f97028769033a0991f9e3c6b893a404fc583274f813f2ed`；它绑定
四份 data/generation contract/runner source receipts、24,909-byte data protocol
和全部 49 outputs / 434,212 bytes。正式 runner 必须满足 merged-master exact
commit、双目标不存在、zero internal retry、staging-root atomic rename、exact-tree
extra-file rejection、persisted-byte independent readback 和 exclusive evidence。
该 runner freeze 已经 PR #52 合并为
`fbf1c64398d89c35e95f80322fd665ae3c2f2c1d`，远近 feature branch 清理且
`master == origin/master` 后，正式 invocation 从该 commit 精确执行一次、无 retry。
它生成并独立回读验证 49 files / 434,212 bytes：24 train + 8 validation records、
32 PNG、14 single-page PDF，以及 65,327 / 22,490 / 14,789-byte 三份 JSON。
16,680-byte execution evidence SHA-256 为
`a11a373a6c7d49b02470a84d9c303cb4f424ff6693dcc516ef8060af032d649f`，16 个
required gates 全为 true。仅 generation/records/images/dataset validation 为 true；
Adapter/Verifier/model/quality/safety/real or external content/capture/Serving/
promotion/Runtime claims 仍为 false。结果态 generation focused 14/14 tests 与本机
CPython 3.11.15、3.12.12、3.13.7 unified 702-test gates 全部通过，均有 4 个预期
Windows privilege skips、56 个 audited source files 和 `valid=true`。
这些 exact consumed outputs/evidence 已通过 PR #53 合并为
`3ae49d372b5184418e8353630336fdb802182cbd`；6 个 Linux matrix checks 全部通过，
review/conflict state clear，远近 feature branch 已清理，`master == origin/master`。
为了让 CI 能校验 evidence 绑定的历史 freeze commit，统一门禁 checkout 改为完整历史；
本地 exact bytes 未重跑、未改写。

`MM-005-document-chart-pdf-adapter-verifier-protocol-v1` 现已在实现前本地冻结：
126,032 canonical bytes，SHA-256 为
`4715134d7bd1f8ae54275764f342bf5a8974cc491298dbefd52971aab876c64a`。它绑定 8 个
source receipts、exact generation evidence/upstreams、全部已消费 outputs、32 个
Adapter projection receipts 与 160 个 deterministic Verifier reference cases
（32 positive / 128 negative）。model payload 仅含 `instruction`、`observation`、
`source_kind`、`task_family_id`；gold、identity、split、provenance、Verifier metadata
和 real image path 均不进入 model payload。strict JSON compiler 拒绝 extra/duplicate
keys、nonfinite、duplicate refs、wrong page 与 oversized output；Verifier 不使用 model
judge。相关 MM-005 focused 38/38 tests、Ruff、scoped strict Mypy、`py_compile`、builder
`--check` 与 `git diff --check` 通过；本机 CPython 3.11.15、3.12.12、3.13.7 unified
712-test gates 全部通过，均有 4 个预期 Windows privilege skips、57 个 audited source
files 和 `valid=true`。这仅建立 protocol/fixture reconstruction，不建立 Adapter/
Verifier execution、model/training repeatability、quality、safety、Serving、promotion
或 Runtime eligibility。该协议已通过 PR #54 合并为
`db8c6833f43c02a0b255c436558e0269a8bde3b4`；6 个 Linux matrix checks 全部通过，
0 review/comment/thread、CLEAN/MERGEABLE，远近 feature branch 已清理且
`master == origin/master` 后才开始实现。

`MM-005-document-chart-pdf-adapter-verifier-implementation-v1` 现已独立实现并对
全部冻结向量执行 conformance。`AdaptedInput` 只向 model-facing transport 提供
canonical model payload JSON 与 exact image bytes，path/receipt/authority 仅在 audit
projection；missing/duplicate/tampered/non-byte/absolute/traversal image binding 全部
fail closed。compiler/Verifier 未调用 reference 实现，独立处理 exact keys、duplicate
keys/refs、nonfinite、UTF-8/size、strict scalar type（包括 bool 不能代替 int）、NFC +
ASCII-space trim、ordered evidence 和 page exact。32/32 projection receipts、160/160
case outcomes 全部一致：96 compiler-valid、64 invalid、32 positive、128 negative，
zero mismatch。

102,117-byte implementation evidence SHA-256 为
`d4cbe61cac4cff60c15e769c35e481ca93f71524b23bf0dad4ddf75095d17bf2`，绑定 5 个
implementation/protocol source receipts、protocol merge commit、read-only consumed
inputs、32 Adapter executions 与 160 Verifier executions。`environment_adapter_implemented/
executed` 和 `verifier_implemented/executed` 现为 true；model training/evaluation、
repeatability、quality、safety、Serving、promotion、Runtime change/eligibility 仍为
false。implementation focused 12/12 tests（完整 MM-005 chain 50 tests）、Ruff、scoped
strict Mypy、`py_compile`、builder `--check` 与 `git diff --check` 通过。本机 CPython
3.11.15、3.12.12、3.13.7 unified 724-test gates 全部通过，均有 4 个预期 Windows
privilege skips、59 个 audited source files 和 `valid=true`。该 exact
implementation/evidence 已通过 PR #55 合并为
`ff52da51aba534b051f9e247518fb2d20d1db1e2`；6 个 Linux matrix checks 全部通过，
0 review/comment/thread，远近 feature branch 已清理且 `master == origin/master` 后才
开始 model-evaluation protocol slice。

`MM-005-document-chart-pdf-model-evaluation-protocol-v1` 现已在任何 model import/call
前本地冻结为 58,414 canonical bytes，SHA-256 为
`cdb8d1ea09221763d87cd79ba752d9af8264ce49b7cf600eed338a073a04561b`。它绑定 exact
Qwen2.5-VL base revision + read-only `mm003-qlora-sft-v2` Adapter、MM-004 candidate
result lineage、已合并 Adapter/Verifier evidence、全部 49 个已消费 dataset outputs、
12 个 protocol source receipts，以及 32 个固定顺序 prompt projections。model payload
只含 `instruction`、`observation`、`source_kind`、`task_family_id`，共 31,430 bytes；
32 份 exact image payload 共 314,128 bytes，gold、Verifier metadata、identity 和真实
path 均隔离。

协议注册一次 fresh base load、一次 independent Adapter load、32 个 ordered generate
calls、zero retry/network/training/write，1,800 seconds 与 16.5 GB allocated/reserved
resource caps；strict compiler、deterministic Verifier 和 compiler/answer/evidence/page/
joint + per-split/family/source total metrics 均固定，accuracy threshold 不改变
measurement completion。attempt 只在 fixed output directory 被 owner-marked atomic
claim 后消费；成功必须持久化 candidate/predictions/evidence，失败只能持久化不含
message/trace/path/secret 的安全 receipt，消费后不得 retry。

在 protocol freeze 时 output directory 不存在，`attempt_consumed=false`、
`evaluation_executed=false`、`model_evaluated=false`。该 exact protocol 后续已通过
PR #56 合并为 `3be0083c3197111d57a4a5e5f70feced9f2c96f9`；6 个 Linux matrix checks
全部通过，0 review/comment/thread，远近 feature branch 清理且
`master == origin/master` 后才正式执行。

`MM-005-document-chart-pdf-model-evaluation-execution-v1` 随后从该 exact merged
commit 仅执行一次：one fresh base load、one independent read-only Adapter load、
32/32 ordered calls、zero retry/network/training/write。正式 measurement gate 通过，
elapsed `216.03030519999447` seconds，peak CUDA allocated/reserved
`6,458,204,160` / `6,777,995,264` bytes。结果为 compiler validity 28/32，answer/joint
exact 19/32，evidence/page exact 28/32；chart 与 table 均 8/8，document text 0/8，
page-region 3/8。13 个 bad cases 精确分为 9 个 compiler-valid answer-only wrong 与
4 个 compiler-invalid。

独立 model-free review 已逐字节重建 candidate、predictions、Verifier/scorer evidence
和 15,235-byte result review；review SHA-256 为
`7cc4990f900787123f078d2387855e4708b5eadb8d6705bb6364d8cab2f935a7`。protocol/result
focused 15/15 + 12/12、完整 MM-005 chain 91/91、Ruff、scoped strict Mypy、
`py_compile`、default validator 与 `git diff --check` 通过。本机 CPython 3.11.15、
3.12.12、3.13.7 unified 751-test gates 全部通过，均有 4 个预期 Windows privilege
skips、60 个 audited source files 和 `valid=true`，且没有 model reload 或 second
attempt。

该 exact consumed result artifacts 与 review 已通过 PR #57 合并为
`056eb8d050eb0f0491ff21a07bd5b7716abf7eb8`；6 个 Linux matrix checks 全部通过，
0 review/comment/thread，远近 feature branch 已清理后才开始 repeatability protocol。

`MM-005-document-chart-pdf-model-evaluation-repeatability-protocol-v1` 现已在任何
second model import/call 前本地冻结为 47,974 canonical bytes，SHA-256 为
`4c5186cbfa542125d4f2b96dae14e31955effa330c42951f993413d276962ed7`。它认证 baseline
protocol/result commits 与 6 个 exact baseline receipts，冻结 unchanged candidate/
environment/32-case order/prompt/image/compiler/Verifier/metrics/generation/resource caps
及 12-source execution closure；one fresh base、one independent read-only Adapter、32
ordered offline calls、zero retry/network/training/write。

raw UTF-8、compiled JSON、Verifier verdict、metrics 与 generated-token counts 分层比较；
equality 不是 measurement gate，resource equality 只作 diagnostics 而 caps 仍是 integrity
gate。16/16 focused model-free tests 与完整 MM-005 chain 107/107、Ruff、scoped strict
Mypy、`py_compile`、builder `--check`、unified protocol subcheck 与 `git diff --check`
已通过。本机 CPython 3.11.15、3.12.12、3.13.7 unified 767-test gates 全部通过，
均有 4 个预期 Windows privilege skips、61 个 audited source files 和 `valid=true`。
在 protocol freeze 时 fixed replay output absent、`replay_attempt_consumed=false`，
same-machine fixed-suite/training/resource/cross-machine/quality/safety/Serving/promotion/
Runtime claims 全部 false；只有 clean merge、branch cleanup 且
`master == origin/master == freeze commit` 后才允许消费一次 replay。

该 protocol 已通过 PR #58 合并为
`874f6c1a201a07d6680a3fa12217c1344b14c141`，6 个 Linux matrix checks 全部通过、
0 review/comment/thread、CLEAN/MERGEABLE，远近 feature branch 清理且
`master == origin/master` 后，正式 replay 仅消费一次：one fresh base、one independent
read-only Adapter、32/32 ordered calls、zero retry/network/training/write。10/10 formal
gates 通过，raw UTF-8、compiled JSON、Verifier verdict、metrics 与 generated-token counts
全部 exact；四个逐 case 层均为 32/32、zero mismatch，total metrics 逐字段一致。

replay elapsed 为 `201.59785200000624` seconds，peak CUDA allocated/reserved 为
`6,458,204,160` / `6,777,995,264` bytes。相对 baseline，GPU peaks exact，但 elapsed
少 `14.432453199988231` seconds，所以 resource vector 不 exact、resource repeatability
保持 false。20,952-byte evidence SHA-256 为
`659ea12140a85c044be1cdd0bf1ab867cbbdff2a097fbd447e07ec3b84e81617`。

独立 model-free review 已逐字节重建 evidence，并生成 18,817-byte review，SHA-256 为
`c5b5f12dfaffb387ca7e394c8acbd2b92fc00e3a256ed8cab0d4e624b28d0ec8`。review 只建立
bounded same-machine、registered-environment-field、fixed-32-case evaluation
repeatability；training/resource repeatability、cross-machine reproducibility、quality
improvement/generalization、safety、real-content、Serving、promotion、Runtime claims 均为
false。正式 runner 在 generation 前强制 live environment exact，但 live mapping 未单独
持久化；token IDs 与 per-case latency 也不是注册 repeatability layer。这些限制已在 review
明示。

新 result-review focused 13/13、完整 MM-005 chain 120/120 通过；Ruff、scoped strict
Mypy、`py_compile`、default validator、unified result subcheck 与 `git diff --check` 通过。
本机 CPython 3.11.15、3.12.12、3.13.7 unified 780-test gates 全部通过，均有 4 个预期
Windows privilege skips、61 个 audited source files 和 `valid=true`。PR #59 已把 exact
replay artifacts、独立 review 与 strict validator 合并为
`5f60cbf44a311b46b312090d62d2783424c1dc85`：6/6 checks 通过，0
review/comment/thread，CLEAN/MERGEABLE，远近 feature branch 已清理且
`master == origin/master`。Document/Chart/PDF repeatability lifecycle 至此关闭；当时的唯一
successor gate 为 model-free `MM-005-browser-research-environment-adaptation-protocol-v1`，必须在
任何 data generation/model call/training/Serving/Runtime change 前冻结第三环境边界。它只
允许界定未来 Browser Research 的 Adapter、任务集、Verifier 与数据，不复制 orchestration、
Serving、审批、恢复或安全系统。两个已消费 MM-005 attempt 均不得
delete/reopen/reuse/overwrite/retry。

`MM-005-browser-research-environment-adaptation-protocol-v1` 已在任何 data
generation、live browser/network、model call、training、Serving、capture 或 Runtime
change 前本地冻结为 76,364 canonical bytes，SHA-256 为
`62ef6c554c90d3523b7d9c2a0a102c2a8c783f3d3ba3496cd8c36dfebe04b06e`。它绑定
Document/Chart/PDF 关闭证据与 102 个 exact source receipts，重算并排除 124 prior
records、96 families、96 instruction/observation identities、124 target identities 和
84 images。

首个 Browser Research slice 仅允许 English、deterministic repository-generated
synthetic static bundles；每个 record 含 1～3 个 source snapshots，并对齐 DOM、exact
screenshot SHA-256 和由 visible DOM text 顺序重建的 page text。四个 task families 为
single-source fact citation、multi-source synthesis、cross-source comparison 与 freshness
conflict resolution；strict output 只有 `answer + citation_refs`，multi-source 必须引用至少
两个来源，freshness 必须引用 latest published source。URL 仅允许 HTTPS `.invalid`，live
retrieval/navigation、JavaScript、login/session、transaction、real/external web、prompt-
injection safety 与 open-web source ranking 均 deferred。

17/17 focused tests、Ruff、strict Mypy、`py_compile`、builder `--check` 与 unified Browser
Research subcheck 已通过；本地 CPython 3.11.15、3.12.12、3.13.7 complete unified gates
均通过 797 tests、4 个预期 Windows privilege skips、62 个 audited source files，且
`valid=true`。Adapter/Verifier implementation、data、browsing、network、model、quality、
safety、Serving、promotion、Runtime claims 全部 false。PR #61 已将 exact protocol 合并为
`d7e7b7f70ff298a47244c34cc22173c70c65e6c9`；6 个 Linux matrix checks 全部通过，
reviews/issue comments/review comments/review threads 均为 0，PR 为 `CLEAN`/`MERGEABLE`，
远端和本地 feature branch 均已删除，且 `master == origin/master`。

随后唯一 gate 切换为 model-free `MM-005-browser-research-data-protocol-v1`：必须先冻结 seed、
counts、train/validation splits、template families、static source snapshots、DOM/page-text/
screenshot deterministic alignment、planned output receipts、prior-content exclusion 与验证规则，
不得在该 protocol clean merge、branch cleanup 且 `master == origin/master` 前生成任何 Browser
Research record 或 image。

该 data protocol 已在任何 Browser Research record/image 落盘前冻结并发布：`seed=55006`，
四 task 各 8 个 template family（6 train + 2 validation），共 32 records 与显式 1～3 source
bundles；68 个 sources 按 51/17 分布到 train/validation。每个 source 的 canonical static JSON
descriptor、DOM、visible-order page text 与 unique 1280×900 PNG 从同一 synthetic ground truth
重建；不使用 executable HTML、browser engine、JavaScript、network、host font、OCR、model、
capture 或 Runtime。68 snapshots、68 PNG、两份 dataset 和 manifest 合计 139 个 planned
outputs / 986,989 bytes，全部 path/bytes/SHA-256 已在内存冻结；在该 data-protocol freeze
时，固定 output root 与 execution evidence 尚不存在。73,476-byte protocol SHA-256 为
`38e31afc46cf92603d191563bc5460062adeb702e7df3ee4ff18f485b034283a`。

14/14 focused adversarial tests、Ruff、scoped strict Mypy、`py_compile`、builder `--check` 与
`git diff --check` 通过；本机 CPython 3.11.15、3.12.12、3.13.7 complete unified gates 均
通过 811 tests、4 个预期 Windows privilege skips、63 个 audited source files，且
`valid=true`。generation/dataset validation、Adapter/Verifier execution、live browser/network、
model/quality/safety、Serving/promotion/Runtime claims 在该 freeze 全部 false。PR #63 已将
exact protocol 合并为 `9518d5b59fb11dbea237caa17fd245f4dcd5c2db`；6/6 Linux matrix
checks 通过，0 review/comment/thread、`CLEAN`/`MERGEABLE`，远近 feature branch 已清理。
PR #64 又以 `5ef3d495af1d10d203a1dbcbba5cc713c2b4ee62` 关闭其 publication status，未改
data protocol 或 generator sources。其下游 generation gate 随后冻结并执行如下。

该 `MM-005-browser-research-data-generation-v1` runner protocol 已在任何 formal
materialization 前冻结：64,590 canonical bytes，SHA-256 为
`78c60102d042b65e8046523e9c78cc03137bbf3bf8edbb45a0e067bd3e16aa0d`。它显式绑定
PR #63 data-protocol merge commit `9518d5b59fb11dbea237caa17fd245f4dcd5c2db`、四份
data/generation source receipts、73,476-byte data protocol 与全部 139 outputs / 986,989
bytes。formal runner 强制 published-data ancestry、exact aligned merged `master`、双目标不存在、
zero internal retry、same-parent staging-root atomic rename、path-escape/symlink/reparse/extra-tree
拒绝、persisted-byte independent readback 与 exclusive evidence；Windows physical I/O 使用
extended-length path，但 registered logical receipts 不变。

PR #65 已把该 exact protocol 合并为
`9739e2b86d8473d9b8e99ea32e541db6055e4523`；6/6 Linux Python-matrix checks 通过，
0 review/comment/thread、`CLEAN`/`MERGEABLE`，远近 feature branch 已删除且本地
`master == origin/master ==` 该 freeze commit。随后唯一登记命令执行一次、zero retry，原子
生成并独立回读验证 32 records、68 static source snapshots、68 PNG screenshots 与完整
139-file / 986,989-byte tree。63,294-byte exclusive execution evidence SHA-256 为
`1c5a7898f9811171c963db95b13a4fd33427b7ec58a4058ab5d4f077110f7fea`，20 个 required
gates 全部为 true。

结果态 17/17 focused adversarial tests、full-repository Ruff、scoped strict Mypy、
`py_compile`、protocol `--check` 与 `git diff --check` 通过；本机 CPython 3.11.15、3.12.12、
3.13.7 complete unified gates 均通过 828 tests、4 个预期 Windows privilege skips、64 个
audited source files，且 `valid=true`。仅 generation/records/source snapshots/screenshots/
dataset validation 为 true；Adapter/Verifier、live browser/network、model/quality/safety/prompt-
injection safety/real or external content/capture/Serving/promotion/cross-machine repeatability/
Runtime claims 仍为 false。PR #66 已把该 consumed exact result 合并为
`6e990f0cf8ba4f76bd35a57479c3649c4cadc3aa`；6/6 Linux matrix checks 通过，
0 review/comment/thread、`CLEAN`/`MERGEABLE`，远近 feature branch 已删除且本地
`master == origin/master`。139 outputs 与 evidence 继续 immutable，不得 delete/reopen/reuse/
overwrite/regenerate/retry。

model-free `MM-005-browser-research-adapter-verifier-protocol-v1` 已在任何 formal
Adapter/Verifier implementation 前冻结为 271,406 bytes，SHA-256 为
`a64f5d3d174ab2e8c7a003626d76981f43c15b9e739f8c999c4198df0c77156b`。它绑定
PR #66 result commit、8 份 source receipts、全部 upstream protocol/evidence/dataset bytes、
68 screenshot + 68 source-snapshot bindings、32 个 gold/path-isolated Adapter projections，
以及 224 个 deterministic Verifier controls（32 positive + 192 negative）。七类 case 覆盖
exact expected、wrong answer、existing-but-wrong DOM ref、unknown DOM ref、citation order/
source coverage/latest freshness source 缺失、duplicate ref 与 malformed JSON；8 条 freshness
记录各有一个去除 latest published source 的明确负例。

11/11 focused adversarial tests、Ruff、scoped strict Mypy、`py_compile` 与 builder `--check`
通过；本机 CPython 3.11.15、3.12.12、3.13.7 complete unified gates 均通过 839 tests、
4 个预期 Windows privilege skips、65 个 audited source files，且 `valid=true`。当前只建立
fixed protocol/fixture/projection/oracle byte reconstruction；
Adapter/Verifier implementation/execution、model-evaluation repeatability、cross-machine
reproducibility、live browser/network、model/quality/safety、Serving/promotion/Runtime claims
全部 false。PR #67 已把该 exact protocol 合并为
`403cc240fec14d3d9123b6f207112a5290f4fc34`；Python 3.11/3.12/3.13 Linux PR checks
通过，0 review/comment/thread、`CLEAN`/`MERGEABLE`，远近 feature branch 已删除且本地
`master == origin/master` 后才开始 implementation。

model-free `MM-005-browser-research-adapter-verifier-implementation-v1` 已完成。独立 Adapter、
strict compiler、deterministic Verifier 与 citation/source/freshness semantics 已对全部 frozen
vectors 执行；
195,994-byte canonical evidence SHA-256 为
`77634e6202354641eef84cf1640c17588e902c073f804b535dfb3ada52d09876`。它绑定 5 份
implementation/protocol source receipts、PR #67 exact merge/protocol、immutable upstream，
32 projections、68 screenshot + 68 audit-only source snapshots，以及 224 个独立重算结果：
160 compiler-valid + 64 invalid、32 positive + 192 negative、8 个 latest-source-removal
freshness negatives，registered mismatch 为 0。

13/13 focused adversarial tests、full-repository Ruff、3 个 typed implementation/evidence/
builder 文件的 strict Mypy、`py_compile`、builder `--check` 与 `git diff --check` 已通过；
本机 CPython 3.11.15、3.12.12、3.13.7 complete unified gates 均通过 852 tests、4 个预期
Windows privilege skips、67 个 audited source files，且 `valid=true`。当前仅新增
Adapter/Verifier implemented/executed claims；model training/evaluation、
model-evaluation repeatability、quality/safety、live browser/
network、real/external content、capture、cross-machine reproducibility、Serving/promotion/
Runtime claims 仍为 false。PR #68 已把该 exact implementation/evidence 合并为
`1177d5649952af6c04f713f5cfbbde47388e3769`；6/6 Linux Python-matrix checks 通过，
0 review/comment/thread、`CLEAN`/`MERGEABLE`，signed squash merge tree 与 implementation tree
完全一致，远近 feature branch 已删除且本地 `master == origin/master` 后才开始 protocol freeze。

Outcome-neutral
`MM-005-browser-research-model-evaluation-protocol-v1` 已在任何 model import/call 或 attempt
claim 前冻结为 116,152 canonical bytes，SHA-256 为
`84cd3d20d5a678a8ad0f7c38ad12e057225a4250e8143c5f004c2eaef8981f3f`；绑定 12 份 source
receipts、PR #68 implementation lineage、immutable MM-004 candidate/dataset、32 个固定顺序
records、68 source/screenshot/audit-snapshot bindings、81,796 model-payload bytes、600,604
screenshot bytes 与 118,742 audit-only source-snapshot bytes。

未来 formal execution 仅登记 1 fresh base load、1 independent Adapter load、32 ordered calls、
68 screenshot visual inputs、0 source-snapshot model inputs、zero retry/network/training；strict
compiler 只接受 `answer` + `citation_refs`，Verifier 独立登记 answer/citation exact、DOM-ref
binding、minimum source coverage、8-case latest-source freshness 及完整 grouped metrics。accuracy
不得改变 measurement completion。16/16 focused adversarial tests、Ruff、scoped strict Mypy、
`py_compile` 与 protocol `--check` 已通过；本机 CPython 3.11.15、3.12.12、3.13.7 complete
unified gates 均通过 868 tests、4 个预期 Windows privilege skips、68 个 audited source files，
且 `valid=true`。PR #69 随后把 exact protocol 合并为 signed squash commit
`7af879457bd55c9b3f6b4f7abf33e43ed181c2e9`；6/6 checks 通过，0
review/comment/thread/conflict，merge tree 与 feature tree 相同，远近 branch 已清理且
`master == origin/master` 后才执行。

第一次 formal command 在 output claim 前因 Windows `git show` long path 失败；owner/output/
model import/call 均未发生，因此未消费 attempt。启用 repo-local `core.longpaths=true` 并完成一次
独立 full freeze preflight 后，同一 registered command 原子写入 649-byte owner，v1 随即永久
`attempt_consumed=true`、`retry_allowed=false`。之后 external controller interruption 终止 active
process，Python exception handler 未能写 terminal artifact；稳定目录仅有 `attempt-owner.json`。
exact counters、completed record IDs、model-load/call progress、raw/compiled outputs、metrics、
latency/resources 与 formal failure stage 均不可恢复且不得推断。

Model-free `MM-005-browser-research-model-evaluation-failure-classification-v1` 已将原始 owner
byte-for-byte tracked，并用 `git cat-file blob` 绑定 v1 preregistration 与 12 个 freeze-commit
sources；11,936-byte classification SHA-256 为
`628f9a24267c292d318ca279eb0642c72fbc705b1211629ef8b9edf6318e6e11`，internal report digest 为
`sha256:8768a18c0aecc1da4bc693130b023b4949f5059b0eac6eabae6cbede6cae4d2a`。9/9 focused tests、Ruff、
strict Mypy、`py_compile` 已通过；CPython 3.11.15、3.12.12、3.13.7 unified gates 各通过 877
tests、4 个预期 Windows privilege skips、69 audited source files、`valid=true`。formal
measurement/evaluation result/model evaluation、
quality/safety、model/training/resource/cross-machine repeatability、Serving/promotion/Runtime claims
全部为 false。PR #70 已把该 exact classification clean merge 为 signed squash commit
`28211e62d907c16a6d2208bca20f139ee7e31f5f`；6/6 Linux matrix checks 通过，0
review/comment/thread/conflict，merge tree 与 feature tree 完全一致，远近 feature branch 已删除，
且 local `master == origin/master` 后才开始 v2 freeze。

Model-free
`MM-005-browser-research-model-evaluation-recovery-protocol-v2` 已冻结为 120,315-byte canonical
config，其 SHA-256 为
`512b3523196bf80e7e137c7777c205fa92a57acf371464f3f65671c406706c2e`；它 exact 保留 12 个
v1 semantic subtrees，绑定 18 个 protocol-source receipts，并通过独立
`source_lineage.recovery_lineage` 绑定 immutable v1 preregistration、tracked owner、classification
与 published commit lineage。它只增加新 experiment/output/source closure、long-path-safe
`git cat-file blob` lineage、atomic owner+genesis/lifecycle-marker publish、named lifecycle lease、
append-only SHA-256-chained durable progress 与 model-free exact terminal repair。21/21 focused
adversarial tests、Ruff、Ruff format check、strict Mypy、`py_compile` 与 protocol `--check` 已通过；
本机 CPython 3.11.15、3.12.12、3.13.7 complete unified gates 均通过 898 tests、4 个预期 Windows
privilege skips、71 audited source files，且 `valid=true`。冻结时 v2 output/lifecycle roots
absent、`attempt_consumed=false`、`model_evaluated=false`，且没有 result/quality claim。PR #71
已将 exact protocol clean merge 为 signed squash commit
`91b637c6b365ea8632b31335f5c74ac6c60e6b71`；6/6 Linux matrix checks 通过，0
review/comment/thread/conflict，merge tree 与 feature tree 完全一致，远近 feature branch 已删除，
且 local `master == origin/master` 后才执行。

完整 frozen preflight 通过后，registered v2 command 于 2026-08-29 exact 执行一次。它完成 1 次
fresh base load、1 次 independent Adapter load、前三个 frozen records，并在第四条只持久化到
`generation_started` checkpoint；随后 Python exception handler 写入 authenticated
`stage=generation`、`exception_type=RuntimeError` terminal。consumed directory 恰有 938-byte
owner、22,782-byte / 14-frame progress 与 2,675-byte failure；candidate/predictions/evidence
均 absent。generate attempts/completions 为 `4/3`、screenshot inputs 为 `9`，retry/network/
training/backward/optimizer/Adapter-write/model-save 均为 `0`。terminal 已完整落盘，因此未运行
recovery command，v2 attempt 不得 retry。

三份 raw artifacts 已 byte-for-byte tracked；SHA-256 分别为
`a80cf6a2a9142fdfbc7a92646498a05e5036fc13227af88470297b98990aad87`、
`a19709eb55fedc248eed32c1acbe9dbf0caa61f2cfc1a9ae7f5cf16b2a9a70b1`、
`46f3968482567db2810237c277f65d982ce9518f829c43ad96bd1fc7d2776bc7`。11,920-byte model-free
classification SHA-256 为
`169c78c7337eca32de8769c8598b9f514e2acc33a04ec50a0fdc4bc5a3895197`，internal report digest 为
`sha256:425bcf20cdab6a70d2bf67ed9bdbd19bddc3c9020bdd99800fedac8d6c9bcbe1`。classification 为
`generation_stage_runtime_error_after_three_completed_calls_before_fourth_completion`，category 为
`generation_pipeline_runtime_failure_without_attributable_substage`。protocol 未持久化 exception
message、traceback 或 generation substage；controller console 中与 CUDA illegal-memory-access
一致的文本只保留为 non-authenticated observation，不能归因 CUDA/GPU/driver/OOM/model/Adapter/
data/prompt/processor/compiler/Verifier/runner。formal measurement/result/model evaluation、quality/
safety/repeatability/Serving/promotion/Runtime claims 全部保持 false。
15/15 focused adversarial tests 在本机 CPython 3.11.15、3.12.12、3.13.7 均通过；三个
complete unified gates 各通过 913 tests、4 个预期 Windows privilege skips、72 audited source
files，且 `valid=true`。type-strict validator 额外拒绝 Python 原本相等的 `false`/`0` 与
`true`/`1` substitutions。

PR #72 已将该 exact classification 以 signed squash commit
`e52060ff82b62f6042ec371b72f011e5fa5c0681` 发布；six Linux Python-matrix checks、review/comment/
thread/conflict state、merge-tree equality 与双端 branch cleanup 均已确认，successor 开始前 local
`master == origin/master`。

33,476-byte model-free
`MM-005-browser-research-model-evaluation-generation-failure-investigation-protocol-v1` 已通过 PR #73
发布为 signed squash commit `fe430710924537a18e677b75202f0c19806d3f12`，SHA-256 为
`be8ecd067e884a8d60c9664013943d6887c769ac35a389934509b73338247494`。six Linux Python-matrix
checks、review/comment/thread/conflict/merge state、merge-tree equality、双端 branch cleanup 与 local
master alignment 均已确认。它冻结 PR #72 lineage、exact fourth record、3 个 authenticated
completed-prefix controls、3 个 same-shape static controls、Adapter/model-payload/prompt/image receipts、
opaque-sentinel runtime-message reconstruction、durable checkpoint boundary 与 outcome-neutral rubric。

PR #74 已将对应 model-free implementation/result contract 发布为 signed squash commit
`c2b04f68dfbb0f96423ecf83a8d73529fdf9d055`；six Linux Python-matrix checks、review/comment/thread/
conflict/merge state、双端 branch cleanup 与 local master alignment 均已确认。从该 exact clean merged
master，唯一一次 model-free formal invocation 于 `2026-08-29T09:11:14Z` exclusive 创建 39,843-byte
fixed result；file SHA-256 为
`2be8caf8dbc35d2741d81d408f21fea08d7961cc970590a25922bc757485ca93`，formal invocation=1、
internal retry=0。其 outcome 为 `static_pipeline_reconstructed_without_contract_violation`：static
pipeline 可重建、generation failure 未被复现、Runtime root cause 仍 unresolved；只允许冻结独立
diagnostic protocol 是当时该 result gate 的唯一 routing，不授权 diagnostic execution 或 recovery-v3。

首次 real historical `--check` 在不改变 result 的前提下发现 parent-only Windows portability defects：
Git checkout 静默漏掉 122 个 long-path tracked files，且 exact c2b worker stdout 使用 terminal CRLF。
本 result slice 仅加入 `core.longpaths=true`、short temp topology 与 single-LF/terminal-CRLF closed wire；
patched parent 随后以 exact c2b runner 在 `-I -S -B` 下完成 recomputation，返回 `checked=true`、
`valid=true`，default runner 未再次执行。32/32 focused tests 已在 Python 3.11.15、3.12.12、3.13.7
通过；Ruff 0.15.22、Ruff format、scoped strict Mypy 2.3.0 与 `py_compile` 通过。三个 complete
present-result unified gates 各通过 961 tests、4 个预期 Windows privilege skips、74 audited source
files，且 `result_present=true`、`investigation_executed=true`、`runner_plan_valid=false`、
`runner_check_valid=true`、`valid=true`。

PR #75 已将 immutable fixed result 与 parent-only Windows historical-check portability fix 发布为
verified signed squash commit `c8541147717870992c60c6d2ea1c2f4ff68ee1d2`；six Linux
Python-matrix checks、review/comment/thread/conflict/merge state、双端 branch cleanup 与 local master
alignment 均已确认。fixed result 仍严格为 39,843 bytes / SHA-256
`2be8caf8dbc35d2741d81d408f21fea08d7961cc970590a25922bc757485ca93`，default runner 未再次执行。

PR #76 已将 57,143-byte、SHA-256
`13d1808168819414df2a0ca33d1f59e5e8efd52de6f0b49946d02cf070c992d6` 的
`MM-005-browser-research-model-evaluation-generation-failure-diagnostic-protocol-v1` 发布为 signed
squash commit `9c90c5e68d4386b30db613930ec7dc0147999c04`；six Linux Python-matrix checks、
review/comment/thread/conflict/merge state、双端 branch cleanup 与 local master alignment 均已确认。

PR #77 已将 exact 11-path diagnostic implementation 发布为 signed squash commit
`7da39396c951a9248fe49c1bd69080923b827fa1`；six feature/PR Linux Python-matrix checks、
review/comment/thread/conflict/merge state、merge tree、双端 branch cleanup 与 local master alignment
均已确认。该 gate 未创建 authority/owner/progress/lifecycle/output/staging artifact，未调用
`--execute`，也未使用 model/PIL/torch/CUDA/network/browser/training/Runtime。

PR #78 已将独立的
`MM-005-browser-research-model-evaluation-generation-failure-diagnostic-execution-authority-v1` exact
10-path slice 发布为 signed squash commit `0a271e2c27c65e9595953dadb98200ea5ec51acb`。其
canonical 2,706-byte artifact SHA-256 为
`903e681c2957e185da36ed1f991cc5b339b0e692e8c730da63069690277b9e6b`，exact-bind PR #77、4 个
critical dependency receipts、frozen 17-field Windows/CUDA environment、registered resource caps、
formal invocation=1、retry=0、per-record attempt=1；authority artifact 仅由该 commit first-parent 引入。

clean aligned short-path master、source/input/wheel/17-field environment/read-only GPU capability preflight
全部通过后，registered v1 command 已严格调用一次且未重试。它在 lifecycle/owner/genesis 之前以
controller-observed `RecoveryIOError` / exit code `1` 退出：fresh worktree 缺少安全
`work/evaluation-runs` parent，而 frozen runner 在创建 parent 之前先构造 `DirectoryTreeGuard`。因此没有
output/lifecycle/owner/progress/staging/terminal、model load 或 CUDA workload。

formal invocation budget 已从 1 消耗到 0，retry budget 仍为 0；但
`diagnostic_attempt_consumed=false`、`diagnostic_executed=false`。frozen failure grammar 最小状态是
owner-bound `attempt_claimed` frame，无法表达 zero-owner/zero-frame boundary。不得合成 failure terminal、
failure scope 或 formal outcome；`selected_outcome=null`，controller observation 不属于 formal telemetry。

model-free
`MM-005-browser-research-model-evaluation-generation-failure-diagnostic-invocation-closeout-v1` exact
10-path slice 仅增加 6,507-byte canonical closeout、deterministic builder/validator、7 个 focused tests、
unified integration 与 canonical docs。artifact SHA-256 为
`d8a64be5b0361322246faf4eeccde04f9921e0a9c586f3498b188a6477d1ddce`。本 closeout 不得调用
`--execute`，不得创建或修改任何 v1 runtime/terminal artifact，也不得运行 model/PIL/torch/CUDA/
network/browser/training/Runtime；v1 command 永久禁止再次执行。

7/7 closeout-focused tests、builder `--check`、Ruff 0.15.2、strict Mypy 2.3.0、
three-version `py_compile` 与 `git diff --check` 均通过；本机 CPython 3.11.15、3.12.12、
3.13.7 complete unified gates 各通过 1,039 tests、4 个预期 Windows privilege skips、
77 个 audited source files，且 `valid=true`。

PR #80 的四个 split jobs 已在 run `33480142139` 全绿，并以 verified signed squash
`266e9b695af0f93ae4c82e36ac484cb2d3d3a521` 合并；exact merge HEAD 的 post-merge run
`33481002184` 再次四绿。ruleset `19977219` 已在两次 observation 后更新并回读为 active/strict、
zero bypass、exact 三个 `python-matrix (3.11/3.12/3.13)` 加 `hydrated-lfs-integrity` 四个 required
contexts；双端 branch 与临时 worktree cleanup 完成。`repository-ci-lfs-maintenance-v1` 因而正式关闭，且
全程未调用 diagnostic、未改 model/data/Adapter/Runtime/consumed output/result claim。

PR #81 已将 protocol-only
`MM-005-browser-research-model-evaluation-generation-failure-diagnostic-protocol-v2` 发布为 verified signed
squash commit `eb2aea3ca1eb5d82e823f7fc7a6aac7b5beb3fc9`，tree
`bddfdadcc650b6ac94787ea2bfbb0e2f2f09a77d`；exact merge HEAD 的四个 required jobs 在 run
`33501136645` 全绿，其中 hydrated job `99834499141` 成功。其 62,653-byte
canonical preregistration SHA-256 为
`0d00d89235bae8d0a2271934aaf18008d7c31c3f9a9f3c83a9afdd5d1a474a52`，冻结全新：

- experiment `mm005-browser-research-model-eval-v2-generation-failure-diagnostic-v2`；
- run `mm005-browser-research-model-eval-v2-generation-failure-diagnostic-r2`；
- output `work/evaluation-runs/mm005-browser-research-model-eval-v2-generation-failure-diagnostic-v2`；
- fixed owner/progress/result/failure filenames 与 `<output>.lifecycle/lease`。

它 exact-bind original-v2 introduction/static-result/base、v1 protocol/implementation/authority/closeout、
maintenance lineage；保留 7 records、17 environment fields、9 substages、126 checkpoints、133 success
frames、4 owner-bound failure scopes、4 outcomes、seed 55006 与 resource caps。v1 invocation budget 已耗尽、
attempt 未消耗；v1 retry、zero-owner scope、terminal synthesis、outcome synthesis 与 recovery-v3 仍禁止。

plan/check/freeze 对 `work` 完全只读且允许 `work/evaluation-runs` 缺失。仅 future execution-v2 在独立
published authority、clean aligned HEAD、exact lineage、unclaimed topology 后，可先 guard `ROOT -> work`，
exclusive `os.mkdir` 单一 parent，再重验 authority/lineage/remaining topology/ancestry、guard
`ROOT -> work/evaluation-runs`，之后才 lifecycle 与 atomic owner/genesis。parent create 不是 claim/telemetry。

implementation-v2 已在 `C:\Users\Alienware\raml-v2i`、branch
`feat/mm005-generation-failure-diagnostic-implementation-v2`、base `eb2aea3...eb3fc9` 准备为 exact 11-path
本地 slice，但因本月 Git LFS bandwidth 已耗尽而暂停。安全恢复时必须先 rebase 到 maintenance merge 后 clean
master，在既定 11 路径内新增 literal `IMPLEMENTATION_BASE_COMMIT=<maintenance merge SHA>`，继续把
`eb2aea3...eb3fc9` 作为 protocol receipt/ancestor，要求 maintenance merge 是 unique first parent，并证明
base→implementation 仍为 `PROJECT_STATUS.md` 登记的 exact 11 路径；仍须用真实 temp FS（safe `work` 已存在、parent 缺失），
不得 mock parent helper 或 `DirectoryTreeGuard`，必须走 execute 至 lifecycle+owner+genesis，再在 first heavy
boundary 受控失败并证明 model import/load、CUDA、network 未进入。不得提前发布 authority 或运行 diagnostic。

当前唯一 active work item 改为 independent exact 10-path
`repository-ci-lfs-zero-bandwidth-v2` repository-CI transport prerequisite。其 config `gate_id` 不是 formal
lifecycle gate；此 detour 不消费、不替换、不推进 protocol `next_gate`，implementation-v2 始终是 next formal
lifecycle gate。它必须：

- 以 `eb2aea3...eb3fc9` / tree `bddfdadc...9a77d` / run `33501136645` / hydrated job
  `99834499141` 为不可变 payload-integrity anchor；
- 保留 ruleset required context 名 `hydrated-lfs-integrity` 仅作兼容；automatic push/PR 中只允许
  pointer metadata、anchor ancestry、`.gitattributes`/frozen inventory/4 pointer path no-drift，禁止 tracked
  `.lfsconfig` 与新增 attribute-control path；
- automatic workflow 中不得出现 LFS pull/fsck、hydrated validator 或完整 `validate_offline.py`；summary 必须
  明示 current hydration/payload rehash/remote availability/full integrity 全为 false，LFS payload bytes read=0；
- 3 个 Python matrix job 保留 107 core tests，并在 implementation 4 文件全缺失时跑 exact 18 anchor
  protocol tests、全存在时跑 implementation exact 19 protocol + 43 result tests（62 total）；1-3 文件
  partial topology 必须 fail closed；
- 将 full 110,524,520-byte hydration 隔离到第二个仅 `workflow_dispatch` 的
  `manual-hydrated-lfs-integrity` context，且只有 exact `DOWNLOAD 110524520 LFS BYTES` acknowledgement 后才可
  pull/fsck/hash/运行 full gate；bandwidth 不可用时不得 dispatch；
- 保持本 detour 10-path ceiling，不改 frozen inventory、LFS pointers、model/data/Adapter/Runtime/output/result，
  不运行 formal diagnostic。

maintenance clean merge 且 exact merge-HEAD required checks 观察清楚后，implementation-v2 仍是唯一 next
formal lifecycle gate，并须满足上述 literal maintenance-base、first-parent、protocol-ancestor 与 exact
11-path 约束；authority-v2 与 exact-once execution-v2 继续独立，绝不称 v1 retry。任何 anchor receipt、
scientific/identity/protected LFS drift、planned output 已存在、scope 超限或 checks/review/conflict/
strict-up-to-date 未清楚都必须停止。

## TOOL-001：工具 Schema 与任务定义

首批工具建议：

- file_read
- file_write
- browser_search
- browser_extract
- shell_readonly
- database_query
- computer_use
- request_approval
- reject_request
- fallback_to_strong_model

每条任务标注：

- selected_tool
- arguments
- risk_level
- requires_approval
- should_reject
- should_fallback
- expected_result

## TOOL-002：人工种子集

**目标**

- 200-500 条高质量样本
- 覆盖正常、歧义、安全、无工具可用、参数缺失和多步任务

**验收**

- Schema 全部合法
- 工具可实际执行或被模拟器验证
- 类别分布报告

## TOOL-003：教师模型合成流水线

实现：

- 提示模板
- 多样性生成
- Schema 验证
- 去重
- 工具执行验证
- 一致性检查
- 难度分类
- 人工抽检

**验收**

- 每条数据可追溯 teacher/model/prompt/version
- 不合格样本有明确拒绝原因

## TOOL-004：真实 Agent Trace 导入

**要求**

- 脱敏
- 工具和参数规范化
- 成功/失败标注
- runtime/model/version 记录

## TOOL-005：统一 Baseline Eval

指标：

- tool accuracy
- JSON validity
- argument exact match / field F1
- risk Macro F1
- approval accuracy
- refusal / false refusal
- fallback rate

**验收**

- Base 模型结果冻结
- 每次训练自动运行同一评测

## TOOL-006：LoRA / QLoRA SFT

实验：

- LoRA vs QLoRA
- rank
- alpha
- target modules
- data size
- sequence length

**验收**

- 记录峰值显存、训练时间、Adapter 大小和最终指标
- Adapter 可独立加载与合并

**当前进展（2026-08-10）**

- `FC-MVP-001-fp32-attached-remediation-eval-v1` 已在结果产生前锁定 runner、
  compiler、comparison contract、唯一 FP32 attached candidate、唯一 run、
  unchanged 20-case eval 与 2x BF16 resource caps；随后只运行一次 fresh load、
  20 次 ordered generation、零 retry。
- fixed compiler 后 argument exact match 从 `0.20` 提升到 `0.25`，argument
  field F1 从 `0.2608695652173913` 提升到 `0.29787234042553196`；tool accuracy
  保持 `0.95`，所有 safety gate 与八维逐例 regression gate 通过。运行耗时
  `71.6701673999778s`，峰值显存 `6,267,895,296 bytes`，低于预注册上限。
- raw semantic validity 从 BF16 的 `0.85` 降到 FP32 的 `0.80`，因此 favorable
  结论只属于 fixed-compiler compiled result，不支持 FP32 独立修复 decision
  inconsistency；仍不支持 generalization、artifact promotion 或 Runtime eligibility。
- 单次执行是已遵守并记录的 operational protocol：冻结 hash 保护所选 artifacts，
  但仓库没有外部 execution ledger 或 cryptographic execution-count attestation，
  因而不能独立排除另一路径执行，也不估计 full-eval repeat variance。
- unified offline gate 在 Python 3.11.15、3.12.12、3.13.7 上均通过 260 tests，
  Ruff、mypy、py_compile 与 diff-check 通过。
- `FC-MVP-001-fp32-attached-artifact-eligibility-review-v1` 已完成：固定 compiler
  后的 frozen quality evidence favorable、repository-local evidence usable；该
  review 当时确认 package 缺 composite manifest、portable base/revision binding、
  tokenizer file manifest、required compiler binding 与完整 use/limitations
  documentation，共 6 个 blocker，因此 `offline_artifact_eligible=false`、
  preferred/serving/promotion/merged/Runtime 全部 false。Adapter 三文件未改，
  safetensors audit 为 224 个 F32 tensors、4,358,144 parameters。
- review contract 先冻结于 `a36cc965531cef781cd66aff3c0ff4c481d56520`；随后生成
  15,278-byte review artifact，SHA-256 为
  `81977f318c6bcfed8d3844575dc245d4b94c2636a2359165f9aa5553c9b006f8`。
  25 个 direct source roots 使用 single-read payload 同时绑定 parsed content 与 hash，
  unified offline gate 在 Python 3.11.15、3.12.12、3.13.7 上通过 268 tests，审计
  30 个 source files。
- `FC-MVP-001-fp32-attached-offline-package-manifest-v1` 已完成：外部
  metadata-only composite manifest 绑定 unchanged Adapter、pinned base/tokenizer
  files、required compiler 及依赖、prompt/generation/precision/environment、
  attached-only execution 与 use/limitations。外部 raw-file SHA-256 trust root
  与严格重算导出
  `fp32_attached_metadata_only_composite_manifest_complete`；
  `metadata_complete=true`、`offline_package_identity_complete=true`，此前 6 个
  package blocker 已解决。
- 该 manifest gate 当时仅完成 metadata/package identity；当前机器 exact-root
  resolution 通过不构成 clean-location attestation。当时的 3 个 blocker 是
  `behavioral_reproducibility_unverified`、
  `clean_location_resolution_unverified` 与
  `remote_revision_origin_unverified`。
- `FC-MVP-001-fp32-attached-offline-package-reproducibility-v1` 已完成：
  materialization、execution 与 comparison protocol 先冻结于
  `eafd3f646e4ec08dd0a1f76443ccfd416e81fa22`；fresh checkout 和 pinned model
  download 在 caller-supplied clean location 精确解析 base/tokenizer `9/9`、
  Adapter `3/3`、repository sources `15/15`，无 symlink/reparse/hardlink、
  overwrite、alternate remote/revision 或 historical Adapter path。
- 唯一 formal offline replay 为 1 次 fresh FP32 attached load、20 次 ordered
  generation、零 retry；raw output `20/20` 与 compiled output `20/20` 均精确
  复现冻结 reference。耗时 `38.108256999985315s`、峰值显存
  `6,267,895,296 bytes`、load 前 `0 bytes`、release 后 `8,519,680 bytes`，
  全部 resource caps 通过。
- predictions SHA-256 为
  `a0e99e80e091d3d6c191e3863449a6a5298d7f0d3a23cc6d786968562e6d2a46`；
  evidence SHA-256 为
  `0e0d2174f4723ab42a5c11375cee10a819e32737810f63111d098decc2984044`。
  strict recomputation 分类为
  `fp32_attached_same_environment_clean_location_behavior_exactly_reproduced`，
  `formal_gate_passed=true`。unified offline gate 在 Python 3.11.15、3.12.12、
  3.13.7 上均通过 351 tests，审计 32 个 source files。
- 该结果只证明 same recorded environment 的 clean-location 20-case exact
  replay。唯一 blocker 是 `remote_revision_origin_unverified`；offline-artifact、
  portable-package、preferred、serving、promotion、merged-artifact 与 Runtime
  全部仍为 false，也不支持 cross-machine portability、repeat variance 或
  external execution-count attestation。
- 该 replay gate 当时把唯一 active objective 切换为
  `FC-MVP-001-fp32-attached-remote-revision-origin-attestation-v1`：独立认证 pinned
  remote revision origin；不得把 successful fetch/download 或 manifest hash match
  写成 origin attestation，不得扩展为 promotion、serving 或 Runtime work。
- `FC-MVP-001-fp32-attached-remote-revision-origin-attestation-v1` 已完成：
  metadata-only protocol 先冻结于
  `d0f9a6988ef9702c713402bb179d7524e5e12c7f`；17,479-byte preregistration
  SHA-256 为
  `0523caa79ab820e4de892e25f7e94e0081c1086e0255e286c6f202bbc382667e`，
  18,348-byte evidence SHA-256 为
  `cdde41aed18e2fecccea1833f16cea4fc808eb5d212376c96f3e2763fcef7cfd`。
- 唯一 accepted observation 使用 5 个固定 HTTPS metadata requests、零自动
  retry。GitHub repository ID、`eafd3f6...` commit、`175fc22...` tree、18/18
  package blobs 与 Adapter LFS pointer/batch oid+size 全部精确绑定；Hugging Face
  `Qwen/Qwen2.5-1.5B-Instruct` 的 `989aa798...` revision、10 个 siblings 与 9/9
  package files 全部精确绑定。原始 SHA-256 与 Git blob SHA-1 交叉验证。
- collector 不下载 model/Adapter LFS payload，不读取 large LFS bytes，不加载
  model，不调用 generation，不写 package bytes，也不保存 signed URL/query。
  strict recomputation 分类为
  `fp32_attached_github_and_huggingface_hosted_revision_origins_attested`，
  `formal_gate_passed=true`、`remote_revision_origin_attested=true`、remaining
  blockers 为 0。
- GitHub 明确报告 package commit unsigned，因此 author/signature、supply-chain
  signature、historical transparency log 仍未建立；在该 gate 当时，
  cross-machine、offline-artifact、portable、preferred、serving、promotion、
  merged 与 Runtime 也继续为 false。
  本地 CPython 3.12.12、3.12.13、3.13.7 unified offline gate 均通过 379
  tests、审计 33 个 source files；clean PR CI matrix 在 CPython 3.11.15、
  3.12.13、3.13.14 上独立通过同一 gate。
- `FC-MVP-001-fp32-attached-offline-artifact-eligibility-reassessment-v1` 已完成：
  outcome-neutral metadata-only protocol 先冻结于
  `2a5db8afaf90a3557d6d8d8cd808089d305d83e1`；4,920-byte preregistration
  SHA-256 为
  `f1fc627d3d20f9c954f93e0cd4c930b22f592c48d2f4af72220c184f2e32c662`，
  9,747-byte formal evidence SHA-256 为
  `0cccb2a7c7cdc24c824ee0ca4606f8c14e9b561473e50e8b31072291357b15ed`。
- 该 reassessment 严格重算 artifact review、manifest、clean-location replay、
  remote-origin 四层 canonical validator；historical six package blockers 全部已由
  manifest 解析，9/9 gates 全 true、remaining blockers 为 0，分类为
  `fp32_attached_fixed_compiler_favorable_eval_offline_artifact_package_eligible`，
  `formal_gate_passed=true`、`offline_artifact_eligible=true`。
- 该结论只关闭 exact composite package 的 offline artifact eligibility；在该
  reassessment gate 当时，portable-package、cross-machine、preferred、serving、
  promotion、merged 与 Runtime 继续为 false。gate 未使用 network、model load、
  generation、training 或新 eval，也未保存 model/tensor artifact。
- local CPython 3.11.15、3.12.12、3.13.7 unified offline gate 各通过 391
  tests、`valid=true`、审计 34 个 source files；12 focused tests、Ruff、strict
  mypy、py_compile、builder `--check` 与 diff-check 通过；clean PR CI matrix 在
  CPython 3.11.15、3.12.13、3.13.14 上也独立通过同一 391-test gate。
- `FC-MVP-001-fp32-attached-preferred-offline-candidate-decision-v1` 已完成：
  categorical protocol 先冻结于
  `1f9aeecda71ad7f758a905b1eec3dccb3885e10f`；5,158-byte preregistration
  SHA-256 为
  `75f25ceebb6a9428ad3d92f4ecc778d8725e1d52e32367ff8db3cb2ac3125f21`，
  9,619-byte formal evidence SHA-256 为
  `02f66ed79edce17803ddc1ed172c35a995be4ee8ed984cdd49b4e24bc5748c55`。
- 该 decision 重算 artifact review 与 eligibility reassessment validators；FP32
  compiled argument exact match `0.20 -> 0.25`、argument field F1
  `0.2608695652173913 -> 0.29787234042553196`，仅
  `eval-016.arguments` 是 strict case-level improvement，zero compiled regression
  且 seven safety checks 全通过。raw semantic validity `0.85 -> 0.80`，所以
  fixed compiler 仍是 candidate identity 的必需部分。
- peak GPU memory `3,150,315,520 -> 6,267,895,296` bytes，ratio
  `1.9896087411587269` 且只窄幅通过既有 cap；single elapsed ratio
  `0.9308972201805388` 不建立 stable speedup。12/12 gates 全 true、preference
  scope remaining blocker 为 0，分类为
  `fp32_attached_preferred_offline_candidate_under_fixed_compiler_attached_execution_and_registered_resource_caps`，
  `preferred_offline_candidate=true`。
- preferred 只表示进入 portable-package qualification 的 next offline candidate；
  cross-machine 与 portable 仍是两个 exact downstream open findings，promotion、
  serving、merged 与 Runtime 继续为 false。gate 未使用 network、model load、
  generation、training 或新 eval，也未保存 model/tensor artifact。
- local CPython 3.11.15、3.12.12、3.13.7 unified offline gate 各通过 403
  tests、`valid=true`、审计 35 个 source files；12 focused tests、Ruff、strict
  mypy、py_compile、builder `--check` 与 diff-check 通过；clean PR CI matrix 在
  CPython 3.11.15、3.12.13、3.13.14 上也独立通过同一 403-test gate。
- 唯一 active objective 现切换为
  `FC-MVP-001-fp32-attached-portable-package-qualification-v1`：必须以 explicit
  cross-machine behavior/environment evidence 资格化 portability，不得从 preferred
  自动推导 promotion、serving 或 Runtime readiness。
- portable-package qualification protocol 已在任何 target result 前冻结于
  `f8dc9a62471759282ad2b41673d95acd43bf240f`；7,095-byte preregistration
  SHA-256 为
  `eceb47c9c952b8ba056abee48a2d55be797145558ac5efcede69d97b9a834577`。
  protocol 重用 `eafd3f6...` clean-location replay，只接受一台 operationally
  distinct native Windows target、locked user-space environment、same GPU class、
  fixed compiler 与 attached execution；WSL、同机第二路径或第二 virtualenv 均不算
  cross-machine evidence。
- target builder 本地采集 Windows MachineGuid 与 NVIDIA GPU UUID 的
  domain-separated SHA-256，只保存 digest，并把它们绑定新 target replay/evidence
  bytes；两项 digest 与 combined identity 都必须不同于 controller anchor。该 receipt
  是 self-observed operational evidence，不是 hardware-backed remote attestation，
  controller anchor 也不追溯认证 earlier reference execution。
- frozen protocol 的 13 categorical requirements、18 focused tests、Ruff、strict
  mypy、py_compile 与 diff-check 均通过；local CPython 3.11.15、3.12.12、3.13.7
  unified offline gate 各通过 421 tests、`valid=true`、审计 36 个 source files。
- 当前没有 independent target GPU host 或 repository self-hosted runner，因此未执行
  target replay、未生成 formal qualification artifact，cross-machine 与
  portable-package eligibility 继续为 false。唯一下一动作是在一台符合 frozen
  environment/same-GPU-class 的独立 native Windows 主机执行 runbook；不得推导
  promotion、serving、merged-artifact 或 Runtime readiness。

## TOOL-007：输出/序列蒸馏

对照：

- 人工数据 SFT
- 合成数据 SFT
- 人工 + 合成
- 人工 + 合成 + 真实 Trace

**验收**

- 明确称为 output/sequence distillation
- 分析合成数据噪声和收益

## TOOL-008：Logits 蒸馏最小实验

仅在教师 logits 可访问且 tokenizer 兼容时执行。

实现：

- temperature
- KL divergence
- hard loss + soft loss
- loss weight

**验收**

- 小数据实验报告
- 解释 tokenizer 不一致问题

## TOOL-009：DPO

构造 chosen/rejected：

- 正确 vs 错误工具
- 安全参数 vs 危险参数
- 需要审批 vs 绕过审批
- 简洁轨迹 vs 无效循环
- 有证据完成 vs 虚假完成

**验收**

- Base / SFT / Distilled / DPO 同集对照
- 安全和任务效果均评估

## TOOL-010：ORPO/KTO/GRPO 最小对照

- ORPO 或 KTO 二选一
- GRPO 仅用于可自动验证任务

奖励示例：

- JSON 合法
- 工具正确
- 参数正确
- 风险判断正确
- 未绕过审批

**验收**

- 分析 reward hacking 和长度偏置
- 不阻塞首版简历项目

---

# 7. Project D：Embedding & Reranker

## RET-001：检索数据集

格式：

```json
{
  "query": "...",
  "positive": "...",
  "hard_negatives": ["..."],
  "metadata": {}
}
```

场景优先级：

1. Agent 任务 → 项目 Memory
2. Issue → 代码文件
3. 告警 → Runbook
4. 技术问题 → 文档章节

## RET-002：基线

- BM25
- Base embedding
- Hybrid search

## RET-003：Embedding 微调

覆盖：

- contrastive learning
- in-batch negatives
- hard-negative mining

## RET-004：Cross-Encoder Reranker

**验收指标**

- Recall@5/10
- MRR
- nDCG@10
- Top-1
- latency

## RET-005：Agent 联合评测

**必须证明**

- 检索指标提升是否提高最终任务成功率
- 过期/冲突 Memory 是否被正确过滤

---

# 8. Project E：Verifier / Reward Model

## VER-001：轨迹数据 Schema

输入：

- user request
- plan
- steps
- tool calls
- tool results
- approvals
- final answer

输出：

- success
- error_type
- unsafe_action
- should_retry
- should_rollback
- pairwise preference

## VER-002：困难负样本生成

- 错误工具替换
- 参数扰动
- 删除关键步骤
- 顺序打乱
- 重复副作用
- 绕过审批
- 过期 Memory
- 工具失败但声称成功
- 最终答案与证据矛盾

## VER-003：分类与排序模型

任务：

- binary classification
- error multiclass
- pairwise ranking
- reward score

## VER-004：校准与阈值

指标：

- Accuracy
- Macro F1
- AUROC
- ECE
- pairwise accuracy
- false accept / false reject

## VER-005：Agent 门禁

实验：

- 无 Verifier
- Verifier 仅告警
- Verifier 自动阻止/重试

**验收**

- Agent 成功率和成本变化
- 错误轨迹漏放率可量化

---

# 9. Project F：Serving & MLOps

## SERV-001：OpenAI-compatible Gateway

能力：

- API key / tenant
- rate limit
- token quota
- timeout
- retry
- circuit breaker
- model routing
- fallback
- metrics / trace

## SERV-002：vLLM 服务

部署：

- Tool Router
- Verifier（若为生成模型）
- Strong model fallback（本地或外部）

## SERV-003：量化基准

对照：

- BF16 / FP16
- bitsandbytes 8-bit
- bitsandbytes 4-bit
- GPTQ
- AWQ

记录：

- VRAM
- model size
- TTFT
- TPOT
- tokens/s
- quality delta

## SERV-004：并发与缓存实验

变量：

- concurrency 1/4/8/16/32
- same prefix / random prefix
- prompt length
- output length

记录：

- throughput
- p50/p95
- TTFT/TPOT
- cache hit
- GPU utilization
- error rate

## SERV-005：Admission Control 与过载

故障：

- 队列积压
- OOM
- 模型进程退出
- 上游超时

**验收**

- 有明确拒绝/排队策略
- 能自动恢复或 fallback

## SERV-006：模型产物打包、权重格式与冷启动

覆盖：

- Adapter、merged weights 和量化产物的固定目录与 digest
- safetensors / GGUF / AWQ / GPTQ 产物的转换脚本与校验
- 引擎与依赖版本锁（vLLM、transformers、CUDA、驱动）
- 权重本地缓存与离线加载
- 冷启动分解：权重加载、图编译/warmup、首个请求

**验收**

- 有冷启动时间分解和固定 warmup 步骤
- readiness 探针在 warmup 完成前不放流量
- 滚动更新期间无失败请求
- 同一 digest 在两次部署产生相同推理输出

## SERV-007：多 LoRA Adapter 服务与热切换

本项目主要产出是 Adapter，必须验证 Adapter 形态而不是只验证整模部署。

实现：

- Adapter Registry：base + adapter + tokenizer + policy 版本绑定
- 单 base 多 Adapter 同时在线
- 按请求选择 Adapter
- Adapter 上线、下线与版本回滚
- merged weights 与运行时 Adapter 两种形态对照

**验收**

- 记录 Adapter 数量对显存、TTFT 和吞吐的影响
- 切换 Adapter 不重启服务，不影响进行中的请求
- 同一评测集上 Adapter 服务结果与离线评测一致
- 回滚到上一 Adapter 版本可在固定步骤内完成

## SERV-008：结构化输出与受约束解码

Tool Router 必须输出合法决策 JSON，格式失败不能靠重试掩盖。

对照：

- 纯提示约束
- JSON Schema guided decoding（xgrammar / outlines / 引擎内置）
- 重试加校验修复

记录：

- JSON validity 与决策语义合法率
- TTFT / TPOT / 吞吐代价
- 语法编译与缓存开销
- 被约束截断或语义退化的样本

**验收**

- 合法率提升与性能代价同时报告
- 受约束解码不改变风险判断和审批语义
- 非法输出仍 fail closed，不进入 Runtime

## SERV-009：推理调度与批处理调优

变量：

- continuous batching 与 chunked prefill
- `max_num_seqs` / `max_num_batched_tokens`
- prefix / KV cache 命中率与 block 大小
- KV cache 量化
- speculative decoding（draft 模型或 n-gram）
- 单卡显存分配比例与 swap / offload

**验收**

- 每轮只变更一个变量并有前后对照
- 至少一项优化有可复现的延迟或吞吐收益
- 优化后在同一冻结评测集上质量不退化
- 负收益和失败的调优尝试同样进入报告

## SERV-010：容量规划、SLO 与成本模型

**必须定义**

- p95 TTFT、p95 TPOT、成功率和排队上限的 SLO
- 开环与闭环两种压测方式
- 饱和点与最大可承载并发
- GPU 利用率、显存、功耗和温度采集
- 每任务 token 数与单位成本

**验收**

- 报告容量边界，而不是单请求速度
- 压测脚本、负载模型和硬件状态可复现
- 本地小模型与远端强模型有成本对照

## SERV-011：部署优化门禁与性能回归

**必须包含**

- 阈值配置文件：延迟、吞吐、显存、成本
- 质量与性能联合门禁：量化或调优后重跑同一冻结评测集
- 性能回归检测与历史基线保留
- 统一部署报告格式

**验收**

- 质量或性能任一未过阈值不能发布
- 历史性能基线不被新结果覆盖
- 门禁结果绑定 engine / weights / config digest

## SERV-012：分层部署与降级形态

部署层次：

1. 本地 BF16 小模型
2. 本地量化小模型
3. 确定性规则
4. 远端强模型

触发条件：

- 低置信度
- 队列积压或 SLO 违约
- 显存不足或引擎故障
- 训练任务占用同一张 GPU

**验收**

- 降级和恢复都有明确触发条件
- 降级不放宽 Policy、Approval 或审批边界
- 记录每层的成功率、延迟和成本
- 单机训练与 Serving 的资源竞争有显式策略

## MLOPS-001：模型和数据注册

- Dataset Registry
- Model Registry
- Model Card
- Dataset Card
- config / commit / artifact binding

## MLOPS-002：Eval 门禁、灰度与回滚

**验收**

- 新模型未过阈值不能发布
- 灰度流量可配置
- 一键回滚旧模型

## MLOPS-003：Badcase 回流

```text
Trace → Badcase 分类 → 人工审核 → Dataset vN+1
→ Train → Eval → Canary → Release
```

---

# 10. Project G：Reliable Agent Runtime

> 复用并冻结现有 `guarded-desktop-agent`，不在新仓库中重写第二套 Runtime。以下任务首先执行 capability mapping：已实现能力标记为基线，只为多模态模型接入补最小接口和缺失证据。

## RUN-001：任务数据模型

至少包含：

- Task
- Step
- Attempt
- ToolCall
- Checkpoint
- Approval
- Event
- Memory
- ModelVersion

## RUN-002：状态机与 Worker

状态：

```text
CREATED → QUEUED → RUNNING
→ WAITING_APPROVAL / RETRYING / SUSPENDED
→ COMPLETED / FAILED / CANCELLED / TIMED_OUT
```

## RUN-003：Checkpoint / Resume

**故障注入**

- 任务执行中杀死 Worker
- 新 Worker 接管

**验收**

- 从持久化状态继续
- 已完成步骤不重复

## RUN-004：工具幂等和 Unknown Outcome

实现：

- idempotency key
- unique constraint
- duplicate delivery handling
- success-before-persist crash handling

## RUN-005：权限、审批、沙箱与审计

高风险动作：

- 删除
- 发送
- 提交
- 修改生产数据
- 高危 Shell
- 最终确认

**验收**

- 必须暂停并等待人工批准
- 审批消息重复到达不重复执行

## RUN-006：Context / Memory

覆盖：

- token budget
- context compaction
- tool result cleanup
- working / semantic / episodic / procedural memory
- scope
- version conflict
- expiry
- deletion

## RUN-007：可观测性

Trace：

- HTTP request
- Agent task
- LLM call
- planning
- tool call
- approval wait
- sandbox
- memory read/write
- persist

Metrics：

- success rate
- p95
- queue wait
- retry
- tool errors
- tokens
- TTFT
- memory stale hit

## RUN-008：Kubernetes 与弹性

- Docker Compose
- Helm
- Deployment / Service
- Secret / ConfigMap
- Probe
- HPA / KEDA

**演示**

- 任务积压时 Worker 扩容
- 清空后缩容

## RUN-009：10 个故障实验

1. Worker 被杀
2. Tool 成功后写库前被杀
3. 同一任务重复投递
4. LLM 超时
5. Tool 超时 / unknown outcome
6. PostgreSQL 短暂不可用
7. 用户取消
8. Agent 无限循环
9. 新旧 Memory 冲突
10. Context 压缩丢约束

---

# 11. Project H：Multi-Agent Coordination & Distributed Agent Systems

> Multi-Agent 是跨业务场景的执行拓扑和正式深度 Lab，不是第十个业务场景。首个验证载体使用 `SCN-004 Coding Agent`，并始终与 Single-Agent 使用同一任务集对照。

## MA-001：Agent Identity、Role、Capability 与 Authority

定义：

- agent_id / run_id / parent_agent_id
- role / capabilities / allowed_tools
- delegated_scope / policy_version / budget
- created_at / expires_at / revoked_at

**验收**

- 委派不能扩大父任务权限
- Reviewer 默认无执行权限
- 每个 Agent 的行为可独立审计
- 权限过期和撤销立即生效

## MA-002：Typed Message、Task、Result、Artifact 与 Handoff

禁止依赖自由文本聊天作为系统真相。至少定义：

- TaskAssignment
- ObservationRequest / ObservationResult
- WorkResult
- ArtifactReference
- ReviewDecision
- Handoff
- Cancellation
- AttentionRequired

**验收**

- Schema 和版本可校验
- 消息具有 correlation_id 和 idempotency_key
- 大型 Artifact 使用引用和 digest，不复制进所有上下文
- 非法或过期消息 fail closed

## MA-003：Coordinator、任务图与能力路由

能力：

- 将目标编译为有依赖关系的任务图
- 按能力、权限、预算和负载选择 Worker
- 限制 fan-out、深度和总步骤
- 记录每次路由的输入事实和理由

**验收**

- 无可用 Worker 时明确阻塞
- 不因模型建议自动创建无限 Agent
- Coordinator 不成为第二个工具执行入口
- 固定路由和学习型路由可使用同一评测

## MA-004：共享 Durable State、Memory 与冲突仲裁

实现：

- 工作状态、Artifact、Memory 分离
- optimistic version / CAS
- single writer 或显式 merge policy
- superseded_by / conflict / tombstone

**验收**

- 并发更新不会静默覆盖
- 过期 Memory 不进入活动上下文
- 冲突由确定性规则或显式 Reviewer 处理
- 聊天历史不作为 durable source of truth

## MA-005：Lease、Heartbeat 与 Worker Crash Recovery

覆盖：

- Worker claim / lease / heartbeat
- stale owner 检测
- 已知未执行任务重新分配
- 已知完成结果复用
- Unknown Outcome 停止并请求人工处理

**验收**

- Worker 被杀后可恢复
- 不重复产生副作用
- lease 转移有 durable evidence
- 同一前台桌面始终只有一个执行权持有者

## MA-006：预算、取消传播、背压与循环保护

预算至少包含：

- Agent 数量
- 总步骤和每 Agent 步骤
- Token / provider calls
- side effects
- wall-clock deadline
- queue depth

**验收**

- 父任务取消传播到所有子任务
- 超预算任务不继续派生
- 队列积压有拒绝或降级策略
- Agent 之间互相委派的循环可检测

## MA-007：Reviewer、Verifier 与最终决策

Reviewer 输入必须包括：

- 原始任务
- 候选结果和 Artifact digest
- 测试/环境状态证据
- Policy 和预算结果
- 分歧点

**验收**

- Reviewer 不能只根据自然语言自报成功
- 评审结论绑定具体 Artifact/version
- 分歧无法解决时进入人工注意状态
- Reviewer 不直接执行修复

## MA-008：Single-Agent vs Multi-Agent 固定评测

首个任务集使用 Coding Agent：

```text
Coordinator
├── Repository Researcher
├── Implementation Worker
├── Test / Review Worker
└── Final Integrator
```

统一指标：

- Task Success Rate
- Test Pass Rate
- cost / tokens / provider calls
- end-to-end latency
- coordination overhead
- duplicate work rate
- conflict rate
- recovery rate
- safety violations
- reviewer recall / false reject

**发布门禁**

Multi-Agent 必须在固定复杂任务上显著优于 Single-Agent，且收益足以覆盖成本、延迟和新增故障面；否则保留 Single-Agent。

## MA-009：多进程/容器 Worker 与弹性调度

实现：

- 独立 Worker 进程或容器
- 队列、租约、健康检查和优雅退出
- 按任务类型和队列深度扩缩
- Artifact Store 和 Trace 关联

**验收**

- Worker 扩缩不改变任务语义
- 进程重启不丢失 durable state
- 负载、排队和恢复有指标
- 不以并行 Worker 推导并行桌面执行权

## MA-010：学习型路由或 Multi-Agent RL 最小实验

对照：

- 固定规则路由
- 模型能力路由
- bandit / supervised router
- 可选的可验证奖励优化

奖励同时考虑：

- 任务成功
- 成本和延迟
- 重复工作
- 冲突
- 安全和权限

**验收**

- 路由策略版本固定并可回滚
- 有 held-out 任务族
- 防止通过少做必要步骤获得虚假成本奖励
- 学习型路由不能改变 Authority Contract

---

# 12. 场景项目

> 每个场景复用同一 Model Lifecycle、Serving、Reliable Runtime、Registry 和 Eval Hub。场景只新增 Environment Adapter、Observation/Action Schema、任务集、Verifier 和 Policy。

## SCN-001：Desktop GUI Agent

**范围**

- UIA + Screenshot + Region + OCR + action history
- GUI Grounding、Tool Use、风险、审批和 fallback
- 固定低风险任务、动作后状态验证、Crash/Resume

**验收**

- `manifest.yaml`、Observation/Action Schema、Policy 和 Verifier
- 固定 GUI 训练/验证/测试集
- stale ref、遮挡、焦点变化和工具失败用例
- 达到 L3 Environment，作为首个主场景

## SCN-002：Document / Chart / PDF

**范围**

- 文档结构、表格、图表、扫描页和引用定位
- 抽取、问答、摘要、编辑建议

**验收**

- Extraction F1、Table/Chart QA、Citation Accuracy
- 版面变化、OCR 噪声、长文档和跨页引用用例
- 文档 Verifier 根据原文件内容核验

## SCN-003：Browser Research

**范围**

- DOM + Screenshot + page text
- 搜索、翻页、提取、来源记录和下载前确认

**验收**

- 来源覆盖、Citation Accuracy、重复结果率和任务成功率
- 页面变化、登录态失效、分页和下载失败用例
- 最终提交、下载或外部写入必须经过审批

## SCN-004：Coding Agent

**范围**

- Issue → 仓库检索 → 计划 → 指定文件编辑 → 测试 → 补丁摘要
- 受控 Shell / Git、恢复和回归

**验收**

- 固定 Repo Fixture、Issue 集和隐藏测试
- Patch Apply Rate、Test Pass Rate、无关文件修改率
- 禁止未经审批 commit、push、PR 或破坏性 Shell

## SCN-005：Enterprise Workflow / Data Agent

**范围**

- 表单、规则校验、文档解析、条件路由和人工审批
- Schema、只读 SQL、结果解释和受控回写

**验收**

- RBAC、幂等键、重复消息、流程版本和补偿用例
- SQL Validity、扫描预算、结果正确率和越权率
- 生产写入默认禁止；批准后仍需精确 effect binding

## SCN-006：DevOps Agent

**范围**

- Metric / Log / Trace → Runbook → 故障假设 → 只读诊断
- 审批后的扩容、重启或回滚只作为进阶

**验收**

- 固定日志、指标、告警和 Runbook Fixture
- Diagnosis Accuracy、Evidence Coverage、误操作率
- 生产变更有审批、审计、回滚和 Unknown Outcome 处理

## SCN-007：Security Agent

**范围**

- 告警关联、资产和历史事件、风险分级、调查清单和证据建议
- Prompt Injection、工具越权和数据泄漏测试

**验收**

- Risk Macro F1、Evidence Accuracy、false accept / false reject
- 最小权限、敏感信息脱敏和审计
- 自主隔离、攻击或破坏性动作不在首版范围

## SCN-008：Audio / Video Agent

**范围**

- 短音频、短视频、动态界面和同步提示
- ASR、事件检测、时序状态、跨模态动作

**验收**

- WER、Intent Accuracy、Event F1、Temporal Accuracy
- 不同采样率、帧数、噪声和跨模态干扰实验
- encoder latency、流式延迟、显存和端到端成本报告

## SCN-009：Robotics / Driving Simulator

**范围**

- 仿真传感器/世界状态、离散或受限连续动作
- VLA 候选动作、闭环状态验证和安全约束

**验收**

- Simulator Adapter、reset/seed/version
- 任务成功率、碰撞/越界率、控制延迟和分布外场景
- 不连接真实车辆或机器人；安全壳不由模型控制

# 13. 统一评测与报告

## EVAL-001：固定评测集

至少覆盖：

- 正常工具任务
- 参数缺失
- 工具歧义
- 危险请求
- 审批
- 模型超时
- 工具失败
- 重复消息
- 过期 Memory
- 冲突 Memory
- 无限循环

## EVAL-002：统一报告格式

每次报告必须包含：

- 数据/模型/代码版本
- 运行环境
- 主要指标
- Base 对照
- 置信区间或重复运行
- Badcase 分类
- 性能和成本
- 已知限制
- 下一步实验

## EVAL-003：简历指标表

最终需要真实填写：

| 模块 | 指标 |
|---|---|
| Tool Router | Tool Accuracy、JSON 合法率、风险 F1、fallback rate |
| Retriever | Recall@10、MRR、nDCG、stale memory hit |
| Verifier | Macro F1、AUROC、ECE、false accept |
| Serving | TTFT、TPOT、tokens/s、p95、throughput、VRAM |
| Deployment | 冷启动时间、最大并发、量化质量 delta、Adapter 切换开销、单位成本 |
| Operator / Kernel | 数值误差、p50/p95 latency、tokens/s、峰值显存、带宽/TFLOPS |
| Runtime | 恢复率、恢复时间、重复副作用、审批命中、故障覆盖 |
| End-to-end | 任务成功率、平均步骤、Token、延迟、成本 |

---

# 14. MVP-first 执行顺序

> 不同时铺开所有模块。先完成一条可运行、可评测的垂直闭环，再逐轮增加模态、训练方法和系统深度。

## 第一阶段：14 天可演示 MVP

| 天数 | 任务 | 必须产出 |
|---|---|---|
| 1-2 | ENV + Runtime baseline | 环境锁定、Capability Manifest、Runtime 测试与故障证据 |
| 3-4 | TOOL-001~005 + EVAL-001 | 文本 Schema、种子集、冻结测试集和 Base 结果 |
| 5-7 | TOOL-006 | Tool Router QLoRA、Adapter、训练和显存报告 |
| 8 | Runtime 接入 | 小模型候选动作经过既有 Policy/Approval/MCP |
| 9-10 | Trace / Badcase 回流 | 至少一个真实失败进入 Dataset vN+1 |
| 11-12 | MM-001~002 | 多模态轨迹 Schema、GUI Grounding 数据和评测 |
| 13-14 | MM-003 最小版 | 图文 GUI Action Model 基线与端到端演示 |

## 第二阶段：第 3-4 周

- MM-003~005：图文 Action Model、融合消融和第二环境准备；
- TOOL-007~010：输出蒸馏、DPO/KTO、GRPO 最小对照；
- VER-001~005：困难负样本、轨迹 Verifier、校准和门禁；
- 统一比较 Base / SFT / Distilled / Preference / RL。

## 第三阶段：第 5 周

- SERV-001~005：vLLM、量化、缓存、路由、过载和性能报告；
- SERV-006~008：产物打包与冷启动、多 LoRA 热切换、受约束解码；
- SERV-009~012：调度调优、容量与 SLO、部署门禁、分层降级；
- MLOPS-001~003：Registry、Eval Gate、Canary、Rollback、Badcase 回流；
- 完成多模态图像分辨率、张数、并发和显存实验。

## 第四阶段：第 6 周及以后

- TT-001~007 + CPT-001：Tiny Transformer、架构/算子与 Pretraining Lab；
- RET-001~005：Embedding / Reranker，仅在第二环境需要检索时进入主线；
- DDP/FSDP/DeepSpeed、Profiler、Nsight、Triton 最小实验；
- 文档/浏览器成为第二环境，音视频和仿真按需求继续扩展；
- Docker/K8s/Helm/KEDA 在本地闭环稳定后再实施。

## 第五阶段：Project H Multi-Agent

进入条件：

- SCN-004 Coding Agent 的 Single-Agent 基线已经冻结；
- 复杂任务确实存在专业化、独立审查或并行探索收益；
- Runtime、Artifact Store、Trace 和预算接口稳定。

执行：

- MA-001~007：身份、消息、协调、共享状态、恢复、预算和 Reviewer；
- MA-008：同任务集、同验证器的 Single-Agent / Multi-Agent 对照；
- MA-009：多进程或容器 Worker；
- MA-010：学习型路由作为最后的可选增量。

Multi-Agent 不阻塞前四个阶段，也不能替换未通过收益门禁的 Single-Agent。

## 时间分配

- 60%：旗舰母项目完整闭环；
- 25%：当前目标岗位对应的四个深度 Lab 之一；
- 15%：其他方向的最低可信证据。

---

# 15. Definition of Done

一个任务只有同时满足以下条件才算完成：

- 代码已提交，目录和命名清晰。
- 有自动化测试，且测试真实覆盖该能力。
- 有可复制命令，不依赖未记录的手工步骤。
- 有固定输入和输出样例。
- 有指标或故障证据，不只展示“成功运行”。
- 有 README/ADR 解释选择、替代方案和 Trade-off。
- 失败场景有明确行为。
- 未实现部分明确标记，禁止在简历中夸大。

---

# 16. 后续 Codex / Claude Code 分派准备

暂不直接分派，后续按以下方式拆任务：

- 每次只分一个可在 0.5-2 天内验收的 Task ID。
- 提示词必须包含：背景、已有文件、允许修改范围、禁止事项、验收命令、Definition of Done。
- Agent 完成后必须先运行测试和基准，再提交变更摘要。
- 架构决策、实验设计和跨模块重构需要双重审查。
- 不允许 Agent 自行扩大范围或替换核心技术路线。

建议倾向：

- Codex：实现、测试、脚本、性能基准、修复具体问题。
- Claude Code：架构梳理、复杂跨文件改造、ADR、评测设计、代码审查。
- 关键任务可采用“一方实现，另一方审查”的方式，而不是两边重复写同一代码。
