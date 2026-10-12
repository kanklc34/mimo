import pytest
from pydantic import ValidationError

from constraints import ConstraintSet
from models import Plan
from validator import validate


def test_constraint_json_schema_has_three_supported_types():
    schema = ConstraintSet.model_json_schema()
    serialized = str(schema)
    for kind in ("courier_unavailable_after", "tag_deadline", "max_stops"):
        assert kind in serialized


def test_constraints_reject_unknown_courier(scenario):
    with pytest.raises(ValidationError):
        ConstraintSet.model_validate(
            {"constraints": [{"type": "courier_unavailable_after", "courier_id": "ghost", "time_min": 10}]},
            context={"scenario": scenario},
        )


def test_constraints_reject_unknown_tag(scenario):
    with pytest.raises(ValidationError):
        ConstraintSet.model_validate(
            {"constraints": [{"type": "tag_deadline", "tag": "hayalet", "within_minutes_from_start": 10}]},
            context={"scenario": scenario},
        )


def test_validator_rejects_unknown_stop_reference(scenario, valid_plan):
    courier_id = scenario.couriers[0].id
    plan = Plan.model_validate(
        {"routes": {**valid_plan.routes, courier_id: [*valid_plan.routes[courier_id], ("ghost", 100)]}}
    )
    assert "unknown_stop" in {item.type for item in validate(plan, scenario, ConstraintSet())}


def test_constraint_set_accepts_all_supported_shapes(scenario):
    parsed = ConstraintSet.model_validate(
        {
            "constraints": [
                {"type": "courier_unavailable_after", "courier_id": scenario.couriers[0].id, "time_min": 60},
                {"type": "tag_deadline", "tag": "soğuk_zincir", "within_minutes_from_start": 120},
                {"type": "max_stops", "courier_id": scenario.couriers[1].id, "n": 5},
            ]
        },
        context={"scenario": scenario},
    )
    assert len(parsed.constraints) == 3


def test_plan_accepts_stop_arrival_pairs(scenario):
    plan = Plan(routes={scenario.couriers[0].id: [(scenario.stops[0].id, 10)]})
    assert plan.routes[scenario.couriers[0].id][0].stop_id == scenario.stops[0].id
    assert plan.routes[scenario.couriers[0].id][0].arrival_min == 10
