"""Tests for bullet_parser module."""

from __future__ import annotations

import pytest

from linkedinto.bullet_parser import parse_bullets
from linkedinto.exceptions import BulletParseError


class TestParseBullets:
    def test_no_bullets(self) -> None:
        summary, highlights = parse_bullets("Plain text description")
        assert summary == "Plain text description"
        assert highlights == []

    def test_empty_or_none(self) -> None:
        assert parse_bullets(None) == ("", [])
        assert parse_bullets("") == ("", [])
        assert parse_bullets("  ") == ("", [])

    def test_single_bullet(self) -> None:
        summary, highlights = parse_bullets("Overview text • Single point")
        assert summary == "Overview text"
        assert highlights == ["Single point"]

    def test_multiple_bullets(self) -> None:
        text = "Summary • Point one • Point two • Point three"
        summary, highlights = parse_bullets(text)
        assert summary == "Summary"
        assert highlights == ["Point one", "Point two", "Point three"]

    def test_bullet_at_start(self) -> None:
        summary, highlights = parse_bullets("• Direct bullet")
        assert summary == ""
        assert highlights == ["Direct bullet"]

    def test_star_bullet(self) -> None:
        summary, highlights = parse_bullets("Intro * Item one * Item two")
        assert summary == "Intro"
        assert highlights == ["Item one", "Item two"]

    def test_custom_bullets(self) -> None:
        text = "Summary - Dash point + Plus point"
        summary, highlights = parse_bullets(text, custom_bullets="-+")
        assert summary == "Summary"
        assert highlights == ["Dash point", "Plus point"]

    def test_custom_bullets_empty_raises(self) -> None:
        with pytest.raises(BulletParseError):
            parse_bullets("test", custom_bullets="")

    def test_mixed_bullets_no_spaces(self) -> None:
        """A bullet without a preceding space should not split at that point."""
        text = "A •B•C"  # second • has no preceding space
        summary, highlights = parse_bullets(text)
        assert summary == "A"
        assert highlights == ["B•C"]

    def test_multiple_spaces(self) -> None:
        text = "Summary   •   Point"
        summary, highlights = parse_bullets(text)
        assert summary == "Summary"
        assert highlights == ["Point"]
