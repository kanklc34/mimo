from scripts.demo_scenario import build_demo_result
from validator import validate


def test_demo_produces_at_least_five_changes_and_valid_plan():
    scenario, before, result, changes, constraints = build_demo_result()
    # The requested tuning is conditional: adjust only if the change count is below five.
    assert len(changes) >= 5
    assert validate(result.plan, scenario, constraints) == []
    assert result.status
    assert before.plan


def test_demo_targets_real_couriers_and_reports_reasons_for_unserved():
    scenario, _before, result, _changes, constraints = build_demo_result()
    courier_ids = scenario.courier_ids
    assert all(
        rule.courier_id in courier_ids
        for rule in constraints.constraints
        if hasattr(rule, "courier_id")
    )
    assert set(result.unserved_reasons) == set(result.plan.unserved_stops)
