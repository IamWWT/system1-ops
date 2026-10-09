# 完整engineering组织返工记录

- 用户拒绝上一轮“内部目录+CI即完成”的结果。读取完整persona/preset、三随包技能、脚手架、工艺/配置库/文档约束，发现缺GAP/数据持久化设计/会话交接/基线登记表，FILE_INDEX只有Markdown，且本机根目录混有运行资产与工具。
- 上次基线v0.2.0，main=f5eb663；本轮特性分支refactor/complete-engineering。计划先落盘tasks，目标白名单system1-ops；frameworks其他仓库只读，不移动。
- 停止四服务并备份配置，真实移动logs/run/models/reports/evidence/dist与工具。模型路径转成迁移前等价绝对值，密钥保留0600；.venv与.native-build位置绑定不移动。迁移映射在.local/migration/moves.json。
- 初轮回归30通过1失败：低RAM测试patch旧worker.ROOT，而锁已改STATE。更新测试隔离边界，重新运行；没有通过create=True隐藏错误。
- 装配v0.3.0待验证，服务恢复与Windows真实native验收进行中。关口不由目录存在自动视为通过；用户对最终组织的人工验收待交付复核。

- 第二轮回归暴露bootstrap测试仍patch ROOT，实际STATE未隔离；测试fixture曾落入.local/vendor/fixture。已移至迁移归档并修正STATE隔离。ADR-001仅修当前报告引用目标，不改历史决策；新决策在ADR-002。

- 本机33项单测与完整门禁通过，coverage37%；模式docs-audit输出合规无整改项。真实三模型Jev、native CPU状态隔离/错误恢复/卸载与桌面/手机页面通过。父目录本任务续接脚本-C调整为system1-ops，不移动其他仓库，防止工作目录再次漂移。

- 用户新增仅main/一个tag约定；最终清理临时分支与旧标签，回退改用提交哈希/归档，已更新工作协议和当前手册。此前特性分支为真实过程记录，不以旧模板覆盖用户要求。

- 配置完整性比对通过：迁移前后模型/解释器/源/二进制路径等价，设备、线程、上下文和端口未改变，moves.json各目标都存在。首次检查误用系统Python未安装包而报ModuleNotFoundError，改用uv锁环境后实际通过；不把环境导入错误误报模型问题。
- 主分支Linux/Windows统一门禁实际通过：https://github.com/IamWWT/system1-ops/actions/runs/37914525575 。本地及远端只剩main；Windows native新路径仍在编译CPU后端，完成前不登记通过。

- Windows native真实迁移验收通过：https://github.com/IamWWT/system1-ops/actions/runs/37914345721 ，包含新.local/vendor/models路径、真实0.8B CPU原生构建/推理、PowerShell启动、管理API与模型重启。代码之后只有文档/日志artifact选项变化，主分支e8df116双平台门禁通过：https://github.com/IamWWT/system1-ops/actions/runs/37915093701 。
- 关口结论：工程基线、需求走查/追踪、数据模型/架构、开发、测试、部署维护信息均齐备，本轮实现者检查通过；用户对目录观感的最终接受仍由用户复核。覆盖/laptop/Windows Laya/4B与旧版全机回退未演练继续明确保留。
- 按用户单main/单tag要求，旧源码f5eb663已归档至.local/archives/v0.2.0/source-f5eb663.tar并记录SHA256，原私有配置与移动清单保留。旧tag移除后仍可按提交哈希回退。发布以最新v0.3.0及.local/products/v0.3.0/manifest.json为唯一产品依据。

- 2026-10-09T18:06 完整模式组织实现已验证：33测试、双平台CI37915093701、Windows native37914345721、三模型HTTP/浏览器和模式文档审计通过。主分支仅main；产品交付标识v0.3.0，源提交与制品SHA256由.local/products/v0.3.0/manifest.json记录。
