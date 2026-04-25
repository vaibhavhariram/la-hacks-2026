from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class RouteRequest(BaseModel):
    start_lat: float = Field(
        ...,
        description="Starting latitude for the route request.",
        examples=[34.0522],
    )
    start_lng: float = Field(
        ...,
        description="Starting longitude for the route request.",
        examples=[-118.2437],
    )
    end_lat: float = Field(
        ...,
        description="Destination latitude for the route request.",
        examples=[34.0689],
    )
    end_lng: float = Field(
        ...,
        description="Destination longitude for the route request.",
        examples=[-118.4452],
    )
    unit_id: Optional[str] = Field(
        default=None,
        description="Optional identifier for the responding unit requesting the route.",
        examples=["engine-12"],
    )


class RouteResponse(BaseModel):
    path: List[List[float]] = Field(
        ...,
        description="Ordered route path represented as latitude/longitude coordinate pairs.",
        examples=[[[34.0522, -118.2437], [34.0601, -118.2504], [34.0689, -118.4452]]],
    )
    cost: float = Field(
        ...,
        description="Computed route traversal cost.",
        examples=[412.8],
    )
    rerouted: bool = Field(
        ...,
        description="Whether the route differs from the default path due to hazards or closures.",
        examples=[True],
    )
    route_id: Optional[str] = Field(
        default=None,
        description="Optional identifier assigned to the generated route.",
        examples=["route-9f3b2c"],
    )


class HazardRequest(BaseModel):
    lat: float = Field(
        ...,
        description="Latitude of the hazard center point.",
        examples=[34.0615],
    )
    lng: float = Field(
        ...,
        description="Longitude of the hazard center point.",
        examples=[-118.3084],
    )
    radius_m: float = Field(
        ...,
        gt=0,
        description="Radius of effect for the hazard in meters.",
        examples=[150.0],
    )
    severity: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Hazard severity normalized between 0.0 and 1.0.",
        examples=[0.85],
    )
    type: Literal["fire", "blocked"] = Field(
        ...,
        description="Hazard category affecting the routing graph.",
        examples=["fire"],
    )


class HazardResponse(BaseModel):
    affected_nodes: int = Field(
        ...,
        description="Number of graph nodes impacted by the hazard update.",
        examples=[24],
    )
    updated_edges: int = Field(
        ...,
        description="Number of graph edges updated after applying the hazard.",
        examples=[61],
    )


class FieldReportRequest(BaseModel):
    text: str = Field(
        ...,
        description="Raw field report text submitted by a responder.",
        examples=["Road blocked by debris near 34.0615, -118.3084."],
    )
    unit_id: Optional[str] = Field(
        default=None,
        description="Optional identifier for the unit submitting the report.",
        examples=["medic-4"],
    )


class FieldReportParsed(BaseModel):
    lat: Optional[float] = Field(
        default=None,
        description="Parsed latitude extracted from the field report, if available.",
        examples=[34.0615],
    )
    lng: Optional[float] = Field(
        default=None,
        description="Parsed longitude extracted from the field report, if available.",
        examples=[-118.3084],
    )
    status: Literal["blocked", "passable"] = Field(
        ...,
        description="Parsed road status inferred from the field report.",
        examples=["blocked"],
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score for the parsed field report interpretation.",
        examples=[0.92],
    )


class FieldReportResponse(BaseModel):
    parsed: FieldReportParsed = Field(
        ...,
        description="Structured interpretation of the submitted field report.",
    )


class HazardState(BaseModel):
    type: str = Field(
        ...,
        description="Hazard type currently stored in global state.",
        examples=["fire"],
    )
    lat: float = Field(
        ...,
        description="Latitude of the hazard center point.",
        examples=[34.0615],
    )
    lng: float = Field(
        ...,
        description="Longitude of the hazard center point.",
        examples=[-118.3084],
    )
    radius_m: float = Field(
        ...,
        description="Radius of effect for the stored hazard in meters.",
        examples=[150.0],
    )
    severity: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Severity of the stored hazard, normalized from 0.0 to 1.0.",
        examples=[0.85],
    )
    timestamp: Optional[str] = Field(
        default=None,
        description="Optional timestamp describing when the hazard was recorded or last updated.",
        examples=["2026-04-25T15:42:00Z"],
    )


class RouteState(BaseModel):
    route_id: str = Field(
        ...,
        description="Unique identifier for a tracked route.",
        examples=["route-9f3b2c"],
    )
    unit_id: Optional[str] = Field(
        default=None,
        description="Optional identifier for the unit assigned to the tracked route.",
        examples=["engine-12"],
    )
    path: List[List[float]] = Field(
        ...,
        description="Current stored route path as ordered latitude/longitude coordinate pairs.",
        examples=[[[34.0522, -118.2437], [34.0601, -118.2504], [34.0689, -118.4452]]],
    )
    rerouted: bool = Field(
        ...,
        description="Whether the stored route has been rerouted from its original plan.",
        examples=[True],
    )


class StateResponse(BaseModel):
    hazards: List[HazardState] = Field(
        ...,
        description="Current collection of active hazards in global state.",
    )
    routes: List[RouteState] = Field(
        ...,
        description="Current collection of tracked routes in global state.",
    )
