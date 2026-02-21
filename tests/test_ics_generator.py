"""Unit tests for ics_generator."""

import pytest

from backend.services.ics_generator import generate_ics


def test_generate_ics_contains_vcalendar_vevent():
    entries = [
        {
            "assessment": "hw1",
            "due_date": "Jan 12, 11:59 pm",
            "where_find": "GitHub",
            "where_submit": "Gradescope",
        }
    ]
    ics = generate_ics(entries, "CPSC 330", 2026)
    assert b"VCALENDAR" in ics
    assert ics.count(b"BEGIN:VEVENT") >= 1


def test_generate_ics_skips_tba():
    entries = [
        {"assessment": "hw1", "due_date": "Jan 12, 11:59 pm", "where_find": "GitHub", "where_submit": "Gradescope"},
        {"assessment": "Final exam", "due_date": "TBA", "where_find": "PrairieLearn", "where_submit": "PrairieLearn"},
    ]
    ics = generate_ics(entries, "CPSC 330", 2026)
    # Should have only 1 event (hw1), not Final exam
    assert ics.count(b"BEGIN:VEVENT") == 1


def test_generate_ics_sanitizes_assessment_name():
    entries = [
        {
            "assessment": "**Midterm 1**",
            "due_date": "Feb 9, 10, 11",
            "where_find": "PrairieLearn",
            "where_submit": "PrairieLearn",
        }
    ]
    ics = generate_ics(entries, "CPSC 330", 2026)
    assert b"Midterm 1" in ics
    assert b"**" not in ics


def test_generate_ics_empty_entries_valid_calendar():
    ics = generate_ics([], "CPSC 330", 2026)
    assert b"VCALENDAR" in ics
    assert ics.count(b"BEGIN:VEVENT") == 0


def test_generate_ics_all_tba_empty_events():
    entries = [
        {"assessment": "a", "due_date": "TBA", "where_find": "", "where_submit": ""},
        {"assessment": "b", "due_date": "TBA", "where_find": "", "where_submit": ""},
    ]
    ics = generate_ics(entries, "MDS", 2026)
    assert b"VCALENDAR" in ics
    assert ics.count(b"BEGIN:VEVENT") == 0
