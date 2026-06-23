"""可观测性模块：推理链路追踪 + Token 消耗统计。

与 safety/audit_log.py 的区别：
- audit_log: 合规日志，记录"做了什么动作、结果如何"，面向审计
- trace_log: 调试日志，记录"模型怎么思考的、耗时多少、显存多少"，面向开发

写入路径：logs/trace_YYYY-MM-DD.jsonl（追加模式）
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


# ──────────────────────────────────────────────────────────────
# 数据结构
# ──────────────────────────────────────────────────────────────


@dataclass
class TraceEntry:
    """单步推理的完整追踪记录。"""

    # 标识
    trace_id: str  # 任务级唯一 ID
    step_id: int  # 步骤序号（从 1 开始）
    timestamp: str  # ISO 8601

    # 输入
    task: str  # 当前任务描述
    screenshot_path: str  # 截图文件路径

    # 模型信息
    backend: str  # "ui-tars" / "qwen3-vl-8b"
    model_name: str

    # 输出（经 action_schema 归一化）
    action_type: str  # CLICK / TYPE / SCROLL / ...
    thought: str  # 模型思考过程
    coordinates: list[float] | None = None
    text: str | None = None
    confidence: float | None = None
    raw_output: str = ""  # 原始输出（前 500 字符）

    # 性能指标
    latency_ms: float = 0.0  # 推理延迟
    gpu_mem_gb: float = 0.0  # 推理时显存占用
    gpu_peak_gb: float = 0.0  # 本次推理的峰值显存

    # Token 统计（vLLM 返回）
    prompt_tokens: int = 0  # 输入 token 数
    completion_tokens: int = 0  # 输出 token 数
    total_tokens: int = 0

    # 状态
    success: bool = True
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ──────────────────────────────────────────────────────────────
# TraceLogger
# ──────────────────────────────────────────────────────────────


class TraceLogger:
    """推理链路追踪日志器。

    每步推理记录一条 TraceEntry，写入 JSONL 文件。
    与 AuditLogger 互补：TraceLogger 面向开发调试，AuditLogger 面向合规审计。

    Usage:
        logger = TraceLogger()
        logger.start_task("open_notepad")
        entry = logger.create_entry(step_id=1, task="...", screenshot_path="...")
        # ... 执行推理 ...
        entry.latency_ms = 380.5
        entry.action_type = "click"
        entry.thought = "..."
        logger.log(entry)
    """

    def __init__(self, log_dir: str = "logs") -> None:
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._trace_id: str = ""
        self._step_counter: int = 0

    def start_task(self, trace_id: str) -> None:
        """开始一个新任务的追踪。"""
        self._trace_id = trace_id
        self._step_counter = 0

    def create_entry(
        self,
        step_id: int | None = None,
        task: str = "",
        screenshot_path: str = "",
        backend: str = "",
        model_name: str = "",
    ) -> TraceEntry:
        """创建一条追踪记录（推理前调用，推理后填充字段）。"""
        if step_id is None:
            self._step_counter += 1
            step_id = self._step_counter

        return TraceEntry(
            trace_id=self._trace_id,
            step_id=step_id,
            timestamp=datetime.now().isoformat(),
            task=task,
            screenshot_path=screenshot_path,
            backend=backend,
            model_name=model_name,
        )

    def log(self, entry: TraceEntry) -> None:
        """写入一条追踪记录到 JSONL 文件。"""
        log_file = self.log_dir / f"trace_{datetime.now().strftime('%Y-%m-%d')}.jsonl"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")


# ──────────────────────────────────────────────────────────────
# TokenUsage 统计
# ──────────────────────────────────────────────────────────────


@dataclass
class TokenUsage:
    """Token 消耗统计（单次会话累计）。"""

    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens: int = 0
    step_count: int = 0

    def add(self, prompt_tokens: int, completion_tokens: int) -> None:
        """累加一次推理的 token 消耗。"""
        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens
        self.total_tokens += prompt_tokens + completion_tokens
        self.step_count += 1

    @property
    def avg_tokens_per_step(self) -> float:
        if self.step_count == 0:
            return 0.0
        return self.total_tokens / self.step_count

    def summary(self) -> dict[str, Any]:
        return {
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_tokens,
            "step_count": self.step_count,
            "avg_tokens_per_step": round(self.avg_tokens_per_step, 1),
        }


# ──────────────────────────────────────────────────────────────
# 异常告警
# ──────────────────────────────────────────────────────────────


class AlertChecker:
    """异常告警规则（本地系统，仅打印告警，不发邮件/短信）。"""

    # 告警阈值
    LATENCY_WARN_MS = 1500.0  # 单步延迟告警（AC-06 上限）
    LATENCY_CRITICAL_MS = 3000.0  # 单步延迟严重告警
    GPU_MEM_WARN_GB = 14.0  # 显存告警（AC-07 接近上限）
    GPU_MEM_CRITICAL_GB = 15.5  # 显存严重告警
    CONFIDENCE_WARN = 0.5  # 置信度告警

    @classmethod
    def check_entry(cls, entry: TraceEntry) -> list[str]:
        """检查一条追踪记录，返回告警消息列表。"""
        alerts: list[str] = []

        # 延迟告警
        if entry.latency_ms > cls.LATENCY_CRITICAL_MS:
            alerts.append(
                f"[CRITICAL] 延迟 {entry.latency_ms:.0f}ms 超过 {cls.LATENCY_CRITICAL_MS}ms"
            )
        elif entry.latency_ms > cls.LATENCY_WARN_MS:
            alerts.append(
                f"[WARN] 延迟 {entry.latency_ms:.0f}ms 超过 {cls.LATENCY_WARN_MS}ms (AC-06)"
            )

        # 显存告警
        if entry.gpu_mem_gb > cls.GPU_MEM_CRITICAL_GB:
            alerts.append(
                f"[CRITICAL] 显存 {entry.gpu_mem_gb:.2f}GB 接近上限 (AC-07)"
            )
        elif entry.gpu_mem_gb > cls.GPU_MEM_WARN_GB:
            alerts.append(
                f"[WARN] 显存 {entry.gpu_mem_gb:.2f}GB 超过 {cls.GPU_MEM_WARN_GB}GB"
            )

        # 置信度告警
        if entry.confidence is not None and entry.confidence < cls.CONFIDENCE_WARN:
            alerts.append(
                f"[WARN] 置信度 {entry.confidence:.2f} 低于 {cls.CONFIDENCE_WARN}"
            )

        # 错误告警
        if not entry.success:
            alerts.append(f"[ERROR] 推理失败：{entry.error}")

        return alerts

    @classmethod
    def print_alerts(cls, entry: TraceEntry) -> None:
        """打印告警到控制台。"""
        for alert in cls.check_entry(entry):
            print(f"  ⚠️ {alert}  [step={entry.step_id} trace={entry.trace_id}]")
