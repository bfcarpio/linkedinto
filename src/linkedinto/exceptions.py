"""Error taxonomy for linkedinto."""


class LinkedIntoError(Exception):
    """Base exception for all linkedinto errors."""


class LinkedInParserError(LinkedIntoError):
    """Raised when parsing the LinkedIn ZIP/CSV fails."""


class DateParseError(LinkedIntoError):
    """Raised when a date string cannot be parsed."""


class BulletParseError(LinkedIntoError):
    """Raised when bullet parsing options are invalid."""


class ConversionError(LinkedIntoError):
    """Raised during JSON Resume or RenderCV conversion."""
