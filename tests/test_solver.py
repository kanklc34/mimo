from constraints import ConstraintSet
from generator import generate_scenario
from models import Courier, Depot, Scenario, Stop
from solver.ortools_solver import solve
from validator import validate


def _small_scenario(stops, *, capacity=10, shift_end=240):
    return Scenario(
        couriers=[Courier(id="ali", name="Ali", capacity=capacity, shift_start=0, shift_end=shift_end)],
        stops=stops,
        depot=Depot(lat=41.0082, lon=28.9784),
    )


def _stop(stop_id, *, lat=41.0082, lon=28.9784, demand=1, service=5, start=0, end=220, tags=None):
    return Stop(
        id=stop_id,
        lat=lat,
        lon=lon,
        demand=demand,
        service_min=service,
        window_start=start,
        window_end=end,
        tags=tags or [],
    )


def test_solver_returns_validator_clean_plan():
    scenario = generate_scenario(seed=42)
    constraints = ConstraintSet.model_validate({"constraints": [
        {"type": "tag_deadline", "tag": "soğuk_zincir", "within_minutes_from_start": 260}
    ]}, context={"scenario": scenario})
    result = solve(scenario, constraints)
    assert result.plan
    assert validate(result.plan, scenario, constraints) == []
    assert result.status
    assert result.solve_time_s >= 0


def test_courier_unavailable_after_limits_service_completion_only():
    scenario = _small_scenario([_stop("near", service=12)])
    constraints = [{"type": "courier_unavailable_after", "courier_id": "ali", "time_min": 12}]
    result = solve(scenario, constraints)
    assert result.plan.routes["ali"][0].arrival_min + 12 <= 12
    assert validate(result.plan, scenario, constraints) == []


def test_courier_unavailable_after_does_not_limit_other_couriers():
    scenario = _small_scenario([_stop("delivery", service=5)])
    scenario.couriers.append(Courier(id="ayse", name="Ayşe", capacity=10, shift_start=0, shift_end=240))
    constraints = [{"type": "courier_unavailable_after", "courier_id": "ali", "time_min": 0}]
    result = solve(scenario, constraints)
    assert result.status == "ortools"
    assert result.plan.routes["ali"] == []
    assert [v.stop_id for v in result.plan.routes["ayse"]] == ["delivery"]
    assert validate(result.plan, scenario, constraints) == []


def test_tag_deadline_is_minutes_from_shift_start():
    scenario = _small_scenario([_stop("tagged", start=35, tags=["soğuk_zincir"])])
    constraints = [{"type": "tag_deadline", "tag": "soğuk_zincir", "within_minutes_from_start": 35}]
    result = solve(scenario, constraints)
    assert result.plan.routes["ali"][0].arrival_min <= 35
    assert validate(result.plan, scenario, constraints) == []


def test_max_stops_limits_route_count():
    scenario = _small_scenario([_stop("one"), _stop("two", lon=28.979)])
    constraints = [{"type": "max_stops", "courier_id": "ali", "n": 1}]
    result = solve(scenario, constraints)
    assert sum(map(len, result.plan.routes.values())) <= 1
    assert validate(result.plan, scenario, constraints) == []


def test_infeasible_stop_is_unserved_with_reason():
    scenario = _small_scenario([_stop("too-heavy", demand=2)], capacity=1)
    result = solve(scenario, [])
    assert result.plan.unserved_stops == ["too-heavy"]
    assert result.unserved_reasons["too-heavy"]
    assert validate(result.plan, scenario, []) == []


def test_solver_is_deterministic_for_same_input():
    scenario = generate_scenario(seed=5)
    first = solve(scenario, [], time_limit_s=2)
    second = solve(scenario, [], time_limit_s=2)
    assert first.plan.model_dump() == second.plan.model_dump()
    assert first.unserved_reasons == second.unserved_reasons
    assert first.status == second.status


def test_previous_plan_is_optional_and_can_be_used_as_stability_hint():
    scenario = _small_scenario([_stop("one"), _stop("two", lon=28.979)])
    previous = solve(scenario, []).plan

    result = solve(scenario, [], previous_plan=previous)

    assert result.plan.model_dump() == previous.model_dump()
    assert validate(result.plan, scenario, []) == []
