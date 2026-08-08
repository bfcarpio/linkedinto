"""Tests for the Typer CLI interface."""

from __future__ import annotations

import json
import os
import tempfile
import zipfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from linkedinto.cli import app
from linkedinto.config import DEFAULT_AI_MODEL, AiConfig
from linkedinto.constants import RENDERC_YAML_FILE, RESUME_JSON_FILE

runner = CliRunner()


SAMPLE_CSV = """Profile.csv,First Name,Last Name,Occupation,EmailAddress,Headline
Profile.csv,John,Smith,Engineer,john@example.com,Senior Dev
Skills.csv,Name,Proficiency
Skills.csv,Python,Expert
"""


def _make_zip(data: str = SAMPLE_CSV) -> Path:
    fd, path = tempfile.mkstemp(suffix=".zip")
    os.close(fd)
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("data.csv", data)
    return Path(path)


class TestCli:
    def test_convert_help(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "linkedinto" in result.stdout

    def test_convert_missing_file(self) -> None:
        result = runner.invoke(app, ["convert", "/tmp/nonexistent.zip"])
        assert result.exit_code == 2  # Typer error for invalid path

    def test_convert_outputs_both(self) -> None:
        zip_path = _make_zip()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(
                app, ["convert", str(zip_path), "--output-dir", tmpdir]
            )
            assert result.exit_code == 0, result.output
            assert RESUME_JSON_FILE in result.output or "✅" in result.output
            json_path = Path(tmpdir) / RESUME_JSON_FILE
            yaml_path = Path(tmpdir) / RENDERC_YAML_FILE
            assert json_path.exists()
            assert yaml_path.exists()
            data = json.loads(json_path.read_text())
            assert data["basics"]["name"] == "John Smith"
        zip_path.unlink()

    def test_convert_jsonresume_only(self) -> None:
        zip_path = _make_zip()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(
                app,
                ["convert", str(zip_path), "--output-dir", tmpdir, "--jsonresume-only"],
            )
            assert result.exit_code == 0
            json_path = Path(tmpdir) / RESUME_JSON_FILE
            yaml_path = Path(tmpdir) / RENDERC_YAML_FILE
            assert json_path.exists()
            assert not yaml_path.exists()
        zip_path.unlink()

    def test_convert_rendercv_only(self) -> None:
        zip_path = _make_zip()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(
                app,
                ["convert", str(zip_path), "--output-dir", tmpdir, "--rendercv-only"],
            )
            assert result.exit_code == 0
            json_path = Path(tmpdir) / RESUME_JSON_FILE
            yaml_path = Path(tmpdir) / RENDERC_YAML_FILE
            assert not json_path.exists()
            assert yaml_path.exists()
        zip_path.unlink()


class _FakeGrouper:
    """Records construction and disable_cache calls; returns canned groups."""

    instances: list[_FakeGrouper] = []

    def __init__(
        self, config: AiConfig, tiobe_override: frozenset[str] | None = None
    ) -> None:
        self.config = config
        self.tiobe_override = tiobe_override
        self.cache_disabled = False
        _FakeGrouper.instances.append(self)

    def disable_cache(self) -> None:
        self.cache_disabled = True

    def group(self, skills: list[str]) -> dict[str, list[str]]:
        return {"DevOps": ["Docker", "Kubernetes"]}


AI_CONFIG_TOML = f'[ai]\nmodel = "{DEFAULT_AI_MODEL}"\n'

MODEL_OVERRIDE = "anthropic/claude-3-haiku-20240307"


class TestCliAiFlags:
    def _setup(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
        _FakeGrouper.instances = []
        monkeypatch.setattr("linkedinto.orchestrator.SkillGrouper", _FakeGrouper)
        monkeypatch.chdir(tmp_path)
        (tmp_path / "linkedinto.toml").write_text(AI_CONFIG_TOML)
        return _make_zip()

    def test_ai_preview_prints_to_stdout_no_files(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        zip_path = self._setup(tmp_path, monkeypatch)
        out_dir = tmp_path / "out"
        result = runner.invoke(
            app,
            [
                "convert",
                str(zip_path),
                "--output-dir",
                str(out_dir),
                "--ai-group",
                "--ai-preview",
            ],
        )
        assert result.exit_code == 0, result.output
        groups = json.loads(result.stdout)
        assert groups == {"DevOps": ["Docker", "Kubernetes"]}
        assert not (out_dir / RESUME_JSON_FILE).exists()
        assert not (out_dir / RENDERC_YAML_FILE).exists()

    def test_ai_group_writes_grouped_output(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        zip_path = self._setup(tmp_path, monkeypatch)
        out_dir = tmp_path / "out"
        result = runner.invoke(
            app,
            ["convert", str(zip_path), "--output-dir", str(out_dir), "--ai-group"],
        )
        assert result.exit_code == 0, result.output
        data = json.loads((out_dir / RESUME_JSON_FILE).read_text())
        assert data["skills"] == [
            {"name": "DevOps", "keywords": ["Docker", "Kubernetes"]}
        ]

    def test_no_cache_disables_cache(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        zip_path = self._setup(tmp_path, monkeypatch)
        result = runner.invoke(
            app,
            [
                "convert",
                str(zip_path),
                "--output-dir",
                str(tmp_path / "out"),
                "--ai-group",
                "--no-cache",
            ],
        )
        assert result.exit_code == 0, result.output
        assert len(_FakeGrouper.instances) == 1
        assert _FakeGrouper.instances[0].cache_disabled is True

    def test_cache_enabled_by_default(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        zip_path = self._setup(tmp_path, monkeypatch)
        result = runner.invoke(
            app,
            [
                "convert",
                str(zip_path),
                "--output-dir",
                str(tmp_path / "out"),
                "--ai-group",
            ],
        )
        assert result.exit_code == 0, result.output
        assert _FakeGrouper.instances[0].cache_disabled is False

    def test_ai_model_overrides_config(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        zip_path = self._setup(tmp_path, monkeypatch)
        result = runner.invoke(
            app,
            [
                "convert",
                str(zip_path),
                "--output-dir",
                str(tmp_path / "out"),
                "--ai-group",
                "--ai-model",
                MODEL_OVERRIDE,
            ],
        )
        assert result.exit_code == 0, result.output
        config = _FakeGrouper.instances[0].config
        assert config.model == MODEL_OVERRIDE

    def test_ai_group_without_ai_config_errors(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _FakeGrouper.instances = []
        monkeypatch.setattr("linkedinto.orchestrator.SkillGrouper", _FakeGrouper)
        monkeypatch.chdir(tmp_path)  # no linkedinto.toml here
        zip_path = _make_zip()
        result = runner.invoke(
            app,
            [
                "convert",
                str(zip_path),
                "--output-dir",
                str(tmp_path / "out"),
                "--ai-group",
            ],
        )
        assert result.exit_code == 1
        assert "[ai]" in result.output
