from api import main
from api.main import InterpretRequest, PlanRequest, app
from models import Plan
from solver import naive_plan


def test_scenario_endpoint_returns_seeded_scenario():
    data = main.scenario_endpoint()

    assert len(data["stops"]) == 50
    assert len(data["couriers"]) == 4
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
    assert any(event["step"] in {"hesaplandı", "doğrulandı"} for event in main.get_log()["events"])


def test_invalid_plan_is_not_marked_valid(monkeypatch):
    monkeypatch.setattr(main.planner, "plan", lambda scenario, constraints, previous_plan=None: (Plan(), {}))

    data = main.create_plan(PlanRequest(constraints={"constraints": []}))

    assert data["summary"]["valid"] is False
    assert data["violations"]

