"""Plain top-level overwrite for partial JSON Resume / RenderCV files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from linkedinto.constants import UTF8_ENCODING, YAML_EXTENSION, YML_EXTENSION
from linkedinto.exceptions import LinkedIntoError


def load_partial(path: str | Path) -> dict[str, Any]:
    """Load a partial JSON Resume or RenderCV file.

    Supports both .json and .yaml/.yml extensions.
    """
    p = Path(path)
    if not p.is_file():
        msg = f"Partial file '{p}' does not exist"
        raise LinkedIntoError(msg)

    raw = p.read_text(encoding=UTF8_ENCODING)

    if p.suffix in (YAML_EXTENSION, YML_EXTENSION):
        return yaml.safe_load(raw) or {}
    return json.loads(raw)


def overwrite(
    base: dict[str, Any],
    partial: dict[str, Any],
) -> dict[str, Any]:
    """Plain top-level key overwrite.

    Only replaces keys that exist in ``partial`` at the top level.
    Does NOT perform deep merge of nested structures or collections.

    Args:
        base: The generated output dict.
        partial: The partial override dict.

    Returns:
        A new dict with partial keys replacing base keys at the top level.
    """
    result = dict(base)
    result.update(partial)
    return result
