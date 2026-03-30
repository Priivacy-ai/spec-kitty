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

    model_config = ConfigDict(frozen=True)

    name: str
    description: str
    bad_example: str
    good_example: str


class Styleguide(BaseModel):
    """
    A style and convention guide for a specific scope.

    Styleguides define principles, anti-patterns, and quality tests
    for consistent governance across a domain area.
    """

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    id: str
    schema_version: str = Field(alias="schema_version")
    title: str
    scope: StyleguideScope
    principles: list[str] = Field(min_length=1)
    anti_patterns: list[AntiPattern] = Field(default_factory=list)
    quality_test: str | None = None
    references: list[str] = Field(default_factory=list)
