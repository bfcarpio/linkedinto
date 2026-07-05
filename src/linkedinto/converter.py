"""Strategy interface for LinkedIn data format converters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Converter(ABC):
    """Abstract strategy for converting LinkedIn data to an output format.

    All format converters (JSON Resume, RenderCV, etc.) must implement
    ``convert()`` and ``validate()``.

    Subclasses can set ``requires`` to declare they need a previous
    converter's output rather than the raw ``LinkedInData``.
    """

    requires: str | None = None
    """Key of a previous converter's output required as input.

    ``None`` (default) means this converter takes the raw
    ``LinkedInData``.  Set to e.g. ``"jsonresume"`` to receive
    the output of the JsonResumeConverter stage.
    """

    tiobe_override: frozenset[str] | None = None
    """Optional TIOBE language list override for programming language detection.

    If set, replaces the default TIOBE_TOP_50 set when checking if a skill
    is a programming language.
    """

    @abstractmethod
    def convert(self, data: Any) -> Any:
        """Convert input data to the target format model.

        Args:
            data: Input data — either ``LinkedInData`` (when
                  ``requires`` is ``None``) or a previous
                  converter's output.

        Returns:
            The converted model instance.

        Raises:
            linkedinto.exceptions.ConversionError: If conversion fails.
        """
        ...

    @abstractmethod
    def validate(self, model: Any) -> list[str]:
        """Validate the converted model for correctness.

        Args:
            model: The model instance returned by ``convert()``.

        Returns:
            A list of validation error messages. An empty list means
            the model is valid.
        """
        ...
