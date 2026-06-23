# AI PC 控制系统

> 完全运行在本地 GPU（RTX 5070 Ti 16GB）上的 AI 桌面自动化系统。零网络依赖，零隐私外泄。
> 最后更新：2026-06-23

## 快速开始

```bash
# 1. 安装依赖
pip install -e ".[dev]"

# 2. 初始化 GPU 环境
python scripts/setup_gpu.py

# 3. 下载模型
python scripts/download_models.py

# 4. 启动服务
python -m src.api.server
```

## 文档导航

| 文档 | 说明 |
|------|------|
| [AGENTS.md](AGENTS.md) | AI 开发行为准则（必读，含长程自循环 + 多代理协作协议） |
| [docs/prd/](docs/prd/) | 产品需求文档 |
| [docs/spec/](docs/spec/) | 技术设计文档 |
| [docs/architecture.md](docs/architecture.md) | 架构总览 |
| [docs/theory/](docs/theory/) | Harness Engineering 理论文档 |
| [docs/progress.md](docs/progress.md) | 进度日志（会话间记忆传递） |
| [docs/lessons.md](docs/lessons.md) | 失败复盘积累 |

## 技术栈

- **主模型**: UI-TARS-1.5-7B (AWQ INT4 量化，GUI Agent SOTA)
- **备选模型**: Qwen3-VL-8B (GPTQ-Int4，通用 VLM)
- **OCR**: UI-TARS 内置（PaddleOCR 作为可选 fallback）
- **执行**: PyAutoGUI + Pywinauto + Playwright
- **GPU**: NVIDIA RTX 5070 Ti (16GB, CUDA 12.8)
