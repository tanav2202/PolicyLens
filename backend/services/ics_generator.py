"""
Generate ICS calendar files from due date entries.
"""

import re
from datetime import datetime

from icalendar import Calendar, Event

from backend.services.date_parser import parse_due_date


def _sanitize_assessment(name: str) -> str:
    """Strip markdown and normalize assessment name for calendar."""
    if not name or not isinstance(name, str):
        return "Assessment"
    s = name.strip()
    s = re.sub(r"\*\*([^*]*)\*\*", r"\1", s)
    return s.strip() or "Assessment"


def generate_ics(
    entries: list[dict],
    course_name: str,
    year: int,
    tz: str = "America/Vancouver",
) -> bytes:
    """
    Generate ICS bytes from due date entries.
    Each entry should have: assessment, due_date, where_find, where_submit (optional).
    Skips entries where due_date cannot be parsed (e.g. TBA).
    Returns empty valid ICS if no parseable entries.
    """
    cal = Calendar()
    cal.add("prodid", f"-//PolicyLens//{course_name}//EN")
    cal.add("version", "2.0")

    for e in entries:
        due_str = e.get("due_date", e.get("deadline", ""))
        parsed = parse_due_date(str(due_str), year, tz)
        if parsed is None:
            continue

        start_dt, end_dt = parsed
        assessment = _sanitize_assessment(e.get("assessment", e.get("item", "Assessment")))
        wf = e.get("where_find", e.get("instructions", ""))
        ws = e.get("where_submit", e.get("submit_to", ""))

        desc_parts = []
        if wf:
            desc_parts.append(f"Find: {wf}")
        if ws:
            desc_parts.append(f"Submit: {ws}")
        desc = "\n".join(desc_parts) if desc_parts else f"{course_name} - {assessment}"

        event = Event()
        event.add("summary", f"{course_name} - {assessment}")
        event.add("description", desc)
        event.add("dtstart", start_dt)
        event.add("dtend", end_dt)
        uid_safe = re.sub(r"[^a-zA-Z0-9\-]", "-", f"{assessment}-{start_dt.timestamp()}")
        event.add("uid", f"{uid_safe}@policylens")
        cal.add_component(event)

    return cal.to_ical()
