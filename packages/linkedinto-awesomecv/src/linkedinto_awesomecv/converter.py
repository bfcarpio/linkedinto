"""Converter: LinkedInData → Awesome-CV LaTeX (``.tex``) via Jinja2 templates."""

from __future__ import annotations

import re
from pathlib import Path
from typing import override

from jinja2 import Environment, FileSystemLoader

from linkedinto.bullet_parser import parse_bullets
from linkedinto.constants import PROFICIENCY_ORDER
from linkedinto.converter import Converter
from linkedinto.domain import (
    AwardHonorRow,
    CertificationRow,
    EducationRow,
    InterestRow,
    LinkedInData,
    PositionRow,
    ProfileRow,
    ProjectRow,
    PublicationRow,
    VolunteerRow,
)
from linkedinto.language_detector import (
    is_programming_language,
    normalize_language_name,
)
from linkedinto.skill_grouper import PROGRAMMING_LANGUAGES
from linkedinto.url_extractor import extract_websites

_TEMPLATE_DIR = Path(__file__).parent / "templates"


def _make_env() -> Environment:
    """Create a Jinja2 environment with custom delimiters for LaTeX."""
    return Environment(
        loader=FileSystemLoader(_TEMPLATE_DIR),
        variable_start_string="<<",
        variable_end_string=">>",
        block_start_string="<%",
        block_end_string="%>",
        comment_start_string="<#",
        comment_end_string="#>",
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def latex_escape(text: str | None) -> str:
    """Escape special LaTeX characters. Returns ``""`` for None."""
    if not text:
        return ""
    replacements = {
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    result = text
    for char, replacement in replacements.items():
        result = result.replace(char, replacement)
    return result


def _escape_and_break(text: str | None) -> str:
    """Escape LaTeX special chars and normalise whitespace.

    LinkedIn CSV exports collapse newlines into double-spaces.  Since
    summary text is rendered inside ``\\item{}`` (itemize), we can't
    use ``\\\\`` line breaks — just collapse 2+ spaces to one so
    sentences don't run together visually.
    """
    if not text:
        return ""
    result = latex_escape(text)
    result = result.replace("\n", " ")
    result = re.sub(r" {2,}", " ", result)
    return result.strip()


def _escape_for_paragraph(text: str | None) -> str:
    """Escape LaTeX and convert newlines to ``\\\\`` line breaks.

    Used for ``cvparagraph`` (outside ``\\cventry``) where ``\\\\``
    forced line breaks are valid.
    """
    if not text:
        return ""
    result = latex_escape(text)
    result = result.replace("\n", r"\\")
    result = re.sub(r" {2,}", r" \\\\", result)
    return result.strip()


def format_acv_date(iso_date: str | None) -> str:
    """Parse an ISO date ``YYYY-MM-DD`` → ``Mon. YYYY``.

    Returns ``""`` for None/empty.
    """
    if not iso_date:
        return ""
    # iso_date may be "2023-09" or "2023-09-01"
    parts = iso_date.split("-")
    if len(parts) < 2:
        return ""
    months = [
        "Jan.",
        "Feb.",
        "Mar.",
        "Apr.",
        "May",
        "Jun.",
        "Jul.",
        "Aug.",
        "Sep.",
        "Oct.",
        "Nov.",
        "Dec.",
    ]
    try:
        month_idx = int(parts[1]) - 1
    except (ValueError, IndexError):
        return ""
    if not 0 <= month_idx < 12:
        return ""
    year = parts[0]
    return f"{months[month_idx]} {year}"


def format_date_range(start: str | None, end: str | None) -> str:
    """Format a date range: ``start - end`` or ``start - Present``."""
    s = format_acv_date(start)
    e = format_acv_date(end) if end else "Present"
    if not s:
        return ""
    if not e:
        e = "Present"
    return f"{s} - {e}"


def _extract_social_handle(raw: str, url_prefix: str = "") -> str:
    """Extract a clean social handle from a URL or raw string.

    Strips leading ``@`` and extracts the last path segment from URLs.
    """
    if url_prefix and url_prefix in raw:
        return raw.rstrip("/").split(url_prefix)[-1].split("/")[0]
    if raw.startswith("@"):
        return raw[1:]
    return raw


class AwesomeCvConverter(Converter):
    """Convert LinkedInData to Awesome-CV LaTeX via Jinja2 templates."""

    requires = None  # takes raw LinkedInData

    @override
    def convert(self, data: LinkedInData) -> str:
        """Render LinkedInData to a ``.tex`` string."""
        context = self._build_context(data)
        env = _make_env()
        env.globals["latex_escape"] = latex_escape
        env.globals["format_date_range"] = format_date_range
        env.globals["format_acv_date"] = format_acv_date
        template = env.get_template("resume.tex.j2")
        return template.render(**context)

    @staticmethod
    def _build_links(urls: list[str]) -> tuple[str, str, str, str]:
        """Detect platform-specific URLs and build LaTeX header lines.

        Maps known domains to Awesome-CV's dedicated icon commands:
          github.com → \\github{username}
          gitlab.com → \\gitlab{username}
          bitbucket.org → \\bitbucket{username}
        All other URLs (codeberg.org, personal sites, etc.) use \\homepage{url}.

        Returns ``(github_line, gitlab_line, bitbucket_line, homepage_line)``.
        """
        github_line = ""
        gitlab_line = ""
        bitbucket_line = ""
        homepage_line = ""
        for url in urls:
            if "github.com/" in url:
                username = url.rstrip("/").split("github.com/")[-1].split("/")[0]
                if username and not github_line:
                    github_line = f"\\github{{{latex_escape(username)}}}"
            elif "gitlab.com/" in url:
                username = url.rstrip("/").split("gitlab.com/")[-1].split("/")[0]
                if username and not gitlab_line:
                    gitlab_line = f"\\gitlab{{{latex_escape(username)}}}"
            elif "bitbucket.org/" in url:
                username = url.rstrip("/").split("bitbucket.org/")[-1].split("/")[0]
                if username and not bitbucket_line:
                    bitbucket_line = f"\\bitbucket{{{latex_escape(username)}}}"
            elif not homepage_line:
                homepage_line = f"\\homepage{{{latex_escape(url)}}}"
        return github_line, gitlab_line, bitbucket_line, homepage_line

    def _build_context(self, data: LinkedInData) -> dict:
        """Prepare template context from LinkedInData."""
        p = data.profile

        # --- Header fields ---
        full_name = ""
        first = ""
        last = ""
        if p:
            first = p.first_name or ""
            last = p.last_name or ""
            full_name = f"{first} {last}".strip()
        name_preamble = f"\\name{{{latex_escape(first)}}}{{{latex_escape(last)}}}"

        position_line = ""
        if p and (p.headline or p.occupation):
            position_line = f"\\position{{{latex_escape(p.headline or p.occupation)}}}"

        address_line = self._cmd_line(p, "address", "address")
        mobile_line = ""
        if p and p.phone_number:
            mobile_line = f"\\mobile{{{latex_escape(p.phone_number.international)}}}"

        email_line = ""
        if p and p.email_address:
            email_line = f"\\email{{{latex_escape(p.email_address.address)}}}"

        # Platform links from websites (GitHub, GitLab, Bitbucket, homepage)
        github_line = ""
        gitlab_line = ""
        bitbucket_line = ""
        homepage_line = ""
        if p and p.websites:
            urls = extract_websites(p.websites)
            github_line, gitlab_line, bitbucket_line, homepage_line = self._build_links(
                urls
            )

        linkedin_line = ""
        if p and p.linkedin:
            handle = _extract_social_handle(p.linkedin, "linkedin.com/in/")
            linkedin_line = f"\\linkedin{{{latex_escape(handle)}}}"

        twitter_line = ""
        if p and p.twitter:
            handle = _extract_social_handle(p.twitter)
            twitter_line = f"\\twitter{{{latex_escape(handle)}}}"

        # --- Sections ---
        positions = [self._build_position(pos) for pos in data.positions]
        education = [self._build_education(edu) for edu in data.education]
        projects = [self._build_project(proj) for proj in data.projects]
        honors = [self._build_honor(h) for h in data.honors]
        certifications = [self._build_certification(c) for c in data.certifications]
        volunteer = [self._build_volunteer(v) for v in data.volunteer]
        publications = [self._build_publication(pub) for pub in data.publications]
        interests = [self._build_interest(i) for i in data.interests]
        languages = self._build_languages(data.languages)
        skills = self._build_skills(data.skills)
        if p and p.summary:
            normalized = p.summary.replace("\r\n", "\n").replace("\r", "\n")
            summary_blocks: list[dict] = []
            for block in normalized.split("\n\n"):
                # The summary (text before first bullet) within each block.
                text, highlights = parse_bullets(block)
                text = _escape_for_paragraph(text)
                highlights = [latex_escape(h) for h in highlights]
                if text or highlights:
                    summary_blocks.append({"text": text, "highlights": highlights})
        else:
            summary_blocks = []

        return {
            "name_preamble": name_preamble,
            "position_line": position_line,
            "address_line": address_line,
            "mobile_line": mobile_line,
            "email_line": email_line,
            "gitlab_line": gitlab_line,
            "github_line": github_line,
            "bitbucket_line": bitbucket_line,
            "homepage_line": homepage_line,
            "linkedin_line": linkedin_line,
            "twitter_line": twitter_line,
            "full_name": latex_escape(full_name),
            "summary_blocks": summary_blocks,
            "positions": positions,
            "education": education,
            "projects": projects,
            "honors": honors,
            "certifications": certifications,
            "volunteer": volunteer,
            "publications": publications,
            "interests": interests,
            "languages": languages,
            "skills": skills,
        }

    # ── Helpers ────────────────────────────────────────────────────

    @staticmethod
    def _cmd_line(profile: ProfileRow | None, field: str, cmd: str) -> str:
        """Build a ``\\cmd{value}`` line from a profile field."""
        if profile is None:
            return ""
        value = getattr(profile, field, None)
        if not value:
            return ""
        return f"\\{cmd}{{{latex_escape(value)}}}"

    @staticmethod
    def _build_position(pos: PositionRow) -> dict:
        summary, highlights = parse_bullets(pos.description)
        summary = _escape_and_break(summary)
        highlights = [latex_escape(h) for h in highlights]
        return {
            "position": pos.position or "",
            "company": pos.company or "",
            "location": pos.location or "",
            "started": pos.started,
            "ended": pos.ended,
            "summary": summary,
            "highlights": highlights,
        }

    @staticmethod
    def _build_education(edu: EducationRow) -> dict:
        return {
            "degree": (edu.degree.abbreviation or edu.degree.full)
            if edu.degree
            else "",
            "institution": edu.school or "",
            "location": "",
            "started": edu.started,
            "ended": edu.ended,
            "score": edu.grade or "",
            "courses": (
                [a.strip() for a in edu.activities.split(",") if a.strip()]
                if edu.activities
                else []
            ),
        }

    @staticmethod
    def _build_project(proj: ProjectRow) -> dict:
        summary, highlights = parse_bullets(proj.description)
        summary = _escape_and_break(summary)
        highlights = [latex_escape(h) for h in highlights]
        return {
            "name": proj.name or proj.title or "",
            "started": proj.started,
            "ended": proj.ended,
            "url": proj.url or "",
            "summary": summary,
            "highlights": highlights,
        }

    @staticmethod
    def _build_honor(h: AwardHonorRow) -> dict:
        return {
            "title": h.title or "",
            "awarder": h.awarder or h.issuer or h.company or "",
            "date": h.date,
        }

    @staticmethod
    def _build_certification(c: CertificationRow) -> dict:
        return {
            "name": c.name or "",
            "issuer": c.issuer or "",
            "date": c.date,
        }

    @staticmethod
    def _build_volunteer(v: VolunteerRow) -> dict:
        summary, highlights = parse_bullets(v.description)
        summary = _escape_and_break(summary)
        highlights = [latex_escape(h) for h in highlights]
        return {
            "position": v.position or "",
            "organization": v.name or "",
            "location": "",
            "started": v.started,
            "ended": v.ended,
            "summary": summary,
            "highlights": highlights,
        }

    @staticmethod
    def _build_publication(pub: PublicationRow) -> dict:
        return {
            "title": pub.name or pub.title or "",
            "publisher": pub.publisher or "",
            "date": pub.date,
        }

    @staticmethod
    def _build_interest(i: InterestRow) -> dict:
        return {"name": i.name or ""}

    def _build_languages(self, languages: list) -> list[tuple[str, str]]:
        """Build (name, proficiency) tuples for the languages section."""
        return [
            (lang.name or "", lang.proficiency or "") for lang in languages if lang.name
        ]

    def _build_skills(self, skills: list) -> list[tuple[str, list[str]]]:
        """Group skills into (category, [skill_names]) tuples.

        Mirrors RenderCvConverter._build_skills logic:
        - With a skill grouper: use AI categories
        - Without: split programming languages vs other skills by proficiency
        """
        if self.skill_groups is None and self.skill_grouper is not None:
            skill_names = [s.name for s in skills if s.name]
            self.skill_groups = self.skill_grouper.group(skill_names)
        if self.skill_groups is not None:
            return [
                (category, skills_list)
                for category, skills_list in self.skill_groups.items()
            ]

        prog_skills: list[str] = []
        non_prog_skills: list[tuple[str, str]] = []

        for s in skills:
            if s.name and is_programming_language(
                s.name, tiobe_override=self.tiobe_override
            ):
                prog_skills.append(normalize_language_name(s.name))
            elif s.name:
                non_prog_skills.append((s.name, s.proficiency or ""))

        result: list[tuple[str, list[str]]] = []

        if prog_skills:
            result.append((PROGRAMMING_LANGUAGES, prog_skills))

        if non_prog_skills:
            non_prog_skills.sort(
                key=lambda x: PROFICIENCY_ORDER.get(
                    x[1].lower(), len(PROFICIENCY_ORDER)
                )
            )
            result.append(
                (
                    "Skills",
                    [
                        f"{name} ({level})" if level else name
                        for name, level in non_prog_skills
                    ],
                )
            )

        return result

    @override
    def validate(self, model: str) -> list[str]:
        """Validate the rendered LaTeX string."""
        errors: list[str] = []

        if not model or not model.strip():
            errors.append("Output is empty")
            return errors

        if "\\documentclass" not in model:
            errors.append("Missing '\\documentclass' declaration")

        if "\\begin{document}" not in model:
            errors.append("Missing '\\begin{document}'")

        if "\\name{" not in model:
            errors.append("Missing '\\name{}' — no profile name set")

        return errors
