---
title: System1 Ops
type: guide
status: active
version: 0.2.0
date: 2026-10-09
owner: IamWWT
applies_to: System1 Ops
references:
  - docs/FILE_INDEX.md
---

# System1 Ops

> 版本: 0.2.0 | 状态: Active
> 适用范围: System1 Ops
> 关联: [[FILE_INDEX|全库索引]]

一个统一项目管理Laya、StartLux Decision 0.8B/4B。FastAPI提供Jev API与运维页面；StartLux可用C++ llama.cpp，Laya使用PyTorch。每模型一个实例，设备、上下文、线程和卸载策略由TOML配置。

## 快速使用

```bash
./system1.sh doctor all
./system1.sh start all
./system1.sh dashboard start
./system1.sh smoke all
```

Windows使用system1.ps1。默认端口8882、8883、8884和运维8885，支持0.0.0.0。已有部署从项目根config.toml和.env读取配置；新的环境从configs模板建立配置，见[运行手册](docs/07-ops/RUNBOOK-system1_MG_0.2.0.md)。

## 阅读与开发

- [全库索引](docs/FILE_INDEX.md)：源码、规范与阶段文档导航。
- [架构与目录蓝图](docs/02-design/SAD-system1_HD_0.2.0.md)：模块职责和Jev契约。
- [编码与质量门禁](docs/03-plan/CODE-system1_CD_0.2.0.md)：统一开发命令和验证标准。
- [性能报告](docs/05-testing/NFTR-system1_VD_0.2.0.md)：真实CPU/GPU数据、失败候选和限制。
- [工程适配决策](docs/02-design/decisions/ADR-001-engineering_CD_0.2.0.md)：规范裁剪、覆盖率和兼容边界。
- [第三方说明](docs/07-ops/NOTICE.md)：代码Apache-2.0及上游许可。

```bash
uv sync --locked
uv run python scripts/quality_gate.py
```

公开仓库：[IamWWT/system1-ops](https://github.com/IamWWT/system1-ops)。Windows CPU native路径在CI验证；目标laptop本身性能未测。

## 参考文档

| 文档 | 用途 |
|---|---|
| [[FILE_INDEX|docs/FILE_INDEX.md]] | 查找本项目的关联文档 |
