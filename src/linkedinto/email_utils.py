"""Email address value object with validation."""

from __future__ import annotations

import typing
from dataclasses import dataclass

from email_validator import EmailNotValidError, validate_email


@dataclass(frozen=True)
class Email:
    """Validated email value object."""

    _address: str

    @classmethod
    def from_raw(cls, raw: str | None) -> Email | None:
        """Parse and validate a raw email string. Returns None for empty/invalid."""
        if not raw or not raw.strip():
            return None

        stripped = raw.strip()
        try:
            validated = validate_email(stripped, check_deliverability=False)
        except EmailNotValidError:
            return None

        return cls(validated.normalized)

    @property
    def address(self) -> str:
        return self._address

    @typing.override
    def __str__(self) -> str:
        return self._address
