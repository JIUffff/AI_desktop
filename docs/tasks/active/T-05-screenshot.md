---
task_id: T-05
title: 实现截图模块（DPI 适配）
priority: 5
status: pending
depends_on: []
spec: spec/perception-pipeline.md
estimate: 0.5d
---

# T-05: 实现截图模块（DPI 适配）

## 描述
实现 DPI 感知的截图模块，解决 Windows 高 DPI 缩放坐标偏移问题。

## 验收标准
- 在 150%/200% 缩放下截图分辨率正确
- 截图坐标与鼠标坐标一致
- 代码在 `src/perception/screenshot.py`
