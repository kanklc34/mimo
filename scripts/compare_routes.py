from __future__ import annotations

import json
import sys
from time import perf_counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from constraints import ConstraintSet
from generator import generate_scenario
from solver.baselines import clustered_naive_plan
from solver.naive import naive_plan, plan_distance_km
from solver.ortools_solver import solve
from validator import validate


def main() -> None:
    scenario = generate_scenario(seed=42)
    courier_name = scenario.couriers[0].name
    cases = {
        "kısıtsız": [],
        f"{courier_name} 14:00 sonrası çalışamaz (vardiya başlangıcından 360 dk)": [
            {"type": "courier_unavailable_after", "courier_id": "courier-1", "time_min": 360}
        ],
        "soğuk zincir ilk 120 dk içinde": [
            {"type": "tag_deadline", "tag": "soğuk_zincir", "within_minutes_from_start": 120}
        ],
    }
    measurements = []
    for name, raw_constraints in cases.items():
        constraints = ConstraintSet.model_validate(
            {"constraints": raw_constraints}, context={"scenario": scenario}
        )
        started = perf_counter()
        naive = naive_plan(scenario)
        naive_time = perf_counter() - started
        started = perf_counter()
        clustered = clustered_naive_plan(scenario)
        clustered_time = perf_counter() - started
        result = solve(scenario, constraints, time_limit_s=10)
        plans = {
            "naive": (naive, naive_time, None),
            "clustered_naive": (clustered, clustered_time, None),
            "ortools": (result.plan, result.solve_time_s, result.status),
        }
        scenario_result = {"scenario": name, "plans": {}}
        for plan_name, (plan, duration, status) in plans.items():
            violations = validate(plan, scenario, constraints)
            scenario_result["plans"][plan_name] = {
                "distance_km": round(plan_distance_km(plan, scenario), 2),
                "violations": len(violations),
                "unserved": len(plan.unserved_stops),
                "solve_time_s": round(duration, 4),
                "status": status,
            }
        measurements.append(scenario_result)
    print(json.dumps(measurements, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
