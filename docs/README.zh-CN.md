# 项目文档索引

English (default): [README.md](README.md)

仓库保留项目说明、已实现技术证据、维护入口和从冻结证据派生的职业学习资料。
职业与面试材料不是项目依赖或第二进度 tracker；项目顺序和完成状态仍只由
`PROJECT_STATUS.md` 管理。

## 项目与维护入口

| 文档 | 用途 |
|---|---|
| [中文仓库 README](../README.zh-CN.md) | 项目定位、架构、边界和已实现模块 |
| [PROJECT_STATUS](../PROJECT_STATUS.md) | 唯一当前目标、顺序和最新验证结果 |
| [Desktop Runtime 依赖与集成](../Desktop_Runtime_依赖与集成.md) | 跨仓所有权、安全边界和版本 pin |
| [AGENTS](../AGENTS.md) | Coding agent 工作约束 |
| [职业与学习中心](career/) | 面试手册、求职证据与教学协作方法 |
| [完整面试手册](career/interview/) | 面向 ML/DL 基础读者的原理、应用、工程、题库和项目故事 |

## 已实现技术证据

| 主题 | 文档 | 状态 |
|---|---|---|
| Runtime bridge consumer | [FC-BRIDGE-001](FC-BRIDGE-001.md) | Complete |
| Lane A reliability dataset | [ADR-0001](adr/ADR-0001-lane-a-reliability-dataset-v1.md) | Complete |
| Lane B consent/capture/security contract v1 | [FC-BRIDGE-003 review](FC-BRIDGE-003-lane-b-consent-capture-security-v1.md) | Contract review complete；真实采集仍未实现 |
| 标准库离线基线 | [ADR-0002](adr/ADR-0002-stdlib-offline-baseline.md) | Complete |
| Python / 工具链环境 | [Environment baseline](environment.md) | Complete |
| Tool Router schema / eval | [FC-MVP-001 schema/eval](FC-MVP-001-schema-eval.md) | Complete |
| 本地 Base model baseline | [FC-MVP-001 base model](FC-MVP-001-base-model-v1.md) | Complete，未通过安全门禁 |
| 首次本地 LoRA SFT | [FC-MVP-001 LoRA SFT v1](FC-MVP-001-lora-sft-v1.md) | Complete，未获 Runtime 准入 |
| FP32 attached/merge numerics v1 | [FC-MVP-001 FP32 attached/merge numerics](FC-MVP-001-fp32-attached-merge-numerics-v1.md) | Complete locally；numerics gate passed，remediation / Runtime 未通过 |
| BF16/FP32 attached dtype boundary control v1 | [FC-MVP-001 attached dtype boundary control](FC-MVP-001-attached-dtype-boundary-control-v1.md) | Complete locally；boundary control matched，remediation / Runtime 未通过 |

## 后续开发资料

| 文档 | 用途 |
|---|---|
| [多模态 LLM 全周期 MVP 演进路线](../多模态LLM全周期_MVP演进路线.md) | MVP 顺序、指标和扩展边界 |
| [多模态与业务场景覆盖矩阵](../多模态与业务场景覆盖矩阵.md) | 模态、环境、任务和场景契约 |
| [待做任务清单](../AI_Infra_LLM_Agent_待做任务清单.md) | 任务编号、依赖和 Definition of Done |
| [写作与执行模块模板](../AI_Infra_LLM_Agent_写作与执行模块模板.md) | 实验、ADR、评测、审查和验收模板 |
