const $ = (selector) => document.querySelector(selector);
const state = { scenario: null, plan: null, previous: null, changed: new Set() };
const courierColors = ["#4b9a70", "#729ac0", "#d59b54", "#9c7eb4"];

async function api(path, body) {
  const response = await fetch(path, body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : {});
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.detail || "İstek başarısız oldu.");
  return payload;
}

function showError(target, message) { target.textContent = message || ""; }

function mimoAsset(filename) {
  const avatar = $("#mimo-avatar");
  const img = document.createElement("img");
  img.src = `/assets/mimo-${filename}.png`;
  img.alt = "Mimo durumu";
  img.onerror = () => { avatar.textContent = filename === "uyari" ? "🙈" : filename === "basari" ? "🐵" : "🐒"; };
  avatar.textContent = "";
  avatar.append(img);
}

function drawMap(svg, plan, old = false) {
  const stops = state.scenario?.stops || [];
  const depot = state.scenario?.depot;
  if (!depot) return;
  const coords = [depot, ...stops];
  const minLat = Math.min(...coords.map(x => x.lat)), maxLat = Math.max(...coords.map(x => x.lat));
  const minLon = Math.min(...coords.map(x => x.lon)), maxLon = Math.max(...coords.map(x => x.lon));
  const point = item => ({ x: 24 + ((item.lon - minLon) / (maxLon - minLon || 1)) * 312, y: 18 + (1 - (item.lat - minLat) / (maxLat - minLat || 1)) * 188 });
  const byId = Object.fromEntries(stops.map(stop => [stop.id, stop]));
  const routes = plan?.routes || {};
  let markup = `<circle cx="${point(depot).x}" cy="${point(depot).y}" r="10" fill="#eef3ef"/>`;
  for (const [index, [courier, visits]] of Object.entries(routes).entries()) {
    const ordered = visits.map(visit => byId[visit.stop_id]).filter(Boolean);
    if (!ordered.length) continue;
    const pts = [point(depot), ...ordered.map(point), point(depot)];
    markup += `<polyline class="route-line ${old ? "old-line" : ""}" stroke="${courierColors[index % courierColors.length]}" points="${pts.map(p => `${p.x},${p.y}`).join(" ")}"/>`;
  }
  const assigned = new Map();
  Object.entries(routes).forEach(([courier, visits], index) => visits.forEach(visit => assigned.set(visit.stop_id, index)));
  for (const stop of stops) {
    const p = point(stop), route = assigned.get(stop.id);
    const fill = route === undefined ? "#cbd4ce" : courierColors[route % courierColors.length];
    const changed = !old && state.changed.has(stop.id);
    const timeOnly = !old && state.timeOnly?.has(stop.id);
    markup += `<circle class="stop-dot ${changed ? "changed-stop" : timeOnly ? "time-only-stop" : ""}" cx="${p.x}" cy="${p.y}" r="${changed || timeOnly ? 4.1 : 2.6}" fill="${fill}"><title>${stop.id}${changed ? " · değişti" : timeOnly ? " · yalnızca saat kaydı" : ""}</title></circle>`;
  }
  const depotPoint = point(depot);
  markup += `<circle class="depot-dot" cx="${depotPoint.x}" cy="${depotPoint.y}" r="4.2"><title>Depo</title></circle>`;
  svg.innerHTML = markup;
}

function renderResult(data) {
  state.previous = state.plan;
  state.plan = data.plan;
  const changes = data.diff.changes || [];
  state.changed = new Set(changes.filter(change => change.type !== "sadece_saat_kaydi").map(change => change.stop_id));
  state.timeOnly = new Set(changes.filter(change => change.type === "sadece_saat_kaydi").map(change => change.stop_id));
  $("#old-distance").textContent = data.diff.previous_distance_km == null ? "— km" : `${data.diff.previous_distance_km.toFixed(2)} km`;
  $("#new-distance").textContent = `${data.summary.distance_km.toFixed(2)} km`;
  drawMap($("#old-map"), state.previous, true);
  drawMap($("#new-map"), state.plan, false);
  const strip = $("#result-strip");
  strip.classList.toggle("invalid", !data.summary.valid);
  $(".result-icon").textContent = data.summary.valid ? "✓" : "!";
  const skipCount = data.unserved.length;
  $("#result-text").textContent = data.summary.valid
    ? `Gerçekten değişen ${data.diff.meaningful_change_count} durak · saat kayması ${data.diff.time_only_count} · ${data.violations.length} ihlal · ${skipCount} atlanan durak`
    : `Doğrulama başarısız · Plan geçerli değil olarak işaretlendi · ${data.violations.length} ihlal`;
  const details = $("#validation-details");
  const rows = [...data.violations.map(v => `İhlal: ${v.description}`), ...data.unserved.map(x => `Atlandı: ${x.stop_id} — ${x.reason}`)];
  const validationHtml = rows.length ? `<ul>${rows.map(text => `<li>${escapeHtml(text)}</li>`).join("")}</ul>` : "";
  const labels = { kurye_degisti: "Kurye değişti", sira_degisti: "Sıra değişti", sadece_saat_kaydi: "Yalnızca saat kaydı", yeni_atlandi: "Yeni atlandı" };
  const changesHtml = changes.map(change => `<li class="${change.type === "sadece_saat_kaydi" ? "time-only-change" : "meaningful-change"}">${escapeHtml(change.stop_id)} · ${labels[change.type] || change.type}</li>`).join("");
  details.innerHTML = validationHtml + (changesHtml ? `<ul class="change-list">${changesHtml}</ul>` : "");
}

function escapeHtml(text) { const div = document.createElement("div"); div.textContent = text; return div.innerHTML; }

async function refreshLog() {
  try {
    const log = await api("/log");
    const last = log.events.at(-1);
    const stateName = log.mimo_state || "dusunuyor";
    mimoAsset(stateName);
    const captions = { dusunuyor: ["Mimo düşünüyor", "Talimatı yorumluyor"], hesapliyor: ["Mimo hesaplıyor", "Rotayı oluşturuyor"], kontrol: ["Mimo kontrol ediyor", "Kuralları doğruluyor"], basari: ["Mimo tamamladı", "Doğrulama bitti"], uyari: ["Dikkat gerekiyor", "Planı gözden geçir"] };
    $("#mimo-caption").textContent = captions[stateName]?.[0] || "Mimo hazır";
    $("#mimo-log").textContent = last ? `${last.step} · ${new Date(last.timestamp).toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" })}` : captions[stateName]?.[1] || "Talimatını bekliyor";
  } catch (_) { /* API may still be starting. */ }
}

$("#interpret").addEventListener("click", async () => {
  showError($("#interpret-error"), "");
  const text = $("#instruction").value.trim();
  if (!text) { showError($("#interpret-error"), "Önce bir talimat yaz."); return; }
  $("#interpret").disabled = true;
  $("#interpret-status").textContent = "YORUMLANIYOR";
  try {
    const result = await api("/interpret", { text });
    $("#interpret-status").textContent = result.ok ? "ONAY BEKLİYOR" : "ANLAŞILAMADI";
    $("#interpret-status").className = `status-chip ${result.ok ? "ok" : "bad"}`;
    $("#understood").textContent = result.understood_text || result.message;
    $("#understood").classList.toggle("has-text", result.ok);
    $("#constraints").value = JSON.stringify(result.constraints, null, 2);
    $("#approve").disabled = !result.ok;
    if (!result.ok) showError($("#interpret-error"), result.message);
    refreshLog();
  } catch (error) { showError($("#interpret-error"), error.message); }
  finally { $("#interpret").disabled = false; }
});

$("#correct").addEventListener("click", () => {
  try {
    const constraints = JSON.parse($("#constraints").value);
    if (!Array.isArray(constraints.constraints)) throw new Error("constraints alanı bir liste olmalı.");
    $("#approve").disabled = false;
    $("#interpret-status").textContent = "DÜZENLENDİ";
    $("#interpret-status").className = "status-chip ok";
    showError($("#plan-error"), "");
  } catch (error) { showError($("#plan-error"), `JSON okunamadı: ${error.message}`); }
});

$("#approve").addEventListener("click", async () => {
  showError($("#plan-error"), "");
  try {
    const constraints = JSON.parse($("#constraints").value);
    $("#approve").disabled = true;
    mimoAsset("hesapliyor");
    const data = await api("/plan", { constraints });
    renderResult(data);
    refreshLog();
  } catch (error) { showError($("#plan-error"), error.message); mimoAsset("uyari"); }
  finally { $("#approve").disabled = false; }
});

api("/scenario").then(async scenario => {
  state.scenario = scenario;
  $("#stop-count").textContent = `${scenario.stops.length} durak · ${scenario.couriers.length} kurye`;
  const baseline = await api("/plan", { constraints: { constraints: [] } });
  state.plan = baseline.plan;
  $("#old-distance").textContent = `${baseline.summary.distance_km.toFixed(2)} km`;
  $("#new-distance").textContent = `${baseline.summary.distance_km.toFixed(2)} km`;
  drawMap($("#old-map"), state.plan, true);
  drawMap($("#new-map"), state.plan, false);
  refreshLog();
}).catch(() => {});
refreshLog();
setInterval(refreshLog, 3500);
