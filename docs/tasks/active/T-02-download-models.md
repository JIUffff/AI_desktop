---
task_id: T-02
title: 下载模型权重
priority: 2
status: in_progress
depends_on: [T-01]
spec: spec/model-deployment.md
estimate: 0.5d
---

# T-02: 下载模型权重

## 描述
下载 UI-TARS-1.5-7B（主 GUI Agent 模型）和可选的 Qwen3-VL-8B-Instruct（备选通用 VLM）到 `models/` 目录。

> **2026-06-23 架构重构更新**：原任务下载 Qwen2-VL+YOLO+PaddleOCR，现改为 UI-TARS+Qwen3-VL。
> YOLO/PaddleOCR/SoM 已被 UI-TARS 内置能力替代，不再需要。

## 验收标准
- UI-TARS-1.5-7B 权重在 `models/ui-tars-1.5-7b/`
- Qwen3-VL-8B-Instruct 权重在 `models/qwen3-vl-8b/`（可选，按需下载）
- 下载脚本 `scripts/download_models.py` 已更新为 UI-TARS 架构
- 下载使用 hf-mirror.com 镜像站直连（优先）或代理（备选）
