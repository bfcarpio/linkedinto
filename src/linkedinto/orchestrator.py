"""Orchestrator — wires parser, converters, overwriter, and writer."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from linkedinto.config import (
    AiConfig,
    apply_profile_config,
    get_tiobe_override,
    load_config,
)
from linkedinto.constants import (
    JSONRESUME_SCHEMA_URL,
    RENDERC_YAML_FILE,
    RENDERCV_SCHEMA_URL,
    RESUME_JSON_FILE,
)
from linkedinto.converter import Converter
from linkedinto.converter_jsonresume import JsonResumeConverter
from linkedinto.converter_rendercv import RenderCvConverter
from linkedinto.domain import LinkedInData
from linkedinto.exceptions import AiGroupingError
from linkedinto.overwriter import load_partial, overwrite
from linkedinto.parser import LinkedinZipParser
from linkedinto.skill_grouper import SkillGrouper
from linkedinto.writer import write_json, write_yaml

_logger = logging.getLogger(__name__)

# Registered output format converters — both are independent peers
# consuming raw LinkedInData (``requires = None``).
# The ``requires`` attribute on each converter is validated at runtime:
# if a required output hasn't been produced yet a ValueError is raised.
_CONVERTERS: list[Converter] = [
    JsonResumeConverter(),
    RenderCvConverter(),
]


def _build_grouper(
    ai_config: AiConfig,
    tiobe_override: frozenset[str] | None,
    no_cache: bool,
) -> SkillGrouper:
    """Construct a SkillGrouper from AI config, honoring --no-cache."""
    grouper = SkillGrouper(ai_config, tiobe_override=tiobe_override)
    if no_cache:
        grouper.disable_cache()
    return grouper


def _run_converters(
    parsed: LinkedInData,
    tiobe_override: frozenset[str] | None = None,
    ai_config: AiConfig | None = None,
    no_cache: bool = False,
) -> dict[str, Any]:
    """Run all registered converters against parsed LinkedIn data.

    Each converter declares its input dependency via ``requires``.
    ``None`` = raw parsed data; ``"jsonresume"`` = previous stage's output.
    """
    outputs: dict[str, Any] = {}

    parsed.sort()

    skill_grouper = None
    if ai_config is not None:
        skill_grouper = _build_grouper(ai_config, tiobe_override, no_cache)

    for converter in _CONVERTERS:
        name = type(converter).__name__.removesuffix("Converter").lower()

        # Resolve input — either raw data or a previous stage's output
        if converter.requires:
            try:
                input_data = outputs[converter.requires]
            except KeyError:
                msg = (
                    f"Converter '{name}' requires '{converter.requires}' "
                    f"which is not in the pipeline output yet. "
                    f"Reorder converters so that dependencies run first."
                )
                raise ValueError(msg) from None
        else:
            input_data = parsed

        # Set tiobe_override if converter has this attribute
        if hasattr(converter, "tiobe_override"):
            converter.tiobe_override = tiobe_override

        # Set AI skill grouper (None resets any previous run's grouper)
        converter.skill_grouper = skill_grouper

        output = converter.convert(input_data)
        outputs[name] = output

        # TODO: Enable validation once schema validation is implemented
        # if errors := converter.validate(output):
        #     for err in errors:
        #         _logger.warning("Validation [%s]: %s", name, err)

    return outputs


def run(
    zip_path: str | Path,
    output_dir: str | Path,
    *,
    partial_jsonresume: str | Path | None = None,
    partial_rendercv: str | Path | None = None,
    jsonresume_only: bool = False,
    rendercv_only: bool = False,
    bullets: str | None = None,
    verbose: bool = False,
    ai_group: bool = False,
    ai_preview: bool = False,
    no_cache: bool = False,
    ai_model: str | None = None,
) -> dict[str, Path]:
    """Full pipeline: parse → convert → overwrite → write.

    Returns a dict mapping ``"jsonresume"`` / ``"rendercv"`` to the
    written output paths. In ``ai_preview`` mode, prints skill groupings
    to stdout and returns an empty dict without writing files.
    """
    # Load configuration
    config = load_config()
    tiobe_override = get_tiobe_override(config)

    # --ai-group is the master switch; --ai-preview implies it
    ai_config: AiConfig | None = None
    if ai_group or ai_preview:
        ai_config = config.ai if config else None
        if ai_config is None:
            raise AiGroupingError(
                "--ai-group requires an [ai] section in linkedinto.toml"
            )
        if ai_model:
            ai_config.model = ai_model

    parser = LinkedinZipParser()
    data = parser.parse(zip_path)

    # Preview mode: group skills, print to stdout, write nothing
    if ai_preview:
        assert ai_config is not None  # guaranteed by check above
        grouper = _build_grouper(ai_config, tiobe_override, no_cache)
        skill_names = [s.name for s in data.skills if s.name]
        groups = grouper.group(skill_names)
        print(json.dumps(groups, indent=2))
        return {}

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Apply configuration overrides to profile data
    if config and data.profile:
        # Convert ProfileRow to dict for apply_profile_config
        # Include all fields even if None, so config can override None values
        profile_dict = {
            field_name: getattr(data.profile, field_name, None)
            for field_name in [
                "first_name",
                "last_name",
                "address",
                "zip_code",
                "geo_location",
                "occupation",
                "summary",
                "industry",
                "country",
                "country_code",
                "email_address",
                "phone_number",
                "twitter",
                "linkedin",
                "websites",
                "headline",
            ]
        }

        # Apply config overrides
        updated_profile_dict = apply_profile_config(config, profile_dict)

        # Convert back to ProfileRow
        for field_name, field_value in updated_profile_dict.items():
            if hasattr(data.profile, field_name):
                # Keep None values as None, empty strings as empty strings
                setattr(data.profile, field_name, field_value)

    # Run converters with TIOBE override and optional AI grouping
    models = _run_converters(
        data, tiobe_override=tiobe_override, ai_config=ai_config, no_cache=no_cache
    )

    resume = models.get("jsonresume")
    rc_model = models.get("rendercv")

    result: dict[str, Path] = {}

    if not rendercv_only and resume is not None:
        resume_dict = resume.model_dump(exclude_none=True)
        if partial_jsonresume:
            partial = load_partial(partial_jsonresume)
            resume_dict = overwrite(resume_dict, partial)
        json_path = out / RESUME_JSON_FILE
        write_json(resume_dict, json_path, schema_url=JSONRESUME_SCHEMA_URL)
        result["jsonresume"] = json_path

    if not jsonresume_only and rc_model is not None:
        rc_dict = rc_model.model_dump(exclude_none=True)
        if partial_rendercv:
            partial = load_partial(partial_rendercv)
            rc_dict = overwrite(rc_dict, partial)
        yaml_path = out / RENDERC_YAML_FILE
        write_yaml(rc_dict, yaml_path, schema_url=RENDERCV_SCHEMA_URL)
        result["rendercv"] = yaml_path

    return result
