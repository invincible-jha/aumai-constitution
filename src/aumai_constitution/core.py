"""Core logic for aumai-constitution."""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from aumai_constitution.models import (
    ComplianceResult,
    Constraint,
    Constitution,
    Principle,
)

__all__ = ["ConstitutionBuilder", "ComplianceChecker"]


class ConstitutionBuilder:
    """Build, persist, and load AI system constitutions."""

    def create(self, name: str, author: str) -> Constitution:
        """Create a new empty constitution.

        Args:
            name: Human-readable name for the constitution.
            author: Author or organization creating the constitution.

        Returns:
            A new Constitution with no principles or constraints.
        """
        return Constitution(
            constitution_id=str(uuid.uuid4()),
            name=name,
            author=author,
            created_at=datetime.utcnow(),
        )

    def add_principle(self, constitution: Constitution, principle: Principle) -> None:
        """Add a principle to an existing constitution in-place.

        Args:
            constitution: The constitution to modify.
            principle: The principle to add.
        """
        constitution.principles.append(principle)

    def add_constraint(self, constitution: Constitution, constraint: Constraint) -> None:
        """Add a constraint to an existing constitution in-place.

        Args:
            constitution: The constitution to modify.
            constraint: The constraint to add.
        """
        constitution.constraints.append(constraint)

    def save(self, constitution: Constitution, path: str) -> None:
        """Persist a constitution to a YAML file.

        Args:
            constitution: The constitution to save.
            path: File system path (must end in .yaml or .yml).
        """
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        data = constitution.model_dump(mode="json")
        output_path.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")

    def load(self, path: str) -> Constitution:
        """Load a constitution from a YAML file.

        Args:
            path: File system path to the YAML file.

        Returns:
            The deserialized Constitution.
        """
        raw = Path(path).read_text(encoding="utf-8")
        data: dict[str, object] = yaml.safe_load(raw)
        return Constitution.model_validate(data)


class ComplianceChecker:
    """Check AI outputs against constitution rules using pattern matching."""

    def check(self, output: str, constitution: Constitution) -> ComplianceResult:
        """Check a text output against all constraints in the constitution.

        Args:
            output: The AI-generated text to validate.
            constitution: The constitution to check against.

        Returns:
            A ComplianceResult indicating pass/fail and any violations.
        """
        violations: list[dict[str, str]] = []

        for constraint in constitution.constraints:
            if not self.check_constraint(output, constraint):
                violations.append(
                    {
                        "constraint_id": constraint.constraint_id,
                        "rule": constraint.rule,
                        "enforcement": constraint.enforcement,
                    }
                )

        compliant = all(
            v["enforcement"] != "strict" for v in violations
        )

        return ComplianceResult(
            constitution_id=constitution.constitution_id,
            output=output,
            violations=violations,
            compliant=compliant,
        )

    def check_constraint(self, output: str, constraint: Constraint) -> bool:
        """Check if output satisfies a single constraint rule.

        The rule is interpreted as a forbidden regex pattern if it starts with
        'forbid:' or 'deny:', and as a required pattern if it starts with
        'require:' or 'must:'. Plain strings are treated as forbidden keywords.

        Args:
            output: The text to check.
            constraint: The constraint to evaluate.

        Returns:
            True if the output satisfies the constraint, False if violated.
        """
        rule = constraint.rule.strip()
        output_lower = output.lower()

        if rule.lower().startswith("forbid:") or rule.lower().startswith("deny:"):
            pattern = re.split(":", rule, maxsplit=1)[1].strip()
            return not bool(re.search(pattern, output, re.IGNORECASE))

        if rule.lower().startswith("require:") or rule.lower().startswith("must:"):
            pattern = re.split(":", rule, maxsplit=1)[1].strip()
            return bool(re.search(pattern, output, re.IGNORECASE))

        # Default: treat the rule as a forbidden keyword or phrase.
        return rule.lower() not in output_lower
