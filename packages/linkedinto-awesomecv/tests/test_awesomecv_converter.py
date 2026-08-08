"""Tests for Awesome-CV converter — consumes LinkedInData directly."""

from __future__ import annotations

from typing import override

from linkedinto_awesomecv.converter import AwesomeCvConverter

from linkedinto.skill_grouper import PROGRAMMING_LANGUAGES, Grouper
from tests.fixtures.rendercv_fixtures import (
    full_profile_fixture,
    minimal_profile_fixture,
    partial_profile_fixture,
)


class TestAwesomeCvConverter:
    def test_convert_empty(self) -> None:
        """Partial (None profile) returns a valid .tex with empty name."""
        converter = AwesomeCvConverter()
        result = converter.convert(partial_profile_fixture())
        assert isinstance(result, str)
        assert "\\documentclass" in result
        assert "\\begin{document}" in result
        assert "\\name{}{}" in result

    def test_convert_basics(self) -> None:
        """Minimal profile produces name, email, and position lines."""
        converter = AwesomeCvConverter()
        result = converter.convert(minimal_profile_fixture())
        assert "\\name{John}{Smith}" in result
        assert "\\email{john@example.com}" in result
        assert "\\position{" in result

    def test_convert_work(self) -> None:
        """Full profile includes Experience section with Acme Corp."""
        converter = AwesomeCvConverter()
        result = converter.convert(full_profile_fixture())
        assert "\\cvsection{Experience}" in result
        assert "Acme Corp" in result
        assert "\\cventry" in result

    def test_convert_education(self) -> None:
        """Full profile includes Education section with MIT."""
        converter = AwesomeCvConverter()
        result = converter.convert(full_profile_fixture())
        assert "\\cvsection{Education}" in result
        assert "MIT" in result

    def test_skills(self) -> None:
        """Skills section contains cvskill entries; programming languages detected."""
        converter = AwesomeCvConverter()
        result = converter.convert(full_profile_fixture())
        assert "\\cvsection{Skills}" in result
        assert "\\cvskill" in result
        assert "Python" in result

    def test_skills_grouped(self) -> None:
        """With a StubGrouper, skills are split into categories."""

        class StubGrouper(Grouper):
            @override
            def group(self, skills: list[str]) -> dict[str, list[str]]:
                return {
                    PROGRAMMING_LANGUAGES: ["Python", "TypeScript"],
                    "Leadership": ["Project Management"],
                }

        converter = AwesomeCvConverter()
        converter.skill_grouper = StubGrouper()
        result = converter.convert(full_profile_fixture())
        assert "\\cvskill" in result
        assert "Programming Languages" in result
        assert "Leadership" in result
        assert "Python" in result

    def test_latex_escaping(self) -> None:
        """Special characters in company name are escaped."""
        from linkedinto.domain import LinkedInData, PositionRow, ProfileRow
        from linkedinto.email_utils import Email

        data = LinkedInData(
            profile=ProfileRow(
                first_name="Test",
                last_name="User",
                email_address=Email.from_raw("test@example.com"),
            ),
            positions=[
                PositionRow(
                    company="A&B Corp",
                    position="Dev",
                    started="2020-01",
                ),
            ],
        )
        converter = AwesomeCvConverter()
        result = converter.convert(data)
        assert r"A\&B Corp" in result

    def test_date_formatting(self) -> None:
        """ISO date 2023-09 renders as 'Sep. 2023'."""
        from linkedinto.degree import Degree
        from linkedinto.domain import EducationRow, LinkedInData, ProfileRow
        from linkedinto.email_utils import Email

        data = LinkedInData(
            profile=ProfileRow(
                first_name="Test",
                last_name="User",
                email_address=Email.from_raw("test@example.com"),
            ),
            education=[
                EducationRow(
                    school="MIT",
                    degree=Degree.from_text("BS"),
                    started="2020-09",
                    ended="2023-09",
                ),
            ],
        )
        converter = AwesomeCvConverter()
        result = converter.convert(data)
        assert "Sep. 2023" in result

    def test_validate(self) -> None:
        """Valid output passes validation, empty string fails."""
        converter = AwesomeCvConverter()
        valid = converter.convert(minimal_profile_fixture())
        assert converter.validate(valid) == []

        errors = converter.validate("")
        assert len(errors) > 0
        assert any("empty" in e.lower() for e in errors)

    def test_summary_newlines(self) -> None:
        """Single newlines in summary become LaTeX line breaks, not spaces."""
        from linkedinto.domain import LinkedInData, ProfileRow
        from linkedinto.email_utils import Email

        data = LinkedInData(
            profile=ProfileRow(
                first_name="Test",
                last_name="User",
                email_address=Email.from_raw("test@example.com"),
                summary="Line one\nLine two\nLine three",
            ),
        )
        converter = AwesomeCvConverter()
        result = converter.convert(data)
        assert "\\cvsection{Summary}" in result
        assert "Line one\\\\Line two\\\\Line three" in result

    def test_summary_bullets(self) -> None:
        """Bullet characters in summary are parsed into cvitems."""
        from linkedinto.domain import LinkedInData, ProfileRow
        from linkedinto.email_utils import Email

        data = LinkedInData(
            profile=ProfileRow(
                first_name="Test",
                last_name="User",
                email_address=Email.from_raw("test@example.com"),
                summary="Engineer with experience\n• Backend systems\n• Cloud architecture",
            ),
        )
        converter = AwesomeCvConverter()
        result = converter.convert(data)
        assert "\\cvsection{Summary}" in result
        assert "Engineer with experience" in result
        assert "\\begin{cvitems}" in result
        assert "\\item {Backend systems}" in result
        assert "\\item {Cloud architecture}" in result

    def test_summary_multi_paragraph_bullets(self) -> None:
        """Multiple bullet groups separated by paragraph breaks render as
        independent cvparagraph/cvitems blocks, not merged."""
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
                    "\u2022 Built platform serving 10M users\n"
                    "\u2022 Reduced costs by 40%"
                ),
            ),
        )
        converter = AwesomeCvConverter()
        result = converter.convert(data)
        assert "\\cvsection{Summary}" in result
        assert "Senior engineer." in result
        assert "Specializing in:" in result
        assert "Key achievements:" in result
        assert "\\item {Backend systems}" in result
        assert "\\item {Cloud architecture}" in result
        assert "\\item {Built platform serving 10M users}" in result
        assert "\\item {Reduced costs by 40\\%}" in result
        # "Key achievements:" should NOT be merged into a highlight item
        assert "\\item {Cloud architecture\\n\\nKey achievements:}" not in result

    def test_project_summary_rendered_before_bullets(self) -> None:
        """General text before bullets is rendered as the first cvitem."""
        from linkedinto.domain import LinkedInData, ProfileRow, ProjectRow
        from linkedinto.email_utils import Email

        data = LinkedInData(
            profile=ProfileRow(
                first_name="Test",
                last_name="User",
                email_address=Email.from_raw("test@example.com"),
            ),
            projects=[
                ProjectRow(
                    title="My App",
                    description=(
                        "A general summary paragraph.\n"
                        "\u2022 First bullet\n"
                        "\u2022 Second bullet"
                    ),
                    started="2023-01",
                    ended="2023-06",
                ),
            ],
        )
        converter = AwesomeCvConverter()
        result = converter.convert(data)
        assert "\\item {A general summary paragraph.}" in result
        assert "\\item {First bullet}" in result
        assert "\\item {Second bullet}" in result
