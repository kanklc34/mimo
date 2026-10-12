from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict

from api.gemini import GeminiTranslator
from api.planner import MockPlanner, Planner
from constraints import ConstraintSet
from generator import generate_scenario
from models import Plan, Scenario
from solver import plan_distance_km
from validator import summarize, validate

app = FastAPI(title="Mimo Kurye")
translator = GeminiTranslator()
planner: Planner = MockPlanner()
_events: list[dict[str, str]] = []
_state_lock = Lock()
_previous_plan: Plan | None = None


class InterpretRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str


class PlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    constraints: dict[str, Any] = {}


def _log(step: str, detail: str = "") -> None:
    event = {"step": step, "detail": detail, "timestamp": datetime.now(timezone.utc).isoformat()}
    with _state_lock:
        _events.append(event)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "Mimo Kurye"}


@app.get("/scenario")
def scenario_endpoint() -> dict[str, Any]:
    return generate_scenario(seed=42).model_dump(mode="json")


@app.post("/interpret")
def interpret(request: InterpretRequest) -> dict[str, Any]:
    scenario = generate_scenario(seed=42)
    try:
        raw = translator.interpret(request.text, scenario)
        constraint_set = ConstraintSet.model_validate(raw["constraints"], context={"scenario": scenario})
        result = {
            "constraints": constraint_set.model_dump(mode="json"),
            "understood_text": raw["understood_text"],
            "ok": True,
            "message": "Kısıtları anladım. Planlamadan önce onayınızı bekliyorum.",
        }
        _log("yorumlandı", request.text)
        _log("onay bekleniyor", result["understood_text"])
        return result
    except Exception:
        message = "Talimatı anlayamadım. Lütfen kurye, etiket veya süreyi kontrol edip yeniden yazın."
        _log("yorumlandı", "anlayamadım")
        return {"constraints": {"constraints": []}, "understood_text": "", "ok": False, "message": message}


@app.post("/plan")
def create_plan(request: PlanRequest) -> dict[str, Any]:
    global _previous_plan
    scenario: Scenario = generate_scenario(seed=42)
    try:
        constraints = ConstraintSet.model_validate(request.constraints, context={"scenario": scenario})
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Kısıtlar geçersiz; kurye, etiket ve alanları kontrol edin.") from exc
    plan, unserved_reasons = planner.plan(scenario, constraints)
    _log("hesaplandı", f"{sum(len(route) for route in plan.routes.values())} durak planlandı")
    _log("doğrulanıyor", "Plan bağımsız kurallarla kontrol ediliyor")
    violations = validate(plan, scenario, constraints)
    is_valid = not violations
    _log("doğrulandı", "geçti" if is_valid else f"{len(violations)} ihlal")
    report = summarize(violations, plan)
    report["valid"] = is_valid
    current_distance = plan_distance_km(plan, scenario)
    prior = _previous_plan
    previous_stop_routes = _stop_route_map(prior)
    current_stop_routes = _stop_route_map(plan)
    changed_stops = sorted(
        stop_id for stop_id in previous_stop_routes.keys() | current_stop_routes.keys()
        if previous_stop_routes.get(stop_id) != current_stop_routes.get(stop_id)
    ) if prior is not None else []
    diff = {
        "has_previous": prior is not None,
        "changed_stops": changed_stops,
        "previous_distance_km": round(plan_distance_km(prior, scenario), 2) if prior else None,
        "distance_delta_km": round(current_distance - plan_distance_km(prior, scenario), 2) if prior else None,
    }
    _previous_plan = plan
    return {
        "plan": plan.model_dump(mode="json"),
        "violations": [violation.model_dump(mode="json") for violation in violations],
        "summary": {**report, "distance_km": round(current_distance, 2)},
        "diff": diff,
        "unserved": [
            {"stop_id": stop_id, "reason": unserved_reasons.get(stop_id, "Planlanmadı")}
            for stop_id in plan.unserved_stops
        ],
    }


def _stop_route_map(plan: Plan | None) -> dict[str, tuple[str, int]]:
    if plan is None:
        return {}
    return {
        visit.stop_id: (courier_id, index)
        for courier_id, visits in plan.routes.items()
        for index, visit in enumerate(visits)
    }


@app.get("/log")
def get_log() -> dict[str, Any]:
    with _state_lock:
        events = list(_events)
    latest_step = events[-1]["step"] if events else "hazır"
    mimo_states = {
        "hazır": "dusunuyor",
        "yorumlandı": "dusunuyor",
        "onay bekleniyor": "dusunuyor",
        "hesaplandı": "hesapliyor",
        "doğrulanıyor": "kontrol",
        "doğrulandı": "basari",
    }
    state = mimo_states.get(latest_step, "uyari")
    if latest_step == "doğrulandı" and "ihlal" in events[-1]["detail"]:
        state = "uyari"
    return {"events": events, "mimo_state": state}


app.mount("/", StaticFiles(directory="web", html=True), name="web")
