"""Tests for LinkedIn ZIP parser."""

from __future__ import annotations

from pathlib import Path

import pytest

from linkedinto.domain import LinkedInData
from linkedinto.exceptions import LinkedInParserError
from linkedinto.parser import LinkedinZipParser


class TestLinkedinZipParser:
    def test_parse_valid_zip(self, sample_csv_zip: Path) -> None:
        parser = LinkedinZipParser()
        data = parser.parse(sample_csv_zip)
        assert isinstance(data, LinkedInData)
        assert data.profile is not None
        assert data.profile.first_name == "John"
        assert data.profile.last_name == "Smith"
        assert len(data.skills) == 2
        assert data.skills[0].name == "Python"
        assert len(data.languages) == 2

    def test_parse_profile(self, sample_csv_zip: Path) -> None:
        parser = LinkedinZipParser()
        data = parser.parse(sample_csv_zip)
        assert data.profile is not None
        assert data.profile.occupation == "Software Eng."
        assert data.profile.email_address == "john@example.com"
        assert data.profile.linkedin == "https://linkedin.com/in/john"
        assert data.profile.headline == "Senior Engineer"

    def test_parse_skills(self, sample_csv_zip: Path) -> None:
        parser = LinkedinZipParser()
        data = parser.parse(sample_csv_zip)
        names = [s.name for s in data.skills]
        assert "Python" in names
        assert "React" in names
        assert data.skills[0].proficiency == "Expert"
        assert data.skills[0].count is not None
        assert data.skills[0].count == 5

    def test_parse_languages(self, sample_csv_zip: Path) -> None:
        parser = LinkedinZipParser()
        data = parser.parse(sample_csv_zip)
        names = [lang.name for lang in data.languages]
        assert "English" in names
        assert "Spanish" in names

    def test_missing_file_raises_error(self) -> None:
        parser = LinkedinZipParser()
        with pytest.raises(LinkedInParserError, match="does not exist"):
            parser.parse("/tmp/nonexistent.zip")

    def test_bad_zip_raises_error(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.zip"
        path.write_text("not a zip file")
        parser = LinkedinZipParser()
        with pytest.raises(LinkedInParserError, match="malformed"):
            parser.parse(path)
