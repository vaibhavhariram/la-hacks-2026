"""Tests for gis/noaa_wind.py."""
from gis.noaa_wind import dominant_wind, get_wind_obs


def test_fixture_mode_loads_wind_obs():
    obs = get_wind_obs(data_mode="fixture")
    assert len(obs) >= 3
    assert all(o.station == "BUR" for o in obs)


def test_fixture_dominant_wind_is_plausible():
    obs = get_wind_obs(data_mode="fixture")
    speed_ms, direction_deg = dominant_wind(obs)
    assert speed_ms > 0
    assert 0 <= direction_deg <= 360
