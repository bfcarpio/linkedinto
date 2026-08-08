"""Tests for AI skill grouping: SkillCache and SkillGrouper."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import NoReturn, TypedDict, Unpack, override

import pytest

from linkedinto.config import AI_API_KEY_ENV_VAR, DEFAULT_AI_MODEL, AiConfig
from linkedinto.exceptions import AiGroupingError
from linkedinto.skill_grouper import (
    OTHER_CATEGORY,
    PROGRAMMING_LANGUAGES,
    CacheStrategy,
    SkillCache,
    SkillGrouper,
)

DEVOPS = "DevOps"
KUBERNETES = "Kubernetes"
TEAM_LEADERSHIP = "Team Leadership"


class _RecordedCall(TypedDict, total=False):
    """Kwargs captured from a litellm.completion call."""

    model: str
    messages: list[dict[str, str]]
    response_format: dict[str, object]
    num_retries: int
    timeout: int
    api_key: str


def _make_response(payload: object) -> SimpleNamespace:
    """Build a fake litellm completion response wrapping a JSON payload."""
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)))]
    )


def _patch_completion(
    monkeypatch: pytest.MonkeyPatch,
    payload: object,
    calls: list[_RecordedCall],
) -> None:
    """Patch litellm.completion to record calls and return a canned payload."""

    def fake_completion(**kwargs: Unpack[_RecordedCall]) -> SimpleNamespace:
        calls.append(kwargs)
        return _make_response(payload)

    monkeypatch.setattr("litellm.completion", fake_completion)


def _grouper(
    tmp_path: Path,
    *,
    api_key: str | None = None,
    skill_groups: dict[str, list[str]] | None = None,
) -> SkillGrouper:
    """SkillGrouper with an isolated on-disk cache."""
    return SkillGrouper(
        AiConfig(api_key=api_key, skill_groups=skill_groups),
        cache=SkillCache(tmp_path / "skill-groups.json"),
    )


class TestSkillCache:
    def test_round_trip(self, tmp_path: Path) -> None:
        cache = SkillCache(tmp_path / "c.json")
        value = {DEVOPS: ["Docker", KUBERNETES]}
        cache.set(["Docker", KUBERNETES], None, value)
        assert cache.get(["Docker", KUBERNETES], None) == value

    def test_skill_order_irrelevant(self, tmp_path: Path) -> None:
        cache = SkillCache(tmp_path / "c.json")
        value = {DEVOPS: ["Docker"]}
        cache.set(["Docker", KUBERNETES], None, value)
        assert cache.get([KUBERNETES, "Docker"], None) == value

    def test_tiobe_override_changes_key(self, tmp_path: Path) -> None:
        cache = SkillCache(tmp_path / "c.json")
        cache.set(["Docker"], None, {DEVOPS: ["Docker"]})
        assert cache.get(["Docker"], frozenset({"customlang"})) is None
        assert cache.get(["Docker"], None) == {DEVOPS: ["Docker"]}

    def test_miss_on_empty_cache(self, tmp_path: Path) -> None:
        cache = SkillCache(tmp_path / "c.json")
        assert cache.get(["Docker"], None) is None

    def test_atomic_write_leaves_no_tmp_files(self, tmp_path: Path) -> None:
        cache = SkillCache(tmp_path / "c.json")
        cache.set(["Docker"], None, {DEVOPS: ["Docker"]})
        assert (tmp_path / "c.json").exists()
        assert list(tmp_path.glob("*.tmp")) == []


class TestSkillGrouper:
    def test_empty_input(self, tmp_path: Path) -> None:
        grouper = _grouper(tmp_path)
        assert grouper.group([]) == {}

    def test_programming_languages_prefiltered(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[_RecordedCall] = []
        _patch_completion(monkeypatch, {DEVOPS: [KUBERNETES]}, calls)

        grouper = _grouper(tmp_path)
        result = grouper.group(["Python", "Go", KUBERNETES])

        assert result[PROGRAMMING_LANGUAGES] == ["Python", "Go"]
        assert result[DEVOPS] == [KUBERNETES]
        # LLM only saw the non-programming skill
        user_msg = calls[0]["messages"][1]["content"]
        assert user_msg == KUBERNETES

    def test_programming_language_name_normalized_in_output(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[_RecordedCall] = []
        _patch_completion(monkeypatch, {DEVOPS: [KUBERNETES]}, calls)
        grouper = _grouper(tmp_path)
        result = grouper.group(["Python", "Go (Programming Language)", KUBERNETES])

        # Suffix stripped → "Go"; Python passes through unchanged.
        assert result[PROGRAMMING_LANGUAGES] == ["Python", "Go"]
        assert result[DEVOPS] == [KUBERNETES]

    def test_all_programming_languages_skips_llm(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[_RecordedCall] = []
        _patch_completion(monkeypatch, {}, calls)

        grouper = _grouper(tmp_path)
        result = grouper.group(["Python", "Rust"])

        assert result == {PROGRAMMING_LANGUAGES: ["Python", "Rust"]}
        assert calls == []

    def test_cache_hit_avoids_second_call(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[_RecordedCall] = []
        _patch_completion(monkeypatch, {DEVOPS: [KUBERNETES]}, calls)

        grouper = _grouper(tmp_path)
        first = grouper.group([KUBERNETES])
        second = grouper.group([KUBERNETES])

        assert first == second == {DEVOPS: [KUBERNETES]}
        assert len(calls) == 1

    def test_disable_cache_forces_fresh_call(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[_RecordedCall] = []
        _patch_completion(monkeypatch, {DEVOPS: [KUBERNETES]}, calls)

        grouper = _grouper(tmp_path)
        grouper.group([KUBERNETES])
        grouper.disable_cache()
        grouper.group([KUBERNETES])

        assert len(calls) == 2

    def test_invented_skills_stripped_missing_go_to_other(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        payload = {"DevOps": [KUBERNETES, "Invented Skill"], "Empty": []}
        _patch_completion(monkeypatch, payload, [])

        grouper = _grouper(tmp_path)
        result = grouper.group([KUBERNETES, TEAM_LEADERSHIP])

        assert result == {
            DEVOPS: [KUBERNETES],
            OTHER_CATEGORY: [TEAM_LEADERSHIP],
        }

    def test_duplicate_skill_in_two_categories_keeps_first(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        payload = {
            "DevOps": [KUBERNETES, TEAM_LEADERSHIP],
            "Management": [KUBERNETES],
        }
        _patch_completion(monkeypatch, payload, [])

        grouper = _grouper(tmp_path)
        result = grouper.group([KUBERNETES, TEAM_LEADERSHIP])

        assert result == {
            "DevOps": [KUBERNETES, TEAM_LEADERSHIP],
        }
        # Skill appears in exactly one category
        all_skills = [s for skills in result.values() for s in skills]
        assert len(all_skills) == len(set(all_skills))

    def test_llm_other_category_merged_with_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """LLM-provided 'Other' skills must not be lost when gaps are filled."""
        payload = {DEVOPS: [KUBERNETES], OTHER_CATEGORY: [TEAM_LEADERSHIP]}
        _patch_completion(monkeypatch, payload, [])

        grouper = _grouper(tmp_path)
        result = grouper.group([KUBERNETES, TEAM_LEADERSHIP, "Agile Coaching"])

        assert result == {
            DEVOPS: [KUBERNETES],
            OTHER_CATEGORY: [TEAM_LEADERSHIP, "Agile Coaching"],
        }

    def test_llm_programming_languages_category_merged(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        payload = {PROGRAMMING_LANGUAGES: [KUBERNETES]}
        _patch_completion(monkeypatch, payload, [])

        grouper = _grouper(tmp_path)
        result = grouper.group(["Python", KUBERNETES])

        assert result == {PROGRAMMING_LANGUAGES: ["Python", KUBERNETES]}

    def test_tiobe_override_passed_to_prefilter(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[_RecordedCall] = []
        _patch_completion(monkeypatch, {DEVOPS: [KUBERNETES]}, calls)

        grouper = SkillGrouper(
            AiConfig(),
            tiobe_override=frozenset({"customlang"}),
            cache=SkillCache(tmp_path / "c.json"),
        )
        result = grouper.group(["CustomLang", KUBERNETES])

        assert result[PROGRAMMING_LANGUAGES] == ["CustomLang"]
        assert calls[0]["messages"][1]["content"] == KUBERNETES

    def test_api_key_from_config_passed_per_call(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[_RecordedCall] = []
        _patch_completion(monkeypatch, {DEVOPS: [KUBERNETES]}, calls)
        monkeypatch.setenv(AI_API_KEY_ENV_VAR, "sk-env")

        import litellm

        key_before = litellm.api_key
        grouper = _grouper(tmp_path, api_key="sk-config")
        grouper.group([KUBERNETES])

        assert calls[0].get("api_key") == "sk-config"
        assert litellm.api_key == key_before  # never set globally

    def test_api_key_env_fallback(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[_RecordedCall] = []
        _patch_completion(monkeypatch, {DEVOPS: [KUBERNETES]}, calls)
        monkeypatch.setenv(AI_API_KEY_ENV_VAR, "sk-env")

        grouper = _grouper(tmp_path)
        grouper.group([KUBERNETES])

        assert calls[0].get("api_key") == "sk-env"

    def test_no_api_key_omits_kwarg(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[_RecordedCall] = []
        _patch_completion(monkeypatch, {DEVOPS: [KUBERNETES]}, calls)
        monkeypatch.delenv(AI_API_KEY_ENV_VAR, raising=False)

        grouper = _grouper(tmp_path)
        grouper.group([KUBERNETES])

        assert "api_key" not in calls[0]

    def test_missing_litellm_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setitem(sys.modules, "litellm", None)

        grouper = _grouper(tmp_path)
        with pytest.raises(AiGroupingError, match="pip install"):
            grouper.group([KUBERNETES])

    def test_llm_failure_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def failing_completion(**kwargs: object) -> NoReturn:
            raise ConnectionError("network down")

        monkeypatch.setattr("litellm.completion", failing_completion)

        grouper = _grouper(tmp_path)
        with pytest.raises(AiGroupingError, match="network down"):
            grouper.group([KUBERNETES])

    def test_invalid_json_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def bad_json_completion(**kwargs: object) -> SimpleNamespace:
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="not json{"))]
            )

        monkeypatch.setattr("litellm.completion", bad_json_completion)

        grouper = _grouper(tmp_path)
        with pytest.raises(AiGroupingError, match="invalid JSON"):
            grouper.group([KUBERNETES])

    def test_non_object_json_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_completion(monkeypatch, ["not", "an", "object"], [])

        grouper = _grouper(tmp_path)
        with pytest.raises(AiGroupingError, match="non-object JSON"):
            grouper.group([KUBERNETES])

    def test_timeout_and_response_format_passed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[_RecordedCall] = []
        _patch_completion(monkeypatch, {DEVOPS: [KUBERNETES]}, calls)

        grouper = _grouper(tmp_path)
        grouper.group([KUBERNETES])

        assert calls[0]["timeout"] == 30
        assert calls[0]["model"] == DEFAULT_AI_MODEL
        assert calls[0]["response_format"]["type"] == "json_schema"
        system_msg = calls[0]["messages"][0]["content"]
        assert "only the JSON object" in system_msg

    def test_presets_bypass_llm(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Preset skills are never sent to the LLM; only the remainder is."""
        calls: list[_RecordedCall] = []
        _patch_completion(monkeypatch, {DEVOPS: [KUBERNETES]}, calls)

        grouper = _grouper(
            tmp_path,
            skill_groups={
                "Tools & Technologies": ["Docker", "Git"],
                "Interpersonal Skills": ["Mentoring"],
            },
        )
        result = grouper.group(["Docker", "Git", "Mentoring", KUBERNETES])

        assert result == {
            "Tools & Technologies": ["Docker", "Git"],
            "Interpersonal Skills": ["Mentoring"],
            DEVOPS: [KUBERNETES],
        }
        # Only the non-preset skill reached the LLM
        assert calls[0]["messages"][1]["content"] == KUBERNETES

    def test_presets_cover_all_skills_skips_llm(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When every skill is preset, no LLM call happens."""
        calls: list[_RecordedCall] = []
        _patch_completion(monkeypatch, {}, calls)

        grouper = _grouper(
            tmp_path,
            skill_groups={
                "Tools & Technologies": ["Docker"],
                "Industry Knowledge": ["Agile Methodologies"],
            },
        )
        result = grouper.group(["Docker", "Agile Methodologies"])

        assert result == {
            "Tools & Technologies": ["Docker"],
            "Industry Knowledge": ["Agile Methodologies"],
        }
        assert calls == []

    def test_preset_win_over_tiobe(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A preset for a programming language overrides TIOBE detection."""
        calls: list[_RecordedCall] = []
        _patch_completion(monkeypatch, {DEVOPS: [KUBERNETES]}, calls)

        grouper = _grouper(
            tmp_path,
            skill_groups={PROGRAMMING_LANGUAGES: ["Rust"]},
        )
        result = grouper.group(["Rust", "Python", KUBERNETES])

        # "Rust" is preset, "Python" detected via TIOBE — both land in one
        # merged Programming Languages category (preset first).
        assert result[PROGRAMMING_LANGUAGES] == ["Rust", "Python"]
        assert calls[0]["messages"][1]["content"] == KUBERNETES

    def test_known_categories_included_in_prompt(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Preset + TIOBE categories are surfaced to the LLM as reusable."""
        calls: list[_RecordedCall] = []
        _patch_completion(monkeypatch, {DEVOPS: [KUBERNETES]}, calls)

        grouper = _grouper(
            tmp_path,
            skill_groups={"Tools & Technologies": ["Docker"]},
        )
        grouper.group(["Docker", "Python", KUBERNETES])

        system_msg = calls[0]["messages"][0]["content"]
        assert "Tools & Technologies" in system_msg
        assert PROGRAMMING_LANGUAGES in system_msg
        assert "Prefer reusing these existing categories" in system_msg

    def test_no_known_categories_omits_hint(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Without presets or languages, no category hint is added."""
        calls: list[_RecordedCall] = []
        _patch_completion(monkeypatch, {DEVOPS: [KUBERNETES]}, calls)

        grouper = _grouper(tmp_path)
        grouper.group([KUBERNETES])

        system_msg = calls[0]["messages"][0]["content"]
        assert "Prefer reusing these existing categories" not in system_msg

    def test_custom_cache_strategy_accepted(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Any CacheStrategy implementation can back the grouper."""

        class InMemoryCache(CacheStrategy):
            def __init__(self) -> None:
                self.store: dict[str, dict[str, list[str]]] = {}

            def _key(self, skills: list[str], tiobe: frozenset[str] | None) -> str:
                return ",".join(sorted(skills))

            @override
            def get(
                self, skills: list[str], tiobe: frozenset[str] | None
            ) -> dict[str, list[str]] | None:
                return self.store.get(self._key(skills, tiobe))

            @override
            def set(
                self,
                skills: list[str],
                tiobe: frozenset[str] | None,
                value: dict[str, list[str]],
            ) -> None:
                self.store[self._key(skills, tiobe)] = value

        calls: list[_RecordedCall] = []
        _patch_completion(monkeypatch, {DEVOPS: [KUBERNETES]}, calls)

        cache = InMemoryCache()
        grouper = SkillGrouper(AiConfig(), cache=cache)
        grouper.group([KUBERNETES])
        grouper.group([KUBERNETES])  # served from in-memory cache

        assert len(calls) == 1
        assert cache.store == {KUBERNETES: {DEVOPS: [KUBERNETES]}}

    def test_num_retries_passed_to_litellm(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify num_retries=3 is passed to litellm.completion."""

        calls: list[_RecordedCall] = []
        _patch_completion(monkeypatch, {"skills": []}, calls)

        grouper = _grouper(tmp_path)
        grouper.group([KUBERNETES])

        assert len(calls) == 1
        # Verify num_retries=3 was passed via the patched function
        assert "num_retries" in calls[0]
        assert calls[0]["num_retries"] == 3
