---
title: Local-GPU AI PC Control System
feature_id: 001
type: prd
created: 2026-06-22
updated: 2026-06-22
status: active
tags: [ai-pc-control, local-gpu, harness-engineering]
hardware:
  gpu: "NVIDIA GeForce RTX 5070 Ti (16GB VRAM, Blackwell, CUDA 12.8)"
---

# Feature: Local-GPU AI PC Control System

> 一个完全运行在本地 RTX 5070 Ti 上的 AI 桌面控制系统，用户用自然语言下指令，AI 自主完成截屏→识别→决策→操作全流程。

---

## Goals · 目标

- 支持自然语言指令驱动桌面操作（鼠标/键盘/应用）
- 完全本地推理，零网络依赖，零隐私外泄
- 单步操作延迟 < 1.5 秒（截图→决策→执行）
- 任务成功率 ≥ 65%（OSWorld 基准子集）
- 支持 Windows 11 原生应用 + Web 页面
- 具备多层安全防护（风险评级/人工确认/审计/熔断）
- 支持失败案例收集与增量微调

---

## Non-Goals · 非目标（红线）

- 不做移动端（Android/iOS）控制
- 不做远程桌面控制（仅控制本机）
- 不做云端 API 调用（即使网络可用也走本地）
- 不做 32B+ 大模型本地推理（显存不够，不硬撑）
- 不做无人工确认的自主删除/发送/支付操作
- 不做游戏自动化（游戏反作弊会封号）
- MVP 阶段不做多用户/权限管理

---

## User Stories · 用户故事

- 作为知识工作者，我想用一句话让 AI 整理桌面杂乱文件到对应文件夹
- 作为程序员，我想让 AI 打开 IDE、切到指定分支、运行测试并报告结果
- 作为财务人员，我想让 AI 打开报表软件、导出 PDF、命名归档
- 作为普通用户，我想让 AI 帮我填一张长表单（从已有数据复制粘贴）
- 作为安全管理者，我想所有 AI 操作都有日志可查、可回放
- 作为开发者，我想收集失败案例用于后续微调模型

---

## Acceptance Criteria · 验收标准

### 功能验收

- **AC-01**: 输入"打开记事本输入 Hello World 保存到桌面"，全流程自动完成
- **AC-02**: 输入"把桌面所有 .png 文件移到 Pictures 文件夹"，正确识别并移动
- **AC-03**: 输入"打开浏览器搜索 AI 并截图"，完成搜索+截图保存
- **AC-04**: 遇到需要确认的危险操作（如删除），弹出人工确认框
- **AC-05**: 连续 3 步失败后自动暂停并报告

### 性能验收

- **AC-06**: 单步操作（截图→决策→执行）延迟 < 1.5 秒
- **AC-07**: GPU 显存占用峰值 < 13GB（主方案实测 ~10-11GB）
- **AC-08**: 连续运行 30 分钟无显存泄漏

### 安全验收

- **AC-09**: 所有操作有审计日志，含截图+动作+时间
- **AC-10**: 高风险操作（删除/发送/支付）100% 触发人工确认
- **AC-11**: 操作步数超 50 步自动熔断
- **AC-12**: 沙箱外的文件系统访问被拒绝

### 本地化验收

- **AC-13**: 断网环境下全部功能正常
- **AC-14**: 任务执行期间无任何出站网络请求（用 Wireshark 验证）

---

## 技术约束

| 约束 | 值 | 原因 |
|------|------|------|
| GPU 显存 | 16GB | 硬件限制 |
| 主模型 | UI-TARS-1.5-7B (AWQ INT4) | GUI Agent SOTA，ScreenSpot-V2 94.2% |
| 备选模型 | Qwen3-VL-8B (GPTQ-Int4) | 通用 VLM，仅 ~3.1GB 显存 |
| 推理框架 | transformers（MVP）→ vLLM（优化） | 渐进式优化 |
| Python | 3.11+ | 类型标注支持 |

---

## See Also

- [架构总览](../architecture.md)
- [Spec: 模型部署架构](../spec/model-deployment.md)
- [Spec: 安全层设计](../spec/safety-layer.md)
