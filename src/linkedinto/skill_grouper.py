"""AI-powered skill grouping via LiteLLM.

Groups flat LinkedIn skill lists into logical professional categories
using an LLM. Programming languages are pre-filtered deterministically
(TIOBE + Pygments) so the LLM only categorizes the remaining skills.
Results are cached on disk to avoid repeat API calls.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Required, TypedDict, override

from linkedinto.config import AI_API_KEY_ENV_VAR, AiConfig
from linkedinto.exceptions import AiGroupingError
from linkedinto.language_detector import (
    is_programming_language,
    normalize_language_name,
)
from linkedinto.logger import setup_logger

_logger = setup_logger(__name__)

PROGRAMMING_LANGUAGES = "Programming Languages"
OTHER_CATEGORY = "Other"
LLM_TIMEOUT_SECONDS = 30

CACHE_DIR_NAME = ".cache/linkedinto"
CACHE_FILENAME = "skill-groups.json"


def _default_cache_path() -> Path:
    """Compute the default cache path at call time (not import time)."""
    return Path.home() / CACHE_DIR_NAME / CACHE_FILENAME


class _Message(TypedDict):
    role: str
    content: str


class _JsonSchemaBody(TypedDict):
    name: str
    schema: dict[str, object]


class _ResponseFormat(TypedDict):
    type: str
    json_schema: _JsonSchemaBody


class _CompletionKwargs(TypedDict, total=False):
    """Kwargs passed to litellm.completion; api_key only when configured."""

    model: Required[str]
    messages: Required[list[_Message]]
    response_format: Required[_ResponseFormat]
    timeout: Required[int]
    api_key: str


class Grouper(ABC):
    """Strategy interface for grouping skills into named categories."""

    @abstractmethod
    def group(self, skills: list[str]) -> dict[str, list[str]]:
        """Group skills into a category → skill-list mapping."""
        ...


class CacheStrategy(ABC):
    """Strategy interface for skill-grouping cache backends.

    Implementations must be safe to call repeatedly with the same key
    material; ``get`` returns ``None`` on a cache miss.
    """

    @abstractmethod
    def get(
        self, skills: list[str], tiobe: frozenset[str] | None
    ) -> dict[str, list[str]] | None:
        """Return cached grouping for these skills, or None on miss."""
        ...

    @abstractmethod
    def set(
        self,
        skills: list[str],
        tiobe: frozenset[str] | None,
        value: dict[str, list[str]],
    ) -> None:
        """Store grouping for these skills."""
        ...


class SkillCache(CacheStrategy):
    """Persistent JSON-file cache for LLM skill groupings. Atomic writes, no TTL."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path if path is not None else _default_cache_path()

    def _key(self, skills: list[str], tiobe: frozenset[str] | None) -> str:
        payload = json.dumps([sorted(skills), sorted(tiobe) if tiobe else None])
        return hashlib.sha256(payload.encode()).hexdigest()

    @override
    def get(
        self, skills: list[str], tiobe: frozenset[str] | None
    ) -> dict[str, list[str]] | None:
        """Return cached grouping for these skills, or None on miss."""
        if not self._path.exists():
            return None
        key = self._key(skills, tiobe)
        data = json.loads(self._path.read_text())
        return data.get(key)

    @override
    def set(
        self,
        skills: list[str],
        tiobe: frozenset[str] | None,
        value: dict[str, list[str]],
    ) -> None:
        """Store grouping. Read-modify-write with atomic tempfile rename."""
        key = self._key(skills, tiobe)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data: dict[str, dict[str, list[str]]] = {}
        if self._path.exists():
            data = json.loads(self._path.read_text())
        data[key] = value
        with tempfile.NamedTemporaryFile(
            mode="w", dir=self._path.parent, delete=False, suffix=".tmp"
        ) as f:
            json.dump(data, f)
            f.flush()
            os.fsync(f.fileno())
        Path(f.name).replace(self._path)


class SkillGrouper(Grouper):
    """Group skills into logical categories using an LLM."""

    def __init__(
        self,
        config: AiConfig,
        tiobe_override: frozenset[str] | None = None,
        cache: CacheStrategy | None = None,
    ) -> None:
        self._model = config.model
        self._tiobe_override = tiobe_override
        self._cache: CacheStrategy | None = cache if cache is not None else SkillCache()
        # Resolve API key (don't set litellm.api_key globally — pass per-call)
        self._api_key: str | None = config.api_key or os.environ.get(AI_API_KEY_ENV_VAR)
        # Deterministic skill → category presets (exact-match lookup)
        self._presets: dict[str, str] = {}
        if config.skill_groups:
            for category, preset_skills in config.skill_groups.items():
                for skill in preset_skills:
                    self._presets[skill] = category

    def disable_cache(self) -> None:
        """Skip the disk cache — force a fresh LLM call on next group()."""
        self._cache = None

    @override
    def group(self, skills: list[str]) -> dict[str, list[str]]:
        """Group skills. Returns {} for empty input.

        Pipeline: config presets (deterministic, exact match) → TIOBE/Pygments
        pre-filter → disk cache → LLM. Preset and programming-language skills
        never reach the LLM.
        """
        if not skills:
            return {}

        # 1. Config presets — exact-match, user-controlled, no LLM.
        # A preset targeting PROGRAMMING_LANGUAGES is folded into prog_langs
        # below so the deterministic and preset buckets merge into one.
        preset_groups: dict[str, list[str]] = {}
        preset_prog_langs: list[str] = []
        for skill in skills:
            category = self._presets.get(skill)
            if category is None:
                continue
            if category == PROGRAMMING_LANGUAGES:
                preset_prog_langs.append(skill)
            else:
                preset_groups.setdefault(category, []).append(skill)
        unpreset = [s for s in skills if s not in self._presets]

        # 2. Pre-filter programming languages (deterministic, no LLM);
        #    preset overrides TIOBE detection
        detected = [
            s
            for s in unpreset
            if is_programming_language(s, tiobe_override=self._tiobe_override)
        ]
        prog_langs = preset_prog_langs + [normalize_language_name(s) for s in detected]
        non_prog = [s for s in unpreset if s not in set(detected)]

        _logger.info(
            "AI skill grouping: %d total → %d preset → %d programming languages"
            " → %d sent to LLM",
            len(skills),
            len(skills) - len(unpreset),
            len(prog_langs),
            len(non_prog),
        )

        if not non_prog:
            result = dict(preset_groups)
            if prog_langs:
                result[PROGRAMMING_LANGUAGES] = prog_langs
            return result

        # 3. Check cache
        if self._cache is not None:
            cached = self._cache.get(non_prog, self._tiobe_override)
            if cached is not None:
                _logger.info(
                    "AI skill grouping: cache hit (%d categories)", len(cached)
                )
                merged = self._merge(prog_langs, cached)
                return {**preset_groups, **merged}

        # 4. LLM call — pass the already-defined categories so the LLM can
        #    extend them rather than inventing near-duplicates
        _logger.info(
            "AI skill grouping: calling %s for %d skills...", self._model, len(non_prog)
        )
        known_categories = list(preset_groups)
        if prog_langs:
            known_categories.append(PROGRAMMING_LANGUAGES)
        result = self._call_llm(non_prog, known_categories)
        validated = self._validate(non_prog, result)
        if self._cache is not None:
            self._cache.set(non_prog, self._tiobe_override, validated)
        _logger.info(
            "AI skill grouping: done (%d categories)",
            len(preset_groups) + len(validated) + (1 if prog_langs else 0),
        )

        merged = self._merge(prog_langs, validated)
        return {**preset_groups, **merged}

    def _call_llm(
        self, skills: list[str], known_categories: list[str]
    ) -> dict[str, list[str]]:
        try:
            import litellm
        except ImportError:
            raise AiGroupingError(
                "litellm is not installed. Run: pip install linkedinto[ai]"
            ) from None

        system_prompt = (
            "Group resume skills into logical professional categories. "
            "Return a JSON object mapping category names to arrays of "
            "skill names. Aim for 4-8 categories. Every input skill "
            "must appear in exactly one category. Do not add, remove, "
            "or rename skills. Respond with only the JSON object: "
            "no markdown fences, no commentary, no explanation."
        )
        if known_categories:
            system_prompt += (
                " Prefer reusing these existing categories when a skill fits, "
                "but create new categories when none apply: "
                + ", ".join(known_categories)
                + "."
            )

        kwargs: _CompletionKwargs = {
            "model": self._model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {"role": "user", "content": ", ".join(skills)},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "skill_groups",
                    "schema": {
                        "type": "object",
                        "additionalProperties": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                },
            },
            "timeout": LLM_TIMEOUT_SECONDS,
        }
        if self._api_key:
            kwargs["api_key"] = self._api_key

        try:
            response = litellm.completion(**kwargs)
        except Exception as exc:
            raise AiGroupingError(f"LLM call to {self._model} failed: {exc}") from exc

        raw = response.choices[0].message.content
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise AiGroupingError(f"LLM returned invalid JSON: {raw[:200]}") from exc
        if not isinstance(parsed, dict):
            raise AiGroupingError(f"LLM returned non-object JSON: {raw[:200]}")
        return parsed

    def _validate(
        self, skills: list[str], result: dict[str, list[str]]
    ) -> dict[str, list[str]]:
        """Validate LLM response: strip extras, fill gaps, deduplicate.

        Every input skill ends up in exactly one category. If the LLM
        places a skill in multiple categories, the first occurrence wins.
        """
        input_set = set(skills)
        grouped: set[str] = set()
        validated: dict[str, list[str]] = {}

        for category, group_skills in result.items():
            # Strip skills the LLM invented or already grouped elsewhere
            filtered = [s for s in group_skills if s in input_set and s not in grouped]
            if filtered:
                validated[category] = filtered
                grouped.update(filtered)

        # Any skill the LLM missed → "Other" (merging with an LLM-provided
        # "Other" category rather than overwriting it)
        missing = input_set - grouped
        if missing:
            other = validated.setdefault(OTHER_CATEGORY, [])
            other.extend(sorted(missing))

        return validated

    def _merge(
        self, prog_langs: list[str], llm_groups: dict[str, list[str]]
    ) -> dict[str, list[str]]:
        """Prepend programming languages, deduplicating category name."""
        result: dict[str, list[str]] = {}
        if prog_langs:
            # If LLM also produced a "Programming Languages" category, merge into ours
            existing = llm_groups.pop(PROGRAMMING_LANGUAGES, [])
            result[PROGRAMMING_LANGUAGES] = prog_langs + existing
        result.update(llm_groups)
        return result
