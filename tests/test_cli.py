"""Tests for the Typer CLI interface."""

from __future__ import annotations

import json
import os
import tempfile
import zipfile
from pathlib import Path

from typer.testing import CliRunner

from linkedinto.cli import app
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
