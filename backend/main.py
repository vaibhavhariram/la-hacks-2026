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
from services.route_service import NoRouteFoundError, RoutingEngineError, handle_route_request


logger = logging.getLogger(__name__)


class HealthResponse(BaseModel):
    status: str


# ---------------------------------------------------------------------------
# In-memory mock state
# ---------------------------------------------------------------------------


HAZARDS: list[HazardState] = []
ROUTES: list[RouteState] = []


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
    )
    ROUTES.append(route)

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
        },
    )

    return RouteResponse(
        path=route.path,
        cost=route_payload["cost"],
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
