"""Integration tests: full pipeline with real LinkedIn export format."""

from __future__ import annotations

import os
import tempfile
import zipfile
from pathlib import Path

import pytest
import yaml

from linkedinto.converter_jsonresume import JsonResumeConverter
from linkedinto.converter_rendercv import RenderCvConverter
from linkedinto.overwriter import overwrite
from linkedinto.parser import LinkedinZipParser

FIXTURES = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> str:
    """Load a fixture CSV file content."""
    return (FIXTURES / name).read_text(encoding="utf-8")


def _make_multi_csv_zip(csv_files: dict[str, str]) -> Path:
    """Create a ZIP containing multiple CSV files (one per section)."""
    fd, path = tempfile.mkstemp(suffix=".zip")
    os.close(fd)
    with zipfile.ZipFile(path, "w") as zf:
        for csv_name, content in csv_files.items():
            zf.writestr(csv_name, content)
    return Path(path)


class TestMultiCsvParser:
    """Test parser with real LinkedIn multi-CSV format."""

    def test_parse_profile(self) -> None:
        csvs = {"Profile.csv": _load_fixture("minimal_profile.csv")}
        path = _make_multi_csv_zip(csvs)
        parser = LinkedinZipParser()
        data = parser.parse(path)
        assert data.profile is not None
        assert data.profile.first_name == "John"
        assert data.profile.last_name == "Smith"
        assert data.profile.occupation == "Software Engineer"
        path.unlink()

    def test_parse_positions(self) -> None:
        csvs = {"Positions.csv": _load_fixture("minimal_positions.csv")}
        path = _make_multi_csv_zip(csvs)
        parser = LinkedinZipParser()
        data = parser.parse(path)
        assert len(data.positions) == 1
        assert data.positions[0].company == "Acme Corp"
        assert data.positions[0].position == "Senior Dev"
        path.unlink()

    def test_parse_skills(self) -> None:
        csvs = {"Skills.csv": _load_fixture("minimal_skills.csv")}
        path = _make_multi_csv_zip(csvs)
        parser = LinkedinZipParser()
        data = parser.parse(path)
        assert len(data.skills) == 6
        names = [s.name for s in data.skills]
        assert "Python" in names
        assert "Rust" in names
        path.unlink()

    def test_parse_education(self) -> None:
        csvs = {"Education.csv": _load_fixture("minimal_education.csv")}
        path = _make_multi_csv_zip(csvs)
        parser = LinkedinZipParser()
        data = parser.parse(path)
        assert len(data.education) == 1
        assert data.education[0].school == "MIT"
        path.unlink()

    def test_parse_languages(self) -> None:
        csvs = {"Languages.csv": _load_fixture("minimal_languages.csv")}
        path = _make_multi_csv_zip(csvs)
        parser = LinkedinZipParser()
        data = parser.parse(path)
        assert len(data.languages) == 2
        names = [lang.name for lang in data.languages]
        assert "English" in names
        path.unlink()

    def test_parse_complete_profile(self) -> None:
        """Test parsing all sections together (real export simulation)."""
        csvs = {
            "Profile.csv": _load_fixture("minimal_profile.csv"),
            "Positions.csv": _load_fixture("minimal_positions.csv"),
            "Education.csv": _load_fixture("minimal_education.csv"),
            "Skills.csv": _load_fixture("minimal_skills.csv"),
            "Languages.csv": _load_fixture("minimal_languages.csv"),
        }
        path = _make_multi_csv_zip(csvs)
        parser = LinkedinZipParser()
        data = parser.parse(path)
        assert data.profile is not None
        assert data.profile.first_name == "John"
        assert len(data.positions) == 1
        assert len(data.education) == 1
        assert len(data.skills) == 6
        assert len(data.languages) == 2
        path.unlink()

    def test_ignores_non_section_csvs(self) -> None:
        """CSVs that don't match any section handler should be ignored."""
        csvs = {
            "Profile.csv": _load_fixture("minimal_profile.csv"),
            "Ad_Targeting.csv": "Interest,Value\nTech,High\n",
            "Company Follows.csv": "Name,Followed On\nAcme,2024-01\n",
        }
        path = _make_multi_csv_zip(csvs)
        parser = LinkedinZipParser()
        data = parser.parse(path)
        # Profile should still be parsed; unknown CSVs silently skipped
        assert data.profile is not None
        assert data.profile.first_name == "John"
        path.unlink()


class TestIntegrationPipeline:
    """End-to-end integration tests: parser → converters → output."""

    def test_full_pipeline_produces_nonempty_jsonresume(self) -> None:
        csvs = {
            "Profile.csv": _load_fixture("minimal_profile.csv"),
            "Positions.csv": _load_fixture("minimal_positions.csv"),
            "Education.csv": _load_fixture("minimal_education.csv"),
            "Skills.csv": _load_fixture("minimal_skills.csv"),
            "Languages.csv": _load_fixture("minimal_languages.csv"),
        }
        path = _make_multi_csv_zip(csvs)
        parser = LinkedinZipParser()
        data = parser.parse(path)

        json_converter = JsonResumeConverter()
        jr = json_converter.convert(data)

        rc_converter = RenderCvConverter()
        rcv = rc_converter.convert(jr)

        # Verify all sections in JSON Resume output
        assert jr.basics is not None
        assert jr.basics.name == "John Smith"
        assert len(jr.work) == 1
        assert len(jr.education) == 1
        assert len(jr.skills) == 6
        assert len(jr.languages) == 2

        # RenderCV output
        assert rcv.cv.name == "John Smith"
        assert len(rcv.cv.sections.get("experience", [])) == 1
        assert len(rcv.cv.sections.get("education", [])) == 1

        path.unlink()

    def test_output_has_no_empty_sections(self) -> None:
        """Regression test: no 'summary': [None] or empty arrays with nulls."""
        csvs = {
            "Profile.csv": _load_fixture("minimal_profile.csv"),
            "Positions.csv": _load_fixture("minimal_positions.csv"),
        }
        path = _make_multi_csv_zip(csvs)
        parser = LinkedinZipParser()
        data = parser.parse(path)

        json_converter = JsonResumeConverter()
        jr = json_converter.convert(data)

        # JSON Resume dump
        jr_dict = jr.model_dump(exclude_none=True)
        # No section should contain None
        for section_name in [
            "work",
            "education",
            "skills",
            "languages",
            "projects",
            "publications",
            "certificates",
            "awards",
            "references",
            "volunteer",
            "interests",
        ]:
            items = jr_dict.get(section_name, [])
            for item in items:
                for val in item.values():
                    assert val is not None, f"{section_name} has null value: {item}"

        rc_converter = RenderCvConverter()
        rcv = rc_converter.convert(jr)

        # RenderCV dump
        sections = rcv.cv.sections
        for section_name, entries in sections.items():
            for entry in entries:
                if isinstance(entry, dict):
                    for val in entry.values():
                        assert val is not None, (
                            f"{section_name} has null value: {entry}"
                        )

        path.unlink()

    def test_convert_uses_real_format_produces_output(self) -> None:
        """Test that multi-CSV format goes through the full conversion pipeline."""
        csvs = {
            "Profile.csv": _load_fixture("minimal_profile.csv"),
            "Positions.csv": _load_fixture("minimal_positions.csv"),
            "Education.csv": _load_fixture("minimal_education.csv"),
            "Skills.csv": _load_fixture("minimal_skills.csv"),
            "Languages.csv": _load_fixture("minimal_languages.csv"),
        }
        zip_path = _make_multi_csv_zip(csvs)

        # Run parser
        parser = LinkedinZipParser()
        data = parser.parse(zip_path)

        # Run conversion
        json_converter = JsonResumeConverter()
        jr = json_converter.convert(data)

        rc_converter = RenderCvConverter()
        rcv = rc_converter.convert(jr)

        # Serialize
        jr_json = jr.model_dump_json(indent=2)
        rcv_yaml = yaml.dump(
            rcv.model_dump(exclude_none=True),
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )

        # Basic sanity checks
        assert '"name": "John Smith"' in jr_json
        assert "Acme Corp" in jr_json
        assert "MIT" in jr_json
        assert "Python" in jr_json
        assert "English" in jr_json

        # RenderCV should contain real data, not empty
        assert "Acme Corp" in rcv_yaml or "Acme" in rcv_yaml

        zip_path.unlink()


class TestPartialOverwrite:
    """Integration tests for the partial file override functionality."""

    def test_overwrite_json_resume_basics(self) -> None:
        """Partial JSON Resume overrides basics fields."""
        csvs = {"Profile.csv": _load_fixture("minimal_profile.csv")}
        zip_path = _make_multi_csv_zip(csvs)
        parser = LinkedinZipParser()
        data = parser.parse(zip_path)

        json_converter = JsonResumeConverter()
        jr = json_converter.convert(data)

        base_dict = jr.model_dump(exclude_none=True)
        # basics came from LinkedIn: name="John Smith", occupation="Software Engineer", etc.
        assert base_dict["basics"]["name"] == "John Smith"

        # Now apply a partial override that adds a custom summary
        partial = {"basics": {"summary": "Custom summary from partial"}}
        merged = overwrite(base_dict, partial)

        # The partial replaced the entire basics object, so name is lost
        # (top-level replacement — not deep merge)
        assert merged["basics"]["summary"] == "Custom summary from partial"
        assert "name" not in merged["basics"]  # replaced wholesale

        zip_path.unlink()

    def test_overwrite_render_cv_sections(self) -> None:
        """Partial RenderCV overrides sections."""
        csvs = {"Profile.csv": _load_fixture("minimal_profile.csv")}
        zip_path = _make_multi_csv_zip(csvs)
        parser = LinkedinZipParser()
        data = parser.parse(zip_path)

        json_converter = JsonResumeConverter()
        jr = json_converter.convert(data)

        rc_converter = RenderCvConverter()
        rcv = rc_converter.convert(jr)

        base_dict = rcv.model_dump(exclude_none=True)
        # Sections exist from LinkedIn (e.g., summary section), but no custom sections
        assert "custom" not in base_dict.get("cv", {}).get("sections", {})

        # Add a custom section via overwrite
        partial = {
            "cv": {
                "name": "John Smith",
                "sections": {
                    "custom": [
                        {"label": "Custom Section", "details": "From partial file"}
                    ]
                },
            }
        }
        merged = overwrite(base_dict, partial)

        assert "custom" in merged["cv"]["sections"]
        assert merged["cv"]["sections"]["custom"][0]["label"] == "Custom Section"

        zip_path.unlink()

    def test_full_pipeline_with_partial_jsonresume(self) -> None:
        """The run() orchestrator accepts and applies partial JSON Resume."""
        import json
        import tempfile

        from linkedinto.orchestrator import run

        csvs = {
            "Profile.csv": _load_fixture("minimal_profile.csv"),
            "Skills.csv": _load_fixture("minimal_skills.csv"),
        }
        zip_path = _make_multi_csv_zip(csvs)

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a partial JSON Resume file
            partial_path = Path(tmpdir) / "partial.json"
            partial_data = {"basics": {"summary": "Overridden summary"}}
            partial_path.write_text(json.dumps(partial_data))

            # Run the full pipeline with the partial
            result = run(
                zip_path,
                output_dir=tmpdir,
                partial_jsonresume=partial_path,
            )

            # Verify the output file exists
            assert "jsonresume" in result
            json_path = result["jsonresume"]
            assert json_path.exists()

            # Read the output and verify the override was applied
            output = json.loads(json_path.read_text())
            # The override replaced basics entirely
            assert output["basics"]["summary"] == "Overridden summary"

        zip_path.unlink()

    def test_full_pipeline_with_partial_rendercv(self) -> None:
        """The run() orchestrator accepts and applies partial RenderCV YAML."""
        import tempfile

        import yaml

        from linkedinto.orchestrator import run

        csvs = {"Profile.csv": _load_fixture("minimal_profile.csv")}
        zip_path = _make_multi_csv_zip(csvs)

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a partial RenderCV file
            partial_path = Path(tmpdir) / "partial.yaml"
            partial_data = {
                "cv": {
                    "name": "John Smith",
                    "sections": {
                        "custom": [
                            {
                                "label": "Volunteer Work",
                                "details": "Overridden from partial",
                            }
                        ]
                    },
                }
            }
            partial_path.write_text(yaml.dump(partial_data))

            # Run the full pipeline with the partial
            result = run(
                zip_path,
                output_dir=tmpdir,
                partial_rendercv=partial_path,
            )

            # Verify output
            assert "rendercv" in result
            yaml_path = result["rendercv"]
            assert yaml_path.exists()

            output = yaml.safe_load(yaml_path.read_text())
            assert "custom" in output["cv"]["sections"]
            assert output["cv"]["sections"]["custom"][0]["label"] == "Volunteer Work"

        zip_path.unlink()

    def test_prefer_partial_over_linkedin_data(self) -> None:
        """Partial values take precedence over LinkedIn values at top level."""
        import json
        import tempfile

        from linkedinto.orchestrator import run

        csvs = {"Profile.csv": _load_fixture("minimal_profile.csv")}
        zip_path = _make_multi_csv_zip(csvs)

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create partial with different basics
            partial_path = Path(tmpdir) / "partial.json"
            partial_data = {
                "basics": {
                    "name": "Jane Doe",
                    "email": "jane@example.com",
                    "summary": "Overridden",
                }
            }
            partial_path.write_text(json.dumps(partial_data))

            result = run(
                zip_path,
                output_dir=tmpdir,
                partial_jsonresume=partial_path,
            )

            output = json.loads(result["jsonresume"].read_text())
            # Since the partial replaces the entire basics dict at the top level,
            # all basics fields come from the partial, not LinkedIn
            assert output["basics"]["name"] == "Jane Doe"
            assert output["basics"]["email"] == "jane@example.com"
            assert output["basics"]["summary"] == "Overridden"

        zip_path.unlink()

    def test_partial_file_not_found_raises_error(self) -> None:
        """Passing a non-existent partial file raises an error."""
        import tempfile

        from linkedinto.exceptions import LinkedIntoError
        from linkedinto.orchestrator import run

        csvs = {"Profile.csv": _load_fixture("minimal_profile.csv")}
        zip_path = _make_multi_csv_zip(csvs)

        with tempfile.TemporaryDirectory() as tmpdir:
            nonexistent = Path(tmpdir) / "nonexistent.json"
            with pytest.raises(LinkedIntoError, match="does not exist"):
                run(
                    zip_path,
                    output_dir=tmpdir,
                    partial_jsonresume=nonexistent,
                )

        zip_path.unlink()

    def test_convert_linkedin_data_no_overwrite(self) -> None:
        """Conversion produces data without any override."""
        csvs = {"Profile.csv": _load_fixture("minimal_profile.csv")}
        zip_path = _make_multi_csv_zip(csvs)
        parser = LinkedinZipParser()
        data = parser.parse(zip_path)

        json_converter = JsonResumeConverter()
        jr = json_converter.convert(data)
        assert jr.basics is not None
        assert jr.basics.name == "John Smith"
        # The minimal_profile fixture includes a summary
        assert jr.basics.summary == "Full-stack engineer with 10 years experience"

        zip_path.unlink()
