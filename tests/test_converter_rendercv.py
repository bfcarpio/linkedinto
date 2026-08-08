"""Tests for RenderCV converter — consumes LinkedInData directly."""

from __future__ import annotations

from typing import cast, override

from rendercv.schema.models.cv.cv import Cv
from rendercv.schema.models.cv.entries.experience import ExperienceEntry

from linkedinto.converter_rendercv import RenderCvConverter
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
        """Programming languages go to technologies, others to skills."""
        converter = RenderCvConverter()
        result = converter.convert(full_profile_fixture())
        assert result.sections is not None and "technologies" in result.sections
        assert result.sections is not None and "skills" in result.sections

        tech_section = result.sections.get("technologies")
        assert tech_section is not None
        from typing import Any

        tech_entry: Any = tech_section[0]
        tech_detail: str = str(tech_entry.details)
        assert "Python" in tech_detail
        assert "TypeScript" in tech_detail

        skill_section = result.sections.get("skills")
        assert skill_section is not None
        skill_entry: Any = skill_section[0]
        skill_detail: str = str(skill_entry.details)
        assert "Project Management" in skill_detail

    def test_skills_grouped(self) -> None:
        """With a skill grouper set, one NormalEntry per category, no technologies."""

        class StubGrouper(Grouper):
            @override
            def group(self, skills: list[str]) -> dict[str, list[str]]:
                return {
                    PROGRAMMING_LANGUAGES: ["Python", "TypeScript"],
                    "Leadership": ["Project Management"],
                }

        from rendercv.schema.models.cv.entries.normal import NormalEntry

        converter = RenderCvConverter()
        converter.skill_grouper = StubGrouper()
        result = converter.convert(full_profile_fixture())

        assert result.sections is not None
        assert "technologies" not in result.sections
        skill_section = result.sections.get("skills")
        assert skill_section is not None
        entries = cast(list[NormalEntry], skill_section)
        assert [e.name for e in entries] == [
            PROGRAMMING_LANGUAGES,
            "Leadership",
        ]
        assert entries[0].highlights == ["Python", "TypeScript"]
        assert entries[1].highlights == ["Project Management"]

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
