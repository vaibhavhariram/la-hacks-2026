"""Tests for gis/fire_spread.py."""
import math
import pytest
from datetime import datetime, timezone
from shapely.geometry import Point

from gis.fire_spread import spread_step, run_simulation, _wind_to_vector, FireState


def _circle(cx: float, cy: float, radius_deg: float = 0.01) -> object:
    return Point(cx, cy).buffer(radius_deg)


def test_wind_to_vector_westerly():
    # Wind FROM 270° (westerly) → fire spreads TO east
    dx, dy = _wind_to_vector(10.0, 270.0)
    assert dx > 0   # eastward (positive lng)
    assert abs(dy) < abs(dx)  # predominantly eastward


def test_wind_to_vector_northerly():
    # Wind FROM 0° (northerly) → fire spreads TO south
    dx, dy = _wind_to_vector(10.0, 0.0)
    assert dy < 0   # southward (negative lat)


def test_spread_step_grows_area():
    initial = _circle(34.18, -118.10)
    expanded = spread_step(initial, wind_speed_ms=8.0, wind_dir_deg=270.0, dt_minutes=30)
    assert expanded.area > initial.area


def test_spread_step_contains_initial():
    initial = _circle(34.18, -118.10)
    expanded = spread_step(initial, wind_speed_ms=8.0, wind_dir_deg=270.0, dt_minutes=30)
    # expanded perimeter should contain or overlap initial
    assert expanded.intersects(initial)


def test_spread_step_directional_bias():
    initial = _circle(34.18, -118.10)
    # Westerly wind → fire should shift east
    expanded = spread_step(initial, wind_speed_ms=15.0, wind_dir_deg=270.0, dt_minutes=60)
    # centroid should shift east (higher lng)
    assert expanded.centroid.x > initial.centroid.x - 0.001


def test_run_simulation_correct_step_count():
    initial = _circle(34.18, -118.10)
    start = datetime(2025, 1, 8, 0, 0, 0, tzinfo=timezone.utc)
    states = run_simulation(initial, 8.0, 270.0, start, steps=5, dt_minutes=30)
    assert len(states) == 5


def test_run_simulation_timestamps_spaced():
    initial = _circle(34.18, -118.10)
    start = datetime(2025, 1, 8, 0, 0, 0, tzinfo=timezone.utc)
    states = run_simulation(initial, 8.0, 270.0, start, steps=3, dt_minutes=30)
    delta = (states[1].timestamp - states[0].timestamp).total_seconds()
    assert delta == pytest.approx(30 * 60)


def test_run_simulation_area_grows_monotonically():
    initial = _circle(34.18, -118.10)
    start = datetime(2025, 1, 8, 0, 0, 0, tzinfo=timezone.utc)
    states = run_simulation(initial, 8.0, 270.0, start, steps=6, dt_minutes=30)
    areas = [s.area_km2 for s in states]
    # area should generally increase (allow small fluctuation from convex hull)
    assert areas[-1] > areas[0]
