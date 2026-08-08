"""Tests for language_detector module."""

from __future__ import annotations

import pytest

from linkedinto.language_detector import (
    is_programming_language,
    normalize_language_name,
)


class TestIsProgrammingLanguage:
    @pytest.mark.parametrize(
        "name",
        [
            "Go",
            # LinkedIn disambiguates the ambiguous short name "Go" (the board
            # game) by appending " (Programming Language)".
            "Go (Programming Language)",
            "go (programming language)",
            "C (Programming Language)",
            "R (Programming Language)",
            "D (Programming Language)",
            # Common alias used in the wild for Go.
            "Golang",
            "golang",
            "Python",
            "C++",
            "TypeScript",
        ],
    )
    def test_detected(self, name: str) -> None:
        assert is_programming_language(name) is True

    @pytest.mark.parametrize(
        "name",
        ["Kubernetes", "Agile", "Team Leadership", ""],
    )
    def test_not_detected(self, name: str) -> None:
        assert is_programming_language(name) is False


class TestNormalizeLanguageName:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("Go (Programming Language)", "Go"),
            ("go (programming language)", "go"),
            ("C (Programming Language)", "C"),
            ("R (Programming Language)", "R"),
            ("D (Programming Language)", "D"),
            ("Golang", "Go"),
            ("golang", "Go"),
            ("Go", "Go"),
            ("Python", "Python"),
        ],
    )
    def test_normalize(self, raw: str, expected: str) -> None:
        assert normalize_language_name(raw) == expected
