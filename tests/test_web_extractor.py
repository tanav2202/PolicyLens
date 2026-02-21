"""Unit and integration tests for web_extractor."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest

from backend.exceptions import (
    POLICY_FETCH_AUTH_REQUIRED,
    POLICY_FETCH_FORBIDDEN,
    POLICY_FETCH_NETWORK_ERROR,
    POLICY_FETCH_NOT_FOUND,
    PolicyFetchAuthRequiredError,
    PolicyFetchForbiddenError,
    PolicyFetchNetworkError,
    PolicyFetchNotFoundError,
    PolicyFetchParseError,
)
from backend.services.web_extractor import (
    extract_policy_to_markdown,
    fetch_html,
    html_to_markdown,
    url_to_rules_filename,
    url_to_slug,
)


# --- Unit tests: slug generation ---


def test_url_to_slug_basic():
    assert url_to_slug("https://ubc-mds.github.io/policies/") == "ubc-mds-github-io-policies"
    assert url_to_slug("https://example.com/foo/bar") == "example-com-foo-bar"


def test_url_to_slug_strips_trailing_slash():
    assert url_to_slug("https://a.com/b/") == url_to_slug("https://a.com/b")


def test_url_to_slug_collapses_hyphens():
    slug = url_to_slug("https://a.com/path/to/page")
    assert "--" not in slug


def test_url_to_slug_empty_path():
    assert url_to_slug("https://example.com") == "example-com"


def test_url_to_rules_filename_mds():
    assert url_to_rules_filename("https://ubc-mds.github.io/policies/") == "mds_rules.md"
    assert url_to_rules_filename("https://ubc-mds.github.io/anything") == "mds_rules.md"


def test_url_to_rules_filename_cpsc330():
    assert url_to_rules_filename("https://ubc-cs.github.io/cpsc330-2025W2/") == "cpsc_330_rules.md"
    assert url_to_rules_filename("https://example.com/cpsc-330/syllabus") == "cpsc_330_rules.md"


def test_url_to_rules_filename_fallback():
    assert url_to_rules_filename("https://unknown.example.com/policies") == "course_rules.md"


# --- Unit tests: HTML to Markdown ---


def test_html_to_markdown_converts_headings():
    html = "<h1>Title</h1><h2>Section</h2>"
    md = html_to_markdown(html, "https://example.com")
    assert "# Title" in md
    assert "## Section" in md


def test_html_to_markdown_resolves_relative_links():
    html = '<a href="resources/quiz/">Quiz</a>'
    base = "https://ubc-mds.github.io/policies/"
    md = html_to_markdown(html, base)
    assert "https://ubc-mds.github.io/resources/quiz/" in md or "ubc-mds.github.io" in md


def test_html_to_markdown_preserves_absolute_links():
    html = '<a href="https://external.com/doc">Doc</a>'
    md = html_to_markdown(html, "https://example.com")
    assert "https://external.com" in md


def test_html_to_markdown_handles_tables():
    html = """
    <table>
      <tr><th>A</th><th>B</th></tr>
      <tr><td>1</td><td>2</td></tr>
    </table>
    """
    md = html_to_markdown(html, "https://example.com")
    assert "A" in md and "B" in md and "1" in md and "2" in md


# --- Mock tests: fetch_html error handling ---


def test_fetch_html_401_raises_auth_required():
    with patch("httpx.get") as mock_get:
        mock_get.return_value = httpx.Response(401, text="Unauthorized")
        with pytest.raises(PolicyFetchAuthRequiredError) as exc_info:
            fetch_html("https://example.com/private")
        assert exc_info.value.code == POLICY_FETCH_AUTH_REQUIRED


def test_fetch_html_403_raises_forbidden():
    with patch("httpx.get") as mock_get:
        mock_get.return_value = httpx.Response(403, text="Forbidden")
        with pytest.raises(PolicyFetchForbiddenError) as exc_info:
            fetch_html("https://example.com/forbidden")
        assert exc_info.value.code == POLICY_FETCH_FORBIDDEN


def test_fetch_html_404_raises_not_found():
    with patch("httpx.get") as mock_get:
        mock_get.return_value = httpx.Response(404, text="Not Found")
        with pytest.raises(PolicyFetchNotFoundError):
            fetch_html("https://example.com/missing")


def test_fetch_html_timeout_raises_network_error():
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.TimeoutException("timeout")
        with pytest.raises(PolicyFetchNetworkError) as exc_info:
            fetch_html("https://example.com/slow")
        assert exc_info.value.code == POLICY_FETCH_NETWORK_ERROR


def test_fetch_html_connect_error_raises_network_error():
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.ConnectError("connection refused")
        with pytest.raises(PolicyFetchNetworkError):
            fetch_html("https://example.com/")


def test_fetch_html_empty_body_raises_parse_error():
    with patch("httpx.get") as mock_get:
        mock_get.return_value = httpx.Response(
            200,
            text="",
            headers={"content-type": "text/html"},
        )
        with pytest.raises(PolicyFetchParseError):
            fetch_html("https://example.com/")


def test_fetch_html_non_html_content_type_raises_parse_error():
    with patch("httpx.get") as mock_get:
        mock_get.return_value = httpx.Response(
            200,
            text="not html",
            headers={"content-type": "application/json"},
        )
        with pytest.raises(PolicyFetchParseError):
            fetch_html("https://example.com/")


# --- Integration test: real fetch ---


@pytest.mark.integration
def test_extract_policy_to_markdown_mds_policies():
    """Fetch real MDS policies page and assert markdown output has expected sections."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = extract_policy_to_markdown(
            "https://ubc-mds.github.io/policies/",
            tmpdir,
        )
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert len(content) > 500
        assert "Attendance" in content
        assert "Academic Concession" in content
        assert "MDS Policies" in content or "Program Policies" in content
        # Metadata header
        assert "source:" in content
        assert "ubc-mds.github.io" in content
        # Output named as course_rules.md (MDS URL -> mds_rules.md)
        assert path.name == "mds_rules.md"


# --- CLI test (optional, basic) ---


def test_extract_policy_md_cli_help():
    """CLI --help works."""
    import subprocess
    result = subprocess.run(
        ["python", "scripts/extract_policy_md.py", "--help"],
        cwd=Path(__file__).resolve().parent.parent,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "url" in result.stdout
    assert "output" in result.stdout
