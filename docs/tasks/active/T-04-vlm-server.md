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
完善 VLMServer 推理服务，确保 UI-TARS 和 Qwen3-VL 后端可切换，提供统一的 `infer(screenshot, task, history) -> Action` 接口。

> **2026-06-23 架构重构更新**：原任务仅封装 Qwen2-VL，现需支持 UI-TARS（主）+ Qwen3-VL（备选）双后端。
> 骨架代码已存在于 `src/inference/vlm_server.py`，需完善并补测试。

## 验收标准
- 输入截图+任务，输出结构化 Action 对象（thought + action_type + coordinates）
- UI-TARS 后端可正常推理（需模型权重已下载）
- Qwen3-VL 后端可正常推理（需模型权重已下载）
- 后端切换功能正常（switch_backend）
- 单次推理延迟 < 3 秒（MVP 阶段，transformers 后端）
- 代码在 `src/inference/vlm_server.py`
- 测试在 `tests/test_vlm_server.py`
