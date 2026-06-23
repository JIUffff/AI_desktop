---
task_id: T-16
title: 实现审计日志
priority: 16
status: pending
depends_on: []
spec: spec/safety-layer.md
estimate: 0.5d
---

# T-16: 实现审计日志

## 描述
追加式记录所有操作，含截图+动作+时间，不可篡改。

## 验收标准
- 日志格式为 JSONL
- 追加写入模式
- 代码在 `src/safety/audit_log.py`
