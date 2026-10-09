---
title: System1 Ops
type: guide
status: active
version: 0.3.0
date: 2026-10-09
owner: IamWWT
applies_to: System1 Ops
references:
  - docs/FILE_INDEX.md
---

# System1 Ops

> 版本: 0.3.0 | 状态: Active
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

Windows使用system1.ps1。默认端口8882、8883、8884和运维8885，支持0.0.0.0。已有部署从 .local/config.toml和.local/.env读取配置；新的环境从configs模板建立配置，见[运行手册](docs/07-ops/RUNBOOK-system1_MG_0.3.0.md)。

## 技术基线

Linux裸机CUDA宿主；Windows CPU为迁移目标。Python3.12、FastAPI/uvicorn/psutil及开发工具精确版本由uv.lock固定；C++17/llama.cpp源版本由bootstrap.SOURCES固定。模型运行环境独立，CPU与CUDA验证版本见测试报告。按生产要求维护错误处理、配置、认证与审计；当前安全/覆盖/目标设备边界在ADR中明示，无全量生产验收结论。无关系库、队列与缓存服务，文件持久化设计见数据模型。

## 工作目录

根目录保留启动入口、工程工具链和导航；src/native是实现，scripts是安装/运维/校验工具，tests是测试，configs是公开模板，docs是阶段产物，standards是规范真源。私有配置、权重、日志、状态、证据和产品归档集中.local。隐藏虚拟环境与原生构建有位置绑定，保留工具默认位置。

## 阅读与开发

- [全库索引](docs/FILE_INDEX.md)：源码、规范与阶段文档导航。
- [架构与目录蓝图](docs/02-design/SAD-system1_HD_0.3.0.md)：模块职责和Jev契约。
- [编码与质量门禁](docs/03-plan/CODE-system1_CD_0.3.0.md)：统一开发命令和验证标准。
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
