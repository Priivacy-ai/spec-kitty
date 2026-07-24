"""
Styleguide domain model and value objects.

Defines Styleguide and AntiPattern Pydantic models and StyleguideScope enum.
"""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

_RETIRED_RELATIONSHIP_FIELDS = ("enhances", "overrides")


def _reject_retired_relationship_fields(kind: str, data: Any) -> Any:
    """Raise an actionable error if a retired relationship key is authored.

    The ``enhances``/``overrides`` fields were retired in the FR-028 hard
    cutover. Relationships are now authored exclusively as DRG fragment edges
    merged into ``src/doctrine/*.graph.yaml``, never as inline artifact fields.
    """
    if not isinstance(data, dict):
        return data
    present = [field for field in _RETIRED_RELATIONSHIP_FIELDS if field in data]
    if present:
        keys = ", ".join(repr(field) for field in present)
        raise ValueError(
            f"Retired relationship field(s) {keys} on {kind} are no longer "
            f"accepted (FR-028 hard cutover). Author the relationship as a DRG "
            f"fragment edge in a `drg/` fragment "
            f"(e.g. {{source: <kind>:<id>, target: <kind>:<id>, "
            f"relation: enhances|overrides}}) merged into "
            f"src/doctrine/graph.yaml — not as an inline artifact field."
        )
    return data


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
    patterns: list[Pattern] = Field(default_factory=list, min_length=1)
    anti_patterns: list[AntiPattern] = Field(default_factory=list, min_length=1)
    tooling: dict[str, str] = Field(default_factory=dict)
    quality_test: str | None = None
    applies_to_languages: list[str] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)
    structural_lint_config: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Optional machine-parseable policy block a companion lint script "
            "LOADS as its single source of truth (e.g. the common-docs "
            "styleguide's docs_structural_lint.py config — FR-011). Plain "
            "nested scalars/lists/mappings only; a styleguide with no "
            "companion lint omits this field."
        ),
    )

    @model_validator(mode="before")
    @classmethod
    def _reject_retired_relationship_fields(cls, data: Any) -> Any:
        return _reject_retired_relationship_fields("styleguide", data)
