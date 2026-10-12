from __future__ import annotations

from models import Plan, RouteVisit, Scenario


def naive_plan(scenario: Scenario) -> Plan:
    """Assign stops in input order round-robin, then estimate arrival times without optimization."""
    assignments = {courier.id: [] for courier in scenario.couriers}
    for index, stop in enumerate(scenario.stops):
        if scenario.couriers:
            assignments[scenario.couriers[index % len(scenario.couriers)].id].append(stop)

    routes = {}
    for courier in scenario.couriers:
        current_time = courier.shift_start
        previous = scenario.depot
        visits = []
        for stop in assignments[courier.id]:
            arrival = max(current_time + scenario.travel_time_min(previous, stop), stop.window_start)
            visits.append(RouteVisit(stop_id=stop.id, arrival_min=arrival))
            current_time = arrival + stop.service_min
            previous = stop
        routes[courier.id] = visits
    return Plan(routes=routes, unserved_stops=[])


def plan_distance_km(plan: Plan, scenario: Scenario) -> float:
    total = 0.0
    for route in plan.routes.values():
        previous = scenario.depot
        last_stop = None
        for visit in route:
            stop = scenario.stop_by_id.get(visit.stop_id)
            if stop is None:
                continue
            total += scenario.distance_km(previous, stop)
            previous = stop
            last_stop = stop
        if last_stop is not None:
            total += scenario.distance_km(last_stop, scenario.depot)
    return total
