"""Pydantic models for aumai-constitution."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

__all__ = [
    "Principle",
    "Constraint",
    "Constitution",
    "ComplianceResult",
]


class Principle(BaseModel):
    """A single guiding principle in a constitution."""

    principle_id: str
    name: str
    description: str
    priority: int = Field(ge=1, description="Lower numbers are higher priority.")
    category: str


class Constraint(BaseModel):
    """A constraint rule applied to AI outputs."""

    constraint_id: str
    rule: str
    enforcement: Literal["strict", "advisory"]
    applies_to: list[str] = Field(default_factory=list, description="Target domains or models.")


class Constitution(BaseModel):
    """A complete AI system constitution."""

    constitution_id: str
    name: str
    version: str = "1.0.0"
    principles: list[Principle] = Field(default_factory=list)
    constraints: list[Constraint] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    author: str


class ComplianceResult(BaseModel):
    """Result of checking an output against a constitution."""

    constitution_id: str
    output: str
    violations: list[dict[str, str]] = Field(default_factory=list)
    compliant: bool
