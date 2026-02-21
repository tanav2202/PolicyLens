"""
Markdown fallback: search course rules .md when JSON has no info.
Extracts structured data (tables, lists) and returns with citations.
Only adds to JSON when highly confident (exact table/list match).
"""

import json
import re
from pathlib import Path
from typing import Any, Optional

from backend.config import DATA_DIR, get_course_facts_map, get_default_course
from backend.models import Citation


def _course_to_md_path(course: Optional[str]) -> Optional[Path]:
    """Get path to rules markdown for course. Convention: cpsc_330 -> cpsc_330_rules.md."""
    if not course:
        return None
    m = get_course_facts_map()
    filename = m.get(course)
    if not filename:
        default = get_default_course()
        filename = m.get(default) if default else None
    if not filename:
        return None
    # cpsc_330_facts.json -> cpsc_330_rules.md
    base = filename.replace("_facts.json", "").replace(".json", "")
    path = DATA_DIR / f"{base}_rules.md"
    return path if path.exists() else None


def _strip_md_links(text: str) -> str:
    """Remove markdown links [text](url) -> text."""
    return re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text).strip()


def _parse_md_table(lines: list[str]) -> list[dict[str, str]]:
    """Parse markdown table into list of dicts. First row = headers."""
    if len(lines) < 2:
        return []
    header_line = lines[0]
    sep_line = lines[1]
    if '---' not in sep_line and '|' not in sep_line:
        return []
    headers = [h.strip() for h in header_line.split('|') if h.strip()]
    rows = []
    for line in lines[2:]:
        if not line.strip() or '|' not in line:
            continue
        cells = [c.strip() for c in line.split('|')]
        cells = [c for c in cells if c]
        if len(cells) >= len(headers):
            row = {}
            for i, h in enumerate(headers):
                if i < len(cells):
                    row[h] = _strip_md_links(cells[i])
            rows.append(row)
    return rows


def _extract_tables(content: str) -> list[tuple[str, list[dict]]]:
    """Extract all markdown tables with their section context."""
    tables = []
    lines = content.split('\n')
    i = 0
    section = ""
    while i < len(lines):
        line = lines[i]
        if line.startswith('## '):
            section = line[3:].strip()
        if line.strip().startswith('|') and i + 1 < len(lines):
            table_lines = [line]
            j = i + 1
            while j < len(lines) and lines[j].strip().startswith('|'):
                table_lines.append(lines[j])
                j += 1
            parsed = _parse_md_table(table_lines)
            if parsed and len(parsed[0]) >= 2:
                tables.append((section, parsed))
            i = j
            continue
        i += 1
    return tables


def _extract_list_items(content: str, section_hint: str) -> list[str]:
    """Extract list items (lines starting with - or *) from relevant section."""
    items = []
    in_section = False
    for line in content.split('\n'):
        if section_hint and section_hint.lower() in line.lower():
            in_section = True
        if in_section and (line.strip().startswith('- ') or line.strip().startswith('* ')):
            items.append(_strip_md_links(line.strip()[2:]).strip())
        if in_section and line.startswith('## ') and section_hint not in line:
            break
    return items


def search_md_due_dates(course: Optional[str], assessment: Optional[str]) -> tuple[str, list[Citation], float]:
    """
    Search MD for due dates. Returns (answer, citations, confidence 0-1).
    High confidence = exact match in structured table.
    """
    path = _course_to_md_path(course)
    if not path:
        return "", [], 0.0
    content = path.read_text(encoding="utf-8")
    tables = _extract_tables(content)
    source = path.name
    for section, rows in tables:
        if "due" not in section.lower() and "deliverable" not in section.lower() and "assessment" not in section.lower():
            continue
        # Normalize headers
        for row in rows:
            norm_row = {k.lower().replace(" ", "_"): v for k, v in row.items()}
            if assessment:
                a_key = next((k for k in norm_row if "assessment" in k or "hw" in k or "quiz" in k), None)
                if a_key:
                    val = norm_row.get(a_key, "").lower()
                    if assessment.lower() in val or val.replace(" ", "_") == assessment.lower().replace(" ", "_"):
                        due_key = next((k for k in norm_row if "due" in k or "date" in k), None)
                        due = norm_row.get(due_key, "?")
                        quote = " | ".join(str(v) for v in row.values())
                        return (
                            f"{assessment} is due {due}. (from course rules)",
                            [Citation(text=due, quote=quote, source=source)],
                            0.95,
                        )
        if not assessment:
            parts = []
            citations = []
            for row in rows:
                norm = {k.lower().replace(" ", "_"): v for k, v in row.items()}
                a_key = next((k for k in norm if "assessment" in k or "hw" in k), list(norm.keys())[0] if norm else None)
                due_key = next((k for k in norm if "due" in k or "date" in k), list(norm.keys())[1] if len(norm) > 1 else None)
                if a_key and due_key:
                    parts.append(f"{norm[a_key]}: {norm[due_key]}")
                    citations.append(Citation(text=norm[due_key], quote=" | ".join(row.values()), source=source))
            if parts:
                return "Deliverable due dates:\n" + "\n".join(parts), citations, 0.9
    return "", [], 0.0


def search_md_instructors(course: Optional[str], section: Optional[str]) -> tuple[str, list[Citation], float]:
    """Search MD for instructor info."""
    path = _course_to_md_path(course)
    if not path:
        return "", [], 0.0
    content = path.read_text(encoding="utf-8")
    tables = _extract_tables(content)
    source = path.name
    for sec, rows in tables:
        if "instructor" not in sec.lower() and "teaching" not in sec.lower():
            continue
        for row in rows:
            norm = {k.lower().replace(" ", "_"): v for k, v in row.items()}
            sec_val = norm.get("section", "")
            if section and str(sec_val) != str(section):
                continue
            inst = norm.get("instructor", norm.get("name", ""))
            when = norm.get("when", norm.get("time", ""))
            where = norm.get("where", norm.get("location", ""))
            contact = norm.get("contact", norm.get("email", ""))
            quote = " | ".join(row.values())
            text = f"Section {sec_val}: {inst} — {when} at {where}. Contact: {contact}."
            return text, [Citation(text=inst, quote=quote, source=source)], 0.95
        if not section:
            parts = [f"Section {r.get('Section', r.get('section', '?'))}: {r.get('Instructor', r.get('instructor', '?'))}" for r in rows]
            return "Instructors:\n" + "\n".join(parts), [Citation(text="Instructors table", quote=sec, source=source)], 0.9
    return "", [], 0.0


def search_md_coordinator(course: Optional[str]) -> tuple[str, list[Citation], float]:
    """Search MD for coordinator (look for 'coordinator' section)."""
    path = _course_to_md_path(course)
    if not path:
        return "", [], 0.0
    content = path.read_text(encoding="utf-8")
    in_section = False
    for line in content.split('\n'):
        if "coordinator" in line.lower() and line.startswith('#'):
            in_section = True
            continue
        if in_section and ('@' in line or 'email' in line.lower()):
            # Extract name and email
            match = re.search(r'([A-Za-z\s]+)\s*\(([^)]+@[^)]+)\)', line)
            if match:
                name, email = match.groups()
                return (
                    f"Course coordinator: {name.strip()} ({email}).",
                    [Citation(text=name.strip(), quote=line.strip(), source=path.name)],
                    0.9,
                )
        if in_section and line.startswith('## '):
            break
    return "", [], 0.0


def search_md_tas(course: Optional[str]) -> tuple[str, list[Citation], float]:
    """Search MD for TA list."""
    path = _course_to_md_path(course)
    if not path:
        return "", [], 0.0
    content = path.read_text(encoding="utf-8")
    items = _extract_list_items(content, "TAs")
    if len(items) >= 3:
        names = [i.split('(')[0].strip() for i in items if i and not i.startswith('http')]
        if names:
            quote = ", ".join(names[:5]) + ("..." if len(names) > 5 else "")
            return (
                "TAs: " + ", ".join(names),
                [Citation(text="TA list", quote=quote, source=path.name)],
                0.9,
            )
    return "", [], 0.0


def search_md_links(course: Optional[str], link_type: Optional[str]) -> tuple[str, list[Citation], float]:
    """Search MD for links (markdown link format)."""
    path = _course_to_md_path(course)
    if not path:
        return "", [], 0.0
    content = path.read_text(encoding="utf-8")
    links = re.findall(r'\*\s*\[([^\]]+)\]\(([^)]+)\)', content)
    if not links:
        links = re.findall(r'\*\s*\[([^\]]+)\]\(([^)]+)\)', content)
    if not links:
        links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
    if not links:
        return "", [], 0.0
    source = path.name
    if link_type:
        lt = link_type.lower()
        for name, url in links:
            if lt in name.lower() or lt in url.lower():
                return f"{name}: {url}", [Citation(text=name, quote=f"[{name}]({url})", source=source)], 0.85
    parts = [f"{n}: {u}" for n, u in links[:15]]
    return "Important links:\n" + "\n".join(parts), [Citation(text="Links", quote=parts[0] if parts else "", source=source)], 0.8


def search_md(intent: str, slots: dict, course: Optional[str]) -> tuple[str, list[Citation], float]:
    """
    Fallback: search markdown when JSON has no info.
    Returns (answer, citations, confidence). Confidence >= 0.85 = high, can add to JSON.
    """
    if intent == "due_date":
        return search_md_due_dates(course, slots.get("assessment"))
    if intent == "instructor_info":
        return search_md_instructors(course, slots.get("section"))
    if intent == "coordinator":
        return search_md_coordinator(course)
    if intent == "ta_list":
        return search_md_tas(course)
    if intent == "links":
        return search_md_links(course, slots.get("link_type"))
    return "", [], 0.0


# Confidence threshold for adding to JSON
ADD_TO_JSON_CONFIDENCE = 0.92

# Email pattern: simple, matches typical institutional emails
_EMAIL_PATTERN = re.compile(
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
)


def extract_contact_email(course: Optional[str]) -> Optional[str]:
    """
    Extract a contact email from the course rules markdown for fallback messaging.
    Prefers coordinator/admin/course-related addresses; otherwise returns the first found.
    """
    path = _course_to_md_path(course)
    if not path:
        return None
    try:
        content = path.read_text(encoding="utf-8")
    except Exception:
        return None
    # Find all emails (from plain text and mailto: links)
    emails = _EMAIL_PATTERN.findall(content)
    mailto_emails = re.findall(r"mailto:([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", content, re.I)
    all_emails = list(dict.fromkeys(emails + mailto_emails))  # order-preserving dedup
    if not all_emails:
        return None
    # Prefer coordinator / admin / course-related
    content_lower = content.lower()
    for e in all_emails:
        el = e.lower()
        if "coordinator" in content_lower and "coordinator" in el:
            return e
        if "admin" in el or "-admin@" in el:
            return e
        if "info-" in el or "course" in el:
            return e
    return all_emails[0]


def get_fallback_message(course: Optional[str]) -> str:
    """
    Message when we have no matching facts: ask user to post on Ed/Piazza or email.
    Uses extracted contact email from course rules MD if available.
    """
    email = extract_contact_email(course)
    if email:
        return (
            "I couldn't find that in the course materials. "
            "Please post on Ed Discussion or Piazza, or email at " + email + "."
        )
    return (
        "I couldn't find that in the course materials. "
        "Please post on Ed Discussion or Piazza with your question."
    )


def maybe_add_to_json(intent: str, slots: dict, course: Optional[str], answer: str, citations: list) -> None:
    """
    If highly confident, add extracted fact to JSON for future lookups.
    Only for structured extractions (tables). Disabled by default for safety.
    """
    # Set to True to enable auto-add
    if not getattr(maybe_add_to_json, "_enabled", False):
        return
    # Implementation would parse answer/citations back to structured form and append to JSON
    # Skipping full impl for now - user can enable and we'd need to map back to JSON schema
    pass
