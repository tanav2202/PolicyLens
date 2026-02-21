"""
Website to Markdown extraction for policy pages.
Fetches HTML, converts to Markdown, resolves relative links, writes to disk.
"""

from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from markdownify import markdownify as md

from backend.exceptions import (
    PolicyFetchAuthRequiredError,
    PolicyFetchError,
    PolicyFetchForbiddenError,
    PolicyFetchNetworkError,
    PolicyFetchNotFoundError,
    PolicyFetchParseError,
)

DEFAULT_USER_AGENT = (
    "PolicyLens/1.0 (policy extraction; "
    "https://github.com/ubc-cpsc/PolicyLens)"
)
DEFAULT_TIMEOUT = 30.0


def url_to_slug(url: str) -> str:
    """
    Derive a filesystem-safe slug from a URL.
    e.g. https://ubc-mds.github.io/policies/ -> ubc-mds-github-io-policies
    """
    parsed = urlparse(url)
    # Combine netloc + path, strip trailing slash
    combined = (parsed.netloc or "") + (parsed.path or "").rstrip("/")
    # Replace separators with hyphens, remove leading/trailing
    slug = combined.replace(".", "-").replace("/", "-").strip("-")
    # Collapse multiple hyphens, lowercase
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.lower() or "policy-page"


def url_to_rules_filename(url: str) -> str:
    """
    Derive course_rules.md style filename from URL.
    Examples:
      https://ubc-mds.github.io/policies/ -> mds_rules.md
      https://.../cpsc330.../ -> cpsc_330_rules.md
    """
    url_lower = url.lower()
    # MDS program policies
    if "ubc-mds" in url_lower or (
        "mds" in url_lower and "github.io" in url_lower and "ubc" in url_lower
    ):
        return "mds_rules.md"
    # CPSC 330 course
    if "cpsc330" in url_lower or "cpsc-330" in url_lower or "cpsc_330" in url_lower:
        return "cpsc_330_rules.md"
    if "cpsc" in url_lower and "330" in url_lower:
        return "cpsc_330_rules.md"
    # Fallback: generic name
    return "course_rules.md"


def _resolve_links(html: str, base_url: str) -> str:
    """Convert relative href/src to absolute URLs in HTML."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(["a", "img", "link"]):
        attr = "href" if tag.name in ("a", "link") else "src"
        val = tag.get(attr)
        if val and not val.startswith(("#", "mailto:", "tel:")):
            tag[attr] = urljoin(base_url, val)
    return str(soup)


def fetch_html(
    url: str,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    headers: dict[str, str] | None = None,
    auth_token: str | None = None,
) -> str:
    """
    Fetch HTML from URL. Raises PolicyFetch* exceptions on failure.
    """
    request_headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
    }
    if headers:
        request_headers.update(headers)
    if auth_token:
        request_headers["Authorization"] = f"Bearer {auth_token}"

    try:
        response = httpx.get(
            url,
            headers=request_headers,
            timeout=timeout,
            follow_redirects=True,
        )
    except httpx.TimeoutException as e:
        raise PolicyFetchNetworkError(f"Request timeout: {e}") from e
    except httpx.ConnectError as e:
        raise PolicyFetchNetworkError(f"Connection error: {e}") from e
    except httpx.RequestError as e:
        raise PolicyFetchNetworkError(f"Request failed: {e}") from e

    if response.status_code == 401:
        raise PolicyFetchAuthRequiredError()
    if response.status_code == 403:
        raise PolicyFetchForbiddenError()
    if response.status_code == 404:
        raise PolicyFetchNotFoundError()

    if response.status_code >= 400:
        raise PolicyFetchError(
            f"HTTP {response.status_code}: {response.reason_phrase or 'Request failed'}",
            http_status=response.status_code,
        )

    content_type = (response.headers.get("content-type") or "").lower()
    if "text/html" not in content_type and "application/xhtml" not in content_type:
        raise PolicyFetchParseError(
            f"Response is not HTML (content-type: {content_type})"
        )

    text = response.text
    if not text or not text.strip():
        raise PolicyFetchParseError("Response body is empty")

    return text


def html_to_markdown(html: str, base_url: str) -> str:
    """
    Convert HTML to Markdown, resolving relative links to absolute.
    """
    resolved = _resolve_links(html, base_url)
    return md(resolved, heading_style="ATX")


def extract_policy_to_markdown(
    url: str,
    output_dir: Path | str,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    auth_token: str | None = None,
    slug: str | None = None,
) -> Path:
    """
    Fetch policy page, convert to Markdown, write to file.
    Returns path to written file.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    html = fetch_html(url, timeout=timeout, auth_token=auth_token)
    markdown_content = html_to_markdown(html, url)

    if not markdown_content.strip():
        raise PolicyFetchParseError("HTML produced empty markdown")

    # Output as {course}_rules.md (e.g. mds_rules.md, cpsc_330_rules.md)
    if slug:
        base = slug.strip().replace(".md", "")
        slug = f"{base}_rules.md" if not base.endswith("_rules") else f"{base}.md"
    else:
        slug = url_to_rules_filename(url)

    out_file = output_path / slug
    metadata = (
        f"<!-- source: {url}\n"
        f"     fetched: {datetime.now(timezone.utc).isoformat()} -->\n\n"
    )
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(metadata)
        f.write(markdown_content)

    return out_file
