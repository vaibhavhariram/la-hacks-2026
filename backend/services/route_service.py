from __future__ import annotations

import importlib
import logging
import math
from typing import Any
from uuid import uuid4

from starlette.concurrency import run_in_threadpool

from config import settings
from models import RouteRequest


logger = logging.getLogger(__name__)


class RoutingEngineError(Exception):
    """Raised when the routing engine fails to compute a route."""


class NoRouteFoundError(Exception):
    """Raised when the routing engine cannot find a valid path."""


def _load_routing_engine() -> Any:
    try:
        return importlib.import_module(settings.routing_engine_module)
    except ModuleNotFoundError as exc:
        logger.exception("routing engine module '%s' could not be imported", settings.routing_engine_module)
        raise RoutingEngineError(
            f"Routing engine module '{settings.routing_engine_module}' is not available."
        ) from exc


def _normalize_path(raw_path: Any) -> list[list[float]]:
    if not isinstance(raw_path, list):
        raise RoutingEngineError("Routing engine returned an invalid path.")

    normalized_path: list[list[float]] = []
    for point in raw_path:
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            raise RoutingEngineError("Routing engine returned malformed coordinates.")

        try:
            lat = float(point[0])
            lng = float(point[1])
        except (TypeError, ValueError) as exc:
            raise RoutingEngineError("Routing engine returned non-numeric coordinates.") from exc

        normalized_path.append([lat, lng])

    return normalized_path


def _normalize_waypoints(raw_waypoints: Any) -> list[list[float]]:
    if not isinstance(raw_waypoints, list):
        raise RoutingEngineError("Routing engine returned invalid waypoints.")

    normalized_path: list[list[float]] = []
    for point in raw_waypoints:
        if isinstance(point, dict):
            lat = point.get("lat")
            lng = point.get("lng")
        elif isinstance(point, (list, tuple)) and len(point) == 2:
            lat, lng = point
        else:
            raise RoutingEngineError("Routing engine returned malformed waypoints.")

        try:
            normalized_path.append([float(lat), float(lng)])
        except (TypeError, ValueError) as exc:
            raise RoutingEngineError("Routing engine returned non-numeric waypoints.") from exc

    return normalized_path


def _estimate_cost(path: list[list[float]]) -> float:
    total = 0.0
    for start_point, end_point in zip(path, path[1:]):
        total += math.hypot(end_point[0] - start_point[0], end_point[1] - start_point[1])
    return round(total, 6)


async def handle_route_request(req: RouteRequest) -> dict[str, Any]:
    routing_engine = _load_routing_engine()
    if not hasattr(routing_engine, "compute_route"):
        raise RoutingEngineError("Routing engine module does not expose compute_route.")

    logger.info(
        "route requested unit_id=%s start=(%s, %s) end=(%s, %s)",
        req.unit_id,
        req.start_lat,
        req.start_lng,
        req.end_lat,
        req.end_lng,
    )

    try:
        route_result = await run_in_threadpool(
            routing_engine.compute_route,
            req.start_lat,
            req.start_lng,
            req.end_lat,
            req.end_lng,
        )
    except Exception as exc:
        logger.exception("routing_engine.compute_route failed")
        raise RoutingEngineError("Routing engine failure.") from exc

    if not isinstance(route_result, dict):
        raise RoutingEngineError("Routing engine returned an invalid response.")

    if "path" in route_result:
        path = _normalize_path(route_result.get("path"))
        if not path:
            raise NoRouteFoundError("No route found.")

        try:
            cost = float(route_result["cost"])
            rerouted = bool(route_result["rerouted"])
        except KeyError as exc:
            raise RoutingEngineError("Routing engine response is missing required fields.") from exc
        except (TypeError, ValueError) as exc:
            raise RoutingEngineError("Routing engine response contains invalid field values.") from exc
    else:
        success = bool(route_result.get("success"))
        if not success:
            error_message = str(route_result.get("error") or "Routing engine failure.")
            if "no path" in error_message.lower():
                raise NoRouteFoundError("No route found.")
            raise RoutingEngineError(error_message)

        path = _normalize_waypoints(route_result.get("waypoints"))
        if not path:
            raise NoRouteFoundError("No route found.")

        cost = _estimate_cost(path)
        rerouted = bool(route_result.get("rerouted", False))

    route_id = str(uuid4())
    response = {
        "path": path,
        "cost": cost,
        "rerouted": rerouted,
        "route_id": route_id,
    }

    logger.info(
        "route computed route_id=%s cost=%s rerouted=%s points=%s",
        route_id,
        cost,
        rerouted,
        len(path),
    )

    return response
