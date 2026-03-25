"""Shared utilities and primitive types for the doctrine package.

Provides cross-cutting concerns used by multiple artifact subpackages:

- :class:`~doctrine.shared.schema_utils.SchemaUtilities` — cached JSON Schema loading
- :exc:`~doctrine.shared.exceptions.DoctrineArtifactLoadError` — load failure signal
- :exc:`~doctrine.shared.exceptions.DoctrineResolutionCycleError` — cycle detection signal

Glossary primitive types (canonical definitions in kernel, re-exported here for convenience):

- :class:`~kernel.glossary_types.Strictness`
- :class:`~kernel.glossary_types.ExtractedTerm`
- :class:`~kernel.glossary_types.SemanticConflict`
- :class:`~kernel.glossary_types.ScopeRef`
- :class:`~kernel.glossary_types.GlossaryScope`
"""

from __future__ import annotations

from .exceptions import DoctrineArtifactLoadError, DoctrineResolutionCycleError
from .schema_utils import SchemaUtilities
from kernel.glossary_types import (
    ConflictType,
    ExtractedTerm,
    GlossaryScope,
    SemanticConflict,
    ScopeRef,
    SenseRef,
    Severity,
    Strictness,
    TermSurface,
)

__all__ = [
    "ConflictType",
    "DoctrineArtifactLoadError",
    "DoctrineResolutionCycleError",
    "ExtractedTerm",
    "GlossaryScope",
    "SchemaUtilities",
    "SemanticConflict",
    "ScopeRef",
    "SenseRef",
    "Severity",
    "Strictness",
    "TermSurface",
]
