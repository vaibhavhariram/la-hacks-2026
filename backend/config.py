from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parent / ".env")


@dataclass(frozen=True)
class Settings:
    mongo_uri: str = (os.getenv("MONGO_URI") or os.getenv("MONGODB_URI") or "").strip()
    db_name: str = os.getenv("DB_NAME", "la_hacks_2026").strip() or "la_hacks_2026"
    routing_engine_module: str = os.getenv("ROUTING_ENGINE_MODULE", "routing_engine").strip() or "routing_engine"
    routing_engine_path: str = (
        os.getenv(
            "ROUTING_ENGINE_PATH",
            str(Path(__file__).resolve().parent.parent / "routing-engine" / "routing_engine.py"),
        ).strip()
    )


settings = Settings()
