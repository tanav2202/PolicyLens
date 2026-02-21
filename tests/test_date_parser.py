"""Unit tests for date_parser."""

from datetime import datetime

import pytest

from backend.services.date_parser import parse_due_date


def test_parse_single_datetime():
    result = parse_due_date("Jan 12, 11:59 pm", 2026)
    assert result is not None
    start, end = result
    assert start.year == 2026
    assert start.month == 1
    assert start.day == 12
    assert start.hour == 23
    assert start.minute == 59
    assert end > start


def test_parse_span_feb_9_10_11():
    result = parse_due_date("Feb 9, 10, 11", 2026)
    assert result is not None
    start, end = result
    assert start.year == 2026
    assert start.month == 2
    assert start.day == 9
    assert start.hour == 0
    assert end.day == 11
    assert end.hour == 23


def test_parse_span_mar_16_17_18():
    result = parse_due_date("Mar 16-17-18", 2026)
    assert result is not None
    start, end = result
    assert start.month == 3
    assert start.day == 16
    assert end.day == 18


def test_parse_tba_returns_none():
    assert parse_due_date("TBA", 2026) is None


def test_parse_with_markdown_suffix():
    result = parse_due_date("Apr 10, 11:59 pm  **No late submissions**", 2026)
    assert result is not None
    start, end = result
    assert start.month == 4
    assert start.day == 10


def test_parse_extended():
    result = parse_due_date("Jan 19 (extended), 11:59 pm", 2026)
    assert result is not None
    start, end = result
    assert start.month == 1
    assert start.day == 19


def test_parse_empty_returns_none():
    assert parse_due_date("", 2026) is None
    assert parse_due_date("   ", 2026) is None


def test_parse_invalid_returns_none():
    assert parse_due_date("sometime next week", 2026) is None
    assert parse_due_date("???", 2026) is None


def test_parse_with_excluded_suffix():
    result = parse_due_date("Mar 02, 11:59 pm  **excluded from drop lowest grade**", 2026)
    assert result is not None
    start, end = result
    assert start.month == 3
    assert start.day == 2
