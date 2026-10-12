from __future__ import annotations

from math import asin, ceil, cos, radians, sin, sqrt

EARTH_RADIUS_KM = 6371.0088
AVERAGE_SPEED_KMH = 30


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return great-circle distance in kilometers for two latitude/longitude points."""
    lat1_r, lat2_r = radians(lat1), radians(lat2)
    delta_lat = radians(lat2 - lat1)
    delta_lon = radians(lon2 - lon1)
    a = sin(delta_lat / 2) ** 2 + cos(lat1_r) * cos(lat2_r) * sin(delta_lon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * asin(sqrt(a))


def travel_time_min(distance_km: float) -> int:
    """Estimate travel time at the documented 30 km/h average speed, rounded up."""
    if distance_km < 0:
        raise ValueError("distance_km cannot be negative")
    return ceil(distance_km / AVERAGE_SPEED_KMH * 60)
