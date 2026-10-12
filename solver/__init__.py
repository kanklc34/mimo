"""Future OR-Tools route optimizer with a simple naive plan generator."""

from .naive import naive_plan, plan_distance_km

__all__ = ["naive_plan", "plan_distance_km"]
