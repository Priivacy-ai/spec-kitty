"""
Styleguide domain model and value objects.

Defines Styleguide and AntiPattern Pydantic models and StyleguideScope enum.
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class StyleguideScope(StrEnum):
    """Scope category for a styleguide."""

    CODE = "code"
    DOCS = "docs"
    ARCHITECTURE = "architecture"
    TESTING = "testing"
    OPERATIONS = "operations"
    GLOSSARY = "glossary"


class AntiPattern(BaseModel):
    """An anti-pattern example within a styleguide."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    description: str
    bad_example: str
    good_example: str


class Pattern(BaseModel):
    """A positive code-pattern example within a styleguide."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    description: str
    bad_example: str | None = None
    good_example: str | None = None


class Styleguide(BaseModel):
    """
    A style and convention guide for a specific scope.

    Styleguides define principles, anti-patterns, and quality tests
    for consistent governance across a domain area.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    id: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    schema_version: str = Field(pattern=r"^1\.0$", alias="schema_version")
    title: str
    scope: StyleguideScope
    principles: list[str] = Field(min_length=1)
    patterns: list[Pattern] = Field(default_factory=list)
    anti_patterns: list[AntiPattern] = Field(default_factory=list)
    tooling: dict[str, str] = Field(default_factory=dict)
    quality_test: str | None = None
    references: list[str] = Field(default_factory=list)
