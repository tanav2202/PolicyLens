# Course Facts Files

Add `*_facts.json` files to this folder. Each file becomes a course option in the dropdown.

## Pipeline: policy URL → Markdown → JSON

1. **Fetch policy page to Markdown** (add new policies from any URL):
   ```bash
   python scripts/extract_policy_md.py <url> -o data/ -s <slug>
   ```
   Writes `data/<slug>_rules.md`. Example: `-s mds` → `mds_rules.md`.

2. **Extract JSON from that Markdown** (generalisable for any `*_rules.md`):
   ```bash
   python scripts/extract_facts_from_md.py data/<slug>_rules.md -o data/<slug>_facts.json --slug "Display Name"
   ```
   Writes `data/<slug>_facts.json` with course + general policy. So adding more policies = run step 1 with new URL/slug, then step 2 on the new file.

## Extracting JSON from Markdown

Use the script to build or refresh `*_facts.json` from a rules/policy Markdown file. The script supports **two policy scopes** (flexible schema):

- **course**: course-specific facts (due_dates, instructors, coordinator, tas, links) from tables and links in the MD.
- **general**: program-wide policy sections (attendance, academic concession, grading, late submission, plagiarism, GenAI, etc.) as `general_policies` with title, summary, quote, source, and `scope: "general"`.

```bash
# From project root
python scripts/extract_facts_from_md.py data/mds_rules.md -o data/mds_facts.json --slug MDS
python scripts/extract_facts_from_md.py data/cpsc_330_rules.md -o data/cpsc_330_facts.json --slug "CPSC 330"

# Skip general policy (course facts only)
python scripts/extract_facts_from_md.py data/foo_rules.md -o data/foo_facts.json --no-general
```

Output JSON includes `_schema.policy_scopes: ["course", "general"]` and `_schema.key_map.general_policy: "general_policies"` so the backend can answer both course-specific and general policy questions.

## MD Fallback

When JSON has no info for a query, the system searches the course rules markdown (`{course_slug}_rules.md`, e.g. `cpsc_330_rules.md`). If found with high confidence (≥0.8), that answer is used. Add-to-JSON on high confidence is available but disabled by default for safety.

When no matching facts are found at all, the system falls back to a message asking the user to post on Ed Discussion or Piazza, or to email the address extracted from the course rules MD (e.g. coordinator or admin email).

## File naming

- `cpsc_330_facts.json` → course "CPSC 330"
- `mds_facts.json` → course "MDS"
- `cpsc_340_facts.json` → course "CPSC 340"

## Schema (optional)

Use `_schema` to customize display name and JSON structure:

```json
{
  "_schema": {
    "course_name": "CPSC 330",
    "key_map": {
      "due_date": "due_dates",
      "instructor_info": "instructors",
      "coordinator": "coordinator",
      "ta_list": "tas",
      "links": "links"
    },
    "field_map": {
      "due_date": {
        "assessment": "item",
        "due_date": "deadline",
        "where_find": "instructions",
        "where_submit": "submit_to"
      }
    }
  },
  "due_dates": [...],
  "instructors": [...]
}
```

- **course_name**: Display name in dropdown (default: derived from filename)
- **key_map**: Map intent → your data key. Use if your JSON uses different keys (e.g. `assignments` instead of `due_dates`)
- **field_map**: Map our field names → your field names per intent. Use if your records have different shapes

## Standard structure (no schema)

If you omit `_schema`, use these keys and field names:

| Intent | Data key | Record fields |
|--------|----------|---------------|
| due_date | due_dates | assessment, due_date, where_find, where_submit, quote, source |
| instructor_info | instructors | section, instructor, contact, when, where, quote, source |
| coordinator | coordinator | name, email, purpose, quote, source |
| ta_list | tas | name, quote?, source? |
| links | links | name, url, quote, source |
