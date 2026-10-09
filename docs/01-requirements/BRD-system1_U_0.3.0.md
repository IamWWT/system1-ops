---
title: 需求与验收矩阵
type: prd
status: active
version: 0.3.0
date: 2026-10-09
owner: IamWWT
applies_to: System1 Ops
references:
  - docs/FILE_INDEX.md
---

# 需求与验收矩阵

> 版本: 0.3.0 | 状态: Active
> 适用范围: System1 Ops
> 关联: [[FILE_INDEX|全库索引]]

## 目标

使用一个维护项目提供三个模型的Jev服务、可配置设备/上下文/资源策略与轻量运维页面；结构和质量工具可迁移至Linux与Windows。

## 验收矩阵

| 编号 | 验收要求 | 实现 | 验证 |
|---|---|---|---|
| R1 | 一个项目管理Laya、0.8B、4B | configs、system1_ops.manage | doctor、start/status/smoke all |
| R2 | 8882–8885与0.0.0.0可配置 | TOML模型表、dashboard表 | 实际监听和宿主LAN地址HTTP |
| R3 | Jev三题型及错误契约稳定 | worker.create_app、project_jev | API单测与三个真实模型smoke |
| R4 | 自动设备与显存预算，明确强制设备失败 | worker.choose_device、Engine | CPU/GPU策略单测与native/GPU日志 |
| R5 | 上下文、线程、卸载策略可调整 | common.config/preflight、Engine | 越界拒绝、64K/16K实测、低RAM串行单测 |
| R6 | 可调试运维页面、管理认证、日志 | dashboard、web、logging_config | ASGI认证/控制、真实浏览器、JSON日志单测 |
| R7 | Windows CPU保底迁移 | configs/windows-gguf、system1.ps1 | Windows真实0.8B推理/HTTP/重启CI |
| R8 | 性能和数值兼容有真实数据 | benchmark、native | [[05-testing/NFTR-system1_VD_0.2.0|CPU/GPU性能报告]] |
| R9 | 源码、测试、模板、规范和文档分层 | src、tests、configs、standards、docs | quality_gate、FILE_INDEX、doc_check |
| R10 | 锁文件、格式、类型、构建和测试门禁 | pyproject、uv.lock、CI | Linux/Windows同一quality_gate |

## 限制

Windows laptop本身和Windows Laya/4B真实权重推理仍未在该设备验收。4B使用官方Q8，未比较原始BF16权重。GPU显存观测不是峰值。性能数字来自固定合成输入，不代表业务准确率或全局最优。

## 上下游

需求来源：[[00-request/request]]。设计：[[02-design/SAD-system1_HD_0.3.0]]。证据：[[05-testing/FTR-system1_VD_0.3.0]]。

## 参考文档

| 文档 | 用途 |
|---|---|
| [[FILE_INDEX|docs/FILE_INDEX.md]] | 查找本项目的关联文档 |

## 变更记录

| 版本 | 日期 | 记录入口 |
|---|---|---|
| 0.3.0 | 2026-10-09 | [[04-progress/2026-10-09-complete-engineering|过程记录]]；历史基线见[[04-progress/baselines]] |
