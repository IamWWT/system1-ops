---
title: 目录迁移部署与回退验证
type: report
status: active
version: 0.3.0
date: 2026-10-09
owner: IamWWT
applies_to: System1 Ops
references:
  - docs/FILE_INDEX.md
---

# 目录迁移部署与回退验证

> 版本: 0.3.0 | 创建: 2026-10-09 | 状态: active
> 关联: [[FILE_INDEX|文件索引]]

## 部署对象与范围

System1 Ops位于frameworks/system1-ops，IamWWT维护；配置.local/config.toml/.env；模型8882–8884、运维8885。父目录是独立项目集合：Laya/StartLux提供现有代码或解释器；NanoJev/jev-decision-models等是其他项目；resume-system1-host.sh是早期续接工具，不是本服务启动入口。本轮不移动无关仓库或个人下载。

## 演练步骤与证据

先按PID身份停四服务，私有配置备份；迁移运行文件并保留所有解析后的模型与环境路径；运行doctor；恢复模型与dashboard；真实三题型smoke；浏览器检查管理/调试/报告；Windows native验证新目录。证据在.local/evidence/layout-*.txt，实际关口结论见04-progress，未完成项不写成通过。

## 故障与回退边界

回退源码为v0.2.0，文件逆向映射见.local/migration/moves.json。先停当前服务，逆向移动并恢复旧配置；源码用独立worktree，环境/二进制保持绝对路径，最后doctor/smoke。本次验证了备份、原/新配置解析一致、数据迁移和恢复启动；未实际切回旧版四服务，不称全量灾备演练通过。8881按此前用户要求保持停止。

## 参考文档

| 文档 | 用途 |
|---|---|
| [[FILE_INDEX|文件索引]] | 本仓文件与阶段产物 |

## 变更记录

| 版本 | 日期 | 变更依据 |
|---|---|---|
| 0.3.0 | 2026-10-09 | 用户完整engineering模式组织返工要求；过程见[[04-progress/2026-10-09-complete-engineering]] |
