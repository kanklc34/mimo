from __future__ import annotations

import logging
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, ValidationError

from api.gemini import GeminiTranslator
from api.planner import OrtoolsPlanner, Planner
from constraints import ConstraintSet
from constraints import CourierUnavailableAfter, MaxStops, TagDeadline
from generator import generate_scenario
from models import Plan, Scenario
from solver.diff import diff_plans
from solver import plan_distance_km
from validator import summarize, validate

app = FastAPI(title="Mimo Kurye")
translator = GeminiTranslator()
planner: Planner = OrtoolsPlanner()
_events: list[dict[str, str]] = []
_state_lock = Lock()
_previous_plan: Plan | None = None

_BASE_VALIDATION_CHECKS = [
    "known_references", "stop_coverage", "valid_arrival", "shift", "return_to_depot",
    "time_windows", "travel_order", "capacity",
]


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


@app.post("/reset")
def reset_planner() -> dict[str, Any]:
    """Restore the deterministic, unconstrained plan as the comparison baseline."""
    global _previous_plan
    scenario = generate_scenario(seed=42)
    constraints = ConstraintSet.model_validate({"constraints": []}, context={"scenario": scenario})
    plan, _ = planner.plan(scenario, constraints, previous_plan=None)
    distance = round(plan_distance_km(plan, scenario), 2)
    _previous_plan = plan
    with _state_lock:
        _events.clear()
        _events.append({
            "step": "sıfırlandı",
            "detail": "Başlangıç planına dönüldü",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    return {"plan": plan.model_dump(mode="json"), "distance_km": distance}


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
    except ValidationError:
        message = "Talimatı anlayamadım. Lütfen kurye, etiket veya süreyi kontrol edip yeniden yazın."
        _log("anlaşılamadı", "Talimat kısıt şemasına uymadı")
        return {
            "constraints": {"constraints": []},
            "understood_text": "",
            "ok": False,
            "error_code": "not_understood",
            "message": message,
        }
    except Exception:
        logging.exception("Gemini /interpret servis hatası")
        message = "Gemini servis hatası oluştu. Lütfen biraz sonra yeniden deneyin."
        _log("servis hatası", "Gemini /interpret başarısız")
        return {
            "constraints": {"constraints": []},
            "understood_text": "",
            "ok": False,
            "error_code": "service_error",
            "message": message,
        }


@app.post("/plan")
def create_plan(request: PlanRequest) -> dict[str, Any]:
    global _previous_plan
    scenario: Scenario = generate_scenario(seed=42)
    try:
        constraints = ConstraintSet.model_validate(request.constraints, context={"scenario": scenario})
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Kısıtlar geçersiz; kurye, etiket ve alanları kontrol edin.") from exc
    plan, unserved_reasons = planner.plan(scenario, constraints, previous_plan=_previous_plan)
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
        "changes": diff_plans(prior, plan) if prior else [],
        "meaningful_change_count": 0,
        "time_only_count": 0,
        "previous_distance_km": round(plan_distance_km(prior, scenario), 2) if prior else None,
        "distance_delta_km": round(current_distance - plan_distance_km(prior, scenario), 2) if prior else None,
    }
    for change in diff["changes"]:
        if change["type"] == "kurye_degisti":
            change["reason"] = _courier_change_reason(change, prior, plan, constraints, scenario)
    diff["meaningful_change_count"] = sum(change["type"] != "sadece_saat_kaydi" for change in diff["changes"])
    diff["time_only_count"] = sum(change["type"] == "sadece_saat_kaydi" for change in diff["changes"])
    _previous_plan = plan
    return {
        "plan": plan.model_dump(mode="json"),
        "violations": [violation.model_dump(mode="json") for violation in violations],
        "summary": {**report, "distance_km": round(current_distance, 2)},
        "constraints": constraints.model_dump(mode="json"),
        "validation_evidence": {
            "checks": _validation_checks(constraints),
            "violation_count": len(violations),
        },
        "diff": diff,
        "unserved": [
            {"stop_id": stop_id, "reason": unserved_reasons.get(stop_id, "Planlanmadı")}
            for stop_id in plan.unserved_stops
        ],
    }


def _clock_at_shift(minute: int, shift_start: int) -> str:
    total = 8 * 60 + shift_start + minute
    return f"{total // 60:02d}:{total % 60:02d}"


def _courier_change_reason(change: dict[str, Any], previous: Plan | None, current: Plan,
                          constraints: ConstraintSet, scenario: Scenario) -> str:
    if previous is None:
        return "Yeniden dağıtımda taşındı"

    stop = scenario.stop_by_id.get(change["stop_id"])
    old_courier_id = change["old_courier_id"]
    old_visit = next(
        (visit for visit in previous.routes.get(old_courier_id, []) if visit.stop_id == change["stop_id"]),
        None,
    )
    old_courier = scenario.courier_by_id.get(old_courier_id)
    if stop is None or old_visit is None or old_courier is None:
        return "Yeniden dağıtımda taşındı"

    old_arrival = old_visit.arrival_min
    old_clock = _clock_at_shift(old_arrival, old_courier.shift_start)
    for rule in constraints.constraints:
        if (isinstance(rule, CourierUnavailableAfter)
                and rule.courier_id == old_courier_id
                and old_arrival > rule.time_min):
            limit_clock = _clock_at_shift(rule.time_min, old_courier.shift_start)
            return (
                f"Eski planda {old_courier.name} buraya {old_clock}'te varacaktı; "
                f"kısıt {limit_clock}'den sonra çalışmayı yasaklıyor."
            )

    for rule in constraints.constraints:
        if isinstance(rule, TagDeadline) and rule.tag in stop.tags and old_arrival > rule.within_minutes_from_start:
            tag_name = "Soğuk zincir" if rule.tag in {"soğuk_zincir", "cold_chain"} else rule.tag.replace("_", " ").capitalize()
            deadline_clock = _clock_at_shift(rule.within_minutes_from_start, old_courier.shift_start)
            return f"{tag_name} durağı eski planda {old_clock}'da teslim ediliyordu; sınır {deadline_clock}."

    old_count = len(previous.routes.get(old_courier_id, []))
    new_count = len(current.routes.get(old_courier_id, []))
    for rule in constraints.constraints:
        if (isinstance(rule, MaxStops) and rule.courier_id == old_courier_id
                and old_count > rule.n and new_count < old_count):
            return f"{old_courier.name} {old_count} duraktan {new_count}'e düştü."

    return "Yeniden dağıtımda taşındı"


def _validation_checks(constraints: ConstraintSet) -> list[str]:
    checks = list(_BASE_VALIDATION_CHECKS)
    constraint_types = {
        CourierUnavailableAfter: "courier_unavailable_after",
        TagDeadline: "tag_deadline",
        MaxStops: "max_stops",
    }
    for rule_type, check_name in constraint_types.items():
        if any(isinstance(rule, rule_type) for rule in constraints.constraints):
            checks.append(check_name)
    return checks


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
        "sıfırlandı": "dusunuyor",
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
