"""统一 Action 数据类与适配层。

UI-TARS 输出 "Thought: ...\nAction: click(start_box='(100,200)')" 文本，
Qwen3-VL 输出自然语言文本。本模块将两者归一化为统一的 Action 数据类，
使上层调用方无需关心后端差异。

这是 VLMServer.switch_backend() 能真正工作的前提。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ──────────────────────────────────────────────────────────────
# 枚举定义
# ──────────────────────────────────────────────────────────────


class ActionType(str, Enum):
    """UI-TARS 支持的动作类型。"""

    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"
    DRAG = "drag"
    TYPE = "type"
    SCROLL = "scroll"
    KEY = "key"  # 键盘快捷键
    WAIT = "wait"
    FINISHED = "finished"
    CALL_USER = "call_user"  # 请求人工介入
    UNKNOWN = "unknown"


# ──────────────────────────────────────────────────────────────
# 统一 Action 数据类
# ──────────────────────────────────────────────────────────────


@dataclass
class Action:
    """统一的动作输出，所有后端的推理结果都归一化为此结构。

    Attributes:
        thought: 模型的思考过程（UI-TARS 的 Thought 字段）
        action_type: 动作类型枚举
        coordinates: 归一化坐标 [x, y]，范围 [0, 1]。
                     UI-TARS 输出 0-1000，适配时除以 1000。
                     非坐标动作（如 type）为 None。
        text: 文本输入内容（type 动作时填入）
        key_combo: 键盘快捷键（key 动作时填入，如 "ctrl+c"）
        scroll_amount: 滚动量（scroll 动作时填入，正向下负向上）
        confidence: 置信度 [0, 1]，部分后端不提供则为 None
        raw_output: 原始文本输出（调试用）
    """

    thought: str = ""
    action_type: ActionType = ActionType.UNKNOWN
    coordinates: list[float] | None = None  # [x, y] 归一化到 [0, 1]
    text: str | None = None
    key_combo: str | None = None
    scroll_amount: int | None = None
    confidence: float | None = None
    raw_output: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "thought": self.thought,
            "action_type": self.action_type.value,
            "coordinates": self.coordinates,
            "text": self.text,
            "key_combo": self.key_combo,
            "scroll_amount": self.scroll_amount,
            "confidence": self.confidence,
        }

    def validate(self) -> bool:
        """校验动作合法性。安全层调用此方法。"""
        # 坐标动作必须提供坐标，且范围合法
        if self.action_type in (
            ActionType.CLICK,
            ActionType.DOUBLE_CLICK,
            ActionType.RIGHT_CLICK,
            ActionType.DRAG,
        ):
            if self.coordinates is None:
                return False
            x, y = self.coordinates
            if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
                return False

        # type 动作必须提供文本
        if self.action_type == ActionType.TYPE and not self.text:
            return False

        # key 动作必须提供快捷键
        if self.action_type == ActionType.KEY and not self.key_combo:
            return False

        # scroll 动作必须提供滚动量
        if self.action_type == ActionType.SCROLL and self.scroll_amount is None:
            return False

        return True


# ──────────────────────────────────────────────────────────────
# UI-TARS 适配器
# ──────────────────────────────────────────────────────────────


# UI-TARS 输出格式示例：
# Thought: Click the button
# Action: click(start_box='(100,200)')

_THOUGHT_PATTERN = re.compile(r"Thought:\s*(.*?)(?=\nAction:|$)", re.DOTALL)
_ACTION_PATTERN = re.compile(r"Action:\s*(\w+)\s*\(([^)]*)\)", re.DOTALL)
_COORD_PATTERN = re.compile(r"\(?(\d+)\s*,\s*(\d+)\)?")


def parse_ui_tars_output(raw: str) -> Action:
    """解析 UI-TARS 文本输出为统一 Action。

    UI-TARS 坐标系：0-1000 归一化，适配时除以 1000 转为 [0, 1]。
    """
    thought_match = _THOUGHT_PATTERN.search(raw)
    thought = thought_match.group(1).strip() if thought_match else ""

    action_match = _ACTION_PATTERN.search(raw)
    if not action_match:
        return Action(
            thought=thought,
            action_type=ActionType.UNKNOWN,
            raw_output=raw,
        )

    action_name = action_match.group(1).lower()
    action_args = action_match.group(2)

    # 映射动作类型
    type_map = {
        "click": ActionType.CLICK,
        "double_click": ActionType.DOUBLE_CLICK,
        "right_click": ActionType.RIGHT_CLICK,
        "drag": ActionType.DRAG,
        "type": ActionType.TYPE,
        "scroll": ActionType.SCROLL,
        "key": ActionType.KEY,
        "wait": ActionType.WAIT,
        "finished": ActionType.FINISHED,
        "call_user": ActionType.CALL_USER,
    }
    action_type = type_map.get(action_name, ActionType.UNKNOWN)

    # 解析参数
    coordinates = None
    text = None
    key_combo = None
    scroll_amount = None

    if action_type in (
        ActionType.CLICK,
        ActionType.DOUBLE_CLICK,
        ActionType.RIGHT_CLICK,
        ActionType.DRAG,
    ):
        # 提取坐标：(100, 200) → [0.1, 0.2]
        coord_match = _COORD_PATTERN.search(action_args)
        if coord_match:
            x_norm = int(coord_match.group(1)) / 1000.0
            y_norm = int(coord_match.group(2)) / 1000.0
            coordinates = [x_norm, y_norm]

    elif action_type == ActionType.TYPE:
        # 提取文本：content='Hello World'
        text_match = re.search(r"content=['\"](.+?)['\"]", action_args)
        if text_match:
            text = text_match.group(1)

    elif action_type == ActionType.KEY:
        # 提取快捷键：content='ctrl+c'
        key_match = re.search(r"content=['\"](.+?)['\"]", action_args)
        if key_match:
            key_combo = key_match.group(1)

    elif action_type == ActionType.SCROLL:
        # 提取滚动量：direction='down' or amount=5
        direction_match = re.search(r"direction=['\"](\w+)['\"]", action_args)
        amount_match = re.search(r"amount=(\d+)", action_args)
        if direction_match:
            direction = direction_match.group(1).lower()
            scroll_amount = 3 if direction == "down" else -3
        elif amount_match:
            scroll_amount = int(amount_match.group(1))
        else:
            scroll_amount = 3  # 默认向下滚动 3 格

    return Action(
        thought=thought,
        action_type=action_type,
        coordinates=coordinates,
        text=text,
        key_combo=key_combo,
        scroll_amount=scroll_amount,
        raw_output=raw,
    )


# ──────────────────────────────────────────────────────────────
# Qwen3-VL 适配器
# ──────────────────────────────────────────────────────────────


def parse_qwen3vl_output(raw: str) -> Action:
    """解析 Qwen3-VL 自然语言输出为统一 Action。

    Qwen3-VL 不是原生 GUI Agent，输出为自然语言文本。
    需要二次解析或正则匹配。置信度较低。

    策略：优先匹配 UI-TARS 格式（若 Qwen3-VL 被引导输出此格式），
    否则尝试从自然语言提取动作意图。
    """
    # 优先尝试 UI-TARS 格式（如果 prompt 引导 Qwen3-VL 模仿该格式）
    if "Action:" in raw and "Thought:" in raw:
        action = parse_ui_tars_output(raw)
        action.confidence = 0.7  # Qwen3-VL 模仿格式，置信度略低
        return action

    # 降级：自然语言解析
    thought = raw.strip()
    action_type = ActionType.UNKNOWN
    coordinates = None
    text = None

    raw_lower = raw.lower()

    # 简单关键词匹配（精度有限，仅作 fallback）
    if any(kw in raw_lower for kw in ["点击", "click", "按下"]):
        action_type = ActionType.CLICK
        # 尝试提取坐标
        coord_match = _COORD_PATTERN.search(raw)
        if coord_match:
            x_norm = int(coord_match.group(1)) / 1000.0
            y_norm = int(coord_match.group(2)) / 1000.0
            coordinates = [x_norm, y_norm]
    elif any(kw in raw_lower for kw in ["输入", "type", "打字"]):
        action_type = ActionType.TYPE
        text_match = re.search(r"['\"](.+?)['\"]", raw)
        if text_match:
            text = text_match.group(1)
    elif any(kw in raw_lower for kw in ["完成", "finished", "done"]):
        action_type = ActionType.FINISHED
    elif any(kw in raw_lower for kw in ["无法", "需要帮助", "call_user"]):
        action_type = ActionType.CALL_USER

    return Action(
        thought=thought,
        action_type=action_type,
        coordinates=coordinates,
        text=text,
        confidence=0.5,  # 自然语言解析置信度低
        raw_output=raw,
    )


# ──────────────────────────────────────────────────────────────
# 适配器工厂
# ──────────────────────────────────────────────────────────────


def parse_output(backend: str, raw: str) -> Action:
    """根据后端名称选择适配器。

    Args:
        backend: "ui-tars" 或 "qwen3-vl-8b" 或 "qwen3-vl-4b"
        raw: 模型原始文本输出

    Returns:
        统一的 Action 对象
    """
    if backend.startswith("ui-tars"):
        return parse_ui_tars_output(raw)
    elif backend.startswith("qwen3-vl"):
        return parse_qwen3vl_output(raw)
    else:
        raise ValueError(f"未知后端：{backend}")


# ──────────────────────────────────────────────────────────────
# 单元测试（可直接运行验证）
# ──────────────────────────────────────────────────────────────


if __name__ == "__main__":
    # 测试 UI-TARS 解析
    test_cases = [
        (
            "Thought: 我需要点击搜索框\nAction: click(start_box='(450,200)')",
            ActionType.CLICK,
            [0.45, 0.2],
        ),
        (
            "Thought: 输入搜索关键词\nAction: type(content='AI PC Control')",
            ActionType.TYPE,
            None,
        ),
        (
            "Thought: 按下回车键\nAction: key(content='enter')",
            ActionType.KEY,
            None,
        ),
        (
            "Thought: 任务已完成\nAction: finished()",
            ActionType.FINISHED,
            None,
        ),
    ]

    print("=== UI-TARS 解析测试 ===\n")
    for raw, expected_type, expected_coord in test_cases:
        action = parse_ui_tars_output(raw)
        ok = action.action_type == expected_type
        if expected_coord:
            ok = ok and action.coordinates == expected_coord
        status = "✅" if ok else "❌"
        print(f"{status} {action.action_type.value:15s} coord={action.coordinates} text={action.text}")
        print(f"   thought: {action.thought[:50]}...")

    # 测试 Qwen3-VL 解析
    print("\n=== Qwen3-VL 解析测试 ===\n")
    qwen_tests = [
        "我建议点击屏幕中央的搜索按钮",
        "任务已完成，所有步骤执行成功",
    ]
    for raw in qwen_tests:
        action = parse_qwen3vl_output(raw)
        print(f"  type={action.action_type.value:15s} conf={action.confidence} text={action.text}")
