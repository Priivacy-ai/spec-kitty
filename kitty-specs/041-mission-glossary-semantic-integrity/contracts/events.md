# Event Contracts: Glossary Semantic Integrity

**Feature**: 041-mission-glossary-semantic-integrity
**Date**: 2026-02-16
**Status**: Complete
**Authority**: Feature 007 (spec-kitty-events package)

## Overview

This document references the canonical glossary event schemas defined in Feature 007. CLI implementation MUST import these events from `spec-kitty-events` package, NOT redefine them locally.

**Package import path**: `spec_kitty_events.glossary.events`

**Contract authority**: `/Users/robert/ClaudeCowork/Spec-Kitty-Cowork/spec-kitty-planning/product-ideas/prd-mission-glossary-semantic-integrity-v1.md`

---

## Canonical Events (Feature 007)

### 1. GlossaryScopeActivated

**Trigger**: Mission starts or scope selected
**Purpose**: Record which glossary scopes are active for this mission run

**Required fields**:

```python
{
    "event_type": "GlossaryScopeActivated",
    "scope_id": str,              # e.g., "team_domain"
    "glossary_version_id": str,   # e.g., "v3"
    "timestamp": datetime,
    "mission_id": str,
    "run_id": str
}
```

**Consumers**: Orchestration runtime, projection layer

**Example**:

```python
GlossaryScopeActivated(
    scope_id="team_domain",
    glossary_version_id="v3",
    timestamp=datetime(2026, 2, 16, 12, 0, 0),
    mission_id="041-mission",
    run_id="run-2026-02-16-001"
)
```

---

### 2. TermCandidateObserved

**Trigger**: New or uncertain term appears in step input/output
**Purpose**: Record term extraction for candidate glossary entry

**Required fields**:

```python
{
    "event_type": "TermCandidateObserved",
    "term": str,                # e.g., "workspace"
    "source_step": str,         # e.g., "step-specify-001"
    "actor_id": str,            # e.g., "user:alice" or "llm:claude-sonnet-4"
    "confidence": float,        # 0.0-1.0
    "extraction_method": str,   # e.g., "metadata_hint", "casing_pattern"
    "context": str,             # e.g., "description field"
    "timestamp": datetime,
    "mission_id": str,
    "run_id": str
}
```

**Consumers**: Candidate scorer, clarification policy

**Example**:

```python
TermCandidateObserved(
    term="workspace",
    source_step="step-specify-001",
    actor_id="llm:claude-sonnet-4",
    confidence=0.8,
    extraction_method="casing_pattern",
    context="description field",
    timestamp=datetime(2026, 2, 16, 12, 5, 0),
    mission_id="041-mission",
    run_id="run-2026-02-16-001"
)
```

---

### 3. SemanticCheckEvaluated

**Trigger**: Step-level pre-generation validation completes
**Purpose**: Record conflict detection results and recommended action

**Required fields**:

```python
{
    "event_type": "SemanticCheckEvaluated",
    "step_id": str,
    "mission_id": str,
    "run_id": str,
    "timestamp": datetime,
    "findings": List[ConflictFinding],  # See structure below
    "overall_severity": str,            # "low" | "medium" | "high"
    "confidence": float,                # 0.0-1.0
    "effective_strictness": str,        # "off" | "medium" | "max"
    "recommended_action": str,          # "proceed" | "warn" | "block"
    "blocked": bool                     # True if generation was blocked
}
```

**ConflictFinding structure**:

```python
{
    "term": str,
    "conflict_type": str,  # "unknown" | "ambiguous" | "inconsistent" | "unresolved_critical"
    "severity": str,       # "low" | "medium" | "high"
    "confidence": float,
    "candidate_senses": List[SenseRef],  # See structure below
    "context": str
}
```

**SenseRef structure**:

```python
{
    "surface": str,
    "scope": str,
    "definition": str,
    "confidence": float
}
```

**Consumers**: Execution gate, UX prompt, dashboards

**Example**:

```python
SemanticCheckEvaluated(
    step_id="step-specify-001",
    mission_id="041-mission",
    run_id="run-2026-02-16-001",
    timestamp=datetime(2026, 2, 16, 12, 10, 0),
    findings=[
        ConflictFinding(
            term="workspace",
            conflict_type="ambiguous",
            severity="high",
            confidence=0.9,
            candidate_senses=[
                SenseRef(surface="workspace", scope="team_domain",
                         definition="Git worktree directory", confidence=0.9),
                SenseRef(surface="workspace", scope="team_domain",
                         definition="VS Code workspace file", confidence=0.7)
            ],
            context="description field"
        )
    ],
    overall_severity="high",
    confidence=0.9,
    effective_strictness="medium",
    recommended_action="block",
    blocked=True
)
```

---

### 4. GlossaryClarificationRequested

**Trigger**: Policy requires user clarification (high severity or low confidence critical term)
**Purpose**: Record clarification question sent to user

**Required fields**:

```python
{
    "event_type": "GlossaryClarificationRequested",
    "question": str,          # Human-readable question
    "term": str,              # Term requiring clarification
    "options": List[str],     # Ranked candidate definitions
    "urgency": str,           # "high" | "medium" | "low"
    "timestamp": datetime,
    "mission_id": str,
    "run_id": str,
    "step_id": str,
    "conflict_id": str        # UUID for tracking resolution
}
```

**Consumers**: Mission participant UI, CLI, SaaS decision inbox

**Example**:

```python
GlossaryClarificationRequested(
    question="What does 'workspace' mean in this context?",
    term="workspace",
    options=[
        "Git worktree directory for a work package",
        "VS Code workspace configuration file"
    ],
    urgency="high",
    timestamp=datetime(2026, 2, 16, 12, 15, 0),
    mission_id="041-mission",
    run_id="run-2026-02-16-001",
    step_id="step-specify-001",
    conflict_id="uuid-1234-5678"
)
```

---

### 5. GlossaryClarificationResolved

**Trigger**: User/participant answer accepted
**Purpose**: Record conflict resolution (selected from candidates)

**Required fields**:

```python
{
    "event_type": "GlossaryClarificationResolved",
    "conflict_id": str,           # UUID from GlossaryClarificationRequested
    "term_surface": str,          # e.g., "workspace"
    "selected_sense": SenseRef,   # See structure in SemanticCheckEvaluated
    "actor": ActorIdentity,       # See structure below
    "timestamp": datetime,
    "resolution_mode": str,       # "interactive" | "async"
    "provenance": Provenance      # See structure below
}
```

**ActorIdentity structure**:

```python
{
    "actor_id": str,
    "actor_type": str,  # "human" | "llm" | "service"
    "display_name": str
}
```

**Provenance structure**:

```python
{
    "source": str,      # e.g., "user_clarification"
    "timestamp": datetime,
    "actor_id": str
}
```

**Consumers**: Glossary updater, execution gate

**Example**:

```python
GlossaryClarificationResolved(
    conflict_id="uuid-1234-5678",
    term_surface="workspace",
    selected_sense=SenseRef(
        surface="workspace",
        scope="team_domain",
        definition="Git worktree directory for a work package",
        confidence=0.9
    ),
    actor=ActorIdentity(
        actor_id="user:alice",
        actor_type="human",
        display_name="Alice"
    ),
    timestamp=datetime(2026, 2, 16, 12, 20, 0),
    resolution_mode="interactive",
    provenance=Provenance(
        source="user_clarification",
        timestamp=datetime(2026, 2, 16, 12, 20, 0),
        actor_id="user:alice"
    )
)
```

---

### 6. GlossarySenseUpdated

**Trigger**: New sense or sense edit accepted (custom definition from user)
**Purpose**: Record glossary modification

**Required fields**:

```python
{
    "event_type": "GlossarySenseUpdated",
    "term_surface": str,
    "scope": str,                # e.g., "team_domain"
    "new_sense": TermSense,      # See structure below
    "actor": ActorIdentity,
    "timestamp": datetime,
    "update_type": str,          # "create" | "update"
    "provenance": Provenance
}
```

**TermSense structure**:

```python
{
    "surface": str,
    "scope": str,
    "definition": str,
    "confidence": float,
    "status": str  # "draft" | "active" | "deprecated"
}
```

**Consumers**: Projection, audit views

**Example**:

```python
GlossarySenseUpdated(
    term_surface="workspace",
    scope="team_domain",
    new_sense=TermSense(
        surface="workspace",
        scope="team_domain",
        definition="Git worktree directory for a work package",
        confidence=1.0,
        status="active"
    ),
    actor=ActorIdentity(actor_id="user:alice", actor_type="human", display_name="Alice"),
    timestamp=datetime(2026, 2, 16, 12, 25, 0),
    update_type="create",
    provenance=Provenance(
        source="user_clarification",
        timestamp=datetime(2026, 2, 16, 12, 25, 0),
        actor_id="user:alice"
    )
)
```

---

### 7. GenerationBlockedBySemanticConflict

**Trigger**: High-severity unresolved conflict at generation boundary
**Purpose**: Record generation gate block decision

**Required fields**:

```python
{
    "event_type": "GenerationBlockedBySemanticConflict",
    "step_id": str,
    "mission_id": str,
    "run_id": str,
    "timestamp": datetime,
    "conflicts": List[ConflictFinding],  # See structure in SemanticCheckEvaluated
    "strictness_mode": str,              # "off" | "medium" | "max"
    "effective_strictness": str          # Resolved strictness (after precedence)
}
```

**Consumers**: Execution runtime, dashboards, audit logs

**Example**:

```python
GenerationBlockedBySemanticConflict(
    step_id="step-specify-001",
    mission_id="041-mission",
    run_id="run-2026-02-16-001",
    timestamp=datetime(2026, 2, 16, 12, 30, 0),
    conflicts=[
        ConflictFinding(
            term="workspace",
            conflict_type="ambiguous",
            severity="high",
            confidence=0.9,
            candidate_senses=[...],
            context="description field"
        )
    ],
    strictness_mode="medium",
    effective_strictness="medium"
)
```

---

## CLI-Specific Events (Pending Feature 007 Approval)

### 8. StepCheckpointed

**Trigger**: Before generation gate evaluation (for resume capability)
**Purpose**: Save minimal state for deterministic resume after conflict resolution

**Required fields**:

```python
{
    "event_type": "StepCheckpointed",
    "mission_id": str,
    "run_id": str,
    "step_id": str,
    "strictness": str,           # "off" | "medium" | "max"
    "scope_refs": List[ScopeRef],  # See structure below
    "input_hash": str,           # SHA256 of step inputs
    "cursor": str,               # e.g., "pre_generation_gate"
    "retry_token": str,          # UUID
    "timestamp": datetime
}
```

**ScopeRef structure**:

```python
{
    "scope": str,          # e.g., "team_domain"
    "version_id": str      # e.g., "v3"
}
```

**Consumers**: Resume middleware, replay engine

**Example**:

```python
StepCheckpointed(
    mission_id="041-mission",
    run_id="run-2026-02-16-001",
    step_id="step-specify-001",
    strictness="medium",
    scope_refs=[
        ScopeRef(scope="mission_local", version_id="v1"),
        ScopeRef(scope="team_domain", version_id="v3")
    ],
    input_hash="abc123...",
    cursor="pre_generation_gate",
    retry_token="uuid-9999-0000",
    timestamp=datetime(2026, 2, 16, 12, 35, 0)
)
```

**Status**: This event may need to be added to Feature 007 canonical events. If not present in spec-kitty-events package, CLI should stub adapter and gate implementation on package update.

---

## Event Emission Guidelines

1. **Import from spec-kitty-events package**:

   ```python
   from spec_kitty_events.glossary.events import (
       GlossaryScopeActivated,
       TermCandidateObserved,
       SemanticCheckEvaluated,
       # ... etc
   )
   ```

2. **DO NOT redefine event schemas locally** - use canonical contracts from package

3. **If event not in package yet** (e.g., StepCheckpointed):
   - Stub adapter boundary in `src/specify_cli/glossary/events.py`
   - Document as "pending Feature 007 approval"
   - Gate implementation on package availability

4. **Event order matters for replay**:
   - Lamport clocks ensure causal ordering
   - Events are append-only, immutable
   - Replay: same events → same state (deterministic)

5. **All events MUST include**:
   - `timestamp` (ISO 8601 format)
   - `mission_id` and `run_id` (for scoping)
   - Appropriate actor/provenance metadata

---

## Testing Event Contracts

**Unit tests** (src/specify_cli/glossary/tests/test_events.py):

- Verify event emission at correct middleware boundaries
- Validate event payload conforms to schema (all required fields present)
- Test event ordering (extraction → check → gate → clarification → resolution)

**Integration tests**:

- Full pipeline: extract → check → block → clarify → resolve → resume
- Verify events emitted in correct order
- Replay events, assert glossary state matches

**Contract tests** (if spec-kitty-events package available):

- Import canonical event classes
- Assert CLI payloads match package schemas
- Test serialization/deserialization round-trip

---

## See Also

- [data-model.md](../data-model.md) - Entity definitions
- [middleware.md](middleware.md) - Middleware interface contracts
- Feature 007 spec: `/Users/robert/ClaudeCowork/Spec-Kitty-Cowork/spec-kitty-planning/product-ideas/prd-mission-glossary-semantic-integrity-v1.md`
