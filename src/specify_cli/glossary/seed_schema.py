"""Pydantic models for glossary seed file schema validation.

Follows the doctrine pattern (``src/doctrine/directives/models.py``):
``ConfigDict(frozen=True, extra="forbid")`` with ``@field_validator``
for domain invariants.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator

__all__ = ["GlossarySeedFile", "GlossarySeedTerm"]


class GlossarySeedTerm(BaseModel):
    """Pydantic model for a single glossary seed file term entry."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    surface: str
    definition: str
    confidence: float = 1.0
    status: Literal["active", "draft", "deprecated"] = "draft"

    # Optional provenance/relationship metadata written by authoring pipelines.
    # Accepted at the schema layer so a single annotated term cannot reject the
    # entire seed file; preserved by save_seed_file when already present.
    see_also: list[dict[str, str]] | None = None
    synonyms_to_avoid: list[str] | None = None
    introduced_in_mission: str | None = None

    @field_validator("surface")
    @classmethod
    def surface_must_be_normalized(cls, v: str) -> str:
        if not v:
            raise ValueError("surface must not be empty")
        if v != v.lower().strip():
            raise ValueError(
                f"surface must be normalized (lowercase, trimmed): "
                f"got {v!r}, expected {v.lower().strip()!r}"
            )
        return v

    @field_validator("definition")
    @classmethod
    def definition_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("definition must not be empty")
        return v

    @field_validator("confidence", mode="before")
    @classmethod
    def confidence_must_be_number(cls, v: Any) -> Any:
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise ValueError("confidence must be a number")
        return v

    @field_validator("confidence")
    @classmethod
    def confidence_in_range(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"confidence must be 0.0..1.0, got {v}")
        return v


class GlossarySeedFile(BaseModel):
    """Pydantic model for a glossary seed file (aggregate root)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    terms: list[GlossarySeedTerm]

    @field_validator("terms", mode="before")
    @classmethod
    def bare_terms_key_means_empty_list(cls, v: Any) -> Any:
        if v is None:
            return []
        return v
