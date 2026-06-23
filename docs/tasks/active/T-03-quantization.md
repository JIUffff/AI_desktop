---
task_id: T-03
title: 实现 AWQ INT4 量化与加载
priority: 3
status: pending
depends_on: [T-02]
spec: spec/model-deployment.md
estimate: 1d
---

# T-03: 实现 AWQ INT4 量化与加载

## 描述
实现 UI-TARS-1.5-7B 的 AWQ INT4 量化加载，验证显存占用在预算内。

> **2026-06-23 架构重构更新**：原任务使用 bitsandbytes NF4 量化 Qwen2-VL，
> 现改为 AWQ INT4 量化 UI-TARS（官方提供 AWQ 量化版，精度损失 <1%）。
> 备选 Qwen3-VL-8B 使用 GPTQ-Int4 量化。

## 验收标准
- UI-TARS-1.5-7B AWQ INT4 加载后显存 < 8GB（含 ViT）
- 能成功进行一次推理（输入截图+任务，输出 Thought+Action）
- 量化配置在 `src/inference/quantization.py`
- Qwen3-VL-8B GPTQ-Int4 加载后显存 < 5.1GB（含 ViT）
