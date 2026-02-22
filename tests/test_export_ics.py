"""API integration tests for GET /export/ics."""

import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_export_ics_with_course():
    resp = client.get("/export/ics", params={"course": "CPSC 330"})
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "text/calendar" or "text/calendar" in resp.headers.get("content-type", "")
    assert b"VCALENDAR" in resp.content
    assert b"VEVENT" in resp.content


def test_export_ics_with_assessments_filter():
    resp = client.get("/export/ics", params={"course": "CPSC 330", "assessments": "hw1"})
    assert resp.status_code == 200
    assert b"VCALENDAR" in resp.content
    assert resp.content.count(b"BEGIN:VEVENT") >= 1


def test_export_ics_course_not_found():
    resp = client.get("/export/ics", params={"course": "Unknown Course XYZ"})
    assert resp.status_code == 404


def test_export_ics_missing_course():
    resp = client.get("/export/ics")
    assert resp.status_code == 422  # FastAPI validation: missing required param


def test_export_ics_empty_course_may_fail():
    resp = client.get("/export/ics", params={"course": ""})
    assert resp.status_code in (400, 422)


def test_export_ics_mds_empty_dates():
    resp = client.get("/export/ics", params={"course": "MDS"})
    assert resp.status_code == 200
    assert b"VCALENDAR" in resp.content
    # MDS has empty due_dates - valid but minimal ICS
    assert resp.content.count(b"BEGIN:VEVENT") == 0


def test_export_ics_generic_filter_fallback():
    """Generic filter like 'homework' matches no specific entry; fall back to all entries."""
    resp = client.get("/export/ics", params={"course": "CPSC 330", "assessments": "homework"})
    assert resp.status_code == 200
    assert b"VCALENDAR" in resp.content
    assert resp.content.count(b"BEGIN:VEVENT") >= 1
