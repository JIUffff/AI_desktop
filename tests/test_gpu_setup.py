"""GPU 环境初始化测试。

验证 PyTorch CUDA 环境、GPU 型号和基本张量运算。
"""

import pytest


def test_torch_import():
    """PyTorch 应成功导入。"""
    import torch

    assert torch.__version__ is not None


def test_cuda_available():
    """CUDA 应可用。"""
    import torch

    assert torch.cuda.is_available() is True


def test_gpu_name():
    """GPU 应为 RTX 5070 Ti。"""
    import torch

    name = torch.cuda.get_device_name(0)
    assert "NVIDIA GeForce RTX 5070 Ti" in name


def test_gpu_memory():
    """显存应 ≥ 15GB（允许少量系统占用）。"""
    import torch

    total_gb = torch.cuda.get_device_properties(0).total_memory / 1024**3
    assert total_gb >= 15.0


def test_tensor_operation_on_gpu():
    """应能在 GPU 上创建并运算张量。"""
    import torch

    x = torch.randn(100, 100, device="cuda")
    y = x @ x.T
    assert y.device.type == "cuda"
    assert y.shape == (100, 100)


def test_cuda_version():
    """CUDA 版本应为 12.8。"""
    import torch

    assert torch.version.cuda == "12.8"
