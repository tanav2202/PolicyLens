"""
Strict JSON validation for Ollama output.
If parse fails, refuse - never guess or hallucinate.
"""

import json
from typing import Any, Optional

from backend.models import IntentClassification, ExtractedSlots

INTENT_OPTIONS = frozenset({
    "due_date", "instructor_info", "ta_list", "coordinator",
    "links", "lecture_schedule", "reference_material", "out_of_scope",
})


def validate_intent_classification(raw: str) -> Optional[IntentClassification]:
    """
    Strictly validate and parse LLM JSON output.
    Returns None (refuse) if:
    - JSON is invalid
    - Required fields missing
    - Intent not in allowed set
    - Confidence out of range
    """
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None

    if not isinstance(data, dict):
        return None

    intent = data.get("intent")
    if intent not in INTENT_OPTIONS:
        return None

    slots_data = data.get("slots")
    if slots_data is None:
        slots_data = {}
    if not isinstance(slots_data, dict):
        return None

    slots = ExtractedSlots(
        assessment=slots_data.get("assessment") if isinstance(slots_data.get("assessment"), (str, type(None))) else None,
        topic=slots_data.get("topic") if isinstance(slots_data.get("topic"), (str, type(None))) else None,
        role=slots_data.get("role") if isinstance(slots_data.get("role"), (str, type(None))) else None,
        section=slots_data.get("section") if isinstance(slots_data.get("section"), (str, type(None))) else None,
        link_type=slots_data.get("link_type") if isinstance(slots_data.get("link_type"), (str, type(None))) else None,
    )

    confidence = data.get("confidence", 0.5)
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        return None
    if not 0 <= confidence <= 1:
        return None

    return IntentClassification(intent=intent, slots=slots, confidence=confidence)
