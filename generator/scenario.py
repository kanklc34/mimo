from __future__ import annotations

import random

from models import Courier, Depot, Scenario, Stop


def generate_scenario(seed: int = 42) -> Scenario:
    """Create a reproducible synthetic Istanbul scenario with 50 stops and 4 couriers.

    Coordinates are sampled around central Istanbul. Haversine distance is used as a
    straight-line approximation; travel time assumes a constant average speed of
    30 km/h and rounds every leg up to an integer minute. Roads and traffic are not
    modeled. All shift and service times are integer minutes from shift start.
    """
    rng = random.Random(seed)
    depot = Depot(lat=41.0082, lon=28.9784)
    couriers = [
        Courier(id=f"courier-{index + 1}", name=f"Kurye {index + 1}", capacity=50, shift_start=0, shift_end=480)
        for index in range(4)
    ]
    stops = []
    cold_chain_ids = set(rng.sample(range(1, 51), 4))
    for index in range(1, 51):
        tags = ["soğuk_zincir"] if index in cold_chain_ids else []
        stops.append(
            Stop(
                id=f"stop-{index:02d}",
                lat=41.0082 + rng.uniform(-0.045, 0.045),
                lon=28.9784 + rng.uniform(-0.055, 0.055),
                demand=rng.randint(1, 3),
                service_min=rng.randint(3, 8),
                window_start=rng.randint(0, 45),
                window_end=rng.randint(360, 480),
                tags=tags,
            )
        )
    return Scenario(couriers=couriers, stops=stops, depot=depot)
