from __future__ import annotations

from typing import Protocol

from constraints import ConstraintSet
from models import Plan, Scenario
from solver import naive_plan


class Planner(Protocol):
    def plan(self, scenario: Scenario, constraints: ConstraintSet) -> tuple[Plan, dict[str, str]]: ...


class MockPlanner:
    """Temporary planner adapter; replace this implementation when a solver arrives."""

    def plan(self, scenario: Scenario, constraints: ConstraintSet) -> tuple[Plan, dict[str, str]]:
        del constraints
        return naive_plan(scenario), {}
