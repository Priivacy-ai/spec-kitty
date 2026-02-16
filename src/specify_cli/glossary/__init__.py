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
    ResumeMiddleware,
)
from .strictness import (
    Strictness,
    resolve_strictness,
    load_global_strictness,
    should_block,
    categorize_conflicts,
)
from .checkpoint import (
    StepCheckpoint,
    ScopeRef,
    compute_input_hash,
    create_checkpoint,
    verify_input_hash,
    handle_context_change,
    load_checkpoint,
    parse_checkpoint_event,
    checkpoint_to_dict,
    compute_input_diff,
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
    "ResumeMiddleware",
    "Strictness",
    "resolve_strictness",
    "load_global_strictness",
    "should_block",
    "categorize_conflicts",
    "StepCheckpoint",
    "ScopeRef",
    "compute_input_hash",
    "create_checkpoint",
    "verify_input_hash",
    "handle_context_change",
    "load_checkpoint",
    "parse_checkpoint_event",
    "checkpoint_to_dict",
    "compute_input_diff",
]

__version__ = "0.1.0"
