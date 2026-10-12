from models import Plan, RouteVisit
from solver.diff import diff_plans


def test_diff_classifies_courier_order_time_and_newly_unserved_changes():
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
    typed = {item["stop_id"]: item["type"] for item in changes}
    assert typed == {"a": "kurye_degisti", "b": "sadece_saat_kaydi", "c": "yeni_atlandi"}


def test_diff_marks_only_arrival_change_as_time_record():
    old = Plan(routes={"ali": [RouteVisit(stop_id="a", arrival_min=10)]})
    new = Plan(routes={"ali": [RouteVisit(stop_id="a", arrival_min=15)]})

    assert diff_plans(old, new) == [{
        "stop_id": "a", "changes": ["arrival_changed"],
        "old_arrival_min": 10, "new_arrival_min": 15,
        "type": "sadece_saat_kaydi",
    }]


def test_diff_does_not_call_following_stops_reordered_after_an_insertion():
    old = Plan(routes={"ali": [RouteVisit(stop_id="a", arrival_min=1), RouteVisit(stop_id="b", arrival_min=2)]})
    new = Plan(routes={"ali": [RouteVisit(stop_id="new", arrival_min=0), RouteVisit(stop_id="a", arrival_min=1), RouteVisit(stop_id="b", arrival_min=2)]})

    assert {item["stop_id"]: item["type"] for item in diff_plans(old, new)} == {"new": "sira_degisti"}
