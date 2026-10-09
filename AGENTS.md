# System1 Ops 开发入口

1. 开始修改时先读README.md、docs/FILE_INDEX.md、docs/04-progress/index.md；从standards/README.md选择任务相关规范。
2. 改目录/模块时读docs/02-design/SAD-system1_HD_0.2.0.md；新取舍记ADR。兼容和规范裁剪以docs/02-design/decisions/ADR-001-engineering_CD_0.2.0.md为准。
3. 运行config.toml和.env在项目根；用户原始模型、vendor、venv、日志与运行数据保持Git忽略。修改代码时保留已公开CLI、Jev接口和PID身份校验。
4. 开发先在特性分支；以uv.lock工具链运行uv run python scripts/quality_gate.py。模型/原生路径变更还需真实模型与平台验证，记录实际输出，不用mock替代外部验收。
5. 文档采用docs的英文编号阶段目录。现状、过程和决策分开；新增/移动Markdown同步目录索引和FILE_INDEX，并运行scripts/doc_check.py。
6. 日常变更按用户已授权范围继续；涉及新的不可逆操作再确认。失败与回退追加04-progress记录。未测能力明确标注，密钥和个人日志留在本机。
