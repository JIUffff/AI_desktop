---
task_id: T-09
title: 实现 OODA 循环主逻辑
priority: 9
status: pending
depends_on: [T-04, T-08]
spec: architecture.md
estimate: 2d
---

# T-09: 实现 OODA 循环主逻辑

## 描述
实现 Observe-Orient-Decide-Act 循环，串联感知层→决策层→安全层→执行层。

## 验收标准
- 能完成"打开记事本输入文字"全流程
- 循环步数可控
- 代码在 `src/core/agent.py`
