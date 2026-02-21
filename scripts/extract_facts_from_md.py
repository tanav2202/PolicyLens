#!/usr/bin/env python3
"""
Extract structured JSON from policy/course rules Markdown.

Supports two policy scopes (flexible schema):
- course: course-specific facts (due_dates, instructors, coordinator, tas, links)
- general: program-wide policy (e.g. attendance, academic concession, grading, plagiarism)

Usage:
  python scripts/extract_facts_from_md.py data/mds_rules.md -o data/mds_facts.json
  python scripts/extract_facts_from_md.py data/cpsc_330_rules.md -o data/cpsc_330_facts.json --slug "CPSC 330"
"""

import argparse
import json
import re
import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# --- Section classification: course vs general ---
COURSE_SECTION_KEYWORDS = (
    "due", "deliverable", "assessment", "instructor", "teaching", "coordinator",
    "ta ", "tas", "links", "schedule", "syllabus", "office hour",
)
GENERAL_SECTION_KEYWORDS = (
    "attendance", "concession", "grade", "grading", "late submission",
    "regrad", "quiz policy", "plagiarism", "academic", "genai", "generative ai",
    "leave", "withdrawal", "full-time", "policy update", "transfer", "ubc policy",
)


def _strip_md_links(text: str) -> str:
    return re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text).strip()


def _classify_section(title: str) -> str:
    """Return 'course' or 'general' from section title."""
    t = title.lower()
    for k in COURSE_SECTION_KEYWORDS:
        if k in t:
            return "course"
    for k in GENERAL_SECTION_KEYWORDS:
        if k in t:
            return "general"
    return "general"  # default: treat as program policy


def _parse_md_table(lines: list[str]) -> list[dict[str, str]]:
    if len(lines) < 2:
        return []
    headers = [h.strip() for h in lines[0].split("|") if h.strip()]
    if not headers:
        return []
    rows = []
    for line in lines[2:]:
        if not line.strip() or "|" not in line:
            continue
        cells = [c.strip() for c in line.split("|") if c.strip()]
        if len(cells) >= len(headers):
            row = {headers[i]: _strip_md_links(cells[i]) for i in range(len(headers))}
            rows.append(row)
    return rows


def _extract_links(content: str) -> list[tuple[str, str]]:
    """Return list of (name, url) from markdown links."""
    return re.findall(r"\[([^\]]+)\]\(([^)]+)\)", content)


def _extract_tables_from_content(content: str) -> list[tuple[str, list[dict]]]:
    tables = []
    lines = content.split("\n")
    i = 0
    section = ""
    while i < len(lines):
        line = lines[i]
        if line.startswith("## "):
            section = line[3:].strip()
        if line.strip().startswith("|") and i + 1 < len(lines):
            block = [line]
            j = i + 1
            while j < len(lines) and lines[j].strip().startswith("|"):
                block.append(lines[j])
                j += 1
            parsed = _parse_md_table(block)
            if parsed and len(parsed[0]) >= 2:
                tables.append((section, parsed))
            i = j
            continue
        i += 1
    return tables


def _section_content_to_summary(content: str, max_chars: int = 400) -> str:
    """First paragraph or first N chars, cleaned."""
    content = _strip_md_links(content)
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
    if not paragraphs:
        return content[:max_chars].strip()
    first = paragraphs[0]
    if len(first) > max_chars:
        return first[: max_chars - 3].rsplit(" ", 1)[0] + "..."
    return first


def parse_md_sections(path: Path) -> list[dict]:
    """Parse MD into list of { level, title, content, scope }."""
    text = path.read_text(encoding="utf-8")
    sections = []
    current = []
    current_title = ""
    current_level = 0

    for line in text.split("\n"):
        if line.startswith("## "):
            if current:
                content = "\n".join(current).strip()
                scope = _classify_section(current_title)
                sections.append({
                    "level": current_level,
                    "title": current_title,
                    "content": content,
                    "scope": scope,
                })
            current_title = line.lstrip("#").strip()
            current_level = 2
            current = []
        elif line.startswith("### "):
            if current:
                content = "\n".join(current).strip()
                scope = _classify_section(current_title)
                sections.append({
                    "level": current_level,
                    "title": current_title,
                    "content": content,
                    "scope": scope,
                })
            current_title = line.lstrip("#").strip()
            current_level = 3
            current = []
        else:
            current.append(line)

    if current:
        content = "\n".join(current).strip()
        scope = _classify_section(current_title)
        sections.append({
            "level": current_level,
            "title": current_title,
            "content": content,
            "scope": scope,
        })
    return sections


def tables_to_course_facts(tables: list[tuple[str, list[dict]]], source: str) -> dict:
    """Convert parsed tables into course fact lists (due_dates, instructors, etc.)."""
    due_dates = []
    instructors = []
    links = []

    for section, rows in tables:
        section_lower = section.lower()
        if "due" in section_lower or "deliverable" in section_lower or "assessment" in section_lower:
            for row in rows:
                norm = {k.lower().replace(" ", "_"): v for k, v in row.items()}
                a_key = next((k for k in norm if "assessment" in k or "item" in k or "hw" in k), list(norm.keys())[0] if norm else None)
                due_key = next((k for k in norm if "due" in k or "date" in k or "deadline" in k), list(norm.keys())[1] if len(norm) > 1 else None)
                wf_key = next((k for k in norm if "find" in k or "where" in k), None)
                ws_key = next((k for k in norm if "submit" in k), None)
                if a_key and due_key:
                    due_dates.append({
                        "assessment": norm.get(a_key, ""),
                        "due_date": norm.get(due_key, ""),
                        "where_find": norm.get(wf_key, "") if wf_key else "",
                        "where_submit": norm.get(ws_key, "") if ws_key else "",
                        "quote": " | ".join(str(v) for v in row.values()),
                        "source": source,
                    })
        elif "instructor" in section_lower or "teaching" in section_lower:
            for row in rows:
                norm = {k.lower().replace(" ", "_"): v for k, v in row.items()}
                inst = norm.get("instructor", norm.get("name", ""))
                sec = norm.get("section", "")
                contact = norm.get("contact", norm.get("email", ""))
                when = norm.get("when", norm.get("time", ""))
                where = norm.get("where", norm.get("location", ""))
                instructors.append({
                    "section": sec,
                    "instructor": inst,
                    "contact": contact,
                    "when": when,
                    "where": where,
                    "quote": " | ".join(str(v) for v in row.values()),
                    "source": source,
                })
        # Other tables not auto-mapped; could extend

    return {"due_dates": due_dates, "instructors": instructors, "links": links}


def extract_facts_from_md(
    md_path: Path,
    source_name: str,
    course_name: str | None = None,
    include_general: bool = True,
) -> dict:
    """
    Build flexible facts JSON from Markdown.
    Returns a dict with _schema and course/general data.
    """
    source = md_path.name
    content = md_path.read_text(encoding="utf-8")

    # Tables -> course facts
    tables = _extract_tables_from_content(content)
    course_from_tables = tables_to_course_facts(tables, source)

    # Links from full content
    link_tuples = _extract_links(content)
    links = [{"name": _strip_md_links(n), "url": u, "quote": f"{n}", "source": source} for n, u in link_tuples if u.startswith("http") or u.startswith("mailto:")]

    # Sections -> general policies (and optionally refine course)
    sections = parse_md_sections(md_path)
    general_policies = []
    for s in sections:
        if not (s.get("title") or "").strip():
            continue
        if s["scope"] == "general" and include_general and s["content"]:
            summary = _section_content_to_summary(s["content"])
            general_policies.append({
                "title": s["title"],
                "summary": summary,
                "quote": summary[:300] + ("..." if len(summary) > 300 else ""),
                "source": source,
                "scope": "general",
            })

    # Build output with flexible schema
    display_name = course_name or md_path.stem.replace("_rules", "").replace("_", " ").upper()
    if "cpsc" in display_name.lower():
        parts = display_name.lower().replace("cpsc", "CPSC").split()
        display_name = " ".join(parts) if len(parts) > 1 else "CPSC"

    out = {
        "_schema": {
            "course_name": display_name,
            "key_map": {
                "due_date": "due_dates",
                "instructor_info": "instructors",
                "coordinator": "coordinator",
                "ta_list": "tas",
                "links": "links",
                "general_policy": "general_policies",
            },
            "policy_scopes": ["course", "general"],
        },
        "due_dates": course_from_tables["due_dates"],
        "instructors": course_from_tables["instructors"],
        "coordinator": [],
        "tas": [],
        "links": links[:50],
        "general_policies": general_policies,
    }

    return out


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract structured JSON from policy/course rules Markdown (course + general policy)."
    )
    parser.add_argument("md_file", type=Path, help="Input Markdown file (e.g. data/mds_rules.md)")
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=None,
        help="Output JSON path. Default: same dir as MD, {stem}_facts.json",
    )
    parser.add_argument(
        "--slug",
        type=str,
        default=None,
        help="Display name for course (e.g. 'CPSC 330', 'MDS'). Default: from filename.",
    )
    parser.add_argument(
        "--no-general",
        action="store_true",
        help="Skip extracting general policy sections; only course facts (tables, links).",
    )

    args = parser.parse_args()
    md_path = args.md_file
    if not md_path.exists():
        print(f"Error: file not found: {md_path}", file=sys.stderr)
        return 1

    out_path = args.output
    if out_path is None:
        base = md_path.stem.replace("_rules", "")
        out_path = md_path.parent / f"{base}_facts.json"

    data = extract_facts_from_md(
        md_path,
        source_name=md_path.name,
        course_name=args.slug,
        include_general=not args.no_general,
    )

    out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(data.get('due_dates', []))} due_dates, {len(data.get('instructors', []))} instructors, {len(data.get('links', []))} links, {len(data.get('general_policies', []))} general_policies -> {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
