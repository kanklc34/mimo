from __future__ import annotations

from math import atan2, floor, pi

from models import Plan, RouteVisit, Scenario


def clustered_naive_plan(scenario: Scenario) -> Plan:
    """Build a geographic-sector baseline with nearest-neighbor routes per courier."""
    couriers = scenario.couriers
    assignments = {courier.id: [] for courier in couriers}
    loads = {courier.id: 0 for courier in couriers}
    unserved: list[str] = []
    if not couriers:
        return Plan(routes={}, unserved_stops=[stop.id for stop in scenario.stops])

    for stop in scenario.stops:
        angle = atan2(stop.lon - scenario.depot.lon, stop.lat - scenario.depot.lat) % (2 * pi)
        preferred = min(len(couriers) - 1, floor(angle * len(couriers) / (2 * pi)))
        assigned = False
        for offset in range(len(couriers)):
            courier = couriers[(preferred + offset) % len(couriers)]
            if loads[courier.id] + stop.demand <= courier.capacity:
                assignments[courier.id].append(stop)
                loads[courier.id] += stop.demand
                assigned = True
                break
        if not assigned:
            unserved.append(stop.id)

    routes = {}
    for courier in couriers:
        remaining = list(assignments[courier.id])
        current_time = courier.shift_start
        previous = scenario.depot
        visits = []
        while remaining:
            feasible = []
            for stop in remaining:
                arrival = max(current_time + scenario.travel_time_min(previous, stop), stop.window_start)
                return_time = arrival + stop.service_min + scenario.travel_time_min(stop, scenario.depot)
                if arrival <= stop.window_end and return_time <= courier.shift_end:
                    feasible.append((scenario.distance_km(previous, stop), stop.id, stop, arrival))
            if not feasible:
                unserved.extend(stop.id for stop in remaining)
                break
            _distance, _stop_id, selected, arrival = min(feasible, key=lambda item: (item[0], item[1]))
            visits.append(RouteVisit(stop_id=selected.id, arrival_min=arrival))
            remaining.remove(selected)
            current_time = arrival + selected.service_min
            previous = selected
        routes[courier.id] = visits

    return Plan(routes=routes, unserved_stops=unserved)
