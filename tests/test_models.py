"""Tests for JSON Resume and RenderCV Pydantic models."""

from __future__ import annotations

import pytest
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
from rendercv.schema.models.cv.cv import Cv
from rendercv.schema.models.cv.entries.education import EducationEntry
from rendercv.schema.models.cv.entries.experience import ExperienceEntry
from rendercv.schema.models.cv.entries.normal import NormalEntry
from rendercv.schema.models.cv.entries.one_line import OneLineEntry
from rendercv.schema.models.cv.entries.publication import PublicationEntry
from rendercv.schema.models.cv.social_network import SocialNetwork

# (model class, constructor kwargs, field->expected) for the JSON Resume
# round-trip cases. Fields prefixed "len(" assert a list length; dotted fields
# descend a nested model attribute; otherwise the attribute is read directly.
JSONRESUME_ROUND_TRIP = [
    (
        Basics,
        {
            "name": "John Smith",
            "label": "Software Engineer",
            "email": "john@example.com",
            "location": Location(city="San Francisco", country_code="US"),
        },
        {
            "name": "John Smith",
            "label": "Software Engineer",
            "email": "john@example.com",
            "location.city": "San Francisco",
        },
    ),
    (
        Work,
        {
            "name": "Acme Corp",
            "position": "Senior Dev",
            "start_date": "2020-03-01",
            "highlights": ["Built payment gateway", "Reduced latency"],
        },
        {
            "name": "Acme Corp",
            "position": "Senior Dev",
            "start_date": "2020-03-01",
            "len(highlights)": 2,
        },
    ),
    (
        Education,
        {
            "institution": "MIT",
            "area": "Computer Science",
            "study_type": "BS",
            "start_date": "2016-09-01",
            "end_date": "2020-06-01",
        },
        {"institution": "MIT", "area": "Computer Science"},
    ),
    (
        Skill,
        {"name": "Python", "level": "Expert", "keywords": ["Django", "FastAPI"]},
        {"name": "Python", "len(keywords)": 2},
    ),
    (Language, {"language": "English", "fluency": "Native"}, {"language": "English"}),
    (
        Project,
        {
            "name": "My App",
            "description": "A cool app",
            "highlights": ["Won award"],
            "url": "https://example.com",
        },
        {"name": "My App", "url": "https://example.com"},
    ),
    (
        Publication,
        {
            "name": "Research Paper",
            "publisher": "IEEE",
            "authors": ["John Smith", "Jane Doe"],
        },
        {"name": "Research Paper", "len(authors)": 2},
    ),
    (
        Certificate,
        {"name": "AWS Certified", "issuer": "Amazon", "date": "2023-01-01"},
        {"name": "AWS Certified"},
    ),
    (
        Award,
        {"title": "Best Paper", "awarder": "IEEE", "date": "2023-06-01"},
        {"title": "Best Paper"},
    ),
    (
        Reference,
        {"name": "Jane Doe", "reference": "Great colleague"},
        {"name": "Jane Doe"},
    ),
    (
        Volunteer,
        {
            "organization": "Charity Org",
            "position": "Volunteer",
            "highlights": ["Helped organize event"],
        },
        {"organization": "Charity Org"},
    ),
    (
        Interest,
        {"name": "Machine Learning", "keywords": ["NLP", "Computer Vision"]},
        {"name": "Machine Learning"},
    ),
]

RENDERCV_ROUND_TRIP = [
    (
        ExperienceEntry,
        {
            "company": "Acme Corp",
            "position": "Senior Dev",
            "start_date": "2020-03",
            "highlights": ["Built feature"],
        },
        {"company": "Acme Corp", "len(highlights)": 1},
    ),
    (
        EducationEntry,
        {"institution": "MIT", "area": "CS", "degree": "BS"},
        {"institution": "MIT"},
    ),
    (NormalEntry, {"name": "Project X", "summary": "A project"}, {"name": "Project X"}),
    (
        PublicationEntry,
        {"title": "Paper", "authors": ["John"], "journal": "Journal"},
        {"title": "Paper", "journal": "Journal"},
    ),
    (OneLineEntry, {"label": "Python", "details": "Expert"}, {"label": "Python"}),
]


def _assert_round_trip(model_cls, kwargs, checks) -> None:
    """model_dump(exclude_none=True) -> model_validate, then assert ``checks``."""
    model = model_cls(**kwargs)
    data = model.model_dump(exclude_none=True)
    restored = model_cls.model_validate(data)
    for field, expected in checks.items():
        if field.startswith("len("):
            attr = field[4:-1]
            assert len(getattr(restored, attr) or []) == expected
        elif "." in field:
            obj_attr, nested_attr = field.split(".", 1)
            assert getattr(getattr(restored, obj_attr), nested_attr) == expected
        else:
            assert getattr(restored, field) == expected


class TestJsonResumeModels:
    """Test JSON Resume model creation and serialization."""

    def test_empty_json_resume_has_default_lists(self) -> None:
        """A JsonResume with no fields should contain default empty lists."""
        resume = JsonResume()
        data = resume.model_dump(exclude_none=True)
        assert data["work"] == []
        assert data["education"] == []
        assert data["skills"] == []

    @pytest.mark.parametrize(
        "model_cls,kwargs,checks",
        JSONRESUME_ROUND_TRIP,
        ids=[c[0].__name__ for c in JSONRESUME_ROUND_TRIP],
    )
    def test_jsonresume_round_trip(self, model_cls, kwargs, checks) -> None:
        """Each JSON Resume model round-trips through dump/validate."""
        _assert_round_trip(model_cls, kwargs, checks)

    def test_profile_serialization(self) -> None:
        profile = Profile(network="LinkedIn", username="johnsmith")
        data = profile.model_dump(exclude_none=True)
        assert data["network"] == "LinkedIn"
        assert data["username"] == "johnsmith"

    def test_full_json_resume(self) -> None:
        resume = JsonResume(
            basics=Basics(name="John Smith", email="john@example.com"),
            work=[Work(name="Acme Corp", position="Dev")],
            skills=[Skill(name="Python")],
        )
        data = resume.model_dump(exclude_none=True)
        assert data["basics"]["name"] == "John Smith"
        assert len(data["work"]) == 1
        assert len(data["skills"]) == 1


class TestRenderCVModels:
    """Test RenderCV model creation and serialization."""

    def test_empty_rendercv_has_defaults(self) -> None:
        """A Cv with no fields should contain default empty lists."""
        cv = Cv()
        data = cv.model_dump()
        assert data["social_networks"] is None or data["social_networks"] == []
        assert data["sections"] is None or data["sections"] == {}

    def test_cv_with_header(self) -> None:
        cv = Cv(
            name="John Smith",
            email="john@example.com",
            social_networks=[SocialNetwork(network="LinkedIn", username="johnsmith")],
        )
        data = cv.model_dump(exclude_none=True)
        assert data["name"] == "John Smith"
        assert len(data["social_networks"]) == 1

    @pytest.mark.parametrize(
        "model_cls,kwargs,checks",
        RENDERCV_ROUND_TRIP,
        ids=[c[0].__name__ for c in RENDERCV_ROUND_TRIP],
    )
    def test_rendercv_round_trip(self, model_cls, kwargs, checks) -> None:
        """Each RenderCV entry round-trips through dump/validate."""
        _assert_round_trip(model_cls, kwargs, checks)

    # test_bullet_entry removed as BulletEntry is not part of official rendercv models

    def test_sections_with_various_entries(self) -> None:
        cv = Cv(
            sections={
                "experience": [
                    ExperienceEntry(company="Co", position="Dev").model_dump(
                        exclude_none=True
                    )
                ],
                "education": [
                    EducationEntry(institution="MIT", area="CS").model_dump(
                        exclude_none=True
                    )
                ],
                "skills": [
                    OneLineEntry(label="Languages", details="Python").model_dump(
                        exclude_none=True
                    )
                ],
            }
        )
        assert cv.sections and "experience" in cv.sections
        assert cv.sections and "education" in cv.sections
        assert cv.sections and "skills" in cv.sections
