"""LinkedIn description bullet parser.

Splits a description string into a summary (text before first bullet)
and a list of highlights (bullet-separated segments).
"""

from __future__ import annotations

import re

from linkedinto.exceptions import BulletParseError

_DEFAULT_BULLET_CHARS = "•◦‣⁃*➲⁌⁍※‽⁂⁑⁕⁖⁗⁘⁙⁚⁛⁜⁝⁞"


def parse_bullets(  # noqa: SIM108
    text: str | None,
    custom_bullets: str | None = None,
) -> tuple[str, list[str]]:
    """Parse a description into (summary, highlights)."""
    if not text or not text.strip():
        return "", []

    if custom_bullets is not None:
        if not custom_bullets.strip():
            msg = "Custom bullets string cannot be empty if provided"
            raise BulletParseError(msg)
        bullet_chars = custom_bullets
    else:
        bullet_chars = _DEFAULT_BULLET_CHARS

    escaped = re.escape(bullet_chars)
    pattern = rf"(?:^|(?<=\s))([{escaped}])"

    text = text.strip()
    matches = list(re.finditer(pattern, text))

    if not matches:
        return text, []

    first_bullet_pos = matches[0].start()
    summary = text[:first_bullet_pos].strip()

    highlights: list[str] = []
    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        highlight = text[start:end].strip()
        if highlight:
            highlights.append(highlight)

    return summary, highlights
