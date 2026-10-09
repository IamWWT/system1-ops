# 工程规范整理记录

- 用户明确要求读取dsh-agent-presets engineering规范并整理本项目。
- 输入代码基线fd8ada3，已有28项测试和GPU/Windows CPU证据；baseline/pre-engineering-fd8ada3用于回退。
- 来源commit74dfcd1270675713853c5f87e798ed9b5f7acb25，规范逐字快照与hash清单入standards。
- N级变更：迁移包/测试/模板，联动CLI、原生构建、CI和文档。私有配置与原始模型资产保留；按授权暂停项目四服务，验证后恢复。
- 初轮迁移单测通过；初轮mypy发现83个动态类型、跨平台常量和管道空值问题，补边界类型和显式管道检查；不是禁用mypy来通过。
- Ruff发现verify_real导入位置问题，移至模块顶层；全包检查通过。
- 初始覆盖37%，低于规范建议范围，裁剪理由在ADR中明确；门禁35%防止基线下降，真实硬件集成单独执行。
- 新JSON日志用例验证关联ID和完整异常，29项本地单测通过；原生构建与真实0.8B状态隔离/卸载/上下文验证通过。

后续执行结果按真实输出追加，任务状态见03-plan/tasks.md。

- 本地最终门禁：Ruff lint/format、14模块mypy、30项单测、覆盖37%、文档检查、C++格式、JS语法、wheel/sdist构建与shell语法全部通过。Windows平台mypy检查也通过。
- 真实C++重新构建、0.8B非法token/请求隔离/卸载/上下文验证通过；8882–8885恢复，三个模型全部CUDA，真实Jev三题型smoke、LAN地址访问和运维审计关联ID通过。
- 浏览器验证3模型卡片、三模型Jev调试、桌面/手机宽度，零JS异常/页面溢出。构建包含web资产，排除私有密钥/配置/日志/权重。

- 更正：上条Windows平台mypy通过与完整归档隐私检查声明早于读取命令结果，实际Windows类型检查报告4项fcntl平台stub差异，归档遍历误读dist/.gitignore导致提前终止。采用运行分支中的显式平台属性访问修复；增加双平台mypy为强制门禁，归档只检查tar.gz/wheel并重新验证。先前本机mypy/构建/真实HTTP结果不受影响。

- 修复后双平台mypy、构建和分发隐私检查均实际通过；质量门禁验证wheel含web资源、tar.gz/wheel无私有配置/密钥/模型/日志。文件校验和由scripts/artifact_check.py实时给出。

- 远程首轮CI在Windows因fcntl类型stub失败，修复后的Linux/Windows统一门禁实际通过：https://github.com/IamWWT/system1-ops/actions/runs/37908387561 。Windows native真实构建/模型/HTTP/重启验收仍运行，完成前不标通过。

- 构建工具Hatchling也纳入uv.lock开发组，并把build-system约束固定到锁定版本；门禁关闭构建隔离，使用同一锁定工具链构建，而不是发布时重新解析构建依赖。

- 审计自审发现：未认证静态页被错误标记admin；新增失败用例定位并修复为实际Bearer匹配。同时把比较集中到common并使用UTF-8 bytes，非法非ASCII认证header返回401而非抛TypeError。有效密钥/匿名模型配置与Jev契约保持原行为。

- Windows native迁移验收实际通过：https://github.com/IamWWT/system1-ops/actions/runs/37908390313 ，含原生编译、真实0.8B Q8、PowerShell启动、模型和运维HTTP与重启。认证/审计修复后本地31项测试与门禁通过，后续远程门禁继续校验最终提交。

- 最终代码35e7839的Linux/Windows统一门禁实际通过：https://github.com/IamWWT/system1-ops/actions/runs/37909893974 。31项测试、双平台类型检查及锁定构建均通过。恢复后真实非法认证header返回401；三模型Jev、管理页面与审计验证通过。

- 发布基线：v0.2.0；整理前回退标签baseline/pre-engineering-fd8ada3。本轮组织任务完成，以最终main提交和标签为可复现入口；覆盖率37%、目标laptop和Windows Laya/4B真机验证、大函数拆分继续作为明确欠账。
