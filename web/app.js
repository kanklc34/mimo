const $ = (selector) => document.querySelector(selector);
const SVG_NS = "http://www.w3.org/2000/svg";
const state = {
  scenario: null, plan: null, previous: null, constraints: { constraints: [] },
  changed: new Set(), timeOnly: new Set(), coordinates: new Map(), depotPoint: null,
  mimoPosition: null, mimoState: null, assetFailed: new Set(), tourId: 0, moveId: 0,
  playTimer: null,
};
const courierColors = ["#4b9a70", "#729ac0", "#d59b54", "#9c7eb4"];
const captions = {
  dusunuyor: ["Mimo düşünüyor", "Talimatı yorumluyor"],
  hesapliyor: ["Mimo hesaplıyor", "Rotayı oluşturuyor"],
  kontrol: ["Mimo kontrol ediyor", "Kuralları doğruluyor"],
  basari: ["Mimo tamamladı", "Doğrulama bitti"],
  uyari: ["Dikkat gerekiyor", "Planı gözden geçir"],
};

async function api(path, body) {
  const response = await fetch(path, body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : {});
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.detail || "İstek başarısız oldu.");
  return payload;
}

function showError(target, message) { target.textContent = message || ""; }
function escapeHtml(text) { const div = document.createElement("div"); div.textContent = String(text ?? ""); return div.innerHTML; }
function courierById(id) { return state.scenario?.couriers.find(courier => courier.id === id); }
function courierName(id) { return courierById(id)?.name || id || ""; }
function stopById(id) { return state.scenario?.stops.find(stop => stop.id === id); }
function formatClock(minutes) {
  const total = 8 * 60 + Number(minutes || 0);
  return `${String(Math.floor(total / 60)).padStart(2, "0")}:${String(total % 60).padStart(2, "0")}`;
}

function mimoAsset(status) {
  const avatar = $("#mimo-avatar");
  const fallback = status === "uyari" ? "🙈" : status === "basari" ? "🐵" : "🐒";
  const mapImage = $("#mimo-marker .mimo-map-image");
  const mapFallback = $("#mimo-marker .mimo-marker-face");
  if (mapImage && mapFallback) {
    mapFallback.textContent = fallback;
    mapImage.classList.toggle("failed", state.assetFailed.has(status));
    if (!state.assetFailed.has(status)) mapImage.setAttribute("href", `/assets/mimo-${status}.png`);
  }
  if (state.assetFailed.has(status)) {
    avatar.textContent = fallback;
    return;
  }
  const img = document.createElement("img");
  img.alt = "Mimo durumu";
  img.onerror = () => {
    state.assetFailed.add(status);
    if (state.mimoState === status) avatar.textContent = fallback;
  };
  img.src = `/assets/mimo-${status}.png`;
  avatar.replaceChildren(img);
}

function setMimoStatus(status) {
  const nextStatus = status || "dusunuyor";
  if (nextStatus === state.mimoState) return;
  state.mimoState = nextStatus;
  mimoAsset(nextStatus);
}

function svgNode(name, attributes = {}) {
  const element = document.createElementNS(SVG_NS, name);
  for (const [key, value] of Object.entries(attributes)) element.setAttribute(key, value);
  return element;
}

function pointFor(item, bounds) {
  return {
    x: 24 + ((item.lon - bounds.minLon) / (bounds.maxLon - bounds.minLon || 1)) * 312,
    y: 18 + (1 - (item.lat - bounds.minLat) / (bounds.maxLat - bounds.minLat || 1)) * 188,
  };
}

function drawMap(svg, plan, old = false) {
  const stops = state.scenario?.stops || [];
  const depot = state.scenario?.depot;
  if (!depot) return;
  const coords = [depot, ...stops];
  const bounds = {
    minLat: Math.min(...coords.map(item => item.lat)), maxLat: Math.max(...coords.map(item => item.lat)),
    minLon: Math.min(...coords.map(item => item.lon)), maxLon: Math.max(...coords.map(item => item.lon)),
  };
  const point = item => pointFor(item, bounds);
  if (!old) {
    state.coordinates = new Map(stops.map(stop => [stop.id, point(stop)]));
    state.depotPoint = point(depot);
  }
  const byId = Object.fromEntries(stops.map(stop => [stop.id, stop]));
  const routes = plan?.routes || {};
  let markup = `<circle cx="${point(depot).x}" cy="${point(depot).y}" r="10" fill="#eef3ef"/>`;
  for (const [index, [courierId, visits]] of Object.entries(routes).entries()) {
    const ordered = visits.map(visit => byId[visit.stop_id]).filter(Boolean);
    if (!ordered.length) continue;
    const pts = [point(depot), ...ordered.map(point), point(depot)];
    markup += `<polyline class="route-line ${old ? "old-line" : ""}" stroke="${courierColors[index % courierColors.length]}" points="${pts.map(p => `${p.x},${p.y}`).join(" ")}"/>`;
  }
  const assigned = new Map();
  Object.entries(routes).forEach(([courierId, visits]) => visits.forEach(visit => assigned.set(visit.stop_id, courierId)));
  for (const stop of stops) {
    const p = point(stop), courierId = assigned.get(stop.id);
    const routeIndex = Object.keys(routes).indexOf(courierId);
    const fill = courierId === undefined ? "#cbd4ce" : courierColors[Math.max(0, routeIndex) % courierColors.length];
    const changed = !old && state.changed.has(stop.id);
    const timeOnly = !old && state.timeOnly.has(stop.id);
    markup += `<circle class="stop-dot ${changed ? "changed-stop" : timeOnly ? "time-only-stop" : ""}" data-stop-id="${escapeHtml(stop.id)}" tabindex="0" role="button" cx="${p.x}" cy="${p.y}" r="${changed || timeOnly ? 4.1 : 2.6}" fill="${fill}"><title>${escapeHtml(stop.id)}${changed ? " · değişti" : timeOnly ? " · yalnızca saat kaydı" : ""}</title></circle>`;
  }
  const depotPoint = point(depot);
  markup += `<circle class="depot-dot" cx="${depotPoint.x}" cy="${depotPoint.y}" r="4.2"><title>Depo</title></circle>`;
  if (!old) {
    for (const [index, courier] of state.scenario.couriers.entries()) {
      markup += `<g class="courier-marker" id="courier-marker-${escapeHtml(courier.id)}" transform="translate(${depotPoint.x} ${depotPoint.y})"><circle r="5.2" fill="${courierColors[index % courierColors.length]}"/><title>${escapeHtml(courier.name)}</title></g>`;
    }
    const mimoStatus = state.mimoState || "dusunuyor";
    markup += `<g id="mimo-marker" class="mimo-marker" transform="translate(${depotPoint.x} ${depotPoint.y})"><rect class="mimo-bubble" x="-120" y="-59" width="240" height="25" style="display:none"/><text id="mimo-bubble-text" x="0" y="-42" text-anchor="middle" textLength="224" lengthAdjust="spacingAndGlyphs"></text><circle class="mimo-marker-body" r="22"/><image class="mimo-map-image${state.assetFailed.has(mimoStatus) ? " failed" : ""}" href="/assets/mimo-${mimoStatus}.png" x="-22" y="-22" width="44" height="44" preserveAspectRatio="xMidYMid meet"/><text class="mimo-marker-face" x="0" y="5" text-anchor="middle">🐒</text></g>`;
    state.mimoPosition = depotPoint;
  }
  svg.innerHTML = markup;
  if (!old) {
    const mapImage = $("#mimo-marker .mimo-map-image");
    mapImage?.addEventListener("error", () => {
      const status = state.mimoState || "dusunuyor";
      state.assetFailed.add(status);
      mapImage.classList.add("failed");
      const face = $("#mimo-marker .mimo-marker-face");
      if (face) face.textContent = status === "uyari" ? "🙈" : status === "basari" ? "🐵" : "🐒";
    });
    renderTimelineMarkers();
  }
}

function setBubble(text) {
  const message = String(text || "").trim();
  const bubble = $("#mimo-bubble-text");
  if (bubble) bubble.textContent = message;
  const rect = $("#mimo-marker .mimo-bubble");
  if (rect) rect.style.display = message ? "" : "none";
}

function walkTo(target, duration = 650) {
  const marker = $("#mimo-marker");
  if (!marker || !target) return Promise.resolve();
  const moveId = ++state.moveId;
  const origin = state.mimoPosition || state.depotPoint || target;
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reducedMotion || duration <= 0) {
    marker.setAttribute("transform", `translate(${target.x} ${target.y})`);
    state.mimoPosition = target;
    return Promise.resolve();
  }
  return new Promise(resolve => {
    const started = performance.now();
    const frame = now => {
      if (moveId !== state.moveId) { resolve(); return; }
      const progress = Math.min(1, (now - started) / duration);
      const eased = progress * progress * (3 - 2 * progress);
      const current = { x: origin.x + (target.x - origin.x) * eased, y: origin.y + (target.y - origin.y) * eased };
      marker.setAttribute("transform", `translate(${current.x} ${current.y})`);
      state.mimoPosition = current;
      if (progress < 1) requestAnimationFrame(frame);
      else { state.mimoPosition = target; resolve(); }
    };
    requestAnimationFrame(frame);
  });
}

function pause(ms, tourId) {
  return new Promise(resolve => {
    const timer = setTimeout(() => resolve(tourId === state.tourId), ms);
    if (tourId !== state.tourId) { clearTimeout(timer); resolve(false); }
  });
}

function changeMessage(change, unservedById) {
  const stop = stopById(change.stop_id);
  const stopName = stop?.id || change.stop_id;
  if (change.type === "kurye_degisti") return `${stopName}: ${courierName(change.old_courier_id)}'ten ${courierName(change.new_courier_id)}'ye geçti`;
  if (change.type === "sira_degisti") return `${stopName}: sırası değişti`;
  if (change.type === "yeni_atlandi") return `${stopName}: atlandı: ${unservedById.get(change.stop_id) || ""}`;
  return "";
}

async function runTour(data) {
  const tourId = ++state.tourId;
  const changes = (data.diff?.changes || []).filter(change => ["kurye_degisti", "sira_degisti", "yeni_atlandi"].includes(change.type));
  const unservedById = new Map((data.unserved || []).map(item => [item.stop_id, item.reason]));
  for (const change of changes) {
    if (tourId !== state.tourId) return;
    const target = state.coordinates.get(change.stop_id);
    if (!target) continue;
    setBubble(changeMessage(change, unservedById));
    await walkTo(target);
    if (!await pause(1200, tourId)) return;
  }
  const lastViolation = [...(data.violations || [])].reverse().find(violation => violation.stop_id && state.coordinates.has(violation.stop_id));
  if ((data.violations || []).length) {
    if (tourId !== state.tourId) return;
    if (lastViolation) {
      setBubble(`${stopById(lastViolation.stop_id)?.id || lastViolation.stop_id}: ${lastViolation.description}`);
      await walkTo(state.coordinates.get(lastViolation.stop_id));
    } else {
      setBubble(data.violations.at(-1).description);
    }
    await refreshLog();
    return;
  }
  if (tourId !== state.tourId) return;
  setBubble("");
  await walkTo(state.depotPoint);
  await refreshLog();
}

function renderResult(data, { tour = true } = {}) {
  state.previous = state.plan || (!tour && data.diff?.previous_distance_km == null ? data.plan : null);
  state.plan = data.plan;
  state.constraints = data.constraints || { constraints: [] };
  const changes = data.diff?.changes || [];
  state.changed = new Set(changes.filter(change => change.type !== "sadece_saat_kaydi").map(change => change.stop_id));
  state.timeOnly = new Set(changes.filter(change => change.type === "sadece_saat_kaydi").map(change => change.stop_id));
  $("#old-distance").textContent = data.diff?.previous_distance_km == null ? "— km" : `${data.diff.previous_distance_km.toFixed(2)} km`;
  $("#new-distance").textContent = `${data.summary.distance_km.toFixed(2)} km`;
  drawMap($("#old-map"), state.previous, true);
  drawMap($("#new-map"), state.plan, false);
  const strip = $("#result-strip");
  strip.classList.toggle("invalid", !data.summary.valid);
  $(".result-icon").textContent = data.summary.valid ? "✓" : "!";
  $("#result-text").textContent = data.summary.valid
    ? `Gerçekten değişen ${data.diff.meaningful_change_count} durak · saat kayması ${data.diff.time_only_count} · ${data.violations.length} ihlal · ${data.unserved.length} atlanan durak`
    : `Doğrulama başarısız · ${data.violations.length} ihlal`;
  renderChangeDetails(data);
  if (tour) void runTour(data);
}

function renderChangeDetails(data) {
  const details = $("#validation-details");
  const rows = [];
  for (const violation of data.violations || []) rows.push(`<li>İhlal: ${escapeHtml(violation.description)}</li>`);
  for (const item of data.unserved || []) rows.push(`<li>Atlandı: ${escapeHtml(item.stop_id)} — ${escapeHtml(item.reason)}</li>`);
  const changes = data.diff?.changes || [];
  const meaningful = changes.filter(change => change.type !== "sadece_saat_kaydi");
  const courierChange = change => `${escapeHtml(change.stop_id)} · ${escapeHtml(courierName(change.old_courier_id))} → ${escapeHtml(courierName(change.new_courier_id))}`;
  for (const change of meaningful) {
    const label = change.type === "kurye_degisti" ? courierChange(change)
      : change.type === "sira_degisti" ? `${escapeHtml(change.stop_id)} · sırası değişti`
        : `${escapeHtml(change.stop_id)} · atlandı`;
    rows.push(`<li>${label}</li>`);
  }
  const timeOnly = changes.filter(change => change.type === "sadece_saat_kaydi");
  const timeRows = timeOnly.map(change => `<li>${escapeHtml(change.stop_id)} · ${escapeHtml(formatClock(change.old_arrival_min))} → ${escapeHtml(formatClock(change.new_arrival_min))}</li>`).join("");
  details.innerHTML = rows.length ? `<ul>${rows.join("")}</ul>` : "";
  if (timeOnly.length) details.insertAdjacentHTML("beforeend", `<details class="time-only-details"><summary>+${timeOnly.length} saat kayması (göster)</summary><ul>${timeRows}</ul></details>`);
}

function matchingConstraints(stop, courierId) {
  return (state.constraints.constraints || []).filter(rule =>
    (rule.type === "tag_deadline" && stop.tags.includes(rule.tag)) ||
    (rule.type !== "tag_deadline" && courierId && rule.courier_id === courierId));
}

function visitForStop(stopId) {
  for (const [courierId, visits] of Object.entries(state.plan?.routes || {})) {
    const visit = visits.find(item => item.stop_id === stopId);
    if (visit) return { courierId, visit };
  }
  return null;
}

function constraintSummary(rule) {
  if (rule.type === "courier_unavailable_after") return `${courierName(rule.courier_id)} ${formatClock(rule.time_min)} sonrası yok`;
  if (rule.type === "max_stops") return `${courierName(rule.courier_id)} en fazla ${rule.n} durak`;
  if (rule.type === "tag_deadline") return `${rule.tag}: ${formatClock(rule.within_minutes_from_start)} öncesi`;
  return "";
}

function showStopDetails(stopId) {
  state.tourId += 1;
  const stop = stopById(stopId);
  if (!stop) return;
  const assigned = visitForStop(stopId);
  const courierId = assigned?.courierId;
  const courier = courierById(courierId);
  const constraints = matchingConstraints(stop, courierId).map(constraintSummary);
  const details = [stop.id, courier?.name || "Atanmadı", assigned ? formatClock(assigned.visit.arrival_min) : "", ...constraints].filter(Boolean);
  setBubble(details.join(" · "));
  void walkTo(state.coordinates.get(stopId));
}

function routePosition(courier, visits, minute) {
  let previousPoint = state.depotPoint;
  let previousTime = courier.shift_start;
  for (const visit of visits) {
    const stopPoint = state.coordinates.get(visit.stop_id);
    const stop = stopById(visit.stop_id);
    if (!stopPoint || !stop) continue;
    const arrival = visit.arrival_min;
    if (minute <= arrival) {
      const span = Math.max(1, arrival - previousTime);
      const ratio = Math.max(0, Math.min(1, (minute - previousTime) / span));
      return { x: previousPoint.x + (stopPoint.x - previousPoint.x) * ratio, y: previousPoint.y + (stopPoint.y - previousPoint.y) * ratio };
    }
    const serviceEnd = arrival + stop.service_min;
    if (minute <= serviceEnd) return stopPoint;
    previousPoint = stopPoint;
    previousTime = serviceEnd;
  }
  return previousPoint;
}

function renderTimelineMarkers() {
  if (!state.scenario || !state.plan || !state.depotPoint) return;
  const minute = Number($("#time-slider").value);
  $("#time-label").textContent = formatClock(minute);
  const unavailableRules = new Map((state.constraints.constraints || [])
    .filter(rule => rule.type === "courier_unavailable_after")
    .map(rule => [rule.courier_id, rule.time_min]));
  const labels = [];
  for (const courier of state.scenario.couriers) {
    const unavailableAt = Math.min(courier.shift_end, unavailableRules.get(courier.id) ?? courier.shift_end);
    const effectiveMinute = Math.min(courier.shift_start + minute, unavailableAt);
    const visits = state.plan.routes[courier.id] || [];
    const pos = routePosition(courier, visits, effectiveMinute);
    const marker = $(`#courier-marker-${CSS.escape(courier.id)}`);
    if (marker) {
      marker.setAttribute("transform", `translate(${pos.x} ${pos.y})`);
      marker.classList.toggle("off-shift", courier.shift_start + minute >= unavailableAt);
    }
    const unavailable = courier.shift_start + minute >= unavailableAt;
    labels.push(`<span class="timeline-courier ${unavailable ? "off-shift" : ""}"><i style="--courier-color:${courierColors[state.scenario.couriers.indexOf(courier) % courierColors.length]}"></i>${escapeHtml(courier.name)}${unavailable ? " · vardiya dışı" : ""}</span>`);
  }
  $("#timeline-couriers").innerHTML = labels.join("");
}

async function refreshLog() {
  try {
    const log = await api("/log");
    const last = log.events.at(-1);
    const stateName = log.mimo_state || "dusunuyor";
    setMimoStatus(stateName);
    $("#mimo-caption").textContent = captions[stateName]?.[0] || "Mimo hazır";
    $("#mimo-log").textContent = last ? `${last.step} · ${new Date(last.timestamp).toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" })}` : captions[stateName]?.[1] || "Talimatını bekliyor";
  } catch (_) { /* API may still be starting. */ }
}

$("#new-map").addEventListener("click", event => {
  const stop = event.target.closest?.("[data-stop-id]");
  if (stop) showStopDetails(stop.dataset.stopId);
});
$("#old-map").addEventListener("click", event => {
  const stop = event.target.closest?.("[data-stop-id]");
  if (stop) showStopDetails(stop.dataset.stopId);
});
$("#time-slider").addEventListener("input", renderTimelineMarkers);
$("#play-time").addEventListener("click", () => {
  if (state.playTimer) {
    clearInterval(state.playTimer);
    state.playTimer = null;
    $("#play-time").textContent = "Oynat";
    return;
  }
  if (Number($("#time-slider").value) >= 480) $("#time-slider").value = "0";
  $("#play-time").textContent = "Duraklat";
  state.playTimer = setInterval(() => {
    const slider = $("#time-slider");
    slider.value = String(Math.min(480, Number(slider.value) + 1));
    renderTimelineMarkers();
    if (Number(slider.value) >= 480) {
      clearInterval(state.playTimer);
      state.playTimer = null;
      $("#play-time").textContent = "Oynat";
    }
  }, 100);
});

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
    const data = await api("/plan", { constraints });
    renderResult(data);
    refreshLog();
  } catch (error) { showError($("#plan-error"), error.message); refreshLog(); }
  finally { $("#approve").disabled = false; }
});

api("/scenario").then(async scenario => {
  state.scenario = scenario;
  $("#stop-count").textContent = `${scenario.stops.length} durak · ${scenario.couriers.length} kurye`;
  const baseline = await api("/plan", { constraints: { constraints: [] } });
  renderResult(baseline, { tour: false });
  state.plan = baseline.plan;
  state.previous = baseline.plan;
  $("#old-distance").textContent = `${baseline.summary.distance_km.toFixed(2)} km`;
  refreshLog();
}).catch(() => {});
refreshLog();
setInterval(refreshLog, 3500);
