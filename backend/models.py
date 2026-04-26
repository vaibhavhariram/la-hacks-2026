from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel


class RouteRequest(BaseModel):
    start_lat: float
    start_lng: float
    end_lat: float
    end_lng: float
    unit_id: str


class RouteResponse(BaseModel):
    path: list[list[float]]
    cost: float
    rerouted: bool
    route_id: str


class RouteState(BaseModel):
    route_id: str
    unit_id: str
    path: list[list[float]]
    rerouted: bool


class HazardRequest(BaseModel):
    type: Literal["fire", "blocked"]
    lat: float
    lng: float
    radius_m: float
    severity: float


class HazardResponse(BaseModel):
    affected_nodes: int
    updated_edges: int


class HazardState(BaseModel):
    event_id: Optional[str] = None
    type: str
    lat: float
    lng: float
    radius_m: float
    severity: float
    timestamp: str


class FieldReportRequest(BaseModel):
    text: str
    unit_id: Optional[str] = None


class FieldReportParsed(BaseModel):
    lat: Optional[float] = None
    lng: Optional[float] = None
    status: str
    confidence: float


class FieldReportResponse(BaseModel):
    parsed: FieldReportParsed


class StateResponse(BaseModel):
    hazards: list[HazardState]
    routes: list[RouteState]
