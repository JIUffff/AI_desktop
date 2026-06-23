---
title: Spec — 模型部署架构
type: spec
prd: 001
created: 2026-06-22
status: draft
---

# Spec: 模型部署架构

> 本文档由 PRD-001 的 Goals（AC-06/07/13）驱动，定义本地 GPU 推理层的技术设计。

---

## 1. 模型清单

| 模型 | 用途 | 来源 | 量化 | 显存 |
|------|------|------|------|------|
| Qwen2-VL-7B-Instruct | 主决策（意图+动作） | HuggingFace | INT4 (NF4) | ~5GB |
| Qwen2-VL ViT | 视觉编码器 | 随主模型 | FP16 | ~3GB |
| YOLOv8m | UI 元素检测 | ultralytics | FP16 | ~2GB |
| PaddleOCR | 中文 OCR | PaddlePaddle | FP16 | ~1GB |

## 2. 推理框架

### MVP 阶段：transformers + accelerate

```python
from transformers import AutoModelForCausalLM, BitsAndBytesConfig
import torch

quantization_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_use_double_quant=True,
)

model = AutoModelForCausalLM.from_pretrained(
    "Qwen/Qwen2-VL-7B-Instruct",
    quantization_config=quantization_config,
    device_map="auto",
    torch_dtype=torch.float16,
)
```

### 优化阶段：vLLM

- 用 vLLM 替换 transformers，启用 PagedAttention
- 预期吞吐提升 2-3x

## 3. 模块接口

### `src/inference/model_manager.py`

```python
class ModelManager:
    """管理所有本地模型的加载、卸载、显存监控。"""

    def load_vlm(self) -> None: ...
    def load_yolo(self) -> None: ...
    def load_ocr(self) -> None: ...
    def get_gpu_usage(self) -> float: ...  # GB
    def check_memory_available(self, required_gb: float) -> bool: ...
```

### `src/inference/vlm_server.py`

```python
class VLMServer:
    """封装 Qwen2-VL 推理调用。"""

    def infer(self, screenshot_path: str, task: str, history: list) -> dict:
        """
        输入：截图路径、当前任务、历史动作
        输出：{"action": "click", "element_id": 2, "reasoning": "..."}
        """
```

### `src/inference/gpu_monitor.py`

```python
class GPUMonitor:
    """后台线程，每 5 秒检查显存。"""

    def start(self) -> None: ...
    def stop(self) -> None: ...
    def get_current_usage(self) -> dict: ...
```

## 4. 推理加速策略

| 策略 | 效果 | 实现位置 |
|------|------|----------|
| KV Cache 复用 | 2-3x | vlm_server.py |
| 截图压缩到 1024x768 | 1.5x | perception/screenshot.py |
| ViT 常驻不卸载 | 省 0.3s | model_manager.py |
| torch.compile | 1.3x | vlm_server.py |

## 5. 错误处理

| 场景 | 处理 |
|------|------|
| 显存不足 | 拒绝加载，返回错误，触发 GC |
| 模型推理超时（>5s） | 中断，返回 fallback 动作 `ask_human` |
| CUDA OOM | 自动 `empty_cache` 并降级到更小输入 |

## 6. 验收映射

| AC | 验证方式 |
|----|---------|
| AC-06（延迟<1.5s） | benchmarks/ 下计时测试 |
| AC-07（显存<15GB） | gpu_monitor 持续监控 |
| AC-08（无泄漏） | 30 分钟压力测试 |
| AC-13（断网可用） | 断网后跑全部功能 |
