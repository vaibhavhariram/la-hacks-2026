from __future__ import annotations

import logging
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from config import settings


logger = logging.getLogger(__name__)

_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


async def connect_db() -> None:
    global _client, _db

    if _client is not None:
        return

    if not settings.mongo_uri:
        logger.warning("MONGO_URI is not set. MongoDB writes are disabled.")
        return

    try:
        _client = AsyncIOMotorClient(settings.mongo_uri)
        await _client.admin.command("ping")
        _db = _client[settings.db_name]
        logger.info("Connected to MongoDB database '%s'.", settings.db_name)
    except Exception:
        logger.exception("Failed to connect to MongoDB. Continuing with DB writes disabled.")
        if _client is not None:
            _client.close()
        _client = None
        _db = None


async def close_db() -> None:
    global _client, _db

    if _client is not None:
        _client.close()
        logger.info("MongoDB connection closed.")

    _client = None
    _db = None


def get_db() -> Optional[AsyncIOMotorDatabase]:
    return _db
