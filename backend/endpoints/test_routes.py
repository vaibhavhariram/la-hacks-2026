from fastapi import APIRouter

from models import (
    FieldReportParsed,
    FieldReportRequest,
    FieldReportResponse,
    HazardRequest,
    HazardResponse,
    RouteRequest,
    RouteResponse,
    StateResponse,
)


router = APIRouter(tags=["test"])


@router.post("/test", response_model=RouteRequest)
async def test(req: RouteRequest) -> RouteRequest:
    return req


@router.post("/test/route", response_model=RouteResponse)
async def test_route(req: RouteRequest) -> RouteResponse:
    path = [
        [req.start_lat, req.start_lng],
        [(req.start_lat + req.end_lat) / 2, (req.start_lng + req.end_lng) / 2],
        [req.end_lat, req.end_lng],
    ]
    return RouteResponse(
        path=path,
        cost=123.4,
        rerouted=False,
        route_id="test-route-001",
    )


@router.post("/test/hazard", response_model=HazardResponse)
async def test_hazard(req: HazardRequest) -> HazardResponse:
    updated_edges = max(1, int(req.radius_m // 10))
    affected_nodes = max(1, updated_edges // 2)
    return HazardResponse(
        affected_nodes=affected_nodes,
        updated_edges=updated_edges,
    )


@router.post("/test/report", response_model=FieldReportResponse)
async def test_report(req: FieldReportRequest) -> FieldReportResponse:
    lowered_text = req.text.lower()
    status = "blocked" if "block" in lowered_text else "passable"

    return FieldReportResponse(
        parsed=FieldReportParsed(
            lat=None,
            lng=None,
            status=status,
            confidence=0.75,
        )
    )


@router.get("/test/state", response_model=StateResponse)
async def test_state() -> StateResponse:
    return StateResponse(hazards=[], routes=[])
