# PolicyLens

## Running locally

Run both from the **project root** (`PolicyLens/`).

**Backend** (FastAPI; port 8000):

```bash
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend** (Vite; port 5173):

```bash
cd frontend && npm install && npm run dev
```

Then open http://localhost:5173. Ensure Ollama is running and the model is pulled (`ollama pull llama3.2`) for the backend to work.