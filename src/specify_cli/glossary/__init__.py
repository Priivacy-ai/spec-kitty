"""Glossary semantic integrity runtime for mission framework."""

from .models import (
    TermSurface,
    TermSense,
    SemanticConflict,
    SenseStatus,
    ConflictType,
    Severity,
)
from .exceptions import (
    GlossaryError,
    BlockedByConflict,
    DeferredToAsync,
    AbortResume,
)
from .scope import GlossaryScope
from .resolution import resolve_term
from .conflict import classify_conflict, score_severity, create_conflict
from .middleware import GlossaryCandidateExtractionMiddleware, SemanticCheckMiddleware

__all__ = [
    "TermSurface",
    "TermSense",
    "SemanticConflict",
    "SenseStatus",
    "ConflictType",
    "Severity",
    "GlossaryError",
    "BlockedByConflict",
    "DeferredToAsync",
    "AbortResume",
    "GlossaryScope",
    "resolve_term",
    "classify_conflict",
    "score_severity",
    "create_conflict",
    "GlossaryCandidateExtractionMiddleware",
    "SemanticCheckMiddleware",
]

__version__ = "0.1.0"
