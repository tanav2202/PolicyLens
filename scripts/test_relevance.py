#!/usr/bin/env python3
"""
Run 15-20 query iterations against PolicyLens API and report relevance.
No code changes - backend must be running: uvicorn backend.main:app --port 8000
Usage: python scripts/test_relevance.py [--base http://localhost:8000]
"""
import argparse
import json
import sys
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# 15-20 diverse questions: course facts, general policy, chitchat, edge cases
QUERIES = [
    ("When is hw1 due?", "CPSC 330"),
    ("Where do I submit homework?", "CPSC 330"),
    ("Who is the coordinator?", "CPSC 330"),
    ("What's the late submission policy?", "MDS"),
    ("How do you fail an MDS course?", "MDS"),
    ("What info do you have about general policies?", "MDS"),
    ("List the TAs", "CPSC 330"),
    ("Hi there", "CPSC 330"),
    ("Thanks!", "MDS"),
    ("When is the syllabus quiz due?", "CPSC 330"),
    ("Academic concession policy?", "MDS"),
    ("Canvas link?", "CPSC 330"),
    ("Who teaches section 201?", "CPSC 330"),
    ("Plagiarism policy?", "MDS"),
    ("Bye", "MDS"),
    ("What is the grading scheme?", "MDS"),
    ("Where do I find assignments?", "CPSC 330"),
    ("Help", "CPSC 330"),
    ("Quiz policy?", "MDS"),
    ("When is midterm 1?", "CPSC 330"),
]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://localhost:8000", help="API base URL")
    args = parser.parse_args()
    base = args.base.rstrip("/")

    results = []
    for i, (question, course) in enumerate(QUERIES, 1):
        try:
            body = json.dumps({"question": question, "course": course}).encode("utf-8")
            req = Request(
                f"{base}/query",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
        except (URLError, HTTPError, json.JSONDecodeError) as e:
            results.append((i, question, course, None, str(e), "ERROR"))
            continue

        answer = (data.get("answer") or "").strip()
        intent = data.get("intent", "")
        refused = data.get("refused", False)
        ref_reason = data.get("refusal_reason") or ""

        # Simple relevance: not relevant if refused with empty answer, or fallback for policy question
        if refused and not answer:
            rel = "NOT_RELEVANT (refused, no answer)"
        elif refused and ref_reason:
            rel = "REFUSED: " + ref_reason[:60]
        elif not answer and intent in ("due_date", "instructor_info", "general_policy", "links"):
            rel = "NOT_RELEVANT (policy question but empty answer)"
        elif "couldn't find" in answer.lower() and "post on ed" in answer.lower():
            rel = "FALLBACK (no match; asked to post/email)"
        elif intent in ("greeting", "thanks", "bye", "help") and answer:
            rel = "RELEVANT (chitchat)"
        elif answer and len(answer) > 20:
            rel = "RELEVANT (substantive answer)"
        elif answer:
            rel = "RELEVANT (short answer)"
        else:
            rel = "CHECK (unclear)"

        results.append((i, question, course, answer[:200] + ("..." if len(answer) > 200 else ""), intent, rel))

    # Print report
    print("=" * 80)
    print("PolicyLens relevance test ({} iterations)".format(len(QUERIES)))
    print("=" * 80)
    for i, question, course, answer, intent, rel in results:
        print("\n[{}] Q ({}): {}".format(i, course, question))
        if answer is None:
            print("    Response: {}".format(rel))
        else:
            print("    Intent: {} | {}".format(intent, rel))
            print("    Answer: {}".format((answer or "(empty)")[:300]))
    print("\n" + "=" * 80)
    relevant = sum(1 for r in results if "RELEVANT" in r[5] or "FALLBACK" in r[5])
    print("Summary: {} / {} with substantive or fallback response".format(relevant, len(results)))
    return 0 if relevant >= len(results) * 0.6 else 1

if __name__ == "__main__":
    sys.exit(main())
