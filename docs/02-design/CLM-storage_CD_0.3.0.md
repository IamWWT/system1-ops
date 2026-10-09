---
title: 文件持久化逻辑与物理模型
type: spec
status: active
version: 0.3.0
date: 2026-10-09
owner: IamWWT
applies_to: System1 Ops
references:
  - docs/FILE_INDEX.md
---

# 文件持久化逻辑与物理模型

> 版本: 0.3.0 | 创建: 2026-10-09 | 状态: active
> 关联: [[FILE_INDEX|文件索引]]

## 概念与逻辑模型

没有关系数据库，但文件就是持久化数据，必须设计其生命周期。配置描述模型实例；一个实例有PID身份、有效配置、日志和原生子进程；一次benchmark生成报告；一次发布生成版本归档和校验和。

| 实体 | 字段/类型与约束 | 关系/规则 |
|---|---|---|
| ModelConfig | name:str唯一、port:int唯一、python/path/source:str、device/context/threads | TOML配置归一化；相对路径由配置父目录解析 |
| ProcessIdentity | pid:int、starttime:float | 仅PID与创建时间都匹配才停止，防PID重用 |
| EffectiveConfig | 归一化配置dict | worker启动快照；不能当作下一次启动配置真源 |
| InferenceLock | 跨进程文件锁 | 低RAM模型共享，进程退出自动释放 |
| LogEvent | UTC/level/request_id/status/exception | JSON行，大小与备份数有限；正文默认关闭 |
| BenchmarkReport | hardware/results/recommendations/limitations | 每批时间目录、latest指针；未测标注 |
| ReleaseArtifact | version:str、filename:str、sha256:str、source_tag:str | 从标签源码构建，归档不可就地覆盖 |

## 物理映射与权限

| 物理位置 | 内容 | 保留与并发 |
|---|---|---|
| .local/config.toml、.local/.env | 私有配置、认证密钥 | 不入Git；密钥文件本机0600；进程环境优先 |
| .local/run/*.json与inference.lock | PID/有效配置与锁 | portable.snapshot原子替换；单实例管理 |
| .local/logs/* | JSON、console、native日志 | 配置轮转；人工维护历史文件 |
| .local/models与vendor | 权重与固定上游源 | 离线复用；bootstrap不覆盖有改动源 |
| .local/reports与evidence | 私有性能与验收证据 | 报告/错误完整记录，不入公开归档 |
| .local/dist、products/<版本> | 构建临时产物与已验证产品归档 | products下版本独立，清单含SHA256 |
| docs/05-testing/samples | 可公开样本 | 已脱离密钥/用户输入，与真实版本证据关联 |

STATE由common.py统一；SYSTEM1_STATE_DIR可覆盖，跨进程由环境继承。文件路径不散落各模块。已安装包用SYSTEM1_HOME绑定仓库checkout。

## 迁移与回退

本轮迁移清單.local/migration/moves.json，配置原文备份config.pre-layout.toml。移动配置先解析并保留模型/解释器/二进制绝对路径，不改变端口和精度。停服务后移动状态和日志；恢复后验证身份、API、dashboard报告。失败则停止新服务、逆向移动并使用v0.2.0。不存在数据库DDL，不伪造迁移表。模型源、权重和环境不批量删除。

## 参考文档

| 文档 | 用途 |
|---|---|
| [[FILE_INDEX|文件索引]] | 本仓文件与阶段产物 |

## 变更记录

| 版本 | 日期 | 变更依据 |
|---|---|---|
| 0.3.0 | 2026-10-09 | 用户完整engineering模式组织返工要求；过程见[[04-progress/2026-10-09-complete-engineering]] |
