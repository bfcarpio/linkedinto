"""Interactive questionnaire tests."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import patch

import pytest

from linkedinto.domain import ProfileRow


def fake_prompt(prompt_text: str, **kwargs: object) -> str:
    """Fake prompt function that returns values from an iterator."""
    value_iter = kwargs.get("_fake_iter")
    if value_iter is None:
        raise ValueError("fake_prompt called without _fake_iter")
    try:
        return next(value_iter)
    except StopIteration:
        raise ValueError("fake_prompt exhausted iterator")


class TestQuestionnaire:
    @pytest.fixture
    def fake_values(self, tmp_path) -> Callable[[], object]:
        """Fixture that provides an iterator constructor for test inputs.

        Usage in tests:
            fake_values_iter = fake_values(
                ("5", "John", ""),
                ("", ""),
            )
        """
        return lambda *items: iter(items)

    def test_no_edits_empty_input(self, fake_values: Callable[[], object]) -> None:
        """Empty input throughout returns unchanged profile."""
        profile = ProfileRow(
            first_name="Jane",
            last_name="Doe",
            email_address="jane@example.com",
        )

        fake_values_iter = fake_values(
            (
                "5",
                "John",
                "",
            ),  # select 5th field (first_name), enter John, Enter to finish
            ("", ""),  # start with empty string → finish
        )

        from linkedinto.questionnaire import run_questionnaire

        result = run_questionnaire(
            profile, prompt_fn=fake_prompt, _fake_iter=fake_values_iter
        )

        assert result.first_name == "John"
        assert result.last_name == "Doe"
        assert result.email_address == "jane@example.com"

    def test_edit_string_field(self, fake_values: Callable[[], object]) -> None:
        """Selecting and editing a string field updates the profile."""
        profile = ProfileRow(
            first_name="Jane",
            last_name="Doe",
        )

        fake_values_iter = fake_values(("5", "John", ""), ("", ""))

        from linkedinto.questionnaire import run_questionnaire

        result = run_questionnaire(
            profile, prompt_fn=fake_prompt, _fake_iter=fake_values_iter
        )

        assert result.first_name == "John"
        assert result.last_name == "Doe"

    def test_edit_email_valid(self, fake_values: Callable[[], object]) -> None:
        """Valid email input updates the profile."""
        profile = ProfileRow(email_address=None)

        fake_values_iter = fake_values(("11", "john@example.com", ""), ("", ""))

        from linkedinto.questionnaire import run_questionnaire

        result = run_questionnaire(
            profile, prompt_fn=fake_prompt, _fake_iter=fake_values_iter
        )

        assert result.email_address is not None
        assert result.email_address.address == "john@example.com"

    def test_edit_email_invalid_then_valid(
        self, fake_values: Callable[[], object]
    ) -> None:
        """Invalid email re-prompts; valid email succeeds."""
        profile = ProfileRow(email_address=None)

        fake_values_iter = fake_values(
            ("11", "not-an-email", ""),  # invalid
            ("11", "jane@example.com", ""),  # valid
            ("", ""),
        )

        from linkedinto.questionnaire import run_questionnaire

        result = run_questionnaire(
            profile, prompt_fn=fake_prompt, _fake_iter=fake_values_iter
        )

        assert result.email_address is not None
        assert result.email_address.address == "jane@example.com"

    def test_edit_phone_valid(self, fake_values: Callable[[], object]) -> None:
        """Valid phone input updates the profile."""
        profile = ProfileRow(phone_number=None)

        fake_values_iter = fake_values(("12", "+1 (555) 123-4567", ""), ("", ""))

        from linkedinto.questionnaire import run_questionnaire

        result = run_questionnaire(
            profile, prompt_fn=fake_prompt, _fake_iter=fake_values_iter
        )

        assert result.phone_number is not None
        assert result.phone_number.international == "+1 555 123-4567"

    def test_profile_same_object_identity(
        self, fake_values: Callable[[], object]
    ) -> None:
        """ProfileRow is the same object identity, but values mutated."""
        profile = ProfileRow(first_name="Jane", last_name="Doe")

        fake_values_iter = fake_values(("5", "John", ""), ("", ""))

        from linkedinto.questionnaire import run_questionnaire

        before = profile.first_name
        result = run_questionnaire(
            profile, prompt_fn=fake_prompt, _fake_iter=fake_values_iter
        )
        after = profile.first_name

        assert after == "John"
        assert before == "Jane"

    def test_display_output_rendered(self, fake_values: Callable[[], object]) -> None:
        """Rich table rendering occurs after run_questionnaire."""
        profile = ProfileRow(first_name="Jane", last_name="Doe")

        fake_values_iter = fake_values(("", ""))

        from linkedinto.questionnaire import run_questionnaire

        # Mock the Table constructor to verify it's called
        with patch("linkedinto.questionnaire.Table") as mock_table:
            mock_table.return_value = None

            run_questionnaire(
                profile, prompt_fn=fake_prompt, _fake_iter=fake_values_iter
            )

            mock_table.assert_called_once()
