"""Converter: LinkedInData → RenderCV YAML model."""

from __future__ import annotations

from typing import Any, override

from rendercv.schema.models.cv.cv import Cv
from rendercv.schema.models.cv.entries.education import EducationEntry
from rendercv.schema.models.cv.entries.experience import ExperienceEntry
from rendercv.schema.models.cv.entries.normal import NormalEntry
from rendercv.schema.models.cv.entries.one_line import OneLineEntry
from rendercv.schema.models.cv.entries.publication import PublicationEntry
from rendercv.schema.models.cv.social_network import SocialNetwork

from linkedinto.bullet_parser import parse_bullets
from linkedinto.converter import Converter
from linkedinto.date_parser import parse_linkedin_date
from linkedinto.domain import (
    AwardHonorRow,
    EducationRow,
    LanguageRow,
    LinkedInData,
    PositionRow,
    ProjectRow,
    PublicationRow,
    SkillRow,
)
from linkedinto.language_detector import is_programming_language
from linkedinto.url_extractor import extract_websites

SECTION_SUMMARY = "summary"
SECTION_EXPERIENCE = "experience"
SECTION_EDUCATION = "education"
SECTION_PROJECTS = "projects"
SECTION_PUBLICATIONS = "publications"
SECTION_AWARDS = "awards"
SECTION_LANGUAGES = "languages"
SECTION_TECHNOLOGIES = "technologies"
SECTION_SKILLS = "skills"

PROFICIENCY_ORDER: dict[str, int] = {
    "expert": 0,
    "advanced": 1,
    "intermediate": 2,
    "beginner": 3,
}


class RenderCvConverter(Converter):
    """Convert LinkedInData to a RenderCV YAML model."""

    requires = None  # takes raw LinkedInData directly

    @override
    def convert(self, data: LinkedInData) -> Cv:
        """Convert LinkedInData to a RenderCV YAML model."""
        if data.profile is None:
            return Cv(name="", sections={})

        p = data.profile
        cv_data: dict[str, Any] = {
            "name": f"{p.first_name or ''} {p.last_name or ''}".strip(),
            "headline": p.headline or p.occupation,
            "location": p.geo_location,
            "email": p.email_address,
            "phone": p.phone_number,
            "website": None,
            "social_networks": [],
            "sections": {},
        }

        parsed_websites = extract_websites(p.websites)
        if parsed_websites:
            cv_data["website"] = parsed_websites[0]

        # --- Social networks ---
        if p.linkedin:
            cv_data["social_networks"].append(
                SocialNetwork(network="LinkedIn", username=p.linkedin)
            )
        if p.twitter:
            cv_data["social_networks"].append(
                SocialNetwork(network="X", username=p.twitter)
            )

        # --- Summary section ---
        if p.summary:
            cv_data["sections"][SECTION_SUMMARY] = [p.summary]

        # --- Experience section ---
        if data.positions:
            cv_data["sections"][SECTION_EXPERIENCE] = [
                self._convert_position(row) for row in data.positions if row
            ]

        # --- Education section ---
        if data.education:
            cv_data["sections"][SECTION_EDUCATION] = [
                self._convert_education(row) for row in data.education if row
            ]

        # --- Projects section ---
        if data.projects:
            cv_data["sections"][SECTION_PROJECTS] = [
                self._convert_project(row) for row in data.projects if row
            ]

        # --- Publications section ---
        if data.publications:
            cv_data["sections"][SECTION_PUBLICATIONS] = [
                self._convert_publication(row) for row in data.publications if row
            ]

        # --- Awards section ---
        if data.honors:
            cv_data["sections"][SECTION_AWARDS] = [
                self._convert_award(row) for row in data.honors if row
            ]

        # --- Languages section ---
        if data.languages:
            cv_data["sections"][SECTION_LANGUAGES] = [
                self._convert_language(row) for row in data.languages if row
            ]

        # --- Skills section ---
        cv_data["sections"].update(self._build_skills(data.skills))

        return Cv(**cv_data)

    def _build_skills(self, skills: list[SkillRow]) -> dict[str, list[Any]]:
        """Split skills into programming languages (technologies) and non-programming skills."""
        prog_skills: list[str] = []
        non_prog_skills: list[tuple[str, str]] = []  # (name, proficiency)

        for s in skills:
            if s.name and is_programming_language(
                s.name, tiobe_override=self.tiobe_override
            ):
                prog_skills.append(s.name)
            elif s.name:
                non_prog_skills.append((s.name, s.proficiency or ""))

        sections: dict[str, list[Any]] = {}

        if prog_skills:
            sections[SECTION_TECHNOLOGIES] = [
                {"label": "Programming Languages", "details": ", ".join(prog_skills)}
            ]

        if non_prog_skills:
            non_prog_skills.sort(
                key=lambda x: PROFICIENCY_ORDER.get(
                    x[1].lower(), len(PROFICIENCY_ORDER)
                )
            )
            details = ", ".join(
                f"{name} ({level})" if level else name
                for name, level in non_prog_skills
            )
            sections[SECTION_SKILLS] = [{"label": "Skills", "details": details}]

        return sections

    @staticmethod
    def _convert_position(row: PositionRow) -> ExperienceEntry:
        summary, highlights = parse_bullets(row.description)
        return ExperienceEntry(
            company=row.company or "",
            position=row.position or "",
            location=row.location,
            start_date=parse_linkedin_date(row.started),
            end_date=parse_linkedin_date(row.ended),
            summary=summary or None,
            highlights=highlights,
        )

    @staticmethod
    def _convert_education(row: EducationRow) -> EducationEntry:
        return EducationEntry(
            institution=row.school or "",
            area=row.field or "",
            degree=row.degree,
            start_date=parse_linkedin_date(row.started),
            end_date=parse_linkedin_date(row.ended),
        )

    @staticmethod
    def _convert_project(row: ProjectRow) -> NormalEntry:
        summary, highlights = parse_bullets(row.description)
        return NormalEntry(
            name=row.name or row.title or "",
            date=parse_linkedin_date(row.started),
            summary=summary or None,
            highlights=highlights,
        )

    @staticmethod
    def _convert_publication(row: PublicationRow) -> PublicationEntry:
        return PublicationEntry(
            title=row.name or row.title or "",
            authors=[row.publisher] if row.publisher else [],
            summary=row.description,
            date=row.date,
        )

    @staticmethod
    def _convert_award(row: AwardHonorRow) -> OneLineEntry:
        return OneLineEntry(
            label=row.title or "",
            details=row.awarder or row.issuer or row.company or "",
        )

    @staticmethod
    def _convert_language(row: LanguageRow) -> OneLineEntry:
        return OneLineEntry(
            label=row.name or "",
            details=row.proficiency or "",
        )

    @override
    def validate(self, model: Cv) -> list[str]:
        """Validate RenderCV model.

        Checks:
        - CV name is present.
        - Social networks have valid entries.

        Returns:
            A list of validation error messages (empty = valid).
        """
        errors: list[str] = []

        if not model.name:
            errors.append("CV 'name' is empty or missing")

        for i, sn in enumerate(model.social_networks or []):
            if not sn.network:
                errors.append(f"Social network[{i}] missing 'network' name")
            if not sn.username:
                errors.append(f"Social network[{i}] missing 'username'")

        return errors
