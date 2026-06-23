"""GPU 环境初始化脚本。验证 CUDA、GPU、PyTorch 是否正确安装。"""
import sys


def main():
    print("=== GPU 环境检查 ===\n")

    try:
        import torch
        print(f"[OK] PyTorch {torch.__version__}")
    except ImportError:
        print("[FAIL] PyTorch 未安装")
        print("  运行: pip install torch --index-url https://download.pytorch.org/whl/cu128")
        sys.exit(1)

    if not torch.cuda.is_available():
        print("[FAIL] CUDA 不可用")
        sys.exit(1)

    gpu_name = torch.cuda.get_device_name(0)
    gpu_mem = torch.cuda.get_device_properties(0).total_memory / 1024**3
    print(f"[OK] GPU: {gpu_name}")
    print(f"[OK] 显存: {gpu_mem:.1f} GB")
    print(f"[OK] CUDA: {torch.version.cuda}")

    # 测试张量运算
    x = torch.randn(100, 100, device="cuda")
    y = x @ x.T
    print(f"[OK] GPU 张量运算测试通过 (结果形状: {y.shape})")

    print("\n=== GPU 环境就绪 ===")


if __name__ == "__main__":
    main()
