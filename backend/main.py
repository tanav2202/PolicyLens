"""
Course Policy QA with Citation Enforcement - FastAPI backend.

Model usage policy (Ollama):
- Allowed: intent classification, slot extraction only
- Optional: GuidanceQuery summarization with quotes shown
- NOT allowed: generating factual answers, inventing dates/weights/policies/emails
- Temperature 0, strict JSON validation. If parse fails, refuse.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.models import QueryRequest, QueryResponse
from backend.services.ollama_router import classify_intent
from backend.services.facts_db import lookup_facts

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
            "query": "POST /query",
            "policy": "GET /policy",
        },
    }


@app.get("/health")
def health():
    """Health check."""
    return {"status": "ok"}


@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest) -> QueryResponse:
    """
    Course policy QA: route with Ollama (intent + slots), answer from facts DB only.
    Citations are mandatory for all factual answers.
    """
    question = req.question.strip()
    if not question:
        return QueryResponse(
            answer="",
            citations=[],
            intent="out_of_scope",
            slots_used={},
            refused=True,
            refusal_reason="Empty question.",
        )

    # 1. Intent classification + slot extraction (Ollama only - no factual generation)
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
        return QueryResponse(
            answer="",
            citations=[],
            intent=classification.intent,
            slots_used=classification.slots.model_dump(exclude_none=True),
            refused=True,
            refusal_reason="Low confidence. Question may be out of scope.",
        )

    if classification.intent == "out_of_scope":
        return QueryResponse(
            answer="",
            citations=[],
            intent="out_of_scope",
            slots_used=classification.slots.model_dump(exclude_none=True),
            refused=True,
            refusal_reason="Question is out of scope for course policy.",
        )

    # 2. Lookup facts from DB only (no LLM factual generation)
    slots_dict = classification.slots.model_dump(exclude_none=True)
    answer, citations = lookup_facts(classification.intent, slots_dict)

    if not answer and not citations:
        return QueryResponse(
            answer="",
            citations=[],
            intent=classification.intent,
            slots_used=slots_dict,
            refused=True,
            refusal_reason="No matching facts in database.",
        )

    return QueryResponse(
        answer=answer,
        citations=citations,
        intent=classification.intent,
        slots_used=slots_dict,
        refused=False,
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
