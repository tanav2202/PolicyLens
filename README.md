# PolicyLens

A course policy QA system that helps students find accurate information about course policies, due dates, instructors, and program rules. PolicyLens combines LLM based intent classification with a structured facts database to provide accurate, citable responses.

## Overview

PolicyLens routes user queries through an LLM classifier, then retrieves answers from a curated facts database. The LLM never generates factual content, it only classifies intent and extracts query parameters. All factual answers come from structured JSON databases built from course policy documents.

## Features

- **Accurate Q&A**: Answers sourced from structured course policy databases
- **Multiple Course Support**: Query policies for different courses via dropdown selection
- **Streaming Responses**: Real time word by word answer streaming
- **Intent Classification**: Routing to policy categories (due dates, instructors, links, general policies)
- **Fallback Handling**: Graceful handling of out of scope queries with helpful guidance
- **Policy Extraction**: Tools to extract and structure policy data from web pages

## Architecture

**Frontend**: React + TypeScript + Vite + Tailwind. Chat UI with course selection and streaming responses.

**Backend**: FastAPI server that routes queries to Ollama for intent classification, then looks up answers from a facts database. Uses markdown fallback when JSON has no match.

**Data Pipeline**: Scripts extract policy pages from URLs → Markdown → structured JSON. Facts are stored in `data/*_facts.json`.

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

- "When are my homeworks due?"
- "How do you not fail in MDS?"
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

1. **User Query**: Frontend sends question to backend
2. **Intent Classification**: Ollama classifies intent and extracts slots
3. **Facts Lookup**: Backend queries course-specific facts database
4. **Fallback**: If no match, searches markdown files (confidence ≥ 0.8)
5. **Response**: Answer streamed back with citations (logged in API)

### Facts Database

- **Course scope**: due_dates, instructors, coordinator, tas, links
- **General scope**: general_policies (attendance, grading, late submission, etc.)
- **Flexible schema**: via `_schema.key_map` and `_schema.field_map`

### Model Usage Policy

The LLM is used only for intent classification and slot extraction. It never generates factual answers, dates, policies, or contact information. All factual content comes from validated sources in the facts database.
