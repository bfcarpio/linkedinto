"""Tests for AI skill grouping: SkillCache and SkillGrouper."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import NoReturn, TypedDict, Unpack, override

import pytest

from linkedinto.config import AiConfig
from linkedinto.exceptions import AiGroupingError
from linkedinto.skill_grouper import (
    PROGRAMMING_LANGUAGES,
    CacheStrategy,
    SkillCache,
    SkillGrouper,
)


class _RecordedCall(TypedDict, total=False):
    """Kwargs captured from a litellm.completion call."""

    model: str
    messages: list[dict[str, str]]
    response_format: dict[str, object]
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


def _grouper(tmp_path: Path, *, api_key: str | None = None) -> SkillGrouper:
    """SkillGrouper with an isolated on-disk cache."""
    return SkillGrouper(
        AiConfig(api_key=api_key), cache=SkillCache(tmp_path / "skill-groups.json")
    )


class TestSkillCache:
    def test_round_trip(self, tmp_path: Path) -> None:
        cache = SkillCache(tmp_path / "c.json")
        value = {"DevOps": ["Docker", "Kubernetes"]}
        cache.set(["Docker", "Kubernetes"], None, value)
        assert cache.get(["Docker", "Kubernetes"], None) == value

    def test_skill_order_irrelevant(self, tmp_path: Path) -> None:
        cache = SkillCache(tmp_path / "c.json")
        value = {"DevOps": ["Docker"]}
        cache.set(["Docker", "Kubernetes"], None, value)
        assert cache.get(["Kubernetes", "Docker"], None) == value

    def test_tiobe_override_changes_key(self, tmp_path: Path) -> None:
        cache = SkillCache(tmp_path / "c.json")
        cache.set(["Docker"], None, {"DevOps": ["Docker"]})
        assert cache.get(["Docker"], frozenset({"customlang"})) is None
        assert cache.get(["Docker"], None) == {"DevOps": ["Docker"]}

    def test_miss_on_empty_cache(self, tmp_path: Path) -> None:
        cache = SkillCache(tmp_path / "c.json")
        assert cache.get(["Docker"], None) is None

    def test_atomic_write_leaves_no_tmp_files(self, tmp_path: Path) -> None:
        cache = SkillCache(tmp_path / "c.json")
        cache.set(["Docker"], None, {"DevOps": ["Docker"]})
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
        _patch_completion(monkeypatch, {"DevOps": ["Kubernetes"]}, calls)

        grouper = _grouper(tmp_path)
        result = grouper.group(["Python", "Go", "Kubernetes"])

        assert result[PROGRAMMING_LANGUAGES] == ["Python", "Go"]
        assert result["DevOps"] == ["Kubernetes"]
        # LLM only saw the non-programming skill
        user_msg = calls[0]["messages"][1]["content"]
        assert user_msg == "Kubernetes"

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
        _patch_completion(monkeypatch, {"DevOps": ["Kubernetes"]}, calls)

        grouper = _grouper(tmp_path)
        first = grouper.group(["Kubernetes"])
        second = grouper.group(["Kubernetes"])

        assert first == second == {"DevOps": ["Kubernetes"]}
        assert len(calls) == 1

    def test_disable_cache_forces_fresh_call(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[_RecordedCall] = []
        _patch_completion(monkeypatch, {"DevOps": ["Kubernetes"]}, calls)

        grouper = _grouper(tmp_path)
        grouper.group(["Kubernetes"])
        grouper.disable_cache()
        grouper.group(["Kubernetes"])

        assert len(calls) == 2

    def test_invented_skills_stripped_missing_go_to_other(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        payload = {"DevOps": ["Kubernetes", "Invented Skill"], "Empty": []}
        _patch_completion(monkeypatch, payload, [])

        grouper = _grouper(tmp_path)
        result = grouper.group(["Kubernetes", "Team Leadership"])

        assert result == {
            "DevOps": ["Kubernetes"],
            "Other": ["Team Leadership"],
        }

    def test_duplicate_skill_in_two_categories_keeps_first(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        payload = {
            "DevOps": ["Kubernetes", "Team Leadership"],
            "Management": ["Kubernetes"],
        }
        _patch_completion(monkeypatch, payload, [])

        grouper = _grouper(tmp_path)
        result = grouper.group(["Kubernetes", "Team Leadership"])

        assert result == {
            "DevOps": ["Kubernetes", "Team Leadership"],
        }
        # Skill appears in exactly one category
        all_skills = [s for skills in result.values() for s in skills]
        assert len(all_skills) == len(set(all_skills))

    def test_llm_other_category_merged_with_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """LLM-provided 'Other' skills must not be lost when gaps are filled."""
        payload = {"DevOps": ["Kubernetes"], "Other": ["Team Leadership"]}
        _patch_completion(monkeypatch, payload, [])

        grouper = _grouper(tmp_path)
        result = grouper.group(["Kubernetes", "Team Leadership", "Agile Coaching"])

        assert result == {
            "DevOps": ["Kubernetes"],
            "Other": ["Team Leadership", "Agile Coaching"],
        }

    def test_llm_programming_languages_category_merged(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        payload = {PROGRAMMING_LANGUAGES: ["Kubernetes"]}
        _patch_completion(monkeypatch, payload, [])

        grouper = _grouper(tmp_path)
        result = grouper.group(["Python", "Kubernetes"])

        assert result == {PROGRAMMING_LANGUAGES: ["Python", "Kubernetes"]}

    def test_tiobe_override_passed_to_prefilter(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[_RecordedCall] = []
        _patch_completion(monkeypatch, {"DevOps": ["Kubernetes"]}, calls)

        grouper = SkillGrouper(
            AiConfig(),
            tiobe_override=frozenset({"customlang"}),
            cache=SkillCache(tmp_path / "c.json"),
        )
        result = grouper.group(["CustomLang", "Kubernetes"])

        assert result[PROGRAMMING_LANGUAGES] == ["CustomLang"]
        assert calls[0]["messages"][1]["content"] == "Kubernetes"

    def test_api_key_from_config_passed_per_call(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[_RecordedCall] = []
        _patch_completion(monkeypatch, {"DevOps": ["Kubernetes"]}, calls)
        monkeypatch.setenv("LINKEDINTO_AI_API_KEY", "sk-env")

        import litellm

        key_before = litellm.api_key
        grouper = _grouper(tmp_path, api_key="sk-config")
        grouper.group(["Kubernetes"])

        assert calls[0].get("api_key") == "sk-config"
        assert litellm.api_key == key_before  # never set globally

    def test_api_key_env_fallback(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[_RecordedCall] = []
        _patch_completion(monkeypatch, {"DevOps": ["Kubernetes"]}, calls)
        monkeypatch.setenv("LINKEDINTO_AI_API_KEY", "sk-env")

        grouper = _grouper(tmp_path)
        grouper.group(["Kubernetes"])

        assert calls[0].get("api_key") == "sk-env"

    def test_no_api_key_omits_kwarg(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[_RecordedCall] = []
        _patch_completion(monkeypatch, {"DevOps": ["Kubernetes"]}, calls)
        monkeypatch.delenv("LINKEDINTO_AI_API_KEY", raising=False)

        grouper = _grouper(tmp_path)
        grouper.group(["Kubernetes"])

        assert "api_key" not in calls[0]

    def test_missing_litellm_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setitem(sys.modules, "litellm", None)

        grouper = _grouper(tmp_path)
        with pytest.raises(AiGroupingError, match="pip install"):
            grouper.group(["Kubernetes"])

    def test_llm_failure_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def failing_completion(**kwargs: object) -> NoReturn:
            raise ConnectionError("network down")

        monkeypatch.setattr("litellm.completion", failing_completion)

        grouper = _grouper(tmp_path)
        with pytest.raises(AiGroupingError, match="network down"):
            grouper.group(["Kubernetes"])

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
            grouper.group(["Kubernetes"])

    def test_non_object_json_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_completion(monkeypatch, ["not", "an", "object"], [])

        grouper = _grouper(tmp_path)
        with pytest.raises(AiGroupingError, match="non-object JSON"):
            grouper.group(["Kubernetes"])

    def test_timeout_and_response_format_passed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[_RecordedCall] = []
        _patch_completion(monkeypatch, {"DevOps": ["Kubernetes"]}, calls)

        grouper = _grouper(tmp_path)
        grouper.group(["Kubernetes"])

        assert calls[0]["timeout"] == 30
        assert calls[0]["model"] == "openai/gpt-4o-mini"
        assert calls[0]["response_format"]["type"] == "json_schema"
        system_msg = calls[0]["messages"][0]["content"]
        assert "only the JSON object" in system_msg

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
        _patch_completion(monkeypatch, {"DevOps": ["Kubernetes"]}, calls)

        cache = InMemoryCache()
        grouper = SkillGrouper(AiConfig(), cache=cache)
        grouper.group(["Kubernetes"])
        grouper.group(["Kubernetes"])  # served from in-memory cache

        assert len(calls) == 1
        assert cache.store == {"Kubernetes": {"DevOps": ["Kubernetes"]}}
