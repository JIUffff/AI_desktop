"""VLM Server：驱动 UI-TARS 模型的推理壳层。

本模块是模型的"壳"——封装模型的加载、推理、输出解析，
对上层提供统一的 infer() 接口，返回 Action 对象。

架构：
    上层（OODA 循环 / API）
        ↓
    VLMServer.infer(screenshot, task, history)
        ↓
    ┌───────────────────────────────────────┐
    │  ContextManager.build_prompt()        │  ← 组装 prompt
    │  Model.generate()                     │  ← 模型推理
    │  action_schema.parse_output()         │  ← 解析输出
    │  TraceLogger.log()                    │  ← 记录追踪
    └───────────────────────────────────────┘
        ↓
    Action(thought, action_type, coordinates, ...)

Usage:
    server = VLMServer(backend="ui-tars")
    server.start()
    action = server.infer("screenshot.png", "打开记事本")
    print(action.thought, action.action_type, action.coordinates)
    server.stop()
"""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from .action_schema import Action, parse_output
from .context_manager import ContextManager, HistoryEntry
from .model_manager import ModelManager, VLMBackend
from .gpu_monitor import GPUMonitor

logger = logging.getLogger(__name__)


class VLMServer:
    """VLM 推理服务器：封装模型加载、推理、输出解析。

    Attributes:
        backend: 当前后端（UI-TARS / Qwen3-VL-8B / Qwen3-VL-4B）
        model_manager: 模型管理器
        context_manager: 上下文窗口管理器
        gpu_monitor: GPU 显存监控器
        history: 当前任务的历史动作列表
    """

    def __init__(
        self,
        backend: VLMBackend = VLMBackend.UI_TARS,
        models_dir: str = "models",
        enable_trace: bool = True,
    ) -> None:
        """初始化 VLM Server。

        Args:
            backend: 使用的后端模型
            models_dir: 模型权重目录
            enable_trace: 是否启用推理追踪日志
        """
        self.backend = backend
        self.models_dir = Path(models_dir)

        self.model_manager = ModelManager()
        self.context_manager = ContextManager()
        self.gpu_monitor = GPUMonitor()

        # 推理追踪（延迟导入，避免循环依赖）
        self._trace_logger = None
        if enable_trace:
            try:
                from ..observability import TraceLogger
                self._trace_logger = TraceLogger()
            except ImportError:
                logger.warning("observability 模块不可用，追踪日志已禁用")

        self.history: list[HistoryEntry] = []
        self._model: Any = None
        self._processor: Any = None
        self._started = False

    def start(self) -> None:
        """加载模型到 GPU，启动 GPU 监控。"""
        if self._started:
            logger.warning("VLMServer 已启动，请勿重复调用 start()")
            return

        logger.info("启动 VLMServer，后端：%s", self.backend.value)

        # 检查显存
        config = ModelManager.BACKEND_CONFIG.get(self.backend)
        if config:
            required = config.get("estimated_vram_gb", 8.0)
            if not self.model_manager.check_memory_available(required):
                raise RuntimeError(
                    f"显存不足：需要 {required}GB，"
                    f"当前可用 {15.0 - self.model_manager.get_gpu_usage():.1f}GB"
                )

        # 加载模型
        self._load_model()
        self.gpu_monitor.start()
        self._started = True
        logger.info("VLMServer 启动完成，显存占用：%.2f GB", self.model_manager.get_gpu_usage())

    def stop(self) -> None:
        """卸载模型，停止监控，释放显存。"""
        if not self._started:
            return

        logger.info("停止 VLMServer...")
        self.gpu_monitor.stop()
        self.model_manager.unload()
        self._model = None
        self._processor = None
        self._started = False
        self.history.clear()
        logger.info("VLMServer 已停止，显存已释放")

    def infer(self, screenshot_path: str, task: str, step_id: int | None = None) -> Action:
        """执行一次推理。

        Args:
            screenshot_path: 截图文件路径
            task: 当前任务描述
            step_id: 步骤序号（None 则自动递增）

        Returns:
            统一的 Action 对象

        Raises:
            RuntimeError: 服务未启动
            FileNotFoundError: 截图不存在
        """
        if not self._started:
            raise RuntimeError("VLMServer 未启动，请先调用 start()")

        if not Path(screenshot_path).exists():
            raise FileNotFoundError(f"截图不存在：{screenshot_path}")

        # 自动步号
        if step_id is None:
            step_id = len(self.history) + 1

        # 构建追踪记录
        trace_entry = None
        if self._trace_logger:
            from ..observability import TraceEntry
            trace_entry = self._trace_logger.create_entry(
                step_id=step_id,
                task=task,
                screenshot_path=screenshot_path,
                backend=self.backend.value,
                model_name=self.model_manager.BACKEND_CONFIG[self.backend]["model_name"],
            )

        # 推理
        t0 = time.perf_counter()
        success = True
        error_msg = None
        raw_output = ""

        try:
            raw_output = self._infer_raw(screenshot_path, task)
        except Exception as e:
            success = False
            error_msg = str(e)
            logger.error("推理失败 [step=%d]：%s", step_id, e)
            raw_output = f"ERROR: {e}"

        latency_ms = (time.perf_counter() - t0) * 1000
        gpu_mem = self.model_manager.get_gpu_usage()

        # 解析输出
        if success:
            action = parse_output(self.backend.value, raw_output)
        else:
            action = Action(
                thought=f"推理失败：{error_msg}",
                action_type=__import__("src.inference.action_schema", fromlist=["ActionType"]).ActionType.CALL_USER,
                raw_output=raw_output,
            )

        action.confidence = action.confidence  # 保留适配器设置的置信度

        # 记录历史
        self._record_history(step_id, action, success)

        # 记录追踪
        if trace_entry:
            trace_entry.latency_ms = latency_ms
            trace_entry.gpu_mem_gb = gpu_mem
            trace_entry.action_type = action.action_type.value
            trace_entry.thought = action.thought
            trace_entry.coordinates = action.coordinates
            trace_entry.text = action.text
            trace_entry.confidence = action.confidence
            trace_entry.raw_output = raw_output[:500]
            trace_entry.success = success
            trace_entry.error = error_msg
            self._trace_logger.log(trace_entry)

            # 告警检查
            try:
                from ..observability import AlertChecker
                AlertChecker.print_alerts(trace_entry)
            except ImportError:
                pass

        logger.info(
            "推理完成 [step=%d] %s %.0fms mem=%.2fGB",
            step_id,
            action.action_type.value,
            latency_ms,
            gpu_mem,
        )

        return action

    def reset_history(self) -> None:
        """清空历史动作（开始新任务时调用）。"""
        self.history.clear()
        if self._trace_logger:
            self._trace_logger.start_task(f"task_{int(time.time())}")

    def switch_backend(self, backend: VLMBackend) -> None:
        """运行时切换后端（需重新加载模型）。"""
        logger.info("切换后端：%s → %s", self.backend.value, backend.value)
        self.stop()
        self.backend = backend
        self.start()

    # ──────────────────────────────────────────────────────────
    # 内部方法
    # ──────────────────────────────────────────────────────────

    def _load_model(self) -> None:
        """加载模型和 processor。"""
        import torch
        from transformers import AutoModelForCausalLM, AutoProcessor

        config = self.model_manager.BACKEND_CONFIG[self.backend]
        local_dir = self.models_dir / config["local_dir"].split("/")[-1]

        model_path = str(local_dir) if local_dir.exists() else config["model_name"]

        logger.info("加载模型：%s", model_path)

        self._model = AutoModelForCausalLM.from_pretrained(
            model_path,
            device_map="auto",
            torch_dtype=torch.float16,
            trust_remote_code=True,
        )
        self._processor = AutoProcessor.from_pretrained(
            model_path,
            trust_remote_code=True,
        )

        self.model_manager._current_backend = self.backend
        self.model_manager._model = self._model

    def _infer_raw(self, screenshot_path: str, task: str) -> str:
        """调用模型进行原始推理，返回文本输出。"""
        import torch
        from PIL import Image

        image = Image.open(screenshot_path)

        # 构建消息（UI-TARS 格式）
        if self.backend == VLMBackend.UI_TARS:
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": image},
                        {"type": "text", "text": task},
                    ],
                }
            ]
        else:
            # Qwen3-VL 格式
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": image},
                        {"type": "text", "text": task},
                    ],
                }
            ]

        # 处理输入
        inputs = self._processor.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        ).to(self._model.device)

        # 推理
        with torch.no_grad():
            output_ids = self._model.generate(
                **inputs,
                max_new_tokens=512,
                do_sample=False,  # 贪心解码，保证可复现
            )

        # 解码（跳过输入部分）
        input_len = inputs["input_ids"].shape[1]
        output = self._processor.decode(
            output_ids[0][input_len:],
            skip_special_tokens=True,
        )

        return output

    def _record_history(self, step_id: int, action: Action, success: bool) -> None:
        """记录到历史列表，供上下文管理使用。"""
        entry = HistoryEntry(
            step_id=step_id,
            thought=action.thought,
            action_type=action.action_type.value,
            coordinates=action.coordinates,
            text=action.text,
            success=success,
        )
        self.history.append(entry)


# ──────────────────────────────────────────────────────────────
# 便捷函数
# ──────────────────────────────────────────────────────────────


def create_server(backend: str = "ui-tars", models_dir: str = "models") -> VLMServer:
    """便捷创建函数。

    Args:
        backend: "ui-tars" / "qwen3-vl-8b" / "qwen3-vl-4b"
        models_dir: 模型目录

    Returns:
        未启动的 VLMServer 实例
    """
    backend_map = {
        "ui-tars": VLMBackend.UI_TARS,
        "qwen3-vl-8b": VLMBackend.QWEN3_VL_8B,
        "qwen3-vl-4b": VLMBackend.QWEN3_VL_4B,
    }
    return VLMServer(
        backend=backend_map.get(backend, VLMBackend.UI_TARS),
        models_dir=models_dir,
    )
