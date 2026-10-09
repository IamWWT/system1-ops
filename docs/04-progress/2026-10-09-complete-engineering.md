# 完整engineering组织返工记录

- 用户拒绝上一轮“内部目录+CI即完成”的结果。读取完整persona/preset、三随包技能、脚手架、工艺/配置库/文档约束，发现缺GAP/数据持久化设计/会话交接/基线登记表，FILE_INDEX只有Markdown，且本机根目录混有运行资产与工具。
- 上次基线v0.2.0，main=f5eb663；本轮特性分支refactor/complete-engineering。计划先落盘tasks，目标白名单system1-ops；frameworks其他仓库只读，不移动。
- 停止四服务并备份配置，真实移动logs/run/models/reports/evidence/dist与工具。模型路径转成迁移前等价绝对值，密钥保留0600；.venv与.native-build位置绑定不移动。迁移映射在.local/migration/moves.json。
- 初轮回归30通过1失败：低RAM测试patch旧worker.ROOT，而锁已改STATE。更新测试隔离边界，重新运行；没有通过create=True隐藏错误。
- 装配v0.3.0待验证，服务恢复与Windows真实native验收进行中。关口不由目录存在自动视为通过；用户对最终组织的人工验收待交付复核。

- 第二轮回归暴露bootstrap测试仍patch ROOT，实际STATE未隔离；测试fixture曾落入.local/vendor/fixture。已移至迁移归档并修正STATE隔离。ADR-001仅修当前报告引用目标，不改历史决策；新决策在ADR-002。

- 本机33项单测与完整门禁通过，coverage37%；模式docs-audit输出合规无整改项。真实三模型Jev、native CPU状态隔离/错误恢复/卸载与桌面/手机页面通过。父目录本任务续接脚本-C调整为system1-ops，不移动其他仓库，防止工作目录再次漂移。
