"""Tests for backend/routing_engine.py."""
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from routing_engine import compute_route


def test_fallback_route_contract():
    result = compute_route(34.18, -118.1, 34.2, -118.08)
    assert set(result) == {"path", "cost", "rerouted"}
    assert len(result["path"]) == 3
    assert result["path"][0] == [34.18, -118.1]
    assert result["path"][-1] == [34.2, -118.08]
    assert result["cost"] > 0
    assert result["rerouted"] is False
