"""自动模型路由：根据任务类型自动选择 VLM 后端。

spec 详见 model-deployment.md §11 自动模型路由。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from .model_manager import VLMBackend


class TaskType(str, Enum):
    """任务类型枚举。"""

    GUI_OPERATION = "gui_operation"  # GUI 操作（点击/输入/打开/选中）
    DOCUMENT_UNDERSTANDING = "document_understanding"  # 文档理解
    IMAGE_QA = "image_qa"  # 图片问答
    COMPLEX_OCR = "complex_ocr"  # 复杂 OCR
    UNKNOWN = "unknown"  # 无法分类


# 任务关键词映射
TASK_KEYWORDS: dict[TaskType, list[str]] = {
    TaskType.GUI_OPERATION: [
        # 中文
        "点击", "输入", "打开", "关闭", "选中", "拖拽", "滚动", "切换",
        "最大化", "最小化", "复制", "粘贴", "保存", "删除", "移动到",
        # 英文
        "click", "type", "open", "close", "select", "drag", "scroll",
        "switch", "maximize", "minimize", "copy", "paste", "save", "delete",
    ],
    TaskType.DOCUMENT_UNDERSTANDING: [
        "读懂", "总结", "翻译这份", "这份文档", "这个pdf", "read this doc",
        "summarize", "translate this",
    ],
    TaskType.IMAGE_QA: [
        "这张图", "图片里", "这张照片", "what's in", "describe this image",
        "这张截图",
    ],
    TaskType.COMPLEX_OCR: [
        "提取", "识别", "这张表的所有", "ocr", "extract text", "extract table",
    ],
}


@dataclass
class RoutingResult:
    """路由结果。"""

    task_type: TaskType
    backend: VLMBackend
    reason: str


class TaskRouter:
    """任务分类器与路由器。

    Usage:
        router = TaskRouter()
        result = router.route("点击桌面上的记事本图标")
        # result.backend == VLMBackend.UI_TARS
        # result.task_type == TaskType.GUI_OPERATION
    """

    def classify(self, task: str) -> TaskType:
        """根据任务文本分类。

        策略：关键词匹配。简单但足够 MVP 使用。
        未来可升级为小型分类模型。
        """
        task_lower = task.lower()

        # 按优先级检查：GUI 操作 > 文档理解 > 图片问答 > 复杂 OCR
        for task_type in [
            TaskType.GUI_OPERATION,
            TaskType.DOCUMENT_UNDERSTANDING,
            TaskType.IMAGE_QA,
            TaskType.COMPLEX_OCR,
        ]:
            for keyword in TASK_KEYWORDS[task_type]:
                if keyword in task_lower:
                    return task_type

        return TaskType.UNKNOWN

    def route(self, task: str) -> RoutingResult:
        """根据任务类型选择后端。"""
        task_type = self.classify(task)

        routing_map = {
            TaskType.GUI_OPERATION: (
                VLMBackend.UI_TARS,
                "GUI 操作任务，路由到 UI-TARS（ScreenSpot 94.2%）",
            ),
            TaskType.DOCUMENT_UNDERSTANDING: (
                VLMBackend.QWEN3_VL_8B,
                "文档理解任务，路由到 Qwen3-VL-8B（256K 上下文）",
            ),
            TaskType.IMAGE_QA: (
                VLMBackend.QWEN3_VL_8B,
                "图片问答任务，路由到 Qwen3-VL-8B（通用 VLM）",
            ),
            TaskType.COMPLEX_OCR: (
                VLMBackend.QWEN3_VL_8B,
                "复杂 OCR 任务，路由到 Qwen3-VL-8B（32 语言 OCR）",
            ),
            TaskType.UNKNOWN: (
                VLMBackend.UI_TARS,
                "无法分类，默认路由到 UI-TARS（主模型）",
            ),
        }

        backend, reason = routing_map[task_type]
        return RoutingResult(task_type=task_type, backend=backend, reason=reason)

    def fallback_chain(self, primary: VLMBackend | None = None) -> list[VLMBackend]:
        """生成失败 fallback 链。

        UI-TARS → Qwen3-VL-8B → Qwen3-VL-4B → CALL_USER
        """
        if primary is None:
            primary = VLMBackend.UI_TARS

        chain = [primary]
        for backend in [VLMBackend.QWEN3_VL_8B, VLMBackend.QWEN3_VL_4B]:
            if backend not in chain:
                chain.append(backend)
        return chain


# ──────────────────────────────────────────────────────────────
# 单元测试
# ──────────────────────────────────────────────────────────────


if __name__ == "__main__":
    router = TaskRouter()

    test_cases = [
        ("点击桌面上的记事本图标", TaskType.GUI_OPERATION, VLMBackend.UI_TARS),
        ("在搜索框输入 AI 并回车", TaskType.GUI_OPERATION, VLMBackend.UI_TARS),
        ("总结这份 PDF 文档的内容", TaskType.DOCUMENT_UNDERSTANDING, VLMBackend.QWEN3_VL_8B),
        ("这张图里有什么动物", TaskType.IMAGE_QA, VLMBackend.QWEN3_VL_8B),
        ("提取这张表的所有文字", TaskType.COMPLEX_OCR, VLMBackend.QWEN3_VL_8B),
        ("帮我看看屏幕", TaskType.UNKNOWN, VLMBackend.UI_TARS),
    ]

    print("=== 任务路由测试 ===\n")
    for task, expected_type, expected_backend in test_cases:
        result = router.route(task)
        ok = (
            result.task_type == expected_type
            and result.backend == expected_backend
        )
        status = "✅" if ok else "❌"
        print(f"{status} {task}")
        print(f"   → {result.task_type.value} / {result.backend.value}")
        print(f"   理由: {result.reason}")

    print("\n=== Fallback 链 ===")
    chain = router.fallback_chain()
    for i, backend in enumerate(chain):
        print(f"  {i+1}. {backend.value}")
