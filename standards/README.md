---
title: 规范层（Standards）— 生产级质量底线
type: standard
status: active
version: 1.2.0
date: 2026-10-08
owner: AI + 维护人
applies_to: 项目文档
---

# 规范层（Standards）— 生产级质量底线

> 给 Agent 在编码、测试、加固阶段查阅。**规范是强制性的**（除明确标注"可选"外）。
> 语言无关规范 + 各语言适配（`languages/`）。

## 规范地图

| 规范 | 回答的问题 | 何时读 |
|------|-----------|--------|
| [quality-gates.md](quality-gates.md) | 什么算"完成"？门禁怎么过？**看什么数字（最小指标集）**？ | 每个阶段结束 |
| [documentation.md](documentation.md) | docs 怎么编：**事实三分（现状/变更史/决策史）**/frontmatter/索引/引用/必要性/依赖链？ | 全程 |
| [process.md](process.md) | 工艺流程：**开工基线（Gate 0 前置）**/阶段关口/产出物依赖链/变更联动/四维检验／重构与迁移？ | 开工 + 计划与评审 |
| [configuration-management.md](configuration-management.md) | 哪些算配置项？基线何时形成？版本怎么标？编号怎么编？ | 交付 + 维护 |
| [change-management.md](change-management.md) | 这次改动该不该做？谁批？怎么退回来？ | 已基线化产物变更时 |
| [interfaces.md](interfaces.md) | 接口怎么管理：生命周期/版本/文档/契约测试？ | 设计与实现 |
| [enterprise/](enterprise/README.md) | 企业存量规范：收纳位置/导入流程/优先级？ | 需求摄入 + 编码 |
| [security.md](security.md) | 哪些安全红线不能碰？ | 设计 + 实现 + 加固 |
| [reliability.md](reliability.md) | 超时/重试/幂等/并发怎么做？外部依赖失败怎么降级？ | 设计 + 实现 |
| [troubleshooting.md](troubleshooting.md) | 故障怎么定位：错误文案不可信怎么办？怎么做对照实验？修复怎么不污染全局？ | 出故障时 + 复盘 |
| [performance.md](performance.md) | 性能靠什么保证？ | 设计 + 加固 |
| [non-functional.md](non-functional.md) | 非功能需求怎么识别与验证？故障怎么按架构层注入？瓶颈怎么收敛？ | 需求 + 设计 + 测试 |
| [observability.md](observability.md) | 日志/指标/追踪/审计怎么接？ | 实现 + 加固 |
| [testing.md](testing.md) | 测试怎么写、证据怎么留？ | 实现 + 测试 |
| [code-style.md](code-style.md) | 代码长什么样？评审看什么？ | 实现 + 评审 |
| [languages/](languages/) | 当前语言的具体命令与惯例 | 脚手架 + 实现 |

## 应用规则

1. 规范冲突时按项目 AGENTS.md §2「冲突优先级」裁决（生产安全 > 数据一致性 > 可审计 > 现有资产）。
2. 规范不是死教条：**更严可以，更松必须写理由**（在 ADR 或进度日志注明）。
3. 新的一般性经验应回流到对应规范（同 AGENTS.md 铁律提升机制）。
4. 检查项都有"如何验证"列；验证不了的条目在交付时明确标注。

## 变更记录

| 日期 | 版本 | 变更 | 操作人 |
|---|---|---|---|
| 2026-10-04 | 1.1.0 | 收录 configuration-management / change-management / non-functional 三个新规范 | AI |
| 2026-10-08 | 1.2.0 | 规范地图描述同步：documentation.md 增「事实三分」、process.md 增「开工基线（Gate 0 前置）」与「重构/迁移」 | AI |
