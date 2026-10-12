from api.main import app, health


def test_health_endpoint():
    assert health() == {"status": "ok", "service": "Mimo Kurye"}
    assert any(route.path == "/health" for route in app.routes)
