from pydantic import BaseModel
from typing import Optional


class RouteRequest(BaseModel):
    start_lat: float
    start_lng: float
    end_lat: float
    end_lng: float
    unit_id: str


class Waypoint(BaseModel):
    lat: float
    lng: float


class RouteResponse(BaseModel):
    success: bool
    waypoints: list[Waypoint]
    node_path: list[int]
    error: Optional[str] = None

class HazardRequest(BaseModel):
    lat: float
    lng: float
    radius_m: float
    severity: float
    hazard_type: str


class AffectedNode(BaseModel):
    node_id: int
    lat: float
    lng: float
    new_cost: float


class HazardResponse(BaseModel):
    affected_nodes: list[AffectedNode]


class FieldReportRequest(BaseModel):
    text: str
    unit_id: Optional[str] = None


class FieldReportResponse(BaseModel):
    success: bool
    extracted_lat: Optional[float] = None
    extracted_lng: Optional[float] = None
    status: Optional[str] = None
    confidence: Optional[float] = None
    message: str
