import math
from threading import Lock


def _haversine_m(lat1, lng1, lat2, lng2) -> float:
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class HazardStore:
    def __init__(self):
        self._fire_nodes = {}
        self._blocked_nodes = {}
        self._lock = Lock()

    def add_fire_node(self, node_id: int, lat: float, lng: float, severity: float):
        with self._lock:
            self._fire_nodes[node_id] = {"lat": lat, "lng": lng, "severity": severity}

    def block_node(self, node_id: int):
        with self._lock:
            self._blocked_nodes[node_id] = True

    def clear_all(self):
        with self._lock:
            self._fire_nodes.clear()
            self._blocked_nodes.clear()

    def update_hazard(self, node_id: int, lat: float, lng: float, severity: float, hazard_type: str) -> None:
        if hazard_type == "blocked":
            self.block_node(node_id)
            return
        self.add_fire_node(node_id=node_id, lat=lat, lng=lng, severity=severity)

    def clear_road(self, node_id: int) -> None:
        with self._lock:
            self._blocked_nodes.pop(node_id, None)

    def get_fire_penalty_at(self, lat: float, lng: float) -> float:
        if not self._fire_nodes:
            return 0.0

        with self._lock:
            fire_snapshot = dict(self._fire_nodes)

        min_dist = float("inf")
        nearest_severity = 0.0

        for fdata in fire_snapshot.values():
            dist = _haversine_m(lat, lng, fdata["lat"], fdata["lng"])
            if dist < min_dist:
                min_dist = dist
                nearest_severity = fdata["severity"]

        if min_dist < 10:
            return 100.0
        elif min_dist < 100:
            return nearest_severity * 50.0
        elif min_dist < 500:
            return nearest_severity * 10.0
        elif min_dist < 1000:
            return nearest_severity * 2.0
        else:
            return 0.0
        
    def is_blocked(self, node_id: int) -> bool:
        return node_id in self._blocked_nodes

    def get_state_snapshot(self) -> dict:
        with self._lock:
            return {
                "fire_nodes": dict(self._fire_nodes),
                "blocked_nodes": list(self._blocked_nodes.keys())
            }


hazard_store = HazardStore()

