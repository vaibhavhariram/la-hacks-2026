from __future__ import annotations

import logging
import random
import re
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from db import close_db, connect_db, save_route
from models import (
    FieldReportParsed,
    FieldReportRequest,
    FieldReportResponse,
    HazardRequest,
    HazardResponse,
    HazardState,
    RouteRequest,
    RouteResponse,
    RouteState,
    StateResponse,
)
from services.db_writes import save_field_report, save_hazard_event, utc_now_iso
from services.route_service import (
    NoRouteFoundError,
    RoutingEngineError,
    apply_hazard_update,
    handle_route_request,
)


logger = logging.getLogger(__name__)


class HealthResponse(BaseModel):
    status: str


# ---------------------------------------------------------------------------
# In-memory mock state
# ---------------------------------------------------------------------------


HAZARDS: list[HazardState] = []
ROUTES: list[RouteState] = []
ACTIVE_ROUTE_REQUESTS: dict[str, RouteRequest] = {}


# ---------------------------------------------------------------------------
# Mock helper functions
# ---------------------------------------------------------------------------


def build_mock_path(request: RouteRequest) -> list[list[float]]:
    """
    Build a fake-but-plausible path between two points.

    This is intentionally simple so frontend teams can integrate against a stable
    shape before real routing logic exists.
    """

    path: list[list[float]] = [[request.start_lat, request.start_lng]]
    midpoint_count = random.randint(1, 2)

    lat_delta = request.end_lat - request.start_lat
    lng_delta = request.end_lng - request.start_lng

    for index in range(1, midpoint_count + 1):
        fraction = index / (midpoint_count + 1)
        base_lat = request.start_lat + (lat_delta * fraction)
        base_lng = request.start_lng + (lng_delta * fraction)

        # Add a small offset so the path looks more like a road route than a
        # perfectly straight line.
        lat_offset = random.uniform(-0.0015, 0.0015)
        lng_offset = random.uniform(-0.0015, 0.0015)

        path.append(
            [
                round(base_lat + lat_offset, 6),
                round(base_lng + lng_offset, 6),
            ]
        )

    path.append([request.end_lat, request.end_lng])
    return path


def build_hazard_state(request: HazardRequest) -> HazardState:
    return HazardState(
        type=request.type,
        lat=request.lat,
        lng=request.lng,
        radius_m=request.radius_m,
        severity=request.severity,
        timestamp=utc_now_iso(),
    )


def paths_differ(path_a: list[list[float]], path_b: list[list[float]]) -> bool:
    if len(path_a) != len(path_b):
        return True

    for point_a, point_b in zip(path_a, path_b):
        if len(point_a) != 2 or len(point_b) != 2:
            return True
        if abs(point_a[0] - point_b[0]) > 0.000001:
            return True
        if abs(point_a[1] - point_b[1]) > 0.000001:
            return True

    return False


async def recompute_active_routes(background_tasks: BackgroundTasks) -> int:
    updated_count = 0

    for index, route in enumerate(list(ROUTES)):
        original_request = ACTIVE_ROUTE_REQUESTS.get(route.route_id)
        if original_request is None:
            continue

        route_payload = await handle_route_request(original_request, route_id=route.route_id)
        rerouted = route_payload["rerouted"] or paths_differ(route.path, route_payload["path"])
        updated_route = RouteState(
            route_id=route.route_id,
            unit_id=route.unit_id,
            path=route_payload["path"],
            rerouted=rerouted,
            start=route.start,
            end=route.end,
            cost=route_payload["cost"],
            last_updated=utc_now_iso(),
        )
        ROUTES[index] = updated_route
        updated_count += 1

        background_tasks.add_task(
            save_route,
            {
                "route_id": updated_route.route_id,
                "unit_id": updated_route.unit_id,
                "start": updated_route.start,
                "end": updated_route.end,
                "path": updated_route.path,
                "cost": updated_route.cost,
                "rerouted": updated_route.rerouted,
                "reason": "hazard_recompute",
            },
        )

    return updated_count


def parse_field_report(request: FieldReportRequest) -> FieldReportParsed:
    lowered_text = request.text.lower()

    if any(keyword in lowered_text for keyword in ("block", "closed", "debris", "collapse")):
        status = "blocked"
        confidence = 0.9
    else:
        status = "passable"
        confidence = 0.65

    match = re.search(r"(-?\d{1,3}\.\d+)\s*,\s*(-?\d{1,3}\.\d+)", request.text)
    lat = float(match.group(1)) if match else None
    lng = float(match.group(2)) if match else None

    return FieldReportParsed(
        lat=lat,
        lng=lng,
        status=status,
        confidence=confidence,
    )


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(_: FastAPI):
    await connect_db()
    yield
    await close_db()


app = FastAPI(title="Disaster Routing Mock API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/route", response_model=RouteResponse)
async def create_route(
    request: RouteRequest,
    background_tasks: BackgroundTasks,
) -> RouteResponse:
    try:
        route_payload = await handle_route_request(request)
    except NoRouteFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RoutingEngineError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    route = RouteState(
        route_id=route_payload["route_id"],
        unit_id=request.unit_id,
        path=route_payload["path"],
        rerouted=route_payload["rerouted"],
        start=[request.start_lat, request.start_lng],
        end=[request.end_lat, request.end_lng],
        cost=route_payload["cost"],
        last_updated=utc_now_iso(),
    )
    ROUTES.append(route)
    ACTIVE_ROUTE_REQUESTS[route.route_id] = request

    background_tasks.add_task(
        save_route,
        {
            "route_id": route.route_id,
            "unit_id": request.unit_id,
            "start": [request.start_lat, request.start_lng],
            "end": [request.end_lat, request.end_lng],
            "path": route.path,
            "cost": route_payload["cost"],
            "rerouted": route.rerouted,
            "reason": "initial_route",
        },
    )

    return RouteResponse(
        path=route.path,
        cost=route_payload["cost"],
        rerouted=route.rerouted,
        route_id=route.route_id,
        unit_id=route.unit_id,
    )


@app.post("/hazard", response_model=HazardResponse)
async def create_hazard(
    request: HazardRequest,
    background_tasks: BackgroundTasks,
) -> HazardResponse:
    hazard_state = build_hazard_state(request)
    HAZARDS.append(hazard_state)

    try:
        graph_update = await apply_hazard_update(
            request.lat,
            request.lng,
            request.radius_m,
            request.severity,
            request.type,
        )
        await recompute_active_routes(background_tasks)
    except RoutingEngineError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    background_tasks.add_task(
        save_hazard_event,
        {
            "type": request.type,
            "lat": request.lat,
            "lng": request.lng,
            "radius_m": request.radius_m,
            "severity": request.severity,
            "timestamp": hazard_state.timestamp,
        },
    )

    return HazardResponse(
        affected_nodes=graph_update["affected_nodes"],
        updated_edges=graph_update["updated_edges"],
    )


@app.post("/field-report", response_model=FieldReportResponse)
async def create_field_report(
    request: FieldReportRequest,
    background_tasks: BackgroundTasks,
) -> FieldReportResponse:
    parsed = parse_field_report(request)

    if parsed.status == "blocked" and parsed.lat is not None and parsed.lng is not None:
        hazard_request = HazardRequest(
            type="blocked",
            lat=parsed.lat,
            lng=parsed.lng,
            radius_m=120,
            severity=1.0,
        )
        HAZARDS.append(build_hazard_state(hazard_request))
        try:
            await apply_hazard_update(
                hazard_request.lat,
                hazard_request.lng,
                hazard_request.radius_m,
                hazard_request.severity,
                hazard_request.type,
            )
            await recompute_active_routes(background_tasks)
        except RoutingEngineError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    background_tasks.add_task(
        save_field_report,
        {
            "text": request.text,
            "unit_id": request.unit_id,
            "parsed": parsed.model_dump(mode="json"),
            "received_at": utc_now_iso(),
        },
    )

    return FieldReportResponse(parsed=parsed)


@app.get("/state", response_model=StateResponse)
async def get_state() -> StateResponse:
    return StateResponse(hazards=HAZARDS, routes=ROUTES)


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(status="ok")
