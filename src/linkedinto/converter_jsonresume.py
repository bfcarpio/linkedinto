"""Converter: parsed LinkedIn data → JSON Resume v1.0.0 model."""

from __future__ import annotations

from typing import override

from linkedinto.bullet_parser import parse_bullets
from linkedinto.converter import Converter
from linkedinto.date_parser import parse_linkedin_date
from linkedinto.domain import (
    EducationRow,
    LinkedInData,
    PositionRow,
    ProjectRow,
    VolunteerRow,
)
from linkedinto.models_jsonresume import (
    Award,
    Basics,
    Certificate,
    Education,
    Interest,
    JsonResume,
    Language,
    Location,
    Profile,
    Project,
    Publication,
    Reference,
    Skill,
    Volunteer,
    Work,
)

NETWORK_LINKEDIN = "LinkedIn"
NETWORK_TWITTER = "Twitter"


class JsonResumeConverter(Converter):
    """Convert parsed LinkedIn data to a JSON Resume v1.0.0 model."""

    requires = None  # takes raw LinkedInData

    @override
    def convert(self, data: LinkedInData) -> JsonResume:
        """Convert LinkedIn data to JSON Resume."""
        resume = JsonResume()

        if data.profile is not None:
            p = data.profile
            location: Location | None = None
            if p.geo_location:
                location = Location(city=p.geo_location)

            profiles: list[Profile] = []
            if p.linkedin:
                profiles.append(Profile(network=NETWORK_LINKEDIN, username=p.linkedin))
            if p.twitter:
                profiles.append(Profile(network=NETWORK_TWITTER, username=p.twitter))

            name = None
            if p.first_name or p.last_name:
                name = f"{p.first_name or ''} {p.last_name or ''}".strip()

            resume.basics = Basics(
                name=name,
                label=p.headline or p.occupation,
                email=p.email_address,
                phone=p.phone_number,
                summary=p.summary,
                location=location,
                profiles=profiles,
            )

        resume.work = [self._convert_position(p) for p in data.positions]
        resume.education = [self._convert_education(e) for e in data.education]
        resume.skills = [Skill(name=s.name, level=s.proficiency) for s in data.skills]
        resume.languages = [
            Language(language=lang.name, fluency=lang.proficiency)
            for lang in data.languages
        ]
        resume.projects = [self._convert_project(p) for p in data.projects]
        resume.publications = [
            Publication(name=p.name, publisher=p.publisher, summary=p.description)
            for p in data.publications
        ]
        resume.certificates = [
            Certificate(name=c.name, issuer=c.issuer, date=c.date)
            for c in data.certifications
        ]
        resume.awards = [
            Award(title=a.title, awarder=a.awarder, summary=a.description)
            for a in data.honors
        ]
        resume.references = [
            Reference(name=r.recommender, reference=r.recommendation_body)
            for r in data.recommendations
        ]
        resume.interests = [Interest(name=i.name) for i in data.interests]
        resume.volunteer = self._convert_volunteer(data.volunteer)

        return resume

    @override
    def validate(self, model: JsonResume) -> list[str]:
        """Validate JSON Resume model.

        Checks:
        - Basics are present (name, email, summary).
        - No empty work/education entries with missing required fields.

        Returns:
            A list of validation error messages (empty = valid).
        """
        errors: list[str] = []

        if model.basics is None:
            errors.append("Missing 'basics': no profile data converted")
        else:
            if not model.basics.name:
                errors.append("Basics 'name' is empty or missing")
            if not model.basics.email:
                errors.append("Basics 'email' is empty or missing")

        # Check work entries for required fields
        for i, w in enumerate(model.work):
            if not w.name:
                errors.append(f"Work[{i}] missing 'name' (company)")
            if not w.position:
                errors.append(f"Work[{i}] missing 'position' (title)")

        # Check education entries
        for i, e in enumerate(model.education):
            if not e.institution:
                errors.append(f"Education[{i}] missing 'institution'")

        return errors

    @staticmethod
    def _convert_position(pos: PositionRow) -> Work:
        summary, highlights = parse_bullets(pos.description)
        return Work(
            name=pos.company,
            position=pos.position,
            location=pos.location,
            url=pos.url,
            start_date=parse_linkedin_date(pos.started),
            end_date=parse_linkedin_date(pos.ended),
            summary=summary or None,
            highlights=highlights,
        )

    @staticmethod
    def _convert_education(edu: EducationRow) -> Education:
        courses: list[str] = []
        if edu.activities:
            courses = [a.strip() for a in edu.activities.split(",") if a.strip()]
        return Education(
            institution=edu.school,
            area=edu.field,
            study_type=edu.degree,
            start_date=parse_linkedin_date(edu.started),
            end_date=parse_linkedin_date(edu.ended),
            score=edu.grade,
            courses=courses,
        )

    @staticmethod
    def _convert_project(proj: ProjectRow) -> Project:
        summary, highlights = parse_bullets(proj.description)
        return Project(
            name=proj.name or proj.title,
            description=summary or None,
            highlights=highlights,
            url=proj.url,
            start_date=parse_linkedin_date(proj.started),
            end_date=parse_linkedin_date(proj.ended),
        )

    @staticmethod
    def _convert_volunteer(vols: list[VolunteerRow]) -> list[Volunteer]:
        result: list[Volunteer] = []
        for v in vols:
            summary, highlights = parse_bullets(v.description)
            result.append(
                Volunteer(
                    organization=v.name,
                    position=v.position,
                    start_date=parse_linkedin_date(v.started),
                    end_date=parse_linkedin_date(v.ended),
                    summary=summary or None,
                    highlights=highlights,
                )
            )
        return result
