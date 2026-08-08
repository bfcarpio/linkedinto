"""Tests for URL extraction utilities."""

from __future__ import annotations

import pytest

from linkedinto.url_extractor import extract_websites


class TestExtractWebsites:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            (
                "[COMPANY: https://company.com, PORTFOLIO: https://portfolio.com]",
                ["https://company.com", "https://portfolio.com"],
            ),
            ("[COMPANY: https://company.com]", ["https://company.com"]),
            # Plain comma-separated URLs (config file format).
            (
                "https://github.com/johndoe,https://johndoe.dev",
                ["https://github.com/johndoe", "https://johndoe.dev"],
            ),
            # Plain URLs with spaces after commas.
            (
                "https://example.com, https://other.com",
                ["https://example.com", "https://other.com"],
            ),
            (None, []),
            ("", []),
            ("   ", []),
            # Brackets present but no valid URL inside.
            ("[LABEL: not-a-url, OTHER: also-not]", []),
        ],
    )
    def test_extract(self, raw: str | None, expected: list[str]) -> None:
        assert extract_websites(raw) == expected
