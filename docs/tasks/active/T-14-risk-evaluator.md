---
task_id: T-14
title: 实现风险评级模块
priority: 14
status: pending
depends_on: []
spec: spec/safety-layer.md
estimate: 1d
---

# T-14: 实现风险评级模块

## 描述
实现动作风险评级（low/medium/high/forbidden）。

## 验收标准
- 删除操作评级为 high
- 银行网站访问评级为 forbidden
- 代码在 `src/safety/risk_evaluator.py`
