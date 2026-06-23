# AGENTS.md — AI PC 控制系统开发指令

> 本文件是 AI 助手在本项目中的行为准则。AI 进入项目时**必须首先完整阅读本文件**，并严格遵守其中的工作流、架构约束和开发规范。
>
> 基于 Harness Engineering 方法论：用结构化文档驱动 AI，实现从需求到代码的精确映射。

---

## 0. 黄金法则

1. **任何代码变更前，先读对应的 PRD 和 Spec**——没有 PRD 的功能不做
2. **每个功能必须有 Acceptance Criteria**——没有验收标准的功能不算完成
3. **Non-Goals 是红线**——明确写了"不做"的事，绝不顺手做了
4. **一次只做一个任务**——从 `docs/tasks/active/` 取最高优先级，完成、测试、提交后再取下一个
5. **出错时更新文档，而非只改代码**——文档是免疫系统，每次错误都应增强它

---

## 1. 项目概况

- **项目名**：AI PC 控制系统（本地 GPU 驱动）
- **目标**：完全运行在本地 RTX 5070 Ti 上的 AI 桌面自动化系统
- **核心技术约束**：16GB 显存、零网络依赖、INT4 量化
- **PRD 文档**：`docs/prd/001-local-gpu-pc-control.md`
- **架构总览**：`docs/architecture.md`

---

## 2. Harness Engineering 七步工作流

AI 必须按以下七步闭环工作，**不得跳步**：

```
PRD → Spec → Tasks → Implementation → Validation → Review → Iterate
```

### Step 1: PRD（需求定义）
- **AI 职责**：读取 `docs/prd/` 下的 PRD 文件，理解 Goals / Non-Goals / User Stories / Acceptance Criteria
- **输入**：用户需求描述
- **输出**：结构化 PRD 文件（含 5 大模块）
- **规则**：PRD 只写"做什么"，不写"怎么做"

### Step 2: Spec（技术设计）
- **AI 职责**：基于 PRD 的 Goals，设计技术方案
- **输入**：PRD 文件
- **输出**：`docs/spec/` 下的技术设计文档
- **规则**：Spec 必须包含模块接口定义、数据流、技术选型理由

### Step 3: Tasks（任务拆解）
- **AI 职责**：将 Spec 拆成原子任务
- **输入**：Spec 文件
- **输出**：`docs/tasks/active/` 下的任务文件，每个任务含：标题、描述、依赖、验收标准
- **规则**：每个任务应可独立完成、独立测试，预计耗时 ≤ 1 天

### Step 4: Implementation（实现）
- **AI 职责**：从 `docs/tasks/active/` 取最高优先级任务，实现代码
- **规则**：
  - 每次只做一个任务
  - 实现前先读取相关 Spec 和已有代码
  - 实现后运行测试确认通过
  - 提交后更新任务状态（移到 `docs/tasks/completed/`）

### Step 5: Validation（验证）
- **AI 职责**：读取 PRD 的 Acceptance Criteria，逐条对照实现结果
- **规则**：对照的是**原始需求**，不是自己的代码。每条 AC 返回 PASS/FAIL

### Step 6: Review（评审）
- **AI 职责**：检查代码质量、安全合规、文档完整性
- **检查清单**：
  - [ ] 代码是否实现了 PRD 定义的所有 Goals
  - [ ] 是否触犯了任何 Non-Goal
  - [ ] 是否覆盖了所有 Acceptance Criteria
  - [ ] 是否有安全风险（见第 5 节）
  - [ ] 是否更新了相关文档

### Step 7: Iterate（迭代）
- **AI 职责**：收集失败案例，更新文档防止再犯
- **规则**：每次错误都应在 AGENTS.md 或相关 Spec 中增加一条规则

---

## 3. 工程目录结构

```
ai-pc-control/
├── AGENTS.md                     ← 本文件（AI 行为准则）
├── docs/
│   ├── prd/                      ← 需求定义（源头）
│   ├── spec/                     ← 技术设计
│   └── tasks/
│       ├── active/               ← 待办任务
│       └── completed/            ← 已完成任务
├── src/
│   ├── core/                     ← OODA 循环主逻辑
│   ├── perception/               ← 视觉感知层
│   ├── inference/                ← 本地 GPU 推理层
│   ├── execution/                ← 执行层
│   ├── safety/                   ← 安全控制层
│   └── api/                      ← 对外接口
├── models/                       ← 模型权重（gitignore）
├── tests/
└── scripts/
```

---

## 4. 本地 GPU 开发约束

### 4.1 显存预算（硬约束）

| 模块 | 预算 | 说明 |
|------|------|------|
| Qwen2-VL-7B INT4 | ≤ 5GB | 主决策模型 |
| 视觉编码器 ViT | ≤ 3GB | 与主模型共享 |
| YOLOv8m | ≤ 2GB | UI 元素检测 |
| PaddleOCR | ≤ 1GB | 中文 OCR |
| KV Cache + 缓冲 | ≤ 3GB | 推理缓存 |
| **总峰值** | **≤ 15GB** | 留 1GB 余量 |

**规则**：任何新增模型必须先评估显存占用，超出预算需架构师批准。

### 4.2 本地化红线

- **禁止**：调用任何云端 AI API（Claude / GPT-4o / Gemini）
- **禁止**：上传截图或用户数据到外部服务
- **要求**：断网环境下全部功能正常
- **验证**：用 Wireshark 确认无出站网络请求

### 4.3 量化规则

- 默认使用 INT4（NF4）量化
- 量化后必须跑基准测试，精度损失 > 5% 需评估是否回退到 INT8
- 量化配置统一放在 `src/inference/quantization.py`

---

## 5. 安全开发规范

### 5.1 五层安全防护（必须实现）

1. **沙箱环境**：Docker 容器隔离运行
2. **风险评级**：每个动作执行前评估风险等级（low/medium/high/forbidden）
3. **人工确认**：high 级别操作必须弹窗确认，30 秒未确认自动拒绝
4. **审计日志**：所有动作记录截图+动作+时间，追加写入不可篡改
5. **预算熔断**：单任务最大 50 步 / 10 分钟 / $0 成本（本地）

### 5.2 提示注入防护

- 屏幕上识别到的文字标记为"不可信数据"
- 系统指令 > 用户指令 > 屏幕内容，低层级不能覆盖高层级
- 含"上传文件""修改密码"等关键词的动作一律拦截

### 5.3 禁止操作清单

AI **不得**实现以下功能：
- 无人工确认的文件删除
- 无人工确认的邮件发送
- 无人工确认的网络支付
- 访问银行/支付网站
- 修改系统密码
- 执行任意 shell 命令（除非在沙箱内且经过审批）

---

## 6. 代码规范

### 6.1 语言与风格

- **语言**：Python 3.11+
- **格式化**：`ruff format`（一行不超过 100 字符）
- **类型标注**：所有公开函数必须有类型标注
- **文档字符串**：所有模块、类、公开函数必须有 docstring

### 6.2 命名约定

- 文件名：`snake_case.py`
- 类名：`PascalCase`
- 函数/变量：`snake_case`
- 常量：`UPPER_SNAKE_CASE`
- 私有成员：`_leading_underscore`

### 6.3 测试要求

- 每个模块必须有对应的 `test_*.py`
- 测试覆盖率 ≥ 70%
- 安全模块覆盖率 ≥ 90%
- 端到端测试覆盖 PRD 中所有 AC

### 6.4 Git 工作流

- 分支命名：`feat/T-XX-简述` / `fix/T-XX-简述`
- 提交信息：`[T-XX] 简述变更`（必须关联任务编号）
- 一个任务一个分支，一个分支一个 PR
- PR 必须通过所有测试才能合并

---

## 7. 文档维护规则

### 7.1 文档是活的

- 每次代码变更必须同步更新相关文档
- 文档过期等于文档不存在
- 发现文档与代码不一致时，**立即更新文档**

### 7.2 错误驱动更新

当 AI 犯错时：
1. 修复代码
2. 在本文件（AGENTS.md）或相关 Spec 中增加一条规则，防止再犯
3. 如果是普遍性问题，更新 PRD 的 Non-Goals 或 Acceptance Criteria

### 7.3 渐进式披露

- 避免巨型单一文档
- 每个文档聚焦一个主题
- 用目录表（如本文件）索引深层文档
- AI 按需读取，不一次性加载所有文档

---

## 8. AI 行为检查清单

每次开始工作前，AI 必须自问：

- [ ] 我读过 AGENTS.md 了吗？
- [ ] 我知道当前任务的 PRD 在哪吗？
- [ ] 我知道这个任务的 Non-Goals 是什么吗？
- [ ] 我知道验收标准是什么吗？
- [ ] 我的实现方案是否违反了显存预算？
- [ ] 我的代码是否触犯了安全红线？
- [ ] 我是否一次只做一个任务？

每次完成后，AI 必须自问：

- [ ] 我实现了 PRD 定义的所有 Goals 吗？
- [ ] 我是否触碰了任何 Non-Goal？
- [ ] 所有 Acceptance Criteria 都 PASS 了吗？
- [ ] 我更新了相关文档吗？
- [ ] 我运行了测试吗？
- [ ] 我把任务从 active/ 移到 completed/ 了吗？

---

## 9. 常见陷阱与对策

| 陷阱 | 对策 |
|------|------|
| AI 跳过 PRD 直接写代码 | 强制要求：无 PRD 编号的任务不受理 |
| AI 一次做多个任务 | 强制要求：从 active/ 取一个，完成后再取下一个 |
| AI 忽略 Non-Goals | 在 Validation 阶段逐条检查 Non-Goals |
| AI 修改测试以通过验证 | 禁止修改测试，测试是 PRD 的延伸 |
| AI 调用云端 API | 代码审查检查 import 语句，禁止 anthropic/openai 等 |
| AI 显存溢出 | 每次加载模型前调用 gpu_monitor 检查 |
| AI 文档不更新 | PR 合并前检查文档是否同步 |

---

## 10. 快速启动指令

当 AI 被要求"开始开发"时，按以下顺序执行：

```
1. 读取本文件（AGENTS.md）
2. 读取 docs/prd/ 下的 PRD 文件
3. 读取 docs/tasks/active/ 下的任务列表
4. 选择最高优先级（编号最小）的任务
5. 读取该任务对应的 Spec（如有）
6. 读取相关已有代码
7. 实现代码
8. 运行测试
9. 更新文档
10. 将任务移到 completed/
11. 提交代码
12. 取下一个任务
```

---

## 11. 长程自循环协议

> 本节解决"AI 怎么不停做下去"。核心机制：**进度持久化 + 自验证 + 自复盘 + 中断恢复**。
> 完整理论见 [docs/theory/long-run-protocol.md](docs/theory/long-run-protocol.md)。

### 11.1 三层结构

```
外层 Driver（调度）→ 启动会话 → 中层 Session（干活）→ 读写 → 底层 State（记忆）
     ↑                                              │
     └────── 读 progress.md 决定是否再启动 ←─────────┘
```

- **Driver**：读 progress.md，有任务且无阻塞就启动新会话，否则退出。不思考，只调度。
- **Session**：按启动序列读文件恢复上下文 → 取任务 → 做 → 验证 → 复盘 → 写进度 → 取下一个，直到会话结束。
- **State**：`progress.md` / `lessons.md` / `tasks/active/` / `tasks/completed/`，会话间唯一可靠的信息传递通道。

### 11.2 单次会话启动序列（不得跳过）

```
1. pwd 确认工作目录
2. 读 AGENTS.md（本文件）
3. 读 docs/progress.md —— 做到哪了
4. 读 docs/lessons.md —— 别重犯什么错
5. git log --oneline -5 —— 最近代码变了什么
6. 读 docs/tasks/active/ —— 下一个任务
7. smoke test —— 环境还正常吗
8. 然后才开始做新任务
```

### 11.3 状态文件

| 文件 | 用途 | 写入时机 |
|------|------|----------|
| `docs/progress.md` | 进度日志（会话间传递） | 开始任务/完成任务/会话结束 |
| `docs/lessons.md` | 失败复盘积累 | 每次犯错后 |

**progress.md 记录格式**：`START T-XX` / `DONE T-XX` / `FAIL T-XX` / `SESSION END, next: T-XX` / `BLOCKED at T-XX`

### 11.4 自验证协议

AI 完成任务后**不得自己说了算**，必须：
1. 运行该任务的验收测试
2. 对照 PRD 的 Acceptance Criteria 检查
3. 只有全部 PASS 才能标记完成
4. 任何 FAIL 必须修复（最多重试 3 次）或记录到 lessons.md

**验证基准来自 PRD，不是来自 AI 自己写的代码。**

### 11.5 自复盘协议

当任务失败或 AI 犯错时：
1. 记录现象到 `docs/lessons.md`
2. 归因分析（需求不清/技术错误/规则缺失）
3. 更新文档（AGENTS.md 增加规则 / Spec 增加陷阱 / PRD 更新 Non-Goals）
4. 验证新规则能防止同类错误

### 11.6 四个停止条件

| 条件 | 动作 |
|------|------|
| active/ 任务清空 | 写 ALL DONE，退出 |
| 连续 2 个任务失败 | 写 BLOCKED，退出，等人工介入 |
| 会话 turn 接近上限 | 写 SESSION END + next，退出 |
| 需要人决策 | 写 WAITING DECISION，退出 |

**禁止**：会话还有余力就停下。只要 active/ 有任务且无阻塞，必须继续。

### 11.7 中断恢复

上一次会话异常中断（没写 SESSION END）时：
1. 读 progress.md 最后一条
2. 检查该任务是否真的完成（代码存在？测试通过？）
3. 未完成 → 继续；已完成 → 补标记，取下一个

### 11.8 启动长程工作

> "读 AGENTS.md 第 11 节，读 docs/progress.md 了解进度，从下一个待办任务开始，按自循环协议持续工作，直到 active/ 清空或遇到阻塞。"

---

## 12. 多代理协作协议

> 本节解决"复杂任务怎么分工"。当任务超出单代理能力时，主代理分解任务并调度子代理并行执行。
> 完整理论见 [docs/theory/multi-agent-collaboration.md](docs/theory/multi-agent-collaboration.md)。

### 12.1 何时启用多代理

| 场景 | 是否启用 |
|------|---------|
| 任务可拆成 ≥3 个无依赖子任务 | ✅ 启用 |
| 子任务需要不同类型能力（探索/推理/编码） | ✅ 启用 |
| 单任务，串行依赖 | ❌ 单代理即可 |
| 子任务间需要频繁实时通信 | ❌ 不适合多代理 |

### 12.2 主代理的职责

主代理（Master）**不写业务代码**，只做四件事：

1. **分解**：把复杂任务拆成子任务，生成 DAG 依赖图
2. **分配**：为每个子任务选合适类型的子代理，定义职责边界
3. **整合**：收集子代理产出，对照 PRD 的 AC 验证，拼接最终结果
4. **仲裁**：处理子代理间的冲突

### 12.3 子代理的角色定义

每个子代理必须明确三个要素：

| 要素 | 含义 | 示例 |
|------|------|------|
| **职责** | 要完成什么 | "实现 YOLO UI 元素检测" |
| **能力边界** | 不能做什么（Non-Goals） | "不负责 OCR、不改 SoM 模块" |
| **上下文范围** | 能读哪些文件、能改哪些代码 | "只能修改 src/perception/yolo_detector.py" |

### 12.4 子代理类型选择

| 子任务特点 | 子代理类型 | 说明 |
|-----------|-----------|------|
| 需要深度推理（架构设计） | reasoning | 推理型，慢但准 |
| 高频简单操作 | lite | 轻量型，快 |
| 需要读取大量代码理解 | Explore | 只读，不能写 |
| 需要写文件、跑命令 | general-purpose | 全能力 |

### 12.5 通信规则

**子代理之间不直接通信**。所有跨子代理的信息流经由主代理中转。

三种通信模式：
- **共享黑板**：所有子代理读写 `shared_context.json`（适合独立子任务）
- **消息传递**：主代理把上游产出传给下游（适合有依赖的任务）
- **任务队列**：主代理维护队列，子代理取任务交结果（适合并行同质任务）

### 12.6 文件领地（防资源冲突）

每个子代理只能修改其职责范围内的文件。Spec 阶段锁定文件领地：

```
子代理 A（感知层）→ src/perception/*
子代理 B（推理层）→ src/inference/*
子代理 C（安全层）→ src/safety/*
```

跨领地修改必须经主代理批准。

### 12.7 冲突处理五策略

1. **预防为主**：Spec 阶段锁定接口契约（数据格式、函数签名）
2. **主代理仲裁**：子代理产出矛盾时，主代理读 PRD 裁决哪个符合需求
3. **依赖排序**：严格按 DAG 拓扑排序，上游完成才启动下游
4. **文件锁**：子代理获取文件锁后才能写，超出范围被拒绝
5. **升级机制**：冲突无法自动解决时，记录详情，升级人工介入

### 12.8 多代理启动指令

> "读 AGENTS.md 第 12 节。当前任务是 [复杂任务描述]。请按多代理协议：先分解为子任务并生成 DAG，为每个子任务选子代理类型并定义边界，然后并行调度无依赖的子任务，整合结果后对照 PRD 的 AC 验证。"

---

## 13. 环境与下载规范

> 本节是硬性约束，违反任何一条都视为环境配置失败。

### 13.1 虚拟环境统一用 uv

- **唯一允许**的虚拟环境与依赖管理工具是 `uv`
- **禁止**使用 conda、cuda 环境方案、venv、virtualenv、pip 直接安装
- 所有包安装命令一律用 `uv pip install` 或 `uv sync`
- 创建环境用 `uv venv`，不用 `python -m venv`

```bash
# 正确：用 uv
uv venv
uv pip install torch --index-url https://download.pytorch.org/whl/cu128
uv sync

# 禁止：用 conda / pip / venv
# conda create ...           ← 禁止
# python -m venv .venv       ← 禁止
# pip install xxx            ← 禁止
```

> **为什么**：uv 比 pip 快 10-100 倍，依赖解析更准确，且统一工具链避免 conda/pip 混用导致的依赖冲突。conda 与 CUDA 的环境管理方式与本项目冲突，一律不用。

### 13.2 下载操作必须走本机代理

- 所有网络下载（模型权重、pip 包、git clone 等）**必须**读取并应用本机代理配置
- AI 在执行任何下载前，必须先读取 `HTTP_PROXY` 和 `HTTPS_PROXY` 环境变量
- **禁止**跳过代理、使用直连、或自行设置其他代理

```bash
# 下载前的强制检查步骤
echo $HTTP_PROXY
echo $HTTPS_PROXY

# 如果环境变量为空，必须暂停并询问用户代理地址，不得自行直连下载
```

- 若 `HTTP_PROXY` / `HTTPS_PROXY` 为空 → **暂停下载，询问用户**，不得自行直连
- 下载命令必须继承代理环境变量，例如：

```bash
# pip/uv 下载（自动继承环境变量）
uv pip install package-name

# huggingface 下载（需要显式设置）
export HF_ENDPOINT=https://hf-mirror.com  # 如使用镜像
huggingface-cli download Qwen/Qwen2-VL-7B-Instruct --local-dir models/qwen2-vl-7b

# git clone（需要显式设置）
git -c http.proxy=$HTTP_PROXY clone https://github.com/xxx/xxx.git
```

### 13.3 下载进度必须实时 UI 反馈

- 执行任何下载任务时，**必须**提供实时进度信息展示
- 禁止静默下载、后台下载、或只输出最终结果

**必须展示的四项信息**：

| 信息 | 说明 |
|------|------|
| 当前下载速度 | 如 `12.3 MB/s` |
| 已下载 / 总大小 | 如 `3.2 GB / 15.0 GB` |
| 进度百分比 | 如 `21.3%` |
| 预计剩余时间 | 如 `ETA: 16m 23s` |

**实现方式**：

```python
# 下载脚本必须包含进度回调
from tqdm import tqdm

def download_with_progress(url, filepath):
    """带实时进度展示的下载函数。"""
    # 必须显示：速度、已下载/总量、百分比、ETA
    # tqdm 自动提供这四项，禁止用静默下载
    pass
```

```bash
# 命令行下载必须显示进度
# 正确：huggingface-cli 自带进度条
huggingface-cli download Qwen/Qwen2-VL-7B-Instruct --local-dir models/qwen2-vl-7b

# 正确：wget 显示进度
wget --progress=bar:force https://example.com/file.bin

# 禁止：静默下载
# wget -q https://...        ← 禁止（-q 静默）
# curl -s https://...        ← 禁止（-s 静默）
```

> **为什么**：模型权重 15GB，下载要 30-60 分钟。没有进度反馈，人工无法判断下载是否正常运行，出现卡死/断流时无法及时发现。实时进度让人工能随时判断是否需要中断重试。

### 13.4 环境准备检查点

AI 在执行任何涉及下载或环境配置的任务前，必须先确认：

- [ ] 当前使用的是 `uv` 而非 conda/pip/venv？
- [ ] `HTTP_PROXY` / `HTTPS_PROXY` 环境变量已读取且非空？
- [ ] 下载命令会显示实时进度（速度/大小/百分比/ETA）？

任一项不满足 → 暂停，不得继续执行。

---

*本文件随项目演进持续更新。每次 AI 犯错，都应在此增加一条规则。*
