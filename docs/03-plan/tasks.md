---
title: 任务与完成标准
type: plan
status: active
version: 0.2.0
date: 2026-10-09
owner: IamWWT
applies_to: System1 Ops
references:
  - docs/FILE_INDEX.md
---

# 任务与完成标准

> 版本: 0.2.0 | 状态: Active
> 适用范围: System1 Ops
> 关联: [[FILE_INDEX|全库索引]]

## 任务清单

| 任务 | 完成标准 | 证据入口 |
|---|---|---|
| 组织源码与测试 | 包布局、旧启动入口、配置路径通过 | [[05-testing/FTR-system1_VD_0.2.0]] |
| 固定规范与工具链 | 来源commit/hash、uv.lock、格式/类型/构建门禁 | [[03-plan/CODE-system1_CD_0.2.0]] |
| 整理文档 | FILE_INDEX、frontmatter、索引、无断链 | scripts/doc_check.py |
| 恢复运行服务 | 8882–8885恢复、Jev smoke、浏览器 | [[07-ops/RUNBOOK-system1_MG_0.2.0]] |
| 发布验证版本 | CI通过、标签/归档可回溯、推送public | [[04-progress/2026-10-09-engineering]] |

上述五项组织任务已完成，发布基线为v0.2.0；验收证据与回退入口见工程记录。

## 待验证与欠账

目标Windows laptop硬件、Windows Laya/4B真权重性能、全包覆盖提升至建议范围、既有Engine/CLI大函数进一步拆分。当前实现不以这些未完成项声称全面生产就绪。

## 变更依据

[[00-request/request]] · [[02-design/decisions/ADR-001-engineering_CD_0.2.0]]

## 参考文档

| 文档 | 用途 |
|---|---|
| [[FILE_INDEX|docs/FILE_INDEX.md]] | 查找本项目的关联文档 |
