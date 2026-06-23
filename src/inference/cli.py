"""VLM 推理 CLI：通过命令行驱动 UI-TARS 模型。

用法：
    # 单次推理
    uv run python -m src.inference.cli infer --screenshot test.png --task "打开记事本"

    # 交互式 REPL
    uv run python -m src.inference.cli repl

    # 查看 GPU 状态
    uv run python -m src.inference.cli gpu

    # 查看模型加载状态
    uv run python -m src.inference.cli status
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def cmd_gpu(args: argparse.Namespace) -> int:
    """查看 GPU 状态。"""
    from .gpu_monitor import get_gpu_info

    info = get_gpu_info()
    print("=== GPU 状态 ===")
    for k, v in info.items():
        print(f"  {k:20s}: {v}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """查看模型和项目状态。"""
    models_dir = Path("models")

    print("=== 项目状态 ===\n")

    # 模型权重检查
    backends = [
        ("UI-TARS-1.5-7B", "models/ui-tars-1.5-7b"),
        ("Qwen3-VL-8B", "models/qwen3-vl-8b"),
        ("Qwen3-VL-4B", "models/qwen3-vl-4b"),
    ]

    print("模型权重：")
    for name, path in backends:
        p = Path(path)
        if p.exists() and any(p.iterdir()):
            # 统计目录大小
            total_size = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
            size_gb = total_size / 1024**3
            print(f"  ✅ {name:20s}  {size_gb:.2f} GB  ({path})")
        else:
            print(f"  ❌ {name:20s}  未下载  ({path})")

    # GPU 状态
    from .gpu_monitor import get_gpu_info

    print("\nGPU：")
    info = get_gpu_info()
    for k, v in info.items():
        print(f"  {k:20s}: {v}")

    # 依赖检查
    print("\n关键依赖：")
    deps = ["torch", "transformers", "PIL", "huggingface_hub"]
    for dep in deps:
        try:
            mod = __import__(dep)
            version = getattr(mod, "__version__", "unknown")
            print(f"  ✅ {dep:20s}  {version}")
        except ImportError:
            print(f"  ❌ {dep:20s}  未安装")

    return 0


def cmd_infer(args: argparse.Namespace) -> int:
    """单次推理。"""
    screenshot = Path(args.screenshot)
    if not screenshot.exists():
        print(f"[错误] 截图不存在：{screenshot}")
        return 1

    # 延迟导入，避免启动时加载 torch
    from .vlm_server import create_server

    print(f"加载模型（后端：{args.backend}）...")
    server = create_server(backend=args.backend, models_dir="models")

    try:
        server.start()
    except RuntimeError as e:
        print(f"[错误] 模型加载失败：{e}")
        return 1

    print(f"\n任务：{args.task}")
    print(f"截图：{screenshot}")
    print(f"\n推理中...\n")

    try:
        action = server.infer(str(screenshot), args.task)

        # 输出结果
        print("=== 推理结果 ===\n")
        print(f"Thought:    {action.thought}")
        print(f"Action:     {action.action_type.value}")
        if action.coordinates:
            print(f"坐标:        [{action.coordinates[0]:.3f}, {action.coordinates[1]:.3f}]  "
                  f"(像素: [{int(action.coordinates[0]*1920)}, {int(action.coordinates[1]*1080)}])")
        if action.text:
            print(f"输入文本:    {action.text}")
        if action.key_combo:
            print(f"快捷键:      {action.key_combo}")
        if action.scroll_amount is not None:
            print(f"滚动:        {action.scroll_amount}")
        if action.confidence is not None:
            print(f"置信度:      {action.confidence:.2f}")
        print(f"\n原始输出:\n{action.raw_output[:500]}")

        # JSON 输出（可选）
        if args.json:
            print(f"\n--- JSON ---")
            print(json.dumps(action.to_dict(), ensure_ascii=False, indent=2))

        return 0

    except Exception as e:
        print(f"[错误] 推理失败：{e}")
        import traceback

        traceback.print_exc()
        return 1

    finally:
        server.stop()


def cmd_repl(args: argparse.Namespace) -> int:
    """交互式 REPL：持续驱动模型。"""
    from .vlm_server import create_server

    print(f"=== VLM 交互式 REPL ===")
    print(f"后端：{args.backend}")
    print(f"命令：")
    print(f"  :task <描述>      设置任务")
    print(f"  :shot <路径>      设置截图")
    print(f"  :run              执行推理")
    print(f"  :history          查看历史")
    print(f"  :reset            清空历史")
    print(f"  :switch <后端>    切换后端")
    print(f"  :quit             退出")
    print()

    # 加载模型
    print("加载模型...")
    server = create_server(backend=args.backend, models_dir="models")
    try:
        server.start()
    except RuntimeError as e:
        print(f"[错误] 模型加载失败：{e}")
        return 1

    current_task = ""
    current_screenshot = ""

    try:
        while True:
            try:
                user_input = input(">>> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n退出")
                break

            if not user_input:
                continue

            if user_input.startswith(":"):
                parts = user_input.split(maxsplit=1)
                cmd = parts[0]
                arg = parts[1] if len(parts) > 1 else ""

                if cmd == ":quit":
                    print("退出")
                    break
                elif cmd == ":task":
                    current_task = arg
                    print(f"任务已设置：{current_task}")
                elif cmd == ":shot":
                    current_screenshot = arg
                    if Path(current_screenshot).exists():
                        print(f"截图已设置：{current_screenshot}")
                    else:
                        print(f"[警告] 截图不存在：{current_screenshot}")
                elif cmd == ":run":
                    if not current_task or not current_screenshot:
                        print("[错误] 请先设置任务和截图")
                        continue
                    action = server.infer(current_screenshot, current_task)
                    print(f"\nThought: {action.thought}")
                    print(f"Action:  {action.action_type.value}")
                    if action.coordinates:
                        print(f"坐标:    [{action.coordinates[0]:.3f}, {action.coordinates[1]:.3f}]")
                    print()
                elif cmd == ":history":
                    for h in server.history:
                        print(f"  Step {h.step_id}: {h.action_type} "
                              f"{'✅' if h.success else '❌'}  {h.thought[:60]}")
                elif cmd == ":reset":
                    server.reset_history()
                    print("历史已清空")
                elif cmd == ":switch":
                    from .model_manager import VLMBackend

                    backend_map = {
                        "ui-tars": VLMBackend.UI_TARS,
                        "qwen3-vl-8b": VLMBackend.QWEN3_VL_8B,
                        "qwen3-vl-4b": VLMBackend.QWEN3_VL_4B,
                    }
                    if arg in backend_map:
                        server.switch_backend(backend_map[arg])
                        print(f"已切换到：{arg}")
                    else:
                        print(f"[错误] 未知后端：{arg}")
                else:
                    print(f"未知命令：{cmd}")

    finally:
        server.stop()

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="VLM 推理 CLI — 驱动 UI-TARS 模型",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # gpu
    subparsers.add_parser("gpu", help="查看 GPU 状态")

    # status
    subparsers.add_parser("status", help="查看模型和项目状态")

    # infer
    infer_parser = subparsers.add_parser("infer", help="单次推理")
    infer_parser.add_argument("--screenshot", "-s", required=True, help="截图文件路径")
    infer_parser.add_argument("--task", "-t", required=True, help="任务描述")
    infer_parser.add_argument(
        "--backend", "-b", default="ui-tars",
        choices=["ui-tars", "qwen3-vl-8b", "qwen3-vl-4b"],
        help="后端模型（默认 ui-tars）",
    )
    infer_parser.add_argument("--json", action="store_true", help="输出 JSON 格式")

    # repl
    repl_parser = subparsers.add_parser("repl", help="交互式 REPL")
    repl_parser.add_argument(
        "--backend", "-b", default="ui-tars",
        choices=["ui-tars", "qwen3-vl-8b", "qwen3-vl-4b"],
        help="后端模型（默认 ui-tars）",
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 0

    handlers = {
        "gpu": cmd_gpu,
        "status": cmd_status,
        "infer": cmd_infer,
        "repl": cmd_repl,
    }

    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
