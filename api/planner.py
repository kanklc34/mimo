from __future__ import annotations

from typing import Protocol

from constraints import ConstraintSet
from models import Plan, Scenario
from solver.ortools_solver import solve


class Planner(Protocol):
    def plan(
        self, scenario: Scenario, constraints: ConstraintSet, previous_plan: Plan | None = None
    ) -> tuple[Plan, dict[str, str]]: ...


class OrtoolsPlanner:
    """Adapter that keeps the API's planner contract while using the VRP solver."""

    def plan(
        self, scenario: Scenario, constraints: ConstraintSet, previous_plan: Plan | None = None
    ) -> tuple[Plan, dict[str, str]]:
        result = solve(scenario, constraints, previous_plan=previous_plan)
        return result.plan, result.unserved_reasons
