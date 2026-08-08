"""Tests for RenderCV converter — consumes LinkedInData directly."""

from __future__ import annotations

from typing import Any, cast, override

from linkedinto_rendercv.converter import RenderCvConverter
from rendercv.schema.models.cv.cv import Cv
from rendercv.schema.models.cv.entries.experience import ExperienceEntry
from rendercv.schema.models.cv.entries.one_line import OneLineEntry

from linkedinto.skill_grouper import PROGRAMMING_LANGUAGES, Grouper
from tests.fixtures.rendercv_fixtures import (
    full_profile_fixture,
    minimal_profile_fixture,
    multiple_websites_fixture,
    no_websites_fixture,
    partial_profile_fixture,
)


class TestRenderCvConverter:
    def test_convert_empty(self) -> None:
        """Partial (None profile) returns empty but valid RenderCV."""
        converter = RenderCvConverter()
        result = converter.convert(partial_profile_fixture())
        assert isinstance(result, Cv)
        assert result.name == ""

    def test_convert_basics(self) -> None:
        """Minimal profile populates header fields."""
        converter = RenderCvConverter()
        result = converter.convert(minimal_profile_fixture())
        assert result.name == "John Smith"
        assert result.headline == "Senior Software Engineer"
        assert result.email == "john@example.com"

    def test_convert_work(self) -> None:
        """Full profile includes experience section."""
        converter = RenderCvConverter()
        result = converter.convert(full_profile_fixture())
        assert result.sections is not None and "experience" in result.sections
        experience_section = result.sections.get("experience")
        assert experience_section is not None
        # result.sections is dict[str, list[Any]], and experience_section is list[Any]
        experience_entry = cast(ExperienceEntry, experience_section[0])
        assert experience_entry.company == "Acme Corp"

    def test_skills_split(self) -> None:
        """All skills go to a single skills section as OneLineEntry entries."""
        converter = RenderCvConverter()
        result = converter.convert(full_profile_fixture())
        assert result.sections is not None and "skills" in result.sections
        assert "technologies" not in result.sections

        skill_section = result.sections.get("skills")
        assert skill_section is not None
        assert len(skill_section) == 2

        prog_entry: Any = skill_section[0]
        assert prog_entry.label == "Programming Languages"
        assert "Python" in str(prog_entry.details)
        assert "TypeScript" in str(prog_entry.details)

        skills_entry: Any = skill_section[1]
        assert skills_entry.label == "Skills"
        assert "Project Management" in str(skills_entry.details)

    def test_skills_grouped(self) -> None:
        """With a skill grouper set, all groups become OneLineEntry in skills."""

        class StubGrouper(Grouper):
            @override
            def group(self, skills: list[str]) -> dict[str, list[str]]:
                return {
                    PROGRAMMING_LANGUAGES: ["Python", "TypeScript"],
                    "Leadership": ["Project Management"],
                }

        converter = RenderCvConverter()
        converter.skill_grouper = StubGrouper()
        result = converter.convert(full_profile_fixture())

        assert result.sections is not None
        assert "technologies" not in result.sections

        skill_section = result.sections.get("skills")
        assert skill_section is not None
        entries = cast(list[OneLineEntry], skill_section)
        assert len(entries) == 2
        assert [e.label for e in entries] == ["Programming Languages", "Leadership"]
        assert entries[0].details == "Python, TypeScript"
        assert entries[1].details == "Project Management"

    def test_website_population(self) -> None:
        """Bracket-format websites populates first URL as cv.website."""
        converter = RenderCvConverter()
        result = converter.convert(multiple_websites_fixture())
        assert str(result.website) == "https://company.com/"

    def test_website_is_none(self) -> None:
        """None/empty websites field results in None website."""
        converter = RenderCvConverter()
        result = converter.convert(no_websites_fixture())
        assert result.website is None

    def test_summary_bullets(self) -> None:
        """Summary with bullets is split into separate text entries."""
        from linkedinto.domain import LinkedInData, ProfileRow
        from linkedinto.email_utils import Email

        data = LinkedInData(
            profile=ProfileRow(
                first_name="Test",
                last_name="User",
                email_address=Email.from_raw("test@example.com"),
                summary=(
                    "Senior engineer.\n\n"
                    "Specializing in:\n"
                    "\u2022 Backend systems\n"
                    "\u2022 Cloud architecture\n\n"
                    "Key achievements:\n"
                    "\u2022 Built platform serving 10M users"
                ),
            ),
        )
        converter = RenderCvConverter()
        result = converter.convert(data)
        summary = result.sections.get("summary", [])
        assert len(summary) >= 5  # text + 2 bullets + text + 1 bullet
        assert "Senior engineer." in summary
        assert "\u2022 Backend systems" in summary
        assert "\u2022 Cloud architecture" in summary
        assert "Key achievements:" in summary
        assert "\u2022 Built platform serving 10M users" in summary
