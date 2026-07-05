"""Tests for JSON Resume converter."""

from __future__ import annotations

from linkedinto.converter_jsonresume import JsonResumeConverter
from linkedinto.domain import (
    EducationRow,
    LinkedInData,
    PositionRow,
    ProfileRow,
    SkillRow,
)
from linkedinto.models_jsonresume import JsonResume


def _minimal_data() -> LinkedInData:
    return LinkedInData(
        profile=ProfileRow(
            first_name="John",
            last_name="Smith",
            headline="Engineer",
            email_address="john@example.com",
        ),
        positions=[
            PositionRow(
                company="Acme", position="Dev", started="2020-03", ended="2024-06"
            ),
        ],
        education=[
            EducationRow(school="MIT", degree="BS", field="CS", started="2016-09"),
        ],
        skills=[
            SkillRow(name="Python", proficiency="Expert"),
            SkillRow(name="React", proficiency="Advanced"),
        ],
    )


class TestJsonResumeConverter:
    def test_convert_basics(self) -> None:
        data = _minimal_data()
        converter = JsonResumeConverter()
        resume = converter.convert(data)
        assert isinstance(resume, JsonResume)
        assert resume.basics is not None
        assert resume.basics.name == "John Smith"
        assert resume.basics.label == "Engineer"
        assert resume.basics.email == "john@example.com"

    def test_convert_work(self) -> None:
        data = _minimal_data()
        converter = JsonResumeConverter()
        resume = converter.convert(data)
        assert len(resume.work) == 1
        assert resume.work[0].name == "Acme"
        assert resume.work[0].position == "Dev"
        assert resume.work[0].start_date == "2020-03-01"
        assert resume.work[0].end_date == "2024-06-01"

    def test_convert_education(self) -> None:
        data = _minimal_data()
        converter = JsonResumeConverter()
        resume = converter.convert(data)
        assert len(resume.education) == 1
        assert resume.education[0].institution == "MIT"
        assert resume.education[0].area == "CS"
        assert resume.education[0].study_type == "BS"

    def test_convert_skills(self) -> None:
        data = _minimal_data()
        converter = JsonResumeConverter()
        resume = converter.convert(data)
        assert len(resume.skills) == 2
        python_skill = next(s for s in resume.skills if s.name == "Python")
        assert python_skill.level == "Expert"

    def test_sort_positions_by_date(self) -> None:
        """Positions are sorted newest-first by started date."""
        data = LinkedInData()
        data.positions = [
            PositionRow(company="Old Corp", started="Jan 2018"),
            PositionRow(company="New Corp", started="Mar 2020"),
            PositionRow(company="Mid Corp", started="Feb 2019"),
            PositionRow(company="Z Co", started=None),
        ]
        data.sort()

        assert data.positions[0].company == "New Corp"  # newest first
        assert data.positions[1].company == "Mid Corp"
        assert data.positions[2].company == "Old Corp"
        assert data.positions[3].company == "Z Co"  # None sorts last
