---
task_id: T-18
title: 实现 FastAPI 控制接口
priority: 18
status: pending
depends_on: [T-09]
spec: architecture.md
estimate: 1d
---

# T-18: 实现 FastAPI 控制接口

## 描述
提供 HTTP 接口接收任务指令，返回执行状态。

## 验收标准
- POST /task 接收自然语言指令
- GET /status 返回任务进度
- 代码在 `src/api/server.py`
