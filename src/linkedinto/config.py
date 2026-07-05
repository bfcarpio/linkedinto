"""Configuration model and loader for linkedinto.toml.

Provides a Pydantic v2 model for configuration with optional overrides
for TIOBE language list and LinkedIn profile data.
"""

from __future__ import annotations

import tomllib
from functools import cached_property
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from linkedinto.logger import setup_logger

# Setup module logger
logger = setup_logger(__name__)


class LinkedIntoConfig(BaseModel):
    """Configuration model for linkedinto.toml.

    All fields are optional to support partial configuration.
    When present, configuration values take highest precedence
    over extracted LinkedIn data.
    """

    model_config = ConfigDict(extra="ignore", frozen=False)

    # TIOBE language list override
    tiobe_override: list[str] | None = Field(
        default=None,
        max_length=50,
        description="Complete replacement for TIOBE_TOP_50 frozenset. "
        "If provided, replaces the entire list (all-or-nothing).",
    )

    # Identity fields matching ProfileRow in domain.py
    first_name: str | None = Field(
        default=None,
        description="First name for the resume/profile.",
    )
    last_name: str | None = Field(
        default=None,
        description="Last name for the resume/profile.",
    )
    address: str | None = Field(
        default=None,
        description="Street address.",
    )
    zip_code: str | None = Field(
        default=None,
        description="Postal/ZIP code.",
    )
    geo_location: str | None = Field(
        default=None,
        description="Geographic location (city, state, etc.).",
    )
    occupation: str | None = Field(
        default=None,
        description="Current occupation/title.",
    )
    summary: str | None = Field(
        default=None,
        description="Professional summary/objective.",
    )
    industry: str | None = Field(
        default=None,
        description="Industry field.",
    )
    country: str | None = Field(
        default=None,
        description="Country name.",
    )
    country_code: str | None = Field(
        default=None,
        description="Country code (ISO 3166-1 alpha-2).",
    )
    email_address: str | None = Field(
        default=None,
        description="Primary email address.",
    )
    phone_number: str | None = Field(
        default=None,
        description="Primary phone number.",
    )
    twitter: str | None = Field(
        default=None,
        description="Twitter/X username.",
    )
    linkedin: str | None = Field(
        default=None,
        description="LinkedIn profile URL.",
    )
    websites: str | None = Field(
        default=None,
        description="Other websites (comma-separated).",
    )
    headline: str | None = Field(
        default=None,
        description="Professional headline.",
    )

    @cached_property
    def tiobe_frozenset(self) -> frozenset[str] | None:
        """Get the TIOBE override as a cached frozenset.

        Returns:
            frozenset of lowercase language names if tiobe_override is configured.
            None if tiobe_override is not set or invalid.
        """
        # Early exit: no override configured
        if not self.tiobe_override:
            return None

        # Validate tiobe_override is a list of strings
        if not isinstance(self.tiobe_override, list):
            logger.warning("tiobe_override must be a list of strings, ignoring")
            return None

        # Parse into lowercase frozenset for case-insensitive matching
        try:
            override_set = frozenset(lang.lower() for lang in self.tiobe_override)
            logger.debug(
                f"TIOBE override converted to frozenset with {len(override_set)} languages"
            )
            return override_set
        except (AttributeError, TypeError) as e:
            logger.warning(f"Invalid tiobe_override format: {e}")
            return None


def load_config(config_path: Path | str | None = None) -> LinkedIntoConfig | None:
    """Load configuration from linkedinto.toml.

    Args:
        config_path: Optional path to config file. If None, looks for
                     'linkedinto.toml' in current working directory.

    Returns:
        LinkedIntoConfig instance if file exists and is valid.
        None if file doesn't exist or has parsing errors.

    Raises:
        FileNotFoundError: If config_path is specified but doesn't exist.
        tomllib.TOMLDecodeError: If config_path contains invalid TOML.
    """
    if config_path is None:
        config_path = Path.cwd() / "linkedinto.toml"
    else:
        config_path = Path(config_path)

    # Early exit: config file doesn't exist
    if not config_path.exists():
        logger.debug(f"No config file found at {config_path}")
        return None

    # Early exit: config file is not a file
    if not config_path.is_file():
        logger.warning(f"Config path {config_path} is not a file")
        return None

    try:
        # Parse TOML content
        config_content = config_path.read_text(encoding="utf-8")
        config_dict = tomllib.loads(config_content)

        # Parse and validate config using Pydantic model
        config = LinkedIntoConfig(**config_dict)

        logger.info(f"Loaded configuration from {config_path}")
        if config.tiobe_override:
            logger.debug(
                f"TIOBE override configured with {len(config.tiobe_override)} languages"
            )

        return config

    except tomllib.TOMLDecodeError as e:
        logger.warning(f"Invalid TOML syntax in {config_path}: {e}")
        return None
    except Exception as e:
        logger.warning(f"Error loading configuration from {config_path}: {e}")
        return None


def get_tiobe_override(config: LinkedIntoConfig | None) -> frozenset[str] | None:
    """Extract TIOBE override as frozenset from configuration.

    Args:
        config: Loaded LinkedIntoConfig instance.

    Returns:
        frozenset of lowercase language names if tiobe_override is configured.
        None if config is None or tiobe_override is not set.
    """
    # Early exit: no config
    if not config:
        return None

    # Return cached frozenset from the config instance
    return config.tiobe_frozenset


def apply_profile_config(
    config: LinkedIntoConfig | None, profile_row: dict[str, str | None]
) -> dict[str, str | None]:
    """Apply configuration overrides to profile data.

    Configuration values take highest precedence over extracted LinkedIn data.
    Only non-None configuration values override existing profile data.

    Args:
        config: Loaded LinkedIntoConfig instance.
        profile_row: Dictionary of profile data from LinkedIn export.

    Returns:
        Updated profile dictionary with configuration overrides applied.
    """
    if not config:
        return profile_row

    # Create a copy to avoid mutating input
    updated_profile = profile_row.copy()

    # Apply all non-None configuration fields
    for field_name, field_value in config.model_dump(exclude_none=True).items():
        # Skip tiobe_override - handled separately
        if field_name == "tiobe_override":
            continue

        # Apply override (field_name is guaranteed to exist on config
        # since we're iterating over config.model_dump())
        updated_profile[field_name] = field_value

    return updated_profile
