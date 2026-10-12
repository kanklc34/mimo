const $ = (selector) => document.querySelector(selector);
const SVG_NS = "http://www.w3.org/2000/svg";
const state = {
  scenario: null, plan: null, previous: null, constraints: { constraints: [] },
  changed: new Set(), timeOnly: new Set(), coordinates: new Map(), depotPoint: null,
  mimoPosition: null, mimoState: null, assetFailed: new Set(), tourId: 0, moveId: 0,
  playTimer: null, detailMap: "new", detailOpener: null,
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

function stopLabel(id) {
  const match = String(id || "").match(/^stop-(\d+)$/i);
  return match ? `Durak ${match[1]}` : String(id || "");
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
    x: bounds.maxLon === bounds.minLon ? 180 : ((item.lon - bounds.minLon) / (bounds.maxLon - bounds.minLon)) * 360,
    y: bounds.maxLat === bounds.minLat ? 115 : (1 - (item.lat - bounds.minLat) / (bounds.maxLat - bounds.minLat)) * 230,
  };
}

function mimoTarget(point) {
  const bounds = { left: 24, right: 336, top: 24, bottom: 206 };
  let dx = point.x > 310 ? -25 : 25;
  let dy = point.y < 40 ? 25 : -25;
  return {
    x: Math.max(bounds.left + 22, Math.min(bounds.right - 22, point.x + dx)),
    y: Math.max(bounds.top + 22, Math.min(bounds.bottom - 22, point.y + dy)),
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
  const projected = coords.map(point);
  const minX = Math.min(...projected.map(item => item.x)), maxX = Math.max(...projected.map(item => item.x));
  const minY = Math.min(...projected.map(item => item.y)), maxY = Math.max(...projected.map(item => item.y));
  const padX = Math.max(22, (maxX - minX) * 0.06), padY = Math.max(14, (maxY - minY) * 0.06);
  const viewMinX = Math.min(0, minX - padX), viewMinY = Math.min(0, minY - padY);
  const viewMaxX = Math.max(360, maxX + padX), viewMaxY = Math.max(230, maxY + padY);
  svg.setAttribute("viewBox", `${viewMinX} ${viewMinY} ${viewMaxX - viewMinX} ${viewMaxY - viewMinY}`);
  if (!old) {
    state.coordinates = new Map(stops.map(stop => [stop.id, point(stop)]));
    state.depotPoint = point(depot);
  }
  const byId = Object.fromEntries(stops.map(stop => [stop.id, stop]));
  const routes = plan?.routes || {};
  let markup = `<circle cx="${point(depot).x}" cy="${point(depot).y}" r="10" fill="#eef3ef"/>`;
  for (const [courierId, visits] of Object.entries(routes)) {
    const ordered = visits.map(visit => byId[visit.stop_id]).filter(Boolean);
    if (!ordered.length) continue;
    const pts = [point(depot), ...ordered.map(point), point(depot)];
    const courierIndex = Math.max(0, state.scenario.couriers.findIndex(courier => courier.id === courierId));
    markup += `<polyline class="route-line ${old ? "old-line" : ""}" stroke="${courierColors[courierIndex % courierColors.length]}" points="${pts.map(p => `${p.x},${p.y}`).join(" ")}"/>`;
  }
  const assigned = new Map();
  Object.entries(routes).forEach(([courierId, visits]) => visits.forEach(visit => assigned.set(visit.stop_id, courierId)));
  for (const stop of stops) {
    const p = point(stop), courierId = assigned.get(stop.id);
    const routeIndex = Math.max(0, state.scenario.couriers.findIndex(courier => courier.id === courierId));
    const fill = courierId === undefined ? "#cbd4ce" : courierColors[routeIndex % courierColors.length];
    const changed = state.changed.has(stop.id);
    const timeOnly = state.timeOnly.has(stop.id);
    markup += `<circle class="stop-dot ${changed ? "changed-stop" : timeOnly ? "time-only-stop" : ""}" data-stop-id="${escapeHtml(stop.id)}" tabindex="0" role="button" cx="${p.x}" cy="${p.y}" r="${changed ? 5 : timeOnly ? 4.1 : 2.6}" fill="${fill}"><title>${escapeHtml(stopLabel(stop.id))}${changed ? " · değişti" : timeOnly ? " · yalnızca saat kaydı" : ""}</title></circle>`;
  }
  const depotPoint = point(depot);
  markup += `<circle class="depot-dot" cx="${depotPoint.x}" cy="${depotPoint.y}" r="4.2"><title>Depo</title></circle>`;
  if (!old) {
    for (const [index, courier] of state.scenario.couriers.entries()) {
      markup += `<g class="courier-marker" id="courier-marker-${escapeHtml(courier.id)}" transform="translate(${depotPoint.x} ${depotPoint.y})"><circle r="5.2" fill="${courierColors[index % courierColors.length]}"/><title>${escapeHtml(courier.name)}</title></g>`;
    }
    const mimoStatus = state.mimoState || "dusunuyor";
    const mimoPoint = mimoTarget(depotPoint);
    markup += `<g id="mimo-marker" class="mimo-marker" transform="translate(${mimoPoint.x} ${mimoPoint.y})"><rect class="mimo-bubble" x="-126" y="-58" width="252" height="38" style="display:none"/><text id="mimo-bubble-text" x="0" y="-44" text-anchor="middle"></text><circle class="mimo-marker-body" r="22"/><image class="mimo-map-image${state.assetFailed.has(mimoStatus) ? " failed" : ""}" href="/assets/mimo-${mimoStatus}.png" x="-22" y="-22" width="44" height="44" preserveAspectRatio="xMidYMid meet"/><text class="mimo-marker-face" x="0" y="5" text-anchor="middle">🐒</text></g>`;
    state.mimoPosition = mimoPoint;
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
  const fullMessage = String(text || "").trim().replace(/\s+/g, " ");
  const lines = [];
  let line = "";
  for (const word of fullMessage.split(" ")) {
    const candidate = line ? `${line} ${word}` : word;
    if (candidate.length > 50 && line) { lines.push(line); line = word; }
    else line = candidate;
  }
  if (line) lines.push(line);
  const messageLines = lines.slice(0, 2);
  const bubble = $("#mimo-bubble-text");
  const marker = $("#mimo-marker");
  const pointMatch = marker?.getAttribute("transform")?.match(/translate\(([-\d.]+)\s+([-\d.]+)\)/);
  const markerX = pointMatch ? Number(pointMatch[1]) : 180;
  const markerY = pointMatch ? Number(pointMatch[2]) : 115;
  const rect = $("#mimo-marker .mimo-bubble");
  if (bubble) {
    bubble.replaceChildren(...messageLines.map((message, index) => {
      const tspan = svgNode("tspan", {
        x: markerX < 132 ? 4 : markerX > 228 ? 356 : markerX,
        dy: index ? 12 : 0,
        textLength: Math.min(232, Math.max(120, message.length * 4.6)),
        lengthAdjust: "spacingAndGlyphs",
      });
      tspan.textContent = message;
      return tspan;
    }));
    if (markerX < 132) { bubble.setAttribute("x", "4"); bubble.setAttribute("text-anchor", "start"); }
    else if (markerX > 228) { bubble.setAttribute("x", "356"); bubble.setAttribute("text-anchor", "end"); }
    else { bubble.setAttribute("x", String(markerX)); bubble.setAttribute("text-anchor", "middle"); }
    bubble.setAttribute("y", markerY < 70 ? String(markerY + 46) : String(markerY - 44));
  }
  if (rect) {
    const anchor = markerX < 132 ? 2 : markerX > 228 ? 106 : markerX - 126;
    rect.setAttribute("x", String(anchor));
    rect.setAttribute("y", markerY < 70 ? String(markerY + 32) : String(markerY - 58));
  }
  if (rect) rect.style.display = messageLines.length ? "" : "none";
}

function walkTo(target, duration = 650) {
  const marker = $("#mimo-marker");
  if (!marker || !target) return Promise.resolve();
  const moveId = ++state.moveId;
  const origin = state.mimoPosition || state.depotPoint || target;
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reducedMotion || duration <= 0) {
    const position = mimoTarget(target);
    marker.setAttribute("transform", `translate(${position.x} ${position.y})`);
    state.mimoPosition = position;
    setBubble($("#mimo-bubble-text")?.textContent || "");
    return Promise.resolve();
  }
  return new Promise(resolve => {
    const started = performance.now();
    const frame = now => {
      if (moveId !== state.moveId) { resolve(); return; }
      const progress = Math.min(1, (now - started) / duration);
      const eased = progress * progress * (3 - 2 * progress);
      const destination = mimoTarget(target);
      const current = { x: origin.x + (destination.x - origin.x) * eased, y: origin.y + (destination.y - origin.y) * eased };
      marker.setAttribute("transform", `translate(${current.x} ${current.y})`);
      state.mimoPosition = current;
      setBubble($("#mimo-bubble-text")?.textContent || "");
      if (progress < 1) requestAnimationFrame(frame);
      else { state.mimoPosition = destination; resolve(); }
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
  const stopName = stopLabel(stop?.id || change.stop_id);
  if (change.type === "kurye_degisti") return change.reason || `${stopName}: yeniden dağıtımda taşındı`;
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
      setBubble(`${stopLabel(stopById(lastViolation.stop_id)?.id || lastViolation.stop_id)}: ${lastViolation.description}`);
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
  renderOverviewMap("new");
  const strip = $("#result-strip");
  strip.classList.toggle("invalid", !data.summary.valid);
  $(".result-icon").textContent = data.summary.valid ? "✓" : "!";
  $("#result-text").textContent = data.summary.valid
    ? `Gerçekten değişen ${data.diff.meaningful_change_count} durak · saat kayması ${data.diff.time_only_count} · ${data.validation_evidence.violation_count} ihlal · ${data.unserved.length} atlanan durak`
    : `Doğrulama başarısız · ${data.validation_evidence.violation_count} ihlal`;
  renderValidationEvidence(data.validation_evidence);
  renderChangeDetails(data);
  if (tour) void runTour(data);
}

function renderValidationEvidence(evidence) {
  const labels = {
    known_references: "Kurye ve durak referansları",
    stop_coverage: "Her durak bir kez atanmış veya atlanmış",
    valid_arrival: "Varış zamanları geçerli",
    shift: "Vardiya sınırları",
    return_to_depot: "Vardiya içinde depoya dönüş",
    time_windows: "Zaman pencereleri",
    travel_order: "Seyahat süreleri ve rota sırası",
    capacity: "Kurye kapasitesi",
    courier_unavailable_after: "Kurye müsaitlik kısıtı",
    tag_deadline: "Etiket teslim sınırı",
    max_stops: "Maksimum durak kısıtı",
  };
  const target = $("#validation-evidence");
  const checks = evidence?.checks || [];
  target.innerHTML = checks.length
    ? `<strong>Doğrulama kanıtı · ${Number(evidence.violation_count) || 0} ihlal</strong><ul>${checks.map(check => `<li>${escapeHtml(labels[check] || check)}</li>`).join("")}</ul>`
    : "";
}

function renderChangeDetails(data) {
  const details = $("#validation-details");
  const rows = [];
  for (const violation of data.violations || []) rows.push(`<li>İhlal: ${escapeHtml(violation.description)}</li>`);
  for (const item of data.unserved || []) rows.push(`<li>Atlandı: ${escapeHtml(stopLabel(item.stop_id))} — ${escapeHtml(item.reason)}</li>`);
  const changes = data.diff?.changes || [];
  const meaningful = changes.filter(change => change.type !== "sadece_saat_kaydi");
  const courierChange = change => {
    const oldIndex = Math.max(0, state.scenario.couriers.findIndex(courier => courier.id === change.old_courier_id));
    const newIndex = Math.max(0, state.scenario.couriers.findIndex(courier => courier.id === change.new_courier_id));
    const reason = change.reason || "Yeniden dağıtımda taşındı";
    return `${escapeHtml(stopLabel(change.stop_id))} · <span class="change-courier"><i style="--courier-color:${courierColors[oldIndex % courierColors.length]}"></i>${escapeHtml(courierName(change.old_courier_id))}</span> → <span class="change-courier"><i style="--courier-color:${courierColors[newIndex % courierColors.length]}"></i>${escapeHtml(courierName(change.new_courier_id))}</span><small class="change-reason">${escapeHtml(reason)}</small>`;
  };
  for (const change of meaningful) {
    const label = change.type === "kurye_degisti" ? courierChange(change)
      : change.type === "sira_degisti" ? `${escapeHtml(stopLabel(change.stop_id))} · sırası değişti`
        : `${escapeHtml(stopLabel(change.stop_id))} · atlandı`;
    rows.push(`<li>${label}</li>`);
  }
  const timeOnly = changes.filter(change => change.type === "sadece_saat_kaydi");
  const timeRows = timeOnly.map(change => `<li>${escapeHtml(stopLabel(change.stop_id))} · ${escapeHtml(formatClock(change.old_arrival_min))} → ${escapeHtml(formatClock(change.new_arrival_min))}</li>`).join("");
  details.innerHTML = rows.length ? `<ul>${rows.join("")}</ul>` : "";
  details.parentElement.hidden = !rows.length;
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
  if (rule.type === "courier_unavailable_after") return `${courierName(rule.courier_id)}: ${formatClock(rule.time_min)}'den sonra çalışmaz`;
  if (rule.type === "max_stops") return `${courierName(rule.courier_id)}: en fazla ${rule.n} durak`;
  if (rule.type === "tag_deadline") {
    const rawTag = String(rule.tag || "");
    const tag = ["soğuk_zincir", "cold_chain"].includes(rawTag.toLocaleLowerCase("tr-TR"))
      ? "Soğuk zincir"
      : rawTag.replace(/[_-]+/g, " ");
    return `${tag.charAt(0).toLocaleUpperCase("tr-TR")}${tag.slice(1)}: ilk ${rule.within_minutes_from_start} dk içinde teslim`;
  }
  return "";
}

function renderConstraintSummaries(value) {
  const rules = Array.isArray(value?.constraints) ? value.constraints : [];
  const lines = rules.map(constraintSummary).filter(Boolean);
  const understood = $("#understood");
  understood.innerHTML = lines.length ? `<ul>${lines.map(line => `<li>${escapeHtml(line)}</li>`).join("")}</ul>` : "Anlaşılan kısıtlar burada görüntülenir.";
  understood.classList.toggle("has-text", lines.length > 0);
}

function showStopDetails(stopId) {
  state.tourId += 1;
  const stop = stopById(stopId);
  if (!stop) return;
  const assigned = visitForStop(stopId);
  const courierId = assigned?.courierId;
  const courier = courierById(courierId);
  const constraints = matchingConstraints(stop, courierId).map(constraintSummary);
  const details = [stopLabel(stop.id), courier?.name || "Atanmadı", assigned ? formatClock(assigned.visit.arrival_min) : "", ...constraints].filter(Boolean);
  setBubble(details.join(" · "));
  void walkTo(state.coordinates.get(stopId));
}

function renderRouteDetail(which = state.detailMap) {
  state.detailMap = which;
  const source = which === "old" ? $("#old-map") : $("#new-map");
  const target = $("#detail-map");
  if (!source || !target || !state.scenario) return;
  target.setAttribute("viewBox", source.getAttribute("viewBox") || "0 0 360 230");
  target.innerHTML = source.innerHTML;
  $("#detail-stop-info").textContent = "Durak ayrıntısı için haritada bir nokta seçin.";
  const isOld = which === "old";
  const plan = isOld ? state.previous : state.plan;
  const distance = isOld ? $("#old-distance").textContent : $("#new-distance").textContent;
  $("#detail-title").textContent = isOld ? "Önceki plan" : "Yeni plan";
  $("#detail-subtitle").textContent = isOld
    ? "Devir öncesindeki rota dağılımı."
    : "Güncellenen rota dağılımı. Duraklara tıklayarak ayrıntıyı görün.";
  document.querySelectorAll("[data-detail-map]").forEach(button => {
    const active = button.dataset.detailMap === which;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", String(active));
  });
  const changedCount = state.changed.size;
  const violationText = $("#result-text").textContent.match(/(\d+) ihlal/)?.[1] || "—";
  $("#detail-stats").innerHTML = [
    ["Toplam mesafe", distance],
    ["Kurye", String(state.scenario.couriers.length)],
    ["Durak", String(state.scenario.stops.length)],
    ["Değişen durak", isOld ? "—" : String(changedCount)],
    ["Doğrulama ihlali", isOld ? "—" : violationText],
  ].map(([label, value]) => `<div class="detail-stat"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`).join("");
  const routes = plan?.routes || {};
  $("#detail-routes").innerHTML = state.scenario.couriers.map((courier, index) => {
    const visits = routes[courier.id] || [];
    const stops = visits.map(visit => stopLabel(visit.stop_id)).join(" · ");
    return `<section class="detail-route"><div class="detail-route-head"><i style="--courier-color:${courierColors[index % courierColors.length]}"></i><strong>${escapeHtml(courier.name)}</strong><span>${visits.length} durak</span></div><p>${escapeHtml(stops || "Atanmış durak yok")}</p></section>`;
  }).join("");
}

function openRouteDetail(which, opener) {
  const dialog = $("#route-detail-dialog");
  state.detailOpener = opener;
  renderRouteDetail(which);
  if (!dialog.open) dialog.showModal();
}

function renderOverviewMap(which = "new") {
  const old = which === "old";
  state.overviewMap = old ? "old" : "new";
  $("#old-map-card").hidden = !old;
  $("#new-map-card").hidden = old;
  document.querySelectorAll("[data-overview-map]").forEach(button => {
    const active = button.dataset.overviewMap === state.overviewMap;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", String(active));
  });
  $(".map-open-main").dataset.routeMap = state.overviewMap;
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
document.querySelectorAll("[data-route-map]").forEach(button => button.addEventListener("click", () => {
  openRouteDetail(button.dataset.routeMap, button);
}));
document.querySelectorAll("[data-overview-map]").forEach(button => button.addEventListener("click", () => {
  renderOverviewMap(button.dataset.overviewMap);
}));
[["#old-map", "old"], ["#new-map", "new"]].forEach(([selector, which]) => $(selector).addEventListener("click", event => {
  if (event.target.closest?.("[data-stop-id]")) return;
  openRouteDetail(which, $(`[data-route-map="${which}"]`));
}));
document.querySelectorAll("[data-detail-map]").forEach(button => button.addEventListener("click", () => renderRouteDetail(button.dataset.detailMap)));
$("#close-route-detail").addEventListener("click", () => $("#route-detail-dialog").close());
$("#route-detail-dialog").addEventListener("click", event => {
  if (event.target === $("#route-detail-dialog")) $("#route-detail-dialog").close();
  const stop = event.target.closest?.("[data-stop-id]");
  if (stop) {
    const stopData = stopById(stop.dataset.stopId);
    const assigned = visitForStop(stop.dataset.stopId);
    const courier = assigned ? courierById(assigned.courierId) : null;
    const rules = stopData && matchingConstraints(stopData, assigned?.courierId).map(constraintSummary);
    const details = [
      stopLabel(stop.dataset.stopId),
      courier?.name || "Atanmadı",
      assigned ? `Varış ${formatClock(assigned.visit.arrival_min)}` : "Planlanmadı",
      ...(rules || []),
    ];
    $("#detail-stop-info").textContent = details.join(" · ");
    stop.classList.add("detail-selected-stop");
  }
});
$("#route-detail-dialog").addEventListener("close", () => state.detailOpener?.focus());
$("#time-slider").addEventListener("input", renderTimelineMarkers);
$("#reset-plan").addEventListener("click", async () => {
  const button = $("#reset-plan");
  button.disabled = true;
  try {
    const baseline = await api("/reset", {});
    state.tourId += 1;
    if (state.playTimer) clearInterval(state.playTimer);
    state.playTimer = null;
    $("#play-time").textContent = "Oynat";
    state.plan = baseline.plan;
    state.previous = baseline.plan;
    state.constraints = { constraints: [] };
    state.changed.clear();
    state.timeOnly.clear();
    $("#old-distance").textContent = `${baseline.distance_km.toFixed(2)} km`;
    $("#new-distance").textContent = `${baseline.distance_km.toFixed(2)} km`;
    drawMap($("#old-map"), baseline.plan, true);
    drawMap($("#new-map"), baseline.plan, false);
    renderOverviewMap("new");
    $("#result-strip").classList.remove("invalid");
    $("#result-text").textContent = "Başa dönüldü · gerçekten değişen 0 durak · saat kayması 0 · 0 ihlal · 0 atlanan durak";
    $("#validation-details").innerHTML = "";
    $("#validation-details").parentElement.hidden = true;
    $("#validation-evidence").innerHTML = "";
    $("#instruction").value = "";
    $("#constraints").value = JSON.stringify(state.constraints, null, 2);
    renderConstraintSummaries(state.constraints);
    $("#interpret-status").textContent = "BEKLİYOR";
    $("#interpret-status").className = "status-chip idle";
    $("#approve").disabled = true;
    showError($("#interpret-error"), "");
    showError($("#plan-error"), "");
    $("#time-slider").value = "0";
    renderTimelineMarkers();
    setMimoStatus("dusunuyor");
    $("#mimo-caption").textContent = captions.dusunuyor[0];
    setBubble("");
    await walkTo(state.depotPoint, 0);
    refreshLog();
  } catch (error) {
    showError($("#plan-error"), error.message);
  } finally {
    button.disabled = false;
  }
});
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
    renderConstraintSummaries(result.constraints);
    if (!result.ok) $("#understood").textContent = result.understood_text || result.message;
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
    renderConstraintSummaries(constraints);
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
