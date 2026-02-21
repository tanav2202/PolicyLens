"""
Test cases for Course Policy QA API.
Run: pytest backend/tests/ -v
"""

import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


# --- Conversational / Greetings (LLM classifies intent; requires Ollama) ---

@pytest.mark.parametrize("input_text", [
    "hello", "hi", "hey", "howdy", "hi there", "good morning",
    "how are you", "what's up", "thanks", "thank you", "bye", "help",
])
def test_conversational_responses(input_text: str):
    """Chitchat gets non-refused responses (LLM intent: greeting/thanks/bye/help)."""
    resp = client.post("/query", json={"question": input_text})
    assert resp.status_code == 200
    data = resp.json()
    assert data["refused"] is False
    assert len(data["answer"]) > 0


# --- Health & Endpoints ---

def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_courses():
    resp = client.get("/courses")
    assert resp.status_code == 200
    data = resp.json()
    assert "courses" in data
    assert isinstance(data["courses"], list)


def test_root():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "docs" in resp.json()


# --- Policy QA (requires Ollama for full flow; these test structure) ---

def test_query_empty():
    resp = client.post("/query", json={"question": ""})
    assert resp.status_code == 422  # validation error


def test_query_structure():
    """Query returns expected structure (answer may vary)."""
    resp = client.post("/query", json={"question": "hello", "course": "CPSC 330"})
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert "citations" in data
    assert "intent" in data
    assert "refused" in data
    assert "slots_used" in data


def test_query_with_course():
    """Query with course param."""
    resp = client.post("/query", json={"question": "hi", "course": "CPSC 330"})
    assert resp.status_code == 200
    assert resp.json()["refused"] is False


# --- Facts lookup (bypasses Ollama - test facts_db directly) ---

def test_facts_lookup_due_date():
    """Test facts lookup for due date (no Ollama)."""
    from backend.services.facts_db import lookup_facts
    answer, citations = lookup_facts("due_date", {"assessment": "hw1"}, "CPSC 330")
    assert "Jan 12" in answer or "11:59" in answer
    assert len(citations) >= 1


def test_facts_lookup_coordinator():
    from backend.services.facts_db import lookup_facts
    answer, citations = lookup_facts("coordinator", {}, "CPSC 330")
    assert "Anca" in answer or "coordinator" in answer.lower()
    assert len(citations) >= 1


# --- MD fallback ---

def test_md_search_due_dates():
    """MD fallback finds due dates when JSON has data (CPSC 330 has both)."""
    from backend.services.facts_db import lookup_facts
    # JSON has the data, so we get JSON result
    answer, _ = lookup_facts("due_date", {"assessment": "hw1"}, "CPSC 330")
    assert "hw1" in answer.lower() or "Jan" in answer


def test_md_search_mds_empty_course():
    """MDS has empty JSON - MD fallback would apply if MDS had rules.md."""
    from backend.services.facts_db import lookup_facts
    answer, _ = lookup_facts("due_date", {}, "MDS")
    # MDS has empty facts - returns "not yet" message
    assert "no " in answer.lower() or "not yet" in answer.lower() or "database" in answer.lower()
