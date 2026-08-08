"""LinkedIn date format parser."""

from __future__ import annotations

from datetime import datetime

from dateutil import parser as dateutil_parser
from dateutil.parser import ParserError

# dateutil fills missing month/day with the current date by default.
# Use a fixed default so "2020" → "2020-01-01" and "March 2020" → "2020-03-01"
# instead of today's month/day.
_DEFAULT = datetime(1, 1, 1)


def parse_linkedin_date(raw: str | None) -> str | None:
    """Parse a LinkedIn date string to ISO format YYYY-MM-DD.

    Uses python-dateutil for robust multi-format parsing.

    Returns None for empty, missing, or unparseable values.
    """
    if not raw or not raw.strip():
        return None

    try:
        parsed = dateutil_parser.parse(raw.strip(), default=_DEFAULT)
    except (ValueError, ParserError, OverflowError):
        return None

    return parsed.date().isoformat()
