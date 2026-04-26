from __future__ import annotations

import importlib
import importlib.util
import logging
from typing import Any
from uuid import uuid4
from pathlib import Path

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
        logger.warning(
            "routing engine module '%s' could not be imported; trying file path '%s'",
            settings.routing_engine_module,
            settings.routing_engine_path,
        )

        engine_path = Path(settings.routing_engine_path).expanduser()
        if not engine_path.is_absolute():
            engine_path = (Path(__file__).resolve().parent.parent / engine_path).resolve()

        if not engine_path.exists():
            raise RoutingEngineError(
                f"Routing engine not found. Tried module '{settings.routing_engine_module}' "
                f"and file '{engine_path}'."
            ) from exc

        spec = importlib.util.spec_from_file_location("aegis_route_routing_engine", engine_path)
        if spec is None or spec.loader is None:
            raise RoutingEngineError(f"Routing engine file '{engine_path}' could not be loaded.") from exc

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module


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


async def handle_route_request(req: RouteRequest, hazards: list[dict] | None = None) -> dict[str, Any]:
    routing_engine = _load_routing_engine()

    # Inject current hazard state so the engine can route around fire
    if hasattr(routing_engine, "HAZARDS"):
        routing_engine.HAZARDS = hazards or []

    logger.info(
        "route requested unit_id=%s start=(%s, %s) end=(%s, %s) hazards=%s",
        req.unit_id,
        req.start_lat,
        req.start_lng,
        req.end_lat,
        req.end_lng,
        len(hazards or []),
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
