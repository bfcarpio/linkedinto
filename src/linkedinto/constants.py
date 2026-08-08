"""Shared constants for linkedinto."""

from __future__ import annotations

# ── Output filenames ──────────────────────────────────────────────
RESUME_JSON_FILE = "resume.json"
RENDERC_YAML_FILE = "rendercv.yaml"
AWESOME_TEX_FILE = "awesome-cv.tex"

# ── Result dict keys (orchestrator / CLI) ─────────────────────────
RESULT_JSONRESUME = "jsonresume"
RESULT_RENDERC = "rendercv"
RESULT_AWESOMECV = "awesomecv"

# ── Encodings ─────────────────────────────────────────────────────
UTF8_ENCODING = "utf-8"
UTF8_SIG_ENCODING = "utf-8-sig"

# ── File extensions ───────────────────────────────────────────────
CSV_EXTENSION = ".csv"
JSON_EXTENSION = ".json"
YAML_EXTENSION = ".yaml"
YML_EXTENSION = ".yml"

# ── Proficiency ordering (shared by rendercv and awesomecv) ───────
PROFICIENCY_ORDER: dict[str, int] = {
    "expert": 0,
    "advanced": 1,
    "intermediate": 2,
    "beginner": 3,
}

# ── Schema URLs ───────────────────────────────────────────────────
RENDERCV_SCHEMA_URL = (
    "https://raw.githubusercontent.com/rendercv/rendercv/refs/tags/v2.8/schema.json"
)
JSONRESUME_SCHEMA_URL = "https://raw.githubusercontent.com/jsonresume/jsonresume.org/refs/heads/master/packages/schema/schema.json"
