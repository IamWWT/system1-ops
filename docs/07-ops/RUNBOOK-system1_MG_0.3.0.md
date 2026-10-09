---
title: 启动维护与回退手册
type: guide
status: active
version: 0.3.0
date: 2026-10-09
owner: IamWWT
applies_to: System1 Ops
references:
  - docs/FILE_INDEX.md
---

# 启动维护与回退手册

> 版本: 0.3.0 | 状态: Active
> 适用范围: System1 Ops
> 关联: [[FILE_INDEX|全库索引]]

## 安装与启动

Python3.12、uv，原生后端另需CMake/C++17与对应CUDA工具链。完整用户工作区基于Git checkout。uv锁服务与开发工具，setup-runtime为模型建立独立环境。

```bash
git clone https://github.com/IamWWT/system1-ops.git
cd system1-ops
uv sync --locked
mkdir -p .local
cp configs/example.toml .local/config.toml
./scripts/setup-runtime.sh cpu
export SYSTEM1_PYTHON="$PWD/.venv-cpu/bin/python"
python scripts/bootstrap.py --sources
python scripts/bootstrap.py --models laya startlux-0.8b-q8 startlux-4b-q8
python scripts/bootstrap.py --build-native cpu
# 编辑.local/config.toml的python/source/path与native_binary，或使用对应模板。
./system1.sh doctor all
./system1.sh start all
./system1.sh dashboard start
```

已配置宿主直接执行doctor/start/status，无须覆盖现有.local/config.toml。TOML在配置所在目录解析相对路径；configs模板必须先复制到.local。工具入口位于scripts/bootstrap.py、scripts/benchmark.py、scripts/publish.py与scripts/verify_*.py，实际实现来自system1_ops包。旧版本命令替换见交接记录。

## Windows CPU

```powershell
.\scripts\setup-runtime.ps1 cpu
.\.venv-cpu\Scripts\python.exe scripts/bootstrap.py --sources
.\.venv-cpu\Scripts\python.exe scripts/bootstrap.py --build-native cpu
.\.venv-cpu\Scripts\python.exe scripts/bootstrap.py --models laya startlux-0.8b-q8 startlux-4b-q8
Copy-Item configs/windows-gguf.toml .local/config.toml
$env:SYSTEM1_PYTHON = "$PWD\.venv-cpu\Scripts\python.exe"
$env:SYSTEM1_NATIVE_BINARY = "$PWD\.local\vendor\llama.cpp\build-cpu\bin\Release\system1-native.exe"
# 配置.local/.env管理密钥；或由进程环境提供。
.\system1.ps1 doctor all
.\system1.ps1 start all
.\system1.ps1 dashboard start
```

保留exe同目录DLL/backend文件。低RAM模板跨模型串行、每请求卸载，付出重新加载延迟；RAM足够可关闭该策略。没有原生编译器时用configs/windows-cpu.toml与原始完整权重。目标laptop容量与性能须复测。

## 使用与日常检查

Jev端口和设备由.local/config.toml决定，运维页面用宿主IP加dashboard端口。管理密钥从.local/.env读取，仅页面内存持有。log_payloads默认false；日志和运行状态不提交Git。

```bash
./system1.sh status all
./system1.sh smoke all
./system1.sh logs startlux-4b --follow
./system1.sh restart laya --device cpu --context-length 8192
./system1.sh stop all
./system1.sh dashboard stop
```

start等待预检/预加载warm-up/健康；--no-wait只建进程。preload=false按需加载，空闲卸载不停止HTTP。PID和创建时间匹配才停止，进程异常无自动重启；systemd/Task Scheduler可由用户部署场景接管。

## 故障与证据

| 症状 | 处理 |
|---|---|
| Git连接127.0.0.1:7897被拒 | git config --show-origin --get-regexp 'http.*proxy|https.*proxy'定位；修复实际代理或单次直连覆盖 |
| 权重缺失 | doctor查metadata和完整分片/GGUF；.incomplete不算完整 |
| torch_cuda=False但native为CUDA | 原生GPU独立于Python torch构建；核对native日志实际层放置 |
| 503/504 | 请求忙/超时，计算可能仍占锁；用health/busy核实后退避 |
| 模型API失败 | 用x-request-id/x-typesafe-request-id查JSON日志与完整exception |
| 端口占用 | 先查实际listener；manager不会覆盖非项目进程，POSIX允许停止服务TIME_WAIT重用 |

JSON日志在.local/logs/<model>.log、dashboard.log；依赖启动在.console.log，原生输出在.native.log。异常堆栈保存完整。管理HTTP审计记录actor/client/path/status/latency与request_id，不打印认证token。原生日志按重新加载时大小轮转。

## 目录与迁移回退

默认运行目录.local；SYSTEM1_STATE_DIR可指定外部运行目录，SYSTEM1_HOME定位源码工作区。配置中的相对路径以配置父目录解析；.local/.env只读取认证键。旧根配置兼容读取仅用于迁移，门禁要求最终归位。

本机迁移清单在.local/migration/moves.json，原配置在.local/migration/config.pre-layout.toml。回退时先停止四服务，将清单中的目标移回原位置并恢复原配置，再使用v0.2.0 worktree。虚拟环境和.native-build不移动，因为解释器shebang和CMake记录绝对路径；移动须重建。

## 交接与产品归档

维护记录使用python scripts/journal.py "实际结果和证据"；会话结束加--handoff --next "下一步和待确认"，同时更新SESSION、当日日志、MEMORY及索引。仅从当前干净验证标签构建产品：uv run python scripts/archive_release.py v0.3.0。归档在.local/products/v0.3.0，manifest.json记录源提交和各文件SHA256，已有版本拒绝覆盖。

## 回退与基线

在另一个worktree检出baseline/pre-engineering-fd8ada3可还原旧目录和入口，复制本机私有配置并指向既有权重/二进制。先停止当前项目服务，检验旧worktree路径与venv，再启动并smoke。禁止git reset --hard清理用户现场。新发布从验证标签构建源码归档并校验SHA256，数据/密钥不进入归档。

配置清单：[[07-ops/CMP-system1_IG_0.3.0]]。取舍：[[02-design/decisions/ADR-001-engineering_CD_0.2.0]]。

## 参考文档

| 文档 | 用途 |
|---|---|
| [[FILE_INDEX|docs/FILE_INDEX.md]] | 查找本项目的关联文档 |

## 变更记录

| 版本 | 日期 | 记录入口 |
|---|---|---|
| 0.3.0 | 2026-10-09 | [[04-progress/2026-10-09-complete-engineering|过程记录]]；历史基线见[[04-progress/baselines]] |
