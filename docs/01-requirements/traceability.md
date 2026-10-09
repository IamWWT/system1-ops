---
title: 需求与实现验证追踪矩阵
type: inventory
status: active
version: 0.3.0
date: 2026-10-09
owner: IamWWT
applies_to: System1 Ops
references:
  - docs/FILE_INDEX.md
---

# 需求与实现验证追踪矩阵

> 版本: 0.3.0 | 创建: 2026-10-09 | 状态: active
> 关联: [[FILE_INDEX|文件索引]]

## 需求范围

R1–R10定义见[[01-requirements/BRD-system1_U_0.3.0]]。Jev客户端是下游；Laya、StartLux、llama.cpp源与权重是上游；路径/启动变更影响CLI、dashboard子进程、Windows工作流与安装手册。

| 需求 | 实现/数据 | 测试与交付 |
|---|---|---|
| R1 三模型维护 | manage/common、模型配置、PID | tests/test_ops.py预检、test_extended.py生命周期；真实doctor/start/smoke |
| R2 端口与监听 | 模板/配置、dashboard | 真实ss和LAN浏览器；manage占用端口用例 |
| R3 Jev契约 | worker.create_app/project_jev | test_ops投影/strict/error用例、test_extended ASGI用例、三模型HTTP |
| R4 CPU/GPU策略 | choose_device、native_gguf | test_ops设备用例；GPU日志和CPU verify_native |
| R5 上下文与资源 | common.preflight、Engine、文件锁 | test_ops上下文/low_memory用例、verify_native；NFTR长输入 |
| R6 运维和日志 | dashboard/logging_config/portable | test_logging、test_extended认证/控制用例、浏览器/JSON日志 |
| R7 Windows保底 | system1.ps1、bootstrap/portable | test_extended portable/源固定用例、Windows native真实工作流 |
| R8 性能保真 | benchmark、native | NFTR固定数据与公开samples；本轮不改变推理数学逻辑 |
| R9 组织与规范 | docs/layout/index_files | test_docs、test_layout；FILE_INDEX和模式docs-audit |
| R10 可复现门禁 | uv.lock、quality_gate、artifact_check/archive_release | Linux/Windows CI、版本归档与SHA256 |
| L1 干净目录 | STATE统一、scripts与.local | test_layout外部state/旧配置选择、真实根目录/配置读回 |
| L2 工作流程 | PP/GAP/CLM/DRR/SESSION/baselines | doc_check强制记录、关口表与会话三同步 |


所有自动用例验证上述功能/边界；外部模型真实HTTP及native验收不计入单测替代。用户对组织结果的判断属于人工验收，当前待交付复核。

## 参考文档

| 文档 | 用途 |
|---|---|
| [[FILE_INDEX|文件索引]] | 本仓文件与阶段产物 |

## 变更记录

| 版本 | 日期 | 变更依据 |
|---|---|---|
| 0.3.0 | 2026-10-09 | 用户完整engineering模式组织返工要求；过程见[[04-progress/2026-10-09-complete-engineering]] |
