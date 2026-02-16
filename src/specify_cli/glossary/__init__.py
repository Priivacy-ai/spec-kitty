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
from .middleware import (
    GlossaryCandidateExtractionMiddleware,
    SemanticCheckMiddleware,
    GenerationGateMiddleware,
    ClarificationMiddleware,
)
from .rendering import render_conflict, render_conflict_batch
from .prompts import (
    PromptChoice,
    prompt_conflict_resolution,
    prompt_conflict_resolution_safe,
    prompt_context_change_confirmation,
    is_interactive,
    auto_defer_conflicts,
)
from .strictness import (
    Strictness,
    resolve_strictness,
    load_global_strictness,
    should_block,
    categorize_conflicts,
)

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
    "GenerationGateMiddleware",
    "ClarificationMiddleware",
    "render_conflict",
    "render_conflict_batch",
    "PromptChoice",
    "prompt_conflict_resolution",
    "prompt_conflict_resolution_safe",
    "prompt_context_change_confirmation",
    "is_interactive",
    "auto_defer_conflicts",
    "Strictness",
    "resolve_strictness",
    "load_global_strictness",
    "should_block",
    "categorize_conflicts",
]

__version__ = "0.1.0"
