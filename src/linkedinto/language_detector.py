"""Programming language detection for LinkedIn skills.

Uses an embedded TIOBE top-50 list (snapshot: June 2026) as the primary
classifier. Falls back to Pygments lexers (loaded dynamically) for any
skill name not found in the TIOBE list.

Supports custom TIOBE override via the tiobe_override parameter.
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
def _check_language(name: str, tiobe_set: frozenset[str] = TIOBE_TOP_50) -> bool:
    """Core check with caching via lru_cache.

    Args:
        name: The skill name to check.
        tiobe_set: Set of programming language names to check against.
                     Defaults to TIOBE_TOP_50.

    Returns:
        True if the name matches a known programming language.
    """
    lower = name.strip().lower()

    # Fast path: TIOBE top 50 or custom set
    if lower in tiobe_set:
        return True

    # Slow path: Pygments fallback
    return _pygments_has_lexer(name)


def is_programming_language(
    name: str, tiobe_override: frozenset[str] | None = None
) -> bool:
    """Check if a skill name is a known programming language.

    Uses TIOBE top-50 list first (fast path), falls back to Pygments lexer lookup
    (slow path, loaded dynamically). Supports custom TIOBE override via configuration.

    The TIOBE list snapshot should be updated periodically (see README).

    Args:
        name: The skill name to check.
        tiobe_override: Optional custom set of programming language names.
                        If None, uses the default TIOBE_TOP_50 set.
                        If provided, uses the provided set.

    Returns:
        True if the name matches a known programming language.
    """
    # Early exit: empty name
    if not name or not name.strip():
        return False

    # Use override if provided, otherwise default to TIOBE_TOP_50
    if tiobe_override is None:
        tiobe_set = TIOBE_TOP_50
    else:
        # Convert to lowercase for case-insensitive matching, matching TIOBE_TOP_50 format
        tiobe_set = frozenset(lang.lower() for lang in tiobe_override)
    return _check_language(name, tiobe_set)
