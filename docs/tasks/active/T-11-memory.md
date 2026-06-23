---
task_id: T-11
title: 实现上下文记忆管理
priority: 11
status: pending
depends_on: []
spec: architecture.md
estimate: 0.5d
---

# T-11: 实现上下文记忆管理

## 描述
维护滚动上下文窗口，保留最近 10 步动作历史。

## 验收标准
- 历史超过 10 步自动压缩为摘要
- 代码在 `src/core/memory.py`
