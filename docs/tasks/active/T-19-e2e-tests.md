---
task_id: T-19
title: 编写端到端测试
priority: 19
status: pending
depends_on: [T-09, T-15, T-17]
spec: prd/001-local-gpu-pc-control.md
estimate: 1d
---

# T-19: 编写端到端测试

## 描述
为 AC-01~AC-05 编写端到端测试。

## 验收标准
- AC-01: 记事本任务测试
- AC-02: 文件整理测试
- AC-03: 浏览器搜索测试
- AC-04: 危险操作确认测试
- AC-05: 连续失败暂停测试
- 测试在 `tests/e2e/`
