import os
import osmnx as ox
import networkx as nx

GRAPH_PATH = "backend/la_graph.graphml"

# Covers Altadena, Pasadena, Eaton Fire area
# Format: (north, south, east, west)
BBOX = (34.23, 34.12, -118.00, -118.22)

def load_graph() -> nx.MultiDiGraph:
    if os.path.exists(GRAPH_PATH):
        print("[graph] Loading from cache...")
        G = ox.load_graphml(GRAPH_PATH)
    else:
        print("[graph] Downloading from OSM (one-time, ~30s)...")
        G = ox.graph_from_bbox(
            bbox=(BBOX[3], BBOX[1], BBOX[2], BBOX[0]),
            network_type="drive"
        )
        ox.save_graphml(G, filepath=GRAPH_PATH)
        print(f"[graph] Saved to {GRAPH_PATH}")

    return G

def nearest_node(G: nx.MultiDiGraph, lat: float, lng: float) -> int:
    return ox.nearest_nodes(G, X=lng, Y=lat)

def path_to_coords(G: nx.MultiDiGraph, node_list: list[int]) -> list[dict]:
    coords = []
    for node in node_list:
        data = G.nodes[node]
        coords.append({"lat": data["y"], "lng": data["x"]})
    return coords


