"use strict";
const $ = (id) => document.getElementById(id);
let key = "", state = null, refreshing = false;
const notice = (message, failed = false) => { $("notice").textContent = message; $("notice").className = failed ? "fail" : ""; };
async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (key) headers.Authorization = `Bearer ${key}`;
  const response = await fetch(path, { ...options, headers });
  const body = await response.json();
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
    for (const [action, label] of [["start", "启动"], ["restart", "重启"], ["stop", "停止"], ["benchmark", "性能测试"]]) {
      const button = text("button", label, action === "stop" ? "danger" : "");
      button.disabled = !state.controls_enabled;
      button.addEventListener("click", () => control(row.name, action)); actions.append(button);
    }
    card.append(actions);
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
  refreshing = true;
  try {
    state = await api("/ops/state"); const host = state.hardware;
    $("hardware").replaceChildren(text("span", `${host.platform} / ${host.machine}`), text("span", `CPU ${host.physical_cores ?? "?"} 核 / ${host.logical_cores} 线程 · ${host.cpu_percent}%`), text("span", `可用 RAM ${(host.ram_available_mb / 1024).toFixed(1)} / ${(host.ram_total_mb / 1024).toFixed(1)} GiB`), text("span", host.gpus.length ? host.gpus.map((gpu) => `${gpu.name} · 可用 ${(gpu.free_mb / 1024).toFixed(1)} GiB`).join(" | ") : "GPU 不可见 / 未安装"));
    models(state.models);
    if (!state.controls_enabled) notice("只读模式：设置 SYSTEM1_ADMIN_KEY 后重新启动运维台，可启用控制和调试。");
  } catch (error) { notice(error.message, true); } finally { refreshing = false; }
}
async function logs() { try { if ($("logModel").value) $("logs").textContent = (await api(`/ops/models/${encodeURIComponent($("logModel").value)}/logs`)).text || "暂无日志"; } catch (error) { $("logs").textContent = error.message; } }
async function reports() {
  try {
    const data = await api("/ops/reports"); $("reports").replaceChildren();
    if (!data.results.length) { $("reports").append(text("p", "尚无性能报告。使用模型卡片的性能测试，或运行 benchmark.py。")); return; }
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
$("request").value = JSON.stringify({ state: "我被重复扣款，请退还第二笔付款。", questions: { team: { type: "choice", instructions: "Which team handles this?", criteria: { billing: "Billing and refunds", technical: "Technical problems", other: "Other issues" } }, refund: { type: "noul", instructions: "Is a refund requested?" } } }, null, 2);
$("connect").onclick = async () => { key = $("key").value; $("key").value = ""; notice(""); await refresh(); await logs(); await reports(); };
$("send").onclick = async () => {
  $("send").disabled = true;
  try { const body = JSON.parse($("request").value); const result = await api(`/ops/debug/${encodeURIComponent($("debugModel").value)}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }); $("debugMeta").textContent = `HTTP ${result.http_status} · ${result.latency_ms.toFixed(1)} ms`; $("response").textContent = JSON.stringify(result.body, null, 2); await refresh(); await logs(); }
  catch (error) { $("response").textContent = error.message; } finally { $("send").disabled = false; }
};
$("refreshLogs").onclick = logs; $("logModel").onchange = logs; $("refreshReports").onclick = reports;
refresh().then(() => { logs(); reports(); }); setInterval(() => { refresh(); if ($("live").checked) logs(); }, 5000);
