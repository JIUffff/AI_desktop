---
task_id: T-15
title: 实现人工确认 UI
priority: 15
status: pending
depends_on: [T-14]
spec: spec/safety-layer.md
estimate: 1d
---

# T-15: 实现人工确认 UI

## 描述
高风险操作弹窗确认，30 秒超时自动拒绝。

## 验收标准
- high 级别操作触发弹窗
- 30 秒未确认自动拒绝
- 代码在 `src/safety/human_approval.py`
