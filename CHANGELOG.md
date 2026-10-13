# 变更记录

## 0.2.0

- 按dsh-agent-presets engineering规范组织src包、tests、configs、scripts和阶段文档；保留公开入口桥接。
- 固定规范来源/hash与uv依赖锁；加入Ruff、mypy、覆盖与跨平台文档/构建门禁。
- 服务JSON日志保留请求ID和异常堆栈；运维HTTP增加无token审计。
- 基线与变更授权、风险和验证结果记录在docs/04-progress/2026-10-09-engineering.md。

## 0.3.0

- 根据用户完整engineering模式返工要求，将运行数据集中.local、工具归scripts，公开样本归测试阶段。
- 统一STATE路径和外部运行目录；保留旧配置读取用于迁移，真实配置解析值保持。
- 全文件索引、根目录归属门禁、持久化设计、需求追踪、关口/基线/SESSION三同步与标签产品归档。
- 命令路径变化：python bootstrap.py/benchmark.py/verify_*.py改为scripts下同名入口；安装脚本也在scripts。system1.sh/ps1保持日常入口。
- 2026-10-12：运维台新增按需状态检查（模型卡片“检查状态”与“检查全部”，GET /ops/models/{name}/check：进程/健康/加载/端口占用/停止时预检，只读端点），覆盖停模型确认与切换决策模型场景；README补全基本运维方式与模型切换流程（R11）。
- 2026-10-13：修复状态检查把“本模型实例占用的端口”误报为异常——占用者按 /health 的 model 字段辨认，是自身实例时报“运行中（未纳入管理记录）”并带出真实设备/内存/请求数，仅外来进程或其它模型才报端口冲突；卡片状态同步（running/unmanaged + health）。新增3个回归用例；/ops/state 增加 unmanaged 字段。
