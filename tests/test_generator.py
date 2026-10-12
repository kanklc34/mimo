from generator import generate_scenario
from generator.distance import haversine_km, travel_time_min


def test_generator_is_seeded_and_has_expected_istanbul_data():
    first = generate_scenario(seed=123)
    second = generate_scenario(seed=123)
    assert first == second
    assert len(first.stops) == 50
    assert len(first.couriers) == 4
    assert sum("soğuk_zincir" in stop.tags for stop in first.stops) >= 2
    assert 40.0 < first.depot.lat < 42.0
    assert 28.0 < first.depot.lon < 30.0


def test_haversine_and_integer_travel_time():
    assert haversine_km(0, 0, 0, 0) == 0
    assert travel_time_min(1.0) == 2
    assert isinstance(travel_time_min(0.1), int)
