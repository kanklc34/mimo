from __future__ import annotations

from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator


class StrictConstraint(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CourierUnavailableAfter(StrictConstraint):
    type: Literal["courier_unavailable_after"]
    courier_id: str
    time_min: int = Field(ge=0)


class TagDeadline(StrictConstraint):
    type: Literal["tag_deadline"]
    tag: str
    within_minutes_from_start: int = Field(ge=0)


class MaxStops(StrictConstraint):
    type: Literal["max_stops"]
    courier_id: str
    n: int = Field(ge=0)


Constraint: TypeAlias = Annotated[
    CourierUnavailableAfter | TagDeadline | MaxStops,
    Field(discriminator="type"),
]


class ConstraintSet(BaseModel):
    model_config = ConfigDict(extra="forbid")
    constraints: list[Constraint] = Field(default_factory=list)

    @field_validator("constraints")
    @classmethod
    def references_exist(cls, constraints, info: ValidationInfo):
        scenario = (info.context or {}).get("scenario")
        if scenario is None:
            return constraints
        for constraint in constraints:
            if isinstance(constraint, (CourierUnavailableAfter, MaxStops)):
                if constraint.courier_id not in scenario.courier_ids:
                    raise ValueError(f"unknown courier_id: {constraint.courier_id}")
            if isinstance(constraint, TagDeadline) and constraint.tag not in scenario.tags:
                raise ValueError(f"unknown tag: {constraint.tag}")
        return constraints

    def validate_references(self, scenario) -> None:
        for constraint in self.constraints:
            if isinstance(constraint, (CourierUnavailableAfter, MaxStops)):
                if constraint.courier_id not in scenario.courier_ids:
                    raise ValueError(f"unknown courier_id: {constraint.courier_id}")
            if isinstance(constraint, TagDeadline) and constraint.tag not in scenario.tags:
                raise ValueError(f"unknown tag: {constraint.tag}")
