from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class RouteRequest(BaseModel):
    start_lat: float = Field(..., ge=-90.0, le=90.0)
    start_lng: float = Field(..., ge=-180.0, le=180.0)
    end_lat: float = Field(..., ge=-90.0, le=90.0)
    end_lng: float = Field(..., ge=-180.0, le=180.0)
    unit_id: Optional[str] = None


class RouteResponse(BaseModel):
    path: List[List[float]]
    cost: float
    rerouted: bool
    route_id: str


class HazardRequest(BaseModel):
    lat: float = Field(..., ge=-90.0, le=90.0)
    lng: float = Field(..., ge=-180.0, le=180.0)
    radius_m: float = Field(..., gt=0)
    severity: float = Field(..., ge=0.0, le=1.0)
    type: Literal["fire", "blocked"]
    source: Optional[Literal["simulation", "field_report", "manual"]] = None
    timestamp: Optional[str] = None


class HazardResponse(BaseModel):
    affected_nodes: int
    updated_edges: int


class FieldReportRequest(BaseModel):
    text: str
    unit_id: Optional[str] = None


class FieldReportParsed(BaseModel):
    lat: Optional[float] = None
    lng: Optional[float] = None
    status: Literal["blocked", "passable"]
    confidence: float = Field(..., ge=0.0, le=1.0)


class FieldReportResponse(BaseModel):
    parsed: FieldReportParsed


class HazardState(BaseModel):
    type: str
    lat: float
    lng: float
    radius_m: float
    severity: float
    timestamp: Optional[str] = None


class RouteState(BaseModel):
    route_id: str
    unit_id: Optional[str] = None
    path: List[List[float]]
    rerouted: bool


class StateResponse(BaseModel):
    hazards: List[HazardState]
    routes: List[RouteState]
