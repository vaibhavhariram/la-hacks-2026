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
    def weight(_u, v, data):
        base = data.get("length", 50.0)

        if hazard_store.is_blocked(v):
            return 999_999

        v_data = G.nodes[v]
        penalty = hazard_store.get_fire_penalty_at(v_data["y"], v_data["x"])

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

    end_data = G.nodes[end_node]
    if hazard_store.is_blocked(end_node) or hazard_store.get_fire_penalty_at(end_data["y"], end_data["x"]) >= 10.0:
        return {"path": [], "cost": 0.0, "rerouted": False}

    try:
        node_path = nx.astar_path(
            G,
            source=start_node,
            target=end_node,
            heuristic=_build_heuristic(end_node),
            weight=_build_weight_fn()
        )
    except nx.NetworkXNoPath:
        return {"path": [], "cost": 0.0, "rerouted": False}

    waypoints = path_to_coords(G, node_path)
    path = [[wp["lat"], wp["lng"]] for wp in waypoints]

    cost = sum(
        _haversine_m(path[i][0], path[i][1], path[i+1][0], path[i+1][1])
        for i in range(len(path) - 1)
    )

    return {"path": path, "cost": round(cost, 2), "rerouted": False}


