# PolicyLens

A course policy question-answering system that helps students find accurate information about course policies, due dates, instructors, and program rules. PolicyLens combines LLM-based intent classification with a structured facts database to provide accurate, citable responses.

## Overview

PolicyLens routes user queries through an LLM classifier, then retrieves answers from a curated facts database. The LLM never generates factual content—it only classifies intent and extracts query parameters. All factual answers come from structured JSON databases built from course policy documents.

## Features

- **Accurate Q&A**: Answers sourced from structured course policy databases
- **Multiple Course Support**: Query policies for different courses via dropdown selection
- **Streaming Responses**: Real-time word-by-word answer streaming
- **Intent Classification**: Routing to policy categories (due dates, instructors, links, general policies)
- **Fallback Handling**: Graceful handling of out-of-scope queries with helpful guidance
- **Policy Extraction**: Tools to extract and structure policy data from web pages

## Architecture

PolicyLens has four main components:

### 1. Frontend (React/TypeScript)

**Location**: `frontend/`

- Real-time streaming chat interface
- Course selection dropdown
- Persistent chat history (localStorage)
- Responsive design with Tailwind CSS

**Tech Stack**: React 18, TypeScript 5.6, Vite 6, Tailwind CSS 3.4, Framer Motion, React Markdown, Lucide React

### 2. Backend API (FastAPI)

**Location**: `backend/`

RESTful API for query processing, intent classification, and facts retrieval.

**Tech Stack**: FastAPI, Uvicorn, Pydantic, HTTPX

**Key Services**: `ollama_router.py`, `facts_db.py`, `md_search.py`, `web_extractor.py`

**Endpoints**: `POST /query`, `POST /query/stream`, `POST /extract`, `GET /courses`, `GET /health`, `GET /policy`

### 3. AI/LLM Services (Ollama)

**Location**: `backend/services/ollama_router.py`

Local LLM for intent classification and slot extraction only. Uses `mistral:latest` at temperature 0. Classifies intent (e.g. `due_date`, `general_policy`, `links`, `greeting`, `out_of_scope`) and extracts slots (assessment, topic, section). Never generates factual answers.

### 4. Data Processing Pipeline (Python Scripts)

**Location**: `scripts/`

- `extract_policy_md.py` - Web page → Markdown (`data/*_rules.md`)
- `extract_facts_from_md.py` - Markdown → structured JSON (`data/*_facts.json`)

**Tech Stack**: Python 3, BeautifulSoup4, Markdownify

## Project Structure

```
PolicyLens/
├── frontend/           # React application
├── backend/           # FastAPI server
│   └── services/     # ollama_router, facts_db, md_search, web_extractor
├── scripts/          # Policy extraction scripts
├── data/             # *_facts.json, *_rules.md
└── README.md
```

## Installation

**Prerequisites**: Python 3.8+, Node.js 16+, Ollama, Mistral model

```bash
# 1. Pull Ollama model
ollama pull mistral

# 2. Backend dependencies
pip install -r backend/requirements.txt

# 3. Frontend dependencies
cd frontend && npm install
```

## Usage

### Run the Application

1. **Ollama** (if not running): `ollama serve`
2. **Backend** (from project root):
   ```bash
   python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
   ```
3. **Frontend**:
   ```bash
   cd frontend && npm run dev
   ```
4. Open **http://localhost:5173**

### Example Questions

- "When is hw1 due?"
- "Who are the instructors?"
- "What's the late submission policy?"
- "Where can I find the course materials?"

### Add New Course Policies

```bash
# 1. Extract policy page to Markdown
python scripts/extract_policy_md.py <url> -o data/ -s <slug>

# 2. Extract facts from Markdown
python scripts/extract_facts_from_md.py data/<slug>_rules.md -o data/<slug>_facts.json --slug "Display Name"
```

Example:
```bash
python scripts/extract_policy_md.py https://ubc-mds.github.io/policies/ -o data/ -s mds
python scripts/extract_facts_from_md.py data/mds_rules.md -o data/mds_facts.json --slug MDS
```

## How It Works

1. **User Query** → Frontend sends question to backend
2. **Intent Classification** → Ollama classifies intent and extracts slots
3. **Facts Lookup** → Backend queries course-specific facts database
4. **Fallback** → If no match, searches markdown files (confidence ≥ 0.8)
5. **Response** → Answer streamed back with citations (logged in API)

### Facts Database

- **Course scope**: due_dates, instructors, coordinator, tas, links
- **General scope**: general_policies (attendance, grading, late submission, etc.)
- **Flexible schema**: via `_schema.key_map` and `_schema.field_map`

### Model Usage Policy

- ✅ Intent classification, slot extraction
- ❌ Not for generating factual answers or inventing dates/policies/emails
