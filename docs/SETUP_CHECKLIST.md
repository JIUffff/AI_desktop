---
title: 开发前资源与工具准备清单
type: checklist
created: 2026-06-23
purpose: 确保开发流程顺畅，最小化 token 消耗
tags: [setup, resources, checklist]
---

# 开发前资源与工具准备清单

> **核心原则**：能预装的都预装，能离线获取的都提前下载。AI 工作时每搜索一次、试错一次，都在烧 token。把准备工作做在前面，AI 就能直接干活。

---

## 优先级说明

| 级别 | 含义 | 必须完成时间 |
|------|------|------------|
| 🔴 P0 | 没它项目无法启动 | 开发前必须完成 |
| 🟡 P1 | 没它会频繁卡顿、烧 token | 开发前尽量完成 |
| 🟢 P2 | 提升效率，非必须 | 可在开发中逐步补充 |

---

## 一、开发环境配置

### 🔴 P0-1：Python 虚拟环境（统一用 uv）

| 项 | 内容 |
|------|------|
| 用途 | 隔离依赖，避免污染系统 Python |
| 版本 | Python 3.11+（推荐 3.13） |
| 工具 | **必须用 uv**，禁止 conda/venv/pip 直接安装（见 AGENTS.md §13.1） |
| 获取方式 | `uv venv` 创建，`uv pip install` 装包 |
| 验证 | `python --version` 输出 3.11+ |

```bash
cd D:\workspace\Codex\AI_Desktop

# 安装 uv（如尚未安装）
pip install uv

# 用 uv 创建虚拟环境（禁止用 python -m venv / conda）
uv venv

# 激活
.venv\Scripts\activate
```

> **⚠️ 硬性约束**：统一使用 `uv` 管理虚拟环境和依赖，禁止使用 conda/cuda 环境方案。所有包安装命令一律用 `uv pip install` 或 `uv sync`。详见 AGENTS.md §13.1。

### 🔴 P0-2：PyTorch + CUDA 12.8

| 项 | 内容 |
|------|------|
| 用途 | GPU 推理的基础，所有 AI 模型依赖它 |
| 版本 | torch ≥ 2.5.0（CUDA 12.8 版本） |
| 获取方式 | 必须用官方 CUDA 专用安装命令，`pip install torch` 默认装 CPU 版 |
| 验证 | `python scripts/setup_gpu.py` 全部 OK |

```bash
# 必须用这个命令，不能直接 pip install torch
# 统一用 uv pip install（见 AGENTS.md §13.1）
uv pip install torch --index-url https://download.pytorch.org/whl/cu128
```

> **⚠️ token 节省点**：装错版本（CPU 版）会导致后续所有 AI 任务报错，AI 反复调试要烧大量 token。这一步必须人工确认装对。

### 🔴 P0-3：Git 仓库初始化

| 项 | 内容 |
|------|------|
| 用途 | 版本控制，AI 每完成一个任务要 commit |
| 获取方式 | `git init && git add . && git commit -m "init"` |
| 验证 | `git log --oneline` 能看到初始提交 |

```bash
cd D:\workspace\Codex\AI_Desktop
git init
git add .
git commit -m "init: 项目骨架 + 文档体系"
```

### 🟡 P1-4：ruff + pytest 预装

| 项 | 内容 |
|------|------|
| 用途 | 代码格式化 + 测试运行，AI 完成任务后要用 |
| 获取方式 | `pip install -e ".[dev]"` |
| 验证 | `ruff --version` 和 `pytest --version` 正常 |

---

## 二、依赖库版本锁定

### 🔴 P0-5：核心 AI 依赖（一次性装全）

**为什么不一个个装**：AI 工作时发现缺包会中断去装，每次中断都要重新读上下文恢复，严重浪费 token。一次性装全，AI 后续不再为依赖分心。

```bash
# 下载前必须确认代理配置（见 AGENTS.md §13.2）
echo $HTTP_PROXY
echo $HTTPS_PROXY
# 若为空 → 暂停，询问用户代理地址，不得直连

# AI 推理（统一用 uv pip install）
uv pip install transformers>=4.45.0 accelerate>=1.0.0 bitsandbytes>=0.44.0

# 图像处理
uv pip install opencv-python>=4.10.0 pillow>=10.4.0

# 执行层
uv pip install pyautogui>=0.9.54 pywinauto>=0.6.8
playwright install  # 安装浏览器驱动

# API + 工具
uv pip install fastapi>=0.115.0 uvicorn>=0.32.0 pydantic>=2.9.0 loguru>=0.7.2

# 开发工具
uv pip install pytest>=8.3.0 pytest-cov>=5.0.0 ruff>=0.7.0 mypy>=1.13.0
```

### 🟡 P1-6：hf CLI（模型下载工具）

| 项 | 内容 |
|------|------|
| 用途 | 下载 UI-TARS-1.5-7B 模型权重 |
| 获取方式 | `uv pip install huggingface-hub`（已安装） |
| 验证 | `hf --version` |

### 🟡 P1-7：Wireshark 或 netstat（网络验证工具）

| 项 | 内容 |
|------|------|
| 用途 | 验证 AC-14（无出站网络请求），证明本地化合规 |
| 获取方式 | [wireshark.org](https://www.wireshark.org/) 下载安装 |
| 替代方案 | Windows 自带 `netstat -an` 也可 |

---

## 三、模型权重（最大头，必须提前下载）

### 🔴 P0-8：UI-TARS-1.5-7B 模型权重

| 项 | 内容 |
|------|------|
| 用途 | 主 GUI Agent 模型，截图→推理→动作（内置 OCR + 检测 + 推理） |
| 大小 | 约 29GB（7 个分片），AWQ INT4 量化后约 6GB 显存 |
| 存放位置 | `models/ui-tars-1.5-7b/` |
| 获取方式 | `hf download ByteDance-Seed/UI-TARS-1.5-7B --local-dir models/ui-tars-1.5-7b` |

```bash
# 下载前必须确认代理（见 AGENTS.md §13.2）
echo $HTTP_PROXY
echo $HTTPS_PROXY
# 若为空 → 暂停，询问用户，不得直连

# 方法一：huggingface-cli（推荐，自带进度条，见 AGENTS.md §13.3）
huggingface-cli download Qwen/Qwen2-VL-7B-Instruct --local-dir models/qwen2-vl-7b

# 方法二：Python 脚本（必须带进度回调）
python scripts/download_models.py
```

> **⚠️ 下载必须显示实时进度**（见 AGENTS.md §13.3）：速度、已下载/总量、百分比、ETA。禁止静默下载（-q / -s）。人工需能随时判断下载是否正常、是否需要中断。

> **⚠️ token 节省点**：模型约 29GB（7 个分片），下载要 30-60 分钟。如果 AI 工作时才发现没下载，会卡住等下载，白白消耗会话时间。**必须提前人工下载好。**

---

## 四、账号与权限

### 🟡 P1-11：HuggingFace 账号 + Token

| 项 | 内容 |
|------|------|
| 用途 | 下载 Qwen2-VL-7B（部分模型需登录） |
| 获取方式 | 注册 [huggingface.co](https://huggingface.co/) → Settings → Access Tokens → New token |
| 配置方式 | `huggingface-cli login` 粘贴 token |
| 注意 | Qwen2-VL-7B 是公开模型，通常不需要 token，但建议配置以备不时之需 |

### 🟢 P2-12：GitHub 仓库（可选）

| 项 | 内容 |
|------|------|
| 用途 | 代码托管 + 版本备份 |
| 获取方式 | 创建 GitHub 仓库 → `git remote add origin <url>` |

### 🔴 P0-13：Windows 管理员权限

| 项 | 内容 |
|------|------|
| 用途 | PyAutoGUI 鼠标键盘控制、Pywinauto 控件树访问、DPI 感知 |
| 验证 | 能正常运行 `python -c "import pyautogui; pyautogui.position()"` |
| 注意 | 部分企业管控的电脑可能限制鼠标键盘模拟，需提前确认 |

---

## 五、数据集与测试样本

### 🟡 P1-14：标准测试截图集

| 项 | 内容 |
|------|------|
| 用途 | 测试 UI-TARS 端到端视觉识别，不用每次临时截图 |
| 数量 | 20-30 张，覆盖常见场景 |
| 存放位置 | `tests/fixtures/screenshots/` |

**需要覆盖的场景**：

```
tests/fixtures/screenshots/
├── windows_explorer.png      ← 文件管理器
├── notepad_empty.png         ← 空记事本
├── notepad_with_text.png     ← 有文字的记事本
├── browser_google.png        ← 浏览器首页
├── browser_search_results.png ← 搜索结果页
├── desktop_full.png          ← 完整桌面
├── dialog_save_as.png        ← 保存对话框
├── dialog_confirm_delete.png ← 删除确认框
├── excel_empty.png           ← 空 Excel
├── excel_with_data.png       ← 有数据的 Excel
└── ... （共 20-30 张）
```

> **⚠️ token 节省点**：没有标准测试截图，AI 每次测试都要先截图，还要描述截图内容。提前准备好，AI 直接 `python -m pytest tests/` 跑测试，省掉大量描述和调试 token。

### 🟡 P1-15：OSWorld 基准测试子集（可选）

| 项 | 内容 |
|------|------|
| 用途 | 评估任务成功率（AC 要求 ≥ 65%） |
| 大小 | 选取 10-20 个任务即可 |
| 获取方式 | [OSWorld GitHub](https://github.com/xlang-ai/osworld) 下载 |
| 注意 | 完整数据集较大，选取子集即可 |

### 🟢 P2-16：标准任务脚本

| 项 | 内容 |
|------|------|
| 用途 | 端到端测试（AC-01~AC-05）的标准输入 |
| 内容 | 5 条标准自然语言指令 |

```python
# tests/fixtures/task_scripts.py
STANDARD_TASKS = [
    "打开记事本输入 Hello World 保存到桌面",           # AC-01
    "把桌面所有 .png 文件移到 Pictures 文件夹",        # AC-02
    "打开浏览器搜索 AI 并截图",                        # AC-03
    "删除桌面上的 test.txt 文件",                      # AC-04（危险操作测试）
    "打开不存在的应用 xyz123",                         # AC-05（失败处理测试）
]
```

---

## 六、文档模板（已有，无需额外准备）

| 文档 | 位置 | 状态 |
|------|------|------|
| PRD 模板 | `docs/prd/001-local-gpu-pc-control.md` | ✅ 已有 |
| Spec 模板 | `docs/spec/*.md` | ✅ 已有（3 份） |
| Task 模板 | `docs/tasks/active/T-XX-*.md` | ✅ 已有（20 份） |
| AGENTS.md | 项目根 | ✅ 已有（12 节完整） |
| progress.md | `docs/progress.md` | ✅ 已有 |
| lessons.md | `docs/lessons.md` | ✅ 已有 |
| PROMPT.md | 项目根 | ✅ 已有 |

---

## 七、一键准备脚本

把以下脚本保存为 `scripts/prepare_all.bat`，一次性完成所有准备工作：

```batch
@echo off
echo === AI PC 控制系统 - 环境准备 ===

cd /d D:\workspace\Codex\AI_Desktop

echo [0/8] 确认代理配置（见 AGENTS.md §13.2）...
echo HTTP_PROXY = %HTTP_PROXY%
echo HTTPS_PROXY = %HTTPS_PROXY%
if "%HTTP_PROXY%"=="" echo [警告] HTTP_PROXY 为空，请先设置代理！
if "%HTTPS_PROXY%"=="" echo [警告] HTTPS_PROXY 为空，请先设置代理！

echo [1/8] 安装 uv（统一环境管理工具，见 AGENTS.md §13.1）...
pip install uv

echo [2/8] 用 uv 创建虚拟环境（禁止 conda/venv）...
uv venv
call .venv\Scripts\activate

echo [3/8] 用 uv 安装 PyTorch (CUDA 12.8)...
uv pip install torch --index-url https://download.pytorch.org/whl/cu128

echo [4/8] 用 uv 安装项目依赖...
uv pip install -e ".[dev]"

echo [5/8] 安装 Playwright 浏览器...
playwright install

echo [6/8] 安装 HuggingFace CLI...
uv pip install huggingface-hub

echo [7/8] 验证 GPU 环境...
python scripts/setup_gpu.py

echo [8/8] 下载模型（需要 30-60 分钟，自带进度条，见 AGENTS.md §13.3）...
python scripts/download_models.py

echo === 准备完成 ===
echo 下一步: 准备测试截图到 tests/fixtures/screenshots/
echo 然后: 复制 PROMPT.md 中的提示词给 AI 开始开发
```

---

## 八、准备完成检查表

开始开发前，逐项确认：

```
环境检查：
[ ] uv 已安装（pip install uv）
[ ] 用 uv venv 创建虚拟环境（非 conda/venv，见 AGENTS.md §13.1）
[ ] PyTorch CUDA 12.8 版本已安装（用 uv pip install，非 CPU 版）
[ ] python scripts/setup_gpu.py 全部 OK
[ ] uv pip install -e ".[dev]" 无报错
[ ] ruff format 和 pytest 可运行
[ ] Git 仓库已初始化，有初始提交
[ ] HTTP_PROXY / HTTPS_PROXY 环境变量已设置（见 AGENTS.md §13.2）

模型检查：
[ ] models/ui-tars-1.5-7b/ 目录存在，约 29GB（7 个分片完整）
[ ] 下载过程有实时进度展示（速度/大小/百分比/ETA，见 AGENTS.md §13.3）

权限检查：
[ ] pyautogui.position() 能正常运行（鼠标权限）
[ ] pywinauto 能枚举窗口（控件树权限）
[ ] playwright 能启动浏览器

测试素材检查：
[ ] tests/fixtures/screenshots/ 有 20+ 张标准截图
[ ] tests/fixtures/task_scripts.py 有 5 条标准任务

文档检查：
[ ] AGENTS.md 完整（13 节，含环境与下载规范）
[ ] docs/prd/001-local-gpu-pc-control.md 完整
[ ] docs/progress.md 初始记录已写
[ ] PROMPT.md 已就位

全部打勾 → 复制 PROMPT.md 提示词给 AI → 开始开发
```

---

## 九、为什么这些准备能省 token

| 准备项 | 不准备的代价 | 节省的 token 类型 |
|--------|------------|-----------------|
| PyTorch CUDA 版装对 | AI 反复调试 CUDA 错误 | 调试 token |
| 模型提前下载 | AI 卡在下载等待，会话超时 | 等待+重试 token |
| 标准测试截图 | AI 每次临时截图+描述内容 | 描述+截图 token |
| 依赖一次装全 | AI 工作中频繁中断装包 | 上下文恢复 token |
| 文档模板就位 | AI 从零设计文档结构 | 设计 token |
| Git 初始化 | AI 无法 commit，任务流程卡住 | 流程 token |
| 代理配置就位 | AI 下载失败反复重试 | 重试 token |
| 下载进度可见 | 人工无法判断是否卡死，AI 盲等 | 等待 token |
| uv 统一工具链 | conda/pip 混用导致依赖冲突 | 调试 token |

**一句话**：准备工作做透了，AI 拿到提示词就能直接写代码，不为环境分心。
