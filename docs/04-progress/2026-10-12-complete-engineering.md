# 工程进度记录

- 2026-10-12T15:25 运维台新增按需状态检查：GET /ops/models/{name}/check 主动探活（进程/健康/加载/端口占用/停止时预检），模型卡片按钮+检查全部，只读端点无密钥可用；README补全基本运维方式、命令速查与决策模型切换流程（R11，2026-10-12用户需求）。36项单测与完整quality_gate通过；真实8885重启后实测占用/预检通过/只读三态均正确；提交cd19795、a1cdcae、420e330已推public main。

- 2026-10-12T16:01 运维台右上角新增密钥状态指示（未连接/只读/已连接·密钥有效/密钥无效或已失效），失效时明确提示并清空旧密钥；密钥长期有效，仅当前标签页内存，修改密钥或重启运维台后失效。按用户要求纠正Jev表述：UI与README/RUNBOOK/BRD/SAD/术语表统一为“Jev兼容接口/本地决策模型”，不再称Jev模型；历史阶段报告不改写。36项单测与完整quality_gate通过；真实8885三态（无密钥401/正确密钥200/错误密钥401）验证通过，页面文件为磁盘直读无需重启。

- 2026-10-12T16:14 按用户反馈修复密钥登录体验：密钥改为保存于当前标签页会话（sessionStorage，刷新不丢失、关闭标签页清除、不落盘/cookie），失效时清除并明确提示重输；刷新后无需重输密钥。真实浏览器（Playwright+Chromium）对活动8885端到端验证8/8通过：未输入→待输入态、正确密钥→已连接、刷新后保持登录（用户报告的失败场景）、错误密钥→明确失效提示、重输恢复、新会话不自动登录；截图存.local/evidence/2026-10-12-key-session/。README/RUNBOOK密钥语义同步更新，request.md补录用户原话与目标锚定，36项单测与完整quality_gate通过。

- 2026-10-12T16:28 定位并修复“刷新后仍丢失登录”：真因有二——浏览器执行缓存的旧版app.js（静态页无Cache-Control、脚本无版本号），以及密钥原先仅存页面内存。修复：运维台对/与/app.js返回Cache-Control:no-store，页面加载/app.js?v=20261012c强制取新版；密钥连接成功后保存至localStorage（fallback sessionStorage），刷新/新标签页/重启浏览器后自动恢复，新增“清除密钥”按钮，服务端密钥变更时自动清除并明确提示重输。Playwright真实Chromium对活动8885端到端验证9/9通过（新浏览器提示输入→输入连接→新标签页自动连接→刷新保持→模拟重启浏览器自动连接→清除密钥→清除后刷新不再自动→重输恢复），截图存.local/evidence/2026-10-12-key-persist/。36项单测与完整quality_gate通过；RUNBOOK/README密钥语义同步更新。

- 2026-10-12T18:19 用户问: 仪表盘设备显示cpu/cuda看着不对? 空闲是否代表进程存在? 结论: 显示本身准确——laya(配置auto)因GPU仅剩360MB(外部进程ninfer-serve PID605496占22.7GB/共24GB)而auto降级cpu; startlux-0.8b/4b配置即cpu; '空闲'指模型权重因空闲300秒被自动卸载(idle_unload_seconds), 进程仍在运行, 请求时自动重载。修复: /health新增configured_device, UI设备行显示'cpu(配置auto)'式降级标注, 状态措辞改为已驻留/未驻留(按需加载)消除'空闲'歧义; 术语表+README补充。验证: 三worker重启后/health含configured_device(laya=auto/8883,8884=cpu), 4b /v1/systemone真实推理返回billing 0.987, app.js(v=20261012d)已由仪表盘服务含deviceLabel/未驻留, 质量门GATE=0(36测试), native CPU-only二进制重编译同步
