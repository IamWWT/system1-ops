# System1 Ops 工程协作入口

1. 先读README、docs/04-progress/SESSION.md、MEMORY、docs/00-request/request.md；目标只允许system1-ops，父目录独立仓库只读。读取交接的进行中/下一步，再按用户当前要求继续。
2. 完整工作方式真源docs/03-plan/PP-engineering_CD_0.3.0.md；规范从standards/README渐进加载。需求原话/假设/验收先落盘，目标与差距分离，七阶段关口不能凭CI自行替代。
3. 当前结构与文件持久化见SAD、CLM；日常命令system1.sh/ps1，工具在scripts，私有配置与运行数据.local。新目录/文件必须登记FILE_INDEX，禁止把运行数据写回根目录。
4. 仅main小批提交；uv sync --locked与scripts/quality_gate.py统一验证。原生/路径/模型变更补真实用户配置HTTP和Windows证明；失败与回退追加当日日志。
5. 现状、过程、决策分离；ADR及历史只增不改；移动文件同批修全文引用。正式文档须元数据、参考与版本变更入口，目录有index，索引覆盖全部维护文件。
6. 结束前SESSION、当日日志、MEMORY三同步；基线登记表、唯一最新标签、产品库与SHA256齐备。已授权维护/测试/public推送继续，不重复请示；新不可逆范围再向用户确认。
