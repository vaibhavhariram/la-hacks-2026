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


async def apply_hazard_update(
    lat: float,
    lng: float,
    radius_m: float,
    severity: float,
    hazard_type: str,
) -> dict[str, int]:
    routing_engine = _load_routing_engine()
    update_fn = getattr(routing_engine, "update_hazard", None)
    if update_fn is None:
        logger.warning("routing engine has no update_hazard(); using fallback impact counts")
        affected_nodes = max(1, round(radius_m / 40))
        updated_edges = max(affected_nodes * 2, round(radius_m / 15))
        return {"affected_nodes": affected_nodes, "updated_edges": updated_edges}

    try:
        result = await run_in_threadpool(update_fn, lat, lng, radius_m, severity, hazard_type)
    except Exception as exc:
        logger.exception("routing_engine.update_hazard failed")
        raise RoutingEngineError("Routing engine hazard update failure.") from exc

    if not isinstance(result, dict):
        affected_nodes = max(1, round(radius_m / 40))
        updated_edges = max(affected_nodes * 2, round(radius_m / 15))
        return {"affected_nodes": affected_nodes, "updated_edges": updated_edges}

    return {
        "affected_nodes": int(result.get("affected_nodes", 0)),
        "updated_edges": int(result.get("updated_edges", 0)),
    }


async def handle_route_request(
    req: RouteRequest,
    *,
    route_id: str | None = None,
    force_rerouted: bool = False,
) -> dict[str, Any]:
    routing_engine = _load_routing_engine()

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

    route_id = route_id or str(uuid4())
    response = {
        "path": path,
        "cost": cost,
        "rerouted": rerouted or force_rerouted,
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
