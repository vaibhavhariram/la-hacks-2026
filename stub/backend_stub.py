# FALLBACK ONLY — primary integration is backend/main.py
"""Mock Person B backend. Accepts all Person C outbound calls so build never blocks on B.

Run:
    uvicorn stub.backend_stub:app --port 8001 --reload

Swap BACKEND_URL in .env to B's real URL when B is ready — zero code change needed.
"""
import time
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="AEGIS Backend Stub", version="0.1.0")

_hazards: list[dict] = []
_field_reports: list[dict] = []


# ── request models ────────────────────────────────────────────────────────────

class HazardIn(BaseModel):
    type: Literal["fire", "blocked"]
    lat: float
    lng: float
    radius_m: float
    severity: float  # 0.0–1.0


class FieldReportIn(BaseModel):
    text: str
    unit_id: str | None = None


# ── endpoints ─────────────────────────────────────────────────────────────────

@app.post("/hazard", status_code=201)
def post_hazard(h: HazardIn):
    record = h.model_dump()
    record["id"] = len(_hazards)
    record["ts"] = time.time()
    _hazards.append(record)
    print(f"[stub /hazard]  #{record['id']}  {h.type}  lat={h.lat:.4f}  lng={h.lng:.4f}  r={h.radius_m:.0f}m  sev={h.severity:.2f}")
    return {"ok": True, "id": record["id"]}


@app.post("/field-report", status_code=201)
def post_field_report(r: FieldReportIn):
    record = r.model_dump(exclude_none=True)
    record["id"] = len(_field_reports)
    record["ts"] = time.time()
    _field_reports.append(record)
    print(f"[stub /field-report]  #{record['id']}  {record}")
    return {"ok": True, "id": record["id"]}


@app.get("/state")
def get_state():
    features = [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [h["lng"], h["lat"]]},
            "properties": {k: v for k, v in h.items() if k not in ("lat", "lng")},
        }
        for h in _hazards
    ]
    return {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "hazard_count": len(_hazards),
            "field_report_count": len(_field_reports),
        },
    }


@app.get("/field-reports")
def get_field_reports():
    return {"reports": _field_reports}


@app.delete("/state", status_code=204)
def reset_state():
    _hazards.clear()
    _field_reports.clear()


@app.get("/health")
def health():
    return {"status": "ok", "stub": True}
