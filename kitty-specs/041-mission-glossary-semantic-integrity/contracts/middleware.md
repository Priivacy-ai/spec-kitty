# Middleware Contracts: Glossary Semantic Integrity

**Feature**: 041-mission-glossary-semantic-integrity
**Date**: 2026-02-16
**Status**: Complete

## Overview

This document defines the middleware pipeline interfaces for glossary semantic integrity checks. All middleware components follow a common protocol and execute in a fixed order.

---

## Base Middleware Protocol

All glossary middleware components implement this protocol:

```python
from typing import Protocol
from specify_cli.missions.primitives import PrimitiveExecutionContext

class GlossaryMiddleware(Protocol):
    """Base protocol for glossary middleware components."""

    def process(self, context: PrimitiveExecutionContext) -> PrimitiveExecutionContext:
        """
        Process primitive execution context.

        Args:
            context: Current execution context with inputs, metadata, config

        Returns:
            Modified context (may add fields like extracted_terms, conflicts)

        Raises:
            BlockedByConflict: If generation must be blocked
        """
        ...
```

---

## Middleware Pipeline Order

Middleware executes in this fixed order:

1. **GlossaryCandidateExtractionMiddleware** - Extract terms from step I/O
2. **SemanticCheckMiddleware** - Resolve terms, detect conflicts
3. **GenerationGateMiddleware** - Block generation on high-severity conflicts
4. **ClarificationMiddleware** - Prompt user for resolution (if blocked)
5. **ResumeMiddleware** - Load checkpoint, restore state (on retry)

---

## 1. GlossaryCandidateExtractionMiddleware

**Purpose**: Extract candidate terms from step inputs/outputs using metadata hints + deterministic heuristics.

**Interface**:

```python
class GlossaryCandidateExtractionMiddleware:
    """Extract candidate terms from step inputs/outputs."""

    def __init__(self, extraction_config: ExtractionConfig):
        """
        Initialize extraction middleware.

        Args:
            extraction_config: Configuration for term extraction
                - metadata_hints: glossary_watch_terms, glossary_aliases, etc.
                - heuristic_patterns: quoted_phrases, acronyms, casing
                - confidence_thresholds: high/medium/low boundaries
        """
        self.extraction_config = extraction_config

    def process(self, context: PrimitiveExecutionContext) -> PrimitiveExecutionContext:
        """
        Extract terms from step inputs/outputs.

        Modifies context:
            - Adds context.extracted_terms: List[ExtractedTerm]

        Emits events:
            - TermCandidateObserved (for each extracted term)

        Returns:
            Modified context with extracted_terms field
        """
        ...
```

**ExtractedTerm structure**:

```python
from dataclasses import dataclass

@dataclass
class ExtractedTerm:
    surface: str                # e.g., "workspace"
    confidence: float           # 0.0-1.0
    extraction_method: str      # e.g., "metadata_hint", "casing_pattern"
    context: str                # e.g., "description field"
    source_step: str            # e.g., "step-specify-001"
```

**Example usage**:

```python
extraction_middleware = GlossaryCandidateExtractionMiddleware(
    extraction_config=ExtractionConfig(
        metadata_hints={
            "glossary_watch_terms": ["workspace", "mission"],
            "glossary_fields": ["description", "requirements"]
        },
        heuristic_patterns=["quoted_phrases", "acronyms", "casing"],
        confidence_thresholds={"high": 0.8, "medium": 0.5, "low": 0.3}
    )
)

context = extraction_middleware.process(context)
# context.extracted_terms = [ExtractedTerm(...), ...]
```

---

## 2. SemanticCheckMiddleware

**Purpose**: Resolve extracted terms against scope hierarchy, detect conflicts.

**Interface**:

```python
class SemanticCheckMiddleware:
    """Resolve terms and detect semantic conflicts."""

    def __init__(self, glossary_store: GlossaryStore):
        """
        Initialize semantic check middleware.

        Args:
            glossary_store: Access to active glossary scopes
                - Provides scope resolution (mission_local -> team_domain -> audience_domain -> spec_kitty_core)
                - Loads seed files from .kittify/glossaries/
        """
        self.glossary_store = glossary_store

    def process(self, context: PrimitiveExecutionContext) -> PrimitiveExecutionContext:
        """
        Resolve terms and detect conflicts.

        Requires:
            - context.extracted_terms (from extraction middleware)

        Modifies context:
            - Adds context.conflicts: List[SemanticConflict]

        Emits events:
            - SemanticCheckEvaluated (with findings, overall severity, recommended action)

        Returns:
            Modified context with conflicts field
        """
        ...
```

**SemanticConflict structure** (see [data-model.md](../data-model.md)):

```python
from dataclasses import dataclass
from enum import Enum

class ConflictType(Enum):
    UNKNOWN = "unknown"
    AMBIGUOUS = "ambiguous"
    INCONSISTENT = "inconsistent"
    UNRESOLVED_CRITICAL = "unresolved_critical"

class Severity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

@dataclass
class SemanticConflict:
    term: str                       # e.g., "workspace"
    conflict_type: ConflictType
    severity: Severity
    confidence: float               # 0.0-1.0
    candidate_senses: List[SenseRef]
    context: str                    # Usage location
```

**Example usage**:

```python
semantic_check_middleware = SemanticCheckMiddleware(
    glossary_store=GlossaryStore(
        scopes=[GlossaryScope.MISSION_LOCAL, GlossaryScope.TEAM_DOMAIN,
                GlossaryScope.AUDIENCE_DOMAIN, GlossaryScope.SPEC_KITTY_CORE]
    )
)

context = semantic_check_middleware.process(context)
# context.conflicts = [SemanticConflict(...), ...]
```

---

## 3. GenerationGateMiddleware

**Purpose**: Block LLM generation on unresolved high-severity conflicts.

**Interface**:

```python
class GenerationGateMiddleware:
    """Block generation on unresolved high-severity conflicts."""

    def __init__(self, strictness_policy: StrictnessPolicy):
        """
        Initialize generation gate middleware.

        Args:
            strictness_policy: Strictness mode configuration
                - Resolves precedence: global -> mission -> step -> runtime override
                - Modes: off, medium, max
        """
        self.strictness_policy = strictness_policy

    def process(self, context: PrimitiveExecutionContext) -> PrimitiveExecutionContext:
        """
        Block generation if high-severity conflicts exist.

        Requires:
            - context.conflicts (from semantic check middleware)
            - context.strictness (resolved strictness mode)

        Emits events:
            - GenerationBlockedBySemanticConflict (if blocked)

        Raises:
            BlockedByConflict: If generation must be blocked

        Returns:
            Unmodified context (if pass)
        """
        ...
```

**Strictness policy logic**:

```python
from enum import Enum

class Strictness(Enum):
    OFF = "off"       # No blocking
    MEDIUM = "medium" # Block only high-severity
    MAX = "max"       # Block any unresolved conflict

def should_block(strictness: Strictness, conflicts: List[SemanticConflict]) -> bool:
    """Determine if generation should be blocked."""
    if strictness == Strictness.OFF:
        return False
    elif strictness == Strictness.MEDIUM:
        return any(c.severity == Severity.HIGH for c in conflicts)
    elif strictness == Strictness.MAX:
        return len(conflicts) > 0
```

**Example usage**:

```python
generation_gate_middleware = GenerationGateMiddleware(
    strictness_policy=StrictnessPolicy(
        global_default=Strictness.MEDIUM,
        mission_override=None,
        step_override=None,
        runtime_override=None
    )
)

try:
    context = generation_gate_middleware.process(context)
    # Generation allowed - proceed to next step
except BlockedByConflict as e:
    # Generation blocked - proceed to clarification
    conflicts = e.conflicts
```

---

## 4. ClarificationMiddleware

**Purpose**: Render ranked candidates, prompt user for resolution (interactive or async).

**Interface**:

```python
class ClarificationMiddleware:
    """Prompt user for conflict resolution."""

    def __init__(self, interaction_mode: InteractionMode):
        """
        Initialize clarification middleware.

        Args:
            interaction_mode: Interactive (CLI) or non-interactive (CI)
        """
        self.interaction_mode = interaction_mode

    def process(self, context: PrimitiveExecutionContext) -> PrimitiveExecutionContext:
        """
        Prompt user for conflict resolution.

        Requires:
            - context.conflicts (from generation gate)

        Emits events:
            - GlossaryClarificationRequested (on defer or non-interactive)
            - GlossaryClarificationResolved (on user selection)
            - GlossarySenseUpdated (on custom sense)

        Raises:
            DeferredToAsync: If user defers resolution

        Returns:
            Modified context with updated glossary (if resolved)
        """
        ...
```

**Clarification flow**:

```python
from enum import Enum

class ClarificationChoice(Enum):
    CANDIDATE_SELECTED = "candidate"  # User picked from candidates
    CUSTOM_SENSE = "custom"           # User provided custom definition
    DEFER_ASYNC = "defer"             # User deferred to async resolution

def prompt_for_resolution(conflict: SemanticConflict) -> ClarificationChoice:
    """
    Render conflict and prompt for resolution.

    Displays:
        - Term, context, scope
        - Ranked candidate senses (by confidence)
        - Options: 1..N (candidates), C (custom), D (defer)

    Returns:
        User's choice
    """
    ...
```

**Example usage**:

```python
clarification_middleware = ClarificationMiddleware(
    interaction_mode=InteractionMode.INTERACTIVE
)

try:
    context = clarification_middleware.process(context)
    # User resolved conflict - glossary updated
except DeferredToAsync:
    # User deferred resolution - exit with blocked status
    exit(1)
```

---

## 5. ResumeMiddleware

**Purpose**: Load checkpoint from events, restore step execution context.

**Interface**:

```python
class ResumeMiddleware:
    """Resume execution from checkpoint after conflict resolution."""

    def __init__(self, checkpoint_store: CheckpointStore):
        """
        Initialize resume middleware.

        Args:
            checkpoint_store: Access to StepCheckpointed events
                - Loads from event log
                - Verifies input_hash integrity
        """
        self.checkpoint_store = checkpoint_store

    def process(self, context: PrimitiveExecutionContext) -> PrimitiveExecutionContext:
        """
        Resume from checkpoint.

        Requires:
            - context.retry_token (from user retry request)

        Modifies context:
            - Restores strictness, scope_refs from checkpoint
            - Loads updated glossary state from GlossarySenseUpdated events

        Emits events:
            - None (checkpoint already exists)

        Returns:
            Restored context (ready to resume from cursor)
        """
        ...
```

**Resume flow**:

```python
def resume_from_checkpoint(retry_token: str, context: PrimitiveExecutionContext) -> PrimitiveExecutionContext:
    """
    Resume execution from checkpoint.

    Steps:
        1. Load StepCheckpointed event by retry_token
        2. Verify input_hash matches current inputs
        3. If changed: prompt user for confirmation
        4. Restore strictness, scope_refs from checkpoint
        5. Load updated glossary state from events
        6. Resume from cursor (skip already-completed stages)

    Returns:
        Restored context
    """
    ...
```

**Example usage**:

```python
resume_middleware = ResumeMiddleware(
    checkpoint_store=CheckpointStore(event_log)
)

context = resume_middleware.process(context)
# context.strictness, context.scope_refs restored from checkpoint
# Skip to cursor: "pre_generation_gate"
```

---

## Pipeline Composition

Middleware components are composed into a pipeline:

```python
from typing import List

class GlossaryMiddlewarePipeline:
    """Compose glossary middleware components into a pipeline."""

    def __init__(self, middleware: List[GlossaryMiddleware]):
        """
        Initialize pipeline.

        Args:
            middleware: Ordered list of middleware components
        """
        self.middleware = middleware

    def process(self, context: PrimitiveExecutionContext) -> PrimitiveExecutionContext:
        """
        Execute middleware pipeline.

        Args:
            context: Initial execution context

        Returns:
            Final context (after all middleware)

        Raises:
            BlockedByConflict: If generation gate blocks
            DeferredToAsync: If clarification deferred
        """
        for mw in self.middleware:
            context = mw.process(context)
        return context
```

**Example pipeline setup**:

```python
pipeline = GlossaryMiddlewarePipeline([
    GlossaryCandidateExtractionMiddleware(extraction_config),
    SemanticCheckMiddleware(glossary_store),
    GenerationGateMiddleware(strictness_policy),
    ClarificationMiddleware(interaction_mode),
    ResumeMiddleware(checkpoint_store)
])

try:
    final_context = pipeline.process(initial_context)
    # All checks passed - proceed to generation
except BlockedByConflict:
    # Generation blocked - clarification required
except DeferredToAsync:
    # User deferred resolution - exit
```

---

## Exception Hierarchy

```python
class GlossaryError(Exception):
    """Base exception for glossary errors."""

class BlockedByConflict(GlossaryError):
    """Generation blocked by unresolved high-severity conflict."""
    def __init__(self, conflicts: List[SemanticConflict]):
        self.conflicts = conflicts
        super().__init__(f"Generation blocked by {len(conflicts)} conflict(s)")

class DeferredToAsync(GlossaryError):
    """User deferred conflict resolution to async mode."""
    def __init__(self, conflict_id: str):
        self.conflict_id = conflict_id
        super().__init__(f"Conflict {conflict_id} deferred to async resolution")

class AbortResume(GlossaryError):
    """User aborted resume (context changed)."""
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Resume aborted: {reason}")
```

---

## Testing Middleware

**Unit tests** (per middleware component):
- Mock inputs, assert outputs
- Verify events emitted at correct stage
- Test exception handling (BlockedByConflict, DeferredToAsync)

**Integration tests** (full pipeline):
- Run extraction → check → gate → clarification → resume
- Verify event order: TermCandidateObserved → SemanticCheckEvaluated → GenerationBlockedBySemanticConflict → GlossaryClarificationResolved
- Test edge cases (no conflicts, all conflicts resolved, defer to async)

**Example integration test**:

```python
def test_full_pipeline_with_conflict_resolution():
    # Setup
    context = PrimitiveExecutionContext(inputs={"description": "The workspace contains files"})
    pipeline = create_pipeline()

    # Execute
    try:
        final_context = pipeline.process(context)
        assert False, "Should have blocked"
    except BlockedByConflict:
        # Expected - clarification required
        pass

    # User resolves conflict
    resolve_conflict(conflict_id="uuid-1234", choice="candidate:1")

    # Retry with resume
    context.retry_token = "uuid-1234"
    final_context = pipeline.process(context)

    # Assert
    assert final_context.glossary_updated
    assert len(final_context.conflicts) == 0
```

---

## See Also

- [events.md](events.md) - Event contract schemas
- [../data-model.md](../data-model.md) - Entity definitions
- [../research.md](../research.md) - Architectural research decisions
