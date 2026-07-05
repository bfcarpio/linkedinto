"""Test fixtures for RenderCV converter tests — hand-crafted LinkedInData objects."""

from __future__ import annotations

from linkedinto.domain import (
    AwardHonorRow,
    EducationRow,
    LanguageRow,
    LinkedInData,
    PositionRow,
    ProfileRow,
    ProjectRow,
    PublicationRow,
    SkillRow,
)

# Scenario: all fields populated (maps to current FULL_RESUME)
FULL_PROFILE: ProfileRow = ProfileRow(
    first_name="John",
    last_name="Smith",
    headline="Senior Software Engineer",
    occupation="Software Engineer",
    geo_location="San Francisco, CA",
    email_address="john@example.com",
    phone_number="+1 650-555-1234",
    summary="Full-stack engineer with 10 years experience",
    linkedin="johnsmith",
    twitter="johnsmith_dev",
    websites="[COMPANY: https://company.com, PORTFOLIO: https://portfolio.com]",
)

FULL_POSITIONS: list[PositionRow] = [
    PositionRow(
        company="Acme Corp",
        position="Senior Dev",
        location="San Francisco, CA",
        url="https://acme.com",
        started="2020-03",
        ended="2024-06",
        description="\u2022 Led team of 5 engineers\n\u2022 Architected microservices platform",
    ),
]

FULL_EDUCATION: list[EducationRow] = [
    EducationRow(
        school="MIT",
        degree="BS",
        field="Computer Science",
        started="2016-09",
        ended="2020-06",
    ),
]

FULL_SKILLS: list[SkillRow] = [
    SkillRow(name="Python", proficiency="Expert"),
    SkillRow(name="TypeScript", proficiency="Advanced"),
    SkillRow(name="React", proficiency="Advanced"),
    SkillRow(name="Rust", proficiency="Intermediate"),
    SkillRow(name="Project Management", proficiency="Expert"),
    SkillRow(name="Public Speaking", proficiency="Intermediate"),
]

FULL_LANGUAGES: list[LanguageRow] = [
    LanguageRow(name="English", proficiency="Native or bilingual"),
    LanguageRow(name="Spanish", proficiency="Professional working"),
]

FULL_PROJECTS: list[ProjectRow] = [
    ProjectRow(
        name="My Project",
        title="My Project",
        description="\u2022 Built a thing\n\u2022 Deployed to production",
        url="https://github.com/myproject",
        started="2023-01",
    ),
]

FULL_PUBLICATIONS: list[PublicationRow] = [
    PublicationRow(
        name="Research Paper",
        title="Research Paper",
        publisher="ACM",
        date="2024-03-15",
        description="A paper about distributed systems",
    ),
]

FULL_HONORS: list[AwardHonorRow] = [
    AwardHonorRow(
        title="Best Paper Award",
        awarder="ACM",
        issuer="ACM SIGCOMM",
        company="",
        date="2024-03",
        description="Awarded at the conference",
    ),
]


def full_profile_fixture() -> LinkedInData:
    """LinkedInData with all fields populated."""
    return LinkedInData(
        profile=FULL_PROFILE,
        positions=FULL_POSITIONS,
        education=FULL_EDUCATION,
        skills=FULL_SKILLS,
        languages=FULL_LANGUAGES,
        projects=FULL_PROJECTS,
        publications=FULL_PUBLICATIONS,
        honors=FULL_HONORS,
    )


def partial_profile_fixture() -> LinkedInData:
    """LinkedInData with no profile (None) and empty lists — malformed export scenario."""
    return LinkedInData(
        profile=None,
        positions=[],
        education=[],
        skills=[],
        languages=[],
        projects=[],
        publications=[],
        honors=[],
    )


def minimal_profile_fixture() -> LinkedInData:
    """LinkedInData with only basic profile fields, no sections."""
    return LinkedInData(
        profile=ProfileRow(
            first_name="John",
            last_name="Smith",
            headline="Senior Software Engineer",
            occupation="Software Engineer",
            email_address="john@example.com",
        ),
        positions=[],
        education=[],
        skills=[],
    )


def unsorted_dates_fixture() -> LinkedInData:
    """Positions and education in unsorted order to test sort() works."""
    return LinkedInData(
        profile=ProfileRow(first_name="Test", last_name="User"),
        positions=[
            PositionRow(company="Older Co", position="Junior", started="2018-01"),
            PositionRow(company="Newer Co", position="Senior", started="2022-01"),
        ],
        education=[
            EducationRow(school="Old School", field="BA", started="2014-09"),
            EducationRow(school="New School", field="MA", started="2018-09"),
        ],
    )


def multiple_websites_fixture() -> LinkedInData:
    """Profile with bracket-format websites."""
    return LinkedInData(
        profile=ProfileRow(
            first_name="Jane",
            last_name="Doe",
            headline="Engineer",
            websites="[COMPANY: https://company.com, BLOG: https://blog.com, PORTFOLIO: https://portfolio.com]",
        ),
    )


def no_websites_fixture() -> LinkedInData:
    """Profile with None/empty websites field."""
    return LinkedInData(
        profile=ProfileRow(
            first_name="Jane",
            last_name="Doe",
            headline="Engineer",
            websites=None,
        ),
    )
