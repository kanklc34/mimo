from models import Plan, RouteVisit
from solver.diff import diff_plans


def test_diff_reports_changed_courier_time_and_newly_unserved_stops():
    old = Plan(routes={
        "ali": [RouteVisit(stop_id="a", arrival_min=10), RouteVisit(stop_id="b", arrival_min=20)],
        "ayse": [],
    })
    new = Plan(routes={
        "ali": [RouteVisit(stop_id="b", arrival_min=25)],
        "ayse": [RouteVisit(stop_id="a", arrival_min=12)],
    }, unserved_stops=["c"])
    changes = diff_plans(old, new)
    assert {item["stop_id"] for item in changes} == {"a", "b", "c"}
    by_stop = {item["stop_id"]: item["changes"] for item in changes}
    assert "courier_changed" in by_stop["a"]
    assert "arrival_changed" in by_stop["a"]
    assert "arrival_changed" in by_stop["b"]
    assert "newly_unserved" in by_stop["c"]
