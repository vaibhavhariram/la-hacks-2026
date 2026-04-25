import math
import networkx as nx
from graph import load_graph, nearest_node, path_to_coords
from hazards import hazard_store

G = load_graph()

def _haversine_m(lat1, lng1, lat2, lng2) -> float:
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def _build_weight_fn():
    def weight(u, v, data):
        base = data.get("length", 50.0)

        if hazard_store.is_blocked(u) or hazard_store.is_blocked(v):
            return 999_999

        u_data = G.nodes[u]
        penalty = hazard_store.get_fire_penalty_at(u_data["y"], u_data["x"])

        if penalty >= 100.0:
            return 999_999

        return base * (1.0 + penalty)

    return weight

def _build_heuristic(goal_node: int):
    goal_lat = G.nodes[goal_node]["y"]
    goal_lng = G.nodes[goal_node]["x"]

    def heuristic(node_id, _):
        n = G.nodes[node_id]
        return _haversine_m(n["y"], n["x"], goal_lat, goal_lng)

    return heuristic


def compute_route(start_lat, start_lng, end_lat, end_lng):
    start_node = nearest_node(G, start_lat, start_lng)
    end_node = nearest_node(G, end_lat, end_lng)

    try:
        node_path = nx.astar_path(
            G,
            source=start_node,
            target=end_node,
            heuristic=_build_heuristic(end_node),
            weight=_build_weight_fn()
        )
    except nx.NetworkXNoPath:
        return {"success": False, "waypoints": [], "error": "No path found"}

    waypoints = path_to_coords(G, node_path)

    return {
        "success": True,
        "waypoints": waypoints,
        "node_path": node_path
    }


