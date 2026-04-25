"""Parse natural language field reports using Gemma 2B via Google AI SDK.

Verified SDK: pip install google-genai → from google import genai (v1.73.1)
Fallback model: gemini-2.0-flash (same API, swap MODEL_ID)
"""
import json
import os
import re
from dataclasses import dataclass

from google import genai

MODEL_ID = "gemma-2-2b-it"
FALLBACK_MODEL_ID = "gemini-2.0-flash"

_PROMPT_TEMPLATE = """\
You are an emergency field report parser for wildfire response. Extract location and road status from the report.

Respond with valid JSON only — no markdown, no explanation:
{{"lat": <float or null>, "lng": <float or null>, "status": "blocked" | "passable" | "unknown", "confidence": <0.0 to 1.0>, "location_description": "<brief string>"}}

Rules:
- lat/lng: decimal degrees for Los Angeles area (lat ~34, lng ~-118). Null if location is too vague to geocode.
- status: "blocked" if road/route is impassable. "passable" if confirmed clear. "unknown" if ambiguous.
- confidence: how certain you are about the extraction (not the field unit's certainty).
- location_description: a brief human-readable location string.

Report: {report}
"""


@dataclass
class FieldReport:
    lat: float | None
    lng: float | None
    status: str           # "blocked" | "passable" | "unknown"
    confidence: float
    location_description: str
    raw_text: str


def make_client(api_key: str | None = None) -> genai.Client:
    key = api_key or os.environ.get("GOOGLE_AI_API_KEY")
    if not key:
        raise ValueError("GOOGLE_AI_API_KEY not set")
    return genai.Client(api_key=key)


def parse_report(text: str, client: genai.Client, model_id: str = MODEL_ID) -> FieldReport:
    """Parse natural language report into structured FieldReport."""
    prompt = _PROMPT_TEMPLATE.format(report=text)
    response = client.models.generate_content(model=model_id, contents=prompt)
    raw_json = _extract_json(response.text)
    return FieldReport(
        lat=raw_json.get("lat"),
        lng=raw_json.get("lng"),
        status=raw_json.get("status", "unknown"),
        confidence=float(raw_json.get("confidence", 0.5)),
        location_description=raw_json.get("location_description", ""),
        raw_text=text,
    )


def _extract_json(text: str) -> dict:
    text = text.strip()
    # strip markdown code fences if model adds them
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # try to find first {...} block
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            return json.loads(m.group())
        raise ValueError(f"Could not parse JSON from model response: {text!r}")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    samples = [
        "Highway 2 near mile marker 14 is completely blocked, trees down across both lanes.",
        "We cleared the debris on Altadena Drive between Lake Ave and Allen Ave, it's passable now.",
        "Unit 7 reporting in, lots of smoke but road seems okay, hard to tell.",
    ]

    client = make_client()
    for text in samples:
        report = parse_report(text, client)
        print(f"\nInput:  {text}")
        print(f"Result: lat={report.lat} lng={report.lng} status={report.status} conf={report.confidence:.2f}")
        print(f"        {report.location_description}")
