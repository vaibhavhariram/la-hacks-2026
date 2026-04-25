"""Tests for gis/firms_pipeline.py."""
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from gis.firms_pipeline import (
    _parse_csv,
    points_to_geojson,
    _geojson_to_points,
    FirePoint,
    EATON_BBOX,
)

SAMPLE_CSV = """\
latitude,longitude,bright_ti4,confidence,acq_date,acq_time,frp
34.18,-118.10,340.5,h,2025-01-08,0132,45.2
34.20,-118.09,335.1,n,2025-01-08,0132,30.1
34.17,-118.12,360.0,h,2025-01-08,0132,80.5
"""


def test_parse_csv_returns_correct_count():
    points = _parse_csv(SAMPLE_CSV)
    assert len(points) == 3


def test_parse_csv_correct_values():
    points = _parse_csv(SAMPLE_CSV)
    assert points[0].lat == pytest.approx(34.18)
    assert points[0].lng == pytest.approx(-118.10)
    assert points[0].confidence == "h"
    assert points[0].frp == pytest.approx(45.2)


def test_parse_csv_empty_returns_empty():
    assert _parse_csv("") == []
    assert _parse_csv("latitude,longitude\n") == []


def test_parse_csv_skips_malformed_rows():
    bad_csv = "latitude,longitude,bright_ti4,confidence,acq_date,acq_time,frp\n34.18,bad,340.5,h,2025-01-08,0132,45.2\n"
    points = _parse_csv(bad_csv)
    assert len(points) == 0


def test_points_to_geojson_structure():
    points = _parse_csv(SAMPLE_CSV)
    gj = points_to_geojson(points)
    assert gj["type"] == "FeatureCollection"
    assert len(gj["features"]) == 3
    f = gj["features"][0]
    assert f["geometry"]["type"] == "Point"
    assert f["geometry"]["coordinates"] == [-118.10, 34.18]


def test_roundtrip_geojson():
    points = _parse_csv(SAMPLE_CSV)
    gj = points_to_geojson(points)
    restored = _geojson_to_points(gj)
    assert len(restored) == len(points)
    assert restored[0].lat == pytest.approx(points[0].lat)
    assert restored[0].lng == pytest.approx(points[0].lng)


def test_eaton_bbox_sanity():
    w, s, e, n = EATON_BBOX
    assert s < n
    assert w < e
    assert 33 < s < 35  # in LA latitude range
    assert -119 < w < -117  # in LA longitude range
