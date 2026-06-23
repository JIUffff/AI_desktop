"""下载所需模型权重到 models/ 目录。

2026-06-23 更新（架构重构后）：
- 主模型：UI-TARS-1.5-7B（GUI Agent SOTA，端到端）
- 备选模型：Qwen3-VL-8B-Instruct（通用 VLM）
- 可选插件：YOLO11m（按需 lazy-load，非主流程）
- 已移除：PaddleOCR（UI-TARS 内置 OCR）、SoM 标注模块
"""
import os
import sys
from pathlib import Path

MODELS_DIR = Path(__file__).parent.parent / "models"
MODELS_DIR.mkdir(exist_ok=True)


def check_proxy():
    """检查代理配置，未设置则警告。"""
    http_proxy = os.environ.get("HTTP_PROXY", "")
    https_proxy = os.environ.get("HTTPS_PROXY", "")
    if not http_proxy and not https_proxy:
        print("[警告] 未检测到 HTTP_PROXY / HTTPS_PROXY 环境变量！")
        print("       大陆网络环境下可能无法直连 HuggingFace。")
        print("       请先设置代理：")
        print("         export HTTP_PROXY=http://127.0.0.1:7890")
        print("         export HTTPS_PROXY=http://127.0.0.1:7890")
        print("       或使用镜像：")
        print("         export HF_ENDPOINT=https://hf-mirror.com")
        resp = input("\n是否继续下载？(y/N): ")
        if resp.lower() != "y":
            print("已取消。请配置代理后重试。")
            sys.exit(0)
    else:
        print(f"[OK] 代理已配置: {http_proxy or https_proxy}")


def download_ui_tars():
    """下载主模型 UI-TARS-1.5-7B（约 15GB）。"""
    print("\n[1/2] UI-TARS-1.5-7B（主 GUI Agent 模型）...")
    print("  来源: ByteDance-Seed/UI-TARS-1.5-7B")
    print("  大小: ~15GB")
    print("  用途: 截图→推理→动作（内置 OCR + 元素检测 + 推理）")
    from huggingface_hub import snapshot_download
    snapshot_download(
        "ByteDance-Seed/UI-TARS-1.5-7B",
        local_dir=MODELS_DIR / "ui-tars-1.5-7b",
        resume_download=True,
    )
    print("  [OK] UI-TARS-1.5-7B 下载完成")


def download_qwen3_vl_8b():
    """下载备选模型 Qwen3-VL-8B-Instruct（约 16GB）。"""
    print("\n[2/?] Qwen3-VL-8B-Instruct（备选通用 VLM）...")
    print("  来源: Qwen/Qwen3-VL-8B-Instruct")
    print("  大小: ~16GB")
    print("  用途: 通用视觉问答、文档理解，GPTQ-Int4 仅 ~3.1GB 显存")
    from huggingface_hub import snapshot_download
    snapshot_download(
        "Qwen/Qwen3-VL-8B-Instruct",
        local_dir=MODELS_DIR / "qwen3-vl-8b",
        resume_download=True,
    )
    print("  [OK] Qwen3-VL-8B-Instruct 下载完成")


def download_yolo_optional():
    """可选插件：下载 YOLO11m（约 60MB）。"""
    print("\n[?] YOLO11m（可选检测插件）...")
    print("  来源: ultralytics")
    print("  大小: ~60MB")
    print("  说明: 非主流程！仅在需要超高速纯检测时 lazy-load 使用")
    resp = input("  是否下载 YOLO11m？(y/N): ")
    if resp.lower() == "y":
        from ultralytics import YOLO
        model = YOLO("yolo11m.pt")
        model.save(str(MODELS_DIR / "yolo11m-ui.pt"))
        print("  [OK] YOLO11m 下载完成")
    else:
        print("  [跳过] YOLO11m 未下载（可在需要时再获取）")


def main():
    print("=" * 60)
    print("  AI PC Control System — 模型下载工具")
    print("  架构: UI-TARS 端到端 Agent（无需独立 YOLO/OCR）")
    print("  主模型: UI-TARS-1.5-7B (GUI Agent SOTA)")
    print("  备选:   Qwen3-VL-8B-Instruct (通用 VLM)")
    print("=" * 60)

    check_proxy()

    # 询问下载哪些模型
    print("\n请选择要下载的模型：")
    print("  [1] 仅主模型（UI-TARS-1.5-7B）— 推荐 ✅，约 15GB")
    print("      注: UI-TARS 自带 OCR + 元素检测 + 动作能力")
    print("  [2] 全部（主 + 备选 Qwen3-VL-8B）— 约 31GB")
    print("  [3] 仅备选（Qwen3-VL-8B）— 约 16GB")
    choice = input("\n请输入选项 (1/2/3): ").strip()

    if choice == "1":
        download_ui_tars()
    elif choice == "2":
        download_ui_tars()
        download_qwen3_vl_8b()
    elif choice == "3":
        download_qwen3_vl_8b()
    else:
        print(f"[错误] 无效选项: {choice}")
        sys.exit(1)

    # 可选：YOLO 插件
    download_yolo_optional()

    print("\n" + "=" * 60)
    print("  模型下载完成！")
    print(f"  模型目录: {MODELS_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
