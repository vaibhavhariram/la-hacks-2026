"""Tests for backend/routing_engine.py."""
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import routing_engine

from routing_engine import compute_route


def test_fallback_route_contract():
    routing_engine.HAZARDS.clear()
    result = compute_route(34.18, -118.1, 34.2, -118.08)
    assert set(result) == {"path", "cost", "rerouted"}
    assert len(result["path"]) == 3
    assert result["path"][0] == [34.18, -118.1]
    assert result["path"][-1] == [34.2, -118.08]
    assert result["cost"] > 0
    assert result["rerouted"] is False


def test_fallback_route_reroutes_around_hazard():
    routing_engine.HAZARDS.clear()
    baseline = compute_route(34.19, -118.14, 34.19, -118.12)

    impact = routing_engine.update_hazard(
        lat=34.19,
        lng=-118.13,
        radius_m=1000,
        severity=0.9,
        type="fire",
    )
    rerouted = compute_route(34.19, -118.14, 34.19, -118.12)

    assert impact["affected_nodes"] > 0
    assert rerouted["rerouted"] is True
    assert rerouted["path"] != baseline["path"]
    assert len(rerouted["path"]) > len(baseline["path"])
