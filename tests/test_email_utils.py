"""Tests for Email value object."""

from __future__ import annotations

import pytest
from dataclasses import FrozenInstanceError

from linkedinto.email_utils import Email


class TestEmail:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("john@example.com", "john@example.com"),
            ("  John.Doe@Example.COM  ", "John.Doe@example.com"),
            (None, None),
            ("", None),
            ("   ", None),
            ("not-an-email", None),
            ("missing@domain", None),
            ("@nodomain.com", None),
        ],
    )
    def test_from_raw(self, raw, expected):
        result = Email.from_raw(raw)
        if expected is None:
            assert result is None
        else:
            assert result is not None
            assert result.address == expected

    def test_str_returns_address(self):
        email = Email.from_raw("john@example.com")
        assert str(email) == "john@example.com"

    def test_frozen(self):
        email = Email.from_raw("john@example.com")
        with pytest.raises(FrozenInstanceError):
            email._address = "changed@example.com"  # type: ignore[misc]
