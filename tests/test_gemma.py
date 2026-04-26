"""Tests for agents/gemma_parser.py — mocks the Google AI client."""
import pytest
from unittest.mock import MagicMock, patch

from agents.gemma_parser import (
    _extract_json,
    blocked_hazard_payload,
    parse_report,
    parse_report_fallback,
    parse_report_safe,
    FieldReport,
)


def test_extract_json_clean():
    raw = '{"lat": 34.18, "lng": -118.10, "status": "blocked", "confidence": 0.9, "location_description": "Hwy 2"}'
    result = _extract_json(raw)
    assert result["status"] == "blocked"
    assert result["lat"] == pytest.approx(34.18)


def test_extract_json_strips_markdown_fences():
    raw = '```json\n{"lat": null, "lng": null, "status": "unknown", "confidence": 0.4, "location_description": "vague"}\n```'
    result = _extract_json(raw)
    assert result["status"] == "unknown"


def test_extract_json_finds_embedded_json():
    raw = 'Here is the result: {"lat": 34.2, "lng": -118.1, "status": "passable", "confidence": 0.8, "location_description": "Altadena Dr"}'
    result = _extract_json(raw)
    assert result["status"] == "passable"


def test_extract_json_raises_on_garbage():
    with pytest.raises(ValueError):
        _extract_json("no json here at all")


def test_parse_report_blocked():
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = MagicMock(
        text='{"lat": 34.18, "lng": -118.09, "status": "blocked", "confidence": 0.95, "location_description": "Hwy 2 mile marker 14"}'
    )
    report = parse_report("Highway 2 at mile marker 14 is blocked", mock_client)
    assert report.status == "blocked"
    assert report.lat == pytest.approx(34.18)
    assert report.confidence == pytest.approx(0.95)
    assert "Hwy 2" in report.location_description
    assert report.raw_text == "Highway 2 at mile marker 14 is blocked"


def test_parse_report_unknown_location():
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = MagicMock(
        text='{"lat": null, "lng": null, "status": "unknown", "confidence": 0.3, "location_description": "unclear"}'
    )
    report = parse_report("Lots of smoke, not sure about the road", mock_client)
    assert report.lat is None
    assert report.lng is None
    assert report.status == "unknown"


def test_parse_report_passable():
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = MagicMock(
        text='{"lat": 34.21, "lng": -118.13, "status": "passable", "confidence": 0.88, "location_description": "Altadena Drive"}'
    )
    report = parse_report("Altadena Drive is clear, we just drove through", mock_client)
    assert report.status == "passable"
    assert report.confidence == pytest.approx(0.88)


def test_parse_report_fallback_blocked_with_coordinates():
    report = parse_report_fallback("Road blocked by debris near 34.18, -118.10")
    assert report.status == "blocked"
    assert report.lat == pytest.approx(34.18)
    assert report.lng == pytest.approx(-118.10)
    assert report.confidence >= 0.6


def test_parse_report_safe_falls_back_on_model_error():
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = RuntimeError("model unavailable")
    report = parse_report_safe("Route closed at 34.18, -118.10", mock_client)
    assert report.status == "blocked"
    assert report.lat == pytest.approx(34.18)


def test_blocked_hazard_payload_requires_actionable_report():
    report = FieldReport(
        lat=34.18,
        lng=-118.10,
        status="blocked",
        confidence=0.9,
        location_description="coords",
        raw_text="blocked",
    )
    payload = blocked_hazard_payload(report)
    assert payload == {
        "type": "blocked",
        "lat": 34.18,
        "lng": -118.1,
        "radius_m": 100.0,
        "severity": 0.9,
    }


def test_blocked_hazard_payload_ignores_low_confidence():
    report = FieldReport(
        lat=34.18,
        lng=-118.10,
        status="blocked",
        confidence=0.4,
        location_description="coords",
        raw_text="blocked",
    )
    assert blocked_hazard_payload(report) is None
