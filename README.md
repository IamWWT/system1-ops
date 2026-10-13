---
title: System1 Ops
type: guide
status: active
version: 0.3.0
date: 2026-10-12
owner: IamWWT
applies_to: System1 Ops
references:
  - docs/FILE_INDEX.md
---

# System1 Ops

> 版本: 0.3.0 | 状态: Active
> 适用范围: System1 Ops
> 关联: [[FILE_INDEX|全库索引]]

一个统一项目管理Laya、StartLux Decision 0.8B/4B。FastAPI提供Jev兼容的决策API与运维页面（本项目模型为本地决策模型，非Jev官方模型）；StartLux可用C++ llama.cpp，Laya使用PyTorch。每模型一个实例，设备、上下文、线程和卸载策略由TOML配置。

## 快速使用

```bash
./system1.sh doctor all        # 预检：权重、运行时、原生后端
./system1.sh start all         # 启动全部模型（等待健康检查）
./system1.sh dashboard start   # 启动 8885 运维台
./system1.sh smoke all         # 三题型冒烟（Jev接口格式）
```

Windows 使用 `system1.ps1`。默认端口 8882、8883、8884 为模型，8885 为运维台，支持 0.0.0.0。已有部署从 .local/config.toml 和 .local/.env 读取配置；新环境从 configs 模板建立配置，详见[运行手册](docs/07-ops/RUNBOOK-system1_MG_0.3.0.md)。

## 基本运维方式

### 命令行速查

| 目的 | 命令 |
|---|---|
| 预检权重/运行时/原生 | `./system1.sh doctor all`（或单模型名） |
| 启动/停止/重启 | `./system1.sh start all`、`./system1.sh stop all`、`./system1.sh restart laya` |
| 查看进程与健康 | `./system1.sh status laya` |
| 三题型冒烟（Jev接口） | `./system1.sh smoke all` |
| 日志（可跟随） | `./system1.sh logs startlux-4b --follow` |
| 单模型性能基准 | `python scripts/benchmark.py --model laya --config .local/config.toml`，或运维台卡片“性能测试” |
| 修改设备/上下文 | `./system1.sh restart laya --device cpu --context-length 8192` |

start 会等待预检、预热与 /health 就绪；`--no-wait` 只拉起进程。配置在 .local/config.toml（设备 auto/cpu/cuda:N、上下文、线程、空闲卸载等），修改后 restart 对应模型生效；密钥在 .local/.env（SYSTEM1_ADMIN_KEY、SYSTEM1_API_KEY）。

### 运维台（8885）

浏览器打开 http://<host>:8885。未配置 SYSTEM1_ADMIN_KEY 时为只读页面；配置后重启运维台并在页面输入密钥、点击“连接”，才能启动/停止/重启/性能测试。页面每 5 秒自动刷新硬件与各模型状态。

管理密钥状态显示在页面右上角：未连接（只读/待输入）、已连接·密钥有效、或密钥无效/已失效的明确提示。密钥连接成功后默认保存在此浏览器（仅本站可访问），刷新页面、关闭页面、重启浏览器后仍然有效；可随时点“清除密钥”移除，或改用无痕窗口访问以免保存。密钥本身长期有效，仅在修改 SYSTEM1_ADMIN_KEY 或重启运维台后失效，失效时页面给出明确提示便于重新输入。

- 模型卡片：运行/加载状态、设备、精度、内存、最近耗时，以及“检查状态 / 启动 / 重启 / 停止 / 性能测试”按钮。
- 状态术语：“运行中/已停止”指 worker 进程是否存在；“已驻留/未驻留”指模型权重是否在内存。空闲超过 `idle_unload_seconds`（默认 300 秒）自动卸载权重释放内存，进程保持运行，下次请求自动重新加载（卸载后首次请求较慢）。“设备”显示实际选中的设备；与配置不同时标注为 `cpu（配置 auto）`，健康信息行给出降级原因（如显存不足）。
- 状态检查：点击卡片“检查状态”或顶部“检查全部状态”，主动探活——进程是否存活、/health 是否健康、模型是否已加载、端口是否被占用、停止时预检（权重/运行时/原生后端）是否通过。**端口在用不等于异常**：占用者会按 `/health` 的 `model` 字段辨认，若正是本模型的实例（但不由管理记录跟踪，例如进程在本页之外启动），结果显示“运行中（未纳入管理记录，本页无法停止）”并带出真实设备/内存/请求数；只有占用者是其它进程或其它模型时才报“端口被占用”。停掉决策模型后用它确认已彻底停止；切换决策模型时，先检查目标模型预检通过，再启动目标、停止旧模型。
- 请求调试：向选定模型发送 /v1/systemone 并查看响应与延迟，用于验证接口行为。
- 运行日志：按模型查看 worker/原生日志尾部。
- 性能测试结果：本机兼容与性能基准结果（scripts/benchmark.py）。

### 常见问题

503/504 为请求忙或超时，先查 /health 的 busy 再退避重试；端口被占用先查实际监听进程，管理脚本不会接管非项目进程；模型 API 失败用响应头 x-request-id 查 .local/logs/ 下 JSON 日志。完整故障与回退流程见[运行手册](docs/07-ops/RUNBOOK-system1_MG_0.3.0.md)。

## 技术基线

Linux裸机CUDA宿主；Windows CPU为迁移目标。Python3.12、FastAPI/uvicorn/psutil及开发工具精确版本由uv.lock固定；C++17/llama.cpp源版本由bootstrap.SOURCES固定。模型运行环境独立，CPU与CUDA验证版本见测试报告。按生产要求维护错误处理、配置、认证与审计；当前安全/覆盖/目标设备边界在ADR中明示，无全量生产验收结论。无关系库、队列与缓存服务，文件持久化设计见数据模型。

## 工作目录

根目录保留启动入口、工程工具链和导航；src/native是实现，scripts是安装/运维/校验工具，tests是测试，configs是公开模板，docs是阶段产物，standards是规范真源。私有配置、权重、日志、状态、证据和产品归档集中.local。隐藏虚拟环境与原生构建有位置绑定，保留工具默认位置。

## 阅读与开发

- [全库索引](docs/FILE_INDEX.md)：源码、规范与阶段文档导航。
- [架构与目录蓝图](docs/02-design/SAD-system1_HD_0.3.0.md)：模块职责和Jev兼容契约。
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
| [[FILE_INDEX\|docs/FILE_INDEX.md]] | 查找本项目的关联文档 |
