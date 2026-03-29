"""Core data models for glossary semantic integrity."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

# Canonical definitions moved to doctrine; re-exported here for backward compat.
from kernel.glossary_types import (  # noqa: F401
    ConflictType,
    SemanticConflict,
    SenseRef,
    Severity,
    TermSurface,
)


class SenseStatus(Enum):
    """Status of a TermSense."""

    DRAFT = "draft"  # Auto-extracted, low confidence
    ACTIVE = "active"  # Promoted by user or high confidence
    DEPRECATED = "deprecated"  # Kept in history, not in active resolution


@dataclass
class Provenance:
    """Provenance metadata for a TermSense."""

    actor_id: str  # e.g., "user:alice" or "llm:claude-sonnet-4"
    timestamp: datetime
    source: str  # e.g., "user_clarification", "metadata_hint", "auto_extraction"


@dataclass
class TermSense:
    """Meaning of a TermSurface within a specific GlossaryScope."""

    surface: TermSurface
    scope: str  # GlossaryScope enum value (defined in scope.py)
    definition: str
    provenance: Provenance
    confidence: float  # 0.0-1.0
    status: SenseStatus = SenseStatus.DRAFT

    def __post_init__(self) -> None:
        # Validate confidence range
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be 0.0-1.0: {self.confidence}")
        # Validate definition not empty
        if not self.definition.strip():
            raise ValueError("Definition cannot be empty")


# Serialization helpers for event emission


def term_surface_to_dict(ts: TermSurface) -> dict[str, Any]:
    """Serialize TermSurface to dict."""
    return {"surface_text": ts.surface_text}


def term_sense_to_dict(ts: TermSense) -> dict[str, Any]:
    """Serialize TermSense to dict."""
    return {
        "surface": term_surface_to_dict(ts.surface),
        "scope": ts.scope,
        "definition": ts.definition,
        "provenance": {
            "actor_id": ts.provenance.actor_id,
            "timestamp": ts.provenance.timestamp.isoformat(),
            "source": ts.provenance.source,
        },
        "confidence": ts.confidence,
        "status": ts.status.value,
    }


def semantic_conflict_to_dict(sc: SemanticConflict) -> dict[str, Any]:
    """Serialize SemanticConflict to dict."""
    return {
        "term": term_surface_to_dict(sc.term),
        "conflict_type": sc.conflict_type.value,
        "severity": sc.severity.value,
        "confidence": sc.confidence,
        "candidate_senses": [
            {
                "surface": c.surface,
                "scope": c.scope,
                "definition": c.definition,
                "confidence": c.confidence,
            }
            for c in sc.candidate_senses
        ],
        "context": sc.context,
    }
