# PolicyLens: Extractor, Router, Composer, Validator

## 1. Extractor

**Role:** Get policy content from the web or from Markdown and turn it into structured data the rest of the system can use.

**Functionality:**
- **Web → Markdown:** Fetches a policy URL and converts the page to a single Markdown file (`scripts/extract_policy_md.py` + `backend/services/web_extractor.py`). Output: `data/<slug>_rules.md`.
- **Markdown → JSON:** Parses that Markdown (sections, tables, links) and produces a flexible facts JSON with course scope (due_dates, instructors, coordinator, tas, links) and general scope (general_policies). Script: `scripts/extract_facts_from_md.py`. Output: `data/<slug>_facts.json`.
- **Runtime MD fallback:** When JSON has no answer, `backend/services/md_search.py` extracts tables/lists/links from the course’s `*_rules.md` and returns an answer with citations if confidence is high enough.

**Where:** `scripts/extract_policy_md.py`, `scripts/extract_facts_from_md.py`, `backend/services/web_extractor.py`, `backend/services/md_search.py`.

---

## 2. Router

**Role:** Decide what the user is asking for (intent) and pull out any specific parameters (slots). Does **not** generate factual answers.

**Functionality:**
- Sends the user question to the LLM (Ollama, e.g. `mistral:latest`) with temperature 0.
- LLM returns strict JSON: `intent` (e.g. `due_date`, `general_policy`, `links`, `greeting`, `out_of_scope`) and `slots` (e.g. `assessment`, `topic`, `section`, `link_type`).
- Parses and normalizes that JSON; if parsing fails, the pipeline refuses (no guess).
- All policy answers are then resolved by the Composer from the facts DB using this intent + slots.

**Where:** `backend/services/ollama_router.py` (`classify_intent`).

---

## 3. Composer

**Role:** Build the final answer and response using only allowed sources (facts DB, chitchat replies, fallback). No free-form LLM generation of facts.

**Functionality:**
- **Chitchat:** If Router says greeting/thanks/bye/help, returns a fixed safe reply (no DB).
- **Policy:** Calls `lookup_facts(intent, slots, course)` against `data/*_facts.json` (and optional MD fallback). Assembles one answer per query (e.g. one due date row when assessment is specified).
- **Fallback:** If no match or Router says low confidence / out_of_scope, returns a single fallback message (post on Ed/Piazza or email), with email taken from the course rules MD when possible.
- **Streaming:** For `POST /query/stream`, composes the reply word-by-word (SSE); citations are kept in the API only, not shown in the UI.

**Where:** `backend/main.py` (`_process_query`, streaming in `_stream_query_sse`), `backend/services/facts_db.py` (`lookup_facts`, `lookup_due_date`, `lookup_general_policy`, etc.), `backend/services/md_search.py` (fallback search).

---

## 4. Validator

**Role:** Enforce correctness and safety: only allow answers that come from the facts DB or from explicit chitchat/fallback; refuse when the Router output is invalid or out of scope.

**Functionality:**
- **Router output:** If the LLM’s JSON cannot be parsed or does not conform to the expected schema, the request is **refused** (no answer). Same if `confidence < 0.5` or `intent == "out_of_scope"` → no factual answer; only fallback or chitchat.
- **No LLM facts:** Validator is the rule that “facts come only from the DB”: the Router never generates dates, weights, or policy text; the Composer only assembles from `lookup_facts` (and MD fallback with confidence threshold). So the system **validates** that every factual answer is traceable to the Extractor-produced data.
- **Optional strict validator:** `backend/services/validator.py` can strictly validate and parse Router JSON (intent in allowed set, confidence in [0,1]); currently the Router does inline validation; this module can be wired in for a single validation layer.

**Where:** Refusal and confidence/out_of_scope checks in `backend/main.py`; design rule “facts from DB only” across Router + Composer; optional `backend/services/validator.py`.

---

## Flow (high level)

1. **Extractor** (offline): URL → Markdown → JSON (`*_rules.md`, `*_facts.json`).
2. **Router** (per request): User question → LLM → intent + slots (no facts).
3. **Composer** (per request): intent + slots + course → lookup in JSON/MD → one answer (or chitchat/fallback).
4. **Validator** (per request): Reject bad Router output; allow only DB/chitchat/fallback answers.
