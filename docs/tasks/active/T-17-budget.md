---
task_id: T-17
title: 实现预算熔断
priority: 17
status: pending
depends_on: []
spec: spec/safety-layer.md
estimate: 0.5d
---

# T-17: 实现预算熔断

## 描述
单任务最大 50 步 / 10 分钟，超限自动熔断。

## 验收标准
- 50 步后自动停止
- 10 分钟后自动停止
- 代码在 `src/safety/budget.py`
