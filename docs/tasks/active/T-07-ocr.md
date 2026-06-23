---
task_id: T-07
title: 集成 PaddleOCR
priority: 7
status: pending
depends_on: [T-02]
spec: spec/perception-pipeline.md
estimate: 0.5d
---

# T-07: 集成 PaddleOCR

## 描述
集成 PaddleOCR 识别界面中文文字。

## 验收标准
- 中文识别准确率 > 90%
- 代码在 `src/perception/ocr.py`
