"""Phone number value object with multi-format output access.

``Phone`` wraps a parsed ``phonenumbers.PhoneNumber`` and exposes
format-specific accessors so each output-format strategy (RenderCV,
JSON Resume, ...) can pull the rendering it wants without re-parsing
or re-knowing the upstream library.

The object is built once — at the parser boundary for LinkedIn CSV
data and at the config-override boundary for ``linkedinto.toml``
values — so every downstream consumer sees an identical, validated
``Phone | None`` rather than raw strings.
"""

from __future__ import annotations

import typing
from dataclasses import dataclass

import phonenumbers
from phonenumbers import NumberParseException, PhoneNumberFormat


@dataclass(frozen=True)
class Phone:
    """Phone number value object exposing multiple output formats.

    Construction is centralized in :meth:`from_raw`; direct ``Phone(...)``
    construction requires a pre-parsed ``phonenumbers.PhoneNumber`` (used
    only by tests or internals that already hold one).

    Each converter asks for the rendering it needs:

    - :attr:`e164`        — RenderCV's ``PhoneNumber`` validator (``"+15175050397"``)
    - :attr:`international` — JSON Resume's free-form string (``"+1 517-505-0397"``)
    - :attr:`national`      — locale-aware display (``"(517) 505-0397"``)
    - :attr:`rfc3966`       — ``tel:`` URI (``"tel:+1-517-505-0397"``)
    """

    _number: phonenumbers.PhoneNumber

    @classmethod
    def from_raw(
        cls,
        raw: str | None,
        default_region: str = "US",
    ) -> Phone | None:
        """Parse a raw phone string into a ``Phone`` value object.

        Args:
            raw: Raw phone number from CSV or config. ``None``/empty
                strings pass through as ``None``.
            default_region: ISO 3166-1 alpha-2 region used when the
                input lacks a country code (e.g. ``"US"`` for
                ``"517-505-0397"``).

        Returns:
            ``Phone`` instance when parsing succeeds and the number is
            valid; ``None`` for empty/unparseable input so downstream
            converters simply omit the field instead of crashing.
        """
        if not raw or not raw.strip():
            return None

        stripped = raw.strip()
        try:
            parsed = phonenumbers.parse(stripped, default_region)
        except NumberParseException:
            return None

        if not phonenumbers.is_valid_number(parsed):
            return None

        return cls(parsed)

    @property
    def e164(self) -> str:
        """E.164 format accepted by RenderCV's ``PhoneNumber`` validator."""
        return phonenumbers.format_number(self._number, PhoneNumberFormat.E164)

    @property
    def international(self) -> str:
        """International format suitable for free-form string fields."""
        return phonenumbers.format_number(self._number, PhoneNumberFormat.INTERNATIONAL)

    @property
    def national(self) -> str:
        """Locale-aware national format for display."""
        return phonenumbers.format_number(self._number, PhoneNumberFormat.NATIONAL)

    @property
    def rfc3966(self) -> str:
        """RFC 3966 ``tel:`` URI form."""
        return phonenumbers.format_number(self._number, PhoneNumberFormat.RFC3966)

    @typing.override
    def __str__(self) -> str:
        return self.international
