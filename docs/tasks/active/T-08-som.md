---
task_id: T-08
title: 实现 SoM 标注生成
priority: 8
status: pending
depends_on: [T-06, T-07]
spec: spec/perception-pipeline.md
estimate: 0.5d
---

# T-08: 实现 SoM 标注生成

## 描述
在截图上为每个检测到的 UI 元素画编号框，生成 Set-of-Mark 标注图。

## 验收标准
- 标注图清晰可读
- 每个元素有唯一编号
- 代码在 `src/perception/som.py`
