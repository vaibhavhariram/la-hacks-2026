"""Small demo-safe routing engine fallback.

Person A can replace this by setting ROUTING_ENGINE_MODULE or ROUTING_ENGINE_PATH.
The backend service expects compute_route() to return path, cost, and rerouted.
"""
from __future__ import annotations

import math
from typing import TypedDict


class Hazard(TypedDict):
    lat: float
    lng: float
    radius_m: float
    severity: float
    type: str


HAZARDS: list[Hazard] = []


def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius_m = 6_371_000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return radius_m * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _project_point(lat: float, lng: float, origin_lat: float, origin_lng: float) -> tuple[float, float]:
    lat_m = 111_320
    lng_m = 111_320 * math.cos(math.radians(origin_lat))
    return ((lng - origin_lng) * lng_m, (lat - origin_lat) * lat_m)


def _unproject_point(x: float, y: float, origin_lat: float, origin_lng: float) -> tuple[float, float]:
    lat_m = 111_320
    lng_m = 111_320 * math.cos(math.radians(origin_lat))
    return (origin_lat + (y / lat_m), origin_lng + (x / lng_m))


def _distance_point_to_segment_m(
    point_lat: float,
    point_lng: float,
    start_lat: float,
    start_lng: float,
    end_lat: float,
    end_lng: float,
) -> float:
    px, py = _project_point(point_lat, point_lng, start_lat, start_lng)
    ax, ay = 0.0, 0.0
    bx, by = _project_point(end_lat, end_lng, start_lat, start_lng)
    dx = bx - ax
    dy = by - ay
    length_sq = (dx * dx) + (dy * dy)
    if length_sq == 0:
        return math.hypot(px - ax, py - ay)

    t = max(0.0, min(1.0, (((px - ax) * dx) + ((py - ay) * dy)) / length_sq))
    closest_x = ax + (t * dx)
    closest_y = ay + (t * dy)
    return math.hypot(px - closest_x, py - closest_y)


def _route_hazard_score(start_lat: float, start_lng: float, end_lat: float, end_lng: float) -> tuple[float, Hazard | None]:
    best_score = 0.0
    best_hazard = None

    for hazard in HAZARDS:
        distance_m = _distance_point_to_segment_m(
            hazard["lat"],
            hazard["lng"],
            start_lat,
            start_lng,
            end_lat,
            end_lng,
        )
        influence_m = max(50.0, hazard["radius_m"])
        if distance_m > influence_m:
            continue

        proximity = 1 - (distance_m / influence_m)
        type_multiplier = 1.5 if hazard["type"] == "blocked" else 1.0
        score = proximity * max(0.0, hazard["severity"]) * type_multiplier
        if score > best_score:
            best_score = score
            best_hazard = hazard

    return best_score, best_hazard


def _detour_point(
    start_lat: float,
    start_lng: float,
    end_lat: float,
    end_lng: float,
    hazard: Hazard,
) -> list[float]:
    sx, sy = _project_point(start_lat, start_lng, start_lat, start_lng)
    ex, ey = _project_point(end_lat, end_lng, start_lat, start_lng)
    hx, hy = _project_point(hazard["lat"], hazard["lng"], start_lat, start_lng)

    dx = ex - sx
    dy = ey - sy
    length = max(1.0, math.hypot(dx, dy))
    normal_x = -dy / length
    normal_y = dx / length

    # Pick the side that keeps the bypass away from the hazard center relative
    # to the start/end midpoint. This makes repeated demo routes deterministic.
    midpoint_x = (sx + ex) / 2
    midpoint_y = (sy + ey) / 2
    side = 1 if ((midpoint_x - hx) * normal_x + (midpoint_y - hy) * normal_y) >= 0 else -1
    clearance_m = max(200.0, hazard["radius_m"] * (1.4 + hazard["severity"]))
    detour_x = hx + (normal_x * clearance_m * side)
    detour_y = hy + (normal_y * clearance_m * side)
    lat, lng = _unproject_point(detour_x, detour_y, start_lat, start_lng)
    return [round(lat, 6), round(lng, 6)]


def update_hazard(lat: float, lng: float, radius_m: float, severity: float, type: str = "fire") -> dict:
    """Apply a hazard to the fallback routing state.

    Real OSM/NetworkX engines can expose the same function name and return
    richer graph counts. This fallback returns deterministic demo-safe counts.
    """
    HAZARDS.append(
        {
            "lat": lat,
            "lng": lng,
            "radius_m": radius_m,
            "severity": severity,
            "type": type,
        }
    )

    affected_nodes = max(1, round(radius_m / 40))
    updated_edges = max(affected_nodes * 2, round(radius_m / 15))
    return {"affected_nodes": affected_nodes, "updated_edges": updated_edges}


def compute_route(start_lat: float, start_lng: float, end_lat: float, end_lng: float) -> dict:
    """Return a deterministic plausible route for backend/frontend demos."""
    mid_lat = (start_lat + end_lat) / 2
    mid_lng = (start_lng + end_lng) / 2
    hazard_score, blocking_hazard = _route_hazard_score(start_lat, start_lng, end_lat, end_lng)

    if blocking_hazard:
        detour = _detour_point(start_lat, start_lng, end_lat, end_lng, blocking_hazard)
        path = [
            [round(start_lat, 6), round(start_lng, 6)],
            [round((start_lat + detour[0]) / 2, 6), round((start_lng + detour[1]) / 2, 6)],
            detour,
            [round((end_lat + detour[0]) / 2, 6), round((end_lng + detour[1]) / 2, 6)],
            [round(end_lat, 6), round(end_lng, 6)],
        ]
    else:
        offset_lat = 0.001 if end_lng >= start_lng else -0.001
        offset_lng = -0.001 if end_lat >= start_lat else 0.001

        path = [
            [round(start_lat, 6), round(start_lng, 6)],
            [round(mid_lat + offset_lat, 6), round(mid_lng + offset_lng, 6)],
            [round(end_lat, 6), round(end_lng, 6)],
        ]

    base_cost = _haversine_m(start_lat, start_lng, end_lat, end_lng)
    cost = base_cost * (1 + (hazard_score * 4))

    return {
        "path": path,
        "cost": round(cost, 2),
        "rerouted": blocking_hazard is not None,
    }
