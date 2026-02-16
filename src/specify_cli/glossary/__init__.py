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
from .clarification import ClarificationMiddleware
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
from .events import (
    EVENTS_AVAILABLE,
    get_event_log_path,
    append_event,
    read_events,
    emit_term_candidate_observed,
    emit_semantic_check_evaluated,
    emit_generation_blocked_event,
    emit_step_checkpointed,
    emit_clarification_requested,
    emit_clarification_resolved,
    emit_sense_updated,
    emit_scope_activated,
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
    "ClarificationMiddleware",
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
    "EVENTS_AVAILABLE",
    "get_event_log_path",
    "append_event",
    "read_events",
    "emit_term_candidate_observed",
    "emit_semantic_check_evaluated",
    "emit_generation_blocked_event",
    "emit_step_checkpointed",
    "emit_clarification_requested",
    "emit_clarification_resolved",
    "emit_sense_updated",
    "emit_scope_activated",
]

__version__ = "0.1.0"
