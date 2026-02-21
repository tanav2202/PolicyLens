#!/usr/bin/env python3
"""
CLI to extract policy website to Markdown.
Usage:
  python scripts/extract_policy_md.py <url> [--output data/] [--slug NAME]
  python scripts/extract_policy_md.py https://ubc-mds.github.io/policies/
"""
import argparse
import sys
from pathlib import Path

# Ensure backend is importable when run from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import DATA_DIR
from backend.exceptions import PolicyFetchError
from backend.services.web_extractor import extract_policy_to_markdown


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract policy website to Markdown file"
    )
    parser.add_argument("url", help="Policy page URL to fetch")
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=DATA_DIR,
        help=f"Output directory (default: {DATA_DIR})",
    )
    parser.add_argument(
        "-s", "--slug",
        type=str,
        default=None,
        help="Output base name (e.g. mds, cpsc_330). Output is {slug}_rules.md. Default: derived from URL",
    )
    parser.add_argument(
        "-t", "--token",
        type=str,
        default=None,
        help="Optional Bearer token for authenticated requests",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Request timeout in seconds (default: 30)",
    )

    args = parser.parse_args()
    url = args.url.strip()
    if not url:
        print("Error: URL is required", file=sys.stderr)
        return 2

    try:
        path = extract_policy_to_markdown(
            url,
            args.output,
            timeout=args.timeout,
            auth_token=args.token,
            slug=args.slug,
        )
        print(str(path))
        return 0
    except PolicyFetchError as e:
        print(f"Error [{e.code}]: {e.message}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
