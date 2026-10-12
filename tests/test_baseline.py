from solver import naive_plan, plan_distance_km
from validator import validate


def test_naive_baseline_covers_all_stops_and_has_distance(scenario):
    plan = naive_plan(scenario)
    assert sum(map(len, plan.routes.values())) == len(scenario.stops)
    assert plan.unserved_stops == []
    assert plan_distance_km(plan, scenario) > 0
    assert isinstance(validate(plan, scenario, []), list)
