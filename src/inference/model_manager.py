"""模型管理器：加载、卸载、切换 VLM 后端。

spec 详见 model-deployment.md §4 模块接口。
"""
from __future__ import annotations

from enum import Enum
from typing import Any


class VLMBackend(Enum):
    """VLM 后端枚举。"""

    UI_TARS = "ui-tars-1.5-7b"      # 主：GUI Agent 专用
    QWEN3_VL_8B = "qwen3-vl-8b"     # 备：通用 VLM
    QWEN3_VL_4B = "qwen3-vl-4b"     # 降级：轻量级


class ModelManager:
    """管理所有本地模型的加载、卸载、显存监控。

    MVP 阶段：单后端常驻，运行时切换需重新加载。
    优化阶段：支持双模型并行（UI-TARS + Qwen3-VL-8B）。
    """

    BACKEND_CONFIG: dict[VLMBackend, dict[str, Any]] = {
        VLMBackend.UI_TARS: {
            "model_name": "ByteDance-Seed/UI-TARS-1.5-7B",
            "local_dir": "models/ui-tars-1.5-7b",
            "quantization": "awq",
            "estimated_vram_gb": 8.0,  # 含 ViT
        },
        VLMBackend.QWEN3_VL_8B: {
            "model_name": "Qwen/Qwen3-VL-8B-Instruct",
            "local_dir": "models/qwen3-vl-8b",
            "quantization": "gptq-int4",
            "estimated_vram_gb": 5.1,
        },
        VLMBackend.QWEN3_VL_4B: {
            "model_name": "Qwen/Qwen3-VL-4B-Instruct",
            "local_dir": "models/qwen3-vl-4b",
            "quantization": "gptq-int4",
            "estimated_vram_gb": 4.5,
        },
    }

    def __init__(self) -> None:
        self._current_backend: VLMBackend | None = None
        self._model: Any = None
        self._processor: Any = None

    def load_vlm(self, backend: VLMBackend = VLMBackend.UI_TARS) -> None:
        """加载指定后端模型到 GPU。

        若已有模型加载，先卸载再加载新的。
        """
        if self._current_backend == backend and self._model is not None:
            return  # 已加载

        if self._model is not None:
            self.unload()

        config = self.BACKEND_CONFIG[backend]
        # 实际加载逻辑在 vlm_server.py 实现
        # 这里仅记录状态
        self._current_backend = backend
        self._model = None  # placeholder
        self._processor = None

    def unload(self) -> None:
        """卸载当前模型，释放显存。"""
        import gc

        import torch

        self._model = None
        self._processor = None
        self._current_backend = None
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def switch_backend(self, backend: VLMBackend) -> None:
        """运行时切换后端（需重新加载模型）。"""
        self.load_vlm(backend)

    def get_gpu_usage(self) -> float:
        """返回当前 GPU 已用显存（GB）。"""
        try:
            import torch

            if not torch.cuda.is_available():
                return 0.0
            return torch.cuda.memory_allocated() / 1024**3
        except Exception:
            return 0.0

    def check_memory_available(self, required_gb: float) -> bool:
        """检查是否有足够显存。RTX 5070 Ti 16GB，留 1GB 余量。"""
        current = self.get_gpu_usage()
        available = 15.0 - current  # 16GB - 1GB 余量 - 当前已用
        return available >= required_gb

    @property
    def current_backend(self) -> VLMBackend | None:
        return self._current_backend
