---
task_id: T-10
title: 实现任务分解 planner
priority: 10
status: pending
depends_on: []
spec: architecture.md
estimate: 1d
---

# T-10: 实现任务分解 planner

## 描述
将用户自然语言指令分解为原子步骤序列。

## 验收标准
- 输入"打开浏览器搜索AI并截图"输出 3-5 个步骤
- 代码在 `src/core/planner.py`
