"""Smoke-test the local AEGIS backend contract.

Default mode is strict and fails if the backend is unavailable. Use --optional
from aggregate demo checks when the backend may not already be running.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from typing import Any


DEFAULT_BACKEND_URL = "http://127.0.0.1:8000"


def _request(method: str, url: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=5) as res:
        body = res.read().decode("utf-8")
        return json.loads(body) if body else {}


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def run_smoke(base_url: str) -> None:
    base_url = base_url.rstrip("/")
    suffix = int(time.time())

    health = _request("GET", f"{base_url}/health")
    _assert(health.get("status") == "ok", f"/health returned {health!r}")

    route = _request(
        "POST",
        f"{base_url}/route",
        {
            "start_lat": 34.18,
            "start_lng": -118.1,
            "end_lat": 34.2,
            "end_lng": -118.08,
            "unit_id": f"smoke-{suffix}",
        },
    )
    _assert(isinstance(route.get("path"), list) and route["path"], "/route returned no path")
    _assert(isinstance(route.get("cost"), (int, float)), "/route returned invalid cost")
    _assert(isinstance(route.get("rerouted"), bool), "/route returned invalid rerouted flag")

    _request(
        "POST",
        f"{base_url}/hazard",
        {"type": "fire", "lat": 34.18, "lng": -118.1, "radius_m": 500, "severity": 0.8},
    )

    report = _request(
        "POST",
        f"{base_url}/field-report",
        {"text": "Road blocked by debris near 34.19, -118.11", "unit_id": f"smoke-{suffix}"},
    )
    parsed = report.get("parsed", {})
    _assert(parsed.get("status") == "blocked", f"/field-report did not parse blocked: {report!r}")

    _request(
        "POST",
        f"{base_url}/hazard",
        {"type": "blocked", "lat": 34.19, "lng": -118.11, "radius_m": 100, "severity": 0.85},
    )

    state = _request("GET", f"{base_url}/state")
    hazards = state.get("hazards", [])
    routes = state.get("routes", [])
    _assert(routes, "/state returned no routes after /route")
    _assert(any(hazard.get("type") == "fire" for hazard in hazards), "/state missing fire hazard")
    _assert(any(hazard.get("type") == "blocked" for hazard in hazards), "/state missing blocked hazard")

    print(f"backend smoke OK: {base_url}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test local backend endpoints")
    parser.add_argument("--backend-url", default=DEFAULT_BACKEND_URL)
    parser.add_argument("--optional", action="store_true", help="skip instead of failing when backend is down")
    args = parser.parse_args()

    try:
        run_smoke(args.backend_url)
    except (ConnectionError, TimeoutError, urllib.error.URLError) as exc:
        if args.optional:
            print(f"backend smoke skipped: {args.backend_url} unavailable ({exc})")
            return 0
        print(f"backend smoke failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"backend smoke failed: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
