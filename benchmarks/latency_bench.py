"""基准测试：UI-TARS-1.5-7B 本地推理性能验证。

验证 PRD AC：
- AC-06: 单步操作延迟 < 1.5s（截图→决策→执行）
- AC-07: GPU 显存占用峰值 < 15GB
- AC-08: 连续运行 30 分钟无显存泄漏

使用方法：
    # 准备 20-30 张标准测试截图到 benchmarks/screenshots/
    uv run python benchmarks/latency_bench.py

    # 仅测试延迟（跳过长时间泄漏测试）
    uv run python benchmarks/latency_bench.py --skip-leak-test

    # 指定后端
    uv run python benchmarks/latency_bench.py --backend ui-tars
    uv run python benchmarks/latency_bench.py --backend qwen3-vl-8b
"""
from __future__ import annotations

import argparse
import json
import statistics
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
SCREENSHOTS_DIR = PROJECT_ROOT / "benchmarks" / "screenshots"
RESULTS_DIR = PROJECT_ROOT / "benchmarks" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


# ──────────────────────────────────────────────────────────────
# 数据结构
# ──────────────────────────────────────────────────────────────


@dataclass
class SingleRunResult:
    """单次推理结果。"""

    screenshot: str
    task: str
    latency_ms: float
    gpu_mem_gb: float
    success: bool
    error: str | None = None
    output_preview: str = ""  # 截取前 200 字符


@dataclass
class BenchmarkSummary:
    """基准测试汇总。"""

    backend: str
    model_name: str
    total_runs: int
    success_count: int

    # 延迟统计（毫秒）
    latency_p50_ms: float
    latency_p95_ms: float
    latency_p99_ms: float
    latency_mean_ms: float
    latency_min_ms: float
    latency_max_ms: float

    # 显存统计（GB）
    gpu_mem_peak_gb: float
    gpu_mem_mean_gb: float

    # AC 验收
    ac_06_pass: bool  # P95 < 1500ms
    ac_07_pass: bool  # peak < 15GB

    # 明细
    runs: list[SingleRunResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["runs"] = [asdict(r) for r in self.runs]
        return d


# ──────────────────────────────────────────────────────────────
# 测试用例定义
# ──────────────────────────────────────────────────────────────


# 标准测试任务集（与 screenshots/*.png 一一对应）
# 命名约定：screenshot_01.png → task_01
STANDARD_TASKS: list[dict[str, str]] = [
    {"screenshot": "desktop_idle.png", "task": "打开记事本应用"},
    {"screenshot": "notepad_empty.png", "task": "在记事本中输入 Hello World"},
    {"screenshot": "browser_home.png", "task": "在搜索框中输入 AI 并回车"},
    {"screenshot": "file_explorer.png", "task": "选中所有 .png 文件"},
    {"screenshot": "settings_panel.png", "task": "点击系统设置中的显示选项"},
    {"screenshot": "dialog_confirm.png", "task": "点击确认按钮保存文件"},
    {"screenshot": "ide_vscode.png", "task": "打开终端面板"},
    {"screenshot": "excel_data.png", "task": "选中 A1 到 C10 单元格区域"},
    {"screenshot": "mail_client.png", "task": "点击新建邮件按钮"},
    {"screenshot": "taskbar.png", "task": "点击任务栏第三个图标"},
    # 可继续扩展到 20-30 个
]


# ──────────────────────────────────────────────────────────────
# GPU 监控（轻量级，不依赖额外包）
# ──────────────────────────────────────────────────────────────


def get_gpu_memory_gb() -> float:
    """返回当前 GPU 已用显存（GB）。"""
    try:
        import torch

        if not torch.cuda.is_available():
            return 0.0
        return torch.cuda.memory_allocated() / 1024**3  # bytes → GB
    except Exception:
        return 0.0


def get_gpu_peak_gb() -> float:
    """返回 GPU 峰值显存（GB），并重置峰值计数器。"""
    try:
        import torch

        if not torch.cuda.is_available():
            return 0.0
        peak = torch.cuda.max_memory_allocated() / 1024**3
        torch.cuda.reset_peak_memory_stats()
        return peak
    except Exception:
        return 0.0


# ──────────────────────────────────────────────────────────────
# 推理后端抽象
# ──────────────────────────────────────────────────────────────


class InferenceBackend:
    """推理后端抽象基类。子类实现 _infer_raw。"""

    def __init__(self, name: str, model_name: str) -> None:
        self.name = name
        self.model_name = model_name
        self._model = None
        self._processor = None

    def load(self) -> None:
        """加载模型到 GPU。子类实现。"""
        raise NotImplementedError

    def unload(self) -> None:
        """卸载模型，释放显存。"""
        import gc

        import torch

        self._model = None
        self._processor = None
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def infer(self, screenshot_path: str, task: str) -> tuple[str, float]:
        """
        执行一次推理。

        Returns:
            (output_text, latency_ms)
        """
        t0 = time.perf_counter()
        output = self._infer_raw(screenshot_path, task)
        latency_ms = (time.perf_counter() - t0) * 1000
        return output, latency_ms

    def _infer_raw(self, screenshot_path: str, task: str) -> str:
        raise NotImplementedError


class UITarsBackend(InferenceBackend):
    """UI-TARS-1.5-7B 后端。"""

    def __init__(self) -> None:
        super().__init__("ui-tars", "ByteDance-Seed/UI-TARS-1.5-7B")

    def load(self) -> None:
        """加载 UI-TARS 模型。MVP 阶段用 transformers + FP16。

        注：AWQ INT4 量化需在 model-deployment.md §3.1 配置就绪后启用。
        """
        import torch
        from transformers import AutoModelForCausalLM, AutoProcessor

        model_path = str(PROJECT_ROOT / "models" / "ui-tars-1.5-7b")
        self._model = AutoModelForCausalLM.from_pretrained(
            model_path if Path(model_path).exists() else self.model_name,
            device_map="auto",
            torch_dtype=torch.float16,
            trust_remote_code=True,
        )
        self._processor = AutoProcessor.from_pretrained(
            model_path if Path(model_path).exists() else self.model_name,
            trust_remote_code=True,
        )

    def _infer_raw(self, screenshot_path: str, task: str) -> str:
        from PIL import Image

        image = Image.open(screenshot_path)
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": task},
                ],
            }
        ]
        inputs = self._processor.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        ).to(self._model.device)

        import torch

        with torch.no_grad():
            output_ids = self._model.generate(**inputs, max_new_tokens=512)

        # 解码输出（跳过输入部分）
        input_len = inputs["input_ids"].shape[1]
        output = self._processor.decode(
            output_ids[0][input_len:], skip_special_tokens=True
        )
        return output


class Qwen3VLBackend(InferenceBackend):
    """Qwen3-VL-8B-Instruct 后端（备选）。"""

    def __init__(self) -> None:
        super().__init__("qwen3-vl-8b", "Qwen/Qwen3-VL-8B-Instruct")

    def load(self) -> None:
        import torch
        from transformers import AutoModelForCausalLM, AutoProcessor

        model_path = str(PROJECT_ROOT / "models" / "qwen3-vl-8b")
        self._model = AutoModelForCausalLM.from_pretrained(
            model_path if Path(model_path).exists() else self.model_name,
            device_map="auto",
            torch_dtype=torch.float16,
            trust_remote_code=True,
        )
        self._processor = AutoProcessor.from_pretrained(
            model_path if Path(model_path).exists() else self.model_name,
            trust_remote_code=True,
        )

    def _infer_raw(self, screenshot_path: str, task: str) -> str:
        from PIL import Image

        image = Image.open(screenshot_path)
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": task},
                ],
            }
        ]
        inputs = self._processor.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        ).to(self._model.device)

        import torch

        with torch.no_grad():
            output_ids = self._model.generate(**inputs, max_new_tokens=512)

        input_len = inputs["input_ids"].shape[1]
        output = self._processor.decode(
            output_ids[0][input_len:], skip_special_tokens=True
        )
        return output


BACKENDS = {
    "ui-tars": UITarsBackend,
    "qwen3-vl-8b": Qwen3VLBackend,
}


# ──────────────────────────────────────────────────────────────
# 基准测试主流程
# ──────────────────────────────────────────────────────────────


def percentile(sorted_values: list[float], p: float) -> float:
    """计算百分位数。p ∈ [0, 100]。"""
    if not sorted_values:
        return 0.0
    k = (len(sorted_values) - 1) * (p / 100)
    f = int(k)
    c = min(f + 1, len(sorted_values) - 1)
    if f == c:
        return sorted_values[f]
    return sorted_values[f] + (sorted_values[c] - sorted_values[f]) * (k - f)


def run_benchmark(backend: InferenceBackend, tasks: list[dict[str, str]]) -> BenchmarkSummary:
    """对给定后端跑完整基准测试。"""
    print(f"\n{'=' * 60}")
    print(f"  基准测试：{backend.name} ({backend.model_name})")
    print(f"  任务数：{len(tasks)}")
    print(f"{'=' * 60}")

    print("\n[1/3] 加载模型...")
    backend.load()
    print(f"  模型加载完成，显存占用：{get_gpu_memory_gb():.2f} GB")

    print("\n[2/3] 推理测试...")
    runs: list[SingleRunResult] = []
    gpu_mem_samples: list[float] = []

    for i, task_def in enumerate(tasks, 1):
        screenshot_path = SCREENSHOTS_DIR / task_def["screenshot"]
        task_text = task_def["task"]

        if not screenshot_path.exists():
            print(f"  [{i}/{len(tasks)}] 跳过（截图缺失）：{screenshot_path.name}")
            runs.append(
                SingleRunResult(
                    screenshot=screenshot_path.name,
                    task=task_text,
                    latency_ms=0.0,
                    gpu_mem_gb=0.0,
                    success=False,
                    error="screenshot_not_found",
                )
            )
            continue

        try:
            output, latency_ms = backend.infer(str(screenshot_path), task_text)
            gpu_mem = get_gpu_memory_gb()
            gpu_mem_samples.append(gpu_mem)

            success = bool(output and len(output.strip()) > 0)
            runs.append(
                SingleRunResult(
                    screenshot=screenshot_path.name,
                    task=task_text,
                    latency_ms=latency_ms,
                    gpu_mem_gb=gpu_mem,
                    success=success,
                    output_preview=output[:200],
                )
            )
            status = "OK" if success else "EMPTY"
            print(
                f"  [{i}/{len(tasks)}] {status} {latency_ms:7.1f}ms  "
                f"mem={gpu_mem:.2f}GB  {screenshot_path.name}"
            )
        except Exception as e:
            runs.append(
                SingleRunResult(
                    screenshot=screenshot_path.name,
                    task=task_text,
                    latency_ms=0.0,
                    gpu_mem_gb=get_gpu_memory_gb(),
                    success=False,
                    error=str(e),
                )
            )
            print(f"  [{i}/{len(tasks)}] FAIL {screenshot_path.name}: {e}")

    print("\n[3/3] 卸载模型...")
    backend.unload()
    print(f"  模型卸载完成，显存占用：{get_gpu_memory_gb():.2f} GB")

    # 计算汇总
    successful_runs = [r for r in runs if r.success]
    latencies = sorted([r.latency_ms for r in successful_runs])

    if latencies:
        summary = BenchmarkSummary(
            backend=backend.name,
            model_name=backend.model_name,
            total_runs=len(runs),
            success_count=len(successful_runs),
            latency_p50_ms=percentile(latencies, 50),
            latency_p95_ms=percentile(latencies, 95),
            latency_p99_ms=percentile(latencies, 99),
            latency_mean_ms=statistics.mean(latencies),
            latency_min_ms=latencies[0],
            latency_max_ms=latencies[-1],
            gpu_mem_peak_gb=max(gpu_mem_samples) if gpu_mem_samples else 0.0,
            gpu_mem_mean_gb=statistics.mean(gpu_mem_samples) if gpu_mem_samples else 0.0,
            ac_06_pass=percentile(latencies, 95) < 1500.0,
            ac_07_pass=(max(gpu_mem_samples) if gpu_mem_samples else 0.0) < 15.0,
            runs=runs,
        )
    else:
        summary = BenchmarkSummary(
            backend=backend.name,
            model_name=backend.model_name,
            total_runs=len(runs),
            success_count=0,
            latency_p50_ms=0.0,
            latency_p95_ms=0.0,
            latency_p99_ms=0.0,
            latency_mean_ms=0.0,
            latency_min_ms=0.0,
            latency_max_ms=0.0,
            gpu_mem_peak_gb=0.0,
            gpu_mem_mean_gb=0.0,
            ac_06_pass=False,
            ac_07_pass=False,
            runs=runs,
        )

    return summary


def print_summary(summary: BenchmarkSummary) -> None:
    """打印基准测试汇总。"""
    print(f"\n{'=' * 60}")
    print(f"  汇总：{summary.backend}")
    print(f"{'=' * 60}")
    print(f"  成功率：        {summary.success_count}/{summary.total_runs} "
          f"({summary.success_count / summary.total_runs * 100:.1f}%)")
    print(f"\n  延迟统计（毫秒）：")
    print(f"    P50:  {summary.latency_p50_ms:8.1f} ms")
    print(f"    P95:  {summary.latency_p95_ms:8.1f} ms   {'✅ PASS' if summary.ac_06_pass else '❌ FAIL'} (AC-06: <1500ms)")
    print(f"    P99:  {summary.latency_p99_ms:8.1f} ms")
    print(f"    Mean: {summary.latency_mean_ms:8.1f} ms")
    print(f"    Min:  {summary.latency_min_ms:8.1f} ms")
    print(f"    Max:  {summary.latency_max_ms:8.1f} ms")
    print(f"\n  显存统计（GB）：")
    print(f"    Peak: {summary.gpu_mem_peak_gb:8.2f} GB  {'✅ PASS' if summary.ac_07_pass else '❌ FAIL'} (AC-07: <15GB)")
    print(f"    Mean: {summary.gpu_mem_mean_gb:8.2f} GB")
    print(f"{'=' * 60}")


def save_results(summary: BenchmarkSummary) -> Path:
    """保存结果到 JSON。"""
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    result_file = RESULTS_DIR / f"bench_{summary.backend}_{timestamp}.json"
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(summary.to_dict(), f, ensure_ascii=False, indent=2)
    return result_file


# ──────────────────────────────────────────────────────────────
# 入口
# ──────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="UI-TARS 本地推理基准测试")
    parser.add_argument(
        "--backend",
        choices=list(BACKENDS.keys()),
        default="ui-tars",
        help="推理后端（默认 ui-tars）",
    )
    parser.add_argument(
        "--skip-leak-test",
        action="store_true",
        help="跳过 30 分钟显存泄漏测试（AC-08）",
    )
    parser.add_argument(
        "--tasks",
        type=int,
        default=0,
        help="仅跑前 N 个任务（0=全部）",
    )
    args = parser.parse_args()

    # 选择任务
    tasks = STANDARD_TASKS
    if args.tasks > 0:
        tasks = tasks[: args.tasks]

    # 检查截图目录
    if not SCREENSHOTS_DIR.exists():
        SCREENSHOTS_DIR.mkdir(parents=True)
        print(f"[提示] 已创建截图目录：{SCREENSHOTS_DIR}")
        print("       请放入对应的标准测试截图后再运行基准测试。")
        print("       参见 benchmarks/README.md 了解截图命名规范。")
        return

    # 创建后端
    backend = BACKENDS[args.backend]()

    # 跑基准
    summary = run_benchmark(backend, tasks)
    print_summary(summary)

    # 保存
    result_file = save_results(summary)
    print(f"\n结果已保存：{result_file}")

    # AC-08 显存泄漏测试（可选）
    if not args.skip_leak_test and summary.success_count > 0:
        print("\n[AC-08] 30 分钟显存泄漏测试（按 Ctrl+C 跳过）...")
        try:
            run_leak_test(backend, tasks)
        except KeyboardInterrupt:
            print("  用户中断，跳过泄漏测试。")


def run_leak_test(backend: InferenceBackend, tasks: list[dict[str, str]]) -> None:
    """AC-08：连续运行 30 分钟，检查显存泄漏。"""
    import datetime

    duration_min = 30
    start = time.time()
    end = start + duration_min * 60
    iteration = 0
    mem_samples: list[float] = []

    backend.load()
    initial_mem = get_gpu_memory_gb()
    print(f"  初始显存：{initial_mem:.2f} GB")

    while time.time() < end:
        iteration += 1
        task = tasks[iteration % len(tasks)]
        screenshot_path = SCREENSHOTS_DIR / task["screenshot"]

        if not screenshot_path.exists():
            continue

        try:
            backend.infer(str(screenshot_path), task["task"])
        except Exception:
            pass

        mem = get_gpu_memory_gb()
        mem_samples.append(mem)

        elapsed = time.time() - start
        remaining = duration_min * 60 - elapsed
        if iteration % 10 == 0:
            delta = mem - initial_mem
            print(
                f"  iter={iteration:4d}  elapsed={elapsed/60:.1f}min  "
                f"mem={mem:.2f}GB  Δ={delta:+.2f}GB  "
                f"remaining={remaining/60:.1f}min"
            )

    backend.unload()
    final_mem = get_gpu_memory_gb()

    # 判定：显存增长 < 0.5GB 视为无泄漏
    max_mem = max(mem_samples) if mem_samples else initial_mem
    leak = max_mem - initial_mem
    passed = leak < 0.5

    print(f"\n  AC-08 结果：{'✅ PASS' if passed else '❌ FAIL'}")
    print(f"    初始显存：{initial_mem:.2f} GB")
    print(f"    峰值显存：{max_mem:.2f} GB")
    print(f"    泄漏量：  {leak:+.2f} GB（阈值 <0.5GB）")
    print(f"    迭代次数：{iteration}")


if __name__ == "__main__":
    main()
