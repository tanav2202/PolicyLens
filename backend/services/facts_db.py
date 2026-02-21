"""
Facts database: source of truth for course policy answers.
All factual answers come from here - never from the LLM.

Supports variable JSON structure via _schema:
  - key_map: intent -> data key (e.g. due_date -> "assignments")
  - field_map: intent -> {our_field: their_field} for different record shapes
"""

import json
from pathlib import Path
from typing import Any, Optional

<<<<<<< Updated upstream
from backend.config import DATA_DIR, get_course_facts_map, get_default_course, DEFAULT_KEY_MAP
from backend.models import Citation


def _get_facts_path(course: Optional[str] = None) -> Path:
    """Get path to facts DB file for the given course."""
    m = get_course_facts_map()
    filename = m.get(course) if course else None
    if not filename:
        default = get_default_course()
        filename = m.get(default) if default else None
    if not filename:
        raise FileNotFoundError(f"No facts file for course '{course}'. Add a *_facts.json file to data/.")
    path = DATA_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Facts DB not found: {path}")
    return path


def _load_facts(course: Optional[str] = None) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Load facts and schema for the given course.
    Returns (facts_data, schema). Schema includes key_map and field_map.
    """
    path = _get_facts_path(course)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    schema = data.get("_schema") or {}
    key_map = {**DEFAULT_KEY_MAP, **(schema.get("key_map") or {})}
    field_map = schema.get("field_map") or {}

    # Return data without _schema for lookups
    facts = {k: v for k, v in data.items() if not k.startswith("_")}
    meta = {"key_map": key_map, "field_map": field_map}
    return facts, meta


def _get_entries(facts: dict, intent: str, meta: dict) -> list[dict]:
    """Get entries for intent, using key_map. Apply field_map to normalize record keys."""
    key_map = meta["key_map"]
    field_map = meta["field_map"]
    data_key = key_map.get(intent, intent)
    raw_entries = facts.get(data_key, [])
    if not isinstance(raw_entries, list):
        return []

    fm = field_map.get(intent)
    if not fm:
        return raw_entries

    # Map their field names to our expected names
    normalized = []
    for r in raw_entries:
        if not isinstance(r, dict):
            continue
        n = {}
        for our_key, their_key in fm.items():
            if their_key in r:
                n[our_key] = r[their_key]
        # Copy any unmapped keys
        for k, v in r.items():
            if k not in fm.values() and k not in n:
                n[k] = v
        normalized.append(n)
    return normalized
=======
from backend.config import get_facts_db_path
from backend.models import Citation


def _load_facts(course: Optional[str] = None) -> dict[str, Any]:
    """Load facts from JSON for the given course. Raises FileNotFoundError if missing."""
    path = get_facts_db_path(course)
    if not path.exists():
        raise FileNotFoundError(f"Facts DB not found for course: {course or 'default'}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)
>>>>>>> Stashed changes


def _normalize_assessment(s: Optional[str]) -> Optional[str]:
    """Normalize assessment names for lookup."""
    if not s:
        return None
    s = s.lower().strip().replace(" ", "_").replace("-", "_")
    aliases = {
        "hw1": "hw1", "homework1": "hw1", "homework 1": "hw1",
        "hw2": "hw2", "homework2": "hw2",
        "hw3": "hw3", "hw4": "hw4", "hw5": "hw5", "hw6": "hw6", "hw7": "hw7", "hw8": "hw8", "hw9": "hw9",
        "midterm1": "midterm_1", "midterm 1": "midterm_1", "midterm_2": "midterm_2", "midterm 2": "midterm_2",
        "syllabus_quiz": "syllabus_quiz", "quiz": "syllabus_quiz",
        "final": "final_exam", "final_exam": "final_exam",
    }
    return aliases.get(s, s)


<<<<<<< Updated upstream
def lookup_due_date(assessment: Optional[str], course: Optional[str] = None) -> tuple[str, list[Citation]]:
    """Look up due date for an assessment. Returns (answer_text, citations)."""
    facts, meta = _load_facts(course)
    entries = _get_entries(facts, "due_date", meta)
=======
def lookup_due_date(assessment: Optional[str], facts: dict[str, Any]) -> tuple[str, list[Citation]]:
    """Look up due date for an assessment. Returns (answer_text, citations)."""
    entries = facts.get("due_dates", [])
>>>>>>> Stashed changes
    citations: list[Citation] = []

    if not entries:
        return "No due dates in database for this course yet.", []

    if assessment:
        norm = _normalize_assessment(assessment)
        for e in entries:
            a = e.get("assessment", e.get("item", ""))
            if str(a).lower().replace("-", "_") == norm:
                due = e.get("due_date", e.get("deadline", ""))
                wf = e.get("where_find", e.get("instructions", ""))
                ws = e.get("where_submit", e.get("submit_to", ""))
                text = f"{a} is due {due}. Find it: {wf}. Submit: {ws}."
                if e.get("note"):
                    text += f" Note: {e['note']}."
                citations.append(Citation(text=str(due), quote=e.get("quote", str(due)), source=e.get("source", "")))
                return text, citations

    parts = []
    for e in entries:
        a = e.get("assessment", e.get("item", "?"))
        due = e.get("due_date", e.get("deadline", "?"))
        ws = e.get("where_submit", e.get("submit_to", "?"))
        parts.append(f"{a}: {due} ({ws})")
        citations.append(Citation(text=str(due), quote=e.get("quote", str(due)), source=e.get("source", "")))
    return "Deliverable due dates:\n" + "\n".join(parts), citations


<<<<<<< Updated upstream
def lookup_instructor(section: Optional[str], course: Optional[str] = None) -> tuple[str, list[Citation]]:
    """Look up instructor info. Returns (answer_text, citations)."""
    facts, meta = _load_facts(course)
    entries = _get_entries(facts, "instructor_info", meta)
=======
def lookup_instructor(section: Optional[str], facts: dict[str, Any]) -> tuple[str, list[Citation]]:
    """Look up instructor info. Returns (answer_text, citations)."""
    entries = facts.get("instructors", [])
>>>>>>> Stashed changes
    citations: list[Citation] = []

    if not entries:
        return "No instructor info in database for this course yet.", []

    if section:
        for e in entries:
            if str(e.get("section", "")) == str(section):
                inst = e.get("instructor", e.get("name", ""))
                when = e.get("when", e.get("time", ""))
                where = e.get("where", e.get("location", ""))
                contact = e.get("contact", e.get("email", ""))
                text = f"Section {e.get('section')}: {inst} — {when} at {where}. Contact: {contact}."
                citations.append(Citation(text=inst, quote=e.get("quote", inst), source=e.get("source", "")))
                return text, citations

    parts = []
    for e in entries:
        inst = e.get("instructor", e.get("name", ""))
        when = e.get("when", e.get("time", ""))
        where = e.get("where", e.get("location", ""))
        parts.append(f"Section {e.get('section')}: {inst} ({when}, {where})")
        citations.append(Citation(text=inst, quote=e.get("quote", inst), source=e.get("source", "")))
    return "Instructors:\n" + "\n".join(parts), citations


<<<<<<< Updated upstream
def lookup_coordinator(course: Optional[str] = None) -> tuple[str, list[Citation]]:
    """Look up course coordinator. Returns (answer_text, citations)."""
    facts, meta = _load_facts(course)
    entries = _get_entries(facts, "coordinator", meta)
=======
def lookup_coordinator(facts: dict[str, Any]) -> tuple[str, list[Citation]]:
    """Look up course coordinator. Returns (answer_text, citations)."""
    entries = facts.get("coordinator", [])
>>>>>>> Stashed changes
    citations = []
    if not entries:
        return "No coordinator info in database for this course yet.", []
    e = entries[0]
    name = e.get("name", "")
    email = e.get("email", "")
    purpose = e.get("purpose", "")
    text = f"Course coordinator: {name} ({email}). Contact for: {purpose}."
    citations.append(Citation(text=name, quote=e.get("quote", name), source=e.get("source", "")))
    return text, citations


<<<<<<< Updated upstream
def lookup_ta_list(course: Optional[str] = None) -> tuple[str, list[Citation]]:
    """Look up TA list. Returns (answer_text, citations)."""
    facts, meta = _load_facts(course)
    entries = _get_entries(facts, "ta_list", meta)
    if not entries:
        return "No TA list in database for this course yet.", []
=======
def lookup_ta_list(facts: dict[str, Any]) -> tuple[str, list[Citation]]:
    """Look up TA list. Returns (answer_text, citations)."""
    entries = facts.get("tas", [])
>>>>>>> Stashed changes
    citations = []
    names = [e.get("name", e.get("ta", "")) for e in entries]
    quote = ", ".join(names)
    source = entries[0].get("source", "course_rules.md") if entries else "course_rules.md"
    citations.append(Citation(text="TA list", quote=quote, source=source))
    return "TAs: " + ", ".join(names), citations


<<<<<<< Updated upstream
def lookup_links(link_type: Optional[str], course: Optional[str] = None) -> tuple[str, list[Citation]]:
    """Look up links. Returns (answer_text, citations)."""
    facts, meta = _load_facts(course)
    entries = _get_entries(facts, "links", meta)
    if not entries:
        return "No links in database for this course yet.", []
=======
def lookup_links(link_type: Optional[str], facts: dict[str, Any]) -> tuple[str, list[Citation]]:
    """Look up links. Returns (answer_text, citations)."""
    entries = facts.get("links", [])
>>>>>>> Stashed changes
    citations = []

    if link_type:
        lt = link_type.lower()
        for e in entries:
            name = e.get("name", e.get("title", ""))
            url = e.get("url", e.get("href", ""))
            if lt in str(name).lower() or lt in str(url).lower():
                text = f"{name}: {url}"
                citations.append(Citation(text=name, quote=e.get("quote", name), source=e.get("source", "")))
                return text, citations

    parts = []
    for e in entries:
        name = e.get("name", e.get("title", ""))
        url = e.get("url", e.get("href", ""))
        parts.append(f"{name}: {url}")
        citations.append(Citation(text=name, quote=e.get("quote", name), source=e.get("source", "")))
    return "Important links:\n" + "\n".join(parts), citations


def lookup_facts(intent: str, slots: dict, course: Optional[str] = None) -> tuple[str, list[Citation]]:
    """
<<<<<<< Updated upstream
    Look up facts by intent and slots. Tries JSON first, then MD fallback.
    Returns (answer_text, citations). Refuses (empty, []) for out_of_scope.
=======
    Look up facts by intent and slots for the given course. All answers come from DB only.
    Returns (answer_text, citations). Raises FileNotFoundError if no facts DB for course.
>>>>>>> Stashed changes
    """
    if intent == "out_of_scope":
        return "", []

    facts = _load_facts(course)
    assessment = slots.get("assessment")
    section = slots.get("section")
    link_type = slots.get("link_type")

<<<<<<< Updated upstream
    def _lookup():
        if intent == "due_date":
            return lookup_due_date(assessment, course)
        if intent == "instructor_info":
            return lookup_instructor(section, course)
        if intent == "coordinator":
            return lookup_coordinator(course)
        if intent == "ta_list":
            return lookup_ta_list(course)
        if intent == "links":
            return lookup_links(link_type, course)
        if intent in ("lecture_schedule", "reference_material"):
            source = "course_rules.md"
            return (
                f"See the full lecture schedule and reference material in {source}.",
                [Citation(text=source, quote="Lecture schedule (tentative)", source=source)],
            )
        return "", []
=======
    if intent == "due_date":
        return lookup_due_date(assessment, facts)
    if intent == "instructor_info":
        return lookup_instructor(section, facts)
    if intent == "coordinator":
        return lookup_coordinator(facts)
    if intent == "ta_list":
        return lookup_ta_list(facts)
    if intent == "links":
        return lookup_links(link_type, facts)
    if intent in ("lecture_schedule", "reference_material"):
        # Point to source doc - we don't have full schedule/reference in DB
        return (
            "See the full lecture schedule and reference material in cpsc_330_rules.md.",
            [Citation(text="cpsc_330_rules.md", quote="Lecture schedule (tentative)", source="cpsc_330_rules.md")],
        )
>>>>>>> Stashed changes

    answer, citations = _lookup()

    # MD fallback: if JSON returned empty/not-found, search markdown
    if (not answer or "not yet" in answer.lower() or "no " in answer.lower()[:10]) and intent in (
        "due_date", "instructor_info", "coordinator", "ta_list", "links"
    ):
        from backend.services.md_search import search_md
        md_answer, md_citations, confidence = search_md(intent, slots, course)
        if md_answer and confidence >= 0.8:
            return md_answer, md_citations

    return answer, citations
