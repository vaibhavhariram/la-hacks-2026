"""AEGIS demo replay — Eaton Fire Jan 8, 2025.

Runs the full pipeline end-to-end:
  1. Load FIRMS fire points (from cache or API)
  2. Load NOAA wind observations (from cache or API)
  3. Build initial fire perimeter from FIRMS point cluster
  4. Run 12-step wind-driven fire spread simulation (6 hours @ 30 min steps)
  5. POST each step to backend /hazard endpoint
  6. Export static GeoJSON snapshots as fallback

Usage:
    python scripts/run_demo.py [--steps N] [--dt-minutes M] [--no-post]
"""
import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# allow running from repo root
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from shapely.geometry import MultiPoint

from gis.firms_pipeline import get_fire_points
from gis.noaa_wind import get_wind_obs, dominant_wind
from gis.fire_spread import run_simulation, export_snapshots, post_hazards


def build_initial_perimeter(fire_points):
    """Build a convex hull polygon from FIRMS fire point cluster."""
    if not fire_points:
        raise ValueError("No fire points — check FIRMS data")
    coords = [(p.lng, p.lat) for p in fire_points]
    hull = MultiPoint(coords).convex_hull
    if hull.geom_type == "Point":
        # single point — buffer to small circle (~500m radius in degrees)
        hull = hull.buffer(0.005)
    elif hull.geom_type == "LineString":
        hull = hull.buffer(0.003)
    print(f"[demo] initial perimeter: {hull.area * 111000**2 / 1e6:.2f} km² ({len(fire_points)} points)")
    return hull


def main():
    parser = argparse.ArgumentParser(description="AEGIS Eaton Fire demo replay")
    parser.add_argument("--steps", type=int, default=12, help="Number of simulation steps (default: 12)")
    parser.add_argument("--dt-minutes", type=int, default=30, help="Minutes per step (default: 30)")
    parser.add_argument("--no-post", action="store_true", help="Skip POSTing to backend (export only)")
    args = parser.parse_args()

    load_dotenv()

    print("=== AEGIS Demo Replay — Eaton Fire Jan 8, 2025 ===\n")

    # Step 1 — FIRMS data
    print("[1/4] Loading FIRMS fire points...")
    fire_points = get_fire_points()
    print(f"      {len(fire_points)} points loaded\n")

    # Step 2 — Wind data
    print("[2/4] Loading NOAA wind observations...")
    wind_obs = get_wind_obs()
    speed_ms, direction_deg = dominant_wind(wind_obs)
    print(f"      Dominant wind: {speed_ms:.1f} m/s from {direction_deg:.0f}° ({len(wind_obs)} obs)\n")

    # Step 3 — Initial perimeter
    print("[3/4] Building initial fire perimeter...")
    initial_perimeter = build_initial_perimeter(fire_points)

    # Step 4 — Simulation
    print(f"[4/4] Running {args.steps}-step simulation ({args.dt_minutes} min/step)...")
    start_time = datetime(2025, 1, 8, 0, 0, 0, tzinfo=timezone.utc)
    states = run_simulation(
        initial_perimeter=initial_perimeter,
        wind_speed_ms=speed_ms,
        wind_dir_deg=direction_deg,
        start_time=start_time,
        steps=args.steps,
        dt_minutes=args.dt_minutes,
    )

    for s in states:
        print(f"      step {s.step:02d}  {s.timestamp.strftime('%H:%M UTC')}  {s.area_km2:.2f} km²")

    print("\n[export] Writing static GeoJSON snapshots...")
    paths = export_snapshots(states)
    print(f"         {len(paths)} files written")

    if not args.no_post:
        backend_url = os.environ.get("BACKEND_URL", "http://localhost:8001")
        print(f"\n[POST] Sending {len(states)} hazard updates → {backend_url}")
        post_hazards(states, backend_url)

    print("\n=== Demo complete ===")


if __name__ == "__main__":
    main()
