from api import main
from api.main import InterpretRequest, PlanRequest, app
from generator import generate_scenario
from models import Plan, RouteVisit
from solver import naive_plan


def test_scenario_endpoint_returns_seeded_scenario():
    data = main.scenario_endpoint()

    assert len(data["stops"]) == 50
    assert len(data["couriers"]) == 4
    assert {"lat", "lon", "service_min"} <= data["stops"][0].keys()
    assert {"shift_start", "shift_end"} <= data["couriers"][0].keys()
    assert any(route.path == "/scenario" for route in app.routes)


def test_interpret_returns_constraints_and_records_approval_step(monkeypatch):
    monkeypatch.setattr(
        main.translator,
        "interpret",
        lambda text, scenario: {
            "constraints": {"constraints": [{"type": "max_stops", "courier_id": "courier-1", "n": 7}]},
            "understood_text": "Kurye 1 en fazla 7 durak alacak.",
        },
    )

    data = main.interpret(InterpretRequest(text="Kurye 1 en fazla 7 durak alsın"))

    assert data["ok"] is True
    assert data["constraints"]["constraints"][0]["n"] == 7
    assert "Kurye 1" in data["understood_text"]
    assert any(event["step"] == "onay bekleniyor" for event in main.get_log()["events"])


def test_interpret_rejects_unknown_references(monkeypatch):
    monkeypatch.setattr(
        main.translator,
        "interpret",
        lambda text, scenario: {
            "constraints": {"constraints": [{"type": "max_stops", "courier_id": "hayali", "n": 2}]},
            "understood_text": "Hayali kurye en fazla 2 durak alacak.",
        },
    )

    data = main.interpret(InterpretRequest(text="Hayali kurye en fazla 2 durak alsın"))

    assert data["ok"] is False
    assert "anlayamadım" in data["message"].lower()


def test_interpret_reports_and_logs_service_errors_separately(monkeypatch, caplog):
    def fail_with_closed_client(text, scenario):
        raise RuntimeError("Cannot send a request, as the client has been closed.")

    monkeypatch.setattr(main.translator, "interpret", fail_with_closed_client)

    data = main.interpret(InterpretRequest(text="Kurye 1 için talimat"))

    assert data["ok"] is False
    assert data["error_code"] == "service_error"
    assert "servis hatası" in data["message"].lower()
    assert "anlayamadım" not in data["message"].lower()
    assert any(
        record.exc_info and "client has been closed" in str(record.exc_info[1])
        for record in caplog.records
    )
    assert any(event["step"] == "servis hatası" for event in main.get_log()["events"])


def test_plan_includes_validation_summary_diff_and_unserved(monkeypatch):
    monkeypatch.setattr(main.planner, "plan", lambda scenario, constraints, previous_plan=None: (naive_plan(scenario), {}))
    request = PlanRequest(constraints={"constraints": []})

    first = main.create_plan(request)
    second = main.create_plan(request)

    assert "violations" in first
    assert "summary" in first
    assert first["summary"]["valid"] is (len(first["violations"]) == 0)
    assert "changed_stops" in second["diff"]
    assert "meaningful_change_count" in second["diff"]
    assert "time_only_count" in second["diff"]
    assert all("type" in item for item in second["diff"]["changes"])
    assert "unserved" in second
    assert "constraints" in second
    assert second["constraints"] == {"constraints": []}
    assert second["validation_evidence"]["violation_count"] == len(second["violations"])
    assert {"stop_coverage", "capacity", "shift", "time_windows", "travel_order"} <= set(
        second["validation_evidence"]["checks"]
    )
    assert all("type" in change for change in second["diff"]["changes"])
    assert any(event["step"] in {"hesaplandı", "doğrulandı"} for event in main.get_log()["events"])


def test_plan_returns_normalized_constraints_for_stop_details(monkeypatch):
    monkeypatch.setattr(main.planner, "plan", lambda scenario, constraints, previous_plan=None: (naive_plan(scenario), {}))
    data = main.create_plan(PlanRequest(constraints={"constraints": [
        {"type": "max_stops", "courier_id": "courier-1", "n": 7},
    ]}))

    assert data["constraints"] == {"constraints": [
        {"type": "max_stops", "courier_id": "courier-1", "n": 7},
    ]}


def test_validation_evidence_lists_active_constraint_types_and_actual_violations(monkeypatch):
    monkeypatch.setattr(main.planner, "plan", lambda scenario, constraints, previous_plan=None: (naive_plan(scenario), {}))
    data = main.create_plan(PlanRequest(constraints={"constraints": [
        {"type": "courier_unavailable_after", "courier_id": "courier-1", "time_min": 0},
        {"type": "tag_deadline", "tag": "soğuk_zincir", "within_minutes_from_start": 0},
        {"type": "max_stops", "courier_id": "courier-1", "n": 1},
    ]}))

    assert {"courier_unavailable_after", "tag_deadline", "max_stops"} <= set(data["validation_evidence"]["checks"])
    assert data["validation_evidence"]["violation_count"] == len(data["violations"]) > 0


def test_invalid_plan_is_not_marked_valid(monkeypatch):
    monkeypatch.setattr(main.planner, "plan", lambda scenario, constraints, previous_plan=None: (Plan(), {}))

    data = main.create_plan(PlanRequest(constraints={"constraints": []}))

    assert data["summary"]["valid"] is False
    assert data["violations"]

def test_reset_replays_same_constraint_changes_from_baseline(monkeypatch):
    monkeypatch.setattr(main, "_previous_plan", None)
    with main._state_lock:
        main._events.clear()

    baseline = main.reset_planner()
    assert main.get_log()["events"][-1]["step"] == "sıfırlandı"
    assert main.get_log()["mimo_state"] == "dusunuyor"
    constraint = {"constraints": [{"type": "max_stops", "courier_id": "courier-1", "n": 7}]}
    first = main.create_plan(PlanRequest(constraints=constraint))
    main.reset_planner()
    second = main.create_plan(PlanRequest(constraints=constraint))

    assert first["diff"]["meaningful_change_count"] > 0
    assert second["diff"]["meaningful_change_count"] == first["diff"]["meaningful_change_count"]
    assert baseline["distance_km"] == 63.89
    assert second["diff"]["previous_distance_km"] == 63.89


def _move_real_scenario_stop(monkeypatch, constraint_factory):
    scenario = generate_scenario(seed=42)
    previous = naive_plan(scenario)
    old_courier_id = next(cid for cid, visits in previous.routes.items() if visits)
    old_visit = previous.routes[old_courier_id][0]
    target_stop = scenario.stop_by_id[old_visit.stop_id]
    new_courier_id = next(cid for cid in previous.routes if cid != old_courier_id)
    current = previous.model_copy(deep=True)
    current.routes[old_courier_id] = current.routes[old_courier_id][1:]
    current.routes[new_courier_id].append(old_visit)
    constraint = constraint_factory(scenario, previous, old_courier_id, old_visit, target_stop)
    monkeypatch.setattr(main, "_previous_plan", previous)
    monkeypatch.setattr(main.planner, "plan", lambda scenario, constraints, previous_plan=None: (current, {}))
    data = main.create_plan(PlanRequest(constraints={"constraints": [constraint]}))
    change = next(item for item in data["diff"]["changes"] if item["stop_id"] == old_visit.stop_id)
    return scenario, previous, old_courier_id, old_visit, target_stop, change


def _clock(minute, shift_start=0):
    total = 8 * 60 + shift_start + minute
    return f"{total // 60:02d}:{total % 60:02d}"


def test_courier_change_reason_uses_unavailability_constraint(monkeypatch):
    scenario, _, courier_id, visit, _, change = _move_real_scenario_stop(
        monkeypatch,
        lambda scenario, previous, courier_id, visit, stop: {
            "type": "courier_unavailable_after", "courier_id": courier_id, "time_min": visit.arrival_min - 1,
        },
    )

    assert change["reason"] == (
        f"Eski planda {scenario.courier_by_id[courier_id].name} buraya "
        f"{_clock(visit.arrival_min)}'te varacaktı; kısıt {_clock(visit.arrival_min - 1)}'den "
        "sonra çalışmayı yasaklıyor."
    )


def test_courier_change_reason_uses_tag_deadline_constraint(monkeypatch):
    scenario = generate_scenario(seed=42)
    tagged_stop = next(stop for stop in scenario.stops if stop.tags)
    previous = naive_plan(scenario)
    old_courier_id = next(cid for cid, visits in previous.routes.items() if any(v.stop_id == tagged_stop.id for v in visits))
    visit = next(v for v in previous.routes[old_courier_id] if v.stop_id == tagged_stop.id)
    deadline = visit.arrival_min - 1
    target_tag = tagged_stop.tags[0]
    new_courier_id = next(cid for cid in previous.routes if cid != old_courier_id)
    current = previous.model_copy(deep=True)
    current.routes[old_courier_id] = [v for v in current.routes[old_courier_id] if v.stop_id != tagged_stop.id]
    current.routes[new_courier_id].append(visit)
    monkeypatch.setattr(main, "_previous_plan", previous)
    monkeypatch.setattr(main.planner, "plan", lambda scenario, constraints, previous_plan=None: (current, {}))

    data = main.create_plan(PlanRequest(constraints={"constraints": [{
        "type": "tag_deadline", "tag": target_tag, "within_minutes_from_start": deadline,
    }]}))
    change = next(item for item in data["diff"]["changes"] if item["stop_id"] == tagged_stop.id)
    tag_name = "Soğuk zincir" if target_tag in {"soğuk_zincir", "cold_chain"} else target_tag.replace("_", " ").capitalize()

    assert change["reason"] == (
        f"{tag_name} durağı eski planda {_clock(visit.arrival_min)}'da teslim ediliyordu; "
        f"sınır {_clock(deadline)}."
    )


def test_courier_change_reason_uses_max_stops_constraint(monkeypatch):
    scenario, previous, courier_id, _, _, change = _move_real_scenario_stop(
        monkeypatch,
        lambda scenario, previous, courier_id, visit, stop: {
            "type": "max_stops", "courier_id": courier_id, "n": len(previous.routes[courier_id]) - 1,
        },
    )
    old_count = len(previous.routes[courier_id])

    assert change["reason"] == (
        f"{scenario.courier_by_id[courier_id].name} {old_count} duraktan {old_count - 1}'e düştü."
    )
