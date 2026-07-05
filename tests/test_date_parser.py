"""Tests for date_parser module."""

from __future__ import annotations

from linkedinto.date_parser import parse_linkedin_date


class TestParseLinkedinDate:
    def test_iso_date(self) -> None:
        assert parse_linkedin_date("2020-03-15") == "2020-03-15"

    def test_yyyy_mm(self) -> None:
        assert parse_linkedin_date("2020-03") == "2020-03-01"

    def test_month_name_yyyy(self) -> None:
        assert parse_linkedin_date("March 2020") == "2020-03-01"

    def test_abbreviated_month(self) -> None:
        assert parse_linkedin_date("Mar 2020") == "2020-03-01"
        assert parse_linkedin_date("Dec 2023") == "2023-12-01"

    def test_year_only(self) -> None:
        assert parse_linkedin_date("2020") == "2020-01-01"

    def test_none_or_empty(self) -> None:
        assert parse_linkedin_date(None) is None
        assert parse_linkedin_date("") is None
        assert parse_linkedin_date("  ") is None

    def test_unparseable_returns_none(self) -> None:
        assert parse_linkedin_date("not a date") is None
        assert parse_linkedin_date("2020/03/01") is None

    def test_edge_cases(self) -> None:
        assert parse_linkedin_date("January 2020") == "2020-01-01"
        assert parse_linkedin_date("September 2023") == "2023-09-01"
        assert parse_linkedin_date("Jun 2021") == "2021-06-01"
