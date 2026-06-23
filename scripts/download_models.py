"""下载所需模型权重到 models/ 目录。"""
from pathlib import Path

MODELS_DIR = Path(__file__).parent.parent / "models"
MODELS_DIR.mkdir(exist_ok=True)


def main():
    print("=== 下载模型 ===\n")

    # 1. Qwen2-VL-7B
    print("[1/3] Qwen2-VL-7B-Instruct...")
    from huggingface_hub import snapshot_download
    snapshot_download(
        "Qwen/Qwen2-VL-7B-Instruct",
        local_dir=MODELS_DIR / "qwen2-vl-7b",
    )
    print("  [OK]")

    # 2. YOLOv8m
    print("[2/3] YOLOv8m...")
    from ultralytics import YOLO
    model = YOLO("yolov8m.pt")
    model.save(str(MODELS_DIR / "yolov8m-ui.pt"))
    print("  [OK]")

    # 3. PaddleOCR
    print("[3/3] PaddleOCR (首次使用自动下载)...")
    print("  [OK] 跳过（PaddleOCR 首次调用时自动下载）")

    print("\n=== 模型下载完成 ===")


if __name__ == "__main__":
    main()
