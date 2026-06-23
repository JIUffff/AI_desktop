---
task_id: T-20
title: 编写性能基准测试
priority: 20
status: pending
depends_on: [T-04]
spec: spec/model-deployment.md
estimate: 0.5d
---

# T-20: 编写性能基准测试

## 描述
为 AC-06~AC-08 编写性能测试。

## 验收标准
- AC-06: 单步延迟 < 1.5s
- AC-07: 显存峰值 < 15GB
- AC-08: 30 分钟无泄漏
- 测试在 `tests/benchmarks/`
