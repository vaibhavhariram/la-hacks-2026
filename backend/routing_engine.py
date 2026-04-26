"""
Hazard-aware routing engine for Aegis-Route.

Builds a grid graph over the Altadena area, penalizes edges that pass through
active fire/blocked hazard zones, then finds the lowest-cost path with a simple
Dijkstra implementation — no external dependencies beyond the stdlib.

The module-level HAZARDS list is populated by main.py before each call so the
engine always sees the current fire state.
"""
from __future__ import annotations

import math
import heapq
from typing import Optional

# Injected by main.py before each compute_route call
HAZARDS: list[dict] = []

# Grid covering Altadena and surrounding area
GRID_LAT_MIN = 34.10
GRID_LAT_MAX = 34.28
GRID_LNG_MIN = -118.22
GRID_LNG_MAX = -118.05
GRID_STEPS = 40  # 40x40 = 1600 nodes — fast enough, fine enough for demo

LAT_STEP = (GRID_LAT_MAX - GRID_LAT_MIN) / GRID_STEPS
LNG_STEP = (GRID_LNG_MAX - GRID_LNG_MIN) / GRID_STEPS

# Cost multiplier applied to edges inside a hazard radius
HAZARD_PENALTY = 50.0
# If penalty pushes cost above this threshold, treat as impassable
IMPASSABLE_COST = 1e9


def _lat_lng_to_node(lat: float, lng: float) -> tuple[int, int]:
    row = round((lat - GRID_LAT_MIN) / LAT_STEP)
    col = round((lng - GRID_LNG_MIN) / LNG_STEP)
    row = max(0, min(GRID_STEPS, row))
    col = max(0, min(GRID_STEPS, col))
    return row, col


def _node_to_lat_lng(row: int, col: int) -> tuple[float, float]:
    lat = GRID_LAT_MIN + row * LAT_STEP
    lng = GRID_LNG_MIN + col * LNG_STEP
    return round(lat, 6), round(lng, 6)


def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6_371_000
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def _point_in_any_hazard(lat: float, lng: float) -> bool:
    for h in HAZARDS:
        dist = _haversine_m(lat, lng, h["lat"], h["lng"])
        if dist < h["radius_m"]:
            return True
    return False


def _edge_penalty(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    mid_lat = (lat1 + lat2) / 2
    mid_lng = (lng1 + lng2) / 2
    penalty = 1.0
    for h in HAZARDS:
        # Check both endpoints and midpoint
        for plat, plng in [(lat1, lng1), (mid_lat, mid_lng), (lat2, lng2)]:
            dist = _haversine_m(plat, plng, h["lat"], h["lng"])
            if dist < h["radius_m"]:
                severity = h.get("severity", 0.8)
                penalty = max(penalty, 1.0 + HAZARD_PENALTY * severity)
    return penalty


def _dijkstra(
    start: tuple[int, int],
    end: tuple[int, int],
) -> Optional[list[tuple[int, int]]]:
    dist: dict[tuple[int, int], float] = {start: 0.0}
    prev: dict[tuple[int, int], Optional[tuple[int, int]]] = {start: None}
    heap: list[tuple[float, tuple[int, int]]] = [(0.0, start)]

    while heap:
        cost, node = heapq.heappop(heap)
        if node == end:
            break
        if cost > dist.get(node, math.inf):
            continue

        row, col = node
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]:
            nr, nc = row + dr, col + dc
            if not (0 <= nr <= GRID_STEPS and 0 <= nc <= GRID_STEPS):
                continue

            lat1, lng1 = _node_to_lat_lng(row, col)
            lat2, lng2 = _node_to_lat_lng(nr, nc)
            base_dist = _haversine_m(lat1, lng1, lat2, lng2)
            penalty = _edge_penalty(lat1, lng1, lat2, lng2)
            edge_cost = base_dist * penalty

            new_cost = cost + edge_cost
            neighbor = (nr, nc)
            if new_cost < dist.get(neighbor, math.inf):
                dist[neighbor] = new_cost
                prev[neighbor] = node
                heapq.heappush(heap, (new_cost, neighbor))

    if end not in prev:
        return None

    path: list[tuple[int, int]] = []
    cur: Optional[tuple[int, int]] = end
    while cur is not None:
        path.append(cur)
        cur = prev[cur]
    path.reverse()
    return path


def compute_route(
    start_lat: float,
    start_lng: float,
    end_lat: float,
    end_lng: float,
) -> dict:
    start_node = _lat_lng_to_node(start_lat, start_lng)
    end_node = _lat_lng_to_node(end_lat, end_lng)

    node_path = _dijkstra(start_node, end_node)

    if node_path is None:
        # Fallback: straight line if graph is fully blocked
        path = [[start_lat, start_lng], [end_lat, end_lng]]
        return {"path": path, "cost": 0.0, "rerouted": False}

    # Convert nodes back to lat/lng, force exact start/end
    path: list[list[float]] = []
    for i, (row, col) in enumerate(node_path):
        if i == 0:
            path.append([start_lat, start_lng])
        elif i == len(node_path) - 1:
            path.append([end_lat, end_lng])
        else:
            lat, lng = _node_to_lat_lng(row, col)
            path.append([lat, lng])

    # Compute actual ground distance (ignoring penalties)
    total_dist = sum(
        _haversine_m(path[i][0], path[i][1], path[i + 1][0], path[i + 1][1])
        for i in range(len(path) - 1)
    )

    # Determine if the route avoids hazards (rerouted = true if any node is near a hazard)
    straight_dist = _haversine_m(start_lat, start_lng, end_lat, end_lng)
    rerouted = bool(HAZARDS) and (total_dist > straight_dist * 1.05)

    return {
        "path": path,
        "cost": round(total_dist, 1),
        "rerouted": rerouted,
    }
