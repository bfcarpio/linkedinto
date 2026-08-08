"""Degree value object with abbreviation mapping.

LinkedIn exports the full degree name (e.g. "Bachelor of Science").
Converters need different representations:
- JSON Resume ``study_type``: the full text
- RenderCV ``degree``: the abbreviation ("BS")
- AwesomeCV: the full text or abbreviation, depending on template
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class _DegreeDef:
    """Canonical definition of one degree."""

    full: str
    abbreviation: str
    aliases: tuple[str, ...] = ()


_DEGREES: tuple[_DegreeDef, ...] = (
    _DegreeDef("Associate of Arts", "AA", ("associate",)),
    _DegreeDef("Associate of Science", "AS"),
    _DegreeDef("Associate of Applied Science", "AAS"),
    _DegreeDef("Associate of Applied Arts", "AAA"),
    _DegreeDef("Bachelor of Arts", "BA", ("bachelors of arts",)),
    _DegreeDef(
        "Bachelor of Science", "BS", ("bachelor", "bachelors", "bachelors of science")
    ),
    _DegreeDef("Bachelor of Engineering", "BEng", ("bachelors of engineering",)),
    _DegreeDef("Bachelor of Fine Arts", "BFA", ("bachelors of fine arts",)),
    _DegreeDef(
        "Bachelor of Business Administration",
        "BBA",
        ("bachelors of business administration",),
    ),
    _DegreeDef("Bachelor of Technology", "BTech", ("bachelors of technology",)),
    _DegreeDef("Master of Arts", "MA", ("masters of arts",)),
    _DegreeDef("Master of Science", "MS", ("master", "masters", "masters of science")),
    _DegreeDef("Master of Engineering", "MEng", ("masters of engineering",)),
    _DegreeDef("Master of Fine Arts", "MFA", ("masters of fine arts",)),
    _DegreeDef(
        "Master of Business Administration",
        "MBA",
        ("masters of business administration",),
    ),
    _DegreeDef("Master of Technology", "MTech", ("masters of technology",)),
    _DegreeDef(
        "Doctor of Philosophy",
        "PhD",
        ("doctor", "doctorate", "doctorate of philosophy"),
    ),
    _DegreeDef("Doctor of Education", "EdD"),
    _DegreeDef("Doctor of Science", "ScD"),
    _DegreeDef("Doctor of Medicine", "MD"),
    _DegreeDef("Doctor of Jurisprudence", "JD"),
    _DegreeDef("Specialist in Education", "EdS", ("education specialist",)),
)


def _build_lookup() -> dict[str, _DegreeDef]:
    """Flatten all degree names into a normalised-key → def mapping."""
    table: dict[str, _DegreeDef] = {}
    for d in _DEGREES:
        for key in (d.full, d.abbreviation, *d.aliases):
            table[_normalise(key)] = d
    return table


def _normalise(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    key = re.sub(r"[^\w\s]", "", text.lower()).strip()
    return re.sub(r"\s+", " ", key)


_LOOKUP = _build_lookup()


@dataclass(frozen=True)
class Degree:
    """Represents an academic degree with its full name and abbreviation."""

    full: str
    abbreviation: str | None = None

    @classmethod
    def from_text(cls, text: str | None) -> Degree | None:
        """Build a ``Degree`` from raw LinkedIn text.

        Returns ``None`` when *text* is empty or whitespace.
        If no abbreviation mapping is found, ``abbreviation`` is ``None``.
        """
        if not text or not text.strip():
            return None
        full = text.strip()
        defn = _LOOKUP.get(_normalise(full))
        if defn is not None:
            return cls(full=defn.full, abbreviation=defn.abbreviation)
        return cls(full=full, abbreviation=None)

    def __str__(self) -> str:
        return self.full
