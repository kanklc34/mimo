from dataclasses import dataclass

import pytest

from constraints import ConstraintSet
from models import Plan, RouteVisit
from validator import validate


def codes(violations):
    return [violation.type for violation in violations]


def test_valid_plan_has_no_violations(valid_plan, scenario, constraints):
    assert validate(valid_plan, scenario, constraints) == []


@dataclass
class Mutation:
    name: str
    plan: Plan
    scenario: object
    constraints: object
    expected_type: str


@pytest.fixture
def mutations(scenario, valid_plan, constraints):
    first_courier = scenario.couriers[0]
    first_stop = scenario.stops[0]
    first_route = valid_plan.routes[first_courier.id]
    first_visit = first_route[0]
    expected = []

    def add(name, plan=valid_plan, sc=scenario, cs=constraints, violation=""):
        expected.append(Mutation(name, plan, sc, cs, violation))

    add("missing stop", valid_plan.model_copy(update={"routes": {**valid_plan.routes, first_courier.id: first_route[1:]}}), violation="stop_coverage")
    duplicate_target = next(
        visit for visit in first_route
        if "soğuk_zincir" not in scenario.stop_by_id[visit.stop_id].tags
    )
    duplicate_arrival = first_route[-1].arrival_min + scenario.stop_by_id[first_route[-1].stop_id].service_min + 60
    duplicate_later = duplicate_target.model_copy(update={"arrival_min": duplicate_arrival})
    add("duplicate stop", valid_plan.model_copy(update={"routes": {**valid_plan.routes, first_courier.id: first_route + [duplicate_later]}}), violation="duplicate_stop")
    add("unknown stop", valid_plan.model_copy(update={"routes": {**valid_plan.routes, first_courier.id: first_route + [RouteVisit(stop_id="ghost", arrival_min=100)]}}), violation="unknown_stop")
    add("unknown courier", valid_plan.model_copy(update={"routes": {**valid_plan.routes, "ghost": []}}), violation="unknown_courier")
    skipped_plan = valid_plan.model_copy(update={"routes": {**valid_plan.routes, first_courier.id: first_route[1:]}, "unserved_stops": [first_visit.stop_id]})
    add("duplicate unserved", skipped_plan.model_copy(update={"unserved_stops": [first_visit.stop_id, first_visit.stop_id]}), violation="duplicate_unserved_stop")
    add("visited and unserved", valid_plan.model_copy(update={"unserved_stops": [first_visit.stop_id]}), violation="visited_and_unserved")

    route_demand = sum(scenario.stop_by_id[v.stop_id].demand for v in first_route)
    changed_courier = first_courier.model_copy(update={"capacity": route_demand - 1})
    changed_scenario = scenario.model_copy(update={"couriers": [changed_courier, *scenario.couriers[1:]]})
    add("capacity exceeded", sc=changed_scenario, violation="capacity_exceeded")

    def with_first_visit(visit, sc=scenario):
        return valid_plan.model_copy(update={"routes": {**valid_plan.routes, first_courier.id: [visit, *first_route[1:]]}})

    add("negative arrival before shift", with_first_visit(first_visit.model_copy(update={"arrival_min": -1})), violation="invalid_time")
    last_visit = first_route[-1]
    last_stop = scenario.stop_by_id[last_visit.stop_id]
    shortened_shift_courier = first_courier.model_copy(update={"shift_end": last_visit.arrival_min + last_stop.service_min - 1})
    shortened_shift_scenario = scenario.model_copy(update={"couriers": [shortened_shift_courier, *scenario.couriers[1:]]})
    add("after shift", valid_plan, shortened_shift_scenario, violation=("outside_shift", "vardiya_asimi_donus"))
    actual_first_stop = scenario.stop_by_id[first_visit.stop_id]
    changed_stop = actual_first_stop.model_copy(update={"window_start": first_visit.arrival_min + 1, "window_end": first_visit.arrival_min + 1000})
    changed_scenario = scenario.model_copy(update={"stops": [changed_stop if stop.id == actual_first_stop.id else stop for stop in scenario.stops]})
    add("early window", with_first_visit(first_visit, changed_scenario), sc=changed_scenario, violation="window_violation")
    changed_stop = actual_first_stop.model_copy(update={"window_end": first_visit.arrival_min - 1})
    changed_scenario = scenario.model_copy(update={"stops": [changed_stop if stop.id == actual_first_stop.id else stop for stop in scenario.stops]})
    add("late window", with_first_visit(first_visit, changed_scenario), sc=changed_scenario, violation="window_violation")
    distant_depot = scenario.depot.model_copy(update={"lat": scenario.depot.lat + 0.25})
    distant_depot_scenario = scenario.model_copy(update={"depot": distant_depot})
    add("insufficient depot travel", valid_plan, distant_depot_scenario, violation="travel_time_violation")

    second_visit = first_route[1]
    reversed_route = [first_visit.model_copy(update={"arrival_min": second_visit.arrival_min + 5}), second_visit, *first_route[2:]]
    add("arrival order reversed", valid_plan.model_copy(update={"routes": {**valid_plan.routes, first_courier.id: reversed_route}}), violation="travel_time_violation")
    too_soon = first_route[1].model_copy(update={"arrival_min": first_visit.arrival_min + scenario.stop_by_id[first_visit.stop_id].service_min})
    second_stop = scenario.stop_by_id[too_soon.stop_id]
    wide_window = second_stop.model_copy(update={"window_start": 0, "window_end": 480})
    wide_scenario = scenario.model_copy(update={"stops": [wide_window if stop.id == second_stop.id else stop for stop in scenario.stops]})
    add("service and travel overlap", valid_plan.model_copy(update={"routes": {**valid_plan.routes, first_courier.id: [first_visit, too_soon, *first_route[2:]]}}), wide_scenario, violation="travel_time_violation")

    unavailable = ConstraintSet.model_validate({"constraints": [{"type": "courier_unavailable_after", "courier_id": first_courier.id, "time_min": first_visit.arrival_min - 1}]}, context={"scenario": scenario})
    add("unavailable courier", cs=unavailable, violation="courier_unavailable_after")
    max_stops = ConstraintSet.model_validate({"constraints": [{"type": "max_stops", "courier_id": first_courier.id, "n": len(first_route) - 1}]}, context={"scenario": scenario})
    add("max stops exceeded", cs=max_stops, violation="max_stops")

    cold = next(stop for stop in scenario.stops if "soğuk_zincir" in stop.tags)
    cold_courier_id = next(cid for cid, route in valid_plan.routes.items() if any(v.stop_id == cold.id for v in route))
    cold_visit = next(v for v in valid_plan.routes[cold_courier_id] if v.stop_id == cold.id)
    deadline = ConstraintSet.model_validate({"constraints": [{"type": "tag_deadline", "tag": "soğuk_zincir", "within_minutes_from_start": cold_visit.arrival_min - 1}]}, context={"scenario": scenario})
    add("tag deadline", cs=deadline, violation="tag_deadline")

    negative = with_first_visit(first_visit.model_copy(update={"arrival_min": -4}))
    add("negative arrival", negative, violation="invalid_time")
    wrong_courier_plan = valid_plan.model_copy(update={"routes": {**valid_plan.routes, first_courier.id: [], "ghost": first_route}})
    add("wrong courier assignment", wrong_courier_plan, violation="unknown_courier")
    add("unknown unserved stop", valid_plan.model_copy(update={"unserved_stops": ["ghost"]}), violation="unknown_stop")

    last_visit = first_route[-1]
    last_stop = scenario.stop_by_id[last_visit.stop_id]
    return_min = last_visit.arrival_min + last_stop.service_min + scenario.travel_time_min(last_stop, scenario.depot)
    return_exceeds_courier = first_courier.model_copy(update={"shift_end": return_min - 1})
    return_exceeds_scenario = scenario.model_copy(update={"couriers": [return_exceeds_courier, *scenario.couriers[1:]]})
    add("return exceeds shift", sc=return_exceeds_scenario, violation="vardiya_asimi_donus")

    for name, shift_end in (("return within shift", return_min + 1), ("return exactly at shift end", return_min)):
        return_courier = first_courier.model_copy(update={"shift_end": shift_end})
        return_scenario = scenario.model_copy(update={"couriers": [return_courier, *scenario.couriers[1:]]})
        add(name, sc=return_scenario, violation=None)

    assert len(expected) == 23
    return expected


@pytest.mark.parametrize("index", range(23))
def test_mutations_are_detected_without_false_alarms(index, mutations):
    mutation = mutations[index]
    found = validate(mutation.plan, mutation.scenario, mutation.constraints)
    found_types = codes(found)
    if mutation.expected_type is None:
        assert found_types == [], mutation.name
        unexpected = found_types
    else:
        expected_types = {mutation.expected_type} if isinstance(mutation.expected_type, str) else set(mutation.expected_type)
        assert expected_types.issubset(found_types), mutation.name
        unexpected = [kind for kind in found_types if kind not in expected_types]
    print(f"Mutation results: {index + 1}/23 exercised; {len(unexpected)} unexpected violation(s) for {mutation.name}")


def test_mutation_report_counts_detection_and_false_alarms(mutations, scenario, constraints):
    caught = 0
    false_alarms = 0
    for mutation in mutations:
        found = codes(validate(mutation.plan, mutation.scenario, mutation.constraints))
        if mutation.expected_type is None:
            caught += not found
            unexpected = found
        else:
            expected_types = {mutation.expected_type} if isinstance(mutation.expected_type, str) else set(mutation.expected_type)
            caught += expected_types.issubset(found)
            unexpected = [code for code in found if code not in expected_types]
        false_alarms += len(unexpected)
        if unexpected:
            print(f"Unexpected for {mutation.name}: {unexpected}")
    print(f"Mutation summary: {caught}/23 handled; {false_alarms} false alarms")
    assert caught == 23
    assert false_alarms == 0


def test_skipped_stops_are_not_violations(valid_plan, scenario, constraints):
    skipped_id = valid_plan.routes[scenario.couriers[0].id][0].stop_id
    routes = {cid: [v for v in visits if v.stop_id != skipped_id] for cid, visits in valid_plan.routes.items()}
    plan = valid_plan.model_copy(update={"routes": routes, "unserved_stops": [skipped_id]})
    assert validate(plan, scenario, constraints) == []
