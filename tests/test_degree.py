"""Tests for the Degree value object and abbreviation mapping."""

import pytest

from linkedinto.degree import Degree


class TestDegreeFromText:
    @pytest.mark.parametrize(
        "text,expected_full,expected_abbreviation",
        [
            # Full names → abbreviation
            ("Bachelor of Science", "Bachelor of Science", "BS"),
            ("Bachelor of Arts", "Bachelor of Arts", "BA"),
            ("Bachelor of Engineering", "Bachelor of Engineering", "BEng"),
            ("Master of Science", "Master of Science", "MS"),
            ("Master of Arts", "Master of Arts", "MA"),
            (
                "Master of Business Administration",
                "Master of Business Administration",
                "MBA",
            ),
            ("Doctor of Philosophy", "Doctor of Philosophy", "PhD"),
            ("Doctor of Medicine", "Doctor of Medicine", "MD"),
            ("Doctor of Jurisprudence", "Doctor of Jurisprudence", "JD"),
            ("Associate of Arts", "Associate of Arts", "AA"),
            ("Associate of Science", "Associate of Science", "AS"),
            ("Specialist in Education", "Specialist in Education", "EdS"),
            # Plural variants → canonical full
            ("Bachelors of Science", "Bachelor of Science", "BS"),
            ("Masters of Arts", "Master of Arts", "MA"),
            (
                "Masters of Business Administration",
                "Master of Business Administration",
                "MBA",
            ),
            # Bare words → canonical
            ("bachelor", "Bachelor of Science", "BS"),
            ("master", "Master of Science", "MS"),
            ("doctor", "Doctor of Philosophy", "PhD"),
            ("doctorate", "Doctor of Philosophy", "PhD"),
            # Already-abbreviated → canonical
            ("BS", "Bachelor of Science", "BS"),
            ("bs", "Bachelor of Science", "BS"),
            ("MS", "Master of Science", "MS"),
            ("PhD", "Doctor of Philosophy", "PhD"),
            ("phd", "Doctor of Philosophy", "PhD"),
            ("MBA", "Master of Business Administration", "MBA"),
            # Case-insensitive
            ("bachelor of science", "Bachelor of Science", "BS"),
            ("master of science", "Master of Science", "MS"),
            # Unknown
            ("Certificate in Welding", "Certificate in Welding", None),
            ("Some Custom Degree", "Some Custom Degree", None),
        ],
    )
    def test_mapping(
        self,
        text: str,
        expected_full: str,
        expected_abbreviation: str | None,
    ) -> None:
        d = Degree.from_text(text)
        assert d is not None
        assert d.full == expected_full
        assert d.abbreviation == expected_abbreviation

    @pytest.mark.parametrize(
        "text",
        ["", "   ", None],
    )
    def test_empty_returns_none(self, text: str | None) -> None:
        assert Degree.from_text(text) is None

    def test_str_returns_full(self) -> None:
        d = Degree.from_text("Bachelor of Science")
        assert str(d) == "Bachelor of Science"
