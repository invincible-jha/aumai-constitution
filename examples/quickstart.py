"""aumai-constitution quickstart — define and enforce AI system constitutions.

Run this file directly:
    python examples/quickstart.py

No LLM API keys required. Constitution creation, rule evaluation, and
compliance checking are all pure-Python and run fully offline.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from aumai_constitution.core import ComplianceChecker, ConstitutionBuilder
from aumai_constitution.models import (
    ComplianceResult,
    Constraint,
    Constitution,
    Principle,
)


# ---------------------------------------------------------------------------
# Demo 1: Build a constitution with principles and constraints
# ---------------------------------------------------------------------------


def demo_build_constitution() -> Constitution:
    """Construct an AI system constitution from scratch using ConstitutionBuilder.

    A constitution consists of:
    - Principles: high-level values that guide system design.
    - Constraints: specific rules that outputs must satisfy, with either
      'strict' enforcement (a violation blocks the output) or 'advisory'
      enforcement (a violation is flagged but not blocked).

    Constraint rule syntax:
      forbid:<pattern>  — the pattern must NOT appear in the output.
      require:<pattern> — the pattern MUST appear in the output.
      <plain text>      — treated as a forbidden keyword/phrase.
    """
    print("=== Demo 1: Build a Constitution ===")

    builder = ConstitutionBuilder()
    constitution = builder.create(
        name="Enterprise AI Safety Constitution v1",
        author="MuVeraAI",
    )

    # Principles encode values. They are informational and not directly
    # enforced by ComplianceChecker; enforcement happens via constraints.
    principles = [
        Principle(
            principle_id="P-001",
            name="Honesty",
            description="The system must not fabricate facts or citations.",
            priority=1,
            category="safety",
        ),
        Principle(
            principle_id="P-002",
            name="Privacy",
            description="The system must not expose personally identifiable information.",
            priority=1,
            category="privacy",
        ),
        Principle(
            principle_id="P-003",
            name="Transparency",
            description="The system must acknowledge when it is uncertain.",
            priority=2,
            category="trust",
        ),
    ]
    for principle in principles:
        builder.add_principle(constitution, principle)

    # Constraints are machine-evaluated rules. 'strict' constraints cause a
    # compliance failure if violated; 'advisory' constraints emit a warning.
    constraints = [
        Constraint(
            constraint_id="C-001",
            rule="forbid:I am not an AI",
            enforcement="strict",
            applies_to=["all"],
        ),
        Constraint(
            constraint_id="C-002",
            rule="forbid:guaranteed",
            enforcement="advisory",
            applies_to=["financial", "legal"],
        ),
        Constraint(
            constraint_id="C-003",
            rule="forbid:social security number",
            enforcement="strict",
            applies_to=["all"],
        ),
        Constraint(
            constraint_id="C-004",
            rule="require:disclaimer",
            enforcement="advisory",
            applies_to=["legal", "medical"],
        ),
    ]
    for constraint in constraints:
        builder.add_constraint(constitution, constraint)

    print(f"  Constitution: {constitution.name}")
    print(f"  Author:       {constitution.author}")
    print(f"  Version:      {constitution.version}")
    print(f"  Principles:   {len(constitution.principles)}")
    print(f"  Constraints:  {len(constitution.constraints)}")
    print()

    return constitution


# ---------------------------------------------------------------------------
# Demo 2: Check a compliant AI output
# ---------------------------------------------------------------------------


def demo_check_compliant_output(constitution: Constitution) -> None:
    """Verify that a well-formed AI output passes all strict constraints.

    ComplianceChecker.check() evaluates every constraint rule against the
    output text. A result is fully compliant only when no strict constraints
    are violated (advisory violations are allowed).
    """
    print("=== Demo 2: Compliance Check — Passing Output ===")

    checker = ComplianceChecker()
    output = (
        "Based on the information available, the current market trend suggests "
        "moderate growth in the sector. Please note this is not financial advice. "
        "Disclaimer: always consult a qualified advisor before making investment decisions."
    )

    result: ComplianceResult = checker.check(output, constitution)

    print(f"  Output (truncated): '{output[:70]}...'")
    print(f"  Compliant:  {result.compliant}")
    print(f"  Violations: {len(result.violations)}")
    if result.violations:
        for violation in result.violations:
            print(f"    [{violation['enforcement']}] {violation['rule']}")
    else:
        print("  No constraint violations detected.")
    print()


# ---------------------------------------------------------------------------
# Demo 3: Check an output that triggers strict violations
# ---------------------------------------------------------------------------


def demo_check_violating_output(constitution: Constitution) -> ComplianceResult:
    """Demonstrate compliance failure when strict constraints are triggered.

    The output below contains two problematic phrases:
    - "I am not an AI" — violates constraint C-001 (strict)
    - "social security number" — violates constraint C-003 (strict)

    Both are strict constraints so compliant=False is returned.
    """
    print("=== Demo 3: Compliance Check — Failing Output ===")

    checker = ComplianceChecker()
    output = (
        "I am not an AI; I am a human assistant. "
        "Your social security number will be stored securely."
    )

    result = checker.check(output, constitution)

    print(f"  Output: '{output}'")
    print(f"  Compliant:  {result.compliant}")
    print(f"  Violations: {len(result.violations)}")
    for violation in result.violations:
        print(
            f"    [{violation['enforcement']}] "
            f"Constraint {violation['constraint_id']}: {violation['rule']}"
        )
    print()

    return result


# ---------------------------------------------------------------------------
# Demo 4: Save and reload a constitution from YAML
# ---------------------------------------------------------------------------


def demo_save_and_load(constitution: Constitution) -> Constitution:
    """Persist a constitution to YAML and deserialize it back.

    ConstitutionBuilder.save() writes a YAML file using model_dump().
    ConstitutionBuilder.load() reads it back with full Pydantic validation.
    This round-trip lets you version-control constitutions alongside your code.
    """
    print("=== Demo 4: Save and Load from YAML ===")

    builder = ConstitutionBuilder()

    with tempfile.TemporaryDirectory() as tmpdir:
        yaml_path = Path(tmpdir) / "constitution_v1.yaml"
        builder.save(constitution, str(yaml_path))

        file_size = yaml_path.stat().st_size
        print(f"  Saved to:  {yaml_path.name}  ({file_size} bytes)")

        # Show the first few lines of the YAML for illustration.
        yaml_content = yaml_path.read_text(encoding="utf-8")
        preview_lines = yaml_content.splitlines()[:8]
        print("  YAML preview:")
        for line in preview_lines:
            print(f"    {line}")

        reloaded = builder.load(str(yaml_path))

    print(f"\n  Reloaded: '{reloaded.name}'")
    print(f"  Principles: {len(reloaded.principles)}  Constraints: {len(reloaded.constraints)}")
    assert reloaded.constitution_id == constitution.constitution_id
    print("  Round-trip verification: passed")
    print()

    return reloaded


# ---------------------------------------------------------------------------
# Demo 5: Evaluate individual constraints against multiple outputs
# ---------------------------------------------------------------------------


def demo_check_individual_constraints(constitution: Constitution) -> None:
    """Evaluate each strict constraint against a set of sample outputs.

    check_constraint() returns True when the output satisfies the rule and
    False when it is violated. This granular API is useful for building
    real-time output filters or pre-flight checks before returning a response
    to the end user.
    """
    print("=== Demo 5: Per-Constraint Evaluation ===")

    checker = ComplianceChecker()
    strict_constraints = [c for c in constitution.constraints if c.enforcement == "strict"]

    test_outputs = [
        "As an AI assistant, I can help you with that request.",
        "I am not an AI. I am a real person.",
        "Your social security number should never be shared online.",
        "The answer is 42. This is a well-known fact.",
    ]

    for constraint in strict_constraints:
        print(f"\n  Constraint [{constraint.constraint_id}]: {constraint.rule}")
        for output in test_outputs:
            passes = checker.check_constraint(output, constraint)
            status = "PASS" if passes else "FAIL"
            preview = output[:55] + ("..." if len(output) > 55 else "")
            print(f"    [{status}] '{preview}'")
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run all quickstart demos in sequence."""
    print("\naumai-constitution quickstart\n")

    constitution = demo_build_constitution()
    demo_check_compliant_output(constitution)
    demo_check_violating_output(constitution)
    reloaded = demo_save_and_load(constitution)
    demo_check_individual_constraints(reloaded)

    print("All demos complete.")


if __name__ == "__main__":
    main()
