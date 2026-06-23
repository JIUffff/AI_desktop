# 基准测试说明

> 验证 PRD AC-06（延迟<1.5s）、AC-07（显存<13GB）、AC-08（30分钟无泄漏）。

---

## 1. 测试截图集规范

### 1.1 目录结构

```
benchmarks/
├── latency_bench.py          # 基准测试脚本
├── README.md                 # 本文件
├── screenshots/              # 标准测试截图（gitignore）
│   ├── desktop_idle.png      # 桌面空闲状态
│   ├── notepad_empty.png     # 记事本空白界面
│   ├── browser_home.png      # 浏览器主页
│   └── ...
└── results/                  # 测试结果 JSON（gitignore）
    └── bench_ui-tars_20260623_121600.json
```

### 1.2 截图命名约定

截图文件名必须与 `latency_bench.py` 中 `STANDARD_TASKS` 列表的 `screenshot` 字段一一对应：

| 截图文件名 | 描述 | 任务 |
|-----------|------|------|
| `desktop_idle.png` | Windows 桌面空闲 | 打开记事本应用 |
| `notepad_empty.png` | 记事本空白界面 | 输入 Hello World |
| `browser_home.png` | 浏览器主页 | 搜索框输入 AI |
| `file_explorer.png` | 文件资源管理器 | 选中所有 .png 文件 |
| `settings_panel.png` | 系统设置面板 | 点击显示选项 |
| `dialog_confirm.png` | 确认对话框 | 点击确认按钮 |
| `ide_vscode.png` | VS Code 编辑器 | 打开终端面板 |
| `excel_data.png` | Excel 数据表 | 选中 A1:C10 单元格 |
| `mail_client.png` | 邮件客户端 | 点击新建邮件 |
| `taskbar.png` | 任务栏 | 点击第三个图标 |

### 1.3 截图采集要求

- **分辨率**：1920x1080（必须统一，否则延迟数据不可比）
- **DPI**：100%（不要在高 DPI 下采集，避免坐标缩放问题）
- **格式**：PNG（无损）
- **场景**：Windows 11 原生应用为主，覆盖桌面/窗口/对话框/任务栏

### 1.4 采集脚本

```bash
# 手动采集（推荐）
# 1. 调整分辨率到 1920x1080
# 2. 打开对应应用
# 3. 按 Win+Shift+S 截图，保存为对应文件名

# 或用 Python 自动采集
uv run python -c "
import pyautogui
import time
input('回车截图 desktop_idle.png...')
pyautogui.screenshot('benchmarks/screenshots/desktop_idle.png')
print('已保存')
"
```

---

## 2. 运行基准测试

### 2.1 前置条件

- 模型权重已下载到 `models/` 目录
- 截图集已放入 `benchmarks/screenshots/`
- GPU 驱动正常，CUDA 可用

### 2.2 运行命令

```bash
# 完整测试（UI-TARS + 30分钟泄漏测试）
uv run python benchmarks/latency_bench.py

# 仅测试延迟（跳过 30 分钟泄漏）
uv run python benchmarks/latency_bench.py --skip-leak-test

# 测试备选后端
uv run python benchmarks/latency_bench.py --backend qwen3-vl-8b

# 仅跑前 5 个任务（快速验证）
uv run python benchmarks/latency_bench.py --tasks 5 --skip-leak-test
```

### 2.3 输出解读

```
================================================================
  汇总：ui-tars
================================================================
  成功率：        10/10 (100.0%)

  延迟统计（毫秒）：
    P50:   380.5 ms
    P95:   520.3 ms   ✅ PASS (AC-06: <1500ms)
    P99:   580.1 ms
    Mean:  410.2 ms

  显存统计（GB）：
    Peak:    10.85 GB  ✅ PASS (AC-07: <13GB)
    Mean:    10.42 GB
================================================================
```

- **P95 < 1500ms** → AC-06 通过
- **Peak < 13GB** → AC-07 通过
- **30分钟泄漏 < 0.5GB** → AC-08 通过

---

## 3. 结果文件

每次运行会在 `benchmarks/results/` 下生成 JSON 文件，包含：

- 后端名称、模型名称
- 每次推理的延迟、显存、输出预览
- P50/P95/P99 统计
- AC 验收结果

用于：
- 横向对比 UI-TARS vs Qwen3-VL-8B
- 纵向对比不同量化方案（FP16 vs AWQ INT4 vs GPTQ-Int4）
- 回归测试（模型升级前后对比）

---

## 4. 测试集扩展

当 10 个标准任务不足以覆盖场景时，在 `latency_bench.py` 的 `STANDARD_TASKS` 列表追加：

```python
{"screenshot": "new_scenario.png", "task": "对应任务描述"},
```

并在 `benchmarks/screenshots/` 放入对应截图。

建议最终达到 **20-30 个任务**，覆盖：
- 桌面/窗口/对话框/任务栏/系统托盘
- 浏览器/办公软件/开发工具/系统设置
- 中文界面/英文界面/混合界面
- 简单点击/拖拽/键盘输入/滚动
