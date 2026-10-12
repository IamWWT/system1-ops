"use strict";
const $ = (id) => document.getElementById(id);
let key = "", state = null, refreshing = false, auth = "none";
const AUTH_TEXT = {
  none: "连接状态检查中…",
  needkey: "未连接 · 服务端已启用管理密钥，请输入",
  readonly: "未连接 · 服务端未启用管理密钥（只读）",
  ok: "已连接 · 密钥有效（长期有效；修改密钥或重启运维台后需重新输入，页面刷新后也需重新输入）",
  invalid: "密钥无效或已失效：请重新输入",
};
function setAuth(mode) {
  if (mode === "invalid" && auth !== "invalid") {
    key = "";
    $("key").value = "";
  }
  auth = mode;
  const el = $("authState");
  el.textContent = AUTH_TEXT[mode];
  el.className = "status" + (mode === "ok" ? " ok" : mode === "invalid" ? " fail" : "");
  if (mode === "invalid") notice("管理密钥无效或已失效：请重新输入（若刚修改了 .local/.env 的 SYSTEM1_ADMIN_KEY，需先重启运维台加载新密钥）", true);
}
const checks = {}, checkLines = {};
const notice = (message, failed = false) => { $("notice").textContent = message; $("notice").className = failed ? "fail" : ""; };
async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (key) headers.Authorization = `Bearer ${key}`;
  const response = await fetch(path, { ...options, headers });
  const body = await response.json().catch(() => ({}));
  if (response.status === 401) {
    setAuth(key ? "invalid" : "needkey");
    throw new Error(body.error || `HTTP ${response.status}`);
  }
  if (!response.ok) throw new Error(body.error || `HTTP ${response.status}`);
  return body;
}
const text = (tag, value, className) => { const element = document.createElement(tag); element.textContent = value; if (className) element.className = className; return element; };
function models(rows) {
  $("models").replaceChildren();
  for (const row of rows) {
    const card = text("article", "", "card"), health = row.health;
    card.append(text("h2", row.name), text("div", health ? (health.loaded ? "● 已加载" : "● 空闲，按需加载") : row.running ? "● 启动中 / 未就绪" : "○ 已停止", `status ${health ? "ok" : ""}`));
    const values = { 端口: row.port, 设备: health?.device || row.config.device, 精度: health?.precision || "—", 内存: health?.rss_mb ? `${health.rss_mb} MiB` : "—", 上下文: health?.max_length || row.config.context_length, 最近耗时: health?.metrics?.last_latency_ms != null ? `${health.metrics.last_latency_ms} ms` : "—", 请求数: health?.metrics?.requests ?? "—" };
    const dl = document.createElement("dl");
    for (const [label, value] of Object.entries(values)) dl.append(text("dt", label), text("dd", String(value)));
    card.append(dl);
    const actions = text("div", "", "actions");
    const checkButton = text("button", "检查状态");
    checkButton.addEventListener("click", () => runCheck(row.name));
    actions.append(checkButton);
    for (const [action, label] of [["start", "启动"], ["restart", "重启"], ["stop", "停止"], ["benchmark", "性能测试"]]) {
      const button = text("button", label, action === "stop" ? "danger" : "");
      button.disabled = !state.controls_enabled;
      button.addEventListener("click", () => control(row.name, action)); actions.append(button);
    }
    card.append(actions);
    const checkLine = text("p", checks[row.name] ? checks[row.name].text : "", "status");
    checkLine.style.margin = "10px 0 0";
    if (checks[row.name]) checkLine.classList.add(checks[row.name].failed ? "fail" : "ok");
    checkLines[row.name] = checkLine;
    card.append(checkLine);
    if (row.error) card.append(text("p", row.error, "fail"));
    if (health?.device_reason) card.append(text("p", health.device_reason));
    const details = document.createElement("details"); details.append(text("summary", "生效配置 / 健康信息"), text("pre", JSON.stringify({ config: row.config, health }, null, 2))); card.append(details);
    $("models").append(card);
  }
  for (const id of ["debugModel", "logModel"]) {
    const previous = $(id).value;
    if ($(id).options.length === rows.length) continue;
    $(id).replaceChildren(...rows.map((row) => { const option = text("option", row.name); option.value = row.name; return option; }));
    if (previous) $(id).value = previous;
  }
}
async function refresh() {
  if (refreshing) return;
  if (auth === "invalid") return;
  refreshing = true;
  try {
    state = await api("/ops/state"); const host = state.hardware;
    setAuth(state.controls_enabled ? "ok" : "readonly");
    $("hardware").replaceChildren(text("span", `${host.platform} / ${host.machine}`), text("span", `CPU ${host.physical_cores ?? "?"} 核 / ${host.logical_cores} 线程 · ${host.cpu_percent}%`), text("span", `可用 RAM ${(host.ram_available_mb / 1024).toFixed(1)} / ${(host.ram_total_mb / 1024).toFixed(1)} GiB`), text("span", host.gpus.length ? host.gpus.map((gpu) => `${gpu.name} · 可用 ${(gpu.free_mb / 1024).toFixed(1)} GiB`).join(" | ") : "GPU 不可见 / 未安装"));
    models(state.models);
  } catch (error) {
    if (auth !== "invalid" && auth !== "needkey") notice(error.message, true);
  } finally { refreshing = false; }
}
async function logs() { try { if ($("logModel").value) $("logs").textContent = (await api(`/ops/models/${encodeURIComponent($("logModel").value)}/logs`)).text || "暂无日志"; } catch (error) { $("logs").textContent = error.message; } }
async function reports() {
  try {
    const data = await api("/ops/reports"); $("reports").replaceChildren();
    if (!data.results.length) { $("reports").append(text("p", "尚无性能报告。使用模型卡片的性能测试，或运行 scripts/benchmark.py。")); return; }
    const table = document.createElement("table"), head = document.createElement("tr");
    for (const label of ["候选", "状态", "P50 ms", "P95 ms", "峰值 MiB", "兼容检查"]) head.append(text("th", label)); table.append(head);
    for (const row of data.results) { const line = document.createElement("tr"); for (const value of [row.candidate || row.model, row.status, row.p50_ms?.toFixed(1) ?? "—", row.p95_ms?.toFixed(1) ?? "—", row.peak_rss_mb?.toFixed(0) ?? "—", row.compatibility ? (row.compatibility.passed ? "通过" : "未通过") : row.reason || "—"]) line.append(text("td", String(value))); table.append(line); }
    $("reports").append(table);
    const details = document.createElement("details"); details.append(text("summary", "本机推荐与测试条件"), text("pre", JSON.stringify({ recommendations: data.recommendations, hardware: data.hardware, limitations: data.limitations }, null, 2))); $("reports").append(details);
  } catch (error) { $("reports").textContent = error.message; }
}
async function control(model, action) {
  try {
    const job = await api(`/ops/models/${encodeURIComponent(model)}/${action}`, { method: "POST" }); notice(`${model} · ${action} 进行中…`);
    for (;;) { await new Promise((resolve) => setTimeout(resolve, 1500)); const current = await api(`/ops/jobs/${job.id}`); if (current.status !== "running") { notice(current.error || `${model} · ${action} 完成`, current.status === "failed"); break; } }
    await refresh(); await logs(); await reports();
  } catch (error) { notice(error.message, true); }
}
async function runCheck(name) {
  const line = checkLines[name];
  if (line) { line.textContent = "状态检查中…"; line.className = "status"; }
  try {
    const data = await api(`/ops/models/${encodeURIComponent(name)}/check`);
    let detail;
    if (data.managed) {
      detail = data.reachable && data.health
        ? `运行中 · ${data.health.loaded ? "已加载" : "空闲，未加载"}${data.health.device ? ` · ${data.health.device}` : ""}${data.health.precision ? ` · ${data.health.precision}` : ""}${data.health.rss_mb ? ` · ${data.health.rss_mb} MiB` : ""}${data.health.metrics?.last_latency_ms != null ? ` · 最近 ${data.health.metrics.last_latency_ms} ms` : ""}`
        : `进程 ${data.pid} 在运行，但健康检查未通过：${data.error || "无响应"}`;
    } else if (data.port_in_use) detail = `已停止 · 端口 ${data.port} 被占用，可能有残留进程或其他服务`;
    else if (data.error) detail = `已停止 · 预检失败：${data.error}`;
    else detail = `已停止 · 端口 ${data.port} 空闲 · 预检通过，可启动`;
    checks[name] = { text: `${new Date(data.checked_at * 1000).toLocaleTimeString("zh-CN", { hour12: false })} · ${detail}`, failed: data.error != null || (data.managed && !data.reachable) };
    if (line) { line.textContent = checks[name].text; line.className = "status" + (checks[name].failed ? " fail" : " ok"); }
  } catch (error) {
    checks[name] = { text: `状态检查失败：${error.message}`, failed: true };
    if (line) { line.textContent = checks[name].text; line.className = "status fail"; }
  }
  return checks[name];
}
async function checkAll() {
  $("checkAll").disabled = true;
  try {
    const names = (state?.models ?? []).map((row) => row.name);
    if (!names.length) { notice("尚无可检查的模型", true); return; }
    const results = await Promise.all(names.map((name) => runCheck(name)));
    const failed = results.filter((row) => row.failed).length;
    notice(`状态检查完成：${names.length - failed}/${names.length} 正常` + (failed ? `，${failed} 个需要关注` : ""), failed > 0);
  } finally { $("checkAll").disabled = false; }
}
$("request").value = JSON.stringify({ state: "我被重复扣款，请退还第二笔付款。", questions: { team: { type: "choice", instructions: "Which team handles this?", criteria: { billing: "Billing and refunds", technical: "Technical problems", other: "Other issues" } }, refund: { type: "noul", instructions: "Is a refund requested?" } } }, null, 2);
$("connect").onclick = async () => {
  key = $("key").value;
  $("key").value = "";
  auth = "none";
  notice("");
  setAuth("none");
  await refresh();
  if (auth === "invalid") return;
  if (auth === "readonly") notice("服务端未启用管理密钥，页面只读。设置 SYSTEM1_ADMIN_KEY 并重启运维台后可启用控制和调试。");
  await logs();
  await reports();
};
$("send").onclick = async () => {
  $("send").disabled = true;
  try { const body = JSON.parse($("request").value); const result = await api(`/ops/debug/${encodeURIComponent($("debugModel").value)}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }); $("debugMeta").textContent = `HTTP ${result.http_status} · ${result.latency_ms.toFixed(1)} ms`; $("response").textContent = JSON.stringify(result.body, null, 2); await refresh(); await logs(); }
  catch (error) { $("response").textContent = error.message; } finally { $("send").disabled = false; }
};
$("refreshLogs").onclick = logs; $("logModel").onchange = logs; $("refreshReports").onclick = reports; $("checkAll").onclick = checkAll;
refresh().then(() => { logs(); reports(); }); setInterval(() => { if (auth !== "invalid") { refresh(); if ($("live").checked) logs(); } }, 5000);
