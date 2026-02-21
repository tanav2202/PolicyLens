# PolicyLens

## Current methodology

1. **LLM as router only (Ollama, `mistral:latest`)**  
   The model does **not** generate factual answers. It only:
   - Classifies **intent** (e.g. `due_date`, `general_policy`, `links`, `greeting`, `out_of_scope`).
   - Fills **slots** (e.g. `assessment`, `topic`, `section`, `link_type`).  
   Temperature is 0; output is strict JSON. If parsing fails, the request is refused.

2. **Facts DB as single source of truth**  
   All factual answers come from **`data/*_facts.json`** (and optionally from **`*_rules.md`** when JSON has no match). The DB holds:
   - **Course scope:** due_dates, instructors, coordinator, tas, links (per course).
   - **General scope:** general_policies (program-wide rules, matched by topic substring in title/summary).  
   Schema is flexible via `_schema.key_map` and `_schema.field_map` so different courses can use different keys/field names.

3. **Lookup flow**  
   - Chitchat (greeting/thanks/bye/help) → fixed safe replies, no DB.  
   - Policy intents → `lookup_facts(intent, slots, course)` against the course’s JSON; if the result is empty or “no data”, **markdown fallback** searches the course’s `*_rules.md` (tables/lists/links) and is used when confidence ≥ 0.8.  
   - Low confidence or `out_of_scope` → **fallback message**: ask user to post on Ed Discussion or Piazza, or email the address **extracted from the course rules MD** (e.g. coordinator/admin).

4. **Responses**  
   - **Streaming:** `POST /query/stream` returns the answer word-by-word (SSE), then citations in the payload (kept in DB/API only).  
   - **UI:** Only the answer text is shown; **sources are not displayed** to the user (citations remain in the API response for logging/audit).

5. **Adding policy data**  
   - **Fetch policy page → Markdown:** `scripts/extract_policy_md.py <url> -o data/ -s <slug>` → `data/<slug>_rules.md`.  
   - **Markdown → JSON:** `scripts/extract_facts_from_md.py data/<slug>_rules.md -o data/<slug>_facts.json --slug "Display Name"` → course + general policies in one flexible JSON.

---

## Run and see everything in action

From the **project root** (`PolicyLens/`):

### 1. Ollama (for intent classification)

The backend uses **mistral:latest** for intent/slot classification. Have Ollama running and the model available:

```bash
ollama pull mistral
# If Ollama isn’t running, start the app or: ollama serve
```

### 2. Backend (FastAPI, port 8000)

In one terminal:

```bash
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

You should see `Uvicorn running on http://0.0.0.0:8000`. Optional: open http://localhost:8000/docs to try the API.

### 3. Frontend (Vite, port 5173)

In a second terminal:

```bash
cd frontend && npm install && npm run dev
```

### 4. Use the app

Open **http://localhost:5173** in your browser.

- Pick a course (e.g. **CPSC 330** or **MDS**) in the dropdown.
- Try:
  - **“When is hw1 due?”** (course fact)
  - **“Where do I check my homework?”** (due_date)
  - **“What’s the late submission policy?”** (MDS general policy)
  - **“Hey, how’s it going?”** (chitchat)
- Replies stream in word-by-word. Sources are kept in the API only (not shown in the UI).

### Optional: refresh policy data from Markdown

If you’ve added or updated `data/*_rules.md`:

```bash
python scripts/extract_facts_from_md.py data/mds_rules.md -o data/mds_facts.json --slug MDS
python scripts/extract_facts_from_md.py data/cpsc_330_rules.md -o data/cpsc_330_facts.json --slug "CPSC 330"
```

Restart the backend (or rely on `--reload`) so it picks up the new JSON.