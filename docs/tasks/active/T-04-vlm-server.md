---
task_id: T-04
title: 实现 VLM 推理服务封装
priority: 4
status: pending
depends_on: [T-03]
spec: spec/model-deployment.md
estimate: 1d
---

# T-04: 实现 VLM 推理服务封装

## 描述
封装 Qwen2-VL 调用，提供统一的 `infer(screenshot, task, history) -> action` 接口。

## 验收标准
- 输入截图+任务，输出结构化动作 JSON
- 单次推理延迟 < 3 秒（MVP 阶段）
- 代码在 `src/inference/vlm_server.py`
