"""Tests for JSON Resume and RenderCV Pydantic models."""

from __future__ import annotations

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
from linkedinto.models_rendercv import (
    BulletEntry,
    Cv,
    EducationEntry,
    ExperienceEntry,
    NormalEntry,
    OneLineEntry,
    PublicationEntry,
    RenderCV,
    SocialNetwork,
)


class TestJsonResumeModels:
    """Test JSON Resume model creation and serialization."""

    def test_empty_json_resume_has_default_lists(self) -> None:
        """A JsonResume with no fields should contain default empty lists."""
        resume = JsonResume()
        data = resume.model_dump(exclude_none=True)
        assert data["work"] == []
        assert data["education"] == []
        assert data["skills"] == []

    def test_basics_round_trip(self) -> None:
        """Basics should serialize/deserialize correctly."""
        original = Basics(
            name="John Smith",
            label="Software Engineer",
            email="john@example.com",
            location=Location(city="San Francisco", country_code="US"),
        )
        data = original.model_dump(exclude_none=True)
        restored = Basics.model_validate(data)
        assert restored.name == "John Smith"
        assert restored.label == "Software Engineer"
        assert restored.email == "john@example.com"
        assert restored.location is not None
        assert restored.location.city == "San Francisco"

    def test_profile_serialization(self) -> None:
        profile = Profile(network="LinkedIn", username="johnsmith")
        data = profile.model_dump(exclude_none=True)
        assert data["network"] == "LinkedIn"
        assert data["username"] == "johnsmith"

    def test_work_round_trip(self) -> None:
        work = Work(
            name="Acme Corp",
            position="Senior Dev",
            start_date="2020-03-01",
            highlights=["Built payment gateway", "Reduced latency"],
        )
        data = work.model_dump(exclude_none=True)
        restored = Work.model_validate(data)
        assert restored.name == "Acme Corp"
        assert restored.position == "Senior Dev"
        assert restored.start_date == "2020-03-01"
        assert len(restored.highlights) == 2

    def test_education_round_trip(self) -> None:
        edu = Education(
            institution="MIT",
            area="Computer Science",
            study_type="BS",
            start_date="2016-09-01",
            end_date="2020-06-01",
        )
        data = edu.model_dump(exclude_none=True)
        restored = Education.model_validate(data)
        assert restored.institution == "MIT"
        assert restored.area == "Computer Science"

    def test_skill_round_trip(self) -> None:
        skill = Skill(name="Python", level="Expert", keywords=["Django", "FastAPI"])
        data = skill.model_dump(exclude_none=True)
        restored = Skill.model_validate(data)
        assert restored.name == "Python"
        assert len(restored.keywords) == 2

    def test_language_round_trip(self) -> None:
        lang = Language(language="English", fluency="Native")
        data = lang.model_dump(exclude_none=True)
        restored = Language.model_validate(data)
        assert restored.language == "English"

    def test_project_round_trip(self) -> None:
        proj = Project(
            name="My App",
            description="A cool app",
            highlights=["Won award"],
            url="https://example.com",
        )
        data = proj.model_dump(exclude_none=True)
        restored = Project.model_validate(data)
        assert restored.name == "My App"
        assert restored.url == "https://example.com"

    def test_publication_round_trip(self) -> None:
        pub = Publication(
            name="Research Paper",
            publisher="IEEE",
            authors=["John Smith", "Jane Doe"],
        )
        data = pub.model_dump(exclude_none=True)
        restored = Publication.model_validate(data)
        assert restored.name == "Research Paper"
        assert len(restored.authors) == 2

    def test_certificate_round_trip(self) -> None:
        cert = Certificate(name="AWS Certified", issuer="Amazon", date="2023-01-01")
        data = cert.model_dump(exclude_none=True)
        restored = Certificate.model_validate(data)
        assert restored.name == "AWS Certified"

    def test_award_round_trip(self) -> None:
        award = Award(title="Best Paper", awarder="IEEE", date="2023-06-01")
        data = award.model_dump(exclude_none=True)
        restored = Award.model_validate(data)
        assert restored.title == "Best Paper"

    def test_reference_round_trip(self) -> None:
        ref = Reference(name="Jane Doe", reference="Great colleague")
        data = ref.model_dump(exclude_none=True)
        restored = Reference.model_validate(data)
        assert restored.name == "Jane Doe"

    def test_volunteer_round_trip(self) -> None:
        vol = Volunteer(
            organization="Charity Org",
            position="Volunteer",
            highlights=["Helped organize event"],
        )
        data = vol.model_dump(exclude_none=True)
        restored = Volunteer.model_validate(data)
        assert restored.organization == "Charity Org"

    def test_interest_round_trip(self) -> None:
        interest = Interest(
            name="Machine Learning", keywords=["NLP", "Computer Vision"]
        )
        data = interest.model_dump(exclude_none=True)
        _ = Interest.model_validate(data)
        assert interest.name == "Machine Learning"

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
        cv = RenderCV()
        data = cv.model_dump(exclude_none=True)
        assert data["cv"]["social_networks"] == []
        assert data["cv"]["sections"] == {}

    def test_cv_with_header(self) -> None:
        cv = RenderCV(
            cv=Cv(
                name="John Smith",
                email="john@example.com",
                social_networks=[
                    SocialNetwork(network="LinkedIn", username="johnsmith")
                ],
            )
        )
        data = cv.model_dump(exclude_none=True)
        assert data["cv"]["name"] == "John Smith"
        assert len(data["cv"]["social_networks"]) == 1

    def test_experience_entry(self) -> None:
        entry = ExperienceEntry(
            company="Acme Corp",
            position="Senior Dev",
            start_date="2020-03",
            highlights=["Built feature"],
        )
        data = entry.model_dump(exclude_none=True)
        restored = ExperienceEntry.model_validate(data)
        assert restored.company == "Acme Corp"
        assert len(restored.highlights) == 1

    def test_education_entry(self) -> None:
        entry = EducationEntry(institution="MIT", area="CS", degree="BS")
        data = entry.model_dump(exclude_none=True)
        restored = EducationEntry.model_validate(data)
        assert restored.institution == "MIT"

    def test_normal_entry(self) -> None:
        entry = NormalEntry(name="Project X", summary="A project")
        data = entry.model_dump(exclude_none=True)
        restored = NormalEntry.model_validate(data)
        assert restored.name == "Project X"

    def test_publication_entry(self) -> None:
        entry = PublicationEntry(title="Paper", authors=["John"], journal="Journal")
        data = entry.model_dump(exclude_none=True)
        restored = PublicationEntry.model_validate(data)
        assert restored.title == "Paper"
        assert restored.journal == "Journal"

    def test_one_line_entry(self) -> None:
        entry = OneLineEntry(label="Python", details="Expert")
        data = entry.model_dump(exclude_none=True)
        restored = OneLineEntry.model_validate(data)
        assert restored.label == "Python"

    def test_bullet_entry(self) -> None:
        entry = BulletEntry(bullet="Achieved something")
        data = entry.model_dump(exclude_none=True)
        restored = BulletEntry.model_validate(data)
        assert restored.bullet == "Achieved something"

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
        assert "experience" in cv.sections
        assert "education" in cv.sections
        assert "skills" in cv.sections
