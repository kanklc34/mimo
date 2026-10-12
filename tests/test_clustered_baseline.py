from collections import Counter

from generator import generate_scenario
from solver.baselines import clustered_naive_plan
from validator import validate


def test_clustered_baseline_serves_each_stop_once_and_is_validator_clean():
    scenario = generate_scenario(seed=42)
    plan = clustered_naive_plan(scenario)
    assigned = [visit.stop_id for route in plan.routes.values() for visit in route]
    counts = Counter(assigned + plan.unserved_stops)
    assert set(counts) == scenario.stop_ids
    assert all(count == 1 for count in counts.values())
    assert validate(plan, scenario, []) == []


def test_clustered_baseline_uses_nearest_neighbor_inside_each_region():
    scenario = generate_scenario(seed=42)
    plan = clustered_naive_plan(scenario)
    for visits in plan.routes.values():
        route_stops = [scenario.stop_by_id[visit.stop_id] for visit in visits]
        for index, left in enumerate(route_stops[:-1]):
            remaining = route_stops[index + 1:]
            nearest = min(remaining, key=lambda stop: (scenario.distance_km(left, stop), stop.id))
            assert route_stops[index + 1].id == nearest.id
