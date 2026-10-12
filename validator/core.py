from __future__ import annotations

from collections import Counter

from constraints import ConstraintSet, CourierUnavailableAfter, MaxStops, TagDeadline
from models import Plan, Scenario, Violation


def _violation(kind: str, description: str, *, stop_id: str | None = None, courier_id: str | None = None) -> Violation:
    return Violation(type=kind, stop_id=stop_id, courier_id=courier_id, description=description)


def validate(
    plan: Plan,
    scenario: Scenario,
    constraints: ConstraintSet | list = None,
) -> list[Violation]:
    """Return deterministic rule violations; stops listed as unserved are reported separately by the plan."""
    if constraints is None:
        constraint_set = ConstraintSet()
    elif isinstance(constraints, ConstraintSet):
        constraint_set = constraints
    else:
        constraint_set = ConstraintSet(constraints=constraints)
    constraint_set.validate_references(scenario)

    violations: list[Violation] = []
    couriers = scenario.courier_by_id
    stops = scenario.stop_by_id
    assigned: Counter[str] = Counter()
    unserved_counts = Counter(plan.unserved_stops)

    for stop_id, count in unserved_counts.items():
        if stop_id not in stops:
            violations.append(_violation("unknown_stop", f"Unserved stop {stop_id!r} does not exist.", stop_id=stop_id))
        if count > 1:
            violations.append(_violation("duplicate_unserved_stop", f"Stop {stop_id!r} appears more than once in unserved_stops.", stop_id=stop_id))

    for courier_id, route in plan.routes.items():
        courier = couriers.get(courier_id)
        if courier is None:
            violations.append(_violation("unknown_courier", f"Courier {courier_id!r} does not exist.", courier_id=courier_id))
        route_demand = 0
        previous_stop = None
        previous_completion = courier.shift_start if courier else 0

        for visit in route:
            stop = stops.get(visit.stop_id)
            if stop is None:
                violations.append(_violation("unknown_stop", f"Stop {visit.stop_id!r} does not exist.", stop_id=visit.stop_id, courier_id=courier_id))
                continue
            assigned[stop.id] += 1
            route_demand += stop.demand

            if visit.arrival_min < 0:
                violations.append(_violation("invalid_time", "Arrival time must be a non-negative integer minute.", stop_id=stop.id, courier_id=courier_id))
            elif courier is not None:
                if visit.arrival_min < courier.shift_start or visit.arrival_min + stop.service_min > courier.shift_end:
                    violations.append(_violation("outside_shift", f"Stop {stop.id} is served outside {courier.name}'s shift.", stop_id=stop.id, courier_id=courier_id))
                if not stop.window_start <= visit.arrival_min <= stop.window_end:
                    violations.append(_violation("window_violation", f"Arrival at {stop.id} is outside its time window.", stop_id=stop.id, courier_id=courier_id))
                origin = previous_stop if previous_stop is not None else scenario.depot
                earliest = previous_completion + scenario.travel_time_min(origin, stop)
                if visit.arrival_min < earliest:
                    violations.append(_violation("travel_time_violation", f"Arrival at {stop.id} precedes the required travel and service time.", stop_id=stop.id, courier_id=courier_id))
                previous_completion = visit.arrival_min + stop.service_min
                previous_stop = stop

            for rule in constraint_set.constraints:
                if isinstance(rule, CourierUnavailableAfter) and courier_id == rule.courier_id:
                    if visit.arrival_min >= 0 and visit.arrival_min + stop.service_min > rule.time_min:
                        violations.append(_violation("courier_unavailable_after", f"Courier {courier_id} works past minute {rule.time_min}.", stop_id=stop.id, courier_id=courier_id))
                elif isinstance(rule, TagDeadline) and rule.tag in stop.tags and visit.arrival_min > rule.within_minutes_from_start:
                    violations.append(_violation("tag_deadline", f"Tagged stop {stop.id} misses the {rule.tag!r} deadline.", stop_id=stop.id, courier_id=courier_id))

        if courier is not None and previous_stop is not None:
            return_arrival = previous_completion + scenario.travel_time_min(previous_stop, scenario.depot)
            if return_arrival > courier.shift_end:
                violations.append(_violation(
                    "vardiya_asimi_donus",
                    f"Courier {courier_id} returns to the depot at minute {return_arrival}, after shift end {courier.shift_end}.",
                    stop_id=previous_stop.id,
                    courier_id=courier_id,
                ))

        if courier is not None and route_demand > courier.capacity:
            violations.append(_violation("capacity_exceeded", f"Route demand {route_demand} exceeds capacity {courier.capacity}.", courier_id=courier_id))
        for rule in constraint_set.constraints:
            if isinstance(rule, MaxStops) and courier_id == rule.courier_id and len(route) > rule.n:
                violations.append(_violation("max_stops", f"Courier {courier_id} has {len(route)} stops; maximum is {rule.n}.", courier_id=courier_id))

    for stop_id, count in assigned.items():
        if count > 1:
            violations.append(_violation("duplicate_stop", f"Stop {stop_id} is assigned {count} times.", stop_id=stop_id))
        if unserved_counts[stop_id]:
            violations.append(_violation("visited_and_unserved", f"Stop {stop_id} is both assigned and marked unserved.", stop_id=stop_id))

    for stop in scenario.stops:
        if assigned[stop.id] == 0 and unserved_counts[stop.id] == 0:
            violations.append(_violation("stop_coverage", f"Stop {stop.id} is neither assigned nor listed as unserved.", stop_id=stop.id))
    return violations
