# PolicyLens Frontend Implementation Guide

This document provides the frontend team with the information needed to implement the policy URL ingestion flow and integrate with the full PolicyLens pipeline.

---

## End-to-End Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                           PolicyLens Full Pipeline                                         │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                           │
│  User Action          Backend (Auto)              Backend (Existing)     User sees       │
│  ───────────          ─────────────               ──────────────────     ────────         │
│                                                                                           │
│  1. Enter policy  →   POST /extract           →   (Website → MD)      →  Success / Error │
│     URL (+ token       Check page access            Write to data/*.md                      │
│     if prompted)       Fetch HTML                                                         │
│                        Convert to Markdown                                                  │
│                                                                                           │
│  2. (Backend)      →   MD → JSON pipeline     →   Build/update          (No UI)          │
│                        (runs after extract)        facts_db.json                          │
│                                                                                           │
│  3. Ask question  →   POST /query             →   LLM intent classify   →  Answer +       │
│     (existing)        Facts lookup                 facts_db lookup        Citations       │
│                       Return answer + cites         Return formatted                       │
│                                                                                           │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 1. User Flow to Implement

### Step 1: Policy URL Input and Extraction

**User action:** Enters a policy website URL (e.g. `https://ubc-mds.github.io/policies/`).

**Frontend responsibilities:**
1. Validate that the input is a valid URL (use URL constructor or regex).
2. Call the **extract API** (see §3).
3. Handle the response:
   - **Success:** Show confirmation (e.g. "Policy extracted to mds_rules.md").
   - **Auth required (401):** Show a credential prompt (e.g. "This page requires authentication. Enter your GitHub token:") and retry the request with `token` in the body.
   - **Other errors:** Show the appropriate error message from the response (see §4).

**Check if webpage works:** The backend performs this when it fetches the URL. The extract API returns success only if the page is reachable and valid HTML. No separate “open webpage and check” call is needed; the extract call does both.

---

## 2. Backend Pipeline (For Context)

| Stage | What happens | Trigger |
|-------|--------------|---------|
| Website → MD | Fetch HTML, convert to Markdown, write `data/{course}_rules.md` | `POST /extract` |
| MD → JSON | Parse `.md`, build structured facts, write `facts_db.json` | Backend pipeline (after extract) |
| JSON → LLM | Load `facts_db.json`; Ollama classifies intent; lookup facts by intent/slots | `POST /query` |
| Output | Return answer + citations via FastAPI | `POST /query` |

The frontend only needs to call `POST /extract` and `POST /query`. The MD→JSON step is backend-owned.

---

## 3. API Contract: Extract Endpoint

**Note:** A `POST /extract` endpoint will need to be added to the backend. Below is the contract for the frontend to implement against.

### Request

```
POST /extract
Content-Type: application/json
```

```json
{
  "url": "https://ubc-mds.github.io/policies/",
  "token": null
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `url` | string | Yes | Policy page URL to fetch |
| `token` | string \| null | No | Bearer token for authenticated pages (e.g. GitHub PAT). Omit for public pages. |

### Success Response (HTTP 200)

```json
{
  "status": "ok",
  "path": "data/mds_rules.md"
}
```

| Field | Description |
|-------|-------------|
| `path` | Relative path to the written Markdown file (e.g. `mds_rules.md`, `cpsc_330_rules.md`) |

### Error Response (HTTP 4xx/5xx)

```json
{
  "error": "Authentication required to access this policy page",
  "code": "POLICY_FETCH_AUTH_REQUIRED",
  "http_status": 401
}
```

---

## 4. Error Codes (For Frontend Branching)

Use `code` to decide how to handle the error:

| Code | HTTP | User-facing message / action |
|------|------|------------------------------|
| `POLICY_FETCH_AUTH_REQUIRED` | 401 | "This page requires authentication. Enter your GitHub token (PAT) to continue." → Show token input, retry with `token`. |
| `POLICY_FETCH_FORBIDDEN` | 403 | "Access forbidden. You may not have permission to view this page." |
| `POLICY_FETCH_NOT_FOUND` | 404 | "Policy page not found. Please check the URL." |
| `POLICY_FETCH_NETWORK_ERROR` | 502 | "Could not reach the page (network or timeout). Try again later." |
| `POLICY_FETCH_PARSE_ERROR` | 422 | "The page could not be parsed as policy content. Ensure it is a valid HTML policy page." |
| `POLICY_FETCH_ERROR` | varies | Generic: show `error` message from response. |

---

## 5. Query API (Existing)

For Q&A after policies are loaded:

```
POST /query
Content-Type: application/json
```

```json
{
  "question": "When is hw1 due?"
}
```

**Response (success, not refused):**
```json
{
  "answer": "hw1 is due Jan 12, 11:59 pm...",
  "citations": [
    { "text": "Jan 12, 11:59 pm", "quote": "hw1 | Jan 12...", "source": "cpsc_330_rules.md" }
  ],
  "intent": "due_date",
  "slots_used": { "assessment": "hw1" },
  "refused": false
}
```

**Response (refused):**
```json
{
  "answer": "",
  "citations": [],
  "intent": "out_of_scope",
  "refused": true,
  "refusal_reason": "No matching facts in database."
}
```

---

## 6. API Base URL and Proxy

- In dev, frontend uses `/api`; Vite proxies `/api` → `http://localhost:8000`.
- Rewrite: `/api/query` → `/query`, `/api/extract` → `/extract`.
- Base URL: `const API_BASE = '/api'` (or from env).

---

## 7. Output File Naming

Extracted files are named by course/program:

| URL pattern | Output file |
|-------------|-------------|
| `ubc-mds.github.io` | `mds_rules.md` |
| `cpsc330`, `cpsc-330` | `cpsc_330_rules.md` |
| Other | `course_rules.md` |

The response `path` will reflect this (e.g. `data/mds_rules.md`).

---

## 8. Recommended UI Flow

1. **Settings / Add Policy**
   - Input: policy URL.
   - Button: "Extract Policy" (or similar).
   - On submit: call `POST /extract` with `{ url }`.
   - If `code === "POLICY_FETCH_AUTH_REQUIRED"`: show token input → retry with `{ url, token }`.
   - On success: show path and a short success message.
   - On other errors: show message based on `code` (see §4).

2. **Chat / Q&A**
   - Keep existing `POST /query` flow.
   - Optionally allow selecting which policy (MDS, CPSC 330, etc.) is in scope; backend may use this later for multi-course support.

3. **Loading states**
   - Show loading while extract and query requests are in progress.
   - Extract can take a few seconds for larger pages.

---

## 9. Security Notes

- **Token handling:** Never log or store tokens in frontend storage unless you have a clear security design. Prefer ephemeral use: collect token → send in request → discard from memory.
- **CORS:** Backend allows `*` origins in dev; adjust for production.
- **URL validation:** Only allow `https://` URLs for policy pages.

---

## 10. Summary Checklist for Frontend

- [ ] URL input field with basic validation.
- [ ] Call `POST /extract` with `{ url }`.
- [ ] On `POLICY_FETCH_AUTH_REQUIRED`: show token prompt and retry with `{ url, token }`.
- [ ] Map other error codes to user-facing messages.
- [ ] Show success with returned `path`.
- [ ] Keep existing `POST /query` Q&A flow.
- [ ] Handle loading and error states.
