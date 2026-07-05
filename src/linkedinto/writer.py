"""Output serialization for JSON Resume and RenderCV."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from linkedinto.constants import (
    UTF8_ENCODING,
)


def write_json(
    data: dict[str, Any] | BaseModel,
    path: str | Path,
    schema_url: str | None = None,
) -> Path:
    """Write data as formatted JSON with optional $schema reference."""
    p = Path(path)
    if isinstance(data, BaseModel):
        data = data.model_dump(exclude_none=True)

    if schema_url:
        data.pop("$schema", None)  # strip any existing key
        data = {"$schema": schema_url, **data}

    p.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding=UTF8_ENCODING,
    )
    return p


def write_yaml(
    data: dict[str, Any] | BaseModel,
    path: str | Path,
    schema_url: str | None = None,
) -> Path:
    """Write data as YAML with optional schema comment."""
    p = Path(path)
    if isinstance(data, BaseModel):
        data = data.model_dump(exclude_none=True)

    lines: list[str] = []
    if schema_url:
        lines.append(f"# yaml-language-server: $schema={schema_url}")
        lines.append("")

    yaml_str = yaml.dump(
        data, default_flow_style=False, allow_unicode=True, sort_keys=False
    ).strip()
    lines.append(yaml_str)
    lines.append("")

    p.write_text("\n".join(lines), encoding=UTF8_ENCODING)
    return p
