"""LinkedIn date format parser."""

from __future__ import annotations

import re

MONTH_NAMES = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}


def parse_linkedin_date(raw: str | None) -> str | None:
    """Parse a LinkedIn date string to ISO format YYYY-MM-DD.

    Supported formats:
    - YYYY-MM-DD  (already ISO)
    - YYYY-MM     -> YYYY-MM-01
    - Month YYYY  -> YYYY-MM-01  (e.g. "March 2020", "Mar 2020")
    - YYYY        -> YYYY-01-01

    Returns None for empty, missing, or unparseable values.
    """
    if not raw or not raw.strip():
        return None

    text = raw.strip()

    # Already ISO: YYYY-MM-DD
    if m := re.match(r"^(\d{4})-(\d{2})-(\d{2})$", text):
        return text

    # YYYY-MM (no day)
    if m := re.match(r"^(\d{4})-(\d{2})$", text):
        return f"{m.group(1)}-{m.group(2)}-01"

    # Month YYYY or Mon YYYY
    if m := re.match(r"^([A-Za-z]+)\s+(\d{4})$", text):
        month_name = m.group(1).lower()
        year = m.group(2)
        month = MONTH_NAMES.get(month_name)
        if month is not None:
            return f"{year}-{month:02d}-01"
        return None

    # YYYY (year only)
    if m := re.match(r"^(\d{4})$", text):
        return f"{m.group(1)}-01-01"

    return None
