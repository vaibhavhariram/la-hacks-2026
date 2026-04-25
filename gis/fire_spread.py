"""Wind-driven fire spread simulation — directional cone + scatter model.

No cellular automata, no heat physics, no terrain elevation.
Expands a Shapely polygon each time step biased toward downwind direction.
"""
import json
import math
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import requests
from shapely.geometry import mapping, Point, Polygon
from shapely.ops import unary_union

SNAPSHOTS_DIR = Path(__file__).parent / "data" / "snapshots"


@dataclass
class FireState:
    timestamp: datetime
    perimeter: Polygon
    area_km2: float
    step: int


def _wind_to_vector(speed_ms: float, direction_deg: float) -> tuple[float, float]:
    """Convert meteorological wind (FROM direction) to spread vector (TO direction)."""
    spread_deg = (direction_deg + 180) % 360
    rad = math.radians(spread_deg)
    return (speed_ms * math.sin(rad), speed_ms * math.cos(rad))  # (dx_lng, dy_lat)


def spread_step(
    current: Polygon,
    wind_speed_ms: float,
    wind_dir_deg: float,
    dt_minutes: int = 30,
) -> Polygon:
    """Advance fire perimeter by one time step.

    Strategy:
    - Base radial expansion: proportional to sqrt(dt) to simulate area growth
    - Downwind bias: expand 3x more in wind direction than upwind
    - Light scatter: small random perturbation on perimeter points
    """
    dt_hours = dt_minutes / 60.0
    dx, dy = _wind_to_vector(wind_speed_ms, wind_dir_deg)

    cx, cy = current.centroid.x, current.centroid.y
    coords = list(current.exterior.coords)

    base_expansion_deg = wind_speed_ms * dt_hours * 0.003  # ~0.003 deg/ms/h empirical
    rng = np.random.default_rng(seed=int(current.area * 1e10) % (2**31))

    new_coords = []
    for x, y in coords:
        # angle from centroid to this point
        angle = math.atan2(y - cy, x - cx)

        # wind alignment: 1.0 = fully downwind, -1.0 = fully upwind
        wind_angle = math.atan2(dy, dx)
        alignment = math.cos(angle - wind_angle)  # -1 to 1

        # expansion factor: downwind 3x, upwind 0.5x
        factor = 1.0 + 1.0 * alignment  # 0.0 to 2.0 → remap to 0.5–3.0
        factor = 0.5 + factor * 1.25

        expansion = base_expansion_deg * factor
        scatter = rng.normal(0, base_expansion_deg * 0.1)

        new_x = x + math.cos(angle) * (expansion + scatter)
        new_y = y + math.sin(angle) * (expansion + scatter)
        new_coords.append((new_x, new_y))

    expanded = Polygon(new_coords)
    return unary_union([current, expanded]).convex_hull


def run_simulation(
    initial_perimeter: Polygon,
    wind_speed_ms: float,
    wind_dir_deg: float,
    start_time: datetime,
    steps: int = 12,
    dt_minutes: int = 30,
) -> list[FireState]:
    """Run full simulation, returning list of FireState snapshots."""
    states: list[FireState] = []
    current = initial_perimeter
    t = start_time

    for i in range(steps):
        area_m2 = current.area * (111_000 ** 2)  # rough deg² → m²
        states.append(FireState(
            timestamp=t,
            perimeter=current,
            area_km2=round(area_m2 / 1e6, 3),
            step=i,
        ))
        current = spread_step(current, wind_speed_ms, wind_dir_deg, dt_minutes)
        t += timedelta(minutes=dt_minutes)

    return states


def export_snapshots(states: list[FireState], out_dir: Path = SNAPSHOTS_DIR) -> list[Path]:
    """Write each state to a GeoJSON file. Static replay fallback."""
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for s in states:
        feature = {
            "type": "Feature",
            "geometry": mapping(s.perimeter),
            "properties": {
                "step": s.step,
                "timestamp": s.timestamp.isoformat(),
                "area_km2": s.area_km2,
            },
        }
        p = out_dir / f"step_{s.step:02d}.geojson"
        p.write_text(json.dumps({"type": "FeatureCollection", "features": [feature]}, indent=2))
        paths.append(p)
    print(f"[fire_spread] exported {len(paths)} snapshots to {out_dir}")
    return paths


def post_hazards(states: list[FireState], backend_url: str | None = None) -> None:
    """POST each fire state to /hazard endpoint as a circle approximation."""
    if backend_url is None:
        backend_url = os.environ.get("BACKEND_URL", "http://localhost:8001")

    for s in states:
        cx, cy = s.perimeter.centroid.x, s.perimeter.centroid.y
        # approximate radius from area
        radius_m = math.sqrt(s.area_km2 * 1e6 / math.pi)
        severity = min(1.0, s.area_km2 / 50.0)  # 50 km² = severity 1.0

        payload = {
            "type": "fire",
            "lat": round(cy, 6),
            "lng": round(cx, 6),
            "radius_m": round(radius_m, 1),
            "severity": round(severity, 3),
        }
        try:
            r = requests.post(f"{backend_url}/hazard", json=payload, timeout=5)
            r.raise_for_status()
            print(f"[fire_spread] step {s.step} → /hazard  {r.status_code}")
        except requests.RequestException as e:
            print(f"[fire_spread] step {s.step} POST failed: {e}")
