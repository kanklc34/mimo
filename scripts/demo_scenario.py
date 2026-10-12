from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from constraints import ConstraintSet
from generator import generate_scenario
from solver.diff import diff_plans
from solver.ortools_solver import solve
from validator import validate


def build_demo_result(unavailable_min: int = 180, max_stops: int = 24):
    scenario = generate_scenario(seed=42)
    # The generator currently names these couriers Kurye 1 and Kurye 2.
    unavailable_courier = limited_courier = scenario.couriers[0]
    before = solve(scenario, [], time_limit_s=10)
    constraints = ConstraintSet.model_validate(
        {"constraints": [
            {"type": "courier_unavailable_after", "courier_id": unavailable_courier.id, "time_min": unavailable_min},
            {"type": "max_stops", "courier_id": limited_courier.id, "n": max_stops},
            {"type": "tag_deadline", "tag": "soğuk_zincir", "within_minutes_from_start": 120},
        ]},
        context={"scenario": scenario},
    )
    after = solve(scenario, constraints, time_limit_s=10, previous_plan=before.plan)
    changes = diff_plans(before.plan, after.plan)
    return scenario, before, after, changes, constraints


def main() -> None:
    scenario, _before, result, changes, constraints = build_demo_result()
    first = scenario.couriers[0]
    print(f"Yeni talimat: {first.name} {constraints.constraints[0].time_min}. dakikadan sonra yok; "
          f"{first.name} en fazla {constraints.constraints[1].n} durak; "
          "soğuk zincir ilk 120 dakikada teslim.")
    meaningful = [change for change in changes if change["type"] != "sadece_saat_kaydi"]
    time_only = [change for change in changes if change["type"] == "sadece_saat_kaydi"]
    print(f"Gerçekten değişen durak: {len(meaningful)}")
    print(f"Yalnızca saat kaydı değişen durak: {len(time_only)}")
    if meaningful:
        print("Gerçek değişiklik kimlikleri: " + ", ".join(change["stop_id"] for change in meaningful))
    if result.plan.unserved_stops:
        print("Atlanan duraklar:")
        for stop_id in result.plan.unserved_stops:
            print(f"- {stop_id}: {result.unserved_reasons.get(stop_id, 'Sebep belirtilmedi.')}")
    print(json.dumps({
        "status": result.status,
        "solve_time_s": round(result.solve_time_s, 4),
        "validator_violations": len(validate(result.plan, scenario, constraints)),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
