from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from constraints import ConstraintSet, CourierUnavailableAfter, MaxStops, TagDeadline
from models import Plan, RouteVisit, Scenario


@dataclass
class SolveResult:
    plan: Plan
    unserved_reasons: dict[str, str]
    solve_time_s: float
    status: str


def _constraint_set(scenario: Scenario, constraints) -> ConstraintSet:
    if constraints is None:
        result = ConstraintSet()
    elif isinstance(constraints, ConstraintSet):
        result = constraints
    else:
        result = ConstraintSet(constraints=constraints)
    result.validate_references(scenario)
    return result


def _reason(stop_id: str, scenario: Scenario, rules: ConstraintSet) -> str:
    stop = scenario.stop_by_id[stop_id]
    if all(stop.demand > courier.capacity for courier in scenario.couriers):
        return "Paket talebi tüm kuryelerin kapasitesinden büyük."
    for rule in rules.constraints:
        if isinstance(rule, TagDeadline) and rule.tag in stop.tags:
            if stop.window_start > rule.within_minutes_from_start:
                return "Durak zaman penceresi etiket teslim son tarihinden sonra başlıyor."
    if not scenario.couriers:
        return "Senaryoda kurye bulunmuyor."
    return "Zaman penceresi, kapasite, vardiya veya tanımlı kısıtlar nedeniyle atanamadı."


def _solve_ortools(scenario: Scenario, rules: ConstraintSet, time_limit_s: float) -> tuple[Plan, str]:
    from ortools.constraint_solver import pywrapcp, routing_enums_pb2

    stops = scenario.stops
    couriers = scenario.couriers
    manager = pywrapcp.RoutingIndexManager(len(stops) + 1, len(couriers), 0)
    routing = pywrapcp.RoutingModel(manager)
    nodes = [scenario.depot, *stops]
    stop_at_node = {index + 1: stop for index, stop in enumerate(stops)}

    def arc_time(from_index: int, to_index: int) -> int:
        origin_node = manager.IndexToNode(from_index)
        destination_node = manager.IndexToNode(to_index)
        origin = nodes[origin_node]
        destination = nodes[destination_node]
        travel = scenario.travel_time_min(origin, destination) if destination_node else scenario.travel_time_min(origin, scenario.depot)
        return travel + (stop_at_node[origin_node].service_min if origin_node else 0)

    time_callback = routing.RegisterTransitCallback(arc_time)
    routing.SetArcCostEvaluatorOfAllVehicles(time_callback)
    horizon = max((courier.shift_end for courier in couriers), default=0)
    routing.AddDimension(time_callback, max(horizon, 1), max(horizon, 1), False, "Time")
    time_dimension = routing.GetDimensionOrDie("Time")
    for vehicle, courier in enumerate(couriers):
        time_dimension.CumulVar(routing.Start(vehicle)).SetRange(courier.shift_start, courier.shift_start)
        time_dimension.CumulVar(routing.End(vehicle)).SetRange(courier.shift_start, courier.shift_end)
    for index, stop in enumerate(stops, 1):
        idx = manager.NodeToIndex(index)
        time_dimension.CumulVar(idx).SetRange(stop.window_start, min(stop.window_end, horizon))
        routing.AddDisjunction([idx], 1_000_000)

    def demand_callback(index: int) -> int:
        node = manager.IndexToNode(index)
        return stop_at_node[node].demand if node in stop_at_node else 0

    demand_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_index, 0, [courier.capacity for courier in couriers], True, "Capacity"
    )

    def stop_count_callback(index: int) -> int:
        return 1 if manager.IndexToNode(index) in stop_at_node else 0

    count_index = routing.RegisterUnaryTransitCallback(stop_count_callback)
    max_counts = [len(stops)] * len(couriers)
    for rule in rules.constraints:
        if isinstance(rule, MaxStops):
            vehicle = next(i for i, courier in enumerate(couriers) if courier.id == rule.courier_id)
            max_counts[vehicle] = min(max_counts[vehicle], rule.n)
    routing.AddDimensionWithVehicleCapacity(count_index, 0, max_counts, True, "StopCount")

    for rule in rules.constraints:
        if isinstance(rule, CourierUnavailableAfter):
            vehicle = next(i for i, courier in enumerate(couriers) if courier.id == rule.courier_id)
            solver = routing.solver()
            for index, stop in enumerate(stops, 1):
                idx = manager.NodeToIndex(index)
                # Reify the service-completion bound by vehicle. Dropped stops and
                # visits assigned to a different vehicle keep their own time bound.
                assigned_to_vehicle = solver.IsEqualCstVar(routing.VehicleVar(idx), vehicle)
                big_m = max(horizon, rule.time_min, courier.shift_end) + stop.service_min + 1
                solver.Add(
                    time_dimension.CumulVar(idx) + stop.service_min
                    <= rule.time_min + big_m * (1 - assigned_to_vehicle)
                )
        elif isinstance(rule, TagDeadline):
            for index, stop in enumerate(stops, 1):
                if rule.tag in stop.tags:
                    time_dimension.CumulVar(manager.NodeToIndex(index)).SetMax(rule.within_minutes_from_start)

    parameters = pywrapcp.DefaultRoutingSearchParameters()
    parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    parameters.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GREEDY_DESCENT
    parameters.time_limit.FromMilliseconds(max(1, int(max(0.001, time_limit_s) * 1000)))
    parameters.log_search = False
    solution = routing.SolveWithParameters(parameters)
    if solution is None:
        raise RuntimeError("OR-Tools did not produce a feasible solution")

    routes: dict[str, list[RouteVisit]] = {courier.id: [] for courier in couriers}
    visited: set[str] = set()
    for vehicle, courier in enumerate(couriers):
        index = routing.Start(vehicle)
        while not routing.IsEnd(index):
            next_index = solution.Value(routing.NextVar(index))
            if not routing.IsEnd(next_index):
                node = manager.IndexToNode(next_index)
                stop = stop_at_node[node]
                routes[courier.id].append(
                    RouteVisit(stop_id=stop.id, arrival_min=solution.Value(time_dimension.CumulVar(next_index)))
                )
                visited.add(stop.id)
            index = next_index
    unserved = [stop.id for stop in stops if stop.id not in visited]
    return Plan(routes=routes, unserved_stops=unserved), "ortools"


def _fallback(scenario: Scenario, rules: ConstraintSet) -> tuple[Plan, str]:
    """Nearest-neighbor assignment followed by feasible 2-opt route improvement."""
    stops = list(scenario.stops)
    routes: dict[str, list[RouteVisit]] = {courier.id: [] for courier in scenario.couriers}
    served: set[str] = set()
    for courier in scenario.couriers:
        remaining = [s for s in stops if s.id not in served]
        previous = scenario.depot
        current = courier.shift_start
        demand = 0
        max_stops = min((r.n for r in rules.constraints if isinstance(r, MaxStops) and r.courier_id == courier.id), default=len(stops))
        unavailable = min((r.time_min for r in rules.constraints if isinstance(r, CourierUnavailableAfter) and r.courier_id == courier.id), default=courier.shift_end)
        route: list[RouteVisit] = []
        while remaining and len(route) < max_stops:
            candidates = sorted(remaining, key=lambda s: (scenario.distance_km(previous, s), s.id))
            selected = None
            for stop in candidates:
                arrival = max(current + scenario.travel_time_min(previous, stop), stop.window_start)
                if demand + stop.demand > courier.capacity or arrival > stop.window_end:
                    continue
                if arrival + stop.service_min > min(courier.shift_end, unavailable):
                    continue
                if any(isinstance(r, TagDeadline) and r.tag in stop.tags and arrival > r.within_minutes_from_start for r in rules.constraints):
                    continue
                if arrival + stop.service_min + scenario.travel_time_min(stop, scenario.depot) > courier.shift_end:
                    continue
                selected = (stop, arrival)
                break
            if selected is None:
                break
            stop, arrival = selected
            route.append(RouteVisit(stop_id=stop.id, arrival_min=arrival))
            served.add(stop.id)
            remaining.remove(stop)
            demand += stop.demand
            current = arrival + stop.service_min
            previous = stop
        # 2-opt only accepts an ordering that remains feasible after exact rescheduling.
        changed = True
        while changed and len(route) >= 3:
            changed = False
            for left in range(len(route) - 1):
                for right in range(left + 2, len(route) + 1):
                    candidate = list(reversed(route[left:right]))
                    proposed = route[:left] + candidate + route[right:]
                    times = _schedule_route(proposed, courier, scenario, rules)
                    if times is not None:
                        route = times
                        changed = True
                        break
                if changed:
                    break
        routes[courier.id] = route
    unserved = [s.id for s in stops if s.id not in served]
    return Plan(routes=routes, unserved_stops=unserved), "fallback-nearest-neighbor-2opt"


def _schedule_route(route: list[RouteVisit], courier, scenario: Scenario, rules: ConstraintSet):
    current, previous, demand, result = courier.shift_start, scenario.depot, 0, []
    unavailable = min((r.time_min for r in rules.constraints if isinstance(r, CourierUnavailableAfter) and r.courier_id == courier.id), default=courier.shift_end)
    for visit in route:
        stop = scenario.stop_by_id[visit.stop_id]
        arrival = max(current + scenario.travel_time_min(previous, stop), stop.window_start)
        if arrival > stop.window_end or arrival + stop.service_min > min(courier.shift_end, unavailable):
            return None
        if demand + stop.demand > courier.capacity:
            return None
        if any(isinstance(r, TagDeadline) and r.tag in stop.tags and arrival > r.within_minutes_from_start for r in rules.constraints):
            return None
        result.append(RouteVisit(stop_id=stop.id, arrival_min=arrival))
        current, previous, demand = arrival + stop.service_min, stop, demand + stop.demand
    if route and current + scenario.travel_time_min(previous, scenario.depot) > courier.shift_end:
        return None
    return result


def solve(scenario: Scenario, constraints, time_limit_s: float = 10) -> SolveResult:
    """Solve the constrained VRP; always return a plan, using the local fallback on errors."""
    started = perf_counter()
    rules = ConstraintSet()
    try:
        rules = _constraint_set(scenario, constraints)
        if not scenario.stops:
            return SolveResult(Plan(routes={c.id: [] for c in scenario.couriers}), {}, perf_counter() - started, "optimal")
        if not scenario.couriers:
            plan, status = Plan(routes={}, unserved_stops=[s.id for s in scenario.stops]), "fallback-no-couriers"
        else:
            try:
                plan, status = _solve_ortools(scenario, rules, time_limit_s)
            except Exception:
                plan, status = _fallback(scenario, rules)
        reasons = {stop_id: _reason(stop_id, scenario, rules) for stop_id in plan.unserved_stops}
        return SolveResult(plan, reasons, perf_counter() - started, status)
    except Exception:
        # Invalid inputs and optional dependency/runtime failures are represented in status.
        try:
            fallback_rules = _constraint_set(scenario, constraints)
            plan, status = _fallback(scenario, fallback_rules) if scenario.couriers else (Plan(routes={}, unserved_stops=[s.id for s in scenario.stops]), "fallback-no-couriers")
        except Exception:
            plan = Plan(routes={c.id: [] for c in scenario.couriers}, unserved_stops=[s.id for s in scenario.stops])
            fallback_rules = ConstraintSet()
            status = "error-fallback"
        reasons = {stop_id: _reason(stop_id, scenario, fallback_rules) for stop_id in plan.unserved_stops}
        return SolveResult(plan, reasons, perf_counter() - started, status)
