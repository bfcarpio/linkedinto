"""Programming language detection for LinkedIn skills.

Uses an embedded TIOBE top-50 list (snapshot: June 2026) as the primary
classifier. Falls back to Pygments lexers (loaded dynamically) for any
skill name not found in the TIOBE list.
"""

from __future__ import annotations

from functools import cache
from importlib import import_module

# TIOBE Index top 50 programming languages (June 2026 snapshot)
TIOBE_TOP_50: frozenset[str] = frozenset(
    {
        name.lower()
        for name in [
            "Python",
            "C++",
            "C",
            "Java",
            "C#",
            "JavaScript",
            "Visual Basic",
            "Go",
            "SQL",
            "Fortran",
            "Delphi/Object Pascal",
            "MATLAB",
            "PHP",
            "Rust",
            "Kotlin",
            "Ruby",
            "R",
            "COBOL",
            "Swift",
            "Assembly",
            "Ada",
            "Dart",
            "Scala",
            "TypeScript",
            "Perl",
            "Prolog",
            "Lua",
            "PL/SQL",
            "Julia",
            "Lisp",
            "Haskell",
            "Logo",
            "AWK",
            "Elixir",
            "SAS",
            "Scheme",
            "Bash",
            "Transact-SQL",
            "Smalltalk",
            "LabVIEW",
            "D",
            "F#",
            "Apex",
            "PowerShell",
            "Groovy",
            "VBScript",
            "Erlang",
            "Scratch",
            "Zig",
            "Ladder Logic",
        ]
    }
)


def _pygments_has_lexer(name: str) -> bool:
    """Check if Pygments has a lexer for the given name."""
    try:
        lexers = import_module("pygments.lexers")
        # Try exact match first
        try:
            lexers.get_lexer_by_name(name.lower())
            return True
        except Exception:
            pass
        # Try matching against lexer aliases
        lower = name.lower()
        for _name, aliases, *_ in lexers.get_all_lexers():
            if any(lower == a.lower() for a in aliases):
                return True
    except ImportError:
        pass
    return False


@cache
def _check_language(name: str) -> bool:
    """Core check with caching via lru_cache.

    Args:
        name: The skill name to check.

    Returns:
        True if the name matches a known programming language.
    """
    lower = name.strip().lower()

    # Fast path: TIOBE top 50
    if lower in TIOBE_TOP_50:
        return True

    # Slow path: Pygments fallback
    return _pygments_has_lexer(name)


def is_programming_language(name: str) -> bool:
    """Check if a skill name is a known programming language.

    Checks the TIOBE top-50 list first (fast path), then falls back
    to Pygments lexer lookup (slow path, loaded dynamically).

    The TIOBE list snapshot should be updated periodically (see README).

    Args:
        name: The skill name to check.

    Returns:
        True if the name matches a known programming language.
    """
    if not name or not name.strip():
        return False

    return _check_language(name)
