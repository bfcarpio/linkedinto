"""Tests for bullet_parser module."""

from __future__ import annotations

import pytest

from linkedinto.bullet_parser import parse_bullets
from linkedinto.exceptions import BulletParseError


class TestParseBullets:
    @pytest.mark.parametrize(
        "text,expected_summary,expected_highlights",
        [
            ("Plain text description", "Plain text description", []),
            (None, "", []),
            ("", "", []),
            ("  ", "", []),
            ("Overview text • Single point", "Overview text", ["Single point"]),
            (
                "Summary • Point one • Point two • Point three",
                "Summary",
                ["Point one", "Point two", "Point three"],
            ),
            ("• Direct bullet", "", ["Direct bullet"]),
            ("Intro * Item one * Item two", "Intro", ["Item one", "Item two"]),
            # Unambiguous bullet chars (•, ➲, etc.) split anywhere — even
            # without a preceding space, since they never appear mid-word.
            ("A •B•C", "A", ["B", "C"]),
            ("Summary   •   Point", "Summary", ["Point"]),
        ],
    )
    def test_default_bullets(
        self,
        text: str | None,
        expected_summary: str,
        expected_highlights: list[str],
    ) -> None:
        summary, highlights = parse_bullets(text)
        assert summary == expected_summary
        assert highlights == expected_highlights

    @pytest.mark.parametrize(
        "text,custom,expected_summary,expected_highlights",
        [
            (
                "Summary - Dash point + Plus point",
                "-+",
                "Summary",
                ["Dash point", "Plus point"],
            ),
        ],
    )
    def test_custom_bullets(
        self,
        text: str,
        custom: str,
        expected_summary: str,
        expected_highlights: list[str],
    ) -> None:
        summary, highlights = parse_bullets(text, custom_bullets=custom)
        assert summary == expected_summary
        assert highlights == expected_highlights

    def test_custom_bullets_empty_raises(self) -> None:
        with pytest.raises(BulletParseError):
            parse_bullets("test", custom_bullets="")
