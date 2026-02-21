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
    "out_of_scope",
]

SYSTEM_PROMPT = """You are a strict router for a course policy QA system. Your ONLY job is to classify the user's intent.

First, detect if the message is conversational chitchat (no policy question):
- greeting: greetings, hellos, "how are you", "what's up", "how's it going", small talk
- thanks: thanks, thank you, appreciation
- bye: goodbye, see you, signing off
- help: user asking what you can do or how to use the system

If it's a real question about course policy (due dates, instructors, TAs, coordinator, links, schedule, materials), use the policy intents and fill slots.

Output EXACTLY this JSON structure, nothing else:
{"intent": "<one of: greeting, thanks, bye, help, due_date, instructor_info, ta_list, coordinator, links, lecture_schedule, reference_material, out_of_scope>", "slots": {"assessment": null or "hw1"|"hw2"|"midterm_1"|"syllabus_quiz"|etc, "topic": null or topic name, "role": null or "instructor"|"ta"|"coordinator", "section": null or "201"|"202"|"203"|"204", "link_type": null or "canvas"|"gradescope"|"ed_discussion"|"github"|etc}, "confidence": 0.0-1.0}

Use out_of_scope only for off-topic or unclear policy questions. Use greeting/thanks/bye/help for chitchat."""

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
