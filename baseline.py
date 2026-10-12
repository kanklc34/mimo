"""Run the deterministic naive baseline and print distance and validation results."""

from constraints import ConstraintSet
from generator import generate_scenario
from solver import naive_plan, plan_distance_km
from validator import validate


def main() -> None:
    scenario = generate_scenario()
    plan = naive_plan(scenario)
    violations = validate(plan, scenario, ConstraintSet())
    print(f"Baseline total distance: {plan_distance_km(plan, scenario):.2f} km")
    print(f"Baseline violations: {len(violations)}")
    print(f"Unserved stops: {len(plan.unserved_stops)} ({', '.join(plan.unserved_stops) or 'none'})")


if __name__ == "__main__":
    main()
