"""Small demo-safe routing engine fallback.

Person A can replace this by setting ROUTING_ENGINE_MODULE or ROUTING_ENGINE_PATH.
The backend service expects compute_route() to return path, cost, and rerouted.
"""
from __future__ import annotations

import math


def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius_m = 6_371_000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return radius_m * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def compute_route(start_lat: float, start_lng: float, end_lat: float, end_lng: float) -> dict:
    """Return a deterministic plausible route for backend/frontend demos."""
    mid_lat = (start_lat + end_lat) / 2
    mid_lng = (start_lng + end_lng) / 2
    offset_lat = 0.001 if end_lng >= start_lng else -0.001
    offset_lng = -0.001 if end_lat >= start_lat else 0.001

    path = [
        [round(start_lat, 6), round(start_lng, 6)],
        [round(mid_lat + offset_lat, 6), round(mid_lng + offset_lng, 6)],
        [round(end_lat, 6), round(end_lng, 6)],
    ]
    cost = _haversine_m(start_lat, start_lng, end_lat, end_lng)

    return {
        "path": path,
        "cost": round(cost, 2),
        "rerouted": False,
    }
