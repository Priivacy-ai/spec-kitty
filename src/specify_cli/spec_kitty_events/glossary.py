"""Glossary semantic integrity event contracts for Feature 007.

Defines event type constants, value objects, payload models,
reducer output models, and the glossary reducer for
mission-level semantic integrity enforcement.
"""

from __future__ import annotations

from typing import Any, Dict, FrozenSet, List, Literal, Optional, Sequence, Set, Tuple

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from .models import Event, SpecKittyEventsError

# ── Section 1: Constants ─────────────────────────────────────────────────────

GLOSSARY_SCOPE_ACTIVATED: str = "GlossaryScopeActivated"
TERM_CANDIDATE_OBSERVED: str = "TermCandidateObserved"
SEMANTIC_CHECK_EVALUATED: str = "SemanticCheckEvaluated"
GLOSSARY_CLARIFICATION_REQUESTED: str = "GlossaryClarificationRequested"
GLOSSARY_CLARIFICATION_RESOLVED: str = "GlossaryClarificationResolved"
GLOSSARY_SENSE_UPDATED: str = "GlossarySenseUpdated"
GENERATION_BLOCKED_BY_SEMANTIC_CONFLICT: str = "GenerationBlockedBySemanticConflict"
GLOSSARY_STRICTNESS_SET: str = "GlossaryStrictnessSet"

GLOSSARY_EVENT_TYPES: FrozenSet[str] = frozenset({
    GLOSSARY_SCOPE_ACTIVATED,
    TERM_CANDIDATE_OBSERVED,
    SEMANTIC_CHECK_EVALUATED,
    GLOSSARY_CLARIFICATION_REQUESTED,
    GLOSSARY_CLARIFICATION_RESOLVED,
    GLOSSARY_SENSE_UPDATED,
    GENERATION_BLOCKED_BY_SEMANTIC_CONFLICT,
    GLOSSARY_STRICTNESS_SET,
})

# ── Section 2: Value Objects ─────────────────────────────────────────────────


class SemanticConflictEntry(BaseModel):
    """Single conflict finding within a semantic check evaluation."""

    model_config = ConfigDict(frozen=True)

    term: str = Field(..., min_length=1, description="The conflicting term surface text")
    nature: Literal["overloaded", "drift", "ambiguous"] = Field(
        ..., description="Classification of the conflict"
    )
    severity: Literal["low", "medium", "high"] = Field(
        ..., description="Severity level of this conflict"
    )
    description: str = Field(..., description="Human-readable explanation of the conflict")


# ── Section 3: Payload Models ────────────────────────────────────────────────


class GlossaryScopeActivatedPayload(BaseModel):
    """Payload for GlossaryScopeActivated event."""

    model_config = ConfigDict(frozen=True)

    mission_id: str = Field(..., min_length=1, description="Mission context")
    scope_id: str = Field(..., min_length=1, description="Unique scope identifier")
    scope_type: Literal[
        "spec_kitty_core", "team_domain", "audience_domain", "mission_local"
    ] = Field(..., description="Scope category")
    glossary_version_id: str = Field(
        ..., min_length=1, description="Version of the glossary being activated"
    )


class TermCandidateObservedPayload(BaseModel):
    """Payload for TermCandidateObserved event."""

    model_config = ConfigDict(frozen=True)

    mission_id: str = Field(..., min_length=1, description="Mission context")
    scope_id: str = Field(..., min_length=1, description="Scope the term was observed in")
    step_id: str = Field(..., min_length=1, description="Mission step that produced the term")
    term_surface: str = Field(
        ..., min_length=1, description="Raw text form of the observed term"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score (0.0–1.0)"
    )
    actor: str = Field(..., min_length=1, description="Identity of the observing actor")
    step_metadata: Dict[str, str] = Field(
        default_factory=dict,
        description="Mission primitive metadata for the step (no hardcoded step names)",
    )


class GlossarySenseUpdatedPayload(BaseModel):
    """Payload for GlossarySenseUpdated event."""

    model_config = ConfigDict(frozen=True)

    mission_id: str = Field(..., min_length=1, description="Mission context")
    scope_id: str = Field(..., min_length=1, description="Scope of the term")
    term_surface: str = Field(..., min_length=1, description="Term being updated")
    before_sense: Optional[str] = Field(
        None, description="Previous sense value (None if first definition)"
    )
    after_sense: str = Field(..., min_length=1, description="New sense value")
    reason: str = Field(..., description="Why the sense was changed")
    actor: str = Field(..., min_length=1, description="Actor who made the change")


class GlossaryStrictnessSetPayload(BaseModel):
    """Payload for GlossaryStrictnessSet event (mission-wide policy change)."""

    model_config = ConfigDict(frozen=True)

    mission_id: str = Field(..., min_length=1, description="Mission context")
    new_strictness: Literal["off", "medium", "max"] = Field(
        ..., description="The new strictness mode"
    )
    previous_strictness: Optional[Literal["off", "medium", "max"]] = Field(
        None, description="Previous mode (None if initial setting)"
    )
    actor: str = Field(..., min_length=1, description="Actor who changed the setting")


class SemanticCheckEvaluatedPayload(BaseModel):
    """Payload for SemanticCheckEvaluated event (step-level semantic check)."""

    model_config = ConfigDict(frozen=True)

    mission_id: str = Field(..., min_length=1, description="Mission context")
    scope_id: str = Field(..., min_length=1, description="Scope checked against")
    step_id: str = Field(..., min_length=1, description="Step being evaluated")
    conflicts: Tuple[SemanticConflictEntry, ...] = Field(
        ..., description="List of detected conflicts"
    )
    severity: Literal["low", "medium", "high"] = Field(
        ..., description="Overall check severity (max of conflicts)"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Overall confidence score"
    )
    recommended_action: Literal["block", "warn", "pass"] = Field(
        ..., description="Action recommendation based on severity and strictness"
    )
    effective_strictness: Literal["off", "medium", "max"] = Field(
        ..., description="Strictness mode used for this evaluation"
    )
    step_metadata: Dict[str, str] = Field(
        default_factory=dict,
        description="Mission primitive metadata (no hardcoded step names)",
    )


class GlossaryClarificationRequestedPayload(BaseModel):
    """Payload for GlossaryClarificationRequested event."""

    model_config = ConfigDict(frozen=True)

    mission_id: str = Field(..., min_length=1, description="Mission context")
    scope_id: str = Field(..., min_length=1, description="Scope context")
    step_id: str = Field(..., min_length=1, description="Step that triggered clarification")
    semantic_check_event_id: str = Field(
        ...,
        min_length=1,
        description="Event ID of triggering SemanticCheckEvaluated (burst-window key)",
    )
    term: str = Field(..., min_length=1, description="The ambiguous term")
    question: str = Field(..., description="Clarification question text")
    options: Tuple[str, ...] = Field(..., description="Available answer options")
    urgency: Literal["low", "medium", "high"] = Field(
        ..., description="Urgency level"
    )
    actor: str = Field(..., min_length=1, description="Actor who triggered the request")


class GlossaryClarificationResolvedPayload(BaseModel):
    """Payload for GlossaryClarificationResolved event."""

    model_config = ConfigDict(frozen=True)

    mission_id: str = Field(..., min_length=1, description="Mission context")
    clarification_event_id: str = Field(
        ...,
        min_length=1,
        description="Event ID of the originating clarification request",
    )
    selected_meaning: str = Field(
        ..., min_length=1, description="The chosen or entered meaning"
    )
    actor: str = Field(..., min_length=1, description="Identity of the resolving actor")


class GenerationBlockedBySemanticConflictPayload(BaseModel):
    """Payload for GenerationBlockedBySemanticConflict event."""

    model_config = ConfigDict(frozen=True)

    mission_id: str = Field(..., min_length=1, description="Mission context")
    step_id: str = Field(..., min_length=1, description="Step that was blocked")
    conflict_event_ids: Tuple[str, ...] = Field(
        ...,
        min_length=1,
        description="Event IDs of unresolved SemanticCheckEvaluated events",
    )
    blocking_strictness: Literal["medium", "max"] = Field(
        ..., description="Policy mode that triggered the block (never 'off')"
    )
    step_metadata: Dict[str, str] = Field(
        default_factory=dict,
        description="Mission primitive metadata",
    )

# ── Section 4: Reducer Output Models ─────────────────────────────────────────


class GlossaryAnomaly(BaseModel):
    """Non-fatal issue encountered during glossary event reduction."""

    model_config = ConfigDict(frozen=True)

    event_id: str = Field(..., description="ID of the event that caused the anomaly")
    event_type: str = Field(..., description="Type of the problematic event")
    reason: str = Field(..., description="Human-readable explanation")


class ClarificationRecord(BaseModel):
    """Tracks clarification lifecycle for burst-cap enforcement."""

    model_config = ConfigDict(frozen=True)

    request_event_id: str = Field(
        ..., description="Event ID of the clarification request"
    )
    semantic_check_event_id: str = Field(
        ..., description="Burst-window grouping key"
    )
    term: str = Field(..., description="The ambiguous term")
    resolved: bool = Field(default=False, description="Whether resolution received")
    resolution_event_id: Optional[str] = Field(
        default=None, description="Event ID of the resolution (if resolved)"
    )


class ReducedGlossaryState(BaseModel):
    """Projected glossary state from reduce_glossary_events()."""

    model_config = ConfigDict(frozen=True)

    mission_id: str = Field(default="", description="Mission context (from first event)")
    active_scopes: Dict[str, GlossaryScopeActivatedPayload] = Field(
        default_factory=dict, description="scope_id → activation payload"
    )
    current_strictness: Literal["off", "medium", "max"] = Field(
        default="medium", description="Latest mission-wide strictness mode"
    )
    strictness_history: Tuple[GlossaryStrictnessSetPayload, ...] = Field(
        default_factory=tuple, description="Ordered history of strictness changes"
    )
    term_candidates: Dict[Tuple[str, str], Tuple[TermCandidateObservedPayload, ...]] = Field(
        default_factory=dict,
        description="(scope_id, term_surface) → observed candidate payloads",
    )
    term_senses: Dict[Tuple[str, str], GlossarySenseUpdatedPayload] = Field(
        default_factory=dict,
        description="(scope_id, term_surface) → latest sense update",
    )
    clarifications: Tuple[ClarificationRecord, ...] = Field(
        default_factory=tuple, description="Ordered clarification timeline"
    )
    semantic_checks: Tuple[SemanticCheckEvaluatedPayload, ...] = Field(
        default_factory=tuple, description="Ordered check history"
    )
    generation_blocks: Tuple[GenerationBlockedBySemanticConflictPayload, ...] = Field(
        default_factory=tuple, description="Ordered block history"
    )
    anomalies: Tuple[GlossaryAnomaly, ...] = Field(
        default_factory=tuple, description="Non-fatal issues encountered"
    )
    event_count: int = Field(default=0, description="Total glossary events processed")
    last_processed_event_id: Optional[str] = Field(
        default=None, description="Last event_id in processed sequence"
    )

    @field_serializer("term_candidates", when_used="json")
    def _serialize_term_candidates_json(
        self,
        value: Dict[Tuple[str, str], Tuple[TermCandidateObservedPayload, ...]],
    ) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
        """Serialize composite keys as nested maps to avoid JSON key collisions."""
        nested: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
        for (scope_id, term_surface), candidates in sorted(value.items()):
            scope_bucket = nested.setdefault(scope_id, {})
            scope_bucket[term_surface] = [
                candidate.model_dump(mode="json") for candidate in candidates
            ]
        return nested

    @field_serializer("term_senses", when_used="json")
    def _serialize_term_senses_json(
        self,
        value: Dict[Tuple[str, str], GlossarySenseUpdatedPayload],
    ) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """Serialize composite keys as nested maps to avoid JSON key collisions."""
        nested: Dict[str, Dict[str, Dict[str, Any]]] = {}
        for (scope_id, term_surface), sense in sorted(value.items()):
            scope_bucket = nested.setdefault(scope_id, {})
            scope_bucket[term_surface] = sense.model_dump(mode="json")
        return nested


# ── Section 5: Glossary Reducer ──────────────────────────────────────────────


def _check_scope_activated(
    scope_id: str,
    active_scopes: Dict[str, GlossaryScopeActivatedPayload],
    event: Event,
    mode: str,
    anomalies: List[GlossaryAnomaly],
) -> None:
    """Validate that a scope has been activated before use."""
    if scope_id not in active_scopes:
        if mode == "strict":
            raise SpecKittyEventsError(
                f"Event {event.event_id} references unactivated scope '{scope_id}'"
            )
        anomalies.append(GlossaryAnomaly(
            event_id=event.event_id,
            event_type=event.event_type,
            reason=f"References unactivated scope '{scope_id}'",
        ))


def reduce_glossary_events(
    events: Sequence[Event],
    *,
    mode: Literal["strict", "permissive"] = "strict",
) -> ReducedGlossaryState:
    """Fold glossary events into projected glossary state.

    Pipeline:
    1. Filter to glossary event types only
    2. Sort by (lamport_clock, timestamp, event_id)
    3. Deduplicate by event_id
    4. Process each event, mutating intermediate state
    5. Assemble frozen ReducedGlossaryState

    Pure function. No I/O. Deterministic for any causal-order-preserving
    permutation.
    """
    from .status import dedup_events, status_event_sort_key

    if not events:
        return ReducedGlossaryState()

    # 1. Filter
    glossary_events = [e for e in events if e.event_type in GLOSSARY_EVENT_TYPES]

    if not glossary_events:
        return ReducedGlossaryState()

    # 2. Sort
    sorted_events = sorted(glossary_events, key=status_event_sort_key)

    # 3. Dedup
    unique_events = dedup_events(sorted_events)

    # Extract mission_id from first event
    first_payload = unique_events[0].payload
    mission_id = str(first_payload.get("mission_id", ""))

    # 4. Process (mutable intermediates)
    active_scopes: Dict[str, GlossaryScopeActivatedPayload] = {}
    current_strictness: str = "medium"
    strictness_history: List[GlossaryStrictnessSetPayload] = []
    term_candidates: Dict[Tuple[str, str], List[TermCandidateObservedPayload]] = {}
    term_senses: Dict[Tuple[str, str], GlossarySenseUpdatedPayload] = {}
    semantic_checks: List[SemanticCheckEvaluatedPayload] = []
    semantic_check_event_ids: Set[str] = set()
    clarifications: List[ClarificationRecord] = []
    generation_blocks: List[GenerationBlockedBySemanticConflictPayload] = []
    anomalies: List[GlossaryAnomaly] = []

    for event in unique_events:
        payload_data = event.payload
        etype = event.event_type

        if etype == GLOSSARY_SCOPE_ACTIVATED:
            p_scope = GlossaryScopeActivatedPayload(**payload_data)
            active_scopes[p_scope.scope_id] = p_scope

        elif etype == GLOSSARY_STRICTNESS_SET:
            p_strict = GlossaryStrictnessSetPayload(**payload_data)
            current_strictness = p_strict.new_strictness
            strictness_history.append(p_strict)

        elif etype == TERM_CANDIDATE_OBSERVED:
            p_term = TermCandidateObservedPayload(**payload_data)
            _check_scope_activated(p_term.scope_id, active_scopes, event, mode, anomalies)
            term_candidates.setdefault((p_term.scope_id, p_term.term_surface), []).append(p_term)

        elif etype == GLOSSARY_SENSE_UPDATED:
            p_sense = GlossarySenseUpdatedPayload(**payload_data)
            _check_scope_activated(p_sense.scope_id, active_scopes, event, mode, anomalies)
            sense_key = (p_sense.scope_id, p_sense.term_surface)
            if sense_key not in term_candidates:
                if mode == "strict":
                    raise SpecKittyEventsError(
                        f"GlossarySenseUpdated for unobserved term '{p_sense.term_surface}' "
                        f"in event {event.event_id}"
                    )
                anomalies.append(GlossaryAnomaly(
                    event_id=event.event_id,
                    event_type=event.event_type,
                    reason=f"Sense update for unobserved term '{p_sense.term_surface}'",
                ))
            term_senses[sense_key] = p_sense

        elif etype == SEMANTIC_CHECK_EVALUATED:
            p_check = SemanticCheckEvaluatedPayload(**payload_data)
            _check_scope_activated(p_check.scope_id, active_scopes, event, mode, anomalies)
            semantic_checks.append(p_check)
            semantic_check_event_ids.add(event.event_id)

        elif etype == GLOSSARY_CLARIFICATION_REQUESTED:
            p_clar = GlossaryClarificationRequestedPayload(**payload_data)
            _check_scope_activated(p_clar.scope_id, active_scopes, event, mode, anomalies)

            if p_clar.semantic_check_event_id not in semantic_check_event_ids:
                if mode == "strict":
                    raise SpecKittyEventsError(
                        f"GlossaryClarificationRequested references unknown "
                        f"semantic check '{p_clar.semantic_check_event_id}' "
                        f"in event {event.event_id}"
                    )
                anomalies.append(GlossaryAnomaly(
                    event_id=event.event_id,
                    event_type=event.event_type,
                    reason=(
                        f"References unknown semantic check "
                        f"'{p_clar.semantic_check_event_id}'"
                    ),
                ))
                continue

            active_for_check = sum(
                1 for c in clarifications
                if c.semantic_check_event_id == p_clar.semantic_check_event_id
                and not c.resolved
            )

            if active_for_check >= 3:
                if mode == "strict":
                    raise SpecKittyEventsError(
                        f"Clarification burst cap exceeded for semantic check "
                        f"'{p_clar.semantic_check_event_id}' in event {event.event_id}"
                    )
                anomalies.append(GlossaryAnomaly(
                    event_id=event.event_id,
                    event_type=event.event_type,
                    reason=(
                        f"Burst cap exceeded: >3 active clarifications for "
                        f"semantic check '{p_clar.semantic_check_event_id}'"
                    ),
                ))
            else:
                clarifications.append(ClarificationRecord(
                    request_event_id=event.event_id,
                    semantic_check_event_id=p_clar.semantic_check_event_id,
                    term=p_clar.term,
                ))

        elif etype == GLOSSARY_CLARIFICATION_RESOLVED:
            p_res = GlossaryClarificationResolvedPayload(**payload_data)

            found = False
            for i, record in enumerate(clarifications):
                if record.request_event_id == p_res.clarification_event_id:
                    clarifications[i] = ClarificationRecord(
                        request_event_id=record.request_event_id,
                        semantic_check_event_id=record.semantic_check_event_id,
                        term=record.term,
                        resolved=True,
                        resolution_event_id=event.event_id,
                    )
                    found = True
                    break

            if not found:
                if mode == "strict":
                    raise SpecKittyEventsError(
                        f"GlossaryClarificationResolved references unknown "
                        f"clarification '{p_res.clarification_event_id}' "
                        f"in event {event.event_id}"
                    )
                anomalies.append(GlossaryAnomaly(
                    event_id=event.event_id,
                    event_type=event.event_type,
                    reason=(
                        f"Resolution for unknown clarification "
                        f"'{p_res.clarification_event_id}'"
                    ),
                ))

        elif etype == GENERATION_BLOCKED_BY_SEMANTIC_CONFLICT:
            p_block = GenerationBlockedBySemanticConflictPayload(**payload_data)
            generation_blocks.append(p_block)

    # 5. Assemble frozen state
    last_event = unique_events[-1]

    return ReducedGlossaryState(
        mission_id=mission_id,
        active_scopes=active_scopes,
        current_strictness=current_strictness,  # type: ignore[arg-type]
        strictness_history=tuple(strictness_history),
        term_candidates={
            k: tuple(v) for k, v in term_candidates.items()
        },
        term_senses=term_senses,
        clarifications=tuple(clarifications),
        semantic_checks=tuple(semantic_checks),
        generation_blocks=tuple(generation_blocks),
        anomalies=tuple(anomalies),
        event_count=len(unique_events),
        last_processed_event_id=last_event.event_id,
    )
