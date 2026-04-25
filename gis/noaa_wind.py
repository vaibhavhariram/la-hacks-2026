"""Historical wind data from Iowa Environmental Mesonet ASOS archive. No API key required."""
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import requests

# Burbank airport — closest ASOS station with good coverage near Eaton Fire
BURBANK_STATION = "BUR"
EATON_DATE = "2025-01-08"
CACHE_PATH = Path(__file__).parent / "data" / "wind_jan8.json"

# IEM ASOS archive endpoint
_IEM_URL = "https://mesonet.agron.iastate.edu/api/1/asos.json"


@dataclass
class WindObs:
    timestamp: datetime
    speed_ms: float       # converted from knots
    direction_deg: float  # 0–360 meteorological (wind FROM this direction)
    station: str


def fetch_wind_obs(station: str = BURBANK_STATION, date: str = EATON_DATE) -> list[WindObs]:
    """Fetch hourly wind observations from IEM ASOS archive for a single day."""
    params = {
        "station": station,
        "data": "sknt,drct",  # speed (knots) + direction
        "year1": date[:4], "month1": date[5:7], "day1": date[8:10],
        "year2": date[:4], "month2": date[5:7], "day2": date[8:10],
        "tz": "UTC",
        "format": "json",
        "latlon": "no",
        "direct": "no",
        "report_type": "1",  # METAR observations
    }
    resp = requests.get(_IEM_URL, params=params, timeout=30)
    resp.raise_for_status()
    return _parse_iem_response(resp.json(), station)


def _parse_iem_response(data: dict, station: str) -> list[WindObs]:
    obs = []
    for entry in data.get("data", []):
        try:
            ts = datetime.fromisoformat(entry["valid"].replace(" ", "T")).replace(tzinfo=timezone.utc)
            sknt = float(entry.get("sknt") or 0)
            drct = float(entry.get("drct") or 0)
            obs.append(WindObs(
                timestamp=ts,
                speed_ms=_knots_to_ms(sknt),
                direction_deg=drct,
                station=station,
            ))
        except (KeyError, TypeError, ValueError):
            continue
    return obs


def _knots_to_ms(knots: float) -> float:
    return knots * 0.514444


def dominant_wind(obs: list[WindObs]) -> tuple[float, float]:
    """Return (speed_ms, direction_deg) as mean over all observations."""
    if not obs:
        return (5.0, 270.0)  # westerly default if no data
    speed = sum(o.speed_ms for o in obs) / len(obs)
    direction = sum(o.direction_deg for o in obs) / len(obs)
    return (round(speed, 2), round(direction, 1))


def cache_to_file(obs: list[WindObs], path: Path = CACHE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [
        {"ts": o.timestamp.isoformat(), "speed_ms": o.speed_ms, "direction_deg": o.direction_deg, "station": o.station}
        for o in obs
    ]
    path.write_text(json.dumps(data, indent=2))
    print(f"[wind] cached {len(data)} observations → {path}")


def load_from_cache(path: Path = CACHE_PATH) -> list[WindObs] | None:
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    return [
        WindObs(
            timestamp=datetime.fromisoformat(d["ts"]),
            speed_ms=d["speed_ms"],
            direction_deg=d["direction_deg"],
            station=d["station"],
        )
        for d in data
    ]


def get_wind_obs(station: str = BURBANK_STATION) -> list[WindObs]:
    """Load from cache if present, else fetch from IEM and cache."""
    cached = load_from_cache()
    if cached:
        print(f"[wind] loaded {len(cached)} obs from cache")
        return cached
    obs = fetch_wind_obs(station)
    cache_to_file(obs)
    return obs


if __name__ == "__main__":
    obs = get_wind_obs()
    speed, direction = dominant_wind(obs)
    print(f"Dominant wind on {EATON_DATE}: {speed:.1f} m/s from {direction:.0f}°")
