from api.main import app, health
from api.planner import OrtoolsPlanner


def test_health_endpoint():
    assert health() == {"status": "ok", "service": "Mimo Kurye"}
    assert any(route.path == "/health" for route in app.routes)


def test_default_planner_uses_ortools_adapter_and_preserves_planner_contract():
    from api import main

    assert isinstance(main.planner, OrtoolsPlanner)
    assert callable(main.planner.plan)
