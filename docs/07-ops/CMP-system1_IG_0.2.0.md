---
title: 配置项与环境清单
type: inventory
status: active
version: 0.2.0
date: 2026-10-09
owner: IamWWT
applies_to: System1 Ops
references:
  - docs/FILE_INDEX.md
---

# 配置项与环境清单

> 版本: 0.2.0 | 状态: Active
> 适用范围: System1 Ops
> 关联: [[FILE_INDEX|全库索引]]

## 单一真源

运行配置config.toml；公开模板configs/example.toml、windows-cpu.toml、windows-gguf.toml。密钥.env或进程环境，环境变量优先。.env只白名单读取两种认证键；其他变量需由调用环境导出。

| 环境变量 | 用途 | 默认/覆盖 |
|---|---|---|
| SYSTEM1_API_KEY | 模型API Bearer认证 | 空保留Jev兼容匿名模式，见ADR |
| SYSTEM1_ADMIN_KEY | 运维认证与控制 | 空只读；设置后ops均需认证 |
| SYSTEM1_PYTHON | 维护CLI解释器 | 启动脚本优先项目venv，再已有Laya环境 |
| SYSTEM1_NATIVE_BINARY | Windows原生exe模板插值 | 调用环境显式指定 |
| SYSTEM1_HOME | 包定位运行工作区 | checkout自动解析；安装包时显式指定 |

## 主要TOML项

| 分组 | 配置项 | 语义 |
|---|---|---|
| 监听/认证 | host、port、api_key_env | 每模型单HTTP进程 |
| 设备 | device、gpu_index、gpu_required_mb、gpu_reserve_mb | auto检查空闲显存，强制设备显式失败 |
| CPU/后端 | threads、cpu_dtype、cpu_affinity、startlux_backend、native_binary、gguf_file | 原生/torch与解释器分离 |
| Laya | laya_backend、laya_gpu_dtype、laya_gpu_tf32、long_input、window_length | 默认FP32，窗口是聚合非全长注意力 |
| 上下文 | context_length、max_batch_tokens、prefill_chunk | checkpoint上限、批量和分块各自约束 |
| 资源 | preload、idle_unload_seconds、serialize_inference、unload_after_request | 常驻、空闲卸载或逐请求释放 |
| 保护 | inference_timeout、max_body_bytes、max_questions | 请求预算与错误语义 |
| 日志 | log_level、log_max_bytes、log_backups、log_payloads | JSON文件轮转；正文默认不记录 |

config变更后restart对应模型；CLI临时--device/--port/--context-length不写回文件。密钥轮换需重启读取环境的服务。

## 版本控制

uv.lock/pyproject/.python-version固定服务工具链。requirements-http.txt是uv.lock的无dev导出，门禁检查二者一致，不手工双写。bootstrap.SOURCES固定模型框架源码commit；模型revision与文件SHA写性能证据。所有私有权重、vendor、配置、日志与二进制不提交。规范源由standards/source.json记录commit和逐文件hash。

操作入口：[[07-ops/RUNBOOK-system1_MG_0.2.0]]。

## 参考文档

| 文档 | 用途 |
|---|---|
| [[FILE_INDEX|docs/FILE_INDEX.md]] | 查找本项目的关联文档 |
