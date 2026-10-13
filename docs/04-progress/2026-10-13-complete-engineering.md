# 工程进度记录

- 2026-10-13T22:45 定位并修复“状态检查把正常运行的服务误报为异常”：用户报告三模型卡片检查后均显示“已停止 · 端口 8882/8883/8884 被占用，可能有残留进程或其他服务”，实际三端口都由本模型实例正常服务（/health status=ok）。真因：/ops/models/{name}/check 与 /ops/state 卡片状态只认 .local/run/<name>.json 管理记录，记录缺失或失效时不辨认占用者，直接按“端口在用=异常”处理。修复：占用者按 /health 的 model 字段辨别（复用 request() 既有校验），是本模型实例时报“运行中（未纳入管理记录，本页无法停止）”并带出真实设备/内存/请求数，仅外来进程或其它模型才报端口冲突；/ops/state 新增 unmanaged 字段，卡片状态显示“● 运行中（未纳管 · 已驻留/按需加载）”。验证：39项单测（原36+3新增/更新）与可用质量门全通过（ruff check/format、mypy三平台、pytest、coverage 40%、doc_check、node --check、uv build/artifact_check、bash -n）；clang-format本机缺依赖未跑（本次未触碰native代码）。真实链路：以进程内 dashboard 对准在跑的8882/8883/8884，三模型由“端口被占用”变为 running/unmanaged/reachable 且带出 health（laya rss510.8MB、0.8b 329MB、4b 5457.5MB）；另构造两类假占用者（外来HTTP服务、另一模型在8883）实测仍正确报端口冲突。

- 2026-10-13T22:46 提交 692ae29（fix(dashboard) 辨认端口占用者身份并同步 README/BRD/追溯表/FTR/CHANGELOG/请求原话）已推 public main；本轮版本仍为 0.3.0，未新建标签（用户约定仅main+最新tag v0.3.0）。
