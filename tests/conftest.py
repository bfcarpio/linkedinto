"""Shared pytest fixtures and helpers for the linkedinto test suite.

Exposes three named ZIP fixtures (`sample_csv_zip`, `minimal_multi_csv_zip`,
`cli_sample_zip`) plus a `make_zip` factory for tests that need custom member
sets. Every fixture backs onto the pytest `tmp_path` so files auto-cleanup
(DIP): tests no longer pair `tempfile.mkstemp` with a manual `unlink()`.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"

# Single-CSV export used by the parser tests (section name lives in column 1).
SAMPLE_CSV = """Profile.csv,First Name,Last Name,Occupation,Summary,Country,EmailAddress,LinkedIn,Headline
Profile.csv,John,Smith,Software Eng.,Full-stack dev,United States,john@example.com,https://linkedin.com/in/john,Senior Engineer
Skills.csv,Name,Proficiency,Count
Skills.csv,Python,Expert,5
Skills.csv,React,Advanced,3
Languages.csv,Name,Proficiency
Languages.csv,English,Native or bilingual
Languages.csv,Spanish,Professional working
"""

# Smaller single-CSV dataset (Profile + Skills) used by the CLI tests.
CLI_SAMPLE_CSV = """Profile.csv,First Name,Last Name,Occupation,EmailAddress,Headline
Profile.csv,John,Smith,Engineer,john@example.com,Senior Dev
Skills.csv,Name,Proficiency
Skills.csv,Python,Expert
"""

_SECTION_CSVS = {
    "Profile.csv": "minimal_profile.csv",
    "Positions.csv": "minimal_positions.csv",
    "Education.csv": "minimal_education.csv",
    "Skills.csv": "minimal_skills.csv",
    "Languages.csv": "minimal_languages.csv",
}


def _load_fixture(name: str) -> str:
    """Return the text contents of a CSV fixture under tests/fixtures/."""
    return (FIXTURES / name).read_text(encoding="utf-8")


def _write_zip(tmp_path: Path, entries: dict[str, str]) -> Path:
    """Write a ZIP whose members map name->content into tmp_path; return its path."""
    path = tmp_path / "sample.zip"
    with zipfile.ZipFile(path, "w") as zf:
        for name, content in entries.items():
            zf.writestr(name, content)
    return path


@pytest.fixture
def sample_csv_zip(tmp_path: Path) -> Path:
    """Single-CSV export ZIP (entry "LinkedIn_Export.csv") for parser tests."""
    return _write_zip(tmp_path, {"LinkedIn_Export.csv": SAMPLE_CSV})


@pytest.fixture
def minimal_multi_csv_zip(tmp_path: Path) -> Path:
    """Real multi-CSV export ZIP: all five minimal section CSVs."""
    return _write_zip(
        tmp_path,
        {name: _load_fixture(file) for name, file in _SECTION_CSVS.items()},
    )


@pytest.fixture
def cli_sample_zip(tmp_path: Path) -> Path:
    """CLI single-CSV ZIP (entry "data.csv", Profile + Skills)."""
    return _write_zip(tmp_path, {"data.csv": CLI_SAMPLE_CSV})


@pytest.fixture
def make_zip(tmp_path: Path):
    """Factory: call with a {member_name: content} dict to build a custom ZIP."""

    def _build(entries: dict[str, str]) -> Path:
        return _write_zip(tmp_path, entries)

    return _build
