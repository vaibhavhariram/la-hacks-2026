"""NASA FIRMS data pipeline — fetches Eaton Fire (Jan 8, 2025) from VIIRS archive."""
import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path

import requests

# Eaton Fire area — Altadena/Pasadena, CA
EATON_BBOX = (-118.3, 34.1, -117.9, 34.4)  # W, S, E, N
EATON_DATE = "2025-01-08"
CACHE_PATH = Path(__file__).parent / "data" / "eaton_fire_jan8.json"

# FIRMS VIIRS archive endpoint (requires MAP_KEY)
_FIRMS_BASE = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
_DATASET = "VIIRS_SNPP_SP"  # standard processing (archived, not NRT)


@dataclass
class FirePoint:
    lat: float
    lng: float
    brightness: float   # kelvin
    confidence: str     # "l" / "n" / "h"
    acq_date: str       # "2025-01-08"
    acq_time: str       # "0132" (HHMM UTC)
    frp: float          # fire radiative power (MW)


def fetch_firms_points(map_key: str, bbox: tuple = EATON_BBOX, date: str = EATON_DATE) -> list[FirePoint]:
    """Fetch VIIRS active fire points from FIRMS archive API for a single date."""
    w, s, e, n = bbox
    url = f"{_FIRMS_BASE}/{map_key}/{_DATASET}/{w},{s},{e},{n}/1/{date}"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return _parse_csv(resp.text)


def _parse_csv(csv_text: str) -> list[FirePoint]:
    lines = csv_text.strip().splitlines()
    if len(lines) < 2:
        return []
    headers = [h.strip() for h in lines[0].split(",")]
    points = []
    for line in lines[1:]:
        row = dict(zip(headers, [v.strip() for v in line.split(",")]))
        try:
            points.append(FirePoint(
                lat=float(row["latitude"]),
                lng=float(row["longitude"]),
                brightness=float(row.get("bright_ti4", row.get("brightness", 0))),
                confidence=row.get("confidence", "n"),
                acq_date=row.get("acq_date", ""),
                acq_time=row.get("acq_time", ""),
                frp=float(row.get("frp", 0)),
            ))
        except (KeyError, ValueError):
            continue
    return points


def points_to_geojson(points: list[FirePoint]) -> dict:
    """Convert FirePoint list to GeoJSON FeatureCollection."""
    features = [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [p.lng, p.lat]},
            "properties": {k: v for k, v in asdict(p).items() if k not in ("lat", "lng")},
        }
        for p in points
    ]
    return {"type": "FeatureCollection", "features": features}


def cache_to_file(data: dict, path: Path = CACHE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))
    print(f"[firms] cached {len(data['features'])} points → {path}")


def load_from_cache(path: Path = CACHE_PATH) -> dict | None:
    if path.exists():
        return json.loads(path.read_text())
    return None


def get_fire_points(map_key: str | None = None) -> list[FirePoint]:
    """Load from cache if present, else fetch from FIRMS and cache."""
    cached = load_from_cache()
    if cached:
        print(f"[firms] loaded {len(cached['features'])} points from cache")
        return _geojson_to_points(cached)

    if not map_key:
        map_key = os.environ.get("FIRMS_MAP_KEY")
    if not map_key:
        raise ValueError("FIRMS_MAP_KEY not set and no cache found")

    points = fetch_firms_points(map_key)
    cache_to_file(points_to_geojson(points))
    return points


def _geojson_to_points(geojson: dict) -> list[FirePoint]:
    points = []
    for f in geojson["features"]:
        coords = f["geometry"]["coordinates"]
        props = f["properties"]
        points.append(FirePoint(
            lat=coords[1],
            lng=coords[0],
            brightness=props.get("brightness", 0),
            confidence=props.get("confidence", "n"),
            acq_date=props.get("acq_date", ""),
            acq_time=props.get("acq_time", ""),
            frp=props.get("frp", 0),
        ))
    return points


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    pts = get_fire_points()
    print(f"Fetched {len(pts)} fire points for Eaton Fire {EATON_DATE}")
