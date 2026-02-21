"""Configuration for Course Policy QA backend."""

from pathlib import Path
from typing import Optional

# Paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR.parent / "data"

# Default intent -> data key mapping (used when _schema.key_map is absent)
DEFAULT_KEY_MAP = {
    "due_date": "due_dates",
    "instructor_info": "instructors",
    "coordinator": "coordinator",
    "ta_list": "tas",
    "links": "links",
}


def _filename_to_display(filename: str) -> str:
    """Convert cpsc_330_facts.json -> CPSC 330, mds_facts.json -> MDS."""
    base = filename.replace("_facts.json", "").replace(".json", "")
    # Uppercase common course prefixes
    if base.startswith("cpsc"):
        parts = base.split("_", 1)
        return f"CPSC {parts[1]}" if len(parts) > 1 else "CPSC"
    return base.replace("_", " ").upper()


def discover_courses() -> dict[str, str]:
    """
    Dynamically discover courses from data/*_facts.json files.
    Returns {display_name: filename} e.g. {"CPSC 330": "cpsc_330_facts.json"}
    """
    if not DATA_DIR.exists():
        return {}
    result = {}
    for path in sorted(DATA_DIR.glob("*_facts.json")):
        filename = path.name
        # Check for _schema.course_name in file for custom display name
        try:
            import json
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            schema = data.get("_schema", {}) or {}
            display = schema.get("course_name") or _filename_to_display(filename)
        except Exception:
            display = _filename_to_display(filename)
        result[display] = filename
    return result


# Lazy: call get_course_facts_map() for fresh discovery (handles new files)
def get_course_facts_map() -> dict[str, str]:
    """Return current course -> filename map (scans data/ each call)."""
    return discover_courses()


# Default: first course when map is non-empty
def get_default_course() -> Optional[str]:
    m = get_course_facts_map()
    return next(iter(m)) if m else None


def get_facts_db_path(course: Optional[str] = None) -> Path:
    """Return facts DB path for the given course. Default = CPSC 330."""
    if not course or course.strip().upper() == "CPSC 330":
        return DATA_DIR / "facts_db.json"
    # MDS -> data/MDS_facts_db.json; other courses same pattern
    safe = course.strip().replace(" ", "_")
    return DATA_DIR / f"{safe}_facts_db.json"

# Ollama settings - Model usage policy: temperature 0 for deterministic routing
OLLAMA_MODEL = "llama3.2"
OLLAMA_TEMPERATURE = 0
OLLAMA_HOST = "http://localhost:11434"
