# 00. Python、Git、操作系统与 CUDA 工程基础

> 本章补齐 ML/DL 之外的工程底座，不是项目进度 tracker。框架和系统 API 会演进，
> 这里强调稳定的语义、故障模型与验证方法。项目完成状态只看
> [PROJECT_STATUS.md](../../../PROJECT_STATUS.md)。

## 1. 面试定位与学习目标

模型工程失败经常不发生在公式里，而发生在文件覆盖、依赖漂移、进程退出、异步 CUDA
计时、错误的 retry 或 Git/artifact 身份混淆。完成本章后，应能：

1. 写出可测试、可类型检查、资源生命周期明确的 Python pipeline；
2. 解释 PyTorch tensor storage/stride、module mode、device transfer、checkpoint 与
   DataLoader multiprocessing 的真实语义；
3. 区分 unit、contract、property、golden、integration 和 fault-injection tests；
4. 用 Git object model 解释 commit、tree、blob、branch、merge、rebase 与 Git LFS；
5. 正确处理 path、encoding、atomic write、subprocess、exit code 与跨平台差异；
6. 解释 CUDA host/device、kernel、stream、memory hierarchy 和同步计时；
7. 区分 PyTorch allocated/reserved memory、OOM、memory leak 与 fragmentation；
8. 把 code/data/model/environment identity 组成可复现工程合同。

证据标签沿用全手册：`[原理]`、`[通用工程]`、`[本仓库已实现]`、
`[本仓库待实施]`。

## 2. Python：从脚本到可靠 pipeline

### 2.1 Object、reference、mutability 与 copy

`[原理]` Python 变量绑定 object，不是把值存入带类型的盒子。两个名字可指向同一
mutable object：

```python
a = {"metrics": []}
b = a
b["metrics"].append(0.95)
assert a["metrics"] == [0.95]
```

常见工程错误：

- 用浅拷贝复制嵌套 config，子对象仍共享；
- 把 mutable default 放在 function 或 dataclass field 中；
- 原地修改传入 record，使 raw、normalized、scored 三层事实混在一起；
- cache 返回 mutable object，调用方静默污染后续请求。

对证据 pipeline，优先使用 immutable/frozen value object、显式 constructor 和 copy-on-
transform：每个 stage 返回新 artifact，并保留输入 identity。需要 deep copy 时先问清
object graph、tensor storage 和文件 handle；盲目 `deepcopy` 可能昂贵或不可行。

### 2.2 Iterator、generator 与流式处理

`[原理]` Iterable 能产生 iterator；iterator 的 `__next__` 消耗状态；generator 用
`yield` 延迟计算。流式读取可以把 memory 从 `O(N)` 降到接近单 record/buffer，但会
带来 one-pass 语义：

```python
def read_jsonl(path):
    with path.open("r", encoding="utf-8", newline="") as handle:
        for line_number, line in enumerate(handle, start=1):
            yield line_number, parse_one_record(line)
```

可靠工程需额外处理：

- iterator 被提前消费或重复迭代；
- 中途 exception 后 partial output；
- 全局统计需要 two-pass、online algorithm 或临时 index；
- fail-fast 与收集全部 reject reason 的选择；
- 输入顺序是否属于 canonical artifact identity。

大文件 validator 常采用 single-read raw bytes：先从同一 byte payload 计算 digest，再
parse，避免“hash 的文件”和“解析的文件”在两次读取之间发生 TOCTOU 改变。

### 2.3 Context manager 与资源生命周期

`[原理]` Context manager 用 `__enter__/__exit__` 或 `contextmanager` 把 acquisition 与
release 组成 lexical scope。适用于文件、锁、临时目录、数据库 transaction、模型 hook、
autocast 和 no-grad。

```python
with acquire_model(candidate) as model:
    result = run_registered_eval(model)
# 离开 scope 后验证 hook 被移除、GPU references 被释放
```

`finally` 必须处理 release；但 release failure 不能覆盖原始 exception。对 GPU lifecycle，
还要清除 Python references、触发必要 synchronization，再测 allocated memory；仅离开
`with` 不保证所有异步工作已结束。

### 2.4 Exception taxonomy 与 fail-closed

不要捕获所有 exception 后返回 `None`。定义稳定错误层级：

```text
InputContractError
  ├─ SchemaVersionError
  ├─ DigestMismatchError
  └─ UnsafePathError
ExecutionError
  ├─ DefinitiveFailure
  └─ UnknownOutcome
EvidenceError
  ├─ IncompleteArtifact
  └─ RecomputeMismatch
```

`[通用工程]` 边界层把 exception 转换为 machine-readable error code、非零 exit code 和
脱敏日志；核心层保持具体类型。只有预期、可恢复错误才捕获。Unknown Outcome 绝不能
被普通 retry handler 当成 definitive failure。

### 2.5 Dataclass、typing、Protocol 与 schema

Python type hints 主要用于静态检查与设计沟通，不自动做 runtime validation。

- `dataclass(frozen=True)`：适合内部 immutable value object；
- `TypedDict`：描述 dict shape，runtime 仍需 validator；
- `Enum/Literal`：关闭状态空间；
- `Protocol`：按行为定义可替换 boundary，便于 fake/test；
- `NewType` 或 wrapper：避免把 artifact ID、digest、path 当成同一种 `str`；
- JSON Schema：跨语言 wire/storage contract；
- parser/validator：把 untrusted JSON 转成 typed domain object。

```python
class ArtifactStore(Protocol):
    def read_verified(self, identity: ArtifactIdentity) -> bytes: ...

@dataclass(frozen=True)
class CandidateIdentity:
    base_revision: str
    adapter_sha256: str
    compiler_sha256: str
    execution_form: Literal["attached", "merged"]
```

静态类型、runtime schema 和 semantic validation 分别捕获不同错误，不能相互替代。

### 2.6 Thread、process 与 async

三种 concurrency 解决不同 workload：

| 方式 | 适合 | 关键风险 |
| --- | --- | --- |
| `asyncio` | 大量可等待 I/O、单线程事件循环 | blocking call 卡住 loop、取消/timeout 泄漏 |
| Thread | 阻塞 I/O、会释放 interpreter lock 的 native op | race、共享 mutable state、线程池耗尽 |
| Process | CPU-bound Python、failure isolation | serialization、启动成本、复制内存、IPC |

传统 CPython build 中，interpreter lock 会限制多个 Python threads 同时执行 CPU-bound
bytecode；但 native libraries 可能释放它。不要用一句“Python 不能多线程”回答。对 GPU
workload，Python 可能只负责 enqueue，真正计算在设备异步执行；瓶颈需 profile。

Async cancellation 是 cooperative：取消 coroutine 不代表下游 HTTP/tool/GPU 操作已
撤销。必须传播 deadline、释放 reservation，并对已产生副作用进入 reconciliation。

### 2.7 PyTorch runtime：Tensor、Module、Device 与 DataLoader

#### Storage、shape、stride 与 view

`[原理]` Tensor 不只是一个多维数组值；还包含 dtype、device、shape、stride、
storage offset，并引用底层 storage。多个 Tensor 可以共享同一 storage：

```python
x = tensor([[1, 2, 3], [4, 5, 6]])
y = x.transpose(0, 1)       # 通常共享 storage，但 stride 改变且可能 non-contiguous
z = y.contiguous()          # 需要时分配按当前逻辑顺序排列的新 storage
```

- `view` 要求 stride/layout 兼容，通常不复制并共享 storage；
- `reshape` 会尽量返回 view，不能时才复制，因此调用方不应依赖其 aliasing；
- `permute/transpose` 常只改变 metadata，后续 kernel 是否接受该 stride 要单独验证；
- `contiguous` 只在需要时复制，可能产生显存与延迟峰值；
- in-place write 会影响所有 alias，并可能触发 autograd version-counter 错误。

面试中遇到“结果正确但显存突然上升”，要检查隐式 contiguous copy、dtype cast、
broadcast materialization 和 retained view，而不只统计参数量。

#### `train/eval` 与 grad mode 是正交轴

`model.train()` / `model.eval()` 改变某些 module 的 forward behavior，例如 Dropout 与
BatchNorm；`no_grad()` / `inference_mode()` 控制是否记录 autograd。两类状态不能互相
替代：

```python
model.eval()
with inference_mode():
    predictions = model(inputs)
```

只调用 `eval()` 仍可建立 computation graph；只进入 `no_grad()` 也不会关闭 Dropout。
`inference_mode()` 比 `no_grad()` 约束更强，可能减少额外 bookkeeping，但其中产生的
Tensor 后续能否参与需要 autograd/version tracking 的路径必须按框架 contract 验证。
Evaluation 要冻结 model mode、grad mode、autocast 和 backend，而不是只写“inference”。

#### Device、dtype 与 transfer

Tensor operation 通常要求参与计算的数据位于兼容 device，并满足 kernel 支持的 dtype。
`.to(device/dtype)` 可能返回原对象，也可能创建新 Tensor，因此应使用返回值而不是假设
原地修改。Module 的 registered parameters 与 buffers 会随 `.to()` 移动，但普通 Python
attribute 不会自动成为 buffer；token IDs 等索引通常仍需整数 dtype。

Pinned CPU memory 配合支持的 async copy、目标 stream 和 `non_blocking=True` 才可能让
host-to-device transfer 与 host 工作重叠。“设置了 non_blocking”不自动证明异步；在
复用 host buffer、跨 stream 消费、读取 CPU 结果或计时前必须建立正确依赖/同步。

#### `state_dict`、完整 Module pickle 与恢复合同

`state_dict` 是参数与 registered buffers 的键值映射；可靠 checkpoint 通常保存它、
optimizer/scaler/scheduler state、step、RNG/data-order state 和结构化 config，再由受版本
控制的代码重建对象并 strict-load。还要核对 missing/unexpected keys、shape、dtype、
model/tokenizer revision 与 digest。

直接 pickle 整个 Module 会绑定 Python class/import path 和执行环境，更脆弱；反序列化
不可信 pickle 还有代码执行风险。无论哪种形式，checkpoint bytes 一致都不自动证明
恢复后的下一 optimizer update 或输出等价，必须做 resume-equivalence test。训练 loop、
autograd、optimizer 与 mixed precision 的完整语义见
[第 02 章](02-training-pytorch-and-numerics.md)。

#### DataLoader worker、RNG 与 Windows/Linux 差异

可复现顺序需要同时绑定 sampler/shuffle generator、base seed、epoch、worker count、
`drop_last`、batch/packing 和每个 worker 内使用的 Python/NumPy/第三方 RNG。Worker init
应从框架提供的 worker seed 派生各 library seed，不能让所有 worker 复制同一随机流。

Windows multiprocessing 通常使用 `spawn`：子进程重新 import 模块，所以入口要受
`if __name__ == "__main__"` 保护，dataset/collate/worker-init 对象要可 pickle，顶层
import 不能产生副作用。Linux 的 `fork` 可能继承内存、RNG、lock 与 file handle；这
看似省启动成本，却可能复制错误状态，尤其不应在初始化 CUDA context 后盲目 fork。
实际 start method、persistent-worker lifecycle、prefetch 和异常传播都要进入测试合同。

### 2.8 Packaging 与 dependency lock

`[通用工程]` 可复现环境至少区分：

```text
project metadata and direct requirements
resolved lock with exact versions/hashes
Python interpreter and ABI
OS / driver / CUDA runtime compatibility
model and tokenizer revisions
environment variables and backend flags
```

Virtual environment 隔离 Python package，不隔离 OS driver、GPU、system DLL、network
或用户 cache。`pip freeze` 记录现有环境，但不自动说明 dependency 来源、platform marker、
构建 artifact 或为何存在；可靠 lock 还应支持 clean install test。

模块 import 不应在顶层偷偷下载模型、启动 network 或执行 GPU probe。把 optional/heavy
dependency 放在明确 boundary，并让 offline validator 在没有它们时仍能检查 schema 和
artifact identity。

## 3. 测试：为 claim 设计证据

### 3.1 测试层次

| Test | 回答的问题 | 例子 |
| --- | --- | --- |
| Unit | 一个纯函数/类是否满足局部 contract？ | canonical JSON、metric 计算 |
| Schema/contract | producer 与 consumer 是否兼容？ | unknown field/version fail closed |
| Property | 一类输入的不变量是否成立？ | coordinate round-trip、idempotency |
| Golden | 固定输入是否产生 exact bytes？ | JSONL、prediction、report |
| Integration | 多组件真实边界能否协作？ | adapter load + scorer |
| Differential | 两实现是否在定义的关系下相等/接近？ | cache on/off、attached/merged |
| Fault injection | crash/timeout/partial write 时语义是否正确？ | WAL unknown outcome |
| Performance | 锁定 workload 下是否满足资源/SLO？ | peak VRAM、TTFT/TPOT |

测试通过只支持测试 contract。Unit test 不能证明生产流量，CPU CI 不能证明 GPU logits，
一个 golden case 不能证明全分布 generalization。

### 3.2 Positive、negative 与 mutation tests

只测合法 input 容易得到“validator 永远返回 true”也通过的假象。Fail-closed contract
至少要构造：unknown field/version、missing required field、wrong digest、duplicate ID、
oversized input、unsafe path、truncated file、semantic contradiction。

Mutation testing 思路是故意修改一个 byte/field/gate，确认 validator 会失败。对于 evidence
record，要分别篡改 source、summary、digest、classification 和 pass flag，验证它们由 raw
facts 重算，而不是互相信任自报。

### 3.3 Hermetic 与 offline test

Hermetic test 固定输入和依赖，不隐式读取网络、用户 home/cache、wall clock 或随机 state。
工程做法：

- caller-supplied temp roots；
- network disabled 或 fake transport；
- frozen clock/RNG；
- explicit environment allowlist；
- 小型 checked-in fixture；
- subprocess 使用当前锁定 interpreter；
- stdout/stderr/exit code 进入断言；
- test 后检查无未预期文件或进程。

Offline test 证明“测试无需网络”，不等于 production offline package 已完整；后者还需
完整 model/tokenizer/compiler bytes、manifest、load 与 behavior replay。

### 3.4 测试选择与独立 oracle

Scorer、builder 和 validator 不应共享所有核心计算，否则同一个 bug 会自洽。可用简单
standard-library oracle 从 raw prediction 重算 metric；candidate optimized path 与 reference
path 分开实现。对浮点比较，事前定义 exact 或 tolerance，以及 tolerance 的 dtype、shape、
reduction-length 理由。

## 4. Git：版本控制不是完整 provenance

### 4.1 Object model

`[原理]` Git 核心对象：

- **blob**：文件 bytes，不含文件名；
- **tree**：文件名/mode 到 blob/tree 的映射；
- **commit**：指向 root tree、parent(s)、author/committer metadata 与 message；
- **tag**：可指向对象的命名/签名发布记录；
- **ref**：branch/tag 等可移动名称，最终指向 object ID；
- **working tree**：当前文件；
- **index/staging area**：下一 commit 的候选 tree。

因此 branch name 不是 immutable identity；commit ID 才绑定历史和 tree。工作区 dirty 时，
HEAD 的 commit 不能代表磁盘上未提交 bytes。`git status`、scoped diff 和 staged diff 必须
在提交前分别检查。

### 4.2 Branch、merge 与 rebase

- branch：一个可移动 ref；
- merge commit：保留两个 parent，记录历史汇合；
- squash merge：产生一个新 commit，原 feature commits 通常不是目标分支祖先；
- rebase：把 patch 重新应用到新 base，commit IDs 改变；
- cherry-pick：复制 patch 形成新 commit，不保留 object identity；
- fast-forward：只移动 ref，不产生 merge commit。

“代码看起来相同”不等于 commit provenance 相同；反过来，commit hash 相同只证明 exact
Git object/history，不证明作者身份，除非另有有效签名和 identity policy。

### 4.3 Git blob hash 与 SHA-256

传统 Git blob object ID 对以下 bytes 求 hash：

```text
"blob " + decimal_size + NUL + file_bytes
```

它不是直接对 file bytes 求同一摘要，因此不能把 Git blob ID 与 raw-file SHA-256 直接
比较。跨系统 package manifest 常保留 raw SHA-256，再独立重算 Git blob ID 绑定 remote
tree。Hash algorithm、canonicalization 和信任的 expected digest 都要明确。

### 4.4 Git LFS

Git LFS 在 Git history 中保存小 pointer，large object 放在 LFS object store。Pointer
通常绑定 object ID 和 size；clone/fetch 成功不自动证明工作区已物化正确 payload。
artifact audit 要区分：

```text
Git blob of the LFS pointer
LFS object oid/size advertised by pointer/server
materialized large-file raw bytes
```

大 tensor 不应因方便而重复 commit；可保存小 summary 或经过必要性审查的 LFS sidecar，
并记录 retention、download 和 validation contract。

### 4.5 PR、CI、review 与 release

一个可靠 publish flow：

```text
scoped branch/diff
→ local validation
→ intentional commit
→ push immutable candidate
→ PR diff/review/conflict inspection
→ required CI
→ merge decision
→ merged commit verification
→ branch cleanup
→ release/promotion remains separate
```

PR merged 证明代码进入目标 branch；它不自动证明 model artifact 被 promoted、GPU run
发生或 production deployed。CI check 必须说明执行了什么环境和 assertion。

## 5. 文件系统、进程与跨平台语义

### 5.1 Path 与链接攻击

用户输入 path 不能只做字符串 prefix 判断：`..`、separator、case-folding、symlink、
hardlink、junction/reparse point 都可能逃出 scope。

`[通用工程]` 安全流程：

1. 从明确允许 root 开始；
2. 拒绝 absolute/UNC/device path（若 contract 不允许）；
3. canonicalize/resolve 已存在 component；
4. 检查 resolved target 仍在 root 内；
5. 必要时以 directory handle/open-at 类机制减少 TOCTOU；
6. 限制 link/reparse/hardlink policy；
7. 写前再验证 revision/identity；
8. 日志脱敏，不输出 secret path/content。

Windows path 大小写、drive、UNC、reserved names 与 Linux 不同；WSL path 不是 native
Windows path 的第二机器证据。

### 5.2 Atomic write

避免直接覆盖 canonical artifact：

```text
write complete bytes to temp file in same target filesystem
→ flush userspace buffer
→ fsync file where required
→ verify size/digest
→ atomic replace/rename
→ fsync parent directory where platform/durability contract requires
```

Atomic visibility 不等于 power-loss durability；网络文件系统也可能有不同语义。多个
文件的 package 不能靠逐个 rename 获得 transaction，通常用 generation directory +
complete manifest/commit marker，让 reader 只接受完整 generation。

### 5.3 Encoding 与 canonical bytes

明确 UTF-8、newline、BOM、Unicode normalization、JSON separators/key order、final
newline。Text 看起来相同但 bytes 可不同；hash、golden test 和 cross-platform artifact
必须对 canonical bytes 定义。不要用 locale default 读写证据文件。

浮点 JSON 还要定义 finite policy、number rendering 和禁止 `NaN/Infinity`；timestamp
使用带 timezone 的标准格式，避免 local time ambiguity。

### 5.4 Subprocess contract

```python
result = run(
    [executable, "--config", str(config_path)],
    cwd=locked_workdir,
    env=explicit_environment,
    timeout=remaining_timeout_seconds,
    capture_output=True,
    text=False,
    check=False,
)
```

要点：

- 参数数组而非拼 shell 字符串，降低 injection/quoting 风险；
- 显式 executable、cwd、env 与 encoding；
- 同时消费 stdout/stderr，防 pipe buffer deadlock；
- timeout 后处理整个 process tree；
- 区分 exit code、signal/termination、timeout 与 unknown external side effect；
- 限制 output bytes，避免日志/内存爆炸；
- 保存 command contract，secret 参数只通过受控 channel，不写日志。

这个简例只适用于 stdout/stderr 已知有界的程序，因为 `capture_output=True` 会在内存中
累计完整输出。不可信或可能大量输出的 child 应使用 `Popen`，并发、有界地 drain 两个
pipe，超过 byte budget 就终止整个 process tree；绝对 deadline 要先换算成每次调用的
remaining timeout。

Exit code `0` 只表示程序按其定义成功退出；若需要 evidence，还要解析并重算 output。

### 5.5 Windows、native Linux 与 WSL

跨平台验证要明确是在验证：

- source/stdlib compatibility；
- Python dependency resolution；
- filesystem/path/locking；
- CUDA/driver/model behavior；
- operationally distinct machine identity。

同一 Windows controller 上的 WSL 可以提供 Linux userspace compatibility evidence，
但共享 hardware/controller，不能替代 cross-machine portability。跨平台 test skip 必须
有明确 reason，不能把未运行写成通过。

## 6. CUDA：理解异步 GPU 的最小模型

### 6.1 Driver、runtime、toolkit 与 framework

面试中常见混淆：

- NVIDIA driver：操作系统侧控制 GPU，并提供 driver API；
- CUDA runtime/toolkit：runtime、compiler、headers/libraries 等开发层；
- framework build：PyTorch 等通常绑定特定 CUDA runtime/library 组合；
- device capability：GPU 支持的 instruction、dtype 和 resource limits；
- kernel library/backend：cuBLAS、attention kernel、custom extension 等。

系统安装了某个 `nvcc` 不等于当前 PyTorch wheel 使用它；driver 可见 GPU 也不等于
目标 dtype/kernel 可运行。证据应记录 framework build、driver、device、effective
backend，并执行真实 tensor/kernel smoke test。

### 6.2 Host、device、kernel、grid 与 warp

`[原理]` CPU host enqueue kernel 到 GPU stream。Kernel 有许多 threads，按 block 和
grid 组织；hardware 以 warp 为调度单位执行 threads。理解重点：

- 同 warp 分支不同会产生 divergence；
- block 内 threads 可通过 shared memory 和 barrier 协作；
- block 间通常不能在同一 kernel 中做普通全局 barrier；
- register/shared-memory 使用过多会降低同时驻留 warps/blocks；
- memory access coalescing 和 layout 会决定有效带宽；
- occupancy 高不保证性能高，仍可能 memory、dependency 或 instruction-bound。

面试无需背某张 GPU 的所有数字，但要知道具体 warp size、shared-memory limit、Tensor
Core dtype 和 occupancy 必须查询目标 architecture。

### 6.3 Memory hierarchy

从线程近端到远端可概括为：register → shared memory/L1 → L2 → device HBM/GDDR；
host-device transfer 经过 PCIe/NVLink 等。越近容量通常越小、延迟越低。

优化目标是提高 data reuse、coalesced access 和 arithmetic intensity，减少无效 transfer
与 materialization。Pinned host memory 可支持更高效的 async transfer，但它占用不可
分页物理内存，不能无限使用。Unified/managed memory 简化地址空间，不消除迁移成本。

### 6.4 Stream、event 与 synchronization

CUDA kernel launch 通常对 host 异步。以下计时是错误的：

```python
start = time.perf_counter()
y = gpu_op(x)
elapsed = time.perf_counter() - start  # 可能只测到 enqueue
```

正确 benchmark 需要 warm-up，并用 device events 或在计时边界 synchronization：

```python
warm_up()
synchronize_device()
start = device_event(enable_timing=True)
end = device_event(enable_timing=True)
start.record(stream=measured_stream)
run_gpu_work(stream=measured_stream)
end.record(stream=measured_stream)
end.synchronize()
elapsed_ms = start.elapsed_time(end)
```

Start、被测 work 和 end 必须处于同一 measured stream，或通过 event 显式建立跨 stream
依赖；`end.synchronize()` 只等待该 event 之前且与其有依赖关系的工作。跨多个互不依赖
streams 时，应分别计时或先建立正确 join，否则可能低估。

正式代码不要到处同步；`.item()`、CPU print、某些 copy 会隐式同步并破坏 overlap。
异步 kernel error 也可能在后续 synchronization 才显现，因此 stack trace 的 Python
行不一定是首个错误 kernel。

### 6.5 Allocated、reserved 与 peak memory

Caching allocator 常区分：

- allocated：live tensors 当前占用；
- reserved：allocator 从 device 获得并保留的 blocks，包含 free cached blocks；
- peak allocated/reserved：测量窗口峰值；
- external/non-framework allocations：可能不在 framework counter 中。

`empty_cache` 只能释放未被 live tensor 引用的 cached blocks，不能释放仍有 reference 的
tensor，也不减少下一次同 workload 的真实 live peak。诊断 memory growth：

1. 在正确同步点 reset/read peak；
2. 记录 batch/sequence/phase；
3. 检查 Python containers、hooks、closures 是否保留 graph/tensor；
4. 比较 allocated 与 reserved；
5. 使用 memory snapshot/profiler；
6. 区分 leak、expected cache、fragmentation 与 workspace peak。

### 6.6 Kernel performance 与 correctness

性能优化顺序：

```text
profile end-to-end
→ 确认热点和目标 shape/dtype
→ 建独立 reference
→ correctness matrix
→ microbenchmark
→ integration benchmark
→ task/safety regression
```

常见手段：fusion、tiling、shared-memory reuse、vectorized/coalesced load、减少 launch、
避免中间 tensor、选择合适 precision。每项都可能改变 operation order 和 rounding，必须
事前定义 tolerance 和 task-level gate。Microbenchmark 快不代表端到端快，需用
Amdahl's Law 和真实 shape distribution 判断。

## 7. 一套可复现命令的合同

命令不是只把 flags 粘贴到 README。它应绑定：

```text
executable/interpreter identity
working directory
argument array
explicit environment
input paths and digests
network/offline policy
stdout/stderr/exit code
start/end time and timeout
hardware/software inventory
expected outputs and overwrite policy
```

PowerShell、bash、CMD 的 quoting/environment 语义不同。跨 shell 不要把动态字符串二次
解释；文件操作使用 native API 和 literal path；secret 不放 command line。运行结果应
由独立 validator 读取 raw outputs 重算，而不是只相信命令打印 `passed=true`。

## 8. 常见失败与排障

| 症状 | 常见根因 | 第一证据 |
| --- | --- | --- |
| 本机能跑，clean env 失败 | undeclared dependency/cache/path | fresh venv/root、import/network audit |
| Hash 每次不同 | timestamp/order/newline/float serialization | raw byte diff、canonical writer |
| Windows pass、Linux fail | path/case/newline/locking/optional dep | platform-specific minimal test |
| Subprocess 卡住 | pipe 未消费、child tree、deadlock | process tree、stdout/stderr bytes |
| 测得 GPU op 极快 | 未同步，只测 enqueue | CUDA event/sync benchmark |
| GPU memory 不降 | live reference 或 allocator cache | allocated/reserved、reference graph |
| 同 seed 仍漂移 | RNG 不完整、kernel/dtype/data order | identity ledger、fresh repeats |
| CI 绿但模型坏 | CI 没执行 GPU/model path | check scope 与 model evidence |
| Commit 对但文件脏 | working tree 未提交 | `git status`、blob/working-tree digest |
| LFS pointer 对但 tensor 缺失 | 只验证 pointer | LFS oid/size + materialized payload |
| Retry 产生两次动作 | timeout 被当失败 | WAL/idempotency/reconciliation |
| Profile 很慢 | profiler overhead | 独立 benchmark，不用 trace wall time |

## 9. 高频面试问题与分层答案

### Q1：怎样让一个 Python 数据/评测 pipeline 可复现？

**30 秒答案**

把输入、schema、transform code/config、环境和输出都做 immutable identity；从同一 raw
bytes 求 digest 并 parse，使用 canonical writer、caller-supplied roots、显式 UTF-8、
offline dependency，最后由独立 validator 从 raw artifacts 重算结果。

**2 分钟展开**

补充 source/license、split manifest、RNG/data order、atomic generation、negative tests、
nonzero exit、stdout/stderr；区分 clean-location same-env replay 与跨机器 portability。

**深挖方向**

- Python hash/random seed 与 data-loader workers；
- TOCTOU 和 symlink/reparse；
- float/canonical JSON；
- partial artifact 和 overwrite policy。

### Q2：Git commit hash 能证明什么？

**30 秒答案**

它内容寻址一个 commit object，间接绑定 root tree、parents 和 metadata；能识别 exact
Git history/tree。它不证明 dirty working tree、LFS materialized bytes、作者真实身份、
程序执行或 production deployment。

**2 分钟展开**

说明 blob/tree/commit/ref、rebase/squash 改 ID、branch name 可移动；再区分 Git blob
object ID、raw SHA-256、LFS pointer/object、签名与 hosted origin binding。

**深挖方向**

- signed commit 的 trust policy；
- shallow clone/remote ref；
- source closure 和 submodule/LFS；
- PR checks 到底执行了什么。

### Q3：为什么 CUDA benchmark 要同步？

**30 秒答案**

GPU launch 对 CPU 通常异步，CPU wall clock 可能只测 enqueue。要预热，在设备 event 或
显式同步边界测真实执行；同时固定 shape/dtype/backend，报告分布而非一次时间。

**2 分钟展开**

说明 stream dependency、隐式同步、compile/autotune warm-up、allocator/cache、event
计时；profile run 和 benchmark 分开，最终看端到端 critical path。

**深挖方向**

- 多 stream timing；
- kernel error 延迟上报；
- CPU-GPU transfer；
- TF32/AMP 对 correctness/performance 的影响。

### Q4：如何区分 GPU memory leak 和 allocator cache？

**30 秒答案**

看 live allocated 与 reserved：allocated 随 iteration 增长通常有 tensor/graph reference；
reserved 高但 allocated 稳定可能是 caching/fragmentation。固定 batch/同步点，抓 memory
snapshot 和 reference 生命周期；`empty_cache` 不是 leak 修复。

**2 分钟展开**

分解 parameters、optimizer、activations、workspace、KV、communication；检查 logging
list、hook、closure、loss tensor 和 dynamic shape。释放对象、移除 hook 后复测完整
fresh lifecycle，并同时看 external allocations。

**深挖方向**

- allocated/reserved/peak；
- fragmentation 与 bin size；
- asynchronous deallocation；
- distributed buffers 和 CUDA graph pool。

### Q5：Thread、process、async 怎样选？

**30 秒答案**

大量可等待 I/O 用 async，阻塞 I/O 或会释放 interpreter lock 的 native work 可用
thread，CPU-bound Python 用 process；选择还要考虑状态共享、serialization、cancel、
failure isolation 和下游限流。

**2 分钟展开**

强调 GPU op 由 host enqueue，不能仅凭 Python CPU 模型判断；bounded pool/queue、deadline
和 backpressure 比“开更多 worker”重要。Process crash、async cancel 与 tool side effect
都需 durable state，不能假装操作被撤销。

**深挖方向**

- GIL 与 native extension；
- event loop blocking；
- process start method；
- context propagation 与 structured concurrency。

## 10. 本项目映射与证据边界

### `[本仓库已实现]`

- Python source 具有 strict schema/semantic validators、canonical artifacts、negative
  fixtures、Ruff、mypy、`py_compile` 和 CPython 3.11/3.12/3.13 offline gate；
- 冻结 data/evidence 使用 SHA-256 绑定；selected FP32 package 另有 Git/Hugging Face
  revision、Git blob 与 Git LFS pointer metadata 的 hosted-origin binding；
- clean-location replay 使用 caller-supplied fresh roots、offline execution、fresh model
  load、ordered generation 与 zero retry；
- Windows native GPU model runs 与 WSL standard-library compatibility checks 被明确区分；
- BF16/FP32、attached/merged、GPU allocated/release memory、elapsed 和 raw logits 均有
  冻结证据。

### `[本仓库待实施]`

- Tiny Transformer/CUDA operator profiling 和 correctness-gated Triton kernel；
- distributed/multi-GPU process、collective、checkpoint 与 recovery；
- production packaging/signing/SBOM/transparency log；
- Serving/Kubernetes 下的 GPU lifecycle、autoscaling 和 incident tests。

本项目可以支持“做过严格 Python/evidence pipeline、Git/LFS artifact binding 和单 GPU
数值诊断”的说法；不能支持“完成自定义 CUDA kernel、大规模 Linux GPU cluster 或
production supply chain”。

## 11. 自测与实践

### 闭卷自测

1. Python 名字、object 与浅/深拷贝的区别是什么？
2. 为什么 generator pipeline 容易发生 one-pass bug？
3. Static typing、JSON Schema 与 semantic validator 分别检查什么？
4. Unit、property、golden、differential、fault-injection test 的 oracle 如何选？
5. Git blob、tree、commit、ref、working tree 和 index 是什么关系？
6. Squash/rebase 为什么改变 commit identity？
7. Git LFS pointer、LFS object 与 materialized file 怎样绑定？
8. Atomic visibility 与 crash/power-loss durability 有什么不同？
9. CUDA kernel launch 为什么让 CPU wall-clock 计时失真？
10. Allocated 与 reserved GPU memory 分别是什么？
11. WSL 测试能证明什么，为什么不等于独立机器？
12. `exit_code=0`、test pass、CI green、artifact promoted 各自是什么 claim？

### 最小实践

1. 写 canonical JSONL builder：UTF-8、stable ordering、duplicate rejection、SHA-256；
2. 对 builder 做 mutation tests：改一 byte、截断、未知字段、重复 ID、超限；
3. 实现 atomic generation directory + complete manifest，并注入 partial write/crash；
4. 画一个 Git commit/tree/blob/LFS evidence graph，手算一个 Git blob object digest；
5. 写安全 subprocess wrapper，覆盖 timeout、stderr flood、nonzero exit 和 child process；
6. 对 CPU、H2D、GPU kernel 分别正确计时，比较同步与未同步结果；
7. 故意把带 graph tensor 存入 list，复现 allocated memory growth 后修复；
8. 在 fresh virtual environment 运行 offline package/import test，记录所有隐式依赖；
9. 为一个 mock side-effect tool 实现 WAL、idempotency 与 unknown-outcome recovery；
10. 用两分钟讲清：为什么同一 commit、同一 hash、同机 replay 与 production-ready 是
    四个不同层级。
