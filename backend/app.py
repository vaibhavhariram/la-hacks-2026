import math
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from models import (
    RouteRequest, RouteResponse, Waypoint,
    HazardRequest, HazardResponse, AffectedNode,
    FieldReportRequest, FieldReportResponse,
)
from router import G, compute_route
from hazards import hazard_store
from gemma_parser import parse_field_report
from geocoder import geocode_location
from graph import nearest_node

app = FastAPI(title="Eye in the Sky API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _haversine_m(lat1, lng1, lat2, lng2) -> float:
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi, dlambda = math.radians(lat2 - lat1), math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


@app.post("/route", response_model=RouteResponse)
async def route(req: RouteRequest):
    result = compute_route(req.start_lat, req.start_lng, req.end_lat, req.end_lng)
    if not result["success"]:
        return RouteResponse(success=False, waypoints=[], node_path=[], error=result.get("error"))
    waypoints = [Waypoint(lat=w["lat"], lng=w["lng"]) for w in result["waypoints"]]
    return RouteResponse(success=True, waypoints=waypoints, node_path=result["node_path"])


@app.post("/hazard", response_model=HazardResponse)
async def hazard(req: HazardRequest):
    affected = []
    for node_id, data in G.nodes(data=True):
        node_lat, node_lng = data["y"], data["x"]
        dist = _haversine_m(req.lat, req.lng, node_lat, node_lng)
        if dist <= req.radius_m:
            hazard_store.update_hazard(node_id, node_lat, node_lng, req.severity, req.hazard_type)
            penalty = hazard_store.get_fire_penalty_at(node_lat, node_lng)
            affected.append(AffectedNode(node_id=node_id, lat=node_lat, lng=node_lng, new_cost=penalty))
    return HazardResponse(affected_nodes=affected)


@app.post("/field-report", response_model=FieldReportResponse)
async def field_report(req: FieldReportRequest):
    parsed = parse_field_report(req.text)
    if parsed["error"]:
        return FieldReportResponse(success=False, message=f"Gemma failed: {parsed['error']}")

    if not parsed["location_description"] or not parsed["status"]:
        return FieldReportResponse(
            success=False,
            status=parsed["status"],
            message="Could not extract location or status from report",
        )

    coords = geocode_location(parsed["location_description"])
    if coords is None:
        return FieldReportResponse(
            success=False,
            status=parsed["status"],
            message=f"Could not geocode: {parsed['location_description']}",
        )

    lat, lng = coords
    node_id = nearest_node(G, lat, lng)

    if parsed["status"] == "blocked":
        hazard_store.block_node(node_id)
        msg = f"Blocked node {node_id} near {parsed['location_description']}"
    else:
        hazard_store.clear_road(node_id)
        msg = f"Cleared node {node_id} near {parsed['location_description']}"

    return FieldReportResponse(
        success=True,
        extracted_lat=lat,
        extracted_lng=lng,
        status=parsed["status"],
        message=msg,
    )


@app.get("/state")
async def state():
    return hazard_store.get_state_snapshot()
