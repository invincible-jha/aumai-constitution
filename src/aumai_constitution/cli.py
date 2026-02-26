"""CLI entry point for aumai-constitution."""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

import click

from aumai_constitution.core import ComplianceChecker, ConstitutionBuilder
from aumai_constitution.models import Constraint, Principle

_builder = ConstitutionBuilder()
_checker = ComplianceChecker()


@click.group()
@click.version_option()
def main() -> None:
    """AumAI Constitution — AI system constitution framework CLI."""


@main.command("create")
@click.option("--name", required=True, help="Name of the constitution.")
@click.option("--author", default="unknown", show_default=True, help="Author name.")
@click.option(
    "--output",
    required=True,
    type=click.Path(dir_okay=False, path_type=Path),
    help="Output YAML file path.",
)
def create(name: str, author: str, output: Path) -> None:
    """Create a new empty constitution and save it to YAML."""
    constitution = _builder.create(name=name, author=author)
    _builder.save(constitution, str(output))
    click.echo(f"Created constitution '{name}' (ID: {constitution.constitution_id}) -> {output}")


@main.command("check")
@click.option(
    "--input",
    "input_file",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Text file to check.",
)
@click.option(
    "--constitution",
    "constitution_file",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Constitution YAML file.",
)
def check(input_file: Path, constitution_file: Path) -> None:
    """Check a text file against a constitution for compliance."""
    output_text = input_file.read_text(encoding="utf-8")
    constitution = _builder.load(str(constitution_file))
    result = _checker.check(output_text, constitution)

    status = "COMPLIANT" if result.compliant else "NON-COMPLIANT"
    click.echo(f"Status: {status}")

    if result.violations:
        click.echo(f"Violations ({len(result.violations)}):")
        for violation in result.violations:
            click.echo(f"  [{violation['enforcement'].upper()}] {violation['rule']}")
    else:
        click.echo("No violations found.")


@main.command("validate")
@click.option(
    "--constitution",
    "constitution_file",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Constitution YAML file to validate.",
)
def validate(constitution_file: Path) -> None:
    """Validate the structure and integrity of a constitution YAML file."""
    try:
        constitution = _builder.load(str(constitution_file))
    except Exception as exc:
        click.echo(f"Validation failed: {exc}", err=True)
        sys.exit(1)

    issues: list[str] = []
    if not constitution.principles:
        issues.append("Constitution has no principles defined.")
    if not constitution.constraints:
        issues.append("Constitution has no constraints defined.")

    principle_ids = {p.principle_id for p in constitution.principles}
    if len(principle_ids) != len(constitution.principles):
        issues.append("Duplicate principle_ids detected.")

    constraint_ids = {c.constraint_id for c in constitution.constraints}
    if len(constraint_ids) != len(constitution.constraints):
        issues.append("Duplicate constraint_ids detected.")

    if issues:
        click.echo("Validation warnings:")
        for issue in issues:
            click.echo(f"  - {issue}")
    else:
        click.echo(f"Constitution '{constitution.name}' v{constitution.version} is valid.")
        click.echo(f"  Principles: {len(constitution.principles)}")
        click.echo(f"  Constraints: {len(constitution.constraints)}")


if __name__ == "__main__":
    main()
