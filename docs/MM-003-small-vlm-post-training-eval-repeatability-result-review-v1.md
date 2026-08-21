# MM-003 small-VLM 后训练评测可重复性结果评审 v1

> **结论：正式唯一回放完成；固定九例评测的 raw output、compiled
> prediction、metrics 与 generated-token counts 全部一致。在本结果评审后，
> 仅建立同一本机、注册环境、固定评测范围内的 bounded eval repeatability；
> 不建立训练、资源、跨机、泛化质量、服务、晋升或 Runtime 结论。**

## 评审决定

正式执行分类为
`same_machine_fixed_eval_repeatability_measurement_complete`。本次独立、
model-free 结果评审重新校验 frozen artifact receipts，重算 scorer，重新绑定
candidate 与 predictions，并从冻结输入逐字节重建 `evidence.json`。评审没有重载
模型，也没有使用 CUDA。

评审分类为
`same_machine_fixed_eval_raw_compiled_metrics_and_generated_token_counts_exact`。
原始执行 evidence 中按 fail-closed 约束保持为 false 的
`same_machine_eval_repeatability_established`，由这个独立结果评审在核对全部证据后
提升为 true。该提升只适用于同一本机、注册环境和固定九例 MM-002 synthetic eval，
不是更广泛的模型、训练或部署授权。

协议绑定如下：

- frozen protocol merge commit：
  `c72b3bd1666ed6b03d9425e1dbaacfe115dda4f8`；
- preregistration：22,951 bytes，SHA-256
  `723db665f98e53ef2fe968ee7c6fe663b42d79b86176eef5cf70f11ccc4a312b`；
- execution gate：
  `MM-003-small-vlm-post-training-eval-repeatability-execution-v1`；
- result-review gate：
  `MM-003-small-vlm-post-training-eval-repeatability-result-review-v1`。

固定输出目录在执行前不存在。owner-marked staging directory 原子重命名到固定目录
后即消费这次 one-shot replay；正式目录只包含四个预注册成功产物，没有
`failure.json`，没有第二次执行或 retry。

## 冻结证据

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `baseline/mm003-qwen2.5-vl-3b-qlora-sft-v2-eval-repeatability-v1-attempt-owner.json` | 586 | `8f6c267ab262021ac6b8805606b9a7e7bb071507968e5d94a0c4b25eadb3d7fb` |
| `baseline/mm003-qwen2.5-vl-3b-qlora-sft-v2-eval-repeatability-v1-evaluation-candidate.json` | 9,855 | `a354f4b3f2b20467ed7d82916345f7b951ca6df1ad9ecc5816734410694e155b` |
| `baseline/mm003-qwen2.5-vl-3b-qlora-sft-v2-eval-repeatability-v1-predictions.json` | 2,241 | `c2c703e5896fe64df9e156bda9d38975b92c1bf18c72f74f5a232dcbbbc4a028` |
| `baseline/mm003-qwen2.5-vl-3b-qlora-sft-v2-eval-repeatability-v1-evidence.json` | 20,243 | `e20262debfbefa3e361855728aa8852f1219053d6fb9152158a2916c806a7ad2` |
| `baseline/mm003-qwen2.5-vl-3b-qlora-sft-v2-eval-repeatability-v1-result-review.json` | 15,119 | `8979693b6962849555e533332331d91dbb9fad8294f7fbc6703fa09ab3414f4a` |

四个执行产物均为 strict canonical JSON，并通过 owner、candidate、prediction、
completed-evaluation 和 evidence validators。17 个 protocol source receipts 与 frozen
preregistration 重新认证成功；从 authenticated upstream result、冻结输入和 replay
内容重建的 evidence 与现有 20,243-byte `evidence.json` 逐字节一致。

## 13 个 formal gates

下列 13 个注册 gate 全部通过：

1. `protocol_integrity`
2. `reference_result_integrity`
3. `exact_model_files`
4. `exact_adapter_files`
5. `locked_environment`
6. `unchanged_mm002_inputs`
7. `offline_single_replay`
8. `prediction_identity`
9. `attempt_ownership`
10. `candidate_and_predictions_binding`
11. `layered_comparison_complete`
12. `resource_caps`
13. `fail_closed_claims`

`formal_gate_passed=true` 表示预注册的测量完整性门禁通过。该协议没有注册 quality
threshold，因此 gate 通过不等于模型质量、安全性或部署资格通过。

## 三层 exact comparison

`all_layers_exact=true` 在本协议中严格由以下三层组成：

1. 九个 UTF-8 raw model output；
2. 九个 compiler 输出的 canonical JSON prediction；
3. scorer 输出的 canonical JSON metrics。

它不是神经网络逐层 tensor 对比，也不包含 logits、hidden states 或 token-ID 序列。
三层结果为：

| Layer | Exact result | Reference SHA-256 | Replay SHA-256 |
|---|---:|---|---|
| Raw outputs | 9/9 | `64f500374fb326b4e38500c5433dbbd6596d69f35b548ee161ce34f623286d02` | `64f500374fb326b4e38500c5433dbbd6596d69f35b548ee161ce34f623286d02` |
| Compiled predictions | 9/9 | `a2f1d4d69d3ab42a784543474277dcfb45c363ecee86148820af0e2986b3486a` | `a2f1d4d69d3ab42a784543474277dcfb45c363ecee86148820af0e2986b3486a` |
| Metrics | all exact | `c49622539576a64823d4bfc5aead9a00244a48044e5603673c61725b9c3b7d44` | `c49622539576a64823d4bfc5aead9a00244a48044e5603673c61725b9c3b7d44` |

所有 mismatch case/metric 列表为空，compiler fallback 差异列表也为空。
`generated_tokens` 计数另外达到 9/9 exact，且没有 token-count mismatch case。
这个诊断字段只持久化每例生成 token 的数量，**没有持久化 token-ID 序列**；因此
不能据此声称内部 token path、logits 或隐藏数值逐项一致。

## 固定 metrics

| Metric | Reference | Replay | Exact |
|---|---:|---:|---:|
| Grounding Accuracy | 3/5 (`0.6`) | 3/5 (`0.6`) | true |
| mean IoU | 1/2 (`0.5`) | 1/2 (`0.5`) | true |
| Action Accuracy | 3/9 (`0.3333333333333333`) | 3/9 (`0.3333333333333333`) | true |
| Tool Accuracy | 5/5 (`1.0`) | 5/5 (`1.0`) | true |
| Argument Exact Match | 5/5 (`1.0`) | 5/5 (`1.0`) | true |
| stale-ref rejection | 0/2 (`0.0`) | 0/2 (`0.0`) | true |
| coordinate/ref disagreement rejection | 0/1 (`0.0`) | 0/1 (`0.0`) | true |
| prediction coordinate/ref disagreement | not applicable | not applicable | true |

这里的 exact 表示第一次正式结果与本次 replay 的值相同，不把已有的 `0/2`、`0/1`
rejection failure 改写成成功，也不新增 quality improvement claim。

## Execution 与资源记录

正式 replay 使用一次 fresh base load、一次 independent Adapter load、一次完整评测和
九次按冻结顺序执行的 generation call：

| Counter | Attempts | Completed |
|---|---:|---:|
| Fresh base load | 1 | 1 |
| Independent Adapter load | 1 | 1 |
| Full eval run | 1 | 1 |
| Generation | 9 | 9 |

`training_runs=0`、`optimizer_steps=0`、`backward_calls=0`、
`adapter_writes=0`、`network_attempts=0`、`network_used=false`、
`retry_count=0`。

| Resource | Observed | Registered cap | Cap used |
|---|---:|---:|---:|
| Elapsed | `62.72212420000005` seconds | `1,800` seconds | `3.484562%` |
| Peak CUDA allocated | `6,456,984,064` bytes | `16,500,000,000` bytes | `39.133237%` |
| Peak CUDA reserved | `7,161,774,080` bytes | `16,500,000,000` bytes | `43.404691%` |

九例 case latency 的总和、均值、最小值和最大值分别为
`44.11204930000122`、`4.901338811111247`、`3.109916500000054` 和
`6.567106800000147` 秒。

这些时间和 CUDA counters 是正式执行自身记录的单次观察值。model-free result review
验证字段、类型、caps 和 evidence binding，**没有独立重跑模型、计时或 GPU memory
measurement**。因此只能确认本次执行未超 cap，不能建立 latency、throughput 或
resource repeatability。

## 环境恢复边界

正式执行前，`work/training-env/Scripts/python.exe` 原来引用的 Anaconda base
interpreter 已不存在。执行环境没有恢复原 Anaconda vendor 或其原始 binary identity；
它使用 `Astral python-build-standalone via uv` 的
`cpython-3.12.12+20260211-x86_64-pc-windows-msvc-install_only_stripped`
恢复 Python 3.12.12 base，再安装已记录 SHA-256 的
`torch-2.6.0+cu124-cp312-cp312-win_amd64.whl`。

正式 launcher 仍为注册路径 `work/training-env/Scripts/python.exe`，其大小为
274,248 bytes，SHA-256 为
`e39ec6e8b80e547ba1b83f7e825122304c106448425207d8496e464757c20c20`。
恢复后，协议注册的 Python、direct dependency、Torch/CUDA、GPU 和 Adapter/model
字段通过 exact environment gate。

但 `requirements/mm003_qlora_training.lock` 只冻结十个 direct entries：direct
versions exact，但没有 hash lock，也不是完整 transitive dependency closure，
transitive dependency hashes 也没有 pin。本次观察到的 transitive versions 记录在
result-review artifact 中，不能反向证明原 Anaconda 环境逐字节复现或建立 hermetic
environment。环境恢复材料的证据类别是
`reviewer_observed_untracked_context`；两个本地 install report 都位于 `work/` 且
`tracked=false`，所以不能仅从 tracked receipts 独立重算 interpreter distribution
或 package provenance。正式 execution preflight 时恢复环境已经可用，并通过注册
字段的 formal environment gate；这不把 untracked recovery context 提升为 hermetic
provenance。相应地：

- `byte_identical_original_base_established=false`；
- `hermetic_environment_established=false`；
- 原 Python base vendor 与 binary identity 均未复现。

这里的“same machine”表示 reference 与 replay 在同一台本地 controller 上、并满足
协议注册环境字段的 operational scope。该 gate 没有保存或比较 Windows
MachineGuid、GPU UUID 等 machine identity，也不是 hardware-backed 或 remote
attestation；它不证明跨机器可移植性，也不能把“同机”扩展为硬件身份的密码学证明。

## Claims 与限制

本结果评审允许为 true 的 claims 只有：

- `replay_executed=true`；
- `model_evaluated=true`；
- `formal_measurement_complete=true`；
- `same_machine_eval_repeatability_established=true`。

以下结论全部保持 false：

- `training_repeatability_established`；
- `cross_machine_reproducibility`；
- `resource_repeatability_established`；
- `generalized_quality_improvement_established` 与 `quality_improved`；
- `real_content_behavior_established` 与
  `safety_rejection_success_established`；
- `direct_desktop_execution_established`；
- `merged_artifact`、`portable_artifact` 与 `commercial_use_eligible`；
- `serving_eligible`、`promotion_eligible` 与 `runtime_eligible`。

结果仍受以下范围限制：一个 reference 加一个 replay、同一本机、固定 synthetic
九例 eval；没有建立 full-eval repeat variance 或外部 execution-count attestation，
也没有测试训练可重复性、资源可重复性、跨机、真实内容、直接桌面执行或 Runtime
integration。原 Anaconda binary 未恢复、transitive dependencies 未完整锁定、
token-ID 未持久化，以及资源/时间未独立复测，也都必须随结果保留。

## 单一下一 gate

MM-003 的这条后训练评测可重复性链在本次 result review 后关闭。单一下一 gate 是：

`MM-004-multimodal-hard-negative-data-protocol-v1`

下一动作是在生成、训练或评测任何新的 MM-004 困难负样本之前，先冻结一个
model-free multimodal hard-negative data protocol。不得把本次已消费 replay 当作可
再次执行的 retry，也不得借本结论提升 serving、promotion 或 Runtime authority。

## Model-free 复核

```powershell
python -I -B -X pycache_prefix=NUL .\scripts\validate_mm003_post_training_eval_repeatability_result.py
```

该 validator 只读取和重建冻结 artifacts，不加载模型或使用 CUDA。它输出
`all_layers_exact=true`、raw/compiled `9/9`、`metrics_exact=true`、
`same_machine_eval_repeatability_established=true`，并确认下一 gate 为 MM-004。

## 验证结果

Focused result-review suite 在本机 CPython 3.11.15、3.12.12、3.13.7 上均为
11/11 passed。三个解释器的 unified offline gate 均为 611 tests、4 个预期的
Windows symlink privilege skips、50 audited source files 和 `valid=true`。

全仓 Ruff、Python `py_compile`、新 validator 的 scoped strict mypy、冻结协议
`prepare --check`、默认 model-free result validator 与 `git diff --check` 全部通过。
这些检查没有再次加载模型、访问 CUDA、删除或复用已消费 output directory。
