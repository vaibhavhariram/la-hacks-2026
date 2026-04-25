from __future__ import annotations

import math
import random
import re
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from db import close_db, connect_db
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
from services.db_writes import save_field_report, save_hazard_event, save_route, utc_now_iso


class HealthResponse(BaseModel):
    status: str


# ---------------------------------------------------------------------------
# In-memory mock state
# ---------------------------------------------------------------------------


HAZARDS: list[HazardState] = []
ROUTES: list[RouteState] = []


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


def build_mock_cost(request: RouteRequest, path: list[list[float]]) -> float:
    """
    Produce a stable-looking mock cost derived from request geometry plus a small
    random factor. This is not real routing cost.
    """

    lat_delta = request.end_lat - request.start_lat
    lng_delta = request.end_lng - request.start_lng
    straight_line_distance = math.hypot(lat_delta, lng_delta)
    base_cost = straight_line_distance * 10000
    complexity_bonus = len(path) * random.uniform(8.0, 20.0)
    return round(base_cost + complexity_bonus, 2)


def build_hazard_state(request: HazardRequest) -> HazardState:
    return HazardState(
        type=request.type,
        lat=request.lat,
        lng=request.lng,
        radius_m=request.radius_m,
        severity=request.severity,
        timestamp=utc_now_iso(),
    )


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
    # Mock routing only: generate a realistic-looking path and store it so the
    # frontend can render active routes before the real engine is ready.
    path = build_mock_path(request)
    cost = build_mock_cost(request, path)
    route = RouteState(
        route_id=str(uuid4()),
        unit_id=request.unit_id,
        path=path,
        rerouted=False,
    )
    ROUTES.append(route)

    background_tasks.add_task(
        save_route,
        {
            "route_id": route.route_id,
            "unit_id": request.unit_id,
            "start_lat": request.start_lat,
            "start_lng": request.start_lng,
            "end_lat": request.end_lat,
            "end_lng": request.end_lng,
            "path": route.path,
            "cost": cost,
            "rerouted": route.rerouted,
        },
    )

    return RouteResponse(
        path=route.path,
        cost=cost,
        rerouted=route.rerouted,
        route_id=route.route_id,
    )


@app.post("/hazard", response_model=HazardResponse)
async def create_hazard(
    request: HazardRequest,
    background_tasks: BackgroundTasks,
) -> HazardResponse:
    # Mock hazard application only: keep the hazard in memory and return fake
    # graph-impact counts so the frontend can exercise update flows.
    hazard_state = build_hazard_state(request)
    HAZARDS.append(hazard_state)

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
        affected_nodes=random.randint(5, 50),
        updated_edges=random.randint(10, 120),
    )


@app.post("/field-report", response_model=FieldReportResponse)
async def create_field_report(
    request: FieldReportRequest,
    background_tasks: BackgroundTasks,
) -> FieldReportResponse:
    parsed = parse_field_report(request)

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
