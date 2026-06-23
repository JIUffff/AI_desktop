---
title: Spec — 感知 Pipeline
type: spec
prd: 001
created: 2026-06-22
status: draft
---

# Spec: 感知 Pipeline

> 本文档由 PRD-001 的 Goals（AC-01/02/03）驱动，定义视觉感知层的技术设计。

---

## 1. Pipeline 流程

```
截图（DPI 适配）
    ↓
YOLOv8 检测 UI 元素 → 边界框 + 类别
    ↓
PaddleOCR 识别文字 → 文字 + 位置
    ↓
SoM 标注 → 在截图上画编号框
    ↓
输出：带编号的标注图 + 元素元数据列表
```

## 2. 模块接口

### `src/perception/screenshot.py`

```python
class ScreenCapture:
    """DPI 感知的截图模块。"""

    def capture(self) -> tuple[Image, tuple[int, int]]:
        """返回截图和真实分辨率。"""
```

### `src/perception/yolo_detector.py`

```python
class UIDetector:
    """YOLOv8 UI 元素检测。"""

    def detect(self, image: Image) -> list[UIElement]:
        """
        返回检测到的 UI 元素列表。
        UIElement = {id, bbox, class_name, confidence}
        class_name: button, input, icon, text, link, checkbox
        """
```

### `src/perception/ocr.py`

```python
class OCRModule:
    """PaddleOCR 封装。"""

    def recognize(self, image: Image) -> list[TextRegion]:
        """
        返回文字区域列表。
        TextRegion = {text, bbox, confidence}
        """
```

### `src/perception/som.py`

```python
class SoMAnnotator:
    """Set-of-Mark 标注生成。"""

    def annotate(self, image: Image, elements: list, texts: list) -> Image:
        """
        在截图上为每个元素画编号框。
        输出：带编号的标注图。
        """
```

## 3. 三层识别回退

```
Layer A: 控件树识别（Pywinauto）
    │ 失败回退
    ▼
Layer B: AI 视觉解析（YOLO + OCR + SoM）
    │ 仍失败
    ▼
Layer C: 模板匹配（OpenCV matchTemplate）
```

## 4. DPI 适配（关键）

```python
import ctypes

# 启动时声明 DPI 感知
ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PER_MONITOR_AWARE

def get_screen_size():
    user32 = ctypes.windll.user32
    return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
```

## 5. 验收映射

| AC | 验证方式 |
|----|---------|
| AC-01（记事本任务） | e2e 测试 |
| AC-02（文件整理） | e2e 测试 |
| AC-03（浏览器搜索） | e2e 测试 |
