"""URL extraction utilities for LinkedIn export data."""

from __future__ import annotations

import re


def extract_url(raw: str | None) -> str | None:
    """Extract a URL from a LinkedIn field.

    Handles bracket format: [Network:https://...]
    Handles plain URLs starting with http:// or https://

    Returns None for invalid or missing URLs.
    """
    if not raw or not raw.strip():
        return None

    text = raw.strip()

    # Bracket format: [Network:https://...]
    bracket_match = re.search(r"\[[^\]]*:\s*(https?://[^\s,\]]+)", text)
    if bracket_match:
        return bracket_match.group(1)

    # Plain URL
    url_match = re.search(r"(https?://[^\s,]+)", text)
    if url_match:
        return url_match.group(1)

    return None


def extract_websites(raw: str | None) -> list[str]:
    """Extract all URLs from a LinkedIn websites field.

    Handles two formats:
    - Labeled bracket: ``[COMPANY: https://example.com, PORTFOLIO: https://portfolio.com]``
      (LinkedIn CSV export)
    - Plain comma-separated: ``https://github.com/johndoe,https://johndoe.dev``
      (linkedinto.toml config)

    The labeled format is tried first so labels aren't captured into URLs.

    Returns:
        A list of all URLs found, or empty list for None/empty input.
    """
    if not raw or not raw.strip():
        return []

    # Labeled format: [LABEL: url, LABEL: url] or LABEL: url (LinkedIn export)
    labeled = re.findall(r"[^:\]]+:\s*(https?://[^\s,\]]+)", raw)
    if labeled:
        return labeled

    # Fallback: plain comma-separated URLs (config file format)
    return re.findall(r"(https?://[^\s,\]]+)", raw)
