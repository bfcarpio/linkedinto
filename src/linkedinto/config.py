"""Configuration model and loader for linkedinto.toml.

Provides a Pydantic v2 model for configuration with optional overrides
for TIOBE language list and LinkedIn profile data.
"""

from __future__ import annotations

import tomllib
from functools import cached_property
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from linkedinto.logger import setup_logger
from linkedinto.phone_utils import Phone
from linkedinto.validation import format_validation_error

# Setup module logger
logger = setup_logger(__name__)

DEFAULT_AI_MODEL = "openai/gpt-4o-mini"
AI_API_KEY_ENV_VAR = "LINKEDINTO_AI_API_KEY"


class AiConfig(BaseModel):
    """AI provider configuration for skill grouping."""

    model_config = ConfigDict(extra="ignore", frozen=False)

    model: str = Field(
        default=DEFAULT_AI_MODEL,
        description="LiteLLM model string: 'provider/model' (e.g. "
        "'anthropic/claude-3-haiku-20240307', 'ollama/llama3').",
        examples=["openai/gpt-4o-mini"],
    )
    api_key: str | None = Field(
        default=None,
        description="API key. Falls back to LINKEDINTO_AI_API_KEY env var, "
        "then provider env vars (OPENAI_API_KEY, etc.).",
    )
    skill_groups: dict[str, list[str]] | None = Field(
        default=None,
        description="Deterministic skill→category presets, applied before the "
        "LLM call. Skills listed here are never sent to the LLM. Keys are "
        'category names (e.g. "Tools & Technologies", "Interpersonal Skills"), '
        "values are exact skill names.",
        examples=[{"Tools & Technologies": ["Python", "Docker"]}],
    )


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
        examples=["python", "javascript", "rust"],
    )

    # Identity fields matching ProfileRow in domain.py
    first_name: str | None = Field(
        default=None,
        description="First name for the resume/profile.",
        examples=["Jane"],
    )
    last_name: str | None = Field(
        default=None,
        description="Last name for the resume/profile.",
        examples=["Doe"],
    )
    address: str | None = Field(
        default=None,
        description="Street address.",
        examples=["123 Main St, Suite 400"],
    )
    zip_code: str | None = Field(
        default=None,
        description="Postal/ZIP code.",
        examples=["94105"],
    )
    geo_location: str | None = Field(
        default=None,
        description="Geographic location (city, state, etc.).",
        examples=["San Francisco, CA, US"],
    )
    occupation: str | None = Field(
        default=None,
        description="Current occupation/title.",
        examples=["Senior Software Engineer"],
    )
    summary: str | None = Field(
        default=None,
        description="Professional summary/objective.",
        examples=["Experienced engineer with 10+ years building distributed systems."],
    )
    industry: str | None = Field(
        default=None,
        description="Industry field.",
        examples=["Technology / Software"],
    )
    country: str | None = Field(
        default=None,
        description="Country name.",
        examples=["United States"],
    )
    country_code: str | None = Field(
        default=None,
        description="Country code (ISO 3166-1 alpha-2).",
        examples=["US"],
    )
    email_address: str | None = Field(
        default=None,
        description="Primary email address.",
        examples=["jane.doe@example.com"],
    )
    phone_number: str | None = Field(
        default=None,
        description="Primary phone number.",
        examples=["+1 (555) 123-4567"],
    )
    twitter: str | None = Field(
        default=None,
        description="Twitter/X username.",
        examples=["janedoe"],
    )
    linkedin: str | None = Field(
        default=None,
        description="LinkedIn profile URL.",
        examples=["https://www.linkedin.com/in/janedoe"],
    )
    websites: str | None = Field(
        default=None,
        description="Other websites (comma-separated).",
        examples=["https://janedoe.dev, https://github.com/janedoe"],
    )
    headline: str | None = Field(
        default=None,
        description="Professional headline.",
        examples=["Senior Software Engineer at Acme Corp"],
    )

    # AI configuration for automatic skill grouping
    ai: AiConfig | None = Field(
        default=None,
        description="AI configuration for automatic skill grouping.",
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
    except ValidationError as e:
        for msg in format_validation_error(e, LinkedIntoConfig):
            logger.warning(msg)
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
    config: LinkedIntoConfig | None, profile_row: dict[str, str | Phone | None]
) -> dict[str, str | Phone | None]:
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
        # Skip ai - not a profile field
        if field_name in ("tiobe_override", "ai"):
            continue

        # Phone numbers come in as raw strings from TOML; normalize to
        # Phone so downstream converters receive the value object, not a
        # raw string from the LinkedIn CSV path.
        if field_name == "phone_number" and isinstance(field_value, str):
            updated_profile[field_name] = Phone.from_raw(field_value)
        else:
            # Apply override (field_name is guaranteed to exist on config
            # since we're iterating over config.model_dump())
            updated_profile[field_name] = field_value

    return updated_profile
