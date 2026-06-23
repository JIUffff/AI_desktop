---
title: Spec — 模型部署架构
type: spec
prd: 001
created: 2026-06-22
updated: 2026-06-23
status: draft
---

# Spec: 模型部署架构

> 本文档由 PRD-001 的 Goals（AC-06/07/13）驱动，定义本地 GPU 推理层的技术设计。
>
> **2026-06-23 架构重构**：UI-TARS 是端到端原生 GUI Agent，已移除独立 CV 子模块（YOLO/PaddleOCR/SoM）。
> 详见 `docs/reports/module-compatibility-2026.html`。

---

## 0. 选型背景（2026-06-23 更新）

原方案选用 Qwen2-VL-7B（2024 年 10 月发布），截至 2026 年已落后两代。
经全面调研 2025-2026 年开源 VLM 生态，最终选定：

| 角色 | 模型 | 选型理由 |
|------|------|----------|
| **主 GUI Agent** | UI-TARS-1.5-7B | GUI 任务 SOTA：ScreenSpot-V2 94.2%、OSWorld 42.5%，超越 OpenAI CUA / Claude 3.7 |
| **通用 VLM 备选** | Qwen3-VL-8B | 2025.10 发布，GPTQ-Int4 仅 ~3.1GB 显存，Instruct+Thinking 双模式 |

> 详细对比见 `docs/reports/vlm-model-selection-2026.html`。
> 模块兼容性分析见 `docs/reports/module-compatibility-2026.html`。

---

## 1. 模型清单

### 1.1 主方案（默认部署）— 端到端 Agent

| 模型 | 用途 | 来源 | 量化 | 显存 |
|------|------|------|------|------|
| **UI-TARS-1.5-7B** | **GUI Agent 核心**：截图→OCR+检测+推理+动作一体化 | HuggingFace `ByteDance-Seed/UI-TARS-1.5-7B` | AWQ INT4 | ~6GB |
| UI-TARS ViT | 视觉编码器（内置 OCR + 元素定位能力来源） | 随主模型加载 | FP16 | ~2GB |

> **关键变化**：不再需要 YOLOv8m、PaddleOCR、SoM 标注模块。UI-TARS 自带全部感知能力。

### 1.2 备选方案（通用 VLM 场景）

| 模型 | 用途 | 来源 | 量化 | 显存 |
|------|------|------|------|------|
| Qwen3-VL-8B-Instruct | 通用视觉问答、文档理解、非 GUI 视觉任务 | HuggingFace `Qwen/Qwen3-VL-8B-Instruct` | GPTQ-Int4 | ~3.1GB |
| Qwen3-VL-8B ViT | 视觉编码器 | 随主模型 | FP16 | ~2GB |

### 1.3 可选插件（按需 lazy-load）

| 插件 | 用途 | 来源 | 显存 | 加载策略 |
|------|------|------|------|----------|
| YOLO11m | 超高速纯检测（非主流程场景） | ultralytics | ~2GB | Lazy-load，用完卸载 |
| PaddleOCR v4 | OCR fallback（VLM 识别失败时降级） | PaddlePaddle | ~1GB | Lazy-load，按需加载 |

| 模型 | 用途 | 量化 | 显存 |
|------|------|------|------|
| Qwen3-VL-4B-Instruct | 降级 GUI Agent | GPTQ-Int4 | ~2.5GB |

---

## 2. 为什么选 UI-TARS-1.5-7B

### 2.1 基准测试对比（2026-06 调研）

| 基准 | UI-TARS-1.5-7B | OpenAI CUA | Claude 3.7 | 前任 SOTA |
|------|----------------|------------|------------|-----------|
| **OSWorld**（100步） | **42.5** | 36.4 | 28 | 38.1 |
| **ScreenSpot-V2** | **94.2** | 87.9 | 87.6 | 91.6 |
| **ScreenSpotPro** | **61.6** | 23.4 | 27.7 | 43.6 |
| **AndroidWorld** | **64.2** | — | — | 59.5 |
| **Online-Mind2Web** | 75.8 | **71** | 62.9 | 71 |

> 数据来源：[HuggingFace UI-TARS-1.5-7B 模型卡](https://huggingface.co/ByteDance-Seed/UI-TARS-1.5-7B)

### 2.2 核心优势

1. **原生 GUI Agent 架构**：专为截图→推理→动作设计，无需额外封装
2. **推理能力**：支持 "thought + action" 模式，先思考再操作
3. **Apache 2.0 许可**：允许商用
4. **字节跳动维护**：UI-TARS-1.5 是最新版本（2025），持续更新
5. **vLLM 支持**：可用 vLLM 0.4.2+ 部署，AWQ 量化显存降低 40%

### 2.3 Qwen3-VL-8B 作为备选的场景

- 需要非 GUI 的视觉任务（文档理解、图片问答、OCR）
- 需要超长上下文（256K tokens）
- 需要 Thinking 模式做复杂推理
- 显存极度紧张时（GPTQ-Int4 仅 ~3.1GB）

---

## 3. 推理框架

### 3.1 MVP 阶段：transformers + bitsandbytes

```python
from transformers import AutoModelForCausalLM, AutoProcessor
import torch

# UI-TARS-1.5-7B 加载（使用官方 AWQ 量化版）
model = AutoModelForCausalLM.from_pretrained(
    "ByteDance-Seed/UI-TARS-1.5-7B",
    device_map="auto",
    torch_dtype=torch.float16,
    trust_remote_code=True,
)
processor = AutoProcessor.from_pretrained(
    "ByteDance-Seed/UI-TARS-1.5-7B",
    trust_remote_code=True,
)
```

### 3.2 优化阶段：vLLM

```bash
# UI-TARS-1.5-7B with vLLM + AWQ
vllm serve "ByteDance-Seed/UI-TARS-1.5-7B" \
  --host 0.0.0.0 \
  --port 8000 \
  --tensor-parallel-size 1 \
  --gpu-memory-utilization 0.90 \
  --max-model-len 16384 \
  --block-size 32 \
  --quantization awq \
  --dtype half \
  --trust-remote-code \
  --enforce-eager \
  --enable-prefix-caching
```

**vLLM 版本要求**：0.4.2（经测试为最优兼容版本，0.5.0+ 有坐标解析异常）

> **`--enable-prefix-caching` 说明**（2026-06-23 新增）：
> 同一任务多步推理共享 system prompt 前缀（~300 tokens），避免重复计算。
> 预期收益：多步任务吞吐提升 2-3x，单步延迟降低 15-25%。
> 注意：prefix caching 在 vLLM 0.4.2 中为实验性功能，若出现坐标异常可关闭。

### 3.3 Qwen3-VL-8B 备选部署

```bash
# Qwen3-VL-8B with vLLM + GPTQ-Int4
vllm serve "Qwen/Qwen3-VL-8B-Instruct-GPTQ-Int4" \
  --host 0.0.0.0 \
  --port 8000 \
  --tensor-parallel-size 1 \
  --gpu-memory-utilization 0.92 \
  --max-model-len 16384 \
  --block-size 32 \
  --dtype auto \
  --enforce-eager \
  --trust-remote-code \
  --enable-prefix-caching
```

---

## 4. 模块接口

### `src/inference/model_manager.py`

```python
from enum import Enum

class VLMBackend(Enum):
    UI_TARS = "ui-tars-1.5-7b"      # 主：GUI Agent 专用
    QWEN3_VL_8B = "qwen3-vl-8b"     # 备：通用 VLM
    QWEN3_VL_4B = "qwen3-vl-4b"     # 降级：轻量级

class ModelManager:
    """管理所有本地模型的加载、卸载、显存监控。"""

    def load_vlm(self, backend: VLMBackend = VLMBackend.UI_TARS) -> None: ...
    def get_gpu_usage(self) -> float: ...  # GB
    def check_memory_available(self, required_gb: float) -> bool: ...
    def switch_backend(self, backend: VLMBackend) -> None: ...  # 运行时切换
```

### `src/inference/action_schema.py`（新增）

```python
@dataclass
class Action:
    """统一动作输出，所有后端归一化为此结构。"""
    thought: str
    action_type: ActionType          # CLICK / TYPE / SCROLL / KEY / FINISHED / ...
    coordinates: list[float] | None  # [x, y] 归一化到 [0, 1]
    text: str | None                 # type 动作的输入文本
    key_combo: str | None            # key 动作的快捷键
    scroll_amount: int | None        # scroll 动作的滚动量
    confidence: float | None         # 置信度
    raw_output: str                  # 原始输出（调试用）

    def validate(self) -> bool: ...  # 合法性校验（安全层调用）

def parse_output(backend: str, raw: str) -> Action:
    """根据后端名称选择适配器，归一化输出。"""
    # UI-TARS → parse_ui_tars_output (Thought+Action 文本格式)
    # Qwen3-VL → parse_qwen3vl_output (自然语言 + 格式模仿)
```

### `src/inference/vlm_server.py`

```python
from .action_schema import Action

class VLMServer:
    """封装 VLM 推理调用，支持 UI-TARS 和 Qwen3-VL 后端。"""

    def infer(self, screenshot_path: str, task: str, history: list) -> Action:
        """
        输入：截图路径、当前任务、历史动作
        输出：统一 Action 对象（经 action_schema 归一化）
              - thought: 模型思考过程
              - action_type: CLICK / TYPE / SCROLL / ...
              - coordinates: [x, y] 归一化到 [0, 1]
              - confidence: 置信度
        """

    def infer_grounding(self, screenshot_path: str, element_desc: str) -> Action:
        """UI-TARS 专用：给定元素描述，返回精确坐标的 Action。"""
```

### `src/inference/context_manager.py`（新增，见 §10）

```python
class ContextManager:
    """管理多步任务的上下文窗口（见 §10 上下文窗口管理策略）。"""
    def build_prompt(self, history: list, task: str) -> str: ...
    def should_compress(self, history: list) -> bool: ...
    def estimate_tokens(self, history: list) -> int: ...
```

### `src/inference/router.py`（新增，见 §11）

```python
class TaskRouter:
    """自动模型路由（见 §11 自动模型路由）。"""
    def classify(self, task: str) -> TaskType: ...
    def route(self, task: str) -> VLMBackend: ...
    def fallback_chain(self) -> list[VLMBackend]: ...
```

### `src/inference/gpu_monitor.py`

```python
class GPUMonitor:
    """后台线程，每 5 秒检查显存。"""

    def start(self) -> None: ...
    def stop(self) -> None: ...
    def get_current_usage(self) -> dict: ...
```

---

## 5. 推理加速策略

| 策略 | 效果 | 实现位置 |
|------|------|----------|
| AWQ INT4 量化 | 显存降 40%，精度损失 <1% | model_manager.py |
| `--enable-prefix-caching` | 多步任务吞吐 2-3x，单步延迟降 15-25% | vLLM 启动参数 |
| KV Cache 复用 | 减少 KV 重复计算 | vlm_server.py |
| 截图压缩到 1024x768 | 1.5x 速度 | src/execution/screenshot.py |
| ViT 常驻不卸载 | 省 0.3s | model_manager.py |
| `--enforce-eager` | 图文混合更稳定 | vLLM 启动参数 |
| `--block-size 32` | 减少内存碎片 | vLLM 启动参数 |
| `--max-model-len 16384` | 释放 ~1.8GB 显存 | vLLM 启动参数 |

---

## 6. 显存预算（RTX 5070 Ti 16GB）

> **2026-06-23 修正**：架构重构移除 YOLO/PaddleOCR/SoM 后，本表与 §1 模型清单、`architecture.md` 显存分配保持一致。

### 主方案：UI-TARS-1.5-7B AWQ INT4（推荐）

| 模块 | 预算 | 说明 |
|------|------|------|
| UI-TARS-1.5-7B (AWQ INT4) | ~6GB | 主 GUI Agent（内置 OCR + 元素检测 + 推理） |
| 视觉编码器 ViT | ~2GB | 随主模型加载 |
| KV Cache + 缓冲 | ~3~4GB | 推理缓存（移除其他模型后可扩容） |
| 图像缓冲 | ~1GB | 截图/历史帧 |
| **总峰值** | **~10~11GB** | **留 5~6GB 余量 ✅** |

### 备选方案：Qwen3-VL-8B GPTQ-Int4（通用场景）

| 模块 | 预算 | 说明 |
|------|------|------|
| Qwen3-VL-8B (GPTQ-Int4) | ~3.1GB | 通用 VLM（极度省显存） |
| 视觉编码器 ViT | ~2GB | 随主模型加载 |
| KV Cache + 缓冲 | ~4~5GB | 推理缓存（256K 上下文支持） |
| 图像缓冲 | ~1GB | 截图/历史帧 |
| **总峰值** | **~10~11GB** | **留 5~6GB 余量 ✅** |

### 可选插件预算（按需 lazy-load，不计入主流程峰值）

| 插件 | 预算 | 加载策略 |
|------|------|----------|
| YOLO11m | ~2GB | Lazy-load，用完卸载 |
| PaddleOCR v4 | ~1GB | Lazy-load，仅 fallback |

---

## 7. 错误处理

| 场景 | 处理 |
|------|------|
| 显存不足 | 拒绝加载，返回错误，触发 GC；若持续不足，降级到 Qwen3-VL-4B |
| 模型推理超时（>5s） | 中断，返回 fallback 动作 `ask_human` |
| CUDA OOM | 自动 `empty_cache` 并降级到更小输入或更轻量模型 |
| vLLM 坐标偏移 | 使用 `smart_resize` 校准坐标转换逻辑 |
| UI-TARS 返回异常坐标 | 校验坐标范围 [0, 1000]，异常时重试或降级 |

---

## 8. 验收映射

| AC | 验证方式 |
|----|---------|
| AC-06（延迟<1.5s） | benchmarks/ 下计时测试（UI-TARS AWQ 预期 ~320-500ms） |
| AC-07（显存<15GB） | gpu_monitor 持续监控（主方案 ~10-11GB，远低于上限） |
| AC-08（无泄漏） | 30 分钟压力测试 |
| AC-13（断网可用） | 断网后跑全部功能（模型已本地化） |

---

## 9. 模型下载

### 9.1 主模型：UI-TARS-1.5-7B

```bash
# 优先使用镜像站直连（不消耗代理流量）
export HF_ENDPOINT=https://hf-mirror.com

# 下载 UI-TARS-1.5-7B（约 15GB）
hf download ByteDance-Seed/UI-TARS-1.5-7B \
  --local-dir models/ui-tars-1.5-7b
```

### 9.2 备选模型：Qwen3-VL-8B

```bash
# 下载 Qwen3-VL-8B-Instruct（约 16GB）
hf download Qwen/Qwen3-VL-8B-Instruct \
  --local-dir models/qwen3-vl-8b
```

### 9.3 可选插件（按需下载）

```bash
# YOLO11m（约 60MB，可选插件，首次使用自动下载）
# PaddleOCR v4（可选 fallback，首次使用自动下载）
# 二者均不在主流程中使用，仅在 UI-TARS OCR/检测失败时降级
```

> 下载脚本见 `scripts/download_models.py`

---

## 10. 上下文窗口管理策略

> 多步 GUI 任务需要历史动作记忆。本节定义如何管理 UI-TARS 的上下文窗口。

### 10.1 上下文容量计算

UI-TARS vLLM 启动参数 `--max-model-len 16384`，单步推理的 token 构成：

| 组成部分 | 估算 token 数 | 说明 |
|---------|--------------|------|
| System prompt | ~300 | 固定，任务指令、安全规则 |
| 当前截图 | ~2000 | 1024x768 截图，按 ViT patch 折算 |
| 当前任务描述 | ~50 | 用户原始指令 + 当前步骤 |
| **单步 thought+action** | ~150 | 模型输出 |
| **单步历史记录** | ~200 | 思考+动作的文本表示 |
| **可用历史步数** | **~65 步** | (16384 - 300 - 2000 - 50) / 200 ≈ 65 |

> 实际可用步数受截图分辨率和输出长度影响，**保守估计 30-40 步**为安全阈值。

### 10.2 三级上下文管理策略

```
步数 ≤ 20     → 全量注入（Full History）
步数 21-40    → 滑动窗口（Sliding Window，最近 20 步）
步数 > 40     → 摘要压缩（Summary Compression）
```

#### 策略 1：全量注入（步数 ≤ 20）

每步推理时，将所有历史 thought+action 拼接到 prompt：

```python
history_text = "\n".join(
    f"Step {i+1}: Thought: {h['thought']} | Action: {h['action']}"
    for i, h in enumerate(history)
)
prompt = f"{system_prompt}\n\n历史动作:\n{history_text}\n\n当前任务: {task}\n当前截图:"
```

#### 策略 2：滑动窗口（步数 21-40）

保留最近 20 步完整记录，早期步数仅保留 action 摘要：

```python
recent = history[-20:]  # 最近 20 步完整
early = history[:-20]   # 早期步数仅保留 action
early_summary = "\n".join(
    f"Step {i+1}: {h['action']}" for i, h in enumerate(early)
)
```

#### 策略 3：摘要压缩（步数 > 40）

每 10 步生成一次阶段性摘要，替换原始记录：

```python
# 每 10 步压缩一次
if len(history) % 10 == 0 and len(history) >= 40:
    last_10 = history[-10:]
    summary = llm_summarize(last_10)  # 调用模型生成摘要
    compressed_history.append({"summary": summary, "range": f"step {start}-{end}"})
```

### 10.3 截断触发条件

| 触发条件 | 阈值 | 动作 |
|---------|------|------|
| Token 数超限 | prompt token > 14000（留 2000 余量） | 强制截断最早历史 |
| 步数超限 | 步数 > 50 | 触发 PRD AC-11 熔断 |
| 显存压力 | KV Cache > 4GB | 截断历史，仅保留最近 10 步 |

### 10.4 实现位置

```
src/inference/context_manager.py   ← 新增
├── class ContextManager
│   ├── build_prompt(history, task, screenshot) → str
│   ├── should_compress(history) → bool
│   ├── compress(history) → list[dict]
│   └── estimate_tokens(history) → int
```

### 10.5 与 PRD AC 的映射

| AC | 关系 |
|----|------|
| AC-06（延迟<1.5s） | 上下文越长延迟越高，P0-1 基准测试验证 |
| AC-11（50步熔断） | 步数超 50 触发熔断，与策略 3 衔接 |

---

## 11. 自动模型路由

> 根据任务类型自动选择后端，无需手动 `switch_backend()`。

### 11.1 路由规则

| 任务类型 | 检测关键词 | 路由到 | 理由 |
|---------|-----------|--------|------|
| **GUI 操作** | 点击/输入/打开/选中/拖拽/滚动 | UI-TARS | 原生 GUI Agent，ScreenSpot 94.2% |
| **文档理解** | 读懂/总结/翻译这份文档 | Qwen3-VL-8B | 256K 上下文，文档理解强 |
| **图片问答** | 这张图/图片里有什么 | Qwen3-VL-8B | 通用 VLM 视觉问答 |
| **复杂 OCR** | 提取这张表的所有文字 | Qwen3-VL-8B | 32 语言 OCR |
| **不确定** | 无法分类 | UI-TARS | 默认走主模型 |

### 11.2 失败 Fallback 链

```
任务输入
    ↓
[路由器] 分类任务类型
    ↓
[UI-TARS] 尝试推理
    ├── 成功 → 返回结果
    └── 失败（OOM/超时/格式异常）
        ↓
[Qwen3-VL-8B] 降级尝试
    ├── 成功 → 返回结果
    └── 失败
        ↓
[Qwen3-VL-4B] 最低降级
    ├── 成功 → 返回结果
    └── 失败
        ↓
[ask_human] 请求人工介入
```

### 11.3 实现位置

```
src/inference/router.py             ← 新增
├── class TaskRouter
│   ├── classify(task: str) → TaskType
│   ├── route(task: str) → VLMBackend
│   └── fallback_chain() → list[VLMBackend]
```
