---
title: 多代理协作实操指南
type: theory
created: 2026-06-23
tags: [harness-engineering, multi-agent, practical-guide]
---

# 多代理协作实操指南

> 本文是 AGENTS.md §12 和 multi-agent-collaboration.md 的执行补充。
> 理论回答"为什么"，本文回答"怎么做"。

---

## 1. 主代理工作台（Master Agent Checklist）

当 AI 被要求启用多代理模式时，按以下 6 步执行，不得跳步：

```
Step 1: 读全局文档
Step 2: 分解任务 → 生成子任务表
Step 3: 按 DAG 确定执行顺序
Step 4: 并行调度无依赖的子代理
Step 5: 收集产出 → 验证 → 集成
Step 6: 归档交付物 → 更新进度
```

### Step 1：读全局文档

主代理启动后先读：
- `AGENTS.md`（含 §12 多代理协议）
- `docs/prd/001-local-gpu-pc-control.md`（AC 是验证基准）
- `docs/architecture.md`（模块边界是任务分解的依据）
- 相关的 Spec 文档

### Step 2：分解任务 → 生成子任务表

用以下模板填，每个子任务一张表：

```
子任务 ID: SUB-XX
职责:      [一句话说清楚要做什么]
检验标准:  [完成后怎么证明做对了，引用 PRD 的 AC]
能力类型:  [reasoning / lite / Explore / general-purpose]
依赖:      [SUB-XX，无依赖写 None]
文件领地:  [只能改哪些文件]
输入:      [需要的上下文文件路径]
输出:      [交付物文件路径]
```

### Step 3：按 DAG 确定执行顺序

画出依赖关系图，无依赖的子任务可以并行启动。

### Step 4：并行调度

用 `Agent` 工具生成子代理。每个子代理的 prompt 必须包含：

- **职责描述**（从子任务表拷贝）
- **禁止做的事**（Non-Goals）
- **允许读的文件清单**（精确到路径）
- **允许改的文件清单**（精确到路径）
- **验收标准**（从子任务表拷贝）
- **要求**：完成后返回交付物路径 + 自查结果

### Step 5：收集 → 验证 → 集成

所有子代理完成后，主代理：
1. 收齐所有交付物
2. 对照 PRD 的 AC 逐条验证
3. 跑集成测试
4. 任一失败 → 定位冲突 → 重派或升级

### Step 6：归档

- 在 `docs/progress.md` 写 "DONE multi-agent batch: SUB-01~SUB-NN"
- 更新相关文档
- commit + push

---

## 2. 本项目实战示例：分解 T-04（VLM Server 实现）

T-04 的原始描述："封装 UI-TARS 调用，提供统一的 infer() 接口"。
如果这个任务特别复杂，用多代理分解：

### 分解结果

```
T-04: VLM Server 实现
├── SUB-01: ActionSchema 适配层      [无依赖, general-purpose]
├── SUB-02: ContextManager           [无依赖, general-purpose]
├── SUB-03: ModelManager + GPUMonitor[无依赖, general-purpose]
├── SUB-04: VLMServer 主流程          [依赖 SUB-01/02/03, reasoning]
└── SUB-05: 集成测试                  [依赖 SUB-04, general-purpose]
```

### SUB-01：ActionSchema 适配层

```
子任务 ID: SUB-01
职责:      实现统一 Action 数据类，适配 UI-TARS 和 Qwen3-VL 两种输出格式
检验标准:  能正确解析 "Thought: ... Action: click(start_box='(450,200)')" 为 Action 对象；
           坐标 0-1000 归一化到 [0,1]；校验函数能拦截非法坐标（对应 AC-06）
能力类型:  general-purpose
依赖:      None
文件领地:  src/inference/action_schema.py（新建）
输入:      docs/spec/model-deployment.md §2 §4
输出:      src/inference/action_schema.py + 内置单元测试
禁止:     不碰 vlm_server.py，不碰 context_manager.py
```

### SUB-02：ContextManager

```
子任务 ID: SUB-02
职责:      实现多步任务上下文窗口管理，支持三级策略（全量/滑动窗口/压缩）
检验标准:  步数≤20时全量注入，21-40时滑动窗口，>40时摘要压缩；
          估算 token 数不超过 16384 预算
能力类型:  general-purpose
依赖:      None
文件领地:  src/inference/context_manager.py（新建）
输入:      docs/spec/model-deployment.md §10
输出:      src/inference/context_manager.py + 内置单元测试
禁止:     不碰 action_schema.py，不碰 vlm_server.py
```

### SUB-03：ModelManager + GPUMonitor

```
子任务 ID: SUB-03
职责:      实现模型加载/卸载/切换管理，和后台 GPU 显存监控线程
检验标准:  VLMBackend 枚举正确；load/switch/unload 能切换后端；
          显存采样每 5 秒，误差 < 50MB（对应 AC-07）
能力类型:  general-purpose
依赖:      None
文件领地:  src/inference/model_manager.py + src/inference/gpu_monitor.py（新建）
输入:      docs/spec/model-deployment.md §4 §6
输出:      model_manager.py + gpu_monitor.py + 内置单元测试
禁止:     不碰 vlm_server.py
```

### SUB-04：VLMServer 主流程

```
子任务 ID: SUB-04
职责:      组装 SUB-01/02/03 的模块，实现 start/stop/infer 接口
检验标准:  server.start() 后加载模型，infer() 返回合法 Action；
          支持 switch_backend() 切换（对应 AC-06）
能力类型:  reasoning
依赖:      SUB-01, SUB-02, SUB-03
文件领地:  src/inference/vlm_server.py（新建）
输入:      已完成的 action_schema.py / context_manager.py / model_manager.py / gpu_monitor.py
          + docs/spec/model-deployment.md
输出:      src/inference/vlm_server.py
禁止:     不修改 SUB-01/02/03 的代码（如需修改接口，先与主代理沟通）
```

### SUB-05：集成测试

```
子任务 ID: SUB-05
职责:      端到端测试 VLMServer，验证 infer() 完整链路
检验标准:  能加载模型、截图推理、返回正确 Action、延迟 < 1.5s（AC-06）
能力类型:  general-purpose
依赖:      SUB-04
文件领地:  tests/test_vlm_server.py（新建）
输入:      src/inference/ 下所有已完成模块
输出:      tests/test_vlm_server.py
禁止:     不修改 src/inference/ 下的业务代码
```

### 调度指令

```
"DAG 评估结果：SUB-01、SUB-02、SUB-03 无依赖，可并行启动 3 个 general-purpose 子代理。

先并行启动这三个：
- SUB-01：调用 Agent 工具，general-purpose 类型
- SUB-02：调用 Agent 工具，general-purpose 类型  
- SUB-03：调用 Agent 工具，general-purpose 类型

等待三个全部完成后，启动 SUB-04（reasoning 类型）。
SUB-04 完成后，启动 SUB-05 做集成测试。
所有完成后，对照 PRD AC-06/07 逐条验证。"
```

---

## 3. 子代理 Prompt 模板

主代理给子代理的 prompt 必须包含以下全部字段，缺一不可：

```
【角色】你是子代理 SUB-XX，负责 [职责描述]。

【背景】项目是 AI PC 控制系统（本地 GPU 驱动）。
架构总览见 D:\workspace\Codex\AI_Desktop\docs\architecture.md

【任务】[从子任务表拷贝职责]

【允许读的文件】
- D:\workspace\Codex\AI_Desktop\docs\spec\xxx.md
- D:\workspace\Codex\AI_Desktop\src\xxx\xxx.py

【允许改的文件】
- D:\workspace\Codex\AI_Desktop\src\xxx\xxx.py（新建）

【禁止做的事】
- [从子任务表拷贝 Non-Goals]
- 不得修改其他子代理的文件领地
- 不得调用云端 API
- 不得修改 tests/ 目录

【验收标准】
[从子任务表拷贝检验标准]

【交付物】
输出文件路径：[路径]
完成后报告：文件名 + 自查是否通过验收标准。

【完成标准】
只有交付物存在且自检通过才能报告完成。
```

---

## 4. 主代理集成检查清单

所有子代理返回后，主代理逐项检查：

```
[ ] 交付物文件全部存在
[ ] 每个子代理的自查结果已读取
[ ] 集成测试通过（pytest tests/）
[ ] 对照 PRD AC 逐条验证
[ ] 接口一致性：子代理产出之间的接口对得上
[ ] 无文件领地冲突（同一个文件被两个子代理改了）
[ ] docs/progress.md 已更新
[ ] Git commit 已提交
```

任一 FAIL → 定位子代理，重新分配。

---

## 5. 何时用 / 何时不用

| 情况 | 决策 |
|------|------|
| 任务可拆成 ≥3 个无依赖子任务 | ✅ 用多代理 |
| 子任务需要不同类型技能 | ✅ 用多代理 |
| 单个任务耗时 >2 小时 | ✅ 考虑并行 |
| 只有 1-2 个串行步骤 | ❌ 单代理更快 |
| 子任务间频繁需要沟通 | ❌ 通信成本 > 并行收益 |

> **经验法则**：先单代理做完看效果。发现瓶颈再拆。不要为了多代理而多代理。
