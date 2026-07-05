"""Tests for RenderCV converter."""

from __future__ import annotations

from linkedinto.converter_rendercv import RenderCvConverter
from linkedinto.models_jsonresume import Basics, JsonResume, Skill, Work
from linkedinto.models_rendercv import RenderCV


class TestRenderCvConverter:
    def test_convert_empty(self) -> None:
        converter = RenderCvConverter()
        result = converter.convert(JsonResume())
        assert isinstance(result, RenderCV)

    def test_convert_basics(self) -> None:
        resume = JsonResume(
            basics=Basics(
                name="John Smith",
                label="Engineer",
                email="john@example.com",
            )
        )
        converter = RenderCvConverter()
        result = converter.convert(resume)
        assert result.cv.name == "John Smith"
        assert result.cv.headline == "Engineer"
        assert result.cv.email == "john@example.com"

    def test_convert_work(self) -> None:
        resume = JsonResume(
            work=[Work(name="Acme", position="Dev", start_date="2020-03-01")]
        )
        converter = RenderCvConverter()
        result = converter.convert(resume)
        assert "experience" in result.cv.sections
        assert result.cv.sections["experience"][0]["company"] == "Acme"

    def test_skills_split(self) -> None:
        resume = JsonResume(
            skills=[
                Skill(name="Python", level="Expert"),
                Skill(name="Project Management", level="Expert"),
                Skill(name="TypeScript", level="Advanced"),
            ]
        )
        converter = RenderCvConverter()
        result = converter.convert(resume)
        # Python and TypeScript should be in technologies (programming languages)
        # Project Management should be in skills
        assert "technologies" in result.cv.sections
        assert "skills" in result.cv.sections
        tech_detail: str = str(result.cv.sections["technologies"][0]["details"])
        assert "Python" in tech_detail
        assert "TypeScript" in tech_detail
        skill_detail: str = str(result.cv.sections["skills"][0]["details"])
        assert "Project Management" in skill_detail
