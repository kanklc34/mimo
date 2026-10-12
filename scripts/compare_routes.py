from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from constraints import ConstraintSet
from generator import generate_scenario
from solver.naive import naive_plan, plan_distance_km
from solver.ortools_solver import solve
from validator import validate


def main() -> None:
    scenario = generate_scenario(seed=42)
    cases = {
        "kısıtsız": [],
        "Ali 14:00 sonrası çalışamaz (vardiya başlangıcından 360 dk)": [
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
        baseline = naive_plan(scenario)
        baseline_violations = validate(baseline, scenario, constraints)
        result = solve(scenario, constraints, time_limit_s=10)
        solver_violations = validate(result.plan, scenario, constraints)
        measurements.append({
            "scenario": name,
            "naive": {
                "distance_km": round(plan_distance_km(baseline, scenario), 2),
                "violations": len(baseline_violations),
                "unserved": len(baseline.unserved_stops),
            },
            "solver": {
                "distance_km": round(plan_distance_km(result.plan, scenario), 2),
                "violations": len(solver_violations),
                "unserved": len(result.plan.unserved_stops),
                "solve_time_s": round(result.solve_time_s, 4),
                "status": result.status,
            },
        })
    print(json.dumps(measurements, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
