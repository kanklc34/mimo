from __future__ import annotations

import pytest

from constraints import ConstraintSet
from generator import generate_scenario
from models import Plan, RouteVisit


@pytest.fixture
def scenario():
    return generate_scenario(seed=17)


@pytest.fixture
def constraints(scenario):
    return ConstraintSet.model_validate(
        {
            "constraints": [
                {"type": "tag_deadline", "tag": "soğuk_zincir", "within_minutes_from_start": 240}
            ]
        },
        context={"scenario": scenario},
    )


@pytest.fixture
def valid_plan(scenario):
    """Build a deterministic, feasible full-coverage plan for validator tests."""
    routes = {}
    stops = sorted(scenario.stops, key=lambda stop: ("soğuk_zincir" not in stop.tags, stop.id))
    assignments = {courier.id: [] for courier in scenario.couriers}
    for index, stop in enumerate(stops):
        assignments[scenario.couriers[index % len(scenario.couriers)].id].append(stop)

    for courier in scenario.couriers:
        current = courier.shift_start
        previous = scenario.depot
        visits = []
        for stop in assignments[courier.id]:
            arrival = max(current + scenario.travel_time_min(previous, stop), stop.window_start)
            visits.append(RouteVisit(stop_id=stop.id, arrival_min=arrival))
            current = arrival + stop.service_min
            previous = stop
        routes[courier.id] = visits
    return Plan(routes=routes, unserved_stops=[])
