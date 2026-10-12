from scripts.demo_scenario import build_demo_result
from validator import validate


def test_demo_produces_five_to_ten_meaningful_changes_and_valid_plan():
    scenario, before, result, changes, constraints = build_demo_result()
    meaningful = [change for change in changes if change["type"] != "sadece_saat_kaydi"]
    assert 5 <= len(meaningful) <= 10
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
