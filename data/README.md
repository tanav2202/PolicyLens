# Course Facts Files

Add `*_facts.json` files to this folder. Each file becomes a course option in the dropdown.

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
