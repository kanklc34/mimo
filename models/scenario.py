from __future__ import annotations

from .entities import Courier, Depot, Stop, StrictModel


class Scenario(StrictModel):
    couriers: list[Courier]
    stops: list[Stop]
    depot: Depot

    @property
    def courier_ids(self) -> set[str]:
        return {courier.id for courier in self.couriers}

    @property
    def stop_ids(self) -> set[str]:
        return {stop.id for stop in self.stops}

    @property
    def tags(self) -> set[str]:
        return {tag for stop in self.stops for tag in stop.tags}

    @property
    def courier_by_id(self) -> dict[str, Courier]:
        return {courier.id: courier for courier in self.couriers}

    @property
    def stop_by_id(self) -> dict[str, Stop]:
        return {stop.id: stop for stop in self.stops}

    def distance_km(self, origin: Depot | Stop, destination: Depot | Stop) -> float:
        from generator.distance import haversine_km

        return haversine_km(origin.lat, origin.lon, destination.lat, destination.lon)

    def travel_time_min(self, origin: Depot | Stop, destination: Stop) -> int:
        from generator.distance import travel_time_min

        return travel_time_min(self.distance_km(origin, destination))
