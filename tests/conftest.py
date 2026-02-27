"""Shared test fixtures for aumai-constitution."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml  # type: ignore[import-untyped]

from aumai_constitution.core import ComplianceChecker, ConstitutionBuilder
from aumai_constitution.models import Constraint, Constitution, Principle


@pytest.fixture()
def builder() -> ConstitutionBuilder:
    """A fresh ConstitutionBuilder instance."""
    return ConstitutionBuilder()


@pytest.fixture()
def checker() -> ComplianceChecker:
    """A fresh ComplianceChecker instance."""
    return ComplianceChecker()


@pytest.fixture()
def sample_principle() -> Principle:
    """A valid Principle for testing."""
    return Principle(
        principle_id="p-001",
        name="Harmlessness",
        description="Do not cause harm to users or society.",
        priority=1,
        category="safety",
    )


@pytest.fixture()
def strict_constraint() -> Constraint:
    """A strict constraint using the forbid: prefix."""
    return Constraint(
        constraint_id="c-001",
        rule="forbid: violence",
        enforcement="strict",
        applies_to=["all"],
    )


@pytest.fixture()
def advisory_constraint() -> Constraint:
    """An advisory constraint using require: prefix."""
    return Constraint(
        constraint_id="c-002",
        rule="require: disclaimer",
        enforcement="advisory",
        applies_to=["medical"],
    )


@pytest.fixture()
def plain_forbidden_constraint() -> Constraint:
    """A plain-string forbidden-keyword constraint."""
    return Constraint(
        constraint_id="c-003",
        rule="badword",
        enforcement="strict",
        applies_to=[],
    )


@pytest.fixture()
def empty_constitution(builder: ConstitutionBuilder) -> Constitution:
    """A freshly created constitution with no principles or constraints."""
    return builder.create(name="Test Constitution", author="test-author")


@pytest.fixture()
def full_constitution(
    builder: ConstitutionBuilder,
    sample_principle: Principle,
    strict_constraint: Constraint,
    advisory_constraint: Constraint,
) -> Constitution:
    """Constitution pre-populated with one principle and two constraints."""
    constitution = builder.create(name="Full Constitution", author="tester")
    builder.add_principle(constitution, sample_principle)
    builder.add_constraint(constitution, strict_constraint)
    builder.add_constraint(constitution, advisory_constraint)
    return constitution


@pytest.fixture()
def saved_constitution_path(
    full_constitution: Constitution,
    builder: ConstitutionBuilder,
    tmp_path: Path,
) -> Path:
    """A full constitution saved to a temp YAML file; returns its path."""
    output = tmp_path / "constitution.yaml"
    builder.save(full_constitution, str(output))
    return output
