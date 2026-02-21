"""
Ollama router: intent classification and slot extraction ONLY.

Model usage policy:
- Allowed: intent classification, slot extraction
- NOT allowed: generating factual answers, inventing dates/weights/policies/emails
- Temperature 0, strict JSON output
"""

import json
import re
from typing import Optional

from ollama import Client

from backend.config import OLLAMA_MODEL, OLLAMA_TEMPERATURE, OLLAMA_HOST
from backend.models import IntentClassification, ExtractedSlots

# Intent options - LLM must pick one (chitchat + policy + out_of_scope)
INTENT_OPTIONS = [
    "greeting",
    "thanks",
    "bye",
    "help",
    "due_date",
    "instructor_info",
    "ta_list",
    "coordinator",
    "links",
    "lecture_schedule",
    "reference_material",
    "general_policy",
    "out_of_scope",
]

SYSTEM_PROMPT = """You are a router for a course policy QA system. Classify the user's intent and extract slots.

Chitchat (no policy question): greeting, thanks, bye, help.
Policy intents: due_date (when/where assignments; if the question names a specific assignment set slots.assessment to it, e.g. "hw3" for "homework 3" or "when is hw3 due?", "midterm_1" for midterm 1), links (Canvas, Gradescope, etc.), general_policy (program rules: use slots.topic as a short keyword, or null to list all), instructor_info, ta_list, coordinator, lecture_schedule, reference_material.
Use out_of_scope only for questions clearly unrelated to the course or program.

Output EXACTLY this JSON, nothing else:
{"intent": "<one of: greeting, thanks, bye, help, due_date, instructor_info, ta_list, coordinator, links, lecture_schedule, reference_material, general_policy, out_of_scope>", "slots": {"assessment": null or string, "topic": null or short keyword for general_policy, "role": null, "section": null, "link_type": null}, "confidence": 0.0-1.0}"""

USER_PROMPT_TEMPLATE = "Classify this question and extract slots. Output ONLY valid JSON, no markdown:\n\n{question}"


def _extract_json(text: str) -> Optional[str]:
    """Extract JSON block from LLM output. Handles markdown code blocks."""
    text = text.strip()
    # Try raw JSON first
    match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
    if match:
        return match.group(0)
    # Try ```json ... ```
    code_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if code_match:
        return code_match.group(1).strip()
    return None


def classify_intent(question: str) -> Optional[IntentClassification]:
    """
    Use Ollama for intent classification and slot extraction only.
    Returns None if JSON parse fails (refuse to proceed).
    """
    client = Client(host=OLLAMA_HOST)
    user_prompt = USER_PROMPT_TEMPLATE.format(question=question)

    try:
        response = client.chat(
            model=OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            options={"temperature": OLLAMA_TEMPERATURE},
        )
    except Exception as e:
        raise RuntimeError(f"Ollama request failed: {e}") from e

    content = response.get("message", {}).get("content", "")
    if not content:
        return None

    json_str = _extract_json(content)
    if not json_str:
        return None

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError:
        return None

    # Validate and coerce to schema
    intent = data.get("intent", "out_of_scope")
    if intent not in INTENT_OPTIONS:
        intent = "out_of_scope"

    slots_data = data.get("slots", {}) or {}
    slots = ExtractedSlots(
        assessment=slots_data.get("assessment"),
        topic=slots_data.get("topic"),
        role=slots_data.get("role"),
        section=slots_data.get("section"),
        link_type=slots_data.get("link_type"),
    )
    confidence = float(data.get("confidence", 0.5))
    confidence = max(0, min(1, confidence))

    return IntentClassification(intent=intent, slots=slots, confidence=confidence)
