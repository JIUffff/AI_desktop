#!/usr/bin/env python3
"""任务验证脚本。

AI 完成任务后必须运行此脚本，验证任务是否真正完成。
用法: python scripts/validate.py T-XX

退出码:
  0 = 全部 PASS
  1 = 有 FAIL 项
  2 = 任务不存在
"""
import sys
import re
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
TASKS_DIR = PROJECT_ROOT / "docs" / "tasks" / "active"


def find_task_file(task_id: str) -> Path | None:
    """在 active/ 和 completed/ 中查找任务文件。"""
    for d in [TASKS_DIR, PROJECT_ROOT / "docs" / "tasks" / "completed"]:
        for f in d.glob(f"{task_id}-*.md"):
            return f
    return None


def parse_acceptance_criteria(task_file: Path) -> list[str]:
    """从任务文件中提取验收标准。"""
    content = task_file.read_text(encoding="utf-8")
    criteria = []
    in_criteria = False
    for line in content.splitlines():
        if "验收标准" in line:
            in_criteria = True
            continue
        if in_criteria:
            if line.startswith("## ") or line.startswith("---"):
                break
            if line.strip().startswith("-"):
                criteria.append(line.strip("- ").strip())
    return criteria


def check_file_exists(path: Path) -> bool:
    """检查任务声明的代码文件是否存在。"""
    return path.exists()


def run_pytest(test_path: Path | None = None) -> tuple[bool, str]:
    """运行 pytest。"""
    cmd = [sys.executable, "-m", "pytest"]
    if test_path:
        cmd.append(str(test_path))
    else:
        cmd.append(str(PROJECT_ROOT / "tests"))
    try:
        result = subprocess.run(
            cmd, cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=120
        )
        return result.returncode == 0, result.stdout[-500:] if result.stdout else ""
    except subprocess.TimeoutExpired:
        return False, "测试超时（120秒）"
    except FileNotFoundError:
        return False, "pytest 未安装"


def validate_task(task_id: str) -> bool:
    """验证一个任务是否完成。"""
    task_file = find_task_file(task_id)
    if not task_file:
        print(f"[FAIL] 任务 {task_id} 不存在")
        return False

    print(f"\n=== 验证 {task_id} ===")
    print(f"任务文件: {task_file.name}")

    criteria = parse_acceptance_criteria(task_file)
    if not criteria:
        print("[WARN] 未找到验收标准，跳过验证")
        return True

    all_pass = True
    for i, criterion in enumerate(criteria, 1):
        print(f"\n  [{i}/{len(criteria)}] {criterion}")

        file_match = re.search(r"代码在\s+`?([^`]+\.py)`?", criterion)
        if file_match:
            code_path = PROJECT_ROOT / file_match.group(1)
            if check_file_exists(code_path):
                print(f"  -> [PASS] 文件存在: {code_path}")
            else:
                print(f"  -> [FAIL] 文件不存在: {code_path}")
                all_pass = False

        test_match = re.search(r"测试在\s+`?([^`]+)`?", criterion)
        if test_match:
            test_path = PROJECT_ROOT / test_match.group(1)
            if test_path.exists():
                ok, output = run_pytest(test_path)
                if ok:
                    print(f"  -> [PASS] 测试通过")
                else:
                    print(f"  -> [FAIL] 测试失败")
                    print(f"     {output[-200:]}")
                    all_pass = False
            else:
                print(f"  -> [SKIP] 测试目录不存在: {test_path}")

        if re.search(r"[<>]\s*[\d.]+", criterion):
            print(f"  -> [MANUAL] 需手动验证（性能/数值标准）")

    print(f"\n=== 结果: {'ALL PASS' if all_pass else 'HAS FAIL'} ===\n")
    return all_pass


def main():
    if len(sys.argv) < 2:
        print("用法: python scripts/validate.py T-XX")
        print("示例: python scripts/validate.py T-01")
        sys.exit(2)

    task_id = sys.argv[1].upper()
    if not task_id.startswith("T-"):
        task_id = "T-" + task_id

    success = validate_task(task_id)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
