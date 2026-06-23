---
task_id: T-05
title: 实现截图模块（DPI 适配）
priority: 5
status: pending
depends_on: []
spec: architecture.md
estimate: 0.5d
---

# T-05: 实现截图模块（DPI 适配）

## 描述
实现 DPI 感知的截图模块，解决 Windows 高 DPI 缩放坐标偏移问题。

> **2026-06-23 架构重构更新**：原任务位于 `src/perception/screenshot.py`，
> 现移至 `src/execution/screenshot.py`（perception 层已废弃）。
> 截图是执行层的输入，不是独立感知模块。

## 验收标准
- 在 150%/200% 缩放下截图分辨率正确
- 截图坐标与鼠标坐标一致
- 截图保存为 PNG 格式，分辨率 1024x768（供 UI-TARS 输入）
- 代码在 `src/execution/screenshot.py`
- 测试在 `tests/test_screenshot.py`
