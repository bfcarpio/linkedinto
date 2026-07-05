"""Converter: JSON Resume model → RenderCV YAML model."""

from __future__ import annotations

from typing import Any, override

from linkedinto.converter import Converter
from linkedinto.language_detector import is_programming_language
from linkedinto.models_jsonresume import JsonResume
from linkedinto.models_rendercv import (
    Cv,
    RenderCV,
    SocialNetwork,
)

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
    """Convert a JSON Resume model to a RenderCV YAML model."""

    requires = "jsonresume"  # needs JsonResume output as input

    @override
    def convert(self, data: JsonResume) -> RenderCV:
        """Convert JSON Resume model to RenderCV."""
        cv = Cv()

        if data.basics is not None:
            b = data.basics
            cv.name = b.name
            cv.headline = b.label
            cv.location = b.location.city if b.location else None
            cv.email = b.email
            cv.phone = b.phone
            cv.website = b.url

            if b.profiles:
                for p in b.profiles:
                    if p.network:
                        cv.social_networks.append(
                            SocialNetwork(network=p.network, username=p.username or "")
                        )

            if b.summary:
                cv.sections.setdefault(SECTION_SUMMARY, []).append(b.summary)

        if data.work:
            cv.sections.setdefault(SECTION_EXPERIENCE, [])
            for w in data.work:
                entry: dict[str, Any] = {
                    "company": w.name or "",
                    "position": w.position or "",
                }
                if w.location:
                    entry["location"] = w.location
                if w.start_date:
                    entry["start_date"] = w.start_date
                if w.end_date:
                    entry["end_date"] = w.end_date
                if w.highlights:
                    entry["highlights"] = w.highlights
                cv.sections[SECTION_EXPERIENCE].append(entry)

        if data.education:
            cv.sections.setdefault(SECTION_EDUCATION, [])
            for e in data.education:
                entry = {"institution": e.institution or "", "area": e.area or ""}
                if e.study_type:
                    entry["degree"] = e.study_type
                if e.start_date:
                    entry["start_date"] = e.start_date
                if e.end_date:
                    entry["end_date"] = e.end_date
                cv.sections[SECTION_EDUCATION].append(entry)

        # Projects → NormalEntry
        if data.projects:
            cv.sections.setdefault(SECTION_PROJECTS, [])
            for p in data.projects:
                entry = {"name": p.name or ""}
                if p.description:
                    entry["summary"] = p.description
                if p.highlights:
                    entry["highlights"] = p.highlights
                if p.start_date:
                    entry["date"] = p.start_date
                cv.sections[SECTION_PROJECTS].append(entry)

        # Publications → OneLineEntry grouped
        if data.publications:
            cv.sections.setdefault(SECTION_PUBLICATIONS, [])
            for p in data.publications:
                entry = {"title": p.name or ""}
                if p.publisher:
                    entry["authors"] = [p.publisher]
                if p.summary:
                    entry["summary"] = p.summary
                if p.release_date:
                    entry["date"] = p.release_date
                cv.sections[SECTION_PUBLICATIONS].append(entry)

        # Awards → OneLineEntry
        if data.awards:
            cv.sections.setdefault(SECTION_AWARDS, [])
            for a in data.awards:
                cv.sections[SECTION_AWARDS].append(
                    {"label": a.title or "", "details": a.awarder or ""}
                )

        # Human languages
        if data.languages:
            cv.sections.setdefault(SECTION_LANGUAGES, [])
            for lang in data.languages:
                cv.sections[SECTION_LANGUAGES].append(
                    {"label": lang.language or "", "details": lang.fluency or ""}
                )

        # Skills: split into programming languages and non-programming
        prog_skills: list[str] = []
        non_prog_skills: list[tuple[str, str]] = []  # (name, proficiency)

        for s in data.skills:
            if s.name and is_programming_language(s.name):
                prog_skills.append(s.name)
            elif s.name:
                non_prog_skills.append((s.name, s.level or ""))

        if prog_skills:
            cv.sections.setdefault(SECTION_TECHNOLOGIES, [])
            cv.sections[SECTION_TECHNOLOGIES].append(
                {"label": "Programming Languages", "details": ", ".join(prog_skills)}
            )

        if non_prog_skills:
            cv.sections.setdefault(SECTION_SKILLS, [])
            # Order by proficiency: Expert > Advanced > Intermediate > Beginner
            non_prog_skills.sort(
                key=lambda x: PROFICIENCY_ORDER.get(
                    x[1].lower(), len(PROFICIENCY_ORDER)
                )
            )
            details = ", ".join(
                f"{name} ({level})" if level else name
                for name, level in non_prog_skills
            )
            cv.sections[SECTION_SKILLS].append({"label": "Skills", "details": details})

        return RenderCV(cv=cv)

    @override
    def validate(self, model: RenderCV) -> list[str]:
        """Validate RenderCV model.

        Checks:
        - CV name is present.
        - Social networks have valid entries.
        - No empty section entries with missing labels.

        Returns:
            A list of validation error messages (empty = valid).
        """
        errors: list[str] = []

        if not model.cv.name:
            errors.append("CV 'name' is empty or missing")

        for i, sn in enumerate(model.cv.social_networks):
            if not sn.network:
                errors.append(f"Social network[{i}] missing 'network' name")
            if not sn.username:
                errors.append(f"Social network[{i}] missing 'username'")

        return errors
