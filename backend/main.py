from __future__ import annotations

import math
import random
from datetime import datetime
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class RouteRequest(BaseModel):
    start_lat: float = Field(..., description="Starting latitude.")
    start_lng: float = Field(..., description="Starting longitude.")
    end_lat: float = Field(..., description="Destination latitude.")
    end_lng: float = Field(..., description="Destination longitude.")
    unit_id: str | None = Field(default=None, description="Optional responder unit id.")


class RouteResponse(BaseModel):
    path: list[list[float]] = Field(
        ..., description="Mock route as ordered [lat, lng] coordinate pairs."
    )
    cost: float = Field(..., description="Mock route cost for frontend integration.")
    rerouted: bool = Field(..., description="Whether the route was rerouted.")
    route_id: str = Field(..., description="Unique route identifier.")


class HazardRequest(BaseModel):
    lat: float = Field(..., description="Hazard latitude.")
    lng: float = Field(..., description="Hazard longitude.")
    radius_m: float = Field(..., gt=0, description="Hazard impact radius in meters.")
    severity: float = Field(..., description="Hazard severity score.")
    type: Literal["fire", "blocked"] = Field(..., description="Hazard type.")


class HazardResponse(BaseModel):
    affected_nodes: int = Field(..., description="Mock count of affected graph nodes.")
    updated_edges: int = Field(..., description="Mock count of updated graph edges.")


class HazardState(BaseModel):
    type: str
    lat: float
    lng: float
    radius_m: float
    severity: float
    timestamp: str


class RouteState(BaseModel):
    route_id: str
    path: list[list[float]]
    rerouted: bool


class StateResponse(BaseModel):
    hazards: list[HazardState]
    routes: list[RouteState]


class HealthResponse(BaseModel):
    status: Literal["ok"]


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
        timestamp=datetime.utcnow().isoformat(),
    )


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------


app = FastAPI(title="Disaster Routing Mock API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/route", response_model=RouteResponse)
async def create_route(request: RouteRequest) -> RouteResponse:
    # Mock routing only: generate a realistic-looking path and store it so the
    # frontend can render active routes before the real engine is ready.
    path = build_mock_path(request)
    route = RouteState(
        route_id=str(uuid4()),
        path=path,
        rerouted=False,
    )
    ROUTES.append(route)

    return RouteResponse(
        path=route.path,
        cost=build_mock_cost(request, path),
        rerouted=route.rerouted,
        route_id=route.route_id,
    )


@app.post("/hazard", response_model=HazardResponse)
async def create_hazard(request: HazardRequest) -> HazardResponse:
    # Mock hazard application only: keep the hazard in memory and return fake
    # graph-impact counts so the frontend can exercise update flows.
    HAZARDS.append(build_hazard_state(request))

    return HazardResponse(
        affected_nodes=random.randint(5, 50),
        updated_edges=random.randint(10, 120),
    )


@app.get("/state", response_model=StateResponse)
async def get_state() -> StateResponse:
    return StateResponse(hazards=HAZARDS, routes=ROUTES)


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(status="ok")
