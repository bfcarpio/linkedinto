"""Tests for LinkedIn ZIP parser."""

from __future__ import annotations

import os
import tempfile
import zipfile
from pathlib import Path

import pytest

from linkedinto.domain import LinkedInData
from linkedinto.exceptions import LinkedInParserError
from linkedinto.parser import LinkedinZipParser


def _make_zip(content: str) -> Path:
    """Create a temporary ZIP file with a single CSV."""
    fd, path = tempfile.mkstemp(suffix=".zip")
    os.close(fd)
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("LinkedIn_Export.csv", content)
    return Path(path)


SAMPLE_CSV = """Profile.csv,First Name,Last Name,Occupation,Summary,Country,EmailAddress,LinkedIn,Headline
Profile.csv,John,Smith,Software Eng.,Full-stack dev,United States,john@example.com,https://linkedin.com/in/john,Senior Engineer
Skills.csv,Name,Proficiency,Count
Skills.csv,Python,Expert,5
Skills.csv,React,Advanced,3
Languages.csv,Name,Proficiency
Languages.csv,English,Native or bilingual
Languages.csv,Spanish,Professional working
"""


class TestLinkedinZipParser:
    def test_parse_valid_zip(self) -> None:
        path = _make_zip(SAMPLE_CSV)
        parser = LinkedinZipParser()
        data = parser.parse(path)
        assert isinstance(data, LinkedInData)
        assert data.profile is not None
        assert data.profile.first_name == "John"
        assert data.profile.last_name == "Smith"
        assert len(data.skills) == 2
        assert data.skills[0].name == "Python"
        assert len(data.languages) == 2
        path.unlink()

    def test_parse_profile(self) -> None:
        path = _make_zip(SAMPLE_CSV)
        parser = LinkedinZipParser()
        data = parser.parse(path)
        assert data.profile is not None
        assert data.profile.occupation == "Software Eng."
        assert data.profile.email_address == "john@example.com"
        assert data.profile.linkedin == "https://linkedin.com/in/john"
        assert data.profile.headline == "Senior Engineer"
        path.unlink()

    def test_parse_skills(self) -> None:
        path = _make_zip(SAMPLE_CSV)
        parser = LinkedinZipParser()
        data = parser.parse(path)
        names = [s.name for s in data.skills]
        assert "Python" in names
        assert "React" in names
        assert data.skills[0].proficiency == "Expert"
        assert data.skills[0].count is not None
        assert data.skills[0].count == 5
        path.unlink()

    def test_parse_languages(self) -> None:
        path = _make_zip(SAMPLE_CSV)
        parser = LinkedinZipParser()
        data = parser.parse(path)
        names = [lang.name for lang in data.languages]
        assert "English" in names
        assert "Spanish" in names
        path.unlink()

    def test_missing_file_raises_error(self) -> None:
        parser = LinkedinZipParser()
        with pytest.raises(LinkedInParserError, match="does not exist"):
            parser.parse("/tmp/nonexistent.zip")

    def test_bad_zip_raises_error(self) -> None:
        fd, path_str = tempfile.mkstemp(suffix=".zip")
        os.close(fd)
        path = Path(path_str)
        path.write_text("not a zip file")
        parser = LinkedinZipParser()
        with pytest.raises(LinkedInParserError, match="malformed"):
            parser.parse(path)
        path.unlink()
