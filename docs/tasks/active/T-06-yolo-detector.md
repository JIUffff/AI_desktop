---
task_id: T-06
title: 集成 YOLOv8 UI 元素检测
priority: 6
status: pending
depends_on: [T-02]
spec: spec/perception-pipeline.md
estimate: 1d
---

# T-06: 集成 YOLOv8 UI 元素检测

## 描述
用 YOLOv8m 检测截图中的 UI 元素（按钮/输入框/图标/链接）。

## 验收标准
- 能检测常见 UI 元素
- 检测速度 > 30 FPS
- 代码在 `src/perception/yolo_detector.py`
