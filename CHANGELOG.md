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
