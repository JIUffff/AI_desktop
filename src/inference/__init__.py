"""推理层：驱动 UI-TARS / Qwen3-VL 模型的完整框架。

核心组件：
- VLMServer: 推理服务器（模型的"壳"），统一 infer() 接口
- ModelManager: 模型加载/卸载/切换
- ActionSchema: 统一动作输出 + 后端适配器
- ContextManager: 多步任务上下文窗口管理
- TaskRouter: 自动模型路由
- GPUMonitor: 显存监控
"""
from .action_schema import Action, ActionType, parse_output
from .model_manager import ModelManager, VLMBackend
from .gpu_monitor import GPUMonitor, get_gpu_info

__all__ = [
    "Action",
    "ActionType",
    "parse_output",
    "ModelManager",
    "VLMBackend",
    "GPUMonitor",
    "get_gpu_info",
]
