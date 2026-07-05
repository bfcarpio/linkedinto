"""Tests for URL extraction utilities."""

from __future__ import annotations

from linkedinto.url_extractor import extract_websites


class TestExtractWebsites:
    def test_bracket_format_multiple(self) -> None:
        raw = "[COMPANY: https://company.com, PORTFOLIO: https://portfolio.com]"
        assert extract_websites(raw) == [
            "https://company.com",
            "https://portfolio.com",
        ]

    def test_bracket_format_single(self) -> None:
        raw = "[COMPANY: https://company.com]"
        assert extract_websites(raw) == ["https://company.com"]

    def test_plain_format(self) -> None:
        """Plain URLs without labels are NOT matched by the bracket regex."""
        raw = "https://example.com, https://other.com"
        assert extract_websites(raw) == []

    def test_none_input(self) -> None:
        assert extract_websites(None) == []

    def test_empty_string(self) -> None:
        assert extract_websites("") == []

    def test_whitespace_only(self) -> None:
        assert extract_websites("   ") == []

    def test_malformed_no_urls(self) -> None:
        """Brackets but no valid URL."""
        raw = "[LABEL: not-a-url, OTHER: also-not]"
        assert extract_websites(raw) == []
