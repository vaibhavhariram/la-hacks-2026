import json
import requests
from typing import Any

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gemma2:2b"

_PROMPT_TEMPLATE = """You are a field report parser for emergency response.
Extract the following from the field report below and return ONLY valid JSON with exactly two keys:
- location_description: the specific street name, intersection, or landmark as a string (include city/neighborhood if mentioned), or null if no location is mentioned
- status: either "blocked" or "passable"

Field report: "{report}"
"""


def parse_field_report(report: str) -> dict[str, Any]:
    prompt = _PROMPT_TEMPLATE.format(report=report)

    try:
        resp = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "format": "json", "stream": False},
            timeout=20,
        )
        resp.raise_for_status()
        raw = resp.json().get("response", "")
        data = json.loads(raw)
    except Exception as exc:
        return {"location_description": None, "status": None, "error": str(exc)}

    location = data.get("location_description") or None
    status = str(data.get("status", "")).lower().strip()
    if status not in {"blocked", "passable"}:
        status = None

    return {"location_description": location, "status": status, "error": None}
