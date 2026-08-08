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
        assert data.profile.email_address is not None
        assert data.profile.email_address.address == "john@example.com"
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

    def test_parse_projects_multi_csv(self, make_zip) -> None:
        """Multi-project CSV: each row becomes a separate ProjectRow with title."""
        csv = (
            "Title,Description,Url,Started On,Finished On\n"
            "Project Alpha,Built an alpha app,https://alpha.dev,2023-01,2023-06\n"
            "Project Beta,Built a beta app,https://beta.dev,2023-07,2023-12\n"
        )
        path = make_zip({"Projects.csv": csv})
        parser = LinkedinZipParser()
        data = parser.parse(path)
        assert len(data.projects) == 2
        assert data.projects[0].title == "Project Alpha"
        assert data.projects[1].title == "Project Beta"
        assert data.projects[0].url == "https://alpha.dev"
        assert data.projects[0].started == "2023-01"
        assert data.projects[0].ended == "2023-06"
