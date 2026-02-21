"""
Facts database: source of truth for course policy answers.
All factual answers come from here - never from the LLM.
"""

import json
from pathlib import Path
from typing import Any, Optional

from backend.config import FACTS_DB_PATH
from backend.models import Citation


def _load_facts() -> dict[str, Any]:
    """Load facts from JSON. Raises if file missing or invalid."""
    if not FACTS_DB_PATH.exists():
        raise FileNotFoundError(f"Facts DB not found: {FACTS_DB_PATH}")
    with open(FACTS_DB_PATH, encoding="utf-8") as f:
        return json.load(f)


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


def lookup_due_date(assessment: Optional[str]) -> tuple[str, list[Citation]]:
    """Look up due date for an assessment. Returns (answer_text, citations)."""
    facts = _load_facts()
    entries = facts.get("due_dates", [])
    citations: list[Citation] = []

    if assessment:
        norm = _normalize_assessment(assessment)
        for e in entries:
            if e.get("assessment", "").lower().replace("-", "_") == norm:
                text = f"{e['assessment']} is due {e['due_date']}. Find it: {e['where_find']}. Submit: {e['where_submit']}."
                if e.get("note"):
                    text += f" Note: {e['note']}."
                citations.append(Citation(text=e["due_date"], quote=e["quote"], source=e["source"]))
                return text, citations

    # No specific match: return all due dates
    parts = []
    for e in entries:
        parts.append(f"{e['assessment']}: {e['due_date']} ({e['where_submit']})")
        citations.append(Citation(text=e["due_date"], quote=e["quote"], source=e["source"]))
    return "Deliverable due dates:\n" + "\n".join(parts), citations


def lookup_instructor(section: Optional[str]) -> tuple[str, list[Citation]]:
    """Look up instructor info. Returns (answer_text, citations)."""
    facts = _load_facts()
    entries = facts.get("instructors", [])
    citations: list[Citation] = []

    if section:
        for e in entries:
            if str(e.get("section", "")) == str(section):
                text = f"Section {e['section']}: {e['instructor']} — {e['when']} at {e['where']}. Contact: {e['contact']}."
                citations.append(Citation(text=e["instructor"], quote=e["quote"], source=e["source"]))
                return text, citations

    parts = []
    for e in entries:
        parts.append(f"Section {e['section']}: {e['instructor']} ({e['when']}, {e['where']})")
        citations.append(Citation(text=e["instructor"], quote=e["quote"], source=e["source"]))
    return "Instructors:\n" + "\n".join(parts), citations


def lookup_coordinator() -> tuple[str, list[Citation]]:
    """Look up course coordinator. Returns (answer_text, citations)."""
    facts = _load_facts()
    entries = facts.get("coordinator", [])
    citations = []
    if not entries:
        return "No coordinator info found.", []
    e = entries[0]
    text = f"Course coordinator: {e['name']} ({e['email']}). Contact for: {e['purpose']}."
    citations.append(Citation(text=e["name"], quote=e["quote"], source=e["source"]))
    return text, citations


def lookup_ta_list() -> tuple[str, list[Citation]]:
    """Look up TA list. Returns (answer_text, citations)."""
    facts = _load_facts()
    entries = facts.get("tas", [])
    citations = []
    names = [e["name"] for e in entries]
    quote = ", ".join(names)
    citations.append(Citation(text="TA list", quote=quote, source="cpsc_330_rules.md"))
    return "TAs: " + ", ".join(names), citations


def lookup_links(link_type: Optional[str]) -> tuple[str, list[Citation]]:
    """Look up links. Returns (answer_text, citations)."""
    facts = _load_facts()
    entries = facts.get("links", [])
    citations = []

    if link_type:
        lt = link_type.lower()
        for e in entries:
            if lt in e.get("name", "").lower() or lt in e.get("url", "").lower():
                text = f"{e['name']}: {e['url']}"
                citations.append(Citation(text=e["name"], quote=e["quote"], source=e["source"]))
                return text, citations

    parts = []
    for e in entries:
        parts.append(f"{e['name']}: {e['url']}")
        citations.append(Citation(text=e["name"], quote=e["quote"], source=e["source"]))
    return "Important links:\n" + "\n".join(parts), citations


def lookup_facts(intent: str, slots: dict) -> tuple[str, list[Citation]]:
    """
    Look up facts by intent and slots. All answers come from DB only.
    Returns (answer_text, citations). Refuses (empty, []) for out_of_scope.
    """
    if intent == "out_of_scope":
        return "", []

    assessment = slots.get("assessment")
    section = slots.get("section")
    link_type = slots.get("link_type")

    if intent == "due_date":
        return lookup_due_date(assessment)
    if intent == "instructor_info":
        return lookup_instructor(section)
    if intent == "coordinator":
        return lookup_coordinator()
    if intent == "ta_list":
        return lookup_ta_list()
    if intent == "links":
        return lookup_links(link_type)
    if intent in ("lecture_schedule", "reference_material"):
        # Point to source doc - we don't have full schedule/reference in DB
        return (
            "See the full lecture schedule and reference material in cpsc_330_rules.md.",
            [Citation(text="cpsc_330_rules.md", quote="Lecture schedule (tentative)", source="cpsc_330_rules.md")],
        )

    return "", []
