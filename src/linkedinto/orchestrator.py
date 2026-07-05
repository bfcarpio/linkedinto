"""Orchestrator — wires parser, converters, overwriter, and writer."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

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
from linkedinto.overwriter import load_partial, overwrite
from linkedinto.parser import LinkedinZipParser
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


def _run_converters(parsed: LinkedInData) -> dict[str, Any]:
    """Run all registered converters against parsed LinkedIn data.

    Each converter declares its input dependency via ``requires``.
    ``None`` = raw parsed data; ``"jsonresume"`` = previous stage's output.
    """
    outputs: dict[str, Any] = {}

    parsed.sort()

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
) -> dict[str, Path]:
    """Full pipeline: parse → convert → overwrite → write.

    Returns a dict mapping ``"jsonresume"`` / ``"rendercv"`` to the
    written output paths.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    parser = LinkedinZipParser()
    data = parser.parse(zip_path)
    models = _run_converters(data)

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
