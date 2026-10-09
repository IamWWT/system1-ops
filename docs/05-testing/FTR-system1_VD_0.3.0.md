---
title: 功能与工程验证报告
type: report
status: active
version: 0.3.0
date: 2026-10-09
owner: IamWWT
applies_to: System1 Ops
references:
  - docs/FILE_INDEX.md
---

# 功能与工程验证报告

> 版本: 0.3.0 | 状态: Active
> 适用范围: System1 Ops
> 关联: [[FILE_INDEX|全库索引]]

## 范围与环境

Linux i9-13900K / RTX4090，Python3.12；保留独立torch CPU/CUDA环境。GitHub Windows native流程验证0.8B官方Q8、MSVC/CMake构建、PowerShell转发、真实HTTP与重启。目标Windows laptop本身未测。

## 验证方法

| 内容 | 可复跑命令 | 证据 |
|---|---|---|
| 格式/类型/单测/文档/构建 | uv run python scripts/quality_gate.py | 本机.local/evidence/layout-gate.txt；Linux/Windows CI |
| 原生协议与请求隔离 | python scripts/verify_native.py | .local/evidence/layout-native.txt |
| 真机三题型 | ./system1.sh smoke all | 各模型真实Jev响应 |
| 运维页面 | 浏览器管理认证、三模型调试、桌面/手机宽度 | .local/evidence/browser-final.json与截图 |
| 原生构建 | cmake --build .native-build/bridge --config Release -j4 | .local/evidence/engineering-native-build.txt |
| 性能与数值门槛 | python scripts/benchmark.py --model all --preset quick | [[05-testing/NFTR-system1_VD_0.2.0]]与公开docs/05-testing/samples |

## 当前结论

33项本机测试通过，14模块mypy及Windows/Linux类型检查、格式/文档/全文件目录归属、JS/C++格式、锁定构建与制品隐私检查通过，覆盖率37%。三个模型迁移后真实HTTP、原生CPU异常恢复/状态隔离/卸载、管理页面和桌面/手机宽度通过。证据位于.local/evidence/layout-*.txt；远程Windows与发布的实际结论见[[04-progress/2026-10-09-complete-engineering]]。

## 非功能检查

| 项目 | 验证 | 当前边界 |
|---|---|---|
| 安全 | 管理/错误Bearer用例，制品私有数据检查 | 模型匿名模式保留，公网TLS与多租户未实现 |
| 可靠性 | PID身份、端口、共享锁、原生请求隔离/卸载 | 无自动进程重启；旧版整机回退未演练 |
| 性能/资源 | 本轮不改推理数学或线程预算，既有NFTR数据保留；低RAM并发用例 | 无新性能提高数字；设备迁移性能待测 |
| 可观测 | 真实HTTP/JSON日志、管理调试、报告迁移 | payload默认关闭，异常堆栈完整 |
| 可维护/迁移 | 全维护文件索引、交接/基线记录、双平台门禁 | 隐藏位置绑定工具未移动；大函数待拆 |

## 需求映射

[[01-requirements/BRD-system1_U_0.3.0]]逐项列出实现和验证。公开报告不包含密钥、权重、私有配置或个人路径。原始本机日志保存于Git忽略的.local/evidence；CI保留测试artifact。

## 参考文档

| 文档 | 用途 |
|---|---|
| [[FILE_INDEX|docs/FILE_INDEX.md]] | 查找本项目的关联文档 |

## 变更记录

| 版本 | 日期 | 记录入口 |
|---|---|---|
| 0.3.0 | 2026-10-09 | [[04-progress/2026-10-09-complete-engineering|过程记录]]；历史基线见[[04-progress/baselines]] |
