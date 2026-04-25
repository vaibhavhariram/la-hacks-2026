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


settings = Settings()
