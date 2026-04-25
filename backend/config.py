from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parent / ".env")


@dataclass(frozen=True)
class Settings:
    mongo_uri: str = os.getenv("MONGO_URI", "").strip()
    db_name: str = os.getenv("DB_NAME", "la_hacks_2026").strip() or "la_hacks_2026"
    routing_engine_module: str = os.getenv("ROUTING_ENGINE_MODULE", "router").strip() or "router"
    routing_engine_path: str = (
        os.getenv("ROUTING_ENGINE_PATH", str(Path(__file__).resolve().parent / "router.py")).strip()
    )


settings = Settings()
