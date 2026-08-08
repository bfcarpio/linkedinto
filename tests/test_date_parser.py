"""Tests for date_parser module."""

from __future__ import annotations

import pytest

from linkedinto.date_parser import parse_linkedin_date


class TestParseLinkedinDate:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("2020-03-15", "2020-03-15"),
            ("2020-03", "2020-03-01"),
            ("March 2020", "2020-03-01"),
            ("Mar 2020", "2020-03-01"),
            ("Dec 2023", "2023-12-01"),
            ("2020", "2020-01-01"),
            (None, None),
            ("", None),
            ("  ", None),
            ("not a date", None),
            ("2020/03/01", None),
            ("January 2020", "2020-01-01"),
            ("September 2023", "2023-09-01"),
            ("Jun 2021", "2021-06-01"),
        ],
    )
    def test_parse_date(self, raw: str | None, expected: str | None) -> None:
        assert parse_linkedin_date(raw) == expected
