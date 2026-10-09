---
title: 工程组织差距与边界
type: report
status: active
version: 0.3.0
date: 2026-10-09
owner: IamWWT
applies_to: System1 Ops
references:
  - docs/FILE_INDEX.md
---

# 工程组织差距与边界

> 版本: 0.3.0 | 创建: 2026-10-09 | 状态: active
> 关联: [[FILE_INDEX|文件索引]]

## 当前目标与差距

目标见[[01-requirements/BRD-system1_U_0.3.0]]；已交付组织结构在[[02-design/SAD-system1_HD_0.3.0]]，返工前实际目录清单及问题记录在[[04-progress/2026-10-09-complete-engineering]]。

| 差距 | 当前边界 | 追踪 |
|---|---|---|
| 完整流程批准证据 | 用户明确要求按模式组织；用户对最终目录的主观接受尚未获得 | 交付目录供检查，不填“用户验收已通过” |
| 覆盖率 | 自动门槛35%，有效全包覆盖约37% | PP任务欠账，硬件真实集成补证据 |
| Windows设备 | CI native仅证明runner的0.8B路径 | 目标laptop、Windows Laya/4B未实测 |
| 根工具目录 | .venv与.native-build含绝对路径 | 隐藏工具目录保留；迁移需重建，ADR明确 |
| 外部工作区 | frameworks下还有独立Git仓库和个人资产 | 只读分类；不凭本项目指令移动其他仓库 |

## 参考文档

| 文档 | 用途 |
|---|---|
| [[FILE_INDEX|文件索引]] | 本仓文件与阶段产物 |

## 变更记录

| 版本 | 日期 | 变更依据 |
|---|---|---|
| 0.3.0 | 2026-10-09 | 用户完整engineering模式组织返工要求；过程见[[04-progress/2026-10-09-complete-engineering]] |
