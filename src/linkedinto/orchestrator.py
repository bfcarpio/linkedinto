"""Orchestrator — wires parser, converters, overwriter, and writer."""

from __future__ import annotations

import json
import logging
from importlib.metadata import entry_points
from pathlib import Path
from typing import Any

from linkedinto.config import (
    AiConfig,
    apply_profile_config,
    get_tiobe_override,
    load_config,
)
from linkedinto.constants import (
    AWESOME_TEX_FILE,
    JSONRESUME_SCHEMA_URL,
    RENDERC_YAML_FILE,
    RENDERCV_SCHEMA_URL,
    RESUME_JSON_FILE,
)
from linkedinto.converter import Converter
from linkedinto.domain import LinkedInData
from linkedinto.exceptions import AiGroupingError
from linkedinto.overwriter import load_partial, overwrite
from linkedinto.parser import LinkedinZipParser
from linkedinto.skill_grouper import SkillGrouper
from linkedinto.writer import write_json, write_tex, write_yaml

_logger = logging.getLogger(__name__)


def _discover_converters() -> list[tuple[str, Converter]]:
    """Discover converter plugins via entry points.

    Returns (entry_point_name, converter_instance) tuples.
    The entry-point name is the source of truth for the converter key
    (matching RESULT_* constants), not the class name.
    """
    converters = []
    for ep in entry_points(group="linkedinto.converters"):
        try:
            converter_cls = ep.load()
            converters.append((ep.name, converter_cls()))
        except Exception as e:  # noqa: BLE001
            _logger.warning("Failed to load converter '%s': %s", ep.name, e)
    return converters


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
    *,
    ai_group: bool = False,
    no_cache: bool = False,
) -> dict[str, Any]:
    """Run all registered converters against parsed LinkedIn data.

    Each converter declares its input dependency via ``requires``.
    ``None`` = raw parsed data; ``"jsonresume"`` = previous stage's output.
    """
    outputs: dict[str, Any] = {}

    parsed.sort()

    skill_grouper = None
    skill_groups: dict[str, list[str]] | None = None
    if ai_config is not None:
        if ai_group:
            # Full AI mode: LLM call on cache miss
            skill_grouper = _build_grouper(ai_config, tiobe_override, no_cache)
            skill_names = [s.name for s in parsed.skills if s.name]
            skill_groups = skill_grouper.group(skill_names)
        elif not no_cache:
            # Cache-only: use disk cache if available, no LLM call
            grouper = SkillGrouper(ai_config, tiobe_override=tiobe_override)
            skill_names = [s.name for s in parsed.skills if s.name]
            if grouper.has_cached_groups(skill_names):
                skill_grouper = grouper
                skill_groups = grouper.group(skill_names)

    for name, converter in _discover_converters():
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

        # Set AI skill grouper and pre-computed groups (None resets previous run)
        converter.skill_grouper = skill_grouper
        converter.skill_groups = skill_groups

        output = converter.convert(input_data)
        outputs[name] = output

        # Run converter validation (raises if invalid)
        if errors := converter.validate(output):
            for err in errors:
                _logger.warning("Validation [%s]: %s", name, err)

    return outputs


def run(
    zip_path: str | Path,
    output_dir: str | Path,
    *,
    ai_group: bool = False,
    ai_preview: bool = False,
    ai_model: str | None = None,
    no_cache: bool = False,
    partial_jsonresume: str | Path | None = None,
    partial_rendercv: str | Path | None = None,
    partial_awesomecv: str | Path | None = None,
    jsonresume_only: bool = False,
    rendercv_only: bool = False,
    awesomecv_only: bool = False,
    bullets: str | None = None,
) -> dict[str, Path]:
    """Full pipeline: parse → convert → overwrite → write.

    Returns a dict mapping result keys to the written output paths.
    In ``ai_preview`` mode, prints skill groupings to stdout and returns
    an empty dict without writing files.
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
    elif not no_cache:
        # Cache-only mode: attempt disk cache even without --ai-group
        ai_config = config.ai if config else None

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
        # Skip value objects (Email, Phone) - factory values are set in the original
        value_object_fields = {"email_address", "phone_number"}

        for field_name, field_value in updated_profile_dict.items():
            if field_name in value_object_fields:
                continue
            if hasattr(data.profile, field_name):
                # Keep None values as None, empty strings as empty strings
                setattr(data.profile, field_name, field_value)

    # Run converters with TIOBE override and optional AI grouping
    models = _run_converters(
        data,
        tiobe_override=tiobe_override,
        ai_config=ai_config,
        ai_group=ai_group,
        no_cache=no_cache,
    )

    resume = models.get("jsonresume")
    rc_model = models.get("rendercv")
    acv_model = models.get("awesomecv")

    result: dict[str, Path] = {}

    if not rendercv_only and not awesomecv_only and resume is not None:
        resume_dict = resume.model_dump(exclude_none=True)
        if partial_jsonresume:
            partial = load_partial(partial_jsonresume)
            resume_dict = overwrite(resume_dict, partial)
        json_path = out / RESUME_JSON_FILE
        write_json(resume_dict, json_path, schema_url=JSONRESUME_SCHEMA_URL)
        result["jsonresume"] = json_path

    if not jsonresume_only and not awesomecv_only and rc_model is not None:
        rc_dict = rc_model.model_dump(exclude_none=True, mode="json")
        if partial_rendercv:
            partial = load_partial(partial_rendercv)
            # Partial RenderCV files use the {cv: {...}} wrapper structure;
            # apply overrides inside the cv dict, then re-wrap.
            partial_cv = partial.get("cv", partial)
            rc_dict = overwrite(rc_dict, partial_cv)
        yaml_path = out / RENDERC_YAML_FILE
        write_yaml({"cv": rc_dict}, yaml_path, schema_url=RENDERCV_SCHEMA_URL)
        result["rendercv"] = yaml_path

    if not jsonresume_only and not rendercv_only and acv_model is not None:
        if partial_awesomecv:
            _logger.warning(
                "--partial-awesomecv is not supported; "
                "the .tex output will be written without merging."
            )
        tex_path = out / AWESOME_TEX_FILE
        write_tex(acv_model, tex_path)
        result["awesomecv"] = tex_path

    return result
