---
title: 软件架构与目录蓝图
type: spec
status: active
version: 0.2.0
date: 2026-10-09
owner: IamWWT
applies_to: System1 Ops
references:
  - docs/FILE_INDEX.md
---

# 软件架构与目录蓝图

> 版本: 0.2.0 | 状态: Active
> 适用范围: System1 Ops
> 关联: [[FILE_INDEX|全库索引]]

## 模块边界

| 模块/目录 | 职责 | 依赖边界 |
|---|---|---|
| src/system1_ops/common.py | TOML归一化、离线预检、运行环境 | 标准库，不导入torch |
| manage.py / portable.py | 生命周期、PID身份、锁、资源、CLI | 包内配置、psutil、受管子进程 |
| worker.py | 每模型单实例、API、线程池、设备策略 | 上游模型仅在加载路径导入 |
| native_gguf.py / native/ | 原生JSONL或loopback HTTP | StartLux模板/校准 + 固定llama.cpp C API |
| startlux_policy.py | 上游加载边界的CPU精度适配 | 不修改上游源码或全局torch |
| dashboard.py / web/ | 管理认证、有限任务、日志、Jev调试 | 只控制项目记录的进程 |
| benchmark.py | 隔离性能/数值门槛 | 同一fixture、完整失败记录 |
| logging_config.py | JSON行日志与异常关联 | 请求ID、可轮转文件，不记录认证header |
| scripts/ | 兼容入口桥接与质量门禁 | 工具自身位置解析路径 |
| configs/ | 可复制至项目根的公开模板 | 私有config.toml是运行配置真源 |
| tests/ | 可重复契约/运维单测 | 真实模型验证独立运行 |

## 运行流

1. system1.sh/ps1选择解释器，scripts/launch.py加载system1_ops.manage。
2. manage预检并启动独立worker或dashboard，保留PID和创建时间。
3. worker验证Jev请求；每模型串行，在有界线程池执行；超时后占锁至计算结束。
4. StartLux使用原生子进程字母logits；Laya使用PyTorch encoder/head；统一返回Jev字段。
5. dashboard经管理认证读取状态、启动任务和调试请求。

## 接口契约

`POST /v1/systemone`接收state、questions，可选max_len/images；三题型choice/score/noul。严格模式返回model、answers、usage。`GET /v1/models`、`/health`、`/v1/health`与`/docs`保留。

| 状态码 | 语义 | 调用方动作 |
|---|---|---|
| 400 | 请求结构/JSON非法 | 修改输入 |
| 401 | 认证失败 | 修正Bearer凭证 |
| 413 | 请求体超限 | 缩小输入 |
| 422 | 模型/上下文验证失败 | 调整合法请求预算 |
| 503 | 模型忙 | 客户端退避重试 |
| 504 | 计算超时，计算仍可能继续 | 先检查busy，避免立即重复计算 |
| 500 | 推理失败 | 用请求ID查日志 |

## 目录蓝图

源码真源在src/system1_ops；native保留C++桥；tests存测试；configs存模板；scripts存工具。根目录Python文件仅兼容入口。运行数据models/vendor/logs/run/reports/evidence与私有配置保持项目根且Git忽略。docs采用00-request至07-ops英文阶段方案；每目录有索引。标准快照在standards，由source.json校验，不手工双写上游规范。

## 设计约束

每模型一个进程和一个推理槽，避免多HTTP worker复制权重。低RAM配置跨进程共享锁并逐请求卸载，保留进程基础开销。配置相对路径以运行config.toml所在目录解析；configs模板先复制到项目根。安装分发基于仓库checkout，指定SYSTEM1_HOME可使用已安装包定位此工作区。

## 关联

[[01-requirements/BRD-system1_U_0.2.0]] · [[02-design/decisions/ADR-001-engineering_CD_0.2.0]] · [[07-ops/RUNBOOK-system1_MG_0.2.0]]

## 参考文档

| 文档 | 用途 |
|---|---|
| [[FILE_INDEX|docs/FILE_INDEX.md]] | 查找本项目的关联文档 |
