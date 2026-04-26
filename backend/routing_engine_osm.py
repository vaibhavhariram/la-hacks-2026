"""
Road-following routing engine for Eye in the Sky (OSMnx + NetworkX A*).

This module matches the routing engine contract expected by
`backend/services/route_service.py`:

    compute_route(start_lat, start_lng, end_lat, end_lng) -> {
        "path": [[lat, lng], ...],
        "cost": <float>,
        "rerouted": <bool>,
    }

`backend/services/route_service.py` injects the current hazard list into the
module-level `HAZARDS` variable before each call.

Notes:
- The first run may download OpenStreetMap data and cache it to
  `backend/la_graph.graphml` (gitignored).
- Hazard application is recomputed per request for simplicity.
"""

from __future__ import annotations

import math
from typing import Any

from hazards import hazard_store
from router import G, compute_route as _compute_route_astar

# Injected by `backend/services/route_service.py` before each compute_route call
HAZARDS: list[dict[str, Any]] = []


def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _apply_hazards() -> None:
    """Project HAZARDS (lat/lng + radius) onto nearby road-graph nodes."""
    hazard_store.clear_all()
    if not HAZARDS:
        return

    # Simple (but O(N_nodes * N_hazards)) projection. Fine for demo-sized graphs.
    for hazard in HAZARDS:
        try:
            hazard_lat = float(hazard["lat"])
            hazard_lng = float(hazard["lng"])
            radius_m = float(hazard.get("radius_m", 0))
            severity = float(hazard.get("severity", 0.8))
            hazard_type = str(hazard.get("type", "fire"))
        except Exception:
            continue

        if radius_m <= 0:
            continue

        for node_id, data in G.nodes(data=True):
            node_lat, node_lng = data["y"], data["x"]
            dist = _haversine_m(hazard_lat, hazard_lng, node_lat, node_lng)
            if dist <= radius_m:
                hazard_store.update_hazard(
                    node_id=node_id,
                    lat=node_lat,
                    lng=node_lng,
                    severity=severity,
                    hazard_type=hazard_type,
                )


def compute_route(start_lat: float, start_lng: float, end_lat: float, end_lng: float) -> dict[str, Any]:
    _apply_hazards()

    straight_dist = _haversine_m(start_lat, start_lng, end_lat, end_lng)
    result = _compute_route_astar(start_lat, start_lng, end_lat, end_lng)

    if not result.get("success"):
        # Match the grid-engine behavior: always return something usable.
        path = [[start_lat, start_lng], [end_lat, end_lng]]
        return {"path": path, "cost": round(straight_dist, 1), "rerouted": False}

    waypoints = result.get("waypoints") or []
    snapped_path: list[list[float]] = [[float(wp["lat"]), float(wp["lng"])] for wp in waypoints]
    if len(snapped_path) < 2:
        path = [[start_lat, start_lng], [end_lat, end_lng]]
        return {"path": path, "cost": round(straight_dist, 1), "rerouted": False}

    # Stitch exact start/end coordinates onto the snapped road-node path so the
    # frontend route polyline attaches to the user's selected points.
    path: list[list[float]] = []
    first = snapped_path[0]
    last = snapped_path[-1]

    start_close = _haversine_m(start_lat, start_lng, first[0], first[1]) <= 15
    end_close = _haversine_m(end_lat, end_lng, last[0], last[1]) <= 15

    path.append([start_lat, start_lng])
    path.extend(snapped_path[1:] if start_close else snapped_path)
    if end_close:
        path[-1] = [end_lat, end_lng]
    else:
        path.append([end_lat, end_lng])

    total_dist = sum(
        _haversine_m(path[i][0], path[i][1], path[i + 1][0], path[i + 1][1])
        for i in range(len(path) - 1)
    )
    rerouted = bool(HAZARDS) and (total_dist > straight_dist * 1.05)

    return {"path": path, "cost": round(total_dist, 1), "rerouted": rerouted}
