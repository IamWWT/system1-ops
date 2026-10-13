# 工程进度记录

- 2026-10-13T22:45 定位并修复“状态检查把正常运行的服务误报为异常”：用户报告三模型卡片检查后均显示“已停止 · 端口 8882/8883/8884 被占用，可能有残留进程或其他服务”，实际三端口都由本模型实例正常服务（/health status=ok）。真因：/ops/models/{name}/check 与 /ops/state 卡片状态只认 .local/run/<name>.json 管理记录，记录缺失或失效时不辨认占用者，直接按“端口在用=异常”处理。修复：占用者按 /health 的 model 字段辨别（复用 request() 既有校验），是本模型实例时报“运行中（未纳入管理记录，本页无法停止）”并带出真实设备/内存/请求数，仅外来进程或其它模型才报端口冲突；/ops/state 新增 unmanaged 字段，卡片状态显示“● 运行中（未纳管 · 已驻留/按需加载）”。验证：39项单测（原36+3新增/更新）与可用质量门全通过（ruff check/format、mypy三平台、pytest、coverage 40%、doc_check、node --check、uv build/artifact_check、bash -n）；clang-format本机缺依赖未跑（本次未触碰native代码）。真实链路：以进程内 dashboard 对准在跑的8882/8883/8884，三模型由“端口被占用”变为 running/unmanaged/reachable 且带出 health（laya rss510.8MB、0.8b 329MB、4b 5457.5MB）；另构造两类假占用者（外来HTTP服务、另一模型在8883）实测仍正确报端口冲突。

- 2026-10-13T22:46 提交 692ae29（fix(dashboard) 辨认端口占用者身份并同步 README/BRD/追溯表/FTR/CHANGELOG/请求原话）已推 public main；本轮版本仍为 0.3.0，未新建标签（用户约定仅main+最新tag v0.3.0）。

- 2026-10-13T22:59 按用户确认范围新增接管能力：stop/restart 在无可用管理记录、但配置端口上 /health 精确回 model=<本模型> 时，按端口反查监听 PID 并结束进程树；start 对未纳管实例打印 already running (no record) 并早退，不再抛端口占用原始异常；本进程无法解析 PID（跨进程命名空间）时报明并指引用户在该实例宿主上手动处理，/health 未标明本模型的占用者一律不动。实现：portable.listener_pids（psutil）、manage.terminate_tree/untracked_instance、stop(name, item)、CLI 与运维台传 item、UI 与 README/RUNBOOK 文案同步。验证：45项单测（较上轮+6）与可用质量门全通过（覆盖率42%）；沙箱内真实子进程两例——本模型实例被接管结束且端口释放、外来占用者保持存活不动；验证只在沙箱内自建端口进行，未触碰线上8882/8883/8884。提交 2cba6fe。
