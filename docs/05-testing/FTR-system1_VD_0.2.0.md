---
title: 功能与工程验证报告
type: report
status: active
version: 0.2.0
date: 2026-10-09
owner: IamWWT
applies_to: System1 Ops
references:
  - docs/FILE_INDEX.md
---

# 功能与工程验证报告

> 版本: 0.2.0 | 状态: Active
> 适用范围: System1 Ops
> 关联: [[FILE_INDEX|全库索引]]

## 范围与环境

Linux i9-13900K / RTX4090，Python3.12；保留独立torch CPU/CUDA环境。GitHub Windows native流程验证0.8B官方Q8、MSVC/CMake构建、PowerShell转发、真实HTTP与重启。目标Windows laptop本身未测。

## 验证方法

| 内容 | 可复跑命令 | 证据 |
|---|---|---|
| 格式/类型/单测/文档/构建 | uv run python scripts/quality_gate.py | 本机evidence/engineering-quality-gate.txt；Linux/Windows CI |
| 原生协议与请求隔离 | python verify_native.py | evidence/engineering-native-real.txt |
| 真机三题型 | ./system1.sh smoke all | 各模型真实Jev响应 |
| 运维页面 | 浏览器管理认证、三模型调试、桌面/手机宽度 | evidence/browser-final.json与截图 |
| 原生构建 | cmake --build .native-build/bridge --config Release -j4 | evidence/engineering-native-build.txt |
| 性能与数值门槛 | python benchmark.py --model all --preset quick | [[05-testing/NFTR-system1_VD_0.2.0]]与公开reports/samples |

## 当前结论

迁移前基线28项通过；结构整理并增加日志/文档回归测试后31项本地通过。Ruff、14模块mypy、Windows平台类型检查、文档、C++格式、JS语法、wheel/sdist构建和shell检查通过；全包覆盖37%。真实native与三个模型HTTP/页面验证通过，8882–8885恢复。最终Linux/Windows CI结果以04-progress中的本轮链接为准，未通过前不标为通过。

## 需求映射

[[01-requirements/BRD-system1_U_0.2.0]]逐项列出实现和验证。公开报告不包含密钥、权重、私有配置或个人路径。原始本机日志保存于Git忽略的evidence；CI保留测试artifact。

## 参考文档

| 文档 | 用途 |
|---|---|
| [[FILE_INDEX|docs/FILE_INDEX.md]] | 查找本项目的关联文档 |
