"""Configuration for Course Policy QA backend."""

from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR.parent / "data"
FACTS_DB_PATH = DATA_DIR / "facts_db.json"

# Ollama settings - Model usage policy: temperature 0 for deterministic routing
OLLAMA_MODEL = "llama3.2"
OLLAMA_TEMPERATURE = 0
OLLAMA_HOST = "http://localhost:11434"
