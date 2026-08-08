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
from linkedinto.url_extractor import extract_websites
from linkedinto_jsonresume.models import (
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


def _is_platform_url(url: str) -> bool:
    """Return True if ``url`` points to a known code-hosting platform."""
    return any(
        domain in url
        for domain in ("github.com/", "gitlab.com/", "bitbucket.org/", "codeberg.org/")
    )


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

            # Detect platform profiles from website URLs
            parsed_websites = extract_websites(p.websites)
            for url in parsed_websites:
                if "github.com/" in url:
                    username = url.rstrip("/").split("github.com/")[-1].split("/")[0]
                    if username:
                        profiles.append(
                            Profile(network="GitHub", username=username, url=url)
                        )
                elif "gitlab.com/" in url:
                    username = url.rstrip("/").split("gitlab.com/")[-1].split("/")[0]
                    if username:
                        profiles.append(
                            Profile(network="GitLab", username=username, url=url)
                        )
                elif "bitbucket.org/" in url:
                    username = url.rstrip("/").split("bitbucket.org/")[-1].split("/")[0]
                    if username:
                        profiles.append(
                            Profile(network="Bitbucket", username=username, url=url)
                        )
                elif "codeberg.org/" in url:
                    username = url.rstrip("/").split("codeberg.org/")[-1].split("/")[0]
                    if username:
                        profiles.append(
                            Profile(network="Codeberg", username=username, url=url)
                        )

            name = None
            if p.first_name or p.last_name:
                name = f"{p.first_name or ''} {p.last_name or ''}".strip()

            resume.basics = Basics(
                name=name,
                label=p.headline or p.occupation,
                email=p.email_address.address if p.email_address else None,
                phone=p.phone_number.international if p.phone_number else None,
                url=next((u for u in parsed_websites if not _is_platform_url(u)), None),
                summary=p.summary,
                location=location,
                profiles=profiles,
            )

        resume.work = [self._convert_position(p) for p in data.positions]
        resume.education = [self._convert_education(e) for e in data.education]
        if self.skill_groups is None and self.skill_grouper is not None:
            skill_names = [s.name for s in data.skills if s.name]
            self.skill_groups = self.skill_grouper.group(skill_names)
        if self.skill_groups is not None:
            resume.skills = [
                Skill(name=category, keywords=skills)
                for category, skills in self.skill_groups.items()
            ]
        else:
            resume.skills = [
                Skill(name=s.name, level=s.proficiency) for s in data.skills
            ]
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
        - Basics are present (name, summary).
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
            study_type=edu.degree.full if edu.degree else None,
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
