"""Shared constants for linkedinto."""

from __future__ import annotations

# ── Output filenames ──────────────────────────────────────────────
RESUME_JSON_FILE = "resume.json"
RENDERC_YAML_FILE = "rendercv.yaml"

# ── Result dict keys (orchestrator / CLI) ─────────────────────────
RESULT_JSONRESUME = "jsonresume"
RESULT_RENDERC = "rendercv"

# ── Encodings ─────────────────────────────────────────────────────
UTF8_ENCODING = "utf-8"
UTF8_SIG_ENCODING = "utf-8-sig"

# ── File extensions ───────────────────────────────────────────────
CSV_EXTENSION = ".csv"
JSON_EXTENSION = ".json"
YAML_EXTENSION = ".yaml"
YML_EXTENSION = ".yml"

# ── Schema URLs ───────────────────────────────────────────────────
RENDERCV_SCHEMA_URL = (
    "https://raw.githubusercontent.com/rendercv/rendercv/refs/tags/v2.8/schema.json"
)
JSONRESUME_SCHEMA_URL = "https://raw.githubusercontent.com/jsonresume/jsonresume.org/refs/heads/master/packages/schema/schema.json"
