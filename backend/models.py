"""Pydantic models for Course Policy QA with citation enforcement."""

from pydantic import BaseModel, Field
from typing import Optional


# --- Intent classification & slot extraction (LLM output schema) ---

class ExtractedSlots(BaseModel):
    """Slots extracted from user query for fact lookup."""
    assessment: Optional[str] = Field(None, description="e.g. hw1, midterm1, syllabus_quiz")
    topic: Optional[str] = Field(None, description="e.g. decision_trees, clustering")
    role: Optional[str] = Field(None, description="e.g. instructor, ta, coordinator")
    section: Optional[str] = Field(None, description="e.g. 201, 202")
    link_type: Optional[str] = Field(None, description="e.g. canvas, gradescope, ed_discussion")


class IntentClassification(BaseModel):
    """Strict JSON schema for Ollama output - intent classification only."""
    intent: str = Field(..., description="One of: due_date, instructor_info, ta_list, coordinator, links, lecture_schedule, reference_material, out_of_scope")
    slots: ExtractedSlots = Field(default_factory=ExtractedSlots)
    confidence: float = Field(ge=0, le=1, default=1.0)


# --- API request/response ---

class QueryRequest(BaseModel):
    """User query for course policy QA."""
    question: str = Field(..., min_length=1, max_length=2000)


class Citation(BaseModel):
    """A cited fact with source quote."""
    text: str = Field(..., description="The factual answer text")
    quote: str = Field(..., description="Exact quote from source document")
    source: str = Field(..., description="Source identifier, e.g. cpsc_330_rules.md")


class QueryResponse(BaseModel):
    """Response with answer and mandatory citations."""
    answer: str = Field(..., description="Answer assembled from facts DB only")
    citations: list[Citation] = Field(default_factory=list)
    intent: str = Field(..., description="Classified intent")
    slots_used: dict = Field(default_factory=dict)
    refused: bool = Field(default=False, description="True if we refused (parse fail, out of scope, no match)")
    refusal_reason: Optional[str] = Field(None)
