from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Courier(StrictModel):
    id: str
    name: str
    capacity: int = Field(gt=0)
    shift_start: int = Field(ge=0)
    shift_end: int = Field(gt=0)

    @model_validator(mode="after")
    def shift_has_positive_length(self):
        if self.shift_end <= self.shift_start:
            raise ValueError("shift_end must be after shift_start")
        return self


class Stop(StrictModel):
    id: str
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    demand: int = Field(gt=0)
    service_min: int = Field(ge=0)
    window_start: int = Field(ge=0)
    window_end: int = Field(gt=0)
    tags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def window_has_positive_length(self):
        if self.window_end < self.window_start:
            raise ValueError("window_end must be at or after window_start")
        return self


class Depot(StrictModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


class RouteVisit(StrictModel):
    stop_id: str
    arrival_min: int

    @model_validator(mode="before")
    @classmethod
    def accept_stop_arrival_pair(cls, value):
        if isinstance(value, (tuple, list)) and len(value) == 2:
            return {"stop_id": value[0], "arrival_min": value[1]}
        return value


class Plan(StrictModel):
    routes: dict[str, list[RouteVisit]] = Field(default_factory=dict)
    unserved_stops: list[str] = Field(default_factory=list)


class Violation(StrictModel):
    type: str
    stop_id: str | None = None
    courier_id: str | None = None
    description: str
