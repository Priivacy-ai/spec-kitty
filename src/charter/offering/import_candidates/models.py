"""Import-candidate schema models.

This module defines two Pydantic models that together produce the
``import-candidate.schema.yaml`` via ``oneOf``.  The two variants are:

* **LegacyImportCandidate** — the original WP01 baseline format with
  ``source.title + source.reference`` and ``target.paradigm + target.directive``.
* **CurationImportCandidate** — the WP03 scaffold with richer
  ``source``, ``classification``, ``adaptation``, and optional
  ``resulting_artifacts`` / ``source_references`` / ``external_references``.

Because the schema uses a top-level ``oneOf`` (not expressible from a single
Pydantic model), ``generate_schemas.py`` uses a dedicated post-processor that
calls ``model_json_schema()`` on each variant and wraps them in ``oneOf``.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Legacy variant (WP01 baseline)
# ---------------------------------------------------------------------------


class LegacyStatus(StrEnum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class LegacySource(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    title: str
    reference: str


class LegacyTarget(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    paradigm: str
    directive: str
    tactic: str | None = None


class LegacyImportCandidate(BaseModel):
    """WP01 baseline import-candidate format."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = Field(pattern=r"^1\.0$")
    id: str = Field(pattern=r"^[A-Z]{2,}-[0-9]{3,}$")
    source: LegacySource
    target: LegacyTarget
    adaptation_notes: str
    status: LegacyStatus


# ---------------------------------------------------------------------------
# Curation variant (WP03 scaffold)
# ---------------------------------------------------------------------------


class CurationStatus(StrEnum):
    PROPOSED = "proposed"
    REVIEWING = "reviewing"
    ADOPTED = "adopted"
    REJECTED = "rejected"


class CurationSource(BaseModel):
    model_config = ConfigDict(frozen=True)

    title: str | None = None
    type: str | None = None
    publisher: str | None = None
    url: str | None = None
    accessed_on: str | None = None


class CurationClassification(BaseModel):
    model_config = ConfigDict(frozen=True)

    target_concepts: list[str] = Field(min_length=1)
    rationale: str | None = None


class CurationAdaptation(BaseModel):
    model_config = ConfigDict(frozen=True)

    summary: str | None = None
    notes: list[str] = Field(default_factory=list)


class SourceReference(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: str | None = None
    path: str | None = None
    lines: str | None = None
    note: str | None = None


class ExternalReference(BaseModel):
    model_config = ConfigDict(frozen=True)

    url: str | None = None
    attribution_reason: str | None = None
    extraction_action: str | None = None


class CurationImportCandidate(BaseModel):
    """WP03 scaffold import-candidate format."""

    model_config = ConfigDict(frozen=True)

    id: str
    source: CurationSource
    classification: CurationClassification
    adaptation: CurationAdaptation
    status: CurationStatus
    resulting_artifacts: list[str] = Field(default_factory=list)
    source_references: list[SourceReference] = Field(default_factory=list)
    external_references: list[ExternalReference] = Field(default_factory=list)
