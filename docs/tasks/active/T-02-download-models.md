---
task_id: T-02
title: 下载模型权重
priority: 2
status: pending
depends_on: [T-01]
spec: spec/model-deployment.md
estimate: 0.5d
---

# T-02: 下载模型权重

## 描述
下载 Qwen2-VL-7B-Instruct、YOLOv8m、PaddleOCR 模型到 `models/` 目录。

## 验收标准
- Qwen2-VL-7B 权重在 `models/qwen2-vl-7b/`
- YOLOv8m 权重在 `models/yolov8m-ui.pt`
- PaddleOCR 模型在 `models/paddleocr/`
- 总大小 < 20GB
