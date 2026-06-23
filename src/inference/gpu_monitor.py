"""GPU 显存监控器：后台线程定期检查显存。"""
from __future__ import annotations

import logging
import threading
import time

logger = logging.getLogger(__name__)


class GPUMonitor:
    """后台线程，定期检查 GPU 显存占用。

    Usage:
        monitor = GPUMonitor(interval=5)
        monitor.start()
        # ... 运行期间 ...
        usage = monitor.get_current_usage()
        monitor.stop()
    """

    def __init__(self, interval: float = 5.0) -> None:
        """初始化。

        Args:
            interval: 检查间隔（秒），默认 5 秒
        """
        self.interval = interval
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._current_usage: dict[str, float] = {"allocated_gb": 0.0, "peak_gb": 0.0}
        self._lock = threading.Lock()

    def start(self) -> None:
        """启动监控线程。"""
        if self._thread is not None and self._thread.is_alive():
            logger.warning("GPUMonitor 已在运行")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="gpu-monitor")
        self._thread.start()
        logger.info("GPU 监控已启动（间隔 %ss）", self.interval)

    def stop(self) -> None:
        """停止监控线程。"""
        if self._thread is None:
            return

        self._stop_event.set()
        self._thread.join(timeout=2.0)
        self._thread = None
        logger.info("GPU 监控已停止")

    def get_current_usage(self) -> dict[str, float]:
        """返回当前显存使用情况。

        Returns:
            {"allocated_gb": float, "peak_gb": float}
        """
        with self._lock:
            return self._current_usage.copy()

    def _run(self) -> None:
        """监控线程主循环。"""
        while not self._stop_event.is_set():
            usage = self._sample_gpu()
            with self._lock:
                self._current_usage = usage
            self._stop_event.wait(self.interval)

    def _sample_gpu(self) -> dict[str, float]:
        """采样一次 GPU 显存。"""
        try:
            import torch

            if not torch.cuda.is_available():
                return {"allocated_gb": 0.0, "peak_gb": 0.0}

            allocated = torch.cuda.memory_allocated() / 1024**3
            peak = torch.cuda.max_memory_allocated() / 1024**3
            return {"allocated_gb": round(allocated, 3), "peak_gb": round(peak, 3)}
        except Exception as e:
            logger.debug("GPU 采样失败：%s", e)
            return {"allocated_gb": 0.0, "peak_gb": 0.0}


# ──────────────────────────────────────────────────────────────
# 便捷函数
# ──────────────────────────────────────────────────────────────


def get_gpu_info() -> dict[str, str]:
    """获取 GPU 基本信息（一次性，非持续监控）。"""
    try:
        import torch

        if not torch.cuda.is_available():
            return {"status": "CUDA 不可用"}

        props = torch.cuda.get_device_properties(0)
        return {
            "status": "OK",
            "name": props.name,
            "total_memory_gb": f"{props.total_memory / 1024**3:.1f}",
            "cuda_version": torch.version.cuda or "unknown",
            "torch_version": torch.__version__,
        }
    except Exception as e:
        return {"status": f"错误：{e}"}


if __name__ == "__main__":
    info = get_gpu_info()
    print("=== GPU 信息 ===")
    for k, v in info.items():
        print(f"  {k}: {v}")

    print("\n=== 显存监控测试（10 秒）===")
    monitor = GPUMonitor(interval=2)
    monitor.start()

    import time as _time

    for _ in range(5):
        _time.sleep(2)
        usage = monitor.get_current_usage()
        print(f"  allocated={usage['allocated_gb']:.3f}GB  peak={usage['peak_gb']:.3f}GB")

    monitor.stop()
    print("\n=== 测试完成 ===")
