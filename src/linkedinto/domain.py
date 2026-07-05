"""Domain types for parsed LinkedIn export data."""

from __future__ import annotations

from dataclasses import dataclass, field

from linkedinto.date_parser import parse_linkedin_date


@dataclass
class ProfileRow:
    first_name: str | None = None
    last_name: str | None = None
    address: str | None = None
    zip_code: str | None = None
    geo_location: str | None = None
    occupation: str | None = None
    summary: str | None = None
    industry: str | None = None
    country: str | None = None
    country_code: str | None = None
    email_address: str | None = None
    phone_number: str | None = None
    twitter: str | None = None
    linkedin: str | None = None
    websites: str | None = None
    headline: str | None = None


@dataclass
class PositionRow:
    company: str | None = None
    position: str | None = None
    location: str | None = None
    url: str | None = None
    started: str | None = None
    ended: str | None = None
    description: str | None = None


@dataclass
class EducationRow:
    school: str | None = None
    degree: str | None = None
    field: str | None = None
    started: str | None = None
    ended: str | None = None
    grade: str | None = None
    activities: str | None = None
    notes: str | None = None


@dataclass
class SkillRow:
    name: str | None = None
    proficiency: str | None = None
    count: int | None = None


@dataclass
class LanguageRow:
    name: str | None = None
    proficiency: str | None = None


@dataclass
class ProjectRow:
    title: str | None = None
    name: str | None = None
    description: str | None = None
    url: str | None = None
    started: str | None = None
    ended: str | None = None


@dataclass
class PublicationRow:
    name: str | None = None
    title: str | None = None
    publisher: str | None = None
    date: str | None = None
    url: str | None = None
    description: str | None = None


@dataclass
class CertificationRow:
    name: str | None = None
    issuer: str | None = None
    date: str | None = None
    url: str | None = None


@dataclass
class AwardHonorRow:
    title: str | None = None
    name: str | None = None
    awarder: str | None = None
    issuer: str | None = None
    company: str | None = None
    date: str | None = None
    description: str | None = None


@dataclass
class RecommendationRow:
    recommender: str | None = None
    recommendation_body: str | None = None
    status: str | None = None


@dataclass
class InterestRow:
    name: str | None = None


@dataclass
class VolunteerRow:
    name: str | None = None
    company: str | None = None
    position: str | None = None
    role: str | None = None
    started: str | None = None
    ended: str | None = None
    description: str | None = None


@dataclass
class LinkedInData:
    """Container bundling all parsed LinkedIn CSV sections."""

    profile: ProfileRow | None = None
    positions: list[PositionRow] = field(default_factory=list)
    education: list[EducationRow] = field(default_factory=list)
    skills: list[SkillRow] = field(default_factory=list)
    languages: list[LanguageRow] = field(default_factory=list)
    projects: list[ProjectRow] = field(default_factory=list)
    publications: list[PublicationRow] = field(default_factory=list)
    certifications: list[CertificationRow] = field(default_factory=list)
    honors: list[AwardHonorRow] = field(default_factory=list)
    recommendations: list[RecommendationRow] = field(default_factory=list)
    interests: list[InterestRow] = field(default_factory=list)
    volunteer: list[VolunteerRow] = field(default_factory=list)

    def sort(self) -> None:
        """Sort date-based entries in-place, newest first.

        Uses ``parse_linkedin_date()`` to canonicalize month-name
        formats (e.g. "January 2020") so they sort correctly.
        """

        def _date_key(raw: str | None) -> str:
            return parse_linkedin_date(raw) or ""

        self.positions.sort(key=lambda p: _date_key(p.started), reverse=True)
        self.education.sort(key=lambda e: _date_key(e.started), reverse=True)
        self.volunteer.sort(key=lambda v: _date_key(v.started), reverse=True)
