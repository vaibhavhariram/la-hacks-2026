from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel

from db import get_db


logger = logging.getLogger(__name__)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def mongo_document(data: dict[str, Any] | BaseModel) -> dict[str, Any]:
    if isinstance(data, BaseModel):
        document = data.model_dump(mode="json")
    else:
        document = dict(data)

    document["created_at"] = utc_now_iso()
    return document


def stringify_mongo_id(document: dict[str, Any]) -> dict[str, Any]:
    mongo_id = document.get("_id")
    if mongo_id is not None:
        document["_id"] = str(mongo_id)
    return document


async def _safe_insert(collection_name: str, data: dict[str, Any] | BaseModel) -> None:
    db = get_db()
    if db is None:
        logger.warning("Skipping MongoDB write to '%s' because the database is unavailable.", collection_name)
        return

    try:
        await db[collection_name].insert_one(mongo_document(data))
    except Exception:
        logger.exception("MongoDB write failed for collection '%s'.", collection_name)


async def save_session(session_data: dict[str, Any] | BaseModel) -> None:
    await _safe_insert("sessions", session_data)


async def save_route(route_data: dict[str, Any] | BaseModel) -> None:
    await _safe_insert("routes", route_data)


async def save_hazard_event(hazard_data: dict[str, Any] | BaseModel) -> None:
    await _safe_insert("hazard_events", hazard_data)


async def save_field_report(report_data: dict[str, Any] | BaseModel) -> None:
    await _safe_insert("field_reports", report_data)
