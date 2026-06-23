---
task_id: T-01
title: GPU 环境初始化
priority: 1
status: completed
depends_on: []
spec: spec/model-deployment.md
estimate: 0.5d
---

# T-01: GPU 环境初始化

## 描述
安装 PyTorch（CUDA 12.8 支持）、transformers、accelerate、bitsandbytes，验证 GPU 可用。

## 验收标准
- `torch.cuda.is_available()` 返回 True
- `torch.cuda.get_device_name(0)` 返回 "NVIDIA GeForce RTX 5070 Ti"
- 能成功在 GPU 上创建张量并运算
