"""
Course Policy QA with Citation Enforcement - FastAPI backend.

Model usage policy (Ollama):
- Allowed: intent classification, slot extraction only
- Optional: GuidanceQuery summarization with quotes shown
- NOT allowed: generating factual answers, inventing dates/weights/policies/emails
- Temperature 0, strict JSON validation. If parse fails, refuse.
"""

import asyncio
import json
import random
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from backend.config import discover_courses
from backend.models import QueryRequest, QueryResponse
from backend.services.ollama_router import classify_intent
from backend.services.facts_db import lookup_facts
from backend.services.md_search import get_fallback_message

app = FastAPI(
    title="Course Policy QA",
    description="Policy QA with citation enforcement. LLM routes; facts DB enforces correctness.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    """Root redirects to docs and lists available endpoints."""
    return {
        "message": "Course Policy QA API",
        "docs": "/docs",
        "endpoints": {
            "health": "GET /health",
            "courses": "GET /courses",
            "query": "POST /query",
            "query_stream": "POST /query/stream",
            "policy": "GET /policy",
        },
    }


@app.get("/health")
def health():
    """Health check."""
    return {"status": "ok"}


@app.get("/courses")
def courses():
    """List available courses (from data/*_facts.json)."""
    return {"courses": list(discover_courses().keys())}


# Chitchat responses (LLM detects intent; we pick a safe reply)
_CHITCHAT_RESPONSES: dict[str, list[str]] = {
    "greeting": [
        "Hey! I'm PolicyLens. Ask me about course policies—due dates, instructors, links, and more.",
        "Hi there! How can I help you today? I can answer questions about course policies.",
        "Hello! What would you like to know? I'm here for due dates, instructors, and other course info.",
        "I'm doing well, thanks for asking! How can I help you with course policies today?",
    ],
    "thanks": [
        "You're welcome! Let me know if you need anything else.",
        "Happy to help! Ask anytime.",
        "Anytime! Feel free to ask more questions.",
    ],
    "bye": [
        "Bye! Come back if you have more questions.",
    ],
    "help": [
        "I can answer questions about course policies—due dates, instructors, TAs, coordinator, links, and more. Just ask!",
    ],
}


def _process_query(question: str, course: Optional[str]) -> QueryResponse:
    """
    Run full query pipeline: LLM intent classification (including chitchat), facts lookup, fallback.
    Returns QueryResponse. Used by both /query and /query/stream.
    """
    if not question:
        return QueryResponse(
            answer="",
            citations=[],
            intent="out_of_scope",
            slots_used={},
            refused=True,
            refusal_reason="Empty question.",
        )

    try:
        classification = classify_intent(question)
    except RuntimeError as e:
        return QueryResponse(
            answer="",
            citations=[],
            intent="out_of_scope",
            slots_used={},
            refused=True,
            refusal_reason=f"Router error: {e}",
        )

    if classification is None:
        return QueryResponse(
            answer="",
            citations=[],
            intent="out_of_scope",
            slots_used={},
            refused=True,
            refusal_reason="JSON parse failed. Refusing to guess.",
        )

    if classification.confidence < 0.5:
        fallback = get_fallback_message(course)
        return QueryResponse(
            answer=fallback,
            citations=[],
            intent=classification.intent,
            slots_used=classification.slots.model_dump(exclude_none=True),
            refused=False,
        )

    if classification.intent == "out_of_scope":
        fallback = get_fallback_message(course)
        return QueryResponse(
            answer=fallback,
            citations=[],
            intent="out_of_scope",
            slots_used=classification.slots.model_dump(exclude_none=True),
            refused=False,
        )

    # Chitchat intents: LLM detected greeting/thanks/bye/help; respond with fixed safe reply
    if classification.intent in _CHITCHAT_RESPONSES:
        choices = _CHITCHAT_RESPONSES[classification.intent]
        return QueryResponse(
            answer=random.choice(choices),
            citations=[],
            intent=classification.intent,
            slots_used=classification.slots.model_dump(exclude_none=True),
            refused=False,
        )

    slots_dict = classification.slots.model_dump(exclude_none=True)
    try:
        answer, citations = lookup_facts(classification.intent, slots_dict, course=course)
    except FileNotFoundError as e:
        return QueryResponse(
            answer="",
            citations=[],
            intent=classification.intent,
            slots_used=slots_dict,
            refused=True,
            refusal_reason=f"Course data not yet available. {e}",
        )

    if not answer and not citations:
        fallback = get_fallback_message(course)
        return QueryResponse(
            answer=fallback,
            citations=[],
            intent=classification.intent,
            slots_used=slots_dict,
            refused=False,
        )

    return QueryResponse(
        answer=answer,
        citations=citations,
        intent=classification.intent,
        slots_used=slots_dict,
        refused=False,
    )


@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest) -> QueryResponse:
    """
    Course policy QA: route with Ollama (intent + slots), answer from facts DB only.
    Citations are mandatory for all factual answers.
    """
    question = req.question.strip()
    course = req.course.strip() if req.course else None
    return _process_query(question, course)


def _stream_words(text: str, delay_seconds: float = 0.12):
    """Yield words from text one at a time with optional delay for readability."""
    words = text.split()
    for i, w in enumerate(words):
        chunk = w + (" " if i < len(words) - 1 else "")
        yield chunk


async def _stream_query_sse(question: str, course: Optional[str], word_delay: float = 0.12):
    """
    Async generator: run query then stream SSE events.
    Events: chunk (word), citations, done.
    """
    # Run blocking query in thread so we don't block the event loop
    loop = asyncio.get_event_loop()
    resp = await loop.run_in_executor(None, _process_query, question, course)

    text_to_stream = resp.refusal_reason if resp.refused else resp.answer
    if not text_to_stream:
        text_to_stream = "No answer available."

    for word in _stream_words(text_to_stream):
        event = json.dumps({"type": "chunk", "content": word})
        yield f"data: {event}\n\n"
        await asyncio.sleep(word_delay)

    citations_payload = [c.model_dump() for c in resp.citations]
    yield f"data: {json.dumps({'type': 'citations', 'citations': citations_payload})}\n\n"

    done_payload = {
        "type": "done",
        "refused": resp.refused,
        "intent": resp.intent,
        "slots_used": resp.slots_used,
    }
    yield f"data: {json.dumps(done_payload)}\n\n"


@app.post("/query/stream")
async def query_stream(req: QueryRequest):
    """
    Same as POST /query but streams the answer word-by-word as Server-Sent Events.
    Event types: chunk (content), citations (citations[]), done (refused, intent, slots_used).
    """
    question = req.question.strip()
    course = req.course.strip() if req.course else None
    return StreamingResponse(
        _stream_query_sse(question, course),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/policy")
def policy():
    """Return the model usage policy (for transparency)."""
    return {
        "ollama_usage": {
            "allowed": [
                "intent classification",
                "slot extraction",
                "optional GuidanceQuery summarization with quotes shown",
            ],
            "not_allowed": [
                "generating factual answers directly",
                "inventing dates, weights, policies, emails",
            ],
            "temperature": 0,
            "json_validation": "strict - if parse fails, refuse",
        },
        "architecture": "Local LLM is router; facts database and validator enforce correctness.",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
