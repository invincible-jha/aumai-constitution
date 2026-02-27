"""Comprehensive CLI tests for aumai-constitution."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml  # type: ignore[import-untyped]
from click.testing import CliRunner

from aumai_constitution.cli import main
from aumai_constitution.core import ConstitutionBuilder
from aumai_constitution.models import Constraint, Constitution, Principle


def _fresh_runner() -> CliRunner:
    """Return a CliRunner without mix_stderr (Click 8.2 compatible)."""
    return CliRunner()


class TestCLIVersion:
    def test_version_flag(self) -> None:
        result = _fresh_runner().invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_help_flag(self) -> None:
        result = _fresh_runner().invoke(main, ["--help"])
        assert result.exit_code == 0


class TestCreateCommand:
    def test_create_writes_yaml(self, tmp_path: Path) -> None:
        output = tmp_path / "c.yaml"
        result = _fresh_runner().invoke(
            main, ["create", "--name", "MyConstitution", "--output", str(output)]
        )
        assert result.exit_code == 0
        assert output.exists()

    def test_create_output_contains_id(self, tmp_path: Path) -> None:
        output = tmp_path / "c.yaml"
        result = _fresh_runner().invoke(
            main, ["create", "--name", "TestConstitution", "--output", str(output)]
        )
        assert result.exit_code == 0
        assert "ID:" in result.output

    def test_create_output_contains_name(self, tmp_path: Path) -> None:
        output = tmp_path / "c.yaml"
        result = _fresh_runner().invoke(
            main, ["create", "--name", "Unique-Name-XYZ", "--output", str(output)]
        )
        assert "Unique-Name-XYZ" in result.output

    def test_create_default_author(self, tmp_path: Path) -> None:
        output = tmp_path / "c.yaml"
        result = _fresh_runner().invoke(
            main, ["create", "--name", "TestC", "--output", str(output)]
        )
        assert result.exit_code == 0
        data = yaml.safe_load(output.read_text(encoding="utf-8"))
        assert data["author"] == "unknown"

    def test_create_custom_author(self, tmp_path: Path) -> None:
        output = tmp_path / "c.yaml"
        result = _fresh_runner().invoke(
            main, ["create", "--name", "TestC", "--author", "alice", "--output", str(output)]
        )
        assert result.exit_code == 0
        data = yaml.safe_load(output.read_text(encoding="utf-8"))
        assert data["author"] == "alice"

    def test_create_missing_name_errors(self, tmp_path: Path) -> None:
        output = tmp_path / "c.yaml"
        result = _fresh_runner().invoke(main, ["create", "--output", str(output)])
        assert result.exit_code != 0

    def test_create_missing_output_errors(self) -> None:
        result = _fresh_runner().invoke(main, ["create", "--name", "TestC"])
        assert result.exit_code != 0

    def test_create_help(self) -> None:
        result = _fresh_runner().invoke(main, ["create", "--help"])
        assert result.exit_code == 0
        assert "name" in result.output.lower()


class TestCheckCommand:
    def test_check_compliant_output(
        self, saved_constitution_path: Path, tmp_path: Path
    ) -> None:
        input_file = tmp_path / "text.txt"
        input_file.write_text("This is a safe message with disclaimer.", encoding="utf-8")
        result = _fresh_runner().invoke(
            main,
            [
                "check",
                "--input", str(input_file),
                "--constitution", str(saved_constitution_path),
            ],
        )
        assert result.exit_code == 0
        assert "COMPLIANT" in result.output

    def test_check_non_compliant_output(
        self, saved_constitution_path: Path, tmp_path: Path
    ) -> None:
        input_file = tmp_path / "text.txt"
        input_file.write_text("This message contains violence.", encoding="utf-8")
        result = _fresh_runner().invoke(
            main,
            [
                "check",
                "--input", str(input_file),
                "--constitution", str(saved_constitution_path),
            ],
        )
        assert result.exit_code == 0
        assert "NON-COMPLIANT" in result.output

    def test_check_violations_listed(
        self, saved_constitution_path: Path, tmp_path: Path
    ) -> None:
        input_file = tmp_path / "text.txt"
        input_file.write_text("violence is here", encoding="utf-8")
        result = _fresh_runner().invoke(
            main,
            [
                "check",
                "--input", str(input_file),
                "--constitution", str(saved_constitution_path),
            ],
        )
        assert "Violation" in result.output or "violation" in result.output

    def test_check_no_violations_message(
        self, saved_constitution_path: Path, tmp_path: Path
    ) -> None:
        input_file = tmp_path / "text.txt"
        input_file.write_text("This is a safe message with disclaimer.", encoding="utf-8")
        result = _fresh_runner().invoke(
            main,
            [
                "check",
                "--input", str(input_file),
                "--constitution", str(saved_constitution_path),
            ],
        )
        assert "No violations" in result.output

    def test_check_missing_input_errors(self, saved_constitution_path: Path) -> None:
        result = _fresh_runner().invoke(
            main,
            ["check", "--constitution", str(saved_constitution_path)],
        )
        assert result.exit_code != 0

    def test_check_missing_constitution_errors(self, tmp_path: Path) -> None:
        input_file = tmp_path / "text.txt"
        input_file.write_text("hello", encoding="utf-8")
        result = _fresh_runner().invoke(
            main,
            ["check", "--input", str(input_file)],
        )
        assert result.exit_code != 0

    def test_check_help(self) -> None:
        result = _fresh_runner().invoke(main, ["check", "--help"])
        assert result.exit_code == 0


class TestValidateCommand:
    def test_validate_valid_constitution(self, saved_constitution_path: Path) -> None:
        result = _fresh_runner().invoke(
            main, ["validate", "--constitution", str(saved_constitution_path)]
        )
        assert result.exit_code == 0
        assert "valid" in result.output.lower()

    def test_validate_reports_principle_and_constraint_counts(
        self, saved_constitution_path: Path
    ) -> None:
        result = _fresh_runner().invoke(
            main, ["validate", "--constitution", str(saved_constitution_path)]
        )
        assert "Principles:" in result.output
        assert "Constraints:" in result.output

    def test_validate_warns_on_no_principles(
        self, tmp_path: Path, builder: ConstitutionBuilder
    ) -> None:
        constitution = builder.create(name="No Principles", author="test")
        constitution.constraints.append(
            Constraint(constraint_id="c1", rule="forbid: x", enforcement="strict", applies_to=[])
        )
        path = tmp_path / "no_principles.yaml"
        builder.save(constitution, str(path))
        result = _fresh_runner().invoke(main, ["validate", "--constitution", str(path)])
        assert result.exit_code == 0
        assert "no principles" in result.output.lower()

    def test_validate_warns_on_no_constraints(
        self, tmp_path: Path, builder: ConstitutionBuilder
    ) -> None:
        constitution = builder.create(name="No Constraints", author="test")
        constitution.principles.append(
            Principle(principle_id="p1", name="P", description="d", priority=1, category="c")
        )
        path = tmp_path / "no_constraints.yaml"
        builder.save(constitution, str(path))
        result = _fresh_runner().invoke(main, ["validate", "--constitution", str(path)])
        assert result.exit_code == 0
        assert "no constraints" in result.output.lower()

    def test_validate_invalid_yaml_exits_nonzero(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.yaml"
        bad.write_text("not: valid: yaml: [[[", encoding="utf-8")
        result = _fresh_runner().invoke(main, ["validate", "--constitution", str(bad)])
        assert result.exit_code != 0

    def test_validate_missing_file_errors(self, tmp_path: Path) -> None:
        result = _fresh_runner().invoke(
            main, ["validate", "--constitution", str(tmp_path / "missing.yaml")]
        )
        assert result.exit_code != 0

    def test_validate_help(self) -> None:
        result = _fresh_runner().invoke(main, ["validate", "--help"])
        assert result.exit_code == 0
