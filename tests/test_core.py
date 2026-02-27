"""Comprehensive tests for aumai-constitution core module."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml  # type: ignore[import-untyped]

from aumai_constitution.core import ComplianceChecker, ConstitutionBuilder
from aumai_constitution.models import (
    ComplianceResult,
    Constraint,
    Constitution,
    Principle,
)


# ---------------------------------------------------------------------------
# Model validation tests
# ---------------------------------------------------------------------------


class TestModels:
    def test_principle_fields(self, sample_principle: Principle) -> None:
        assert sample_principle.principle_id == "p-001"
        assert sample_principle.priority == 1
        assert sample_principle.category == "safety"

    def test_principle_priority_must_be_positive(self) -> None:
        with pytest.raises(Exception):
            Principle(
                principle_id="x",
                name="x",
                description="x",
                priority=0,  # ge=1 fails
                category="x",
            )

    def test_constraint_enforcement_literal(self) -> None:
        with pytest.raises(Exception):
            Constraint(
                constraint_id="x",
                rule="forbid: x",
                enforcement="mandatory",  # not a valid literal
                applies_to=[],
            )

    def test_constraint_enforcement_valid_values(self) -> None:
        for value in ("strict", "advisory"):
            c = Constraint(
                constraint_id="x",
                rule="forbid: x",
                enforcement=value,  # type: ignore[arg-type]
                applies_to=[],
            )
            assert c.enforcement == value

    def test_constitution_default_version(self, empty_constitution: Constitution) -> None:
        assert empty_constitution.version == "1.0.0"

    def test_constitution_empty_by_default(self, empty_constitution: Constitution) -> None:
        assert empty_constitution.principles == []
        assert empty_constitution.constraints == []


# ---------------------------------------------------------------------------
# ConstitutionBuilder tests
# ---------------------------------------------------------------------------


class TestConstitutionBuilder:
    def test_create_returns_constitution(self, builder: ConstitutionBuilder) -> None:
        c = builder.create(name="My AI Rules", author="alice")
        assert isinstance(c, Constitution)
        assert c.name == "My AI Rules"
        assert c.author == "alice"

    def test_create_generates_unique_ids(self, builder: ConstitutionBuilder) -> None:
        c1 = builder.create(name="A", author="a")
        c2 = builder.create(name="B", author="b")
        assert c1.constitution_id != c2.constitution_id

    def test_add_principle_appends_in_place(
        self,
        builder: ConstitutionBuilder,
        empty_constitution: Constitution,
        sample_principle: Principle,
    ) -> None:
        builder.add_principle(empty_constitution, sample_principle)
        assert len(empty_constitution.principles) == 1
        assert empty_constitution.principles[0].principle_id == "p-001"

    def test_add_multiple_principles(
        self,
        builder: ConstitutionBuilder,
        empty_constitution: Constitution,
    ) -> None:
        for i in range(3):
            p = Principle(
                principle_id=f"p-{i}",
                name=f"Principle {i}",
                description="desc",
                priority=i + 1,
                category="test",
            )
            builder.add_principle(empty_constitution, p)
        assert len(empty_constitution.principles) == 3

    def test_add_constraint_appends_in_place(
        self,
        builder: ConstitutionBuilder,
        empty_constitution: Constitution,
        strict_constraint: Constraint,
    ) -> None:
        builder.add_constraint(empty_constitution, strict_constraint)
        assert len(empty_constitution.constraints) == 1

    def test_save_creates_yaml_file(
        self,
        builder: ConstitutionBuilder,
        full_constitution: Constitution,
        tmp_path: Path,
    ) -> None:
        path = tmp_path / "output.yaml"
        builder.save(full_constitution, str(path))
        assert path.exists()

    def test_save_yaml_is_valid_yaml(
        self,
        builder: ConstitutionBuilder,
        full_constitution: Constitution,
        tmp_path: Path,
    ) -> None:
        path = tmp_path / "output.yaml"
        builder.save(full_constitution, str(path))
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert isinstance(data, dict)
        assert "constitution_id" in data

    def test_save_creates_parent_dirs(
        self,
        builder: ConstitutionBuilder,
        full_constitution: Constitution,
        tmp_path: Path,
    ) -> None:
        nested = tmp_path / "a" / "b" / "constitution.yaml"
        builder.save(full_constitution, str(nested))
        assert nested.exists()

    def test_load_round_trips_constitution(
        self,
        builder: ConstitutionBuilder,
        full_constitution: Constitution,
        saved_constitution_path: Path,
    ) -> None:
        loaded = builder.load(str(saved_constitution_path))
        assert loaded.constitution_id == full_constitution.constitution_id
        assert loaded.name == full_constitution.name
        assert loaded.author == full_constitution.author

    def test_load_preserves_principles(
        self,
        builder: ConstitutionBuilder,
        saved_constitution_path: Path,
    ) -> None:
        loaded = builder.load(str(saved_constitution_path))
        assert len(loaded.principles) == 1
        assert loaded.principles[0].principle_id == "p-001"

    def test_load_preserves_constraints(
        self,
        builder: ConstitutionBuilder,
        saved_constitution_path: Path,
    ) -> None:
        loaded = builder.load(str(saved_constitution_path))
        assert len(loaded.constraints) == 2


# ---------------------------------------------------------------------------
# ComplianceChecker tests
# ---------------------------------------------------------------------------


class TestComplianceCheckerCheckConstraint:
    def test_forbid_prefix_passes_when_pattern_absent(
        self,
        checker: ComplianceChecker,
        strict_constraint: Constraint,
    ) -> None:
        # strict_constraint rule = "forbid: violence"
        assert checker.check_constraint("This is a peaceful message.", strict_constraint) is True

    def test_forbid_prefix_fails_when_pattern_present(
        self,
        checker: ComplianceChecker,
        strict_constraint: Constraint,
    ) -> None:
        assert checker.check_constraint("This contains violence.", strict_constraint) is False

    def test_forbid_case_insensitive(
        self,
        checker: ComplianceChecker,
        strict_constraint: Constraint,
    ) -> None:
        assert checker.check_constraint("VIOLENCE is prohibited", strict_constraint) is False

    def test_deny_prefix_behaves_like_forbid(
        self,
        checker: ComplianceChecker,
    ) -> None:
        constraint = Constraint(
            constraint_id="x",
            rule="deny: spam",
            enforcement="advisory",
            applies_to=[],
        )
        assert checker.check_constraint("no spam here", constraint) is False
        assert checker.check_constraint("clean message", constraint) is True

    def test_require_prefix_passes_when_pattern_present(
        self,
        checker: ComplianceChecker,
        advisory_constraint: Constraint,
    ) -> None:
        # advisory_constraint rule = "require: disclaimer"
        assert checker.check_constraint("Please note this disclaimer.", advisory_constraint) is True

    def test_require_prefix_fails_when_pattern_absent(
        self,
        checker: ComplianceChecker,
        advisory_constraint: Constraint,
    ) -> None:
        assert checker.check_constraint("No legal notes here.", advisory_constraint) is False

    def test_must_prefix_behaves_like_require(
        self,
        checker: ComplianceChecker,
    ) -> None:
        constraint = Constraint(
            constraint_id="x",
            rule="must: signature",
            enforcement="strict",
            applies_to=[],
        )
        assert checker.check_constraint("message with signature", constraint) is True
        assert checker.check_constraint("message without sig", constraint) is False

    def test_plain_rule_is_forbidden_keyword(
        self,
        checker: ComplianceChecker,
        plain_forbidden_constraint: Constraint,
    ) -> None:
        # plain_forbidden_constraint rule = "badword"
        assert checker.check_constraint("this contains badword here", plain_forbidden_constraint) is False
        assert checker.check_constraint("this is clean", plain_forbidden_constraint) is True

    def test_plain_rule_case_sensitive_check(
        self,
        checker: ComplianceChecker,
        plain_forbidden_constraint: Constraint,
    ) -> None:
        # Plain rules use output.lower() matching, so BADWORD should match
        assert checker.check_constraint("BADWORD appears", plain_forbidden_constraint) is False


class TestComplianceCheckerCheck:
    def test_no_constraints_is_compliant(
        self,
        checker: ComplianceChecker,
        empty_constitution: Constitution,
    ) -> None:
        result = checker.check("any output text", empty_constitution)
        assert result.compliant is True
        assert result.violations == []

    def test_all_constraints_satisfied(
        self,
        checker: ComplianceChecker,
        full_constitution: Constitution,
    ) -> None:
        # full_constitution has: forbid:violence, require:disclaimer
        result = checker.check("This is a safe message with disclaimer.", full_constitution)
        assert result.compliant is True

    def test_strict_violation_makes_non_compliant(
        self,
        checker: ComplianceChecker,
        full_constitution: Constitution,
    ) -> None:
        # Trigger strict "forbid: violence" constraint
        result = checker.check("This message contains violence.", full_constitution)
        assert result.compliant is False

    def test_advisory_violation_is_compliant(
        self,
        checker: ComplianceChecker,
        full_constitution: Constitution,
    ) -> None:
        # Missing "disclaimer" triggers advisory constraint only
        # strict "violence" is not triggered since text has no violence
        result = checker.check("This is safe but lacks required notice.", full_constitution)
        # strict violation did not occur, advisory only = still compliant
        assert result.compliant is True

    def test_violation_recorded_in_result(
        self,
        checker: ComplianceChecker,
        full_constitution: Constitution,
    ) -> None:
        result = checker.check("violence is present here", full_constitution)
        assert len(result.violations) >= 1
        violation = result.violations[0]
        assert "constraint_id" in violation
        assert "rule" in violation
        assert "enforcement" in violation

    def test_result_contains_constitution_id(
        self,
        checker: ComplianceChecker,
        full_constitution: Constitution,
    ) -> None:
        result = checker.check("hello", full_constitution)
        assert result.constitution_id == full_constitution.constitution_id

    def test_result_contains_output_text(
        self,
        checker: ComplianceChecker,
        empty_constitution: Constitution,
    ) -> None:
        text = "sample output text"
        result = checker.check(text, empty_constitution)
        assert result.output == text

    def test_multiple_strict_violations_all_recorded(
        self,
        checker: ComplianceChecker,
        builder: ConstitutionBuilder,
    ) -> None:
        constitution = builder.create(name="Multi-strict", author="test")
        for i in range(3):
            builder.add_constraint(
                constitution,
                Constraint(
                    constraint_id=f"c-{i}",
                    rule=f"forbid: badterm{i}",
                    enforcement="strict",
                    applies_to=[],
                ),
            )
        result = checker.check("contains badterm0 and badterm1 and badterm2", constitution)
        assert len(result.violations) == 3
        assert result.compliant is False
