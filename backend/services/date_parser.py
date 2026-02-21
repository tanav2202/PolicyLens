"""
Parse human-readable due date strings from facts DB into datetime ranges.
Handles formats like "Jan 12, 11:59 pm", "Feb 9, 10, 11", "Mar 16-17-18", "TBA".
"""

import re
from datetime import datetime, time

from dateutil import parser as dateutil_parser
from dateutil.tz import gettz

DEFAULT_TZ = "America/Vancouver"


def _strip_markdown_and_suffixes(s: str) -> str:
    """Remove markdown and common suffixes that break parsing."""
    if not s or not s.strip():
        return ""
    # Remove **...** (bold)
    s = re.sub(r"\*\*[^*]*\*\*", "", s).strip()
    # Remove (extended), (optional), etc.
    s = re.sub(r"\s*\([^)]*\)\s*,?", ", ", s).strip()
    # Remove trailing suffixes like "**excluded from drop lowest grade**"
    s = re.sub(r"\s+\*\*[^*]*\*\*$", "", s).strip()
    s = re.sub(r"\s+No late submissions$", "", s, flags=re.I).strip()
    return s.strip()


def _parse_single_datetime(s: str, year: int, tz: str) -> datetime | None:
    """Parse a single date/time string. Returns datetime or None."""
    s = _strip_markdown_and_suffixes(s)
    if not s or s.upper() == "TBA":
        return None
    try:
        tzinfo = gettz(tz)
        # dateutil.parser.parse handles "Jan 12, 11:59 pm"
        dt = dateutil_parser.parse(s, default=datetime(year, 1, 1))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tzinfo)
        return dt
    except (ValueError, TypeError, Exception):
        return None


def _parse_span_format(s: str, year: int) -> tuple[datetime, datetime] | None:
    """
    Parse formats like "Feb 9, 10, 11" (month, day1, day2, day3) or "Mar 16-17-18".
    Returns (start, end) or None.
    """
    s = _strip_markdown_and_suffixes(s)
    if not s or s.upper() == "TBA":
        return None

    tzinfo = gettz(DEFAULT_TZ)

    # Try "Feb 9, 10, 11" -> month=Feb, days=9,10,11
    match1 = re.match(r"^([A-Za-z]+)\s+(\d+)\s*,\s*(\d+)\s*,\s*(\d+)$", s.strip())
    if match1:
        try:
            month_str, d1, d2, d3 = match1.groups()
            dt_month = dateutil_parser.parse(f"{month_str} 1, {year}")
            start = datetime(year, dt_month.month, int(d1), 0, 0, 0, tzinfo=tzinfo)
            end = datetime(year, dt_month.month, int(d3), 23, 59, 59, tzinfo=tzinfo)
            return (start, end)
        except (ValueError, TypeError):
            pass

    # Try "Mar 16-17-18" -> month=Mar, days=16,17,18
    match2 = re.match(r"^([A-Za-z]+)\s+(\d+)-(\d+)-(\d+)$", s.strip())
    if match2:
        try:
            month_str, d1, d2, d3 = match2.groups()
            dt_month = dateutil_parser.parse(f"{month_str} 1, {year}")
            start = datetime(year, dt_month.month, int(d1), 0, 0, 0, tzinfo=tzinfo)
            end = datetime(year, dt_month.month, int(d3), 23, 59, 59, tzinfo=tzinfo)
            return (start, end)
        except (ValueError, TypeError):
            pass

    # Try "Mar 16-18" (range)
    match3 = re.match(r"^([A-Za-z]+)\s+(\d+)-(\d+)$", s.strip())
    if match3:
        try:
            month_str, d1, d2 = match3.groups()
            dt_month = dateutil_parser.parse(f"{month_str} 1, {year}")
            start = datetime(year, dt_month.month, int(d1), 0, 0, 0, tzinfo=tzinfo)
            end = datetime(year, dt_month.month, int(d2), 23, 59, 59, tzinfo=tzinfo)
            return (start, end)
        except (ValueError, TypeError):
            pass

    return None


def parse_due_date(
    due_date_str: str, year: int, tz: str = DEFAULT_TZ
) -> tuple[datetime, datetime] | None:
    """
    Parse a due date string into (start, end) for ICS.
    - Single datetime (e.g. "Jan 12, 11:59 pm"): start=end at that time (end + 1 min for visibility)
    - Span (e.g. "Feb 9, 10, 11"): start Feb 9 00:00, end Feb 11 23:59
    Returns None for unparseable (e.g. TBA).
    """
    if not due_date_str or not str(due_date_str).strip():
        return None

    s = str(due_date_str).strip()

    # Try span format first (more specific)
    span = _parse_span_format(s, year)
    if span:
        return span

    # Try single datetime
    dt = _parse_single_datetime(s, year, tz)
    if dt:
        # For deadline at 11:59 pm: event from 11:59 to 12:00 (or +1h for visibility)
        from datetime import timedelta

        end = dt + timedelta(minutes=1)
        return (dt, end)

    return None
