---
task_id: T-03
title: 实现 INT4 量化脚本
priority: 3
status: pending
depends_on: [T-02]
spec: spec/model-deployment.md
estimate: 1d
---

# T-03: 实现 INT4 量化脚本

## 描述
用 bitsandbytes 实现 Qwen2-VL-7B 的 INT4 (NF4) 量化，验证显存占用。

## 验收标准
- 量化后模型加载显存 < 6GB
- 能成功进行一次推理
- 脚本在 `src/inference/quantization.py`
